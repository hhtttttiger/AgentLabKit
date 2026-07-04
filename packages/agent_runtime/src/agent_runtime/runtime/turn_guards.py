"""Turn guardrails execution — input/output guards, global guardrails, voice evaluation.

Extracted from ``engine.py`` to isolate all guardrail evaluation logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from ..config import AgentSettings
from ..contracts.models import (
    AgentAction,
    AgentTurnRequest,
    AgentTurnResult,
    AgentTurnStreamEvent,
    AppliedSkillRecord,
)
from ..definition.models import AgentDefinitionSnapshot
from ..errors import AgentError, AgentErrorCode
from ..guardrails import GuardVerdict, GuardsPipeline

if TYPE_CHECKING:
    from ..guardrails.global_guard import GlobalGuardrailMatch, GlobalGuardrailService
    from ..channels.voice import VoiceGuardrailEvaluator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class InputGuardResult:
    """Result of the input guard phase.

    If ``blocked_result`` is set, the caller should return/yield it immediately.
    If ``stream_blocked_event`` is set, the streaming caller should yield it and return.
    Otherwise, proceed with the modified ``resolved_request``.
    """

    resolved_request: AgentTurnRequest
    input_global_alert_match: GlobalGuardrailMatch | None = None
    blocked_result: AgentTurnResult | None = None
    stream_blocked_event: AgentTurnStreamEvent | None = None


class TurnGuards:
    """Stateless helper for guardrail evaluation — methods extracted from ``AgentRuntime``."""

    def __init__(
        self,
        *,
        guards_pipeline: GuardsPipeline | None = None,
        global_guardrail_service: GlobalGuardrailService | None = None,
        voice_evaluator: VoiceGuardrailEvaluator | None = None,
        settings: AgentSettings,
    ) -> None:
        self.guards_pipeline = guards_pipeline
        self._global_guardrail_service = global_guardrail_service
        self._voice_evaluator = voice_evaluator
        self.settings = settings

    async def run_input_guards(
        self,
        prepared: AgentTurnRequest,
        definition: AgentDefinitionSnapshot | None,
        applied_skills: list[AppliedSkillRecord],
        *,
        mode: Literal["blocking", "streaming"],
    ) -> InputGuardResult:
        """Run input guards + global input guards."""
        resolved_request = prepared
        input_global_alert_match: GlobalGuardrailMatch | None = None

        # Standard input guards
        if self.guards_pipeline is not None:
            input_result = await self.guards_pipeline.run_input_guards(
                message=resolved_request.user_message,
                session_id=resolved_request.session_id,
                trace_id=resolved_request.trace_id or "",
                metadata=dict(resolved_request.metadata),
            )
            if input_result.final_verdict is GuardVerdict.BLOCK:
                block_text = self.guards_pipeline.block_response
                if mode == "blocking":
                    return InputGuardResult(
                        resolved_request=resolved_request,
                        blocked_result=AgentTurnResult(
                            session_id=resolved_request.session_id,
                            trace_id=resolved_request.trace_id or "",
                            action=AgentAction.REPLY,
                            reply_text=block_text,
                            agent_key=resolved_request.agent_key,
                            agent_version=definition.version_number if definition else None,
                            applied_skills=list(applied_skills),
                        ),
                    )
                else:
                    return InputGuardResult(
                        resolved_request=resolved_request,
                        stream_blocked_event=AgentTurnStreamEvent(
                            event_type="reply_completed",
                            session_id=resolved_request.session_id,
                            trace_id=resolved_request.trace_id or "",
                            reply_text=block_text,
                            applied_skills=list(applied_skills),
                            agent_key=resolved_request.agent_key,
                            agent_version=definition.version_number if definition else None,
                        ),
                    )
            if input_result.modified_text is not None:
                resolved_request = resolved_request.model_copy(
                    update={"user_message": input_result.modified_text},
                )

        # Global input guards
        if self._global_guardrail_service is not None:
            input_global_match = await self._global_guardrail_service.evaluate(
                request=resolved_request,
                stage="input",
                content=resolved_request.user_message,
            )
            if input_global_match is not None:
                self._global_guardrail_service.record_match(
                    request=resolved_request, match=input_global_match,
                )
                if input_global_match.rule.action == "block":
                    blocked_resp = self._global_guardrail_service.blocked_response(
                        request=resolved_request,
                        definition=definition,
                        match=input_global_match,
                        applied_skills=applied_skills,
                    )
                    if mode == "blocking":
                        return InputGuardResult(
                            resolved_request=resolved_request,
                            blocked_result=blocked_resp,
                        )
                    else:
                        return InputGuardResult(
                            resolved_request=resolved_request,
                            stream_blocked_event=self._global_guardrail_service.blocked_stream_event(
                                request=resolved_request,
                                definition=definition,
                                match=input_global_match,
                                applied_skills=applied_skills,
                            ),
                        )
                if input_global_match.rule.action == "handoff":
                    handoff_resp = self._global_guardrail_service.handoff_response(
                        request=resolved_request,
                        definition=definition,
                        match=input_global_match,
                        applied_skills=applied_skills,
                    )
                    if mode == "blocking":
                        return InputGuardResult(
                            resolved_request=resolved_request,
                            blocked_result=handoff_resp,
                        )
                    else:
                        handoff_text = self.settings.default_handoff_message
                        return InputGuardResult(
                            resolved_request=resolved_request,
                            stream_blocked_event=self._global_guardrail_service.handoff_stream_event(
                                request=resolved_request,
                                definition=definition,
                                match=input_global_match,
                                handoff_text=handoff_text,
                                applied_skills=applied_skills,
                            ),
                        )
                input_global_alert_match = input_global_match

        return InputGuardResult(
            resolved_request=resolved_request,
            input_global_alert_match=input_global_alert_match,
        )

    async def run_output_guards(
        self,
        reply_text: str,
        request: AgentTurnRequest,
    ) -> tuple[str, bool]:
        """Run output guards on the reply text.

        Returns:
            ``(final_text, was_blocked)`` tuple.
        """
        if self.guards_pipeline is None:
            return reply_text, False

        output_result = await self.guards_pipeline.run_output_guards(
            message=reply_text,
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            metadata=dict(request.metadata),
        )
        if output_result.final_verdict is GuardVerdict.BLOCK:
            return self.guards_pipeline.block_response, True
        if output_result.modified_text is not None:
            return output_result.modified_text, False
        return reply_text, False

    async def evaluate_voice_segment(
        self,
        *,
        request: AgentTurnRequest,
        definition: AgentDefinitionSnapshot | None,
        segment: str,
    ):
        """Evaluate a voice segment against guardrails."""
        if self._voice_evaluator is None:
            return None
        return await self._voice_evaluator.evaluate_segment(
            request=request,
            definition=definition,
            segment=segment,
        )

    async def evaluate_global_guardrails(
        self,
        *,
        request: AgentTurnRequest,
        stage: Literal["input", "output"],
        content: str,
    ):
        """Evaluate content against global guardrails."""
        if self._global_guardrail_service is None:
            return None
        return await self._global_guardrail_service.evaluate(
            request=request, stage=stage, content=content,
        )

    def block_text(self) -> str:
        """Get the configured block response text."""
        if self.guards_pipeline is not None:
            return self.guards_pipeline.block_response
        return self.settings.guardrails.block_response


__all__ = ["InputGuardResult", "TurnGuards"]
