"""SkillRegistry — in-process registry for Skill specifications.

Designed for startup-time registration (not thread-safe for concurrent
writes). Read-only access after startup is safe from multiple threads.
"""

from __future__ import annotations

import logging

from agent_runtime.skills.contracts import SkillSpec

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Central store for :class:`~agent_runtime.skills.contracts.SkillSpec` objects.

    **Thread-safety note:** This registry is designed for startup-time
    registration. All ``register`` / ``unregister`` calls should complete
    before the application begins serving requests. Concurrent read access
    (``get``, ``list_all``, ``list_by_tag``) is safe once writing is done.
    """

    def __init__(self) -> None:
        self._specs: dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> None:
        """Register a skill spec, overwriting any existing entry with the same key.

        Args:
            spec: The :class:`SkillSpec` to register.
        """
        if spec.skill_key in self._specs:
            logger.debug(
                "SkillRegistry: overwriting existing skill '%s'", spec.skill_key
            )
        self._specs[spec.skill_key] = spec

    def get(self, skill_key: str) -> SkillSpec | None:
        """Return the :class:`SkillSpec` for *skill_key*, or ``None`` if not found.

        Args:
            skill_key: The unique skill identifier to look up.
        """
        return self._specs.get(skill_key)

    def list_all(self) -> list[SkillSpec]:
        """Return all registered specs (order is insertion order)."""
        return list(self._specs.values())

    def list_by_tag(self, tag: str) -> list[SkillSpec]:
        """Return all specs that include *tag* in their :attr:`SkillSpec.tags`.

        Args:
            tag: The tag string to filter by.
        """
        return [spec for spec in self._specs.values() if tag in spec.tags]

    def unregister(self, skill_key: str) -> bool:
        """Remove a skill from the registry.

        Args:
            skill_key: The unique skill identifier to remove.

        Returns:
            ``True`` if the skill existed and was removed, ``False`` otherwise.
        """
        if skill_key in self._specs:
            del self._specs[skill_key]
            return True
        return False
