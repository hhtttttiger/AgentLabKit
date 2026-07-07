from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from sqlalchemy import select

from llm_gateway.model_catalog import SqlAlchemyModelCatalogRepository
from llm_gateway.models import Capability, ProviderId
from llm_gateway.model_catalog.errors import CatalogError, CatalogErrorCode
from llm_gateway.model_catalog.session import create_catalog_engine
from llm_gateway.model_catalog.orm_models import (
    LlmCatalogRevisionOrm,
    LlmConnectionProfileOrm,
    LlmFeatureDefinitionOrm,
    LlmModelBindingOrm,
    LlmModelFeatureOrm,
    LlmModelOrm,
    LlmModelInstanceOrm,
)


class _FakeScalarResult:
    def __init__(self, rows: Sequence[Any]) -> None:
        self._rows = list(rows)

    def __iter__(self):
        return iter(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeExecuteResult:
    def __init__(self, rows: Sequence[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._rows)


class _FakeSession:
    def __init__(self, results_by_entity: dict[type[Any], Sequence[Any]], *, failure: Exception | None = None) -> None:
        self._results_by_entity = results_by_entity
        self._failure = failure

    async def execute(self, statement):
        if self._failure is not None:
            raise self._failure
        entity = statement.column_descriptions[0]["entity"]
        return _FakeExecuteResult(self._results_by_entity.get(entity, ()))


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self) -> _FakeSessionContext:
        return _FakeSessionContext(self._session)


class TestSqlAlchemyModelCatalogRepository:
    def test_create_catalog_engine_enables_pre_ping(self):
        engine = create_catalog_engine("postgresql+asyncpg://user:password@localhost/testdb")

        assert engine.sync_engine.pool._pre_ping is True

    @pytest.mark.asyncio
    async def test_load_snapshot_maps_llm_catalog_rows_into_domain_snapshot(self):
        repository = SqlAlchemyModelCatalogRepository(
            _FakeSessionFactory(
                _FakeSession(
                    {
                        LlmConnectionProfileOrm: [
                            LlmConnectionProfileOrm(
                                id=101,
                                profile_key="openai.primary",
                                display_name="OpenAI Primary",
                                provider="openai",
                                base_url="https://api.openai.test/v1",
                                websocket_base_url=None,
                                api_version=None,
                                region="us-east",
                                extra_json={"tier": "gold"},
                                is_enabled=True,
                            )
                        ],
                        LlmModelOrm: [
                            LlmModelOrm(
                                id=201,
                                model_key="gateway.default.text",
                                type="text",
                                model_name="gpt-4.1-mini",
                                display_name="Gateway Default Text",
                                description="text card",
                                connection_profile_id=101,
                                tags_json=["text", "default"],
                                routing_policy_json={"strategy": "priority"},
                                retry_policy_json={"max_attempts": 2},
                                is_enabled=True,
                            )
                        ],
                        LlmModelBindingOrm: [
                            LlmModelBindingOrm(
                                id=301,
                                binding_key="gateway.default_text",
                                display_name="Gateway Default Text",
                                capability="text",
                                model_id=201,
                                metadata_json={"channel": "web"},
                                is_enabled=True,
                            )
                        ],
                        LlmModelInstanceOrm: [
                            LlmModelInstanceOrm(
                                id=401,
                                instance_key="text-primary",
                                model_id=201,
                                provider_deployment_name=None,
                                region="us-east-1",
                                priority=10,
                                weight=80,
                                default_timeout_ms=45000,
                                extra_json={"temperature": "0.2"},
                                is_enabled=True,
                                is_healthy=True,
                                encrypted_api_key="cipher-text",
                            )
                        ],
                        LlmFeatureDefinitionOrm: [
                            LlmFeatureDefinitionOrm(
                                id=501,
                                feature_key="function_call",
                                display_name="Function Call",
                                description="structured tool use",
                                value_type="boolean",
                                allowed_values_json=[],
                                is_filterable=True,
                                is_routable=True,
                                is_enabled=True,
                            )
                        ],
                        LlmModelFeatureOrm: [
                            LlmModelFeatureOrm(
                                id=601,
                                model_id=201,
                                feature_id=501,
                                is_supported=True,
                                value_json=True,
                                source="manual",
                                remark="enabled",
                            )
                        ],
                        LlmCatalogRevisionOrm: [
                            LlmCatalogRevisionOrm(id=701, revision=7)
                        ],
                    }
                )
            )
        )

        snapshot = await repository.load_snapshot()

        assert snapshot.revision == 7
        definition = snapshot.feature_definitions_by_key["function_call"]
        assert definition.value_type == "boolean"
        assert definition.is_routable is True
        profile = snapshot.connection_profiles_by_key["openai.primary"]
        assert profile.provider == ProviderId.OPENAI
        assert profile.extra["tier"] == "gold"

        card = snapshot.cards_by_key["gateway.default.text"]
        assert card.display_name == "Gateway Default Text"
        assert card.capabilities == (Capability.TEXT,)
        assert card.retry_policy["max_attempts"] == 2
        instance = card.instances[0]
        assert instance.instance_key == "text-primary"
        assert instance.connection_profile_key == "openai.primary"
        assert instance.capability == Capability.TEXT
        assert instance.provider_model_name == "gpt-4.1-mini"
        assert instance.default_timeout_ms == 45000
        assert instance.extra["temperature"] == "0.2"
        assert card.features[0].feature_key == "function_call"
        assert card.features[0].value is True
        assert card.features[0].remark == "enabled"

        binding = snapshot.bindings_by_key["gateway.default_text"]
        assert binding.card_key == "gateway.default.text"
        assert binding.metadata["channel"] == "web"

    @pytest.mark.asyncio
    async def test_load_snapshot_wraps_repository_failures_as_catalog_unavailable(self):
        repository = SqlAlchemyModelCatalogRepository(
            _FakeSessionFactory(_FakeSession({}, failure=RuntimeError("db offline")))
        )

        with pytest.raises(CatalogError) as context:
            await repository.load_snapshot()

        assert context.value.code == CatalogErrorCode.CATALOG_UNAVAILABLE
        assert "could not be loaded" in context.value.message

    @pytest.mark.asyncio
    async def test_load_snapshot_wraps_broken_foreign_keys_as_catalog_unavailable(self):
        repository = SqlAlchemyModelCatalogRepository(
            _FakeSessionFactory(
                _FakeSession(
                    {
                        LlmConnectionProfileOrm: [],
                        LlmModelOrm: [
                            LlmModelOrm(
                                id=202,
                                model_key="gateway.default.text",
                                type="text",
                                model_name="gpt-4.1-mini",
                                display_name="Gateway Default Text",
                                description=None,
                                connection_profile_id=999,
                                tags_json=[],
                                routing_policy_json={},
                                retry_policy_json={},
                                is_enabled=True,
                            )
                        ],
                        LlmModelBindingOrm: [],
                        LlmModelInstanceOrm: [
                            LlmModelInstanceOrm(
                                id=402,
                                instance_key="text-primary",
                                model_id=202,
                                provider_deployment_name=None,
                                region=None,
                                priority=1,
                                weight=100,
                                default_timeout_ms=30000,
                                extra_json={},
                                is_enabled=True,
                                is_healthy=True,
                            )
                        ],
                        LlmCatalogRevisionOrm: [],
                    }
                )
            )
        )

        with pytest.raises(CatalogError) as context:
            await repository.load_snapshot()

        assert context.value.code == CatalogErrorCode.CATALOG_UNAVAILABLE
        assert "missing connection profile" in context.value.message

    @pytest.mark.asyncio
    async def test_load_snapshot_wraps_missing_feature_definition_as_catalog_unavailable(self):
        repository = SqlAlchemyModelCatalogRepository(
            _FakeSessionFactory(
                _FakeSession(
                    {
                        LlmConnectionProfileOrm: [
                            LlmConnectionProfileOrm(
                                id=103,
                                profile_key="openai.primary",
                                display_name="OpenAI Primary",
                                provider="openai",
                                base_url=None,
                                websocket_base_url=None,
                                api_version=None,
                                region=None,
                                extra_json={},
                                is_enabled=True,
                            )
                        ],
                        LlmModelOrm: [
                            LlmModelOrm(
                                id=203,
                                model_key="gateway.default.text",
                                type="text",
                                model_name="gpt-4.1-mini",
                                display_name="Gateway Default Text",
                                description=None,
                                connection_profile_id=103,
                                tags_json=[],
                                routing_policy_json={},
                                retry_policy_json={},
                                is_enabled=True,
                            )
                        ],
                        LlmModelBindingOrm: [],
                        LlmModelInstanceOrm: [
                            LlmModelInstanceOrm(
                                id=403,
                                instance_key="text-primary",
                                model_id=203,
                                provider_deployment_name=None,
                                region=None,
                                priority=1,
                                weight=100,
                                default_timeout_ms=30000,
                                extra_json={},
                                is_enabled=True,
                                is_healthy=True,
                            )
                        ],
                        LlmFeatureDefinitionOrm: [],
                        LlmModelFeatureOrm: [
                            LlmModelFeatureOrm(
                                id=602,
                                model_id=203,
                                feature_id=998,
                                is_supported=True,
                                value_json=True,
                                source="manual",
                                remark=None,
                            )
                        ],
                        LlmCatalogRevisionOrm: [],
                    }
                )
            )
        )

        with pytest.raises(CatalogError) as context:
            await repository.load_snapshot()

        assert context.value.code == CatalogErrorCode.CATALOG_UNAVAILABLE
        assert "missing feature definition" in context.value.message
