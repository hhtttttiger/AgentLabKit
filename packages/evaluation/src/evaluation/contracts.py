from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class EvalCase:
    """单个评估用例。"""
    id: int = 0
    dataset_id: int = 0
    case_index: int = 0
    input_text: str = ""
    expected_output: str | None = None
    context: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class EvalMetricResult:
    """单个指标的评估结果。"""
    metric_name: str
    score: float = 0.0        # 0.0 - 1.0
    reasoning: str | None = None
    passed: bool | None = None


@dataclass(slots=True)
class EvalRunConfig:
    """评估运行配置。"""
    id: int = 0
    name: str = ""
    dataset_id: int = 0
    target_type: str = "agent"   # agent / rag_pipeline
    target_key: str = ""
    metric_configs: list[dict[str, Any]] = field(default_factory=list)
    judge_model_key: str = ""


@dataclass(slots=True)
class EvalRunResult:
    """单个用例的运行结果。"""
    id: int = 0
    run_id: int = 0
    case_id: int = 0
    actual_output: str = ""
    metric_results: list[EvalMetricResult] = field(default_factory=list)
    overall_score: float = 0.0
    error_message: str | None = None
    duration_ms: int = 0


@runtime_checkable
class TargetExecutor(Protocol):
    """协议：评估目标执行器。

    具体实现（Agent / RAG Pipeline）由后端适配器提供。
    评估包本身不依赖 agent_runtime 或 llm_gateway。
    """

    target_type: str  # "agent" | "rag_pipeline"

    async def execute(self, case: EvalCase, config: EvalRunConfig) -> str:
        """执行目标并返回实际输出字符串。"""
        ...
