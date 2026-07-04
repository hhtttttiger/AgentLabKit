from __future__ import annotations

from datetime import datetime

from pydantic import Field

from common.schemas import CamelModel


# ── 概览 ──────────────────────────────────────────────────────────────


class CostOverviewResponse(CamelModel):
    total_spend: float
    total_requests: int
    total_tokens: int
    avg_latency_ms: float
    period_start: datetime
    period_end: datetime
    prev_total_spend: float
    prev_total_requests: int
    spend_change_pct: float
    top_models: list[CostBreakdownItem]
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0


class CostBreakdownItem(CamelModel):
    scope: str
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost: float
    avg_latency_ms: float
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0


# ── 趋势 ──────────────────────────────────────────────────────────────


class CostTrendPointResponse(CamelModel):
    period: str
    total_cost: float
    total_tokens: int
    request_count: int
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0


# ── 预算 CRUD ─────────────────────────────────────────────────────────


class BudgetCreateRequest(CamelModel):
    scope_type: str = Field(pattern="^(global|model|agent|user)$")
    scope_key: str = Field(default="*", max_length=128)
    monthly_limit_usd: float = Field(gt=0)
    alert_threshold_pct: float = Field(default=80, ge=0, le=100)
    is_enabled: bool = True


class BudgetUpdateRequest(CamelModel):
    monthly_limit_usd: float | None = Field(default=None, gt=0)
    alert_threshold_pct: float | None = Field(default=None, ge=0, le=100)
    is_enabled: bool | None = None


class BudgetResponse(CamelModel):
    id: int
    scope_type: str
    scope_key: str
    monthly_limit_usd: float
    alert_threshold_pct: float
    is_enabled: bool
    created_at_utc: datetime
    updated_at_utc: datetime


# ── 告警 ──────────────────────────────────────────────────────────────


class AlertResponse(CamelModel):
    id: int
    budget_id: int
    scope_type: str
    scope_key: str
    alert_type: str
    current_spend_usd: float
    threshold_usd: float
    triggered_at_utc: datetime
    acknowledged_at_utc: datetime | None = None
