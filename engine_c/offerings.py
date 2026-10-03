"""募資文件——稀釋燈的判色依據（Phase 6 Step 6.6；使用者定案 plan 2026-10-02-002 §0.1 #9）。

## 為什麼

稀釋燈原本只看 companyfacts 的新股發行金額（`us-gaap:StockIssuedDuringPeriodValueNewIssues`）：2026-10-02 黃燈 11 檔裡，
NVDA／MRVL／LRCX／META／INTC 的發行額不到市值 0.15%——員工計畫等級的數字也會亮。金額 > 0 同時承載「靠發股補錢」與
「員工計畫配股」（L12）。修法是再要一個**只在真的募資時才存在**的輸入：窗內有一份募資文件。

## 封閉清單（判定只有 `is_offering_filing` 一處；`engine_c.checklist._equity_issuance` → `alpha.wipeout.dilution_flag` 一條路）

- **算募資**：`424B1`–`424B5`、`424B7`（公開說明書補充）、`S-1`／`S-1/A`、`F-1`／`F-1/A`（首次登記）、
  `8-K`／`8-K/A` 且項目含 **3.02**（未註冊股權出售＝私募；COHR 對 NVIDIA 的 20 億美元、LITE 的可轉換特別股都是這個）。
- **不算、但存下來印給人看**（`CONTEXT_FORMS`）：`S-8`（員工計畫）、`S-3`／`F-3`／`S-3ASR`（只是授權——授權另有人工欄位
  `equity_issuance_authorizations`，照舊只印）。
- ⚠ 已知限制（2026-10-03 手核）：`424B2`／`424B5` 也用來發**公司債**（NVDA 2026-06 的 424B5 是七檔 Notes、META 2026-04 的
  424B2 是優先票據）。submissions JSON 沒有任何欄位分得出股權或債，分要多抓文件本身——plan 要求 daily 的請求數不變，
  所以本模組**照清單算**、把配到的文件逐份印出（form、日期、accession），讀的人點得回原文；要不要再分，是使用者的題
  （plan §14）。

## 時間語意（INV-6）

- 申報日用 EDGAR 的 `filingDate`（`filed`），不是抓取日；文件是歷史紀錄、申報日不會改，所以 as-of T 只取 `filed ≤ T` 的。
- submissions 的 `recent` 只保證最近約一年或 1000 筆：每次抓取記下清單裡**最早**的申報日（`coverage_from`）。窗的起點早於它、
  或最後一次抓取早於窗尾——窗內「沒找到」就不是「沒有」，消費端照實說涵蓋不到（不判綠也不判黃）。

## 兩張表（可重建的 ETL 觀測：今天重抓一次拿得回來——L10）

- `equity_offering_filings`：每份申報一列（accession 主鍵）；只存清單上的表單（算募資的＋`CONTEXT_FORMS`）。
  **不存判定**——判定在讀取端（`is_offering_filing`），清單改了不必重抓。
- `equity_offering_checks`：每檔最後一次抓 submissions 的時間、涵蓋起點、清單筆數——「抓過、沒有」與「沒抓過」不得同形（L12）。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping, Sequence

#: 算募資的表單（8-K 另由項目 3.02 判）。
OFFERING_FORMS: frozenset[str] = frozenset({
    "424B1", "424B2", "424B3", "424B4", "424B5", "424B7", "S-1", "S-1/A", "F-1", "F-1/A",
})
#: 8-K 要含這個項目才算（未註冊股權出售）。
OFFERING_8K_FORMS: frozenset[str] = frozenset({"8-K", "8-K/A"})
OFFERING_8K_ITEM = "3.02"
#: 不算募資、但存下來給稽核區印「窗內只有這些」：員工計畫與 shelf 授權。
CONTEXT_FORMS: frozenset[str] = frozenset({
    "S-8", "S-8 POS", "S-3", "S-3/A", "S-3ASR", "S-3MEF", "F-3", "F-3/A", "F-3ASR",
})

SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS equity_offering_filings (
    accession TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    cik TEXT NOT NULL,
    form TEXT NOT NULL,
    items TEXT,
    filed TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_equity_offering_filings_ticker
    ON equity_offering_filings (ticker, filed);
CREATE TABLE IF NOT EXISTS equity_offering_checks (
    ticker TEXT PRIMARY KEY,
    cik TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    coverage_from TEXT,
    recent_count INTEGER NOT NULL
);
"""


def ensure_offering_schema(conn: Any) -> None:
    """非破壞性建表（SQLite）：只 CREATE IF NOT EXISTS，**不動任何既有表**（plan：不改 Engine C 既有表的 CHECK）。"""
    conn.executescript(SQLITE_DDL)


def _items(items: str | None) -> set[str]:
    return {part.strip() for part in str(items or "").split(",") if part.strip()}


def is_offering_filing(form: str | None, items: str | None = None) -> bool:
    """這份申報算不算募資文件——**唯一判定**（清單見檔頭）。"""
    name = str(form or "").strip().upper()
    if name in OFFERING_FORMS:
        return True
    return name in OFFERING_8K_FORMS and OFFERING_8K_ITEM in _items(items)


def is_stored_form(form: str | None, items: str | None = None) -> bool:
    """要不要存進 `equity_offering_filings`：算募資的，或 `CONTEXT_FORMS`（員工計畫、shelf）。"""
    return is_offering_filing(form, items) or str(form or "").strip().upper() in CONTEXT_FORMS


def offering_rows(filings: Iterable[Mapping[str, Any]], *, ticker: str, cik: str, fetched_at: str) -> list[dict]:
    """`fetchers.edgar.recent_filings` 的輸出 → 要存的列（純函式）。"""
    rows = []
    for f in filings:
        if not is_stored_form(f.get("form_type"), f.get("items")):
            continue
        rows.append({"accession": str(f.get("accession_dashed") or f.get("accession")), "ticker": ticker,
                     "cik": cik, "form": str(f.get("form_type")), "items": str(f.get("items") or ""),
                     "filed": str(f.get("filed_date")), "fetched_at": fetched_at})
    return rows


def coverage_from(filings: Sequence[Mapping[str, Any]]) -> str | None:
    """這份清單涵蓋到哪一天（`recent` 裡最早的申報日）；空清單＝None。"""
    dates = sorted(str(f.get("filed_date")) for f in filings if f.get("filed_date"))
    return dates[0] if dates else None


def store_offerings(conn: Any, filings: Sequence[Mapping[str, Any]], *, ticker: str, cik: str,
                    fetched_at: str) -> int:
    """一次抓取的結果寫進兩張表（同一個 transaction 由呼叫端 commit）；回寫入（含更新）的申報列數。

    表由開庫時建（`engine_c.db._ensure_sqlite_schema` → `ensure_offering_schema`）；這裡不再 `executescript`——
    它會隱式 commit 呼叫端還沒完成的 transaction。"""
    rows = offering_rows(filings, ticker=ticker, cik=cik, fetched_at=fetched_at)
    conn.executemany(
        "INSERT OR REPLACE INTO equity_offering_filings (accession, ticker, cik, form, items, filed, fetched_at) "
        "VALUES (:accession, :ticker, :cik, :form, :items, :filed, :fetched_at)", rows)
    conn.execute(
        "INSERT OR REPLACE INTO equity_offering_checks (ticker, cik, checked_at, coverage_from, recent_count) "
        "VALUES (?, ?, ?, ?, ?)", (ticker, cik, fetched_at, coverage_from(filings), len(filings)))
    return len(rows)


def offerings_in_window(conn: Any, ticker: str, *, start: date, end: date, today: date) -> dict[str, Any]:
    """窗 [start, end]（且 `filed ≤ today`）內的募資文件與不算募資的登記表單；涵蓋不到窗就照實說。

    回：`status`＝`ok`／`upstream_unavailable`（表不存在或從沒抓過）；`complete`＝這次抓取涵蓋得到整個窗
    （`coverage_from ≤ start` 且最後一次抓取不早於 `end`）；`documents`／`context` 逐份帶 form、filed、accession、items。
    """
    import sqlite3

    window = {"start": start.isoformat(), "end": end.isoformat()}
    try:
        check = conn.execute(
            "SELECT checked_at, coverage_from, recent_count FROM equity_offering_checks WHERE ticker = ?",
            (ticker,)).fetchone()
        rows = conn.execute(
            "SELECT form, items, filed, accession FROM equity_offering_filings "
            "WHERE ticker = ? AND filed >= ? AND filed <= ? AND filed <= ? ORDER BY filed, accession",
            (ticker, start.isoformat(), end.isoformat(), today.isoformat())).fetchall()
    except sqlite3.OperationalError:
        return {"status": "upstream_unavailable", "window": window,
                "reason": "募資文件表不存在（舊庫）——跑一次 daily 的 EDGAR 增量或 python -m engine_c.history_backfill --incremental"}
    if check is None:
        return {"status": "upstream_unavailable", "window": window,
                "reason": "這一檔還沒抓過 EDGAR 申報清單（daily 的 EDGAR 增量在有既存財報列時才抓）"}
    checked_at, covered_from, recent_count = check
    docs = [{"form": f, "items": i or "", "filed": d, "accession": a} for f, i, d, a in rows]
    gaps = []
    if covered_from and covered_from > start.isoformat():
        gaps.append(f"申報清單只涵蓋到 {covered_from}（submissions 的 recent 只給最近約 1000 筆），窗起點 {start.isoformat()} 更早")
    if str(checked_at)[:10] < end.isoformat():
        gaps.append(f"最後一次抓清單是 {str(checked_at)[:10]}，早於窗尾 {end.isoformat()}")
    return {"status": "ok", "window": window, "checked_at": checked_at, "coverage_from": covered_from,
            "recent_count": recent_count, "complete": not gaps, "gaps": gaps,
            "documents": [d for d in docs if is_offering_filing(d["form"], d["items"])],
            "context": [d for d in docs if not is_offering_filing(d["form"], d["items"])]}


__all__ = ["CONTEXT_FORMS", "OFFERING_8K_FORMS", "OFFERING_8K_ITEM", "OFFERING_FORMS", "coverage_from",
           "ensure_offering_schema", "is_offering_filing", "is_stored_form", "offering_rows", "offerings_in_window",
           "store_offerings"]
