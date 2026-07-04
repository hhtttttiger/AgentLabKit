"""Tests for SpanBuilder — span construction from EventBus events."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from observability.span_builder import SpanBuilder


# ── Helpers ────────────────────────────────────────────────────────────


def _make_event(event_type: str, **kwargs) -> SimpleNamespace:
    return SimpleNamespace(type=event_type, **kwargs)


def _msg_event(event_type: str, role: str = "assistant", **kwargs) -> SimpleNamespace:
    msg = SimpleNamespace(role=role, **kwargs)
    return SimpleNamespace(type=event_type, message=msg, **kwargs)


def _tool_event(event_type: str, tool_name: str, **kwargs) -> SimpleNamespace:
    return SimpleNamespace(type=event_type, tool_name=tool_name, **kwargs)


# ── Tests ──────────────────────────────────────────────────────────────


class TestSpanBuilder:
    """Core span construction logic."""

    def test_basic_turn_creates_trace_and_span(self):
        builder = SpanBuilder(trace_id="test-basic")
        builder._on_turn_start()
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        assert trace.trace_id == "test-basic"
        assert trace.status == "ok"
        assert trace.span_count == 1
        assert len(spans) == 1
        assert spans[0].span_kind == "agent_turn"
        assert spans[0].name == "agent_turn"
        assert spans[0].parent_span_id is None

    def test_llm_call_span_created(self):
        builder = SpanBuilder(trace_id="test-llm")
        builder._on_turn_start()
        builder._on_message_start(_msg_event("message_start", role="assistant"))
        builder._on_message_end(_msg_event("message_end", role="assistant"))
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        assert len(spans) == 2  # agent_turn + llm_call
        llm_spans = [s for s in spans if s.span_kind == "llm_call"]
        assert len(llm_spans) == 1
        assert llm_spans[0].name == "llm_completion"

    def test_tool_execution_span(self):
        builder = SpanBuilder(trace_id="test-tool")
        builder._on_turn_start()
        builder._on_tool_start(_tool_event("tool_execution_start", "search", args={"q": "test"}))
        builder._on_tool_end(_tool_event("tool_execution_end", "search", is_error=False, result="found"))
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        tool_spans = [s for s in spans if s.span_kind == "tool_execution"]
        assert len(tool_spans) == 1
        assert tool_spans[0].name == "tool:search"
        assert tool_spans[0].status == "ok"

    def test_tool_error_status(self):
        builder = SpanBuilder(trace_id="test-tool-err")
        builder._on_turn_start()
        builder._on_tool_start(_tool_event("tool_execution_start", "failing_tool"))
        builder._on_tool_end(_tool_event("tool_execution_end", "failing_tool", is_error=True, result="boom"))
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        tool_spans = [s for s in spans if s.span_kind == "tool_execution"]
        assert len(tool_spans) == 1
        assert tool_spans[0].status == "error"

    def test_concurrent_llm_calls(self):
        """Two overlapping LLM calls should both be recorded."""
        builder = SpanBuilder(trace_id="test-concurrent-llm")
        builder._on_turn_start()

        # Start both before ending either
        builder._on_message_start(_msg_event("message_start", role="assistant"))
        builder._on_message_start(_msg_event("message_start", role="assistant"))
        builder._on_message_end(_msg_event("message_end", role="assistant"))
        builder._on_message_end(_msg_event("message_end", role="assistant"))

        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        llm_spans = [s for s in spans if s.span_kind == "llm_call"]
        assert len(llm_spans) == 2, f"Expected 2 LLM spans, got {len(llm_spans)}"
        # Each span should have a distinct span_id
        assert llm_spans[0].span_id != llm_spans[1].span_id

    def test_max_spans_limit(self):
        builder = SpanBuilder(trace_id="test-max", max_spans=3)
        builder._on_turn_start()
        # Generate many tool spans
        for i in range(10):
            builder._on_tool_start(_tool_event("tool_execution_start", f"tool{i}"))
            builder._on_tool_end(_tool_event("tool_execution_end", f"tool{i}"))
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        # max_spans applies to total spans; 1 agent_turn + up to max_spans others
        assert len(spans) <= 4  # 1 turn + up to 3 capped tool spans
        assert trace.span_count == len(spans)

    def test_error_status_on_trace(self):
        builder = SpanBuilder(trace_id="test-error")
        builder._on_turn_start()
        builder.set_error("Something went wrong")
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        assert trace.status == "error"
        assert spans[0].error_message == "Something went wrong"

    def test_token_accumulation(self):
        builder = SpanBuilder(trace_id="test-tokens")
        builder._on_turn_start()

        # Simulate an LLM call with usage
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        builder._on_message_start(_msg_event("message_start", role="assistant"))
        builder._on_message_end(_msg_event("message_end", role="assistant", usage=usage))
        builder._on_turn_end(SimpleNamespace())

        trace, spans = builder.finalize()
        assert trace.total_input_tokens == 100
        assert trace.total_output_tokens == 50

    def test_ignores_non_assistant_messages(self):
        builder = SpanBuilder(trace_id="test-non-assistant")
        builder._on_turn_start()
        builder._on_message_start(_msg_event("message_start", role="user"))
        builder._on_message_end(_msg_event("message_end", role="user"))
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        # Only agent_turn span, no llm_call span
        llm_spans = [s for s in spans if s.span_kind == "llm_call"]
        assert len(llm_spans) == 0

    def test_span_has_duration(self):
        builder = SpanBuilder(trace_id="test-duration")
        builder._on_turn_start()
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        assert spans[0].duration_ms is not None
        assert spans[0].duration_ms >= 0
        assert trace.total_duration_ms is not None
        assert trace.total_duration_ms >= 0

    def test_span_timestamps_are_utc(self):
        builder = SpanBuilder(trace_id="test-timestamps")
        builder._on_turn_start()
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        assert spans[0].started_at_utc is not None
        assert spans[0].completed_at_utc is not None
        assert spans[0].started_at_utc <= spans[0].completed_at_utc

    def test_unknown_event_type_ignored(self):
        builder = SpanBuilder(trace_id="test-unknown")
        builder._on_turn_start()
        builder.on_event(_make_event("some_random_event"))
        builder._on_turn_end(SimpleNamespace())
        trace, spans = builder.finalize()

        assert len(spans) == 1  # Only agent_turn
