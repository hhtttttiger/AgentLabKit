"""CostProjector — 消费 RuntimeEvent v2 语义事件，生成 CostRecord。

核心原则：
- Cost 数据完全可以从 execution events 生成
- 不再依赖 llm_gateway 的 model_request_logs 表
- 支持 cost per run / agent / workflow / experiment

用法：

    projector = CostProjector(publisher)
    bus.subscribe(projector.handle)

当收到 LLMCallCompleted 时，构建 CostRecord 并提交。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .contracts import CostRecord
from .publisher import CostPublisher

logger = logging.getLogger(__name__)


def _to_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class CostProjector:
    """消费语义事件，构建 CostRecord。

    目前只处理 LLMCallCompleted 事件。
    未来可以扩展处理 RunCompleted 事件以聚合 run 级别成本。
    """

    def __init__(self, publisher: CostPublisher) -> None:
        self._publisher = publisher

    async def handle(self, event: Any) -> None:
        """EventBus listener — 处理所有事件类型。

        只处理 v2 语义事件（有 event_type 属性的 RuntimeEvent 子类）。
        旧事件（AgentStartEvent 等）被忽略。
        """
        event_type = getattr(event, "event_type", None)
        if event_type is None or not isinstance(event_type, str):
            return  # 不是 v2 语义事件，跳过

        # 按事件类型分发
        handler = self._HANDLERS.get(event_type)
        if handler is not None:
            handler(self, event)

    # ── LLM calls ───────────────────────────────────────────────────

    def _handle_llm_completed(self, event: Any) -> None:
        """处理 LLMCallCompleted 事件，生成 CostRecord。"""
        run_id = getattr(event, "run_id", "")
        if not run_id:
            return

        # 提取 usage 数据
        input_tokens = getattr(event, "input_tokens", 0) or 0
        output_tokens = getattr(event, "output_tokens", 0) or 0
        cache_write_tokens = getattr(event, "cache_write_tokens", 0) or 0
        cache_read_tokens = getattr(event, "cache_read_tokens", 0) or 0
        estimated_cost = getattr(event, "estimated_cost", Decimal("0")) or Decimal("0")

        # 时间戳：优先使用 completed_at，回退到 timestamp (5.3)
        started_at = getattr(event, "started_at", None)
        completed_at = getattr(event, "completed_at", None) or getattr(event, "timestamp", None)

        # 构建 CostRecord — identity 来自 event (5.2)
        record = CostRecord(
            run_id=run_id,
            trace_id=getattr(event, "trace_id", ""),
            span_id=getattr(event, "span_id", ""),
            agent_key=getattr(event, "agent_key", "") or "",
            model=getattr(event, "model", ""),
            provider=getattr(event, "provider", ""),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_write_tokens=cache_write_tokens,
            cache_read_tokens=cache_read_tokens,
            estimated_cost=float(estimated_cost),
            started_at_utc=_to_utc(started_at),
            completed_at_utc=_to_utc(completed_at),
        )

        try:
            self._publisher.submit_nowait(record)
        except Exception:
            logger.exception("cost_projector.submit_failed run_id=%s", run_id)

    def _handle_llm_failed(self, event: Any) -> None:
        """处理 LLMCallFailed 事件，生成零成本 CostRecord。

        失败的调用也需要记录，以便追踪失败的成本影响。
        """
        run_id = getattr(event, "run_id", "")
        if not run_id:
            return

        started_at = getattr(event, "started_at", None)
        completed_at = getattr(event, "completed_at", None) or getattr(event, "timestamp", None)

        record = CostRecord(
            run_id=run_id,
            trace_id=getattr(event, "trace_id", ""),
            span_id=getattr(event, "span_id", ""),
            agent_key=getattr(event, "agent_key", "") or "",
            model=getattr(event, "model", ""),
            provider=getattr(event, "provider", ""),
            input_tokens=0,
            output_tokens=0,
            cache_write_tokens=0,
            cache_read_tokens=0,
            estimated_cost=0.0,
            error_code=getattr(event, "error_code", None),
            error_message=getattr(event, "error_message", None),
            started_at_utc=_to_utc(started_at),
            completed_at_utc=_to_utc(completed_at),
        )

        try:
            self._publisher.submit_nowait(record)
        except Exception:
            logger.exception("cost_projector.submit_failed run_id=%s", run_id)

    # ── Handler dispatch table ──────────────────────────────────────

    _HANDLERS = {
        "llm.call_completed": _handle_llm_completed,
        "llm.call_failed": _handle_llm_failed,
    }


__all__ = ["CostProjector"]
