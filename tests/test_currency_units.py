"""報價單位 → 結算幣別正規化的行為契約。

事發（2026-08-05）：IQE.L 的 Engine D snapshot 長期 quarantined。根因是把「交易所
報價單位」與「結算幣別」塞進同一個欄位——LSE 以便士報價，Yahoo 回傳 ``GBp``，而
每一個下游驗證器都寫死「3 碼大寫 ISO code」。兩種修法都會壞：不改就整份行情被
擋；把 registry 直接改成 ``GBP`` 則價格差 100 倍。

本測試釘住的是「以後只會越來越多」的那部分：ISO code 的新市場（TWD／JPY…）不必
改任何 config 就能用；minor unit 只加一列 config；兩者都不是時 fail closed。
"""
from __future__ import annotations

import pytest

from identity.currency import (
    is_settlement_currency,
    resolve_quote_unit,
    settlement_currency,
)
from identity.registry import IdentityRegistry
from engine_c.market_data import build_fx_snapshot, build_tradeability_snapshot


# ── registry 正規化 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("code", ["USD", "TWD", "SEK", "EUR", "JPY", "HKD"])
def test_iso_currencies_need_no_registration(code: str) -> None:
    """新市場只要以 ISO code 報價就直接可用——這是「越來越多」的主要路徑。"""

    unit = resolve_quote_unit(code)

    assert unit is not None
    assert unit.currency == code
    assert unit.factor == 1.0
    assert not unit.is_minor_unit


def test_registered_minor_unit_maps_to_iso_currency_with_factor() -> None:
    unit = resolve_quote_unit("GBp")

    assert unit is not None
    assert unit.quote_code == "GBp"
    assert unit.currency == "GBP"
    assert unit.is_minor_unit
    assert unit.to_settlement(44.8) == pytest.approx(0.448)


def test_case_sensitive_lookup_keeps_gbp_and_gbp_pence_distinct() -> None:
    """GBp 與 GBP 只差大小寫；折疊大小寫會讓結算幣別被誤當成便士。"""

    assert settlement_currency("GBp") == "GBP"
    assert resolve_quote_unit("GBp").factor == 0.01
    assert resolve_quote_unit("GBP").factor == 1.0


@pytest.mark.parametrize("code", ["", "  ", "US", "USDD", "US1", None, 123, "元"])
def test_unresolvable_codes_fail_closed(code) -> None:
    assert resolve_quote_unit(code) is None
    assert settlement_currency(code) is None


def test_is_settlement_currency_is_strict_about_canonical_form() -> None:
    assert is_settlement_currency("TWD")
    assert not is_settlement_currency("twd")  # 未正規化
    assert not is_settlement_currency("GBp")  # minor unit
    assert not is_settlement_currency("")


# ── company identity 正規化 ─────────────────────────────────────────────────


def _registry(entries: list[dict]) -> IdentityRegistry:
    import json
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "identity.json"
        path.write_text(
            json.dumps({"version": 1, "companies": entries}), encoding="utf-8"
        )
        return IdentityRegistry.from_path(path)


def test_registry_exposes_settlement_currency_and_raw_quote_unit() -> None:
    registry = _registry(
        [
            {"company_id": "co:x", "research_ticker": "X.L", "market_currency": "GBp"},
            {"company_id": "co:y", "research_ticker": "Y.TW", "market_currency": "TWD"},
        ]
    )

    lse = registry.company("co:x")
    twse = registry.company("co:y")

    assert lse.market_currency == "GBP"
    assert lse.market_quote_unit == "GBp"
    assert twse.market_currency == "TWD"
    assert twse.market_quote_unit == "TWD"


def test_registry_fails_closed_on_unregistered_quote_unit() -> None:
    registry = _registry(
        [{"company_id": "co:x", "research_ticker": "X", "market_currency": "XYZZY"}]
    )

    company = registry.company("co:x")

    # 幣別解析不出來，但原始字串留著——identity 層才能區分「沒填」與「未登記」。
    assert company.market_currency is None
    assert company.market_quote_unit == "XYZZY"


# ── 行情快照換算 ─────────────────────────────────────────────────────────────


def _rows(close: float) -> list[dict]:
    return [
        {
            "as_of": f"2026-07-{day:02d}T16:00:00+00:00",
            "close": close,
            "volume": 1000.0,
        }
        for day in range(1, 22)
    ]


def test_minor_unit_price_is_converted_and_original_quote_retained() -> None:
    result = build_tradeability_snapshot(
        ticker="IQE.L",
        currency="GBp",
        rows=_rows(44.8),
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "observed"
    assert result["currency"] == "GBP"
    assert result["price"] == pytest.approx(0.448)
    assert result["quote_currency"] == "GBp"
    assert result["quote_price"] == pytest.approx(44.8)
    assert result["quote_factor"] == pytest.approx(0.01)
    # adv20 是股數，不隨報價單位換算。
    assert result["adv20"] == pytest.approx(1000.0)
    # 換算是已驗證的單位處理，不該退化成 market_unit_unverified。
    assert result["unit_status"] == "ok"


def test_iso_currency_snapshot_is_unchanged_and_carries_no_quote_fields() -> None:
    result = build_tradeability_snapshot(
        ticker="2330.TW",
        currency="TWD",
        rows=_rows(1085.0),
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "observed"
    assert result["currency"] == "TWD"
    assert result["price"] == pytest.approx(1085.0)
    assert "quote_currency" not in result
    assert "quote_factor" not in result


def test_unregistered_quote_unit_quarantines_with_actionable_blocker() -> None:
    result = build_tradeability_snapshot(
        ticker="X",
        currency="pence",
        rows=_rows(10.0),
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "quarantined"
    assert "market_quote_unit_unregistered" in result["blockers"]


def test_missing_currency_is_still_reported_as_invalid_not_unregistered() -> None:
    """「沒填」與「填了但未登記」要能分辨——修法不同。"""

    result = build_tradeability_snapshot(
        ticker="X",
        currency="",
        rows=_rows(10.0),
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert "market_currency_invalid" in result["blockers"]


# ── FX pair ─────────────────────────────────────────────────────────────────


def test_fx_pair_normalizes_minor_unit_to_settlement_currency() -> None:
    """匯率本身不隨報價單位改變；換算倍率已在價格側套用，這裡再折一次就重複。"""

    result = build_fx_snapshot(
        pair="GBp/USD",
        rows=[{"as_of": "2026-08-04T00:00:00+00:00", "rate": 1.3447}],
        fetched_at="2026-08-05T00:00:00+00:00",
        source="fixture://fx",
    )

    assert result["status"] == "observed"
    assert result["pair"] == "GBP/USD"
    assert result["rate"] == pytest.approx(1.3447)


def test_fx_pair_rejects_unresolvable_side() -> None:
    result = build_fx_snapshot(
        pair="pence/USD",
        rows=[{"as_of": "2026-08-04T00:00:00+00:00", "rate": 1.0}],
        fetched_at="2026-08-05T00:00:00+00:00",
        source="fixture://fx",
    )

    assert result["status"] == "malformed"
