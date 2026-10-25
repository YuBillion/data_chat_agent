"""
字段与指标关联业务实体

用于表达一个指标依赖哪些字段，为后续指标知识组织和关联查询提供统一的中间对象
"""

from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class ColumnMetric:  # 定义类 ColumnMetric，组织相关状态与行为
    """字段和指标之间的关联关系"""

    column_id: str  # 声明或继续传入参数 column_id: str
    metric_id: str  # 声明或继续传入参数 metric_id: str
