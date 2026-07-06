import uuid
from pathlib import Path

from app.adapters.base import NormalizedResult, STTAdapter, Word
from app.config import settings


class GoogleAdapter(STTAdapter):
    """Google Cloud Speech-to-Text v1 (long_running_recognize).

    1분 초과 오디오는 GCS URI가 필수 → 임시 업로드 후 인식, 완료 시 삭제.
    """

    name = "google"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.gcp_project_id and settings.gcs_bucket)

    def _transcribe(self, wav_path: str) -> NormalizedResult:
        from google.cloud import speech, storage

        # 1) GCS 임시 업로드
        blob_name = f"stt-bench/{uuid.uuid4().hex}_{Path(wav_path).name}"
        bucket = storage.Client(project=settings.gcp_project_id).bucket(
            settings.gcs_bucket
        )
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(wav_path)

        try:
            client = speech.SpeechClient()
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="ko-KR",
                enable_word_time_offsets=True,
                enable_word_confidence=True,
                enable_automatic_punctuation=True,
            )
            audio = speech.RecognitionAudio(uri=f"gs://{settings.gcs_bucket}/{blob_name}")
            operation = client.long_running_recognize(config=config, audio=audio)
            response = operation.result(timeout=600)
        finally:
            blob.delete()

        words: list[Word] = []
        texts: list[str] = []
        for result in response.results:
            alt = result.alternatives[0]
            texts.append(alt.transcript.strip())
            for w in alt.words:
                words.append(
                    Word(
                        text=w.word,
                        start=w.start_time.total_seconds(),
                        end=w.end_time.total_seconds(),
                        confidence=w.confidence or None,
                    )
                )
        return NormalizedResult(
            transcript=" ".join(texts),
            words=words,
            audio_duration=0.0,
            raw_response=type(response).to_dict(response),
        )
