from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from app.conf.settings import Settings
from app.harness.database import HarnessDatabase
from app.harness.db_models import HarnessBase
from app.harness.store import HarnessStore
from app.harness.types import Identity

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("HARNESS_TEST_POSTGRES_DSN"),
        reason="HARNESS_TEST_POSTGRES_DSN is not configured",
    ),
]


@pytest.fixture
async def store() -> AsyncIterator[HarnessStore]:
    settings = Settings(
        dev_auth_enabled=True,
        postgres_dsn=os.environ["HARNESS_TEST_POSTGRES_DSN"],
    )
    database = HarnessDatabase(settings)
    async with database.engine.begin() as connection:
        await connection.exec_driver_sql("create schema if not exists harness")
        await connection.run_sync(HarnessBase.metadata.create_all)
    try:
        yield HarnessStore(database.session_factory)
    finally:
        await database.close()


async def test_create_session_and_enqueue_idempotent_run(
    store: HarnessStore,
) -> None:
    identity = Identity(
        user_id=f"test-{uuid4()}",
        tenant_id=f"tenant-{uuid4()}",
        roles=frozenset({"agent:user"}),
    )
    session = await store.create_session(identity, "integration")
    key = str(uuid4())
    first, first_created = await store.create_run(
        identity,
        session_id=session.id,
        query="统计 GMV",
        requested_agent_id="analytics_sql",
        idempotency_key=key,
        trace_id=None,
        traceparent=None,
        max_user_active=5,
        max_tenant_active=50,
        max_queue_depth=1000,
    )
    second, second_created = await store.create_run(
        identity,
        session_id=session.id,
        query="统计 GMV",
        requested_agent_id="analytics_sql",
        idempotency_key=key,
        trace_id=None,
        traceparent=None,
        max_user_active=5,
        max_tenant_active=50,
        max_queue_depth=1000,
    )
    assert first.id == second.id
    assert first_created is True
    assert second_created is False
    event = await store.append_event(
        first.id,
        event_type="run.queued",
        payload={"status": "queued"},
        trace_id=None,
    )
    assert event.seq == 1
