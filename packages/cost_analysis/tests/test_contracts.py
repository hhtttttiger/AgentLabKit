"""Cost Analysis contracts 测试 — Phase 0 安全网。

覆盖：dataclass 构造、枚举值、边界条件。
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cost_analysis.contracts import (
    BudgetScopeType,
    CostAlertInfo,
    CostBreakdown,
    CostOverview,
    CostTrendPoint,
    Granularity,
    BudgetStatus,
)


# ── Enum 值 ────────────────────────────────────────────────────────


class TestEnums:
    def test_budget_scope_values(self) -> None:
        assert BudgetScopeType.GLOBAL.value == "global"
        assert BudgetScopeType.MODEL.value == "model"
        assert BudgetScopeType.AGENT.value == "agent"
        assert BudgetScopeType.USER.value == "user"

    def test_granularity_values(self) -> None:
        assert Granularity.DAY.value == "day"
        assert Granularity.WEEK.value == "week"
        assert Granularity.MONTH.value == "month"

    def test_budget_scope_from_string(self) -> None:
        assert BudgetScopeType("model") == BudgetScopeType.MODEL

    def test_invalid_scope_raises(self) -> None:
        with pytest.raises(ValueError):
            BudgetScopeType("nonexistent")


# ── CostBreakdown ──────────────────────────────────────────────────


class TestCostBreakdown:
    def test_construction(self) -> None:
        bd = CostBreakdown(
            scope="gpt-4o",
            total_requests=100,
            total_input_tokens=50000,
            total_output_tokens=10000,
            total_estimated_cost=1.23,
            avg_latency_ms=450.5,
        )
        assert bd.scope == "gpt-4o"
        assert bd.total_requests == 100
        assert bd.total_estimated_cost == 1.23

    def test_frozen(self) -> None:
        bd = CostBreakdown(
            scope="test",
            total_requests=1,
            total_input_tokens=100,
            total_output_tokens=50,
            total_estimated_cost=0.01,
            avg_latency_ms=200.0,
        )
        with pytest.raises(AttributeError):
            bd.scope = "changed"  # type: ignore[misc]

    def test_cache_tokens_default_zero(self) -> None:
        bd = CostBreakdown(
            scope="test",
            total_requests=1,
            total_input_tokens=100,
            total_output_tokens=50,
            total_estimated_cost=0.01,
            avg_latency_ms=200.0,
        )
        assert bd.total_cache_write_tokens == 0
        assert bd.total_cache_read_tokens == 0


# ── CostTrendPoint ─────────────────────────────────────────────────


class TestCostTrendPoint:
    def test_construction(self) -> None:
        pt = CostTrendPoint(
            period="2025-01-15",
            total_cost=5.5,
            total_tokens=10000,
            request_count=42,
        )
        assert pt.period == "2025-01-15"
        assert pt.total_cost == 5.5
        assert pt.request_count == 42


# ── CostOverview ───────────────────────────────────────────────────


class TestCostOverview:
    def test_construction(self) -> None:
        now = datetime.now(timezone.utc)
        ov = CostOverview(
            total_spend=100.0,
            total_requests=500,
            total_tokens=100000,
            avg_latency_ms=300.0,
            period_start=now,
            period_end=now,
            prev_total_spend=80.0,
            prev_total_requests=400,
            spend_change_pct=25.0,
            top_models=[],
        )
        assert ov.total_spend == 100.0
        assert ov.spend_change_pct == 25.0

    def test_spend_change_can_be_negative(self) -> None:
        now = datetime.now(timezone.utc)
        ov = CostOverview(
            total_spend=60.0,
            total_requests=300,
            total_tokens=50000,
            avg_latency_ms=250.0,
            period_start=now,
            period_end=now,
            prev_total_spend=80.0,
            prev_total_requests=400,
            spend_change_pct=-25.0,
            top_models=[],
        )
        assert ov.spend_change_pct == -25.0


# ── BudgetStatus ───────────────────────────────────────────────────


class TestBudgetStatus:
    def test_under_budget(self) -> None:
        bs = BudgetStatus(
            scope_type=BudgetScopeType.MODEL,
            scope_key="gpt-4o",
            monthly_limit_usd=100.0,
            current_spend_usd=75.0,
            usage_pct=75.0,
            alert_threshold_pct=80.0,
            is_over_budget=False,
        )
        assert bs.is_over_budget is False
        assert bs.usage_pct == 75.0

    def test_over_budget(self) -> None:
        bs = BudgetStatus(
            scope_type=BudgetScopeType.GLOBAL,
            scope_key="*",
            monthly_limit_usd=100.0,
            current_spend_usd=105.0,
            usage_pct=105.0,
            alert_threshold_pct=80.0,
            is_over_budget=True,
        )
        assert bs.is_over_budget is True


# ── CostAlertInfo ──────────────────────────────────────────────────


class TestCostAlertInfo:
    def test_threshold_alert(self) -> None:
        now = datetime.now(timezone.utc)
        alert = CostAlertInfo(
            id=123,
            budget_id=1,
            scope_type=BudgetScopeType.MODEL,
            scope_key="gpt-4o",
            alert_type="threshold",
            current_spend_usd=85.0,
            threshold_usd=80.0,
            triggered_at_utc=now,
            acknowledged_at_utc=None,
        )
        assert alert.alert_type == "threshold"
        assert alert.acknowledged_at_utc is None

    def test_exceeded_alert(self) -> None:
        now = datetime.now(timezone.utc)
        alert = CostAlertInfo(
            id=456,
            budget_id=1,
            scope_type=BudgetScopeType.GLOBAL,
            scope_key="*",
            alert_type="exceeded",
            current_spend_usd=110.0,
            threshold_usd=100.0,
            triggered_at_utc=now,
            acknowledged_at_utc=None,
        )
        assert alert.alert_type == "exceeded"
