"""財務三題（Phase 3 Step 3.3）的純函式守門。

守的是：①每一行有值與缺席二擇一、每個缺席出口都真的會出現（L12：燈滅與燈綠不同形）；
②T 時刻知道什麼（只用 filed ≤ d 的財報）；③口徑不相容不換算；④**沒有任何門檻或布林結論欄位**；
⑤邊緣判定是 AND、缺輸入落「無法量」；⑥主題等權組的 spec 驗證。
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from alpha import three_questions as tq
from alpha.edge import EDGE_REASONS, edge_state
from alpha.errors import ContractViolation
from alpha.theme_cohort import cohort_record, parse_cohort_record, select_current, spec_digest, validate_spec

TODAY = date(2026, 9, 29)


def _weekdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _quarters(first_end: date, n: int, *, revenue: float = 100.0, growth: float = 0.0, lag_days: int = 40,
              currency: str = "USD", metric_value=None) -> list[dict]:
    rows, end = [], first_end
    for i in range(n):
        start = end - timedelta(days=90)
        value = metric_value(i) if metric_value else revenue * (1 + growth) ** i
        rows.append({"period_start": start.isoformat(), "period_end": end.isoformat(),
                     "filed": (end + timedelta(days=lag_days)).isoformat(), "accession": f"A{i}",
                     "value": value, "currency": currency})
        end = end + timedelta(days=91)
    return rows


def _balance(first_end: date, n: int, value: float) -> list[dict]:
    """與營收同期末的資產負債表點（淨負債要同一期末、而且夠新）。"""
    return [{"period_end": r["period_end"], "filed": r["filed"], "accession": r["accession"], "value": value}
            for r in _quarters(first_end, n)]


def _domestic(**over) -> dict:
    bars_days = _weekdays(TODAY - timedelta(days=365 * 3 + 20), TODAY)
    price = {d: 10.0 + 5.0 * (i / len(bars_days)) for i, d in enumerate(bars_days)}    # 一路上漲
    inp = {
        "ticker": "XYZ", "filer_class": "domestic_quarterly", "revenue_kind": "quarterly",
        "price_bars": [(d, price[d]) for d in bars_days], "adjusted_bars": [(d, price[d]) for d in bars_days],
        "price_settlement_currency": "USD", "price_to_settlement": 1.0,
        "revenue_quarters": _quarters(date(2022, 3, 31), 18),
        "operating_income_quarters": _quarters(date(2022, 3, 31), 18, revenue=10.0),
        "cash": _balance(date(2022, 3, 31), 18, 50.0),
        "total_debt": _balance(date(2022, 3, 31), 18, 20.0),
        "shares_cover": [{"period_end": "2022-01-15", "filed": "2022-02-01", "accession": "S", "value": 1000.0}],
        "splits": [], "source": "fixture",
    }
    inp.update(over)
    return inp


# ---------------------------------------------------------------------------
# 行：有值與缺席二擇一
# ---------------------------------------------------------------------------

def test_a_line_is_value_xor_absence_and_absence_needs_a_reason() -> None:
    with pytest.raises(ValueError):
        tq.line("k", "l", rule="r")                                       # 沒值也沒缺席
    with pytest.raises(ValueError):
        tq.line("k", "l", value=1, rule="r", absence_kind="insufficient_evidence", reason="x")
    with pytest.raises(ValueError):
        tq.line("k", "l", rule="r", absence_kind="insufficient_evidence")  # 缺席沒理由
    with pytest.raises(Exception):
        tq.line("k", "l", rule="r", absence_kind="made_up", reason="x")    # 字彙封閉


# ---------------------------------------------------------------------------
# as-of 小工具
# ---------------------------------------------------------------------------

def test_ttm_uses_only_filings_known_at_d_and_requires_four_consecutive_quarters() -> None:
    rows = _quarters(date(2025, 3, 31), 5, growth=0.1)
    last_filed = date.fromisoformat(rows[-1]["filed"])
    value, last, ccy = tq.ttm(rows, last_filed - timedelta(days=1))      # 第五季還沒申報
    assert last == date.fromisoformat(rows[3]["period_end"]) and ccy == "USD"
    assert value == pytest.approx(sum(r["value"] for r in rows[:4]))
    value2, last2, _ = tq.ttm(rows, last_filed)
    assert last2 == date.fromisoformat(rows[4]["period_end"])
    assert value2 == pytest.approx(sum(r["value"] for r in rows[1:]))
    gap = [r for i, r in enumerate(rows) if i != 2]     # 中間缺一季 → 不連續
    assert tq.ttm(gap, date(2026, 12, 31))[0] is None


def test_shares_on_applies_splits_after_the_cover_date() -> None:
    cover = [{"period_end": "2024-05-20", "filed": "2024-05-29", "accession": "S", "value": 2.46e9}]
    splits = [(date(2024, 6, 10), 10.0)]
    assert tq.shares_on(cover, splits, date(2024, 6, 7)) == 2.46e9
    assert tq.shares_on(cover, splits, date(2024, 6, 10)) == pytest.approx(24.6e9)
    assert tq.shares_on(cover, splits, date(2024, 5, 28)) is None       # 還沒申報


def test_net_debt_needs_the_same_period_end_on_both_sides() -> None:
    cash = [{"period_end": "2025-12-31", "filed": "2026-02-01", "accession": "a", "value": 50.0}]
    debt = [{"period_end": "2025-09-30", "filed": "2025-11-01", "accession": "b", "value": 80.0}]
    assert tq.net_debt_on(cash, debt, TODAY) == (None, None)
    debt.append({"period_end": "2025-12-31", "filed": "2026-02-01", "accession": "a", "value": 80.0})
    assert tq.net_debt_on(cash, debt, TODAY) == (30.0, date(2025, 12, 31))


# ---------------------------------------------------------------------------
# 已定價①
# ---------------------------------------------------------------------------

def test_basis_refuses_a_stale_operating_income_ttm_and_a_stale_net_debt() -> None:
    """COHR 型：營業利益的 tag 停在兩年前，舊版拿那個 TTM 當「今天」判 EV/S（2026-09-29 Step 3.5 試跑撞到）。"""
    assert tq.decide_basis(_domestic(), TODAY)[0] == "EV/S"
    stale_op = _domestic(operating_income_quarters=_quarters(date(2022, 3, 31), 10, revenue=10.0))
    basis, reason = tq.decide_basis(stale_op, TODAY)
    assert basis == "P/S" and "不同步或已過期" in reason
    stale_bs = _domestic(cash=_balance(date(2022, 3, 31), 10, 50.0), total_debt=_balance(date(2022, 3, 31), 10, 20.0))
    basis, reason = tq.decide_basis(stale_bs, TODAY)
    assert basis == "P/S" and "淨負債" in reason


def test_history_samples_skip_days_whose_ttm_has_gone_stale() -> None:
    """營收停在某一季之後，更晚的價格日不得繼續拿那個舊 TTM 算倍數（樣本數只算新鮮的日子）。"""
    fresh = tq.own_history(_domestic(operating_income_quarters=()), today=TODAY)
    stopped = tq.own_history(_domestic(operating_income_quarters=(),
                                       revenue_quarters=_quarters(date(2022, 3, 31), 12)), today=TODAY)
    assert fresh["basis"] == stopped["basis"] == "P/S"
    assert fresh["absence_kind"] is None
    assert stopped["absence_kind"] == "insufficient_evidence"            # 今天的倍數算不出來：不拿兩年前的營收冒充
    assert stopped["detail"]["samples"] < fresh["detail"]["samples"]


def test_own_history_percentile_on_a_rising_price_with_flat_revenue_is_near_the_top() -> None:
    row = tq.own_history(_domestic(), today=TODAY)
    assert row["absence_kind"] is None and row["basis"] == "EV/S"
    assert row["value"] >= 99.0
    assert row["detail"]["window_days"] >= 365 * 3 - tq.HISTORY_SLACK_DAYS


def test_today_and_history_use_the_same_function_so_a_late_filing_is_invisible_before_it_is_filed() -> None:
    """PIT：一季營收在 T 之後才申報——T 那一天的倍數不得用到它。"""
    inp = _domestic()
    late = dict(inp["revenue_quarters"][-1])
    late.update(accession="LATE", filed=(TODAY + timedelta(days=5)).isoformat(), value=10_000.0)
    inp["revenue_quarters"] = [*inp["revenue_quarters"], late]
    before = tq.own_history(_domestic(), today=TODAY)
    after = tq.own_history(inp, today=TODAY)
    assert before["detail"]["multiple_today"] == after["detail"]["multiple_today"]


def test_loss_making_or_no_net_debt_falls_back_to_price_to_sales_and_says_why() -> None:
    loss = tq.own_history(_domestic(operating_income_quarters=_quarters(date(2022, 3, 31), 18, revenue=-5.0)),
                          today=TODAY)
    assert loss["basis"] == "P/S" and "< 0" in loss["detail"]["basis_reason"]
    no_debt = tq.own_history(_domestic(total_debt=[]), today=TODAY)
    assert no_debt["basis"] == "P/S" and "淨負債缺席" in no_debt["detail"]["basis_reason"]


def test_adr_type_currency_mismatch_is_inputs_incompatible_not_converted() -> None:
    """TSM 型：TWD 營收、USD ADR 價格——不換匯、不猜 ADR 比率。"""
    rows = _quarters(date(2022, 3, 31), 18, currency="TWD")
    row = tq.own_history(_domestic(revenue_quarters=rows), today=TODAY)
    assert row["absence_kind"] == "inputs_incompatible" and "TWD" in row["reason"]
    foreign = tq.own_history(_domestic(filer_class="foreign_annual"), today=TODAY)
    assert foreign["absence_kind"] == "inputs_incompatible"


def test_every_own_history_absence_exit_is_reachable() -> None:
    short = _domestic()
    short["price_bars"] = short["price_bars"][-200:]
    assert tq.own_history(short, today=TODAY)["absence_kind"] == "insufficient_evidence"   # 窗不滿 3 年
    stale = _domestic()
    stale["price_bars"] = [(d, p) for d, p in stale["price_bars"] if d < TODAY - timedelta(days=30)]
    assert "距今" in tq.own_history(stale, today=TODAY)["reason"]
    declared = tq.own_history(_domestic(), today=TODAY,
                              history_not_comparable={"since": "2025-01-01", "reason": "轉型", "source": "self"})
    assert declared["absence_kind"] == "inputs_incompatible" and "2025-01-01" in declared["reason"]
    gated = tq.own_history(_domestic(gate={"absence_kind": "upstream_unavailable", "reason": "歷史不可得"}),
                           today=TODAY)
    assert gated["absence_kind"] == "upstream_unavailable"
    no_shares = tq.own_history(_domestic(shares_cover=[]), today=TODAY)
    assert no_shares["absence_kind"] == "insufficient_evidence"


# ---------------------------------------------------------------------------
# 已定價②③：只印、同口徑、本檔除外
# ---------------------------------------------------------------------------

def test_cohort_median_uses_only_same_basis_members_and_needs_half_of_them() -> None:
    own = {"basis": "EV/S", "as_of": "2026-09-29"}
    members = {"A": {"basis": "EV/S", "detail": {"multiple_today": 2.0}},
               "B": {"basis": "EV/S", "detail": {"multiple_today": 4.0}},
               "C": {"basis": "P/S", "detail": {"multiple_today": 9.0}}}
    row = tq.cohort_median(own, members, cohort={"record_id": "tc_x", "theme": "t"}, cohort_absence=None)
    assert row["value"] == 3.0 and row["detail"]["n_same_basis"] == 2 and row["detail"]["n_members"] == 3
    thin = tq.cohort_median(own, {"C": members["C"], "D": members["C"]}, cohort=None, cohort_absence=None)
    assert thin["absence_kind"] == "insufficient_evidence"
    undefined = tq.cohort_median(own, {}, cohort=None,
                                 cohort_absence={"absence_kind": "not_yet_recorded", "reason": "主題等權組未定義"})
    assert undefined["absence_kind"] == "not_yet_recorded"


def test_relative_return_is_own_minus_equal_weight_member_mean() -> None:
    days = _weekdays(TODAY - timedelta(days=200), TODAY)
    own = [(d, 100.0 * (1.01 ** i)) for i, d in enumerate(days)]
    flat = [(d, 50.0) for d in days]
    rows = tq.relative_returns(own, {"A": flat, "B": flat}, today=TODAY, cohort={"record_id": "tc_x"},
                               cohort_absence=None)
    assert [r["key"] for r in rows] == ["rel_return_30d", "rel_return_90d"]
    assert rows[0]["value"] == pytest.approx(1.01 ** 30 - 1, rel=1e-3)
    assert rows[0]["detail"]["cohort_mean_return"] == 0.0


# ---------------------------------------------------------------------------
# 出現在數字裡了嗎
# ---------------------------------------------------------------------------

def test_a_single_segment_point_is_context_and_edgar_quarters_become_the_series() -> None:
    inp = _domestic(segment_shares=[{"as_of": "2025-12-31", "value": {"InP": 0.6}, "field": "segment_revenue_share"}])
    rows = tq.in_numbers(inp, today=TODAY)
    assert rows[0]["key"] == "in_numbers_series" and "EDGAR 季營收" in rows[0]["basis"]
    assert len(rows[0]["value"]) == 8 and rows[1]["key"] == "in_numbers_structure"


def test_two_segment_points_take_priority_and_nothing_is_upstream_unavailable() -> None:
    segs = [{"as_of": "2025-06-30", "value": {"a": 0.4}, "field": "segment_revenue_share"},
            {"as_of": "2025-12-31", "value": {"a": 0.5}, "field": "segment_revenue_share"}]
    assert "分部" in tq.in_numbers(_domestic(segment_shares=segs), today=TODAY)[0]["basis"]
    empty = tq.in_numbers({"revenue_kind": "quarterly"}, today=TODAY)
    assert empty[0]["absence_kind"] == "upstream_unavailable"


def test_segment_and_product_line_points_never_make_one_series() -> None:
    """2026-09-29 試跑：3081.TWO 的產品線占比（2025-12）與分部占比（2026-06）被湊成一條「序列」——兩種切法不能相比。"""
    segs = [{"as_of": "2025-12-31", "value": {"a": 1.0}, "field": "product_line_revenue_share"},
            {"as_of": "2026-06-30", "value": {"b": 1.0}, "field": "segment_revenue_share"}]
    months = [{"data_month": f"2026-0{m}", "revenue": 100 + m, "revenue_year_ago": 100, "unit_scale": 1000,
               "available_on": f"2026-0{m + 1}-10"} for m in range(1, 9)]
    rows = tq.in_numbers({"revenue_kind": "monthly", "monthly_revenue": months, "segment_shares": segs},
                         today=TODAY)
    assert "月營收" in rows[0]["basis"]
    assert [r["key"] for r in rows[1:]] == ["in_numbers_structure", "in_numbers_structure"]


def test_a_stale_latest_point_is_not_today_s_number() -> None:
    """TSM 型：2024 起的年度被拒寫（多種計價單位），最新一期停在 2023——不得當成「現在的數字」印。"""
    rows = [{"period_start": f"{y}-01-01", "period_end": f"{y}-12-31", "filed": f"{y + 1}-04-15",
             "accession": f"F{y}", "value": 100.0 * y, "currency": "TWD"} for y in (2021, 2022, 2023)]
    out = tq.in_numbers({"revenue_kind": "annual", "revenue_annual": rows}, today=TODAY)
    assert out[0]["absence_kind"] == "insufficient_evidence" and out[0]["detail"]["days_since_last"] > 550


def test_taiwan_monthly_revenue_uses_the_statutory_deadline() -> None:
    months = [{"data_month": f"2026-0{m}", "revenue": 100 + m, "revenue_year_ago": 100, "unit_scale": 1000,
               "available_on": f"2026-0{m + 1}-10"} for m in range(1, 9)]
    rows = tq.in_numbers({"revenue_kind": "monthly", "monthly_revenue": months}, today=date(2026, 9, 9))
    assert rows[0]["value"][-1]["data_month"] == "2026-07"      # 8 月的要到 9/10 才算知道
    assert "法定期限" in rows[0]["basis"]


# ---------------------------------------------------------------------------
# 沒有門檻、沒有結論欄位
# ---------------------------------------------------------------------------

def test_the_audit_section_has_no_boolean_verdict_anywhere() -> None:
    result = tq.evaluate(_domestic(), today=TODAY, wipeout=None, wipeout_reason="fixture")

    def walk(node):
        if isinstance(node, bool):
            raise AssertionError("稽核區不得有布林結論")
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in ("priced", "is_priced", "priced_in_verdict", "threshold", "verdict"), k
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(result)
    assert set(tq.QUESTIONS) <= set(result)


def test_no_field_name_in_the_audit_section_carries_position_semantics() -> None:
    """黑箱輸出的欄位名守門（`alpha.contracts.FORBIDDEN_POSITION_TOKENS`）：2026-09-29 稀釋燈的 `base_shares`
    一亮就撞上——公司的在外流通股數不是部位，但欄位名不得讓人分不出來。"""
    from alpha.contracts import FORBIDDEN_POSITION_TOKENS
    from alpha.wipeout import wipeout_flags

    series = [(date(2025, 5, 1), 100.0), (date(2025, 9, 1), 101.0), (TODAY, 120.0)]
    flags = wipeout_flags(runway=None, shares_series=series, going_concern=None, today=TODAY, shares_source="x")
    segs = [{"as_of": "2025-06-30", "value": {"a": 0.4}, "field": "segment_revenue_share"},
            {"as_of": "2025-12-31", "value": {"a": 0.5}, "field": "segment_revenue_share"}]
    result = tq.evaluate(_domestic(segment_shares=segs), today=TODAY, wipeout=flags)

    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield str(k)
                yield from keys(v)
        elif isinstance(node, list):
            for v in node:
                yield from keys(v)

    offenders = {k for k in keys(result) if set(k.lower().split("_")) & FORBIDDEN_POSITION_TOKENS}
    assert not offenders, offenders


def test_rollup_counts_value_and_absence_by_kind_per_line() -> None:
    a = tq.evaluate(_domestic(), today=TODAY, wipeout=None)
    b = tq.evaluate(_domestic(gate={"absence_kind": "upstream_unavailable", "reason": "x"}), today=TODAY,
                    wipeout=None)
    counts = tq.rollup([a, b])
    assert counts["own_history_pctile"] == {"value": 1, "upstream_unavailable": 1}
    assert counts["cohort_median"] == {"not_yet_recorded": 2}


# ---------------------------------------------------------------------------
# 邊緣判定
# ---------------------------------------------------------------------------

LIMITS = {"market_cap_max_usd": 10e9, "analyst_count_max": 12}


def test_edge_is_an_and_of_both_limits() -> None:
    assert edge_state(market_cap_usd=4.8e9, analyst_count=5, thresholds=LIMITS)["state"] == "edge"
    tsm = edge_state(market_cap_usd=2.25e12, analyst_count=13, thresholds=LIMITS)
    assert tsm["state"] == "not_edge" and tsm["reasons"] == ["cap_over_edge", "coverage_over_edge"]
    assert edge_state(market_cap_usd=1e9, analyst_count=30, thresholds=LIMITS)["reasons"] == ["coverage_over_edge"]


def test_missing_inputs_are_unmeasurable_not_passed_and_not_dropped() -> None:
    row = edge_state(market_cap_usd=0.5e9, analyst_count=None, thresholds=LIMITS)
    assert row["state"] == "unmeasurable" and row["missing"] == ["coverage_unavailable"]
    # 一個輸入就已經超過 → 非邊緣（缺的那個照列）
    over = edge_state(market_cap_usd=None, analyst_count=40, thresholds=LIMITS)
    assert over["state"] == "not_edge" and over["missing"] == ["market_cap_unavailable"]


def test_edge_reason_codes_do_not_reuse_the_retired_filter_words() -> None:
    assert not {"market_cap_above_max", "analyst_count_above_max"} & set(EDGE_REASONS)


# ---------------------------------------------------------------------------
# 主題等權組 spec
# ---------------------------------------------------------------------------

SPEC = {"theme": "ai_capex", "reason": "同題材邊緣供應商",
        "members": [{"ticker": "AXTI", "company_id": "co:axt", "reason": "InP 基板"},
                    {"ticker": "SIVE.ST", "company_id": "co:sivers_semiconductors", "reason": "CW DFB 雷射"}],
        "excluded": [{"name": "COHR", "reason": "非邊緣（市值 62B）"}]}


@pytest.mark.parametrize("mutate", [
    lambda s: s.update(members=[s["members"][0]]),                       # 一檔不成組
    lambda s: s.update(members=[*s["members"], s["members"][0]]),        # 重複
    lambda s: s["members"][0].update(company_id="axt"),                   # 不是 co:*
    lambda s: s["members"][0].pop("reason"),                              # 缺入選理由
    lambda s: s.pop("excluded"),                                          # 沒寫排除了誰
    lambda s: s.update(weights=[0.5, 0.5]),                              # 未登記欄位（等權，不收權重）
])
def test_invalid_cohort_specs_are_refused(mutate) -> None:
    import copy

    spec = copy.deepcopy(SPEC)
    mutate(spec)
    with pytest.raises(ContractViolation):
        validate_spec(spec)


def test_cohort_record_is_content_addressed_and_the_digest_binds_the_spec() -> None:
    from datetime import datetime, timezone

    stamp = datetime(2026, 9, 30, tzinfo=timezone.utc)
    rec = cohort_record(SPEC, pq2_ref=700, decided_on=date(2026, 9, 30), created_at=stamp)
    assert rec["cohort_id"].startswith("tc_")
    assert cohort_record(SPEC, pq2_ref=700, decided_on=date(2026, 9, 30), created_at=stamp)["cohort_id"] == \
        rec["cohort_id"]
    changed = {**SPEC, "reason": "改了理由"}
    assert spec_digest(changed) != spec_digest(SPEC)
    parsed = parse_cohort_record(rec)
    assert parsed.tickers == ("AXTI", "SIVE.ST") and parsed.pq2_ref == 700
    assert select_current([parsed], as_of=date(2026, 9, 29)) is None
    assert select_current([parsed], as_of=date(2026, 9, 30)) == parsed
