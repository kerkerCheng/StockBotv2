from __future__ import annotations

from copy import deepcopy

import pytest

from decision_lab.beta_policy import load_beta_policy
from decision_lab.portfolio_risk import (
    append_risk_snapshot,
    build_portfolio_components,
    event_search_requests,
    read_latest_risk_snapshot,
    risk_changes,
)


def _snapshot(*, tsmc: float) -> dict:
    return {
        "schema_version": "portfolio-risk-snapshot-v1",
        "as_of": "2026-07-29T00:00:00+00:00",
        "policy_version": "test",
        "etf_leverage": {"nominal_weight": 0.06, "effective_weight": 0.16},
        "loan_leverage_weight": 0.0,
        "combined_leverage_weight": 0.16,
        "alpha_total_weight": 0.02,
        "issuer_exposures": {
            "TSMC": {
                "direct_weight": 0.10,
                "indirect_weight": tsmc - 0.10,
                "total_weight": tsmc,
            }
        },
        "snapshot_digest": "x",
    }


def test_known_issuer_lookthrough_separates_direct_indirect_and_alpha() -> None:
    policy = load_beta_policy()
    rows = [
        {"ticker": "CASH", "bucket": "cash", "market_value_base": 10, "nav_base": 100, "base_currency": "USD"},
        {"ticker": "0050.TW", "market_value_base": 40, "nav_base": 100, "base_currency": "USD"},
        {"ticker": "2330.TW", "market_value_base": 10, "nav_base": 100, "base_currency": "USD"},
        {
            "ticker": "FRA:2DG",
            "company_id": "co:sivers_semiconductors",
            "market_value_base": 40,
            "nav_base": 100,
            "base_currency": "USD",
        },
    ]

    result = build_portfolio_components(rows, policy)

    assert result["alpha_total_base"] == 40
    assert result["issuer_direct_base"]["TSMC"] == 10
    assert result["issuer_indirect_base"]["TSMC"] == pytest.approx(23.476)
    assert result["issuer_direct_base"]["SIVE.ST"] == 40
    assert not any("mapping_unresolved" in item for item in result["blockers"])


def test_small_issuer_move_inside_same_band_stays_silent() -> None:
    policy = load_beta_policy()
    previous = _snapshot(tsmc=0.293)
    current = _snapshot(tsmc=0.295)

    changes = risk_changes(current, previous, policy)

    assert not any(item["metric"] == "issuer_exposure:TSMC" for item in changes)


def test_concentrated_issuer_price_drop_creates_ephemeral_search_packet() -> None:
    policy = load_beta_policy()
    snapshot = _snapshot(tsmc=0.30)
    current = {
        "data_status": "observed",
        "session_date": "2026-07-29",
        "return_1d": -0.05,
    }
    previous = deepcopy(current) | {"session_date": "2026-07-28", "return_1d": -0.01}

    requests = event_search_requests(
        snapshot,
        observations_by_benchmark={"tsmc": current},
        history_by_benchmark={"tsmc": [current, previous]},
        policy=policy,
    )

    assert len(requests) == 1
    assert requests[0]["issuer"] == "TSMC"
    assert requests[0]["verification_status"] == "unverified"
    assert requests[0]["persistence"] == "none"
    assert requests[0]["authority_effect"] == "none"


def test_private_risk_history_is_append_only_and_idempotent(tmp_path) -> None:
    path = tmp_path / "risk.jsonl"
    first = _snapshot(tsmc=0.293)
    second = _snapshot(tsmc=0.295) | {
        "as_of": "2026-07-30T00:00:00+00:00",
        "snapshot_digest": "y",
    }

    assert append_risk_snapshot(path, first) is True
    assert append_risk_snapshot(path, first) is False
    assert append_risk_snapshot(path, second) is True
    assert read_latest_risk_snapshot(path) == second
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def _exposure_rows(*, nav, cash, plain, tqqq=0.0):
    rows = [
        {"ticker": "CASH", "bucket": "cash", "market_value_base": cash,
         "nav_base": nav, "base_currency": "USD"},
        {"ticker": "LON:VWRA", "bucket": "大盤", "market_value_base": plain,
         "nav_base": nav, "base_currency": "USD"},
    ]
    if tqqq:
        rows.append({"ticker": "TQQQ", "bucket": "槓桿", "market_value_base": tqqq,
                     "nav_base": nav, "base_currency": "USD"})
    return rows


def _exposure_snapshot(rows, *, drawn=0.0, callable_debt=0.0):
    from decision_lab.beta_policy import load_beta_policy
    from decision_lab.portfolio_risk import (
        build_portfolio_components,
        compose_risk_snapshot,
    )

    policy = load_beta_policy()
    components = build_portfolio_components(rows, policy=policy)
    return compose_risk_snapshot(
        components,
        {"drawn_debt_base": drawn, "callable_drawn_debt_base": callable_debt},
        policy,
        as_of="2026-08-01T00:00:00+00:00",
    )


def test_total_exposure_does_not_double_count_borrowed_money() -> None:
    """借來的錢已買成持股、本來就在 market_total_base 裡，不可再加一次負債。

    分母也必須是自有資本（nav 為毛資產、不扣負債），否則同一筆借款會被
    計入兩次而高估曝險。開發時曾寫成 (曝險+負債)/nav，使全額提款顯示 1.97x
    而非正確的 1.53x。
    """
    # 借 100 元買進 100 元持股：毛資產與持股同時增加
    borrowed = _exposure_snapshot(
        _exposure_rows(nav=1100.0, cash=100.0, plain=1000.0), drawn=100.0
    )
    # 完全相同的曝險、但用自有資金
    unlevered = _exposure_snapshot(_exposure_rows(nav=1000.0, cash=100.0, plain=900.0))

    assert borrowed["total_exposure_weight"] == pytest.approx(1000.0 / 1000.0)
    assert unlevered["total_exposure_weight"] == pytest.approx(900.0 / 1000.0)


def test_total_exposure_cap_blocks_borrowing_that_etf_caps_miss() -> None:
    """修正前的 🔴：hard_blocks 只看槓桿 ETF，借款完全不受約束。"""
    from decision_lab.beta_policy import load_beta_policy

    cap = load_beta_policy()["risk"]["total_exposure_cap"]
    # 全部是 1x 持股，槓桿 ETF 為零——舊 ETF cap 完全擋不到
    over = _exposure_snapshot(
        _exposure_rows(nav=1000.0 + 1200.0, cash=0.0, plain=1000.0 + 1200.0),
        drawn=1200.0,
    )
    assert over["total_exposure_weight"] >= cap
    assert "total_exposure_cap_reached" in over["hard_blocks"]
    assert not any("etf_leverage" in b for b in over["hard_blocks"]), (
        "此情境沒有任何槓桿 ETF，舊 cap 本來就擋不到——這正是新硬擋存在的理由"
    )


def test_callable_debt_is_capped_separately_from_non_callable() -> None:
    """IB margin 在遠早於自有資本歸零之前就會強制平倉，不可與 30 年期額度同視。"""
    rows = _exposure_rows(nav=1000.0, cash=100.0, plain=900.0)
    assert _exposure_snapshot(rows, drawn=0.0)["hard_blocks"] == []
    blocked = _exposure_snapshot(rows, drawn=1.0, callable_debt=1.0)
    assert "callable_debt_cap_reached" in blocked["hard_blocks"]


def test_wipeout_threshold_is_reported_with_the_multiple() -> None:
    """維持 L 倍時指數跌 100/L% 即自有資本歸零；這是接受風險水準的唯一直觀數字。"""
    snap = _exposure_snapshot(_exposure_rows(nav=1000.0, cash=0.0, plain=1000.0))
    assert snap["total_exposure_weight"] == pytest.approx(1.0)
    assert snap["wipeout_index_drawdown"] == pytest.approx(1.0)
