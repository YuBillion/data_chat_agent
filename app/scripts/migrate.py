"""Run database migrations and create LangGraph checkpoint tables."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用

from alembic import command  # 从 alembic 导入 command，供本模块后续代码使用
from alembic.config import Config  # 从 alembic.config 导入 Config，供本模块后续代码使用
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # 从 langgraph.checkpoint.postgres.aio 导入 AsyncPostgresSaver，供本模块后续代码使用
from psycopg import AsyncConnection  # 从 psycopg 导入 AsyncConnection，供本模块后续代码使用
from psycopg.rows import dict_row  # 从 psycopg.rows 导入 dict_row，供本模块后续代码使用
from sqlalchemy import text  # 从 sqlalchemy 导入 text，供本模块后续代码使用

from app.conf.settings import get_settings  # 从 app.conf.settings 导入 get_settings，供本模块后续代码使用
from app.harness.database import HarnessDatabase, libpq_postgres_dsn  # 从 app.harness.database 导入 HarnessDatabase, libpq_postgres_dsn，供本模块后续代码使用


async def run() -> None:  # 定义异步函数 run，封装可被事件循环调度的协程逻辑
    settings = get_settings()  # 计算 get_settings() 并保存到变量 settings
    config = Config("alembic.ini")  # 计算 Config("alembic.ini") 并保存到变量 config
    command.upgrade(config, "head")  # 调用 upgrade 执行当前步骤：command.upgrade(config, "head")

    database = HarnessDatabase(settings)  # 计算 HarnessDatabase(settings) 并保存到变量 database
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        async with database.engine.begin() as connection:  # 进入受管理的上下文 async with database.engine.begin() as connection:，确保资源正确获取与释放
            await connection.execute(  # 等待异步操作完成并取得结果：connection.execute(
                text(f'create schema if not exists "{settings.postgres_langgraph_schema}"')  # 调用 text 执行当前步骤：text(f'create schema if not exists "{settings.postgres_langgraph_schema…
            )  # 结束 connection.execute 调用参数，得到完整表达式结果
    finally:  # 进入无论成功失败都必须执行的资源清理分支
        await database.close()  # 等待异步操作完成并取得结果：database.close()

    checkpoint_connection = await AsyncConnection.connect(  # 等待 connect 完成，并将其结果保存到 checkpoint_connection
        libpq_postgres_dsn(settings.postgres_dsn),  # 继续向上一处调用或声明传入 libpq_postgres_dsn(settings.postgres_dsn)
        autocommit=True,  # 为 AsyncConnection.connect 设置关键字参数 autocommit，传入当前行给出的值
        prepare_threshold=0,  # 为 AsyncConnection.connect 设置关键字参数 prepare_threshold，传入当前行给出的值
        row_factory=dict_row,  # 为 AsyncConnection.connect 设置关键字参数 row_factory，传入当前行给出的值
        options=(  # 为 AsyncConnection.connect 设置关键字参数 options，传入当前行给出的值
            f"-c search_path={settings.postgres_langgraph_schema},public"  # 在函数 run 中执行表达式 f"-c search_path={settings.postgres_langgraph_schema},public"，推进当前业务流程
        ),  # 结束函数 run 的调用或声明结构
    )  # 结束 AsyncConnection.connect 调用参数，得到完整表达式结果
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        saver = AsyncPostgresSaver(checkpoint_connection)  # 计算 AsyncPostgresSaver(checkpoint_connection) 并保存到变量 saver
        await saver.setup()  # 等待异步操作完成并取得结果：saver.setup()
    finally:  # 进入无论成功失败都必须执行的资源清理分支
        await checkpoint_connection.close()  # 等待异步操作完成并取得结果：checkpoint_connection.close()


if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    asyncio.run(run())  # 调用 run 执行当前步骤：asyncio.run(run())
