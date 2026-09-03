"""Persist authoritative Runtime Run ownership.

Revision ID: 0021
Revises: 0020
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable is intentional: legacy/unowned rows are denied by the HTTP
    # resource policy rather than being guessed or backfilled from projections.
    op.add_column("run_records", sa.Column("user_id", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("run_records", "user_id")
