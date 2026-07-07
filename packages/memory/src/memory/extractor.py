"""MemoryExtractor — 使用 LLM 从对话中提取记忆。

三种提取模式：
- episodic: 对话摘要
- semantic: 事实性知识（偏好、关键实体）
- procedural: 用户行为模式
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryExtractor(Protocol):
    async def extract_episodic(self, messages: list[Any]) -> list[str]: ...
    async def extract_semantic(self, messages: list[Any]) -> list[str]: ...
    async def extract_procedural(self, messages: list[Any]) -> list[str]: ...


EPISODIC_PROMPT = """\
分析以下对话，提取一个简洁的对话摘要（1-2句话）。只关注关键事实和结果，忽略寒暄。

对话内容：
{conversation}

输出格式：直接输出摘要文本，不要任何前缀或格式。
"""

SEMANTIC_PROMPT = """\
分析以下对话，提取其中包含的事实性知识和信息。包括但不限于：
- 用户明确表达的偏好或要求
- 提到的关键实体（人名、地名、项目名等）
- 具体的技术细节或配置信息

每条事实一行，格式为简洁的陈述句。如果没有可提取的事实，输出"无"。

对话内容：
{conversation}
"""

PROCEDURAL_PROMPT = """\
分析以下对话，推断用户的交互偏好和行为模式。例如：
- 用户喜欢简洁还是详细的回复
- 用户偏好的语言风格
- 用户常用的操作模式

每条推断一行。如果无法推断，输出"无"。

对话内容：
{conversation}
"""


class GatewayMemoryExtractor:
    """通过 LLM Gateway 提取记忆。"""

    def __init__(self, gateway_service: Any, model_key: str = "") -> None:
        self._gateway = gateway_service
        self._model = model_key

    def _messages_to_text(self, messages: list[Any]) -> str:
        """将 AgentMessage 列表转为纯文本。"""
        lines = []
        for msg in messages:
            role = getattr(msg, "role", "")
            content = getattr(msg, "content", "")
            if content and role in ("user", "assistant"):
                lines.append(f"[{role}]: {content}")
        return "\n".join(lines)

    async def _extract(self, prompt_template: str, messages: list[Any]) -> list[str]:
        conversation = self._messages_to_text(messages)
        if not conversation.strip():
            return []

        prompt = prompt_template.format(conversation=conversation)

        try:
            # 使用 llm_gateway 的 GatewayService
            from llm_gateway.models import TextGenerateRequest
            request = TextGenerateRequest(
                prompt=prompt,
                model=self._model or None,
                max_output_tokens=512,
                temperature=0.1,
            )
            response = await self._gateway.generate_text(request)
            text = response.text
        except Exception:
            import logging
            logging.getLogger(__name__).exception("memory.extractor._extract_failed")
            return []

        # Parse results
        results = []
        for line in text.strip().split("\n"):
            line = line.strip().lstrip("- •*0123456789. ").strip()
            if line and line != "无" and len(line) > 5:
                results.append(line)
        return results

    async def extract_episodic(self, messages: list[Any]) -> list[str]:
        return await self._extract(EPISODIC_PROMPT, messages)

    async def extract_semantic(self, messages: list[Any]) -> list[str]:
        return await self._extract(SEMANTIC_PROMPT, messages)

    async def extract_procedural(self, messages: list[Any]) -> list[str]:
        return await self._extract(PROCEDURAL_PROMPT, messages)
