from app.adapters.base import NormalizedResult, STTAdapter, Word

__all__ = ["NormalizedResult", "STTAdapter", "Word"]


def available_adapters() -> dict[str, STTAdapter]:
    """API 키(또는 로컬 모델)가 준비된 어댑터만 인스턴스로 반환한다."""
    from app.adapters.clova import ClovaAdapter
    from app.adapters.sensevoice import SenseVoiceAdapter
    from app.adapters.vito import VitoAdapter
    from app.adapters.whisper import WhisperAdapter

    adapters: dict[str, STTAdapter] = {}
    for cls in (ClovaAdapter, VitoAdapter, WhisperAdapter, SenseVoiceAdapter):
        if cls.is_configured():
            adapters[cls.name] = cls()
    return adapters
