"""评估 Provider / Metric 协议定义。

所有评估 provider（RAGAS、DeepEval 等）必须实现 EvalProvider 协议；
provider 内部的每个指标必须实现 EvalMetric 协议。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts import EvalCase, EvalRunConfig, EvalRunResult


@runtime_checkable
class EvalMetric(Protocol):
    """单个评估指标。"""

    name: str
    provider: str

    async def score(self, case: EvalCase) -> float:
        """对单个用例评分，返回 0.0-1.0。"""
        ...


@runtime_checkable
class EvalProvider(Protocol):
    """评估提供器协议 — 所有 provider 必须实现。

    生命周期：
      1. 通过 ``ProviderRegistry.register()`` 注册实例
      2. 通过 ``get_metric()`` 获取具体指标
      3. 通过 ``evaluate()`` 批量评估
    """

    name: str

    def get_metric(self, metric_name: str) -> EvalMetric:
        """按名称获取指标实例。未知名称应抛出 KeyError。"""
        ...

    def list_metrics(self) -> list[str]:
        """返回该 provider 支持的所有指标名称。"""
        ...

    async def evaluate(
        self,
        cases: list[EvalCase],
        metrics: list[str],
        config: EvalRunConfig,
        *,
        actual_outputs: list[str] | None = None,
        evidence: list[Any] | None = None,
    ) -> list[EvalRunResult]:
        """批量评估：对每个 case 执行指定 metrics，返回 per-case 结果列表。

        ``actual_outputs``（可选、与 cases 等长）是目标（Agent/RAG）对每个
        case 的真实输出。提供时它是被评估的 response；缺省时回退到
        ``case.expected_output``（dataset-only 模式）。

        ``evidence``（可选、与 cases 等长）是 canonical candidate evidence
        （``evaluation.evidence.EvaluationEvidence``）。提供时
        ``retrieved_contexts`` 只来自 evidence 的 successful retrieval
        attempts；缺省时 provider 回退到 ``case.context``（dataset-only 模式，
        数据集 expectation 字段，不是 candidate 检索证据）。
        """
        ...
