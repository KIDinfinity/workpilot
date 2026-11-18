#!/usr/bin/env bash
# 服务器：~/workpilot/deploy/scripts/backup.sh  → ~/backups/wp-YYYYmmdd-HHMMSS.tgz，保留 7 份
set -euo pipefail
cd "$(dirname "$0")/../.."
COMPOSE="docker compose --env-file .env -f deploy/docker-compose.prod.yml"
NET="workpilot_default"; COLL="${QDRANT_COLLECTION:-kb_default}"   # 集合名以你的配置为准
ROOT="${BACKUP_ROOT:-$HOME/backups}"; TS="$(date +%Y%m%d-%H%M%S)"; WORK="$ROOT/wp-$TS"
curl_net() { docker run --rm --network "$NET" curlimages/curl -sfS "$@"; }
mkdir -p "$WORK"

# 1) Qdrant：创建快照 → 下载 → 删除服务端快照
SNAP=$(curl_net -X POST "http://qdrant:6333/collections/$COLL/snapshots?wait=true" \
       | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["name"])')
curl_net "http://qdrant:6333/collections/$COLL/snapshots/$SNAP" > "$WORK/qdrant-$COLL.snapshot"
curl_net -X DELETE "http://qdrant:6333/collections/$COLL/snapshots/$SNAP" > /dev/null

# 2) SQLite：在线备份 API，再拷出容器
$COMPOSE exec -T api python -c "import sqlite3; s=sqlite3.connect('/app/data/workpilot.db'); \
d=sqlite3.connect('/app/data/backup.db'); s.backup(d); d.close(); s.close()"
$COMPOSE cp api:/app/data/backup.db "$WORK/workpilot.db"
$COMPOSE exec -T api rm -f /app/data/backup.db

# 3) MinIO：只读挂载数据卷打包（单节点、低写入量下可接受；严格一致可先 stop minio）
docker run --rm -v workpilot_minio-data:/data:ro -v "$WORK":/backup alpine \
  tar czf /backup/minio.tgz -C /data .

tar czf "$ROOT/wp-$TS.tgz" -C "$ROOT" "wp-$TS" && rm -rf "$WORK"
ls -1t "$ROOT"/wp-*.tgz | tail -n +8 | xargs -r rm -f          # 只保留最近 7 份
echo "backup ok: $ROOT/wp-$TS.tgz ($(du -h "$ROOT/wp-$TS.tgz" | cut -f1))"
