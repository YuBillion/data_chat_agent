"""
元数据知识构建服务

负责组织元数据知识库构建的核心业务流程，位于脚本入口和仓储层之间
一方面接收配置文件，另一方面协调元数据库和数仓查询仓储

当前这条主线已经覆盖表字段入库 字段向量索引 字段取值全文索引
以及指标入库和指标向量索引构建逻辑
"""

import uuid  # 导入uuid，建立本模块需要的外部能力引用
from dataclasses import asdict  # 从 dataclasses 导入 asdict，供本模块后续代码使用
from pathlib import Path  # 从 pathlib 导入 Path，供本模块后续代码使用

from langchain_huggingface import HuggingFaceEndpointEmbeddings  # 从 langchain_huggingface 导入 HuggingFaceEndpointEmbeddings，供本模块后续代码使用
from omegaconf import OmegaConf  # 从 omegaconf 导入 OmegaConf，供本模块后续代码使用

from app.conf.meta_config import MetaConfig  # 从 app.conf.meta_config 导入 MetaConfig，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.entities.column_info import ColumnInfo  # 从 app.entities.column_info 导入 ColumnInfo，供本模块后续代码使用
from app.entities.column_metric import ColumnMetric  # 从 app.entities.column_metric 导入 ColumnMetric，供本模块后续代码使用
from app.entities.metric_info import MetricInfo  # 从 app.entities.metric_info 导入 MetricInfo，供本模块后续代码使用
from app.entities.table_info import TableInfo  # 从 app.entities.table_info 导入 TableInfo，供本模块后续代码使用
from app.entities.value_info import ValueInfo  # 从 app.entities.value_info 导入 ValueInfo，供本模块后续代码使用
from app.repositories.es.value_es_repository import ValueESRepository  # 从 app.repositories.es.value_es_repository 导入 ValueESRepository，供本模块后续代码使用
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository  # 从 app.repositories.mysql.dw.dw_mysql_repository 导入 DWMySQLRepository，供本模块后续代码使用
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository  # 从 app.repositories.mysql.meta.meta_mysql_repository 导入 MetaMySQLRepository，供本模块后续代码使用
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository  # 从 app.repositories.qdrant.column_qdrant_repository 导入 ColumnQdrantRepository，供本模块后续代码使用
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository  # 从 app.repositories.qdrant.metric_qdrant_repository 导入 MetricQdrantRepository，供本模块后续代码使用

PROJECT_ROOT = Path(__file__).parents[2].resolve()  # 计算 Path(__file__).parents[2].resolve() 并保存到变量 PROJECT_ROOT


class MetaKnowledgeService:  # 定义类 MetaKnowledgeService，组织相关状态与行为
    """负责串联元数据知识库构建流程的应用服务"""

    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        meta_mysql_repository: MetaMySQLRepository,  # 为函数 __init__ 声明参数 meta_mysql_repository 及其类型或默认值
        dw_mysql_repository: DWMySQLRepository,  # 为函数 __init__ 声明参数 dw_mysql_repository 及其类型或默认值
        column_qdrant_repository: ColumnQdrantRepository,  # 为函数 __init__ 声明参数 column_qdrant_repository 及其类型或默认值
        embedding_client: HuggingFaceEndpointEmbeddings,  # 为函数 __init__ 声明参数 embedding_client 及其类型或默认值
        value_es_repository: ValueESRepository,  # 为函数 __init__ 声明参数 value_es_repository 及其类型或默认值
        metric_qdrant_repository: MetricQdrantRepository,  # 为函数 __init__ 声明参数 metric_qdrant_repository 及其类型或默认值
    ):  # 结束 __init__ 的参数列表并声明返回类型
        # meta repository 负责结构化元数据的落库
        self.meta_mysql_repository: MetaMySQLRepository = meta_mysql_repository  # 将 meta_mysql_repository 保存到实例属性 self.meta_mysql_repository
        # dw repository 负责到教学数仓中读取真实表结构和示例值
        self.dw_mysql_repository: DWMySQLRepository = dw_mysql_repository  # 将 dw_mysql_repository 保存到实例属性 self.dw_mysql_repository
        # 字段向量集合的创建和写入统一交给 Qdrant Repository
        self.column_qdrant_repository: ColumnQdrantRepository = column_qdrant_repository  # 将 column_qdrant_repository 保存到实例属性 self.column_qdrant_repository
        # 向量化动作放在 Service 层
        self.embedding_client: HuggingFaceEndpointEmbeddings = embedding_client  # 将 embedding_client 保存到实例属性 self.embedding_client
        # 字段值全文索引的写入统一交给 ES Repository
        self.value_es_repository: ValueESRepository = value_es_repository  # 将 value_es_repository 保存到实例属性 self.value_es_repository
        # 指标向量集合和字段向量集合分开管理，便于后续按对象类型独立召回
        self.metric_qdrant_repository: MetricQdrantRepository = metric_qdrant_repository  # 将 metric_qdrant_repository 保存到实例属性 self.metric_qdrant_repository

    async def _save_tables_to_meta_db(  # 定义异步函数 _save_tables_to_meta_db，封装可被事件循环调度的协程逻辑
        self, meta_config: MetaConfig  # 为函数 _save_tables_to_meta_db 声明参数 self, meta_config 及其类型或默认值
    ) -> list[ColumnInfo]:  # 结束 _save_tables_to_meta_db 的参数列表并声明返回类型
        """把配置里的表字段信息补齐后写入 Meta MySQL"""
        table_infos: list[TableInfo] = []  # 计算 [] 并保存到变量 table_infos
        column_infos: list[ColumnInfo] = []  # 计算 [] 并保存到变量 column_infos

        for table in meta_config.tables:  # 按迭代条件执行循环：for table in meta_config.tables:
            # 先把配置里的表定义整理成业务实体，后面统一交给 Meta Repository 落库
            table_info = TableInfo(  # 调用 TableInfo 构造结果并保存到 table_info
                id=table.name,  # 为 TableInfo 设置关键字参数 id，传入当前行给出的值
                name=table.name,  # 为 TableInfo 设置关键字参数 name，传入当前行给出的值
                role=table.role,  # 为 TableInfo 设置关键字参数 role，传入当前行给出的值
                description=table.description,  # 为 TableInfo 设置关键字参数 description，传入当前行给出的值
            )  # 结束 TableInfo 调用参数，得到完整表达式结果
            table_infos.append(table_info)  # 调用 append 执行当前步骤：table_infos.append(table_info)

            # 字段类型属于数仓里的真实信息，所以这里仍然要回到 DW 查询
            column_types = await self.dw_mysql_repository.get_column_types(table.name)  # 等待 get_column_types 完成，并将其结果保存到 column_types

            for column in table.columns:  # 按迭代条件执行循环：for column in table.columns:
                # 这里只拿少量示例值，目的是让字段元数据更容易被人和模型理解
                column_values = await self.dw_mysql_repository.get_column_values(  # 等待 get_column_values 完成，并将其结果保存到 column_values
                    table.name, column.name  # 在函数 _save_tables_to_meta_db 中执行表达式 table.name, column.name，推进当前业务流程
                )  # 结束 self.dw_mysql_repository.get_column_values 调用参数，得到完整表达式结果
                # 字段 id 使用 table.column 形式，后续在向量索引和全文索引里都会复用
                column_info = ColumnInfo(  # 调用 ColumnInfo 构造结果并保存到 column_info
                    id=f"{table.name}.{column.name}",  # 为 ColumnInfo 设置关键字参数 id，传入当前行给出的值
                    name=column.name,  # 为 ColumnInfo 设置关键字参数 name，传入当前行给出的值
                    type=column_types[column.name],  # 为 ColumnInfo 设置关键字参数 type，传入当前行给出的值
                    role=column.role,  # 为 ColumnInfo 设置关键字参数 role，传入当前行给出的值
                    examples=column_values,  # 为 ColumnInfo 设置关键字参数 examples，传入当前行给出的值
                    description=column.description,  # 为 ColumnInfo 设置关键字参数 description，传入当前行给出的值
                    alias=column.alias,  # 为 ColumnInfo 设置关键字参数 alias，传入当前行给出的值
                    table_id=table.name,  # 为 ColumnInfo 设置关键字参数 table_id，传入当前行给出的值
                )  # 结束 ColumnInfo 调用参数，得到完整表达式结果
                column_infos.append(column_info)  # 调用 append 执行当前步骤：column_infos.append(column_info)

        async with self.meta_mysql_repository.session.begin():  # 进入受管理的上下文 async with self.meta_mysql_repository.session.begin():，确保资源正确获取与释放
            self.meta_mysql_repository.save_table_infos(table_infos)  # 调用 save_table_infos 执行当前步骤：self.meta_mysql_repository.save_table_infos(table_infos)
            self.meta_mysql_repository.save_column_infos(column_infos)  # 调用 save_column_infos 执行当前步骤：self.meta_mysql_repository.save_column_infos(column_infos)

        return column_infos  # 返回 column_infos 给调用方

    async def _save_column_info_to_qdrant(self, column_infos: list[ColumnInfo]):  # 定义异步函数 _save_column_info_to_qdrant，封装可被事件循环调度的协程逻辑
        """把字段元数据继续推进成可语义检索的 Qdrant 向量点"""
        await self.column_qdrant_repository.ensure_collection()  # 等待异步操作完成并取得结果：self.column_qdrant_repository.ensure_collection()

        points: list[dict] = []  # 计算 [] 并保存到变量 points
        for column_info in column_infos:  # 按迭代条件执行循环：for column_info in column_infos:
            # 一个字段不会只生成一个向量点，而是把名字 描述 别名都拆开建立语义入口
            points.append(  # 调用 append 执行当前步骤：points.append(
                {  # 在函数 _save_column_info_to_qdrant 中执行表达式 {，推进当前业务流程
                    "id": uuid.uuid4(),  # 为多行字典定义键 "id" 及其对应值
                    "embedding_text": column_info.name,  # 为多行字典定义键 "embedding_text" 及其对应值
                    "payload": asdict(column_info),  # 为多行字典定义键 "payload" 及其对应值
                }  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束 points.append 调用参数，得到完整表达式结果

            points.append(  # 调用 append 执行当前步骤：points.append(
                {  # 在函数 _save_column_info_to_qdrant 中执行表达式 {，推进当前业务流程
                    "id": uuid.uuid4(),  # 为多行字典定义键 "id" 及其对应值
                    "embedding_text": column_info.description,  # 为多行字典定义键 "embedding_text" 及其对应值
                    "payload": asdict(column_info),  # 为多行字典定义键 "payload" 及其对应值
                }  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束 points.append 调用参数，得到完整表达式结果

            for alia in column_info.alias:  # 按迭代条件执行循环：for alia in column_info.alias:
                points.append(  # 调用 append 执行当前步骤：points.append(
                    {  # 在函数 _save_column_info_to_qdrant 中执行表达式 {，推进当前业务流程
                        "id": uuid.uuid4(),  # 为多行字典定义键 "id" 及其对应值
                        "embedding_text": alia,  # 为多行字典定义键 "embedding_text" 及其对应值
                        "payload": asdict(column_info),  # 为多行字典定义键 "payload" 及其对应值
                    }  # 结束上一处多行结构，保持表达式边界清晰
                )  # 结束 points.append 调用参数，得到完整表达式结果

        # 先把待向量化文本抽出来，再分批调用 Embedding 服务
        # 这样更容易控制单次请求大小
        embeddings: list[list[float]] = []  # 计算 [] 并保存到变量 embeddings
        embedding_texts = [point["embedding_text"] for point in points]  # 计算 [point["embedding_text"] for point in points] 并保存到变量 embedding_texts
        embedding_batch_size = 20  # 计算 20 并保存到变量 embedding_batch_size
        for i in range(0, len(embedding_texts), embedding_batch_size):  # 按迭代条件执行循环：for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i : i + embedding_batch_size]  # 计算 embedding_texts[i : i + embedding_batch_size] 并保存到变量 batch_embedding_texts
            batch_embeddings = await self.embedding_client.aembed_documents(  # 等待 aembed_documents 完成，并将其结果保存到 batch_embeddings
                batch_embedding_texts  # 在函数 _save_column_info_to_qdrant 中执行表达式 batch_embedding_texts，推进当前业务流程
            )  # 结束 self.embedding_client.aembed_documents 调用参数，得到完整表达式结果
            embeddings.extend(batch_embeddings)  # 调用 extend 执行当前步骤：embeddings.extend(batch_embeddings)

        ids = [point["id"] for point in points]  # 计算 [point["id"] for point in points] 并保存到变量 ids
        payloads = [point["payload"] for point in points]  # 计算 [point["payload"] for point in points] 并保存到变量 payloads

        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)  # 等待异步操作完成并取得结果：self.column_qdrant_repository.upsert(ids, embeddings, payloads)

    async def _save_value_info_to_es(  # 定义异步函数 _save_value_info_to_es，封装可被事件循环调度的协程逻辑
        self, meta_config: MetaConfig, column_infos: list[ColumnInfo]  # 为函数 _save_value_info_to_es 声明参数 self, meta_config 及其类型或默认值
    ):  # 结束 _save_value_info_to_es 的参数列表并声明返回类型
        """把允许同步的字段真实取值写入 Elasticsearch 全文索引"""
        await self.value_es_repository.ensure_index()  # 等待异步操作完成并取得结果：self.value_es_repository.ensure_index()

        # 不是所有字段都要同步真实值，是否同步由配置里的 sync 显式控制
        column2sync: dict[str, bool] = {}  # 计算 {} 并保存到变量 column2sync
        for table in meta_config.tables:  # 按迭代条件执行循环：for table in meta_config.tables:
            for column in table.columns:  # 按迭代条件执行循环：for column in table.columns:
                column2sync[f"{table.name}.{column.name}"] = column.sync  # 计算 column.sync 并保存到变量 column2sync[f"{table.name}.{column.name}"]

        value_infos: list[ValueInfo] = []  # 计算 [] 并保存到变量 value_infos
        for column_info in column_infos:  # 按迭代条件执行循环：for column_info in column_infos:
            sync = column2sync[column_info.id]  # 计算 column2sync[column_info.id] 并保存到变量 sync
            if sync:  # 判断分支条件：if sync:
                # 这里拿的是字段真实值全集，不再是第 8 章里的少量 examples
                current_column_values = (  # 调用 目标函数 构造结果并保存到 current_column_values
                    await self.dw_mysql_repository.get_column_values(  # 等待异步操作完成并取得结果：self.dw_mysql_repository.get_column_values(
                        column_info.table_id, column_info.name, 100000  # 在函数 _save_value_info_to_es 中执行表达式 column_info.table_id, column_info.name, 100000，推进当前业务流程
                    )  # 结束 self.dw_mysql_repository.get_column_values 调用参数，得到完整表达式结果
                )  # 结束函数 _save_value_info_to_es 的调用或声明结构
                current_values_infos = [  # 计算 [ 并保存到变量 current_values_infos
                    ValueInfo(  # 调用 ValueInfo 执行当前步骤：ValueInfo(
                        id=f"{column_info.id}.{current_column_value}",  # 为 ValueInfo 设置关键字参数 id，传入当前行给出的值
                        value=current_column_value,  # 为 ValueInfo 设置关键字参数 value，传入当前行给出的值
                        column_id=column_info.id,  # 为 ValueInfo 设置关键字参数 column_id，传入当前行给出的值
                    )  # 结束 ValueInfo 调用参数，得到完整表达式结果
                    for current_column_value in current_column_values  # 按迭代条件执行循环：for current_column_value in current_column_values
                ]  # 结束上一处多行结构，保持表达式边界清晰
                value_infos.extend(current_values_infos)  # 调用 extend 执行当前步骤：value_infos.extend(current_values_infos)

        await self.value_es_repository.index(value_infos)  # 等待异步操作完成并取得结果：self.value_es_repository.index(value_infos)

    async def _save_metrics_to_meta_db(  # 定义异步函数 _save_metrics_to_meta_db，封装可被事件循环调度的协程逻辑
        self, meta_config: MetaConfig  # 为函数 _save_metrics_to_meta_db 声明参数 self, meta_config 及其类型或默认值
    ) -> list[MetricInfo]:  # 结束 _save_metrics_to_meta_db 的参数列表并声明返回类型
        """把配置里的指标信息和字段依赖关系写入 Meta MySQL"""
        metric_infos: list[MetricInfo] = []  # 计算 [] 并保存到变量 metric_infos
        column_metrics: list[ColumnMetric] = []  # 计算 [] 并保存到变量 column_metrics

        for metric in meta_config.metrics:  # 按迭代条件执行循环：for metric in meta_config.metrics:
            # MetricInfo 表达指标本身，当前直接用指标名作为稳定业务 id
            metric_info = MetricInfo(  # 调用 MetricInfo 构造结果并保存到 metric_info
                id=metric.name,  # 为 MetricInfo 设置关键字参数 id，传入当前行给出的值
                name=metric.name,  # 为 MetricInfo 设置关键字参数 name，传入当前行给出的值
                description=metric.description,  # 为 MetricInfo 设置关键字参数 description，传入当前行给出的值
                relevant_columns=metric.relevant_columns,  # 为 MetricInfo 设置关键字参数 relevant_columns，传入当前行给出的值
                alias=metric.alias,  # 为 MetricInfo 设置关键字参数 alias，传入当前行给出的值
            )  # 结束 MetricInfo 调用参数，得到完整表达式结果
            metric_infos.append(metric_info)  # 调用 append 执行当前步骤：metric_infos.append(metric_info)
            for column in metric.relevant_columns:  # 按迭代条件执行循环：for column in metric.relevant_columns:
                # ColumnMetric 单独表达“某个指标依赖某个字段”这层关系
                column_metric = ColumnMetric(column_id=column, metric_id=metric.name)  # 计算 ColumnMetric(column_id=column, metric_id=metric.name) 并保存到变量 column_metric
                column_metrics.append(column_metric)  # 调用 append 执行当前步骤：column_metrics.append(column_metric)

        # 指标本身和字段关系要放在同一笔事务里，避免只写入其中一部分
        async with self.meta_mysql_repository.session.begin():  # 进入受管理的上下文 async with self.meta_mysql_repository.session.begin():，确保资源正确获取与释放
            self.meta_mysql_repository.save_metric_infos(metric_infos)  # 调用 save_metric_infos 执行当前步骤：self.meta_mysql_repository.save_metric_infos(metric_infos)
            self.meta_mysql_repository.save_column_metrics(column_metrics)  # 调用 save_column_metrics 执行当前步骤：self.meta_mysql_repository.save_column_metrics(column_metrics)

        return metric_infos  # 返回 metric_infos 给调用方

    async def _save_metrics_to_qdrant(self, metric_infos: list[MetricInfo]):  # 定义异步函数 _save_metrics_to_qdrant，封装可被事件循环调度的协程逻辑
        """把指标元数据继续推进成可语义检索的 Qdrant 向量点"""
        await self.metric_qdrant_repository.ensure_collection()  # 等待异步操作完成并取得结果：self.metric_qdrant_repository.ensure_collection()

        points: list[dict] = []  # 计算 [] 并保存到变量 points
        for metric_info in metric_infos:  # 按迭代条件执行循环：for metric_info in metric_infos:
            # 和字段一样，一个指标也会拆成名字 描述 别名这几类语义入口
            points.append(  # 调用 append 执行当前步骤：points.append(
                {  # 在函数 _save_metrics_to_qdrant 中执行表达式 {，推进当前业务流程
                    "id": uuid.uuid4(),  # 为多行字典定义键 "id" 及其对应值
                    "embedding_text": metric_info.name,  # 为多行字典定义键 "embedding_text" 及其对应值
                    "payload": asdict(metric_info),  # 为多行字典定义键 "payload" 及其对应值
                }  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束 points.append 调用参数，得到完整表达式结果

            points.append(  # 调用 append 执行当前步骤：points.append(
                {  # 在函数 _save_metrics_to_qdrant 中执行表达式 {，推进当前业务流程
                    "id": uuid.uuid4(),  # 为多行字典定义键 "id" 及其对应值
                    "embedding_text": metric_info.description,  # 为多行字典定义键 "embedding_text" 及其对应值
                    "payload": asdict(metric_info),  # 为多行字典定义键 "payload" 及其对应值
                }  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束 points.append 调用参数，得到完整表达式结果

            for alia in metric_info.alias:  # 按迭代条件执行循环：for alia in metric_info.alias:
                points.append(  # 调用 append 执行当前步骤：points.append(
                    {  # 在函数 _save_metrics_to_qdrant 中执行表达式 {，推进当前业务流程
                        "id": uuid.uuid4(),  # 为多行字典定义键 "id" 及其对应值
                        "embedding_text": alia,  # 为多行字典定义键 "embedding_text" 及其对应值
                        "payload": asdict(metric_info),  # 为多行字典定义键 "payload" 及其对应值
                    }  # 结束上一处多行结构，保持表达式边界清晰
                )  # 结束 points.append 调用参数，得到完整表达式结果

        # 先把待向量化文本抽出来，再分批调用 Embedding 服务
        # 返回的 embeddings 要继续和前面的 id payload 按顺序对齐
        embeddings: list[list[float]] = []  # 计算 [] 并保存到变量 embeddings
        embedding_texts = [point["embedding_text"] for point in points]  # 计算 [point["embedding_text"] for point in points] 并保存到变量 embedding_texts
        embedding_batch_size = 20  # 计算 20 并保存到变量 embedding_batch_size
        for i in range(0, len(embedding_texts), embedding_batch_size):  # 按迭代条件执行循环：for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i : i + embedding_batch_size]  # 计算 embedding_texts[i : i + embedding_batch_size] 并保存到变量 batch_embedding_texts
            batch_embeddings = await self.embedding_client.aembed_documents(  # 等待 aembed_documents 完成，并将其结果保存到 batch_embeddings
                batch_embedding_texts  # 在函数 _save_metrics_to_qdrant 中执行表达式 batch_embedding_texts，推进当前业务流程
            )  # 结束 self.embedding_client.aembed_documents 调用参数，得到完整表达式结果
            embeddings.extend(batch_embeddings)  # 调用 extend 执行当前步骤：embeddings.extend(batch_embeddings)

        ids = [point["id"] for point in points]  # 计算 [point["id"] for point in points] 并保存到变量 ids
        payloads = [point["payload"] for point in points]  # 计算 [point["payload"] for point in points] 并保存到变量 payloads

        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)  # 等待异步操作完成并取得结果：self.metric_qdrant_repository.upsert(ids, embeddings, payloads)

    async def build(self, config_path: Path):  # 定义异步函数 build，封装可被事件循环调度的协程逻辑
        """读取配置并依次构建 Meta MySQL Qdrant 和 ES 中的元数据索引"""
        resolved_path = config_path.resolve()  # 计算 config_path.resolve() 并保存到变量 resolved_path
        if not resolved_path.is_relative_to(PROJECT_ROOT):  # 判断分支条件：if not resolved_path.is_relative_to(PROJECT_ROOT):
            raise ValueError("meta config path must stay inside the project")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("meta config path must stay inside the project")
        context = OmegaConf.load(resolved_path)  # 计算 OmegaConf.load(resolved_path) 并保存到变量 context
        schema = OmegaConf.structured(MetaConfig)  # 计算 OmegaConf.structured(MetaConfig) 并保存到变量 schema
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))  # 计算 OmegaConf.to_object(OmegaConf.merge(schema, context)) 并保存到变量 meta_config

        # 根据配置文件判断后续要进入哪条构建链路
        if meta_config.tables:  # 判断分支条件：if meta_config.tables:
            # 将表信息和字段信息保存到 Meta MySQL
            column_infos = await self._save_tables_to_meta_db(meta_config)  # 等待 _save_tables_to_meta_db 完成，并将其结果保存到 column_infos
            logger.info("保存表信息和字段信息到 Meta MySQL")  # 调用 info 执行当前步骤：logger.info("保存表信息和字段信息到 Meta MySQL")
            # 对字段信息建立向量索引
            await self._save_column_info_to_qdrant(column_infos)  # 等待异步操作完成并取得结果：self._save_column_info_to_qdrant(column_infos)
            logger.info("为字段信息建立向量索引")  # 调用 info 执行当前步骤：logger.info("为字段信息建立向量索引")
            # 对指定的维度字段取值建立全文索引
            await self._save_value_info_to_es(meta_config, column_infos)  # 等待异步操作完成并取得结果：self._save_value_info_to_es(meta_config, column_infos)
            logger.info("为字段取值建立全文索引")  # 调用 info 执行当前步骤：logger.info("为字段取值建立全文索引")

        # 根据配置文件同步指定的指标信息
        if meta_config.metrics:  # 判断分支条件：if meta_config.metrics:
            # 将指标信息和字段依赖关系保存到 Meta MySQL
            metric_infos = await self._save_metrics_to_meta_db(meta_config)  # 等待 _save_metrics_to_meta_db 完成，并将其结果保存到 metric_infos
            logger.info("保存指标信息到数据库成功")  # 调用 info 执行当前步骤：logger.info("保存指标信息到数据库成功")

            # 对指标信息建立向量索引
            await self._save_metrics_to_qdrant(metric_infos)  # 等待异步操作完成并取得结果：self._save_metrics_to_qdrant(metric_infos)
            logger.info("为指标信息建立向量索引成功")  # 调用 info 执行当前步骤：logger.info("为指标信息建立向量索引成功")
