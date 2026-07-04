"""Simplify model binding table by removing scene and type columns.

Drops the ``scene`` and ``type`` columns from ``llm_model_bindings``,
consolidating the binding's classification into the ``capability`` column
(which is promoted to NOT NULL).

Revision ID: 0005
Revises: 0004
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Backfill capability from type for rows where capability is NULL.
    op.execute(sa.text(
        "UPDATE llm_model_bindings SET capability = type WHERE capability IS NULL"
    ))
    # 2. Make capability NOT NULL now that all rows have a value.
    op.alter_column(
        "llm_model_bindings",
        "capability",
        existing_type=sa.String(32),
        nullable=False,
    )
    # 3. Drop the type column.
    op.drop_column("llm_model_bindings", "type")
    # 4. Drop the scene column.
    op.drop_column("llm_model_bindings", "scene")


def downgrade() -> None:
    # 1. Re-add scene column.
    op.add_column(
        "llm_model_bindings",
        sa.Column("scene", sa.String(64), nullable=True),
    )
    # 2. Re-add type column, backfill from capability.
    op.add_column(
        "llm_model_bindings",
        sa.Column("type", sa.String(32), nullable=True),
    )
    op.execute(sa.text(
        "UPDATE llm_model_bindings SET type = capability"
    ))
    op.alter_column(
        "llm_model_bindings",
        "type",
        existing_type=sa.String(32),
        nullable=False,
    )
    # 3. Restore scene from binding_key naming convention.
    op.execute(sa.text(
        "UPDATE llm_model_bindings SET scene = 'gateway' WHERE binding_key LIKE 'gateway.%'"
    ))
    op.execute(sa.text(
        "UPDATE llm_model_bindings SET scene = 'voice' WHERE binding_key LIKE 'voice.%'"
    ))
    op.execute(sa.text(
        "UPDATE llm_model_bindings SET scene = 'direct' WHERE scene IS NULL"
    ))
    op.alter_column(
        "llm_model_bindings",
        "scene",
        existing_type=sa.String(64),
        nullable=False,
    )
    # 4. Make capability nullable again.
    op.alter_column(
        "llm_model_bindings",
        "capability",
        existing_type=sa.String(32),
        nullable=True,
    )
