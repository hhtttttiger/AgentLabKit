from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.trace import StatusCode

from .config import ObservabilitySettings
from .contracts import SpanEnvelope, TraceEnvelope, TraceStatus
from .publisher import AsyncTracePublisher
from .sanitizer import bounded_attributes

logger = logging.getLogger(__name__)

_ROOT_ATTRIBUTE = "agentlabkit.trace.root"
_BUFFER_TTL_SECONDS = 600


class TraceBufferSpanProcessor(SpanProcessor):
    """Collect completed spans and publish one bounded envelope per agent trace."""

    def __init__(self, publisher: AsyncTracePublisher, settings: ObservabilitySettings) -> None:
        self._publisher = publisher
        self._settings = settings
        self._spans: dict[str, list[SpanEnvelope]] = defaultdict(list)
        self._first_seen: dict[str, float] = {}
        self._dropped: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self._next_prune_at = time.monotonic() + 60
        self._max_active_traces = settings.publisher_queue_capacity
        self._buffer_overflow_dropped = 0

    def on_start(self, span: Span, parent_context=None) -> None:  # noqa: ANN001
        return

    def on_end(self, span: ReadableSpan) -> None:
        if not self._settings.enabled or not span.context:
            return
        trace_id = format(span.context.trace_id, "032x")
        envelope_span = self._convert_span(span)
        attrs = dict(span.attributes or {})
        completed: list[SpanEnvelope] | None = None
        dropped = 0
        with self._lock:
            overflow = (
                trace_id not in self._spans
                and len(self._spans) >= self._max_active_traces
            )
            if overflow:
                self._buffer_overflow_dropped += 1
                if attrs.get(_ROOT_ATTRIBUTE) is True:
                    completed = [envelope_span]
                    dropped = 1
            else:
                self._first_seen.setdefault(trace_id, time.monotonic())
                self._retain_span(trace_id, envelope_span)
            if not overflow and attrs.get(_ROOT_ATTRIBUTE) is True:
                completed = self._spans.pop(trace_id, [])
                self._first_seen.pop(trace_id, None)
                dropped = self._dropped.pop(trace_id, 0)
        if completed is not None:
            envelope = self._build_trace(span, completed, dropped)
            if envelope is not None:
                self._publisher.submit_nowait(envelope)
        if time.monotonic() >= self._next_prune_at:
            self._prune_stale()

    def shutdown(self) -> None:
        with self._lock:
            self._spans.clear()
            self._first_seen.clear()
            self._dropped.clear()

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        del timeout_millis
        return True

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "active_traces": len(self._spans),
                "buffered_spans": sum(len(spans) for spans in self._spans.values()),
                "buffer_overflow_dropped": self._buffer_overflow_dropped,
            }

    def _retain_span(self, trace_id: str, span: SpanEnvelope) -> None:
        spans = self._spans[trace_id]
        hard_limit = self._settings.max_spans_per_trace
        if len(spans) < hard_limit:
            spans.append(span)
            return

        priority = _span_priority(span)
        replace_index = next(
            (index for index, current in enumerate(spans) if _span_priority(current) < priority),
            None,
        )
        if replace_index is not None:
            spans[replace_index] = span
        self._dropped[trace_id] += 1

    def _build_trace(
        self,
        root: ReadableSpan,
        spans: list[SpanEnvelope],
        dropped: int,
    ) -> TraceEnvelope | None:
        raw_attrs = dict(root.attributes or {})
        attrs = bounded_attributes(
            raw_attrs,
            max_bytes=self._settings.max_attribute_bytes,
        )
        status = _trace_status(root, raw_attrs)
        duration_ms = _duration_ms(root.start_time, root.end_time)
        reason = _sample_reason(status, duration_ms, self._settings.slow_trace_threshold_ms)
        trace_id = format(root.context.trace_id, "032x")
        if reason == "normal" and not _deterministic_sample(trace_id, self._settings.normal_sample_rate):
            return None

        input_tokens = output_tokens = cache_write = cache_read = 0
        cost = Decimal("0")
        for child in spans:
            if child.name != "llm.generate":
                continue
            input_tokens += _as_int(child.attributes.get("gen_ai.usage.input_tokens"))
            output_tokens += _as_int(child.attributes.get("gen_ai.usage.output_tokens"))
            cache_write += _as_int(child.attributes.get("gen_ai.usage.cache_write_tokens"))
            cache_read += _as_int(child.attributes.get("gen_ai.usage.cache_read_tokens"))
            cost += _as_decimal(child.attributes.get("gen_ai.usage.estimated_cost"))

        envelope = TraceEnvelope(
            trace_id=trace_id,
            root_span_id=format(root.context.span_id, "016x"),
            run_id=str(raw_attrs.get("agentlabkit.run_id") or ""),
            agent_key=_optional_str(raw_attrs.get("agentlabkit.agent_key")),
            session_id=_optional_str(raw_attrs.get("agentlabkit.session_id")),
            user_id=_optional_str(raw_attrs.get("agentlabkit.user_id")),
            correlation_id=_optional_str(raw_attrs.get("agentlabkit.correlation_id")),
            status=status,
            started_at_utc=_to_datetime(root.start_time),
            completed_at_utc=_to_datetime(root.end_time),
            total_duration_ms=duration_ms,
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            cache_write_tokens=cache_write,
            cache_read_tokens=cache_read,
            total_estimated_cost=cost,
            span_count=len(spans),
            dropped_span_count=dropped,
            sample_reason=reason,
            attributes=attrs,
            spans=sorted(spans, key=lambda item: (item.started_at_utc, item.span_id)),
        )
        return self._fit_envelope(envelope)

    def _fit_envelope(self, envelope: TraceEnvelope) -> TraceEnvelope:
        max_bytes = self._settings.max_envelope_bytes
        serialized = envelope.model_dump_json().encode("utf-8")
        if len(serialized) <= max_bytes:
            return envelope

        empty = envelope.model_copy(update={"spans": [], "span_count": 0})
        used = len(empty.model_dump_json().encode("utf-8"))
        kept: list[SpanEnvelope] = []
        dropped = envelope.dropped_span_count
        ranked = sorted(
            envelope.spans,
            key=lambda item: (
                -_span_priority(item),
                item.started_at_utc,
                item.span_id,
            ),
        )
        for original_span in ranked:
            span = original_span
            span_size = len(span.model_dump_json().encode("utf-8")) + 1
            if (
                span.span_id == envelope.root_span_id
                and used + span_size > max_bytes
            ):
                span = span.model_copy(
                    update={"events": [], "links": [], "attributes": {}},
                )
                span_size = len(span.model_dump_json().encode("utf-8")) + 1
            if used + span_size <= max_bytes:
                kept.append(span)
                used += span_size
            else:
                dropped += 1

        kept.sort(key=lambda item: (item.started_at_utc, item.span_id))
        fitted = envelope.model_copy(
            update={
                "spans": kept,
                "span_count": len(kept),
                "dropped_span_count": dropped,
            },
        )
        while kept and len(fitted.model_dump_json().encode("utf-8")) > max_bytes:
            removable = min(kept, key=_span_priority)
            kept.remove(removable)
            dropped += 1
            fitted = fitted.model_copy(
                update={
                    "spans": kept,
                    "span_count": len(kept),
                    "dropped_span_count": dropped,
                },
            )
        return fitted

    def _convert_span(self, span: ReadableSpan) -> SpanEnvelope:
        attrs = dict(span.attributes or {})
        if self._settings.capture_mode == "off":
            attrs = {
                key: value
                for key, value in attrs.items()
                if not any(token in key.lower() for token in ("prompt", "preview", "arguments", "result"))
            }
        attrs = bounded_attributes(attrs, max_bytes=self._settings.max_attribute_bytes)

        events = [
            {
                "name": event.name,
                "timestamp": _to_datetime(event.timestamp).isoformat(),
                "attributes": bounded_attributes(
                    dict(event.attributes or {}),
                    max_bytes=self._settings.max_attribute_bytes,
                ),
            }
            for event in span.events[-25:]
        ]
        links = [
            {
                "trace_id": format(link.context.trace_id, "032x"),
                "span_id": format(link.context.span_id, "016x"),
                "attributes": bounded_attributes(
                    dict(link.attributes or {}),
                    max_bytes=self._settings.max_attribute_bytes,
                ),
            }
            for link in span.links[:25]
        ]
        error_message = None
        error_code = None
        for event in events:
            if event["name"] == "exception":
                event_attrs = event["attributes"]
                error_message = _optional_str(event_attrs.get("exception.message"))
                error_code = _optional_str(event_attrs.get("exception.type"))
                break

        return SpanEnvelope(
            span_id=format(span.context.span_id, "016x"),
            trace_id=format(span.context.trace_id, "032x"),
            parent_span_id=format(span.parent.span_id, "016x") if span.parent else None,
            name=span.name[:256],
            kind=getattr(span.kind, "name", str(span.kind)).lower(),
            status=_trace_status(span, attrs),
            instrumentation_scope=(
                getattr(span.instrumentation_scope, "name", "") or ""
            )[:256],
            started_at_utc=_to_datetime(span.start_time),
            completed_at_utc=_to_datetime(span.end_time),
            duration_ms=_duration_ms(span.start_time, span.end_time),
            attributes=attrs,
            events=events,
            links=links,
            error_code=error_code,
            error_message=error_message,
        )

    def _prune_stale(self) -> None:
        now = time.monotonic()
        self._next_prune_at = now + 60
        with self._lock:
            stale = [
                trace_id
                for trace_id, started in self._first_seen.items()
                if now - started > _BUFFER_TTL_SECONDS
            ]
            stale_counts = []
            for trace_id in stale:
                stale_counts.append((trace_id, len(self._spans.pop(trace_id, []))))
                self._first_seen.pop(trace_id, None)
                self._dropped.pop(trace_id, None)
        for trace_id, dropped in stale_counts:
            logger.warning("trace_buffer.stale_trace_dropped trace_id=%s spans=%d", trace_id, dropped)


def _trace_status(span: ReadableSpan, attrs: dict[str, Any]) -> TraceStatus:
    explicit = attrs.get("agentlabkit.status")
    if explicit in {"ok", "error", "timeout", "cancelled"}:
        return explicit
    if span.status.status_code is StatusCode.ERROR:
        return "error"
    return "ok"


def _sample_reason(status: TraceStatus, duration_ms: int, slow_ms: int) -> str:
    if status != "ok":
        return status
    if duration_ms >= slow_ms:
        return "slow"
    return "normal"


def _deterministic_sample(trace_id: str, rate: float) -> bool:
    if rate >= 1:
        return True
    if rate <= 0:
        return False
    return int(trace_id[-8:], 16) / 0xFFFFFFFF < rate


def _span_priority(span: SpanEnvelope) -> int:
    if span.name == "agent.run":
        return 100
    if span.status != "ok":
        return 90
    if span.name in {"llm.generate", "tool.execute", "llm_gateway.request"}:
        return 70
    return 10


def _duration_ms(start_ns: int | None, end_ns: int | None) -> int:
    if start_ns is None or end_ns is None:
        return 0
    return max(0, int((end_ns - start_ns) / 1_000_000))


def _to_datetime(timestamp_ns: int | None) -> datetime:
    if timestamp_ns is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, timezone.utc)


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _optional_str(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


__all__ = ["TraceBufferSpanProcessor"]
