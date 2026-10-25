# 智能问数 Multi-Agent Harness 教程

本目录围绕当前 `data_chat_agent` 重构版编写。教程覆盖数据仓库、元数据知识库、LangGraph、多 Agent 注册与路由、PostgreSQL Checkpoint、Redis 热层、FastAPI/Worker、HITL、安全、观测、前端和生产部署。

## 学习顺序

### 第一部分：业务与数据基础

1. [00 - 前言与学习路径](00-前言与学习路径.md)
2. [01 - 项目概述与数仓基础](01-项目概述与数仓基础.md)
3. [02 - Harness 总体架构与请求生命周期](02-Harness总体架构与请求生命周期.md)
4. [03 - 开发环境与生产依赖准备](03-开发环境与生产依赖准备.md)
5. [04 - 项目结构、配置与异步基础设施](04-项目结构、配置与异步基础设施.md)
6. [05 - Qdrant 与 Elasticsearch 接入](05-Qdrant与Elasticsearch接入.md)
7. [06 - MySQL、Embedding 与仓储基础](06-MySQL、Embedding与仓储基础.md)
8. [07 - 元数据知识库总览与构建入口](07-元数据知识库总览与构建入口.md)
9. [08 - 表与字段元数据同步](08-表与字段元数据同步.md)
10. [09 - 字段、指标与值索引构建](09-字段、指标与值索引构建.md)

### 第二部分：Agent 与 Harness

11. [10 - LangGraph、Checkpoint 与中断恢复](10-LangGraph、Checkpoint与中断恢复基础.md)
12. [11 - Agent 注册表与运行契约](11-Agent注册表与运行契约.md)
13. [12 - Agent Router 与低置信度选择](12-Agent%20Router与低置信度选择.md)
14. [13 - Harness Graph 与双 Agent 子图](13-Harness%20Graph与双Agent子图.md)
15. [14 - 多轮查询规划与并行召回](14-多轮查询规划与并行召回.md)
16. [15 - 召回合并、过滤与 SQL 上下文](15-召回合并、过滤与SQL上下文.md)
17. [16 - SQL 生成、Guard、EXPLAIN 与校正](16-SQL生成、Guard、EXPLAIN与校正.md)
18. [17 - Human-in-the-Loop 与四眼审批](17-Human-in-the-Loop与四眼审批.md)
19. [18 - PostgreSQL 持久化、队列与 Checkpointer](18-PostgreSQL持久化、任务队列与Checkpointer.md)
20. [19 - Redis 热缓存、事件流与降级](19-Redis热缓存、事件流与降级.md)
21. [20 - FastAPI v1 API、SSE 与兼容层](20-FastAPI%20v1%20API、SSE与兼容层.md)
22. [21 - 应用装配、Worker 与异步高并发](21-应用装配、Worker与异步高并发.md)

### 第三部分：生产治理

23. [22 - OIDC、RBAC 与 SQL 安全治理](22-OIDC、RBAC与SQL安全治理.md)
24. [23 - OpenTelemetry、Langfuse 与结构化日志](23-OpenTelemetry、Langfuse与结构化日志.md)
25. [24 - 预算、限流、审计与数据保留](24-预算、限流、审计与数据保留.md)
26. [25 - 前端 Agent 选择、SSE 与审批交互](25-前端Agent选择、SSE与审批交互.md)
27. [26 - 测试、路由评估与压力验证](26-测试、路由评估与压力验证.md)
28. [27 - Docker Compose 生产部署与运维](27-Docker%20Compose生产部署与运维.md)
29. [28 - 源码模块地图、调试与扩展指南](28-源码模块地图、调试与扩展指南.md)

## 源码与验证

- 项目源码：`../data_chat_agent`
- 后端测试：`uv run pytest tests/unit -q`
- 代码检查：`uv run ruff check app main.py migrations tests evals scripts`
- 前端检查：`pnpm --dir frontend lint && pnpm --dir frontend test && pnpm --dir frontend build`

## 阅读约定

- 所有路径均相对于 `data_chat_agent` 项目根目录。
- “源码”指重构后的仓库，不以历史教程或已删除模块为准。
- Mermaid 图描述实际状态流；旧版截图只在内容仍准确时引用。
- `app` 中每个非空代码行都有中文注释，文档只摘取关键片段。
- 本地无法验证的 Docker、PostgreSQL、Redis、真实 LLM 和 Langfuse 项必须明确报告。
