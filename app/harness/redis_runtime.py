"""Redis-backed hot session cache, event fan-out, and distributed rate limits."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import json  # 导入json，建立本模块需要的外部能力引用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from redis import RedisError  # 从 redis 导入 RedisError，供本模块后续代码使用
from redis.asyncio import Redis  # 从 redis.asyncio 导入 Redis，供本模块后续代码使用

from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用
from app.harness.types import EventEnvelope  # 从 app.harness.types 导入 EventEnvelope，供本模块后续代码使用


class RedisRuntime:  # 定义类 RedisRuntime，组织相关状态与行为
    def __init__(self, settings: Settings, client: Redis | None = None) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        self.settings = settings  # 将依赖或状态 settings 保存到实例属性 self.settings
        self.client = client or Redis.from_url(  # 将依赖或状态 client or Redis.from_url( 保存到实例属性 self.client
            settings.redis_url,  # 继续向上一处调用或声明传入 settings.redis_url
            max_connections=settings.redis_pool_max_connections,  # 为 Redis.from_url 设置关键字参数 max_connections，传入当前行给出的值
            decode_responses=True,  # 为 Redis.from_url 设置关键字参数 decode_responses，传入当前行给出的值
            socket_connect_timeout=5,  # 为 Redis.from_url 设置关键字参数 socket_connect_timeout，传入当前行给出的值
            socket_timeout=5,  # 为 Redis.from_url 设置关键字参数 socket_timeout，传入当前行给出的值
            health_check_interval=30,  # 为 Redis.from_url 设置关键字参数 health_check_interval，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体

    async def ping(self) -> None:  # 定义异步函数 ping，封装可被事件循环调度的协程逻辑
        await self.client.ping()  # 等待异步操作完成并取得结果：self.client.ping()

    async def close(self) -> None:  # 定义异步函数 close，封装可被事件循环调度的协程逻辑
        await self.client.aclose()  # 等待异步操作完成并取得结果：self.client.aclose()

    async def get_session_snapshot(  # 定义异步函数 get_session_snapshot，封装可被事件循环调度的协程逻辑
        self, tenant_id: str, session_id: UUID  # 为函数 get_session_snapshot 声明参数 self, tenant_id 及其类型或默认值
    ) -> dict[str, Any] | None:  # 结束 get_session_snapshot 的参数列表并声明返回类型
        key = self._session_key(tenant_id, session_id)  # 计算 self._session_key(tenant_id, session_id) 并保存到变量 key
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            raw = await self.client.get(key)  # 等待 get 完成，并将其结果保存到 raw
            if raw:  # 判断分支条件：if raw:
                return json.loads(raw)  # 返回 json.loads(raw) 给调用方
        except (RedisError, ValueError) as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except (RedisError, ValueError) as exc:
            logger.warning("Redis session cache read failed: {}", type(exc).__name__)  # 调用 warning 执行当前步骤：logger.warning("Redis session cache read failed: {}", type(exc).__name_…
        return None  # 返回 None 给调用方

    async def set_session_snapshot(  # 定义异步函数 set_session_snapshot，封装可被事件循环调度的协程逻辑
        self,  # 为函数 set_session_snapshot 声明参数 self 及其类型或默认值
        tenant_id: str,  # 为函数 set_session_snapshot 声明参数 tenant_id 及其类型或默认值
        session_id: UUID,  # 为函数 set_session_snapshot 声明参数 session_id 及其类型或默认值
        snapshot: dict[str, Any],  # 为函数 set_session_snapshot 声明参数 snapshot 及其类型或默认值
        *,  # 为函数 set_session_snapshot 声明参数 * 及其类型或默认值
        revision: int | None = None,  # 为函数 set_session_snapshot 声明参数 revision 及其类型或默认值
    ) -> None:  # 结束 set_session_snapshot 的参数列表并声明返回类型
        if revision is not None:  # 判断分支条件：if revision is not None:
            snapshot = {**snapshot, "revision": revision}  # 计算 {**snapshot, "revision": revision} 并保存到变量 snapshot
        key = self._session_key(tenant_id, session_id)  # 计算 self._session_key(tenant_id, session_id) 并保存到变量 key
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            await self.client.set(  # 等待异步操作完成并取得结果：self.client.set(
                key,  # 继续向上一处调用或声明传入 key
                json.dumps(snapshot, ensure_ascii=False, default=str),  # 继续向上一处调用或声明传入 json.dumps(snapshot, ensure_ascii=False, default=str)
                ex=self.settings.redis_cache_ttl_seconds,  # 为 self.client.set 设置关键字参数 ex，传入当前行给出的值
            )  # 结束函数 set_session_snapshot 的参数及返回类型声明并开始函数体
        except RedisError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError as exc:
            logger.warning("Redis session cache write failed: {}", type(exc).__name__)  # 调用 warning 执行当前步骤：logger.warning("Redis session cache write failed: {}", type(exc).__name…

    async def invalidate_session(self, tenant_id: str, session_id: UUID) -> None:  # 定义异步函数 invalidate_session，封装可被事件循环调度的协程逻辑
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            await self.client.delete(self._session_key(tenant_id, session_id))  # 等待异步操作完成并取得结果：self.client.delete(self._session_key(tenant_id, session_id))
        except RedisError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError as exc:
            logger.warning("Redis session invalidation failed: {}", type(exc).__name__)  # 调用 warning 执行当前步骤：logger.warning("Redis session invalidation failed: {}", type(exc).__nam…

    async def publish_event(self, event: EventEnvelope) -> None:  # 定义异步函数 publish_event，封装可被事件循环调度的协程逻辑
        key = self._events_key(event.run_id)  # 计算 self._events_key(event.run_id) 并保存到变量 key
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            await self.client.xadd(  # 等待异步操作完成并取得结果：self.client.xadd(
                key,  # 继续向上一处调用或声明传入 key
                {  # 在函数 publish_event 中执行表达式 {，推进当前业务流程
                    "seq": str(event.seq),  # 为多行字典定义键 "seq" 及其对应值
                    "payload": event.model_dump_json(),  # 为多行字典定义键 "payload" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
                maxlen=2000,  # 为 self.client.xadd 设置关键字参数 maxlen，传入当前行给出的值
                approximate=True,  # 为 self.client.xadd 设置关键字参数 approximate，传入当前行给出的值
            )  # 结束函数 publish_event 的参数及返回类型声明并开始函数体
            await self.client.expire(  # 等待异步操作完成并取得结果：self.client.expire(
                key, self.settings.redis_event_ttl_seconds  # 在函数 publish_event 中执行表达式 key, self.settings.redis_event_ttl_seconds，推进当前业务流程
            )  # 结束函数 publish_event 的参数及返回类型声明并开始函数体
        except RedisError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError as exc:
            logger.warning("Redis event publish failed: {}", type(exc).__name__)  # 调用 warning 执行当前步骤：logger.warning("Redis event publish failed: {}", type(exc).__name__)

    async def read_events(  # 定义异步函数 read_events，封装可被事件循环调度的协程逻辑
        self, run_id: UUID, *, after_seq: int, limit: int = 500  # 为函数 read_events 声明参数 self, run_id 及其类型或默认值
    ) -> list[EventEnvelope]:  # 结束 read_events 的参数列表并声明返回类型
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            entries = await self.client.xrange(  # 等待 xrange 完成，并将其结果保存到 entries
                self._events_key(run_id), min="-", max="+", count=limit * 2  # 调用 _events_key 执行当前步骤：self._events_key(run_id), min="-", max="+", count=limit * 2
            )  # 结束函数 read_events 的参数及返回类型声明并开始函数体
        except RedisError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError:
            return []  # 返回 [] 给调用方
        events: list[EventEnvelope] = []  # 计算 [] 并保存到变量 events
        for _, fields in entries:  # 按迭代条件执行循环：for _, fields in entries:
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                seq = int(fields.get("seq", "0"))  # 计算 int(fields.get("seq", "0")) 并保存到变量 seq
                if seq <= after_seq:  # 判断分支条件：if seq <= after_seq:
                    continue  # 跳过本轮剩余逻辑并进入下一轮迭代
                events.append(  # 调用 append 执行当前步骤：events.append(
                    EventEnvelope.model_validate_json(fields["payload"])  # 调用 model_validate_json 执行当前步骤：EventEnvelope.model_validate_json(fields["payload"])
                )  # 结束函数 read_events 的参数及返回类型声明并开始函数体
            except (KeyError, ValueError):  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except (KeyError, ValueError):
                continue  # 跳过本轮剩余逻辑并进入下一轮迭代
            if len(events) >= limit:  # 判断分支条件：if len(events) >= limit:
                break  # 提前结束当前循环并继续后续控制流
        return events  # 返回 events 给调用方

    async def acquire_rate_slot(  # 定义异步函数 acquire_rate_slot，封装可被事件循环调度的协程逻辑
        self, *, tenant_id: str, user_id: str, limit_per_minute: int  # 为函数 acquire_rate_slot 声明参数 self, *, tenant_id 及其类型或默认值
    ) -> tuple[bool, int]:  # 结束 acquire_rate_slot 的参数列表并声明返回类型
        key = f"harness:rate:{tenant_id}:{user_id}"  # 计算 f"harness:rate:{tenant_id}:{user_id}" 并保存到变量 key
        script = """
        local current = redis.call('INCR', KEYS[1])
        if current == 1 then
          redis.call('EXPIRE', KEYS[1], 60)
        end
        local ttl = redis.call('TTL', KEYS[1])
        if current > tonumber(ARGV[1]) then
          return {0, ttl}
        end
        return {1, ttl}
        """
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            allowed, ttl = await self.client.eval(  # 等待 eval 完成，并将其结果保存到 allowed, ttl
                script, 1, key, limit_per_minute  # 在函数 acquire_rate_slot 中执行表达式 script, 1, key, limit_per_minute，推进当前业务流程
            )  # 结束函数 acquire_rate_slot 的参数及返回类型声明并开始函数体
            return bool(int(allowed)), int(ttl)  # 返回 bool(int(allowed)), int(ttl) 给调用方
        except RedisError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError:
            # Mutations fail closed because distributed abuse controls are unavailable.
            raise  # 重新抛出当前异常，保留原始失败上下文

    async def wake_workers(self) -> None:  # 定义异步函数 wake_workers，封装可被事件循环调度的协程逻辑
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            await self.client.lpush("harness:queue:wake", "1")  # 等待异步操作完成并取得结果：self.client.lpush("harness:queue:wake", "1")
            await self.client.ltrim("harness:queue:wake", 0, 999)  # 等待异步操作完成并取得结果：self.client.ltrim("harness:queue:wake", 0, 999)
        except RedisError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError:
            return  # 提前返回空结果，结束当前函数调用

    async def wait_for_wake(self, timeout_seconds: float) -> bool:  # 定义异步函数 wait_for_wake，封装可被事件循环调度的协程逻辑
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            result = await self.client.brpop(  # 等待 brpop 完成，并将其结果保存到 result
                ["harness:queue:wake"], timeout=max(int(timeout_seconds), 1)  # 调用 目标函数 执行当前步骤：["harness:queue:wake"], timeout=max(int(timeout_seconds), 1)
            )  # 结束函数 wait_for_wake 的参数及返回类型声明并开始函数体
            return result is not None  # 返回 result is not None 给调用方
        except RedisError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except RedisError:
            return False  # 返回 False 给调用方

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def _session_key(tenant_id: str, session_id: UUID) -> str:  # 定义函数 _session_key，封装该模块的一项明确职责
        return f"harness:session:{tenant_id}:{session_id}"  # 返回 f"harness:session:{tenant_id}:{session_id}" 给调用方

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def _events_key(run_id: UUID) -> str:  # 定义函数 _events_key，封装该模块的一项明确职责
        return f"harness:run:{run_id}:events"  # 返回 f"harness:run:{run_id}:events" 给调用方
