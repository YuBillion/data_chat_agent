"""Transient-session repository proxy for long-running agent workers."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用


class ScopedRepository:  # 定义类 ScopedRepository，组织相关状态与行为
    """Open one AsyncSession per repository call and return it to the pool."""

    def __init__(self, session_factory: Any, repository_type: type) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        self._session_factory = session_factory  # 将 session_factory 保存到实例属性 self._session_factory
        self._repository_type = repository_type  # 将 repository_type 保存到实例属性 self._repository_type

    def __getattr__(self, name: str):  # 定义函数 __getattr__，封装该模块的一项明确职责
        if name.startswith("_"):  # 判断分支条件：if name.startswith("_"):
            raise AttributeError(name)  # 抛出明确异常，阻止错误状态被静默接受：AttributeError(name)

        async def invoke(*args, **kwargs):  # 定义异步函数 invoke，封装可被事件循环调度的协程逻辑
            async with self._session_factory() as session:  # 进入受管理的上下文 async with self._session_factory() as session:，确保资源正确获取与释放
                repository = self._repository_type(session)  # 计算 self._repository_type(session) 并保存到变量 repository
                method = getattr(repository, name)  # 计算 getattr(repository, name) 并保存到变量 method
                return await method(*args, **kwargs)  # 返回 await method(*args, **kwargs) 给调用方

        return invoke  # 返回 invoke 给调用方
