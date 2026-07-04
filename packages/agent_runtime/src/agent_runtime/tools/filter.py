"""Tool filtering logic — reconciles registered tools with agent bindings.

:class:`ToolFilter` is a **pure, stateless** utility.  It takes the list of
tools currently registered in a :class:`~agent_runtime.tools.registry.DynamicToolRegistry`
and the list of :class:`~agent_runtime.tools.contracts.ToolBinding` objects
from an agent definition and returns only the tools that should be visible to
that agent at runtime.

Filtering rules
---------------
- ``bindings=None``  →  all registered tools are returned (backward-compat,
  no agent definition scenario).
- ``bindings=[]``    →  empty list (agent explicitly declares no tools).
- ``binding.is_enabled=False``  →  tool is excluded.
- ``binding.invocation_mode="disabled"``  →  tool is excluded.
- A ``tool_name`` that appears in *bindings* but is **not** registered in the
  registry is silently skipped with a ``WARNING`` log.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .contracts import ToolBinding, ToolSpec

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ToolFilter:
    """Reconcile registered tool specs with agent definition bindings."""

    @staticmethod
    def apply(
        registered: list[ToolSpec],
        bindings: list[ToolBinding] | None,
    ) -> list[tuple[ToolSpec, ToolBinding | None]]:
        """Return the subset of *registered* tools permitted by *bindings*.

        Args:
            registered: All tools currently held by the registry.
            bindings: Per-agent binding list from the agent definition.
                      Pass ``None`` to return **all** registered tools.

        Returns:
            Ordered list of ``(spec, binding)`` pairs.  ``binding`` is
            ``None`` when ``bindings`` is ``None`` (backward-compat path).
        """
        if bindings is None:
            return [(spec, None) for spec in registered]

        # Build a lookup from name → spec for O(1) access
        registered_index: dict[str, ToolSpec] = {s.name: s for s in registered}

        result: list[tuple[ToolSpec, ToolBinding]] = []
        for binding in bindings:
            # Skip disabled tools
            if not binding.is_enabled:
                continue
            if binding.invocation_mode == "disabled":
                continue

            spec = registered_index.get(binding.tool_name)
            if spec is None:
                logger.warning(
                    "ToolFilter: binding references unregistered tool '%s' — skipping",
                    binding.tool_name,
                )
                continue

            result.append((spec, binding))

        return result

    @staticmethod
    def auto_only(
        pairs: list[tuple[ToolSpec, ToolBinding | None]],
    ) -> list[tuple[ToolSpec, ToolBinding | None]]:
        """Filter *pairs* to only those that should be injected into the LLM schema.

        - ``binding=None``             → include (backward-compat, all are auto)
        - ``invocation_mode="auto"``   → include
        - ``invocation_mode="manual_only"`` → exclude from LLM schema
        """
        return [
            (spec, binding)
            for spec, binding in pairs
            if binding is None or binding.invocation_mode == "auto"
        ]
