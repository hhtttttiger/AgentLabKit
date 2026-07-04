"""Unit tests for the external tool framework (Phase 3).

Covers:
- ExternalToolConfig: dataclass construction and defaults
- HttpToolHandler: spec validation (requires "external" tag)
- HttpToolHandler.execute: success, HTTP error, credential injection
- HttpToolHandler.execute: graceful handling of import errors and network errors
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest



from agent_runtime.tools import (
    ExternalToolConfig,
    HttpToolHandler,
    ToolExecutionContext,
    ToolResult,
    ToolSpec,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context() -> ToolExecutionContext:
    return ToolExecutionContext(
        session_id="sess-1",
        trace_id="trace-1",
        agent_key="test-agent",
    )


def _external_spec(name: str = "my_external") -> ToolSpec:
    return ToolSpec(
        name=name,
        description="An external tool.",
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        tags=frozenset({"external", "read_only"}),
        timeout_seconds=15.0,
    )


class _SimpleExternalTool(HttpToolHandler):
    spec = _external_spec()

    def __init__(self, config: ExternalToolConfig | None = None) -> None:
        super().__init__(
            config=config
            or ExternalToolConfig(endpoint_url="http://localhost:9999/execute")
        )


# ---------------------------------------------------------------------------
# ExternalToolConfig
# ---------------------------------------------------------------------------


class TestExternalToolConfig:
    def test_defaults(self):
        cfg = ExternalToolConfig(endpoint_url="http://example.com/tool")
        assert cfg.endpoint_url == "http://example.com/tool"
        assert cfg.http_method == "POST"
        assert cfg.auth_header is None
        assert cfg.credential_key is None
        assert cfg.extra_headers == {}
        assert cfg.request_timeout_seconds == 25.0

    def test_full_construction(self):
        cfg = ExternalToolConfig(
            endpoint_url="http://svc/tool",
            http_method="PATCH",
            auth_header="X-Api-Key",
            credential_key="MY_SECRET",
            extra_headers={"X-Custom": "value"},
            request_timeout_seconds=10.0,
        )
        assert cfg.http_method == "PATCH"
        assert cfg.auth_header == "X-Api-Key"
        assert cfg.credential_key == "MY_SECRET"
        assert cfg.extra_headers["X-Custom"] == "value"
        assert cfg.request_timeout_seconds == 10.0

    def test_immutable(self):
        cfg = ExternalToolConfig(endpoint_url="http://x.com")
        with pytest.raises((AttributeError, TypeError)):
            cfg.endpoint_url = "http://changed.com"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# HttpToolHandler spec validation
# ---------------------------------------------------------------------------


class TestHttpToolHandlerValidation:
    def test_missing_spec_raises(self):
        class NoSpecTool(HttpToolHandler):
            pass  # no spec attribute

        with pytest.raises(TypeError, match="must define a class-level 'spec'"):
            NoSpecTool(ExternalToolConfig(endpoint_url="http://x.com"))

    def test_missing_external_tag_raises(self):
        class BadTagTool(HttpToolHandler):
            spec = ToolSpec(
                name="bad_tool",
                description="Missing external tag",
                parameters_schema={"type": "object"},
                tags=frozenset({"read_only"}),  # no "external"
            )

        with pytest.raises(ValueError, match="must include 'external'"):
            BadTagTool(ExternalToolConfig(endpoint_url="http://x.com"))

    def test_valid_tool_created_successfully(self):
        tool = _SimpleExternalTool()
        assert tool.spec.name == "my_external"
        assert "external" in tool.spec.tags


# ---------------------------------------------------------------------------
# HttpToolHandler.execute — success path
# ---------------------------------------------------------------------------


class TestHttpToolHandlerExecute:
    @pytest.mark.asyncio
    async def test_success_response(self):
        tool = _SimpleExternalTool()
        context = _make_context()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": "result text",
            "structured_data": {"key": "value"},
        }

        with _patch_httpx(mock_response):
            result = await tool.execute({"query": "hello"}, context)

        assert result.status == "success"
        assert result.output == "result text"
        assert result.structured_data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_error_message_in_response_body(self):
        tool = _SimpleExternalTool()
        context = _make_context()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": "",
            "error_message": "Something went wrong upstream",
        }

        with _patch_httpx(mock_response):
            result = await tool.execute({"query": "hello"}, context)

        assert result.status == "error"
        assert "Something went wrong upstream" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_http_4xx_returns_error(self):
        tool = _SimpleExternalTool()
        context = _make_context()

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Unprocessable Entity"

        with _patch_httpx(mock_response):
            result = await tool.execute({"query": "q"}, context)

        assert result.status == "error"
        assert "422" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_request_uses_configured_http_method(self):
        class PatchTool(HttpToolHandler):
            spec = _external_spec("patch_tool")

        tool = PatchTool(
            ExternalToolConfig(
                endpoint_url="http://svc/tool",
                http_method="PATCH",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": "patched"}

        captured_method: dict[str, str] = {}

        async def mock_request(self_client, method, url, content, headers):
            captured_method["value"] = method
            return mock_response

        with patch("httpx.AsyncClient.request", mock_request):
            result = await tool.execute({"query": "q"}, _make_context())

        assert captured_method["value"] == "PATCH"
        assert result.output == "patched"

    @pytest.mark.asyncio
    async def test_network_error_returns_error(self):
        tool = _SimpleExternalTool()
        context = _make_context()

        with patch(
            "agent_runtime.tools.external.HttpToolHandler._post",
            side_effect=ConnectionError("connection refused"),
        ):
            result = await tool.execute({"query": "q"}, context)

        assert result.status == "error"
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_exception_isolation_returns_error_not_raise(self):
        """execute() must never raise; exceptions become status='error' results."""
        tool = _SimpleExternalTool()
        context = _make_context()

        with patch.object(tool, "_post", side_effect=RuntimeError("boom")):
            result = await tool.execute({}, context)

        assert result.status == "error"
        assert "boom" in (result.error_message or "")


# ---------------------------------------------------------------------------
# Credential injection
# ---------------------------------------------------------------------------


class TestCredentialInjection:
    @pytest.mark.asyncio
    async def test_credential_injected_from_env(self, monkeypatch):
        monkeypatch.setenv("MY_TOOL_SECRET", "secret-token-123")
        config = ExternalToolConfig(
            endpoint_url="http://svc/tool",
            auth_header="X-Api-Key",
            credential_key="MY_TOOL_SECRET",
        )

        class CredTool(HttpToolHandler):
            spec = _external_spec("cred_tool")

        tool = CredTool(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": "ok"}

        posted_headers: dict = {}

        async def mock_post_request(self_client, method, url, content, headers):
            assert method == "POST"
            posted_headers.update(headers)
            return mock_response

        with patch("httpx.AsyncClient.request", mock_post_request):
            result = await tool.execute({"query": "q"}, _make_context())

        assert posted_headers.get("X-Api-Key") == "secret-token-123"
        assert result.status == "success"

    def test_missing_credential_logs_warning(self, monkeypatch, caplog):
        monkeypatch.delenv("MY_TOOL_SECRET", raising=False)
        config = ExternalToolConfig(
            endpoint_url="http://svc/tool",
            auth_header="X-Api-Key",
            credential_key="MY_TOOL_SECRET",
        )

        class CredTool(HttpToolHandler):
            spec = _external_spec("cred_tool2")

        tool = CredTool(config)
        import logging

        with caplog.at_level(logging.WARNING, logger="agent_runtime.tools.external"):
            cred = tool._resolve_credential()

        assert cred is None
        assert any("MY_TOOL_SECRET" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Integration: external tool registered in DynamicToolRegistry
# ---------------------------------------------------------------------------


class TestExternalToolRegistration:
    def test_register_external_tool(self):
        from agent_runtime.tools import DynamicToolRegistry

        tool = _SimpleExternalTool()
        reg = DynamicToolRegistry()
        reg.register(tool.spec, tool)

        spec = reg.get_spec("my_external")
        assert spec is not None
        assert "external" in spec.tags

    def test_external_tag_visible_in_list_all(self):
        from agent_runtime.tools import DynamicToolRegistry

        tool = _SimpleExternalTool()
        reg = DynamicToolRegistry()
        reg.register(tool.spec, tool)

        external_tools = [s for s in reg.list_all() if "external" in s.tags]
        assert any(s.name == "my_external" for s in external_tools)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_httpx(mock_response):
    """Patch httpx.AsyncClient.request to return mock_response."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_response)
    return patch("httpx.AsyncClient", return_value=mock_client)
