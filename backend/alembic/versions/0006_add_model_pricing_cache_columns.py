"""Add model pricing columns and cache token tracking.

Adds ``input_price_per_mtok``, ``output_price_per_mtok``,
``cache_write_price_per_mtok``, ``cache_read_price_per_mtok`` to
``llm_models``, and ``CacheWriteTokens`` / ``CacheReadTokens`` to
the usage log tables.

Revision ID: 0006
Revises: 0005
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. llm_models pricing columns (snake_case, without timezone convention).
    op.add_column(
        "llm_models",
        sa.Column("input_price_per_mtok", sa.Numeric(10, 6), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("output_price_per_mtok", sa.Numeric(10, 6), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("cache_write_price_per_mtok", sa.Numeric(10, 6), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("cache_read_price_per_mtok", sa.Numeric(10, 6), nullable=True),
    )

    # 2. model_request_logs cache columns (PascalCase, with timezone convention).
    op.add_column(
        "model_request_logs",
        sa.Column("CacheWriteTokens", sa.Integer, server_default="0", nullable=False),
    )
    op.add_column(
        "model_request_logs",
        sa.Column("CacheReadTokens", sa.Integer, server_default="0", nullable=False),
    )

    # 3. model_attempt_logs cache columns (PascalCase, with timezone convention, nullable).
    op.add_column(
        "model_attempt_logs",
        sa.Column("CacheWriteTokens", sa.Integer, nullable=True),
    )
    op.add_column(
        "model_attempt_logs",
        sa.Column("CacheReadTokens", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("model_attempt_logs", "CacheReadTokens")
    op.drop_column("model_attempt_logs", "CacheWriteTokens")
    op.drop_column("model_request_logs", "CacheReadTokens")
    op.drop_column("model_request_logs", "CacheWriteTokens")
    op.drop_column("llm_models", "cache_read_price_per_mtok")
    op.drop_column("llm_models", "cache_write_price_per_mtok")
    op.drop_column("llm_models", "output_price_per_mtok")
    op.drop_column("llm_models", "input_price_per_mtok")
