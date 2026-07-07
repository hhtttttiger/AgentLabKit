from __future__ import annotations

from enum import Enum


class CatalogErrorCode(str, Enum):
    BINDING_NOT_FOUND = "binding_not_found"
    MODEL_NOT_FOUND = "model_not_found"
    MODEL_NAME_NOT_FOUND = "model_name_not_found"
    MODEL_REF_AMBIGUOUS = "model_ref_ambiguous"
    NO_ENABLED_INSTANCE = "no_enabled_instance"
    FEATURE_REQUIREMENT_NOT_SATISFIED = "feature_requirement_not_satisfied"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    PROVIDER_CONFLICT = "provider_conflict"
    CREDENTIAL_NOT_RESOLVED = "credential_not_resolved"
    CATALOG_UNAVAILABLE = "catalog_unavailable"


class CatalogError(Exception):
    def __init__(
        self,
        code: CatalogErrorCode,
        message: str,
        *,
        binding_key: str | None = None,
        model_key: str | None = None,
        provider: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.binding_key = binding_key
        self.model_key = model_key
        self.provider = provider
