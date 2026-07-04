"""align timestamp types to non-tz (model DateTime without timezone).

003-006 迁移建表时部分时间戳列用了 DateTime(timezone=True),而 model 用 DateTime()
(无 tz)。本迁移把 DB 这些列统一为 timestamp WITHOUT TIME ZONE,对齐 model。

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE public."cost_budgets" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."cost_budgets" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."cost_alerts" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."cost_alerts" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."trace_records" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."trace_records" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."trace_spans" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."trace_spans" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."memory_records" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."memory_records" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."memory_embeddings" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."memory_embeddings" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_datasets" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_datasets" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_cases" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_cases" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_run_configs" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_run_configs" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_runs" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_runs" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_run_results" ALTER COLUMN "created_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_run_results" ALTER COLUMN "updated_at_utc" TYPE timestamp WITHOUT TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')


def downgrade() -> None:
    op.execute('ALTER TABLE public."eval_run_results" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_run_results" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_runs" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_runs" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_run_configs" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_run_configs" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_cases" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_cases" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_datasets" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."eval_datasets" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."memory_embeddings" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."memory_embeddings" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."memory_records" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."memory_records" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."trace_spans" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."trace_spans" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."trace_records" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."trace_records" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."cost_alerts" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."cost_alerts" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."cost_budgets" ALTER COLUMN "updated_at_utc" TYPE timestamp WITH TIME ZONE USING "updated_at_utc" AT TIME ZONE \'UTC\'')
    op.execute('ALTER TABLE public."cost_budgets" ALTER COLUMN "created_at_utc" TYPE timestamp WITH TIME ZONE USING "created_at_utc" AT TIME ZONE \'UTC\'')
