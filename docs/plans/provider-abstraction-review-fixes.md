# Provider 抽象化 Review 修复计划

> 状态：**待实施**
> 创建时间：2026-08-22
> 来源：evaluation + memory provider abstraction code review

## 背景

evaluation（RAGAS v0.4.3）和 memory（Mem0）的 provider 抽象化已完成初步实施（12 commits, +2472 行），但 review 发现 6 个 Critical + 13 个 Warning 级别问题需修复。

## 修复清单

---

### 🔴 Critical — 第一批（阻塞使用）

#### Fix 1: Mem0 ID 映射断裂

**文件**: `packages/memory/src/memory/providers/mem0_provider.py`

**问题**: `save()` 把 Mem0 UUID hash 成 int（`hash(mem.get("id", "")) % (2**31)`），但 `get()`/`delete()` 把 int 传回 Mem0，Mem0 期望自己的 UUID string，永远查不到。

**修复方案**: 存 Mem0 UUID 原始值，建立 int ↔ UUID 双向映射。

```python
# 方案 A: 在 MemoryRecord 中存原始 UUID（推荐）
# store 层用 int ID，但 Mem0StoreAdapter 内部维护 uuid 映射

class Mem0StoreAdapter:
    def __init__(self, provider: "Mem0MemoryProvider"):
        self._provider = provider
        self._id_map: dict[int, str] = {}  # int_id -> mem0_uuid
        self._reverse_map: dict[str, int] = {}  # mem0_uuid -> int_id
        self._counter = 0

    def _to_int_id(self, mem0_uuid: str) -> int:
        if mem0_uuid in self._reverse_map:
            return self._reverse_map[mem0_uuid]
        self._counter += 1
        int_id = self._counter
        self._id_map[int_id] = mem0_uuid
        self._reverse_map[mem0_uuid] = int_id
        return int_id

    def _to_mem0_id(self, int_id: int) -> str | None:
        return self._id_map.get(int_id)

    async def save(self, record: MemoryRecord) -> int:
        client = self._provider._get_client()
        metadata = {"type": record.type, ...}
        result = await asyncio.to_thread(
            client.add,
            [{"role": "user", "content": record.content}],
            user_id=record.user_id,
            metadata=metadata,
        )
        mem0_id = result.get("id", "")
        return self._to_int_id(mem0_id)

    async def get(self, memory_id: int) -> MemoryRecord | None:
        mem0_id = self._to_mem0_id(memory_id)
        if not mem0_id:
            return None
        client = self._provider._get_client()
        result = await asyncio.to_thread(client.get, mem0_id)
        ...
```

#### Fix 2: Mem0 SDK 同步调用阻塞事件循环

**文件**: `packages/memory/src/memory/providers/mem0_provider.py`

**问题**: 所有 `client.add()`, `client.search()`, `client.get_all()`, `client.get()`, `client.delete()` 都是同步调用，直接在 async 方法里阻塞事件循环。

**修复方案**: 全部包装 `asyncio.to_thread()`。

```python
# 修改前
result = client.add(messages, user_id=record.user_id, metadata=metadata)

# 修改后
result = await asyncio.to_thread(
    client.add, messages, user_id=record.user_id, metadata=metadata
)
```

需要修改的方法：
- `save()` → `client.add()`
- `search()` → `client.search()`
- `list_by_user()` → `client.get_all()`
- `get()` → `client.get()`
- `deactivate()` → `client.delete()`

#### Fix 3: `provider.initialize()` 从未调用

**文件**: `packages/memory/src/memory/module.py`

**问题**: `create_memory_module()` 调用 `provider.get_store()` 和 `provider.get_extractor()` 但从未调用 `await provider.initialize()`。配置错误延迟到首次使用才暴露。

**修复方案**: 在 `create_memory_module()` 开头调用 `await provider.initialize()`。

```python
async def create_memory_module(
    settings: MemorySettings,
    gateway_service: Any = None,
    db_session_factory: Any = None,
    embedding_provider: Any = None,
    provider_registry: Any = None,
) -> MemoryModule:
    # 选择 provider
    if provider_registry:
        provider = provider_registry.get(settings.provider)
    else:
        provider = _create_legacy_provider(...)

    # 确保 provider 初始化
    await provider.initialize()  # <-- 新增

    store = provider.get_store()
    extractor = provider.get_extractor()
    ...
```

#### Fix 4: `run_batch()` 返回形状 breaking change

**文件**: `packages/evaluation/src/evaluation/runner.py`

**问题**: provider 模式返回单元素 list `[result]`，legacy 模式返回 per-case list。下游遍历行为不一致。

**修复方案**: provider 的 `evaluate()` 返回 per-case 结果 list，与 legacy 行为一致。

```python
# runner.py - run_batch() 修改
async def run_batch(self, cases: list[EvalCase], ...) -> list[EvalRunResult]:
    if self._provider:
        # provider.evaluate() 已返回 list[EvalRunResult]
        return await self._provider.evaluate(cases, metrics, config)
    else:
        # legacy 模式不变
        ...
```

```python
# ragas_provider.py - evaluate() 修改
async def evaluate(
    self,
    cases: list[EvalCase],
    metrics: list[str],
    config: EvalRunConfig,
) -> list[EvalRunResult]:  # 返回 per-case 结果
    # 构建 dataset
    dataset = EvaluationDataset.from_list([...])

    # 调用 RAGAS
    result = await asyncio.to_thread(
        ragas.evaluate, dataset=dataset, metrics=selected_metrics, llm=self._llm
    )

    # 拆分为 per-case 结果
    results = []
    for i, case in enumerate(cases):
        scores = {m: result[m][i] for m in metrics if m in result}
        results.append(EvalRunResult(
            case_id=case.id,
            scores=scores,
            provider="ragas",
        ))
    return results
```

#### Fix 5: `_RAGASMetricAdapter.score()` 违反 Protocol

**文件**: `packages/evaluation/src/evaluation/providers/ragas_provider.py`

**问题**: `score()` 抛 `NotImplementedError`，但 `EvalMetric` Protocol 要求实现。

**修复方案**: 正确实现 `score()`，或者不声称实现 Protocol（用普通 class 而非 Protocol conformance）。

```python
# 方案 A: 实现 score()（推荐）
class _RAGASMetricAdapter:
    def __init__(self, name: str, ragas_metric, llm):
        self.name = name
        self.provider = "ragas"
        self._ragas_metric = ragas_metric
        self._llm = llm

    async def score(self, case: EvalCase) -> float:
        """单个 case 评分 — 构造最小 dataset 调用 RAGAS"""
        dataset = EvaluationDataset.from_list([{
            "user_input": case.input,
            "retrieved_contexts": case.contexts or [],
            "response": case.response or "",
            "reference": case.expected_output or "",
        }])
        result = await asyncio.to_thread(
            ragas.evaluate,
            dataset=dataset,
            metrics=[self._ragas_metric],
            llm=self._llm,
        )
        return float(result[self.name][0])
```

#### Fix 6: `_aggregate_results()` 死代码

**文件**: `packages/evaluation/src/evaluation/providers/ragas_provider.py`

**问题**: 定义了 `_aggregate_results()` 但从未调用。

**修复方案**: 删除该函数及其测试。如果 Fix 4 采用 per-case 方案，聚合逻辑不需要了。

---

### 🟡 Warning — 第二批（质量保障）

#### Fix 7: RAGAS 改为 optional dependency

**文件**: `packages/evaluation/pyproject.toml`

```toml
[project]
dependencies = [
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "sqlalchemy[asyncio]>=2.0",
    "agentlabkit-db>=0.1",
]

[project.optional-dependencies]
ragas = [
    "ragas>=0.4.3,<0.5",
    "datasets>=3.0,<4.0",
]
```

在 `ragas_provider.py` 和 `ragas_metrics.py` 顶部：
```python
try:
    import ragas
    from ragas.llms import llm_factory
    from ragas import evaluate, EvaluationDataset
except ImportError:
    raise ImportError(
        "RAGAS provider requires 'ragas' package. "
        "Install with: pip install agentlabkit-evaluation[ragas]"
    )
```

#### Fix 8: metric 名称映射修复

**文件**: `packages/evaluation/src/evaluation/runner.py`

```python
# _resolve_metric_names 里修复映射
METRIC_NAME_MAP = {
    "answer_relevance": "answer_relevancy",      # RAGAS 用这个名字
    "context_relevance": "context_precision",     # RAGAS 用这个名字
    "faithfulness": "faithfulness",               # 一致
}

def _resolve_metric_names(self, metrics: list[str] | None) -> list[str]:
    if not metrics:
        return list(self._builtin_metrics.keys())
    resolved = []
    for m in metrics:
        mapped = METRIC_NAME_MAP.get(m, m)
        resolved.append(mapped)
    return resolved
```

#### Fix 9: `ragas_metrics.py` 类型标注和分数范围

**文件**: `packages/evaluation/src/evaluation/providers/ragas_metrics.py`

```python
# 修复类型标注
def create_context_relevance_cn(llm) -> DiscreteMetric:  # 不是 -> None
    ...

# 修复分数范围 — RubricsScore 用 0-1 而非 1-5
def create_answer_relevancy_cn(llm) -> RubricsScore:
    return RubricsScore(
        name="answer_relevancy_cn",
        rubrics={
            "1.0": "回答与问题高度相关，完全解答了问题",
            "0.75": "回答与问题大部分相关，基本解答了问题",
            "0.5": "回答与问题部分相关，但有明显遗漏",
            "0.25": "回答与问题关联度低，未有效解答",
            "0.0": "回答与问题无关",
        },
        llm=llm,
    )
```

#### Fix 10: `web_modules.py` 错误处理

**文件**: `backend/src/runtime/web_modules.py`

```python
# 修改前
except Exception:
    registry = None

# 修改后
except Exception:
    logger.warning(
        "RAGAS evaluation provider init failed; falling back to legacy",
        exc_info=True,
    )
    registry = None
```

#### Fix 11: Mem0 `get_store()` 缓存

**文件**: `packages/memory/src/memory/providers/mem0_provider.py`

```python
def __init__(self, ...):
    ...
    self._store = Mem0StoreAdapter(self)      # 缓存
    self._extractor = _Mem0NoOpExtractor()    # 缓存

def get_store(self) -> MemoryStore:
    return self._store

def get_extractor(self) -> MemoryExtractor:
    return self._extractor
```

#### Fix 12: Mem0 `os.environ.setdefault` 副作用

**文件**: `packages/memory/src/memory/providers/mem0_provider.py`

```python
# 修改前
os.environ.setdefault("OPENAI_API_KEY", self._config.get("api_key", ""))

# 修改后: 通过 Mem0 config dict 传递，不污染全局环境
# 如果 Mem0 SDK 支持 config 里传 api_key，用那个方式
# 如果不支持，在文档中说明这个副作用
```

#### Fix 13: `web_modules.py` 访问私有属性

**文件**: `backend/src/runtime/web_modules.py`

```python
# 修改前
registry._default = "native"

# 修改后
registry.register(native_provider, default=True)
```

#### Fix 14: `_DummyExtractor` 重复定义

**文件**: `packages/memory/src/memory/module.py` 和 `packages/memory/src/memory/providers/native_provider.py`

**修复**: 提取到 `packages/memory/src/memory/providers/_common.py`，两处 import。

#### Fix 15: `search()` 忽略 embedding 参数

**文件**: `packages/memory/src/memory/providers/mem0_provider.py`

**修复**: 文档说明 Mem0 自行处理 embedding，此参数为 Protocol 兼容保留。

#### Fix 16: 拼写错误

**文件**: `packages/memory/src/memory/config.py` line 30

```python
# 修改前
"episodoc"

# 修改后
"episodic"
```

---

### 🟢 Suggestion — 第三批（可选改进）

#### Fix 17: `_build_ragas_llm` 补测试

**文件**: `packages/evaluation/tests/test_ragas_provider.py`

添加测试覆盖 OpenAI / Anthropic / fallback 三条路径。

#### Fix 18: `ragas_metrics.py` 补测试

**文件**: 新建 `packages/evaluation/tests/test_ragas_metrics.py`

测试中文 metric 创建和返回值。

#### Fix 19: `_NullEmbeddingProvider` 维度对齐

**文件**: `packages/memory/src/memory/module.py`

维度应从配置读取，而非硬编码 1024。

---

## 实施顺序

```
Fix 1 (ID映射) → Fix 2 (async) → Fix 3 (initialize)  [Memory Critical]
Fix 4 (run_batch) → Fix 5 (score) → Fix 6 (死代码)    [Evaluation Critical]
Fix 7 (optional dep) → Fix 8 (metric名) → Fix 9 (类型) [Evaluation Warning]
Fix 10 (错误处理) → Fix 11-16 (其余 Warning)            [Warning 收尾]
Fix 17-19 (测试补充)                                    [可选]
```

## 验证标准

1. `pytest packages/evaluation/tests/` 全部通过
2. `pytest packages/memory/tests/` 全部通过（如果有的话）
3. `Mem0StoreAdapter` 的 `save()` → `get()` → `deactivate()` 链路可通
4. `run_batch()` 在 provider 和 legacy 模式下返回相同形状
5. `import evaluation` 不强制要求 ragas 已安装（lazy import）
6. Mem0 SDK 调用不阻塞事件循环（可用 `asyncio.to_thread` 验证）

## 参考

- Review 原始输出: 本会话 conversation history
- 实施计划: `docs/plans/evaluation-provider-abstraction.md`
