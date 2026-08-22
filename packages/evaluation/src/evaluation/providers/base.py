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
    ) -> list[EvalRunResult]:
        """批量评估：对每个 case 执行指定 metrics，返回 per-case 结果列表。"""
        ...
