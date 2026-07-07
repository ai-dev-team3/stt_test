"""DB의 벤치마크 결과 → 마크다운 비교표 출력.

사용법:
    uv run python scripts/build_report.py                       # 콘솔 출력
    uv run python scripts/build_report.py docs/결과표_생성본.md   # 파일로 저장 (UTF-8)

파일 경로를 인자로 주면 스크립트가 직접 UTF-8로 쓴다. Windows/PowerShell의 `>`
리디렉션은 cp949로 재인코딩되어 한글이 깨지므로 사용하지 말 것.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func

from app.db import get_session, init_db
from app.models import Metric, STTResult


def build_report() -> str:
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
            return "결과가 없습니다. 먼저 run_benchmark.py를 실행하세요."

        lines = [
            "# STT API 벤치마크 결과",
            "",
            "| API | n | CER | WER | 문장정확도 | Latency(s) | RTF | 추임새/건 | 더듬음/건 | SPS |",
            "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
        ]
        for r in rows:
            lines.append(
                f"| {r[0]} | {r[1]} | {r[3]:.3f} | {r[2]:.3f} | {r[4]:.3f} "
                f"| {r[5]:.1f} | {r[6]:.2f} | {r[7]:.1f} | {r[8]:.1f} | {r[9]:.2f} |"
            )
        lines.append("")
        lines.append(
            "- CER 오름차순 정렬 (1차 지표). 추임새/더듬음 수치는 verbatim 전사 능력의 간접 지표."
        )
        return "\n".join(lines)
    finally:
        session.close()


def main() -> None:
    # 콘솔 출력을 UTF-8로 (Windows 기본 cp949에서 한글 깨짐 방지)
    sys.stdout.reconfigure(encoding="utf-8")
    report = build_report()
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
        out.write_text(report + "\n", encoding="utf-8")
        print(f"저장 완료: {out} (UTF-8)")
    else:
        print(report)


if __name__ == "__main__":
    main()
