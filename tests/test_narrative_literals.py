"""首屏敘事不寫死燈色與價格報酬（2026-10-31 使用者「都做」；failure log #120）＋宣告可開前的深挖清單（#119）。

守的事：①敘事任何一格與候選理由寫死燈色（「現金跑道紅燈」）寫入端拒收——燈每天重算、首屏另有一行；只擋寫入，舊紀錄照讀；
「開綠燈」這種核准的意思不擋（L16）。②已定價那一格寫收盤價只印不擋（寫入結果帶 notices）。③故事也不准寫死燈色。
④深挖清單：沒給、缺幾項、「不適用：理由」算答了、「缺：…」算沒答、不認得的鍵另列。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import lamp_colour_claims, price_quote_claims
from alpha.narrative.depth_check import DEPTH_CHECK_KEYS, depth_check_gaps, depth_check_lines
from alpha.narrative.story import story_problems
from alpha.providers.briefs import WriteContext, write_brief
from engine_b import event_watch as ew

CO, T = "co:axt", "AXTI"
READ = "sr_" + "b" * 16
PRICED = "已定價：自家三年 {own_history_basis} 的第 {own_history_pctile} 百分位。"


def _slots(**over) -> dict:
    ev = ["graph://x"]
    texts = {"demand": "Coherent 預付產能。", "position": "坐在基板層，年增 {in_numbers_latest}（{in_numbers_as_of}）。",
             "bottleneck": "三家供應、產能同時補不上。", "priced_in": PRICED, "our_bet": "賭層的量。",
             "what_must_be_true": "擴產沒提前。", "when": "{next_checkpoint_date} 財報。", **over}
    return {k: {"text": v, "evidence_refs": ev} for k, v in texts.items()}


def _ctx():
    tq = {"priced_in": [{"key": "own_history_pctile", "value": 50.0, "absence_kind": None, "basis": "P/S",
                         "as_of": "2026-10-30", "detail": {"multiple_today": 2.0}},
                        {"key": "cohort_median", "value": None, "absence_kind": "not_yet_recorded"}],
          "in_numbers": [{"key": "in_numbers_series", "value": [{"yoy": 0.5}], "absence_kind": None}]}
    today = date.today()
    ctx = WriteContext(today=today, reading_rows=[{"node": "tech:x", "unit": "layer", "reading_id": READ,
                                                   "status": "current", "kind": "volume"}],
                       readings_by_id={READ: SimpleNamespace(angles={"supply_side": [(CO, "supplies_to", "tech:x")],
                                                                     "demand_side": []})},
                       three_questions=tq, watches={"schema_version": 1, "watches": []}, lifecycle={})
    wake = ew.add_watch(ctx.watches, kind="date", wake_brief=CO, expires=(today + timedelta(days=200)).isoformat(),
                        until=(today + timedelta(days=30)).isoformat())
    return ctx, wake["watch_id"]


def _record(watch_id: str, *, reason: str = "缺：客戶沒具名", at: datetime | None = None, **slot_over) -> dict:
    return brief_record(company_id=CO, ticker=T, slots=_slots(**slot_over), record_version=RECORD_VERSION_V2,
                        rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                        answers={"priced_in": "no", "in_numbers": "yes"},
                        candidate_state={"state": "missing", "watch_id": watch_id, "reason": reason},
                        created_at=at or datetime.now(timezone.utc))


# ---- ① 燈色：寫入端拒收，舊紀錄照讀 ----

@pytest.mark.parametrize("slot, text", [
    ("what_must_be_true", "擴產沒提前；現金跑道與負債都是紅燈。"),          # AAON 10-16 的寫法
    ("priced_in", PRICED + "缺的是份額的印證與會死嗎的兩盞紅燈。"),           # 4971.TWO 10-19 的寫法
    ("what_must_be_true", "燒錢——系統的歸零燈現金跑道是紅燈。"),             # CECO 10-28 的寫法
    ("what_must_be_true", "仍在燒錢（現金跑道黃燈）、股數增加（稀釋黃燈）。"),  # OUST 的寫法
])
def test_a_hard_coded_lamp_colour_in_any_slot_is_refused(tmp_path: Path, slot: str, text: str) -> None:
    ctx, wid = _ctx()
    with pytest.raises(ContractViolation, match="寫死了燈色"):
        write_brief(_record(wid, **{slot: text}), ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")


def test_a_hard_coded_lamp_colour_in_the_candidate_reason_is_refused(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    with pytest.raises(ContractViolation, match="candidate_state.reason：寫死了燈色"):
        write_brief(_record(wid, reason="缺：①營收沒拆；②現金跑道紅燈。"), ctx=ctx, directory=tmp_path / "b",
                    watches_path=tmp_path / "w.json")


def test_the_fact_behind_the_lamp_and_a_regulatory_green_light_pass(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    text = "擴產沒提前；本業在燒錢、照現在的速度現金撐不到一年。主管機關已開綠燈。"
    out = write_brief(_record(wid, what_must_be_true=text), ctx=ctx, directory=tmp_path / "b",
                      watches_path=tmp_path / "w.json")
    assert out["brief_id"] and out["notices"] == []
    assert lamp_colour_claims("主管機關開綠燈") == [] and lamp_colour_claims("現金跑道紅燈")
    assert lamp_colour_claims("法院對負債重整開綠燈") == [] and lamp_colour_claims("負債亮紅燈、跑道綠燈")


def test_an_old_record_with_a_lamp_colour_still_parses() -> None:
    """規則只在寫入端：放進 parse 路徑，6 份現行敘事會解析失敗、從候選板上安靜消失（INV-3）。"""
    old = _record("ew_x", at=datetime(2026, 10, 16, 4, tzinfo=timezone.utc),
                  what_must_be_true="擴產沒提前；現金跑道與負債都是紅燈。")
    assert parse_brief_record(old).brief_id == old["brief_id"]


# ---- ② 收盤價：只印不擋 ----

def test_a_closing_price_in_priced_in_is_written_but_noticed(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    priced = PRICED + "寫這句的 2026-10-28：調整後收盤由 2026 年 1 月 2 日 59.79 美元漲到 6 月 22 日 99.67 美元。"
    out = write_brief(_record(wid, priced_in=priced), ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")
    assert out["brief_id"] and len(out["notices"]) == 1 and "寫了收盤價" in out["notices"][0]


def test_words_about_the_price_and_filing_numbers_are_not_noticed() -> None:
    assert price_quote_claims("寫這句的 2026-10-28：股價上半年大漲、6 月見高點後跌回年初以下。") == []
    assert price_quote_claims("營收 1.2 億元，收盤後公布第三季財報。") == []
    assert price_quote_claims("10 月 27 日收盤 4.54 美元。")


# ---- ③ 故事 ----

def test_a_story_with_a_lamp_colour_is_refused_and_the_fact_passes() -> None:
    assert any("寫死了燈色" in p for p in story_problems("what_must_be_true", "現金跑道是紅燈，要看第三季現金流。"))
    assert not any("寫死了燈色" in p for p in story_problems("what_must_be_true", "本業在燒錢，要看第三季現金流。"))


# ---- ④ 深挖清單 ----

def test_no_depth_check_on_an_open_narrative_says_so() -> None:
    (line,) = depth_check_lines(None)
    assert "沒有深挖清單" in line and "只印、不擋" in line


def test_missing_items_are_listed_and_not_applicable_counts_as_answered() -> None:
    given = {k: "library/raw/x.txt" for k in DEPTH_CHECK_KEYS}
    given["latest_call"] = "不適用：公司不辦法說"
    given["core_premise"] = "缺：只有供應商自述"
    given["typo_key"] = "x"
    missing, unknown = depth_check_gaps(given)
    assert missing == ["所押讀圖的核心前提有供應商自述以外的證據（L8）"] and unknown == ["typo_key"]
    lines = depth_check_lines(given)
    assert "還缺 1 項" in lines[0] and "不認得的鍵" in lines[1]
    assert depth_check_lines({k: "sr_" + "c" * 16 for k in DEPTH_CHECK_KEYS}) == ["  ✓ 深挖清單 10 項都答了"]
