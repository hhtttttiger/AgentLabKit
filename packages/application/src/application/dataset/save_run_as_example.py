from __future__ import annotations

from ..ports.datasets import DatasetWriter
from ..ports.execution import RunReader
from .contracts import SaveRunAsDatasetExampleCommand, SaveRunAsDatasetExampleResult

class SaveRunAsDatasetExample:
    """Capture a real Run through Dataset's identity-owning capability."""
    def __init__(self, runs: RunReader, datasets: DatasetWriter) -> None:
        self._runs = runs
        self._datasets = datasets

    async def execute(self, command: SaveRunAsDatasetExampleCommand) -> SaveRunAsDatasetExampleResult:
        run = await self._runs.get_run(command.run_id)
        if run is None:
            raise LookupError(f"run {command.run_id} not found")
        example = await self._datasets.create_example_from_run(dataset_id=command.dataset_id, run=run)
        return SaveRunAsDatasetExampleResult(
            dataset_id=command.dataset_id,
            example_id=example.example_id,
            source_run_id=command.run_id,
        )
