"""Application configuration — nested by domain for maintainability.

Environment variables support **both** the old flat names and new nested names:

    # Old (still works):
    APP_DB_HOST=localhost APP_JWT_SECRET_KEY=...

    # New (preferred):
    APP_DB__HOST=localhost APP_AUTH__SECRET_KEY=...
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Load .env into process environment (once, at import time) ─────
# All Settings classes below read from os.environ via their env_prefix;
# no model carries its own env_file path.

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


# ── Nested sub-models ──────────────────────────────────────────────


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_DB_", env_nested_delimiter="__", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "app"
    password: str = ""
    name: str = "agentlabkit"

    @computed_field
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_JWT_", env_nested_delimiter="__", extra="ignore")

    secret_key: str = ""
    issuer: str = "agentlabkit"
    audience: str = "agentlabkit"
    expires_minutes: int = 480
    algorithm: str = "HS256"


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    file_storage_local_base_path: str = "./uploads"


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_GATEWAY_", env_nested_delimiter="__", extra="ignore")

    catalog_database_url: str = ""
    catalog_encrypt_key: str = ""


class RetrievalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_RETRIEVAL_", env_nested_delimiter="__", extra="ignore")

    enabled: bool = False
    database_url: str = ""
    top_k: int = 5
    embedding_model: str = "embedding-3"
    embedding_dimensions: int = 1024

    # Hybrid search
    rrf_k: int = 60  # RRF constant (higher = less weight on rank)
    trgm_similarity_threshold: float = 0.1  # pg_trgm minimum similarity score

    # HNSW tuning (set at index creation time; runtime ef_search via SET)
    hnsw_m: int = 16
    hnsw_ef_construction: int = 64


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_REDIS_", env_nested_delimiter="__", extra="ignore")

    url: str = "redis://localhost:6379/0"
    enabled: bool = False


# ── Composite root settings ────────────────────────────────────────


class Settings(BaseSettings):
    """Root settings — delegates to nested sub-models.

    Sub-models read their own prefixed env vars (``APP_DB_HOST``,
    ``APP_JWT_SECRET_KEY``, etc.).  The root class also exposes flat
    property aliases for backward compatibility with code that accessed
    ``settings.db_host`` directly.
    """
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Service-level (remain flat on root)
    service_name: str = "agentlabkit"
    service_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Nested sub-models (read their own env vars)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    gateway: GatewaySettings = Field(default_factory=GatewaySettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)

    # ── Flat backward-compatible properties ────────────────────────
    # These let existing code like ``settings.db_host`` keep working.

    @property
    def db_host(self) -> str:
        return self.db.host

    @property
    def db_port(self) -> int:
        return self.db.port

    @property
    def db_user(self) -> str:
        return self.db.user

    @property
    def db_password(self) -> str:
        return self.db.password

    @property
    def db_name(self) -> str:
        return self.db.name

    @property
    def database_url(self) -> str:
        return self.db.url

    @property
    def jwt_secret_key(self) -> str:
        return self.auth.secret_key

    @property
    def jwt_issuer(self) -> str:
        return self.auth.issuer

    @property
    def jwt_audience(self) -> str:
        return self.auth.audience

    @property
    def jwt_expires_minutes(self) -> int:
        return self.auth.expires_minutes

    @property
    def jwt_algorithm(self) -> str:
        return self.auth.algorithm

    @property
    def file_storage_local_base_path(self) -> str:
        return self.storage.file_storage_local_base_path

    @property
    def gateway_catalog_database_url(self) -> str:
        return self.gateway.catalog_database_url

    @property
    def gateway_catalog_encrypt_key(self) -> str:
        return self.gateway.catalog_encrypt_key

    @property
    def retrieval_enabled(self) -> bool:
        return self.retrieval.enabled

    @property
    def retrieval_database_url(self) -> str:
        return self.retrieval.database_url

    @property
    def retrieval_top_k(self) -> int:
        return self.retrieval.top_k

    @property
    def embedding_model(self) -> str:
        return self.retrieval.embedding_model

    @property
    def embedding_dimensions(self) -> int:
        return self.retrieval.embedding_dimensions

    @property
    def redis_url(self) -> str:
        return self.redis.url

    @property
    def redis_enabled(self) -> bool:
        return self.redis.enabled
