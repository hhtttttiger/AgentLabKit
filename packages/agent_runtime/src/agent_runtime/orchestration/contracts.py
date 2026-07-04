"""Orchestration contracts — shared data types for multi-agent coordination.

All types in this module are pure data (no logic, no external dependencies).
Import from anywhere in the orchestration package without risk of cycles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal, Protocol, runtime_checkable

from ..contracts.models import AgentAction, AgentMessage, AgentTurnRequest, AgentTurnResult, AgentTurnStreamEvent, ToolExecutionRecord
from llm_gateway import UsageInfo


# ---------------------------------------------------------------------------
# SubTurnRunner — decouples orchestration from concrete AgentRuntime
# ---------------------------------------------------------------------------


@runtime_checkable
class SubTurnRunner(Protocol):
    """Protocol implemented by AgentRuntime (and any test double).

    Using a Protocol instead of a direct import prevents circular references
    between the ``orchestration`` and ``runtime`` packages.
    """

    async def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
        """Execute a single agent turn and return the result."""
        ...


@runtime_checkable
class SubStreamRunner(Protocol):
    """Optional streaming variant of SubTurnRunner.

    Implemented by AgentRuntime alongside SubTurnRunner.  Pass to
    :class:`~sub_agent_executor.SubAgentExecutor` to enable
    :meth:`~sub_agent_executor.SubAgentExecutor.stream_sub_turn`.
    """

    def stream_turn(self, request: AgentTurnRequest) -> AsyncIterator[AgentTurnStreamEvent]:
        """Stream a single agent turn, yielding events as they arrive."""
        ...


# ---------------------------------------------------------------------------
# SubAgentContext — metadata passed from parent to sub-agent
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SubAgentContext:
    """Execution context propagated from a parent agent to a sub-agent.

    Tracks identity, depth, and the call chain for safety guards.
    """

    parent_agent_key: str
    parent_session_id: str
    parent_trace_id: str
    depth: int = 0                              # Current nesting level (0 = top)
    summary: str | None = None                  # Optional context summary for the sub-agent
    shared_metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# DelegationResult — outcome of a sub-agent execution
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DelegationResult:
    """Result returned by SubAgentExecutor after a sub-agent turn."""

    agent_key: str
    reply_text: str
    action: AgentAction
    tool_events: list[ToolExecutionRecord] = field(default_factory=list)
    usage: UsageInfo | None = None
    handoff_target: Any | None = None           # HandoffTarget if sub-agent triggered a handoff
    error_message: str | None = None


# ---------------------------------------------------------------------------
# HandoffTarget (orchestration) — structured destination for handoff
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HandoffRouteTarget:
    """Resolved handoff target produced by AgentRouter.

    NOTE: Fields are identical to ``contracts.models.HandoffTarget``.
    These two types exist separately to avoid import cycles between
    ``orchestration`` and ``contracts``.  A future refactor should merge
    them by extracting shared field definitions into a protocol or
    moving ``HandoffTarget`` into a lower-level module.
    """

    target_type: Literal["human", "agent"]
    target_agent_key: str | None = None
    reason: str | None = None
    context_message: str | None = None


# ---------------------------------------------------------------------------
# HandoffResolution — output of HandoffManager.resolve_handoff()
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class HandoffResolution:
    """Fully resolved handoff decision ready for execution."""

    action: AgentAction                         # HANDOFF_HUMAN or HANDOFF_AGENT
    target_agent_key: str | None = None
    context_for_target: str | None = None
    reason: str | None = None


# ---------------------------------------------------------------------------
# AgentHandoffContext — context package sent to the target agent
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AgentHandoffContext:
    """Structured context bundle passed to a target agent during handoff."""

    summary: str | None
    key_facts: list[str]
    source_agent_key: str
    handoff_reason: str | None
    original_customer_id: str | None
    original_locale: str | None
    turn_count: int


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ORCHESTRATION_DEPTH: int = 3
_CHAIN_METADATA_KEY = "_orchestration_chain"
_DEPTH_METADATA_KEY = "_orchestration_depth"
