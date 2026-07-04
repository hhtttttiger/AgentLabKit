"""LLM-as-Judge — 协议与共享常量。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Judge(Protocol):
    """LLM-as-Judge 协议。

    具体实现由后端适配器提供（例如 GatewayJudge 通过 LLM Gateway 评分）。
    评估包本身不依赖 llm_gateway。
    """

    async def score(
        self,
        *,
        prompt: str,
        rubric: str,
    ) -> tuple[float, str]:
        """返回 (score, reasoning)。score 在 0-1 之间。"""
        ...


JUDGE_SYSTEM_PROMPT = """
你是一个严格的评估助手。根据给定的评分标准对内容进行评分。

输出格式（严格遵守）：
分数: X.X
理由: 你的评估理由

其中 X.X 是 0.0 到 1.0 之间的数字。
"""
