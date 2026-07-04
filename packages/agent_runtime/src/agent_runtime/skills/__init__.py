"""Skills package — reusable capability units for AgentRuntime.

Public API::

    from agent_runtime.skills import (
        SkillSpec,
        SkillPromptFragment,
        SkillBinding,
        SkillRegistry,
        SkillComposer,
    )
"""

from agent_runtime.skills.composer import SkillComposer
from agent_runtime.skills.contracts import SkillBinding, SkillPromptFragment, SkillSpec
from agent_runtime.skills.registry import SkillRegistry

__all__ = [
    "SkillSpec",
    "SkillPromptFragment",
    "SkillBinding",
    "SkillRegistry",
    "SkillComposer",
]
