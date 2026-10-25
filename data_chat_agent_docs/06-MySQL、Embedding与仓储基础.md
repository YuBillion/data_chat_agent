# 06 - 电商问数：MySQL、Embedding 与仓储基础

---

**本章目标：**

- 理解 SQLAlchemy Engine、Session 与连接池。
- 掌握 Meta MySQL、DW MySQL 的职责边界。
- 理解 ScopedRepository 如何避免长调用占用数据库连接。

**对应源码：**

- `app/clients/mysql_client_manager.py`
- `app/repositories/scoped.py`
- `app/repositories/mysql/`
- `app/clients/embedding_client_manager.py`

---

## 1、两套 MySQL

| 数据库 | 内容 | 业务性质 |
| --- | --- | --- |
| Meta MySQL | `table_info`、`column_info`、`metric_info`、`column_metric` | 权威目录数据 |
| DW MySQL | `fact_order` 和维度表 | 被查询的业务数据 |

两套连接使用不同配置和连接池。DW 查询不应该和元数据补全共享 Session。

## 2、Engine 与 Session

`Engine` 长期维护连接池，`AsyncSession` 表示一次短生命周期数据库工作单元。

```python
async with session_factory() as session:
    result = await session.execute(statement)
```

Connection 池参数来自配置：

- `pool_size`
- `max_overflow`
- `pool_timeout`
- `pool_pre_ping`
- `pool_recycle`
- `connect_timeout`

`pool_pre_ping` 处理被服务端断开的空闲连接，`expire_on_commit=False` 避免提交后属性访问触发隐式异步查询。

## 3、ScopedRepository

传统写法可能在整个 Agent 执行期间持有两个 Session。Agent 会等待 LLM 和 Qdrant 数秒甚至数分钟，长占用会迅速耗尽连接池。

`ScopedRepository` 的规则是：

```text
调用 repository.method(...)
  -> 创建 Session
  -> 创建具体 Repository
  -> await 方法
  -> 退出 async with 并归还连接
```

因此 Worker 可以维持较高协程并发，而 LLM 等待期间不会占 DB 连接。

## 4、事务

元数据构建包含多步写入。事务应包住同一业务事实：

```python
async with repository.session.begin():
    repository.save_table_infos(tables)
    repository.save_column_infos(columns)
```

注意：

- `session.add_all()` 只把对象加入 Session，不等同于数据库提交。
- 选择在 Service 层开启事务，Repository 只负责写操作。
- 异常退出 `async with` 时自动回滚。

## 5、ORM 与实体

- `models/`：SQLAlchemy 表映射。
- `entities/`：业务实体。
- `mappers/`：实体与 ORM 转换。

业务层处理 `ColumnInfo`，仓储对内使用 `ColumnInfoMySQL`。这样可以避免上层到处传播 ORM 对象或 Session。

## 6、异步 MySQL 驱动

SQLAlchemy 提供抽象层，`asyncmy` 提供 MySQL 异步协议支持。连接 URL 使用 `URL.create()` 构造，避免密码中的特殊字符破坏 URL 结构。

数据库异常必须保留，不可返回空列表。召回阶段“没有候选”和“依赖不可用”是不同语义。

## 7、Embedding

`EmbeddingClientManager` 管理 HuggingFace 兼容的 TEI Endpoint：

- 文档向量：`aembed_documents`
- 查询向量：`aembed_query`
- 模型名与地址来自配置

索引构建可以批量生成文档向量；在线召回一次或少量生成查询向量。

Embedding 的维度必须与 Qdrant collection 配置一致。模型更换属于索引格式变更，不能只改模型名而不重建向量集合。

## 8、日志

当前日志采用 stdout JSON，并带：

- request_id
- run_id
- trace_id
- module/function/line

不要记录完整 Prompt、用户问题、SQL、结果行或数据库凭据。

## 9、验证

```bash
uv run pytest tests/unit -q
uv run python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
```

检查：

- 元数据表字段类型和样例值是否写入。
- 异常是否让事务回滚。
- Worker 并发时 MySQL 连接池是否保持在配置上限内。

## 10、注意事项

- 不在模块 import 时建立网络连接。
- 不跨协程共享 AsyncSession。
- 不为一次简单查询创建新的 Engine。
- 不把 Engine 或 Session 序列化到 LangGraph State。
- 不将数据库连接错误吞成空检索结果。

---

**本章小结：**

MySQL 继续承担权威元数据和数仓数据，SQLAlchemy 负责连接池与事务，ScopedRepository 确保连接只在真实数据库调用期间被占用，Embedding 服务则为 Qdrant 提供稳定的向量来源。

[上一章：Qdrant 与 Elasticsearch](05-Qdrant与Elasticsearch接入.md) | [文档导航](README.md) | [下一章：元数据知识库](07-元数据知识库总览与构建入口.md)
