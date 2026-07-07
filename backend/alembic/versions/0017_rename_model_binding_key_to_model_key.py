"""Rename model_binding_key to model_key.

Agents bind to models, not binding relations.  Rename the column in
``agent_definition_versions`` and ``evaluation_configs`` to reflect this.

Idempotent: safe to run multiple times.

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def _has_column(inspector, table: str, column: str) -> bool:
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_column(inspector, "agent_definition_versions", "model_binding_key"):
        op.alter_column(
            "agent_definition_versions",
            "model_binding_key",
            new_column_name="model_key",
        )

    if _has_column(inspector, "evaluation_configs", "judge_model_binding_key"):
        op.alter_column(
            "evaluation_configs",
            "judge_model_binding_key",
            new_column_name="judge_model_key",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_column(inspector, "evaluation_configs", "judge_model_key"):
        op.alter_column(
            "evaluation_configs",
            "judge_model_key",
            new_column_name="judge_model_binding_key",
        )

    if _has_column(inspector, "agent_definition_versions", "model_key"):
        op.alter_column(
            "agent_definition_versions",
            "model_key",
            new_column_name="model_binding_key",
        )
