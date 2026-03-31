from __future__ import annotations

import os


def _use_semantic_ranking() -> bool:
    return os.getenv("USE_SEMANTIC_RANKING", "true").lower() in ("1", "true", "yes")


def _semantic_sort_key(r: dict) -> tuple:
    m = r.get("metrics") or {}
    s = m.get("semantic")
    if s and isinstance(s, dict) and "accuracy" in s:
        return (
            -float(s.get("accuracy", 0.0)),
            float(s.get("hallucination", 1.0)),
            float(m.get("latency", 0.0)),
            -float(s.get("confidence", 0.0)),
        )
    return (
        -float(m.get("accuracyScore", 0.0)),
        float(m.get("hallucinationScore", 1.0)),
        float(m.get("latency", 0.0)),
        -float(m.get("confidenceScore", 0.0)),
    )


def _lexical_sort_key(r: dict) -> tuple:
    m = r.get("metrics") or {}
    return (
        -m["accuracyScore"],
        m["hallucinationScore"],
        m["latency"],
        -m["confidenceScore"],
    )


def rank_responses(responses: list[dict]) -> list[dict]:
    key = _semantic_sort_key if _use_semantic_ranking() else _lexical_sort_key
    return sorted(responses, key=key)
