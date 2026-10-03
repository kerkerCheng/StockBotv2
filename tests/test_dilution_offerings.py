"""稀釋燈只認募資文件（Phase 6 Step 6.6；plan 2026-10-02-002 §7、使用者定案 §0.1 #9）。

plan 的五個夾具：金額＋424B5 → 黃；金額＋只有 S-8 → 不上色另列；金額＋8-K 3.02 → 黃；金額＋S-3 → 不上色（授權不是募資）；
抓取失敗 → upstream_unavailable。另守：表單判定是封閉清單、以 EDGAR 申報日落窗（窗外與 as-of 之後的都不算，INV-6）、
清單涵蓋不到窗＝說不出「沒有」、daily 的 EDGAR 增量**不多抓一次** submissions（同一次抓取同時給落後檢查與募資文件）。
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date

import pytest

from alpha.wipeout import dilution_flag
from engine_c.offerings import (ensure_offering_schema, is_offering_filing, offerings_in_window, store_offerings)

TODAY = date(2026, 10, 3)
START, END = date(2025, 7, 1), date(2026, 8, 5)
FETCHED = "2026-10-03T00:00:00+00:00"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    ensure_offering_schema(conn)
    return conn


def _filing(form, filed, accession, items=""):
    return {"form_type": form, "filed_date": filed, "accession_dashed": accession, "items": items}


def _offerings(*filings, coverage=("10-K", "2019-02-01", "OLD")):
    """一份清單（最後補一筆很舊的申報當涵蓋起點）寫進表、再照稀釋燈的窗讀出來。"""
    conn = _conn()
    store_offerings(conn, [*filings, _filing(*coverage)], ticker="XYZ", cik="0000000001", fetched_at=FETCHED)
    return offerings_in_window(conn, "XYZ", start=START, end=END, today=TODAY)


def _issuance(total, offerings):
    return {"status": "ok", "filer_class": "domestic_quarterly", "window_after": date(2025, 8, 14),
            "window_end": date(2026, 6, 30), "basis": "quarters", "quarters_found": 4, "trailing_total": total,
            "issued_total": max(total, 0.0), "currencies": ["USD"], "facts": [],
            "tags": ["us-gaap:StockIssuedDuringPeriodValueNewIssues"], "unattributed": [], "inconsistent": [],
            "market_cap_usd": 1e10, "market_cap_absence": None, "offerings": offerings}


def _flag(total, offerings):
    series = [(date(2025, 9, 1), 100.0), (TODAY, 100.0)]
    return dilution_flag(series, {"status": "manual_required"}, today=TODAY, issuance=_issuance(total, offerings))


# ---------------------------------------------------------------------------
# 表單判定（封閉清單）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("form, items, expected", [
    ("424B5", "", True), ("424B2", "", True), ("424B7", "", True), ("S-1", "", True), ("F-1/A", "", True),
    ("8-K", "1.01,3.02,9.01", True), ("8-K/A", "3.02", True),
    ("8-K", "1.01,2.03,9.01", False), ("8-K", "3.021", False),            # 項目逐一比，不做子字串
    ("S-8", "", False), ("S-8 POS", "", False), ("S-3", "", False), ("S-3ASR", "", False), ("F-3", "", False),
    ("10-Q", "", False), ("424B6", "", False),
])
def test_offering_forms_are_a_closed_list(form, items, expected) -> None:
    assert is_offering_filing(form, items) is expected


# ---------------------------------------------------------------------------
# plan §7 的五個夾具
# ---------------------------------------------------------------------------

def test_amount_and_a_prospectus_supplement_is_amber() -> None:
    flag = _flag(600_000_000.0, _offerings(_filing("424B5", "2025-12-29", "A-424")))
    assert flag["colour"] == "amber"
    assert flag["inputs"]["offering_summary"] == "424B5 2025-12-29"
    assert flag["inputs"]["offerings"]["documents"][0]["accession"] == "A-424"
    assert not re.search(r"\d", flag["reason"]), "理由句不帶數字（D2）——表單與日期住稽核層"


def test_amount_with_only_an_employee_plan_registration_is_grey_and_listed_apart() -> None:
    flag = _flag(791_000_000.0, _offerings(_filing("S-8", "2025-11-07", "A-S8")))
    assert flag["colour"] is None and flag["absence_kind"] == "insufficient_evidence"
    assert flag["inputs"]["issued_without_offering"] is True
    assert flag["inputs"]["context_summary"] == "S-8 2025-11-07"                     # 窗內只有什麼，照印
    assert "員工計畫" in flag["reason"] and not re.search(r"\d", flag["reason"])


def test_amount_and_an_unregistered_sale_8k_is_amber() -> None:
    """COHR 型（對 NVIDIA 的私募）：8-K 第 3.02 項——plan L11-6 ④ 最先壞的那一型。"""
    flag = _flag(1_998_450_000.0, _offerings(_filing("8-K", "2026-03-02", "A-8K", "3.02,7.01,9.01"),
                                             _filing("8-K", "2026-04-01", "A-8K-OTHER", "2.02,9.01")))
    assert flag["colour"] == "amber"
    assert [d["accession"] for d in flag["inputs"]["offerings"]["documents"]] == ["A-8K"]
    assert "3.02" in flag["inputs"]["offering_summary"]


def test_amount_with_only_a_shelf_registration_is_grey() -> None:
    """S-3 是授權，不是募資（授權另有人工欄位，照舊只印）。"""
    flag = _flag(17_447_000.0, _offerings(_filing("S-3ASR", "2025-08-11", "A-S3")))
    assert flag["colour"] is None and flag["absence_kind"] == "insufficient_evidence"
    assert flag["inputs"]["context_summary"] == "S-3ASR 2025-08-11"


def test_an_unreadable_filing_list_is_upstream_unavailable_not_green_or_amber() -> None:
    never_fetched = offerings_in_window(_conn(), "XYZ", start=START, end=END, today=TODAY)
    assert never_fetched["status"] == "upstream_unavailable"
    flag = _flag(600_000_000.0, never_fetched)
    assert flag["colour"] is None and flag["absence_kind"] == "upstream_unavailable"
    old_db = offerings_in_window(sqlite3.connect(":memory:"), "XYZ", start=START, end=END, today=TODAY)
    assert old_db["status"] == "upstream_unavailable" and "舊庫" in old_db["reason"]
    assert _flag(600_000_000.0, None)["absence_kind"] == "upstream_unavailable"      # issuance 沒帶 offerings


# ---------------------------------------------------------------------------
# 落窗（INV-6）與涵蓋
# ---------------------------------------------------------------------------

def test_only_filings_inside_the_window_and_known_by_today_count() -> None:
    got = _offerings(_filing("424B5", "2025-06-30", "BEFORE"),                         # 窗起點前一天
                     _filing("424B5", "2026-08-06", "AFTER"),                          # 窗尾後一天
                     _filing("424B5", "2025-07-01", "FIRST-DAY"), _filing("424B5", "2026-08-05", "LAST-DAY"))
    assert [d["accession"] for d in got["documents"]] == ["FIRST-DAY", "LAST-DAY"]
    as_of = offerings_in_window(_conn_with(_filing("424B5", "2026-05-01", "LATER")), "XYZ", start=START, end=END,
                                today=date(2026, 4, 30))
    assert as_of["documents"] == []                                                    # T 之後才申報的看不到
    assert _flag(600_000_000.0, _offerings(_filing("424B5", "2025-06-30", "BEFORE")))["colour"] is None


def _conn_with(*filings):
    conn = _conn()
    store_offerings(conn, [*filings, _filing("10-K", "2019-02-01", "OLD")], ticker="XYZ", cik="1", fetched_at=FETCHED)
    return conn


def test_a_list_that_does_not_reach_back_to_the_window_cannot_say_none() -> None:
    """submissions 的 recent 只給最近約 1000 筆：清單最早只到窗起點之後 → 沒找到不是沒有。"""
    got = _offerings(coverage=("10-Q", "2025-11-01", "RECENT-ONLY"))
    assert got["complete"] is False and "只涵蓋到 2025-11-01" in got["gaps"][0]
    flag = _flag(600_000_000.0, got)
    assert flag["colour"] is None and flag["absence_kind"] == "upstream_unavailable"
    # 但涵蓋不全時**找到了**仍是黃（有文件就是證據）
    found = _offerings(_filing("8-K", "2026-01-15", "A-8K", "3.02"), coverage=("10-Q", "2025-11-01", "R"))
    assert _flag(600_000_000.0, found)["colour"] == "amber"


def test_a_document_without_an_issuance_amount_does_not_colour_the_lamp() -> None:
    """文件不是判色的單獨依據：窗內沒有發行金額就照舊（股數沒增加、窗滿一年 → 綠）。"""
    assert _flag(0.0, _offerings(_filing("424B5", "2025-12-29", "A-424")))["colour"] == "green"


# ---------------------------------------------------------------------------
# daily 的 EDGAR 增量：同一次抓取同時給落後檢查與募資文件（請求數不變）
# ---------------------------------------------------------------------------

SUBMISSIONS = {"name": "XYZ Corp", "filings": {"recent": {
    "form": ["10-Q", "8-K", "S-8", "424B5", "10-K", "10-K"],
    "filingDate": ["2026-08-05", "2026-03-02", "2025-11-07", "2025-12-29", "2026-02-20", "2019-02-20"],
    "accessionNumber": ["Q", "8K", "S8", "B5", "K", "K-OLD"],
    "items": ["", "3.02,9.01", "", "", "", ""],
    "primaryDocument": ["q.htm", "k.htm", "s.htm", "b.htm", "ten.htm", "old.htm"]}}}


def test_incremental_refresh_reuses_the_lag_checks_fetch(monkeypatch) -> None:
    import fetchers.edgar as edgar
    from engine_c import history_backfill as hb

    calls: list[str] = []
    monkeypatch.setattr(edgar, "fetch_submissions", lambda cik: calls.append(cik) or SUBMISSIONS)
    cache: dict = {}
    latest = hb._caching_submissions_latest(cache)
    assert latest("0000000001", ("10-Q", "10-K")) == date(2026, 8, 5)                # 落後檢查要的那個日子
    conn = _conn()
    report = hb._store_offerings(conn, "XYZ", "0000000001", cache, incremental=True, fetched_at=FETCHED)
    assert calls == ["0000000001"], "增量不得為募資文件多抓一次 submissions"
    assert report["outcome"] == "written" and report["rows"] == 3                     # 8-K 3.02、S-8、424B5（10-Q/10-K 不存）
    got = offerings_in_window(conn, "XYZ", start=START, end=END, today=TODAY)
    assert [d["accession"] for d in got["documents"]] == ["B5", "8K"] and got["complete"] is True
    # 這一輪沒抓到（沒有既存財報列）：增量不補抓，照實記 not_fetched
    assert hb._store_offerings(conn, "XYZ", "0000000001", {}, incremental=True, fetched_at=FETCHED)["outcome"] \
        == "not_fetched" and calls == ["0000000001"]
    # 互動回填（非增量）才補抓一次
    assert hb._store_offerings(conn, "XYZ", "0000000001", {}, incremental=False, fetched_at=FETCHED)["outcome"] \
        == "written" and len(calls) == 2


def test_get_filings_keeps_its_keys_and_adds_items(monkeypatch) -> None:
    import fetchers.edgar as edgar

    monkeypatch.setattr(edgar, "fetch_submissions", lambda cik: SUBMISSIONS)
    filings = edgar.get_filings("0000000001", ["8-K"], 5)
    assert [f["accession"] for f in filings] == ["8K"] and filings[0]["items"] == "3.02,9.01"
    assert {"form_type", "filed_date", "accession", "primary_doc", "company_name", "cik"} <= set(filings[0])
