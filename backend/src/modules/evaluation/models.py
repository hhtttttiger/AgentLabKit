from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from alkit_db.base import EntityBase


class EvalDataset(EntityBase):
    __tablename__ = "eval_datasets"
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(1024))
    tags_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)


class EvalCase(EntityBase):
    __tablename__ = "eval_cases"
    dataset_id: Mapped[int] = mapped_column(BigInteger, index=True)
    case_index: Mapped[int] = mapped_column(Integer)
    input_text: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str | None] = mapped_column(Text)
    context_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    tags_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class EvalRunConfig(EntityBase):
    __tablename__ = "eval_run_configs"
    name: Mapped[str] = mapped_column(String(256))
    dataset_id: Mapped[int] = mapped_column(BigInteger, index=True)
    target_type: Mapped[str] = mapped_column(String(32), default="agent")
    target_key: Mapped[str] = mapped_column(String(128), default="")
    metric_configs_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    judge_model_binding_key: Mapped[str] = mapped_column(String(128), default="")


class EvalRun(EntityBase):
    __tablename__ = "eval_runs"
    config_id: Mapped[int] = mapped_column(BigInteger, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/running/completed/failed
    started_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class EvalRunResult(EntityBase):
    __tablename__ = "eval_run_results"
    run_id: Mapped[int] = mapped_column(BigInteger, index=True)
    case_id: Mapped[int] = mapped_column(BigInteger, index=True)
    actual_output: Mapped[str] = mapped_column(Text, default="")
    metric_results_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    overall_score: Mapped[float] = mapped_column(Float, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(BigInteger, default=0)
