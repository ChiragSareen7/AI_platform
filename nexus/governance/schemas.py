from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str
    plan: str = "starter"
    api_key: str = Field(..., min_length=16)


class TenantOut(BaseModel):
    id: str
    name: str
    plan: str
    api_key_prefix: str
    is_active: bool


class WorkspaceCreate(BaseModel):
    tenant_id: str
    name: str
    enabled_models: list[str] = Field(default_factory=lambda: ["python", "organic", "gita", "general"])
    knowledge_base_path: str = ""
    config: dict = Field(default_factory=dict)


class WorkspaceOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    enabled_models: list[str]
    knowledge_base_path: str
    config: dict


class PolicyRuleCreate(BaseModel):
    workspace_id: str
    metric: str
    operator: str
    threshold: float
    action: str
    priority: int = 100
    is_active: bool = True
    description: str
    dsl: str | None = None


class PolicyRuleOut(BaseModel):
    id: str
    workspace_id: str
    metric: str
    operator: str
    threshold: float
    action: str
    priority: int
    is_active: bool
    description: str

