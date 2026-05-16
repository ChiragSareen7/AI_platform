from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    workspace_id: str


class QueryResponse(BaseModel):
    query_id: str
    policy_decision: str
    model_selected: str
    final_answer: str
    score_overall: float
    score_card: dict
    triggered_rule: str | None = None

