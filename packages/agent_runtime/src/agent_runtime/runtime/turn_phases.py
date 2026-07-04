"""TurnPhase protocol and StreamAwarePhase protocol.

Phases are the building blocks of the turn pipeline.  Each phase implements
``TurnPhase`` and optionally ``StreamAwarePhase`` for streaming-specific
behaviour.  The pipeline driver calls ``execute()`` (or ``stream_execute()``
when streaming) on each phase in order.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ..contracts.models import AgentTurnStreamEvent
from .turn_context import TurnContext


@runtime_checkable
class TurnPhase(Protocol):
    """A single step in the turn execution pipeline.

    Each phase receives the shared ``TurnContext``, may mutate it, and
    signals whether the pipeline should continue.  Phases are stateless
    with respect to a single turn; all per-turn state lives in
    ``TurnContext``.
    """

    @property
    def name(self) -> str: ...

    async def execute(self, ctx: TurnContext) -> None:
        """Run this phase, mutating *ctx* as needed.

        Set ``ctx.should_stop = True`` (and optionally
        ``ctx.short_circuit_result`` or
        ``ctx.short_circuit_stream_event``) to halt the pipeline early.
        Raise ``AgentError`` for hard failures.
        """
        ...


@runtime_checkable
class StreamAwarePhase(Protocol):
    """Optional extension for phases that produce streaming events.

    When a phase implements both ``TurnPhase`` and ``StreamAwarePhase``,
    the pipeline driver calls ``stream_execute()`` instead of
    ``execute()`` when running in streaming mode.
    """

    async def stream_execute(
        self,
        ctx: TurnContext,
    ) -> AsyncIterator[AgentTurnStreamEvent]:
        """Yield streaming events while executing this phase."""
        ...
