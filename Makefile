.DEFAULT_GOAL := help
PROJECT ?= workpilot
# --env-file .env 让 ${MINIO_ACCESS_KEY} 等从仓库根 .env 插值（compose 默认只读 deploy/.env）
COMPOSE := docker compose -p $(PROJECT) --env-file .env -f deploy/docker-compose.yml
API_DIR := apps/api
BASE ?= http://localhost:8080

.PHONY: help bootstrap dev test lint up down logs ps seed eval eval-rag eval-rag-judge backup deploy web web-build web-types

help: ## 列出所有命令
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

bootstrap: ## 初始化本地环境（复制 .env、检查依赖）
	@bash scripts/bootstrap.sh

dev: ## 启动 API（热重载，:8000）
	cd $(API_DIR) && uv run uvicorn app.main:app --reload --port 8000

test: ## 运行 API 测试
	cd $(API_DIR) && uv run pytest -q

lint: ## ruff 检查 + 格式检查
	cd $(API_DIR) && uv run ruff check . && uv run ruff format --check .

up: ## 构建并启动全栈（api + web + qdrant + minio，浏览器 :8080）
	$(COMPOSE) up -d --build

down: ## 停止并移除 compose 服务（保留命名卷数据）
	$(COMPOSE) down

logs: ## 跟踪 compose 日志
	$(COMPOSE) logs -f --tail=100

ps: ## 查看 compose 服务状态与健康检查
	$(COMPOSE) ps

seed: ## 上传 data/sample 公开样例到知识库（云端：make seed BASE=https://域名）
	BASE=$(BASE) ./scripts/seed_sample.sh

eval: ## 运行评测（W5 接入）
	@echo "TODO: eval"

eval-rag: ## 运行 RAG 检索指标基线（可传 ARGS，如 ARGS="--with-answer"）
	cd $(API_DIR) && PYTHONPATH=. uv run python ../../eval/runners/run_rag_eval.py --name rag-baseline $(ARGS)

eval-rag-judge: ## 运行 RAG 生成质量与 judge 评测
	cd $(API_DIR) && PYTHONPATH=. uv run python ../../eval/runners/run_rag_eval.py --with-answer --judge --name rag-v0.3 $(ARGS)

backup: ## 备份数据（W7 接入 deploy/scripts/backup.sh）
	@echo "TODO: backup"

deploy: ## 部署到生产服务器（DEPLOY_HOST 默认 wp-prod）
	DEPLOY_HOST=$(or $(DEPLOY_HOST),wp-prod) ./deploy/scripts/deploy.sh

web: ## 启动前端（Vite，:5173，代理 /v1 到 :8000）
	cd apps/web && pnpm dev

web-build: ## 构建前端
	cd apps/web && pnpm build

web-types: ## 从运行中的 API 生成前端类型
	cd apps/web && pnpm gen:api
