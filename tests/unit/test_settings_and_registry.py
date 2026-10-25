from __future__ import annotations

import pytest

from app.agents.defaults import build_default_registry
from app.conf.settings import Settings
from app.core.errors import AppError
from app.prompt.prompt_loader import load_prompt, prompt_digest


def test_development_settings_and_registry_are_valid() -> None:
    settings = Settings(dev_auth_enabled=True)
    registry = build_default_registry(settings)

    assert registry.agent_ids == ("analytics_sql", "catalog_qa")
    assert len(prompt_digest("generate_sql")) == 64


def test_production_requires_oidc_and_disables_dev_auth() -> None:
    with pytest.raises(ValueError, match="OIDC"):
        Settings(environment="production", dev_auth_enabled=False)
    with pytest.raises(ValueError, match="DEV_AUTH_ENABLED"):
        Settings(
            environment="production",
            dev_auth_enabled=True,
            oidc_issuer="https://issuer.example",
            oidc_audience="agent",
            oidc_jwks_url="https://issuer.example/.well-known/jwks.json",
        )


@pytest.mark.parametrize("name", ["../secret", "nested/path", "", "..\\secret"])
def test_prompt_loader_rejects_path_escape(name: str) -> None:
    with pytest.raises(AppError):
        load_prompt(name)
