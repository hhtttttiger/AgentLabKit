"""中文评估 Metric — 基于 RAGAS DiscreteMetric / RubricsScore。

提供 faithfulness、answer_relevancy、context_relevance 的中文 rubric 版本，
用于中文问答场景下的 LLM-as-Judge 评估。

依赖：pip install agentlabkit-evaluation[ragas]
"""

from __future__ import annotations

from typing import Any

try:
    from ragas.metrics import DiscreteMetric, RubricsScore
except ImportError:
    DiscreteMetric = None  # type: ignore[assignment,misc]
    RubricsScore = None  # type: ignore[assignment,misc]


def _check_ragas():
    """检查 RAGAS 是否已安装。"""
    if DiscreteMetric is None:
        raise ImportError(
            "RAGAS metrics require the 'ragas' package. "
            "Install with: pip install agentlabkit-evaluation[ragas]"
        )


def create_faithfulness_cn(llm: Any | None = None) -> Any:
    """中文忠实度指标（离散值: faithful / partial / unfaithful）。

    评估回答是否忠实于给定的上下文。
    """
    _check_ragas()

    return DiscreteMetric(
        name="faithfulness_cn",
        prompt=(
            "请评估以下回答是否忠实于给定的上下文。\n\n"
            "上下文：{context}\n"
            "回答：{answer}\n\n"
            "请返回以下三个等级之一：\n"
            "- faithful: 回答完全基于上下文，所有声明都有依据\n"
            "- partial: 回答部分基于上下文，但包含一些推测或未验证的内容\n"
            "- unfaithful: 回答包含上下文中没有的信息（幻觉）"
        ),
        allowed_values=["faithful", "partial", "unfaithful"],
        llm=llm,
    )


def create_answer_relevancy_cn(llm: Any | None = None) -> Any:
    """中文答案相关性指标（数值评分 0-1）。

    评估回答与问题的相关性和完整性。
    """
    _check_ragas()

    return RubricsScore(
        name="answer_relevancy_cn",
        rubrics={
            "1.0": "回答与问题高度相关，完全解答了问题",
            "0.75": "回答与问题大部分相关，基本解答了问题",
            "0.5": "回答与问题部分相关，但有明显遗漏",
            "0.25": "回答与问题关联度低，未有效解答",
            "0.0": "回答与问题无关",
        },
        llm=llm,
    )


def create_context_relevance_cn(llm: Any | None = None) -> Any:
    """中文上下文相关性指标（离散值: relevant / partial / irrelevant）。

    评估 RAG 检索到的上下文与问题的相关性。
    """
    _check_ragas()

    return DiscreteMetric(
        name="context_relevance_cn",
        prompt=(
            "请评估以下检索到的上下文与问题的相关性。\n\n"
            "问题：{question}\n"
            "检索到的上下文：{context}\n\n"
            "请返回以下三个等级之一：\n"
            "- relevant: 上下文完全针对问题，信息密度高，能有效回答问题\n"
            "- partial: 上下文部分相关，包含一些有用信息但也有很多冗余\n"
            "- irrelevant: 上下文与问题无关，无法帮助回答问题"
        ),
        allowed_values=["relevant", "partial", "irrelevant"],
        llm=llm,
    )


# ── 全部中文 metric 一次性创建 ────────────────────────────────────────


def create_all_cn_metrics(llm: Any | None = None) -> dict[str, Any]:
    """创建全部中文 metric，返回 {name: metric} 映射。"""
    return {
        "faithfulness_cn": create_faithfulness_cn(llm),
        "answer_relevancy_cn": create_answer_relevancy_cn(llm),
        "context_relevance_cn": create_context_relevance_cn(llm),
    }
