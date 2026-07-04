"""集成模块 — 将 SpanBuilder 桥接到 agent_runtime 的 EventBus。

提供 ``create_span_bridge`` 工厂函数，返回一个可订阅 EventBus 的 listener。
在 run_turn 开始时调用，结束时 finalize 并写入 TraceStore。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..span_builder import SpanBuilder
from ..trace_store import TraceStore

logger = logging.getLogger(__name__)


class SpanBridge:
    """桥接 EventBus → SpanBuilder → TraceStore。"""

    def __init__(
        self,
        trace_store: TraceStore,
        trace_id: str,
        agent_key: str | None = None,
        session_id: str | None = None,
        max_spans: int = 500,
    ) -> None:
        self._builder = SpanBuilder(
            trace_id=trace_id,
            agent_key=agent_key,
            session_id=session_id,
            max_spans=max_spans,
        )
        self._trace_store = trace_store
        self._unsub: Callable[[], None] | None = None

    def on_event(self, event: Any) -> None:
        self._builder.on_event(event)

    def set_error(self, error_message: str) -> None:
        self._builder.set_error(error_message)

    async def finalize(self) -> None:
        trace, spans = self._builder.finalize()
        logger.info("SpanBridge.finalize: trace_id=%s span_count=%d spans_len=%d", trace.trace_id, trace.span_count, len(spans))
        await self._trace_store.save_trace_and_spans(trace, spans)


class NoopSpanBridge:
    """No-op bridge used when observability is disabled."""

    def on_event(self, event: Any) -> None:
        pass

    def set_error(self, error_message: str) -> None:
        pass

    async def finalize(self) -> None:
        pass


def create_span_bridge(
    *,
    trace_store: TraceStore,
    trace_id: str,
    agent_key: str | None = None,
    session_id: str | None = None,
    event_bus: Any | None = None,
    max_spans: int = 500,
    enabled: bool = True,
) -> SpanBridge | NoopSpanBridge:
    """创建 SpanBridge 并可选地订阅 EventBus。

    Parameters
    ----------
    trace_store:
        用于持久化 trace 数据。
    trace_id:
        关联的 trace ID。
    event_bus:
        如果提供，自动订阅并开始监听。
    max_spans:
        单条 trace 最大 span 数，超限时丢弃。
    enabled:
        设为 False 时返回 NoopSpanBridge（不记录任何数据）。
    """
    if not enabled:
        return NoopSpanBridge()

    bridge = SpanBridge(
        trace_store=trace_store,
        trace_id=trace_id,
        agent_key=agent_key,
        session_id=session_id,
        max_spans=max_spans,
    )
    if event_bus is not None:
        bridge._unsub = event_bus.subscribe(bridge.on_event)
    return bridge
