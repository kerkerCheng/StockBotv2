from __future__ import annotations

from decision_lab.identity import resolve_identity
from fetchers.gsheets import get_execution_aliases


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
