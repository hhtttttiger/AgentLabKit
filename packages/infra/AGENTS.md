# infra — 基础设施层

> **定位**：系统最底层的包，不依赖项目的任何其他模块。提供 Redis 连接管理、缓存抽象、消息队列等基础设施能力。其他模块通过 `agentlabkit-infra` 包依赖使用。

## 系统中的角色

```
llm_gateway / retrieval / agent_runtime / backend
                    │
                    ▼
              packages/infra  ← 本包
              (Redis · Cache · Queue)
```

本包是依赖方向的最底层。任何需要 Redis、缓存、队列的模块都应依赖此包。

## 目录结构

```
packages/infra/src/alkit_infra/
├── __init__.py              # 公开 API 导出
├── redis/
│   ├── __init__.py
│   ├── client.py            # 连接池生命周期: init_redis / get_redis / close_redis
│   └── config.py            # RedisSettings (AFREDIS_ 前缀)
├── cache/
│   ├── __init__.py
│   └── backend.py           # CacheBackend Protocol + RedisCache + InMemoryCache
└── queue/
    ├── __init__.py
    ├── errors.py            # QueueError / DeadLetterError 等
    ├── config.py            # QueueSettings (AFQUEUE_ 前缀)
    ├── message.py           # Message dataclass (含 jitter 退避)
    ├── protocol.py          # QueueBackend Protocol
    ├── redis_backend.py     # RedisStreamsQueue — Streams 实现 (含 delayed/dead-letter)
    ├── memory_backend.py    # InMemoryQueue — 内存实现 (测试用)
    └── consumer.py          # QueueConsumer — 后台 Worker (Semaphore 并发控制)
```

## 核心接口

### Redis 连接管理 (`redis/client.py`)

```python
init_redis(url, *, max_connections=20, ...) -> Redis   # 创建全局连接池
get_redis() -> Redis                                    # 获取已初始化的客户端
close_redis() -> None                                   # 关闭连接池
```

### 缓存 (`cache/backend.py`)

```python
class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def get_many(self, keys: list[str]) -> list[str | None]: ...
    async def set_many(self, mapping: dict[str, str], ttl: int | None = None) -> None: ...
    async def delete_many(self, keys: list[str]) -> None: ...
    async def acquire_lock(self, name: str, ttl: int, *, blocking_timeout: float = 0) -> bool: ...
    async def release_lock(self, name: str) -> None: ...

class RedisCache(CacheBackend): ...     # Redis 实现，默认使用 get_redis()
class InMemoryCache(CacheBackend): ...  # 进程内实现，用于测试
```

### 队列 (`queue/`)

```python
class QueueBackend(Protocol):
    async def publish(self, queue_name: str, message: Message) -> str: ...
    async def publish_batch(self, queue_name: str, messages: list[Message]) -> list[str]: ...
    async def consume(self, queue_name: str, consumer_name: str, ...) -> list[tuple[str, Message]]: ...
    async def ack(self, queue_name: str, consumer_name: str, entry_id: str) -> None: ...
    async def nack(self, queue_name: str, consumer_name: str, entry_id: str, *, requeue: bool) -> None: ...
    async def queue_length(self, queue_name: str) -> int: ...
    async def purge(self, queue_name: str) -> int: ...

class RedisStreamsQueue(QueueBackend): ...  # XADD/XREADGROUP/XACK
class InMemoryQueue(QueueBackend): ...     # 进程内实现，用于测试

class QueueConsumer:                        # 后台 Worker
    async def start(self) -> None: ...
    async def stop(self, timeout: float = 30.0) -> None: ...

class Message:                              # 消息模型
    topic: str
    payload: str                            # 调用方自行 JSON 序列化
    scheduled_at: float | None              # 延迟投递时间戳
    retry_count: int                        # 已重试次数
    max_retries: int                        # 最大重试次数
    # 重试退避: min(5s × 2^retry_count, 60s) × uniform(0.5, 1.0)
    # jitter 防止多消费者同时重试造成雷群效应
```

## 使用示例

### 应用启动时初始化 Redis

```python
from alkit_infra import init_redis

init_redis("redis://localhost:6379/0")          # 方式一：直接传参

from alkit_infra.redis.config import RedisSettings  # 方式二：从配置
init_redis(RedisSettings().url)
```

### 缓存

```python
from alkit_infra import RedisCache

cache = RedisCache()
await cache.set("user:123", user_json, ttl=300)
data = await cache.get("user:123")
```

### 队列

```python
from alkit_infra.queue import RedisStreamsQueue, QueueConsumer, Message
import json

backend = RedisStreamsQueue()

# 发布
msg = Message(topic="doc.index", payload=json.dumps({"doc_id": 123}))
await backend.publish("doc-processing", msg)

# 消费
async def handle(msg: Message) -> None:
    data = json.loads(msg.payload)

consumer = QueueConsumer(
    backend=backend, queue_name="doc-processing",
    consumer_name="worker-1", handler=handle, concurrency=3,
)
await consumer.start()
```

## 配置

| 前缀 | 关键字段 | 默认值 |
|------|----------|--------|
| `AFREDIS_` | `URL`, `MAX_CONNECTIONS` | `redis://localhost:6379/0`, `20` |
| `AFQUEUE_` | `DEFAULT_MAX_RETRIES`, `CONSUMER_BATCH_SIZE` | `3`, `10` |

## 依赖

- `redis[hiredis]>=5.0.0`
- `pydantic>=2.0.0`, `pydantic-settings>=2.0.0`
- `loguru>=0.7.0`

无项目内部依赖。

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [packages/db/AGENTS.md](../db/AGENTS.md) — 同层级的共享数据库包
