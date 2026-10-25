from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import Command

from app.agent.nodes.approval_gate import approval_gate
from app.agent.state import DataAgentState
from app.conf.settings import Settings
from app.harness.context import HarnessContext


def build_graph():
    builder = StateGraph(DataAgentState, context_schema=HarnessContext)
    builder.add_node("approval_gate", approval_gate)
    builder.add_edge(START, "approval_gate")
    builder.add_edge("approval_gate", END)
    return builder.compile(checkpointer=InMemorySaver())


async def test_approval_interrupt_can_be_resumed_once() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "approval-test"}}
    state = {
        "sql": "select region_name from dim_region",
        "executed_sql": "SELECT region_name FROM dim_region",
        "sql_hash": "a" * 64,
        "approval_required": True,
        "approval_rounds": 0,
        "estimated_rows": 1,
        "risk_reasons": ["corrected_sql"],
        "high_risk": False,
    }
    context: HarnessContext = {"settings": Settings(dev_auth_enabled=True)}

    chunks = [
        chunk
        async for chunk in graph.astream(
            state,
            config=config,
            context=context,
            stream_mode="custom",
        )
    ]
    snapshot = await graph.aget_state(config)
    assert snapshot.interrupts
    assert any(item.get("type") == "sql.approval_required" for item in chunks)

    resumed = [
        chunk
        async for chunk in graph.astream(
            Command(
                resume={
                    "action": "approve",
                    "sql_hash": "a" * 64,
                }
            ),
            config=config,
            context=context,
            stream_mode="custom",
        )
    ]
    final = await graph.aget_state(config)
    assert final.values["approval_action"] == "approve"
    assert resumed


async def test_stale_sql_hash_is_rejected() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "approval-stale"}}
    state = {
        "sql": "select region_name from dim_region",
        "executed_sql": "SELECT region_name FROM dim_region",
        "sql_hash": "b" * 64,
        "approval_required": True,
        "approval_rounds": 0,
        "risk_reasons": ["corrected_sql"],
        "high_risk": False,
    }
    context: HarnessContext = {"settings": Settings(dev_auth_enabled=True)}
    async for _ in graph.astream(
        state, config=config, context=context, stream_mode="custom"
    ):
        pass
    with pytest.raises(Exception, match="approval"):
        async for _ in graph.astream(
            Command(
                resume={
                    "action": "approve",
                    "sql_hash": "c" * 64,
                }
            ),
            config=config,
            context=context,
            stream_mode="custom",
        ):
            pass
