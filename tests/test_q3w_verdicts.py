"""Q3W 裁決常駐計數器（整體盲點審查 2026-11-01 §2 D；plan 2026-11-02-001 §1 第 1 條）。

鎖四件事：①到點日照名單規則 2（候選 watch 的 until；沒有 watch 才看裁決點欄）②已寫只認「### 裁決（」段的行——
「### 裁決點來源」也是「### 裁決」開頭，第一版就數錯成 0 ③全部到點且寫完就不印（出口）④讀不到說讀不到、不印 0（INV-3）。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from crons import q3w_verdicts as q3w

CASES = """# Phase 7 case 表

## O1 AXTI
- 裁決：（尚無）
  - 2026-11-03｜AXTI｜這一行在 O1 段，不算 Q3W

## Q3W Q3 財報季窗內名單

- 窗：2026-10-21～2026-11-30（含兩端）。

### 名單（4）

| # | ticker | 名稱 | 宣告狀態（板上分組） | 凍結的敘事 | 裁決點 | 來源 | 候選 watch（until） | 凍結時已觸發未檢 |
|---|---|---|---|---|---|---|---|---|
| 1 | 002270.SZ | 華明裝備 | 缺 X | `ib_x`（10-20） | Q3 季報 10-27（預約；法定 10-31） | [b] | `ew_0435`（10-31）；另 `ew_1339`（12-24，窗外） | — |
| 2 | AXTI | AXT | 已定價等回落 | `ib_y`（10-20） | Q3 財報 10-29 盤後 | [a] | `ew_0148`（11-13）；另 `ew_1433`（10-31） | — |
| 3 | COHR | Coherent | 不要 | `ib_z`（10-20） | FY27 Q1 財報 11-04 盤後（12-01 在窗外） | [f] | —（不要，沒有候選 watch） | — |
| 4 | 1802.TW | 台玻 | 缺 X | `ib_w`（10-20） | 同上 | [m] | `ew_0978`（11-16） | — |

### 裁決點來源

- [a] 2026-10-01｜AXTI｜這一行在裁決點來源段，不算已寫

### 裁決（逐檔 append：日期｜ticker｜文件｜新版 `ib_*` 或不換版理由｜「錯」的 kind）

- （尚無）
- 2026-10-31｜002270.SZ｜三季報｜新版 `ib_a`｜錯：無
- 2026-10-30｜AXTI｜新聞稿｜新版 `ib_b`｜錯：無
- 2026-11-05｜LITE｜名單外的層證據，不算名單的已寫

### 2×2

- （尚無）
"""


def test_due_dates_follow_registration_rule_two_and_fall_back_to_the_event_column() -> None:
    counts = q3w.parse(CASES)
    assert [(r.ticker, r.due) for r in counts.rows] == [
        ("002270.SZ", date(2026, 10, 31)),     # 候選 watch 欄的第一個日期，不是窗外那一筆
        ("AXTI", date(2026, 11, 13)),          # 規則 2：watch 的 until，不是財報日 10-29
        ("COHR", date(2026, 11, 4)),           # 沒有候選 watch → 裁決點欄的第一個日期
        ("1802.TW", date(2026, 11, 16)),
    ]
    assert counts.written == {"002270.SZ", "AXTI"}  # O1 段與裁決點來源段的行都不算


def test_the_line_names_every_due_row_that_has_no_verdict() -> None:
    assert q3w.status_lines(date(2026, 11, 3), path=_write(CASES)) == ["Q3W 裁決：到點 1／4｜已寫 2"]
    line = q3w.status_lines(date(2026, 11, 14), path=_write(CASES))[0]
    assert line.startswith("Q3W 裁決：到點 3／4｜已寫 2｜**到點未寫 1：COHR**")


def test_the_line_disappears_once_every_row_is_due_and_written() -> None:
    done = CASES.replace("- 2026-10-30｜AXTI｜", "- 2026-11-05｜COHR｜財報｜不換版｜錯：無\n"
                                                 "- 2026-11-16｜1802.TW｜財報｜新版｜錯：無\n- 2026-10-30｜AXTI｜")
    assert q3w.status_lines(date(2026, 11, 20), path=_write(done)) == []
    assert q3w.status_lines(date(2026, 11, 10), path=_write(done))[0].startswith("Q3W 裁決：到點 2／4｜已寫 4")


def test_unreadable_is_said_not_printed_as_zero(tmp_path) -> None:
    assert q3w.status_lines(date(2026, 11, 3), path=tmp_path / "gone.md")[0].startswith("Q3W 裁決：讀不到")
    no_section = tmp_path / "cases.md"
    no_section.write_text("# 只有別的段\n", encoding="utf-8")
    assert q3w.status_lines(date(2026, 11, 3), path=no_section) == ["Q3W 裁決：讀不到（cases.md 沒有 Q3W 段）"]


def test_the_frozen_list_in_the_repo_still_parses() -> None:
    """名單 2026-10-21 凍結 28 列；cases.md 改版若讓解析失效，心跳只會印讀不到——這裡先紅。"""
    counts = q3w.parse(q3w.CASES_PATH.read_text(encoding="utf-8"))
    assert len(counts.rows) == 28 and not counts.undated()
    assert {"002428.SZ", "002270.SZ", "300395.SZ", "AXTI", "LYC.AX"} <= counts.written   # 11-03 回填的五列


def test_the_short_brief_status_block_prints_the_line(tmp_path, monkeypatch) -> None:
    from crons import daily_brief
    from crons import heartbeat as hb

    monkeypatch.setattr(hb, "watch_today_counts", lambda **_kw: {"woken": 0, "expired": 0, "semantic_flagged": 0})
    monkeypatch.setattr(hb, "quota_entries", lambda rows, now: [])
    monkeypatch.setattr(q3w, "status_lines", lambda today: [f"Q3W 裁決：到點 1／4｜已寫 0｜**到點未寫 1：X**（{today}）"])
    leads_path = tmp_path / "pending_leads.json"
    leads_path.write_text(json.dumps({"leads": {}, "harvest_log": []}), encoding="utf-8")
    text = daily_brief.compose_brief(now=datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc), summary="Daily 2026-11-03｜球在你 0",
                                     snapshot={}, run_record_path=tmp_path / "missing.json", leads_path=leads_path,
                                     heartbeat_dir=tmp_path)
    block = text.split("### ④ 狀態與健康度", 1)[1].split("### ⑤", 1)[0]
    assert "- Q3W 裁決：到點 1／4｜已寫 0｜**到點未寫 1：X**（2026-11-03）" in block


def _write(text: str):
    import tempfile
    from pathlib import Path

    path = Path(tempfile.mkdtemp()) / "cases.md"
    path.write_text(text, encoding="utf-8")
    return path
