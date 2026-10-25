"""
SQL 生成节点

负责根据用户问题和前面整理出的表结构 指标 日期 数据库环境生成候选 SQL。
本节点只生成 SQL，不做校验和执行，后续会交给 validate_sql 和 run_sql 继续处理。
"""

import yaml  # 导入yaml，建立本模块需要的外部能力引用
from langchain_core.output_parsers import StrOutputParser  # 从 langchain_core.output_parsers 导入 StrOutputParser，供本模块后续代码使用
from langchain_core.prompts import PromptTemplate  # 从 langchain_core.prompts 导入 PromptTemplate，供本模块后续代码使用
from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.prompt.prompt_loader import load_prompt  # 从 app.prompt.prompt_loader 导入 load_prompt，供本模块后续代码使用


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):  # 定义异步函数 generate_sql，封装可被事件循环调度的协程逻辑
    """基于已检索和过滤的上下文生成 SQL"""

    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "生成SQL"  # 计算 "生成SQL" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})

    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        # 这些上下文都由前置节点准备完成，模型只在给定表 字段 指标口径范围内生成 SQL
        table_infos = state["table_infos"]  # 计算 state["table_infos"] 并保存到变量 table_infos
        metric_infos = state["metric_infos"]  # 计算 state["metric_infos"] 并保存到变量 metric_infos
        date_info = state["date_info"]  # 计算 state["date_info"] 并保存到变量 date_info
        db_info = state["db_info"]  # 计算 state["db_info"] 并保存到变量 db_info
        query = state.get("resolved_query") or state["query"]  # 计算 state.get("resolved_query") or state["query"] 并保存到变量 query

        prompt = PromptTemplate(  # 调用 PromptTemplate 构造结果并保存到 prompt
            template=load_prompt("generate_sql"),  # 为 load_prompt 设置关键字参数 template，传入当前行给出的值
            input_variables=[  # 为 PromptTemplate 设置关键字参数 input_variables，传入当前行给出的值
                "table_infos",  # 向多行序列加入元素 "table_infos"
                "metric_infos",  # 向多行序列加入元素 "metric_infos"
                "date_info",  # 向多行序列加入元素 "date_info"
                "db_info",  # 向多行序列加入元素 "db_info"
                "query",  # 向多行序列加入元素 "query"
            ],  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束函数 generate_sql 的参数及返回类型声明并开始函数体
        # SQL 生成节点只需要纯文本 SQL，不能要求模型输出 JSON 或 Markdown 代码块
        output_parser = StrOutputParser()  # 计算 StrOutputParser() 并保存到变量 output_parser
        chain = prompt | runtime.context["llm"].model | output_parser  # 计算 prompt | runtime.context["llm"].model | output_parser 并保存到变量 chain

        result = await runtime.context["llm"].ainvoke(  # 等待 目标函数 完成，并将其结果保存到 result
            chain,  # 继续向上一处调用或声明传入 chain
            {  # 在函数 generate_sql 中执行表达式 {，推进当前业务流程
                # YAML 更适合放进提示词：保留嵌套结构 顺序和中文说明，方便模型理解表字段关系
                "table_infos": yaml.dump(  # 为多行字典定义键 "table_infos" 及其对应值
                    table_infos, allow_unicode=True, sort_keys=False  # 在函数 generate_sql 中执行表达式 table_infos, allow_unicode=True, sort_keys=False，推进当前业务流程
                ),  # 结束函数 generate_sql 的参数及返回类型声明并开始函数体
                "metric_infos": yaml.dump(  # 为多行字典定义键 "metric_infos" 及其对应值
                    metric_infos, allow_unicode=True, sort_keys=False  # 在函数 generate_sql 中执行表达式 metric_infos, allow_unicode=True, sort_keys=False，推进当前业务流程
                ),  # 结束函数 generate_sql 的参数及返回类型声明并开始函数体
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),  # 为多行字典定义键 "date_info" 及其对应值
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),  # 为多行字典定义键 "db_info" 及其对应值
                "query": query,  # 为多行字典定义键 "query" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
            name="generate_sql",  # 为 ainvoke 设置关键字参数 name，传入当前行给出的值
        )  # 结束函数 generate_sql 的参数及返回类型声明并开始函数体
        logger.info("SQL generated: chars={}", len(str(result)))  # 调用 info 执行当前步骤：logger.info("SQL generated: chars={}", len(str(result)))
        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": result}  # 返回 {"sql": result} 给调用方

    except Exception as e:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as e:
        logger.error(f"{step} failed: {e}")  # 调用 error 执行当前步骤：logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
