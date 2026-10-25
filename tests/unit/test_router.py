from __future__ import annotations

from app.agents.defaults import build_default_registry
from app.agents.types import RouteCandidate, RouterModelOutput
from app.conf.settings import Settings
from app.harness.router import AgentRouter
from app.harness.types import Identity, RouteMode


class RuleFirstRouter(AgentRouter):
    def __init__(self, registry, model_output: RouterModelOutput) -> None:
        super().__init__(registry)
        self.model_output = model_output

    async def _model_route(self, **kwargs):  # type: ignore[override]
        del kwargs
        return self.model_output


def identity() -> Identity:
    return Identity(
        user_id="u1",
        tenant_id="t1",
        roles=frozenset({"agent:user", "agent:approver"}),
    )


async def test_explicit_route_does_not_call_model() -> None:
    settings = Settings(dev_auth_enabled=True)
    registry = build_default_registry(settings)
    router = AgentRouter(registry)
    decision = await router.route(
        identity=identity(),
        query="随便",
        requested_agent_id="catalog_qa",
        history=[],
        llm=None,  # type: ignore[arg-type]
    )
    assert decision.mode == RouteMode.EXPLICIT
    assert decision.selected_agent_id == "catalog_qa"


async def test_catalog_definition_rule() -> None:
    router = AgentRouter(build_default_registry(Settings(dev_auth_enabled=True)))
    decision = await router.route(
        identity=identity(),
        query="fact_order 表结构有哪些字段？",
        requested_agent_id=None,
        history=[],
        llm=None,  # type: ignore[arg-type]
    )
    assert decision.mode == RouteMode.RULE
    assert decision.selected_agent_id == "catalog_qa"


async def test_low_confidence_requires_human_selection() -> None:
    registry = build_default_registry(Settings(dev_auth_enabled=True))
    router = RuleFirstRouter(
        registry,
        RouterModelOutput(
            agent_id="catalog_qa",
            confidence=0.70,
            alternatives=[
                RouteCandidate(
                    agent_id="analytics_sql",
                    confidence=0.65,
                    reason="could_be_query",
                )
            ],
            reason_code="ambiguous",
            resolved_query="GMV",
        ),
    )
    decision = await router.route(
        identity=identity(),
        query="GMV",
        requested_agent_id=None,
        history=[],
        llm=None,  # type: ignore[arg-type]
    )
    assert decision.requires_human is True
    assert decision.selected_agent_id is None
