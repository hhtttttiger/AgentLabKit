"""DelegateToAgentTool — built-in tool that delegates a sub-task to another agent.

From the LLM's perspective this is just another function-calling tool.  The
executor behind it is :class:`~sub_agent_executor.SubAgentExecutor`, which
runs the target agent and returns the result as a tool output string.

Registration example::

    executor = SubAgentExecutor(runner=runtime, definition_loader=loader)
    delegate_tool = DelegateToAgentTool(executor, allowed_agents=["data-analyst"])

    registry = DynamicToolRegistry()
    registry.register(delegate_tool.spec, delegate_tool)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator

from ..contracts.models import AgentAction, AgentTurnStreamEvent
from ..tools.contracts import ToolExecutionContext, ToolResult, ToolSpec
from .contracts import SubAgentContext, _CHAIN_METADATA_KEY, _DEPTH_METADATA_KEY
from .sub_agent_executor import SubAgentExecutor

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_BASE_DESCRIPTION = (
    "Delegate a sub-task to a specialist agent and get the result back. "
    "Use this only when a specialist agent is clearly better suited to answer. "
    "Do not delegate if you can answer directly."
)


def _build_spec(allowed_agents: list[str] | None) -> ToolSpec:
    """Build ToolSpec, optionally restricting the agent_key enum."""
    agent_key_schema: dict[str, Any] = {"type": "string"}
    description = _BASE_DESCRIPTION
    if allowed_agents:
        agent_key_schema["enum"] = allowed_agents
        description = (
            f"{_BASE_DESCRIPTION} "
            f"Available agents: {', '.join(allowed_agents)}."
        )

    return ToolSpec(
        name="delegate_to_agent",
        description=description,
        parameters_schema={
            "type": "object",
            "properties": {
                "agent_key": {
                    **agent_key_schema,
                    "description": "Identifier of the target specialist agent.",
                },
                "task_message": {
                    "type": "string",
                    "description": "The sub-task or question to send to the agent.",
                    "minLength": 1,
                },
                "context": {
                    "type": "string",
                    "description": (
                        "Optional background context relevant to the sub-task "
                        "(e.g. customer intent, previous decisions)."
                    ),
                },
            },
            "required": ["agent_key", "task_message"],
            "additionalProperties": False,
        },
        returns_description="The specialist agent's reply text.",
        tags=frozenset({"orchestration", "delegation"}),
        timeout_seconds=60.0,   # sub-agent turns can be slow
        max_retries=0,
        is_idempotent=False,    # agent turns may have side effects
    )


class DelegateToAgentTool:
    """Built-in tool handler that wraps :class:`SubAgentExecutor`.

    Args:
        executor: The :class:`SubAgentExecutor` used to run the sub-agent turn.
        allowed_agents: When provided, restricts the ``agent_key`` parameter
            to the listed values (injected into the JSON Schema as ``enum``).
    """

    def __init__(
        self,
        executor: SubAgentExecutor,
        *,
        allowed_agents: list[str] | None = None,
    ) -> None:
        self._executor = executor
        self.spec: ToolSpec = _build_spec(allowed_agents)

    @property
    def can_stream(self) -> bool:
        """``True`` when the underlying executor supports streaming delegation."""
        return self._executor.can_stream

    @staticmethod
    def build_stream_result(event: AgentTurnStreamEvent | None) -> ToolResult:
        """Normalize a terminal streaming event into the public tool contract."""
        if event is None:
            return ToolResult(
                output="",
                status="error",
                error_message="Streaming delegation ended without a terminal event.",
            )

        if event.event_type == "handoff":
            handoff_info = (
                event.handoff_target.reason
                if event.handoff_target is not None
                else event.handoff_reason or "unspecified"
            )
            return ToolResult(
                output=f"[Sub-agent requested human handoff: {handoff_info}]",
                status="success",
                delegation_usage=event.usage,
            )

        return ToolResult(
            output=event.reply_text or "",
            status="success",
            delegation_usage=event.usage,
        )

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolResult:
        agent_key: str = str(arguments.get("agent_key", "")).strip()
        task_message: str = str(arguments.get("task_message", "")).strip()
        ctx_summary: str | None = arguments.get("context") or None

        if not agent_key:
            return ToolResult(
                output="Error: 'agent_key' is required.",
                status="error",
                error_message="Missing agent_key",
            )
        if not task_message:
            return ToolResult(
                output="Error: 'task_message' is required.",
                status="error",
                error_message="Missing task_message",
            )

        current_depth = int(context.metadata.get(_DEPTH_METADATA_KEY, "0"))
        current_chain = context.metadata.get(_CHAIN_METADATA_KEY, "")

        parent_context = SubAgentContext(
            parent_agent_key=context.agent_key or "unknown",
            parent_session_id=context.session_id,
            parent_trace_id=context.trace_id,
            depth=current_depth,
            summary=ctx_summary,
            shared_metadata={
                _CHAIN_METADATA_KEY: current_chain,
                _DEPTH_METADATA_KEY: str(current_depth),
            },
        )

        result = await self._executor.run_sub_turn(
            agent_key=agent_key,
            user_message=task_message,
            parent_context=parent_context,
        )

        # If the sub-agent requested a human handoff, surface it clearly
        if result.action in (AgentAction.HANDOFF, AgentAction.HANDOFF_HUMAN):
            handoff_info = (
                result.handoff_target.reason
                if result.handoff_target
                else "unspecified"
            )
            return ToolResult(
                output=f"[Sub-agent requested human handoff: {handoff_info}]",
                status="success",
                delegation_usage=result.usage,
            )

        if result.error_message:
            return ToolResult(
                output=result.reply_text,
                status="error",
                error_message=result.error_message,
            )

        return ToolResult(
            output=result.reply_text,
            status="success",
            delegation_usage=result.usage,
        )

    async def execute_stream(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> AsyncIterator[AgentTurnStreamEvent]:
        """Stream sub-agent execution, yielding :class:`AgentTurnStreamEvent` objects.

        Uses :meth:`SubAgentExecutor.stream_sub_turn` when
        :attr:`can_stream` is ``True``; otherwise falls back to
        non-streaming :meth:`execute`.

        Callers should forward ``reply_delta`` events to the user as
        ``delegation_delta`` events and extract the tool result from the final
        ``reply_completed`` or ``handoff`` event.
        """
        agent_key: str = str(arguments.get("agent_key", "")).strip()
        task_message: str = str(arguments.get("task_message", "")).strip()
        ctx_summary: str | None = arguments.get("context") or None

        if not agent_key or not task_message:
            # Emit a single error event instead of raising
            yield AgentTurnStreamEvent(
                event_type="reply_completed",
                session_id=context.session_id,
                trace_id=context.trace_id,
                reply_text=(
                    "Error: 'agent_key' is required."
                    if not agent_key
                    else "Error: 'task_message' is required."
                ),
            )
            return

        current_depth = int(context.metadata.get(_DEPTH_METADATA_KEY, "0"))
        current_chain = context.metadata.get(_CHAIN_METADATA_KEY, "")

        parent_context = SubAgentContext(
            parent_agent_key=context.agent_key or "unknown",
            parent_session_id=context.session_id,
            parent_trace_id=context.trace_id,
            depth=current_depth,
            summary=ctx_summary,
            shared_metadata={
                _CHAIN_METADATA_KEY: current_chain,
                _DEPTH_METADATA_KEY: str(current_depth),
            },
        )

        async for event in self._executor.stream_sub_turn(
            agent_key=agent_key,
            user_message=task_message,
            parent_context=parent_context,
        ):
            yield event
