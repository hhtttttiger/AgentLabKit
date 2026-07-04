# evaluation — 评估框架

> **定位**：AgentLabKit 的评估框架。提供数据集(EvalCase)、可插拔指标(Metric)、Judge 协议，由 EvaluationRunner 编排单条/批量评估并汇总结果。包本身零外部依赖（仅定义 Protocol），具体实现由后端适配器提供。

## 系统中的角色

```
backend (main.py lifespan 初始化 + modules/evaluation HTTP 层 + adapters)
                    │
                    ▼
               evaluation  ← 本包（纯协议 + 引擎，零外部依赖）
        (EvaluationRunner · Judge Protocol · Metric Protocol · TargetExecutor Protocol)
                    ▲
                    │  实现
    ┌───────────────┴──────────────────┐
    │  backend/modules/evaluation/     │
    │  adapters.py                     │
    │  ├── GatewayJudge (llm_gateway)  │
    │  ├── AgentTargetExecutor         │
    │  └── RagTargetExecutor           │
    └──────────────────────────────────┘
```

- 被 `backend/src/main.py` 通过 `create_evaluation_module(judge=..., target_executor=..., settings=...)` 初始化，挂到 `app.state.evaluation_module`。
- HTTP 层在 `backend/src/modules/evaluation/`，具体适配器在 `adapters.py`。
- `judge` 和 `target_executor` 均为可选注入：不传则评估时使用 fallback（expected_output 对比）。

## 目录结构

```
packages/evaluation/src/evaluation/
├── __init__.py          # 公开 API 导出
├── config.py            # EvaluationSettings (EVALUATION_ 前缀)
├── contracts.py         # EvalCase / EvalRunConfig / EvalMetricResult / EvalRunResult / TargetExecutor
├── judge.py             # Judge Protocol + JUDGE_SYSTEM_PROMPT 常量
├── runner.py            # EvaluationRunner — 评估执行编排器
├── module.py            # EvaluationModule + create_evaluation_module() 工厂
└── metrics/
    ├── __init__.py
    └── base.py          # Metric Protocol + 内置指标 (answer_relevance / faithfulness / context_relevance)
```

## 核心接口

### EvaluationRunner (`runner.py`)

```python
class EvaluationRunner:
    def __init__(self, *, judge: Judge | None = None, max_concurrent: int = 5) -> None
    async def run_single_case(self, case: EvalCase, config: EvalRunConfig, target_executor: TargetExecutor | None = None) -> EvalRunResult
    async def run_batch(self, cases: list[EvalCase], config: EvalRunConfig, target_executor: TargetExecutor | None = None) -> list[EvalRunResult]
```

- `target_executor` 为 `None` 时，回退到 `case.expected_output` 作为实际输出。
- `judge` 为 `None` 时，指标返回中性分 0.5。

### Judge (`judge.py`)

```python
@runtime_checkable
class Judge(Protocol):
    async def score(self, *, prompt: str, rubric: str) -> tuple[float, str]: ...
```

- 具体实现 `GatewayJudge` 位于 `backend/src/modules/evaluation/adapters.py`，通过 `llm_gateway` 调用 LLM。
- `JUDGE_SYSTEM_PROMPT` 常量供 Judge 实现使用。

### TargetExecutor (`contracts.py`)

```python
@runtime_checkable
class TargetExecutor(Protocol):
    target_type: str  # "agent" | "rag_pipeline"
    async def execute(self, case: EvalCase, config: EvalRunConfig) -> str: ...
```

- 具体实现位于 `backend/src/modules/evaluation/adapters.py`：
  - `AgentTargetExecutor` — 调用 `AgentRuntime.run_turn()`
  - `RagTargetExecutor` — 调用检索 + LLM 直接生成

### Metric (`metrics/base.py`)

```python
@runtime_checkable
class Metric(Protocol):
    name: str
    async def evaluate(self, *, input_text, actual_output, expected_output=None, context=None, judge=None) -> EvalMetricResult: ...

class AnswerRelevanceMetric: ...    # name = "answer_relevance"  — 答案相关性
class FaithfulnessMetric: ...      # name = "faithfulness"      — 忠实度（是否忠于上下文）
class ContextRelevanceMetric: ...   # name = "context_relevance" — 上下文相关性（RAG 检索质量）
```

### 关键数据类 (`contracts.py`)

```python
class EvalCase:          # id, dataset_id, case_index, input_text, expected_output, context, tags, metadata
class EvalRunConfig:     # id, name, dataset_id, target_type("agent"|"rag_pipeline"), target_key, metric_configs, judge_model_binding_key
class EvalMetricResult:  # metric_name, score(0-1), reasoning, passed
class EvalRunResult:     # id, run_id, case_id, actual_output, metric_results, overall_score, error_message, duration_ms
```

### 工厂 (`module.py`)

```python
def create_evaluation_module(
    *,
    judge: Judge | None = None,
    target_executor: TargetExecutor | None = None,
    settings: EvaluationSettings | None = None,
) -> EvaluationModule
```

- `judge`：由调用方（backend main.py）通过 `GatewayJudge(gateway_service, model=...)` 创建后注入。
- `target_executor`：per-run 动态解析，在 `trigger_run` 端点根据 config 的 `target_type` 调用 `create_target_executor()` 工厂创建。
- `settings.max_concurrent_cases` → Runner 并发数。

## 配置

| Settings 类 | env 前缀 | 关键字段 | 默认值 |
|------|------|------|------|
| `EvaluationSettings` | `EVALUATION_` | `enabled`、`default_judge_model`、`max_concurrent_cases` | `True`、`""`、`5` |

## 依赖

### 内部

- `agentlabkit-db`（硬依赖）

### 外部

- `pydantic`、`pydantic-settings`

本包不依赖 `llm_gateway`、`agent_runtime`、`retrieval`。所有外部集成通过 Protocol 解耦，具体适配器在 backend 层实现。

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [backend/AGENTS.md](../../backend/AGENTS.md) — 评估 HTTP 路由、数据集/运行表、适配器
