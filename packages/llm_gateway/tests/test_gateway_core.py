from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from llm_gateway.config import GatewaySettings, ProviderConfig
from llm_gateway.core.adapters import EmbeddingAdapter, RealtimeAdapter, SpeechStreamAdapter, TextAdapter
from llm_gateway.core.registry import ProviderAdapterBundle, ProviderRegistry
from llm_gateway.core.service import GatewayService
from llm_gateway.errors import GatewayError, GatewayErrorCode
from llm_gateway.model_catalog import EnvironmentSecretResolver, ModelCatalogService, ModelResolver, StaticModelCatalogRepository, snapshot_from_model_definitions
from llm_gateway.models import (
    Capability,
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    ModelDefinition,
    ProviderId,
    RealtimeClientEvent,
    RealtimeServerEvent,
    SpeechStreamChunk,
    SpeechStreamEvent,
    TextGenerateRequest,
    TextGenerateResponse,
    TextStreamEvent,
    UsageInfo,
    GeneratedImage,
    ImageGenerateRequest,
    ImageGenerateResponse,
)
from llm_gateway.provider_runtime import RuntimeProviderConfig
from llm_gateway.usage import UsageAttemptRecord, UsageRequestRecord


class DummyTextAdapter(TextAdapter):
    async def generate(
        self,
        request: TextGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> TextGenerateResponse:
        del runtime_config
        return TextGenerateResponse(
            provider=ProviderId.OPENAI,
            model=request.model or "",
            text=f"handled:{request.model}:{request.prompt}",
            finish_reason="stop",
            usage=UsageInfo(input_tokens=12, output_tokens=5, estimated_cost=0.25),
        )

    async def generate_stream(
        self,
        request: TextGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[TextStreamEvent]:
        del runtime_config
        yield TextStreamEvent(
            event_type="completed",
            provider=ProviderId.OPENAI,
            model=request.model or "",
            text=f"handled:{request.model}:{request.prompt}",
            finish_reason="stop",
            usage=UsageInfo(input_tokens=12, output_tokens=5, total_tokens=17, estimated_cost=0.25),
        )


class DummySpeechStreamAdapter(SpeechStreamAdapter):
    def __init__(self) -> None:
        self.first_chunk: SpeechStreamChunk | None = None

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[SpeechStreamEvent]:
        del runtime_config
        self.first_chunk = await anext(chunks)
        yield SpeechStreamEvent(
            event_type="final_transcript",
            provider=ProviderId.OPENAI,
            model=self.first_chunk.model or "",
            transcript=self.first_chunk.model,
            is_final=True,
        )
        yield SpeechStreamEvent(
            event_type="response_completed",
            provider=ProviderId.OPENAI,
            model=self.first_chunk.model or "",
            usage=UsageInfo(input_tokens=8, output_tokens=2, total_tokens=10),
            is_final=True,
        )


class DummyRealtimeAdapter(RealtimeAdapter):
    def __init__(self) -> None:
        self.first_event: RealtimeClientEvent | None = None

    async def session(
        self,
        events: AsyncIterator[RealtimeClientEvent],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[RealtimeServerEvent]:
        del runtime_config
        self.first_event = await anext(events)
        yield RealtimeServerEvent(
            event_type="session_started",
            provider=ProviderId.OPENAI,
            model=self.first_event.model or "",
        )
        yield RealtimeServerEvent(
            event_type="response_completed",
            provider=ProviderId.OPENAI,
            model=self.first_event.model or "",
            usage=UsageInfo(input_tokens=4, output_tokens=6, total_tokens=10),
            is_final=True,
        )


class DummyImageAdapter:
    async def generate(
        self,
        request: ImageGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> ImageGenerateResponse:
        del runtime_config
        return ImageGenerateResponse(
            provider=ProviderId.OPENAI,
            model=request.model or "",
            images=[GeneratedImage(url="memory://generated")],
            usage=UsageInfo(input_tokens=4, output_tokens=0, total_tokens=4, estimated_cost=0.12),
        )


class DummyEmbeddingAdapter(EmbeddingAdapter):
    async def generate(
        self,
        request: EmbeddingGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> EmbeddingGenerateResponse:
        del runtime_config
        return EmbeddingGenerateResponse(
            provider=ProviderId.OPENAI,
            model=request.model or "",
            embedding=[0.1, 0.2, 0.3],
            dimensions=3,
            usage=UsageInfo(input_tokens=3, output_tokens=0, total_tokens=3, estimated_cost=0.01),
        )


class RecordingUsageRecorder:
    def __init__(self) -> None:
        self.requests: list[UsageRequestRecord] = []
        self.attempts: list[UsageAttemptRecord] = []

    async def record_request(self, record: UsageRequestRecord) -> None:
        self.requests.append(record)

    async def record_attempt(self, record: UsageAttemptRecord) -> None:
        self.attempts.append(record)


def build_service(
    settings: GatewaySettings,
    registry: ProviderRegistry,
    usage_recorder: RecordingUsageRecorder | None = None,
) -> GatewayService:
    catalog_service = ModelCatalogService(
        StaticModelCatalogRepository(snapshot_from_model_definitions(settings.models))
    )
    resolver = ModelResolver(
        catalog_service,
        EnvironmentSecretResolver(
            env={},
            defaults=ProviderConfig(api_key="test-openai-key"),
        ),
    )
    return GatewayService(
        settings,
        registry,
        resolver,
        catalog_service,
        usage_recorder=usage_recorder,
    )


@pytest.mark.asyncio
class TestGatewayCore:
    def setup_method(self) -> None:
        settings = GatewaySettings(
            models=[
                ModelDefinition(
                    model_key="logical-model",
                    provider=ProviderId.OPENAI,
                    provider_model_name="provider-model",
                    capabilities={Capability.TEXT},
                )
            ]
        )
        registry = ProviderRegistry()
        registry.register(
            ProviderAdapterBundle(provider=ProviderId.OPENAI, text=DummyTextAdapter())
        )
        self.service = build_service(settings, registry)

    async def test_service_rewrites_to_provider_model_but_returns_logical_model(self):
        response = await self.service.generate_text(
            TextGenerateRequest(model="logical-model", prompt="hello")
        )
        assert response.model == "logical-model"
        assert response.provider == ProviderId.OPENAI
        assert response.text == "handled:provider-model:hello"

    async def test_stream_events_are_rewritten_back_to_logical_model(self):
        events = [
            event
            async for event in self.service.generate_text_stream(
                TextGenerateRequest(model="logical-model", prompt="hello")
            )
        ]
        assert events[0].model == "logical-model"
        assert events[0].text == "handled:provider-model:hello"

    async def test_generate_embedding_rewrites_back_to_logical_model(self):
        settings = GatewaySettings(
            models=[
                ModelDefinition(
                    model_key="kb-embedding",
                    provider=ProviderId.OPENAI,
                    provider_model_name="text-embedding-3-small",
                    capabilities={Capability.EMBEDDING},
                )
            ]
        )
        registry = ProviderRegistry()
        registry.register(
            ProviderAdapterBundle(provider=ProviderId.OPENAI, embedding=DummyEmbeddingAdapter())
        )
        service = build_service(settings, registry)

        response = await service.generate_embedding(
            EmbeddingGenerateRequest(model="kb-embedding", input="hello world")
        )

        assert response.model == "kb-embedding"
        assert response.provider == ProviderId.OPENAI
        assert response.dimensions == 3
        assert response.embedding == [0.1, 0.2, 0.3]

    async def test_unary_requests_record_usage_with_estimated_cost(self):
        recorder = RecordingUsageRecorder()
        settings = GatewaySettings(
            models=[
                ModelDefinition(
                    model_key="logical-model",
                    provider=ProviderId.OPENAI,
                    provider_model_name="provider-model",
                    capabilities={Capability.TEXT},
                )
            ]
        )
        registry = ProviderRegistry()
        registry.register(
            ProviderAdapterBundle(provider=ProviderId.OPENAI, text=DummyTextAdapter())
        )
        service = build_service(settings, registry, usage_recorder=recorder)

        await service.generate_text(TextGenerateRequest(model="logical-model", prompt="hello"))

        request_record = recorder.requests[0]
        attempt_record = recorder.attempts[0]
        assert request_record.capability == "text"
        assert request_record.total_estimated_cost == pytest.approx(0.25)
        assert attempt_record.estimated_cost == pytest.approx(0.25)

    async def test_text_stream_records_usage_from_completed_event(self):
        recorder = RecordingUsageRecorder()
        settings = GatewaySettings(
            models=[
                ModelDefinition(
                    model_key="logical-model",
                    provider=ProviderId.OPENAI,
                    provider_model_name="provider-model",
                    capabilities={Capability.TEXT},
                )
            ]
        )
        registry = ProviderRegistry()
        registry.register(
            ProviderAdapterBundle(provider=ProviderId.OPENAI, text=DummyTextAdapter())
        )
        service = build_service(settings, registry, usage_recorder=recorder)

        events = [event async for event in service.generate_text_stream(TextGenerateRequest(model="logical-model", prompt="hello"))]

        assert events[-1].event_type == "completed"
        request_record = recorder.requests[0]
        attempt_record = recorder.attempts[0]
        assert request_record.total_input_tokens == 12
        assert request_record.total_output_tokens == 5
        assert attempt_record.input_tokens == 12
        assert attempt_record.output_tokens == 5

    async def test_text_stream_completed_event_preserves_usage_after_model_rewrite(self):
        settings = GatewaySettings(
            models=[
                ModelDefinition(
                    model_key="logical-model",
                    provider=ProviderId.OPENAI,
                    provider_model_name="provider-model",
                    capabilities={Capability.TEXT},
                )
            ]
        )
        registry = ProviderRegistry()
        registry.register(
            ProviderAdapterBundle(provider=ProviderId.OPENAI, text=DummyTextAdapter())
        )
        service = build_service(settings, registry)

        events = [event async for event in service.generate_text_stream(TextGenerateRequest(model="logical-model", prompt="hello"))]

        assert events[-1].event_type == "completed"
        assert events[-1].model == "logical-model"
        assert events[-1].usage is not None
        assert events[-1].usage.input_tokens == 12
        assert events[-1].usage.output_tokens == 5
        assert events[-1].usage.total_tokens == 17

    async def test_image_generate_records_usage_when_provider_returns_it(self):
        recorder = RecordingUsageRecorder()
        settings = GatewaySettings(
            models=[
                ModelDefinition(
                    model_key="image-model",
                    provider=ProviderId.OPENAI,
                    provider_model_name="provider-image-model",
                    capabilities={Capability.IMAGE},
                )
            ]
        )
        registry = ProviderRegistry()
        registry.register(
            ProviderAdapterBundle(provider=ProviderId.OPENAI, image=DummyImageAdapter())
        )
        service = build_service(settings, registry, usage_recorder=recorder)

        response = await service.generate_image(ImageGenerateRequest(model="image-model", prompt="cat"))

        assert response.model == "image-model"
        request_record = recorder.requests[0]
        attempt_record = recorder.attempts[0]
        assert request_record.capability == "image"
        assert request_record.total_input_tokens == 4
        assert request_record.total_output_tokens == 0
        assert request_record.total_estimated_cost == pytest.approx(0.12)
        assert attempt_record.input_tokens == 4
        assert attempt_record.output_tokens == 0
        assert attempt_record.estimated_cost == pytest.approx(0.12)
