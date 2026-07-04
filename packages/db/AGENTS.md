# db — 共享数据库基础设施

> **定位**：提供 SQLAlchemy Base 类、Snowflake ID 生成器、异步 Engine/Session 生命周期管理。所有需要 ORM 和数据库访问的包都依赖此包。

## 系统中的角色

```
llm_gateway / agent_runtime / backend
                │
                ▼
          packages/db  ← 本包
          (ORM Base · Engine · Snowflake)
```

本包不依赖项目中任何其他模块。

## 目录结构

```
packages/db/src/alkit_db/
├── __init__.py          # 公开导出
├── base.py              # Base, EntityBase (snowflake ID, audit timestamps)
├── engine.py            # init_engine / get_session_factory / dispose_engine
├── snowflake.py         # 线程安全的雪花 ID 生成器
└── llm_catalog.py       # LLM Catalog ORM 模型 (供 llm_gateway 复用)
```

## 核心接口

### Engine 生命周期 (`engine.py`)

```python
init_engine(database_url: str, *, echo=False, pool_size=10, max_overflow=20) -> async_sessionmaker
get_session_factory() -> async_sessionmaker[AsyncSession]
dispose_engine() -> None
```

设计要点：`init_engine` 接受连接 URL 参数，与 Settings 解耦——调用方自行决定配置来源。

### ORM Base (`base.py`)

```python
class Base: ...                # SQLAlchemy DeclarativeBase
class EntityBase(Base): ...    # 含 id (snowflake)、created_at、updated_at
```

### Snowflake ID (`snowflake.py`)

```python
configure(worker_id: int = 0) -> None
next_id() -> int               # 全局唯一 64-bit ID
```

## 使用示例

```python
from alkit_db import init_engine, get_session_factory, EntityBase
from alkit_db import configure as configure_snowflake, next_id as next_snowflake_id

# 启动时
init_engine("postgresql+asyncpg://app:pass@localhost:5432/mydb")
configure_snowflake(worker_id=1)

# 业务代码中
from sqlalchemy import select

session_factory = get_session_factory()
async with session_factory() as session:
    result = await session.execute(select(MyModel).limit(10))
```

## 依赖

- `sqlalchemy[asyncio]>=2.0.0`

无项目内部依赖。

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [packages/infra/AGENTS.md](../infra/AGENTS.md) — 同层级的基础设施包
