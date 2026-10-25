"""Application services for durable sessions, runs, and human interventions."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import dataclasses  # 导入dataclasses，建立本模块需要的外部能力引用
from collections.abc import AsyncIterator, Callable  # 从 collections.abc 导入 AsyncIterator, Callable，供本模块后续代码使用
from datetime import datetime  # 从 datetime 导入 datetime，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from redis import RedisError  # 从 redis 导入 RedisError，供本模块后续代码使用

from app.agents.registry import AgentRegistry  # 从 app.agents.registry 导入 AgentRegistry，供本模块后续代码使用
from app.agents.types import AgentPublicView  # 从 app.agents.types 导入 AgentPublicView，供本模块后续代码使用
from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.core.errors import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    AppError,  # 从当前 import 模块导入符号 AppError
    ConflictError,  # 从当前 import 模块导入符号 ConflictError
    DependencyUnavailableError,  # 从当前 import 模块导入符号 DependencyUnavailableError
    ForbiddenError,  # 从当前 import 模块导入符号 ForbiddenError
    NotFoundError,  # 从当前 import 模块导入符号 NotFoundError
)  # 结束多符号导入列表
from app.harness.events import EventPublisher, format_sse  # 从 app.harness.events 导入 EventPublisher, format_sse，供本模块后续代码使用
from app.harness.records import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    AuditRecord,  # 从当前 import 模块导入符号 AuditRecord
    InterventionRecord,  # 从当前 import 模块导入符号 InterventionRecord
    RunRecord,  # 从当前 import 模块导入符号 RunRecord
    SessionRecord,  # 从当前 import 模块导入符号 SessionRecord
)  # 结束多符号导入列表
from app.harness.redis_runtime import RedisRuntime  # 从 app.harness.redis_runtime 导入 RedisRuntime，供本模块后续代码使用
from app.harness.store import HarnessStore  # 从 app.harness.store 导入 HarnessStore，供本模块后续代码使用
from app.harness.types import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    TERMINAL_RUN_STATUSES,  # 从当前 import 模块导入符号 TERMINAL_RUN_STATUSES
    DecisionAction,  # 从当前 import 模块导入符号 DecisionAction
    Identity,  # 从当前 import 模块导入符号 Identity
    InterventionKind,  # 从当前 import 模块导入符号 InterventionKind
    RunStatus,  # 从当前 import 模块导入符号 RunStatus
)  # 结束多符号导入列表
from app.observability.telemetry import Telemetry  # 从 app.observability.telemetry 导入 Telemetry，供本模块后续代码使用


class RunService:  # 定义类 RunService，组织相关状态与行为
    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        *,  # 为函数 __init__ 声明参数 * 及其类型或默认值
        settings: Settings,  # 为函数 __init__ 声明参数 settings 及其类型或默认值
        store: HarnessStore,  # 为函数 __init__ 声明参数 store 及其类型或默认值
        redis: RedisRuntime,  # 为函数 __init__ 声明参数 redis 及其类型或默认值
        events: EventPublisher,  # 为函数 __init__ 声明参数 events 及其类型或默认值
        registry: AgentRegistry,  # 为函数 __init__ 声明参数 registry 及其类型或默认值
        telemetry: Telemetry,  # 为函数 __init__ 声明参数 telemetry 及其类型或默认值
    ) -> None:  # 结束 __init__ 的参数列表并声明返回类型
        self.settings = settings  # 将依赖或状态 settings 保存到实例属性 self.settings
        self.store = store  # 将依赖或状态 store 保存到实例属性 self.store
        self.redis = redis  # 将依赖或状态 redis 保存到实例属性 self.redis
        self.events = events  # 将依赖或状态 events 保存到实例属性 self.events
        self.registry = registry  # 将依赖或状态 registry 保存到实例属性 self.registry
        self.telemetry = telemetry  # 将依赖或状态 telemetry 保存到实例属性 self.telemetry

    def list_agents(self, identity: Identity) -> list[AgentPublicView]:  # 定义函数 list_agents，封装该模块的一项明确职责
        return self.registry.public_list(identity)  # 返回 self.registry.public_list(identity) 给调用方

    def get_agent(self, identity: Identity, agent_id: str) -> AgentPublicView:  # 定义函数 get_agent，封装该模块的一项明确职责
        return self.registry.public_one(identity, agent_id)  # 返回 self.registry.public_one(identity, agent_id) 给调用方

    async def create_session(self, identity: Identity, title: str) -> SessionRecord:  # 定义异步函数 create_session，封装可被事件循环调度的协程逻辑
        record = await self.store.create_session(identity, title)  # 等待 create_session 完成，并将其结果保存到 record
        await self._audit(  # 等待异步操作完成并取得结果：self._audit(
            identity,  # 继续向上一处调用或声明传入 identity
            action="session.create",  # 为 self._audit 设置关键字参数 action，传入当前行给出的值
            resource_type="session",  # 为 self._audit 设置关键字参数 resource_type，传入当前行给出的值
            resource_id=str(record.id),  # 为 str 设置关键字参数 resource_id，传入当前行给出的值
            outcome="success",  # 为 self._audit 设置关键字参数 outcome，传入当前行给出的值
        )  # 结束函数 create_session 的参数及返回类型声明并开始函数体
        return record  # 返回 record 给调用方

    async def list_sessions(  # 定义异步函数 list_sessions，封装可被事件循环调度的协程逻辑
        self,  # 为函数 list_sessions 声明参数 self 及其类型或默认值
        identity: Identity,  # 为函数 list_sessions 声明参数 identity 及其类型或默认值
        *,  # 为函数 list_sessions 声明参数 * 及其类型或默认值
        limit: int,  # 为函数 list_sessions 声明参数 limit 及其类型或默认值
        cursor: str | None,  # 为函数 list_sessions 声明参数 cursor 及其类型或默认值
    ) -> tuple[list[SessionRecord], str | None]:  # 结束 list_sessions 的参数列表并声明返回类型
        cursor_updated_at: datetime | None = None  # 计算 None 并保存到变量 cursor_updated_at
        cursor_id: UUID | None = None  # 计算 None 并保存到变量 cursor_id
        if cursor:  # 判断分支条件：if cursor:
            cursor_updated_at, cursor_id = _decode_cursor(cursor)  # 计算 _decode_cursor(cursor) 并保存到变量 cursor_updated_at, cursor_id
        records = await self.store.list_sessions(  # 等待 list_sessions 完成，并将其结果保存到 records
            identity,  # 继续向上一处调用或声明传入 identity
            limit=limit,  # 为 self.store.list_sessions 设置关键字参数 limit，传入当前行给出的值
            cursor_updated_at=cursor_updated_at,  # 为 self.store.list_sessions 设置关键字参数 cursor_updated_at，传入当前行给出的值
            cursor_id=cursor_id,  # 为 self.store.list_sessions 设置关键字参数 cursor_id，传入当前行给出的值
        )  # 结束函数 list_sessions 的参数及返回类型声明并开始函数体
        has_more = len(records) > limit  # 计算 len(records) > limit 并保存到变量 has_more
        records = records[:limit]  # 计算 records[:limit] 并保存到变量 records
        next_cursor = (  # 调用 目标函数 构造结果并保存到 next_cursor
            _encode_cursor(records[-1].updated_at, records[-1].id)  # 调用 _encode_cursor 执行当前步骤：_encode_cursor(records[-1].updated_at, records[-1].id)
            if has_more and records  # 判断分支条件：if has_more and records
            else None  # 在函数 list_sessions 中执行表达式 else None，推进当前业务流程
        )  # 结束函数 list_sessions 的参数及返回类型声明并开始函数体
        return records, next_cursor  # 返回 records, next_cursor 给调用方

    async def get_session_view(  # 定义异步函数 get_session_view，封装可被事件循环调度的协程逻辑
        self, identity: Identity, session_id: UUID  # 为函数 get_session_view 声明参数 self, identity 及其类型或默认值
    ) -> dict[str, Any]:  # 结束 get_session_view 的参数列表并声明返回类型
        session = await self.store.get_session(identity, session_id)  # 等待 get_session 完成，并将其结果保存到 session
        cached = await self.redis.get_session_snapshot(  # 等待 get_session_snapshot 完成，并将其结果保存到 cached
            identity.tenant_id, session_id  # 在函数 get_session_view 中执行表达式 identity.tenant_id, session_id，推进当前业务流程
        )  # 结束函数 get_session_view 的参数及返回类型声明并开始函数体
        if cached:  # 判断分支条件：if cached:
            self.telemetry.metrics.cache_events.add(1, {"result": "hit"})  # 调用 add 执行当前步骤：self.telemetry.metrics.cache_events.add(1, {"result": "hit"})
            return cached  # 返回 cached 给调用方
        self.telemetry.metrics.cache_events.add(1, {"result": "miss"})  # 调用 add 执行当前步骤：self.telemetry.metrics.cache_events.add(1, {"result": "miss"})
        messages = await self.store.list_messages(identity, session_id, limit=100)  # 等待 list_messages 完成，并将其结果保存到 messages
        runs = await self.store.list_session_runs(  # 等待 list_session_runs 完成，并将其结果保存到 runs
            identity, session_id, limit=20  # 在函数 get_session_view 中执行表达式 identity, session_id, limit=20，推进当前业务流程
        )  # 结束函数 get_session_view 的参数及返回类型声明并开始函数体
        snapshot = {  # 计算 { 并保存到变量 snapshot
            "session": _jsonable(dataclasses.asdict(session)),  # 为多行字典定义键 "session" 及其对应值
            "messages": [  # 为多行字典定义键 "messages" 及其对应值
                _jsonable(dataclasses.asdict(message)) for message in messages  # 调用 _jsonable 执行当前步骤：_jsonable(dataclasses.asdict(message)) for message in messages
            ],  # 结束上一处多行结构，保持表达式边界清晰
            "runs": [_jsonable(dataclasses.asdict(run)) for run in runs],  # 为多行字典定义键 "runs" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
        await self.redis.set_session_snapshot(  # 等待异步操作完成并取得结果：self.redis.set_session_snapshot(
            identity.tenant_id,  # 继续向上一处调用或声明传入 identity.tenant_id
            session_id,  # 继续向上一处调用或声明传入 session_id
            snapshot,  # 继续向上一处调用或声明传入 snapshot
            revision=session.version,  # 为 self.redis.set_session_snapshot 设置关键字参数 revision，传入当前行给出的值
        )  # 结束函数 get_session_view 的参数及返回类型声明并开始函数体
        return snapshot  # 返回 snapshot 给调用方

    async def delete_session(self, identity: Identity, session_id: UUID) -> None:  # 定义异步函数 delete_session，封装可被事件循环调度的协程逻辑
        cancelled_runs = await self.store.delete_session(identity, session_id)  # 等待 delete_session 完成，并将其结果保存到 cancelled_runs
        for run_id in cancelled_runs:  # 按迭代条件执行循环：for run_id in cancelled_runs:
            await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
                run_id,  # 继续向上一处调用或声明传入 run_id
                "run.cancelled",  # 继续向上一处调用或声明传入 "run.cancelled"
                {  # 在函数 delete_session 中执行表达式 {，推进当前业务流程
                    "status": RunStatus.CANCELLED.value,  # 为多行字典定义键 "status" 及其对应值
                    "error_code": "SESSION_DELETED",  # 为多行字典定义键 "error_code" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
                trace_id=self.telemetry.current_trace_id(),  # 为 self.telemetry.current_trace_id 设置关键字参数 trace_id，传入当前行给出的值
            )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
        await self.redis.invalidate_session(identity.tenant_id, session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(identity.tenant_id, session_id)
        await self._audit(  # 等待异步操作完成并取得结果：self._audit(
            identity,  # 继续向上一处调用或声明传入 identity
            action="session.delete",  # 为 self._audit 设置关键字参数 action，传入当前行给出的值
            resource_type="session",  # 为 self._audit 设置关键字参数 resource_type，传入当前行给出的值
            resource_id=str(session_id),  # 为 str 设置关键字参数 resource_id，传入当前行给出的值
            outcome="success",  # 为 self._audit 设置关键字参数 outcome，传入当前行给出的值
        )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体

    async def create_run(  # 定义异步函数 create_run，封装可被事件循环调度的协程逻辑
        self,  # 为函数 create_run 声明参数 self 及其类型或默认值
        identity: Identity,  # 为函数 create_run 声明参数 identity 及其类型或默认值
        *,  # 为函数 create_run 声明参数 * 及其类型或默认值
        session_id: UUID,  # 为函数 create_run 声明参数 session_id 及其类型或默认值
        query: str,  # 为函数 create_run 声明参数 query 及其类型或默认值
        requested_agent_id: str | None,  # 为函数 create_run 声明参数 requested_agent_id 及其类型或默认值
        idempotency_key: str,  # 为函数 create_run 声明参数 idempotency_key 及其类型或默认值
    ) -> RunRecord:  # 结束 create_run 的参数列表并声明返回类型
        if not self.settings.agent_execution_enabled:  # 判断分支条件：if not self.settings.agent_execution_enabled:
            raise DependencyUnavailableError("agent execution is disabled")  # 抛出明确异常，阻止错误状态被静默接受：DependencyUnavailableError("agent execution is disabled")
        if len(query) > self.settings.max_query_chars:  # 判断分支条件：if len(query) > self.settings.max_query_chars:
            raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
                code="QUERY_TOO_LONG",  # 为 AppError 设置关键字参数 code，传入当前行给出的值
                message="query exceeds the configured limit",  # 为 AppError 设置关键字参数 message，传入当前行给出的值
                status_code=422,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
                details={"max_length": self.settings.max_query_chars},  # 为 AppError 设置关键字参数 details，传入当前行给出的值
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
        if requested_agent_id:  # 判断分支条件：if requested_agent_id:
            available = {  # 计算 { 并保存到变量 available
                definition.agent_id  # 在函数 create_run 中执行表达式 definition.agent_id，推进当前业务流程
                for definition in self.registry.list_for(identity)  # 按迭代条件执行循环：for definition in self.registry.list_for(identity)
            }  # 结束上一处多行结构，保持表达式边界清晰
            if requested_agent_id not in available:  # 判断分支条件：if requested_agent_id not in available:
                raise NotFoundError("agent", requested_agent_id)  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("agent", requested_agent_id)
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            allowed, ttl = await self.redis.acquire_rate_slot(  # 等待 acquire_rate_slot 完成，并将其结果保存到 allowed, ttl
                tenant_id=identity.tenant_id,  # 为 self.redis.acquire_rate_slot 设置关键字参数 tenant_id，传入当前行给出的值
                user_id=identity.user_id,  # 为 self.redis.acquire_rate_slot 设置关键字参数 user_id，传入当前行给出的值
                limit_per_minute=self.settings.rate_limit_runs_per_minute,  # 为 self.redis.acquire_rate_slot 设置关键字参数 limit_per_minute，传入当前行给出的值
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
        except RedisError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError as exc:
            raise DependencyUnavailableError("redis") from exc  # 抛出明确异常，阻止错误状态被静默接受：DependencyUnavailableError("redis") from exc
        if not allowed:  # 判断分支条件：if not allowed:
            raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
                code="RATE_LIMITED",  # 为 AppError 设置关键字参数 code，传入当前行给出的值
                message="run rate limit exceeded",  # 为 AppError 设置关键字参数 message，传入当前行给出的值
                status_code=429,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
                details={"retry_after_seconds": ttl},  # 为 AppError 设置关键字参数 details，传入当前行给出的值
                retryable=True,  # 为 AppError 设置关键字参数 retryable，传入当前行给出的值
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
        traceparent = self.telemetry.capture_traceparent()  # 计算 self.telemetry.capture_traceparent() 并保存到变量 traceparent
        run, created = await self.store.create_run(  # 等待 create_run 完成，并将其结果保存到 run, created
            identity,  # 继续向上一处调用或声明传入 identity
            session_id=session_id,  # 为 self.store.create_run 设置关键字参数 session_id，传入当前行给出的值
            query=query,  # 为 self.store.create_run 设置关键字参数 query，传入当前行给出的值
            requested_agent_id=requested_agent_id,  # 为 self.store.create_run 设置关键字参数 requested_agent_id，传入当前行给出的值
            idempotency_key=idempotency_key,  # 为 self.store.create_run 设置关键字参数 idempotency_key，传入当前行给出的值
            trace_id=self.telemetry.current_trace_id(),  # 为 self.telemetry.current_trace_id 设置关键字参数 trace_id，传入当前行给出的值
            traceparent=traceparent,  # 为 self.store.create_run 设置关键字参数 traceparent，传入当前行给出的值
            max_user_active=self.settings.per_user_active_runs,  # 为 self.store.create_run 设置关键字参数 max_user_active，传入当前行给出的值
            max_tenant_active=self.settings.per_tenant_active_runs,  # 为 self.store.create_run 设置关键字参数 max_tenant_active，传入当前行给出的值
            max_queue_depth=self.settings.queue_max_depth,  # 为 self.store.create_run 设置关键字参数 max_queue_depth，传入当前行给出的值
        )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
        if created:  # 判断分支条件：if created:
            await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
                run.id,  # 继续向上一处调用或声明传入 run.id
                "run.queued",  # 继续向上一处调用或声明传入 "run.queued"
                {"status": RunStatus.QUEUED.value},  # 向多行字典加入配置项 {"status": RunStatus.QUEUED.value}
                trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            await self.redis.invalidate_session(identity.tenant_id, session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(identity.tenant_id, session_id)
            await self.redis.wake_workers()  # 等待异步操作完成并取得结果：self.redis.wake_workers()
        await self._audit(  # 等待异步操作完成并取得结果：self._audit(
            identity,  # 继续向上一处调用或声明传入 identity
            action="run.create",  # 为 self._audit 设置关键字参数 action，传入当前行给出的值
            resource_type="run",  # 为 self._audit 设置关键字参数 resource_type，传入当前行给出的值
            resource_id=str(run.id),  # 为 str 设置关键字参数 resource_id，传入当前行给出的值
            outcome="success" if created else "idempotent_replay",  # 为 self._audit 设置关键字参数 outcome，传入当前行给出的值
            metadata={  # 为 self._audit 设置关键字参数 metadata，传入当前行给出的值
                "requested_agent_id": requested_agent_id,  # 为多行字典定义键 "requested_agent_id" 及其对应值
                "created": created,  # 为多行字典定义键 "created" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
        if created:  # 判断分支条件：if created:
            self.telemetry.metrics.runs_started.add(  # 调用 add 执行当前步骤：self.telemetry.metrics.runs_started.add(
                1, {"requested_agent": requested_agent_id or "auto"}  # 在函数 create_run 中执行表达式 1, {"requested_agent": requested_agent_id or "auto"}，推进当前业务流程
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
        return run  # 返回 run 给调用方

    async def get_run(self, identity: Identity, run_id: UUID) -> RunRecord:  # 定义异步函数 get_run，封装可被事件循环调度的协程逻辑
        return await self.store.get_run(  # 返回 await self.store.get_run( 给调用方
            identity, run_id, allow_tenant_admin=True  # 在函数 get_run 中执行表达式 identity, run_id, allow_tenant_admin=True，推进当前业务流程
        )  # 结束函数 get_run 的参数及返回类型声明并开始函数体

    async def cancel_run(self, identity: Identity, run_id: UUID) -> RunRecord:  # 定义异步函数 cancel_run，封装可被事件循环调度的协程逻辑
        run = await self.store.cancel_run(identity, run_id)  # 等待 cancel_run 完成，并将其结果保存到 run
        await self.redis.invalidate_session(identity.tenant_id, run.session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(identity.tenant_id, run.session_id)
        await self.events.publish(  # 等待异步操作完成并取得结果：self.events.publish(
            run.id,  # 继续向上一处调用或声明传入 run.id
            "run.cancelled",  # 继续向上一处调用或声明传入 "run.cancelled"
            {"status": RunStatus.CANCELLED.value},  # 向多行字典加入配置项 {"status": RunStatus.CANCELLED.value}
            trace_id=run.trace_id,  # 为 self.events.publish 设置关键字参数 trace_id，传入当前行给出的值
        )  # 结束函数 cancel_run 的参数及返回类型声明并开始函数体
        await self._audit(  # 等待异步操作完成并取得结果：self._audit(
            identity,  # 继续向上一处调用或声明传入 identity
            action="run.cancel",  # 为 self._audit 设置关键字参数 action，传入当前行给出的值
            resource_type="run",  # 为 self._audit 设置关键字参数 resource_type，传入当前行给出的值
            resource_id=str(run.id),  # 为 str 设置关键字参数 resource_id，传入当前行给出的值
            outcome="success",  # 为 self._audit 设置关键字参数 outcome，传入当前行给出的值
        )  # 结束函数 cancel_run 的参数及返回类型声明并开始函数体
        return run  # 返回 run 给调用方

    async def list_interventions(  # 定义异步函数 list_interventions，封装可被事件循环调度的协程逻辑
        self, identity: Identity, run_id: UUID  # 为函数 list_interventions 声明参数 self, identity 及其类型或默认值
    ) -> list[InterventionRecord]:  # 结束 list_interventions 的参数列表并声明返回类型
        await self.store.get_run(identity, run_id, allow_tenant_admin=True)  # 等待异步操作完成并取得结果：self.store.get_run(identity, run_id, allow_tenant_admin=True)
        return await self.store.list_interventions(run_id)  # 返回 await self.store.list_interventions(run_id) 给调用方

    async def respond_to_intervention(  # 定义异步函数 respond_to_intervention，封装可被事件循环调度的协程逻辑
        self,  # 为函数 respond_to_intervention 声明参数 self 及其类型或默认值
        identity: Identity,  # 为函数 respond_to_intervention 声明参数 identity 及其类型或默认值
        intervention_id: UUID,  # 为函数 respond_to_intervention 声明参数 intervention_id 及其类型或默认值
        *,  # 为函数 respond_to_intervention 声明参数 * 及其类型或默认值
        expected_version: int,  # 为函数 respond_to_intervention 声明参数 expected_version 及其类型或默认值
        action: DecisionAction,  # 为函数 respond_to_intervention 声明参数 action 及其类型或默认值
        decision: dict[str, Any],  # 为函数 respond_to_intervention 声明参数 decision 及其类型或默认值
    ) -> InterventionRecord:  # 结束 respond_to_intervention 的参数列表并声明返回类型
        intervention = await self.store.get_intervention(intervention_id)  # 等待 get_intervention 完成，并将其结果保存到 intervention
        run = await self.store.get_run(  # 等待 get_run 完成，并将其结果保存到 run
            identity, intervention.run_id, allow_tenant_admin=True  # 在函数 respond_to_intervention 中执行表达式 identity, intervention.run_id, allow_tenant_admin=True，推进当前业务流程
        )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
        payload = dict(decision)  # 计算 dict(decision) 并保存到变量 payload
        if intervention.kind == InterventionKind.AGENT_SELECTION:  # 判断分支条件：if intervention.kind == InterventionKind.AGENT_SELECTION:
            if not (  # 判断分支条件：if not (
                identity.has_role("agent:user")  # 调用 has_role 执行当前步骤：identity.has_role("agent:user")
                or identity.has_role("agent:admin")  # 调用 目标函数 执行当前步骤：or identity.has_role("agent:admin")
            ):  # 结束 respond_to_intervention 的参数列表并声明返回类型
                raise ForbiddenError("agent:user role is required")  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError("agent:user role is required")
            agent_id = str(payload.get("agent_id", ""))  # 计算 str(payload.get("agent_id", "")) 并保存到变量 agent_id
            self.registry.get(agent_id)  # 调用 get 执行当前步骤：self.registry.get(agent_id)
            payload = {"agent_id": agent_id}  # 计算 {"agent_id": agent_id} 并保存到变量 payload
        elif intervention.kind == InterventionKind.SQL_APPROVAL:  # 在前一条件不成立时继续判断：elif intervention.kind == InterventionKind.SQL_APPROVAL:
            if not identity.has_role("agent:approver"):  # 判断分支条件：if not identity.has_role("agent:approver"):
                raise ForbiddenError("agent:approver role is required")  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError("agent:approver role is required")
            if (  # 判断分支条件：if (
                intervention.payload.get("high_risk")  # 调用 get 执行当前步骤：intervention.payload.get("high_risk")
                and identity.user_id == run.user_id  # 在函数 respond_to_intervention 中执行表达式 and identity.user_id == run.user_id，推进当前业务流程
            ):  # 结束 respond_to_intervention 的参数列表并声明返回类型
                raise ForbiddenError(  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError(
                    "high-risk SQL must be approved by a different approver"  # 在函数 respond_to_intervention 中执行表达式 "high-risk SQL must be approved by a different approver"，推进当前业务流程
                )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
            if action in {DecisionAction.EDIT, DecisionAction.REJECT}:  # 判断分支条件：if action in {DecisionAction.EDIT, DecisionAction.REJECT}:
                if action == DecisionAction.EDIT and not str(  # 判断分支条件：if action == DecisionAction.EDIT and not str(
                    payload.get("edited_sql", "")  # 调用 get 执行当前步骤：payload.get("edited_sql", "")
                ).strip():  # 在函数 respond_to_intervention 中执行表达式 ).strip():，推进当前业务流程
                    raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
                        code="EDITED_SQL_REQUIRED",  # 为 AppError 设置关键字参数 code，传入当前行给出的值
                        message="edited_sql is required for an edit decision",  # 为 AppError 设置关键字参数 message，传入当前行给出的值
                        status_code=422,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
                    )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
                if action == DecisionAction.REJECT and not str(  # 判断分支条件：if action == DecisionAction.REJECT and not str(
                    payload.get("reason", "")  # 调用 get 执行当前步骤：payload.get("reason", "")
                ).strip():  # 在函数 respond_to_intervention 中执行表达式 ).strip():，推进当前业务流程
                    raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
                        code="REJECTION_REASON_REQUIRED",  # 为 AppError 设置关键字参数 code，传入当前行给出的值
                        message="reason is required for a rejection",  # 为 AppError 设置关键字参数 message，传入当前行给出的值
                        status_code=422,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
                    )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
            payload = {  # 计算 { 并保存到变量 payload
                "action": action.value,  # 为多行字典定义键 "action" 及其对应值
                "sql_hash": intervention.payload.get("sql_hash"),  # 为多行字典定义键 "sql_hash" 及其对应值
                "edited_sql": payload.get("edited_sql"),  # 为多行字典定义键 "edited_sql" 及其对应值
                "reason": payload.get("reason"),  # 为多行字典定义键 "reason" 及其对应值
            }  # 结束上一处多行结构，保持表达式边界清晰
        else:  # 进入前面条件均不成立时的兜底分支
            raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                "UNKNOWN_INTERVENTION", "unknown intervention kind"  # 在函数 respond_to_intervention 中执行表达式 "UNKNOWN_INTERVENTION", "unknown intervention kind"，推进当前业务流程
            )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
        record = await self.store.respond_to_intervention(  # 等待 respond_to_intervention 完成，并将其结果保存到 record
            intervention_id,  # 继续向上一处调用或声明传入 intervention_id
            actor=identity,  # 为 self.store.respond_to_intervention 设置关键字参数 actor，传入当前行给出的值
            expected_version=expected_version,  # 为 self.store.respond_to_intervention 设置关键字参数 expected_version，传入当前行给出的值
            action=action,  # 为 self.store.respond_to_intervention 设置关键字参数 action，传入当前行给出的值
            decision=payload,  # 为 self.store.respond_to_intervention 设置关键字参数 decision，传入当前行给出的值
            traceparent=self.telemetry.capture_traceparent(),  # 为 self.telemetry.capture_traceparent 设置关键字参数 traceparent，传入当前行给出的值
        )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
        await self.redis.invalidate_session(identity.tenant_id, run.session_id)  # 等待异步操作完成并取得结果：self.redis.invalidate_session(identity.tenant_id, run.session_id)
        await self.redis.wake_workers()  # 等待异步操作完成并取得结果：self.redis.wake_workers()
        await self._audit(  # 等待异步操作完成并取得结果：self._audit(
            identity,  # 继续向上一处调用或声明传入 identity
            action=f"intervention.{action.value}",  # 为 self._audit 设置关键字参数 action，传入当前行给出的值
            resource_type="intervention",  # 为 self._audit 设置关键字参数 resource_type，传入当前行给出的值
            resource_id=str(record.id),  # 为 str 设置关键字参数 resource_id，传入当前行给出的值
            outcome="success",  # 为 self._audit 设置关键字参数 outcome，传入当前行给出的值
            metadata={"run_id": str(record.run_id), "kind": record.kind.value},  # 为 str 设置关键字参数 metadata，传入当前行给出的值
        )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
        return record  # 返回 record 给调用方

    async def stream_run_events(  # 定义异步函数 stream_run_events，封装可被事件循环调度的协程逻辑
        self,  # 为函数 stream_run_events 声明参数 self 及其类型或默认值
        identity: Identity,  # 为函数 stream_run_events 声明参数 identity 及其类型或默认值
        run_id: UUID,  # 为函数 stream_run_events 声明参数 run_id 及其类型或默认值
        *,  # 为函数 stream_run_events 声明参数 * 及其类型或默认值
        after_seq: int,  # 为函数 stream_run_events 声明参数 after_seq 及其类型或默认值
        is_disconnected: Callable[[], Any] | None = None,  # 为函数 stream_run_events 声明参数 is_disconnected 及其类型或默认值
    ) -> AsyncIterator[str]:  # 结束 stream_run_events 的参数列表并声明返回类型
        await self.store.get_run(identity, run_id, allow_tenant_admin=True)  # 等待异步操作完成并取得结果：self.store.get_run(identity, run_id, allow_tenant_admin=True)
        cursor = max(after_seq, 0)  # 计算 max(after_seq, 0) 并保存到变量 cursor
        last_heartbeat = asyncio.get_running_loop().time()  # 计算 asyncio.get_running_loop().time() 并保存到变量 last_heartbeat
        self.telemetry.metrics.sse_active.add(1)  # 调用 add 执行当前步骤：self.telemetry.metrics.sse_active.add(1)
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            yield "retry: 3000\n\n"  # 产出流式结果 "retry: 3000\n\n"，保留生成器后续执行状态
            while True:  # 在函数 stream_run_events 中执行表达式 while True:，推进当前业务流程
                if is_disconnected is not None and await _maybe_await(  # 判断分支条件：if is_disconnected is not None and await _maybe_await(
                    is_disconnected()  # 调用 is_disconnected 执行当前步骤：is_disconnected()
                ):  # 结束 stream_run_events 的参数列表并声明返回类型
                    break  # 提前结束当前循环并继续后续控制流
                events = await self.events.replay(  # 等待 replay 完成，并将其结果保存到 events
                    run_id, after_seq=cursor, limit=200  # 在函数 stream_run_events 中执行表达式 run_id, after_seq=cursor, limit=200，推进当前业务流程
                )  # 结束函数 stream_run_events 的参数及返回类型声明并开始函数体
                for event in events:  # 按迭代条件执行循环：for event in events:
                    cursor = event.seq  # 计算 event.seq 并保存到变量 cursor
                    yield format_sse(event)  # 产出流式结果 format_sse(event)，保留生成器后续执行状态
                current = await self.store.get_run(  # 等待 get_run 完成，并将其结果保存到 current
                    identity, run_id, allow_tenant_admin=True  # 在函数 stream_run_events 中执行表达式 identity, run_id, allow_tenant_admin=True，推进当前业务流程
                )  # 结束函数 stream_run_events 的参数及返回类型声明并开始函数体
                if current.status in TERMINAL_RUN_STATUSES and not events:  # 判断分支条件：if current.status in TERMINAL_RUN_STATUSES and not events:
                    break  # 提前结束当前循环并继续后续控制流
                now = asyncio.get_running_loop().time()  # 计算 asyncio.get_running_loop().time() 并保存到变量 now
                if now - last_heartbeat >= 15:  # 判断分支条件：if now - last_heartbeat >= 15:
                    last_heartbeat = now  # 计算 now 并保存到变量 last_heartbeat
                    yield f"event: heartbeat\ndata: {{\"run_id\":\"{run_id}\"}}\n\n"  # 产出流式结果 f"event: heartbeat\ndata: {{\"run_id\":\"{run_id}\"}}\n\n"，保留生成器后续执行状态
                await asyncio.sleep(0.75 if not events else 0.05)  # 等待异步操作完成并取得结果：asyncio.sleep(0.75 if not events else 0.05)
        finally:  # 进入无论成功失败都必须执行的资源清理分支
            self.telemetry.metrics.sse_active.add(-1)  # 调用 add 执行当前步骤：self.telemetry.metrics.sse_active.add(-1)

    async def expire_human_waits(self) -> list[UUID]:  # 定义异步函数 expire_human_waits，封装可被事件循环调度的协程逻辑
        return await self.store.expire_interventions()  # 返回 await self.store.expire_interventions() 给调用方

    async def _audit(  # 定义异步函数 _audit，封装可被事件循环调度的协程逻辑
        self,  # 为函数 _audit 声明参数 self 及其类型或默认值
        identity: Identity,  # 为函数 _audit 声明参数 identity 及其类型或默认值
        *,  # 为函数 _audit 声明参数 * 及其类型或默认值
        action: str,  # 为函数 _audit 声明参数 action 及其类型或默认值
        resource_type: str,  # 为函数 _audit 声明参数 resource_type 及其类型或默认值
        resource_id: str,  # 为函数 _audit 声明参数 resource_id 及其类型或默认值
        outcome: str,  # 为函数 _audit 声明参数 outcome 及其类型或默认值
        metadata: dict[str, Any] | None = None,  # 为函数 _audit 声明参数 metadata 及其类型或默认值
    ) -> None:  # 结束 _audit 的参数列表并声明返回类型
        await self.store.add_audit(  # 等待异步操作完成并取得结果：self.store.add_audit(
            AuditRecord(  # 调用 AuditRecord 执行当前步骤：AuditRecord(
                id=UUID(int=0),  # 为 UUID 设置关键字参数 id，传入当前行给出的值
                tenant_id=identity.tenant_id,  # 为 AuditRecord 设置关键字参数 tenant_id，传入当前行给出的值
                actor_id=identity.user_id,  # 为 AuditRecord 设置关键字参数 actor_id，传入当前行给出的值
                action=action,  # 为 AuditRecord 设置关键字参数 action，传入当前行给出的值
                resource_type=resource_type,  # 为 AuditRecord 设置关键字参数 resource_type，传入当前行给出的值
                resource_id=resource_id,  # 为 AuditRecord 设置关键字参数 resource_id，传入当前行给出的值
                outcome=outcome,  # 为 AuditRecord 设置关键字参数 outcome，传入当前行给出的值
                trace_id=self.telemetry.current_trace_id(),  # 为 self.telemetry.current_trace_id 设置关键字参数 trace_id，传入当前行给出的值
                metadata=metadata or {},  # 为 AuditRecord 设置关键字参数 metadata，传入当前行给出的值
            )  # 结束函数 _audit 的参数及返回类型声明并开始函数体
        )  # 结束函数 _audit 的参数及返回类型声明并开始函数体


def _jsonable(value: Any) -> Any:  # 定义函数 _jsonable，封装该模块的一项明确职责
    if isinstance(value, dict):  # 判断分支条件：if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}  # 返回 {str(key): _jsonable(item) for key, item in value.items()} 给调用方
    if isinstance(value, list):  # 判断分支条件：if isinstance(value, list):
        return [_jsonable(item) for item in value]  # 返回 [_jsonable(item) for item in value] 给调用方
    if isinstance(value, datetime):  # 判断分支条件：if isinstance(value, datetime):
        return value.isoformat()  # 返回 value.isoformat() 给调用方
    if isinstance(value, UUID):  # 判断分支条件：if isinstance(value, UUID):
        return str(value)  # 返回 str(value) 给调用方
    if isinstance(value, str) or hasattr(value, "value"):  # 判断分支条件：if isinstance(value, str) or hasattr(value, "value"):
        return getattr(value, "value", value)  # 返回 getattr(value, "value", value) 给调用方
    return value  # 返回 value 给调用方


def _encode_cursor(updated_at: datetime, item_id: UUID) -> str:  # 定义函数 _encode_cursor，封装该模块的一项明确职责
    import base64  # 导入base64，建立本模块需要的外部能力引用

    raw = f"{updated_at.isoformat()}|{item_id}".encode()  # 计算 f"{updated_at.isoformat()}|{item_id}".encode() 并保存到变量 raw
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")  # 返回 base64.urlsafe_b64encode(raw).decode().rstrip("=") 给调用方


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:  # 定义函数 _decode_cursor，封装该模块的一项明确职责
    import base64  # 导入base64，建立本模块需要的外部能力引用

    padding = "=" * (-len(cursor) % 4)  # 计算 "=" * (-len(cursor) % 4) 并保存到变量 padding
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        raw = base64.urlsafe_b64decode(cursor + padding).decode()  # 计算 base64.urlsafe_b64decode(cursor + padding).decode() 并保存到变量 raw
        timestamp, item_id = raw.split("|", maxsplit=1)  # 计算 raw.split("|", maxsplit=1) 并保存到变量 timestamp, item_id
        return datetime.fromisoformat(timestamp), UUID(item_id)  # 返回 datetime.fromisoformat(timestamp), UUID(item_id) 给调用方
    except (ValueError, TypeError) as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except (ValueError, TypeError) as exc:
        raise ConflictError("INVALID_CURSOR", "cursor is invalid") from exc  # 抛出明确异常，阻止错误状态被静默接受：ConflictError("INVALID_CURSOR", "cursor is invalid") from exc


async def _maybe_await(value: Any) -> Any:  # 定义异步函数 _maybe_await，封装可被事件循环调度的协程逻辑
    if hasattr(value, "__await__"):  # 判断分支条件：if hasattr(value, "__await__"):
        return await value  # 返回 await value 给调用方
    return value  # 返回 value 给调用方
