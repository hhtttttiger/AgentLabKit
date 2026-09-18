from __future__ import annotations

import asyncio
import json
import os
import platform
import sys
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
from application.execution.contracts import ExecuteAgentCommand, ReplayRunCommand
from application.execution.replay_run import (
    ReplayInputUnavailable,
    ReplayRun,
    ReplaySourceNotFound,
    ReplayTargetUnavailable,
    ReplayTargetUnsupported,
)
from application.execution.execute_agent import ExecuteAgent
from application.execution.replay_external import (
    ExternalReplayInputUnavailable,
    ExternalReplaySourceNotFound,
    ExternalReplayWorkspaceUnavailable,
    ReplayExternalRun,
    ReplayExternalRunCommand,
)
from application.evaluation.compare import (
    CompareEvaluationRuns,
    CompareEvaluationRunsCommand,
    InvalidEvaluationResultSet,
    EvaluationRunNotFound,
    EvaluationRunsNotComparable,
)
from evaluation.contracts_v2 import EvaluationResult
from llm_gateway import Capability, ProviderId, TextGenerateRequest

from tools.registry import create_desktop_tool_registry
from desktop.core.config import AppConfig, LLMConfig, apply_environment_overrides

from .store import LocalAgentReader, LocalDatabase, LocalDatasetStore, LocalEvaluationStore, LocalRunStore, parse_dt, utc_iso
from .external_agent import ExternalAgentRunner, detect_codex


class TurnBody(BaseModel):
    Message: str
    SessionId: str | None = None
    UserId: str | None = None
    History: list[dict[str, Any]] = []
    WorkingDirectory: str | None = None


class ModelTextBody(BaseModel):
    Message: str
    SystemPrompt: str | None = None
    InvocationContext: dict[str, Any] | None = None


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
    workingDirectory: str | None = None


class ReplayBody(BaseModel):
    sourceRunId: str
    agentId: str = "codex"


class ModelSettingsBody(BaseModel):
    provider: str
    baseUrl: str
    model: str
    apiKey: str | None = None
    clearApiKey: bool = False


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
    def __init__(self, runtime: Any, external_runner: ExternalAgentRunner | None = None) -> None:
        self.runtime = runtime
        self.external_runner = external_runner

    async def execute(self, *, input: str, target: Any, session_id: str | None,
                      user_id: str | None, history: tuple[AgentMessage, ...],
                      metadata: dict[str, object]) -> Any:
        target_kind = getattr(target, "kind", "native")
        if target_kind == "external":
            if target.agent_key != "codex":
                raise ValueError(f"unsupported external agent: {target.agent_key}")
            workspace = metadata.get("working_directory")
            if self.external_runner is None or not workspace:
                raise ValueError("working_directory is required for Codex evaluation")
            return await self.external_runner.execute(input=input, target=target, working_directory=str(workspace), metadata=metadata)
        if target_kind != "native":
            raise ValueError(f"unsupported agent execution kind: {target_kind}")
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
            working_directory=row["working_directory"],
        )


class LocalComposition:
    def __init__(self, db_path: Path) -> None:
        self.db = LocalDatabase(db_path)
        self.runs = LocalRunStore(self.db)
        self.datasets = LocalDatasetStore(self.db)
        self.evaluations = LocalEvaluationStore(self.db)
        self.agents = LocalAgentReader(self.db)
        self._external_availability = detect_codex()
        self.external_runner = ExternalAgentRunner(availability=self._external_availability)
        self._sync_external_agent(self._external_availability)
        self._runtime = None
        self._gateway = None
        self._active_executions = 0

    def _sync_external_agent(self, availability: Any) -> None:
        with self.db._lock, self.db.connection:
            self.db.connection.execute(
                "INSERT INTO local_agents(agent_key, display_name, version, model, kind, availability, executable, availability_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(agent_key) DO UPDATE SET version=excluded.version, availability=excluded.availability, executable=excluded.executable, availability_message=excluded.availability_message, kind=excluded.kind",
                (availability.agent_id, availability.display_name, availability.version or "unknown", "", availability.kind, availability.availability, availability.executable, availability.message),
            )

    def refresh_agent_catalog(self) -> Any:
        self._external_availability = detect_codex()
        self.external_runner.update_availability(self._external_availability)
        self._sync_external_agent(self._external_availability)
        return self._external_availability

    def start_runtime(self) -> None:
        self._gateway, self._runtime = self._build_runtime(AppConfig.load_effective().llm)

    def _build_runtime(self, config: LLMConfig):
        config.validate()
        provider_id = ProviderId.OPENAI if config.provider == "openai" else ProviderId.ANTHROPIC
        from llm_gateway.config import GatewaySettings, ModelDefinition, ProviderConfig
        from llm_gateway.bootstrap import create_gateway_service
        provider = ProviderConfig(api_key=config.api_key or "not-set", base_url=config.base_url or None)
        model = ModelDefinition(model_key=config.model, provider=provider_id, provider_model_name=config.model, capabilities={Capability.TEXT})
        gateway_kwargs: dict[str, Any] = {"catalog": {"enable_static_fallback": True}, "models": [model]}
        gateway_kwargs["openai" if provider_id is ProviderId.OPENAI else "anthropic"] = provider
        settings = GatewaySettings(**gateway_kwargs)
        gateway = create_gateway_service(settings)
        try:
            tools = create_desktop_tool_registry()
        except Exception:
            tools = ToolRegistry()
        runtime = create_agent_runtime(
            settings=AgentSettings(default_model=config.model, enable_mcp=False),
            gateway=gateway,
            tool_registry=tools,
            completion_sink=self.runs.finalize,
        )
        return gateway, runtime

    async def reload_model_config(self) -> None:
        if self._active_executions:
            raise RuntimeError("Model settings cannot be changed while an Agent execution is active")
        gateway, runtime = self._build_runtime(AppConfig.load_effective().llm)
        old_runtime = self._runtime
        self._gateway, self._runtime = gateway, runtime
        if old_runtime is not None:
            await old_runtime.stop()

    @property
    def runtime(self) -> Any:
        if self._runtime is None:
            self.start_runtime()
        return self._runtime

    @property
    def gateway(self) -> Any:
        if self._gateway is None:
            self.start_runtime()
        return self._gateway


def _load_llm_config() -> dict[str, str]:
    llm = AppConfig.load_effective().llm
    return {"provider": llm.provider, "base_url": llm.base_url, "api_key": llm.api_key, "model": llm.model}


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


def _evaluation_result_view(result: EvaluationResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "exampleId": result.example_id,
        "score": result.score,
        "passed": result.passed,
        "message": result.message,
        "details": dict(result.details),
        "durationMs": result.duration_ms,
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
        return envelope([{"agentKey": r["agent_key"], "displayName": r["display_name"], "publishedVersionNumber": int(r["version"]) if str(r["version"]).isdigit() else None, "id": r["agent_key"], "kind": r["kind"], "availability": r["availability"], "availabilityMessage": r["availability_message"]} for r in row])

    @app.get("/api/desktop/agents")
    async def desktop_agents(refresh: bool = False):
        if refresh:
            composition.refresh_agent_catalog()
        rows = composition.db.connection.execute("SELECT * FROM local_agents WHERE enabled=1 ORDER BY kind, display_name").fetchall()
        return envelope([{"id": r["agent_key"], "displayName": r["display_name"], "kind": r["kind"], "availability": r["availability"], "version": r["version"], "message": r["availability_message"]} for r in rows])

    @app.get("/api/llm-catalog/options/models")
    async def model_options():
        config = _load_llm_config()
        return envelope([{"modelKey": config["model"], "displayName": config["model"], "isEnabled": bool(config["api_key"])}])

    def model_settings_view() -> dict[str, Any]:
        config = AppConfig.load_effective().llm
        overrides = AppConfig.environment_overrides()
        return {
            "provider": config.provider,
            "baseUrl": config.base_url,
            "model": config.model,
            "apiKeyConfigured": bool(config.api_key),
            "providerOverridden": "provider" in overrides,
            "baseUrlOverridden": "base_url" in overrides,
            "apiKeyOverridden": "api_key" in overrides,
            "modelOverridden": "model" in overrides,
            "overrideEnvironment": overrides,
        }

    @app.get("/api/desktop/settings/models")
    async def get_model_settings():
        return envelope(model_settings_view())

    def draft_model_config(body: ModelSettingsBody, *, current: LLMConfig) -> LLMConfig:
        api_key = current.api_key if body.apiKey is None else body.apiKey
        if body.clearApiKey:
            api_key = ""
        config = LLMConfig(provider=body.provider, base_url=body.baseUrl, api_key=api_key or "", model=body.model)
        config.validate()
        return config

    async def test_model_config(config: LLMConfig) -> None:
        gateway, _runtime = composition._build_runtime(config)
        try:
            await gateway.generate_text(TextGenerateRequest(model=config.model, prompt="Reply with OK."))
        except Exception as error:
            message = str(error).lower()
            if "401" in message or "auth" in message or "api key" in message:
                raise HTTPException(502, "Authentication failed. Check your API key.") from error
            if "model" in message:
                raise HTTPException(502, "The configured model could not be used.") from error
            raise HTTPException(502, "Could not connect to provider endpoint.") from error

    @app.post("/api/desktop/settings/models/test")
    async def test_model_settings(body: ModelSettingsBody):
        try:
            config = draft_model_config(body, current=AppConfig.load_effective().llm)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        await test_model_config(config)
        return envelope({"status": "connected"})

    @app.put("/api/desktop/settings/models")
    async def update_model_settings(body: ModelSettingsBody):
        if composition._active_executions:
            raise HTTPException(409, "Model settings cannot be changed while an Agent execution is active")
        previous = AppConfig.load()
        try:
            config = draft_model_config(body, current=previous.llm)
            candidate_gateway, candidate_runtime = composition._build_runtime(apply_environment_overrides(config))
            config.validate()
            AppConfig(llm=config).save()
            old_runtime = composition._runtime
            composition._gateway, composition._runtime = candidate_gateway, candidate_runtime
            if old_runtime is not None:
                await old_runtime.stop()
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except Exception as error:
            previous.save()
            raise HTTPException(500, "Could not apply model settings. Previous configuration is still active.") from error
        return envelope(model_settings_view())

    @app.get("/api/agents")
    async def agents(page: int = 1, pageSize: int = 20, refresh: bool = False):
        if refresh:
            composition.refresh_agent_catalog()
        row = composition.db.connection.execute("SELECT * FROM local_agents WHERE enabled=1").fetchall()
        items = [{"agentKey": r["agent_key"], "displayName": r["display_name"], "description": "Desktop local agent", "publishedVersionNumber": int(r["version"]) if str(r["version"]).isdigit() else None, "isEnabled": r["availability"] == "ready", "kind": r["kind"], "availability": r["availability"], "availabilityMessage": r["availability_message"]} for r in row]
        return envelope({"items": items, "totalCount": len(items), "page": page, "pageSize": pageSize})

    @app.post("/api/ai/invoke/agents/{agent_key}/turn/stream")
    async def stream_turn(agent_key: str, body: TurnBody):
        if composition._active_executions:
            # Multiple sessions may still run; this counter only protects the
            # settings reload boundary from swapping a live runtime.
            pass
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
            composition._active_executions += 1
            try:
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
            finally:
                composition._active_executions = max(0, composition._active_executions - 1)
        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/api/ai/invoke/{model_id}/text/stream")
    async def stream_model(model_id: str, body: ModelTextBody):
        config = AppConfig.load_effective().llm
        if model_id != config.model:
            raise HTTPException(404, "Model not found")
        session_id = str((body.InvocationContext or {}).get("SessionId") or "desktop-model")

        async def events():
            composition._active_executions += 1
            try:
                prompt = body.Message
                if body.SystemPrompt:
                    prompt = f"System instructions:\n{body.SystemPrompt}\n\nUser message:\n{body.Message}"
                async for event in composition.gateway.generate_text_stream(TextGenerateRequest(model=model_id, prompt=prompt)):
                    if event.delta or event.text:
                        yield f"data: {json.dumps({'content': event.delta or event.text or '', 'done': False}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                composition._active_executions = max(0, composition._active_executions - 1)

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

    @app.post("/api/runs/{run_id}/replay")
    async def replay_run(run_id: str):
        if composition._active_executions:
            raise HTTPException(409, "Replay cannot start while an Agent execution is active")
        try:
            use_case = ReplayRun(
                composition.runs,
                LocalExecutor(composition.runtime, composition.external_runner),
                composition.agents,
            )
            result = await use_case.execute(ReplayRunCommand(source_run_id=run_id, user_id="local"))
        except ReplaySourceNotFound as error:
            raise HTTPException(404, "Source Run not found") from error
        except ReplayTargetUnavailable as error:
            raise HTTPException(409, str(error)) from error
        except ReplayTargetUnsupported as error:
            raise HTTPException(422, str(error)) from error
        except ReplayInputUnavailable as error:
            raise HTTPException(422, "Source Run has no replayable input") from error
        await composition.runs.finalize(result.run)
        stored = await composition.runs.get_run(result.run.run_id)
        return envelope({"sourceRunId": result.source_run_id, "run": run_view(stored or result.run)})

    @app.post("/api/desktop/replay")
    async def replay_external(body: ReplayBody):
        target = await composition.agents.resolve(body.agentId)
        if target.kind != "external":
            raise HTTPException(400, "Replay target must be an external agent")
        if target.agent_key != "codex":
            raise HTTPException(422, f"unsupported external agent: {target.agent_key}")
        availability = composition._external_availability
        if availability.availability != "ready":
            raise HTTPException(409, availability.message or "Codex CLI is not installed")
        source = await composition.runs.get_run(body.sourceRunId)
        if source is None:
            raise HTTPException(404, "Source Run not found")
        source_case = await composition.datasets.case_for_source_run(source.run_id)
        metadata = {
            "source_case_id": source_case["id"] if source_case else None,
            "source_dataset_id": source_case["datasetId"] if source_case else None,
        }
        try:
            result = await ReplayExternalRun(composition.runs, composition.external_runner).execute(
                ReplayExternalRunCommand(source_run_id=body.sourceRunId, agent_id=body.agentId, agent_kind=target.kind, metadata=metadata),
            )
        except ExternalReplaySourceNotFound as error:
            raise HTTPException(404, "Source Run not found") from error
        except ExternalReplayInputUnavailable as error:
            raise HTTPException(422, "Source Run has no replayable input") from error
        except ExternalReplayWorkspaceUnavailable as error:
            raise HTTPException(409, str(error)) from error
        run = result.run
        await composition.runs.finalize(run)
        return envelope(run_view(await composition.runs.get_run(run.run_id)))

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
        return envelope([{"id": str(r["id"]), "name": r["name"], "datasetId": str(r["dataset_id"]), "targetType": r["target_type"], "targetKey": r["target_key"], "metricConfigs": composition.db.value(r["metric_configs_json"], []), "judgeModelKey": r["judge_model_key"], "workingDirectory": r["working_directory"]} for r in rows])

    @app.post("/api/eval/run-configs")
    async def create_config(body: ConfigBody):
        with composition.db._lock, composition.db.connection:
            cur = composition.db.connection.execute("INSERT INTO local_eval_configs(name, dataset_id, target_type, target_key, metric_configs_json, judge_model_key, working_directory) VALUES (?, ?, ?, ?, ?, ?, ?)", (body.name, int(body.datasetId), body.targetType, body.targetKey, composition.db.json(body.metricConfigs), body.judgeModelKey, body.workingDirectory))
        return envelope({"id": str(cur.lastrowid), **body.model_dump()})

    @app.post("/api/eval/run-configs/{config_id}/run")
    async def evaluate_config(config_id: str):
        config = await LocalEvaluationConfigurationReader(composition.db).get_configuration(config_id)
        use_case = EvaluateDataset(composition.datasets, composition.agents, LocalExecutor(composition.runtime, composition.external_runner), LocalEvaluator(), composition.evaluations, finalization=LocalTraceFinalization(), configurations=LocalEvaluationConfigurationReader(composition.db))
        metadata = {"working_directory": config.working_directory} if config.working_directory else {}
        result = await use_case.execute(EvaluateDatasetCommand(dataset_id=config.dataset_id, agent_key=config.target_key, evaluation_config_id=config.config_id, metadata=metadata))
        run = result.evaluation_run
        return envelope({"id": str(run["id"]), "configId": config_id, "datasetId": config.dataset_id, "status": run.get("status", "completed"), "summary": run.get("summary", {})})

    @app.get("/api/eval/runs")
    async def list_eval_runs(limit: int = 20):
        rows = composition.db.connection.execute("SELECT * FROM local_eval_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return envelope([{"id": str(r["id"]), "configId": str(r["config_id"]), "datasetId": str(r["dataset_id"]), "agentKey": r["agent_key"], "status": r["status"], "summary": composition.db.value(r["summary_json"], {})} for r in rows])

    @app.post("/api/eval/runs/compare")
    async def compare_eval_runs(body: dict[str, str]):
        try:
            result = await CompareEvaluationRuns(composition.evaluations).execute(CompareEvaluationRunsCommand(left_run_id=body["leftRunId"], right_run_id=body["rightRunId"]))
        except (KeyError, EvaluationRunNotFound) as error:
            raise HTTPException(404, "Evaluation run not found") from error
        except (EvaluationRunsNotComparable, InvalidEvaluationResultSet) as error:
            raise HTTPException(422, str(error)) from error
        return envelope({
            "leftRunId": result.left_run_id, "rightRunId": result.right_run_id, "datasetId": result.dataset_id,
            "matchedCount": result.matched_count, "leftOnlyCount": result.left_only_count, "rightOnlyCount": result.right_only_count,
            "examples": [{"exampleId": item.example_id, "classification": item.classification,
                          "left": _evaluation_result_view(item.left), "right": _evaluation_result_view(item.right)} for item in result.examples],
        })

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
