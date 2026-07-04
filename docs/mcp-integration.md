# MCP (Model Context Protocol) 集成

Agent 通过 MCP 协议连接外部工具服务器，自动发现和调用远程工具。

## 架构概览

```
Agent 对话请求
  → BackendAgentDefinitionLoader 加载 AgentDefinitionSnapshot
    → 从 agent_mcp_bindings + agent_mcp_servers 表构建 McpBindingSnapshot
  → TurnPrep._ensure_mcp_for_definition()
    → McpServerConfig.model_validate(server_config_json)
    → McpClientManager.ensure_server(config)
      → stdio: 启动子进程 (npx, uvx, python...)
      → http/sse: 连接远程端点
    → McpRegistryBridge.sync_all()
      → 发现工具 → 适配为 ToolSpec → 注册到 DynamicToolRegistry
  → Agent LLM 调用时自动将 MCP 工具注入 tool schemas
  → LLM 决定调用工具 → ToolExecution 分发 → MCP 远程执行
```

## 传输类型

| transport | 说明 | 必需字段 |
|-----------|------|---------|
| `stdio` | 启动本地子进程，通过 stdin/stdout 通信 | `command`, `argsJson` |
| `http` | streamable HTTP 连接 | `url` |
| `sse` | Server-Sent Events 连接 | `url` |

### stdio 示例

```json
{
  "name": "time",
  "transportType": "stdio",
  "command": "alans-date-time-mcp",
  "argsJson": []
}
```

支持的命令形式：
- 全局安装的 npm 包：`"command": "alans-date-time-mcp"`
- 通过 npx：`"command": "npx"`, `"argsJson": ["-y", "alans-date-time-mcp"]`
- 通过 uvx (Python)：`"command": "uvx"`, `"argsJson": ["mcp-server-time"]`
- 任意可执行文件

### http/sse 示例

```json
{
  "name": "remote-tools",
  "transportType": "sse",
  "url": "http://localhost:8765/sse",
  "headersJson": {"Authorization": "Bearer xxx"}
}
```

## API

所有端点需要认证（Bearer Token）。

### MCP 服务器管理

```
GET    /api/agent-mcp/servers          # 列表
POST   /api/agent-mcp/servers          # 创建
GET    /api/agent-mcp/servers/{name}   # 详情
PUT    /api/agent-mcp/servers/{name}   # 更新
DELETE /api/agent-mcp/servers/{name}   # 删除
```

### Agent 绑定

在创建/更新 Agent 版本时，通过 `mcpBindings` 字段绑定 MCP 服务器：

```json
POST /api/agents/{agentKey}/versions
{
  "systemPromptTemplate": "你有时间工具...",
  "modelKey": "mimo-v2-flash-chat",
  "mcpBindings": [
    {
      "serverName": "time",
      "isEnabled": true,
      "toolWhitelist": ["get_time", "get_date"],
      "configOverrides": {}
    }
  ]
}
```

`toolWhitelist` 为 `null` 表示允许所有工具；设置为列表则只允许指定工具。

## 种子数据

`bootstrap.py` 会自动创建 MCP 示例：

| 资源 | Key/Name | 说明 |
|------|----------|------|
| MCP Server | `time` | stdio 连接 `alans-date-time-mcp` |
| Agent | `mcp-demo` | 已发布，绑定 time server |

### 前置条件

```bash
npm install -g alans-date-time-mcp
```

种子数据是**幂等**的 — 重复运行不会重复创建。

## 工具发现与调用流程

1. **启动时**：`AgentSettings.enable_mcp=True` → `_build_mcp_client_manager()` 创建 `McpClientManager`
2. **每次 Turn**：`TurnPrep._ensure_mcp_for_definition()` 检查 definition 的 `mcp_bindings`
3. **连接**：`McpClientManager.ensure_server(config)` — 如果已连接则复用
4. **工具同步**：`McpRegistryBridge.sync_server()` → 发现工具 → 注册到 `DynamicToolRegistry`
5. **LLM 调用**：MCP 工具注入 tool schemas，LLM 可选择调用
6. **执行**：`ToolExecution` → `McpClientManager.call_tool()` → 返回文本结果

MCP 工具在 registry 中带有标签 `mcp:{server_name}` 和 `mcp`，来源标记为 `source_type="mcp"`。

## 关键配置

### 启用 MCP

在 `main.py` 中：
```python
agent_runtime = create_agent_runtime(
    settings=AgentSettings(enable_mcp=True),
    ...
)
```

或通过环境变量：`AGENT_RUNTIME_ENABLE_MCP=true`

### 相关文件

| 文件 | 作用 |
|------|------|
| `backend/src/modules/agent/models.py` | `AgentMcpServer` / `AgentMcpBinding` ORM |
| `backend/src/modules/agent/schemas.py` | `McpConfigCreate/Update`, `McpBindingItem` |
| `backend/src/modules/agent/mcp_router.py` | MCP CRUD API |
| `backend/src/modules/agent/services/mcp_service.py` | MCP 业务逻辑 |
| `backend/src/modules/agent/definition_loader.py` | DB → `McpBindingSnapshot` 映射 |
| `backend/src/modules/agent/seed.py` | `seed_mcp_demo()` |
| `packages/agent_runtime/src/agent_runtime/mcp/` | MCP 运行时：client, transport, contracts, adapter, registry_bridge |
| `packages/agent_runtime/src/agent_runtime/config/agent.py` | `AgentSettings.enable_mcp` |
| `packages/agent_runtime/src/agent_runtime/runtime/turn_prep.py` | `_ensure_mcp_for_definition()` |

## 故障排查

### Connection closed 错误

stdio transport 最常见的问题：

1. **命令不存在** — 确认可执行文件在 PATH 中
   ```bash
   which alans-date-time-mcp
   ```
2. **npx 首次下载超时** — 先全局安装
   ```bash
   npm install -g alans-date-time-mcp
   ```
3. **命令权限** — 确认可执行

### 工具未出现在 Agent 响应中

1. 确认 MCP server `is_enabled=true`
2. 确认 Agent 版本已发布（`published_version` 非空）
3. 确认 MCP binding `is_enabled=true`
4. 检查后端日志中 `mcp_connected` / `mcp_connect_failed` 消息
5. 检查 `mcp_binding_refers_to_missing_server` 警告

### 验证 MCP 连接

发送对话请求后检查 `toolEvents`：
```json
{
  "toolEvents": [{
    "tool_name": "get_time",
    "source_type": "mcp",
    "source_ref": "time",
    "status": "success"
  }]
}
```

## 推荐 MCP 服务

| 服务 | 安装 | 工具 |
|------|------|------|
| **alans-date-time-mcp** | `npm i -g alans-date-time-mcp` | get_time, get_date, get_datetime (支持时区) |
| **@modelcontextprotocol/server-filesystem** | `npm i -g @modelcontextprotocol/server-filesystem` | read_file, write_file, list_directory |
| **@modelcontextprotocol/server-fetch** | `npm i -g @modelcontextprotocol/server-fetch` | fetch (HTTP 请求) |
| **@modelcontextprotocol/server-memory** | `npm i -g @modelcontextprotocol/server-memory` | 知识图谱记忆 |
| **@modelcontextprotocol/server-sequential-thinking** | `npm i -g @modelcontextprotocol/server-sequential-thinking` | 链式推理 |
