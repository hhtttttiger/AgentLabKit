"""Unit tests for ToolCatalogSyncer and DbBackedExternalToolLoader (Phase 4).

These tests use in-memory mock sessions — no real DB required.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.tools.catalog_syncer import (
    DbBackedExternalToolLoader,
    ToolCatalogSyncer,
    _normalize_kubernetes_service_url,
    _parse_json,
)
from agent_runtime.tools.contracts import ToolSpec
from agent_runtime.tools.external import ExternalToolConfig
from agent_runtime.tools.registry import DynamicToolRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_spec(name: str = "knowledge_search", timeout: float = 10.0) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=f"Description of {name}",
        parameters_schema={"type": "object", "properties": {}},
        tags=frozenset({"rag"}),
        timeout_seconds=timeout,
        max_retries=0,
    )


def _make_session_factory(execute_result: Any = None):
    """Build a mock async_sessionmaker that returns a mock session."""
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = execute_result or []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=None)
    mock_begin.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=mock_begin)

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session
    return mock_factory, mock_session


# ---------------------------------------------------------------------------
# ToolCatalogSyncer.upsert_all
# ---------------------------------------------------------------------------


class TestToolCatalogSyncerUpsertAll:
    @pytest.mark.asyncio
    async def test_upsert_empty_specs_returns_zero(self):
        factory, _ = _make_session_factory()
        syncer = ToolCatalogSyncer(factory)
        result = await syncer.upsert_all([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_upsert_single_spec_executes_once(self):
        factory, session = _make_session_factory()
        syncer = ToolCatalogSyncer(factory)
        spec = _make_spec("knowledge_search")

        result = await syncer.upsert_all([spec])

        assert result == 1
        assert session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_upsert_multiple_specs_executes_for_each(self):
        factory, session = _make_session_factory()
        syncer = ToolCatalogSyncer(factory)
        specs = [_make_spec("tool_a"), _make_spec("tool_b"), _make_spec("tool_c")]

        result = await syncer.upsert_all(specs)

        assert result == 3
        assert session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_upsert_executes_with_correct_params(self):
        factory, session = _make_session_factory()
        syncer = ToolCatalogSyncer(factory)
        spec = ToolSpec(
            name="time_now",
            description="Returns current UTC time.",
            parameters_schema={"type": "object", "properties": {}},
            tags=frozenset({"utility"}),
            timeout_seconds=5.0,
            max_retries=1,
        )

        await syncer.upsert_all([spec])

        call_args = session.execute.call_args
        params = call_args[0][1]  # positional args: (sql, params)
        assert params["tool_name"] == "time_now"
        assert params["description"] == "Returns current UTC time."
        assert params["timeout_seconds"] == 5.0
        assert params["max_retries"] == 1
        assert json.loads(params["tags_json"]) == ["utility"]

    @pytest.mark.asyncio
    async def test_upsert_failure_does_not_raise(self):
        """DB failures must not crash service startup."""
        factory, session = _make_session_factory()
        session.execute.side_effect = Exception("connection refused")
        syncer = ToolCatalogSyncer(factory)

        # Must complete without raising
        result = await syncer.upsert_all([_make_spec()])
        assert result == 1  # still returns the count it *attempted*


# ---------------------------------------------------------------------------
# ToolCatalogSyncer.load_external_tools
# ---------------------------------------------------------------------------


def _make_external_row(
    tool_name: str = "crm_lookup",
    endpoint: str = "https://crm.example.com/lookup",
    credential_key: str | None = "CRM_KEY",
) -> dict:
    return {
        "ToolName": tool_name,
        "DisplayName": "CRM Lookup",
        "Description": "Looks up CRM data.",
        "ParametersSchemaJson": '{"type":"object"}',
        "TagsJson": '["crm","read_only"]',
        "EndpointUrl": endpoint,
        "HttpMethod": "POST",
        "CredentialKey": credential_key,
        "TimeoutSeconds": 15.0,
        "MaxRetries": 0,
    }


class TestToolCatalogSyncerLoadExternalTools:
    @pytest.mark.asyncio
    async def test_load_returns_rows_from_db(self):
        factory, _ = _make_session_factory(execute_result=[_make_external_row()])
        syncer = ToolCatalogSyncer(factory)

        rows = await syncer.load_external_tools()

        assert len(rows) == 1
        assert rows[0].tool_name == "crm_lookup"
        assert rows[0].endpoint_url == "https://crm.example.com/lookup"
        assert rows[0].credential_key == "CRM_KEY"

    @pytest.mark.asyncio
    async def test_load_parses_tags_json(self):
        factory, _ = _make_session_factory(execute_result=[_make_external_row()])
        syncer = ToolCatalogSyncer(factory)

        rows = await syncer.load_external_tools()
        assert "crm" in rows[0].tags
        assert "read_only" in rows[0].tags

    @pytest.mark.asyncio
    async def test_load_skips_row_with_missing_endpoint(self):
        row = _make_external_row()
        row["EndpointUrl"] = None
        factory, _ = _make_session_factory(execute_result=[row])
        syncer = ToolCatalogSyncer(factory)

        rows = await syncer.load_external_tools()
        assert len(rows) == 0  # filtered out

    @pytest.mark.asyncio
    async def test_load_db_failure_returns_empty_list(self):
        factory, session = _make_session_factory()
        session.execute.side_effect = Exception("timeout")
        syncer = ToolCatalogSyncer(factory)

        rows = await syncer.load_external_tools()
        assert rows == []


# ---------------------------------------------------------------------------
# DbBackedExternalToolLoader
# ---------------------------------------------------------------------------


class TestDbBackedExternalToolLoader:
    @pytest.mark.asyncio
    async def test_load_and_register_adds_tools_to_registry(self):
        factory, _ = _make_session_factory(
            execute_result=[_make_external_row("crm_lookup")]
        )
        syncer = ToolCatalogSyncer(factory)
        loader = DbBackedExternalToolLoader(syncer)
        registry = DynamicToolRegistry()

        count = await loader.load_and_register(registry)

        assert count == 1
        spec = registry.get_spec("crm_lookup")
        assert spec is not None
        assert spec.name == "crm_lookup"
        assert "external" in spec.tags

        handler = registry.get_handler("crm_lookup")
        assert getattr(handler, "_config").http_method == "POST"

    @pytest.mark.asyncio
    async def test_load_and_register_multiple_tools(self):
        factory, _ = _make_session_factory(
            execute_result=[
                _make_external_row("tool_a", "https://a.com"),
                _make_external_row("tool_b", "https://b.com"),
            ]
        )
        syncer = ToolCatalogSyncer(factory)
        loader = DbBackedExternalToolLoader(syncer)
        registry = DynamicToolRegistry()

        count = await loader.load_and_register(registry)
        assert count == 2
        assert registry.get_spec("tool_a") is not None
        assert registry.get_spec("tool_b") is not None

    @pytest.mark.asyncio
    async def test_load_and_register_replaces_existing_tool(self):
        """Re-loading a tool (e.g. after config change) should replace it."""
        old_spec = ToolSpec(
            name="crm_lookup",
            description="Old description",
            parameters_schema={},
            tags=frozenset({"external"}),
        )
        old_handler = MagicMock()
        registry = DynamicToolRegistry()
        registry.register(old_spec, old_handler)

        factory, _ = _make_session_factory(
            execute_result=[_make_external_row("crm_lookup")]
        )
        syncer = ToolCatalogSyncer(factory)
        loader = DbBackedExternalToolLoader(syncer)

        await loader.load_and_register(registry)

        updated_spec = registry.get_spec("crm_lookup")
        assert updated_spec.description == "Looks up CRM data."

    @pytest.mark.asyncio
    async def test_load_and_register_no_tools_returns_zero(self):
        factory, _ = _make_session_factory(execute_result=[])
        syncer = ToolCatalogSyncer(factory)
        loader = DbBackedExternalToolLoader(syncer)
        registry = DynamicToolRegistry()

        count = await loader.load_and_register(registry)
        assert count == 0


# ---------------------------------------------------------------------------
# _parse_json helper
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_parses_valid_json(self):
        assert _parse_json('{"key": "value"}', {}) == {"key": "value"}

    def test_returns_default_on_invalid_json(self):
        assert _parse_json("{invalid}", {}) == {}

    def test_returns_default_on_none(self):
        assert _parse_json(None, []) == []

    def test_parses_list(self):
        assert _parse_json('["a", "b"]', []) == ["a", "b"]


class TestNormalizeKubernetesServiceUrl:
    def test_expands_short_service_name_with_namespace(self, monkeypatch):
        monkeypatch.setenv("POD_NAMESPACE", "voices-demo")

        normalized = _normalize_kubernetes_service_url("http://aihost-api/api/external/weather-query")

        assert normalized == "http://aihost-api.voices-demo.svc.cluster.local/api/external/weather-query"

    def test_leaves_fqdn_unchanged(self, monkeypatch):
        monkeypatch.setenv("POD_NAMESPACE", "voices-demo")

        normalized = _normalize_kubernetes_service_url(
            "http://aihost-api.voices-demo.svc.cluster.local/api/external/weather-query"
        )

        assert normalized == "http://aihost-api.voices-demo.svc.cluster.local/api/external/weather-query"

    def test_leaves_external_host_unchanged(self, monkeypatch):
        monkeypatch.setenv("POD_NAMESPACE", "voices-demo")

        normalized = _normalize_kubernetes_service_url("https://api.open-meteo.com/v1/forecast")

        assert normalized == "https://api.open-meteo.com/v1/forecast"
