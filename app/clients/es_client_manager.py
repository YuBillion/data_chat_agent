"""
Elasticsearch 客户端管理器

统一创建和管理 Elasticsearch 异步客户端，
主要服务于字段真实取值的全文索引构建和检索
"""

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from typing import Optional  # 从 typing 导入 Optional，供本模块后续代码使用

from elasticsearch import AsyncElasticsearch  # 从 elasticsearch 导入 AsyncElasticsearch，供本模块后续代码使用

from app.conf.app_config import ESConfig, app_config  # 从 app.conf.app_config 导入 ESConfig, app_config，供本模块后续代码使用


class ESClientManager:  # 定义类 ESClientManager，组织相关状态与行为
    """管理 Elasticsearch 客户端的生命周期"""

    def __init__(self, es_config: ESConfig):  # 定义函数 __init__，封装该模块的一项明确职责
        # 保存 ES 配置对象，后面初始化客户端时会从这里读取 host 和 port
        self.es_config = es_config  # 将依赖或状态 es_config 保存到实例属性 self.es_config
        # 先把 client 声明出来，真正初始化放到 init() 中进行
        self.client: Optional[AsyncElasticsearch] = None  # 将依赖或状态 None 保存到实例属性 self.client: Optional[AsyncElasticsearch]

    def _get_url(self) -> str:  # 定义函数 _get_url，封装该模块的一项明确职责
        """拼接 Elasticsearch 服务地址"""
        return f"http://{self.es_config.host}:{self.es_config.port}"  # 返回 f"http://{self.es_config.host}:{self.es_config.port}" 给调用方

    def init(self):  # 定义函数 init，封装该模块的一项明确职责
        """
        初始化异步 Elasticsearch 客户端
        hosts 之所以是列表，是为了兼容 ES 常见的集群连接方式
        """
        self.client = AsyncElasticsearch(hosts=[self._get_url()])  # 将依赖或状态 AsyncElasticsearch(hosts=[self._get_url()]) 保存到实例属性 self.client

    async def close(self):  # 定义异步函数 close，封装可被事件循环调度的协程逻辑
        """关闭客户端连接"""
        await self.client.close()  # 等待异步操作完成并取得结果：self.client.close()


# 创建一个全局可复用的 ES 客户端管理器对象
es_client_manager = ESClientManager(app_config.es)  # 计算 ESClientManager(app_config.es) 并保存到变量 es_client_manager

if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    es_client_manager.init()  # 调用 init 执行当前步骤：es_client_manager.init()

    async def test():  # 定义异步函数 test，封装可被事件循环调度的协程逻辑
        """执行一次索引创建、写入与查询，验证 ES 接入链路"""
        client = es_client_manager.client  # 计算 es_client_manager.client 并保存到变量 client

        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            # 创建索引（已存在则跳过，避免重复执行脚本时报 resource_already_exists）
            # 这里同时显式定义了字段结构
            # dynamic=False 表示关闭动态映射，要求写入数据必须符合当前定义
            if not await client.indices.exists(index="my-books"):  # 判断分支条件：if not await client.indices.exists(index="my-books"):
                await client.indices.create(  # 等待异步操作完成并取得结果：client.indices.create(
                    index="my-books",  # 为 client.indices.create 设置关键字参数 index，传入当前行给出的值
                    mappings={  # 为 client.indices.create 设置关键字参数 mappings，传入当前行给出的值
                        "dynamic": False,  # 为多行字典定义键 "dynamic" 及其对应值
                        "properties": {  # 为多行字典定义键 "properties" 及其对应值
                            "name": {"type": "text"},  # 为多行字典定义键 "name" 及其对应值
                            "author": {"type": "text"},  # 为多行字典定义键 "author" 及其对应值
                            "release_date": {"type": "date", "format": "yyyy-MM-dd"},  # 为多行字典定义键 "release_date" 及其对应值
                            "page_count": {"type": "integer"},  # 为多行字典定义键 "page_count" 及其对应值
                        },  # 结束上一处多行结构，保持表达式边界清晰
                    },  # 结束上一处多行结构，保持表达式边界清晰
                )  # 结束函数 test 的参数及返回类型声明并开始函数体
            # 插入数据
            # bulk 采用“操作说明 + 数据本体”交替出现的格式
            # 适合一次性写入多条文档
            await client.bulk(  # 等待异步操作完成并取得结果：client.bulk(
                operations=[  # 为 client.bulk 设置关键字参数 operations，传入当前行给出的值
                    {"index": {"_index": "my-books"}},  # 向多行字典加入配置项 {"index": {"_index": "my-books"}}
                    {  # 在函数 test 中执行表达式 {，推进当前业务流程
                        "name": "Revelation Space",  # 为多行字典定义键 "name" 及其对应值
                        "author": "Alastair Reynolds",  # 为多行字典定义键 "author" 及其对应值
                        "release_date": "2000-03-15",  # 为多行字典定义键 "release_date" 及其对应值
                        "page_count": 585,  # 为多行字典定义键 "page_count" 及其对应值
                    },  # 结束上一处多行结构，保持表达式边界清晰
                    {"index": {"_index": "my-books"}},  # 向多行字典加入配置项 {"index": {"_index": "my-books"}}
                    {  # 在函数 test 中执行表达式 {，推进当前业务流程
                        "name": "1984",  # 为多行字典定义键 "name" 及其对应值
                        "author": "George Orwell",  # 为多行字典定义键 "author" 及其对应值
                        "release_date": "1985-06-01",  # 为多行字典定义键 "release_date" 及其对应值
                        "page_count": 328,  # 为多行字典定义键 "page_count" 及其对应值
                    },  # 结束上一处多行结构，保持表达式边界清晰
                    {"index": {"_index": "my-books"}},  # 向多行字典加入配置项 {"index": {"_index": "my-books"}}
                    {  # 在函数 test 中执行表达式 {，推进当前业务流程
                        "name": "Fahrenheit 451",  # 为多行字典定义键 "name" 及其对应值
                        "author": "Ray Bradbury",  # 为多行字典定义键 "author" 及其对应值
                        "release_date": "1953-10-15",  # 为多行字典定义键 "release_date" 及其对应值
                        "page_count": 227,  # 为多行字典定义键 "page_count" 及其对应值
                    },  # 结束上一处多行结构，保持表达式边界清晰
                    {"index": {"_index": "my-books"}},  # 向多行字典加入配置项 {"index": {"_index": "my-books"}}
                    {  # 在函数 test 中执行表达式 {，推进当前业务流程
                        "name": "Brave New World",  # 为多行字典定义键 "name" 及其对应值
                        "author": "Aldous Huxley",  # 为多行字典定义键 "author" 及其对应值
                        "release_date": "1932-06-01",  # 为多行字典定义键 "release_date" 及其对应值
                        "page_count": 268,  # 为多行字典定义键 "page_count" 及其对应值
                    },  # 结束上一处多行结构，保持表达式边界清晰
                    {"index": {"_index": "my-books"}},  # 向多行字典加入配置项 {"index": {"_index": "my-books"}}
                    {  # 在函数 test 中执行表达式 {，推进当前业务流程
                        "name": "The Handmaids Tale",  # 为多行字典定义键 "name" 及其对应值
                        "author": "Margaret Atwood",  # 为多行字典定义键 "author" 及其对应值
                        "release_date": "1985-06-01",  # 为多行字典定义键 "release_date" 及其对应值
                        "page_count": 311,  # 为多行字典定义键 "page_count" 及其对应值
                    },  # 结束上一处多行结构，保持表达式边界清晰
                ],  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束函数 test 的参数及返回类型声明并开始函数体

            resp = await client.search(  # 等待 search 完成，并将其结果保存到 resp
                index="my-books",  # 为 client.search 设置关键字参数 index，传入当前行给出的值
                query={"match": {"name": "brave"}},  # 为 client.search 设置关键字参数 query，传入当前行给出的值
            )  # 结束函数 test 的参数及返回类型声明并开始函数体

            print(resp)  # 调用 print 执行当前步骤：print(resp)
        finally:  # 进入无论成功失败都必须执行的资源清理分支
            # 成功或异常都关闭连接，避免 aiohttp ClientSession 未关闭告警
            await es_client_manager.close()  # 等待异步操作完成并取得结果：es_client_manager.close()

    asyncio.run(test())  # 调用 run 执行当前步骤：asyncio.run(test())
