# cost_analysis — 成本分析与预算管理

> **定位**：LLM 用量成本的 SQL 聚合查询 + 预算配额检查与告警评估。读取 Gateway 落库的用量日志与 backend 维护的预算/告警表，提供成本概览、分维度拆解、趋势、预算状态与告警管理。

## 系统中的角色

```
backend (main.py lifespan 初始化 + modules/cost_analysis HTTP 层)
                    │
                    ▼
              cost_analysis  ← 本包
              (CostAggregator · BudgetManager)
                    │
                    ▼
   agentlabkit-db (card_request_logs / cost_budgets / cost_alerts)
```

- 被 `backend/src/main.py` 在 lifespan 中通过 `create_cost_analysis_module(session_factory=..., settings=CostAnalysisSettings())` 初始化，挂到 `app.state.cost_analysis_module`。
- HTTP 层在 `backend/src/modules/cost_analysis/`（薄 router + 编排）。

## 目录结构

```
packages/cost_analysis/src/cost_analysis/
├── __init__.py          # 公开 API 导出
├── config.py            # CostAnalysisSettings (COST_ANALYSIS_ 前缀)
├── contracts.py         # CostBreakdown / CostTrendPoint / BudgetScopeType / Granularity / BudgetStatus / CostAlertInfo
├── aggregator.py        # CostAggregator — 成本 SQL 聚合查询引擎
├── budget.py            # BudgetManager — 预算检查与告警管理
└── module.py            # CostAnalysisModule + create_cost_analysis_module() 工厂
```

## 核心接口

### CostAggregator (`aggregator.py`)

```python
class CostAggregator:
    def __init__(self, session_factory) -> None
    async def get_overview(self, *, from_date, to_date) -> CostOverview
    async def get_breakdown_by_model(self, *, from_date, to_date, limit=20) -> list[CostBreakdown]
    async def get_breakdown_by_capability(self, *, from_date, to_date, limit=20) -> list[CostBreakdown]
    async def get_cost_trend(self, *, granularity: Granularity, from_date, to_date) -> list[CostTrendPoint]
    async def get_total_spend(self, *, from_date, to_date, scope_key=None) -> float
```

### BudgetManager (`budget.py`)

```python
class BudgetManager:
    def __init__(self, session_factory) -> None
    async def check_budget(self, session, *, scope_type: BudgetScopeType, scope_key, current_spend) -> BudgetStatus | None
    async def evaluate_alerts(self) -> list[CostAlertInfo]
    async def list_alerts(self, *, acknowledged=None, limit=50) -> list[CostAlertInfo]
    async def acknowledge_alert(self, alert_id: int) -> bool
```

### 关键枚举 / 数据类 (`contracts.py`)

```python
class BudgetScopeType(str, Enum):   # GLOBAL / MODEL / AGENT / USER
class Granularity(str, Enum):       # DAY / WEEK / MONTH

@dataclass(frozen=True, slots=True)
class CostBreakdown:     # scope, total_requests, total_input_tokens, total_output_tokens, total_estimated_cost, avg_latency_ms
class CostTrendPoint:    # period, total_cost, total_tokens, request_count
class BudgetStatus:      # scope_type, scope_key, monthly_limit_usd, current_spend_usd, usage_pct, alert_threshold_pct, is_over_budget
class CostAlertInfo:     # id, budget_id, scope_type, scope_key, alert_type("threshold"|"exceeded"), current_spend_usd, threshold_usd, triggered_at_utc, acknowledged_at_utc
```

### 工厂 (`module.py`)

```python
def create_cost_analysis_module(*, session_factory, settings: CostAnalysisSettings | None = None) -> CostAnalysisModule
```

注入 `session_factory`（async_sessionmaker）给 CostAggregator 与 BudgetManager。

## 配置

| Settings 类 | env 前缀 | 关键字段 | 默认值 |
|------|------|------|------|
| `CostAnalysisSettings` | `COST_ANALYSIS_` | `enabled`、`default_alert_threshold_pct` | `True`、`80.0` |

读取的数据表：`card_request_logs`（来自 llm_gateway usage）、`cost_budgets`、`cost_alerts`（由 backend 定义/迁移）。

## 依赖

### 内部

- `agentlabkit-db`（硬依赖，pyproject 声明）

### 外部

- `pydantic`、`pydantic-settings`、`sqlalchemy[asyncio]`

无对 llm_gateway / agent_runtime 的代码依赖（只读其落库的用量日志）。

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [backend/AGENTS.md](../../backend/AGENTS.md) — cost_* 表迁移与 HTTP 路由
- [packages/llm_gateway/AGENTS.md](../llm_gateway/AGENTS.md) — `card_request_logs` 用量日志的来源
