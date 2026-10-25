"""Small concurrency helper for bounded retrieval fan-out."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from collections.abc import Awaitable, Callable, Iterable  # 从 collections.abc 导入 Awaitable, Callable, Iterable，供本模块后续代码使用
from typing import TypeVar  # 从 typing 导入 TypeVar，供本模块后续代码使用

T = TypeVar("T")  # 计算 TypeVar("T") 并保存到变量 T
R = TypeVar("R")  # 计算 TypeVar("R") 并保存到变量 R


async def bounded_gather(  # 定义异步函数 bounded_gather，封装可被事件循环调度的协程逻辑
    items: Iterable[T],  # 为函数 bounded_gather 声明参数 items 及其类型或默认值
    operation: Callable[[T], Awaitable[R]],  # 为函数 bounded_gather 声明参数 operation 及其类型或默认值
    *,  # 为函数 bounded_gather 声明参数 * 及其类型或默认值
    concurrency: int,  # 为函数 bounded_gather 声明参数 concurrency 及其类型或默认值
) -> list[R]:  # 结束 bounded_gather 的参数列表并声明返回类型
    semaphore = asyncio.Semaphore(max(concurrency, 1))  # 计算 asyncio.Semaphore(max(concurrency, 1)) 并保存到变量 semaphore

    async def guarded(item: T) -> R:  # 定义异步函数 guarded，封装可被事件循环调度的协程逻辑
        async with semaphore:  # 进入受管理的上下文 async with semaphore:，确保资源正确获取与释放
            return await operation(item)  # 返回 await operation(item) 给调用方

    async with asyncio.TaskGroup() as task_group:  # 进入受管理的上下文 async with asyncio.TaskGroup() as task_group:，确保资源正确获取与释放
        tasks = [  # 计算 [ 并保存到变量 tasks
            task_group.create_task(guarded(item))  # 调用 create_task 执行当前步骤：task_group.create_task(guarded(item))
            for item in items  # 按迭代条件执行循环：for item in items
        ]  # 结束上一处多行结构，保持表达式边界清晰
    return [task.result() for task in tasks]  # 返回 [task.result() for task in tasks] 给调用方
