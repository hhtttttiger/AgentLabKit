"""RuntimeEvent v2 测试 — Phase 1。

覆盖：所有事件类型构造、默认值、字段完整性、event_type 唯一性、RunStatus/SpanKind 枚举。
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agent_runtime.events_v2 import (
    RuntimeEvent,
    RunStatus,
    SpanKind,
    RunStarted,
    RunCompleted,
    RunFailed,
    RunCancelled,
    AgentStarted,
    AgentCompleted,
    AgentTurnStarted,
    AgentTurnCompleted,
    LLMCallStarted,
    LLMCallCompleted,
    LLMCallFailed,
    ToolCallStarted,
    ToolCallCompleted,
    ToolCallFailed,
    RetrievalStarted,
    RetrievalCompleted,
    RetrievalFailed,
    GuardrailEvaluated,
    GuardrailBlocked,
    HandoffStarted,
    HandoffCompleted,
    DelegationStarted,
    DelegationCompleted,
)

# 所有具体事件类
ALL_EVENT_CLASSES = [
    RunStarted,
    RunCompleted,
    RunFailed,
    RunCancelled,
    AgentStarted,
    AgentCompleted,
    AgentTurnStarted,
    AgentTurnCompleted,
    LLMCallStarted,
    LLMCallCompleted,
    LLMCallFailed,
    ToolCallStarted,
    ToolCallCompleted,
    ToolCallFailed,
    RetrievalStarted,
    RetrievalCompleted,
    RetrievalFailed,
    GuardrailEvaluated,
    GuardrailBlocked,
    HandoffStarted,
    HandoffCompleted,
    DelegationStarted,
    DelegationCompleted,
]

# event_type → class 的预期映射
EXPECTED_EVENT_TYPES = {
    RunStarted: "run.started",
    RunCompleted: "run.completed",
    RunFailed: "run.failed",
    RunCancelled: "run.cancelled",
    AgentStarted: "agent.started",
    AgentCompleted: "agent.completed",
    AgentTurnStarted: "agent.turn_started",
    AgentTurnCompleted: "agent.turn_completed",
    LLMCallStarted: "llm.call_started",
    LLMCallCompleted: "llm.call_completed",
    LLMCallFailed: "llm.call_failed",
    ToolCallStarted: "tool.call_started",
    ToolCallCompleted: "tool.call_completed",
    ToolCallFailed: "tool.call_failed",
    RetrievalStarted: "retrieval.started",
    RetrievalCompleted: "retrieval.completed",
    RetrievalFailed: "retrieval.failed",
    GuardrailEvaluated: "guardrail.evaluated",
    GuardrailBlocked: "guardrail.blocked",
    HandoffStarted: "handoff.started",
    HandoffCompleted: "handoff.completed",
    DelegationStarted: "delegation.started",
    DelegationCompleted: "delegation.completed",
}


# ── 基类 ───────────────────────────────────────────────────────────


class TestRuntimeEventBase:
    def test_default_event_id_generated(self) -> None:
        e1 = RuntimeEvent()
        e2 = RuntimeEvent()
        assert e1.event_id != e2.event_id
        assert len(e1.event_id) == 32  # uuid4 hex

    def test_default_timestamp_is_utc(self) -> None:
        e = RuntimeEvent()
        assert e.timestamp.tzinfo == timezone.utc

    def test_base_fields(self) -> None:
        e = RuntimeEvent(
            run_id="run-1",
            trace_id="trace-1",
            span_id="span-1",
            parent_span_id="parent-1",
        )
        assert e.run_id == "run-1"
        assert e.trace_id == "trace-1"
        assert e.span_id == "span-1"
        assert e.parent_span_id == "parent-1"

    def test_attributes_default_empty(self) -> None:
        e = RuntimeEvent()
        assert e.attributes == {}


# ── event_type 唯一性 ──────────────────────────────────────────────


class TestEventTypeUniqueness:
    def test_all_event_types_unique(self) -> None:
        types = [cls().event_type for cls in ALL_EVENT_CLASSES]
        assert len(types) == len(set(types)), f"Duplicate event_types: {types}"

    def test_event_types_match_expected(self) -> None:
        for cls, expected_type in EXPECTED_EVENT_TYPES.items():
            event = cls()
            assert event.event_type == expected_type, (
                f"{cls.__name__}: expected '{expected_type}', got '{event.event_type}'"
            )


# ── 所有事件可默认构造 ────────────────────────────────────────────


class TestDefaultConstruction:
    @pytest.mark.parametrize("cls", ALL_EVENT_CLASSES, ids=lambda c: c.__name__)
    def test_default_construction(self, cls) -> None:
        event = cls()
        assert isinstance(event, RuntimeEvent)
        assert event.event_type  # 非空
        assert event.event_id   # 自动生成
        assert isinstance(event.timestamp, datetime)


# ── Run events ─────────────────────────────────────────────────────


class TestRunEvents:
    def test_run_started_fields(self) -> None:
        e = RunStarted(
            run_id="r1",
            agent_key="customer-service",
            agent_version="v3",
            input_text="退款",
            session_id="s1",
        )
        assert e.agent_key == "customer-service"
        assert e.agent_version == "v3"
        assert e.input_text == "退款"
        assert e.session_id == "s1"

    def test_run_completed_fields(self) -> None:
        e = RunCompleted(
            run_id="r1",
            output_text="已退款",
            total_input_tokens=100,
            total_output_tokens=50,
            total_duration_ms=1500,
        )
        assert e.output_text == "已退款"
        assert e.total_input_tokens == 100
        assert e.total_output_tokens == 50
        assert e.total_duration_ms == 1500

    def test_run_failed_fields(self) -> None:
        e = RunFailed(
            run_id="r1",
            error_code="GATEWAY_ERROR",
            error_message="timeout",
        )
        assert e.error_code == "GATEWAY_ERROR"
        assert e.error_message == "timeout"

    def test_run_cancelled_fields(self) -> None:
        e = RunCancelled(run_id="r1", reason="user abort")
        assert e.reason == "user abort"


# ── LLM events ─────────────────────────────────────────────────────


class TestLLMEvents:
    def test_llm_call_started_fields(self) -> None:
        e = LLMCallStarted(model="gpt-4o", provider="openai")
        assert e.model == "gpt-4o"
        assert e.provider == "openai"

    def test_llm_call_completed_fields(self) -> None:
        e = LLMCallCompleted(
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            cache_write_tokens=10,
            cache_read_tokens=5,
            estimated_cost=0.003,
            latency_ms=800,
            finish_reason="stop",
        )
        assert e.input_tokens == 100
        assert e.output_tokens == 50
        assert e.cache_write_tokens == 10
        assert e.cache_read_tokens == 5
        assert e.estimated_cost == 0.003
        assert e.latency_ms == 800
        assert e.finish_reason == "stop"

    def test_llm_call_completed_defaults(self) -> None:
        e = LLMCallCompleted()
        assert e.input_tokens == 0
        assert e.output_tokens == 0
        assert e.estimated_cost == 0.0

    def test_llm_call_failed_fields(self) -> None:
        e = LLMCallFailed(
            model="gpt-4o",
            provider="openai",
            error_code="RATE_LIMIT",
            error_message="rate limited",
        )
        assert e.error_code == "RATE_LIMIT"


# ── Tool events ────────────────────────────────────────────────────


class TestToolEvents:
    def test_tool_call_started_fields(self) -> None:
        e = ToolCallStarted(
            tool_name="get_order",
            arguments={"order_id": "123"},
            source_type="builtin",
        )
        assert e.tool_name == "get_order"
        assert e.arguments == {"order_id": "123"}
        assert e.source_type == "builtin"

    def test_tool_call_completed_fields(self) -> None:
        e = ToolCallCompleted(
            tool_name="get_order",
            result='{"status": "shipped"}',
            duration_ms=150,
        )
        assert e.tool_name == "get_order"
        assert e.duration_ms == 150
        assert e.is_error is False

    def test_tool_call_failed_fields(self) -> None:
        e = ToolCallFailed(
            tool_name="get_order",
            error_code="TIMEOUT",
            error_message="tool timeout",
        )
        assert e.error_code == "TIMEOUT"


# ── Guardrail events ───────────────────────────────────────────────


class TestGuardrailEvents:
    def test_guardrail_evaluated_passed(self) -> None:
        e = GuardrailEvaluated(
            guardrail_name="content_safety",
            guardrail_type="output",
            passed=True,
        )
        assert e.passed is True

    def test_guardrail_blocked_fields(self) -> None:
        e = GuardrailBlocked(
            guardrail_name="pii_masking",
            guardrail_type="output",
            action="block",
            reason="PII detected",
        )
        assert e.action == "block"
        assert e.reason == "PII detected"


# ── Multi-agent events ─────────────────────────────────────────────


class TestMultiAgentEvents:
    def test_handoff_started_fields(self) -> None:
        e = HandoffStarted(
            source_agent="customer_service",
            target_agent="refund_agent",
            reason="refund request",
        )
        assert e.source_agent == "customer_service"
        assert e.target_agent == "refund_agent"

    def test_delegation_completed_fields(self) -> None:
        e = DelegationCompleted(
            delegating_agent="coordinator",
            target_agent="researcher",
            output_text="research result",
        )
        assert e.output_text == "research result"


# ── Enums ──────────────────────────────────────────────────────────


class TestEnums:
    def test_run_status_values(self) -> None:
        assert RunStatus.RUNNING.value == "running"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.CANCELLED.value == "cancelled"

    def test_span_kind_values(self) -> None:
        assert SpanKind.RUN.value == "RUN"
        assert SpanKind.AGENT.value == "AGENT"
        assert SpanKind.LLM_CALL.value == "LLM_CALL"
        assert SpanKind.TOOL_CALL.value == "TOOL_CALL"
        assert SpanKind.HANDOFF.value == "HANDOFF"
        assert SpanKind.CUSTOM.value == "CUSTOM"


# ── 事件可序列化 ───────────────────────────────────────────────────


class TestSerialization:
    @pytest.mark.parametrize("cls", ALL_EVENT_CLASSES, ids=lambda c: c.__name__)
    def test_event_to_dict(self, cls) -> None:
        """所有事件都应该可以转为 dict（dataclass 特性）。"""
        from dataclasses import asdict
        event = cls(run_id="test-run", trace_id="test-trace")
        d = asdict(event)
        assert isinstance(d, dict)
        assert d["run_id"] == "test-run"
        assert d["trace_id"] == "test-trace"
        assert "event_type" in d
        assert "timestamp" in d

    def test_llm_call_completed_full_dict(self) -> None:
        from dataclasses import asdict
        e = LLMCallCompleted(
            run_id="r1",
            trace_id="t1",
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.003,
            latency_ms=800,
            finish_reason="stop",
        )
        d = asdict(e)
        assert d["model"] == "gpt-4o"
        assert d["input_tokens"] == 100
        assert d["estimated_cost"] == 0.003
