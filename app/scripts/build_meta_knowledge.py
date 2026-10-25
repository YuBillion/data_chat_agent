"""
元数据知识库构建脚本入口

相当于构建流程的 controller 层，负责接收命令行参数 初始化客户端 创建仓储和服务对象
再把真正的构建任务调度到 MetaKnowledgeService，它本身不承载复杂业务细节
主要目标是把整条构建链路稳定地启动起来
"""

import argparse  # 导入argparse，建立本模块需要的外部能力引用
import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from pathlib import Path  # 从 pathlib 导入 Path，供本模块后续代码使用

from app.clients.embedding_client_manager import embedding_client_manager  # 从 app.clients.embedding_client_manager 导入 embedding_client_manager，供本模块后续代码使用
from app.clients.es_client_manager import es_client_manager  # 从 app.clients.es_client_manager 导入 es_client_manager，供本模块后续代码使用
from app.clients.mysql_client_manager import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    dw_mysql_client_manager,  # 从当前 import 模块导入符号 dw_mysql_client_manager
    meta_mysql_client_manager,  # 从当前 import 模块导入符号 meta_mysql_client_manager
)  # 结束多符号导入列表
from app.clients.qdrant_client_manager import qdrant_client_manager  # 从 app.clients.qdrant_client_manager 导入 qdrant_client_manager，供本模块后续代码使用
from app.repositories.es.value_es_repository import ValueESRepository  # 从 app.repositories.es.value_es_repository 导入 ValueESRepository，供本模块后续代码使用
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository  # 从 app.repositories.mysql.dw.dw_mysql_repository 导入 DWMySQLRepository，供本模块后续代码使用
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository  # 从 app.repositories.mysql.meta.meta_mysql_repository 导入 MetaMySQLRepository，供本模块后续代码使用
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository  # 从 app.repositories.qdrant.column_qdrant_repository 导入 ColumnQdrantRepository，供本模块后续代码使用
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository  # 从 app.repositories.qdrant.metric_qdrant_repository 导入 MetricQdrantRepository，供本模块后续代码使用
from app.services.meta_knowledge_service import MetaKnowledgeService  # 从 app.services.meta_knowledge_service 导入 MetaKnowledgeService，供本模块后续代码使用


async def build(config_path: Path):  # 定义异步函数 build，封装可被事件循环调度的协程逻辑
    """初始化依赖并执行一次元数据知识构建"""

    # 初始化元数据MySQL客户端
    meta_mysql_client_manager.init()  # 调用 init 执行当前步骤：meta_mysql_client_manager.init()
    # 初始化数据仓库MySQL客户端
    dw_mysql_client_manager.init()  # 调用 init 执行当前步骤：dw_mysql_client_manager.init()
    # 初始化Qdrant客户端
    qdrant_client_manager.init()  # 调用 init 执行当前步骤：qdrant_client_manager.init()
    # 初始化Embedding客户端
    embedding_client_manager.init()  # 调用 init 执行当前步骤：embedding_client_manager.init()
    # 初始化Elasticsearch客户端
    es_client_manager.init()  # 调用 init 执行当前步骤：es_client_manager.init()

    async with (  # 进入受管理的上下文 async with (，确保资源正确获取与释放
        meta_mysql_client_manager.session_factory() as meta_session,  # 继续向上一处调用或声明传入 meta_mysql_client_manager.session_factory() as meta_session
        dw_mysql_client_manager.session_factory() as dw_session,  # 继续向上一处调用或声明传入 dw_mysql_client_manager.session_factory() as dw_session
    ):  # 结束 build 的参数列表并声明返回类型
        # 创建 repository 对象
        meta_mysql_repository = MetaMySQLRepository(meta_session)  # 计算 MetaMySQLRepository(meta_session) 并保存到变量 meta_mysql_repository
        dw_mysql_repository = DWMySQLRepository(dw_session)  # 计算 DWMySQLRepository(dw_session) 并保存到变量 dw_mysql_repository
        # 字段和指标分别写入不同的 Qdrant collection，后续可以独立召回
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)  # 计算 ColumnQdrantRepository(qdrant_client_manager.client) 并保存到变量 column_qdrant_repository
        embedding_client = embedding_client_manager.client  # 计算 embedding_client_manager.client 并保存到变量 embedding_client
        value_es_repository = ValueESRepository(es_client_manager.client)  # 计算 ValueESRepository(es_client_manager.client) 并保存到变量 value_es_repository
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)  # 计算 MetricQdrantRepository(qdrant_client_manager.client) 并保存到变量 metric_qdrant_repository

        # 创建 service 对象，并把 repository 注入进去
        meta_knowledge_service = MetaKnowledgeService(  # 调用 MetaKnowledgeService 构造结果并保存到 meta_knowledge_service
            meta_mysql_repository=meta_mysql_repository,  # 为 MetaKnowledgeService 设置关键字参数 meta_mysql_repository，传入当前行给出的值
            dw_mysql_repository=dw_mysql_repository,  # 为 MetaKnowledgeService 设置关键字参数 dw_mysql_repository，传入当前行给出的值
            column_qdrant_repository=column_qdrant_repository,  # 为 MetaKnowledgeService 设置关键字参数 column_qdrant_repository，传入当前行给出的值
            embedding_client=embedding_client,  # 为 MetaKnowledgeService 设置关键字参数 embedding_client，传入当前行给出的值
            value_es_repository=value_es_repository,  # 为 MetaKnowledgeService 设置关键字参数 value_es_repository，传入当前行给出的值
            metric_qdrant_repository=metric_qdrant_repository,  # 为 MetaKnowledgeService 设置关键字参数 metric_qdrant_repository，传入当前行给出的值
        )  # 结束 MetaKnowledgeService 调用参数，得到完整表达式结果

        # 真正进入服务层的构建逻辑
        await meta_knowledge_service.build(config_path)  # 等待异步操作完成并取得结果：meta_knowledge_service.build(config_path)

    # 结束后关闭客户端连接
    await meta_mysql_client_manager.close()  # 等待异步操作完成并取得结果：meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()  # 等待异步操作完成并取得结果：dw_mysql_client_manager.close()
    await qdrant_client_manager.close()  # 等待异步操作完成并取得结果：qdrant_client_manager.close()
    await es_client_manager.close()  # 等待异步操作完成并取得结果：es_client_manager.close()


if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    # 解析命令行参数，由外部决定本次构建使用哪份配置文件
    parser = argparse.ArgumentParser()  # 计算 argparse.ArgumentParser() 并保存到变量 parser
    parser.add_argument("-c", "--conf", required=True)  # 调用 add_argument 执行当前步骤：parser.add_argument("-c", "--conf", required=True)
    args = parser.parse_args()  # 计算 parser.parse_args() 并保存到变量 args

    # 将字符串路径转成 Path，再启动异步 build
    asyncio.run(build(Path(args.conf)))  # 调用 run 执行当前步骤：asyncio.run(build(Path(args.conf)))
