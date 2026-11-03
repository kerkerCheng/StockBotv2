"""只差已定價進短版 ③ 待你決定（盲點修法 plan 2026-11-02-001 §1 第 3 條；failure log #123、#124）。

整體盲點審查 2026-11-01：等回落被歸為「等待」，永遠不進 ③——10-31 四次價格叫醒、四次重寫，四份仍等回落，價格判斷沒有
地方交到使用者手上。守的事：①只差已定價的列進 ③、排在編號前面，沒有編號、不進批次指令；②0 檔不印、讀不到照說，
不壓成「沒有」；③摘要行「球在你」旁邊印它；④完整心跳段 3 也印一行（0 也印）；⑤判斷只有 `priced_only_rows` 一份。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from alpha.candidates import priced_only_counts, priced_only_rows
from crons import heartbeat as hb
from crons.daily_brief import decisions_block
from engine_b import todo
from engine_b import todo_ledger as tl

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
ROWS = [{"ticker": "STLTECH.NS", "company_id": "co:sterlite", "open_gaps": []},
        {"ticker": "AXTI", "company_id": "co:axt", "open_gaps": ["待處置的反證 watch：ew_1"]},
        {"ticker": "OLD", "company_id": "co:old"}]                                      # 舊 artifact：沒算


def test_one_judgment_for_rows_and_counts() -> None:
    assert [r["ticker"] for r in priced_only_rows(ROWS)] == ["STLTECH.NS"]
    assert priced_only_counts(ROWS) == {"priced_only": 1, "priced_only_unknown": 1}


def test_priced_only_is_a_decision_not_a_wait() -> None:
    assert tl.COVERAGE["candidate:priced_only"] == "decision" and tl.COVERAGE["candidate:priced_wait"] == "wait"


def test_priced_only_comes_first_in_decisions_and_stays_out_of_the_batch() -> None:
    item = {"n": 900, "type": "manual", "title": "題目", "recommendation": {"verb": "go", "reason": "r"}}
    lines, batch = decisions_block(actionable=[item], problem=None, todo_mod=todo, priced_only=["思特利 STLTECH.NS", "B"])
    assert lines[0] == "### ③ 待你決定（1＋只差已定價 2）"
    assert lines[1] == "**只差已定價 2 檔：思特利 STLTECH.NS、B**"
    assert lines.index("**[900] 題目**") > 1 and batch == "900 go"           # 批次指令只有編號


def test_priced_only_alone_replaces_none_and_zero_prints_nothing() -> None:
    lines, batch = decisions_block(actionable=[], problem=None, todo_mod=todo, priced_only=["A"])
    assert lines[0] == "### ③ 待你決定（0＋只差已定價 1）" and "- 沒有" not in lines and batch is None
    assert decisions_block(actionable=[], problem=None, todo_mod=todo, priced_only=[])[0] == ["### ③ 待你決定（0）",
                                                                                            "- 沒有"]


def test_unreadable_board_is_said_not_folded_into_none() -> None:
    lines, _ = decisions_block(actionable=[], problem=None, todo_mod=todo, priced_only=None,
                               priced_problem="候選板沒有 artifact")
    assert "**只差已定價：讀不到（候選板沒有 artifact）**" in lines and "- 沒有" not in lines
    lines, _ = decisions_block(actionable=None, problem="OSError", todo_mod=todo, priced_only=["A"])
    assert "讀不到：OSError" in lines[0] and "**只差已定價 1 檔：A**" in lines      # pq2 讀不到不帶走它


def test_names_come_from_the_board_wait_rows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: ({"groups": {"priced_wait": ROWS}}, None))
    assert hb.priced_only_names(tmp_path) == (["STLTECH.NS"], None)
    assert hb.priced_only_names(tmp_path, label=lambda r: f"名 {r['ticker']}") == (["名 STLTECH.NS"], None)
    monkeypatch.undo()
    names, problem = hb.priced_only_names(tmp_path / "none")
    assert names is None and problem                                           # 讀不到＝None＋理由，不是 []


def test_summary_line_counts_it_beside_the_ball(tmp_path: Path) -> None:
    kw = dict(now=NOW, run_record_path=tmp_path / "nope.json", leads_path=tmp_path / "nope.json", theme_nudge=False,
              theme_line="")
    line = hb.summary_line(snapshot={"pq2.actionable": 2, "candidate.priced_only": 1}, **kw)
    assert line.startswith("Daily 2026-11-03｜球在你 2｜只差已定價 1")
    assert "只差已定價" not in hb.summary_line(snapshot={"pq2.actionable": 2, "candidate.priced_only": 0}, **kw)
    assert "只差已定價" not in hb.summary_line(snapshot={"pq2.actionable": 2, "candidate.priced_only": None}, **kw)


def test_full_heartbeat_section_three_line_prints_zero_and_unread() -> None:
    assert hb.priced_only_queue_line([], None) == "**只差已定價 0**（可開的機械前提都成立，價格判斷由你下；短版 ③）"
    assert hb.priced_only_queue_line(["A", "B"], None).endswith("短版 ③）：A、B")
    assert hb.priced_only_queue_line(None, "候選板讀不到") == "只差已定價：讀不到（候選板讀不到）"


def test_full_heartbeat_section_three_is_wired_to_the_board(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: ({"groups": {"priced_wait": ROWS}}, None))
    lines = hb.build_queue(state_dir=tmp_path, now=NOW).lines
    assert any(x.startswith("**只差已定價 1**") and x.endswith("：STLTECH.NS") for x in lines)
