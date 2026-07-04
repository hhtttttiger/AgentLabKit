from __future__ import annotations

from enum import Enum
import os
import re

from ..config import ProviderConfig
from ..provider_runtime import RuntimeProviderConfig
from .domain import ConnectionProfileSnapshot, ModelInstanceSnapshot
from .errors import CatalogError, CatalogErrorCode
from ..models import ProviderId
from .instance_encryption import decrypt_instance_api_key, parse_encryption_key


class SecretResolver:
    async def resolve(
        self,
        profile: ConnectionProfileSnapshot,
        instance: ModelInstanceSnapshot | None = None,
    ) -> RuntimeProviderConfig:
        raise NotImplementedError


class SecretResolutionMode(str, Enum):
    INSTANCE_ONLY = "instance_only"
    INSTANCE_THEN_ENV = "instance_then_env"
    ENV_ONLY = "env_only"


def _normalize_ref(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


class EnvironmentSecretResolver(SecretResolver):
    def __init__(
        self,
        env: dict[str, str] | None = None,
        *,
        defaults: ProviderConfig | None = None,
    ) -> None:
        self._env = env if env is not None else os.environ
        self._defaults = defaults or ProviderConfig()

    async def resolve(
        self,
        profile: ConnectionProfileSnapshot,
        instance: ModelInstanceSnapshot | None = None,
    ) -> RuntimeProviderConfig:
        _ = instance
        keys = self._candidate_env_keys(profile)
        defaults = self._defaults
        api_key = self._first_present(*[f"{prefix}_API_KEY" for prefix in keys]) or defaults.api_key
        if not api_key:
            raise CatalogError(
                CatalogErrorCode.CREDENTIAL_NOT_RESOLVED,
                f"Connection profile '{profile.profile_key}' could not be resolved from the environment.",
                provider=profile.provider.value,
            )

        provider_alias = self._PROVIDER_ALIASES.get(profile.provider, "")
        base_url = self._first_present(
            *[f"{prefix}_BASE_URL" for prefix in keys],
            f"{provider_alias}_BASE_URL" if provider_alias else "",
        ) or self._first_present(
            *[f"{prefix}_ENDPOINT" for prefix in keys],
        ) or defaults.base_url

        return RuntimeProviderConfig(
            api_key=api_key,
            base_url=base_url,
            websocket_base_url=self._first_present(
                *[f"{prefix}_WEBSOCKET_BASE_URL" for prefix in keys],
            ) or defaults.websocket_base_url,
            api_version=self._first_present(
                *[f"{prefix}_API_VERSION" for prefix in keys],
            ) or defaults.api_version,
            organization=self._first_present(*[f"{prefix}_ORGANIZATION" for prefix in keys]) or None,
            project=self._first_present(*[f"{prefix}_PROJECT" for prefix in keys]) or None,
            region=self._first_present(*[f"{prefix}_REGION" for prefix in keys]) or profile.region,
        )

    _PROVIDER_ALIASES: dict[ProviderId, str] = {
        ProviderId.OPENAI: "OPENAI",
        ProviderId.ANTHROPIC: "ANTHROPIC",
    }

    def _candidate_env_keys(self, profile: ConnectionProfileSnapshot) -> tuple[str, ...]:
        normalized = _normalize_ref(profile.profile_key)
        aliases = [normalized]
        provider_alias = self._PROVIDER_ALIASES.get(profile.provider)
        if provider_alias is not None:
            aliases.append(provider_alias)
        return tuple(dict.fromkeys(alias for alias in aliases if alias))

    def _first_present(self, *keys: str) -> str | None:
        for key in keys:
            if key and (value := self._env.get(key)):
                return value
        return None


class InstanceSecretResolver(SecretResolver):
    def __init__(
        self,
        *,
        encryption_key: str | None = None,
        fallback: SecretResolver | None = None,
    ) -> None:
        self._encryption_key = parse_encryption_key(encryption_key)
        self._fallback = fallback

    async def resolve(
        self,
        profile: ConnectionProfileSnapshot,
        instance: ModelInstanceSnapshot | None = None,
    ) -> RuntimeProviderConfig:
        encrypted_api_key = instance.encrypted_api_key if instance is not None else None
        if encrypted_api_key:
            if self._encryption_key is None:
                raise CatalogError(
                    CatalogErrorCode.CREDENTIAL_NOT_RESOLVED,
                    "Instance encryption key is not configured.",
                    provider=profile.provider.value,
                )

            api_key = decrypt_instance_api_key(encrypted_api_key, self._encryption_key)
            if api_key is None:
                raise CatalogError(
                    CatalogErrorCode.CREDENTIAL_NOT_RESOLVED,
                    f"Encrypted API key for instance '{instance.instance_key}' could not be decrypted.",
                    provider=profile.provider.value,
                )

            return RuntimeProviderConfig(
                api_key=api_key,
                base_url=profile.base_url,
                websocket_base_url=profile.websocket_base_url,
                api_version=profile.api_version,
                region=profile.region,
            )

        if self._fallback is not None:
            return await self._fallback.resolve(profile, instance)

        instance_key = instance.instance_key if instance is not None else "unknown"
        raise CatalogError(
            CatalogErrorCode.CREDENTIAL_NOT_RESOLVED,
            f"Instance '{instance_key}' has no encrypted API key and no fallback secret source is enabled.",
            provider=profile.provider.value,
        )
