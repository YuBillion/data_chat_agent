"""
表信息过滤节点

负责在合并后的候选表结构中筛选出当前问题真正需要的表和字段
这里让大模型只返回“保留哪些表和字段”的选择结果，真正的结构裁剪仍由程序完成
"""

import copy  # 导入copy，建立本模块需要的外部能力引用

import yaml  # 导入yaml，建立本模块需要的外部能力引用
from langchain_core.output_parsers import JsonOutputParser  # 从 langchain_core.output_parsers 导入 JsonOutputParser，供本模块后续代码使用
from langchain_core.prompts import PromptTemplate  # 从 langchain_core.prompts 导入 PromptTemplate，供本模块后续代码使用
from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState, TableInfoState  # 从 app.agent.state 导入 DataAgentState, TableInfoState，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.prompt.prompt_loader import load_prompt  # 从 app.prompt.prompt_loader 导入 load_prompt，供本模块后续代码使用


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):  # 定义异步函数 filter_table，封装可被事件循环调度的协程逻辑
    """根据用户问题裁剪候选表结构上下文"""

    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "过滤表信息"  # 计算 "过滤表信息" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})

    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        query = state.get("resolved_query") or state["query"]  # 计算 state.get("resolved_query") or state["query"] 并保存到变量 query
        table_infos: list[TableInfoState] = copy.deepcopy(state["table_infos"])  # 计算 copy.deepcopy(state["table_infos"]) 并保存到变量 table_infos

        # table_infos 是嵌套结构，转成 YAML 后更适合放进提示词，也保留中文字段说明
        prompt = PromptTemplate(  # 调用 PromptTemplate 构造结果并保存到 prompt
            template=load_prompt("filter_table_info"),  # 为 load_prompt 设置关键字参数 template，传入当前行给出的值
            input_variables=["query", "table_infos"],  # 为 PromptTemplate 设置关键字参数 input_variables，传入当前行给出的值
        )  # 结束函数 filter_table 的参数及返回类型声明并开始函数体
        # filter_table_info prompt 要求模型只输出 JSON 对象：表名 -> 字段名列表
        output_parser = JsonOutputParser()  # 计算 JsonOutputParser() 并保存到变量 output_parser
        # LCEL 管道：填充提示词 -> 调用模型 -> 解析 JSON
        chain = prompt | runtime.context["llm"].model | output_parser  # 计算 prompt | runtime.context["llm"].model | output_parser 并保存到变量 chain

        result = await runtime.context["llm"].ainvoke(  # 等待 目标函数 完成，并将其结果保存到 result
            chain,  # 继续向上一处调用或声明传入 chain
            {  # 在函数 filter_table 中执行表达式 {，推进当前业务流程
                "query": query,  # 为多行字典定义键 "query" 及其对应值
                "table_infos": yaml.dump(  # 为多行字典定义键 "table_infos" 及其对应值
                    table_infos, allow_unicode=True, sort_keys=False  # 在函数 filter_table 中执行表达式 table_infos, allow_unicode=True, sort_keys=False，推进当前业务流程
                ),  # 结束函数 filter_table 的参数及返回类型声明并开始函数体
            },  # 结束上一处多行结构，保持表达式边界清晰
            name="filter_tables",  # 为 ainvoke 设置关键字参数 name，传入当前行给出的值
        )  # 结束函数 filter_table 的参数及返回类型声明并开始函数体
        # 模型只负责选择，程序根据选择结果从原始 TableInfoState 中裁剪，避免模型重写复杂结构出错
        filtered_table_infos: list[TableInfoState] = []  # 计算 [] 并保存到变量 filtered_table_infos
        for table_info in table_infos:  # 按迭代条件执行循环：for table_info in table_infos:
            if table_info["name"] in result:  # 判断分支条件：if table_info["name"] in result:
                selected_columns = [  # 计算 [ 并保存到变量 selected_columns
                    column_info  # 在函数 filter_table 中执行表达式 column_info，推进当前业务流程
                    for column_info in table_info["columns"]  # 按迭代条件执行循环：for column_info in table_info["columns"]
                    if column_info["name"] in result[table_info["name"]]  # 判断分支条件：if column_info["name"] in result[table_info["name"]]
                ]  # 结束上一处多行结构，保持表达式边界清晰
                selected_names = {  # 计算 { 并保存到变量 selected_names
                    column_info["name"] for column_info in selected_columns  # 在函数 filter_table 中执行表达式 column_info["name"] for column_info in selected_columns，推进当前业务流程
                }  # 结束上一处多行结构，保持表达式边界清晰
                for column_info in table_info["columns"]:  # 按迭代条件执行循环：for column_info in table_info["columns"]:
                    if (  # 判断分支条件：if (
                        column_info.get("role")  # 调用 get 执行当前步骤：column_info.get("role")
                        in {"primary_key", "foreign_key"}  # 在函数 filter_table 中执行表达式 in {"primary_key", "foreign_key"}，推进当前业务流程
                        and column_info["name"] not in selected_names  # 在函数 filter_table 中执行表达式 and column_info["name"] not in selected_names，推进当前业务流程
                    ):  # 结束 filter_table 的参数列表并声明返回类型
                        selected_columns.append(column_info)  # 调用 append 执行当前步骤：selected_columns.append(column_info)
                table_info["columns"] = selected_columns  # 计算 selected_columns 并保存到变量 table_info["columns"]
                filtered_table_infos.append(table_info)  # 调用 append 执行当前步骤：filtered_table_infos.append(table_info)

        logger.info(  # 调用 info 执行当前步骤：logger.info(
            f"过滤后的表信息：{[filtered_table_info['name'] for filtered_table_info in filtered_table_infos]}"  # 在函数 filter_table 中执行表达式 f"过滤后的表信息：{[filtered_table_info['name'] for filtered_table_info in filt…，推进当前业务流程
        )  # 结束函数 filter_table 的参数及返回类型声明并开始函数体
        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": filtered_table_infos}  # 返回 {"table_infos": filtered_table_infos} 给调用方

    except Exception as e:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as e:
        logger.error(f"{step} failed: {e}")  # 调用 error 执行当前步骤：logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
