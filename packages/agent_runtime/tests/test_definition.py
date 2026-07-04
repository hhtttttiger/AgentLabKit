"""Tests for agent definition models, cache, and static loader."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, fields
from types import SimpleNamespace

import pytest

from agent_runtime.definition.models import (
    AgentDefinitionSnapshot,
    KnowledgeBindingSnapshot,
    ToolBindingSnapshot,
    VoiceGuardrailsSnapshot,
)
from agent_runtime.definition.cache import InMemoryAgentDefinitionCache
from agent_runtime.definition.loader import (
    SqlAlchemyAgentDefinitionLoader,
    StaticAgentDefinitionLoader,
)


def _sample_definition(
    agent_key: str = "test-agent",
    version_number: int = 1,
    **kwargs,
) -> AgentDefinitionSnapshot:
    defaults = dict(
        agent_key=agent_key,
        version_number=version_number,
        display_name="Test Agent",
        system_prompt_template="You are a test agent.",
        model_binding_key="gateway.default_text",
        tools=(
            ToolBindingSnapshot(tool_name="order.query", invocation_mode="auto"),
            ToolBindingSnapshot(tool_name="order.cancel", invocation_mode="manual_only"),
            ToolBindingSnapshot(tool_name="debug.internal", invocation_mode="disabled"),
        ),
        checksum="sha256:abc123",
    )
    defaults.update(kwargs)
    return AgentDefinitionSnapshot(**defaults)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Model tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAgentDefinitionSnapshot:
    def test_auto_tool_names(self):
        d = _sample_definition()
        assert d.auto_tool_names == frozenset({"order.query"})

    def test_enabled_tool_names(self):
        d = _sample_definition()
        assert d.enabled_tool_names == frozenset({"order.query", "order.cancel"})

    def test_immutable(self):
        d = _sample_definition()
        with pytest.raises(AttributeError):
            d.agent_key = "changed"  # type: ignore[misc]

    def test_knowledge_bindings_default_empty(self):
        d = _sample_definition()

        assert d.knowledge_bindings == ()

    def test_knowledge_binding_snapshot_defaults_config_version(self):
        binding = KnowledgeBindingSnapshot(
            knowledge_base_id="101",
            sort_order=10,
            config={"max_results": 3},
        )

        assert binding.config_version == 1

    def test_voice_guardrails_are_derived_from_local_guardrails_policy(self):
        definition = _sample_definition(
            guardrails_policy={
                "voice_guardrails": {
                    "mode": "observe_only",
                    "revision": 9,
                    "judge_timeout_ms": 125,
                    "generator_timeout_ms": 175,
                    "max_added_latency_ms": 450,
                    "actions": ["interrupt_only", "fallback_reply"],
                }
            }
        )

        assert definition.voice_guardrails == VoiceGuardrailsSnapshot(
            mode="observe_only",
            revision=9,
            judge_timeout_ms=125,
            generator_timeout_ms=175,
            max_added_latency_ms=450,
            actions=("interrupt_only", "fallback_reply"),
        )

    def test_voice_guardrails_are_not_stored_as_separate_snapshot_field(self):
        definition = _sample_definition(guardrails_policy={"voice_guardrails": {}})

        assert "voice_guardrails" not in {field.name for field in fields(AgentDefinitionSnapshot)}
        assert "voice_guardrails" not in asdict(definition)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cache tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestInMemoryCache:
    @pytest.fixture
    def cache(self):
        return InMemoryAgentDefinitionCache(ttl_seconds=10.0)

    @pytest.mark.asyncio
    async def test_put_and_get(self, cache):
        d = _sample_definition()
        await cache.put(d)
        result = await cache.get("test-agent")
        assert result is not None
        assert result.agent_key == "test-agent"

    @pytest.mark.asyncio
    async def test_get_versioned(self, cache):
        d = _sample_definition()
        await cache.put(d)
        result = await cache.get("test-agent", 1)
        assert result is not None
        assert result.version_number == 1

    @pytest.mark.asyncio
    async def test_get_miss(self, cache):
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_specific(self, cache):
        d1 = _sample_definition(agent_key="agent-a")
        d2 = _sample_definition(agent_key="agent-b")
        await cache.put(d1)
        await cache.put(d2)
        await cache.invalidate("agent-a")
        assert await cache.get("agent-a") is None
        assert await cache.get("agent-b") is not None

    @pytest.mark.asyncio
    async def test_invalidate_all(self, cache):
        d1 = _sample_definition(agent_key="agent-a")
        d2 = _sample_definition(agent_key="agent-b")
        await cache.put(d1)
        await cache.put(d2)
        await cache.invalidate()
        assert await cache.get("agent-a") is None
        assert await cache.get("agent-b") is None

    @pytest.mark.asyncio
    async def test_revision_tracking(self, cache):
        assert await cache.get_revision() == 0
        await cache.set_revision(5)
        assert await cache.get_revision() == 5

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        cache = InMemoryAgentDefinitionCache(ttl_seconds=0.01)
        d = _sample_definition()
        await cache.put(d)
        await asyncio.sleep(0.02)
        assert await cache.get("test-agent") is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Static loader tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStaticLoader:
    @pytest.mark.asyncio
    async def test_load_existing(self):
        d = _sample_definition()
        loader = StaticAgentDefinitionLoader({"test-agent": d})
        result = await loader.load("test-agent")
        assert result is not None
        assert result.agent_key == "test-agent"

    @pytest.mark.asyncio
    async def test_load_nonexistent(self):
        loader = StaticAgentDefinitionLoader()
        result = await loader.load("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_load_wrong_version(self):
        d = _sample_definition(version_number=1)
        loader = StaticAgentDefinitionLoader({"test-agent": d})
        result = await loader.load("test-agent", 99)
        assert result is None

    @pytest.mark.asyncio
    async def test_check_revision(self):
        loader = StaticAgentDefinitionLoader()
        assert await loader.check_revision() == 1

    @pytest.mark.asyncio
    async def test_register(self):
        loader = StaticAgentDefinitionLoader()
        d = _sample_definition(agent_key="new-agent")
        loader.register(d)
        result = await loader.load("new-agent")
        assert result is not None


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, query):
        del query
        return _FakeExecuteResult(
            sorted(self._rows, key=lambda row: (row.sort_order, row.knowledge_base_id))
        )


class TestSqlAlchemyAgentDefinitionLoader:
    @pytest.mark.asyncio
    async def test_load_knowledge_bindings_normalizes_enabled_rows(self):
        rows = [
            SimpleNamespace(
                knowledge_base_id=202,
                sort_order=20,
                config_json={"max_results": 2},
            ),
            SimpleNamespace(
                knowledge_base_id=101,
                sort_order=10,
                config_json={},
            ),
        ]
        loader = SqlAlchemyAgentDefinitionLoader(session_factory=lambda: None)  # type: ignore[arg-type]

        bindings = await loader._load_knowledge_bindings(_FakeSession(rows), version_id=3)  # noqa: SLF001

        assert bindings == (
            KnowledgeBindingSnapshot(
                knowledge_base_id="101",
                sort_order=10,
                config={},
                config_version=1,
            ),
            KnowledgeBindingSnapshot(
                knowledge_base_id="202",
                sort_order=20,
                config={"max_results": 2},
                config_version=1,
            ),
        )

