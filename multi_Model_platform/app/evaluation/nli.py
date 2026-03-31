from __future__ import annotations

from typing import Literal

import numpy as np

_ce = None
_ce_name: str | None = None

Label = Literal["entailment", "neutral", "contradiction"]


def _get_cross_encoder(model_name: str):
    global _ce, _ce_name
    if _ce is None or _ce_name != model_name:
        from sentence_transformers import CrossEncoder

        _ce = CrossEncoder(model_name, device="cpu", max_length=256)
        _ce_name = model_name
    return _ce


def _normalize_label(s: str) -> Label:
    s = (s or "").lower()
    if "entail" in s:
        return "entailment"
    if "contradict" in s:
        return "contradiction"
    return "neutral"


def entailment_label(premise: str, hypothesis: str, model_name: str) -> tuple[Label, float]:
    premise, hypothesis = premise.strip(), hypothesis.strip()
    if not premise or not hypothesis:
        return "neutral", 1 / 3

    model = _get_cross_encoder(model_name)
    raw = model.predict([(premise, hypothesis)], show_progress_bar=False)
    logits = np.asarray(raw[0] if isinstance(raw, (list, tuple)) else raw).flatten()
    exp = np.exp(logits - np.max(logits))
    probs = exp / (np.sum(exp) + 1e-12)
    idx = int(np.argmax(probs))
    conf = float(probs[idx])

    cfg = getattr(model.model, "config", None)
    id2label = getattr(cfg, "id2label", None) if cfg is not None else None
    if isinstance(id2label, dict) and idx in id2label:
        lab = _normalize_label(str(id2label[idx]))
    else:
        order = ["contradiction", "entailment", "neutral"]
        lab = order[idx] if idx < len(order) else "neutral"
    return lab, conf


def entailment_mean_score(
    context: str,
    sentences: list[str],
    model_name: str,
) -> tuple[float, list[Label]]:
    if not (context or "").strip() or not sentences:
        return 0.5, []
    premise = context[:4000]
    scores: list[float] = []
    labels: list[Label] = []
    for sent in sentences:
        lab, p = entailment_label(premise, sent, model_name)
        labels.append(lab)
        if lab == "entailment":
            scores.append(1.0)
        elif lab == "contradiction":
            scores.append(0.0)
        else:
            scores.append(0.5)
    mean_s = float(sum(scores) / len(scores)) if scores else 0.5
    return mean_s, labels
