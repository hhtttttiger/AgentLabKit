"""Guardrails: composable input/output/tool safety pipeline for AgentRuntime."""

from .contracts import (
    Guard,
    GuardAuditCallback,
    GuardContext,
    GuardPipelineResult,
    GuardResult,
    GuardVerdict,
)
from .factory import (
    DEFAULT_REGISTRY,
    GuardRegistry,
    build_guards_pipeline,
    register_guard_factory,
    register_safe_reply_factory,
)
from .global_repository import (
    GlobalGuardrailsRepository,
    StaticGlobalGuardrailsRepository,
)
from .global_snapshot import (
    GlobalGuardrailMatcher,
    GlobalGuardrailRule,
    GlobalGuardrailsSnapshot,
)
from .pipeline import GuardsPipeline

__all__ = [
    "DEFAULT_REGISTRY",
    "Guard",
    "GuardAuditCallback",
    "GuardContext",
    "GuardPipelineResult",
    "GuardRegistry",
    "GuardResult",
    "GuardVerdict",
    "GlobalGuardrailMatcher",
    "GlobalGuardrailRule",
    "GlobalGuardrailsRepository",
    "GlobalGuardrailsSnapshot",
    "GuardsPipeline",
    "StaticGlobalGuardrailsRepository",
    "build_guards_pipeline",
    "register_guard_factory",
    "register_safe_reply_factory",
]
