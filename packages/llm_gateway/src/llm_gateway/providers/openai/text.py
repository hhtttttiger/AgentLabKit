from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from ...config import ProviderConfig
from ...core.adapters import TextAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import ProviderId, TextGenerateRequest, TextGenerateResponse, TextStreamEvent
from ...provider_runtime import RuntimeProviderConfig
from ...usage_info import usage_from_response_usage
from ..shared.common import provider_config_error, require_api_key, resolve_provider_secrets
from ..shared.error_mapping import map_sdk_error
from ..shared.openai_transport import create_openai_client


class OpenAITextAdapter(TextAdapter):
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

    def _build_payload(
        self,
        request: TextGenerateRequest,
        model_name: str,
        *,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if stream:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
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
            result = await self._get_client(model_name, secrets).chat.completions.create(**payload)
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
        choice = (result.choices or [None])[0]
        text = choice.message.content if choice and choice.message else ""
        finish_reason = choice.finish_reason.value if choice and choice.finish_reason else None
        return TextGenerateResponse(
            provider=self.provider,
            model=model_name,
            text=text or "",
            finish_reason=finish_reason,
            usage=usage_from_response_usage(getattr(result, "usage", None)),
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
        payload = self._build_payload(request, model_name, stream=True)
        try:
            stream = await self._get_client(model_name, secrets).chat.completions.create(**payload)
            collected_text = ""
            async for chunk in stream:
                delta_obj = chunk.choices[0].delta if chunk.choices else None
                delta_text = delta_obj.content if delta_obj and delta_obj.content else None
                if delta_text:
                    collected_text += delta_text
                    yield TextStreamEvent(
                        event_type="delta",
                        provider=self.provider,
                        model=model_name,
                        delta=delta_text,
                    )
                # Stream may carry usage in the final chunk (with stream_options.include_usage)
                if chunk.usage is not None:
                    yield TextStreamEvent(
                        event_type="completed",
                        provider=self.provider,
                        model=model_name,
                        text=collected_text,
                        finish_reason="stop",
                        usage=usage_from_response_usage(chunk.usage),
                    )
                    return
            # Fallback if no usage chunk was sent
            yield TextStreamEvent(
                event_type="completed",
                provider=self.provider,
                model=model_name,
                text=collected_text,
                finish_reason="stop",
            )
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
