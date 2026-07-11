"""Internal AI gateway package."""

from dataclasses import dataclass

from .bootstrap import build_gateway_service, create_gateway_service
from .config import GatewaySettings
from .core.service import GatewayService
from .errors import GatewayError, GatewayErrorCode
from .models import (
    Capability,
    ModelRef,
    ProviderId,
    TextGenerateRequest,
    TextGenerateResponse,
    TextStreamEvent,
    UsageInfo,
)
from .protocol import GatewayProtocol


@dataclass
class GatewayModule:
    """Container for gateway settings and service, used by agent_runtime."""

    settings: GatewaySettings
    service: GatewayService


def load_gateway_module() -> GatewayModule:
    """Create a GatewayModule with default settings."""
    settings = GatewaySettings()
    service = create_gateway_service(settings)
    return GatewayModule(settings=settings, service=service)


__all__ = [
    "Capability",
    "GatewayError",
    "GatewayErrorCode",
    "GatewayModule",
    "GatewayProtocol",
    "GatewayService",
    "GatewaySettings",
    "ModelRef",
    "ProviderId",
    "TextGenerateRequest",
    "TextGenerateResponse",
    "TextStreamEvent",
    "UsageInfo",
    "build_gateway_service",
    "create_gateway_service",
    "load_gateway_module",
]
