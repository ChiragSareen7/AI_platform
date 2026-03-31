from __future__ import annotations

import re


DOMAIN_KEYWORDS = {
    "chemistry": {"compound", "molecule", "organic", "benzene", "ethanol", "acetone", "boiling", "melting", "toxicity", "solubility", "ph"},
    "python": {"python", "list", "tuple", "dict", "function", "class", "loop", "decorator", "pandas", "numpy"},
    "gita": {"gita", "krishna", "arjuna", "dharma", "karma", "chapter", "verse", "bhagavad"},
}


def analyze_query(query: str) -> dict:
    q = query.lower().strip()
    words = set(re.findall(r"[a-zA-Z0-9]+", q))

    domain_scores = {d: len(words & kws) for d, kws in DOMAIN_KEYWORDS.items()}
    best_domain = max(domain_scores, key=domain_scores.get)
    domain = best_domain if domain_scores[best_domain] > 0 else "general"

    length = len(words)
    if length <= 8:
        complexity = "low"
    elif length <= 18:
        complexity = "medium"
    else:
        complexity = "high"

    intent = "explanation" if any(k in words for k in {"why", "how", "explain"}) else "fact_lookup"

    return {
        "domain": domain,
        "complexity": complexity,
        "intent": intent,
        "domain_scores": domain_scores,
    }
