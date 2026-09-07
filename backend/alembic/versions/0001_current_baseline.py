"""Create the current database schema from the authoritative ORM metadata.

This is a destructive compatibility boundary. Databases created before this
revision are unsupported and must be recreated rather than upgraded.

Revision ID: 0001_current_baseline
Revises:
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

from alkit_db import Base
from llm_gateway.usage.orm_models import UsageBase

# alembic/env.py imports every ORM model before executing revisions. Keeping
# model loading there avoids importing application package __init__ modules when
# Alembic only inspects revision identities (heads/history/branches).

revision = "0001_current_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Extensions must exist before metadata.create_all emits vector/trigram
    # indexes. CREATE EXTENSION is safe and repeatable on a clean database.
    bind.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
    bind.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.create_all(bind=bind)
    UsageBase.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    UsageBase.metadata.drop_all(bind=bind)
    Base.metadata.drop_all(bind=bind)
    bind.execute(text("DROP EXTENSION IF EXISTS pg_trgm"))
    bind.execute(text("DROP EXTENSION IF EXISTS vector"))
