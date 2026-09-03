from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from alkit_db.base import Base


class RunRecordModel(Base):
    """SQL representation of the application RunRecord read model.

    ``run_id`` is deliberately the table identity; this is not an EntityBase
    CRUD resource and therefore has no surrogate database id.
    """

    __tablename__ = "run_records"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trace_id: Mapped[str | None] = mapped_column(String(128))
    user_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_key: Mapped[str | None] = mapped_column(String(256))
    target_version: Mapped[str | None] = mapped_column(String(128))
    input_json: Mapped[Any | None] = mapped_column(JSONB)
    output_json: Mapped[Any | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    session_id: Mapped[str | None] = mapped_column(String(256))
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    projected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    projection_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("ix_run_records_trace_id", "trace_id"),
        Index("ix_run_records_status", "status"),
        Index("ix_run_records_started_at", "started_at"),
    )


class RunProjectionEventModel(Base):
    """Durable event-id ledger for RuntimeEvent idempotency."""

    __tablename__ = "run_projection_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (Index("ix_run_projection_events_run_id", "run_id"),)
