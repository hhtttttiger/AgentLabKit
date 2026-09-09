"""Private execution scope and lifecycle owner for Runtime boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..contracts.models import AgentTurnRequest, AgentTurnResult, AgentTurnStreamEvent
from ..contracts.run import AgentRun, ExecutionContext, RunError, RunStatus, RunTarget, RunUsage
from ..event_bus import EventBus
from ..events_v2 import RunCancelled, RunCompleted, RunFailed, RunStarted
from .cancel import CancelToken


@dataclass(slots=True)
class ExecutionScope:
    """Runtime-owned scope passed to internal helpers and child executions."""

    context: ExecutionContext
    cancel: CancelToken
    target: RunTarget
    span_stack: list[str] = field(default_factory=list)

    @property
    def run_id(self) -> str:
        return self.context.run_id

    @property
    def trace_id(self) -> str:
        return self.context.trace_id

    @property
    def current_span_id(self) -> str | None:
        return self.span_stack[-1] if self.span_stack else None

    def child_span(self) -> str:
        span_id = uuid4().hex[:16]
        self.span_stack.append(span_id)
        return span_id

    def pop_span(self) -> str | None:
        return self.span_stack.pop() if self.span_stack else None

    def fork(self, *, target: RunTarget | None = None) -> "ExecutionScope":
        """Fork a branch scope sharing root identity without creating a Run."""
        return ExecutionScope(
            context=self.context,
            cancel=self.cancel,
            target=target or self.target,
            span_stack=list(self.span_stack),
        )


class RunLifecycle:
    """Single owner of start, terminal event, and authoritative AgentRun."""

    def __init__(
        self,
        *,
        context: ExecutionContext,
        request: AgentTurnRequest,
        event_bus: EventBus,
        cancel: CancelToken,
        target: RunTarget,
    ) -> None:
        self.context = context
        self.request = request
        self.event_bus = event_bus
        self.scope = ExecutionScope(context, cancel, target, [context.root_span_id])
        self.run = AgentRun(
            run_id=context.run_id,
            trace_id=context.trace_id,
            user_id=context.user_id,
            input=request.user_message,
            session_id=context.session_id,
            target=target,
            started_at=context.started_at,
            metadata=dict(context.metadata),
        )
        self.started = False
        self.finalized = False

    async def start(self, *, agent_key: str | None = None, agent_version: str | None = None) -> None:
        if self.started:
            return
        self.started = True
        await self.event_bus.emit(RunStarted(
            run_id=self.context.run_id,
            trace_id=self.context.trace_id,
            agent_key=agent_key or self.scope.target.agent_key or "",
            agent_version=agent_version or self.scope.target.agent_version or "",
            input_text=self.request.user_message,
            session_id=self.context.session_id,
            user_id=self.context.user_id,
            span_id=self.context.root_span_id,
        ))

    async def finish(
        self,
        *,
        status: RunStatus,
        result: AgentTurnResult | None = None,
        stream_event: AgentTurnStreamEvent | None = None,
        error: BaseException | None = None,
        reason: str = "",
        output: Any | None = None,
    ) -> AgentRun:
        if self.finalized:
            return self.run
        self.finalized = True
        output = output if output is not None else (result.reply_text if result is not None else (
            stream_event.reply_text if stream_event is not None else ""
        ))
        if status is RunStatus.CANCELLED:
            self.run.mark_cancelled(reason or "run_cancelled")
            await self.event_bus.emit(RunCancelled(
                run_id=self.context.run_id, trace_id=self.context.trace_id,
                span_id=self.context.root_span_id, reason=reason or "run_cancelled",
            ))
        elif status is RunStatus.FAILED:
            message = str(error or "run failed")
            self.run.mark_failed(error_code=type(error).__name__ if error else "RUNTIME_ERROR", error_message=message)
            await self.event_bus.emit(RunFailed(
                run_id=self.context.run_id, trace_id=self.context.trace_id,
                span_id=self.context.root_span_id,
                error_code=type(error).__name__ if error else "RUNTIME_ERROR",
                error_message=message,
            ))
        else:
            usage = None
            raw_usage = result.usage if result is not None else (stream_event.usage if stream_event else None)
            if raw_usage is not None:
                usage = RunUsage(
                    input_tokens=getattr(raw_usage, "input_tokens", 0) or 0,
                    output_tokens=getattr(raw_usage, "output_tokens", 0) or 0,
                    total_tokens=getattr(raw_usage, "total_tokens", 0) or 0,
                )
            self.run.mark_completed(output=output, usage=usage)
            await self.event_bus.emit(RunCompleted(
                run_id=self.context.run_id, trace_id=self.context.trace_id,
                span_id=self.context.root_span_id, output_text=output or "",
            ))
        return self.run
