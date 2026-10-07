"""SessionStart hook `crons/phase_status_hint.py`：開 session 該 /phase-run 還是 /phase-plan。

2026-10-01 事發：狀態欄比對寫成 `== "active"`，Phase 4 那一列是「active（2026-10-01；…）」，
hook 因此說「沒有 active plan、Phase 5 待寫 plan」——照做的執行者會停在一份正在跑的 plan 前面。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from crons import phase_status_hint as hint

ROOT = Path(__file__).resolve().parent.parent

_HEADER = "| Phase | plan 檔 | 狀態 |\n|---|---|---|\n"


def _run(tmp_path, monkeypatch, capsys, rows: str) -> str:
    readme = tmp_path / "README.md"
    readme.write_text(_HEADER + rows, encoding="utf-8")
    monkeypatch.setattr(hint, "PLANS_README", readme)
    assert hint.main() == 0
    return json.loads(capsys.readouterr().out)["systemMessage"]


def test_status_with_trailing_annotation_counts_as_active(tmp_path, monkeypatch, capsys):
    msg = _run(tmp_path, monkeypatch, capsys,
               "| 3 候選 | [x](x.md) | completed（2026-09-30；closeout `x`；R2 GO） |\n"
               "| 4 層中心來源 | [y](y.md) | active（2026-10-01；12 題定案；執行者全程強模型） |\n"
               "| 5 量測 | 尚無 | — |\n")
    assert "Phase 4 層中心來源 執行中" in msg
    assert "/phase-run" in msg
    assert "待寫 plan" not in msg
    # 註記照抄：使用者定案的執行者模型不能被「建議模型：便宜」蓋掉
    assert "執行者全程強模型" in msg


def test_no_active_row_points_to_phase_plan(tmp_path, monkeypatch, capsys):
    msg = _run(tmp_path, monkeypatch, capsys,
               "| 4 層中心來源 | [y](y.md) | completed（2026-10-09） |\n"
               "| 5 量測 | 尚無 | — |\n")
    assert "沒有 active plan" in msg and "Phase 5 量測" in msg


def test_two_active_rows_is_flagged(tmp_path, monkeypatch, capsys):
    msg = _run(tmp_path, monkeypatch, capsys,
               "| 4 | [y](y.md) | active |\n| 5 | [z](z.md) | active（註記） |\n")
    assert "兩份以上 active" in msg


def test_is_active_needs_the_whole_word():
    assert hint._is_active("active")
    assert hint._is_active(" active（2026-10-01） ")
    assert not hint._is_active("activated")
    assert not hint._is_active("inactive")
    assert not hint._is_active("completed（active 期間的註記）")


def test_real_readme_status_cells_start_with_a_known_word():
    """對照表每一列的狀態欄都要以封閉字彙開頭——否則 hook 判不出來（不綁今天哪一份是 active）。"""
    rows = hint._phase_rows((ROOT / "docs" / "plans" / "README.md").read_text(encoding="utf-8"))
    assert rows, "對照表解析不到任何一列"
    known = re.compile(r"^(active|completed|superseded)(?![A-Za-z_])|^—$")
    bad = [r for r in rows if not known.match(r["status"].strip())]
    assert not bad, bad
    assert sum(1 for r in rows if hint._is_active(r["status"])) <= 1


def test_next_step_prints_resume_pointer_and_executor_model(tmp_path, monkeypatch, capsys):
    """2026-10-07：hook 只印定義欄——7.1 定義寫的「InP 磊晶層說明（排第一件）」已做完，新 session 會照著重做；
    建議模型也一律寫「便宜」，可是 7.1 的執行者欄是強模型，便宜模型跑到研究 Step 就停下交回。"""
    plan = tmp_path / "plan.md"
    plan.write_text(
        "| Step | 內容 | 狀態 | 執行者 | commit |\n|---|---|---|---|---|\n"
        "| 7.0 | 開場 | ✅ | 執行模型 | x |\n"
        "| 7.1 | 研究：**舊的第一件**、積壓 | ○（已做：舊的第一件。**續工指標**：①新的第一件 ②第二件〔研究：強模型〕） | 強模型 | |\n"
        "| 7.2 | 回放 | ○ | 執行模型 | |\n", encoding="utf-8")
    msg = _run(tmp_path, monkeypatch, capsys, f"| 7 研究 | [p]({plan.as_posix()}) | active（2026-10-04） |\n")
    assert "續工：①新的第一件 ②第二件" in msg
    assert "舊的第一件" not in msg
    assert "建議模型：強模型" in msg
    # 沒有續工指標、執行者是執行模型時照舊：印定義、建議便宜
    plan.write_text(
        "| Step | 內容 | 狀態 | 執行者 | commit |\n|---|---|---|---|---|\n"
        "| 7.2 | 回放 | ○ | 執行模型 | |\n", encoding="utf-8")
    msg = _run(tmp_path, monkeypatch, capsys, f"| 7 研究 | [p]({plan.as_posix()}) | active |\n")
    assert "7.2（回放）" in msg and "建議模型：便宜" in msg
