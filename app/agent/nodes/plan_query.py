"""Context-aware query rewriting and one-call retrieval planning."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import json  # 导入json，建立本模块需要的外部能力引用
from typing import TypedDict  # 从 typing 导入 TypedDict，供本模块后续代码使用

import jieba.analyse  # 导入jieba.analyse，建立本模块需要的外部能力引用
from langchain_core.output_parsers import JsonOutputParser  # 从 langchain_core.output_parsers 导入 JsonOutputParser，供本模块后续代码使用
from langchain_core.prompts import PromptTemplate  # 从 langchain_core.prompts 导入 PromptTemplate，供本模块后续代码使用
from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用
from pydantic import BaseModel, Field  # 从 pydantic 导入 BaseModel, Field，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState  # 从 app.agent.state 导入 DataAgentState，供本模块后续代码使用
from app.core.errors import AppError  # 从 app.core.errors 导入 AppError，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.prompt.prompt_loader import load_prompt  # 从 app.prompt.prompt_loader 导入 load_prompt，供本模块后续代码使用


class QueryPlan(TypedDict):  # 定义类 QueryPlan，组织相关状态与行为
    resolved_query: str  # 声明或继续传入参数 resolved_query: str
    column_terms: list[str]  # 声明或继续传入参数 column_terms: list[str]
    metric_terms: list[str]  # 声明或继续传入参数 metric_terms: list[str]
    value_terms: list[str]  # 声明或继续传入参数 value_terms: list[str]


class QueryPlanModel(BaseModel):  # 定义类 QueryPlanModel，组织相关状态与行为
    resolved_query: str = Field(min_length=1, max_length=4000)  # 计算 Field(min_length=1, max_length=4000) 并保存到变量 resolved_query
    column_terms: list[str] = Field(default_factory=list)  # 计算 Field(default_factory=list) 并保存到变量 column_terms
    metric_terms: list[str] = Field(default_factory=list)  # 计算 Field(default_factory=list) 并保存到变量 metric_terms
    value_terms: list[str] = Field(default_factory=list)  # 计算 Field(default_factory=list) 并保存到变量 value_terms


async def plan_query(  # 定义异步函数 plan_query，封装可被事件循环调度的协程逻辑
    state: DataAgentState, runtime: Runtime[DataAgentContext]  # 为函数 plan_query 声明参数 state 及其类型或默认值
) -> dict:  # 结束 plan_query 的参数列表并声明返回类型
    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "规划检索"  # 计算 "规划检索" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})
    context = runtime.context  # 计算 runtime.context 并保存到变量 context
    query = state.get("resolved_query") or state["query"]  # 计算 state.get("resolved_query") or state["query"] 并保存到变量 query
    history = state.get("conversation", [])  # 计算 state.get("conversation", []) 并保存到变量 history
    settings = context["settings"]  # 计算 context["settings"] 并保存到变量 settings
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        async with asyncio.timeout(5):  # 进入受管理的上下文 async with asyncio.timeout(5):，确保资源正确获取与释放
            keywords = await asyncio.to_thread(_extract_keywords, query)  # 等待 to_thread 完成，并将其结果保存到 keywords
    except TimeoutError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except TimeoutError:
        keywords = [query]  # 计算 [query] 并保存到变量 keywords

    prompt = PromptTemplate(  # 调用 PromptTemplate 构造结果并保存到 prompt
        template=load_prompt("plan_query"),  # 为 load_prompt 设置关键字参数 template，传入当前行给出的值
        input_variables=["keywords", "history", "query"],  # 为 PromptTemplate 设置关键字参数 input_variables，传入当前行给出的值
    )  # 结束函数 plan_query 的参数及返回类型声明并开始函数体
    chain = prompt | context["llm"].model | JsonOutputParser(  # 调用 目标函数 构造结果并保存到 chain
        pydantic_object=QueryPlanModel  # 为 JsonOutputParser 设置关键字参数 pydantic_object，传入当前行给出的值
    )  # 结束函数 plan_query 的参数及返回类型声明并开始函数体
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        raw = await context["llm"].ainvoke(  # 等待 目标函数 完成，并将其结果保存到 raw
            chain,  # 继续向上一处调用或声明传入 chain
            {  # 在函数 plan_query 中执行表达式 {，推进当前业务流程
                "keywords": json.dumps(keywords, ensure_ascii=False),  # 为多行字典定义键 "keywords" 及其对应值
                "history": json.dumps(history[-12:], ensure_ascii=False),  # 为多行字典定义键 "history" 及其对应值
                "query": query,  # 为多行字典定义键 "query" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
            name="query_planner",  # 为 ainvoke 设置关键字参数 name，传入当前行给出的值
        )  # 结束函数 plan_query 的参数及返回类型声明并开始函数体
        plan = QueryPlanModel.model_validate(raw)  # 计算 QueryPlanModel.model_validate(raw) 并保存到变量 plan
        plan_fallback = None  # 计算 None 并保存到变量 plan_fallback
    except AppError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except AppError:
        raise  # 重新抛出当前异常，保留原始失败上下文
    except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
        logger.warning("query planning fell back to lexical terms: {}", type(exc).__name__)  # 调用 warning 执行当前步骤：logger.warning("query planning fell back to lexical terms: {}", type(ex…
        plan = QueryPlanModel(  # 调用 QueryPlanModel 构造结果并保存到 plan
            resolved_query=query,  # 为 QueryPlanModel 设置关键字参数 resolved_query，传入当前行给出的值
            column_terms=keywords,  # 为 QueryPlanModel 设置关键字参数 column_terms，传入当前行给出的值
            metric_terms=keywords,  # 为 QueryPlanModel 设置关键字参数 metric_terms，传入当前行给出的值
            value_terms=keywords,  # 为 QueryPlanModel 设置关键字参数 value_terms，传入当前行给出的值
        )  # 结束函数 plan_query 的参数及返回类型声明并开始函数体
        plan_fallback = type(exc).__name__  # 计算 type(exc).__name__ 并保存到变量 plan_fallback

    max_terms = settings.retrieval_max_terms  # 计算 settings.retrieval_max_terms 并保存到变量 max_terms
    result: QueryPlan = {  # 计算 { 并保存到变量 result
        "resolved_query": plan.resolved_query.strip() or query,  # 为多行字典定义键 "resolved_query" 及其对应值
        "column_terms": _terms(plan.column_terms, keywords, max_terms),  # 为多行字典定义键 "column_terms" 及其对应值
        "metric_terms": _terms(plan.metric_terms, keywords, max_terms),  # 为多行字典定义键 "metric_terms" 及其对应值
        "value_terms": _terms(plan.value_terms, keywords, max_terms),  # 为多行字典定义键 "value_terms" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰
    writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
    return {  # 返回 { 给调用方
        **result,  # 向多行字典加入配置项 **result
        "keywords": keywords[:max_terms],  # 为多行字典定义键 "keywords" 及其对应值
        "plan_fallback_reason": plan_fallback,  # 为多行字典定义键 "plan_fallback_reason" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰


def _extract_keywords(query: str) -> list[str]:  # 定义函数 _extract_keywords，封装该模块的一项明确职责
    allow_pos = (  # 调用 目标函数 构造结果并保存到 allow_pos
        "n",  # 向多行序列加入元素 "n"
        "nr",  # 向多行序列加入元素 "nr"
        "ns",  # 向多行序列加入元素 "ns"
        "nt",  # 向多行序列加入元素 "nt"
        "nz",  # 向多行序列加入元素 "nz"
        "v",  # 向多行序列加入元素 "v"
        "vn",  # 向多行序列加入元素 "vn"
        "a",  # 向多行序列加入元素 "a"
        "an",  # 向多行序列加入元素 "an"
        "eng",  # 向多行序列加入元素 "eng"
        "i",  # 向多行序列加入元素 "i"
        "l",  # 向多行序列加入元素 "l"
    )  # 结束函数 _extract_keywords 的参数及返回类型声明并开始函数体
    extracted = jieba.analyse.extract_tags(query, allowPOS=allow_pos)  # 计算 jieba.analyse.extract_tags(query, allowPOS=allow_pos) 并保存到变量 extracted
    return list(dict.fromkeys([*extracted, query]))  # 返回 list(dict.fromkeys([*extracted, query])) 给调用方


def _terms(  # 定义函数 _terms，封装该模块的一项明确职责
    model_terms: list[str], fallback: list[str], limit: int  # 为函数 _terms 声明参数 model_terms 及其类型或默认值
) -> list[str]:  # 结束 _terms 的参数列表并声明返回类型
    result: list[str] = []  # 计算 [] 并保存到变量 result
    for value in [*model_terms, *fallback]:  # 按迭代条件执行循环：for value in [*model_terms, *fallback]:
        normalized = str(value).strip()[:200]  # 计算 str(value).strip()[:200] 并保存到变量 normalized
        if normalized and normalized not in result:  # 判断分支条件：if normalized and normalized not in result:
            result.append(normalized)  # 调用 append 执行当前步骤：result.append(normalized)
        if len(result) >= limit:  # 判断分支条件：if len(result) >= limit:
            break  # 提前结束当前循环并继续后续控制流
    return result  # 返回 result 给调用方
