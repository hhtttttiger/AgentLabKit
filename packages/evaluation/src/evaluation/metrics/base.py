"""Metric Protocol + MetricResult。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..contracts import EvalMetricResult


@dataclass(slots=True)
class MetricResult:
    metric_name: str
    score: float
    reasoning: str | None = None
    passed: bool | None = None


@runtime_checkable
class Metric(Protocol):
    name: str
    async def evaluate(
        self,
        *,
        input_text: str,
        actual_output: str,
        expected_output: str | None = None,
        context: list[str] | None = None,
        judge: Any | None = None,
    ) -> EvalMetricResult: ...


# ── 内置指标实现 ────────────────────────────────────────────────────


class AnswerRelevanceMetric:
    """答案相关性 — 输入与输出的语义相关性。"""
    name = "answer_relevance"

    async def evaluate(
        self,
        *,
        input_text: str,
        actual_output: str,
        expected_output: str | None = None,
        context: list[str] | None = None,
        judge: Any | None = None,
    ) -> EvalMetricResult:
        if not actual_output.strip():
            return EvalMetricResult(metric_name=self.name, score=0.0, reasoning="Empty output")
        if judge is None:
            return EvalMetricResult(metric_name=self.name, score=0.5, reasoning="No judge available")

        rubric = (
            "评估回答与问题的相关性。评分标准：\n"
            "- 1.0: 回答完全针对问题，内容准确且完整\n"
            "- 0.7: 回答基本相关，但可能缺少部分信息\n"
            "- 0.4: 回答与问题部分相关，但有明显偏离\n"
            "- 0.0: 回答与问题无关"
        )
        prompt = f"问题: {input_text}\n回答: {actual_output}"
        score, reasoning = await judge.score(prompt=prompt, rubric=rubric)
        return EvalMetricResult(metric_name=self.name, score=score, reasoning=reasoning)


class FaithfulnessMetric:
    """忠实度 — 输出是否忠于上下文。"""
    name = "faithfulness"

    async def evaluate(
        self,
        *,
        input_text: str,
        actual_output: str,
        expected_output: str | None = None,
        context: list[str] | None = None,
        judge: Any | None = None,
    ) -> EvalMetricResult:
        if not context:
            return EvalMetricResult(metric_name=self.name, score=1.0, reasoning="No context to verify against")
        if judge is None:
            return EvalMetricResult(metric_name=self.name, score=0.5, reasoning="No judge available")

        context_text = "\n".join(context)
        rubric = (
            "评估回答是否忠实于提供的参考上下文。评分标准：\n"
            "- 1.0: 所有声明都可以从上下文中找到依据\n"
            "- 0.5: 部分声明无法从上下文中验证\n"
            "- 0.0: 回答包含上下文中没有的信息（幻觉）"
        )
        prompt = f"参考上下文:\n{context_text}\n\n回答: {actual_output}"
        score, reasoning = await judge.score(prompt=prompt, rubric=rubric)
        return EvalMetricResult(metric_name=self.name, score=score, reasoning=reasoning)


class ContextRelevanceMetric:
    """上下文相关性 — RAG 检索的上下文与问题的相关性。"""
    name = "context_relevance"

    async def evaluate(
        self,
        *,
        input_text: str,
        actual_output: str,
        expected_output: str | None = None,
        context: list[str] | None = None,
        judge: Any | None = None,
    ) -> EvalMetricResult:
        if not context:
            return EvalMetricResult(metric_name=self.name, score=0.0, reasoning="No context provided")
        if judge is None:
            return EvalMetricResult(metric_name=self.name, score=0.5, reasoning="No judge available")

        context_text = "\n".join(context)
        rubric = (
            "评估检索到的上下文与问题的相关性。评分标准：\n"
            "- 1.0: 上下文完全针对问题，信息密度高\n"
            "- 0.5: 上下文部分相关，但包含冗余信息\n"
            "- 0.0: 上下文与问题无关"
        )
        prompt = f"问题: {input_text}\n检索到的上下文:\n{context_text}"
        score, reasoning = await judge.score(prompt=prompt, rubric=rubric)
        return EvalMetricResult(metric_name=self.name, score=score, reasoning=reasoning)
