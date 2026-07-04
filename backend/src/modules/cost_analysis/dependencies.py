"""成本分析依赖注入 — 从 app.state 取出 CostAnalysisModule。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from common.dependencies import DbSession
from cost_analysis import CostAnalysisModule, BudgetManager
from cost_analysis.aggregator import CostAggregator
from .services.budget_service import BudgetService


def get_cost_module(request: Request) -> CostAnalysisModule:
    mod: CostAnalysisModule | None = getattr(request.app.state, "cost_analysis_module", None)
    if mod is None:
        raise RuntimeError("CostAnalysisModule not initialized — check lifespan wiring")
    return mod


def get_aggregator(mod: CostAnalysisModule = Depends(get_cost_module)) -> CostAggregator:
    return mod.aggregator


def get_budget_manager(mod: CostAnalysisModule = Depends(get_cost_module)) -> BudgetManager:
    return mod.budget_manager


def get_budget_service(db: DbSession) -> BudgetService:
    return BudgetService(db)


AggregatorDep = Annotated[CostAggregator, Depends(get_aggregator)]
BudgetManagerDep = Annotated[BudgetManager, Depends(get_budget_manager)]
BudgetServiceDep = Annotated[BudgetService, Depends(get_budget_service)]
