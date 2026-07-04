from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    """Redis connection settings.

    All settings can be overridden via environment variables with the
    ``AFREDIS_`` prefix, e.g. ``AFREDIS_URL=redis://host:6379/1``.
    """

    model_config = SettingsConfigDict(
        env_prefix="AFREDIS_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    url: str = "redis://localhost:6379/0"
    max_connections: int = Field(default=20, ge=1)
    socket_timeout: float = Field(default=5.0, ge=1.0)
    socket_connect_timeout: float = Field(default=3.0, ge=1.0)
    retry_on_timeout: bool = True
    decode_responses: bool = True
