"""Turn post-processing — voice guardrails, handoff, output guards, result building.

Extracted from ``engine.py`` to isolate post-turn processing logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..contracts.models import (
    AgentAction,
    AgentDecision,
    AgentMessage,
    AgentRole,
    AgentTurnResult,
    AppliedSkillRecord,
    HandoffTarget,
)
from ..memory import SessionSnapshot

if TYPE_CHECKING:
    from ..config import AgentSettings
    from ..contracts.models import AgentTurnRequest
    from ..definition.models import AgentDefinitionSnapshot
    from ..guardrails import GuardsPipeline
    from ..guardrails.global_guard import GlobalGuardrailMatch, GlobalGuardrailService
    from ..orchestration import HandoffManager
    from .engine import AgentRunDeps
    from .message_builder import MessageBuilder


@dataclass(slots=True)
class TurnOutput:
    """Captures the result of LLM execution + all post-processing state."""

    result: AgentTurnResult
    session_snapshot_to_save: SessionSnapshot | None


class TurnPostProcessor:
    """Stateless helper for post-turn processing — methods extracted from ``AgentRuntime``."""

    def __init__(
        self,
        *,
        guards_pipeline: GuardsPipeline | None = None,
        global_guardrail_service: GlobalGuardrailService | None = None,
        handoff_manager: HandoffManager | None = None,
        settings: AgentSettings,
    ) -> None:
        self.guards_pipeline = guards_pipeline
        self._global_guardrail_service = global_guardrail_service
        self._handoff_manager = handoff_manager
        self.settings = settings

    async def post_process_turn(
        self,
        *,
        decision: AgentDecision,
        deps: AgentRunDeps,
        raw_messages: list[Any],
        resolved_request: AgentTurnRequest,
        definition: AgentDefinitionSnapshot | None,
        effective_settings: AgentSettings,
        restored_snapshot: SessionSnapshot | None,
        applied_skills: list[AppliedSkillRecord],
        input_global_alert_match: GlobalGuardrailMatch | None,
        original_request: AgentTurnRequest,
        usage: Any = None,
    ) -> TurnOutput | AgentTurnResult:
        """Post-process a completed LLM turn.

        Handles output guards, handoff, and result building.
        Returns either a ``TurnOutput`` or an ``AgentTurnResult`` directly
        (when an agent-to-agent handoff short-circuits).
        """
        from .message_builder import MessageBuilder

        is_voice_guardrail_turn = (
            resolved_request.channel == "voice"
            and definition is not None
            and definition.voice_guardrails is not None
        )

        # Legacy human handoff check
        handoff = await self._apply_handoff_policy(decision, deps, effective_settings)
        action = AgentAction.HANDOFF if handoff.get("should_handoff") else AgentAction.REPLY
        handoff_reason = handoff.get("reason")
        reply_text = (
            effective_settings.default_handoff_message
            if action != AgentAction.REPLY
            else decision.reply_text
        )

        # Output guards
        if self.guards_pipeline is not None and not is_voice_guardrail_turn:
            from ..guardrails import GuardVerdict

            output_result = await self.guards_pipeline.run_output_guards(
                message=reply_text,
                session_id=resolved_request.session_id,
                trace_id=resolved_request.trace_id or "",
                metadata=dict(resolved_request.metadata),
            )
            if output_result.final_verdict is GuardVerdict.BLOCK:
                reply_text = self.guards_pipeline.block_response
            elif output_result.modified_text is not None:
                reply_text = output_result.modified_text

        # Normalize messages
        normalized_messages = MessageBuilder.normalize_raw_messages(raw_messages)

        # Build result
        result = AgentTurnResult(
            session_id=resolved_request.session_id,
            trace_id=deps.trace_id,
            action=action,
            reply_text=reply_text,
            handoff_reason=handoff_reason,
            tool_events=list(deps.tool_events),
            usage=usage,
            raw_messages=normalized_messages,
            agent_key=original_request.agent_key,
            agent_version=definition.version_number if definition else None,
            applied_skills=applied_skills,
        )
        return TurnOutput(
            result=result,
            session_snapshot_to_save=restored_snapshot,
        )

    async def _apply_handoff_policy(
        self,
        decision: AgentDecision,
        deps: AgentRunDeps,
        settings: AgentSettings,
    ) -> dict[str, Any]:
        """Apply handoff policy — simplified version.

        TODO: Integrate with tool_registry.apply_handoff_policy when fully migrated.
        """
        if decision.should_handoff:
            return {"should_handoff": True, "reason": decision.handoff_reason}
        return {"should_handoff": False}


__all__ = ["TurnOutput", "TurnPostProcessor"]
