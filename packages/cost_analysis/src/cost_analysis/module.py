"""CostAnalysisModule — 遵循项目统一的 Module 模式。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .config import CostAnalysisSettings
from .aggregator import CostAggregator
from .budget import BudgetManager


@dataclass(slots=True)
class CostAnalysisModule:
    settings: CostAnalysisSettings
    aggregator: CostAggregator
    budget_manager: BudgetManager


def create_cost_analysis_module(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: CostAnalysisSettings | None = None,
) -> CostAnalysisModule:
    """工厂函数：创建 CostAnalysisModule 实例。

    Parameters
    ----------
    session_factory:
        async_sessionmaker 实例，用于创建数据库会话。
    settings:
        可选配置，默认从环境变量读取。
    """
    settings = settings or CostAnalysisSettings()
    aggregator = CostAggregator(session_factory)
    budget_manager = BudgetManager(session_factory)
    return CostAnalysisModule(
        settings=settings,
        aggregator=aggregator,
        budget_manager=budget_manager,
    )
