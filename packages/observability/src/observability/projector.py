"""TraceProjector — pure projection from RuntimeEvent v2 to Trace.

核心原则 (Phase 4 rewrite):
- TraceProjector 不生成 span_id / parent_span_id / run_id / trace_id
- 所有 identity 来自 RuntimeEvent（Runtime 是唯一创建者）
- span_id 用作 Started/Completed/Failed 之间的 correlation id
- SpanKind 映射明确化，禁止统一 kind="internal"
- malformed event 不能 silent drop，需记录计数

用法：

    projector = TraceProjector(publisher, settings)
    bus.subscribe(projector.handle)

当收到 RunCompleted / RunFailed / RunCancelled 时，构建 TraceEnvelope 并提交。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

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


# ── Event type → SpanKind mapping (4.2) ────────────────────────────

_EVENT_SPAN_KIND: dict[str, str] = {
    "run.started": "RUN",
    "run.completed": "RUN",
    "run.failed": "RUN",
    "run.cancelled": "RUN",
    "agent.started": "AGENT",
    "agent.completed": "AGENT",
    "agent.turn_started": "AGENT_TURN",
    "agent.turn_completed": "AGENT_TURN",
    "llm.call_started": "LLM_CALL",
    "llm.call_completed": "LLM_CALL",
    "llm.call_failed": "LLM_CALL",
    "tool.call_started": "TOOL_CALL",
    "tool.call_completed": "TOOL_CALL",
    "tool.call_failed": "TOOL_CALL",
    "retrieval.started": "RETRIEVAL",
    "retrieval.completed": "RETRIEVAL",
    "retrieval.failed": "RETRIEVAL",
    "guardrail.evaluated": "GUARDRAIL",
    "guardrail.blocked": "GUARDRAIL",
    "handoff.started": "HANDOFF",
    "handoff.completed": "HANDOFF",
    "delegation.started": "DELEGATION",
    "delegation.completed": "DELEGATION",
}


class TraceProjector:
    """Pure projection: RuntimeEvent → TraceEnvelope.

    不生成任何 identity。span_id / parent_span_id / run_id / trace_id
    全部来自事件本身。span_id 用于 Started/Completed/Failed 之间的 correlation。
    """

    def __init__(
        self,
        publisher: AsyncTracePublisher,
        settings: ObservabilitySettings,
    ) -> None:
        self._publisher = publisher
        self._settings = settings
        # run_id → {span_id → SpanEnvelope} — open spans indexed by span_id
        self._open_spans: dict[str, dict[str, SpanEnvelope]] = {}
        # run_id → completed spans
        self._spans: dict[str, list[SpanEnvelope]] = {}
        # run_id → metadata
        self._run_meta: dict[str, dict[str, Any]] = {}
        # run_id → trace_id
        self._trace_ids: dict[str, str] = {}
        # Malformed event counters (4.9)
        self._unknown_event_count = 0
        self._malformed_event_count = 0
        self._orphan_completion_count = 0
        self._duplicate_span_start_count = 0

    async def handle(self, event: Any) -> None:
        """EventBus listener — process all v2 semantic events."""
        event_type = getattr(event, "event_type", None)
        if event_type is None or not isinstance(event_type, str):
            return

        run_id = getattr(event, "run_id", "")
        if not run_id:
            self._malformed_event_count += 1
            return

        handler = self._HANDLERS.get(event_type)
        if handler is not None:
            handler(self, event, run_id)
        else:
            self._unknown_event_count += 1

    # ── Run lifecycle ───────────────────────────────────────────────

    def _handle_run_started(self, event: Any, run_id: str) -> None:
        trace_id = getattr(event, "trace_id", "")
        if not trace_id:
            self._malformed_event_count += 1
            return
        self._trace_ids[run_id] = trace_id
        self._spans[run_id] = []
        self._open_spans[run_id] = {}
        self._run_meta[run_id] = {
            "agent_key": getattr(event, "agent_key", ""),
            "session_id": getattr(event, "session_id", ""),
            "started_at": _to_utc(getattr(event, "timestamp", None)),
        }

        # Create root span using event's span_id (4.1)
        span_id = getattr(event, "span_id", None)
        if span_id is None:
            self._malformed_event_count += 1
            return

        root = SpanEnvelope(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=getattr(event, "parent_span_id", None),
            name="agent.run",
            kind="RUN",
            status="ok",
            instrumentation_scope="trace_projector",
            started_at_utc=_to_utc(getattr(event, "timestamp", None)),
            completed_at_utc=_to_utc(getattr(event, "timestamp", None)),
            duration_ms=0,
            attributes=bounded_attributes(
                {
                    "agentlabkit.trace.root": True,
                    "agentlabkit.run_id": run_id,
                    "agentlabkit.agent_key": getattr(event, "agent_key", ""),
                },
                max_bytes=self._settings.max_attribute_bytes,
            ),
        )
        self._open_spans[run_id][span_id] = root

    def _handle_run_completed(self, event: Any, run_id: str) -> None:
        self._finalize_run(run_id, event, status="ok")

    def _handle_run_failed(self, event: Any, run_id: str) -> None:
        self._finalize_run(run_id, event, status="error")

    def _handle_run_cancelled(self, event: Any, run_id: str) -> None:
        self._finalize_run(run_id, event, status="cancelled")

    def _finalize_run(self, run_id: str, event: Any, status: TraceStatus) -> None:
        trace_id = self._trace_ids.pop(run_id, "")
        open_spans = self._open_spans.pop(run_id, {})
        completed_spans = self._spans.pop(run_id, [])
        meta = self._run_meta.pop(run_id, {})

        if not trace_id:
            return

        # Close any remaining open spans (4.3)
        for span_id, span in open_spans.items():
            if len(completed_spans) < self._settings.max_spans_per_trace:
                completed_spans.append(_close_span(span, event, status))

        # Update root span status (4.3)
        root_span_id = getattr(event, "span_id", None)
        root = None
        for s in completed_spans:
            if s.span_id == root_span_id:
                root = s
                break
        if root is None and completed_spans:
            root = completed_spans[0]

        if root is None:
            return

        completed_at = _to_utc(getattr(event, "timestamp", None))
        started_at = meta.get("started_at", completed_at)
        duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))

        # Update root span with final status
        root_idx = completed_spans.index(root)
        completed_spans[root_idx] = SpanEnvelope(
            span_id=root.span_id,
            trace_id=root.trace_id,
            parent_span_id=root.parent_span_id,
            name=root.name,
            kind=root.kind,
            status=status,
            instrumentation_scope=root.instrumentation_scope,
            started_at_utc=root.started_at_utc,
            completed_at_utc=completed_at,
            duration_ms=duration_ms,
            attributes=root.attributes,
            events=root.events,
            links=root.links,
            error_code=getattr(event, "error_code", None),
            error_message=getattr(event, "error_message", None),
        )

        # Aggregate tokens
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
            span_count=len(completed_spans),
            spans=sorted(completed_spans, key=lambda s: (s.started_at_utc, s.span_id)),
        )

        try:
            self._publisher.submit_nowait(envelope)
        except Exception:
            logger.exception("projector.submit_failed run_id=%s", run_id)

    # ── Agent lifecycle ─────────────────────────────────────────────

    def _handle_agent_started(self, event: Any, run_id: str) -> None:
        self._open_span(run_id, event, name="agent.process", attributes={
            "agent.key": getattr(event, "agent_key", ""),
        })

    def _handle_agent_completed(self, event: Any, run_id: str) -> None:
        self._close_span_by_id(run_id, event)

    def _handle_turn_started(self, event: Any, run_id: str) -> None:
        self._open_span(run_id, event, name="agent.turn", attributes={
            "turn.index": getattr(event, "turn_index", 0),
        })

    def _handle_turn_completed(self, event: Any, run_id: str) -> None:
        self._close_span_by_id(run_id, event)

    # ── LLM calls ───────────────────────────────────────────────────

    def _handle_llm_started(self, event: Any, run_id: str) -> None:
        self._open_span(run_id, event, name="llm.generate", attributes={
            "gen_ai.request.model": getattr(event, "model", ""),
            "gen_ai.system": getattr(event, "provider", ""),
        })

    def _handle_llm_completed(self, event: Any, run_id: str) -> None:
        """Close LLM span and inject usage attributes (4.5)."""
        span = self._close_span_by_id(run_id, event)
        if span is not None:
            # Enrich with usage data
            attrs = dict(span.attributes)
            attrs["gen_ai.usage.input_tokens"] = getattr(event, "input_tokens", 0)
            attrs["gen_ai.usage.output_tokens"] = getattr(event, "output_tokens", 0)
            attrs["gen_ai.usage.cache_write_tokens"] = getattr(event, "cache_write_tokens", 0)
            attrs["gen_ai.usage.cache_read_tokens"] = getattr(event, "cache_read_tokens", 0)
            attrs["gen_ai.usage.estimated_cost"] = getattr(event, "estimated_cost", 0.0)
            attrs["gen_ai.usage.finish_reason"] = getattr(event, "finish_reason", "")
            attrs["gen_ai.usage.latency_ms"] = getattr(event, "latency_ms", 0)
            # Replace in completed list
            spans = self._spans.get(run_id, [])
            for i, s in enumerate(spans):
                if s.span_id == span.span_id:
                    spans[i] = SpanEnvelope(
                        span_id=s.span_id,
                        trace_id=s.trace_id,
                        parent_span_id=s.parent_span_id,
                        name=s.name,
                        kind=s.kind,
                        status=s.status,
                        instrumentation_scope=s.instrumentation_scope,
                        started_at_utc=s.started_at_utc,
                        completed_at_utc=s.completed_at_utc,
                        duration_ms=s.duration_ms,
                        attributes=bounded_attributes(attrs, max_bytes=self._settings.max_attribute_bytes),
                        events=s.events,
                        links=s.links,
                        error_code=s.error_code,
                        error_message=s.error_message,
                    )
                    break

    def _handle_llm_failed(self, event: Any, run_id: str) -> None:
        self._close_span_by_id(run_id, event, error=True)

    # ── Tool calls ──────────────────────────────────────────────────

    def _handle_tool_started(self, event: Any, run_id: str) -> None:
        self._open_span(run_id, event, name=f"tool.{getattr(event, 'tool_name', 'unknown')}", attributes={
            "tool.name": getattr(event, "tool_name", ""),
            "tool.source_type": getattr(event, "source_type", ""),
            "tool.arguments": str(getattr(event, "arguments", ""))[:500],
        })

    def _handle_tool_completed(self, event: Any, run_id: str) -> None:
        """Close tool span. is_error=True → error status (4.4)."""
        is_error = getattr(event, "is_error", False)
        span = self._close_span_by_id(run_id, event, error=is_error)
        if span is not None:
            attrs = dict(span.attributes)
            attrs["tool.result"] = str(getattr(event, "result", ""))[:500]
            attrs["tool.is_error"] = is_error
            attrs["tool.duration_ms"] = getattr(event, "duration_ms", 0)
            spans = self._spans.get(run_id, [])
            for i, s in enumerate(spans):
                if s.span_id == span.span_id:
                    status: TraceStatus = "error" if is_error else "ok"
                    spans[i] = SpanEnvelope(
                        span_id=s.span_id,
                        trace_id=s.trace_id,
                        parent_span_id=s.parent_span_id,
                        name=s.name,
                        kind=s.kind,
                        status=status,
                        instrumentation_scope=s.instrumentation_scope,
                        started_at_utc=s.started_at_utc,
                        completed_at_utc=s.completed_at_utc,
                        duration_ms=s.duration_ms,
                        attributes=bounded_attributes(attrs, max_bytes=self._settings.max_attribute_bytes),
                        events=s.events,
                        links=s.links,
                        error_code=s.error_code,
                        error_message=s.error_message,
                    )
                    break

    def _handle_tool_failed(self, event: Any, run_id: str) -> None:
        self._close_span_by_id(run_id, event, error=True)

    # ── Retrieval (4.6) ─────────────────────────────────────────────

    def _handle_retrieval_started(self, event: Any, run_id: str) -> None:
        self._open_span(run_id, event, name="retrieval.query", attributes={
            "retrieval.query": str(getattr(event, "query", ""))[:200],
            "retrieval.source": getattr(event, "source", ""),
            "retrieval.knowledge_base_ids": list(getattr(event, "knowledge_base_ids", ())),
            "retrieval.top_k": getattr(event, "top_k", None),
            "retrieval.search_mode": getattr(event, "search_mode", None),
        })

    def _handle_retrieval_completed(self, event: Any, run_id: str) -> None:
        span = self._close_span_by_id(run_id, event)
        if span is not None:
            attrs = dict(span.attributes)
            attrs["retrieval.result_count"] = getattr(event, "result_count", 0)
            attrs["retrieval.duration_ms"] = getattr(event, "duration_ms", 0)
            attrs["retrieval.results"] = [
                {
                    "knowledge_base_id": ref.knowledge_base_id,
                    "document_id": ref.document_id,
                    "segment_id": ref.segment_id,
                    "score": ref.score,
                    "title": ref.title,
                    "source": ref.source,
                    "content_preview": ref.content_preview,
                }
                for ref in getattr(event, "results", ())
            ]
            spans = self._spans.get(run_id, [])
            for i, s in enumerate(spans):
                if s.span_id == span.span_id:
                    spans[i] = SpanEnvelope(
                        span_id=s.span_id,
                        trace_id=s.trace_id,
                        parent_span_id=s.parent_span_id,
                        name=s.name,
                        kind=s.kind,
                        status=s.status,
                        instrumentation_scope=s.instrumentation_scope,
                        started_at_utc=s.started_at_utc,
                        completed_at_utc=s.completed_at_utc,
                        duration_ms=s.duration_ms,
                        attributes=bounded_attributes(attrs, max_bytes=self._settings.max_attribute_bytes),
                        events=s.events,
                        links=s.links,
                    )
                    break

    def _handle_retrieval_failed(self, event: Any, run_id: str) -> None:
        span = self._close_span_by_id(run_id, event, error=True)
        if span is not None:
            self._update_completed_span(
                run_id,
                span.span_id,
                attributes={"retrieval.error_message": str(getattr(event, "error_message", ""))[:500]},
                status="error",
            )

    # ── Guardrails (4.7) ────────────────────────────────────────────

    def _handle_guardrail_evaluated(self, event: Any, run_id: str) -> None:
        allowed = getattr(event, "allowed", getattr(event, "passed", True))
        self._open_span(run_id, event, name=f"guardrail.{getattr(event, 'guardrail_name', 'unknown')}", attributes={
            "guardrail.name": getattr(event, "guardrail_name", ""),
            "guardrail.type": getattr(event, "guardrail_type", ""),
            "guardrail.allowed": allowed,
            "guardrail.passed": getattr(event, "passed", allowed),
            "guardrail.reason": getattr(event, "reason", ""),
        })
        # GuardrailEvaluated is a point event — close immediately
        self._close_span_by_id(run_id, event)

    def _handle_guardrail_blocked(self, event: Any, run_id: str) -> None:
        """Enrich the evaluation span; blocking is not a second operation.

        A blocked guardrail emits both ``guardrail.evaluated`` and
        ``guardrail.blocked`` with the same span identity.  The latter is a
        semantic event about the already completed evaluation, not another
        span lifecycle.  In particular, a block is an expected guardrail
        outcome and must not be represented as a span error.
        """
        self._update_completed_span(
            run_id,
            getattr(event, "span_id", None),
            attributes={
                "guardrail.allowed": False,
                "guardrail.blocked": True,
                "guardrail.action": getattr(event, "action", ""),
                "guardrail.reason": getattr(event, "reason", ""),
            },
        )

    # ── Multi-agent ─────────────────────────────────────────────────

    def _handle_handoff_started(self, event: Any, run_id: str) -> None:
        self._open_span(run_id, event, name="handoff", attributes={
            "handoff.source": getattr(event, "source_agent", ""),
            "handoff.target": getattr(event, "target_agent", ""),
            "handoff.reason": getattr(event, "reason", ""),
        })

    def _handle_handoff_completed(self, event: Any, run_id: str) -> None:
        self._close_span_by_id(run_id, event)

    def _handle_delegation_started(self, event: Any, run_id: str) -> None:
        self._open_span(run_id, event, name="delegation", attributes={
            "delegation.agent": getattr(event, "target_agent", ""),
            "delegation.tool": getattr(event, "tool_name", ""),
        })

    def _handle_delegation_completed(self, event: Any, run_id: str) -> None:
        self._close_span_by_id(run_id, event)

    # ── Internal helpers ────────────────────────────────────────────

    def _open_span(
        self,
        run_id: str,
        event: Any,
        *,
        name: str,
        status: TraceStatus = "ok",
        attributes: dict[str, Any] | None = None,
    ) -> SpanEnvelope | None:
        """Open a new span using event's span_id (4.1)."""
        span_id = getattr(event, "span_id", None)
        if span_id is None:
            self._malformed_event_count += 1
            return None

        trace_id = self._trace_ids.get(run_id, "")
        if not trace_id:
            return None

        # Check for duplicate span_id (4.9)
        open_spans = self._open_spans.get(run_id, {})
        if span_id in open_spans:
            self._duplicate_span_start_count += 1
            logger.warning("projector.duplicate_span_start run_id=%s span_id=%s", run_id, span_id)

        ts = _to_utc(getattr(event, "timestamp", None))
        kind = _EVENT_SPAN_KIND.get(getattr(event, "event_type", ""), "CUSTOM")

        attrs = bounded_attributes(
            attributes or {},
            max_bytes=self._settings.max_attribute_bytes,
        )

        span = SpanEnvelope(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=getattr(event, "parent_span_id", None),
            name=name[:256],
            kind=kind,
            status=status,
            instrumentation_scope="trace_projector",
            started_at_utc=ts,
            completed_at_utc=ts,
            duration_ms=0,
            attributes=attrs,
        )

        if open_spans is not None:
            open_spans[span_id] = span
        return span

    def _update_completed_span(
        self,
        run_id: str,
        span_id: str | None,
        *,
        attributes: dict[str, Any] | None = None,
        status: TraceStatus | None = None,
    ) -> SpanEnvelope | None:
        """Update an existing completed span without appending another one."""
        if span_id is None:
            self._malformed_event_count += 1
            return None

        spans = self._spans.get(run_id, [])
        for index, span in enumerate(spans):
            if span.span_id != span_id:
                continue
            merged_attributes = dict(span.attributes)
            merged_attributes.update(attributes or {})
            updated = SpanEnvelope(
                span_id=span.span_id,
                trace_id=span.trace_id,
                parent_span_id=span.parent_span_id,
                name=span.name,
                kind=span.kind,
                status=status or span.status,
                instrumentation_scope=span.instrumentation_scope,
                started_at_utc=span.started_at_utc,
                completed_at_utc=span.completed_at_utc,
                duration_ms=span.duration_ms,
                attributes=bounded_attributes(
                    merged_attributes,
                    max_bytes=self._settings.max_attribute_bytes,
                ),
                events=span.events,
                links=span.links,
                error_code=span.error_code,
                error_message=span.error_message,
            )
            spans[index] = updated
            return updated
        return None

    def _close_span_by_id(
        self,
        run_id: str,
        event: Any,
        *,
        error: bool = False,
    ) -> SpanEnvelope | None:
        """Close span by event.span_id correlation (4.3)."""
        span_id = getattr(event, "span_id", None)
        if span_id is None:
            self._malformed_event_count += 1
            return None

        open_spans = self._open_spans.get(run_id, {})
        span = open_spans.pop(span_id, None)
        if span is None:
            self._orphan_completion_count += 1
            logger.warning("projector.orphan_completion run_id=%s span_id=%s", run_id, span_id)
            return None

        closed = _close_span(span, event, "error" if error else "ok")
        spans = self._spans.get(run_id)
        if spans is not None and len(spans) < self._settings.max_spans_per_trace:
            spans.append(closed)
        return closed

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
        "retrieval.started": _handle_retrieval_started,
        "retrieval.completed": _handle_retrieval_completed,
        "retrieval.failed": _handle_retrieval_failed,
        "guardrail.evaluated": _handle_guardrail_evaluated,
        "guardrail.blocked": _handle_guardrail_blocked,
        "handoff.started": _handle_handoff_started,
        "handoff.completed": _handle_handoff_completed,
        "delegation.started": _handle_delegation_started,
        "delegation.completed": _handle_delegation_completed,
    }


def _close_span(span: SpanEnvelope, event: Any, status: TraceStatus) -> SpanEnvelope:
    """Create a closed copy of a span."""
    completed_at = _to_utc(getattr(event, "timestamp", None))
    started_at = span.started_at_utc
    duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
    return SpanEnvelope(
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


__all__ = ["TraceProjector"]
