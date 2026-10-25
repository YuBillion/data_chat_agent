"""Live LLM router evaluation; requires the configured model endpoint."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.agents.defaults import build_default_registry
from app.conf.settings import get_settings
from app.harness.router import AgentRouter
from app.harness.types import Identity, RunBudget
from app.infrastructure.llm import ChatModelFactory
from app.observability.telemetry import Telemetry


async def run(cases_path: Path, threshold: float) -> int:
    settings = get_settings()
    registry = build_default_registry(settings)
    router = AgentRouter(
        registry,
        min_confidence=settings.router_min_confidence,
        min_margin=settings.router_min_margin,
    )
    telemetry = Telemetry(settings)
    telemetry.setup()
    llm_factory = ChatModelFactory(settings)
    identity = Identity(
        user_id="eval-user",
        tenant_id="eval-tenant",
        roles=frozenset({"agent:user"}),
    )
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    correct = 0
    results = []
    try:
        for index, case in enumerate(cases):
            budget = RunBudget(
                settings.run_max_llm_calls,
                settings.run_max_tokens,
                settings.run_max_wall_seconds,
            )
            llm = llm_factory.bind(
                budget=budget,
                telemetry=telemetry,
                trace_id=None,
                agent_id="router",
                run_id=f"eval-{index}",
            )
            decision = await router.route(
                identity=identity,
                query=case["query"],
                requested_agent_id=None,
                history=[],
                llm=llm,
            )
            expected = case["expected_agent"]
            passed = (
                decision.selected_agent_id == expected
                or (
                    expected is None
                    and case.get("allow_low_confidence")
                    and decision.requires_human
                )
            )
            correct += int(passed)
            results.append(
                {
                    "query": case["query"],
                    "expected": expected,
                    "selected": decision.selected_agent_id,
                    "mode": decision.mode.value,
                    "confidence": decision.confidence,
                    "requires_human": decision.requires_human,
                    "passed": passed,
                }
            )
    finally:
        telemetry.flush()

    accuracy = correct / max(len(cases), 1)
    report = {"accuracy": accuracy, "threshold": threshold, "results": results}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if accuracy >= threshold else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("evals/router_cases.json"),
    )
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.cases, args.threshold)))
