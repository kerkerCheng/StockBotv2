from __future__ import annotations

import pytest

from decision_lab.identity import resolve_identity
from fetchers import gsheets
from fetchers.gsheets import fetch_portfolio, get_execution_aliases


def test_sheet_execution_alias_is_a_separate_reference_not_company_identity() -> None:
    aliases = get_execution_aliases()
    resolved = resolve_identity(
        company_id="co:sivers_semiconductors",
        execution_aliases=aliases,
    )

    assert resolved.company_id == "co:sivers_semiconductors"
    assert resolved.research_ticker == "SIVE.ST"
    assert resolved.execution_symbol == "FRA:2DG"

    aliases["SIVE.ST"] = "MUTATED"
    assert get_execution_aliases()["SIVE.ST"] == "FRA:2DG"


def test_identity_mismatch_and_private_company_fail_closed_differently() -> None:
    mismatch = resolve_identity(
        company_id="co:sivers_semiconductors",
        research_ticker="COHR",
    )
    private = resolve_identity(company_id="co:anthropic")
    unknown = resolve_identity(company_id="co:not_registered")

    assert mismatch.blockers == ("identity_mismatch",)
    assert private.blockers == ("research_ticker_unavailable",)
    assert unknown.blockers == ("unresolved_company_identity",)


class _SheetRequest:
    def __init__(self, values):
        self._values = values

    def execute(self):
        return {"values": self._values}


class _SheetValues:
    def __init__(self, values):
        self._values = values

    def get(self, **_kwargs):
        return _SheetRequest(self._values)


class _SheetSpreadsheets:
    def __init__(self, values):
        self._values = values

    def values(self):
        return _SheetValues(self._values)


class _SheetService:
    def __init__(self, values):
        self._values = values

    def spreadsheets(self):
        return _SheetSpreadsheets(self._values)


def test_operational_sheet_read_parses_mark_to_market_fields_strictly(
    monkeypatch,
) -> None:
    headers = [
        "ticker",
        "shares",
        "avg_cost",
        "currency",
        "market_value_base",
        "nav_base",
        "base_currency",
    ]
    monkeypatch.setattr(gsheets, "SPREADSHEET_ID", "fixture")
    monkeypatch.setattr(
        gsheets,
        "_get_service",
        lambda: _SheetService([headers, ["FRA:2DG", "10", "2", "eur", "25", "100", "usd"]]),
    )

    rows = fetch_portfolio(strict_operational=True)

    assert rows[0]["shares"] == 10.0
    assert rows[0]["market_value_base"] == 25.0
    assert rows[0]["nav_base"] == 100.0
    assert rows[0]["currency"] == "EUR"
    assert rows[0]["base_currency"] == "USD"


def test_operational_sheet_read_rejects_malformed_numeric_cells(monkeypatch) -> None:
    headers = [
        "ticker",
        "shares",
        "avg_cost",
        "currency",
        "market_value_base",
        "nav_base",
        "base_currency",
    ]
    monkeypatch.setattr(gsheets, "SPREADSHEET_ID", "fixture")
    monkeypatch.setattr(
        gsheets,
        "_get_service",
        lambda: _SheetService([headers, ["FRA:2DG", "bad", "2", "EUR", "25", "100", "USD"]]),
    )

    with pytest.raises(ValueError, match="shares"):
        fetch_portfolio(strict_operational=True)
