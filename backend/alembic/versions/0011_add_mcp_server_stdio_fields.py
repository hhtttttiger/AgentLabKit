"""Add stdio transport fields to agent_mcp_servers

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_mcp_servers",
        sa.Column("command", sa.String(1024), nullable=True),
    )
    op.add_column(
        "agent_mcp_servers",
        sa.Column(
            "args_json",
            JSONB,
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_mcp_servers", "args_json")
    op.drop_column("agent_mcp_servers", "command")
