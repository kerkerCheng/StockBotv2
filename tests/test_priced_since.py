"""已定價變動常駐計數器（ROADMAP；failure log #94；2026-10-21 使用者「已定價計數器 go」）。

守的事：①判斷日＝最後一次真的改判的那一版——換騎、只換引用不算改判；②判斷當時的百分位：寫入端記下的優先，
舊版本點時回算、截點＝判斷日前一天（daily 05:30 才抓前一天收盤），回算不到照實寫量不到、**不拿今天的值頂替**（INV-6）；
③寫入端自動記下 `priced_at_write`、不收手寫、不進 id；④已定價那一格與候選理由的位置詞沒寫日期就拒收（只擋寫入，舊紀錄照讀）；
⑤答量不到而今天有值＝前提失效（對稱面），稽核行用寫入端那一份、不含相對組漲幅；⑥心跳與短版只印不判。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.candidates import judgment_version, priced_since
from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import new_brief_id, undated_position_claims
from alpha.providers.briefs import WriteContext, read_brief_records, write_brief
from alpha.providers.candidates import derive_row, open_preconditions
from engine_b import event_watch as ew

CO, T = "co:axt", "AXTI"
READ = "sr_" + "a" * 16
TODAY = date(2026, 10, 21)
EDGE = {"state": "edge", "label": "邊緣", "reasons": ["within_edge"], "market_cap_usd": 4.8e9, "analyst_count": 5}
HELD_NONE = {"status": "ok", "by_company": {}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
PRICED = "已定價：自家三年 {own_history_basis} 的第 {own_history_pctile} 百分位。"


def _slots(priced=PRICED, bottleneck="三家供應、產能同時補不上。") -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "Coherent 預付產能。", "evidence_refs": ev},
            "position": {"text": "坐在基板層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": bottleneck, "evidence_refs": ev},
            "priced_in": {"text": priced, "evidence_refs": ev},
            "our_bet": {"text": "賭層的量。", "evidence_refs": ev},
            "what_must_be_true": {"text": "擴產沒提前。", "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 財報。", "evidence_refs": ev}}


def _rec(*, at: datetime, state="priced_wait", watch_id="ew_wait", reason="寫入時第 88 百分位", priced=PRICED,
         answers=None, supersedes=None, evidence="graph://x", priced_at_write=None, bottleneck=None) -> dict:
    slots = _slots(priced=priced, **({"bottleneck": bottleneck} if bottleneck else {}))
    slots["demand"]["evidence_refs"] = [evidence]
    rec = brief_record(company_id=CO, ticker=T, slots=slots, record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                       answers=answers or {"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": state, "watch_id": watch_id, "reason": reason},
                       supersedes_id=supersedes, created_at=at)
    if priced_at_write is not None:
        rec["priced_at_write"] = priced_at_write
    return rec


def _at(month: int, day: int) -> datetime:
    return datetime(2026, month, day, 4, tzinfo=timezone.utc)       # 台北 12:00，同一個日子


def _chain() -> list:
    """09-29 判等回落（同一筆等待）→ 10-15 重寫理由（改判）→ 10-20 換騎（只換引用，內容一字不改）。"""
    a = _rec(at=_at(9, 29), reason="寫入時第 90 百分位")
    b = _rec(at=_at(10, 15), reason="寫入時第 87 百分位", supersedes=a["brief_id"])
    c = _rec(at=_at(10, 20), reason="寫入時第 87 百分位", supersedes=b["brief_id"], evidence="graph://y")
    return [parse_brief_record(r) for r in (a, b, c)]


# ---- 判斷日 ----

def test_a_reride_is_not_a_new_judgment_but_rewriting_the_reason_is() -> None:
    a, b, c = _chain()
    assert judgment_version([a, b, c], c).brief_id == b.brief_id              # 10-20 換騎 → 判斷日仍是 10-15
    d = parse_brief_record(_rec(at=_at(10, 21), priced="已定價：寫這句的 2026-10-21 當天第 {own_history_pctile}。",
                                reason="寫入時第 87 百分位", supersedes=c.brief_id))
    assert judgment_version([a, b, c, d], d).brief_id == d.brief_id           # 已定價那一格的文字一改就重置


def _derive(records, *, then=None, now=88.0, bars=None, calls=None, state_tq=True):
    calls = calls if calls is not None else []

    def own_history_at(ticker, day, *, history_not_comparable=None):
        calls.append(day)
        return then if then is not None else {"value": 86.8, "basis": "P/S", "as_of": (day).isoformat()}

    def bars_at(ticker, today):
        return bars if bars is not None else [(date(2026, 9, 28), 100.0), (date(2026, 10, 14), 90.0),
                                              (date(2026, 10, 20), 77.85)]

    tq = {"priced_in": [{"key": "own_history_pctile", "value": now, "absence_kind": None if now is not None else
                         "insufficient_evidence", "basis": "P/S", "as_of": "2026-10-20"}],
          "in_numbers": [{"key": "in_numbers_series", "value": [1], "absence_kind": None}], "will_it_die": []}
    watches = [{"watch_id": "ew_wait", "kind": "date", "status": "active", "wake_brief": CO,
                "until": "2026-11-14", "expires": "2027-01-31"}]
    return derive_row(T, CO, records=records, today=TODAY, reading_rows={("tech:x", "layer"): {
        "node": "tech:x", "unit": "layer", "reading_id": READ, "status": "current", "kind": "volume"}},
        watches=watches, lifecycle={}, edge=EDGE, three_questions=tq, held=HELD_NONE,
        own_history_at=own_history_at, bars_at=bars_at), calls


def test_an_old_version_is_recomputed_at_the_day_before_the_judgment_and_marked_as_such() -> None:
    row, calls = _derive(_chain())
    info = row["priced_since"]
    assert info["judgment_day"] == "2026-10-15" and info["then_source"] == "recomputed"
    assert calls[0] == date(2026, 10, 14)                                      # 判斷日前一天（daily 05:30 才抓前一天收盤）
    assert info["return_since"] == pytest.approx(77.85 / 90.0 - 1)             # 基準＝判斷日前一天最後一根
    assert "判斷日 10-15" in info["line"] and "回算" in info["line"] and "→ 今天 第 88.0" in info["line"]
    assert "−13.5%" in info["line"]
    # 等回落起點（同一筆等待連續的最早一版）與判斷日不同 → 另印
    assert info["wait_since"]["day"] == "2026-09-29" and "等回落自 09-29" in info["line"]
    assert info["wait_since"]["return"] == pytest.approx(77.85 / 100.0 - 1) and calls[1] == date(2026, 9, 28)


def test_a_recorded_snapshot_wins_over_recomputing_and_its_bar_is_the_return_base() -> None:
    snap = {"recorded_on": "2026-10-15", "value": 90.1, "basis": "P/S", "as_of": "2026-10-14"}
    a = _rec(at=_at(10, 15), priced_at_write=snap)
    b = _rec(at=_at(10, 20), supersedes=a["brief_id"], evidence="graph://y", priced_at_write={**snap, "value": 81.0,
                                                                                               "as_of": "2026-10-19"})
    row, calls = _derive([parse_brief_record(a), parse_brief_record(b)])
    info = row["priced_since"]
    assert info["then"]["value"] == 90.1 and info["then_source"] == "recorded" and calls == []   # 換騎那版的 81 不算
    assert "寫入時記下" in info["line"]


def test_when_the_judgment_day_cannot_be_measured_today_is_never_used_in_its_place() -> None:
    """INV-6：答不出「T 時刻我知道什麼」就明確說，不得靜默回傳當前值。"""
    row, _ = _derive(_chain(), then={"absence_kind": "insufficient_evidence", "reason": "窗不滿三年"})
    line = row["priced_since"]["line"]
    assert "判斷日 10-15：自家三年 P/S 量不到（insufficient_evidence）" in line and "→ 今天 第 88.0" in line


def test_only_yes_no_wait_or_unmeasurable_but_valued_today_get_a_line() -> None:
    brief = parse_brief_record(_rec(at=_at(10, 15), state="missing", watch_id="ew_wait",
                                    answers={"priced_in": "unmeasurable", "in_numbers": "yes"}))
    kw = dict(judgment_day="2026-10-15", then={"absence_kind": "insufficient_evidence"}, then_source="recomputed",
              return_since=None)
    assert priced_since(T, brief, brief, now={"absence_kind": "insufficient_evidence"}, **kw) is None
    out = priced_since(T, brief, brief, now={"value": 82.6, "basis": "P/S", "as_of": "2026-10-20"}, **kw)
    assert out["line"].startswith("答量不到 AXTI") and "第 82.6" in out["line"]


def test_the_line_never_carries_an_action_or_a_lamp() -> None:
    row, _ = _derive(_chain())
    for word in ("回落了", "該", "燈", "買", "賣", "門檻"):
        assert word not in row["priced_since"]["line"]


# ---- 寫入端 ----

def _ctx(own=88.0):
    tq = {"priced_in": [{"key": "own_history_pctile", "value": own, "absence_kind": None, "basis": "P/S",
                         "as_of": "2026-10-20", "detail": {"multiple_today": 4.2}},
                        {"key": "cohort_median", "value": None, "absence_kind": "not_yet_recorded"}],
          "in_numbers": [{"key": "in_numbers_series", "value": [{"yoy": 1.0}], "absence_kind": None}]}
    today = date.today()
    watches = {"schema_version": 1, "watches": []}
    ctx = WriteContext(today=today, reading_rows=[{"node": "tech:x", "unit": "layer", "reading_id": READ,
                                                   "status": "current", "kind": "volume"}],
                       readings_by_id={READ: SimpleNamespace(angles={"supply_side": [(CO, "supplies_to", "tech:x")],
                                                                     "demand_side": []})},
                       three_questions=tq, watches=watches, lifecycle={})
    wake = ew.add_watch(ctx.watches, kind="date", wake_brief=CO, expires=(today + timedelta(days=200)).isoformat(),
                        until=(today + timedelta(days=30)).isoformat())
    return ctx, wake["watch_id"]


def _fresh(watch_id, **kw) -> dict:
    return _rec(at=datetime.now(timezone.utc), watch_id=watch_id, **kw)


def test_the_writer_records_the_percentile_it_saw_and_it_does_not_change_the_id(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    record = _fresh(wid)
    out = write_brief(record, ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")
    (saved,), _ = read_brief_records(T, directory=tmp_path / "b")
    assert saved.priced_at_write.value == 88.0 and saved.priced_at_write.basis == "P/S"
    assert saved.priced_at_write.as_of == "2026-10-20" and saved.priced_at_write.multiple == 4.2
    assert out["brief_id"] == record["brief_id"] == new_brief_id({**record, "priced_at_write": {"value": 1}})


def test_a_handwritten_snapshot_is_refused(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    record = _fresh(wid, priced_at_write={"recorded_on": "2026-10-21", "value": 10.0})
    with pytest.raises(ContractViolation, match="不收手寫"):
        write_brief(record, ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")


@pytest.mark.parametrize("field, text, refused", [
    ("priced", "已定價：價格已在自家三年的高檔，第 {own_history_pctile} 百分位。", True),
    ("priced", "已定價：寫這句的 2026-10-20 當天在自家三年高檔，第 {own_history_pctile} 百分位。", False),
    ("reason", "價格在偏貴那一端，等回落", True),
    ("reason", "寫入時第 87 百分位，等回落", False),
    ("bottleneck", "只有高端產品線缺貨。", False),                         # 位置詞規則只看已定價那一格與理由
    ("priced", "已定價：在自己歷史的最貴那一端，第 {own_history_pctile}。", True),       # R2：MXL 同模板漏擋
    ("reason", "價格在自家歷史最貴那一端不是改判理由", True),
    ("reason", "缺：Q2 營益率落在指引下緣以上的證據", False),                  # 理由沒講價格的句子不檢查（R2）
    ("priced", "已定價：法說會當天之後股價在高檔，第 {own_history_pctile}。", True),       # 單獨的「當天」不是寫入日
])
def test_an_undated_position_word_is_refused_only_where_the_percentile_is_judged(tmp_path, field, text, refused) -> None:
    ctx, wid = _ctx()
    kw = {"priced": {"priced": text}, "reason": {"reason": text}, "bottleneck": {"bottleneck": text}}[field]
    record = _fresh(wid, **kw)
    if refused:
        with pytest.raises(ContractViolation, match="位置結論"):
            write_brief(record, ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")
    else:
        write_brief(record, ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")


def test_an_old_record_with_a_position_word_still_parses() -> None:
    """規則只在寫入端：放進 parse 路徑，舊紀錄會解析失敗、從候選板上安靜消失（INV-3）。"""
    old = _rec(at=_at(10, 5), priced="已定價：在自家三年的高檔，第 {own_history_pctile}。")
    assert parse_brief_record(old).brief_id == old["brief_id"]
    assert undated_position_claims("高檔") and not undated_position_claims("這一句偏低是量測偏差")


# ---- 對稱面 ----

@pytest.mark.parametrize("valued, failed", [("own_history_pctile", True), ("rel_return_30d", False)])
def test_answering_unmeasurable_while_the_write_side_line_is_valued_today_breaks_the_precondition(valued, failed) -> None:
    brief = parse_brief_record(_rec(at=_at(10, 15), state="open", watch_id=None, reason=None,
                                    answers={"priced_in": "unmeasurable", "in_numbers": "yes"}))
    tq = {"priced_in": [{"key": k, "value": 1.0 if k == valued else None,
                         "absence_kind": None if k == valued else "not_yet_recorded"}
                        for k in ("own_history_pctile", "cohort_median", "rel_return_30d", "rel_return_90d")],
          "in_numbers": [{"key": "in_numbers_series", "value": [1], "absence_kind": None}]}
    out = open_preconditions(brief, reading_rows={("tech:x", "layer"): {"reading_id": READ, "status": "current",
                                                                       "kind": "volume"}},
                             three_questions=tq, blocking=(), breaks=())
    assert (any("答量不到" in f for f in out)) is failed


# ---- 心跳與短版 ----

def _artifact(tmp_path: Path, wait_rows) -> Path:
    import json

    state = tmp_path / "state"
    state.mkdir(parents=True)
    payload = {"schema_version": "stockbot-app/candidates/1", "kind": "candidates", "generated_at": "2026-10-20T22:00:00+00:00",
               "groups": {"priced_wait": wait_rows, "missing": []}, "side_groups": {}, "counts": {}}
    (state / "candidates.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return state


def test_the_heartbeat_prints_zero_and_each_wait_row_and_the_short_line_keeps_dates_intact(tmp_path, monkeypatch) -> None:
    from crons import heartbeat as hb

    row, _ = _derive(_chain())
    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: (None, SimpleNamespace(reason="未讀到", kind="x"))
                        if state_dir is None else (__import__("json").loads((state_dir / "candidates.json")
                                                                            .read_text(encoding="utf-8")), None))
    empty = _artifact(tmp_path / "a", [])
    assert hb._priced_wait_lines(empty)[0].startswith("等回落 0") and hb._priced_wait_short(empty) == "等回落 0"
    full = _artifact(tmp_path / "b", [row])
    lines = hb._priced_wait_lines(full)
    assert lines[0].startswith("等回落 1") and lines[1].strip() == row["priced_since"]["line"]
    assert "記下 0｜回算 1" in lines[-1]
    short = hb._priced_wait_short(full)
    assert "AXTI 86.8→88.0 −13.5%（等回落自 09-29 −22.2%）" in short     # 日期的連字號不被換成負號
    assert "等回落起點的值有回算的" in short
    for word in ("該", "燈", "買", "賣"):
        assert word not in short


# ---- R2（2026-10-21）的條件 ----

def test_a_version_written_before_the_daily_run_only_knew_the_bar_before_yesterday() -> None:
    """R2 D1：daily 05:30（台北）才抓前一天收盤——00:38 寫的版本手上最後一根是前前一天（美股那天收盤甚至還不存在）。"""
    from alpha.providers.candidates import knowable_bar_day

    assert knowable_bar_day(datetime(2026, 10, 16, 16, 38, tzinfo=timezone.utc)) == date(2026, 10, 15)   # 台北 10-17 00:38
    assert knowable_bar_day(datetime(2026, 10, 17, 4, 0, tzinfo=timezone.utc)) == date(2026, 10, 16)     # 台北 10-17 12:00
    early = _rec(at=datetime(2026, 10, 16, 16, 38, tzinfo=timezone.utc))
    row, calls = _derive([parse_brief_record(early)])
    assert row["priced_since"]["judgment_day"] == "2026-10-17" and calls[0] == date(2026, 10, 15)


def test_the_wait_start_says_it_was_recomputed_and_from_which_close() -> None:
    row, _ = _derive(_chain())
    assert "等回落自 09-29（同一筆等待）：第 86.8（09-28 收盤，回算）" in row["priced_since"]["line"]


def test_a_transient_unreadable_snapshot_falls_back_to_recomputing() -> None:
    snap = {"recorded_on": "2026-10-15", "value": None, "absence_kind": "upstream_unavailable",
            "reason": "寫入當下讀不到三題稽核區"}
    a = parse_brief_record(_rec(at=_at(10, 15), priced_at_write=snap))
    row, calls = _derive([a])
    assert row["priced_since"]["then_source"] == "recomputed" and calls == [date(2026, 10, 14)]


def test_a_handwritten_snapshot_is_refused_even_on_a_retraction(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    first = _fresh(wid)
    write_brief(first, ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")
    retraction = brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                              rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                              answers={"priced_in": "yes", "in_numbers": "yes"},
                              candidate_state={"state": "priced_wait", "watch_id": wid, "reason": "寫入時第 88 百分位"},
                              supersedes_id=first["brief_id"], retracted=True)
    with pytest.raises(ContractViolation, match="不收手寫"):
        write_brief({**retraction, "priced_at_write": {"recorded_on": "2026-10-21", "value": 1.0}}, ctx=ctx,
                    directory=tmp_path / "b", watches_path=tmp_path / "w.json")


def test_no_basis_on_either_side_prints_no_none() -> None:
    brief = parse_brief_record(_rec(at=_at(10, 15)))
    out = priced_since(T, brief, brief, judgment_day="2026-10-15", then={"absence_kind": "inputs_incompatible"},
                       then_source="recomputed", now={"absence_kind": "inputs_incompatible"}, return_since=None)
    assert "None" not in out["line"] and "自家三年 量不到" in out["line"]
