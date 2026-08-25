"""賣出側每日檢查（唯讀）：證偽條件與催化劑今天到了沒。

不寫任何 authority。用法：
    python scripts/catalyst_watch.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from decision_lab.catalyst_watch import build_watchlist, render_markdown  # noqa: E402
from thesis.lifecycle_schedule import checkpoints_by_ticker  # noqa: E402

DECISION_DB = ROOT / "library" / "private" / "decision_lab" / "decision_lab.db"


def main() -> int:
    if not DECISION_DB.is_file():
        print(f"找不到 Decision Store：{DECISION_DB}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(f"file:{DECISION_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        by_ticker = checkpoints_by_ticker()
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
        if covered < len(rows):
            print(
                f"\n---\n⚠ **{covered}/{len(rows)} 檔有結構化催化劑日期。**"
                " 其餘只有散文 catalyst，`expiry 早於催化劑` 這類錯誤在它們身上**測不到**"
                "——沒抓到問題不等於沒有問題（L13）。"
                "\n補法：有 lane memo 的 thesis 加進 `thesis/lifecycle.json`；"
                "其餘 Engine D cohort 加進 `thesis/catalyst_calendar.json`"
                "（兩者的 `catalyst_checkpoints` 欄位相同）。"
            )
        else:
            print(
                f"\n---\n✅ **{covered}/{len(rows)} 檔都有結構化催化劑日期**，"
                "`expiry 早於催化劑` 這類錯誤現在每檔都測得到。"
                "\n⚠ 但**沒抓到問題不等於沒有問題**（L13）：標「推估」的日期來自 provider"
                " earnings calendar 或散文推算，公司正式公告後應更新為 `confirmed`。"
            )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
