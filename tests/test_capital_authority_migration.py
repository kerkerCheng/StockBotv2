from __future__ import annotations

import pytest

from fetchers.gsheets import CAPITAL_AUTHORITY_HEADERS
from scripts.migrate_capital_authority_schema import (
    OLD_HEADERS,
    _normalized_cells,
    build_migration_matrix,
)


def _old_row(**values):
    return [values.get(header, "") for header in OLD_HEADERS]


def test_migration_collapses_old_authority_to_floor_and_credit() -> None:
    rows = [
        list(OLD_HEADERS),
        _old_row(
            record_id="portfolio_cash_authority_01",
            as_of="2026-07-28",
            capital_type="portfolio_cash_authority",
        ),
        _old_row(
            record_id="operating_floor_twd_01",
            as_of="2026-07-28",
            capital_type="operating_floor",
            currency="TWD",
            amount="20000",
        ),
        _old_row(
            record_id="planned_outflows_24m_twd_01",
            as_of="2026-07-28",
            capital_type="planned_outflows_reserve_24m",
            currency="TWD",
            amount="0",
        ),
        _old_row(
            record_id="credit_facility_twd_01",
            as_of="2026-07-29",
            capital_type="contingent_liquidity_credit_facility",
            currency="TWD",
            limit_amount="6000000",
            drawn_amount="0",
            annual_rate_pct="3.1",
            interest_accrual="daily",
            facility_term_years="30",
            repayment_structure="interest_only_bullet_principal_at_maturity",
        ),
    ]

    plan = build_migration_matrix(rows)
    matrix = plan["matrix"]

    assert matrix[0] == list(CAPITAL_AUTHORITY_HEADERS)
    assert plan["before_rows"] == 4
    assert plan["after_rows"] == 2
    assert plan["before_columns"] == 28
    assert plan["after_columns"] == 12
    assert matrix[1][0:5] == [
        "cash_floor_twd_01",
        "2026-07-28",
        "cash_floor",
        "TWD",
        "20000",
    ]
    assert matrix[2][0:4] == [
        "credit_facility_twd_01",
        "2026-07-29",
        "credit_facility",
        "TWD",
    ]
    assert matrix[2][5:11] == [
        "6000000",
        "0",
        "3.1",
        "daily",
        "30",
        "interest_only_bullet_principal_at_maturity",
    ]
    flattened = " ".join(str(value) for row in matrix for value in row)
    assert "planned_outflows" not in flattened
    assert "portfolio_cash_authority" not in flattened


def test_migration_rejects_unknown_or_partial_schema() -> None:
    with pytest.raises(ValueError, match="既不是舊 schema"):
        build_migration_matrix([["record_id", "capital_type"]])


def test_read_back_normalization_accepts_trimmed_blanks_and_numeric_cells() -> None:
    expected = [["cash_floor_01", "2026-07-30", "cash_floor", "TWD", "20000", ""]]
    actual = [["cash_floor_01", "2026-07-30", "cash_floor", "TWD", 20000]]

    assert _normalized_cells(actual, 6) == _normalized_cells(expected, 6)
