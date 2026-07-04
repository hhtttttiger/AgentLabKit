from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import EntityBase


class LlmConnectionProfile(EntityBase):
    __tablename__ = "llm_connection_profiles"

    profile_key: Mapped[str] = mapped_column(String(128), unique=True)
    display_name: Mapped[str] = mapped_column(String(256))
    provider: Mapped[str] = mapped_column(String(64))
    base_url: Mapped[str | None] = mapped_column(String(1024))
    websocket_base_url: Mapped[str | None] = mapped_column(String(1024))
    api_version: Mapped[str | None] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64))
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_enabled: Mapped[bool] = mapped_column(Boolean)


class LlmModel(EntityBase):
    __tablename__ = "llm_models"

    model_key: Mapped[str] = mapped_column(String(128), unique=True)
    type: Mapped[str] = mapped_column(String(32))
    model_name: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(1024))
    connection_profile_id: Mapped[int] = mapped_column(BigInteger, index=True)
    tags_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    routing_policy_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    retry_policy_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_enabled: Mapped[bool] = mapped_column(Boolean)
    input_price_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    output_price_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    cache_write_price_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    cache_read_price_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)


class LlmModelInstance(EntityBase):
    __tablename__ = "llm_model_instances"

    instance_key: Mapped[str] = mapped_column(String(128), unique=True)
    model_id: Mapped[int] = mapped_column(BigInteger, index=True)
    provider_deployment_name: Mapped[str | None] = mapped_column(String(128))
    region: Mapped[str | None] = mapped_column(String(64))
    priority: Mapped[int] = mapped_column(Integer)
    weight: Mapped[int] = mapped_column(Integer)
    default_timeout_ms: Mapped[int] = mapped_column(Integer)
    extra_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_enabled: Mapped[bool] = mapped_column(Boolean)
    is_healthy: Mapped[bool] = mapped_column(Boolean)
    encrypted_api_key: Mapped[str | None] = mapped_column(String(512))


class LlmFeature(EntityBase):
    __tablename__ = "llm_features"

    feature_key: Mapped[str] = mapped_column(String(128), unique=True)
    display_name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(1024))
    value_type: Mapped[str] = mapped_column(String(32))
    allowed_values_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    is_filterable: Mapped[bool] = mapped_column(Boolean)
    is_routable: Mapped[bool] = mapped_column(Boolean)
    is_enabled: Mapped[bool] = mapped_column(Boolean)


class LlmModelFeature(EntityBase):
    __tablename__ = "llm_model_features"

    model_id: Mapped[int] = mapped_column(BigInteger, index=True)
    feature_id: Mapped[int] = mapped_column(BigInteger, index=True)
    is_supported: Mapped[bool] = mapped_column(Boolean)
    value_json: Mapped[object | None] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(String(512))

    __table_args__ = (
        UniqueConstraint("model_id", "feature_id", name="uq_model_feature"),
    )


class LlmModelBinding(EntityBase):
    __tablename__ = "llm_model_bindings"

    binding_key: Mapped[str] = mapped_column(String(128), unique=True)
    display_name: Mapped[str] = mapped_column(String(256))
    capability: Mapped[str] = mapped_column(String(32))
    model_id: Mapped[int] = mapped_column(BigInteger, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_enabled: Mapped[bool] = mapped_column(Boolean)


class LlmCatalogRevision(EntityBase):
    __tablename__ = "llm_catalog_revisions"

    revision: Mapped[int] = mapped_column(BigInteger, unique=True)
