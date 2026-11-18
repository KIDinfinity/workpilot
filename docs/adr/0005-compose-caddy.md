# 0005. 部署：单机 Docker Compose + Caddy 反代（IP + HTTP，域名/TLS 后续）

- 状态：已采纳
- 日期：2026-11-10（W8·Day28）

## 背景（要解决什么问题，有什么约束）

需要把 WorkPilot 部署到一台单机云服务器，让招聘方 / 协作者能直接访问。约束：

- 单机、无 K8s，运维要轻（作者每天 1–2 小时）。
- 前端 SPA 静态资源 + 后端 SSE 流式都要走同一个入口。
- SSE 必须**逐 token 下发**，反向代理不能缓冲，否则「流式问答」退化成一次性返回。
- 本阶段先不绑域名 / 证书（域名作为后续优化项），先跑通公网 IP + HTTP。

## 决策（选了什么）

**单机 Docker Compose（`deploy/docker-compose.prod.yml`）+ Caddy 反代。** Caddy 负责：

- 静态资源（SPA dist）+ `/v1/*`、`/health`、`/ready` 反代到 api。
- SSE 用 `reverse_proxy { flush_interval -1 }` 关闭缓冲，逐 token 下发。
- 入口站点用 `http://8.148.216.61`（`http://` 前缀 = 不申请证书），
  域名 / TLS 留作后续优化项，届时只需在 Caddyfile 写站点地址即可自动 ACME 申请。
- W19 前用 `basic_auth` 做 Demo 门禁。

dev / prod 差异（同底 `docker-compose.yml`，prod 只改差异）：

| 项 | dev | prod |
| ---- | ---- | ---- |
| Embedding | 本机 Ollama（bge-m3） | SiliconFlow（同模型 bge-m3，1024 维） |
| 入口 | `localhost:8080`（无鉴权） | `8.148.216.61:80`（basic_auth） |
| qdrant / minio | 暴露端口便于调试 | 只在 compose 内网可达 |

## 备选方案（列出并说明放弃理由）

- **Kubernetes**：单机单服务场景严重超规模，运维与心智成本远超收益。放弃。
- **Nginx + certbot**：功能等价，但 HTTPS 证书要多一步 certbot 运维；Caddy 自动
  HTTPS 开箱即用，SSE `flush_interval` 配置也直观。放弃。
- **Cloudflare Tunnel**：免开端口、自带公网入口，作为「域名 / TLS 上线」时的备选
  保留；本阶段直接 IP + 22/80 更简单直接。

## 后果（好处 / 代价 / 后续动作）

好处：

- 单机一键 `make deploy`（rsync + `docker compose up -d`），发布成本极低。
- Caddy 一行 `flush_interval -1` 解决 SSE 流式，无需自己处理缓冲。
- 域名 / TLS 是「加一行站点地址」即可启用的优化项，不影响当前交付。

代价：

- 当前 HTTP 明文 + basic_auth，安全性有限，仅作 W19 前的 Demo 门禁。
- 单机无高可用，服务器故障需按 runbook 备份 / 恢复重建。

复审条件：

- 需要多实例 / 自动扩缩容、或正式对外生产时，重新评估 K8s 或托管方案；
  绑域名时启用 HTTPS，并重新评估 Cloudflare Tunnel。
