"""EvaluationRunner — 编排评估执行。"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from .contracts import EvalCase, EvalMetricResult, EvalRunConfig, EvalRunResult, TargetExecutor
from .judge import Judge
from .metrics.base import AnswerRelevanceMetric, FaithfulnessMetric, ContextRelevanceMetric

BUILTIN_METRICS = {
    "answer_relevance": AnswerRelevanceMetric,
    "faithfulness": FaithfulnessMetric,
    "context_relevance": ContextRelevanceMetric,
}


class EvaluationRunner:
    """执行评估运行。"""

    def __init__(
        self,
        *,
        judge: Judge | None = None,
        max_concurrent: int = 5,
    ) -> None:
        self._judge = judge
        self._max_concurrent = max_concurrent

    async def run_single_case(
        self,
        case: EvalCase,
        config: EvalRunConfig,
        target_executor: TargetExecutor | None = None,
    ) -> EvalRunResult:
        """评估单个用例。"""
        start = time.monotonic()

        try:
            # 1. 获取实际输出
            actual_output = ""
            if target_executor:
                actual_output = await target_executor.execute(case, config)
            elif case.expected_output:
                actual_output = case.expected_output  # fallback

            # 2. 运行指标评估
            metrics = self._resolve_metrics(config)
            metric_results: list[EvalMetricResult] = []

            for metric in metrics:
                result = await metric.evaluate(
                    input_text=case.input_text,
                    actual_output=actual_output,
                    expected_output=case.expected_output,
                    context=case.context or None,
                    judge=self._judge,
                )
                metric_results.append(result)

            # 3. 计算总分
            scores = [r.score for r in metric_results]
            overall = sum(scores) / len(scores) if scores else 0.0

            return EvalRunResult(
                case_id=case.id,
                actual_output=actual_output,
                metric_results=metric_results,
                overall_score=round(overall, 4),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        except Exception as e:
            return EvalRunResult(
                case_id=case.id,
                error_message=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    async def run_batch(
        self,
        cases: list[EvalCase],
        config: EvalRunConfig,
        target_executor: TargetExecutor | None = None,
    ) -> list[EvalRunResult]:
        """并发评估多个用例。"""
        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def limited(case: EvalCase) -> EvalRunResult:
            async with semaphore:
                return await self.run_single_case(case, config, target_executor)

        return list(await asyncio.gather(*[limited(c) for c in cases]))

    @staticmethod
    def _resolve_metrics(config: EvalRunConfig) -> list:
        """根据配置解析指标实例。"""
        metrics = []
        for mc in config.metric_configs:
            name = mc.get("name", "")
            cls = BUILTIN_METRICS.get(name)
            if cls:
                metrics.append(cls())
        if not metrics:
            # 默认使用所有内置指标
            metrics = [cls() for cls in BUILTIN_METRICS.values()]
        return metrics
