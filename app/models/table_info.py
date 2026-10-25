"""
`table_info` ORM 模型

负责定义元数据库中表元数据表的结构，保存纳入知识库的表名、角色和说明
"""

from sqlalchemy import String, Text  # 从 sqlalchemy 导入 String, Text，供本模块后续代码使用
from sqlalchemy.orm import Mapped, mapped_column  # 从 sqlalchemy.orm 导入 Mapped, mapped_column，供本模块后续代码使用

from app.models.base import Base  # 从 app.models.base 导入 Base，供本模块后续代码使用


class TableInfoMySQL(Base):  # 定义类 TableInfoMySQL，组织相关状态与行为
    """表元数据表对应的 ORM 模型"""

    __tablename__ = "table_info"  # 计算 "table_info" 并保存到变量 __tablename__

    # id 直接使用表名
    # 它既是主键 也是后续字段归属关系里的表标识
    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="表编号")  # 计算 mapped_column(String(64), primary_key=True, comment="表编号") 并保存到变量 id
    name: Mapped[str | None] = mapped_column(String(128), comment="表名称")  # 计算 mapped_column(String(128), comment="表名称") 并保存到变量 name
    role: Mapped[str | None] = mapped_column(String(32), comment="表类型(fact/dim)")  # 计算 mapped_column(String(32), comment="表类型(fact/dim)") 并保存到变量 role
    description: Mapped[str | None] = mapped_column(Text, comment="表描述")  # 计算 mapped_column(Text, comment="表描述") 并保存到变量 description
