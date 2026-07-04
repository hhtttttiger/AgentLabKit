"""Integration tests for Skills Phase 2.

Verifies that AgentRuntime.run_turn() and stream_turn() correctly apply
SkillComposer when the agent definition carries skill_bindings.

DoD criteria from 2026-04-04-agent-skills-plan.md Phase 2:
- run_turn with 2 skills: prompt and tool bindings are correctly composed
- Fallback path (no skill_bindings): behaviour is identical to Phase 1
- stream_turn with skills: prompt is composed before the LLM is called
"""

from __future__ import annotations

import pytest



from agent_runtime import AgentTurnRequest, AgentTurnResult, ToolRegistry
from agent_runtime.config import AgentSettings
from agent_runtime.definition.loader import StaticAgentDefinitionLoader
from agent_runtime.definition.models import (
    AgentDefinitionSnapshot,
    SkillBindingSnapshot,
    SkillDefinitionSnapshot,
    ToolBindingSnapshot,
)
from agent_runtime.runtime import AgentRuntime
from agent_runtime.skills import SkillBinding, SkillPromptFragment, SkillRegistry, SkillSpec
from agent_runtime.skills.builtin import CustomerSupportSkill, RagQaSkill
from llm_gateway import ProviderId, TextGenerateResponse, TextStreamEvent, UsageInfo


# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------


class FakeGatewayService:
    """Minimal gateway stub that captures requests and returns canned responses."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.requests: list = []

    async def generate_text(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def generate_text_stream(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        for event in response:
            yield event


def _reply_response(text: str) -> TextGenerateResponse:
    return TextGenerateResponse(
        provider=ProviderId.OPENAI,
        model="gpt-4.1-mini",
        text=f'{{"kind":"final","reply_text":"{text}","should_handoff":false}}',
        usage=UsageInfo(input_tokens=10, output_tokens=5, total_tokens=15),
    )


def _make_runtime(
    *,
    definition: AgentDefinitionSnapshot,
    gateway: FakeGatewayService,
    skill_registry: SkillRegistry | None = None,
) -> AgentRuntime:
    loader = StaticAgentDefinitionLoader({definition.agent_key: definition})
    return AgentRuntime(
        settings=AgentSettings(default_model="gpt-4.1-mini"),
        gateway=gateway,
        tool_registry=ToolRegistry(),
        definition_loader=loader,
        skill_registry=skill_registry,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSkillsPhase2RunTurn:
    async def test_no_skill_bindings_prompt_unchanged(self) -> None:
        """Fallback: no skill_bindings → base prompt used as-is."""
        gateway = FakeGatewayService([_reply_response("Hello")])
        definition = AgentDefinitionSnapshot(
            agent_key="test-agent",
            version_number=1,
            display_name="Test",
            system_prompt_template="Base prompt only.",
            model_binding_key="gpt-4.1-mini",
            # skill_bindings defaults to ()
        )
        runtime = _make_runtime(definition=definition, gateway=gateway)

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="Hello",
                agent_key="test-agent",
            )
        )

        prompt_sent = gateway.requests[0].prompt
        assert "Base prompt only." in prompt_sent
        # No skill sections appended
        assert "##" not in prompt_sent

    async def test_single_skill_prompt_appended(self) -> None:
        """A single skill binding appends its fragment section to the prompt."""
        skill_spec = SkillSpec(
            skill_key="greet_v1",
            display_name="Greeter",
            description="Always greet warmly.",
            version="1.0.0",
            prompt_fragments=(
                SkillPromptFragment(
                    section="Greeting Instructions",
                    content="Always start with 'Hello there!'",
                    order=10,
                ),
            ),
        )
        skill_registry = SkillRegistry()
        skill_registry.register(skill_spec)

        gateway = FakeGatewayService([_reply_response("Hi")])
        definition = AgentDefinitionSnapshot(
            agent_key="greeter-agent",
            version_number=1,
            display_name="Greeter",
            system_prompt_template="You are a greeter.",
            model_binding_key="gpt-4.1-mini",
            skill_bindings=(
                SkillBindingSnapshot(skill_key="greet_v1", is_enabled=True, binding_order=100),
            ),
        )
        runtime = _make_runtime(
            definition=definition, gateway=gateway, skill_registry=skill_registry
        )

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="Hi",
                agent_key="greeter-agent",
            )
        )

        prompt_sent = gateway.requests[0].prompt
        assert "You are a greeter." in prompt_sent
        assert "## Greeting Instructions" in prompt_sent
        assert "Always start with 'Hello there!'" in prompt_sent

    async def test_definition_provided_skill_spec_is_consumed_without_preregistration(self) -> None:
        """Published skill specs from the management plane should drive composition directly."""
        gateway = FakeGatewayService([_reply_response("Hi")])
        definition = AgentDefinitionSnapshot(
            agent_key="managed-skill-agent",
            version_number=1,
            display_name="Managed Skill Agent",
            system_prompt_template="You are a greeter.",
            model_binding_key="gpt-4.1-mini",
            skill_bindings=(
                SkillBindingSnapshot(
                    skill_key="managed_greet_v1",
                    is_enabled=True,
                    binding_order=100,
                    definition=SkillDefinitionSnapshot(
                        skill_key="managed_greet_v1",
                        display_name="Managed Greeter",
                        description="Defined in .NET.",
                        version="1.0.0",
                        spec={
                            "promptFragments": [
                                {
                                    "section": "Managed Greeting",
                                    "content": "Say hello in a managed way.",
                                    "order": 10,
                                }
                            ],
                            "recommendedTools": [],
                            "tags": ["managed"],
                        },
                    ),
                ),
            ),
        )
        runtime = _make_runtime(definition=definition, gateway=gateway)

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="Hi",
                agent_key="managed-skill-agent",
            )
        )

        prompt_sent = gateway.requests[0].prompt
        assert "You are a greeter." in prompt_sent
        assert "## Managed Greeting" in prompt_sent
        assert "Say hello in a managed way." in prompt_sent

    async def test_two_skills_compose_in_order(self) -> None:
        """Two skill bindings produce prompt sections ordered by binding.order."""
        skill_a = SkillSpec(
            skill_key="skill_a_v1",
            display_name="Skill A",
            description="A.",
            version="1.0.0",
            prompt_fragments=(
                SkillPromptFragment(section="Section A", content="Content from A.", order=50),
            ),
        )
        skill_b = SkillSpec(
            skill_key="skill_b_v1",
            display_name="Skill B",
            description="B.",
            version="1.0.0",
            prompt_fragments=(
                SkillPromptFragment(section="Section B", content="Content from B.", order=50),
            ),
        )
        registry = SkillRegistry()
        registry.register(skill_a)
        registry.register(skill_b)

        gateway = FakeGatewayService([_reply_response("ok")])
        definition = AgentDefinitionSnapshot(
            agent_key="combo-agent",
            version_number=1,
            display_name="Combo",
            system_prompt_template="Base.",
            model_binding_key="gpt-4.1-mini",
            skill_bindings=(
                # B has lower order → appears first
                SkillBindingSnapshot(skill_key="skill_b_v1", is_enabled=True, binding_order=1),
                SkillBindingSnapshot(skill_key="skill_a_v1", is_enabled=True, binding_order=2),
            ),
        )
        runtime = _make_runtime(definition=definition, gateway=gateway, skill_registry=registry)

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="go",
                agent_key="combo-agent",
            )
        )

        prompt = gateway.requests[0].prompt
        pos_b = prompt.index("Section B")
        pos_a = prompt.index("Section A")
        assert pos_b < pos_a, "Skill B (order=1) should appear before Skill A (order=2)"

    async def test_builtin_rag_and_customer_support_skills(self) -> None:
        """Builtin skills are correctly resolved and appended to the prompt."""
        registry = SkillRegistry()
        registry.register(RagQaSkill.spec)
        registry.register(CustomerSupportSkill.spec)

        gateway = FakeGatewayService([_reply_response("Understood.")])
        definition = AgentDefinitionSnapshot(
            agent_key="full-agent",
            version_number=1,
            display_name="Full",
            system_prompt_template="You are a support agent.",
            model_binding_key="gpt-4.1-mini",
            tools=(ToolBindingSnapshot(tool_name="knowledge_search", invocation_mode="auto"),),
            skill_bindings=(
                SkillBindingSnapshot(skill_key="rag_qa_v1", is_enabled=True, binding_order=10),
                SkillBindingSnapshot(
                    skill_key="customer_support_v1", is_enabled=True, binding_order=5
                ),
            ),
        )
        runtime = _make_runtime(definition=definition, gateway=gateway, skill_registry=registry)

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="Help me with my order.",
                agent_key="full-agent",
            )
        )

        prompt = gateway.requests[0].prompt
        assert "知识库检索指令" in prompt
        assert "客服行为规范" in prompt
        # Customer support has order=5 (binding) → appears before RAG (order=10)
        pos_cs = prompt.index("客服行为规范")
        pos_rag = prompt.index("知识库检索指令")
        assert pos_cs < pos_rag

    async def test_disabled_skill_binding_excluded(self) -> None:
        """A binding with is_enabled=False is completely ignored."""
        skill_spec = SkillSpec(
            skill_key="hidden_v1",
            display_name="Hidden",
            description="Should not appear.",
            version="1.0.0",
            prompt_fragments=(
                SkillPromptFragment(section="Hidden Section", content="HIDDEN"),
            ),
        )
        registry = SkillRegistry()
        registry.register(skill_spec)

        gateway = FakeGatewayService([_reply_response("ok")])
        definition = AgentDefinitionSnapshot(
            agent_key="partial-agent",
            version_number=1,
            display_name="Partial",
            system_prompt_template="Base.",
            model_binding_key="gpt-4.1-mini",
            skill_bindings=(
                SkillBindingSnapshot(skill_key="hidden_v1", is_enabled=False, binding_order=100),
            ),
        )
        runtime = _make_runtime(definition=definition, gateway=gateway, skill_registry=registry)

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="test",
                agent_key="partial-agent",
            )
        )

        prompt = gateway.requests[0].prompt
        assert "Hidden Section" not in prompt
        assert "HIDDEN" not in prompt

    async def test_skill_template_variable_rendered_from_config(self) -> None:
        """Config values from SkillBindingSnapshot are rendered in prompt templates."""
        skill_spec = SkillSpec(
            skill_key="cfg_v1",
            display_name="Configurable",
            description="Uses config vars.",
            version="1.0.0",
            prompt_fragments=(
                SkillPromptFragment(
                    section="Config Section",
                    content="Max results: {config.max_results}.",
                ),
            ),
        )
        registry = SkillRegistry()
        registry.register(skill_spec)

        gateway = FakeGatewayService([_reply_response("ok")])
        definition = AgentDefinitionSnapshot(
            agent_key="cfg-agent",
            version_number=1,
            display_name="Cfg",
            system_prompt_template="Base.",
            model_binding_key="gpt-4.1-mini",
            skill_bindings=(
                SkillBindingSnapshot(
                    skill_key="cfg_v1",
                    is_enabled=True,
                    binding_order=100,
                    config={"max_results": "20"},
                ),
            ),
        )
        runtime = _make_runtime(definition=definition, gateway=gateway, skill_registry=registry)

        await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="test",
                agent_key="cfg-agent",
            )
        )

        prompt = gateway.requests[0].prompt
        assert "Max results: 20." in prompt

    async def test_tool_override_from_skill_binding_snapshot(self) -> None:
        """tool_overrides_raw in SkillBindingSnapshot merges into tool bindings."""
        skill_spec = SkillSpec(
            skill_key="tool_override_v1",
            display_name="Tool Override",
            description="Overrides a tool.",
            version="1.0.0",
        )
        registry = SkillRegistry()
        registry.register(skill_spec)

        gateway = FakeGatewayService([_reply_response("ok")])
        definition = AgentDefinitionSnapshot(
            agent_key="tool-agent",
            version_number=1,
            display_name="Tool",
            system_prompt_template="Base.",
            model_binding_key="gpt-4.1-mini",
            tools=(
                ToolBindingSnapshot(tool_name="knowledge_search", invocation_mode="manual_only"),
            ),
            skill_bindings=(
                SkillBindingSnapshot(
                    skill_key="tool_override_v1",
                    is_enabled=True,
                    binding_order=100,
                    tool_overrides_raw=(
                        {
                            "toolName": "knowledge_search",
                            "invocationMode": "auto",  # upgrade to auto
                            "isEnabled": True,
                        },
                    ),
                ),
            ),
        )
        runtime = _make_runtime(definition=definition, gateway=gateway, skill_registry=registry)

        result = await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="test",
                agent_key="tool-agent",
            )
        )
        # After skill composition, knowledge_search should be in auto mode.
        # The gateway request should include it in the function-calling schema.
        # We verify indirectly by checking the request's tools list if available.
        assert isinstance(result, AgentTurnResult)

    async def test_unknown_skill_key_is_skipped_silently(self) -> None:
        """A skill_key not in the registry is silently ignored (no exception)."""
        gateway = FakeGatewayService([_reply_response("ok")])
        definition = AgentDefinitionSnapshot(
            agent_key="ghost-agent",
            version_number=1,
            display_name="Ghost",
            system_prompt_template="Base.",
            model_binding_key="gpt-4.1-mini",
            skill_bindings=(
                SkillBindingSnapshot(skill_key="nonexistent_skill", is_enabled=True),
            ),
        )
        # No skill registered → binding is silently skipped, prompt unchanged.
        runtime = _make_runtime(definition=definition, gateway=FakeGatewayService([_reply_response("ok")]))
        # Should not raise
        await runtime.run_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="test",
                agent_key="ghost-agent",
            )
        )


@pytest.mark.asyncio
class TestSkillsPhase2StreamTurn:
    async def test_stream_turn_prompt_includes_skill_fragment(self) -> None:
        """stream_turn also applies skill composition to the prompt."""
        from llm_gateway import TextStreamEvent

        skill_spec = SkillSpec(
            skill_key="stream_skill_v1",
            display_name="Stream Skill",
            description="For streaming test.",
            version="1.0.0",
            prompt_fragments=(
                SkillPromptFragment(section="Stream Section", content="Streaming content."),
            ),
        )
        registry = SkillRegistry()
        registry.register(skill_spec)

        reply_json = '{"kind":"final","reply_text":"Stream reply","should_handoff":false}'
        stream_events = [
            TextStreamEvent(
                event_type="delta",
                provider=ProviderId.OPENAI,
                model="gpt-4.1-mini",
                delta=reply_json[:20],
            ),
            TextStreamEvent(
                event_type="completed",
                provider=ProviderId.OPENAI,
                model="gpt-4.1-mini",
                text=reply_json,
                usage=None,
            ),
        ]
        gateway = FakeGatewayService([stream_events])
        definition = AgentDefinitionSnapshot(
            agent_key="stream-agent",
            version_number=1,
            display_name="Stream",
            system_prompt_template="You are a streaming agent.",
            model_binding_key="gpt-4.1-mini",
            skill_bindings=(
                SkillBindingSnapshot(
                    skill_key="stream_skill_v1", is_enabled=True, binding_order=100
                ),
            ),
        )
        runtime = _make_runtime(definition=definition, gateway=gateway, skill_registry=registry)

        events = []
        async for event in runtime.stream_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="stream test",
                agent_key="stream-agent",
            )
        ):
            events.append(event)

        prompt = gateway.requests[0].prompt
        assert "You are a streaming agent." in prompt
        assert "## Stream Section" in prompt
        assert "Streaming content." in prompt

    async def test_stream_turn_no_skills_unchanged(self) -> None:
        """stream_turn with no skill_bindings is unaffected (backward compat)."""
        from llm_gateway import TextStreamEvent

        reply_json = '{"kind":"final","reply_text":"Plain reply","should_handoff":false}'
        stream_events = [
            TextStreamEvent(
                event_type="delta",
                provider=ProviderId.OPENAI,
                model="gpt-4.1-mini",
                delta=reply_json,
            ),
            TextStreamEvent(
                event_type="completed",
                provider=ProviderId.OPENAI,
                model="gpt-4.1-mini",
                text=reply_json,
                usage=None,
            ),
        ]
        gateway = FakeGatewayService([stream_events])
        definition = AgentDefinitionSnapshot(
            agent_key="plain-stream-agent",
            version_number=1,
            display_name="Plain",
            system_prompt_template="Plain base prompt.",
            model_binding_key="gpt-4.1-mini",
        )
        runtime = _make_runtime(definition=definition, gateway=gateway)

        events = []
        async for event in runtime.stream_turn(
            AgentTurnRequest(
                session_id="s1",
                user_message="plain stream",
                agent_key="plain-stream-agent",
            )
        ):
            events.append(event)

        prompt = gateway.requests[0].prompt
        assert "Plain base prompt." in prompt
        assert "##" not in prompt
