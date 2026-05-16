"""initial tables

Revision ID: 0001_initial
Revises: 
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("api_key_prefix", sa.String(length=32), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled_models", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("knowledge_base_path", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "policy_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=8), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.String(length=512), nullable=False),
    )

    op.create_table(
        "query_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("raw_query", sa.Text(), nullable=False),
        sa.Column("domain_detected", sa.String(length=64), nullable=False),
        sa.Column("timestamp_in", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("model_selected", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("routing_reason", sa.Text(), nullable=False),
        sa.Column("raw_answer", sa.Text(), nullable=False),
        sa.Column("context_chunks", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_hallucination", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_relevance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_groundedness", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_lexical", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_semantic", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_overall", sa.Float(), nullable=False, server_default="0"),
        sa.Column("policy_decision", sa.String(length=16), nullable=False),
        sa.Column("policy_rule_triggered", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_answer", sa.Text(), nullable=False),
        sa.Column("timestamp_out", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("operator_notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("query_trace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("query_traces.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("query_traces")
    op.drop_table("policy_rules")
    op.drop_table("workspaces")
    op.drop_table("tenants")

