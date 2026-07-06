# AI 면접 서비스용 STT API 선정 프로젝트 설계서

> 작성일: 2026-07-06
> 대상 API: Naver Clova Speech / Vito(리턴제로) STT / Google Cloud Speech-to-Text / Amazon Transcribe

---

## 1. 프로젝트 개요

한국어 면접 음성 데이터셋(음성 + 정답 텍스트)을 이용해 4개 상용 STT API를 **동일 조건에서 벤치마크**하고,
그 결과를 근거로 **AI 면접 평가 서비스에 가장 적합한 STT API를 선정**하는 사이드 프로젝트.

- **데이터**: AI Hub 채용면접 인터뷰 데이터 (`data/origin/*.wav` + `data/label/*.json`)
  - wav: 16kHz / 16bit / mono, 질문(`ckmk_q_*`)·답변(`ckmk_a_*`) 분리
  - label: `dataSet.answer.raw.text` = 답변 정답 전사(Ground Truth), `rawDataInfo.answer.duration` = 발화 길이(ms)
  - **답변(`ckmk_a_*`) 파일만 평가 대상으로 사용** (면접 평가 대상은 지원자 발화이므로)
- **평가 환경**: Python 3.11+ / FastAPI

## 2. 프로젝트 목적

단순 "어느 STT가 정확한가"가 아니라, 다음 질문에 답하는 것이 목적이다.

> **"AI 면접 평가(말속도·더듬음·추임새·침묵·발화비율·억양)를 구현하기 위해
> 어떤 STT API가 가장 적합하며, 그 근거는 무엇인가?"**

따라서 정확도(WER/CER) 외에 **면접 평가에 필요한 메타데이터(word timestamp, confidence, 간투어 보존 여부)** 를
API가 얼마나 제공하는지가 핵심 평가축이다.

## 3. 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
│                                                              │
│  ┌──────────┐   ┌─────────────────────────────────────┐     │
│  │ /evaluate │──▶│           STT Adapter Layer          │     │
│  └──────────┘   │  ┌───────┐ ┌──────┐ ┌────────┐ ┌───┐ │     │
│                 │  │ Clova │ │ Vito │ │ Google │ │AWS│ │     │
│                 │  └───┬───┘ └──┬───┘ └───┬────┘ └─┬─┘ │     │
│                 └──────┼────────┼─────────┼────────┼───┘     │
│                        ▼        ▼         ▼        ▼         │
│                 ┌─────────────────────────────────────┐     │
│                 │   공통 결과 스키마 (NormalizedResult)   │     │
│                 │  transcript / words[] / confidence   │     │
│                 └──────────────────┬──────────────────┘     │
│                                    ▼                         │
│  ┌──────────────────┐   ┌──────────────────────────┐        │
│  │  음향 분석 모듈     │──▶│      후처리 / 평가 모듈      │        │
│  │ librosa/parsel-  │   │ WER·CER / 말속도 / 더듬음   │        │
│  │ mouth/webrtcvad  │   │ 추임새 / 침묵 / 억양        │        │
│  └──────────────────┘   └────────────┬─────────────┘        │
│                                      ▼                       │
│                              ┌──────────────┐                │
│                              │  DB (SQLite/  │                │
│                              │  PostgreSQL) │                │
│                              └──────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

핵심 설계 원칙: **4개 API의 응답을 하나의 공통 스키마로 정규화**하는 Adapter 패턴.
후처리·평가 코드는 API에 독립적이 되어, API 교체 비용이 어댑터 1개 구현으로 줄어든다.

## 4. 전체 처리 흐름

```
음성 파일 (data/origin/**/ckmk_a_*.wav)
   ↓
STT API 호출 (4개 병렬, 응답시간 측정)
   ↓
공통 스키마 정규화 (transcript, words[{text, start, end, confidence}])
   ↓
후처리 (텍스트 정규화, VAD, pitch 추출)
   ↓
음성 평가 (WER/CER + 말속도/더듬음/추임새/침묵/발화비율/억양)
   ↓
결과 저장 (DB) → 비교 리포트 생성
```

## 5. API 비교표

### 5.1 기능 비교 (사전 조사 — 실험으로 검증할 가설)

| 항목 | Clova Speech | Vito (리턴제로) | Google STT (v2) | Amazon Transcribe |
|---|---|---|---|---|
| 한국어 특화 | ◎ (네이버 자체 학습) | ◎ (한국어 전용) | ○ (다국어 중 하나) | ○ (다국어 중 하나) |
| Word timestamp | ✅ 제공 | ✅ 제공 | ✅ 제공 (`enable_word_time_offsets`) | ✅ 제공 |
| Sentence/segment timestamp | ✅ segment 단위 제공 | ✅ utterance 단위 | △ (word에서 조합) | △ (word에서 조합) |
| Confidence | ✅ segment 단위 | ✅ 제공 | ✅ word 단위 | ✅ word 단위 |
| Speaker Diarization | ✅ (한국어 지원) | ✅ (한국어 지원) | ⚠️ ko-KR 지원 제한적 → **실험 확인 필요** | ✅ (최대 10명) |
| 간투어("음","어") 전사 | ⚠️ 필터링 옵션 있음 → verbatim 설정 확인 | ✅ 간투어 보존 옵션 | ⚠️ 필터링 경향 → 실험 확인 | ✅ vocabulary filter 미사용 시 보존 |
| 실시간 스트리밍 | ✅ (gRPC) | ✅ (WebSocket) | ✅ (gRPC) | ✅ (WebSocket) |
| 요청 방식 | 파일 업로드/URL | 파일 업로드 (비동기 폴링) | 파일/GCS URI | S3 URI (비동기) |

> ⚠️ 표시 항목은 문서만으로 단정할 수 없어 **실험 항목**으로 편입한다. 특히 "간투어 보존 여부"는
> 추임새·더듬음 평가의 성립 조건이므로 **정확도만큼 중요한 검증 대상**이다.

### 5.2 비용 비교 (2026-07 공시가 기준 추정치 — 계약/환율에 따라 변동, 실험 시점에 재확인)

| API | 단가 (기준) | 100시간 | 1,000시간 | 10,000시간 |
|---|---|---|---|---|
| Clova Speech (장문) | 4원 / 15초 (≈960원/시간) | ≈ 9.6만 원 | ≈ 96만 원 | ≈ 960만 원 |
| Vito STT | ≈ 0.3원/초 (≈1,080원/시간, 월 무료량 별도) | ≈ 10.8만 원 | ≈ 108만 원 | ≈ 1,080만 원 |
| Google STT v1 Standard | $0.024/분 (≈$1.44/시간) | ≈ $144 (≈20만 원) | ≈ $1,440 (≈200만 원) | ≈ $14,400 (≈2,000만 원, 구간할인 별도) |
| Amazon Transcribe | $0.024/분 T1 → $0.015/분 T2(25만 분 초과) | ≈ $144 (≈20만 원) | ≈ $1,440 (≈200만 원) | ≈ $11,000대 (구간할인 적용) |

관찰 포인트: **국내 API(Clova/Vito)가 글로벌 API 대비 절반 이하 비용**. 환율 리스크도 없다.
단, Google v2의 dynamic batch(비실시간 허용 시)·AWS 구간할인은 대량 사용 시 격차를 줄인다.

### 5.3 구현 난이도 (Python/FastAPI 기준)

| API | 난이도 | 비고 |
|---|---|---|
| Vito | ★☆☆ | REST + JWT, 문서 간결. 비동기 폴링만 구현하면 됨 |
| Clova | ★★☆ | REST, Secret Key 방식. 장문 인식은 사실상 REST 한 번 호출 |
| Google | ★★★ | GCP 프로젝트/서비스계정/GCS 세팅 필요. SDK는 잘 되어 있음 |
| AWS | ★★★ | S3 업로드 → 비동기 Job → 결과 JSON 다운로드. IAM 세팅 필요 |

### 5.4 응답속도 (실험으로 측정)

측정 지표: **RTF (Real-Time Factor) = 처리시간 / 오디오길이**, 그리고 요청→결과 수신까지의 wall-clock latency.

- 면접 서비스는 "답변 종료 후 수 초 내 분석"이면 충분 → **배치 RTF < 0.5, latency < 오디오길이의 30%** 를 합격선으로 설정
- 실시간 자막이 요구사항이 되면 스트리밍 first-token latency도 별도 측정

## 6. 면접 음성 평가 지표 — STT 가능 여부 분석

**범례**: `STT만` = API 응답만으로 계산 / `후처리` = API 응답 + 우리 코드 / `음향분석` = 원본 wav 별도 분석 필요

### 6.1 말속도

| 구분 | 내용 |
|---|---|
| 필요 데이터 | transcript, word timestamp |
| 계산 방법 | 총 음절 수(한글 글자 수) ÷ 실제 발화 시간(침묵 제외) → SPS(syllables/sec) |
| 판정 | **STT만으로 가능** (후처리는 단순 계산) |

### 6.2 더듬음

| 구분 | 내용 |
|---|---|
| STT로 가능한 것 | 단어 반복("그 그 그래서"), 구/문장 반복, 재시작("저는 저는요") — transcript + word timestamp로 탐지 |
| STT로 불가능한 것 | 발음 막힘(block), 음절 연장(prolongation, "그으으래서"), 음절 내 끊김 — STT가 정규화해서 출력하므로 텍스트에 안 남음 |
| 추가 분석 | librosa(에너지·스펙트럼 연속성), parselmouth(포먼트 지속시간) |
| 판정 | **후처리(반복) + 음향분석(막힘/연장)** |
| ⚠️ 성립 조건 | STT가 반복을 "정리"하지 않고 **verbatim으로 전사**해야 함 → 실험 항목 |

### 6.3 불필요한 추임새

| 구분 | 내용 |
|---|---|
| 필요 데이터 | transcript (간투어가 보존된), word timestamp |
| 계산 방법 | 간투어 사전("음", "어", "그", "저기", "뭐랄까", "약간", "이제" 등) 매칭 + 문맥 필터(단독 발화 + 앞뒤 pause 동반 시 추임새로 판정) |
| 판정 | **후처리 필요** (STT가 간투어를 전사한다는 전제 하에) |
| ⚠️ 성립 조건 | **간투어 필터링을 끈 상태로 전사 가능한 API여야 함** — 4개 API 중 이것이 안 되는 API는 면접 평가용으로 치명적 감점 |

### 6.4 침묵 시간

| 구분 | 내용 |
|---|---|
| STT로 근사 | word timestamp 간 gap ≥ 임계값(예: 1.5초)을 침묵으로 집계 |
| STT의 한계 | STT는 "인식된 단어" 기준이라 잡음·숨소리 구간 처리 방식이 API마다 다름 |
| 추가 분석 | webrtcvad 또는 silero-vad로 원본 wav에서 직접 발화/비발화 구간 추출 → 더 정확 |
| 판정 | **후처리(근사 가능) + 음향분석(정밀)** — 실험에서 두 방식의 차이를 측정해 STT gap만으로 충분한지 판단 |

### 6.5 발화 비율

| 구분 | 내용 |
|---|---|
| 계산 방법 | 총 발화 시간(word timestamp 합 또는 VAD 발화 구간 합) ÷ 전체 답변 시간 |
| 판정 | **후처리** (침묵 계산의 부산물) |

### 6.6 억양 분석

| 구분 | 내용 |
|---|---|
| STT로 가능한 것 | 없음 — STT는 pitch/에너지 정보를 제공하지 않음 |
| 필요 분석 | parselmouth(Praat)로 F0(기본 주파수) 컨투어 추출 → 평균 pitch, pitch 표준편차(단조로움 지표), 문장 끝 pitch 하강 패턴 |
| STT의 역할 | word/sentence timestamp로 pitch 컨투어를 문장 단위로 분할하는 기준 제공 |
| 판정 | **음향분석 필수** (STT는 시간축 정렬 보조) |

### 6.7 요약 매트릭스

| 지표 | STT만 | 후처리 | 음향분석 | STT에 요구되는 것 |
|---|:-:|:-:|:-:|---|
| 말속도 | ✅ | 계산만 | – | word timestamp 정확도 |
| 더듬음(반복) | – | ✅ | – | **verbatim 전사** + timestamp |
| 더듬음(막힘/연장) | – | – | ✅ | timestamp (구간 정렬용) |
| 추임새 | – | ✅ | – | **간투어 보존 전사** |
| 침묵 | – | ✅(근사) | ✅(정밀) | timestamp |
| 발화 비율 | – | ✅ | ✅(보조) | timestamp |
| 억양 | – | – | ✅ | timestamp (구간 정렬용) |

> **결론적으로 STT 선정에서 가장 중요한 것은 ① word timestamp의 존재와 정확도,
> ② 간투어/반복을 지우지 않는 verbatim 전사 옵션, ③ 한국어 정확도(CER)** 이다.
> 억양·발음 막힘은 어떤 STT를 선택해도 별도 음향분석이 필요하므로 선정 기준에서 제외된다.

## 7. 음성 평가 알고리즘 (후처리 구현 설계)

모든 알고리즘은 공통 정규화 스키마를 입력으로 받는다:

```python
from dataclasses import dataclass

@dataclass
class Word:
    text: str
    start: float   # 초
    end: float     # 초
    confidence: float | None

@dataclass
class NormalizedResult:
    transcript: str
    words: list[Word]
    audio_duration: float   # 전체 오디오 길이(초)
```

### 7.1 말속도 계산

```python
import re

HANGUL = re.compile(r"[가-힣]")

def count_syllables(text: str) -> int:
    """한글은 1글자 = 1음절이므로 한글 글자 수를 센다."""
    return len(HANGUL.findall(text))

def speech_rate(result: NormalizedResult) -> dict:
    syllables = count_syllables(result.transcript)
    # 발화 시간 = 각 단어 구간의 합 (침묵 제외)
    speaking_time = sum(w.end - w.start for w in result.words)
    return {
        "syllables": syllables,
        "speaking_time_sec": speaking_time,
        "sps": syllables / speaking_time if speaking_time else 0.0,
        # 한국어 평균 발화 속도 약 5~6 SPS. 4 미만 느림 / 7 초과 빠름 (기준은 실험으로 보정)
    }
```

### 7.2 더듬음 탐지 (반복 기반)

```python
def detect_stutter(words: list[Word], max_gap: float = 1.0) -> list[dict]:
    """인접 단어가 동일하거나(완전 반복), 뒤 단어가 앞 단어로 시작(재시작)하면 더듬음 후보.
    gap이 크면 의도적 강조일 수 있으므로 max_gap 이내만 인정."""
    events = []
    for prev, curr in zip(words, words[1:]):
        gap = curr.start - prev.end
        if gap > max_gap:
            continue
        if curr.text == prev.text:                       # "그 그"
            events.append({"type": "repeat", "word": curr.text, "time": prev.start})
        elif len(prev.text) >= 1 and curr.text.startswith(prev.text) and curr.text != prev.text:
            events.append({"type": "restart", "word": curr.text, "time": prev.start})  # "저 저는"
    return events
```

발음 막힘/연장은 STT로 불가 → librosa 에너지 기반 보완(선택 구현):

```python
import librosa
import numpy as np

def detect_prolongation(wav_path: str, min_dur: float = 0.8) -> list[tuple[float, float]]:
    """스펙트럼 변화가 거의 없는 유성음 구간이 min_dur 이상 지속되면 음절 연장 후보."""
    y, sr = librosa.load(wav_path, sr=16000)
    flux = librosa.onset.onset_strength(y=y, sr=sr)          # 프레임별 스펙트럼 변화량
    rms = librosa.feature.rms(y=y)[0]
    frame_t = librosa.frames_to_time(np.arange(len(flux)), sr=sr)
    is_flat = (flux < np.percentile(flux, 20)) & (rms[:len(flux)] > np.percentile(rms, 40))
    # 연속 flat 구간을 (start, end)로 병합 후 min_dur 이상만 반환
    return merge_runs(is_flat, frame_t, min_dur)
```

### 7.3 추임새 탐지

```python
FILLERS = {"음", "어", "그", "저", "뭐", "이제", "약간", "저기", "그러니까"}
AMBIGUOUS = {"그", "저", "이제", "약간"}   # 문맥상 정상 단어일 수 있는 것들

def detect_fillers(words: list[Word], pause: float = 0.3) -> list[dict]:
    events = []
    for i, w in enumerate(words):
        if w.text not in FILLERS:
            continue
        # 모호한 간투어는 앞뒤에 pause가 있을 때만 추임새로 판정
        if w.text in AMBIGUOUS:
            prev_gap = w.start - words[i-1].end if i > 0 else pause
            next_gap = words[i+1].start - w.end if i+1 < len(words) else pause
            if prev_gap < pause and next_gap < pause:
                continue
        events.append({"filler": w.text, "time": w.start})
    return events
```

### 7.4 침묵 시간 계산

```python
def silence_from_stt(words: list[Word], audio_duration: float,
                     threshold: float = 1.5) -> dict:
    """word timestamp gap 기반 침묵 (근사)."""
    gaps = []
    # 답변 시작 전 침묵
    if words and words[0].start >= threshold:
        gaps.append((0.0, words[0].start))
    for prev, curr in zip(words, words[1:]):
        if curr.start - prev.end >= threshold:
            gaps.append((prev.end, curr.start))
    return {
        "silences": gaps,
        "total_silence": sum(e - s for s, e in gaps),
        "max_silence": max((e - s for s, e in gaps), default=0.0),
    }
```

정밀 버전 (webrtcvad, 원본 wav 직접 분석):

```python
import webrtcvad, wave

def silence_from_vad(wav_path: str, aggressiveness: int = 2) -> list[tuple[float, float]]:
    vad = webrtcvad.Vad(aggressiveness)
    with wave.open(wav_path) as wf:
        sr, pcm = wf.getframerate(), wf.readframes(wf.getnframes())
    frame_len = int(sr * 0.03) * 2                     # 30ms, 16bit
    speech_flags = [
        vad.is_speech(pcm[i:i+frame_len], sr)
        for i in range(0, len(pcm) - frame_len, frame_len)
    ]
    return flags_to_silence_intervals(speech_flags, frame_sec=0.03)
```

### 7.5 발화 비율 계산

```python
def speaking_ratio(words: list[Word], audio_duration: float) -> float:
    speaking = sum(w.end - w.start for w in words)
    return speaking / audio_duration if audio_duration else 0.0
```

### 7.6 억양 분석 (parselmouth)

```python
import parselmouth
import numpy as np

def intonation_metrics(wav_path: str) -> dict:
    snd = parselmouth.Sound(wav_path)
    pitch = snd.to_pitch(time_step=0.01)
    f0 = pitch.selected_array["frequency"]
    f0 = f0[f0 > 0]                        # 무성 구간 제거
    if len(f0) == 0:
        return {"error": "no voiced frames"}
    semitones = 12 * np.log2(f0 / np.median(f0))   # 화자 기본 pitch 정규화
    return {
        "f0_mean_hz": float(np.mean(f0)),
        "f0_std_semitones": float(np.std(semitones)),  # 낮으면 단조로운 억양
        "f0_range_semitones": float(np.percentile(semitones, 95)
                                    - np.percentile(semitones, 5)),
    }
```

STT의 sentence timestamp와 결합하면 "문장 끝 pitch 하강 여부"(자신감 지표)도 문장 단위로 계산 가능.

## 8. FastAPI 프로젝트 구조

```
stt_test/
├── app/
│   ├── main.py                  # FastAPI 엔트리포인트
│   ├── config.py                # API 키, 경로 설정 (pydantic-settings)
│   ├── adapters/                # ★ STT Adapter Layer
│   │   ├── base.py              # STTAdapter 추상클래스 + NormalizedResult
│   │   ├── clova.py
│   │   ├── vito.py
│   │   ├── google.py
│   │   └── aws.py
│   ├── analysis/                # 후처리·음향분석
│   │   ├── accuracy.py          # WER / CER / 문장 정확도
│   │   ├── speech_rate.py
│   │   ├── stutter.py
│   │   ├── filler.py
│   │   ├── silence.py           # STT gap + webrtcvad
│   │   └── intonation.py        # parselmouth
│   ├── models/                  # SQLAlchemy 모델
│   ├── routers/
│   │   ├── evaluate.py          # POST /evaluate  (파일 1개 → 4 API 실행)
│   │   └── report.py            # GET  /report    (비교 리포트)
│   └── db.py
├── scripts/
│   ├── run_benchmark.py         # data/ 전체 일괄 실행
│   └── build_report.py          # DB → 마크다운/CSV 비교표
├── data/                        # (기존) origin / label
├── docs/
└── requirements.txt
```

어댑터 인터페이스:

```python
class STTAdapter(ABC):
    name: str

    @abstractmethod
    async def transcribe(self, wav_path: str) -> NormalizedResult: ...
    # 내부에서 latency를 측정해 NormalizedResult.meta에 기록
```

## 9. DB 설계

```sql
-- 평가 대상 음성 파일 (label JSON에서 적재)
CREATE TABLE audio_files (
    id            INTEGER PRIMARY KEY,
    file_path     TEXT NOT NULL,          -- data/origin/.../ckmk_a_*.wav
    ground_truth  TEXT NOT NULL,          -- label의 answer.raw.text
    duration_ms   INTEGER NOT NULL,
    gender        TEXT,                   -- FEMALE / MALE
    experience    TEXT                    -- NEW / EXPERIENCED
);

-- STT 호출 결과 (파일 × API 당 1행)
CREATE TABLE stt_results (
    id            INTEGER PRIMARY KEY,
    audio_id      INTEGER REFERENCES audio_files(id),
    api_name      TEXT NOT NULL,          -- clova / vito / google / aws
    transcript    TEXT,
    latency_sec   REAL,                   -- 요청→응답
    rtf           REAL,                   -- latency / duration
    raw_response  TEXT,                   -- 원본 JSON (사후 분석용)
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(audio_id, api_name)
);

-- word timestamp (정규화 스키마)
CREATE TABLE stt_words (
    id          INTEGER PRIMARY KEY,
    result_id   INTEGER REFERENCES stt_results(id),
    seq         INTEGER,
    text        TEXT,
    start_sec   REAL,
    end_sec     REAL,
    confidence  REAL
);

-- 평가 지표 (파일 × API 당 1행)
CREATE TABLE metrics (
    id             INTEGER PRIMARY KEY,
    result_id      INTEGER REFERENCES stt_results(id),
    wer            REAL,
    cer            REAL,
    sentence_acc   REAL,
    sps            REAL,     -- 말속도
    stutter_count  INTEGER,
    filler_count   INTEGER,
    silence_total  REAL,
    speaking_ratio REAL,
    f0_std         REAL      -- 억양 (API 무관하지만 조인 편의상 저장)
);
```

소규모 실험이므로 SQLite로 시작, 서비스 전환 시 PostgreSQL (스키마 호환).

## 10. 실험 방법

### 10.1 정확도 측정 프로토콜

1. **텍스트 정규화** (양쪽 동일 적용 — 공정성의 핵심)
   - 문장부호·특수문자 제거, 공백 정리
   - 숫자 표기 통일 (예: "3년" vs "삼 년" → 한쪽으로 변환)
   - ⚠️ 간투어는 **정확도 계산 시에는 GT에 있는 그대로 유지** (간투어 전사 능력도 정확도의 일부)
2. **지표 계산** — `jiwer` 라이브러리 사용
   - **CER을 1차 지표로 사용** — 한국어는 교착어라 띄어쓰기 변동이 커서 WER이 과대평가됨
   - WER은 참고 지표, 문장 정확도 = 정규화 후 완전 일치 문장 비율
3. **층화 분석**: 성별(M/F) × 경력(신입/경력) 그룹별로 나눠 편차 확인

### 10.2 기능 검증 프로토콜 (면접 특화)

| 실험 | 방법 | 검증 대상 |
|---|---|---|
| Verbatim 검증 | GT에 반복/간투어가 포함된 샘플 선별 → 각 API 전사에 보존됐는지 수동 대조 | 더듬음·추임새 평가 성립 여부 |
| Timestamp 정확도 | 샘플 5개를 Audacity로 수동 라벨링 → API word timestamp와의 평균 오차(ms) 측정 | 말속도·침묵 계산 신뢰도 |
| 침묵 일치도 | STT gap 기반 침묵 vs webrtcvad 침묵의 IoU 비교 | STT만으로 침묵 평가 가능한지 |
| Diarization | 질문+답변을 이어붙인 wav 생성 → 화자 2명 분리 정확도 확인 | 면접관/지원자 분리 필요 시 |
| 응답속도 | 파일별 latency, RTF 기록 (각 3회 반복, 중앙값) | 서비스 응답성 |

### 10.3 실행 절차

```bash
python scripts/run_benchmark.py          # data/ 전체 × 4 API 실행 → DB 적재
python scripts/build_report.py           # 비교표 마크다운 생성
```

## 11. API 선정 기준

AI 면접 서비스 관점의 가중치 매트릭스 (각 항목 실험 결과를 5점 척도로 환산):

| 기준 | 가중치 | 이유 (면접 서비스 관점) |
|---|---:|---|
| 한국어 정확도 (CER) | 25% | 전사가 틀리면 모든 후속 평가가 무너짐 |
| **Verbatim/간투어 보존** | **20%** | 더듬음·추임새 평가의 성립 조건. 일반 STT 비교에는 없는 면접 특화 기준 |
| Word timestamp 정확도 | 20% | 말속도·침묵·발화비율·억양 정렬의 기반 |
| 비용 | 15% | 면접 1건 ≈ 20~30분 → 볼륨 커지면 지배적 비용 |
| 응답속도 (RTF) | 10% | 배치 분석이라 임계값만 넘으면 됨 |
| 구현·운영 난이도 | 5% | 1회 비용 성격 |
| Diarization | 5% | 지원자 단독 녹음이 기본 시나리오라 낮게 책정 |

**의도적으로 낮춘 것**: 실시간 스트리밍 성능 (면접 답변은 종료 후 배치 분석으로 충분).
**의도적으로 높인 것**: verbatim 보존 (일반 STT 벤치마크는 오히려 간투어 제거를 "좋은 것"으로 평가하지만, 면접 평가에서는 정반대).

## 12. 최종 결론 (실험 후 작성 — 예상 시나리오)

실험 전이므로 결론은 비워두되, 선정 논리가 어떻게 전개될지 시나리오를 명시한다:

**시나리오 A — "Clova를 선택해야 하는 이유"가 되는 경우**
> 한국어 CER 최저 + 간투어 보존 옵션 확인 + segment timestamp 기본 제공 + 시간당 비용 최저 수준.
> → "면접 평가 7개 지표 중 5개를 추가 분석 없이 지원하며, 10,000시간 기준 글로벌 API 대비 약 50% 비용"

**시나리오 B — "Google을 선택해야 하는 이유"가 되는 경우**
> word 단위 confidence의 세밀함 + timestamp 오차 최소 + GCP 인프라 통합(면접 영상도 GCP에 저장하는 경우).
> → "정확도 차이가 CER 1%p 이내라면 word-level confidence 기반 신뢰도 필터링 가치가 비용 차이를 상회"

**시나리오 C — Vito가 다크호스가 되는 경우**
> CER이 Clova와 대등하면서 verbatim 전사가 더 충실한 경우 (통화음성 학습 특성상 간투어 보존에 유리할 가능성).

어느 경우든 결론 문장은 다음 형식으로 작성한다:

> "우리는 **X**를 선택한다. 근거: ① CER {n}%로 {1위/2위} ② 간투어 보존율 {n}% ③ timestamp 평균 오차 {n}ms
> ④ 10,000시간 기준 연 {n}원 ⑤ 미지원 지표(억양, 발음막힘)는 어떤 API를 선택해도 동일하게 별도 분석이 필요하므로 감점 사유가 아님."

## 13. 추가 Python 라이브러리

| 라이브러리 | 역할 | 사용 지표 |
|---|---|---|
| `jiwer` | WER/CER 계산 (편집거리 기반) | STT 정확도 |
| `librosa` | 오디오 로딩, RMS 에너지, 스펙트럼 분석 | 발음 연장 탐지, 에너지 기반 보조 분석 |
| `parselmouth` | Praat 바인딩 — F0(pitch), 포먼트, jitter/shimmer | 억양 분석, 음성 떨림(선택) |
| `webrtcvad` | 경량 VAD (30ms 프레임 단위 발화 판정) | 침묵/발화비율 정밀 측정 |
| `silero-vad` | 딥러닝 VAD (webrtcvad보다 정확, 약간 무거움) | 침묵 측정 대안 (둘 중 하나 선택) |
| `pydub` / `soundfile` | wav 자르기·이어붙이기 | diarization 실험용 합성 데이터 제작 |
| `jamo` (선택) | 한글 자모 분해 | 자모 단위 CER 등 세밀한 오류 분석 |

---

## 부록 A. 데이터셋 스키마 (실측)

`data/label/**/*.json` 구조 (AI Hub 채용면접 인터뷰 데이터):

```
dataSet.info            : occupation(ICT), gender, ageRange, experience
dataSet.question.raw.text : 질문 정답 전사
dataSet.answer.raw.text   : 답변 정답 전사  ← Ground Truth로 사용
rawDataInfo.answer      : duration(ms), samplingRate(16kHz), audioPath
```

wav 파일명 규칙: `ckmk_{q|a}_ict_{f|m}_{n|e}_{id}.wav` (q=질문, a=답변 / f=여성, m=남성 / n=신입, e=경력)

현재 보유: 8개 세트 (여성 신입 2, 여성 경력 2, 남성 신입 2, 남성 경력 2) → 평가 대상 답변 wav 8개.
