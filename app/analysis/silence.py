"""침묵 시간 / 발화 비율.

두 가지 방식을 모두 구현해 실험에서 비교한다 (설계서 6.4, 10.2):
- STT word timestamp gap 기반 (근사)
- webrtcvad 원본 wav 직접 분석 (정밀)
"""

import wave

import webrtcvad

from app.adapters.base import NormalizedResult, Word


def silence_from_stt(
    words: list[Word], audio_duration: float, threshold: float = 1.5
) -> dict:
    """word timestamp gap 기반 침묵 (근사)."""
    gaps: list[tuple[float, float]] = []
    if words and words[0].start >= threshold:  # 답변 시작 전 침묵
        gaps.append((0.0, words[0].start))
    for prev, curr in zip(words, words[1:]):
        if curr.start - prev.end >= threshold:
            gaps.append((prev.end, curr.start))
    if words and audio_duration - words[-1].end >= threshold:  # 답변 후 침묵
        gaps.append((words[-1].end, audio_duration))
    return {
        "silences": gaps,
        "total_silence": sum(e - s for s, e in gaps),
        "max_silence": max((e - s for s, e in gaps), default=0.0),
    }


def _flags_to_intervals(
    flags: list[bool], frame_sec: float, min_dur: float
) -> list[tuple[float, float]]:
    """연속 True 프레임을 (start, end) 구간으로 병합, min_dur 이상만 반환."""
    intervals = []
    start = None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i * frame_sec
        elif not flag and start is not None:
            if i * frame_sec - start >= min_dur:
                intervals.append((start, i * frame_sec))
            start = None
    if start is not None and len(flags) * frame_sec - start >= min_dur:
        intervals.append((start, len(flags) * frame_sec))
    return intervals


def silence_from_vad(
    wav_path: str, aggressiveness: int = 2, threshold: float = 1.5
) -> dict:
    """webrtcvad로 원본 wav에서 직접 침묵 구간 추출 (16kHz/16bit/mono 전제)."""
    vad = webrtcvad.Vad(aggressiveness)
    with wave.open(wav_path) as wf:
        sr = wf.getframerate()
        pcm = wf.readframes(wf.getnframes())
    frame_sec = 0.03  # 30ms
    frame_len = int(sr * frame_sec) * 2  # 16bit = 2 bytes
    silence_flags = [
        not vad.is_speech(pcm[i : i + frame_len], sr)
        for i in range(0, len(pcm) - frame_len, frame_len)
    ]
    gaps = _flags_to_intervals(silence_flags, frame_sec, min_dur=threshold)
    speech_sec = (len(silence_flags) - sum(silence_flags)) * frame_sec
    return {
        "silences": gaps,
        "total_silence": sum(e - s for s, e in gaps),
        "max_silence": max((e - s for s, e in gaps), default=0.0),
        "speech_sec": speech_sec,
    }


def speaking_ratio(result: NormalizedResult) -> float:
    """발화 비율 = 발화 시간(word 구간 합) / 전체 답변 시간."""
    speaking = sum(w.end - w.start for w in result.words)
    return speaking / result.audio_duration if result.audio_duration else 0.0
