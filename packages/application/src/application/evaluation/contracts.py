from dataclasses import dataclass, field
from typing import Mapping

@dataclass(frozen=True)
class EvaluationConfiguration:
    """Framework-neutral snapshot of a persisted evaluation configuration."""
    config_id: str
    dataset_id: str
    target_type: str
    target_key: str
    metric_configs: tuple[Mapping[str, object], ...] = ()
    judge_model_key: str = ""

@dataclass(frozen=True)
class EvaluateDatasetCommand:
    # Prefer evaluation_config_id for persisted runs. The legacy fields remain
    # usable for CLI/in-memory callers and are resolved only when no snapshot is supplied.
    dataset_id: str | None = None
    agent_key: str | None = None
    evaluation_config_id: str | None = None
    configuration: EvaluationConfiguration | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

@dataclass(frozen=True)
class EvaluateDatasetResult:
    evaluation_run: object
