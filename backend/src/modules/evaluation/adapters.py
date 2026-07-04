"""评估框架的具体适配器。

将 evaluation 包的抽象协议（Judge、TargetExecutor）桥接到
后端具体服务（GatewayService、AgentRuntime、RetrievalService）。
所有对 llm_gateway / agent_runtime 的依赖集中于此文件，
evaluation 包本身保持零依赖。
"""

from __future__ import annotations

import uuid
from typing import Any

from evaluation.contracts import EvalCase, EvalRunConfig, TargetExecutor
from evaluation.judge import JUDGE_SYSTEM_PROMPT


# ── GatewayJudge（从 packages/evaluation 迁出）────────────────────────

class GatewayJudge:
    """通过 LLM Gateway 实现 Judge 协议。"""

    def __init__(self, gateway_service: Any, model: str = "") -> None:
        self._gateway = gateway_service
        self._model = model

    async def score(
        self,
        *,
        prompt: str,
        rubric: str,
    ) -> tuple[float, str]:
        user_msg = f"评分标准：\n{rubric}\n\n待评估内容：\n{prompt}"
        try:
            from llm_gateway.models import TextGenerateRequest

            request = TextGenerateRequest(
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                model=self._model or None,
                max_tokens=512,
                temperature=0.1,
            )
            response = await self._gateway.generate_text(request)
            text = response.choices[0].message.content if response.choices else ""
        except Exception as e:
            return 0.0, f"Judge error: {e}"

        return self._parse_score(text)

    @staticmethod
    def _parse_score(text: str) -> tuple[float, str]:
        score = 0.0
        reasoning = text

        for line in text.split("\n"):
            line_lower = line.strip().lower()
            if line_lower.startswith("分数:") or line_lower.startswith("分数："):
                try:
                    score = float(line.split(":", 1)[1].split("：", 1)[-1].strip())
                    score = max(0.0, min(1.0, score))
                except (ValueError, IndexError):
                    pass
            elif line_lower.startswith("理由:") or line_lower.startswith("理由："):
                reasoning = line.split(":", 1)[-1].split("：", 1)[-1].strip()

        return score, reasoning


# ── AgentTargetExecutor ────────────────────────────────────────────────

class AgentTargetExecutor:
    """调用 AgentRuntime.run_turn 获取每个评估用例的实际输出。"""

    target_type = "agent"

    def __init__(self, agent_runtime: Any) -> None:
        self._runtime = agent_runtime

    async def execute(self, case: EvalCase, config: EvalRunConfig) -> str:
        from agent_runtime.contracts.models import (
            AgentTurnRequest,
            KnowledgeChunk,
        )

        agent_key = config.target_key
        if not agent_key:
            raise ValueError("target_key is required for agent target_type")

        knowledge_chunks = [
            KnowledgeChunk(
                content=chunk,
                source=f"case-{case.id}-ctx-{i}",
            )
            for i, chunk in enumerate(case.context or [])
        ]

        session_id = f"eval-{uuid.uuid4().hex[:12]}"
        trace_id = f"eval-trace-{uuid.uuid4().hex[:12]}"

        request = AgentTurnRequest(
            session_id=session_id,
            user_message=case.input_text,
            history=[],
            agent_key=agent_key,
            knowledge_chunks=knowledge_chunks,
            trace_id=trace_id,
        )

        result = await self._runtime.run_turn(request)

        if result.error is not None:
            return f"[ERROR] {result.error.code}: {result.error.message}"

        return result.reply_text


# ── RagTargetExecutor ──────────────────────────────────────────────────

class RagTargetExecutor:
    """调用检索 + 直接 LLM 生成获取每个评估用例的实际输出。"""

    target_type = "rag_pipeline"

    def __init__(self, retrieval_service: Any, gateway_service: Any) -> None:
        self._retrieval = retrieval_service
        self._gateway = gateway_service

    async def execute(self, case: EvalCase, config: EvalRunConfig) -> str:
        from llm_gateway.models import TextGenerateRequest

        kb_id = config.target_key
        if not kb_id:
            raise ValueError("target_key is required for rag_pipeline target_type")

        # 1. 检索上下文
        search_results = await self._retrieval.asearch(kb_id, case.input_text, top_k=5)
        context_text = "\n\n".join(r.text for r in search_results if r.text)

        # 2. 组装 prompt
        system_prompt = "你是一个知识库助手。请根据提供的上下文回答问题。如果上下文不包含答案，请如实说明。"
        user_prompt = f"上下文：\n{context_text}\n\n问题：{case.input_text}" if context_text else case.input_text

        # 3. 生成回答
        request = TextGenerateRequest(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1024,
            temperature=0.3,
        )
        response = await self._gateway.generate_text(request)
        return response.choices[0].message.content if response.choices else ""


# ── 工厂函数 ───────────────────────────────────────────────────────────

def create_target_executor(
    *,
    target_type: str,
    target_key: str,
    agent_runtime: Any = None,
    retrieval_service: Any = None,
    gateway_service: Any = None,
) -> TargetExecutor | None:
    """根据 run config 创建对应的 TargetExecutor。

    如果所需后端服务未就绪，返回 None，
    此时评估将回退到 expected_output 对比模式。
    """
    if not target_type or not target_key:
        return None

    if target_type == "agent":
        if agent_runtime is None:
            return None
        return AgentTargetExecutor(agent_runtime)

    if target_type == "rag_pipeline":
        if retrieval_service is None or gateway_service is None:
            return None
        return RagTargetExecutor(retrieval_service, gateway_service)

    return None
