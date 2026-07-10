from pathlib import Path

from app.adapters.base import NormalizedResult, STTAdapter, Word

_MODEL_SIZE = "turbo"
_model = None


def _get_model():
    global _model
    if _model is None:
        import whisper

        _model = whisper.load_model(_MODEL_SIZE)
    return _model


def _model_uses_cuda() -> bool:
    device = getattr(_get_model(), "device", None)
    return getattr(device, "type", None) == "cuda"


class WhisperTurboAdapter(STTAdapter):
    """Local openai/whisper turbo model adapter."""

    name = "whisper_turbo"

    @classmethod
    def is_configured(cls) -> bool:
        try:
            import whisper  # noqa: F401
        except ImportError:
            return False
        return True

    def transcribe(self, wav_path: str) -> NormalizedResult:
        _get_model()
        return super().transcribe(wav_path)

    def _transcribe(self, wav_path: str) -> NormalizedResult:
        result = _get_model().transcribe(
            str(Path(wav_path)),
            language="ko",
            task="transcribe",
            word_timestamps=True,
            fp16=_model_uses_cuda(),
        )

        words: list[Word] = []
        for segment in result.get("segments", []):
            for word in segment.get("words", []):
                text = word.get("word", "").strip()
                start = word.get("start")
                end = word.get("end")
                if text and start is not None and end is not None:
                    words.append(
                        Word(
                            text=text,
                            start=float(start),
                            end=float(end),
                            confidence=word.get("probability"),
                        )
                    )

        return NormalizedResult(
            transcript=result.get("text", "").strip(),
            words=words,
            audio_duration=0.0,
            raw_response=result,
        )
