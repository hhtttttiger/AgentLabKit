"""Voice channel — guardrail evaluation, safe-reply generation, and audit.

All voice-specific constants, data structures, and evaluation logic are
extracted here so that ``runtime/engine.py`` stays focused on the generic
turn lifecycle.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
import inspect
import logging
from typing import Any

from ..contracts.models import AgentTurnRequest
from ..definition.models import AgentDefinitionSnapshot
from ..guardrails import GuardContext, GuardResult, GuardsPipeline, GuardVerdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VOICE_TOOL_TIMEOUT_MS = "voice_tool_timeout_ms"
VOICE_INPUT_SOURCE = "voice_input_source"
TURN_TIMEOUT_MS = "turn_timeout_ms"
DEFAULT_VOICE_TOOL_TIMEOUT_SECONDS = 6.0

_SENTENCE_ENDINGS = ("。", "！", "？", ".", "!", "?")
VOICE_SAFE_FALLBACK_TEXT = "I'm sorry, but I can't help with that."
VOICE_SUPPORTED_ACTIONS = frozenset(
    {"interrupt_only", "fallback_reply", "transfer_human", "transfer_agent"}
)


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def parse_positive_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def split_flushable_voice_segments(buffer: str) -> tuple[list[str], str]:
    """Return all complete sentence segments and the remaining unfinished tail."""
    import re

    pattern = r'(.*?[。！？.!?])'
    segments = []
    last_end = 0
    for match in re.finditer(pattern, buffer, re.DOTALL):
        segments.append(match.group(1).strip())
        last_end = match.end()
    tail = buffer[last_end:] if last_end < len(buffer) else ""
    if tail and not tail.strip():
        tail = ""
    return [s for s in segments if s], tail


def voice_tool_timeout_seconds(request: AgentTurnRequest) -> float | None:
    metadata = request.metadata or {}
    if request.channel != "voice" and VOICE_INPUT_SOURCE not in metadata:
        return None

    configured_ms = parse_positive_float(metadata.get(VOICE_TOOL_TIMEOUT_MS))
    if configured_ms is not None:
        return max(0.001, configured_ms / 1000)

    timeout = DEFAULT_VOICE_TOOL_TIMEOUT_SECONDS
    turn_timeout_ms = parse_positive_float(metadata.get(TURN_TIMEOUT_MS))
    if turn_timeout_ms is not None:
        timeout = min(timeout, max(1.0, (turn_timeout_ms / 1000) * 0.35))
    return timeout


def voice_tool_fallback_output(tool_name: str, error: BaseException) -> str:
    return (
        f"Tool {tool_name} did not return usable data quickly enough: {error}. "
        "Give the user a brief natural-language answer now. If live data is required, "
        "say the live lookup is temporarily unavailable and ask them to try again."
    )


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class VoiceSegmentOutcome:
    action: str
    visible_text: str = ""
    handoff_reason: str | None = None
    modified: bool = False
    handoff_target_type: str | None = None
    """``"human"`` or ``"agent"`` — when ``action="handoff"``."""
    handoff_target_agent_key: str | None = None
    """Agent key — set when ``handoff_target_type="agent"``."""


@dataclass(slots=True)
class VoiceGuardrailAuditRecord:
    session_id: str
    trace_id: str
    revision: int
    mode: str
    action: str
    reason: str | None
    visible_text: str
    simulated: bool
    matched: bool
    segment: str
    failure_mode: str | None = None
    guard_name: str | None = None
    confidence: float | None = None


@dataclass(slots=True)
class VoiceSafeReplyOutcome:
    text: str
    failure_mode: str | None = None


# ---------------------------------------------------------------------------
# VoiceGuardrailEvaluator
# ---------------------------------------------------------------------------


class VoiceGuardrailEvaluator:
    """Evaluates voice segments against guardrails and generates safe replies.

    Extracted from ``AgentRuntime`` to decouple voice-specific logic from the
    core turn lifecycle.
    """

    def __init__(
        self,
        guards_pipeline: GuardsPipeline | None = None,
        build_output_guard_metadata: Callable[..., dict[str, str]] | None = None,
    ) -> None:
        self._guards_pipeline = guards_pipeline
        self._build_output_guard_metadata = build_output_guard_metadata
        self._records: deque[VoiceGuardrailAuditRecord] = deque(maxlen=100)
        self._counters: dict[str, int] = {
            "evaluated_count": 0,
            "hit_count": 0,
            "block_count": 0,
            "fallback_count": 0,
            "handoff_count": 0,
            "interrupt_count": 0,
            "modify_count": 0,
            "simulated_count": 0,
            "judge_failure_count": 0,
            "generator_failure_count": 0,
        }

    # ------------------------------------------------------------------
    # Properties for runtime delegation
    # ------------------------------------------------------------------

    @property
    def guards_pipeline(self) -> GuardsPipeline | None:
        return self._guards_pipeline

    @guards_pipeline.setter
    def guards_pipeline(self, value: GuardsPipeline | None) -> None:
        self._guards_pipeline = value

    @property
    def build_output_guard_metadata(self) -> Callable[..., dict[str, str]] | None:
        return self._build_output_guard_metadata

    @build_output_guard_metadata.setter
    def build_output_guard_metadata(self, value: Callable[..., dict[str, str]] | None) -> None:
        self._build_output_guard_metadata = value

    # ------------------------------------------------------------------
    # Public query API (delegated from AgentRuntime)
    # ------------------------------------------------------------------

    def recent_samples(self, limit: int = 10) -> list[dict[str, object]]:
        if limit <= 0:
            return []
        records = list(self._records)[-limit:]
        return [
            {
                "session_id": record.session_id,
                "trace_id": record.trace_id,
                "revision": record.revision,
                "mode": record.mode,
                "action": record.action,
                "reason": record.reason,
                "visible_text": record.visible_text,
                "simulated": record.simulated,
                "matched": record.matched,
                "segment": record.segment,
                "failure_mode": record.failure_mode,
                "guard_name": record.guard_name,
                "confidence": record.confidence,
            }
            for record in reversed(records)
        ]

    def metrics(self) -> dict[str, int | float]:
        metrics: dict[str, int | float] = dict(self._counters)
        evaluated = max(1, int(metrics["evaluated_count"]))
        metrics["judge_failure_rate"] = (
            float(metrics["judge_failure_count"]) / evaluated
        )
        metrics["generator_failure_rate"] = (
            float(metrics["generator_failure_count"]) / evaluated
        )
        metrics["recent_sample_count"] = len(self._records)
        return metrics

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    async def evaluate_segment(
        self,
        *,
        request: AgentTurnRequest,
        definition: AgentDefinitionSnapshot | None,
        segment: str,
    ) -> VoiceSegmentOutcome:
        """Evaluate a voice segment against output guardrails."""
        import time

        if (
            self._guards_pipeline is None
            or definition is None
            or definition.voice_guardrails is None
        ):
            return VoiceSegmentOutcome(action="emit", visible_text=segment)

        voice_guardrails = definition.voice_guardrails
        budget_ms = voice_guardrails.max_added_latency_ms
        start = time.monotonic()
        try:
            async with asyncio.timeout(voice_guardrails.judge_timeout_ms / 1000):
                metadata = (
                    self._build_output_guard_metadata(request=request, segment=segment)
                    if self._build_output_guard_metadata
                    else dict(request.metadata)
                )
                output_result = await self._guards_pipeline.run_output_guards(
                    message=segment,
                    session_id=request.session_id,
                    trace_id=request.trace_id or "",
                    metadata=metadata,
                )
        except TimeoutError:
            logger.warning(
                "voice_guardrails_judge_timed_out trace_id=%s session_id=%s",
                request.trace_id,
                request.session_id,
            )
            self._record_outcome(
                request=request,
                voice_guardrails=voice_guardrails,
                segment=segment,
                action="allow",
                visible_text=segment,
                matched=False,
                simulated=False,
                failure_mode="judge_timeout",
            )
            return VoiceSegmentOutcome(action="emit", visible_text=segment)
        except Exception:
            logger.exception(
                "voice_guardrails_judge_failed trace_id=%s session_id=%s",
                request.trace_id,
                request.session_id,
            )
            self._record_outcome(
                request=request,
                voice_guardrails=voice_guardrails,
                segment=segment,
                action="allow",
                visible_text=segment,
                matched=False,
                simulated=False,
                failure_mode="judge_failed",
            )
            return VoiceSegmentOutcome(action="emit", visible_text=segment)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        remaining_budget_ms = max(0, budget_ms - elapsed_ms)

        if output_result.final_verdict is GuardVerdict.BLOCK:
            guard_result = output_result.results[-1] if output_result.results else None
            action = self._resolve_action(
                voice_guardrails.actions,
                guard_result,
            )
            if voice_guardrails.mode != "enforced":
                logger.info(
                    "voice_guardrails_simulated trace_id=%s session_id=%s action=%s reason=%s",
                    request.trace_id,
                    request.session_id,
                    action,
                    output_result.block_reason,
                )
                self._record_outcome(
                    request=request,
                    voice_guardrails=voice_guardrails,
                    segment=segment,
                    action=action,
                    visible_text=segment,
                    reason=output_result.block_reason,
                    matched=True,
                    simulated=True,
                    guard_result=guard_result,
                )
                return VoiceSegmentOutcome(action="emit", visible_text=segment)

            if action == "transfer_human":
                self._record_outcome(
                    request=request,
                    voice_guardrails=voice_guardrails,
                    segment=segment,
                    action=action,
                    visible_text="",
                    reason=output_result.block_reason,
                    matched=True,
                    simulated=False,
                    guard_result=guard_result,
                )
                return VoiceSegmentOutcome(
                    action="handoff",
                    handoff_reason=output_result.block_reason or "voice_guardrail_transfer",
                    handoff_target_type="human",
                    modified=True,
                )
            if action == "transfer_agent":
                self._record_outcome(
                    request=request,
                    voice_guardrails=voice_guardrails,
                    segment=segment,
                    action=action,
                    visible_text="",
                    reason=output_result.block_reason,
                    matched=True,
                    simulated=False,
                    guard_result=guard_result,
                )
                return VoiceSegmentOutcome(
                    action="handoff",
                    handoff_reason=output_result.block_reason or "voice_guardrail_transfer_agent",
                    handoff_target_type="agent",
                    modified=True,
                )
            if action == "fallback_reply":
                # Enforce latency budget for safe reply generation
                if remaining_budget_ms <= 0:
                    logger.warning(
                        "voice_guardrails_latency_budget_exceeded trace_id=%s session_id=%s",
                        request.trace_id,
                        request.session_id,
                    )
                    self._record_outcome(
                        request=request,
                        voice_guardrails=voice_guardrails,
                        segment=segment,
                        action="allow",
                        visible_text=segment,
                        reason=output_result.block_reason,
                        matched=True,
                        simulated=False,
                        failure_mode="latency_budget_exceeded",
                        guard_result=guard_result,
                    )
                    return VoiceSegmentOutcome(action="emit", visible_text=segment)
                timeout = min(voice_guardrails.generator_timeout_ms, remaining_budget_ms)
                timeout_fallback_text = (
                    segment
                    if timeout < voice_guardrails.generator_timeout_ms
                    else VOICE_SAFE_FALLBACK_TEXT
                )
                safe_reply = await self._generate_safe_reply(
                    request=request,
                    guard_result=guard_result,
                    segment=segment,
                    definition=definition,
                    timeout_ms=timeout,
                    timeout_fallback_text=timeout_fallback_text,
                )
                visible_text = safe_reply.text
                self._record_outcome(
                    request=request,
                    voice_guardrails=voice_guardrails,
                    segment=segment,
                    action=action,
                    visible_text=visible_text,
                    reason=output_result.block_reason,
                    matched=True,
                    simulated=False,
                    failure_mode=safe_reply.failure_mode,
                    guard_result=guard_result,
                )
                return VoiceSegmentOutcome(
                    action="emit",
                    visible_text=visible_text,
                    modified=visible_text != segment,
                )
            self._record_outcome(
                request=request,
                voice_guardrails=voice_guardrails,
                segment=segment,
                action=action,
                visible_text="",
                reason=output_result.block_reason,
                matched=True,
                simulated=False,
                guard_result=guard_result,
            )
            return VoiceSegmentOutcome(action="suppress", modified=True)

        if voice_guardrails.mode != "enforced":
            logger.info(
                "voice_guardrails_simulated trace_id=%s session_id=%s action=modify reason=%s",
                request.trace_id,
                request.session_id,
                output_result.block_reason,
            )
            guard_result = output_result.results[-1] if output_result.results else None
            action = "modify" if output_result.modified_text is not None else "allow"
            self._record_outcome(
                request=request,
                voice_guardrails=voice_guardrails,
                segment=segment,
                action=action,
                visible_text=segment,
                reason=output_result.block_reason,
                matched=output_result.modified_text is not None,
                simulated=True,
                guard_result=guard_result,
            )
            return VoiceSegmentOutcome(action="emit", visible_text=segment)

        if output_result.modified_text is not None:
            guard_result = output_result.results[-1] if output_result.results else None
            self._record_outcome(
                request=request,
                voice_guardrails=voice_guardrails,
                segment=segment,
                action="modify",
                visible_text=output_result.modified_text,
                reason=output_result.block_reason,
                matched=True,
                simulated=False,
                guard_result=guard_result,
            )
            return VoiceSegmentOutcome(
                action="emit",
                visible_text=output_result.modified_text,
                modified=True,
            )
        guard_result = output_result.results[-1] if output_result.results else None
        self._record_outcome(
            request=request,
            voice_guardrails=voice_guardrails,
            segment=segment,
            action="allow",
            visible_text=segment,
            reason=output_result.block_reason,
            matched=False,
            simulated=False,
            guard_result=guard_result,
        )
        return VoiceSegmentOutcome(action="emit", visible_text=segment)

    # ------------------------------------------------------------------
    # Safe reply generation
    # ------------------------------------------------------------------

    async def _generate_safe_reply(
        self,
        *,
        request: AgentTurnRequest,
        guard_result: GuardResult | None,
        segment: str,
        definition: AgentDefinitionSnapshot | None,
        timeout_ms: int | None = None,
        timeout_fallback_text: str | None = None,
    ) -> VoiceSafeReplyOutcome:
        if (
            self._guards_pipeline is None
            or self._guards_pipeline.safe_reply_generator is None
            or definition is None
            or definition.voice_guardrails is None
            or guard_result is None
        ):
            return VoiceSafeReplyOutcome(text=VOICE_SAFE_FALLBACK_TEXT)

        try:
            effective_timeout_ms = (
                timeout_ms
                if timeout_ms is not None
                else definition.voice_guardrails.generator_timeout_ms
            )
            metadata = (
                self._build_output_guard_metadata(request=request, segment=segment)
                if self._build_output_guard_metadata
                else dict(request.metadata)
            )
            async with asyncio.timeout(effective_timeout_ms / 1000):
                generated = self._guards_pipeline.safe_reply_generator(
                    GuardContext(
                        phase="output",
                        message=segment,
                        session_id=request.session_id,
                        trace_id=request.trace_id or "",
                        metadata=metadata,
                    ),
                    guard_result,
                )
                if inspect.isawaitable(generated):
                    generated = await generated
        except TimeoutError:
            logger.warning(
                "voice_safe_reply_generation_timed_out trace_id=%s session_id=%s",
                request.trace_id,
                request.session_id,
            )
            return VoiceSafeReplyOutcome(
                text=(
                    timeout_fallback_text
                    if timeout_fallback_text is not None
                    else VOICE_SAFE_FALLBACK_TEXT
                ),
                failure_mode="generator_timeout",
            )
        except Exception:
            logger.exception(
                "voice_safe_reply_generation_failed trace_id=%s session_id=%s",
                request.trace_id,
                request.session_id,
            )
            return VoiceSafeReplyOutcome(
                text=VOICE_SAFE_FALLBACK_TEXT,
                failure_mode="generator_failed",
            )

        generated_text = str(generated).strip()
        return VoiceSafeReplyOutcome(text=generated_text or VOICE_SAFE_FALLBACK_TEXT)

    # ------------------------------------------------------------------
    # Audit & metrics
    # ------------------------------------------------------------------

    def _record_outcome(
        self,
        *,
        request: AgentTurnRequest,
        voice_guardrails: Any,
        segment: str,
        action: str,
        visible_text: str,
        matched: bool,
        simulated: bool,
        reason: str | None = None,
        failure_mode: str | None = None,
        guard_result: GuardResult | None = None,
    ) -> None:
        record = VoiceGuardrailAuditRecord(
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            revision=voice_guardrails.revision,
            mode=voice_guardrails.mode,
            action=action,
            reason=reason,
            visible_text=visible_text,
            simulated=simulated,
            matched=matched,
            segment=segment,
            failure_mode=failure_mode,
            guard_name=guard_result.guard_name if guard_result else None,
            confidence=guard_result.confidence if guard_result else None,
        )
        self._records.append(record)
        self._counters["evaluated_count"] += 1
        if matched:
            self._counters["hit_count"] += 1
        if simulated:
            self._counters["simulated_count"] += 1
        if action in {"fallback_reply", "transfer_human", "transfer_agent", "interrupt_only"}:
            self._counters["block_count"] += 1
        if action == "fallback_reply":
            self._counters["fallback_count"] += 1
        elif action in {"transfer_human", "transfer_agent"}:
            self._counters["handoff_count"] += 1
        elif action == "interrupt_only":
            self._counters["interrupt_count"] += 1
        elif action == "modify":
            self._counters["modify_count"] += 1
        if failure_mode == "judge_timeout" or failure_mode == "judge_failed":
            self._counters["judge_failure_count"] += 1
        if failure_mode == "generator_timeout" or failure_mode == "generator_failed":
            self._counters["generator_failure_count"] += 1

    @staticmethod
    def _resolve_action(
        allowed_actions: tuple[str, ...],
        guard_result: GuardResult | None,
    ) -> str:
        suggested = guard_result.details.get("suggested_action") if guard_result else None
        if isinstance(suggested, str):
            suggested = suggested.strip().lower()
        if suggested in VOICE_SUPPORTED_ACTIONS and (
            not allowed_actions or suggested in allowed_actions
        ):
            return suggested
        if "interrupt_only" in allowed_actions or not allowed_actions:
            return "interrupt_only"
        for action in allowed_actions:
            if action in VOICE_SUPPORTED_ACTIONS:
                return action
        return "interrupt_only"
