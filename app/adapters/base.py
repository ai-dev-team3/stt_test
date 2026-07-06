import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import soundfile as sf


@dataclass
class Word:
    text: str
    start: float  # 초
    end: float  # 초
    confidence: float | None = None


@dataclass
class NormalizedResult:
    transcript: str
    words: list[Word]
    audio_duration: float  # 전체 오디오 길이(초)
    latency_sec: float = 0.0
    raw_response: dict | list | None = field(default=None, repr=False)

    @property
    def rtf(self) -> float | None:
        """Real-Time Factor = 처리시간 / 오디오길이"""
        return self.latency_sec / self.audio_duration if self.audio_duration else None


def audio_duration_sec(wav_path: str) -> float:
    info = sf.info(wav_path)
    return info.frames / info.samplerate


class STTAdapter(ABC):
    """4개 STT API를 공통 스키마(NormalizedResult)로 정규화하는 어댑터.

    latency 측정을 일관되게 하기 위해 transcribe()가 시간을 재고,
    구현체는 _transcribe()만 작성한다.
    """

    name: str = "base"

    @classmethod
    @abstractmethod
    def is_configured(cls) -> bool:
        """필요한 API 키가 .env에 설정되어 있는지."""

    @abstractmethod
    def _transcribe(self, wav_path: str) -> NormalizedResult: ...

    def transcribe(self, wav_path: str) -> NormalizedResult:
        started = time.monotonic()
        result = self._transcribe(wav_path)
        result.latency_sec = time.monotonic() - started
        if not result.audio_duration:
            result.audio_duration = audio_duration_sec(wav_path)
        return result
