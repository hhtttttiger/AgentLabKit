"""EvaluationModule — 遵循项目统一的 Module 模式。"""

from __future__ import annotations

from dataclasses import dataclass

from .config import EvaluationSettings
from .runner import EvaluationRunner
from .judge import Judge
from .contracts import TargetExecutor
from .providers.registry import ProviderRegistry


@dataclass(slots=True)
class EvaluationModule:
    settings: EvaluationSettings
    runner: EvaluationRunner
    judge: Judge | None
    target_executor: TargetExecutor | None = None
    provider_registry: ProviderRegistry | None = None


def create_evaluation_module(
    *,
    judge: Judge | None = None,
    target_executor: TargetExecutor | None = None,
    settings: EvaluationSettings | None = None,
    provider_registry: ProviderRegistry | None = None,
    provider_name: str | None = None,
) -> EvaluationModule:
    """工厂函数：创建 EvaluationModule 实例。

    调用方（后端 main.py）负责提供具体的 Judge 和 TargetExecutor 实现。
    评估包本身不依赖 llm_gateway 或 agent_runtime。

    Args:
        judge: LLM-as-Judge 实例（legacy 模式）。
        target_executor: 评估目标执行器。
        settings: 评估配置。
        provider_registry: Provider 注册表（provider 模式）。
        provider_name: 指定 provider 名称，不传则使用默认。
    """
    settings = settings or EvaluationSettings()

    runner = EvaluationRunner(
        judge=judge,
        max_concurrent=settings.max_concurrent_cases,
        provider_registry=provider_registry,
        provider_name=provider_name,
    )

    return EvaluationModule(
        settings=settings,
        runner=runner,
        judge=judge,
        target_executor=target_executor,
        provider_registry=provider_registry,
    )
