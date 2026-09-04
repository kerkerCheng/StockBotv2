"""Engine D beta 監控：目標配置差距、行情心跳與相對水位，全程不含技術訊號。

⚠ 本檔在 2026-08-29 大幅改寫。原本斷言三態系統動作（CONTRIBUTE REVIEW／HOLD／
PAUSE CONTRIBUTION）、pace 節奏、RSI／MACD tier 與例行提醒節奏的測試已一併刪除，
理由是它們唯一斷言的行為隨技術訊號機制移除；被刪的每一個都在下方留了說明。
斷言仍存在行為（行情心跳、槓桿 cap、資本呈現）的測試改用新欄位，原意圖保留。
"""
from __future__ import annotations

import json

import pytest

from portfolio.allocation import (
    build_allocation_gap,
    build_beta_monitor,
    render_beta_monitor_markdown,
    water_level,
)
from portfolio.policy import (
    instrument_price_key,
    load_beta_policy,
    load_target_allocation,
    unique_technical_targets,
)


NOW = "2026-07-28T00:00:00+00:00"


def _observation(
    key: str,
    *,
    drawdown: float = -0.25,
    percentile: float = 0.35,
    distance_200: float = 0.02,
):
    return {
        "benchmark_key": key,
        "data_status": "observed",
        "fetched_at": NOW,
        "session_date": "2026-07-27",
        "return_1d": -0.01,
        "return_5d": -0.03,
        "return_20d": -0.08,
        "drawdown_252": drawdown,
        "range_percentile_252": percentile,
        "distance_sma_20": -0.03,
        "distance_sma_50": -0.05,
        "distance_sma_200": distance_200,
        "realized_vol_20": 0.3,
        "realized_vol_60": 0.25,
        "blockers": [],
    }


def _observations(policy, **kwargs):
    return {
        item["benchmark_key"]: _observation(item["benchmark_key"], **kwargs)
        for item in unique_technical_targets(policy)
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


def _report(**kwargs):
    policy = kwargs.pop("policy", None) or load_beta_policy()
    observations = kwargs.pop("observations", None) or _observations(policy)
    return build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=kwargs.pop(
            "histories", {key: [value] for key, value in observations.items()}
        ),
        holdings_rows=kwargs.pop("holdings_rows", _holdings(cash=10.0)),
        capital_authority_rows=kwargs.pop("capital_authority_rows", _capital_rows()),
        as_of=NOW,
        policy=policy,
        **kwargs,
    )


# ── 拔除訊號後的回歸防線 ───────────────────────────────────────────────────────


def test_output_contains_no_action_states_pace_or_momentum_indicators() -> None:
    """三態動作、節奏百分比與任何動能指標都不得再出現在輸出裡。

    2026-08-01 三次回測全部失敗，2026-08-29 定案整組拔掉。RSI 以「相對水位」
    之名放回來等於把測過失敗的東西換名字重來，所以連欄位名都不許出現。
    """
    report = _report()
    payload = json.dumps(report, ensure_ascii=False, default=str)
    rendered = render_beta_monitor_markdown(report, risk_view="full")

    for banned in ("CONTRIBUTE REVIEW", "PAUSE CONTRIBUTION", "HOLD", "節奏", "RSI", "MACD"):
        assert banned not in payload, banned
        assert banned not in rendered, banned

    def _keys(value) -> set[str]:
        if isinstance(value, dict):
            found = {str(key).casefold() for key in value}
            for child in value.values():
                found |= _keys(child)
            return found
        if isinstance(value, list):
            return {name for child in value for name in _keys(child)}
        return set()

    banned_tokens = {"rsi", "macd", "momentum", "tier", "pace", "signal"}
    for key in _keys(report):
        assert not banned_tokens & set(key.split("_")), f"{key} 仍帶動能／訊號語意"


def test_water_level_is_position_only_and_never_produces_a_ranking() -> None:
    """相對水位只有位置欄位，且高水位不是「該等」的訊號。"""
    level = water_level(_observation("qqq", drawdown=-0.02, percentile=0.95, distance_200=0.26))

    assert set(level) == {
        "status",
        "range_percentile_52w",
        "pct_from_52w_high",
        "pct_from_sma200",
        "interpretation",
    }
    assert level["range_percentile_52w"] == pytest.approx(0.95)
    assert level["pct_from_52w_high"] == pytest.approx(-0.02)
    assert level["pct_from_sma200"] == pytest.approx(0.26)
    assert level["interpretation"] == "position_only_no_momentum_not_a_timing_signal"


def test_water_level_is_none_when_the_series_is_degraded_not_zero() -> None:
    """行情降級時水位是 None，不是 0——0 會被誤讀成「在 52 週低點」。"""
    for status in ("insufficient_history", "unavailable", "quarantined", "stale"):
        level = water_level({"data_status": status, "blockers": []})
        assert level["status"] == status
        assert level["range_percentile_52w"] is None
        assert level["pct_from_52w_high"] is None


# ── 保留行為：行情心跳 ────────────────────────────────────────────────────────


def test_every_instrument_keeps_its_daily_heartbeat_even_with_no_contribution() -> None:
    """行情表是每日心跳：每檔都必須有最新完整交易日與 1 日漲跌，一列都不省略。"""
    report = _report()

    assert len(report["items"]) == 14
    for item in report["items"]:
        assert item["heartbeat"]["session_date"] == "2026-07-27"
        assert item["heartbeat"]["return_1d"] == pytest.approx(-0.01)

    rendered = render_beta_monitor_markdown(report)
    assert "## 主力 ETF／權值（每日心跳，不受今日是否投入影響）" in rendered
    assert "最新完整交易日 2026-07-27：1日 -1.0%｜5日 -3.0%｜20日 -8.0%" in rendered
    for ticker in ("QQQ", "TQQQ", "LON:VWRA", "SOXX", "00631L.TW", "2330.TW", "00981A.TW"):
        assert any(line.startswith(f"| {ticker} |") for line in rendered.splitlines()), ticker


def test_leveraged_product_uses_its_own_price_series_not_the_benchmark() -> None:
    """TQQQ 的心跳與水位必須來自 TQQQ 自身序列，不得冒用 QQQ。"""
    policy = load_beta_policy()
    observations = _observations(policy)
    tqqq_price_key = instrument_price_key(
        next(item for item in policy["instruments"] if item["ticker"] == "TQQQ")
    )
    assert tqqq_price_key != "qqq"
    observations[tqqq_price_key] = {
        **observations[tqqq_price_key],
        "return_1d": -0.03,
        "return_5d": -0.09,
        "return_20d": -0.20,
        "drawdown_252": -0.40,
        "range_percentile_252": 0.12,
        "distance_sma_200": -0.18,
    }

    report = _report(policy=policy, observations=observations)
    tqqq = next(item for item in report["items"] if item["ticker"] == "TQQQ")
    qqq = next(item for item in report["items"] if item["ticker"] == "QQQ")

    assert tqqq["price_series_key"] == tqqq_price_key
    assert tqqq["price_symbol"] == "TQQQ"
    assert tqqq["heartbeat"]["return_1d"] == pytest.approx(-0.03)
    assert tqqq["water_level"]["range_percentile_52w"] == pytest.approx(0.12)
    assert qqq["water_level"]["range_percentile_52w"] == pytest.approx(0.35)

    rendered = render_beta_monitor_markdown(report)
    tqqq_row = next(line for line in rendered.splitlines() if line.startswith("| TQQQ |"))
    assert "最新完整交易日 2026-07-27：1日 -3.0%｜5日 -9.0%｜20日 -20.0%" in tqqq_row
    assert "52週區間位置 12%" in tqqq_row


def test_stale_price_series_degrades_that_row_without_hiding_it() -> None:
    """過期／歷史不足只降級該列並說明原因，不得讓它從心跳表消失。"""
    policy = load_beta_policy()
    observations = _observations(policy)
    observations["dram"] = {
        "data_status": "insufficient_history",
        "fetched_at": NOW,
        "blockers": ["technical_history_insufficient_252_sessions"],
    }
    observations["soxx"] = {**observations["soxx"], "fetched_at": "2026-07-01T00:00:00+00:00"}

    report = _report(policy=policy, observations=observations)

    dram = next(item for item in report["items"] if item["ticker"] == "DRAM")
    soxx = next(item for item in report["items"] if item["ticker"] == "SOXX")
    assert dram["price_status"] == "insufficient_history"
    assert "technical_history_insufficient_252_sessions" in dram["blockers"]
    assert soxx["price_status"] == "stale"
    assert soxx["water_level"]["range_percentile_52w"] is None
    assert report["status"] == "degraded"
    rendered = render_beta_monitor_markdown(report)
    assert any(line.startswith("| SOXX |") for line in rendered.splitlines())
    assert "行情資料過期" in rendered


def test_twse_reference_is_rendered_without_becoming_adjusted_indicator() -> None:
    """TWSE 官方列只作最新交易日校驗，不混入 adjusted-close 序列。"""
    policy = load_beta_policy()
    observations = _observations(policy)
    observations["tw50"]["_twse_reference"] = {
        "status": "provider_lagging",
        "session_date": "2026-07-31",
        "close_raw": 102.85,
        "change_raw": 9.35,
        "change_pct": 0.1,
        "source": "fixture://twse",
    }

    report = _report(policy=policy, observations=observations)

    tw50 = next(item for item in report["items"] if item["ticker"] == "0050.TW")
    assert tw50["heartbeat"]["twse_session_date"] == "2026-07-31"
    assert tw50["heartbeat"]["twse_change_pct"] == 0.1
    assert "TWSE 官方 2026-07-31 +10.0%" in render_beta_monitor_markdown(report)


# ── 新增行為：目標配置差距 ────────────────────────────────────────────────────


def _gap(rows, *, policy=None, target=None):
    from risk.snapshot import build_portfolio_components

    policy = policy or load_beta_policy()
    portfolio = build_portfolio_components(rows, policy)
    return build_allocation_gap(
        portfolio=dict(portfolio) | {"status": portfolio["status"]},
        policy=policy,
        target_policy=target or load_target_allocation(),
    )


def test_allocation_gap_uses_invested_non_cash_and_treats_band_as_on_target() -> None:
    """分母是已投入的非現金部位；落在 band 內視為到位、沒有偏好。"""
    target = load_target_allocation()
    core_target = target["sleeves"]["beta_core"]["target"]
    band = target["sleeves"]["beta_core"]["band"]
    # 非現金 80：VWRA 落在 beta_core 目標的 band 內，其餘丟給 alpha 殘量。
    core_value = round(80.0 * core_target, 4)
    rows = [
        {"ticker": "CASH", "bucket": "cash", "market_value_base": 20.0, "nav_base": 100.0, "base_currency": "USD"},
        {"ticker": "LON:VWRA", "bucket": "大盤", "market_value_base": core_value, "nav_base": 100.0, "base_currency": "USD"},
        {"ticker": "UNMAPPED", "bucket": "觀察", "market_value_base": 80.0 - core_value, "nav_base": 100.0, "base_currency": "USD"},
    ]

    gap = _gap(rows, target=target)
    by_sleeve = {item["sleeve"]: item for item in gap["sleeves"]}

    assert gap["status"] == "available"
    assert gap["basis"] == "invested_non_cash"
    assert gap["invested_non_cash_base"] == pytest.approx(80.0)
    assert by_sleeve["beta_core"]["actual"] == pytest.approx(core_target)
    assert by_sleeve["beta_core"]["gap"] == pytest.approx(0.0)
    assert by_sleeve["beta_core"]["state"] == "on_target"
    # 剛好落在 band 邊界仍算到位
    shifted = _gap(
        [
            rows[0],
            {**rows[1], "market_value_base": round(80.0 * (core_target - band), 4)},
            {**rows[2], "market_value_base": round(80.0 * (1 - core_target + band), 4)},
        ],
        target=target,
    )
    assert {item["sleeve"]: item for item in shifted["sleeves"]}["beta_core"]["state"] == "on_target"
    # 空手的 sleeve 必然低於目標
    assert by_sleeve["beta_leverage"]["actual"] == pytest.approx(0.0)
    assert by_sleeve["beta_leverage"]["state"] == "below_band"
    # 只給差距，不給金額也不排名
    assert "suggested_amount" not in by_sleeve["beta_core"]
    assert "rank" not in by_sleeve["beta_core"]


def test_allocation_gap_flags_an_overweight_sleeve() -> None:
    """超出 band 才標示，並指向「新資金避開」，不是要人賣出。"""
    target = load_target_allocation()
    rows = [
        {"ticker": "CASH", "bucket": "cash", "market_value_base": 20.0, "nav_base": 100.0, "base_currency": "USD"},
        {"ticker": "2330.TW", "bucket": "個股", "market_value_base": 40.0, "nav_base": 100.0, "base_currency": "USD"},
        {"ticker": "LON:VWRA", "bucket": "大盤", "market_value_base": 40.0, "nav_base": 100.0, "base_currency": "USD"},
    ]

    gap = _gap(rows, target=target)
    by_sleeve = {item["sleeve"]: item for item in gap["sleeves"]}

    assert by_sleeve["large_cap_tilt"]["actual"] == pytest.approx(0.5)
    assert by_sleeve["large_cap_tilt"]["state"] == "above_band"
    assert by_sleeve["large_cap_tilt"]["gap"] > 0
    assert gap["rebalancing"]["method"] == "new_money_only"


def test_alpha_sleeve_is_marked_unknown_rather_than_zero_when_holdings_are_missing() -> None:
    """算不到就標算不到。0% 會把新資金推向一個根本沒算過的格子（L12：None ≠ 0）。"""
    gap = _gap(None)
    by_sleeve = {item["sleeve"]: item for item in gap["sleeves"]}

    assert gap["status"] == "unavailable"
    assert gap["unavailable_reason"] == "holdings_unavailable"
    for entry in gap["sleeves"]:
        assert entry["actual"] is None, entry["sleeve"]
        assert entry["state"] == "unknown", entry["sleeve"]
    assert by_sleeve["alpha"]["actual_source"] == "residual_non_beta_holdings"
    assert by_sleeve["alpha"]["unavailable_reason"] == "holdings_unavailable"


def test_allocation_gap_and_correlation_warnings_always_render() -> None:
    """兩條相關性警告每天都要講一次，不因為每天一樣就省略。"""
    report = _report()
    rendered = render_beta_monitor_markdown(report)

    assert "## 目標配置差距（決定「這次投哪一檔」的錨點）" in rendered
    assert "已投入的非現金部位" in rendered
    assert "alpha 與 beta 是同一個賭注" in rendered
    assert "TSMC look-through" in rendered
    warnings = report["allocation_gap"]["correlation_warnings"]
    assert len(warnings) == 2
    for warning in warnings:
        assert warning["detail"] in rendered


# ── 保留行為：資本呈現與槓桿／曝險 cap ─────────────────────────────────────────


def test_shared_cash_pool_subtracts_only_floor_and_never_uses_credit() -> None:
    report = _report()
    larger_credit = _report(capital_authority_rows=_capital_rows(credit_limit="999999"))

    assert report["portfolio"]["deployable_cash_base"] == pytest.approx(9.0)
    # 可投入區間就是可部署現金本身，不再被任何單輪預算或訊號縮小。
    assert report["self_funded_supported_range"] == [0.0, pytest.approx(9.0)]
    assert report["self_funded_supported_range"] == larger_credit["self_funded_supported_range"]
    assert report["contingent_credit_available"]["undrawn_amount_base"] == 1000.0
    assert report["loan_funded_supported_range"]["status"] == "manual_review_required"
    assert report["capital_scope"] == "shared_cash_pool"
    assert report["policy_mode"] == "paper_observation"

    rendered = render_beta_monitor_markdown(report)
    assert "共同現金池計算" in rendered
    assert "cash floor" in rendered
    assert "未動用貸款額度：USD 1,000" in rendered
    assert "不算自有現金" in rendered


def test_missing_cash_floor_authority_fails_shared_cash_closed() -> None:
    report = _report(capital_authority_rows=None)

    assert report["self_funded_supported_range"] == [0.0, 0.0]
    assert "capital_authority_unavailable" in report["blockers"]
    rendered = render_beta_monitor_markdown(report)
    assert "自有現金可部署" in rendered
    assert "cash floor 未知" in rendered


def test_leverage_effective_cap_zeroes_the_self_funded_range() -> None:
    """槓桿 cap 是真實歸零風險，與訊號無關，拔訊號後必須完全保留。"""
    policy = load_beta_policy()
    # TQQQ 是 3x：持有量取自 policy 的 effective cap，確保必然越界。
    # 依 policy 推導而非寫死數字，改 cap 時測試不會腐爛。
    cap = policy["risk"]["leveraged_effective_cap"]
    nav = 100.0
    tqqq_nominal = round(nav * cap / 3.0 + 1.0, 4)

    report = _report(
        policy=policy,
        holdings_rows=_holdings(cash=nav - tqqq_nominal, tqqq=tqqq_nominal),
        capital_authority_rows=_capital_rows(),
    )

    assert "etf_leverage_effective_cap_reached" in report["risk_snapshot"]["hard_blocks"]
    assert "etf_leverage_effective_cap_reached" in report["blockers"]
    assert report["self_funded_supported_range"] == [0.0, 0.0]


def test_alpha_total_is_warning_only_and_never_a_hard_block() -> None:
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

    report = _report(holdings_rows=rows)

    assert report["risk_snapshot"]["alpha_total_weight"] == pytest.approx(0.65)
    assert "alpha_total_warning" in report["warnings"]
    assert report["risk_snapshot"]["hard_blocks"] == []
    assert report["self_funded_supported_range"][1] > 0


def test_known_tsmc_concentration_warns_without_blocking() -> None:
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

    report = _report(holdings_rows=rows)

    exposure = report["risk_snapshot"]["issuer_exposures"]["TSMC"]
    assert exposure["total_weight"] == pytest.approx(0.36)
    assert exposure["direct_weight"] == pytest.approx(0.36)
    assert "issuer_concentration_warning:TSMC" in report["warnings"]
    assert report["self_funded_supported_range"][1] > 0
    rendered = render_beta_monitor_markdown(report, risk_view="full")
    assert "TSMC：總曝險 已知至少 36.0%" in rendered


def test_drawn_debt_is_separate_from_etf_leverage_and_combined() -> None:
    report = _report(capital_authority_rows=_capital_rows(drawn_amount="20"))

    risk = report["risk_snapshot"]
    assert risk["etf_leverage"]["effective_weight"] == 0.0
    assert risk["loan_leverage_weight"] == pytest.approx(0.20)
    assert risk["combined_leverage_weight"] == pytest.approx(0.20)
    assert risk["hard_blocks"] == []


def test_markdown_is_aggregate_and_preserves_human_boundary() -> None:
    report = _report()
    rendered = render_beta_monitor_markdown(report)

    assert "自有現金可部署" in rendered
    assert "未動用貸款額度" in rendered
    assert "共同現金池計算" in rendered
    assert "不預扣 alpha reserve" in rendered
    assert "Sheet／household" not in rendered
    assert "## TL;DR" in rendered
    assert "退休淨終值" in rendered
    assert "月息不得依賴被迫賣出 beta" in rendered
    assert rendered.index("QQQ") < rendered.index("TQQQ")
    assert "不代表已核准、已提款、已下單或已寫回" in rendered
    for raw in ("campaign_budget", "technical_history_insufficient_252_sessions", "shares"):
        assert raw not in rendered


def test_daily_risk_view_is_silent_without_change_but_weekly_full_is_explicit() -> None:
    first = _report()
    second = _report(previous_risk_snapshot=first["risk_snapshot"])

    daily = render_beta_monitor_markdown(second)
    weekly = render_beta_monitor_markdown(second, risk_view="full")

    assert "## 投組風險變化" not in daily
    assert "## 投組風險完整快照" in weekly
    assert "Issuer look-through coverage：partial" in weekly
    assert "槓桿 ETF 資金占比" in weekly
    assert "換算槓桿曝險" in weekly
    assert "名目槓桿" not in weekly


# ── 2026-08-29 隨技術訊號一併刪除的測試（不留空殼，只留刪除理由） ─────────────
#
# - test_signal_state_uses_macd_and_ma_as_pace_guard_not_extra_votes
# - test_stretched_above_sma200_downgrades_pace_even_on_a_real_drawdown
# - test_baseline_pace_floors_contribution_regardless_of_signal
# - test_baseline_does_not_fabricate_contribution_when_data_is_missing
# - test_same_signal_respects_repeat_cadence
# - test_self_funded_routine_reminder_uses_full_session_count_not_signal
# - test_ranges_share_one_frozen_deployable_cash_budget
#     這七個唯一斷言的都是 signal_state／pace／tier／例行提醒節奏／單輪 campaign
#     budget 切分——機制本身已於 2026-08-29 移除，測試沒有可斷言的行為留下。
#     其中「資料不足時誠實歸零」與「共用一份可部署現金」兩個意圖仍在，分別由
#     test_water_level_is_none_when_the_series_is_degraded_not_zero 與
#     test_shared_cash_pool_subtracts_only_floor_and_never_uses_credit 承接。
