"""Voice stream handler — buffering and guardrail evaluation for voice channels.

Extracts the voice-specific streaming logic from :meth:`AgentRuntime.stream_turn`
so the engine stays focused on the generic turn lifecycle.

The handler accumulates streaming text into sentence-level segments, evaluates
each segment against voice guardrails, and tracks whether the reply was modified
or a handoff was triggered.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..channels.voice import (
    VoiceSegmentOutcome,
    split_flushable_voice_segments,
)
from ..contracts.models import AgentTurnRequest
from ..definition.models import AgentDefinitionSnapshot

if TYPE_CHECKING:
    from .turn_guards import TurnGuards

logger = logging.getLogger(__name__)


class VoiceStreamHandler:
    """Manages voice guardrail buffering during streaming turns.

    When voice guardrails are active, streaming deltas are accumulated into a
    sentence buffer.  Complete sentences are evaluated against guardrails, and
    only approved text is forwarded to the client.

    Methods return lists of deltas ready for client emission, keeping the
    caller's ``pending_reply_deltas`` list in sync without fragile length
    tracking.
    """

    def __init__(
        self,
        *,
        turn_guards: TurnGuards,
        request: AgentTurnRequest,
        definition: AgentDefinitionSnapshot | None,
    ) -> None:
        self._turn_guards = turn_guards
        self._request = request
        self._definition = definition

        # Determine if voice buffer mode is active
        self._active = (
            request.channel == "voice"
            and definition is not None
            and definition.voice_guardrails is not None
        )

        # Accumulation state
        self._sentence_buffer = ""
        self._visible_parts: list[str] = []
        self._modified = False
        self._handoff_reason: str | None = None
        self._handoff_outcome: VoiceSegmentOutcome | None = None

    # ── Public properties ──────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Whether voice buffer mode is active for this turn."""
        return self._active

    @property
    def should_handoff(self) -> bool:
        """Whether a voice guardrail triggered a handoff."""
        return self._handoff_reason is not None

    @property
    def handoff_reason(self) -> str | None:
        """The reason for the handoff, if triggered."""
        return self._handoff_reason

    @property
    def handoff_outcome(self) -> VoiceSegmentOutcome | None:
        """The full outcome of the voice guardrail that triggered handoff."""
        return self._handoff_outcome

    @property
    def visible_reply(self) -> str:
        """The accumulated visible reply text (after guardrail filtering)."""
        return "".join(self._visible_parts)

    @property
    def was_modified(self) -> bool:
        """Whether the reply was modified by voice guardrails."""
        return self._modified

    # ── Processing ─────────────────────────────────────────────────────────

    async def process_delta(self, delta_text: str) -> list[str]:
        """Process a streaming text delta and return new deltas for emission.

        In voice buffer mode, text is accumulated into a sentence buffer.
        Complete sentences are evaluated against guardrails.  Returns an
        empty list when the buffer has not yet produced a flushable segment.
        """
        if not self._active:
            return [delta_text]

        self._sentence_buffer += delta_text
        segments, self._sentence_buffer = split_flushable_voice_segments(
            self._sentence_buffer,
        )
        new_deltas: list[str] = []
        for seg in segments:
            if self._handoff_reason is not None:
                continue
            new_deltas.extend(await self._evaluate_segment(seg))
        return new_deltas

    async def flush(self) -> list[str]:
        """Flush remaining text in the sentence buffer.

        Called when the LLM stream signals ``is_done``.  Returns deltas
        from any remaining segments.
        """
        if not self._active or self._handoff_reason is not None:
            return []
        if not self._sentence_buffer.strip():
            self._sentence_buffer = ""
            return []

        new_deltas: list[str] = []
        segments, tail = split_flushable_voice_segments(self._sentence_buffer)
        for seg in segments:
            if self._handoff_reason is not None:
                break
            new_deltas.extend(await self._evaluate_segment(seg))

        if self._handoff_reason is None and tail.strip():
            new_deltas.extend(await self._evaluate_segment(tail.strip()))

        self._sentence_buffer = ""
        return new_deltas

    # ── Internal ───────────────────────────────────────────────────────────

    async def _evaluate_segment(self, segment: str) -> list[str]:
        """Evaluate a single segment against voice guardrails.

        Returns deltas for emission (empty if the segment was blocked or
        triggered a handoff).
        """
        outcome = await self._turn_guards.evaluate_voice_segment(
            request=self._request,
            definition=self._definition,
            segment=segment,
        )
        if outcome is None:
            return []
        self._modified = self._modified or outcome.modified
        if outcome.action == "handoff":
            self._handoff_reason = outcome.handoff_reason
            self._handoff_outcome = outcome
            return []
        if outcome.visible_text:
            self._visible_parts.append(outcome.visible_text)
            return [outcome.visible_text]
        return []
