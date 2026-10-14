"""事件的相對反應（個股頁 S3e，2026-10-14；`alpha/event_reaction.py`＋`alpha/providers/event_reaction.py`）。

守：①基準＝事件日之前最後一個收盤、第 n 日＝事件日當天起第 n 個交易日；相對＝本檔 − 組員平均；②還沒滿 n 日寫「還沒滿」、
組員不足一半具名缺席、交易日曆不同的市場照樣對得上；③同一則新聞叫醒兩個等待＝一件事；④事件只來自這一檔名下醒過的等待與
已過的**確定**檢核點（估計日期照數寫出來、不算）；⑤as-of 只看那天以前已經醒的；⑥頁面合約與前端只照抄。"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from alpha.event_reaction import dedupe, page_reactions, window_reaction
from alpha.providers.event_reaction import company_events


def _bars(start: date, closes: list[float], *, skip_weekends: bool = True) -> list[tuple[date, float]]:
    out, day = [], start
    for close in closes:
        while skip_weekends and day.weekday() >= 5:
            day += timedelta(days=1)
        out.append((day, close))
        day += timedelta(days=1)
    return out


MON = date(2026, 10, 5)                                   # 週一


def test_base_is_the_close_before_the_event_and_day_n_counts_from_the_event_day() -> None:
    own = _bars(date(2026, 9, 28), [100, 100, 100, 100, 100, 110, 121, 121, 121, 121, 121])  # 10/05 起漲
    members = {"M1": _bars(date(2026, 9, 28), [50] * 5 + [51] * 6), "M2": _bars(date(2026, 9, 28), [20] * 5 + [20.4] * 6)}
    out = window_reaction(own, members, MON, windows=(1, 5))
    assert out["base_date"] == "2026-10-02" and out["base_close"] == 100     # 事件日（週一）之前最後一個收盤＝上週五
    day1, day5 = out["windows"]
    assert day1["end_date"] == "2026-10-05" and day1["own"] == 0.1          # 事件日當天的收盤就是第 1 日
    assert day1["cohort_mean"] == 0.02 and day1["relative"] == 0.08 and day1["members_used"] == 2
    assert day5["end_date"] == "2026-10-09" and day5["own"] == 0.21


def test_windows_not_reached_yet_are_pending_and_thin_cohorts_are_named() -> None:
    own = _bars(date(2026, 9, 28), [100] * 5 + [105, 106])                  # 事件後只有兩個交易日
    out = window_reaction(own, {"M1": _bars(date(2026, 9, 28), [10] * 7), "M2": []}, MON)
    one, five, twenty = out["windows"]
    assert "pending" not in one and five["pending"].startswith("還沒滿 5 個交易日") and "還沒滿 20" in twenty["pending"]
    thin = window_reaction(own, {"M1": [], "M2": [], "M3": _bars(date(2026, 9, 28), [10] * 7)}, MON, windows=(1,))
    assert "不足一半" in thin["windows"][0]["absence"] and thin["windows"][0]["own"] == 0.05
    none = window_reaction(_bars(MON, [100, 101]), {}, MON)
    assert none["absence"].startswith("事件日之前沒有這家的收盤")


def test_members_on_other_calendars_use_their_last_close_on_or_before_the_end_date() -> None:
    own = _bars(date(2026, 9, 28), [100] * 5 + [110])                      # 本檔 10/05（週一）收 110
    taiwan = [(date(2026, 10, 2), 50.0), (date(2026, 10, 6), 55.0)]        # 組員 10/05 休市：用 10/02 → 第 1 日（10/05）以前沒有新收盤
    us = [(date(2026, 10, 2), 20.0), (date(2026, 10, 5), 21.0)]
    out = window_reaction(own, {"TW": taiwan, "US": us}, MON, windows=(1,))
    window = out["windows"][0]
    assert window["members_used"] == 1 and window["cohort_mean"] == 0.05   # 台股那一家這一段沒有收盤，不算進平均


def test_the_same_news_waking_two_waits_is_one_event_and_newest_comes_first() -> None:
    events = [{"key": "lead:L1", "kind": "lead", "date": "2026-10-07", "label": "a", "sources": ["ew_1"]},
              {"key": "lead:L1", "kind": "lead", "date": "2026-10-07", "label": "a", "sources": ["ew_2"]},
              {"key": "watch:ew_3", "kind": "date", "date": "2026-10-12", "label": "b", "sources": ["ew_3"]}]
    out = dedupe(events)
    assert [e["key"] for e in out] == ["watch:ew_3", "lead:L1"] and out[1]["sources"] == ["ew_1", "ew_2"]


def test_page_reactions_list_events_even_without_a_cohort_and_name_the_missing_reaction() -> None:
    own_adj = _bars(date(2026, 9, 28), [100] * 5 + [110])
    own_raw = _bars(date(2026, 9, 28), [200] * 5 + [220])
    event = {"key": "lead:L1", "kind": "touched", "date": "2026-10-05", "label": "客戶公告擴產", "sources": ["ew_1"]}
    alone = page_reactions([event], adjusted_bars=own_adj, raw_bars=own_raw, cohorts=None,
                           cohort_absence={"kind": "not_yet_recorded", "reason": "不在任何主題等權組"}, quote_unit="USD")
    item = alone["events"][0]
    assert item["kind_label"] == "判定觸及" and item["price_before"] == {"date": "2026-10-02", "close": 200.0, "unit": "USD"}
    assert item["reactions"] == [] and item["reaction_absence"]["reason"] == "不在任何主題等權組"
    grouped = page_reactions([event], adjusted_bars=own_adj, raw_bars=own_raw, quote_unit="USD", cohort_absence=None,
                             cohorts=[{"cohort": {"record_id": "tc_x", "theme": "光通訊"},
                                       "member_bars": {"M1": _bars(date(2026, 9, 28), [10] * 5 + [10.5])}}])
    reaction = grouped["events"][0]["reactions"][0]
    assert reaction["theme"] == "光通訊" and reaction["windows"][0]["relative"] == 0.05
    empty = page_reactions([], adjusted_bars=(), raw_bars=(), cohorts=None, cohort_absence=None, quote_unit=None)
    assert empty["absence"]["kind"] == "not_yet_recorded" and empty["events"] == []


def test_the_page_contract_counts_only_events_with_a_computed_relative_window() -> None:
    from briefing.analyst_view import page_schema as ps
    from webapp.materialize import page_extra_for

    computed = {"events": [{"key": "lead:L1", "reactions": [{"windows": [{"n": 1, "relative": 0.02}, {"n": 5, "pending": "還沒滿"}]}]},
                           {"key": "watch:ew_2", "reactions": [{"windows": [{"n": 1, "pending": "還沒滿"}]}]}], "absence": None}
    extra = page_extra_for("X", None, reaction=computed)
    assert extra["event_reaction"] == ["lead:L1"]                         # 只有「還沒滿」的那件不算有值
    rows = {r["element"]: r for r in ps.fill_table({}, extra=extra)}
    assert rows["B5.relative_reaction"]["state"] == "value"
    waiting = page_extra_for("X", None, reaction={"events": [computed["events"][1]], "absence": None})
    rows = {r["element"]: r for r in ps.fill_table({}, extra=waiting)}
    assert rows["B5.relative_reaction"]["absence_kind"] == "not_yet_recorded"
    unread = page_extra_for("X", None, reaction={"events": [], "absence": {"kind": "upstream_unavailable"}}) or {}
    rows = {r["element"]: r for r in ps.fill_table({}, extra=unread)}
    assert rows["B5.relative_reaction"]["absence_kind"] == "upstream_unavailable"     # 讀不到≠沒有


def test_the_b5_lines_only_copy_the_materialized_reactions() -> None:
    import re
    from pathlib import Path

    app = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")

    def body(name: str) -> str:
        start = app.index(f"function {name}(")
        nxt = re.search(r"\n(?:async )?function |\nconst [A-Z_]+ =", app[start + 10:])
        return app[start: start + 10 + (nxt.start() if nxt else len(app))]

    assert "eventReactionLines(payload)" in body("blockVisuals")
    lines = body("eventReactionLines")
    for copied in ("payload.event_reaction", "e.kind_label", "w.relative", "w.pending", "r.absence", "e.reaction_absence",
                   "counts.estimated_checkpoints", "e.price_before"):
        assert copied in lines, copied
    for forbidden in (".sort(", "value / ", "reduce(("):
        assert forbidden not in lines, forbidden


def _brief(brief_id: str) -> SimpleNamespace:
    return SimpleNamespace(brief_id=brief_id, retracted=False, rides=(), disproof=())


def test_events_are_dates_touched_conditions_filings_and_confirmed_checkpoints_only() -> None:
    """AI 標旗還沒判定、判定沒觸及的不算事件（2026-10-14 實測：一則穩懋法說會公告叫醒六家公司的同一個條件，判定沒觸及）。"""
    flagged = {"kind": "semantic_condition", "at": "2026-10-08T01:00:00+00:00", "lead_id": "L2"}
    watches = [
        {"watch_id": "ew_1", "kind": "semantic_condition", "wake_brief": "co:x", "status": "fired", "condition": "客戶改用第二家",
         "judgments": [{"touches": "yes"}], "woken_by": {"kind": "semantic_condition", "at": "2026-10-08T01:00:00+00:00",
                                                       "lead_id": "L1"}},
        {"watch_id": "ew_2", "kind": "date", "wake_brief": "co:x", "status": "consumed", "until": "2026-10-12",
         "note": "9 月月營收後重寫", "woken_by": {"kind": "date", "at": "2026-10-12T22:00:00+00:00"}},
        {"watch_id": "ew_3", "kind": "semantic_condition", "source_ref": "brief:ib_x#1", "status": "active"},     # 沒醒
        {"watch_id": "ew_4", "kind": "semantic_condition", "wake_brief": "co:other", "status": "fired",
         "judgments": [{"touches": "yes"}], "woken_by": {"kind": "semantic_condition", "at": "2026-10-09T00:00:00+00:00"}},
        {"watch_id": "ew_5", "kind": "semantic_condition", "source_ref": "brief:ib_x#2", "status": "fired",
         "woken_by": flagged},                                                                                  # 標旗、沒判定
        {"watch_id": "ew_6", "kind": "semantic_condition", "source_ref": "brief:ib_x#3", "status": "consumed",
         "judgments": [{"touches": "no"}], "woken_by": flagged},                                                # 判定沒觸及
        {"watch_id": "ew_7", "kind": "entity_filing_signal", "wake_brief": "co:x", "status": "consumed",
         "woken_by": {"kind": "entity_filing_signal", "at": "2026-10-13T02:00:00+00:00", "lead_id": "L3"}},
        {"watch_id": "ew_8", "kind": "fact_verification", "wake_brief": "co:x", "status": "consumed",
         "woken_by": {"kind": "fact_verification", "at": "2026-10-11T00:00:00+00:00"}},                         # 其他醒法
    ]
    leads = {"L1": {"title": "客戶公告改用第二家", "published_at": "2026-10-07", "url": "https://example.com/a"},
             "L2": {"title": "別家的法說會公告", "published_at": "2026-10-07"},
             "L3": {"title": "X 10-Q filed 2026-10-12", "published_at": "2026-10-12"}}
    checkpoints = [{"date": "2026-10-09", "date_confidence": "estimated", "what": "Q3 財報"},
                   {"date": "2026-10-10", "date_confidence": "confirmed", "what": "股東會"},
                   {"date": "2026-11-30", "date_confidence": "confirmed", "what": "還沒到"}]
    events, counts = company_events("co:x", "X", as_of=date(2026, 10, 14), watches=watches, leads=leads,
                                    brief_records=[_brief("ib_x")], lifecycle={}, checkpoints=checkpoints)
    by_key = {e["key"]: e for e in events}
    assert set(by_key) == {"lead:L1", "watch:ew_2", "lead:L3", "checkpoint:2026-10-10:股東會"}
    assert by_key["lead:L1"]["kind"] == "touched" and by_key["lead:L1"]["date"] == "2026-10-07"
    assert by_key["lead:L1"]["label"] == "客戶改用第二家" and by_key["lead:L1"]["lead_title"] == "客戶公告改用第二家"
    assert by_key["watch:ew_2"]["kind"] == "date" and by_key["watch:ew_2"]["date_basis"] == "watch_date"
    assert by_key["lead:L3"]["kind"] == "filing" and by_key["lead:L3"]["date"] == "2026-10-12"
    assert counts == {"after_as_of": 0, "flagged_unjudged": 1, "judged_not_touched": 1, "other_wakes": 1,
                      "estimated_checkpoints": 1}
    past, past_counts = company_events("co:x", "X", as_of=date(2026, 10, 10), watches=watches, leads=leads,
                                       brief_records=[_brief("ib_x")], lifecycle={}, checkpoints=checkpoints)
    assert {e["key"] for e in past} == {"lead:L1", "checkpoint:2026-10-10:股東會"}          # 10/12 以後才醒的不算
    assert past_counts["after_as_of"] == 2
