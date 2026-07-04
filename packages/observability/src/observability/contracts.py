from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SpanKind(str, Enum):
    AGENT_TURN = "agent_turn"
    LLM_CALL = "llm_call"
    TOOL_EXECUTION = "tool_execution"
    RAG_QUERY = "rag_query"
    HANDOFF = "handoff"
    GUARDRAIL = "guardrail"


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """单个可观测性 span。"""
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    span_kind: str = ""
    name: str = ""
    status: str = "ok"  # ok / error / timeout
    started_at_utc: datetime | None = None
    completed_at_utc: datetime | None = None
    duration_ms: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class TraceRecord:
    """一条完整的执行链路。"""
    trace_id: str
    root_span_id: str = ""
    agent_key: str | None = None
    session_id: str | None = None
    status: str = "ok"
    total_duration_ms: int | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_estimated_cost: float = 0.0
    span_count: int = 0
    started_at_utc: datetime | None = None
    completed_at_utc: datetime | None = None
