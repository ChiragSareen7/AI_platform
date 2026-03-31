from __future__ import annotations

from app.services.learning import get_domain_bias


DOMAIN_PRIMARY = {
    "chemistry": "organic_model",
    "python": "python_model",
    "gita": "gita_model",
    "general": "groq_model",
}

ALL_MODELS = ["organic_model", "python_model", "gita_model", "groq_model"]


def route_models(domain: str) -> dict:
    primary = DOMAIN_PRIMARY.get(domain, "groq_model")
    bias = get_domain_bias(domain)

    ranked = [primary]
    if bias and bias in ALL_MODELS and bias not in ranked:
        ranked.append(bias)

    for model in ALL_MODELS:
        if model not in ranked:
            ranked.append(model)

    return {
        "primary": primary,
        "ranked": ranked,
        "fallbacks": [m for m in ranked if m != primary],
    }
