"""ROADMAP「敘事 stale 計數器」②④（2026-11-03 批次三 C；failure log #93）：正文最後一次改動時騎的那份讀圖，跟這一格
現行的讀圖比——②判讀（kind）變了、④供給側家數變了——進候選列 `rewrite[]`、整板清單（kind=reading_kind／supply_count）、
⑤「敘事該重寫」；寫入端拒收正文一字不改、卻跨過判讀或家數改變的換騎（⑫）。

事發：AEVA 10-19 換騎跨過 undecided→neither、正文仍寫「NPO 沒有需求側」；COHR／LITE／SIVE.ST 換騎跨過供給側 7→9 家、正文
仍寫「七家」——換騎工具寫「內容一字不改」就過。回放全部 ledger（2026-11-03，497 版）：正文沒改的換騎 115 次，判讀變了 1（AEVA）、
家數變了 29。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.candidates import (BODY_BEHIND_KINDS, READING_KIND_CHANGED_PREFIX, SUPPLY_COUNT_CHANGED_PREFIX,
                              body_behind_readings, body_behind_reasons, body_version, rewrite_words,
                              supply_side_companies)
from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.providers.briefs import WriteContext, body_behind_problems, write_brief
from alpha.providers.candidates import board_rewrite, derive_row

CO, T = "co:aeva", "AEVA"
OLD = "sr_" + "a" * 16
NEW = "sr_" + "b" * 16
NOW = datetime.now(timezone.utc)
FAR = (date.today() + timedelta(days=200)).isoformat()


def _reading(kind: str, supply: tuple[str, ...] = (CO, "co:b")):
    return SimpleNamespace(kind=kind, angles={"supply_side": [(c, "supplies_to", "tech:npo") for c in supply],
                                              "demand_side": [("co:nvidia", "depends_on", "tech:npo")]})


def _slots(bottleneck: str = "兩家做得出來、客戶刻意分給兩家。") -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "NPO 沒有需求側。", "evidence_refs": ev},
            "position": {"text": "坐在 NPO 這一層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": bottleneck, "evidence_refs": ev},
            "priced_in": {"text": "已定價：自家三年 {own_history_basis} 的第 {own_history_pctile} 百分位。",
                          "evidence_refs": ev},
            "our_bet": {"text": "賭層的量。", "evidence_refs": ev},
            "what_must_be_true": {"text": "必須為真：客戶下單；錯的訊號是改用銅。", "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 的財報。", "evidence_refs": ev}}


def _record(*, reading_id: str = OLD, slots: dict | None = None, supersedes: str | None = None,
            stamp: datetime | None = None, rides: list | None = None) -> dict:
    return brief_record(
        company_id=CO, ticker=T, slots=slots or _slots(), record_version=RECORD_VERSION_V2,
        rides=rides if rides is not None else [{"node": "tech:npo", "unit": "layer", "reading_id": reading_id}],
        disproof=[{"condition": "若 Broadcom 在 2026-12-31 前公告改用銅互連則 NPO 這一層的量的賭注不成立",
                   "check_frequency": "每季", "action_48h": "重寫敘事並重看讀圖", "entities": [CO], "expires": FAR,
                   "source": "self", "link_source_ref": None}],
        answers={"priced_in": "yes", "in_numbers": "yes"},
        candidate_state={"state": "pass", "watch_id": None, "reason": "不要：測試"},
        supersedes_id=supersedes, created_at=stamp or NOW)


def _chain(*, second_reading: str = NEW, second_slots: dict | None = None):
    first = parse_brief_record(_record(stamp=NOW - timedelta(days=3)))
    second = parse_brief_record(_record(reading_id=second_reading, slots=second_slots, supersedes=first.brief_id,
                                        stamp=NOW - timedelta(days=1)))
    return [first, second]


# ---------------------------------------------------------------------------
# 純函式
# ---------------------------------------------------------------------------

def test_a_reride_across_a_kind_change_is_reading_kind_and_across_a_supply_change_is_supply_count() -> None:
    records = _chain()
    head = records[-1]
    body = body_version(records, head)
    assert body.brief_id == records[0].brief_id, "第二版只換騎、正文一字不改——正文版是第一版"
    readings = {OLD: _reading("undecided"), NEW: _reading("neither")}
    entries, unchecked = body_behind_readings(body, head, readings_by_id=readings,
                                              current_cells={("tech:npo", "layer"): NEW})
    assert unchecked == 0 and [e["changes"] for e in entries] == [["reading_kind"]]
    e = entries[0]
    assert (e["body_reading_id"], e["current_reading_id"], e["body_kind"], e["current_kind"]) == (OLD, NEW, "undecided",
                                                                                                    "neither")
    readings = {OLD: _reading("volume"), NEW: _reading("volume", (CO, "co:b", "co:c", "co:d"))}
    entries, _ = body_behind_readings(body, head, readings_by_id=readings, current_cells={("tech:npo", "layer"): NEW})
    assert [e["changes"] for e in entries] == [["supply_count"]]
    assert entries[0]["body_supply"] == 2 and entries[0]["current_supply"] == 4
    assert entries[0]["added"] == ["co:c", "co:d"] and entries[0]["removed"] == []
    readings = {OLD: _reading("undecided"), NEW: _reading("neither", (CO,))}
    entries, _ = body_behind_readings(body, head, readings_by_id=readings, current_cells={("tech:npo", "layer"): NEW})
    assert entries[0]["changes"] == ["reading_kind", "supply_count"] and entries[0]["removed"] == ["co:b"]


def test_nothing_to_flag_when_the_body_was_rewritten_or_nothing_changed_or_only_members_swapped() -> None:
    rewritten = _chain(second_slots=_slots(bottleneck="判讀改成都不是：客戶刻意讓任何一家都做得出來。"))
    readings = {OLD: _reading("undecided"), NEW: _reading("neither")}
    body = body_version(rewritten, rewritten[-1])
    assert body.brief_id == rewritten[-1].brief_id
    assert body_behind_readings(body, rewritten[-1], readings_by_id=readings,
                                current_cells={("tech:npo", "layer"): NEW}) == ([], 0)
    records = _chain()
    body = body_version(records, records[-1])
    same = {OLD: _reading("volume"), NEW: _reading("volume")}
    assert body_behind_readings(body, records[-1], readings_by_id=same,
                                current_cells={("tech:npo", "layer"): NEW}) == ([], 0)
    # 同樣家數、換了一家（不在 ②④ 的範圍——回放 0 次；要比成員另議）
    swapped = {OLD: _reading("volume", (CO, "co:b")), NEW: _reading("volume", (CO, "co:z"))}
    assert body_behind_readings(body, records[-1], readings_by_id=swapped,
                                current_cells={("tech:npo", "layer"): NEW}) == ([], 0)


def test_a_superseded_ride_is_compared_against_the_current_cell_and_a_missing_record_is_unchecked_not_zero() -> None:
    """騎舊讀圖（①）的格也比：正文寫時騎 OLD、這一格現行已是 NEW——判讀或家數變了就是 ②④（只換騎不夠），沒變就只有 ①。"""
    single = [parse_brief_record(_record(stamp=NOW - timedelta(days=3)))]
    head = single[-1]
    readings = {OLD: _reading("volume"), NEW: _reading("volume", (CO, "co:b", "co:c"))}
    entries, _ = body_behind_readings(head, head, readings_by_id=readings, current_cells={("tech:npo", "layer"): NEW})
    assert [e["changes"] for e in entries] == [["supply_count"]] and entries[0]["current_reading_id"] == NEW
    # 舊讀圖紀錄找不到：不比、記成沒比成
    entries, unchecked = body_behind_readings(head, head, readings_by_id={NEW: readings[NEW]},
                                              current_cells={("tech:npo", "layer"): NEW})
    assert entries == [] and unchecked == 1
    # 正文版沒騎這一格（之後才加騎）：不比
    added = [*_chain()]
    head = parse_brief_record(_record(supersedes=added[-1].brief_id, rides=[
        {"node": "tech:npo", "unit": "layer", "reading_id": NEW},
        {"node": "tech:other", "unit": "layer", "reading_id": "sr_" + "c" * 16}]))
    entries, unchecked = body_behind_readings(body_version([*added, head], head), head,
                                              readings_by_id={OLD: _reading("volume"), NEW: _reading("volume"),
                                                              "sr_" + "c" * 16: _reading("moat")},
                                              current_cells={})
    assert entries == [] and unchecked == 0


def test_reasons_point_back_to_the_readings_and_companies_and_map_to_five_words() -> None:
    entry = {"node": "tech:npo", "unit": "layer", "body_reading_id": OLD, "current_reading_id": NEW,
             "body_kind": "undecided", "current_kind": "neither", "body_supply": 7, "current_supply": 9,
             "added": ["co:c", "co:d"], "removed": [], "changes": ["reading_kind", "supply_count"]}
    kind_reason, count_reason = body_behind_reasons(entry)
    assert kind_reason.startswith(READING_KIND_CHANGED_PREFIX) and OLD in kind_reason and NEW in kind_reason
    assert "undecided（判不出）" in kind_reason and "neither（都不是）" in kind_reason
    assert count_reason.startswith(SUPPLY_COUNT_CHANGED_PREFIX) and "7 家" in count_reason and "9 家" in count_reason
    assert "多 co:c、co:d" in count_reason
    assert rewrite_words([kind_reason, count_reason]) == ["判讀變了", "家數變了"]
    assert BODY_BEHIND_KINDS == ("reading_kind", "supply_count")


def test_supply_side_is_one_function_shared_with_the_write_side() -> None:
    from alpha.providers import briefs

    reading = _reading("volume", (CO, "co:b", "TICKER_NOT_ID"))
    assert supply_side_companies(reading) == {CO, "co:b"} and briefs._supply_side(reading) == {CO, "co:b"}


# ---------------------------------------------------------------------------
# 候選列與整板清單
# ---------------------------------------------------------------------------

HELD_NONE = {"status": "ok", "by_company": {}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
EDGE = {"state": "edge", "label": "邊緣", "reasons": ["within_edge"], "market_cap_usd": 1e9, "analyst_count": 3}


def _derive(records, *, cell: str = NEW, readings=None):
    rows = {("tech:npo", "layer"): {"node": "tech:npo", "unit": "layer", "reading_id": cell, "status": "current",
                                    "kind": "neither"}}
    return derive_row(T, CO, records=records, today=date.today(), reading_rows=rows, watches=[], lifecycle={},
                      edge=EDGE, three_questions=None, held=HELD_NONE, readings_by_id=readings)


def test_the_row_names_the_change_in_rewrite_and_the_board_list_counts_each_signal() -> None:
    row = _derive(_chain(), readings={OLD: _reading("undecided"), NEW: _reading("neither", (CO,))})
    assert [e["changes"] for e in row["rewrite_reading_changes"]] == [["reading_kind", "supply_count"]]
    assert row["reading_change_unchecked"] == 0
    assert sum(1 for r in row["rewrite"] if r.startswith(READING_KIND_CHANGED_PREFIX)) == 1
    assert sum(1 for r in row["rewrite"] if r.startswith(SUPPLY_COUNT_CHANGED_PREFIX)) == 1
    assert "判讀變了" in row["rewrite_words"] and "家數變了" in row["rewrite_words"]
    items = board_rewrite([row], [])
    kinds = sorted(i["kind"] for i in items)
    assert kinds == ["reading_kind", "supply_count"]
    assert all(i["ticker"] == T and i["company_id"] == CO and "changes" not in i for i in items)


def test_a_row_without_the_reading_records_says_not_checked_instead_of_zero() -> None:
    row = _derive(_chain(), readings=None)
    assert row["rewrite_reading_changes"] is None and row["reading_change_unchecked"] is None
    assert not any(r.startswith((READING_KIND_CHANGED_PREFIX, SUPPLY_COUNT_CHANGED_PREFIX)) for r in row["rewrite"])
    assert board_rewrite([row], []) == []


def test_a_superseded_ride_with_only_a_new_id_is_rides_only_but_with_a_count_change_is_both() -> None:
    single = [parse_brief_record(_record(stamp=NOW - timedelta(days=3)))]
    same = _derive(single, readings={OLD: _reading("neither"), NEW: _reading("neither")})
    assert [i["kind"] for i in board_rewrite([same], [])] == ["rides"]
    grown = _derive(single, readings={OLD: _reading("neither"), NEW: _reading("neither", (CO, "co:b", "co:c"))})
    assert sorted(i["kind"] for i in board_rewrite([grown], [])) == ["rides", "supply_count"]


# ---------------------------------------------------------------------------
# 寫入端（⑫）
# ---------------------------------------------------------------------------

def _tq() -> dict:
    def row(key, value=1.0, absent=None):
        return {"key": key, "value": None if absent else value, "absence_kind": absent}
    return {"priced_in": [row("own_history_pctile", 88.0), row("cohort_median", absent="not_yet_recorded"),
                          row("rel_return_30d", absent="not_yet_recorded"),
                          row("rel_return_90d", absent="not_yet_recorded")],
            "in_numbers": [row("in_numbers_series", [{"yoy": 1.0}])]}


def _ctx(cell: str, readings: dict) -> WriteContext:
    return WriteContext(today=date.today(),
                        reading_rows=[{"node": "tech:npo", "unit": "layer", "reading_id": cell, "status": "current",
                                       "kind": readings[cell].kind}],
                        readings_by_id=readings, three_questions=_tq(),
                        watches={"schema_version": 1, "watches": []}, lifecycle={})


def _write(tmp_path: Path, record: dict, ctx: WriteContext) -> dict:
    return write_brief(record, ctx=ctx, directory=tmp_path / "briefs", watches_path=tmp_path / "w.json")


@pytest.mark.parametrize("new_reading, message", [
    (_reading("neither"), READING_KIND_CHANGED_PREFIX),                         # AEVA 10-19：undecided → neither
    (_reading("undecided", (CO, "co:b", "co:c")), SUPPLY_COUNT_CHANGED_PREFIX),  # COHR 10-18：7 → 9 家
])
def test_the_write_side_refuses_a_word_for_word_reride_across_a_kind_or_count_change(tmp_path: Path, new_reading,
                                                                                      message) -> None:
    readings = {OLD: _reading("undecided"), NEW: new_reading}
    first = _write(tmp_path, _record(stamp=NOW - timedelta(days=2)), _ctx(OLD, readings))
    ctx = _ctx(NEW, readings)
    with pytest.raises(ContractViolation, match=message):
        _write(tmp_path, _record(reading_id=NEW, supersedes=first["brief_id"]), ctx)
    # 正文改了（寫出新的判讀或家數為什麼不改變結論）就收
    rewritten = _write(tmp_path, _record(reading_id=NEW, supersedes=first["brief_id"],
                                         slots=_slots(bottleneck="讀圖已改判（2026-11-03）；結論不變的理由：客戶仍只認兩家。")),
                       ctx)
    assert rewritten["brief_id"]


def test_the_write_side_still_accepts_a_reride_when_kind_and_count_did_not_change(tmp_path: Path) -> None:
    readings = {OLD: _reading("undecided"), NEW: _reading("undecided", (CO, "co:z"))}   # 同樣兩家、換了一家
    first = _write(tmp_path, _record(stamp=NOW - timedelta(days=2)), _ctx(OLD, readings))
    out = _write(tmp_path, _record(reading_id=NEW, supersedes=first["brief_id"]), _ctx(NEW, readings))
    assert out["brief_id"]


def test_the_write_side_check_skips_first_versions_and_retractions() -> None:
    first = parse_brief_record(_record(stamp=NOW - timedelta(days=2)))
    readings = {OLD: _reading("undecided"), NEW: _reading("neither")}
    assert body_behind_problems(first, existing=[], readings_by_id=readings) == []
    retract = parse_brief_record(brief_record(
        company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
        rides=[{"node": "tech:npo", "unit": "layer", "reading_id": NEW}], disproof=[],
        answers={"priced_in": "yes", "in_numbers": "yes"},
        candidate_state={"state": "pass", "watch_id": None, "reason": "不要：測試"},
        supersedes_id=first.brief_id, retracted=True, created_at=NOW))
    assert body_behind_problems(retract, existing=[first], readings_by_id=readings) == []
    reride = parse_brief_record(_record(reading_id=NEW, supersedes=first.brief_id))
    problems = body_behind_problems(reride, existing=[first], readings_by_id=readings)
    assert len(problems) == 1 and problems[0].startswith("rides：" + READING_KIND_CHANGED_PREFIX)
    assert first.brief_id in problems[0]
