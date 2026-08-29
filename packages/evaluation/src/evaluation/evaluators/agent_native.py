"""Agent Native Evaluators — 无需 LLM judge 的行为评估器。

基于 Execution Model v2 的语义事件和 AgentRun，
对 Agent 行为进行规则化评估。

用法：

    evaluator = ToolCalledEvaluator(tool_name="search")
    result = await evaluator.evaluate(context)
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ..contracts_v2 import (
    EvaluationContext,
    EvaluationResult,
    MetricResult,
)

logger = logging.getLogger(__name__)


class ToolCalledEvaluator:
    """检查指定工具是否被调用。"""

    def __init__(self, tool_name: str, name: str = "tool_called") -> None:
        self.tool_name = tool_name
        self.name = name

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        start = time.monotonic()
        called = self._check(context)
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            metric_results=[MetricResult(
                metric_name=self.name,
                score=1.0 if called else 0.0,
                passed=called,
                details={"tool_name": self.tool_name, "called": called},
            )],
            score=1.0 if called else 0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def evaluate_batch(self, contexts: list[EvaluationContext]) -> list[EvaluationResult]:
        return [await self.evaluate(ctx) for ctx in contexts]

    def _check(self, context: EvaluationContext) -> bool:
        # 从 run.tool_names 检查
        if context.run and self.tool_name in (context.run.tool_names or []):
            return True
        # 从 spans 检查 tool. 前缀的 span
        for span in context.spans:
            if span.name.startswith("tool.") and span.attributes.get("tool.name") == self.tool_name:
                return True
        return False


class ToolNotCalledEvaluator:
    """检查指定工具是否未被调用。"""

    def __init__(self, tool_name: str, name: str = "tool_not_called") -> None:
        self.tool_name = tool_name
        self.name = name

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        start = time.monotonic()
        called = self._check(context)
        not_called = not called
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            metric_results=[MetricResult(
                metric_name=self.name,
                score=1.0 if not_called else 0.0,
                passed=not_called,
                details={"tool_name": self.tool_name, "called": called},
            )],
            score=1.0 if not_called else 0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def evaluate_batch(self, contexts: list[EvaluationContext]) -> list[EvaluationResult]:
        return [await self.evaluate(ctx) for ctx in contexts]

    def _check(self, context: EvaluationContext) -> bool:
        if context.run and self.tool_name in (context.run.tool_names or []):
            return True
        for span in context.spans:
            if span.name.startswith("tool.") and span.attributes.get("tool.name") == self.tool_name:
                return True
        return False


class ToolArgsEvaluator:
    """检查工具调用参数是否包含指定键值。"""

    def __init__(
        self,
        tool_name: str,
        expected_args: dict[str, Any],
        name: str = "tool_args",
    ) -> None:
        self.tool_name = tool_name
        self.expected_args = expected_args
        self.name = name

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        start = time.monotonic()
        matched, details = self._check(context)
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            metric_results=[MetricResult(
                metric_name=self.name,
                score=1.0 if matched else 0.0,
                passed=matched,
                details=details,
            )],
            score=1.0 if matched else 0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def evaluate_batch(self, contexts: list[EvaluationContext]) -> list[EvaluationResult]:
        return [await self.evaluate(ctx) for ctx in contexts]

    def _check(self, context: EvaluationContext) -> tuple[bool, dict]:
        for span in context.spans:
            if span.name == f"tool.{self.tool_name}":
                args = span.attributes.get("tool.arguments", {})
                if isinstance(args, dict):
                    for key, expected_val in self.expected_args.items():
                        actual_val = args.get(key)
                        if actual_val != expected_val:
                            return False, {
                                "tool_name": self.tool_name,
                                "key": key,
                                "expected": expected_val,
                                "actual": actual_val,
                            }
                    return True, {"tool_name": self.tool_name, "matched": True}
        return False, {"tool_name": self.tool_name, "found": False}


class MaxStepsEvaluator:
    """检查 Agent 是否在最大步骤数限制内完成。"""

    def __init__(self, max_steps: int, name: str = "max_steps") -> None:
        self.max_steps = max_steps
        self.name = name

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        start = time.monotonic()
        actual_steps = self._count_steps(context)
        within_limit = actual_steps <= self.max_steps
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            metric_results=[MetricResult(
                metric_name=self.name,
                score=1.0 if within_limit else 0.0,
                passed=within_limit,
                details={"max_steps": self.max_steps, "actual_steps": actual_steps},
            )],
            score=1.0 if within_limit else 0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def evaluate_batch(self, contexts: list[EvaluationContext]) -> list[EvaluationResult]:
        return [await self.evaluate(ctx) for ctx in contexts]

    def _count_steps(self, context: EvaluationContext) -> int:
        if context.run:
            return context.run.tool_call_count
        # fallback: count tool spans
        return sum(1 for s in context.spans if s.name.startswith("tool."))


class LatencyEvaluator:
    """检查执行延迟是否在阈值内。"""

    def __init__(self, max_duration_ms: int, name: str = "latency") -> None:
        self.max_duration_ms = max_duration_ms
        self.name = name

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        start = time.monotonic()
        actual_ms = self._get_duration(context)
        within_limit = actual_ms <= self.max_duration_ms
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            metric_results=[MetricResult(
                metric_name=self.name,
                score=1.0 if within_limit else 0.0,
                passed=within_limit,
                details={"max_ms": self.max_duration_ms, "actual_ms": actual_ms},
            )],
            score=1.0 if within_limit else 0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def evaluate_batch(self, contexts: list[EvaluationContext]) -> list[EvaluationResult]:
        return [await self.evaluate(ctx) for ctx in contexts]

    def _get_duration(self, context: EvaluationContext) -> int:
        if context.run:
            return context.run.duration_ms
        # fallback: sum span durations
        return sum(s.duration_ms for s in context.spans)


class CostEvaluator:
    """检查执行成本是否在预算内。"""

    def __init__(self, max_cost_usd: float, name: str = "cost") -> None:
        self.max_cost_usd = max_cost_usd
        self.name = name

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        start = time.monotonic()
        actual_cost = self._estimate_cost(context)
        within_budget = actual_cost <= self.max_cost_usd
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            metric_results=[MetricResult(
                metric_name=self.name,
                score=1.0 if within_budget else 0.0,
                passed=within_budget,
                details={"max_cost_usd": self.max_cost_usd, "actual_cost_usd": actual_cost},
            )],
            score=1.0 if within_budget else 0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def evaluate_batch(self, contexts: list[EvaluationContext]) -> list[EvaluationResult]:
        return [await self.evaluate(ctx) for ctx in contexts]

    def _estimate_cost(self, context: EvaluationContext) -> float:
        # 简单估算: 基于 token 数
        if context.run:
            total_tokens = context.run.total_input_tokens + context.run.total_output_tokens
            # 粗略估算: $0.01 per 1K tokens
            return total_tokens / 1000 * 0.01
        return 0.0


class NoErrorEvaluator:
    """检查 Agent 执行是否无错误。"""

    def __init__(self, name: str = "no_error") -> None:
        self.name = name

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        start = time.monotonic()
        has_error = self._check_error(context)
        no_error = not has_error
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            metric_results=[MetricResult(
                metric_name=self.name,
                score=1.0 if no_error else 0.0,
                passed=no_error,
                details={"has_error": has_error},
            )],
            score=1.0 if no_error else 0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def evaluate_batch(self, contexts: list[EvaluationContext]) -> list[EvaluationResult]:
        return [await self.evaluate(ctx) for ctx in contexts]

    def _check_error(self, context: EvaluationContext) -> bool:
        # 检查 run status
        if context.run and context.run.status not in ("ok", "completed"):
            return True
        # 检查是否有 error span
        for span in context.spans:
            if span.attributes.get("error") or span.attributes.get("status") == "error":
                return True
        return False


class TrajectoryEvaluator:
    """检查 Agent 执行轨迹是否匹配预期模式。

    expected_trajectory 是一个 span name 列表，表示期望的执行顺序。
    支持通配符 "*" 匹配任意 span。
    """

    def __init__(
        self,
        expected_trajectory: list[str],
        name: str = "trajectory",
    ) -> None:
        self.expected_trajectory = expected_trajectory
        self.name = name

    async def evaluate(self, context: EvaluationContext) -> EvaluationResult:
        start = time.monotonic()
        actual_trajectory = [s.name for s in context.spans]
        matched = self._match(actual_trajectory)
        return EvaluationResult(
            example_id=context.example.example_id,
            run_id=context.run.run_id if context.run else None,
            metric_results=[MetricResult(
                metric_name=self.name,
                score=1.0 if matched else 0.0,
                passed=matched,
                details={
                    "expected": self.expected_trajectory,
                    "actual": actual_trajectory,
                },
            )],
            score=1.0 if matched else 0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def evaluate_batch(self, contexts: list[EvaluationContext]) -> list[EvaluationResult]:
        return [await self.evaluate(ctx) for ctx in contexts]

    def _match(self, actual: list[str]) -> bool:
        """简单的前缀匹配，支持 "*" 通配符。"""
        if len(actual) < len(self.expected_trajectory):
            return False
        for expected, actual_name in zip(self.expected_trajectory, actual):
            if expected == "*":
                continue
            if expected != actual_name:
                return False
        return True


__all__ = [
    "ToolCalledEvaluator",
    "ToolNotCalledEvaluator",
    "ToolArgsEvaluator",
    "MaxStepsEvaluator",
    "LatencyEvaluator",
    "CostEvaluator",
    "NoErrorEvaluator",
    "TrajectoryEvaluator",
]
