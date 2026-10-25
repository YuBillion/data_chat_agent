"""Lightweight process health checks used by Docker Compose."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import sys  # 导入sys，建立本模块需要的外部能力引用

import httpx  # 导入httpx，建立本模块需要的外部能力引用
from sqlalchemy import text  # 从 sqlalchemy 导入 text，供本模块后续代码使用

from app.clients.embedding_client_manager import embedding_client_manager  # 从 app.clients.embedding_client_manager 导入 embedding_client_manager，供本模块后续代码使用
from app.clients.es_client_manager import es_client_manager  # 从 app.clients.es_client_manager 导入 es_client_manager，供本模块后续代码使用
from app.clients.mysql_client_manager import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    dw_mysql_client_manager,  # 从当前 import 模块导入符号 dw_mysql_client_manager
    meta_mysql_client_manager,  # 从当前 import 模块导入符号 meta_mysql_client_manager
)  # 结束多符号导入列表
from app.clients.qdrant_client_manager import qdrant_client_manager  # 从 app.clients.qdrant_client_manager 导入 qdrant_client_manager，供本模块后续代码使用
from app.conf.settings import get_settings  # 从 app.conf.settings 导入 get_settings，供本模块后续代码使用
from app.harness.database import HarnessDatabase  # 从 app.harness.database 导入 HarnessDatabase，供本模块后续代码使用
from app.harness.redis_runtime import RedisRuntime  # 从 app.harness.redis_runtime 导入 RedisRuntime，供本模块后续代码使用


async def check() -> None:  # 定义异步函数 check，封装可被事件循环调度的协程逻辑
    settings = get_settings()  # 计算 get_settings() 并保存到变量 settings
    database = HarnessDatabase(settings)  # 计算 HarnessDatabase(settings) 并保存到变量 database
    redis = RedisRuntime(settings)  # 计算 RedisRuntime(settings) 并保存到变量 redis
    qdrant_client_manager.init()  # 调用 init 执行当前步骤：qdrant_client_manager.init()
    es_client_manager.init()  # 调用 init 执行当前步骤：es_client_manager.init()
    meta_mysql_client_manager.init()  # 调用 init 执行当前步骤：meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()  # 调用 init 执行当前步骤：dw_mysql_client_manager.init()
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        await asyncio.wait_for(database.ping(), timeout=3)  # 等待异步操作完成并取得结果：asyncio.wait_for(database.ping(), timeout=3)
        await asyncio.wait_for(redis.ping(), timeout=3)  # 等待异步操作完成并取得结果：asyncio.wait_for(redis.ping(), timeout=3)
        async with (  # 进入受管理的上下文 async with (，确保资源正确获取与释放
            meta_mysql_client_manager.session_factory() as meta_session,  # 继续向上一处调用或声明传入 meta_mysql_client_manager.session_factory() as meta_session
            dw_mysql_client_manager.session_factory() as dw_session,  # 继续向上一处调用或声明传入 dw_mysql_client_manager.session_factory() as dw_session
        ):  # 结束 check 的参数列表并声明返回类型
            await meta_session.execute(text("select 1"))  # 等待异步操作完成并取得结果：meta_session.execute(text("select 1"))
            await dw_session.execute(text("select 1"))  # 等待异步操作完成并取得结果：dw_session.execute(text("select 1"))
        if qdrant_client_manager.client is not None:  # 判断分支条件：if qdrant_client_manager.client is not None:
            await asyncio.wait_for(  # 等待异步操作完成并取得结果：asyncio.wait_for(
                qdrant_client_manager.client.get_collections(), timeout=3  # 调用 get_collections 执行当前步骤：qdrant_client_manager.client.get_collections(), timeout=3
            )  # 结束 asyncio.wait_for 调用参数，得到完整表达式结果
        if es_client_manager.client is not None:  # 判断分支条件：if es_client_manager.client is not None:
            await asyncio.wait_for(es_client_manager.client.ping(), timeout=3)  # 等待异步操作完成并取得结果：asyncio.wait_for(es_client_manager.client.ping(), timeout=3)
        async with httpx.AsyncClient(timeout=3) as client:  # 进入受管理的上下文 async with httpx.AsyncClient(timeout=3) as client:，确保资源正确获取与释放
            response = await client.get(  # 等待 get 完成，并将其结果保存到 response
                f"http://{embedding_client_manager.config.host}:"  # 在函数 check 中执行表达式 f"http://{embedding_client_manager.config.host}:"，推进当前业务流程
                f"{embedding_client_manager.config.port}/health"  # 在函数 check 中执行表达式 f"{embedding_client_manager.config.port}/health"，推进当前业务流程
            )  # 结束 client.get 调用参数，得到完整表达式结果
            response.raise_for_status()  # 调用 raise_for_status 执行当前步骤：response.raise_for_status()
    finally:  # 进入无论成功失败都必须执行的资源清理分支
        await qdrant_client_manager.close()  # 等待异步操作完成并取得结果：qdrant_client_manager.close()
        await es_client_manager.close()  # 等待异步操作完成并取得结果：es_client_manager.close()
        await meta_mysql_client_manager.close()  # 等待异步操作完成并取得结果：meta_mysql_client_manager.close()
        await dw_mysql_client_manager.close()  # 等待异步操作完成并取得结果：dw_mysql_client_manager.close()
        await redis.close()  # 等待异步操作完成并取得结果：redis.close()
        await database.close()  # 等待异步操作完成并取得结果：database.close()


if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        asyncio.run(check())  # 调用 run 执行当前步骤：asyncio.run(check())
    except Exception:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception:
        sys.exit(1)  # 调用 exit 执行当前步骤：sys.exit(1)
