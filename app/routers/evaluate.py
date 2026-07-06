from fastapi import APIRouter, HTTPException

from app.adapters import available_adapters
from app.db import get_session
from app.models import AudioFile
from app.pipeline import run_one

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("/{audio_id}")
def evaluate(audio_id: int, apis: str | None = None):
    """음성 1개를 설정된 STT API들로 평가. apis="clova,vito" 형태로 제한 가능."""
    adapters = available_adapters()
    if apis:
        requested = set(apis.split(","))
        unknown = requested - adapters.keys()
        if unknown:
            raise HTTPException(400, f"미설정/미지원 API: {sorted(unknown)}")
        adapters = {k: v for k, v in adapters.items() if k in requested}
    if not adapters:
        raise HTTPException(400, "설정된 STT API가 없습니다 (.env 확인)")

    session = get_session()
    try:
        audio = session.get(AudioFile, audio_id)
        if not audio:
            raise HTTPException(404, f"audio_id={audio_id} 없음")
        results = {}
        for name, adapter in adapters.items():
            row = run_one(session, audio, adapter)
            results[name] = {"transcript": row.transcript, "latency_sec": row.latency_sec}
        return {"audio_id": audio_id, "results": results}
    finally:
        session.close()
