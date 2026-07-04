# 模型定价 & 缓存感知成本计算 — 设计文档

**日期:** 2026-06-27
**状态:** 待评审

---

## 背景

AgentLabKit 已有 LLM 模型管理、token 消耗记录、成本分析/预算模块框架。但存在三个缺口：

1. **模型无定价字段** — `llm_models` 表没有 input/output/cache 单价列
2. **缓存信息被丢弃** — pydantic_ai 的 `RunUsage` 已包含 `cache_write_tokens`/`cache_read_tokens`，但 `usage_info.py` 提取时丢弃
3. **成本从未计算** — `estimated_cost` 始终为 `None → 0.0`，没有 token × 单价的逻辑

本设计覆盖：模型定价数据模型 → 缓存 token 捕获 → 成本计算引擎 → 前端展示。

---

## 关键决策

| 决策 | 选择 |
|------|------|
| 定价来源 | 纯手动录入 |
| 定价粒度 | 每 1M tokens (USD) |
| 缓存字段 | 完整 4 字段（input / output / cache_write / cache_read） |
| 计算时机 | 请求记录时一次计算，写入 DB |
| 币种 | 仅 USD |

---

## 1. 数据模型变更

### 1.1 `llm_models` — 新增定价列

`packages/db/src/alkit_db/llm_catalog.py` 的 `LlmModel`：

```python
input_price_per_mtok: Mapped[Decimal | None]
output_price_per_mtok: Mapped[Decimal | None]
cache_write_price_per_mtok: Mapped[Decimal | None]
cache_read_price_per_mtok: Mapped[Decimal | None]
```

- 类型 `Numeric(10,6)`，nullable
- 全部为 NULL → 该模型"未定价"，成本计算时 `estimated_cost` 记为 NULL
- 部分为 NULL → 对应维度成本贡献 0

### 1.2 `UsageInfo` — 新增缓存字段

`packages/llm_gateway/src/llm_gateway/models.py`：

```python
class UsageInfo(BaseModel):
    # ...existing...
    cache_write_tokens: int | None = None   # ← 新增
    cache_read_tokens: int | None = None    # ← 新增
```

### 1.3 使用量表 — 新增缓存列

`model_attempt_logs`:
- `CacheWriteTokens` (Integer, nullable)
- `CacheReadTokens` (Integer, nullable)

`model_request_logs`:
- `CacheWriteTokens` (Integer)
- `CacheReadTokens` (Integer)

`model_request_logs.TotalEstimatedCost` 开始填入真实值。

---

## 2. 成本计算引擎

### 2.1 计算公式

```
cost = (
    (input_tokens - cache_write - cache_read) × input_price
  + cache_write                                × cache_write_price
  + cache_read                                 × cache_read_price
  + output_tokens                              × output_price
) / 1_000_000
```

- 若某价格字段为 NULL，该维度贡献 0
- 若 4 个字段全为 NULL，`estimated_cost = None`

### 2.2 实现位置

`packages/llm_gateway/src/llm_gateway/core/service.py` → `_record_usage()` 方法：

1. 已有逻辑：从 response 提取 `usage`（所有 token 字段）
2. 新增逻辑：根据 `model_key` 查询定价 → 按公式计算 → 填入 `estimated_cost`
3. 定价缓存：Gateway 启动时将 `{model_key: pricing}` 加载到内存，避免每次查库

### 2.3 缓存 token 提取

`packages/llm_gateway/src/llm_gateway/usage_info.py` → `usage_from_response_usage()`:

```python
cache_write_tokens=getattr(usage, "cache_write_tokens", None),
cache_read_tokens=getattr(usage, "cache_read_tokens", None),
```

`accumulate_usage()` 同步累加缓存字段。

---

## 3. 后端 API

### 3.1 ModelCreate / ModelUpdate

`backend/src/modules/llm_catalog/schemas.py` — 新增：

```python
input_price_per_mtok: Decimal | None = None
output_price_per_mtok: Decimal | None = None
cache_write_price_per_mtok: Decimal | None = None
cache_read_price_per_mtok: Decimal | None = None
```

### 3.2 ModelRead

同样 4 个字段。已有 `GET /api/llm-catalog/models` 和 `GET /api/llm-catalog/models/{key}` 自动带出。

### 3.3 成本分析 / 模型使用量 API

现有聚合查询增加 `SUM(CacheWriteTokens)`, `SUM(CacheReadTokens)`。响应 schema 增加 `totalCacheWriteTokens`, `totalCacheReadTokens`, `cacheHitRate`。

---

## 4. 前端

### 4.1 模型管理 — 定价表单

`frontend/admin/src/modules/model-management/.../ModelCardDrawer.tsx`

在"高级"折叠区上方，新增"定价"区域：

```
┌─ 定价（每 1M tokens / USD）──────────────┐
│  输入价格      [________] $/MTok          │
│  输出价格      [________] $/MTok          │
│  缓存写入价格  [________] $/MTok          │
│  缓存读取价格  [________] $/MTok          │
└───────────────────────────────────────────┘
```

- 全部可选，留空 = 不适用
- 非负数，最多 6 位小数
- unit suffix " $/MTok" 灰色显示

### 4.2 成本分析页面

- `estimated_cost` 从占位 $0.00 → 真实美元值
- 新增 **缓存命中率** 指标：`cache_read / (input + cache_read)` × 100%
- 新增 **缓存节省金额** 指标：对比"全部按 input_price 计费"和"实际计费"的差额

### 4.3 模型监控

请求明细表格新增列：`CacheWrites`、`CacheReads`、`EstimatedCost`（有真实值）。

---

## 5. 迁移

### 5.1 数据库

- `llm_models` 增加 4 个定价列 → Alembic migration
- `model_attempt_logs` / `model_request_logs` 增加 2 个缓存列 → Alembic migration

### 5.2 数据回填

不需要。现有模型定价留空（NULL），历史记录缓存列默认 0。

---

## 6. 涉及文件清单

| 层 | 文件 | 变更 |
|----|------|------|
| ORM | `packages/db/src/alkit_db/llm_catalog.py` | 新增 4 列 |
| Usage ORM | `packages/llm_gateway/src/llm_gateway/usage/orm_models.py` | 新增缓存列 |
| Usage 合约 | `packages/llm_gateway/src/llm_gateway/usage/contracts.py` | 新增缓存字段 |
| UsageInfo | `packages/llm_gateway/src/llm_gateway/models.py` | 新增缓存字段 |
| 提取逻辑 | `packages/llm_gateway/src/llm_gateway/usage_info.py` | 提取 + 累加缓存 |
| 记录器 | `packages/llm_gateway/src/llm_gateway/usage/recorder.py` | 写入缓存字段 |
| 核心服务 | `packages/llm_gateway/src/llm_gateway/core/service.py` | 成本计算 + 定价查询 |
| 后端 Schema | `backend/src/modules/llm_catalog/schemas.py` | 新增定价字段 |
| 后端 ORM | `backend/src/modules/llm_catalog/orm.py`（如有） | 新增定价字段 |
| 成本聚合器 | `packages/cost_analysis/src/cost_analysis/aggregator.py` | 聚合缓存字段 |
| 模型使用量 | `backend/src/modules/model_usage/service.py` | 聚合缓存字段 |
| 迁移 | `backend/alembic/versions/` | 新增 migration |
| 前端类型 | `frontend/admin/.../contracts.ts` | 新增定价 + 缓存字段 |
| 前端表单 | `frontend/admin/.../ModelCardDrawer.tsx` | 定价输入区域 |
| 前端 API | `frontend/admin/.../api.ts` | 传递定价字段 |
| 前端成本分析 | `frontend/admin/.../cost-analysis/` | 真实成本 + 缓存指标 |
| 前端模型监控 | `frontend/admin/.../model-monitoring/` | 缓存列 + 成本列 |

---

## 7. 不在范围内

- 多币种支持（留到 V2）
- 从提供商 API 自动获取价格
- 定价变更历史审计
- 基于定价的智能路由（选最便宜模型）
