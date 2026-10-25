"""
字段取值业务实体

该对象用于承接字段值同步链路中的结构化结果，和表、字段、指标实体保持
一致的业务层表达方式
"""

from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class ValueInfo:  # 定义类 ValueInfo，组织相关状态与行为
    """字段具体取值及其所属字段的业务表达"""

    id: str  # 声明或继续传入参数 id: str
    value: str  # 声明或继续传入参数 value: str
    column_id: str  # 声明或继续传入参数 column_id: str
