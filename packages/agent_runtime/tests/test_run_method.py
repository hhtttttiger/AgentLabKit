"""AgentRuntime.run() 测试 — Phase 2。

验证 run() 方法返回 AgentRun，以及与 run_turn 的一致性。
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agent_runtime import (
    AgentMessage,
    AgentRole,
    AgentTurnRequest,
    ToolRegistry,
)
from agent_runtime.config import AgentSettings
from agent_runtime.contracts.run import AgentRun, RunStatus
from agent_runtime.runtime import AgentRuntime
from llm_gateway import ProviderId, TextGenerateResponse, UsageInfo


class FakeGatewayService:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def generate_text(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _make_runtime(gateway, *, tool_registry=None):
    if tool_registry is None:
        tool_registry = ToolRegistry()

    return AgentRuntime(
        settings=AgentSettings(),
        gateway=gateway,
        tool_registry=tool_registry,
    )


def _make_response(text: str, usage=None):
    """Create a response in the structured format the runtime expects."""
    import json
    payload = json.dumps({
        "kind": "final",
        "reply_text": text,
        "should_handoff": False,
    })
    return TextGenerateResponse(
        provider=ProviderId.OPENAI,
        model="gpt-4o",
        text=payload,
        usage=usage or UsageInfo(input_tokens=10, output_tokens=5),
    )


# ── Tests ───────────────────────────────────────────────────────────


class TestAgentRuntimeRun:
    @pytest.mark.asyncio
    async def test_run_returns_agent_run(self) -> None:
        """run() 应该返回 AgentRun 对象。"""
        gateway = FakeGatewayService([_make_response("hello")])
        runtime = _make_runtime(gateway)

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="hi",
            session_id="s1",
        ))

        assert isinstance(agent_run, AgentRun)
        assert agent_run.run_id  # auto-generated
        assert agent_run.status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_populates_output_text(self) -> None:
        """AgentRun.output_text 应该包含回复内容。"""
        gateway = FakeGatewayService([_make_response("退款已提交")])
        runtime = _make_runtime(gateway)

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="退款",
            session_id="s1",
        ))

        assert agent_run.output_text == "退款已提交"

    @pytest.mark.asyncio
    async def test_run_populates_input_text(self) -> None:
        """AgentRun.input_text 应该包含用户输入。"""
        gateway = FakeGatewayService([_make_response("ok")])
        runtime = _make_runtime(gateway)

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="test input",
            session_id="s1",
        ))

        assert agent_run.input_text == "test input"

    @pytest.mark.asyncio
    async def test_run_populates_usage(self) -> None:
        """AgentRun.usage 应该包含 token 使用信息。"""
        usage = UsageInfo(input_tokens=100, output_tokens=50, total_tokens=150)
        gateway = FakeGatewayService([_make_response("ok", usage)])
        runtime = _make_runtime(gateway)

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="q",
            session_id="s1",
        ))

        assert agent_run.usage is not None
        assert agent_run.usage.input_tokens == 100
        assert agent_run.usage.output_tokens == 50
        assert agent_run.total_tokens == 150

    @pytest.mark.asyncio
    async def test_run_on_error_marks_failed(self) -> None:
        """当 run_turn 抛出 AgentError 时，AgentRun 应该标记为 FAILED。"""
        from llm_gateway.errors import GatewayError, GatewayErrorCode

        gateway = FakeGatewayService([
            GatewayError(GatewayErrorCode.PROVIDER_TIMEOUT, "request timeout"),
        ])
        runtime = _make_runtime(gateway)

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="q",
            session_id="s1",
        ))

        assert agent_run.status == RunStatus.FAILED
        assert agent_run.error is not None
        assert "timeout" in agent_run.error.message.lower()

    @pytest.mark.asyncio
    async def test_run_creates_own_trace_id(self) -> None:
        """AgentRun.trace_id 由 Runtime 通过 ExecutionContext 创建，不从 request 继承。"""
        gateway = FakeGatewayService([_make_response("ok")])
        runtime = _make_runtime(gateway)

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="q",
            session_id="s1",
            trace_id="my-trace",
        ))

        # Runtime is the sole creator of identity — request.trace_id is ignored
        assert agent_run.trace_id is not None
        assert agent_run.trace_id != "my-trace"
        assert len(agent_run.trace_id) == 32  # uuid4().hex

    @pytest.mark.asyncio
    async def test_run_sets_session_id(self) -> None:
        gateway = FakeGatewayService([_make_response("ok")])
        runtime = _make_runtime(gateway)

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="q",
            session_id="session-123",
        ))

        assert agent_run.session_id == "session-123"

    @pytest.mark.asyncio
    async def test_run_consistent_with_run_turn(self) -> None:
        """run() 的输出应该与 run_turn() 的结果一致。"""
        # Provide two identical responses for two calls
        gateway = FakeGatewayService([
            _make_response("test reply"),
            _make_response("test reply"),
        ])
        runtime = _make_runtime(gateway)

        # run_turn (legacy path — creates its own identity)
        result = await runtime.run_turn(AgentTurnRequest(
            user_message="q",
            session_id="s1",
        ))

        # run (v2 path — creates ExecutionContext)
        agent_run = await runtime.run(AgentTurnRequest(
            user_message="q",
            session_id="s1",
        ))

        assert agent_run.output_text == result.reply_text
        assert agent_run.action == result.action.value

    @pytest.mark.asyncio
    async def test_run_identity_consistency(self) -> None:
        """AgentRun.run_id/trace_id 与 loop 产生的 RuntimeEvent 一致。

        这是最重要的架构验收测试：证明 run() 创建的 ExecutionContext
        贯穿整条链路，AgentRun.run_id == RuntimeEvent.run_id。
        """
        from agent_runtime.event_bus import EventBus
        from agent_runtime.events_v2 import RunStarted, RunCompleted

        gateway = FakeGatewayService([_make_response("hello")])
        runtime = _make_runtime(gateway)

        # Collect v2 semantic events
        collected_events: list = []
        original_emit = runtime._event_bus.emit

        async def capture_emit(event):
            collected_events.append(event)
            await original_emit(event)

        runtime._event_bus.emit = capture_emit

        agent_run = await runtime.run(AgentTurnRequest(
            user_message="hi",
            session_id="s1",
            user_id="user-123",
        ))

        # Extract RunStarted and RunCompleted events
        run_started = [e for e in collected_events if isinstance(e, RunStarted)]
        run_completed = [e for e in collected_events if isinstance(e, RunCompleted)]

        assert len(run_started) == 1, f"Expected 1 RunStarted, got {len(run_started)}"
        assert len(run_completed) == 1, f"Expected 1 RunCompleted, got {len(run_completed)}"

        # Core invariant: AgentRun.run_id == RuntimeEvent.run_id
        assert agent_run.run_id == run_started[0].run_id, \
            "AgentRun.run_id must equal RunStarted.run_id"
        assert agent_run.run_id == run_completed[0].run_id, \
            "AgentRun.run_id must equal RunCompleted.run_id"

        # Core invariant: AgentRun.trace_id == RuntimeEvent.trace_id
        assert agent_run.trace_id == run_started[0].trace_id, \
            "AgentRun.trace_id must equal RunStarted.trace_id"
        assert agent_run.trace_id == run_completed[0].trace_id, \
            "AgentRun.trace_id must equal RunCompleted.trace_id"
        assert run_started[0].user_id == "user-123"
