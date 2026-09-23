"""Daily 的 pane renderer——只剩備份計數器。

⚠ 2026-09-23（Phase 0 Step 0b.4）：`render_today_markdown`（decision brief 的 Markdown 組裝：items／
live entry／capital expression／identity alignment）隨 decision_lab 研究側與 today brief 退役。
Alpha Card／NAV／position events／outcome aggregate 的 renderer 各自留在它們的 domain
（`briefing/alpha_view/render.py`、`portfolio/brief.py`、`alpha/brief.py`），目前沒有組裝端消費
——Phase 1 心跳要不要接是待決問題（見 Phase 0 closeout 報告）。

`render_backup_status` 留下：它是「從未備份」「狀態檔壞掉」「備份後新增的 authority 檔」三種紅燈的
唯一渲染器（L12／L14），由 `briefing.sources.load_backup_status` 供料。
"""
from __future__ import annotations

from typing import Any, Mapping

from shared.markdown import markdown_text

__all__ = ["render_backup_status"]


def render_backup_status(backup: Mapping[str, Any] | None) -> list[str]:
    """備份計數器：「從未備份」與「狀態檔壞掉」都必須現形，不得靜默（L12／L14）。

    `None`（surface 不提供）→ 整段略過，不與「從未備份」混用。
    """
    if not backup:
        return []
    backup_state = str(backup.get("status") or "")
    if backup_state == "never":
        return ["- 🔴 最後一次備份：從未備份——跑 `python scripts/backup_private.py run`"]
    if backup_state == "invalid":
        return [
            "- 🔴 最後一次備份：狀態檔無法解讀（library/private/backups/"
            "last_backup.json），視同沒有備份處理"
        ]
    age = int(backup.get("age_days") or 0)
    drive_status = str(backup.get("drive_status") or "unknown")
    notes = [
        "Drive ✓" if drive_status == "uploaded" else f"Drive 🔴 {markdown_text(drive_status)}",
        "restore 已驗證" if backup.get("restore_verified") else "restore 🔴 未驗證",
    ]
    unbacked = int(backup.get("unbacked_files") or 0)
    if unbacked:
        sample = "、".join(markdown_text(x) for x in (backup.get("unbacked_sample") or []))
        notes.append(f"🔴 {unbacked} 個 private authority 檔不在這份備份裡"
                     + (f"（例：{sample}）" if sample else ""))
    marker = "🔴 " if age > 7 or drive_status != "uploaded" or unbacked else ""
    return [f"- {marker}最後一次備份：{age} 天前（{'，'.join(notes)}）"]
