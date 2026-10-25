"""Runtime-only dependencies injected into LangGraph nodes."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from typing import Any, TypedDict  # 从 typing 导入 Any, TypedDict，供本模块后续代码使用

from langchain_huggingface import HuggingFaceEndpointEmbeddings  # 从 langchain_huggingface 导入 HuggingFaceEndpointEmbeddings，供本模块后续代码使用

from app.agents.registry import AgentRegistry  # 从 app.agents.registry 导入 AgentRegistry，供本模块后续代码使用
from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.harness.router import AgentRouter  # 从 app.harness.router 导入 AgentRouter，供本模块后续代码使用
from app.harness.store import HarnessStore  # 从 app.harness.store 导入 HarnessStore，供本模块后续代码使用
from app.harness.types import Identity, RunBudget  # 从 app.harness.types 导入 Identity, RunBudget，供本模块后续代码使用
from app.infrastructure.llm import RunLLM  # 从 app.infrastructure.llm 导入 RunLLM，供本模块后续代码使用
from app.observability.telemetry import Telemetry  # 从 app.observability.telemetry 导入 Telemetry，供本模块后续代码使用
from app.repositories.es.value_es_repository import ValueESRepository  # 从 app.repositories.es.value_es_repository 导入 ValueESRepository，供本模块后续代码使用
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository  # 从 app.repositories.mysql.dw.dw_mysql_repository 导入 DWMySQLRepository，供本模块后续代码使用
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository  # 从 app.repositories.mysql.meta.meta_mysql_repository 导入 MetaMySQLRepository，供本模块后续代码使用
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository  # 从 app.repositories.qdrant.column_qdrant_repository 导入 ColumnQdrantRepository，供本模块后续代码使用
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository  # 从 app.repositories.qdrant.metric_qdrant_repository 导入 MetricQdrantRepository，供本模块后续代码使用
from app.tools.sql_execution import MySQLReadTool  # 从 app.tools.sql_execution 导入 MySQLReadTool，供本模块后续代码使用
from app.tools.sql_guard import SQLGuard  # 从 app.tools.sql_guard 导入 SQLGuard，供本模块后续代码使用


class HarnessContext(TypedDict, total=False):  # 定义类 HarnessContext，组织相关状态与行为
    settings: Settings  # 声明或继续传入参数 settings: Settings
    identity: Identity  # 声明或继续传入参数 identity: Identity
    registry: AgentRegistry  # 声明或继续传入参数 registry: AgentRegistry
    router: AgentRouter  # 声明或继续传入参数 router: AgentRouter
    store: HarnessStore  # 声明或继续传入参数 store: HarnessStore
    telemetry: Telemetry  # 声明或继续传入参数 telemetry: Telemetry
    budget: RunBudget  # 声明或继续传入参数 budget: RunBudget
    llm: RunLLM  # 声明或继续传入参数 llm: RunLLM
    run_id: str  # 声明或继续传入参数 run_id: str
    session_id: str  # 声明或继续传入参数 session_id: str
    trace_id: str | None  # 声明或继续传入参数 trace_id: str | None

    column_qdrant_repository: ColumnQdrantRepository  # 声明或继续传入参数 column_qdrant_repository: ColumnQdrantRepository
    embedding_client: HuggingFaceEndpointEmbeddings  # 声明或继续传入参数 embedding_client: HuggingFaceEndpointEmbeddings
    metric_qdrant_repository: MetricQdrantRepository  # 声明或继续传入参数 metric_qdrant_repository: MetricQdrantRepository
    value_es_repository: ValueESRepository  # 声明或继续传入参数 value_es_repository: ValueESRepository
    meta_mysql_repository: MetaMySQLRepository  # 声明或继续传入参数 meta_mysql_repository: MetaMySQLRepository
    dw_mysql_repository: DWMySQLRepository  # 声明或继续传入参数 dw_mysql_repository: DWMySQLRepository
    sql_guard: SQLGuard  # 声明或继续传入参数 sql_guard: SQLGuard
    sql_read_tool: MySQLReadTool  # 声明或继续传入参数 sql_read_tool: MySQLReadTool
    tool_semaphore: asyncio.Semaphore  # 声明或继续传入参数 tool_semaphore: asyncio.Semaphore
    sensitive_columns: set[str]  # 声明或继续传入参数 sensitive_columns: set[str]
    business_timezone: str  # 声明或继续传入参数 business_timezone: str
    extra: dict[str, Any]  # 声明或继续传入参数 extra: dict[str, Any]
