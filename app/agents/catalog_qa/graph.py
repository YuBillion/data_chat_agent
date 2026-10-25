"""LangGraph subgraph for metadata-only catalog questions."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import json  # 导入json，建立本模块需要的外部能力引用
from typing import Any, Literal, TypedDict  # 从 typing 导入 Any, Literal, TypedDict，供本模块后续代码使用

from langchain_core.output_parsers import JsonOutputParser  # 从 langchain_core.output_parsers 导入 JsonOutputParser，供本模块后续代码使用
from langchain_core.prompts import PromptTemplate  # 从 langchain_core.prompts 导入 PromptTemplate，供本模块后续代码使用
from langgraph.constants import END, START  # 从 langgraph.constants 导入 END, START，供本模块后续代码使用
from langgraph.graph import StateGraph  # 从 langgraph.graph 导入 StateGraph，供本模块后续代码使用
from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用
from pydantic import BaseModel, Field  # 从 pydantic 导入 BaseModel, Field，供本模块后续代码使用

from app.harness.context import HarnessContext  # 从 app.harness.context 导入 HarnessContext，供本模块后续代码使用
from app.observability.nodes import traced_node  # 从 app.observability.nodes 导入 traced_node，供本模块后续代码使用
from app.prompt.prompt_loader import load_prompt  # 从 app.prompt.prompt_loader 导入 load_prompt，供本模块后续代码使用


class CatalogAnswerReference(BaseModel):  # 定义类 CatalogAnswerReference，组织相关状态与行为
    type: Literal["table", "column", "metric"]  # 声明或继续传入参数 type: Literal["table", "column", "metric"]
    id: str  # 声明或继续传入参数 id: str


class CatalogAnswerModel(BaseModel):  # 定义类 CatalogAnswerModel，组织相关状态与行为
    answer: str = Field(min_length=1, max_length=8000)  # 计算 Field(min_length=1, max_length=8000) 并保存到变量 answer
    references: list[CatalogAnswerReference] = Field(default_factory=list)  # 计算 Field(default_factory=list) 并保存到变量 references
    confidence: float = Field(ge=0, le=1)  # 计算 Field(ge=0, le=1) 并保存到变量 confidence
    limitations: list[str] = Field(default_factory=list)  # 计算 Field(default_factory=list) 并保存到变量 limitations


class CatalogState(TypedDict, total=False):  # 定义类 CatalogState，组织相关状态与行为
    query: str  # 声明或继续传入参数 query: str
    resolved_query: str  # 声明或继续传入参数 resolved_query: str
    conversation: list[dict[str, str]]  # 声明或继续传入参数 conversation: list[dict[str, str]]
    catalog: dict[str, Any]  # 声明或继续传入参数 catalog: dict[str, Any]
    catalog_answer: dict[str, Any]  # 声明或继续传入参数 catalog_answer: dict[str, Any]
    agent_output: dict[str, Any]  # 声明或继续传入参数 agent_output: dict[str, Any]
    error: str | None  # 声明或继续传入参数 error: str | None


async def load_catalog(  # 定义异步函数 load_catalog，封装可被事件循环调度的协程逻辑
    state: CatalogState, runtime: Runtime[HarnessContext]  # 为函数 load_catalog 声明参数 state 及其类型或默认值
) -> dict:  # 结束 load_catalog 的参数列表并声明返回类型
    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "检索元数据"  # 计算 "检索元数据" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})
    context = runtime.context  # 计算 runtime.context 并保存到变量 context
    query = state.get("resolved_query") or state["query"]  # 计算 state.get("resolved_query") or state["query"] 并保存到变量 query
    async with context["tool_semaphore"]:  # 进入受管理的上下文 async with context["tool_semaphore"]:，确保资源正确获取与释放
        async with asyncio.timeout(context["settings"].tool_timeout_seconds):  # 进入受管理的上下文 async with asyncio.timeout(context["settings"].tool_timeout_seconds):，确保资源正确获取与释放
            embedding = await context["embedding_client"].aembed_query(query)  # 等待 目标函数 完成，并将其结果保存到 embedding
            async with asyncio.TaskGroup() as task_group:  # 进入受管理的上下文 async with asyncio.TaskGroup() as task_group:，确保资源正确获取与释放
                column_task = task_group.create_task(  # 调用 create_task 构造结果并保存到 column_task
                    context["column_qdrant_repository"].search(  # 调用 目标函数 执行当前步骤：context["column_qdrant_repository"].search(
                        embedding, limit=20  # 在函数 load_catalog 中执行表达式 embedding, limit=20，推进当前业务流程
                    )  # 结束函数 load_catalog 的参数及返回类型声明并开始函数体
                )  # 结束函数 load_catalog 的参数及返回类型声明并开始函数体
                metric_task = task_group.create_task(  # 调用 create_task 构造结果并保存到 metric_task
                    context["metric_qdrant_repository"].search(  # 调用 目标函数 执行当前步骤：context["metric_qdrant_repository"].search(
                        embedding, limit=20  # 在函数 load_catalog 中执行表达式 embedding, limit=20，推进当前业务流程
                    )  # 结束函数 load_catalog 的参数及返回类型声明并开始函数体
                )  # 结束函数 load_catalog 的参数及返回类型声明并开始函数体
            columns = column_task.result()  # 计算 column_task.result() 并保存到变量 columns
            metrics = metric_task.result()  # 计算 metric_task.result() 并保存到变量 metrics
    repository = context["meta_mysql_repository"]  # 计算 context["meta_mysql_repository"] 并保存到变量 repository
    table_ids = list(dict.fromkeys(item.table_id for item in columns if item.table_id))  # 计算 list(dict.fromkeys(item.table_id for item in columns if item.table_id)) 并保存到变量 table_ids
    table_records = []  # 计算 [] 并保存到变量 table_records
    async with asyncio.timeout(context["settings"].tool_timeout_seconds):  # 进入受管理的上下文 async with asyncio.timeout(context["settings"].tool_timeout_seconds):，确保资源正确获取与释放
        for table_id in table_ids[:10]:  # 按迭代条件执行循环：for table_id in table_ids[:10]:
            table = await repository.get_table_info_by_id(table_id)  # 等待 get_table_info_by_id 完成，并将其结果保存到 table
            if table:  # 判断分支条件：if table:
                table_columns = await repository.list_columns_by_table_id(table_id)  # 等待 list_columns_by_table_id 完成，并将其结果保存到 table_columns
                table_records.append(  # 调用 append 执行当前步骤：table_records.append(
                    {  # 在函数 load_catalog 中执行表达式 {，推进当前业务流程
                        "id": table.id,  # 为多行字典定义键 "id" 及其对应值
                        "name": table.name,  # 为多行字典定义键 "name" 及其对应值
                        "role": table.role,  # 为多行字典定义键 "role" 及其对应值
                        "description": table.description,  # 为多行字典定义键 "description" 及其对应值
                        "columns": [  # 为多行字典定义键 "columns" 及其对应值
                            {  # 在函数 load_catalog 中执行表达式 {，推进当前业务流程
                                "id": item.id,  # 为多行字典定义键 "id" 及其对应值
                                "name": item.name,  # 为多行字典定义键 "name" 及其对应值
                                "type": item.type,  # 为多行字典定义键 "type" 及其对应值
                                "role": item.role,  # 为多行字典定义键 "role" 及其对应值
                                "description": item.description,  # 为多行字典定义键 "description" 及其对应值
                                "alias": item.alias,  # 为多行字典定义键 "alias" 及其对应值
                            }  # 结束上一处多行结构，保持表达式边界清晰
                            for item in table_columns  # 按迭代条件执行循环：for item in table_columns
                        ],  # 结束上一处多行结构，保持表达式边界清晰
                    }  # 结束上一处多行结构，保持表达式边界清晰
                )  # 结束函数 load_catalog 的参数及返回类型声明并开始函数体
    metric_records = [  # 计算 [ 并保存到变量 metric_records
        {  # 在函数 load_catalog 中执行表达式 {，推进当前业务流程
            "id": item.id,  # 为多行字典定义键 "id" 及其对应值
            "name": item.name,  # 为多行字典定义键 "name" 及其对应值
            "description": item.description,  # 为多行字典定义键 "description" 及其对应值
            "relevant_columns": item.relevant_columns,  # 为多行字典定义键 "relevant_columns" 及其对应值
            "alias": item.alias,  # 为多行字典定义键 "alias" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
        for item in metrics[:20]  # 按迭代条件执行循环：for item in metrics[:20]
    ]  # 结束上一处多行结构，保持表达式边界清晰
    catalog = {"tables": table_records, "metrics": metric_records}  # 计算 {"tables": table_records, "metrics": metric_records} 并保存到变量 catalog
    writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
    return {"catalog": catalog}  # 返回 {"catalog": catalog} 给调用方


async def answer_catalog(  # 定义异步函数 answer_catalog，封装可被事件循环调度的协程逻辑
    state: CatalogState, runtime: Runtime[HarnessContext]  # 为函数 answer_catalog 声明参数 state 及其类型或默认值
) -> dict:  # 结束 answer_catalog 的参数列表并声明返回类型
    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "回答元数据问题"  # 计算 "回答元数据问题" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})
    context = runtime.context  # 计算 runtime.context 并保存到变量 context
    catalog = state.get("catalog", {"tables": [], "metrics": []})  # 计算 state.get("catalog", {"tables": [], "metrics": []}) 并保存到变量 catalog
    prompt = PromptTemplate(  # 调用 PromptTemplate 构造结果并保存到 prompt
        template=load_prompt("catalog_qa"),  # 为 load_prompt 设置关键字参数 template，传入当前行给出的值
        input_variables=["catalog", "history", "query"],  # 为 PromptTemplate 设置关键字参数 input_variables，传入当前行给出的值
    )  # 结束函数 answer_catalog 的参数及返回类型声明并开始函数体
    parser = JsonOutputParser(pydantic_object=CatalogAnswerModel)  # 计算 JsonOutputParser(pydantic_object=CatalogAnswerModel) 并保存到变量 parser
    chain = prompt | context["llm"].model | parser  # 计算 prompt | context["llm"].model | parser 并保存到变量 chain
    raw = await context["llm"].ainvoke(  # 等待 目标函数 完成，并将其结果保存到 raw
        chain,  # 继续向上一处调用或声明传入 chain
        {  # 在函数 answer_catalog 中执行表达式 {，推进当前业务流程
            "catalog": json.dumps(catalog, ensure_ascii=False),  # 为多行字典定义键 "catalog" 及其对应值
            "history": json.dumps(  # 为多行字典定义键 "history" 及其对应值
                state.get("conversation", [])[-12:], ensure_ascii=False  # 调用 get 执行当前步骤：state.get("conversation", [])[-12:], ensure_ascii=False
            ),  # 结束函数 answer_catalog 的参数及返回类型声明并开始函数体
            "query": state.get("resolved_query") or state["query"],  # 为多行字典定义键 "query" 及其对应值
        },  # 结束上一处多行结构，保持表达式边界清晰
        name="catalog_answer",  # 为 ainvoke 设置关键字参数 name，传入当前行给出的值
    )  # 结束函数 answer_catalog 的参数及返回类型声明并开始函数体
    parsed = CatalogAnswerModel.model_validate(raw)  # 计算 CatalogAnswerModel.model_validate(raw) 并保存到变量 parsed
    allowed_references = _allowed_reference_ids(catalog)  # 计算 _allowed_reference_ids(catalog) 并保存到变量 allowed_references
    references = [  # 计算 [ 并保存到变量 references
        reference.model_dump()  # 调用 model_dump 执行当前步骤：reference.model_dump()
        for reference in parsed.references  # 按迭代条件执行循环：for reference in parsed.references
        if (reference.type, reference.id) in allowed_references  # 判断分支条件：if (reference.type, reference.id) in allowed_references
    ]  # 结束上一处多行结构，保持表达式边界清晰
    output = {  # 计算 { 并保存到变量 output
        "agent_id": "catalog_qa",  # 为多行字典定义键 "agent_id" 及其对应值
        "text": parsed.answer,  # 为多行字典定义键 "text" 及其对应值
        "references": references,  # 为多行字典定义键 "references" 及其对应值
        "confidence": parsed.confidence,  # 为多行字典定义键 "confidence" 及其对应值
        "limitations": parsed.limitations[:10],  # 为多行字典定义键 "limitations" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰
    writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
    writer({"type": "result", "data": output})  # 调用 writer 执行当前步骤：writer({"type": "result", "data": output})
    return {"catalog_answer": parsed.model_dump(), "agent_output": output}  # 返回 {"catalog_answer": parsed.model_dump(), "agent_output": output} 给调用方


def _allowed_reference_ids(catalog: dict[str, Any]) -> set[tuple[str, str]]:  # 定义函数 _allowed_reference_ids，封装该模块的一项明确职责
    allowed: set[tuple[str, str]] = set()  # 计算 set() 并保存到变量 allowed
    for table in catalog.get("tables", []):  # 按迭代条件执行循环：for table in catalog.get("tables", []):
        allowed.add(("table", str(table["id"])))  # 调用 add 执行当前步骤：allowed.add(("table", str(table["id"])))
        for column in table.get("columns", []):  # 按迭代条件执行循环：for column in table.get("columns", []):
            allowed.add(("column", str(column["id"])))  # 调用 add 执行当前步骤：allowed.add(("column", str(column["id"])))
    for metric in catalog.get("metrics", []):  # 按迭代条件执行循环：for metric in catalog.get("metrics", []):
        allowed.add(("metric", str(metric["id"])))  # 调用 add 执行当前步骤：allowed.add(("metric", str(metric["id"])))
    return allowed  # 返回 allowed 给调用方


def build_catalog_graph():  # 定义函数 build_catalog_graph，封装该模块的一项明确职责
    builder = StateGraph(state_schema=CatalogState, context_schema=HarnessContext)  # 计算 StateGraph(state_schema=CatalogState, context_schema=HarnessContext) 并保存到变量 builder
    builder.add_node("load_catalog", traced_node("load_catalog", load_catalog))  # 调用 add_node 执行当前步骤：builder.add_node("load_catalog", traced_node("load_catalog", load_catal…
    builder.add_node("answer_catalog", traced_node("answer_catalog", answer_catalog))  # 调用 add_node 执行当前步骤：builder.add_node("answer_catalog", traced_node("answer_catalog", answer…
    builder.add_edge(START, "load_catalog")  # 调用 add_edge 执行当前步骤：builder.add_edge(START, "load_catalog")
    builder.add_edge("load_catalog", "answer_catalog")  # 调用 add_edge 执行当前步骤：builder.add_edge("load_catalog", "answer_catalog")
    builder.add_edge("answer_catalog", END)  # 调用 add_edge 执行当前步骤：builder.add_edge("answer_catalog", END)
    return builder.compile(name="catalog_qa")  # 返回 builder.compile(name="catalog_qa") 给调用方


def build_graph():  # 定义函数 build_graph，封装该模块的一项明确职责
    return build_catalog_graph()  # 返回 build_catalog_graph() 给调用方
