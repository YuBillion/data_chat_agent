from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import fakeredis.aioredis

from app.conf.settings import Settings
from app.harness.redis_runtime import RedisRuntime
from app.harness.types import EventEnvelope


async def test_session_cache_and_event_stream_round_trip() -> None:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    runtime = RedisRuntime(Settings(dev_auth_enabled=True), client=client)
    session_id = uuid4()
    run_id = uuid4()
    await runtime.set_session_snapshot(
        "tenant", session_id, {"status": "active"}, revision=3
    )
    snapshot = await runtime.get_session_snapshot("tenant", session_id)
    assert snapshot == {"status": "active", "revision": 3}

    event = EventEnvelope(
        run_id=run_id,
        seq=1,
        occurred_at=datetime.now(UTC),
        event_type="run.queued",
        payload={"status": "queued"},
    )
    await runtime.publish_event(event)
    events = await runtime.read_events(run_id, after_seq=0)
    assert [item.seq for item in events] == [1]
    await runtime.close()
