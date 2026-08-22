"""RAGAS v0.4.3 评估 Provider。

通过 llm_factory 桥接 llm_gateway 的 RuntimeProviderConfig，
复用网关的凭证与路由能力。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from ..contracts import EvalCase, EvalMetricResult, EvalRunConfig, EvalRunResult
from .base import EvalMetric, EvalProvider

logger = logging.getLogger(__name__)

# ── 默认 metric 注册表 ────────────────────────────────────────────────

_RAGAS_METRIC_MAP: dict[str, str] = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "AnswerRelevancy",
    "context_precision": "ContextPrecision",
}


# ── 内部 EvalMetric 适配 ──────────────────────────────────────────────


@dataclass
class _RAGASMetricAdapter:
    """将 RAGAS metric 适配为 EvalMetric 协议。"""

    name: str
    _ragas_metric: Any = field(repr=False)
    provider: str = "ragas"

    async def score(self, case: EvalCase) -> float:
        raise NotImplementedError("Use evaluate() on the provider instead")


# ── EvalRunResult 聚合辅助 ────────────────────────────────────────────


def _aggregate_results(per_case_results: list[EvalRunResult]) -> EvalRunResult:
    """将多个 per-case 结果聚合为单一 EvalRunResult。"""
    if not per_case_results:
        return EvalRunResult()

    all_metric_results: list[EvalMetricResult] = []
    total_score = 0.0
    total_duration = 0
    errors: list[str] = []

    for r in per_case_results:
        all_metric_results.extend(r.metric_results)
        total_score += r.overall_score
        total_duration += r.duration_ms
        if r.error_message:
            errors.append(r.error_message)

    n = len(per_case_results)
    return EvalRunResult(
        metric_results=all_metric_results,
        overall_score=round(total_score / n, 4) if n else 0.0,
        duration_ms=total_duration,
        error_message="; ".join(errors) if errors else None,
    )


# ── RAGAS LLM 构建桥接 ───────────────────────────────────────────────


def _build_ragas_llm(provider_config: Any) -> Any:
    """从 RuntimeProviderConfig 构建 RAGAS LLM。

    Args:
        provider_config: 需要 ``api_key``、``base_url``、``provider`` 属性。
            典型来源: ``llm_gateway.provider_runtime.RuntimeProviderConfig``。
    """
    from ragas.llms import llm_factory

    provider_name = getattr(provider_config, "provider", "openai") or "openai"
    api_key = getattr(provider_config, "api_key", None)
    base_url = getattr(provider_config, "base_url", None)

    if provider_name == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key, base_url=base_url)
        return llm_factory(
            getattr(provider_config, "model", "claude-sonnet-4-20250514"),
            provider="anthropic",
            client=client,
        )

    # 默认: OpenAI SDK client（兼容 OpenAI 及 OpenAI-compatible 端点）
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    return llm_factory(
        getattr(provider_config, "model", "gpt-4o"),
        client=client,
    )


# ── RAGASEvalProvider ────────────────────────────────────────────────


class RAGASEvalProvider:
    """基于 RAGAS v0.4.3 的评估 Provider。

    支持三种初始化方式（优先级从高到低）::

        # 方式 1: 直接注入已构建的 LLM
        provider = RAGASEvalProvider(llm=ragas_llm)

        # 方式 2: 传入 RuntimeProviderConfig
        provider = RAGASEvalProvider(provider_config=runtime_config)

        # 方式 3: 传入 GatewayService（懒解析，推荐用于后端集成）
        provider = RAGASEvalProvider(gateway_service=gateway, model_name="gpt-4o")
    """

    name = "ragas"

    def __init__(
        self,
        *,
        model_name: str = "gpt-4o",
        provider_config: Any | None = None,
        gateway_service: Any | None = None,
        llm: Any | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """
        Args:
            model_name: 用于评估的模型名称（也用于 gateway 路由）。
            provider_config: RuntimeProviderConfig 实例，用于构建 RAGAS LLM。
            gateway_service: GatewayService 实例，首次 evaluate() 时懒解析 provider_config。
            llm: 直接传入已构建的 RAGAS LLM（优先级最高）。
            metrics: 自定义 metric 实例映射 {name: ragas_metric}。
        """
        self._model_name = model_name
        self._gateway_service = gateway_service
        self._custom_metrics = metrics or {}

        if llm is not None:
            self._llm = llm
            self._config_resolved = True
        elif provider_config is not None:
            self._llm = _build_ragas_llm(provider_config)
            self._config_resolved = True
        else:
            self._llm = None  # 等待懒解析
            self._config_resolved = False

    async def _ensure_llm(self) -> Any:
        """确保 RAGAS LLM 已构建（懒解析 gateway provider config）。"""
        if self._config_resolved and self._llm is not None:
            return self._llm

        if self._gateway_service is not None:
            config = await self._gateway_service.resolve_provider_config(
                self._model_name,
            )
            self._llm = _build_ragas_llm(config)
            self._config_resolved = True
            return self._llm

        raise RuntimeError(
            "RAGASEvalProvider 无法构建 LLM: 需要 llm、provider_config 或 gateway_service 之一"
        )

    def get_metric(self, metric_name: str) -> EvalMetric:
        if metric_name not in self._RAGAS_METRIC_NAMES():
            raise KeyError(f"Unknown RAGAS metric: {metric_name!r}")
        ragas_metric = self._resolve_ragas_metric(metric_name)
        return _RAGASMetricAdapter(name=metric_name, _ragas_metric=ragas_metric)

    def list_metrics(self) -> list[str]:
        return list(self._RAGAS_METRIC_NAMES())

    async def evaluate(
        self,
        cases: list[EvalCase],
        metrics: list[str],
        config: EvalRunConfig,
    ) -> EvalRunResult:
        """批量评估 — 将 EvalCase 转换为 RAGAS EvaluationDataset 并执行。"""
        import time as _time

        start = _time.monotonic()

        try:
            from ragas import EvaluationDataset, evaluate
        except ImportError:
            return EvalRunResult(
                error_message="ragas package not installed. pip install ragas>=0.4.3",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )

        # 确保 LLM 已构建
        try:
            await self._ensure_llm()
        except RuntimeError as e:
            return EvalRunResult(
                error_message=str(e),
                duration_ms=int((_time.monotonic() - start) * 1000),
            )

        # 解析 metric 实例
        ragas_metrics = []
        for name in metrics:
            if name in self._custom_metrics:
                ragas_metrics.append(self._custom_metrics[name])
            elif name in _RAGAS_METRIC_MAP:
                ragas_metrics.append(self._resolve_ragas_metric(name))
            else:
                logger.warning("Skipping unknown RAGAS metric: %s", name)

        if not ragas_metrics:
            return EvalRunResult(
                error_message="No valid metrics resolved",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )

        # 构建 RAGAS dataset
        dataset_items = []
        for case in cases:
            item = {
                "user_input": case.input_text,
                "retrieved_contexts": case.context or [],
                "response": case.expected_output or "",
            }
            if case.expected_output:
                item["reference"] = case.expected_output
            dataset_items.append(item)

        dataset = EvaluationDataset.from_list(dataset_items)

        # 异步执行（RAGAS evaluate() 是同步的）
        try:
            result = await asyncio.to_thread(
                evaluate,
                dataset=dataset,
                metrics=ragas_metrics,
                llm=self._llm,
            )
        except Exception as e:
            logger.error("RAGAS evaluate() failed: %s", e, exc_info=True)
            return EvalRunResult(
                error_message=f"RAGAS evaluation failed: {e}",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )

        # 解析结果
        metric_results = self._parse_ragas_result(result, metrics, len(cases))
        scores = [mr.score for mr in metric_results]

        return EvalRunResult(
            metric_results=metric_results,
            overall_score=round(sum(scores) / len(scores), 4) if scores else 0.0,
            duration_ms=int((_time.monotonic() - start) * 1000),
        )

    # ── 内部方法 ──────────────────────────────────────────────────────

    def _RAGAS_METRIC_NAMES(self) -> set[str]:
        return set(_RAGAS_METRIC_MAP.keys()) | set(self._custom_metrics.keys())

    def _resolve_ragas_metric(self, metric_name: str) -> Any:
        """延迟导入并实例化 RAGAS metric。"""
        if metric_name in self._custom_metrics:
            return self._custom_metrics[metric_name]

        from ragas import metrics as ragas_metrics_module

        class_name = _RAGAS_METRIC_MAP[metric_name]
        cls = getattr(ragas_metrics_module, class_name)
        return cls(llm=self._llm)

    @staticmethod
    def _parse_ragas_result(
        result: Any,
        requested_metrics: list[str],
        num_cases: int,
    ) -> list[EvalMetricResult]:
        """将 RAGAS evaluate() 返回值解析为 EvalMetricResult 列表。"""
        metric_results: list[EvalMetricResult] = []

        for metric_name in requested_metrics:
            score = result.get(metric_name)
            if score is not None:
                metric_results.append(
                    EvalMetricResult(
                        metric_name=metric_name,
                        score=float(score),
                        reasoning=None,
                    )
                )

        return metric_results


# ── 便捷工厂 ─────────────────────────────────────────────────────────


def create_ragas_provider(
    *,
    model_name: str = "gpt-4o",
    provider_config: Any | None = None,
) -> RAGASEvalProvider:
    """便捷工厂函数。"""
    return RAGASEvalProvider(
        model_name=model_name,
        provider_config=provider_config,
    )
