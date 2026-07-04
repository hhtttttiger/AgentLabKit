from __future__ import annotations

from functools import lru_cache

from .config import GatewaySettings
from .core.registry import ProviderAdapterBundle, ProviderRegistry
from .core.service import GatewayService
from .model_catalog import (
    EnvironmentSecretResolver,
    InMemoryCatalogCache,
    InstanceSecretResolver,
    ModelCatalogService,
    ModelResolver,
    NoOpCatalogCache,
    SqlAlchemyModelCatalogRepository,
    StaticModelCatalogRepository,
    snapshot_from_model_definitions,
)
from .model_catalog.session import create_catalog_session_factory
from .models import ProviderId
from .observability import GatewayObservability
from .usage.recorder import NullUsageRecorder, SqlAlchemyUsageRecorder
from .providers.openai.embedding import OpenAIEmbeddingAdapter
from .providers.openai.image import OpenAIImageAdapter
from .providers.openai.realtime import OpenAIRealtimeAdapter
from .providers.openai.speech import OpenAISpeechBatchAdapter, OpenAISpeechStreamAdapter
from .providers.openai.text import OpenAITextAdapter
from .providers.anthropic.text import AnthropicTextAdapter


def _build_secret_resolver(settings: GatewaySettings):
    """Assemble runtime secret resolution for instance-level encrypted API keys."""
    fallback = None
    if settings.catalog.enable_static_fallback:
        fallback = EnvironmentSecretResolver(
            defaults=settings.openai,
        )

    return InstanceSecretResolver(
        encryption_key=settings.instance_encryption.encryption_key,
        fallback=fallback,
    )


def _create_cache(settings: GatewaySettings):
    if settings.catalog.cache_backend == "memory":
        return InMemoryCatalogCache(ttl_seconds=settings.catalog.refresh_ttl_seconds)
    return NoOpCatalogCache()


def _create_catalog_service(settings: GatewaySettings) -> tuple[ModelCatalogService, ModelResolver]:
    repository: ModelCatalogRepository | None = None
    if settings.catalog.database_url:
        repository = SqlAlchemyModelCatalogRepository(
            create_catalog_session_factory(settings.catalog.database_url)
        )
    elif settings.catalog.enable_static_fallback:
        repository = StaticModelCatalogRepository(
            snapshot_from_model_definitions(settings.models)
        )
    else:
        raise ValueError(
            "Gateway catalog database_url is not configured and static fallback is disabled."
        )

    cache = _create_cache(settings)
    catalog_service = ModelCatalogService(repository, cache=cache)
    secret_resolver = _build_secret_resolver(settings)
    resolver = ModelResolver(catalog_service, secret_resolver)
    return catalog_service, resolver


def create_gateway_service(settings: GatewaySettings | None = None) -> GatewayService:
    gateway_settings = settings or GatewaySettings()
    redis_metrics = None
    if gateway_settings.redis_metrics.enabled:
        try:
            from redis.asyncio import from_url as redis_from_url

            from .observability import RedisMetrics

            redis_client = redis_from_url(gateway_settings.redis_metrics.url)
            redis_metrics = RedisMetrics(
                redis_client,
                key_prefix=gateway_settings.redis_metrics.key_prefix,
            )
        except ImportError:
            import logging

            logging.getLogger(__name__).warning(
                "Redis metrics enabled but redis[hiredis] is not installed. "
                "Install with: pip install agentlabkit-llm-gateway[redis]"
            )
    observability = GatewayObservability(
        metrics=GatewayMetrics(redis_metrics=redis_metrics) if redis_metrics else None,
    )
    registry = ProviderRegistry()
    catalog_service, resolver = _create_catalog_service(gateway_settings)
    if gateway_settings.catalog.database_url:
        usage_session_factory = create_catalog_session_factory(gateway_settings.catalog.database_url)
        usage_recorder = SqlAlchemyUsageRecorder(usage_session_factory)
    else:
        usage_recorder = NullUsageRecorder()
    openai_speech_batch = OpenAISpeechBatchAdapter(gateway_settings.openai)
    registry.register(
        ProviderAdapterBundle(
            provider=ProviderId.OPENAI,
            embedding=OpenAIEmbeddingAdapter(gateway_settings.openai),
            text=OpenAITextAdapter(gateway_settings.openai),
            speech_batch=openai_speech_batch,
            speech_stream=OpenAISpeechStreamAdapter(gateway_settings.openai),
            image=OpenAIImageAdapter(gateway_settings.openai),
            realtime=OpenAIRealtimeAdapter(
                provider=ProviderId.OPENAI,
                secrets=gateway_settings.openai,
            ),
        )
    )
    registry.register(
        ProviderAdapterBundle(
            provider=ProviderId.ANTHROPIC,
            text=AnthropicTextAdapter(gateway_settings.anthropic),
        )
    )
    return GatewayService(
        gateway_settings,
        registry,
        resolver,
        catalog_service,
        observability=observability,
        usage_recorder=usage_recorder,
    )


@lru_cache(maxsize=1)
def build_gateway_service() -> GatewayService:
    return create_gateway_service()
