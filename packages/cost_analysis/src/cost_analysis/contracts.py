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


# ── RuntimeEvent v2 成本记录 ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CostRecord:
    """单次 LLM 调用的成本记录。

    由 CostProjector 从 LLMCallCompleted 事件生成。
    关联到 run_id / trace_id 以支持 cost per run / agent / workflow。
    """
    run_id: str
    trace_id: str
    span_id: str
    agent_key: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    estimated_cost: float
    started_at_utc: datetime
    completed_at_utc: datetime
    error_code: str | None = None
    error_message: str | None = None
