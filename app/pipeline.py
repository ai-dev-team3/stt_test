"""벤치마크 파이프라인: 음성 1개 × API 1개 실행 → 결과/지표 DB 저장.

라우터(routers/evaluate.py)와 스크립트(scripts/run_benchmark.py)가 공유한다.
"""

import json

from sqlalchemy.orm import Session

from app.adapters.base import STTAdapter
from app.analysis.accuracy import accuracy_metrics
from app.analysis.filler import detect_fillers
from app.analysis.intonation import intonation_metrics
from app.analysis.silence import silence_from_stt, speaking_ratio
from app.analysis.speech_rate import speech_rate
from app.analysis.stutter import detect_stutter
from app.models import AudioFile, Metric, STTResult, STTWord


def run_one(session: Session, audio: AudioFile, adapter: STTAdapter) -> STTResult:
    """이미 결과가 있으면 재사용(API 비용 절약), 없으면 호출 후 저장."""
    existing = (
        session.query(STTResult)
        .filter_by(audio_id=audio.id, api_name=adapter.name)
        .one_or_none()
    )
    if existing:
        return existing

    result = adapter.transcribe(audio.file_path)

    row = STTResult(
        audio_id=audio.id,
        api_name=adapter.name,
        transcript=result.transcript,
        latency_sec=result.latency_sec,
        rtf=result.rtf,
        raw_response=json.dumps(result.raw_response, ensure_ascii=False),
    )
    session.add(row)
    session.flush()

    for i, w in enumerate(result.words):
        session.add(
            STTWord(
                result_id=row.id,
                seq=i,
                text=w.text,
                start_sec=w.start,
                end_sec=w.end,
                confidence=w.confidence,
            )
        )

    acc = accuracy_metrics(audio.ground_truth, result.transcript)
    silence = silence_from_stt(result.words, result.audio_duration)
    intonation = intonation_metrics(audio.file_path)
    session.add(
        Metric(
            result_id=row.id,
            wer=acc["wer"],
            cer=acc["cer"],
            sentence_acc=acc["sentence_acc"],
            sps=speech_rate(result)["sps"],
            stutter_count=len(detect_stutter(result.words)),
            filler_count=len(detect_fillers(result.words)),
            silence_total=silence["total_silence"],
            speaking_ratio=speaking_ratio(result),
            f0_std=intonation["f0_std_semitones"],
        )
    )
    session.commit()
    return row
