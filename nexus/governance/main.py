from fastapi import Depends, FastAPI, Query
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from governance.db import engine, get_db
from governance.models.base import Base
from governance.repository import (
    create_policy_rule,
    create_tenant,
    create_workspace,
    list_policy_rules,
    list_query_traces,
    list_tenants,
    list_workspaces,
)
from governance.schemas import (
    PolicyRuleCreate,
    PolicyRuleOut,
    TenantCreate,
    TenantOut,
    WorkspaceCreate,
    WorkspaceOut,
)
from governance.tenant_service import api_key_prefix, hash_api_key
from governance.threshold_manager import DEFAULT_THRESHOLDS

app = FastAPI(title="Nexus Governance", version="1.0.0")


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(_request, _exc):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.exception_handler(Exception)
async def generic_error_handler(_request, _exc):
    return JSONResponse(status_code=503, content={"detail": "Service dependency unavailable"})


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"ok": True, "service": "nexus-governance"}


@app.get("/api/v1/thresholds")
async def thresholds() -> dict:
    return {"thresholds": DEFAULT_THRESHOLDS}


@app.post("/api/v1/tenants", response_model=TenantOut)
async def tenants_create(body: TenantCreate, db: AsyncSession = Depends(get_db)) -> TenantOut:
    obj = await create_tenant(
        db,
        name=body.name,
        plan=body.plan,
        api_key_hash=hash_api_key(body.api_key),
        api_key_prefix=api_key_prefix(body.api_key),
    )
    return TenantOut(
        id=str(obj.id),
        name=obj.name,
        plan=obj.plan,
        api_key_prefix=obj.api_key_prefix,
        is_active=obj.is_active,
    )


@app.get("/api/v1/tenants", response_model=list[TenantOut])
async def tenants_list(db: AsyncSession = Depends(get_db)) -> list[TenantOut]:
    rows = await list_tenants(db)
    return [
        TenantOut(
            id=str(x.id),
            name=x.name,
            plan=x.plan,
            api_key_prefix=x.api_key_prefix,
            is_active=x.is_active,
        )
        for x in rows
    ]


@app.post("/api/v1/workspaces", response_model=WorkspaceOut)
async def workspaces_create(body: WorkspaceCreate, db: AsyncSession = Depends(get_db)) -> WorkspaceOut:
    obj = await create_workspace(
        db,
        tenant_id=body.tenant_id,
        name=body.name,
        enabled_models=body.enabled_models,
        knowledge_base_path=body.knowledge_base_path,
        config=body.config,
    )
    return WorkspaceOut(
        id=str(obj.id),
        tenant_id=str(obj.tenant_id),
        name=obj.name,
        enabled_models=list(obj.enabled_models or []),
        knowledge_base_path=obj.knowledge_base_path,
        config=dict(obj.config or {}),
    )


@app.get("/api/v1/workspaces", response_model=list[WorkspaceOut])
async def workspaces_list(tenant_id: str | None = Query(default=None), db: AsyncSession = Depends(get_db)) -> list[WorkspaceOut]:
    rows = await list_workspaces(db, tenant_id=tenant_id)
    return [
        WorkspaceOut(
            id=str(x.id),
            tenant_id=str(x.tenant_id),
            name=x.name,
            enabled_models=list(x.enabled_models or []),
            knowledge_base_path=x.knowledge_base_path,
            config=dict(x.config or {}),
        )
        for x in rows
    ]


@app.post("/api/v1/policy-rules", response_model=PolicyRuleOut)
async def policy_rules_create(body: PolicyRuleCreate, db: AsyncSession = Depends(get_db)) -> PolicyRuleOut:
    obj = await create_policy_rule(
        db,
        workspace_id=body.workspace_id,
        metric=body.metric,
        operator=body.operator,
        threshold=body.threshold,
        action=body.action,
        priority=body.priority,
        is_active=body.is_active,
        description=body.description if not body.dsl else f"{body.description} | {body.dsl}",
    )
    return PolicyRuleOut(
        id=str(obj.id),
        workspace_id=str(obj.workspace_id),
        metric=obj.metric,
        operator=obj.operator,
        threshold=obj.threshold,
        action=obj.action,
        priority=obj.priority,
        is_active=obj.is_active,
        description=obj.description,
    )


@app.get("/api/v1/policy-rules", response_model=list[PolicyRuleOut])
async def policy_rules_list(workspace_id: str = Query(...), db: AsyncSession = Depends(get_db)) -> list[PolicyRuleOut]:
    rows = await list_policy_rules(db, workspace_id=workspace_id)
    return [
        PolicyRuleOut(
            id=str(x.id),
            workspace_id=str(x.workspace_id),
            metric=x.metric,
            operator=x.operator,
            threshold=x.threshold,
            action=x.action,
            priority=x.priority,
            is_active=x.is_active,
            description=x.description,
        )
        for x in rows
    ]


@app.get("/api/v1/query-traces")
async def query_traces_list(limit: int = Query(default=100, ge=1, le=500), db: AsyncSession = Depends(get_db)) -> dict:
    rows = await list_query_traces(db, limit=limit)
    return {
        "items": [
            {
                "id": str(x.id),
                "tenant_id": str(x.tenant_id),
                "workspace_id": str(x.workspace_id),
                "raw_query": x.raw_query,
                "model_selected": x.model_selected,
                "policy_decision": x.policy_decision,
                "score_overall": x.score_overall,
                "score_hallucination": x.score_hallucination,
                "score_relevance": x.score_relevance,
                "score_groundedness": x.score_groundedness,
                "latency_ms": x.latency_ms,
                "timestamp_in": x.timestamp_in.isoformat() if x.timestamp_in else None,
                "timestamp_out": x.timestamp_out.isoformat() if x.timestamp_out else None,
            }
            for x in rows
        ]
    }

