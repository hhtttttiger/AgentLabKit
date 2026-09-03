from dataclasses import dataclass

import pytest

from application import (
    CompareEvaluationRuns, CompareEvaluationRunsCommand, EvaluationRunNotFound,
    EvaluationRunsNotComparable, InvalidEvaluationResultSet,
)
from evaluation.contracts_v2 import EvaluationResult


@dataclass
class Run:
    run_id: str
    dataset_id: str


class Reader:
    def __init__(self, runs, results):
        self.runs, self.results = runs, results
        self.listed = []

    async def get_run(self, run_id):
        return self.runs.get(run_id)

    async def list_results(self, run_id):
        self.listed.append(run_id)
        return self.results.get(run_id, [])


def result(example_id, *, score=None, passed=None):
    return EvaluationResult(example_id=example_id, score=score, passed=passed)


@pytest.mark.asyncio
async def test_compare_pairs_by_example_id_and_keeps_deterministic_partial_union():
    reader = Reader(
        {"a": Run("a", "dataset"), "b": Run("b", "dataset")},
        {"a": [result("C", score=0.0), result("A", passed=True)],
         "b": [result("D"), result("C", score=1.0), result("B")]},
    )
    compared = await CompareEvaluationRuns(reader).execute(
        CompareEvaluationRunsCommand("a", "b")
    )
    assert [x.example_id for x in compared.examples] == ["A", "B", "C", "D"]
    assert compared.examples[0].left.passed is True
    assert compared.examples[1].left is None
    assert compared.examples[2].left.score == 0.0
    assert compared.matched_count == 1
    assert compared.left_only_count == 1
    assert compared.right_only_count == 2


@pytest.mark.asyncio
async def test_compare_rejects_missing_runs_and_different_datasets():
    reader = Reader({"a": Run("a", "one")}, {})
    with pytest.raises(EvaluationRunNotFound):
        await CompareEvaluationRuns(reader).execute(CompareEvaluationRunsCommand("x", "a"))
    with pytest.raises(EvaluationRunNotFound):
        await CompareEvaluationRuns(reader).execute(CompareEvaluationRunsCommand("a", "x"))
    reader.runs["b"] = Run("b", "two")
    with pytest.raises(EvaluationRunsNotComparable):
        await CompareEvaluationRuns(reader).execute(CompareEvaluationRunsCommand("a", "b"))


@pytest.mark.asyncio
async def test_compare_rejects_duplicate_example_and_preserves_tri_state_verdicts():
    reader = Reader(
        {"a": Run("a", "d"), "b": Run("b", "d")},
        {"a": [result("x"), result("x")], "b": []},
    )
    with pytest.raises(InvalidEvaluationResultSet):
        await CompareEvaluationRuns(reader).execute(CompareEvaluationRunsCommand("a", "b"))

    reader.results["a"] = [result("x", passed=None)]
    reader.results["b"] = [result("x", passed=False)]
    compared = await CompareEvaluationRuns(reader).execute(
        CompareEvaluationRunsCommand("a", "b")
    )
    assert compared.examples[0].classification == "incomparable"
