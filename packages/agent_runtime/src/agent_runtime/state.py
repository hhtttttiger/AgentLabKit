"""Agent state management — inspired by pi agent-core AgentState.

Provides a copy-on-write state container so that the public view of agent
state remains immutable between mutations. This enables time-travel debugging
and event sourcing patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts.models import AgentMessage
from .tools.contracts import ToolSpec


@dataclass
class AgentState:
    """Immutable-by-convention snapshot of agent state.

    Assigning to ``messages`` or ``tools`` copies the incoming list so that
    callers cannot mutate internal state through the reference they passed.

    Runtime-only fields (``is_streaming``, ``streaming_message``, etc.) are
    read-only indicators of the current run status.
    """

    system_prompt: str = ""
    model: str = ""

    # ── Copy-on-write collections ─────────────────────────────────────────

    _messages: list[AgentMessage] = field(default_factory=list)
    _tools: list[ToolSpec] = field(default_factory=list)

    # ── Runtime state (read-only) ─────────────────────────────────────────

    is_streaming: bool = False
    streaming_message: AgentMessage | None = None
    pending_tool_calls: frozenset[str] = frozenset()
    error_message: str | None = None

    # ── Messages accessors (copy-on-write) ────────────────────────────────

    @property
    def messages(self) -> list[AgentMessage]:
        """Return a *copy* of the internal message list."""
        return list(self._messages)

    @messages.setter
    def messages(self, value: list[AgentMessage]) -> None:
        self._messages = list(value)

    def append_message(self, message: AgentMessage) -> None:
        """Append a single message to the internal list (no copy)."""
        self._messages.append(message)

    # ── Tools accessors (copy-on-write) ───────────────────────────────────

    @property
    def tools(self) -> list[ToolSpec]:
        """Return a *copy* of the internal tool list."""
        return list(self._tools)

    @tools.setter
    def tools(self, value: list[ToolSpec]) -> None:
        self._tools = list(value)

    # ── Snapshot helpers ──────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """Return a plain dict snapshot of the current state."""
        return {
            "system_prompt": self.system_prompt,
            "model": self.model,
            "messages": self.messages,
            "tools": self.tools,
            "is_streaming": self.is_streaming,
            "pending_tool_calls": set(self.pending_tool_calls),
            "error_message": self.error_message,
        }


__all__ = ["AgentState"]
