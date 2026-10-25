from __future__ import annotations

import pytest

from app.agents.defaults import build_default_registry
from app.conf.settings import Settings
from app.core.errors import ForbiddenError
from app.harness.tool_access import require_tool_access


def test_catalog_agent_cannot_use_sql_execution_tool() -> None:
    context = {
        "registry": build_default_registry(Settings(dev_auth_enabled=True))
    }
    with pytest.raises(ForbiddenError):
        require_tool_access(
            context,  # type: ignore[arg-type]
            {"selected_agent_id": "catalog_qa"},
            "sql_execute",
        )


def test_analytics_agent_can_use_sql_execution_tool() -> None:
    context = {
        "registry": build_default_registry(Settings(dev_auth_enabled=True))
    }
    require_tool_access(
        context,  # type: ignore[arg-type]
        {"selected_agent_id": "analytics_sql"},
        "sql_execute",
    )
