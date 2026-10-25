"""
指标向量仓储

管理指标向量集合，并把 Service 层准备好的指标 point 批量写入 Qdrant

字段和指标虽然都用向量检索，但它们是两类不同对象
所以指标单独使用 metric_info_collection，避免后续召回时和字段结果混在一起
"""

from qdrant_client import AsyncQdrantClient  # 从 qdrant_client 导入 AsyncQdrantClient，供本模块后续代码使用
from qdrant_client.models import Distance, PointStruct, VectorParams  # 从 qdrant_client.models 导入 Distance, PointStruct, VectorParams，供本模块后续代码使用

from app.conf.app_config import app_config  # 从 app.conf.app_config 导入 app_config，供本模块后续代码使用
from app.entities.metric_info import MetricInfo  # 从 app.entities.metric_info 导入 MetricInfo，供本模块后续代码使用


class MetricQdrantRepository:  # 定义类 MetricQdrantRepository，组织相关状态与行为
    """负责指标向量集合的创建 写入和基础检索"""

    collection_name = "metric_info_collection"  # 计算 "metric_info_collection" 并保存到变量 collection_name

    def __init__(self, client: AsyncQdrantClient):  # 定义函数 __init__，封装该模块的一项明确职责
        self.client = client  # 将 client 保存到实例属性 self.client

    async def ensure_collection(self):  # 定义异步函数 ensure_collection，封装可被事件循环调度的协程逻辑
        """确保指标向量集合存在，并按当前 Embedding 维度初始化"""
        if not await self.client.collection_exists(self.collection_name):  # 判断分支条件：if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(  # 等待异步操作完成并取得结果：self.client.create_collection(
                collection_name=self.collection_name,  # 为 self.client.create_collection 设置关键字参数 collection_name，传入当前行给出的值
                vectors_config=VectorParams(  # 为 VectorParams 设置关键字参数 vectors_config，传入当前行给出的值
                    # 向量维度必须和 Embedding 模型输出一致，否则写入时会失败
                    size=app_config.qdrant.embedding_size,  # 为 VectorParams 设置关键字参数 size，传入当前行给出的值
                    distance=Distance.COSINE,  # 为 VectorParams 设置关键字参数 distance，传入当前行给出的值
                ),  # 结束 VectorParams 调用参数，得到完整表达式结果
            )  # 结束 self.client.create_collection 调用参数，得到完整表达式结果

    async def upsert(  # 定义异步函数 upsert，封装可被事件循环调度的协程逻辑
        self,  # 为函数 upsert 声明参数 self 及其类型或默认值
        ids: list[str],  # 为函数 upsert 声明参数 ids 及其类型或默认值
        embeddings: list[list[float]],  # 为函数 upsert 声明参数 embeddings 及其类型或默认值
        payloads: list[dict],  # 为函数 upsert 声明参数 payloads 及其类型或默认值
        batch_size: int = 10,  # 为函数 upsert 声明参数 batch_size 及其类型或默认值
    ):  # 结束 upsert 的参数列表并声明返回类型
        """分批 upsert 指标向量点，避免一次提交过多 point"""
        # ids embeddings payloads 三个列表按相同下标组成一条完整的 Qdrant point
        points: list[PointStruct] = [  # 计算 [ 并保存到变量 points
            PointStruct(id=id, vector=embedding, payload=payload)  # 调用 PointStruct 执行当前步骤：PointStruct(id=id, vector=embedding, payload=payload)
            for id, embedding, payload in zip(ids, embeddings, payloads)  # 按迭代条件执行循环：for id, embedding, payload in zip(ids, embeddings, payloads)
        ]  # 结束上一处多行结构，保持表达式边界清晰
        for i in range(0, len(points), batch_size):  # 按迭代条件执行循环：for i in range(0, len(points), batch_size):
            await self.client.upsert(  # 等待异步操作完成并取得结果：self.client.upsert(
                collection_name=self.collection_name, points=points[i : i + batch_size]  # 为 self.client.upsert 设置关键字参数 collection_name，传入当前行给出的值
            )  # 结束 self.client.upsert 调用参数，得到完整表达式结果

    async def search(  # 定义异步函数 search，封装可被事件循环调度的协程逻辑
        self, embedding: list[float], score_threshold: float = 0.6, limit: int = 20  # 为函数 search 声明参数 self, embedding 及其类型或默认值
    ) -> list[MetricInfo]:  # 结束 search 的参数列表并声明返回类型
        """按向量相似度检索指标元数据，并还原为 MetricInfo 实体"""

        result = await self.client.query_points(  # 等待 query_points 完成，并将其结果保存到 result
            collection_name=self.collection_name,  # 为 self.client.query_points 设置关键字参数 collection_name，传入当前行给出的值
            query=embedding,  # 为 self.client.query_points 设置关键字参数 query，传入当前行给出的值
            limit=limit,  # 为 self.client.query_points 设置关键字参数 limit，传入当前行给出的值
            score_threshold=score_threshold,  # 为 self.client.query_points 设置关键字参数 score_threshold，传入当前行给出的值
        )  # 结束 self.client.query_points 调用参数，得到完整表达式结果
        # Qdrant point 的 payload 中保存的是指标元数据，业务层继续使用 MetricInfo
        return [MetricInfo(**point.payload) for point in result.points]  # 返回 [MetricInfo(**point.payload) for point in result.points] 给调用方
