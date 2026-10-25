"""Transport-neutral records returned by harness persistence."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from dataclasses import dataclass, field  # 从 dataclasses 导入 dataclass, field，供本模块后续代码使用
from datetime import datetime  # 从 datetime 导入 datetime，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from app.harness.types import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    DecisionAction,  # 从当前 import 模块导入符号 DecisionAction
    InterventionKind,  # 从当前 import 模块导入符号 InterventionKind
    InterventionStatus,  # 从当前 import 模块导入符号 InterventionStatus
    JobStatus,  # 从当前 import 模块导入符号 JobStatus
    JobType,  # 从当前 import 模块导入符号 JobType
    RouteMode,  # 从当前 import 模块导入符号 RouteMode
    RunStatus,  # 从当前 import 模块导入符号 RunStatus
)  # 结束多符号导入列表


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class SessionRecord:  # 定义类 SessionRecord，组织相关状态与行为
    id: UUID  # 声明或继续传入参数 id: UUID
    tenant_id: str  # 声明或继续传入参数 tenant_id: str
    user_id: str  # 声明或继续传入参数 user_id: str
    title: str  # 声明或继续传入参数 title: str
    status: str  # 声明或继续传入参数 status: str
    version: int  # 声明或继续传入参数 version: int
    created_at: datetime  # 声明或继续传入参数 created_at: datetime
    updated_at: datetime  # 声明或继续传入参数 updated_at: datetime
    deleted_at: datetime | None = None  # 计算 None 并保存到变量 deleted_at
    redacted_at: datetime | None = None  # 计算 None 并保存到变量 redacted_at


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class MessageRecord:  # 定义类 MessageRecord，组织相关状态与行为
    id: UUID  # 声明或继续传入参数 id: UUID
    session_id: UUID  # 声明或继续传入参数 session_id: UUID
    run_id: UUID | None  # 声明或继续传入参数 run_id: UUID | None
    role: str  # 声明或继续传入参数 role: str
    content: str  # 声明或继续传入参数 content: str
    metadata: dict[str, Any]  # 声明或继续传入参数 metadata: dict[str, Any]
    created_at: datetime  # 声明或继续传入参数 created_at: datetime


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class RunRecord:  # 定义类 RunRecord，组织相关状态与行为
    id: UUID  # 声明或继续传入参数 id: UUID
    session_id: UUID  # 声明或继续传入参数 session_id: UUID
    tenant_id: str  # 声明或继续传入参数 tenant_id: str
    user_id: str  # 声明或继续传入参数 user_id: str
    query: str  # 声明或继续传入参数 query: str
    status: RunStatus  # 声明或继续传入参数 status: RunStatus
    requested_agent_id: str | None  # 声明或继续传入参数 requested_agent_id: str | None
    selected_agent_id: str | None  # 声明或继续传入参数 selected_agent_id: str | None
    agent_version: str | None  # 声明或继续传入参数 agent_version: str | None
    route_mode: RouteMode | None  # 声明或继续传入参数 route_mode: RouteMode | None
    route_confidence: float | None  # 声明或继续传入参数 route_confidence: float | None
    route: dict[str, Any] | None  # 声明或继续传入参数 route: dict[str, Any] | None
    budget: dict[str, Any]  # 声明或继续传入参数 budget: dict[str, Any]
    output: dict[str, Any] | None  # 声明或继续传入参数 output: dict[str, Any] | None
    error_code: str | None  # 声明或继续传入参数 error_code: str | None
    error_message: str | None  # 声明或继续传入参数 error_message: str | None
    trace_id: str | None  # 声明或继续传入参数 trace_id: str | None
    idempotency_key: str  # 声明或继续传入参数 idempotency_key: str
    version: int  # 声明或继续传入参数 version: int
    created_at: datetime  # 声明或继续传入参数 created_at: datetime
    started_at: datetime | None  # 声明或继续传入参数 started_at: datetime | None
    completed_at: datetime | None  # 声明或继续传入参数 completed_at: datetime | None
    updated_at: datetime  # 声明或继续传入参数 updated_at: datetime
    traceparent: str | None = None  # 计算 None 并保存到变量 traceparent


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class EventRecord:  # 定义类 EventRecord，组织相关状态与行为
    id: UUID  # 声明或继续传入参数 id: UUID
    run_id: UUID  # 声明或继续传入参数 run_id: UUID
    seq: int  # 声明或继续传入参数 seq: int
    trace_id: str | None  # 声明或继续传入参数 trace_id: str | None
    event_type: str  # 声明或继续传入参数 event_type: str
    payload: dict[str, Any]  # 声明或继续传入参数 payload: dict[str, Any]
    created_at: datetime  # 声明或继续传入参数 created_at: datetime


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class JobRecord:  # 定义类 JobRecord，组织相关状态与行为
    id: UUID  # 声明或继续传入参数 id: UUID
    run_id: UUID  # 声明或继续传入参数 run_id: UUID
    job_type: JobType  # 声明或继续传入参数 job_type: JobType
    status: JobStatus  # 声明或继续传入参数 status: JobStatus
    payload: dict[str, Any]  # 声明或继续传入参数 payload: dict[str, Any]
    traceparent: str | None  # 声明或继续传入参数 traceparent: str | None
    available_at: datetime  # 声明或继续传入参数 available_at: datetime
    lease_owner: str | None  # 声明或继续传入参数 lease_owner: str | None
    lease_until: datetime | None  # 声明或继续传入参数 lease_until: datetime | None
    attempts: int  # 声明或继续传入参数 attempts: int


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class InterventionRecord:  # 定义类 InterventionRecord，组织相关状态与行为
    id: UUID  # 声明或继续传入参数 id: UUID
    run_id: UUID  # 声明或继续传入参数 run_id: UUID
    kind: InterventionKind  # 声明或继续传入参数 kind: InterventionKind
    status: InterventionStatus  # 声明或继续传入参数 status: InterventionStatus
    payload: dict[str, Any]  # 声明或继续传入参数 payload: dict[str, Any]
    payload_hash: str  # 声明或继续传入参数 payload_hash: str
    decision: DecisionAction | None  # 声明或继续传入参数 decision: DecisionAction | None
    decision_data: dict[str, Any] | None  # 声明或继续传入参数 decision_data: dict[str, Any] | None
    actor_id: str | None  # 声明或继续传入参数 actor_id: str | None
    version: int  # 声明或继续传入参数 version: int
    requested_at: datetime  # 声明或继续传入参数 requested_at: datetime
    expires_at: datetime  # 声明或继续传入参数 expires_at: datetime
    responded_at: datetime | None  # 声明或继续传入参数 responded_at: datetime | None


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class AuditRecord:  # 定义类 AuditRecord，组织相关状态与行为
    id: UUID  # 声明或继续传入参数 id: UUID
    tenant_id: str  # 声明或继续传入参数 tenant_id: str
    actor_id: str  # 声明或继续传入参数 actor_id: str
    action: str  # 声明或继续传入参数 action: str
    resource_type: str  # 声明或继续传入参数 resource_type: str
    resource_id: str  # 声明或继续传入参数 resource_id: str
    outcome: str  # 声明或继续传入参数 outcome: str
    trace_id: str | None  # 声明或继续传入参数 trace_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)  # 计算 field(default_factory=dict) 并保存到变量 metadata
    created_at: datetime | None = None  # 计算 None 并保存到变量 created_at
