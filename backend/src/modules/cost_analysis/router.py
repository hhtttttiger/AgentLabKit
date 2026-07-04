"""成本分析 API Router — 成本概览、分项明细、趋势、预算、告警。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from common.response import ok
from .dependencies import AggregatorDep, BudgetManagerDep, BudgetServiceDep
from .schemas import (
    BudgetCreateRequest,
    BudgetUpdateRequest,
    BudgetResponse,
    AlertResponse,
    CostOverviewResponse,
    CostBreakdownItem,
    CostTrendPointResponse,
)

router = APIRouter()


# ── 概览 ─────────────────────────────────────────────────────────────


@router.get("/overview")
async def cost_overview(
    agg: AggregatorDep,
    days: int = Query(30, ge=1, le=365),
):
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=days)
    data = await agg.get_overview(from_date=from_date, to_date=to_date)
    return ok(CostOverviewResponse(
        total_spend=data.total_spend,
        total_requests=data.total_requests,
        total_tokens=data.total_tokens,
        avg_latency_ms=data.avg_latency_ms,
        period_start=data.period_start,
        period_end=data.period_end,
        prev_total_spend=data.prev_total_spend,
        prev_total_requests=data.prev_total_requests,
        spend_change_pct=data.spend_change_pct,
        top_models=[
            CostBreakdownItem(
                scope=b.scope,
                total_requests=b.total_requests,
                total_input_tokens=b.total_input_tokens,
                total_output_tokens=b.total_output_tokens,
                total_estimated_cost=b.total_estimated_cost,
                avg_latency_ms=b.avg_latency_ms,
                total_cache_write_tokens=b.total_cache_write_tokens,
                total_cache_read_tokens=b.total_cache_read_tokens,
            )
            for b in data.top_models
        ],
        total_cache_write_tokens=data.total_cache_write_tokens,
        total_cache_read_tokens=data.total_cache_read_tokens,
    ).model_dump())


# ── 分项明细 ─────────────────────────────────────────────────────────


@router.get("/breakdown/by-model")
async def breakdown_by_model(
    agg: AggregatorDep,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
):
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=days)
    items = await agg.get_breakdown_by_model(from_date=from_date, to_date=to_date, limit=limit)
    return ok([CostBreakdownItem(
        scope=i.scope,
        total_requests=i.total_requests,
        total_input_tokens=i.total_input_tokens,
        total_output_tokens=i.total_output_tokens,
        total_estimated_cost=i.total_estimated_cost,
        avg_latency_ms=i.avg_latency_ms,
        total_cache_write_tokens=i.total_cache_write_tokens,
        total_cache_read_tokens=i.total_cache_read_tokens,
    ).model_dump() for i in items])


@router.get("/breakdown/by-capability")
async def breakdown_by_capability(
    agg: AggregatorDep,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
):
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=days)
    items = await agg.get_breakdown_by_capability(from_date=from_date, to_date=to_date, limit=limit)
    return ok([CostBreakdownItem(
        scope=i.scope,
        total_requests=i.total_requests,
        total_input_tokens=i.total_input_tokens,
        total_output_tokens=i.total_output_tokens,
        total_estimated_cost=i.total_estimated_cost,
        avg_latency_ms=i.avg_latency_ms,
        total_cache_write_tokens=i.total_cache_write_tokens,
        total_cache_read_tokens=i.total_cache_read_tokens,
    ).model_dump() for i in items])


# ── 趋势 ─────────────────────────────────────────────────────────────


@router.get("/trend")
async def cost_trend(
    agg: AggregatorDep,
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    days: int = Query(30, ge=1, le=365),
):
    from cost_analysis.contracts import Granularity

    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=days)
    points = await agg.get_cost_trend(
        granularity=Granularity(granularity),
        from_date=from_date,
        to_date=to_date,
    )
    return ok([
        CostTrendPointResponse(
            period=p.period,
            total_cost=p.total_cost,
            total_tokens=p.total_tokens,
            request_count=p.request_count,
            total_cache_write_tokens=p.total_cache_write_tokens,
            total_cache_read_tokens=p.total_cache_read_tokens,
        ).model_dump()
        for p in points
    ])


# ── 预算 CRUD ────────────────────────────────────────────────────────


@router.get("/budgets")
async def list_budgets(svc: BudgetServiceDep):
    return ok(await svc.list_budgets())


@router.post("/budgets")
async def create_budget(body: BudgetCreateRequest, svc: BudgetServiceDep):
    return ok(await svc.create_budget(**body.model_dump(by_alias=False)))


@router.put("/budgets/{budget_id}")
async def update_budget(budget_id: int, body: BudgetUpdateRequest, svc: BudgetServiceDep):
    return ok(await svc.update_budget(budget_id, **body.model_dump(exclude_none=True, by_alias=False)))


@router.delete("/budgets/{budget_id}")
async def delete_budget(budget_id: int, svc: BudgetServiceDep):
    await svc.delete_budget(budget_id)
    return ok(None)


# ── 告警 ─────────────────────────────────────────────────────────────


@router.get("/alerts")
async def list_alerts(
    bm: BudgetManagerDep,
    acknowledged: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    alerts = await bm.list_alerts(acknowledged=acknowledged, limit=limit)
    return ok([AlertResponse(
        id=a.id,
        budget_id=a.budget_id,
        scope_type=a.scope_type.value,
        scope_key=a.scope_key,
        alert_type=a.alert_type,
        current_spend_usd=a.current_spend_usd,
        threshold_usd=a.threshold_usd,
        triggered_at_utc=a.triggered_at_utc,
        acknowledged_at_utc=a.acknowledged_at_utc,
    ).model_dump() for a in alerts])


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, bm: BudgetManagerDep):
    updated = await bm.acknowledge_alert(alert_id)
    if not updated:
        from common.errors import NotFoundError
        raise NotFoundError("Alert", str(alert_id))
    return ok(None)


@router.post("/alerts/evaluate")
async def evaluate_alerts(bm: BudgetManagerDep):
    """手动触发告警评估（扫描所有预算）。"""
    new_alerts = await bm.evaluate_alerts()
    return ok({"triggered_count": len(new_alerts)})
