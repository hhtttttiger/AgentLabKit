from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from alkit_db.base import EntityBase


class TraceRecordOrm(EntityBase):
    """链路记录 — 一次完整的 Agent/LLM 请求。"""
    __tablename__ = "trace_records"

    trace_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    root_span_id: Mapped[str] = mapped_column(String(64), default="")
    agent_key: Mapped[str | None] = mapped_column(String(128), index=True)
    session_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="ok")
    total_duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    span_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_trace_records_agent_time", "agent_key", "started_at_utc"),
    )


class TraceSpanOrm(EntityBase):
    """链路 span — 单个操作（LLM 调用、工具执行等）。"""
    __tablename__ = "trace_spans"

    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    span_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(64))
    span_kind: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default="ok")
    started_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    attributes_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_trace_spans_trace_id", "trace_id"),
    )
