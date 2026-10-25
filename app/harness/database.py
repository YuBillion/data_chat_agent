"""Async SQLAlchemy lifecycle for harness persistence."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from collections.abc import AsyncIterator  # 从 collections.abc 导入 AsyncIterator，供本模块后续代码使用

from sqlalchemy.ext.asyncio import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    AsyncEngine,  # 从当前 import 模块导入符号 AsyncEngine
    AsyncSession,  # 从当前 import 模块导入符号 AsyncSession
    async_sessionmaker,  # 从当前 import 模块导入符号 async_sessionmaker
    create_async_engine,  # 从当前 import 模块导入符号 create_async_engine
)  # 结束多符号导入列表

from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用


def sqlalchemy_postgres_dsn(dsn: str) -> str:  # 定义函数 sqlalchemy_postgres_dsn，封装该模块的一项明确职责
    if dsn.startswith("postgresql+psycopg://"):  # 判断分支条件：if dsn.startswith("postgresql+psycopg://"):
        return dsn  # 返回 dsn 给调用方
    if dsn.startswith("postgresql://"):  # 判断分支条件：if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")  # 返回 "postgresql+psycopg://" + dsn.removeprefix("postgresql://") 给调用方
    if dsn.startswith("postgres://"):  # 判断分支条件：if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgres://")  # 返回 "postgresql+psycopg://" + dsn.removeprefix("postgres://") 给调用方
    raise ValueError("unsupported PostgreSQL DSN")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("unsupported PostgreSQL DSN")


def libpq_postgres_dsn(dsn: str) -> str:  # 定义函数 libpq_postgres_dsn，封装该模块的一项明确职责
    if dsn.startswith("postgresql+psycopg://"):  # 判断分支条件：if dsn.startswith("postgresql+psycopg://"):
        return "postgresql://" + dsn.removeprefix("postgresql+psycopg://")  # 返回 "postgresql://" + dsn.removeprefix("postgresql+psycopg://") 给调用方
    if dsn.startswith("postgres://"):  # 判断分支条件：if dsn.startswith("postgres://"):
        return "postgresql://" + dsn.removeprefix("postgres://")  # 返回 "postgresql://" + dsn.removeprefix("postgres://") 给调用方
    return dsn  # 返回 dsn 给调用方


class HarnessDatabase:  # 定义类 HarnessDatabase，组织相关状态与行为
    def __init__(self, settings: Settings) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        self.settings = settings  # 将依赖或状态 settings 保存到实例属性 self.settings
        self.engine: AsyncEngine = create_async_engine(  # 将依赖或状态 create_async_engine( 保存到实例属性 self.engine: AsyncEngine
            sqlalchemy_postgres_dsn(settings.postgres_dsn),  # 继续向上一处调用或声明传入 sqlalchemy_postgres_dsn(settings.postgres_dsn)
            pool_size=settings.postgres_pool_max_size,  # 为 create_async_engine 设置关键字参数 pool_size，传入当前行给出的值
            max_overflow=0,  # 为 create_async_engine 设置关键字参数 max_overflow，传入当前行给出的值
            pool_pre_ping=True,  # 为 create_async_engine 设置关键字参数 pool_pre_ping，传入当前行给出的值
            connect_args={"prepare_threshold": 0},  # 为 create_async_engine 设置关键字参数 connect_args，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体
        self.session_factory = async_sessionmaker(  # 将依赖或状态 async_sessionmaker( 保存到实例属性 self.session_factory
            self.engine,  # 继续向上一处调用或声明传入 self.engine
            class_=AsyncSession,  # 为 async_sessionmaker 设置关键字参数 class_，传入当前行给出的值
            autoflush=False,  # 为 async_sessionmaker 设置关键字参数 autoflush，传入当前行给出的值
            expire_on_commit=False,  # 为 async_sessionmaker 设置关键字参数 expire_on_commit，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体

    async def ping(self) -> None:  # 定义异步函数 ping，封装可被事件循环调度的协程逻辑
        async with self.engine.connect() as connection:  # 进入受管理的上下文 async with self.engine.connect() as connection:，确保资源正确获取与释放
            await connection.exec_driver_sql("select 1")  # 等待异步操作完成并取得结果：connection.exec_driver_sql("select 1")

    async def session(self) -> AsyncIterator[AsyncSession]:  # 定义异步函数 session，封装可被事件循环调度的协程逻辑
        async with self.session_factory() as session:  # 进入受管理的上下文 async with self.session_factory() as session:，确保资源正确获取与释放
            yield session  # 产出流式结果 session，保留生成器后续执行状态

    async def close(self) -> None:  # 定义异步函数 close，封装可被事件循环调度的协程逻辑
        await self.engine.dispose()  # 等待异步操作完成并取得结果：self.engine.dispose()
