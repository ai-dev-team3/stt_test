"""STT 정확도: WER / CER / 문장 정확도.

한국어는 띄어쓰기 변동으로 WER이 과대평가되므로 CER을 1차 지표로 사용한다.
"""

import re

import jiwer

# 한글·영숫자·공백만 남긴다 (문장부호/특수문자 제거)
_NON_TEXT = re.compile(r"[^가-힣a-zA-Z0-9\s]")
_SENT_SPLIT = re.compile(r"[.?!]")


def normalize(text: str) -> str:
    text = _NON_TEXT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def accuracy_metrics(ground_truth: str, hypothesis: str) -> dict:
    ref, hyp = normalize(ground_truth), normalize(hypothesis)
    # CER은 띄어쓰기 자체를 오류로 세지 않도록 공백 제거 후 계산
    cer = jiwer.cer(ref.replace(" ", ""), hyp.replace(" ", "")) if ref else None
    wer = jiwer.wer(ref, hyp) if ref else None

    # 문장 정확도: GT 문장(정규화)이 hypothesis 안에 그대로 존재하는 비율
    ref_sents = [normalize(s) for s in _SENT_SPLIT.split(ground_truth)]
    ref_sents = [s for s in ref_sents if s]
    hyp_flat = hyp.replace(" ", "")
    matched = sum(1 for s in ref_sents if s.replace(" ", "") in hyp_flat)
    sentence_acc = matched / len(ref_sents) if ref_sents else None

    return {"wer": wer, "cer": cer, "sentence_acc": sentence_acc}
