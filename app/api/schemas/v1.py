"""Public Pydantic contracts for the v1 harness API."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from datetime import datetime  # 从 datetime 导入 datetime，供本模块后续代码使用
from typing import Any, Literal  # 从 typing 导入 Any, Literal，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from pydantic import BaseModel, ConfigDict, Field, model_validator  # 从 pydantic 导入 BaseModel, ConfigDict, Field, model_validator，供本模块后续代码使用

from app.harness.types import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    DecisionAction,  # 从当前 import 模块导入符号 DecisionAction
    InterventionKind,  # 从当前 import 模块导入符号 InterventionKind
    InterventionStatus,  # 从当前 import 模块导入符号 InterventionStatus
    RouteMode,  # 从当前 import 模块导入符号 RouteMode
    RunStatus,  # 从当前 import 模块导入符号 RunStatus
)  # 结束多符号导入列表


class AgentResponse(BaseModel):  # 定义类 AgentResponse，组织相关状态与行为
    agent_id: str  # 声明或继续传入参数 agent_id: str
    version: str  # 声明或继续传入参数 version: str
    display_name: str  # 声明或继续传入参数 display_name: str
    description: str  # 声明或继续传入参数 description: str
    capabilities: list[str]  # 声明或继续传入参数 capabilities: list[str]
    response_types: list[str]  # 声明或继续传入参数 response_types: list[str]


class SessionCreateRequest(BaseModel):  # 定义类 SessionCreateRequest，组织相关状态与行为
    title: str = Field(default="新会话", min_length=1, max_length=200)  # 计算 Field(default="新会话", min_length=1, max_length=200) 并保存到变量 title


class SessionResponse(BaseModel):  # 定义类 SessionResponse，组织相关状态与行为
    model_config = ConfigDict(from_attributes=True)  # 计算 ConfigDict(from_attributes=True) 并保存到变量 model_config

    id: UUID  # 声明或继续传入参数 id: UUID
    title: str  # 声明或继续传入参数 title: str
    status: str  # 声明或继续传入参数 status: str
    version: int  # 声明或继续传入参数 version: int
    created_at: datetime  # 声明或继续传入参数 created_at: datetime
    updated_at: datetime  # 声明或继续传入参数 updated_at: datetime


class MessageResponse(BaseModel):  # 定义类 MessageResponse，组织相关状态与行为
    model_config = ConfigDict(from_attributes=True)  # 计算 ConfigDict(from_attributes=True) 并保存到变量 model_config

    id: UUID  # 声明或继续传入参数 id: UUID
    run_id: UUID | None  # 声明或继续传入参数 run_id: UUID | None
    role: str  # 声明或继续传入参数 role: str
    content: str  # 声明或继续传入参数 content: str
    metadata: dict[str, Any]  # 声明或继续传入参数 metadata: dict[str, Any]
    created_at: datetime  # 声明或继续传入参数 created_at: datetime


class RunSummaryResponse(BaseModel):  # 定义类 RunSummaryResponse，组织相关状态与行为
    model_config = ConfigDict(from_attributes=True)  # 计算 ConfigDict(from_attributes=True) 并保存到变量 model_config

    id: UUID  # 声明或继续传入参数 id: UUID
    status: RunStatus  # 声明或继续传入参数 status: RunStatus
    requested_agent_id: str | None  # 声明或继续传入参数 requested_agent_id: str | None
    selected_agent_id: str | None  # 声明或继续传入参数 selected_agent_id: str | None
    agent_version: str | None  # 声明或继续传入参数 agent_version: str | None
    route_mode: RouteMode | None  # 声明或继续传入参数 route_mode: RouteMode | None
    route_confidence: float | None  # 声明或继续传入参数 route_confidence: float | None
    created_at: datetime  # 声明或继续传入参数 created_at: datetime
    completed_at: datetime | None  # 声明或继续传入参数 completed_at: datetime | None


class SessionListItem(BaseModel):  # 定义类 SessionListItem，组织相关状态与行为
    model_config = ConfigDict(from_attributes=True)  # 计算 ConfigDict(from_attributes=True) 并保存到变量 model_config

    id: UUID  # 声明或继续传入参数 id: UUID
    title: str  # 声明或继续传入参数 title: str
    status: str  # 声明或继续传入参数 status: str
    version: int  # 声明或继续传入参数 version: int
    created_at: datetime  # 声明或继续传入参数 created_at: datetime
    updated_at: datetime  # 声明或继续传入参数 updated_at: datetime


class SessionListResponse(BaseModel):  # 定义类 SessionListResponse，组织相关状态与行为
    items: list[SessionListItem]  # 声明或继续传入参数 items: list[SessionListItem]
    next_cursor: str | None  # 声明或继续传入参数 next_cursor: str | None


class SessionDetailResponse(BaseModel):  # 定义类 SessionDetailResponse，组织相关状态与行为
    session: SessionResponse  # 声明或继续传入参数 session: SessionResponse
    messages: list[MessageResponse]  # 声明或继续传入参数 messages: list[MessageResponse]
    runs: list[RunSummaryResponse]  # 声明或继续传入参数 runs: list[RunSummaryResponse]


class RunCreateRequest(BaseModel):  # 定义类 RunCreateRequest，组织相关状态与行为
    query: str = Field(min_length=1, max_length=4000)  # 计算 Field(min_length=1, max_length=4000) 并保存到变量 query
    agent_id: str | None = Field(  # 调用 Field 构造结果并保存到 agent_id
        default=None, pattern=r"^[a-z][a-z0-9_]{2,63}$"  # 为 Field 设置关键字参数 default，传入当前行给出的值
    )  # 结束 Field 调用参数，得到完整表达式结果

    @model_validator(mode="after")  # 应用装饰器 model_validator(mode="after")，为紧随其后的定义附加框架行为
    def normalize_query(self) -> "RunCreateRequest":  # 定义函数 normalize_query，封装该模块的一项明确职责
        self.query = self.query.strip()  # 将依赖或状态 self.query.strip() 保存到实例属性 self.query
        if not self.query:  # 判断分支条件：if not self.query:
            raise ValueError("query must not be blank")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("query must not be blank")
        return self  # 返回 self 给调用方


class RunResponse(BaseModel):  # 定义类 RunResponse，组织相关状态与行为
    model_config = ConfigDict(from_attributes=True)  # 计算 ConfigDict(from_attributes=True) 并保存到变量 model_config

    id: UUID  # 声明或继续传入参数 id: UUID
    session_id: UUID  # 声明或继续传入参数 session_id: UUID
    status: RunStatus  # 声明或继续传入参数 status: RunStatus
    query: str  # 声明或继续传入参数 query: str
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
    version: int  # 声明或继续传入参数 version: int
    created_at: datetime  # 声明或继续传入参数 created_at: datetime
    started_at: datetime | None  # 声明或继续传入参数 started_at: datetime | None
    completed_at: datetime | None  # 声明或继续传入参数 completed_at: datetime | None
    updated_at: datetime  # 声明或继续传入参数 updated_at: datetime


class InterventionResponse(BaseModel):  # 定义类 InterventionResponse，组织相关状态与行为
    model_config = ConfigDict(from_attributes=True)  # 计算 ConfigDict(from_attributes=True) 并保存到变量 model_config

    id: UUID  # 声明或继续传入参数 id: UUID
    run_id: UUID  # 声明或继续传入参数 run_id: UUID
    kind: InterventionKind  # 声明或继续传入参数 kind: InterventionKind
    status: InterventionStatus  # 声明或继续传入参数 status: InterventionStatus
    payload: dict[str, Any]  # 声明或继续传入参数 payload: dict[str, Any]
    decision_data: dict[str, Any] | None = None  # 计算 None 并保存到变量 decision_data
    version: int  # 声明或继续传入参数 version: int
    requested_at: datetime  # 声明或继续传入参数 requested_at: datetime
    expires_at: datetime  # 声明或继续传入参数 expires_at: datetime
    decision: DecisionAction | None  # 声明或继续传入参数 decision: DecisionAction | None
    actor_id: str | None  # 声明或继续传入参数 actor_id: str | None
    responded_at: datetime | None  # 声明或继续传入参数 responded_at: datetime | None


class InterventionDecisionRequest(BaseModel):  # 定义类 InterventionDecisionRequest，组织相关状态与行为
    expected_version: int = Field(ge=1)  # 计算 Field(ge=1) 并保存到变量 expected_version
    action: Literal["select", "approve", "edit", "reject"]  # 声明或继续传入参数 action: Literal["select", "approve", "edit", "reject"]
    agent_id: str | None = Field(  # 调用 Field 构造结果并保存到 agent_id
        default=None, pattern=r"^[a-z][a-z0-9_]{2,63}$"  # 为 Field 设置关键字参数 default，传入当前行给出的值
    )  # 结束 Field 调用参数，得到完整表达式结果
    edited_sql: str | None = Field(default=None, max_length=50_000)  # 计算 Field(default=None, max_length=50_000) 并保存到变量 edited_sql
    reason: str | None = Field(default=None, max_length=2000)  # 计算 Field(default=None, max_length=2000) 并保存到变量 reason

    def payload(self) -> dict[str, Any]:  # 定义函数 payload，封装该模块的一项明确职责
        return {  # 返回 { 给调用方
            "agent_id": self.agent_id,  # 为多行字典定义键 "agent_id" 及其对应值
            "edited_sql": self.edited_sql,  # 为多行字典定义键 "edited_sql" 及其对应值
            "reason": self.reason,  # 为多行字典定义键 "reason" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰


class ProblemDetail(BaseModel):  # 定义类 ProblemDetail，组织相关状态与行为
    type: str = "about:blank"  # 计算 "about:blank" 并保存到变量 type
    title: str  # 声明或继续传入参数 title: str
    status: int  # 声明或继续传入参数 status: int
    detail: str  # 声明或继续传入参数 detail: str
    code: str  # 声明或继续传入参数 code: str
    request_id: str  # 声明或继续传入参数 request_id: str
    trace_id: str | None = None  # 计算 None 并保存到变量 trace_id
    retryable: bool = False  # 计算 False 并保存到变量 retryable
    details: dict[str, Any] = Field(default_factory=dict)  # 计算 Field(default_factory=dict) 并保存到变量 details
