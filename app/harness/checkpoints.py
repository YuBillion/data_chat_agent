"""LangGraph PostgreSQL checkpointer lifecycle."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from contextlib import asynccontextmanager  # 从 contextlib 导入 asynccontextmanager，供本模块后续代码使用
from typing import AsyncIterator  # 从 typing 导入 AsyncIterator，供本模块后续代码使用

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # 从 langgraph.checkpoint.postgres.aio 导入 AsyncPostgresSaver，供本模块后续代码使用
from psycopg import AsyncConnection  # 从 psycopg 导入 AsyncConnection，供本模块后续代码使用
from psycopg.rows import dict_row  # 从 psycopg.rows 导入 dict_row，供本模块后续代码使用

from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.harness.database import libpq_postgres_dsn  # 从 app.harness.database 导入 libpq_postgres_dsn，供本模块后续代码使用


@asynccontextmanager  # 应用装饰器 asynccontextmanager，为紧随其后的定义附加框架行为
async def open_postgres_checkpointer(  # 定义异步函数 open_postgres_checkpointer，封装可被事件循环调度的协程逻辑
    settings: Settings,  # 为函数 open_postgres_checkpointer 声明参数 settings 及其类型或默认值
) -> AsyncIterator[AsyncPostgresSaver]:  # 结束 open_postgres_checkpointer 的参数列表并声明返回类型
    options = f"-c search_path={settings.postgres_langgraph_schema},public"  # 计算 f"-c search_path={settings.postgres_langgraph_schema},public" 并保存到变量 options
    connection = await AsyncConnection.connect(  # 等待 connect 完成，并将其结果保存到 connection
        libpq_postgres_dsn(settings.postgres_dsn),  # 继续向上一处调用或声明传入 libpq_postgres_dsn(settings.postgres_dsn)
        autocommit=True,  # 为 AsyncConnection.connect 设置关键字参数 autocommit，传入当前行给出的值
        prepare_threshold=0,  # 为 AsyncConnection.connect 设置关键字参数 prepare_threshold，传入当前行给出的值
        row_factory=dict_row,  # 为 AsyncConnection.connect 设置关键字参数 row_factory，传入当前行给出的值
        options=options,  # 为 AsyncConnection.connect 设置关键字参数 options，传入当前行给出的值
    )  # 结束函数 open_postgres_checkpointer 的参数及返回类型声明并开始函数体
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        yield AsyncPostgresSaver(connection)  # 产出流式结果 AsyncPostgresSaver(connection)，保留生成器后续执行状态
    finally:  # 进入无论成功失败都必须执行的资源清理分支
        await connection.close()  # 等待异步操作完成并取得结果：connection.close()
