from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from ..models import CatalogModelSummary
from ..provider_runtime import RuntimeProviderConfig
from .cache import CatalogCache, NoOpCatalogCache
from .domain import ModelCatalogSnapshot, ResolvedModelRoute
from .errors import CatalogError, CatalogErrorCode
from ..models import Capability
from .repository import ModelCatalogRepository
from .retry_policy import RetryPolicy
from .secret_resolver import SecretResolver

_BASE_URL_KEYS = ("endpointUrl", "endpointURL", "instanceUrl", "url", "baseUrl")
_WEBSOCKET_URL_KEYS = ("webSocketBaseUrl", "websocketBaseUrl", "wsBaseUrl")


class ModelCatalogService:
    def __init__(
        self,
        repository: ModelCatalogRepository,
        *,
        cache: CatalogCache | None = None,
    ) -> None:
        self._repository = repository
        self._cache = cache or NoOpCatalogCache()

    async def get_snapshot(self, *, force_refresh: bool = False) -> ModelCatalogSnapshot:
        if not force_refresh and (cached := await self._cache.get()) is not None:
            return cached
        snapshot = await self._repository.load_snapshot()
        await self._cache.set(snapshot)
        return snapshot

    async def list_models(self) -> list[CatalogModelSummary]:
        snapshot = await self.get_snapshot()
        binding_map: dict[str, list[str]] = defaultdict(list)
        for binding in snapshot.bindings:
            binding_map[binding.model_key].append(binding.binding_key)
        summaries: list[CatalogModelSummary] = []
        for model in snapshot.models:
            providers = {
                snapshot.connection_profiles_by_key[instance.connection_profile_key].provider
                for instance in model.instances
                if instance.connection_profile_key in snapshot.connection_profiles_by_key
            }
            summaries.append(
                CatalogModelSummary(
                    model_key=model.model_key,
                    display_name=model.display_name,
                    enabled=model.is_enabled,
                    capabilities=set(model.capabilities),
                    providers=providers,
                    binding_keys=sorted(binding_map.get(model.model_key, [])),
                )
            )
        return summaries


_DEFAULT_BINDING_KEYS: dict[Capability, str] = {
    Capability.TEXT: "gateway.default_text",
    Capability.EMBEDDING: "gateway.default_embedding",
    Capability.SPEECH_BATCH: "gateway.default_speech_batch",
    Capability.SPEECH_STREAM: "gateway.default_speech_stream",
    Capability.IMAGE: "gateway.default_image",
    Capability.REALTIME: "gateway.default_realtime",
}


class ModelResolver:
    def __init__(
        self,
        catalog_service: ModelCatalogService,
        secret_resolver: SecretResolver,
    ) -> None:
        self._catalog_service = catalog_service
        self._secret_resolver = secret_resolver

    async def resolve_for_capability(
        self,
        capability: Capability,
        model_key: str | None = None,
        provider_hint=None,
        required_features: Mapping[str, Any] | None = None,
    ) -> ResolvedModelRoute:
        """Resolve the best route for a given capability using the default binding."""
        binding_key = _DEFAULT_BINDING_KEYS[capability]
        return await self.resolve(
            binding_key,
            model_key=model_key,
            provider_hint=provider_hint,
            required_features=required_features,
            capability=capability,
        )

    async def resolve_binding(
        self,
        binding_key: str,
        *,
        provider_hint=None,
        required_features: Mapping[str, Any] | None = None,
    ) -> ResolvedModelRoute:
        return await self.resolve(
            binding_key,
            model_key=None,
            provider_hint=provider_hint,
            required_features=required_features,
        )

    async def resolve(
        self,
        binding_key: str,
        *,
        model_key: str | None,
        provider_hint,
        required_features: Mapping[str, Any] | None = None,
        capability: Capability | None = None,
    ) -> ResolvedModelRoute:
        routes, _ = await self.resolve_candidates(
            binding_key,
            model_key=model_key,
            provider_hint=provider_hint,
            required_features=required_features,
            capability=capability,
        )
        return routes[0]

    async def resolve_candidates(
        self,
        binding_key: str,
        *,
        model_key: str | None,
        provider_hint,
        required_features: Mapping[str, Any] | None = None,
        capability: Capability | None = None,
    ) -> tuple[list[ResolvedModelRoute], RetryPolicy]:
        """Return an ordered list of candidate routes and the model's retry policy.

        The first element is the highest-priority route (same as :meth:`resolve`
        would return).  Callers can iterate the remaining candidates as fallback
        options on failure.
        """
        snapshot = await self._catalog_service.get_snapshot()

        # Reconcile callers that pass a *binding* key via the model field.
        # agent_runtime maps agent.model_binding_key → request.model, so a value
        # like "mimo-v2-flash-chat" (a binding) reaches us as model_key. If the
        # supplied value is not a real model key but names a registered binding,
        # honour the binding and derive the real model_key from it. Purely
        # additive fallback — only changes behaviour when model_key is an actual
        # binding key; genuine model keys are unaffected.
        if (
            model_key is not None
            and model_key not in snapshot.models_by_key
            and model_key in snapshot.bindings_by_key
        ):
            binding_key = model_key
            model_key = snapshot.bindings_by_key[binding_key].model_key

        binding = snapshot.bindings_by_key.get(binding_key)

        # When model_key is provided, allow direct resolution without a binding.
        if model_key is not None and (binding is None or not binding.is_enabled):
            if capability is None:
                raise CatalogError(
                    CatalogErrorCode.BINDING_NOT_FOUND,
                    f"Binding '{binding_key}' was not found.",
                    binding_key=binding_key,
                )
            # Synthesize a minimal binding for direct model invocation.
            from .domain import ModelBindingSnapshot, freeze_mapping
            binding = ModelBindingSnapshot(
                binding_key=binding_key,
                display_name=binding_key,
                capability=capability,
                model_key=model_key,
                metadata=freeze_mapping(),
                is_enabled=True,
            )
        elif binding is None or not binding.is_enabled:
            raise CatalogError(
                CatalogErrorCode.BINDING_NOT_FOUND,
                f"Binding '{binding_key}' was not found.",
                binding_key=binding_key,
            )

        effective_model_key = model_key or binding.model_key
        model = snapshot.models_by_key.get(effective_model_key)
        if model is None or not model.is_enabled:
            raise CatalogError(
                CatalogErrorCode.MODEL_NOT_FOUND,
                f"Model '{effective_model_key}' was not found.",
                model_key=effective_model_key,
            )

        candidates = []
        supported_providers = {
            snapshot.connection_profiles_by_key[instance.connection_profile_key].provider
            for instance in model.instances
            if instance.connection_profile_key in snapshot.connection_profiles_by_key
        }
        for instance in model.instances:
            profile = snapshot.connection_profiles_by_key.get(instance.connection_profile_key)
            if instance.capability != binding.capability:
                continue
            if profile is None:
                continue
            if not instance.is_enabled or not instance.is_healthy or not profile.is_enabled:
                continue
            if provider_hint is not None and profile.provider != provider_hint:
                continue
            candidates.append((instance, profile))

        if provider_hint is not None and supported_providers and provider_hint not in supported_providers:
            raise CatalogError(
                CatalogErrorCode.PROVIDER_CONFLICT,
                f"Model '{effective_model_key}' does not support provider '{provider_hint.value}'.",
                model_key=effective_model_key,
                provider=provider_hint.value,
            )

        if not candidates:
            raise CatalogError(
                CatalogErrorCode.NO_ENABLED_INSTANCE,
                f"Model '{effective_model_key}' has no enabled instance for capability '{binding.capability.value}'.",
                model_key=effective_model_key,
            )

        if required_features and not _matches_required_features(model, required_features):
            raise CatalogError(
                CatalogErrorCode.FEATURE_REQUIREMENT_NOT_SATISFIED,
                f"Model '{effective_model_key}' does not satisfy the requested features.",
                model_key=effective_model_key,
            )

        # Group by priority, then apply weighted random selection within each tier.
        # Lower priority values are tried first.  Within a tier, the primary
        # candidate is chosen by weight (higher weight = more likely), and the
        # remaining instances are shuffled for diverse fallback ordering.
        import random
        from collections import defaultdict

        by_priority: dict[int, list[tuple[Any, Any]]] = defaultdict(list)
        for instance, profile in candidates:
            by_priority[instance.priority].append((instance, profile))

        ordered: list[tuple[Any, Any]] = []
        for _priority in sorted(by_priority):
            tier = by_priority[_priority]
            if len(tier) <= 1:
                ordered.extend(tier)
            else:
                weights = [item[0].weight for item in tier]
                primary_idx = random.choices(range(len(tier)), weights=weights, k=1)[0]
                remainder = [item for i, item in enumerate(tier) if i != primary_idx]
                random.shuffle(remainder)
                ordered.append(tier[primary_idx])
                ordered.extend(remainder)

        routes: list[ResolvedModelRoute] = []
        for instance, profile in ordered:
            resolved_config = await self._secret_resolver.resolve(profile, instance)
            endpoint_url = _read_instance_extra(instance.extra, _BASE_URL_KEYS)
            websocket_base_url = _read_instance_extra(instance.extra, _WEBSOCKET_URL_KEYS)
            runtime_config = RuntimeProviderConfig(
                api_key=resolved_config.api_key,
                base_url=endpoint_url or profile.base_url or resolved_config.base_url,
                websocket_base_url=websocket_base_url or profile.websocket_base_url or resolved_config.websocket_base_url,
                api_version=profile.api_version or resolved_config.api_version,
                organization=resolved_config.organization,
                project=resolved_config.project,
                region=instance.region or profile.region or resolved_config.region,
            )
            routes.append(
                ResolvedModelRoute(
                    model_key=model.model_key,
                    instance_key=instance.instance_key,
                    capability=instance.capability,
                    provider=profile.provider,
                    provider_model_name=instance.provider_model_name,
                    provider_deployment_name=instance.provider_deployment_name,
                    default_timeout_ms=instance.default_timeout_ms,
                    runtime_config=runtime_config,
                    extra=instance.extra,
                    catalog_revision=snapshot.revision,
                    input_price_per_mtok=model.input_price_per_mtok,
                    output_price_per_mtok=model.output_price_per_mtok,
                    cache_write_price_per_mtok=model.cache_write_price_per_mtok,
                    cache_read_price_per_mtok=model.cache_read_price_per_mtok,
                )
            )

        retry_policy = RetryPolicy.from_json(model.retry_policy)
        return routes, retry_policy

    async def resolve_binding_model_key(self, binding_key: str, provider_hint=None) -> str:
        route = await self.resolve_binding(binding_key, provider_hint=provider_hint)
        return route.model_key


def _matches_required_features(model, required_features: Mapping[str, Any]) -> bool:
    features_by_key = {feature.feature_key: feature for feature in model.features}
    for feature_key, expected_value in required_features.items():
        feature = features_by_key.get(feature_key)
        if not _feature_satisfies_requirement(feature, expected_value):
            return False
    return True


def _feature_satisfies_requirement(feature, expected_value: Any) -> bool:
    if feature is None or not feature.is_enabled or not feature.is_routable or not feature.is_supported:
        return False
    if feature.allowed_values and (expected_value not in feature.allowed_values or feature.value not in feature.allowed_values):
        return False
    return feature.value == expected_value


def _read_instance_extra(
    extra: Mapping[str, Any] | None,
    keys: tuple[str, ...],
) -> str | None:
    if not extra:
        return None

    for key in keys:
        value = extra.get(key)
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed

    return None
