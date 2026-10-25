from __future__ import annotations

from types import SimpleNamespace

import httpx

from app.agents.types import AgentPublicView
from app.api.app import create_app
from app.conf.settings import Settings


class FakeTelemetry:
    def current_trace_id(self):
        return "trace-1"


class FakeRunService:
    def list_agents(self, identity):
        assert identity.user_id == "local-user"
        return [
            AgentPublicView(
                agent_id="analytics_sql",
                version="1.0.0",
                display_name="问数 Agent",
                description="query data",
                capabilities=["business_data_query"],
                response_types=["text"],
            )
        ]


async def test_agent_endpoint_uses_dev_identity() -> None:
    settings = Settings(dev_auth_enabled=True, trusted_hosts="testserver")
    container = SimpleNamespace(
        settings=settings,
        telemetry=FakeTelemetry(),
        run_service=FakeRunService(),
    )
    app = create_app(settings=settings, container=container)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json()[0]["agent_id"] == "analytics_sql"
    assert response.headers["x-request-id"]


async def test_invalid_query_returns_problem_detail() -> None:
    settings = Settings(dev_auth_enabled=True, trusted_hosts="testserver")
    container = SimpleNamespace(
        settings=settings,
        telemetry=FakeTelemetry(),
        run_service=FakeRunService(),
    )
    app = create_app(settings=settings, container=container)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/sessions/00000000-0000-0000-0000-000000000001/runs",
            headers={"Idempotency-Key": "test"},
            json={"query": "   "},
        )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_oversized_request_returns_problem_detail() -> None:
    settings = Settings(dev_auth_enabled=True, trusted_hosts="testserver")
    container = SimpleNamespace(
        settings=settings,
        telemetry=FakeTelemetry(),
        run_service=FakeRunService(),
    )
    app = create_app(settings=settings, container=container)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/sessions",
            headers={
                "content-length": "2097152",
                "content-type": "application/json",
            },
            content=b"{}",
        )
    assert response.status_code == 413
    assert response.json()["code"] == "REQUEST_TOO_LARGE"
