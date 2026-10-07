"""Phase 7 Step 7.0d：敘事「加碼條件」`confirm[]`（使用者 2026-10-04 A2）。

加碼條件＝「這件事發生，代表結構被確認了」。與反證對稱：寫下即登記成語意 watch、有到期、到期是重問；
**觸及只提醒，不是買進訊號、不改候選狀態**。它**不得被算成反證**：心跳「反證：在盯／觸及」、downside 面板、
圖預測表、`blocking_for_open` 都不吃它（plan §4、§13 已知陷阱）。既有敘事紀錄的 `brief_id` 一位都不變（§0 第 7 條）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import new_brief_id
from alpha.providers.briefs import read_brief_records
from engine_b import disproof
from engine_b import event_watch as ew
from engine_b.narrative_watches import blocking_for_open, pending_rewrite
from engine_b.queue_segments import narrative_rewrite_state
from tests.test_narrative_v2 import CO, FAR, _ctx, _record, _write

ROOT = Path(__file__).resolve().parents[1]
T = "AXTI"
COND = "客戶 Coherent 在自己的 10-Q 具名 AXT 為六吋 InP 基板供應商並揭露量產採購金額"
STAMP = datetime(2026, 10, 4, 3, tzinfo=timezone.utc)


def _confirm(condition: str = COND, **over) -> dict:
    item = {"condition": condition, "check_frequency": "每季", "action_48h": "重寫敘事：寫明確認了什麼、候選狀態換不換",
            "entities": [CO], "expires": FAR, "source": "self"}
    item.update(over)
    return item


def _written(tmp_path: Path, **record_kw):
    ctx = _ctx()
    out = _write(tmp_path, _record(confirm=[_confirm()], stamp=STAMP, **record_kw), ctx)
    records, _errors = read_brief_records(T, directory=tmp_path / "briefs")
    brief = next(r for r in records if r.brief_id == out["brief_id"])
    watch = next(w for w in ctx.watches["watches"] if w["watch_id"] == out["confirm_registered"][0])
    return ctx, out, brief, watch


def _touch(data: dict, watch: dict) -> None:
    """照真實流程：先醒來（fired），再由互動 session 判定觸及（`ew.judge`：consume＋judgment，quote 是文件逐字）。"""
    watch.update(status="fired", woken_by={"kind": ew.SEMANTIC_KIND, "lead_id": "lead_x", "at": "2026-11-05T01:00:00+00:00"})
    ew.judge(data, watch["watch_id"], touches=True, note="Coherent 10-Q 具名 AXT 為六吋基板供應商",
             quote="AXT is our supplier of six-inch InP substrates")


# ---------------------------------------------------------------------------
# 契約與 id 穩定
# ---------------------------------------------------------------------------

def test_confirm_is_an_optional_v2_field_that_leaves_ids_without_it_alone() -> None:
    without = _record(stamp=STAMP)
    explicit_empty = _record(stamp=STAMP, confirm=[])
    assert "confirm" not in without and without["brief_id"] == explicit_empty["brief_id"]
    with_confirm = _record(stamp=STAMP, confirm=[_confirm()])
    assert with_confirm["brief_id"] != without["brief_id"] and new_brief_id(with_confirm) == with_confirm["brief_id"]
    assert parse_brief_record(with_confirm).confirm[0].condition == COND


def test_every_real_ledger_line_keeps_its_brief_id() -> None:
    """§0 第 7 條：真實 ledger 每一行用新程式重算，逐位相同（只讀；這台機器沒有 private ledger 就跳過）。"""
    directory = ROOT / "library" / "private" / "alpha" / "briefs"
    lines = ([line for p in sorted(directory.glob("*.jsonl")) for line in p.read_text(encoding="utf-8").splitlines()
              if line.strip()] if directory.is_dir() else [])
    if not lines:
        pytest.skip("沒有真實敘事 ledger（private，不進 Git）")
    for line in lines:
        raw = json.loads(line)
        assert new_brief_id(raw) == raw["brief_id"], raw["brief_id"]


@pytest.mark.parametrize("over, message", [
    ({"entities": ["AXTI"]}, "co:"),
    ({"source": "lead_x"}, "source"),
    ({"expires": None}, "expires"),
    ({"action_48h": ""}, "action_48h"),
])
def test_confirm_needs_the_same_triplet_entities_and_source_as_a_disproof(over, message) -> None:
    with pytest.raises(ContractViolation, match=message):
        _record(confirm=[_confirm(**over)])


@pytest.mark.parametrize("confirm, message", [
    ([_confirm(), _confirm()], r"confirm\[2\]：與 confirm\[1\] 是同一個條件"),
    ([_confirm(condition="若 JX 在 2026-12-31 前宣布新產能投產則供給缺口消失，本敘事的量的賭注不成立")],
     r"confirm\[1\]：與 disproof\[1\] 是同一個條件"),
    ([_confirm(entities=[CO, "co:no_such_company_xyz"])], "registry 解析不到"),
    ([_confirm(source="sr_" + "c" * 16)], "不是任何讀圖 id"),
])
def test_write_time_checks_mirror_the_disproof_ones(tmp_path: Path, confirm, message) -> None:
    with pytest.raises(ContractViolation, match=message):
        _write(tmp_path, _record(confirm=confirm), _ctx())
    assert not (tmp_path / "briefs").exists()


# ---------------------------------------------------------------------------
# 登記與類別分離
# ---------------------------------------------------------------------------

def test_writing_registers_each_confirm_as_its_own_semantic_watch(tmp_path: Path) -> None:
    _ctx_, out, _brief, watch = _written(tmp_path)
    assert len(out["registered"]) == 1 and len(out["confirm_registered"]) == 1      # 反證一條、加碼條件一條，分開數
    assert watch["source_ref"] == f"brief:{out['brief_id']}#c1" == watch["disproof_ref"]
    assert ew.is_confirm(watch) and watch["kind"] == ew.SEMANTIC_KIND
    target = ew.wake_target(watch)
    assert target["kind"] == "confirm" and "不是買進訊號" in target["label"]


def test_condition_role_is_closed_and_only_for_narrative_sources() -> None:
    data = {"schema_version": 1, "watches": []}
    ref = "thesis:thesis/x.md#1"
    with pytest.raises(ew.EventWatchError, match="只用在敘事來源"):
        ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref=ref, source_ref=ref, expires=FAR, entities=[CO],
                     condition=COND, check_frequency="每季", action_48h="重寫", condition_role="confirm")
    with pytest.raises(ew.EventWatchError, match="未登記"):
        ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref="brief:ib_x#c1", source_ref="brief:ib_x#c1",
                     expires=FAR, entities=[CO], condition=COND, check_frequency="每季", action_48h="重寫",
                     condition_role="maybe")


def test_a_confirm_watch_is_never_counted_as_a_disproof(tmp_path: Path) -> None:
    """變異：把加碼條件算成反證 → 反證「觸及待處置」會從 0 變 1、可開會被它擋。"""
    ctx, out, brief, watch = _written(tmp_path)
    watches = ctx.watches["watches"]
    _touch(ctx.watches, watch)
    assert disproof.watch_category(watch) == disproof.CONFIRM and disproof.confirm_state(watch) == "touched"
    counts = disproof.disproof_counts(watches, lifecycle={}, readings={}, briefs=[brief])
    assert counts["touched_pending"] == 0 and counts["orphan_touched"] == 0 and counts["watching"] == 1
    assert disproof.confirm_counts(watches) == {"watching": 0, "touched_pending": 1, "expired_pending": 0}
    assert blocking_for_open(CO, T, watches=watches, lifecycle={}, brief_ids=[out["brief_id"]], current_brief=brief) == []
    downside = disproof.downside_rows(CO, T, records=[brief], current_brief=brief, watches=watches, lifecycle={},
                                      reading_rows={}, root=tmp_path)
    assert all(row.get("watch_id") != watch["watch_id"] for row in downside["rows"])


# ---------------------------------------------------------------------------
# 觸及與到期：只提醒、進 narrative_rewrite、下一版逐條處置；候選狀態不被自動改
# ---------------------------------------------------------------------------

def test_a_touched_confirm_is_rewrite_work_and_the_next_version_acknowledges_it(tmp_path: Path) -> None:
    ctx, out, _brief, watch = _written(tmp_path)
    _touch(ctx.watches, watch)
    assert narrative_rewrite_state(watch) == "touched"
    assert watch in pending_rewrite(CO, watches=ctx.watches["watches"], brief_ids=[out["brief_id"]])
    later = STAMP + timedelta(minutes=5)
    with pytest.raises(ContractViolation, match="acknowledged_touched"):
        _write(tmp_path, _record(confirm=[_confirm()], supersedes=out["brief_id"], stamp=later), ctx)
    ack = {"watch_id": watch["watch_id"], "disposition": "confirmed", "note": "客戶 10-Q 具名，結構確認；候選狀態照判"}
    second = _write(tmp_path, _record(confirm=[_confirm()], supersedes=out["brief_id"], stamp=later, acks=[ack]), ctx)
    assert watch["judgment"]["handled"]["verb"] == "confirmed"
    records, _ = read_brief_records(T, directory=tmp_path / "briefs")
    assert next(r for r in records if r.brief_id == second["brief_id"]).candidate_state.state == "open"   # 照宣告


def test_an_expired_confirm_also_asks_for_a_rewrite(tmp_path: Path) -> None:
    ctx, out, _brief, watch = _written(tmp_path)
    watch.update(status="expired")
    assert narrative_rewrite_state(watch) == "expired" and disproof.confirm_state(watch) == "expired"
    assert disproof.confirm_counts(ctx.watches["watches"])["expired_pending"] == 1


def test_the_board_lists_each_confirm_and_a_touched_one_is_a_reminder_not_a_state_change() -> None:
    from tests.test_candidates import EDGE, HELD_NONE, READ, _rows, _tq
    from alpha.providers.candidates import derive_row

    rec = brief_record(company_id=CO, ticker=T, slots=_record()["slots"], record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}], disproof=[],
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "open", "watch_id": None, "reason": None},
                       confirm=[_confirm()], created_at=datetime(2026, 9, 29, 3, tzinfo=timezone.utc))
    brief = parse_brief_record(rec)
    ref = f"brief:{brief.brief_id}#c1"
    watch = {"watch_id": "ew_c", "kind": ew.SEMANTIC_KIND, "status": "active", "expires": FAR, "source_ref": ref,
             "disproof_ref": ref, "condition": COND, "entities": [CO], "condition_role": "confirm"}
    _touch({"watches": [watch]}, watch)
    row = derive_row(T, CO, records=[brief], today=datetime(2026, 11, 6).date(), reading_rows=_rows(),
                     watches=[watch], lifecycle={}, edge=EDGE, three_questions=_tq(), held=HELD_NONE)
    assert row["confirm"][0]["state"] == "touched" and "不是買進訊號" in row["confirm"][0]["state_label"]
    assert row["confirm"][0]["touched_at"] == watch["judgment"]["at"][:10]     # 判定那天
    # plan §4 第 3 項的字，整句在 materialize 端組好（前端照印）
    assert row["confirm"][0]["line"] == f"加碼條件已觸及：{COND}（{watch['judgment']['at'][:10]}）——提醒，不是買進訊號"
    assert row["group"] == "open" and row["preconditions"] == []                  # 可開不被它擋、狀態照宣告
    assert any("ew_c" in text for text in row["rewrite"])                         # 但它是敘事重寫的工作


def test_an_untouched_confirm_line_says_when_it_will_be_asked_again() -> None:
    assert disproof.confirm_line(COND, "active", until="2027-03-31") == f"加碼條件：{COND}｜在盯（最晚 2027-03-31 到期重問）"
    assert disproof.confirm_line(COND, "unwatched") == f"加碼條件：{COND}｜未盯"              # 沒 watch 照實印（INV-3）
    assert disproof.confirm_line(COND, "touched") == f"加碼條件已觸及：{COND}（日期不明）——提醒，不是買進訊號"


def test_the_frontend_prints_the_line_it_is_given_and_composes_no_words() -> None:
    """`app.js` 有全檔的部位用語禁字檢查（`tests/test_webapp_beta.py`，不放寬）：這一類的字只住 materialize 端。"""
    source = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    body = source.split("function confirmLines(", 1)[1].split("\n}\n", 1)[0]
    assert "c.line" in body and "`" not in body                                  # 照印、不用樣板字串組字


# ---------------------------------------------------------------------------
# 心跳與 audit
# ---------------------------------------------------------------------------

def test_the_heartbeat_prints_confirm_on_its_own_line(monkeypatch: pytest.MonkeyPatch) -> None:
    from crons import heartbeat

    ref = "brief:ib_x#c1"
    watches = [{"watch_id": "ew_c", "kind": ew.SEMANTIC_KIND, "status": "active", "expires": FAR, "source_ref": ref,
                "disproof_ref": ref, "condition": COND, "entities": [CO], "condition_role": "confirm"}]
    monkeypatch.setattr(ew, "load_watches", lambda: {"watches": watches})
    monkeypatch.setattr(ew, "primary_coverage", lambda: frozenset())
    monkeypatch.setattr(disproof, "current_readings", lambda: {})
    monkeypatch.setattr(disproof, "current_layer_notes", lambda: {})   # 2026-10-07 S4a：不讀真實層說明 ledger
    monkeypatch.setattr(disproof, "frozen_history_count", lambda: 0)
    monkeypatch.setattr(disproof, "load_lifecycle", lambda: {})
    monkeypatch.setattr(disproof, "current_briefs", lambda: [])
    text = "\n".join(heartbeat._disproof_lines())
    assert "反證：在盯 0" in text and "觸及待處置 0" in text
    assert "加碼條件：在盯 1｜**觸及待處置 0**（提醒，不是買進訊號）｜到期待重寫 0" in text
    assert {"confirm.watching", "confirm.touched_pending", "confirm.expired_pending"} <= set(heartbeat.SNAPSHOT_KEYS)


def test_audit_resolves_a_confirm_watch_against_the_briefs_confirm_list(monkeypatch: pytest.MonkeyPatch) -> None:
    from audit import checks, sources

    rec = _record(confirm=[_confirm()], stamp=STAMP)
    brief = parse_brief_record(rec)
    ref = f"brief:{brief.brief_id}#c1"
    watch = {"watch_id": "ew_c", "kind": ew.SEMANTIC_KIND, "status": "active", "expires": FAR, "source_ref": ref,
             "disproof_ref": ref, "condition": COND, "entities": [CO], "condition_role": "confirm",
             "created_at": STAMP.isoformat()}
    monkeypatch.setattr(sources, "thesis_lifecycle", lambda: {})
    monkeypatch.setattr(sources, "reading_ledgers", lambda: {})
    monkeypatch.setattr(sources, "brief_ledgers", lambda: {T: {"records": [brief], "errors": []}})
    monkeypatch.setattr(sources, "current_briefs", lambda: [brief])
    findings, _soft, examined = checks._semantic_source_orphans([watch])
    assert examined == 1 and findings == []
    watch["condition"] = "客戶在自己的文件裡說了另一件完全不同的事情，與加碼條件原文對不上"
    findings, _soft, _ = checks._semantic_source_orphans([watch])
    assert any("confirm[] 對不到" in f for f in findings)
