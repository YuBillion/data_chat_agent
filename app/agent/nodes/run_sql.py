"""Execute a guarded and approved read-only query."""

from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.harness.records import AuditRecord  # 从 app.harness.records 导入 AuditRecord，供本模块后续代码使用
from app.harness.tool_access import require_tool_access  # 从 app.harness.tool_access 导入 require_tool_access，供本模块后续代码使用


async def run_sql(  # 定义异步函数 run_sql，封装可被事件循环调度的协程逻辑
    state: DataAgentState, runtime: Runtime[DataAgentContext]  # 为函数 run_sql 声明参数 state 及其类型或默认值
) -> dict:  # 结束 run_sql 的参数列表并声明返回类型
    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "执行SQL"  # 计算 "执行SQL" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})
    context = runtime.context  # 计算 runtime.context 并保存到变量 context
    require_tool_access(context, state, "sql_execute")  # 调用 require_tool_access 执行当前步骤：require_tool_access(context, state, "sql_execute")
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        result = await context["sql_read_tool"].execute(state["executed_sql"])  # 等待 目标函数 完成，并将其结果保存到 result
        output = {  # 计算 { 并保存到变量 output
            "agent_id": "analytics_sql",  # 为多行字典定义键 "agent_id" 及其对应值
            "text": f"查询完成，共返回 {result.row_count} 行。",  # 为多行字典定义键 "text" 及其对应值
            "columns": result.columns,  # 为多行字典定义键 "columns" 及其对应值
            "rows": result.rows,  # 为多行字典定义键 "rows" 及其对应值
            "row_count": result.row_count,  # 为多行字典定义键 "row_count" 及其对应值
            "truncated": result.truncated,  # 为多行字典定义键 "truncated" 及其对应值
            "duration_ms": result.duration_ms,  # 为多行字典定义键 "duration_ms" 及其对应值
            "sql": state.get("executed_sql"),  # 为多行字典定义键 "sql" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        writer({"type": "result", "data": output})  # 调用 writer 执行当前步骤：writer({"type": "result", "data": output})
        identity = context["identity"]  # 计算 context["identity"] 并保存到变量 identity
        await context["store"].add_audit(  # 等待异步操作完成并取得结果：context["store"].add_audit(
            AuditRecord(  # 调用 AuditRecord 执行当前步骤：AuditRecord(
                id=UUID(int=0),  # 为 UUID 设置关键字参数 id，传入当前行给出的值
                tenant_id=identity.tenant_id,  # 为 AuditRecord 设置关键字参数 tenant_id，传入当前行给出的值
                actor_id=identity.user_id,  # 为 AuditRecord 设置关键字参数 actor_id，传入当前行给出的值
                action="sql.execute",  # 为 AuditRecord 设置关键字参数 action，传入当前行给出的值
                resource_type="run",  # 为 AuditRecord 设置关键字参数 resource_type，传入当前行给出的值
                resource_id=str(context["run_id"]),  # 为 str 设置关键字参数 resource_id，传入当前行给出的值
                outcome="success",  # 为 AuditRecord 设置关键字参数 outcome，传入当前行给出的值
                trace_id=context.get("trace_id"),  # 为 context.get 设置关键字参数 trace_id，传入当前行给出的值
                metadata={  # 为 AuditRecord 设置关键字参数 metadata，传入当前行给出的值
                    "agent_id": "analytics_sql",  # 为多行字典定义键 "agent_id" 及其对应值
                    "sql_hash": state.get("sql_hash"),  # 为多行字典定义键 "sql_hash" 及其对应值
                    "row_count": result.row_count,  # 为多行字典定义键 "row_count" 及其对应值
                    "truncated": result.truncated,  # 为多行字典定义键 "truncated" 及其对应值
                    "duration_ms": result.duration_ms,  # 为多行字典定义键 "duration_ms" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束函数 run_sql 的参数及返回类型声明并开始函数体
        )  # 结束函数 run_sql 的参数及返回类型声明并开始函数体
        logger.info(  # 调用 info 执行当前步骤：logger.info(
            "SQL executed: rows={}, truncated={}, duration_ms={}",  # 继续向上一处调用或声明传入 "SQL executed: rows={}, truncated={}, duration_ms={}"
            result.row_count,  # 继续向上一处调用或声明传入 result.row_count
            result.truncated,  # 继续向上一处调用或声明传入 result.truncated
            result.duration_ms,  # 继续向上一处调用或声明传入 result.duration_ms
        )  # 结束函数 run_sql 的参数及返回类型声明并开始函数体
        return {"result": output, "agent_output": output}  # 返回 {"result": output, "agent_output": output} 给调用方
    except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
        logger.error("SQL execution failed: {}", type(exc).__name__)  # 调用 error 执行当前步骤：logger.error("SQL execution failed: {}", type(exc).__name__)
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
