"""Top-level LangGraph routing shell for registered agents."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from langgraph.checkpoint.base import BaseCheckpointSaver  # 从 langgraph.checkpoint.base 导入 BaseCheckpointSaver，供本模块后续代码使用
from langgraph.constants import END, START  # 从 langgraph.constants 导入 END, START，供本模块后续代码使用
from langgraph.graph import StateGraph  # 从 langgraph.graph 导入 StateGraph，供本模块后续代码使用
from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用
from langgraph.types import interrupt  # 从 langgraph.types 导入 interrupt，供本模块后续代码使用

from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.agents.registry import AgentRegistry  # 从 app.agents.registry 导入 AgentRegistry，供本模块后续代码使用
from app.core.errors import ConflictError  # 从 app.core.errors 导入 ConflictError，供本模块后续代码使用
from app.harness.context import HarnessContext  # 从 app.harness.context 导入 HarnessContext，供本模块后续代码使用
from app.harness.records import AuditRecord  # 从 app.harness.records 导入 AuditRecord，供本模块后续代码使用
from app.harness.types import RouteMode  # 从 app.harness.types 导入 RouteMode，供本模块后续代码使用
from app.observability.nodes import traced_node  # 从 app.observability.nodes 导入 traced_node，供本模块后续代码使用


class HarnessState(DataAgentState, total=False):  # 定义类 HarnessState，组织相关状态与行为
    session_id: str  # 声明或继续传入参数 session_id: str
    run_id: str  # 声明或继续传入参数 run_id: str
    requested_agent_id: str | None  # 声明或继续传入参数 requested_agent_id: str | None
    selected_agent_id: str | None  # 声明或继续传入参数 selected_agent_id: str | None
    agent_version: str | None  # 声明或继续传入参数 agent_version: str | None
    route_mode: str | None  # 声明或继续传入参数 route_mode: str | None
    route_confidence: float | None  # 声明或继续传入参数 route_confidence: float | None
    route_reason_code: str | None  # 声明或继续传入参数 route_reason_code: str | None
    route_candidates: list[dict]  # 声明或继续传入参数 route_candidates: list[dict]
    run_outcome_status: str | None  # 声明或继续传入参数 run_outcome_status: str | None
    max_corrections: int  # 声明或继续传入参数 max_corrections: int


async def load_session_context(  # 定义异步函数 load_session_context，封装可被事件循环调度的协程逻辑
    state: HarnessState, runtime: Runtime[HarnessContext]  # 为函数 load_session_context 声明参数 state 及其类型或默认值
) -> dict:  # 结束 load_session_context 的参数列表并声明返回类型
    runtime.context["budget"].start_clock()  # 调用 目标函数 执行当前步骤：runtime.context["budget"].start_clock()
    return {  # 返回 { 给调用方
        "correction_count": state.get("correction_count", 0),  # 为多行字典定义键 "correction_count" 及其对应值
        "approval_rounds": state.get("approval_rounds", 0),  # 为多行字典定义键 "approval_rounds" 及其对应值
        "human_edited_sql": state.get("human_edited_sql", False),  # 为多行字典定义键 "human_edited_sql" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰


async def route_agent(  # 定义异步函数 route_agent，封装可被事件循环调度的协程逻辑
    state: HarnessState, runtime: Runtime[HarnessContext]  # 为函数 route_agent 声明参数 state 及其类型或默认值
) -> dict:  # 结束 route_agent 的参数列表并声明返回类型
    context = runtime.context  # 计算 runtime.context 并保存到变量 context
    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    identity = context["identity"]  # 计算 context["identity"] 并保存到变量 identity
    decision = await context["router"].route(  # 等待 目标函数 完成，并将其结果保存到 decision
        identity=identity,  # 为 route 设置关键字参数 identity，传入当前行给出的值
        query=state["query"],  # 为 route 设置关键字参数 query，传入当前行给出的值
        requested_agent_id=state.get("requested_agent_id"),  # 为 state.get 设置关键字参数 requested_agent_id，传入当前行给出的值
        history=state.get("conversation", []),  # 为 state.get 设置关键字参数 history，传入当前行给出的值
        llm=context["llm"],  # 为 route 设置关键字参数 llm，传入当前行给出的值
    )  # 结束函数 route_agent 的参数及返回类型声明并开始函数体
    route = decision.as_dict()  # 计算 decision.as_dict() 并保存到变量 route
    if decision.selected_agent_id:  # 判断分支条件：if decision.selected_agent_id:
        definition = context["registry"].get(decision.selected_agent_id)  # 计算 context["registry"].get(decision.selected_agent_id) 并保存到变量 definition
        context["llm"].agent_id = definition.agent_id  # 计算 definition.agent_id 并保存到变量 context["llm"].agent_id
        route["agent_version"] = definition.version  # 计算 definition.version 并保存到变量 route["agent_version"]
        route["state_schema_version"] = definition.state_schema_version  # 计算 definition.state_schema_version 并保存到变量 route["state_schema_version"]
        route["prompt_versions"] = context["registry"].prompt_manifest(  # 调用 目标函数 构造结果并保存到 route["prompt_versions"]
            definition.agent_id  # 在函数 route_agent 中执行表达式 definition.agent_id，推进当前业务流程
        )  # 结束函数 route_agent 的参数及返回类型声明并开始函数体
        route["model_profile"] = definition.model_profile  # 计算 definition.model_profile 并保存到变量 route["model_profile"]
        await context["store"].set_run_route(  # 等待异步操作完成并取得结果：context["store"].set_run_route(
            _run_uuid(state),  # 继续向上一处调用或声明传入 _run_uuid(state)
            selected_agent_id=definition.agent_id,  # 为 set_run_route 设置关键字参数 selected_agent_id，传入当前行给出的值
            agent_version=definition.version,  # 为 set_run_route 设置关键字参数 agent_version，传入当前行给出的值
            route_mode=decision.mode,  # 为 set_run_route 设置关键字参数 route_mode，传入当前行给出的值
            confidence=decision.confidence,  # 为 set_run_route 设置关键字参数 confidence，传入当前行给出的值
            route=route,  # 为 set_run_route 设置关键字参数 route，传入当前行给出的值
        )  # 结束函数 route_agent 的参数及返回类型声明并开始函数体
        await context["store"].add_audit(  # 等待异步操作完成并取得结果：context["store"].add_audit(
            AuditRecord(  # 调用 AuditRecord 执行当前步骤：AuditRecord(
                id=_run_uuid(state),  # 为 _run_uuid 设置关键字参数 id，传入当前行给出的值
                tenant_id=identity.tenant_id,  # 为 AuditRecord 设置关键字参数 tenant_id，传入当前行给出的值
                actor_id=identity.user_id,  # 为 AuditRecord 设置关键字参数 actor_id，传入当前行给出的值
                action="agent.route",  # 为 AuditRecord 设置关键字参数 action，传入当前行给出的值
                resource_type="run",  # 为 AuditRecord 设置关键字参数 resource_type，传入当前行给出的值
                resource_id=str(_run_uuid(state)),  # 为 str 设置关键字参数 resource_id，传入当前行给出的值
                outcome="selected",  # 为 AuditRecord 设置关键字参数 outcome，传入当前行给出的值
                trace_id=context.get("trace_id"),  # 为 context.get 设置关键字参数 trace_id，传入当前行给出的值
                metadata={  # 为 AuditRecord 设置关键字参数 metadata，传入当前行给出的值
                    "agent_id": definition.agent_id,  # 为多行字典定义键 "agent_id" 及其对应值
                    "agent_version": definition.version,  # 为多行字典定义键 "agent_version" 及其对应值
                    "mode": decision.mode.value,  # 为多行字典定义键 "mode" 及其对应值
                    "confidence": decision.confidence,  # 为多行字典定义键 "confidence" 及其对应值
                    "reason_code": decision.reason_code,  # 为多行字典定义键 "reason_code" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束函数 route_agent 的参数及返回类型声明并开始函数体
        )  # 结束函数 route_agent 的参数及返回类型声明并开始函数体
        writer(  # 调用 writer 执行当前步骤：writer(
            {  # 在函数 route_agent 中执行表达式 {，推进当前业务流程
                "type": "agent.selected",  # 为多行字典定义键 "type" 及其对应值
                "data": route,  # 为多行字典定义键 "data" 及其对应值
            }  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束函数 route_agent 的参数及返回类型声明并开始函数体
        context["telemetry"].metrics.route_selections.add(  # 调用 目标函数 执行当前步骤：context["telemetry"].metrics.route_selections.add(
            1,  # 继续向上一处调用或声明传入 1
            {  # 在函数 route_agent 中执行表达式 {，推进当前业务流程
                "agent_id": definition.agent_id,  # 为多行字典定义键 "agent_id" 及其对应值
                "mode": decision.mode.value,  # 为多行字典定义键 "mode" 及其对应值
                "result": "selected",  # 为多行字典定义键 "result" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束函数 route_agent 的参数及返回类型声明并开始函数体
        return {  # 返回 { 给调用方
            "selected_agent_id": definition.agent_id,  # 为多行字典定义键 "selected_agent_id" 及其对应值
            "agent_version": definition.version,  # 为多行字典定义键 "agent_version" 及其对应值
            "route_mode": decision.mode.value,  # 为多行字典定义键 "route_mode" 及其对应值
            "route_confidence": decision.confidence,  # 为多行字典定义键 "route_confidence" 及其对应值
            "route_reason_code": decision.reason_code,  # 为多行字典定义键 "route_reason_code" 及其对应值
            "route_candidates": route["candidates"],  # 为多行字典定义键 "route_candidates" 及其对应值
            "resolved_query": decision.resolved_query,  # 为多行字典定义键 "resolved_query" 及其对应值
            "run_outcome_status": "running",  # 为多行字典定义键 "run_outcome_status" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    writer(  # 调用 writer 执行当前步骤：writer(
        {  # 在函数 route_agent 中执行表达式 {，推进当前业务流程
            "type": "agent.selection_required",  # 为多行字典定义键 "type" 及其对应值
            "data": route,  # 为多行字典定义键 "data" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    )  # 结束函数 route_agent 的参数及返回类型声明并开始函数体
    return {  # 返回 { 给调用方
        "selected_agent_id": None,  # 为多行字典定义键 "selected_agent_id" 及其对应值
        "route_mode": decision.mode.value,  # 为多行字典定义键 "route_mode" 及其对应值
        "route_confidence": decision.confidence,  # 为多行字典定义键 "route_confidence" 及其对应值
        "route_reason_code": decision.reason_code,  # 为多行字典定义键 "route_reason_code" 及其对应值
        "route_candidates": route["candidates"],  # 为多行字典定义键 "route_candidates" 及其对应值
        "resolved_query": decision.resolved_query,  # 为多行字典定义键 "resolved_query" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰


async def route_confirmation_gate(  # 定义异步函数 route_confirmation_gate，封装可被事件循环调度的协程逻辑
    state: HarnessState, runtime: Runtime[HarnessContext]  # 为函数 route_confirmation_gate 声明参数 state 及其类型或默认值
) -> dict:  # 结束 route_confirmation_gate 的参数列表并声明返回类型
    if state.get("selected_agent_id"):  # 判断分支条件：if state.get("selected_agent_id"):
        return {"run_outcome_status": "running"}  # 返回 {"run_outcome_status": "running"} 给调用方
    context = runtime.context  # 计算 runtime.context 并保存到变量 context
    payload = {  # 计算 { 并保存到变量 payload
        "kind": "agent_selection",  # 为多行字典定义键 "kind" 及其对应值
        "query": state["query"],  # 为多行字典定义键 "query" 及其对应值
        "resolved_query": state.get("resolved_query") or state["query"],  # 为多行字典定义键 "resolved_query" 及其对应值
        "reason_code": state.get("route_reason_code"),  # 为多行字典定义键 "reason_code" 及其对应值
        "candidates": state.get("route_candidates", []),  # 为多行字典定义键 "candidates" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰
    selected = interrupt(payload)  # 计算 interrupt(payload) 并保存到变量 selected
    if not isinstance(selected, dict):  # 判断分支条件：if not isinstance(selected, dict):
        raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
            "INVALID_AGENT_SELECTION", "agent selection response is invalid"  # 在函数 route_confirmation_gate 中执行表达式 "INVALID_AGENT_SELECTION", "agent selection response is invalid"，推进当前业务流程
        )  # 结束函数 route_confirmation_gate 的参数及返回类型声明并开始函数体
    agent_id = str(selected.get("agent_id", ""))  # 计算 str(selected.get("agent_id", "")) 并保存到变量 agent_id
    available = {  # 计算 { 并保存到变量 available
        item.agent_id  # 在函数 route_confirmation_gate 中执行表达式 item.agent_id，推进当前业务流程
        for item in context["registry"].list_for(context["identity"])  # 按迭代条件执行循环：for item in context["registry"].list_for(context["identity"])
    }  # 结束上一处多行结构，保持表达式边界清晰
    if agent_id not in available:  # 判断分支条件：if agent_id not in available:
        raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
            "AGENT_NOT_AVAILABLE", "selected agent is not available"  # 在函数 route_confirmation_gate 中执行表达式 "AGENT_NOT_AVAILABLE", "selected agent is not available"，推进当前业务流程
        )  # 结束函数 route_confirmation_gate 的参数及返回类型声明并开始函数体
    definition = context["registry"].get(agent_id)  # 计算 context["registry"].get(agent_id) 并保存到变量 definition
    context["llm"].agent_id = definition.agent_id  # 计算 definition.agent_id 并保存到变量 context["llm"].agent_id
    route_payload = {  # 计算 { 并保存到变量 route_payload
        "selected_agent_id": definition.agent_id,  # 为多行字典定义键 "selected_agent_id" 及其对应值
        "agent_version": definition.version,  # 为多行字典定义键 "agent_version" 及其对应值
        "state_schema_version": definition.state_schema_version,  # 为多行字典定义键 "state_schema_version" 及其对应值
        "prompt_versions": context["registry"].prompt_manifest(agent_id),  # 为多行字典定义键 "prompt_versions" 及其对应值
        "model_profile": definition.model_profile,  # 为多行字典定义键 "model_profile" 及其对应值
        "mode": RouteMode.USER.value,  # 为多行字典定义键 "mode" 及其对应值
        "reason_code": "user_selection",  # 为多行字典定义键 "reason_code" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰
    await context["store"].set_run_route(  # 等待异步操作完成并取得结果：context["store"].set_run_route(
        _run_uuid(state),  # 继续向上一处调用或声明传入 _run_uuid(state)
        selected_agent_id=definition.agent_id,  # 为 set_run_route 设置关键字参数 selected_agent_id，传入当前行给出的值
        agent_version=definition.version,  # 为 set_run_route 设置关键字参数 agent_version，传入当前行给出的值
        route_mode=RouteMode.USER,  # 为 set_run_route 设置关键字参数 route_mode，传入当前行给出的值
        confidence=1.0,  # 为 set_run_route 设置关键字参数 confidence，传入当前行给出的值
        route=route_payload,  # 为 set_run_route 设置关键字参数 route，传入当前行给出的值
    )  # 结束函数 route_confirmation_gate 的参数及返回类型声明并开始函数体
    await context["store"].add_audit(  # 等待异步操作完成并取得结果：context["store"].add_audit(
        AuditRecord(  # 调用 AuditRecord 执行当前步骤：AuditRecord(
            id=_run_uuid(state),  # 为 _run_uuid 设置关键字参数 id，传入当前行给出的值
            tenant_id=context["identity"].tenant_id,  # 为 AuditRecord 设置关键字参数 tenant_id，传入当前行给出的值
            actor_id=context["identity"].user_id,  # 为 AuditRecord 设置关键字参数 actor_id，传入当前行给出的值
            action="agent.route",  # 为 AuditRecord 设置关键字参数 action，传入当前行给出的值
            resource_type="run",  # 为 AuditRecord 设置关键字参数 resource_type，传入当前行给出的值
            resource_id=str(_run_uuid(state)),  # 为 str 设置关键字参数 resource_id，传入当前行给出的值
            outcome="selected",  # 为 AuditRecord 设置关键字参数 outcome，传入当前行给出的值
            trace_id=context.get("trace_id"),  # 为 context.get 设置关键字参数 trace_id，传入当前行给出的值
            metadata={  # 为 AuditRecord 设置关键字参数 metadata，传入当前行给出的值
                "agent_id": definition.agent_id,  # 为多行字典定义键 "agent_id" 及其对应值
                "agent_version": definition.version,  # 为多行字典定义键 "agent_version" 及其对应值
                "mode": RouteMode.USER.value,  # 为多行字典定义键 "mode" 及其对应值
                "reason_code": "user_selection",  # 为多行字典定义键 "reason_code" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束函数 route_confirmation_gate 的参数及返回类型声明并开始函数体
    )  # 结束函数 route_confirmation_gate 的参数及返回类型声明并开始函数体
    runtime.stream_writer(  # 调用 stream_writer 执行当前步骤：runtime.stream_writer(
        {  # 在函数 route_confirmation_gate 中执行表达式 {，推进当前业务流程
            "type": "agent.selected",  # 为多行字典定义键 "type" 及其对应值
            "data": {  # 为多行字典定义键 "data" 及其对应值
                "selected_agent_id": definition.agent_id,  # 为多行字典定义键 "selected_agent_id" 及其对应值
                "agent_version": definition.version,  # 为多行字典定义键 "agent_version" 及其对应值
                "mode": RouteMode.USER.value,  # 为多行字典定义键 "mode" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        }  # 结束上一处多行结构，保持表达式边界清晰
    )  # 结束函数 route_confirmation_gate 的参数及返回类型声明并开始函数体
    context["telemetry"].metrics.route_selections.add(  # 调用 目标函数 执行当前步骤：context["telemetry"].metrics.route_selections.add(
        1,  # 继续向上一处调用或声明传入 1
        {  # 在函数 route_confirmation_gate 中执行表达式 {，推进当前业务流程
            "agent_id": definition.agent_id,  # 为多行字典定义键 "agent_id" 及其对应值
            "mode": RouteMode.USER.value,  # 为多行字典定义键 "mode" 及其对应值
            "result": "selected",  # 为多行字典定义键 "result" 及其对应值
        },  # 结束上一处多行结构，保持表达式边界清晰
    )  # 结束函数 route_confirmation_gate 的参数及返回类型声明并开始函数体
    return {  # 返回 { 给调用方
        "selected_agent_id": definition.agent_id,  # 为多行字典定义键 "selected_agent_id" 及其对应值
        "agent_version": definition.version,  # 为多行字典定义键 "agent_version" 及其对应值
        "route_mode": RouteMode.USER.value,  # 为多行字典定义键 "route_mode" 及其对应值
        "route_confidence": 1.0,  # 为多行字典定义键 "route_confidence" 及其对应值
        "route_reason_code": "user_selection",  # 为多行字典定义键 "route_reason_code" 及其对应值
        "run_outcome_status": "running",  # 为多行字典定义键 "run_outcome_status" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰


def _agent_route(state: HarnessState) -> str:  # 定义函数 _agent_route，封装该模块的一项明确职责
    selected = state.get("selected_agent_id")  # 计算 state.get("selected_agent_id") 并保存到变量 selected
    if selected:  # 判断分支条件：if selected:
        return selected  # 返回 selected 给调用方
    raise ConflictError("AGENT_NOT_SELECTED", "no agent was selected")  # 抛出明确异常，阻止错误状态被静默接受：ConflictError("AGENT_NOT_SELECTED", "no agent was selected")


async def finalize(state: HarnessState, runtime: Runtime[HarnessContext]) -> dict:  # 定义异步函数 finalize，封装可被事件循环调度的协程逻辑
    del runtime  # 删除或显式忽略名称 runtime，避免未使用变量干扰
    if state.get("approval_action") == "reject":  # 判断分支条件：if state.get("approval_action") == "reject":
        return {"run_outcome_status": "rejected"}  # 返回 {"run_outcome_status": "rejected"} 给调用方
    output = state.get("agent_output") or {}  # 计算 state.get("agent_output") or {} 并保存到变量 output
    if output.get("status") == "failed" or output.get("error_code"):  # 判断分支条件：if output.get("status") == "failed" or output.get("error_code"):
        return {"run_outcome_status": "failed"}  # 返回 {"run_outcome_status": "failed"} 给调用方
    return {  # 返回 { 给调用方
        "run_outcome_status": "completed",  # 为多行字典定义键 "run_outcome_status" 及其对应值
        "agent_output": {  # 为多行字典定义键 "agent_output" 及其对应值
            **output,  # 向多行字典加入配置项 **output
            "agent_id": state.get("selected_agent_id"),  # 为多行字典定义键 "agent_id" 及其对应值
            "agent_version": state.get("agent_version"),  # 为多行字典定义键 "agent_version" 及其对应值
        },  # 结束上一处多行结构，保持表达式边界清晰
    }  # 结束上一处多行结构，保持表达式边界清晰


def _run_uuid(state: HarnessState):  # 定义函数 _run_uuid，封装该模块的一项明确职责
    from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

    return UUID(str(state["run_id"]))  # 返回 UUID(str(state["run_id"])) 给调用方


def build_harness_graph(  # 定义函数 build_harness_graph，封装该模块的一项明确职责
    registry: AgentRegistry,  # 为函数 build_harness_graph 声明参数 registry 及其类型或默认值
    checkpointer: BaseCheckpointSaver | None = None,  # 为函数 build_harness_graph 声明参数 checkpointer 及其类型或默认值
):  # 结束 build_harness_graph 的参数列表并声明返回类型
    builder = StateGraph(state_schema=HarnessState, context_schema=HarnessContext)  # 计算 StateGraph(state_schema=HarnessState, context_schema=HarnessContext) 并保存到变量 builder
    builder.add_node(  # 调用 add_node 执行当前步骤：builder.add_node(
        "load_session_context",  # 继续向上一处调用或声明传入 "load_session_context"
        traced_node("load_session_context", load_session_context),  # 继续向上一处调用或声明传入 traced_node("load_session_context", load_session_context)
    )  # 结束函数 build_harness_graph 的参数及返回类型声明并开始函数体
    builder.add_node("route_agent", traced_node("route_agent", route_agent))  # 调用 add_node 执行当前步骤：builder.add_node("route_agent", traced_node("route_agent", route_agent))
    builder.add_node(  # 调用 add_node 执行当前步骤：builder.add_node(
        "route_confirmation_gate",  # 继续向上一处调用或声明传入 "route_confirmation_gate"
        traced_node("route_confirmation_gate", route_confirmation_gate),  # 继续向上一处调用或声明传入 traced_node("route_confirmation_gate", route_confirmation_gate)
    )  # 结束函数 build_harness_graph 的参数及返回类型声明并开始函数体
    agent_ids = [definition.agent_id for definition in registry.definitions]  # 计算 [definition.agent_id for definition in registry.definitions] 并保存到变量 agent_ids
    for definition in registry.definitions:  # 按迭代条件执行循环：for definition in registry.definitions:
        builder.add_node(definition.agent_id, definition.graph_factory())  # 调用 add_node 执行当前步骤：builder.add_node(definition.agent_id, definition.graph_factory())
    builder.add_node("finalize", traced_node("finalize", finalize))  # 调用 add_node 执行当前步骤：builder.add_node("finalize", traced_node("finalize", finalize))
    builder.add_edge(START, "load_session_context")  # 调用 add_edge 执行当前步骤：builder.add_edge(START, "load_session_context")
    builder.add_edge("load_session_context", "route_agent")  # 调用 add_edge 执行当前步骤：builder.add_edge("load_session_context", "route_agent")
    builder.add_edge("route_agent", "route_confirmation_gate")  # 调用 add_edge 执行当前步骤：builder.add_edge("route_agent", "route_confirmation_gate")
    builder.add_conditional_edges(  # 调用 add_conditional_edges 执行当前步骤：builder.add_conditional_edges(
        "route_confirmation_gate",  # 继续向上一处调用或声明传入 "route_confirmation_gate"
        _agent_route,  # 继续向上一处调用或声明传入 _agent_route
        {agent_id: agent_id for agent_id in agent_ids},  # 继续向上一处调用或声明传入 {agent_id: agent_id for agent_id in agent_ids}
    )  # 结束函数 build_harness_graph 的参数及返回类型声明并开始函数体
    for agent_id in agent_ids:  # 按迭代条件执行循环：for agent_id in agent_ids:
        builder.add_edge(agent_id, "finalize")  # 调用 add_edge 执行当前步骤：builder.add_edge(agent_id, "finalize")
    builder.add_edge("finalize", END)  # 调用 add_edge 执行当前步骤：builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer, name="agent_harness")  # 返回 builder.compile(checkpointer=checkpointer, name="agent_harness") 给调用方
