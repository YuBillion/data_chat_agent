from __future__ import annotations

import pytest

from app.core.errors import BudgetExceededError
from app.harness.types import RunBudget
from app.observability.telemetry import Telemetry


def test_llm_call_and_token_budgets_fail_closed() -> None:
    budget = RunBudget(
        max_llm_calls=1,
        max_tokens=100,
        max_active_seconds=60,
    )
    budget.before_llm_call()
    budget.record_llm_call(input_tokens=6, output_tokens=5)
    with pytest.raises(BudgetExceededError):
        budget.before_llm_call()

    token_budget = RunBudget(
        max_llm_calls=2,
        max_tokens=10,
        max_active_seconds=60,
    )
    with pytest.raises(BudgetExceededError):
        token_budget.record_llm_call(input_tokens=6, output_tokens=5)


def test_langfuse_mask_redacts_user_and_result_content() -> None:
    masked = Telemetry._mask_langfuse_data(
        {
            "query": "secret question",
            "nested": {
                "content": "private",
                "safe": "kept",
            },
            "rows": [{"customer": "alice"}],
        }
    )
    assert masked["query"] == "[REDACTED]"
    assert masked["nested"]["content"] == "[REDACTED]"
    assert masked["nested"]["safe"] == "kept"
    assert masked["rows"] == "[REDACTED]"
