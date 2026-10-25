"""Liveness, readiness, and Prometheus metrics."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from typing import Annotated  # 从 typing 导入 Annotated，供本模块后续代码使用

from fastapi import APIRouter, Depends, Response, status  # 从 fastapi 导入 APIRouter, Depends, Response, status，供本模块后续代码使用
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest  # 从 prometheus_client 导入 CONTENT_TYPE_LATEST, REGISTRY, generate_latest，供本模块后续代码使用

from app.api.dependencies_v1 import get_container  # 从 app.api.dependencies_v1 导入 get_container，供本模块后续代码使用
from app.application import ApplicationContainer  # 从 app.application 导入 ApplicationContainer，供本模块后续代码使用

health_router = APIRouter(tags=["operations"])  # 计算 APIRouter(tags=["operations"]) 并保存到变量 health_router


@health_router.get("/health/live")  # 应用装饰器 health_router.get("/health/live")，为紧随其后的定义附加框架行为
async def liveness() -> dict[str, str]:  # 定义异步函数 liveness，封装可被事件循环调度的协程逻辑
    return {"status": "ok"}  # 返回 {"status": "ok"} 给调用方


@health_router.get("/health/ready")  # 应用装饰器 health_router.get("/health/ready")，为紧随其后的定义附加框架行为
async def readiness(  # 定义异步函数 readiness，封装可被事件循环调度的协程逻辑
    container: Annotated[ApplicationContainer, Depends(get_container)],  # 为函数 readiness 声明参数 container 及其类型或默认值
) -> Response:  # 结束 readiness 的参数列表并声明返回类型
    checks: dict[str, str] = {}  # 计算 {} 并保存到变量 checks
    healthy = True  # 计算 True 并保存到变量 healthy
    for name, check in (  # 按迭代条件执行循环：for name, check in (
        ("postgres", container.database.ping),  # 向多行序列加入元素 ("postgres", container.database.ping)
        ("redis", container.redis.ping),  # 向多行序列加入元素 ("redis", container.redis.ping)
    ):  # 结束 readiness 的参数列表并声明返回类型
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            await asyncio.wait_for(check(), timeout=2)  # 等待异步操作完成并取得结果：asyncio.wait_for(check(), timeout=2)
            checks[name] = "ok"  # 计算 "ok" 并保存到变量 checks[name]
        except Exception:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception:
            healthy = False  # 计算 False 并保存到变量 healthy
            checks[name] = "unavailable"  # 计算 "unavailable" 并保存到变量 checks[name]
    return Response(  # 返回 Response( 给调用方
        content=__import__("json").dumps(  # 为 __import__ 设置关键字参数 content，传入当前行给出的值
            {"status": "ok" if healthy else "degraded", "checks": checks}  # 在函数 readiness 中执行表达式 {"status": "ok" if healthy else "degraded", "checks": checks}，推进当前业务流程
        ),  # 结束函数 readiness 的参数及返回类型声明并开始函数体
        status_code=(  # 为 Response 设置关键字参数 status_code，传入当前行给出的值
            status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE  # 在函数 readiness 中执行表达式 status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE，推进当前业务流程
        ),  # 结束函数 readiness 的参数及返回类型声明并开始函数体
        media_type="application/json",  # 为 Response 设置关键字参数 media_type，传入当前行给出的值
    )  # 结束函数 readiness 的参数及返回类型声明并开始函数体


@health_router.get("/metrics", include_in_schema=False)  # 应用装饰器 health_router.get("/metrics", include_in_schema=False)，为紧随其后的定义附加框架行为
async def metrics() -> Response:  # 定义异步函数 metrics，封装可被事件循环调度的协程逻辑
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)  # 返回 Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LAT… 给调用方
