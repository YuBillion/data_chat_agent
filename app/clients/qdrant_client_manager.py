"""
Qdrant 客户端管理器

统一创建和管理 Qdrant 异步客户端
主要用于保存字段和指标的向量索引，支撑后续问数流程中的语义召回
"""

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import random  # 导入random，建立本模块需要的外部能力引用
from typing import Optional  # 从 typing 导入 Optional，供本模块后续代码使用

from qdrant_client import AsyncQdrantClient, models  # 从 qdrant_client 导入 AsyncQdrantClient, models，供本模块后续代码使用

from app.conf.app_config import QdrantConfig, app_config  # 从 app.conf.app_config 导入 QdrantConfig, app_config，供本模块后续代码使用


class QdrantClientManager:  # 定义类 QdrantClientManager，组织相关状态与行为
    """管理 Qdrant 客户端的初始化与关闭"""

    def __init__(self, qdrant_config: QdrantConfig):  # 定义函数 __init__，封装该模块的一项明确职责
        # 保存配置对象，后面初始化客户端时要从这里读取 host 和 port
        self.qdrant_config = qdrant_config  # 将依赖或状态 qdrant_config 保存到实例属性 self.qdrant_config
        # 先把 client 声明出来，真正初始化放到 init() 中进行
        self.client: Optional[AsyncQdrantClient] = None  # 将依赖或状态 None 保存到实例属性 self.client: Optional[AsyncQdrantClient]

    def _get_url(self) -> str:  # 定义函数 _get_url，封装该模块的一项明确职责
        """拼接 Qdrant 服务地址"""
        return f"http://{self.qdrant_config.host}:{self.qdrant_config.port}"  # 返回 f"http://{self.qdrant_config.host}:{self.qdrant_config.port}" 给调用方

    def init(self):  # 定义函数 init，封装该模块的一项明确职责
        """
        显式初始化 Qdrant 客户端
        这里不在 __init__ 中直接初始化，是为了和项目的生命周期管理保持一致
        """
        self.client = AsyncQdrantClient(url=self._get_url())  # 将依赖或状态 AsyncQdrantClient(url=self._get_url()) 保存到实例属性 self.client

    async def close(self):  # 定义异步函数 close，封装可被事件循环调度的协程逻辑
        """关闭 Qdrant 客户端连接"""
        await self.client.close()  # 等待异步操作完成并取得结果：self.client.close()


# 创建一个全局的管理器对象
# 后续项目中的其他模块都通过它来获取同一套 Qdrant 客户端
qdrant_client_manager = QdrantClientManager(app_config.qdrant)  # 计算 QdrantClientManager(app_config.qdrant) 并保存到变量 qdrant_client_manager


if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    # 先初始化客户端，后面的测试逻辑才能真正访问 Qdrant
    qdrant_client_manager.init()  # 调用 init 执行当前步骤：qdrant_client_manager.init()

    async def test():  # 定义异步函数 test，封装可被事件循环调度的协程逻辑
        """执行一次集合创建、写入和查询，验证 Qdrant 接入链路"""
        client = qdrant_client_manager.client  # 计算 qdrant_client_manager.client 并保存到变量 client
        # 如果集合不存在，就先创建一个集合
        if not await client.collection_exists("my_collection"):  # 判断分支条件：if not await client.collection_exists("my_collection"):
            await client.create_collection(  # 等待异步操作完成并取得结果：client.create_collection(
                collection_name="my_collection",  # 为 client.create_collection 设置关键字参数 collection_name，传入当前行给出的值
                vectors_config=models.VectorParams(  # 为 models.VectorParams 设置关键字参数 vectors_config，传入当前行给出的值
                    # 当前集合中的向量维度是 10
                    size=10,  # 为 models.VectorParams 设置关键字参数 size，传入当前行给出的值
                    # 使用余弦相似度作为距离计算方式
                    distance=models.Distance.COSINE,  # 为 models.VectorParams 设置关键字参数 distance，传入当前行给出的值
                ),  # 结束函数 test 的参数及返回类型声明并开始函数体
            )  # 结束函数 test 的参数及返回类型声明并开始函数体

        # 向集合中写入 100 个随机 point
        # 每个 point 都有一个 id 和一个 10 维向量
        await client.upsert(  # 等待异步操作完成并取得结果：client.upsert(
            collection_name="my_collection",  # 为 client.upsert 设置关键字参数 collection_name，传入当前行给出的值
            points=[  # 为 client.upsert 设置关键字参数 points，传入当前行给出的值
                models.PointStruct(  # 调用 PointStruct 执行当前步骤：models.PointStruct(
                    id=i,  # 为 models.PointStruct 设置关键字参数 id，传入当前行给出的值
                    vector=[random.random() for _ in range(10)],  # 为 random.random 设置关键字参数 vector，传入当前行给出的值
                )  # 结束函数 test 的参数及返回类型声明并开始函数体
                for i in range(100)  # 按迭代条件执行循环：for i in range(100)
            ],  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束函数 test 的参数及返回类型声明并开始函数体

        # 用一个随机生成的查询向量做相似度检索
        # limit=10 表示最多返回 10 条结果
        # score_threshold=0.8 表示只保留分数不低于 0.8 的结果
        res = await client.query_points(  # 等待 query_points 完成，并将其结果保存到 res
            collection_name="my_collection",  # 为 client.query_points 设置关键字参数 collection_name，传入当前行给出的值
            query=[random.random() for _ in range(10)],  # type: ignore
            limit=10,  # 为 client.query_points 设置关键字参数 limit，传入当前行给出的值
            score_threshold=0.8,  # 为 client.query_points 设置关键字参数 score_threshold，传入当前行给出的值
        )  # 结束函数 test 的参数及返回类型声明并开始函数体

        print(res)  # 调用 print 执行当前步骤：print(res)

    asyncio.run(test())  # 调用 run 执行当前步骤：asyncio.run(test())
