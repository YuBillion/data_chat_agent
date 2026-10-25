"""Concurrent field-value full-text retrieval."""

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用

from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.nodes.retrieval_utils import bounded_gather  # 从 app.agent.nodes.retrieval_utils 导入 bounded_gather，供本模块后续代码使用
from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.entities.value_info import ValueInfo  # 从 app.entities.value_info 导入 ValueInfo，供本模块后续代码使用


async def recall_value(  # 定义异步函数 recall_value，封装可被事件循环调度的协程逻辑
    state: DataAgentState, runtime: Runtime[DataAgentContext]  # 为函数 recall_value 声明参数 state 及其类型或默认值
) -> dict:  # 结束 recall_value 的参数列表并声明返回类型
    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "召回字段取值"  # 计算 "召回字段取值" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})
    context = runtime.context  # 计算 runtime.context 并保存到变量 context
    terms = (  # 调用 目标函数 构造结果并保存到 terms
        state.get("value_terms")  # 调用 get 执行当前步骤：state.get("value_terms")
        or state.get("keywords")  # 调用 目标函数 执行当前步骤：or state.get("keywords")
        or [state.get("resolved_query") or state["query"]]  # 调用 目标函数 执行当前步骤：or [state.get("resolved_query") or state["query"]]
    )  # 结束函数 recall_value 的参数及返回类型声明并开始函数体
    repository = context["value_es_repository"]  # 计算 context["value_es_repository"] 并保存到变量 repository
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        async def search(term: str) -> list[ValueInfo]:  # 定义异步函数 search，封装可被事件循环调度的协程逻辑
            async with context["tool_semaphore"]:  # 进入受管理的上下文 async with context["tool_semaphore"]:，确保资源正确获取与释放
                async with asyncio.timeout(  # 进入受管理的上下文 async with asyncio.timeout(，确保资源正确获取与释放
                    context["settings"].tool_timeout_seconds  # 在函数 search 中执行表达式 context["settings"].tool_timeout_seconds，推进当前业务流程
                ):  # 结束 search 的参数列表并声明返回类型
                    return await repository.search(term)  # 返回 await repository.search(term) 给调用方

        batches = await bounded_gather(  # 等待 bounded_gather 完成，并将其结果保存到 batches
            list(dict.fromkeys(terms)),  # 继续向上一处调用或声明传入 list(dict.fromkeys(terms))
            search,  # 继续向上一处调用或声明传入 search
            concurrency=context["settings"].retrieval_max_concurrency,  # 为 bounded_gather 设置关键字参数 concurrency，传入当前行给出的值
        )  # 结束函数 recall_value 的参数及返回类型声明并开始函数体
        unique: dict[str, ValueInfo] = {}  # 计算 {} 并保存到变量 unique
        for batch in batches:  # 按迭代条件执行循环：for batch in batches:
            for item in batch:  # 按迭代条件执行循环：for item in batch:
                unique.setdefault(item.id, item)  # 调用 setdefault 执行当前步骤：unique.setdefault(item.id, item)
        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_value_infos": list(unique.values())}  # 返回 {"retrieved_value_infos": list(unique.values())} 给调用方
    except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
        logger.error("{} failed: {}", step, type(exc).__name__)  # 调用 error 执行当前步骤：logger.error("{} failed: {}", step, type(exc).__name__)
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
