"""LangGraph interrupt gate for risky or corrected SQL."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用
from langgraph.types import interrupt  # 从 langgraph.types 导入 interrupt，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.core.errors import ConflictError  # 从 app.core.errors 导入 ConflictError，供本模块后续代码使用


async def approval_gate(  # 定义异步函数 approval_gate，封装可被事件循环调度的协程逻辑
    state: DataAgentState, runtime: Runtime[DataAgentContext]  # 为函数 approval_gate 声明参数 state 及其类型或默认值
) -> dict:  # 结束 approval_gate 的参数列表并声明返回类型
    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "SQL审批"  # 计算 "SQL审批" 并保存到变量 step
    if not state.get("approval_required"):  # 判断分支条件：if not state.get("approval_required"):
        return {"approval_action": "approve"}  # 返回 {"approval_action": "approve"} 给调用方
    max_rounds = runtime.context["settings"].max_approval_rounds  # 计算 runtime.context["settings"].max_approval_rounds 并保存到变量 max_rounds
    if state.get("approval_rounds", 0) >= max_rounds:  # 判断分支条件：if state.get("approval_rounds", 0) >= max_rounds:
        return {  # 返回 { 给调用方
            "approval_action": "fail",  # 为多行字典定义键 "approval_action" 及其对应值
            "agent_output": {  # 为多行字典定义键 "agent_output" 及其对应值
                "agent_id": "analytics_sql",  # 为多行字典定义键 "agent_id" 及其对应值
                "text": "SQL 在最大人工审批轮次内仍未获批准。",  # 为多行字典定义键 "text" 及其对应值
                "error_code": "APPROVAL_ROUND_LIMIT",  # 为多行字典定义键 "error_code" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        }  # 结束上一处多行结构，保持表达式边界清晰
    payload = {  # 计算 { 并保存到变量 payload
        "kind": "sql_approval",  # 为多行字典定义键 "kind" 及其对应值
        "sql": state.get("executed_sql") or state["sql"],  # 为多行字典定义键 "sql" 及其对应值
        "sql_hash": state.get("sql_hash"),  # 为多行字典定义键 "sql_hash" 及其对应值
        "tables": state.get("risk_tables", []),  # 为多行字典定义键 "tables" 及其对应值
        "columns": state.get("risk_columns", []),  # 为多行字典定义键 "columns" 及其对应值
        "estimated_rows": state.get("estimated_rows"),  # 为多行字典定义键 "estimated_rows" 及其对应值
        "risk_reasons": state.get("risk_reasons", []),  # 为多行字典定义键 "risk_reasons" 及其对应值
        "high_risk": state.get("high_risk", False),  # 为多行字典定义键 "high_risk" 及其对应值
        "round": state.get("approval_rounds", 0) + 1,  # 为多行字典定义键 "round" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰
    writer({"type": "sql.approval_required", "data": payload})  # 调用 writer 执行当前步骤：writer({"type": "sql.approval_required", "data": payload})
    decision = interrupt(payload)  # 计算 interrupt(payload) 并保存到变量 decision
    if not isinstance(decision, dict):  # 判断分支条件：if not isinstance(decision, dict):
        raise ConflictError("INVALID_APPROVAL_RESPONSE", "approval response is invalid")  # 抛出明确异常，阻止错误状态被静默接受：ConflictError("INVALID_APPROVAL_RESPONSE", "approval response is invali…
    if decision.get("sql_hash") != payload["sql_hash"]:  # 判断分支条件：if decision.get("sql_hash") != payload["sql_hash"]:
        raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
            "STALE_APPROVAL",  # 继续向上一处调用或声明传入 "STALE_APPROVAL"
            "approval does not match the current SQL",  # 继续向上一处调用或声明传入 "approval does not match the current SQL"
        )  # 结束函数 approval_gate 的参数及返回类型声明并开始函数体
    action = str(decision.get("action", ""))  # 计算 str(decision.get("action", "")) 并保存到变量 action
    writer(  # 调用 writer 执行当前步骤：writer(
        {  # 在函数 approval_gate 中执行表达式 {，推进当前业务流程
            "type": "progress",  # 为多行字典定义键 "type" 及其对应值
            "step": step,  # 为多行字典定义键 "step" 及其对应值
            "status": "success",  # 为多行字典定义键 "status" 及其对应值
            "action": action,  # 为多行字典定义键 "action" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    )  # 结束函数 approval_gate 的参数及返回类型声明并开始函数体
    if action == "reject":  # 判断分支条件：if action == "reject":
        return {  # 返回 { 给调用方
            "approval_action": "reject",  # 为多行字典定义键 "approval_action" 及其对应值
            "approval_rounds": payload["round"],  # 为多行字典定义键 "approval_rounds" 及其对应值
            "agent_output": {  # 为多行字典定义键 "agent_output" 及其对应值
                "agent_id": "analytics_sql",  # 为多行字典定义键 "agent_id" 及其对应值
                "text": "SQL 执行已被审批人拒绝。",  # 为多行字典定义键 "text" 及其对应值
                "reason": decision.get("reason"),  # 为多行字典定义键 "reason" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        }  # 结束上一处多行结构，保持表达式边界清晰
    if action == "edit":  # 判断分支条件：if action == "edit":
        edited_sql = str(decision.get("edited_sql", "")).strip()  # 计算 str(decision.get("edited_sql", "")).strip() 并保存到变量 edited_sql
        if not edited_sql:  # 判断分支条件：if not edited_sql:
            raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
                "INVALID_EDIT", "edited SQL is required for an edit decision"  # 在函数 approval_gate 中执行表达式 "INVALID_EDIT", "edited SQL is required for an edit decision"，推进当前业务流程
            )  # 结束函数 approval_gate 的参数及返回类型声明并开始函数体
        return {  # 返回 { 给调用方
            "sql": edited_sql,  # 为多行字典定义键 "sql" 及其对应值
            "human_edited_sql": True,  # 为多行字典定义键 "human_edited_sql" 及其对应值
            "approval_rounds": payload["round"],  # 为多行字典定义键 "approval_rounds" 及其对应值
            "approval_action": "validate",  # 为多行字典定义键 "approval_action" 及其对应值
            "error": None,  # 为多行字典定义键 "error" 及其对应值
            "executed_sql": None,  # 为多行字典定义键 "executed_sql" 及其对应值
            "sql_hash": None,  # 为多行字典定义键 "sql_hash" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    if action == "approve":  # 判断分支条件：if action == "approve":
        return {  # 返回 { 给调用方
            "approval_action": "approve",  # 为多行字典定义键 "approval_action" 及其对应值
            "approval_rounds": payload["round"],  # 为多行字典定义键 "approval_rounds" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    raise ConflictError("INVALID_APPROVAL_ACTION", "unsupported approval action")  # 抛出明确异常，阻止错误状态被静默接受：ConflictError("INVALID_APPROVAL_ACTION", "unsupported approval action")
