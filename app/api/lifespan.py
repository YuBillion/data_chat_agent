"""FastAPI lifecycle for the harness API process."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from contextlib import asynccontextmanager  # 从 contextlib 导入 asynccontextmanager，供本模块后续代码使用

from fastapi import FastAPI  # 从 fastapi 导入 FastAPI，供本模块后续代码使用

from app.application import ApplicationContainer, create_container  # 从 app.application 导入 ApplicationContainer, create_container，供本模块后续代码使用
from app.conf.settings import get_settings  # 从 app.conf.settings 导入 get_settings，供本模块后续代码使用


@asynccontextmanager  # 应用装饰器 asynccontextmanager，为紧随其后的定义附加框架行为
async def lifespan(app: FastAPI):  # 定义异步函数 lifespan，封装可被事件循环调度的协程逻辑
    container = getattr(app.state, "container", None)  # 计算 getattr(app.state, "container", None) 并保存到变量 container
    owns_container = container is None  # 计算 container is None 并保存到变量 owns_container
    if container is None:  # 判断分支条件：if container is None:
        container = create_container(get_settings())  # 计算 create_container(get_settings()) 并保存到变量 container
        app.state.container = container  # 计算 container 并保存到变量 app.state.container
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        await container.start(with_worker=False)  # 等待异步操作完成并取得结果：container.start(with_worker=False)
        container.telemetry.instrument_app(app)  # 调用 instrument_app 执行当前步骤：container.telemetry.instrument_app(app)
        yield  # 产出流式结果 ，保留生成器后续执行状态
    finally:  # 进入无论成功失败都必须执行的资源清理分支
        if owns_container:  # 判断分支条件：if owns_container:
            await container.close()  # 等待异步操作完成并取得结果：container.close()


def build_lifespan(container: ApplicationContainer):  # 定义函数 build_lifespan，封装该模块的一项明确职责
    @asynccontextmanager  # 应用装饰器 asynccontextmanager，为紧随其后的定义附加框架行为
    async def injected_lifespan(app: FastAPI):  # 定义异步函数 injected_lifespan，封装可被事件循环调度的协程逻辑
        app.state.container = container  # 计算 container 并保存到变量 app.state.container
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            await container.start(with_worker=False)  # 等待异步操作完成并取得结果：container.start(with_worker=False)
            container.telemetry.instrument_app(app)  # 调用 instrument_app 执行当前步骤：container.telemetry.instrument_app(app)
            yield  # 产出流式结果 ，保留生成器后续执行状态
        finally:  # 进入无论成功失败都必须执行的资源清理分支
            await container.close()  # 等待异步操作完成并取得结果：container.close()

    return injected_lifespan  # 返回 injected_lifespan 给调用方
