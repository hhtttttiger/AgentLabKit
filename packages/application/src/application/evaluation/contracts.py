from dataclasses import dataclass, field
from typing import Mapping

@dataclass(frozen=True)
class EvaluateDatasetCommand:
    dataset_id: str
    agent_key: str
    metadata: Mapping[str, object] = field(default_factory=dict)

@dataclass(frozen=True)
class EvaluateDatasetResult:
    evaluation_run: object
