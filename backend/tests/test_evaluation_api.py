from __future__ import annotations

import pytest

from application import CompareEvaluationRuns
from evaluation.contracts_v2 import EvaluationResult, EvaluationRun
from modules.evaluation.dependencies import get_compare_evaluation_runs


class FakeEvaluationRunReader:
    def __init__(self, runs, results):
        self.runs = runs
        self.results = results

    async def get_run(self, run_id):
        return self.runs.get(run_id)

    async def list_results(self, run_id):
        return self.results.get(run_id, [])


def evaluation_run(run_id: str, dataset_id: str = "dataset-1") -> EvaluationRun:
    return EvaluationRun(run_id=run_id, dataset_id=dataset_id, agent_key="agent")


def result(example_id: str, *, passed=None, score=None) -> EvaluationResult:
    return EvaluationResult(example_id=example_id, passed=passed, score=score)


@pytest.mark.asyncio
async def test_compare_public_contract_pairs_by_example_id_and_preserves_partial_sets(
    app, client, auth_headers,
):
    reader = FakeEvaluationRunReader(
        {"left": evaluation_run("left"), "right": evaluation_run("right")},
        {
            # Deliberately different order: the API must follow example identity.
            "left": [result("B", passed=False, score=0.0), result("A", passed=True, score=0.0), result("C", passed=None, score=0.0)],
            "right": [result("D", passed=True, score=0.0), result("C", passed=None, score=0.0), result("B", passed=True, score=0.0)],
        },
    )
    compare = CompareEvaluationRuns(reader)
    app.dependency_overrides[get_compare_evaluation_runs] = lambda: compare
    try:
        response = await client.post(
            "/api/eval/runs/compare",
            json={"leftRunId": "left", "rightRunId": "right"},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_compare_evaluation_runs, None)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["leftRunId"] == "left"
    assert data["rightRunId"] == "right"
    assert data["datasetId"] == "dataset-1"
    assert data["matchedCount"] == 2
    assert data["leftOnlyCount"] == 1
    assert data["rightOnlyCount"] == 1
    assert [item["exampleId"] for item in data["examples"]] == ["A", "B", "C", "D"]
    by_id = {item["exampleId"]: item for item in data["examples"]}
    assert by_id["A"]["classification"] == "incomparable"
    assert by_id["A"]["right"] is None
    assert by_id["B"]["classification"] == "improved"
    assert by_id["B"]["left"]["passed"] is False
    assert by_id["B"]["right"]["passed"] is True
    assert by_id["C"]["left"]["passed"] is None
    assert by_id["C"]["right"]["passed"] is None
    assert by_id["C"]["left"]["score"] == 0.0
    assert by_id["D"]["left"] is None


@pytest.mark.asyncio
async def test_compare_requires_authentication(client):
    response = await client.post(
        "/api/eval/runs/compare",
        json={"leftRunId": "left", "rightRunId": "right"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_id", ["left", "right"])
async def test_compare_missing_evaluation_run_is_not_found(app, client, auth_headers, missing_id):
    runs = {"left": evaluation_run("left"), "right": evaluation_run("right")}
    runs.pop(missing_id)
    compare = CompareEvaluationRuns(FakeEvaluationRunReader(runs, {}))
    app.dependency_overrides[get_compare_evaluation_runs] = lambda: compare
    try:
        response = await client.post(
            "/api/eval/runs/compare",
            json={"leftRunId": "left", "rightRunId": "right"},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_compare_evaluation_runs, None)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_compare_different_datasets_and_duplicate_examples_are_client_errors(
    app, client, auth_headers,
):
    cases = [
        (
            {"left": evaluation_run("left", "dataset-a"), "right": evaluation_run("right", "dataset-b")},
            {"left": [], "right": []},
        ),
        (
            {"left": evaluation_run("left"), "right": evaluation_run("right")},
            {"left": [result("A"), result("A")], "right": []},
        ),
    ]
    for runs, results in cases:
        compare = CompareEvaluationRuns(FakeEvaluationRunReader(runs, results))
        app.dependency_overrides[get_compare_evaluation_runs] = lambda: compare
        try:
            response = await client.post(
                "/api/eval/runs/compare",
                json={"leftRunId": "left", "rightRunId": "right"},
                headers=auth_headers,
            )
        finally:
            app.dependency_overrides.pop(get_compare_evaluation_runs, None)
        assert response.status_code == 422
        assert response.json()["success"] is False
