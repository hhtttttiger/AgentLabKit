"""EvaluationModule — 遵循项目统一的 Module 模式。"""

from __future__ import annotations

from dataclasses import dataclass

from .config import EvaluationSettings
from .runner import EvaluationRunner
from .judge import Judge
from .contracts import TargetExecutor


@dataclass(slots=True)
class EvaluationModule:
    settings: EvaluationSettings
    runner: EvaluationRunner
    judge: Judge | None
    target_executor: TargetExecutor | None = None


def create_evaluation_module(
    *,
    judge: Judge | None = None,
    target_executor: TargetExecutor | None = None,
    settings: EvaluationSettings | None = None,
) -> EvaluationModule:
    """工厂函数：创建 EvaluationModule 实例。

    调用方（后端 main.py）负责提供具体的 Judge 和 TargetExecutor 实现。
    评估包本身不依赖 llm_gateway 或 agent_runtime。
    """
    settings = settings or EvaluationSettings()

    runner = EvaluationRunner(
        judge=judge,
        max_concurrent=settings.max_concurrent_cases,
    )

    return EvaluationModule(
        settings=settings,
        runner=runner,
        judge=judge,
        target_executor=target_executor,
    )
