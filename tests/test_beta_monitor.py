"""Engine D beta monitor separates timing from hard contribution capacity。"""
from __future__ import annotations

from copy import deepcopy

import pytest

from decision_lab.beta_monitor import build_beta_monitor, render_beta_monitor_markdown, signal_state
from decision_lab.beta_policy import load_beta_policy, unique_benchmarks


NOW = "2026-07-28T00:00:00+00:00"


def _observation(
    key: str,
    *,
    drawdown: float = -0.25,
    rsi: float = 35.0,
    histogram_slope: float = 0.1,
    distance_200: float = 0.02,
    slope_50: float = 0.01,
):
    return {
        "benchmark_key": key,
        "data_status": "observed",
        "fetched_at": NOW,
        "session_date": "2026-07-27",
        "return_1d": -0.01,
        "return_5d": -0.03,
        "return_20d": -0.08,
        "rsi_14": rsi,
        "drawdown_252": drawdown,
        "macd_histogram": -0.2,
        "macd_histogram_slope": histogram_slope,
        "distance_sma_20": -0.03,
        "distance_sma_50": -0.05,
        "distance_sma_200": distance_200,
        "sma_50_slope_5": slope_50,
        "realized_vol_20": 0.3,
        "realized_vol_60": 0.25,
        "blockers": [],
    }


def _observations(policy, **kwargs):
    return {
        item["benchmark_key"]: _observation(item["benchmark_key"], **kwargs)
        for item in unique_benchmarks(policy)
    }


def _holdings(*, cash: float = 10.0, tqqq: float = 0.0, other: list[dict] | None = None):
    other_rows = list(other or [])
    residual = 100.0 - cash - tqqq - sum(float(row["market_value_base"]) for row in other_rows)
    rows = [
        {
            "ticker": "CASH",
            "bucket": "cash",
            "market_value_base": cash,
            "nav_base": 100.0,
            "base_currency": "USD",
        },
        {
            "ticker": "TQQQ",
            "bucket": "槓桿",
            "market_value_base": tqqq,
            "nav_base": 100.0,
            "base_currency": "USD",
        },
    ]
    if residual > 0:
        rows.append(
            {
                "ticker": "LON:VWRA",
                "bucket": "大盤",
                "market_value_base": residual,
                "nav_base": 100.0,
                "base_currency": "USD",
            }
        )
    rows.extend(other_rows)
    return rows


def _capital_rows(*, credit_limit: str = "1000", drawn_amount: str = "0") -> list[dict]:
    common = {"as_of": "2026-07-28", "currency": "USD"}
    return [
        {
            **common,
            "record_id": "cash_floor_01",
            "capital_type": "cash_floor",
            "amount": "1",
        },
        {
            **common,
            "record_id": "credit_facility_01",
            "capital_type": "credit_facility",
            "limit_amount": credit_limit,
            "drawn_amount": drawn_amount,
            "annual_rate_pct": "3.1",
            "interest_accrual": "daily",
            "facility_term_years": "30",
            "repayment_structure": "interest_only_bullet_principal_at_maturity",
        },
    ]


def test_signal_state_uses_macd_and_ma_as_pace_guard_not_extra_votes() -> None:
    policy = load_beta_policy()

    bullish = signal_state(_observation("qqq"), policy)
    bearish = signal_state(
        _observation("qqq", histogram_slope=0.1, distance_200=-0.1, slope_50=-0.02),
        policy,
    )

    assert bullish["tier"] == "deep"
    assert bullish["pace"] == 0.5
    assert bearish["tier"] == "deep"
    assert bearish["pace"] == 0.25


def test_stretched_above_sma200_downgrades_pace_even_on_a_real_drawdown() -> None:
    """回撤 tier 只看「跌了多少」，看不出「跌之前漲了多少」。

    2026-07-31 實況：SOXX 距高點 -23%、RSI 42.5，看似便宜，但仍在 200 日均線
    上方 +25.7%——它跌得多是因為先漲得更多。以 30 年累積為目標時，買在趨勢
    之上不該與買在趨勢附近同速。
    """
    policy = load_beta_policy()
    threshold = policy["signal"]["stretched_above_sma200"]
    base = dict(
        benchmark_key="soxx",
        data_status="observed",
        drawdown_252=-0.23,
        rsi_14=42.5,
        macd_histogram_slope=0.1,
        sma_50_slope_5=-0.003,
        blockers=[],
    )

    stretched = signal_state({**base, "distance_sma_200": threshold + 0.05}, policy)
    near_trend = signal_state({**base, "distance_sma_200": 0.03}, policy)

    assert stretched["tier"] == near_trend["tier"], "只降 pace，不改 tier 判定"
    assert stretched["stretched_above_sma200"] is True
    assert near_trend["stretched_above_sma200"] is False
    # guard 作用在訊號自算的 pace 上
    assert stretched["signal_pace_raw"] < near_trend["signal_pace_raw"]
    assert stretched["pace"] in policy["signal"]["allowed_paces"]
    # 但它壓不到 baseline 以下：baseline 有實測證據（gate 現金投入輸定投 8.5%），
    # stretched guard 是未驗證的推論——未驗證的機制不得覆蓋有證據的下限。
    baseline = policy["signal"]["baseline_pace"]
    assert stretched["pace"] >= baseline
    assert stretched["pace_source"] == "baseline"


def test_ranges_share_one_frozen_deployable_cash_budget() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=10.0),
        capital_authority_rows=_capital_rows(),
        as_of=NOW,
        policy=policy,
    )

    reviews = [item for item in report["items"] if item["action"] == "CONTRIBUTE REVIEW"]
    assert report["portfolio"]["deployable_cash_base"] == pytest.approx(9.0)
    assert sum(item["supported_order_range_base"][1] for item in reviews) <= 9.0
    assert report["portfolio"]["allocated_review_base"] == pytest.approx(
        sum(item["supported_order_range_base"][1] for item in reviews)
    )
    assert report["capital_scope"] == "shared_cash_pool"
    assert report["policy_mode"] == "paper_observation"


def test_shared_cash_pool_subtracts_only_floor_and_never_uses_credit() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=10.0),
        capital_authority_rows=_capital_rows(),
        as_of=NOW,
        policy=policy,
    )
    larger_credit = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=10.0),
        capital_authority_rows=_capital_rows(credit_limit="999999"),
        as_of=NOW,
        policy=policy,
    )

    assert report["portfolio"]["deployable_cash_base"] == pytest.approx(9.0)
    assert report["self_funded_supported_range"] == larger_credit["self_funded_supported_range"]
    assert report["contingent_credit_available"]["undrawn_amount_base"] == 1000.0
    assert report["loan_funded_supported_range"]["status"] == "manual_review_required"
    rendered = render_beta_monitor_markdown(report)
    assert "共同現金池計算" in rendered
    assert "cash floor" in rendered
    assert "未動用貸款額度：USD 1,000" in rendered
    assert "不算自有現金" in rendered


def test_missing_cash_floor_authority_fails_shared_cash_closed() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=10.0),
        capital_authority_rows=None,
        as_of=NOW,
        policy=policy,
    )

    assert report["self_funded_supported_range"] == [0.0, 0.0]
    assert "capital_authority_unavailable" in report["blockers"]
    rendered = render_beta_monitor_markdown(report)
    assert "自有現金可部署" in rendered
    assert "cash floor 未知" in rendered
    assert "LON:VWRA — observed｜" not in rendered


def test_leverage_effective_cap_binds_even_when_signal_is_extreme() -> None:
    policy = load_beta_policy()
    observations = _observations(policy, drawdown=-0.5, rsi=15.0)
    histories = {key: [value] for key, value in observations.items()}
    # TQQQ 是 3x：持有量取自 policy 的 effective cap，確保必然越界。
    # 依 policy 推導而非寫死數字，改 cap 時測試不會腐爛。
    cap = policy["risk"]["leveraged_effective_cap"]
    nav = 100.0
    tqqq_nominal = round(nav * cap / 3.0 + 1.0, 4)  # 超過 cap 的最小整量
    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=nav - tqqq_nominal, tqqq=tqqq_nominal),
        as_of=NOW,
        policy=policy,
    )

    tqqq = next(item for item in report["items"] if item["ticker"] == "TQQQ")
    assert tqqq["signal_pace"] == 1.0
    assert tqqq["action"] == "PAUSE CONTRIBUTION"
    assert tqqq["supported_order_range_base"] == [0.0, 0.0]
    assert "etf_leverage_effective_cap_reached" in tqqq["blockers"]
    assert "etf_leverage_effective_cap_reached" in report["risk_snapshot"]["hard_blocks"]


def test_alpha_total_is_warning_only_and_does_not_consume_beta_capacity() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}
    rows = _holdings(
        cash=35.0,
        other=[
            {
                "ticker": "UNMAPPED",
                "bucket": "觀察",
                "market_value_base": 65.0,
                "nav_base": 100.0,
                "base_currency": "USD",
            }
        ],
    )

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=rows,
        capital_authority_rows=_capital_rows(),
        as_of=NOW,
        policy=policy,
    )
    assert report["risk_snapshot"]["alpha_total_weight"] == pytest.approx(0.65)
    assert "alpha_total_warning" in report["warnings"]
    assert any(item["supported_order_range_base"][1] > 0 for item in report["items"])


def test_missing_sheet_or_partial_technical_data_returns_zero_ranges() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    observations["dram"] = {
        "data_status": "insufficient_history",
        "fetched_at": NOW,
        "blockers": ["technical_history_insufficient_252_sessions"],
    }

    no_sheet = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark={},
        holdings_rows=None,
        as_of=NOW,
        policy=policy,
    )
    with_sheet = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark={key: [value] for key, value in observations.items()},
        holdings_rows=_holdings(),
        as_of=NOW,
        policy=policy,
    )

    assert no_sheet["status"] == "degraded"
    assert all(item["supported_order_range_base"] == [0.0, 0.0] for item in no_sheet["items"])
    dram = next(item for item in with_sheet["items"] if item["ticker"] == "DRAM")
    assert dram["action"] == "PAUSE CONTRIBUTION"
    assert "technical_history_insufficient_252_sessions" in dram["blockers"]


def test_same_signal_respects_repeat_cadence() -> None:
    policy = load_beta_policy()
    observation = _observation("qqq")
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}
    histories["qqq"] = [deepcopy(observation) for _ in range(2)]

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=20.0),
        capital_authority_rows=_capital_rows(),
        as_of=NOW,
        policy=policy,
    )

    qqq = next(item for item in report["items"] if item["ticker"] == "QQQ")
    tqqq = next(item for item in report["items"] if item["ticker"] == "TQQQ")
    assert qqq["review_cadence"]["reason"] == "cooldown"
    assert qqq["action"] == "HOLD"
    assert tqqq["action"] == "HOLD"


def test_known_tsmc_concentration_warns_without_pausing_additions() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}
    rows = _holdings(
        cash=50.0,
        other=[
            {
                "ticker": "2330.TW",
                "bucket": "觀察",
                "market_value_base": 36.0,
                "nav_base": 100.0,
                "base_currency": "USD",
            }
        ],
    )

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=rows,
        capital_authority_rows=_capital_rows(),
        as_of=NOW,
        policy=policy,
    )

    taiwan = [
        item
        for item in report["items"]
        if item["ticker"] in {"0050.TW", "006208.TW", "00631L.TW", "2330.TW"}
    ]
    assert any(item["supported_order_range_base"][1] > 0 for item in taiwan)
    exposure = report["risk_snapshot"]["issuer_exposures"]["TSMC"]
    assert exposure["total_weight"] == pytest.approx(0.36)
    assert exposure["direct_weight"] == pytest.approx(0.36)
    assert "issuer_concentration_warning:TSMC" in report["warnings"]


def test_drawn_debt_is_separate_from_etf_leverage_and_combined() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark={key: [value] for key, value in observations.items()},
        holdings_rows=_holdings(),
        capital_authority_rows=_capital_rows(drawn_amount="20"),
        as_of=NOW,
        policy=policy,
    )

    risk = report["risk_snapshot"]
    assert risk["etf_leverage"]["effective_weight"] == 0.0
    assert risk["loan_leverage_weight"] == pytest.approx(0.20)
    assert risk["combined_leverage_weight"] == pytest.approx(0.20)
    assert risk["hard_blocks"] == []


def test_markdown_is_aggregate_and_preserves_human_boundary() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark={key: [value] for key, value in observations.items()},
        holdings_rows=_holdings(),
        capital_authority_rows=_capital_rows(),
        as_of=NOW,
        policy=policy,
    )

    rendered = render_beta_monitor_markdown(report)

    assert "自有現金可部署" in rendered
    assert "本輪可評估上限" in rendered
    assert "未動用貸款額度" in rendered
    assert "共同現金池計算" in rendered
    assert "不預扣 alpha reserve" in rendered
    assert "Sheet／household" not in rendered
    assert "## TL;DR" in rendered
    assert "退休淨終值" in rendered
    assert "技術訊號只決定新增的時點與節奏" in rendered
    assert "月息不得依賴被迫賣出 beta" in rendered
    assert "節奏 " in rendered
    assert "5日 -3.0%｜20日 -8.0%" in rendered
    assert "## 主力 ETF／權值" in rendered
    assert rendered.index("QQQ") < rendered.index("TQQQ")
    assert "不代表已核准、已提款、已下單或已寫回" in rendered
    for raw in (
        "manual_review_required",
        "campaign_budget",
        "technical_history_insufficient_252_sessions",
    ):
        assert raw not in rendered
    assert "shares" not in rendered


def test_daily_risk_view_is_silent_without_change_but_weekly_full_is_explicit() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    history = {key: [value] for key, value in observations.items()}
    first = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=history,
        holdings_rows=_holdings(),
        as_of=NOW,
        policy=policy,
    )
    second = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=history,
        holdings_rows=_holdings(),
        as_of=NOW,
        policy=policy,
        previous_risk_snapshot=first["risk_snapshot"],
    )

    daily = render_beta_monitor_markdown(second)
    weekly = render_beta_monitor_markdown(second, risk_view="full")

    assert "## 投組風險變化" not in daily
    assert "## 投組風險完整快照" in weekly
    assert "Issuer look-through coverage：partial" in weekly
    assert "槓桿 ETF 資金占比" in weekly
    assert "換算槓桿曝險" in weekly
    assert "名目槓桿" not in weekly
    assert "科技 effective proxy" not in weekly


def test_baseline_pace_floors_contribution_regardless_of_signal() -> None:
    """訊號不得 gate 掉例行投入。

    2026-08-01 實測：以訊號 gate 自有現金投入，終值輸給無腦定投 8.5%
    （QQQ 91.5%、SOXX 91.9%）——市場多數時間在漲，等回檔等於在上漲期間抱現金。
    因此 baseline 是有證據的機制，訊號只能往上加。
    """
    policy = load_beta_policy()
    baseline = policy["signal"]["baseline_pace"]
    # 完全不觸發任何 tier 的平靜多頭
    calm = signal_state(
        {
            "benchmark_key": "qqq",
            "data_status": "observed",
            "drawdown_252": -0.02,
            "rsi_14": 62.0,
            "macd_histogram_slope": -0.1,
            "distance_sma_200": 0.08,
            "sma_50_slope_5": 0.01,
            "blockers": [],
        },
        policy,
    )
    assert calm["tier"] == "none", "此情境本來就不該觸發訊號"
    assert calm["signal_pace_raw"] == 0.0
    assert calm["pace"] == baseline, "訊號歸零時仍須維持例行投入"
    assert calm["pace_source"] == "baseline"


def test_baseline_does_not_fabricate_contribution_when_data_is_missing() -> None:
    """資料不足時仍誠實歸零——baseline 不是「無論如何都投」。"""
    policy = load_beta_policy()
    for status in ("insufficient_history", "unavailable", "quarantined"):
        state = signal_state({"data_status": status, "blockers": []}, policy)
        assert state["pace"] == 0.0, status
