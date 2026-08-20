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
CATALYST_CALENDAR = ROOT / "thesis" / "catalyst_calendar.json"


def _iter_entries(path, key: str | None = None):
    """兩個來源的 entry 形狀不同，在這裡收斂成同一個迭代器。"""
    if not path.is_file():
        return
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if key is not None:
        raw = raw.get(key) or []
    for entry in raw.values() if isinstance(raw, dict) else raw:
        if isinstance(entry, dict):
            yield entry


def _checkpoints_by_company() -> dict[str, list]:
    """把結構化催化劑接過來，以 ticker 對應到 cohort。

    兩個來源、刻意分開（2026-08-20）：
    - `thesis/lifecycle.json` 只涵蓋有 lane memo 的 thesis（目前 3 條）。
    - `thesis/catalyst_calendar.json` 涵蓋其餘 Engine D cohort。

    先前只讀前者，於是 11 檔裡只有 3 檔可做「`expiry` 早於催化劑」的結構化比對——
    IQE 那次假逾期（到期日被設在催化劑之前）就是靠人眼發現的，不是被這支腳本抓到。
    非 thesis 的 cohort **不能**塞進 lifecycle.json：該檔另有兩個消費者會把每個 entry
    當成一條 thesis，`thesis_freshness_check` 還會去找對應的 `*_lane_memo.md`。
    語意不同就分開存，兩邊共用同一支 `catalyst_checkpoints()` 正規化函式。
    """
    out: dict[str, list] = {}
    for path, key in ((LIFECYCLE, None), (CATALYST_CALENDAR, "entries")):
        for entry in _iter_entries(path, key):
            ticker = str(entry.get("ticker") or "")
            checkpoints = catalyst_checkpoints(entry)
            if ticker and checkpoints:
                out.setdefault(ticker, checkpoints)
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
