from __future__ import annotations

import itertools
import re


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", (text or "").lower()))


def jaccard_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def keyword_overlap(query: str, response: str) -> float:
    q, r = _tokens(query), _tokens(response)
    if not q:
        return 0.0
    return len(q & r) / len(q)


def average_pairwise_similarity(texts: list[str]) -> float:
    if len(texts) < 2:
        return 1.0
    sims = [jaccard_similarity(a, b) for a, b in itertools.combinations(texts, 2)]
    return sum(sims) / len(sims) if sims else 1.0
