"""MemoryInjector — 将检索到的记忆注入到 agent 上下文中。"""

from __future__ import annotations

from typing import Any, Sequence

from .contracts import MemoryRecord

# Metadata keys compatible with agent_runtime's MessagePriority system
PRIORITY_METADATA_KEY = "_priority"
MEMORY_KIND_METADATA_KEY = "_memory_kind"
MEMORY_KIND_LONG_TERM = "long_term_memory"


class MemoryInjector:
    """将长期记忆注入到 agent 消息列表中。

    生成的消息带有 metadata:
    - _priority: "normal" — 适配现有 ContextManager 的优先级系统
    - _memory_kind: "long_term_memory" — 标识为长期记忆
    """

    def inject(
        self,
        memories: Sequence[MemoryRecord],
        history: Sequence[Any],
    ) -> list[Any]:
        """将记忆作为 system 消息插入到 history 开头。

        Parameters
        ----------
        memories:
            MemoryRecord 列表。
        history:
            现有的 AgentMessage 列表。

        Returns
        -------
        增强后的消息列表（不修改原列表）。
        """
        if not memories:
            return list(history)

        # 构建记忆摘要文本
        lines = ["[长期记忆] 以下是关于此用户的历史记忆，请在回复时参考："]
        for m in memories:
            type_label = m.memory_type.value if hasattr(m, "memory_type") else "unknown"
            lines.append(f"- ({type_label}) {m.content}")

        memory_content = "\n".join(lines)

        # 创建记忆消息 — 使用 duck typing 适配 AgentMessage
        # agent_runtime 的 AgentMessage 是 pydantic model，需要构造兼容对象
        try:
            from agent_runtime.contracts.models import AgentMessage, AgentRole
            memory_msg = AgentMessage(
                role=AgentRole.SYSTEM,
                content=memory_content,
                metadata={
                    PRIORITY_METADATA_KEY: "normal",
                    MEMORY_KIND_METADATA_KEY: MEMORY_KIND_LONG_TERM,
                },
            )
        except ImportError:
            # Fallback: 如果无法导入，返回原始 history
            return list(history)

        return [memory_msg] + list(history)
