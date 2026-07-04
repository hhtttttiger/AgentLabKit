"""SkillComposer — merges skill fragments and tool bindings into agent context.

Stateless beyond the registry reference; safe to call concurrently.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from agent_runtime.skills.contracts import SkillBinding, SkillPromptFragment
from agent_runtime.skills.registry import SkillRegistry
from agent_runtime.tools.contracts import ToolBinding

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Regex that matches {config.KEY} template variables in prompt content.
_CONFIG_VAR_RE = re.compile(r"\{config\.([^}]+)\}")

# Invocation-mode precedence (higher index = more permissive).
_MODE_PRECEDENCE: dict[str, int] = {
    "disabled": 0,
    "manual_only": 1,
    "auto": 2,
}


class SkillComposer:
    """Composes the final system prompt and tool binding list from skill bindings.

    The composer is intentionally stateless beyond its reference to a
    :class:`~agent_runtime.skills.registry.SkillRegistry`. All merging
    logic is pure and easily unit-tested.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        """Initialise the composer with a skill registry.

        Args:
            registry: The :class:`SkillRegistry` used to resolve skill keys.
        """
        self._registry = registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compose_prompt(
        self,
        base_prompt: str,
        bindings: list[SkillBinding],
        runtime_config: dict | None = None,
    ) -> str:
        """Append skill prompt fragments to *base_prompt*.

        Steps:

        1. Filter: only ``is_enabled=True`` bindings whose ``skill_key``
           exists in the registry.
        2. Collect all :class:`SkillPromptFragment` objects from enabled
           bindings.
        3. Sort fragments by global key
           ``(binding.order * 1000 + fragment.order)`` for stable ordering.
        4. Render ``{config.KEY}`` template variables from
           ``binding.config`` merged with *runtime_config*.
           Unknown variables are kept verbatim and a WARNING is logged.
        5. Append each fragment as ``"\\n\\n## {section}\\n{content}"``.
        6. Return result. If no bindings or all are disabled/missing,
           *base_prompt* is returned unchanged.

        Args:
            base_prompt: The system prompt to extend.
            bindings: Skill bindings for the current agent.
            runtime_config: Optional runtime config that overrides
                ``binding.config`` values during template rendering.

        Returns:
            Extended system prompt string.
        """
        if not bindings:
            return base_prompt

        # Step 1 & 2: collect (sort_key, fragment, merged_config) tuples.
        collected: list[tuple[int, SkillPromptFragment, dict]] = []
        for binding in bindings:
            if not binding.is_enabled:
                continue
            spec = self._registry.get(binding.skill_key)
            if spec is None:
                logger.warning(
                    "SkillComposer: skill '%s' not found in registry — skipping",
                    binding.skill_key,
                )
                continue
            # Merge config: binding.config base, runtime_config overrides.
            merged_config: dict = {**binding.config, **(runtime_config or {})}
            for fragment in spec.prompt_fragments:
                sort_key = binding.order * 1000 + fragment.order
                collected.append((sort_key, fragment, merged_config))

        if not collected:
            return base_prompt

        # Step 3: stable sort by global sort key.
        collected.sort(key=lambda t: t[0])

        # Steps 4 & 5: render and append.
        result = base_prompt
        for _, fragment, merged_config in collected:
            rendered = self._render_template(fragment.content, merged_config)
            result += f"\n\n## {fragment.section}\n{rendered}"

        return result

    def compose_tool_bindings(
        self,
        base_bindings: list[ToolBinding],
        skill_bindings: list[SkillBinding],
    ) -> list[ToolBinding]:
        """Merge base tool bindings with overrides from skill bindings.

        Conflict resolution (same ``tool_name`` from multiple sources):

        - ``is_enabled=False`` wins over ``True`` (any False → disabled).
        - ``invocation_mode``: ``"auto"`` > ``"manual_only"`` > ``"disabled"``
          (most permissive wins).
        - ``description``: last explicit (non-``None``) value ordered by
          ``SkillBinding.order`` wins.
        - ``config``: shallow merge; later skills (by ``SkillBinding.order``)
          override earlier ones.

        Args:
            base_bindings: The agent's base tool bindings.
            skill_bindings: Skill bindings that may carry tool overrides.

        Returns:
            Merged list of :class:`ToolBinding` objects (one per tool name).
        """
        if not skill_bindings:
            return list(base_bindings)

        # Accumulate all tool binding candidates keyed by tool_name.
        # Order: base first, then skill overrides in binding.order sequence.
        all_bindings: list[tuple[int, ToolBinding]] = [
            (0, tb) for tb in base_bindings
        ]

        sorted_skill_bindings = sorted(skill_bindings, key=lambda sb: sb.order)
        for idx, skill_binding in enumerate(sorted_skill_bindings, start=1):
            if not skill_binding.is_enabled:
                continue
            for tool_override in skill_binding.tool_overrides:
                all_bindings.append((idx, tool_override))

        # Merge per tool_name.
        merged: dict[str, ToolBinding] = {}
        for _order_idx, tb in all_bindings:
            name = tb.tool_name
            if name not in merged:
                merged[name] = tb
                continue
            existing = merged[name]
            merged[name] = self._merge_tool_binding(existing, tb)

        return list(merged.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _render_template(content: str, config: dict) -> str:
        """Replace ``{config.KEY}`` placeholders using *config*.

        Unknown keys are kept verbatim and a WARNING is emitted.

        Args:
            content: Raw fragment content with optional template vars.
            config: Key→value mapping used for substitution.

        Returns:
            Rendered string.
        """
        missing_keys: list[str] = []

        def replacer(match: re.Match) -> str:
            key = match.group(1)
            if key in config:
                return str(config[key])
            missing_keys.append(key)
            return match.group(0)  # keep original placeholder

        rendered = _CONFIG_VAR_RE.sub(replacer, content)
        if missing_keys:
            logger.warning(
                "SkillComposer: unknown template variable(s) %s — kept as-is",
                missing_keys,
            )
        return rendered

    @staticmethod
    def _merge_tool_binding(existing: ToolBinding, incoming: ToolBinding) -> ToolBinding:
        """Merge *incoming* into *existing* using conflict-resolution rules.

        Args:
            existing: Currently accumulated binding for this tool.
            incoming: New binding to fold in.

        Returns:
            A new :class:`ToolBinding` reflecting the merged state.
        """
        # is_enabled: False wins.
        is_enabled = existing.is_enabled and incoming.is_enabled

        # invocation_mode: most permissive wins.
        existing_precedence = _MODE_PRECEDENCE.get(existing.invocation_mode, 0)
        incoming_precedence = _MODE_PRECEDENCE.get(incoming.invocation_mode, 0)
        invocation_mode = (
            incoming.invocation_mode
            if incoming_precedence >= existing_precedence
            else existing.invocation_mode
        )

        # description: last explicit (non-None) wins.
        description = (
            incoming.description
            if incoming.description is not None
            else existing.description
        )

        # config: shallow merge, incoming overrides.
        config = {**existing.config, **incoming.config}

        # display_name: last explicit (non-None) wins.
        display_name = (
            incoming.display_name
            if incoming.display_name is not None
            else existing.display_name
        )

        return ToolBinding(
            tool_name=existing.tool_name,
            display_name=display_name,
            description=description,
            invocation_mode=invocation_mode,  # type: ignore[arg-type]
            is_enabled=is_enabled,
            config=config,
        )
