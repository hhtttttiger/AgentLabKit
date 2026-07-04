from __future__ import annotations

from decimal import Decimal

from pydantic import ConfigDict, field_validator, model_validator

from common.schemas import CamelModel


class _ResponseBase(CamelModel):
    """Response base — supports validation from ORM objects."""
    model_config = ConfigDict(from_attributes=True)


# ── Response schemas ───────────────────────────────────────────
# These schemas filter out sensitive fields (e.g. encrypted_api_key)
# and provide a stable API contract for the frontend.

class ConnectionProfileResponse(_ResponseBase):
    profile_key: str
    display_name: str
    provider: str
    base_url: str | None = None
    websocket_base_url: str | None = None
    api_version: str | None = None
    region: str | None = None
    extra_json: dict = {}
    is_enabled: bool = True


class ModelResponse(_ResponseBase):
    model_key: str
    type: str
    model_name: str
    display_name: str
    description: str | None = None
    connection_profile_id: int
    connection_profile_key: str = ""
    tags_json: list = []
    routing_policy_json: dict = {}
    retry_policy_json: dict = {}
    is_enabled: bool = True
    input_price_per_mtok: Decimal | None = None
    output_price_per_mtok: Decimal | None = None
    cache_write_price_per_mtok: Decimal | None = None
    cache_read_price_per_mtok: Decimal | None = None


class ModelInstanceResponse(_ResponseBase):
    instance_key: str
    model_id: int
    model_key: str = ""
    provider_deployment_name: str | None = None
    region: str | None = None
    priority: int = 0
    weight: int = 100
    default_timeout_ms: int = 30000
    extra_json: dict = {}
    is_enabled: bool = True
    is_healthy: bool = True
    has_api_key: bool = False


class FeatureResponse(_ResponseBase):
    feature_key: str
    display_name: str
    description: str | None = None
    value_type: str = "boolean"
    allowed_values_json: list = []
    is_filterable: bool = False
    is_routable: bool = False
    is_enabled: bool = True


class ModelBindingResponse(_ResponseBase):
    binding_key: str
    display_name: str
    capability: str
    model_id: int
    metadata_json: dict = {}
    is_enabled: bool = True


# ── Create / Update schemas ───────────────────────────────────

# --- Connection Profiles ---

class ConnectionProfileCreate(CamelModel):
    profile_key: str
    display_name: str
    provider: str
    base_url: str | None = None
    websocket_base_url: str | None = None
    api_version: str | None = None
    region: str | None = None
    extra_json: dict = {}
    is_enabled: bool = True


class ConnectionProfileUpdate(CamelModel):
    display_name: str | None = None
    provider: str | None = None
    base_url: str | None = None
    websocket_base_url: str | None = None
    api_version: str | None = None
    region: str | None = None
    extra_json: dict | None = None
    is_enabled: bool | None = None


# --- Models ---

def _validate_retry_policy_json(value: dict) -> dict:
    """Validate retry_policy_json structure against the schema."""
    from llm_gateway.model_catalog.policies import RetryPolicySchema
    RetryPolicySchema.model_validate(value)
    return value


def _validate_routing_policy_json(value: dict) -> dict:
    """Validate routing_policy_json structure against the schema."""
    from llm_gateway.model_catalog.policies import RoutingPolicy
    RoutingPolicy.model_validate(value)
    return value


class ModelCreate(CamelModel):
    model_key: str
    type: str
    model_name: str
    display_name: str
    description: str | None = None
    connection_profile_key: str
    tags_json: list = []
    routing_policy_json: dict = {}
    retry_policy_json: dict = {}
    is_enabled: bool = True
    input_price_per_mtok: Decimal | None = None
    output_price_per_mtok: Decimal | None = None
    cache_write_price_per_mtok: Decimal | None = None
    cache_read_price_per_mtok: Decimal | None = None

    @field_validator("retry_policy_json")
    @classmethod
    def validate_retry_policy(cls, v: dict) -> dict:
        return _validate_retry_policy_json(v)

    @field_validator("routing_policy_json")
    @classmethod
    def validate_routing_policy(cls, v: dict) -> dict:
        return _validate_routing_policy_json(v)


class ModelUpdate(CamelModel):
    type: str | None = None
    model_name: str | None = None
    display_name: str | None = None
    description: str | None = None
    connection_profile_key: str | None = None
    tags_json: list | None = None
    routing_policy_json: dict | None = None
    retry_policy_json: dict | None = None
    is_enabled: bool | None = None
    input_price_per_mtok: Decimal | None = None
    output_price_per_mtok: Decimal | None = None
    cache_write_price_per_mtok: Decimal | None = None
    cache_read_price_per_mtok: Decimal | None = None

    @field_validator("retry_policy_json")
    @classmethod
    def validate_retry_policy(cls, v: dict | None) -> dict | None:
        if v is not None:
            _validate_retry_policy_json(v)
        return v

    @field_validator("routing_policy_json")
    @classmethod
    def validate_routing_policy(cls, v: dict | None) -> dict | None:
        if v is not None:
            _validate_routing_policy_json(v)
        return v


# --- Model Instances ---

class ModelInstanceCreate(CamelModel):
    instance_key: str
    model_id: int
    provider_deployment_name: str | None = None
    region: str | None = None
    priority: int = 0
    weight: int = 100
    default_timeout_ms: int = 30000
    extra_json: dict = {}
    is_enabled: bool = True
    encrypted_api_key: str | None = None


class ModelInstanceCreateByModel(CamelModel):
    """Create instance via nested route — model_id is resolved from URL, not body."""
    instance_key: str
    provider_deployment_name: str | None = None
    region: str | None = None
    priority: int = 0
    weight: int = 100
    default_timeout_ms: int = 30000
    extra_json: dict = {}
    is_enabled: bool = True
    is_healthy: bool = True
    api_key: str | None = None


class ModelInstanceUpdate(CamelModel):
    provider_deployment_name: str | None = None
    region: str | None = None
    priority: int | None = None
    weight: int | None = None
    default_timeout_ms: int | None = None
    extra_json: dict | None = None
    is_enabled: bool | None = None
    api_key: str | None = None


# --- Features ---

class FeatureCreate(CamelModel):
    feature_key: str
    display_name: str
    description: str | None = None
    value_type: str = "boolean"
    allowed_values_json: list = []
    is_filterable: bool = False
    is_routable: bool = False
    is_enabled: bool = True


class FeatureUpdate(CamelModel):
    display_name: str | None = None
    description: str | None = None
    value_type: str | None = None
    allowed_values_json: list | None = None
    is_filterable: bool | None = None
    is_routable: bool | None = None
    is_enabled: bool | None = None


# --- Model Bindings ---

class ModelBindingCreate(CamelModel):
    binding_key: str
    display_name: str
    capability: str
    model_id: int | None = None
    model_key: str | None = None
    metadata_json: dict = {}
    is_enabled: bool = True

    @model_validator(mode="after")
    def _require_model_ref(self):
        if self.model_id is None and self.model_key is None:
            raise ValueError("Either model_id or model_key must be provided")
        return self


class ModelBindingCreateByModel(CamelModel):
    """Create binding via nested route — model_id is resolved from URL, not body."""
    binding_key: str
    display_name: str
    capability: str
    metadata_json: dict = {}
    is_enabled: bool = True


class ModelBindingUpdate(CamelModel):
    display_name: str | None = None
    capability: str | None = None
    model_id: int | None = None
    metadata_json: dict | None = None
    is_enabled: bool | None = None


# --- Model Features (junction) ---

class ModelFeatureResponse(_ResponseBase):
    model_key: str
    feature_key: str
    display_name: str = ""
    value_type: str = "boolean"
    allowed_values_json: list = []
    is_supported: bool = False
    value_json: object | None = None
    source: str = ""
    remark: str | None = None


class ModelFeatureUpsert(CamelModel):
    """Upsert model-feature — model_key and feature_key come from URL."""
    is_supported: bool = True
    value_json: object | None = None
    source: str = "manual"
    remark: str | None = None
