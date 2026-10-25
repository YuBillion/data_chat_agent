from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.defaults import build_default_registry
from app.conf.settings import Settings
from app.core.errors import ForbiddenError
from app.harness.records import InterventionRecord, RunRecord
from app.harness.service import RunService
from app.harness.types import (
    DecisionAction,
    Identity,
    InterventionKind,
    InterventionStatus,
    RunStatus,
)


class FakeStore:
    def __init__(self, intervention: InterventionRecord, run: RunRecord) -> None:
        self.intervention = intervention
        self.run = run
        self.responded = False
        self.audits = []

    async def get_intervention(self, _intervention_id):
        return self.intervention

    async def get_run(self, _identity, _run_id, **_kwargs):
        return self.run

    async def respond_to_intervention(self, _id, **kwargs):
        self.responded = True
        self.intervention = replace(
            self.intervention,
            status=InterventionStatus.RESPONDED,
            decision=kwargs["action"],
            actor_id=kwargs["actor"].user_id,
            version=self.intervention.version + 1,
        )
        return self.intervention

    async def add_audit(self, record):
        self.audits.append(record)


class FakeRedis:
    async def invalidate_session(self, *_args):
        return None

    async def wake_workers(self):
        return None


class FakeEvents:
    pass


class NoopMetric:
    def add(self, *_args, **_kwargs):
        return None


class FakeTelemetry:
    metrics = SimpleNamespace(
        sse_active=NoopMetric(),
        runs_started=NoopMetric(),
        runs_finished=NoopMetric(),
        run_duration=NoopMetric(),
        queue_claims=NoopMetric(),
        llm_calls=NoopMetric(),
        sql_duration=NoopMetric(),
        route_selections=NoopMetric(),
        cache_events=NoopMetric(),
    )

    def current_trace_id(self):
        return "trace"

    def capture_traceparent(self):
        return None


def service_fixture(requester_id: str = "requester"):
    now = datetime.now(UTC)
    run_id = uuid4()
    intervention = InterventionRecord(
        id=uuid4(),
        run_id=run_id,
        kind=InterventionKind.SQL_APPROVAL,
        status=InterventionStatus.PENDING,
        payload={
            "high_risk": True,
            "sql_hash": "a" * 64,
            "sql": "select 1",
        },
        payload_hash="b" * 64,
        decision=None,
        decision_data=None,
        actor_id=None,
        version=1,
        requested_at=now,
        expires_at=now,
        responded_at=None,
    )
    run = RunRecord(
        id=run_id,
        session_id=uuid4(),
        tenant_id="tenant",
        user_id=requester_id,
        query="q",
        status=RunStatus.WAITING_HUMAN,
        requested_agent_id=None,
        selected_agent_id="analytics_sql",
        agent_version="1.0.0",
        route_mode=None,
        route_confidence=None,
        route=None,
        budget={},
        output=None,
        error_code=None,
        error_message=None,
        trace_id="trace",
        idempotency_key="idem",
        version=1,
        created_at=now,
        started_at=now,
        completed_at=None,
        updated_at=now,
    )
    store = FakeStore(intervention, run)
    service = RunService(
        settings=Settings(dev_auth_enabled=True),
        store=store,
        redis=FakeRedis(),
        events=FakeEvents(),
        registry=build_default_registry(Settings(dev_auth_enabled=True)),
        telemetry=FakeTelemetry(),
    )
    return service, store, intervention


async def test_high_risk_sql_cannot_be_approved_by_requester() -> None:
    service, store, intervention = service_fixture("same-user")
    actor = Identity(
        user_id="same-user",
        tenant_id="tenant",
        roles=frozenset({"agent:user", "agent:approver"}),
    )
    with pytest.raises(ForbiddenError):
        await service.respond_to_intervention(
            actor,
            intervention.id,
            expected_version=1,
            action=DecisionAction.APPROVE,
            decision={"reason": "ok"},
        )
    assert store.responded is False


async def test_different_approver_can_approve_high_risk_sql() -> None:
    service, store, intervention = service_fixture("requester")
    actor = Identity(
        user_id="approver",
        tenant_id="tenant",
        roles=frozenset({"agent:approver"}),
    )
    result = await service.respond_to_intervention(
        actor,
        intervention.id,
        expected_version=1,
        action=DecisionAction.APPROVE,
        decision={"reason": "ok"},
    )
    assert result.status == InterventionStatus.RESPONDED
    assert store.responded is True
