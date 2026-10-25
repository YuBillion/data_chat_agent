"""PostgreSQL authority for sessions, runs, jobs, events, and interventions."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import hashlib  # 导入hashlib，建立本模块需要的外部能力引用
import json  # 导入json，建立本模块需要的外部能力引用
from datetime import datetime, timedelta  # 从 datetime 导入 datetime, timedelta，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用
from uuid import UUID, uuid4  # 从 uuid 导入 UUID, uuid4，供本模块后续代码使用

from sqlalchemy import and_, delete, func, or_, select, text, update  # 从 sqlalchemy 导入 and_, delete, func, or_, select, text, update，供本模块后续代码使用
from sqlalchemy.exc import IntegrityError  # 从 sqlalchemy.exc 导入 IntegrityError，供本模块后续代码使用
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # 从 sqlalchemy.ext.asyncio 导入 AsyncSession, async_sessionmaker，供本模块后续代码使用

from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError  # 从 app.core.errors 导入 AppError, ConflictError, ForbiddenError, NotFoundError，供本模块后续代码使用
from app.harness.db_models import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    HARNESS_SCHEMA,  # 从当前 import 模块导入符号 HARNESS_SCHEMA
    AuditLogRow,  # 从当前 import 模块导入符号 AuditLogRow
    HarnessSessionRow,  # 从当前 import 模块导入符号 HarnessSessionRow
    HumanInterventionRow,  # 从当前 import 模块导入符号 HumanInterventionRow
    RunEventRow,  # 从当前 import 模块导入符号 RunEventRow
    RunJobRow,  # 从当前 import 模块导入符号 RunJobRow
    RunRow,  # 从当前 import 模块导入符号 RunRow
    SessionMessageRow,  # 从当前 import 模块导入符号 SessionMessageRow
)  # 结束多符号导入列表
from app.harness.records import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    AuditRecord,  # 从当前 import 模块导入符号 AuditRecord
    EventRecord,  # 从当前 import 模块导入符号 EventRecord
    InterventionRecord,  # 从当前 import 模块导入符号 InterventionRecord
    JobRecord,  # 从当前 import 模块导入符号 JobRecord
    MessageRecord,  # 从当前 import 模块导入符号 MessageRecord
    RunRecord,  # 从当前 import 模块导入符号 RunRecord
    SessionRecord,  # 从当前 import 模块导入符号 SessionRecord
)  # 结束多符号导入列表
from app.harness.types import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    TERMINAL_RUN_STATUSES,  # 从当前 import 模块导入符号 TERMINAL_RUN_STATUSES
    DecisionAction,  # 从当前 import 模块导入符号 DecisionAction
    Identity,  # 从当前 import 模块导入符号 Identity
    InterventionKind,  # 从当前 import 模块导入符号 InterventionKind
    InterventionStatus,  # 从当前 import 模块导入符号 InterventionStatus
    JobStatus,  # 从当前 import 模块导入符号 JobStatus
    JobType,  # 从当前 import 模块导入符号 JobType
    RouteMode,  # 从当前 import 模块导入符号 RouteMode
    RunStatus,  # 从当前 import 模块导入符号 RunStatus
    utc_now,  # 从当前 import 模块导入符号 utc_now
)  # 结束多符号导入列表

ACTIVE_RUN_STATUSES = (  # 调用 目标函数 构造结果并保存到 ACTIVE_RUN_STATUSES
    RunStatus.QUEUED.value,  # 向多行序列加入元素 RunStatus.QUEUED.value
    RunStatus.RUNNING.value,  # 向多行序列加入元素 RunStatus.RUNNING.value
    RunStatus.WAITING_HUMAN.value,  # 向多行序列加入元素 RunStatus.WAITING_HUMAN.value
)  # 结束上一处多行结构，保持表达式边界清晰


class HarnessStore:  # 定义类 HarnessStore，组织相关状态与行为
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        self.session_factory = session_factory  # 将依赖或状态 session_factory 保存到实例属性 self.session_factory

    async def ping(self) -> None:  # 定义异步函数 ping，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            await session.execute(text("select 1"))  # 等待异步操作完成并取得结果：session.execute(text("select 1"))

    # Sessions and messages

    async def create_session(self, identity: Identity, title: str) -> SessionRecord:  # 定义异步函数 create_session，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            row = HarnessSessionRow(  # 调用 HarnessSessionRow 构造结果并保存到 row
                tenant_id=identity.tenant_id,  # 为 HarnessSessionRow 设置关键字参数 tenant_id，传入当前行给出的值
                user_id=identity.user_id,  # 为 HarnessSessionRow 设置关键字参数 user_id，传入当前行给出的值
                title=title[:200],  # 为 HarnessSessionRow 设置关键字参数 title，传入当前行给出的值
            )  # 结束函数 create_session 的参数及返回类型声明并开始函数体
            session.add(row)  # 调用 add 执行当前步骤：session.add(row)
            await session.flush()  # 等待异步操作完成并取得结果：session.flush()
            record = _session_record(row)  # 计算 _session_record(row) 并保存到变量 record
        return record  # 返回 record 给调用方

    async def list_sessions(  # 定义异步函数 list_sessions，封装可被事件循环调度的协程逻辑
        self,  # 为函数 list_sessions 声明参数 self 及其类型或默认值
        identity: Identity,  # 为函数 list_sessions 声明参数 identity 及其类型或默认值
        *,  # 为函数 list_sessions 声明参数 * 及其类型或默认值
        limit: int,  # 为函数 list_sessions 声明参数 limit 及其类型或默认值
        cursor_updated_at: datetime | None = None,  # 为函数 list_sessions 声明参数 cursor_updated_at 及其类型或默认值
        cursor_id: UUID | None = None,  # 为函数 list_sessions 声明参数 cursor_id 及其类型或默认值
    ) -> list[SessionRecord]:  # 结束 list_sessions 的参数列表并声明返回类型
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            stmt = select(HarnessSessionRow).where(  # 调用 select 构造结果并保存到 stmt
                HarnessSessionRow.tenant_id == identity.tenant_id,  # 继续向上一处调用或声明传入 HarnessSessionRow.tenant_id == identity.tenant_id
                HarnessSessionRow.user_id == identity.user_id,  # 继续向上一处调用或声明传入 HarnessSessionRow.user_id == identity.user_id
                HarnessSessionRow.status == "active",  # 继续向上一处调用或声明传入 HarnessSessionRow.status == "active"
                HarnessSessionRow.redacted_at.is_(None),  # 继续向上一处调用或声明传入 HarnessSessionRow.redacted_at.is_(None)
            )  # 结束函数 list_sessions 的参数及返回类型声明并开始函数体
            if cursor_updated_at and cursor_id:  # 判断分支条件：if cursor_updated_at and cursor_id:
                stmt = stmt.where(  # 调用 where 构造结果并保存到 stmt
                    or_(  # 调用 or_ 执行当前步骤：or_(
                        HarnessSessionRow.updated_at < cursor_updated_at,  # 继续向上一处调用或声明传入 HarnessSessionRow.updated_at < cursor_updated_at
                        and_(  # 调用 and_ 执行当前步骤：and_(
                            HarnessSessionRow.updated_at == cursor_updated_at,  # 继续向上一处调用或声明传入 HarnessSessionRow.updated_at == cursor_updated_at
                            HarnessSessionRow.id < cursor_id,  # 继续向上一处调用或声明传入 HarnessSessionRow.id < cursor_id
                        ),  # 结束函数 list_sessions 的参数及返回类型声明并开始函数体
                    )  # 结束函数 list_sessions 的参数及返回类型声明并开始函数体
                )  # 结束函数 list_sessions 的参数及返回类型声明并开始函数体
            stmt = stmt.order_by(  # 调用 order_by 构造结果并保存到 stmt
                HarnessSessionRow.updated_at.desc(), HarnessSessionRow.id.desc()  # 调用 desc 执行当前步骤：HarnessSessionRow.updated_at.desc(), HarnessSessionRow.id.desc()
            ).limit(limit + 1)  # 调用 目标函数 执行当前步骤：).limit(limit + 1)
            rows = (await session.scalars(stmt)).all()  # 计算 (await session.scalars(stmt)).all() 并保存到变量 rows
            return [_session_record(row) for row in rows]  # 返回 [_session_record(row) for row in rows] 给调用方

    async def get_session(  # 定义异步函数 get_session，封装可被事件循环调度的协程逻辑
        self,  # 为函数 get_session 声明参数 self 及其类型或默认值
        identity: Identity,  # 为函数 get_session 声明参数 identity 及其类型或默认值
        session_id: UUID,  # 为函数 get_session 声明参数 session_id 及其类型或默认值
        *,  # 为函数 get_session 声明参数 * 及其类型或默认值
        include_deleted: bool = False,  # 为函数 get_session 声明参数 include_deleted 及其类型或默认值
    ) -> SessionRecord:  # 结束 get_session 的参数列表并声明返回类型
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            row = await session.get(HarnessSessionRow, session_id)  # 等待 get 完成，并将其结果保存到 row
            if (  # 判断分支条件：if (
                not row  # 在函数 get_session 中执行表达式 not row，推进当前业务流程
                or (  # 调用 or 执行当前步骤：or (
                    not include_deleted  # 在函数 get_session 中执行表达式 not include_deleted，推进当前业务流程
                    and (row.status != "active" or row.redacted_at is not None)  # 调用 and 执行当前步骤：and (row.status != "active" or row.redacted_at is not None)
                )  # 结束函数 get_session 的参数及返回类型声明并开始函数体
            ):  # 结束 get_session 的参数列表并声明返回类型
                raise NotFoundError("session", str(session_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("session", str(session_id))
            if row.tenant_id != identity.tenant_id:  # 判断分支条件：if row.tenant_id != identity.tenant_id:
                raise ForbiddenError()  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError()
            if row.user_id != identity.user_id and not identity.has_role("agent:admin"):  # 判断分支条件：if row.user_id != identity.user_id and not identity.has_role("agent:adm…
                raise ForbiddenError()  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError()
            return _session_record(row)  # 返回 _session_record(row) 给调用方

    async def list_messages(  # 定义异步函数 list_messages，封装可被事件循环调度的协程逻辑
        self, identity: Identity, session_id: UUID, *, limit: int = 100  # 为函数 list_messages 声明参数 self, identity 及其类型或默认值
    ) -> list[MessageRecord]:  # 结束 list_messages 的参数列表并声明返回类型
        await self.get_session(identity, session_id)  # 等待异步操作完成并取得结果：self.get_session(identity, session_id)
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            rows = (  # 调用 目标函数 构造结果并保存到 rows
                await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                    select(SessionMessageRow)  # 调用 select 执行当前步骤：select(SessionMessageRow)
                    .where(SessionMessageRow.session_id == session_id)  # 调用 目标函数 执行当前步骤：.where(SessionMessageRow.session_id == session_id)
                    .order_by(SessionMessageRow.created_at.desc())  # 调用 目标函数 执行当前步骤：.order_by(SessionMessageRow.created_at.desc())
                    .limit(limit)  # 调用 目标函数 执行当前步骤：.limit(limit)
                )  # 结束函数 list_messages 的参数及返回类型声明并开始函数体
            ).all()  # 调用 目标函数 执行当前步骤：).all()
        return [_message_record(row) for row in reversed(rows)]  # 返回 [_message_record(row) for row in reversed(rows)] 给调用方

    async def add_message(  # 定义异步函数 add_message，封装可被事件循环调度的协程逻辑
        self,  # 为函数 add_message 声明参数 self 及其类型或默认值
        *,  # 为函数 add_message 声明参数 * 及其类型或默认值
        session_id: UUID,  # 为函数 add_message 声明参数 session_id 及其类型或默认值
        run_id: UUID | None,  # 为函数 add_message 声明参数 run_id 及其类型或默认值
        role: str,  # 为函数 add_message 声明参数 role 及其类型或默认值
        content: str,  # 为函数 add_message 声明参数 content 及其类型或默认值
        metadata: dict[str, Any] | None = None,  # 为函数 add_message 声明参数 metadata 及其类型或默认值
        session: AsyncSession | None = None,  # 为函数 add_message 声明参数 session 及其类型或默认值
    ) -> MessageRecord:  # 结束 add_message 的参数列表并声明返回类型
        async def _add(db: AsyncSession) -> MessageRecord:  # 定义异步函数 _add，封装可被事件循环调度的协程逻辑
            row = SessionMessageRow(  # 调用 SessionMessageRow 构造结果并保存到 row
                session_id=session_id,  # 为 SessionMessageRow 设置关键字参数 session_id，传入当前行给出的值
                run_id=run_id,  # 为 SessionMessageRow 设置关键字参数 run_id，传入当前行给出的值
                role=role,  # 为 SessionMessageRow 设置关键字参数 role，传入当前行给出的值
                content=content,  # 为 SessionMessageRow 设置关键字参数 content，传入当前行给出的值
                metadata_json=metadata or {},  # 为 SessionMessageRow 设置关键字参数 metadata_json，传入当前行给出的值
            )  # 结束函数 _add 的参数及返回类型声明并开始函数体
            db.add(row)  # 调用 add 执行当前步骤：db.add(row)
            await db.flush()  # 等待异步操作完成并取得结果：db.flush()
            await db.execute(  # 等待异步操作完成并取得结果：db.execute(
                update(HarnessSessionRow)  # 调用 update 执行当前步骤：update(HarnessSessionRow)
                .where(HarnessSessionRow.id == session_id)  # 调用 目标函数 执行当前步骤：.where(HarnessSessionRow.id == session_id)
                .values(updated_at=func.now(), version=HarnessSessionRow.version + 1)  # 调用 目标函数 执行当前步骤：.values(updated_at=func.now(), version=HarnessSessionRow.version + 1)
            )  # 结束函数 _add 的参数及返回类型声明并开始函数体
            return _message_record(row)  # 返回 _message_record(row) 给调用方

        if session is not None:  # 判断分支条件：if session is not None:
            return await _add(session)  # 返回 await _add(session) 给调用方
        async with self.session_factory() as db, db.begin():  # 进入受管理的上下文 async with self.session_factory() as db, db.begin():，确保资源正确获取与释放
            return await _add(db)  # 返回 await _add(db) 给调用方

    async def delete_session(  # 定义异步函数 delete_session，封装可被事件循环调度的协程逻辑
        self, identity: Identity, session_id: UUID  # 为函数 delete_session 声明参数 self, identity 及其类型或默认值
    ) -> list[UUID]:  # 结束 delete_session 的参数列表并声明返回类型
        await self.get_session(identity, session_id)  # 等待异步操作完成并取得结果：self.get_session(identity, session_id)
        now = utc_now()  # 计算 utc_now() 并保存到变量 now
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                update(HarnessSessionRow)  # 调用 update 执行当前步骤：update(HarnessSessionRow)
                .where(HarnessSessionRow.id == session_id)  # 调用 目标函数 执行当前步骤：.where(HarnessSessionRow.id == session_id)
                .values(status="deleted", deleted_at=now, version=HarnessSessionRow.version + 1)  # 调用 目标函数 执行当前步骤：.values(status="deleted", deleted_at=now, version=HarnessSessionRow.ver…
            )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
            active_runs = (  # 调用 目标函数 构造结果并保存到 active_runs
                await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                    select(RunRow).where(  # 调用 select 执行当前步骤：select(RunRow).where(
                        RunRow.session_id == session_id,  # 继续向上一处调用或声明传入 RunRow.session_id == session_id
                        RunRow.status.in_(ACTIVE_RUN_STATUSES),  # 继续向上一处调用或声明传入 RunRow.status.in_(ACTIVE_RUN_STATUSES)
                    )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
                )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
            ).all()  # 调用 目标函数 执行当前步骤：).all()
            for run in active_runs:  # 按迭代条件执行循环：for run in active_runs:
                run.status = RunStatus.CANCELLED.value  # 计算 RunStatus.CANCELLED.value 并保存到变量 run.status
                run.error_code = "SESSION_DELETED"  # 计算 "SESSION_DELETED" 并保存到变量 run.error_code
                run.completed_at = now  # 计算 now 并保存到变量 run.completed_at
                run.version += 1  # 计算 1 并保存到变量 run.version +
            if active_runs:  # 判断分支条件：if active_runs:
                active_run_ids = [run.id for run in active_runs]  # 计算 [run.id for run in active_runs] 并保存到变量 active_run_ids
                await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                    update(RunJobRow)  # 调用 update 执行当前步骤：update(RunJobRow)
                    .where(  # 调用 目标函数 执行当前步骤：.where(
                        RunJobRow.run_id.in_(active_run_ids),  # 继续向上一处调用或声明传入 RunJobRow.run_id.in_(active_run_ids)
                        RunJobRow.status.in_(  # 调用 in_ 执行当前步骤：RunJobRow.status.in_(
                            (JobStatus.QUEUED.value, JobStatus.LEASED.value)  # 调用 目标函数 执行当前步骤：(JobStatus.QUEUED.value, JobStatus.LEASED.value)
                        ),  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
                    )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
                    .values(status=JobStatus.CANCELLED.value, updated_at=now)  # 调用 目标函数 执行当前步骤：.values(status=JobStatus.CANCELLED.value, updated_at=now)
                )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
                await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                    update(HumanInterventionRow)  # 调用 update 执行当前步骤：update(HumanInterventionRow)
                    .where(  # 调用 目标函数 执行当前步骤：.where(
                        HumanInterventionRow.run_id.in_(active_run_ids),  # 继续向上一处调用或声明传入 HumanInterventionRow.run_id.in_(active_run_ids)
                        HumanInterventionRow.status  # 在函数 delete_session 中执行表达式 HumanInterventionRow.status，推进当前业务流程
                        == InterventionStatus.PENDING.value,  # 继续向上一处调用或声明传入 == InterventionStatus.PENDING.value
                    )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
                    .values(status=InterventionStatus.CANCELLED.value)  # 调用 目标函数 执行当前步骤：.values(status=InterventionStatus.CANCELLED.value)
                )  # 结束函数 delete_session 的参数及返回类型声明并开始函数体
        return [run.id for run in active_runs]  # 返回 [run.id for run in active_runs] 给调用方

    # Runs

    async def create_run(  # 定义异步函数 create_run，封装可被事件循环调度的协程逻辑
        self,  # 为函数 create_run 声明参数 self 及其类型或默认值
        identity: Identity,  # 为函数 create_run 声明参数 identity 及其类型或默认值
        *,  # 为函数 create_run 声明参数 * 及其类型或默认值
        session_id: UUID,  # 为函数 create_run 声明参数 session_id 及其类型或默认值
        query: str,  # 为函数 create_run 声明参数 query 及其类型或默认值
        requested_agent_id: str | None,  # 为函数 create_run 声明参数 requested_agent_id 及其类型或默认值
        idempotency_key: str,  # 为函数 create_run 声明参数 idempotency_key 及其类型或默认值
        trace_id: str | None,  # 为函数 create_run 声明参数 trace_id 及其类型或默认值
        traceparent: str | None,  # 为函数 create_run 声明参数 traceparent 及其类型或默认值
        max_user_active: int,  # 为函数 create_run 声明参数 max_user_active 及其类型或默认值
        max_tenant_active: int,  # 为函数 create_run 声明参数 max_tenant_active 及其类型或默认值
        max_queue_depth: int,  # 为函数 create_run 声明参数 max_queue_depth 及其类型或默认值
    ) -> tuple[RunRecord, bool]:  # 结束 create_run 的参数列表并声明返回类型
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            session_row = await session.get(  # 等待 get 完成，并将其结果保存到 session_row
                HarnessSessionRow, session_id, with_for_update=True  # 在函数 create_run 中执行表达式 HarnessSessionRow, session_id, with_for_update=True，推进当前业务流程
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            if (  # 判断分支条件：if (
                not session_row  # 在函数 create_run 中执行表达式 not session_row，推进当前业务流程
                or session_row.status != "active"  # 在函数 create_run 中执行表达式 or session_row.status != "active"，推进当前业务流程
                or session_row.redacted_at is not None  # 在函数 create_run 中执行表达式 or session_row.redacted_at is not None，推进当前业务流程
            ):  # 结束 create_run 的参数列表并声明返回类型
                raise NotFoundError("session", str(session_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("session", str(session_id))
            if session_row.tenant_id != identity.tenant_id:  # 判断分支条件：if session_row.tenant_id != identity.tenant_id:
                raise ForbiddenError()  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError()
            if (  # 判断分支条件：if (
                session_row.user_id != identity.user_id  # 在函数 create_run 中执行表达式 session_row.user_id != identity.user_id，推进当前业务流程
                and not identity.has_role("agent:admin")  # 调用 目标函数 执行当前步骤：and not identity.has_role("agent:admin")
            ):  # 结束 create_run 的参数列表并声明返回类型
                raise ForbiddenError()  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError()

            existing = await session.scalar(  # 等待 scalar 完成，并将其结果保存到 existing
                select(RunRow).where(  # 调用 select 执行当前步骤：select(RunRow).where(
                    RunRow.tenant_id == identity.tenant_id,  # 继续向上一处调用或声明传入 RunRow.tenant_id == identity.tenant_id
                    RunRow.session_id == session_id,  # 继续向上一处调用或声明传入 RunRow.session_id == session_id
                    RunRow.idempotency_key == idempotency_key,  # 继续向上一处调用或声明传入 RunRow.idempotency_key == idempotency_key
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            if existing:  # 判断分支条件：if existing:
                if (  # 判断分支条件：if (
                    existing.query != query  # 在函数 create_run 中执行表达式 existing.query != query，推进当前业务流程
                    or existing.requested_agent_id != requested_agent_id  # 在函数 create_run 中执行表达式 or existing.requested_agent_id != requested_agent_id，推进当前业务流程
                ):  # 结束 create_run 的参数列表并声明返回类型
                    raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                        "IDEMPOTENCY_MISMATCH",  # 继续向上一处调用或声明传入 "IDEMPOTENCY_MISMATCH"
                        "idempotency key was already used with a different request",  # 继续向上一处调用或声明传入 "idempotency key was already used with a different request"
                    )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
                return _run_record(existing), False  # 返回 _run_record(existing), False 给调用方

            active_in_session = await session.scalar(  # 等待 scalar 完成，并将其结果保存到 active_in_session
                select(func.count(RunRow.id)).where(  # 调用 select 执行当前步骤：select(func.count(RunRow.id)).where(
                    RunRow.session_id == session_id,  # 继续向上一处调用或声明传入 RunRow.session_id == session_id
                    RunRow.status.in_(ACTIVE_RUN_STATUSES),  # 继续向上一处调用或声明传入 RunRow.status.in_(ACTIVE_RUN_STATUSES)
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            if active_in_session:  # 判断分支条件：if active_in_session:
                raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                    "ACTIVE_RUN_EXISTS",  # 继续向上一处调用或声明传入 "ACTIVE_RUN_EXISTS"
                    "the session already has an active run",  # 继续向上一处调用或声明传入 "the session already has an active run"
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体

            active_for_user = await session.scalar(  # 等待 scalar 完成，并将其结果保存到 active_for_user
                select(func.count(RunRow.id)).where(  # 调用 select 执行当前步骤：select(func.count(RunRow.id)).where(
                    RunRow.tenant_id == identity.tenant_id,  # 继续向上一处调用或声明传入 RunRow.tenant_id == identity.tenant_id
                    RunRow.user_id == identity.user_id,  # 继续向上一处调用或声明传入 RunRow.user_id == identity.user_id
                    RunRow.status.in_(ACTIVE_RUN_STATUSES),  # 继续向上一处调用或声明传入 RunRow.status.in_(ACTIVE_RUN_STATUSES)
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            if (active_for_user or 0) >= max_user_active:  # 判断分支条件：if (active_for_user or 0) >= max_user_active:
                raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
                    "USER_RUN_LIMIT",  # 继续向上一处调用或声明传入 "USER_RUN_LIMIT"
                    "the user has reached the active run limit",  # 继续向上一处调用或声明传入 "the user has reached the active run limit"
                    status_code=429,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            active_for_tenant = await session.scalar(  # 等待 scalar 完成，并将其结果保存到 active_for_tenant
                select(func.count(RunRow.id)).where(  # 调用 select 执行当前步骤：select(func.count(RunRow.id)).where(
                    RunRow.tenant_id == identity.tenant_id,  # 继续向上一处调用或声明传入 RunRow.tenant_id == identity.tenant_id
                    RunRow.status.in_(ACTIVE_RUN_STATUSES),  # 继续向上一处调用或声明传入 RunRow.status.in_(ACTIVE_RUN_STATUSES)
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            if (active_for_tenant or 0) >= max_tenant_active:  # 判断分支条件：if (active_for_tenant or 0) >= max_tenant_active:
                raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
                    "TENANT_RUN_LIMIT",  # 继续向上一处调用或声明传入 "TENANT_RUN_LIMIT"
                    "the tenant has reached the active run limit",  # 继续向上一处调用或声明传入 "the tenant has reached the active run limit"
                    status_code=429,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            queued = await session.scalar(  # 等待 scalar 完成，并将其结果保存到 queued
                select(func.count(RunJobRow.id)).where(  # 调用 select 执行当前步骤：select(func.count(RunJobRow.id)).where(
                    RunJobRow.status == JobStatus.QUEUED.value  # 在函数 create_run 中执行表达式 RunJobRow.status == JobStatus.QUEUED.value，推进当前业务流程
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            if (queued or 0) >= max_queue_depth:  # 判断分支条件：if (queued or 0) >= max_queue_depth:
                raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
                    code="QUEUE_FULL",  # 为 AppError 设置关键字参数 code，传入当前行给出的值
                    message="the execution queue is full",  # 为 AppError 设置关键字参数 message，传入当前行给出的值
                    status_code=503,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
                    retryable=True,  # 为 AppError 设置关键字参数 retryable，传入当前行给出的值
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体

            run_id = uuid4()  # 计算 uuid4() 并保存到变量 run_id
            run = RunRow(  # 调用 RunRow 构造结果并保存到 run
                id=run_id,  # 为 RunRow 设置关键字参数 id，传入当前行给出的值
                session_id=session_id,  # 为 RunRow 设置关键字参数 session_id，传入当前行给出的值
                tenant_id=identity.tenant_id,  # 为 RunRow 设置关键字参数 tenant_id，传入当前行给出的值
                user_id=identity.user_id,  # 为 RunRow 设置关键字参数 user_id，传入当前行给出的值
                query=query,  # 为 RunRow 设置关键字参数 query，传入当前行给出的值
                status=RunStatus.QUEUED.value,  # 为 RunRow 设置关键字参数 status，传入当前行给出的值
                requested_agent_id=requested_agent_id,  # 为 RunRow 设置关键字参数 requested_agent_id，传入当前行给出的值
                trace_id=trace_id,  # 为 RunRow 设置关键字参数 trace_id，传入当前行给出的值
                traceparent=traceparent,  # 为 RunRow 设置关键字参数 traceparent，传入当前行给出的值
                idempotency_key=idempotency_key,  # 为 RunRow 设置关键字参数 idempotency_key，传入当前行给出的值
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            session.add(run)  # 调用 add 执行当前步骤：session.add(run)
            session.add(  # 调用 add 执行当前步骤：session.add(
                RunJobRow(  # 调用 RunJobRow 执行当前步骤：RunJobRow(
                    run_id=run_id,  # 为 RunJobRow 设置关键字参数 run_id，传入当前行给出的值
                    job_type=JobType.START.value,  # 为 RunJobRow 设置关键字参数 job_type，传入当前行给出的值
                    dedupe_key=f"start:{run_id}",  # 为 RunJobRow 设置关键字参数 dedupe_key，传入当前行给出的值
                    traceparent=traceparent,  # 为 RunJobRow 设置关键字参数 traceparent，传入当前行给出的值
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            session.add(  # 调用 add 执行当前步骤：session.add(
                SessionMessageRow(  # 调用 SessionMessageRow 执行当前步骤：SessionMessageRow(
                    session_id=session_id,  # 为 SessionMessageRow 设置关键字参数 session_id，传入当前行给出的值
                    run_id=run_id,  # 为 SessionMessageRow 设置关键字参数 run_id，传入当前行给出的值
                    role="user",  # 为 SessionMessageRow 设置关键字参数 role，传入当前行给出的值
                    content=query,  # 为 SessionMessageRow 设置关键字参数 content，传入当前行给出的值
                    metadata_json={"requested_agent_id": requested_agent_id},  # 为 SessionMessageRow 设置关键字参数 metadata_json，传入当前行给出的值
                )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                await session.flush()  # 等待异步操作完成并取得结果：session.flush()
            except IntegrityError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except IntegrityError as exc:
                raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                    "RUN_CREATE_CONFLICT", "the run could not be created"  # 在函数 create_run 中执行表达式 "RUN_CREATE_CONFLICT", "the run could not be created"，推进当前业务流程
                ) from exc  # 在函数 create_run 中执行表达式 ) from exc，推进当前业务流程
            record = _run_record(run)  # 计算 _run_record(run) 并保存到变量 record
        return record, True  # 返回 record, True 给调用方

    async def get_run(  # 定义异步函数 get_run，封装可被事件循环调度的协程逻辑
        self, identity: Identity, run_id: UUID, *, allow_tenant_admin: bool = False  # 为函数 get_run 声明参数 self, identity 及其类型或默认值
    ) -> RunRecord:  # 结束 get_run 的参数列表并声明返回类型
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            row = await session.get(RunRow, run_id)  # 等待 get 完成，并将其结果保存到 row
            if not row:  # 判断分支条件：if not row:
                raise NotFoundError("run", str(run_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("run", str(run_id))
            if row.tenant_id != identity.tenant_id:  # 判断分支条件：if row.tenant_id != identity.tenant_id:
                raise ForbiddenError()  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError()
            if (  # 判断分支条件：if (
                row.user_id != identity.user_id  # 在函数 get_run 中执行表达式 row.user_id != identity.user_id，推进当前业务流程
                and not (  # 调用 目标函数 执行当前步骤：and not (
                    allow_tenant_admin  # 在函数 get_run 中执行表达式 allow_tenant_admin，推进当前业务流程
                    and (  # 调用 and 执行当前步骤：and (
                        identity.has_role("agent:admin")  # 调用 has_role 执行当前步骤：identity.has_role("agent:admin")
                        or identity.has_role("agent:approver")  # 调用 目标函数 执行当前步骤：or identity.has_role("agent:approver")
                    )  # 结束函数 get_run 的参数及返回类型声明并开始函数体
                )  # 结束函数 get_run 的参数及返回类型声明并开始函数体
            ):  # 结束 get_run 的参数列表并声明返回类型
                raise ForbiddenError()  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError()
            return _run_record(row)  # 返回 _run_record(row) 给调用方

    async def get_run_internal(  # 定义异步函数 get_run_internal，封装可被事件循环调度的协程逻辑
        self, run_id: UUID, *, session: AsyncSession | None = None  # 为函数 get_run_internal 声明参数 self, run_id 及其类型或默认值
    ) -> RunRecord:  # 结束 get_run_internal 的参数列表并声明返回类型
        if session is not None:  # 判断分支条件：if session is not None:
            row = await session.get(RunRow, run_id)  # 等待 get 完成，并将其结果保存到 row
            if not row:  # 判断分支条件：if not row:
                raise NotFoundError("run", str(run_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("run", str(run_id))
            return _run_record(row)  # 返回 _run_record(row) 给调用方
        async with self.session_factory() as db:  # 进入受管理的上下文 async with self.session_factory() as db:，确保资源正确获取与释放
            return await self.get_run_internal(run_id, session=db)  # 返回 await self.get_run_internal(run_id, session=db) 给调用方

    async def list_session_runs(  # 定义异步函数 list_session_runs，封装可被事件循环调度的协程逻辑
        self, identity: Identity, session_id: UUID, *, limit: int = 20  # 为函数 list_session_runs 声明参数 self, identity 及其类型或默认值
    ) -> list[RunRecord]:  # 结束 list_session_runs 的参数列表并声明返回类型
        await self.get_session(identity, session_id)  # 等待异步操作完成并取得结果：self.get_session(identity, session_id)
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            rows = (  # 调用 目标函数 构造结果并保存到 rows
                await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                    select(RunRow)  # 调用 select 执行当前步骤：select(RunRow)
                    .where(RunRow.session_id == session_id)  # 调用 目标函数 执行当前步骤：.where(RunRow.session_id == session_id)
                    .order_by(RunRow.created_at.desc())  # 调用 目标函数 执行当前步骤：.order_by(RunRow.created_at.desc())
                    .limit(limit)  # 调用 目标函数 执行当前步骤：.limit(limit)
                )  # 结束函数 list_session_runs 的参数及返回类型声明并开始函数体
            ).all()  # 调用 目标函数 执行当前步骤：).all()
        return [_run_record(row) for row in rows]  # 返回 [_run_record(row) for row in rows] 给调用方

    async def mark_run_running(self, run_id: UUID) -> None:  # 定义异步函数 mark_run_running，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                update(RunRow)  # 调用 update 执行当前步骤：update(RunRow)
                .where(  # 调用 目标函数 执行当前步骤：.where(
                    RunRow.id == run_id,  # 继续向上一处调用或声明传入 RunRow.id == run_id
                    RunRow.status.in_(  # 调用 in_ 执行当前步骤：RunRow.status.in_(
                        (RunStatus.QUEUED.value, RunStatus.RUNNING.value)  # 调用 目标函数 执行当前步骤：(RunStatus.QUEUED.value, RunStatus.RUNNING.value)
                    ),  # 结束函数 mark_run_running 的参数及返回类型声明并开始函数体
                )  # 结束函数 mark_run_running 的参数及返回类型声明并开始函数体
                .values(  # 调用 目标函数 执行当前步骤：.values(
                    status=RunStatus.RUNNING.value,  # 为 values 设置关键字参数 status，传入当前行给出的值
                    started_at=func.coalesce(RunRow.started_at, func.now()),  # 为 func.coalesce 设置关键字参数 started_at，传入当前行给出的值
                    updated_at=func.now(),  # 为 func.now 设置关键字参数 updated_at，传入当前行给出的值
                    version=RunRow.version + 1,  # 为 values 设置关键字参数 version，传入当前行给出的值
                )  # 结束函数 mark_run_running 的参数及返回类型声明并开始函数体
            )  # 结束函数 mark_run_running 的参数及返回类型声明并开始函数体

    async def set_run_route(  # 定义异步函数 set_run_route，封装可被事件循环调度的协程逻辑
        self,  # 为函数 set_run_route 声明参数 self 及其类型或默认值
        run_id: UUID,  # 为函数 set_run_route 声明参数 run_id 及其类型或默认值
        *,  # 为函数 set_run_route 声明参数 * 及其类型或默认值
        selected_agent_id: str,  # 为函数 set_run_route 声明参数 selected_agent_id 及其类型或默认值
        agent_version: str,  # 为函数 set_run_route 声明参数 agent_version 及其类型或默认值
        route_mode: RouteMode,  # 为函数 set_run_route 声明参数 route_mode 及其类型或默认值
        confidence: float | None,  # 为函数 set_run_route 声明参数 confidence 及其类型或默认值
        route: dict[str, Any],  # 为函数 set_run_route 声明参数 route 及其类型或默认值
    ) -> None:  # 结束 set_run_route 的参数列表并声明返回类型
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                update(RunRow)  # 调用 update 执行当前步骤：update(RunRow)
                .where(RunRow.id == run_id)  # 调用 目标函数 执行当前步骤：.where(RunRow.id == run_id)
                .values(  # 调用 目标函数 执行当前步骤：.values(
                    selected_agent_id=selected_agent_id,  # 为 values 设置关键字参数 selected_agent_id，传入当前行给出的值
                    agent_version=agent_version,  # 为 values 设置关键字参数 agent_version，传入当前行给出的值
                    route_mode=route_mode.value,  # 为 values 设置关键字参数 route_mode，传入当前行给出的值
                    route_confidence=confidence,  # 为 values 设置关键字参数 route_confidence，传入当前行给出的值
                    route_json=route,  # 为 values 设置关键字参数 route_json，传入当前行给出的值
                    updated_at=func.now(),  # 为 func.now 设置关键字参数 updated_at，传入当前行给出的值
                    version=RunRow.version + 1,  # 为 values 设置关键字参数 version，传入当前行给出的值
                )  # 结束函数 set_run_route 的参数及返回类型声明并开始函数体
            )  # 结束函数 set_run_route 的参数及返回类型声明并开始函数体

    async def set_run_budget(self, run_id: UUID, budget: dict[str, Any]) -> None:  # 定义异步函数 set_run_budget，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                update(RunRow)  # 调用 update 执行当前步骤：update(RunRow)
                .where(RunRow.id == run_id)  # 调用 目标函数 执行当前步骤：.where(RunRow.id == run_id)
                .values(budget_json=budget, updated_at=func.now())  # 调用 目标函数 执行当前步骤：.values(budget_json=budget, updated_at=func.now())
            )  # 结束函数 set_run_budget 的参数及返回类型声明并开始函数体

    async def complete_run(  # 定义异步函数 complete_run，封装可被事件循环调度的协程逻辑
        self,  # 为函数 complete_run 声明参数 self 及其类型或默认值
        run_id: UUID,  # 为函数 complete_run 声明参数 run_id 及其类型或默认值
        *,  # 为函数 complete_run 声明参数 * 及其类型或默认值
        output: dict[str, Any],  # 为函数 complete_run 声明参数 output 及其类型或默认值
        budget: dict[str, Any],  # 为函数 complete_run 声明参数 budget 及其类型或默认值
    ) -> RunRecord:  # 结束 complete_run 的参数列表并声明返回类型
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            row = await session.get(RunRow, run_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 row
            if not row:  # 判断分支条件：if not row:
                raise NotFoundError("run", str(run_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("run", str(run_id))
            if row.status in TERMINAL_RUN_STATUSES:  # 判断分支条件：if row.status in TERMINAL_RUN_STATUSES:
                return _run_record(row)  # 返回 _run_record(row) 给调用方
            row.status = RunStatus.COMPLETED.value  # 计算 RunStatus.COMPLETED.value 并保存到变量 row.status
            row.output_json = output  # 计算 output 并保存到变量 row.output_json
            row.budget_json = budget  # 计算 budget 并保存到变量 row.budget_json
            row.completed_at = utc_now()  # 计算 utc_now() 并保存到变量 row.completed_at
            row.version += 1  # 计算 1 并保存到变量 row.version +
            if output.get("text"):  # 判断分支条件：if output.get("text"):
                session.add(  # 调用 add 执行当前步骤：session.add(
                    SessionMessageRow(  # 调用 SessionMessageRow 执行当前步骤：SessionMessageRow(
                        session_id=row.session_id,  # 为 SessionMessageRow 设置关键字参数 session_id，传入当前行给出的值
                        run_id=row.id,  # 为 SessionMessageRow 设置关键字参数 run_id，传入当前行给出的值
                        role="assistant",  # 为 SessionMessageRow 设置关键字参数 role，传入当前行给出的值
                        content=str(output["text"]),  # 为 str 设置关键字参数 content，传入当前行给出的值
                        metadata_json={  # 为 SessionMessageRow 设置关键字参数 metadata_json，传入当前行给出的值
                            "agent_id": row.selected_agent_id,  # 为多行字典定义键 "agent_id" 及其对应值
                            "agent_version": row.agent_version,  # 为多行字典定义键 "agent_version" 及其对应值
                        },  # 结束上一处多行结构，保持表达式边界清晰
                    )  # 结束函数 complete_run 的参数及返回类型声明并开始函数体
                )  # 结束函数 complete_run 的参数及返回类型声明并开始函数体
            await session.flush()  # 等待异步操作完成并取得结果：session.flush()
            return _run_record(row)  # 返回 _run_record(row) 给调用方

    async def finish_run(  # 定义异步函数 finish_run，封装可被事件循环调度的协程逻辑
        self,  # 为函数 finish_run 声明参数 self 及其类型或默认值
        run_id: UUID,  # 为函数 finish_run 声明参数 run_id 及其类型或默认值
        status: RunStatus,  # 为函数 finish_run 声明参数 status 及其类型或默认值
        *,  # 为函数 finish_run 声明参数 * 及其类型或默认值
        error_code: str | None = None,  # 为函数 finish_run 声明参数 error_code 及其类型或默认值
        error_message: str | None = None,  # 为函数 finish_run 声明参数 error_message 及其类型或默认值
        budget: dict[str, Any] | None = None,  # 为函数 finish_run 声明参数 budget 及其类型或默认值
    ) -> RunRecord:  # 结束 finish_run 的参数列表并声明返回类型
        if status not in TERMINAL_RUN_STATUSES:  # 判断分支条件：if status not in TERMINAL_RUN_STATUSES:
            raise ValueError("finish_run requires a terminal status")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("finish_run requires a terminal status")
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            row = await session.get(RunRow, run_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 row
            if not row:  # 判断分支条件：if not row:
                raise NotFoundError("run", str(run_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("run", str(run_id))
            if row.status in TERMINAL_RUN_STATUSES:  # 判断分支条件：if row.status in TERMINAL_RUN_STATUSES:
                return _run_record(row)  # 返回 _run_record(row) 给调用方
            row.status = status.value  # 计算 status.value 并保存到变量 row.status
            row.error_code = error_code  # 计算 error_code 并保存到变量 row.error_code
            row.error_message = error_message[:2000] if error_message else None  # 计算 error_message[:2000] if error_message else None 并保存到变量 row.error_message
            row.completed_at = utc_now()  # 计算 utc_now() 并保存到变量 row.completed_at
            if budget is not None:  # 判断分支条件：if budget is not None:
                row.budget_json = budget  # 计算 budget 并保存到变量 row.budget_json
            row.version += 1  # 计算 1 并保存到变量 row.version +
            await session.flush()  # 等待异步操作完成并取得结果：session.flush()
            return _run_record(row)  # 返回 _run_record(row) 给调用方

    async def cancel_run(self, identity: Identity, run_id: UUID) -> RunRecord:  # 定义异步函数 cancel_run，封装可被事件循环调度的协程逻辑
        await self.get_run(identity, run_id)  # 等待异步操作完成并取得结果：self.get_run(identity, run_id)
        now = utc_now()  # 计算 utc_now() 并保存到变量 now
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            row = await session.get(RunRow, run_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 row
            if not row:  # 判断分支条件：if not row:
                raise NotFoundError("run", str(run_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("run", str(run_id))
            if row.status in TERMINAL_RUN_STATUSES:  # 判断分支条件：if row.status in TERMINAL_RUN_STATUSES:
                return _run_record(row)  # 返回 _run_record(row) 给调用方
            row.status = RunStatus.CANCELLED.value  # 计算 RunStatus.CANCELLED.value 并保存到变量 row.status
            row.completed_at = now  # 计算 now 并保存到变量 row.completed_at
            row.error_code = "CANCELLED"  # 计算 "CANCELLED" 并保存到变量 row.error_code
            row.error_message = "run was cancelled by the user"  # 计算 "run was cancelled by the user" 并保存到变量 row.error_message
            row.version += 1  # 计算 1 并保存到变量 row.version +
            await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                update(RunJobRow)  # 调用 update 执行当前步骤：update(RunJobRow)
                .where(  # 调用 目标函数 执行当前步骤：.where(
                    RunJobRow.run_id == run_id,  # 继续向上一处调用或声明传入 RunJobRow.run_id == run_id
                    RunJobRow.status.in_(  # 调用 in_ 执行当前步骤：RunJobRow.status.in_(
                        (JobStatus.QUEUED.value, JobStatus.LEASED.value)  # 调用 目标函数 执行当前步骤：(JobStatus.QUEUED.value, JobStatus.LEASED.value)
                    ),  # 结束函数 cancel_run 的参数及返回类型声明并开始函数体
                )  # 结束函数 cancel_run 的参数及返回类型声明并开始函数体
                .values(status=JobStatus.CANCELLED.value, updated_at=now)  # 调用 目标函数 执行当前步骤：.values(status=JobStatus.CANCELLED.value, updated_at=now)
            )  # 结束函数 cancel_run 的参数及返回类型声明并开始函数体
            await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                update(HumanInterventionRow)  # 调用 update 执行当前步骤：update(HumanInterventionRow)
                .where(  # 调用 目标函数 执行当前步骤：.where(
                    HumanInterventionRow.run_id == run_id,  # 继续向上一处调用或声明传入 HumanInterventionRow.run_id == run_id
                    HumanInterventionRow.status == InterventionStatus.PENDING.value,  # 继续向上一处调用或声明传入 HumanInterventionRow.status == InterventionStatus.PENDING.value
                )  # 结束函数 cancel_run 的参数及返回类型声明并开始函数体
                .values(status=InterventionStatus.CANCELLED.value)  # 调用 目标函数 执行当前步骤：.values(status=InterventionStatus.CANCELLED.value)
            )  # 结束函数 cancel_run 的参数及返回类型声明并开始函数体
            await session.flush()  # 等待异步操作完成并取得结果：session.flush()
            return _run_record(row)  # 返回 _run_record(row) 给调用方

    # Events

    async def append_event(  # 定义异步函数 append_event，封装可被事件循环调度的协程逻辑
        self,  # 为函数 append_event 声明参数 self 及其类型或默认值
        run_id: UUID,  # 为函数 append_event 声明参数 run_id 及其类型或默认值
        *,  # 为函数 append_event 声明参数 * 及其类型或默认值
        event_type: str,  # 为函数 append_event 声明参数 event_type 及其类型或默认值
        payload: dict[str, Any],  # 为函数 append_event 声明参数 payload 及其类型或默认值
        trace_id: str | None,  # 为函数 append_event 声明参数 trace_id 及其类型或默认值
    ) -> EventRecord:  # 结束 append_event 的参数列表并声明返回类型
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            run = await session.get(RunRow, run_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 run
            if not run:  # 判断分支条件：if not run:
                raise NotFoundError("run", str(run_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("run", str(run_id))
            current_seq = await session.scalar(  # 等待 scalar 完成，并将其结果保存到 current_seq
                select(func.coalesce(func.max(RunEventRow.seq), 0)).where(  # 调用 select 执行当前步骤：select(func.coalesce(func.max(RunEventRow.seq), 0)).where(
                    RunEventRow.run_id == run_id  # 在函数 append_event 中执行表达式 RunEventRow.run_id == run_id，推进当前业务流程
                )  # 结束函数 append_event 的参数及返回类型声明并开始函数体
            )  # 结束函数 append_event 的参数及返回类型声明并开始函数体
            row = RunEventRow(  # 调用 RunEventRow 构造结果并保存到 row
                run_id=run_id,  # 为 RunEventRow 设置关键字参数 run_id，传入当前行给出的值
                seq=int(current_seq or 0) + 1,  # 为 int 设置关键字参数 seq，传入当前行给出的值
                trace_id=trace_id,  # 为 RunEventRow 设置关键字参数 trace_id，传入当前行给出的值
                event_type=event_type,  # 为 RunEventRow 设置关键字参数 event_type，传入当前行给出的值
                payload_json=payload,  # 为 RunEventRow 设置关键字参数 payload_json，传入当前行给出的值
            )  # 结束函数 append_event 的参数及返回类型声明并开始函数体
            session.add(row)  # 调用 add 执行当前步骤：session.add(row)
            await session.flush()  # 等待异步操作完成并取得结果：session.flush()
            return _event_record(row)  # 返回 _event_record(row) 给调用方

    async def list_events(  # 定义异步函数 list_events，封装可被事件循环调度的协程逻辑
        self, run_id: UUID, *, after_seq: int = 0, limit: int = 500  # 为函数 list_events 声明参数 self, run_id 及其类型或默认值
    ) -> list[EventRecord]:  # 结束 list_events 的参数列表并声明返回类型
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            rows = (  # 调用 目标函数 构造结果并保存到 rows
                await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                    select(RunEventRow)  # 调用 select 执行当前步骤：select(RunEventRow)
                    .where(  # 调用 目标函数 执行当前步骤：.where(
                        RunEventRow.run_id == run_id,  # 继续向上一处调用或声明传入 RunEventRow.run_id == run_id
                        RunEventRow.seq > after_seq,  # 继续向上一处调用或声明传入 RunEventRow.seq > after_seq
                    )  # 结束函数 list_events 的参数及返回类型声明并开始函数体
                    .order_by(RunEventRow.seq.asc())  # 调用 目标函数 执行当前步骤：.order_by(RunEventRow.seq.asc())
                    .limit(limit)  # 调用 目标函数 执行当前步骤：.limit(limit)
                )  # 结束函数 list_events 的参数及返回类型声明并开始函数体
            ).all()  # 调用 目标函数 执行当前步骤：).all()
        return [_event_record(row) for row in rows]  # 返回 [_event_record(row) for row in rows] 给调用方

    # Job queue

    async def claim_next_job(  # 定义异步函数 claim_next_job，封装可被事件循环调度的协程逻辑
        self,  # 为函数 claim_next_job 声明参数 self 及其类型或默认值
        *,  # 为函数 claim_next_job 声明参数 * 及其类型或默认值
        worker_id: str,  # 为函数 claim_next_job 声明参数 worker_id 及其类型或默认值
        lease_seconds: int,  # 为函数 claim_next_job 声明参数 lease_seconds 及其类型或默认值
        max_attempts: int,  # 为函数 claim_next_job 声明参数 max_attempts 及其类型或默认值
    ) -> JobRecord | None:  # 结束 claim_next_job 的参数列表并声明返回类型
        query = text(  # 将下方参数化 SQL 包装成 SQLAlchemy TextClause 供后续执行
            f"""
            WITH candidate AS (
                SELECT id
                FROM {HARNESS_SCHEMA}.run_jobs
                WHERE (
                    (status = 'queued' AND available_at <= now())
                    OR (
                        status = 'leased'
                        AND lease_until IS NOT NULL
                        AND lease_until < now()
                    )
                )
                  AND attempts < :max_attempts
                ORDER BY available_at ASC, created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE {HARNESS_SCHEMA}.run_jobs AS jobs
            SET status = 'leased',
                lease_owner = :worker_id,
                lease_until = now() + (:lease_seconds * interval '1 second'),
                attempts = jobs.attempts + 1,
                updated_at = now()
            FROM candidate
            WHERE jobs.id = candidate.id
            RETURNING jobs.id, jobs.run_id, jobs.job_type, jobs.status,
                      jobs.payload_json, jobs.traceparent, jobs.available_at,
                      jobs.lease_owner, jobs.lease_until, jobs.attempts
            """
        )  # 结束 text 调用参数，得到完整表达式结果
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            result = await session.execute(  # 等待 execute 完成，并将其结果保存到 result
                query,  # 继续向上一处调用或声明传入 query
                {  # 在函数 claim_next_job 中执行表达式 {，推进当前业务流程
                    "worker_id": worker_id,  # 为多行字典定义键 "worker_id" 及其对应值
                    "lease_seconds": lease_seconds,  # 为多行字典定义键 "lease_seconds" 及其对应值
                    "max_attempts": max_attempts,  # 为多行字典定义键 "max_attempts" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束函数 claim_next_job 的参数及返回类型声明并开始函数体
            row = result.mappings().one_or_none()  # 计算 result.mappings().one_or_none() 并保存到变量 row
        return _job_mapping_record(row) if row else None  # 返回 _job_mapping_record(row) if row else None 给调用方

    async def heartbeat_job(  # 定义异步函数 heartbeat_job，封装可被事件循环调度的协程逻辑
        self, job_id: UUID, worker_id: str, lease_seconds: int  # 为函数 heartbeat_job 声明参数 self, job_id 及其类型或默认值
    ) -> bool:  # 结束 heartbeat_job 的参数列表并声明返回类型
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            result = await session.execute(  # 等待 execute 完成，并将其结果保存到 result
                update(RunJobRow)  # 调用 update 执行当前步骤：update(RunJobRow)
                .where(  # 调用 目标函数 执行当前步骤：.where(
                    RunJobRow.id == job_id,  # 继续向上一处调用或声明传入 RunJobRow.id == job_id
                    RunJobRow.status == JobStatus.LEASED.value,  # 继续向上一处调用或声明传入 RunJobRow.status == JobStatus.LEASED.value
                    RunJobRow.lease_owner == worker_id,  # 继续向上一处调用或声明传入 RunJobRow.lease_owner == worker_id
                )  # 结束函数 heartbeat_job 的参数及返回类型声明并开始函数体
                .values(  # 调用 目标函数 执行当前步骤：.values(
                    lease_until=func.now() + timedelta(seconds=lease_seconds),  # 为 func.now 设置关键字参数 lease_until，传入当前行给出的值
                    updated_at=func.now(),  # 为 func.now 设置关键字参数 updated_at，传入当前行给出的值
                )  # 结束函数 heartbeat_job 的参数及返回类型声明并开始函数体
            )  # 结束函数 heartbeat_job 的参数及返回类型声明并开始函数体
            return bool(result.rowcount)  # 返回 bool(result.rowcount) 给调用方

    async def complete_job(self, job_id: UUID, worker_id: str) -> None:  # 定义异步函数 complete_job，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                update(RunJobRow)  # 调用 update 执行当前步骤：update(RunJobRow)
                .where(  # 调用 目标函数 执行当前步骤：.where(
                    RunJobRow.id == job_id,  # 继续向上一处调用或声明传入 RunJobRow.id == job_id
                    RunJobRow.status == JobStatus.LEASED.value,  # 继续向上一处调用或声明传入 RunJobRow.status == JobStatus.LEASED.value
                    RunJobRow.lease_owner == worker_id,  # 继续向上一处调用或声明传入 RunJobRow.lease_owner == worker_id
                )  # 结束函数 complete_job 的参数及返回类型声明并开始函数体
                .values(  # 调用 目标函数 执行当前步骤：.values(
                    status=JobStatus.COMPLETED.value,  # 为 values 设置关键字参数 status，传入当前行给出的值
                    lease_owner=None,  # 为 values 设置关键字参数 lease_owner，传入当前行给出的值
                    lease_until=None,  # 为 values 设置关键字参数 lease_until，传入当前行给出的值
                    updated_at=func.now(),  # 为 func.now 设置关键字参数 updated_at，传入当前行给出的值
                )  # 结束函数 complete_job 的参数及返回类型声明并开始函数体
            )  # 结束函数 complete_job 的参数及返回类型声明并开始函数体

    async def fail_job(  # 定义异步函数 fail_job，封装可被事件循环调度的协程逻辑
        self,  # 为函数 fail_job 声明参数 self 及其类型或默认值
        job_id: UUID,  # 为函数 fail_job 声明参数 job_id 及其类型或默认值
        worker_id: str,  # 为函数 fail_job 声明参数 worker_id 及其类型或默认值
        *,  # 为函数 fail_job 声明参数 * 及其类型或默认值
        max_attempts: int,  # 为函数 fail_job 声明参数 max_attempts 及其类型或默认值
        retryable: bool,  # 为函数 fail_job 声明参数 retryable 及其类型或默认值
    ) -> bool:  # 结束 fail_job 的参数列表并声明返回类型
        """Return True when the job was made available for another attempt."""

        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            row = await session.get(RunJobRow, job_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 row
            if not row or row.lease_owner != worker_id:  # 判断分支条件：if not row or row.lease_owner != worker_id:
                return False  # 返回 False 给调用方
            should_retry = retryable and row.attempts < max_attempts  # 计算 retryable and row.attempts < max_attempts 并保存到变量 should_retry
            if should_retry:  # 判断分支条件：if should_retry:
                row.status = JobStatus.QUEUED.value  # 计算 JobStatus.QUEUED.value 并保存到变量 row.status
                row.available_at = utc_now() + timedelta(  # 调用 utc_now 构造结果并保存到 row.available_at
                    seconds=min(2 ** row.attempts, 30)  # 为 min 设置关键字参数 seconds，传入当前行给出的值
                )  # 结束函数 fail_job 的参数及返回类型声明并开始函数体
            else:  # 进入前面条件均不成立时的兜底分支
                row.status = JobStatus.FAILED.value  # 计算 JobStatus.FAILED.value 并保存到变量 row.status
            row.lease_owner = None  # 计算 None 并保存到变量 row.lease_owner
            row.lease_until = None  # 计算 None 并保存到变量 row.lease_until
            row.updated_at = utc_now()  # 计算 utc_now() 并保存到变量 row.updated_at
            return should_retry  # 返回 should_retry 给调用方

    async def release_job(self, job_id: UUID, worker_id: str) -> None:  # 定义异步函数 release_job，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                update(RunJobRow)  # 调用 update 执行当前步骤：update(RunJobRow)
                .where(  # 调用 目标函数 执行当前步骤：.where(
                    RunJobRow.id == job_id,  # 继续向上一处调用或声明传入 RunJobRow.id == job_id
                    RunJobRow.status == JobStatus.LEASED.value,  # 继续向上一处调用或声明传入 RunJobRow.status == JobStatus.LEASED.value
                    RunJobRow.lease_owner == worker_id,  # 继续向上一处调用或声明传入 RunJobRow.lease_owner == worker_id
                )  # 结束函数 release_job 的参数及返回类型声明并开始函数体
                .values(  # 调用 目标函数 执行当前步骤：.values(
                    status=JobStatus.QUEUED.value,  # 为 values 设置关键字参数 status，传入当前行给出的值
                    lease_owner=None,  # 为 values 设置关键字参数 lease_owner，传入当前行给出的值
                    lease_until=None,  # 为 values 设置关键字参数 lease_until，传入当前行给出的值
                    available_at=func.now(),  # 为 func.now 设置关键字参数 available_at，传入当前行给出的值
                    attempts=func.greatest(RunJobRow.attempts - 1, 0),  # 为 func.greatest 设置关键字参数 attempts，传入当前行给出的值
                    updated_at=func.now(),  # 为 func.now 设置关键字参数 updated_at，传入当前行给出的值
                )  # 结束函数 release_job 的参数及返回类型声明并开始函数体
            )  # 结束函数 release_job 的参数及返回类型声明并开始函数体

    async def fail_exhausted_jobs(self, max_attempts: int) -> list[UUID]:  # 定义异步函数 fail_exhausted_jobs，封装可被事件循环调度的协程逻辑
        """Close jobs whose lease or retry budget can no longer make progress."""

        now = utc_now()  # 计算 utc_now() 并保存到变量 now
        failed_run_ids: list[UUID] = []  # 计算 [] 并保存到变量 failed_run_ids
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            rows = (  # 调用 目标函数 构造结果并保存到 rows
                await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                    select(RunJobRow)  # 调用 select 执行当前步骤：select(RunJobRow)
                    .where(  # 调用 目标函数 执行当前步骤：.where(
                        RunJobRow.status.in_(  # 调用 in_ 执行当前步骤：RunJobRow.status.in_(
                            (JobStatus.QUEUED.value, JobStatus.LEASED.value)  # 调用 目标函数 执行当前步骤：(JobStatus.QUEUED.value, JobStatus.LEASED.value)
                        ),  # 结束函数 fail_exhausted_jobs 的参数及返回类型声明并开始函数体
                        RunJobRow.attempts >= max_attempts,  # 继续向上一处调用或声明传入 RunJobRow.attempts >= max_attempts
                        (  # 调用 目标函数 执行当前步骤：(
                            RunJobRow.lease_until.is_(None)  # 调用 is_ 执行当前步骤：RunJobRow.lease_until.is_(None)
                            | (RunJobRow.lease_until < now)  # 调用 目标函数 执行当前步骤：| (RunJobRow.lease_until < now)
                        ),  # 结束函数 fail_exhausted_jobs 的参数及返回类型声明并开始函数体
                    )  # 结束函数 fail_exhausted_jobs 的参数及返回类型声明并开始函数体
                    .with_for_update(skip_locked=True)  # 调用 目标函数 执行当前步骤：.with_for_update(skip_locked=True)
                )  # 结束函数 fail_exhausted_jobs 的参数及返回类型声明并开始函数体
            ).all()  # 调用 目标函数 执行当前步骤：).all()
            for job in rows:  # 按迭代条件执行循环：for job in rows:
                job.status = JobStatus.FAILED.value  # 计算 JobStatus.FAILED.value 并保存到变量 job.status
                job.lease_owner = None  # 计算 None 并保存到变量 job.lease_owner
                job.lease_until = None  # 计算 None 并保存到变量 job.lease_until
                run = await session.get(RunRow, job.run_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 run
                if run and run.status not in {  # 判断分支条件：if run and run.status not in {
                    status.value for status in TERMINAL_RUN_STATUSES  # 在函数 fail_exhausted_jobs 中执行表达式 status.value for status in TERMINAL_RUN_STATUSES，推进当前业务流程
                }:  # 在函数 fail_exhausted_jobs 中执行表达式 }:，推进当前业务流程
                    run.status = RunStatus.FAILED.value  # 计算 RunStatus.FAILED.value 并保存到变量 run.status
                    run.completed_at = now  # 计算 now 并保存到变量 run.completed_at
                    run.error_code = "JOB_ATTEMPTS_EXHAUSTED"  # 计算 "JOB_ATTEMPTS_EXHAUSTED" 并保存到变量 run.error_code
                    run.version += 1  # 计算 1 并保存到变量 run.version +
                    failed_run_ids.append(run.id)  # 调用 append 执行当前步骤：failed_run_ids.append(run.id)
        return failed_run_ids  # 返回 failed_run_ids 给调用方

    # Human interventions

    async def create_intervention(  # 定义异步函数 create_intervention，封装可被事件循环调度的协程逻辑
        self,  # 为函数 create_intervention 声明参数 self 及其类型或默认值
        run_id: UUID,  # 为函数 create_intervention 声明参数 run_id 及其类型或默认值
        *,  # 为函数 create_intervention 声明参数 * 及其类型或默认值
        kind: InterventionKind,  # 为函数 create_intervention 声明参数 kind 及其类型或默认值
        payload: dict[str, Any],  # 为函数 create_intervention 声明参数 payload 及其类型或默认值
        ttl_seconds: int,  # 为函数 create_intervention 声明参数 ttl_seconds 及其类型或默认值
    ) -> InterventionRecord:  # 结束 create_intervention 的参数列表并声明返回类型
        payload_hash = _payload_hash(payload)  # 计算 _payload_hash(payload) 并保存到变量 payload_hash
        expires_at = utc_now() + timedelta(seconds=ttl_seconds)  # 计算 utc_now() + timedelta(seconds=ttl_seconds) 并保存到变量 expires_at
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            run = await session.get(RunRow, run_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 run
            if not run:  # 判断分支条件：if not run:
                raise NotFoundError("run", str(run_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("run", str(run_id))
            existing = await session.scalar(  # 等待 scalar 完成，并将其结果保存到 existing
                select(HumanInterventionRow)  # 调用 select 执行当前步骤：select(HumanInterventionRow)
                .where(  # 调用 目标函数 执行当前步骤：.where(
                    HumanInterventionRow.run_id == run_id,  # 继续向上一处调用或声明传入 HumanInterventionRow.run_id == run_id
                    HumanInterventionRow.kind == kind.value,  # 继续向上一处调用或声明传入 HumanInterventionRow.kind == kind.value
                    HumanInterventionRow.payload_hash == payload_hash,  # 继续向上一处调用或声明传入 HumanInterventionRow.payload_hash == payload_hash
                    HumanInterventionRow.status == InterventionStatus.PENDING.value,  # 继续向上一处调用或声明传入 HumanInterventionRow.status == InterventionStatus.PENDING.value
                )  # 结束函数 create_intervention 的参数及返回类型声明并开始函数体
                .order_by(HumanInterventionRow.requested_at.desc())  # 调用 目标函数 执行当前步骤：.order_by(HumanInterventionRow.requested_at.desc())
            )  # 结束函数 create_intervention 的参数及返回类型声明并开始函数体
            if existing and existing.expires_at > utc_now():  # 判断分支条件：if existing and existing.expires_at > utc_now():
                return _intervention_record(existing)  # 返回 _intervention_record(existing) 给调用方
            row = HumanInterventionRow(  # 调用 HumanInterventionRow 构造结果并保存到 row
                run_id=run_id,  # 为 HumanInterventionRow 设置关键字参数 run_id，传入当前行给出的值
                kind=kind.value,  # 为 HumanInterventionRow 设置关键字参数 kind，传入当前行给出的值
                payload_json=payload,  # 为 HumanInterventionRow 设置关键字参数 payload_json，传入当前行给出的值
                payload_hash=payload_hash,  # 为 HumanInterventionRow 设置关键字参数 payload_hash，传入当前行给出的值
                expires_at=expires_at,  # 为 HumanInterventionRow 设置关键字参数 expires_at，传入当前行给出的值
            )  # 结束函数 create_intervention 的参数及返回类型声明并开始函数体
            session.add(row)  # 调用 add 执行当前步骤：session.add(row)
            run.status = RunStatus.WAITING_HUMAN.value  # 计算 RunStatus.WAITING_HUMAN.value 并保存到变量 run.status
            run.updated_at = utc_now()  # 计算 utc_now() 并保存到变量 run.updated_at
            run.version += 1  # 计算 1 并保存到变量 run.version +
            await session.flush()  # 等待异步操作完成并取得结果：session.flush()
            return _intervention_record(row)  # 返回 _intervention_record(row) 给调用方

    async def get_intervention(  # 定义异步函数 get_intervention，封装可被事件循环调度的协程逻辑
        self, intervention_id: UUID  # 为函数 get_intervention 声明参数 self, intervention_id 及其类型或默认值
    ) -> InterventionRecord:  # 结束 get_intervention 的参数列表并声明返回类型
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            row = await session.get(HumanInterventionRow, intervention_id)  # 等待 get 完成，并将其结果保存到 row
            if not row:  # 判断分支条件：if not row:
                raise NotFoundError("intervention", str(intervention_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("intervention", str(intervention_id))
            return _intervention_record(row)  # 返回 _intervention_record(row) 给调用方

    async def list_interventions(self, run_id: UUID) -> list[InterventionRecord]:  # 定义异步函数 list_interventions，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            rows = (  # 调用 目标函数 构造结果并保存到 rows
                await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                    select(HumanInterventionRow)  # 调用 select 执行当前步骤：select(HumanInterventionRow)
                    .where(HumanInterventionRow.run_id == run_id)  # 调用 目标函数 执行当前步骤：.where(HumanInterventionRow.run_id == run_id)
                    .order_by(HumanInterventionRow.requested_at.asc())  # 调用 目标函数 执行当前步骤：.order_by(HumanInterventionRow.requested_at.asc())
                )  # 结束函数 list_interventions 的参数及返回类型声明并开始函数体
            ).all()  # 调用 目标函数 执行当前步骤：).all()
        return [_intervention_record(row) for row in rows]  # 返回 [_intervention_record(row) for row in rows] 给调用方

    async def respond_to_intervention(  # 定义异步函数 respond_to_intervention，封装可被事件循环调度的协程逻辑
        self,  # 为函数 respond_to_intervention 声明参数 self 及其类型或默认值
        intervention_id: UUID,  # 为函数 respond_to_intervention 声明参数 intervention_id 及其类型或默认值
        *,  # 为函数 respond_to_intervention 声明参数 * 及其类型或默认值
        actor: Identity,  # 为函数 respond_to_intervention 声明参数 actor 及其类型或默认值
        expected_version: int,  # 为函数 respond_to_intervention 声明参数 expected_version 及其类型或默认值
        action: DecisionAction,  # 为函数 respond_to_intervention 声明参数 action 及其类型或默认值
        decision: dict[str, Any],  # 为函数 respond_to_intervention 声明参数 decision 及其类型或默认值
        traceparent: str | None,  # 为函数 respond_to_intervention 声明参数 traceparent 及其类型或默认值
    ) -> InterventionRecord:  # 结束 respond_to_intervention 的参数列表并声明返回类型
        now = utc_now()  # 计算 utc_now() 并保存到变量 now
        expired = False  # 计算 False 并保存到变量 expired
        record: InterventionRecord | None = None  # 计算 None 并保存到变量 record
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            row = await session.get(  # 等待 get 完成，并将其结果保存到 row
                HumanInterventionRow, intervention_id, with_for_update=True  # 在函数 respond_to_intervention 中执行表达式 HumanInterventionRow, intervention_id, with_for_update=True，推进当前业务流程
            )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
            if not row:  # 判断分支条件：if not row:
                raise NotFoundError("intervention", str(intervention_id))  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("intervention", str(intervention_id))
            run = await session.get(RunRow, row.run_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 run
            if not run or run.tenant_id != actor.tenant_id:  # 判断分支条件：if not run or run.tenant_id != actor.tenant_id:
                raise ForbiddenError()  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError()
            if row.status == InterventionStatus.RESPONDED.value:  # 判断分支条件：if row.status == InterventionStatus.RESPONDED.value:
                if row.actor_id == actor.user_id and row.decision == action.value:  # 判断分支条件：if row.actor_id == actor.user_id and row.decision == action.value:
                    return _intervention_record(row)  # 返回 _intervention_record(row) 给调用方
                raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                    "INTERVENTION_ALREADY_RESPONDED",  # 继续向上一处调用或声明传入 "INTERVENTION_ALREADY_RESPONDED"
                    "intervention has already been answered",  # 继续向上一处调用或声明传入 "intervention has already been answered"
                )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
            if row.status != InterventionStatus.PENDING.value:  # 判断分支条件：if row.status != InterventionStatus.PENDING.value:
                raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                    "INTERVENTION_NOT_PENDING",  # 继续向上一处调用或声明传入 "INTERVENTION_NOT_PENDING"
                    "intervention is no longer pending",  # 继续向上一处调用或声明传入 "intervention is no longer pending"
                )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
            if row.version != expected_version:  # 判断分支条件：if row.version != expected_version:
                raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                    "STALE_INTERVENTION",  # 继续向上一处调用或声明传入 "STALE_INTERVENTION"
                    "intervention version does not match",  # 继续向上一处调用或声明传入 "intervention version does not match"
                    expected_version=row.version,  # 为 ConflictError 设置关键字参数 expected_version，传入当前行给出的值
                )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
            if row.expires_at <= now:  # 判断分支条件：if row.expires_at <= now:
                row.status = InterventionStatus.EXPIRED.value  # 计算 InterventionStatus.EXPIRED.value 并保存到变量 row.status
                run.status = RunStatus.EXPIRED.value  # 计算 RunStatus.EXPIRED.value 并保存到变量 run.status
                run.completed_at = now  # 计算 now 并保存到变量 run.completed_at
                run.error_code = "HUMAN_WAIT_EXPIRED"  # 计算 "HUMAN_WAIT_EXPIRED" 并保存到变量 run.error_code
                expired = True  # 计算 True 并保存到变量 expired
            else:  # 进入前面条件均不成立时的兜底分支
                allowed = {  # 计算 { 并保存到变量 allowed
                    InterventionKind.AGENT_SELECTION.value: {  # 在函数 respond_to_intervention 中执行表达式 InterventionKind.AGENT_SELECTION.value: {，推进当前业务流程
                        DecisionAction.SELECT.value  # 在函数 respond_to_intervention 中执行表达式 DecisionAction.SELECT.value，推进当前业务流程
                    },  # 结束上一处多行结构，保持表达式边界清晰
                    InterventionKind.SQL_APPROVAL.value: {  # 在函数 respond_to_intervention 中执行表达式 InterventionKind.SQL_APPROVAL.value: {，推进当前业务流程
                        DecisionAction.APPROVE.value,  # 向多行字典加入配置项 DecisionAction.APPROVE.value
                        DecisionAction.EDIT.value,  # 向多行字典加入配置项 DecisionAction.EDIT.value
                        DecisionAction.REJECT.value,  # 向多行字典加入配置项 DecisionAction.REJECT.value
                    },  # 结束上一处多行结构，保持表达式边界清晰
                }[row.kind]  # 在函数 respond_to_intervention 中执行表达式 }[row.kind]，推进当前业务流程
                if action.value not in allowed:  # 判断分支条件：if action.value not in allowed:
                    raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                        "INVALID_INTERVENTION_ACTION",  # 继续向上一处调用或声明传入 "INVALID_INTERVENTION_ACTION"
                        "action is not valid for this intervention",  # 继续向上一处调用或声明传入 "action is not valid for this intervention"
                    )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
                row.status = InterventionStatus.RESPONDED.value  # 计算 InterventionStatus.RESPONDED.value 并保存到变量 row.status
                row.decision = action.value  # 计算 action.value 并保存到变量 row.decision
                row.decision_json = decision  # 计算 decision 并保存到变量 row.decision_json
                row.actor_id = actor.user_id  # 计算 actor.user_id 并保存到变量 row.actor_id
                row.responded_at = now  # 计算 now 并保存到变量 row.responded_at
                row.version += 1  # 计算 1 并保存到变量 row.version +
                run.status = RunStatus.QUEUED.value  # 计算 RunStatus.QUEUED.value 并保存到变量 run.status
                run.updated_at = now  # 计算 now 并保存到变量 run.updated_at
                run.version += 1  # 计算 1 并保存到变量 run.version +
                session.add(  # 调用 add 执行当前步骤：session.add(
                    RunJobRow(  # 调用 RunJobRow 执行当前步骤：RunJobRow(
                        run_id=row.run_id,  # 为 RunJobRow 设置关键字参数 run_id，传入当前行给出的值
                        job_type=JobType.RESUME.value,  # 为 RunJobRow 设置关键字参数 job_type，传入当前行给出的值
                        dedupe_key=f"resume:{row.id}",  # 为 RunJobRow 设置关键字参数 dedupe_key，传入当前行给出的值
                        payload_json={  # 为 RunJobRow 设置关键字参数 payload_json，传入当前行给出的值
                            "intervention_id": str(row.id),  # 为多行字典定义键 "intervention_id" 及其对应值
                            "kind": row.kind,  # 为多行字典定义键 "kind" 及其对应值
                            "action": action.value,  # 为多行字典定义键 "action" 及其对应值
                            "decision": decision,  # 为多行字典定义键 "decision" 及其对应值
                        },  # 结束上一处多行结构，保持表达式边界清晰
                        traceparent=traceparent,  # 为 RunJobRow 设置关键字参数 traceparent，传入当前行给出的值
                    )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
                )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
            await session.flush()  # 等待异步操作完成并取得结果：session.flush()
            record = _intervention_record(row)  # 计算 _intervention_record(row) 并保存到变量 record
        if expired:  # 判断分支条件：if expired:
            raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                "INTERVENTION_EXPIRED", "intervention has expired"  # 在函数 respond_to_intervention 中执行表达式 "INTERVENTION_EXPIRED", "intervention has expired"，推进当前业务流程
            )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
        if record is None:  # 判断分支条件：if record is None:
            raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                "INTERVENTION_NOT_PENDING",  # 继续向上一处调用或声明传入 "INTERVENTION_NOT_PENDING"
                "intervention could not be answered",  # 继续向上一处调用或声明传入 "intervention could not be answered"
            )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
        return record  # 返回 record 给调用方

    async def expire_interventions(self) -> list[UUID]:  # 定义异步函数 expire_interventions，封装可被事件循环调度的协程逻辑
        now = utc_now()  # 计算 utc_now() 并保存到变量 now
        expired_run_ids: list[UUID] = []  # 计算 [] 并保存到变量 expired_run_ids
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            rows = (  # 调用 目标函数 构造结果并保存到 rows
                await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                    select(HumanInterventionRow)  # 调用 select 执行当前步骤：select(HumanInterventionRow)
                    .where(  # 调用 目标函数 执行当前步骤：.where(
                        HumanInterventionRow.status  # 在函数 expire_interventions 中执行表达式 HumanInterventionRow.status，推进当前业务流程
                        == InterventionStatus.PENDING.value,  # 继续向上一处调用或声明传入 == InterventionStatus.PENDING.value
                        HumanInterventionRow.expires_at <= now,  # 继续向上一处调用或声明传入 HumanInterventionRow.expires_at <= now
                    )  # 结束函数 expire_interventions 的参数及返回类型声明并开始函数体
                    .with_for_update(skip_locked=True)  # 调用 目标函数 执行当前步骤：.with_for_update(skip_locked=True)
                )  # 结束函数 expire_interventions 的参数及返回类型声明并开始函数体
            ).all()  # 调用 目标函数 执行当前步骤：).all()
            for row in rows:  # 按迭代条件执行循环：for row in rows:
                row.status = InterventionStatus.EXPIRED.value  # 计算 InterventionStatus.EXPIRED.value 并保存到变量 row.status
                expired_run_ids.append(row.run_id)  # 调用 append 执行当前步骤：expired_run_ids.append(row.run_id)
                run = await session.get(RunRow, row.run_id, with_for_update=True)  # 等待 get 完成，并将其结果保存到 run
                if run and run.status == RunStatus.WAITING_HUMAN.value:  # 判断分支条件：if run and run.status == RunStatus.WAITING_HUMAN.value:
                    run.status = RunStatus.EXPIRED.value  # 计算 RunStatus.EXPIRED.value 并保存到变量 run.status
                    run.completed_at = now  # 计算 now 并保存到变量 run.completed_at
                    run.error_code = "HUMAN_WAIT_EXPIRED"  # 计算 "HUMAN_WAIT_EXPIRED" 并保存到变量 run.error_code
                    run.version += 1  # 计算 1 并保存到变量 run.version +
            return expired_run_ids  # 返回 expired_run_ids 给调用方

    # Audit

    async def add_audit(self, record: AuditRecord) -> None:  # 定义异步函数 add_audit，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            session.add(  # 调用 add 执行当前步骤：session.add(
                AuditLogRow(  # 调用 AuditLogRow 执行当前步骤：AuditLogRow(
                    tenant_id=record.tenant_id,  # 为 AuditLogRow 设置关键字参数 tenant_id，传入当前行给出的值
                    actor_id=record.actor_id,  # 为 AuditLogRow 设置关键字参数 actor_id，传入当前行给出的值
                    action=record.action,  # 为 AuditLogRow 设置关键字参数 action，传入当前行给出的值
                    resource_type=record.resource_type,  # 为 AuditLogRow 设置关键字参数 resource_type，传入当前行给出的值
                    resource_id=record.resource_id,  # 为 AuditLogRow 设置关键字参数 resource_id，传入当前行给出的值
                    outcome=record.outcome,  # 为 AuditLogRow 设置关键字参数 outcome，传入当前行给出的值
                    trace_id=record.trace_id,  # 为 AuditLogRow 设置关键字参数 trace_id，传入当前行给出的值
                    metadata_json=record.metadata,  # 为 AuditLogRow 设置关键字参数 metadata_json，传入当前行给出的值
                )  # 结束函数 add_audit 的参数及返回类型声明并开始函数体
            )  # 结束函数 add_audit 的参数及返回类型声明并开始函数体

    async def purge_expired(  # 定义异步函数 purge_expired，封装可被事件循环调度的协程逻辑
        self,  # 为函数 purge_expired 声明参数 self 及其类型或默认值
        *,  # 为函数 purge_expired 声明参数 * 及其类型或默认值
        session_retention_days: int,  # 为函数 purge_expired 声明参数 session_retention_days 及其类型或默认值
        event_retention_days: int,  # 为函数 purge_expired 声明参数 event_retention_days 及其类型或默认值
        audit_retention_days: int,  # 为函数 purge_expired 声明参数 audit_retention_days 及其类型或默认值
    ) -> dict[str, int]:  # 结束 purge_expired 的参数列表并声明返回类型
        now = utc_now()  # 计算 utc_now() 并保存到变量 now
        session_cutoff = now - timedelta(days=session_retention_days)  # 计算 now - timedelta(days=session_retention_days) 并保存到变量 session_cutoff
        event_cutoff = now - timedelta(days=event_retention_days)  # 计算 now - timedelta(days=event_retention_days) 并保存到变量 event_cutoff
        audit_cutoff = now - timedelta(days=audit_retention_days)  # 计算 now - timedelta(days=audit_retention_days) 并保存到变量 audit_cutoff
        async with self.session_factory() as session, session.begin():  # 进入受管理的上下文 async with self.session_factory() as session, session.begin():，确保资源正确获取与释放
            lock_acquired = await session.scalar(  # 等待 scalar 完成，并将其结果保存到 lock_acquired
                text("select pg_try_advisory_xact_lock(812743210)")  # 调用 text 执行当前步骤：text("select pg_try_advisory_xact_lock(812743210)")
            )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            if not lock_acquired:  # 判断分支条件：if not lock_acquired:
                return {  # 返回 { 给调用方
                    "redacted_sessions": 0,  # 为多行字典定义键 "redacted_sessions" 及其对应值
                    "deleted_sessions": 0,  # 为多行字典定义键 "deleted_sessions" 及其对应值
                    "events": 0,  # 为多行字典定义键 "events" 及其对应值
                    "audit": 0,  # 为多行字典定义键 "audit" 及其对应值
                }  # 结束上一处多行结构，保持表达式边界清晰
            event_result = await session.execute(  # 等待 execute 完成，并将其结果保存到 event_result
                delete(RunEventRow).where(RunEventRow.created_at < event_cutoff)  # 调用 delete 执行当前步骤：delete(RunEventRow).where(RunEventRow.created_at < event_cutoff)
            )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            audit_result = await session.execute(  # 等待 execute 完成，并将其结果保存到 audit_result
                delete(AuditLogRow).where(AuditLogRow.created_at < audit_cutoff)  # 调用 delete 执行当前步骤：delete(AuditLogRow).where(AuditLogRow.created_at < audit_cutoff)
            )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            redaction_session_ids = list(  # 调用 list 构造结果并保存到 redaction_session_ids
                (  # 调用 目标函数 执行当前步骤：(
                    await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                        _sessions_due_for_redaction_statement(session_cutoff)  # 调用 _sessions_due_for_redaction_statement 执行当前步骤：_sessions_due_for_redaction_statement(session_cutoff)
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                ).all()  # 调用 目标函数 执行当前步骤：).all()
            )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            if redaction_session_ids:  # 判断分支条件：if redaction_session_ids:
                await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                    update(SessionMessageRow)  # 调用 update 执行当前步骤：update(SessionMessageRow)
                    .where(  # 调用 目标函数 执行当前步骤：.where(
                        SessionMessageRow.session_id.in_(  # 调用 in_ 执行当前步骤：SessionMessageRow.session_id.in_(
                            redaction_session_ids  # 在函数 purge_expired 中执行表达式 redaction_session_ids，推进当前业务流程
                        )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                    .values(  # 调用 目标函数 执行当前步骤：.values(
                        content="[expired by retention policy]",  # 为 values 设置关键字参数 content，传入当前行给出的值
                        metadata_json={},  # 为 values 设置关键字参数 metadata_json，传入当前行给出的值
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                    update(RunRow)  # 调用 update 执行当前步骤：update(RunRow)
                    .where(RunRow.session_id.in_(redaction_session_ids))  # 调用 目标函数 执行当前步骤：.where(RunRow.session_id.in_(redaction_session_ids))
                    .values(  # 调用 目标函数 执行当前步骤：.values(
                        query="[expired by retention policy]",  # 为 values 设置关键字参数 query，传入当前行给出的值
                        output_json=None,  # 为 values 设置关键字参数 output_json，传入当前行给出的值
                        error_message=None,  # 为 values 设置关键字参数 error_message，传入当前行给出的值
                        route_json=None,  # 为 values 设置关键字参数 route_json，传入当前行给出的值
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                    update(HumanInterventionRow)  # 调用 update 执行当前步骤：update(HumanInterventionRow)
                    .where(  # 调用 目标函数 执行当前步骤：.where(
                        HumanInterventionRow.run_id.in_(  # 调用 in_ 执行当前步骤：HumanInterventionRow.run_id.in_(
                            select(RunRow.id).where(  # 调用 select 执行当前步骤：select(RunRow.id).where(
                                RunRow.session_id.in_(redaction_session_ids)  # 调用 in_ 执行当前步骤：RunRow.session_id.in_(redaction_session_ids)
                            )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                        )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                    .values(  # 调用 目标函数 执行当前步骤：.values(
                        payload_json={"redacted": True},  # 为 values 设置关键字参数 payload_json，传入当前行给出的值
                        decision_json=None,  # 为 values 设置关键字参数 decision_json，传入当前行给出的值
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                    update(HarnessSessionRow)  # 调用 update 执行当前步骤：update(HarnessSessionRow)
                    .where(  # 调用 目标函数 执行当前步骤：.where(
                        HarnessSessionRow.id.in_(redaction_session_ids)  # 调用 in_ 执行当前步骤：HarnessSessionRow.id.in_(redaction_session_ids)
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                    .values(  # 调用 目标函数 执行当前步骤：.values(
                        title="[expired by retention policy]",  # 为 values 设置关键字参数 title，传入当前行给出的值
                        redacted_at=now,  # 为 values 设置关键字参数 redacted_at，传入当前行给出的值
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            deletion_session_ids = list(  # 调用 list 构造结果并保存到 deletion_session_ids
                (  # 调用 目标函数 执行当前步骤：(
                    await session.scalars(  # 等待异步操作完成并取得结果：session.scalars(
                        _sessions_due_for_deletion_statement(audit_cutoff)  # 调用 _sessions_due_for_deletion_statement 执行当前步骤：_sessions_due_for_deletion_statement(audit_cutoff)
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                ).all()  # 调用 目标函数 执行当前步骤：).all()
            )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            if deletion_session_ids:  # 判断分支条件：if deletion_session_ids:
                await session.execute(  # 等待异步操作完成并取得结果：session.execute(
                    delete(RunRow).where(  # 调用 delete 执行当前步骤：delete(RunRow).where(
                        RunRow.session_id.in_(deletion_session_ids)  # 调用 in_ 执行当前步骤：RunRow.session_id.in_(deletion_session_ids)
                    )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            session_result = await session.execute(  # 等待 execute 完成，并将其结果保存到 session_result
                delete(HarnessSessionRow).where(  # 调用 delete 执行当前步骤：delete(HarnessSessionRow).where(
                    HarnessSessionRow.id.in_(deletion_session_ids)  # 调用 in_ 执行当前步骤：HarnessSessionRow.id.in_(deletion_session_ids)
                )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
                if deletion_session_ids  # 判断分支条件：if deletion_session_ids
                else delete(HarnessSessionRow).where(  # 调用 目标函数 执行当前步骤：else delete(HarnessSessionRow).where(
                    HarnessSessionRow.id.is_(None)  # 调用 is_ 执行当前步骤：HarnessSessionRow.id.is_(None)
                )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            )  # 结束函数 purge_expired 的参数及返回类型声明并开始函数体
            return {  # 返回 { 给调用方
                "redacted_sessions": len(redaction_session_ids),  # 为多行字典定义键 "redacted_sessions" 及其对应值
                "deleted_sessions": int(session_result.rowcount or 0),  # 为多行字典定义键 "deleted_sessions" 及其对应值
                "events": int(event_result.rowcount or 0),  # 为多行字典定义键 "events" 及其对应值
                "audit": int(audit_result.rowcount or 0),  # 为多行字典定义键 "audit" 及其对应值
            }  # 结束上一处多行结构，保持表达式边界清晰

    async def list_run_ids_for_expired_sessions(  # 定义异步函数 list_run_ids_for_expired_sessions，封装可被事件循环调度的协程逻辑
        self, *, session_retention_days: int  # 为函数 list_run_ids_for_expired_sessions 声明参数 self, *, session_retention_days 及其类型或默认值
    ) -> list[UUID]:  # 结束 list_run_ids_for_expired_sessions 的参数列表并声明返回类型
        cutoff = utc_now() - timedelta(days=session_retention_days)  # 计算 utc_now() - timedelta(days=session_retention_days) 并保存到变量 cutoff
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            expired_sessions = _sessions_due_for_redaction_statement(  # 调用 _sessions_due_for_redaction_statement 构造结果并保存到 expired_sessions
                cutoff  # 在函数 list_run_ids_for_expired_sessions 中执行表达式 cutoff，推进当前业务流程
            ).subquery()  # 调用 目标函数 执行当前步骤：).subquery()
            rows = await session.scalars(  # 等待 scalars 完成，并将其结果保存到 rows
                select(RunRow.id).where(  # 调用 select 执行当前步骤：select(RunRow.id).where(
                    RunRow.session_id.in_(  # 调用 in_ 执行当前步骤：RunRow.session_id.in_(
                        select(expired_sessions.c.id)  # 调用 select 执行当前步骤：select(expired_sessions.c.id)
                    )  # 结束函数 list_run_ids_for_expired_sessions 的参数及返回类型声明并开始函数体
                )  # 结束函数 list_run_ids_for_expired_sessions 的参数及返回类型声明并开始函数体
            )  # 结束函数 list_run_ids_for_expired_sessions 的参数及返回类型声明并开始函数体
            return list(rows.all())  # 返回 list(rows.all()) 给调用方


def _session_record(row: HarnessSessionRow) -> SessionRecord:  # 定义函数 _session_record，封装该模块的一项明确职责
    return SessionRecord(  # 返回 SessionRecord( 给调用方
        id=row.id,  # 为 SessionRecord 设置关键字参数 id，传入当前行给出的值
        tenant_id=row.tenant_id,  # 为 SessionRecord 设置关键字参数 tenant_id，传入当前行给出的值
        user_id=row.user_id,  # 为 SessionRecord 设置关键字参数 user_id，传入当前行给出的值
        title=row.title,  # 为 SessionRecord 设置关键字参数 title，传入当前行给出的值
        status=row.status,  # 为 SessionRecord 设置关键字参数 status，传入当前行给出的值
        version=row.version,  # 为 SessionRecord 设置关键字参数 version，传入当前行给出的值
        created_at=row.created_at,  # 为 SessionRecord 设置关键字参数 created_at，传入当前行给出的值
        updated_at=row.updated_at,  # 为 SessionRecord 设置关键字参数 updated_at，传入当前行给出的值
        deleted_at=row.deleted_at,  # 为 SessionRecord 设置关键字参数 deleted_at，传入当前行给出的值
        redacted_at=row.redacted_at,  # 为 SessionRecord 设置关键字参数 redacted_at，传入当前行给出的值
    )  # 结束函数 _session_record 的参数及返回类型声明并开始函数体


def _message_record(row: SessionMessageRow) -> MessageRecord:  # 定义函数 _message_record，封装该模块的一项明确职责
    return MessageRecord(  # 返回 MessageRecord( 给调用方
        id=row.id,  # 为 MessageRecord 设置关键字参数 id，传入当前行给出的值
        session_id=row.session_id,  # 为 MessageRecord 设置关键字参数 session_id，传入当前行给出的值
        run_id=row.run_id,  # 为 MessageRecord 设置关键字参数 run_id，传入当前行给出的值
        role=row.role,  # 为 MessageRecord 设置关键字参数 role，传入当前行给出的值
        content=row.content,  # 为 MessageRecord 设置关键字参数 content，传入当前行给出的值
        metadata=row.metadata_json,  # 为 MessageRecord 设置关键字参数 metadata，传入当前行给出的值
        created_at=row.created_at,  # 为 MessageRecord 设置关键字参数 created_at，传入当前行给出的值
    )  # 结束函数 _message_record 的参数及返回类型声明并开始函数体


def _run_record(row: RunRow) -> RunRecord:  # 定义函数 _run_record，封装该模块的一项明确职责
    return RunRecord(  # 返回 RunRecord( 给调用方
        id=row.id,  # 为 RunRecord 设置关键字参数 id，传入当前行给出的值
        session_id=row.session_id,  # 为 RunRecord 设置关键字参数 session_id，传入当前行给出的值
        tenant_id=row.tenant_id,  # 为 RunRecord 设置关键字参数 tenant_id，传入当前行给出的值
        user_id=row.user_id,  # 为 RunRecord 设置关键字参数 user_id，传入当前行给出的值
        query=row.query,  # 为 RunRecord 设置关键字参数 query，传入当前行给出的值
        status=RunStatus(row.status),  # 为 RunStatus 设置关键字参数 status，传入当前行给出的值
        requested_agent_id=row.requested_agent_id,  # 为 RunRecord 设置关键字参数 requested_agent_id，传入当前行给出的值
        selected_agent_id=row.selected_agent_id,  # 为 RunRecord 设置关键字参数 selected_agent_id，传入当前行给出的值
        agent_version=row.agent_version,  # 为 RunRecord 设置关键字参数 agent_version，传入当前行给出的值
        route_mode=RouteMode(row.route_mode) if row.route_mode else None,  # 为 RouteMode 设置关键字参数 route_mode，传入当前行给出的值
        route_confidence=row.route_confidence,  # 为 RunRecord 设置关键字参数 route_confidence，传入当前行给出的值
        route=row.route_json,  # 为 RunRecord 设置关键字参数 route，传入当前行给出的值
        budget=row.budget_json or {},  # 为 RunRecord 设置关键字参数 budget，传入当前行给出的值
        output=row.output_json,  # 为 RunRecord 设置关键字参数 output，传入当前行给出的值
        error_code=row.error_code,  # 为 RunRecord 设置关键字参数 error_code，传入当前行给出的值
        error_message=row.error_message,  # 为 RunRecord 设置关键字参数 error_message，传入当前行给出的值
        trace_id=row.trace_id,  # 为 RunRecord 设置关键字参数 trace_id，传入当前行给出的值
        idempotency_key=row.idempotency_key,  # 为 RunRecord 设置关键字参数 idempotency_key，传入当前行给出的值
        version=row.version,  # 为 RunRecord 设置关键字参数 version，传入当前行给出的值
        created_at=row.created_at,  # 为 RunRecord 设置关键字参数 created_at，传入当前行给出的值
        started_at=row.started_at,  # 为 RunRecord 设置关键字参数 started_at，传入当前行给出的值
        completed_at=row.completed_at,  # 为 RunRecord 设置关键字参数 completed_at，传入当前行给出的值
        updated_at=row.updated_at,  # 为 RunRecord 设置关键字参数 updated_at，传入当前行给出的值
        traceparent=row.traceparent,  # 为 RunRecord 设置关键字参数 traceparent，传入当前行给出的值
    )  # 结束函数 _run_record 的参数及返回类型声明并开始函数体


def _event_record(row: RunEventRow) -> EventRecord:  # 定义函数 _event_record，封装该模块的一项明确职责
    return EventRecord(  # 返回 EventRecord( 给调用方
        id=row.id,  # 为 EventRecord 设置关键字参数 id，传入当前行给出的值
        run_id=row.run_id,  # 为 EventRecord 设置关键字参数 run_id，传入当前行给出的值
        seq=row.seq,  # 为 EventRecord 设置关键字参数 seq，传入当前行给出的值
        trace_id=row.trace_id,  # 为 EventRecord 设置关键字参数 trace_id，传入当前行给出的值
        event_type=row.event_type,  # 为 EventRecord 设置关键字参数 event_type，传入当前行给出的值
        payload=row.payload_json,  # 为 EventRecord 设置关键字参数 payload，传入当前行给出的值
        created_at=row.created_at,  # 为 EventRecord 设置关键字参数 created_at，传入当前行给出的值
    )  # 结束函数 _event_record 的参数及返回类型声明并开始函数体


def _job_mapping_record(row: Any) -> JobRecord:  # 定义函数 _job_mapping_record，封装该模块的一项明确职责
    return JobRecord(  # 返回 JobRecord( 给调用方
        id=row["id"],  # 为 JobRecord 设置关键字参数 id，传入当前行给出的值
        run_id=row["run_id"],  # 为 JobRecord 设置关键字参数 run_id，传入当前行给出的值
        job_type=JobType(row["job_type"]),  # 为 JobType 设置关键字参数 job_type，传入当前行给出的值
        status=JobStatus(row["status"]),  # 为 JobStatus 设置关键字参数 status，传入当前行给出的值
        payload=row["payload_json"] or {},  # 为 JobRecord 设置关键字参数 payload，传入当前行给出的值
        traceparent=row["traceparent"],  # 为 JobRecord 设置关键字参数 traceparent，传入当前行给出的值
        available_at=row["available_at"],  # 为 JobRecord 设置关键字参数 available_at，传入当前行给出的值
        lease_owner=row["lease_owner"],  # 为 JobRecord 设置关键字参数 lease_owner，传入当前行给出的值
        lease_until=row["lease_until"],  # 为 JobRecord 设置关键字参数 lease_until，传入当前行给出的值
        attempts=row["attempts"],  # 为 JobRecord 设置关键字参数 attempts，传入当前行给出的值
    )  # 结束函数 _job_mapping_record 的参数及返回类型声明并开始函数体


def _intervention_record(row: HumanInterventionRow) -> InterventionRecord:  # 定义函数 _intervention_record，封装该模块的一项明确职责
    return InterventionRecord(  # 返回 InterventionRecord( 给调用方
        id=row.id,  # 为 InterventionRecord 设置关键字参数 id，传入当前行给出的值
        run_id=row.run_id,  # 为 InterventionRecord 设置关键字参数 run_id，传入当前行给出的值
        kind=InterventionKind(row.kind),  # 为 InterventionKind 设置关键字参数 kind，传入当前行给出的值
        status=InterventionStatus(row.status),  # 为 InterventionStatus 设置关键字参数 status，传入当前行给出的值
        payload=row.payload_json,  # 为 InterventionRecord 设置关键字参数 payload，传入当前行给出的值
        payload_hash=row.payload_hash,  # 为 InterventionRecord 设置关键字参数 payload_hash，传入当前行给出的值
        decision=DecisionAction(row.decision) if row.decision else None,  # 为 DecisionAction 设置关键字参数 decision，传入当前行给出的值
        decision_data=row.decision_json,  # 为 InterventionRecord 设置关键字参数 decision_data，传入当前行给出的值
        actor_id=row.actor_id,  # 为 InterventionRecord 设置关键字参数 actor_id，传入当前行给出的值
        version=row.version,  # 为 InterventionRecord 设置关键字参数 version，传入当前行给出的值
        requested_at=row.requested_at,  # 为 InterventionRecord 设置关键字参数 requested_at，传入当前行给出的值
        expires_at=row.expires_at,  # 为 InterventionRecord 设置关键字参数 expires_at，传入当前行给出的值
        responded_at=row.responded_at,  # 为 InterventionRecord 设置关键字参数 responded_at，传入当前行给出的值
    )  # 结束函数 _intervention_record 的参数及返回类型声明并开始函数体


def _payload_hash(payload: dict[str, Any]) -> str:  # 定义函数 _payload_hash，封装该模块的一项明确职责
    canonical = json.dumps(  # 调用 dumps 构造结果并保存到 canonical
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")  # 调用 目标函数 执行当前步骤：payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )  # 结束函数 _payload_hash 的参数及返回类型声明并开始函数体
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()  # 返回 hashlib.sha256(canonical.encode("utf-8")).hexdigest() 给调用方


def _active_run_exists_expression():  # 定义函数 _active_run_exists_expression，封装该模块的一项明确职责
    return (  # 返回 ( 给调用方
        select(RunRow.id)  # 调用 select 执行当前步骤：select(RunRow.id)
        .where(  # 调用 目标函数 执行当前步骤：.where(
            RunRow.session_id == HarnessSessionRow.id,  # 继续向上一处调用或声明传入 RunRow.session_id == HarnessSessionRow.id
            RunRow.status.in_(ACTIVE_RUN_STATUSES),  # 继续向上一处调用或声明传入 RunRow.status.in_(ACTIVE_RUN_STATUSES)
        )  # 结束函数 _active_run_exists_expression 的参数及返回类型声明并开始函数体
        .exists()  # 调用 目标函数 执行当前步骤：.exists()
    )  # 结束函数 _active_run_exists_expression 的参数及返回类型声明并开始函数体


def _sessions_due_for_redaction_statement(cutoff: datetime):  # 定义函数 _sessions_due_for_redaction_statement，封装该模块的一项明确职责
    return select(HarnessSessionRow.id).where(  # 返回 select(HarnessSessionRow.id).where( 给调用方
        HarnessSessionRow.redacted_at.is_(None),  # 继续向上一处调用或声明传入 HarnessSessionRow.redacted_at.is_(None)
        or_(  # 调用 or_ 执行当前步骤：or_(
            and_(  # 调用 and_ 执行当前步骤：and_(
                HarnessSessionRow.deleted_at.is_not(None),  # 继续向上一处调用或声明传入 HarnessSessionRow.deleted_at.is_not(None)
                HarnessSessionRow.deleted_at < cutoff,  # 继续向上一处调用或声明传入 HarnessSessionRow.deleted_at < cutoff
            ),  # 结束函数 _sessions_due_for_redaction_statement 的参数及返回类型声明并开始函数体
            and_(  # 调用 and_ 执行当前步骤：and_(
                HarnessSessionRow.updated_at < cutoff,  # 继续向上一处调用或声明传入 HarnessSessionRow.updated_at < cutoff
                ~_active_run_exists_expression(),  # 继续向上一处调用或声明传入 ~_active_run_exists_expression()
            ),  # 结束函数 _sessions_due_for_redaction_statement 的参数及返回类型声明并开始函数体
        )  # 结束函数 _sessions_due_for_redaction_statement 的参数及返回类型声明并开始函数体
    )  # 结束函数 _sessions_due_for_redaction_statement 的参数及返回类型声明并开始函数体


def _sessions_due_for_deletion_statement(cutoff: datetime):  # 定义函数 _sessions_due_for_deletion_statement，封装该模块的一项明确职责
    return select(HarnessSessionRow.id).where(  # 返回 select(HarnessSessionRow.id).where( 给调用方
        or_(  # 调用 or_ 执行当前步骤：or_(
            HarnessSessionRow.updated_at < cutoff,  # 继续向上一处调用或声明传入 HarnessSessionRow.updated_at < cutoff
            HarnessSessionRow.deleted_at < cutoff,  # 继续向上一处调用或声明传入 HarnessSessionRow.deleted_at < cutoff
        ),  # 结束函数 _sessions_due_for_deletion_statement 的参数及返回类型声明并开始函数体
        ~_active_run_exists_expression(),  # 继续向上一处调用或声明传入 ~_active_run_exists_expression()
    )  # 结束函数 _sessions_due_for_deletion_statement 的参数及返回类型声明并开始函数体
