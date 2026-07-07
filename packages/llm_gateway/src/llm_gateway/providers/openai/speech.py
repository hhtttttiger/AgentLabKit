from __future__ import annotations

from collections.abc import AsyncIterator
from io import BytesIO
from typing import Any

from ...config import ProviderConfig
from ...core.adapters import SpeechStreamAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import (
    ProviderId,
    SpeechStreamChunk,
    SpeechStreamEvent,
    UsageInfo,
)
from ...provider_runtime import RuntimeProviderConfig
from ..shared.common import (
    build_audio_file,
    provider_config_error,
    require_api_key,
    resolve_provider_secrets,
)
from ..shared.error_mapping import map_sdk_error
from ..shared.openai_transport import (
    build_openai_realtime_headers,
    build_openai_realtime_url,
    create_openai_client,
)
from ..shared.openai_compatible_speech import (
    OpenAICompatibleSpeechBatchAdapter,
    OpenAICompatibleSpeechStreamAdapter,
)
from .realtime import RealtimeSessionManager


class OpenAISpeechBatchAdapter(OpenAICompatibleSpeechBatchAdapter):
    def __init__(self, secrets: ProviderConfig, *, client: Any | None = None) -> None:
        super().__init__(
            secrets,
            provider=ProviderId.OPENAI,
            auth_error_message="OpenAI API key is not configured.",
            client=client,
            client_factory=(lambda resolved: create_openai_client(resolved)) if client is None else None,
        )


class OpenAISpeechStreamAdapter(OpenAICompatibleSpeechStreamAdapter):
    def __init__(
        self,
        secrets: ProviderConfig,
        *,
        session_manager: RealtimeSessionManager | None = None,
    ) -> None:
        super().__init__(
            secrets,
            provider=ProviderId.OPENAI,
            auth_error_message="OpenAI API key is not configured.",
            url_builder=build_openai_realtime_url,
            headers_builder=build_openai_realtime_headers,
            session_manager=session_manager,
        )


def _transcription_usage(event: Any) -> UsageInfo | None:
    """Map transcription SSE event usage to gateway UsageInfo.

    OpenAI transcription streaming events may carry usage in two forms:
    - Duration-based: ``{ "type": "duration", "seconds": N }``
    - Token-based: ``{ "type": "tokens", "input_tokens": N, ... }``
    """
    usage = getattr(event, "usage", None)
    if usage is None:
        return None
    usage_type = getattr(usage, "type", None)
    if usage_type == "duration":
        seconds = getattr(usage, "seconds", None)
        return UsageInfo(
            audio_duration_ms=int(float(seconds) * 1000) if seconds is not None else None,
        )
    # Token-based usage.
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)
    audio_tokens = None
    details = getattr(usage, "input_token_details", None)
    if details is not None:
        audio_tokens = getattr(details, "audio_tokens", None)
    return UsageInfo(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


class OpenAITranscriptionStreamAdapter(SpeechStreamAdapter):
    """Streaming speech-to-text via ``/audio/transcriptions`` with SSE.

    OpenAI's transcription API supports ``stream=True`` which returns
    server-sent events:

    - ``transcript.text.delta`` — partial transcript text
    - ``transcript.text.done`` — final complete text with usage

    This adapter buffers incoming audio chunks, sends the complete file
    to the transcription endpoint with streaming enabled, and yields
    :class:`SpeechStreamEvent` for each SSE event.
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
        if self.client is None:
            raise GatewayError(
                GatewayErrorCode.PROVIDER_AUTH_FAILED,
                "OpenAI API key is not configured.",
                provider=self.provider,
                model=model_name,
            )
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
        # Buffer all audio — the transcription API requires the full file.
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

        audio_file = build_audio_file(b"".join(audio_parts), first_chunk.mime_type)
        try:
            stream = await self._get_client(model_name, secrets).audio.transcriptions.create(
                model=model_name,
                file=audio_file,
                language=first_chunk.language,
                stream=True,
            )
            async for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "transcript.text.delta":
                    delta = getattr(event, "delta", None)
                    if delta:
                        yield SpeechStreamEvent(
                            event_type="partial_transcript",
                            provider=self.provider,
                            model=model_name,
                            transcript=delta,
                            is_final=False,
                        )
                elif event_type == "transcript.text.done":
                    text = getattr(event, "text", "")
                    yield SpeechStreamEvent(
                        event_type="final_transcript",
                        provider=self.provider,
                        model=model_name,
                        transcript=text,
                        is_final=True,
                        usage=_transcription_usage(event),
                    )
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
