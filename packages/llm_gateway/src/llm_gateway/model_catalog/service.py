from __future__ import annotations

import random
import warnings
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from ..models import CatalogModelSummary, ModelRef
from ..provider_runtime import RuntimeProviderConfig
from .cache import CatalogCache, NoOpCatalogCache
from .domain import ModelBindingSnapshot, ModelCatalogSnapshot, ResolvedModelRoute, freeze_mapping
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
    """Resolves a model reference (binding key / model key / model name) into
    an ordered list of candidate routes for failover.

    Primary entry point: :meth:`resolve` — accepts a :class:`ModelRef` and
    returns ``(routes, retry_policy)``.
    """

    def __init__(
        self,
        catalog_service: ModelCatalogService,
        secret_resolver: SecretResolver,
    ) -> None:
        self._catalog_service = catalog_service
        self._secret_resolver = secret_resolver

    # ── Primary API ───────────────────────────────────────────────────────

    async def resolve(
        self,
        ref: ModelRef,
        *,
        capability_hint: Capability | None = None,
        provider_hint: Any = None,
        required_features: Mapping[str, Any] | None = None,
    ) -> tuple[list[ResolvedModelRoute], RetryPolicy]:
        """Resolve *ref* into ordered candidate routes + retry policy.

        Resolution strategy (first match wins):
        1. ``ref.binding_key`` → lookup in ``bindings_by_key`` → target model
        2. ``ref.model_key``   → lookup in ``models_by_key`` directly
        3. ``ref.model_name``  → lookup in ``models_by_name`` (provider model name)

        Capability is inferred when the target model exposes exactly one; pass
        *capability_hint* when the model supports multiple capabilities.
        """
        snapshot = await self._catalog_service.get_snapshot()
        model, capability, binding = self._resolve_ref(ref, snapshot, capability_hint)
        return await self._build_candidates(
            model=model,
            capability=capability,
            binding=binding,
            snapshot=snapshot,
            provider_hint=provider_hint,
            required_features=required_features,
        )

    # ── Backward-compatible entry ─────────────────────────────────────────

    async def resolve_candidates(
        self,
        binding_key: str,
        *,
        model_key: str | None,
        provider_hint: Any,
        required_features: Mapping[str, Any] | None = None,
        capability: Capability | None = None,
    ) -> tuple[list[ResolvedModelRoute], RetryPolicy]:
        """Backward-compatible entry point.

        .. deprecated::
            Use :meth:`resolve` with a :class:`ModelRef` instead::

                routes, retry = await resolver.resolve(
                    ModelRef.model("gpt-5.4-mini"),
                    capability_hint=Capability.TEXT,
                )
        """
        warnings.warn(
            "resolve_candidates() is deprecated; use resolve(ModelRef, ...) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        snapshot = await self._catalog_service.get_snapshot()

        # Build a ModelRef from the legacy arguments.
        if model_key is not None:
            ref = ModelRef.model(model_key)
        else:
            ref = ModelRef.binding(binding_key)

        model, resolved_capability, binding = self._resolve_ref(
            ref, snapshot, capability,
        )

        # When the caller passed a non-default binding_key that doesn't exist
        # and resolution succeeded via model_key or binding fallback, synthesise
        # a binding so the downstream pipeline has a capability.
        if binding is None:
            if resolved_capability is None:
                raise CatalogError(
                    CatalogErrorCode.BINDING_NOT_FOUND,
                    f"Binding '{binding_key}' was not found.",
                    binding_key=binding_key,
                )
            binding = ModelBindingSnapshot(
                binding_key=binding_key,
                display_name=binding_key,
                capability=resolved_capability,
                model_key=model.model_key,
                metadata=freeze_mapping(),
                is_enabled=True,
            )

        return await self._build_candidates(
            model=model,
            capability=resolved_capability,
            binding=binding,
            snapshot=snapshot,
            provider_hint=provider_hint,
            required_features=required_features,
        )

    # ── Internal resolution ───────────────────────────────────────────────

    def _resolve_ref(
        self,
        ref: ModelRef,
        snapshot: ModelCatalogSnapshot,
        capability_hint: Capability | None,
    ) -> tuple[Any, Capability, ModelBindingSnapshot | None]:
        """Resolve *ref* to ``(model, capability, binding_or_None)``.

        The *binding* is ``None`` when resolution succeeded via model_key or
        model_name (no binding involved).
        """
        if ref.binding_key is not None:
            return self._resolve_binding(ref.binding_key, snapshot, capability_hint)
        if ref.model_key is not None:
            return self._resolve_model_key(ref.model_key, snapshot, capability_hint)
        return self._resolve_model_name(ref.model_name, snapshot, capability_hint)  # type: ignore[arg-type]

    def _resolve_binding(
        self,
        binding_key: str,
        snapshot: ModelCatalogSnapshot,
        capability_hint: Capability | None,
    ) -> tuple[Any, Capability, ModelBindingSnapshot | None]:
        binding = snapshot.bindings_by_key.get(binding_key)
        if binding is None or not binding.is_enabled:
            raise CatalogError(
                CatalogErrorCode.BINDING_NOT_FOUND,
                f"Binding '{binding_key}' was not found.",
                binding_key=binding_key,
            )
        model = snapshot.models_by_key.get(binding.model_key)
        if model is None or not model.is_enabled:
            raise CatalogError(
                CatalogErrorCode.MODEL_NOT_FOUND,
                f"Model '{binding.model_key}' was not found.",
                model_key=binding.model_key,
            )
        return model, binding.capability, binding

    def _resolve_model_key(
        self,
        model_key: str,
        snapshot: ModelCatalogSnapshot,
        capability_hint: Capability | None,
    ) -> tuple[Any, Capability, ModelBindingSnapshot | None]:
        model = snapshot.models_by_key.get(model_key)
        if model is not None and model.is_enabled:
            capability = self._infer_capability(model, capability_hint)
            return model, capability, None

        # Fallback: if the key is actually a binding key (e.g. agent_runtime
        # passes agent.model_key via request.model), resolve via binding.
        binding = snapshot.bindings_by_key.get(model_key)
        if binding is not None and binding.is_enabled:
            bound_model = snapshot.models_by_key.get(binding.model_key)
            if bound_model is not None and bound_model.is_enabled:
                return bound_model, binding.capability, binding

        raise CatalogError(
            CatalogErrorCode.MODEL_NOT_FOUND,
            f"Model '{model_key}' was not found.",
            model_key=model_key,
        )

    def _resolve_model_name(
        self,
        model_name: str,
        snapshot: ModelCatalogSnapshot,
        capability_hint: Capability | None,
    ) -> tuple[Any, Capability, None]:
        model = snapshot.models_by_name.get(model_name)
        if model is None or not model.is_enabled:
            raise CatalogError(
                CatalogErrorCode.MODEL_NAME_NOT_FOUND,
                f"No enabled model found for provider name '{model_name}'.",
                model_key=model_name,
            )
        capability = self._infer_capability(model, capability_hint)
        return model, capability, None

    @staticmethod
    def _infer_capability(
        model: Any,
        capability_hint: Capability | None,
    ) -> Capability:
        """Infer the capability for *model*.

        - If the model has exactly one capability, use it.
        - If *capability_hint* is provided and valid, use it.
        - Otherwise raise.
        """
        caps = model.capabilities
        if len(caps) == 1:
            return caps[0]
        if capability_hint is not None and capability_hint in caps:
            return capability_hint
        cap_names = ", ".join(c.value for c in caps)
        raise CatalogError(
            CatalogErrorCode.UNSUPPORTED_CAPABILITY,
            f"Model '{model.model_key}' supports multiple capabilities [{cap_names}]; "
            f"pass capability_hint to disambiguate.",
            model_key=model.model_key,
        )

    # ── Candidate building ────────────────────────────────────────────────

    async def _build_candidates(
        self,
        *,
        model: Any,
        capability: Capability,
        binding: ModelBindingSnapshot | None,
        snapshot: ModelCatalogSnapshot,
        provider_hint: Any,
        required_features: Mapping[str, Any] | None,
    ) -> tuple[list[ResolvedModelRoute], RetryPolicy]:
        """Build ordered candidate routes for *model* + *capability*."""
        candidates: list[tuple[Any, Any]] = []
        supported_providers: set[Any] = set()
        for instance in model.instances:
            profile = snapshot.connection_profiles_by_key.get(instance.connection_profile_key)
            if profile is None:
                continue
            supported_providers.add(profile.provider)
            if instance.capability != capability:
                continue
            if not instance.is_enabled or not instance.is_healthy or not profile.is_enabled:
                continue
            if provider_hint is not None and profile.provider != provider_hint:
                continue
            candidates.append((instance, profile))

        if provider_hint is not None and supported_providers and provider_hint not in supported_providers:
            raise CatalogError(
                CatalogErrorCode.PROVIDER_CONFLICT,
                f"Model '{model.model_key}' does not support provider '{provider_hint.value}'.",
                model_key=model.model_key,
                provider=provider_hint.value,
            )

        if not candidates:
            raise CatalogError(
                CatalogErrorCode.NO_ENABLED_INSTANCE,
                f"Model '{model.model_key}' has no enabled instance for capability '{capability.value}'.",
                model_key=model.model_key,
            )

        if required_features and not _matches_required_features(model, required_features):
            raise CatalogError(
                CatalogErrorCode.FEATURE_REQUIREMENT_NOT_SATISFIED,
                f"Model '{model.model_key}' does not satisfy the requested features.",
                model_key=model.model_key,
            )

        # Group by priority, then apply weighted random selection within each tier.
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


# ── Helpers ───────────────────────────────────────────────────────────────


def _matches_required_features(model: Any, required_features: Mapping[str, Any]) -> bool:
    features_by_key = {feature.feature_key: feature for feature in model.features}
    for feature_key, expected_value in required_features.items():
        feature = features_by_key.get(feature_key)
        if not _feature_satisfies_requirement(feature, expected_value):
            return False
    return True


def _feature_satisfies_requirement(feature: Any, expected_value: Any) -> bool:
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
