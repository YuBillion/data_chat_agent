"""
召回信息合并节点

负责把字段 字段取值和指标三路召回结果聚合成统一上下文
这一层会补齐指标依赖字段 字段真实取值 主外键字段和表信息
后续过滤节点不再关心信息来自哪个检索分支，只处理合并后的表上下文和指标上下文
"""

from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    ColumnInfoState,  # 从当前 import 模块导入符号 ColumnInfoState
    DataAgentState,  # 从当前 import 模块导入符号 DataAgentState
    MetricInfoState,  # 从当前 import 模块导入符号 MetricInfoState
    TableInfoState,  # 从当前 import 模块导入符号 TableInfoState
)  # 结束多符号导入列表
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.entities.column_info import ColumnInfo  # 从 app.entities.column_info 导入 ColumnInfo，供本模块后续代码使用
from app.entities.metric_info import MetricInfo  # 从 app.entities.metric_info 导入 MetricInfo，供本模块后续代码使用
from app.entities.table_info import TableInfo  # 从 app.entities.table_info 导入 TableInfo，供本模块后续代码使用
from app.entities.value_info import ValueInfo  # 从 app.entities.value_info 导入 ValueInfo，供本模块后续代码使用


async def merge_retrieved_info(  # 定义异步函数 merge_retrieved_info，封装可被事件循环调度的协程逻辑
    state: DataAgentState, runtime: Runtime[DataAgentContext]  # 为函数 merge_retrieved_info 声明参数 state 及其类型或默认值
):  # 结束 merge_retrieved_info 的参数列表并声明返回类型
    """合并召回结果，并输出 SQL 生成前的候选表信息和指标信息"""

    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "合并召回信息"  # 计算 "合并召回信息" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})

    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        retrieved_column_infos: list[ColumnInfo] = state["retrieved_column_infos"]  # 计算 state["retrieved_column_infos"] 并保存到变量 retrieved_column_infos
        retrieved_metric_infos: list[MetricInfo] = state["retrieved_metric_infos"]  # 计算 state["retrieved_metric_infos"] 并保存到变量 retrieved_metric_infos
        retrieved_value_infos: list[ValueInfo] = state["retrieved_value_infos"]  # 计算 state["retrieved_value_infos"] 并保存到变量 retrieved_value_infos

        meta_mysql_repository = runtime.context["meta_mysql_repository"]  # 计算 runtime.context["meta_mysql_repository"] 并保存到变量 meta_mysql_repository

        # 本节点的主线是：
        # 字段召回 + 指标依赖字段 + 字段真实取值 + 主外键补齐
        # -> table_infos / metric_infos，交给后续过滤和 SQL 生成节点继续使用。

        # 1. 以 column_id 为 key 合并字段信息
        # 三路召回可能命中同一个字段，用 dict 可以自然去重；
        # 后续指标依赖字段和字段取值也都通过 column_id 合并进来。
        retrieved_column_infos_map: dict[str, ColumnInfo] = {  # 计算 { 并保存到变量 retrieved_column_infos_map
            retrieved_column_info.id: retrieved_column_info  # 在函数 merge_retrieved_info 中执行表达式 retrieved_column_info.id: retrieved_column_info，推进当前业务流程
            for retrieved_column_info in retrieved_column_infos  # 按迭代条件执行循环：for retrieved_column_info in retrieved_column_infos
        }  # 结束上一处多行结构，保持表达式边界清晰

        # 2. 补齐指标依赖字段
        # 指标告诉模型“怎么算”，但生成 SQL 还需要知道指标依赖哪些真实字段。
        # 如果相关字段没有被字段召回命中，就从 Meta MySQL 里按 id 查出来补进上下文。
        for retrieved_metric_info in retrieved_metric_infos:  # 按迭代条件执行循环：for retrieved_metric_info in retrieved_metric_infos:
            for relevant_column in retrieved_metric_info.relevant_columns:  # 按迭代条件执行循环：for relevant_column in retrieved_metric_info.relevant_columns:
                if relevant_column not in retrieved_column_infos_map:  # 判断分支条件：if relevant_column not in retrieved_column_infos_map:
                    column_info: ColumnInfo = (  # 调用 目标函数 构造结果并保存到 column_info
                        await meta_mysql_repository.get_column_info_by_id(  # 等待异步操作完成并取得结果：meta_mysql_repository.get_column_info_by_id(
                            relevant_column  # 在函数 merge_retrieved_info 中执行表达式 relevant_column，推进当前业务流程
                        )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体
                    )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体
                    retrieved_column_infos_map[relevant_column] = column_info  # 计算 column_info 并保存到变量 retrieved_column_infos_map[relevant_column]

        # 3. 把字段取值合并回字段 examples
        # 字段取值召回命中的是 column_id + value，例如 dim_region.region_name.华北。
        # 把真实 value 放进字段 examples，可以帮助模型写出更接近真实数据的 where 条件。
        for retrieved_value_info in retrieved_value_infos:  # 按迭代条件执行循环：for retrieved_value_info in retrieved_value_infos:
            value = retrieved_value_info.value  # 计算 retrieved_value_info.value 并保存到变量 value
            column_id = retrieved_value_info.column_id  # 计算 retrieved_value_info.column_id 并保存到变量 column_id
            if column_id not in retrieved_column_infos_map:  # 判断分支条件：if column_id not in retrieved_column_infos_map:
                column_info: ColumnInfo = (  # 调用 目标函数 构造结果并保存到 column_info
                    await meta_mysql_repository.get_column_info_by_id(column_id)  # 等待异步操作完成并取得结果：meta_mysql_repository.get_column_info_by_id(column_id)
                )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体
                retrieved_column_infos_map[column_id] = column_info  # 计算 column_info 并保存到变量 retrieved_column_infos_map[column_id]
            if value not in retrieved_column_infos_map[column_id].examples:  # 判断分支条件：if value not in retrieved_column_infos_map[column_id].examples:
                retrieved_column_infos_map[column_id].examples.append(value)  # 调用 目标函数 执行当前步骤：retrieved_column_infos_map[column_id].examples.append(value)

        # 4. 按表组织字段上下文
        # SQL 生成提示词通常按“表 -> 字段列表”的方式描述结构，
        # 所以这里先把分散的字段按 table_id 归到各自所属表下面。
        table_to_columns_map: dict[str, list[ColumnInfo]] = {}  # 计算 {} 并保存到变量 table_to_columns_map
        for column_info in retrieved_column_infos_map.values():  # 按迭代条件执行循环：for column_info in retrieved_column_infos_map.values():
            table_id = column_info.table_id  # 计算 column_info.table_id 并保存到变量 table_id
            if table_id not in table_to_columns_map:  # 判断分支条件：if table_id not in table_to_columns_map:
                table_to_columns_map[table_id] = []  # 计算 [] 并保存到变量 table_to_columns_map[table_id]
            table_to_columns_map[table_id].append(column_info)  # 调用 目标函数 执行当前步骤：table_to_columns_map[table_id].append(column_info)

        # 5. 补齐主外键字段
        # 主外键通常不会出现在用户问题里，单靠向量召回容易漏掉；
        # 但多表查询的 Join 路径必须依赖它们，所以每张候选表都要兜底补齐。
        for table_id in table_to_columns_map.keys():  # 按迭代条件执行循环：for table_id in table_to_columns_map.keys():
            key_columns: list[  # 声明或继续传入参数 key_columns: list[
                ColumnInfo  # 在函数 merge_retrieved_info 中执行表达式 ColumnInfo，推进当前业务流程
            ] = await meta_mysql_repository.get_key_columns_by_table_id(table_id)  # 调用 目标函数 执行当前步骤：] = await meta_mysql_repository.get_key_columns_by_table_id(table_id)
            column_ids = [  # 计算 [ 并保存到变量 column_ids
                column_info.id for column_info in table_to_columns_map[table_id]  # 在函数 merge_retrieved_info 中执行表达式 column_info.id for column_info in table_to_columns_map[table_id]，推进当前业务流程
            ]  # 结束上一处多行结构，保持表达式边界清晰
            for key_column in key_columns:  # 按迭代条件执行循环：for key_column in key_columns:
                if key_column.id not in column_ids:  # 判断分支条件：if key_column.id not in column_ids:
                    table_to_columns_map[table_id].append(key_column)  # 调用 目标函数 执行当前步骤：table_to_columns_map[table_id].append(key_column)

        # 6. 生成表结构上下文
        # 数据库实体里可能包含入库和索引用字段，传给模型前只保留必要信息，
        # 让后续过滤和 SQL 生成节点面对的是更稳定的 TableInfoState 结构。
        table_infos: list[TableInfoState] = []  # 计算 [] 并保存到变量 table_infos
        for table_id, column_infos in table_to_columns_map.items():  # 按迭代条件执行循环：for table_id, column_infos in table_to_columns_map.items():
            table_info: TableInfo = await meta_mysql_repository.get_table_info_by_id(  # 等待 get_table_info_by_id 完成，并将其结果保存到 table_info
                table_id  # 在函数 merge_retrieved_info 中执行表达式 table_id，推进当前业务流程
            )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体
            columns = [  # 计算 [ 并保存到变量 columns
                ColumnInfoState(  # 调用 ColumnInfoState 执行当前步骤：ColumnInfoState(
                    name=column_info.name,  # 为 ColumnInfoState 设置关键字参数 name，传入当前行给出的值
                    type=column_info.type,  # 为 ColumnInfoState 设置关键字参数 type，传入当前行给出的值
                    role=column_info.role,  # 为 ColumnInfoState 设置关键字参数 role，传入当前行给出的值
                    examples=column_info.examples,  # 为 ColumnInfoState 设置关键字参数 examples，传入当前行给出的值
                    description=column_info.description,  # 为 ColumnInfoState 设置关键字参数 description，传入当前行给出的值
                    alias=column_info.alias,  # 为 ColumnInfoState 设置关键字参数 alias，传入当前行给出的值
                )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体
                for column_info in column_infos  # 按迭代条件执行循环：for column_info in column_infos
            ]  # 结束上一处多行结构，保持表达式边界清晰
            table_info_state = TableInfoState(  # 调用 TableInfoState 构造结果并保存到 table_info_state
                name=table_info.name,  # 为 TableInfoState 设置关键字参数 name，传入当前行给出的值
                role=table_info.role,  # 为 TableInfoState 设置关键字参数 role，传入当前行给出的值
                description=table_info.description,  # 为 TableInfoState 设置关键字参数 description，传入当前行给出的值
                columns=columns,  # 为 TableInfoState 设置关键字参数 columns，传入当前行给出的值
            )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体
            table_infos.append(table_info_state)  # 调用 append 执行当前步骤：table_infos.append(table_info_state)

        # 7. 生成指标上下文
        # 指标上下文保留名称 描述 别名和依赖字段，足够让模型理解业务口径。
        metric_infos: list[MetricInfoState] = [  # 计算 [ 并保存到变量 metric_infos
            MetricInfoState(  # 调用 MetricInfoState 执行当前步骤：MetricInfoState(
                name=retrieved_metric_info.name,  # 为 MetricInfoState 设置关键字参数 name，传入当前行给出的值
                description=retrieved_metric_info.description,  # 为 MetricInfoState 设置关键字参数 description，传入当前行给出的值
                relevant_columns=retrieved_metric_info.relevant_columns,  # 为 MetricInfoState 设置关键字参数 relevant_columns，传入当前行给出的值
                alias=retrieved_metric_info.alias,  # 为 MetricInfoState 设置关键字参数 alias，传入当前行给出的值
            )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体
            for retrieved_metric_info in retrieved_metric_infos  # 按迭代条件执行循环：for retrieved_metric_info in retrieved_metric_infos
        ]  # 结束上一处多行结构，保持表达式边界清晰

        logger.info(  # 调用 info 执行当前步骤：logger.info(
            f"合并后的表信息：{[table_info['name'] for table_info in table_infos]}"  # 在函数 merge_retrieved_info 中执行表达式 f"合并后的表信息：{[table_info['name'] for table_info in table_infos]}"，推进当前业务流程
        )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体
        logger.info(  # 调用 info 执行当前步骤：logger.info(
            f"合并后的指标信息：{[metric_info['name'] for metric_info in metric_infos]}"  # 在函数 merge_retrieved_info 中执行表达式 f"合并后的指标信息：{[metric_info['name'] for metric_info in metric_infos]}"，推进当前业务流程
        )  # 结束函数 merge_retrieved_info 的参数及返回类型声明并开始函数体

        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        return {  # 返回 { 给调用方
            "table_infos": table_infos,  # 为多行字典定义键 "table_infos" 及其对应值
            "metric_infos": metric_infos,  # 为多行字典定义键 "metric_infos" 及其对应值
        }  # 结束上一处多行结构，保持表达式边界清晰
    except Exception as e:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as e:
        logger.error(f"{step} failed: {e}")  # 调用 error 执行当前步骤：logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
