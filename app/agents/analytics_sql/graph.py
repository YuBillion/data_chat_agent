"""LangGraph subgraph for the analytics SQL agent."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from langgraph.constants import END, START  # 从 langgraph.constants 导入 END, START，供本模块后续代码使用
from langgraph.graph import StateGraph  # 从 langgraph.graph 导入 StateGraph，供本模块后续代码使用

from app.agent.nodes.add_extra_context import add_extra_context  # 从 app.agent.nodes.add_extra_context 导入 add_extra_context，供本模块后续代码使用
from app.agent.nodes.approval_gate import approval_gate  # 从 app.agent.nodes.approval_gate 导入 approval_gate，供本模块后续代码使用
from app.agent.nodes.correct_sql import correct_sql  # 从 app.agent.nodes.correct_sql 导入 correct_sql，供本模块后续代码使用
from app.agent.nodes.filter_metric import filter_metric  # 从 app.agent.nodes.filter_metric 导入 filter_metric，供本模块后续代码使用
from app.agent.nodes.filter_table import filter_table  # 从 app.agent.nodes.filter_table 导入 filter_table，供本模块后续代码使用
from app.agent.nodes.generate_sql import generate_sql  # 从 app.agent.nodes.generate_sql 导入 generate_sql，供本模块后续代码使用
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info  # 从 app.agent.nodes.merge_retrieved_info 导入 merge_retrieved_info，供本模块后续代码使用
from app.agent.nodes.plan_query import plan_query  # 从 app.agent.nodes.plan_query 导入 plan_query，供本模块后续代码使用
from app.agent.nodes.recall_column import recall_column  # 从 app.agent.nodes.recall_column 导入 recall_column，供本模块后续代码使用
from app.agent.nodes.recall_metric import recall_metric  # 从 app.agent.nodes.recall_metric 导入 recall_metric，供本模块后续代码使用
from app.agent.nodes.recall_value import recall_value  # 从 app.agent.nodes.recall_value 导入 recall_value，供本模块后续代码使用
from app.agent.nodes.run_sql import run_sql  # 从 app.agent.nodes.run_sql 导入 run_sql，供本模块后续代码使用
from app.agent.nodes.validate_sql import validate_sql  # 从 app.agent.nodes.validate_sql 导入 validate_sql，供本模块后续代码使用
from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.harness.context import HarnessContext  # 从 app.harness.context 导入 HarnessContext，供本模块后续代码使用
from app.observability.nodes import traced_node  # 从 app.observability.nodes 导入 traced_node，供本模块后续代码使用


async def rejected_node(state: DataAgentState) -> dict:  # 定义异步函数 rejected_node，封装可被事件循环调度的协程逻辑
    del state  # 删除或显式忽略名称 state，避免未使用变量干扰
    return {"agent_output": {"agent_id": "analytics_sql", "status": "rejected"}}  # 返回 {"agent_output": {"agent_id": "analytics_sql", "status": "rejected"}} 给调用方


async def failed_node(state: DataAgentState) -> dict:  # 定义异步函数 failed_node，封装可被事件循环调度的协程逻辑
    return {  # 返回 { 给调用方
        "agent_output": {  # 为多行字典定义键 "agent_output" 及其对应值
            "agent_id": "analytics_sql",  # 为多行字典定义键 "agent_id" 及其对应值
            "status": "failed",  # 为多行字典定义键 "status" 及其对应值
            "text": "SQL 校验在允许的校正次数内未通过。",  # 为多行字典定义键 "text" 及其对应值
            "error_code": "SQL_VALIDATION_FAILED",  # 为多行字典定义键 "error_code" 及其对应值
            "error": state.get("error"),  # 为多行字典定义键 "error" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    }  # 结束上一处多行结构，保持表达式边界清晰


def _validation_route(state: DataAgentState) -> str:  # 定义函数 _validation_route，封装该模块的一项明确职责
    if state.get("error") is None:  # 判断分支条件：if state.get("error") is None:
        return "approval_gate"  # 返回 "approval_gate" 给调用方
    max_corrections = int(state.get("max_corrections", 1))  # 计算 int(state.get("max_corrections", 1)) 并保存到变量 max_corrections
    if int(state.get("correction_count", 0)) < max_corrections:  # 判断分支条件：if int(state.get("correction_count", 0)) < max_corrections:
        return "correct_sql"  # 返回 "correct_sql" 给调用方
    return "failed"  # 返回 "failed" 给调用方


def _approval_route(state: DataAgentState) -> str:  # 定义函数 _approval_route，封装该模块的一项明确职责
    action = state.get("approval_action")  # 计算 state.get("approval_action") 并保存到变量 action
    if action == "validate":  # 判断分支条件：if action == "validate":
        return "validate_sql"  # 返回 "validate_sql" 给调用方
    if action == "reject":  # 判断分支条件：if action == "reject":
        return "rejected"  # 返回 "rejected" 给调用方
    if action == "fail":  # 判断分支条件：if action == "fail":
        return "failed"  # 返回 "failed" 给调用方
    return "run_sql"  # 返回 "run_sql" 给调用方


def build_analytics_graph():  # 定义函数 build_analytics_graph，封装该模块的一项明确职责
    builder = StateGraph(  # 调用 StateGraph 构造结果并保存到 builder
        state_schema=DataAgentState,  # 为 StateGraph 设置关键字参数 state_schema，传入当前行给出的值
        context_schema=HarnessContext,  # 为 StateGraph 设置关键字参数 context_schema，传入当前行给出的值
    )  # 结束函数 build_analytics_graph 的参数及返回类型声明并开始函数体
    builder.add_node("plan_query", traced_node("plan_query", plan_query))  # 调用 add_node 执行当前步骤：builder.add_node("plan_query", traced_node("plan_query", plan_query))
    builder.add_node("recall_column", traced_node("recall_column", recall_column))  # 调用 add_node 执行当前步骤：builder.add_node("recall_column", traced_node("recall_column", recall_c…
    builder.add_node("recall_value", traced_node("recall_value", recall_value))  # 调用 add_node 执行当前步骤：builder.add_node("recall_value", traced_node("recall_value", recall_val…
    builder.add_node("recall_metric", traced_node("recall_metric", recall_metric))  # 调用 add_node 执行当前步骤：builder.add_node("recall_metric", traced_node("recall_metric", recall_m…
    builder.add_node(  # 调用 add_node 执行当前步骤：builder.add_node(
        "merge_retrieved_info",  # 继续向上一处调用或声明传入 "merge_retrieved_info"
        traced_node("merge_retrieved_info", merge_retrieved_info),  # 继续向上一处调用或声明传入 traced_node("merge_retrieved_info", merge_retrieved_info)
    )  # 结束函数 build_analytics_graph 的参数及返回类型声明并开始函数体
    builder.add_node("filter_metric", traced_node("filter_metric", filter_metric))  # 调用 add_node 执行当前步骤：builder.add_node("filter_metric", traced_node("filter_metric", filter_m…
    builder.add_node("filter_table", traced_node("filter_table", filter_table))  # 调用 add_node 执行当前步骤：builder.add_node("filter_table", traced_node("filter_table", filter_tab…
    builder.add_node(  # 调用 add_node 执行当前步骤：builder.add_node(
        "add_extra_context",  # 继续向上一处调用或声明传入 "add_extra_context"
        traced_node("add_extra_context", add_extra_context),  # 继续向上一处调用或声明传入 traced_node("add_extra_context", add_extra_context)
    )  # 结束函数 build_analytics_graph 的参数及返回类型声明并开始函数体
    builder.add_node("generate_sql", traced_node("generate_sql", generate_sql))  # 调用 add_node 执行当前步骤：builder.add_node("generate_sql", traced_node("generate_sql", generate_s…
    builder.add_node("validate_sql", traced_node("validate_sql", validate_sql))  # 调用 add_node 执行当前步骤：builder.add_node("validate_sql", traced_node("validate_sql", validate_s…
    builder.add_node("correct_sql", traced_node("correct_sql", correct_sql))  # 调用 add_node 执行当前步骤：builder.add_node("correct_sql", traced_node("correct_sql", correct_sql))
    builder.add_node(  # 调用 add_node 执行当前步骤：builder.add_node(
        "approval_gate", traced_node("approval_gate", approval_gate)  # 调用 目标函数 执行当前步骤："approval_gate", traced_node("approval_gate", approval_gate)
    )  # 结束函数 build_analytics_graph 的参数及返回类型声明并开始函数体
    builder.add_node("run_sql", traced_node("run_sql", run_sql))  # 调用 add_node 执行当前步骤：builder.add_node("run_sql", traced_node("run_sql", run_sql))
    builder.add_node("rejected", traced_node("rejected", rejected_node))  # 调用 add_node 执行当前步骤：builder.add_node("rejected", traced_node("rejected", rejected_node))
    builder.add_node("failed", traced_node("failed", failed_node))  # 调用 add_node 执行当前步骤：builder.add_node("failed", traced_node("failed", failed_node))

    builder.add_edge(START, "plan_query")  # 调用 add_edge 执行当前步骤：builder.add_edge(START, "plan_query")
    builder.add_edge("plan_query", "recall_column")  # 调用 add_edge 执行当前步骤：builder.add_edge("plan_query", "recall_column")
    builder.add_edge("plan_query", "recall_value")  # 调用 add_edge 执行当前步骤：builder.add_edge("plan_query", "recall_value")
    builder.add_edge("plan_query", "recall_metric")  # 调用 add_edge 执行当前步骤：builder.add_edge("plan_query", "recall_metric")
    builder.add_edge("recall_column", "merge_retrieved_info")  # 调用 add_edge 执行当前步骤：builder.add_edge("recall_column", "merge_retrieved_info")
    builder.add_edge("recall_value", "merge_retrieved_info")  # 调用 add_edge 执行当前步骤：builder.add_edge("recall_value", "merge_retrieved_info")
    builder.add_edge("recall_metric", "merge_retrieved_info")  # 调用 add_edge 执行当前步骤：builder.add_edge("recall_metric", "merge_retrieved_info")
    builder.add_edge("merge_retrieved_info", "filter_table")  # 调用 add_edge 执行当前步骤：builder.add_edge("merge_retrieved_info", "filter_table")
    builder.add_edge("merge_retrieved_info", "filter_metric")  # 调用 add_edge 执行当前步骤：builder.add_edge("merge_retrieved_info", "filter_metric")
    builder.add_edge("filter_table", "add_extra_context")  # 调用 add_edge 执行当前步骤：builder.add_edge("filter_table", "add_extra_context")
    builder.add_edge("filter_metric", "add_extra_context")  # 调用 add_edge 执行当前步骤：builder.add_edge("filter_metric", "add_extra_context")
    builder.add_edge("add_extra_context", "generate_sql")  # 调用 add_edge 执行当前步骤：builder.add_edge("add_extra_context", "generate_sql")
    builder.add_edge("generate_sql", "validate_sql")  # 调用 add_edge 执行当前步骤：builder.add_edge("generate_sql", "validate_sql")
    builder.add_conditional_edges(  # 调用 add_conditional_edges 执行当前步骤：builder.add_conditional_edges(
        "validate_sql",  # 继续向上一处调用或声明传入 "validate_sql"
        _validation_route,  # 继续向上一处调用或声明传入 _validation_route
        {  # 在函数 build_analytics_graph 中执行表达式 {，推进当前业务流程
            "approval_gate": "approval_gate",  # 为多行字典定义键 "approval_gate" 及其对应值
            "correct_sql": "correct_sql",  # 为多行字典定义键 "correct_sql" 及其对应值
            "failed": "failed",  # 为多行字典定义键 "failed" 及其对应值
        },  # 结束上一处多行结构，保持表达式边界清晰
    )  # 结束函数 build_analytics_graph 的参数及返回类型声明并开始函数体
    builder.add_edge("correct_sql", "validate_sql")  # 调用 add_edge 执行当前步骤：builder.add_edge("correct_sql", "validate_sql")
    builder.add_conditional_edges(  # 调用 add_conditional_edges 执行当前步骤：builder.add_conditional_edges(
        "approval_gate",  # 继续向上一处调用或声明传入 "approval_gate"
        _approval_route,  # 继续向上一处调用或声明传入 _approval_route
        {  # 在函数 build_analytics_graph 中执行表达式 {，推进当前业务流程
            "validate_sql": "validate_sql",  # 为多行字典定义键 "validate_sql" 及其对应值
            "run_sql": "run_sql",  # 为多行字典定义键 "run_sql" 及其对应值
            "rejected": "rejected",  # 为多行字典定义键 "rejected" 及其对应值
            "failed": "failed",  # 为多行字典定义键 "failed" 及其对应值
        },  # 结束上一处多行结构，保持表达式边界清晰
    )  # 结束函数 build_analytics_graph 的参数及返回类型声明并开始函数体
    builder.add_edge("run_sql", END)  # 调用 add_edge 执行当前步骤：builder.add_edge("run_sql", END)
    builder.add_edge("rejected", END)  # 调用 add_edge 执行当前步骤：builder.add_edge("rejected", END)
    builder.add_edge("failed", END)  # 调用 add_edge 执行当前步骤：builder.add_edge("failed", END)
    return builder.compile(name="analytics_sql")  # 返回 builder.compile(name="analytics_sql") 给调用方


def build_graph():  # 定义函数 build_graph，封装该模块的一项明确职责
    return build_analytics_graph()  # 返回 build_analytics_graph() 给调用方
