"""
指标信息过滤节点

负责从合并后的候选指标中筛选出当前问题真正需要的指标
过滤后的指标会进入 SQL 生成上下文，帮助模型遵循正确的业务口径
"""

import yaml  # 导入yaml，建立本模块需要的外部能力引用
from langchain_core.output_parsers import JsonOutputParser  # 从 langchain_core.output_parsers 导入 JsonOutputParser，供本模块后续代码使用
from langchain_core.prompts import PromptTemplate  # 从 langchain_core.prompts 导入 PromptTemplate，供本模块后续代码使用
from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState, MetricInfoState  # 从 app.agent.state 导入 DataAgentState, MetricInfoState，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.prompt.prompt_loader import load_prompt  # 从 app.prompt.prompt_loader 导入 load_prompt，供本模块后续代码使用


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):  # 定义异步函数 filter_metric，封装可被事件循环调度的协程逻辑
    """根据用户问题裁剪候选指标上下文"""

    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "过滤指标信息"  # 计算 "过滤指标信息" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})

    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        query = state.get("resolved_query") or state["query"]  # 计算 state.get("resolved_query") or state["query"] 并保存到变量 query
        metric_infos: list[MetricInfoState] = state["metric_infos"]  # 计算 state["metric_infos"] 并保存到变量 metric_infos

        # metric_infos 转成 YAML 后作为候选项交给模型，模型只需要返回被选中的指标名称
        prompt = PromptTemplate(  # 调用 PromptTemplate 构造结果并保存到 prompt
            template=load_prompt("filter_metric_info"),  # 为 load_prompt 设置关键字参数 template，传入当前行给出的值
            input_variables=["query", "metric_infos"],  # 为 PromptTemplate 设置关键字参数 input_variables，传入当前行给出的值
        )  # 结束函数 filter_metric 的参数及返回类型声明并开始函数体
        # filter_metric_info prompt 要求模型只输出 JSON 数组
        output_parser = JsonOutputParser()  # 计算 JsonOutputParser() 并保存到变量 output_parser
        # LCEL 管道：填充提示词 -> 调用模型 -> 解析 JSON
        chain = prompt | runtime.context["llm"].model | output_parser  # 计算 prompt | runtime.context["llm"].model | output_parser 并保存到变量 chain

        result = await runtime.context["llm"].ainvoke(  # 等待 目标函数 完成，并将其结果保存到 result
            chain,  # 继续向上一处调用或声明传入 chain
            {  # 在函数 filter_metric 中执行表达式 {，推进当前业务流程
                "query": query,  # 为多行字典定义键 "query" 及其对应值
                "metric_infos": yaml.dump(  # 为多行字典定义键 "metric_infos" 及其对应值
                    metric_infos, allow_unicode=True, sort_keys=False  # 在函数 filter_metric 中执行表达式 metric_infos, allow_unicode=True, sort_keys=False，推进当前业务流程
                ),  # 结束函数 filter_metric 的参数及返回类型声明并开始函数体
            },  # 结束上一处多行结构，保持表达式边界清晰
            name="filter_metrics",  # 为 ainvoke 设置关键字参数 name，传入当前行给出的值
        )  # 结束函数 filter_metric 的参数及返回类型声明并开始函数体
        # 用模型返回的指标名称过滤原始结构，保留描述 依赖字段 别名等完整上下文
        filtered_metric_infos = [  # 计算 [ 并保存到变量 filtered_metric_infos
            metric_info for metric_info in metric_infos if metric_info["name"] in result  # 在函数 filter_metric 中执行表达式 metric_info for metric_info in metric_infos if metric_info["name"] in r…，推进当前业务流程
        ]  # 结束上一处多行结构，保持表达式边界清晰

        logger.info(  # 调用 info 执行当前步骤：logger.info(
            f"过滤后的指标信息：{[filtered_metric_info['name'] for filtered_metric_info in filtered_metric_infos]}"  # 在函数 filter_metric 中执行表达式 f"过滤后的指标信息：{[filtered_metric_info['name'] for filtered_metric_info in f…，推进当前业务流程
        )  # 结束函数 filter_metric 的参数及返回类型声明并开始函数体

        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        return {"metric_infos": filtered_metric_infos}  # 返回 {"metric_infos": filtered_metric_infos} 给调用方

    except Exception as e:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as e:
        logger.error(f"{step} failed: {e}")  # 调用 error 执行当前步骤：logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
