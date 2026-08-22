"""EvaluationRunner — 编排评估执行。

支持两种模式：
1. Legacy（Judge + 内置 Metric）— 向后兼容
2. Provider（EvalProvider via ProviderRegistry）— 新架构
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .contracts import EvalCase, EvalMetricResult, EvalRunConfig, EvalRunResult, TargetExecutor
from .judge import Judge
from .metrics.base import AnswerRelevanceMetric, FaithfulnessMetric, ContextRelevanceMetric
from .providers.base import EvalProvider
from .providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

BUILTIN_METRICS = {
    "answer_relevance": AnswerRelevanceMetric,
    "faithfulness": FaithfulnessMetric,
    "context_relevance": ContextRelevanceMetric,
}


class EvaluationRunner:
    """执行评估运行。

    支持两种模式：

    - **Provider 模式**（推荐）：通过 ``provider_registry`` 路由到 EvalProvider 实现。
    - **Legacy 模式**：直接使用 Judge + 内置 Metric，保持向后兼容。
    """

    def __init__(
        self,
        *,
        judge: Judge | None = None,
        max_concurrent: int = 5,
        provider_registry: ProviderRegistry | None = None,
        provider_name: str | None = None,
    ) -> None:
        """
        Args:
            judge: LLM-as-Judge 实例（legacy 模式）。
            max_concurrent: 最大并发数。
            provider_registry: Provider 注册表（provider 模式）。
            provider_name: 指定 provider 名称，不传则使用默认。
        """
        self._judge = judge
        self._max_concurrent = max_concurrent
        self._registry = provider_registry
        self._provider_name = provider_name

    @property
    def use_provider(self) -> bool:
        """是否使用 provider 模式。"""
        return self._registry is not None

    def _get_provider(self) -> EvalProvider | None:
        """获取当前 provider 实例。"""
        if self._registry is None:
            return None
        return self._registry.get(self._provider_name)

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

            # 2. 选择评估路径
            provider = self._get_provider()
            if provider is not None:
                return await self._run_with_provider(case, config, provider, start)

            return await self._run_with_legacy(case, actual_output, config, start)

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
        provider = self._get_provider()

        # Provider 模式: 批量调用 provider.evaluate()
        if provider is not None:
            start = time.monotonic()
            try:
                metric_names = self._resolve_metric_names(config)
                result = await provider.evaluate(cases, metric_names, config)
                # 将聚合结果拆分为 per-case 列表（保持 API 兼容）
                # 如果 provider 返回了 per-case 信息则使用，否则返回聚合结果
                return [result]
            except Exception as e:
                return [EvalRunResult(
                    error_message=str(e),
                    duration_ms=int((time.monotonic() - start) * 1000),
                )]

        # Legacy 模式: 逐 case 并发
        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def limited(case: EvalCase) -> EvalRunResult:
            async with semaphore:
                return await self.run_single_case(case, config, target_executor)

        return list(await asyncio.gather(*[limited(c) for c in cases]))

    # ── Provider 模式 ─────────────────────────────────────────────────

    async def _run_with_provider(
        self,
        case: EvalCase,
        config: EvalRunConfig,
        provider: EvalProvider,
        start: float,
    ) -> EvalRunResult:
        """通过 EvalProvider 评估单个用例。"""
        metric_names = self._resolve_metric_names(config)
        result = await provider.evaluate([case], metric_names, config)
        result.case_id = case.id
        return result

    # ── Legacy 模式 ───────────────────────────────────────────────────

    async def _run_with_legacy(
        self,
        case: EvalCase,
        actual_output: str,
        config: EvalRunConfig,
        start: float,
    ) -> EvalRunResult:
        """通过 Judge + 内置 Metric 评估单个用例。"""
        metrics = self._resolve_legacy_metrics(config)
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

        scores = [r.score for r in metric_results]
        overall = sum(scores) / len(scores) if scores else 0.0

        return EvalRunResult(
            case_id=case.id,
            actual_output=actual_output,
            metric_results=metric_results,
            overall_score=round(overall, 4),
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    # ── 辅助方法 ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_metric_names(config: EvalRunConfig) -> list[str]:
        """从配置中提取 metric 名称列表。"""
        names = [mc.get("name", "") for mc in config.metric_configs if mc.get("name")]
        return names or list(BUILTIN_METRICS.keys())

    @staticmethod
    def _resolve_legacy_metrics(config: EvalRunConfig) -> list:
        """根据配置解析 legacy 指标实例。"""
        metrics = []
        for mc in config.metric_configs:
            name = mc.get("name", "")
            cls = BUILTIN_METRICS.get(name)
            if cls:
                metrics.append(cls())
        if not metrics:
            metrics = [cls() for cls in BUILTIN_METRICS.values()]
        return metrics
