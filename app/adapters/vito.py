import json
import time

import httpx

from app.adapters.base import NormalizedResult, STTAdapter, Word
from app.config import settings

BASE_URL = "https://openapi.vito.ai/v1"


class VitoAdapter(STTAdapter):
    """Vito(리턴제로) STT — 파일 업로드 후 비동기 폴링.

    use_disfluency_filter=False 가 핵심: 간투어/더듬음을 지우지 않고 전사
    (면접 평가의 verbatim 요구사항).
    """

    name = "vito"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.vito_client_id and settings.vito_client_secret)

    def _auth_token(self) -> str:
        resp = httpx.post(
            f"{BASE_URL}/authenticate",
            data={
                "client_id": settings.vito_client_id,
                "client_secret": settings.vito_client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _transcribe(self, wav_path: str) -> NormalizedResult:
        headers = {"Authorization": f"Bearer {self._auth_token()}"}
        config = {
            "use_itn": True,
            "use_disfluency_filter": False,  # 간투어 보존 (verbatim)
            "use_profanity_filter": False,
            "use_diarization": False,
            "use_word_timestamp": True,
        }
        with open(wav_path, "rb") as f:
            resp = httpx.post(
                f"{BASE_URL}/transcribe",
                headers=headers,
                files={"file": f},
                data={"config": json.dumps(config)},
                timeout=120,
            )
        resp.raise_for_status()
        job_id = resp.json()["id"]

        # 폴링 (완료까지 대기)
        while True:
            resp = httpx.get(f"{BASE_URL}/transcribe/{job_id}", headers=headers, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            if body["status"] == "completed":
                break
            if body["status"] == "failed":
                raise RuntimeError(f"Vito job failed: {body}")
            time.sleep(1)

        words: list[Word] = []
        texts: list[str] = []
        for utt in body["results"]["utterances"]:
            texts.append(utt["msg"])
            # utterance 단위 timestamp(ms). word 단위는 응답에 포함되면 사용.
            for w in utt.get("words", []):
                words.append(
                    Word(
                        text=w.get("text", w.get("word", "")),
                        start=w["start_at"] / 1000,
                        end=(w["start_at"] + w["duration"]) / 1000,
                        confidence=w.get("confidence"),
                    )
                )
            if not utt.get("words"):
                # word timestamp 미제공 시 utterance를 하나의 Word로 폴백
                words.append(
                    Word(
                        text=utt["msg"],
                        start=utt["start_at"] / 1000,
                        end=(utt["start_at"] + utt["duration"]) / 1000,
                    )
                )
        return NormalizedResult(
            transcript=" ".join(texts),
            words=words,
            audio_duration=0.0,
            raw_response=body,
        )
