"""Read-side global guardrails snapshot models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, frozenset):
        return {_thaw_value(item) for item in value}
    return value


@dataclass(frozen=True, slots=True)
class GlobalGuardrailMatcher:
    """Matcher definition for a single global guardrail rule."""

    type: str
    rubric: str
    scope: str
    threshold: float | None = None
    hints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "hints", tuple(self.hints))


@dataclass(frozen=True, slots=True)
class GlobalGuardrailRule:
    """Single global guardrail rule in the active snapshot."""

    rule_key: str
    title: str
    description: str
    enabled: bool
    priority: int
    matcher: GlobalGuardrailMatcher
    action: str
    action_config: Mapping[str, Any] = field(default_factory=dict)
    failure_mode: str = "fail_open"

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_config", _freeze_value(self.action_config))


@dataclass(frozen=True, slots=True)
class GlobalGuardrailsSnapshot:
    """Active global guardrails ruleset resolved for runtime consumption."""

    ruleset_key: str = "global"
    revision: int = 0
    rules: tuple[GlobalGuardrailRule, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", tuple(self.rules))


def clone_global_guardrails_snapshot(
    snapshot: GlobalGuardrailsSnapshot | None,
) -> GlobalGuardrailsSnapshot | None:
    if snapshot is None:
        return None

    return GlobalGuardrailsSnapshot(
        ruleset_key=snapshot.ruleset_key,
        revision=snapshot.revision,
        rules=tuple(
            GlobalGuardrailRule(
                rule_key=rule.rule_key,
                title=rule.title,
                description=rule.description,
                enabled=rule.enabled,
                priority=rule.priority,
                matcher=GlobalGuardrailMatcher(
                    type=rule.matcher.type,
                    rubric=rule.matcher.rubric,
                    scope=rule.matcher.scope,
                    threshold=rule.matcher.threshold,
                    hints=tuple(rule.matcher.hints),
                ),
                action=rule.action,
                action_config=_thaw_value(rule.action_config),
                failure_mode=rule.failure_mode,
            )
            for rule in snapshot.rules
        ),
    )
