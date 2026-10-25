"""Standalone durable worker entry point."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import signal  # 导入signal，建立本模块需要的外部能力引用

from app.application import create_container  # 从 app.application 导入 create_container，供本模块后续代码使用
from app.conf.settings import get_settings  # 从 app.conf.settings 导入 get_settings，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用


async def main() -> None:  # 定义异步函数 main，封装可被事件循环调度的协程逻辑
    stop = asyncio.Event()  # 计算 asyncio.Event() 并保存到变量 stop
    loop = asyncio.get_running_loop()  # 计算 asyncio.get_running_loop() 并保存到变量 loop
    for sig in (signal.SIGINT, signal.SIGTERM):  # 按迭代条件执行循环：for sig in (signal.SIGINT, signal.SIGTERM):
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            loop.add_signal_handler(sig, stop.set)  # 调用 add_signal_handler 执行当前步骤：loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError):  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except (NotImplementedError, RuntimeError):
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))  # 调用 signal 执行当前步骤：signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))
    settings = get_settings()  # 计算 get_settings() 并保存到变量 settings
    container = create_container(settings)  # 计算 create_container(settings) 并保存到变量 container
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        await container.start(with_worker=True)  # 等待异步操作完成并取得结果：container.start(with_worker=True)
        await stop.wait()  # 等待异步操作完成并取得结果：stop.wait()
    finally:  # 进入无论成功失败都必须执行的资源清理分支
        await container.close()  # 等待异步操作完成并取得结果：container.close()
        logger.info("Worker process stopped")  # 调用 info 执行当前步骤：logger.info("Worker process stopped")


if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    asyncio.run(main())  # 调用 run 执行当前步骤：asyncio.run(main())
