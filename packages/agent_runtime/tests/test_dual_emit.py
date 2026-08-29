"""Dual Emit 集成测试 — Phase 1。

验证 run_agent_loop 在执行过程中同时发射旧事件和 v2 语义事件。
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_runtime.event_bus import EventBus
from agent_runtime.events import (
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    MessageStartEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionEndEvent,
)
from agent_runtime.events_v2 import (
    RunStarted,
    RunCompleted,
    AgentStarted,
    AgentCompleted,
    AgentTurnStarted,
    AgentTurnCompleted,
    LLMCallStarted,
    LLMCallCompleted,
    ToolCallStarted,
    ToolCallCompleted,
    RuntimeEvent,
)
from agent_runtime.runtime.loop import run_agent_loop, LoopContext, LoopConfig
from agent_runtime.contracts.models import AgentMessage, AgentRole
from agent_runtime.runtime.llm_adapter import FinalDirective, ToolDirective, ToolSchema
from agent_runtime.tools.contracts import ToolExecutionMode


# ── helpers ─────────────────────────────────────────────────────────


class _FakeLlmAdapter:
    """可控的 LLM adapter mock。"""

    def __init__(self, *responses):
        self._responses = list(responses)
        self._idx = 0
        self._model = "test-model"
        self._provider = "test-provider"

    async def generate(self, **kwargs):
        resp = self._responses[self._idx]
        self._idx += 1
        return resp


def _final_directive(text: str = "done") -> tuple[FinalDirective, MagicMock]:
    usage = MagicMock()
    usage.input_tokens = 10
    usage.output_tokens = 5
    usage.cache_write_tokens = 0
    usage.cache_read_tokens = 0
    usage.estimated_cost = 0.001
    return FinalDirective(reply_text=text, should_handoff=False), usage


def _tool_directive(name: str = "search", args: dict | None = None) -> tuple[ToolDirective, MagicMock]:
    usage = MagicMock()
    usage.input_tokens = 10
    usage.output_tokens = 5
    usage.cache_write_tokens = 0
    usage.cache_read_tokens = 0
    usage.estimated_cost = 0.001
    return ToolDirective(reply_text="", tool_name=name, arguments=args or {"q": "test"}), usage


# ── Tests ───────────────────────────────────────────────────────────


class TestDualEmit:
    @pytest.mark.asyncio
    async def test_run_agent_loop_emits_v2_run_events(self) -> None:
        """run_agent_loop 应该发射 RunStarted 和 RunCompleted。"""
        bus = EventBus()
        v2_events: list[RuntimeEvent] = []

        def collector(event):
            if isinstance(event, RuntimeEvent):
                v2_events.append(event)

        bus.subscribe(collector)

        llm = _FakeLlmAdapter(_final_directive("hello"))
        context = LoopContext(
            system_prompt="test",
            messages=[],
            tools=[],
        )
        config = LoopConfig()

        await run_agent_loop(
            prompts=[AgentMessage(role=AgentRole.USER, content="hi")],
            context=context,
            config=config,
            llm=llm,
            event_bus=bus,
            run_id="run-123",
            trace_id="trace-456",
        )

        event_types = [e.event_type for e in v2_events]
        assert "run.started" in event_types
        assert "run.completed" in event_types
        assert "agent.started" in event_types
        assert "agent.completed" in event_types
        assert "agent.turn_started" in event_types
        assert "agent.turn_completed" in event_types

    @pytest.mark.asyncio
    async def test_run_agent_loop_emits_v2_llm_events(self) -> None:
        """run_agent_loop 应该发射 LLMCallStarted 和 LLMCallCompleted。"""
        bus = EventBus()
        v2_events: list[RuntimeEvent] = []

        def collector(event):
            if isinstance(event, RuntimeEvent):
                v2_events.append(event)

        bus.subscribe(collector)

        llm = _FakeLlmAdapter(_final_directive("response"))
        context = LoopContext(system_prompt="test", messages=[], tools=[])
        config = LoopConfig()

        await run_agent_loop(
            prompts=[AgentMessage(role=AgentRole.USER, content="q")],
            context=context,
            config=config,
            llm=llm,
            event_bus=bus,
            run_id="r1",
            trace_id="t1",
        )

        llm_events = [e for e in v2_events if e.event_type.startswith("llm.")]
        assert len(llm_events) >= 2  # started + completed
        started = [e for e in llm_events if e.event_type == "llm.call_started"]
        completed = [e for e in llm_events if e.event_type == "llm.call_completed"]
        assert len(started) >= 1
        assert len(completed) >= 1

    @pytest.mark.asyncio
    async def test_run_agent_loop_emits_v2_tool_events(self) -> None:
        """run_agent_loop 应该在 tool call 时发射 ToolCallStarted 和 ToolCallCompleted。"""
        bus = EventBus()
        v2_events: list[RuntimeEvent] = []

        def collector(event):
            if isinstance(event, RuntimeEvent):
                v2_events.append(event)

        bus.subscribe(collector)

        # 第一次返回 tool directive，第二次返回 final
        tool_dir, tool_usage = _tool_directive("search", {"q": "test"})
        final_dir, final_usage = _final_directive("answer")

        call_count = 0

        class _StepLlm(_FakeLlmAdapter):
            async def generate(self, **kwargs):
                nonlocal call_count
                if call_count == 0:
                    call_count += 1
                    return tool_dir, tool_usage
                return final_dir, final_usage

        llm = _StepLlm()

        async def _fake_tool_executor(tool_name, arguments, tool_call_id):
            return "tool result", False

        context = LoopContext(
            system_prompt="test",
            messages=[],
            tools=[ToolSchema(name="search", description="search", parameters_json_schema={})],
        )
        config = LoopConfig(tool_executor=_fake_tool_executor)

        await run_agent_loop(
            prompts=[AgentMessage(role=AgentRole.USER, content="search for X")],
            context=context,
            config=config,
            llm=llm,
            event_bus=bus,
            run_id="r1",
            trace_id="t1",
        )

        tool_events = [e for e in v2_events if e.event_type.startswith("tool.")]
        assert len(tool_events) >= 2
        started = [e for e in tool_events if e.event_type == "tool.call_started"]
        completed = [e for e in tool_events if e.event_type == "tool.call_completed"]
        assert len(started) >= 1
        assert started[0].tool_name == "search"
        assert started[0].arguments == {"q": "test"}
        assert len(completed) >= 1

    @pytest.mark.asyncio
    async def test_v2_events_carry_run_id_and_trace_id(self) -> None:
        """所有 v2 事件应该携带 run_id 和 trace_id。"""
        bus = EventBus()
        v2_events: list[RuntimeEvent] = []

        def collector(event):
            if isinstance(event, RuntimeEvent):
                v2_events.append(event)

        bus.subscribe(collector)

        llm = _FakeLlmAdapter(_final_directive("ok"))
        context = LoopContext(system_prompt="test", messages=[], tools=[])
        config = LoopConfig()

        await run_agent_loop(
            prompts=[AgentMessage(role=AgentRole.USER, content="q")],
            context=context,
            config=config,
            llm=llm,
            event_bus=bus,
            run_id="my-run",
            trace_id="my-trace",
        )

        for event in v2_events:
            assert event.run_id == "my-run", f"{event.event_type} missing run_id"
            assert event.trace_id == "my-trace", f"{event.event_type} missing trace_id"

    @pytest.mark.asyncio
    async def test_old_events_still_emitted(self) -> None:
        """旧事件应该继续发射（向后兼容）。"""
        bus = EventBus()
        old_events = []

        def collector(event):
            old_events.append(type(event).__name__)

        bus.subscribe(collector)

        llm = _FakeLlmAdapter(_final_directive("ok"))
        context = LoopContext(system_prompt="test", messages=[], tools=[])
        config = LoopConfig()

        await run_agent_loop(
            prompts=[AgentMessage(role=AgentRole.USER, content="q")],
            context=context,
            config=config,
            llm=llm,
            event_bus=bus,
        )

        assert "AgentStartEvent" in old_events
        assert "TurnStartEvent" in old_events
        assert "AgentEndEvent" in old_events

    @pytest.mark.asyncio
    async def test_no_event_bus_no_error(self) -> None:
        """没有 event_bus 时不应该报错。"""
        llm = _FakeLlmAdapter(_final_directive("ok"))
        context = LoopContext(system_prompt="test", messages=[], tools=[])
        config = LoopConfig()

        result = await run_agent_loop(
            prompts=[AgentMessage(role=AgentRole.USER, content="q")],
            context=context,
            config=config,
            llm=llm,
            event_bus=None,
        )
        assert result.final_directive.reply_text == "ok"
