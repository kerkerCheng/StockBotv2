"""MOPS 全市場重訊的過濾報告進心跳段 1（盲點修法 plan 2026-11-02-001 §1 第 4 條；INV-3）。

`harvest_mops` 逐檔呼叫 `select_tickers(rows, [ticker])`，每檔各自的報告沒有意義、整份丟掉；`fetch_material_announcements`
又在那之前就丟掉代號解析不出來的列，所以「代號解析不出」恆為 0。守的事：①解析不出的列留空代號、數得到；②每個市場
每輪記一筆 `mops-batch:<市場>`，帶全市場報告；抓不到也記，蓋過上一輪的數；③心跳段 1 自己一行、不算一個來源。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from crons import harvest_leads
from crons import heartbeat as hb
from engine_b import leads
from fetchers import mops_open_data as mops

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_unparseable_codes_are_kept_so_the_filter_can_count_them(monkeypatch) -> None:
    payload = [{"公司代號": "3081", "主旨": "董事會決議", "發言日期": "1151103"}, {"公司代號": "ABCD"}, "not a row"]
    monkeypatch.setattr(mops, "_get", lambda url, **_kw: _Response(payload))
    rows = mops.fetch_material_announcements("tpex")
    assert [r["ticker"] for r in rows] == ["3081.TWO", "", ""]
    _accepted, report = mops.select_tickers(rows, ["3081.TWO"])
    assert report == {"input": 3, "accepted": 1, "filtered": 2, "filtered_not_watched": 0,
                      "filtered_unresolved_ticker": 2}


def _harvest(monkeypatch, fetch) -> dict:
    store = leads.empty_store()
    monkeypatch.setattr(harvest_leads, "_mops_watch_tickers", lambda watch: ["3081.TWO"])
    monkeypatch.setattr(mops, "fetch_material_announcements", fetch)
    harvest_leads.harvest_mops({"mops_watch": {"tickers": ["3081.TWO"]}}, store, seen_at=NOW.isoformat())
    return store


def test_each_market_run_records_the_whole_market_report(monkeypatch) -> None:
    store = _harvest(monkeypatch, lambda market: [{"ticker": "6488.TWO"}, {"ticker": ""}])
    by_source = {e["source"]: e for e in store["harvest_log"]}
    assert by_source["mops:3081.TWO"]["result"] == "ok"                       # 逐檔那一筆照舊
    batch = by_source[f"{leads.MOPS_BATCH_SOURCE_PREFIX}tpex"]
    assert batch["result"] == "ok" and batch["new"] == 0
    assert batch["filter"] == {"input": 2, "accepted": 0, "filtered": 2, "filtered_not_watched": 1,
                               "filtered_unresolved_ticker": 1}


def test_a_failed_fetch_also_records_the_batch(monkeypatch) -> None:
    def boom(market):
        raise OSError("connection reset")

    store = _harvest(monkeypatch, boom)
    batch = [e for e in store["harvest_log"] if e["source"] == f"{leads.MOPS_BATCH_SOURCE_PREFIX}tpex"]
    assert len(batch) == 1 and batch[0]["result"] == "fetch_failed" and "filter" not in batch[0]


def test_the_line_prints_zero_and_failure_and_nothing_without_records() -> None:
    ok = {"result": "ok", "filter": {"input": 412, "accepted": 3, "filtered": 409, "filtered_not_watched": 405,
                                     "filtered_unresolved_ticker": 0}}
    line = hb.mops_batch_line({"twse": ok, "tpex": {"result": "fetch_failed", "failure_class": "network"}})
    assert line == ("MOPS 全市場重訊（最後一輪）：上櫃 **抓不到**（network）；"
                    "上市 輸入 412｜名冊內 3｜名冊外 405｜代號解析不出 0")
    assert hb.mops_batch_line({}) is None


def test_section_one_prints_it_without_counting_it_as_a_source(tmp_path: Path) -> None:
    stamp = NOW.isoformat()
    log = [{"run_at": stamp, "source": "mops:3081.TWO", "result": "ok", "new": 0},
           {"run_at": stamp, "source": f"{leads.MOPS_BATCH_SOURCE_PREFIX}tpex", "result": "ok", "new": 0,
            "filter": {"input": 120, "accepted": 1, "filtered": 119, "filtered_not_watched": 118,
                       "filtered_unresolved_ticker": 1}}]
    path = tmp_path / "pending_leads.json"
    path.write_text(json.dumps({"leads": {}, "harvest_log": log}), encoding="utf-8")
    lines = hb.build_freshness(now=NOW, state_dir=tmp_path, leads_path=path).lines
    assert any(x.startswith("harvest 來源 1 個｜失敗 0 個") for x in lines), lines
    assert "MOPS 全市場重訊（最後一輪）：上櫃 輸入 120｜名冊內 1｜名冊外 118｜代號解析不出 1" in lines
