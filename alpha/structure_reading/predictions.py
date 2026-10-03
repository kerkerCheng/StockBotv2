"""圖預測對錯表（Phase 5 Step 5.4；plan §5）——**每一份讀圖斷言一個機械的終局**：對、錯（分種類）、改寫、現行、到期未重讀。

## 它回答什麼

AGENTS 量測段：「圖自己的預測也要量（讀圖說只有一家、半年後客戶 filing 列出第二家＝讀圖錯）」。
讀圖 ledger 只維護「讀圖跟圖還一不一致」（`contracts.py` 檔頭），**對不對**要靠這張表。

## 判定只來自兩種既有的人工紀錄（plan 不可越線 5；L15：程式只分類時間，不判對錯）

1. **讀圖 ledger 的 supersede 鏈**：研究 session 自己寫下的後繼（同 kind＝維持、不同 kind＝翻轉、撤回）；
2. **互動 session 判定反證觸及**（`watch.judgment.touches == "yes"`）。

staleness 的 `supply_added`、`documents` 增加、任何 LLM 判讀**都不是判定**——本模組刻意不吃 staleness 的輸入。

## 改寫不算對（5.0 實測修正，plan §0.6 #2）

`result_digest` 會因為**查詢程式改版**而變（需求走訪加 constrained_by、證據欄修正、反向路徑只收 competes_with），
不只因為圖變了。所以同 kind 的後繼必須**同一版 schema、帶來 r 沒引用過的來源**才算「圖有變」→ 對；否則是改寫。
`new_sources` 與「錯的種類」用同一支（一個 owner）。
① 同 `result_digest` 的後繼只有在**同 kind 或同一天**時算改寫（2026-10-03 Phase 6 Step 6.7d；使用者 10-02 原句「同 digest 的同日改寫」）：
圖沒變、隔天以後換了讀法＝讀法自己翻了 → reversed（錯）；同一天內換讀法是研究當下的更正 → 改寫。

## 錯的種類

新來源（或判觸及引用的文件）的 `published_at` 對舊讀圖的 `created_on`：早於＝`already_available`（當時已有反例，讀得不夠）；
全部晚於或同日＝`emerged_later`（之後才出現，判斷錯）；沒有新來源、沒日期、或日期精度跨過讀圖那一天＝`undated`。
只看 `published_at`，**不拿 retrieved_at／first_seen 冒充**（INV-6）。對照表讀不到（Neo4j 沒開）＝`upstream_unavailable`。

**只印不判、不排序、不設門檻**；它不 gate 任何東西。
"""
from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from .contracts import StructureReading

#: 會被判對錯的讀法（斷言）。`neither`／`undecided` 是母體、不判。
ASSERTION_KINDS = frozenset({"moat", "volume"})

#: 終局（封閉字彙，一份讀圖恰好一格）。中文給讀圖頁與心跳用。
OUTCOMES: Mapping[str, str] = {
    "held": "對：同讀法、圖有變（帶新來源）或已到期後重讀",
    "reversed": "錯：被不同讀法取代",
    "disproof_touched": "錯：反證被互動 session 判觸及",
    "retracted": "錯：撤回",
    "rewritten": "改寫：schema 升版、補引文、查法改版後重存、同一輪研究內補寫——不算對錯",
    "open": "現行",
    "expired_unread": "到期未重讀",
    "non_assertion": "非斷言（neither／undecided）——母體，不判",
}
WRONG_OUTCOMES: tuple[str, ...] = ("reversed", "disproof_touched", "retracted")

#: 「錯」的種類（封閉字彙）。
WRONG_KINDS: Mapping[str, str] = {
    "already_available": "當時已有反例（讀得不夠）",
    "emerged_later": "之後才出現（判斷錯）",
    "undated": "未定日",
    "upstream_unavailable": "日期對照表讀不到（不是未定日）",
}


def _date_bounds(text: Any) -> tuple[date, date] | None:
    """`published_at` → （最早可能、最晚可能）。完整日期兩端相同；只有年月＝那個月的第一天到最後一天；讀不懂回 None。"""
    if not text:
        return None
    raw = str(text).strip()
    try:
        day = date.fromisoformat(raw[:10])
        return day, day
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{4})-(\d{2})", raw[:7]) if len(raw) >= 7 else None
    if not match:
        return None
    year, month = int(match[1]), int(match[2])
    if not 1 <= month <= 12:
        return None
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def timing_kind(published: Iterable[Any], *, created_on: date) -> str:
    """一組反例文件的日期 → 錯的種類。任一份**最晚可能**早於讀圖那天＝`already_available`；全部**最早可能**不早於＝
    `emerged_later`；其餘（沒有文件、有一份沒日期、精度跨過那一天）＝`undated`——不猜。"""
    bounds = [_date_bounds(p) for p in published]
    if not bounds:
        return "undated"
    if any(b is not None and b[1] < created_on for b in bounds):
        return "already_available"
    if all(b is not None and b[0] >= created_on for b in bounds):
        return "emerged_later"
    return "undated"


def new_sources(successor: StructureReading, reading: StructureReading) -> list[str]:
    """後繼帶來、前一份沒引用過的來源（SourceDoc id）。v1／v2 沒有引用欄，兩邊皆空。"""
    before = {c.source_id for c in reading.citations}
    return sorted({c.source_id for c in successor.citations} - before)


def _successor(reading: StructureReading, records: Sequence[StructureReading]) -> tuple[StructureReading | None, int]:
    """`supersedes_id` 指向它的紀錄；有多筆（分岔）取最早那筆，並回分岔數讓呈現端印出來。"""
    hits = sorted((r for r in records if r.supersedes_id == reading.reading_id),
                  key=lambda r: (r.created_at, r.reading_id))
    return (hits[0] if hits else None), len(hits)


def _touched(reading: StructureReading, watches: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """這份讀圖登記的語意 watch 裡，被互動 session 判觸及的（**單數** `judgment`、`touches == "yes"`；
    判無關寫在複數 `judgments`，不算）。`source_ref` 的格式是 `reading:<id>#<第幾條>`。"""
    prefix = f"reading:{reading.reading_id}"
    out = []
    for watch in watches:
        ref = str(watch.get("source_ref") or "")
        if watch.get("kind") != "semantic_condition" or not (ref == prefix or ref.startswith(prefix + "#")):
            continue
        judgment = watch.get("judgment") if isinstance(watch.get("judgment"), Mapping) else None
        if judgment and judgment.get("touches") == "yes":
            out.append(watch)
    return out


def prediction_rows(records_by_node: Mapping[str, Sequence[StructureReading]], *, today: date,
                    watches: Sequence[Mapping[str, Any]] = (),
                    source_published: Mapping[str, Any] | None = None,
                    lead_published: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """讀圖 ledger（每個節點的**全部**紀錄，含撤回）＋語意 watch＋兩張日期對照表 → 逐筆終局與計數。**純函式**。

    `source_published`：SourceDoc id → `published_at`（`None`＝這次讀不到圖，錯的種類整段 `upstream_unavailable`，
    終局照算）。`lead_published`：lead id → `published_at`（判觸及引用的文件；`None`＝lead registry 讀不到）。
    """
    rows: list[dict[str, Any]] = []
    markers = 0
    for node in sorted(records_by_node):
        records = list(records_by_node[node])
        for reading in sorted(records, key=lambda r: (r.created_at, r.reading_id)):
            if reading.retracted:
                markers += 1                          # 撤回紀錄是標記，不是一份讀圖；「錯」記在被撤回的那一份上
                continue
            rows.append(_row(reading, records, today=today, watches=watches,
                             source_published=source_published, lead_published=lead_published))
    counts: dict[str, Any] = {key: 0 for key in OUTCOMES}
    for outcome in WRONG_OUTCOMES:
        counts[outcome] = {kind: 0 for kind in WRONG_KINDS}
    for row in rows:
        if row["outcome"] in WRONG_OUTCOMES:
            counts[row["outcome"]][row["wrong_kind"]] += 1
        else:
            counts[row["outcome"]] += 1
    open_expiries = [row["expires"] for row in rows if row["outcome"] == "open"]
    return {
        "rows": rows,
        "counts": counts,
        "wrong_total": sum(sum(counts[o].values()) for o in WRONG_OUTCOMES),
        "retraction_markers": markers,
        "earliest_open_expiry": min(open_expiries) if open_expiries else None,
    }


def _row(reading: StructureReading, records: Sequence[StructureReading], *, today: date,
         watches: Sequence[Mapping[str, Any]], source_published: Mapping[str, Any] | None,
         lead_published: Mapping[str, Any] | None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "node": reading.node, "unit": reading.unit, "reading_id": reading.reading_id, "kind": reading.kind,
        "record_version": reading.record_version, "created_on": reading.created_on.isoformat(),
        "expires": reading.expires.isoformat(), "outcome": None, "wrong_kind": None, "basis": None,
        "evidence": [], "branches": 0,
    }
    if reading.kind not in ASSERTION_KINDS:
        row["outcome"] = "non_assertion"
        return row
    successor, branches = _successor(reading, records)
    row["branches"] = branches
    if successor is not None:
        row["basis"] = successor.reading_id
        fresh = new_sources(successor, reading)
        row["evidence"] = [{"source_id": s, "published_at": (source_published or {}).get(s)} for s in fresh]
        if successor.retracted:
            row["outcome"] = "retracted"
        elif successor.created_on > reading.expires:
            # 到期之後才重讀：同讀法＝對（已到期＝對，定案 #3）、不同讀法＝錯；不再問 digest 或新來源
            row["outcome"] = "held" if successor.kind == reading.kind else "reversed"
        elif successor.result_digest == reading.result_digest and (
                successor.kind == reading.kind or successor.created_on == reading.created_on):
            # ①（Phase 6 Step 6.7d；使用者 10-02 原句「同 digest 的同日改寫」）：圖一樣、讀法也一樣，或同一天內改寫＝改寫；
            # 圖一樣、隔天以後卻換了讀法——沒有新的圖可以怪，是讀法自己翻了——不在這裡收，落到下面的 reversed
            row["outcome"] = "rewritten"
        elif successor.kind == reading.kind:
            # 同讀法：只有同一版 schema、帶來新來源才算「圖有變」（5.0 修正）；否則查法改版或補寫＝改寫
            same_version = successor.record_version == reading.record_version
            row["outcome"] = "held" if (same_version and fresh) else "rewritten"
        else:
            row["outcome"] = "reversed"
        if row["outcome"] in WRONG_OUTCOMES:
            row["wrong_kind"] = ("upstream_unavailable" if source_published is None
                                 else timing_kind([e["published_at"] for e in row["evidence"]],
                                                  created_on=reading.created_on))
        return row
    touched = _touched(reading, watches)
    if touched:
        row["outcome"] = "disproof_touched"
        row["basis"] = touched[0].get("watch_id")
        leads = [str((w.get("judgment") or {}).get("lead_id") or "") for w in touched]
        if lead_published is None:
            row["wrong_kind"] = "upstream_unavailable"
        else:
            row["evidence"] = [{"lead_id": lead or None, "published_at": lead_published.get(lead) if lead else None}
                               for lead in leads]
            row["wrong_kind"] = timing_kind([e["published_at"] for e in row["evidence"]],
                                            created_on=reading.created_on)
        return row
    row["outcome"] = "expired_unread" if reading.is_expired(today) else "open"
    return row


__all__ = ["ASSERTION_KINDS", "OUTCOMES", "WRONG_KINDS", "WRONG_OUTCOMES", "new_sources", "prediction_rows",
           "timing_kind"]
