"""HTTP/SSE load probe for an already deployed harness.

This is intentionally an external smoke/load tool, not a unit test. It
performs real model and warehouse work and must only be run against an
approved test environment.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import time
from dataclasses import dataclass, field
from uuid import uuid4

import httpx


@dataclass(slots=True)
class LoadResult:
    accepted: int = 0
    rejected: int = 0
    streams_completed: int = 0
    stream_errors: int = 0
    statuses: dict[str, int] = field(default_factory=dict)


async def stream_events(
    client: httpx.AsyncClient,
    run_id: str,
    result: LoadResult,
    stop: asyncio.Event,
) -> None:
    try:
        async with client.stream(
            "GET",
            f"/api/v1/runs/{run_id}/events?after_seq=0",
            headers={"Accept": "text/event-stream"},
            timeout=None,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if stop.is_set():
                    return
                if line.startswith("event:"):
                    event_type = line.removeprefix("event:").strip()
                    if event_type in {
                        "run.completed",
                        "run.failed",
                        "run.rejected",
                        "run.cancelled",
                        "run.expired",
                    }:
                        result.streams_completed += 1
                        return
    except Exception:
        result.stream_errors += 1


async def run(args: argparse.Namespace) -> LoadResult:
    headers = {"Accept": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    result = LoadResult()
    stop = asyncio.Event()
    started = time.perf_counter()
    limits = httpx.Limits(
        max_connections=args.connections + 100,
        max_keepalive_connections=args.connections,
    )
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"),
        headers=headers,
        timeout=30,
        limits=limits,
    ) as client:
        sessions: list[str] = []
        for _ in range(args.connections):
            response = await client.post(
                "/api/v1/sessions", json={"title": "load-test"}
            )
            result.statuses[f"session:{response.status_code}"] = (
                result.statuses.get(f"session:{response.status_code}", 0) + 1
            )
            if response.is_success:
                sessions.append(response.json()["id"])

        run_ids: list[str] = []
        for index, session_id in enumerate(sessions):
            target = started + index / args.rate
            delay = target - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            response = await client.post(
                f"/api/v1/sessions/{session_id}/runs",
                headers={"Idempotency-Key": str(uuid4())},
                json={"query": args.query, "agent_id": args.agent_id},
            )
            result.statuses[f"run:{response.status_code}"] = (
                result.statuses.get(f"run:{response.status_code}", 0) + 1
            )
            if response.status_code == 202:
                result.accepted += 1
                run_ids.append(response.json()["id"])
            else:
                result.rejected += 1

        streams = [
            asyncio.create_task(stream_events(client, run_id, result, stop))
            for run_id in run_ids
        ]
        try:
            await asyncio.wait_for(
                asyncio.gather(*streams, return_exceptions=True),
                timeout=args.timeout,
            )
        except TimeoutError:
            stop.set()
            for task in streams:
                task.cancel()
            await asyncio.gather(*streams, return_exceptions=True)
        elapsed = time.perf_counter() - started
        result.statuses["elapsed_seconds"] = int(elapsed)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", default=os.getenv("LOAD_TEST_JWT"))
    parser.add_argument("--connections", type=int, default=200)
    parser.add_argument("--rate", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--agent-id", default=None)
    parser.add_argument(
        "--query",
        default="统计 2025 年第一季度各大区的 GMV",
    )
    arguments = parser.parse_args()
    outcome = asyncio.run(run(arguments))
    print(json.dumps(dataclasses.asdict(outcome), ensure_ascii=False, indent=2))
