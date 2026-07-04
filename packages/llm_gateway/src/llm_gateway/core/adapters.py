from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from ..models import (
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    ImageGenerateRequest,
    ImageGenerateResponse,
    RealtimeClientEvent,
    RealtimeServerEvent,
    SpeechStreamChunk,
    SpeechStreamEvent,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
    TextGenerateRequest,
    TextGenerateResponse,
    TextStreamEvent,
)
from ..provider_runtime import RuntimeProviderConfig


class EmbeddingAdapter(ABC):
    @abstractmethod
    async def generate(
        self,
        request: EmbeddingGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> EmbeddingGenerateResponse:
        raise NotImplementedError


class TextAdapter(ABC):
    @abstractmethod
    async def generate(
        self,
        request: TextGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> TextGenerateResponse:
        raise NotImplementedError

    @abstractmethod
    async def generate_stream(
        self,
        request: TextGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[TextStreamEvent]:
        raise NotImplementedError


class SpeechBatchAdapter(ABC):
    @abstractmethod
    async def transcribe(
        self,
        request: SpeechTranscribeRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> SpeechTranscribeResponse:
        raise NotImplementedError


class SpeechStreamAdapter(ABC):
    @abstractmethod
    async def transcribe_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[SpeechStreamEvent]:
        raise NotImplementedError


class ImageAdapter(ABC):
    @abstractmethod
    async def generate(
        self,
        request: ImageGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> ImageGenerateResponse:
        raise NotImplementedError


class RealtimeAdapter(ABC):
    @abstractmethod
    async def session(
        self,
        events: AsyncIterator[RealtimeClientEvent],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[RealtimeServerEvent]:
        raise NotImplementedError
