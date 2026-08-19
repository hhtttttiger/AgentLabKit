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

5. **engine.py tracer 集成**
   - 当前 web_modules.py 使用 bridge factory（兼容旧方式）
   - Windows 版本改为 `tracer=obs_module.tracer` 直接注入
   - 需要修改 `packages/agent_runtime/src/agent_runtime/runtime/factory.py`：
     - 添加 `tracer: Tracer | None = None` 参数
     - engine 内部使用 tracer（可选，渐进式）
   - 这是一个独立的重构任务，不阻塞当前迁移

6. **ObservabilityModule 在 main.py 的 lifespan 中注册**
   - 确认 `request.app.state.observability_module` 被正确设置
   - 确认 `request.app.state.queue_backend` 被正确设置（ingestion-health 需要）
   - 需要检查 `backend/src/main.py` 的 lifespan 逻辑

7. **前端 i18n 补充**
   - 新增的 UI 文字（ingestion health dashboard、cost、dropped spans）目前是硬编码英文
   - 需要添加到 `frontend/admin/src/shared/i18n/locales/en-US/observability.ts`
   - 和 `zh-CN/observability.ts`

### 低优先级

8. **span_builder.py / agent_runtime_listener.py 清理**
   - 确认没有其他地方引用后可删除
   - 或者保留为 deprecated 直到下个大版本

9. **docker-compose.yml 更新**
   - worker 服务的 command 可能需要调整（从单任务改为通用）
   - 环境变量 `APP_WORKER_TASKS=*` 已是默认值

10. **测试补充**
    - 为新的 queue consumer、sanitizer、span_processor 编写单元测试
    - 为 worker_task.py 编写集成测试

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
