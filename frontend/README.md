# Agent Harness Frontend

React 19 + TypeScript + Vite 前端，对接 FastAPI v1 会话、运行、SSE 和 Human-in-the-Loop 接口。

功能：

- Agent 自动路由或显式选择。
- 自动路由低置信度时选择 Agent。
- SQL 批准、修改和拒绝。
- SSE 断线后按事件序号续传。
- 服务端会话历史和运行状态。

开发：

```bash
pnpm install
pnpm dev
```

Vite 将 `/api` 代理到 `VITE_DEV_PROXY_TARGET`，默认 `http://127.0.0.1:8000`。认证应由上游 OIDC Gateway 注入 Bearer JWT；本地后端可使用 `DEV_AUTH_ENABLED=true`。

验证：

```bash
pnpm lint
pnpm test
pnpm build
```

生产镜像使用 `Dockerfile` 构建静态资源，由 Nginx 同域反代 API 并关闭 SSE 缓冲。
