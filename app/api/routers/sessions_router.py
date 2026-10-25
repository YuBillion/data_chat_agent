"""Session lifecycle API."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from typing import Annotated  # 从 typing 导入 Annotated，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from fastapi import APIRouter, Depends, Query, Response, status  # 从 fastapi 导入 APIRouter, Depends, Query, Response, status，供本模块后续代码使用

from app.api.dependencies_v1 import get_run_service  # 从 app.api.dependencies_v1 导入 get_run_service，供本模块后续代码使用
from app.api.schemas.v1 import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    SessionCreateRequest,  # 从当前 import 模块导入符号 SessionCreateRequest
    SessionDetailResponse,  # 从当前 import 模块导入符号 SessionDetailResponse
    SessionListItem,  # 从当前 import 模块导入符号 SessionListItem
    SessionListResponse,  # 从当前 import 模块导入符号 SessionListResponse
    SessionResponse,  # 从当前 import 模块导入符号 SessionResponse
)  # 结束多符号导入列表
from app.auth.oidc import require_user  # 从 app.auth.oidc 导入 require_user，供本模块后续代码使用
from app.harness.service import RunService  # 从 app.harness.service 导入 RunService，供本模块后续代码使用
from app.harness.types import Identity  # 从 app.harness.types 导入 Identity，供本模块后续代码使用

sessions_router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])  # 计算 APIRouter(prefix="/api/v1/sessions", tags=["sessions"]) 并保存到变量 sessions_router


@sessions_router.post(  # 应用装饰器 sessions_router.post(，为紧随其后的定义附加框架行为
    "", response_model=SessionResponse, status_code=status.HTTP_201_CREATED  # 执行源码表达式 "", response_model=SessionResponse, status_code=status.HTTP_201_CREATED，完成本行对应的语义动作
)  # 结束 sessions_router.post 调用参数，得到完整表达式结果
async def create_session(  # 定义异步函数 create_session，封装可被事件循环调度的协程逻辑
    body: SessionCreateRequest,  # 为函数 create_session 声明参数 body 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 create_session 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 create_session 声明参数 service 及其类型或默认值
) -> SessionResponse:  # 结束 create_session 的参数列表并声明返回类型
    record = await service.create_session(identity, body.title)  # 等待 create_session 完成，并将其结果保存到 record
    return SessionResponse.model_validate(record)  # 返回 SessionResponse.model_validate(record) 给调用方


@sessions_router.get("", response_model=SessionListResponse)  # 应用装饰器 sessions_router.get("", response_model=SessionListResponse)，为紧随其后的定义附加框架行为
async def list_sessions(  # 定义异步函数 list_sessions，封装可被事件循环调度的协程逻辑
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 list_sessions 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 list_sessions 声明参数 service 及其类型或默认值
    limit: Annotated[int, Query(ge=1, le=100)] = 20,  # 为函数 list_sessions 声明参数 limit 及其类型或默认值
    cursor: str | None = None,  # 为函数 list_sessions 声明参数 cursor 及其类型或默认值
) -> SessionListResponse:  # 结束 list_sessions 的参数列表并声明返回类型
    records, next_cursor = await service.list_sessions(  # 等待 list_sessions 完成，并将其结果保存到 records, next_cursor
        identity, limit=limit, cursor=cursor  # 在函数 list_sessions 中执行表达式 identity, limit=limit, cursor=cursor，推进当前业务流程
    )  # 结束函数 list_sessions 的参数及返回类型声明并开始函数体
    return SessionListResponse(  # 返回 SessionListResponse( 给调用方
        items=[SessionListItem.model_validate(record) for record in records],  # 为 SessionListItem.model_validate 设置关键字参数 items，传入当前行给出的值
        next_cursor=next_cursor,  # 为 SessionListResponse 设置关键字参数 next_cursor，传入当前行给出的值
    )  # 结束函数 list_sessions 的参数及返回类型声明并开始函数体


@sessions_router.get("/{session_id}", response_model=SessionDetailResponse)  # 应用装饰器 sessions_router.get("/{session_id}", response_model=SessionDetailRespon…，为紧随其后的定义附加框架行为
async def get_session(  # 定义异步函数 get_session，封装可被事件循环调度的协程逻辑
    session_id: UUID,  # 为函数 get_session 声明参数 session_id 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 get_session 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 get_session 声明参数 service 及其类型或默认值
) -> SessionDetailResponse:  # 结束 get_session 的参数列表并声明返回类型
    snapshot = await service.get_session_view(identity, session_id)  # 等待 get_session_view 完成，并将其结果保存到 snapshot
    return SessionDetailResponse.model_validate(snapshot)  # 返回 SessionDetailResponse.model_validate(snapshot) 给调用方


@sessions_router.delete(  # 应用装饰器 sessions_router.delete(，为紧随其后的定义附加框架行为
    "/{session_id}", status_code=status.HTTP_204_NO_CONTENT  # 执行源码表达式 "/{session_id}", status_code=status.HTTP_204_NO_CONTENT，完成本行对应的语义动作
)  # 结束 sessions_router.delete 调用参数，得到完整表达式结果
async def delete_session(  # 定义异步函数 delete_session，封装可被事件循环调度的协程逻辑
    session_id: UUID,  # 为函数 delete_session 声明参数 session_id 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 delete_session 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 delete_session 声明参数 service 及其类型或默认值
) -> Response:  # 结束 delete_session 的参数列表并声明返回类型
    await service.delete_session(identity, session_id)  # 等待异步操作完成并取得结果：service.delete_session(identity, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)  # 返回 Response(status_code=status.HTTP_204_NO_CONTENT) 给调用方
