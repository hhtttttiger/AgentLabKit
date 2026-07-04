from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import Capability, ModelDefinition, ProviderId


def default_model_definitions() -> list[ModelDefinition]:
    """Default model definitions for static fallback mode.

    [Deprecated] Only used when enable_static_fallback=True (test/bootstrap).
    Production deployments should use the database catalog.
    """
    return [
        ModelDefinition(
            model_key="gpt-5.4-mini",
            provider=ProviderId.OPENAI,
            provider_model_name="gpt-5.4-mini",
            capabilities={Capability.TEXT},
        ),
        ModelDefinition(
            model_key="gpt-4o-mini-transcribe",
            provider=ProviderId.OPENAI,
            provider_model_name="gpt-4o-mini-transcribe",
            capabilities={Capability.SPEECH_BATCH, Capability.SPEECH_STREAM},
        ),
        ModelDefinition(
            model_key="gpt-image-2",
            provider=ProviderId.OPENAI,
            provider_model_name="gpt-image-2",
            capabilities={Capability.IMAGE},
        ),
        ModelDefinition(
            model_key="gpt-realtime-2",
            provider=ProviderId.OPENAI,
            provider_model_name="gpt-realtime-2",
            capabilities={Capability.TEXT, Capability.REALTIME, Capability.SPEECH_STREAM},
        ),
        ModelDefinition(
            model_key="claude-sonnet-4-20250514",
            provider=ProviderId.ANTHROPIC,
            provider_model_name="claude-sonnet-4-20250514",
            capabilities={Capability.TEXT},
        ),
        ModelDefinition(
            model_key="claude-haiku-4-20250514",
            provider=ProviderId.ANTHROPIC,
            provider_model_name="claude-haiku-4-20250514",
            capabilities={Capability.TEXT},
        ),
    ]


class ProviderConfig(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    websocket_base_url: str | None = None
    api_version: str | None = None


class RedisMetricsSettings(BaseModel):
    enabled: bool = False
    url: str = "redis://localhost:6379/0"
    key_prefix: str = "ai_gateway"


class InstanceEncryptionSettings(BaseModel):
    encryption_key: str | None = None


class ModelCatalogSettings(BaseModel):
    backend: str = "database"
    database_url: str | None = None
    enable_static_fallback: bool = False
    cache_backend: str = "noop"
    refresh_ttl_seconds: int = 30
    secret_resolution_mode: str = "instance_only"

    from pydantic import model_validator

    @model_validator(mode="after")
    def _validate_secret_resolution_mode(self):
        from .model_catalog.secret_resolver import SecretResolutionMode
        try:
            SecretResolutionMode(self.secret_resolution_mode)
        except ValueError:
            valid = ", ".join(m.value for m in SecretResolutionMode)
            raise ValueError(
                f"Invalid secret_resolution_mode '{self.secret_resolution_mode}'. "
                f"Must be one of: {valid}"
            )
        return self


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AI_GATEWAY_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    catalog: ModelCatalogSettings = Field(default_factory=ModelCatalogSettings)
    instance_encryption: InstanceEncryptionSettings = Field(default_factory=InstanceEncryptionSettings)
    redis_metrics: RedisMetricsSettings = Field(default_factory=RedisMetricsSettings)
    models: list[ModelDefinition] = Field(default_factory=default_model_definitions)
