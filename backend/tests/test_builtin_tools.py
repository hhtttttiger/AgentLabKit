"""Tests for builtin tool registration.

Pure unit tests — no DB, no LLM. Confirms ``register_builtin_tools`` makes the
bundled ``time_now`` / ``calculator`` built-ins resolvable through the same
binding-based path the engine uses, without dropping the auto-registered
``knowledge_search``.
"""

from __future__ import annotations

from agent_runtime.config.agent import AgentSettings
from agent_runtime.tools.contracts import ToolBinding
from agent_runtime.tools.registry import ToolRegistry

from modules.agent.builtin_tools import register_builtin_tools


def _names(registry: ToolRegistry, bindings: list[ToolBinding] | None) -> set[str]:
    defs = registry.tool_definitions(AgentSettings(), tool_bindings=bindings)
    return {d.name for d in defs}


def test_register_builtin_tools_adds_time_now_and_calculator():
    registry = ToolRegistry()
    register_builtin_tools(registry)

    # With no bindings, every registered tool is visible (backward-compat path).
    assert _names(registry, None) == {"knowledge_search", "time_now", "calculator"}


def test_time_now_binding_resolves_to_tool_definition():
    registry = ToolRegistry()
    register_builtin_tools(registry)

    # The exact resolution an agent binding `time_now` (invocation_mode="auto")
    # goes through: ToolFilter keeps only bound + auto tools.
    names = _names(registry, [ToolBinding(tool_name="time_now", invocation_mode="auto")])
    assert names == {"time_now"}
    # calculator must NOT leak in just because it is registered — bindings gate it.
    assert "calculator" not in names


def test_knowledge_search_remains_registered():
    # Auto-registration in __post_init__ must survive registering the others.
    registry = ToolRegistry()
    register_builtin_tools(registry)
    assert "knowledge_search" in _names(registry, None)
