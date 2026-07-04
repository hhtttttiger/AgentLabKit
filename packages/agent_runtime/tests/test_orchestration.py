"""Unit tests for the orchestration package.

Coverage:
- AgentRouter: keyword matching, regex matching, LLM routing, fallback, default
- DirectContextPasser: message trimming, key fact extraction
- SummarizingContextPasser: short history fast-path, summarizer invocation
- HandoffManager: human handoff, agent handoff, validation failure fallback
- SubAgentExecutor: normal delegation, depth limit, cycle detection, loader validation
- DelegateToAgentTool: argument validation, result passthrough, handoff surface
"""

from __future__ import annotations

import pytest

from agent_runtime.contracts.models import (
    AgentAction,
    AgentMessage,
    AgentRole,
    AgentTurnRequest,
    AgentTurnResult,
    HandoffTarget,
)
from agent_runtime.definition.models import AgentDefinitionSnapshot
from agent_runtime.definition.loader import StaticAgentDefinitionLoader
from agent_runtime.orchestration import (
    AgentHandoffContext,
    AgentRouter,
    DelegateToAgentTool,
    DelegationResult,
    DirectContextPasser,
    HandoffManager,
    HandoffResolution,
    HandoffRouteTarget,
    MAX_ORCHESTRATION_DEPTH,
    SubAgentContext,
    SubAgentExecutor,
    SummarizingContextPasser,
)
from agent_runtime.orchestration.contracts import (
    _CHAIN_METADATA_KEY,
    _DEPTH_METADATA_KEY,
)
from agent_runtime.tools.contracts import ToolExecutionContext


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------


def _make_request(**kwargs) -> AgentTurnRequest:
    defaults = dict(
        session_id="sess-1",
        user_message="hello",
        agent_key="triage",
        trace_id="trace-1",
        metadata={},
    )
    defaults.update(kwargs)
    return AgentTurnRequest(**defaults)


def _make_result(
    *,
    reply_text: str = "ok",
    action: AgentAction = AgentAction.REPLY,
    agent_key: str = "specialist",
) -> AgentTurnResult:
    return AgentTurnResult(
        session_id="sess-1",
        trace_id="trace-1",
        action=action,
        reply_text=reply_text,
        agent_key=agent_key,
    )


def _make_definition(key: str = "specialist", status: str = "published") -> AgentDefinitionSnapshot:
    return AgentDefinitionSnapshot(
        agent_key=key,
        version_number=1,
        display_name=key,
        status=status,
    )


def _make_messages(*texts: str, role: AgentRole = AgentRole.USER) -> list[AgentMessage]:
    return [AgentMessage(role=role, content=t) for t in texts]


class StubRunner:
    """Minimal SubTurnRunner stub for testing."""

    def __init__(self, result: AgentTurnResult | None = None, side_effect: Exception | None = None):
        self.calls: list[AgentTurnRequest] = []
        self._result = result or _make_result()
        self._side_effect = side_effect

    async def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
        self.calls.append(request)
        if self._side_effect:
            raise self._side_effect
        return self._result


class StubSummarizer:
    """Minimal summarizer stub for testing SummarizingContextPasser."""

    def __init__(self, summary: str = "Short summary."):
        self._summary = summary
        self.calls: list[tuple] = []

    async def summarize(
        self, messages: list[AgentMessage], context_hint: str | None = None
    ) -> str:
        self.calls.append((messages, context_hint))
        return self._summary


# ===========================================================================
# AgentRouter
# ===========================================================================


class TestAgentRouter:
    def _router(self, policy: dict) -> AgentRouter:
        return AgentRouter(policy)

    def test_empty_policy_returns_human(self):
        router = self._router({})
        target = router.resolve("some reason")
        assert target.target_type == "human"

    def test_keyword_match_routes_to_agent(self):
        router = self._router({
            "routes": [
                {"match": "refund", "target_type": "agent", "target_agent_key": "refund-agent"}
            ]
        })
        target = router.resolve("I need a refund please")
        assert target.target_type == "agent"
        assert target.target_agent_key == "refund-agent"

    def test_regex_match_routes_to_agent(self):
        router = self._router({
            "routes": [
                {"match": "refund|退款", "target_type": "agent", "target_agent_key": "refund-agent"}
            ]
        })
        # Chinese keyword
        target = router.resolve("我要退款")
        assert target.target_type == "agent"
        assert target.target_agent_key == "refund-agent"

    def test_no_match_returns_default_human(self):
        router = self._router({
            "routes": [
                {"match": "technical", "target_type": "agent", "target_agent_key": "tech-support"}
            ]
        })
        target = router.resolve("I need a refund")
        assert target.target_type == "human"

    def test_no_match_with_custom_default_agent(self):
        router = self._router({
            "default_target": "fallback-agent",
            "routes": [
                {"match": "technical", "target_type": "agent", "target_agent_key": "tech-support"}
            ]
        })
        target = router.resolve("unrelated query")
        assert target.target_type == "agent"
        assert target.target_agent_key == "fallback-agent"

    def test_llm_routing_disabled_by_default(self):
        router = self._router({})
        target = router.resolve(
            "reason",
            llm_target_type="agent",
            llm_target_agent="specialist",
        )
        # LLM routing disabled → falls through to default (human)
        assert target.target_type == "human"

    def test_llm_routing_enabled(self):
        router = self._router({"allow_llm_routing": True})
        target = router.resolve(
            "reason",
            llm_target_type="agent",
            llm_target_agent="specialist",
        )
        assert target.target_type == "agent"
        assert target.target_agent_key == "specialist"

    def test_llm_routing_rejected_when_not_in_available_list(self):
        router = self._router({"allow_llm_routing": True})
        target = router.resolve(
            "reason",
            llm_target_type="agent",
            llm_target_agent="unknown-agent",
            available_agents=["specialist"],
        )
        assert target.target_type == "human"

    def test_first_route_wins(self):
        router = self._router({
            "routes": [
                {"match": "refund", "target_type": "agent", "target_agent_key": "refund-agent"},
                {"match": "refund", "target_type": "agent", "target_agent_key": "other-agent"},
            ]
        })
        target = router.resolve("I need a refund")
        assert target.target_agent_key == "refund-agent"

    def test_build_handoff_instructions_empty_without_routes(self):
        router = self._router({})
        assert router.build_handoff_instructions() == ""

    def test_build_handoff_instructions_lists_agent_routes(self):
        router = self._router({
            "routes": [
                {"match": "refund", "target_type": "agent", "target_agent_key": "refund-agent"},
                {"match": "billing", "target_type": "human"},
            ]
        })
        instructions = router.build_handoff_instructions()
        assert "refund-agent" in instructions
        # Human routes should NOT appear
        assert "billing" not in instructions

    def test_none_reason_no_routes_returns_human(self):
        router = self._router({})
        target = router.resolve(None)
        assert target.target_type == "human"


# ===========================================================================
# DirectContextPasser
# ===========================================================================


class TestDirectContextPasser:
    @pytest.mark.asyncio
    async def test_empty_history_produces_none_summary(self):
        passer = DirectContextPasser()
        ctx = await passer.prepare_context("src", "tgt", [], "reason")
        assert ctx.summary is None
        assert ctx.turn_count == 0

    @pytest.mark.asyncio
    async def test_trims_to_max_messages(self):
        passer = DirectContextPasser(max_messages=2)
        msgs = _make_messages("a", "b", "c", "d")
        ctx = await passer.prepare_context("src", "tgt", msgs, "reason")
        # Summary should only contain the last 2
        assert ctx.summary is not None
        assert "c" in ctx.summary or "d" in ctx.summary
        assert "a" not in ctx.summary

    @pytest.mark.asyncio
    async def test_forwards_customer_and_locale(self):
        passer = DirectContextPasser()
        msgs = _make_messages("hello")
        ctx = await passer.prepare_context(
            "src", "tgt", msgs, "reason",
            customer_id="cust-1", locale="zh-CN"
        )
        assert ctx.original_customer_id == "cust-1"
        assert ctx.original_locale == "zh-CN"

    @pytest.mark.asyncio
    async def test_extracts_user_key_facts(self):
        passer = DirectContextPasser()
        msgs = [
            AgentMessage(role=AgentRole.USER, content="I need a refund for order 123"),
            AgentMessage(role=AgentRole.ASSISTANT, content="Sure, I can help."),
        ]
        ctx = await passer.prepare_context("src", "tgt", msgs, None)
        assert any("I need a refund" in f for f in ctx.key_facts)

    def test_invalid_max_messages_raises(self):
        with pytest.raises(ValueError):
            DirectContextPasser(max_messages=0)


# ===========================================================================
# SummarizingContextPasser
# ===========================================================================


class TestSummarizingContextPasser:
    @pytest.mark.asyncio
    async def test_uses_direct_for_short_history(self):
        stub = StubSummarizer()
        passer = SummarizingContextPasser(stub, max_messages_direct=3)
        msgs = _make_messages("a", "b")  # 2 messages ≤ 3 → direct
        await passer.prepare_context("src", "tgt", msgs, "reason")
        assert len(stub.calls) == 0  # summarizer NOT called

    @pytest.mark.asyncio
    async def test_calls_summarizer_for_long_history(self):
        stub = StubSummarizer("The customer had a billing issue.")
        passer = SummarizingContextPasser(stub, max_messages_direct=2)
        msgs = _make_messages("a", "b", "c", "d")  # 4 > 2 → summarize
        ctx = await passer.prepare_context("src", "tgt", msgs, "billing problem")
        assert len(stub.calls) == 1
        assert ctx.summary == "The customer had a billing issue."

    @pytest.mark.asyncio
    async def test_includes_reason_in_context_hint(self):
        stub = StubSummarizer()
        passer = SummarizingContextPasser(stub, max_messages_direct=1)
        msgs = _make_messages("hello", "world")  # 2 > 1 → summarize
        await passer.prepare_context("src", "tgt", msgs, "refund needed")
        _, hint = stub.calls[0]
        assert hint is not None
        assert "refund needed" in hint


# ===========================================================================
# HandoffManager
# ===========================================================================


class TestHandoffManager:
    @pytest.mark.asyncio
    async def test_human_target_resolves_to_handoff_human(self):
        runner = StubRunner()
        mgr = HandoffManager(runner)
        target = HandoffTarget(target_type="human", reason="need help")
        resolution = await mgr.resolve_handoff(target)
        assert resolution.action is AgentAction.HANDOFF_HUMAN

    @pytest.mark.asyncio
    async def test_agent_target_with_no_loader_resolves_to_handoff_agent(self):
        runner = StubRunner()
        mgr = HandoffManager(runner, definition_loader=None)
        target = HandoffTarget(target_type="agent", target_agent_key="specialist", reason="x")
        resolution = await mgr.resolve_handoff(target)
        assert resolution.action is AgentAction.HANDOFF_AGENT
        assert resolution.target_agent_key == "specialist"

    @pytest.mark.asyncio
    async def test_agent_target_with_loader_validates_definition(self):
        loader = StaticAgentDefinitionLoader({"specialist": _make_definition("specialist")})
        runner = StubRunner()
        mgr = HandoffManager(runner, definition_loader=loader)
        target = HandoffTarget(target_type="agent", target_agent_key="specialist")
        resolution = await mgr.resolve_handoff(target)
        assert resolution.action is AgentAction.HANDOFF_AGENT

    @pytest.mark.asyncio
    async def test_unknown_agent_falls_back_to_human(self):
        loader = StaticAgentDefinitionLoader({})  # no definitions
        runner = StubRunner()
        mgr = HandoffManager(runner, definition_loader=loader)
        target = HandoffTarget(target_type="agent", target_agent_key="nonexistent")
        resolution = await mgr.resolve_handoff(target)
        assert resolution.action is AgentAction.HANDOFF_HUMAN

    @pytest.mark.asyncio
    async def test_disabled_agent_falls_back_to_human(self):
        loader = StaticAgentDefinitionLoader(
            {"disabled-agent": _make_definition("disabled-agent", status="disabled")}
        )
        runner = StubRunner()
        mgr = HandoffManager(runner, definition_loader=loader)
        target = HandoffTarget(target_type="agent", target_agent_key="disabled-agent")
        resolution = await mgr.resolve_handoff(target)
        assert resolution.action is AgentAction.HANDOFF_HUMAN

    @pytest.mark.asyncio
    async def test_execute_agent_handoff_calls_runner(self):
        runner = StubRunner(_make_result(reply_text="specialist reply", agent_key="specialist"))
        mgr = HandoffManager(runner, definition_loader=None)
        resolution = HandoffResolution(
            action=AgentAction.HANDOFF_AGENT,
            target_agent_key="specialist",
            reason="technical issue",
        )
        request = _make_request(agent_key="triage")
        result = await mgr.execute_agent_handoff(
            resolution, request=request, history=[]
        )
        assert len(runner.calls) == 1
        assert runner.calls[0].agent_key == "specialist"
        assert result.responding_agent_key == "specialist"

    @pytest.mark.asyncio
    async def test_execute_agent_handoff_sets_orchestration_chain(self):
        runner = StubRunner(_make_result(agent_key="specialist"))
        mgr = HandoffManager(runner, definition_loader=None)
        resolution = HandoffResolution(
            action=AgentAction.HANDOFF_AGENT,
            target_agent_key="specialist",
        )
        request = _make_request(agent_key="triage")
        result = await mgr.execute_agent_handoff(
            resolution, request=request, history=[]
        )
        assert result.orchestration_chain == ["triage", "specialist"]

    @pytest.mark.asyncio
    async def test_handoff_policy_routes_override_target(self):
        runner = StubRunner(_make_result(agent_key="refund-agent"))
        mgr = HandoffManager(runner, definition_loader=None)
        policy = {
            "routes": [
                {"match": "refund", "target_type": "agent", "target_agent_key": "refund-agent"}
            ]
        }
        # LLM specified human but policy routes to refund-agent based on reason
        target = HandoffTarget(target_type="human", reason="customer needs a refund")
        resolution = await mgr.resolve_handoff(target, handoff_policy=policy)
        assert resolution.action is AgentAction.HANDOFF_AGENT
        assert resolution.target_agent_key == "refund-agent"


class StubStreamRunner:
    """Minimal SubStreamRunner stub for testing streaming handoff."""

    def __init__(self, events: list | None = None, *, result: AgentTurnResult | None = None):
        from agent_runtime.contracts.models import AgentTurnStreamEvent
        self.calls: list[AgentTurnRequest] = []
        self._result = result or _make_result()
        self._events = events or [
            AgentTurnStreamEvent(
                event_type="reply_delta",
                session_id="sess-1",
                trace_id="trace-1",
                delta="Hello ",
            ),
            AgentTurnStreamEvent(
                event_type="reply_delta",
                session_id="sess-1",
                trace_id="trace-1",
                delta="from sub-agent",
            ),
            AgentTurnStreamEvent(
                event_type="reply_completed",
                session_id="sess-1",
                trace_id="trace-1",
                reply_text="Hello from sub-agent",
                handoff_target=HandoffTarget(
                    target_type="agent",
                    target_agent_key="specialist",
                ),
            ),
        ]

    def stream_turn(self, request: AgentTurnRequest):
        self.calls.append(request)
        return self._iter()

    async def _iter(self):
        for event in self._events:
            yield event

    async def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
        self.calls.append(request)
        return self._result


class TestHandoffManagerStreaming:
    @pytest.mark.asyncio
    async def test_can_stream_true_when_stream_runner_provided(self):
        runner = StubRunner()
        stream_runner = StubStreamRunner()
        mgr = HandoffManager(runner, stream_runner=stream_runner)
        assert mgr.can_stream is True

    @pytest.mark.asyncio
    async def test_can_stream_false_without_stream_runner(self):
        runner = StubRunner()
        mgr = HandoffManager(runner)
        assert mgr.can_stream is False

    @pytest.mark.asyncio
    async def test_stream_execute_forwards_events(self):
        runner = StubRunner()
        stream_runner = StubStreamRunner()
        mgr = HandoffManager(runner, stream_runner=stream_runner, definition_loader=None)
        resolution = HandoffResolution(
            action=AgentAction.HANDOFF_AGENT,
            target_agent_key="specialist",
            reason="technical",
        )
        request = _make_request(agent_key="triage")
        events = []
        async for event in mgr.stream_execute_agent_handoff(
            resolution, request=request, history=[]
        ):
            events.append(event)

        assert len(events) == 3
        assert events[0].event_type == "reply_delta"
        assert events[0].delta == "Hello "
        assert events[1].event_type == "reply_delta"
        assert events[1].delta == "from sub-agent"
        assert events[2].event_type == "reply_completed"
        assert events[2].reply_text == "Hello from sub-agent"

    @pytest.mark.asyncio
    async def test_stream_execute_sends_sub_request_to_correct_agent(self):
        runner = StubRunner()
        stream_runner = StubStreamRunner()
        mgr = HandoffManager(runner, stream_runner=stream_runner, definition_loader=None)
        resolution = HandoffResolution(
            action=AgentAction.HANDOFF_AGENT,
            target_agent_key="specialist",
        )
        request = _make_request(agent_key="triage")
        async for _ in mgr.stream_execute_agent_handoff(
            resolution, request=request, history=[]
        ):
            pass

        assert len(stream_runner.calls) == 1
        assert stream_runner.calls[0].agent_key == "specialist"

    @pytest.mark.asyncio
    async def test_stream_execute_fallback_when_no_stream_runner(self):
        runner = StubRunner(_make_result(reply_text="blocking result"))
        mgr = HandoffManager(runner, definition_loader=None)
        resolution = HandoffResolution(
            action=AgentAction.HANDOFF_AGENT,
            target_agent_key="specialist",
        )
        request = _make_request(agent_key="triage")
        events = []
        async for event in mgr.stream_execute_agent_handoff(
            resolution, request=request, history=[]
        ):
            events.append(event)

        # Should yield a single synthetic reply_completed event
        assert len(events) == 1
        assert events[0].event_type == "reply_completed"
        assert events[0].reply_text == "blocking result"

    @pytest.mark.asyncio
    async def test_stream_execute_builds_chain_metadata(self):
        runner = StubRunner()
        stream_runner = StubStreamRunner()
        mgr = HandoffManager(runner, stream_runner=stream_runner, definition_loader=None)
        resolution = HandoffResolution(
            action=AgentAction.HANDOFF_AGENT,
            target_agent_key="specialist",
        )
        request = _make_request(agent_key="triage")
        events = []
        async for event in mgr.stream_execute_agent_handoff(
            resolution, request=request, history=[]
        ):
            events.append(event)

        # The final event should carry the handoff target with the correct agent key
        final = events[-1]
        assert final.handoff_target is not None
        assert final.handoff_target.target_agent_key == "specialist"


class TestVoiceSegmentOutcomeAgentFields:
    """Verify VoiceSegmentOutcome carries agent switching fields."""

    def test_default_fields_are_none(self):
        from agent_runtime.channels.voice import VoiceSegmentOutcome
        outcome = VoiceSegmentOutcome(action="handoff", handoff_reason="escalation")
        assert outcome.handoff_target_type is None
        assert outcome.handoff_target_agent_key is None

    def test_agent_target_fields(self):
        from agent_runtime.channels.voice import VoiceSegmentOutcome
        outcome = VoiceSegmentOutcome(
            action="handoff",
            handoff_reason="transfer to specialist",
            handoff_target_type="agent",
            handoff_target_agent_key="refund-specialist",
        )
        assert outcome.handoff_target_type == "agent"
        assert outcome.handoff_target_agent_key == "refund-specialist"

    def test_human_target_backward_compat(self):
        from agent_runtime.channels.voice import VoiceSegmentOutcome
        outcome = VoiceSegmentOutcome(
            action="handoff",
            handoff_reason="escalation",
            handoff_target_type="human",
        )
        assert outcome.handoff_target_type == "human"
        assert outcome.handoff_target_agent_key is None


# ===========================================================================
# SubAgentExecutor
# ===========================================================================


class TestSubAgentExecutor:
    def _parent_ctx(self, depth: int = 0, chain: str = "") -> SubAgentContext:
        return SubAgentContext(
            parent_agent_key="triage",
            parent_session_id="sess-1",
            parent_trace_id="trace-1",
            depth=depth,
            shared_metadata={_CHAIN_METADATA_KEY: chain},
        )

    @pytest.mark.asyncio
    async def test_normal_delegation_calls_runner(self):
        runner = StubRunner(_make_result(reply_text="analysis done"))
        exe = SubAgentExecutor(runner)
        result = await exe.run_sub_turn("analyst", "analyse Q1", self._parent_ctx())
        assert len(runner.calls) == 1
        assert runner.calls[0].agent_key == "analyst"
        assert result.reply_text == "analysis done"

    @pytest.mark.asyncio
    async def test_depth_limit_returns_safe_error(self):
        runner = StubRunner()
        exe = SubAgentExecutor(runner, max_depth=2)
        ctx = self._parent_ctx(depth=2)  # already at max
        result = await exe.run_sub_turn("analyst", "task", ctx)
        assert result.action is AgentAction.REPLY
        assert "depth" in result.reply_text.lower()
        assert len(runner.calls) == 0

    @pytest.mark.asyncio
    async def test_cycle_detection_returns_safe_error(self):
        runner = StubRunner()
        exe = SubAgentExecutor(runner)
        ctx = self._parent_ctx(chain="triage,analyst")  # analyst already in chain
        result = await exe.run_sub_turn("analyst", "task", ctx)
        assert result.action is AgentAction.REPLY
        assert "circular" in result.reply_text.lower()
        assert len(runner.calls) == 0

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_safe_error_when_loader_present(self):
        runner = StubRunner()
        loader = StaticAgentDefinitionLoader({})  # empty — agent not found
        exe = SubAgentExecutor(runner, definition_loader=loader)
        result = await exe.run_sub_turn("nonexistent", "task", self._parent_ctx())
        assert result.action is AgentAction.REPLY
        assert "not available" in result.reply_text
        assert len(runner.calls) == 0

    @pytest.mark.asyncio
    async def test_disabled_agent_returns_safe_error(self):
        loader = StaticAgentDefinitionLoader(
            {"disabled": _make_definition("disabled", status="disabled")}
        )
        runner = StubRunner()
        exe = SubAgentExecutor(runner, definition_loader=loader)
        result = await exe.run_sub_turn("disabled", "task", self._parent_ctx())
        assert result.action is AgentAction.REPLY
        assert len(runner.calls) == 0

    @pytest.mark.asyncio
    async def test_no_loader_skips_validation(self):
        runner = StubRunner(_make_result())
        exe = SubAgentExecutor(runner, definition_loader=None)
        result = await exe.run_sub_turn("any-agent", "task", self._parent_ctx())
        assert len(runner.calls) == 1

    @pytest.mark.asyncio
    async def test_runner_exception_captured_as_error_result(self):
        runner = StubRunner(side_effect=RuntimeError("gateway error"))
        exe = SubAgentExecutor(runner, definition_loader=None)
        result = await exe.run_sub_turn("analyst", "task", self._parent_ctx())
        assert result.action is AgentAction.REPLY
        assert result.error_message is not None
        assert "gateway error" in result.error_message

    @pytest.mark.asyncio
    async def test_chain_metadata_propagated_to_sub_request(self):
        runner = StubRunner(_make_result())
        exe = SubAgentExecutor(runner, definition_loader=None)
        ctx = self._parent_ctx(depth=1, chain="triage")
        await exe.run_sub_turn("specialist", "task", ctx)
        sub_req = runner.calls[0]
        assert "specialist" in sub_req.metadata.get(_CHAIN_METADATA_KEY, "")
        assert sub_req.metadata.get(_DEPTH_METADATA_KEY) == "2"

    @pytest.mark.asyncio
    async def test_context_summary_prepended_to_message(self):
        runner = StubRunner(_make_result())
        exe = SubAgentExecutor(runner, definition_loader=None)
        ctx = self._parent_ctx()
        ctx.summary = "Customer is angry about billing."
        await exe.run_sub_turn("specialist", "Help with billing", ctx)
        sub_req = runner.calls[0]
        assert "Customer is angry about billing." in sub_req.user_message


# ===========================================================================
# DelegateToAgentTool
# ===========================================================================


class TestDelegateToAgentTool:
    def _context(self, metadata: dict | None = None) -> ToolExecutionContext:
        return ToolExecutionContext(
            session_id="sess-1",
            trace_id="trace-1",
            agent_key="main",
            metadata=metadata or {},
        )

    @pytest.mark.asyncio
    async def test_missing_agent_key_returns_error(self):
        exe = SubAgentExecutor(StubRunner(), definition_loader=None)
        tool = DelegateToAgentTool(exe)
        result = await tool.execute({"task_message": "do something"}, self._context())
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_missing_task_message_returns_error(self):
        exe = SubAgentExecutor(StubRunner(), definition_loader=None)
        tool = DelegateToAgentTool(exe)
        result = await tool.execute({"agent_key": "analyst"}, self._context())
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_successful_delegation_returns_reply(self):
        runner = StubRunner(_make_result(reply_text="analysis complete"))
        exe = SubAgentExecutor(runner, definition_loader=None)
        tool = DelegateToAgentTool(exe)
        result = await tool.execute(
            {"agent_key": "analyst", "task_message": "analyse Q1"},
            self._context(),
        )
        assert result.status == "success"
        assert result.output == "analysis complete"

    @pytest.mark.asyncio
    async def test_human_handoff_from_sub_agent_surfaces_message(self):
        sub_result = _make_result(
            reply_text="I need to transfer you",
            action=AgentAction.HANDOFF,
        )
        runner = StubRunner(sub_result)
        exe = SubAgentExecutor(runner, definition_loader=None)
        tool = DelegateToAgentTool(exe)
        result = await tool.execute(
            {"agent_key": "specialist", "task_message": "help"},
            self._context(),
        )
        assert result.status == "success"
        assert "human handoff" in result.output.lower()

    @pytest.mark.asyncio
    async def test_context_passed_as_summary(self):
        runner = StubRunner(_make_result())
        exe = SubAgentExecutor(runner, definition_loader=None)
        tool = DelegateToAgentTool(exe)
        await tool.execute(
            {
                "agent_key": "analyst",
                "task_message": "query Q1",
                "context": "Customer complained about billing",
            },
            self._context(),
        )
        sub_req = runner.calls[0]
        assert "Customer complained about billing" in sub_req.user_message

    @pytest.mark.asyncio
    async def test_depth_metadata_propagated(self):
        runner = StubRunner(_make_result())
        exe = SubAgentExecutor(runner, definition_loader=None)
        tool = DelegateToAgentTool(exe)
        ctx = self._context(metadata={_DEPTH_METADATA_KEY: "1"})
        await tool.execute(
            {"agent_key": "analyst", "task_message": "task"},
            ctx,
        )
        sub_req = runner.calls[0]
        assert sub_req.metadata.get(_DEPTH_METADATA_KEY) == "2"

    def test_allowed_agents_restricts_enum_in_spec(self):
        exe = SubAgentExecutor(StubRunner(), definition_loader=None)
        tool = DelegateToAgentTool(exe, allowed_agents=["analyst", "translator"])
        agent_key_schema = tool.spec.parameters_schema["properties"]["agent_key"]
        assert agent_key_schema.get("enum") == ["analyst", "translator"]

    def test_no_allowed_agents_has_no_enum(self):
        exe = SubAgentExecutor(StubRunner(), definition_loader=None)
        tool = DelegateToAgentTool(exe)
        agent_key_schema = tool.spec.parameters_schema["properties"]["agent_key"]
        assert "enum" not in agent_key_schema


# ===========================================================================
# Phase 2 tail: Usage Accumulation
# ===========================================================================


from llm_gateway import UsageInfo


def _make_result_with_usage(
    *,
    reply_text: str = "ok",
    action: AgentAction = AgentAction.REPLY,
    input_tokens: int = 10,
    output_tokens: int = 5,
) -> AgentTurnResult:
    return AgentTurnResult(
        session_id="sess-1",
        trace_id="trace-1",
        action=action,
        reply_text=reply_text,
        agent_key="specialist",
        usage=UsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        ),
    )


class TestDelegationUsage:
    """delegation_usage is propagated from DelegationResult → ToolResult."""

    @pytest.mark.asyncio
    async def test_delegation_result_carries_usage(self):
        runner = StubRunner(_make_result_with_usage(input_tokens=10, output_tokens=5))
        exe = SubAgentExecutor(runner, definition_loader=None)

        ctx = SubAgentContext(
            parent_agent_key="main",
            parent_session_id="sess-1",
            parent_trace_id="trace-1",
        )
        result = await exe.run_sub_turn("analyst", "task", ctx)

        assert result.usage is not None
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 5

    @pytest.mark.asyncio
    async def test_tool_result_carries_delegation_usage(self):
        runner = StubRunner(_make_result_with_usage(input_tokens=10, output_tokens=5))
        exe = SubAgentExecutor(runner, definition_loader=None)
        tool = DelegateToAgentTool(exe)

        ctx = ToolExecutionContext(session_id="sess-1", trace_id="trace-1", agent_key="main")
        result = await tool.execute({"agent_key": "analyst", "task_message": "run"}, ctx)

        assert result.status == "success"
        assert result.delegation_usage is not None
        assert result.delegation_usage.input_tokens == 10
        assert result.delegation_usage.output_tokens == 5

    @pytest.mark.asyncio
    async def test_tool_result_carries_usage_on_handoff(self):
        runner = StubRunner(
            _make_result_with_usage(
                reply_text="transferring",
                action=AgentAction.HANDOFF,
                input_tokens=8,
                output_tokens=4,
            )
        )
        exe = SubAgentExecutor(runner, definition_loader=None)
        tool = DelegateToAgentTool(exe)

        ctx = ToolExecutionContext(session_id="sess-1", trace_id="trace-1", agent_key="main")
        result = await tool.execute({"agent_key": "specialist", "task_message": "help"}, ctx)

        assert result.delegation_usage is not None
        assert result.delegation_usage.input_tokens == 8

    @pytest.mark.asyncio
    async def test_tool_result_no_usage_on_error(self):
        """Error results (missing agent_key) don't carry delegation_usage."""
        exe = SubAgentExecutor(StubRunner(), definition_loader=None)
        tool = DelegateToAgentTool(exe)

        ctx = ToolExecutionContext(session_id="sess-1", trace_id="trace-1")
        result = await tool.execute({"task_message": "task"}, ctx)

        assert result.status == "error"
        assert result.delegation_usage is None


# ===========================================================================
# Phase 2 tail: stream_sub_turn
# ===========================================================================


# (StubStreamRunner is defined above at class TestHandoffManagerStreaming)


def _make_stream_events(
    deltas: list[str],
    final_text: str = "final reply",
    *,
    usage: UsageInfo | None = None,
) -> list:
    from agent_runtime.contracts.models import AgentTurnStreamEvent
    events = [
        AgentTurnStreamEvent(
            event_type="reply_delta",
            session_id="sess-1",
            trace_id="trace-1",
            delta=d,
        )
        for d in deltas
    ]
    events.append(
        AgentTurnStreamEvent(
            event_type="reply_completed",
            session_id="sess-1",
            trace_id="trace-1",
            reply_text=final_text,
            usage=usage,
        )
    )
    return events


class TestStreamSubTurn:
    def _ctx(self, depth: int = 0, chain: str = "") -> SubAgentContext:
        return SubAgentContext(
            parent_agent_key="main",
            parent_session_id="sess-1",
            parent_trace_id="trace-1",
            depth=depth,
            shared_metadata={
                _CHAIN_METADATA_KEY: chain,
                _DEPTH_METADATA_KEY: str(depth),
            },
        )

    @pytest.mark.asyncio
    async def test_streams_deltas_then_completed(self):
        events = _make_stream_events(["Hello", " world"], final_text="Hello world")
        runner = StubStreamRunner(events)
        exe = SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)

        collected = []
        async for ev in exe.stream_sub_turn("analyst", "task", self._ctx()):
            collected.append(ev)

        deltas = [e for e in collected if e.event_type == "reply_delta"]
        completed = [e for e in collected if e.event_type == "reply_completed"]
        assert [d.delta for d in deltas] == ["Hello", " world"]
        assert len(completed) == 1
        assert completed[0].reply_text == "Hello world"

    @pytest.mark.asyncio
    async def test_stream_carries_usage(self):
        usage = UsageInfo(input_tokens=12, output_tokens=8, total_tokens=20)
        events = _make_stream_events(["ok"], usage=usage)
        runner = StubStreamRunner(events)
        exe = SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)

        collected = []
        async for ev in exe.stream_sub_turn("analyst", "task", self._ctx()):
            collected.append(ev)

        completed = [e for e in collected if e.event_type == "reply_completed"]
        assert completed[0].usage is not None
        assert completed[0].usage.input_tokens == 12

    @pytest.mark.asyncio
    async def test_depth_limit_emits_error_completed(self):
        runner = StubStreamRunner([])
        exe = SubAgentExecutor(runner, definition_loader=None, stream_runner=runner, max_depth=2)

        ctx = self._ctx(depth=2)  # at max_depth
        collected = []
        async for ev in exe.stream_sub_turn("analyst", "task", ctx):
            collected.append(ev)

        assert len(collected) == 1
        assert collected[0].event_type == "reply_completed"
        assert "depth" in collected[0].reply_text.lower()
        assert runner.calls == []  # runner never called

    @pytest.mark.asyncio
    async def test_cycle_detection_emits_error_completed(self):
        runner = StubStreamRunner([])
        exe = SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)

        ctx = self._ctx(chain="main,analyst")
        collected = []
        async for ev in exe.stream_sub_turn("analyst", "task", ctx):
            collected.append(ev)

        assert len(collected) == 1
        assert "circular" in collected[0].reply_text.lower()
        assert runner.calls == []

    @pytest.mark.asyncio
    async def test_unknown_agent_emits_error_completed(self):
        from agent_runtime.definition.loader import StaticAgentDefinitionLoader
        loader = StaticAgentDefinitionLoader({})  # no agents
        runner = StubStreamRunner([])
        exe = SubAgentExecutor(runner, definition_loader=loader, stream_runner=runner)

        collected = []
        async for ev in exe.stream_sub_turn("ghost", "task", self._ctx()):
            collected.append(ev)

        assert len(collected) == 1
        assert "ghost" in collected[0].reply_text

    @pytest.mark.asyncio
    async def test_fallback_when_no_stream_runner(self):
        """When stream_runner is absent, a single reply_completed is emitted."""
        runner = StubRunner(_make_result(reply_text="non-streaming reply"))
        exe = SubAgentExecutor(runner, definition_loader=None)  # no stream_runner

        collected = []
        async for ev in exe.stream_sub_turn("analyst", "task", self._ctx()):
            collected.append(ev)

        assert len(collected) == 1
        assert collected[0].event_type == "reply_completed"
        assert collected[0].reply_text == "non-streaming reply"

    @pytest.mark.asyncio
    async def test_can_stream_true_when_stream_runner_provided(self):
        runner = StubStreamRunner([])
        exe = SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)
        assert exe.can_stream is True

    def test_can_stream_false_without_stream_runner(self):
        exe = SubAgentExecutor(StubRunner(), definition_loader=None)
        assert exe.can_stream is False


# ===========================================================================
# Phase 2 tail: DelegateToAgentTool.execute_stream
# ===========================================================================


class TestDelegateToAgentToolStream:
    def _context(self) -> ToolExecutionContext:
        return ToolExecutionContext(
            session_id="sess-1",
            trace_id="trace-1",
            agent_key="main",
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_execute_stream_forwards_deltas_and_completed(self):
        events = _make_stream_events(["chunk1", "chunk2"], final_text="chunk1chunk2")
        runner = StubStreamRunner(events)
        exe = SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)
        tool = DelegateToAgentTool(exe)

        collected = []
        async for ev in tool.execute_stream(
            {"agent_key": "analyst", "task_message": "run"}, self._context()
        ):
            collected.append(ev)

        deltas = [e for e in collected if e.event_type == "reply_delta"]
        assert [d.delta for d in deltas] == ["chunk1", "chunk2"]
        completed = [e for e in collected if e.event_type == "reply_completed"]
        assert completed[0].reply_text == "chunk1chunk2"

    @pytest.mark.asyncio
    async def test_execute_stream_missing_agent_key_emits_error(self):
        exe = SubAgentExecutor(StubStreamRunner([]), definition_loader=None, stream_runner=StubStreamRunner([]))
        tool = DelegateToAgentTool(exe)

        collected = []
        async for ev in tool.execute_stream({"task_message": "task"}, self._context()):
            collected.append(ev)

        assert len(collected) == 1
        assert collected[0].event_type == "reply_completed"
        assert "agent_key" in collected[0].reply_text

    @pytest.mark.asyncio
    async def test_execute_stream_missing_task_message_emits_error(self):
        exe = SubAgentExecutor(StubStreamRunner([]), definition_loader=None, stream_runner=StubStreamRunner([]))
        tool = DelegateToAgentTool(exe)

        collected = []
        async for ev in tool.execute_stream({"agent_key": "analyst"}, self._context()):
            collected.append(ev)

        assert len(collected) == 1
        assert "task_message" in collected[0].reply_text

    def test_can_stream_property(self):
        runner = StubStreamRunner([])
        exe = SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)
        tool = DelegateToAgentTool(exe)
        assert tool.can_stream is True

    def test_can_stream_false_without_stream_runner(self):
        exe = SubAgentExecutor(StubRunner(), definition_loader=None)
        tool = DelegateToAgentTool(exe)
        assert tool.can_stream is False

    @pytest.mark.asyncio
    async def test_context_summary_passed_to_stream_sub_turn(self):
        events = _make_stream_events(["ok"])
        runner = StubStreamRunner(events)
        exe = SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)
        tool = DelegateToAgentTool(exe)

        async for _ in tool.execute_stream(
            {"agent_key": "analyst", "task_message": "query", "context": "some context"},
            self._context(),
        ):
            pass

        assert len(runner.calls) == 1
        req = runner.calls[0]
        assert "some context" in req.user_message
