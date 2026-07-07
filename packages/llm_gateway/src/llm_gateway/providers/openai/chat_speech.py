"""Speech adapters that use the chat completions endpoint with audio content.

Some OpenAI-compatible providers (e.g. Xiaomi MiMo ASR) expose speech
recognition through ``/v1/chat/completions`` by sending audio as a
``input_audio`` content part, rather than the traditional
``/v1/audio/transcriptions`` file-upload endpoint.

These adapters bridge that API shape into the gateway's
:class:`SpeechBatchAdapter` / :class:`SpeechStreamAdapter` interfaces.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from typing import Any

from ...config import ProviderConfig
from ...core.adapters import SpeechBatchAdapter, SpeechStreamAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import (
    ProviderId,
    SpeechStreamChunk,
    SpeechStreamEvent,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
)
from ...provider_runtime import RuntimeProviderConfig
from ...usage_info import UsageInfo
from ..shared.common import (
    provider_config_error,
    require_api_key,
    resolve_provider_secrets,
)
from ..shared.error_mapping import map_sdk_error
from ..shared.openai_transport import create_openai_client


def _build_audio_content(audio: bytes, mime_type: str) -> dict[str, Any]:
    """Build an ``input_audio`` content part for the chat completions API.

    Supports two encoding methods:
    1. Data URL: ``data:{MIME_TYPE};base64,{data}`` (format field optional)
    2. Plain base64 with explicit ``format`` field
    """
    normalized = (mime_type or "").strip().lower()
    b64 = base64.b64encode(audio).decode("ascii")
    # Use data URL format — universally accepted by providers.
    return {
        "type": "input_audio",
        "input_audio": {
            "data": f"data:{normalized};base64,{b64}",
        },
    }


def _extract_asr_options(metadata: dict[str, str]) -> dict[str, Any] | None:
    """Extract ``asr_options`` from request metadata, if present."""
    language = metadata.get("asr_language")
    if language:
        return {"language": language}
    return None


def _map_usage(chunk_or_resp: Any) -> UsageInfo | None:
    """Map chat completion usage to gateway UsageInfo."""
    usage = getattr(chunk_or_resp, "usage", None)
    if usage is None:
        return None
    audio_tokens = None
    seconds = None
    prompt_details = getattr(usage, "prompt_tokens_details", None)
    if prompt_details is not None:
        audio_tokens = getattr(prompt_details, "audio_tokens", None)
    # MiMo returns audio duration in seconds at the usage level.
    seconds = getattr(usage, "seconds", None)
    return UsageInfo(
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
        audio_duration_ms=int(float(seconds) * 1000) if seconds is not None else None,
    )


class OpenAIChatSpeechBatchAdapter(SpeechBatchAdapter):
    """Batch speech-to-text via ``chat.completions`` with audio content.

    Compatible with providers that expose ASR through the chat completions
    endpoint (e.g. MiMo ``mimo-v2.5-asr``).
    """

    def __init__(
        self,
        secrets: ProviderConfig,
        *,
        provider: ProviderId = ProviderId.OPENAI,
        client: Any | None = None,
    ) -> None:
        self.secrets = secrets
        self.provider = provider
        self.client = client

    def _get_client(self, model_name: str, secrets: ProviderConfig):
        if self.client is not None and secrets == self.secrets:
            return self.client
        try:
            client = create_openai_client(secrets)
        except Exception as exc:
            raise provider_config_error(
                provider=self.provider,
                model=model_name,
                exc=exc,
            ) from exc
        if secrets == self.secrets:
            self.client = client
        return client

    async def transcribe(
        self,
        request: SpeechTranscribeRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> SpeechTranscribeResponse:
        model_name = request.model or ""
        secrets = resolve_provider_secrets(self.secrets, runtime_config)
        require_api_key(
            self.provider,
            model_name,
            secrets,
            "OpenAI API key is not configured.",
        )

        audio_part = _build_audio_content(request.audio, request.mime_type)
        asr_options = _extract_asr_options(request.metadata)
        extra_body: dict[str, Any] = {}
        if asr_options:
            extra_body["asr_options"] = asr_options

        try:
            result = await self._get_client(model_name, secrets).chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [audio_part],
                    }
                ],
                **({"extra_body": extra_body} if extra_body else {}),
            )
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc

        transcript = ""
        if result.choices:
            message = getattr(result.choices[0], "message", None)
            if message is not None:
                transcript = getattr(message, "content", "") or ""

        return SpeechTranscribeResponse(
            provider=self.provider,
            model=model_name,
            transcript=transcript,
            language=request.language,
            usage=_map_usage(result),
        )


class OpenAIChatSpeechStreamAdapter(SpeechStreamAdapter):
    """Streaming speech-to-text via ``chat.completions`` with audio content.

    Sends the full audio as a single chat completion request with
    ``stream=True`` and yields partial / final transcript events as
    SSE chunks arrive.
    """

    def __init__(
        self,
        secrets: ProviderConfig,
        *,
        provider: ProviderId = ProviderId.OPENAI,
        client: Any | None = None,
    ) -> None:
        self.secrets = secrets
        self.provider = provider
        self.client = client

    def _get_client(self, model_name: str, secrets: ProviderConfig):
        if self.client is not None and secrets == self.secrets:
            return self.client
        try:
            client = create_openai_client(secrets)
        except Exception as exc:
            raise provider_config_error(
                provider=self.provider,
                model=model_name,
                exc=exc,
            ) from exc
        if secrets == self.secrets:
            self.client = client
        return client

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[SpeechStreamEvent]:
        # Buffer all audio chunks (the chat completions API requires
        # the full audio in a single request — true streaming audio
        # would need a different protocol like WebSocket).
        audio_parts: list[bytes] = []
        first_chunk: SpeechStreamChunk | None = None

        async for chunk in chunks:
            if first_chunk is None:
                first_chunk = chunk
            audio_parts.append(chunk.audio_chunk)
            if chunk.end_of_audio:
                break

        if first_chunk is None:
            return

        model_name = first_chunk.model or ""
        secrets = resolve_provider_secrets(self.secrets, runtime_config)
        require_api_key(
            self.provider,
            model_name,
            secrets,
            "OpenAI API key is not configured.",
        )

        audio_part = _build_audio_content(b"".join(audio_parts), first_chunk.mime_type)
        asr_options = _extract_asr_options(first_chunk.metadata)
        extra_body: dict[str, Any] = {}
        if asr_options:
            extra_body["asr_options"] = asr_options

        accumulated_text = ""
        accumulated_usage: UsageInfo | None = None
        try:
            stream = await self._get_client(model_name, secrets).chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [audio_part],
                    }
                ],
                stream=True,
                **({"extra_body": extra_body} if extra_body else {}),
            )
            async for chunk in stream:
                usage = _map_usage(chunk)
                if usage is not None:
                    accumulated_usage = usage

                # Extract content delta (may be None for role-only or finish chunks).
                content: str | None = None
                finish_reason: str | None = None
                if chunk.choices:
                    delta = getattr(chunk.choices[0], "delta", None)
                    if delta is not None:
                        content = getattr(delta, "content", None)
                    finish_reason = getattr(chunk.choices[0], "finish_reason", None)

                if content is not None:
                    accumulated_text += content

                if finish_reason is not None:
                    # Final chunk — emit accumulated transcript.
                    yield SpeechStreamEvent(
                        event_type="final_transcript",
                        provider=self.provider,
                        model=model_name,
                        transcript=accumulated_text,
                        is_final=True,
                        usage=accumulated_usage,
                    )
                elif content is not None:
                    yield SpeechStreamEvent(
                        event_type="partial_transcript",
                        provider=self.provider,
                        model=model_name,
                        transcript=content,
                        is_final=False,
                    )
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
