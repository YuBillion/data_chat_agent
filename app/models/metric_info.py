"""
`metric_info` ORM 模型

定义元数据库中 metric_info 表对应的 ORM 模型
负责保存指标名称 指标说明 指标别名，以及指标和底层字段之间的关联关系
"""

from sqlalchemy import String, Text  # 从 sqlalchemy 导入 String, Text，供本模块后续代码使用
from sqlalchemy.orm import Mapped, mapped_column  # 从 sqlalchemy.orm 导入 Mapped, mapped_column，供本模块后续代码使用
from sqlalchemy.types import JSON  # 从 sqlalchemy.types 导入 JSON，供本模块后续代码使用

from app.models.base import Base  # 从 app.models.base 导入 Base，供本模块后续代码使用


class MetricInfoMySQL(Base):  # 定义类 MetricInfoMySQL，组织相关状态与行为
    """指标元数据表对应的 ORM 模型"""

    __tablename__ = "metric_info"  # 计算 "metric_info" 并保存到变量 __tablename__

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="指标编码")  # 计算 mapped_column(String(64), primary_key=True, comment="指标编码") 并保存到变量 id
    name: Mapped[str | None] = mapped_column(String(128), comment="指标名称")  # 计算 mapped_column(String(128), comment="指标名称") 并保存到变量 name
    description: Mapped[str | None] = mapped_column(Text, comment="指标描述")  # 计算 mapped_column(Text, comment="指标描述") 并保存到变量 description
    # 指标通常会关联一个或多个底层字段
    # 这里直接以 JSON 数组保存字段标识列表
    relevant_columns: Mapped[dict | list | None] = mapped_column(  # 调用 mapped_column 构造结果并保存到 relevant_columns
        JSON, comment="关联字段"  # 在类 MetricInfoMySQL 中执行声明或表达式 JSON, comment="关联字段"，提供实例所需能力
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    alias: Mapped[dict | list | None] = mapped_column(JSON, comment="指标别名")  # 计算 mapped_column(JSON, comment="指标别名") 并保存到变量 alias
