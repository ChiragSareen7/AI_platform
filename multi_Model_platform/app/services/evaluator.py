from __future__ import annotations

import os
import traceback

from app.utils.similarity import jaccard_similarity, keyword_overlap


def _legacy_lexical_metrics(query: str, response: str, latency: float, token_usage: int) -> dict:
    relevance = keyword_overlap(query, response)
    lexical = jaccard_similarity(query, response)
    accuracy = min(1.0, (0.65 * relevance) + (0.35 * lexical))

    low_quality_markers = ["i don't know", "uncertain", "not sure", "cannot determine"]
    has_marker = any(m in response.lower() for m in low_quality_markers)
    hallucination = max(0.0, 1.0 - accuracy + (0.1 if has_marker else 0.0))

    confidence = max(0.0, min(1.0, accuracy - (latency / 40000.0) - (0.15 if has_marker else 0.0)))
    toxicity = 0.0

    return {
        "accuracyScore": round(accuracy, 4),
        "relevanceScore": round(relevance, 4),
        "hallucinationScore": round(hallucination, 4),
        "confidenceScore": round(confidence, 4),
        "latency": latency,
        "tokenUsage": token_usage,
        "cost": round(token_usage * 0.000002, 6),
        "toxicityScore": toxicity,
        "errorRate": 0.0,
    }


def evaluate_response(
    query: str,
    response: str,
    latency: float,
    token_usage: int,
    error: str | None,
    *,
    context: str | None = None,
    ground_truth: str | None = None,
) -> dict:
    if error:
        return {
            "accuracyScore": 0.0,
            "relevanceScore": 0.0,
            "hallucinationScore": 1.0,
            "confidenceScore": 0.0,
            "latency": latency,
            "tokenUsage": token_usage,
            "cost": round(token_usage * 0.000002, 6),
            "toxicityScore": 0.0,
            "errorRate": 1.0,
            "semantic": None,
        }

    legacy = _legacy_lexical_metrics(query, response, latency, token_usage)

    semantic: dict | None = None
    if os.getenv("EVAL_ENABLE_SEMANTIC", "true").lower() in ("1", "true", "yes"):
        try:
            from app.evaluation.pipeline import load_thresholds_from_env, run_semantic_evaluation

            semantic = run_semantic_evaluation(
                query,
                response,
                context=context or "",
                ground_truth=ground_truth,
                thresholds=load_thresholds_from_env(),
            )
        except Exception:
            semantic = {
                "relevance": 0.0,
                "groundedness": 0.0,
                "hallucination": 1.0,
                "accuracy": 0.0,
                "confidence": 0.0,
                "unsupported_sentences": [],
                "metadata": {
                    "error": traceback.format_exc()[:800],
                    "embedding_model": os.getenv("EVAL_EMBEDDING_MODEL", ""),
                    "model_used": "error",
                },
            }
    else:
        semantic = None

    return {**legacy, "semantic": semantic}
