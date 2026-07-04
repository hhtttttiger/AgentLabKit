from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CostAnalysisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COST_ANALYSIS_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    enabled: bool = True
    """预算检查是否启用（关闭后仍可查询成本，只是不主动拦截）。"""

    default_alert_threshold_pct: float = 80.0
    """默认告警阈值百分比（0–100）。"""
