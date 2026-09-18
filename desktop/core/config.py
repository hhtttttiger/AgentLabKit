"""桌面端配置管理。

配置文件路径：~/.config/agentlabkit/desktop.toml
首次运行时自动创建默认配置。
"""
from __future__ import annotations

import tomllib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


CONFIG_DIR = Path.home() / ".config" / "agentlabkit"
CONFIG_FILE = CONFIG_DIR / "desktop.toml"
SUPPORTED_PROVIDERS = ("openai", "anthropic")
ENV_KEYS = {
    "provider": "AGENTLAB_LLM_PROVIDER",
    "base_url": "AGENTLAB_LLM_BASE_URL",
    "api_key": "AGENTLAB_LLM_API_KEY",
    "model": "AGENTLAB_LLM_MODEL",
}


@dataclass
class LLMConfig:
    provider: str = "openai"          # openai | anthropic
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"

    def validate(self) -> None:
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {self.provider}")
        if self.provider == "openai":
            parsed = urlparse(self.base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Base URL must be a valid http or https URL")
        if not self.model.strip():
            raise ValueError("Model is required")


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)

    # ── 序列化 ──

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Keep persistence dependency-free: the Desktop runtime only needs a
        # small, flat string table and Python's stdlib has no TOML writer.
        lines = ["[llm]"]
        for key, value in (("provider", self.llm.provider), ("base_url", self.llm.base_url), ("api_key", self.llm.api_key), ("model", self.llm.model)):
            lines.append(f"{key} = {json.dumps(value)}")
        CONFIG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def load_effective(cls) -> AppConfig:
        config = cls.load()
        config.llm = apply_environment_overrides(config.llm)
        return config

    @staticmethod
    def environment_overrides() -> dict[str, str]:
        return {field_name: env_name for field_name, env_name in ENV_KEYS.items() if os.environ.get(env_name) is not None}

    @classmethod
    def load(cls) -> AppConfig:
        if not CONFIG_FILE.exists():
            config = cls()
            config.save()  # 首次运行，写入默认配置
            return config

        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)

        llm_data = data.get("llm", {})
        return cls(
            llm=LLMConfig(
                provider=llm_data.get("provider", "openai"),
                base_url=llm_data.get("base_url", "https://api.openai.com/v1"),
                api_key=llm_data.get("api_key", ""),
                model=llm_data.get("model", "gpt-4o-mini"),
            ),
        )


def apply_environment_overrides(llm: LLMConfig) -> LLMConfig:
    values = {
        "provider": llm.provider,
        "base_url": llm.base_url,
        "api_key": llm.api_key,
        "model": llm.model,
    }
    for field_name, env_name in ENV_KEYS.items():
        value = os.environ.get(env_name)
        if value is not None:
            values[field_name] = value
    return LLMConfig(**values)
