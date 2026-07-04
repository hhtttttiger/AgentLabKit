"""Tool execution within the agent turn — tool call dispatch, delegation, guard integration.

Extracted from ``engine.py`` to isolate tool execution logic.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import logging
from typing import TYPE_CHECKING

from ..contracts.models import AgentTurnStreamEvent, ToolExecutionRecord
from ..errors import AgentError, AgentErrorCode
from ..tools.contracts import ToolResult

if TYPE_CHECKING:
    from ..config import AgentSettings
    from ..contracts.models import AgentTurnRequest
    from ..orchestration import DelegateToAgentTool
    from ..tools import ToolBinding, ToolRegistry
    from .engine import AgentRunDeps

logger = logging.getLogger(__name__)


class ToolExecution:
    """Stateless helper for tool execution during turns — methods extracted from ``AgentRuntime``."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    async def execute_tool_call(
        self,
        *,
        request: AgentTurnRequest,
        settings: AgentSettings,
        deps: AgentRunDeps,
        tool_name: str,
        arguments: dict[str, object],
        allowed_tool_names: frozenset[str] | None,
        tool_bindings: list[ToolBinding] | None,
        guards_pipeline=None,
    ) -> str:
        """Execute a single tool call with guard checks."""
        self._ensure_tool_allowed(tool_name, allowed_tool_names)
        guarded_arguments, blocked_output = await self._run_tool_guards(
            request=request,
            deps=deps,
            tool_name=tool_name,
            arguments=arguments,
            guards_pipeline=guards_pipeline,
        )
        if blocked_output is not None:
            return blocked_output

        invoke = self.tool_registry.invoke_tool(
            tool_name=tool_name,
            arguments=guarded_arguments,
            settings=settings,
            deps=deps,
            allowed_tool_names=allowed_tool_names,
            tool_bindings=tool_bindings,
        )

        # Voice timeout support
        from ..channels.voice import voice_tool_timeout_seconds, voice_tool_fallback_output

        voice_timeout = voice_tool_timeout_seconds(request)
        try:
            if voice_timeout is None:
                return await invoke
            return await asyncio.wait_for(invoke, timeout=voice_timeout)
        except (TimeoutError, ValueError) as exc:
            if voice_timeout is None:
                raise
            result = ToolResult(
                output="",
                status="timeout" if isinstance(exc, TimeoutError) else "error",
                error_message=str(exc),
            )
            self.tool_registry.record_tool_result(
                deps=deps,
                tool_name=tool_name,
                arguments=guarded_arguments,
                result=result,
            )
            logger.warning(
                "agent_runtime.voice_tool_degraded session_id=%s trace_id=%s tool=%s error=%s",
                request.session_id,
                request.trace_id,
                tool_name,
                exc,
            )
            return voice_tool_fallback_output(tool_name, exc)

    async def execute_streaming_delegate_tool_call(
        self,
        *,
        request: AgentTurnRequest,
        settings: AgentSettings,
        deps: AgentRunDeps,
        delegate_handler: DelegateToAgentTool,
        arguments: dict[str, object],
        allowed_tool_names: frozenset[str] | None,
        tool_bindings: list[ToolBinding] | None,
        guards_pipeline=None,
    ) -> AsyncIterator[AgentTurnStreamEvent]:
        """Execute a streaming delegate tool call, forwarding sub-agent deltas."""
        tool_name = delegate_handler.spec.name
        self._ensure_tool_allowed(tool_name, allowed_tool_names)

        guarded_arguments, blocked_output = await self._run_tool_guards(
            request=request,
            deps=deps,
            tool_name=tool_name,
            arguments=arguments,
            guards_pipeline=guards_pipeline,
        )
        if blocked_output is not None:
            yield AgentTurnStreamEvent(
                event_type="reply_completed",
                session_id=request.session_id,
                trace_id=request.trace_id or "",
                reply_text=blocked_output,
            )
            return

        prepared = self.tool_registry.prepare_tool_execution(
            tool_name=tool_name,
            arguments=guarded_arguments,
            settings=settings,
            allowed_tool_names=allowed_tool_names,
            tool_bindings=tool_bindings,
        )
        if isinstance(prepared, ToolResult):
            self.tool_registry.record_tool_result(
                deps=deps,
                tool_name=tool_name,
                arguments=guarded_arguments,
                result=prepared,
            )
            self.tool_registry.unwrap_tool_result(tool_name, prepared)
            return

        terminal_event: AgentTurnStreamEvent | None = None
        try:
            async with asyncio.timeout(prepared.spec.timeout_seconds):
                async for sub_event in delegate_handler.execute_stream(
                    guarded_arguments,
                    self.tool_registry.build_execution_context(deps),
                ):
                    if sub_event.event_type == "reply_delta":
                        yield AgentTurnStreamEvent(
                            event_type="delegation_delta",
                            session_id=request.session_id,
                            trace_id=request.trace_id or "",
                            delta=sub_event.delta,
                            delegation_agent_key=str(
                                guarded_arguments.get("agent_key", "")
                            ),
                        )
                        continue
                    if sub_event.event_type in ("reply_completed", "handoff"):
                        terminal_event = sub_event
        except TimeoutError:
            result = ToolResult(
                output="",
                status="timeout",
                error_message=f"Tool '{tool_name}' timed out after {prepared.spec.timeout_seconds}s",
            )
        except Exception as exc:
            result = ToolResult(
                output="",
                status="error",
                error_message=str(exc),
            )
        else:
            result = delegate_handler.build_stream_result(terminal_event)

        self.tool_registry.record_tool_result(
            deps=deps,
            tool_name=tool_name,
            arguments=guarded_arguments,
            result=result,
        )
        tool_output = self.tool_registry.unwrap_tool_result(tool_name, result)
        yield AgentTurnStreamEvent(
            event_type="reply_completed",
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            reply_text=tool_output,
        )

    def build_tool_started_event(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ) -> ToolExecutionRecord:
        """Build a tool execution started event record."""
        from ..tools.registry import _resolve_tool_source, _default_display_name

        spec = self.tool_registry.dynamic_registry.get_spec(tool_name)
        source_type, source_ref = _resolve_tool_source(spec) if spec is not None else ("builtin", None)
        tags = sorted(spec.tags) if spec is not None else []
        return ToolExecutionRecord(
            tool_name=tool_name,
            status="started",
            arguments=dict(arguments),
            display_name=_default_display_name(tool_name),
            source_type=source_type,
            source_ref=source_ref,
            tags=tags,
        )

    async def _run_tool_guards(
        self,
        *,
        request: AgentTurnRequest,
        deps: AgentRunDeps,
        tool_name: str,
        arguments: dict[str, object],
        guards_pipeline=None,
    ) -> tuple[dict[str, object], str | None]:
        guarded_arguments = dict(arguments)
        pipeline = guards_pipeline
        if pipeline is None:
            return guarded_arguments, None

        tool_guard_result = await pipeline.run_tool_guards(
            tool_name=tool_name,
            tool_arguments=guarded_arguments,
            session_id=request.session_id,
            trace_id=request.trace_id or "",
            metadata=dict(request.metadata),
        )
        if tool_guard_result.final_verdict is not None and tool_guard_result.final_verdict.value == "block":
            blocked_reason = tool_guard_result.block_reason or "tool_blocked"
            started = self.build_tool_started_event(tool_name, guarded_arguments)
            deps.tool_events.append(
                ToolExecutionRecord(
                    tool_name=tool_name,
                    status="blocked",
                    arguments=guarded_arguments,
                    error_message=blocked_reason,
                    output_text=pipeline.block_response,
                    display_name=started.display_name,
                    source_type=started.source_type,
                    source_ref=started.source_ref,
                    tags=list(started.tags),
                )
            )
            return guarded_arguments, pipeline.block_response
        return guarded_arguments, None

    @staticmethod
    def _ensure_tool_allowed(
        tool_name: str,
        allowed_tool_names: frozenset[str] | None,
    ) -> None:
        if allowed_tool_names is None or tool_name in allowed_tool_names:
            return
        raise AgentError(
            AgentErrorCode.INVALID_REQUEST,
            f"Tool '{tool_name}' is not enabled for this agent definition.",
        )


__all__ = ["ToolExecution"]
