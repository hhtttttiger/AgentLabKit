from __future__ import annotations

from datetime import datetime
from typing import Any


from common.schemas import CamelModel


# ── Trace ─────────────────────────────────────────────────────────────


class TraceListItem(CamelModel):
    trace_id: str
    root_span_id: str = ""
    agent_key: str | None = None
    session_id: str | None = None
    status: str
    total_duration_ms: int | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_estimated_cost: float = 0
    span_count: int = 0
    started_at_utc: datetime
    completed_at_utc: datetime | None = None


class SpanItem(CamelModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    span_kind: str
    name: str
    status: str
    started_at_utc: datetime | None = None
    completed_at_utc: datetime | None = None
    duration_ms: int | None = None
    attributes: dict[str, Any] = {}
    error_code: str | None = None
    error_message: str | None = None


class TraceDetailResponse(CamelModel):
    trace: TraceListItem
    spans: list[SpanItem]


class TraceStatsResponse(CamelModel):
    total_traces: int
    avg_duration_ms: float
    total_tokens: int
    error_count: int

