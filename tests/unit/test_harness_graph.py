from __future__ import annotations

import asyncio
import json
from contextlib import nullcontext
from types import SimpleNamespace

from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agents.defaults import build_default_registry
from app.agents.types import RouteCandidate, RouteDecision
from app.conf.settings import Settings
from app.harness.graph import build_harness_graph
from app.harness.types import Identity, RouteMode, RunBudget


class ManualRouter:
    async def route(self, **kwargs):
        del kwargs
        return RouteDecision(
            selected_agent_id=None,
            mode=RouteMode.MODEL,
            confidence=0.5,
            candidates=[
                RouteCandidate(
                    agent_id="catalog_qa",
                    confidence=0.5,
                    reason="definition",
                ),
                RouteCandidate(
                    agent_id="analytics_sql",
                    confidence=0.45,
                    reason="data",
                ),
            ],
            reason_code="low_confidence",
            resolved_query="GMV 的定义",
            requires_human=True,
        )


class Store:
    def __init__(self) -> None:
        self.routes = []

    async def set_run_route(self, run_id, **kwargs):
        self.routes.append((run_id, kwargs))

    async def add_audit(self, _record):
        return None


class NoopMetric:
    def add(self, *_args, **_kwargs):
        return None


class FakeSpan:
    def set_attribute(self, *_args):
        return None


class FakeTracer:
    def start_as_current_span(self, *_args, **_kwargs):
        return nullcontext(FakeSpan())


class FakeTelemetry:
    tracer = FakeTracer()
    metrics = SimpleNamespace(route_selections=NoopMetric())

    def record_exception(self, *_args):
        return None


class FakeLLM:
    def __init__(self) -> None:
        self.model = RunnableLambda(
            lambda _: json.dumps(
                {
                    "answer": "GMV 是成交金额总和。",
                    "references": [{"type": "metric", "id": "GMV"}],
                    "confidence": 0.9,
                    "limitations": [],
                },
                ensure_ascii=False,
            )
        )

    async def ainvoke(self, runnable, value, *, name):
        del name
        return await runnable.ainvoke(value)


class EmptySearch:
    async def search(self, *_args, **_kwargs):
        return []


class Embedding:
    async def aembed_query(self, _query):
        return [0.0, 1.0]


class MetaRepository:
    async def get_table_info_by_id(self, _table_id):
        return None

    async def list_columns_by_table_id(self, _table_id):
        return []


async def test_route_gate_interrupt_and_resume_executes_selected_agent() -> None:
    settings = Settings(dev_auth_enabled=True)
    registry = build_default_registry(settings)
    graph = build_harness_graph(registry, InMemorySaver())
    config = {"configurable": {"thread_id": "harness-route-test"}}
    identity = Identity(
        user_id="u1",
        tenant_id="t1",
        roles=frozenset({"agent:user"}),
    )
    store = Store()
    budget = RunBudget(10, 64_000, 180)
    context = {
        "settings": settings,
        "identity": identity,
        "registry": registry,
        "router": ManualRouter(),
        "store": store,
        "telemetry": FakeTelemetry(),
        "budget": budget,
        "llm": FakeLLM(),
        "run_id": "00000000-0000-0000-0000-000000000010",
        "session_id": "00000000-0000-0000-0000-000000000011",
        "trace_id": None,
        "column_qdrant_repository": EmptySearch(),
        "metric_qdrant_repository": EmptySearch(),
        "embedding_client": Embedding(),
        "meta_mysql_repository": MetaRepository(),
        "tool_semaphore": asyncio.Semaphore(2),
    }
    async for _ in graph.astream(
        {
            "run_id": "00000000-0000-0000-0000-000000000010",
            "session_id": "00000000-0000-0000-0000-000000000011",
            "query": "GMV 是什么",
            "requested_agent_id": None,
            "conversation": [],
            "correction_count": 0,
            "max_corrections": 1,
            "approval_rounds": 0,
        },
        config=config,
        context=context,
        stream_mode="custom",
    ):
        pass
    interrupted = await graph.aget_state(config)
    assert interrupted.interrupts

    async for _ in graph.astream(
        Command(resume={"agent_id": "catalog_qa"}),
        config=config,
        context=context,
        stream_mode="custom",
    ):
        pass
    final = await graph.aget_state(config)
    assert final.values["selected_agent_id"] == "catalog_qa"
    assert final.values["run_outcome_status"] == "completed"
    assert final.values["agent_output"]["agent_id"] == "catalog_qa"
    assert store.routes
