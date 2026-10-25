from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.agents.defaults import build_default_registry
from app.conf.settings import Settings
from app.harness.records import JobRecord, RunRecord
from app.harness.types import JobStatus, JobType, RunStatus
from app.harness.worker import HarnessWorker


class NoopMetric:
    def add(self, *_args, **_kwargs):
        return None

    def record(self, *_args, **_kwargs):
        return None


class FakeSpan:
    def set_attribute(self, *_args):
        return None

    def record_exception(self, *_args):
        return None

    def set_status(self, *_args):
        return None


class FakeTracer:
    def start_as_current_span(self, *_args, **_kwargs):
        return nullcontext(FakeSpan())


class FakeTelemetry:
    tracer = FakeTracer()
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

    def activate_traceparent(self, *_args):
        return nullcontext()

    def record_exception(self, *_args):
        return None

    def current_trace_id(self):
        return "trace"


class FakeGraph:
    def __init__(self) -> None:
        self.values = {}
        self.received_input = None
        self.received_context = None

    async def aget_state(self, _config):
        return SimpleNamespace(values=self.values, interrupts=())

    async def astream(self, *, input, config, context, stream_mode):
        del config, stream_mode
        self.received_input = input
        self.received_context = context
        self.values = {
            "run_outcome_status": "completed",
            "agent_output": {
                "agent_id": "catalog_qa",
                "text": "catalog answer",
            },
        }
        yield {"type": "progress", "step": "检索元数据", "status": "success"}
        yield {"type": "result", "data": self.values["agent_output"]}


class FakeStore:
    def __init__(self, run: RunRecord) -> None:
        self.run = run
        self.completed_jobs = []
        self.budgets = []

    async def get_run_internal(self, _run_id):
        return self.run

    async def list_messages(self, *_args, **_kwargs):
        return []

    async def mark_run_running(self, _run_id):
        return None

    async def set_run_budget(self, _run_id, budget):
        self.budgets.append(budget)

    async def complete_run(self, _run_id, *, output, budget):
        del output, budget
        self.run = RunRun(self.run, RunStatus.COMPLETED)
        return self.run

    async def finish_run(self, *_args, **_kwargs):
        raise AssertionError("completion path must not mark the run failed")

    async def complete_job(self, job_id, worker_id):
        self.completed_jobs.append((job_id, worker_id))


def RunRun(run: RunRecord, status: RunStatus) -> RunRecord:
    from dataclasses import replace

    return replace(run, status=status)


class FakeEvents:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, run_id, event_type, payload, *, trace_id=None):
        self.events.append((run_id, event_type, payload, trace_id))


class FakeRedis:
    async def get_session_snapshot(self, *_args):
        return None

    async def invalidate_session(self, *_args):
        return None


class FakeLLMFactory:
    def bind(self, **_kwargs):
        return SimpleNamespace(model=object())


class FakeSQLTool:
    pass


@asynccontextmanager
async def fake_session():
    yield SimpleNamespace()


class FakeEmbedding:
    pass


class FakeRepository:
    pass


async def test_worker_completes_run_and_publishes_terminal_event() -> None:
    now = datetime.now(UTC)
    run = RunRecord(
        id=uuid4(),
        session_id=uuid4(),
        tenant_id="tenant",
        user_id="user",
        query="catalog",
        status=RunStatus.QUEUED,
        requested_agent_id="catalog_qa",
        selected_agent_id=None,
        agent_version=None,
        route_mode=None,
        route_confidence=None,
        route=None,
        budget={},
        output=None,
        error_code=None,
        error_message=None,
        trace_id="trace",
        idempotency_key="key",
        version=1,
        created_at=now,
        started_at=None,
        completed_at=None,
        updated_at=now,
    )
    job = JobRecord(
        id=uuid4(),
        run_id=run.id,
        job_type=JobType.START,
        status=JobStatus.LEASED,
        payload={},
        traceparent=None,
        available_at=now,
        lease_owner="worker",
        lease_until=now,
        attempts=1,
    )
    store = FakeStore(run)
    events = FakeEvents()
    graph = FakeGraph()
    telemetry = FakeTelemetry()
    worker = HarnessWorker(
        settings=Settings(dev_auth_enabled=True),
        store=store,
        redis=FakeRedis(),
        events=events,
        registry=build_default_registry(Settings(dev_auth_enabled=True)),
        telemetry=telemetry,
        graph=graph,
        llm_factory=FakeLLMFactory(),
        sql_read_tool=FakeSQLTool(),
        meta_session_factory=fake_session,
        dw_session_factory=fake_session,
        column_qdrant_repository=FakeRepository(),
        metric_qdrant_repository=FakeRepository(),
        value_es_repository=FakeRepository(),
        embedding_client=FakeEmbedding(),
        tool_semaphore=asyncio.Semaphore(2),
        checkpointer=SimpleNamespace(),
    )
    await worker._run_job(job)

    assert graph.received_input["query"] == "catalog"
    assert graph.received_context["registry"] is not None
    assert graph.received_context["router"] is not None
    assert store.completed_jobs
    assert store.run.status == RunStatus.COMPLETED
    assert events.events[-1][1] == "run.completed"
