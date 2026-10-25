"""Contracts shared by registered agents and the router."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from collections.abc import Callable  # 从 collections.abc 导入 Callable，供本模块后续代码使用
from dataclasses import dataclass, field  # 从 dataclasses 导入 dataclass, field，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用

from pydantic import BaseModel, ConfigDict, Field  # 从 pydantic 导入 BaseModel, ConfigDict, Field，供本模块后续代码使用

from app.harness.types import RouteMode  # 从 app.harness.types 导入 RouteMode，供本模块后续代码使用


@dataclass(frozen=True, slots=True)  # 应用装饰器 dataclass(frozen=True, slots=True)，为紧随其后的定义附加框架行为
class AgentDefinition:  # 定义类 AgentDefinition，组织相关状态与行为
    agent_id: str  # 声明或继续传入参数 agent_id: str
    version: str  # 声明或继续传入参数 version: str
    display_name: str  # 声明或继续传入参数 display_name: str
    description: str  # 声明或继续传入参数 description: str
    capabilities: tuple[str, ...]  # 声明或继续传入参数 capabilities: tuple[str, ...]
    state_schema_version: str  # 声明或继续传入参数 state_schema_version: str
    prompt_ids: tuple[str, ...]  # 声明或继续传入参数 prompt_ids: tuple[str, ...]
    graph_factory: Callable[[], Any]  # 声明或继续传入参数 graph_factory: Callable[[], Any]
    allowed_tools: frozenset[str]  # 声明或继续传入参数 allowed_tools: frozenset[str]
    model_profile: str  # 声明或继续传入参数 model_profile: str
    policy_profile: str  # 声明或继续传入参数 policy_profile: str
    default_priority: int = 100  # 计算 100 并保存到变量 default_priority
    enabled: bool = True  # 计算 True 并保存到变量 enabled

    def public_view(self) -> "AgentPublicView":  # 定义函数 public_view，封装该模块的一项明确职责
        return AgentPublicView(  # 返回 AgentPublicView( 给调用方
            agent_id=self.agent_id,  # 为 AgentPublicView 设置关键字参数 agent_id，传入当前行给出的值
            version=self.version,  # 为 AgentPublicView 设置关键字参数 version，传入当前行给出的值
            display_name=self.display_name,  # 为 AgentPublicView 设置关键字参数 display_name，传入当前行给出的值
            description=self.description,  # 为 AgentPublicView 设置关键字参数 description，传入当前行给出的值
            capabilities=list(self.capabilities),  # 为 list 设置关键字参数 capabilities，传入当前行给出的值
            response_types=["text", "structured"],  # 为 AgentPublicView 设置关键字参数 response_types，传入当前行给出的值
        )  # 结束函数 public_view 的参数及返回类型声明并开始函数体


class AgentPublicView(BaseModel):  # 定义类 AgentPublicView，组织相关状态与行为
    model_config = ConfigDict(extra="forbid")  # 计算 ConfigDict(extra="forbid") 并保存到变量 model_config

    agent_id: str  # 声明或继续传入参数 agent_id: str
    version: str  # 声明或继续传入参数 version: str
    display_name: str  # 声明或继续传入参数 display_name: str
    description: str  # 声明或继续传入参数 description: str
    capabilities: list[str]  # 声明或继续传入参数 capabilities: list[str]
    response_types: list[str]  # 声明或继续传入参数 response_types: list[str]


class RouteCandidate(BaseModel):  # 定义类 RouteCandidate，组织相关状态与行为
    model_config = ConfigDict(extra="forbid")  # 计算 ConfigDict(extra="forbid") 并保存到变量 model_config

    agent_id: str  # 声明或继续传入参数 agent_id: str
    confidence: float = Field(ge=0, le=1)  # 计算 Field(ge=0, le=1) 并保存到变量 confidence
    reason: str  # 声明或继续传入参数 reason: str


class RouterModelOutput(BaseModel):  # 定义类 RouterModelOutput，组织相关状态与行为
    model_config = ConfigDict(extra="forbid")  # 计算 ConfigDict(extra="forbid") 并保存到变量 model_config

    agent_id: str  # 声明或继续传入参数 agent_id: str
    confidence: float = Field(ge=0, le=1)  # 计算 Field(ge=0, le=1) 并保存到变量 confidence
    alternatives: list[RouteCandidate] = Field(default_factory=list)  # 计算 Field(default_factory=list) 并保存到变量 alternatives
    reason_code: str  # 声明或继续传入参数 reason_code: str
    resolved_query: str  # 声明或继续传入参数 resolved_query: str


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class RouteDecision:  # 定义类 RouteDecision，组织相关状态与行为
    selected_agent_id: str | None  # 声明或继续传入参数 selected_agent_id: str | None
    mode: RouteMode  # 声明或继续传入参数 mode: RouteMode
    confidence: float | None  # 声明或继续传入参数 confidence: float | None
    candidates: list[RouteCandidate]  # 声明或继续传入参数 candidates: list[RouteCandidate]
    reason_code: str  # 声明或继续传入参数 reason_code: str
    resolved_query: str  # 声明或继续传入参数 resolved_query: str
    requires_human: bool = False  # 计算 False 并保存到变量 requires_human
    alternative_payload: dict[str, Any] = field(default_factory=dict)  # 计算 field(default_factory=dict) 并保存到变量 alternative_payload

    def as_dict(self) -> dict[str, Any]:  # 定义函数 as_dict，封装该模块的一项明确职责
        return {  # 返回 { 给调用方
            "selected_agent_id": self.selected_agent_id,  # 为多行字典定义键 "selected_agent_id" 及其对应值
            "mode": self.mode.value,  # 为多行字典定义键 "mode" 及其对应值
            "confidence": self.confidence,  # 为多行字典定义键 "confidence" 及其对应值
            "candidates": [  # 为多行字典定义键 "candidates" 及其对应值
                candidate.model_dump() for candidate in self.candidates  # 调用 model_dump 执行当前步骤：candidate.model_dump() for candidate in self.candidates
            ],  # 结束上一处多行结构，保持表达式边界清晰
            "reason_code": self.reason_code,  # 为多行字典定义键 "reason_code" 及其对应值
            "resolved_query": self.resolved_query,  # 为多行字典定义键 "resolved_query" 及其对应值
            "requires_human": self.requires_human,  # 为多行字典定义键 "requires_human" 及其对应值
            **self.alternative_payload,  # 向多行字典加入配置项 **self.alternative_payload
        }  # 结束上一处多行结构，保持表达式边界清晰
