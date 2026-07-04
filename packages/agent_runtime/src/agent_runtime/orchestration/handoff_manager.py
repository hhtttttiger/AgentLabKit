"""HandoffManager — manages the complete agent-to-agent handoff flow.

Responsibilities:
- Resolve a ``HandoffDecision`` (human vs agent) using ``AgentRouter``
- Validate that the target agent exists and is published
- Prepare cross-agent context via a ``ContextPasser``
- Execute the target agent's first turn via ``SubTurnRunner``
- Stream the target agent's turn via ``SubStreamRunner`` (when available)

The manager is optional in ``AgentRuntime`` — when absent, the legacy
human-only handoff behaviour is unchanged.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from uuid import uuid4

from ..contracts.models import (
    AgentAction,
    AgentMessage,
    AgentTurnRequest,
    AgentTurnResult,
    AgentTurnStreamEvent,
    HandoffTarget,
)
from ..definition.loader import AgentDefinitionLoader
from .contracts import (
    HandoffResolution,
    HandoffRouteTarget,
    SubStreamRunner,
    SubTurnRunner,
    _CHAIN_METADATA_KEY,
    _DEPTH_METADATA_KEY,
)
from .context_passing import ContextPasser
from .router import AgentRouter

logger = logging.getLogger(__name__)


class HandoffManager:
    """Orchestrates agent-to-agent handoff.

    ``definition_loader`` is used to validate that the target agent is
    published before attempting execution.  Pass ``None`` to disable
    validation (useful in tests with pre-wired definitions).

    ``context_passer`` determines how conversation history is prepared for
    the target agent.  Defaults to :class:`~context_passing.DirectContextPasser`.

    ``stream_runner`` enables :meth:`stream_execute_agent_handoff`.  When
    absent, :attr:`can_stream` is ``False`` and streaming falls back to the
    blocking runner.
    """

    def __init__(
        self,
        runner: SubTurnRunner,
        *,
        definition_loader: AgentDefinitionLoader | None = None,
        context_passer: ContextPasser | None = None,
        stream_runner: SubStreamRunner | None = None,
    ) -> None:
        from .context_passing import DirectContextPasser

        self._runner = runner
        self._loader = definition_loader
        self._context_passer: ContextPasser = context_passer or DirectContextPasser()
        self._stream_runner = stream_runner

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def can_stream(self) -> bool:
        """True when a :class:`SubStreamRunner` is available for streaming handoff."""
        return self._stream_runner is not None

    # ------------------------------------------------------------------
    # Public API — Resolution
    # ------------------------------------------------------------------

    async def resolve_handoff(
        self,
        handoff_target: HandoffTarget,
        *,
        handoff_policy: dict | None = None,
    ) -> HandoffResolution:
        """Resolve a structured HandoffTarget to a HandoffResolution.

        If ``handoff_policy`` contains routes, runs ``AgentRouter`` to
        refine/override the LLM-specified target.

        Returns a resolution with ``action=HANDOFF_HUMAN`` or ``HANDOFF_AGENT``.
        """
        # 1. Route through policy if available
        resolved_target: HandoffRouteTarget | None = None
        if handoff_policy:
            router = AgentRouter(handoff_policy)
            resolved_target = router.resolve(
                handoff_target.reason,
                llm_target_type=handoff_target.target_type,
                llm_target_agent=handoff_target.target_agent_key,
            )

        # 2. If no policy routing, use the LLM-specified target directly
        if resolved_target is None:
            if handoff_target.target_type == "agent" and handoff_target.target_agent_key:
                resolved_target = HandoffRouteTarget(
                    target_type="agent",
                    target_agent_key=handoff_target.target_agent_key,
                    reason=handoff_target.reason,
                )
            else:
                resolved_target = HandoffRouteTarget(
                    target_type="human",
                    reason=handoff_target.reason,
                )

        # 3. Validate agent target
        if resolved_target.target_type == "agent":
            valid = await self._validate_agent_target(resolved_target.target_agent_key)
            if not valid:
                logger.warning(
                    "handoff_manager target validation failed agent_key=%s, falling back to human",
                    resolved_target.target_agent_key,
                )
                return HandoffResolution(
                    action=AgentAction.HANDOFF_HUMAN,
                    reason=resolved_target.reason,
                )
            return HandoffResolution(
                action=AgentAction.HANDOFF_AGENT,
                target_agent_key=resolved_target.target_agent_key,
                reason=resolved_target.reason,
                context_for_target=resolved_target.context_message,
            )

        return HandoffResolution(
            action=AgentAction.HANDOFF_HUMAN,
            reason=resolved_target.reason,
        )

    # ------------------------------------------------------------------
    # Public API — Blocking execution
    # ------------------------------------------------------------------

    async def execute_agent_handoff(
        self,
        resolution: HandoffResolution,
        *,
        request: AgentTurnRequest,
        history: list[AgentMessage],
    ) -> AgentTurnResult:
        """Execute an agent-to-agent handoff (blocking).

        Prepares context from ``history``, builds a new request with the
        target agent key, and delegates to ``SubTurnRunner.run_turn()``.

        The returned ``AgentTurnResult`` will have ``orchestration_chain`` set
        to reflect the handoff path (e.g. ``["triage", "refund-specialist"]``).
        """
        target_key = resolution.target_agent_key
        assert target_key, "execute_agent_handoff called without a target_agent_key"

        sub_request = await self._build_handoff_sub_request(
            resolution, request=request, history=history,
        )

        logger.info(
            "handoff_manager executing agent handoff source=%s target=%s",
            request.agent_key or "unknown",
            target_key,
        )

        sub_result = await self._runner.run_turn(sub_request)

        return self._annotate_chain(sub_result, sub_request, target_key, resolution)

    # ------------------------------------------------------------------
    # Public API — Streaming execution
    # ------------------------------------------------------------------

    async def stream_execute_agent_handoff(
        self,
        resolution: HandoffResolution,
        *,
        request: AgentTurnRequest,
        history: list[AgentMessage],
    ) -> AsyncIterator[AgentTurnStreamEvent]:
        """Execute an agent-to-agent handoff (streaming).

        Yields ``AgentTurnStreamEvent`` objects from the target agent's turn.
        When a ``SubStreamRunner`` is available, events are streamed in
        real-time.  Otherwise falls back to a blocking turn and yields a
        single synthetic ``reply_completed`` event.

        The final yielded event will have ``responding_agent_key`` and
        ``orchestration_chain`` set in its metadata.
        """
        target_key = resolution.target_agent_key
        assert target_key, "stream_execute_agent_handoff called without a target_agent_key"

        sub_request = await self._build_handoff_sub_request(
            resolution, request=request, history=history,
        )

        logger.info(
            "handoff_manager streaming agent handoff source=%s target=%s",
            request.agent_key or "unknown",
            target_key,
        )

        # Build chain annotation for final event
        existing_chain = sub_request.metadata.get(_CHAIN_METADATA_KEY, "")
        source_key = request.agent_key or "unknown"
        chain = f"{existing_chain},{source_key}" if existing_chain else source_key
        chain_list = [k for k in chain.split(",") if k] + [target_key]

        if self._stream_runner is not None:
            # Streaming path — forward events from the sub-agent
            async for event in self._stream_runner.stream_turn(sub_request):
                yield event
        else:
            # Fallback — blocking call, yield single synthetic event
            sub_result = await self._runner.run_turn(sub_request)
            yield AgentTurnStreamEvent(
                event_type="reply_completed",
                session_id=sub_request.session_id,
                trace_id=sub_request.trace_id,
                reply_text=sub_result.reply_text,
                usage=sub_result.usage,
                raw_messages=sub_result.raw_messages,
                handoff_target=HandoffTarget(
                    target_type="agent",
                    target_agent_key=target_key,
                    reason=resolution.reason,
                ),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _build_handoff_sub_request(
        self,
        resolution: HandoffResolution,
        *,
        request: AgentTurnRequest,
        history: list[AgentMessage],
    ) -> AgentTurnRequest:
        """Build the sub-request for a handoff execution (shared by blocking + streaming)."""
        target_key = resolution.target_agent_key
        assert target_key

        # Prepare handoff context
        context = await self._context_passer.prepare_context(
            source_agent_key=request.agent_key or "unknown",
            target_agent_key=target_key,
            history=history,
            handoff_reason=resolution.reason,
            customer_id=request.customer_id,
            locale=request.locale,
        )

        # Build the opening message for the target agent
        intro_parts: list[str] = []
        if context.summary:
            intro_parts.append(f"[Context from {context.source_agent_key}]\n{context.summary}")
        if resolution.context_for_target:
            intro_parts.append(
                f"[Additional handoff context]\n{resolution.context_for_target}"
            )
        if context.handoff_reason:
            intro_parts.append(f"Handoff reason: {context.handoff_reason}")
        if context.key_facts:
            intro_parts.append("Key facts:\n" + "\n".join(f"• {f}" for f in context.key_facts))
        intro_parts.append(f"[Customer message] {request.user_message}")
        target_message = "\n\n".join(intro_parts)

        # Build the metadata chain
        existing_chain = request.metadata.get(_CHAIN_METADATA_KEY, "")
        source_key = request.agent_key or "unknown"
        chain = f"{existing_chain},{source_key}" if existing_chain else source_key

        new_metadata = dict(request.metadata)
        new_metadata[_CHAIN_METADATA_KEY] = chain
        new_metadata[_DEPTH_METADATA_KEY] = str(
            int(request.metadata.get(_DEPTH_METADATA_KEY, "0")) + 1
        )

        return request.model_copy(
            update={
                "agent_key": target_key,
                "user_message": target_message,
                "history": [],
                "trace_id": f"{request.trace_id or uuid4().hex}->{target_key}",
                "metadata": new_metadata,
            }
        )

    @staticmethod
    def _annotate_chain(
        sub_result: AgentTurnResult,
        sub_request: AgentTurnRequest,
        target_key: str,
        resolution: HandoffResolution,
    ) -> AgentTurnResult:
        """Annotate a sub-turn result with orchestration chain metadata."""
        existing_chain = sub_request.metadata.get(_CHAIN_METADATA_KEY, "")
        chain_list = [k for k in existing_chain.split(",") if k] + [target_key]
        return sub_result.model_copy(
            update={
                "responding_agent_key": target_key,
                "orchestration_chain": chain_list,
                "handoff_target": HandoffTarget(
                    target_type="agent",
                    target_agent_key=target_key,
                    reason=resolution.reason,
                ),
            }
        )

    async def _validate_agent_target(self, agent_key: str | None) -> bool:
        """Return True if the target agent is published and available."""
        if not agent_key:
            return False
        if self._loader is None:
            # No loader — assume valid (caller is responsible for correctness)
            return True
        definition = await self._loader.load(agent_key)
        if definition is None:
            return False
        return definition.status == "published"
