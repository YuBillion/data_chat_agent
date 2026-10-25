"""
MySQL 客户端管理器

统一创建和管理项目中的异步 MySQL 客户端，当前项目会同时连接两套 MySQL
一套是保存结构化元数据的 meta 数据库，一套是模拟教学数仓的 dw 数据库
模块对外提供可复用的客户端管理器和 session 工厂
方便脚本入口 服务层和仓储层按统一方式访问数据库
"""

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用

from sqlalchemy import URL, text  # 从 sqlalchemy 导入 URL, text，供本模块后续代码使用
from sqlalchemy.ext.asyncio import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    AsyncEngine,  # 从当前 import 模块导入符号 AsyncEngine
    async_sessionmaker,  # 从当前 import 模块导入符号 async_sessionmaker
    create_async_engine,  # 从当前 import 模块导入符号 create_async_engine
)  # 结束多符号导入列表

from app.conf.app_config import DBConfig, app_config  # 从 app.conf.app_config 导入 DBConfig, app_config，供本模块后续代码使用


class MySQLClientManager:  # 定义类 MySQLClientManager，组织相关状态与行为
    """管理 MySQL Engine 和 Session 工厂"""

    def __init__(self, config: DBConfig):  # 定义函数 __init__，封装该模块的一项明确职责
        # Engine 是数据库连接层核心对象，底层会维护连接池
        self.engine: AsyncEngine | None = None  # 将依赖或状态 None 保存到实例属性 self.engine: AsyncEngine | None
        # session_factory 用来按需创建新的 AsyncSession
        self.session_factory = None  # 将依赖或状态 None 保存到实例属性 self.session_factory
        # 保存数据库配置，后面拼接连接地址要用
        self.config = config  # 将依赖或状态 config 保存到实例属性 self.config

    def _get_url(self) -> URL:  # 定义函数 _get_url，封装该模块的一项明确职责
        """Build a credential-safe SQLAlchemy URL."""

        return URL.create(  # 返回 URL.create( 给调用方
            drivername="mysql+asyncmy",  # 为 URL.create 设置关键字参数 drivername，传入当前行给出的值
            username=self.config.user,  # 为 URL.create 设置关键字参数 username，传入当前行给出的值
            password=self.config.password,  # 为 URL.create 设置关键字参数 password，传入当前行给出的值
            host=self.config.host,  # 为 URL.create 设置关键字参数 host，传入当前行给出的值
            port=self.config.port,  # 为 URL.create 设置关键字参数 port，传入当前行给出的值
            database=self.config.database,  # 为 URL.create 设置关键字参数 database，传入当前行给出的值
            query={"charset": "utf8mb4"},  # 为 URL.create 设置关键字参数 query，传入当前行给出的值
        )  # 结束函数 _get_url 的参数及返回类型声明并开始函数体

    def init(self):  # 定义函数 init，封装该模块的一项明确职责
        """初始化 Engine 和 Session 工厂"""
        # 创建异步 Engine，相当于先把“数据库连接能力”准备好
        self.engine = create_async_engine(  # 将依赖或状态 create_async_engine( 保存到实例属性 self.engine
            self._get_url(),  # 继续向上一处调用或声明传入 self._get_url()
            pool_size=self.config.pool_size,  # 为 create_async_engine 设置关键字参数 pool_size，传入当前行给出的值
            max_overflow=10,  # 为 create_async_engine 设置关键字参数 max_overflow，传入当前行给出的值
            pool_timeout=10,  # 为 create_async_engine 设置关键字参数 pool_timeout，传入当前行给出的值
            pool_recycle=1800,  # 为 create_async_engine 设置关键字参数 pool_recycle，传入当前行给出的值
            pool_pre_ping=True,  # 为 create_async_engine 设置关键字参数 pool_pre_ping，传入当前行给出的值
            connect_args={"connect_timeout": 10},  # 为 create_async_engine 设置关键字参数 connect_args，传入当前行给出的值
        )  # 结束函数 init 的参数及返回类型声明并开始函数体
        # 基于 Engine 创建 Session 工厂，后面真正查库时再拿 session
        self.session_factory = async_sessionmaker(  # 将依赖或状态 async_sessionmaker( 保存到实例属性 self.session_factory
            self.engine, autoflush=True, expire_on_commit=False  # 在函数 init 中执行表达式 self.engine, autoflush=True, expire_on_commit=False，推进当前业务流程
        )  # 结束函数 init 的参数及返回类型声明并开始函数体

    async def close(self):  # 定义异步函数 close，封装可被事件循环调度的协程逻辑
        """释放连接池资源"""
        await self.engine.dispose()  # 等待异步操作完成并取得结果：self.engine.dispose()


# 一套连元数据库，一套连数仓模拟库
# 后续由不同 repository 按职责分别使用
meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)  # 计算 MySQLClientManager(app_config.db_meta) 并保存到变量 meta_mysql_client_manager
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)  # 计算 MySQLClientManager(app_config.db_dw) 并保存到变量 dw_mysql_client_manager

if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    dw_mysql_client_manager.init()  # 调用 init 执行当前步骤：dw_mysql_client_manager.init()

    async def test():  # 定义异步函数 test，封装可被事件循环调度的协程逻辑
        """执行一次简单查询，验证 MySQL 连接与结果结构"""
        async with dw_mysql_client_manager.session_factory() as session:  # 进入受管理的上下文 async with dw_mysql_client_manager.session_factory() as session:，确保资源正确获取与释放
            sql = "select * from fact_order limit 10"  # 计算 "select * from fact_order limit 10" 并保存到变量 sql
            result = await session.execute(text(sql))  # 等待 execute 完成，并将其结果保存到 result
            # mappings().fetchall() 会把结果转成“按列名访问”的行对象列表
            rows = result.mappings().fetchall()  # 计算 result.mappings().fetchall() 并保存到变量 rows
            print(type(rows))  # 调用 print 执行当前步骤：print(type(rows))
            print(type(rows[0]))  # 调用 print 执行当前步骤：print(type(rows[0]))
            print(rows[0]["order_id"])  # 调用 print 执行当前步骤：print(rows[0]["order_id"])

    asyncio.run(test())  # 调用 run 执行当前步骤：asyncio.run(test())
