"""Tool registry — dynamic registration, filtering, and pydantic-ai integration.

Two classes are exposed:

:class:`DynamicToolRegistry`
    The core engine: stores ``(spec, handler)`` pairs by name, filters them
    by agent-definition bindings, and produces pydantic-ai ``Tool`` objects
    or raw ``ToolDefinition`` lists on demand.

:class:`ToolRegistry`
    Backward-compatible wrapper used by :class:`~agent_runtime.runtime.AgentRuntime`.
    Accepts the legacy ``knowledge_provider`` and ``handoff_policy`` constructor
    args, auto-registers the built-in ``knowledge_search`` tool, and delegates
    storage/filtering to an internal ``DynamicToolRegistry``.

Migration path
--------------
Existing code that constructs ``ToolRegistry(knowledge_provider=..., ...)`` continues
to work unchanged.  New code can construct a ``DynamicToolRegistry`` directly and
call ``register()`` to add any number of tools.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from ..config import AgentSettings
from ..contracts.models import (
    AgentSessionState,
    HandoffDecision,
    KnowledgeChunk,
    ToolExecutionRecord,
)
from .contracts import ToolBinding, ToolExecutionContext, ToolHandler, ToolResult, ToolSpec
from .executor import PreparedToolExecution, ToolExecutor
from .filter import ToolFilter

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Self-built ToolDefinition — replaces pydantic_ai.tools.ToolDefinition
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Lightweight tool schema descriptor — replaces ``pydantic_ai.tools.ToolDefinition``.

    Attributes match the original pydantic-ai type so callers don't need changes.
    """

    name: str
    description: str = ""
    parameters_json_schema: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Legacy provider / policy protocols (kept for backward compatibility)
# ---------------------------------------------------------------------------


class KnowledgeProvider(Protocol):
    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[KnowledgeChunk] | Awaitable[list[KnowledgeChunk]]:
        ...


class HandoffPolicy(Protocol):
    def evaluate(
        self,
        reason: str,
        context: AgentSessionState,
    ) -> HandoffDecision | Awaitable[HandoffDecision]:
        ...


class NullKnowledgeProvider:
    def search(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        return [
            KnowledgeChunk(
                title="Knowledge base unavailable",
                content="No knowledge provider is configured for this runtime.",
            )
        ]


class ConservativeHandoffPolicy:
    def evaluate(self, reason: str, context: AgentSessionState) -> HandoffDecision:
        normalized = reason.strip()
        if not normalized:
            return HandoffDecision()
        return HandoffDecision(should_handoff=True, reason=normalized)


async def _maybe_await(value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await value  # type: ignore[misc]
    return value  # type: ignore[return-value]


def _stringify_chunks(chunks: list[KnowledgeChunk]) -> str:
    if not chunks:
        return "No matching knowledge was found."
    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        title = chunk.title or f"Knowledge {index}"
        source = f" ({chunk.source})" if chunk.source else ""
        lines.append(f"[{index}] {title}{source}: {chunk.content}")
    return "\n".join(lines)


def _resolve_tool_source(spec: ToolSpec) -> tuple[str, str | None]:
    """Classify a tool spec into (source_type, source_ref).

    source_type is one of: "delegate", "mcp", "http_external", "builtin".
    source_ref is the MCP server name for mcp tools, otherwise None.
    """
    if spec.name == "delegate_to_agent":
        return "delegate", None
    if "mcp" in spec.tags:
        server_tag = next((tag for tag in spec.tags if tag.startswith("mcp:")), None)
        return "mcp", server_tag.split(":", 1)[1] if server_tag else None
    if "external" in spec.tags:
        return "http_external", None
    return "builtin", None


def _default_display_name(tool_name: str) -> str:
    return tool_name.replace("_", " ").title()


# ---------------------------------------------------------------------------
# DynamicToolRegistry — core storage, filtering, and build engine
# ---------------------------------------------------------------------------


class DynamicToolRegistry:
    """Runtime tool registry with dynamic registration and agent-binding support.

    All public methods are thread-safe for reads; ``register`` / ``unregister``
    should be called from a single initialisation path (e.g., application
    startup) before concurrent requests begin.

    Example::

        registry = DynamicToolRegistry()
        registry.register(MyTool.spec, MyTool())

        defs = registry.build_tool_definitions(
            bindings=None,   # all tools enabled
        )
    """

    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, ToolHandler]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        """Register a tool.

        Args:
            spec: Immutable metadata for the tool.
            handler: Object implementing :class:`~contracts.ToolHandler`.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if spec.name in self._tools:
            raise ValueError(
                f"Tool '{spec.name}' is already registered. "
                "Call unregister() first to replace it."
            )
        self._tools[spec.name] = (spec, handler)
        logger.debug("tool_registered name=%s", spec.name)

    def register_or_replace(self, spec: ToolSpec, handler: ToolHandler) -> None:
        """Register a tool, silently replacing any existing registration."""
        was_replaced = spec.name in self._tools
        self._tools[spec.name] = (spec, handler)
        if was_replaced:
            logger.debug("tool_replaced name=%s", spec.name)
        else:
            logger.debug("tool_registered name=%s", spec.name)

    def unregister(self, name: str) -> bool:
        """Remove a tool by name.

        Returns:
            ``True`` if the tool existed and was removed, ``False`` otherwise.
        """
        if name in self._tools:
            del self._tools[name]
            logger.debug("tool_unregistered name=%s", name)
            return True
        return False

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_spec(self, name: str) -> ToolSpec | None:
        """Return the :class:`ToolSpec` for *name*, or ``None``."""
        entry = self._tools.get(name)
        return entry[0] if entry else None

    def get_handler(self, name: str) -> ToolHandler | None:
        """Return the handler for *name*, or ``None``."""
        entry = self._tools.get(name)
        return entry[1] if entry else None

    def list_all(self) -> list[ToolSpec]:
        """Return all registered tool specs (unfiltered)."""
        return [spec for spec, _ in self._tools.values()]

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def list_filtered(
        self,
        bindings: list[ToolBinding] | None = None,
    ) -> list[tuple[ToolSpec, ToolBinding | None]]:
        """Return ``(spec, binding)`` pairs after applying *bindings*.

        When *bindings* is ``None``, all registered tools are returned with
        ``binding=None`` (backward-compat, no agent definition).
        """
        return ToolFilter.apply(self.list_all(), bindings)

    # ------------------------------------------------------------------
    # Build: ToolDefinition list (for gateway / streaming)
    # ------------------------------------------------------------------

    def build_tool_definitions(
        self,
        bindings: list[ToolBinding] | None = None,
    ) -> list[ToolDefinition]:
        """Build a ``ToolDefinition`` list for use by ``GatewayBackedModel``.

        The tool description is taken from ``ToolBinding.description`` when
        present, falling back to ``ToolSpec.description``.
        """
        pairs = ToolFilter.auto_only(self.list_filtered(bindings))
        result: list[ToolDefinition] = []
        for spec, binding in pairs:
            description = (
                (binding.description or spec.description)
                if binding is not None
                else spec.description
            )
            result.append(
                ToolDefinition(
                    name=spec.name,
                    description=description,
                    parameters_json_schema=spec.parameters_schema,
                    tags=sorted(spec.tags) if spec.tags else [],
                )
            )
        return result


# ---------------------------------------------------------------------------
# ToolRegistry — backward-compatible wrapper
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ToolRegistry:
    """Backward-compatible orchestrator that wraps :class:`DynamicToolRegistry`.

    Maintains the original constructor signature (``knowledge_provider``,
    ``handoff_policy``) and all public methods used by the engine, while
    delegating tool storage and filtering to ``DynamicToolRegistry``.

    New code should prefer constructing a ``DynamicToolRegistry`` directly
    and calling ``register()`` for each tool.
    """

    knowledge_provider: KnowledgeProvider = field(default_factory=NullKnowledgeProvider)
    handoff_policy: HandoffPolicy = field(default_factory=ConservativeHandoffPolicy)

    # Lazily initialised so slots=True still works with post_init
    _dynamic: DynamicToolRegistry = field(init=False)
    _executor: ToolExecutor = field(init=False)

    def __post_init__(self) -> None:
        from .builtin.knowledge_search import KnowledgeSearchTool

        self._dynamic = DynamicToolRegistry()
        self._executor = ToolExecutor()
        # Auto-register the knowledge_search built-in, wiring the provider
        self._dynamic.register(
            KnowledgeSearchTool.spec,
            KnowledgeSearchTool(self.knowledge_provider),
        )

    # ------------------------------------------------------------------
    # Public property for direct dynamic registry access
    # ------------------------------------------------------------------

    @property
    def dynamic_registry(self) -> DynamicToolRegistry:
        """Expose the underlying :class:`DynamicToolRegistry` for direct use."""
        return self._dynamic

    def build_execution_context(self, deps: Any) -> ToolExecutionContext:
        """Build the runtime context object injected into tool handlers."""
        return _build_execution_context_from_deps(deps)

    # ------------------------------------------------------------------
    # Registration proxy
    # ------------------------------------------------------------------

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        """Register an additional tool into the dynamic registry."""
        self._dynamic.register(spec, handler)

    def unregister(self, name: str) -> bool:
        """Remove a tool by name.  Returns ``True`` if it existed."""
        return self._dynamic.unregister(name)

    # ------------------------------------------------------------------
    # Legacy engine interface — kept unchanged for backward compat
    # ------------------------------------------------------------------

    def tool_definitions(
        self,
        settings: AgentSettings,
        *,
        allowed_tool_names: frozenset[str] | None = None,
        tool_bindings: list[ToolBinding] | None = None,
    ) -> list[ToolDefinition]:
        """Return ToolDefinition list, honouring legacy ``settings`` filters.

        When *tool_bindings* is provided (from an agent definition), it takes
        precedence over *allowed_tool_names* so that description overrides and
        invocation-mode rules from the definition are respected.
        """
        if tool_bindings is not None:
            return self._dynamic.build_tool_definitions(tool_bindings)
        bindings = self._settings_to_bindings(settings, allowed_tool_names)
        return self._dynamic.build_tool_definitions(bindings)

    def prepare_tool_execution(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        settings: AgentSettings,
        allowed_tool_names: frozenset[str] | None = None,
        tool_bindings: list[ToolBinding] | None = None,
    ) -> PreparedToolExecution | ToolResult:
        """Validate a tool invocation and resolve its execution policy."""
        if tool_bindings is not None:
            available = {spec.name for spec, _ in self._dynamic.list_filtered(tool_bindings)}
        else:
            bindings = self._settings_to_bindings(settings, allowed_tool_names)
            available = {spec.name for spec, _ in self._dynamic.list_filtered(bindings)}
        if tool_name not in available:
            return ToolResult(
                output="",
                status="error",
                error_message=f"Unknown or disabled tool '{tool_name}'.",
            )
        return self._executor.prepare_execution(self._dynamic, tool_name, arguments)

    def record_tool_result(
        self,
        *,
        deps: Any,
        tool_name: str,
        arguments: dict[str, Any],
        result: ToolResult,
    ) -> None:
        """Persist tool audit data and sub-agent usage onto runtime deps."""
        if hasattr(deps, "tool_events") and deps.tool_events is not None:
            from ..contracts.models import ToolExecutionRecord
            spec = self._dynamic.get_spec(tool_name)
            source_type, source_ref = _resolve_tool_source(spec) if spec is not None else ("builtin", None)
            deps.tool_events.append(
                ToolExecutionRecord(
                    tool_name=tool_name,
                    status=result.status,
                    arguments=arguments,
                    output_text=result.output if result.status == "success" else None,
                    structured_data=result.structured_data,
                    error_message=result.error_message,
                    display_name=_default_display_name(tool_name),
                    source_type=source_type,  # type: ignore[arg-type]
                    source_ref=source_ref,
                    tags=sorted(spec.tags) if spec is not None else [],
                    duration_ms=result.duration_ms,
                )
            )

        if (
            result.delegation_usage is not None
            and hasattr(deps, "delegation_usage_list")
            and deps.delegation_usage_list is not None
        ):
            deps.delegation_usage_list.append(result.delegation_usage)

    @staticmethod
    def unwrap_tool_result(tool_name: str, result: ToolResult) -> str:
        return _unwrap_tool_result(tool_name, result)

    async def invoke_tool_result(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        settings: AgentSettings,
        deps: Any,
        allowed_tool_names: frozenset[str] | None = None,
        tool_bindings: list[ToolBinding] | None = None,
    ) -> ToolResult:
        """Execute a tool and return the structured :class:`ToolResult`."""
        prepared = self.prepare_tool_execution(
            tool_name=tool_name,
            arguments=arguments,
            settings=settings,
            allowed_tool_names=allowed_tool_names,
            tool_bindings=tool_bindings,
        )
        if isinstance(prepared, ToolResult):
            self.record_tool_result(
                deps=deps,
                tool_name=tool_name,
                arguments=arguments,
                result=prepared,
            )
            return prepared

        result = await self._executor.execute(
            self._dynamic,
            tool_name,
            arguments,
            self.build_execution_context(deps),
        )
        self.record_tool_result(
            deps=deps,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
        )
        return result

    async def invoke_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        settings: AgentSettings,
        deps: Any,
        allowed_tool_names: frozenset[str] | None = None,
        tool_bindings: list[ToolBinding] | None = None,
    ) -> str:
        """Execute a tool by name, applying legacy ``settings`` guards.

        Uses :class:`ToolExecutor` internally for timeout and error isolation.

        When *tool_bindings* is provided (from an agent definition), availability
        is checked against those bindings instead of *allowed_tool_names*.
        """
        result = await self.invoke_tool_result(
            tool_name=tool_name,
            arguments=arguments,
            settings=settings,
            deps=deps,
            allowed_tool_names=allowed_tool_names,
            tool_bindings=tool_bindings,
        )
        return self.unwrap_tool_result(tool_name, result)

    async def search_knowledge(
        self,
        *,
        query: str,
        top_k: int,
        tool_events: list[ToolExecutionRecord] | None = None,
    ) -> list[KnowledgeChunk]:
        """Direct knowledge search (legacy path used by some tests)."""
        raw = self.knowledge_provider.search(query, top_k)
        if inspect.isawaitable(raw):
            chunks: list[KnowledgeChunk] = await raw
        else:
            chunks = raw

        if tool_events is not None:
            spec = self._dynamic.get_spec("knowledge_search")
            source_type, source_ref = _resolve_tool_source(spec) if spec is not None else ("builtin", None)
            tool_events.append(
                ToolExecutionRecord(
                    tool_name="knowledge_search",
                    status="success",
                    arguments={"query": query, "top_k": top_k},
                    output_text=_stringify_chunks(chunks),
                    display_name=_default_display_name("knowledge_search"),
                    source_type=source_type,  # type: ignore[arg-type]
                    source_ref=source_ref,
                    tags=sorted(spec.tags) if spec is not None else [],
                )
            )
        return chunks

    async def apply_handoff_policy(
        self,
        reason: str | None,
        *,
        session_state: AgentSessionState,
        enabled: bool,
    ) -> HandoffDecision:
        if not enabled or not reason:
            return HandoffDecision()
        return await _maybe_await(self.handoff_policy.evaluate(reason, session_state))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _settings_to_bindings(
        self,
        settings: AgentSettings,
        allowed_tool_names: frozenset[str] | None,
    ) -> list[ToolBinding] | None:
        """Convert legacy ``settings`` + ``allowed_tool_names`` into bindings.

        Returns ``None`` (all tools) when ``allowed_tool_names`` is ``None``
        and settings does not restrict knowledge_search.
        When settings disables knowledge_search, we construct an explicit
        binding list that excludes it.
        """
        all_specs = self._dynamic.list_all()

        # If both knobs are unrestricted, skip filtering entirely (fast path)
        if allowed_tool_names is None and settings.enable_knowledge_tool:
            return None

        # Build an explicit allowlist
        result: list[ToolBinding] = []
        for spec in all_specs:
            if spec.name == "knowledge_search" and not settings.enable_knowledge_tool:
                continue
            if allowed_tool_names is not None and spec.name not in allowed_tool_names:
                continue
            result.append(ToolBinding(tool_name=spec.name))
        return result


def _build_execution_context_from_deps(deps: Any) -> ToolExecutionContext:  # noqa: ANN401
    """Best-effort extraction of tool execution context from runtime deps."""
    request = getattr(deps, "request", None)
    session_state = getattr(deps, "session_state", None)
    definition = getattr(deps, "definition", None)

    metadata_source = (
        getattr(request, "metadata", None)
        or getattr(deps, "metadata", None)
        or getattr(session_state, "metadata", None)
        or {}
    )
    metadata = dict(metadata_source) if isinstance(metadata_source, dict) else {}

    return ToolExecutionContext(
        session_id=(
            getattr(request, "session_id", None)
            or getattr(deps, "session_id", None)
            or getattr(session_state, "session_id", None)
            or ""
        ),
        trace_id=(
            getattr(deps, "trace_id", None)
            or getattr(request, "trace_id", None)
            or ""
        ),
        agent_key=(
            getattr(request, "agent_key", None)
            or getattr(deps, "agent_key", None)
            or getattr(definition, "agent_key", None)
        ),
        agent_version=(
            getattr(request, "agent_version", None)
            or getattr(deps, "agent_version", None)
            or getattr(definition, "version_number", None)
        ),
        knowledge_bindings=(
            getattr(deps, "knowledge_bindings", None)
            if getattr(deps, "knowledge_bindings", None) is not None
            else getattr(definition, "knowledge_bindings", None)
        ),
        customer_id=(
            getattr(request, "customer_id", None)
            or getattr(deps, "customer_id", None)
            or getattr(session_state, "customer_id", None)
        ),
        locale=(
            getattr(request, "locale", None)
            or getattr(deps, "locale", None)
            or getattr(session_state, "locale", None)
        ),
        metadata=metadata,
    )


def _unwrap_tool_result(tool_name: str, result: ToolResult) -> str:
    """Convert an executor result into the legacy string-or-exception contract."""
    if result.status == "success":
        return result.output
    if result.status == "timeout":
        raise TimeoutError(result.error_message or f"Tool '{tool_name}' timed out.")
    raise ValueError(result.error_message or f"Tool '{tool_name}' failed.")
