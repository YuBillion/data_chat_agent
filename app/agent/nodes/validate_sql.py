"""Guard and validate model-generated SQL before any execution decision."""

from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.core.errors import AppError  # 从 app.core.errors 导入 AppError，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.harness.tool_access import require_tool_access  # 从 app.harness.tool_access 导入 require_tool_access，供本模块后续代码使用
from app.tools.sql_guard import catalog_allowlist  # 从 app.tools.sql_guard 导入 catalog_allowlist，供本模块后续代码使用


async def validate_sql(  # 定义异步函数 validate_sql，封装可被事件循环调度的协程逻辑
    state: DataAgentState, runtime: Runtime[DataAgentContext]  # 为函数 validate_sql 声明参数 state 及其类型或默认值
) -> dict:  # 结束 validate_sql 的参数列表并声明返回类型
    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "校验SQL"  # 计算 "校验SQL" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})
    context = runtime.context  # 计算 runtime.context 并保存到变量 context
    require_tool_access(context, state, "sql_guard")  # 调用 require_tool_access 执行当前步骤：require_tool_access(context, state, "sql_guard")
    require_tool_access(context, state, "sql_explain")  # 调用 require_tool_access 执行当前步骤：require_tool_access(context, state, "sql_explain")
    sql = state["sql"]  # 计算 state["sql"] 并保存到变量 sql
    tables, columns = catalog_allowlist(  # 调用 catalog_allowlist 构造结果并保存到 tables, columns
        state.get("table_infos", []),  # 向多行序列加入元素 state.get("table_infos", [])
        context.get("extra", {}).get("extra_columns", []),  # 向多行字典加入配置项 context.get("extra", {}).get("extra_columns", [])
    )  # 结束函数 validate_sql 的参数及返回类型声明并开始函数体
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        assessment = context["sql_guard"].inspect(  # 调用 目标函数 构造结果并保存到 assessment
            sql,  # 继续向上一处调用或声明传入 sql
            allowed_tables=tables,  # 为 inspect 设置关键字参数 allowed_tables，传入当前行给出的值
            allowed_columns=columns,  # 为 inspect 设置关键字参数 allowed_columns，传入当前行给出的值
            corrected=state.get("correction_count", 0) > 0  # 为 state.get 设置关键字参数 corrected，传入当前行给出的值
            or state.get("human_edited_sql", False),  # 继续向上一处调用或声明传入 or state.get("human_edited_sql", False)
        )  # 结束函数 validate_sql 的参数及返回类型声明并开始函数体
        plan, estimated_rows = await context["sql_read_tool"].explain(  # 等待 目标函数 完成，并将其结果保存到 plan, estimated_rows
            assessment.normalized_sql  # 在函数 validate_sql 中执行表达式 assessment.normalized_sql，推进当前业务流程
        )  # 结束函数 validate_sql 的参数及返回类型声明并开始函数体
        assessment = context["sql_guard"].inspect(  # 调用 目标函数 构造结果并保存到 assessment
            sql,  # 继续向上一处调用或声明传入 sql
            allowed_tables=tables,  # 为 inspect 设置关键字参数 allowed_tables，传入当前行给出的值
            allowed_columns=columns,  # 为 inspect 设置关键字参数 allowed_columns，传入当前行给出的值
            corrected=state.get("correction_count", 0) > 0  # 为 state.get 设置关键字参数 corrected，传入当前行给出的值
            or state.get("human_edited_sql", False),  # 继续向上一处调用或声明传入 or state.get("human_edited_sql", False)
            estimated_rows=estimated_rows,  # 为 inspect 设置关键字参数 estimated_rows，传入当前行给出的值
        )  # 结束函数 validate_sql 的参数及返回类型声明并开始函数体
        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        logger.info(  # 调用 info 执行当前步骤：logger.info(
            "SQL validated: tables={}, estimated_rows={}",  # 继续向上一处调用或声明传入 "SQL validated: tables={}, estimated_rows={}"
            assessment.tables,  # 继续向上一处调用或声明传入 assessment.tables
            estimated_rows,  # 继续向上一处调用或声明传入 estimated_rows
        )  # 结束函数 validate_sql 的参数及返回类型声明并开始函数体
        return {  # 返回 { 给调用方
            "error": None,  # 为多行字典定义键 "error" 及其对应值
            "executed_sql": assessment.normalized_sql,  # 为多行字典定义键 "executed_sql" 及其对应值
            "estimated_rows": estimated_rows,  # 为多行字典定义键 "estimated_rows" 及其对应值
            "sql_hash": assessment.sql_hash,  # 为多行字典定义键 "sql_hash" 及其对应值
            "risk_reasons": assessment.reasons,  # 为多行字典定义键 "risk_reasons" 及其对应值
            "high_risk": assessment.high_risk,  # 为多行字典定义键 "high_risk" 及其对应值
            "approval_required": assessment.approval_required,  # 为多行字典定义键 "approval_required" 及其对应值
            "risk_tables": assessment.tables,  # 为多行字典定义键 "risk_tables" 及其对应值
            "risk_columns": assessment.columns,  # 为多行字典定义键 "risk_columns" 及其对应值
            "explain_plan": plan,  # 为多行字典定义键 "explain_plan" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    except AppError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except AppError as exc:
        logger.info("SQL validation failed: code={}", exc.code)  # 调用 info 执行当前步骤：logger.info("SQL validation failed: code={}", exc.code)
        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        return {  # 返回 { 给调用方
            "error": exc.message,  # 为多行字典定义键 "error" 及其对应值
            "executed_sql": None,  # 为多行字典定义键 "executed_sql" 及其对应值
            "estimated_rows": None,  # 为多行字典定义键 "estimated_rows" 及其对应值
            "sql_hash": None,  # 为多行字典定义键 "sql_hash" 及其对应值
            "risk_reasons": [exc.code],  # 为多行字典定义键 "risk_reasons" 及其对应值
            "high_risk": False,  # 为多行字典定义键 "high_risk" 及其对应值
            "approval_required": False,  # 为多行字典定义键 "approval_required" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    except Exception:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception:
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
