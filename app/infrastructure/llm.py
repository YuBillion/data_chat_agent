"""Centralized chat-model construction and budget-aware invocation."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用

from langchain.chat_models import init_chat_model  # 从 langchain.chat_models 导入 init_chat_model，供本模块后续代码使用
from langchain_core.callbacks import UsageMetadataCallbackHandler  # 从 langchain_core.callbacks 导入 UsageMetadataCallbackHandler，供本模块后续代码使用
from langchain_core.runnables import Runnable  # 从 langchain_core.runnables 导入 Runnable，供本模块后续代码使用

from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.harness.types import RunBudget  # 从 app.harness.types 导入 RunBudget，供本模块后续代码使用
from app.observability.telemetry import Telemetry  # 从 app.observability.telemetry 导入 Telemetry，供本模块后续代码使用


class ChatModelFactory:  # 定义类 ChatModelFactory，组织相关状态与行为
    def __init__(self, settings: Settings) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        if (  # 判断分支条件：if (
            settings.llm_api_key is None  # 在函数 __init__ 中执行表达式 settings.llm_api_key is None，推进当前业务流程
            or not settings.llm_api_key.get_secret_value().strip()  # 调用 目标函数 执行当前步骤：or not settings.llm_api_key.get_secret_value().strip()
        ):  # 结束 __init__ 的参数列表并声明返回类型
            raise ValueError("LLM_API_KEY is required")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("LLM_API_KEY is required")
        self.settings = settings  # 将 settings 保存到实例属性 self.settings
        self._semaphore = asyncio.Semaphore(settings.llm_max_concurrency)  # 将 asyncio.Semaphore(settings.llm_max_concurrency) 保存到实例属性 self._semaphore
        self.model = init_chat_model(  # 调用 init_chat_model 构造结果并保存到 self.model
            model=settings.llm_model_name,  # 为 init_chat_model 设置关键字参数 model，传入当前行给出的值
            model_provider="openai",  # 为 init_chat_model 设置关键字参数 model_provider，传入当前行给出的值
            base_url=settings.llm_base_url,  # 为 init_chat_model 设置关键字参数 base_url，传入当前行给出的值
            api_key=settings.llm_api_key.get_secret_value(),  # 为 settings.llm_api_key.get_secret_value 设置关键字参数 api_key，传入当前行给出的值
            temperature=0,  # 为 init_chat_model 设置关键字参数 temperature，传入当前行给出的值
            timeout=settings.llm_timeout_seconds,  # 为 init_chat_model 设置关键字参数 timeout，传入当前行给出的值
            max_retries=0,  # 为 init_chat_model 设置关键字参数 max_retries，传入当前行给出的值
        )  # 结束 init_chat_model 调用参数，得到完整表达式结果

    def bind(  # 定义函数 bind，封装该模块的一项明确职责
        self,  # 为函数 bind 声明参数 self 及其类型或默认值
        *,  # 为函数 bind 声明参数 * 及其类型或默认值
        budget: RunBudget,  # 为函数 bind 声明参数 budget 及其类型或默认值
        telemetry: Telemetry,  # 为函数 bind 声明参数 telemetry 及其类型或默认值
        trace_id: str | None,  # 为函数 bind 声明参数 trace_id 及其类型或默认值
        agent_id: str,  # 为函数 bind 声明参数 agent_id 及其类型或默认值
        run_id: str,  # 为函数 bind 声明参数 run_id 及其类型或默认值
    ) -> "RunLLM":  # 结束 bind 的参数列表并声明返回类型
        return RunLLM(  # 返回 RunLLM( 给调用方
            model=self.model,  # 为 RunLLM 设置关键字参数 model，传入当前行给出的值
            semaphore=self._semaphore,  # 为 RunLLM 设置关键字参数 semaphore，传入当前行给出的值
            timeout_seconds=self.settings.llm_timeout_seconds,  # 为 RunLLM 设置关键字参数 timeout_seconds，传入当前行给出的值
            budget=budget,  # 为 RunLLM 设置关键字参数 budget，传入当前行给出的值
            telemetry=telemetry,  # 为 RunLLM 设置关键字参数 telemetry，传入当前行给出的值
            trace_id=trace_id,  # 为 RunLLM 设置关键字参数 trace_id，传入当前行给出的值
            agent_id=agent_id,  # 为 RunLLM 设置关键字参数 agent_id，传入当前行给出的值
            run_id=run_id,  # 为 RunLLM 设置关键字参数 run_id，传入当前行给出的值
        )  # 结束 RunLLM 调用参数，得到完整表达式结果


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class RunLLM:  # 定义类 RunLLM，组织相关状态与行为
    model: Any  # 声明或继续传入参数 model: Any
    semaphore: asyncio.Semaphore  # 声明或继续传入参数 semaphore: asyncio.Semaphore
    timeout_seconds: float  # 声明或继续传入参数 timeout_seconds: float
    budget: RunBudget  # 声明或继续传入参数 budget: RunBudget
    telemetry: Telemetry  # 声明或继续传入参数 telemetry: Telemetry
    trace_id: str | None  # 声明或继续传入参数 trace_id: str | None
    agent_id: str  # 声明或继续传入参数 agent_id: str
    run_id: str  # 声明或继续传入参数 run_id: str

    async def ainvoke(  # 定义异步函数 ainvoke，封装可被事件循环调度的协程逻辑
        self,  # 为函数 ainvoke 声明参数 self 及其类型或默认值
        runnable: Runnable,  # 为函数 ainvoke 声明参数 runnable 及其类型或默认值
        value: Any,  # 为函数 ainvoke 声明参数 value 及其类型或默认值
        *,  # 为函数 ainvoke 声明参数 * 及其类型或默认值
        name: str,  # 为函数 ainvoke 声明参数 name 及其类型或默认值
    ) -> Any:  # 结束 ainvoke 的参数列表并声明返回类型
        self.budget.before_llm_call()  # 调用 before_llm_call 执行当前步骤：self.budget.before_llm_call()
        usage = UsageMetadataCallbackHandler()  # 计算 UsageMetadataCallbackHandler() 并保存到变量 usage
        callbacks: list[Any] = [usage]  # 计算 [usage] 并保存到变量 callbacks
        langfuse_callback = self.telemetry.langchain_callback(self.trace_id)  # 计算 self.telemetry.langchain_callback(self.trace_id) 并保存到变量 langfuse_callback
        if langfuse_callback is not None:  # 判断分支条件：if langfuse_callback is not None:
            callbacks.append(langfuse_callback)  # 调用 append 执行当前步骤：callbacks.append(langfuse_callback)
        config = {  # 计算 { 并保存到变量 config
            "callbacks": callbacks,  # 为多行字典定义键 "callbacks" 及其对应值
            "run_name": name,  # 为多行字典定义键 "run_name" 及其对应值
            "metadata": {  # 为多行字典定义键 "metadata" 及其对应值
                "agent_id": self.agent_id,  # 为多行字典定义键 "agent_id" 及其对应值
                "run_id": self.run_id,  # 为多行字典定义键 "run_id" 及其对应值
                "llm_call": self.budget.snapshot.llm_calls + 1,  # 为多行字典定义键 "llm_call" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        }  # 结束上一处多行结构，保持表达式边界清晰
        with self.telemetry.tracer.start_as_current_span(  # 进入受管理的上下文 with self.telemetry.tracer.start_as_current_span(，确保资源正确获取与释放
            f"llm.{name}",  # 继续向上一处调用或声明传入 f"llm.{name}"
            attributes={  # 为 self.telemetry.tracer.start_as_current_span 设置关键字参数 attributes，传入当前行给出的值
                "agent.id": self.agent_id,  # 为多行字典定义键 "agent.id" 及其对应值
                "run.id": self.run_id,  # 为多行字典定义键 "run.id" 及其对应值
                "llm.call_index": self.budget.snapshot.llm_calls + 1,  # 为多行字典定义键 "llm.call_index" 及其对应值
            },  # 结束上一处多行结构，保持表达式边界清晰
        ) as span:  # 在函数 ainvoke 中执行表达式 ) as span:，推进当前业务流程
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                async with self.semaphore:  # 进入受管理的上下文 async with self.semaphore:，确保资源正确获取与释放
                    async with asyncio.timeout(self.timeout_seconds):  # 进入受管理的上下文 async with asyncio.timeout(self.timeout_seconds):，确保资源正确获取与释放
                        result = await runnable.ainvoke(value, config=config)  # 等待 ainvoke 完成，并将其结果保存到 result
            except TimeoutError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except TimeoutError:
                self.telemetry.record_exception(span, TimeoutError("LLM timed out"))  # 调用 record_exception 执行当前步骤：self.telemetry.record_exception(span, TimeoutError("LLM timed out"))
                raise  # 重新抛出当前异常，保留原始失败上下文
            except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
                self.telemetry.record_exception(span, exc)  # 调用 record_exception 执行当前步骤：self.telemetry.record_exception(span, exc)
                raise  # 重新抛出当前异常，保留原始失败上下文
            input_tokens, output_tokens = _usage_totals(usage)  # 计算 _usage_totals(usage) 并保存到变量 input_tokens, output_tokens
            self.budget.record_llm_call(input_tokens, output_tokens)  # 调用 record_llm_call 执行当前步骤：self.budget.record_llm_call(input_tokens, output_tokens)
            self.telemetry.metrics.llm_calls.add(  # 调用 add 执行当前步骤：self.telemetry.metrics.llm_calls.add(
                1,  # 继续向上一处调用或声明传入 1
                {  # 在函数 ainvoke 中执行表达式 {，推进当前业务流程
                    "agent_id": self.agent_id,  # 为多行字典定义键 "agent_id" 及其对应值
                    "input_tokens_bucket": _token_bucket(input_tokens),  # 为多行字典定义键 "input_tokens_bucket" 及其对应值
                    "output_tokens_bucket": _token_bucket(output_tokens),  # 为多行字典定义键 "output_tokens_bucket" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束 self.telemetry.metrics.llm_calls.add 调用参数，得到完整表达式结果
            span.set_attribute("llm.input_tokens", input_tokens)  # 调用 set_attribute 执行当前步骤：span.set_attribute("llm.input_tokens", input_tokens)
            span.set_attribute("llm.output_tokens", output_tokens)  # 调用 set_attribute 执行当前步骤：span.set_attribute("llm.output_tokens", output_tokens)
            return result  # 返回 result 给调用方


def _usage_totals(handler: UsageMetadataCallbackHandler) -> tuple[int, int]:  # 定义函数 _usage_totals，封装该模块的一项明确职责
    input_tokens = 0  # 计算 0 并保存到变量 input_tokens
    output_tokens = 0  # 计算 0 并保存到变量 output_tokens
    for metadata in handler.usage_metadata.values():  # 按迭代条件执行循环：for metadata in handler.usage_metadata.values():
        if not isinstance(metadata, dict):  # 判断分支条件：if not isinstance(metadata, dict):
            continue  # 跳过本轮剩余逻辑并进入下一轮迭代
        input_tokens += int(metadata.get("input_tokens", 0) or 0)  # 计算 int(metadata.get("input_tokens", 0) or 0) 并保存到变量 input_tokens +
        output_tokens += int(metadata.get("output_tokens", 0) or 0)  # 计算 int(metadata.get("output_tokens", 0) or 0) 并保存到变量 output_tokens +
    return input_tokens, output_tokens  # 返回 input_tokens, output_tokens 给调用方


def _token_bucket(tokens: int) -> str:  # 定义函数 _token_bucket，封装该模块的一项明确职责
    if tokens < 1000:  # 判断分支条件：if tokens < 1000:
        return "lt_1k"  # 返回 "lt_1k" 给调用方
    if tokens < 10_000:  # 判断分支条件：if tokens < 10_000:
        return "lt_10k"  # 返回 "lt_10k" 给调用方
    return "gte_10k"  # 返回 "gte_10k" 给调用方
