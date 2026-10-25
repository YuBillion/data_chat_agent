# 智能问数 Multi-Agent Harness

基于 FastAPI、LangGraph、PostgreSQL 和 Redis 的生产化问数 Agent Harness。系统保留原有字段/指标/值混合检索与 Text-to-SQL 能力，同时提供多 Agent 注册与路由、跨请求 Human-in-the-Loop、持久 checkpoint、异步 Worker、SQL 安全治理、OIDC、限流、审计、OpenTelemetry 和 Langfuse 观测。

## 教程

完整中文教程位于 [data_chat_agent_docs/README.md](data_chat_agent_docs/README.md)，按“数据基础 → Agent/Harness → 生产治理 → 运维扩展”重新编排，共 29 个章节。`app` 下所有非空源码行均带中文说明；注释覆盖、AST 不变和行为回归由测试验证。

## Agent

| Agent | 用途 | 工具边界 |
| --- | --- | --- |
| `analytics_sql` | 查询真实业务数据，生成、校验、审批并执行只读 SQL | 目录/向量/全文检索、SQL Guard、EXPLAIN、受控执行 |
| `catalog_qa` | 回答表、字段和指标定义与口径 | 只读元数据与目录检索，禁止 SQL 和真实数仓查询 |

Agent 注册表由代码静态构建，不从数据库或 HTTP 加载可执行代码。请求可以显式指定 Agent；未指定时依次尝试确定性规则、结构化 LLM Router。路由器置信度不足时通过 LangGraph `interrupt()` 暂停并请求用户选择。

## 架构

```text
Browser
  -> OIDC/JWT Gateway -> Nginx
  -> FastAPI API -----------------> PostgreSQL
        |                            sessions/runs/events/jobs/audit
        |                            human interventions
        |                            LangGraph checkpoints
        +-> Redis                    hot session cache, event stream,
        |                            rate limit, worker wake-up
        v
     FastAPI Worker -> Harness Graph
                         -> route_agent
                         -> analytics_sql | catalog_qa
                         -> human interrupt / resume
                         -> MySQL / Qdrant / Elasticsearch / LLM
```

PostgreSQL 是唯一权威状态源。Redis 只保存可重建的热会话、流式事件和临时控制数据，清空 Redis 不会丢失运行状态。

## 目录

```text
app/
  agents/          Agent 注册、analytics_sql、catalog_qa
  harness/         运行、队列、Checkpoint、事件、路由、审批、Worker
  api/             FastAPI v1、兼容接口、Pydantic 契约
  auth/            OIDC/JWT 与角色
  tools/           SQL Guard、受控 MySQL 执行
  observability/   OpenTelemetry、Langfuse、指标
  repositories/    现有 MySQL/Qdrant/Elasticsearch 数据访问
  services/        元数据知识库构建
migrations/        PostgreSQL harness schema
prompts/           版本化 Prompt
evals/             路由黄金集与实时评估脚本
frontend/          React Agent/HITL 界面
docker/            本地依赖和生产 Compose
tests/             不依赖真实模型的单元测试
data_chat_agent_docs/ 29 章模块化教程与 Mermaid 架构图
```

## 运行预算

- 单次运行最多 10 次 LLM 调用、64k tokens、180 秒有效执行。
- SQL 最多自动校正 1 次，校正后必须重新校验。
- 人工等待默认 24 小时，不计入 180 秒执行预算。
- 查询最多返回 1000 行、2 MiB；SQL 数据库超时 15 秒。
- 会话和结果默认保留 30 天，事件 7 天，审批/审计 180 天。

数值均可在环境变量中覆盖，不在节点内散落配置。

## 本地准备

需要 Python 3.12+、uv、Node.js、pnpm、Docker，以及可访问的 PostgreSQL 和 Redis。

```bash
cp .env.example .env
uv sync --all-groups
```

在 `.env` 中至少设置：

```dotenv
POSTGRES_DSN=postgresql://user:password@host:5432/data_chat_agent
POSTGRES_MIGRATION_DSN=postgresql://migration:password@host:5432/data_chat_agent
REDIS_URL=redis://host:6379/0
LLM_API_KEY=...
META_DB_PASSWORD=...
DW_DB_PASSWORD=...
```

开发环境可使用 `DEV_AUTH_ENABLED=true`。生产环境会拒绝匿名开发身份，并要求完整的 OIDC issuer、audience 和 JWKS URL。

启动本地 MySQL、Qdrant、Elasticsearch、Kibana 和 Embedding：

```bash
docker compose -f docker/docker-compose.yaml --env-file .env up -d
```

构建元数据知识库：

```bash
uv run python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
```

执行 harness 迁移并创建 LangGraph checkpoint 表：

```bash
uv run python -m app.scripts.migrate
```

分别启动 API 和 Worker：

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
uv run python -m app.worker_main
```

启动前端：

```bash
cd frontend
pnpm install
pnpm dev
```

## API 流程

```text
GET    /api/v1/agents
POST   /api/v1/sessions
POST   /api/v1/sessions/{session_id}/runs
GET    /api/v1/runs/{run_id}/events?after_seq=0
GET    /api/v1/runs/{run_id}
GET    /api/v1/runs/{run_id}/interventions
POST   /api/v1/interventions/{id}/respond
POST   /api/v1/runs/{run_id}/cancel
GET    /health/live
GET    /health/ready
```

创建会话：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sessions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <jwt-or-dev-bypass>' \
  -d '{"title":"季度经营分析"}'
```

创建运行：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sessions/<session-id>/runs \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: <uuid>' \
  -H 'Authorization: Bearer <jwt>' \
  -d '{"query":"统计 2025 年第一季度各大区的 GMV","agent_id":null}'
```

接口立即返回 `202`。通过 `/events` 建立可续传 SSE；断线后使用 `Last-Event-ID` 或 `after_seq` 恢复。事件包括 Agent 选择、节点进度、人工任务、部分 Agent 结果和最终状态。

### HITL

- 自动路由低置信度：返回 `agent_selection_required`，用户提交 `select`。
- SQL 经校正、敏感字段或高扫描风险命中策略：返回 `sql.approval_required`。
- SQL 审批动作：`approve`、`edit`、`reject`。
- 高风险 SQL 必须由同租户、不同于发起人的 `agent:approver` 审批。
- 修改 SQL 后重新执行 AST Guard、目录白名单、EXPLAIN、风险和预算检查。
- 审批只对对应 SQL 哈希和版本有效。

响应示例：

```json
{
  "expected_version": 1,
  "action": "approve",
  "reason": "口径和扫描范围已确认"
}
```

旧 `/api/query` 已标记弃用，仅作为 90 天兼容适配器；完整 HITL 必须使用 v1 API。

## SQL 安全

实际执行前依次完成：

1. `sqlglot` MySQL AST 解析，只允许单条 SELECT/UNION/CTE。
2. 拒绝 DML、DDL、多语句、文件/危险函数、系统库、行锁和目录外对象。
3. 使用已解析表字段白名单，不接受模型新增的目录外对象。
4. `EXPLAIN` 成功后计算风险；敏感或高扫描量进入审批。
5. 只读会话、数据库执行时限、应用级 timeout、行数和字节上限。
6. 执行 SQL 的规范化哈希必须与审批哈希一致。

当前部署选择继续使用现有 DW 账号，因此应用层防护是主边界。残留风险和后续切换独立只读账号的建议见 [生产治理](docs/PRODUCTION.md)。

## 可观测性

- OpenTelemetry 自动采集 FastAPI、HTTPX、SQLAlchemy、Redis 链路。
- API 将 W3C `traceparent` 写入 Job，Worker 恢复后形成跨进程 trace。
- Langfuse 使用外部实例：设置 `LANGFUSE_HOST`、`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`。
- 默认不在日志和 Langfuse 中记录完整问题、SQL、结果、JWT 或密钥。
- `/metrics` 提供 OpenTelemetry/Prometheus 指标，仅应暴露给内网监控。

结构化日志写入 stdout，兼容容器日志采集。

## 测试与评估

```bash
uv run ruff check app main.py migrations tests
uv run pytest tests/unit -q
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

单元测试使用 stub/fixture，不调用真实模型或外部 API。路由实时评估需要已配置模型：

```bash
uv run python -m evals.run_router_eval --threshold 0.8
```

经批准的测试环境可以运行真实 HTTP/SSE 压测：

```bash
LOAD_TEST_JWT='<token>' uv run python scripts/load_test.py \
  --base-url https://agent-test.example.com \
  --connections 200 \
  --rate 20
```

该脚本会产生真实模型和数仓调用，不应在未授权环境中运行。

PostgreSQL、Redis、真实 MySQL/Qdrant/ES 和 Compose 端到端验证需要外部运行环境，不能由纯单元测试替代。

## 生产部署

```bash
cp .env.example .env
# 填写生产 OIDC、外部 PostgreSQL/Redis、Langfuse 和数据服务
docker compose -f docker/docker-compose.prod.yaml up --build -d
```

生产 Compose 包含 API、Worker、Web/Nginx、OTel Collector 和一次性迁移任务；PostgreSQL、Redis、Langfuse 及现有数据服务使用外部端点。完整部署、备份、监控和降级说明见 [docs/PRODUCTION.md](docs/PRODUCTION.md)。

## 约束

- 首版为单租户组织模型，不使用不存在的行级 `tenant_id` 改写业务 SQL。
- `tenant_id` 用于身份、配额、会话和审计隔离。
- 不动态上传 Agent 或插件，不接收任意 Python import path。
- 不修改 MySQL 初始化数据、ES 插件、Embedding 模型或生成目录。
