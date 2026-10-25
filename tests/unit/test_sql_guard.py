from __future__ import annotations

import pytest

from app.tools.sql_guard import SQLGuard, SQLPolicyError

ALLOWED_TABLES = {"fact_order", "dim_region"}
ALLOWED_COLUMNS = {
    "fact_order.order_amount",
    "fact_order.region_id",
    "dim_region.region_id",
    "dim_region.region_name",
}


def test_guard_accepts_catalog_scoped_select_with_alias() -> None:
    guard = SQLGuard()
    result = guard.inspect(
        """
        SELECT r.region_name, SUM(f.order_amount) AS gmv
        FROM fact_order AS f
        JOIN dim_region AS r ON f.region_id = r.region_id
        GROUP BY r.region_name
        """,
        allowed_tables=ALLOWED_TABLES,
        allowed_columns=ALLOWED_COLUMNS,
    )

    assert result.allowed is True
    assert result.tables == ["dim_region", "fact_order"]
    assert "fact_order.order_amount" in result.columns
    assert len(result.sql_hash) == 64


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM fact_order",
        "UPDATE fact_order SET order_amount = 0",
        "SELECT 1; SELECT 2",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM fact_order FOR UPDATE",
        "SELECT LOAD_FILE('/etc/passwd') FROM fact_order",
        "WITH changed AS (DELETE FROM fact_order) SELECT 1",
    ],
)
def test_guard_rejects_write_or_dangerous_sql(sql: str) -> None:
    guard = SQLGuard()
    with pytest.raises(SQLPolicyError):
        guard.inspect(
            sql,
            allowed_tables=ALLOWED_TABLES,
            allowed_columns=ALLOWED_COLUMNS,
        )


def test_guard_marks_corrected_and_expensive_queries_for_approval() -> None:
    guard = SQLGuard(
        approval_scan_rows=100,
        high_risk_scan_rows=1000,
        sensitive_columns={"dim_region.region_name"},
    )
    result = guard.inspect(
        "SELECT region_name FROM dim_region",
        allowed_tables=ALLOWED_TABLES,
        allowed_columns=ALLOWED_COLUMNS,
        corrected=True,
        estimated_rows=2000,
    )

    assert result.approval_required is True
    assert result.high_risk is True
    assert "corrected_sql" in result.reasons
    assert "sensitive_columns" in result.reasons
    assert "high_scan_estimate" in result.reasons
