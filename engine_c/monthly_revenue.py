"""
monthly_revenue.py — 台股每月營收：Engine C 的一手時變觀測（ROADMAP Phase 6 / D15）。

**為什麼它住 Engine C 而不是圖：** 月營收是帶時戳的財務數字，A1 不含時變數字（L4 第二問）。

**為什麼它是 ETL 表而不是 append-only ledger：** 依 L10 的判準——「這筆資料今天重新取
一次拿得回來嗎？」——拿得回來（MOPS 的歷史頁按年月永久可查），所以它與
`financial_snapshots`／`technical_observations` 同類：可重建、零核准、**不是** pq2 的
judgment ledger。寫入端是 `fetchers/mops_open_data.py`，不經 LLM。

**三個單位／時間語意，寫死在表上而不是靠人記得：**

- `unit_scale = 1000`：MOPS 的數字是**新台幣千元**。差 1000 倍的錯誤在這裡結構上
  不可能靜默發生——欄位自己說了單位。
- `currency = 'TWD'`：報價幣別與結算幣別的分野（`identity/currency.py`）在這裡不適用，
  月營收就是新台幣，但仍明寫，避免下游假設。
- `published_at` 與 `report_date` **刻意分成兩欄**：MOPS 的「出表日期」是它產表的日期，
  不是公司公告日。`AGENTS.md` 明令不得用 ingest／retrieval 日期冒充 `published_at`
  ——那會讓回測在每個歷史時點看到全部證據。實際公告日這些來源都沒有，所以
  `published_at` 永遠是 NULL，而**為什麼是 NULL 由 `published_at_basis` 自己宣告**
  （L16：absence 的種類由產生它的那段程式宣告，不讓呈現層去猜）。
  可機械推導的只有法定期限：次月 10 日（`disclosure_deadline`）。

用法::

    python -m engine_c.monthly_revenue --ticker 3081.TWO            # 印序列
    python -m engine_c.monthly_revenue --sync                       # 抓當期並寫入
    python -m engine_c.monthly_revenue --backfill 12                # 回補最近 12 個月
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: `published_at` 為什麼是空的——封閉字彙。新增一種要先有一種真的新情況（L16-3）。
PUBLISHED_AT_BASIS = ("statutory_deadline_only",)

#: MOPS 月營收的固定單位與幣別。它們不是「預設值」，是這個來源的事實。
UNIT_SCALE = 1000
CURRENCY = "TWD"

#: 每月營收的法定公告期限：次月 10 日（證交所／櫃買中心的申報期限）。
#: 它是**可機械推導的上界**（「最晚到這天全市場都已公告」），不是實際公告日。
DISCLOSURE_DEADLINE_DAY = 10


def disclosure_deadline(data_month: str) -> str | None:
    """`2026-08` → `2026-09-10`（法定公告期限，不是實際公告日）。

    ⚠ 它住這裡而不是 fetcher：**「這個月的資料何時該齊」是 Engine C 的語意**，
    抓取器只負責把數字搬過來。心跳要判「落後幾個月」也讀這一個定義，
    不另寫一份（L16：分類有 SSOT 就讓它跟著走到需要它的地方）。
    """

    text = str(data_month or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", text):
        return None
    year, month = int(text[:4]), int(text[5:7])
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return date(year, month, DISCLOSURE_DEADLINE_DAY).isoformat()


_NUMERIC_COLUMNS = (
    "revenue_current",
    "revenue_prev_month",
    "revenue_year_ago",
    "cumulative_current",
    "cumulative_year_ago",
)
_RATE_COLUMNS = ("change_mom_pct", "change_yoy_pct", "change_cumulative_pct")


class MonthlyRevenueError(ValueError):
    """形狀不對的觀測。**fail closed，不補預設值。**"""


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_monthly_revenue_schema(conn) -> None:
    """非破壞性建表（SQLite）。Postgres 走 `engine_c/migrations/`。"""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS monthly_revenue_observations (
            observation_id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            market TEXT NOT NULL CHECK (market IN ('twse', 'tpex')),
            company_code TEXT NOT NULL,
            company_name TEXT,
            data_month TEXT NOT NULL,
            revenue_current INTEGER,
            revenue_prev_month INTEGER,
            revenue_year_ago INTEGER,
            change_mom_pct REAL,
            change_yoy_pct REAL,
            cumulative_current INTEGER,
            cumulative_year_ago INTEGER,
            change_cumulative_pct REAL,
            note TEXT,
            currency TEXT NOT NULL,
            unit_scale INTEGER NOT NULL CHECK (unit_scale > 0),
            disclosure_deadline TEXT NOT NULL,
            published_at TEXT,
            published_at_basis TEXT NOT NULL,
            report_date TEXT,
            source TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            payload_digest TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_monthly_revenue_ticker_month
            ON monthly_revenue_observations (ticker, data_month DESC, fetched_at DESC);
        """
    )


def build_observation(row: Mapping[str, Any], *, fetched_at: datetime | None = None) -> dict[str, Any]:
    """把 `fetchers.mops_open_data` 的一列轉成可寫入的觀測。"""

    ticker = str(row.get("ticker") or "").strip().upper()
    market = str(row.get("market") or "").strip().lower()
    data_month = str(row.get("data_month") or "").strip()
    if not ticker:
        raise MonthlyRevenueError("月營收觀測缺 ticker——代號解析不出來時不得寫入（INV-1）")
    if market not in {"twse", "tpex"}:
        raise MonthlyRevenueError(f"未知市場：{market}")
    deadline = disclosure_deadline(data_month)
    if deadline is None:
        raise MonthlyRevenueError(f"data_month 不合法：{data_month!r}")
    if row.get("revenue_current") is None:
        raise MonthlyRevenueError(f"{ticker} {data_month} 沒有當月營收——缺料不寫 0")
    stamp = (fetched_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    observation = {
        "ticker": ticker,
        "market": market,
        "company_code": str(row.get("company_code") or "").strip(),
        "company_name": (str(row.get("company_name") or "").strip() or None),
        "data_month": data_month,
        **{key: row.get(key) for key in _NUMERIC_COLUMNS},
        **{key: row.get(key) for key in _RATE_COLUMNS},
        "note": (str(row.get("note")).strip() or None) if row.get("note") else None,
        "currency": CURRENCY,
        "unit_scale": UNIT_SCALE,
        "disclosure_deadline": deadline,
        # ⚠ 永遠 NULL：這三個來源都沒有公司的實際公告日，而出表日期不是它（見 module docstring）。
        "published_at": None,
        "published_at_basis": PUBLISHED_AT_BASIS[0],
        "report_date": (str(row.get("report_date")).strip() or None) if row.get("report_date") else None,
        "source": str(row.get("source_url") or "").strip(),
        "fetched_at": stamp.isoformat(),
    }
    if not observation["source"]:
        raise MonthlyRevenueError(f"{ticker} {data_month} 缺 source URL")
    return observation


def append_monthly_revenue(conn, observation: Mapping[str, Any], *, commit: bool = True) -> str:
    """冪等寫入一筆觀測，回傳穩定 ID。同一來源同一數字重跑不會長出第二列。"""

    payload = dict(observation)
    if payload.get("published_at_basis") not in PUBLISHED_AT_BASIS:
        raise MonthlyRevenueError(
            f"published_at_basis 未登記：{payload.get('published_at_basis')!r}")
    # digest 刻意不含 fetched_at：同一來源重抓同一個月不該長出第二列。
    identity = {key: payload.get(key) for key in payload if key != "fetched_at"}
    payload_digest = _digest(_canonical_json(identity))
    observation_id = "mr_" + payload_digest[:32]
    params = {"observation_id": observation_id, **payload, "payload_digest": payload_digest}
    columns = list(params)
    try:
        from engine_c.db import DB_TYPE
    except ImportError:  # pragma: no cover
        DB_TYPE = "sqlite"
    if DB_TYPE == "postgres":
        placeholders = ",".join(f"%({column})s" for column in columns)
        with conn.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO monthly_revenue_observations ({','.join(columns)}) "
                f"VALUES ({placeholders}) ON CONFLICT (payload_digest) DO NOTHING",
                params,
            )
    else:
        ensure_monthly_revenue_schema(conn)
        conn.execute(
            f"INSERT OR IGNORE INTO monthly_revenue_observations ({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in columns)})",
            tuple(params[column] for column in columns),
        )
    if commit:
        conn.commit()
    return observation_id


def _rows(conn, sql: str, params: Sequence[Any]) -> list[dict[str, Any]]:
    try:
        from engine_c.db import DB_TYPE
    except ImportError:  # pragma: no cover
        DB_TYPE = "sqlite"
    if DB_TYPE == "postgres":
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            names = [d[0] for d in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]
    ensure_monthly_revenue_schema(conn)
    cursor = conn.execute(sql.replace("%s", "?"), tuple(params))
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def monthly_revenue_series(conn, ticker: str, *, limit: int = 36) -> dict[str, Any]:
    """一檔的月營收序列（新到舊），外加 point-in-time 與衝突報表。

    **同一個 (ticker, data_month) 可能有兩列**——當期 API 抓過一次、歷史頁又抓過一次。
    數字相同時沉默地取最新；**數字不同時列進 `conflicts`**，不靜默取一個（L12：
    成功與失敗不得在同一個訊號上同形）。
    """

    symbol = str(ticker or "").strip().upper()
    rows = _rows(
        conn,
        "SELECT * FROM monthly_revenue_observations WHERE ticker = %s "
        "ORDER BY data_month DESC, fetched_at DESC",
        [symbol],
    )
    by_month: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_month.setdefault(str(row.get("data_month")), []).append(row)
    series: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for month in sorted(by_month, reverse=True)[:limit]:
        candidates = by_month[month]
        series.append(candidates[0])
        distinct = {
            tuple(candidate.get(column) for column in _NUMERIC_COLUMNS)
            for candidate in candidates
        }
        if len(distinct) > 1:
            conflicts.append({
                "data_month": month,
                "sources": [candidate.get("source") for candidate in candidates],
                "revenue_current": [candidate.get("revenue_current") for candidate in candidates],
            })
    return {
        "ticker": symbol,
        "months": len(series),
        "series": series,
        "conflicts": conflicts,
        "unit_scale": UNIT_SCALE,
        "currency": CURRENCY,
    }


def _row_count(conn) -> int:
    """實際列數。`written` 要回報**真的多了幾列**，不是「嘗試寫入幾次」——
    冪等寫入讓兩者在重跑時完全同形（L13-2：成功與沒發生不得在同一個訊號上同形）。"""

    return int(_rows(conn, "SELECT COUNT(*) AS n FROM monthly_revenue_observations", [])[0]["n"])


def registry_taiwan_tickers() -> list[str]:
    """registry 裡所有台股。**identity 走 registry，不從別處猜**（INV-1）。"""

    from identity.registry import get_registry

    registry = get_registry()
    out = {
        str(ticker).strip().upper()
        for ticker in dict(registry.ticker_map).values()
        if ticker and str(ticker).strip().upper().endswith((".TW", ".TWO"))
    }
    return sorted(out)


def sync_current(conn, *, tickers: Iterable[str] | None = None) -> dict[str, Any]:
    """抓兩個市場的當期月營收，寫入我們追蹤的標的。回傳 INV-3 四欄報表。"""

    from fetchers.mops_open_data import (
        MARKETS,
        fetch_monthly_revenue_current,
        select_tickers,
    )

    watched = list(tickers) if tickers is not None else registry_taiwan_tickers()
    report: dict[str, Any] = {"watched": len(watched), "written": 0, "seen": 0, "markets": {}}
    for market in MARKETS:
        rows = fetch_monthly_revenue_current(market)
        accepted, counts = select_tickers(rows, watched)
        before = _row_count(conn)
        for row in accepted:
            append_monthly_revenue(conn, build_observation(row), commit=False)
        conn.commit()
        written = _row_count(conn) - before
        report["markets"][market] = {**counts, "seen": len(accepted), "written": written}
        report["written"] += written
        report["seen"] += len(accepted)
    return report


def backfill(conn, months: int, *, tickers: Iterable[str] | None = None,
             today: date | None = None) -> dict[str, Any]:
    """回補最近 N 個月（含當月往前數）。歷史頁是唯一能建序列的來源。"""

    from fetchers.mops_open_data import (
        MARKETS,
        MopsOpenDataError,
        fetch_monthly_revenue_month,
        select_tickers,
    )

    if months < 1:
        raise MonthlyRevenueError("--backfill 至少要 1 個月")
    watched = list(tickers) if tickers is not None else registry_taiwan_tickers()
    anchor = today or date.today()
    report: dict[str, Any] = {
        "watched": len(watched), "written": 0, "seen": 0, "months": [], "failed": []}
    year, month = anchor.year, anchor.month
    for _ in range(months):
        # 當月的月營收要到次月才公告，所以從上一個月開始往回數。
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        before = _row_count(conn)
        seen = 0
        for market in MARKETS:
            try:
                rows = fetch_monthly_revenue_month(market, year, month)
            except MopsOpenDataError as exc:
                # 「這個月的檔案還沒產生」與「版型變了」都會走到這裡——記下來，
                # 不讓它與「這個月沒有我們的公司」同形（L13-2）。
                report["failed"].append({"market": market, "month": f"{year:04d}-{month:02d}",
                                         "reason": str(exc)})
                continue
            accepted, _counts = select_tickers(rows, watched)
            for row in accepted:
                append_monthly_revenue(conn, build_observation(row), commit=False)
                seen += 1
        conn.commit()
        written = _row_count(conn) - before
        report["months"].append(
            {"month": f"{year:04d}-{month:02d}", "seen": seen, "written": written})
        report["written"] += written
        report["seen"] += seen
    return report


def _format_series(payload: Mapping[str, Any]) -> str:
    lines = [
        f"{payload['ticker']}｜{payload['months']} 個月｜"
        f"單位 {payload['currency']} {payload['unit_scale']:,} 元"
    ]
    for row in payload["series"]:
        revenue = row.get("revenue_current")
        yoy = row.get("change_yoy_pct")
        note = row.get("note")
        lines.append(
            f"  {row.get('data_month')}｜{revenue:,}"
            + (f"｜YoY {yoy:+.2f}%" if yoy is not None else "｜YoY —")
            + (f"｜{note}" if note else "")
        )
    for conflict in payload["conflicts"]:
        lines.append(f"  ⚠ {conflict['data_month']} 兩個來源數字不同：{conflict['revenue_current']}")
    if not payload["series"]:
        lines.append("  （沒有任何觀測——跑 `--sync` 或 `--backfill N`）")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="台股月營收（Engine C 一手觀測）")
    parser.add_argument("--ticker", help="印這一檔的序列")
    parser.add_argument("--sync", action="store_true", help="抓當期月營收並寫入")
    parser.add_argument("--backfill", type=int, metavar="N", help="回補最近 N 個月")
    parser.add_argument("--limit", type=int, default=36, help="序列最多印幾個月")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    args = parser.parse_args(argv)

    from engine_c.db import get_conn

    conn = get_conn()
    try:
        if args.sync:
            report = sync_current(conn)
            print(json.dumps(report, ensure_ascii=False, indent=2) if args.json
                  else f"sync：寫入 {report['written']} 筆｜{report['markets']}")
        if args.backfill:
            report = backfill(conn, args.backfill)
            print(json.dumps(report, ensure_ascii=False, indent=2) if args.json
                  else f"backfill：寫入 {report['written']} 筆｜失敗 {len(report['failed'])} 次")
        if args.ticker:
            payload = monthly_revenue_series(conn, args.ticker, limit=args.limit)
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=str) if args.json
                  else _format_series(payload))
        if not (args.sync or args.backfill or args.ticker):
            for symbol in registry_taiwan_tickers():
                payload = monthly_revenue_series(conn, symbol, limit=3)
                print(_format_series(payload))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
