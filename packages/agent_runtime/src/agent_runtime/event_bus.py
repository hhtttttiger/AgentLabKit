"""Event bus for agent lifecycle events — inspired by pi agent-core subscribe().

The bus allows multiple listeners to subscribe to all agent events. Listeners
are awaited in subscription order. A listener that throws does not prevent
subsequent listeners from receiving the event (errors are logged, not re-raised).
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from .events import AgentEvent

logger = logging.getLogger(__name__)

EventListener = Callable[[AgentEvent], Awaitable[None] | None]
"""Callback signature for event subscribers.

Can be sync or async. The bus ``await``s the return value when it is a coroutine.
"""


class EventBus:
    """Pub/sub hub for :class:`AgentEvent` instances.

    Usage::

        bus = EventBus()

        def on_event(event: AgentEvent) -> None:
            print(event.type)

        unsub = bus.subscribe(on_event)
        await bus.emit(AgentStartEvent())
        unsub()  # remove listener
    """

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []

    # ── Public API ────────────────────────────────────────────────────────

    def subscribe(self, listener: EventListener) -> Callable[[], None]:
        """Register *listener* and return an unsubscribe callable."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    async def emit(self, event: AgentEvent) -> None:
        """Emit *event* to all registered listeners in order.

        If a listener raises, the error is logged and the remaining listeners
        still receive the event.
        """
        for listener in list(self._listeners):
            try:
                result = listener(event)
                if result is not None:
                    await result
            except Exception:
                logger.exception(
                    "event_bus.listener_error event_type=%s",
                    getattr(event, "type", "unknown"),
                )

    # ── Introspection ─────────────────────────────────────────────────────

    @property
    def listener_count(self) -> int:
        return len(self._listeners)

    def clear(self) -> None:
        self._listeners.clear()


__all__ = ["EventBus", "EventListener"]
