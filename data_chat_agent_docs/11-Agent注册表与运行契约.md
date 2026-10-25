# 11 - 电商问数：Agent 注册表与运行契约

---

**本章目标：**

- 理解代码定义、静态构建的 Agent 注册表。
- 掌握 `AgentDefinition` 的版本、工具、Prompt 和策略契约。
- 理解注册表校验与运行快照。

**对应源码：** `app/agents/types.py`、`app/agents/registry.py`、`app/agents/defaults.py`

---

## 1、为什么不从 HTTP 注册 Agent

允许运行时上传 Prompt 或 Python import path 会直接引入远程代码执行风险。当前注册表在进程启动时由代码显式构建：

```python
AgentRegistry(
    (ANALYTICS_SQL_AGENT, CATALOG_QA_AGENT),
    settings,
)
```

配置文件只能启用已知 Agent，不能注入新模块。

## 2、AgentDefinition

核心字段：

```python
@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    version: str
    capabilities: tuple[str, ...]
    state_schema_version: str
    prompt_ids: tuple[str, ...]
    graph_factory: Callable[[], Any]
    allowed_tools: frozenset[str]
    model_profile: str
    policy_profile: str
```

`frozen=True` 表示启动后不可修改。

## 3、启动校验

注册表会检查：

- ID 格式与唯一性。
- 语义版本格式。
- Graph factory 可调用。
- Tool 名称属于已知集合。
- Prompt 文件存在且可计算 SHA-256。
- `ENABLED_AGENT_IDS` 引用的 Agent 已注册。

启动失败优于运行到一半才发现 Prompt 或工具缺失。

## 4、Prompt 版本

每次运行在 `route_json` 中保存：

- Agent 版本
- State schema 版本
- Prompt ID 到 SHA-256 的映射
- Model profile

这样可回答“这次结果使用了哪一版 Agent 和 Prompt”。

## 5、工具白名单

`analytics_sql` 可使用目录、向量、全文检索和 SQL 工具。

`catalog_qa` 只允许目录和向量工具，不允许 SQL 执行。

`app/harness/tool_access.py` 在运行时检查：

```python
definition = context["registry"].get(agent_id)
if tool_name not in definition.allowed_tools:
    raise ForbiddenError(...)
```

注册表不只是展示信息，也参与执行权限。

## 6、公共查询接口

```text
GET /api/v1/agents
GET /api/v1/agents/{agent_id}
```

只返回用户可读信息，不暴露内部 import path、源码、Prompt 正文或 Secret。

## 7、版本与发布

- 一次只把一个 Agent 版本设为默认。
- 运行固定保存所选版本。
- 等待审批的运行可能跨越一次发布。
- 发布前保留 N-1 兼容图；无法兼容时明确失败。
- 删除旧版本前确认没有活动运行依赖。

## 8、新增 Agent 的契约

新增步骤：

1. 建立独立 `graph.py`、State、Prompt 和工具白名单。
2. 导出不可变 `AgentDefinition`。
3. 在默认注册表显式加入。
4. 增加公开视图测试。
5. 增加路由黄金集和工具失败边界。
6. 更新文档与源码地图。

不得从数据库、环境变量或请求中动态 import 可执行代码。

## 9、常见问题

### 9.1 运行中修改 AgentDefinition 会怎样？

不支持。运行使用启动时固定的定义；修改代码需要重新发布。

### 9.2 某个 Agent 无法使用可用工具却声明允许

启动校验只验证已知名称，具体工具连接错误由执行阶段暴露，不会静默成功。

### 9.3 为什么能力描述也属于运行契约？

Router 使用能力描述进行候选预筛和模型路由；描述不清晰会直接降低路由质量。

---

**本章小结：**

注册表把 Agent 的代码入口、版本、Prompt、模型、策略和工具权限变成可验证契约。它既是路由数据源，也是运行安全和审计边界。

[上一章：LangGraph 与 Checkpoint](10-LangGraph、Checkpoint与中断恢复基础.md) | [文档导航](README.md) | [下一章：Agent Router](12-Agent%20Router与低置信度选择.md)
