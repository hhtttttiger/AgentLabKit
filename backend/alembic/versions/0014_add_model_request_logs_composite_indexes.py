"""Add composite indexes on model_request_logs for monitoring queries.

- ix_mlogs_model_started:  covers /statistics/models filtered by ModelKey + time range
- ix_mlogs_errors_lookup: covers /errors filtered by Success + ErrorCode + time range

Revision ID: 0014
Revises: 0013
"""

from __future__ import annotations

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_mlogs_model_started",
        "model_request_logs",
        ["ModelKey", "StartedAtUtc"],
    )
    op.create_index(
        "ix_mlogs_errors_lookup",
        "model_request_logs",
        ["Success", "ErrorCode", "StartedAtUtc"],
    )


def downgrade() -> None:
    op.drop_index("ix_mlogs_errors_lookup", table_name="model_request_logs")
    op.drop_index("ix_mlogs_model_started", table_name="model_request_logs")
