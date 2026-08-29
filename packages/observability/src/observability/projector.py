"""TraceProjector — 消费 RuntimeEvent v2 语义事件，生成 Trace。

核心原则：
- Observability 不再理解业务事件
- 只负责：RuntimeEvent → Trace Projection
- 不再出现 if event_name.startswith("tool_") 这种隐式语义判断

用法：

    projector = TraceProjector(publisher, settings)
    bus.subscribe(projector.handle)

当收到 RunCompleted / RunFailed / RunCancelled 时，构建 TraceEnvelope 并提交。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from .config import ObservabilitySettings
from .contracts import SpanEnvelope, TraceEnvelope, TraceStatus
from .publisher import AsyncTracePublisher
from .sanitizer import bounded_attributes

logger = logging.getLogger(__name__)


def _to_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class TraceProjector:
    """消费语义事件，构建 TraceEnvelope。

    每个语义事件映射为一个 SpanEnvelope。当 Run 终止时，收集所有
    累积的 Span 并构建 TraceEnvelope 提交到 publisher。
    """

    def __init__(
        self,
        publisher: AsyncTracePublisher,
        settings: ObservabilitySettings,
    ) -> None:
        self._publisher = publisher
        self._settings = settings
        self._spans: dict[str, list[SpanEnvelope]] = {}  # run_id → spans
        self._run_meta: dict[str, dict[str, Any]] = {}   # run_id → metadata
        self._trace_ids: dict[str, str] = {}              # run_id → trace_id

    async def handle(self, event: Any) -> None:
        """EventBus listener — 处理所有事件类型。

        只处理 v2 语义事件（有 event_type 属性的 RuntimeEvent 子类）。
        旧事件（AgentStartEvent 等）被忽略。
        """
        event_type = getattr(event, "event_type", None)
        if event_type is None or not isinstance(event_type, str):
            return  # 不是 v2 语义事件，跳过

        run_id = getattr(event, "run_id", "")
        if not run_id:
            return

        # 按事件类型分发
        handler = self._HANDLERS.get(event_type)
        if handler is not None:
            handler(self, event, run_id)

    # ── Run lifecycle ───────────────────────────────────────────────

    def _handle_run_started(self, event: Any, run_id: str) -> None:
        trace_id = getattr(event, "trace_id", "") or uuid4().hex
        self._trace_ids[run_id] = trace_id
        self._spans[run_id] = []
        self._run_meta[run_id] = {
            "agent_key": getattr(event, "agent_key", ""),
            "session_id": getattr(event, "session_id", ""),
            "started_at": _to_utc(getattr(event, "timestamp", None)),
        }
        # 创建 root span
        root = self._make_span(
            run_id=run_id,
            trace_id=trace_id,
            name="agent.run",
            event=event,
            attributes={
                "agentlabkit.trace.root": True,
                "agentlabkit.run_id": run_id,
                "agentlabkit.agent_key": getattr(event, "agent_key", ""),
            },
        )
        self._spans[run_id].append(root)

    def _handle_run_completed(self, event: Any, run_id: str) -> None:
        self._finalize_run(run_id, event, status="ok")

    def _handle_run_failed(self, event: Any, run_id: str) -> None:
        self._finalize_run(run_id, event, status="error")

    def _handle_run_cancelled(self, event: Any, run_id: str) -> None:
        self._finalize_run(run_id, event, status="cancelled")

    def _finalize_run(self, run_id: str, event: Any, status: TraceStatus) -> None:
        trace_id = self._trace_ids.pop(run_id, "")
        spans = self._spans.pop(run_id, [])
        meta = self._run_meta.pop(run_id, {})

        if not trace_id or not spans:
            return

        # 更新 root span 的结束时间和状态
        root = spans[0]
        completed_at = _to_utc(getattr(event, "timestamp", None))
        started_at = meta.get("started_at", completed_at)
        duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))

        # 聚合 token
        input_tokens = getattr(event, "total_input_tokens", 0) or 0
        output_tokens = getattr(event, "total_output_tokens", 0) or 0

        envelope = TraceEnvelope(
            trace_id=trace_id,
            root_span_id=root.span_id,
            run_id=run_id,
            agent_key=meta.get("agent_key") or None,
            session_id=meta.get("session_id") or None,
            status=status,
            started_at_utc=started_at,
            completed_at_utc=completed_at,
            total_duration_ms=duration_ms,
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            span_count=len(spans),
            spans=sorted(spans, key=lambda s: (s.started_at_utc, s.span_id)),
        )

        try:
            self._publisher.submit_nowait(envelope)
        except Exception:
            logger.exception("projector.submit_failed run_id=%s", run_id)

    # ── Agent lifecycle ─────────────────────────────────────────────

    def _handle_agent_started(self, event: Any, run_id: str) -> None:
        self._append_span(run_id, self._make_span(
            run_id=run_id,
            trace_id=self._trace_ids.get(run_id, ""),
            name="agent.process",
            event=event,
            attributes={"agent.key": getattr(event, "agent_key", "")},
        ))

    def _handle_agent_completed(self, event: Any, run_id: str) -> None:
        self._close_last_span(run_id, "agent.process", event)

    def _handle_turn_started(self, event: Any, run_id: str) -> None:
        self._append_span(run_id, self._make_span(
            run_id=run_id,
            trace_id=self._trace_ids.get(run_id, ""),
            name="agent.turn",
            event=event,
            attributes={"turn.index": getattr(event, "turn_index", 0)},
        ))

    def _handle_turn_completed(self, event: Any, run_id: str) -> None:
        self._close_last_span(run_id, "agent.turn", event)

    # ── LLM calls ───────────────────────────────────────────────────

    def _handle_llm_started(self, event: Any, run_id: str) -> None:
        self._append_span(run_id, self._make_span(
            run_id=run_id,
            trace_id=self._trace_ids.get(run_id, ""),
            name="llm.generate",
            event=event,
            attributes={
                "gen_ai.request.model": getattr(event, "model", ""),
                "gen_ai.system": getattr(event, "provider", ""),
            },
        ))

    def _handle_llm_completed(self, event: Any, run_id: str) -> None:
        """关闭 LLM span 并注入 usage 属性。"""
        spans = self._spans.get(run_id, [])
        # 找到最近的未关闭 llm.generate span
        for span in reversed(spans):
            if span.name == "llm.generate" and span.completed_at_utc == span.started_at_utc:
                attrs = dict(span.attributes)
                attrs["gen_ai.usage.input_tokens"] = getattr(event, "input_tokens", 0)
                attrs["gen_ai.usage.output_tokens"] = getattr(event, "output_tokens", 0)
                attrs["gen_ai.usage.cache_write_tokens"] = getattr(event, "cache_write_tokens", 0)
                attrs["gen_ai.usage.cache_read_tokens"] = getattr(event, "cache_read_tokens", 0)
                attrs["gen_ai.usage.estimated_cost"] = getattr(event, "estimated_cost", 0.0)
                completed_at = _to_utc(getattr(event, "timestamp", None))
                started_at = span.started_at_utc
                duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))

                # Replace the span with updated version
                idx = spans.index(span)
                spans[idx] = SpanEnvelope(
                    span_id=span.span_id,
                    trace_id=span.trace_id,
                    parent_span_id=span.parent_span_id,
                    name=span.name,
                    kind=span.kind,
                    status=span.status,
                    instrumentation_scope=span.instrumentation_scope,
                    started_at_utc=span.started_at_utc,
                    completed_at_utc=completed_at,
                    duration_ms=duration_ms,
                    attributes=attrs,
                    events=span.events,
                    links=span.links,
                    error_code=span.error_code,
                    error_message=span.error_message,
                )
                break

    def _handle_llm_failed(self, event: Any, run_id: str) -> None:
        self._close_last_span(run_id, "llm.generate", event, error=True)

    # ── Tool calls ──────────────────────────────────────────────────

    def _handle_tool_started(self, event: Any, run_id: str) -> None:
        self._append_span(run_id, self._make_span(
            run_id=run_id,
            trace_id=self._trace_ids.get(run_id, ""),
            name=f"tool.{getattr(event, 'tool_name', 'unknown')}",
            event=event,
            attributes={
                "tool.name": getattr(event, "tool_name", ""),
                "tool.source_type": getattr(event, "source_type", ""),
            },
        ))

    def _handle_tool_completed(self, event: Any, run_id: str) -> None:
        tool_name = getattr(event, "tool_name", "unknown")
        self._close_last_span(run_id, f"tool.{tool_name}", event)

    def _handle_tool_failed(self, event: Any, run_id: str) -> None:
        tool_name = getattr(event, "tool_name", "unknown")
        self._close_last_span(run_id, f"tool.{tool_name}", event, error=True)

    # ── Guardrails ──────────────────────────────────────────────────

    def _handle_guardrail_evaluated(self, event: Any, run_id: str) -> None:
        self._append_span(run_id, self._make_span(
            run_id=run_id,
            trace_id=self._trace_ids.get(run_id, ""),
            name=f"guardrail.{getattr(event, 'guardrail_name', 'unknown')}",
            event=event,
            attributes={
                "guardrail.name": getattr(event, "guardrail_name", ""),
                "guardrail.type": getattr(event, "guardrail_type", ""),
                "guardrail.passed": getattr(event, "passed", True),
            },
        ))

    def _handle_guardrail_blocked(self, event: Any, run_id: str) -> None:
        name = getattr(event, "guardrail_name", "unknown")
        self._append_span(run_id, self._make_span(
            run_id=run_id,
            trace_id=self._trace_ids.get(run_id, ""),
            name=f"guardrail.{name}",
            event=event,
            status="error",
            attributes={
                "guardrail.name": name,
                "guardrail.type": getattr(event, "guardrail_type", ""),
                "guardrail.action": getattr(event, "action", ""),
                "guardrail.reason": getattr(event, "reason", ""),
            },
        ))

    # ── Multi-agent ─────────────────────────────────────────────────

    def _handle_handoff_started(self, event: Any, run_id: str) -> None:
        self._append_span(run_id, self._make_span(
            run_id=run_id,
            trace_id=self._trace_ids.get(run_id, ""),
            name="handoff",
            event=event,
            attributes={
                "handoff.source": getattr(event, "source_agent", ""),
                "handoff.target": getattr(event, "target_agent", ""),
                "handoff.reason": getattr(event, "reason", ""),
            },
        ))

    def _handle_handoff_completed(self, event: Any, run_id: str) -> None:
        self._close_last_span(run_id, "handoff", event)

    def _handle_delegation_started(self, event: Any, run_id: str) -> None:
        self._append_span(run_id, self._make_span(
            run_id=run_id,
            trace_id=self._trace_ids.get(run_id, ""),
            name="delegation",
            event=event,
            attributes={
                "delegation.agent": getattr(event, "target_agent", ""),
                "delegation.tool": getattr(event, "tool_name", ""),
            },
        ))

    def _handle_delegation_completed(self, event: Any, run_id: str) -> None:
        self._close_last_span(run_id, "delegation", event)

    # ── Internal helpers ────────────────────────────────────────────

    def _make_span(
        self,
        *,
        run_id: str,
        trace_id: str,
        name: str,
        event: Any,
        status: TraceStatus = "ok",
        attributes: dict[str, Any] | None = None,
    ) -> SpanEnvelope:
        ts = _to_utc(getattr(event, "timestamp", None))
        span_id = uuid4().hex[:16]
        parent_span_id = self._find_parent_span_id(run_id)

        attrs = bounded_attributes(
            attributes or {},
            max_bytes=self._settings.max_attribute_bytes,
        )

        return SpanEnvelope(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name[:256],
            kind="internal",
            status=status,
            instrumentation_scope="trace_projector",
            started_at_utc=ts,
            completed_at_utc=ts,  # 未关闭时等于 started_at
            duration_ms=0,
            attributes=attrs,
        )

    def _append_span(self, run_id: str, span: SpanEnvelope) -> None:
        spans = self._spans.get(run_id)
        if spans is not None and len(spans) < self._settings.max_spans_per_trace:
            spans.append(span)

    def _close_last_span(self, run_id: str, name: str, event: Any, error: bool = False) -> None:
        spans = self._spans.get(run_id, [])
        for span in reversed(spans):
            if span.name == name and span.completed_at_utc == span.started_at_utc:
                completed_at = _to_utc(getattr(event, "timestamp", None))
                started_at = span.started_at_utc
                duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
                status: TraceStatus = "error" if error else "ok"

                idx = spans.index(span)
                spans[idx] = SpanEnvelope(
                    span_id=span.span_id,
                    trace_id=span.trace_id,
                    parent_span_id=span.parent_span_id,
                    name=span.name,
                    kind=span.kind,
                    status=status,
                    instrumentation_scope=span.instrumentation_scope,
                    started_at_utc=span.started_at_utc,
                    completed_at_utc=completed_at,
                    duration_ms=duration_ms,
                    attributes=span.attributes,
                    events=span.events,
                    links=span.links,
                    error_code=getattr(event, "error_code", None),
                    error_message=getattr(event, "error_message", None),
                )
                break

    def _find_parent_span_id(self, run_id: str) -> str | None:
        spans = self._spans.get(run_id, [])
        if not spans:
            return None
        # 最近的 span 作为 parent
        return spans[-1].span_id

    # ── Handler dispatch table ──────────────────────────────────────

    _HANDLERS = {
        "run.started": _handle_run_started,
        "run.completed": _handle_run_completed,
        "run.failed": _handle_run_failed,
        "run.cancelled": _handle_run_cancelled,
        "agent.started": _handle_agent_started,
        "agent.completed": _handle_agent_completed,
        "agent.turn_started": _handle_turn_started,
        "agent.turn_completed": _handle_turn_completed,
        "llm.call_started": _handle_llm_started,
        "llm.call_completed": _handle_llm_completed,
        "llm.call_failed": _handle_llm_failed,
        "tool.call_started": _handle_tool_started,
        "tool.call_completed": _handle_tool_completed,
        "tool.call_failed": _handle_tool_failed,
        "guardrail.evaluated": _handle_guardrail_evaluated,
        "guardrail.blocked": _handle_guardrail_blocked,
        "handoff.started": _handle_handoff_started,
        "handoff.completed": _handle_handoff_completed,
        "delegation.started": _handle_delegation_started,
        "delegation.completed": _handle_delegation_completed,
    }


__all__ = ["TraceProjector"]
