"""LangGraph node tracing that does not alter node business behavior."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from functools import wraps  # 从 functools 导入 wraps，供本模块后续代码使用
from typing import Any, Callable  # 从 typing 导入 Any, Callable，供本模块后续代码使用

from langgraph.errors import GraphInterrupt  # 从 langgraph.errors 导入 GraphInterrupt，供本模块后续代码使用


def traced_node(name: str, node: Callable[..., Any]) -> Callable[..., Any]:  # 定义函数 traced_node，封装该模块的一项明确职责
    @wraps(node)  # 应用装饰器 wraps(node)，为紧随其后的定义附加框架行为
    async def wrapped(*args: Any, **kwargs: Any) -> Any:  # 定义异步函数 wrapped，封装可被事件循环调度的协程逻辑
        runtime = args[1] if len(args) > 1 else None  # 计算 args[1] if len(args) > 1 else None 并保存到变量 runtime
        telemetry = (  # 调用 目标函数 构造结果并保存到 telemetry
            runtime.context.get("telemetry")  # 调用 get 执行当前步骤：runtime.context.get("telemetry")
            if runtime is not None and hasattr(runtime, "context")  # 判断分支条件：if runtime is not None and hasattr(runtime, "context")
            else None  # 在函数 wrapped 中执行表达式 else None，推进当前业务流程
        )  # 结束函数 wrapped 的调用或声明结构
        if telemetry is None:  # 判断分支条件：if telemetry is None:
            return await node(*args, **kwargs)  # 返回 await node(*args, **kwargs) 给调用方
        state = args[0] if args and isinstance(args[0], dict) else {}  # 计算 args[0] if args and isinstance(args[0], dict) else {} 并保存到变量 state
        attributes = {  # 计算 { 并保存到变量 attributes
            "langgraph.node": name,  # 为多行字典定义键 "langgraph.node" 及其对应值
            "agent.id": state.get("selected_agent_id") or "unselected",  # 为多行字典定义键 "agent.id" 及其对应值
            "run.id": state.get("run_id") or "-",  # 为多行字典定义键 "run.id" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
        with telemetry.tracer.start_as_current_span(  # 进入受管理的上下文 with telemetry.tracer.start_as_current_span(，确保资源正确获取与释放
            f"langgraph.node.{name}", attributes=attributes  # 在函数 wrapped 中执行表达式 f"langgraph.node.{name}", attributes=attributes，推进当前业务流程
        ) as span:  # 在函数 wrapped 中执行表达式 ) as span:，推进当前业务流程
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                return await node(*args, **kwargs)  # 返回 await node(*args, **kwargs) 给调用方
            except GraphInterrupt:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except GraphInterrupt:
                span.set_attribute("langgraph.interrupted", True)  # 调用 set_attribute 执行当前步骤：span.set_attribute("langgraph.interrupted", True)
                raise  # 重新抛出当前异常，保留原始失败上下文
            except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
                telemetry.record_exception(span, exc)  # 调用 record_exception 执行当前步骤：telemetry.record_exception(span, exc)
                raise  # 重新抛出当前异常，保留原始失败上下文

    return wrapped  # 返回 wrapped 给调用方
