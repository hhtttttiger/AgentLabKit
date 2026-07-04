"""Factory: build a GuardsPipeline from GuardrailsSettings.

Extension point
---------------
Use :data:`DEFAULT_REGISTRY` to register custom guards globally, or instantiate
a fresh :class:`GuardRegistry` for isolated testing / multi-tenant scenarios::

    from agent_runtime.guardrails.factory import DEFAULT_REGISTRY

    DEFAULT_REGISTRY.register(
        "my_guard",
        phase="input",
        factory=lambda settings: MyGuard(threshold=settings.my_threshold),
    )
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .contracts import Guard, GuardAuditCallback
from .pipeline import GuardsPipeline, SafeReplyGenerator

if TYPE_CHECKING:
    from ..config import GuardrailsSettings

GuardPhase = Literal["input", "output", "tool"]
GuardFactory = Callable[["GuardrailsSettings"], Guard]
SafeReplyFactory = Callable[["GuardrailsSettings"], SafeReplyGenerator]


@dataclass(frozen=True, slots=True)
class RegisteredGuardFactory:
    phase: GuardPhase
    factory: GuardFactory


@dataclass(frozen=True, slots=True)
class RegisteredSafeReplyFactory:
    factory: SafeReplyFactory


class GuardRegistry:
    """Stateful registry mapping guard names to their factory functions.

    Instantiate a fresh :class:`GuardRegistry` in tests to avoid sharing
    state with :data:`DEFAULT_REGISTRY`.
    """

    def __init__(self) -> None:
        self._factories: dict[str, RegisteredGuardFactory] = {}
        self._safe_reply_factories: dict[str, RegisteredSafeReplyFactory] = {}

    def register(
        self,
        name: str,
        *,
        phase: GuardPhase,
        factory: GuardFactory,
        replace: bool = False,
    ) -> None:
        """Register a guard factory.  No-op if *name* already exists and ``replace=False``."""
        if not replace and name in self._factories:
            return
        self._factories[name] = RegisteredGuardFactory(phase=phase, factory=factory)

    def build_pipeline(
        self,
        settings: "GuardrailsSettings",
        *,
        audit_callback: GuardAuditCallback | None = None,
        extra_guards: list[Guard] | None = None,
        safe_reply_generator: SafeReplyGenerator | None = None,
        safe_reply_generator_name: str | None = None,
    ) -> GuardsPipeline:
        """Construct a :class:`GuardsPipeline` from declarative settings.

        Unknown guard names are silently skipped so that settings referencing
        unregistered guards degrade gracefully.
        """
        input_guards: list[Guard] = []
        output_guards: list[Guard] = []
        tool_guards: list[Guard] = []

        for name in settings.input_guards:
            guard = self._instantiate(name, settings)
            if guard is not None:
                input_guards.append(guard)

        for name in settings.output_guards:
            guard = self._instantiate(name, settings)
            if guard is not None:
                output_guards.append(guard)

        for name in settings.tool_guards:
            guard = self._instantiate(name, settings)
            if guard is not None:
                tool_guards.append(guard)

        for guard in extra_guards or []:
            bucket: list[Guard] | None = {
                "input": input_guards,
                "output": output_guards,
                "tool": tool_guards,
            }.get(guard.phase)
            if bucket is not None:
                bucket.append(guard)

        return GuardsPipeline(
            input_guards=input_guards,
            output_guards=output_guards,
            tool_guards=tool_guards,
            block_response=settings.block_response,
            audit_callback=audit_callback,
            safe_reply_generator=(
                safe_reply_generator
                if safe_reply_generator is not None
                else self.create_safe_reply_generator(
                    safe_reply_generator_name,
                    settings=settings,
                )
            ),
        )

    def register_safe_reply_factory(
        self,
        name: str,
        *,
        factory: SafeReplyFactory,
        replace: bool = False,
    ) -> None:
        """Register a safe-reply generator factory."""
        if not replace and name in self._safe_reply_factories:
            return
        self._safe_reply_factories[name] = RegisteredSafeReplyFactory(factory=factory)

    def create_safe_reply_generator(
        self,
        name: str | None,
        *,
        settings: "GuardrailsSettings",
    ) -> SafeReplyGenerator | None:
        if not name:
            return None
        entry = self._safe_reply_factories.get(name)
        if entry is None:
            return None
        return entry.factory(settings)

    def _instantiate(self, name: str, settings: "GuardrailsSettings") -> Guard | None:
        entry = self._factories.get(name)
        if entry is None:
            return None
        return entry.factory(settings)


def _make_default_registry() -> GuardRegistry:
    """Build the default registry with all built-in guards pre-registered."""
    from .input.input_length import InputLengthGuard
    from .input.prompt_injection import PromptInjectionGuard
    from .output.content_safety import ContentSafetyGuard
    from .output.pii_masking import PiiMaskingGuard
    from .tool.parameter_guard import ParameterGuard

    registry = GuardRegistry()
    registry.register(
        "prompt_injection",
        phase="input",
        factory=lambda s: PromptInjectionGuard(block_threshold=s.prompt_injection_threshold),
    )
    registry.register(
        "input_length",
        phase="input",
        factory=lambda s: InputLengthGuard(max_chars=s.max_input_chars),
    )
    registry.register(
        "pii_masking",
        phase="output",
        factory=lambda s: PiiMaskingGuard(categories=frozenset(s.pii_categories)),
    )
    registry.register(
        "content_safety",
        phase="output",
        factory=lambda s: ContentSafetyGuard(block_categories=frozenset(s.content_safety_categories)),
    )
    registry.register(
        "parameter_validation",
        phase="tool",
        factory=lambda s: ParameterGuard(max_string_length=s.max_tool_param_length),
    )
    return registry


#: Module-level default registry.  Import and call ``.register()`` to add custom guards.
DEFAULT_REGISTRY: GuardRegistry = _make_default_registry()


# ── Backward-compatible free functions ─────────────────────────────────────────


def register_guard_factory(
    name: str,
    *,
    phase: GuardPhase,
    factory: GuardFactory,
    replace: bool = False,
) -> None:
    """Register a guard factory in :data:`DEFAULT_REGISTRY`."""
    DEFAULT_REGISTRY.register(name, phase=phase, factory=factory, replace=replace)


def register_safe_reply_factory(
    name: str,
    *,
    factory: SafeReplyFactory,
    replace: bool = False,
) -> None:
    """Register a safe-reply generator factory in :data:`DEFAULT_REGISTRY`."""
    DEFAULT_REGISTRY.register_safe_reply_factory(
        name,
        factory=factory,
        replace=replace,
    )


def build_guards_pipeline(
    settings: "GuardrailsSettings",
    *,
    audit_callback: GuardAuditCallback | None = None,
    extra_guards: list[Guard] | None = None,
    safe_reply_generator: SafeReplyGenerator | None = None,
    safe_reply_generator_name: str | None = None,
) -> GuardsPipeline:
    """Build a :class:`GuardsPipeline` using :data:`DEFAULT_REGISTRY`."""
    return DEFAULT_REGISTRY.build_pipeline(
        settings,
        audit_callback=audit_callback,
        extra_guards=extra_guards,
        safe_reply_generator=safe_reply_generator,
        safe_reply_generator_name=safe_reply_generator_name,
    )
