from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from alkit_db.base import EntityBase


class TraceRecordOrm(EntityBase):
    __tablename__ = "trace_records"

    trace_id: Mapped[str] = mapped_column(String(32), unique=True)
    root_span_id: Mapped[str] = mapped_column(String(16))
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True)
    agent_key: Mapped[str | None] = mapped_column(String(128))
    session_id: Mapped[str | None] = mapped_column(String(128))
    user_id: Mapped[str | None] = mapped_column(String(128))
    correlation_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16))
    total_duration_ms: Mapped[int] = mapped_column(BigInteger)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_estimated_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    span_count: Mapped[int] = mapped_column(Integer, default=0)
    dropped_span_count: Mapped[int] = mapped_column(Integer, default=0)
    sample_reason: Mapped[str] = mapped_column(String(32), default="normal")
    attributes_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status IN ('ok','error','timeout','cancelled')", name="ck_trace_status"),
        Index("ix_trace_records_started_cursor", started_at_utc.desc(), trace_id.desc()),
        Index("ix_trace_records_agent_time", "agent_key", started_at_utc.desc()),
        Index("ix_trace_records_session_time", "session_id", started_at_utc.desc()),
        Index("ix_trace_records_status_time", "status", started_at_utc.desc()),
    )


class TraceSpanOrm(EntityBase):
    __tablename__ = "trace_spans"

    span_id: Mapped[str] = mapped_column(String(16), unique=True)
    trace_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("trace_records.trace_id", ondelete="CASCADE"),
    )
    parent_span_id: Mapped[str | None] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(256))
    span_kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    instrumentation_scope: Mapped[str] = mapped_column(String(256), default="")
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int] = mapped_column(BigInteger)
    attributes_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    events_json: Mapped[list] = mapped_column(JSONB, default=list)
    links_json: Mapped[list] = mapped_column(JSONB, default=list)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("status IN ('ok','error','timeout','cancelled')", name="ck_trace_span_status"),
        Index("ix_trace_spans_trace_time", "trace_id", "started_at_utc", "span_id"),
    )
