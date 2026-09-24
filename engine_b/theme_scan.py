"""題材掃描的「上次是什麼時候」（Phase 1 Step 1.8／1.9）——心跳段 3 與 SessionStart hook 共用。

weekly 退役之後，題材掃描只在互動 session 由使用者發起（`skills/theme-scan`）。沒有排程會提醒它，
所以「距上次掃題材 N 天」必須是一個**每天都印、會自己出現的計數器**（L14），而不是要人記得的事。

上次的日期取 `docs/reports/` 裡 `theme_scan_<日期>.md` 與舊的 `weekly_scan_<日期>.md` 檔名日期的最大值
（只認報告本體；`_<題目>.proposal.json` 這類附件不算）。一份都沒有 → `date=None`，呼叫端照實說「從沒掃過」，不當成 0。
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "docs" / "reports"
_REPORT = re.compile(r"^(?:theme_scan|weekly_scan)_(\d{4}-\d{2}-\d{2})\.md$")


def last_scan(*, reports_dir: Path = REPORTS_DIR, today: date | None = None) -> dict[str, Any]:
    """{"date": ISO 或 None, "days": 距今天數或 None, "file": 檔名或 None}。"""
    today = today or date.today()
    best: tuple[date, str] | None = None
    for path in (reports_dir.iterdir() if reports_dir.is_dir() else ()):
        match = _REPORT.match(path.name)
        if not match:
            continue
        try:
            when = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if best is None or when > best[0]:
            best = (when, path.name)
    if best is None:
        return {"date": None, "days": None, "file": None}
    return {"date": best[0].isoformat(), "days": (today - best[0]).days, "file": best[1]}


__all__ = ["REPORTS_DIR", "last_scan"]
