"""
指标元数据业务实体

用于表达一个业务指标的名称 说明 别名以及它依赖的底层字段
后续写入 Meta MySQL 和 Qdrant 时都会复用这份统一的业务对象
"""

from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class MetricInfo:  # 定义类 MetricInfo，组织相关状态与行为
    """系统内部统一使用的指标元数据表达"""

    id: str  # 声明或继续传入参数 id: str
    name: str  # 声明或继续传入参数 name: str
    description: str  # 声明或继续传入参数 description: str
    # 指标依赖的底层字段列表，例如 GMV 依赖 fact_order.order_amount
    relevant_columns: list[str]  # 声明或继续传入参数 relevant_columns: list[str]
    alias: list[str]  # 声明或继续传入参数 alias: list[str]
