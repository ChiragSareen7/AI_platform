import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class QueryTrace(Base):
    __tablename__ = "query_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    domain_detected: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    timestamp_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    model_selected: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    routing_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    raw_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    context_chunks: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    score_hallucination: Mapped[float] = mapped_column(nullable=False, default=0.0)
    score_relevance: Mapped[float] = mapped_column(nullable=False, default=0.0)
    score_groundedness: Mapped[float] = mapped_column(nullable=False, default=0.0)
    score_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    score_lexical: Mapped[float] = mapped_column(nullable=False, default=0.0)
    score_semantic: Mapped[float] = mapped_column(nullable=False, default=0.0)
    score_overall: Mapped[float] = mapped_column(nullable=False, default=0.0)

    policy_decision: Mapped[str] = mapped_column(String(16), nullable=False, default="DELIVER")
    policy_rule_triggered: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")

    timestamp_out: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    operator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("query_traces.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

