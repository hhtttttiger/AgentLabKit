from __future__ import annotations

from urllib.parse import urlencode

from openai import AsyncOpenAI

from ...config import ProviderConfig
from .common import require_api_key
from ...models import ProviderId


def create_openai_client(config: ProviderConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=30.0,
    )


def _strip_trailing_slash(value: str) -> str:
    return value[:-1] if value.endswith("/") else value


def _normalize_websocket_scheme(value: str) -> str:
    if value.startswith("https://"):
        return "wss://" + value.removeprefix("https://")
    if value.startswith("http://"):
        return "ws://" + value.removeprefix("http://")
    return value


def build_openai_realtime_url(config: ProviderConfig, model: str) -> str:
    base = config.websocket_base_url
    if not base:
        raw = config.base_url or "https://api.openai.com/v1"
        base = _normalize_websocket_scheme(raw)
        base = _strip_trailing_slash(base) + "/realtime"
    query = urlencode({"model": model})
    return f"{_strip_trailing_slash(base)}?{query}"


def build_openai_realtime_headers(config: ProviderConfig) -> dict[str, str]:
    require_api_key(
        ProviderId.OPENAI,
        "realtime",
        config,
        "OpenAI API key is not configured.",
    )
    return {
        "Authorization": f"Bearer {config.api_key}",
        "OpenAI-Beta": "realtime=v1",
    }
