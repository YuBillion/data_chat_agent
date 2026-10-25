"""
元数据知识构建配置

定义 meta_config.yaml 在程序中的结构，这份配置不描述底层基础设施
而是描述一次元数据知识构建要处理哪些表 哪些字段 和哪些指标，脚本入口会先读取 YAML
再把内容转换成这里定义的 dataclass 对象，后续服务层就可以按统一结构完成元数据同步
"""

from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用
from typing import Optional  # 从 typing 导入 Optional，供本模块后续代码使用


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class ColumnConfig:  # 定义类 ColumnConfig，组织相关状态与行为
    """
    单个字段的同步配置
    描述字段的业务角色 说明 别名以及是否同步字段值
    """

    name: str  # 声明或继续传入参数 name: str
    role: str  # 声明或继续传入参数 role: str
    description: str  # 声明或继续传入参数 description: str
    alias: list[str]  # 声明或继续传入参数 alias: list[str]
    sync: bool  # 声明或继续传入参数 sync: bool


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class TableConfig:  # 定义类 TableConfig，组织相关状态与行为
    """
    单张表及其字段列表的同步配置
    一张表下面会继续声明需要纳入知识库的字段列表
    """

    name: str  # 声明或继续传入参数 name: str
    role: str  # 声明或继续传入参数 role: str
    description: str  # 声明或继续传入参数 description: str
    columns: list[ColumnConfig]  # 声明或继续传入参数 columns: list[ColumnConfig]


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class MetricConfig:  # 定义类 MetricConfig，组织相关状态与行为
    """
    单个指标的同步配置
    用来描述指标和底层字段之间的关联关系
    """

    name: str  # 声明或继续传入参数 name: str
    description: str  # 声明或继续传入参数 description: str
    relevant_columns: list[str]  # 声明或继续传入参数 relevant_columns: list[str]
    alias: list[str]  # 声明或继续传入参数 alias: list[str]


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class MetaConfig:  # 定义类 MetaConfig，组织相关状态与行为
    """
    元数据知识构建总配置
    tables 和 metrics 都允许为空 便于分阶段只构建其中一部分
    """

    tables: Optional[list[TableConfig]] = None  # 计算 None 并保存到变量 tables
    metrics: Optional[list[MetricConfig]] = None  # 计算 None 并保存到变量 metrics
