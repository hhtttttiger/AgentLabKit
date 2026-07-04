"""Add chat_sessions and chat_messages tables for AI chat persistence.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("model_type", sa.String(16), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_sessions_user_updated",
        "chat_sessions",
        ["user_id", sa.text("updated_at_utc DESC")],
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="sent"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trace_json", JSONB, nullable=True),
        sa.Column(
            "created_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_messages_session_created",
        "chat_messages",
        ["session_id", "created_at_utc"],
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
