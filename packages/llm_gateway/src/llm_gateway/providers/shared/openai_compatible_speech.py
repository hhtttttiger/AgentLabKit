from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from ...config import ProviderConfig
from ...core.adapters import SpeechBatchAdapter, SpeechStreamAdapter
from ...errors import GatewayError, GatewayErrorCode
from ...models import (
    ProviderId,
    RealtimeClientEvent,
    SpeechStreamChunk,
    SpeechStreamEvent,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
)
from ...provider_runtime import RuntimeProviderConfig
from ...usage_info import accumulate_usage
from ..openai.realtime import RealtimeConnectionConfig, RealtimeSessionManager
from .common import (
    build_audio_file,
    provider_config_error,
    require_api_key,
    resolve_provider_secrets,
    usage_info_from_result,
)
from .error_mapping import map_sdk_error


class OpenAICompatibleSpeechBatchAdapter(SpeechBatchAdapter):
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
            self.auth_error_message,
        )
        audio_file = build_audio_file(request.audio, request.mime_type)
        try:
            result = await self._get_client(model_name, secrets).audio.transcriptions.create(
                model=model_name,
                file=audio_file,
                language=request.language,
            )
        except Exception as exc:
            raise map_sdk_error(exc, provider=self.provider, model=model_name) from exc
        usage_info = usage_info_from_result(result)
        if usage_info is not None and getattr(result, "duration", None) is not None:
            usage_info.audio_duration_ms = int(float(result.duration) * 1000)
        return SpeechTranscribeResponse(
            provider=self.provider,
            model=model_name,
            transcript=getattr(result, "text", ""),
            language=request.language,
            usage=usage_info,
        )


class OpenAICompatibleSpeechStreamAdapter(SpeechStreamAdapter):
    def __init__(
        self,
        secrets: ProviderConfig,
        *,
        provider: ProviderId,
        auth_error_message: str,
        url_builder: Callable[[ProviderConfig, str], str],
        headers_builder: Callable[[ProviderConfig], dict[str, str]],
        session_manager: RealtimeSessionManager | None = None,
    ) -> None:
        self.secrets = secrets
        self.provider = provider
        self.auth_error_message = auth_error_message
        self.url_builder = url_builder
        self.headers_builder = headers_builder
        self.session_manager = session_manager or RealtimeSessionManager()

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[SpeechStreamEvent]:
        try:
            first_chunk = await anext(chunks)
        except StopAsyncIteration:
            return

        model_name = first_chunk.model or ""
        secrets = resolve_provider_secrets(self.secrets, runtime_config)
        require_api_key(
            self.provider,
            model_name,
            secrets,
            self.auth_error_message,
        )
        transport_model = (
            first_chunk.metadata.get("realtime_transport_model")
            or first_chunk.metadata.get("playback_model")
            or model_name
        )
        config = RealtimeConnectionConfig(
            provider=self.provider,
            model=transport_model,
            url=self.url_builder(secrets, transport_model),
            headers=self.headers_builder(secrets),
        )

        async def speech_events() -> AsyncIterator[RealtimeClientEvent]:
            session_metadata = {
                "session_type": "transcription",
                "transcription_only": "true",
                "input_audio_transcription_model": model_name,
                "input_audio_format": first_chunk.mime_type,
            }
            yield RealtimeClientEvent(
                event_type="session_start",
                provider=self.provider,
                model=model_name,
                trace_id=first_chunk.trace_id,
                metadata=session_metadata,
            )

            async def emit_audio(chunk: SpeechStreamChunk) -> AsyncIterator[RealtimeClientEvent]:
                if chunk.audio_chunk:
                    yield RealtimeClientEvent(
                        event_type="audio_chunk",
                        provider=self.provider,
                        model=chunk.model,
                        audio_chunk=chunk.audio_chunk,
                        trace_id=chunk.trace_id,
                        metadata=session_metadata,
                    )
                if chunk.end_of_audio:
                    yield RealtimeClientEvent(
                        event_type="audio_commit",
                        provider=self.provider,
                        model=chunk.model,
                        trace_id=chunk.trace_id,
                        metadata=session_metadata,
                    )

            async for event in emit_audio(first_chunk):
                yield event

            async for chunk in chunks:
                async for event in emit_audio(chunk):
                    yield event
                if chunk.end_of_audio:
                    break

        pending_final_event: SpeechStreamEvent | None = None
        accumulated_usage = None
        async for event in self.session_manager.stream(config, speech_events()):
            if event.event_type == "response_completed":
                accumulated_usage = accumulate_usage(accumulated_usage, event.usage)
                if pending_final_event is not None:
                    yield pending_final_event.model_copy(update={"usage": accumulated_usage})
                    pending_final_event = None
                continue
            if event.event_type == "partial_transcript":
                if pending_final_event is not None:
                    yield pending_final_event.model_copy(update={"usage": accumulated_usage})
                    pending_final_event = None
                yield SpeechStreamEvent(
                    event_type=event.event_type,
                    provider=event.provider,
                    model=event.model,
                    transcript=event.transcript,
                    is_final=event.is_final,
                    error=event.error,
                )
                continue
            if event.event_type != "final_transcript":
                continue
            pending_final_event = SpeechStreamEvent(
                event_type=event.event_type,
                provider=event.provider,
                model=event.model,
                transcript=event.transcript,
                is_final=event.is_final,
                usage=accumulated_usage,
                error=event.error,
            )
        if pending_final_event is not None:
            yield pending_final_event.model_copy(update={"usage": accumulated_usage})
