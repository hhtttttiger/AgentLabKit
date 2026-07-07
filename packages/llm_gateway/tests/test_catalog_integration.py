from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from llm_gateway.config import GatewaySettings, ProviderConfig
from llm_gateway.core.adapters import RealtimeAdapter, SpeechBatchAdapter, SpeechStreamAdapter, TextAdapter
from llm_gateway.core.registry import ProviderAdapterBundle, ProviderRegistry
from llm_gateway.core.service import GatewayService
from llm_gateway.errors import GatewayError, GatewayErrorCode
from llm_gateway.model_catalog import EnvironmentSecretResolver, ModelCatalogService, ModelResolver, SqlAlchemyModelCatalogRepository
from llm_gateway.model_catalog.errors import CatalogError, CatalogErrorCode
from alkit_db.base import Base
from llm_gateway.model_catalog.orm_models import (
    LlmCatalogRevisionOrm,
    LlmConnectionProfileOrm,
    LlmFeatureDefinitionOrm,
    LlmModelBindingOrm,
    LlmModelFeatureOrm,
    LlmModelOrm,
    LlmModelInstanceOrm,
)
from llm_gateway.models import (
    Capability,
    ModelRef,
    ProviderId,
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
from llm_gateway.provider_runtime import RuntimeProviderConfig


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@dataclass
class CatalogHarness:
    database_url: str
    sync_session_factory: sessionmaker[Session]
    async_session_factory: object


class _AsyncSyncSession:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def execute(self, statement):
        return self._session.execute(statement)


class _AsyncSyncSessionContext:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    async def __aenter__(self) -> _AsyncSyncSession:
        self._session = self._session_factory()
        return _AsyncSyncSession(self._session)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self._session is not None
        self._session.close()
        self._session = None


class _AsyncSyncSessionFactory:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> _AsyncSyncSessionContext:
        return _AsyncSyncSessionContext(self._session_factory)


class RecordingTextAdapter(TextAdapter):
    def __init__(self) -> None:
        self.generate_requests: list[TextGenerateRequest] = []
        self.generate_runtime_configs: list[RuntimeProviderConfig] = []
        self.stream_requests: list[TextGenerateRequest] = []
        self.stream_runtime_configs: list[RuntimeProviderConfig] = []

    async def generate(
        self,
        request: TextGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> TextGenerateResponse:
        self.generate_requests.append(request)
        self.generate_runtime_configs.append(runtime_config)
        return TextGenerateResponse(
            provider=request.provider or ProviderId.OPENAI,
            model=request.model or "",
            text=f"text:{request.model}:{request.prompt}",
            finish_reason="stop",
        )

    async def generate_stream(
        self,
        request: TextGenerateRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[TextStreamEvent]:
        self.stream_requests.append(request)
        self.stream_runtime_configs.append(runtime_config)
        yield TextStreamEvent(
            event_type="completed",
            provider=request.provider or ProviderId.OPENAI,
            model=request.model or "",
            text=f"stream:{request.model}:{request.prompt}",
            finish_reason="stop",
        )


class RecordingSpeechBatchAdapter(SpeechBatchAdapter):
    def __init__(self) -> None:
        self.requests: list[SpeechTranscribeRequest] = []
        self.runtime_configs: list[RuntimeProviderConfig] = []

    async def transcribe(
        self,
        request: SpeechTranscribeRequest,
        runtime_config: RuntimeProviderConfig,
    ) -> SpeechTranscribeResponse:
        self.requests.append(request)
        self.runtime_configs.append(runtime_config)
        return SpeechTranscribeResponse(
            provider=request.provider or ProviderId.OPENAI,
            model=request.model or "",
            transcript=request.audio.decode("utf-8"),
            language=request.language,
        )


class RecordingSpeechStreamAdapter(SpeechStreamAdapter):
    def __init__(self) -> None:
        self.first_chunk: SpeechStreamChunk | None = None
        self.first_runtime_config: RuntimeProviderConfig | None = None

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[SpeechStreamChunk],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[SpeechStreamEvent]:
        self.first_chunk = await anext(chunks)
        self.first_runtime_config = runtime_config
        yield SpeechStreamEvent(
            event_type="final_transcript",
            provider=self.first_chunk.provider or ProviderId.OPENAI,
            model=self.first_chunk.model or "",
            transcript="stream:ok",
            is_final=True,
        )


class RecordingRealtimeAdapter(RealtimeAdapter):
    def __init__(self) -> None:
        self.first_event: RealtimeClientEvent | None = None
        self.first_runtime_config: RuntimeProviderConfig | None = None

    async def session(
        self,
        events: AsyncIterator[RealtimeClientEvent],
        runtime_config: RuntimeProviderConfig,
    ) -> AsyncIterator[RealtimeServerEvent]:
        self.first_event = await anext(events)
        self.first_runtime_config = runtime_config
        yield RealtimeServerEvent(
            event_type="session_started",
            provider=self.first_event.provider or ProviderId.OPENAI,
            model=self.first_event.model or "",
        )


@pytest.fixture
def catalog_harness(tmp_path: Path) -> CatalogHarness:
    database_path = tmp_path / "catalog.db"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    sync_session_factory = sessionmaker(engine, expire_on_commit=False)

    with sync_session_factory() as session:
        session.add_all(
            [
                LlmConnectionProfileOrm(
                    id=101,
                    profile_key="openai.primary",
                    display_name="OpenAI Primary",
                    provider="openai",
                    base_url="https://api.openai.example/v1",
                    websocket_base_url=None,
                    api_version=None,
                    region="us-east-1",
                    extra_json={"tier": "gold"},
                    is_enabled=True,
                ),
                LlmModelOrm(
                    id=201,
                    model_key="gateway.text.primary",
                    type="text",
                    model_name="gpt-4.1-mini",
                    display_name="Gateway Text Primary",
                    description="Primary text card",
                    connection_profile_id=101,
                    tags_json=["text"],
                    routing_policy_json={"strategy": "priority"},
                    retry_policy_json={},
                    is_enabled=True,
                ),
                LlmModelOrm(
                    id=202,
                    model_key="gateway.text.secondary",
                    type="text",
                    model_name="gpt-4o-mini",
                    display_name="Gateway Text Secondary",
                    description="Secondary text card",
                    connection_profile_id=101,
                    tags_json=["text"],
                    routing_policy_json={"strategy": "priority"},
                    retry_policy_json={},
                    is_enabled=True,
                ),
                LlmModelOrm(
                    id=203,
                    model_key="gateway.voice.catalog",
                    type="speech",
                    model_name="gpt-4o-mini-transcribe",
                    display_name="Gateway Voice Catalog",
                    description="Speech card",
                    connection_profile_id=101,
                    tags_json=["speech"],
                    routing_policy_json={"strategy": "priority"},
                    retry_policy_json={},
                    is_enabled=True,
                ),
                LlmModelOrm(
                    id=204,
                    model_key="gateway.voice.stream.catalog",
                    type="speech",
                    model_name="gpt-4o-mini-transcribe",
                    display_name="Gateway Voice Stream Catalog",
                    description="Speech stream card",
                    connection_profile_id=101,
                    tags_json=["speech", "stream"],
                    routing_policy_json={"strategy": "priority"},
                    retry_policy_json={},
                    is_enabled=True,
                ),
                LlmModelOrm(
                    id=205,
                    model_key="gateway.realtime.catalog",
                    type="speech",
                    model_name="gpt-realtime-1.5",
                    display_name="Gateway Realtime Catalog",
                    description="Realtime card",
                    connection_profile_id=101,
                    tags_json=["realtime"],
                    routing_policy_json={"strategy": "priority"},
                    retry_policy_json={},
                    is_enabled=True,
                ),
                LlmModelInstanceOrm(
                    id=301,
                    instance_key="gateway.text.primary.openai",
                    model_id=201,
                    provider_deployment_name=None,
                    region="us-east-1",
                    priority=1,
                    weight=100,
                    default_timeout_ms=30000,
                    extra_json={"temperature": "0.2"},
                    is_enabled=True,
                    is_healthy=True,
                ),
                LlmModelInstanceOrm(
                    id=302,
                    instance_key="gateway.text.secondary.openai",
                    model_id=202,
                    provider_deployment_name=None,
                    region="us-east-1",
                    priority=1,
                    weight=100,
                    default_timeout_ms=30000,
                    extra_json={"temperature": "0.3"},
                    is_enabled=True,
                    is_healthy=True,
                ),
                LlmModelInstanceOrm(
                    id=303,
                    instance_key="gateway.voice.catalog.batch",
                    model_id=203,
                    provider_deployment_name=None,
                    region="us-east-1",
                    priority=1,
                    weight=100,
                    default_timeout_ms=30000,
                    extra_json={},
                    is_enabled=True,
                    is_healthy=True,
                ),
                LlmModelInstanceOrm(
                    id=304,
                    instance_key="gateway.voice.catalog.stream",
                    model_id=204,
                    provider_deployment_name=None,
                    region="us-east-1",
                    priority=1,
                    weight=100,
                    default_timeout_ms=30000,
                    extra_json={},
                    is_enabled=True,
                    is_healthy=True,
                ),
                LlmModelInstanceOrm(
                    id=305,
                    instance_key="gateway.realtime.catalog.openai",
                    model_id=205,
                    provider_deployment_name=None,
                    region="us-east-1",
                    priority=1,
                    weight=100,
                    default_timeout_ms=30000,
                    extra_json={},
                    is_enabled=True,
                    is_healthy=True,
                ),
                LlmModelBindingOrm(
                    id=401,
                    binding_key="gateway.default_text",
                    display_name="Gateway Default Text",
                    capability="text",
                    model_id=201,
                    metadata_json={},
                    is_enabled=True,
                ),
                LlmModelBindingOrm(
                    id=402,
                    binding_key="gateway.default_speech_batch",
                    display_name="Gateway Default Speech Batch",
                    capability="speech_batch",
                    model_id=203,
                    metadata_json={},
                    is_enabled=True,
                ),
                LlmModelBindingOrm(
                    id=403,
                    binding_key="gateway.default_speech_stream",
                    display_name="Gateway Default Speech Stream",
                    capability="speech_stream",
                    model_id=204,
                    metadata_json={},
                    is_enabled=True,
                ),
                LlmModelBindingOrm(
                    id=404,
                    binding_key="gateway.default_realtime",
                    display_name="Gateway Default Realtime",
                    capability="realtime",
                    model_id=205,
                    metadata_json={},
                    is_enabled=True,
                ),
                LlmCatalogRevisionOrm(
                    id=501,
                    revision=1,
                ),
            ]
        )
        session.commit()

    return CatalogHarness(
        database_url=database_url,
        sync_session_factory=sync_session_factory,
        async_session_factory=_AsyncSyncSessionFactory(sync_session_factory),
    )


@pytest.fixture
def database_service(catalog_harness: CatalogHarness):
    text_adapter = RecordingTextAdapter()
    speech_batch_adapter = RecordingSpeechBatchAdapter()
    speech_stream_adapter = RecordingSpeechStreamAdapter()
    realtime_adapter = RecordingRealtimeAdapter()
    settings = GatewaySettings(
        catalog={"database_url": catalog_harness.database_url},
        openai=ProviderConfig(api_key="openai-key"),
    )
    registry = ProviderRegistry()
    registry.register(
        ProviderAdapterBundle(
            provider=ProviderId.OPENAI,
            text=text_adapter,
            speech_batch=speech_batch_adapter,
            speech_stream=speech_stream_adapter,
            realtime=realtime_adapter,
        )
    )
    catalog_service = ModelCatalogService(
        SqlAlchemyModelCatalogRepository(catalog_harness.async_session_factory)
    )
    resolver = ModelResolver(
        catalog_service,
        EnvironmentSecretResolver(
            env={
                "OPENAI_API_KEY": "openai-key",
            },
            defaults=settings.openai,
        ),
    )
    service = GatewayService(settings, registry, resolver, catalog_service)
    return catalog_harness, service, text_adapter, speech_batch_adapter, speech_stream_adapter, realtime_adapter


@pytest.mark.asyncio
async def test_database_catalog_routes_text_and_stream_requests(database_service):
    _, service, text_adapter, _, _, _ = database_service

    response = await service.generate_text(TextGenerateRequest(model=None, prompt="hello"))
    events = [
        event
        async for event in service.generate_text_stream(
            TextGenerateRequest(model=None, prompt="stream-hello")
        )
    ]

    assert response.model == "gateway.text.primary"
    assert response.text == "text:gpt-4.1-mini:hello"
    assert text_adapter.generate_requests[0].model == "gpt-4.1-mini"
    assert text_adapter.generate_runtime_configs[0].api_key == "openai-key"
    assert events[0].model == "gateway.text.primary"
    assert events[0].text == "stream:gpt-4.1-mini:stream-hello"
    assert text_adapter.stream_requests[0].model == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_database_catalog_routes_batch_stream_and_realtime_requests(database_service):
    _, service, _, speech_batch_adapter, speech_stream_adapter, realtime_adapter = database_service

    batch = await service.transcribe_speech(
        SpeechTranscribeRequest(
            model=None,
            audio=b"batch-audio",
            mime_type="audio/wav",
        )
    )

    async def chunks() -> AsyncIterator[SpeechStreamChunk]:
        yield SpeechStreamChunk(
            model=None,
            audio_chunk=b"abc",
            mime_type="audio/wav",
            end_of_audio=True,
            metadata={"realtime_transport_model": "gateway.realtime.catalog"},
        )

    stream_events = [
        event
        async for event in service.transcribe_speech_stream(
            chunks(),
            model_key=None,
            provider=None,
        )
    ]

    async def realtime_events() -> AsyncIterator[RealtimeClientEvent]:
        yield RealtimeClientEvent(
            event_type="session_start",
            model=None,
        )

    realtime_results = [
        event
        async for event in service.run_realtime_session(
            realtime_events(),
            model_key=None,
            provider=None,
        )
    ]

    assert batch.model == "gateway.voice.catalog"
    assert batch.transcript == "batch-audio"
    assert speech_batch_adapter.requests[0].model == "gpt-4o-mini-transcribe"
    assert speech_batch_adapter.runtime_configs[0].api_key == "openai-key"
    assert speech_stream_adapter.first_chunk is not None
    assert speech_stream_adapter.first_chunk.model == "gpt-4o-mini-transcribe"
    assert speech_stream_adapter.first_chunk.metadata["realtime_transport_model"] == "gpt-realtime-1.5"
    assert stream_events[0].model == "gateway.voice.stream.catalog"
    assert realtime_adapter.first_event is not None
    assert realtime_adapter.first_event.model == "gpt-realtime-1.5"
    assert realtime_adapter.first_runtime_config is not None
    assert realtime_results[0].model == "gateway.realtime.catalog"


@pytest.mark.asyncio
async def test_database_catalog_binding_switch_takes_effect_without_env_changes(database_service):
    harness, service, text_adapter, _, _, _ = database_service

    first = await service.generate_text(TextGenerateRequest(model=None, prompt="first"))

    with harness.sync_session_factory() as session:
        binding = session.get(LlmModelBindingOrm, 401)
        assert binding is not None
        binding.model_id = 202
        session.add(LlmCatalogRevisionOrm(id=502, revision=2))
        session.commit()

    second = await service.generate_text(TextGenerateRequest(model=None, prompt="second"))

    assert first.model == "gateway.text.primary"
    assert second.model == "gateway.text.secondary"
    assert text_adapter.generate_requests[-1].model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_database_catalog_list_models_keeps_card_capabilities_without_instances(database_service):
    harness, service, _, _, _, _ = database_service

    with harness.sync_session_factory() as session:
        session.add(
            LlmModelOrm(
                id=260,
                model_key="catalog.prefilled.image",
                type="image",
                model_name="gpt-image-1",
                display_name="Catalog Prefilled Image",
                description="Prefilled card without instance",
                connection_profile_id=101,
                tags_json=["image"],
                routing_policy_json={},
                retry_policy_json={},
                is_enabled=True,
            )
        )
        session.add(
            LlmCatalogRevisionOrm(id=560, revision=3)
        )
        session.commit()

    models = await service.catalog_service.list_models()
    summary = next(item for item in models if item.model_key == "catalog.prefilled.image")

    assert summary.capabilities == {Capability.IMAGE}
    assert summary.providers == set()


@pytest.mark.asyncio
async def test_database_catalog_resolver_filters_instances_by_required_features(database_service):
    harness, service, _, _, _, _ = database_service

    with harness.sync_session_factory() as session:
        session.add(
            LlmModelInstanceOrm(
                id=306,
                instance_key="gateway.text.primary.openai.tools",
                model_id=201,
                provider_deployment_name=None,
                region="us-east-1",
                priority=2,
                weight=100,
                default_timeout_ms=30000,
                extra_json={},
                is_enabled=True,
                is_healthy=True,
            )
        )
        session.add(
            LlmFeatureDefinitionOrm(
                id=601,
                feature_key="function_call",
                display_name="Function Call",
                description=None,
                value_type="boolean",
                allowed_values_json=[],
                is_filterable=True,
                is_routable=True,
                is_enabled=True,
            )
        )
        session.add_all(
            [
                LlmModelFeatureOrm(
                    id=701,
                    model_id=201,
                    feature_id=601,
                    is_supported=True,
                    value_json=True,
                    source="manual",
                    remark=None,
                ),
            ]
        )
        session.commit()

    routes, _ = await service.resolver.resolve(
        ModelRef.model("gateway.text.primary"),
        capability_hint=Capability.TEXT,
        required_features={"function_call": True},
    )
    route = routes[0]

    assert route.instance_key == "gateway.text.primary.openai"
    assert route.provider_model_name == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_database_catalog_resolver_rejects_non_routable_feature_requirements(database_service):
    harness, service, _, _, _, _ = database_service

    with harness.sync_session_factory() as session:
        session.add(
            LlmFeatureDefinitionOrm(
                id=602,
                feature_key="json_mode",
                display_name="Json Mode",
                description=None,
                value_type="boolean",
                allowed_values_json=[],
                is_filterable=True,
                is_routable=False,
                is_enabled=True,
            )
        )
        session.add(
            LlmModelFeatureOrm(
                id=702,
                model_id=201,
                feature_id=602,
                is_supported=True,
                value_json=True,
                source="manual",
                remark=None,
            )
        )
        session.commit()

    with pytest.raises(CatalogError) as context:
        await service.resolver.resolve(
            ModelRef.model("gateway.text.primary"),
            capability_hint=Capability.TEXT,
            required_features={"json_mode": True},
        )

    assert context.value.code == CatalogErrorCode.FEATURE_REQUIREMENT_NOT_SATISFIED


@pytest.mark.asyncio
async def test_database_catalog_gateway_request_routes_using_required_features(database_service):
    harness, service, text_adapter, _, _, _ = database_service

    with harness.sync_session_factory() as session:
        session.add(
            LlmModelInstanceOrm(
                id=307,
                instance_key="gateway.text.primary.openai.tools",
                model_id=201,
                provider_deployment_name=None,
                region="us-east-1",
                priority=2,
                weight=100,
                default_timeout_ms=30000,
                extra_json={},
                is_enabled=True,
                is_healthy=True,
            )
        )
        session.add(
            LlmFeatureDefinitionOrm(
                id=603,
                feature_key="function_call",
                display_name="Function Call",
                description=None,
                value_type="boolean",
                allowed_values_json=[],
                is_filterable=True,
                is_routable=True,
                is_enabled=True,
            )
        )
        session.add_all(
            [
                LlmModelFeatureOrm(
                    id=703,
                    model_id=201,
                    feature_id=603,
                    is_supported=True,
                    value_json=True,
                    source="manual",
                    remark=None,
                ),
            ]
        )
        session.commit()

    response = await service.generate_text(
        TextGenerateRequest(
            model="gateway.text.primary",
            prompt="hello",
            required_features={"function_call": True},
        )
    )

    assert response.model == "gateway.text.primary"
    assert response.text == "text:gpt-4.1-mini:hello"
    assert text_adapter.generate_requests[-1].model == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_database_catalog_instance_endpoint_url_overrides_profile_base_url(
    database_service,
):
    harness, service, text_adapter, _, _, _ = database_service

    with harness.sync_session_factory() as session:
        instance = session.get(LlmModelInstanceOrm, 301)
        assert instance is not None
        instance.extra_json = {"endpointUrl": "https://instance.example.com/custom/v1/"}
        session.commit()

    await service.generate_text(TextGenerateRequest(model=None, prompt="hello"))

    assert text_adapter.generate_runtime_configs[-1].base_url == "https://instance.example.com/custom/v1/"


@pytest.mark.asyncio
async def test_database_catalog_gateway_request_maps_feature_requirement_errors(database_service):
    harness, service, _, _, _, _ = database_service

    with harness.sync_session_factory() as session:
        session.add(
            LlmFeatureDefinitionOrm(
                id=604,
                feature_key="json_mode",
                display_name="Json Mode",
                description=None,
                value_type="boolean",
                allowed_values_json=[],
                is_filterable=True,
                is_routable=False,
                is_enabled=True,
            )
        )
        session.add(
            LlmModelFeatureOrm(
                id=704,
                model_id=201,
                feature_id=604,
                is_supported=True,
                value_json=True,
                source="manual",
                remark=None,
            )
        )
        session.commit()

    with pytest.raises(GatewayError) as context:
        await service.generate_text(
            TextGenerateRequest(
                model="gateway.text.primary",
                prompt="hello",
                required_features={"json_mode": True},
            )
        )

    assert context.value.code == GatewayErrorCode.FEATURE_REQUIREMENT_NOT_SATISFIED


@pytest.mark.asyncio
async def test_database_catalog_rejects_feature_values_outside_definition(database_service):
    harness, service, text_adapter, _, _, _ = database_service

    with harness.sync_session_factory() as session:
        session.add(
            LlmFeatureDefinitionOrm(
                id=605,
                feature_key="response_format",
                display_name="Response Format",
                description=None,
                value_type="string",
                allowed_values_json=["json_object"],
                is_filterable=True,
                is_routable=True,
                is_enabled=True,
            )
        )
        session.add(
            LlmModelFeatureOrm(
                id=705,
                model_id=201,
                feature_id=605,
                is_supported=True,
                value_json="text",
                source="manual",
                remark=None,
            )
        )
        session.commit()

    with pytest.raises(GatewayError) as context:
        await service.generate_text(
            TextGenerateRequest(
                model="gateway.text.primary",
                prompt="hello",
                required_features={"response_format": "text"},
            )
        )

    assert context.value.code == GatewayErrorCode.FEATURE_REQUIREMENT_NOT_SATISFIED
    assert text_adapter.generate_requests == []
