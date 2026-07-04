from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from llm_gateway.bootstrap import create_gateway_service
from llm_gateway.config import GatewaySettings, ProviderConfig
from llm_gateway.errors import GatewayError, GatewayErrorCode
from llm_gateway.models import ProviderId, TextGenerateRequest


class _FakeTextResult:
    def __init__(self, output: str) -> None:
        self.output = output
        self._usage = SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2)

    def usage(self):
        return self._usage


class _FakeAgent:
    async def run(self, prompt: str) -> _FakeTextResult:
        return _FakeTextResult(f"text:{prompt}")


@pytest.mark.asyncio
class TestGatewayBootstrap:
    async def test_create_gateway_service_does_not_require_provider_secrets_at_startup(self):
        service = create_gateway_service(
            GatewaySettings(catalog={"enable_static_fallback": True})
        )
        assert service is not None

    async def test_database_backend_without_url_and_without_static_fallback_fails_fast(self):
        # enable_static_fallback defaults to False, so bare GatewaySettings() should fail
        with pytest.raises(ValueError, match="static fallback is disabled"):
            create_gateway_service(GatewaySettings())

    async def test_database_backend_uses_builtin_bootstrap_catalog_when_database_url_is_absent(self):
        service = create_gateway_service(
            GatewaySettings(catalog={"enable_static_fallback": True})
        )

        assert service is not None
        model_summary = await service.models()
        assert any(model.model_key == "gpt-4.1-mini" for model in model_summary.models)

    async def test_openai_missing_api_key_fails_on_call_instead_of_startup(self):
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "",
            },
            clear=False,
        ):
            service = create_gateway_service(
                GatewaySettings(
                    openai=ProviderConfig(api_key=None),
                    catalog={"enable_static_fallback": True},
                )
            )

            with pytest.raises(GatewayError) as context:
                await service.generate_text(
                    TextGenerateRequest(
                        model="gpt-4.1-mini",
                        prompt="hello",
                    )
                )

        assert context.value.code == GatewayErrorCode.CREDENTIAL_NOT_RESOLVED
        assert context.value.provider == ProviderId.OPENAI

    async def test_non_instance_secret_resolution_mode_is_rejected(self):
        with pytest.raises(ValueError, match="secret_resolution_mode"):
            GatewaySettings(
                catalog={
                    "enable_static_fallback": True,
                    "secret_resolution_mode": "invalid_mode",
                },
            )

