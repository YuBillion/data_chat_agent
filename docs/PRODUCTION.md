# 生产治理与运维

## 1. 外部依赖

生产 Compose 只运行应用进程、Nginx 和 OTel Collector。以下依赖必须由外部托管或已有平台提供：

- PostgreSQL：harness 元数据、任务、事件、审批、审计和 LangGraph checkpoint 的权威存储。
- Redis：会话热缓存、事件流、限流和 Worker 唤醒。
- Langfuse：外部 trace 可视化。
- MySQL：现有元数据和 DW。
- Qdrant / Elasticsearch / TEI：现有语义检索、全文检索和 Embedding。
- OIDC Provider：JWT issuer、audience 和 JWKS。

应用不会在启动时自动创建生产表。`docker/docker-compose.prod.yaml` 的 `migrate` 服务必须先成功执行。

## 2. 启动前检查

1. PostgreSQL 与 Redis 使用 TLS 和独立应用账号。
2. `POSTGRES_DSN` 指向专用数据库；应用运行账号不应拥有 schema DDL 权限。`migrate` 使用独立 `POSTGRES_MIGRATION_DSN`。
3. `OIDC_ISSUER`、`OIDC_AUDIENCE`、`OIDC_JWKS_URL` 完整。
4. `DEV_AUTH_ENABLED=false`；生产配置校验会拒绝匿名模式。
5. `TRUSTED_HOSTS` 和 `CORS_ALLOWED_ORIGINS` 只包含正式域名。
6. `LLM_API_KEY` 从 Secret 注入，不写入镜像或仓库。
7. Langfuse 和 OTel Upstream 连通，默认关闭原始内容采集。
8. 上游 OIDC Gateway 注入受信任的 Bearer JWT；FastAPI 仍会重新校验签名和 claims。
9. MySQL DW 账号仍为现有账号时必须加强网络 ACL、数据库审计和 SQL Guard 监控；条件允许时切换只读账号。

启动：

```bash
docker compose -f docker/docker-compose.prod.yaml --env-file .env up --build -d
```

检查：

```bash
curl https://agent.example.com/health/live
curl https://agent.example.com/health/ready
docker compose -f docker/docker-compose.prod.yaml ps
docker compose -f docker/docker-compose.prod.yaml logs --tail=200 api worker
```

## 3. 数据与保留

| 数据 | 默认保留 | 清理 |
| --- | --- | --- |
| 会话内容、消息、SQL 与运行结果 | 30 天 | 过期后正文脱敏，会话不再对外可见 |
| 运行事件 | 7 天 | Worker 周期清理 |
| 人工任务与审计 | 180 天 | Worker 周期清理 |
| 会话/运行最小审计元数据 | 180 天 | 脱敏后到期硬删除 |
| LangGraph checkpoint | 30 天 | Worker 通过 saver 删除 |
| Redis 会话快照 | 15 分钟 TTL | 自动过期 |
| Redis 事件流 | 1 小时 TTL | 自动过期 |

PostgreSQL 是备份重点；Redis 不保存不可恢复数据。建议托管 PostgreSQL 开启时间点恢复，至少每日全量备份并定期演练恢复。备份不得包含未经脱敏的 Langfuse 导出内容。

清理任务使用 PostgreSQL Advisory Lock，多 Worker 部署不会重复执行同一批清理。

## 4. 监控与告警

建议告警：

- `/health/ready` 连续失败 2 分钟。
- 队列最老任务超过 30 秒或队列达到 80% 上限。
- Worker lease 丢失或任务重试率超过 5%。
- 运行失败率 5 分钟超过 5%。
- SQL timeout、Guard 拒绝或审批拒绝率异常上升。
- wait_human 超过 24 小时未处理。
- PostgreSQL、Redis、LLM、Embedding 的 p95 延迟超过 SLO。
- OTel exporter 队列丢弃数大于 0。

核心指标和 trace 已包含 `run_id`、`session_id`、`agent_id`、`agent_version`、状态、耗时和 token 桶，不包含查询原文或结果内容。

## 5. Redis 降级

- Redis 故障时，已接受运行继续通过 PostgreSQL 执行。
- SSE 自动回退为 PostgreSQL 事件轮询。
- 新运行因无法执行严格分布式限流而返回 503。
- 审批决定仍可通过 PostgreSQL 提交，恢复 Redis 后事件继续分发。
- 恢复时不从缓存回填权威状态；缓存按 TTL 重建。

## 6. PostgreSQL 故障

PostgreSQL 不可用时：

- API readiness 失败，新运行返回 503。
- 已建立 Worker 运行无法写 checkpoint，执行停止并按租约重试。
- 不得由 Redis 单独恢复运行；待 PostgreSQL 恢复后由 Worker 使用 checkpoint 继续。

## 7. 发布与回滚

1. 备份数据库并为当前镜像固定不可变 tag。
2. 执行只增不减的 Alembic 迁移。
3. 先启动新 Worker，确认其可以领取任务且 N-1 Agent checkpoint 可恢复。
4. 再替换 API。
5. 运行 Agent 列表、创建运行、SSE、HITL 和取消冒烟测试。
6. 保留上一版镜像；回滚只切换应用镜像，不立即回退已执行迁移。

含破坏性 schema 变更时使用“扩展、双读写、迁移、收缩”两个以上发布周期，不在同一次发布中删除旧列。

## 8. 容量检查

验收目标为：

- 单实例 200 个持续 SSE。
- 20 次新运行/秒成功入队。
- 断线后按事件序号无丢失、无重复。
- Worker 重启后任务可恢复且审批不重复执行。

API 只做校验和入队；真正吞吐由 Worker、模型 API、Embedding、MySQL 和 Qdrant 的 p95 决定。必须用与生产相近的模型限流和数据库规模压测，不能只测入队接口。
