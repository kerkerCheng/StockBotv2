"""pending_leads_digest.py — SessionStart hook：開 session 時提示待判斷 leads。

沿用 crons/weekly_scan_digest.py 的雙通道模式：systemMessage 給終端 UI、
additionalContext 進 agent context（讓手機 App 遙控與 cloud session 也能轉述）。
安靜原則：沒有 pending／triaged_go 就不輸出，不打擾。gh/檔案缺失都優雅跳過，
不能讓 session 開不起來。

計數只讀本機 library/leads/pending_leads.json（tracked，本機 authority）；
不 harvest、不寫入。完整 brief 由使用者說「daily brief」或 /daily-brief 觸發。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _counts() -> dict[str, int]:
    try:
        from engine_b import leads

        store = leads.load()
        return leads.status_counts(store)
    except Exception:
        return {}


def main() -> int:
    counts = _counts()
    pending = counts.get("pending", 0)
    triaged_go = counts.get("triaged_go", 0)
    if not pending and not triaged_go:
        return 0  # 沒有待判斷，安靜過去

    parts = []
    if pending:
        parts.append(f"{pending} 條待判斷")
    if triaged_go:
        parts.append(f"{triaged_go} 條 triaged_go 待深挖／入庫")
    msg = "🗞 pending leads：" + "、".join(parts) + "（說「daily brief」看完整今日摘要）"
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
