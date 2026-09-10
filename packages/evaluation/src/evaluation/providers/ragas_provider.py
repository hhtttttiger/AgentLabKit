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
from ..evidence import (
    REASON_EVIDENCE_NOT_PROVIDED,
    REASON_MISSING_ACTUAL_OUTPUT,
    REASON_MISSING_REFERENCE,
    REASON_NO_RETRIEVAL,
    REASON_RETRIEVAL_FAILED,
    REASON_TRACE_UNAVAILABLE,
    EvidenceAvailability,
)
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

# 每个 metric 声明它需要哪些 canonical evidence 字段（§14）。
# 不写 provider name 特判，也不在 orchestration 散落 if metric == ...；
# provider 用这张小映射决定 missing evidence 时的 truthful unavailable。
_RAGAS_METRIC_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    # faithfulness: 回答是否忠实于 candidate 实际检索到的 contexts
    "faithfulness": ("actual_output", "retrieved_contexts"),
    # answer_relevancy: 只需要回答本身（answer-only metric）
    "answer_relevancy": ("actual_output",),
    # context_precision: 检索 contexts 是否支撑 reference 答案
    "context_precision": ("retrieved_contexts", "reference"),
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


# ── Canonical evidence → provider inputs ─────────────────────────────


class _CaseInputs:
    """单个 case 已解析的 provider 输入与 evidence 摘要。"""

    __slots__ = ("user_input", "response", "reference", "contexts",
                 "retrieval_reason", "evidence_summary")

    def __init__(
        self,
        *,
        user_input: str,
        response: str,
        reference: str | None,
        contexts: list[str] | None,
        retrieval_reason: str | None,
        evidence_summary: dict[str, Any] | None,
    ) -> None:
        self.user_input = user_input
        self.response = response
        self.reference = reference
        # None 表示 retrieval evidence 不可用/不适用（不能喂给 ragas）；
        # [] 是 AVAILABLE 的零结果，是合法输入。
        self.contexts = contexts
        self.retrieval_reason = retrieval_reason
        self.evidence_summary = evidence_summary


def _resolve_case_inputs(
    index: int,
    case: EvalCase,
    actual_outputs: list[str] | None,
    evidence: list[Any] | None,
) -> _CaseInputs:
    ev = evidence[index] if evidence is not None and index < len(evidence) else None
    if ev is not None:
        # Candidate evidence is the single source of truth for the actual
        # output (it carries the Runtime-owned Run output verbatim).
        response = ev.actual_output if ev.actual_output is not None else ""
    elif actual_outputs is not None and index < len(actual_outputs):
        response = actual_outputs[index]
    else:
        response = case.expected_output or ""
    if ev is None:
        # 没有 canonical evidence：caller 没有提供 candidate 执行事实。
        # DatasetExample.context 是数据集 expectation 字段 —— 绝不能被解释成
        # candidate retrieved_contexts（向后兼容只意味着"仍可调用"，不意味着
        # "恢复 Dataset context 语义"）。retrieval-aware metric 如实
        # unavailable；answer-only / reference-only metric 继续工作。
        return _CaseInputs(
            user_input=case.input_text,
            response=response,
            reference=case.expected_output,
            contexts=None,
            retrieval_reason=REASON_EVIDENCE_NOT_PROVIDED,
            evidence_summary=None,
        )

    retrieval = ev.retrieval
    summary = ev.retrieval_summary()
    if retrieval.availability is EvidenceAvailability.UNAVAILABLE:
        contexts, reason = None, (retrieval.reason or REASON_TRACE_UNAVAILABLE)
    elif retrieval.availability is EvidenceAvailability.NOT_APPLICABLE:
        contexts, reason = None, REASON_NO_RETRIEVAL
    elif retrieval.successful_attempts == 0:
        # 有 retrieval 事实但全部失败：没有可评分的 contexts。
        contexts, reason = None, REASON_RETRIEVAL_FAILED
    else:
        # AVAILABLE（包括成功但 0 结果 → 空列表是合法输入）
        contexts, reason = list(retrieval.contexts), None
    return _CaseInputs(
        user_input=case.input_text,
        response=response,
        reference=case.expected_output,
        contexts=contexts,
        retrieval_reason=reason,
        evidence_summary=summary,
    )


def _metric_unavailable_reason(metric_name: str, inputs: _CaseInputs) -> str | None:
    """按 metric 声明的 evidence 需求判断缺失；返回 machine-readable reason。"""
    for requirement in _RAGAS_METRIC_REQUIREMENTS.get(metric_name, ()):
        if requirement == "actual_output" and not inputs.response:
            return REASON_MISSING_ACTUAL_OUTPUT
        if requirement == "reference" and not inputs.reference:
            return REASON_MISSING_REFERENCE
        if requirement == "retrieved_contexts" and inputs.contexts is None:
            return inputs.retrieval_reason or REASON_TRACE_UNAVAILABLE
    return None


_UNAVAILABLE_TEXT = {
    REASON_MISSING_ACTUAL_OUTPUT: "unavailable: candidate produced no output",
    REASON_MISSING_REFERENCE: "unavailable: dataset example has no reference answer",
    REASON_NO_RETRIEVAL: "unavailable: no retrieval occurred for this run",
    REASON_RETRIEVAL_FAILED: "unavailable: all retrieval attempts failed",
    REASON_TRACE_UNAVAILABLE: "unavailable: candidate trace evidence unavailable",
    REASON_EVIDENCE_NOT_PROVIDED: "unavailable: candidate evidence not provided by caller",
}


def _unavailable_text(reason: str | None) -> str:
    if reason is None:
        return "metric unavailable"
    return _UNAVAILABLE_TEXT.get(
        reason, f"metric unavailable ({reason})",
    )


def _ragas_item(inputs: _CaseInputs) -> dict[str, Any]:
    item: dict[str, Any] = {
        "user_input": inputs.user_input,
        "retrieved_contexts": inputs.contexts or [],
        "response": inputs.response,
    }
    if inputs.reference:
        item["reference"] = inputs.reference
    return item


# ── 内部 EvalMetric 适配 ──────────────────────────────────────────────


@dataclass
class _RAGASMetricAdapter:
    """将 RAGAS metric 适配为 EvalMetric 协议。"""

    name: str
    _ragas_metric: Any = field(repr=False)
    _llm: Any = field(repr=False, default=None)
    provider: str = "ragas"

    async def score(self, case: EvalCase) -> float:
        """单个 case 评分 — 构造最小 dataset 调用 RAGAS。

        没有 candidate evidence：DatasetExample.context 是数据集 expectation
        字段，绝不作为 retrieved_contexts 喂给 ragas；context 依赖的 metric
        会因空 contexts 得到 NaN → ValueError（truthful unavailable）。
        """
        from ragas import EvaluationDataset, evaluate

        dataset = EvaluationDataset.from_list([{
            "user_input": case.input_text,
            "retrieved_contexts": [],
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


def _build_ragas_llm(provider_config: Any, model_name: str = "") -> Any:
    """从 RuntimeProviderConfig 构建 RAGAS LLM。

    Args:
        provider_config: 需要 ``api_key``、``base_url``、``provider`` 属性。
            典型来源: ``llm_gateway.provider_runtime.RuntimeProviderConfig``。
        model_name: 已解析的 judge 模型名。``RuntimeProviderConfig`` 是
            provider 无关的传输配置，刻意不携带 model 字段；模型名必须由
            调用方（gateway 路由 / per-run judge 配置）显式传入，
            绝不默认到某个供应商模型。
    """
    from ragas.llms import llm_factory

    provider_name = getattr(provider_config, "provider", "openai") or "openai"
    api_key = getattr(provider_config, "api_key", None)
    base_url = getattr(provider_config, "base_url", None)
    model = (model_name or "").strip()
    if not model:
        raise RuntimeError(
            "RAGAS LLM requires an explicit judge model name; refusing to "
            "guess a vendor default."
        )

    if provider_name == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key, base_url=base_url)
        return llm_factory(model, provider="anthropic", client=client)

    # 默认: OpenAI SDK client（兼容 OpenAI 及 OpenAI-compatible 端点）
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    return llm_factory(model, client=client)


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
            self._llm = _build_ragas_llm(config, model)
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
        *,
        actual_outputs: list[str] | None = None,
        evidence: list[Any] | None = None,
    ) -> list[EvalRunResult]:
        """批量评估 — 返回 per-case 结果列表，与 legacy 行为一致。

        ``actual_outputs`` 是目标对每个 case 的真实输出（被评估对象）；
        缺省时回退到 ``case.expected_output``（dataset-only 模式）。

        ``evidence``（与 cases 等长）是 canonical candidate evidence。
        提供时 ``retrieved_contexts`` 只来自 evidence 中 successful retrieval
        attempts 的 bounded previews。未提供时 retrieval-aware metric 得到
        truthful unavailable（DatasetExample.context 是数据集 expectation
        字段，永远不是 candidate 检索证据）。

        缺少 metric 声明需要的 evidence 时，该 metric 得到
        ``score=None / passed=None`` 加 machine-readable reason（truthful
        unavailable），绝不折算成 0 或 FAIL。多个 metric 可以部分可用。
        """
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

        # ── Canonical evidence → per-case provider inputs ────────────
        per_case = [
            _resolve_case_inputs(i, case, actual_outputs, evidence)
            for i, case in enumerate(cases)
        ]

        # 按"gated-in metric 集合"分组；每组一次 ragas evaluate 调用。
        # gated-out 的 (case, metric) 直接得到 truthful unavailable。
        grouped: dict[tuple[str, ...], list[int]] = {}
        for i, inputs in enumerate(per_case):
            computable = tuple(
                name for name in resolved_names
                if _metric_unavailable_reason(
                    name, inputs,
                ) is None
            )
            grouped.setdefault(computable, []).append(i)

        metric_results_by_case: list[list[EvalMetricResult]] = [
            [] for _ in cases
        ]
        for computable, case_indices in grouped.items():
            if not computable:
                continue
            group_metrics = [self._resolve_ragas_metric(n) for n in computable]
            dataset = EvaluationDataset.from_list([
                _ragas_item(per_case[i]) for i in case_indices
            ])
            try:
                result = await asyncio.to_thread(
                    evaluate,
                    dataset=dataset,
                    metrics=group_metrics,
                    llm=self._llm,
                )
            except Exception as e:
                # 引擎级失败沿用既有契约：整体返回单个 error 结果，
                # 不把异常折算成 per-case 分数。
                logger.error("RAGAS evaluate() failed: %s", e, exc_info=True)
                return [EvalRunResult(
                    error_message=f"RAGAS evaluation failed: {e}",
                    duration_ms=int((_time.monotonic() - start) * 1000),
                )]

            for row, i in enumerate(case_indices):
                inputs = per_case[i]
                for metric_name in computable:
                    # ragas 0.4.3 EvaluationResult: result[name] 是 per-row 分数
                    # 列表（无 .get()）；raise_exceptions=False 时失败行为 NaN。
                    try:
                        row_scores = list(result[metric_name])
                    except (KeyError, IndexError, TypeError):
                        logger.warning("ragas result missing metric %r", metric_name)
                        continue
                    val: float | None = None
                    if row < len(row_scores):
                        val = _score_or_none(row_scores[row])
                    if val is not None:
                        metric_results_by_case[i].append(
                            EvalMetricResult(
                                metric_name=metric_name, score=val,
                                reasoning=None, evidence=inputs.evidence_summary,
                            )
                        )
                    else:
                        # unavailable ≠ 0.0，且不据此判 FAIL
                        metric_results_by_case[i].append(
                            EvalMetricResult(
                                metric_name=metric_name, score=None, passed=None,
                                reasoning="metric unavailable (ragas returned no score)",
                                reason="ragas_no_score",
                                evidence=inputs.evidence_summary,
                            )
                        )

        # gated-out + grouped 结果合并为 per-case 有序结果
        duration = int((_time.monotonic() - start) * 1000)
        results: list[EvalRunResult] = []
        for i, case in enumerate(cases):
            inputs = per_case[i]
            case_metric_results: list[EvalMetricResult] = []
            for metric_name in resolved_names:
                already = next(
                    (m for m in metric_results_by_case[i]
                     if m.metric_name == metric_name),
                    None,
                )
                if already is not None:
                    case_metric_results.append(already)
                    continue
                reason = _metric_unavailable_reason(metric_name, inputs)
                case_metric_results.append(EvalMetricResult(
                    metric_name=metric_name,
                    score=None,
                    passed=None,
                    reasoning=_unavailable_text(reason),
                    reason=reason,
                    evidence=inputs.evidence_summary,
                ))

            scores = [m.score for m in case_metric_results if m.score is not None]
            results.append(EvalRunResult(
                case_id=case.id,
                metric_results=case_metric_results,
                # None = 没有任何可用分数（unavailable ≠ 0.0）
                overall_score=round(sum(scores) / len(scores), 4) if scores else None,
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
