"""SubAgentExecutor — runs a sub-agent turn on behalf of a parent agent.

Used by :class:`~delegate_tool.DelegateToAgentTool` to implement the
delegation pattern: the main agent calls ``delegate_to_agent`` as a tool,
and this executor runs the target agent's turn and returns the result.

Safety guards applied before every sub-turn:
1. **Depth limit** — prevents unbounded agent nesting.
2. **Cycle detection** — prevents A→B→A loops.
3. **Agent key validation** — target must be a published definition
   (when a ``definition_loader`` is provided).
"""

from __future__ import annotations

import logging
from typing import AsyncIterator
from uuid import uuid4

from ..contracts.models import AgentAction, AgentTurnRequest, AgentTurnStreamEvent
from ..definition.loader import AgentDefinitionLoader
from .contracts import (
    DelegationResult,
    SubAgentContext,
    SubStreamRunner,
    SubTurnRunner,
    MAX_ORCHESTRATION_DEPTH,
    _CHAIN_METADATA_KEY,
    _DEPTH_METADATA_KEY,
)

logger = logging.getLogger(__name__)

_DEPTH_EXCEEDED_MSG = (
    "Unable to complete: maximum agent delegation depth reached. "
    "Please provide a direct answer."
)
_CYCLE_DETECTED_MSG = (
    "Unable to complete: circular agent delegation detected. "
    "Please provide a direct answer."
)
_AGENT_NOT_FOUND_MSG = (
    "Unable to complete: target agent '{}' is not available. "
    "Please provide a direct answer."
)


class SubAgentExecutor:
    """Executes a single sub-agent turn with safety guards.

    The executor is intentionally stateless between calls — it does not cache
    definitions or maintain connection pools.  All per-call state lives in
    :class:`~contracts.SubAgentContext`.

    Args:
        runner: The :class:`~contracts.SubTurnRunner` that ultimately calls
                ``AgentRuntime.run_turn()``.
        definition_loader: Optional loader used to validate target agents.
                           Pass ``None`` to skip validation (e.g. in tests).
        max_depth: Maximum nesting depth before returning a safe error.
        stream_runner: Optional :class:`~contracts.SubStreamRunner` for
                       :meth:`stream_sub_turn`.  When provided, delegation
                       inside a streaming parent turn will forward sub-agent
                       deltas in real time instead of blocking until complete.
    """

    def __init__(
        self,
        runner: SubTurnRunner,
        *,
        definition_loader: AgentDefinitionLoader | None = None,
        max_depth: int = MAX_ORCHESTRATION_DEPTH,
        stream_runner: SubStreamRunner | None = None,
    ) -> None:
        self._runner = runner
        self._loader = definition_loader
        self._max_depth = max(1, max_depth)
        self._stream_runner = stream_runner

    @property
    def can_stream(self) -> bool:
        """``True`` when a :class:`~contracts.SubStreamRunner` is available."""
        return self._stream_runner is not None

    async def run_sub_turn(
        self,
        agent_key: str,
        user_message: str,
        parent_context: SubAgentContext,
    ) -> DelegationResult:
        """Execute one sub-agent turn and return a :class:`DelegationResult`.

        Args:
            agent_key: Target agent identifier.
            user_message: The task description sent to the sub-agent.
            parent_context: Metadata from the calling agent.

        Returns:
            Always returns a ``DelegationResult``; errors are captured as
            ``action=REPLY`` with an explanatory ``reply_text``.
        """
        error_result = self._check_guards(agent_key, parent_context)
        if error_result is not None:
            return error_result

        if self._loader is not None:
            definition = await self._loader.load(agent_key)
            if definition is None or definition.status != "published":
                logger.warning(
                    "sub_agent_executor unknown agent agent_key=%s", agent_key
                )
                return DelegationResult(
                    agent_key=agent_key,
                    reply_text=_AGENT_NOT_FOUND_MSG.format(agent_key),
                    action=AgentAction.REPLY,
                )

        sub_request = self._build_sub_request(agent_key, user_message, parent_context)

        logger.info(
            "sub_agent_executor delegating parent=%s target=%s depth=%d",
            parent_context.parent_agent_key,
            agent_key,
            parent_context.depth,
        )

        try:
            result = await self._runner.run_turn(sub_request)
        except Exception as exc:
            logger.error(
                "sub_agent_executor run_turn failed agent_key=%s error=%s",
                agent_key,
                exc,
                exc_info=True,
            )
            return DelegationResult(
                agent_key=agent_key,
                reply_text=f"Sub-agent error: {exc}",
                action=AgentAction.REPLY,
                error_message=str(exc),
            )

        return DelegationResult(
            agent_key=agent_key,
            reply_text=result.reply_text,
            action=result.action,
            tool_events=list(result.tool_events),
            usage=result.usage,
            handoff_target=result.handoff_target,
        )

    async def stream_sub_turn(
        self,
        agent_key: str,
        user_message: str,
        parent_context: SubAgentContext,
    ) -> AsyncIterator[AgentTurnStreamEvent]:
        """Stream one sub-agent turn, yielding events as they arrive.

        Requires :attr:`can_stream` to be ``True`` (i.e. a
        :class:`~contracts.SubStreamRunner` was passed at construction time).
        Falls back to a single ``reply_completed`` event when streaming is
        unavailable (using :meth:`run_sub_turn` internally).

        Callers should handle events by type:

        - ``reply_delta`` → forward to the end-user as ``delegation_delta``.
        - ``reply_completed`` / ``handoff`` → extract ``reply_text`` and
          ``usage`` as the tool's final output; do **not** forward verbatim.

        Safety guards (depth, cycle, agent validity) are applied before the
        first event is yielded.  If a guard fires, a single synthetic
        ``reply_completed`` event carrying the error message is emitted.

        Usage::

            async for event in executor.stream_sub_turn(agent_key, msg, ctx):
                if event.event_type == "reply_delta":
                    yield delegation_delta_event(event.delta)
                elif event.event_type == "reply_completed":
                    tool_output = event.reply_text
        """
        from ..contracts.models import AgentTurnStreamEvent as _Event

        def _error_event(text: str) -> AgentTurnStreamEvent:
            return _Event(
                event_type="reply_completed",
                session_id=parent_context.parent_session_id,
                trace_id=parent_context.parent_trace_id,
                reply_text=text,
            )

        error_result = self._check_guards(agent_key, parent_context)
        if error_result is not None:
            yield _error_event(error_result.reply_text)
            return

        if self._loader is not None:
            definition = await self._loader.load(agent_key)
            if definition is None or definition.status != "published":
                logger.warning(
                    "sub_agent_executor (stream) unknown agent agent_key=%s", agent_key
                )
                yield _error_event(_AGENT_NOT_FOUND_MSG.format(agent_key))
                return

        sub_request = self._build_sub_request(agent_key, user_message, parent_context)

        logger.info(
            "sub_agent_executor stream delegating parent=%s target=%s depth=%d",
            parent_context.parent_agent_key,
            agent_key,
            parent_context.depth,
        )

        if self._stream_runner is not None:
            try:
                async for event in self._stream_runner.stream_turn(sub_request):
                    yield event
            except Exception as exc:
                logger.error(
                    "sub_agent_executor stream_turn failed agent_key=%s error=%s",
                    agent_key,
                    exc,
                    exc_info=True,
                )
                yield _error_event(f"Sub-agent error: {exc}")
        else:
            # Fallback: run non-streaming and emit a single completed event
            try:
                result = await self._runner.run_turn(sub_request)
                yield _Event(
                    event_type="reply_completed",
                    session_id=parent_context.parent_session_id,
                    trace_id=parent_context.parent_trace_id,
                    reply_text=result.reply_text,
                    usage=result.usage,
                )
            except Exception as exc:
                logger.error(
                    "sub_agent_executor fallback run_turn failed agent_key=%s error=%s",
                    agent_key,
                    exc,
                    exc_info=True,
                )
                yield _error_event(f"Sub-agent error: {exc}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_guards(
        self,
        agent_key: str,
        parent_context: SubAgentContext,
    ) -> DelegationResult | None:
        """Return a safe-error DelegationResult if a guard fires, else None."""
        if parent_context.depth >= self._max_depth:
            logger.warning(
                "sub_agent_executor depth limit agent_key=%s depth=%d max=%d",
                agent_key,
                parent_context.depth,
                self._max_depth,
            )
            return DelegationResult(
                agent_key=agent_key,
                reply_text=_DEPTH_EXCEEDED_MSG,
                action=AgentAction.REPLY,
            )

        chain = parent_context.shared_metadata.get(_CHAIN_METADATA_KEY, "")
        chain_keys = [k for k in chain.split(",") if k]
        if agent_key in chain_keys:
            logger.warning(
                "sub_agent_executor cycle detected agent_key=%s chain=%s",
                agent_key,
                chain,
            )
            return DelegationResult(
                agent_key=agent_key,
                reply_text=_CYCLE_DETECTED_MSG,
                action=AgentAction.REPLY,
            )
        return None

    def _build_sub_request(
        self,
        agent_key: str,
        user_message: str,
        parent_context: SubAgentContext,
    ) -> AgentTurnRequest:
        """Build the AgentTurnRequest for the sub-agent turn."""
        chain = parent_context.shared_metadata.get(_CHAIN_METADATA_KEY, "")
        updated_chain = f"{chain},{agent_key}" if chain else agent_key

        new_metadata = dict(parent_context.shared_metadata)
        new_metadata[_CHAIN_METADATA_KEY] = updated_chain
        new_metadata[_DEPTH_METADATA_KEY] = str(parent_context.depth + 1)

        intro_parts: list[str] = []
        if parent_context.summary:
            intro_parts.append(f"[Context]\n{parent_context.summary}")
        intro_parts.append(user_message)
        composed_message = "\n\n".join(intro_parts)

        return AgentTurnRequest(
            session_id=parent_context.parent_session_id,
            user_message=composed_message,
            agent_key=agent_key,
            customer_id=None,
            trace_id=f"{parent_context.parent_trace_id}->{agent_key}-{uuid4().hex[:6]}",
            metadata=new_metadata,
        )
