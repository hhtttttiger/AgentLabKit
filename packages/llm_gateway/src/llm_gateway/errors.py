from __future__ import annotations

from enum import Enum


class GatewayErrorCode(str, Enum):
    PROVIDER_NOT_FOUND = "provider_not_found"
    MODEL_NOT_FOUND = "model_not_found"
    MODEL_NAME_NOT_FOUND = "model_name_not_found"
    MODEL_REF_AMBIGUOUS = "model_ref_ambiguous"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    VALIDATION_ERROR = "validation_error"
    PROVIDER_AUTH_FAILED = "provider_auth_failed"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    UPSTREAM_ERROR = "upstream_error"
    SESSION_CLOSED = "session_closed"
    BINDING_NOT_FOUND = "binding_not_found"
    NO_ENABLED_INSTANCE = "no_enabled_instance"
    FEATURE_REQUIREMENT_NOT_SATISFIED = "feature_requirement_not_satisfied"
    PROVIDER_CONFLICT = "provider_conflict"
    CREDENTIAL_NOT_RESOLVED = "credential_not_resolved"
    CATALOG_UNAVAILABLE = "catalog_unavailable"


class GatewayError(Exception):
    def __init__(
        self,
        code: GatewayErrorCode,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.provider = provider
        self.model = model
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, str]:
        data = {"code": self.code.value, "message": self.message}
        if self.provider:
            data["provider"] = self.provider
        if self.model:
            data["model"] = self.model
        return data
