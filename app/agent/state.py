"""
电商问数 Agent 状态定义

State 是 LangGraph 各节点之间传递和更新的共享数据
本章在用户原始问题之外，新增关键词列表和三路召回结果
并把召回到的实体整理成后续提示词更容易消费的表信息和指标信息
SQL 生成闭环会继续写入候选 SQL 以及校验错误信息，用于控制校正或执行分支
"""

from typing import Any, TypedDict  # 从 typing 导入 Any, TypedDict，供本模块后续代码使用

from app.entities.column_info import ColumnInfo  # 从 app.entities.column_info 导入 ColumnInfo，供本模块后续代码使用
from app.entities.metric_info import MetricInfo  # 从 app.entities.metric_info 导入 MetricInfo，供本模块后续代码使用
from app.entities.value_info import ValueInfo  # 从 app.entities.value_info 导入 ValueInfo，供本模块后续代码使用


class MetricInfoState(TypedDict):  # 定义类 MetricInfoState，组织相关状态与行为
    """面向 SQL 生成提示词的指标信息"""

    name: str  # 声明或继续传入参数 name: str
    description: str  # 声明或继续传入参数 description: str
    # 指标依赖的字段 id，用来提示模型不要脱离业务口径随意计算
    relevant_columns: list[str]  # 声明或继续传入参数 relevant_columns: list[str]
    alias: list[str]  # 声明或继续传入参数 alias: list[str]


class ColumnInfoState(TypedDict):  # 定义类 ColumnInfoState，组织相关状态与行为
    """表上下文中的字段信息"""

    name: str  # 声明或继续传入参数 name: str
    type: str  # 声明或继续传入参数 type: str
    role: str  # 声明或继续传入参数 role: str
    # 字段真实样例值，尤其用于辅助 where 条件里的枚举值选择
    examples: list  # 声明或继续传入参数 examples: list
    description: str  # 声明或继续传入参数 description: str
    alias: list[str]  # 声明或继续传入参数 alias: list[str]


class TableInfoState(TypedDict):  # 定义类 TableInfoState，组织相关状态与行为
    """SQL 生成阶段真正传给模型的表结构上下文"""

    name: str  # 声明或继续传入参数 name: str
    role: str  # 声明或继续传入参数 role: str
    description: str  # 声明或继续传入参数 description: str
    columns: list[ColumnInfoState]  # 声明或继续传入参数 columns: list[ColumnInfoState]


class DateInfoState(TypedDict):  # 定义类 DateInfoState，组织相关状态与行为
    """SQL 生成阶段使用的当前日期上下文"""

    date: str  # 声明或继续传入参数 date: str
    weekday: str  # 声明或继续传入参数 weekday: str
    quarter: str  # 声明或继续传入参数 quarter: str


class DBInfoState(TypedDict):  # 定义类 DBInfoState，组织相关状态与行为
    """SQL 生成阶段使用的数据库环境信息"""

    dialect: str  # 声明或继续传入参数 dialect: str
    version: str  # 声明或继续传入参数 version: str


class DataAgentState(TypedDict, total=False):  # 定义类 DataAgentState，组织相关状态与行为
    """一次问数链路中的核心状态"""

    query: str  # 用户输入的查询
    run_id: str  # 声明或继续传入参数 run_id: str
    session_id: str  # 声明或继续传入参数 session_id: str
    selected_agent_id: str | None  # 声明或继续传入参数 selected_agent_id: str | None
    agent_version: str | None  # 声明或继续传入参数 agent_version: str | None
    resolved_query: str  # 声明或继续传入参数 resolved_query: str
    conversation: list[dict[str, str]]  # 声明或继续传入参数 conversation: list[dict[str, str]]
    column_terms: list[str]  # 声明或继续传入参数 column_terms: list[str]
    metric_terms: list[str]  # 声明或继续传入参数 metric_terms: list[str]
    value_terms: list[str]  # 声明或继续传入参数 value_terms: list[str]
    plan_fallback_reason: str | None  # 声明或继续传入参数 plan_fallback_reason: str | None
    keywords: list[str]  # 抽取的关键词
    retrieved_column_infos: list[ColumnInfo]  # 检索到的字段信息
    retrieved_metric_infos: list[MetricInfo]  # 检索到的指标信息
    retrieved_value_infos: list[ValueInfo]  # 检索到的取值信息

    table_infos: list[TableInfoState]  # 合并和补齐后的表结构上下文
    metric_infos: list[MetricInfoState]  # 合并后的指标上下文
    date_info: DateInfoState  # 当前日期 星期和季度信息
    db_info: DBInfoState  # 数据库方言和版本信息

    sql: str  # 生成或校正后的SQL
    executed_sql: str | None  # 声明或继续传入参数 executed_sql: str | None
    estimated_rows: int | None  # 声明或继续传入参数 estimated_rows: int | None
    sql_hash: str | None  # 声明或继续传入参数 sql_hash: str | None
    risk_reasons: list[str]  # 声明或继续传入参数 risk_reasons: list[str]
    high_risk: bool  # 声明或继续传入参数 high_risk: bool
    approval_required: bool  # 声明或继续传入参数 approval_required: bool
    approval_action: str | None  # 声明或继续传入参数 approval_action: str | None
    approval_rounds: int  # 声明或继续传入参数 approval_rounds: int
    correction_count: int  # 声明或继续传入参数 correction_count: int
    max_corrections: int  # 声明或继续传入参数 max_corrections: int
    human_edited_sql: bool  # 声明或继续传入参数 human_edited_sql: bool
    explain_plan: str | None  # 声明或继续传入参数 explain_plan: str | None
    risk_tables: list[str]  # 声明或继续传入参数 risk_tables: list[str]
    risk_columns: list[str]  # 声明或继续传入参数 risk_columns: list[str]

    error: str | None  # 校验SQL时出现的错误信息
    result: dict[str, Any] | None  # 声明或继续传入参数 result: dict[str, Any] | None
    agent_output: dict[str, Any] | None  # 声明或继续传入参数 agent_output: dict[str, Any] | None
