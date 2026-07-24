"""
thesis_freshness_check.py — SessionStart hook: 提醒哪些 thesis 距上次核查已超過 90 天。

只讀本機 thesis/*_lane_memo.md，不碰 Neo4j / Engine C（見 U8 修訂設計，
docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md）。
完整核查（讀 disproof_condition → WebSearch → engine_c/checklist.py）由使用者
在對話中觸發，本 script 只負責「該不該現在問」。

日期來源優先序：
1. 檔案內 "**生成日期：** YYYY-MM-DD" 一行（新格式 Lane Memo 都有）
2. 沒有的話退回檔案 mtime（舊格式 Lane Memo，如 v1 檔案）

同一家公司多個版本（*_v1_*, *_v2_*）只取最新日期，不重複提醒。
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THESIS_DIR = ROOT / "thesis"
STALE_DAYS = 90

DATE_RE = re.compile(r"生成日期[:：]\s*(\d{4}-\d{2}-\d{2})")
COMPANY_RE = re.compile(r"^(?P<company>.+?)_v\d+_lane_memo$")


def _file_date(path: Path) -> date:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = DATE_RE.search(text)
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    return datetime.fromtimestamp(path.stat().st_mtime).date()


def check() -> list[tuple[str, int]]:
    """回傳 [(company, days_since), ...]，只含超過 STALE_DAYS 的公司。"""
    latest_by_company: dict[str, date] = {}

    for path in sorted(THESIS_DIR.glob("*_lane_memo.md")):
        m = COMPANY_RE.match(path.stem)
        company = m.group("company") if m else path.stem
        d = _file_date(path)
        if company not in latest_by_company or d > latest_by_company[company]:
            latest_by_company[company] = d

    today = date.today()
    stale = []
    for company, d in latest_by_company.items():
        days = (today - d).days
        if days > STALE_DAYS:
            stale.append((company, days))

    return sorted(stale, key=lambda x: -x[1])


LIFECYCLE = ROOT / "thesis" / "lifecycle.json"


def lifecycle_due() -> list[tuple[str, str]]:
    """讀 lifecycle.json，回 [(thesis_id, 原因)]——到期（next_check<=今天）或
    review_required。這是 lifecycle 的權威到期訊號（memo 檔日期只是次要 fallback）。

    lifecycle 的正式狀態更新（disproof 評估、retired/revised）需人工判斷，本 hook
    只 surface 到期供你本機手動複查（plan R17）；不寫入。
    """
    try:
        data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    today = date.today()
    due: list[tuple[str, str]] = []
    for tid, entry in (data.items() if isinstance(data, dict) else []):
        if not isinstance(entry, dict):
            continue
        if entry.get("status") == "review_required":
            due.append((tid, "review_required"))
            continue
        nc = entry.get("next_check")
        try:
            if nc and date.fromisoformat(str(nc)) <= today:
                due.append((tid, f"到期 {nc}"))
        except ValueError:
            continue
    return due


def main() -> int:
    stale = check()
    due = lifecycle_due()
    if not stale and not due:
        return 0  # 都新鮮，安靜過去，不輸出任何東西

    segments = []
    if due:
        parts = ", ".join(f"{tid}（{why}）" for tid, why in due)
        segments.append(f"⛔ lifecycle 到期複查：{parts}")
    if stale:
        parts = ", ".join(f"{company} {days}天" for company, days in stale)
        segments.append(f"📋 memo 已超過 {STALE_DAYS} 天未核查：{parts}")
    msg = "thesis-monitor: " + "；".join(segments) + " — 要現在複查嗎？"
    # 雙通道：systemMessage 只給終端 UI；additionalContext 進 agent context，
    # 讓 agent 在任何介面（含手機 App 遙控、cloud session）都能主動轉述。
    print(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "【session 待辦摘要——請在你給使用者的第一則回覆開頭轉述】" + msg
            ),
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
