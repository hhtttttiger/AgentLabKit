"""Persist candidate execution identity on eval_run_results.

Evaluation Evidence Composition v1: each result row records the Runtime-owned
candidate run_id / trace_id whose Trace projection produced the metric
evidence.  These columns make "Open Run / Inspect Trace" possible and keep
capture provenance (eval_cases.metadata source_run_id) distinct from candidate
evidence.  Both are NULL for rows predating this change and for dataset-only
(rag_pipeline) evaluations.

Revision ID: 0003_eval_result_candidate_identity
Revises: 0002_eval_score_nullable
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_eval_candidate_identity"
down_revision = "0002_eval_score_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_run_results",
        sa.Column("candidate_run_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "eval_run_results",
        sa.Column("candidate_trace_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("eval_run_results", "candidate_trace_id")
    op.drop_column("eval_run_results", "candidate_run_id")
