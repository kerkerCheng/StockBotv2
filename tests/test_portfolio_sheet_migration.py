from __future__ import annotations

import pytest

from scripts.migrate_portfolio_sheet_schema import build_update_matrix, column_letter


def test_column_letter_handles_sheet_boundaries() -> None:
    assert column_letter(0) == "A"
    assert column_letter(25) == "Z"
    assert column_letter(26) == "AA"


def test_build_update_matrix_only_aliases_existing_market_usd() -> None:
    rows = [
        ["broker", "symbol", "market_usd"],
        ["IB", "NVDA", "=D2*100"],
        ["IB", "QQQ", "=D3*200"],
    ]

    plan = build_update_matrix(rows)

    assert plan["start_col"] == "D"
    assert plan["end_col"] == "F"
    assert plan["matrix"] == [
        ["market_value_base", "nav_base", "base_currency"],
        ["=C2", "=SUM($C$2:$C$3)", "USD"],
        ["=C3", "=SUM($C$2:$C$3)", "USD"],
    ]


def test_build_update_matrix_is_idempotent_and_rejects_partial_contract() -> None:
    complete = [[
        "symbol",
        "market_usd",
        "market_value_base",
        "nav_base",
        "base_currency",
    ]]
    assert build_update_matrix(complete)["already_migrated"] is True

    with pytest.raises(ValueError, match="只存在一部分"):
        build_update_matrix([["symbol", "market_usd", "nav_base"]])
