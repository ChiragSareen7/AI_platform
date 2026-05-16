import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url

from gateway.auth import verify_jwt
from gateway.query_trace import new_trace
from gateway.rate_limiter import enforce_rate_limit
from gateway.schemas import QueryRequest, QueryResponse
from gateway.tenant_resolver import resolve_tenant_context
from governance.policy_engine import evaluate_policies
from governance.db import SessionLocal
from governance.repository import (
    create_audit_log,
    create_policy_rule,
    create_query_trace,
    list_policy_rules,
    list_query_traces,
)
from shared.events import publish_event
from shared.config import settings
from shared.constants import PolicyDecision
from shared.query_id import new_query_id
from shared.score_card import ScoreCard

router = APIRouter(prefix="/api/v1")


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_json_response(resp: httpx.Response, name: str) -> dict:
    if resp.status_code >= 500:
        return {}
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"{name} returned non-JSON response") from exc


def _recompute_score_card(mm: dict, det: dict, plat: dict) -> ScoreCard:
    mm_metrics = mm.get("metrics", {}) if isinstance(mm, dict) else {}
    mm_sem = mm_metrics.get("semantic", {}) if isinstance(mm_metrics, dict) else {}
    det_h = _safe_float(det.get("hallucinationScore"))
    det_s = _safe_float(det.get("similarityScore"))
    plat_ai = (plat.get("metrics", {}) or {}).get("aiQuality", {}) if isinstance(plat, dict) else {}

    hallucination = max(_safe_float(mm_sem.get("hallucination")), det_h)
    relevance = max(_safe_float(mm_sem.get("relevance")), _safe_float(plat_ai.get("relevanceScore")))
    groundedness = max(_safe_float(mm_sem.get("groundedness")), det_s)
    confidence = _safe_float(mm_sem.get("confidence"), _safe_float(mm_metrics.get("confidenceScore")))
    accuracy = max(_safe_float(mm_sem.get("accuracy")), _safe_float(mm_metrics.get("accuracyScore")), _safe_float(plat_ai.get("accuracyScore")))
    lexical = _safe_float(mm_metrics.get("accuracyScore"))
    semantic = _safe_float(mm_sem.get("accuracy"))
    latency_ms = int(max(_safe_float(mm_metrics.get("latency")), _safe_float(det.get("latency_ms")), _safe_float((plat.get("metrics", {}) or {}).get("system", {}).get("latency", 0))))
    tokens = int(_safe_float(mm_metrics.get("tokenUsage"), 0))

    latency_penalty = min(1.0, latency_ms / 60000.0)
    overall = (
        settings.nexus_score_w_accuracy * accuracy
        + settings.nexus_score_w_relevance * relevance
        + settings.nexus_score_w_groundedness * groundedness
        + settings.nexus_score_w_confidence * confidence
        + settings.nexus_score_w_hallucination * (1.0 - hallucination)
        + settings.nexus_score_w_latency * (1.0 - latency_penalty)
    )
    return ScoreCard(
        accuracy=round(accuracy, 4),
        hallucination=round(hallucination, 4),
        relevance=round(relevance, 4),
        groundedness=round(groundedness, 4),
        confidence=round(confidence, 4),
        lexical=round(lexical, 4),
        semantic=round(semantic, 4),
        latency_ms=latency_ms,
        tokens=tokens,
        overall=round(max(0.0, min(1.0, overall)), 4),
    )


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "nexus-gateway"}


@router.get("/metrics")
async def metrics(tenant_ctx: tuple[str, str] = Depends(resolve_tenant_context)) -> dict:
    tenant_id, _workspace_id = tenant_ctx
    async with SessionLocal() as db:
        traces = await list_query_traces(db, limit=200)
    traces = [t for t in traces if str(t.tenant_id) == tenant_id]
    if not traces:
        return {"count": 0, "avg_overall": 0.0, "avg_latency_ms": 0.0, "decision_breakdown": {}}
    count = len(traces)
    avg_overall = round(sum(t.score_overall for t in traces) / count, 4)
    avg_latency = round(sum(t.latency_ms for t in traces) / count, 2)
    breakdown: dict[str, int] = {}
    for t in traces:
        breakdown[t.policy_decision] = breakdown.get(t.policy_decision, 0) + 1
    return {
        "count": count,
        "avg_overall": avg_overall,
        "avg_latency_ms": avg_latency,
        "decision_breakdown": breakdown,
    }


@router.get("/stream")
async def stream(
    tenant_ctx: tuple[str, str] = Depends(resolve_tenant_context),
):
    tenant_id, _workspace_id = tenant_ctx

    async def event_gen():
        redis = redis_from_url(settings.redis_url, decode_responses=True)
        pubsub = redis.pubsub()
        channel = f"nexus:tenant:{tenant_id}:queries"
        await pubsub.subscribe(channel)
        try:
            yield "event: hello\ndata: connected\n\n"
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if msg and msg.get("data"):
                    yield f"event: query\ndata: {msg['data']}\n\n"
                else:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await redis.close()

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/query", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    request: Request,
    _operator: str = Depends(verify_jwt),
    tenant_ctx: tuple[str, str] = Depends(resolve_tenant_context),
):
    tenant_id, workspace_id = tenant_ctx
    redis: Redis | None = getattr(request.app.state, "redis", None)
    if redis is None:
        redis = redis_from_url(settings.redis_url, decode_responses=True)
        request.app.state.redis = redis
    await enforce_rate_limit(redis, tenant_id)

    qid = new_query_id()
    _trace = new_trace(qid, tenant_id, workspace_id)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            t0 = time.time()
            mm_resp = await client.post(f"{settings.multi_model_base}/query", json={"query": body.query})
            det_resp = await client.post(f"{settings.deterministic_base}/deterministic-query", json={"query": body.query})
            plat_resp = await client.post(f"{settings.platform_base}/query", json={"query": body.query})
            elapsed = int((time.time() - t0) * 1000)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream services unreachable: {exc.__class__.__name__}") from exc

    if mm_resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"multi_model failed: {mm_resp.text[:200]}")
    mm_data = _safe_json_response(mm_resp, "multi_model")
    det_data = _safe_json_response(det_resp, "deterministic")
    plat_data = _safe_json_response(plat_resp, "platform")

    score = _recompute_score_card(mm_data, det_data, plat_data)

    async with SessionLocal() as db:
        rules_db = await list_policy_rules(db, workspace_id=workspace_id)
        if not rules_db:
            # bootstrap default rules once
            await create_policy_rule(
                db,
                workspace_id=workspace_id,
                metric="hallucination",
                operator="gt",
                threshold=0.40,
                action="BLOCK",
                priority=10,
                is_active=True,
                description="Block high hallucination",
            )
            await create_policy_rule(
                db,
                workspace_id=workspace_id,
                metric="latency_ms",
                operator="gt",
                threshold=45000,
                action="ESCALATE",
                priority=20,
                is_active=True,
                description="Escalate high latency",
            )
            await create_policy_rule(
                db,
                workspace_id=workspace_id,
                metric="relevance",
                operator="lt",
                threshold=0.45,
                action="RETRY",
                priority=30,
                is_active=True,
                description="Retry low relevance",
            )
            rules_db = await list_policy_rules(db, workspace_id=workspace_id)

        rules = [
            {
                "metric": r.metric,
                "operator": r.operator,
                "threshold": r.threshold,
                "action": r.action,
                "priority": r.priority,
                "description": r.description,
                "is_active": r.is_active,
            }
            for r in rules_db
        ]

    decision, triggered = evaluate_policies(score, rules, retry_count=0)
    final_answer = mm_data.get("best_answer", "")
    if decision == PolicyDecision.ESCALATE:
        final_answer = f"{final_answer}\n\n[Escalation Notice] Flagged for operator review."
    if decision == PolicyDecision.BLOCK:
        final_answer = "Response blocked by governance policy due to quality/safety constraints."

    async with SessionLocal() as db:
        trace = await create_query_trace(
            db,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            raw_query=body.query,
            domain_detected=mm_data.get("analysis", {}).get("domain", "general"),
            model_selected=mm_data.get("best_model", "unknown"),
            prompt_version=mm_data.get("best_prompt", "v1"),
            routing_reason="Combined orchestration over multi_model + deterministic + platform",
            raw_answer=mm_data.get("best_answer", ""),
            context_chunks=det_data.get("contextChunks", []),
            latency_ms=score.latency_ms,
            score_hallucination=score.hallucination,
            score_relevance=score.relevance,
            score_groundedness=score.groundedness,
            score_confidence=score.confidence,
            score_lexical=score.lexical,
            score_semantic=score.semantic,
            score_overall=score.overall,
            policy_decision=decision.value,
            policy_rule_triggered=triggered or "",
            retry_count=0,
            final_answer=final_answer,
        )
        await create_audit_log(
            db,
            query_trace_id=str(trace.id),
            event_type="policy_decision",
            payload={
                "query_id": qid,
                "decision": decision.value,
                "triggered_rule": triggered,
                "score": score.__dict__,
            },
        )

    await publish_event(
        redis,
        channel=f"nexus:tenant:{tenant_id}:queries",
        payload={
            "query_id": qid,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "query": body.query,
            "decision": decision.value,
            "model": mm_data.get("best_model", "unknown"),
            "score_overall": score.overall,
            "latency_ms": score.latency_ms,
        },
    )

    return QueryResponse(
        query_id=qid,
        policy_decision=decision.value,
        model_selected=mm_data.get("best_model", "unknown"),
        final_answer=final_answer,
        score_overall=score.overall,
        score_card=score.__dict__ | {"elapsed_ms": elapsed},
        triggered_rule=triggered,
    )

