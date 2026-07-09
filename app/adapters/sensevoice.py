"""SenseVoice-Small (알리바바 FunAudioLLM) — 무료 로컬 모델.

- 비자기회귀 구조로 매우 빠름 (85초 오디오 forward ~1.3초, RTX 3070 Ti 기준)
- ko 포함 5개 언어 특화, 감정/이벤트 태그 내장 (raw text의 <|NEUTRAL|> 등)
- timestamp: CTC alignment 기반 — BPE 토큰별 onset(60ms 폭)만 제공하므로
  word span이 아니라 "위치"에 가깝다. 어절 단위로 병합해 근사 span을 만든다.
  → timestamp 정밀도는 설계서 10.2 실험에서 상용 API와 비교 검증
- 최초 실행 시 모델(~1GB)을 자동 다운로드한다
"""

import re

from app.adapters.base import NormalizedResult, STTAdapter, Word

# <|ko|><|NEUTRAL|><|Speech|> 같은 특수 태그 제거용
_TAG = re.compile(r"<\|[^|]+\|>")
_PUNCT = re.compile(r"^[^\w가-힣]+|[^\w가-힣]+$")

_model = None  # 프로세스당 1회만 로드 (로딩 수 초 + 최초 다운로드 수십 분)


def _get_model():
    global _model
    if _model is None:
        import torch
        from funasr import AutoModel

        _model = AutoModel(
            model="iic/SenseVoiceSmall",
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device="cuda" if torch.cuda.is_available() else "cpu",
            disable_update=True,
        )
    return _model


class SenseVoiceAdapter(STTAdapter):
    name = "sensevoice"

    @classmethod
    def is_configured(cls) -> bool:
        try:
            import funasr  # noqa: F401
        except ImportError:
            return False
        return True

    def transcribe(self, wav_path: str) -> NormalizedResult:
        _get_model()  # 모델 다운로드/로딩은 latency 측정에서 제외
        return super().transcribe(wav_path)

    def _transcribe(self, wav_path: str) -> NormalizedResult:
        res = _get_model().generate(
            input=wav_path,
            cache={},
            language="ko",
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
            output_timestamp=True,
        )

        words: list[Word] = []
        texts: list[str] = []
        for seg in res:
            clean = _TAG.sub("", seg["text"]).strip()
            texts.append(clean)
            words.extend(_merge_tokens(clean, seg.get("words") or [], seg.get("timestamp") or []))

        return NormalizedResult(
            transcript=" ".join(t for t in texts if t),
            words=words,
            audio_duration=0.0,  # base에서 채움
            raw_response=res,
        )


def _merge_tokens(
    clean_text: str, tokens: list[str], timestamps: list[list[int]]
) -> list[Word]:
    """BPE 토큰(+ onset timestamp)을 어절 단위 Word로 병합.

    토큰을 순서대로 이어 붙이면 공백 제거한 원문과 일치한다는 성질을 이용,
    각 어절이 소비한 토큰 구간의 [첫 onset, 마지막 onset+폭]을 span으로 삼는다.
    """
    if len(tokens) != len(timestamps):
        return []
    words: list[Word] = []
    ti = 0
    for eojeol in clean_text.split():
        if ti >= len(tokens):
            break
        start = timestamps[ti][0]
        end = timestamps[ti][1]
        acc = ""
        while ti < len(tokens) and len(acc) < len(eojeol):
            acc += tokens[ti].strip()
            end = timestamps[ti][1]
            ti += 1
        text = _PUNCT.sub("", eojeol)  # "그." → "그" (다른 API와 일관성)
        if text:
            words.append(Word(text=text, start=start / 1000, end=end / 1000))
    return words
