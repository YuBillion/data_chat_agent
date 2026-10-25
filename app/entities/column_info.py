"""
字段元数据业务实体

字段配置中的业务语义、从数仓补齐的真实类型，以及抽样得到的示例值，
都会汇总到这个对象里，再继续流向元数据库与后续检索链路
"""

from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class ColumnInfo:  # 定义类 ColumnInfo，组织相关状态与行为
    """系统内部统一使用的字段元数据表达"""

    id: str  # 声明或继续传入参数 id: str
    name: str  # 声明或继续传入参数 name: str
    type: str  # 声明或继续传入参数 type: str
    role: str  # 声明或继续传入参数 role: str
    examples: list[Any]  # 声明或继续传入参数 examples: list[Any]
    description: str  # 声明或继续传入参数 description: str
    alias: list[str]  # 声明或继续传入参数 alias: list[str]
    table_id: str  # 声明或继续传入参数 table_id: str
