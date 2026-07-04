from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UsageBase(DeclarativeBase):
    pass


class ModelRequestLogOrm(UsageBase):
    __tablename__ = "model_request_logs"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    request_id: Mapped[str] = mapped_column("RequestId", String(64))
    model_key: Mapped[str] = mapped_column("ModelKey", String(128))
    capability: Mapped[str] = mapped_column("Capability", String(32))
    success: Mapped[bool] = mapped_column("Success", Boolean)
    attempt_count: Mapped[int] = mapped_column("AttemptCount", Integer)
    final_instance_key: Mapped[str | None] = mapped_column("FinalInstanceKey", String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column("ErrorCode", String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column("ErrorMessage", String(2048), nullable=True)
    total_input_tokens: Mapped[int] = mapped_column("TotalInputTokens", Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column("TotalOutputTokens", Integer, default=0)
    total_estimated_cost: Mapped[float] = mapped_column("TotalEstimatedCost", Numeric(18, 6), default=0)
    cache_write_tokens: Mapped[int] = mapped_column("CacheWriteTokens", Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column("CacheReadTokens", Integer, default=0)
    total_duration_ms: Mapped[int] = mapped_column("TotalDurationMs", BigInteger, default=0)
    started_at_utc: Mapped[datetime] = mapped_column("StartedAtUtc", DateTime(timezone=True))
    completed_at_utc: Mapped[datetime] = mapped_column("CompletedAtUtc", DateTime(timezone=True))
    created_at_utc: Mapped[datetime] = mapped_column("CreatedAtUtc", DateTime(timezone=True))
    updated_at_utc: Mapped[datetime | None] = mapped_column("UpdatedAtUtc", DateTime(timezone=True), nullable=True)


class ModelAttemptLogOrm(UsageBase):
    __tablename__ = "model_attempt_logs"

    id: Mapped[int] = mapped_column("Id", BigInteger, primary_key=True)
    request_id: Mapped[str] = mapped_column("RequestId", String(64))
    model_key: Mapped[str] = mapped_column("ModelKey", String(128))
    instance_key: Mapped[str] = mapped_column("InstanceKey", String(128))
    attempt_no: Mapped[int] = mapped_column("AttemptNo", Integer)
    success: Mapped[bool] = mapped_column("Success", Boolean)
    error_code: Mapped[str | None] = mapped_column("ErrorCode", String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column("ErrorMessage", String(2048), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column("InputTokens", Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column("OutputTokens", Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column("EstimatedCost", Numeric(18, 6), nullable=True)
    cache_write_tokens: Mapped[int | None] = mapped_column("CacheWriteTokens", Integer, nullable=True)
    cache_read_tokens: Mapped[int | None] = mapped_column("CacheReadTokens", Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column("DurationMs", BigInteger, default=0)
    started_at_utc: Mapped[datetime] = mapped_column("StartedAtUtc", DateTime(timezone=True))
    completed_at_utc: Mapped[datetime] = mapped_column("CompletedAtUtc", DateTime(timezone=True))
    created_at_utc: Mapped[datetime] = mapped_column("CreatedAtUtc", DateTime(timezone=True))
    updated_at_utc: Mapped[datetime | None] = mapped_column("UpdatedAtUtc", DateTime(timezone=True), nullable=True)
