# observability — 分布式链路追踪

> **定位**：AgentLabKit 的分布式链路追踪。通过订阅 agent_runtime 的 EventBus 事件，自动把 agent 执行过程（turn / LLM 调用 / 工具执行）累积为 Span 树，落库为 Trace + Span，并提供查询与统计。

## 系统中的角色

```
agent_runtime (EventBus: turn_* / message_* / tool_execution_* 事件)
                    │  event_bus.subscribe(bridge.on_event)   ← 无直接 import, 事件解耦
                    ▼
              observability  ← 本包
   (SpanBridge · SpanBuilder · TraceStore/PostgresTraceStore)
                    │
                    ▼
        agentlabkit-db (trace_records / trace_spans)
                    ▲
backend (main.py lifespan 初始化 + modules/observability HTTP 层)
```

- 被 `backend/src/main.py` 通过 `create_observability_module(session_factory=..., settings=ObservabilitySettings())` 初始化，挂到 `app.state.observability_module`。
- HTTP 层在 `backend/src/modules/observability/`。
- **agent_runtime 集成**：`create_span_bridge(trace_store, trace_id, agent_key, event_bus=...)` 订阅 EventBus；agent_runtime engine 在 `run_turn` / `stream_turn` 中通过 `observability_bridge_factory` 自动创建 bridge，结束时 `finalize()` 落库。backend `main.py` lifespan 已注入 factory，`agent_key` 从 request 自动传递，`max_spans_per_trace` 从 `ObservabilitySettings` 获取。

## 目录结构

```
packages/observability/src/observability/
├── __init__.py          # 公开 API 导出
├── config.py            # ObservabilitySettings (OBSERVABILITY_ 前缀)
├── contracts.py         # SpanKind 枚举 / SpanRecord / TraceRecord
├── span_builder.py      # SpanBuilder — 从 EventBus 事件累积构建 span 树
├── trace_store.py       # TraceStore Protocol + PostgresTraceStore
├── module.py            # ObservabilityModule + create_observability_module() 工厂
└── integrations/
    └── agent_runtime_listener.py   # SpanBridge + create_span_bridge() (EventBus 桥接)
```

## 核心接口

### SpanKind (`contracts.py`)

```python
class SpanKind(str, Enum):   # AGENT_TURN / LLM_CALL / TOOL_EXECUTION / RAG_QUERY / HANDOFF / GUARDRAIL
```

### SpanBuilder (`span_builder.py`)

```python
class SpanBuilder:
    def __init__(self, trace_id, agent_key=None, session_id=None, max_spans=500) -> None
    def on_event(self, event) -> None      # EventBus listener: turn_*→AGENT_TURN, tool_execution_*→TOOL_EXECUTION, message_*(仅 assistant)→LLM_CALL
    def set_error(self, error_message) -> None
    def finalize(self) -> tuple[TraceRecord, list[SpanRecord]]   # 累积 token/cost 指标并输出
```
- `max_spans` 超限时 SpanBuilder 丢弃新 span 并记录 warning（`_append_span` 负责检查）

### TraceStore / PostgresTraceStore (`trace_store.py`)

```python
@runtime_checkable
class TraceStore(Protocol):
    async def save_trace(self, trace: TraceRecord) -> None: ...
    async def save_spans(self, spans: list[SpanRecord]) -> None: ...
    async def get_trace(self, trace_id: str) -> TraceRecord | None: ...
    async def get_trace_spans(self, trace_id: str) -> list[SpanRecord]: ...
    async def list_traces(self, *, agent_key=None, status=None, from_date=None, to_date=None, page=1, page_size=20) -> tuple[list[TraceRecord], int]: ...
    async def get_stats(self, *, from_date=None, to_date=None) -> dict: ...   # total_traces / avg_duration_ms / total_tokens / error_count
```

### SpanBridge (`integrations/agent_runtime_listener.py`)

```python
def create_span_bridge(*, trace_store: TraceStore, trace_id: str, agent_key=None, session_id=None, event_bus=None) -> SpanBridge
# event_bus 非空时自动 event_bus.subscribe(bridge.on_event)

class SpanBridge:
    def on_event(self, event) -> None        # 转发 SpanBuilder.on_event
    async def finalize(self) -> None         # builder.finalize() → 写入 trace_store
```

### 关键数据类 (`contracts.py`)

```python
class SpanRecord:    # span_id, trace_id, parent_span_id, span_kind, name, status("ok"|"error"|"timeout"), started_at_utc, completed_at_utc, duration_ms, attributes, error_code, error_message
class TraceRecord:   # trace_id, root_span_id, agent_key, session_id, status, total_duration_ms, total_input_tokens, total_output_tokens, total_estimated_cost, span_count, started_at_utc, completed_at_utc
```

### 工厂 (`module.py`)

```python
def create_observability_module(*, session_factory, settings: ObservabilitySettings | None = None) -> ObservabilityModule
```

注入 `session_factory`→PostgresTraceStore；返回含 settings/trace_store 的 ObservabilityModule。

## 配置

| Settings 类 | env 前缀 | 关键字段 | 默认值 |
|------|------|------|------|
| `ObservabilitySettings` | `OBSERVABILITY_` | `enabled`、`max_spans_per_trace` | `True`、`500` |

## 已知陷阱

- **`asyncpg` 不兼容 `::jsonb` 语法**：`sa_text()` 中写 `:attrs::jsonb` 会导致参数绑定失败（`syntax error at or near ":"`）。必须改为 `CAST(:attrs AS jsonb)`。只有 `save_spans` 受影响。
- **Token 用量必须随事件传递**：`SpanBuilder._on_message_end` 从 `event.usage`（优先）或 `event.message.usage` 提取 token 计数。`MessageEndEvent` 已添加 `usage` 字段，`run_agent_loop` 和 `stream_turn` 的流式/非流式路径都需传入 LLM 返回的 usage。
- **流式路径缺少 `MessageStartEvent`**：`run_agent_loop` 流式路径在 `llm.generate_stream()` 前必须 emit `MessageStartEvent`，否则 SpanBuilder 不会创建 LLM span。

## 依赖

### 内部

- `agentlabkit-db`（硬依赖，pyproject 声明）
- `agent_runtime` — **无直接 import**，仅通过 EventBus 事件契约解耦（监听 turn / message / tool_execution 事件）

### 外部

- `pydantic`、`pydantic-settings`、`sqlalchemy[asyncio]`

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [agent_runtime/runtime](../agent_runtime/src/agent_runtime/runtime/AGENTS.md) — EventBus 事件来源 + observability_bridge_factory 接入点
- [backend/AGENTS.md](../../backend/AGENTS.md) — trace_records/trace_spans 表与 HTTP 路由
