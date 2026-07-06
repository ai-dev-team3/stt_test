"""DB의 벤치마크 결과 → 마크다운 비교표 출력.

사용법: uv run python scripts/build_report.py [> reports/comparison.md]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func

from app.db import get_session, init_db
from app.models import Metric, STTResult


def main() -> None:
    init_db()
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
                func.avg(Metric.sps),
            )
            .join(Metric, Metric.result_id == STTResult.id)
            .group_by(STTResult.api_name)
            .order_by(func.avg(Metric.cer))
            .all()
        )
        if not rows:
            print("결과가 없습니다. 먼저 run_benchmark.py를 실행하세요.")
            return

        print("# STT API 벤치마크 결과\n")
        print("| API | n | CER | WER | 문장정확도 | Latency(s) | RTF | 추임새/건 | 더듬음/건 | SPS |")
        print("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
        for r in rows:
            print(
                f"| {r[0]} | {r[1]} | {r[3]:.3f} | {r[2]:.3f} | {r[4]:.3f} "
                f"| {r[5]:.1f} | {r[6]:.2f} | {r[7]:.1f} | {r[8]:.1f} | {r[9]:.2f} |"
            )
        print("\n- CER 오름차순 정렬 (1차 지표). 추임새/더듬음 수치는 verbatim 전사 능력의 간접 지표.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
