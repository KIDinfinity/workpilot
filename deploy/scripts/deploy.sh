#!/usr/bin/env bash
# 用法：DEPLOY_HOST=wp-prod ./deploy/scripts/deploy.sh
# 把仓库同步到远端 home 下的 workpilot/，用 prod compose 构建并启动，最后校验 /ready。
set -euo pipefail
HOST="${DEPLOY_HOST:?请设置 DEPLOY_HOST，如 wp-prod}"
DIR="${DEPLOY_DIR:-workpilot}"                      # 远端 home 下的目录
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE="docker compose --env-file .env -f deploy/docker-compose.prod.yml"

# --delete 不会删除被 exclude 的远端文件，所以服务器上的 .env 是安全的
rsync -az --delete \
  --exclude '.git/' --exclude '.env' --exclude '.env.*' \
  --exclude '/data/' --exclude 'apps/api/data/' --exclude '/eval/' \
  --exclude 'node_modules/' --exclude '.venv/' --exclude 'dist/' \
  --exclude '__pycache__/' --exclude '.pytest_cache/' \
  "$ROOT/" "$HOST:$DIR/"

ssh "$HOST" "cd $DIR && test -f .env || { echo '缺少服务器 .env'; exit 1; }"
ssh "$HOST" "cd $DIR && $COMPOSE up -d --build --remove-orphans && $COMPOSE ps"
ssh "$HOST" "cd $DIR && $COMPOSE exec -T api python -c \
  \"import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/ready',timeout=5).read().decode())\""
