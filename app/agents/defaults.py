"""Static registration of agents shipped with this repository."""

from app.agents.analytics_sql.definition import ANALYTICS_SQL_AGENT  # 从 app.agents.analytics_sql.definition 导入 ANALYTICS_SQL_AGENT，供本模块后续代码使用
from app.agents.catalog_qa.definition import CATALOG_QA_AGENT  # 从 app.agents.catalog_qa.definition 导入 CATALOG_QA_AGENT，供本模块后续代码使用
from app.agents.registry import AgentRegistry  # 从 app.agents.registry 导入 AgentRegistry，供本模块后续代码使用
from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用


def build_default_registry(settings: Settings) -> AgentRegistry:  # 定义函数 build_default_registry，封装该模块的一项明确职责
    return AgentRegistry(  # 返回 AgentRegistry( 给调用方
        (ANALYTICS_SQL_AGENT, CATALOG_QA_AGENT),  # 向多行序列加入元素 (ANALYTICS_SQL_AGENT, CATALOG_QA_AGENT)
        settings,  # 继续向上一处调用或声明传入 settings
    )  # 结束函数 build_default_registry 的参数及返回类型声明并开始函数体
