"""賣出側每日檢查（唯讀）：證偽條件與催化劑今天到了沒。

不寫任何 authority。用法：
    python scripts/catalyst_watch.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from decision_lab.catalyst_watch import build_watchlist, render_markdown  # noqa: E402
from thesis.lifecycle_schedule import catalyst_checkpoints  # noqa: E402

DECISION_DB = ROOT / "library" / "private" / "decision_lab" / "decision_lab.db"
LIFECYCLE = ROOT / "thesis" / "lifecycle.json"


def _checkpoints_by_company() -> dict[str, list]:
    """把 lifecycle 的結構化催化劑接過來，以 ticker 對應到 cohort。

    ⚠ lifecycle 只有 3 條 thesis，對不上的 cohort 就沒有結構化催化劑可比——
    那正是 `expiry` 早於催化劑這類錯誤在多數 cohort 上**測不到**的原因。
    這個限制必須顯示出來，不能讓「沒抓到問題」看起來像「沒有問題」（L13）。
    """
    if not LIFECYCLE.is_file():
        return {}
    raw = json.loads(LIFECYCLE.read_text(encoding="utf-8-sig"))
    out: dict[str, list] = {}
    for entry in raw.values() if isinstance(raw, dict) else raw:
        if not isinstance(entry, dict):
            continue
        ticker = str(entry.get("ticker") or "")
        checkpoints = catalyst_checkpoints(entry)
        if ticker and checkpoints:
            out[ticker] = checkpoints
    return out


def main() -> int:
    if not DECISION_DB.is_file():
        print(f"找不到 Decision Store：{DECISION_DB}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(f"file:{DECISION_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        by_ticker = _checkpoints_by_company()
        rows = build_watchlist(conn)
        # cohort 以 company_id 為鍵，lifecycle 以 ticker——在這裡對接。
        by_company = {}
        for row in rows:
            ticker = row.get("ticker")
            if ticker and ticker in by_ticker:
                by_company[str(row["company_id"])] = by_ticker[ticker]
        rows = build_watchlist(conn, checkpoints_by_company=by_company)
        print("\n".join(render_markdown(rows)).lstrip())
        covered = sum(1 for r in rows if r["next_catalyst"])
        print(
            f"\n---\n⚠ **{covered}/{len(rows)} 檔有結構化催化劑日期。**"
            " 其餘只有散文 catalyst，`expiry 早於催化劑` 這類錯誤在它們身上**測不到**"
            "——沒抓到問題不等於沒有問題（L13）。"
            "\n補法：在 `thesis/lifecycle.json` 的該條目加 `catalyst_checkpoints`"
            "（含 `date`／`date_confidence`）。"
        )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
