from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...config import ProviderConfig
from ...core.adapters import ImageAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import ImageGenerateRequest, ImageGenerateResponse, ProviderId
from ...provider_runtime import RuntimeProviderConfig
from .common import image_list_from_result, provider_config_error, require_api_key, resolve_provider_secrets, usage_info_from_result
from .error_mapping import map_sdk_error


class OpenAICompatibleImageAdapter(ImageAdapter):
    def __init__(
        self,
        secrets: ProviderConfig,
        *,
        provider: ProviderId,
        auth_error_message: str,
        client: Any | None = None,
        client_factory: Callable[[ProviderConfig], Any] | None = None,
    ) -> None:
        self.secrets = secrets
        self.provider = provider
        self.auth_error_message = auth_error_message
        self.client = client
        self.client_factory = client_factory

    def _get_client(self, model_name: str, secrets: ProviderConfig):
        if self.client is not None and secrets == self.secrets:
            return self.client
        if self.client_factory is None:
            raise GatewayError(
                GatewayErrorCode.PROVIDER_AUTH_FAILED,
                self.auth_error_message,
                provider=self.provider,
                model=model_name,
            )
        try:
            client = self.client_factory(secrets)
            if secrets == self.secrets:
                self.client = client
        except Exception as exc:
            raise provider_config_error(
                provider=self.provider,
                model=model_name,
                exc=exc,
            ) from exc
        return client

    async def generate(
        self,
        request: ImageGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> ImageGenerateResponse:
        model_name = request.model or ""
        secrets = resolve_provider_secrets(self.secrets, runtime_config)
        require_api_key(
            self.provider,
            model_name,
            secrets,
            self.auth_error_message,
        )
        try:
            result = await self._get_client(model_name, secrets).images.generate(
                model=model_name,
                prompt=request.prompt,
                size=request.size,
                n=request.count,
            )
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
        return ImageGenerateResponse(
            provider=self.provider,
            model=model_name,
            images=image_list_from_result(result),
            usage=usage_info_from_result(result),
        )
