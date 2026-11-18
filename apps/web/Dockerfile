# syntax=docker/dockerfile:1

# ---- build：pnpm 装依赖 → tsc + vite 产出 /app/dist ----
FROM node:22-alpine AS build
WORKDIR /app
# 与本机 pnpm 同版本（pnpm 12 的 packageManager 字段会改写 lockfile，故这里直接装固定版本）
# 国内镜像：npm/pnpm registry 走 npmmirror，加速依赖下载（大陆服务器直连 npmjs 极慢）
RUN npm config set registry https://registry.npmmirror.com \
 && npm i -g pnpm@12.8.1 \
 && pnpm config set registry https://registry.npmmirror.com
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

# ---- runtime：Caddy 托管静态文件 + 反代 API ----
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
