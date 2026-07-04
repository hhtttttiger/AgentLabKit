"""Typed agent lifecycle events — inspired by pi agent-core AgentEvent.

All state changes in the agent runtime flow through these typed event objects.
Consumers subscribe via :class:`EventBus` and receive the appropriate event
subclass for each lifecycle transition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union


# ── Agent lifecycle ──────────────────────────────────────────────────────────


@dataclass
class AgentStartEvent:
    """Emitted when an agent run begins (before the first turn)."""

    type: str = "agent_start"


@dataclass
class AgentEndEvent:
    """Emitted when an agent run finishes (after all turns).

    ``messages`` contains all messages produced during this run.
    """

    type: str = "agent_end"
    messages: list[Any] = field(default_factory=list)


# ── Turn lifecycle ───────────────────────────────────────────────────────────
# A *turn* is one assistant response plus any tool calls/results it triggers.


@dataclass
class TurnStartEvent:
    """Emitted at the beginning of each turn."""

    type: str = "turn_start"


@dataclass
class TurnEndEvent:
    """Emitted when a turn completes (after tool results are resolved)."""

    type: str = "turn_end"
    message: Any = None
    tool_results: list[Any] = field(default_factory=list)


# ── Message lifecycle ────────────────────────────────────────────────────────


@dataclass
class MessageStartEvent:
    """Emitted when a new message (user, assistant, or tool-result) begins."""

    type: str = "message_start"
    message: Any = None


@dataclass
class MessageUpdateEvent:
    """Emitted during streaming when an assistant message receives new content.

    ``delta`` contains the incremental text since the last update.
    """

    type: str = "message_update"
    message: Any = None
    delta: str = ""


@dataclass
class MessageEndEvent:
    """Emitted when a message is finalized.

    ``usage`` is optionally set when token usage data is available (e.g.
    from the LLM gateway response), allowing SpanBuilder to record it.
    """

    type: str = "message_end"
    message: Any = None
    usage: Any = None


# ── Tool execution lifecycle ─────────────────────────────────────────────────


@dataclass
class ToolExecutionStartEvent:
    """Emitted just before a tool begins executing."""

    type: str = "tool_execution_start"
    tool_call_id: str = ""
    tool_name: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    source_type: str | None = None  # "mcp", "builtin", "http_external", "delegate"
    source_ref: str | None = None   # MCP server name (for mcp tools)


@dataclass
class ToolExecutionUpdateEvent:
    """Emitted when a tool streams a partial result via ``on_update``."""

    type: str = "tool_execution_update"
    tool_call_id: str = ""
    tool_name: str = ""
    partial_result: Any = None


@dataclass
class ToolExecutionEndEvent:
    """Emitted after a tool finishes executing (success or error)."""

    type: str = "tool_execution_end"
    tool_call_id: str = ""
    tool_name: str = ""
    result: Any = None
    is_error: bool = False


# ── Union type ───────────────────────────────────────────────────────────────

AgentEvent = Union[
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
]
"""All possible events emitted by the agent runtime."""

__all__ = [
    "AgentEndEvent",
    "AgentEvent",
    "AgentStartEvent",
    "MessageEndEvent",
    "MessageStartEvent",
    "MessageUpdateEvent",
    "ToolExecutionEndEvent",
    "ToolExecutionStartEvent",
    "ToolExecutionUpdateEvent",
    "TurnEndEvent",
    "TurnStartEvent",
]
