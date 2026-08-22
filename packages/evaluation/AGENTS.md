# evaluation — 评估框架

> **定位**：AgentLabKit 的评估框架。提供数据集(EvalCase)、可插拔指标(Metric)、Judge 协议，由 EvaluationRunner 编排单条/批量评估并汇总结果。支持 **Provider 抽象层**（RAGAS v0.4.3）和 **Legacy Judge 模式**双路径。

## 系统中的角色

```
backend (main.py lifespan 初始化 + modules/evaluation HTTP 层 + adapters)
                    │
                    ▼
               evaluation  ← 本包
        (EvaluationRunner · EvalProvider Protocol · ProviderRegistry · Judge Protocol)
                    ▲
                    │  实现
    ┌───────────────┴──────────────────────────────────┐
    │  backend/modules/evaluation/adapters.py           │
    │  ├── GatewayJudge (llm_gateway, legacy)           │
    │  ├── AgentTargetExecutor                          │
    │  └── RagTargetExecutor                            │
    ├───────────────────────────────────────────────────┤
    │  backend/runtime/web_modules.py                   │
    │  └── build_evaluation_module()                    │
    │      └── 自动注册 RAGASEvalProvider(gateway)      │
    └───────────────────────────────────────────────────┘
```

- 被 `backend/src/main.py` 通过 `create_evaluation_module(judge=..., provider_registry=..., settings=...)` 初始化。
- `build_evaluation_module(gateway_service)` 在 gateway 可用时自动注册 RAGAS provider 为默认。
- gateway 不可用时静默降级到 legacy Judge + 内置 Metric。

## 架构：Provider 双模式

```
EvaluationRunner
     │
     ├─ provider_registry 不为空 → Provider 模式（推荐）
     │    └─ RAGASEvalProvider.evaluate()
     │         └─ _ensure_llm() → gateway.resolve_provider_config()
     │              → _build_ragas_llm() → ragas.evaluate()
     │
     └─ provider_registry 为空 → Legacy 模式（向后兼容）
          └─ Judge.score() + 内置 Metric (deprecated)
```

## 目录结构

```
packages/evaluation/src/evaluation/
├── __init__.py              # 公开 API 导出
├── config.py                # EvaluationSettings (EVALUATION_ 前缀)
├── contracts.py             # EvalCase / EvalRunConfig / EvalMetricResult / EvalRunResult / TargetExecutor
├── judge.py                 # Judge Protocol + JUDGE_SYSTEM_PROMPT（legacy）
├── runner.py                # EvaluationRunner — 双模式评估编排器
├── module.py                # EvaluationModule + create_evaluation_module() 工厂
├── providers/               # Provider 抽象层
│   ├── __init__.py
│   ├── base.py              # EvalMetric Protocol + EvalProvider Protocol
│   ├── registry.py          # ProviderRegistry — 注册/发现/配置驱动切换
│   ├── ragas_provider.py    # RAGASEvalProvider — RAGAS v0.4.3 实现
│   └── ragas_metrics.py     # 中文 metric（faithfulness_cn / answer_relevancy_cn / context_relevance_cn）
└── metrics/                 # Legacy 内置指标（deprecated）
    ├── __init__.py
    └── base.py              # Metric Protocol + 3 个 deprecated 指标
```

## 核心接口

### EvalProvider Protocol (`providers/base.py`)

```python
@runtime_checkable
class EvalMetric(Protocol):
    name: str
    provider: str
    async def score(self, case: EvalCase) -> float: ...

@runtime_checkable
class EvalProvider(Protocol):
    name: str
    def get_metric(self, metric_name: str) -> EvalMetric: ...
    def list_metrics(self) -> list[str]: ...
    async def evaluate(self, cases: list[EvalCase], metrics: list[str], config: EvalRunConfig) -> EvalRunResult: ...
```

### ProviderRegistry (`providers/registry.py`)

```python
class ProviderRegistry:
    def register(self, provider: EvalProvider, *, default: bool = False) -> None: ...
    def get(self, name: str | None = None) -> EvalProvider: ...
    def list_providers(self) -> list[str]: ...
    def list_all_metrics(self) -> dict[str, list[str]]: ...
```

- 第一个注册的 provider 自动成为默认（除非显式 `default=True`）。
- `get()` 不传名称时返回默认 provider。

### RAGASEvalProvider (`providers/ragas_provider.py`)

```python
class RAGASEvalProvider:
    name = "ragas"

    def __init__(
        self,
        *,
        model_name: str = "gpt-4o",
        provider_config: Any | None = None,     # RuntimeProviderConfig
        gateway_service: Any | None = None,      # GatewayService（懒解析）
        llm: Any | None = None,                  # 直接注入 RAGAS LLM
        metrics: dict[str, Any] | None = None,   # 自定义 metric
    ) -> None
```

**三种初始化方式**（优先级：`llm` > `provider_config` > `gateway_service`）：

1. **直接注入 LLM**：`RAGASEvalProvider(llm=ragas_llm)`
2. **传入 provider_config**：`RAGASEvalProvider(provider_config=runtime_config)`
3. **传入 gateway_service**（推荐，懒解析）：`RAGASEvalProvider(gateway_service=gw)`

`gateway_service` 模式下，首次调用 `evaluate()` 时通过 `gateway_service.resolve_provider_config()` 获取凭证，构建 OpenAI/Anthropic SDK client，再通过 `ragas.llm_factory()` 创建 RAGAS LLM。

**支持的 metric**：

| Metric | RAGAS 类 | 说明 |
|--------|----------|------|
| `faithfulness` | `Faithfulness` | 回答是否忠于上下文 |
| `answer_relevancy` | `AnswerRelevancy` | 回答与问题的相关性 |
| `context_precision` | `ContextPrecision` | 检索上下文的精确度 |

### 中文 Metric (`providers/ragas_metrics.py`)

```python
create_faithfulness_cn(llm)        # DiscreteMetric: faithful / partial / unfaithful
create_answer_relevancy_cn(llm)    # RubricsScore: 1-5 分
create_context_relevance_cn(llm)   # DiscreteMetric: relevant / partial / irrelevant
create_all_cn_metrics(llm)         # 一次性创建全部
```

### EvaluationRunner (`runner.py`)

```python
class EvaluationRunner:
    def __init__(
        self,
        *,
        judge: Judge | None = None,                    # legacy 模式
        max_concurrent: int = 5,
        provider_registry: ProviderRegistry | None = None,  # provider 模式
        provider_name: str | None = None,
    ) -> None
```

- `provider_registry` 不为空时走 provider 模式。
- `provider_registry` 为空时降级到 legacy Judge + 内置 Metric。
- `run_single_case()` / `run_batch()` 自动选择路径。

### Legacy Metric（deprecated）

```python
class AnswerRelevanceMetric: ...    # deprecated → RAGAS AnswerRelevancy
class FaithfulnessMetric: ...       # deprecated → RAGAS Faithfulness
class ContextRelevanceMetric: ...   # deprecated → RAGAS ContextPrecision
```

`__init__` 触发 `DeprecationWarning`，功能不变。

### Judge Protocol（legacy）

```python
@runtime_checkable
class Judge(Protocol):
    async def score(self, *, prompt: str, rubric: str) -> tuple[float, str]: ...
```

### TargetExecutor Protocol

```python
@runtime_checkable
class TargetExecutor(Protocol):
    target_type: str  # "agent" | "rag_pipeline"
    async def execute(self, case: EvalCase, config: EvalRunConfig) -> str: ...
```

### 工厂 (`module.py`)

```python
def create_evaluation_module(
    *,
    judge: Judge | None = None,
    target_executor: TargetExecutor | None = None,
    settings: EvaluationSettings | None = None,
    provider_registry: ProviderRegistry | None = None,
    provider_name: str | None = None,
) -> EvaluationModule
```

## 配置

| Settings 类 | env 前缀 | 关键字段 | 默认值 |
|------|------|------|------|
| `EvaluationSettings` | `EVALUATION_` | `enabled`、`default_judge_model`、`max_concurrent_cases` | `True`、`""`、`5` |

## 依赖

### 内部

- `agentlabkit-db`（硬依赖）

### 外部

- `pydantic`、`pydantic-settings`
- `ragas>=0.4.3,<0.5`、`datasets>=3.0`（RAGAS provider 依赖）

本包不依赖 `llm_gateway`、`agent_runtime`、`retrieval`。所有外部集成通过 Protocol 解耦，具体适配器在 backend 层实现。

## 测试

```bash
cd packages/evaluation
python -m pytest tests/ -v   # 34 tests
```

| 测试文件 | 数量 | 覆盖 |
|----------|------|------|
| `test_provider_registry.py` | 8 | Registry CRUD、默认选择、边界条件 |
| `test_ragas_provider.py` | 12 | Provider mock、懒解析、异常处理、聚合 |
| `test_runner_provider.py` | 8 | Provider/Legacy 双模式、metric 解析 |
| `test_deprecated_metrics.py` | 5 | deprecated 警告、向后兼容 |

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [backend/AGENTS.md](../../backend/AGENTS.md) — 评估 HTTP 路由、数据集/运行表、适配器
- [docs/plans/evaluation-provider-abstraction.md](../../docs/plans/evaluation-provider-abstraction.md) — Provider 抽象化完整实施计划
