"""成交路徑硬擋（`risk/hard_caps.py`）：5% 單筆、ETF 槓桿 cap、量不到就 fail closed。

這兩道是 `AGENTS.md` 唯二的資本硬擋。它們原本住在舊 Decision Store 的 live choice 路徑
（Phase 0 凍結），搬到成交路徑後這裡守三件事：

1. **規則本身**：alpha 標的比 5% 單筆；槓桿 ETF 比 nominal／effective 兩個 cap；未槓桿 beta 無硬擋。
2. **Missing != Zero**：NAV 缺席、不一致、匯率缺席都是 `unmeasurable`，不是「持有 0% 所以放行」。
3. **賣出不適用**：不增加曝險的動作不被煞車擋住。
"""
from __future__ import annotations

import pytest

from risk.hard_caps import HardCapVerdict, check_trade_hard_caps, gross_in_base_currency


INVESTMENT_POLICY = {"single_position_nav_cap": 0.05}
BETA_POLICY = {
    "instruments": [
        {"ticker": "QQQ", "sheet_aliases": ["QQQ"], "sleeve": "beta_tilt",
         "leverage_multiple": 1.0, "issuer_loads": {}},
        {"ticker": "TQQQ", "sheet_aliases": ["TQQQ"], "sleeve": "beta_leverage",
         "leverage_multiple": 3.0, "issuer_loads": {}},
    ],
    "capital": {"cash_bucket_aliases": ["cash"]},
    "risk": {"leveraged_nominal_cap": 0.2, "leveraged_effective_cap": 0.4},
}


def _rows(nav: float = 100_000.0, **positions: float) -> list[dict]:
    rows = []
    invested = 0.0
    for ticker, value in positions.items():
        rows.append({"ticker": ticker, "bucket": "ALPHA" if ticker not in ("QQQ", "TQQQ") else "BETA",
                     "market_value_base": value, "nav_base": nav, "base_currency": "USD",
                     "currency": "USD", "shares": 1.0})
        invested += value
    rows.append({"ticker": "CASH", "bucket": "CASH", "market_value_base": nav - invested,
                 "nav_base": nav, "base_currency": "USD", "currency": "USD", "shares": 0.0})
    return rows


def _check(rows, *, symbol: str, side: str = "buy", gross_base=1_000.0, **kw) -> HardCapVerdict:
    return check_trade_hard_caps(
        rows, symbol=symbol, side=side, gross_base=gross_base,
        investment_policy=INVESTMENT_POLICY, beta_policy=BETA_POLICY, **kw,
    )


def test_alpha_buy_under_the_single_position_cap_passes() -> None:
    verdict = _check(_rows(AXTI=3_000.0), symbol="AXTI", gross_base=1_000.0)
    assert verdict.status == "pass"
    assert verdict.allows
    assert verdict.measures["post_trade_weight"] == pytest.approx(0.04)


def test_alpha_buy_that_crosses_five_percent_is_blocked_on_total_not_on_the_single_lot() -> None:
    """上限管的是部位總量：已持有 4.5% 再買 1% 必須被擋，不是只看這一筆 1%。"""
    verdict = _check(_rows(AXTI=4_500.0), symbol="AXTI", gross_base=1_000.0)
    assert verdict.status == "blocked"
    assert not verdict.allows
    assert verdict.breaches == ("single_position_nav_cap_reached",)
    assert verdict.measures["post_trade_weight"] == pytest.approx(0.055)


def test_log_only_treats_the_sheet_as_post_trade_state() -> None:
    """--log-only 時 Sheet 已含這筆成交，不得再加一次總額（否則同一筆算兩次）。"""
    verdict = _check(_rows(AXTI=4_800.0), symbol="AXTI", gross_base=1_000.0, already_in_sheet=True)
    assert verdict.status == "pass"
    assert verdict.measures["post_trade_weight"] == pytest.approx(0.048)


def test_unlevered_beta_instrument_has_no_hard_cap() -> None:
    """QQQ 之類的 beta 核心本來就超過 5%：對它套單筆上限只會讓煞車變噪音（L14）。"""
    verdict = _check(_rows(QQQ=40_000.0), symbol="QQQ", gross_base=10_000.0)
    assert verdict.status == "pass"
    assert verdict.measures["rule"] == "beta_unlevered_no_hard_cap"


def test_leveraged_etf_is_checked_on_both_nominal_and_effective_weight() -> None:
    # 已持 TQQQ 15% nominal（45% effective）：再買 6% → nominal 21%（>20%）、effective 63%（>40%）。
    verdict = _check(_rows(TQQQ=15_000.0), symbol="TQQQ", gross_base=6_000.0)
    assert verdict.status == "blocked"
    assert set(verdict.breaches) == {
        "etf_leverage_nominal_cap_reached", "etf_leverage_effective_cap_reached",
    }
    assert verdict.measures["post_trade_nominal_weight"] == pytest.approx(0.21)
    assert verdict.measures["post_trade_effective_weight"] == pytest.approx(0.63)


def test_leveraged_etf_can_breach_effective_cap_alone() -> None:
    # nominal 14%（<20%）但 effective 42%（>40%）：兩個指標不得混用，各自比自己的 cap。
    verdict = _check(_rows(TQQQ=10_000.0), symbol="TQQQ", gross_base=4_000.0)
    assert verdict.status == "blocked"
    assert verdict.breaches == ("etf_leverage_effective_cap_reached",)


def test_sell_is_not_applicable_even_when_nav_is_unreadable() -> None:
    verdict = _check(None, symbol="AXTI", side="sell", gross_base=None)
    assert verdict.status == "not_applicable"
    assert verdict.allows


@pytest.mark.parametrize(
    ("rows", "expect"),
    [
        (None, "讀不到"),
        ([{"ticker": "AXTI", "bucket": "ALPHA", "market_value_base": 100.0, "currency": "USD"}],
         "holdings_nav_missing"),
        ([{"ticker": "AXTI", "bucket": "ALPHA", "market_value_base": 100.0, "nav_base": 1_000.0,
           "base_currency": "USD"},
          {"ticker": "CASH", "bucket": "CASH", "market_value_base": 900.0, "nav_base": 2_000.0,
           "base_currency": "USD"}],
         "holdings_nav_inconsistent"),
    ],
)
def test_unmeasurable_nav_fails_closed_instead_of_reading_zero_exposure(rows, expect) -> None:
    verdict = _check(rows, symbol="AXTI", gross_base=10.0)
    assert verdict.status == "unmeasurable"
    assert not verdict.allows
    assert any(expect in reason for reason in verdict.reasons)


def test_missing_fx_is_unmeasurable_not_a_pass() -> None:
    amount, reason = gross_in_base_currency(
        gross=1_000.0, trade_currency="TWD", base_currency="USD", fx_to_base=None,
    )
    assert amount is None and "fx-to-base" in reason
    verdict = _check(_rows(AXTI=0.0), symbol="3105.TWO", gross_base=None, gross_reason=reason)
    assert verdict.status == "unmeasurable"
    assert not verdict.allows


def test_fx_converts_when_given_and_same_currency_needs_none() -> None:
    assert gross_in_base_currency(gross=100.0, trade_currency="usd", base_currency="USD",
                                  fx_to_base=None) == (100.0, None)
    amount, reason = gross_in_base_currency(gross=32_000.0, trade_currency="TWD",
                                            base_currency="USD", fx_to_base=0.03125)
    assert reason is None and amount == pytest.approx(1_000.0)


def test_verdict_serialises_with_lists_for_the_trade_log_receipt() -> None:
    verdict = _check(_rows(AXTI=4_500.0), symbol="AXTI", gross_base=1_000.0)
    payload = verdict.to_dict()
    assert payload["status"] == "blocked"
    assert payload["breaches"] == ["single_position_nav_cap_reached"]
    assert isinstance(payload["reasons"], list) and payload["reasons"]
