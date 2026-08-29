"""Trace envelope 构建测试 — Phase 0 安全网。

覆盖：root span 检测、token 聚合、_convert_span、priority 驱动的 span 保留、envelope 大小裁剪。
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from opentelemetry.trace import StatusCode

from observability.config import ObservabilitySettings
from observability.span_processor import TraceBufferSpanProcessor
from observability.contracts import SpanEnvelope


def _make_settings(**overrides) -> ObservabilitySettings:
    defaults = dict(
        enabled=True,
        max_spans_per_trace=100,
        max_attribute_bytes=4096,
        max_envelope_bytes=65536,
        publisher_queue_capacity=1000,
        slow_trace_threshold_ms=5000,
        normal_sample_rate=1.0,
    )
    defaults.update(overrides)
    return ObservabilitySettings(**defaults)


def _make_publisher() -> MagicMock:
    publisher = MagicMock()
    publisher.submit_nowait = MagicMock()
    return publisher


def _make_span(
    trace_id: int = 0xABCDEF1234567890ABCDEF1234567890,
    span_id: int = 0x1234567890ABCDEF,
    parent_span_id: int | None = None,
    name: str = "test.span",
    status_code: StatusCode = StatusCode.UNSET,
    start_time: int = 1_000_000_000_000,  # 1s in ns
    end_time: int = 2_000_000_000_000,    # 2s in ns
    attributes: dict | None = None,
    events: list | None = None,
) -> MagicMock:
    """构造一个模拟的 OTel ReadableSpan。"""
    span = MagicMock()
    span.context.trace_id = trace_id
    span.context.span_id = span_id
    # parent 需要是 None 或有 span_id 属性的对象
    if parent_span_id is not None:
        parent = MagicMock()
        parent.span_id = parent_span_id
        span.parent = parent
    else:
        span.parent = None
    span.name = name
    span.kind.name = "INTERNAL"
    span.status.status_code = status_code
    span.start_time = start_time
    span.end_time = end_time
    span.attributes = attributes or {}
    span.events = events or []
    span.links = []
    span.instrumentation_scope.name = "test"
    return span


# ── root span 检测 ─────────────────────────────────────────────────


class TestRootSpanDetection:
    def test_root_span_triggers_envelope_publish(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        root = _make_span(
            attributes={"agentlabkit.trace.root": True, "agentlabkit.run_id": "550e8400-e29b-41d4-a716-446655440000"},
        )
        processor.on_end(root)

        publisher.submit_nowait.assert_called_once()
        envelope = publisher.submit_nowait.call_args[0][0]
        assert envelope.trace_id == format(0xABCDEF1234567890ABCDEF1234567890, "032x")
        assert envelope.span_count == 1

    def test_non_root_span_does_not_publish(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        child = _make_span(name="llm.generate")
        processor.on_end(child)

        publisher.submit_nowait.assert_not_called()
        assert processor.snapshot()["buffered_spans"] == 1

    def test_child_spans_collected_before_root(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        trace_id = 0xABCDEF1234567890ABCDEF1234567890
        # 先发 child spans
        child1 = _make_span(trace_id=trace_id, span_id=0x1111, name="llm.generate")
        child2 = _make_span(trace_id=trace_id, span_id=0x2222, name="tool.execute")
        processor.on_end(child1)
        processor.on_end(child2)

        # 再发 root
        root = _make_span(
            trace_id=trace_id,
            span_id=0x3333,
            attributes={"agentlabkit.trace.root": True, "agentlabkit.run_id": "550e8400-e29b-41d4-a716-446655440000"},
        )
        processor.on_end(root)

        envelope = publisher.submit_nowait.call_args[0][0]
        assert envelope.span_count == 3  # root + 2 children


# ── token 聚合 ─────────────────────────────────────────────────────


class TestTokenAggregation:
    def test_tokens_aggregated_from_llm_spans(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        trace_id = 0xABCDEF1234567890ABCDEF1234567890
        # LLM span 1
        llm1 = _make_span(
            trace_id=trace_id,
            span_id=0x1111,
            name="llm.generate",
            attributes={
                "gen_ai.usage.input_tokens": 100,
                "gen_ai.usage.output_tokens": 50,
                "gen_ai.usage.estimated_cost": 0.005,
            },
        )
        # LLM span 2
        llm2 = _make_span(
            trace_id=trace_id,
            span_id=0x2222,
            name="llm.generate",
            attributes={
                "gen_ai.usage.input_tokens": 200,
                "gen_ai.usage.output_tokens": 80,
                "gen_ai.usage.estimated_cost": 0.012,
            },
        )
        processor.on_end(llm1)
        processor.on_end(llm2)

        root = _make_span(
            trace_id=trace_id,
            span_id=0x3333,
            attributes={"agentlabkit.trace.root": True, "agentlabkit.run_id": "550e8400-e29b-41d4-a716-446655440000"},
        )
        processor.on_end(root)

        envelope = publisher.submit_nowait.call_args[0][0]
        assert envelope.total_input_tokens == 300
        assert envelope.total_output_tokens == 130
        assert envelope.total_estimated_cost == Decimal("0.017")

    def test_non_llm_spans_do_not_contribute_tokens(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        trace_id = 0xABCDEF1234567890ABCDEF1234567890
        tool_span = _make_span(
            trace_id=trace_id,
            span_id=0x1111,
            name="tool.execute",
            attributes={"gen_ai.usage.input_tokens": 999},  # 应该被忽略
        )
        processor.on_end(tool_span)

        root = _make_span(
            trace_id=trace_id,
            span_id=0x2222,
            attributes={"agentlabkit.trace.root": True, "agentlabkit.run_id": "550e8400-e29b-41d4-a716-446655440000"},
        )
        processor.on_end(root)

        envelope = publisher.submit_nowait.call_args[0][0]
        assert envelope.total_input_tokens == 0


# ── _convert_span ──────────────────────────────────────────────────


class TestConvertSpan:
    def test_basic_conversion(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        span = _make_span(
            name="tool.execute",
            attributes={"tool.name": "search"},
        )
        envelope_span = processor._convert_span(span)

        assert envelope_span.name == "tool.execute"
        assert envelope_span.attributes["tool.name"] == "search"
        assert envelope_span.kind == "internal"

    def test_error_event_extracted(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        error_event = MagicMock()
        error_event.name = "exception"
        error_event.timestamp = 1_000_000_000
        error_event.attributes = {
            "exception.message": "something failed",
            "exception.type": "RuntimeError",
        }

        span = _make_span(events=[error_event])
        envelope_span = processor._convert_span(span)

        assert envelope_span.error_message == "something failed"
        assert envelope_span.error_code == "RuntimeError"

    def test_capture_mode_off_filters_sensitive_attributes(self) -> None:
        settings = _make_settings(capture_mode="off")
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        span = _make_span(
            attributes={
                "tool.name": "search",
                "gen_ai.prompt": "sensitive data",
                "tool.arguments": '{"key": "secret"}',
            },
        )
        envelope_span = processor._convert_span(span)

        assert "tool.name" in envelope_span.attributes
        assert "gen_ai.prompt" not in envelope_span.attributes
        assert "tool.arguments" not in envelope_span.attributes


# ── priority-based span 保留 ───────────────────────────────────────


class TestSpanRetention:
    def test_higher_priority_replaces_lower(self) -> None:
        settings = _make_settings(max_spans_per_trace=2)
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        trace_id = 0xABCDEF1234567890ABCDEF1234567890
        # 填满 2 个低优先级 span
        low1 = _make_span(trace_id=trace_id, span_id=0x1111, name="custom.span")
        low2 = _make_span(trace_id=trace_id, span_id=0x2222, name="custom.span")
        processor.on_end(low1)
        processor.on_end(low2)

        # 高优先级应该替换一个
        high = _make_span(trace_id=trace_id, span_id=0x3333, name="llm.generate")
        processor.on_end(high)

        snap = processor.snapshot()
        assert snap["buffered_spans"] == 2  # 仍然 2 个
        assert snap["buffer_overflow_dropped"] == 0  # 不是 overflow，是 replacement

    def test_lower_priority_dropped_when_at_limit(self) -> None:
        settings = _make_settings(max_spans_per_trace=2)
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        trace_id = 0xABCDEF1234567890ABCDEF1234567890
        # 填满高优先级
        high1 = _make_span(trace_id=trace_id, span_id=0x1111, name="llm.generate")
        high2 = _make_span(trace_id=trace_id, span_id=0x2222, name="tool.execute")
        processor.on_end(high1)
        processor.on_end(high2)

        # 低优先级应该被丢弃
        low = _make_span(trace_id=trace_id, span_id=0x3333, name="custom.span")
        processor.on_end(low)

        snap = processor.snapshot()
        assert snap["buffered_spans"] == 2


# ── buffer overflow ────────────────────────────────────────────────


class TestBufferOverflow:
    def test_overflow_drops_new_traces(self) -> None:
        settings = _make_settings(publisher_queue_capacity=2)
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        # 填满 2 个 trace
        processor.on_end(_make_span(trace_id=0x1, span_id=0x11, name="a"))
        processor.on_end(_make_span(trace_id=0x2, span_id=0x22, name="b"))

        # 第 3 个 trace 应该被丢弃
        processor.on_end(_make_span(trace_id=0x3, span_id=0x33, name="c"))

        snap = processor.snapshot()
        assert snap["active_traces"] == 2
        assert snap["buffer_overflow_dropped"] == 1

    def test_overflow_root_still_publishes(self) -> None:
        settings = _make_settings(publisher_queue_capacity=1)
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        # 填满 1 个 trace
        processor.on_end(_make_span(trace_id=0x1, span_id=0x11, name="a"))

        # 第 2 个 trace 的 root span 应该直接 publish（不入 buffer）
        root = _make_span(
            trace_id=0x2,
            span_id=0x22,
            attributes={"agentlabkit.trace.root": True, "agentlabkit.run_id": "550e8400-e29b-41d4-a716-446655440000"},
        )
        processor.on_end(root)

        publisher.submit_nowait.assert_called_once()


# ── envelope 状态 ──────────────────────────────────────────────────


class TestEnvelopeStatus:
    def test_error_status_propagated(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        root = _make_span(
            status_code=StatusCode.ERROR,
            attributes={"agentlabkit.trace.root": True, "agentlabkit.run_id": "550e8400-e29b-41d4-a716-446655440000"},
        )
        processor.on_end(root)

        envelope = publisher.submit_nowait.call_args[0][0]
        assert envelope.status == "error"
        assert envelope.sample_reason == "error"

    def test_explicit_status_attribute(self) -> None:
        settings = _make_settings()
        publisher = _make_publisher()
        processor = TraceBufferSpanProcessor(publisher, settings)

        root = _make_span(
            attributes={
                "agentlabkit.trace.root": True,
                "agentlabkit.run_id": "550e8400-e29b-41d4-a716-446655440000",
                "agentlabkit.status": "timeout",
            },
        )
        processor.on_end(root)

        envelope = publisher.submit_nowait.call_args[0][0]
        assert envelope.status == "timeout"
