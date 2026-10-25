"""
`column_info` ORM 模型

定义元数据库中 column_info 表对应的 ORM 模型
保存字段级元数据，包括字段类型 字段角色 示例值 说明 别名 以及所属表
"""

from sqlalchemy import String, Text  # 从 sqlalchemy 导入 String, Text，供本模块后续代码使用
from sqlalchemy.orm import Mapped, mapped_column  # 从 sqlalchemy.orm 导入 Mapped, mapped_column，供本模块后续代码使用
from sqlalchemy.types import JSON  # 从 sqlalchemy.types 导入 JSON，供本模块后续代码使用

from app.models.base import Base  # 从 app.models.base 导入 Base，供本模块后续代码使用


class ColumnInfoMySQL(Base):  # 定义类 ColumnInfoMySQL，组织相关状态与行为
    """字段元数据表对应的 ORM 模型"""

    __tablename__ = "column_info"  # 计算 "column_info" 并保存到变量 __tablename__

    # id 采用 表名.字段名 的组合形式
    # 这样在整个数仓范围内更容易保证唯一性
    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="列编号")  # 计算 mapped_column(String(64), primary_key=True, comment="列编号") 并保存到变量 id
    name: Mapped[str | None] = mapped_column(String(128), comment="列名称")  # 计算 mapped_column(String(128), comment="列名称") 并保存到变量 name
    type: Mapped[str | None] = mapped_column(String(64), comment="数据类型")  # 计算 mapped_column(String(64), comment="数据类型") 并保存到变量 type
    role: Mapped[str | None] = mapped_column(  # 调用 mapped_column 构造结果并保存到 role
        String(32), comment="列类型(primary_key,foreign_key,measure,dimension)"  # 调用 String 执行当前步骤：String(32), comment="列类型(primary_key,foreign_key,measure,dimension)"
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    # examples 和 alias 都使用 JSON 存储
    # 方便保存列表结构而不是再拆独立子表
    examples: Mapped[dict | list | None] = mapped_column(JSON, comment="数据示例")  # 计算 mapped_column(JSON, comment="数据示例") 并保存到变量 examples
    description: Mapped[str | None] = mapped_column(Text, comment="列描述")  # 计算 mapped_column(Text, comment="列描述") 并保存到变量 description
    alias: Mapped[dict | list | None] = mapped_column(JSON, comment="列别名")  # 计算 mapped_column(JSON, comment="列别名") 并保存到变量 alias
    table_id: Mapped[str | None] = mapped_column(String(64), comment="所属表编号")  # 计算 mapped_column(String(64), comment="所属表编号") 并保存到变量 table_id
