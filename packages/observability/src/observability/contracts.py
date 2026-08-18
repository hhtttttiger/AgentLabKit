from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TRACE_SCHEMA_VERSION = 1
TRACE_QUEUE_NAME = "observability_traces"
TraceStatus = Literal["ok", "error", "timeout", "cancelled"]


class SpanEnvelope(BaseModel):
    """Serializable OpenTelemetry span used on the Redis ingestion boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    span_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    parent_span_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{16}$",
    )
    name: str
    kind: str = "internal"
    status: TraceStatus = "ok"
    instrumentation_scope: str = ""
    started_at_utc: datetime
    completed_at_utc: datetime
    duration_ms: int = Field(ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    links: list[dict[str, Any]] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class TraceEnvelope(BaseModel):
    """Immutable, versioned unit published by web and ingested by a worker."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[TRACE_SCHEMA_VERSION] = TRACE_SCHEMA_VERSION
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    root_span_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    run_id: str
    agent_key: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    correlation_id: str | None = None
    status: TraceStatus = "ok"
    started_at_utc: datetime
    completed_at_utc: datetime
    total_duration_ms: int = Field(ge=0)
    total_input_tokens: int = Field(default=0, ge=0)
    total_output_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    total_estimated_cost: Decimal = Field(default=Decimal("0"), ge=0)
    span_count: int = Field(ge=1)
    dropped_span_count: int = Field(default=0, ge=0)
    sample_reason: str = "normal"
    attributes: dict[str, Any] = Field(default_factory=dict)
    spans: list[SpanEnvelope] = Field(min_length=1)

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: str) -> str:
        return str(UUID(value))

    @model_validator(mode="after")
    def _validate_span_membership(self) -> "TraceEnvelope":
        if any(span.trace_id != self.trace_id for span in self.spans):
            raise ValueError("all spans must belong to the envelope trace_id")
        if self.spans and not any(
            span.span_id == self.root_span_id for span in self.spans
        ):
            raise ValueError("root_span_id must reference a retained span")
        if self.span_count != len(self.spans):
            raise ValueError("span_count must equal the retained span count")
        return self


class TraceRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trace_id: str
    root_span_id: str
    run_id: str
    agent_key: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    correlation_id: str | None = None
    status: TraceStatus
    total_duration_ms: int
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    total_estimated_cost: Decimal = Decimal("0")
    span_count: int = 0
    dropped_span_count: int = 0
    sample_reason: str = "normal"
    attributes: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = TRACE_SCHEMA_VERSION
    started_at_utc: datetime
    completed_at_utc: datetime


SpanRecord = SpanEnvelope


class TracePage(BaseModel):
    items: list[TraceRecord]
    next_cursor: str | None = None


class TraceStats(BaseModel):
    total_traces: int = 0
    error_count: int = 0
    timeout_count: int = 0
    cancelled_count: int = 0
    p50_duration_ms: float = 0
    p95_duration_ms: float = 0
    total_tokens: int = 0
    total_estimated_cost: Decimal = Decimal("0")


__all__ = [
    "SpanEnvelope",
    "SpanRecord",
    "TRACE_QUEUE_NAME",
    "TRACE_SCHEMA_VERSION",
    "TraceEnvelope",
    "TracePage",
    "TraceRecord",
    "TraceStats",
    "TraceStatus",
]
