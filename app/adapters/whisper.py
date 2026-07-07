from pathlib import Path

import httpx

from app.adapters.base import NormalizedResult, STTAdapter, Word
from app.config import settings


class WhisperAdapter(STTAdapter):
    """OpenAI Whisper API (whisper-1).

    - verbose_json + timestamp_granularities=word → word timestamp 제공
    - confidence는 word 단위로 제공하지 않음 (None)
    - 주의: Whisper는 간투어/반복을 정규화하는 경향 → verbatim 보존율 실험 대상
    """

    name = "whisper"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.openai_api_key)

    def _transcribe(self, wav_path: str) -> NormalizedResult:
        with open(wav_path, "rb") as f:
            resp = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                files={"file": (Path(wav_path).name, f, "audio/wav")},
                data={
                    "model": "whisper-1",
                    "language": "ko",
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word",
                },
                timeout=600,
            )
        resp.raise_for_status()
        body = resp.json()

        words = [
            Word(text=w["word"], start=w["start"], end=w["end"])
            for w in body.get("words", [])
        ]
        return NormalizedResult(
            transcript=body.get("text", "").strip(),
            words=words,
            audio_duration=0.0,  # base에서 채움
            raw_response=body,
        )
