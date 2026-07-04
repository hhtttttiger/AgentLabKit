.PHONY: help up stop reset status logs worker

# 管理本地调试用的 postgres + redis 生命周期。
# 数据落在命名卷(pgdata/redisdata)，停机/重启 colima/重启电脑都不丢；
# 想要干净环境用 `make reset`（会删数据卷，不可逆）。
# backend / frontend 是本地进程(uvicorn/vite)，由 /local-dev 启动，不在这里。

help: ## 显示所有命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

up: ## 启动 postgres + redis（已运行则秒级 resume，数据常驻）
	@colima status >/dev/null 2>&1 || colima start
	@docker compose up -d postgres redis
	@echo "等待健康检查..."
	@n=0; while [ $$n -lt 30 ]; do \
		healthy=$$(docker compose ps postgres redis --format '{{.Status}}' | grep -c healthy); \
		[ "$$healthy" -ge 2 ] && break; \
		n=$$((n+1)); sleep 1; \
	done
	@docker compose ps postgres redis

stop: ## 暂停 postgres + redis（保留容器与数据，下次 up 秒级恢复）
	@docker compose stop postgres redis

reset: ## ⚠️ 彻底清空：删除容器 + 数据卷（干净环境，不可逆）
	@docker compose down -v
	@echo "已清空 postgres/redis 容器与数据卷（make up 后需重新迁移/seed）"

status: ## 查看容器状态
	@docker compose ps postgres redis

logs: ## 跟随 postgres/redis 日志（Ctrl-C 退出）
	@docker compose logs -f postgres redis

worker: ## 启动文档索引 worker（本地进程；索引消费已从 web 进程剥离）
	@cd backend && source .venv/bin/activate && \
		PYTHONPATH=src python -m worker
