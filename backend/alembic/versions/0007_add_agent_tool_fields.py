"""Add status, tags_json, endpoint_url, http_method, credential_key, timeout_seconds, max_retries to agent_tools.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add status column, backfill from is_enabled
    op.add_column(
        "agent_tools",
        sa.Column("status", sa.String(32), nullable=True),
    )
    op.execute(sa.text(
        "UPDATE agent_tools SET status = CASE WHEN is_enabled THEN 'active' ELSE 'disabled' END"
    ))
    op.alter_column("agent_tools", "status", nullable=False)

    # 2. Add tags_json
    op.add_column(
        "agent_tools",
        sa.Column("tags_json", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
    )

    # 3. Add endpoint_url
    op.add_column(
        "agent_tools",
        sa.Column("endpoint_url", sa.String(2048), nullable=True),
    )

    # 4. Add http_method
    op.add_column(
        "agent_tools",
        sa.Column("http_method", sa.String(8), server_default="POST", nullable=False),
    )

    # 5. Add credential_key
    op.add_column(
        "agent_tools",
        sa.Column("credential_key", sa.String(256), nullable=True),
    )

    # 6. Add timeout_seconds
    op.add_column(
        "agent_tools",
        sa.Column("timeout_seconds", sa.Integer, server_default="30", nullable=False),
    )

    # 7. Add max_retries
    op.add_column(
        "agent_tools",
        sa.Column("max_retries", sa.Integer, server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("agent_tools", "max_retries")
    op.drop_column("agent_tools", "timeout_seconds")
    op.drop_column("agent_tools", "credential_key")
    op.drop_column("agent_tools", "http_method")
    op.drop_column("agent_tools", "endpoint_url")
    op.drop_column("agent_tools", "tags_json")
    op.drop_column("agent_tools", "status")
