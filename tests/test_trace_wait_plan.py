"""停放的等待跟著觸發條件走（2026-10-08，Phase 7 failure log #1、#2、#15；plan 2026-10-08-001 D1）。

#1：停放時 watch 等的是「lead 提到的所有公司」、任何提及就醒——10-04～07 被排回的 11 次裡 9 次跟原研究無關。
#15：終局 trace status（`original_obtained` 等）一律不建 watch，於是「拿到原文、但研究在等未來事件」的停放沒人在等
     （CCXI S-4 那則等的東西出現了 31 天沒接回）。
#2：被排回的 lead 重新停放時，同名 ref 把前次結論蓋掉（10-04 三條靠備份 zip 復原）。
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from engine_b import event_watch as ew
from engine_b import leads
from engine_b.entities import lead_subject, trigger_entities


def _lead(store: dict, *, source: str, url: str, title: str, tier: int = 4, at: str,
          company_id: str | None = None, form_type: str | None = None, published_at: str | None = None) -> str:
    lead_id, _ = leads.register(store, source=source, url=url, title=title)
    lead = store["leads"][lead_id]
    if company_id:
        lead["company_id"] = company_id
    if form_type:
        lead["form_type"] = form_type
    if published_at:
        lead["published_at"] = published_at
    leads.triage(store, lead_id, go=True, tier=tier, reason="r", decided_at=at)
    return lead_id


def _watch_for(lead_id: str) -> dict:
    return next(w for w in ew.load_watches()["watches"]
                if w.get("wake_lead") == lead_id and w.get("status") in ("active", "fired"))


# --- 觸發條件點名到誰 -----------------------------------------------------------

def test_trigger_entities_reads_names_cashtags_and_strict_plain_tickers() -> None:
    assert "co:axt" in trigger_entities("AXT 下一份 8-K（Item 2.02）")             # 名冊的名字
    assert "co:applied_optoelectronics" in trigger_entities("AAOI 第三季 10-Q 的 ATM 段")  # 不帶 $ 的已登記代號
    assert "co:lumentum" in trigger_entities("等 $LITE 的 10-Q")                     # cashtag
    assert "co:poet_technologies" in trigger_entities("no_retry_unless_POET_names_laser_company")  # 底線算分隔
    # 去後綴的猜法不用在觸發條件：「SOI 晶圓」不是 Soitec
    assert "co:soitec" not in trigger_entities("SOI 晶圓的供應商名單")
    assert trigger_entities("取得券商報告原文") == ()


def test_lead_subject_is_declared_publisher_or_the_single_company() -> None:
    assert lead_subject({"company_id": "co:axt", "entities": {"tickers": ["NVDA"], "company_ids": ["co:nvidia"]}}) == ("co:axt",)
    assert lead_subject({"entities": {"tickers": ["AAOI"], "company_ids": ["co:applied_optoelectronics"]}}) == (
        "co:applied_optoelectronics",)
    two = {"entities": {"tickers": ["AAOI", "LITE"], "company_ids": ["co:applied_optoelectronics", "co:lumentum"]}}
    assert lead_subject(two) == ()     # 兩家以上不猜（INV-1）


@pytest.mark.parametrize("trigger, kind", [
    ("無；官方 Form 4 已取得，按內部人交易彙總觀測處理", "none"),
    ("no_retry_opinion_only", "none"),
    ("none_dated_observation", "none"),
    ("terminal_original_does_not_support_aaoi", "none"),
    ("no_retry_unless_named_customer_or_supply_relationship_disclosed", "date"),   # 有條件的等，不是不等
    ("無線模組廠的下一份年報", "date"),                                            # 「無」只認開頭＋標點
])
def test_no_wait_convention_is_parsed_once_into_a_structured_kind(trigger: str, kind: str) -> None:
    out = leads.default_trace_trigger({"title": "t"}, trigger, trace_status="original_obtained")
    assert out["trace_trigger_kind"] == kind


def test_terminal_trace_waits_only_on_named_companies_non_terminal_adds_the_publisher() -> None:
    lead = {"company_id": "co:sivers_semiconductors", "title": "Sivers 公告"}
    generic = "同標的後續出現具名客戶／供應協議、產能執行證據或財報結構性揭露"
    # 終局＋沒點名 → 不把發文公司當標的（否則它的每一份申報都會叫醒一次），等日子
    assert leads.default_trace_trigger(lead, generic, trace_status="original_obtained") == {
        "trace_trigger_kind": "date", "trace_trigger_entities": []}
    # 追源還沒結束 → 主詞就是發文公司
    assert leads.default_trace_trigger(lead, generic, trace_status="partial") == {
        "trace_trigger_kind": "entity_filing_signal", "trace_trigger_entities": ["co:sivers_semiconductors"]}


# --- #1：只等點名的公司的一手 ----------------------------------------------------

def test_a_tweet_listing_many_cashtags_waits_only_for_the_company_its_trigger_names() -> None:
    """lead_26bd4214 的形狀：一則 TLDR 推文 27 個 cashtag，觸發條件是「AXT 下一份 8-K」。"""
    store = leads.empty_store()
    parked = _lead(store, source="x:tldr", url="https://x.com/t/1",
                   title="TLDR: $GOOGL $AMD $NVDA $MRVL $MU $AXTI news", at="2026-08-01T00:00:00+00:00")
    leads.advance(store, parked, "parked", ref={
        "parked_reason": "只有轉述", "trace_status": "not_pursued", "trace_requires_user": "false",
        "trace_next_trigger": "AXT 下一份 8-K（Item 2.02）揭露 InP 出口許可狀態"})
    watch = _watch_for(parked)
    assert (watch["kind"], watch["entities"]) == ("entity_filing_signal", ["co:axt"])

    _lead(store, source="edgar:MU", url="https://sec.gov/mu/8k", title="MU 8-K", tier=1,
          at="2026-08-02T00:00:00+00:00", company_id="co:micron_technology", form_type="8-K")
    _lead(store, source="x:other", url="https://x.com/t/2", title="$AXTI $NVDA 又一則推文",
          at="2026-08-03T00:00:00+00:00")
    assert store["leads"][parked]["status"] == "parked", "別家的申報、提到 AXT 的推文都不是它在等的"
    _lead(store, source="edgar:AXTI", url="https://sec.gov/axti/8k", title="AXTI 8-K", tier=1,
          at="2026-08-04T00:00:00+00:00", company_id="co:axt", form_type="8-K")
    assert store["leads"][parked]["status"] == "triaged_go", "AXT 自己的一手申報必須叫醒它"


def test_ownership_filings_and_backfilled_documents_do_not_wake_filing_watches() -> None:
    store = leads.empty_store()
    parked = _lead(store, source="x:a", url="https://x.com/a/1", title="$AXTI 轉述", at="2026-08-01T00:00:00+00:00")
    leads.advance(store, parked, "parked", ref={
        "parked_reason": "只有轉述", "trace_status": "partial", "trace_requires_user": "false",
        "trace_next_trigger": "AXT 下一份 10-Q"})
    _lead(store, source="edgar:AXTI", url="https://sec.gov/axti/f4", title="AXTI 4 filed", tier=1,
          at="2026-08-02T00:00:00+00:00", company_id="co:axt", form_type="4")
    assert store["leads"][parked]["status"] == "parked", "Form 4 不是「某實體的正式文件」在等的那種"
    _lead(store, source="edgar:AXTI", url="https://sec.gov/axti/old10q", title="AXTI 10-Q（回補）", tier=1,
          at="2026-08-03T00:00:00+00:00", company_id="co:axt", form_type="10-Q", published_at="2026-05-01")
    assert store["leads"][parked]["status"] == "parked", "回補的舊文件不是新事件"
    _lead(store, source="edgar:AXTI", url="https://sec.gov/axti/10q", title="AXTI 10-Q", tier=1,
          at="2026-08-04T00:00:00+00:00", company_id="co:axt", form_type="10-Q", published_at="2026-08-04")
    assert store["leads"][parked]["status"] == "triaged_go"


# --- #15：終局但寫了觸發條件的也在等 ---------------------------------------------

def test_terminal_park_with_a_named_trigger_gets_a_watch() -> None:
    """lead_6e6000e1 的形狀：拿到原文（original_obtained）但在等 CCXI 遞交 S-4。"""
    store = leads.empty_store()
    parked = _lead(store, source="x:a", url="https://x.com/a/ccxi", title="$XPEV $NVDA 談 Agility 估值",
                   at="2026-08-01T00:00:00+00:00")
    leads.advance(store, parked, "parked", ref={
        "parked_reason": "原文已取得；Agility 財報要等 S-4", "trace_status": "original_obtained",
        "trace_requires_user": "false",
        "trace_next_trigger": "AXT 遞交 S-4 或 S-4/A 並生效，屆時首次揭露歷史財報"})
    watch = _watch_for(parked)
    assert watch["kind"] == "entity_filing_signal" and "co:axt" in watch["entities"]
    assert leads.parked_without_expiry(store) == []


def test_terminal_without_a_trigger_and_explicit_no_wait_are_not_holes() -> None:
    store = leads.empty_store()
    done = _lead(store, source="x:a", url="https://x.com/a/2", title="t", at="2026-08-01T00:00:00+00:00")
    leads.advance(store, done, "parked", ref={"parked_reason": "原文已取得", "trace_status": "original_obtained"})
    none = _lead(store, source="x:a", url="https://x.com/a/3", title="t", at="2026-08-01T00:00:00+00:00")
    leads.advance(store, none, "parked", ref={"parked_reason": "原文已取得", "trace_status": "original_obtained",
                                              "trace_next_trigger": "無；只是治理公告"})
    assert store["leads"][none]["refs"]["trace_trigger_kind"] == "none"
    assert not [w for w in ew.load_watches()["watches"] if w.get("wake_lead") in (done, none)]
    assert leads.parked_without_expiry(store) == []


def test_an_ownership_filing_lead_never_gets_a_watch() -> None:
    """持股申報等的是下一份持股申報，而持股申報刻意不叫醒任何 watch——建了也醒不了。"""
    store = leads.empty_store()
    form4 = _lead(store, source="edgar:NVDA", url="https://sec.gov/nvda/f4", title="NVDA 4 filed", tier=1,
                  at="2026-08-01T00:00:00+00:00", company_id="co:nvidia", form_type="4")
    leads.advance(store, form4, "parked", ref={
        "parked_reason": "官方 Form 4", "trace_status": "original_obtained",
        "trace_next_trigger": "後續 Form 4 出現公開市場買入、10% owner 申報或非例行集中買賣"})
    assert not [w for w in ew.load_watches()["watches"] if w.get("wake_lead") == form4]
    assert leads.trace_wait_plan(store["leads"][form4]) is None


def test_date_watch_requeues_once_then_is_consumed_not_reactivated() -> None:
    """日期型等的是那一天：叫醒過就完成（回 active 會每輪再醒）；再停放時建下一輪。"""
    due = ew._today() + timedelta(days=30)
    store = leads.empty_store()
    parked = _lead(store, source="x:a", url="https://x.com/a/gov", title="某份政府報告的轉述",
                   at="2026-08-01T00:00:00+00:00")
    leads.advance(store, parked, "parked", ref={
        "parked_reason": "等報告", "trace_status": "partial", "trace_requires_user": "false",
        "trace_next_trigger": f"國家實驗室 {due.isoformat()} 前發布正式報告"})
    watch = _watch_for(parked)
    assert (watch["kind"], watch["until"]) == ("date", due.isoformat())    # 觸發條件寫的日子

    data = ew.load_watches()
    assert ew.check_watches(data, leads=store["leads"], today=due - timedelta(days=1)) == []
    fired = ew.check_watches(data, leads=store["leads"], today=due)
    assert [f["wake_lead"] for f in fired] == [parked]
    result = leads.consume_fired_lead_watches(store, data)
    assert result["requeued"] == [parked] and store["leads"][parked]["status"] == "triaged_go"
    assert next(w for w in data["watches"] if w["watch_id"] == watch["watch_id"])["status"] == "consumed"
    assert ew.check_watches(data, leads=store["leads"], today=due + timedelta(days=1)) == []


def test_trace_date_until_uses_the_first_future_date_else_ttl() -> None:
    today = date(2026, 10, 8)
    assert ew.trace_date_until("約 2026-11-09 送件；2027-03-31 前完成", today=today, ttl=120) == date(2026, 11, 9)
    assert ew.trace_date_until("2026-09-24 法說", today=today, ttl=120) == today + timedelta(days=120)


# --- #2：前次結論不被蓋掉 ---------------------------------------------------------

def test_re_park_after_requeue_must_say_it_replaces_the_previous_trace_status() -> None:
    store = leads.empty_store()
    lead_id = _lead(store, source="x:a", url="https://x.com/a/9", title="$AXTI 轉述", at="2026-08-01T00:00:00+00:00")
    leads.advance(store, lead_id, "parked", ref={
        "parked_reason": "等 AXT 點名客戶", "trace_status": "awaiting_named_disclosure",
        "trace_next_trigger": "AXT 10-Q 點名客戶"})
    leads.requeue_trace(store, lead_id, trigger="event_watch:ew_x", reason="r", requeued_at="2026-08-05T00:00:00+00:00")
    leads.advance(store, lead_id, "researching")
    with pytest.raises(leads.LeadStateError, match="replace-trace-status"):
        leads.advance(store, lead_id, "parked", ref={"trace_status": "partial", "parked_reason": "重查"})
    assert store["leads"][lead_id]["status"] == "researching"

    leads.advance(store, lead_id, "parked", ref={"trace_status": "partial", "parked_reason": "重查：只拿到一半"},
                  replace_trace_status=True)
    history = store["leads"][lead_id]["trace_history"]
    assert history[-1]["trace_status"] == "awaiting_named_disclosure"
    assert history[-1]["parked_reason"] == "等 AXT 點名客戶"
    # 同一個結論重新停放不必明示
    leads.requeue_trace(store, lead_id, trigger="event_watch:ew_y", reason="r", requeued_at="2026-08-09T00:00:00+00:00")
    leads.advance(store, lead_id, "researching")
    leads.advance(store, lead_id, "parked", ref={"trace_status": "partial", "parked_reason": "還是一半"})


def test_annotate_keeps_the_overwritten_conclusion() -> None:
    store = leads.empty_store()
    lead_id = _lead(store, source="x:a", url="https://x.com/a/10", title="t", at="2026-08-01T00:00:00+00:00")
    leads.annotate_refs(store, lead_id, refs={"parked_reason": "第一版"})
    leads.annotate_refs(store, lead_id, refs={"parked_reason": "第二版"})
    assert store["leads"][lead_id]["trace_history"][-1]["parked_reason"] == "第一版"


def test_drain_shows_the_previous_conclusion_of_a_requeued_lead() -> None:
    from engine_b.cli import _previous_conclusion

    store = leads.empty_store()
    lead_id = _lead(store, source="x:a", url="https://x.com/a/11", title="t", at="2026-08-01T00:00:00+00:00")
    assert _previous_conclusion(store["leads"][lead_id]) is None
    leads.advance(store, lead_id, "parked", ref={"parked_reason": "等 AXT 點名客戶", "trace_status": "partial",
                                                 "trace_next_trigger": "AXT 10-Q"})
    leads.requeue_trace(store, lead_id, trigger="event_watch:ew_x", reason="r", requeued_at="2026-08-05T00:00:00+00:00")
    line = _previous_conclusion(store["leads"][lead_id])
    assert "partial" in line and "等 AXT 點名客戶" in line


# --- 存量對齊 ---------------------------------------------------------------------

def test_sync_aligns_existing_parks_from_now_without_backfilling_wakes() -> None:
    """存量：舊預設寫的寬條件改成觸發條件點名的公司；沒有 watch 的終局停放補建；新條件從現在起算，不把舊申報當新事件。"""
    store = leads.empty_store()
    old = _lead(store, source="x:a", url="https://x.com/a/20", title="$AXTI $NVDA $MU 轉述", at="2026-08-01T00:00:00+00:00")
    terminal = _lead(store, source="x:a", url="https://x.com/a/21", title="$LITE 轉述", at="2026-08-01T00:00:00+00:00")
    for lead_id, status, trigger in ((old, "partial", "AXT 下一份 10-Q"),
                                     (terminal, "original_obtained", "Lumentum 下一份 10-Q 點名客戶")):
        lead = store["leads"][lead_id]
        lead["status"] = "parked"
        lead["refs"].update({"trace_status": status, "trace_next_trigger": trigger})
    # 舊預設寫進 refs 的寬條件
    store["leads"][old]["refs"].update({"trace_trigger_kind": "related_entity_signal",
                                        "trace_trigger_entities": ["AXTI", "MU", "NVDA"]})
    data = ew.load_watches()
    ew.add_watch(data, kind="related_entity_signal", wake_lead=old, expires="2026-12-01",
                 entities=["AXTI", "NVDA", "MU"], created_at="2026-08-01T00:00:00+00:00")
    _lead(store, source="edgar:LITE", url="https://sec.gov/lite/8k", title="LITE 8-K", tier=1,
          at="2026-08-10T00:00:00+00:00", company_id="co:lumentum", form_type="8-K")
    assert {row["lead_id"] for row in _holes(store, data)} == {terminal}

    result = leads.sync_trace_watches(store, data)
    assert result["retargeted"] == [old] and result["created_entity"] == [terminal]
    assert {w["wake_lead"]: (w["kind"], w["entities"]) for w in data["watches"]} == {
        old: ("entity_filing_signal", ["co:axt"]), terminal: ("entity_filing_signal", ["co:lumentum"])}
    assert store["leads"][old]["trace_history"][-1]["trace_trigger_entities"] == ["AXTI", "MU", "NVDA"]
    assert next(w for w in data["watches"] if w["wake_lead"] == old)["retargets"][-1]["from_entities"] == [
        "AXTI", "MU", "NVDA"]
    assert ew.check_watches(data, leads=store["leads"]) == [], "08-10 的 LITE 8-K 不是對齊之後的新事件"
    assert _holes(store, data) == []
    again = leads.sync_trace_watches(store, data)
    assert again["counts"]["unchanged"] == 2 and not again["created_entity"] and not again["retargeted"]


def _holes(store: dict, data: dict) -> list[dict]:
    original = ew.load_watches
    ew.load_watches = lambda path=None: data   # noqa: E731 — parked_without_expiry 讀 registry
    try:
        return leads.parked_without_expiry(store)
    finally:
        ew.load_watches = original


def test_a_round_that_expired_is_not_resurrected_by_sync() -> None:
    """A3（2026-09-24 定案）：等滿一輪還沒出現就結案、不無聲續等——終局寫了觸發條件的也一樣；再停放才是新的一輪。"""
    store = leads.empty_store()
    lead_id = _lead(store, source="x:a", url="https://x.com/a/30", title="$LITE 轉述", at="2026-08-01T00:00:00+00:00")
    leads.advance(store, lead_id, "parked", ref={"parked_reason": "原文已取得", "trace_status": "original_obtained",
                                                 "trace_next_trigger": "Lumentum 下一份 10-Q 點名客戶"})
    data = ew.load_watches()
    _watch = next(w for w in data["watches"] if w["wake_lead"] == lead_id)
    _watch["expires"] = "2026-01-01"
    ew.mark_expired(data)
    assert leads.close_expired_trace_watches(store, data)[0]["outcome"] == "lead_already_terminal"
    assert store["leads"][lead_id]["refs"]["trace_status"] == "original_obtained"      # 終局不覆寫
    assert store["leads"][lead_id]["refs"]["trace_trigger_kind"] == "none"
    assert _holes(store, data) == []
    result = leads.sync_trace_watches(store, data)
    assert result["counts"]["created_entity"] == 0 and lead_id in result["round_over"]
    # 再停放＝新的一輪
    leads.requeue_trace(store, lead_id, trigger="user_requested", reason="r", requeued_at="2026-10-01T00:00:00+00:00")
    leads.advance(store, lead_id, "researching")
    leads.advance(store, lead_id, "parked", ref={"parked_reason": "還在等"})
    assert _watch_for(lead_id)["kind"] == "entity_filing_signal"


def test_re_park_never_rewrites_a_fact_verification_watch_hung_on_the_lead() -> None:
    """ew_0068／ew_0069 的形狀：假說查核掛在 lead 上，等的是一個具體事實——停放重算觸發條件不得把它改成等申報（R1）。"""
    store = leads.empty_store()
    lead_id = _lead(store, source="x:a", url="https://x.com/a/40", title="$THK 轉述", at="2026-08-01T00:00:00+00:00")
    leads.advance(store, lead_id, "parked", ref={"parked_reason": "等事實", "trace_status": "partial"})
    data = ew.load_watches()
    ew.add_watch(data, kind="fact_verification", wake_lead=lead_id, expires="2027-01-01", entities=["THK"],
                 fact="THK 是否有 humanoid roller screw 具名客戶")
    ew.save_watches(data)
    leads.requeue_trace(store, lead_id, trigger="event_watch:ew_x", reason="r", requeued_at="2026-08-05T00:00:00+00:00")
    leads.advance(store, lead_id, "researching")
    leads.advance(store, lead_id, "parked", ref={"parked_reason": "還在等", "trace_next_trigger": "AXT 下一份 10-Q"})
    watch = _watch_for(lead_id)
    assert watch["kind"] == "fact_verification" and watch["entities"] == ["THK"] and not watch.get("retargets")
