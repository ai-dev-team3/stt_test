"""더듬음 탐지 (반복 기반).

STT transcript로는 단어 반복/재시작만 탐지 가능하다.
발음 막힘·음절 연장은 STT가 정규화해버리므로 별도 음향분석 영역 (설계서 6.2).
"""

from app.adapters.base import Word


def detect_stutter(words: list[Word], max_gap: float = 1.0) -> list[dict]:
    """인접 단어가 동일(완전 반복)하거나 뒤 단어가 앞 단어로 시작(재시작)하면 더듬음 후보.

    gap이 max_gap보다 크면 의도적 강조/새 문장일 수 있으므로 제외.
    """
    events = []
    for prev, curr in zip(words, words[1:]):
        if curr.start - prev.end > max_gap:
            continue
        if curr.text == prev.text:  # "그 그"
            events.append({"type": "repeat", "word": curr.text, "time": prev.start})
        elif curr.text.startswith(prev.text) and curr.text != prev.text:  # "저 저는"
            events.append({"type": "restart", "word": curr.text, "time": prev.start})
    return events
