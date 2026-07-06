"""억양 분석 — STT로 불가능한 영역, parselmouth(Praat)로 원본 wav 분석 (설계서 6.6)."""

import numpy as np
import parselmouth


def intonation_metrics(wav_path: str) -> dict:
    snd = parselmouth.Sound(wav_path)
    pitch = snd.to_pitch(time_step=0.01)
    f0 = pitch.selected_array["frequency"]
    f0 = f0[f0 > 0]  # 무성 구간 제거
    if len(f0) == 0:
        return {"f0_mean_hz": None, "f0_std_semitones": None, "f0_range_semitones": None}
    # 화자 기본 pitch로 정규화 (남/녀 음역대 차이 제거)
    semitones = 12 * np.log2(f0 / np.median(f0))
    return {
        "f0_mean_hz": float(np.mean(f0)),
        "f0_std_semitones": float(np.std(semitones)),  # 낮을수록 단조로운 억양
        "f0_range_semitones": float(
            np.percentile(semitones, 95) - np.percentile(semitones, 5)
        ),
    }
