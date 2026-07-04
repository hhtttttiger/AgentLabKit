"""TurnContext — mutable state threaded through every pipeline phase.

A single ``TurnContext`` instance is created at the start of each turn
(by ``run_turn`` or ``stream_turn``) and passed through every
:class:`TurnPhase` in the pipeline.  Phases read and write fields to
coordinate their work without coupling to each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from ..contracts.models import (
    AgentAction,
    AgentDecision,
    AgentMessage,
    AgentTurnRequest,
    AgentTurnResult,
    AgentTurnStreamEvent,
    AppliedSkillRecord,
    HandoffTarget,
    ToolExecutionRecord,
)
from ..definition.models import AgentDefinitionSnapshot
from ..config import AgentSettings
from ..memory import SessionSnapshot
from ..tools import ToolBinding
from ..guardrails.global_guard import GlobalGuardrailMatch
from llm_gateway import UsageInfo


@dataclass
class TurnContext:
    """Mutable turn state shared across all phases in the pipeline.

    Immutable inputs (set once at construction):
        original_request, resolved_request, definition, effective_settings,
        tool_bindings, auto_tool_names, applied_skills, restored_snapshot,
        trace_id, mode.

    Mutable state (phases read and write):
        reply_text, action, handoff_reason, handoff_target, raw_messages,
        tool_events, usage, decision, should_stop, etc.

    Early-exit:
        Set ``should_stop = True`` to signal the pipeline driver to stop
        processing further phases.  Optionally set
        ``short_circuit_result`` or ``short_circuit_stream_event`` to
        provide the final output directly.
    """

    # ── Immutable inputs (set once in _prepare_context) ──────────────
    original_request: AgentTurnRequest
    resolved_request: AgentTurnRequest
    definition: AgentDefinitionSnapshot | None
    effective_settings: AgentSettings
    tool_bindings: list[ToolBinding] | None
    auto_tool_names: frozenset[str] | None
    applied_skills: list[AppliedSkillRecord]
    restored_snapshot: SessionSnapshot | None
    trace_id: str
    mode: Literal["blocking", "streaming"]

    # ── Mutable state (phases read and write) ───────────────────────
    reply_text: str = ""
    action: AgentAction = AgentAction.REPLY
    handoff_reason: str | None = None
    handoff_target: HandoffTarget | None = None
    raw_messages: list[AgentMessage] = field(default_factory=list)
    tool_events: list[ToolExecutionRecord] = field(default_factory=list)
    usage: UsageInfo | None = None
    decision: AgentDecision | None = None

    # ── Early-exit signal ──────────────────────────────────────────
    should_stop: bool = False
    short_circuit_result: AgentTurnResult | None = None
    short_circuit_stream_event: AgentTurnStreamEvent | None = None

    # ── Global guardrails state ────────────────────────────────────
    input_global_alert_match: GlobalGuardrailMatch | None = None

    # ── Voice-specific mutable state ───────────────────────────────
    voice_reply_text: str | None = None
    voice_handoff_reason: str | None = None
    is_voice_guardrail_turn: bool = False

    # ── Streaming accumulator ──────────────────────────────────────
    pending_reply_deltas: list[str] = field(default_factory=list)
    stream_usage: UsageInfo | None = None

    # ── Convenience properties ─────────────────────────────────────
    @property
    def is_streaming(self) -> bool:
        return self.mode == "streaming"

    @property
    def session_id(self) -> str:
        return self.resolved_request.session_id
