"""Evaluation framework for AgentLabKit."""

from .contracts import EvalCase, EvalMetricResult, EvalRunConfig, EvalRunResult, TargetExecutor
from .contracts_v2 import (
    DatasetExample,
    AgentRunSummary,
    SpanSummary,
    EvaluationContext,
    MetricScore,
    EvaluationResult,
    EvaluationRunStatus,
    EvaluationRun,
    Evaluator,
    eval_case_to_dataset_example,
    eval_run_result_to_evaluation_result,
)
from .evaluators import (
    RagasEvaluator,
    ToolCalledEvaluator,
    ToolNotCalledEvaluator,
    ToolArgsEvaluator,
    MaxStepsEvaluator,
    LatencyEvaluator,
    CostEvaluator,
    NoErrorEvaluator,
    TrajectoryEvaluator,
)
from .judge import Judge, JUDGE_SYSTEM_PROMPT
from .metrics.base import Metric, MetricResult
from .providers import EvalMetric, EvalProvider, ProviderRegistry
from .runner import EvaluationRunner
from .module import EvaluationModule, create_evaluation_module

__all__ = [
    "EvaluationModule",
    "create_evaluation_module",
    "EvaluationRunner",
    "EvalMetric",
    "EvalProvider",
    "Judge",
    "JUDGE_SYSTEM_PROMPT",
    "Metric",
    "MetricResult",
    "ProviderRegistry",
    "EvalCase",
    "EvalMetricResult",
    "EvalRunConfig",
    "EvalRunResult",
    "TargetExecutor",
    # v2
    "DatasetExample",
    "AgentRunSummary",
    "SpanSummary",
    "EvaluationContext",
    "MetricScore",
    "EvaluationResult",
    "EvaluationRunStatus",
    "EvaluationRun",
    "Evaluator",
    "RagasEvaluator",
    "ToolCalledEvaluator",
    "ToolNotCalledEvaluator",
    "ToolArgsEvaluator",
    "MaxStepsEvaluator",
    "LatencyEvaluator",
    "CostEvaluator",
    "NoErrorEvaluator",
    "TrajectoryEvaluator",
    "eval_case_to_dataset_example",
    "eval_run_result_to_evaluation_result",
]
