"""Composite speech adapters that route by model name.

The gateway registry allows one adapter per (provider, capability) pair.
When the OpenAI provider has both ``/audio/transcriptions`` models (e.g.
``gpt-4o-mini-transcribe``) and ``chat.completions`` ASR models (e.g.
``mimo-v2.5-asr``), these routers dispatch to the correct sub-adapter
based on the model name in the request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from ...core.adapters import SpeechBatchAdapter, SpeechStreamAdapter
from ...models import (
    SpeechStreamChunk,
    SpeechStreamEvent,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
)
from ...provider_runtime import RuntimeProviderConfig


class CompositeSpeechBatchAdapter(SpeechBatchAdapter):
    """Routes :class:`SpeechTranscribeRequest` by model name.

    Models listed in *chat_models* go to the chat-completions adapter;
    everything else goes to the default (audio.transcriptions) adapter.
    """

    def __init__(
        self,
        default: SpeechBatchAdapter,
        chat: SpeechBatchAdapter,
        *,
        chat_models: set[str],
    ) -> None:
        self.default = default
        self.chat = chat
        self.chat_models = chat_models

    def _resolve(self, model: str | None) -> SpeechBatchAdapter:
        if model and model in self.chat_models:
            return self.chat
        return self.default

    async def transcribe(
        self,
        request: SpeechTranscribeRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> SpeechTranscribeResponse:
        return await self._resolve(request.model).transcribe(request, runtime_config)


class CompositeSpeechStreamAdapter(SpeechStreamAdapter):
    """Routes :class:`SpeechStreamChunk` by model name.

    Models listed in *chat_models* go to the chat-completions stream
    adapter; everything else goes to the default (Realtime WebSocket)
    adapter.
    """

    def __init__(
        self,
        default: SpeechStreamAdapter,
        chat: SpeechStreamAdapter,
        *,
        chat_models: set[str],
    ) -> None:
        self.default = default
        self.chat = chat
        self.chat_models = chat_models

    def _resolve(self, model: str | None) -> SpeechStreamAdapter:
        if model and model in self.chat_models:
            return self.chat
        return self.default

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[SpeechStreamEvent]:
        # We need to peek the first chunk to determine the model.
        first_chunk = None
        async for chunk in chunks:
            first_chunk = chunk
            break

        if first_chunk is None:
            return

        adapter = self._resolve(first_chunk.model)

        async def _prepend_first():
            yield first_chunk
            async for chunk in chunks:
                yield chunk

        async for event in adapter.transcribe_stream(_prepend_first(), runtime_config):
            yield event
