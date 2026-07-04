from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeProviderConfig:
    """Internal provider execution config resolved by the gateway.

    This object is intentionally provider-agnostic. Provider-specific adapters
    can derive the transport details they need from these normalized values plus
    their own static defaults.
    """

    api_key: str | None = None
    base_url: str | None = None
    websocket_base_url: str | None = None
    api_version: str | None = None
    organization: str | None = None
    project: str | None = None
    region: str | None = None
