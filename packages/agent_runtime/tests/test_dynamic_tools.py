"""Unit tests for the dynamic tool system (Phase 1).

Covers:
- DynamicToolRegistry: register/unregister/duplicate/lookup/list
- DynamicToolRegistry: list_filtered with ToolBinding
- DynamicToolRegistry: build_tool_definitions and build_pydantic_ai_tools
- ToolExecutor: success, timeout, error isolation, retries
- ToolFilter: all/whitelist/empty bindings, disabled, manual_only, unknown
- SchemaValidator: valid/invalid/required/types/ranges (jsonschema & fallback)
- KnowledgeSearchTool / TimeNowTool / CalculatorTool: happy path + edge cases
- ToolRegistry: backward compat with settings.enable_knowledge_tool
- binding_from_snapshot: ToolBindingSnapshot → ToolBinding conversion
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest



from agent_runtime.tools import (
    CalculatorTool,
    DynamicToolRegistry,
    KnowledgeSearchTool,
    SchemaValidator,
    TimeNowTool,
    ToolBinding,
    ToolExecutionContext,
    ToolExecutor,
    ToolFilter,
    ToolRegistry,
    ToolResult,
    ToolSpec,
    binding_from_snapshot,
    validate_arguments,
)
from agent_runtime.config import AgentSettings
from agent_runtime.contracts import KnowledgeChunk
from agent_runtime.definition.models import KnowledgeBindingSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(name: str = "test_tool", timeout: float = 5.0, retries: int = 0, idempotent: bool = True) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=f"Description for {name}",
        parameters_schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        timeout_seconds=timeout,
        max_retries=retries,
        is_idempotent=idempotent,
    )


def _make_context(session_id: str = "s1", trace_id: str = "t1") -> ToolExecutionContext:
    return ToolExecutionContext(session_id=session_id, trace_id=trace_id)


class _EchoHandler:
    """Returns the 'value' argument as output."""
    async def execute(self, arguments: dict, context: ToolExecutionContext) -> ToolResult:
        return ToolResult(output=arguments.get("value", ""), status="success")


class _ErrorHandler:
    """Always raises RuntimeError."""
    async def execute(self, arguments: dict, context: ToolExecutionContext) -> ToolResult:
        raise RuntimeError("intentional error")


class _TimeoutHandler:
    """Sleeps forever."""
    async def execute(self, arguments: dict, context: ToolExecutionContext) -> ToolResult:
        await asyncio.sleep(999)
        return ToolResult(output="never", status="success")  # unreachable


class _RetryTrackingHandler:
    """Fails N-1 times then succeeds."""
    def __init__(self, fail_count: int):
        self.calls = 0
        self._fail_count = fail_count

    async def execute(self, arguments: dict, context: ToolExecutionContext) -> ToolResult:
        self.calls += 1
        if self.calls <= self._fail_count:
            raise RuntimeError(f"attempt {self.calls} failed")
        return ToolResult(output="ok", status="success")


class _ScopedKnowledgeProvider:
    def __init__(self) -> None:
        self.global_calls = 0
        self.scoped_calls: list[tuple[tuple[KnowledgeBindingSnapshot, ...], str, int, str | None, int | None]] = []

    def search(self, query: str, top_k: int = 5):
        self.global_calls += 1
        raise AssertionError("knowledge_search must not use global search when bindings are in context")

    async def search_bound_knowledge_bases(
        self,
        *,
        knowledge_bindings,
        query: str,
        top_k: int,
        agent_key: str | None = None,
        agent_version: int | None = None,
    ):
        bindings = tuple(knowledge_bindings)
        self.scoped_calls.append((bindings, query, top_k, agent_key, agent_version))
        return [
            KnowledgeChunk(
                title="Refund policy",
                content="Refunds are available within 30 days.",
                source="kb://101/refunds",
                metadata={
                    "knowledge_base_id": bindings[0].knowledge_base_id,
                    "binding_config_version": str(bindings[0].config_version),
                },
            )
        ]


class _ContextEchoHandler:
    """Captures the context passed to the tool and returns one field."""

    def __init__(self) -> None:
        self.last_context: ToolExecutionContext | None = None

    async def execute(self, arguments: dict, context: ToolExecutionContext) -> ToolResult:
        self.last_context = context
        return ToolResult(output=context.session_id, status="success")


# ---------------------------------------------------------------------------
# DynamicToolRegistry — registration
# ---------------------------------------------------------------------------


class TestDynamicToolRegistryRegistration:
    def test_register_and_list_all(self):
        reg = DynamicToolRegistry()
        spec = _make_spec("tool_a")
        handler = _EchoHandler()
        reg.register(spec, handler)
        all_specs = reg.list_all()
        assert len(all_specs) == 1
        assert all_specs[0].name == "tool_a"

    def test_register_multiple(self):
        reg = DynamicToolRegistry()
        for name in ("a", "b", "c"):
            reg.register(_make_spec(name), _EchoHandler())
        assert {s.name for s in reg.list_all()} == {"a", "b", "c"}

    def test_duplicate_registration_raises(self):
        reg = DynamicToolRegistry()
        spec = _make_spec("dup")
        reg.register(spec, _EchoHandler())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(spec, _EchoHandler())

    def test_register_or_replace_overwrites(self):
        reg = DynamicToolRegistry()
        spec = _make_spec("x")
        reg.register(spec, _EchoHandler())
        handler2 = _EchoHandler()
        reg.register_or_replace(spec, handler2)
        assert reg.get_handler("x") is handler2

    def test_unregister_returns_true_when_exists(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("del_me"), _EchoHandler())
        assert reg.unregister("del_me") is True
        assert reg.list_all() == []

    def test_unregister_returns_false_when_missing(self):
        reg = DynamicToolRegistry()
        assert reg.unregister("ghost") is False

    def test_get_spec_returns_none_for_unknown(self):
        reg = DynamicToolRegistry()
        assert reg.get_spec("missing") is None

    def test_get_handler_returns_none_for_unknown(self):
        reg = DynamicToolRegistry()
        assert reg.get_handler("missing") is None

    def test_get_spec_after_unregister_returns_none(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("gone"), _EchoHandler())
        reg.unregister("gone")
        assert reg.get_spec("gone") is None


# ---------------------------------------------------------------------------
# DynamicToolRegistry — filtering
# ---------------------------------------------------------------------------


class TestDynamicToolRegistryFiltering:
    def _reg_with_abc(self) -> DynamicToolRegistry:
        reg = DynamicToolRegistry()
        for name in ("a", "b", "c"):
            reg.register(_make_spec(name), _EchoHandler())
        return reg

    def test_list_filtered_none_returns_all(self):
        reg = self._reg_with_abc()
        pairs = reg.list_filtered(None)
        assert len(pairs) == 3
        assert all(binding is None for _, binding in pairs)

    def test_list_filtered_whitelist(self):
        reg = self._reg_with_abc()
        bindings = [ToolBinding(tool_name="a"), ToolBinding(tool_name="c")]
        pairs = reg.list_filtered(bindings)
        names = [spec.name for spec, _ in pairs]
        assert sorted(names) == ["a", "c"]

    def test_list_filtered_empty_bindings(self):
        reg = self._reg_with_abc()
        pairs = reg.list_filtered([])
        assert pairs == []

    def test_list_filtered_disabled_excluded(self):
        reg = self._reg_with_abc()
        bindings = [
            ToolBinding(tool_name="a"),
            ToolBinding(tool_name="b", invocation_mode="disabled"),
        ]
        pairs = reg.list_filtered(bindings)
        assert [s.name for s, _ in pairs] == ["a"]

    def test_list_filtered_is_enabled_false_excluded(self):
        reg = self._reg_with_abc()
        bindings = [ToolBinding(tool_name="a", is_enabled=False)]
        pairs = reg.list_filtered(bindings)
        assert pairs == []

    def test_list_filtered_unregistered_tool_skipped(self, caplog):
        reg = self._reg_with_abc()
        bindings = [ToolBinding(tool_name="z")]
        import logging
        with caplog.at_level(logging.WARNING, logger="agent_runtime.tools.filter"):
            pairs = reg.list_filtered(bindings)
        assert pairs == []
        assert "z" in caplog.text

    def test_manual_only_excluded_from_auto_only(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("auto_tool"), _EchoHandler())
        reg.register(_make_spec("manual_tool"), _EchoHandler())
        bindings = [
            ToolBinding(tool_name="auto_tool", invocation_mode="auto"),
            ToolBinding(tool_name="manual_tool", invocation_mode="manual_only"),
        ]
        all_pairs = reg.list_filtered(bindings)
        auto_pairs = ToolFilter.auto_only(all_pairs)
        assert [s.name for s, _ in auto_pairs] == ["auto_tool"]


# ---------------------------------------------------------------------------
# DynamicToolRegistry — build_tool_definitions
# ---------------------------------------------------------------------------


class TestBuildToolDefinitions:
    def test_definitions_use_spec_description(self):
        reg = DynamicToolRegistry()
        spec = _make_spec("my_tool")
        reg.register(spec, _EchoHandler())
        defs = reg.build_tool_definitions()
        assert len(defs) == 1
        assert defs[0].name == "my_tool"
        assert defs[0].description == spec.description

    def test_binding_description_overrides_spec(self):
        reg = DynamicToolRegistry()
        spec = _make_spec("t")
        reg.register(spec, _EchoHandler())
        bindings = [ToolBinding(tool_name="t", description="Overridden desc")]
        defs = reg.build_tool_definitions(bindings)
        assert defs[0].description == "Overridden desc"

    def test_manual_only_excluded_from_definitions(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("auto"), _EchoHandler())
        reg.register(_make_spec("manual"), _EchoHandler())
        bindings = [
            ToolBinding(tool_name="auto", invocation_mode="auto"),
            ToolBinding(tool_name="manual", invocation_mode="manual_only"),
        ]
        defs = reg.build_tool_definitions(bindings)
        assert [d.name for d in defs] == ["auto"]


# ---------------------------------------------------------------------------
# DynamicToolRegistry — build_pydantic_ai_tools
# ---------------------------------------------------------------------------


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("ok"), _EchoHandler())
        executor = ToolExecutor()
        result = await executor.execute(reg, "ok", {"value": "hello"}, _make_context())
        assert result.status == "success"
        assert result.output == "hello"
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        reg = DynamicToolRegistry()
        executor = ToolExecutor()
        result = await executor.execute(reg, "ghost", {}, _make_context())
        assert result.status == "error"
        assert "ghost" in result.error_message

    @pytest.mark.asyncio
    async def test_schema_validation_rejects_missing_required(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("t"), _EchoHandler())
        executor = ToolExecutor()
        result = await executor.execute(reg, "t", {}, _make_context())
        assert result.status == "error"
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_schema_validation_rejects_wrong_type(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("t"), _EchoHandler())
        executor = ToolExecutor()
        result = await executor.execute(reg, "t", {"value": 123}, _make_context())
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("bad"), _ErrorHandler())
        executor = ToolExecutor()
        result = await executor.execute(reg, "bad", {"value": "x"}, _make_context())
        assert result.status == "error"
        assert "intentional error" in result.error_message

    @pytest.mark.asyncio
    async def test_timeout_returns_timeout_status(self):
        reg = DynamicToolRegistry()
        spec = _make_spec("slow", timeout=0.05)
        reg.register(spec, _TimeoutHandler())
        executor = ToolExecutor()
        result = await executor.execute(reg, "slow", {"value": "x"}, _make_context())
        assert result.status == "timeout"
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_retry_idempotent_succeeds_on_second_attempt(self):
        reg = DynamicToolRegistry()
        handler = _RetryTrackingHandler(fail_count=1)
        spec = _make_spec("flaky", retries=2, idempotent=True)
        reg.register(spec, handler)
        executor = ToolExecutor()
        result = await executor.execute(reg, "flaky", {"value": "x"}, _make_context())
        assert result.status == "success"
        assert handler.calls == 2

    @pytest.mark.asyncio
    async def test_no_retry_for_non_idempotent(self):
        reg = DynamicToolRegistry()
        handler = _RetryTrackingHandler(fail_count=99)
        spec = _make_spec("non_idemp", retries=3, idempotent=False)
        reg.register(spec, handler)
        executor = ToolExecutor()
        result = await executor.execute(reg, "non_idemp", {"value": "x"}, _make_context())
        assert result.status == "error"
        assert handler.calls == 1  # no retries for non-idempotent

    @pytest.mark.asyncio
    async def test_duration_ms_populated(self):
        reg = DynamicToolRegistry()
        reg.register(_make_spec("timed"), _EchoHandler())
        executor = ToolExecutor()
        result = await executor.execute(reg, "timed", {"value": "y"}, _make_context())
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# ToolFilter
# ---------------------------------------------------------------------------


class TestToolFilter:
    def _specs(self) -> list[ToolSpec]:
        return [_make_spec(n) for n in ("x", "y", "z")]

    def test_none_bindings_returns_all_with_none_binding(self):
        specs = self._specs()
        pairs = ToolFilter.apply(specs, None)
        assert len(pairs) == 3
        assert all(b is None for _, b in pairs)

    def test_empty_bindings_returns_empty(self):
        pairs = ToolFilter.apply(self._specs(), [])
        assert pairs == []

    def test_whitelist_filters_correctly(self):
        specs = self._specs()
        bindings = [ToolBinding(tool_name="x"), ToolBinding(tool_name="z")]
        pairs = ToolFilter.apply(specs, bindings)
        assert [s.name for s, _ in pairs] == ["x", "z"]

    def test_disabled_invocation_mode_excluded(self):
        specs = self._specs()
        bindings = [ToolBinding(tool_name="x", invocation_mode="disabled")]
        pairs = ToolFilter.apply(specs, bindings)
        assert pairs == []

    def test_is_enabled_false_excluded(self):
        specs = self._specs()
        bindings = [ToolBinding(tool_name="x", is_enabled=False)]
        pairs = ToolFilter.apply(specs, bindings)
        assert pairs == []

    def test_manual_only_included_by_apply_excluded_by_auto_only(self):
        specs = self._specs()
        bindings = [
            ToolBinding(tool_name="x", invocation_mode="auto"),
            ToolBinding(tool_name="y", invocation_mode="manual_only"),
        ]
        all_pairs = ToolFilter.apply(specs, bindings)
        assert len(all_pairs) == 2
        auto_pairs = ToolFilter.auto_only(all_pairs)
        assert len(auto_pairs) == 1
        assert auto_pairs[0][0].name == "x"

    def test_auto_only_with_none_bindings_passes_all(self):
        specs = self._specs()
        pairs = ToolFilter.apply(specs, None)
        auto_pairs = ToolFilter.auto_only(pairs)
        assert len(auto_pairs) == 3


# ---------------------------------------------------------------------------
# SchemaValidator
# ---------------------------------------------------------------------------


class TestSchemaValidator:
    def _validator(self) -> SchemaValidator:
        return SchemaValidator()

    def _schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer", "minimum": 1},
            },
            "required": ["name"],
            "additionalProperties": False,
        }

    def test_valid_arguments_returns_none(self):
        v = self._validator()
        assert v.validate(self._schema(), {"name": "Alice", "count": 5}) is None

    def test_missing_required_returns_error(self):
        v = self._validator()
        error = v.validate(self._schema(), {"count": 3})
        assert error is not None

    def test_wrong_type_returns_error(self):
        v = self._validator()
        error = v.validate(self._schema(), {"name": 123})
        assert error is not None

    def test_additional_properties_returns_error(self):
        v = self._validator()
        error = v.validate(self._schema(), {"name": "Bob", "extra": True})
        assert error is not None

    def test_minimum_violation_returns_error(self):
        v = self._validator()
        error = v.validate(self._schema(), {"name": "Bob", "count": 0})
        assert error is not None

    def test_module_level_validate_arguments(self):
        schema = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
        assert validate_arguments(schema, {"x": "hello"}) is None
        assert validate_arguments(schema, {}) is not None


# ---------------------------------------------------------------------------
# KnowledgeSearchTool
# ---------------------------------------------------------------------------


class TestKnowledgeSearchTool:
    def _tool(self, provider=None) -> KnowledgeSearchTool:
        return KnowledgeSearchTool(knowledge_provider=provider, default_top_k=3)

    @pytest.mark.asyncio
    async def test_returns_chunks(self):
        class FakeProvider:
            def search(self, query, top_k=5):
                return [KnowledgeChunk(title="T", content="chunk")]

        tool = self._tool(FakeProvider())
        result = await tool.execute({"query": "hello"}, _make_context())
        assert result.status == "success"
        assert "chunk" in result.output

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self):
        tool = self._tool()
        result = await tool.execute({"query": ""}, _make_context())
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_no_provider_returns_message(self):
        tool = self._tool(provider=None)
        result = await tool.execute({"query": "anything"}, _make_context())
        assert result.status == "success"
        assert "not configured" in result.output

    @pytest.mark.asyncio
    async def test_provider_exception_captured(self):
        class FailProvider:
            def search(self, query, top_k=5):
                raise RuntimeError("db down")

        tool = self._tool(FailProvider())
        result = await tool.execute({"query": "q"}, _make_context())
        assert result.status == "error"
        assert "db down" in result.error_message

    @pytest.mark.asyncio
    async def test_async_provider_supported(self):
        class AsyncProvider:
            async def search(self, query, top_k=5):
                return [KnowledgeChunk(content="async chunk")]

        tool = self._tool(AsyncProvider())
        result = await tool.execute({"query": "q"}, _make_context())
        assert result.status == "success"
        assert "async chunk" in result.output

    @pytest.mark.asyncio
    async def test_uses_scoped_search_when_context_has_knowledge_bindings(self):
        provider = _ScopedKnowledgeProvider()
        binding = KnowledgeBindingSnapshot(
            knowledge_base_id="101",
            sort_order=10,
            config={"max_results": 2},
            config_version=3,
        )
        context = ToolExecutionContext(
            session_id="s1",
            trace_id="t1",
            agent_key="sales-assistant",
            agent_version=3,
            knowledge_bindings=(binding,),
        )

        result = await self._tool(provider).execute({"query": "refund", "top_k": 2}, context)

        assert result.status == "success"
        assert "Refunds are available" in result.output
        assert provider.global_calls == 0
        assert provider.scoped_calls == [((binding,), "refund", 2, "sales-assistant", 3)]
        assert result.structured_data is not None
        assert result.structured_data["knowledge_base_ids"] == ["101"]
        assert result.structured_data["binding_config_versions"] == [3]

    @pytest.mark.asyncio
    async def test_returns_empty_success_for_bound_agent_without_knowledge_bindings(self):
        provider = _ScopedKnowledgeProvider()
        context = ToolExecutionContext(
            session_id="s1",
            trace_id="t1",
            agent_key="sales-assistant",
            agent_version=3,
            knowledge_bindings=(),
        )

        result = await self._tool(provider).execute({"query": "refund"}, context)

        assert result.status == "success"
        assert result.structured_data == {
            "chunks": [],
            "knowledge_base_ids": [],
            "binding_config_versions": [],
        }
        assert provider.global_calls == 0
        assert provider.scoped_calls == []

    def test_spec_name(self):
        assert KnowledgeSearchTool.spec.name == "knowledge_search"

    def test_spec_has_required_query(self):
        assert "query" in KnowledgeSearchTool.spec.parameters_schema["required"]


# ---------------------------------------------------------------------------
# TimeNowTool
# ---------------------------------------------------------------------------


class TestTimeNowTool:
    @pytest.mark.asyncio
    async def test_returns_utc_timestamp(self):
        tool = TimeNowTool()
        result = await tool.execute({}, _make_context())
        assert result.status == "success"
        assert "T" in result.output  # ISO format
        assert result.structured_data is not None
        assert "utc" in result.structured_data

    @pytest.mark.asyncio
    async def test_with_timezone_offset(self):
        tool = TimeNowTool()
        result = await tool.execute({"timezone_offset_hours": 8}, _make_context())
        assert result.status == "success"
        assert "Local" in result.output or "UTC" in result.output

    def test_spec_name(self):
        assert TimeNowTool.spec.name == "time_now"


# ---------------------------------------------------------------------------
# CalculatorTool
# ---------------------------------------------------------------------------


class TestCalculatorTool:
    @pytest.mark.asyncio
    async def test_basic_arithmetic(self):
        tool = CalculatorTool()
        result = await tool.execute({"expression": "2 + 3"}, _make_context())
        assert result.status == "success"
        assert result.output == "5"

    @pytest.mark.asyncio
    async def test_float_result(self):
        tool = CalculatorTool()
        result = await tool.execute({"expression": "7 / 2"}, _make_context())
        assert result.status == "success"
        assert result.output == "3.5"

    @pytest.mark.asyncio
    async def test_parentheses(self):
        tool = CalculatorTool()
        result = await tool.execute({"expression": "(10 + 5) * 2"}, _make_context())
        assert result.output == "30"

    @pytest.mark.asyncio
    async def test_division_by_zero(self):
        tool = CalculatorTool()
        result = await tool.execute({"expression": "1 / 0"}, _make_context())
        assert result.status == "error"
        assert "zero" in result.error_message

    @pytest.mark.asyncio
    async def test_invalid_expression(self):
        tool = CalculatorTool()
        result = await tool.execute({"expression": "import os"}, _make_context())
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_empty_expression_returns_error(self):
        tool = CalculatorTool()
        result = await tool.execute({"expression": ""}, _make_context())
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_power_operator(self):
        tool = CalculatorTool()
        result = await tool.execute({"expression": "2 ** 8"}, _make_context())
        assert result.output == "256"

    @pytest.mark.asyncio
    async def test_structured_data_contains_result(self):
        tool = CalculatorTool()
        result = await tool.execute({"expression": "3 * 4"}, _make_context())
        assert result.structured_data is not None
        assert result.structured_data["result"] == 12.0

    def test_spec_name(self):
        assert CalculatorTool.spec.name == "calculator"


# ---------------------------------------------------------------------------
# ToolRegistry — backward compat
# ---------------------------------------------------------------------------


class TestBindingFromSnapshot:
    def test_basic_conversion(self):
        from agent_runtime.definition.models import ToolBindingSnapshot

        snap = ToolBindingSnapshot(
            tool_name="my_tool",
            description="A description",
            invocation_mode="auto",
        )
        binding = binding_from_snapshot(snap)
        assert binding.tool_name == "my_tool"
        assert binding.description == "A description"
        assert binding.invocation_mode == "auto"
        assert binding.is_enabled is True

    def test_invalid_invocation_mode_defaults_to_auto(self):
        snap = MagicMock()
        snap.tool_name = "t"
        snap.description = None
        snap.invocation_mode = "unknown_mode"
        snap.config = {}
        binding = binding_from_snapshot(snap)
        assert binding.invocation_mode == "auto"

    def test_manual_only_preserved(self):
        snap = MagicMock()
        snap.tool_name = "t"
        snap.description = None
        snap.invocation_mode = "manual_only"
        snap.config = {}
        binding = binding_from_snapshot(snap)
        assert binding.invocation_mode == "manual_only"


# ---------------------------------------------------------------------------
# Phase 2: definition-aware tool integration
# ---------------------------------------------------------------------------


class TestEngineResolveToolBindings:
    """AgentRuntime._resolve_tool_bindings maps definition snapshots to ToolBindings."""

    def test_none_definition_returns_none(self):
        from agent_runtime.runtime.engine import AgentRuntime
        result = AgentRuntime._resolve_tool_bindings(None)
        assert result is None

    def test_definition_with_tools_returns_full_list(self):
        from agent_runtime.runtime.engine import AgentRuntime
        from agent_runtime.definition.models import AgentDefinitionSnapshot, ToolBindingSnapshot

        snapshot = AgentDefinitionSnapshot(
            agent_key="k",
            version_number=1,
            display_name="D",
            system_prompt_template="",
            model_binding_key="",
            tools=(
                ToolBindingSnapshot(tool_name="tool_x", description="X desc", invocation_mode="auto"),
                ToolBindingSnapshot(tool_name="tool_y", invocation_mode="manual_only"),
                ToolBindingSnapshot(tool_name="tool_z", invocation_mode="disabled"),
            ),
        )
        bindings = AgentRuntime._resolve_tool_bindings(snapshot)
        assert bindings is not None
        assert len(bindings) == 3
        by_name = {b.tool_name: b for b in bindings}
        assert by_name["tool_x"].description == "X desc"
        assert by_name["tool_x"].invocation_mode == "auto"
        assert by_name["tool_y"].invocation_mode == "manual_only"
        assert by_name["tool_z"].invocation_mode == "disabled"

    def test_description_carried_through_binding_from_snapshot(self):
        from agent_runtime.runtime.engine import AgentRuntime
        from agent_runtime.definition.models import AgentDefinitionSnapshot, ToolBindingSnapshot

        snapshot = AgentDefinitionSnapshot(
            agent_key="k",
            version_number=1,
            display_name="D",
            system_prompt_template="",
            model_binding_key="",
            tools=(
                ToolBindingSnapshot(tool_name="custom_tool", description="LLM-facing desc"),
            ),
        )
        bindings = AgentRuntime._resolve_tool_bindings(snapshot)
        assert bindings[0].description == "LLM-facing desc"
