"""Run config management and run orchestration."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import NotFoundError
from ..models import EvalRunConfig, EvalRun, EvalRunResult, EvalCase


class RunService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_run_configs(self) -> list[dict]:
        result = await self._db.execute(select(EvalRunConfig).order_by(EvalRunConfig.id.desc()))
        return [self._to_run_config_view(c) for c in result.scalars().all()]

    async def create_run_config(self, **kwargs) -> dict:
        config = EvalRunConfig(**kwargs)
        self._db.add(config)
        await self._db.flush()
        await self._db.refresh(config)
        return self._to_run_config_view(config)

    async def trigger_run(self, config_id: int) -> dict:
        result = await self._db.execute(select(EvalRunConfig).where(EvalRunConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("RunConfig", str(config_id))

        run = EvalRun(config_id=config_id, status="pending")
        self._db.add(run)
        await self._db.flush()
        await self._db.refresh(run)
        return self._to_run_view(run)

    async def trigger_run_and_execute(
        self,
        config_id: int,
        eval_mod,
        background_tasks,
        request_app_state,
    ) -> dict:
        """Trigger a run and schedule its execution via background tasks.

        Encapsulates the full orchestration: create the run record,
        resolve the TargetExecutor from runtime services, and schedule
        execute_run as a background task.
        """
        run = await self.trigger_run(config_id)

        from ..adapters import create_target_executor

        run_configs = await self.list_run_configs()
        config = next(
            (c for c in run_configs if str(c["id"]) == str(config_id)), None
        )

        target_executor = None
        if config:
            target_executor = create_target_executor(
                target_type=config["target_type"],
                target_key=config["target_key"],
                agent_runtime=getattr(request_app_state, "agent_runtime", None),
                retrieval_service=getattr(request_app_state, "retrieval_service", None),
                gateway_service=getattr(request_app_state, "gateway_service", None),
            )

        background_tasks.add_task(
            self.execute_run, run["id"], config_id, eval_mod, target_executor
        )
        return run

    async def list_runs(self, *, limit: int) -> list[dict]:
        result = await self._db.execute(select(EvalRun).order_by(EvalRun.id.desc()).limit(limit))
        return [self._to_run_view(r) for r in result.scalars().all()]

    async def get_run_detail(self, run_id: int) -> dict:
        result = await self._db.execute(select(EvalRun).where(EvalRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            raise NotFoundError("Run", str(run_id))

        r_result = await self._db.execute(select(EvalRunResult).where(EvalRunResult.run_id == run_id))
        results = r_result.scalars().all()

        return {
            "run": self._to_run_view(run),
            "results": [self._to_run_result_view(r) for r in results],
        }

    @staticmethod
    async def execute_run(run_id: int, config_id: int, eval_mod, target_executor=None) -> None:
        """Background task: execute an evaluation run."""
        from alkit_db.engine import get_session_factory
        session_factory = get_session_factory()

        async with session_factory() as session:
            run_result = await session.execute(select(EvalRun).where(EvalRun.id == run_id))
            run = run_result.scalar_one_or_none()
            if not run:
                return

            config_result = await session.execute(select(EvalRunConfig).where(EvalRunConfig.id == config_id))
            config_orm = config_result.scalar_one_or_none()
            if not config_orm:
                run.status = "failed"
                run.summary_json = {"error": "Config not found"}
                await session.commit()
                return

            cases_result = await session.execute(
                select(EvalCase).where(EvalCase.dataset_id == config_orm.dataset_id).order_by(EvalCase.case_index)
            )
            cases_orm = cases_result.scalars().all()

            run.status = "running"
            run.started_at_utc = func.now()
            await session.commit()

            from evaluation.contracts import EvalCase as EvalCaseContract, EvalRunConfig as EvalRunConfigContract
            eval_cases = [
                EvalCaseContract(
                    id=c.id, dataset_id=c.dataset_id, case_index=c.case_index,
                    input_text=c.input_text, expected_output=c.expected_output,
                    context=c.context_json or [],
                )
                for c in cases_orm
            ]
            eval_config = EvalRunConfigContract(
                id=config_orm.id, name=config_orm.name, dataset_id=config_orm.dataset_id,
                target_type=config_orm.target_type, target_key=config_orm.target_key,
                metric_configs=config_orm.metric_configs_json or [],
                judge_model_key=config_orm.judge_model_key,
            )

            try:
                results = await eval_mod.runner.run_batch(
                    eval_cases, eval_config, target_executor=target_executor,
                )
            except Exception as exc:
                run.status = "failed"
                run.completed_at_utc = func.now()
                run.summary_json = {"error": f"Evaluation failed: {exc}"}
                await session.commit()
                return

            scores = []
            for r in results:
                scores.append(r.overall_score)
                orm_result = EvalRunResult(
                    run_id=run_id, case_id=r.case_id,
                    actual_output=r.actual_output,
                    metric_results_json=[{
                        "metric_name": mr.metric_name,
                        "score": mr.score,
                        "reasoning": mr.reasoning,
                        "passed": mr.passed,
                    } for mr in r.metric_results],
                    overall_score=r.overall_score,
                    error_message=r.error_message,
                    duration_ms=r.duration_ms,
                )
                session.add(orm_result)

            run.status = "completed"
            run.completed_at_utc = func.now()
            run.summary_json = {
                "total_cases": len(results),
                "avg_score": round(sum(scores) / len(scores), 4) if scores else 0,
                "error_count": sum(1 for r in results if r.error_message),
            }
            await session.commit()

    @staticmethod
    def _to_run_config_view(c) -> dict:
        return {
            "id": c.id, "name": c.name, "dataset_id": c.dataset_id,
            "target_type": c.target_type, "target_key": c.target_key,
            "metric_configs": c.metric_configs_json or [],
            "judge_model_key": c.judge_model_key,
            "created_at_utc": c.created_at_utc,
        }

    @staticmethod
    def _to_run_view(r) -> dict:
        return {
            "id": r.id, "config_id": r.config_id, "status": r.status,
            "started_at_utc": r.started_at_utc, "completed_at_utc": r.completed_at_utc,
            "summary": r.summary_json, "created_at_utc": r.created_at_utc,
        }

    @staticmethod
    def _to_run_result_view(r) -> dict:
        return {
            "id": r.id, "run_id": r.run_id, "case_id": r.case_id,
            "actual_output": r.actual_output or "",
            "metric_results": r.metric_results_json or [],
            "overall_score": r.overall_score,
            "error_message": r.error_message,
            "duration_ms": r.duration_ms,
        }
