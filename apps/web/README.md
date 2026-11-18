# apps/web

WorkPilot 前端控制台（Vite + React 18 + TypeScript + Tailwind v4 + react-router，pnpm 管理）。只调用 API，不放任何密钥。

## 目录约定

- `pages/` 路由级页面（ChatPage、Day25 KnowledgePage）
- `components/` 纯展示组件，不直接 fetch
- `api/` 唯一调用后端的地方（`client.ts`）
- `hooks/` 有状态逻辑（Day23 `useStreamingAnswer`）
- `lib/` 纯函数（Day23 SSE 解析）
- `types/` `api.ts`（由 `pnpm gen:api` 生成，勿手改）+ `ui.ts`（手写 UI 类型）

## 常用命令

```bash
pnpm install              # 安装依赖
pnpm dev                  # 启动 Vite（http://localhost:5173，经代理调用 :8000）
pnpm gen:api              # 从运行中的 API 生成 src/types/api.ts（需先 make dev）
pnpm exec tsc --noEmit -p tsconfig.app.json   # 类型检查
pnpm build                # tsc -b && vite build
```

## 开发期代理

浏览器只访问 `http://localhost:5173`，`/v1/*` 由 Vite 代理到 `http://127.0.0.1:8000`（同源，无 CORS）。生产环境由 Caddy 做同样的 `/v1` 反代（Day26）。
