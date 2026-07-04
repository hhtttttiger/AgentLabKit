from __future__ import annotations

from typing import Any

from ...config import ProviderConfig


def create_anthropic_client(config: ProviderConfig) -> Any:
    """Create an async Anthropic client from gateway config."""
    from anthropic import AsyncAnthropic

    kwargs: dict[str, Any] = {}
    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return AsyncAnthropic(**kwargs)
