"""Contracts for the Skills system.

Defines the core data structures used by SkillRegistry and SkillComposer.
Nothing here imports from sibling modules; safe to import from anywhere in
the skills package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_runtime.tools.contracts import ToolBinding


# ---------------------------------------------------------------------------
# SkillPromptFragment — a single insertable prompt section
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillPromptFragment:
    """A single section of prompt text contributed by a Skill.

    Fragments from all enabled skills are sorted and appended to the base
    prompt by :class:`~agent_runtime.skills.composer.SkillComposer`.
    """

    section: str
    """Section header displayed as a Markdown H2, e.g. ``"RAG 检索指令"``."""

    content: str
    """Prompt text; supports ``{config.KEY}`` template variable substitution."""

    order: int = 100
    """Sorting key within a skill (lower = earlier). Combined with
    ``SkillBinding.order`` for cross-skill ordering."""

    is_required: bool = True
    """Reserved for future use — currently all fragments from enabled
    bindings are always included."""


# ---------------------------------------------------------------------------
# SkillSpec — immutable metadata for a single skill
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillSpec:
    """Complete, immutable metadata for a registered Skill.

    A Skill bundles prompt fragments, recommended tools, and a configuration
    schema into a versioned, reusable capability unit.
    """

    skill_key: str
    """Unique identifier, e.g. ``"rag_qa_v1"``."""

    display_name: str
    """Human-readable name shown in management UI."""

    description: str
    """What this skill does — shown to operators selecting skills."""

    version: str
    """Semver-style string, e.g. ``"1.0.0"``."""

    prompt_fragments: tuple[SkillPromptFragment, ...] = ()
    """Ordered collection of prompt sections contributed by this skill."""

    recommended_tools: tuple[str, ...] = ()
    """Tool names this skill expects to be present (advisory, not enforced)."""

    config_schema: dict = field(default_factory=dict)
    """JSON Schema describing accepted config keys for ``SkillBinding.config``."""

    tags: frozenset[str] = frozenset()
    """Classification tags, e.g. ``frozenset({"rag", "read_only"})``."""


# ---------------------------------------------------------------------------
# SkillBinding — per-agent binding controlling how a Skill is activated
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillBinding:
    """Controls how a registered Skill is activated for a specific agent.

    Derived from the ``agent_skill_bindings`` configuration managed by the
    .NET management plane (Phase 2 will load these from DB).
    """

    skill_key: str
    """Must match a :attr:`SkillSpec.skill_key` registered in the registry."""

    is_enabled: bool = True
    """Master switch; disabled bindings are completely ignored by the composer."""

    order: int = 100
    """Cross-skill ordering multiplier. Fragment global sort key =
    ``binding.order * 1000 + fragment.order``."""

    config: dict = field(default_factory=dict)
    """Runtime config passed to the skill; values substitute ``{config.KEY}``
    template variables in prompt fragments."""

    tool_overrides: tuple[ToolBinding, ...] = ()
    """Optional per-agent overrides for the skill's recommended tools."""
