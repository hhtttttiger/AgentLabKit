"""Allow eval_run_results.overall_score to be NULL (unavailable ≠ 0.0).

Ragas returns NaN for rows a metric could not judge (missing context,
unparsable output). Persisting those as 0.0 fabricated failing scores;
Postgres JSONB/Float columns also cannot store NaN. The column becomes
nullable: NULL means "no available score", matching the tri-state
``passed`` column semantics documented on the same table.

Revision ID: 0002_eval_score_nullable
Revises: 0001_current_baseline
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_eval_score_nullable"
down_revision = "0001_current_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "eval_run_results",
        "overall_score",
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    # Destructive: rows with NULL scores (unavailable) are coerced to 0.0.
    op.execute("UPDATE eval_run_results SET overall_score = 0.0 WHERE overall_score IS NULL")
    op.alter_column(
        "eval_run_results",
        "overall_score",
        existing_type=sa.Float(),
        nullable=False,
    )
