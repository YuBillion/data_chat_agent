"""
数仓 MySQL 仓储

这一层对应文档里的 DW Repository，职责是到真实数仓中补齐配置文件里
没有显式维护的信息，例如字段类型和字段示例值。受控 SQL 执行由独立
SQL Guard/Read Tool 负责，本仓储不接收模型生成的 SQL。
"""

import re  # 导入re，建立本模块需要的外部能力引用

from sqlalchemy import text  # 从 sqlalchemy 导入 text，供本模块后续代码使用
from sqlalchemy.ext.asyncio import AsyncSession  # 从 sqlalchemy.ext.asyncio 导入 AsyncSession，供本模块后续代码使用


class DWMySQLRepository:  # 定义类 DWMySQLRepository，组织相关状态与行为
    """负责查询数仓真实表结构和字段样例值"""

    def __init__(self, session: AsyncSession):  # 定义函数 __init__，封装该模块的一项明确职责
        self.session = session  # 将 session 保存到实例属性 self.session

    async def get_column_types(self, table_name: str) -> dict[str, str]:  # 定义异步函数 get_column_types，封装可被事件循环调度的协程逻辑
        """查询整张表的字段类型，作为 ColumnInfo.type 的真实来源"""
        table_name = _identifier(table_name)  # 计算 _identifier(table_name) 并保存到变量 table_name
        sql = f"show columns from {table_name}"  # 计算 f"show columns from {table_name}" 并保存到变量 sql
        result = await self.session.execute(text(sql))  # 等待 execute 完成，并将其结果保存到 result
        result_dict = result.mappings().fetchall()  # 计算 result.mappings().fetchall() 并保存到变量 result_dict
        return {row["Field"]: row["Type"] for row in result_dict}  # 返回 {row["Field"]: row["Type"] for row in result_dict} 给调用方

    async def get_column_values(  # 定义异步函数 get_column_values，封装可被事件循环调度的协程逻辑
        self, table_name: str, column_name: str, limit: int = 10  # 为函数 get_column_values 声明参数 self, table_name 及其类型或默认值
    ) -> list:  # 结束 get_column_values 的参数列表并声明返回类型
        """抽样查询字段示例值，供元数据入库和后续检索链路复用"""
        table_name = _identifier(table_name)  # 计算 _identifier(table_name) 并保存到变量 table_name
        column_name = _identifier(column_name)  # 计算 _identifier(column_name) 并保存到变量 column_name
        limit = max(1, min(int(limit), 100_000))  # 计算 max(1, min(int(limit), 100_000)) 并保存到变量 limit
        sql = f"select distinct {column_name} from {table_name} limit {limit}"  # 计算 f"select distinct {column_name} from {table_name} limit {limit}" 并保存到变量 sql
        result = await self.session.execute(text(sql))  # 等待 execute 完成，并将其结果保存到 result
        return [row[0] for row in result.fetchall()]  # 返回 [row[0] for row in result.fetchall()] 给调用方

    async def get_db_info(self):  # 定义异步函数 get_db_info，封装可被事件循环调度的协程逻辑
        """读取当前数仓数据库的方言和版本，供 SQL 生成提示词使用"""

        sql = "select version()"  # 计算 "select version()" 并保存到变量 sql
        result = await self.session.execute(text(sql))  # 等待 execute 完成，并将其结果保存到 result
        version = result.scalar()  # 计算 result.scalar() 并保存到变量 version

        # dialect 来自 SQLAlchemy 当前绑定的数据库方言，例如 mysql
        dialect = (  # 调用 目标函数 构造结果并保存到 dialect
            self.session.bind.dialect.name if self.session.bind is not None else "mysql"  # 在函数 get_db_info 中执行表达式 self.session.bind.dialect.name if self.session.bind is not None else "m…，推进当前业务流程
        )  # 结束函数 get_db_info 的调用或声明结构
        return {"dialect": dialect, "version": version}  # 返回 {"dialect": dialect, "version": version} 给调用方


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")  # 计算 re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$") 并保存到变量 IDENTIFIER


def _identifier(value: str) -> str:  # 定义函数 _identifier，封装该模块的一项明确职责
    if not IDENTIFIER.fullmatch(value):  # 判断分支条件：if not IDENTIFIER.fullmatch(value):
        raise ValueError("database identifier is invalid")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("database identifier is invalid")
    return value  # 返回 value 给调用方

