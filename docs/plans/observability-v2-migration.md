# Observability V2 迁移 — 进度与待办

## 已完成（5 commits on `feature/observability-v2`）

### Commit 1: `0a06c7a` — Infra Queue 改进
- NonRetryableQueueError（直接进 DLQ）
- QueueConsumer 改为 inflight task set 并发模型
- _claim_stuck 返回消息（修复丢消息 bug）
- publish_batch 修复（ensure_group 前置、pipeline 内 trim）
- queue_stats() 协议方法 + 实现
- InMemoryQueue pending 跟踪防重复投递

### Commit 2: `982ad60` — Observability 包重写
- contracts.py → Pydantic 模型（SpanEnvelope, TraceEnvelope, TracePage, TraceStats）
- config.py → 完整配置（capture_mode, sampling, publisher tuning, retention）
- 新增 sanitizer.py（PII 脱敏、secret key redaction）
- 新增 span_processor.py（TraceBufferSpanProcessor，priority retention）
- 新增 publisher.py（AsyncTracePublisher，backpressure）
- trace_store.py → ingest_trace 单入口、cursor 分页、delete_expired
- module.py → 完整 OTel 生命周期（TracerProvider, health 诊断）
- span_builder.py / agent_runtime_listener.py 标记 deprecated

### Commit 3: `f7d6ddb` — Backend Worker 框架
- 新增 worker_runtime.py（WorkerCapability, WorkerContext, WorkerTaskSpec, WorkerRegistry, WorkerSupervisor）
- 新增 worker_modules.py（注册 document_indexing + trace_ingestion）
- 新增 worker_task.py（trace ingestion handler）
- worker.py 从单任务改为通用 WorkerSupervisor
- observability models/router/schemas/dependencies 重写
- web_modules.py 更新（queue_backend、service_name 参数）
- config.py 新增 WorkerSettings

### Commit 4: `f036fde` — DB Migration 0019
- DROP + CREATE trace_records / trace_spans
- 新增 run_id, user_id, correlation_id, cache tokens, dropped_span_count
- CHECK constraints, FK CASCADE, 复合索引

### Commit 5: `a362309` — 前端更新
- contracts.ts → TraceStatus union、扩展字段、TracePage cursor 分页
- api.ts → cursor 参数、getIngestionHealth
- hooks.ts → useIngestionHealth (refetchInterval: 10s)
- TraceListPage → cursor 分页、丰富过滤器、ingestion health dashboard
- TraceDetailPage → span 深度缩进、cache/cost info bar
- TraceWaterfallChart → spanKind → kind
- i18n 保持 WSL2 的 `observability:` namespace split

---

## 待处理事项

### 高优先级（必须在合并前完成）— ✅ 全部完成

1. ✅ **数据库迁移验证** — `alembic upgrade head` 成功，trace_records/trace_spans v2 schema 正确
2. ✅ **后端启动验证** — uvicorn 启动干净无报错，`/api/traces`、`/stats`、`/ingestion-health` 均正常
3. ✅ **前端编译验证** — `tsc --noEmit` + `vite build` 通过

### 修复项（本次新增）
- ✅ migration 0017 `_has_column` 添加表存在性检查（`evaluation_configs` 不存在时跳过）
- ✅ web_modules.py 移除 `BackendKnowledgeProvider` 不支持的 `tracer` 参数

### 中优先级

5. ✅ **engine.py tracer 集成** — 已完成（`17c251d`）
   - 新增 `_TracerSpanManager` 管理 OTel root span 生命周期
   - `AgentRuntime` 和 `create_agent_runtime` 新增 `tracer` 参数
   - `web_modules.py` 改为传入 `obs_module.get_tracer("agent_runtime")`
   - `_build_obs_bridge_factory` 标记 deprecated（`DeprecationWarning`）

6. ✅ **ObservabilityModule lifespan 注册** — 已验证 `app.state.observability_module` 和 `app.state.queue_backend` 正确设置

7. ✅ **前端 i18n 补充** — 所有硬编码英文已替换为 i18n key（health dashboard、filters、pagination、detail info bar）

### 低优先级

8. ✅ **span_builder.py / agent_runtime_listener.py 清理** — 已完成（`17c251d`）
   - 删除 `span_builder.py`、`agent_runtime_listener.py`、`test_span_builder.py`
   - `observability/__init__.py` 移除 `SpanBuilder` 导出
   - `events.py` / `loop.py` 注释更新

9. ✅ **docker-compose.yml** — worker 已使用通用入口 `python -m worker`，无需修改

10. ✅ **测试补充** — 55 个单元测试覆盖 sanitizer、contracts、span_processor（packages/observability/tests/）

### 后续优化（`17c251d` + `b26e7c6` 完成）

11. ✅ **预存测试修复** — `conftest.py` + observability lazy imports
    - `conftest.py`：`auth=AuthSettings(secret_key=...)` 替代被忽略的 property kwarg
    - `conftest.py`：手动调用 `configure_auth()`（lifespan 跳过时不会自动调用）
    - `conftest.py`：override `get_db` → HTTP 503 + patch `get_session_factory`
    - `module.py` / `__init__.py`：OTel 导入延迟化，避免 `ModuleNotFoundError`
    - 16/22 测试通过（6 个 `@pytest.mark.db` 需要真实数据库）

---

## 关键文件路径

| 组件 | 路径 |
|------|------|
| Queue infra | `packages/infra/src/alkit_infra/queue/` |
| Observability 包 | `packages/observability/src/observability/` |
| Worker runtime | `backend/src/runtime/worker_runtime.py` |
| Worker modules | `backend/src/runtime/worker_modules.py` |
| Worker entry | `backend/src/worker.py` |
| Trace ingestion | `backend/src/modules/observability/worker_task.py` |
| Observability models | `backend/src/modules/observability/models.py` |
| Observability router | `backend/src/modules/observability/router.py` |
| DB migration | `backend/alembic/versions/0019_observability_v2.py` |
| Frontend contracts | `frontend/admin/src/modules/observability/lib/contracts.ts` |
| Frontend pages | `frontend/admin/src/modules/observability/resources/traces/` |
| Config | `backend/src/config.py`（新增 WorkerSettings） |
| Web modules | `backend/src/runtime/web_modules.py` |

## 分支状态

- 分支：`feature/observability-v2`
- 已 push 到 `origin/feature/observability-v2`
- 基于 `main` 的 `711a185`
- 5 commits ahead of main
