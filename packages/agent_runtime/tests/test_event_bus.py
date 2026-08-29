"""EventBus 核心测试 — Phase 0 安全网。

覆盖：subscribe/unsubscribe、emit 顺序、error isolation、sync+async listener、clear。
"""
from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock

import pytest

from agent_runtime.event_bus import EventBus
from agent_runtime.events import (
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionEndEvent,
)


# ── subscribe / unsubscribe ─────────────────────────────────────────


class TestSubscribeUnsubscribe:
    def test_subscribe_returns_unsub_callable(self) -> None:
        bus = EventBus()
        unsub = bus.subscribe(lambda e: None)
        assert callable(unsub)
        assert bus.listener_count == 1

    def test_unsub_removes_listener(self) -> None:
        bus = EventBus()
        unsub = bus.subscribe(lambda e: None)
        unsub()
        assert bus.listener_count == 0

    def test_unsub_is_idempotent(self) -> None:
        bus = EventBus()
        unsub = bus.subscribe(lambda e: None)
        unsub()
        unsub()  # 第二次不应报错
        assert bus.listener_count == 0

    def test_multiple_listeners(self) -> None:
        bus = EventBus()
        unsub_a = bus.subscribe(lambda e: None)
        unsub_b = bus.subscribe(lambda e: None)
        assert bus.listener_count == 2
        unsub_a()
        assert bus.listener_count == 1
        unsub_b()
        assert bus.listener_count == 0


# ── emit ────────────────────────────────────────────────────────────


class TestEmit:
    @pytest.mark.asyncio
    async def test_sync_listener_receives_event(self) -> None:
        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))

        event = AgentStartEvent()
        await bus.emit(event)

        assert len(received) == 1
        assert received[0] is event

    @pytest.mark.asyncio
    async def test_async_listener_receives_event(self) -> None:
        bus = EventBus()
        received = []

        async def listener(e):
            received.append(e)

        bus.subscribe(listener)
        await bus.emit(TurnStartEvent())

        assert len(received) == 1
        assert isinstance(received[0], TurnStartEvent)

    @pytest.mark.asyncio
    async def test_emit_preserves_order(self) -> None:
        bus = EventBus()
        order = []
        bus.subscribe(lambda e: order.append("first"))
        bus.subscribe(lambda e: order.append("second"))
        bus.subscribe(lambda e: order.append("third"))

        await bus.emit(AgentStartEvent())
        assert order == ["first", "second", "third"]

    @pytest.mark.asyncio
    async def test_emit_to_empty_bus(self) -> None:
        bus = EventBus()
        # 不应报错
        await bus.emit(AgentStartEvent())

    @pytest.mark.asyncio
    async def test_multiple_emits(self) -> None:
        bus = EventBus()
        count = 0

        def counter(e):
            nonlocal count
            count += 1

        bus.subscribe(counter)
        await bus.emit(AgentStartEvent())
        await bus.emit(TurnStartEvent())
        await bus.emit(TurnEndEvent())

        assert count == 3


# ── error isolation ─────────────────────────────────────────────────


class TestErrorIsolation:
    @pytest.mark.asyncio
    async def test_sync_listener_error_does_not_block_others(self) -> None:
        bus = EventBus()
        received = []

        def bad_listener(e):
            raise RuntimeError("boom")

        bus.subscribe(bad_listener)
        bus.subscribe(lambda e: received.append(e))

        await bus.emit(AgentStartEvent())
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_async_listener_error_does_not_block_others(self) -> None:
        bus = EventBus()
        received = []

        async def bad_listener(e):
            raise ValueError("async boom")

        bus.subscribe(bad_listener)

        async def good_listener(e):
            received.append(e)

        bus.subscribe(good_listener)

        await bus.emit(TurnStartEvent())
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_error_in_first_still_delivers_to_rest(self) -> None:
        bus = EventBus()
        order = []

        def first(e):
            order.append("first")
            raise RuntimeError("fail")

        def second(e):
            order.append("second")

        bus.subscribe(first)
        bus.subscribe(second)

        await bus.emit(AgentStartEvent())
        assert order == ["first", "second"]


# ── clear ───────────────────────────────────────────────────────────


class TestClear:
    def test_clear_removes_all(self) -> None:
        bus = EventBus()
        bus.subscribe(lambda e: None)
        bus.subscribe(lambda e: None)
        bus.subscribe(lambda e: None)
        bus.clear()
        assert bus.listener_count == 0

    @pytest.mark.asyncio
    async def test_clear_then_emit_is_noop(self) -> None:
        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))
        bus.clear()
        await bus.emit(AgentStartEvent())
        assert len(received) == 0


# ── event type coverage ────────────────────────────────────────────


class TestEventTypeCoverage:
    """确保所有事件类型都能正确通过 EventBus 传递。"""

    @pytest.mark.asyncio
    async def test_all_event_types(self) -> None:
        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))

        events = [
            AgentStartEvent(),
            AgentEndEvent(),
            TurnStartEvent(),
            TurnEndEvent(),
            ToolExecutionStartEvent(tool_name="search"),
            ToolExecutionEndEvent(tool_name="search", result="ok"),
        ]

        for event in events:
            await bus.emit(event)

        assert len(received) == len(events)
        for original, captured in zip(events, received):
            assert original is captured
