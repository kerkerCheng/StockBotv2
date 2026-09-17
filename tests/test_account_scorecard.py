"""帳號計分表與訊號來源登記表的守門測試（ROADMAP Phase 3／D5）。

這裡守的是**判準**，不是數字：數字每天都在變，判準不該變。
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from engine_b import account_scorecard as sc
from engine_b import signal_source_registry as ssr


# ---------------------------------------------------------------------------
# 登記表：封閉字彙與「本模組不改 tier」
# ---------------------------------------------------------------------------

def _write_registry(tmp_path, sources):
    path = tmp_path / "signal_sources.json"
    path.write_text(json.dumps({"version": 1, "schema_version": 2, "sources": sources},
                               ensure_ascii=False), encoding="utf-8")
    return path


def test_tier_is_a_closed_vocabulary(tmp_path) -> None:
    """打錯的 tier 必須在載入時就爆——字彙一旦有行為後果就必須被強制（L16-3）。"""
    path = _write_registry(tmp_path, [
        {"source_id": "a", "status": "active", "tier": "trusted_ish",
         "research_priority": 1, "auto_capture": True}])
    with pytest.raises(ssr.SignalSourceRegistryError, match="tier 未登記"):
        ssr.load(path)


def test_missing_tier_is_not_silently_allowed(tmp_path) -> None:
    """未宣告不得預設放行——那會讓新帳號安靜地拿到它沒被授予的信任。"""
    path = _write_registry(tmp_path, [
        {"source_id": "a", "status": "active", "research_priority": 1, "auto_capture": True}])
    with pytest.raises(ssr.SignalSourceRegistryError, match="tier 未登記"):
        ssr.load(path)


def test_status_vocabulary_comes_from_decision_lab_ssot() -> None:
    """status 的 SSOT 在 decision_lab；這裡借它而不是抄一份（L16）。"""
    from decision_lab.intake import _SOURCE_STATUSES

    assert set(ssr.STATUSES) == set(_SOURCE_STATUSES)


def test_probation_means_zero_bonus_and_tiers_are_ordered() -> None:
    """tier 只給 pq1 優先序加分；probation 是 0 不是負數（新帳號不被懲罰，只是還沒有理由被優先看）。"""
    assert ssr.PQ1_PRIORITY_BONUS["probation"] == 0
    assert (ssr.PQ1_PRIORITY_BONUS["probation"] < ssr.PQ1_PRIORITY_BONUS["measured"]
            < ssr.PQ1_PRIORITY_BONUS["trusted"])


def test_registry_module_has_no_write_path() -> None:
    """tier 升降是一季一次的 pq2 manual（D5）——本模組刻意沒有寫入函式。"""
    for name in ("save", "write", "set_tier", "promote", "demote", "update"):
        assert not hasattr(ssr, name), f"登記表模組不該有 {name}()——tier 升降走 pq2，不走程式"


def test_tier_counts_include_empty_tiers() -> None:
    """每一級都要出現，包含 0——缺席不得被壓成「沒有這一級」。"""
    counts = ssr.load().tier_counts()
    assert set(counts) == set(ssr.TIERS)


def test_shipped_registry_loads_and_is_all_probation() -> None:
    """實際出貨的登記表載得起來；且沒有任何帳號在未經 pq2 的情況下高於 probation。"""
    registry = ssr.load()
    assert registry.sources
    assert all(s.tier == "probation" for s in registry.sources.values()), (
        "有帳號的 tier 高於 probation——那必須有一筆 pq2 receipt，"
        "不得由某個 session 自行認定（INV-5：未量測的機制不得享有默認信任）")


# ---------------------------------------------------------------------------
# 計分表：缺席不得被壓成 0、filter 要能報 reasons、去重與不去重不得互相取代
# ---------------------------------------------------------------------------

def _call(symbol: str, day: str, *, trace: str | None = None, status: str = "parked") -> sc.NamedCall:
    return sc.NamedCall(lead_id=f"lead_{symbol}_{day}", source="x:acct", company_id=f"co:{symbol}",
                        symbol=symbol, called_on=date.fromisoformat(day), status=status,
                        trace_status=trace)


def _flat_series(start: str, days: int, step: float, base: float = 100.0):
    from datetime import timedelta

    begin = date.fromisoformat(start)
    return {begin + timedelta(days=i): base + i * step for i in range(days)}


def test_hypothesis_hit_rate_is_never_zero_it_is_absent() -> None:
    """算不回來的欄位宣告 absence_kind，**不填 0**——「還沒建」與「命中率是 0」是兩件事（L12）。"""
    scored = sc.score_account([], prices={}, today=date(2026, 9, 17),
                              no_go_rate=sc.Metric(value=0.5, n=2),
                              trace_metric=sc.Metric(value=0.5, n=2))
    cell = scored["hypothesis_hit_rate"]
    assert cell["value"] is None
    assert cell["absence_kind"] == sc.ABSENCE_CAPABILITY


def test_unelapsed_horizon_is_insufficient_sample_not_zero() -> None:
    """持有期還沒走完 → 沒有值，而且理由要說出是哪一種沒有。"""
    prices = {"AAA": _flat_series("2026-09-01", 20, 1.0), "QQQ": _flat_series("2026-09-01", 20, 0.5),
              "SOXX": _flat_series("2026-09-01", 20, 0.5)}
    scored = sc.score_account([_call("AAA", "2026-09-10")], prices=prices, today=date(2026, 9, 17),
                              no_go_rate=sc.Metric(), trace_metric=sc.Metric())
    cell = scored["excess_returns"]["excess_30d_vs_QQQ"]
    assert cell["value"] is None and cell["absence_kind"] == sc.ABSENCE_INSUFFICIENT
    assert scored["excess_return_filters"]["excess_30d_vs_QQQ"]["reasons"]["horizon_not_elapsed"] == 1


def test_excess_is_computed_against_both_benchmarks() -> None:
    """兩個基準都要算——只對 QQQ 算會被單邊上漲高估（D5 §6 的逐字要求）。"""
    prices = {"AAA": _flat_series("2026-09-01", 60, 1.0),
              "QQQ": _flat_series("2026-09-01", 60, 0.5),
              "SOXX": _flat_series("2026-09-01", 60, 2.0)}
    scored = sc.score_account([_call("AAA", "2026-09-02")], prices=prices, today=date(2026, 10, 31),
                              no_go_rate=sc.Metric(), trace_metric=sc.Metric())
    vs_qqq = scored["excess_returns"]["excess_30d_vs_QQQ"]["value"]
    vs_soxx = scored["excess_returns"]["excess_30d_vs_SOXX"]["value"]
    assert vs_qqq is not None and vs_soxx is not None
    # 標的漲得比 QQQ 快、比 SOXX 慢：**兩個基準給出相反符號**，而那正是要同時印的理由。
    assert vs_qqq > 0 > vs_soxx


def test_lead_filter_reports_input_accepted_filtered_reasons() -> None:
    """INV-3：每個 filter 都能報 input／accepted／filtered／reasons。"""
    leads = {
        "1": {"lead_id": "1", "source": "x:acct", "published_at": "2026-09-01T00:00:00+00:00",
              "entities": {"company_ids": ["co:aaa"], "tickers": ["AAA"]}, "status": "parked"},
        "2": {"lead_id": "2", "source": "x:acct", "published_at": "2026-09-01T00:00:00+00:00",
              "entities": {"company_ids": [], "tickers": []}, "status": "triaged_no_go"},
        "3": {"lead_id": "3", "source": "x:acct", "published_at": "2026-09-01T00:00:00+00:00",
              "entities": {"company_ids": [], "tickers": ["ZZZ"]}, "status": "parked"},
    }
    calls, report = sc.collect_named_calls(leads, harvest_key="x:acct",
                                           ticker_map={"co:aaa": "AAA"})
    payload = report.as_dict()
    assert payload["input"] == 3 and payload["accepted"] == 1 and payload["filtered"] == 2
    assert payload["reasons"]["no_named_company"] == 1
    assert payload["reasons"]["ticker_without_registry_company_id"] == 1
    assert [c.symbol for c in calls] == ["AAA"]


def test_ticker_without_registry_company_id_is_filtered_not_guessed() -> None:
    """INV-1：ticker 不是 identity。抽到 `SIVE` 不得自己補成 `SIVE.ST` 去查價。"""
    leads = {"1": {"lead_id": "1", "source": "x:acct", "published_at": "2026-09-01T00:00:00+00:00",
                   "entities": {"company_ids": [], "tickers": ["SIVE"]}, "status": "parked"}}
    calls, report = sc.collect_named_calls(leads, harvest_key="x:acct", ticker_map={})
    assert calls == []
    assert report.as_dict()["reasons"]["ticker_without_registry_company_id"] == 1


def test_first_call_per_symbol_keeps_earliest_only() -> None:
    """去重取最早一次——重複點名不得把中位數拉成「它多常提某一檔」。"""
    calls = [_call("AAA", "2026-09-10"), _call("AAA", "2026-07-01"), _call("BBB", "2026-08-01")]
    deduped = sc.first_call_per_symbol(calls)
    assert [(c.symbol, c.called_on.isoformat()) for c in deduped] == [
        ("AAA", "2026-07-01"), ("BBB", "2026-08-01")]


def test_trace_success_denominator_is_only_traced_calls() -> None:
    """沒去追的不進分母——「沒去追」與「追不到」是兩件事。"""
    calls = [_call("AAA", "2026-09-01", trace="original_obtained"),
             _call("BBB", "2026-09-01", trace="partial"),
             _call("CCC", "2026-09-01")]
    metric = sc.trace_success(calls)
    assert metric.n == 2 and metric.value == pytest.approx(0.5)


def test_no_go_rate_excludes_undecided_leads() -> None:
    """no-go 率的分母是**已 triage 的**；還沒判的不算（否則會隨待辦積壓而虛低）。"""
    leads = {
        "1": {"source": "x:acct", "status": "triaged_no_go"},
        "2": {"source": "x:acct", "status": "parked"},
        "3": {"source": "x:acct", "status": "pending"},
        "4": {"source": "x:other", "status": "triaged_no_go"},
    }
    metric = sc.no_go_share(leads, harvest_key="x:acct")
    assert metric.n == 2 and metric.value == pytest.approx(0.5)


def test_known_biases_are_a_field_not_a_footnote() -> None:
    """三個偏差必須在 artifact 裡，而且逐字包含 SOXX 那一條的理由。"""
    assert len(sc.KNOWN_BIASES) == 3
    assert any("SOXX" in b for b in sc.KNOWN_BIASES)
    assert any("倖存者" in b for b in sc.KNOWN_BIASES)


def test_stamp_records_close_or_declares_why_not() -> None:
    """D5 的蓋章：有價格就記價格，沒有就宣告 absence——不得留一個看不出差別的 None。"""
    call = _call("AAA", "2026-09-10")
    with_price = call.stamp({"AAA": _flat_series("2026-09-01", 20, 1.0)})
    without = call.stamp({})
    assert with_price["close_on_call"] is not None and with_price["close_absent_kind"] is None
    assert without["close_on_call"] is None and without["close_absent_kind"] == "upstream_missing"


# ---------------------------------------------------------------------------
# harvest 每月花費上限
# ---------------------------------------------------------------------------

def test_harvest_config_declares_a_monthly_spend_cap() -> None:
    """出貨的 config 必須有上限——沒有上限的付費來源會安靜地一直花下去。"""
    from crons import harvest_leads

    cfg = harvest_leads.load_config()
    cap = (cfg.get("x_accounts") or {}).get("monthly_spend_cap_usd")
    assert isinstance(cap, (int, float)) and 0 < float(cap) <= 1000


def test_config_without_spend_cap_is_rejected(tmp_path) -> None:
    """未宣告不得預設無上限（INV-5 在花錢這一側的樣子）。"""
    from crons import harvest_leads

    path = tmp_path / "harvest_config.json"
    path.write_text(json.dumps({"feeds": [], "x_accounts": {"handles": ["a"]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="monthly_spend_cap_usd"):
        harvest_leads.load_config(path)


def test_budget_exhausted_is_not_a_failure() -> None:
    """預算保護生效不是故障——否則健康段會每天亮一次，而恆亮等於零鑑別力（L14-4）。"""
    from engine_b import leads

    assert "budget_exhausted" in leads.HARVEST_RESULTS
    store = {"harvest_log": [
        {"source": "x:acct", "result": "budget_exhausted", "run_at": "2026-09-17T00:00:00+00:00"},
        {"source": "rss:foo", "result": "fetch_failed", "run_at": "2026-09-17T00:00:00+00:00"},
    ]}
    unresolved = [r["source"] for r in leads.unresolved_harvest_failures(store)]
    assert unresolved == ["rss:foo"]
    assert [r["source"] for r in leads.budget_halted_sources(store)] == ["x:acct"]


def test_monthly_spend_only_counts_recorded_costs() -> None:
    """只加總確實帶 cost_usd 的紀錄；舊紀錄算 0（方向刻意偏寬鬆，見 docstring）。"""
    from engine_b import leads

    store = {"harvest_log": [
        {"source": "x:a", "result": "ok", "run_at": "2026-09-01T00:00:00+00:00", "cost_usd": 1.25},
        {"source": "x:a", "result": "ok", "run_at": "2026-09-02T00:00:00+00:00"},
        {"source": "x:a", "result": "ok", "run_at": "2026-08-31T00:00:00+00:00", "cost_usd": 99.0},
        {"source": "rss:b", "result": "ok", "run_at": "2026-09-03T00:00:00+00:00", "cost_usd": 5.0},
    ]}
    assert leads.monthly_spend_usd(store, month="2026-09") == pytest.approx(1.25)


def test_state_flag_list_covers_every_state_materializer() -> None:
    """新增 state materializer 必須同時加進 `_STATE_FLAGS`，否則它會被當成「沒指定」而重跑全部單檔。"""
    from webapp.__main__ import _STATE_FLAGS
    from webapp.contracts import STATE_KINDS

    assert set(STATE_KINDS) == set(_STATE_FLAGS), (
        "state kind 與 CLI flag 對不起來——漏掉的那個不會壞，只會安靜地多做十分鐘的事（L17）")


def test_time_bound_absence_carries_a_revisit_date_and_capability_absence_does_not() -> None:
    """兩種缺席的下一步完全相反，所以不得在讀者眼裡同形（ROADMAP Phase 3 驗收行 A 案）。

    `insufficient_sample`＝**等時間**，必須答得出「哪一天會有值」（INV-2：每個等待都要有到期）；
    `capability_absent`＝**要建能力**，等到天荒地老也不會有值，所以刻意**沒有** `revisit_after`。
    """
    from datetime import date as _date, timedelta as _timedelta

    called_on = _date(2026, 6, 29)
    calls = [sc.NamedCall(lead_id="lead_x", source="x:acct", company_id="co:axt",
                          symbol="AXTI", called_on=called_on, status="triaged_go",
                          trace_status="original_obtained")]
    payload = sc.score_account(
        calls,
        prices={},                       # 沒有價格序列不影響「持有期還沒走完」那條路徑
        today=called_on + _timedelta(days=40),
        no_go_rate=sc.Metric(value=0.5, n=2),
        trace_metric=sc.Metric(value=0.5, n=2),
    )

    ninety = payload["excess_returns"]["excess_90d_vs_QQQ"]
    assert ninety["value"] is None
    assert ninety["absence_kind"] == "insufficient_sample"
    # 最早那一則點名走完 90 天的那一天＝這一格該有第一個值的日子。
    assert ninety["revisit_after"] == (called_on + _timedelta(days=90)).isoformat()

    hypothesis = payload["hypothesis_hit_rate"]
    assert hypothesis["value"] is None
    assert hypothesis["absence_kind"] == "capability_absent"
    assert "revisit_after" not in hypothesis, "要建能力的缺席不得假裝只是等時間"
    assert "ROADMAP" in hypothesis["reason"], "capability_absent 必須指出要建什麼"
