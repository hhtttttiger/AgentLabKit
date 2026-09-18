---
name: docker-debug-startup
description: Docker 本地全栈调试启动指南
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
docker compose down --rmi local --remove-orphans  # 清除当前 compose 资源
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000/admin/ |
| 后端 API | http://localhost:8000/health |
| 数据库 | localhost:15432 (app/devpassword/agentlabkit) |
| Redis | localhost:6379 |

默认账号：`admin / admin`

## 依赖版本约束

`cryptography>=43.0.0,<44.0.0` — 48.x 的 Rust 绑定在 Colima VZ (ARM) 中 SIGILL。
`bcrypt>=4.0.0,<5.0.0` — 5.x 与 passlib 1.7.4 不兼容。

## 当前数据库与启动说明

当前仓库使用 `backend/alembic/versions/0001_current_baseline.py` 作为数据库
基线，随后是 `0002_eval_score_nullable` 和
`0003_eval_candidate_identity`。旧启动记录中出现的
`001_initial_schema.py`、`002_kb_refactor.py` 和 `0019_observability_v2.py`
不属于当前 migration chain；排查迁移问题时以 `alembic history` 和仓库中的
实际文件为准。

Docker compose 会按当前镜像入口执行迁移和服务启动。若修改依赖或镜像内容，
重新执行 `docker compose up --build`；仅修改应用代码时可使用前台或后台启动命令。

## 环境前提

- Colima 作为 Docker runtime（macOS ARM）
- `docker compose` v2 插件（`brew install docker-compose` + `~/.docker/config.json` 添加 `cliPluginsExtraDirs`）
