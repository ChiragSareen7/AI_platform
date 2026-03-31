from __future__ import annotations

from collections import defaultdict

from app.services.query_analyzer import analyze_query
from app.services.model_router import route_models
from app.services.prompt_generator import generate_prompts
from app.services.model_executor import execute_model
from app.services.evaluator import evaluate_response
from app.services.ranker import rank_responses
from app.services.learning import update_learning
from app.services.logger import append_log
from app.utils.similarity import average_pairwise_similarity


def _blue_metrics(responses: list[dict]) -> dict:
    by_model = defaultdict(list)
    for r in responses:
        by_model[r["model"]].append(r)

    all_lat = [r["metrics"]["latency"] for r in responses]
    all_cost = [r["metrics"]["cost"] for r in responses]
    all_err = [r["metrics"]["errorRate"] for r in responses]

    stabilities = []
    for vals in by_model.values():
        texts = [v.get("response", "") for v in vals if v.get("response")]
        if len(texts) >= 2:
            stabilities.append(average_pairwise_similarity(texts))

    behavior_stability = round(sum(stabilities) / len(stabilities), 4) if stabilities else 0.0

    return {
        "behaviorStability": behavior_stability,
        "latency": round(sum(all_lat) / len(all_lat), 2) if all_lat else 0.0,
        "usageCost": round(sum(all_cost), 6),
        "errorRate": round(sum(all_err) / len(all_err), 4) if all_err else 0.0,
    }


def run_query_pipeline(
    query: str,
    context: str | None = None,
    ground_truth: str | None = None,
) -> dict:
    analysis = analyze_query(query)
    routing = route_models(analysis["domain"])
    prompts = generate_prompts(query)

    responses = []
    for model in routing["ranked"]:
        for prompt in prompts:
            raw = execute_model(model, query, prompt["text"])
            metrics = evaluate_response(
                query,
                raw.get("response", ""),
                raw["latency"],
                raw["tokenUsage"],
                raw.get("error"),
                context=context,
                ground_truth=ground_truth,
            )
            responses.append(
                {
                    "model": model,
                    "prompt_version": prompt["version"],
                    "prompt": prompt["text"],
                    "response": raw.get("response", ""),
                    "error": raw.get("error"),
                    "metrics": metrics,
                }
            )

    ranked = rank_responses(responses)
    best = ranked[0]
    all_failed = all((r.get("error") is not None) for r in responses)

    if all_failed:
        errors = []
        for r in responses:
            err = r.get("error")
            if err and err not in errors:
                errors.append(err)
        best_answer = "All model calls failed. Check model server/Groq credentials."
    else:
        errors = []
        best_answer = best["response"]

    update_learning(analysis["domain"], best["model"], best["metrics"])

    blue = _blue_metrics(responses)

    log_entry = {
        "query": query,
        "analysis": analysis,
        "responses": responses,
        "best_model": best["model"],
        "best_prompt": best["prompt_version"],
        "best_response": best_answer,
        "metrics": best["metrics"],
        "blue_metrics": blue,
        "errors": errors,
    }
    append_log(log_entry)

    return {
        "best_answer": best_answer,
        "best_model": best["model"],
        "best_prompt": best["prompt_version"],
        "metrics": best["metrics"],
        "blue_metrics": blue,
        "analysis": analysis,
        "errors": errors,
        "all_responses": ranked,
    }
