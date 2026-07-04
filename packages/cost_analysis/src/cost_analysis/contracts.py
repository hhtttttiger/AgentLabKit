from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class BudgetScopeType(str, Enum):
    GLOBAL = "global"
    MODEL = "model"
    AGENT = "agent"
    USER = "user"


class Granularity(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# ── 查询结果 ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """按某个维度（模型 / Agent / 用户）的成本汇总。"""
    scope: str                    # model_key, agent_key, user_id, ...
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost: float
    avg_latency_ms: float
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0


@dataclass(frozen=True, slots=True)
class CostTrendPoint:
    """时间序列上的一个数据点。"""
    period: str                   # ISO date / week / month label
    total_cost: float
    total_tokens: int
    request_count: int
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0


@dataclass(frozen=True, slots=True)
class CostOverview:
    """成本概览页所需的总览数据。"""
    total_spend: float
    total_requests: int
    total_tokens: int
    avg_latency_ms: float
    period_start: datetime
    period_end: datetime
    # 环比上一周期
    prev_total_spend: float
    prev_total_requests: int
    spend_change_pct: float       # (current - prev) / prev * 100
    top_models: list[CostBreakdown]
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    """某个 scope 下的预算使用情况。"""
    scope_type: BudgetScopeType
    scope_key: str
    monthly_limit_usd: float
    current_spend_usd: float
    usage_pct: float
    alert_threshold_pct: float
    is_over_budget: bool


@dataclass(frozen=True, slots=True)
class CostAlertInfo:
    """一条预算告警记录。"""
    id: int
    budget_id: int
    scope_type: BudgetScopeType
    scope_key: str
    alert_type: str               # "threshold" | "exceeded"
    current_spend_usd: float
    threshold_usd: float
    triggered_at_utc: datetime
    acknowledged_at_utc: datetime | None
