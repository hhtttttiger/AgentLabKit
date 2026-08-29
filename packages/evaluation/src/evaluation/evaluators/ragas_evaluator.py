"""RagasEvaluator — 将 RAGAS Provider 适配为 Evaluator 协议。

桥接旧的 RAGAS Provider 和新的 Evaluator 协议，
使 RAGAS 能通过新 Evaluator API 工作。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..contracts_v2 import (
    DatasetExample,
    EvaluationContext,
    EvaluationResult,
    Evaluator,
    MetricResult,
)
from ..providers.ragas_provider import RAGASEvalProvider

logger = logging.getLogger(__name__)


class RagasEvaluator:
    """RAGAS 评估器 — 实现 Evaluator 协议。

    内部使用 RagasProvider 进行实际评估，
    将新的 EvaluationContext 转换为旧的 EvalCase 格式。
    """

    def __init__(
        self,
        provider: RAGASEvalProvider,
        metric_names: list[str] | None = None,
    ) -> None:
        self._provider = provider
        self._metric_names = metric_names or [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
        ]
        self.name = "ragas"

    async def evaluate(
        self,
        context: EvaluationContext,
    ) -> EvaluationResult:
        """评估单个样本。"""
        import time
        start = time.monotonic()

        try:
            # 将 EvaluationContext 转换为 EvalCase
            case = _context_to_eval_case(context)

            # 使用 provider 评估
            from ..contracts import EvalRunConfig
            config = EvalRunConfig(
                metric_configs=[{"name": name} for name in self._metric_names],
            )
            results = await self._provider.evaluate([case], self._metric_names, config)

            if not results:
                return EvaluationResult(
                    example_id=context.example.example_id,
                    error_message="no results returned from RAGAS",
                    duration_ms=int((time.monotonic() - start) * 1000),
                )

            result = results[0]

            # 转换为 EvaluationResult
            metric_results = []
            for mr in result.metric_results:
                metric_results.append(MetricResult(
                    metric_name=mr.metric_name,
                    score=mr.score,
                    reasoning=mr.reasoning,
                    passed=mr.passed,
                ))

            return EvaluationResult(
                example_id=context.example.example_id,
                run_id=context.run.run_id if context.run else None,
                metric_results=metric_results,
                score=result.overall_score,
                message=result.error_message,
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        except Exception as e:
            logger.exception("ragas_evaluator.evaluate_failed example_id=%s", context.example.example_id)
            return EvaluationResult(
                example_id=context.example.example_id,
                message=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    async def evaluate_batch(
        self,
        contexts: list[EvaluationContext],
    ) -> list[EvaluationResult]:
        """批量评估多个样本。"""
        if not contexts:
            return []

        # 并发评估
        tasks = [self.evaluate(ctx) for ctx in contexts]
        return await asyncio.gather(*tasks)


def _context_to_eval_case(context: EvaluationContext) -> Any:
    """将 EvaluationContext 转换为 EvalCase。"""
    from ..contracts import EvalCase

    return EvalCase(
        id=int(context.example.example_id) if context.example.example_id.isdigit() else 0,
        dataset_id=int(context.example.dataset_id) if context.example.dataset_id.isdigit() else 0,
        input_text=context.example.input_text,
        expected_output=context.example.expected_output,
        context=context.example.context,
        tags=context.example.tags,
        metadata=context.example.metadata,
    )


__all__ = ["RagasEvaluator"]
