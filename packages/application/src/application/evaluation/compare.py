from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from evaluation.contracts_v2 import EvaluationResult
from ..ports.evaluation import EvaluationRunReader


@dataclass(frozen=True)
class CompareEvaluationRunsCommand:
    left_run_id: str
    right_run_id: str


@dataclass(frozen=True)
class EvaluationExampleComparison:
    example_id: str
    left: EvaluationResult | None
    right: EvaluationResult | None

    @property
    def classification(self) -> str:
        """A verdict-only transition; score and verdict remain separate."""
        if self.left is None or self.right is None:
            return "incomparable"
        if self.left.passed is None or self.right.passed is None:
            return "incomparable"
        if self.left.passed is False and self.right.passed is True:
            return "improved"
        if self.left.passed is True and self.right.passed is False:
            return "regressed"
        return "unchanged"


@dataclass(frozen=True)
class CompareEvaluationRunsResult:
    left_run_id: str
    right_run_id: str
    dataset_id: str
    examples: tuple[EvaluationExampleComparison, ...]

    @property
    def matched_count(self) -> int:
        return sum(e.left is not None and e.right is not None for e in self.examples)

    @property
    def left_only_count(self) -> int:
        return sum(e.left is not None and e.right is None for e in self.examples)

    @property
    def right_only_count(self) -> int:
        return sum(e.left is None and e.right is not None for e in self.examples)


class EvaluationRunNotFound(LookupError):
    pass


class EvaluationRunsNotComparable(ValueError):
    pass


class InvalidEvaluationResultSet(ValueError):
    pass


class CompareEvaluationRuns:
    """Compare persisted evaluation facts; never execute or evaluate again."""

    def __init__(self, evaluation_runs: EvaluationRunReader) -> None:
        self._evaluation_runs = evaluation_runs

    async def execute(self, command: CompareEvaluationRunsCommand) -> CompareEvaluationRunsResult:
        left = await self._evaluation_runs.get_run(command.left_run_id)
        if left is None:
            raise EvaluationRunNotFound(f"evaluation run {command.left_run_id} not found")
        right = await self._evaluation_runs.get_run(command.right_run_id)
        if right is None:
            raise EvaluationRunNotFound(f"evaluation run {command.right_run_id} not found")
        if left.dataset_id != right.dataset_id:
            raise EvaluationRunsNotComparable(
                f"evaluation runs use different datasets: {left.dataset_id!r} != {right.dataset_id!r}"
            )

        left_results = await self._evaluation_runs.list_results(command.left_run_id)
        right_results = await self._evaluation_runs.list_results(command.right_run_id)
        left_by_id = self._index(command.left_run_id, left_results)
        right_by_id = self._index(command.right_run_id, right_results)
        examples = tuple(
            EvaluationExampleComparison(example_id=example_id,
                                         left=left_by_id.get(example_id),
                                         right=right_by_id.get(example_id))
            for example_id in sorted(left_by_id.keys() | right_by_id.keys())
        )
        return CompareEvaluationRunsResult(
            left_run_id=command.left_run_id, right_run_id=command.right_run_id,
            dataset_id=left.dataset_id, examples=examples,
        )

    @staticmethod
    def _index(run_id: str, results: Sequence[EvaluationResult]) -> dict[str, EvaluationResult]:
        indexed: dict[str, EvaluationResult] = {}
        for result in results:
            if result.example_id in indexed:
                raise InvalidEvaluationResultSet(
                    f"evaluation run {run_id} contains duplicate example_id {result.example_id!r}"
                )
            indexed[result.example_id] = result
        return indexed
