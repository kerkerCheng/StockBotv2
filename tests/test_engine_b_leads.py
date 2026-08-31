"""Engine B pending-leads 狀態機、去重與 harvest 誠實降級測試（plan U1）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_b import leads
from crons import harvest_leads


# --- URL 去重 / 註冊冪等 ---------------------------------------------------

def test_register_is_idempotent_by_normalized_url() -> None:
    store = leads.empty_store()
    id1, new1 = leads.register(store, source="s", url="https://Example.com/a/")
    id2, new2 = leads.register(store, source="s", url="https://example.com/a")
    assert id1 == id2  # 正規化後同一 URL
    assert new1 is True and new2 is False
    assert len(store["leads"]) == 1


def test_reregister_does_not_clobber_status_or_triage() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/1")
    leads.triage(store, lead_id, go=True, tier=2, reason="有新角度")
    leads.advance(store, lead_id, "researching")
    # 同 URL 重複 harvest 不得倒退狀態
    again_id, is_new = leads.register(store, source="s", url="https://x.io/1")
    assert again_id == lead_id and is_new is False
    assert store["leads"][lead_id]["status"] == "researching"
    assert store["leads"][lead_id]["triage"]["decision"] == "go"


def test_reregister_enriches_full_text_and_media_without_clobbering_state() -> None:
    store = leads.empty_store()
    full = ("第一段 " + ("完整 roundup 內容 " * 20)).strip()
    short = full[:140]
    lead_id, _ = leads.register(
        store, source="x:author", url="https://x.com/author/status/1", title=short
    )
    leads.triage(store, lead_id, go=True, tier=3, reason="值得追源")

    again_id, is_new = leads.register(
        store,
        source="x:author",
        url="https://x.com/author/status/1",
        title=full,
        raw_text=full.replace(" ", "\n", 1),
        media=[{
            "media_key": "3_1",
            "type": "photo",
            "url": "https://pbs.twimg.com/media/one.jpg",
            "cache": {
                "local_path": "library/private/lead_media/lead_1/3_1.jpg",
                "sha256": "a" * 64,
                "bytes": 12,
                "content_type": "image/jpeg",
            },
        }],
    )

    lead = store["leads"][lead_id]
    assert again_id == lead_id and is_new is False
    assert lead["status"] == "triaged_go"
    assert lead["triage"]["reason"] == "值得追源"
    assert lead["title"] == full
    assert "\n" in lead["raw_text"]
    assert lead["media"][0]["cache"]["bytes"] == 12


def test_register_rejects_empty_source_and_url() -> None:
    store = leads.empty_store()
    with pytest.raises(ValueError):
        leads.register(store, source="", url="https://x.io/1")
    with pytest.raises(ValueError):
        leads.register(store, source="s", url="   ")


# --- 封閉狀態機 -----------------------------------------------------------

def test_full_forward_path() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/2")
    leads.triage(store, lead_id, go=True, tier=1, reason="tier1 filing")
    for nxt in ("researching", "action_prepared", "applied"):
        leads.advance(store, lead_id, nxt)
    assert store["leads"][lead_id]["status"] == "applied"


def test_illegal_transition_rejected() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/3")
    # pending 不能直接跳到 applied
    with pytest.raises(leads.LeadStateError):
        leads.advance(store, lead_id, "applied")


def test_applied_is_terminal_cannot_park() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/4")
    leads.triage(store, lead_id, go=True, tier=1, reason="ok")
    leads.advance(store, lead_id, "researching")
    leads.advance(store, lead_id, "action_prepared")
    leads.advance(store, lead_id, "applied")
    with pytest.raises(leads.LeadStateError):
        leads.advance(store, lead_id, "parked")


def test_park_and_unpark_clears_triage() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/5")
    leads.triage(store, lead_id, go=False, tier=4, reason="純社群猜測")
    leads.advance(store, lead_id, "parked")
    assert store["leads"][lead_id]["status"] == "parked"
    leads.advance(store, lead_id, "pending")  # un-park
    assert store["leads"][lead_id]["status"] == "pending"
    assert store["leads"][lead_id]["triage"] is None


def test_advance_unknown_lead_or_status() -> None:
    store = leads.empty_store()
    with pytest.raises(leads.LeadStateError):
        leads.advance(store, "lead_missing", "parked")
    lead_id, _ = leads.register(store, source="s", url="https://x.io/6")
    with pytest.raises(leads.LeadStateError):
        leads.advance(store, lead_id, "nonsense")


def test_annotate_refs_preserves_parked_status_and_triage() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/audio")
    leads.triage(store, lead_id, go=True, tier=3, reason="待追音訊")
    leads.advance(store, lead_id, "parked")

    lead = leads.annotate_refs(
        store,
        lead_id,
        refs={"outcome": "official_audio_obtained", "asr_timestamp": "00:08:38-00:09:10"},
    )

    assert lead["status"] == "parked"
    assert lead["triage"]["decision"] == "go"
    assert lead["refs"]["asr_timestamp"] == "00:08:38-00:09:10"


def test_annotate_refs_rejects_empty_refs_and_unknown_lead() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/audio-2")
    with pytest.raises(ValueError):
        leads.annotate_refs(store, lead_id, refs={})
    with pytest.raises(leads.LeadStateError):
        leads.annotate_refs(store, "lead_missing", refs={"outcome": "x"})


# --- triage 約束 ----------------------------------------------------------

def test_triage_requires_reason_and_valid_tier() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/7")
    with pytest.raises(ValueError):
        leads.triage(store, lead_id, go=True, tier=2, reason="  ")
    with pytest.raises(ValueError):
        leads.triage(store, lead_id, go=True, tier=9, reason="x")


def test_triage_only_from_pending() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="s", url="https://x.io/8")
    leads.triage(store, lead_id, go=True, tier=2, reason="ok")
    with pytest.raises(leads.LeadStateError):
        leads.triage(store, lead_id, go=True, tier=2, reason="再一次")


def test_related_triaged_lead_requeues_machine_linked_trace_backlog() -> None:
    store = leads.empty_store()
    parked_id, _ = leads.register(
        store,
        source="x:old",
        url="https://x.com/old/status/trace",
        title="Waiting for $AXTI primary source",
    )
    # 等待從 park 那一刻起算（[321]）：park 當下就已存在的舊 lead 不該立刻觸發重查，
    # 因為 park 的決定已經考慮過當時的資訊。故時間軸必須真實：先 park，後有新事件。
    leads.triage(
        store, parked_id, go=True, tier=4, reason="需要追原文",
        decided_at="2026-08-01T00:00:00+00:00",
    )
    leads.advance(store, parked_id, "parked", ref={
        "parked_reason": "目前只有 tier 3 轉述",
        "trace_status": "isolated_tier_3",
        "trace_next_trigger": "下一份 AXT filing 或一手文件",
        "trace_requires_user": "false",
    })
    assert store["leads"][parked_id]["refs"]["trace_trigger_kind"] == (
        "related_entity_signal"
    )

    event_id, _ = leads.register(
        store,
        source="edgar:AXTI",
        url="https://www.sec.gov/Archives/edgar/data/axt/new-filing",
        title="AXTI 8-K",
    )
    event = leads.triage(
        store,
        event_id,
        go=True,
        tier=1,
        reason="一手 filing，值得追源",
        decided_at="2026-08-02T00:00:00+00:00",
    )

    parked = store["leads"][parked_id]
    assert parked["status"] == "triaged_go"
    assert parked["refs"]["trace_requeue_trigger"] == (
        f"related_triaged_lead:{event_id}"
    )
    assert parked["refs"]["trace_trigger_event_ref"] == f"lead:{event_id}"
    assert event["triage"]["related_trace_requeues"] == [parked_id]


def test_related_signal_never_bypasses_trace_requiring_user() -> None:
    store = leads.empty_store()
    parked_id, _ = leads.register(
        store,
        source="x:old",
        url="https://x.com/old/status/paywall-axti",
        title="$AXTI paywalled report",
    )
    leads.triage(store, parked_id, go=True, tier=4, reason="需要合法 access")
    leads.advance(store, parked_id, "parked", ref={
        "parked_reason": "需使用者提供合法 access",
        "trace_status": "isolated_tier_3",
        "trace_next_trigger": "取得合法報告全文",
        "trace_requires_user": "true",
    })
    event_id, _ = leads.register(
        store,
        source="edgar:AXTI",
        url="https://www.sec.gov/Archives/edgar/data/axt/other",
    )
    leads.triage(store, event_id, go=True, tier=1, reason="新 filing")

    assert store["leads"][parked_id]["status"] == "parked"


def test_campaign_requeue_preserves_prior_triage_receipt() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/1"
    )
    leads.triage(store, lead_id, go=False, tier=4, reason="未追蹤標的")

    lead = leads.requeue_for_triage(
        store,
        lead_id,
        reason="使用者指定 robotics campaign",
        campaign_id="robotics_30d",
        requeued_at="2026-07-29T00:00:00+00:00",
    )

    assert lead["status"] == "pending" and lead["triage"] is None
    assert lead["refs"]["campaign_ids"] == ["robotics_30d"]
    assert lead["triage_history"] == [{
        "status": "triaged_no_go",
        "triage": {
            "decision": "no_go",
            "tier": 4,
            "reason": "未追蹤標的",
            "decided_at": lead["triage_history"][0]["triage"]["decided_at"],
            "priority_flags": {},
        },
        "superseded_at": "2026-07-29T00:00:00+00:00",
        "superseded_reason": "使用者指定 robotics campaign",
        "campaign_id": "robotics_30d",
    }]


def test_campaign_requeue_rejects_non_no_go() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/2"
    )
    with pytest.raises(leads.LeadStateError, match="只允許 triaged_no_go"):
        leads.requeue_for_triage(
            store, lead_id, reason="x", campaign_id="campaign"
        )


# --- harvest_log 誠實降級 -------------------------------------------------

def test_record_run_rejects_unknown_result() -> None:
    store = leads.empty_store()
    with pytest.raises(ValueError):
        leads.record_run(store, source="s", result="maybe", new=0)


def test_record_run_rejects_unknown_failure_class_and_class_on_success() -> None:
    store = leads.empty_store()
    with pytest.raises(ValueError, match="failure_class"):
        leads.record_run(
            store,
            source="s",
            result="fetch_failed",
            new=0,
            failure_class="shrug",
        )
    with pytest.raises(ValueError, match="successful"):
        leads.record_run(
            store,
            source="s",
            result="ok",
            new=0,
            failure_class="access_blocked",
        )


def test_unresolved_harvest_failures_clear_only_after_same_source_recovers() -> None:
    store = leads.empty_store()
    leads.record_run(
        store,
        source="edgar:AXTI",
        result="fetch_failed",
        new=0,
        failure_class="access_blocked",
    )
    leads.record_run(
        store,
        source="customer_ir:casela",
        result="fetch_failed",
        new=0,
        failure_class="tls_failure",
    )
    assert {
        item["source"]: item["failure_class"]
        for item in leads.unresolved_harvest_failures(store)
    } == {
        "customer_ir:casela": "tls_failure",
        "edgar:AXTI": "access_blocked",
    }

    leads.record_run(store, source="edgar:AXTI", result="ok", new=1)

    unresolved = leads.unresolved_harvest_failures(store)
    assert [item["source"] for item in unresolved] == ["customer_ir:casela"]


def test_parse_failed_is_logged_not_silently_empty() -> None:
    store = leads.empty_store()
    with pytest.raises(harvest_leads.HarvestParseError):
        harvest_leads.parse_rss(b"<not valid xml", "aleabitoreddit_rss")
    # 呼叫端要把它記成 parse_failed，而不是當成 0 新文
    leads.record_run(store, source="aleabitoreddit_rss", result="parse_failed", new=0)
    log = store["harvest_log"]
    assert log[-1]["result"] == "parse_failed"


# --- RSS / Atom 解析 ------------------------------------------------------

def test_parse_rss_extracts_items() -> None:
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>Serenity</title>
      <item><title>InP capacity note</title>
        <link>https://aleabitoreddit.substack.com/p/inp-1</link>
        <pubDate>Tue, 21 Jul 2026 08:00:00 GMT</pubDate></item>
      <item><title>Second post</title>
        <link>https://aleabitoreddit.substack.com/p/post-2</link></item>
    </channel></rss>"""
    items = harvest_leads.parse_rss(xml, "aleabitoreddit_rss")
    assert len(items) == 2
    assert items[0]["url"].endswith("/inp-1")
    assert items[0]["published_at"].startswith("Tue")
    assert items[1]["published_at"] is None


def test_parse_atom_uses_link_href() -> None:
    xml = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Atom item</title>
        <link href="https://example.com/atom-1"/>
        <updated>2026-07-21T00:00:00Z</updated></entry>
    </feed>"""
    items = harvest_leads.parse_rss(xml, "some_atom")
    assert items == [
        {"url": "https://example.com/atom-1", "title": "Atom item",
         "published_at": "2026-07-21T00:00:00Z"}
    ]


# --- EDGAR 純轉換 ---------------------------------------------------------

def test_filings_to_leads_builds_stable_urls() -> None:
    filings = [
        {"accession": "000082031826000013", "primary_doc": "iivi-20260331.htm",
         "form_type": "10-Q", "filed_date": "2026-05-06"},
    ]
    out = harvest_leads.filings_to_leads("COHR", "0000820318", filings)
    assert out[0]["source"] == "edgar:COHR"
    assert out[0]["url"] == (
        "https://www.sec.gov/Archives/edgar/data/820318/"
        "000082031826000013/iivi-20260331.htm"
    )
    assert "10-Q filed 2026-05-06" in out[0]["title"]


# --- config fail closed ---------------------------------------------------

def test_load_config_fail_closed_on_missing_fields(tmp_path: Path) -> None:
    bad = tmp_path / "cfg.json"
    bad.write_text(json.dumps({"feeds": [{"source": "x"}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        harvest_leads.load_config(bad)
    bad.write_text(json.dumps({"edgar_watch": {"tickers": "COHR"}}), encoding="utf-8")
    with pytest.raises(ValueError):
        harvest_leads.load_config(bad)


def test_load_config_accepts_repo_default() -> None:
    cfg = harvest_leads.load_config()  # repo 內 crons/harvest_config.json
    assert isinstance(cfg["feeds"], list)  # 2026-07-25 起為空（substack 已由 X 取代）
    assert "aleabitoreddit" in cfg["x_accounts"]["handles"]
    assert "COHR" in cfg["edgar_watch"]["tickers"]


# --- atomic 寫檔 round-trip ----------------------------------------------

def test_save_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "pending_leads.json"
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="edgar:COHR",
                                url="https://x.io/9", title="t")
    leads.triage(store, lead_id, go=True, tier=1, reason="ok")
    leads.save(store, path)
    assert path.exists()
    reloaded = leads.load(path)
    assert reloaded["leads"][lead_id]["status"] == "triaged_go"
    assert reloaded["schema_version"] == leads.SCHEMA_VERSION


def test_load_missing_returns_empty_skeleton(tmp_path: Path) -> None:
    store = leads.load(tmp_path / "nope.json")
    assert store == leads.empty_store()


def test_load_lazily_migrates_v1_store_to_v2(tmp_path: Path) -> None:
    path = tmp_path / "pending_leads.json"
    path.write_text(
        json.dumps({"schema_version": "1", "leads": {}, "harvest_log": []}),
        encoding="utf-8",
    )
    assert leads.load(path)["schema_version"] == "2"


def test_status_counts(tmp_path: Path) -> None:
    store = leads.empty_store()
    a, _ = leads.register(store, source="s", url="https://x.io/a")
    b, _ = leads.register(store, source="s", url="https://x.io/b")
    leads.register(store, source="s", url="https://x.io/c")
    leads.triage(store, a, go=True, tier=2, reason="ok")
    leads.triage(store, b, go=False, tier=4, reason="no")
    counts = leads.status_counts(store)
    assert counts == {"triaged_go": 1, "triaged_no_go": 1, "pending": 1}


# --- harvest run 端到端（無網路，注入 items）-----------------------------

def test_run_records_fetch_failed_for_unreachable_feed(monkeypatch) -> None:
    store = leads.empty_store()
    config = {"feeds": [{"source": "dead_feed", "url": "https://0.0.0.0/none"}],
              "edgar_watch": {}}

    def boom(url, **kw):
        raise OSError("no route")

    monkeypatch.setattr(harvest_leads, "fetch_url", boom)
    harvest_leads.run(config, store)
    assert store["harvest_log"][-1] == {
        **store["harvest_log"][-1],
        "source": "dead_feed",
        "result": "fetch_failed",
        "new": 0,
        "failure_class": "transport_failure",
    }
    assert len(store["leads"]) == 0


def test_requeue_consumed_marker_stops_same_entity_waking_lead_repeatedly() -> None:
    """2026-08-12 迴歸：同一個標的重複觸發，會把 pq1 預算耗在必然無產出的重查上。

    park 的理由（缺某份特定文件、內容不屬圖譜材料）不會因為「又一則提到同一檔的
    貼文」而改變，因此第二次以後的同標的觸發必須被擋下；新標的仍應正常喚醒。
    """
    store = leads.empty_store()
    parked_id, _ = leads.register(
        store,
        source="x:old",
        url="https://x.com/old/status/macro",
        title="$AXTI and $LITE macro roundup",
    )
    # 等待從 park 那一刻起算（[321]）：park 當下就已存在的舊 lead 不該立刻觸發重查，
    # 因為 park 的決定已經考慮過當時的資訊。故時間軸必須真實：先 park，後有新事件。
    leads.triage(
        store, parked_id, go=True, tier=4, reason="需要追原文",
        decided_at="2026-08-01T00:00:00+00:00",
    )
    leads.advance(store, parked_id, "parked", ref={
        "parked_reason": "只有 tier 3 轉述",
        "trace_status": "isolated_tier_3",
        "trace_next_trigger": "取得券商報告原文",
        "trace_requires_user": "false",
    })

    def _fire(source: str, url: str, title: str, at: str) -> None:
        lead_id, _ = leads.register(store, source=source, url=url, title=title)
        leads.triage(store, lead_id, go=True, tier=1, reason="一手 filing", decided_at=at)

    # 第一次 AXTI 觸發 → 喚醒
    _fire("edgar:AXTI", "https://sec.gov/axt/1", "AXTI 8-K", "2026-08-02T00:00:00+00:00")
    assert store["leads"][parked_id]["status"] == "triaged_go"
    # [321]：消化標記住在 Event Watch，不再於 lead refs 留第二份——
    # 兩份會偏離，而偏離不會報錯（L16）。
    from engine_b import event_watch as ew

    watch = next(
        w for w in ew.load_watches()["watches"] if w.get("wake_lead") == parked_id
    )
    assert "AXTI" in watch["consumed_entities"]

    # 重新 park 後，同一個 AXTI 再來一次 → 不得再喚醒
    leads.advance(store, parked_id, "parked", ref={
        "parked_reason": "重查後仍無新事證",
        "trace_status": "isolated_tier_3",
        "trace_next_trigger": "取得券商報告原文",
        "trace_requires_user": "false",
    })
    _fire("edgar:AXTI", "https://sec.gov/axt/2", "AXTI 8-K 第二份", "2026-08-03T00:00:00+00:00")
    assert store["leads"][parked_id]["status"] == "parked", (
        "同一標的的第二次觸發不應再喚醒已重查過的 parked lead"
    )

    # 但**新**標的（LITE）仍應喚醒
    _fire("edgar:LITE", "https://sec.gov/lite/1", "LITE 8-K", "2026-08-04T00:00:00+00:00")
    assert store["leads"][parked_id]["status"] == "triaged_go", (
        "尚未消化過的新標的仍必須能觸發重查"
    )


def test_primary_source_signal_only_wakes_on_tier1_documents() -> None:
    """B 類等待條件：等某方未來的具名一手揭露，不是「該實體被提到」。

    用 related_entity_signal 表達時，任何一則提到該公司的推文都會觸發重查，於是每次
    都得到「trigger 沒帶來新東西」（2026-08-12 實測，5 個 pq1 slot 全被這類重排吃光）。
    """
    store = leads.empty_store()
    parked_id, _ = leads.register(
        store,
        source="x:old",
        url="https://x.com/old/status/memo",
        title="$META internal memo 轉述",
    )
    leads.triage(
        store, parked_id, go=True, tier=4, reason="需要 memo 原文",
        decided_at="2026-08-01T00:00:00+00:00",
    )
    leads.advance(store, parked_id, "parked", ref={
        "parked_reason": "只有二手轉述，未見 memo 原文",
        "trace_status": "partial",
        "trace_next_trigger": "Meta 一手揭露",
        "trace_requires_user": "false",
        "trace_trigger_kind": "primary_source_signal",
        "trace_trigger_entities": ["META"],
    })

    def _fire(source: str, url: str, title: str, tier: int, at: str) -> None:
        lead_id, _ = leads.register(store, source=source, url=url, title=title)
        leads.triage(store, lead_id, go=True, tier=tier, reason="r", decided_at=at)

    # 又一則提到 $META 的推文（tier 4）→ 不得觸發
    _fire("x:someone", "https://x.com/a/1", "$META 又有新聞", 4, "2026-08-02T00:00:00+00:00")
    assert store["leads"][parked_id]["status"] == "parked", (
        "primary_source_signal 不應被二手轉述觸發"
    )

    # Meta 的 tier-1 一手 filing → 必須觸發
    _fire("edgar:META", "https://sec.gov/meta/10q", "META 10-Q", 1, "2026-08-03T00:00:00+00:00")
    assert store["leads"][parked_id]["status"] == "triaged_go"
    refs = store["leads"][parked_id]["refs"]
    assert refs["trace_trigger_kind"] == "primary_source_signal", (
        "kind 不得被覆寫回 related_entity_signal，否則限縮只生效一次"
    )
    # 一手來源不以標的消化：下一季的 filing 可能正好含有等待中的揭露
    assert "trace_requeue_consumed_entities" not in refs

    leads.advance(store, parked_id, "parked", ref={
        "parked_reason": "該季 filing 未含 memo 內容",
        "trace_status": "partial",
        "trace_requires_user": "false",
    })
    _fire("edgar:META", "https://sec.gov/meta/10k", "META 10-K", 1, "2026-08-04T00:00:00+00:00")
    assert store["leads"][parked_id]["status"] == "triaged_go", (
        "同一實體的**下一份**一手文件仍必須觸發"
    )


def test_trace_backlog_flags_entries_no_trigger_can_ever_reach() -> None:
    """2026-08-13：既不需人工 authority、又沒有具名標的的 parked lead 已經死了。

    兩種 trace_trigger_kind 都靠具名標的比對；沒有標的就永遠不會命中，而它看起來
    仍在「等事件」。標出來才不會變成安靜沉底的黑洞（同 §10.11 的「有入口沒出口」）。
    """
    store = leads.empty_store()

    def _park(url: str, title: str, ref: dict) -> str:
        lead_id, _ = leads.register(store, source="x:t", url=url, title=title)
        leads.triage(store, lead_id, go=True, tier=4, reason="r")
        leads.advance(store, lead_id, "parked", ref=ref)
        return lead_id

    base = {
        "parked_reason": "trace 未果",
        "trace_status": "isolated_tier_3",
        "trace_requires_user": "false",
    }
    # 有具名標的 → 可觸發
    reachable = _park(
        "https://x.com/a/1", "$AXTI 相關轉述",
        base | {"trace_next_trigger": "AXT 一手揭露"},
    )
    # 無標的、也不需人工 authority → 永遠不會命中
    unreachable = _park(
        "https://x.com/a/2", "某份政府報告的轉述（無具名公司）",
        base | {"trace_next_trigger": "canonical_dhs_committee_report"},
    )
    # 無標的但需人工 authority → 走 pq2，本來就不靠自動觸發
    manual = _park(
        "https://x.com/a/3", "付費報告轉述（無具名公司）",
        base | {"trace_next_trigger": "取得報告原文", "trace_requires_user": "true"},
    )

    rows = {row["lead_id"]: row for row in leads.trace_backlog(store)}
    # [321]：等待狀態由 Event Watch registry 回答。有具名標的的在 park 當下
    # 就自動建 watch，因此是 watching（且拿到到期日）。
    assert rows[reachable]["wake_state"] == "watching"
    assert rows[reachable]["auto_trigger_reachable"] is True
    assert rows[reachable]["unreachable_reason"] is None
    assert rows[reachable]["expires"], "watch 必須帶到期日，無限期等待會腐爛成事實"

    # 無具名標的 → 建不出觸發條件，是唯一真正的黑洞，必須現形。
    assert rows[unreachable]["wake_state"] == "unwatched"
    assert rows[unreachable]["auto_trigger_reachable"] is False
    assert "沒有對應的 Event Watch" in rows[unreachable]["unreachable_reason"]

    assert rows[manual]["wake_state"] == "pq2_manual"
    assert rows[manual]["auto_trigger_reachable"] is True, (
        "requires_user 走 pq2 人工授權，不該被標成不可達"
    )
