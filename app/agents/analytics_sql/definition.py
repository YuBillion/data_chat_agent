"""Static analytics agent registration."""

from app.agents.analytics_sql.graph import build_analytics_graph  # 从 app.agents.analytics_sql.graph 导入 build_analytics_graph，供本模块后续代码使用
from app.agents.types import AgentDefinition  # 从 app.agents.types 导入 AgentDefinition，供本模块后续代码使用

ANALYTICS_SQL_AGENT = AgentDefinition(  # 调用 AgentDefinition 构造结果并保存到 ANALYTICS_SQL_AGENT
    agent_id="analytics_sql",  # 为 AgentDefinition 设置关键字参数 agent_id，传入当前行给出的值
    version="1.0.0",  # 为 AgentDefinition 设置关键字参数 version，传入当前行给出的值
    display_name="问数 Agent",  # 为 AgentDefinition 设置关键字参数 display_name，传入当前行给出的值
    description="查询真实业务数据并执行受控 SQL，支持多轮追问和人工审批。",  # 为 AgentDefinition 设置关键字参数 description，传入当前行给出的值
    capabilities=(  # 为 AgentDefinition 设置关键字参数 capabilities，传入当前行给出的值
        "business_data_query",  # 向多行序列加入元素 "business_data_query"
        "sql_generation",  # 向多行序列加入元素 "sql_generation"
        "sql_execution",  # 向多行序列加入元素 "sql_execution"
        "multi_turn_follow_up",  # 向多行序列加入元素 "multi_turn_follow_up"
    ),  # 结束上一处多行结构，保持表达式边界清晰
    state_schema_version="analytics.1",  # 为 AgentDefinition 设置关键字参数 state_schema_version，传入当前行给出的值
    prompt_ids=(  # 为 AgentDefinition 设置关键字参数 prompt_ids，传入当前行给出的值
        "plan_query",  # 向多行序列加入元素 "plan_query"
        "filter_table_info",  # 向多行序列加入元素 "filter_table_info"
        "filter_metric_info",  # 向多行序列加入元素 "filter_metric_info"
        "generate_sql",  # 向多行序列加入元素 "generate_sql"
        "correct_sql",  # 向多行序列加入元素 "correct_sql"
    ),  # 结束上一处多行结构，保持表达式边界清晰
    graph_factory=build_analytics_graph,  # 为 AgentDefinition 设置关键字参数 graph_factory，传入当前行给出的值
    allowed_tools=frozenset(  # 为 frozenset 设置关键字参数 allowed_tools，传入当前行给出的值
        {  # 执行源码表达式 {，完成本行对应的语义动作
            "catalog_search",  # 向多行序列加入元素 "catalog_search"
            "column_vector_search",  # 向多行序列加入元素 "column_vector_search"
            "metric_vector_search",  # 向多行序列加入元素 "metric_vector_search"
            "value_full_text_search",  # 向多行序列加入元素 "value_full_text_search"
            "sql_guard",  # 向多行序列加入元素 "sql_guard"
            "sql_explain",  # 向多行序列加入元素 "sql_explain"
            "sql_execute",  # 向多行序列加入元素 "sql_execute"
        }  # 结束上一处多行结构，保持表达式边界清晰
    ),  # 结束 frozenset 调用参数，得到完整表达式结果
    model_profile="analytics_default",  # 为 AgentDefinition 设置关键字参数 model_profile，传入当前行给出的值
    policy_profile="conditional_sql_approval",  # 为 AgentDefinition 设置关键字参数 policy_profile，传入当前行给出的值
    default_priority=10,  # 为 AgentDefinition 设置关键字参数 default_priority，传入当前行给出的值
)  # 结束 AgentDefinition 调用参数，得到完整表达式结果
