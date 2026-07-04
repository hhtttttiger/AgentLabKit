"""SpanBuilder — 从 EventBus 事件累积构建 span。

监听 agent_runtime 的 EventBus 事件，逐步构建出完整的 SpanRecord 列表，
最终 finalize() 输出 TraceRecord + list[SpanRecord]。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Protocol, TypedDict
from uuid import uuid4

from .contracts import SpanRecord, TraceRecord


class _ActiveSpanMeta(TypedDict, total=False):
    span_id: str
    kind: str
    name: str
    parent_id: str | None
    start_mono: float
    start_utc: datetime
    tool_name: str
    args: dict[str, Any]
    source_type: str | None
    source_ref: str | None


class _Event(Protocol):
    type: str

logger = logging.getLogger(__name__)


class SpanBuilder:
    """订阅 EventBus 事件，累积构建 span 树。

    典型用法::

        builder = SpanBuilder(trace_id="abc", agent_key="my-agent")
        unsub = event_bus.subscribe(builder.on_event)
        # ... agent runs ...
        unsub()
        trace, spans = builder.finalize()
    """

    def __init__(
        self,
        trace_id: str,
        agent_key: str | None = None,
        session_id: str | None = None,
        max_spans: int = 500,
    ) -> None:
        self.trace_id = trace_id
        self.agent_key = agent_key
        self.session_id = session_id
        self._max_spans = max_spans

        self._spans: list[SpanRecord] = []
        self._active_spans: dict[str, _ActiveSpanMeta] = {}  # span_id → metadata
        self._start_mono = time.monotonic()
        self._start_utc = datetime.now(timezone.utc)
        self._root_span_id: str | None = None

        # Token / cost 累积
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_estimated_cost = 0.0

        # 最终状态
        self._status = "ok"
        self._error_message: str | None = None

    # ── EventBus listener ────────────────────────────────────────────────

    def _append_span(self, span: SpanRecord) -> None:
        """追加 span，超限时丢弃并记录 warning。"""
        if len(self._spans) >= self._max_spans:
            logger.warning(
                "max_spans_per_trace reached (%d), dropping span %s",
                self._max_spans, span.span_id,
            )
            return
        self._spans.append(span)

    def on_event(self, event: _Event) -> None:
        event_type = getattr(event, "type", "")

        if event_type == "turn_start":
            self._on_turn_start()
        elif event_type == "turn_end":
            self._on_turn_end(event)
        elif event_type == "tool_execution_start":
            self._on_tool_start(event)
        elif event_type == "tool_execution_end":
            self._on_tool_end(event)
        elif event_type == "message_start":
            self._on_message_start(event)
        elif event_type == "message_end":
            self._on_message_end(event)

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_turn_start(self) -> None:
        span_id = uuid4().hex[:16]
        self._root_span_id = span_id
        self._active_spans[span_id] = {
            "kind": "agent_turn",
            "name": "agent_turn",
            "parent_id": None,
            "start_mono": time.monotonic(),
            "start_utc": datetime.now(timezone.utc),
        }

    def _on_turn_end(self, event: Any) -> None:
        if self._root_span_id and self._root_span_id in self._active_spans:
            meta = self._active_spans.pop(self._root_span_id)
            elapsed = int((time.monotonic() - meta["start_mono"]) * 1000)
            self._append_span(SpanRecord(
                span_id=self._root_span_id,
                trace_id=self.trace_id,
                parent_span_id=None,
                span_kind="agent_turn",
                name="agent_turn",
                status=self._status,
                started_at_utc=meta["start_utc"],
                completed_at_utc=datetime.now(timezone.utc),
                duration_ms=elapsed,
                attributes={
                    "agent_key": self.agent_key or "",
                    "session_id": self.session_id or "",
                },
                error_message=self._error_message,
            ))

    def _on_tool_start(self, event: Any) -> None:
        span_id = uuid4().hex[:16]
        tool_name = getattr(event, "tool_name", "unknown")
        self._active_spans[f"tool:{tool_name}:{span_id}"] = {
            "span_id": span_id,
            "kind": "tool_execution",
            "name": f"tool:{tool_name}",
            "parent_id": self._root_span_id,
            "start_mono": time.monotonic(),
            "start_utc": datetime.now(timezone.utc),
            "tool_name": tool_name,
            "args": getattr(event, "args", {}),
            "source_type": getattr(event, "source_type", None) or None,
            "source_ref": getattr(event, "source_ref", None) or None,
        }

    def _on_tool_end(self, event: Any) -> None:
        tool_name = getattr(event, "tool_name", "unknown")
        is_error = getattr(event, "is_error", False)

        # Find matching active span
        key = None
        for k, v in self._active_spans.items():
            if k.startswith(f"tool:{tool_name}:") and v.get("kind") == "tool_execution":
                key = k
                break

        if key and key in self._active_spans:
            meta = self._active_spans.pop(key)
            elapsed = int((time.monotonic() - meta["start_mono"]) * 1000)
            result_preview = str(getattr(event, "result", ""))[:200] if not is_error else None

            self._append_span(SpanRecord(
                span_id=meta["span_id"],
                trace_id=self.trace_id,
                parent_span_id=meta["parent_id"],
                span_kind="tool_execution",
                name=meta["name"],
                status="error" if is_error else "ok",
                started_at_utc=meta["start_utc"],
                completed_at_utc=datetime.now(timezone.utc),
                duration_ms=elapsed,
                attributes={
                    "tool_name": tool_name,
                    "args_preview": str(meta.get("args", {}))[:500],
                    "result_preview": result_preview or "",
                    "source_type": str(meta.get("source_type") or ""),
                    "source_ref": str(meta.get("source_ref") or ""),
                },
                error_message=str(getattr(event, "result", ""))[:500] if is_error else None,
            ))

    def _on_message_start(self, event: Any) -> None:
        msg = getattr(event, "message", None)
        if msg is None:
            return
        role = getattr(msg, "role", "")
        if role == "assistant":
            span_id = uuid4().hex[:16]
            self._active_spans[f"llm_call:{span_id}"] = {
                "span_id": span_id,
                "kind": "llm_call",
                "name": "llm_completion",
                "parent_id": self._root_span_id,
                "start_mono": time.monotonic(),
                "start_utc": datetime.now(timezone.utc),
            }

    def _on_message_end(self, event: Any) -> None:
        # Find the oldest active llm_call span (FIFO — matches tool span pattern)
        key = None
        for k, v in self._active_spans.items():
            if k.startswith("llm_call:") and v.get("kind") == "llm_call":
                key = k
                break

        if key and key in self._active_spans:
            meta = self._active_spans.pop(key)
            elapsed = int((time.monotonic() - meta["start_mono"]) * 1000)
            msg = getattr(event, "message", None)

            # Extract usage if available (check event first, then message)
            usage = (
                getattr(event, "usage", None)
                or getattr(msg, "usage", None)
                or {}
            )
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0

            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens

            self._append_span(SpanRecord(
                span_id=meta["span_id"],
                trace_id=self.trace_id,
                parent_span_id=meta["parent_id"],
                span_kind="llm_call",
                name="llm_completion",
                status="ok",
                started_at_utc=meta["start_utc"],
                completed_at_utc=datetime.now(timezone.utc),
                duration_ms=elapsed,
                attributes={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            ))

    # ── Error tracking ────────────────────────────────────────────────────

    def set_error(self, error_message: str) -> None:
        self._status = "error"
        self._error_message = error_message

    # ── Finalize ──────────────────────────────────────────────────────────

    def finalize(self) -> tuple[TraceRecord, list[SpanRecord]]:
        """输出最终的 TraceRecord + SpanRecords。"""
        now = datetime.now(timezone.utc)
        total_duration = int((time.monotonic() - self._start_mono) * 1000)

        trace = TraceRecord(
            trace_id=self.trace_id,
            root_span_id=self._root_span_id or "",
            agent_key=self.agent_key,
            session_id=self.session_id,
            status=self._status,
            total_duration_ms=total_duration,
            total_input_tokens=self._total_input_tokens,
            total_output_tokens=self._total_output_tokens,
            total_estimated_cost=self._total_estimated_cost,
            span_count=len(self._spans),
            started_at_utc=self._start_utc,
            completed_at_utc=now,
        )
        return trace, list(self._spans)
