from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GuardrailsSettings(BaseModel):
    """Configuration for the guardrails pipeline.

    When ``enabled`` is *False* (the default) the entire guardrails
    pipeline is skipped — zero runtime overhead.
    """

    enabled: bool = False
    block_response: str = "I'm unable to process this request."

    input_guards: list[str] = Field(
        default_factory=lambda: ["prompt_injection", "input_length"]
    )
    output_guards: list[str] = Field(default_factory=lambda: ["pii_masking"])
    tool_guards: list[str] = Field(
        default_factory=lambda: ["parameter_validation"]
    )

    prompt_injection_threshold: float = 0.7
    max_input_chars: int = 10_000

    pii_categories: list[str] = Field(
        default_factory=lambda: ["email", "phone_cn", "id_card_cn", "credit_card"]
    )
    content_safety_categories: list[str] = Field(
        default_factory=lambda: ["violence", "self_harm"]
    )

    max_tool_param_length: int = 2000
    streaming_guard_mode: Literal["buffered", "post_complete"] = "post_complete"
