"""Built-in skills: RagQaSkill."""

from __future__ import annotations

from agent_runtime.skills.contracts import SkillPromptFragment, SkillSpec


class RagQaSkill:
    """Built-in skill that enables RAG-based knowledge-base Q&A behaviour.

    Register via::

        registry.register(RagQaSkill.spec)
    """

    spec = SkillSpec(
        skill_key="rag_qa_v1",
        display_name="RAG 知识库问答",
        description="启用基于知识库检索的问答能力，引导 agent 优先从知识库获取信息。",
        version="1.0.0",
        prompt_fragments=(
            SkillPromptFragment(
                section="知识库检索指令",
                content=(
                    "当用户提问时，优先使用 knowledge_search 工具检索相关信息。\n"
                    "若检索结果与问题高度相关，基于检索结果作答并说明信息来源。\n"
                    "若检索结果不足，诚实说明知识库中无相关信息，不要编造。"
                ),
                order=50,
            ),
        ),
        recommended_tools=("knowledge_search",),
        tags=frozenset({"rag", "read_only"}),
    )
