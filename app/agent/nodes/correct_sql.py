"""
SQL 修正节点

负责在 SQL 校验失败后，结合原问题 原 SQL 数据库错误和完整上下文做最小必要修正
只有 validate_sql 写入错误信息时，LangGraph 才会进入这个分支
"""

import yaml  # 导入yaml，建立本模块需要的外部能力引用
from langchain_core.output_parsers import StrOutputParser  # 从 langchain_core.output_parsers 导入 StrOutputParser，供本模块后续代码使用
from langchain_core.prompts import PromptTemplate  # 从 langchain_core.prompts 导入 PromptTemplate，供本模块后续代码使用
from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.prompt.prompt_loader import load_prompt  # 从 app.prompt.prompt_loader 导入 load_prompt，供本模块后续代码使用


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):  # 定义异步函数 correct_sql，封装可被事件循环调度的协程逻辑
    """根据校验错误修正 SQL"""

    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "校正SQL"  # 计算 "校正SQL" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})

    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        # 校正 SQL 仍然需要完整上下文，避免模型只根据报错修语法却改丢业务语义
        table_infos = state["table_infos"]  # 计算 state["table_infos"] 并保存到变量 table_infos
        metric_infos = state["metric_infos"]  # 计算 state["metric_infos"] 并保存到变量 metric_infos
        date_info = state["date_info"]  # 计算 state["date_info"] 并保存到变量 date_info
        db_info = state["db_info"]  # 计算 state["db_info"] 并保存到变量 db_info
        query = state.get("resolved_query") or state["query"]  # 计算 state.get("resolved_query") or state["query"] 并保存到变量 query

        # sql 是待修正的候选 SQL，error 是数据库 explain 返回的具体错误信息
        sql = state["sql"]  # 计算 state["sql"] 并保存到变量 sql
        error = state["error"]  # 计算 state["error"] 并保存到变量 error

        prompt = PromptTemplate(  # 调用 PromptTemplate 构造结果并保存到 prompt
            template=load_prompt("correct_sql"),  # 为 load_prompt 设置关键字参数 template，传入当前行给出的值
            input_variables=[  # 为 PromptTemplate 设置关键字参数 input_variables，传入当前行给出的值
                "table_infos",  # 向多行序列加入元素 "table_infos"
                "metric_infos",  # 向多行序列加入元素 "metric_infos"
                "date_info",  # 向多行序列加入元素 "date_info"
                "db_info",  # 向多行序列加入元素 "db_info"
                "query",  # 向多行序列加入元素 "query"
                "sql",  # 向多行序列加入元素 "sql"
                "error",  # 向多行序列加入元素 "error"
            ],  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束函数 correct_sql 的参数及返回类型声明并开始函数体
        # 修正后的输出仍然是一条纯 SQL 文本，用来覆盖 state["sql"]
        output_parser = StrOutputParser()  # 计算 StrOutputParser() 并保存到变量 output_parser
        chain = prompt | runtime.context["llm"].model | output_parser  # 计算 prompt | runtime.context["llm"].model | output_parser 并保存到变量 chain

        result = await runtime.context["llm"].ainvoke(  # 等待 目标函数 完成，并将其结果保存到 result
            chain,  # 继续向上一处调用或声明传入 chain
            {  # 在函数 correct_sql 中执行表达式 {，推进当前业务流程
                # 与生成节点保持一致，用 YAML 向模型提供稳定 可读的结构化上下文
                "table_infos": yaml.dump(  # 为多行字典定义键 "table_infos" 及其对应值
                    table_infos, allow_unicode=True, sort_keys=False  # 在函数 correct_sql 中执行表达式 table_infos, allow_unicode=True, sort_keys=False，推进当前业务流程
                ),  # 结束函数 correct_sql 的参数及返回类型声明并开始函数体
                "metric_infos": yaml.dump(  # 为多行字典定义键 "metric_infos" 及其对应值
                    metric_infos, allow_unicode=True, sort_keys=False  # 在函数 correct_sql 中执行表达式 metric_infos, allow_unicode=True, sort_keys=False，推进当前业务流程
                ),  # 结束函数 correct_sql 的参数及返回类型声明并开始函数体
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),  # 为多行字典定义键 "date_info" 及其对应值
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),  # 为多行字典定义键 "db_info" 及其对应值
                "query": query,  # 为多行字典定义键 "query" 及其对应值
                "sql": sql,  # 为多行字典定义键 "sql" 及其对应值
                "error": error,  # 为多行字典定义键 "error" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
            name="correct_sql",  # 为 ainvoke 设置关键字参数 name，传入当前行给出的值
        )  # 结束函数 correct_sql 的参数及返回类型声明并开始函数体

        logger.info("SQL corrected: chars={}", len(str(result)))  # 调用 info 执行当前步骤：logger.info("SQL corrected: chars={}", len(str(result)))
        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        return {  # 返回 { 给调用方
            "sql": result,  # 为多行字典定义键 "sql" 及其对应值
            "correction_count": state.get("correction_count", 0) + 1,  # 为多行字典定义键 "correction_count" 及其对应值
            "error": None,  # 为多行字典定义键 "error" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    except Exception as e:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as e:
        logger.error(f"{step} failed: {e}")  # 调用 error 执行当前步骤：logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
