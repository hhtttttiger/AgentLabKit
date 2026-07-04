from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from ...config import ProviderConfig
from ...core.adapters import TextAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import ProviderId, TextGenerateRequest, TextGenerateResponse, TextStreamEvent, UsageInfo
from ...provider_runtime import RuntimeProviderConfig
from ..shared.common import provider_config_error, require_api_key, resolve_provider_secrets
from ..shared.error_mapping import map_sdk_error
from .clients import create_anthropic_client


class AnthropicTextAdapter(TextAdapter):
    def __init__(
        self,
        secrets: ProviderConfig,
        *,
        client: Any | None = None,
        client_factory: Callable[[ProviderConfig], Any] | None = None,
    ) -> None:
        self.secrets = secrets
        self.provider = ProviderId.ANTHROPIC
        self.auth_error_message = "Anthropic API key is not configured."
        self.client = client
        self.client_factory = client_factory or (
            (lambda resolved: create_anthropic_client(resolved)) if client is None else None
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

    def _build_payload(
        self,
        request: TextGenerateRequest,
        model_name: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_output_tokens or 4096,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        return payload

    async def generate(
        self,
        request: TextGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> TextGenerateResponse:
        model_name = request.model or ""
        secrets = resolve_provider_secrets(self.secrets, runtime_config)
        require_api_key(
            self.provider,
            model_name,
            secrets,
            self.auth_error_message,
        )
        payload = self._build_payload(request, model_name)
        try:
            result = await self._get_client(model_name, secrets).messages.create(**payload)
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
        text = result.content[0].text if result.content else ""
        usage = None
        if result.usage:
            usage = UsageInfo(
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
            )
        return TextGenerateResponse(
            provider=self.provider,
            model=model_name,
            text=text,
            finish_reason=result.stop_reason.value if result.stop_reason else None,
            usage=usage,
        )

    async def generate_stream(
        self,
        request: TextGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[TextStreamEvent]:
        model_name = request.model or ""
        secrets = resolve_provider_secrets(self.secrets, runtime_config)
        require_api_key(
            self.provider,
            model_name,
            secrets,
            self.auth_error_message,
        )
        payload = self._build_payload(request, model_name)
        try:
            async with self._get_client(model_name, secrets).messages.stream(**payload) as stream:
                collected_text = ""
                async for text in stream.text_stream:
                    collected_text += text
                    yield TextStreamEvent(
                        event_type="delta",
                        provider=self.provider,
                        model=model_name,
                        delta=text,
                    )
                final_message = await stream.get_final_message()
                usage = None
                if final_message.usage:
                    usage = UsageInfo(
                        input_tokens=final_message.usage.input_tokens,
                        output_tokens=final_message.usage.output_tokens,
                    )
                yield TextStreamEvent(
                    event_type="completed",
                    provider=self.provider,
                    model=model_name,
                    text=collected_text,
                    finish_reason=final_message.stop_reason.value if final_message.stop_reason else None,
                    usage=usage,
                )
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
