"""Remove unused definition column from glossary_terms

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("glossary_terms", "definition")


def downgrade() -> None:
    op.add_column(
        "glossary_terms",
        sa.Column("definition", sa.Text, nullable=True),
    )
