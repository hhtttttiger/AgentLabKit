"""桌面端配置管理。

配置文件路径：~/.config/agentlabkit/desktop.toml
首次运行时自动创建默认配置。
"""
from __future__ import annotations

import tomllib
import tomli_w
from dataclasses import dataclass, field
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "agentlabkit"
CONFIG_FILE = CONFIG_DIR / "desktop.toml"


@dataclass
class LLMConfig:
    provider: str = "openai"          # openai | anthropic
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)

    # ── 序列化 ──

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "llm": {
                "provider": self.llm.provider,
                "base_url": self.llm.base_url,
                "api_key": self.llm.api_key,
                "model": self.llm.model,
            },
        }
        CONFIG_FILE.write_text(tomli_w.dumps(data), encoding="utf-8")

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
