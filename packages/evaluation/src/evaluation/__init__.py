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
from .cli import load_config, run_evaluation, check_threshold, compare_with_baseline, main, save_result
from .compare import ComparisonResult, ExampleDiff, ChangeType, compare_runs, format_comparison_report
from .dataset import DatasetManager, DatasetStore, InMemoryDatasetStore, DatasetEvaluationRunner
from .replay import ReplayConfig, ReplayResult, ReplayRunner, InMemoryRunStore, MockRunExecutor, RunStore, RunExecutor
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
    "DatasetManager",
    "DatasetStore",
    "InMemoryDatasetStore",
    "DatasetEvaluationRunner",
    "ComparisonResult",
    "ExampleDiff",
    "ChangeType",
    "compare_runs",
    "format_comparison_report",
    "RunStore",
    "RunExecutor",
    "ReplayConfig",
    "ReplayResult",
    "ReplayRunner",
    "InMemoryRunStore",
    "MockRunExecutor",
    # CLI
    "load_config",
    "run_evaluation",
    "check_threshold",
    "compare_with_baseline",
    "main",
    "save_result",
    # Evaluators
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
