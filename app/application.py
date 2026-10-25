"""Application composition root for API and worker processes."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from contextlib import AsyncExitStack  # 从 contextlib 导入 AsyncExitStack，供本模块后续代码使用
from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用

from redis import RedisError  # 从 redis 导入 RedisError，供本模块后续代码使用

from app.agents.defaults import build_default_registry  # 从 app.agents.defaults 导入 build_default_registry，供本模块后续代码使用
from app.agents.registry import AgentRegistry  # 从 app.agents.registry 导入 AgentRegistry，供本模块后续代码使用
from app.auth.oidc import JWTValidator  # 从 app.auth.oidc 导入 JWTValidator，供本模块后续代码使用
from app.clients.embedding_client_manager import embedding_client_manager  # 从 app.clients.embedding_client_manager 导入 embedding_client_manager，供本模块后续代码使用
from app.clients.es_client_manager import es_client_manager  # 从 app.clients.es_client_manager 导入 es_client_manager，供本模块后续代码使用
from app.clients.mysql_client_manager import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    dw_mysql_client_manager,  # 从当前 import 模块导入符号 dw_mysql_client_manager
    meta_mysql_client_manager,  # 从当前 import 模块导入符号 meta_mysql_client_manager
)  # 结束多符号导入列表
from app.clients.qdrant_client_manager import qdrant_client_manager  # 从 app.clients.qdrant_client_manager 导入 qdrant_client_manager，供本模块后续代码使用
from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.harness.database import HarnessDatabase  # 从 app.harness.database 导入 HarnessDatabase，供本模块后续代码使用
from app.harness.events import EventPublisher  # 从 app.harness.events 导入 EventPublisher，供本模块后续代码使用
from app.harness.graph import build_harness_graph  # 从 app.harness.graph 导入 build_harness_graph，供本模块后续代码使用
from app.harness.redis_runtime import RedisRuntime  # 从 app.harness.redis_runtime 导入 RedisRuntime，供本模块后续代码使用
from app.harness.service import RunService  # 从 app.harness.service 导入 RunService，供本模块后续代码使用
from app.harness.store import HarnessStore  # 从 app.harness.store 导入 HarnessStore，供本模块后续代码使用
from app.harness.worker import HarnessWorker  # 从 app.harness.worker 导入 HarnessWorker，供本模块后续代码使用
from app.infrastructure.llm import ChatModelFactory  # 从 app.infrastructure.llm 导入 ChatModelFactory，供本模块后续代码使用
from app.observability.telemetry import Telemetry  # 从 app.observability.telemetry 导入 Telemetry，供本模块后续代码使用
from app.repositories.es.value_es_repository import ValueESRepository  # 从 app.repositories.es.value_es_repository 导入 ValueESRepository，供本模块后续代码使用
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository  # 从 app.repositories.qdrant.column_qdrant_repository 导入 ColumnQdrantRepository，供本模块后续代码使用
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository  # 从 app.repositories.qdrant.metric_qdrant_repository 导入 MetricQdrantRepository，供本模块后续代码使用
from app.tools.sql_execution import MySQLReadTool  # 从 app.tools.sql_execution 导入 MySQLReadTool，供本模块后续代码使用


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class ApplicationContainer:  # 定义类 ApplicationContainer，组织相关状态与行为
    settings: Settings  # 声明或继续传入参数 settings: Settings
    telemetry: Telemetry  # 声明或继续传入参数 telemetry: Telemetry
    database: HarnessDatabase  # 声明或继续传入参数 database: HarnessDatabase
    store: HarnessStore  # 声明或继续传入参数 store: HarnessStore
    redis: RedisRuntime  # 声明或继续传入参数 redis: RedisRuntime
    events: EventPublisher  # 声明或继续传入参数 events: EventPublisher
    registry: AgentRegistry  # 声明或继续传入参数 registry: AgentRegistry
    jwt_validator: JWTValidator  # 声明或继续传入参数 jwt_validator: JWTValidator
    run_service: RunService  # 声明或继续传入参数 run_service: RunService
    tool_semaphore: asyncio.Semaphore  # 声明或继续传入参数 tool_semaphore: asyncio.Semaphore
    run_worker: HarnessWorker | None = None  # 计算 None 并保存到变量 run_worker
    llm_factory: ChatModelFactory | None = None  # 计算 None 并保存到变量 llm_factory
    sql_read_tool: MySQLReadTool | None = None  # 计算 None 并保存到变量 sql_read_tool
    graph: Any = None  # 计算 None 并保存到变量 graph
    _exit_stack: AsyncExitStack | None = None  # 计算 None 并保存到变量 _exit_stack
    _worker_enabled: bool = False  # 计算 False 并保存到变量 _worker_enabled

    async def start(self, *, with_worker: bool) -> None:  # 定义异步函数 start，封装可被事件循环调度的协程逻辑
        self._worker_enabled = with_worker  # 将依赖或状态 with_worker 保存到实例属性 self._worker_enabled
        self.telemetry.setup()  # 调用 setup 执行当前步骤：self.telemetry.setup()
        self._exit_stack = AsyncExitStack()  # 将依赖或状态 AsyncExitStack() 保存到实例属性 self._exit_stack
        await self.database.ping()  # 等待异步操作完成并取得结果：self.database.ping()
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            await self.redis.ping()  # 等待异步操作完成并取得结果：self.redis.ping()
        except RedisError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError:
            logger.warning(  # 调用 warning 执行当前步骤：logger.warning(
                "Redis is unavailable at startup; entering degraded mode"  # 在函数 start 中执行表达式 "Redis is unavailable at startup; entering degraded mode"，推进当前业务流程
            )  # 结束函数 start 的参数及返回类型声明并开始函数体
        self.telemetry.instrument_engine(self.database.engine)  # 调用 instrument_engine 执行当前步骤：self.telemetry.instrument_engine(self.database.engine)

        if not with_worker:  # 判断分支条件：if not with_worker:
            logger.info("API application container started")  # 调用 info 执行当前步骤：logger.info("API application container started")
            return  # 提前返回空结果，结束当前函数调用

        self._initialize_data_clients()  # 调用 _initialize_data_clients 执行当前步骤：self._initialize_data_clients()
        self.llm_factory = ChatModelFactory(self.settings)  # 将依赖或状态 ChatModelFactory(self.settings) 保存到实例属性 self.llm_factory
        dw_engine = dw_mysql_client_manager.engine  # 计算 dw_mysql_client_manager.engine 并保存到变量 dw_engine
        if dw_engine is None:  # 判断分支条件：if dw_engine is None:
            raise RuntimeError("DW MySQL engine was not initialized")  # 抛出明确异常，阻止错误状态被静默接受：RuntimeError("DW MySQL engine was not initialized")
        self.sql_read_tool = MySQLReadTool(  # 将依赖或状态 MySQLReadTool( 保存到实例属性 self.sql_read_tool
            dw_engine,  # 继续向上一处调用或声明传入 dw_engine
            timeout_ms=self.settings.sql_timeout_ms,  # 为 MySQLReadTool 设置关键字参数 timeout_ms，传入当前行给出的值
            max_rows=self.settings.result_max_rows,  # 为 MySQLReadTool 设置关键字参数 max_rows，传入当前行给出的值
            max_bytes=self.settings.result_max_bytes,  # 为 MySQLReadTool 设置关键字参数 max_bytes，传入当前行给出的值
        )  # 结束函数 start 的参数及返回类型声明并开始函数体

        from app.harness.checkpoints import open_postgres_checkpointer  # 从 app.harness.checkpoints 导入 open_postgres_checkpointer，供本模块后续代码使用

        checkpointer = await self._exit_stack.enter_async_context(  # 等待 enter_async_context 完成，并将其结果保存到 checkpointer
            open_postgres_checkpointer(self.settings)  # 调用 open_postgres_checkpointer 执行当前步骤：open_postgres_checkpointer(self.settings)
        )  # 结束函数 start 的参数及返回类型声明并开始函数体
        self.graph = build_harness_graph(self.registry, checkpointer)  # 将依赖或状态 build_harness_graph(self.registry, checkpointer) 保存到实例属性 self.graph
        column_repository = ColumnQdrantRepository(qdrant_client_manager.client)  # 计算 ColumnQdrantRepository(qdrant_client_manager.client) 并保存到变量 column_repository
        metric_repository = MetricQdrantRepository(qdrant_client_manager.client)  # 计算 MetricQdrantRepository(qdrant_client_manager.client) 并保存到变量 metric_repository
        value_repository = ValueESRepository(es_client_manager.client)  # 计算 ValueESRepository(es_client_manager.client) 并保存到变量 value_repository
        self.run_worker = HarnessWorker(  # 将依赖或状态 HarnessWorker( 保存到实例属性 self.run_worker
            settings=self.settings,  # 为 HarnessWorker 设置关键字参数 settings，传入当前行给出的值
            store=self.store,  # 为 HarnessWorker 设置关键字参数 store，传入当前行给出的值
            redis=self.redis,  # 为 HarnessWorker 设置关键字参数 redis，传入当前行给出的值
            events=self.events,  # 为 HarnessWorker 设置关键字参数 events，传入当前行给出的值
            registry=self.registry,  # 为 HarnessWorker 设置关键字参数 registry，传入当前行给出的值
            telemetry=self.telemetry,  # 为 HarnessWorker 设置关键字参数 telemetry，传入当前行给出的值
            graph=self.graph,  # 为 HarnessWorker 设置关键字参数 graph，传入当前行给出的值
            llm_factory=self.llm_factory,  # 为 HarnessWorker 设置关键字参数 llm_factory，传入当前行给出的值
            sql_read_tool=self.sql_read_tool,  # 为 HarnessWorker 设置关键字参数 sql_read_tool，传入当前行给出的值
            meta_session_factory=meta_mysql_client_manager.session_factory,  # 为 HarnessWorker 设置关键字参数 meta_session_factory，传入当前行给出的值
            dw_session_factory=dw_mysql_client_manager.session_factory,  # 为 HarnessWorker 设置关键字参数 dw_session_factory，传入当前行给出的值
            column_qdrant_repository=column_repository,  # 为 HarnessWorker 设置关键字参数 column_qdrant_repository，传入当前行给出的值
            metric_qdrant_repository=metric_repository,  # 为 HarnessWorker 设置关键字参数 metric_qdrant_repository，传入当前行给出的值
            value_es_repository=value_repository,  # 为 HarnessWorker 设置关键字参数 value_es_repository，传入当前行给出的值
            embedding_client=embedding_client_manager.client,  # 为 HarnessWorker 设置关键字参数 embedding_client，传入当前行给出的值
            tool_semaphore=self.tool_semaphore,  # 为 HarnessWorker 设置关键字参数 tool_semaphore，传入当前行给出的值
            checkpointer=checkpointer,  # 为 HarnessWorker 设置关键字参数 checkpointer，传入当前行给出的值
        )  # 结束函数 start 的参数及返回类型声明并开始函数体
        await self.run_worker.start()  # 等待异步操作完成并取得结果：self.run_worker.start()
        logger.info("Worker application container started")  # 调用 info 执行当前步骤：logger.info("Worker application container started")

    async def close(self) -> None:  # 定义异步函数 close，封装可被事件循环调度的协程逻辑
        if self.run_worker is not None:  # 判断分支条件：if self.run_worker is not None:
            await self.run_worker.stop()  # 等待异步操作完成并取得结果：self.run_worker.stop()
        if self._worker_enabled:  # 判断分支条件：if self._worker_enabled:
            await qdrant_client_manager.close()  # 等待异步操作完成并取得结果：qdrant_client_manager.close()
            await es_client_manager.close()  # 等待异步操作完成并取得结果：es_client_manager.close()
            await meta_mysql_client_manager.close()  # 等待异步操作完成并取得结果：meta_mysql_client_manager.close()
            await dw_mysql_client_manager.close()  # 等待异步操作完成并取得结果：dw_mysql_client_manager.close()
        if self._exit_stack is not None:  # 判断分支条件：if self._exit_stack is not None:
            await self._exit_stack.aclose()  # 等待异步操作完成并取得结果：self._exit_stack.aclose()
        await self.redis.close()  # 等待异步操作完成并取得结果：self.redis.close()
        await self.database.close()  # 等待异步操作完成并取得结果：self.database.close()
        await self.jwt_validator.close()  # 等待异步操作完成并取得结果：self.jwt_validator.close()
        self.telemetry.shutdown()  # 调用 shutdown 执行当前步骤：self.telemetry.shutdown()

    def _initialize_data_clients(self) -> None:  # 定义函数 _initialize_data_clients，封装该模块的一项明确职责
        qdrant_client_manager.init()  # 调用 init 执行当前步骤：qdrant_client_manager.init()
        embedding_client_manager.init()  # 调用 init 执行当前步骤：embedding_client_manager.init()
        es_client_manager.init()  # 调用 init 执行当前步骤：es_client_manager.init()
        meta_mysql_client_manager.init()  # 调用 init 执行当前步骤：meta_mysql_client_manager.init()
        dw_mysql_client_manager.init()  # 调用 init 执行当前步骤：dw_mysql_client_manager.init()


def create_container(  # 定义函数 create_container，封装该模块的一项明确职责
    settings: Settings,  # 为函数 create_container 声明参数 settings 及其类型或默认值
    *,  # 为函数 create_container 声明参数 * 及其类型或默认值
    redis_runtime: RedisRuntime | None = None,  # 为函数 create_container 声明参数 redis_runtime 及其类型或默认值
) -> ApplicationContainer:  # 结束 create_container 的参数列表并声明返回类型
    telemetry = Telemetry(settings)  # 计算 Telemetry(settings) 并保存到变量 telemetry
    database = HarnessDatabase(settings)  # 计算 HarnessDatabase(settings) 并保存到变量 database
    store = HarnessStore(database.session_factory)  # 计算 HarnessStore(database.session_factory) 并保存到变量 store
    redis = redis_runtime or RedisRuntime(settings)  # 计算 redis_runtime or RedisRuntime(settings) 并保存到变量 redis
    events = EventPublisher(store, redis, telemetry)  # 计算 EventPublisher(store, redis, telemetry) 并保存到变量 events
    registry = build_default_registry(settings)  # 计算 build_default_registry(settings) 并保存到变量 registry
    jwt_validator = JWTValidator(settings)  # 计算 JWTValidator(settings) 并保存到变量 jwt_validator
    run_service = RunService(  # 调用 RunService 构造结果并保存到 run_service
        settings=settings,  # 为 RunService 设置关键字参数 settings，传入当前行给出的值
        store=store,  # 为 RunService 设置关键字参数 store，传入当前行给出的值
        redis=redis,  # 为 RunService 设置关键字参数 redis，传入当前行给出的值
        events=events,  # 为 RunService 设置关键字参数 events，传入当前行给出的值
        registry=registry,  # 为 RunService 设置关键字参数 registry，传入当前行给出的值
        telemetry=telemetry,  # 为 RunService 设置关键字参数 telemetry，传入当前行给出的值
    )  # 结束函数 create_container 的参数及返回类型声明并开始函数体
    tool_semaphore = asyncio.Semaphore(  # 调用 Semaphore 构造结果并保存到 tool_semaphore
        settings.external_tool_max_concurrency  # 在函数 create_container 中执行表达式 settings.external_tool_max_concurrency，推进当前业务流程
    )  # 结束函数 create_container 的参数及返回类型声明并开始函数体
    return ApplicationContainer(  # 返回 ApplicationContainer( 给调用方
        settings=settings,  # 为 ApplicationContainer 设置关键字参数 settings，传入当前行给出的值
        telemetry=telemetry,  # 为 ApplicationContainer 设置关键字参数 telemetry，传入当前行给出的值
        database=database,  # 为 ApplicationContainer 设置关键字参数 database，传入当前行给出的值
        store=store,  # 为 ApplicationContainer 设置关键字参数 store，传入当前行给出的值
        redis=redis,  # 为 ApplicationContainer 设置关键字参数 redis，传入当前行给出的值
        events=events,  # 为 ApplicationContainer 设置关键字参数 events，传入当前行给出的值
        registry=registry,  # 为 ApplicationContainer 设置关键字参数 registry，传入当前行给出的值
        jwt_validator=jwt_validator,  # 为 ApplicationContainer 设置关键字参数 jwt_validator，传入当前行给出的值
        run_service=run_service,  # 为 ApplicationContainer 设置关键字参数 run_service，传入当前行给出的值
        tool_semaphore=tool_semaphore,  # 为 ApplicationContainer 设置关键字参数 tool_semaphore，传入当前行给出的值
    )  # 结束函数 create_container 的参数及返回类型声明并开始函数体
