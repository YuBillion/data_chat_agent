"""Runtime tool allowlist enforcement for code-defined agents."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from app.core.errors import ForbiddenError  # 从 app.core.errors 导入 ForbiddenError，供本模块后续代码使用
from app.harness.context import HarnessContext  # 从 app.harness.context 导入 HarnessContext，供本模块后续代码使用


def require_tool_access(  # 定义函数 require_tool_access，封装该模块的一项明确职责
    context: HarnessContext,  # 为函数 require_tool_access 声明参数 context 及其类型或默认值
    state: dict,  # 为函数 require_tool_access 声明参数 state 及其类型或默认值
    tool_name: str,  # 为函数 require_tool_access 声明参数 tool_name 及其类型或默认值
) -> None:  # 结束 require_tool_access 的参数列表并声明返回类型
    agent_id = state.get("selected_agent_id")  # 计算 state.get("selected_agent_id") 并保存到变量 agent_id
    if not agent_id:  # 判断分支条件：if not agent_id:
        raise ForbiddenError("agent must be selected before using tools")  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError("agent must be selected before using tools")
    definition = context["registry"].get(str(agent_id))  # 计算 context["registry"].get(str(agent_id)) 并保存到变量 definition
    if tool_name not in definition.allowed_tools:  # 判断分支条件：if tool_name not in definition.allowed_tools:
        raise ForbiddenError(  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError(
            f"tool {tool_name} is not allowed for agent {agent_id}"  # 在函数 require_tool_access 中执行表达式 f"tool {tool_name} is not allowed for agent {agent_id}"，推进当前业务流程
        )  # 结束 ForbiddenError 调用参数，得到完整表达式结果
