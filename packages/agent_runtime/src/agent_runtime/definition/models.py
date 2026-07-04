"""Domain models for published agent definitions.

These mirror the cross-language read model (Section 7.1 of the plan).
Python only reads; .NET owns the write path.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any


def _voice_get(policy: dict[str, Any], snake: str, camel: str, default: Any) -> Any:
    value = policy.get(snake)
    if value is None:
        value = policy.get(camel)
    return default if value is None else value


def _parse_voice_guardrails_policy(
    policy: dict[str, Any],
) -> "VoiceGuardrailsSnapshot | None":
    voice = policy.get("voice_guardrails")
    if voice is None:
        voice = policy.get("voiceGuardrails")
    if voice is None:
        return None
    return VoiceGuardrailsSnapshot(
        mode=str(_voice_get(voice, "mode", "mode", "observe_only") or "observe_only"),
        revision=int(_voice_get(voice, "revision", "revision", 0) or 0),
        judge_timeout_ms=int(
            _voice_get(voice, "judge_timeout_ms", "judgeTimeoutMs", 350) or 350
        ),
        generator_timeout_ms=int(
            _voice_get(voice, "generator_timeout_ms", "generatorTimeoutMs", 250)
            or 250
        ),
        max_added_latency_ms=int(
            _voice_get(voice, "max_added_latency_ms", "maxAddedLatencyMs", 700) or 700
        ),
        actions=tuple(_voice_get(voice, "actions", "actions", ()) or ()),
    )


@dataclass(frozen=True, slots=True)
class SkillDefinitionSnapshot:
    """Read-only snapshot of a published skill definition from the .NET plane."""

    skill_key: str
    display_name: str
    description: str
    version: str
    spec: dict[str, Any] = field(default_factory=dict)
    """Raw SkillSpec payload stored in ``agent_skill_definitions.SpecJson``."""


@dataclass(frozen=True, slots=True)
class SkillBindingSnapshot:
    """Snapshot of a skill binding as stored in ``agent_skill_bindings``.

    Lightweight, DB-derived representation. The runtime engine converts these
    into typed :class:`~agent_runtime.skills.contracts.SkillBinding` objects
    before passing them to :class:`~agent_runtime.skills.composer.SkillComposer`.
    """

    skill_key: str
    """Must reference a published ``agent_skill_definitions.SkillKey``."""

    is_enabled: bool = True
    """When ``False``, this binding is silently skipped by the composer."""

    binding_order: int = 100
    """Cross-skill ordering weight; lower = earlier in the composed prompt."""

    config: dict[str, Any] = field(default_factory=dict)
    """Runtime config overrides passed to the skill for template rendering."""

    tool_overrides_raw: tuple[dict[str, Any], ...] = ()
    """Raw tool-override dicts deserialized from ``ToolOverridesJson``.

    Each dict has the same shape as :class:`~agent_runtime.tools.contracts.ToolBinding`
    field names (``tool_name``, ``invocation_mode``, ``is_enabled``, …).
    The engine converts these to typed ``ToolBinding`` objects.
    """

    definition: SkillDefinitionSnapshot | None = None
    """Published skill definition metadata loaded from ``agent_skill_definitions``."""


@dataclass(frozen=True, slots=True)
class McpBindingSnapshot:
    """Resolved MCP server binding for an agent definition version.

    Combines the per-agent binding policy (``is_enabled``, ``tool_whitelist``)
    with the referenced server's connection parameters (``server_config_json``).
    Stored as an immutable snapshot so the runtime can reconstruct a typed
    :class:`~agent_runtime.mcp.contracts.McpServerConfig` via
    ``McpServerConfig.model_validate(snap.server_config_json)`` without coupling
    this module to the MCP package.

    Loaded by :class:`~agent_runtime.definition.loader.SqlAlchemyAgentDefinitionLoader`
    from ``agent_mcp_bindings`` joined with ``agent_mcp_server_configs``.
    """

    server_name: str
    """Logical server identifier — matches ``McpServerConfig.name``."""

    is_enabled: bool = True
    """When ``False``, the runtime must skip this binding entirely."""

    tool_whitelist: tuple[str, ...] | None = None
    """Raw (un-prefixed) tool names permitted for this agent.

    ``None`` means all tools are allowed; an empty tuple means no tools.
    """

    server_config_json: dict[str, Any] = field(default_factory=dict)
    """Full ``McpServerConfig`` payload (transport, command/url, headers, …).

    Serialised from ``agent_mcp_server_configs.ConfigJson``, merged with any
    ``config_overrides`` from the binding row.
    """


@dataclass(frozen=True, slots=True)
class ToolBindingSnapshot:
    """A tool binding as declared in the agent definition version."""

    tool_name: str
    description: str | None = None
    invocation_mode: str = "auto"
    is_required: bool = False
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeBindingSnapshot:
    """Published knowledge-base binding available to this agent version."""

    knowledge_base_id: str
    sort_order: int
    config: dict[str, Any] = field(default_factory=dict)
    config_version: int = 1


@dataclass(frozen=True, slots=True)
class VoiceGuardrailsSnapshot:
    """Typed agent-local voice guardrail policy.

    Derived on demand from ``AgentDefinitionSnapshot.guardrails_policy`` so the
    definition snapshot keeps a single source of truth for advanced policy JSON.
    """

    mode: str = "observe_only"
    """Rollout mode: 'enforced', 'observe_only'."""
    revision: int = 0
    """Management-plane revision number; used for snapshot freshness checks."""
    judge_timeout_ms: int = 350
    """Maximum ms to wait for the LLM-based judge response."""
    generator_timeout_ms: int = 250
    """Maximum ms to wait for the safe-reply generator response."""
    max_added_latency_ms: int = 700
    """Hard cap on total added latency before the guard is bypassed."""
    actions: tuple[str, ...] = ()
    """Permitted action set: interrupt_only, fallback_reply, transfer_human."""


@dataclass(frozen=True, slots=True)
class AgentDefinitionSnapshot:
    """Immutable snapshot of a published agent definition version.

    Contains everything the runtime needs to drive a single agent turn.
    """

    agent_key: str
    version_number: int
    display_name: str
    description: str | None = None
    status: str = "published"
    default_locale: str | None = None
    system_prompt_template: str = ""
    model_binding_key: str = ""
    tools: tuple[ToolBindingSnapshot, ...] = ()
    knowledge_sources: tuple[str, ...] = ()
    knowledge_bindings: tuple[KnowledgeBindingSnapshot, ...] = ()
    runtime_options: dict[str, Any] = field(default_factory=dict)
    handoff_policy: dict[str, Any] = field(default_factory=dict)
    response_policy: dict[str, Any] = field(default_factory=dict)
    guardrails_policy: dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    updated_at: str = ""
    mcp_bindings: tuple[McpBindingSnapshot, ...] = ()
    """MCP server bindings declared for this version (Phase 2)."""

    skill_bindings: tuple[SkillBindingSnapshot, ...] = ()
    """Skill bindings declared for this version (Skills Phase 2)."""
    voice_guardrails: InitVar["VoiceGuardrailsSnapshot | None"] = None

    def __post_init__(self, voice_guardrails: "VoiceGuardrailsSnapshot | None") -> None:
        if (
            not isinstance(voice_guardrails, VoiceGuardrailsSnapshot)
            or self.guardrails_policy.get("voice_guardrails") is not None
            or self.guardrails_policy.get("voiceGuardrails") is not None
        ):
            return
        object.__setattr__(
            self,
            "guardrails_policy",
            {
                **self.guardrails_policy,
                "voice_guardrails": {
                    "mode": voice_guardrails.mode,
                    "revision": voice_guardrails.revision,
                    "judge_timeout_ms": voice_guardrails.judge_timeout_ms,
                    "generator_timeout_ms": voice_guardrails.generator_timeout_ms,
                    "max_added_latency_ms": voice_guardrails.max_added_latency_ms,
                    "actions": list(voice_guardrails.actions),
                },
            },
        )

    @property
    def auto_tool_names(self) -> frozenset[str]:
        """Tool names that should be included in the LLM function-calling schema."""
        return frozenset(
            t.tool_name for t in self.tools if t.invocation_mode == "auto"
        )

    @property
    def enabled_tool_names(self) -> frozenset[str]:
        """All non-disabled tool names (auto + manual_only)."""
        return frozenset(
            t.tool_name for t in self.tools if t.invocation_mode != "disabled"
        )

    @property
    def voice_guardrails(self) -> "VoiceGuardrailsSnapshot | None":
        """Agent-local voice guardrails derived from ``guardrails_policy``."""
        return _parse_voice_guardrails_policy(dict(self.guardrails_policy or {}))
