"""Add the durable Runtime Run projection.

Revision ID: 0020
Revises: 0019
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_records",
        sa.Column("run_id", sa.String(128), primary_key=True),
        sa.Column("trace_id", sa.String(128)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("target_type", sa.String(32)),
        sa.Column("target_key", sa.String(256)),
        sa.Column("target_version", sa.String(128)),
        sa.Column("input_json", JSONB()),
        sa.Column("output_json", JSONB()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("session_id", sa.String(256)),
        sa.Column("error_code", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("metadata_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("projected_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("projection_version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("status IN ('running','completed','failed','cancelled')", name="ck_run_records_status"),
    )
    op.create_index("ix_run_records_trace_id", "run_records", ["trace_id"])
    op.create_index("ix_run_records_status", "run_records", ["status"])
    op.create_index("ix_run_records_started_at", "run_records", ["started_at"])

    op.create_table(
        "run_projection_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("run_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_run_projection_events_run_id", "run_projection_events", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_projection_events_run_id", table_name="run_projection_events")
    op.drop_table("run_projection_events")
    op.drop_index("ix_run_records_started_at", table_name="run_records")
    op.drop_index("ix_run_records_status", table_name="run_records")
    op.drop_index("ix_run_records_trace_id", table_name="run_records")
    op.drop_table("run_records")
