"""Resolver fallback: a binding key passed as model_key resolves to its model.

agent_runtime maps ``agent.model_binding_key`` onto the gateway request's
``model`` field, so a value like ``"mimo-v2-flash-chat"`` (a *binding* key)
reaches the resolver as ``model_key``. The resolver must recognise it as a
binding and derive the real model key rather than failing MODEL_NOT_FOUND.

These tests build a :class:`ModelCatalogSnapshot` directly (no DB) and drive
:class:`ModelResolver.resolve_candidates` with a stub secret resolver.
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
from llm_gateway.models import Capability, ProviderId


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


def _snapshot_with_binding() -> ModelCatalogSnapshot:
    binding_key = "mimo-v2-flash-chat"
    model_key = "mimo-v2-flash"
    profile = ConnectionProfileSnapshot(
        profile_key="openai-profile", display_name="OpenAI", provider=ProviderId.OPENAI,
        base_url="https://api.example.com", is_enabled=True,
    )
    instance = ModelInstanceSnapshot(
        instance_key=f"{model_key}.text", model_key=model_key,
        connection_profile_key=profile.profile_key, capability=Capability.TEXT,
        provider_model_name="mimo-v2-flash", is_enabled=True, is_healthy=True,
    )
    model = ModelSnapshot(
        model_key=model_key, display_name="MiMo V2 Flash",
        capabilities=(Capability.TEXT,), is_enabled=True, instances=(instance,),
    )
    binding = ModelBindingSnapshot(
        binding_key=binding_key, display_name="MiMo V2 Flash Chat",
        capability=Capability.TEXT, model_key=model_key, is_enabled=True,
    )
    return ModelCatalogSnapshot(
        revision=1, connection_profiles=(profile,), feature_definitions=(),
        models=(model,), bindings=(binding,),
    )


def _resolver(snapshot: ModelCatalogSnapshot) -> ModelResolver:
    return ModelResolver(_FakeCatalogService(snapshot), _StubSecretResolver())


@pytest.mark.asyncio
async def test_binding_key_passed_as_model_key_resolves_to_model():
    resolver = _resolver(_snapshot_with_binding())

    # The caller passes the *binding* key in the model field (as agent_runtime
    # does). binding_key below is the resolver's default ("gateway.default_text"),
    # which is intentionally absent from the snapshot.
    routes, _ = await resolver.resolve_candidates(
        "gateway.default_text",
        model_key="mimo-v2-flash-chat",
        provider_hint=None,
        capability=Capability.TEXT,
    )

    assert routes, "expected at least one resolved route"
    assert routes[0].model_key == "mimo-v2-flash"  # the real model key, not the binding


@pytest.mark.asyncio
async def test_genuine_model_key_still_resolves_directly():
    # A real model key must keep working (fallback must not shadow direct model keys).
    resolver = _resolver(_snapshot_with_binding())
    routes, _ = await resolver.resolve_candidates(
        "gateway.default_text",
        model_key="mimo-v2-flash",
        provider_hint=None,
        capability=Capability.TEXT,
    )
    assert routes and routes[0].model_key == "mimo-v2-flash"


@pytest.mark.asyncio
async def test_unknown_model_key_still_raises_not_found():
    # Values that are neither a model key nor a binding must still fail clearly.
    resolver = _resolver(_snapshot_with_binding())
    with pytest.raises(CatalogError) as exc_info:
        await resolver.resolve_candidates(
            "gateway.default_text",
            model_key="does-not-exist",
            provider_hint=None,
            capability=Capability.TEXT,
        )
    assert exc_info.value.code == CatalogErrorCode.MODEL_NOT_FOUND
