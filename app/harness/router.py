"""Explicit, rule-based, and model-assisted Agent routing."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import json  # 导入json，建立本模块需要的外部能力引用
import re  # 导入re，建立本模块需要的外部能力引用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用

from langchain_core.output_parsers import JsonOutputParser  # 从 langchain_core.output_parsers 导入 JsonOutputParser，供本模块后续代码使用
from langchain_core.prompts import PromptTemplate  # 从 langchain_core.prompts 导入 PromptTemplate，供本模块后续代码使用

from app.agents.registry import AgentRegistry  # 从 app.agents.registry 导入 AgentRegistry，供本模块后续代码使用
from app.agents.types import RouteCandidate, RouteDecision, RouterModelOutput  # 从 app.agents.types 导入 RouteCandidate, RouteDecision, RouterModelOutput，供本模块后续代码使用
from app.core.errors import AppError, BudgetExceededError  # 从 app.core.errors 导入 AppError, BudgetExceededError，供本模块后续代码使用
from app.harness.types import Identity, RouteMode  # 从 app.harness.types 导入 Identity, RouteMode，供本模块后续代码使用
from app.infrastructure.llm import RunLLM  # 从 app.infrastructure.llm 导入 RunLLM，供本模块后续代码使用
from app.prompt.prompt_loader import load_prompt  # 从 app.prompt.prompt_loader 导入 load_prompt，供本模块后续代码使用

DATA_INTENT = re.compile(  # 调用 compile 构造结果并保存到 DATA_INTENT
    r"(多少|统计|汇总|总计|合计|排行|排名|趋势|环比|同比|增长|下降|"  # 调用 目标函数 执行当前步骤：r"(多少|统计|汇总|总计|合计|排行|排名|趋势|环比|同比|增长|下降|"
    r"按.+分组|按月|按季度|按地区|销量|销售额|订单数|GMV\s*(是多少|有多少|排名))",  # 继续向上一处调用或声明传入 r"按.+分组|按月|按季度|按地区|销量|销售额|订单数|GMV\s*(是多少|有多少|排名))"
    re.IGNORECASE,  # 继续向上一处调用或声明传入 re.IGNORECASE
)  # 结束 re.compile 调用参数，得到完整表达式结果
DATA_NOUN = re.compile(  # 调用 compile 构造结果并保存到 DATA_NOUN
    r"(GMV|AOV|销量|销售额|订单数|收入|数量|金额|客单价)", re.IGNORECASE  # 调用 目标函数 执行当前步骤：r"(GMV|AOV|销量|销售额|订单数|收入|数量|金额|客单价)", re.IGNORECASE
)  # 结束 re.compile 调用参数，得到完整表达式结果
CATALOG_INTENT = re.compile(  # 调用 compile 构造结果并保存到 CATALOG_INTENT
    r"(什么是|是什么|定义|含义|口径|怎么算|如何计算|有哪些字段|字段说明|"  # 调用 目标函数 执行当前步骤：r"(什么是|是什么|定义|含义|口径|怎么算|如何计算|有哪些字段|字段说明|"
    r"表结构|包括哪些|字段类型)"  # 执行源码表达式 r"表结构|包括哪些|字段类型)"，完成本行对应的语义动作
)  # 结束 re.compile 调用参数，得到完整表达式结果


class RouterError(AppError):  # 定义类 RouterError，组织相关状态与行为
    def __init__(self, message: str) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(  # 调用 super 执行当前步骤：super().__init__(
            code="AGENT_ROUTE_FAILED",  # 为 __init__ 设置关键字参数 code，传入当前行给出的值
            message=message,  # 为 __init__ 设置关键字参数 message，传入当前行给出的值
            status_code=409,  # 为 __init__ 设置关键字参数 status_code，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体


class AgentRouter:  # 定义类 AgentRouter，组织相关状态与行为
    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        registry: AgentRegistry,  # 为函数 __init__ 声明参数 registry 及其类型或默认值
        *,  # 为函数 __init__ 声明参数 * 及其类型或默认值
        min_confidence: float = 0.8,  # 为函数 __init__ 声明参数 min_confidence 及其类型或默认值
        min_margin: float = 0.15,  # 为函数 __init__ 声明参数 min_margin 及其类型或默认值
    ) -> None:  # 结束 __init__ 的参数列表并声明返回类型
        self.registry = registry  # 将依赖或状态 registry 保存到实例属性 self.registry
        self.min_confidence = min_confidence  # 将依赖或状态 min_confidence 保存到实例属性 self.min_confidence
        self.min_margin = min_margin  # 将依赖或状态 min_margin 保存到实例属性 self.min_margin

    async def route(  # 定义异步函数 route，封装可被事件循环调度的协程逻辑
        self,  # 为函数 route 声明参数 self 及其类型或默认值
        *,  # 为函数 route 声明参数 * 及其类型或默认值
        identity: Identity,  # 为函数 route 声明参数 identity 及其类型或默认值
        query: str,  # 为函数 route 声明参数 query 及其类型或默认值
        requested_agent_id: str | None,  # 为函数 route 声明参数 requested_agent_id 及其类型或默认值
        history: list[dict[str, str]],  # 为函数 route 声明参数 history 及其类型或默认值
        llm: RunLLM,  # 为函数 route 声明参数 llm 及其类型或默认值
    ) -> RouteDecision:  # 结束 route 的参数列表并声明返回类型
        agents = self.registry.list_for(identity)  # 计算 self.registry.list_for(identity) 并保存到变量 agents
        if requested_agent_id:  # 判断分支条件：if requested_agent_id:
            requested = self.registry.try_get(requested_agent_id)  # 计算 self.registry.try_get(requested_agent_id) 并保存到变量 requested
            if requested is None or requested not in agents:  # 判断分支条件：if requested is None or requested not in agents:
                raise RouterError(  # 抛出明确异常，阻止错误状态被静默接受：RouterError(
                    f"requested agent is not available: {requested_agent_id}"  # 在函数 route 中执行表达式 f"requested agent is not available: {requested_agent_id}"，推进当前业务流程
                )  # 结束函数 route 的参数及返回类型声明并开始函数体
            return RouteDecision(  # 返回 RouteDecision( 给调用方
                selected_agent_id=requested.agent_id,  # 为 RouteDecision 设置关键字参数 selected_agent_id，传入当前行给出的值
                mode=RouteMode.EXPLICIT,  # 为 RouteDecision 设置关键字参数 mode，传入当前行给出的值
                confidence=1.0,  # 为 RouteDecision 设置关键字参数 confidence，传入当前行给出的值
                candidates=[  # 为 RouteDecision 设置关键字参数 candidates，传入当前行给出的值
                    RouteCandidate(  # 调用 RouteCandidate 执行当前步骤：RouteCandidate(
                        agent_id=requested.agent_id,  # 为 RouteCandidate 设置关键字参数 agent_id，传入当前行给出的值
                        confidence=1.0,  # 为 RouteCandidate 设置关键字参数 confidence，传入当前行给出的值
                        reason="explicit_selection",  # 为 RouteCandidate 设置关键字参数 reason，传入当前行给出的值
                    )  # 结束函数 route 的参数及返回类型声明并开始函数体
                ],  # 结束上一处多行结构，保持表达式边界清晰
                reason_code="explicit_selection",  # 为 RouteDecision 设置关键字参数 reason_code，传入当前行给出的值
                resolved_query=query,  # 为 RouteDecision 设置关键字参数 resolved_query，传入当前行给出的值
            )  # 结束函数 route 的参数及返回类型声明并开始函数体

        if len(agents) == 1:  # 判断分支条件：if len(agents) == 1:
            only = agents[0]  # 计算 agents[0] 并保存到变量 only
            return RouteDecision(  # 返回 RouteDecision( 给调用方
                selected_agent_id=only.agent_id,  # 为 RouteDecision 设置关键字参数 selected_agent_id，传入当前行给出的值
                mode=RouteMode.RULE,  # 为 RouteDecision 设置关键字参数 mode，传入当前行给出的值
                confidence=1.0,  # 为 RouteDecision 设置关键字参数 confidence，传入当前行给出的值
                candidates=[  # 为 RouteDecision 设置关键字参数 candidates，传入当前行给出的值
                    RouteCandidate(  # 调用 RouteCandidate 执行当前步骤：RouteCandidate(
                        agent_id=only.agent_id,  # 为 RouteCandidate 设置关键字参数 agent_id，传入当前行给出的值
                        confidence=1.0,  # 为 RouteCandidate 设置关键字参数 confidence，传入当前行给出的值
                        reason="only_enabled_agent",  # 为 RouteCandidate 设置关键字参数 reason，传入当前行给出的值
                    )  # 结束函数 route 的参数及返回类型声明并开始函数体
                ],  # 结束上一处多行结构，保持表达式边界清晰
                reason_code="only_enabled_agent",  # 为 RouteDecision 设置关键字参数 reason_code，传入当前行给出的值
                resolved_query=query,  # 为 RouteDecision 设置关键字参数 resolved_query，传入当前行给出的值
            )  # 结束函数 route 的参数及返回类型声明并开始函数体

        rule_decision = self._rule_route(query)  # 计算 self._rule_route(query) 并保存到变量 rule_decision
        if rule_decision is not None:  # 判断分支条件：if rule_decision is not None:
            return rule_decision  # 返回 rule_decision 给调用方

        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            model_result = await self._model_route(  # 等待 _model_route 完成，并将其结果保存到 model_result
                query=query,  # 为 self._model_route 设置关键字参数 query，传入当前行给出的值
                history=history,  # 为 self._model_route 设置关键字参数 history，传入当前行给出的值
                allowed_agent_ids={agent.agent_id for agent in agents},  # 为 self._model_route 设置关键字参数 allowed_agent_ids，传入当前行给出的值
                llm=llm,  # 为 self._model_route 设置关键字参数 llm，传入当前行给出的值
            )  # 结束函数 route 的参数及返回类型声明并开始函数体
        except BudgetExceededError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except BudgetExceededError:
            raise  # 重新抛出当前异常，保留原始失败上下文
        except Exception:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception:
            return self._manual_decision(  # 返回 self._manual_decision( 给调用方
                query=query,  # 为 self._manual_decision 设置关键字参数 query，传入当前行给出的值
                agents=agents,  # 为 self._manual_decision 设置关键字参数 agents，传入当前行给出的值
                reason_code="router_failure",  # 为 self._manual_decision 设置关键字参数 reason_code，传入当前行给出的值
            )  # 结束函数 route 的参数及返回类型声明并开始函数体
        candidates = [  # 计算 [ 并保存到变量 candidates
            RouteCandidate(  # 调用 RouteCandidate 执行当前步骤：RouteCandidate(
                agent_id=model_result.agent_id,  # 为 RouteCandidate 设置关键字参数 agent_id，传入当前行给出的值
                confidence=model_result.confidence,  # 为 RouteCandidate 设置关键字参数 confidence，传入当前行给出的值
                reason=model_result.reason_code,  # 为 RouteCandidate 设置关键字参数 reason，传入当前行给出的值
            ),  # 结束函数 route 的参数及返回类型声明并开始函数体
            *model_result.alternatives,  # 向多行序列加入元素 *model_result.alternatives
        ]  # 结束上一处多行结构，保持表达式边界清晰
        allowed = {agent.agent_id for agent in agents}  # 计算 {agent.agent_id for agent in agents} 并保存到变量 allowed
        candidates = [item for item in candidates if item.agent_id in allowed]  # 计算 [item for item in candidates if item.agent_id in allowed] 并保存到变量 candidates
        if not candidates:  # 判断分支条件：if not candidates:
            return self._manual_decision(  # 返回 self._manual_decision( 给调用方
                query=query,  # 为 self._manual_decision 设置关键字参数 query，传入当前行给出的值
                agents=agents,  # 为 self._manual_decision 设置关键字参数 agents，传入当前行给出的值
                reason_code="invalid_model_route",  # 为 self._manual_decision 设置关键字参数 reason_code，传入当前行给出的值
            )  # 结束函数 route 的参数及返回类型声明并开始函数体
        by_id = {item.agent_id: item for item in candidates}  # 计算 {item.agent_id: item for item in candidates} 并保存到变量 by_id
        ordered = sorted(candidates, key=lambda item: item.confidence, reverse=True)  # 计算 sorted(candidates, key=lambda item: item.confidence, reverse=True) 并保存到变量 ordered
        best = ordered[0]  # 计算 ordered[0] 并保存到变量 best
        margin = best.confidence - (ordered[1].confidence if len(ordered) > 1 else 0)  # 计算 best.confidence - (ordered[1].confidence if len(ordered) > 1 else 0) 并保存到变量 margin
        if (  # 判断分支条件：if (
            best.confidence >= self.min_confidence  # 在函数 route 中执行表达式 best.confidence >= self.min_confidence，推进当前业务流程
            and margin >= self.min_margin  # 在函数 route 中执行表达式 and margin >= self.min_margin，推进当前业务流程
        ):  # 结束 route 的参数列表并声明返回类型
            return RouteDecision(  # 返回 RouteDecision( 给调用方
                selected_agent_id=best.agent_id,  # 为 RouteDecision 设置关键字参数 selected_agent_id，传入当前行给出的值
                mode=RouteMode.MODEL,  # 为 RouteDecision 设置关键字参数 mode，传入当前行给出的值
                confidence=best.confidence,  # 为 RouteDecision 设置关键字参数 confidence，传入当前行给出的值
                candidates=ordered,  # 为 RouteDecision 设置关键字参数 candidates，传入当前行给出的值
                reason_code=model_result.reason_code,  # 为 RouteDecision 设置关键字参数 reason_code，传入当前行给出的值
                resolved_query=model_result.resolved_query or query,  # 为 RouteDecision 设置关键字参数 resolved_query，传入当前行给出的值
            )  # 结束函数 route 的参数及返回类型声明并开始函数体
        return RouteDecision(  # 返回 RouteDecision( 给调用方
            selected_agent_id=None,  # 为 RouteDecision 设置关键字参数 selected_agent_id，传入当前行给出的值
            mode=RouteMode.MODEL,  # 为 RouteDecision 设置关键字参数 mode，传入当前行给出的值
            confidence=by_id[best.agent_id].confidence,  # 为 RouteDecision 设置关键字参数 confidence，传入当前行给出的值
            candidates=ordered,  # 为 RouteDecision 设置关键字参数 candidates，传入当前行给出的值
            reason_code="low_confidence",  # 为 RouteDecision 设置关键字参数 reason_code，传入当前行给出的值
            resolved_query=model_result.resolved_query or query,  # 为 RouteDecision 设置关键字参数 resolved_query，传入当前行给出的值
            requires_human=True,  # 为 RouteDecision 设置关键字参数 requires_human，传入当前行给出的值
        )  # 结束函数 route 的参数及返回类型声明并开始函数体

    def _rule_route(self, query: str) -> RouteDecision | None:  # 定义函数 _rule_route，封装该模块的一项明确职责
        has_data_intent = bool(DATA_INTENT.search(query))  # 计算 bool(DATA_INTENT.search(query)) 并保存到变量 has_data_intent
        has_catalog_intent = bool(CATALOG_INTENT.search(query))  # 计算 bool(CATALOG_INTENT.search(query)) 并保存到变量 has_catalog_intent
        if has_data_intent and not has_catalog_intent:  # 判断分支条件：if has_data_intent and not has_catalog_intent:
            return self._rule_decision("analytics_sql", query, "data_intent_rule")  # 返回 self._rule_decision("analytics_sql", query, "data_intent_rule") 给调用方
        if has_catalog_intent and not DATA_NOUN.search(query):  # 判断分支条件：if has_catalog_intent and not DATA_NOUN.search(query):
            return self._rule_decision("catalog_qa", query, "catalog_intent_rule")  # 返回 self._rule_decision("catalog_qa", query, "catalog_intent_rule") 给调用方
        if re.fullmatch(r"\s*(有哪些表|表结构|元数据)\s*[？?]?\s*", query):  # 判断分支条件：if re.fullmatch(r"\s*(有哪些表|表结构|元数据)\s*[？?]?\s*", query):
            return self._rule_decision("catalog_qa", query, "catalog_intent_rule")  # 返回 self._rule_decision("catalog_qa", query, "catalog_intent_rule") 给调用方
        return None  # 返回 None 给调用方

    def _rule_decision(  # 定义函数 _rule_decision，封装该模块的一项明确职责
        self, agent_id: str, query: str, reason: str  # 为函数 _rule_decision 声明参数 self, agent_id 及其类型或默认值
    ) -> RouteDecision | None:  # 结束 _rule_decision 的参数列表并声明返回类型
        if self.registry.try_get(agent_id) is None:  # 判断分支条件：if self.registry.try_get(agent_id) is None:
            return None  # 返回 None 给调用方
        return RouteDecision(  # 返回 RouteDecision( 给调用方
            selected_agent_id=agent_id,  # 为 RouteDecision 设置关键字参数 selected_agent_id，传入当前行给出的值
            mode=RouteMode.RULE,  # 为 RouteDecision 设置关键字参数 mode，传入当前行给出的值
            confidence=0.95,  # 为 RouteDecision 设置关键字参数 confidence，传入当前行给出的值
            candidates=[  # 为 RouteDecision 设置关键字参数 candidates，传入当前行给出的值
                RouteCandidate(  # 调用 RouteCandidate 执行当前步骤：RouteCandidate(
                    agent_id=agent_id,  # 为 RouteCandidate 设置关键字参数 agent_id，传入当前行给出的值
                    confidence=0.95,  # 为 RouteCandidate 设置关键字参数 confidence，传入当前行给出的值
                    reason=reason,  # 为 RouteCandidate 设置关键字参数 reason，传入当前行给出的值
                )  # 结束函数 _rule_decision 的参数及返回类型声明并开始函数体
            ],  # 结束上一处多行结构，保持表达式边界清晰
            reason_code=reason,  # 为 RouteDecision 设置关键字参数 reason_code，传入当前行给出的值
            resolved_query=query,  # 为 RouteDecision 设置关键字参数 resolved_query，传入当前行给出的值
        )  # 结束函数 _rule_decision 的参数及返回类型声明并开始函数体

    async def _model_route(  # 定义异步函数 _model_route，封装可被事件循环调度的协程逻辑
        self,  # 为函数 _model_route 声明参数 self 及其类型或默认值
        *,  # 为函数 _model_route 声明参数 * 及其类型或默认值
        query: str,  # 为函数 _model_route 声明参数 query 及其类型或默认值
        history: list[dict[str, str]],  # 为函数 _model_route 声明参数 history 及其类型或默认值
        allowed_agent_ids: set[str],  # 为函数 _model_route 声明参数 allowed_agent_ids 及其类型或默认值
        llm: RunLLM,  # 为函数 _model_route 声明参数 llm 及其类型或默认值
    ) -> RouterModelOutput:  # 结束 _model_route 的参数列表并声明返回类型
        agent_payload = [  # 计算 [ 并保存到变量 agent_payload
            self.registry.get(agent_id).public_view().model_dump()  # 调用 get 执行当前步骤：self.registry.get(agent_id).public_view().model_dump()
            for agent_id in sorted(allowed_agent_ids)  # 按迭代条件执行循环：for agent_id in sorted(allowed_agent_ids)
        ]  # 结束上一处多行结构，保持表达式边界清晰
        history_payload = [  # 计算 [ 并保存到变量 history_payload
            {"role": item.get("role", ""), "content": str(item.get("content", ""))[-1500:]}  # 调用 目标函数 执行当前步骤：{"role": item.get("role", ""), "content": str(item.get("content", ""))[…
            for item in history[-12:]  # 按迭代条件执行循环：for item in history[-12:]
        ]  # 结束上一处多行结构，保持表达式边界清晰
        prompt = PromptTemplate(  # 调用 PromptTemplate 构造结果并保存到 prompt
            template=load_prompt("agent_router"),  # 为 load_prompt 设置关键字参数 template，传入当前行给出的值
            input_variables=["agents", "history", "query"],  # 为 PromptTemplate 设置关键字参数 input_variables，传入当前行给出的值
        )  # 结束函数 _model_route 的参数及返回类型声明并开始函数体
        parser = JsonOutputParser(pydantic_object=RouterModelOutput)  # 计算 JsonOutputParser(pydantic_object=RouterModelOutput) 并保存到变量 parser
        chain = prompt | llm.model | parser  # 计算 prompt | llm.model | parser 并保存到变量 chain
        parsed = await llm.ainvoke(  # 等待 ainvoke 完成，并将其结果保存到 parsed
            chain,  # 继续向上一处调用或声明传入 chain
            {  # 在函数 _model_route 中执行表达式 {，推进当前业务流程
                "agents": json.dumps(agent_payload, ensure_ascii=False),  # 为多行字典定义键 "agents" 及其对应值
                "history": json.dumps(history_payload, ensure_ascii=False),  # 为多行字典定义键 "history" 及其对应值
                "query": query,  # 为多行字典定义键 "query" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
            name="agent_router",  # 为 llm.ainvoke 设置关键字参数 name，传入当前行给出的值
        )  # 结束函数 _model_route 的参数及返回类型声明并开始函数体
        result = RouterModelOutput.model_validate(parsed)  # 计算 RouterModelOutput.model_validate(parsed) 并保存到变量 result
        if result.agent_id not in allowed_agent_ids:  # 判断分支条件：if result.agent_id not in allowed_agent_ids:
            raise RouterError("router selected an unavailable agent")  # 抛出明确异常，阻止错误状态被静默接受：RouterError("router selected an unavailable agent")
        return result  # 返回 result 给调用方

    def _manual_decision(  # 定义函数 _manual_decision，封装该模块的一项明确职责
        self,  # 为函数 _manual_decision 声明参数 self 及其类型或默认值
        *,  # 为函数 _manual_decision 声明参数 * 及其类型或默认值
        query: str,  # 为函数 _manual_decision 声明参数 query 及其类型或默认值
        agents: list[Any],  # 为函数 _manual_decision 声明参数 agents 及其类型或默认值
        reason_code: str,  # 为函数 _manual_decision 声明参数 reason_code 及其类型或默认值
    ) -> RouteDecision:  # 结束 _manual_decision 的参数列表并声明返回类型
        return RouteDecision(  # 返回 RouteDecision( 给调用方
            selected_agent_id=None,  # 为 RouteDecision 设置关键字参数 selected_agent_id，传入当前行给出的值
            mode=RouteMode.MODEL,  # 为 RouteDecision 设置关键字参数 mode，传入当前行给出的值
            confidence=None,  # 为 RouteDecision 设置关键字参数 confidence，传入当前行给出的值
            candidates=[  # 为 RouteDecision 设置关键字参数 candidates，传入当前行给出的值
                RouteCandidate(  # 调用 RouteCandidate 执行当前步骤：RouteCandidate(
                    agent_id=agent.agent_id,  # 为 RouteCandidate 设置关键字参数 agent_id，传入当前行给出的值
                    confidence=0,  # 为 RouteCandidate 设置关键字参数 confidence，传入当前行给出的值
                    reason=agent.description,  # 为 RouteCandidate 设置关键字参数 reason，传入当前行给出的值
                )  # 结束函数 _manual_decision 的参数及返回类型声明并开始函数体
                for agent in agents  # 按迭代条件执行循环：for agent in agents
            ],  # 结束上一处多行结构，保持表达式边界清晰
            reason_code=reason_code,  # 为 RouteDecision 设置关键字参数 reason_code，传入当前行给出的值
            resolved_query=query,  # 为 RouteDecision 设置关键字参数 resolved_query，传入当前行给出的值
            requires_human=True,  # 为 RouteDecision 设置关键字参数 requires_human，传入当前行给出的值
        )  # 结束函数 _manual_decision 的参数及返回类型声明并开始函数体
