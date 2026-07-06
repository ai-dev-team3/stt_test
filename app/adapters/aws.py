import time
import uuid
from pathlib import Path

import httpx

from app.adapters.base import NormalizedResult, STTAdapter, Word
from app.config import settings


class AwsAdapter(STTAdapter):
    """Amazon Transcribe — S3 업로드 → 비동기 Job → 결과 JSON 파싱.

    item 단위(start_time/end_time/confidence) 제공.
    """

    name = "aws"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(
            settings.aws_access_key_id
            and settings.aws_secret_access_key
            and settings.aws_s3_bucket
        )

    def _transcribe(self, wav_path: str) -> NormalizedResult:
        import boto3

        session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        s3 = session.client("s3")
        transcribe = session.client("transcribe")

        key = f"stt-bench/{uuid.uuid4().hex}_{Path(wav_path).name}"
        job_name = f"stt-bench-{uuid.uuid4().hex}"
        s3.upload_file(wav_path, settings.aws_s3_bucket, key)

        try:
            transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                LanguageCode="ko-KR",
                MediaFormat="wav",
                Media={"MediaFileUri": f"s3://{settings.aws_s3_bucket}/{key}"},
            )
            while True:
                job = transcribe.get_transcription_job(TranscriptionJobName=job_name)[
                    "TranscriptionJob"
                ]
                status = job["TranscriptionJobStatus"]
                if status == "COMPLETED":
                    break
                if status == "FAILED":
                    raise RuntimeError(f"Transcribe job failed: {job.get('FailureReason')}")
                time.sleep(2)
            body = httpx.get(
                job["Transcript"]["TranscriptFileUri"], timeout=60
            ).json()
        finally:
            s3.delete_object(Bucket=settings.aws_s3_bucket, Key=key)

        words: list[Word] = []
        for item in body["results"]["items"]:
            if item["type"] != "pronunciation":  # punctuation 항목 제외
                continue
            alt = item["alternatives"][0]
            words.append(
                Word(
                    text=alt["content"],
                    start=float(item["start_time"]),
                    end=float(item["end_time"]),
                    confidence=float(alt["confidence"]),
                )
            )
        transcript = body["results"]["transcripts"][0]["transcript"]
        return NormalizedResult(
            transcript=transcript,
            words=words,
            audio_duration=0.0,
            raw_response=body,
        )
