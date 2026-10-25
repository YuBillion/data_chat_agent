"""
`column_metric` ORM 模型

定义元数据库中 column_metric 表对应的 ORM 模型
负责保存字段和指标之间的关联关系，方便后续从字段追踪相关指标，或者从指标回查依赖字段
"""

from sqlalchemy import String  # 从 sqlalchemy 导入 String，供本模块后续代码使用
from sqlalchemy.orm import Mapped, mapped_column  # 从 sqlalchemy.orm 导入 Mapped, mapped_column，供本模块后续代码使用

from app.models.base import Base  # 从 app.models.base 导入 Base，供本模块后续代码使用


class ColumnMetricMySQL(Base):  # 定义类 ColumnMetricMySQL，组织相关状态与行为
    """字段与指标关联关系表对应的 ORM 模型"""

    __tablename__ = "column_metric"  # 计算 "column_metric" 并保存到变量 __tablename__

    # 这里采用联合主键
    # 表示同一对 字段 指标 关系只允许出现一次
    column_id: Mapped[str] = mapped_column(  # 调用 mapped_column 构造结果并保存到 column_id
        String(64), primary_key=True, comment="列编号"  # 调用 String 执行当前步骤：String(64), primary_key=True, comment="列编号"
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
    metric_id: Mapped[str] = mapped_column(  # 调用 mapped_column 构造结果并保存到 metric_id
        String(64), primary_key=True, comment="指标编号"  # 调用 String 执行当前步骤：String(64), primary_key=True, comment="指标编号"
    )  # 结束 mapped_column 调用参数，得到完整表达式结果
