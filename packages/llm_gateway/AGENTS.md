# llm_gateway — LLM 模型网关

> **定位**：系统**唯一**调用 LLM API 的入口。提供模型统一访问、路由、负载均衡、凭据解析、Usage 提取。任何业务模块需要 LLM 能力时必须依赖此包，不得直接调用 provider API。

## 系统中的角色

```
chat / ai_invoke / knowledge_base / agent_runtime
                    │
                    ▼
              llm_gateway  ← 本包
              (GatewayService · ModelCatalog · Provider 路由)
                    │
                    ▼
              packages/db (ORM 模型)
```

**关键约束**：`llm_gateway` 是系统中**唯一**调用 LLM API 的入口。

## 目录结构

```
packages/llm_gateway/src/llm_gateway/
├── __init__.py               # 公共 API：GatewayService, ModelRef, Capability 等
├── config.py                 # GatewaySettings (AI_GATEWAY_ 前缀)
├── bootstrap.py              # create_gateway_service() 工厂
├── errors.py                 # GatewayError, GatewayErrorCode
├── models.py                 # 请求/响应模型, ModelRef, Capability, ProviderId
├── core/
│   ├── service.py            # GatewayService — 统一调用入口 + 重试/限流/熔断
│   ├── adapters.py           # 抽象适配器接口 (TextAdapter, EmbeddingAdapter 等)
│   ├── registry.py           # ProviderRegistry — provider 适配器注册
│   ├── dispatch.py           # _DispatchSession — 容错调度
│   ├── rate_limiter.py       # TokenBucketRateLimiter — per-instance 令牌桶限流
│   └── circuit_breaker.py    # CircuitBreaker — per-instance 熔断器
├── providers/                # Provider 适配器 (OpenAI, Anthropic)
│   ├── openai/               # OpenAI 适配器
│   └── anthropic/            # Anthropic 适配器
├── model_catalog/            # 模型目录（读侧）
│   ├── service.py            # ModelCatalogService, ModelResolver
│   ├── domain.py             # 领域快照 (ModelSnapshot, ResolvedModelRoute 等)
│   ├── repository.py         # SqlAlchemy / Static 目录仓库
│   ├── cache.py              # InMemoryCatalogCache / NoOpCatalogCache
│   ├── secret_resolver.py    # API Key 凭据解析
│   ├── retry_policy.py       # RetryPolicy (指数退避 + jitter + Retry-After)
│   └── errors.py             # CatalogError, CatalogErrorCode
└── usage/                    # 用量记录
    └── recorder.py           # SqlAlchemyUsageRecorder / NullUsageRecorder
```

## 核心接口

### ModelRef — 模型引用（推荐方式）

`ModelRef` 是指定模型的统一方式，支持三种解析策略：

```python
from llm_gateway import ModelRef, Capability

# 1. 通过场景绑定解析（binding_key → model）
ref = ModelRef.binding("gateway.default_text")

# 2. 直接指定模型 key（model_key → model）
ref = ModelRef.model("gpt-5.4-mini")

# 3. 通过 provider 模型名解析（model_name → model）
ref = ModelRef.name("gpt-5.4-mini")
```

**必须恰好指定一种**，Pydantic 校验器会在运行时强制。

### GatewayService — 统一调用入口

```python
from llm_gateway import GatewayService, TextGenerateRequest

# 文本生成
response = await service.generate_text(TextGenerateRequest(
    model=None,       # None = 使用 capability 对应的默认绑定
    prompt="hello",
))

# 流式文本生成
async for event in service.generate_text_stream(request):
    print(event.delta)

# 其他能力
await service.generate_embedding(request)
await service.transcribe_speech(request)
await service.generate_image(request)
```

请求支持两种模型指定方式：

```python
# 推荐：通过 model_ref 显式指定解析策略
TextGenerateRequest(
    model_ref=ModelRef.binding("mimo-v2-flash-chat"),
    prompt="hello",
)

# 兼容（逐步废弃）：通过 model 字符串自动检测
TextGenerateRequest(
    model="mimo-v2-flash-chat",
    prompt="hello",
)
```

优先级：`model_ref` > `model` > 默认绑定。当 `model_ref` 存在时，`model` 字段被忽略。

`model` 字符串支持三种值（自动检测，逐步废弃）：
- `None` — 使用 capability 对应的默认绑定（如 `gateway.default_text`）
- binding key（如 `"mimo-v2-flash-chat"`）— 自动走绑定解析
- model key / provider 模型名（如 `"gpt-5.4-mini"`）— 自动检测后解析

### ModelResolver — 模型解析器

```python
from llm_gateway.model_catalog import ModelResolver
from llm_gateway import ModelRef, Capability

# 推荐方式：通过 ModelRef 解析
routes, retry_policy = await resolver.resolve(
    ModelRef.model("gpt-5.4-mini"),
    capability_hint=Capability.TEXT,
    provider_hint=ProviderId.OPENAI,           # 可选
    required_features={"function_call": True},  # 可选
)

# 旧方式（已废弃，逐步移除）
routes, retry_policy = await resolver.resolve_candidates(
    "gateway.default_text",
    model_key="gpt-5.4-mini",
    provider_hint=None,
)
```

**Capability 自动推断**：当目标模型只有一种 capability 时，无需传 `capability_hint`；支持多种时必须指定，否则抛 `UNSUPPORTED_CAPABILITY`。

## 模型解析流程

```
请求 (model=str | None)
  │
  ▼
GatewayService._build_model_ref()
  ├─ None  → ModelRef.binding("gateway.default_{capability}")
  └─ str   → ModelRef.model(str)
  │
  ▼
ModelResolver.resolve(ModelRef)
  ├─ binding_key → bindings_by_key → model_key → models_by_key → instances
  ├─ model_key   → models_by_key → instances
  │                  └─ 回退: bindings_by_key（兼容 agent_runtime 传 binding_key 的场景）
  └─ model_name  → models_by_name → model_key → models_by_key → instances
  │
  ▼
capability 推断 → 过滤 instances (health/enabled/provider) → 优先级+权重排序 → failover 候选列表
```

## 容错机制

Gateway 在 provider 调用链路上有 4 层容错保护：

### 1. SDK 异常映射

所有 provider adapter 的 SDK 调用都包裹了 `try/except`，统一翻译为 `GatewayError`。

### 2. 重试策略

per-model 可配，存储在 `llm_models.retry_policy_json`。指数退避 + jitter，Retry-After 头优先。

### 3. 令牌桶限流

per-instance 可选，在实例 `extra` 字段中配置 `{"rate_limit": {"rate": 5, "capacity": 10}}`。

### 4. 熔断器

per-instance 可选，在实例 `extra` 字段中配置 `{"circuit_breaker": {"failure_threshold": 5, ...}}`。

状态机：`CLOSED → OPEN → HALF_OPEN → CLOSED`

### 调用链路

```
请求 → _dispatch_unary/_dispatch_stream
  → ModelResolver.resolve(ModelRef)  # 解析候选路由
  → 熔断器 check → 令牌桶 acquire
  → adapter SDK 调用
  → 失败: error_mapping → RetryPolicy → backoff → 下一候选
  → 成功: metrics + usage 记录
```

## 配置

环境变量前缀 `AI_GATEWAY_`，嵌套分隔符 `__`。

```bash
AI_GATEWAY_CATALOG__DATABASE_URL=postgresql+asyncpg://...    # Catalog 数据库
AI_GATEWAY_CATALOG__CACHE_BACKEND=memory|noop                # Catalog 缓存
AI_GATEWAY_INSTANCE_ENCRYPTION__ENCRYPTION_KEY=<base64>      # API Key 解密密钥
```

## 凭据解析

三种模式（`catalog.secret_resolution_mode`）：

| 模式 | 说明 |
|------|------|
| `instance_only` | 仅从模型实例的加密 API Key 读取 |
| `instance_then_env` | 优先实例，回退环境变量 |
| `env_only` | 仅环境变量，兼容旧部署 |

## LLM Catalog 表关系

```
LlmConnectionProfile ──1:N── LlmModelInstance ──N:1── LlmModel
                                                      │
                                    ┌─────────────────┼──────────────────┐
                                    │                 │                  │
                              LlmModelBinding   LlmModelFeature   LlmCatalogRevision
                              (capability→model) (model ↔ feature)  (版本号, 缓存失效)

LlmFeatureDefinition ──1:N── LlmModelFeature
```

### 业务概念

- **ConnectionProfile** = AI 提供商连接配置（base_url, api_version, region）
- **Model** = 模型定义（model_key, type, capabilities, retry_policy）
- **ModelInstance** = 模型的具体部署（priority/weight 负载均衡, 健康状态, 加密 API key）
- **ModelBinding** = binding_key → model + capability 的映射，运行时通过 binding_key 解析到模型
- **FeatureDefinition** = 可路由的元数据（如 "supports_function_calling"）
- **CatalogRevision** = 单调递增版本号，变更时递增，触发缓存刷新

## 废弃计划

| 项目 | 状态 | 替代方案 |
|------|------|---------|
| `resolve_candidates(binding_key, model_key, ...)` | ⚠️ 已废弃（DeprecationWarning） | `resolve(ModelRef, ...)` |
| 请求 `model` 字段自动检测 | ⚠️ 保留兼容 | 请求 `model_ref` 字段显式指定 |
| `voice.*` 硬编码绑定 | ❌ 已删除 | 数据库中配置 |

### 迁移清单

**agent_runtime** ✅ 已完成：
- `turn_prep.py` 构造 `ModelRef` 并设置到 `request.model_ref`
- `llm_adapter.py` 传递 `model_ref` 到 gateway `TextGenerateRequest`

**其他调用方**（待迁移）：
- 使用 `model_ref=ModelRef.binding(key)` 替代 `model=key`
- 使用 `model_ref=ModelRef.model(key)` 替代 `model=key`（明确是 model_key 时）
- 使用 `model_ref=ModelRef.name(name)` 替代 `model=name`（明确是 provider 模型名时）

## 依赖

- `agentlabkit-db` (ORM 模型)
- `pydantic`, `pydantic-settings`
- `openai`, `anthropic` (Provider 适配)

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [packages/agent_runtime/AGENTS.md](../agent_runtime/AGENTS.md) — Agent 运行时（主要调用方）
