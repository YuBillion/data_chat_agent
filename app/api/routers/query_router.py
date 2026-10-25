"""Deprecated single-call SSE adapter backed by the durable harness."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import json  # 导入json，建立本模块需要的外部能力引用
from typing import Annotated  # 从 typing 导入 Annotated，供本模块后续代码使用
from uuid import uuid4  # 从 uuid 导入 uuid4，供本模块后续代码使用

from fastapi import APIRouter, Depends, Request  # 从 fastapi 导入 APIRouter, Depends, Request，供本模块后续代码使用
from starlette.responses import StreamingResponse  # 从 starlette.responses 导入 StreamingResponse，供本模块后续代码使用

from app.api.dependencies_v1 import get_container  # 从 app.api.dependencies_v1 导入 get_container，供本模块后续代码使用
from app.api.schemas.query_schema import QuerySchema  # 从 app.api.schemas.query_schema 导入 QuerySchema，供本模块后续代码使用
from app.application import ApplicationContainer  # 从 app.application 导入 ApplicationContainer，供本模块后续代码使用
from app.auth.oidc import require_user  # 从 app.auth.oidc 导入 require_user，供本模块后续代码使用
from app.harness.types import TERMINAL_RUN_STATUSES, Identity  # 从 app.harness.types 导入 TERMINAL_RUN_STATUSES, Identity，供本模块后续代码使用

query_router = APIRouter()  # 计算 APIRouter() 并保存到变量 query_router


@query_router.post(  # 应用装饰器 query_router.post(，为紧随其后的定义附加框架行为
    "/api/query",  # 继续向上一处调用或声明传入 "/api/query"
    deprecated=True,  # 为 query_router.post 设置关键字参数 deprecated，传入当前行给出的值
    description=(  # 为 query_router.post 设置关键字参数 description，传入当前行给出的值
        "Deprecated compatibility endpoint. Use /api/v1 sessions and runs "  # 执行源码表达式 "Deprecated compatibility endpoint. Use /api/v1 sessions and runs "，完成本行对应的语义动作
        "for resumable SSE and human-in-the-loop responses."  # 执行源码表达式 "for resumable SSE and human-in-the-loop responses."，完成本行对应的语义动作
    ),  # 结束上一处多行结构，保持表达式边界清晰
)  # 结束 query_router.post 调用参数，得到完整表达式结果
async def query_handler(  # 定义异步函数 query_handler，封装可被事件循环调度的协程逻辑
    query: QuerySchema,  # 为函数 query_handler 声明参数 query 及其类型或默认值
    request: Request,  # 为函数 query_handler 声明参数 request 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 query_handler 声明参数 identity 及其类型或默认值
    container: Annotated[ApplicationContainer, Depends(get_container)],  # 为函数 query_handler 声明参数 container 及其类型或默认值
):  # 结束 query_handler 的参数列表并声明返回类型
    session = await container.run_service.create_session(  # 等待 create_session 完成，并将其结果保存到 session
        identity, title=query.query[:80] or "临时问询"  # 在函数 query_handler 中执行表达式 identity, title=query.query[:80] or "临时问询"，推进当前业务流程
    )  # 结束函数 query_handler 的参数及返回类型声明并开始函数体
    run = await container.run_service.create_run(  # 等待 create_run 完成，并将其结果保存到 run
        identity,  # 继续向上一处调用或声明传入 identity
        session_id=session.id,  # 为 container.run_service.create_run 设置关键字参数 session_id，传入当前行给出的值
        query=query.query,  # 为 container.run_service.create_run 设置关键字参数 query，传入当前行给出的值
        requested_agent_id=None,  # 为 container.run_service.create_run 设置关键字参数 requested_agent_id，传入当前行给出的值
        idempotency_key=f"legacy-{uuid4()}",  # 为 uuid4 设置关键字参数 idempotency_key，传入当前行给出的值
    )  # 结束函数 query_handler 的参数及返回类型声明并开始函数体
    return StreamingResponse(  # 返回 StreamingResponse( 给调用方
        _legacy_stream(request, identity, container, run.id),  # 继续向上一处调用或声明传入 _legacy_stream(request, identity, container, run.id)
        media_type="text/event-stream",  # 为 StreamingResponse 设置关键字参数 media_type，传入当前行给出的值
        headers={  # 为 StreamingResponse 设置关键字参数 headers，传入当前行给出的值
            "Cache-Control": "no-cache, no-transform",  # 为多行字典定义键 "Cache-Control" 及其对应值
            "X-Accel-Buffering": "no",  # 为多行字典定义键 "X-Accel-Buffering" 及其对应值
            "X-Deprecated": "use /api/v1",  # 为多行字典定义键 "X-Deprecated" 及其对应值
        },  # 结束上一处多行结构，保持表达式边界清晰
    )  # 结束函数 query_handler 的参数及返回类型声明并开始函数体


async def _legacy_stream(  # 定义异步函数 _legacy_stream，封装可被事件循环调度的协程逻辑
    request: Request,  # 为函数 _legacy_stream 声明参数 request 及其类型或默认值
    identity: Identity,  # 为函数 _legacy_stream 声明参数 identity 及其类型或默认值
    container: ApplicationContainer,  # 为函数 _legacy_stream 声明参数 container 及其类型或默认值
    run_id,  # 为函数 _legacy_stream 声明参数 run_id 及其类型或默认值
):  # 结束 _legacy_stream 的参数列表并声明返回类型
    cursor = 0  # 计算 0 并保存到变量 cursor
    result_sent = False  # 计算 False 并保存到变量 result_sent
    while not await request.is_disconnected():  # 在函数 _legacy_stream 中执行表达式 while not await request.is_disconnected():，推进当前业务流程
        events = await container.events.replay(  # 等待 replay 完成，并将其结果保存到 events
            run_id, after_seq=cursor, limit=200  # 在函数 _legacy_stream 中执行表达式 run_id, after_seq=cursor, limit=200，推进当前业务流程
        )  # 结束函数 _legacy_stream 的参数及返回类型声明并开始函数体
        for event in events:  # 按迭代条件执行循环：for event in events:
            cursor = event.seq  # 计算 event.seq 并保存到变量 cursor
            translated = _translate_event(event.event_type, event.payload)  # 计算 _translate_event(event.event_type, event.payload) 并保存到变量 translated
            if translated is not None:  # 判断分支条件：if translated is not None:
                yield (  # 产出流式结果 (，保留生成器后续执行状态
                    "data: "  # 在函数 _legacy_stream 中执行表达式 "data: "，推进当前业务流程
                    f"{json.dumps(translated, ensure_ascii=False, default=str)}\n\n"  # 调用 目标函数 执行当前步骤：f"{json.dumps(translated, ensure_ascii=False, default=str)}\n\n"
                )  # 结束函数 _legacy_stream 的参数及返回类型声明并开始函数体
                if translated.get("type") == "result":  # 判断分支条件：if translated.get("type") == "result":
                    result_sent = True  # 计算 True 并保存到变量 result_sent
        run = await container.run_service.get_run(identity, run_id)  # 等待 get_run 完成，并将其结果保存到 run
        if run.status in TERMINAL_RUN_STATUSES and not events:  # 判断分支条件：if run.status in TERMINAL_RUN_STATUSES and not events:
            if run.status == "completed" and run.output and not result_sent:  # 判断分支条件：if run.status == "completed" and run.output and not result_sent:
                yield (  # 产出流式结果 (，保留生成器后续执行状态
                    "data: "  # 在函数 _legacy_stream 中执行表达式 "data: "，推进当前业务流程
                    f"{json.dumps({'type': 'result', 'data': run.output}, ensure_ascii=False, default=str)}\n\n"  # 调用 目标函数 执行当前步骤：f"{json.dumps({'type': 'result', 'data': run.output}, ensure_ascii=Fals…
                )  # 结束函数 _legacy_stream 的参数及返回类型声明并开始函数体
            break  # 提前结束当前循环并继续后续控制流
        await asyncio.sleep(0.25 if events else 0.75)  # 等待异步操作完成并取得结果：asyncio.sleep(0.25 if events else 0.75)


def _translate_event(event_type: str, payload: dict) -> dict | None:  # 定义函数 _translate_event，封装该模块的一项明确职责
    if event_type == "node.progress":  # 判断分支条件：if event_type == "node.progress":
        if payload.get("status") in {"running", "success", "error"}:  # 判断分支条件：if payload.get("status") in {"running", "success", "error"}:
            return {  # 返回 { 给调用方
                "type": "progress",  # 为多行字典定义键 "type" 及其对应值
                "step": payload.get("step", "处理中"),  # 为多行字典定义键 "step" 及其对应值
                "status": payload["status"],  # 为多行字典定义键 "status" 及其对应值
            }  # 结束上一处多行结构，保持表达式边界清晰
        return None  # 返回 None 给调用方
    if event_type == "agent.result":  # 判断分支条件：if event_type == "agent.result":
        return {"type": "result", "data": payload.get("data")}  # 返回 {"type": "result", "data": payload.get("data")} 给调用方
    if event_type in {"agent.selection_required", "sql.approval_required"}:  # 判断分支条件：if event_type in {"agent.selection_required", "sql.approval_required"}:
        return {  # 返回 { 给调用方
            "type": "approval_required",  # 为多行字典定义键 "type" 及其对应值
            "message": "运行已暂停，需要人工输入。",  # 为多行字典定义键 "message" 及其对应值
            "intervention": payload,  # 为多行字典定义键 "intervention" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    if event_type == "run.failed":  # 判断分支条件：if event_type == "run.failed":
        return {  # 返回 { 给调用方
            "type": "error",  # 为多行字典定义键 "type" 及其对应值
            "message": payload.get("message")  # 为多行字典定义键 "message" 及其对应值
            or payload.get("error_code")  # 调用 目标函数 执行当前步骤：or payload.get("error_code")
            or "运行失败",  # 向多行字典加入配置项 or "运行失败"
        }  # 结束上一处多行结构，保持表达式边界清晰
    if event_type == "run.rejected":  # 判断分支条件：if event_type == "run.rejected":
        return {"type": "error", "message": "SQL 审批被拒绝。"}  # 返回 {"type": "error", "message": "SQL 审批被拒绝。"} 给调用方
    return None  # 返回 None 给调用方
