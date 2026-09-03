"""Agent loop — self-built execution engine inspired by pi agent-core ``agent-loop.ts``.

This module implements the core agent execution loop with:

- **Dual-layer loop**: outer loop handles follow-up messages, inner loop handles
  tool calls and steering messages (mirrors pi's ``runLoop`` structure).
- **Message queues**: steering (interrupt mid-turn) and follow-up (post-run)
  message injection.
- **Tool execution modes**: parallel or sequential tool execution.
- **Event emission**: typed events via the ``EventBus`` for every lifecycle
  transition (agent/turn/message/tool).
- **Cancellation**: cooperative ``CancelToken`` checked at every await point.

The loop has **zero dependency on pydantic-ai** — it calls ``LlmAdapter``
directly for LLM interactions.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Awaitable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum  # noqa: F401 — used by QueueMode
from typing import Any
from uuid import uuid4

from ..tools.contracts import ToolExecutionMode, ToolExecutionObservers, ToolResult
from ..contracts.models import AgentMessage, AgentRole
from ..errors import AgentError, AgentErrorCode
from ..event_bus import EventBus
from ..events import (
    AgentEndEvent,
    AgentStartEvent,
    AgentEvent,
    MessageEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    TurnEndEvent,
    TurnStartEvent,
)
from ..events_v2 import (
    AgentCompleted,
    AgentStarted,
    AgentTurnStarted,
    AgentTurnCompleted,
    LLMCallStarted,
    LLMCallCompleted,
    LLMCallFailed,
    RunCancelled,
    RunCompleted,
    RunFailed,
    RunStarted,
    RuntimeEvent,
    ToolCallCompleted,
    ToolCallFailed,
    ToolCallStarted,
)
from .cancel import CancelToken
from .llm_adapter import (
    Directive,
    FinalDirective,
    LlmAdapter,
    StreamDelta,
    ToolDirective,
    ToolSchema,
)

logger = logging.getLogger(__name__)

# Type alias for semantic event callbacks
SemanticEventSink = Callable[[RuntimeEvent], Awaitable[None] | None]


@dataclass
class _SpanContext:
    """Manages span identity and parent hierarchy within a single run.

    Runtime is the sole creator of span_id (Phase 3.1).
    parent_span_id is determined by the span stack, not inferred by projector (3.2).
    """

    _stack: list[str] = field(default_factory=list)

    def push(self, span_id: str) -> None:
        """Push a new span onto the stack."""
        self._stack.append(span_id)

    def pop(self) -> str | None:
        """Pop the current span off the stack."""
        return self._stack.pop() if self._stack else None

    @property
    def current_span_id(self) -> str | None:
        """The current (innermost) span."""
        return self._stack[-1] if self._stack else None

    @property
    def parent_span_id(self) -> str | None:
        """The parent of the next span to be created.

        For a stack [run, agent, llm], the parent of the next span is 'llm'.
        For a stack [run, agent], the parent of the next span is 'agent'.
        """
        return self._stack[-1] if self._stack else None


def _make_semantic_emit(
    event_bus: EventBus | None,
    run_id: str,
    trace_id: str,
    span_ctx: _SpanContext | None = None,
    agent_key: str = "",
) -> SemanticEventSink:
    """Create a callback that emits v2 semantic events with run_id/trace_id/span_id filled in.

    If span_ctx is provided, events that have span_id set will use it,
    and parent_span_id will be derived from the span stack.

    If agent_key is provided, LLMCallCompleted and LLMCallFailed events
    will carry it so that CostProjector can attribute costs correctly.
    """

    async def _semantic_emit(event: RuntimeEvent) -> None:
        event.run_id = run_id
        event.trace_id = trace_id
        # If the event already has a span_id (set by caller), derive parent
        if event.span_id is not None and span_ctx is not None and event.parent_span_id is None:
            event.parent_span_id = span_ctx.parent_span_id
        # Propagate agent_key to LLM events for CostProjector
        if agent_key and hasattr(event, "agent_key") and not event.agent_key:
            event.agent_key = agent_key
        if event_bus is not None:
            await event_bus.emit(event)

    return _semantic_emit

# ── Queue types ───────────────────────────────────────────────────────────────


class QueueMode(str, Enum):
    ALL = "all"
    ONE_AT_A_TIME = "one_at_a_time"


class PendingMessageQueue:
    """Queue for steering or follow-up messages — inspired by pi ``PendingMessageQueue``.

    ``mode`` controls how many messages are drained at each queue checkpoint:

    - ``ALL``: drain and return every queued message.
    - ``ONE_AT_A_TIME``: drain and return only the oldest message.
    """

    def __init__(self, mode: QueueMode = QueueMode.ONE_AT_A_TIME) -> None:
        self._messages: list[AgentMessage] = []
        self.mode = mode

    def enqueue(self, message: AgentMessage) -> None:
        self._messages.append(message)

    def has_items(self) -> bool:
        return len(self._messages) > 0

    def drain(self) -> list[AgentMessage]:
        if self.mode == QueueMode.ALL:
            drained = self._messages[:]
            self._messages.clear()
            return drained
        if not self._messages:
            return []
        first = self._messages[0]
        self._messages = self._messages[1:]
        return [first]

    def clear(self) -> None:
        self._messages.clear()


# ── Loop data types ──────────────────────────────────────────────────────────


@dataclass
class LoopContext:
    """Snapshot of conversation context passed into the loop — inspired by pi ``AgentContext``."""

    system_prompt: str
    messages: list[AgentMessage] = field(default_factory=list)
    tools: list[ToolSchema] = field(default_factory=list)


@dataclass
class ToolCallRecord:
    """Record of a tool call within a loop iteration."""

    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    result_text: str
    is_error: bool = False


@dataclass
class LoopConfig:
    """Configuration for the agent loop — inspired by pi ``AgentLoopConfig``."""

    max_tool_rounds: int = 10

    # Queue callbacks
    get_steering_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None
    get_follow_up_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None

    # Turn control
    should_stop_after_turn: Callable[[Any], Awaitable[bool]] | None = None
    prepare_next_turn: Callable[[Any], Awaitable[Any]] | None = None

    # Tool hooks
    before_tool_call: Callable[[str, dict], Awaitable[str | None]] | None = None
    after_tool_call: Callable[[str, dict, str, bool], Awaitable[str | None]] | None = None

    # Tool executor — called by the loop to execute a tool
    tool_executor: Callable[..., Awaitable[ToolResult]] | None = None


@dataclass
class LoopResult:
    """Result of a completed agent loop."""

    messages: list[AgentMessage] = field(default_factory=list)
    final_directive: FinalDirective | None = None
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    usage: Any = None


# ── Event sink type ──────────────────────────────────────────────────────────

EventSink = Callable[[AgentEvent], Awaitable[None] | None]
"""Callback that receives every event emitted by the loop."""


# ── Main loop ────────────────────────────────────────────────────────────────


async def run_agent_loop(
    prompts: list[AgentMessage],
    context: LoopContext,
    config: LoopConfig,
    llm: LlmAdapter,
    event_bus: EventBus | None = None,
    cancel: CancelToken | None = None,
    *,
    run_id: str = "",
    trace_id: str = "",
    agent_key: str = "",
    skip_run_lifecycle: bool = False,
    root_span_id: str | None = None,
) -> LoopResult:
    """Run the agent loop in **blocking** mode.

    This is the Python equivalent of pi's ``runAgentLoop()``.

    Args:
        prompts: Initial user messages to process.
        context: Current conversation context (system prompt + history + tools).
        config: Loop configuration (queues, hooks, tool execution mode).
        llm: LLM adapter for making gateway calls.
        event_bus: Optional event bus for lifecycle events.
        cancel: Optional cancellation token.
        run_id: Optional run ID for semantic v2 events.
        trace_id: Optional trace ID for semantic v2 events.
        agent_key: Agent key for cost attribution.
        skip_run_lifecycle: When True, the caller has already emitted RunStarted
            and will handle terminal events. The loop skips RunStarted emission
            but still emits Agent/Tool/LLM events and terminal events.
        root_span_id: Optional root span ID from ExecutionContext. When provided
            (with skip_run_lifecycle), used instead of generating a new one so
            RunStarted and RunCompleted share the same span_id.

    Returns:
        A :class:`LoopResult` with all produced messages and the final directive.
    """
    async def _emit(event: AgentEvent) -> None:
        if event_bus is not None:
            await event_bus.emit(event)

    span_ctx = _SpanContext()
    _sem = _make_semantic_emit(event_bus, run_id, trace_id, span_ctx, agent_key=agent_key)

    cancel = cancel or CancelToken()
    new_messages: list[AgentMessage] = list(prompts)
    current_messages = list(context.messages) + list(prompts)

    # ── Dual emit: old + v2 ────────────────────────────────────────
    # Create root span for the run (3.1: Runtime creates span_id)
    run_span_id = root_span_id or uuid4().hex[:16]
    span_ctx.push(run_span_id)

    await _emit(AgentStartEvent())
    if not skip_run_lifecycle:
        await _sem(RunStarted(
            input_text=prompts[0].content if prompts else "",
            span_id=run_span_id,
        ))
    agent_span_id = uuid4().hex[:16]
    span_ctx.push(agent_span_id)
    await _sem(AgentStarted(span_id=agent_span_id))
    turn_span_id = uuid4().hex[:16]
    span_ctx.push(turn_span_id)
    await _emit(TurnStartEvent())
    await _sem(AgentTurnStarted(turn_index=0, span_id=turn_span_id))

    for prompt in prompts:
        await _emit(MessageStartEvent(message=prompt))
        await _emit(MessageEndEvent(message=prompt))

    try:
        result = await _run_loop_body(
            current_messages=current_messages,
            new_messages=new_messages,
            context=context,
            config=config,
            llm=llm,
            emit=_emit,
            cancel=cancel,
            semantic_emit=_sem,
            span_ctx=span_ctx,
            agent_key=agent_key,
        )
    except asyncio.CancelledError:
        # ── Cancellation as first-class status (2.5) ──────────────
        # Pop remaining spans
        while span_ctx.current_span_id is not None:
            span_ctx.pop()
        if not skip_run_lifecycle:
            await _sem(RunCancelled(reason="cancelled", span_id=run_span_id))
        raise
    except Exception as exc:
        # ── Run terminal invariant: failure path (2.1) ────────────
        while span_ctx.current_span_id is not None:
            span_ctx.pop()
        if not skip_run_lifecycle:
            await _sem(RunFailed(
                error_code="RUNTIME_ERROR",
                error_message=str(exc),
                span_id=run_span_id,
            ))
        raise
    else:
        # ── Run terminal invariant: success path (2.1) ────────────
        # Pop turn and agent spans
        span_ctx.pop()  # turn
        span_ctx.pop()  # agent
        span_ctx.pop()  # run
        final_text = result.final_directive.reply_text if result.final_directive else ""
        await _emit(AgentEndEvent(messages=result.messages))
        await _sem(AgentTurnCompleted(turn_index=0, output_text=final_text, span_id=turn_span_id))
        await _sem(AgentCompleted(span_id=agent_span_id))
        if not skip_run_lifecycle:
            await _sem(RunCompleted(output_text=final_text, span_id=run_span_id))
        return result


async def stream_agent_loop(
    prompts: list[AgentMessage],
    context: LoopContext,
    config: LoopConfig,
    llm: LlmAdapter,
    event_bus: EventBus | None = None,
    cancel: CancelToken | None = None,
    *,
    run_id: str = "",
    trace_id: str = "",
    agent_key: str = "",
    skip_run_lifecycle: bool = False,
    root_span_id: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """Run the agent loop in **streaming** mode.

    Yields events as they occur. The final event is always
    :class:`AgentEndEvent`.

    This is the Python equivalent of pi's ``agentLoop()`` which returns an
    ``EventStream``.
    """
    span_ctx = _SpanContext()
    _sem = _make_semantic_emit(event_bus, run_id, trace_id, span_ctx, agent_key=agent_key)

    cancel = cancel or CancelToken()
    new_messages: list[AgentMessage] = list(prompts)
    current_messages = list(context.messages) + list(prompts)

    # ── Dual emit: old (yielded) + v2 (event_bus) ──────────────────
    run_span_id = root_span_id or uuid4().hex[:16]
    span_ctx.push(run_span_id)
    yield AgentStartEvent()
    if not skip_run_lifecycle:
        await _sem(RunStarted(input_text=prompts[0].content if prompts else "", span_id=run_span_id))
    agent_span_id = uuid4().hex[:16]
    span_ctx.push(agent_span_id)
    await _sem(AgentStarted(span_id=agent_span_id))
    turn_span_id = uuid4().hex[:16]
    span_ctx.push(turn_span_id)
    yield TurnStartEvent()
    await _sem(AgentTurnStarted(turn_index=0, span_id=turn_span_id))

    for prompt in prompts:
        yield MessageStartEvent(message=prompt)
        yield MessageEndEvent(message=prompt)

    # Collect events from the body and re-yield them
    final_directive: FinalDirective | None = None
    tool_call_records: list[ToolCallRecord] = []

    async def _streaming_emit(event: AgentEvent) -> None:
        pass  # events collected differently for streaming

    # Run the loop body and collect intermediate state
    # For streaming, we need a different approach - yield events as they happen
    # We'll use a queue-based approach

    event_queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()
    result_holder: list[LoopResult] = []

    async def _emit_to_queue(event: AgentEvent) -> None:
        await event_queue.put(event)
        if event_bus is not None:
            await event_bus.emit(event)

    async def _run_body():
        try:
            result = await _run_loop_body(
                current_messages=current_messages,
                new_messages=new_messages,
                context=context,
                config=config,
                llm=llm,
                emit=_emit_to_queue,
                cancel=cancel,
                semantic_emit=_sem,
            )
            result_holder.append(result)
        finally:
            await event_queue.put(None)  # sentinel

    task = asyncio.create_task(_run_body())

    try:
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield event
    except asyncio.CancelledError:
        # ── Cancellation as first-class status (2.5) ──────────────
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        while span_ctx.current_span_id is not None:
            span_ctx.pop()
        await _sem(RunCancelled(reason="stream_cancelled", span_id=run_span_id))
        raise
    except Exception:
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        raise
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    if result_holder:
        result = result_holder[0]
        final_text = result.final_directive.reply_text if result.final_directive else ""
        # Pop turn, agent, run spans
        span_ctx.pop()  # turn
        span_ctx.pop()  # agent
        span_ctx.pop()  # run
        yield AgentEndEvent(messages=result.messages)
        await _sem(AgentTurnCompleted(turn_index=0, output_text=final_text, span_id=turn_span_id))
        await _sem(AgentCompleted(span_id=agent_span_id))
        await _sem(RunCompleted(output_text=final_text, span_id=run_span_id))
    else:
        # Task failed without producing results — emit RunFailed
        while span_ctx.current_span_id is not None:
            span_ctx.pop()
        await _sem(RunFailed(
            error_code="RUNTIME_ERROR",
            error_message="streaming loop exited without result",
            span_id=run_span_id,
        ))


# ── Core loop body ───────────────────────────────────────────────────────────


def _resolve_tool_source_from_tags(tags: list[str]) -> tuple[str | None, str | None]:
    """Determine (source_type, source_ref) from a tool's tag list.

    Mirrors :func:`agent_runtime.tools.registry._resolve_tool_source` but
    operates on the lightweight tag list carried by ``ToolSchema`` so the
    loop does not need the full ToolSpec / registry.
    """
    if "mcp" in tags:
        server_tag = next((t for t in tags if t.startswith("mcp:")), None)
        return "mcp", server_tag.split(":", 1)[1] if server_tag else None
    if "external" in tags:
        return "http_external", None
    return "builtin", None


async def _run_loop_body(
    *,
    current_messages: list[AgentMessage],
    new_messages: list[AgentMessage],
    context: LoopContext,
    config: LoopConfig,
    llm: LlmAdapter,
    emit: EventSink,
    cancel: CancelToken,
    semantic_emit: SemanticEventSink | None = None,
    span_ctx: _SpanContext | None = None,
    agent_key: str = "",
) -> LoopResult:
    """Core loop logic shared by blocking and streaming modes.

    Implements the pi-style dual-layer loop:

    1. **Outer loop**: checks follow-up queue after agent would stop.
    2. **Inner loop**: processes tool calls and steering messages.
    """
    tool_call_records: list[ToolCallRecord] = []
    final_directive: FinalDirective | None = None
    total_usage: Any = None
    first_turn = True
    pending_messages: list[AgentMessage] = []

    # Map tool_name → tags so we can resolve source_type when emitting
    # ToolExecutionStartEvent (needed by the observability layer).
    _tool_tags_lookup: dict[str, list[str]] = {
        t.name: t.tags for t in context.tools if t.tags
    }

    # Check for initial steering messages
    if config.get_steering_messages is not None:
        pending_messages = await config.get_steering_messages()

    # Outer loop: continues when follow-up messages arrive
    while True:
        has_more_tool_calls = True

        # Inner loop: process tool calls and steering messages
        while has_more_tool_calls or pending_messages:
            cancel.check()

            if not first_turn:
                await emit(TurnStartEvent())
            else:
                first_turn = False

            # Inject pending messages (steering)
            if pending_messages:
                for message in pending_messages:
                    await emit(MessageStartEvent(message=message))
                    await emit(MessageEndEvent(message=message))
                    current_messages.append(message)
                    new_messages.append(message)
                pending_messages = []

            cancel.check()

            # Call LLM — dual emit old + v2 (2.3: failure must emit, 3.1: span_id)
            conversation = _messages_to_conversation(current_messages)
            _llm_model = getattr(llm, "_model", "")
            _llm_provider = getattr(llm, "_provider", "")
            # Create span_id for this LLM call (3.1)
            _llm_span_id = uuid4().hex[:16]
            _llm_started_at = datetime.now(timezone.utc)
            if span_ctx is not None:
                span_ctx.push(_llm_span_id)
            if semantic_emit is not None:
                await semantic_emit(LLMCallStarted(
                    model=_llm_model,
                    provider=_llm_provider,
                    span_id=_llm_span_id,
                    agent_key=agent_key,
                ))
            try:
                directive, usage = await llm.generate(
                    system_prompt=context.system_prompt,
                    conversation=conversation,
                    tools=context.tools,
                )
            except Exception as exc:
                if semantic_emit is not None:
                    await semantic_emit(LLMCallFailed(
                        model=_llm_model,
                        provider=_llm_provider,
                        error_code="LLM_ERROR",
                        error_message=str(exc),
                        span_id=_llm_span_id,
                        started_at=_llm_started_at,
                        completed_at=datetime.now(timezone.utc),
                        agent_key=agent_key,
                    ))
                if span_ctx is not None:
                    span_ctx.pop()
                raise
            total_usage = _merge_usage(total_usage, usage)
            _llm_completed_at = datetime.now(timezone.utc)
            if semantic_emit is not None:
                await semantic_emit(LLMCallCompleted(
                    model=_llm_model,
                    provider=_llm_provider,
                    input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
                    output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
                    cache_write_tokens=getattr(usage, "cache_write_tokens", 0) if usage else 0,
                    cache_read_tokens=getattr(usage, "cache_read_tokens", 0) if usage else 0,
                    estimated_cost=float(getattr(usage, "estimated_cost", 0) or 0) if usage else 0.0,
                    span_id=_llm_span_id,
                    started_at=_llm_started_at,
                    completed_at=_llm_completed_at,
                    agent_key=agent_key,
                ))
            if span_ctx is not None:
                span_ctx.pop()

            if isinstance(directive, FinalDirective):
                # No tool calls — emit message events and finish
                assistant_msg = AgentMessage(
                    role=AgentRole.ASSISTANT,
                    content=directive.reply_text,
                )
                await emit(MessageStartEvent(message=assistant_msg))
                await emit(MessageEndEvent(message=assistant_msg, usage=usage))
                current_messages.append(assistant_msg)
                new_messages.append(assistant_msg)
                final_directive = directive

                await emit(TurnEndEvent(message=assistant_msg, tool_results=[]))

                # Check should_stop_after_turn
                if config.should_stop_after_turn is not None:
                    if await config.should_stop_after_turn(directive):
                        break

                # Poll steering
                if config.get_steering_messages is not None:
                    pending_messages = await config.get_steering_messages()
                    if pending_messages:
                        continue

                break  # No more tool calls, exit inner loop

            # Tool directive — execute tool(s) — dual emit old + v2
            if isinstance(directive, ToolDirective):
                tool_call_id = str(uuid4())
                tool_tags = _tool_tags_lookup.get(directive.tool_name, [])
                source_type, source_ref = _resolve_tool_source_from_tags(tool_tags)
                await emit(ToolExecutionStartEvent(
                    tool_call_id=tool_call_id,
                    tool_name=directive.tool_name,
                    args=directive.arguments,
                    source_type=source_type,
                    source_ref=source_ref,
                ))
                # Create span_id for this tool call (3.1)
                _tool_span_id = uuid4().hex[:16]
                if span_ctx is not None:
                    span_ctx.push(_tool_span_id)
                if semantic_emit is not None:
                    await semantic_emit(ToolCallStarted(
                        tool_name=directive.tool_name,
                        arguments=dict(directive.arguments),
                        source_type=source_type,
                        source_ref=source_ref,
                        span_id=_tool_span_id,
                    ))

                # Execute tool (2.4: distinguish business error vs runtime failure)
                import time as _time
                _tool_start = _time.monotonic()
                try:
                    from .retrieval_observer import RuntimeRetrievalObserver
                    observers = ToolExecutionObservers(
                        retrieval=RuntimeRetrievalObserver(semantic_emit, span_ctx)
                    ) if semantic_emit is not None and span_ctx is not None else None
                    tool_result = await _execute_tool(
                        tool_name=directive.tool_name,
                        arguments=directive.arguments,
                        tool_call_id=tool_call_id,
                        config=config,
                        emit=emit,
                        observers=observers,
                    )
                    result_text = tool_result.output
                    is_error = tool_result.status != "success"
                except Exception as exc:
                    # Tool invocation itself failed — emit ToolCallFailed (2.4, 3.1)
                    _tool_duration_ms = int((_time.monotonic() - _tool_start) * 1000)
                    await emit(ToolExecutionEndEvent(
                        tool_call_id=tool_call_id,
                        tool_name=directive.tool_name,
                        result=str(exc),
                        is_error=True,
                    ))
                    if semantic_emit is not None:
                        await semantic_emit(ToolCallFailed(
                            tool_name=directive.tool_name,
                            error_code="TOOL_EXECUTION_ERROR",
                            error_message=str(exc),
                            span_id=_tool_span_id,
                        ))
                    if span_ctx is not None:
                        span_ctx.pop()
                    raise
                _tool_duration_ms = int((_time.monotonic() - _tool_start) * 1000)

                await emit(ToolExecutionEndEvent(
                    tool_call_id=tool_call_id,
                    tool_name=directive.tool_name,
                    result=result_text,
                    is_error=is_error,
                ))
                if semantic_emit is not None:
                    await semantic_emit(ToolCallCompleted(
                        tool_name=directive.tool_name,
                        result=result_text[:500] if result_text else "",
                        duration_ms=_tool_duration_ms,
                        is_error=is_error,
                        span_id=_tool_span_id,
                    ))
                if span_ctx is not None:
                    span_ctx.pop()

                tool_call_records.append(ToolCallRecord(
                    tool_call_id=tool_call_id,
                    tool_name=directive.tool_name,
                    arguments=directive.arguments,
                    result_text=result_text,
                    is_error=is_error,
                ))

                # Add assistant tool-call message + tool result to history
                assistant_tool_msg = AgentMessage(
                    role=AgentRole.ASSISTANT,
                    content=directive.reply_text or "",
                    name=directive.tool_name,
                )
                tool_result_msg = AgentMessage(
                    role=AgentRole.TOOL,
                    content=result_text,
                    name=directive.tool_name,
                )
                current_messages.append(assistant_tool_msg)
                current_messages.append(tool_result_msg)
                new_messages.append(assistant_tool_msg)
                new_messages.append(tool_result_msg)

                has_more_tool_calls = True

                await emit(TurnEndEvent(
                    message=assistant_tool_msg,
                    tool_results=[tool_result_msg],
                ))

                # Check should_stop_after_turn
                if config.should_stop_after_turn is not None:
                    if await config.should_stop_after_turn(directive):
                        break

                # Check prepare_next_turn
                if config.prepare_next_turn is not None:
                    update = await config.prepare_next_turn(directive)
                    # Can update context/tools here in the future

                cancel.check()

                # Poll steering
                if config.get_steering_messages is not None:
                    pending_messages = await config.get_steering_messages()

                continue

        # Agent would stop here. Check for follow-up messages.
        if config.get_follow_up_messages is not None:
            follow_ups = await config.get_follow_up_messages()
            if follow_ups:
                pending_messages = follow_ups
                continue

        break

    return LoopResult(
        messages=new_messages,
        final_directive=final_directive,
        tool_calls=tool_call_records,
        usage=total_usage,
    )


# ── Streaming loop body ──────────────────────────────────────────────────────


async def _run_streaming_loop_body(
    *,
    current_messages: list[AgentMessage],
    new_messages: list[AgentMessage],
    context: LoopContext,
    config: LoopConfig,
    llm: LlmAdapter,
    emit: EventSink,
    cancel: CancelToken,
) -> LoopResult:
    """Streaming variant of the loop body.

    Uses ``LlmAdapter.generate_stream()`` and emits ``MessageUpdateEvent``
    deltas as they arrive.
    """
    tool_call_records: list[ToolCallRecord] = []
    final_directive: FinalDirective | None = None
    total_usage: Any = None
    first_turn = True
    pending_messages: list[AgentMessage] = []

    if config.get_steering_messages is not None:
        pending_messages = await config.get_steering_messages()

    while True:
        has_more_tool_calls = True

        while has_more_tool_calls or pending_messages:
            cancel.check()

            if not first_turn:
                await emit(TurnStartEvent())
            else:
                first_turn = False

            if pending_messages:
                for message in pending_messages:
                    await emit(MessageStartEvent(message=message))
                    await emit(MessageEndEvent(message=message))
                    current_messages.append(message)
                    new_messages.append(message)
                pending_messages = []

            cancel.check()

            # Stream LLM call
            conversation = _messages_to_conversation(current_messages)
            accumulated_text = ""
            completed_text: str | None = None
            stream_usage: Any = None

            # Emit start event so the observability layer can track the LLM call span
            await emit(MessageStartEvent(
                message=AgentMessage(role=AgentRole.ASSISTANT, content=""),
            ))

            async for delta in llm.generate_stream(
                system_prompt=context.system_prompt,
                conversation=conversation,
                tools=context.tools,
            ):
                cancel.check()
                if delta.delta:
                    accumulated_text = delta.full_text
                    await emit(MessageUpdateEvent(delta=delta.delta))
                if delta.is_done:
                    completed_text = delta.full_text
                    stream_usage = delta.usage

            total_usage = _merge_usage(total_usage, stream_usage)
            response_text = completed_text or accumulated_text

            # Parse response
            directive = llm.parse_response(response_text)

            if isinstance(directive, FinalDirective):
                assistant_msg = AgentMessage(
                    role=AgentRole.ASSISTANT,
                    content=directive.reply_text,
                )
                await emit(MessageEndEvent(message=assistant_msg, usage=total_usage))
                current_messages.append(assistant_msg)
                new_messages.append(assistant_msg)
                final_directive = directive

                await emit(TurnEndEvent(message=assistant_msg, tool_results=[]))

                if config.should_stop_after_turn is not None:
                    if await config.should_stop_after_turn(directive):
                        break

                if config.get_steering_messages is not None:
                    pending_messages = await config.get_steering_messages()
                    if pending_messages:
                        continue

                break

            if isinstance(directive, ToolDirective):
                tool_call_id = str(uuid4())
                tool_tags2 = _tool_tags_lookup.get(directive.tool_name, [])
                source_type2, source_ref2 = _resolve_tool_source_from_tags(tool_tags2)
                await emit(ToolExecutionStartEvent(
                    tool_call_id=tool_call_id,
                    tool_name=directive.tool_name,
                    args=directive.arguments,
                    source_type=source_type2,
                    source_ref=source_ref2,
                ))

                tool_result = await _execute_tool(
                    tool_name=directive.tool_name,
                    arguments=directive.arguments,
                    tool_call_id=tool_call_id,
                    config=config,
                    emit=emit,
                )
                result_text = tool_result.output
                is_error = tool_result.status != "success"

                await emit(ToolExecutionEndEvent(
                    tool_call_id=tool_call_id,
                    tool_name=directive.tool_name,
                    result=result_text,
                    is_error=is_error,
                ))

                tool_call_records.append(ToolCallRecord(
                    tool_call_id=tool_call_id,
                    tool_name=directive.tool_name,
                    arguments=directive.arguments,
                    result_text=result_text,
                    is_error=is_error,
                ))

                assistant_tool_msg = AgentMessage(
                    role=AgentRole.ASSISTANT,
                    content=directive.reply_text or "",
                    name=directive.tool_name,
                )
                tool_result_msg = AgentMessage(
                    role=AgentRole.TOOL,
                    content=result_text,
                    name=directive.tool_name,
                )
                current_messages.append(assistant_tool_msg)
                current_messages.append(tool_result_msg)
                new_messages.append(assistant_tool_msg)
                new_messages.append(tool_result_msg)

                has_more_tool_calls = True

                await emit(TurnEndEvent(
                    message=assistant_tool_msg,
                    tool_results=[tool_result_msg],
                ))

                if config.should_stop_after_turn is not None:
                    if await config.should_stop_after_turn(directive):
                        break

                cancel.check()

                if config.get_steering_messages is not None:
                    pending_messages = await config.get_steering_messages()

                continue

        if config.get_follow_up_messages is not None:
            follow_ups = await config.get_follow_up_messages()
            if follow_ups:
                pending_messages = follow_ups
                continue

        break

    return LoopResult(
        messages=new_messages,
        final_directive=final_directive,
        tool_calls=tool_call_records,
        usage=total_usage,
    )


# ── Tool execution ───────────────────────────────────────────────────────────


async def _execute_tool(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    tool_call_id: str,
    config: LoopConfig,
    emit: EventSink,
    observers: ToolExecutionObservers | None = None,
) -> ToolResult:
    """Execute a single tool call.

    Calls ``before_tool_call`` hook, executes via ``config.tool_executor``,
    then calls ``after_tool_call`` hook.

    Returns:
        The canonical typed ``ToolResult``.
    """
    # Before hook
    if config.before_tool_call is not None:
        block_reason = await config.before_tool_call(tool_name, arguments)
        if block_reason is not None:
            return ToolResult(output=block_reason, status="error", error_message=block_reason)

    # Execute
    if config.tool_executor is None:
        return f"Tool '{tool_name}' has no executor configured.", True

    try:
        result = await config.tool_executor(tool_name, arguments, tool_call_id, observers)
    except TypeError:
        # Compatibility for legacy loop callers with the former 3-argument callback.
        result = await config.tool_executor(tool_name, arguments, tool_call_id)

    if not isinstance(result, ToolResult):
        result = ToolResult(output=str(result), status="success")
    result_text = result.output
    is_error = result.status != "success"

    # After hook
    if config.after_tool_call is not None:
        override = await config.after_tool_call(tool_name, arguments, result_text, is_error)
        if override is not None:
            result.output = override
            result_text = override

    return result


# ── Helpers ──────────────────────────────────────────────────────────────────


def _messages_to_conversation(
    messages: Sequence[AgentMessage],
) -> list[tuple[str, str]]:
    """Convert ``AgentMessage`` list to ``(role, content)`` tuples for prompt building."""
    result: list[tuple[str, str]] = []
    for msg in messages:
        role_name = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
        prefix = role_name
        if msg.name:
            prefix = f"{role_name}[{msg.name}]"
        result.append((prefix, msg.content))
    return result


def _merge_usage(left: Any, right: Any) -> Any:
    """Merge two usage info objects."""
    if left is None:
        return right
    if right is None:
        return left
    try:
        from llm_gateway import UsageInfo
        if isinstance(left, UsageInfo) and isinstance(right, UsageInfo):
            return UsageInfo(
                input_tokens=(left.input_tokens or 0) + (right.input_tokens or 0),
                output_tokens=(left.output_tokens or 0) + (right.output_tokens or 0),
                total_tokens=(left.total_tokens or 0) + (right.total_tokens or 0),
                audio_duration_ms=(left.audio_duration_ms or 0) + (right.audio_duration_ms or 0),
            )
    except ImportError:
        pass
    return left


__all__ = [
    "LoopConfig",
    "LoopContext",
    "LoopResult",
    "PendingMessageQueue",
    "QueueMode",
    "ToolCallRecord",
    "ToolExecutionMode",
    "EventSink",
    "run_agent_loop",
    "stream_agent_loop",
]
