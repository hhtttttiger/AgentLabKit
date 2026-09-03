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
from .dataset.contracts import SaveRunAsDatasetExampleCommand, SaveRunAsDatasetExampleResult
from .dataset.save_run_as_example import SaveRunAsDatasetExample
from .evaluation.contracts import EvaluationConfiguration, EvaluateDatasetCommand, EvaluateDatasetResult
from .evaluation.evaluate_dataset import EvaluateDataset

__all__ = [
    "ExecuteAgent", "ExecuteAgentCommand", "ExecuteAgentResult", "ExecuteAgentUpdate",
    "ReplayRun", "ReplayRunCommand", "ReplayRunResult", "ReplayRunError",
    "ReplaySourceNotFound", "ReplayTargetUnavailable", "ReplayTargetUnsupported",
    "ReplayInputUnavailable",
    "SaveRunAsDatasetExample", "SaveRunAsDatasetExampleCommand", "SaveRunAsDatasetExampleResult",
    "EvaluateDataset", "EvaluationConfiguration", "EvaluateDatasetCommand", "EvaluateDatasetResult",
]
