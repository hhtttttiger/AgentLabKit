# 使用 package 层快速构建 Agent

这条路径面向希望把 AgentLabKit 当作通用开发库使用的项目。它不要求启动 FastAPI、PostgreSQL、Redis 或 Admin frontend；HTTP 服务只是另一种 composition root。

## 边界

```text
你的应用 / composition root
        │
        ├── application use cases（可选）
        ├── agent_runtime（执行事实、tools、guardrails、memory、workflow）
        ├── llm_gateway（唯一 LLM API entrypoint）
        └── retrieval（唯一 document / embedding / vector retrieval engine）
```

Runtime 负责创建 `run_id`、`trace_id`、spans 和 lifecycle events。Replay、Evaluation、projector 和 HTTP adapter 消费这些事实，但不创建 execution identity。`run_id` 也永远不是 DatasetExample 的稳定 `example_id`。

## 安装与组合

从仓库根目录创建开发环境，并按应用需要安装 package。下面的组合覆盖 Runtime、LLM、Retrieval、Evaluation 和 Application use cases：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e packages/agent_runtime -e packages/llm_gateway \
  -e packages/retrieval -e packages/evaluation -e packages/application
```

具体 provider 的可选依赖以对应 package 的 `pyproject.toml` 为准。provider-specific code 应留在 package protocol/adapter 后面；业务代码不应直接调用 OpenAI、Anthropic、向量库或 Mem0 SDK。

## 推荐开发顺序

1. 在 `llm_gateway` 配置模型 provider，在 `retrieval` 配置文档与向量能力。
2. 用 `agent_runtime` 的 `ToolRegistry`、Agent definition、guardrails 和 memory 组合 Agent。
3. 需要平台动作时调用 `packages/application` 的 `ExecuteAgent`、`ReplayRun`、`CaptureRunAsDatasetExample`、`EvaluateDataset` 或 `CompareEvaluationRuns`。
4. 在应用自己的 composition root 中接入 persistence、observability 和业务授权。
5. 只有需要远程 HTTP/SSE 时，才把这些 use cases 接到 `backend` adapter；不要从 FastAPI route 反向定义领域行为。

`ExecuteAgent` 接收 `RunExecutor` port，因此 library-first 应用可以提供自己的 Runtime executor。Application contracts 不是 HTTP DTO，也不要求使用 backend 的 SQLAlchemy store。

## 最小骨架

```python
from agent_runtime import ToolRegistry
from agent_runtime.runtime.factory import create_agent_runtime
from application import ExecuteAgent

registry = ToolRegistry()
# registry.register(...)  # 注册应用自己的 tool adapter
runtime = create_agent_runtime(tool_registry=registry)

# 将 runtime 封装成 application 的 RunExecutor，
# 再把 ExecuteAgent 注入到你的应用 service / CLI / worker。
use_case = ExecuteAgent(executor=runtime_executor, agents=agent_reader)
```

上面的骨架表达 ownership，而不是完整的 provider 配置模板；`runtime_executor` 应由应用组合层实现 `RunExecutor` port，并把 Runtime 返回的 `AgentRun` 原样交给 Application。不要在 executor 外部生成 `run_id`、`trace_id` 或伪造 lifecycle events。

## 何时使用 backend

使用 `backend`，当你需要 authenticated public API、SSE、PostgreSQL persistence、Redis worker、Admin frontend 或多用户资源授权。此时遵守 [`fastapi-adapter-boundary.md`](../architecture/fastapi-adapter-boundary.md)：route 保持薄，平台动作委托 Application use cases，资源 CRUD 使用 module services，读取使用 Readers/Stores/Projections。

进一步阅读：[`packages/application/README.md`](../../packages/application/README.md)、[`execution-model-v2.md`](../architecture/execution-model-v2.md) 和 [`agent-turn-streaming.md`](../architecture/agent-turn-streaming.md)。
