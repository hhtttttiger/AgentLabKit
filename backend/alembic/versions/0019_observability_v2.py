"""Replace legacy event-derived traces with OpenTelemetry trace storage.

Revision ID: 0019
Revises: 0018
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("trace_spans")
    op.drop_table("trace_records")

    op.create_table(
        "trace_records",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("trace_id", sa.String(32), nullable=False, unique=True),
        sa.Column("root_span_id", sa.String(16), nullable=False),
        sa.Column("run_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("agent_key", sa.String(128)),
        sa.Column("session_id", sa.String(128)),
        sa.Column("user_id", sa.String(128)),
        sa.Column("correlation_id", sa.String(128)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("total_duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("total_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_write_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_estimated_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("span_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dropped_span_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_reason", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("attributes_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('ok','error','timeout','cancelled')", name="ck_trace_status"),
    )
    op.create_index(
        "ix_trace_records_started_cursor",
        "trace_records",
        [sa.text("started_at_utc DESC"), sa.text("trace_id DESC")],
    )
    op.create_index("ix_trace_records_agent_time", "trace_records", ["agent_key", sa.text("started_at_utc DESC")])
    op.create_index("ix_trace_records_session_time", "trace_records", ["session_id", sa.text("started_at_utc DESC")])
    op.create_index("ix_trace_records_status_time", "trace_records", ["status", sa.text("started_at_utc DESC")])

    op.create_table(
        "trace_spans",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("span_id", sa.String(16), nullable=False, unique=True),
        sa.Column(
            "trace_id",
            sa.String(32),
            sa.ForeignKey("trace_records.trace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("parent_span_id", sa.String(16)),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("span_kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("instrumentation_scope", sa.String(256), nullable=False, server_default=""),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("attributes_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("events_json", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("links_json", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("error_code", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('ok','error','timeout','cancelled')", name="ck_trace_span_status"),
    )
    op.create_index(
        "ix_trace_spans_trace_time",
        "trace_spans",
        ["trace_id", "started_at_utc", "span_id"],
    )


def downgrade() -> None:
    op.drop_table("trace_spans")
    op.drop_table("trace_records")

    op.create_table(
        "trace_records",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("trace_id", sa.String(64), nullable=False, unique=True),
        sa.Column("root_span_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("agent_key", sa.String(128)),
        sa.Column("session_id", sa.String(128)),
        sa.Column("status", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("total_duration_ms", sa.BigInteger()),
        sa.Column("total_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_estimated_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("span_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at_utc", sa.DateTime(timezone=True)),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "trace_spans",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("span_id", sa.String(64), nullable=False, unique=True),
        sa.Column("parent_span_id", sa.String(64)),
        sa.Column("span_kind", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("started_at_utc", sa.DateTime(timezone=True)),
        sa.Column("completed_at_utc", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.BigInteger()),
        sa.Column("attributes_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
