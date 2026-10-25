from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.harness.db_models import HarnessSessionRow, RunRow
from app.harness.store import _run_record, _session_record
from app.harness.types import RunStatus


def test_session_and_run_mappers_keep_retention_and_trace_fields() -> None:
    now = datetime.now(UTC)
    session = HarnessSessionRow(
        id=uuid4(),
        tenant_id="tenant",
        user_id="user",
        title="title",
        status="active",
        version=1,
        created_at=now,
        updated_at=now,
        deleted_at=None,
        redacted_at=now,
    )
    session_record = _session_record(session)
    assert session_record.redacted_at == now

    run = RunRow(
        id=uuid4(),
        session_id=session.id,
        tenant_id="tenant",
        user_id="user",
        query="query",
        status=RunStatus.QUEUED.value,
        requested_agent_id=None,
        selected_agent_id=None,
        agent_version=None,
        route_mode=None,
        route_confidence=None,
        route_json=None,
        budget_json={},
        output_json=None,
        error_code=None,
        error_message=None,
        trace_id="trace",
        traceparent="00-" + "1" * 32 + "-" + "2" * 16 + "-01",
        idempotency_key="key",
        version=1,
        created_at=now,
        started_at=None,
        completed_at=None,
        updated_at=now,
    )
    run_record = _run_record(run)
    assert run_record.traceparent == run.traceparent
