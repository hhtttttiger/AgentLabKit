from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from ..provider_runtime import RuntimeProviderConfig
from ..models import Capability, ProviderId


JsonMap = MappingProxyType[str, Any]


def freeze_mapping(value: dict[str, Any] | None = None) -> JsonMap:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class FeatureDefinitionSnapshot:
    feature_key: str
    display_name: str
    scope: str
    value_type: str
    allowed_values: tuple[Any, ...] = ()
    is_enabled: bool = True
    is_filterable: bool = True
    is_routable: bool = True


@dataclass(frozen=True, slots=True)
class ModelFeatureSnapshot:
    feature_key: str
    display_name: str
    scope: str
    value_type: str
    allowed_values: tuple[Any, ...] = ()
    is_enabled: bool = True
    is_filterable: bool = True
    is_routable: bool = True
    is_supported: bool = True
    value: Any = None
    source: str = "manual"
    remark: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectionProfileSnapshot:
    profile_key: str
    display_name: str
    provider: ProviderId
    base_url: str | None = None
    websocket_base_url: str | None = None
    api_version: str | None = None
    region: str | None = None
    extra: JsonMap = field(default_factory=freeze_mapping)
    is_enabled: bool = True


@dataclass(frozen=True, slots=True)
class ModelInstanceSnapshot:
    instance_key: str
    model_key: str
    connection_profile_key: str
    capability: Capability
    provider_model_name: str
    provider_deployment_name: str | None = None
    region: str | None = None
    priority: int = 100
    weight: int = 100
    default_timeout_ms: int = 30000
    extra: JsonMap = field(default_factory=freeze_mapping)
    is_enabled: bool = True
    is_healthy: bool = True
    encrypted_api_key: str | None = None

    def upstream_model_name(self) -> str:
        return self.provider_deployment_name or self.provider_model_name


@dataclass(frozen=True, slots=True)
class ModelSnapshot:
    model_key: str
    display_name: str
    capabilities: tuple[Capability, ...] = ()
    description: str | None = None
    tags: tuple[str, ...] = ()
    routing_policy: JsonMap = field(default_factory=freeze_mapping)
    retry_policy: JsonMap = field(default_factory=freeze_mapping)
    is_enabled: bool = True
    features: tuple[ModelFeatureSnapshot, ...] = ()
    instances: tuple[ModelInstanceSnapshot, ...] = ()
    input_price_per_mtok: Decimal | None = None
    output_price_per_mtok: Decimal | None = None
    cache_write_price_per_mtok: Decimal | None = None
    cache_read_price_per_mtok: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ModelBindingSnapshot:
    binding_key: str
    display_name: str
    capability: Capability
    model_key: str
    metadata: JsonMap = field(default_factory=freeze_mapping)
    is_enabled: bool = True


@dataclass(frozen=True, slots=True)
class ResolvedModelRoute:
    model_key: str
    instance_key: str
    capability: Capability
    provider: ProviderId
    provider_model_name: str
    provider_deployment_name: str | None
    default_timeout_ms: int
    runtime_config: RuntimeProviderConfig = field(default_factory=RuntimeProviderConfig)
    extra: JsonMap = field(default_factory=freeze_mapping)
    catalog_revision: int = 0
    input_price_per_mtok: Decimal | None = None
    output_price_per_mtok: Decimal | None = None
    cache_write_price_per_mtok: Decimal | None = None
    cache_read_price_per_mtok: Decimal | None = None

    def upstream_model_name(self) -> str:
        return self.provider_deployment_name or self.provider_model_name


@dataclass(frozen=True, slots=True)
class ModelCatalogSnapshot:
    revision: int
    connection_profiles: tuple[ConnectionProfileSnapshot, ...]
    feature_definitions: tuple[FeatureDefinitionSnapshot, ...]
    models: tuple[ModelSnapshot, ...]
    bindings: tuple[ModelBindingSnapshot, ...]

    # ── Pre-computed lookup indexes (built once in __post_init__) ──────────
    connection_profiles_by_key: MappingProxyType[str, ConnectionProfileSnapshot] = field(init=False, repr=False)
    models_by_key: MappingProxyType[str, ModelSnapshot] = field(init=False, repr=False)
    bindings_by_key: MappingProxyType[str, ModelBindingSnapshot] = field(init=False, repr=False)
    feature_definitions_by_key: MappingProxyType[str, FeatureDefinitionSnapshot] = field(init=False, repr=False)
    models_by_name: MappingProxyType[str, ModelSnapshot] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connection_profiles_by_key",
            MappingProxyType({p.profile_key: p for p in self.connection_profiles}),
        )
        object.__setattr__(
            self,
            "models_by_key",
            MappingProxyType({m.model_key: m for m in self.models}),
        )
        object.__setattr__(
            self,
            "bindings_by_key",
            MappingProxyType({b.binding_key: b for b in self.bindings}),
        )
        object.__setattr__(
            self,
            "feature_definitions_by_key",
            MappingProxyType({d.feature_key: d for d in self.feature_definitions}),
        )
        # provider_model_name → ModelSnapshot (first match wins for duplicates)
        name_index: dict[str, ModelSnapshot] = {}
        for model in self.models:
            for instance in model.instances:
                if instance.provider_model_name not in name_index:
                    name_index[instance.provider_model_name] = model
        object.__setattr__(
            self,
            "models_by_name",
            MappingProxyType(name_index),
        )
