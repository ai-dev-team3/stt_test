"""data/ 전체를 설정된 STT API들로 일괄 실행 → DB 적재.

사용법:
    uv run python scripts/run_benchmark.py           # 설정된 모든 API
    uv run python scripts/run_benchmark.py clova     # 특정 API만
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters import available_adapters
from app.db import get_session, init_db
from app.models import AudioFile
from app.pipeline import run_one

DATA_DIR = Path(__file__).parent.parent / "data"


def load_audio_files(session) -> list[AudioFile]:
    """label JSON을 파싱해 답변 wav를 audio_files에 적재 (이미 있으면 재사용)."""
    audios = []
    for label_path in sorted(DATA_DIR.glob("label/**/*.json")):
        with open(label_path, encoding="utf-8") as f:
            label = json.load(f)
        # ckmk_d_..._{id}.json → ckmk_a_..._{id}.wav (같은 성별/경력 하위 경로)
        wav_name = label_path.stem.replace("ckmk_d_", "ckmk_a_") + ".wav"
        rel = label_path.relative_to(DATA_DIR / "label").parent
        wav_path = DATA_DIR / "origin" / rel / wav_name
        if not wav_path.exists():
            print(f"[skip] 답변 wav 없음: {wav_path}")
            continue

        existing = (
            session.query(AudioFile).filter_by(file_path=str(wav_path)).one_or_none()
        )
        if existing:
            audios.append(existing)
            continue

        info = label["dataSet"]["info"]
        audio = AudioFile(
            file_path=str(wav_path),
            ground_truth=label["dataSet"]["answer"]["raw"]["text"],
            duration_ms=label["rawDataInfo"]["answer"]["duration"],
            gender=info.get("gender"),
            experience=info.get("experience"),
        )
        session.add(audio)
        session.flush()
        audios.append(audio)
    session.commit()
    return audios


def main() -> None:
    init_db()
    adapters = available_adapters()
    if len(sys.argv) > 1:
        adapters = {k: v for k, v in adapters.items() if k in sys.argv[1:]}
    if not adapters:
        print("설정된 STT API가 없습니다. .env를 확인하세요 (.env.example 참고)")
        return
    print(f"실행 대상 API: {', '.join(adapters)}")

    session = get_session()
    try:
        audios = load_audio_files(session)
        print(f"평가 대상 음성: {len(audios)}개\n")
        for audio in audios:
            for name, adapter in adapters.items():
                try:
                    row = run_one(session, audio, adapter)
                    print(
                        f"[ok] {Path(audio.file_path).name} × {name}: "
                        f"latency={row.latency_sec:.1f}s"
                    )
                except Exception as e:  # 개별 실패가 전체를 멈추지 않게
                    session.rollback()
                    print(f"[fail] {Path(audio.file_path).name} × {name}: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
