"""叫醒先過預篩（failure log #96）：只比發文公司的追源／讀圖叫醒，預篩標觸及或看不出才放行，其餘擋下待互動確認。

守的機制：
- triage 的同步重排與 consume-fired 都問同一個 `event_watch.wake_screen`：抓得到全文、還沒標旗 → 不重排（lead 照舊停放）。
- 標「無關」仍擋著（只標旗不判定，G7）；互動 `wake-judge` 判無關才回 active，判觸及才放行給原 consumer。
- 抓不到全文的觸發照舊放行（不比修之前差）；修之前醒的（沒有 `screen`）照舊放行。
- 讀圖重讀理由同一個判斷；佇列段與 ⑤ 待做清單有自己的一格；預篩批次照文件算名額、全文只放一次。
"""
from __future__ import annotations

import pytest

from crons import llm_step
from crons.daily_task import chunk_items
from engine_b import event_watch as ew
from engine_b import leads
from engine_b import queue_segments as qs
from engine_b import semantic_prescreen as sp

FILING = "https://www.sec.gov/Archives/edgar/data/1051627/000105162726000041/axti-20261023.htm"


def _park(store, *, url="https://x.com/old/status/trace", trigger="AXT 下一份 10-Q 揭露磷化銦基板的中國出口許可進度"):
    lead_id, _ = leads.register(store, source="x:old", url=url, title="Waiting for $AXTI primary source")
    leads.triage(store, lead_id, go=True, tier=4, reason="需要追原文", decided_at="2026-08-01T00:00:00+00:00")
    leads.advance(store, lead_id, "parked", ref={
        "parked_reason": "目前只有 tier 3 轉述", "trace_status": "isolated_tier_3",
        "trace_next_trigger": trigger, "trace_requires_user": "false",
    })
    return lead_id


def _filing_event(store, url=FILING):
    event_id, _ = leads.register(store, source="edgar:AXTI", url=url, title="AXTI 8-K")
    event = leads.triage(store, event_id, go=True, tier=1, reason="一手 filing",
                         decided_at="2026-08-02T00:00:00+00:00")
    return event_id, event


def _watch_for(lead_id):
    data = ew.load_watches()
    return data, next(w for w in data["watches"] if w.get("wake_lead") == lead_id)


def test_fetchable_filing_holds_the_parked_lead_instead_of_requeueing() -> None:
    store = leads.empty_store()
    parked = _park(store)
    before = dict(store["leads"][parked]["refs"])
    event_id, event = _filing_event(store)

    assert store["leads"][parked]["status"] == "parked"           # 沒被叫回 pq1
    assert "related_trace_requeues" not in event["triage"]
    assert store["leads"][parked]["refs"] == before                # 停放理由與處置一筆都不動
    data, watch = _watch_for(parked)
    assert watch["status"] == "fired" and watch["woken_by"]["screen"] == "pending"
    assert ew.wake_screen(watch) == "held_unscreened"
    assert qs.classify_watch(watch) == "wake_screen_hold"
    assert ew.counters(data)["wake_held"] == 1

    result = leads.consume_fired_lead_watches(store, data)      # daily ⑨ 也不放行
    assert result["requeued"] == [] and [h["lead_id"] for h in result["held"]] == [parked]
    assert result["held"][0]["trigger_lead"] == event_id and watch["status"] == "fired"


def test_prescreen_unrelated_still_holds_until_interactive_judge() -> None:
    store = leads.empty_store()
    parked = _park(store)
    event_id, _ = _filing_event(store)
    data, watch = _watch_for(parked)
    ew.flag(data, watch["watch_id"], lead_id=event_id, verdict="likely_unrelated", note="只是循環信用合約修訂")
    assert ew.wake_screen(watch) == "held_unrelated"              # 只標旗不判定：不自動回 active
    assert leads.consume_fired_lead_watches(store, data)["requeued"] == []

    with pytest.raises(ew.EventWatchError):
        ew.judge_wake(data, watch["watch_id"], touches=False, note="  ")
    judgment = ew.judge_wake(data, watch["watch_id"], touches=False, note="8-K 只有 Item 1.01 信用合約")
    assert judgment["prescreen_verdict"] == "likely_unrelated"
    assert watch["status"] == "active" and event_id in watch["consumed_leads"]   # 同一份文件不會再叫醒
    assert "互動確認無關" in watch["reactivations"][-1]["note"]
    assert store["leads"][parked]["status"] == "parked"
    counts = ew.wake_screen_counts(data)
    assert counts["prescreen_unrelated_agreed"] == 1 and counts["prescreen_unrelated_wrong"] == 0
    with pytest.raises(ew.EventWatchError):                       # 回 active 後不能再判
        ew.judge_wake(data, watch["watch_id"], touches=False, note="x")


@pytest.mark.parametrize("verdict", ["likely_touches", "cannot_tell"])
def test_prescreen_touches_or_cannot_tell_releases_to_consume_fired(verdict) -> None:
    store = leads.empty_store()
    parked = _park(store)
    event_id, _ = _filing_event(store)
    data, watch = _watch_for(parked)
    quote = "export license for indium phosphide" if verdict == "likely_touches" else None
    ew.flag(data, watch["watch_id"], lead_id=event_id, verdict=verdict, quote=quote)
    assert ew.wake_screen(watch) == "pass" and qs.classify_watch(watch) == "fired_lead_requeue"

    result = leads.consume_fired_lead_watches(store, data, at="2026-08-03T00:00:00+00:00")
    assert result["requeued"] == [parked] and result["held"] == []
    assert store["leads"][parked]["status"] == "triaged_go"
    assert f"預篩 {verdict}" in store["leads"][parked]["requeued"][-1]["reason"]
    assert watch["status"] == "active"


def test_interactive_touches_needs_a_quote_and_then_releases() -> None:
    store = leads.empty_store()
    parked = _park(store)
    _filing_event(store)
    data, watch = _watch_for(parked)
    with pytest.raises(ew.EventWatchError):
        ew.judge_wake(data, watch["watch_id"], touches=True, note="有寫出口許可")
    ew.judge_wake(data, watch["watch_id"], touches=True, note="有寫出口許可", quote="export license")
    assert watch["woken_by"]["screen"] == "judged" and ew.wake_screen(watch) == "pass"
    assert leads.consume_fired_lead_watches(store, data, at="2026-08-03T00:00:00+00:00")["requeued"] == [parked]
    assert "互動判定觸及" in store["leads"][parked]["requeued"][-1]["reason"]


def test_unfetchable_trigger_releases_as_before_and_legacy_wakes_pass() -> None:
    store = leads.empty_store()
    parked = _park(store)
    # 不是 EDGAR 主文件路徑（抓不到全文）→ 照舊放行：不比修之前差
    _, event = _filing_event(store, url="https://www.sec.gov/Archives/edgar/data/axt/new-filing")
    assert event["triage"]["related_trace_requeues"] == [parked]
    legacy = {"status": "fired", "kind": "entity_filing_signal", "wake_lead": "L", "woken_by": {"lead_id": "x"}}
    assert ew.wake_screen(legacy) is None and ew.wake_released(legacy)


def test_date_and_fact_watches_are_not_screened() -> None:
    for kind in ("date", "fact_verification"):
        watch = {"status": "fired", "kind": kind, "wake_lead": "L", "woken_by": {"lead_id": "x", "screen": "pending"}}
        assert ew.wake_screen(watch) is None


def _reading_watch(screen, flag=None):
    watch = {"watch_id": "ew_r", "status": "fired", "kind": "entity_filing_signal", "wake_reading": "mat:inp_substrate",
             "entities": ["co:marvell_technology"],
             "woken_by": {"lead_id": "L1", "shared_entities": ["co:marvell_technology"], "screen": screen}}
    if flag:
        watch["semantic_flag"] = {"lead_id": "L1", "verdict": flag, "quote": "q" if flag == "likely_touches" else None}
    return watch


def test_reading_reread_reasons_wait_for_the_screen() -> None:
    from alpha.providers.structure_readings import reread_reasons

    assert reread_reasons("mat:inp_substrate", [_reading_watch("pending")]) == []
    assert reread_reasons("mat:inp_substrate", [_reading_watch("pending", "likely_unrelated")]) == []
    assert qs.classify_watch(_reading_watch("pending", "likely_unrelated")) == "wake_screen_hold"
    assert len(reread_reasons("mat:inp_substrate", [_reading_watch("pending", "cannot_tell")])) == 1
    assert len(reread_reasons("mat:inp_substrate", [_reading_watch("unfetchable")])) == 1


def test_prepare_screens_held_wakes_once_per_document(tmp_path, monkeypatch) -> None:
    base = ew.load_config()
    monkeypatch.setattr(ew, "load_config", lambda: {**base, "semantic_screen_daily_limit": 1,
                                                    "prescreen_text_max_chars": 1000})
    watches = []
    for i in range(3):                               # 同一份文件叫醒三條
        watch = _reading_watch("pending")
        watch["watch_id"] = f"ew_{i}"
        watches.append(watch)
    other = _reading_watch("pending")
    other["watch_id"], other["woken_by"] = "ew_9", {**other["woken_by"], "lead_id": "L2", "at": "z"}
    data = {"watches": [*watches, other]}
    leads_store = {"L1": {"source": "mops:3105.TWO", "raw_text": "全文一"},
                   "L2": {"source": "mops:3105.TWO", "raw_text": "全文二"}}
    batch = sp.prepare(data, leads_store, run_id="r", text_dir=tmp_path)
    assert [i["watch_id"] for i in batch["items"]] == ["ew_0", "ew_1", "ew_2"]     # 名額 1 份文件，三條都進
    assert batch["counts"]["documents"] == 1 and batch["counts"]["not_in_batch"] == 1
    assert "mat:inp_substrate" in batch["items"][0]["condition"]

    prompt = llm_step.compose_prescreen_prompt(batch["items"], max_chars=1000)
    assert prompt.count("全文一") == 1 and prompt.count("watch_id: ew_") == 3


def test_same_document_stays_together_even_when_woken_at_different_times(tmp_path, monkeypatch) -> None:
    base = ew.load_config()
    monkeypatch.setattr(ew, "load_config", lambda: {**base, "semantic_screen_daily_limit": 5,
                                                    "prescreen_text_max_chars": 1000})
    early, mid, late = _reading_watch("pending"), _reading_watch("pending"), _reading_watch("pending")
    early["watch_id"], early["woken_by"] = "ew_a", {**early["woken_by"], "at": "1"}
    mid["watch_id"], mid["woken_by"] = "ew_b", {**mid["woken_by"], "lead_id": "L2", "at": "2"}
    late["watch_id"], late["woken_by"] = "ew_c", {**late["woken_by"], "at": "3"}
    leads_store = {"L1": {"source": "mops:3105.TWO", "raw_text": "一"}, "L2": {"source": "mops:3105.TWO", "raw_text": "二"}}
    batch = sp.prepare({"watches": [early, mid, late]}, leads_store, run_id="r", text_dir=tmp_path)
    assert [i["watch_id"] for i in batch["items"]] == ["ew_a", "ew_c", "ew_b"]


def test_wake_condition_reads_the_parked_trigger() -> None:
    watch = {"wake_lead": "P", "kind": "entity_filing_signal"}
    condition = sp.wake_condition(watch, {"P": {"title": "t", "refs": {"trace_next_trigger": "等 10-Q 揭露出口許可"}}})
    assert "等 10-Q 揭露出口許可" in condition and "例行申報" in condition


def test_company_press_page_fetcher_only_talks_to_the_harvested_feed_host(tmp_path, monkeypatch) -> None:
    import json

    config = tmp_path / "harvest_config.json"
    config.write_text(json.dumps({"feeds": [
        {"source": "sivers:press", "source_class": "primary",
         "url": "https://www.sivers-semiconductors.com/?feed=rss2&post_type=press"},
        {"source": "yahoo:iqe-l", "source_class": "secondary", "url": "https://feeds.finance.yahoo.com/rss"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(sp, "HARVEST_CONFIG", config)
    page = "https://www.sivers-semiconductors.com/press/bulletin-egm/"
    assert sp.fetcher_for({"source": "sivers:press", "url": page}) is not None
    assert sp.fetcher_for({"source": "sivers:press", "url": "https://evil.example.com/press/x"}) is None
    assert sp.fetcher_for({"source": "yahoo:iqe-l", "url": "https://feeds.finance.yahoo.com/x"}) is None   # 二手不抓

    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return "<html><body><article><p>Bulletin from the EGM</p></article></body></html>".encode()

    def opener(request, timeout=None):
        seen["ua"] = request.get_header("User-agent")
        return Resp()

    monkeypatch.setattr("fetchers.utils.rate_sleep", lambda *a, **k: None)
    assert "Bulletin from the EGM" in sp.fetch_page_text(page, opener=opener)
    assert "@" not in seen["ua"]                     # 不帶聯絡信箱


def test_raw_text_is_the_text_for_x_posts_but_never_replaces_edgar_or_ownership() -> None:
    post = {"source": "x:someone", "url": "https://x.com/a/status/1", "raw_text": "$LITE purchase obligations"}
    assert sp.fetcher_for(post)() == "$LITE purchase obligations"
    form4 = {"source": "edgar:NVDA", "raw_text": "x",
             "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/xslF345X06/form4.xml"}
    assert sp.fetcher_for(form4) is None             # 持股申報照舊是明確缺席


def test_chunk_items_groups_by_document_and_keeps_the_old_shape_without_key() -> None:
    batch = [{"lead_id": "A"}, {"lead_id": "A"}, {"lead_id": "B"}, {"lead_id": "C"}, {"lead_id": "C"}]
    assert [len(c) for c in chunk_items(batch, 2, key="lead_id")] == [3, 2]
    assert [len(c) for c in chunk_items(batch, 2)] == [2, 2, 1]


def test_ledger_has_its_own_cell_for_held_wakes() -> None:
    from datetime import date

    from engine_b import todo_ledger

    held = _reading_watch("pending", "likely_unrelated")
    rows = {r.key: r for r in todo_ledger.collect(
        today=date(2026, 10, 27), leads_store={"leads": {}}, watches=[held], todo_items=[], hypotheses=[],
        briefs=None, current_readings=None, reading_needs_reread=0, layer_note_reread=0, candidates=None,
        thesis_due=None, loaders={"classification_gaps": lambda: [], "undisposed": lambda: []})}
    assert rows["todo.wake_hold"].count == 1 and "預篩標無關 1" in rows["todo.wake_hold"].work
    assert rows["todo.semantic"].count == 0
