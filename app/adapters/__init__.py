from app.adapters.base import NormalizedResult, STTAdapter, Word

__all__ = ["NormalizedResult", "STTAdapter", "Word"]


def available_adapters() -> dict[str, STTAdapter]:
    """API 키가 설정된 어댑터만 인스턴스로 반환한다."""
    from app.adapters.aws import AwsAdapter
    from app.adapters.clova import ClovaAdapter
    from app.adapters.google import GoogleAdapter
    from app.adapters.vito import VitoAdapter

    adapters: dict[str, STTAdapter] = {}
    for cls in (ClovaAdapter, VitoAdapter, GoogleAdapter, AwsAdapter):
        if cls.is_configured():
            adapters[cls.name] = cls()
    return adapters
