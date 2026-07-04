"""TurnPipeline — orchestrates a sequence of ``TurnPhase`` instances.

The pipeline driver walks through phases in order and supports both
blocking (``run``) and streaming (``stream``) modes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import logging

from ..contracts.models import (
    AgentAction,
    AgentMessage,
    AgentRole,
    AgentTurnResult,
    AgentTurnStreamEvent,
    HandoffTarget,
)
from .turn_context import TurnContext
from .turn_phases import StreamAwarePhase, TurnPhase

logger = logging.getLogger(__name__)


class TurnPipeline:
    """Orchestrates the execution of a list of ``TurnPhase`` instances.

    Typical usage::

        pipeline = TurnPipeline([
            ResolveDefinitionPhase(...),
            InputGuardsPhase(...),
            ExecutePhase(...),
            PostExecutionPhase(...),
            PersistSessionPhase(...),
        ])

        # Blocking mode
        result = await pipeline.run(ctx)

        # Streaming mode
        async for event in pipeline.stream(ctx):
            yield event
    """

    def __init__(self, phases: list[TurnPhase]) -> None:
        self.phases = phases

    async def run(self, ctx: TurnContext) -> AgentTurnResult:
        """Execute all phases in blocking mode and return the final result."""
        for phase in self.phases:
            if ctx.should_stop:
                break
            await phase.execute(ctx)

        if ctx.short_circuit_result is not None:
            return ctx.short_circuit_result

        return self._build_result(ctx)

    async def stream(self, ctx: TurnContext) -> AsyncIterator[AgentTurnStreamEvent]:
        """Execute all phases in streaming mode, yielding events."""
        for phase in self.phases:
            if ctx.should_stop:
                break

            if isinstance(phase, StreamAwarePhase):
                async for event in phase.stream_execute(ctx):
                    yield event
            else:
                await phase.execute(ctx)

            if ctx.short_circuit_stream_event is not None:
                yield ctx.short_circuit_stream_event
                return

        # If we get here without a short-circuit, yield any pending deltas
        for delta in ctx.pending_reply_deltas:
            yield AgentTurnStreamEvent(
                event_type="reply_delta",
                session_id=ctx.session_id,
                trace_id=ctx.trace_id,
                delta=delta,
            )
        ctx.pending_reply_deltas.clear()

    @staticmethod
    def _build_result(ctx: TurnContext) -> AgentTurnResult:
        """Build the final ``AgentTurnResult`` from context state."""
        return AgentTurnResult(
            session_id=ctx.session_id,
            trace_id=ctx.trace_id,
            action=ctx.action,
            reply_text=ctx.reply_text,
            handoff_reason=ctx.handoff_reason,
            tool_events=list(ctx.tool_events),
            usage=ctx.usage,
            raw_messages=list(ctx.raw_messages),
            agent_key=ctx.original_request.agent_key,
            agent_version=ctx.definition.version_number if ctx.definition else None,
            applied_skills=list(ctx.applied_skills),
            handoff_target=ctx.handoff_target,
        )
