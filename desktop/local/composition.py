from __future__ import annotations

import asyncio
import json
import os
import platform
import sys
import tomllib
from hmac import compare_digest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Local Mode is runnable from the repository checkout and from a packaged
# launcher that sets AGENTLAB_REPO_ROOT.  It does not import backend modules.
_ROOT = Path(os.environ.get("AGENTLAB_REPO_ROOT", Path(__file__).resolve().parents[2]))
for _path in (
    _ROOT / "desktop", _ROOT / "packages/application/src", _ROOT / "packages/agent_runtime/src",
    _ROOT / "packages/evaluation/src", _ROOT / "packages/llm_gateway/src", _ROOT / "packages/infra/src",
):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_runtime import AgentMessage, AgentRole, AgentSettings, AgentTurnRequest, ToolRegistry, create_agent_runtime
from application import (
    CaptureRunAsDatasetExample,
    CaptureRunAsDatasetExampleCommand,
    EvaluateDataset,
    EvaluateDatasetCommand,
)
from application.execution.contracts import ExecuteAgentCommand
from application.execution.execute_agent import ExecuteAgent
from evaluation.contracts_v2 import EvaluationResult
from llm_gateway import Capability, ProviderId

from tools.registry import create_desktop_tool_registry

from .store import LocalAgentReader, LocalDatabase, LocalDatasetStore, LocalEvaluationStore, LocalRunStore, parse_dt, utc_iso


class TurnBody(BaseModel):
    Message: str
    SessionId: str | None = None
    UserId: str | None = None
    History: list[dict[str, Any]] = []
    WorkingDirectory: str | None = None


class DatasetBody(BaseModel):
    name: str
    description: str | None = None
    tags: list[str] = []


class CaseBody(BaseModel):
    inputText: str
    expectedOutput: str | None = None
    context: list[str] = []


class ConfigBody(BaseModel):
    name: str
    datasetId: str
    targetType: str = "agent"
    targetKey: str = "local-agent"
    metricConfigs: list[dict[str, Any]] = []
    judgeModelKey: str = ""


class LocalTraceFinalization:
    async def wait_until_persisted(self, trace_id: str, *, timeout_seconds: float) -> bool:
        return True


class LocalEvaluator:
    name = "local.output_match"

    async def evaluate(self, context: Any) -> EvaluationResult:
        expected = context.example.expected_output
        actual = str(context.run.output or "")
        if expected in (None, ""):
            return EvaluationResult(
                evaluator_name=self.name, example_id=context.example.example_id,
                run_id=context.run.run_id, score=None, passed=None,
                message="No expected output supplied", details={"actual_output": actual},
            )
        passed = actual.strip() == str(expected).strip()
        return EvaluationResult(
            evaluator_name=self.name, example_id=context.example.example_id,
            run_id=context.run.run_id, score=1.0 if passed else 0.0, passed=passed,
            details={"actual_output": actual, "expected_output": expected},
        )


class LocalExecutor:
    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    async def execute(self, *, input: str, target: Any, session_id: str | None,
                      user_id: str | None, history: tuple[AgentMessage, ...],
                      metadata: dict[str, object]) -> Any:
        return await self.runtime.run(AgentTurnRequest(
            session_id=session_id or "local-evaluation",
            user_message=input, history=list(history), user_id=user_id,
            agent_key=target.agent_key,
            agent_version=int(target.agent_version) if target.agent_version else None,
            metadata={str(k): str(v) for k, v in metadata.items()},
        ))

    def stream(self, **kwargs: Any):
        async def updates():
            async for event in self.runtime.stream(AgentTurnRequest(
                session_id=kwargs.get("session_id") or "desktop",
                user_message=kwargs["input"], history=list(kwargs.get("history", ())),
                user_id=kwargs.get("user_id"), agent_key=kwargs["target"].agent_key,
                agent_version=int(kwargs["target"].agent_version) if kwargs["target"].agent_version else None,
            )):
                yield event
        return updates()


class LocalEvaluationConfigurationReader:
    def __init__(self, db: LocalDatabase) -> None:
        self.db = db

    async def get_configuration(self, config_id: str):
        from application.evaluation.contracts import EvaluationConfiguration
        row = self.db.connection.execute("SELECT * FROM local_eval_configs WHERE id=?", (int(config_id),)).fetchone()
        if row is None:
            raise LookupError(f"evaluation config {config_id} not found")
        return EvaluationConfiguration(
            config_id=str(row["id"]), dataset_id=str(row["dataset_id"]),
            target_type=row["target_type"], target_key=row["target_key"],
            metric_configs=tuple(self.db.value(row["metric_configs_json"], [])),
            judge_model_key=row["judge_model_key"],
        )


class LocalComposition:
    def __init__(self, db_path: Path) -> None:
        self.db = LocalDatabase(db_path)
        self.runs = LocalRunStore(self.db)
        self.datasets = LocalDatasetStore(self.db)
        self.evaluations = LocalEvaluationStore(self.db)
        self.agents = LocalAgentReader(self.db)
        self._runtime = None
        self._gateway = None

    def start_runtime(self) -> None:
        config = _load_llm_config()
        provider_id = ProviderId.OPENAI if config["provider"] == "openai" else ProviderId.ANTHROPIC
        from llm_gateway.config import GatewaySettings, ModelDefinition, ProviderConfig
        from llm_gateway.bootstrap import create_gateway_service
        provider = ProviderConfig(api_key=config["api_key"] or "not-set", base_url=config["base_url"] or None)
        model = ModelDefinition(model_key=config["model"], provider=provider_id, provider_model_name=config["model"], capabilities={Capability.TEXT})
        gateway_kwargs: dict[str, Any] = {"catalog": {"enable_static_fallback": True}, "models": [model]}
        gateway_kwargs["openai" if provider_id is ProviderId.OPENAI else "anthropic"] = provider
        settings = GatewaySettings(**gateway_kwargs)
        self._gateway = create_gateway_service(settings)
        try:
            tools = create_desktop_tool_registry()
        except Exception:
            tools = ToolRegistry()
        self._runtime = create_agent_runtime(
            settings=AgentSettings(default_model=config["model"], enable_mcp=False),
            gateway=self._gateway,
            tool_registry=tools,
            completion_sink=self.runs.finalize,
        )

    @property
    def runtime(self) -> Any:
        if self._runtime is None:
            self.start_runtime()
        return self._runtime


def _load_llm_config() -> dict[str, str]:
    """Read the Desktop TOML without requiring the optional writer package."""
    path = Path.home() / ".config" / "agentlabkit" / "desktop.toml"
    data: dict[str, Any] = {}
    if path.exists():
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    llm = data.get("llm", {})
    return {
        "provider": str(os.environ.get("AGENTLAB_LLM_PROVIDER", llm.get("provider", "openai"))),
        "base_url": str(os.environ.get("AGENTLAB_LLM_BASE_URL", llm.get("base_url", "https://api.openai.com/v1"))),
        "api_key": str(os.environ.get("AGENTLAB_LLM_API_KEY", llm.get("api_key", ""))),
        "model": str(os.environ.get("AGENTLAB_LLM_MODEL", llm.get("model", "gpt-4o-mini"))),
    }


def envelope(data: Any) -> dict[str, Any]:
    return {"success": True, "msg": "ok", "data": data}


def run_view(record: Any) -> dict[str, Any]:
    return {
        "runId": record.run_id, "traceId": record.trace_id, "status": record.status,
        "targetType": record.target_type, "targetKey": record.target_key,
        "targetVersion": record.target_version, "input": record.input, "output": record.output,
        "startedAt": utc_iso(record.started_at), "completedAt": utc_iso(record.completed_at),
        "durationMs": record.duration_ms, "sessionId": record.session_id,
        "errorCode": record.error_code, "errorMessage": record.error_message,
        "metadata": record.metadata,
    }


def create_local_app(db_path: Path | None = None) -> FastAPI:
    data_dir = Path(os.environ.get("AGENTLAB_DATA_DIR", _default_data_dir()))
    composition = LocalComposition(db_path or data_dir / "agentlab.db")
    app = FastAPI(title="AgentLab Desktop Local Mode", version="0.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["tauri://localhost", "http://tauri.localhost", "http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-AgentLab-Local-Token"],
    )
    local_token = os.environ.get("AGENTLAB_LOCAL_TOKEN", "")

    @app.middleware("http")
    async def require_local_token(request: Request, call_next):
        # Browser CORS preflight cannot include the private request header;
        # the actual API request is still checked below.
        if request.url.path.startswith("/api/") and request.method != "OPTIONS":
            supplied = request.headers.get("X-AgentLab-Local-Token", "")
            if not local_token or not compare_digest(supplied, local_token):
                from fastapi.responses import JSONResponse
                return JSONResponse({"success": False, "msg": "Local API token required", "data": None}, status_code=401)
        return await call_next(request)

    app.state.local = composition

    @app.on_event("startup")
    async def startup() -> None:
        composition.start_runtime()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        if composition._runtime is not None:
            await composition._runtime.stop()
        composition.db.close()

    @app.get("/health")
    async def health():
        return envelope({"status": "healthy", "mode": "desktop-local", "database": str(composition.db.path)})

    @app.get("/api/ai/invoke/agents/options")
    async def agent_options():
        row = composition.db.connection.execute("SELECT * FROM local_agents WHERE enabled=1 ORDER BY display_name").fetchall()
        return envelope([{"agentKey": r["agent_key"], "displayName": r["display_name"], "publishedVersionNumber": int(r["version"])} for r in row])

    @app.get("/api/llm-catalog/options/models")
    async def model_options():
        config = _load_llm_config()
        return envelope([{"modelKey": config["model"], "displayName": config["model"], "isEnabled": bool(config["api_key"])}])

    @app.get("/api/agents")
    async def agents(page: int = 1, pageSize: int = 20):
        row = composition.db.connection.execute("SELECT * FROM local_agents WHERE enabled=1").fetchall()
        items = [{"agentKey": r["agent_key"], "displayName": r["display_name"], "description": "Desktop local agent", "publishedVersionNumber": int(r["version"]), "isEnabled": True} for r in row]
        return envelope({"items": items, "totalCount": len(items), "page": page, "pageSize": pageSize})

    @app.post("/api/ai/invoke/agents/{agent_key}/turn/stream")
    async def stream_turn(agent_key: str, body: TurnBody):
        target = await composition.agents.resolve(agent_key)
        history = tuple(AgentMessage(role=AgentRole(item.get("Role", "user").lower()), content=item.get("Content", ""), name=item.get("Name"), metadata=item.get("Metadata", {})) for item in body.History)
        metadata = {}
        if body.WorkingDirectory:
            from tools.filesystem import canonicalize_workspace
            try:
                metadata["working_directory"] = str(canonicalize_workspace(body.WorkingDirectory))
            except ValueError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
        request = AgentTurnRequest(session_id=body.SessionId or "desktop", user_message=body.Message, history=list(history), user_id=body.UserId or "local", agent_key=target.agent_key, agent_version=int(target.agent_version or 1), metadata=metadata)

        async def events():
            async for event in composition.runtime.stream(request):
                payload = {
                    "type": {"turn_context": "context", "reply_delta": "reply_delta", "reply_completed": "completed", "tool_call": "tool_call", "tool_result": "tool_result", "delegation_delta": "delegation_delta", "handoff": "handoff", "error": "error"}.get(event.event_type, event.event_type),
                    "runId": event.run_id, "sessionId": event.session_id, "traceId": event.trace_id,
                    "agentKey": event.agent_key, "agentVersion": event.agent_version,
                    "delta": event.delta, "replyText": event.reply_text,
                    "toolName": event.tool_name, "toolEvent": event.tool_event.model_dump() if event.tool_event else None,
                    "errorCode": event.error.code if event.error else None,
                    "errorMessage": event.error.message if event.error else None,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(events(), media_type="text/event-stream")

    @app.get("/api/runs")
    async def list_runs(limit: int = 20, offset: int = 0):
        items = await composition.runs.list_runs(user_id="local", limit=limit, offset=offset)
        return envelope({"items": [run_view(item) for item in items], "total": await composition.runs.count_runs(user_id="local")})

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str):
        record = await composition.runs.get_run(run_id)
        if record is None:
            raise HTTPException(404, "Run not found")
        return envelope(run_view(record))

    @app.get("/api/traces/{trace_id}")
    async def get_trace(trace_id: str):
        row = composition.db.connection.execute("SELECT * FROM local_traces WHERE trace_id=?", (trace_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Trace not found")
        return envelope({"trace": {"traceId": row["trace_id"], "rootSpanId": "local", "runId": row["run_id"], "agentKey": "local-agent", "sessionId": row["session_id"], "userId": "local", "correlationId": None, "status": row["status"], "totalDurationMs": 0, "totalInputTokens": 0, "totalOutputTokens": 0, "cacheWriteTokens": 0, "cacheReadTokens": 0, "totalEstimatedCost": 0, "spanCount": 0, "droppedSpanCount": 0, "sampleReason": "local", "attributes": composition.db.value(row["attributes_json"], {}), "schemaVersion": 1, "startedAtUtc": row["started_at"], "completedAtUtc": row["completed_at"]}, "spans": []})

    @app.get("/api/eval/datasets")
    async def list_datasets(page: int = 1, pageSize: int = 20):
        items, total = await composition.datasets.list(page, pageSize)
        return envelope({"items": items, "total": total})

    @app.post("/api/eval/datasets")
    async def create_dataset(body: DatasetBody):
        return envelope(await composition.datasets.create(body.name, body.description, body.tags))

    @app.get("/api/eval/datasets/{dataset_id}/cases")
    async def list_cases(dataset_id: str):
        return envelope(await composition.datasets.cases(dataset_id))

    @app.post("/api/eval/datasets/{dataset_id}/cases")
    async def create_cases(dataset_id: str, body: list[CaseBody]):
        return envelope(await composition.datasets.create_cases(dataset_id, [item.model_dump() for item in body]))

    @app.post("/api/runs/{run_id}/capture")
    async def capture_run(run_id: str, request: Request):
        body = await request.json()
        result = await CaptureRunAsDatasetExample(composition.runs, composition.datasets).execute(CaptureRunAsDatasetExampleCommand(dataset_id=str(body["datasetId"]), run_id=run_id, expected_output=body.get("expectedOutput"), metadata=body.get("metadata", {})))
        return envelope({"datasetId": result.dataset_id, "sourceRunId": result.source_run_id, "exampleId": result.example_id})

    @app.get("/api/eval/run-configs")
    async def list_configs():
        rows = composition.db.connection.execute("SELECT * FROM local_eval_configs ORDER BY id DESC").fetchall()
        return envelope([{"id": str(r["id"]), "name": r["name"], "datasetId": str(r["dataset_id"]), "targetType": r["target_type"], "targetKey": r["target_key"], "metricConfigs": composition.db.value(r["metric_configs_json"], []), "judgeModelKey": r["judge_model_key"]} for r in rows])

    @app.post("/api/eval/run-configs")
    async def create_config(body: ConfigBody):
        with composition.db._lock, composition.db.connection:
            cur = composition.db.connection.execute("INSERT INTO local_eval_configs(name, dataset_id, target_type, target_key, metric_configs_json, judge_model_key) VALUES (?, ?, ?, ?, ?, ?)", (body.name, int(body.datasetId), body.targetType, body.targetKey, composition.db.json(body.metricConfigs), body.judgeModelKey))
        return envelope({"id": str(cur.lastrowid), **body.model_dump()})

    @app.post("/api/eval/run-configs/{config_id}/run")
    async def evaluate_config(config_id: str):
        config = await LocalEvaluationConfigurationReader(composition.db).get_configuration(config_id)
        use_case = EvaluateDataset(composition.datasets, composition.agents, LocalExecutor(composition.runtime), LocalEvaluator(), composition.evaluations, finalization=LocalTraceFinalization(), configurations=LocalEvaluationConfigurationReader(composition.db))
        result = await use_case.execute(EvaluateDatasetCommand(dataset_id=config.dataset_id, agent_key=config.target_key, evaluation_config_id=config.config_id))
        run = result.evaluation_run
        return envelope({"id": str(run["id"]), "configId": config_id, "datasetId": config.dataset_id, "status": run.get("status", "completed"), "summary": run.get("summary", {})})

    @app.get("/api/eval/runs")
    async def list_eval_runs(limit: int = 20):
        rows = composition.db.connection.execute("SELECT * FROM local_eval_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return envelope([{"id": str(r["id"]), "configId": str(r["config_id"]), "datasetId": str(r["dataset_id"]), "agentKey": r["agent_key"], "status": r["status"], "summary": composition.db.value(r["summary_json"], {})} for r in rows])

    @app.get("/api/eval/runs/{run_id}")
    async def eval_run_detail(run_id: str):
        run = await composition.evaluations.get_run(run_id)
        if run is None:
            raise HTTPException(404, "Evaluation run not found")
        return envelope({"run": {"id": run.run_id, "datasetId": run.dataset_id, "agentKey": run.agent_key, "status": run.status.value, "totalExamples": run.total_examples, "completedExamples": run.completed_examples, "overallScore": run.overall_score}, "results": [asdict(item) for item in await composition.evaluations.list_results(run_id)]})

    return app


def _default_data_dir() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "AgentLab"
    if system == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "AgentLab"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "AgentLab"


def main() -> None:
    import uvicorn
    port = int(os.environ.get("AGENTLAB_LOCAL_PORT", "8000"))
    uvicorn.run(create_local_app(), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
