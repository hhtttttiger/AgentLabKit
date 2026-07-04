from __future__ import annotations

import base64

import pytest

from llm_gateway.config import ProviderConfig
from llm_gateway.model_catalog.domain import ConnectionProfileSnapshot, ModelInstanceSnapshot
from llm_gateway.models import Capability, ProviderId
from llm_gateway.model_catalog.errors import CatalogError
from llm_gateway.model_catalog.instance_encryption import encrypt_instance_api_key
from llm_gateway.model_catalog.secret_resolver import (
    EnvironmentSecretResolver,
    InstanceSecretResolver,
    SecretResolutionMode,
)


def _profile(provider: ProviderId = ProviderId.OPENAI) -> ConnectionProfileSnapshot:
    return ConnectionProfileSnapshot(
        profile_key="openai.primary",
        display_name="OpenAI Primary",
        provider=provider,
    )


def _instance(encrypted_api_key: str | None = None) -> ModelInstanceSnapshot:
    return ModelInstanceSnapshot(
        instance_key="instance.primary",
        card_key="gateway.default.text",
        connection_profile_key="openai.primary",
        capability=Capability.TEXT,
        provider_model_name="gpt-4.1-mini",
        encrypted_api_key=encrypted_api_key,
    )


class TestEnvironmentSecretResolver:
    @pytest.mark.asyncio
    async def test_resolves_from_env(self):
        resolver = EnvironmentSecretResolver(env={"OPENAI_API_KEY": "sk-test"})
        bundle = await resolver.resolve(_profile(), _instance())
        assert bundle.api_key == "sk-test"

    @pytest.mark.asyncio
    async def test_raises_when_no_api_key_exists(self):
        resolver = EnvironmentSecretResolver(env={})
        with pytest.raises(CatalogError):
            await resolver.resolve(_profile(), _instance())


class TestInstanceSecretResolver:
    @pytest.mark.asyncio
    async def test_resolves_from_instance_encrypted_api_key(self):
        key = bytes(range(32))
        encrypted = encrypt_instance_api_key("instance-key", key)
        resolver = InstanceSecretResolver(
            encryption_key=base64.b64encode(key).decode("ascii"),
        )

        bundle = await resolver.resolve(_profile(), _instance(encrypted))

        assert bundle.api_key == "instance-key"

    @pytest.mark.asyncio
    async def test_instance_resolution_preserves_profile_transport_settings(self):
        key = bytes(range(32))
        encrypted = encrypt_instance_api_key("instance-key", key)
        resolver = InstanceSecretResolver(
            encryption_key=base64.b64encode(key).decode("ascii"),
        )

        bundle = await resolver.resolve(
            ConnectionProfileSnapshot(
                profile_key="openai.secondary",
                display_name="OpenAI Secondary",
                provider=ProviderId.OPENAI,
                base_url="https://api.openai.example/v1/",
            ),
            _instance(encrypted),
        )

        assert bundle.base_url == "https://api.openai.example/v1/"

    @pytest.mark.asyncio
    async def test_falls_back_to_environment_when_enabled(self):
        resolver = InstanceSecretResolver(
            encryption_key=None,
            fallback=EnvironmentSecretResolver(
                env={},
                defaults=ProviderConfig(api_key="fallback-openai-key"),
            ),
        )

        bundle = await resolver.resolve(_profile(), _instance())

        assert bundle.api_key == "fallback-openai-key"

    @pytest.mark.asyncio
    async def test_raises_when_encrypted_api_key_exists_but_key_missing(self):
        key = bytes(range(32))
        encrypted = encrypt_instance_api_key("instance-key", key)
        resolver = InstanceSecretResolver()

        with pytest.raises(CatalogError) as exc_info:
            await resolver.resolve(_profile(), _instance(encrypted))

        assert exc_info.value.code.value == "credential_not_resolved"


def test_secret_resolution_mode_values_match_runtime_contract():
    assert SecretResolutionMode.INSTANCE_ONLY.value == "instance_only"
