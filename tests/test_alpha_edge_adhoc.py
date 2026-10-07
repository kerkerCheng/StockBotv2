"""研究時判邊緣（failure log #43）：名冊外的代號也能判——同一個 `edge_state`、同一份門檻，缺的輸入用 yfinance 補、逐欄標來源。

三個原始案例寫死成假資料（不打網路）：雙鴻 3324.TWO（分析師 16 家 → 非邊緣，上一版讀圖目測寫成「邊緣大小」）、
日東紡 3110.T（9 家、約 45 億美元 → 邊緣）、波若威 3163.TWO（家數取不到 → 邊緣無法量）。
"""
from __future__ import annotations

from alpha.providers.edge import adhoc_edge_states

LIMITS = {"market_cap_max_usd": 10_000_000_000.0, "analyst_count_max": 12, "effective_from": "2026-09-19", "version": 1}
FX = {"TWD/USD": 0.031, "JPY/USD": 0.0067, "GBP/USD": 1.27}

INFO = {
    "3324.TWO": {"currentPrice": 1525.0, "sharesOutstanding": 93_076_000, "currency": "TWD", "numberOfAnalystOpinions": 16},
    "3110.T": {"currentPrice": 3675.0, "sharesOutstanding": 182_025_000, "currency": "JPY", "numberOfAnalystOpinions": 9},
    "3163.TWO": {"currentPrice": 702.0, "sharesOutstanding": 95_000_000, "currency": "TWD", "numberOfAnalystOpinions": None},
    # LSE 小單位報價：60 便士 × 10 億股 ＝ 6 億英鎊 ≈ 7.6 億美元（不換算會多 100 倍、被當成大型股）
    "SMALL.L": {"currentPrice": 60.0, "sharesOutstanding": 1_000_000_000, "currency": "GBp", "numberOfAnalystOpinions": 3},
    "ODD.X": {"currentPrice": 10.0, "sharesOutstanding": 1_000_000, "currency": "ZZpx", "numberOfAnalystOpinions": 2},
}


def _run(tickers, *, registry_inputs=None, fetch=None):
    return adhoc_edge_states(
        tickers, fetch_info=fetch or (lambda t: INFO[t]), fx_cache=dict(FX), thresholds=LIMITS,
        registry_inputs=registry_inputs or (lambda ts: {}))


def test_the_three_original_cases() -> None:
    rows = _run(["3324.TWO", "3110.T", "3163.TWO"])
    assert rows["3324.TWO"]["state"] == "not_edge"
    assert rows["3324.TWO"]["reasons"] == ["coverage_over_edge"]          # 市值在線內，敗在覆蓋太厚
    assert rows["3110.T"]["state"] == "edge"
    assert 4.0e9 < rows["3110.T"]["market_cap_usd"] < 5.0e9
    assert rows["3163.TWO"]["state"] == "unmeasurable"
    assert rows["3163.TWO"]["missing"] == ["coverage_unavailable"]       # 缺的是家數，照實寫，不當成邊緣


def test_minor_unit_quote_is_converted_before_usd() -> None:
    row = _run(["SMALL.L"])["SMALL.L"]
    assert row["state"] == "edge"
    assert 0.7e9 < row["market_cap_usd"] < 0.8e9


def test_unregistered_quote_unit_fails_closed_with_a_reason() -> None:
    row = _run(["ODD.X"])["ODD.X"]
    assert row["state"] == "unmeasurable"
    assert "market_cap_unavailable" in row["missing"]
    assert "未登記" in (row["market_cap_absence"] or "")


def test_registry_values_win_and_only_missing_fields_are_filled() -> None:
    canonical = {"3110.T": {"market_cap_usd": 4.4e9, "market_cap_absence": None, "analyst_count": None}}
    row = _run(["3110.T"], registry_inputs=lambda ts: canonical)["3110.T"]
    assert row["market_cap_usd"] == 4.4e9                                 # 名冊＋Engine C 的值不被覆蓋
    assert row["analyst_count"] == 9                                      # 缺的那一欄才用 yfinance
    assert row["sources"] == {"market_cap": "名冊＋Engine C", "analyst_count": "yfinance numberOfAnalystOpinions"}


def test_fetch_failure_is_reported_not_swallowed() -> None:
    def boom(_t):
        raise RuntimeError("Too Many Requests")

    row = _run(["3324.TWO"], fetch=boom)["3324.TWO"]
    assert row["state"] == "unmeasurable"
    assert "Too Many Requests" in (row["market_cap_absence"] or "")
