"""Add extra_json column to KB, MCP, and skill binding tables for config data.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("agent_knowledge_base_bindings", "agent_mcp_bindings", "agent_skill_bindings"):
        op.add_column(
            table,
            sa.Column("extra_json", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        )


def downgrade() -> None:
    for table in ("agent_skill_bindings", "agent_mcp_bindings", "agent_knowledge_base_bindings"):
        op.drop_column(table, "extra_json")
