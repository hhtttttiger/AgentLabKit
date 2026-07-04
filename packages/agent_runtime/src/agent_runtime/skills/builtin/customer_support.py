"""Built-in skills: CustomerSupportSkill."""

from __future__ import annotations

from agent_runtime.skills.contracts import SkillPromptFragment, SkillSpec


class CustomerSupportSkill:
    """Built-in skill that enforces customer-support behavioural guidelines.

    Register via::

        registry.register(CustomerSupportSkill.spec)
    """

    spec = SkillSpec(
        skill_key="customer_support_v1",
        display_name="客服场景",
        description="启用客服场景的标准行为规范：礼貌用语、问题分类、升级策略。",
        version="1.0.0",
        prompt_fragments=(
            SkillPromptFragment(
                section="客服行为规范",
                content=(
                    "始终保持礼貌、专业的语气。\n"
                    "对于无法解决的问题，主动提示转人工处理，不要强行作答。\n"
                    "不透露内部系统信息或其他客户数据。"
                ),
                order=10,
            ),
        ),
        tags=frozenset({"customer_support", "safety"}),
    )
