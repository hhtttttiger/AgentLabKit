"""RAGAS v0.4.3 评估 Provider。

通过 llm_factory 桥接 llm_gateway 的 RuntimeProviderConfig，
复用网关的凭证与路由能力。
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import Any

from ..contracts import EvalCase, EvalMetricResult, EvalRunConfig, EvalRunResult
from .base import EvalMetric, EvalProvider

# RAGAS 是 optional dependency — 顶层不导入，延迟到函数内部
# 未安装时 import 会在调用点抛出清晰的 ImportError

logger = logging.getLogger(__name__)

# ── 默认 metric 注册表 ────────────────────────────────────────────────

_RAGAS_METRIC_MAP: dict[str, str] = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "AnswerRelevancy",
    "context_precision": "ContextPrecision",
}


def _score_or_none(value: Any) -> float | None:
    """ragas 用 NaN 表示该行该指标评估失败；NaN/Inf 不允许进入结果。

    unavailable 返回 None（没有分数），绝不折算成 0.0，也不据此判 FAIL。
    """
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(score) or math.isinf(score):
        return None
    return score


# ── 内部 EvalMetric 适配 ──────────────────────────────────────────────


@dataclass
class _RAGASMetricAdapter:
    """将 RAGAS metric 适配为 EvalMetric 协议。"""

    name: str
    _ragas_metric: Any = field(repr=False)
    _llm: Any = field(repr=False, default=None)
    provider: str = "ragas"

    async def score(self, case: EvalCase) -> float:
        """单个 case 评分 — 构造最小 dataset 调用 RAGAS。"""
        from ragas import EvaluationDataset, evaluate

        dataset = EvaluationDataset.from_list([{
            "user_input": case.input_text,
            "retrieved_contexts": case.context or [],
            "response": case.expected_output or "",
            "reference": case.expected_output or "",
        }])
        result = await asyncio.to_thread(
            evaluate,
            dataset=dataset,
            metrics=[self._ragas_metric],
            llm=self._llm,
        )
        # ragas 0.4.3 EvaluationResult 支持 __getitem__（per-row 分数列表），
        # 没有 .get()。
        value = _score_or_none(result[self.name][0])
        if value is None:
            raise ValueError(f"ragas metric {self.name!r} unavailable (NaN) for this case")
        return value


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

    async def _ensure_llm(self, model_override: str | None = None) -> Any:
        """确保 RAGAS LLM 已构建（懒解析 gateway provider config）。

        Args:
            model_override: per-run-config judge 模型（``EvalRunConfig.judge_model_key``），
                为空时使用 provider 级 ``model_name``。两者都为空时 fail-fast。
        """
        if self._config_resolved and self._llm is not None:
            return self._llm

        if self._gateway_service is not None:
            model = (model_override or self._model_name or "").strip()
            if not model:
                raise RuntimeError(
                    "Judge model not configured: set the run config's judge "
                    "model or EVALUATION_DEFAULT_JUDGE_MODEL. Refusing to "
                    "guess a vendor default."
                )
            try:
                config = await self._gateway_service.resolve_provider_config(model)
            except Exception as exc:
                raise RuntimeError(
                    f"Judge model {model!r} could not be resolved through the "
                    f"LLM gateway: {exc}"
                ) from exc
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
        return _RAGASMetricAdapter(name=metric_name, _ragas_metric=ragas_metric, _llm=self._llm)

    def list_metrics(self) -> list[str]:
        return list(self._RAGAS_METRIC_NAMES())

    async def evaluate(
        self,
        cases: list[EvalCase],
        metrics: list[str],
        config: EvalRunConfig,
    ) -> list[EvalRunResult]:
        """批量评估 — 返回 per-case 结果列表，与 legacy 行为一致。"""
        import time as _time

        start = _time.monotonic()

        try:
            from ragas import EvaluationDataset, evaluate
        except ImportError:
            err = EvalRunResult(
                error_message="ragas package not installed. pip install agentlabkit-evaluation[ragas]",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )
            return [err]

        # 确保 LLM 已构建（per-config judge 模型优先于模块级默认）
        try:
            await self._ensure_llm(
                model_override=getattr(config, "judge_model_key", None),
            )
        except RuntimeError as e:
            err = EvalRunResult(
                error_message=str(e),
                duration_ms=int((_time.monotonic() - start) * 1000),
            )
            return [err]

        # 解析 metric 实例（只跟踪实际交给 ragas 的名字）
        ragas_metrics = []
        resolved_names: list[str] = []
        for name in metrics:
            if name in self._custom_metrics:
                ragas_metrics.append(self._custom_metrics[name])
                resolved_names.append(name)
            elif name in _RAGAS_METRIC_MAP:
                ragas_metrics.append(self._resolve_ragas_metric(name))
                resolved_names.append(name)
            else:
                logger.warning("Skipping unknown RAGAS metric: %s", name)

        if not ragas_metrics:
            err = EvalRunResult(
                error_message="No valid metrics resolved",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )
            return [err]

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
            err = EvalRunResult(
                error_message=f"RAGAS evaluation failed: {e}",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )
            return [err]

        # 拆分为 per-case 结果
        duration = int((_time.monotonic() - start) * 1000)
        results: list[EvalRunResult] = []
        for i, case in enumerate(cases):
            case_scores: list[float] = []
            case_metric_results: list[EvalMetricResult] = []
            for metric_name in resolved_names:
                # ragas 0.4.3 EvaluationResult: result[name] 是 per-row 分数
                # 列表（无 .get()）；raise_exceptions=False 时失败行为 NaN。
                try:
                    row_scores = list(result[metric_name])
                except (KeyError, IndexError, TypeError):
                    logger.warning("ragas result missing metric %r", metric_name)
                    continue
                val: float | None = None
                if i < len(row_scores):
                    val = _score_or_none(row_scores[i])
                if val is not None:
                    case_metric_results.append(
                        EvalMetricResult(metric_name=metric_name, score=val, reasoning=None)
                    )
                    case_scores.append(val)
                else:
                    # unavailable ≠ 0.0，且不据此判 FAIL
                    case_metric_results.append(
                        EvalMetricResult(
                            metric_name=metric_name, score=None, passed=None,
                            reasoning="metric unavailable (ragas returned no score)",
                        )
                    )

            results.append(EvalRunResult(
                case_id=case.id,
                metric_results=case_metric_results,
                overall_score=round(sum(case_scores) / len(case_scores), 4) if case_scores else None,
                duration_ms=duration,
            ))
        return results

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
