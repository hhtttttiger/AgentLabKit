from __future__ import annotations

from collections.abc import AsyncIterator

from ..models import (
    ProviderId,
    SpeechStreamChunk,
    SpeechStreamEvent,
    SpeechTranscribeRequest,
)
from ..provider_runtime import RuntimeProviderConfig
from .adapters import SpeechBatchAdapter, SpeechStreamAdapter


class BufferedSpeechStreamAdapter(SpeechStreamAdapter):
    """Fallback stream adapter that buffers audio and emits a final transcript event.

    This is not a true low-latency streaming implementation, but it gives the
    gateway a consistent stream surface until provider-native partial transcript
    adapters are implemented.
    """

    def __init__(
        self,
        batch_adapter: SpeechBatchAdapter,
        *,
        provider: ProviderId,
    ) -> None:
        self.batch_adapter = batch_adapter
        self.provider = provider

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[SpeechStreamEvent]:
        first_chunk: SpeechStreamChunk | None = None
        audio_parts: list[bytes] = []

        async for chunk in chunks:
            if first_chunk is None:
                first_chunk = chunk
            audio_parts.append(chunk.audio_chunk)
            if chunk.end_of_audio:
                break

        if first_chunk is None:
            return

        response = await self.batch_adapter.transcribe(
            SpeechTranscribeRequest(
                provider=first_chunk.provider or self.provider,
                model=first_chunk.model,
                audio=b"".join(audio_parts),
                mime_type=first_chunk.mime_type,
                language=first_chunk.language,
                trace_id=first_chunk.trace_id,
                metadata=first_chunk.metadata,
            ),
            runtime_config,
        )

        yield SpeechStreamEvent(
            event_type="final_transcript",
            provider=response.provider,
            model=response.model,
            transcript=response.transcript,
            is_final=True,
            usage=response.usage,
            error=response.error,
        )
