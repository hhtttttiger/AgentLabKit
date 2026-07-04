---
name: docker-debug-startup
description: Docker 本地全栈调试启动的事实性记录
metadata: 
  node_type: memory
  type: project
  originSessionId: fa011c18-94fa-4c6e-b6dd-b55ac52cc8db
---

# Docker 本地全栈调试启动

## 启动命令

```bash
docker compose up --build          # 首次或代码变更后
docker compose up -d               # 已有镜像时后台启动
docker compose down --rmi local --remove-orphans  # 清除所有痕迹
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000/admin/ |
| 后端 API | http://localhost:8000/health |
| 数据库 | localhost:5432 (app/devpassword/agentlabkit) |
| Redis | localhost:6379 |

默认账号：`admin / admin`

## 依赖版本约束

`cryptography>=43.0.0,<44.0.0` — 48.x 的 Rust 绑定在 Colima VZ (ARM) 中 SIGILL。
`bcrypt>=4.0.0,<5.0.0` — 5.x 与 passlib 1.7.4 不兼容。

## 已修复的代码问题

这些是系统首次启动时发现的 bug，已修复：

- `backend/alembic/versions/002_kb_refactor.py` — `down_revision` 从 `"001"` 改为 `"001_initial"`（与 001 迁移的 revision ID 对齐）
- `backend/alembic/versions/001_initial_schema.py` — HNSW 索引去掉 `knowledge_base_id` 列（pgvector HNSW 不支持多列索引）
- `backend/Dockerfile` — CMD 为 `PYTHONPATH=/app/src alembic upgrade head && python -m bootstrap && uvicorn main:create_app`
- `backend/src/main.py` — 相对导入改为绝对导入（`from .common.errors` → `from common.errors`），与 `package-dir = {"" = "src"}` 安装方式一致
- `backend/src/modules/knowledge_base/router.py` — `DbSession` 已含 `Depends`，去掉多余的 `= Depends()`；无默认值参数移到有默认值参数前面
- `backend/src/common/dependencies.py` — `get_session_factory()` 返回 `async_sessionmaker`，需 `get_session_factory()()` 获取 session
- `packages/db/src/alkit_db/base.py` — 移除 `MetaData()` 自定义（不需要）

## 环境前提

- Colima 作为 Docker runtime（macOS ARM）
- `docker compose` v2 插件（`brew install docker-compose` + `~/.docker/config.json` 添加 `cliPluginsExtraDirs`）
