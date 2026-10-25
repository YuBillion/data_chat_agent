"""Durable async worker for the multi-Agent LangGraph harness."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import dataclasses  # 导入dataclasses，建立本模块需要的外部能力引用
import os  # 导入os，建立本模块需要的外部能力引用
import socket  # 导入socket，建立本模块需要的外部能力引用
from datetime import date, datetime  # 从 datetime 导入 date, datetime，供本模块后续代码使用
from enum import Enum  # 从 enum 导入 Enum，供本模块后续代码使用
from types import SimpleNamespace  # 从 types 导入 SimpleNamespace，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用
from uuid import UUID, uuid4  # 从 uuid 导入 UUID, uuid4，供本模块后续代码使用

from langgraph.types import Command  # 从 langgraph.types 导入 Command，供本模块后续代码使用

from app.agents.registry import AgentRegistry  # 从 app.agents.registry 导入 AgentRegistry，供本模块后续代码使用
from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.core.context import run_id_ctx_var  # 从 app.core.context 导入 run_id_ctx_var，供本模块后续代码使用
from app.core.errors import AppError, ConflictError, DependencyUnavailableError  # 从 app.core.errors 导入 AppError, ConflictError, DependencyUnavailableError，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.harness.context import HarnessContext  # 从 app.harness.context 导入 HarnessContext，供本模块后续代码使用
from app.harness.events import EventPublisher  # 从 app.harness.events 导入 EventPublisher，供本模块后续代码使用
from app.harness.records import JobRecord, RunRecord  # 从 app.harness.records 导入 JobRecord, RunRecord，供本模块后续代码使用
from app.harness.redis_runtime import RedisRuntime  # 从 app.harness.redis_runtime 导入 RedisRuntime，供本模块后续代码使用
from app.harness.router import AgentRouter  # 从 app.harness.router 导入 AgentRouter，供本模块后续代码使用
from app.harness.store import HarnessStore  # 从 app.harness.store 导入 HarnessStore，供本模块后续代码使用
from app.harness.types import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    TERMINAL_RUN_STATUSES,  # 从当前 import 模块导入符号 TERMINAL_RUN_STATUSES
    Identity,  # 从当前 import 模块导入符号 Identity
    InterventionKind,  # 从当前 import 模块导入符号 InterventionKind
    JobType,  # 从当前 import 模块导入符号 JobType
    RunBudget,  # 从当前 import 模块导入符号 RunBudget
    RunBudgetSnapshot,  # 从当前 import 模块导入符号 RunBudgetSnapshot
    RunStatus,  # 从当前 import 模块导入符号 RunStatus
    event_type_from_chunk,  # 从当前 import 模块导入符号 event_type_from_chunk
)  # 结束多符号导入列表
from app.infrastructure.llm import ChatModelFactory  # 从 app.infrastructure.llm 导入 ChatModelFactory，供本模块后续代码使用
from app.observability.telemetry import Telemetry  # 从 app.observability.telemetry 导入 Telemetry，供本模块后续代码使用
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository  # 从 app.repositories.mysql.dw.dw_mysql_repository 导入 DWMySQLRepository，供本模块后续代码使用
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository  # 从 app.repositories.mysql.meta.meta_mysql_repository 导入 MetaMySQLRepository，供本模块后续代码使用
from app.repositories.scoped import ScopedRepository  # 从 app.repositories.scoped 导入 ScopedRepository，供本模块后续代码使用
from app.tools.sql_execution import MySQLReadTool  # 从 app.tools.sql_execution 导入 MySQLReadTool，供本模块后续代码使用
from app.tools.sql_guard import SQLGuard  # 从 app.tools.sql_guard 导入 SQLGuard，供本模块后续代码使用


class LeaseLostError(DependencyUnavailableError):  # 定义类 LeaseLostError，组织相关状态与行为
    def __init__(self) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__("worker lease was lost")  # 调用 super 执行当前步骤：super().__init__("worker lease was lost")


class HarnessWorker:  # 定义类 HarnessWorker，组织相关状态与行为
    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        *,  # 为函数 __init__ 声明参数 * 及其类型或默认值
        settings: Settings,  # 为函数 __init__ 声明参数 settings 及其类型或默认值
        store: HarnessStore,  # 为函数 __init__ 声明参数 store 及其类型或默认值
        redis: RedisRuntime,  # 为函数 __init__ 声明参数 redis 及其类型或默认值
        events: EventPublisher,  # 为函数 __init__ 声明参数 events 及其类型或默认值
        registry: AgentRegistry,  # 为函数 __init__ 声明参数 registry 及其类型或默认值
        telemetry: Telemetry,  # 为函数 __init__ 声明参数 telemetry 及其类型或默认值
        graph: Any,  # 为函数 __init__ 声明参数 graph 及其类型或默认值
        llm_factory: ChatModelFactory,  # 为函数 __init__ 声明参数 llm_factory 及其类型或默认值
        sql_read_tool: MySQLReadTool,  # 为函数 __init__ 声明参数 sql_read_tool 及其类型或默认值
        meta_session_factory: Any,  # 为函数 __init__ 声明参数 meta_session_factory 及其类型或默认值
        dw_session_factory: Any,  # 为函数 __init__ 声明参数 dw_session_factory 及其类型或默认值
        column_qdrant_repository: Any,  # 为函数 __init__ 声明参数 column_qdrant_repository 及其类型或默认值
        metric_qdrant_repository: Any,  # 为函数 __init__ 声明参数 metric_qdrant_repository 及其类型或默认值
        value_es_repository: Any,  # 为函数 __init__ 声明参数 value_es_repository 及其类型或默认值
        embedding_client: Any,  # 为函数 __init__ 声明参数 embedding_client 及其类型或默认值
        tool_semaphore: asyncio.Semaphore,  # 为函数 __init__ 声明参数 tool_semaphore 及其类型或默认值
        checkpointer: Any,  # 为函数 __init__ 声明参数 checkpointer 及其类型或默认值
    ) -> None:  # 结束 __init__ 的参数列表并声明返回类型
        self.settings = settings  # 将 settings 保存到实例属性 self.settings
        self.store = store  # 将 store 保存到实例属性 self.store
        self.redis = redis  # 将 redis 保存到实例属性 self.redis
        self.events = events  # 将 events 保存到实例属性 self.events
        self.registry = registry  # 将 registry 保存到实例属性 self.registry
        self.router = AgentRouter(  # 调用 AgentRouter 构造结果并保存到 self.router
            registry,  # 继续向上一处调用或声明传入 registry
            min_confidence=settings.router_min_confidence,  # 为 AgentRouter 设置关键字参数 min_confidence，传入当前行给出的值
            min_margin=settings.router_min_margin,  # 为 AgentRouter 设置关键字参数 min_margin，传入当前行给出的值
        )  # 结束 AgentRouter 调用参数，得到完整表达式结果
        self.telemetry = telemetry  # 将 telemetry 保存到实例属性 self.telemetry
        self.graph = graph  # 将 graph 保存到实例属性 self.graph
        self.llm_factory = llm_factory  # 将 llm_factory 保存到实例属性 self.llm_factory
        self.sql_read_tool = sql_read_tool  # 将 sql_read_tool 保存到实例属性 self.sql_read_tool
        self.meta_session_factory = meta_session_factory  # 将 meta_session_factory 保存到实例属性 self.meta_session_factory
        self.dw_session_factory = dw_session_factory  # 将 dw_session_factory 保存到实例属性 self.dw_session_factory
        self.column_qdrant_repository = column_qdrant_repository  # 将 column_qdrant_repository 保存到实例属性 self.column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository  # 将 metric_qdrant_repository 保存到实例属性 self.metric_qdrant_repository
        self.value_es_repository = value_es_repository  # 将 value_es_repository 保存到实例属性 self.value_es_repository
        self.embedding_client = embedding_client  # 将 embedding_client 保存到实例属性 self.embedding_client
        self.tool_semaphore = tool_semaphore  # 将 tool_semaphore 保存到实例属性 self.tool_semaphore
        self.checkpointer = checkpointer  # 将 checkpointer 保存到实例属性 self.checkpointer
        self.worker_id = (  # 构造并保存实例属性 self.worker_id 的多行计算结果
            f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"  # 调用 目标函数 执行当前步骤：f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
        )  # 结束函数 __init__ 的调用或声明结构
        self._stop = asyncio.Event()  # 将 asyncio.Event() 保存到实例属性 self._stop
        self._tasks: list[asyncio.Task] = []  # 将 [] 保存到实例属性 self._tasks

    async def start(self) -> None:  # 定义异步函数 start，封装可被事件循环调度的协程逻辑
        if self._tasks:  # 判断分支条件：if self._tasks:
            return  # 提前返回空结果，结束当前函数调用
        for index in range(self.settings.worker_concurrency):  # 按迭代条件执行循环：for index in range(self.settings.worker_concurrency):
            self._tasks.append(  # 调用 append 执行当前步骤：self._tasks.append(
                asyncio.create_task(  # 调用 create_task 执行当前步骤：asyncio.create_task(
                    self._consumer_loop(index),  # 继续向上一处调用或声明传入 self._consumer_loop(index)
                    name=f"harness-worker-{index}",  # 为 asyncio.create_task 设置关键字参数 name，传入当前行给出的值
                )  # 结束 asyncio.create_task 调用参数，得到完整表达式结果
            )  # 结束 self._tasks.append 调用参数，得到完整表达式结果
        self._tasks.append(  # 调用 append 执行当前步骤：self._tasks.append(
            asyncio.create_task(self._maintenance_loop(), name="harness-maintenance")  # 调用 create_task 执行当前步骤：asyncio.create_task(self._maintenance_loop(), name="harness-maintenance…
        )  # 结束 self._tasks.append 调用参数，得到完整表达式结果
        logger.info(  # 调用 info 执行当前步骤：logger.info(
            "Harness worker started: id={}, concurrency={}",  # 继续向上一处调用或声明传入 "Harness worker started: id={}, concurrency={}"
            self.worker_id,  # 继续向上一处调用或声明传入 self.worker_id
            self.settings.worker_concurrency,  # 继续向上一处调用或声明传入 self.settings.worker_concurrency
        )  # 结束 logger.info 调用参数，得到完整表达式结果

    async def stop(self) -> None:  # 定义异步函数 stop，封装可被事件循环调度的协程逻辑
        self._stop.set()  # 调用 set 执行当前步骤：self._stop.set()
        if not self._tasks:  # 判断分支条件：if not self._tasks:
            return  # 提前返回空结果，结束当前函数调用
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            await asyncio.wait_for(  # 等待异步操作完成并取得结果：asyncio.wait_for(
                asyncio.gather(*self._tasks, return_exceptions=True),  # 继续向上一处调用或声明传入 asyncio.gather(*self._tasks, return_exceptions=True)
                timeout=30,  # 为 asyncio.wait_for 设置关键字参数 timeout，传入当前行给出的值
            )  # 结束 asyncio.wait_for 调用参数，得到完整表达式结果
        except TimeoutError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except TimeoutError:
            for task in self._tasks:  # 按迭代条件执行循环：for task in self._tasks:
                task.cancel()  # 调用 cancel 执行当前步骤：task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)  # 等待异步操作完成并取得结果：asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()  # 调用 clear 执行当前步骤：self._tasks.clear()

    async def _consumer_loop(self, index: int) -> None:  # 定义异步函数 _consumer_loop，封装可被事件循环调度的协程逻辑
        while not self._stop.is_set():  # 在函数 _consumer_loop 中执行表达式 while not self._stop.is_set():，推进当前业务流程
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                job = await self.store.claim_next_job(  # 等待 claim_next_job 完成，并将其结果保存到 job
                    worker_id=self.worker_id,  # 为 self.store.claim_next_job 设置关键字参数 worker_id，传入当前行给出的值
                    lease_seconds=self.settings.worker_lease_seconds,  # 为 self.store.claim_next_job 设置关键字参数 lease_seconds，传入当前行给出的值
                    max_attempts=self.settings.job_max_attempts,  # 为 self.store.claim_next_job 设置关键字参数 max_attempts，传入当前行给出的值
                )  # 结束 self.store.claim_next_job 调用参数，得到完整表达式结果
                if job is None:  # 判断分支条件：if job is None:
                    await self.redis.wait_for_wake(  # 等待异步操作完成并取得结果：self.redis.wait_for_wake(
                        self.settings.worker_poll_seconds  # 在函数 _consumer_loop 中执行表达式 self.settings.worker_poll_seconds，推进当前业务流程
                    )  # 结束 self.redis.wait_for_wake 调用参数，得到完整表达式结果
                    await asyncio.sleep(self.settings.worker_poll_seconds)  # 等待异步操作完成并取得结果：asyncio.sleep(self.settings.worker_poll_seconds)
                    continue  # 跳过本轮剩余逻辑并进入下一轮迭代
                self.telemetry.metrics.queue_claims.add(1)  # 调用 add 执行当前步骤：self.telemetry.metrics.queue_claims.add(1)
                await self._process_job(job)  # 等待异步操作完成并取得结果：self._process_job(job)
            except TimeoutError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except TimeoutError:
                continue  # 跳过本轮剩余逻辑并进入下一轮迭代
            except asyncio.CancelledError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except asyncio.CancelledError:
                raise  # 重新抛出当前异常，保留原始失败上下文
            except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
                logger.error(  # 调用 error 执行当前步骤：logger.error(
                    "Worker loop failure index={}: {}",  # 继续向上一处调用或声明传入 "Worker loop failure index={}: {}"
                    index,  # 继续向上一处调用或声明传入 index
                    type(exc).__name__,  # 继续向上一处调用或声明传入 type(exc).__name__
                )  # 结束 logger.error 调用参数，得到完整表达式结果
                await asyncio.sleep(1)  # 等待异步操作完成并取得结果：asyncio.sleep(1)

    async def _process_job(self, job: JobRecord) -> None:  # 定义异步函数 _process_job，封装可被事件循环调度的协程逻辑
        run_task = asyncio.create_task(self._run_job(job))  # 计算 asyncio.create_task(self._run_job(job)) 并保存到变量 run_task
        heartbeat = asyncio.create_task(self._heartbeat(job))  # 计算 asyncio.create_task(self._heartbeat(job)) 并保存到变量 heartbeat
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            done, _ = await asyncio.wait(  # 等待 wait 完成，并将其结果保存到 done, _
                {run_task, heartbeat},  # 向多行序列加入元素 {run_task, heartbeat}
                return_when=asyncio.FIRST_COMPLETED,  # 为 asyncio.wait 设置关键字参数 return_when，传入当前行给出的值
            )  # 结束 asyncio.wait 调用参数，得到完整表达式结果
            if heartbeat in done:  # 判断分支条件：if heartbeat in done:
                heartbeat_exception = heartbeat.exception()  # 计算 heartbeat.exception() 并保存到变量 heartbeat_exception
                if heartbeat_exception is not None:  # 判断分支条件：if heartbeat_exception is not None:
                    run_task.cancel()  # 调用 cancel 执行当前步骤：run_task.cancel()
                    await asyncio.gather(run_task, return_exceptions=True)  # 等待异步操作完成并取得结果：asyncio.gather(run_task, return_exceptions=True)
                    raise LeaseLostError() from heartbeat_exception  # 抛出明确异常，阻止错误状态被静默接受：LeaseLostError() from heartbeat_exception
            await run_task  # 等待异步操作完成并取得结果：run_task
        except asyncio.CancelledError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except asyncio.CancelledError:
            await self.store.release_job(job.id, self.worker_id)  # 等待异步操作完成并取得结果：self.store.release_job(job.id, self.worker_id)
            raise  # 重新抛出当前异常，保留原始失败上下文
        except LeaseLostError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except LeaseLostError as exc:
            logger.warning("Job lease lost: {}", job.id)  # 调用 warning 执行当前步骤：logger.warning("Job lease lost: {}", job.id)
            await self.store.release_job(job.id, self.worker_id)  # 等待异步操作完成并取得结果：self.store.release_job(job.id, self.worker_id)
            del exc  # 删除或显式忽略名称 exc，避免未使用变量干扰
        except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
            await self._handle_job_failure(job, exc)  # 等待异步操作完成并取得结果：self._handle_job_failure(job, exc)
        finally:  # 进入无论成功失败都必须执行的资源清理分支
            heartbeat.cancel()  # 调用 cancel 执行当前步骤：heartbeat.cancel()
            if not run_task.done():  # 判断分支条件：if not run_task.done():
                run_task.cancel()  # 调用 cancel 执行当前步骤：run_task.cancel()
            await asyncio.gather(run_task, heartbeat, return_exceptions=True)  # 等待异步操作完成并取得结果：asyncio.gather(run_task, heartbeat, return_exceptions=True)

    async def _run_job(self, job: JobRecord) -> None:  # 定义异步函数 _run_job，封装可被事件循环调度的协程逻辑
        run_id_ctx_var.set(str(job.run_id))  # 调用 set 执行当前步骤：run_id_ctx_var.set(str(job.run_id))
        run = await self.store.get_run_internal(job.run_id)  # 等待 get_run_internal 完成，并将其结果保存到 run
        if run.status in TERMINAL_RUN_STATUSES:  # 判断分支条件：if run.status in TERMINAL_RUN_STATUSES:
            await self.store.complete_job(job.id, self.worker_id)  # 等待异步操作完成并取得结果：self.store.complete_job(job.id, self.worker_id)
            return  # 提前返回空结果，结束当前函数调用
        if not self.settings.agent_execution_enabled:  # 判断分支条件：if not self.settings.agent_execution_enabled:
            await self.store.finish_run(  # 等待异步操作完成并取得结果：self.store.finish_run(
                run.id,  # 继续向上一处调用或声明传入 run.id
                RunStatus.FAILED,  # 继续向上一处调用或声明传入 RunStatus.FAILED
                error_code="AGENT_EXECUTION_DISABLED",  # 为 self.store.finish_run 设置关键字参数 error_code，传入当前行给出的值
                error_message="agent execution is disabled",  # 为 self.store.finish_run 设置关键字参数 error_message，传入当前行给出的值
            )  # 结束 self.store.finish_run 调用参数，得到完整表达式结果
            await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
                run.id,  # 继续向上一处调用或声明传入 run.id
                "run.failed",  # 继续向上一处调用或声明传入 "run.failed"
                {  # 在函数 _run_job 中执行表达式 {，推进当前业务流程
                    "status": RunStatus.FAILED.value,  # 为多行字典定义键 "status" 及其对应值
                    "error_code": "AGENT_EXECUTION_DISABLED",  # 为多行字典定义键 "error_code" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
                trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
            )  # 结束 self.events.publish 调用参数，得到完整表达式结果
            await self.store.complete_job(job.id, self.worker_id)  # 等待异步操作完成并取得结果：self.store.complete_job(job.id, self.worker_id)
            return  # 提前返回空结果，结束当前函数调用
        if run.status == RunStatus.WAITING_HUMAN and job.job_type == JobType.START:  # 判断分支条件：if run.status == RunStatus.WAITING_HUMAN and job.job_type == JobType.ST…
            await self.store.complete_job(job.id, self.worker_id)  # 等待异步操作完成并取得结果：self.store.complete_job(job.id, self.worker_id)
            return  # 提前返回空结果，结束当前函数调用
        if run.agent_version and run.selected_agent_id:  # 判断分支条件：if run.agent_version and run.selected_agent_id:
            definition = self.registry.try_get(run.selected_agent_id)  # 计算 self.registry.try_get(run.selected_agent_id) 并保存到变量 definition
            if definition is None or definition.version != run.agent_version:  # 判断分支条件：if definition is None or definition.version != run.agent_version:
                await self.store.finish_run(  # 等待异步操作完成并取得结果：self.store.finish_run(
                    run.id,  # 继续向上一处调用或声明传入 run.id
                    RunStatus.FAILED,  # 继续向上一处调用或声明传入 RunStatus.FAILED
                    error_code="CHECKPOINT_AGENT_VERSION_INCOMPATIBLE",  # 为 self.store.finish_run 设置关键字参数 error_code，传入当前行给出的值
                    error_message=(  # 为 self.store.finish_run 设置关键字参数 error_message，传入当前行给出的值
                        "the pinned agent version is no longer available"  # 在函数 _run_job 中执行表达式 "the pinned agent version is no longer available"，推进当前业务流程
                    ),  # 结束函数 _run_job 的调用或声明结构
                )  # 结束 self.store.finish_run 调用参数，得到完整表达式结果
                await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
                    run.id,  # 继续向上一处调用或声明传入 run.id
                    "run.failed",  # 继续向上一处调用或声明传入 "run.failed"
                    {  # 在函数 _run_job 中执行表达式 {，推进当前业务流程
                        "status": RunStatus.FAILED.value,  # 为多行字典定义键 "status" 及其对应值
                        "error_code": "CHECKPOINT_AGENT_VERSION_INCOMPATIBLE",  # 为多行字典定义键 "error_code" 及其对应值
                    },  # 结束上一处多行结构，保持表达式边界清晰
                    trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
                )  # 结束 self.events.publish 调用参数，得到完整表达式结果
                await self.store.complete_job(job.id, self.worker_id)  # 等待异步操作完成并取得结果：self.store.complete_job(job.id, self.worker_id)
                return  # 提前返回空结果，结束当前函数调用

        identity = Identity(  # 调用 Identity 构造结果并保存到 identity
            user_id=run.user_id,  # 为 Identity 设置关键字参数 user_id，传入当前行给出的值
            tenant_id=run.tenant_id,  # 为 Identity 设置关键字参数 tenant_id，传入当前行给出的值
            roles=frozenset({"agent:user"}),  # 为 frozenset 设置关键字参数 roles，传入当前行给出的值
        )  # 结束 Identity 调用参数，得到完整表达式结果
        conversation = await self._load_conversation(run)  # 等待 _load_conversation 完成，并将其结果保存到 conversation
        budget_snapshot = RunBudgetSnapshot.model_validate(run.budget or {})  # 计算 RunBudgetSnapshot.model_validate(run.budget or {}) 并保存到变量 budget_snapshot
        budget = RunBudget.from_snapshot(  # 调用 from_snapshot 构造结果并保存到 budget
            budget_snapshot,  # 继续向上一处调用或声明传入 budget_snapshot
            max_llm_calls=self.settings.run_max_llm_calls,  # 为 RunBudget.from_snapshot 设置关键字参数 max_llm_calls，传入当前行给出的值
            max_tokens=self.settings.run_max_tokens,  # 为 RunBudget.from_snapshot 设置关键字参数 max_tokens，传入当前行给出的值
            max_active_seconds=self.settings.run_max_wall_seconds,  # 为 RunBudget.from_snapshot 设置关键字参数 max_active_seconds，传入当前行给出的值
        )  # 结束 RunBudget.from_snapshot 调用参数，得到完整表达式结果
        budget.start_clock()  # 调用 start_clock 执行当前步骤：budget.start_clock()
        llm = self.llm_factory.bind(  # 调用 bind 构造结果并保存到 llm
            budget=budget,  # 为 self.llm_factory.bind 设置关键字参数 budget，传入当前行给出的值
            telemetry=self.telemetry,  # 为 self.llm_factory.bind 设置关键字参数 telemetry，传入当前行给出的值
            trace_id=run.trace_id,  # 为 self.llm_factory.bind 设置关键字参数 trace_id，传入当前行给出的值
            agent_id=run.selected_agent_id or "router",  # 为 self.llm_factory.bind 设置关键字参数 agent_id，传入当前行给出的值
            run_id=str(run.id),  # 为 str 设置关键字参数 run_id，传入当前行给出的值
        )  # 结束 self.llm_factory.bind 调用参数，得到完整表达式结果
        await self.store.mark_run_running(run.id)  # 等待异步操作完成并取得结果：self.store.mark_run_running(run.id)
        await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
            run.id,  # 继续向上一处调用或声明传入 run.id
            "run.started",  # 继续向上一处调用或声明传入 "run.started"
            {"status": RunStatus.RUNNING.value, "attempt": job.attempts},  # 向多行字典加入配置项 {"status": RunStatus.RUNNING.value, "attempt": job.attempts}
            trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
        )  # 结束 self.events.publish 调用参数，得到完整表达式结果
        await self.redis.invalidate_session(run.tenant_id, run.session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(run.tenant_id, run.session_id)

        context: HarnessContext = {  # 计算 { 并保存到变量 context
            "settings": self.settings,  # 为多行字典定义键 "settings" 及其对应值
            "identity": identity,  # 为多行字典定义键 "identity" 及其对应值
            "registry": self.registry,  # 为多行字典定义键 "registry" 及其对应值
            "router": self.router,  # 为多行字典定义键 "router" 及其对应值
            "store": self.store,  # 为多行字典定义键 "store" 及其对应值
            "telemetry": self.telemetry,  # 为多行字典定义键 "telemetry" 及其对应值
            "budget": budget,  # 为多行字典定义键 "budget" 及其对应值
            "llm": llm,  # 为多行字典定义键 "llm" 及其对应值
            "run_id": str(run.id),  # 为多行字典定义键 "run_id" 及其对应值
            "session_id": str(run.session_id),  # 为多行字典定义键 "session_id" 及其对应值
            "trace_id": run.trace_id,  # 为多行字典定义键 "trace_id" 及其对应值
            "column_qdrant_repository": self.column_qdrant_repository,  # 为多行字典定义键 "column_qdrant_repository" 及其对应值
            "embedding_client": self.embedding_client,  # 为多行字典定义键 "embedding_client" 及其对应值
            "metric_qdrant_repository": self.metric_qdrant_repository,  # 为多行字典定义键 "metric_qdrant_repository" 及其对应值
            "value_es_repository": self.value_es_repository,  # 为多行字典定义键 "value_es_repository" 及其对应值
            "meta_mysql_repository": ScopedRepository(  # 为多行字典定义键 "meta_mysql_repository" 及其对应值
                self.meta_session_factory, MetaMySQLRepository  # 在函数 _run_job 中执行表达式 self.meta_session_factory, MetaMySQLRepository，推进当前业务流程
            ),  # 结束 ScopedRepository 调用参数，得到完整表达式结果
            "dw_mysql_repository": ScopedRepository(  # 为多行字典定义键 "dw_mysql_repository" 及其对应值
                self.dw_session_factory, DWMySQLRepository  # 在函数 _run_job 中执行表达式 self.dw_session_factory, DWMySQLRepository，推进当前业务流程
            ),  # 结束 ScopedRepository 调用参数，得到完整表达式结果
            "sql_guard": self._build_sql_guard(),  # 为多行字典定义键 "sql_guard" 及其对应值
            "sql_read_tool": self.sql_read_tool,  # 为多行字典定义键 "sql_read_tool" 及其对应值
            "tool_semaphore": self.tool_semaphore,  # 为多行字典定义键 "tool_semaphore" 及其对应值
            "sensitive_columns": self.settings.sensitive_columns,  # 为多行字典定义键 "sensitive_columns" 及其对应值
            "business_timezone": "Asia/Shanghai",  # 为多行字典定义键 "business_timezone" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
        with self.telemetry.activate_traceparent(  # 进入受管理的上下文 with self.telemetry.activate_traceparent(，确保资源正确获取与释放
            run.traceparent or job.traceparent  # 在函数 _run_job 中执行表达式 run.traceparent or job.traceparent，推进当前业务流程
        ):  # 结束 _run_job 的参数列表并声明返回类型
            with self.telemetry.tracer.start_as_current_span(  # 进入受管理的上下文 with self.telemetry.tracer.start_as_current_span(，确保资源正确获取与释放
                "harness.run",  # 继续向上一处调用或声明传入 "harness.run"
                attributes={  # 为 self.telemetry.tracer.start_as_current_span 设置关键字参数 attributes，传入当前行给出的值
                    "run.id": str(run.id),  # 为多行字典定义键 "run.id" 及其对应值
                    "session.id": str(run.session_id),  # 为多行字典定义键 "session.id" 及其对应值
                    "agent.requested": run.requested_agent_id or "auto",  # 为多行字典定义键 "agent.requested" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
            ) as span:  # 在函数 _run_job 中执行表达式 ) as span:，推进当前业务流程
                try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                    graph_input = await self._build_graph_input(  # 等待 _build_graph_input 完成，并将其结果保存到 graph_input
                        run, job, conversation  # 在函数 _run_job 中执行表达式 run, job, conversation，推进当前业务流程
                    )  # 结束 self._build_graph_input 调用参数，得到完整表达式结果
                    config = {  # 计算 { 并保存到变量 config
                        "configurable": {"thread_id": str(run.id)},  # 为多行字典定义键 "configurable" 及其对应值
                        "recursion_limit": 32,  # 为多行字典定义键 "recursion_limit" 及其对应值
                    }  # 结束上一处多行结构，保持表达式边界清晰
                    async for chunk in self.graph.astream(  # 按迭代条件执行循环：async for chunk in self.graph.astream(
                        input=graph_input,  # 为 self.graph.astream 设置关键字参数 input，传入当前行给出的值
                        config=config,  # 为 self.graph.astream 设置关键字参数 config，传入当前行给出的值
                        context=context,  # 为 self.graph.astream 设置关键字参数 context，传入当前行给出的值
                        stream_mode="custom",  # 为 self.graph.astream 设置关键字参数 stream_mode，传入当前行给出的值
                    ):  # 结束 _run_job 的参数列表并声明返回类型
                        await self._persist_chunk(run, chunk)  # 等待异步操作完成并取得结果：self._persist_chunk(run, chunk)
                        if self._stop.is_set():  # 判断分支条件：if self._stop.is_set():
                            raise asyncio.CancelledError  # 抛出明确异常，阻止错误状态被静默接受：asyncio.CancelledError
                    snapshot = await self.graph.aget_state(config)  # 等待 aget_state 完成，并将其结果保存到 snapshot
                    interrupts = tuple(snapshot.interrupts)  # 计算 tuple(snapshot.interrupts) 并保存到变量 interrupts
                    if interrupts:  # 判断分支条件：if interrupts:
                        budget.pause_clock()  # 调用 pause_clock 执行当前步骤：budget.pause_clock()
                        await self.store.set_run_budget(  # 等待异步操作完成并取得结果：self.store.set_run_budget(
                            run.id, budget.snapshot.model_dump()  # 调用 目标函数 执行当前步骤：run.id, budget.snapshot.model_dump()
                        )  # 结束 self.store.set_run_budget 调用参数，得到完整表达式结果
                        await self._store_intervention(  # 等待异步操作完成并取得结果：self._store_intervention(
                            run, interrupts[0].value  # 在函数 _run_job 中执行表达式 run, interrupts[0].value，推进当前业务流程
                        )  # 结束 self._store_intervention 调用参数，得到完整表达式结果
                        await self.store.complete_job(job.id, self.worker_id)  # 等待异步操作完成并取得结果：self.store.complete_job(job.id, self.worker_id)
                        self.telemetry.metrics.runs_finished.add(  # 调用 add 执行当前步骤：self.telemetry.metrics.runs_finished.add(
                            1,  # 继续向上一处调用或声明传入 1
                            {  # 在函数 _run_job 中执行表达式 {，推进当前业务流程
                                "status": "waiting_human",  # 为多行字典定义键 "status" 及其对应值
                                "agent_id": run.selected_agent_id or "router",  # 为多行字典定义键 "agent_id" 及其对应值
                            },  # 结束上一处多行结构，保持表达式边界清晰
                        )  # 结束 self.telemetry.metrics.runs_finished.add 调用参数，得到完整表达式结果
                        return  # 提前返回空结果，结束当前函数调用
                    current_run = await self.store.get_run_internal(run.id)  # 等待 get_run_internal 完成，并将其结果保存到 current_run
                    if current_run.status in TERMINAL_RUN_STATUSES:  # 判断分支条件：if current_run.status in TERMINAL_RUN_STATUSES:
                        await self.store.complete_job(  # 等待异步操作完成并取得结果：self.store.complete_job(
                            job.id, self.worker_id  # 在函数 _run_job 中执行表达式 job.id, self.worker_id，推进当前业务流程
                        )  # 结束 self.store.complete_job 调用参数，得到完整表达式结果
                        return  # 提前返回空结果，结束当前函数调用
                    await self._finish_from_state(  # 等待异步操作完成并取得结果：self._finish_from_state(
                        current_run, snapshot.values, budget  # 在函数 _run_job 中执行表达式 current_run, snapshot.values, budget，推进当前业务流程
                    )  # 结束 self._finish_from_state 调用参数，得到完整表达式结果
                    await self.store.complete_job(job.id, self.worker_id)  # 等待异步操作完成并取得结果：self.store.complete_job(job.id, self.worker_id)
                except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
                    self.telemetry.record_exception(span, exc)  # 调用 record_exception 执行当前步骤：self.telemetry.record_exception(span, exc)
                    raise  # 重新抛出当前异常，保留原始失败上下文
                finally:  # 进入无论成功失败都必须执行的资源清理分支
                    budget.pause_clock()  # 调用 pause_clock 执行当前步骤：budget.pause_clock()
                    await self.store.set_run_budget(  # 等待异步操作完成并取得结果：self.store.set_run_budget(
                        run.id, budget.snapshot.model_dump()  # 调用 目标函数 执行当前步骤：run.id, budget.snapshot.model_dump()
                    )  # 结束 self.store.set_run_budget 调用参数，得到完整表达式结果

    async def _build_graph_input(  # 定义异步函数 _build_graph_input，封装可被事件循环调度的协程逻辑
        self,  # 为函数 _build_graph_input 声明参数 self 及其类型或默认值
        run: RunRecord,  # 为函数 _build_graph_input 声明参数 run 及其类型或默认值
        job: JobRecord,  # 为函数 _build_graph_input 声明参数 job 及其类型或默认值
        conversation: list[dict[str, str]],  # 为函数 _build_graph_input 声明参数 conversation 及其类型或默认值
    ) -> Any:  # 结束 _build_graph_input 的参数列表并声明返回类型
        config = {"configurable": {"thread_id": str(run.id)}}  # 计算 {"configurable": {"thread_id": str(run.id)}} 并保存到变量 config
        snapshot = await self.graph.aget_state(config)  # 等待 aget_state 完成，并将其结果保存到 snapshot
        if job.job_type == JobType.RESUME:  # 判断分支条件：if job.job_type == JobType.RESUME:
            if snapshot.values and not snapshot.interrupts:  # 判断分支条件：if snapshot.values and not snapshot.interrupts:
                return None  # 返回 None 给调用方
            intervention_id = job.payload.get("intervention_id")  # 计算 job.payload.get("intervention_id") 并保存到变量 intervention_id
            if not intervention_id:  # 判断分支条件：if not intervention_id:
                raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                    "INVALID_RESUME_JOB", "resume job has no intervention"  # 在函数 _build_graph_input 中执行表达式 "INVALID_RESUME_JOB", "resume job has no intervention"，推进当前业务流程
                )  # 结束 ConflictError 调用参数，得到完整表达式结果
            intervention = await self.store.get_intervention(  # 等待 get_intervention 完成，并将其结果保存到 intervention
                UUID(str(intervention_id))  # 调用 UUID 执行当前步骤：UUID(str(intervention_id))
            )  # 结束 self.store.get_intervention 调用参数，得到完整表达式结果
            decision = dict(intervention.decision_data or {})  # 计算 dict(intervention.decision_data or {}) 并保存到变量 decision
            if intervention.kind == InterventionKind.AGENT_SELECTION:  # 判断分支条件：if intervention.kind == InterventionKind.AGENT_SELECTION:
                decision = {"agent_id": decision.get("agent_id")}  # 计算 {"agent_id": decision.get("agent_id")} 并保存到变量 decision
            return Command(resume=decision)  # 返回 Command(resume=decision) 给调用方
        if snapshot.values:  # 判断分支条件：if snapshot.values:
            return None  # 返回 None 给调用方
        return {  # 返回 { 给调用方
            "run_id": str(run.id),  # 为多行字典定义键 "run_id" 及其对应值
            "session_id": str(run.session_id),  # 为多行字典定义键 "session_id" 及其对应值
            "query": run.query,  # 为多行字典定义键 "query" 及其对应值
            "requested_agent_id": run.requested_agent_id,  # 为多行字典定义键 "requested_agent_id" 及其对应值
            "conversation": conversation,  # 为多行字典定义键 "conversation" 及其对应值
            "correction_count": 0,  # 为多行字典定义键 "correction_count" 及其对应值
            "max_corrections": self.settings.run_max_sql_corrections,  # 为多行字典定义键 "max_corrections" 及其对应值
            "approval_rounds": 0,  # 为多行字典定义键 "approval_rounds" 及其对应值
            "human_edited_sql": False,  # 为多行字典定义键 "human_edited_sql" 及其对应值
            "run_outcome_status": "running",  # 为多行字典定义键 "run_outcome_status" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰

    async def _persist_chunk(self, run: RunRecord, chunk: Any) -> None:  # 定义异步函数 _persist_chunk，封装可被事件循环调度的协程逻辑
        event_type = event_type_from_chunk(chunk)  # 计算 event_type_from_chunk(chunk) 并保存到变量 event_type
        if event_type in {  # 判断分支条件：if event_type in {
            "agent.result",  # 向多行序列加入元素 "agent.result"
            "agent.selection_required",  # 向多行序列加入元素 "agent.selection_required"
            "sql.approval_required",  # 向多行序列加入元素 "sql.approval_required"
        }:  # 在函数 _persist_chunk 中执行表达式 }:，推进当前业务流程
            return  # 提前返回空结果，结束当前函数调用
        if isinstance(chunk, dict) and "type" in chunk:  # 判断分支条件：if isinstance(chunk, dict) and "type" in chunk:
            payload = {key: value for key, value in chunk.items() if key != "type"}  # 计算 {key: value for key, value in chunk.items() if key != "type"} 并保存到变量 payload
        else:  # 进入前面条件均不成立时的兜底分支
            payload = {"value": chunk}  # 计算 {"value": chunk} 并保存到变量 payload
        await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
            run.id,  # 继续向上一处调用或声明传入 run.id
            event_type,  # 继续向上一处调用或声明传入 event_type
            _json_safe(payload),  # 继续向上一处调用或声明传入 _json_safe(payload)
            trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
        )  # 结束 self.events.publish 调用参数，得到完整表达式结果
        if event_type == "agent.selected":  # 判断分支条件：if event_type == "agent.selected":
            await self.redis.invalidate_session(run.tenant_id, run.session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(run.tenant_id, run.session_id)

    async def _store_intervention(self, run: RunRecord, payload: Any) -> None:  # 定义异步函数 _store_intervention，封装可被事件循环调度的协程逻辑
        if not isinstance(payload, dict):  # 判断分支条件：if not isinstance(payload, dict):
            raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                "INVALID_INTERRUPT", "LangGraph interrupt payload is invalid"  # 在函数 _store_intervention 中执行表达式 "INVALID_INTERRUPT", "LangGraph interrupt payload is invalid"，推进当前业务流程
            )  # 结束 ConflictError 调用参数，得到完整表达式结果
        kind_raw = payload.get("kind")  # 计算 payload.get("kind") 并保存到变量 kind_raw
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            kind = InterventionKind(str(kind_raw))  # 计算 InterventionKind(str(kind_raw)) 并保存到变量 kind
        except ValueError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except ValueError as exc:
            raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                "UNKNOWN_INTERVENTION", "unsupported interrupt kind"  # 在函数 _store_intervention 中执行表达式 "UNKNOWN_INTERVENTION", "unsupported interrupt kind"，推进当前业务流程
            ) from exc  # 在函数 _store_intervention 中执行表达式 ) from exc，推进当前业务流程
        payload = _json_safe(payload)  # 计算 _json_safe(payload) 并保存到变量 payload
        intervention = await self.store.create_intervention(  # 等待 create_intervention 完成，并将其结果保存到 intervention
            run.id,  # 继续向上一处调用或声明传入 run.id
            kind=kind,  # 为 self.store.create_intervention 设置关键字参数 kind，传入当前行给出的值
            payload=payload,  # 为 self.store.create_intervention 设置关键字参数 payload，传入当前行给出的值
            ttl_seconds=self.settings.human_wait_ttl_seconds,  # 为 self.store.create_intervention 设置关键字参数 ttl_seconds，传入当前行给出的值
        )  # 结束 self.store.create_intervention 调用参数，得到完整表达式结果
        event_type = (  # 调用 目标函数 构造结果并保存到 event_type
            "agent.selection_required"  # 在函数 _store_intervention 中执行表达式 "agent.selection_required"，推进当前业务流程
            if kind == InterventionKind.AGENT_SELECTION  # 判断分支条件：if kind == InterventionKind.AGENT_SELECTION
            else "sql.approval_required"  # 在函数 _store_intervention 中执行表达式 else "sql.approval_required"，推进当前业务流程
        )  # 结束函数 _store_intervention 的调用或声明结构
        await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
            run.id,  # 继续向上一处调用或声明传入 run.id
            event_type,  # 继续向上一处调用或声明传入 event_type
            {  # 在函数 _store_intervention 中执行表达式 {，推进当前业务流程
                "intervention_id": str(intervention.id),  # 为多行字典定义键 "intervention_id" 及其对应值
                "version": intervention.version,  # 为多行字典定义键 "version" 及其对应值
                "expires_at": intervention.expires_at.isoformat(),  # 为多行字典定义键 "expires_at" 及其对应值
                "payload": intervention.payload,  # 为多行字典定义键 "payload" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
            trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
        )  # 结束 self.events.publish 调用参数，得到完整表达式结果
        await self.redis.invalidate_session(run.tenant_id, run.session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(run.tenant_id, run.session_id)

    async def _finish_from_state(  # 定义异步函数 _finish_from_state，封装可被事件循环调度的协程逻辑
        self, run: RunRecord, state: dict[str, Any], budget: RunBudget  # 为函数 _finish_from_state 声明参数 self, run 及其类型或默认值
    ) -> None:  # 结束 _finish_from_state 的参数列表并声明返回类型
        status = str(state.get("run_outcome_status") or "failed")  # 计算 str(state.get("run_outcome_status") or "failed") 并保存到变量 status
        output = _json_safe(state.get("agent_output") or {})  # 计算 _json_safe(state.get("agent_output") or {}) 并保存到变量 output
        if status == "completed":  # 判断分支条件：if status == "completed":
            finished = await self.store.complete_run(  # 等待 complete_run 完成，并将其结果保存到 finished
                run.id,  # 继续向上一处调用或声明传入 run.id
                output=output,  # 为 self.store.complete_run 设置关键字参数 output，传入当前行给出的值
                budget=budget.snapshot.model_dump(),  # 为 budget.snapshot.model_dump 设置关键字参数 budget，传入当前行给出的值
            )  # 结束 self.store.complete_run 调用参数，得到完整表达式结果
            event_type = "run.completed"  # 计算 "run.completed" 并保存到变量 event_type
        elif status == "rejected":  # 在前一条件不成立时继续判断：elif status == "rejected":
            finished = await self.store.finish_run(  # 等待 finish_run 完成，并将其结果保存到 finished
                run.id,  # 继续向上一处调用或声明传入 run.id
                RunStatus.REJECTED,  # 继续向上一处调用或声明传入 RunStatus.REJECTED
                error_code="APPROVAL_REJECTED",  # 为 self.store.finish_run 设置关键字参数 error_code，传入当前行给出的值
                error_message=output.get("reason"),  # 为 output.get 设置关键字参数 error_message，传入当前行给出的值
                budget=budget.snapshot.model_dump(),  # 为 budget.snapshot.model_dump 设置关键字参数 budget，传入当前行给出的值
            )  # 结束 self.store.finish_run 调用参数，得到完整表达式结果
            event_type = "run.rejected"  # 计算 "run.rejected" 并保存到变量 event_type
        else:  # 进入前面条件均不成立时的兜底分支
            finished = await self.store.finish_run(  # 等待 finish_run 完成，并将其结果保存到 finished
                run.id,  # 继续向上一处调用或声明传入 run.id
                RunStatus.FAILED,  # 继续向上一处调用或声明传入 RunStatus.FAILED
                error_code=str(output.get("error_code") or "AGENT_FAILED"),  # 为 str 设置关键字参数 error_code，传入当前行给出的值
                error_message=output.get("error"),  # 为 output.get 设置关键字参数 error_message，传入当前行给出的值
                budget=budget.snapshot.model_dump(),  # 为 budget.snapshot.model_dump 设置关键字参数 budget，传入当前行给出的值
            )  # 结束 self.store.finish_run 调用参数，得到完整表达式结果
            event_type = "run.failed"  # 计算 "run.failed" 并保存到变量 event_type
        await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
            run.id,  # 继续向上一处调用或声明传入 run.id
            event_type,  # 继续向上一处调用或声明传入 event_type
            {  # 在函数 _finish_from_state 中执行表达式 {，推进当前业务流程
                "status": finished.status.value,  # 为多行字典定义键 "status" 及其对应值
                "agent_id": output.get("agent_id"),  # 为多行字典定义键 "agent_id" 及其对应值
                "text": output.get("text"),  # 为多行字典定义键 "text" 及其对应值
                "row_count": output.get("row_count"),  # 为多行字典定义键 "row_count" 及其对应值
                "truncated": output.get("truncated"),  # 为多行字典定义键 "truncated" 及其对应值
                "error_code": finished.error_code,  # 为多行字典定义键 "error_code" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
            trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
        )  # 结束 self.events.publish 调用参数，得到完整表达式结果
        await self.redis.invalidate_session(run.tenant_id, run.session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(run.tenant_id, run.session_id)
        self.telemetry.metrics.runs_finished.add(  # 调用 add 执行当前步骤：self.telemetry.metrics.runs_finished.add(
            1,  # 继续向上一处调用或声明传入 1
            {  # 在函数 _finish_from_state 中执行表达式 {，推进当前业务流程
                "status": finished.status.value,  # 为多行字典定义键 "status" 及其对应值
                "agent_id": run.selected_agent_id or "router",  # 为多行字典定义键 "agent_id" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束 self.telemetry.metrics.runs_finished.add 调用参数，得到完整表达式结果
        self.telemetry.metrics.run_duration.record(  # 调用 record 执行当前步骤：self.telemetry.metrics.run_duration.record(
            budget.snapshot.active_seconds,  # 继续向上一处调用或声明传入 budget.snapshot.active_seconds
            {"agent_id": run.selected_agent_id or "router"},  # 向多行字典加入配置项 {"agent_id": run.selected_agent_id or "router"}
        )  # 结束 self.telemetry.metrics.run_duration.record 调用参数，得到完整表达式结果

    async def _handle_job_failure(self, job: JobRecord, exc: Exception) -> None:  # 定义异步函数 _handle_job_failure，封装可被事件循环调度的协程逻辑
        run = await self.store.get_run_internal(job.run_id)  # 等待 get_run_internal 完成，并将其结果保存到 run
        retryable = isinstance(exc, (OSError, TimeoutError)) or (  # 调用 isinstance 构造结果并保存到 retryable
            isinstance(exc, AppError) and exc.retryable  # 调用 isinstance 执行当前步骤：isinstance(exc, AppError) and exc.retryable
        )  # 结束函数 _handle_job_failure 的调用或声明结构
        should_retry = await self.store.fail_job(  # 等待 fail_job 完成，并将其结果保存到 should_retry
            job.id,  # 继续向上一处调用或声明传入 job.id
            self.worker_id,  # 继续向上一处调用或声明传入 self.worker_id
            max_attempts=self.settings.job_max_attempts,  # 为 self.store.fail_job 设置关键字参数 max_attempts，传入当前行给出的值
            retryable=retryable,  # 为 self.store.fail_job 设置关键字参数 retryable，传入当前行给出的值
        )  # 结束 self.store.fail_job 调用参数，得到完整表达式结果
        if should_retry:  # 判断分支条件：if should_retry:
            await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
                run.id,  # 继续向上一处调用或声明传入 run.id
                "run.retrying",  # 继续向上一处调用或声明传入 "run.retrying"
                {  # 在函数 _handle_job_failure 中执行表达式 {，推进当前业务流程
                    "status": RunStatus.RUNNING.value,  # 为多行字典定义键 "status" 及其对应值
                    "attempt": job.attempts,  # 为多行字典定义键 "attempt" 及其对应值
                    "error_code": _error_code(exc),  # 为多行字典定义键 "error_code" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
                trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
            )  # 结束 self.events.publish 调用参数，得到完整表达式结果
            return  # 提前返回空结果，结束当前函数调用
        error_code = _error_code(exc)  # 计算 _error_code(exc) 并保存到变量 error_code
        error_message = str(exc)[:2000]  # 计算 str(exc)[:2000] 并保存到变量 error_message
        finished = await self.store.finish_run(  # 等待 finish_run 完成，并将其结果保存到 finished
            run.id,  # 继续向上一处调用或声明传入 run.id
            RunStatus.FAILED,  # 继续向上一处调用或声明传入 RunStatus.FAILED
            error_code=error_code,  # 为 self.store.finish_run 设置关键字参数 error_code，传入当前行给出的值
            error_message=error_message,  # 为 self.store.finish_run 设置关键字参数 error_message，传入当前行给出的值
        )  # 结束 self.store.finish_run 调用参数，得到完整表达式结果
        await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
            run.id,  # 继续向上一处调用或声明传入 run.id
            "run.failed",  # 继续向上一处调用或声明传入 "run.failed"
            {  # 在函数 _handle_job_failure 中执行表达式 {，推进当前业务流程
                "status": finished.status.value,  # 为多行字典定义键 "status" 及其对应值
                "error_code": error_code,  # 为多行字典定义键 "error_code" 及其对应值
                "message": error_message,  # 为多行字典定义键 "message" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
            trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
        )  # 结束 self.events.publish 调用参数，得到完整表达式结果
        await self.redis.invalidate_session(run.tenant_id, run.session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(run.tenant_id, run.session_id)
        self.telemetry.metrics.runs_finished.add(  # 调用 add 执行当前步骤：self.telemetry.metrics.runs_finished.add(
            1,  # 继续向上一处调用或声明传入 1
            {  # 在函数 _handle_job_failure 中执行表达式 {，推进当前业务流程
                "status": "failed",  # 为多行字典定义键 "status" 及其对应值
                "agent_id": run.selected_agent_id or "router",  # 为多行字典定义键 "agent_id" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束 self.telemetry.metrics.runs_finished.add 调用参数，得到完整表达式结果

    async def _heartbeat(self, job: JobRecord) -> None:  # 定义异步函数 _heartbeat，封装可被事件循环调度的协程逻辑
        while True:  # 在函数 _heartbeat 中执行表达式 while True:，推进当前业务流程
            await asyncio.sleep(self.settings.worker_heartbeat_seconds)  # 等待异步操作完成并取得结果：asyncio.sleep(self.settings.worker_heartbeat_seconds)
            alive = await self.store.heartbeat_job(  # 等待 heartbeat_job 完成，并将其结果保存到 alive
                job.id,  # 继续向上一处调用或声明传入 job.id
                self.worker_id,  # 继续向上一处调用或声明传入 self.worker_id
                self.settings.worker_lease_seconds,  # 继续向上一处调用或声明传入 self.settings.worker_lease_seconds
            )  # 结束 self.store.heartbeat_job 调用参数，得到完整表达式结果
            if not alive:  # 判断分支条件：if not alive:
                raise LeaseLostError()  # 抛出明确异常，阻止错误状态被静默接受：LeaseLostError()

    async def _maintenance_loop(self) -> None:  # 定义异步函数 _maintenance_loop，封装可被事件循环调度的协程逻辑
        while not self._stop.is_set():  # 在函数 _maintenance_loop 中执行表达式 while not self._stop.is_set():，推进当前业务流程
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                exhausted_runs = await self.store.fail_exhausted_jobs(  # 等待 fail_exhausted_jobs 完成，并将其结果保存到 exhausted_runs
                    self.settings.job_max_attempts  # 在函数 _maintenance_loop 中执行表达式 self.settings.job_max_attempts，推进当前业务流程
                )  # 结束 self.store.fail_exhausted_jobs 调用参数，得到完整表达式结果
                for run_id in exhausted_runs:  # 按迭代条件执行循环：for run_id in exhausted_runs:
                    run = await self.store.get_run_internal(run_id)  # 等待 get_run_internal 完成，并将其结果保存到 run
                    await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
                        run_id,  # 继续向上一处调用或声明传入 run_id
                        "run.failed",  # 继续向上一处调用或声明传入 "run.failed"
                        {  # 在函数 _maintenance_loop 中执行表达式 {，推进当前业务流程
                            "status": RunStatus.FAILED.value,  # 为多行字典定义键 "status" 及其对应值
                            "error_code": "JOB_ATTEMPTS_EXHAUSTED",  # 为多行字典定义键 "error_code" 及其对应值
                        },  # 结束上一处多行结构，保持表达式边界清晰
                        trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
                    )  # 结束 self.events.publish 调用参数，得到完整表达式结果
                    await self.redis.invalidate_session(  # 等待异步操作完成并取得结果：self.redis.invalidate_session(
                        run.tenant_id, run.session_id  # 在函数 _maintenance_loop 中执行表达式 run.tenant_id, run.session_id，推进当前业务流程
                    )  # 结束 self.redis.invalidate_session 调用参数，得到完整表达式结果
                expired_human_runs = await self.store.expire_interventions()  # 等待 expire_interventions 完成，并将其结果保存到 expired_human_runs
                for run_id in expired_human_runs:  # 按迭代条件执行循环：for run_id in expired_human_runs:
                    run = await self.store.get_run_internal(run_id)  # 等待 get_run_internal 完成，并将其结果保存到 run
                    await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
                        run_id,  # 继续向上一处调用或声明传入 run_id
                        "run.expired",  # 继续向上一处调用或声明传入 "run.expired"
                        {  # 在函数 _maintenance_loop 中执行表达式 {，推进当前业务流程
                            "status": RunStatus.EXPIRED.value,  # 为多行字典定义键 "status" 及其对应值
                            "error_code": "HUMAN_WAIT_EXPIRED",  # 为多行字典定义键 "error_code" 及其对应值
                        },  # 结束上一处多行结构，保持表达式边界清晰
                        trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
                    )  # 结束 self.events.publish 调用参数，得到完整表达式结果
                    await self.redis.invalidate_session(  # 等待异步操作完成并取得结果：self.redis.invalidate_session(
                        run.tenant_id, run.session_id  # 在函数 _maintenance_loop 中执行表达式 run.tenant_id, run.session_id，推进当前业务流程
                    )  # 结束 self.redis.invalidate_session 调用参数，得到完整表达式结果
                expired_runs = (  # 调用 目标函数 构造结果并保存到 expired_runs
                    await self.store.list_run_ids_for_expired_sessions(  # 等待异步操作完成并取得结果：self.store.list_run_ids_for_expired_sessions(
                        session_retention_days=self.settings.session_retention_days  # 为 self.store.list_run_ids_for_expired_sessions 设置关键字参数 session_retention_days，传入当前行给出的值
                    )  # 结束 self.store.list_run_ids_for_expired_sessions 调用参数，得到完整表达式结果
                )  # 结束函数 _maintenance_loop 的调用或声明结构
                if expired_runs:  # 判断分支条件：if expired_runs:
                    await self.checkpointer.adelete_for_runs(expired_runs)  # 等待异步操作完成并取得结果：self.checkpointer.adelete_for_runs(expired_runs)
                purge = await self.store.purge_expired(  # 等待 purge_expired 完成，并将其结果保存到 purge
                    session_retention_days=self.settings.session_retention_days,  # 为 self.store.purge_expired 设置关键字参数 session_retention_days，传入当前行给出的值
                    event_retention_days=self.settings.event_retention_days,  # 为 self.store.purge_expired 设置关键字参数 event_retention_days，传入当前行给出的值
                    audit_retention_days=self.settings.audit_retention_days,  # 为 self.store.purge_expired 设置关键字参数 audit_retention_days，传入当前行给出的值
                )  # 结束 self.store.purge_expired 调用参数，得到完整表达式结果
                logger.info("Retention cleanup completed: {}", purge)  # 调用 info 执行当前步骤：logger.info("Retention cleanup completed: {}", purge)
            except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
                logger.warning(  # 调用 warning 执行当前步骤：logger.warning(
                    "Maintenance iteration failed: {}", type(exc).__name__  # 调用 目标函数 执行当前步骤："Maintenance iteration failed: {}", type(exc).__name__
                )  # 结束 logger.warning 调用参数，得到完整表达式结果
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                await asyncio.wait_for(self._stop.wait(), timeout=60)  # 等待异步操作完成并取得结果：asyncio.wait_for(self._stop.wait(), timeout=60)
            except TimeoutError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except TimeoutError:
                continue  # 跳过本轮剩余逻辑并进入下一轮迭代

    async def _load_conversation(self, run: RunRecord) -> list[dict[str, str]]:  # 定义异步函数 _load_conversation，封装可被事件循环调度的协程逻辑
        identity = Identity(  # 调用 Identity 构造结果并保存到 identity
            user_id=run.user_id,  # 为 Identity 设置关键字参数 user_id，传入当前行给出的值
            tenant_id=run.tenant_id,  # 为 Identity 设置关键字参数 tenant_id，传入当前行给出的值
            roles=frozenset({"agent:user", "agent:admin"}),  # 为 frozenset 设置关键字参数 roles，传入当前行给出的值
        )  # 结束 Identity 调用参数，得到完整表达式结果
        cached = await self.redis.get_session_snapshot(  # 等待 get_session_snapshot 完成，并将其结果保存到 cached
            run.tenant_id, run.session_id  # 在函数 _load_conversation 中执行表达式 run.tenant_id, run.session_id，推进当前业务流程
        )  # 结束 self.redis.get_session_snapshot 调用参数，得到完整表达式结果
        if cached and isinstance(cached.get("messages"), list):  # 判断分支条件：if cached and isinstance(cached.get("messages"), list):
            raw_messages = cached["messages"]  # 计算 cached["messages"] 并保存到变量 raw_messages
            messages = [  # 计算 [ 并保存到变量 messages
                SimpleNamespace(  # 调用 SimpleNamespace 执行当前步骤：SimpleNamespace(
                    run_id=item.get("run_id"),  # 为 item.get 设置关键字参数 run_id，传入当前行给出的值
                    role=item.get("role", ""),  # 为 item.get 设置关键字参数 role，传入当前行给出的值
                    content=item.get("content", ""),  # 为 item.get 设置关键字参数 content，传入当前行给出的值
                )  # 结束 SimpleNamespace 调用参数，得到完整表达式结果
                for item in raw_messages  # 按迭代条件执行循环：for item in raw_messages
                if isinstance(item, dict)  # 判断分支条件：if isinstance(item, dict)
            ]  # 结束上一处多行结构，保持表达式边界清晰
            self.telemetry.metrics.cache_events.add(1, {"result": "hit"})  # 调用 add 执行当前步骤：self.telemetry.metrics.cache_events.add(1, {"result": "hit"})
        else:  # 进入前面条件均不成立时的兜底分支
            messages = await self.store.list_messages(  # 等待 list_messages 完成，并将其结果保存到 messages
                identity,  # 继续向上一处调用或声明传入 identity
                run.session_id,  # 继续向上一处调用或声明传入 run.session_id
                limit=self.settings.max_history_turns * 3,  # 为 self.store.list_messages 设置关键字参数 limit，传入当前行给出的值
            )  # 结束 self.store.list_messages 调用参数，得到完整表达式结果
            self.telemetry.metrics.cache_events.add(1, {"result": "miss"})  # 调用 add 执行当前步骤：self.telemetry.metrics.cache_events.add(1, {"result": "miss"})
        selected = [  # 计算 [ 并保存到变量 selected
            item  # 在函数 _load_conversation 中执行表达式 item，推进当前业务流程
            for item in messages  # 按迭代条件执行循环：for item in messages
            if str(item.run_id) != str(run.id)  # 判断分支条件：if str(item.run_id) != str(run.id)
        ][-self.settings.max_history_turns * 2 :]  # 在函数 _load_conversation 中执行表达式 ][-self.settings.max_history_turns * 2 :]，推进当前业务流程
        remaining = self.settings.max_history_tokens  # 计算 self.settings.max_history_tokens 并保存到变量 remaining
        conversation: list[dict[str, str]] = []  # 计算 [] 并保存到变量 conversation
        for item in reversed(selected):  # 按迭代条件执行循环：for item in reversed(selected):
            if remaining <= 0:  # 判断分支条件：if remaining <= 0:
                break  # 提前结束当前循环并继续后续控制流
            content = item.content[:remaining]  # 计算 item.content[:remaining] 并保存到变量 content
            remaining -= len(content)  # 计算 len(content) 并保存到变量 remaining -
            conversation.append({"role": item.role, "content": content})  # 调用 append 执行当前步骤：conversation.append({"role": item.role, "content": content})
        conversation.reverse()  # 调用 reverse 执行当前步骤：conversation.reverse()
        return conversation  # 返回 conversation 给调用方

    def _build_sql_guard(self) -> SQLGuard:  # 定义函数 _build_sql_guard，封装该模块的一项明确职责
        return SQLGuard(  # 返回 SQLGuard( 给调用方
            sensitive_columns=self.settings.sensitive_columns,  # 为 SQLGuard 设置关键字参数 sensitive_columns，传入当前行给出的值
            approval_scan_rows=self.settings.sql_approval_scan_rows,  # 为 SQLGuard 设置关键字参数 approval_scan_rows，传入当前行给出的值
            high_risk_scan_rows=self.settings.sql_high_risk_scan_rows,  # 为 SQLGuard 设置关键字参数 high_risk_scan_rows，传入当前行给出的值
        )  # 结束 SQLGuard 调用参数，得到完整表达式结果

def _json_safe(value: Any) -> Any:  # 定义函数 _json_safe，封装该模块的一项明确职责
    if dataclasses.is_dataclass(value):  # 判断分支条件：if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))  # 返回 _json_safe(dataclasses.asdict(value)) 给调用方
    if isinstance(value, BaseException):  # 判断分支条件：if isinstance(value, BaseException):
        return str(value)  # 返回 str(value) 给调用方
    if isinstance(value, Enum):  # 判断分支条件：if isinstance(value, Enum):
        return value.value  # 返回 value.value 给调用方
    if isinstance(value, UUID):  # 判断分支条件：if isinstance(value, UUID):
        return str(value)  # 返回 str(value) 给调用方
    if isinstance(value, (datetime, date)):  # 判断分支条件：if isinstance(value, (datetime, date)):
        return value.isoformat()  # 返回 value.isoformat() 给调用方
    if hasattr(value, "model_dump"):  # 判断分支条件：if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())  # 返回 _json_safe(value.model_dump()) 给调用方
    if isinstance(value, dict):  # 判断分支条件：if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}  # 返回 {str(key): _json_safe(item) for key, item in value.items()} 给调用方
    if isinstance(value, (list, tuple, set)):  # 判断分支条件：if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]  # 返回 [_json_safe(item) for item in value] 给调用方
    if isinstance(value, (str, int, float, bool)) or value is None:  # 判断分支条件：if isinstance(value, (str, int, float, bool)) or value is None:
        return value  # 返回 value 给调用方
    return str(value)  # 返回 str(value) 给调用方


def _error_code(exc: Exception) -> str:  # 定义函数 _error_code，封装该模块的一项明确职责
    if isinstance(exc, AppError):  # 判断分支条件：if isinstance(exc, AppError):
        return exc.code  # 返回 exc.code 给调用方
    if isinstance(exc, TimeoutError):  # 判断分支条件：if isinstance(exc, TimeoutError):
        return "TIMEOUT"  # 返回 "TIMEOUT" 给调用方
    return type(exc).__name__.upper()  # 返回 type(exc).__name__.upper() 给调用方
