"""Shared harness enums, identity objects, events, and execution budgets."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import time  # 导入time，建立本模块需要的外部能力引用
from dataclasses import dataclass, field  # 从 dataclasses 导入 dataclass, field，供本模块后续代码使用
from datetime import UTC, datetime  # 从 datetime 导入 UTC, datetime，供本模块后续代码使用
from enum import StrEnum  # 从 enum 导入 StrEnum，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from pydantic import BaseModel, ConfigDict, Field  # 从 pydantic 导入 BaseModel, ConfigDict, Field，供本模块后续代码使用

from app.core.errors import BudgetExceededError  # 从 app.core.errors 导入 BudgetExceededError，供本模块后续代码使用


def utc_now() -> datetime:  # 定义函数 utc_now，封装该模块的一项明确职责
    return datetime.now(UTC)  # 返回 datetime.now(UTC) 给调用方


class RunStatus(StrEnum):  # 定义类 RunStatus，组织相关状态与行为
    QUEUED = "queued"  # 计算 "queued" 并保存到变量 QUEUED
    RUNNING = "running"  # 计算 "running" 并保存到变量 RUNNING
    WAITING_HUMAN = "waiting_human"  # 计算 "waiting_human" 并保存到变量 WAITING_HUMAN
    COMPLETED = "completed"  # 计算 "completed" 并保存到变量 COMPLETED
    REJECTED = "rejected"  # 计算 "rejected" 并保存到变量 REJECTED
    FAILED = "failed"  # 计算 "failed" 并保存到变量 FAILED
    CANCELLED = "cancelled"  # 计算 "cancelled" 并保存到变量 CANCELLED
    EXPIRED = "expired"  # 计算 "expired" 并保存到变量 EXPIRED


TERMINAL_RUN_STATUSES = frozenset(  # 调用 frozenset 构造结果并保存到 TERMINAL_RUN_STATUSES
    {  # 执行源码表达式 {，完成本行对应的语义动作
        RunStatus.COMPLETED,  # 向多行序列加入元素 RunStatus.COMPLETED
        RunStatus.REJECTED,  # 向多行序列加入元素 RunStatus.REJECTED
        RunStatus.FAILED,  # 向多行序列加入元素 RunStatus.FAILED
        RunStatus.CANCELLED,  # 向多行序列加入元素 RunStatus.CANCELLED
        RunStatus.EXPIRED,  # 向多行序列加入元素 RunStatus.EXPIRED
    }  # 结束上一处多行结构，保持表达式边界清晰
)  # 结束 frozenset 调用参数，得到完整表达式结果


class JobType(StrEnum):  # 定义类 JobType，组织相关状态与行为
    START = "start"  # 计算 "start" 并保存到变量 START
    RESUME = "resume"  # 计算 "resume" 并保存到变量 RESUME


class JobStatus(StrEnum):  # 定义类 JobStatus，组织相关状态与行为
    QUEUED = "queued"  # 计算 "queued" 并保存到变量 QUEUED
    LEASED = "leased"  # 计算 "leased" 并保存到变量 LEASED
    COMPLETED = "completed"  # 计算 "completed" 并保存到变量 COMPLETED
    FAILED = "failed"  # 计算 "failed" 并保存到变量 FAILED
    CANCELLED = "cancelled"  # 计算 "cancelled" 并保存到变量 CANCELLED


class InterventionKind(StrEnum):  # 定义类 InterventionKind，组织相关状态与行为
    AGENT_SELECTION = "agent_selection"  # 计算 "agent_selection" 并保存到变量 AGENT_SELECTION
    SQL_APPROVAL = "sql_approval"  # 计算 "sql_approval" 并保存到变量 SQL_APPROVAL


class InterventionStatus(StrEnum):  # 定义类 InterventionStatus，组织相关状态与行为
    PENDING = "pending"  # 计算 "pending" 并保存到变量 PENDING
    RESPONDED = "responded"  # 计算 "responded" 并保存到变量 RESPONDED
    EXPIRED = "expired"  # 计算 "expired" 并保存到变量 EXPIRED
    CANCELLED = "cancelled"  # 计算 "cancelled" 并保存到变量 CANCELLED


class DecisionAction(StrEnum):  # 定义类 DecisionAction，组织相关状态与行为
    SELECT = "select"  # 计算 "select" 并保存到变量 SELECT
    APPROVE = "approve"  # 计算 "approve" 并保存到变量 APPROVE
    EDIT = "edit"  # 计算 "edit" 并保存到变量 EDIT
    REJECT = "reject"  # 计算 "reject" 并保存到变量 REJECT


class RouteMode(StrEnum):  # 定义类 RouteMode，组织相关状态与行为
    EXPLICIT = "explicit"  # 计算 "explicit" 并保存到变量 EXPLICIT
    RULE = "rule"  # 计算 "rule" 并保存到变量 RULE
    MODEL = "model"  # 计算 "model" 并保存到变量 MODEL
    USER = "user"  # 计算 "user" 并保存到变量 USER


@dataclass(frozen=True, slots=True)  # 应用装饰器 dataclass(frozen=True, slots=True)，为紧随其后的定义附加框架行为
class Identity:  # 定义类 Identity，组织相关状态与行为
    user_id: str  # 声明或继续传入参数 user_id: str
    tenant_id: str  # 声明或继续传入参数 tenant_id: str
    roles: frozenset[str]  # 声明或继续传入参数 roles: frozenset[str]
    raw_claims: dict[str, Any] = field(default_factory=dict)  # 计算 field(default_factory=dict) 并保存到变量 raw_claims

    def has_role(self, role: str) -> bool:  # 定义函数 has_role，封装该模块的一项明确职责
        return role in self.roles  # 返回 role in self.roles 给调用方


class RunBudgetSnapshot(BaseModel):  # 定义类 RunBudgetSnapshot，组织相关状态与行为
    model_config = ConfigDict(extra="forbid")  # 计算 ConfigDict(extra="forbid") 并保存到变量 model_config

    llm_calls: int = 0  # 计算 0 并保存到变量 llm_calls
    input_tokens: int = 0  # 计算 0 并保存到变量 input_tokens
    output_tokens: int = 0  # 计算 0 并保存到变量 output_tokens
    active_seconds: float = 0  # 计算 0 并保存到变量 active_seconds


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class RunBudget:  # 定义类 RunBudget，组织相关状态与行为
    """Mutable budget shared by router and agent calls for one run."""

    max_llm_calls: int  # 声明或继续传入参数 max_llm_calls: int
    max_tokens: int  # 声明或继续传入参数 max_tokens: int
    max_active_seconds: float  # 声明或继续传入参数 max_active_seconds: float
    snapshot: RunBudgetSnapshot = field(default_factory=RunBudgetSnapshot)  # 计算 field(default_factory=RunBudgetSnapshot) 并保存到变量 snapshot
    _active_started_at: float | None = None  # 计算 None 并保存到变量 _active_started_at
    _accumulated_seconds: float = 0.0  # 计算 0.0 并保存到变量 _accumulated_seconds

    @classmethod  # 应用装饰器 classmethod，为紧随其后的定义附加框架行为
    def from_snapshot(  # 定义函数 from_snapshot，封装该模块的一项明确职责
        cls,  # 为函数 from_snapshot 声明参数 cls 及其类型或默认值
        snapshot: RunBudgetSnapshot,  # 为函数 from_snapshot 声明参数 snapshot 及其类型或默认值
        *,  # 为函数 from_snapshot 声明参数 * 及其类型或默认值
        max_llm_calls: int,  # 为函数 from_snapshot 声明参数 max_llm_calls 及其类型或默认值
        max_tokens: int,  # 为函数 from_snapshot 声明参数 max_tokens 及其类型或默认值
        max_active_seconds: float,  # 为函数 from_snapshot 声明参数 max_active_seconds 及其类型或默认值
    ) -> "RunBudget":  # 结束 from_snapshot 的参数列表并声明返回类型
        budget = cls(  # 调用 cls 构造结果并保存到 budget
            max_llm_calls=max_llm_calls,  # 为 cls 设置关键字参数 max_llm_calls，传入当前行给出的值
            max_tokens=max_tokens,  # 为 cls 设置关键字参数 max_tokens，传入当前行给出的值
            max_active_seconds=max_active_seconds,  # 为 cls 设置关键字参数 max_active_seconds，传入当前行给出的值
            snapshot=snapshot,  # 为 cls 设置关键字参数 snapshot，传入当前行给出的值
        )  # 结束 cls 调用参数，得到完整表达式结果
        budget._accumulated_seconds = snapshot.active_seconds  # 计算 snapshot.active_seconds 并保存到变量 budget._accumulated_seconds
        return budget  # 返回 budget 给调用方

    def start_clock(self) -> None:  # 定义函数 start_clock，封装该模块的一项明确职责
        if self._active_started_at is None:  # 判断分支条件：if self._active_started_at is None:
            self._active_started_at = time.monotonic()  # 将 time.monotonic() 保存到实例属性 self._active_started_at

    def pause_clock(self) -> None:  # 定义函数 pause_clock，封装该模块的一项明确职责
        if self._active_started_at is None:  # 判断分支条件：if self._active_started_at is None:
            return  # 提前返回空结果，结束当前函数调用
        self._accumulated_seconds += time.monotonic() - self._active_started_at  # 将 time.monotonic() - self._active_started_at 保存到实例属性 self._accumulated_seconds +
        self._active_started_at = None  # 将 None 保存到实例属性 self._active_started_at
        self.snapshot.active_seconds = round(self._accumulated_seconds, 3)  # 将 round(self._accumulated_seconds, 3) 保存到实例属性 self.snapshot.active_seconds

    def check_active_time(self) -> None:  # 定义函数 check_active_time，封装该模块的一项明确职责
        elapsed = self._accumulated_seconds  # 计算 self._accumulated_seconds 并保存到变量 elapsed
        if self._active_started_at is not None:  # 判断分支条件：if self._active_started_at is not None:
            elapsed += time.monotonic() - self._active_started_at  # 计算 time.monotonic() - self._active_started_at 并保存到变量 elapsed +
        if elapsed > self.max_active_seconds:  # 判断分支条件：if elapsed > self.max_active_seconds:
            raise BudgetExceededError("active_seconds")  # 抛出明确异常，阻止错误状态被静默接受：BudgetExceededError("active_seconds")

    def before_llm_call(self) -> None:  # 定义函数 before_llm_call，封装该模块的一项明确职责
        self.check_active_time()  # 调用 check_active_time 执行当前步骤：self.check_active_time()
        if self.snapshot.llm_calls >= self.max_llm_calls:  # 判断分支条件：if self.snapshot.llm_calls >= self.max_llm_calls:
            raise BudgetExceededError("llm_calls")  # 抛出明确异常，阻止错误状态被静默接受：BudgetExceededError("llm_calls")
        if self.total_tokens >= self.max_tokens:  # 判断分支条件：if self.total_tokens >= self.max_tokens:
            raise BudgetExceededError("tokens")  # 抛出明确异常，阻止错误状态被静默接受：BudgetExceededError("tokens")

    def record_llm_call(self, input_tokens: int = 0, output_tokens: int = 0) -> None:  # 定义函数 record_llm_call，封装该模块的一项明确职责
        self.snapshot.llm_calls += 1  # 将 1 保存到实例属性 self.snapshot.llm_calls +
        self.snapshot.input_tokens += max(input_tokens, 0)  # 将 max(input_tokens, 0) 保存到实例属性 self.snapshot.input_tokens +
        self.snapshot.output_tokens += max(output_tokens, 0)  # 将 max(output_tokens, 0) 保存到实例属性 self.snapshot.output_tokens +
        if self.total_tokens > self.max_tokens:  # 判断分支条件：if self.total_tokens > self.max_tokens:
            raise BudgetExceededError("tokens")  # 抛出明确异常，阻止错误状态被静默接受：BudgetExceededError("tokens")

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def total_tokens(self) -> int:  # 定义函数 total_tokens，封装该模块的一项明确职责
        return self.snapshot.input_tokens + self.snapshot.output_tokens  # 返回 self.snapshot.input_tokens + self.snapshot.output_tokens 给调用方


class EventEnvelope(BaseModel):  # 定义类 EventEnvelope，组织相关状态与行为
    model_config = ConfigDict(extra="forbid")  # 计算 ConfigDict(extra="forbid") 并保存到变量 model_config

    schema_version: str = "1.0"  # 计算 "1.0" 并保存到变量 schema_version
    run_id: UUID  # 声明或继续传入参数 run_id: UUID
    seq: int = Field(ge=1)  # 计算 Field(ge=1) 并保存到变量 seq
    trace_id: str | None = None  # 计算 None 并保存到变量 trace_id
    occurred_at: datetime  # 声明或继续传入参数 occurred_at: datetime
    event_type: str  # 声明或继续传入参数 event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)  # 计算 Field(default_factory=dict) 并保存到变量 payload


def event_type_from_chunk(chunk: Any) -> str:  # 定义函数 event_type_from_chunk，封装该模块的一项明确职责
    if not isinstance(chunk, dict):  # 判断分支条件：if not isinstance(chunk, dict):
        return "node.progress"  # 返回 "node.progress" 给调用方
    raw_type = str(chunk.get("type", "node.progress"))  # 计算 str(chunk.get("type", "node.progress")) 并保存到变量 raw_type
    mapping = {  # 计算 { 并保存到变量 mapping
        "progress": "node.progress",  # 为多行字典定义键 "progress" 及其对应值
        "result": "agent.result",  # 为多行字典定义键 "result" 及其对应值
        "error": "run.failed",  # 为多行字典定义键 "error" 及其对应值
        "agent.selected": "agent.selected",  # 为多行字典定义键 "agent.selected" 及其对应值
        "agent.selection_required": "agent.selection_required",  # 为多行字典定义键 "agent.selection_required" 及其对应值
        "sql.approval_required": "sql.approval_required",  # 为多行字典定义键 "sql.approval_required" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰
    return mapping.get(raw_type, raw_type)  # 返回 mapping.get(raw_type, raw_type) 给调用方
