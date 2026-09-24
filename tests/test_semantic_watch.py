"""語意條件 watch（`semantic_condition`）與語意預篩（Phase 1 Step 1.4；G7、C2、C7）。

守的機制：
- 「kind × 喚醒目標」每一組都有平行消費端的條目，不落到「未知」或預設「假設」（2026-09-02 事故的守門）。
- 語意型 T0 只認 lead 的**來源宣告**（primary、不是持股申報、實體交集、時間在建立之後），**不看 triage**；
  其他 kind 的判準不變。`published_at` 的 ISO 與 RFC 822 都要解析，解析不到只用 first_seen 並計數。
- 登記的驗證：L7 三件套、至少一個 registry 解析得到的 co:*、到期不早於條件寫的日期。
- 判定只在互動（judge）；預篩只標旗、不改狀態，名額每日、沒有 fetcher 的不佔名額、引文必須原文逐字。
- 來源宣告寫成 lead 頂層欄位：經過 register 補強與 backfill_entities(rescan) 之後仍叫得醒（N-a）。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from engine_b import event_watch as ew
from engine_b import leads as leads_mod
from engine_b import semantic_prescreen as sp

SIVERS = "co:sivers_semiconductors"
COND = "Sivers 期中或年報揭露 CW DFB laser array 進入量產，或客戶在正式文件具名（2027-03-31 前）"


def _fresh():
    return {"schema_version": 1, "watches": []}


def _semantic(data, **over):
    kwargs = dict(kind=ew.SEMANTIC_KIND, disproof_ref="thesis:thesis/sivers_v4_lane_memo.md#1",
                  source_ref="thesis:thesis/sivers_v4_lane_memo.md#1", expires="2027-06-30",
                  entities=[SIVERS, "SIVE.ST"], condition=COND, check_frequency="每季財報後",
                  action_48h="重讀 thesis 並決定是否 revise", today=date(2026, 9, 24))
    kwargs.update(over)
    watch = ew.add_watch(data, **kwargs)
    watch["created_at"] = "2026-09-24T00:00:00+00:00"
    return watch


def _lead(**over):
    lead = {"source": "mfn:sivers-semiconductors", "source_class": "primary", "company_id": SIVERS,
            "first_seen": "2026-09-25T06:00:00+00:00", "published_at": "Thu, 25 Sep 2026 05:00:00 +0000",
            "title": "Sivers Semiconductors interim report", "entities": {"tickers": [], "company_ids": []},
            "triage": None, "refs": {}}
    lead.update(over)
    return lead


# ---------------------------------------------------------------------------
# kind × 喚醒目標：每一組都要有條目
# ---------------------------------------------------------------------------

def _one_of_each():
    data = _fresh()
    ew.add_watch(data, kind="date", wake_pq2=1, expires="2027-01-01", until="2026-10-01")
    ew.add_watch(data, kind="entity_filing_signal", wake_lead="lead_x", expires="2027-01-01", entities=["NVDA"])
    ew.add_watch(data, kind="fact_verification", hypothesis_ref="hy_1", expires="2027-01-01",
                 fact="x", fact_check_ref="lead_1", entities=["AMD"])
    ew.add_watch(data, kind="related_entity_signal", wake_lead="lead_2", expires="2027-01-01", entities=["COHR"])
    _semantic(data)
    return data


@pytest.mark.parametrize("index", range(5))
def test_every_kind_and_wake_target_has_its_own_entry(index) -> None:
    from engine_b import queue_segments as qs

    watch = _one_of_each()["watches"][index]
    assert "未知 kind" not in ew.watch_detail(watch)
    target = ew.wake_target(watch)
    assert target["kind"] != "unknown"
    if not watch.get("hypothesis_ref"):
        assert target["kind"] != "hypothesis", "沒有假設 id 的 watch 不得被預設成「假設」（§14 陷阱）"
    fired = dict(watch, status="fired")
    segment = qs.classify_watch(fired)
    assert segment and not segment.startswith("unmapped"), segment
    if watch["kind"] == ew.SEMANTIC_KIND:
        assert segment == "semantic_pending_check" and target["kind"] == "disproof"


def test_fired_summary_puts_semantic_watches_in_their_own_bucket(monkeypatch) -> None:
    from engine_b import cli

    data = _one_of_each()
    for watch in data["watches"]:
        watch["status"] = "fired"
    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: data)
    summary = cli._fired_watch_summary()
    assert len(summary["disproof"]) == 1 and all(w.get("hypothesis_ref") for w in summary["hypothesis"])


# ---------------------------------------------------------------------------
# 登記的驗證
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("over, needle", [
    ({"check_frequency": ""}, "L7"),
    ({"action_48h": ""}, "L7"),
    ({"condition": "太短"}, "至少"),
    ({"entities": ["SIVE.ST"]}, "co:"),                                    # 只有 ticker（N-b）
    ({"entities": ["co:not_a_real_company_xyz"]}, "INV-1"),
    ({"expires": "2027-01-01"}, "早於條件自己寫的日期"),                     # 條件寫了 2027-03-31
    ({"expires": "2026-09-01"}, "晚於建立日"),
    ({"source_ref": "memo#1", "disproof_ref": "memo#1"}, "source_ref"),
    ({"disproof_ref": "thesis:other.md#2"}, "disproof_ref"),
])
def test_registration_rejects_incomplete_or_unanchored_conditions(over, needle) -> None:
    with pytest.raises(ew.EventWatchError, match=needle):
        _semantic(_fresh(), **over)


def test_disproof_ref_is_exclusive_to_semantic_and_semantic_requires_it() -> None:
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(_fresh(), kind="related_entity_signal", disproof_ref="thesis:x.md#1",
                     expires="2027-01-01", entities=["COHR"])
    with pytest.raises(ew.EventWatchError):
        _semantic(_fresh(), disproof_ref="", wake_lead="lead_1")


def test_condition_dates_and_published_at_parsing() -> None:
    assert ew.condition_dates("到 2027-06-30 或 2027 年 1 月 5 日") == [date(2027, 6, 30), date(2027, 1, 5)]
    assert ew.parse_published("Tue, 30 Jun 2026 23:15:00 +0000") == date(2026, 6, 30)
    assert ew.parse_published("2026-09-16") == date(2026, 9, 16)
    assert ew.parse_published("2026-08-03T23:35:14.000Z") == date(2026, 8, 3)
    assert ew.parse_published("不是日期") is None


# ---------------------------------------------------------------------------
# T0 矩陣
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lead, fires", [
    (_lead(), True),                                                                     # 未 triage 的 MFN 公告
    (_lead(source="edgar:X", form_type="8-K", title="8-K"), True),                       # 一手 8-K
    (_lead(form_type="4", triage={"decision": "no_go", "tier": 1}), False),              # Form 4（即使 tier=1）
    (_lead(form_type="SC 13G/A"), False),                                                # 持股申報
    (_lead(source_class="secondary"), False),                                            # secondary feed
    (_lead(source="x:aleabitoreddit", source_class="secondary",
           triage={"decision": "go", "tier": 1}), False),                                # X（triage tier 不算數）
    (_lead(published_at="Tue, 01 Sep 2026 05:00:00 +0000"), False),                     # RFC 822 回補舊文件
    (_lead(published_at="2026-09-01"), False),                                           # ISO 回補舊文件
    (_lead(first_seen="2026-09-23T00:00:00+00:00"), False),                              # 建立之前就出現
    (_lead(company_id="co:iqe"), False),                                                 # 實體沒交集
])
def test_t0_matrix(lead, fires) -> None:
    data = _fresh()
    _semantic(data)
    fired = ew.check_watches(data, leads={"L1": lead}, today=date(2026, 9, 25))
    assert bool(fired) is fires
    if fires:
        woken = data["watches"][0]["woken_by"]
        assert woken["lead_id"] == "L1" and woken["disproof_ref"].startswith("thesis:")


def test_unparsable_published_at_falls_back_to_first_seen_and_is_counted() -> None:
    data = _fresh()
    _semantic(data)
    stats: dict[str, int] = {}
    fired = ew.check_watches(data, leads={"L1": _lead(published_at="sometime")}, today=date(2026, 9, 25),
                             stats=stats)
    assert fired and stats["published_at_unparsed"] == 1


def test_consumed_lead_does_not_refire_and_other_kinds_are_untouched() -> None:
    data = _fresh()
    watch = _semantic(data)
    ew.check_watches(data, leads={"L1": _lead()}, today=date(2026, 9, 25))
    ew.judge(data, watch["watch_id"], touches=False, note="只是股權變動")
    assert watch["status"] == "active"
    assert ew.check_watches(data, leads={"L1": _lead()}, today=date(2026, 9, 26)) == []
    # 其他 kind 的一手判準仍看 triage tier（一個字都不動）
    other = ew.add_watch(data, kind="entity_filing_signal", wake_lead="lead_z", expires="2027-01-01",
                         entities=[SIVERS])
    other["created_at"] = "2026-09-24T00:00:00+00:00"
    fired = ew.check_watches(data, leads={"L2": _lead()}, today=date(2026, 9, 25))
    assert not [f for f in fired if f["kind"] == "entity_filing_signal"], \
        "未 triage 的 lead 對 entity_filing_signal 仍不算一手"
    assert [f["kind"] for f in fired] == [ew.SEMANTIC_KIND]


def test_declared_company_survives_register_enrichment_and_entity_rescan() -> None:
    """N-a：`entities` 會被只從文字重算並覆寫——宣告的公司住頂層欄位，由 lead_entities() 併入。"""
    from engine_b.entities import backfill_entities, lead_entities

    store = leads_mod.empty_store()
    lead_id, _ = leads_mod.register(store, source="mfn:sivers-semiconductors",
                                    url="https://mfn.se/cis/a/sivers-semiconductors/interim-q3-abc12345",
                                    title="Delårsrapport", source_class="primary", company_id=SIVERS)
    leads_mod.register(store, source="mfn:sivers-semiconductors",
                       url="https://mfn.se/cis/a/sivers-semiconductors/interim-q3-abc12345",
                       title="Delårsrapport Q3 2026", raw_text="Sivers ...")          # 內容補強
    backfill_entities(store, rescan=True)
    lead = store["leads"][lead_id]
    assert SIVERS not in (lead["entities"].get("company_ids") or [])   # 文字抽不到全名
    assert SIVERS in lead_entities(lead)                                 # 但宣告仍併入
    lead["first_seen"] = "2026-09-25T06:00:00+00:00"
    data = _fresh()
    _semantic(data)
    assert ew.check_watches(data, leads={lead_id: lead}, today=date(2026, 9, 25))


def test_register_rejects_bad_provenance_and_fills_only_missing_fields() -> None:
    store = leads_mod.empty_store()
    with pytest.raises(leads_mod.LeadProvenanceError):
        leads_mod.register(store, source="x", url="https://e.com/1", source_class="tier1")
    with pytest.raises(leads_mod.LeadProvenanceError):
        leads_mod.register(store, source="x", url="https://e.com/1", company_id="co:made_up_zzz")
    lead_id, _ = leads_mod.register(store, source="x", url="https://e.com/2", source_class="secondary")
    leads_mod.register(store, source="x", url="https://e.com/2", source_class="primary", company_id=SIVERS)
    lead = store["leads"][lead_id]
    assert lead["source_class"] == "secondary" and lead["company_id"] == SIVERS   # 不覆寫、只補缺


def test_harvest_feed_config_must_declare_company_and_class(tmp_path) -> None:
    from crons import harvest_leads as h

    base = {"feeds": [{"source": "f", "url": "https://e.com/rss"}]}
    path = tmp_path / "cfg.json"
    for feed_over in ({}, {"company_id": None}, {"source_class": "primary"},
                      {"company_id": "co:made_up_zzz", "source_class": "primary"},
                      {"company_id": None, "source_class": "first_hand"}):
        cfg = {"feeds": [{**base["feeds"][0], **feed_over}]}
        path.write_text(json.dumps(cfg), encoding="utf-8")
        with pytest.raises(ValueError):
            h.load_config(path)
    cfg = {"feeds": [{**base["feeds"][0], "company_id": None, "source_class": "secondary"}]}
    path.write_text(json.dumps(cfg), encoding="utf-8")
    assert h.load_config(path)["feeds"][0]["source_class"] == "secondary"


def test_provenance_error_is_counted_not_silently_dropped(capsys) -> None:
    from crons import harvest_leads as h

    store = leads_mod.empty_store()
    errors: list[str] = []
    new = h._register_all(store, "edgar:X", [{"url": "https://e.com/a", "title": "X 8-K filed 2026-09-25"}], None,
                          provenance={"source_class": "primary", "company_id": "co:made_up_zzz"}, errors=errors)
    assert new == 1 and len(errors) == 1, "lead 照樣登記、宣告錯誤被計數（不走泛用 ValueError 被吞掉）"
    leads_mod.record_run(store, source="edgar:X", result="ok", new=new, provenance_errors=len(errors))
    assert store["harvest_log"][-1]["provenance_errors"] == 1


def test_backfill_provenance_is_idempotent_and_reads_edgar_forms() -> None:
    store = leads_mod.empty_store()
    leads_mod.register(store, source="edgar:NVDA", url="https://www.sec.gov/a", title="NVDA 8-K filed 2026-09-01 [000001]")
    leads_mod.register(store, source="edgar:NVDA", url="https://www.sec.gov/b", title="NVDA SC 13G/A filed 2026-09-01")
    leads_mod.register(store, source="mfn:sivers-semiconductors", url="https://mfn.se/c", title="t")
    leads_mod.register(store, source="weekly:cpo", url="https://e.com/d", title="t")
    feeds = [{"source": "mfn:sivers-semiconductors", "company_id": SIVERS, "source_class": "primary"}]
    counts = leads_mod.backfill_provenance(store, feeds=feeds)
    assert counts == {"edgar:*": 2, "mfn:sivers-semiconductors": 1}
    forms = sorted(l.get("form_type") for l in store["leads"].values() if l["source"].startswith("edgar"))
    assert forms == ["8-K", "SC 13G/A"]
    assert leads_mod.backfill_provenance(store, feeds=feeds) == {}, "第二次跑不得再改任何東西"
    assert "source_class" not in next(l for l in store["leads"].values() if l["source"] == "weekly:cpo")


# ---------------------------------------------------------------------------
# 判定與計數
# ---------------------------------------------------------------------------

def test_judge_yes_consumes_with_quote_and_no_reactivates_with_note() -> None:
    data = _fresh()
    watch = _semantic(data)
    ew.check_watches(data, leads={"L1": _lead()}, today=date(2026, 9, 25))
    with pytest.raises(ew.EventWatchError):
        ew.judge(data, watch["watch_id"], touches=True, note="觸及", quote="")
    with pytest.raises(ew.EventWatchError):
        ew.judge(data, watch["watch_id"], touches=False, note=" ")
    judgment = ew.judge(data, watch["watch_id"], touches=True, note="量產了", quote="entered volume production")
    assert watch["status"] == "consumed" and judgment["touches"] == "yes" and judgment["handled"] is None


def test_counters_count_semantic_states_and_unreachable_only_when_coverage_given() -> None:
    data = _fresh()
    reachable = _semantic(data)
    _semantic(data, entities=["co:jx_advanced_metals"] if _has("co:jx_advanced_metals") else [SIVERS],
              source_ref="thesis:thesis/sivers_v4_lane_memo.md#2", disproof_ref="thesis:thesis/sivers_v4_lane_memo.md#2")
    ew.check_watches(data, leads={"L1": _lead()}, today=date(2026, 9, 25))
    assert reachable["status"] == "fired"
    c = ew.counters(data)
    assert c["semantic_pending_check"] >= 1 and c["semantic_unreachable"] is None
    c = ew.counters(data, coverage=frozenset({SIVERS}))
    assert c["semantic_unreachable"] == (1 if _has("co:jx_advanced_metals") else 0)


def _has(company_id: str) -> bool:
    from identity.registry import get_registry

    return get_registry().has_company(company_id)


# ---------------------------------------------------------------------------
# 預篩：prepare
# ---------------------------------------------------------------------------

def _fired_semantic(data, n, *, lead_prefix="L"):
    for i in range(n):
        watch = _semantic(data, source_ref=f"thesis:thesis/sivers_v4_lane_memo.md#{i + 1}",
                          disproof_ref=f"thesis:thesis/sivers_v4_lane_memo.md#{i + 1}")
        watch["status"] = "fired"
        watch["woken_by"] = {"kind": ew.SEMANTIC_KIND, "lead_id": f"{lead_prefix}{i}",
                             "at": f"2026-09-25T0{i % 10}:00:00+00:00"}


def _cfg(monkeypatch, limit=10, max_chars=100):
    base = ew.load_config()
    monkeypatch.setattr(ew, "load_config", lambda: {**base, "semantic_screen_daily_limit": limit,
                                                    "prescreen_text_max_chars": max_chars})


def test_prepare_caps_by_daily_limit_minus_flags_already_written_today(tmp_path, monkeypatch) -> None:
    _cfg(monkeypatch, limit=10)
    data = _fresh()
    _fired_semantic(data, 12)
    for watch in data["watches"][:3]:                 # 當日稍早那一輪已標 3 筆（模擬同日重跑）
        watch["semantic_flag"] = {"lead_id": watch["woken_by"]["lead_id"], "at": datetime.now(timezone.utc).isoformat(),
                                  "verdict": "cannot_tell"}
    leads = {f"L{i}": {"source": "mops:3105.TWO", "raw_text": f"全文 {i}"} for i in range(12)}
    batch = sp.prepare(data, leads, run_id="r", text_dir=tmp_path)
    assert batch["counts"]["flags_today"] == 3
    assert len(batch["items"]) == 7 and batch["counts"]["not_in_batch"] == 2


def test_no_fetcher_sources_do_not_eat_the_quota(tmp_path, monkeypatch) -> None:
    _cfg(monkeypatch, limit=2)
    data = _fresh()
    _fired_semantic(data, 12)
    leads = {f"L{i}": ({"source": "sivers:press", "url": "https://www.sivers-semiconductors.com/press/x"}
                       if i < 10 else {"source": "mops:3105.TWO", "raw_text": "全文"}) for i in range(12)}
    batch = sp.prepare(data, leads, run_id="r", text_dir=tmp_path)
    assert batch["counts"]["no_fetcher"] == 10 and len(batch["items"]) == 2


def test_fetch_failure_is_counted_and_never_replaced_by_the_title(tmp_path, monkeypatch) -> None:
    _cfg(monkeypatch)
    data = _fresh()
    _fired_semantic(data, 1)
    batch = sp.prepare(data, {"L0": {"source": "x", "title": "標題"}}, run_id="r", text_dir=tmp_path,
                       fetcher=lambda lead: (lambda: None))
    assert batch["items"] == [] and batch["counts"]["no_text"] == 1


def test_stored_text_is_reused_without_network_and_truncation_is_counted(tmp_path, monkeypatch) -> None:
    _cfg(monkeypatch, max_chars=10)
    data = _fresh()
    _fired_semantic(data, 1)
    (tmp_path / "L0.txt").write_text("已存檔的全文，超過十個字的長度", encoding="utf-8")

    def boom():
        raise AssertionError("不得重抓")

    batch = sp.prepare(data, {"L0": {"source": "x"}}, run_id="r", text_dir=tmp_path, fetcher=lambda lead: boom)
    assert batch["counts"]["reused_text"] == 1 and batch["counts"]["truncated"] == 1


def test_edgar_url_parsing_and_ownership_paths_are_explicit_absence() -> None:
    assert sp.parse_edgar_url("https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/q2.htm") == (
        "1045810", "000104581026000073", "q2.htm")
    assert sp.parse_edgar_url(
        "https://www.sec.gov/Archives/edgar/data/1633978/000171491026000003/xslF345X06/form4.xml") is None
    assert sp.parse_edgar_url("https://example.com/Archives/edgar/data/1/2/x.htm") is None
    assert sp.fetcher_for({"url": "https://www.sivers-semiconductors.com/press/x"}) is None


def test_xbrl_header_is_stripped_from_the_cover_page_on() -> None:
    text = "mrvl-20260801 false 2027 Q2 http://fasb.org/us-gaap/2026#X UNITED STATES SECURITIES AND EXCHANGE COMMISSION Form 10-Q"
    assert sp.strip_xbrl_header(text).startswith("UNITED STATES SECURITIES AND EXCHANGE COMMISSION")
    assert sp.strip_xbrl_header("no cover here") == "no cover here"


def test_mfn_text_only_talks_to_mfn_and_never_fetches_attachments(monkeypatch) -> None:
    import fetchers.mfn as mfn

    hosts: list[str] = []

    class Session:
        def get(self, url, timeout=None):
            from urllib.parse import urlsplit

            hosts.append(urlsplit(url).netloc)

            class Resp:
                text = "<html>page</html>"

                def raise_for_status(self):
                    return None

            return Resp()

    monkeypatch.setattr(mfn, "parse_release_page", lambda html: {"text": "公告正文", "attachments": ["x.pdf"]})
    monkeypatch.setattr("fetchers.utils.rate_sleep", lambda *a, **k: None)
    assert sp.fetch_mfn_text("https://mfn.se/cis/a/sivers-semiconductors/q3-abc12345", session=Session()) == "公告正文"
    assert hosts == ["mfn.se"]
    with pytest.raises(ValueError):
        sp.fetch_mfn_text("https://mb.cision.com/x.pdf", session=Session())


# ---------------------------------------------------------------------------
# 預篩：apply
# ---------------------------------------------------------------------------

def _apply_setup(tmp_path, n=2):
    data = _fresh()
    _fired_semantic(data, n)
    items = []
    for i in range(n):
        path = tmp_path / f"L{i}.txt"
        path.write_text("The CW DFB laser array\nentered   volume production in Q3.", encoding="utf-8")
        items.append({"watch_id": data["watches"][i]["watch_id"], "lead_id": f"L{i}", "text_path": str(path)})
    return data, {"run_id": "r1", "items": items}


def _flag(item, verdict="likely_touches", quote="entered volume production", **over):
    return {"watch_id": item["watch_id"], "lead_id": item["lead_id"], "verdict": verdict, "quote": quote,
            "note": "x", "session_id": "s1", **over}


def test_apply_writes_only_the_flag_and_never_changes_status(tmp_path) -> None:
    data, batch = _apply_setup(tmp_path)
    result = {"run_id": "r1", "flags": [_flag(batch["items"][0]),
                                        _flag(batch["items"][1], verdict="cannot_tell", quote=None)]}
    summary = sp.apply(data, batch, result, run_id="r1")
    assert summary["flagged"] == 2 and summary["by_verdict"] == {"likely_touches": 1, "likely_unrelated": 0,
                                                                 "cannot_tell": 1}
    assert all(w["status"] == "fired" for w in data["watches"]), "預篩只標旗、不改狀態（G7）"
    assert data["watches"][0]["semantic_flag"]["session_id"] == "s1"


@pytest.mark.parametrize("mutate, reason", [
    (lambda f: f.update(quote=None), "缺引文"),
    (lambda f: f.update(quote="went bankrupt"), "逐字"),
    (lambda f: f.update(verdict="maybe"), "字彙"),
    (lambda f: f.pop("verdict"), "缺"),
    (lambda f: f.update(watch_id=""), "缺"),
    (lambda f: f.update(lead_id="L_other"), "not_in_batch"),
])
def test_apply_rejects_bad_proposals(tmp_path, mutate, reason) -> None:
    data, batch = _apply_setup(tmp_path, n=1)
    proposal = _flag(batch["items"][0])
    mutate(proposal)
    summary = sp.apply(data, batch, {"run_id": "r1", "flags": [proposal]}, run_id="r1")
    assert summary["flagged"] == 0 and summary["rejected"] == 1
    assert reason in summary["rejections"][0]["reason"]
    assert "semantic_flag" not in data["watches"][0]


def test_whitespace_only_differences_in_the_quote_still_match(tmp_path) -> None:
    data, batch = _apply_setup(tmp_path, n=1)
    summary = sp.apply(data, batch, {"run_id": "r1", "flags": [_flag(batch["items"][0], quote="laser array entered volume\nproduction")]},
                       run_id="r1")
    assert summary["flagged"] == 1


def test_duplicate_pairs_are_all_rejected(tmp_path) -> None:
    data, batch = _apply_setup(tmp_path, n=1)
    item = batch["items"][0]
    summary = sp.apply(data, batch, {"run_id": "r1", "flags": [_flag(item), _flag(item, verdict="cannot_tell", quote=None)]},
                       run_id="r1")
    assert summary["flagged"] == 0 and summary["rejected"] == 2


@pytest.mark.parametrize("kind", ["run_id_param", "stale_result", "missing_file", "bad_json"])
def test_cmd_apply_writes_nothing_when_the_run_does_not_match(tmp_path, monkeypatch, kind) -> None:
    data, batch = _apply_setup(tmp_path, n=1)
    saved: list = []
    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: data)
    monkeypatch.setattr(ew, "save_watches", lambda *a, **k: saved.append(1))
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    result_path = tmp_path / "result.json"
    result = {"run_id": "r1", "flags": [_flag(batch["items"][0])]}
    run_id = "r1"
    if kind == "run_id_param":
        run_id = "r2"
    elif kind == "stale_result":
        result["run_id"] = "earlier-same-day"
    if kind == "bad_json":
        result_path.write_text("{nope", encoding="utf-8")
    elif kind != "missing_file":
        result_path.write_text(json.dumps(result), encoding="utf-8")
    code = sp.cmd_apply(result_path=result_path, batch_path=batch_path, run_id=run_id)
    assert code != 0 and not saved and "semantic_flag" not in data["watches"][0]


def test_prescreen_schema_verdicts_equal_the_closed_vocabulary() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "crons" / "prescreen_schema.json").read_text(encoding="utf-8"))
    item = schema["properties"]["flags"]["items"]
    assert tuple(item["properties"]["verdict"]["enum"]) == ew.PRESCREEN_VERDICTS
    assert item["additionalProperties"] is False and set(item["required"]) == set(item["properties"])
    assert item["properties"]["quote"]["type"] == ["string", "null"]
