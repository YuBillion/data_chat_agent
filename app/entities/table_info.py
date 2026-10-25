"""
表元数据业务实体

这一层对应文档里“先把配置描述转换成业务实体”的部分，用于在 Service
和 Repository 之间传递统一的表语义信息，而不是直接暴露 ORM 模型
"""

from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class TableInfo:  # 定义类 TableInfo，组织相关状态与行为
    """系统内部统一使用的表元数据表达"""

    id: str  # 声明或继续传入参数 id: str
    name: str  # 声明或继续传入参数 name: str
    role: str  # 声明或继续传入参数 role: str
    description: str  # 声明或继续传入参数 description: str
