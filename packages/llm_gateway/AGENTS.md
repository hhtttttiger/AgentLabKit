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
├── __init__.py
├── config.py               # GatewaySettings (AI_GATEWAY_ 前缀)
├── bootstrap.py            # create_gateway_service() 工厂
├── errors.py               # GatewayError, GatewayErrorCode (含 PROVIDER_RATE_LIMITED)
├── core/
│   ├── service.py          # GatewayService — 统一调用入口 + 重试/限流/熔断集成
│   ├── rate_limiter.py     # TokenBucketRateLimiter — per-instance 令牌桶限流
│   └── circuit_breaker.py  # CircuitBreaker — per-instance 熔断器 (closed/open/half-open)
├── providers/              # Provider 适配器 (OpenAI, Azure 等)
│   └── shared/
│       ├── error_mapping.py          # SDK 异常 → GatewayError 统一映射
│       ├── openai_compatible_text.py # Text 适配器 (含 429 捕获)
│       ├── openai_compatible_image.py
│       ├── openai_compatible_speech.py
│       └── openai_transport.py
├── model_catalog/          # Model Catalog 读侧
│   ├── catalog_service.py  # 模型目录查询
│   ├── secret_resolver.py  # API Key 凭据解析
│   ├── retry_policy.py     # RetryPolicy — 重试策略 (指数退避 + jitter + Retry-After)
│   ├── policies.py         # RetryPolicySchema, RoutingPolicy 验证
│   └── cache.py            # InMemoryCatalogCache / NoOpCatalogCache
└── models.py               # ModelDefinition, ProviderId, Capability 等内部模型
```

## 核心接口

### GatewayService

```python
class GatewayService:
    async def complete(self, card_key, capability, *, messages, ...) -> Result
    async def stream(self, card_key, capability, *, messages, ...) -> AsyncIterator
    async def generate_embedding(self, text: str, model: str) -> list[float]
```

## 容错机制

Gateway 在 provider 调用链路上有 4 层容错保护：

### 1. SDK 异常映射 (`providers/shared/error_mapping.py`)

所有 provider adapter 的 SDK 调用（text/embedding/image/speech）都包裹了 `try/except`，通过 `map_sdk_error()` 将 OpenAI SDK 异常统一翻译为 `GatewayError`：

| SDK 异常 | GatewayErrorCode |
|----------|-----------------|
| `openai.RateLimitError` (429) | `PROVIDER_RATE_LIMITED` |
| `openai.AuthenticationError` (401) | `PROVIDER_AUTH_FAILED` |
| `openai.APITimeoutError` | `PROVIDER_TIMEOUT` |
| `openai.NotFoundError` (404) | `MODEL_NOT_FOUND` |
| `openai.APIStatusError` (5xx) | `UPSTREAM_ERROR` |
| `pydantic_ai.ModelHTTPError` | 按 status_code 映射 |
| 其他网络/连接错误 | `PROVIDER_TIMEOUT` |

### 2. 重试策略 (`model_catalog/retry_policy.py`)

per-model 可配，存储在 `llm_models.retry_policy_json`：

```json
{
  "max_attempts": 3,          // 1-10
  "retry_on_timeout": true,
  "retry_on_rate_limit": true,
  "retry_on_server_error": true,
  "retry_on_auth_error": false,
  "initial_backoff_ms": 500,
  "max_backoff_ms": 10000,
  "backoff_multiplier": 2.0
}
```

- **指数退避 + jitter**：`base * random.uniform(0.5, 1.0)` 防雷群效应
- **Retry-After 优先**：如果 429 响应带 `Retry-After` 头，直接用它作为退避时间

### 3. 令牌桶限流 (`core/rate_limiter.py`)

per-instance 可选配置，在模型实例的 `extra` 字段中：

```json
{"rate_limit": {"rate": 5, "capacity": 10}}
```

- `rate`：每秒补充的令牌数（可持续 QPS）
- `capacity`：突发容量
- 未配置则不限流

### 4. 熔断器 (`core/circuit_breaker.py`)

per-instance 可选配置，在模型实例的 `extra` 字段中：

```json
{"circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 30, "half_open_max_calls": 1}}
```

状态机：`CLOSED → (连续 N 次失败) → OPEN → (等待 recovery_timeout) → HALF_OPEN → (探测成功) → CLOSED`

### 调用链路

```
请求 → _dispatch_unary/_dispatch_stream
  → 熔断器 allow_request() 检查
    → 令牌桶 acquire() 限速
      → invoker (adapter SDK 调用)
        → error_mapping 捕获 SDK 异常 → GatewayError
          → RetryPolicy.should_retry() 判断
            → backoff_ms(attempt, retry_after=...) 计算退避
              → asyncio.sleep → 下一次 attempt
```

### 队列层面容错 (`packages/infra`)

文档处理队列（`document_processing`）有独立的消息级重试：

- 消息失败 → `nack(requeue=True)` → 延迟重投
- 退避公式：`min(5s × 2^retry_count, 60s) × random.uniform(0.5, 1.0)`
- 默认 `max_retries=3`，超限进死信队列 `{queue}:dead`

## 配置

环境变量前缀 `AI_GATEWAY_`，嵌套分隔符 `__`。

```bash
AI_GATEWAY_CATALOG__DATABASE_URL=postgresql+asyncpg://...    # Catalog 数据库连接
AI_GATEWAY_CATALOG__CACHE_BACKEND=memory|noop                # Catalog 缓存后端
AI_GATEWAY_INSTANCE_ENCRYPTION__ENCRYPTION_KEY=<base64>      # API Key 解密密钥
```

## 凭据解析

三种模式（`catalog.secret_resolution_mode`）：

| 模式 | 说明 |
|------|------|
| `instance_only` | 仅从模型实例的加密 API Key 读取 |
| `instance_then_env` | 优先实例，回退环境变量 |
| `env_only` | 仅环境变量，兼容旧部署 |

## LLM Catalog 模块

LLM Gateway 的模型目录通过 `llm_catalog` 业务模块（backend）管理 CRUD，Gateway 包负责读侧。

### 表关系

```
LlmConnectionProfile ──1:N── LlmModelInstance ──N:1── LlmModelCard
                                                      │
                                    ┌─────────────────┼──────────────────┐
                                    │                 │                  │
                              LlmModelBinding   LlmModelCardFeature   LlmCatalogRevision
                              (capability→card) (card ↔ feature_def)   (版本号, 缓存失效)

LlmFeatureDefinition ──1:N── LlmModelCardFeature
```

### 业务概念

- **ConnectionProfile** = 一个 AI 提供商的连接配置，含 base_url、api_version、region
- **ModelCard** = 一个模型的能力定义，含类型、路由策略、重试策略
- **ModelInstance** = 模型卡片在某连接上的具体部署，含 priority/weight（负载均衡）、健康状态、加密 API key
- **ModelBinding** = 按 capability（Text / Embedding / SpeechBatch / SpeechStream / Image / Realtime 等）将模型卡片绑定到一个可引用的 binding_key。运行时业务模块通过 binding_key 或 capability 查 binding → card → instances → 路由。binding_key 命名约定隐含使用上下文（如 `gateway.default_text`、`voice.agent_text`）
- **FeatureDefinition** = 可查询/可路由的元数据（如 "supports_function_calling"）
- **ModelCardFeature** = 卡片与特性的关联，标记是否支持 + 具体值
- **CatalogRevision** = 单调递增版本号，catalog 变更时递增，用于缓存失效

## 依赖

### 内部

- `agentlabkit-db` (ORM 模型)

### 外部

- `pydantic`, `pydantic-settings`, `loguru`
- `openai` (Provider 适配)

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [packages/retrieval/AGENTS.md](../retrieval/AGENTS.md) — 同层级的 RAG 引擎
- [backend/AGENTS.md](../../backend/AGENTS.md) — LLM Catalog CRUD 路由在 backend 中
