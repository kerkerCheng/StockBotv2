"""「早於建立日的舊文件不叫醒」那道閘要在 `published_at` 的日曆上比（2026-11-01）。

事發：停放時建的追源 watch `created_at`＝lead 進 pq1 的時間（daily 在台北 05:15–07:05 分類＝UTC 前一天晚上），
原本建立日取 UTC 日期，於是前一晚的 MOPS 重訊（台北 10-30）對台北 10-31 05:43 建的 watch 算「不早於建立日」——
同一場董事會的 sibling 重訊把剛建的追源 watch 全部叫醒（11-01 當天 16 次叫醒裡 5 次：ew_1919–1924）。
反向（EDGAR）：台北早上建的 watch（UTC 當天、美東前一天）會把前一晚美東的 8-K 當回補舊文件靜默擋掉（INV-3）。
"""
from __future__ import annotations

from datetime import date

import pytest

from engine_b import event_watch as ew

KINSUS = "co:kinsus"
AXT = "co:axt"


def _fresh():
    return {"schema_version": 1, "watches": []}


def _trace_watch(data, *, entities, created_at: str, kind: str = "entity_filing_signal"):
    watch = ew.add_watch(data, kind=kind, wake_lead="lead_parked", expires="2027-02-28",
                         entities=entities, today=date(2026, 10, 31))
    watch["created_at"] = created_at
    return watch


def _semantic_watch(data, *, entities, created_at: str):
    watch = ew.add_watch(
        data, kind=ew.SEMANTIC_KIND, disproof_ref="thesis:thesis/axt_inp_memo.md#1",
        source_ref="thesis:thesis/axt_inp_memo.md#1", expires="2027-06-30", entities=entities,
        condition="AXT 下一份 10-Q 的 MD&A 寫出 InP 基板毛利率主因與 Lumentum 合約的定價機制（2027-03-31 前）",
        check_frequency="每季財報後", action_48h="重讀 thesis 並決定是否 revise", today=date(2026, 10, 31))
    watch["created_at"] = created_at
    return watch


def _mops(*, published_at: str, decided_at: str, first_seen: str):
    """MOPS 重訊：`published_at` 寫台北當天；分類層隔天早上才 triage。"""
    return {"source": "mops:3189.TW", "source_class": "primary", "company_id": KINSUS,
            "entities": {"tickers": ["3189.TW"], "company_ids": [KINSUS]},
            "first_seen": first_seen, "published_at": published_at, "form_type": None,
            "title": "3189.TW 景碩 重訊", "url": "https://openapi.twse.com.tw/v1/opendata/t187ap04_L?co_id=3189",
            "triage": {"decision": "go", "tier": 1, "decided_at": decided_at}, "refs": {}}


def _edgar(*, published_at: str, decided_at: str, first_seen: str, form_type: str = "8-K"):
    """EDGAR：`published_at` 是美東日曆的 filing date。"""
    return {"source": "edgar:AXTI", "source_class": "primary", "company_id": AXT,
            "entities": {"tickers": ["AXTI"], "company_ids": [AXT]},
            "first_seen": first_seen, "published_at": published_at, "form_type": form_type,
            "title": "AXTI 8-K", "url": "https://www.sec.gov/Archives/edgar/data/1051627/000105162726000001/axti-8k.htm",
            "triage": {"decision": "go", "tier": 1, "decided_at": decided_at}, "refs": {}}


# --- 日曆換算本身 --------------------------------------------------------------------

def test_created_day_is_read_on_the_calendar_published_at_is_written_in() -> None:
    created = "2026-10-30T21:43:28+00:00"          # 台北 10-31 05:43；美東 10-30 17:43
    assert ew._created_day(created, _mops(published_at="2026-10-30", decided_at=created, first_seen=created)) == date(2026, 10, 31)
    assert ew._created_day(created, _edgar(published_at="2026-10-30", decided_at=created, first_seen=created)) == date(2026, 10, 30)
    other = {"source": "mfn:x", "url": "https://mfn.se/a"}
    assert ew._created_day(created, other) == date(2026, 10, 30)              # 沒宣告日曆→UTC（原行為）
    assert ew._created_day("", other) is None and ew._created_day("不是時間", other) is None


# --- MOPS：同日同源的 sibling 重訊不叫醒剛建的追源 watch ------------------------------------

@pytest.mark.parametrize("kind", ["entity_filing_signal", "related_entity_signal"])
def test_sibling_mops_announcement_from_the_night_before_does_not_wake_a_watch_created_next_morning(kind) -> None:
    """ew_1919 的形狀：10-30 晚董事會三則重訊，daily 10-31 05:43 分類；停放其中一則建的 watch 被另兩則叫醒。"""
    data = _fresh()
    _trace_watch(data, entities=[KINSUS], created_at="2026-10-30T21:43:28.569121+00:00", kind=kind)
    sibling = _mops(published_at="2026-10-30", decided_at="2026-10-30T21:43:29+00:00",
                    first_seen="2026-10-30T21:30:30+00:00")
    assert ew.check_watches(data, leads={"L_sibling": sibling}, today=date(2026, 10, 31)) == []
    assert data["watches"][0]["status"] == "active"


def test_next_day_mops_announcement_still_wakes_the_same_watch() -> None:
    data = _fresh()
    _trace_watch(data, entities=[KINSUS], created_at="2026-10-30T21:43:28.569121+00:00")
    later = _mops(published_at="2026-10-31", decided_at="2026-10-31T21:45:00+00:00",
                  first_seen="2026-10-31T21:30:00+00:00")
    fired = ew.check_watches(data, leads={"L_next": later}, today=date(2026, 11, 1))
    assert [w["woken_by"]["lead_id"] for w in fired] == ["L_next"]


def test_semantic_watch_applies_the_same_calendar() -> None:
    data = _fresh()
    _semantic_watch(data, entities=[KINSUS], created_at="2026-10-30T21:43:28+00:00")
    sibling = _mops(published_at="2026-10-30", decided_at="2026-10-30T21:43:29+00:00",
                    first_seen="2026-10-30T21:50:00+00:00")      # first_seen 晚於建立（否則 ④ 就擋了）
    assert ew.check_watches(data, leads={"L": sibling}, today=date(2026, 10, 31)) == []
    later = _mops(published_at="2026-10-31", decided_at="2026-10-31T21:45:00+00:00",
                  first_seen="2026-10-31T21:30:00+00:00")
    assert len(ew.check_watches(data, leads={"L2": later}, today=date(2026, 11, 1))) == 1


# --- EDGAR：台北早上建的 watch 不得把前一晚美東的申報當回補舊文件 ----------------------------

def test_edgar_filing_from_the_previous_us_evening_still_wakes_a_watch_created_the_taipei_morning() -> None:
    """watch 10-31 09:00 台北（01:00Z 10-31＝美東 10-30 21:00）；8-K 美東 10-30 21:30 申報、隔天 daily 才 harvest。
    舊規則：建立日 UTC 10-31 > published 10-30 → 靜默擋掉。"""
    data = _fresh()
    _trace_watch(data, entities=[AXT], created_at="2026-10-31T01:00:00+00:00")
    filing = _edgar(published_at="2026-10-30", decided_at="2026-10-31T21:45:00+00:00",
                    first_seen="2026-10-31T21:30:00+00:00")
    fired = ew.check_watches(data, leads={"L_8k": filing}, today=date(2026, 11, 1))
    assert [w["woken_by"]["lead_id"] for w in fired] == ["L_8k"]


def test_edgar_backfilled_old_filing_is_still_not_an_event() -> None:
    data = _fresh()
    _trace_watch(data, entities=[AXT], created_at="2026-10-31T01:00:00+00:00")
    old = _edgar(published_at="2026-05-01", decided_at="2026-10-31T21:45:00+00:00",
                 first_seen="2026-10-31T21:30:00+00:00", form_type="10-Q")
    assert ew.check_watches(data, leads={"L_old": old}, today=date(2026, 11, 1)) == []
