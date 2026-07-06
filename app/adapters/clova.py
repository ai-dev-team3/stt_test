import json

import httpx

from app.adapters.base import NormalizedResult, STTAdapter, Word
from app.config import settings


class ClovaAdapter(STTAdapter):
    """Naver Clova Speech 장문 인식 (파일 업로드, 동기 응답).

    - wordAlignment=True → word timestamp(ms) 제공
    - segment 단위 confidence 제공
    """

    name = "clova"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.clova_invoke_url and settings.clova_secret_key)

    def _transcribe(self, wav_path: str) -> NormalizedResult:
        params = {
            "language": "ko-KR",
            "completion": "sync",
            "wordAlignment": True,
            "fullText": True,
            # 면접 평가 특성상 간투어/반복을 지우지 않는 것이 중요 → 필터 옵션 미사용
        }
        with open(wav_path, "rb") as f:
            resp = httpx.post(
                f"{settings.clova_invoke_url}/recognizer/upload",
                headers={"X-CLOVASPEECH-API-KEY": settings.clova_secret_key},
                files={"media": f},
                data={"params": json.dumps(params)},
                timeout=600,
            )
        resp.raise_for_status()
        body = resp.json()

        words: list[Word] = []
        for seg in body.get("segments", []):
            confidence = seg.get("confidence")  # Clova는 segment 단위 confidence
            for start_ms, end_ms, text in seg.get("words", []):
                words.append(
                    Word(
                        text=text,
                        start=start_ms / 1000,
                        end=end_ms / 1000,
                        confidence=confidence,
                    )
                )
        return NormalizedResult(
            transcript=body.get("text", ""),
            words=words,
            audio_duration=0.0,  # base에서 채움
            raw_response=body,
        )
