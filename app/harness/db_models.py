"""SQLAlchemy models for the durable harness state."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from datetime import datetime  # 从 datetime 导入 datetime，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用
from uuid import UUID, uuid4  # 从 uuid 导入 UUID, uuid4，供本模块后续代码使用

from sqlalchemy import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    DateTime,  # 从当前 import 模块导入符号 DateTime
    Float,  # 从当前 import 模块导入符号 Float
    ForeignKey,  # 从当前 import 模块导入符号 ForeignKey
    Index,  # 从当前 import 模块导入符号 Index
    Integer,  # 从当前 import 模块导入符号 Integer
    MetaData,  # 从当前 import 模块导入符号 MetaData
    String,  # 从当前 import 模块导入符号 String
    Text,  # 从当前 import 模块导入符号 Text
    UniqueConstraint,  # 从当前 import 模块导入符号 UniqueConstraint
    func,  # 从当前 import 模块导入符号 func
    text,  # 从当前 import 模块导入符号 text
)  # 结束多符号导入列表
from sqlalchemy.dialects.postgresql import JSONB  # 从 sqlalchemy.dialects.postgresql 导入 JSONB，供本模块后续代码使用
from sqlalchemy.dialects.postgresql import UUID as PGUUID  # 从 sqlalchemy.dialects.postgresql 导入 UUID as PGUUID，供本模块后续代码使用
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # 从 sqlalchemy.orm 导入 DeclarativeBase, Mapped, mapped_column，供本模块后续代码使用

from app.conf.settings import get_settings  # 从 app.conf.settings 导入 get_settings，供本模块后续代码使用
from app.harness.types import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    InterventionKind,  # 从当前 import 模块导入符号 InterventionKind
    InterventionStatus,  # 从当前 import 模块导入符号 InterventionStatus
    JobStatus,  # 从当前 import 模块导入符号 JobStatus
    JobType,  # 从当前 import 模块导入符号 JobType
    RunStatus,  # 从当前 import 模块导入符号 RunStatus
)  # 结束多符号导入列表

HARNESS_SCHEMA = get_settings().postgres_schema  # 计算 get_settings().postgres_schema 并保存到变量 HARNESS_SCHEMA


class HarnessBase(DeclarativeBase):  # 定义类 HarnessBase，组织相关状态与行为
    metadata = MetaData(schema=HARNESS_SCHEMA)  # 计算 MetaData(schema=HARNESS_SCHEMA) 并保存到变量 metadata


class HarnessSessionRow(HarnessBase):  # 定义类 HarnessSessionRow，组织相关状态与行为
    __tablename__ = "sessions"  # 计算 "sessions" 并保存到变量 __tablename__

    id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 id
        PGUUID(as_uuid=True), primary_key=True, default=uuid4  # 调用 PGUUID 执行当前步骤：PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # 计算 mapped_column(String(128), nullable=False, index=True) 并保存到变量 tenant_id
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # 计算 mapped_column(String(128), nullable=False, index=True) 并保存到变量 user_id
    title: Mapped[str] = mapped_column(String(200), nullable=False)  # 计算 mapped_column(String(200), nullable=False) 并保存到变量 title
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")  # 计算 mapped_column(String(32), nullable=False, default="active") 并保存到变量 status
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 计算 mapped_column(Integer, nullable=False, default=1) 并保存到变量 version
    created_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 created_at
        DateTime(timezone=True), nullable=False, server_default=func.now()  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), nullable=False, server_default=func.now()
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    updated_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 updated_at
        DateTime(timezone=True),  # 继续向上一处调用或声明传入 DateTime(timezone=True)
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        server_default=func.now(),  # 为 func.now 设置关键字参数 server_default，传入当前行给出的值
        onupdate=func.now(),  # 为 func.now 设置关键字参数 onupdate，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 计算 mapped_column(DateTime(timezone=True)) 并保存到变量 deleted_at
    redacted_at: Mapped[datetime | None] = mapped_column(  # 调用 mapped_column 构造结果并保存到 redacted_at
        DateTime(timezone=True), index=True  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), index=True
    )  # 结束 mapped_column 调用参数，得到完整表达式结果

    __table_args__ = (  # 调用 目标函数 构造结果并保存到 __table_args__
        Index("ix_sessions_tenant_user_updated", "tenant_id", "user_id", "updated_at"),  # 向多行序列加入元素 Index("ix_sessions_tenant_user_updated", "tenant_id", "user_id", "updat…
    )  # 结束上一处多行结构，保持表达式边界清晰


class SessionMessageRow(HarnessBase):  # 定义类 SessionMessageRow，组织相关状态与行为
    __tablename__ = "session_messages"  # 计算 "session_messages" 并保存到变量 __tablename__

    id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 id
        PGUUID(as_uuid=True), primary_key=True, default=uuid4  # 调用 PGUUID 执行当前步骤：PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    session_id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 session_id
        PGUUID(as_uuid=True),  # 继续向上一处调用或声明传入 PGUUID(as_uuid=True)
        ForeignKey(f"{HARNESS_SCHEMA}.sessions.id", ondelete="CASCADE"),  # 继续向上一处调用或声明传入 ForeignKey(f"{HARNESS_SCHEMA}.sessions.id", ondelete="CASCADE")
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        index=True,  # 为 mapped_column 设置关键字参数 index，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)  # 计算 mapped_column(PGUUID(as_uuid=True), index=True) 并保存到变量 run_id
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # 计算 mapped_column(String(32), nullable=False) 并保存到变量 role
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 计算 mapped_column(Text, nullable=False) 并保存到变量 content
    metadata_json: Mapped[dict[str, Any]] = mapped_column(  # 调用 mapped_column 构造结果并保存到 metadata_json
        "metadata", JSONB, nullable=False, default=dict  # 在类 SessionMessageRow 中执行声明或表达式 "metadata", JSONB, nullable=False, default=dict，提供实例所需能力
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    created_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 created_at
        DateTime(timezone=True), nullable=False, server_default=func.now()  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), nullable=False, server_default=func.now()
    )  # 结束 mapped_column 调用参数，得到完整表达式结果

    __table_args__ = (  # 调用 目标函数 构造结果并保存到 __table_args__
        Index("ix_session_messages_session_created", "session_id", "created_at"),  # 向多行序列加入元素 Index("ix_session_messages_session_created", "session_id", "created_at")
    )  # 结束上一处多行结构，保持表达式边界清晰


class RunRow(HarnessBase):  # 定义类 RunRow，组织相关状态与行为
    __tablename__ = "runs"  # 计算 "runs" 并保存到变量 __tablename__

    id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 id
        PGUUID(as_uuid=True), primary_key=True, default=uuid4  # 调用 PGUUID 执行当前步骤：PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    session_id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 session_id
        PGUUID(as_uuid=True),  # 继续向上一处调用或声明传入 PGUUID(as_uuid=True)
        ForeignKey(f"{HARNESS_SCHEMA}.sessions.id", ondelete="RESTRICT"),  # 继续向上一处调用或声明传入 ForeignKey(f"{HARNESS_SCHEMA}.sessions.id", ondelete="RESTRICT")
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        index=True,  # 为 mapped_column 设置关键字参数 index，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # 计算 mapped_column(String(128), nullable=False, index=True) 并保存到变量 tenant_id
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # 计算 mapped_column(String(128), nullable=False, index=True) 并保存到变量 user_id
    query: Mapped[str] = mapped_column(Text, nullable=False)  # 计算 mapped_column(Text, nullable=False) 并保存到变量 query
    status: Mapped[str] = mapped_column(  # 调用 mapped_column 构造结果并保存到 status
        String(32), nullable=False, default=RunStatus.QUEUED.value, index=True  # 调用 String 执行当前步骤：String(32), nullable=False, default=RunStatus.QUEUED.value, index=True
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    requested_agent_id: Mapped[str | None] = mapped_column(String(64))  # 计算 mapped_column(String(64)) 并保存到变量 requested_agent_id
    selected_agent_id: Mapped[str | None] = mapped_column(String(64), index=True)  # 计算 mapped_column(String(64), index=True) 并保存到变量 selected_agent_id
    agent_version: Mapped[str | None] = mapped_column(String(32))  # 计算 mapped_column(String(32)) 并保存到变量 agent_version
    route_mode: Mapped[str | None] = mapped_column(String(32))  # 计算 mapped_column(String(32)) 并保存到变量 route_mode
    route_confidence: Mapped[float | None] = mapped_column(Float)  # 计算 mapped_column(Float) 并保存到变量 route_confidence
    route_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 计算 mapped_column(JSONB) 并保存到变量 route_json
    budget_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # 计算 mapped_column(JSONB, nullable=False, default=dict) 并保存到变量 budget_json
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 计算 mapped_column(JSONB) 并保存到变量 output_json
    error_code: Mapped[str | None] = mapped_column(String(128))  # 计算 mapped_column(String(128)) 并保存到变量 error_code
    error_message: Mapped[str | None] = mapped_column(Text)  # 计算 mapped_column(Text) 并保存到变量 error_message
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)  # 计算 mapped_column(String(64), index=True) 并保存到变量 trace_id
    traceparent: Mapped[str | None] = mapped_column(String(128))  # 计算 mapped_column(String(128)) 并保存到变量 traceparent
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)  # 计算 mapped_column(String(128), nullable=False) 并保存到变量 idempotency_key
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 计算 mapped_column(Integer, nullable=False, default=1) 并保存到变量 version
    created_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 created_at
        DateTime(timezone=True), nullable=False, server_default=func.now()  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), nullable=False, server_default=func.now()
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 计算 mapped_column(DateTime(timezone=True)) 并保存到变量 started_at
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 计算 mapped_column(DateTime(timezone=True)) 并保存到变量 completed_at
    updated_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 updated_at
        DateTime(timezone=True),  # 继续向上一处调用或声明传入 DateTime(timezone=True)
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        server_default=func.now(),  # 为 func.now 设置关键字参数 server_default，传入当前行给出的值
        onupdate=func.now(),  # 为 func.now 设置关键字参数 onupdate，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果

    __table_args__ = (  # 调用 目标函数 构造结果并保存到 __table_args__
        UniqueConstraint(  # 调用 UniqueConstraint 执行当前步骤：UniqueConstraint(
            "tenant_id",  # 向多行序列加入元素 "tenant_id"
            "session_id",  # 向多行序列加入元素 "session_id"
            "idempotency_key",  # 向多行序列加入元素 "idempotency_key"
            name="uq_runs_tenant_session_idempotency",  # 为 UniqueConstraint 设置关键字参数 name，传入当前行给出的值
        ),  # 结束 UniqueConstraint 调用参数，得到完整表达式结果
        Index("ix_runs_tenant_status", "tenant_id", "status"),  # 向多行序列加入元素 Index("ix_runs_tenant_status", "tenant_id", "status")
        Index("ix_runs_active_session", "session_id", "status"),  # 向多行序列加入元素 Index("ix_runs_active_session", "session_id", "status")
        Index(  # 调用 Index 执行当前步骤：Index(
            "uq_runs_one_active_session",  # 向多行序列加入元素 "uq_runs_one_active_session"
            "session_id",  # 向多行序列加入元素 "session_id"
            unique=True,  # 为 Index 设置关键字参数 unique，传入当前行给出的值
            postgresql_where=text(  # 为 text 设置关键字参数 postgresql_where，传入当前行给出的值
                "status IN ('queued', 'running', 'waiting_human')"  # 调用 目标函数 执行当前步骤："status IN ('queued', 'running', 'waiting_human')"
            ),  # 结束 text 调用参数，得到完整表达式结果
        ),  # 结束 Index 调用参数，得到完整表达式结果
    )  # 结束上一处多行结构，保持表达式边界清晰


class RunJobRow(HarnessBase):  # 定义类 RunJobRow，组织相关状态与行为
    __tablename__ = "run_jobs"  # 计算 "run_jobs" 并保存到变量 __tablename__

    id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 id
        PGUUID(as_uuid=True), primary_key=True, default=uuid4  # 调用 PGUUID 执行当前步骤：PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    run_id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 run_id
        PGUUID(as_uuid=True),  # 继续向上一处调用或声明传入 PGUUID(as_uuid=True)
        ForeignKey(f"{HARNESS_SCHEMA}.runs.id", ondelete="CASCADE"),  # 继续向上一处调用或声明传入 ForeignKey(f"{HARNESS_SCHEMA}.runs.id", ondelete="CASCADE")
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        index=True,  # 为 mapped_column 设置关键字参数 index，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    job_type: Mapped[str] = mapped_column(  # 调用 mapped_column 构造结果并保存到 job_type
        String(32), nullable=False, default=JobType.START.value  # 调用 String 执行当前步骤：String(32), nullable=False, default=JobType.START.value
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    status: Mapped[str] = mapped_column(  # 调用 mapped_column 构造结果并保存到 status
        String(32), nullable=False, default=JobStatus.QUEUED.value, index=True  # 调用 String 执行当前步骤：String(32), nullable=False, default=JobStatus.QUEUED.value, index=True
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)  # 计算 mapped_column(String(200), nullable=False, unique=True) 并保存到变量 dedupe_key
    payload_json: Mapped[dict[str, Any]] = mapped_column(  # 调用 mapped_column 构造结果并保存到 payload_json
        JSONB, nullable=False, default=dict  # 在类 RunJobRow 中执行声明或表达式 JSONB, nullable=False, default=dict，提供实例所需能力
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    traceparent: Mapped[str | None] = mapped_column(String(128))  # 计算 mapped_column(String(128)) 并保存到变量 traceparent
    available_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 available_at
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), nullable=False, server_default=func.now(), ind…
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    lease_owner: Mapped[str | None] = mapped_column(String(128), index=True)  # 计算 mapped_column(String(128), index=True) 并保存到变量 lease_owner
    lease_until: Mapped[datetime | None] = mapped_column(  # 调用 mapped_column 构造结果并保存到 lease_until
        DateTime(timezone=True), index=True  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), index=True
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 计算 mapped_column(Integer, nullable=False, default=0) 并保存到变量 attempts
    created_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 created_at
        DateTime(timezone=True), nullable=False, server_default=func.now()  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), nullable=False, server_default=func.now()
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    updated_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 updated_at
        DateTime(timezone=True),  # 继续向上一处调用或声明传入 DateTime(timezone=True)
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        server_default=func.now(),  # 为 func.now 设置关键字参数 server_default，传入当前行给出的值
        onupdate=func.now(),  # 为 func.now 设置关键字参数 onupdate，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果

    __table_args__ = (  # 调用 目标函数 构造结果并保存到 __table_args__
        Index("ix_run_jobs_claim", "status", "available_at", "lease_until"),  # 向多行序列加入元素 Index("ix_run_jobs_claim", "status", "available_at", "lease_until")
    )  # 结束上一处多行结构，保持表达式边界清晰


class RunEventRow(HarnessBase):  # 定义类 RunEventRow，组织相关状态与行为
    __tablename__ = "run_events"  # 计算 "run_events" 并保存到变量 __tablename__

    id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 id
        PGUUID(as_uuid=True), primary_key=True, default=uuid4  # 调用 PGUUID 执行当前步骤：PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    run_id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 run_id
        PGUUID(as_uuid=True),  # 继续向上一处调用或声明传入 PGUUID(as_uuid=True)
        ForeignKey(f"{HARNESS_SCHEMA}.runs.id", ondelete="CASCADE"),  # 继续向上一处调用或声明传入 ForeignKey(f"{HARNESS_SCHEMA}.runs.id", ondelete="CASCADE")
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        index=True,  # 为 mapped_column 设置关键字参数 index，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    seq: Mapped[int] = mapped_column(Integer, nullable=False)  # 计算 mapped_column(Integer, nullable=False) 并保存到变量 seq
    trace_id: Mapped[str | None] = mapped_column(String(64))  # 计算 mapped_column(String(64)) 并保存到变量 trace_id
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)  # 计算 mapped_column(String(80), nullable=False) 并保存到变量 event_type
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # 计算 mapped_column(JSONB, nullable=False) 并保存到变量 payload_json
    created_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 created_at
        DateTime(timezone=True), nullable=False, server_default=func.now()  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), nullable=False, server_default=func.now()
    )  # 结束 mapped_column 调用参数，得到完整表达式结果

    __table_args__ = (  # 调用 目标函数 构造结果并保存到 __table_args__
        UniqueConstraint("run_id", "seq", name="uq_run_events_run_seq"),  # 向多行序列加入元素 UniqueConstraint("run_id", "seq", name="uq_run_events_run_seq")
        Index("ix_run_events_run_created", "run_id", "created_at"),  # 向多行序列加入元素 Index("ix_run_events_run_created", "run_id", "created_at")
    )  # 结束上一处多行结构，保持表达式边界清晰


class HumanInterventionRow(HarnessBase):  # 定义类 HumanInterventionRow，组织相关状态与行为
    __tablename__ = "human_interventions"  # 计算 "human_interventions" 并保存到变量 __tablename__

    id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 id
        PGUUID(as_uuid=True), primary_key=True, default=uuid4  # 调用 PGUUID 执行当前步骤：PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    run_id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 run_id
        PGUUID(as_uuid=True),  # 继续向上一处调用或声明传入 PGUUID(as_uuid=True)
        ForeignKey(f"{HARNESS_SCHEMA}.runs.id", ondelete="CASCADE"),  # 继续向上一处调用或声明传入 ForeignKey(f"{HARNESS_SCHEMA}.runs.id", ondelete="CASCADE")
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        index=True,  # 为 mapped_column 设置关键字参数 index，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    kind: Mapped[str] = mapped_column(  # 调用 mapped_column 构造结果并保存到 kind
        String(32), nullable=False, default=InterventionKind.AGENT_SELECTION.value  # 调用 String 执行当前步骤：String(32), nullable=False, default=InterventionKind.AGENT_SELECTION.va…
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    status: Mapped[str] = mapped_column(  # 调用 mapped_column 构造结果并保存到 status
        String(32),  # 继续向上一处调用或声明传入 String(32)
        nullable=False,  # 为 mapped_column 设置关键字参数 nullable，传入当前行给出的值
        default=InterventionStatus.PENDING.value,  # 为 mapped_column 设置关键字参数 default，传入当前行给出的值
        index=True,  # 为 mapped_column 设置关键字参数 index，传入当前行给出的值
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # 计算 mapped_column(JSONB, nullable=False) 并保存到变量 payload_json
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # 计算 mapped_column(String(64), nullable=False) 并保存到变量 payload_hash
    decision: Mapped[str | None] = mapped_column(String(32))  # 计算 mapped_column(String(32)) 并保存到变量 decision
    decision_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 计算 mapped_column(JSONB) 并保存到变量 decision_json
    actor_id: Mapped[str | None] = mapped_column(String(128))  # 计算 mapped_column(String(128)) 并保存到变量 actor_id
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 计算 mapped_column(Integer, nullable=False, default=1) 并保存到变量 version
    requested_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 requested_at
        DateTime(timezone=True), nullable=False, server_default=func.now()  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), nullable=False, server_default=func.now()
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # 计算 mapped_column(DateTime(timezone=True), nullable=False) 并保存到变量 expires_at
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 计算 mapped_column(DateTime(timezone=True)) 并保存到变量 responded_at

    __table_args__ = (  # 调用 目标函数 构造结果并保存到 __table_args__
        Index("ix_interventions_run_status", "run_id", "status"),  # 向多行序列加入元素 Index("ix_interventions_run_status", "run_id", "status")
    )  # 结束上一处多行结构，保持表达式边界清晰


class AuditLogRow(HarnessBase):  # 定义类 AuditLogRow，组织相关状态与行为
    __tablename__ = "audit_logs"  # 计算 "audit_logs" 并保存到变量 __tablename__

    id: Mapped[UUID] = mapped_column(  # 调用 mapped_column 构造结果并保存到 id
        PGUUID(as_uuid=True), primary_key=True, default=uuid4  # 调用 PGUUID 执行当前步骤：PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # 计算 mapped_column(String(128), nullable=False, index=True) 并保存到变量 tenant_id
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)  # 计算 mapped_column(String(128), nullable=False) 并保存到变量 actor_id
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # 计算 mapped_column(String(100), nullable=False) 并保存到变量 action
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 计算 mapped_column(String(64), nullable=False) 并保存到变量 resource_type
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)  # 计算 mapped_column(String(128), nullable=False) 并保存到变量 resource_id
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)  # 计算 mapped_column(String(32), nullable=False) 并保存到变量 outcome
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)  # 计算 mapped_column(String(64), index=True) 并保存到变量 trace_id
    metadata_json: Mapped[dict[str, Any]] = mapped_column(  # 调用 mapped_column 构造结果并保存到 metadata_json
        "metadata", JSONB, nullable=False, default=dict  # 在类 AuditLogRow 中执行声明或表达式 "metadata", JSONB, nullable=False, default=dict，提供实例所需能力
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    created_at: Mapped[datetime] = mapped_column(  # 调用 mapped_column 构造结果并保存到 created_at
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True  # 调用 DateTime 执行当前步骤：DateTime(timezone=True), nullable=False, server_default=func.now(), ind…
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
