"""OpenTelemetry setup with optional Langfuse visualization."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import contextlib  # 导入contextlib，建立本模块需要的外部能力引用
from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用
from typing import Iterator  # 从 typing 导入 Iterator，供本模块后续代码使用

from fastapi import FastAPI  # 从 fastapi 导入 FastAPI，供本模块后续代码使用
from langfuse import Langfuse  # 从 langfuse 导入 Langfuse，供本模块后续代码使用
from langfuse.langchain import CallbackHandler  # 从 langfuse.langchain 导入 CallbackHandler，供本模块后续代码使用
from opentelemetry import context, metrics, propagate, trace  # 从 opentelemetry 导入 context, metrics, propagate, trace，供本模块后续代码使用
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # 从 opentelemetry.exporter.otlp.proto.http.trace_exporter 导入 OTLPSpanExporter，供本模块后续代码使用
from opentelemetry.exporter.prometheus import PrometheusMetricReader  # 从 opentelemetry.exporter.prometheus 导入 PrometheusMetricReader，供本模块后续代码使用
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # 从 opentelemetry.instrumentation.fastapi 导入 FastAPIInstrumentor，供本模块后续代码使用
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor  # 从 opentelemetry.instrumentation.httpx 导入 HTTPXClientInstrumentor，供本模块后续代码使用
from opentelemetry.instrumentation.redis import RedisInstrumentor  # 从 opentelemetry.instrumentation.redis 导入 RedisInstrumentor，供本模块后续代码使用
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor  # 从 opentelemetry.instrumentation.sqlalchemy 导入 SQLAlchemyInstrumentor，供本模块后续代码使用
from opentelemetry.sdk.metrics import MeterProvider  # 从 opentelemetry.sdk.metrics 导入 MeterProvider，供本模块后续代码使用
from opentelemetry.sdk.resources import Resource  # 从 opentelemetry.sdk.resources 导入 Resource，供本模块后续代码使用
from opentelemetry.sdk.trace import TracerProvider  # 从 opentelemetry.sdk.trace 导入 TracerProvider，供本模块后续代码使用
from opentelemetry.sdk.trace.export import BatchSpanProcessor  # 从 opentelemetry.sdk.trace.export 导入 BatchSpanProcessor，供本模块后续代码使用
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased  # 从 opentelemetry.sdk.trace.sampling 导入 ParentBased, TraceIdRatioBased，供本模块后续代码使用
from opentelemetry.trace import Status, StatusCode  # 从 opentelemetry.trace 导入 Status, StatusCode，供本模块后续代码使用
from prometheus_client import REGISTRY  # 从 prometheus_client 导入 REGISTRY，供本模块后续代码使用

from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class HarnessMetrics:  # 定义类 HarnessMetrics，组织相关状态与行为
    sse_active: object  # 声明或继续传入参数 sse_active: object
    runs_started: object  # 声明或继续传入参数 runs_started: object
    runs_finished: object  # 声明或继续传入参数 runs_finished: object
    run_duration: object  # 声明或继续传入参数 run_duration: object
    queue_claims: object  # 声明或继续传入参数 queue_claims: object
    llm_calls: object  # 声明或继续传入参数 llm_calls: object
    sql_duration: object  # 声明或继续传入参数 sql_duration: object
    route_selections: object  # 声明或继续传入参数 route_selections: object
    cache_events: object  # 声明或继续传入参数 cache_events: object


class Telemetry:  # 定义类 Telemetry，组织相关状态与行为
    def __init__(self, settings: Settings) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        self.settings = settings  # 将 settings 保存到实例属性 self.settings
        self._configured = False  # 将 False 保存到实例属性 self._configured
        self._tracer_provider: TracerProvider | None = None  # 将 None 保存到实例属性 self._tracer_provider
        self._meter_provider: MeterProvider | None = None  # 将 None 保存到实例属性 self._meter_provider
        self._prometheus_reader: PrometheusMetricReader | None = None  # 将 None 保存到实例属性 self._prometheus_reader
        self._langfuse: Langfuse | None = None  # 将 None 保存到实例属性 self._langfuse
        self._langfuse_tracer_provider: TracerProvider | None = None  # 将 None 保存到实例属性 self._langfuse_tracer_provider
        self.tracer = trace.get_tracer(__name__)  # 将 trace.get_tracer(__name__) 保存到实例属性 self.tracer
        self.metrics = self._build_noop_metrics()  # 将 self._build_noop_metrics() 保存到实例属性 self.metrics

    def setup(self) -> None:  # 定义函数 setup，封装该模块的一项明确职责
        if self._configured:  # 判断分支条件：if self._configured:
            return  # 提前返回空结果，结束当前函数调用
        resource = Resource.create(  # 调用 create 构造结果并保存到 resource
            {  # 在函数 setup 中执行表达式 {，推进当前业务流程
                "service.name": self.settings.otel_service_name,  # 为多行字典定义键 "service.name" 及其对应值
                "service.version": self.settings.app_version,  # 为多行字典定义键 "service.version" 及其对应值
                "deployment.environment.name": self.settings.environment,  # 为多行字典定义键 "deployment.environment.name" 及其对应值
            }  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束 Resource.create 调用参数，得到完整表达式结果
        if self.settings.otel_enabled:  # 判断分支条件：if self.settings.otel_enabled:
            provider = TracerProvider(  # 调用 TracerProvider 构造结果并保存到 provider
                resource=resource,  # 为 TracerProvider 设置关键字参数 resource，传入当前行给出的值
                sampler=ParentBased(  # 为 ParentBased 设置关键字参数 sampler，传入当前行给出的值
                    TraceIdRatioBased(self.settings.otel_sample_ratio)  # 调用 TraceIdRatioBased 执行当前步骤：TraceIdRatioBased(self.settings.otel_sample_ratio)
                ),  # 结束 ParentBased 调用参数，得到完整表达式结果
            )  # 结束 TracerProvider 调用参数，得到完整表达式结果
            endpoint = self.settings.otel_exporter_endpoint.rstrip("/")  # 计算 self.settings.otel_exporter_endpoint.rstrip("/") 并保存到变量 endpoint
            provider.add_span_processor(  # 调用 add_span_processor 执行当前步骤：provider.add_span_processor(
                BatchSpanProcessor(  # 调用 BatchSpanProcessor 执行当前步骤：BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"),  # 继续向上一处调用或声明传入 OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
                    max_queue_size=2048,  # 为 BatchSpanProcessor 设置关键字参数 max_queue_size，传入当前行给出的值
                    max_export_batch_size=256,  # 为 BatchSpanProcessor 设置关键字参数 max_export_batch_size，传入当前行给出的值
                )  # 结束 BatchSpanProcessor 调用参数，得到完整表达式结果
            )  # 结束 provider.add_span_processor 调用参数，得到完整表达式结果
            trace.set_tracer_provider(provider)  # 调用 set_tracer_provider 执行当前步骤：trace.set_tracer_provider(provider)
            self._tracer_provider = provider  # 将 provider 保存到实例属性 self._tracer_provider
            self.tracer = provider.get_tracer("app.harness")  # 将 provider.get_tracer("app.harness") 保存到实例属性 self.tracer

            self._prometheus_reader = PrometheusMetricReader(registry=REGISTRY)  # 将 PrometheusMetricReader(registry=REGISTRY) 保存到实例属性 self._prometheus_reader
            meter_provider = MeterProvider(  # 调用 MeterProvider 构造结果并保存到 meter_provider
                resource=resource,  # 为 MeterProvider 设置关键字参数 resource，传入当前行给出的值
                metric_readers=[self._prometheus_reader],  # 为 MeterProvider 设置关键字参数 metric_readers，传入当前行给出的值
            )  # 结束 MeterProvider 调用参数，得到完整表达式结果
            metrics.set_meter_provider(meter_provider)  # 调用 set_meter_provider 执行当前步骤：metrics.set_meter_provider(meter_provider)
            self._meter_provider = meter_provider  # 将 meter_provider 保存到实例属性 self._meter_provider
            meter = meter_provider.get_meter("app.harness")  # 计算 meter_provider.get_meter("app.harness") 并保存到变量 meter
            self.metrics = HarnessMetrics(  # 调用 HarnessMetrics 构造结果并保存到 self.metrics
                sse_active=meter.create_up_down_counter(  # 为 meter.create_up_down_counter 设置关键字参数 sse_active，传入当前行给出的值
                    "harness.sse.active", unit="{connection}"  # 在函数 setup 中执行表达式 "harness.sse.active", unit="{connection}"，推进当前业务流程
                ),  # 结束 meter.create_up_down_counter 调用参数，得到完整表达式结果
                runs_started=meter.create_counter(  # 为 meter.create_counter 设置关键字参数 runs_started，传入当前行给出的值
                    "harness.runs.started", unit="{run}"  # 在函数 setup 中执行表达式 "harness.runs.started", unit="{run}"，推进当前业务流程
                ),  # 结束 meter.create_counter 调用参数，得到完整表达式结果
                runs_finished=meter.create_counter(  # 为 meter.create_counter 设置关键字参数 runs_finished，传入当前行给出的值
                    "harness.runs.finished", unit="{run}"  # 在函数 setup 中执行表达式 "harness.runs.finished", unit="{run}"，推进当前业务流程
                ),  # 结束 meter.create_counter 调用参数，得到完整表达式结果
                run_duration=meter.create_histogram(  # 为 meter.create_histogram 设置关键字参数 run_duration，传入当前行给出的值
                    "harness.run.duration", unit="s"  # 在函数 setup 中执行表达式 "harness.run.duration", unit="s"，推进当前业务流程
                ),  # 结束 meter.create_histogram 调用参数，得到完整表达式结果
                queue_claims=meter.create_counter(  # 为 meter.create_counter 设置关键字参数 queue_claims，传入当前行给出的值
                    "harness.queue.claims", unit="{job}"  # 在函数 setup 中执行表达式 "harness.queue.claims", unit="{job}"，推进当前业务流程
                ),  # 结束 meter.create_counter 调用参数，得到完整表达式结果
                llm_calls=meter.create_counter(  # 为 meter.create_counter 设置关键字参数 llm_calls，传入当前行给出的值
                    "harness.llm.calls", unit="{call}"  # 在函数 setup 中执行表达式 "harness.llm.calls", unit="{call}"，推进当前业务流程
                ),  # 结束 meter.create_counter 调用参数，得到完整表达式结果
                sql_duration=meter.create_histogram(  # 为 meter.create_histogram 设置关键字参数 sql_duration，传入当前行给出的值
                    "harness.sql.duration", unit="s"  # 在函数 setup 中执行表达式 "harness.sql.duration", unit="s"，推进当前业务流程
                ),  # 结束 meter.create_histogram 调用参数，得到完整表达式结果
                route_selections=meter.create_counter(  # 为 meter.create_counter 设置关键字参数 route_selections，传入当前行给出的值
                    "harness.routes.selection", unit="{run}"  # 在函数 setup 中执行表达式 "harness.routes.selection", unit="{run}"，推进当前业务流程
                ),  # 结束 meter.create_counter 调用参数，得到完整表达式结果
                cache_events=meter.create_counter(  # 为 meter.create_counter 设置关键字参数 cache_events，传入当前行给出的值
                    "harness.cache.events", unit="{event}"  # 在函数 setup 中执行表达式 "harness.cache.events", unit="{event}"，推进当前业务流程
                ),  # 结束 meter.create_counter 调用参数，得到完整表达式结果
            )  # 结束 HarnessMetrics 调用参数，得到完整表达式结果

        if self.settings.langfuse_enabled:  # 判断分支条件：if self.settings.langfuse_enabled:
            self._langfuse_tracer_provider = TracerProvider(resource=resource)  # 将 TracerProvider(resource=resource) 保存到实例属性 self._langfuse_tracer_provider
            self._langfuse = Langfuse(  # 调用 Langfuse 构造结果并保存到 self._langfuse
                public_key=self.settings.langfuse_public_key.get_secret_value()  # 为 self.settings.langfuse_public_key.get_secret_value 设置关键字参数 public_key，传入当前行给出的值
                if self.settings.langfuse_public_key  # 判断分支条件：if self.settings.langfuse_public_key
                else None,  # 继续向上一处调用或声明传入 else None
                secret_key=self.settings.langfuse_secret_key.get_secret_value()  # 为 self.settings.langfuse_secret_key.get_secret_value 设置关键字参数 secret_key，传入当前行给出的值
                if self.settings.langfuse_secret_key  # 判断分支条件：if self.settings.langfuse_secret_key
                else None,  # 继续向上一处调用或声明传入 else None
                host=self.settings.langfuse_host,  # 为 Langfuse 设置关键字参数 host，传入当前行给出的值
                environment=self.settings.environment,  # 为 Langfuse 设置关键字参数 environment，传入当前行给出的值
                release=self.settings.app_version,  # 为 Langfuse 设置关键字参数 release，传入当前行给出的值
                tracing_enabled=True,  # 为 Langfuse 设置关键字参数 tracing_enabled，传入当前行给出的值
                tracer_provider=self._langfuse_tracer_provider,  # 为 Langfuse 设置关键字参数 tracer_provider，传入当前行给出的值
                mask=(  # 为 Langfuse 设置关键字参数 mask，传入当前行给出的值
                    None  # 在函数 setup 中执行表达式 None，推进当前业务流程
                    if self.settings.langfuse_capture_content  # 判断分支条件：if self.settings.langfuse_capture_content
                    else self._mask_langfuse_data  # 在函数 setup 中执行表达式 else self._mask_langfuse_data，推进当前业务流程
                ),  # 结束函数 setup 的调用或声明结构
            )  # 结束 Langfuse 调用参数，得到完整表达式结果
        self._configured = True  # 将 True 保存到实例属性 self._configured

    def instrument_app(self, app: FastAPI) -> None:  # 定义函数 instrument_app，封装该模块的一项明确职责
        if not self.settings.otel_enabled:  # 判断分支条件：if not self.settings.otel_enabled:
            return  # 提前返回空结果，结束当前函数调用
        FastAPIInstrumentor.instrument_app(  # 调用 instrument_app 执行当前步骤：FastAPIInstrumentor.instrument_app(
            app,  # 继续向上一处调用或声明传入 app
            tracer_provider=self._tracer_provider,  # 为 FastAPIInstrumentor.instrument_app 设置关键字参数 tracer_provider，传入当前行给出的值
            excluded_urls="health/live,health/ready,metrics",  # 为 FastAPIInstrumentor.instrument_app 设置关键字参数 excluded_urls，传入当前行给出的值
        )  # 结束 FastAPIInstrumentor.instrument_app 调用参数，得到完整表达式结果

    def instrument_engine(self, engine: object) -> None:  # 定义函数 instrument_engine，封装该模块的一项明确职责
        if self.settings.otel_enabled:  # 判断分支条件：if self.settings.otel_enabled:
            SQLAlchemyInstrumentor().instrument(  # 调用 SQLAlchemyInstrumentor 执行当前步骤：SQLAlchemyInstrumentor().instrument(
                engine=engine,  # 为 instrument 设置关键字参数 engine，传入当前行给出的值
                tracer_provider=self._tracer_provider,  # 为 instrument 设置关键字参数 tracer_provider，传入当前行给出的值
            )  # 结束 instrument 调用参数，得到完整表达式结果
            HTTPXClientInstrumentor().instrument(  # 调用 HTTPXClientInstrumentor 执行当前步骤：HTTPXClientInstrumentor().instrument(
                tracer_provider=self._tracer_provider  # 为 instrument 设置关键字参数 tracer_provider，传入当前行给出的值
            )  # 结束 instrument 调用参数，得到完整表达式结果
            RedisInstrumentor().instrument(tracer_provider=self._tracer_provider)  # 调用 RedisInstrumentor 执行当前步骤：RedisInstrumentor().instrument(tracer_provider=self._tracer_provider)

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def langfuse_enabled(self) -> bool:  # 定义函数 langfuse_enabled，封装该模块的一项明确职责
        return self._langfuse is not None  # 返回 self._langfuse is not None 给调用方

    def langchain_callback(self, trace_id: str | None = None) -> CallbackHandler | None:  # 定义函数 langchain_callback，封装该模块的一项明确职责
        if not self.settings.langfuse_enabled:  # 判断分支条件：if not self.settings.langfuse_enabled:
            return None  # 返回 None 给调用方
        trace_context = {"trace_id": trace_id} if trace_id else None  # 计算 {"trace_id": trace_id} if trace_id else None 并保存到变量 trace_context
        return CallbackHandler(trace_context=trace_context)  # 返回 CallbackHandler(trace_context=trace_context) 给调用方

    @contextlib.contextmanager  # 应用装饰器 contextlib.contextmanager，为紧随其后的定义附加框架行为
    def activate_traceparent(  # 定义函数 activate_traceparent，封装该模块的一项明确职责
        self, traceparent: str | None, tracestate: str | None = None  # 为函数 activate_traceparent 声明参数 self, traceparent 及其类型或默认值
    ) -> Iterator[None]:  # 结束 activate_traceparent 的参数列表并声明返回类型
        carrier: dict[str, str] = {}  # 计算 {} 并保存到变量 carrier
        if traceparent:  # 判断分支条件：if traceparent:
            carrier["traceparent"] = traceparent  # 计算 traceparent 并保存到变量 carrier["traceparent"]
        if tracestate:  # 判断分支条件：if tracestate:
            carrier["tracestate"] = tracestate  # 计算 tracestate 并保存到变量 carrier["tracestate"]
        token = context.attach(propagate.extract(carrier))  # 计算 context.attach(propagate.extract(carrier)) 并保存到变量 token
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            yield  # 产出流式结果 ，保留生成器后续执行状态
        finally:  # 进入无论成功失败都必须执行的资源清理分支
            context.detach(token)  # 调用 detach 执行当前步骤：context.detach(token)

    def capture_traceparent(self) -> str | None:  # 定义函数 capture_traceparent，封装该模块的一项明确职责
        carrier: dict[str, str] = {}  # 计算 {} 并保存到变量 carrier
        propagate.inject(carrier)  # 调用 inject 执行当前步骤：propagate.inject(carrier)
        return carrier.get("traceparent")  # 返回 carrier.get("traceparent") 给调用方

    def current_trace_id(self) -> str | None:  # 定义函数 current_trace_id，封装该模块的一项明确职责
        span_context = trace.get_current_span().get_span_context()  # 计算 trace.get_current_span().get_span_context() 并保存到变量 span_context
        if not span_context.is_valid:  # 判断分支条件：if not span_context.is_valid:
            return None  # 返回 None 给调用方
        return format(span_context.trace_id, "032x")  # 返回 format(span_context.trace_id, "032x") 给调用方

    def flush(self) -> None:  # 定义函数 flush，封装该模块的一项明确职责
        if self._tracer_provider:  # 判断分支条件：if self._tracer_provider:
            self._tracer_provider.force_flush(timeout_millis=5000)  # 调用 force_flush 执行当前步骤：self._tracer_provider.force_flush(timeout_millis=5000)
        if self._meter_provider:  # 判断分支条件：if self._meter_provider:
            self._meter_provider.force_flush(timeout_millis=5000)  # 调用 force_flush 执行当前步骤：self._meter_provider.force_flush(timeout_millis=5000)
        if self._langfuse:  # 判断分支条件：if self._langfuse:
            self._langfuse.flush()  # 调用 flush 执行当前步骤：self._langfuse.flush()

    def shutdown(self) -> None:  # 定义函数 shutdown，封装该模块的一项明确职责
        self.flush()  # 调用 flush 执行当前步骤：self.flush()
        if self._langfuse:  # 判断分支条件：if self._langfuse:
            self._langfuse.shutdown()  # 调用 shutdown 执行当前步骤：self._langfuse.shutdown()
        if self._langfuse_tracer_provider:  # 判断分支条件：if self._langfuse_tracer_provider:
            self._langfuse_tracer_provider.shutdown()  # 调用 shutdown 执行当前步骤：self._langfuse_tracer_provider.shutdown()
        if self._meter_provider:  # 判断分支条件：if self._meter_provider:
            self._meter_provider.shutdown()  # 调用 shutdown 执行当前步骤：self._meter_provider.shutdown()
        if self._tracer_provider:  # 判断分支条件：if self._tracer_provider:
            self._tracer_provider.shutdown()  # 调用 shutdown 执行当前步骤：self._tracer_provider.shutdown()

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def record_exception(span: trace.Span, exc: BaseException) -> None:  # 定义函数 record_exception，封装该模块的一项明确职责
        span.record_exception(exc)  # 调用 record_exception 执行当前步骤：span.record_exception(exc)
        span.set_status(Status(StatusCode.ERROR, str(exc)[:500]))  # 调用 set_status 执行当前步骤：span.set_status(Status(StatusCode.ERROR, str(exc)[:500]))

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def _mask_langfuse_data(data: object) -> object:  # 定义函数 _mask_langfuse_data，封装该模块的一项明确职责
        if isinstance(data, dict):  # 判断分支条件：if isinstance(data, dict):
            return {  # 返回 { 给调用方
                key: (  # 声明或继续传入参数 key: (
                    "[REDACTED]"  # 在函数 _mask_langfuse_data 中执行表达式 "[REDACTED]"，推进当前业务流程
                    if str(key).lower()  # 判断分支条件：if str(key).lower()
                    in {  # 在函数 _mask_langfuse_data 中执行表达式 in {，推进当前业务流程
                        "query",  # 向多行序列加入元素 "query"
                        "sql",  # 向多行序列加入元素 "sql"
                        "input",  # 向多行序列加入元素 "input"
                        "output",  # 向多行序列加入元素 "output"
                        "content",  # 向多行序列加入元素 "content"
                        "messages",  # 向多行序列加入元素 "messages"
                        "rows",  # 向多行序列加入元素 "rows"
                        "result",  # 向多行序列加入元素 "result"
                        "authorization",  # 向多行序列加入元素 "authorization"
                        "token",  # 向多行序列加入元素 "token"
                        "api_key",  # 向多行序列加入元素 "api_key"
                    }  # 结束上一处多行结构，保持表达式边界清晰
                    else Telemetry._mask_langfuse_data(value)  # 调用 目标函数 执行当前步骤：else Telemetry._mask_langfuse_data(value)
                )  # 结束函数 _mask_langfuse_data 的调用或声明结构
                for key, value in data.items()  # 按迭代条件执行循环：for key, value in data.items()
            }  # 结束上一处多行结构，保持表达式边界清晰
        if isinstance(data, list):  # 判断分支条件：if isinstance(data, list):
            return [Telemetry._mask_langfuse_data(item) for item in data]  # 返回 [Telemetry._mask_langfuse_data(item) for item in data] 给调用方
        return data  # 返回 data 给调用方

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def _build_noop_metrics() -> HarnessMetrics:  # 定义函数 _build_noop_metrics，封装该模块的一项明确职责
        meter = metrics.get_meter("app.harness.disabled")  # 计算 metrics.get_meter("app.harness.disabled") 并保存到变量 meter
        return HarnessMetrics(  # 返回 HarnessMetrics( 给调用方
            sse_active=meter.create_up_down_counter("harness.disabled.sse"),  # 为 meter.create_up_down_counter 设置关键字参数 sse_active，传入当前行给出的值
            runs_started=meter.create_counter("harness.disabled.started"),  # 为 meter.create_counter 设置关键字参数 runs_started，传入当前行给出的值
            runs_finished=meter.create_counter("harness.disabled.finished"),  # 为 meter.create_counter 设置关键字参数 runs_finished，传入当前行给出的值
            run_duration=meter.create_histogram("harness.disabled.duration"),  # 为 meter.create_histogram 设置关键字参数 run_duration，传入当前行给出的值
            queue_claims=meter.create_counter("harness.disabled.claims"),  # 为 meter.create_counter 设置关键字参数 queue_claims，传入当前行给出的值
            llm_calls=meter.create_counter("harness.disabled.llm"),  # 为 meter.create_counter 设置关键字参数 llm_calls，传入当前行给出的值
            sql_duration=meter.create_histogram("harness.disabled.sql"),  # 为 meter.create_histogram 设置关键字参数 sql_duration，传入当前行给出的值
            route_selections=meter.create_counter("harness.disabled.routes"),  # 为 meter.create_counter 设置关键字参数 route_selections，传入当前行给出的值
            cache_events=meter.create_counter("harness.disabled.cache"),  # 为 meter.create_counter 设置关键字参数 cache_events，传入当前行给出的值
        )  # 结束 HarnessMetrics 调用参数，得到完整表达式结果
