# storage — 本地存储

> **定位**：SQLite 持久化层。聊天历史 + 记忆存储。数据文件在 `~/.config/agentlabkit/`。

## 职责

- 聊天消息持久化（按时间序列）
- 记忆记录 CRUD + 向量搜索（余弦相似度）

## 文件

| 文件 | 说明 |
|------|------|
| `chat_store.py` | `ChatStore` — 聊天历史（`chat.db`），支持 add / recent / clear |
| `memory_store.py` | `SqliteMemoryStore` — `MemoryStore` 协议实现（`memory.db`），支持 CRUD + 向量搜索 |

## 数据库

| 库 | 路径 | 用途 |
|----|------|------|
| `chat.db` | `~/.config/agentlabkit/chat.db` | 聊天消息 |
| `memory.db` | `~/.config/agentlabkit/memory.db` | 记忆记录 + 嵌入向量 |

## 核心接口

```python
# chat_store.py
store = ChatStore()
store.add("user", "hello")           # → ChatMessage
messages = store.recent(limit=50)     # → list[ChatMessage]
store.clear()

# memory_store.py
store = SqliteMemoryStore()
await store.save(record)              # → MemoryRecord
await store.search(query, embedding)  # → list[MemoryRecord]（余弦相似度排序）
```

## 注意事项

- `memory_store.py` 实现 `memory.contracts.MemoryStore` 协议，与 server 端共享接口
- 向量搜索使用纯 Python 余弦相似度（无 numpy 依赖）
- 两个 SQLite 库独立，避免写锁竞争
- `ChatStore` 是同步 API（Qt 主线程直接调用），`SqliteMemoryStore` 是 async API
