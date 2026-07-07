"""Resolver: multi-strategy model resolution via ModelRef.

Tests the three resolution strategies (binding_key, model_key, model_name)
and the backward-compatible ``resolve_candidates`` entry point.  Builds a
:class:`ModelCatalogSnapshot` directly (no DB) and drives
:class:`ModelResolver` with a stub secret resolver.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from llm_gateway.model_catalog.domain import (
    ConnectionProfileSnapshot,
    ModelBindingSnapshot,
    ModelCatalogSnapshot,
    ModelInstanceSnapshot,
    ModelSnapshot,
)
from llm_gateway.model_catalog.errors import CatalogError, CatalogErrorCode
from llm_gateway.model_catalog.service import ModelResolver
from llm_gateway.models import Capability, ModelRef, ProviderId


@dataclass
class _ResolvedSecret:
    api_key: str | None = "sk-test"
    base_url: str | None = None
    websocket_base_url: str | None = None
    api_version: str | None = None
    organization: str | None = None
    project: str | None = None
    region: str | None = None


class _StubSecretResolver:
    async def resolve(self, profile, instance):  # noqa: ANN001
        return _ResolvedSecret()


class _FakeCatalogService:
    def __init__(self, snapshot: ModelCatalogSnapshot) -> None:
        self._snapshot = snapshot

    async def get_snapshot(self) -> ModelCatalogSnapshot:
        return self._snapshot


def _snapshot() -> ModelCatalogSnapshot:
    """Build a snapshot with one model, one binding, two capabilities."""
    profile = ConnectionProfileSnapshot(
        profile_key="openai-profile",
        display_name="OpenAI",
        provider=ProviderId.OPENAI,
        base_url="https://api.example.com",
        is_enabled=True,
    )
    text_instance = ModelInstanceSnapshot(
        instance_key="mimo-v2-flash.text",
        model_key="mimo-v2-flash",
        connection_profile_key=profile.profile_key,
        capability=Capability.TEXT,
        provider_model_name="mimo-v2-flash",
        is_enabled=True,
        is_healthy=True,
    )
    embed_instance = ModelInstanceSnapshot(
        instance_key="mimo-v2-flash.embedding",
        model_key="mimo-v2-flash",
        connection_profile_key=profile.profile_key,
        capability=Capability.EMBEDDING,
        provider_model_name="mimo-v2-flash",
        is_enabled=True,
        is_healthy=True,
    )
    model = ModelSnapshot(
        model_key="mimo-v2-flash",
        display_name="MiMo V2 Flash",
        capabilities=(Capability.TEXT, Capability.EMBEDDING),
        is_enabled=True,
        instances=(text_instance, embed_instance),
    )
    # Single-capability model for auto-inference tests
    single_model = ModelSnapshot(
        model_key="gpt-5.4-mini",
        display_name="GPT-5.4 Mini",
        capabilities=(Capability.TEXT,),
        is_enabled=True,
        instances=(
            ModelInstanceSnapshot(
                instance_key="gpt-5.4-mini.text",
                model_key="gpt-5.4-mini",
                connection_profile_key=profile.profile_key,
                capability=Capability.TEXT,
                provider_model_name="gpt-5.4-mini",
                is_enabled=True,
                is_healthy=True,
            ),
        ),
    )
    binding = ModelBindingSnapshot(
        binding_key="mimo-v2-flash-chat",
        display_name="MiMo V2 Flash Chat",
        capability=Capability.TEXT,
        model_key="mimo-v2-flash",
        is_enabled=True,
    )
    return ModelCatalogSnapshot(
        revision=1,
        connection_profiles=(profile,),
        feature_definitions=(),
        models=(model, single_model),
        bindings=(binding,),
    )


def _resolver(snapshot: ModelCatalogSnapshot | None = None) -> ModelResolver:
    return ModelResolver(_FakeCatalogService(snapshot or _snapshot()), _StubSecretResolver())


# ── ModelRef.binding ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_via_binding_key():
    resolver = _resolver()
    ref = ModelRef.binding("mimo-v2-flash-chat")
    routes, _ = await resolver.resolve(ref, capability_hint=Capability.TEXT)

    assert routes, "expected at least one resolved route"
    assert routes[0].model_key == "mimo-v2-flash"


@pytest.mark.asyncio
async def test_resolve_via_binding_key_not_found():
    resolver = _resolver()
    ref = ModelRef.binding("nonexistent-binding")
    with pytest.raises(CatalogError) as exc_info:
        await resolver.resolve(ref)
    assert exc_info.value.code == CatalogErrorCode.BINDING_NOT_FOUND


# ── ModelRef.model (direct model key) ────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_via_model_key_single_capability():
    resolver = _resolver()
    ref = ModelRef.model("gpt-5.4-mini")
    routes, _ = await resolver.resolve(ref)

    assert routes
    assert routes[0].model_key == "gpt-5.4-mini"
    assert routes[0].capability == Capability.TEXT


@pytest.mark.asyncio
async def test_resolve_via_model_key_multi_capability_with_hint():
    resolver = _resolver()
    ref = ModelRef.model("mimo-v2-flash")
    routes, _ = await resolver.resolve(ref, capability_hint=Capability.EMBEDDING)

    assert routes
    assert routes[0].capability == Capability.EMBEDDING


@pytest.mark.asyncio
async def test_resolve_via_model_key_multi_capability_no_hint_raises():
    resolver = _resolver()
    ref = ModelRef.model("mimo-v2-flash")
    with pytest.raises(CatalogError) as exc_info:
        await resolver.resolve(ref)
    assert exc_info.value.code == CatalogErrorCode.UNSUPPORTED_CAPABILITY


@pytest.mark.asyncio
async def test_resolve_via_model_key_not_found():
    resolver = _resolver()
    ref = ModelRef.model("does-not-exist")
    with pytest.raises(CatalogError) as exc_info:
        await resolver.resolve(ref)
    assert exc_info.value.code == CatalogErrorCode.MODEL_NOT_FOUND


@pytest.mark.asyncio
async def test_model_key_falls_back_to_binding_when_not_a_model():
    """A value that is not a model key but IS a binding key should resolve
    via the binding (backward compat for agent_runtime)."""
    resolver = _resolver()
    ref = ModelRef.model("mimo-v2-flash-chat")  # this is a binding key
    routes, _ = await resolver.resolve(ref, capability_hint=Capability.TEXT)

    assert routes
    assert routes[0].model_key == "mimo-v2-flash"


# ── ModelRef.name (provider model name) ──────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_via_model_name():
    resolver = _resolver()
    ref = ModelRef.name("gpt-5.4-mini")
    routes, _ = await resolver.resolve(ref)

    assert routes
    assert routes[0].model_key == "gpt-5.4-mini"


@pytest.mark.asyncio
async def test_resolve_via_model_name_multi_capability():
    resolver = _resolver()
    ref = ModelRef.name("mimo-v2-flash")
    routes, _ = await resolver.resolve(ref, capability_hint=Capability.TEXT)

    assert routes
    assert routes[0].model_key == "mimo-v2-flash"


@pytest.mark.asyncio
async def test_resolve_via_model_name_not_found():
    resolver = _resolver()
    ref = ModelRef.name("nonexistent-model")
    with pytest.raises(CatalogError) as exc_info:
        await resolver.resolve(ref)
    assert exc_info.value.code == CatalogErrorCode.MODEL_NAME_NOT_FOUND


# ── Backward-compatible resolve_candidates ────────────────────────────────


@pytest.mark.asyncio
async def test_binding_key_passed_as_model_key_resolves_to_model():
    """agent_runtime passes binding key via model field."""
    resolver = _resolver()
    routes, _ = await resolver.resolve_candidates(
        "gateway.default_text",
        model_key="mimo-v2-flash-chat",
        provider_hint=None,
        capability=Capability.TEXT,
    )
    assert routes
    assert routes[0].model_key == "mimo-v2-flash"


@pytest.mark.asyncio
async def test_genuine_model_key_still_resolves_directly():
    resolver = _resolver()
    routes, _ = await resolver.resolve_candidates(
        "gateway.default_text",
        model_key="mimo-v2-flash",
        provider_hint=None,
        capability=Capability.TEXT,
    )
    assert routes and routes[0].model_key == "mimo-v2-flash"


@pytest.mark.asyncio
async def test_unknown_model_key_still_raises_not_found():
    resolver = _resolver()
    with pytest.raises(CatalogError) as exc_info:
        await resolver.resolve_candidates(
            "gateway.default_text",
            model_key="does-not-exist",
            provider_hint=None,
            capability=Capability.TEXT,
        )
    assert exc_info.value.code == CatalogErrorCode.MODEL_NOT_FOUND
