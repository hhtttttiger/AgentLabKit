from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from evaluation.contracts_v2 import DatasetExample


@dataclass(frozen=True, slots=True)
class CaptureRunAsDatasetExampleCommand:
    dataset_id: str
    run_id: str
    metadata: Mapping[str, Any] | None = None
    expected_output: Any | None = None


@dataclass(frozen=True, slots=True)
class CaptureRunAsDatasetExampleResult:
    dataset_id: str
    source_run_id: str
    example: DatasetExample

    @property
    def example_id(self) -> str:
        """Compatibility projection for the scaffold result shape."""
        return self.example.example_id


# Compatibility aliases for the pre-production scaffold.
SaveRunAsDatasetExampleCommand = CaptureRunAsDatasetExampleCommand
SaveRunAsDatasetExampleResult = CaptureRunAsDatasetExampleResult
