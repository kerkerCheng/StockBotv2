"""Alpha live 部位事件監控。

回歸錨點是 2026-08-24 的真實事件：COHR（唯一一筆 live fill）單日 -4.85%，而當時
系統沒有任何路徑會發現。這裡用同一段真實收盤序列當 fixture，確保它會觸發——
「beta 那套對 alpha 恆不觸發」是本模組存在的理由（L14 第 4 點的恆滅測試）。
"""
from __future__ import annotations

import pytest

from decision_lab.alpha_event_monitor import alpha_event_search_requests
from thesis.investment_policy import PolicyError, validate_policy


POLICY = {"live_position_monitor": {"return_1d_at_most": -0.04, "history_sessions": 10}}

# COHR 實際收盤（yfinance，2026-08-25 取得）。
COHR_SERIES = [
    {"session_date": "2026-08-17", "close": 351.22},
    {"session_date": "2026-08-18", "close": 306.43},  # -12.75%
    {"session_date": "2026-08-19", "close": 287.47},  # -6.19%
    {"session_date": "2026-08-20", "close": 290.03},
    {"session_date": "2026-08-21", "close": 289.52},
    {"session_date": "2026-08-24", "close": 275.49},  # -4.85%
]

POSITION = {
    "cohort_id": "dc_957bff3701ea4e46d962bfb9ff0932c8",
    "company_id": "co:coherent",
    "ticker": "COHR",
    "shares": 10.0,
    "entry_price": 316.23,
    "currency": "USD",
    "selected_weight": 0.00732,
}


def test_real_drop_fires_and_reports_loss_since_entry() -> None:
    requests = alpha_event_search_requests(
        [POSITION], series_by_ticker={"COHR": COHR_SERIES}, policy=POLICY
    )

    assert len(requests) == 1
    packet = requests[0]
    assert packet["ticker"] == "COHR"
    assert packet["session_date"] == "2026-08-24"
    assert packet["return_1d"] == pytest.approx(-0.0485, abs=1e-3)
    # 進場價 316.23 → 275.49，使用者真正在意的是這個數字，不是單日。
    assert packet["return_since_entry"] == pytest.approx(-0.1288, abs=1e-3)
    # 觸發依據是「有 live fill」而非曝險占比——0.732% 遠低於 beta 的 20% 門檻。
    assert packet["trigger_basis"] == "live_fill_exists"
    assert packet["position_weight"] == pytest.approx(0.00732)


def test_packet_never_carries_authority() -> None:
    packet = alpha_event_search_requests(
        [POSITION], series_by_ticker={"COHR": COHR_SERIES}, policy=POLICY
    )[0]

    assert packet["persistence"] == "none"
    assert packet["authority_effect"] == "none"
    assert packet["verification_status"] == "unverified"


def test_consecutive_drop_does_not_refire() -> None:
    """08-19（-6.19%）緊接在 08-18（-12.75%）之後，屬同一段下跌，不重發。"""

    through_19 = COHR_SERIES[:3]
    requests = alpha_event_search_requests(
        [POSITION], series_by_ticker={"COHR": through_19}, policy=POLICY
    )
    assert requests == []

    # 但 08-18 這根本身是首次跨越，必須發。
    through_18 = COHR_SERIES[:2] + [{"session_date": "2026-08-14", "close": 325.83}]
    first_cross = alpha_event_search_requests(
        [POSITION],
        series_by_ticker={"COHR": sorted(through_18, key=lambda r: r["session_date"])},
        policy=POLICY,
    )
    assert len(first_cross) == 1
    assert first_cross[0]["session_date"] == "2026-08-18"


def test_quiet_days_produce_nothing() -> None:
    quiet = [
        {"session_date": "2026-08-20", "close": 290.03},
        {"session_date": "2026-08-21", "close": 289.52},
    ]
    assert (
        alpha_event_search_requests(
            [POSITION], series_by_ticker={"COHR": quiet}, policy=POLICY
        )
        == []
    )


def test_unlisted_position_is_skipped_not_crashed() -> None:
    """co:agility_robotics 未上市（research_ticker=null），沒有行情可監控。"""

    unlisted = dict(POSITION, ticker=None, company_id="co:agility_robotics")
    assert (
        alpha_event_search_requests(
            [unlisted], series_by_ticker={"COHR": COHR_SERIES}, policy=POLICY
        )
        == []
    )


def test_missing_threshold_disables_monitor_rather_than_guessing() -> None:
    assert (
        alpha_event_search_requests(
            [POSITION], series_by_ticker={"COHR": COHR_SERIES}, policy={}
        )
        == []
    )


def test_policy_rejects_non_negative_threshold() -> None:
    """>= 0 的門檻會讓每天都觸發——L14 第 4 點的『恆亮』失效型態。"""

    base = {
        "policy_version": "2026-07-29.2",
        "single_position_nav_cap": 0.05,
        "minimum_open_conviction": 3,
        "conviction_coefficients": {"3": 0.08, "4": 0.1, "5": 0.15},
        "analyst_coverage_threshold": 8,
        "analyst_coverage_discount_levels": 1,
        "minimum_holding_days": 90,
    }
    with pytest.raises(PolicyError, match="must be negative"):
        validate_policy(
            dict(base, live_position_monitor={"return_1d_at_most": 0.0, "history_sessions": 10})
        )


def test_repository_policy_registers_the_monitor() -> None:
    """`validate_policy` 會丟掉未登記的 key——沒有這條，加了 config 也會靜默失效。"""

    from thesis.investment_policy import load_policy

    monitor = load_policy()["live_position_monitor"]
    assert monitor["return_1d_at_most"] < 0
    assert monitor["history_sessions"] >= 2
