"""
字段向量仓储

管理字段向量集合并把已经准备好的 point 批量写入 Qdrant

Service 层负责决定一个字段要拆成哪些 point
Repository 只关心集合存在和向量点如何稳定落库
"""

from qdrant_client import AsyncQdrantClient  # 从 qdrant_client 导入 AsyncQdrantClient，供本模块后续代码使用
from qdrant_client.http.models import PointStruct  # 从 qdrant_client.http.models 导入 PointStruct，供本模块后续代码使用
from qdrant_client.models import Distance, VectorParams  # 从 qdrant_client.models 导入 Distance, VectorParams，供本模块后续代码使用

from app.conf.app_config import app_config  # 从 app.conf.app_config 导入 app_config，供本模块后续代码使用
from app.entities.column_info import ColumnInfo  # 从 app.entities.column_info 导入 ColumnInfo，供本模块后续代码使用


class ColumnQdrantRepository:  # 定义类 ColumnQdrantRepository，组织相关状态与行为
    """负责字段向量集合的创建 写入和基础检索"""

    collection_name = "column_info_collection"  # 计算 "column_info_collection" 并保存到变量 collection_name

    def __init__(self, client: AsyncQdrantClient):  # 定义函数 __init__，封装该模块的一项明确职责
        self.client = client  # 将 client 保存到实例属性 self.client

    async def ensure_collection(self):  # 定义异步函数 ensure_collection，封装可被事件循环调度的协程逻辑
        """确保字段向量集合存在，并按配置中的维度初始化"""
        if not await self.client.collection_exists(self.collection_name):  # 判断分支条件：if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(  # 等待异步操作完成并取得结果：self.client.create_collection(
                collection_name=self.collection_name,  # 为 self.client.create_collection 设置关键字参数 collection_name，传入当前行给出的值
                vectors_config=VectorParams(  # 为 VectorParams 设置关键字参数 vectors_config，传入当前行给出的值
                    size=app_config.qdrant.embedding_size, distance=Distance.COSINE  # 为 VectorParams 设置关键字参数 size，传入当前行给出的值
                ),  # 结束 VectorParams 调用参数，得到完整表达式结果
            )  # 结束 self.client.create_collection 调用参数，得到完整表达式结果

    async def upsert(  # 定义异步函数 upsert，封装可被事件循环调度的协程逻辑
        self,  # 为函数 upsert 声明参数 self 及其类型或默认值
        ids: list[str],  # 为函数 upsert 声明参数 ids 及其类型或默认值
        embeddings: list[list[float]],  # 为函数 upsert 声明参数 embeddings 及其类型或默认值
        payloads: list[dict],  # 为函数 upsert 声明参数 payloads 及其类型或默认值
        batch_size: int = 10,  # 为函数 upsert 声明参数 batch_size 及其类型或默认值
    ):  # 结束 upsert 的参数列表并声明返回类型
        """分批 upsert 字段向量点，避免一次提交过多 point"""
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
    ) -> list[ColumnInfo]:  # 结束 search 的参数列表并声明返回类型
        """按向量相似度检索字段元数据，并还原为 ColumnInfo 实体"""
        result = await self.client.query_points(  # 等待 query_points 完成，并将其结果保存到 result
            collection_name=self.collection_name,  # 为 self.client.query_points 设置关键字参数 collection_name，传入当前行给出的值
            query=embedding,  # 为 self.client.query_points 设置关键字参数 query，传入当前行给出的值
            limit=limit,  # 为 self.client.query_points 设置关键字参数 limit，传入当前行给出的值
            score_threshold=score_threshold,  # 为 self.client.query_points 设置关键字参数 score_threshold，传入当前行给出的值
        )  # 结束 self.client.query_points 调用参数，得到完整表达式结果
        # Qdrant 只保存字段元数据 payload，业务层继续使用 ColumnInfo
        return [ColumnInfo(**point.payload) for point in result.points]  # 返回 [ColumnInfo(**point.payload) for point in result.points] 给调用方
