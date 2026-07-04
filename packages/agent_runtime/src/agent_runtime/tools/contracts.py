"""Contracts for the dynamic tool system.

Defines the core data structures shared across registry, executor, filter,
and built-in tool implementations. Nothing here imports from sibling modules;
it is safe to import from anywhere in the tools package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from llm_gateway import UsageInfo
    from agent_runtime.definition.models import KnowledgeBindingSnapshot


# ---------------------------------------------------------------------------
# ToolExecutionMode — parallel vs sequential tool calls
# ---------------------------------------------------------------------------


class ToolExecutionMode(str, Enum):
    """Controls how tool calls from a single assistant message are executed.

    Inspired by pi agent-core ``ToolExecutionMode``.
    """

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


# ---------------------------------------------------------------------------
# ToolSpec — immutable metadata for a single tool
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Complete metadata for a registered tool.

    The spec is the single source of truth for everything the system needs to
    know about a tool: its identity, LLM-facing description, JSON Schema for
    parameters, and execution policy (timeout, retries, idempotency).
    """

    name: str
    """Unique tool identifier, e.g. ``"knowledge_search"``."""

    description: str
    """Human- and LLM-readable description used in the function-calling schema."""

    parameters_schema: dict[str, Any]
    """JSON Schema object describing accepted parameters (``"type": "object"``)."""

    returns_description: str = ""
    """Optional description of the return value for documentation purposes."""

    tags: frozenset[str] = frozenset()
    """Classification tags, e.g. ``frozenset({"rag", "read_only"})``."""

    timeout_seconds: float = 30.0
    """Maximum wall-clock seconds allowed for a single execution attempt."""

    max_retries: int = 0
    """Number of additional attempts after the first failure (0 = no retry)."""

    is_idempotent: bool = True
    """When ``False``, retries are suppressed even if ``max_retries > 0``."""

    execution_mode: ToolExecutionMode = ToolExecutionMode.PARALLEL
    """Per-tool execution mode override — inspired by pi ``AgentTool.executionMode``."""

    label: str | None = None
    """Human-readable label for UI display — inspired by pi ``AgentTool.label``."""


# ---------------------------------------------------------------------------
# ToolExecutionContext — runtime context injected into every tool call
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ToolExecutionContext:
    """Runtime context available to every tool handler during execution.

    Mirrors the fields that the agent engine already tracks so tools can
    emit structured audit events, enforce per-customer policies, etc.
    """

    session_id: str
    trace_id: str
    agent_key: str | None = None
    agent_version: int | None = None
    knowledge_bindings: tuple[KnowledgeBindingSnapshot, ...] | None = None
    customer_id: str | None = None
    locale: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ToolResult — structured output from a tool handler
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ToolResult:
    """Outcome of a single tool execution attempt."""

    output: str
    """Text representation returned to the LLM.  Always a string."""

    structured_data: dict[str, Any] | None = None
    """Optional machine-readable payload for downstream consumers."""

    status: Literal["success", "error", "timeout"] = "success"
    """Execution outcome category."""

    error_message: str | None = None
    """Human-readable error detail, populated when ``status != "success"``."""

    duration_ms: int = 0
    """Wall-clock execution time in milliseconds, set by the executor."""

    delegation_usage: UsageInfo | None = None
    """LLM token usage from a sub-agent delegation, if this result came from
    :class:`~agent_runtime.orchestration.delegate_tool.DelegateToAgentTool`.
    The engine accumulates this into the parent turn's total usage.
    """

    terminate: bool = False
    """Hint that the agent should stop after this tool batch.

    Inspired by pi ``AgentToolResult.terminate``.  Early termination only
    happens when **every** tool result in the batch sets this to ``True``.
    """


# ---------------------------------------------------------------------------
# ToolHandler — the protocol every tool implementation must satisfy
# ---------------------------------------------------------------------------


@runtime_checkable
class ToolHandler(Protocol):
    """Interface that every tool implementation must satisfy.

    The ``on_update`` callback is optional and allows tools to stream partial
    results during long-running execution — inspired by pi
    ``AgentTool.onUpdate``.
    """

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        on_update: Callable[[ToolResult], None] | None = None,
    ) -> ToolResult:
        """Execute the tool and return a :class:`ToolResult`.

        Args:
            arguments: Validated parameter dict (keys match the tool's schema).
            context: Runtime context for the current agent turn.
            on_update: Optional callback for streaming partial results during
                long-running execution.  Ignored by tools that don't support it.

        Returns:
            A :class:`ToolResult` — never raises; errors are captured as
            ``status="error"`` results.
        """
        ...


# ---------------------------------------------------------------------------
# ToolBinding — runtime binding applied by agent definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolBinding:
    """Per-agent binding that controls how a registered tool is exposed.

    Derived from the ``agent_tool_bindings`` table managed by the .NET
    management plane.  Phase 2 will load these from DB via the definition
    loader; in Phase 1 they can be constructed manually or via
    :func:`binding_from_snapshot`.
    """

    tool_name: str
    """Must match a :attr:`ToolSpec.name` already registered in the registry."""

    display_name: str | None = None
    """Optional override for the tool name shown to users (not sent to LLM)."""

    description: str | None = None
    """When set, overrides :attr:`ToolSpec.description` in the function-calling schema."""

    invocation_mode: Literal["auto", "manual_only", "disabled"] = "auto"
    """Controls how the tool appears in LLM context:
    - ``"auto"``        — included in function-calling schema.
    - ``"manual_only"`` — registered but not injected into LLM schema.
    - ``"disabled"``    — neither registered nor injected.
    """

    is_enabled: bool = True
    """Master switch; if ``False``, overrides *invocation_mode*."""

    config: dict[str, Any] = field(default_factory=dict)
    """Arbitrary tool-specific runtime configuration (e.g. max_results)."""


def binding_from_snapshot(snapshot: Any) -> ToolBinding:  # noqa: ANN401
    """Convert a :class:`~agent_runtime.definition.models.ToolBindingSnapshot`
    into a :class:`ToolBinding`.

    This bridge function keeps the tools package decoupled from the definition
    package — the definition package can evolve independently.
    """
    mode = getattr(snapshot, "invocation_mode", "auto")
    if mode not in ("auto", "manual_only", "disabled"):
        mode = "auto"
    return ToolBinding(
        tool_name=snapshot.tool_name,
        description=getattr(snapshot, "description", None),
        invocation_mode=mode,  # type: ignore[arg-type]
        is_enabled=True,
        config=dict(getattr(snapshot, "config", {})),
    )
