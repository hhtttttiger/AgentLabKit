"""DF-04 regression: evaluation identities are opaque strings on the wire.

Snowflake ids exceed Number.MAX_SAFE_INTEGER (2**53); any id that round-trips
as a JSON number loses precision in the browser. Tests seed rows with real
>2^53 ids and verify the full HTTP round-trip: list/detail responses carry
exact string ids, camelCase contract keys, and string request bodies land on
the exact bigint rows. Also pins tri-state passed (null preserved) and
score=0.0 (not coerced to null or nonzero).
"""
from __future__ import annotations

import pytest

from common.dependencies import get_db
from modules.evaluation.models import EvalCase, EvalDataset, EvalRun, EvalRunConfig, EvalRunResult

pytestmark = [pytest.mark.asyncio, pytest.mark.db]

# Real snowflake-magnitude ids: strictly above 2**53 and pairwise distinct,
# so any precision loss or key mismatch changes the asserted string.
BIG_DATASET_ID = 9007199254740993   # 2**53 + 1
BIG_CASE_ID = 9007199254740995      # 2**53 + 3
BIG_CONFIG_ID = 9007199254740997    # 2**53 + 5
BIG_RUN_ID = 9007199254740999       # 2**53 + 7
BIG_RESULT_ID = 9007199254741001    # 2**53 + 9


@pytest.fixture
async def seeded(db_session_factory):
    async with db_session_factory() as session:
        session.add(EvalDataset(id=BIG_DATASET_ID, name="big-id-dataset", case_count=1))
        session.add(EvalCase(
            id=BIG_CASE_ID, dataset_id=BIG_DATASET_ID, case_index=0,
            input_text="q", expected_output="a",
        ))
        session.add(EvalRunConfig(
            id=BIG_CONFIG_ID, name="big-id-config", dataset_id=BIG_DATASET_ID,
            target_type="rag_pipeline", target_key="kb",
        ))
        session.add(EvalRun(id=BIG_RUN_ID, config_id=BIG_CONFIG_ID, status="completed"))
        session.add(EvalRunResult(
            id=BIG_RESULT_ID, run_id=BIG_RUN_ID, case_id=BIG_CASE_ID,
            actual_output="out",
            metric_results_json=[
                {"metric_name": "faithfulness", "score": 0.0, "passed": None},
                {"metric_name": "context_precision", "score": 1.0, "passed": True},
                {
                    "metric_name": "answer_relevancy", "score": None, "passed": None,
                    "reason": "missing_reference",
                    "evidence": {
                        "availability": "not_applicable", "attempts": 0,
                        "successful_attempts": 0, "contexts_used": 0,
                        "reason": None,
                    },
                },
            ],
            overall_score=0.0,
            passed=None,
            candidate_run_id="candidate-run-hex",
            candidate_trace_id="candidate-trace-hex",
        ))
        await session.commit()


@pytest.fixture
async def eval_client(db_session_factory, settings):
    from httpx import ASGITransport, AsyncClient
    from common.auth import configure_auth
    from main import create_app

    configure_auth(settings)
    app = create_app(settings)

    async def _real_test_db():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _real_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_dataset_and_case_ids_round_trip_as_exact_strings(eval_client, seeded, auth_headers):
    resp = await eval_client.get("/api/eval/datasets", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    target = next(d for d in items if d["id"] == str(BIG_DATASET_ID))
    # Wire keys follow the frontend camelCase contract; ids are strings.
    assert isinstance(target["id"], str)
    assert target["caseCount"] == 1

    resp = await eval_client.get(f"/api/eval/datasets/{BIG_DATASET_ID}/cases", headers=auth_headers)
    assert resp.status_code == 200
    case = resp.json()["data"][0]
    assert case["id"] == str(BIG_CASE_ID)
    assert case["datasetId"] == str(BIG_DATASET_ID)
    assert case["inputText"] == "q"


async def test_run_config_accepts_string_dataset_id_and_returns_exact_string(
    eval_client, seeded, auth_headers
):
    resp = await eval_client.post(
        "/api/eval/run-configs",
        json={
            "name": "wire-config",
            "datasetId": str(BIG_DATASET_ID),  # string body, as the frontend sends
            "targetType": "rag_pipeline",
            "targetKey": "kb",
            "metricConfigs": [{"name": "faithfulness"}],
            "judgeModelKey": "judge-key",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data["id"], str)
    assert data["datasetId"] == str(BIG_DATASET_ID), "bigint must survive str->int->str exactly"
    assert data["judgeModelKey"] == "judge-key"

    # The created config targets the exact bigint row, not a precision-mangled one.
    resp = await eval_client.get("/api/eval/run-configs", headers=auth_headers)
    assert any(
        c["datasetId"] == str(BIG_DATASET_ID) for c in resp.json()["data"]
    )


async def test_run_detail_preserves_config_link_and_tri_state_fields(
    eval_client, seeded, auth_headers
):
    resp = await eval_client.get(f"/api/eval/runs/{BIG_RUN_ID}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    # configId is present as a string — the field the "Run Again" button uses
    # to build /run-configs/{id}/run; snake_case output made it undefined.
    assert data["run"]["configId"] == str(BIG_CONFIG_ID)

    result = data["results"][0]
    assert result["caseId"] == str(BIG_CASE_ID)
    assert result["metricResults"][0]["metricName"] == "faithfulness"
    assert result["metricResults"][0]["score"] == 0.0
    assert result["metricResults"][0]["passed"] is None, "unavailable verdict stays null"
    assert result["metricResults"][1]["passed"] is True
    assert result["overallScore"] == 0.0
    assert result["passed"] is None


async def test_run_result_round_trips_candidate_identity_and_metric_reason(
    eval_client, seeded, auth_headers
):
    """Candidate execution identity and per-metric evidence/reason survive the
    wire intact — the surface Open Run / Inspect Trace and the evidence drawer
    are built on."""
    resp = await eval_client.get(f"/api/eval/runs/{BIG_RUN_ID}", headers=auth_headers)
    assert resp.status_code == 200
    result = resp.json()["data"]["results"][0]

    # Runtime-owned candidate identity, opaque strings on the wire.
    assert result["candidateRunId"] == "candidate-run-hex"
    assert result["candidateTraceId"] == "candidate-trace-hex"

    # Tri-state entries without reason/evidence stay clean.
    plain = result["metricResults"][0]
    assert plain["reason"] is None
    assert plain["evidence"] is None

    # Gated entry carries the machine-readable reason and bounded evidence.
    gated = result["metricResults"][2]
    assert gated["score"] is None
    assert gated["reason"] == "missing_reference"
    assert gated["evidence"] == {
        "availability": "not_applicable",
        "attempts": 0,
        "successfulAttempts": 0,
        "contextsUsed": 0,
        "reason": None,
    }
