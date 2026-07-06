from fastapi import APIRouter
from sqlalchemy import func

from app.db import get_session
from app.models import Metric, STTResult

router = APIRouter(prefix="/report", tags=["report"])


@router.get("")
def report():
    """API별 평균 지표 비교표."""
    session = get_session()
    try:
        rows = (
            session.query(
                STTResult.api_name,
                func.count(Metric.id),
                func.avg(Metric.wer),
                func.avg(Metric.cer),
                func.avg(Metric.sentence_acc),
                func.avg(STTResult.latency_sec),
                func.avg(STTResult.rtf),
                func.avg(Metric.filler_count),
                func.avg(Metric.stutter_count),
            )
            .join(Metric, Metric.result_id == STTResult.id)
            .group_by(STTResult.api_name)
            .all()
        )
        return [
            {
                "api": r[0],
                "n": r[1],
                "avg_wer": r[2],
                "avg_cer": r[3],
                "avg_sentence_acc": r[4],
                "avg_latency_sec": r[5],
                "avg_rtf": r[6],
                "avg_filler_count": r[7],
                "avg_stutter_count": r[8],
            }
            for r in rows
        ]
    finally:
        session.close()
