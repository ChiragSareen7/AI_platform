from fastapi import Header, HTTPException, Query


def resolve_tenant_context(
    x_tenant_id: str | None = Header(default=None),
    x_workspace_id: str | None = Header(default=None),
    tenant_id: str | None = Query(default=None),
    workspace_id: str | None = Query(default=None),
) -> tuple[str, str]:
    if not x_tenant_id and tenant_id:
        x_tenant_id = tenant_id
    if not x_workspace_id and workspace_id:
        x_workspace_id = workspace_id
    if not x_tenant_id or not x_workspace_id:
        raise HTTPException(status_code=400, detail="Missing x-tenant-id or x-workspace-id header")
    return x_tenant_id, x_workspace_id

