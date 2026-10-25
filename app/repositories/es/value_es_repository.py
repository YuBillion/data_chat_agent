"""
字段取值 ES 仓储

把字段真实取值组织成 Elasticsearch 全文索引，并提供索引创建 批量写入和关键词检索能力

Service 层负责决定哪些字段需要同步
Repository 只关心索引是否存在 ValueInfo 如何写进 ES 以及如何按关键词召回
"""

from dataclasses import asdict  # 从 dataclasses 导入 asdict，供本模块后续代码使用

from elasticsearch import AsyncElasticsearch  # 从 elasticsearch 导入 AsyncElasticsearch，供本模块后续代码使用

from app.entities.value_info import ValueInfo  # 从 app.entities.value_info 导入 ValueInfo，供本模块后续代码使用


class ValueESRepository:  # 定义类 ValueESRepository，组织相关状态与行为
    """负责字段取值全文索引的创建 写入和基础检索"""

    index_name = "value_index"  # 计算 "value_index" 并保存到变量 index_name
    # value 字段使用 IK 分词，这样地区 会员等级 品类等中文值才能按全文方式检索
    index_mappings = {  # 计算 { 并保存到变量 index_mappings
        "dynamic": False,  # 为多行字典定义键 "dynamic" 及其对应值
        "properties": {  # 为多行字典定义键 "properties" 及其对应值
            "id": {"type": "keyword"},  # 为多行字典定义键 "id" 及其对应值
            "value": {  # 为多行字典定义键 "value" 及其对应值
                "type": "text",  # 为多行字典定义键 "type" 及其对应值
                "analyzer": "ik_max_word",  # 为多行字典定义键 "analyzer" 及其对应值
                "search_analyzer": "ik_max_word",  # 为多行字典定义键 "search_analyzer" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
            "column_id": {"type": "keyword"},  # 为多行字典定义键 "column_id" 及其对应值
        },  # 结束上一处多行结构，保持表达式边界清晰
    }  # 结束上一处多行结构，保持表达式边界清晰

    def __init__(self, client: AsyncElasticsearch):  # 定义函数 __init__，封装该模块的一项明确职责
        self.client = client  # 将 client 保存到实例属性 self.client

    async def ensure_index(self):  # 定义异步函数 ensure_index，封装可被事件循环调度的协程逻辑
        """确保字段取值索引已经创建好"""
        if not await self.client.indices.exists(index=self.index_name):  # 判断分支条件：if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(  # 等待异步操作完成并取得结果：self.client.indices.create(
                index=self.index_name, mappings=self.index_mappings  # 为 self.client.indices.create 设置关键字参数 index，传入当前行给出的值
            )  # 结束 self.client.indices.create 调用参数，得到完整表达式结果

    async def index(self, value_infos: list[ValueInfo], batch_size=20):  # 定义异步函数 index，封装可被事件循环调度的协程逻辑
        """分批写入字段取值，避免一次 bulk 过大"""
        if not value_infos:  # 判断分支条件：if not value_infos:
            return  # 提前返回空结果，结束当前函数调用

        for i in range(0, len(value_infos), batch_size):  # 按迭代条件执行循环：for i in range(0, len(value_infos), batch_size):
            batch_value_infos = value_infos[i : i + batch_size]  # 计算 value_infos[i : i + batch_size] 并保存到变量 batch_value_infos
            batch_operations = []  # 计算 [] 并保存到变量 batch_operations
            for value_info in batch_value_infos:  # 按迭代条件执行循环：for value_info in batch_value_infos:
                # 用 ValueInfo.id 作为文档 id，这样重复构建时会覆盖同一条值记录
                batch_operations.append(  # 调用 append 执行当前步骤：batch_operations.append(
                    {"index": {"_index": self.index_name, "_id": value_info.id}}  # 在函数 index 中执行表达式 {"index": {"_index": self.index_name, "_id": value_info.id}}，推进当前业务流程
                )  # 结束 batch_operations.append 调用参数，得到完整表达式结果
                batch_operations.append(asdict(value_info))  # 调用 append 执行当前步骤：batch_operations.append(asdict(value_info))
            await self.client.bulk(operations=batch_operations)  # 等待异步操作完成并取得结果：self.client.bulk(operations=batch_operations)

    async def search(  # 定义异步函数 search，封装可被事件循环调度的协程逻辑
        self, keyword: str, score_threshold: float = 0.6, limit: int = 20  # 为函数 search 声明参数 self, keyword 及其类型或默认值
    ) -> list[ValueInfo]:  # 结束 search 的参数列表并声明返回类型
        """按关键词全文检索字段取值，并还原为 ValueInfo 实体"""

        resp = await self.client.search(  # 等待 search 完成，并将其结果保存到 resp
            index=self.index_name,  # 为 self.client.search 设置关键字参数 index，传入当前行给出的值
            # value 字段启用了 IK 分词，match 查询可以处理中文短语和枚举值匹配
            query={"match": {"value": keyword}},  # 为 self.client.search 设置关键字参数 query，传入当前行给出的值
            size=limit,  # 为 self.client.search 设置关键字参数 size，传入当前行给出的值
            # 过滤掉相关度过低的命中，避免把明显无关的取值带入后续上下文
            min_score=score_threshold,  # 为 self.client.search 设置关键字参数 min_score，传入当前行给出的值
        )  # 结束 self.client.search 调用参数，得到完整表达式结果
        # ES 文档 _source 中保存的是 ValueInfo 的字段结构，业务层继续使用实体对象
        return [ValueInfo(**hit["_source"]) for hit in resp["hits"]["hits"]]  # 返回 [ValueInfo(**hit["_source"]) for hit in resp["hits"]["hits"]] 给调用方
