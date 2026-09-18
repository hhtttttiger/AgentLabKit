from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from desktop.core import config as desktop_config
from desktop.local.composition import create_local_app


def request_app(monkeypatch, tmp_path: Path):
    config_dir = tmp_path / "config"
    monkeypatch.setattr(desktop_config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(desktop_config, "CONFIG_FILE", config_dir / "desktop.toml")
    monkeypatch.setenv("AGENTLAB_LOCAL_TOKEN", "test-token")
    return create_local_app(tmp_path / "agentlab.db")


def test_model_settings_redacts_secret_and_preserves_key(monkeypatch, tmp_path: Path) -> None:
    app = request_app(monkeypatch, tmp_path)
    desktop_config.AppConfig(llm=desktop_config.LLMConfig(api_key="secret", model="old-model")).save()

    async def exercise() -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-AgentLab-Local-Token": "test-token"}
            response = await client.get("/api/desktop/settings/models", headers=headers)
            assert response.status_code == 200
            payload = response.json()["data"]
            assert payload["apiKeyConfigured"] is True
            assert "secret" not in response.text

            response = await client.put("/api/desktop/settings/models", headers=headers, json={
                "provider": "openai", "baseUrl": "https://api.example.test/v1", "model": "new-model"
            })
            assert response.status_code == 200
            assert desktop_config.AppConfig.load().llm.api_key == "secret"
            assert desktop_config.AppConfig.load().llm.model == "new-model"

    try:
        asyncio.run(exercise())
    finally:
        app.state.local.db.close()


def test_model_settings_environment_override_is_effective(monkeypatch, tmp_path: Path) -> None:
    app = request_app(monkeypatch, tmp_path)
    monkeypatch.setenv("AGENTLAB_LLM_MODEL", "env-model")

    async def exercise() -> None:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/desktop/settings/models", headers={"X-AgentLab-Local-Token": "test-token"})
            assert response.status_code == 200
            payload = response.json()["data"]
            assert payload["model"] == "env-model"
            assert payload["modelOverridden"] is True
            assert payload["overrideEnvironment"]["model"] == "AGENTLAB_LLM_MODEL"

    try:
        asyncio.run(exercise())
    finally:
        app.state.local.db.close()
