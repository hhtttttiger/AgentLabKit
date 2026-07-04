# 为 Agent 添加自定义工具

本文档说明如何为 `agent_runtime` 注册和实现自定义工具，包括进程内置工具和 HTTP 外部工具两种形式。

---

## 一、核心概念

| 类 | 职责 |
|----|------|
| `ToolSpec` | 工具的不可变元信息（name、description、JSON Schema、timeout、tags 等） |
| `ToolHandler` | 实现 `async execute(arguments, context) -> ToolResult` 的任意对象 |
| `ToolResult` | 执行结果：`output`（给 LLM 的文本）+ `status`（success/error/timeout）|
| `DynamicToolRegistry` | 运行时注册表：`register(spec, handler)` / `list_all()` / `build_tool_definitions()` |
| `ToolBinding` | Agent definition 中对工具的绑定（description 覆盖、invocation_mode）|

工具注册后，`AgentRuntime` 会在每次 `run_turn()` / `stream_turn()` 时自动将可用工具注入 LLM 的 function-calling schema。

---

## 二、实现进程内置工具（Built-in Tool）

### 2.1 最小示例

```python
# my_tools/weather.py
from agent_runtime.tools import ToolSpec, ToolResult, ToolExecutionContext

class WeatherTool:
    spec = ToolSpec(
        name="get_weather",
        description="获取指定城市的当前天气。",
        parameters_schema={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如 'Shanghai'",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius",
                },
            },
            "required": ["city"],
        },
        tags=frozenset({"weather", "read_only"}),
        timeout_seconds=10.0,
        max_retries=1,        # 超时后最多重试 1 次（幂等操作）
        is_idempotent=True,
    )

    async def execute(
        self,
        arguments: dict,
        context: ToolExecutionContext,
    ) -> ToolResult:
        city = arguments["city"]
        unit = arguments.get("unit", "celsius")
        # 在此调用实际天气 API
        temp = await self._fetch_temp(city, unit)
        return ToolResult(
            output=f"{city} 当前气温：{temp}°{'C' if unit == 'celsius' else 'F'}",
            structured_data={"city": city, "temp": temp, "unit": unit},
            status="success",
        )

    async def _fetch_temp(self, city: str, unit: str) -> float:
        # 实现实际 API 调用
        ...
```

### 2.2 注册到 ToolRegistry

```python
from agent_runtime.tools import ToolRegistry
from my_tools.weather import WeatherTool

registry = ToolRegistry()              # 或直接使用 DynamicToolRegistry
registry.register(WeatherTool.spec, WeatherTool())
```

或在 `create_agent_module()` 时注入：

```python
from agent_runtime import create_agent_module
from agent_runtime.tools import ToolRegistry
from my_tools.weather import WeatherTool

tool_registry = ToolRegistry()
tool_registry.register(WeatherTool.spec, WeatherTool())

module = create_agent_module(tool_registry=tool_registry)
```

### 2.3 设计建议

- **`spec` 定义为 class-level 属性**：与 built-in tools（`KnowledgeSearchTool`、`TimeNowTool`、`CalculatorTool`）保持一致，方便扫描和注册。
- **`execute` 永远不向外抛异常**：所有错误通过 `ToolResult(status="error", error_message=...)` 返回。`ToolExecutor` 本身已有隔离，但 handler 内部自己处理错误能给 LLM 更有意义的错误描述。
- **`timeout_seconds` 设置合理值**：远程 API 调用建议 10~30s；本地计算建议 5s 以内。
- **`tags` 分类工具**：例如 `{"read_only"}`（只读）、`{"write"}`（写操作）、`{"rag"}`（知识检索）。`ToolBinding` 可用 tags 实现额外过滤（未来扩展）。

---

## 三、实现 HTTP 外部工具（External Tool）

当工具逻辑在独立微服务中（如 Node.js / Go / Java 实现），可通过 `HttpToolHandler` 以标准 HTTP 协议接入。

### 3.1 最小示例

```python
# my_tools/order_query.py
from agent_runtime.tools import ToolSpec
from agent_runtime.tools.external import ExternalToolConfig, HttpToolHandler

class OrderQueryTool(HttpToolHandler):
    spec = ToolSpec(
        name="order.query",
        description="查询订单状态。",
        parameters_schema={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号"},
            },
            "required": ["order_id"],
        },
        tags=frozenset({"external", "read_only"}),
        timeout_seconds=15.0,
    )

    def __init__(self) -> None:
        super().__init__(
            config=ExternalToolConfig(
                endpoint_url="http://order-service/v1/tools/order.query",
                auth_header="X-Tool-Api-Key",
                credential_key="ORDER_TOOL_SECRET",  # 从环境变量读取
            ),
        )
```

### 3.2 远端服务协议

外部工具服务需实现一个 `POST` 端点，接收以下 JSON：

```json
{
    "arguments": { "order_id": "ORD-12345" },
    "context": {
        "session_id": "sess-abc",
        "trace_id": "trace-xyz",
        "agent_key": "customer-support"
    }
}
```

成功时返回：

```json
{
    "output": "订单 ORD-12345 状态：已发货，预计明日送达",
    "structured_data": { "status": "shipped", "eta": "2026-04-08" }
}
```

失败时返回（HTTP 200 + error_message）：

```json
{
    "output": "",
    "error_message": "订单不存在"
}
```

或直接返回 HTTP 4xx/5xx（`HttpToolHandler` 会将其映射为 `status="error"`）。

### 3.3 凭证注入

- `ExternalToolConfig.credential_key` 指定环境变量名
- 运行时从 `os.environ` 读取，通过 `auth_header` 注入请求头
- **生产环境**：通过 Kubernetes Secret 等注入环境变量，不要硬编码
- `credential_key=None` 时不注入凭证（仅用于开发/测试）

### 3.4 外部工具标签要求

`HttpToolHandler` 的子类必须在 `spec.tags` 中包含 `"external"`，否则实例化时会报 `ValueError`。这是设计约束，确保运维人员能通过 `/v1/tools` API 和标签系统区分进程内工具和远程工具。

---

## 四、工具发现 API（GET /v1/tools）

`agent_service` 暴露了 `GET /v1/tools` 端点，返回当前运行时注册的所有工具：

```json
{
    "tools": [
        {
            "name": "knowledge_search",
            "description": "Search the knowledge base for relevant information.",
            "tags": ["rag", "read_only"],
            "parameters_schema": { ... },
            "timeout_seconds": 10.0,
            "max_retries": 0,
            "is_idempotent": true
        },
        {
            "name": "order.query",
            "description": "查询订单状态。",
            "tags": ["external", "read_only"],
            ...
        }
    ],
    "count": 2
}
```

`.NET` 管理面在发布 agent definition 时可调用此端点，校验 `agent_tool_bindings` 中的 `tool_name` 在 Python 侧已注册。

---

## 五、通过 Agent Definition 控制工具可见性

工具注册后默认对所有 agent 可见。通过 `.NET` 管理面的 `agent_tool_bindings` 表，可以：

| `invocation_mode` | 效果 |
|-------------------|------|
| `auto` | 工具出现在 LLM function-calling schema，LLM 可自主选择调用 |
| `manual_only` | 工具已注册但不注入 LLM schema（未来用于手动触发场景） |
| `disabled` | 工具对该 agent 完全不可见 |

`ToolBinding.description` 可覆盖 `ToolSpec.description`，为不同 agent 提供不同的工具描述文案。

---

## 六、内置工具参考

| 工具 | 名称 | 描述 |
|------|------|------|
| `KnowledgeSearchTool` | `knowledge_search` | 向量知识库检索，通过 `KnowledgeProvider` 注入后端 |
| `TimeNowTool` | `time_now` | 返回当前 UTC 时间（ISO 8601 格式）|
| `CalculatorTool` | `calculator` | 安全的算术表达式求值（不支持 `exec`/`eval` 代码）|

默认情况下只有 `knowledge_search` 自动注册（受 `settings.enable_knowledge_tool` 控制）。`TimeNowTool` 和 `CalculatorTool` 可按需手动注册：

```python
from agent_runtime.tools import ToolRegistry, TimeNowTool, CalculatorTool

registry = ToolRegistry()
registry.register(TimeNowTool.spec, TimeNowTool())
registry.register(CalculatorTool.spec, CalculatorTool())
```

---

## 七、测试自定义工具

工具实现推荐独立单元测试：

```python
import pytest
from agent_runtime.tools import ToolExecutionContext, ToolExecutor, DynamicToolRegistry
from my_tools.weather import WeatherTool

@pytest.mark.asyncio
async def test_weather_tool_happy_path(mocker):
    tool = WeatherTool()
    mocker.patch.object(tool, "_fetch_temp", return_value=23.5)

    ctx = ToolExecutionContext(session_id="s", trace_id="t")
    result = await tool.execute({"city": "Shanghai"}, ctx)

    assert result.status == "success"
    assert "23.5" in result.output

@pytest.mark.asyncio
async def test_weather_tool_timeout_handled():
    """ToolExecutor 超时后返回 status='timeout'，不抛异常。"""
    import asyncio
    from agent_runtime.tools import ToolSpec

    class SlowTool:
        async def execute(self, arguments, context):
            await asyncio.sleep(999)

    spec = ToolSpec(
        name="slow",
        description="",
        parameters_schema={"type": "object"},
        timeout_seconds=0.01,
    )
    reg = DynamicToolRegistry()
    reg.register(spec, SlowTool())

    executor = ToolExecutor()
    ctx = ToolExecutionContext(session_id="s", trace_id="t")
    result = await executor.execute(reg, "slow", {}, ctx)

    assert result.status == "timeout"
```
