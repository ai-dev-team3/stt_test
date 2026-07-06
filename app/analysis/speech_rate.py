"""말속도: 총 음절 수 / 실제 발화 시간 (SPS)."""

import re

from app.adapters.base import NormalizedResult

_HANGUL = re.compile(r"[가-힣]")


def count_syllables(text: str) -> int:
    """한글은 1글자 = 1음절이므로 한글 글자 수를 센다."""
    return len(_HANGUL.findall(text))


def speech_rate(result: NormalizedResult) -> dict:
    syllables = count_syllables(result.transcript)
    speaking_time = sum(w.end - w.start for w in result.words)
    return {
        "syllables": syllables,
        "speaking_time_sec": speaking_time,
        # 한국어 평균 발화 속도 약 5~6 SPS (기준선은 실험으로 보정)
        "sps": syllables / speaking_time if speaking_time else 0.0,
    }
