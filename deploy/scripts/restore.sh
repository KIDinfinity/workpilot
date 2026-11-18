#!/usr/bin/env bash
# 服务器：~/workpilot/deploy/scripts/restore.sh <backup.tgz>
# 恢复演练：删除云端数据卷（破坏性，仅限只含公开样例数据的 Demo 环境），
# 再用备份包还原 Qdrant 快照 / SQLite / MinIO，计时输出 RTO。
# 运行前请先在 Mac 上确认已有最新备份副本，且 `tar tzf <backup.tgz>` 校验通过。
set -euo pipefail

B="${1:?用法: restore.sh <backup.tgz>}"
[ -f "$B" ] || { echo "备份包不存在: $B" >&2; exit 1; }

cd "$(dirname "$0")/../.."
COMPOSE="docker compose --env-file .env -f deploy/docker-compose.prod.yml"
NET="workpilot_default"; COLL="${QDRANT_COLLECTION:-kb_default}"

echo "== 校验备份包内容（应含 qdrant-$COLL.snapshot / workpilot.db / minio.tgz）=="
tar tzf "$B"

echo ""
echo "警告：以下操作会删除云端数据卷（qdrant-data / minio-data / api-data）。"
echo "      只在只含公开样例数据的 Demo 环境执行，切勿在真实数据环境运行。"
read -r -p "确认继续？(输入 yes 回车) " ans
[ "$ans" = "yes" ] || { echo "已取消"; exit 1; }

START=$SECONDS
rm -rf /tmp/restore && mkdir -p /tmp/restore
tar xzf "$B" -C /tmp/restore
R=$(ls -d /tmp/restore/wp-*)

echo "== 停服并删除数据卷 =="
$COMPOSE down
docker volume rm workpilot_qdrant-data workpilot_minio-data workpilot_api-data

echo "== 由 compose 重建空卷并只启动 qdrant =="
$COMPOSE up --no-start
$COMPOSE start qdrant

echo "== 恢复 MinIO 对象存储 =="
docker run --rm -v workpilot_minio-data:/data -v "$R":/backup alpine sh -c 'tar xzf /backup/minio.tgz -C /data'

echo "== 恢复 SQLite 业务库 =="
docker run --rm -v workpilot_api-data:/data -v "$R":/backup alpine sh -c 'cp /backup/workpilot.db /data/ && chown 10001:10001 /data/workpilot.db'

echo "== 等待 qdrant 就绪 =="
until docker run --rm --network "$NET" curlimages/curl -sf http://qdrant:6333/readyz >/dev/null; do sleep 2; done

echo "== 上传 Qdrant 快照 =="
docker run --rm --network "$NET" -v "$R":/backup curlimages/curl -sfS \
  -X POST "http://qdrant:6333/collections/$COLL/snapshots/upload?priority=snapshot" \
  -F "snapshot=@/backup/qdrant-$COLL.snapshot"

echo "== 启动全栈 =="
$COMPOSE up -d

echo "RTO: $((SECONDS-START)) 秒（约 $(( (SECONDS-START + 59) / 60 )) 分钟）"
