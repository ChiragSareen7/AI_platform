import asyncio
import uuid

from governance.db import SessionLocal, engine
from governance.models.base import Base
from governance.repository import create_policy_rule, create_tenant, create_workspace, list_tenants, list_workspaces
from governance.tenant_service import api_key_prefix, hash_api_key


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        tenants = await list_tenants(db)
        if tenants:
            tenant = tenants[0]
        else:
            raw_key = "nx_live_demo_1234567890"
            tenant = await create_tenant(
                db,
                name="Demo Tenant",
                plan="starter",
                api_key_hash=hash_api_key(raw_key),
                api_key_prefix=api_key_prefix(raw_key),
            )

        workspaces = await list_workspaces(db, tenant_id=str(tenant.id))
        if workspaces:
            ws = workspaces[0]
        else:
            ws = await create_workspace(
                db,
                tenant_id=str(tenant.id),
                name="Production",
                enabled_models=["python", "organic", "gita", "general"],
                knowledge_base_path="",
                config={"execution_mode": "combined"},
            )
            await create_policy_rule(
                db,
                workspace_id=str(ws.id),
                metric="hallucination",
                operator="gt",
                threshold=0.40,
                action="BLOCK",
                priority=10,
                is_active=True,
                description="Block high hallucination",
            )

    print("Seed complete.")
    print("tenant_id:", tenant.id)
    print("workspace_id:", ws.id)


if __name__ == "__main__":
    asyncio.run(seed())

