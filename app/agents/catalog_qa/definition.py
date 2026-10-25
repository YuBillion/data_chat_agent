"""Static catalog question-answering agent registration."""

from app.agents.catalog_qa.graph import build_catalog_graph  # 从 app.agents.catalog_qa.graph 导入 build_catalog_graph，供本模块后续代码使用
from app.agents.types import AgentDefinition  # 从 app.agents.types 导入 AgentDefinition，供本模块后续代码使用

CATALOG_QA_AGENT = AgentDefinition(  # 调用 AgentDefinition 构造结果并保存到 CATALOG_QA_AGENT
    agent_id="catalog_qa",  # 为 AgentDefinition 设置关键字参数 agent_id，传入当前行给出的值
    version="1.0.0",  # 为 AgentDefinition 设置关键字参数 version，传入当前行给出的值
    display_name="元数据问答 Agent",  # 为 AgentDefinition 设置关键字参数 display_name，传入当前行给出的值
    description="解释表、字段和指标定义与口径，不查询真实业务数据。",  # 为 AgentDefinition 设置关键字参数 description，传入当前行给出的值
    capabilities=(  # 为 AgentDefinition 设置关键字参数 capabilities，传入当前行给出的值
        "catalog_definition",  # 向多行序列加入元素 "catalog_definition"
        "metric_definition",  # 向多行序列加入元素 "metric_definition"
        "table_schema",  # 向多行序列加入元素 "table_schema"
        "multi_turn_follow_up",  # 向多行序列加入元素 "multi_turn_follow_up"
    ),  # 结束上一处多行结构，保持表达式边界清晰
    state_schema_version="catalog.1",  # 为 AgentDefinition 设置关键字参数 state_schema_version，传入当前行给出的值
    prompt_ids=("catalog_qa",),  # 为 AgentDefinition 设置关键字参数 prompt_ids，传入当前行给出的值
    graph_factory=build_catalog_graph,  # 为 AgentDefinition 设置关键字参数 graph_factory，传入当前行给出的值
    allowed_tools=frozenset(  # 为 frozenset 设置关键字参数 allowed_tools，传入当前行给出的值
        {  # 执行源码表达式 {，完成本行对应的语义动作
            "catalog_search",  # 向多行序列加入元素 "catalog_search"
            "column_vector_search",  # 向多行序列加入元素 "column_vector_search"
            "metric_vector_search",  # 向多行序列加入元素 "metric_vector_search"
        }  # 结束上一处多行结构，保持表达式边界清晰
    ),  # 结束 frozenset 调用参数，得到完整表达式结果
    model_profile="catalog_default",  # 为 AgentDefinition 设置关键字参数 model_profile，传入当前行给出的值
    policy_profile="read_only_metadata",  # 为 AgentDefinition 设置关键字参数 policy_profile，传入当前行给出的值
    default_priority=20,  # 为 AgentDefinition 设置关键字参数 default_priority，传入当前行给出的值
)  # 结束 AgentDefinition 调用参数，得到完整表达式结果
