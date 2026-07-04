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
from enum import Enum  # noqa: F401 — used by QueueMode
from typing import Any
from uuid import uuid4

from ..tools.contracts import ToolExecutionMode
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
    tool_executor: Callable[
        [str, dict[str, Any], str],  # (tool_name, arguments, tool_call_id)
        Awaitable[tuple[str, bool]],  # (result_text, is_error)
    ] | None = None


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

    Returns:
        A :class:`LoopResult` with all produced messages and the final directive.
    """
    async def _emit(event: AgentEvent) -> None:
        if event_bus is not None:
            await event_bus.emit(event)

    cancel = cancel or CancelToken()
    new_messages: list[AgentMessage] = list(prompts)
    current_messages = list(context.messages) + list(prompts)

    await _emit(AgentStartEvent())
    await _emit(TurnStartEvent())

    for prompt in prompts:
        await _emit(MessageStartEvent(message=prompt))
        await _emit(MessageEndEvent(message=prompt))

    result = await _run_loop_body(
        current_messages=current_messages,
        new_messages=new_messages,
        context=context,
        config=config,
        llm=llm,
        emit=_emit,
        cancel=cancel,
    )

    await _emit(AgentEndEvent(messages=result.messages))
    return result


async def stream_agent_loop(
    prompts: list[AgentMessage],
    context: LoopContext,
    config: LoopConfig,
    llm: LlmAdapter,
    event_bus: EventBus | None = None,
    cancel: CancelToken | None = None,
) -> AsyncIterator[AgentEvent]:
    """Run the agent loop in **streaming** mode.

    Yields events as they occur. The final event is always
    :class:`AgentEndEvent`.

    This is the Python equivalent of pi's ``agentLoop()`` which returns an
    ``EventStream``.
    """
    cancel = cancel or CancelToken()
    new_messages: list[AgentMessage] = list(prompts)
    current_messages = list(context.messages) + list(prompts)

    yield AgentStartEvent()
    yield TurnStartEvent()

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
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    if result_holder:
        result = result_holder[0]
        yield AgentEndEvent(messages=result.messages)


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
    # ToolExecutionStartEvent (needed by SpanBuilder for observability).
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

            # Call LLM
            conversation = _messages_to_conversation(current_messages)
            directive, usage = await llm.generate(
                system_prompt=context.system_prompt,
                conversation=conversation,
                tools=context.tools,
            )
            total_usage = _merge_usage(total_usage, usage)

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

            # Tool directive — execute tool(s)
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

                # Execute tool
                result_text, is_error = await _execute_tool(
                    tool_name=directive.tool_name,
                    arguments=directive.arguments,
                    tool_call_id=tool_call_id,
                    config=config,
                    emit=emit,
                )

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

            # Emit start event so SpanBuilder can track the LLM call span
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

                result_text, is_error = await _execute_tool(
                    tool_name=directive.tool_name,
                    arguments=directive.arguments,
                    tool_call_id=tool_call_id,
                    config=config,
                    emit=emit,
                )

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
) -> tuple[str, bool]:
    """Execute a single tool call.

    Calls ``before_tool_call`` hook, executes via ``config.tool_executor``,
    then calls ``after_tool_call`` hook.

    Returns:
        ``(result_text, is_error)`` tuple.
    """
    # Before hook
    if config.before_tool_call is not None:
        block_reason = await config.before_tool_call(tool_name, arguments)
        if block_reason is not None:
            return block_reason, True

    # Execute
    if config.tool_executor is None:
        return f"Tool '{tool_name}' has no executor configured.", True

    result_text, is_error = await config.tool_executor(tool_name, arguments, tool_call_id)

    # After hook
    if config.after_tool_call is not None:
        override = await config.after_tool_call(tool_name, arguments, result_text, is_error)
        if override is not None:
            result_text = override

    return result_text, is_error


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
