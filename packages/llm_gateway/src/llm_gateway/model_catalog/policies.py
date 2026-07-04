"""Pydantic schemas for JSONB policy columns stored on models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RoutingPolicy(BaseModel):
    """Controls how instances are selected for a given model."""

    strategy: Literal["priority", "round_robin", "random", "least_latency"] = "priority"


class RetryPolicySchema(BaseModel):
    """Validates the ``retry_policy_json`` column on llm_models.

    Mirrors the runtime ``RetryPolicy`` dataclass but serves as a validation
    gate at the CRUD layer so bad data never reaches the gateway.
    """

    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_on_server_error: bool = True
    retry_on_auth_error: bool = False
    initial_backoff_ms: int = Field(default=500, ge=0)
    max_backoff_ms: int = Field(default=10_000, ge=0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)
