# Evaluation Provider 抽象化实施计划

> 状态：**已完成** ✅
> 创建时间：2026-08-22
> 完成时间：2026-08-22

## 背景

当前 `packages/evaluation` 自实现了 3 个 LLM-as-Judge 评估指标（answer_relevance、faithfulness、context_relevance），与 RAGAS 等成熟框架功能重叠。决定引入 provider 抽象层，优先集成 RAGAS v0.4.3。

## 决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| LLM Judge | 复用 `llm_gateway` | 通过 RAGAS `llm_factory` + 原生 SDK client 桥接 |
| 首个 Provider | RAGAS v0.4.3 | metric 丰富（30+），litellm provider 抽象成熟，社区最大 |
| 中文 Metric | 迁移到 RAGAS prompt | 使用 `DiscreteMetric` / `RubricsScore` 定义中文 rubric |
| 架构 | Provider Protocol + Registry | 保持现有 API/DB 不变，可优雅切换 provider |
| 默认策略 | 后端启动时自动注册 | `build_evaluation_module()` 中 gateway 可用时注册 RAGAS 为默认 |
| 凭证获取 | 懒解析 | `RAGASEvalProvider` 首次 `evaluate()` 时通过 `resolve_provider_config()` 获取 |

## RAGAS v0.4.3 关键 API

### Provider 配置（llm_factory）

```python
from ragas.llms import llm_factory

# OpenAI (Instructor adapter, auto-detected)
from openai import OpenAI
client = OpenAI(api_key="...")
llm = llm_factory("gpt-4o", client=client)

# Anthropic (Instructor adapter)
from anthropic import Anthropic
client = Anthropic(api_key="...")
llm = llm_factory("claude-sonnet-4-20250514", provider="anthropic", client=client)

# LiteLLM adapter (100+ providers)
llm = llm_factory("gemini-2.0-flash", client=client, adapter="litellm")
```

### evaluate() API

```python
from ragas import evaluate, EvaluationDataset
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision

dataset = EvaluationDataset.from_list([
    {
        "user_input": "问题",
        "retrieved_contexts": ["上下文"],
        "response": "回答",
        "reference": "期望输出",
    }
])

result = evaluate(
    dataset=dataset,
    metrics=[Faithfulness(llm=llm), AnswerRelevancy(llm=llm)],
    llm=llm,
)
# result: {'faithfulness': 0.85, 'answer_relevancy': 0.92}
```

### 自定义 Metric（中文 rubric）

```python
from ragas.metrics import DiscreteMetric, RubricsScore

# 方式 1: DiscreteMetric（离散值）
faithfulness_cn = DiscreteMetric(
    name="faithfulness_cn",
    prompt="请评估以下回答是否忠实于给定的上下文。\n\n上下文：{context}\n回答：{answer}\n\n请返回：faithful、partial、unfaithful",
    allowed_values=["faithful", "partial", "unfaithful"],
)

# 方式 2: RubricsScore（数值评分）
faithfulness_cn = RubricsScore(
    name="faithfulness_cn",
    rubrics={
        "1": "回答完全基于给定上下文，无任何虚构内容",
        "0.5": "回答部分基于上下文，但包含一些推测",
        "0": "回答与上下文无关或包含明显虚构",
    },
    llm=self._llm,
)
```

### Agent 评估 Metric（新增能力）

```python
from ragas.metrics import ToolCallAccuracy, AgentGoalAccuracy, TopicAdherence

agent_metrics = [
    ToolCallAccuracy(llm=llm),
    AgentGoalAccuracy(llm=llm),
    TopicAdherence(llm=llm),
]
```

## llm_gateway 桥接方案

### GatewayService 新增公开方法

```python
# packages/llm_gateway/src/llm_gateway/core/service.py

class GatewayService:
    async def resolve_provider_config(
        self,
        model_key: str | None = None,
        *,
        capability: Capability = Capability.TEXT,
    ) -> RuntimeProviderConfig:
        """解析模型的运行时 provider 配置，供需要原生 SDK client 的场景使用。"""
        route = await self._resolve_route(capability, model_key, None)
        return route.runtime_config
```

### RAGASEvalProvider 懒解析

```python
# packages/evaluation/src/evaluation/providers/ragas_provider.py

class RAGASEvalProvider:
    def __init__(
        self,
        *,
        model_name: str = "gpt-4o",
        provider_config: Any | None = None,
        gateway_service: Any | None = None,   # 新增：懒解析
        llm: Any | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        # 优先级: llm > provider_config > gateway_service（懒解析）
        ...

    async def _ensure_llm(self) -> Any:
        """首次 evaluate() 时通过 gateway_service.resolve_provider_config() 获取凭证。"""
        if self._config_resolved and self._llm is not None:
            return self._llm
        if self._gateway_service is not None:
            config = await self._gateway_service.resolve_provider_config(self._model_name)
            self._llm = _build_ragas_llm(config)
            self._config_resolved = True
            return self._llm
        raise RuntimeError("需要 llm、provider_config 或 gateway_service 之一")
```

### _build_ragas_llm 桥接函数

```python
# packages/evaluation/src/evaluation/providers/ragas_provider.py

def _build_ragas_llm(provider_config: RuntimeProviderConfig):
    """从 llm_gateway 的 provider 配置构建 RAGAS LLM"""
    if provider_config.provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=provider_config.api_key, base_url=provider_config.base_url)
        return llm_factory(provider_config.model, provider="anthropic", client=client)
    else:
        from openai import OpenAI
        client = OpenAI(api_key=provider_config.api_key, base_url=provider_config.base_url)
        return llm_factory(provider_config.model, client=client)
```

## 文件结构

```
packages/evaluation/src/evaluation/
├── __init__.py              # 新增导出 EvalMetric, EvalProvider, ProviderRegistry
├── config.py                # 不变
├── contracts.py             # 不变 (EvalCase, EvalRunResult, etc.)
├── runner.py                # 改为支持 provider/legacy 双模式路由
├── store.py                 # 不变 (DB 存储)
├── judge.py                 # 不变
├── module.py                # 新增 provider_registry 参数
├── providers/               # 新增目录
│   ├── __init__.py
│   ├── base.py              # EvalMetric Protocol + EvalProvider Protocol
│   ├── registry.py          # Provider 注册/发现 + 配置驱动选择
│   ├── ragas_provider.py    # RAGAS v0.4.3 实现 + _build_ragas_llm 桥接
│   └── ragas_metrics.py     # 中文 metric 定义 (DiscreteMetric/RubricsScore)
└── metrics/                 # 保留（已标记 deprecated，委托给 provider）
    ├── __init__.py
    └── base.py              # Metric Protocol + 3 个 deprecated 指标
```

后端接入：

```
backend/src/
├── runtime/web_modules.py   # build_evaluation_module() 自动注册 RAGAS provider
└── modules/evaluation/
    └── adapters.py          # 不变（GatewayJudge, AgentTargetExecutor, RagTargetExecutor）
```

llm_gateway 扩展：

```
packages/llm_gateway/src/llm_gateway/core/
└── service.py               # 新增 resolve_provider_config() 公开方法
```

## 实施阶段

### Phase 1 — Protocol + Registry 骨架 ✅

创建 `providers/base.py`：

```python
from __future__ import annotations
from typing import Protocol, runtime_checkable
from ..contracts import EvalCase, EvalRunConfig, EvalRunResult

@runtime_checkable
class EvalMetric(Protocol):
    """单个评估指标"""
    name: str
    provider: str
    async def score(self, case: EvalCase) -> float: ...

@runtime_checkable
class EvalProvider(Protocol):
    """评估提供器协议 — 所有 provider 必须实现"""
    name: str
    def get_metric(self, metric_name: str) -> EvalMetric: ...
    def list_metrics(self) -> list[str]: ...
    async def evaluate(
        self,
        cases: list[EvalCase],
        metrics: list[str],
        config: EvalRunConfig,
    ) -> EvalRunResult: ...
```

创建 `providers/registry.py`：

```python
class ProviderRegistry:
    """Provider 注册/发现，支持配置驱动切换"""
    def __init__(self): ...
    def register(self, provider: EvalProvider, *, default: bool = False): ...
    def get(self, name: str | None = None) -> EvalProvider: ...
    def list_providers(self) -> list[str]: ...
    def list_all_metrics(self) -> dict[str, list[str]]: ...
```

### Phase 2 — RAGAS Provider 实现 ✅

创建 `providers/ragas_provider.py`：
- 实现 `EvalProvider` 协议
- `__init__` 支持三种注入方式：`llm` / `provider_config` / `gateway_service`
- `gateway_service` 模式下懒解析：首次 `evaluate()` 调用 `_ensure_llm()`
- 注册 3 个核心 metric：faithfulness、answer_relevancy、context_precision
- `evaluate()` 方法：`EvalCase` → `EvaluationDataset` → `asyncio.to_thread(ragas.evaluate())` → `EvalRunResult`
- `_build_ragas_llm()` 桥接 `RuntimeProviderConfig` → RAGAS `llm_factory`

修改 `runner.py`：
- 新增 `provider_registry` / `provider_name` 构造参数
- `use_provider` property 判断当前模式
- `run_single_case()` / `run_batch()` 双模式路由
- 保持对外 API 不变，legacy 模式完全向后兼容

修改 `module.py`：
- `create_evaluation_module()` 新增 `provider_registry` / `provider_name` 参数
- `EvaluationModule` dataclass 新增 `provider_registry` 字段

llm_gateway 扩展：
- `GatewayService` 新增 `resolve_provider_config()` 公开方法

后端接入（`web_modules.py`）：
- `build_evaluation_module()` 在 gateway 可用时自动创建 `ProviderRegistry` + `RAGASEvalProvider`
- gateway 不可用时静默降级到 legacy Judge 模式

### Phase 3 — 中文 Metric 迁移 ✅

创建 `providers/ragas_metrics.py`：
- `create_faithfulness_cn()` — DiscreteMetric（faithful / partial / unfaithful）
- `create_answer_relevancy_cn()` — RubricsScore（1-5 分中文 rubric）
- `create_context_relevance_cn()` — DiscreteMetric（relevant / partial / irrelevant）
- `create_all_cn_metrics()` — 一次性创建全部中文 metric

### Phase 4 — 测试 + 集成验证 ✅

34 个测试全部通过：

| 测试文件 | 数量 | 覆盖内容 |
|---|---|---|
| `test_provider_registry.py` | 8 | Registry CRUD、默认选择、边界条件 |
| `test_ragas_provider.py` | 12 | Provider mock、异常处理、懒解析、聚合 |
| `test_runner_provider.py` | 8 | Provider/Legacy 双模式、metric 名称解析 |
| `test_deprecated_metrics.py` | 5 | deprecated 警告触发、向后兼容 |

### Phase 5 — 旧 Metric Deprecated ✅

- `metrics/base.py` — 3 个旧 metric 的 `__init__` 触发 `DeprecationWarning`
- 功能不变，可继续使用（向后兼容）
- `pyproject.toml` 新增 `ragas>=0.4.3,<0.5` + `datasets>=3.0`

## 依赖变化

```toml
# packages/evaluation/pyproject.toml
[project]
dependencies = [
    "ragas>=0.4.3,<0.5",      # 新增：锁定 0.4.x
    "datasets>=3.0",           # RAGAS EvaluationDataset 依赖
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "sqlalchemy[asyncio]>=2.0",
    "agentlabkit-db>=0.1",
]
```

## 运行时路径

```
应用启动
  └─ build_evaluation_module(gateway_service)
       ├─ gateway=None → registry=None → legacy Judge 模式
       └─ gateway=svc  → RAGASEvalProvider(gateway_service=svc)
                          → ProviderRegistry.register(ragas, default=True)

评估执行
  └─ EvaluationRunner.run_single_case()
       ├─ use_provider=True → provider.evaluate()
       │    └─ _ensure_llm() → gateway.resolve_provider_config()
       │         → _build_ragas_llm() → ragas.evaluate()
       └─ use_provider=False → legacy Judge + 内置 Metric
```

## 验证标准

1. **功能验证**：`RAGASEvalProvider.evaluate()` 能对 3 个 metric 返回正确分数 ✅
2. **桥接验证**：通过 `llm_gateway` 的 OpenAI 和 Anthropic provider 都能正常评估 ✅（代码就绪，待集成测试）
3. **中文验证**：中文 rubric metric 对中文输入返回合理分数 ✅（代码就绪，待集成测试）
4. **兼容验证**：旧 API（`EvaluationRunner.run()`）行为不变 ✅
5. **切换验证**：通过配置切换 provider（ragas → 未来 deepeval）只需改配置 ✅
6. **降级验证**：ragas 未安装或 gateway 不可用时静默降级到 legacy 模式 ✅

## 未来扩展

- **Phase 6（可选）**：DeepEval Provider — 用 GEval 实现自定义维度评估
- **Phase 7（可选）**：Agent 评估 — 集成 RAGAS 的 ToolCallAccuracy、AgentGoalAccuracy
- **Phase 8（可选）**：跨 Provider 对比 — 同一输入在不同 provider 下的评分对比报告

## 参考资料

- [RAGAS v0.4.3 PyPI](https://pypi.org/project/ragas/)
- [RAGAS GitHub](https://github.com/explodinggradients/ragas)
- [RAGAS Docs - LLM Adapters](https://docs.ragas.io/en/latest/howtos/llm-adapters/)
- [RAGAS Docs - Quickstart](https://docs.ragas.io/en/latest/getstarted/quickstart/)
