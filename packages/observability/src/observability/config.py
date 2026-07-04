from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OBSERVABILITY_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    enabled: bool = True
    """是否启用链路追踪。"""
    max_spans_per_trace: int = 500
    """单条 trace 最大 span 数，防止异常场景写入过多。"""
