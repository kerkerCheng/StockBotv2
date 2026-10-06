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


def test_status_vocabulary_is_the_registry_ssot() -> None:
    """2026-09-23（Phase 0 Step 0b.4）：status 字彙原本借自 decision_lab.intake（L16）；intake 隨研究側
    退役後 registry 自己就是 SSOT，值逐字不變——這條鎖住它不漂。"""
    assert set(ssr.STATUSES) == {"candidate", "probation", "active", "suspended"}


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
    """偏差必須在 artifact 裡，而且逐字包含 SOXX 那一條的理由。
    Phase 5 Step 5.5 起第四條：主題等權組是回溯基準（成分是某一天才定的）。刻意硬編條數——加一條就該紅一次。"""
    assert len(sc.KNOWN_BIASES) == 4
    assert any("SOXX" in b for b in sc.KNOWN_BIASES)
    assert any("倖存者" in b for b in sc.KNOWN_BIASES)
    assert any("主題等權組" in b and "回溯" in b for b in sc.KNOWN_BIASES)


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


# ---------------------------------------------------------------------------
# Phase 5 Step 5.5：第三個基準＝主題等權組（plan §6）
# ---------------------------------------------------------------------------

def _cohort(*members: str, cohort_id: str = "tc_test", decided_on: str = "2026-09-30"):
    from datetime import datetime, timezone

    from alpha.theme_cohort import CohortMember, ThemeCohort

    return ThemeCohort(cohort_id=cohort_id, theme="ai_capex_optical",
                       members=tuple(CohortMember(t, f"co:{t}", "test") for t in members),
                       excluded=(), reason="test", decided_on=date.fromisoformat(decided_on), pq2_ref=1,
                       created_at=datetime(2026, 9, 30, tzinfo=timezone.utc))


#: 2026-07-01 起 130 天的線性序列：AAA 每天 +1、BBB +0.5、CCC +2、QQQ +0.3、SOXX +0.8。
_SERIES = {"AAA": (1.0, 100.0), "BBB": (0.5, 100.0), "CCC": (2.0, 100.0), "QQQ": (0.3, 100.0), "SOXX": (0.8, 100.0)}


def _prices(*symbols: str):
    return {s: _flat_series("2026-07-01", 130, *_SERIES[s]) for s in symbols}


def _ret(symbol: str, start: str, end: str) -> float:
    series = _prices(symbol)[symbol]
    return series[date.fromisoformat(end)] / series[date.fromisoformat(start)] - 1.0


def test_theme_cohort_excess_equals_the_hand_computation() -> None:
    """點名的 AAA 是組員、另兩個成員 → 對組的超額＝本檔報酬 − 另兩個成員報酬的等權平均（手算；本檔排除）。"""
    scored = sc.score_account([_call("AAA", "2026-08-01")], prices=_prices("AAA", "BBB", "CCC", "QQQ", "SOXX"),
                              today=date(2026, 10, 31), no_go_rate=sc.Metric(), trace_metric=sc.Metric(),
                              cohorts=[_cohort("AAA", "BBB", "CCC")])
    expected = _ret("AAA", "2026-08-01", "2026-08-31") - (
        _ret("BBB", "2026-08-01", "2026-08-31") + _ret("CCC", "2026-08-01", "2026-08-31")) / 2
    cell = scored["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] == pytest.approx(expected) and cell["n"] == 1
    ninety = scored["excess_returns"]["excess_90d_vs_theme_cohort"]
    assert ninety["value"] == pytest.approx(_ret("AAA", "2026-08-01", "2026-10-30") - (
        _ret("BBB", "2026-08-01", "2026-10-30") + _ret("CCC", "2026-08-01", "2026-10-30")) / 2)
    # QQQ／SOXX 兩格照舊：第三個基準是**加**一格，不取代任何一格
    assert scored["excess_returns"]["excess_30d_vs_QQQ"]["value"] == pytest.approx(
        _ret("AAA", "2026-08-01", "2026-08-31") - _ret("QQQ", "2026-08-01", "2026-08-31"))


def test_the_called_symbol_is_excluded_from_its_own_theme_cohort() -> None:
    """本檔是成員時從組裡排除——不然它一部分是在跟自己比。"""
    scored = sc.score_account([_call("AAA", "2026-08-01")], prices=_prices("AAA", "BBB", "QQQ", "SOXX"),
                              today=date(2026, 10, 31), no_go_rate=sc.Metric(), trace_metric=sc.Metric(),
                              cohorts=[_cohort("AAA", "BBB")])
    cell = scored["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] == pytest.approx(
        _ret("AAA", "2026-08-01", "2026-08-31") - _ret("BBB", "2026-08-01", "2026-08-31"))


def test_absent_cohort_is_not_yet_recorded_not_zero() -> None:
    """沒有組 → 每一格是 `not_yet_recorded` 缺席（附理由），不是 0、也不是「樣本不足」。"""
    scored = sc.score_account([_call("AAA", "2026-08-01")], prices=_prices("AAA", "QQQ", "SOXX"),
                              today=date(2026, 10, 31), no_go_rate=sc.Metric(), trace_metric=sc.Metric(),
                              cohorts=(), cohort_absence={"kind": "not_yet_recorded", "reason": "主題等權組未定義"})
    for horizon in sc.HORIZONS_DAYS:
        cell = scored["excess_returns"][f"excess_{horizon}d_vs_theme_cohort"]
        assert cell["value"] is None and cell["absence_kind"] == "not_yet_recorded" and cell["reason"]


def test_unpriced_cohort_is_insufficient_sample_with_its_own_reason() -> None:
    """組在、本檔是組員、其他成員一檔都取不到價 → 缺席，filter reasons 寫 `theme_cohort_unpriced`（不與「標的沒價」混成一條）。"""
    scored = sc.score_account([_call("AAA", "2026-08-01")], prices=_prices("AAA", "QQQ", "SOXX"),
                              today=date(2026, 10, 31), no_go_rate=sc.Metric(), trace_metric=sc.Metric(),
                              cohorts=[_cohort("AAA", "BBB")])
    cell = scored["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] is None and cell["absence_kind"] == sc.ABSENCE_INSUFFICIENT
    assert scored["excess_return_filters"]["excess_30d_vs_theme_cohort"]["reasons"] == {"theme_cohort_unpriced": 1}


def test_a_call_on_a_non_member_is_filtered_and_named_never_borrows_another_cohort() -> None:
    """多主題等權組 S1（選項 A）：點名的標的不是任何組的組員 → 那一格 `not_in_any_cohort`（filter reasons 照計），
    QQQ／SOXX 兩格照算。只有組員點名時才比；組員與非組員混在一起時只算組員那幾則。

    變異：讓非組員也拿現有那一組比 → 這一格會有值，這條紅。"""
    only_outsider = sc.score_account([_call("AAA", "2026-08-01")], prices=_prices("AAA", "BBB", "CCC", "QQQ", "SOXX"),
                                     today=date(2026, 10, 31), no_go_rate=sc.Metric(), trace_metric=sc.Metric(),
                                     cohorts=[_cohort("BBB", "CCC")])
    cell = only_outsider["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] is None and cell["absence_kind"] == "not_in_any_cohort" and "1 則點名" in cell["reason"]
    assert only_outsider["excess_return_filters"]["excess_30d_vs_theme_cohort"]["reasons"] == {"not_in_any_cohort": 1}
    assert only_outsider["excess_returns"]["excess_30d_vs_QQQ"]["value"] is not None
    mixed = sc.score_account([_call("AAA", "2026-08-01"), _call("BBB", "2026-08-01")],
                             prices=_prices("AAA", "BBB", "CCC", "QQQ", "SOXX"), today=date(2026, 10, 31),
                             no_go_rate=sc.Metric(), trace_metric=sc.Metric(), cohorts=[_cohort("BBB", "CCC")])
    cell = mixed["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["n"] == 1 and cell["value"] == pytest.approx(
        _ret("BBB", "2026-08-01", "2026-08-31") - _ret("CCC", "2026-08-01", "2026-08-31"))
    assert mixed["excess_return_filters"]["excess_30d_vs_theme_cohort"]["reasons"] == {"not_in_any_cohort": 1}


def test_a_member_whose_cohort_is_unpriced_is_still_a_member_not_an_outsider() -> None:
    """「組員但組報酬取不到」（theme_cohort_unpriced）是組員的理由：旁邊有非組員點名時，那一格是「樣本不足」，
    不得被併成「沒有一則是組員」（R2 2026-10-06：兩種缺席分開；`NON_MEMBER_KINDS` 不含它）。

    變異：只把「組報酬算得出」的點名算成組員（`member_days` 移到組報酬之後）→ 這一格變成 not_in_any_cohort，這條紅。
    （把 theme_cohort_unpriced 塞進 `NON_MEMBER_KINDS` 在現行邏輯裡是等價變異：組員與否看 `member_days`，不看理由集合。）"""
    scored = sc.score_account([_call("AAA", "2026-08-01"), _call("CCC", "2026-08-01")],
                              prices=_prices("AAA", "CCC", "QQQ", "SOXX"), today=date(2026, 10, 31),
                              no_go_rate=sc.Metric(), trace_metric=sc.Metric(), cohorts=[_cohort("AAA", "BBB")])
    cell = scored["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] is None and cell["absence_kind"] == sc.ABSENCE_INSUFFICIENT
    assert scored["excess_return_filters"]["excess_30d_vs_theme_cohort"]["reasons"] == {
        "theme_cohort_unpriced": 1, "not_in_any_cohort": 1}


def test_waiting_member_calls_keep_their_revisit_date_even_with_non_members_around() -> None:
    """INV-2：組員點名的持有期還沒走完 → `revisit_after` 照算；旁邊多一則非組員點名不得讓到期日消失。"""
    scored = sc.score_account([_call("AAA", "2026-10-20"), _call("CCC", "2026-08-01")],
                              prices=_prices("AAA", "BBB", "CCC", "QQQ", "SOXX"), today=date(2026, 10, 31),
                              no_go_rate=sc.Metric(), trace_metric=sc.Metric(), cohorts=[_cohort("AAA", "BBB")])
    cell = scored["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] is None and cell["absence_kind"] == sc.ABSENCE_INSUFFICIENT
    assert cell["revisit_after"] == "2026-11-19"


@pytest.fixture()
def scorecard_env(monkeypatch, tmp_path):
    """一個帳號（`x:acct`）、一則點名 AAA（2026-08-01）、名冊只認得 AAA——不讀真的 lead registry、登記表、名冊。"""
    import identity.registry as registry_mod

    source_path = _write_registry(tmp_path, [
        {"source_id": "acct", "platform": "x", "handle": "acct", "status": "active", "tier": "probation",
         "research_priority": 1, "auto_capture": True}])
    real_load = ssr.load
    monkeypatch.setattr(ssr, "load", lambda path=None: real_load(source_path))

    class _Registry:
        ticker_map = {"co:AAA": "AAA"}

    monkeypatch.setattr(registry_mod, "get_registry", lambda: _Registry())
    leads = tmp_path / "pending_leads.json"
    leads.write_text(json.dumps({"leads": {"lead_1": {
        "lead_id": "lead_1", "source": "x:acct", "published_at": "2026-08-01T12:00:00Z", "status": "parked",
        "entities": {"company_ids": ["co:AAA"], "tickers": ["AAA"]}, "refs": {}}}}), encoding="utf-8")
    asked: list[list[str]] = []

    def loader(wanted, start, end):
        asked.append(list(wanted))
        return _prices(*[s for s in wanted if s in _SERIES])

    return {"leads": leads, "loader": loader, "asked": asked}


def _build(env, **kw):
    return sc.build_scorecard(leads_path=env["leads"], today=date(2026, 10, 31), price_loader=env["loader"], **kw)


def fake_scorecard_payload(directory) -> dict:
    """給 APP request path 測試用的計分表 artifact：**真的 `build_scorecard`**（出貨的登記表與名冊、空的 lead 檔、
    不抓價、沒有組）——形狀跟著真的 materializer 走，不另手寫一份會漂開的假 payload。"""
    from pathlib import Path

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    leads = directory / "pending_leads.json"
    leads.write_text(json.dumps({"leads": {}}), encoding="utf-8")
    return sc.build_scorecard(leads_path=leads, today=date(2026, 10, 2), price_loader=lambda *_: {},
                              cohorts=([], []))


def test_build_adds_cohort_members_to_the_price_list_and_reports_the_block(scorecard_env) -> None:
    """成員併進取價清單（集合、去重）：`requested` 增加的數＝成員中原本不在清單的檔數；payload 印組的來歷。"""
    card = _build(scorecard_env, cohorts=([_cohort("AAA", "BBB", "CCC", "QQQ")], []))
    budget = card["price_budget"]
    assert budget["theme_cohort_added"] == ["BBB", "CCC"]           # AAA（點名）與 QQQ（基準）本來就在
    assert budget["requested"] == 2 + 1 + 2 and budget["truncated"] == []
    assert scorecard_env["asked"] == [["AAA", "BBB", "CCC", "QQQ", "SOXX"]]
    from alpha.theme_cohort import ROW_COHORT_ABSENCE_LABELS

    block = card["theme_cohort"]
    assert block == {"mode": "per_row", "absence": None, "parse_errors": [],
                     "absence_labels": dict(ROW_COHORT_ABSENCE_LABELS),
                     "cohorts": [{"cohort_id": "tc_test", "theme": "ai_capex_optical", "decided_on": "2026-09-30",
                                  "members_total": 4, "members_priced": 4, "missing": []}]}
    cell = card["accounts"][0]["metrics"]["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] == pytest.approx(_ret("AAA", "2026-08-01", "2026-08-31") - sum(
        _ret(s, "2026-08-01", "2026-08-31") for s in ("BBB", "CCC", "QQQ")) / 3)
    assert card["schema_version"] == "stockbot-app/account_scorecard/3"


def test_truncation_cuts_cohort_members_before_calls_and_never_benchmarks(scorecard_env, monkeypatch) -> None:
    """L11-6 ④：最先壞的是截斷——成員不是基準、可被截，但不得把基準或點名標的擠掉；被截的照印、該格缺席。"""
    monkeypatch.setattr(sc, "MAX_PRICED_SYMBOLS", 3)
    card = _build(scorecard_env, cohorts=([_cohort("AAA", "BBB", "CCC")], []))
    assert card["price_budget"]["truncated"] == ["BBB", "CCC"]
    assert scorecard_env["asked"] == [["AAA", "QQQ", "SOXX"]]
    entry = card["theme_cohort"]["cohorts"][0]
    assert entry["missing"] == ["BBB", "CCC"] and entry["members_priced"] == 1        # 只剩點名的 AAA 自己有價
    metrics = card["accounts"][0]["metrics"]["excess_returns"]
    assert metrics["excess_30d_vs_QQQ"]["value"] is not None and metrics["excess_30d_vs_SOXX"]["value"] is not None
    assert metrics["excess_30d_vs_theme_cohort"]["value"] is None
    assert "theme_cohort.missing" in card["price_note"]


@pytest.mark.parametrize("cohorts, kind", [
    (([], []), "not_yet_recorded"),
    (None, "upstream_unavailable"),
])
def test_cohort_absence_kinds_reach_the_payload(scorecard_env, monkeypatch, cohorts, kind) -> None:
    """0 組 → `not_yet_recorded`；ledger 讀不到 → `upstream_unavailable`（計分表其餘照算）；多組另見下一條。"""
    import alpha.providers.theme_cohorts as provider

    def broken(**_kw):
        raise OSError("ledger unreadable")

    monkeypatch.setattr(provider, "current_cohorts", broken)
    card = _build(scorecard_env, cohorts=cohorts)
    assert card["theme_cohort"]["absence"]["kind"] == kind
    cell = card["accounts"][0]["metrics"]["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] is None and cell["absence_kind"] == kind
    assert card["accounts"][0]["metrics"]["excess_returns"]["excess_30d_vs_QQQ"]["value"] is not None
    assert card["price_budget"]["theme_cohort_added"] == []


def test_several_cohorts_coexist_and_each_call_uses_its_own(scorecard_env) -> None:
    """多組並存不再整格缺席：每則點名用自己所屬的組；同時是兩組組員的點名 `ambiguous_membership`（不猜）。

    變異：改回「多於一組就整格 `ambiguous_cohort`」→ 第一張卡的那一格會缺席，這條紅。"""
    card = _build(scorecard_env, cohorts=([_cohort("AAA", "BBB", cohort_id="tc_a"), _cohort("CCC", "DDD", cohort_id="tc_b")], []))
    assert card["theme_cohort"]["absence"] is None
    assert [e["cohort_id"] for e in card["theme_cohort"]["cohorts"]] == ["tc_a", "tc_b"]
    cell = card["accounts"][0]["metrics"]["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] == pytest.approx(_ret("AAA", "2026-08-01", "2026-08-31") - _ret("BBB", "2026-08-01", "2026-08-31"))
    both = _build(scorecard_env, cohorts=([_cohort("AAA", "BBB", cohort_id="tc_a"), _cohort("AAA", "CCC", cohort_id="tc_b")], []))
    cell = both["accounts"][0]["metrics"]["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] is None and cell["absence_kind"] == "ambiguous_membership"
    assert both["accounts"][0]["metrics"]["excess_return_filters"]["excess_30d_vs_theme_cohort"]["reasons"] == {
        "ambiguous_membership": 1}


def test_freshness_follows_the_cohort_not_the_prices(scorecard_env) -> None:
    """換一組（cohort_id）＝認知變化；同一組、價格小數變動＝不是。"""
    first = _build(scorecard_env, cohorts=([_cohort("BBB")], []))
    shifted = dict(_SERIES, BBB=(0.6, 101.0))
    original = scorecard_env["loader"]

    def other_prices(wanted, start, end):
        original(wanted, start, end)
        return {s: _flat_series("2026-07-01", 130, *shifted[s]) for s in wanted if s in shifted}

    scorecard_env["loader"] = other_prices
    repriced = _build(scorecard_env, cohorts=([_cohort("BBB")], []))
    other = _build(scorecard_env, cohorts=([_cohort("BBB", cohort_id="tc_other")], []))
    assert first["freshness_identity"] == repriced["freshness_identity"]
    assert first["freshness_identity"] != other["freshness_identity"]


def test_render_and_heartbeat_show_the_cohort_cell(scorecard_env, tmp_path) -> None:
    """render 印組的來歷與每格；心跳段 5 只印「有／無」一格，不印數字。"""
    from crons import heartbeat as hb
    from webapp.store import StateArtifactStore

    card = _build(scorecard_env, cohorts=([_cohort("BBB", "CCC")], []))
    text = sc.render(card)
    assert ("主題等權組基準 1 組（每則點名只跟自己所屬的組比）：`tc_test`（ai_capex_optical，決定於 2026-09-30）"
            "｜成員 2、取得到價 2｜缺價：—") in text
    assert "excess_30d_vs_theme_cohort" in text and "**已知偏差" in text
    StateArtifactStore(tmp_path / "state").write(card)
    line = hb.build_scorecard(state_dir=tmp_path / "state").lines[-1]
    assert line.endswith("｜主題等權組基準：有（1 組，每則點名只比自己的組）"), line

    absent = _build(scorecard_env, cohorts=([], []))
    assert "主題等權組基準：無（not_yet_recorded）" in sc.render(absent)
    StateArtifactStore(tmp_path / "state").write(absent)
    assert hb.build_scorecard(state_dir=tmp_path / "state").lines[-1].endswith("主題等權組基準：無（not_yet_recorded）")
    assert sc.theme_cohort_line({}) .startswith("主題等權組基準：這份計分表早於這一格")


def test_yfinance_nan_close_is_skipped_so_the_endpoint_falls_back(monkeypatch) -> None:
    """§0.6 #3：yfinance 對尚未收盤的歐洲標的回 NaN 收盤——跳過它，端點退回前一根；不跳就算出 NaN 報酬。"""
    import sys
    import types
    from datetime import datetime as _dt, timedelta as _td

    days = [_dt(2026, 9, 1) + _td(days=i) for i in range(40)]
    closes = [100.0 + i for i in range(40)]
    closes[-1] = float("nan")                                    # 終點那一天是 NaN

    class _Column:
        def items(self):
            return zip(days, closes)

    class _Frame:
        empty = False

        def __contains__(self, key):
            return key == "Close"

        def __getitem__(self, key):
            return _Column()

    fake = types.SimpleNamespace(Ticker=lambda symbol: types.SimpleNamespace(history=lambda **kw: _Frame()))
    monkeypatch.setitem(sys.modules, "yfinance", fake)
    series = sc._yfinance_closes(["IQE.L"], date(2026, 9, 1), date(2026, 10, 10))["IQE.L"]
    assert days[-1].date() not in series and len(series) == 39
    move = sc._pct_change(series, date(2026, 9, 1), days[-1].date())
    assert move == pytest.approx(138.0 / 100.0 - 1.0)            # 退回前一根，不是 NaN
