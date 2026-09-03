from __future__ import annotations

from ..ports.datasets import DatasetExampleWriter
from ..ports.execution import RunReader
from .contracts import (
    CaptureRunAsDatasetExampleCommand,
    CaptureRunAsDatasetExampleResult,
)


class CaptureSourceRunNotFound(LookupError):
    """The requested durable source Run does not exist."""


class RunNotCapturable(ValueError):
    """The source Run has not reached a capturable terminal state."""


class CaptureRunAsDatasetExample:
    """Capture a completed durable Run as a new Dataset-owned example.

    This use case only composes the Run read capability and Dataset write
    capability.  It neither reconstructs execution from Trace/Audit nor
    starts Runtime or Evaluation.
    """

    def __init__(self, runs: RunReader, datasets: DatasetExampleWriter) -> None:
        self._runs = runs
        self._datasets = datasets

    async def execute(
        self, command: CaptureRunAsDatasetExampleCommand,
    ) -> CaptureRunAsDatasetExampleResult:
        run = await self._runs.get_run(command.run_id)
        if run is None:
            raise CaptureSourceRunNotFound(f"run {command.run_id} not found")
        if run.status != "completed":
            raise RunNotCapturable(
                f"run {command.run_id} has status {run.status!r}; only completed runs can be captured"
            )

        # Caller metadata is deliberately lower precedence than authoritative
        # provenance.  Arbitrary Run metadata is never copied.
        provenance = dict(command.metadata or {})
        provenance.update({
            "source_run_id": run.run_id,
            "source_trace_id": run.trace_id,
        })
        for name, key in (
            ("target_type", "source_target_type"),
            ("target_key", "source_target_key"),
            ("target_version", "source_target_version"),
        ):
            value = getattr(run, name, None)
            if value is not None:
                provenance[key] = value

        example = await self._datasets.create_example(
            dataset_id=command.dataset_id,
            input_text=run.input,
            # A Run output is an actual result, not a golden answer.  Only an
            # explicit command value becomes expected_output.
            expected_output=command.expected_output,
            metadata=provenance,
            source_run_id=run.run_id,
            source_trace_id=run.trace_id,
        )
        return CaptureRunAsDatasetExampleResult(
            dataset_id=command.dataset_id,
            source_run_id=run.run_id,
            example=example,
        )


class SaveRunAsDatasetExample:
    """Deprecated scaffold adapter retained for import compatibility only."""

    def __init__(self, runs: RunReader, datasets) -> None:
        self._runs = runs
        self._datasets = datasets

    async def execute(self, command):
        run = await self._runs.get_run(command.run_id)
        if run is None:
            raise LookupError(f"run {command.run_id} not found")
        example = await self._datasets.create_example_from_run(
            dataset_id=command.dataset_id, run=run,
        )
        return CaptureRunAsDatasetExampleResult(
            dataset_id=command.dataset_id,
            source_run_id=command.run_id,
            example=example,
        )
