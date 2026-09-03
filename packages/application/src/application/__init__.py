"""Framework-neutral application use cases."""

from .execution.contracts import ExecuteAgentCommand, ExecuteAgentResult, ExecuteAgentUpdate, ReplayRunCommand, ReplayRunResult
from .execution.execute_agent import ExecuteAgent
from .execution.replay_run import (
    ReplayInputUnavailable,
    ReplayRun,
    ReplayRunError,
    ReplaySourceNotFound,
    ReplayTargetUnavailable,
    ReplayTargetUnsupported,
)
from .dataset import (
    CaptureRunAsDatasetExample,
    CaptureRunAsDatasetExampleCommand,
    CaptureRunAsDatasetExampleResult,
    CaptureSourceRunNotFound,
    RunNotCapturable,
    SaveRunAsDatasetExample,
    SaveRunAsDatasetExampleCommand,
    SaveRunAsDatasetExampleResult,
)
from .evaluation.contracts import EvaluationConfiguration, EvaluateDatasetCommand, EvaluateDatasetResult
from .evaluation.evaluate_dataset import EvaluateDataset
from .evaluation.compare import (
    CompareEvaluationRuns, CompareEvaluationRunsCommand, CompareEvaluationRunsResult,
    EvaluationExampleComparison, EvaluationRunNotFound, EvaluationRunsNotComparable,
    InvalidEvaluationResultSet,
)

__all__ = [
    "ExecuteAgent", "ExecuteAgentCommand", "ExecuteAgentResult", "ExecuteAgentUpdate",
    "ReplayRun", "ReplayRunCommand", "ReplayRunResult", "ReplayRunError",
    "ReplaySourceNotFound", "ReplayTargetUnavailable", "ReplayTargetUnsupported",
    "ReplayInputUnavailable",
    "CaptureRunAsDatasetExample", "CaptureRunAsDatasetExampleCommand", "CaptureRunAsDatasetExampleResult",
    "CaptureSourceRunNotFound", "RunNotCapturable",
    "SaveRunAsDatasetExample", "SaveRunAsDatasetExampleCommand", "SaveRunAsDatasetExampleResult",
    "EvaluateDataset", "EvaluationConfiguration", "EvaluateDatasetCommand", "EvaluateDatasetResult",
    "CompareEvaluationRuns", "CompareEvaluationRunsCommand", "CompareEvaluationRunsResult",
    "EvaluationExampleComparison", "EvaluationRunNotFound", "EvaluationRunsNotComparable",
    "InvalidEvaluationResultSet",
]
