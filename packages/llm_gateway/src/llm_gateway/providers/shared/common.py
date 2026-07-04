from __future__ import annotations

from collections.abc import AsyncIterator
from io import BytesIO
from typing import Any
import wave

from ...config import ProviderConfig
from ...core.adapters import ImageAdapter, SpeechBatchAdapter, SpeechStreamAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import (
    GeneratedImage,
    ImageGenerateRequest,
    ImageGenerateResponse,
    ProviderId,
    SpeechStreamChunk,
    SpeechStreamEvent,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
)
from ...provider_runtime import RuntimeProviderConfig
from ...usage_info import usage_from_response_usage


def build_audio_file(audio: bytes, mime_type: str) -> BytesIO:
    normalized = (mime_type or "").strip().lower()
    if normalized == "audio/pcm":
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(audio)
        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"
        return wav_buffer

    suffix = normalized.split("/")[-1] if "/" in normalized else "bin"
    file_obj = BytesIO(audio)
    file_obj.name = f"audio.{suffix}"
    return file_obj


def resolve_provider_secrets(
    defaults: ProviderConfig,
    runtime_config: RuntimeProviderConfig | None,
) -> ProviderConfig:
    if runtime_config is None:
        return defaults
    return ProviderConfig(
        api_key=runtime_config.api_key or defaults.api_key,
        base_url=runtime_config.base_url or defaults.base_url,
        websocket_base_url=runtime_config.websocket_base_url or defaults.websocket_base_url,
        api_version=runtime_config.api_version or defaults.api_version,
    )


def usage_info_from_result(result: object | None):
    if result is None:
        return None
    usage = getattr(result, "usage", None)
    if callable(usage):
        usage = usage()
    return usage_from_response_usage(usage)


class UnsupportedSpeechBatchAdapter(SpeechBatchAdapter):
    def __init__(self, provider: ProviderId, reason: str) -> None:
        self.provider = provider
        self.reason = reason

    async def transcribe(
        self,
        request: SpeechTranscribeRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> SpeechTranscribeResponse:
        del runtime_config
        raise GatewayError(
            GatewayErrorCode.UNSUPPORTED_CAPABILITY,
            self.reason,
            provider=self.provider,
            model=request.model,
        )


class UnsupportedSpeechStreamAdapter(SpeechStreamAdapter):
    def __init__(self, provider: ProviderId, reason: str) -> None:
        self.provider = provider
        self.reason = reason

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[SpeechStreamEvent]:
        del chunks, runtime_config
        raise GatewayError(
            GatewayErrorCode.UNSUPPORTED_CAPABILITY,
            self.reason,
            provider=self.provider,
        )
        yield  # pragma: no cover


class UnsupportedImageAdapter(ImageAdapter):
    def __init__(self, provider: ProviderId, reason: str) -> None:
        self.provider = provider
        self.reason = reason

    async def generate(
        self,
        request: ImageGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> ImageGenerateResponse:
        del runtime_config
        raise GatewayError(
            GatewayErrorCode.UNSUPPORTED_CAPABILITY,
            self.reason,
            provider=self.provider,
            model=request.model,
        )

def image_list_from_result(result: object) -> list[GeneratedImage]:
    data = getattr(result, "data", []) or []
    images: list[GeneratedImage] = []
    for item in data:
        images.append(
            GeneratedImage(
                url=getattr(item, "url", None),
                data_base64=getattr(item, "b64_json", None),
                mime_type="image/png",
            )
        )
    return images


def require_api_key(
    provider: ProviderId,
    model: str,
    secrets: ProviderConfig,
    message: str,
) -> None:
    if not secrets.api_key:
        raise GatewayError(
            GatewayErrorCode.PROVIDER_AUTH_FAILED,
            message,
            provider=provider,
            model=model,
        )


def provider_config_error(
    *,
    provider: ProviderId,
    model: str,
    exc: Exception,
) -> GatewayError:
    if isinstance(exc, GatewayError):
        return exc
    message = str(exc).strip() or "Provider configuration is invalid."
    normalized = message.lower()
    code = GatewayErrorCode.VALIDATION_ERROR
    if any(
        token in normalized
        for token in (
            "api_key",
            "api key",
        )
    ):
        code = GatewayErrorCode.PROVIDER_AUTH_FAILED
    return GatewayError(
        code,
        message,
        provider=provider,
        model=model,
    )
