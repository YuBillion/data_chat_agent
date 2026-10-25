"""Durable event ledger with Redis real-time fan-out."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from app.harness.redis_runtime import RedisRuntime  # 从 app.harness.redis_runtime 导入 RedisRuntime，供本模块后续代码使用
from app.harness.store import HarnessStore  # 从 app.harness.store 导入 HarnessStore，供本模块后续代码使用
from app.harness.types import EventEnvelope, utc_now  # 从 app.harness.types 导入 EventEnvelope, utc_now，供本模块后续代码使用
from app.observability.telemetry import Telemetry  # 从 app.observability.telemetry 导入 Telemetry，供本模块后续代码使用


class EventPublisher:  # 定义类 EventPublisher，组织相关状态与行为
    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        store: HarnessStore,  # 为函数 __init__ 声明参数 store 及其类型或默认值
        redis: RedisRuntime,  # 为函数 __init__ 声明参数 redis 及其类型或默认值
        telemetry: Telemetry,  # 为函数 __init__ 声明参数 telemetry 及其类型或默认值
    ) -> None:  # 结束 __init__ 的参数列表并声明返回类型
        self.store = store  # 将依赖或状态 store 保存到实例属性 self.store
        self.redis = redis  # 将依赖或状态 redis 保存到实例属性 self.redis
        self.telemetry = telemetry  # 将依赖或状态 telemetry 保存到实例属性 self.telemetry

    async def publish(  # 定义异步函数 publish，封装可被事件循环调度的协程逻辑
        self,  # 为函数 publish 声明参数 self 及其类型或默认值
        run_id: UUID,  # 为函数 publish 声明参数 run_id 及其类型或默认值
        event_type: str,  # 为函数 publish 声明参数 event_type 及其类型或默认值
        payload: dict[str, Any],  # 为函数 publish 声明参数 payload 及其类型或默认值
        *,  # 为函数 publish 声明参数 * 及其类型或默认值
        trace_id: str | None = None,  # 为函数 publish 声明参数 trace_id 及其类型或默认值
    ) -> EventEnvelope:  # 结束 publish 的参数列表并声明返回类型
        record = await self.store.append_event(  # 等待 append_event 完成，并将其结果保存到 record
            run_id,  # 继续向上一处调用或声明传入 run_id
            event_type=event_type,  # 为 self.store.append_event 设置关键字参数 event_type，传入当前行给出的值
            payload=payload,  # 为 self.store.append_event 设置关键字参数 payload，传入当前行给出的值
            trace_id=trace_id or self.telemetry.current_trace_id(),  # 为 self.telemetry.current_trace_id 设置关键字参数 trace_id，传入当前行给出的值
        )  # 结束函数 publish 的参数及返回类型声明并开始函数体
        envelope = EventEnvelope(  # 调用 EventEnvelope 构造结果并保存到 envelope
            run_id=run_id,  # 为 EventEnvelope 设置关键字参数 run_id，传入当前行给出的值
            seq=record.seq,  # 为 EventEnvelope 设置关键字参数 seq，传入当前行给出的值
            trace_id=record.trace_id,  # 为 EventEnvelope 设置关键字参数 trace_id，传入当前行给出的值
            occurred_at=record.created_at or utc_now(),  # 为 utc_now 设置关键字参数 occurred_at，传入当前行给出的值
            event_type=record.event_type,  # 为 EventEnvelope 设置关键字参数 event_type，传入当前行给出的值
            payload=record.payload,  # 为 EventEnvelope 设置关键字参数 payload，传入当前行给出的值
        )  # 结束函数 publish 的参数及返回类型声明并开始函数体
        await self.redis.publish_event(envelope)  # 等待异步操作完成并取得结果：self.redis.publish_event(envelope)
        return envelope  # 返回 envelope 给调用方

    async def replay(  # 定义异步函数 replay，封装可被事件循环调度的协程逻辑
        self, run_id: UUID, *, after_seq: int, limit: int = 500  # 为函数 replay 声明参数 self, run_id 及其类型或默认值
    ) -> list[EventEnvelope]:  # 结束 replay 的参数列表并声明返回类型
        cached = await self.redis.read_events(  # 等待 read_events 完成，并将其结果保存到 cached
            run_id, after_seq=after_seq, limit=limit  # 在函数 replay 中执行表达式 run_id, after_seq=after_seq, limit=limit，推进当前业务流程
        )  # 结束函数 replay 的参数及返回类型声明并开始函数体
        records = await self.store.list_events(  # 等待 list_events 完成，并将其结果保存到 records
            run_id, after_seq=after_seq, limit=limit  # 在函数 replay 中执行表达式 run_id, after_seq=after_seq, limit=limit，推进当前业务流程
        )  # 结束函数 replay 的参数及返回类型声明并开始函数体
        durable = [  # 计算 [ 并保存到变量 durable
            EventEnvelope(  # 调用 EventEnvelope 执行当前步骤：EventEnvelope(
                run_id=record.run_id,  # 为 EventEnvelope 设置关键字参数 run_id，传入当前行给出的值
                seq=record.seq,  # 为 EventEnvelope 设置关键字参数 seq，传入当前行给出的值
                trace_id=record.trace_id,  # 为 EventEnvelope 设置关键字参数 trace_id，传入当前行给出的值
                occurred_at=record.created_at,  # 为 EventEnvelope 设置关键字参数 occurred_at，传入当前行给出的值
                event_type=record.event_type,  # 为 EventEnvelope 设置关键字参数 event_type，传入当前行给出的值
                payload=record.payload,  # 为 EventEnvelope 设置关键字参数 payload，传入当前行给出的值
            )  # 结束函数 replay 的参数及返回类型声明并开始函数体
            for record in records  # 按迭代条件执行循环：for record in records
        ]  # 结束上一处多行结构，保持表达式边界清晰
        by_seq = {event.seq: event for event in durable}  # 计算 {event.seq: event for event in durable} 并保存到变量 by_seq
        for event in cached:  # 按迭代条件执行循环：for event in cached:
            by_seq.setdefault(event.seq, event)  # 调用 setdefault 执行当前步骤：by_seq.setdefault(event.seq, event)
        return sorted(by_seq.values(), key=lambda event: event.seq)[:limit]  # 返回 sorted(by_seq.values(), key=lambda event: event.seq)[:limit] 给调用方


def format_sse(event: EventEnvelope) -> str:  # 定义函数 format_sse，封装该模块的一项明确职责
    data = event.model_dump(mode="json")  # 计算 event.model_dump(mode="json") 并保存到变量 data
    return (  # 返回 ( 给调用方
        f"id: {event.seq}\n"  # 在函数 format_sse 中执行表达式 f"id: {event.seq}\n"，推进当前业务流程
        f"event: {event.event_type}\n"  # 在函数 format_sse 中执行表达式 f"event: {event.event_type}\n"，推进当前业务流程
        f"data: {_json_dumps(data)}\n\n"  # 调用 目标函数 执行当前步骤：f"data: {_json_dumps(data)}\n\n"
    )  # 结束函数 format_sse 的参数及返回类型声明并开始函数体


def _json_dumps(data: dict[str, Any]) -> str:  # 定义函数 _json_dumps，封装该模块的一项明确职责
    import json  # 导入json，建立本模块需要的外部能力引用

    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)  # 返回 json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str) 给调用方
