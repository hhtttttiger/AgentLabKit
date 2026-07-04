"""Internal AI gateway package."""

from .bootstrap import build_gateway_service, create_gateway_service
from .config import GatewaySettings
from .core.service import GatewayService
from .errors import GatewayError, GatewayErrorCode
from .models import (
    Capability,
    ProviderId,
    TextGenerateRequest,
    TextGenerateResponse,
    TextStreamEvent,
    UsageInfo,
)

__all__ = [
    "Capability",
    "GatewayError",
    "GatewayErrorCode",
    "GatewayService",
    "GatewaySettings",
    "ProviderId",
    "TextGenerateRequest",
    "TextGenerateResponse",
    "TextStreamEvent",
    "UsageInfo",
    "build_gateway_service",
    "create_gateway_service",
]
