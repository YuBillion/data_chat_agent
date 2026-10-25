"""FastAPI dependencies for harness v1 routes."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from typing import Annotated  # 从 typing 导入 Annotated，供本模块后续代码使用

from fastapi import Depends, Request  # 从 fastapi 导入 Depends, Request，供本模块后续代码使用

from app.application import ApplicationContainer  # 从 app.application 导入 ApplicationContainer，供本模块后续代码使用
from app.harness.service import RunService  # 从 app.harness.service 导入 RunService，供本模块后续代码使用


def get_container(request: Request) -> ApplicationContainer:  # 定义函数 get_container，封装该模块的一项明确职责
    return request.app.state.container  # 返回 request.app.state.container 给调用方


def get_run_service(  # 定义函数 get_run_service，封装该模块的一项明确职责
    container: Annotated[ApplicationContainer, Depends(get_container)],  # 为函数 get_run_service 声明参数 container 及其类型或默认值
) -> RunService:  # 结束 get_run_service 的参数列表并声明返回类型
    return container.run_service  # 返回 container.run_service 给调用方
