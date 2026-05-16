from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class QueryTraceEnvelope:
    query_id: str
    tenant_id: str
    workspace_id: str
    timestamp_in: datetime


def new_trace(query_id: str, tenant_id: str, workspace_id: str) -> QueryTraceEnvelope:
    return QueryTraceEnvelope(
        query_id=query_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        timestamp_in=datetime.now(timezone.utc),
    )

