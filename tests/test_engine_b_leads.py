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


# --- harvest_log 誠實降級 -------------------------------------------------

def test_record_run_rejects_unknown_result() -> None:
    store = leads.empty_store()
    with pytest.raises(ValueError):
        leads.record_run(store, source="s", result="maybe", new=0)


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
    }
    assert len(store["leads"]) == 0
