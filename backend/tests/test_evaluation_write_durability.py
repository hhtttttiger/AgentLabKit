"""DF-03 regression: evaluation HTTP writes must be durable.

get_db never commits; evaluation services used to flush only, so every
write endpoint returned HTTP 200 and then silently rolled back when the
request session closed.  These tests run the real routes against a
throwaway PostgreSQL database and assert durability from independent
sessions that never shared the writing request session.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from common.dependencies import get_db
from modules.evaluation.models import EvalCase, EvalDataset, EvalRun, EvalRunConfig
from modules.evaluation.services.run_service import RunService

pytestmark = [pytest.mark.asyncio, pytest.mark.db]


@pytest.fixture
async def eval_client(db_session_factory, settings):
    """ASGI client whose request sessions come from the throwaway DB factory."""
    from httpx import ASGITransport, AsyncClient
    from common.auth import configure_auth
    from main import create_app

    configure_auth(settings)
    app = create_app(settings)

    async def _real_test_db():
        # Mirrors production get_db: the session closes without committing;
        # durability must come from the service layer.
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _real_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _fetch_one(db_session_factory, model, **filters):
    async with db_session_factory() as session:
        stmt = select(model).where(*[getattr(model, k) == v for k, v in filters.items()])
        return (await session.execute(stmt)).scalar_one_or_none()


async def test_dataset_create_and_delete_are_durable(eval_client, db_session_factory, auth_headers):
    resp = await eval_client.post(
        "/api/eval/datasets",
        json={"name": "durability", "description": "df03", "tags": ["t"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    dataset_id = int(resp.json()["data"]["id"])  # wire ids are strings (snowflake-safe JSON)

    row = await _fetch_one(db_session_factory, EvalDataset, id=dataset_id)
    assert row is not None, "HTTP 200 must imply a durable write"
    assert row.name == "durability"

    resp = await eval_client.delete(f"/api/eval/datasets/{dataset_id}", headers=auth_headers)
    assert resp.status_code == 200
    row = await _fetch_one(db_session_factory, EvalDataset, id=dataset_id)
    assert row is not None and row.is_active is False, "soft delete must be durable"


async def test_case_create_and_delete_are_durable(eval_client, db_session_factory, auth_headers):
    resp = await eval_client.post(
        "/api/eval/datasets",
        json={"name": "cases-durability"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    dataset_id = int(resp.json()["data"]["id"])  # wire ids are strings (snowflake-safe JSON)

    resp = await eval_client.post(
        f"/api/eval/datasets/{dataset_id}/cases",
        json=[{"input_text": "q1", "expected_output": "a1"}, {"input_text": "q2"}],
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["added"] == 2

    async with db_session_factory() as session:
        cases = (
            await session.execute(select(EvalCase).where(EvalCase.dataset_id == dataset_id))
        ).scalars().all()
        assert len(cases) == 2, "bulk case insert must survive session close"
        case_id = cases[0].id
        dataset_row = await session.get(EvalDataset, dataset_id)
        assert dataset_row.case_count == 2

    resp = await eval_client.delete(
        f"/api/eval/datasets/{dataset_id}/cases/{case_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    async with db_session_factory() as session:
        remaining = (
            await session.execute(select(EvalCase).where(EvalCase.dataset_id == dataset_id))
        ).scalars().all()
        assert len(remaining) == 1


async def test_run_config_create_is_durable(eval_client, db_session_factory, auth_headers):
    resp = await eval_client.post(
        "/api/eval/run-configs",
        json={
            "name": "cfg-durability",
            "datasetId": 1,
            "targetType": "rag_pipeline",
            "targetKey": "kb",
            "metricConfigs": [{"name": "faithfulness"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    config_id = int(resp.json()["data"]["id"])  # wire ids are strings (snowflake-safe JSON)

    row = await _fetch_one(db_session_factory, EvalRunConfig, id=config_id)
    assert row is not None, "run config must survive session close"
    assert row.name == "cfg-durability"


async def test_triggered_pending_run_is_durable_and_visible_to_a_new_session(
    db_session_factory,
):
    """The background executor re-selects the pending run in its own session."""
    async with db_session_factory() as session:
        svc = RunService(session)
        config = await svc.create_run_config(
            name="trigger-durability",
            dataset_id=1,
            target_type="rag_pipeline",
            target_key="kb",
            metric_configs_json=[],
            judge_model_key="",
        )
        config_id = config["id"]

    async with db_session_factory() as session:
        svc = RunService(session)
        run = await svc.trigger_run(config_id)
        assert run["status"] == "pending"

    # Independent session, as the scheduled background task would use.
    async with db_session_factory() as session:
        row = (
            await session.execute(select(EvalRun).where(EvalRun.id == run["id"]))
        ).scalar_one_or_none()
        assert row is not None, "pending run must be committed before the response returns"
        assert row.status == "pending"
