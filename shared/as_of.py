"""「T 時刻知道什麼」的唯一規則（INV-6；Phase 3 Step 3.2／3.3）。

財報類觀測每份申報各一列（同一期被後來的申報重編時兩列並存）。as-of T 的讀法只有一條：
**每個期末（period_end）取 `filed ≤ T` 的最新一列**；同一天申報兩份時以 accession 定序（決定論）。
`fetched_at`（我們哪天抓的）永遠不參與。

Engine C 的讀取端（`engine_c.history.fundamental_series`）與財務三題的逐日計算（`alpha.three_questions`）
都呼叫這一支——兩份實作的那天起，後改的那份就不會回頭改前一份（L16）。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def latest_known_by_period(rows: Sequence[Mapping[str, Any]], as_of: date | str) -> dict[date, Mapping[str, Any]]:
    """`{period_end: 那一期在 as_of 已知的最新一列}`。`filed` 或 `period_end` 解析不了的列不算（不猜日期）。"""
    t = _as_date(as_of)
    if t is None:
        raise ValueError(f"as_of 不是日期：{as_of!r}")
    best: dict[date, tuple[date, str, Mapping[str, Any]]] = {}
    for row in rows:
        filed, end = _as_date(row.get("filed")), _as_date(row.get("period_end"))
        if filed is None or end is None or filed > t:
            continue
        key = (filed, str(row.get("accession") or ""))
        prev = best.get(end)
        if prev is None or key > prev[:2]:
            best[end] = (filed, key[1], row)
    return {end: v[2] for end, v in best.items()}


__all__ = ["latest_known_by_period"]
