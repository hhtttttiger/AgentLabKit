"""Add unique constraint on (category_id, term) in glossary_terms

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_glossary_term",
        "glossary_terms",
        ["category_id", "term"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_glossary_term", "glossary_terms", type_="unique")
