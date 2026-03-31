from __future__ import annotations

import os
from dataclasses import dataclass, field


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _b(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


@dataclass
class EvaluationThresholds:
    grounding_min_sim: float = field(default_factory=lambda: _f("EVAL_GROUNDING_MIN_SIM", 0.75))
    weight_groundedness: float = field(default_factory=lambda: _f("EVAL_W_GROUNDEDNESS", 0.35))
    weight_relevance: float = field(default_factory=lambda: _f("EVAL_W_RELEVANCE", 0.35))
    weight_entailment: float = field(default_factory=lambda: _f("EVAL_W_ENTAILMENT", 0.30))
    enable_nli: bool = field(default_factory=lambda: _b("EVAL_ENABLE_NLI", False))
    enable_llm_judge: bool = field(default_factory=lambda: _b("EVAL_ENABLE_LLM_JUDGE", False))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EVAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    nli_model: str = field(
        default_factory=lambda: os.getenv("EVAL_NLI_MODEL", "cross-encoder/nli-MiniLM-L6-H-6")
    )
