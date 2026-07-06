"""DB 모델 — 설계서 9장 스키마."""

from datetime import datetime

from sqlalchemy import ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str]  # data/origin/.../ckmk_a_*.wav
    ground_truth: Mapped[str] = mapped_column(Text)  # label의 answer.raw.text
    duration_ms: Mapped[int]
    gender: Mapped[str | None]  # FEMALE / MALE
    experience: Mapped[str | None]  # NEW / EXPERIENCED

    results: Mapped[list["STTResult"]] = relationship(back_populates="audio")


class STTResult(Base):
    __tablename__ = "stt_results"
    __table_args__ = (UniqueConstraint("audio_id", "api_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    audio_id: Mapped[int] = mapped_column(ForeignKey("audio_files.id"))
    api_name: Mapped[str]  # clova / vito / google / aws
    transcript: Mapped[str | None] = mapped_column(Text)
    latency_sec: Mapped[float | None]
    rtf: Mapped[float | None]
    raw_response: Mapped[str | None] = mapped_column(Text)  # 원본 JSON (사후 분석용)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    audio: Mapped[AudioFile] = relationship(back_populates="results")
    words: Mapped[list["STTWord"]] = relationship(back_populates="result")
    metric: Mapped["Metric | None"] = relationship(back_populates="result")


class STTWord(Base):
    __tablename__ = "stt_words"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("stt_results.id"))
    seq: Mapped[int]
    text: Mapped[str]
    start_sec: Mapped[float]
    end_sec: Mapped[float]
    confidence: Mapped[float | None]

    result: Mapped[STTResult] = relationship(back_populates="words")


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("stt_results.id"))
    wer: Mapped[float | None]
    cer: Mapped[float | None]
    sentence_acc: Mapped[float | None]
    sps: Mapped[float | None]  # 말속도
    stutter_count: Mapped[int | None]
    filler_count: Mapped[int | None]
    silence_total: Mapped[float | None]
    speaking_ratio: Mapped[float | None]
    f0_std: Mapped[float | None]  # 억양 (API 무관, 조인 편의상 저장)

    result: Mapped[STTResult] = relationship(back_populates="metric")
