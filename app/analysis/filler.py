"""추임새(간투어) 탐지.

전제: STT가 간투어를 필터링하지 않고 전사해야 한다 (verbatim).
이 전제 자체가 API 선정의 핵심 실험 항목이다 (설계서 6.3).
"""

from app.adapters.base import Word

FILLERS = {"음", "어", "그", "저", "뭐", "이제", "약간", "저기", "그러니까"}
# 문맥상 정상 단어일 수 있는 간투어 → 앞뒤 pause 동반 시에만 추임새 판정
AMBIGUOUS = {"그", "저", "이제", "약간", "뭐"}


def detect_fillers(words: list[Word], pause: float = 0.3) -> list[dict]:
    events = []
    for i, w in enumerate(words):
        if w.text not in FILLERS:
            continue
        if w.text in AMBIGUOUS:
            prev_gap = w.start - words[i - 1].end if i > 0 else pause
            next_gap = words[i + 1].start - w.end if i + 1 < len(words) else pause
            if prev_gap < pause and next_gap < pause:
                continue
        events.append({"filler": w.text, "time": w.start})
    return events
