from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...config import ProviderConfig
from ...core.adapters import EmbeddingAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import EmbeddingGenerateRequest, EmbeddingGenerateResponse, ProviderId
from ...provider_runtime import RuntimeProviderConfig
from ...usage_info import usage_from_response_usage
from ..shared.common import provider_config_error, require_api_key, resolve_provider_secrets
from ..shared.error_mapping import map_sdk_error
from ..shared.openai_transport import create_openai_client


class OpenAIEmbeddingAdapter(EmbeddingAdapter):
    def __init__(
        self,
        secrets: ProviderConfig,
        *,
        client: Any | None = None,
        client_factory: Callable[[ProviderConfig], Any] | None = None,
    ) -> None:
        self.secrets = secrets
        self.provider = ProviderId.OPENAI
        self.auth_error_message = "OpenAI API key is not configured."
        self.client = client
        self.client_factory = client_factory or (
            (lambda resolved: create_openai_client(resolved)) if client is None else None
        )

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
        request: EmbeddingGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> EmbeddingGenerateResponse:
        model_name = request.model or ""
        secrets = resolve_provider_secrets(self.secrets, runtime_config)
        require_api_key(
            self.provider,
            model_name,
            secrets,
            self.auth_error_message,
        )
        payload: dict[str, object] = {
            "model": model_name,
            "input": request.input,
        }
        if request.dimensions is not None:
            payload["dimensions"] = request.dimensions
        try:
            result = await self._get_client(model_name, secrets).embeddings.create(**payload)
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
        data = getattr(result, "data", []) or []
        vector = [float(value) for value in getattr(data[0], "embedding", [])] if data else []
        return EmbeddingGenerateResponse(
            provider=self.provider,
            model=model_name,
            embedding=vector,
            dimensions=request.dimensions or len(vector),
            usage=usage_from_response_usage(getattr(result, "usage", None)),
        )
