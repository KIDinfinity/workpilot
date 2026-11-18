# Runbook

## 本地开发

API 与前端分开跑（热重载，改代码即时生效）：

```bash
make bootstrap   # 首次：复制 .env、检查依赖（uv / pnpm / docker）
make dev         # API：uvicorn 热重载，http://localhost:8000
make web         # 前端：Vite 热重载，http://localhost:5173（/v1 代理到 :8000）
```

- `make dev` 在 `apps/api` 下用 `uv run uvicorn app.main:app --reload --port 8000`
- `make web` 在 `apps/web` 下用 `pnpm dev`
- API 单元测试（不调真实 LLM）：`cd apps/api && uv run pytest -m "not live" -q`

## 本地全栈

一条命令起全部服务（api + web + qdrant + minio，浏览器 :8080）：

```bash
make up          # 构建并启动（compose 读仓库根 .env 插值）
make seed        # 上传 data/sample 公开样例到知识库
make ps          # 服务状态 + 健康检查
make logs        # 跟踪日志
make down        # 停止并移除服务（保留命名卷数据）
```

- 健康检查：`curl -s http://localhost:8080/health` 应返回 `{"status":"ok",...}`；`/ready` 三项 ok
- dev 的 Embedding 用本机 Ollama（`host.docker.internal:11434`，模型 `bge-m3`），改 SiliconFlow 见 `.env` 的 `EMBEDDING_BASE_URL`

## 备份（Day29 起）

- 内容：一个 `wp-YYYYmmdd-HHMMSS.tgz`，内含三件——
  - `qdrant-kb_default.snapshot`：Qdrant 集合快照（向量 + payload）
  - `workpilot.db`：SQLite 业务库（文档 / 会话 / 反馈），用 online backup API（`sqlite3.Connection.backup`）导出，非直接 `cp`
  - `minio.tgz`：MinIO 原始文档对象存储归档
- 位置：服务器 `~/backups/`；Mac 异副本在 `~/lab/backups/workpilot-cloud/`
- 保留策略：每日一次（RPO ≤ 24 小时），保留最近 7 份（`backup.sh` 自动轮换）
- 生成：服务器执行 `~/workpilot/deploy/scripts/backup.sh`
- 定时：服务器 crontab `30 3 * * *`（03:30 UTC = 北京时间 11:30）
- Mac 拉回（异地副本，每周至少一次，服务器无法主动连回 Mac）：

```bash
mkdir -p ~/lab/backups/workpilot-cloud && rsync -az wp-prod:backups/ ~/lab/backups/workpilot-cloud/
```

## 恢复（Day29 起）

破坏性演练，**只对含公开样例数据的 Demo 环境执行**。前提：Mac 上已有最新备份副本且 `tar tzf` 校验通过。

```bash
# Mac 端先校验最新备份
ssh wp-prod 'tar tzf $(ls -1t ~/backups/wp-*.tgz | head -1)'

# 服务器端执行恢复（脚本内含确认提示，逐行审查删卷部分）
ssh wp-prod 'workpilot/deploy/scripts/restore.sh $(ls -1t ~/backups/wp-*.tgz | head -1)'
```

- 脚本会：停服 → 删三卷（qdrant-data / minio-data / api-data）→ 重建空卷 → 还原 MinIO / SQLite / Qdrant 快照 → 起全栈 → 输出 RTO
- 本次演练：RTO **1 分钟**（实测 22 秒，2026-11-16；停服→删卷→重建→还原 MinIO/SQLite/Qdrant 快照→起全栈→问答验证通过）
- 演练后验证：同一样例问题带引用、引用点开有片段、知识库文档列表与备份前一致、历史会话仍在

## CI（Day29 起）

- 工作流：`.gitea/workflows/ci.yml`，push（main）与 PR 触发；`api`（ruff + pytest 非 live）与 `web`（tsc + build）两个 job
- runner 启动（Mac；注册 token 见 Gitea 站点管理 → Actions → Runners → 创建新 Runner）：

```bash
mkdir -p ~/gitea/runner
docker run -d --name gitea-runner --restart unless-stopped \
  -e GITEA_INSTANCE_URL=http://host.docker.internal:3000 \
  -e GITEA_RUNNER_REGISTRATION_TOKEN=<token> \
  -e GITEA_RUNNER_NAME=mac-runner \
  -e GITEA_RUNNER_LABELS=ubuntu-latest:docker://node:20-bookworm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/gitea/runner:/data \
  gitea/act_runner:latest
docker logs -f gitea-runner   # 看到 "runner: mac-runner ... declared successfully" 即可 Ctrl-C
```

- 常见失败：
  - `dial tcp 127.0.0.1:3000: connect: connection refused` → `GITEA_INSTANCE_URL` 不能用 localhost，改 `http://host.docker.internal:3000` 并删除 `~/gitea/runner/.runner` 重新注册
  - checkout 失败 `unable to access 'http://localhost:3000/...'` → 未设置 `github-server-url`
  - 拉取 `actions/checkout` 或 `node:20-bookworm` 超时 → 给 runner 加代理 `-e HTTPS_PROXY=http://host.docker.internal:7890`
  - CI 中 `ValidationError: Field required` → 在 workflow `env` 补占位变量（不放真实密钥）

## 部署（Day28 起）

### 服务器信息

- 别名 `wp-prod`（Mac `~/.ssh/config` 里配置，不在此写 IP）
- 部署用户 `deploy`（无密码、无 sudo、已加 docker 组）
- 远端目录 `~/workpilot`，生产配置在 `deploy/Caddyfile.prod` + `deploy/docker-compose.prod.yml`
- 公网地址 `http://8.148.216.61`（IP 直连，暂未绑域名 / HTTPS，后续再补）；仅开放 22/80
- root 可用密钥登录（`ssh root@<IP>`，密码登录仍禁用），方便运维

### 首次初始化清单（新服务器只做一次）

```bash
# 1) 专用密钥（Mac，若还没有）
ssh-keygen -t ed25519 -f ~/.ssh/workpilot_ed25519 -C "workpilot-deploy"

# 2) 把公钥放到管理账号（云厂商给的 root/ubuntu）
ssh-copy-id -i ~/.ssh/workpilot_ed25519.pub root@<IP>

# 3) 服务器（管理账号）初始化
curl -fsSL https://get.docker.com | sudo sh
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
sudo mkdir -p /home/deploy/.ssh && sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown -R deploy:deploy /home/deploy/.ssh && sudo chmod 700 /home/deploy/.ssh && sudo chmod 600 /home/deploy/.ssh/authorized_keys
printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin yes\n' | sudo tee /etc/ssh/sshd_config.d/00-hardening.conf
sudo sshd -t && sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin)'
sudo systemctl restart ssh
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw --force enable && sudo ufw status

# 4) Mac 加别名（~/.ssh/config），之后都用 wp-prod
#   Host wp-prod
#     HostName <IP>
#     User deploy
#     IdentityFile ~/.ssh/workpilot_ed25519

# 5) （暂缓）域名 A 记录：wp -> <IP>，TTL 600；dig +short wp.<域名> 返回 IP 再继续
```

### 部署（每次发布）

```bash
# 首次：把 .env.prod 传到服务器并收紧权限
ssh wp-prod 'mkdir -p ~/workpilot'
scp .env.prod wp-prod:~/workpilot/.env && ssh wp-prod 'chmod 600 ~/workpilot/.env'

# 之后每次发布一条命令
make deploy            # 等价 DEPLOY_HOST=wp-prod ./deploy/scripts/deploy.sh
```

### 查看日志

```bash
ssh wp-prod 'cd workpilot && docker compose -f deploy/docker-compose.prod.yml logs -f --tail=100 api'
```

### 401 / 访问排查

- `curl -sI http://8.148.216.61 | head -1` 应返回 `HTTP/1.1 401`（basic auth，当前为 HTTP 明文，域名 + HTTPS 留作后续）
- 443 当前关闭（无 HTTPS）：`nc -zvw3 <IP> 443` 应失败；后续绑域名时在 Caddyfile 写站点地址即可自动 ACME 申请证书
- basic auth 一直 401（密码正确）：`.env` 里 `BASIC_AUTH_HASH` 的 `$` 被插值吃掉，改单引号，或 `docker compose --env-file .env -f deploy/docker-compose.prod.yml config | grep BASIC` 检查

### 轮换 basic auth 密码

```bash
# 1) 生成新哈希（交互输入，不进 shell 历史）
docker run --rm -it caddy:2-alpine caddy hash-password

# 2) 改本地 .env.prod 的 BASIC_AUTH_HASH（单引号包裹）
# 3) 重新上传并重启
scp .env.prod wp-prod:~/workpilot/.env && ssh wp-prod 'chmod 600 ~/workpilot/.env'
make deploy
```

## 常见故障

| 现象 | 处理 |
| --- | --- |
| SSE 不流式（一次全量返回） | Caddy 反代必须带 `flush_interval -1`（见 `deploy/Caddyfile*`）；确认请求走 `-N` 且上游返回 `text/event-stream` |
| 证书失败 / HTTPS 打不开 | 当前 prod 是 IP + HTTP，**无证书**（预期内，443 未开）；绑域名启用 HTTPS 后，Caddyfile 写站点地址会自动 ACME 申请，见 ADR 0005 |
| `/ready` 返回 503 | 逐项看返回里的 `embedding / qdrant / minio` 哪个 `not ok`：多半是 Embedding 连不上（见下）或 Qdrant 未起，`make ps` 确认健康 |
| Embedding 连接失败 | dev 确认 Ollama 在跑且已 `ollama pull bge-m3`；prod 确认 `.env` 的 `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` 指向 SiliconFlow 且 key 有效 |
| CI runner 离线 | `docker logs -f gitea-runner` 看注册；常见是 `GITEA_INSTANCE_URL` 用了 localhost（改 `http://host.docker.internal:3000`），或拉镜像超时（加代理，见「CI」节） |

## 技术债

- dev 阶段 WorkPilot 复用 `infra/compose/.env` 的 MinIO root 凭据（`MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`）；生产环境已改为独立强密码（见 `.env.prod`），后续 W7 应改为按 bucket 收敛权限的 access key，不再使用 root 凭据。
- basic auth 只是 W19 前的 Demo 门禁，无用户区分、无法单独吊销，W19 换登录系统。
