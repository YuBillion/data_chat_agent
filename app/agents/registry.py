"""Immutable, code-first registry for agent graphs."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import re  # 导入re，建立本模块需要的外部能力引用
from collections.abc import Iterable  # 从 collections.abc 导入 Iterable，供本模块后续代码使用

from app.agents.types import AgentDefinition, AgentPublicView  # 从 app.agents.types 导入 AgentDefinition, AgentPublicView，供本模块后续代码使用
from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.core.errors import AppError, NotFoundError  # 从 app.core.errors 导入 AppError, NotFoundError，供本模块后续代码使用
from app.harness.types import Identity  # 从 app.harness.types 导入 Identity，供本模块后续代码使用
from app.prompt.prompt_loader import load_prompt, prompt_digest  # 从 app.prompt.prompt_loader 导入 load_prompt, prompt_digest，供本模块后续代码使用

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")  # 计算 re.compile(r"^\d+\.\d+\.\d+$") 并保存到变量 SEMVER
KNOWN_TOOLS = frozenset(  # 调用 frozenset 构造结果并保存到 KNOWN_TOOLS
    {  # 执行源码表达式 {，完成本行对应的语义动作
        "catalog_search",  # 向多行序列加入元素 "catalog_search"
        "column_vector_search",  # 向多行序列加入元素 "column_vector_search"
        "metric_vector_search",  # 向多行序列加入元素 "metric_vector_search"
        "value_full_text_search",  # 向多行序列加入元素 "value_full_text_search"
        "sql_guard",  # 向多行序列加入元素 "sql_guard"
        "sql_explain",  # 向多行序列加入元素 "sql_explain"
        "sql_execute",  # 向多行序列加入元素 "sql_execute"
    }  # 结束上一处多行结构，保持表达式边界清晰
)  # 结束 frozenset 调用参数，得到完整表达式结果


class AgentRegistryError(AppError):  # 定义类 AgentRegistryError，组织相关状态与行为
    def __init__(self, message: str) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(  # 调用 super 执行当前步骤：super().__init__(
            code="AGENT_REGISTRY_INVALID",  # 为 __init__ 设置关键字参数 code，传入当前行给出的值
            message=message,  # 为 __init__ 设置关键字参数 message，传入当前行给出的值
            status_code=500,  # 为 __init__ 设置关键字参数 status_code，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体


class AgentRegistry:  # 定义类 AgentRegistry，组织相关状态与行为
    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        definitions: Iterable[AgentDefinition],  # 为函数 __init__ 声明参数 definitions 及其类型或默认值
        settings: Settings,  # 为函数 __init__ 声明参数 settings 及其类型或默认值
    ) -> None:  # 结束 __init__ 的参数列表并声明返回类型
        self.settings = settings  # 将依赖或状态 settings 保存到实例属性 self.settings
        self._definitions: dict[str, AgentDefinition] = {}  # 将依赖或状态 {} 保存到实例属性 self._definitions: dict[str, AgentDefinition]
        enabled = set(settings.enabled_agents)  # 计算 set(settings.enabled_agents) 并保存到变量 enabled
        for definition in definitions:  # 按迭代条件执行循环：for definition in definitions:
            self._validate_definition(definition)  # 调用 _validate_definition 执行当前步骤：self._validate_definition(definition)
            if definition.agent_id in self._definitions:  # 判断分支条件：if definition.agent_id in self._definitions:
                raise AgentRegistryError(  # 抛出明确异常，阻止错误状态被静默接受：AgentRegistryError(
                    f"duplicate agent id: {definition.agent_id}"  # 在函数 __init__ 中执行表达式 f"duplicate agent id: {definition.agent_id}"，推进当前业务流程
                )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体
            if definition.agent_id in enabled:  # 判断分支条件：if definition.agent_id in enabled:
                self._definitions[definition.agent_id] = definition  # 将 definition 保存到实例属性 self._definitions[definition.agent_id]
        missing = enabled.difference(self._definitions)  # 计算 enabled.difference(self._definitions) 并保存到变量 missing
        if missing:  # 判断分支条件：if missing:
            raise AgentRegistryError(  # 抛出明确异常，阻止错误状态被静默接受：AgentRegistryError(
                "enabled agents are not registered: " + ", ".join(sorted(missing))  # 调用 目标函数 执行当前步骤："enabled agents are not registered: " + ", ".join(sorted(missing))
            )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体

    def _validate_definition(self, definition: AgentDefinition) -> None:  # 定义函数 _validate_definition，封装该模块的一项明确职责
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", definition.agent_id):  # 判断分支条件：if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", definition.agent_id):
            raise AgentRegistryError(  # 抛出明确异常，阻止错误状态被静默接受：AgentRegistryError(
                f"invalid agent id: {definition.agent_id}"  # 在函数 _validate_definition 中执行表达式 f"invalid agent id: {definition.agent_id}"，推进当前业务流程
            )  # 结束函数 _validate_definition 的参数及返回类型声明并开始函数体
        if not SEMVER.fullmatch(definition.version):  # 判断分支条件：if not SEMVER.fullmatch(definition.version):
            raise AgentRegistryError(  # 抛出明确异常，阻止错误状态被静默接受：AgentRegistryError(
                f"agent {definition.agent_id} has an invalid semantic version"  # 在函数 _validate_definition 中执行表达式 f"agent {definition.agent_id} has an invalid semantic version"，推进当前业务流程
            )  # 结束函数 _validate_definition 的参数及返回类型声明并开始函数体
        if not callable(definition.graph_factory):  # 判断分支条件：if not callable(definition.graph_factory):
            raise AgentRegistryError(  # 抛出明确异常，阻止错误状态被静默接受：AgentRegistryError(
                f"agent {definition.agent_id} graph factory is not callable"  # 在函数 _validate_definition 中执行表达式 f"agent {definition.agent_id} graph factory is not callable"，推进当前业务流程
            )  # 结束函数 _validate_definition 的参数及返回类型声明并开始函数体
        unknown_tools = definition.allowed_tools.difference(KNOWN_TOOLS)  # 计算 definition.allowed_tools.difference(KNOWN_TOOLS) 并保存到变量 unknown_tools
        if unknown_tools:  # 判断分支条件：if unknown_tools:
            raise AgentRegistryError(  # 抛出明确异常，阻止错误状态被静默接受：AgentRegistryError(
                f"agent {definition.agent_id} references unknown tools: "  # 在函数 _validate_definition 中执行表达式 f"agent {definition.agent_id} references unknown tools: "，推进当前业务流程
                + ", ".join(sorted(unknown_tools))  # 调用 目标函数 执行当前步骤：+ ", ".join(sorted(unknown_tools))
            )  # 结束函数 _validate_definition 的参数及返回类型声明并开始函数体
        for prompt_id in definition.prompt_ids:  # 按迭代条件执行循环：for prompt_id in definition.prompt_ids:
            load_prompt(prompt_id)  # 调用 load_prompt 执行当前步骤：load_prompt(prompt_id)
            prompt_digest(prompt_id)  # 调用 prompt_digest 执行当前步骤：prompt_digest(prompt_id)

    def get(self, agent_id: str) -> AgentDefinition:  # 定义函数 get，封装该模块的一项明确职责
        definition = self._definitions.get(agent_id)  # 计算 self._definitions.get(agent_id) 并保存到变量 definition
        if definition is None:  # 判断分支条件：if definition is None:
            raise AgentRegistryError(f"agent is not available: {agent_id}")  # 抛出明确异常，阻止错误状态被静默接受：AgentRegistryError(f"agent is not available: {agent_id}")
        return definition  # 返回 definition 给调用方

    def try_get(self, agent_id: str | None) -> AgentDefinition | None:  # 定义函数 try_get，封装该模块的一项明确职责
        if not agent_id:  # 判断分支条件：if not agent_id:
            return None  # 返回 None 给调用方
        return self._definitions.get(agent_id)  # 返回 self._definitions.get(agent_id) 给调用方

    def list_for(self, identity: Identity, permission: str = "use") -> list[AgentDefinition]:  # 定义函数 list_for，封装该模块的一项明确职责
        if not identity.has_role("agent:user") and not identity.has_role("agent:admin"):  # 判断分支条件：if not identity.has_role("agent:user") and not identity.has_role("agent…
            return []  # 返回 [] 给调用方
        del permission  # 删除或显式忽略名称 permission，避免未使用变量干扰
        return sorted(  # 返回 sorted( 给调用方
            self._definitions.values(),  # 继续向上一处调用或声明传入 self._definitions.values()
            key=lambda item: (item.default_priority, item.agent_id),  # 为 sorted 设置关键字参数 key，传入当前行给出的值
        )  # 结束函数 list_for 的参数及返回类型声明并开始函数体

    def public_list(self, identity: Identity) -> list[AgentPublicView]:  # 定义函数 public_list，封装该模块的一项明确职责
        return [  # 返回 [ 给调用方
            definition.public_view()  # 调用 public_view 执行当前步骤：definition.public_view()
            for definition in self.list_for(identity)  # 按迭代条件执行循环：for definition in self.list_for(identity)
        ]  # 结束上一处多行结构，保持表达式边界清晰

    def public_one(self, identity: Identity, agent_id: str) -> AgentPublicView:  # 定义函数 public_one，封装该模块的一项明确职责
        definition = self.try_get(agent_id)  # 计算 self.try_get(agent_id) 并保存到变量 definition
        if definition is None or definition not in self.list_for(identity):  # 判断分支条件：if definition is None or definition not in self.list_for(identity):
            raise NotFoundError("agent", agent_id)  # 抛出明确异常，阻止错误状态被静默接受：NotFoundError("agent", agent_id)
        return definition.public_view()  # 返回 definition.public_view() 给调用方

    def prompt_manifest(self, agent_id: str) -> dict[str, str]:  # 定义函数 prompt_manifest，封装该模块的一项明确职责
        definition = self.get(agent_id)  # 计算 self.get(agent_id) 并保存到变量 definition
        return {  # 返回 { 给调用方
            prompt_id: prompt_digest(prompt_id)  # 声明或继续传入参数 prompt_id: prompt_digest(prompt_id)
            for prompt_id in definition.prompt_ids  # 按迭代条件执行循环：for prompt_id in definition.prompt_ids
        }  # 结束上一处多行结构，保持表达式边界清晰

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def agent_ids(self) -> tuple[str, ...]:  # 定义函数 agent_ids，封装该模块的一项明确职责
        return tuple(sorted(self._definitions))  # 返回 tuple(sorted(self._definitions)) 给调用方

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def definitions(self) -> tuple[AgentDefinition, ...]:  # 定义函数 definitions，封装该模块的一项明确职责
        return tuple(  # 返回 tuple( 给调用方
            self._definitions[agent_id]  # 在函数 definitions 中执行表达式 self._definitions[agent_id]，推进当前业务流程
            for agent_id in sorted(self._definitions)  # 按迭代条件执行循环：for agent_id in sorted(self._definitions)
        )  # 结束函数 definitions 的参数及返回类型声明并开始函数体
