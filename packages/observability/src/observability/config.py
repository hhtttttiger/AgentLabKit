from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OBSERVABILITY_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    enabled: bool = True
    capture_mode: Literal["off", "redacted_preview"] = "redacted_preview"
    normal_sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    slow_trace_threshold_ms: int = Field(default=2_000, ge=0)
    max_spans_per_trace: int = Field(default=500, ge=1, le=10_000)
    max_attribute_bytes: int = Field(default=4_096, ge=256)
    max_envelope_bytes: int = Field(default=524_288, ge=16_384)
    publisher_queue_capacity: int = Field(default=1_000, ge=1)
    publish_batch_size: int = Field(default=50, ge=1, le=1_000)
    publish_interval_ms: int = Field(default=100, ge=10)
    publish_max_retries: int = Field(default=3, ge=0, le=10)
    flush_timeout_seconds: float = Field(default=5.0, ge=0.1)
    # Bounded wait for the worker-side ingestion ACK (Postgres commit done),
    # consumed through the observability finalization seam — publish/flush
    # only proves the envelope reached Redis, not that the trace is readable.
    finalization_timeout_seconds: float = Field(default=10.0, ge=0.1)
    # Level-observable ACK lifetime. Must comfortably exceed the longest
    # finalization wait plus worker redelivery back-off; expiry only loses
    # the "already persisted" hint for late waiters, never fabricates one.
    finalization_ack_ttl_seconds: int = Field(default=900, ge=1)
    retention_days: int = Field(default=30, ge=1)
    retention_batch_size: int = Field(default=1_000, ge=1, le=100_000)
