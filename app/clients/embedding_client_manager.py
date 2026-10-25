"""
Embedding 客户端管理器

负责按配置初始化 Embedding 服务客户端，并为字段、指标和用户问题的向量化
提供统一访问入口
"""

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from typing import Optional  # 从 typing 导入 Optional，供本模块后续代码使用

from huggingface_hub import AsyncInferenceClient, InferenceClient  # 从 huggingface_hub 导入 AsyncInferenceClient, InferenceClient，供本模块后续代码使用
from langchain_huggingface import HuggingFaceEndpointEmbeddings  # 从 langchain_huggingface 导入 HuggingFaceEndpointEmbeddings，供本模块后续代码使用

from app.conf.app_config import EmbeddingConfig, app_config  # 从 app.conf.app_config 导入 EmbeddingConfig, app_config，供本模块后续代码使用


class EmbeddingClientManager:  # 定义类 EmbeddingClientManager，组织相关状态与行为
    """管理 Embedding 服务客户端的初始化与复用"""

    def __init__(self, config: EmbeddingConfig):  # 定义函数 __init__，封装该模块的一项明确职责
        self.client: Optional[HuggingFaceEndpointEmbeddings] = None  # 将依赖或状态 None 保存到实例属性 self.client: Optional[HuggingFaceEndpointEmbeddings]
        self.config = config  # 将依赖或状态 config 保存到实例属性 self.config

    def _get_url(self) -> str:  # 定义函数 _get_url，封装该模块的一项明确职责
        """拼接 Embedding 服务地址"""
        return f"http://{self.config.host}:{self.config.port}"  # 返回 f"http://{self.config.host}:{self.config.port}" 给调用方

    def init(self):  # 定义函数 init，封装该模块的一项明确职责
        """显式初始化客户端，避免模块导入时立即建立外部连接"""
        # LangChain 的 model 参数使用模型 ID，本地 TEI 地址交给底层推理客户端。
        self.client = HuggingFaceEndpointEmbeddings(model=self.config.model)  # 将依赖或状态 HuggingFaceEndpointEmbeddings(model=self.config.model) 保存到实例属性 self.client
        endpoint_url = f"{self._get_url()}/embed"  # 计算 f"{self._get_url()}/embed" 并保存到变量 endpoint_url
        self.client.client = InferenceClient(model=endpoint_url)  # 将依赖或状态 InferenceClient(model=endpoint_url) 保存到实例属性 self.client.client
        self.client.async_client = AsyncInferenceClient(model=endpoint_url)  # 将依赖或状态 AsyncInferenceClient(model=endpoint_url) 保存到实例属性 self.client.async_client


# 模块级单例，供整个项目复用同一套 Embedding 客户端管理器
embedding_client_manager = EmbeddingClientManager(app_config.embedding)  # 计算 EmbeddingClientManager(app_config.embedding) 并保存到变量 embedding_client_manager


if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    embedding_client_manager.init()  # 调用 init 执行当前步骤：embedding_client_manager.init()
    client = embedding_client_manager.client  # 计算 embedding_client_manager.client 并保存到变量 client

    async def test():  # 定义异步函数 test，封装可被事件循环调度的协程逻辑
        """执行一次最小化向量化调用，验证服务是否可用"""
        text = "What is deep learning?"  # 计算 "What is deep learning?" 并保存到变量 text
        query_result = await client.aembed_query(text)  # 等待 aembed_query 完成，并将其结果保存到 query_result
        print(query_result[:3])  # 调用 print 执行当前步骤：print(query_result[:3])

    asyncio.run(test())  # 调用 run 执行当前步骤：asyncio.run(test())
