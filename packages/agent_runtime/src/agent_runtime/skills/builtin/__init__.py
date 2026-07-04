"""Builtin skills package."""

from agent_runtime.skills.registry import SkillRegistry
from agent_runtime.skills.builtin.customer_support import CustomerSupportSkill
from agent_runtime.skills.builtin.rag_qa import RagQaSkill


def register_builtin_skills(registry: SkillRegistry) -> SkillRegistry:
    """Register all built-in skill specs into *registry* and return it."""
    registry.register(RagQaSkill.spec)
    registry.register(CustomerSupportSkill.spec)
    return registry


__all__ = ["RagQaSkill", "CustomerSupportSkill", "register_builtin_skills"]
