from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import Field

from common.schemas import CamelModel


class TraceListItem(CamelModel):
    trace_id: str
    root_span_id: str
    run_id: str
    agent_key: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    correlation_id: str | None = None
    status: str
    total_duration_ms: int
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    total_estimated_cost: float = 0
    span_count: int = 0
    dropped_span_count: int = 0
    sample_reason: str
    attributes: dict[str, Any]
    schema_version: int
    started_at_utc: datetime
    completed_at_utc: datetime


class SpanItem(CamelModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    name: str
    kind: str
    status: str
    instrumentation_scope: str
    started_at_utc: datetime
    completed_at_utc: datetime
    duration_ms: int
    attributes: dict[str, Any]
    events: list[dict[str, Any]]
    links: list[dict[str, Any]]
    error_code: str | None = None
    error_message: str | None = None


class TraceDetailResponse(CamelModel):
    trace: TraceListItem
    spans: list[SpanItem]


class TracePageResponse(CamelModel):
    items: list[TraceListItem]
    next_cursor: str | None = None


class TraceStatsResponse(CamelModel):
    total_traces: int
    error_count: int
    timeout_count: int
    cancelled_count: int
    p50_duration_ms: float
    p95_duration_ms: float
    total_tokens: int
    total_estimated_cost: float


class QueueHealth(CamelModel):
    backlog: int = 0
    pending: int = 0
    delayed: int = 0
    dead_letter: int = 0
    consumers: int = 0
    available: int = 0


class PublisherHealth(CamelModel):
    published: int = 0
    retried: int = 0
    dropped: int = 0
    queue_depth: int = 0
    active_traces: int = 0
    buffered_spans: int = 0
    buffer_overflow_dropped: int = 0


class IngestionHealthResponse(CamelModel):
    publisher: PublisherHealth
    queue: QueueHealth | None = None
    worker_tasks: dict[str, QueueHealth] = Field(default_factory=dict)
