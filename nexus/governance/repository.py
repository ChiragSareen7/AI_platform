import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from governance.models.audit import AuditLog, QueryTrace
from governance.models.policy import PolicyRule
from governance.models.tenant import Tenant, Workspace


async def create_tenant(
    db: AsyncSession,
    *,
    name: str,
    plan: str,
    api_key_hash: str,
    api_key_prefix: str,
) -> Tenant:
    obj = Tenant(name=name, plan=plan, api_key=api_key_hash, api_key_prefix=api_key_prefix, is_active=True)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_tenants(db: AsyncSession) -> list[Tenant]:
    res = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return list(res.scalars().all())


async def create_workspace(
    db: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    enabled_models: list[str],
    knowledge_base_path: str,
    config: dict,
) -> Workspace:
    obj = Workspace(
        tenant_id=uuid.UUID(tenant_id),
        name=name,
        enabled_models=enabled_models,
        knowledge_base_path=knowledge_base_path,
        config=config,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_workspaces(db: AsyncSession, tenant_id: str | None = None) -> list[Workspace]:
    stmt = select(Workspace)
    if tenant_id:
        stmt = stmt.where(Workspace.tenant_id == uuid.UUID(tenant_id))
    res = await db.execute(stmt.order_by(Workspace.name.asc()))
    return list(res.scalars().all())


async def create_policy_rule(
    db: AsyncSession,
    *,
    workspace_id: str,
    metric: str,
    operator: str,
    threshold: float,
    action: str,
    priority: int,
    is_active: bool,
    description: str,
) -> PolicyRule:
    obj = PolicyRule(
        workspace_id=uuid.UUID(workspace_id),
        metric=metric,
        operator=operator,
        threshold=threshold,
        action=action,
        priority=priority,
        is_active=is_active,
        description=description,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_policy_rules(db: AsyncSession, workspace_id: str) -> list[PolicyRule]:
    res = await db.execute(
        select(PolicyRule).where(PolicyRule.workspace_id == uuid.UUID(workspace_id)).order_by(PolicyRule.priority.asc())
    )
    return list(res.scalars().all())


async def create_query_trace(db: AsyncSession, **kwargs) -> QueryTrace:
    if "tenant_id" in kwargs and isinstance(kwargs["tenant_id"], str):
        kwargs["tenant_id"] = uuid.UUID(kwargs["tenant_id"])
    if "workspace_id" in kwargs and isinstance(kwargs["workspace_id"], str):
        kwargs["workspace_id"] = uuid.UUID(kwargs["workspace_id"])
    obj = QueryTrace(**kwargs)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_query_traces(db: AsyncSession, limit: int = 100) -> list[QueryTrace]:
    res = await db.execute(select(QueryTrace).order_by(QueryTrace.timestamp_in.desc()).limit(limit))
    return list(res.scalars().all())


async def create_audit_log(db: AsyncSession, query_trace_id: str, event_type: str, payload: dict) -> AuditLog:
    obj = AuditLog(query_trace_id=uuid.UUID(query_trace_id), event_type=event_type, payload=payload)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

