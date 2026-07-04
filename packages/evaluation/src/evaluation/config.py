from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class EvaluationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVALUATION_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    enabled: bool = True
    default_judge_model: str = ""
    """LLM-as-Judge 使用的模型 binding key。留空则使用默认。"""
    max_concurrent_cases: int = 5
    """并发评估的最大用例数。"""
