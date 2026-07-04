from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QueueSettings(BaseSettings):
    """Queue settings.

    All settings can be overridden via environment variables with the
    ``AFQUEUE_`` prefix, e.g. ``AFQUEUE_DEFAULT_MAX_RETRIES=5``.
    """

    model_config = SettingsConfigDict(
        env_prefix="AFQUEUE_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    default_max_retries: int = Field(default=3, ge=0)
    default_retry_delay_seconds: float = Field(default=5.0, ge=1.0)
    default_max_length: int = Field(default=10_000, ge=1)
    consumer_batch_size: int = Field(default=10, ge=1, le=100)
    consumer_poll_timeout_ms: int = Field(default=5000, ge=100)
    scheduler_poll_interval_seconds: float = Field(default=1.0, ge=0.1)
    claim_min_idle_ms: int = Field(default=30_000, ge=1000)
