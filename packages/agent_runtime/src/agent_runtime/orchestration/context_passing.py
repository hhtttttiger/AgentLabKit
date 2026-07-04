"""Cross-agent context passing strategies.

Two implementations are provided:

:class:`DirectContextPasser`
    Passes the most recent N messages verbatim — low latency, no LLM call.
    Suitable for delegation (sub-agent call) where the full context is short.

:class:`SummarizingContextPasser`
    Uses :class:`~agent_runtime.memory.GatewaySummarizer` to compress the
    conversation into a short paragraph before passing it to the target agent.
    Suitable for handoff where the history may be long.

Both implement the :class:`ContextPasser` Protocol so callers can swap them.
"""

from __future__ import annotations

from textwrap import dedent
from typing import Protocol, runtime_checkable

from ..contracts.models import AgentMessage, AgentRole
from .contracts import AgentHandoffContext


@runtime_checkable
class ContextPasser(Protocol):
    """Protocol for strategies that prepare context for a target agent."""

    async def prepare_context(
        self,
        source_agent_key: str,
        target_agent_key: str,
        history: list[AgentMessage],
        handoff_reason: str | None,
        *,
        customer_id: str | None = None,
        locale: str | None = None,
    ) -> AgentHandoffContext:
        """Prepare a context bundle for the target agent.

        Args:
            source_agent_key: The agent initiating the handoff/delegation.
            target_agent_key: The agent that will receive the context.
            history: Full conversation history from the source agent's session.
            handoff_reason: Free-text reason provided by the LLM.
            customer_id: Forwarded for audit and personalisation.
            locale: Forwarded for localisation.

        Returns:
            An :class:`~contracts.AgentHandoffContext` ready for injection.
        """
        ...


# ---------------------------------------------------------------------------
# DirectContextPasser — verbatim last-N messages
# ---------------------------------------------------------------------------


class DirectContextPasser:
    """Pass the most recent ``max_messages`` turns verbatim.

    No LLM call — minimal latency.  Best for delegation where histories are
    short and the sub-agent needs precise details rather than a summary.
    """

    def __init__(self, max_messages: int = 10) -> None:
        if max_messages < 1:
            raise ValueError("max_messages must be ≥ 1")
        self.max_messages = max_messages

    async def prepare_context(
        self,
        source_agent_key: str,
        target_agent_key: str,
        history: list[AgentMessage],
        handoff_reason: str | None,
        *,
        customer_id: str | None = None,
        locale: str | None = None,
    ) -> AgentHandoffContext:
        recent = history[-self.max_messages :]
        summary = _render_messages(recent) if recent else None
        key_facts = _extract_key_facts(recent)
        return AgentHandoffContext(
            summary=summary,
            key_facts=key_facts,
            source_agent_key=source_agent_key,
            handoff_reason=handoff_reason,
            original_customer_id=customer_id,
            original_locale=locale,
            turn_count=len(history),
        )


# ---------------------------------------------------------------------------
# SummarizingContextPasser — LLM-generated summary
# ---------------------------------------------------------------------------


class SummarizingContextPasser:
    """Compress the conversation with an LLM before handing off.

    Reuses :class:`~agent_runtime.memory.GatewaySummarizer`.  Falls back to
    :class:`DirectContextPasser` when the history is very short (no point
    calling an LLM to "summarise" one or two messages).
    """

    HANDOFF_CONTEXT_HINT = dedent("""\
        You are summarizing a conversation for a specialist agent who will take over.
        Focus on: the customer's problem, any decisions made, and pending actions.
        Keep the summary under 200 words and use plain prose.
        Reason for handoff: {reason}
    """).strip()

    _SHORT_HISTORY_THRESHOLD = 3  # Use DirectContextPasser below this

    def __init__(self, summarizer: object, *, max_messages_direct: int = 3) -> None:
        """
        Args:
            summarizer: An object with ``async summarize(messages, context_hint) -> str``.
                        Typically :class:`~agent_runtime.memory.GatewaySummarizer`.
            max_messages_direct: When history length ≤ this value, skip LLM
                                 summarisation and use direct passing instead.
        """
        self._summarizer = summarizer
        self._fallback = DirectContextPasser(max_messages=max_messages_direct)
        self._threshold = max(1, max_messages_direct)

    async def prepare_context(
        self,
        source_agent_key: str,
        target_agent_key: str,
        history: list[AgentMessage],
        handoff_reason: str | None,
        *,
        customer_id: str | None = None,
        locale: str | None = None,
    ) -> AgentHandoffContext:
        if len(history) <= self._threshold:
            return await self._fallback.prepare_context(
                source_agent_key,
                target_agent_key,
                history,
                handoff_reason,
                customer_id=customer_id,
                locale=locale,
            )

        context_hint = self.HANDOFF_CONTEXT_HINT.format(reason=handoff_reason or "not specified")
        summary = await self._summarizer.summarize(history, context_hint=context_hint)
        key_facts = _extract_key_facts(history[-5:])

        return AgentHandoffContext(
            summary=summary or None,
            key_facts=key_facts,
            source_agent_key=source_agent_key,
            handoff_reason=handoff_reason,
            original_customer_id=customer_id,
            original_locale=locale,
            turn_count=len(history),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_messages(messages: list[AgentMessage]) -> str:
    lines: list[str] = []
    for msg in messages:
        if msg.role in (AgentRole.SYSTEM,):
            continue
        role_label = msg.role.value.capitalize()
        lines.append(f"[{role_label}] {msg.content}")
    return "\n".join(lines) if lines else ""


def _extract_key_facts(messages: list[AgentMessage]) -> list[str]:
    """Extract brief key-fact snippets from the tail of the history.

    This is intentionally simple — a heuristic to give the target agent a
    quick reference list alongside the summary.
    """
    facts: list[str] = []
    for msg in messages:
        if msg.role == AgentRole.USER and msg.content:
            snippet = msg.content[:120].strip()
            if snippet:
                facts.append(f"User said: {snippet}")
    return facts
