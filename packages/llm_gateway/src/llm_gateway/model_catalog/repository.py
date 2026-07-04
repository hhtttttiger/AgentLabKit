from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import ModelDefinition
from .domain import (
    ConnectionProfileSnapshot,
    FeatureDefinitionSnapshot,
    ModelBindingSnapshot,
    ModelFeatureSnapshot,
    ModelSnapshot,
    ModelCatalogSnapshot,
    ModelInstanceSnapshot,
)
from ..models import Capability, ProviderId
from .errors import CatalogError, CatalogErrorCode
from .orm_models import (
    LlmCatalogRevisionOrm,
    LlmConnectionProfileOrm,
    LlmFeatureDefinitionOrm,
    LlmModelBindingOrm,
    LlmModelFeatureOrm,
    LlmModelOrm,
    LlmModelInstanceOrm,
)


class ModelCatalogRepository(Protocol):
    async def load_snapshot(self) -> ModelCatalogSnapshot: ...


_DEFAULT_BINDINGS: tuple[tuple[str, str, Capability, str], ...] = (
    ("gateway.default_embedding", "Gateway Default Embedding", Capability.EMBEDDING, "text-embedding-3-small"),
    ("gateway.default_text", "Gateway Default Text", Capability.TEXT, "gpt-5.4-mini"),
    ("gateway.default_realtime", "Gateway Default Realtime", Capability.REALTIME, "gpt-realtime-2"),
    ("gateway.default_image", "Gateway Default Image", Capability.IMAGE, "gpt-image-2"),
    ("voice.realtime_transport", "Voice Realtime Transport", Capability.REALTIME, "gpt-realtime-2"),
    ("voice.agent_text", "Voice Agent Text", Capability.TEXT, "gpt-5.4-mini"),
)


class StaticModelCatalogRepository:
    def __init__(self, snapshot: ModelCatalogSnapshot) -> None:
        self._snapshot = snapshot

    async def load_snapshot(self) -> ModelCatalogSnapshot:
        return self._snapshot


class SqlAlchemyModelCatalogRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load_snapshot(self) -> ModelCatalogSnapshot:
        async with self._session_factory() as session:
            return await self._load_snapshot(session)

    async def _load_snapshot(self, session: AsyncSession) -> ModelCatalogSnapshot:
        try:
            profile_rows = list((await session.execute(select(LlmConnectionProfileOrm))).scalars())
            feature_definition_rows = list((await session.execute(select(LlmFeatureDefinitionOrm))).scalars())
            model_rows = list((await session.execute(select(LlmModelOrm))).scalars())
            binding_rows = list((await session.execute(select(LlmModelBindingOrm))).scalars())
            instance_rows = list((await session.execute(select(LlmModelInstanceOrm))).scalars())
            model_feature_rows = list((await session.execute(select(LlmModelFeatureOrm))).scalars())
            revision_row = (
                await session.execute(
                    select(LlmCatalogRevisionOrm).order_by(LlmCatalogRevisionOrm.revision.desc())
                )
            ).scalars().first()
            profiles_by_id = {
                row.id: ConnectionProfileSnapshot(
                    profile_key=row.profile_key,
                    display_name=row.display_name,
                    provider=ProviderId(row.provider),
                    base_url=row.base_url,
                    websocket_base_url=row.websocket_base_url,
                    api_version=row.api_version,
                    region=row.region,
                    extra=MappingProxyType(dict(row.extra_json or {})),
                    is_enabled=row.is_enabled,
                )
                for row in profile_rows
            }
            models_by_row_id = {row.id: row for row in model_rows}
            model_capabilities_by_model_id: dict[int, set[Capability]] = defaultdict(set)
            for row in binding_rows:
                model_capabilities_by_model_id[row.model_id].add(_binding_capability(row))
            feature_definitions_by_id = {
                row.id: FeatureDefinitionSnapshot(
                    feature_key=row.feature_key,
                    display_name=row.display_name,
                    scope="model",
                    value_type=row.value_type,
                    allowed_values=tuple(row.allowed_values_json or ()),
                    is_enabled=row.is_enabled,
                    is_filterable=row.is_filterable,
                    is_routable=row.is_routable,
                )
                for row in feature_definition_rows
            }
            model_keys_by_id = {row.id: row.model_key for row in model_rows}
            model_features_by_model_id: dict[int, list[ModelFeatureSnapshot]] = defaultdict(list)
            for row in model_feature_rows:
                definition = _require_reference(
                    feature_definitions_by_id,
                    row.feature_id,
                    "feature definition",
                )
                model_features_by_model_id[row.model_id].append(
                    ModelFeatureSnapshot(
                        feature_key=definition.feature_key,
                        display_name=definition.display_name,
                        scope=definition.scope,
                        value_type=definition.value_type,
                        allowed_values=definition.allowed_values,
                        is_enabled=definition.is_enabled,
                        is_filterable=definition.is_filterable,
                        is_routable=definition.is_routable,
                        is_supported=row.is_supported,
                        value=row.value_json,
                        source=row.source,
                        remark=row.remark,
                    )
                )
            instances_by_model: dict[int, list[ModelInstanceSnapshot]] = defaultdict(list)
            for row in instance_rows:
                model_key = _require_reference(model_keys_by_id, row.model_id, "model")
                model_row = _require_reference(models_by_row_id, row.model_id, "model")
                connection_profile_key = _require_reference(
                    profiles_by_id,
                    model_row.connection_profile_id,
                    "connection profile",
                ).profile_key
                capabilities = sorted(
                    model_capabilities_by_model_id.get(row.model_id) or _fallback_capabilities(model_row.type),
                    key=lambda item: item.value,
                )
                for capability in capabilities:
                    instances_by_model[row.model_id].append(
                        ModelInstanceSnapshot(
                            instance_key=row.instance_key,
                            model_key=model_key,
                            connection_profile_key=connection_profile_key,
                            capability=capability,
                            provider_model_name=model_row.model_name,
                            provider_deployment_name=row.provider_deployment_name,
                            region=row.region,
                            priority=row.priority,
                            weight=row.weight,
                            default_timeout_ms=row.default_timeout_ms,
                            extra=MappingProxyType(dict(row.extra_json or {})),
                            is_enabled=row.is_enabled,
                            is_healthy=row.is_healthy,
                            encrypted_api_key=row.encrypted_api_key,
                        )
                    )

            models_by_id = {
                row.id: ModelSnapshot(
                    model_key=row.model_key,
                    display_name=row.display_name,
                    capabilities=tuple(
                        sorted(
                            model_capabilities_by_model_id.get(row.id) or _fallback_capabilities(row.type),
                            key=lambda item: item.value,
                        )
                    ),
                    description=row.description,
                    tags=tuple(row.tags_json or []),
                    routing_policy=MappingProxyType(dict(row.routing_policy_json or {})),
                    retry_policy=MappingProxyType(dict(row.retry_policy_json or {})),
                    is_enabled=row.is_enabled,
                    features=tuple(
                        sorted(
                            model_features_by_model_id.get(row.id, []),
                            key=lambda item: item.feature_key,
                        )
                    ),
                    instances=tuple(instances_by_model.get(row.id, [])),
                    input_price_per_mtok=row.input_price_per_mtok,
                    output_price_per_mtok=row.output_price_per_mtok,
                    cache_write_price_per_mtok=row.cache_write_price_per_mtok,
                    cache_read_price_per_mtok=row.cache_read_price_per_mtok,
                )
                for row in model_rows
            }
            bindings = tuple(
                ModelBindingSnapshot(
                    binding_key=row.binding_key,
                    display_name=row.display_name,
                    capability=_binding_capability(row),
                    model_key=_require_reference(models_by_id, row.model_id, "model").model_key,
                    metadata=MappingProxyType(dict(row.metadata_json or {})),
                    is_enabled=row.is_enabled,
                )
                for row in binding_rows
            )
            return ModelCatalogSnapshot(
                revision=revision_row.revision if revision_row is not None else 0,
                connection_profiles=tuple(profile for _, profile in sorted(profiles_by_id.items())),
                feature_definitions=tuple(
                    definition
                    for _, definition in sorted(
                        feature_definitions_by_id.items(),
                        key=lambda item: item[1].feature_key,
                    )
                ),
                models=tuple(model for _, model in sorted(models_by_id.items())),
                bindings=bindings,
            )
        except CatalogError:
            raise
        except Exception as exc:
            raise CatalogError(
                CatalogErrorCode.CATALOG_UNAVAILABLE,
                f"The model catalog could not be loaded from the database: {type(exc).__name__}: {exc}",
            ) from exc


def snapshot_from_model_definitions(models: list[ModelDefinition]) -> ModelCatalogSnapshot:
    openai_profile = ConnectionProfileSnapshot(
        profile_key="openai.default",
        display_name="OpenAI Default",
        provider=ProviderId.OPENAI,
    )
    instances_by_model: dict[str, list[ModelInstanceSnapshot]] = defaultdict(list)
    for model in models:
        for capability in sorted(model.capabilities, key=lambda item: item.value):
            instances_by_model[model.model_key].append(
                ModelInstanceSnapshot(
                    instance_key=f"{model.model_key}.{capability.value}",
                    model_key=model.model_key,
                    connection_profile_key=openai_profile.profile_key,
                    capability=capability,
                    provider_model_name=model.provider_model_name,
                    provider_deployment_name=model.provider_deployment_name,
                    region=model.region,
                    default_timeout_ms=model.default_timeout_ms,
                    is_enabled=model.enabled,
                    is_healthy=True,
                    encrypted_api_key=None,
                )
            )
    models_tuple = tuple(
        ModelSnapshot(
            model_key=model.model_key,
            display_name=model.model_key,
            capabilities=tuple(sorted(model.capabilities, key=lambda item: item.value)),
            is_enabled=model.enabled,
            features=(),
            instances=tuple(instances_by_model[model.model_key]),
        )
        for model in models
    )
    bindings = tuple(_build_static_bindings(models))
    return ModelCatalogSnapshot(
        revision=1,
        connection_profiles=(openai_profile,),
        feature_definitions=(),
        models=models_tuple,
        bindings=bindings,
    )


def _build_static_bindings(models: list[ModelDefinition]) -> list[ModelBindingSnapshot]:
    bindings: list[ModelBindingSnapshot] = []
    binding_specs = list(_DEFAULT_BINDINGS)
    existing_keys = {binding_key for binding_key, *_ in binding_specs}
    for required_binding in (
        ("gateway.default_speech_batch", "Gateway Default Speech Batch", Capability.SPEECH_BATCH, "gpt-4o-mini-transcribe"),
        ("gateway.default_speech_stream", "Gateway Default Speech Stream", Capability.SPEECH_STREAM, "gpt-4o-mini-transcribe"),
    ):
        if required_binding[0] not in existing_keys:
            binding_specs.append(required_binding)

    for binding_key, display_name, capability, preferred_target in binding_specs:
        model_key = _resolve_static_binding_model_key(models, capability, preferred_target)
        if model_key is None:
            continue
        bindings.append(
            ModelBindingSnapshot(
                binding_key=binding_key,
                display_name=display_name,
                capability=capability,
                model_key=model_key,
            )
        )
    return bindings


def _resolve_static_binding_model_key(
    models: list[ModelDefinition],
    capability: Capability,
    preferred_target: str,
) -> str | None:
    matching_models = [model for model in models if capability in model.capabilities and model.enabled]
    if not matching_models:
        return None

    for model in matching_models:
        if (
            model.model_key == preferred_target
            or model.provider_model_name == preferred_target
            or model.provider_deployment_name == preferred_target
        ):
            return model.model_key

    return matching_models[0].model_key


def _require_reference(mapping: dict[object, object], key: object, resource: str):
    try:
        return mapping[key]
    except KeyError as exc:
        raise CatalogError(
            CatalogErrorCode.CATALOG_UNAVAILABLE,
            f"The model catalog references a missing {resource} (key={key!r}).",
        ) from exc


def _binding_capability(row) -> Capability:
    """Resolve binding capability from the ``capability`` column, falling
    back to string-pattern matching on ``binding_key`` for legacy rows.
    """
    explicit = getattr(row, "capability", None)
    if explicit:
        try:
            return Capability(explicit)
        except ValueError:
            pass
    return _infer_capability_from_key(row.binding_key)


def _infer_capability_from_key(binding_key: str) -> Capability:
    normalized = binding_key.lower()
    if "embedding" in normalized:
        return Capability.EMBEDDING
    if "realtime" in normalized or normalized.endswith("playback"):
        return Capability.REALTIME
    if "speech_stream" in normalized:
        return Capability.SPEECH_STREAM
    if "speech_batch" in normalized or "transcription" in normalized:
        return Capability.SPEECH_BATCH
    if "image" in normalized:
        return Capability.IMAGE
    return Capability.TEXT


def _fallback_capabilities(model_type: str | None) -> set[Capability]:
    normalized = (model_type or "").lower()
    if normalized == "embedding":
        return {Capability.EMBEDDING}
    if normalized == "speech":  # legacy broad value, kept for back-compat
        return {Capability.SPEECH_BATCH, Capability.SPEECH_STREAM, Capability.REALTIME}
    if normalized == "speechbatch":
        return {Capability.SPEECH_BATCH}
    if normalized == "speechstream":
        return {Capability.SPEECH_STREAM}
    if normalized in ("realtime", "playback"):
        return {Capability.REALTIME}
    if normalized == "image":
        return {Capability.IMAGE}
    if normalized == "text":
        return {Capability.TEXT}
    return {Capability.TEXT}
