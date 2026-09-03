"""Persist nullable per-example evaluation verdicts.

Revision ID: 0022
Revises: 0021
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eval_run_results", sa.Column("passed", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("eval_run_results", "passed")
