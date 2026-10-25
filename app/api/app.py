"""FastAPI application factory shared by production and tests."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import uuid  # 导入uuid，建立本模块需要的外部能力引用

from fastapi import FastAPI, HTTPException, Request  # 从 fastapi 导入 FastAPI, HTTPException, Request，供本模块后续代码使用
from fastapi.exceptions import RequestValidationError  # 从 fastapi.exceptions 导入 RequestValidationError，供本模块后续代码使用
from fastapi.middleware.cors import CORSMiddleware  # 从 fastapi.middleware.cors 导入 CORSMiddleware，供本模块后续代码使用
from fastapi.middleware.trustedhost import TrustedHostMiddleware  # 从 fastapi.middleware.trustedhost 导入 TrustedHostMiddleware，供本模块后续代码使用
from fastapi.responses import JSONResponse  # 从 fastapi.responses 导入 JSONResponse，供本模块后续代码使用

from app.api.lifespan import build_lifespan, lifespan  # 从 app.api.lifespan 导入 build_lifespan, lifespan，供本模块后续代码使用
from app.api.routers.agents_router import agents_router  # 从 app.api.routers.agents_router 导入 agents_router，供本模块后续代码使用
from app.api.routers.health_router import health_router  # 从 app.api.routers.health_router 导入 health_router，供本模块后续代码使用
from app.api.routers.interventions_router import interventions_router  # 从 app.api.routers.interventions_router 导入 interventions_router，供本模块后续代码使用
from app.api.routers.query_router import query_router  # 从 app.api.routers.query_router 导入 query_router，供本模块后续代码使用
from app.api.routers.runs_router import runs_router  # 从 app.api.routers.runs_router 导入 runs_router，供本模块后续代码使用
from app.api.routers.sessions_router import sessions_router  # 从 app.api.routers.sessions_router 导入 sessions_router，供本模块后续代码使用
from app.api.schemas.v1 import ProblemDetail  # 从 app.api.schemas.v1 导入 ProblemDetail，供本模块后续代码使用
from app.application import ApplicationContainer  # 从 app.application 导入 ApplicationContainer，供本模块后续代码使用
from app.conf.settings import Settings, get_settings  # 从 app.conf.settings 导入 Settings, get_settings，供本模块后续代码使用
from app.core.context import request_id_ctx_var  # 从 app.core.context 导入 request_id_ctx_var，供本模块后续代码使用
from app.core.errors import AppError  # 从 app.core.errors 导入 AppError，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用


def create_app(  # 定义函数 create_app，封装该模块的一项明确职责
    *,  # 为函数 create_app 声明参数 * 及其类型或默认值
    settings: Settings | None = None,  # 为函数 create_app 声明参数 settings 及其类型或默认值
    container: ApplicationContainer | None = None,  # 为函数 create_app 声明参数 container 及其类型或默认值
) -> FastAPI:  # 结束 create_app 的参数列表并声明返回类型
    runtime_settings = settings or get_settings()  # 计算 settings or get_settings() 并保存到变量 runtime_settings
    app = FastAPI(  # 调用 FastAPI 构造结果并保存到 app
        title="Data Chat Agent Harness",  # 为 FastAPI 设置关键字参数 title，传入当前行给出的值
        version=runtime_settings.app_version,  # 为 FastAPI 设置关键字参数 version，传入当前行给出的值
        lifespan=(  # 为 FastAPI 设置关键字参数 lifespan，传入当前行给出的值
            build_lifespan(container) if container is not None else lifespan  # 调用 build_lifespan 执行当前步骤：build_lifespan(container) if container is not None else lifespan
        ),  # 结束函数 create_app 的参数及返回类型声明并开始函数体
    )  # 结束函数 create_app 的参数及返回类型声明并开始函数体
    if container is not None:  # 判断分支条件：if container is not None:
        app.state.container = container  # 计算 container 并保存到变量 app.state.container
    app.add_middleware(  # 调用 add_middleware 执行当前步骤：app.add_middleware(
        CORSMiddleware,  # 继续向上一处调用或声明传入 CORSMiddleware
        allow_origins=runtime_settings.cors_origins,  # 为 app.add_middleware 设置关键字参数 allow_origins，传入当前行给出的值
        allow_credentials=True,  # 为 app.add_middleware 设置关键字参数 allow_credentials，传入当前行给出的值
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],  # 为 app.add_middleware 设置关键字参数 allow_methods，传入当前行给出的值
        allow_headers=[  # 为 app.add_middleware 设置关键字参数 allow_headers，传入当前行给出的值
            "Authorization",  # 向多行序列加入元素 "Authorization"
            "Content-Type",  # 向多行序列加入元素 "Content-Type"
            "Idempotency-Key",  # 向多行序列加入元素 "Idempotency-Key"
            "Last-Event-ID",  # 向多行序列加入元素 "Last-Event-ID"
        ],  # 结束上一处多行结构，保持表达式边界清晰
        expose_headers=["X-Request-ID", "X-Trace-ID"],  # 为 app.add_middleware 设置关键字参数 expose_headers，传入当前行给出的值
    )  # 结束函数 create_app 的参数及返回类型声明并开始函数体
    app.add_middleware(  # 调用 add_middleware 执行当前步骤：app.add_middleware(
        TrustedHostMiddleware,  # 继续向上一处调用或声明传入 TrustedHostMiddleware
        allowed_hosts=runtime_settings.trusted_host_values,  # 为 app.add_middleware 设置关键字参数 allowed_hosts，传入当前行给出的值
    )  # 结束函数 create_app 的参数及返回类型声明并开始函数体

    @app.middleware("http")  # 应用装饰器 app.middleware("http")，为紧随其后的定义附加框架行为
    async def request_context_middleware(request: Request, call_next):  # 定义异步函数 request_context_middleware，封装可被事件循环调度的协程逻辑
        request_id = request.headers.get("X-Request-ID", "").strip()  # 计算 request.headers.get("X-Request-ID", "").strip() 并保存到变量 request_id
        if not request_id or len(request_id) > 128:  # 判断分支条件：if not request_id or len(request_id) > 128:
            request_id = str(uuid.uuid4())  # 计算 str(uuid.uuid4()) 并保存到变量 request_id
        request_id_ctx_var.set(request_id)  # 调用 set 执行当前步骤：request_id_ctx_var.set(request_id)
        request.state.request_id = request_id  # 计算 request_id 并保存到变量 request.state.request_id
        content_length = request.headers.get("content-length")  # 计算 request.headers.get("content-length") 并保存到变量 content_length
        if content_length:  # 判断分支条件：if content_length:
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                if int(content_length) > runtime_settings.max_request_bytes:  # 判断分支条件：if int(content_length) > runtime_settings.max_request_bytes:
                    return JSONResponse(  # 返回 JSONResponse( 给调用方
                        status_code=413,  # 为 JSONResponse 设置关键字参数 status_code，传入当前行给出的值
                        content=ProblemDetail(  # 为 model_dump 设置关键字参数 content，传入当前行给出的值
                            title="Request Too Large",  # 为 model_dump 设置关键字参数 title，传入当前行给出的值
                            status=413,  # 为 model_dump 设置关键字参数 status，传入当前行给出的值
                            detail="request body is too large",  # 为 model_dump 设置关键字参数 detail，传入当前行给出的值
                            code="REQUEST_TOO_LARGE",  # 为 model_dump 设置关键字参数 code，传入当前行给出的值
                            request_id=request_id,  # 为 model_dump 设置关键字参数 request_id，传入当前行给出的值
                        ).model_dump(mode="json"),  # 继续向上一处调用或声明传入 ).model_dump(mode="json")
                        media_type="application/problem+json",  # 为 JSONResponse 设置关键字参数 media_type，传入当前行给出的值
                    )  # 结束函数 request_context_middleware 的参数及返回类型声明并开始函数体
            except ValueError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except ValueError as exc:
                del exc  # 删除或显式忽略名称 exc，避免未使用变量干扰
                return JSONResponse(  # 返回 JSONResponse( 给调用方
                    status_code=400,  # 为 JSONResponse 设置关键字参数 status_code，传入当前行给出的值
                    content=ProblemDetail(  # 为 model_dump 设置关键字参数 content，传入当前行给出的值
                        title="Invalid Content Length",  # 为 model_dump 设置关键字参数 title，传入当前行给出的值
                        status=400,  # 为 model_dump 设置关键字参数 status，传入当前行给出的值
                        detail="content-length header is invalid",  # 为 model_dump 设置关键字参数 detail，传入当前行给出的值
                        code="INVALID_CONTENT_LENGTH",  # 为 model_dump 设置关键字参数 code，传入当前行给出的值
                        request_id=request_id,  # 为 model_dump 设置关键字参数 request_id，传入当前行给出的值
                    ).model_dump(mode="json"),  # 继续向上一处调用或声明传入 ).model_dump(mode="json")
                    media_type="application/problem+json",  # 为 JSONResponse 设置关键字参数 media_type，传入当前行给出的值
                )  # 结束函数 request_context_middleware 的参数及返回类型声明并开始函数体
        response = await call_next(request)  # 等待 call_next 完成，并将其结果保存到 response
        response.headers["X-Request-ID"] = request_id  # 计算 request_id 并保存到变量 response.headers["X-Request-ID"]
        active_container = getattr(request.app.state, "container", None)  # 计算 getattr(request.app.state, "container", None) 并保存到变量 active_container
        if active_container is not None:  # 判断分支条件：if active_container is not None:
            trace_id = active_container.telemetry.current_trace_id()  # 计算 active_container.telemetry.current_trace_id() 并保存到变量 trace_id
            if trace_id:  # 判断分支条件：if trace_id:
                response.headers["X-Trace-ID"] = trace_id  # 计算 trace_id 并保存到变量 response.headers["X-Trace-ID"]
        response.headers["X-Content-Type-Options"] = "nosniff"  # 计算 "nosniff" 并保存到变量 response.headers["X-Content-Type-Options"]
        response.headers["Referrer-Policy"] = "no-referrer"  # 计算 "no-referrer" 并保存到变量 response.headers["Referrer-Policy"]
        return response  # 返回 response 给调用方

    @app.exception_handler(AppError)  # 应用装饰器 app.exception_handler(AppError)，为紧随其后的定义附加框架行为
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # 定义异步函数 app_error_handler，封装可被事件循环调度的协程逻辑
        active_container = getattr(request.app.state, "container", None)  # 计算 getattr(request.app.state, "container", None) 并保存到变量 active_container
        problem = ProblemDetail(  # 调用 ProblemDetail 构造结果并保存到 problem
            title=exc.code.replace("_", " ").title(),  # 为 title 设置关键字参数 title，传入当前行给出的值
            status=exc.status_code,  # 为 ProblemDetail 设置关键字参数 status，传入当前行给出的值
            detail=exc.message,  # 为 ProblemDetail 设置关键字参数 detail，传入当前行给出的值
            code=exc.code,  # 为 ProblemDetail 设置关键字参数 code，传入当前行给出的值
            request_id=getattr(request.state, "request_id", "unknown"),  # 为 getattr 设置关键字参数 request_id，传入当前行给出的值
            trace_id=(  # 为 ProblemDetail 设置关键字参数 trace_id，传入当前行给出的值
                active_container.telemetry.current_trace_id()  # 调用 current_trace_id 执行当前步骤：active_container.telemetry.current_trace_id()
                if active_container is not None  # 判断分支条件：if active_container is not None
                else None  # 在函数 app_error_handler 中执行表达式 else None，推进当前业务流程
            ),  # 结束函数 app_error_handler 的参数及返回类型声明并开始函数体
            retryable=exc.retryable,  # 为 ProblemDetail 设置关键字参数 retryable，传入当前行给出的值
            details=exc.details,  # 为 ProblemDetail 设置关键字参数 details，传入当前行给出的值
        )  # 结束函数 app_error_handler 的参数及返回类型声明并开始函数体
        headers = {}  # 计算 {} 并保存到变量 headers
        if exc.status_code == 429:  # 判断分支条件：if exc.status_code == 429:
            headers["Retry-After"] = str(  # 调用 str 构造结果并保存到 headers["Retry-After"]
                max(int(exc.details.get("retry_after_seconds", 60)), 1)  # 调用 max 执行当前步骤：max(int(exc.details.get("retry_after_seconds", 60)), 1)
            )  # 结束函数 app_error_handler 的参数及返回类型声明并开始函数体
        return JSONResponse(  # 返回 JSONResponse( 给调用方
            status_code=exc.status_code,  # 为 JSONResponse 设置关键字参数 status_code，传入当前行给出的值
            content=problem.model_dump(mode="json"),  # 为 problem.model_dump 设置关键字参数 content，传入当前行给出的值
            headers=headers,  # 为 JSONResponse 设置关键字参数 headers，传入当前行给出的值
            media_type="application/problem+json",  # 为 JSONResponse 设置关键字参数 media_type，传入当前行给出的值
        )  # 结束函数 app_error_handler 的参数及返回类型声明并开始函数体

    @app.exception_handler(RequestValidationError)  # 应用装饰器 app.exception_handler(RequestValidationError)，为紧随其后的定义附加框架行为
    async def validation_error_handler(  # 定义异步函数 validation_error_handler，封装可被事件循环调度的协程逻辑
        request: Request, exc: RequestValidationError  # 为函数 validation_error_handler 声明参数 request 及其类型或默认值
    ) -> JSONResponse:  # 结束 validation_error_handler 的参数列表并声明返回类型
        errors = [  # 计算 [ 并保存到变量 errors
            {  # 在函数 validation_error_handler 中执行表达式 {，推进当前业务流程
                "location": ".".join(str(part) for part in item.get("loc", ())),  # 为多行字典定义键 "location" 及其对应值
                "message": item.get("msg", "invalid value"),  # 为多行字典定义键 "message" 及其对应值
                "type": item.get("type", "value_error"),  # 为多行字典定义键 "type" 及其对应值
            }  # 结束上一处多行结构，保持表达式边界清晰
            for item in exc.errors()  # 按迭代条件执行循环：for item in exc.errors()
        ]  # 结束上一处多行结构，保持表达式边界清晰
        problem = ProblemDetail(  # 调用 ProblemDetail 构造结果并保存到 problem
            title="Request Validation Failed",  # 为 ProblemDetail 设置关键字参数 title，传入当前行给出的值
            status=422,  # 为 ProblemDetail 设置关键字参数 status，传入当前行给出的值
            detail="request validation failed",  # 为 ProblemDetail 设置关键字参数 detail，传入当前行给出的值
            code="VALIDATION_ERROR",  # 为 ProblemDetail 设置关键字参数 code，传入当前行给出的值
            request_id=getattr(request.state, "request_id", "unknown"),  # 为 getattr 设置关键字参数 request_id，传入当前行给出的值
            details={"errors": errors},  # 为 ProblemDetail 设置关键字参数 details，传入当前行给出的值
        )  # 结束函数 validation_error_handler 的参数及返回类型声明并开始函数体
        return JSONResponse(  # 返回 JSONResponse( 给调用方
            status_code=422,  # 为 JSONResponse 设置关键字参数 status_code，传入当前行给出的值
            content=problem.model_dump(mode="json"),  # 为 problem.model_dump 设置关键字参数 content，传入当前行给出的值
            media_type="application/problem+json",  # 为 JSONResponse 设置关键字参数 media_type，传入当前行给出的值
        )  # 结束函数 validation_error_handler 的参数及返回类型声明并开始函数体

    @app.exception_handler(HTTPException)  # 应用装饰器 app.exception_handler(HTTPException)，为紧随其后的定义附加框架行为
    async def http_error_handler(  # 定义异步函数 http_error_handler，封装可被事件循环调度的协程逻辑
        request: Request, exc: HTTPException  # 为函数 http_error_handler 声明参数 request 及其类型或默认值
    ) -> JSONResponse:  # 结束 http_error_handler 的参数列表并声明返回类型
        problem = ProblemDetail(  # 调用 ProblemDetail 构造结果并保存到 problem
            title="HTTP Error",  # 为 ProblemDetail 设置关键字参数 title，传入当前行给出的值
            status=exc.status_code,  # 为 ProblemDetail 设置关键字参数 status，传入当前行给出的值
            detail=str(exc.detail),  # 为 str 设置关键字参数 detail，传入当前行给出的值
            code="HTTP_ERROR",  # 为 ProblemDetail 设置关键字参数 code，传入当前行给出的值
            request_id=getattr(request.state, "request_id", "unknown"),  # 为 getattr 设置关键字参数 request_id，传入当前行给出的值
        )  # 结束函数 http_error_handler 的参数及返回类型声明并开始函数体
        return JSONResponse(  # 返回 JSONResponse( 给调用方
            status_code=exc.status_code,  # 为 JSONResponse 设置关键字参数 status_code，传入当前行给出的值
            content=problem.model_dump(mode="json"),  # 为 problem.model_dump 设置关键字参数 content，传入当前行给出的值
            headers=exc.headers,  # 为 JSONResponse 设置关键字参数 headers，传入当前行给出的值
            media_type="application/problem+json",  # 为 JSONResponse 设置关键字参数 media_type，传入当前行给出的值
        )  # 结束函数 http_error_handler 的参数及返回类型声明并开始函数体

    @app.exception_handler(Exception)  # 应用装饰器 app.exception_handler(Exception)，为紧随其后的定义附加框架行为
    async def unhandled_error_handler(  # 定义异步函数 unhandled_error_handler，封装可被事件循环调度的协程逻辑
        request: Request, exc: Exception  # 为函数 unhandled_error_handler 声明参数 request 及其类型或默认值
    ) -> JSONResponse:  # 结束 unhandled_error_handler 的参数列表并声明返回类型
        logger.exception(  # 调用 exception 执行当前步骤：logger.exception(
            "Unhandled request failure: type={} path={}",  # 继续向上一处调用或声明传入 "Unhandled request failure: type={} path={}"
            type(exc).__name__,  # 继续向上一处调用或声明传入 type(exc).__name__
            request.url.path,  # 继续向上一处调用或声明传入 request.url.path
        )  # 结束函数 unhandled_error_handler 的参数及返回类型声明并开始函数体
        problem = ProblemDetail(  # 调用 ProblemDetail 构造结果并保存到 problem
            title="Internal Server Error",  # 为 ProblemDetail 设置关键字参数 title，传入当前行给出的值
            status=500,  # 为 ProblemDetail 设置关键字参数 status，传入当前行给出的值
            detail="an internal error occurred",  # 为 ProblemDetail 设置关键字参数 detail，传入当前行给出的值
            code="INTERNAL_ERROR",  # 为 ProblemDetail 设置关键字参数 code，传入当前行给出的值
            request_id=getattr(request.state, "request_id", "unknown"),  # 为 getattr 设置关键字参数 request_id，传入当前行给出的值
        )  # 结束函数 unhandled_error_handler 的参数及返回类型声明并开始函数体
        return JSONResponse(  # 返回 JSONResponse( 给调用方
            status_code=500,  # 为 JSONResponse 设置关键字参数 status_code，传入当前行给出的值
            content=problem.model_dump(mode="json"),  # 为 problem.model_dump 设置关键字参数 content，传入当前行给出的值
            media_type="application/problem+json",  # 为 JSONResponse 设置关键字参数 media_type，传入当前行给出的值
        )  # 结束函数 unhandled_error_handler 的参数及返回类型声明并开始函数体

    app.include_router(health_router)  # 调用 include_router 执行当前步骤：app.include_router(health_router)
    app.include_router(agents_router)  # 调用 include_router 执行当前步骤：app.include_router(agents_router)
    app.include_router(sessions_router)  # 调用 include_router 执行当前步骤：app.include_router(sessions_router)
    app.include_router(runs_router)  # 调用 include_router 执行当前步骤：app.include_router(runs_router)
    app.include_router(interventions_router)  # 调用 include_router 执行当前步骤：app.include_router(interventions_router)
    app.include_router(query_router)  # 调用 include_router 执行当前步骤：app.include_router(query_router)
    return app  # 返回 app 给调用方
