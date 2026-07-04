from __future__ import annotations

import os

from llm_gateway.config import GatewaySettings, default_model_definitions
from llm_gateway.models import ProviderId


class TestGatewaySettings:
    def test_defaults_include_builtin_bootstrap_models_and_use_database_first_catalog(self):
        settings = GatewaySettings()
        assert settings.catalog.backend == "database"
        assert settings.catalog.secret_resolution_mode == "instance_only"
        assert [model.model_key for model in settings.models] == [
            model.model_key for model in default_model_definitions()
        ]
        openai_model = next(model for model in settings.models if model.model_key == "gpt-4.1-mini")
        assert openai_model.provider == ProviderId.OPENAI
        assert openai_model.provider_model_name == "gpt-4.1-mini"

    def test_supports_catalog_database_url_from_ai_gateway_env(self):
        previous = {
            key: os.environ.get(key)
            for key in (
                "AI_GATEWAY_CATALOG__BACKEND",
                "AI_GATEWAY_CATALOG__DATABASE_URL",
                "AI_GATEWAY_CATALOG__ENABLE_STATIC_FALLBACK",
            )
        }
        os.environ["AI_GATEWAY_CATALOG__BACKEND"] = "database"
        os.environ["AI_GATEWAY_CATALOG__DATABASE_URL"] = "postgresql+asyncpg://gateway-catalog"
        os.environ["AI_GATEWAY_CATALOG__ENABLE_STATIC_FALLBACK"] = "false"
        try:
            settings = GatewaySettings()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        assert settings.catalog.backend == "database"
        assert settings.catalog.database_url == "postgresql+asyncpg://gateway-catalog"
        assert settings.catalog.enable_static_fallback is False
