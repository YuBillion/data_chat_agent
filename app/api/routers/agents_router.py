"""Agent registry API."""

from typing import Annotated  # 从 typing 导入 Annotated，供本模块后续代码使用

from fastapi import APIRouter, Depends  # 从 fastapi 导入 APIRouter, Depends，供本模块后续代码使用

from app.api.dependencies_v1 import get_run_service  # 从 app.api.dependencies_v1 导入 get_run_service，供本模块后续代码使用
from app.api.schemas.v1 import AgentResponse  # 从 app.api.schemas.v1 导入 AgentResponse，供本模块后续代码使用
from app.auth.oidc import require_user  # 从 app.auth.oidc 导入 require_user，供本模块后续代码使用
from app.harness.service import RunService  # 从 app.harness.service 导入 RunService，供本模块后续代码使用
from app.harness.types import Identity  # 从 app.harness.types 导入 Identity，供本模块后续代码使用

agents_router = APIRouter(prefix="/api/v1/agents", tags=["agents"])  # 计算 APIRouter(prefix="/api/v1/agents", tags=["agents"]) 并保存到变量 agents_router


@agents_router.get("", response_model=list[AgentResponse])  # 应用装饰器 agents_router.get("", response_model=list[AgentResponse])，为紧随其后的定义附加框架行为
async def list_agents(  # 定义异步函数 list_agents，封装可被事件循环调度的协程逻辑
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 list_agents 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 list_agents 声明参数 service 及其类型或默认值
) -> list[AgentResponse]:  # 结束 list_agents 的参数列表并声明返回类型
    return [  # 返回 [ 给调用方
        AgentResponse.model_validate(item.model_dump())  # 调用 model_validate 执行当前步骤：AgentResponse.model_validate(item.model_dump())
        for item in service.list_agents(identity)  # 按迭代条件执行循环：for item in service.list_agents(identity)
    ]  # 结束上一处多行结构，保持表达式边界清晰


@agents_router.get("/{agent_id}", response_model=AgentResponse)  # 应用装饰器 agents_router.get("/{agent_id}", response_model=AgentResponse)，为紧随其后的定义附加框架行为
async def get_agent(  # 定义异步函数 get_agent，封装可被事件循环调度的协程逻辑
    agent_id: str,  # 为函数 get_agent 声明参数 agent_id 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 get_agent 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 get_agent 声明参数 service 及其类型或默认值
) -> AgentResponse:  # 结束 get_agent 的参数列表并声明返回类型
    return AgentResponse.model_validate(  # 返回 AgentResponse.model_validate( 给调用方
        service.get_agent(identity, agent_id).model_dump()  # 调用 get_agent 执行当前步骤：service.get_agent(identity, agent_id).model_dump()
    )  # 结束函数 get_agent 的参数及返回类型声明并开始函数体
