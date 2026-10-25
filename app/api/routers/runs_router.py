"""Durable run and SSE API."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from typing import Annotated  # 从 typing 导入 Annotated，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from fastapi import APIRouter, Depends, Header, Query, Request, status  # 从 fastapi 导入 APIRouter, Depends, Header, Query, Request, status，供本模块后续代码使用
from starlette.responses import StreamingResponse  # 从 starlette.responses 导入 StreamingResponse，供本模块后续代码使用

from app.api.dependencies_v1 import get_container, get_run_service  # 从 app.api.dependencies_v1 导入 get_container, get_run_service，供本模块后续代码使用
from app.api.schemas.v1 import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    InterventionResponse,  # 从当前 import 模块导入符号 InterventionResponse
    RunCreateRequest,  # 从当前 import 模块导入符号 RunCreateRequest
    RunResponse,  # 从当前 import 模块导入符号 RunResponse
)  # 结束多符号导入列表
from app.application import ApplicationContainer  # 从 app.application 导入 ApplicationContainer，供本模块后续代码使用
from app.auth.oidc import require_user  # 从 app.auth.oidc 导入 require_user，供本模块后续代码使用
from app.core.errors import AppError  # 从 app.core.errors 导入 AppError，供本模块后续代码使用
from app.harness.service import RunService  # 从 app.harness.service 导入 RunService，供本模块后续代码使用
from app.harness.types import Identity  # 从 app.harness.types 导入 Identity，供本模块后续代码使用

runs_router = APIRouter(prefix="/api/v1", tags=["runs"])  # 计算 APIRouter(prefix="/api/v1", tags=["runs"]) 并保存到变量 runs_router


@runs_router.post(  # 应用装饰器 runs_router.post(，为紧随其后的定义附加框架行为
    "/sessions/{session_id}/runs",  # 继续向上一处调用或声明传入 "/sessions/{session_id}/runs"
    response_model=RunResponse,  # 为 runs_router.post 设置关键字参数 response_model，传入当前行给出的值
    status_code=status.HTTP_202_ACCEPTED,  # 为 runs_router.post 设置关键字参数 status_code，传入当前行给出的值
)  # 结束 runs_router.post 调用参数，得到完整表达式结果
async def create_run(  # 定义异步函数 create_run，封装可被事件循环调度的协程逻辑
    session_id: UUID,  # 为函数 create_run 声明参数 session_id 及其类型或默认值
    body: RunCreateRequest,  # 为函数 create_run 声明参数 body 及其类型或默认值
    idempotency_key: Annotated[  # 为函数 create_run 声明参数 idempotency_key 及其类型或默认值
        str,  # 向多行序列加入元素 str
        Header(  # 为函数 create_run 声明参数 Header( 及其类型或默认值
            alias="Idempotency-Key",  # 为函数 create_run 声明参数 alias 及其类型或默认值
            min_length=1,  # 为函数 create_run 声明参数 min_length 及其类型或默认值
            max_length=128,  # 为函数 create_run 声明参数 max_length 及其类型或默认值
        ),  # 结束函数 create_run 的参数及返回类型声明并开始函数体
    ],  # 为函数 create_run 声明参数 ] 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 create_run 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 create_run 声明参数 service 及其类型或默认值
    container: Annotated[ApplicationContainer, Depends(get_container)],  # 为函数 create_run 声明参数 container 及其类型或默认值
) -> RunResponse:  # 结束 create_run 的参数列表并声明返回类型
    if len(body.query) > container.settings.max_query_chars:  # 判断分支条件：if len(body.query) > container.settings.max_query_chars:
        raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
            code="QUERY_TOO_LONG",  # 为 AppError 设置关键字参数 code，传入当前行给出的值
            message="query exceeds the configured limit",  # 为 AppError 设置关键字参数 message，传入当前行给出的值
            status_code=422,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
            details={"max_length": container.settings.max_query_chars},  # 为 AppError 设置关键字参数 details，传入当前行给出的值
        )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
    record = await service.create_run(  # 等待 create_run 完成，并将其结果保存到 record
        identity,  # 继续向上一处调用或声明传入 identity
        session_id=session_id,  # 为 service.create_run 设置关键字参数 session_id，传入当前行给出的值
        query=body.query,  # 为 service.create_run 设置关键字参数 query，传入当前行给出的值
        requested_agent_id=body.agent_id,  # 为 service.create_run 设置关键字参数 requested_agent_id，传入当前行给出的值
        idempotency_key=idempotency_key,  # 为 service.create_run 设置关键字参数 idempotency_key，传入当前行给出的值
    )  # 结束函数 create_run 的参数及返回类型声明并开始函数体
    return RunResponse.model_validate(record)  # 返回 RunResponse.model_validate(record) 给调用方


@runs_router.get("/runs/{run_id}", response_model=RunResponse)  # 应用装饰器 runs_router.get("/runs/{run_id}", response_model=RunResponse)，为紧随其后的定义附加框架行为
async def get_run(  # 定义异步函数 get_run，封装可被事件循环调度的协程逻辑
    run_id: UUID,  # 为函数 get_run 声明参数 run_id 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 get_run 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 get_run 声明参数 service 及其类型或默认值
) -> RunResponse:  # 结束 get_run 的参数列表并声明返回类型
    return RunResponse.model_validate(await service.get_run(identity, run_id))  # 返回 RunResponse.model_validate(await service.get_run(identity, run_id)) 给调用方


@runs_router.post("/runs/{run_id}/cancel", response_model=RunResponse)  # 应用装饰器 runs_router.post("/runs/{run_id}/cancel", response_model=RunResponse)，为紧随其后的定义附加框架行为
async def cancel_run(  # 定义异步函数 cancel_run，封装可被事件循环调度的协程逻辑
    run_id: UUID,  # 为函数 cancel_run 声明参数 run_id 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 cancel_run 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 cancel_run 声明参数 service 及其类型或默认值
) -> RunResponse:  # 结束 cancel_run 的参数列表并声明返回类型
    return RunResponse.model_validate(await service.cancel_run(identity, run_id))  # 返回 RunResponse.model_validate(await service.cancel_run(identity, run_id)) 给调用方


@runs_router.get(  # 应用装饰器 runs_router.get(，为紧随其后的定义附加框架行为
    "/runs/{run_id}/interventions",  # 继续向上一处调用或声明传入 "/runs/{run_id}/interventions"
    response_model=list[InterventionResponse],  # 为 runs_router.get 设置关键字参数 response_model，传入当前行给出的值
)  # 结束 runs_router.get 调用参数，得到完整表达式结果
async def list_interventions(  # 定义异步函数 list_interventions，封装可被事件循环调度的协程逻辑
    run_id: UUID,  # 为函数 list_interventions 声明参数 run_id 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 list_interventions 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 list_interventions 声明参数 service 及其类型或默认值
) -> list[InterventionResponse]:  # 结束 list_interventions 的参数列表并声明返回类型
    records = await service.list_interventions(identity, run_id)  # 等待 list_interventions 完成，并将其结果保存到 records
    return [  # 返回 [ 给调用方
        InterventionResponse(  # 调用 InterventionResponse 执行当前步骤：InterventionResponse(
            id=item.id,  # 为 InterventionResponse 设置关键字参数 id，传入当前行给出的值
            run_id=item.run_id,  # 为 InterventionResponse 设置关键字参数 run_id，传入当前行给出的值
            kind=item.kind,  # 为 InterventionResponse 设置关键字参数 kind，传入当前行给出的值
            status=item.status,  # 为 InterventionResponse 设置关键字参数 status，传入当前行给出的值
            payload=item.payload,  # 为 InterventionResponse 设置关键字参数 payload，传入当前行给出的值
            version=item.version,  # 为 InterventionResponse 设置关键字参数 version，传入当前行给出的值
            requested_at=item.requested_at,  # 为 InterventionResponse 设置关键字参数 requested_at，传入当前行给出的值
            expires_at=item.expires_at,  # 为 InterventionResponse 设置关键字参数 expires_at，传入当前行给出的值
            decision=item.decision,  # 为 InterventionResponse 设置关键字参数 decision，传入当前行给出的值
            actor_id=item.actor_id,  # 为 InterventionResponse 设置关键字参数 actor_id，传入当前行给出的值
            responded_at=item.responded_at,  # 为 InterventionResponse 设置关键字参数 responded_at，传入当前行给出的值
        )  # 结束函数 list_interventions 的参数及返回类型声明并开始函数体
        for item in records  # 按迭代条件执行循环：for item in records
    ]  # 结束上一处多行结构，保持表达式边界清晰


@runs_router.get("/runs/{run_id}/events")  # 应用装饰器 runs_router.get("/runs/{run_id}/events")，为紧随其后的定义附加框架行为
async def stream_run_events(  # 定义异步函数 stream_run_events，封装可被事件循环调度的协程逻辑
    run_id: UUID,  # 为函数 stream_run_events 声明参数 run_id 及其类型或默认值
    request: Request,  # 为函数 stream_run_events 声明参数 request 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 stream_run_events 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 stream_run_events 声明参数 service 及其类型或默认值
    after_seq: Annotated[int, Query(ge=0)] = 0,  # 为函数 stream_run_events 声明参数 after_seq 及其类型或默认值
    last_event_id: Annotated[  # 为函数 stream_run_events 声明参数 last_event_id 及其类型或默认值
        str | None,  # 向多行序列加入元素 str | None
        Header(alias="Last-Event-ID"),  # 向多行序列加入元素 Header(alias="Last-Event-ID")
    ] = None,  # 为函数 stream_run_events 声明参数 ] 及其类型或默认值
) -> StreamingResponse:  # 结束 stream_run_events 的参数列表并声明返回类型
    cursor = after_seq  # 计算 after_seq 并保存到变量 cursor
    if last_event_id:  # 判断分支条件：if last_event_id:
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            cursor = max(cursor, int(last_event_id))  # 计算 max(cursor, int(last_event_id)) 并保存到变量 cursor
        except ValueError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except ValueError as exc:
            raise AppError(  # 抛出明确异常，阻止错误状态被静默接受：AppError(
                code="INVALID_LAST_EVENT_ID",  # 为 AppError 设置关键字参数 code，传入当前行给出的值
                message="Last-Event-ID must be an integer",  # 为 AppError 设置关键字参数 message，传入当前行给出的值
                status_code=422,  # 为 AppError 设置关键字参数 status_code，传入当前行给出的值
            ) from exc  # 在函数 stream_run_events 中执行表达式 ) from exc，推进当前业务流程
    return StreamingResponse(  # 返回 StreamingResponse( 给调用方
        service.stream_run_events(  # 调用 stream_run_events 执行当前步骤：service.stream_run_events(
            identity,  # 继续向上一处调用或声明传入 identity
            run_id,  # 继续向上一处调用或声明传入 run_id
            after_seq=cursor,  # 为 service.stream_run_events 设置关键字参数 after_seq，传入当前行给出的值
            is_disconnected=request.is_disconnected,  # 为 service.stream_run_events 设置关键字参数 is_disconnected，传入当前行给出的值
        ),  # 结束函数 stream_run_events 的参数及返回类型声明并开始函数体
        media_type="text/event-stream",  # 为 StreamingResponse 设置关键字参数 media_type，传入当前行给出的值
        headers={  # 为 StreamingResponse 设置关键字参数 headers，传入当前行给出的值
            "Cache-Control": "no-cache, no-transform",  # 为多行字典定义键 "Cache-Control" 及其对应值
            "X-Accel-Buffering": "no",  # 为多行字典定义键 "X-Accel-Buffering" 及其对应值
        },  # 结束上一处多行结构，保持表达式边界清晰
    )  # 结束函数 stream_run_events 的参数及返回类型声明并开始函数体
