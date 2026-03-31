from __future__ import annotations

from typing import Any

from app.evaluation.config import EvaluationThresholds
from app.evaluation.embeddings import relevance_query_response, semantic_similarity_pair
from app.evaluation.grounding import chunk_context, groundedness_from_chunks, split_sentences
from app.evaluation.llm_judge import make_judge
from app.evaluation.logging_hooks import emit_eval_event
from app.evaluation.nli import entailment_mean_score

DEFAULT_THRESHOLDS = EvaluationThresholds()


def run_semantic_evaluation(
    query: str,
    response: str,
    *,
    context: str = "",
    ground_truth: str | None = None,
    thresholds: EvaluationThresholds | None = None,
) -> dict[str, Any]:
    t = thresholds or DEFAULT_THRESHOLDS
    emb = t.embedding_model
    q, r = (query or "").strip(), (response or "").strip()
    meta_base = {
        "model_used": emb,
        "embedding_model": emb,
        "thresholds": {
            "grounding_min_sim": t.grounding_min_sim,
            "weights": {
                "groundedness": t.weight_groundedness,
                "relevance": t.weight_relevance,
                "entailment": t.weight_entailment,
            },
        },
        "grounding_skipped": False,
        "nli_enabled": t.enable_nli,
        "llm_judge_used": False,
    }

    if not r:
        out = _empty_semantic(meta_base, emb)
        emit_eval_event("semantic_eval", {"query": q, "empty_response": True})
        return out

    relevance = relevance_query_response(q, r, emb)

    sentences = split_sentences(r)
    if not sentences and r:
        sentences = [r[:2000]]
    chunks = chunk_context(context)
    grounding_skipped = not (context or "").strip()
    unsupported: list[str] = []
    entailment_avg: float | None = None

    if grounding_skipped:
        groundedness = float(relevance)
        meta_base["grounding_skipped"] = True
        hallucination = 0.0
    else:
        g, unsupported = groundedness_from_chunks(sentences, chunks, emb, t.grounding_min_sim)
        groundedness = float(g)
        n_sent = len(sentences) if sentences else 1
        hallucination = len(unsupported) / max(n_sent, 1)

    if t.enable_nli and not grounding_skipped and sentences:
        try:
            ent_avg, nli_lab_list = entailment_mean_score(context, sentences, t.nli_model)
            entailment_avg = ent_avg
            for sent, lab in zip(sentences, nli_lab_list):
                if lab == "contradiction" and sent not in unsupported:
                    unsupported.append(sent)
            if nli_lab_list:
                contrad = sum(1 for x in nli_lab_list if x == "contradiction")
                hallucination = max(hallucination, contrad / len(nli_lab_list))
        except Exception:
            entailment_avg = None

    if ground_truth and (ground_truth or "").strip():
        accuracy = semantic_similarity_pair(r, ground_truth.strip(), emb)
    else:
        accuracy = float(groundedness * relevance)

    wg, wr, we = t.weight_groundedness, t.weight_relevance, t.weight_entailment
    if entailment_avg is not None:
        wsum = wg + wr + we
        confidence = (wg * groundedness + wr * relevance + we * entailment_avg) / wsum
    else:
        wsum = wg + wr
        confidence = (wg * groundedness + wr * relevance) / wsum if wsum else relevance

    confidence = max(0.0, min(1.0, float(confidence)))

    judge_raw: dict[str, Any] | None = None
    if t.enable_llm_judge:
        judge_fn = make_judge(None)
        if judge_fn:
            judge_raw = judge_fn(q, r, context)
            meta_base["llm_judge_used"] = judge_raw is not None
            if judge_raw:
                jc = float(judge_raw.get("correctness", 0.5))
                confidence = max(0.0, min(1.0, 0.5 * confidence + 0.5 * jc))

    result = {
        "relevance": round(float(relevance), 4),
        "groundedness": round(float(groundedness), 4),
        "hallucination": round(float(hallucination), 4),
        "accuracy": round(float(accuracy), 4),
        "confidence": round(float(confidence), 4),
        "unsupported_sentences": unsupported[:50],
        "metadata": {
            **meta_base,
            "entailment_avg": round(entailment_avg, 4) if entailment_avg is not None else None,
            "llm_judge": judge_raw,
        },
    }
    emit_eval_event("semantic_eval", {"query_len": len(q), "response_len": len(r), "result": result})
    return result


def _empty_semantic(meta_base: dict, emb: str) -> dict[str, Any]:
    z = {
        "relevance": 0.0,
        "groundedness": 0.0,
        "hallucination": 1.0,
        "accuracy": 0.0,
        "confidence": 0.0,
        "unsupported_sentences": [],
        "metadata": {**meta_base, "embedding_model": emb},
    }
    return z


def load_thresholds_from_env() -> EvaluationThresholds:
    return EvaluationThresholds()
