"""Add updated_at_utc column to chat_messages table.

ChatMessageOrm inherits updated_at_utc from EntityBase but the 0009 migration
omitted the column, causing queries to fail with "column does not exist".
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS updated_at_utc "
        "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS updated_at_utc")
