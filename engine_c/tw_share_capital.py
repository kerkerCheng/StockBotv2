"""
tw_share_capital.py — 台股季報股數：Engine C 的可重建觀測（Phase 7 旁支開發「台股歷史股數」S1，2026-10-05）。

**它回答的只有一件事：T 時刻市場已經知道這家公司有多少股。** 已定價①（自家三年 P/S 百分位）要「當天的市值」，
市值＝當天收盤 × 當時已知的股數；TWSE／TPEx 的開放資料只有當期股本，用今天的股數回推過去會把配股、增資、
庫藏股全部算錯——所以 2026-10-05 之前台股的已定價①一律缺席（`engine_c/three_question_inputs.py`）。

**來源：** MOPS 資產負債表彙總 `ajax_t163sb05`（`fetchers.mops_open_data.fetch_balance_sheet_quarter`）——一季一張、
全市場。表上沒有「股數」這一欄，有股本（千元）、權益、每股參考淨值與庫藏股股數，股數在這裡換算：

- `shares_issued = 股本 × 1000 ÷ 面額`（面額 10 元——台灣絕大多數公司；**不是**假設放行，見下一條）
- `shares_outstanding = shares_issued − 母公司暨子公司持有之母公司庫藏股股數`
- **交叉核對**：`權益 ÷ 每股參考淨值` 也是一個股數（權益取歸屬母公司業主；表上是「--」且沒有非控制權益時取權益總計）。
  兩者相對差超過 `CROSS_CHECK_TOLERANCE` 就 **fail closed**：那一列照寫進表（`cross_check_status='mismatch'`）、讀取端
  不用、報表逐筆列出——面額不是 10 元的公司會在這裡現形，不會被「股本 ÷ 10」靜默算錯十倍。
  2026-10-05 首次回補（12 檔 × 14 季）攔下的 4 筆都不是面額：**股本含待分配股票股利**（股東會決議後、除權前就記進股本；
  3081.TWO 2026Q2 正好 +10%，那筆配股 07-15 除權、`corporate_actions` 記成 1.1 的分割——收了這一季會被 `shares_on` 再乘一次），
  以及奇鋐三季（+4%～+29%，可轉債換股等尚未變成流通在外的股本）。被拒的季由前一季股數接著用，配股由分割比例補上。

**為什麼是 ETL 表不是 append-only ledger（L10）：** MOPS 按季永久可查，今天重抓拿得回來——與
`monthly_revenue_observations` 同類：可重建、零核准、不是 pq2 的 judgment ledger。

**可知日＝法定期限，不是抓取日（INV-6）：** 一般業 Q1 5/15、Q2 8/14、Q3 11/14、年報次年 3/31（季後 45 日、年後 3 個月）。
`available_on_basis='statutory_deadline_only'` 自己宣告為什麼不是實際公告日（L16）。⚠ **金融業的半年報期限不同**——
所以只收已登記的兩種版型（一般業、異業；`fetchers.mops_open_data.BALANCE_SHEET_TEMPLATES`），銀行、金控、保險、證券期貨
與任何未登記的新版型都在抓取層拒收、列進報表，不套一般業的期限。

用法::

    python -m engine_c.tw_share_capital --ticker 3081.TWO        # 印序列（含核對不一致的列）
    python -m engine_c.tw_share_capital --backfill 14            # 回補最近 14 季（已過法定期限的）
    python -m engine_c.tw_share_capital --sync                   # 只抓最近一季已過期限的那一季
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: `available_on` 為什麼不是實際公告日——封閉字彙（與月營收同一個值）。
AVAILABLE_ON_BASIS = ("statutory_deadline_only",)
#: 交叉核對的封閉字彙：`ok` 才給讀取端用。
CROSS_CHECK_STATUSES = ("ok", "mismatch", "not_checkable")
#: 「股本 ÷ 面額」與「權益 ÷ 每股參考淨值」的相對差上限。每股淨值只到小數第二位，捨入誤差在 0.1% 量級；
#: 2% 遠大於捨入、遠小於「面額不是 10 元」（差 2 倍以上）。
CROSS_CHECK_TOLERANCE = 0.02
#: 面額（元）。不是預設值：交叉核對失敗的列不給讀取端用，所以面額不對的公司不會被它算錯。
PAR_VALUE = 10
UNIT_SCALE = 1000          # 金額欄（股本、權益）是新台幣千元
CURRENCY = "TWD"
#: 一般業的法定期限（季後 45 日、年報 3 個月）。key＝季別，value＝(月, 日, 是否次年)。
_DEADLINES = {1: (5, 15, False), 2: (8, 14, False), 3: (11, 14, False), 4: (3, 31, True)}
_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


class ShareCapitalError(ValueError):
    """形狀不對的觀測。**fail closed，不補預設值。**"""


def quarter_end(year: int, quarter: int) -> str:
    month, day = _QUARTER_END[int(quarter)]
    return date(int(year), month, day).isoformat()


def statutory_deadline(year: int, quarter: int) -> str:
    """`(2026, 2)` → `2026-08-14`；`(2025, 4)` → `2026-03-31`。一般業的法定期限（上界，不是實際公告日）。"""
    if int(quarter) not in _DEADLINES:
        raise ShareCapitalError(f"季別不合法：{quarter}")
    month, day, next_year = _DEADLINES[int(quarter)]
    return date(int(year) + (1 if next_year else 0), month, day).isoformat()


def latest_due_quarter(today: date) -> tuple[int, int]:
    """今天之前（含）已過法定期限的最近一季。"""
    candidates = [(y, q) for y in (today.year - 1, today.year) for q in (1, 2, 3, 4)
                  if date.fromisoformat(statutory_deadline(y, q)) <= today]
    return max(candidates)


def previous_quarter(year: int, quarter: int) -> tuple[int, int]:
    return (year - 1, 4) if quarter == 1 else (year, quarter - 1)


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_share_capital_schema(conn) -> None:
    """非破壞性建表（SQLite；由 `engine_c.db._ensure_sqlite_schema` 呼叫）。Postgres 的對等表在
    `engine_c/migrations/20261005_add_tw_share_capital.sql`；讀寫端與 `engine_c.history` 一樣只走 SQLite。
    ⚠ 讀取端**不**呼叫這一支：三題用唯讀連線（不在讀取路徑建表），表不存在＝還沒有觀測（`engine_c.history`）。"""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tw_share_capital_observations (
            observation_id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            market TEXT NOT NULL CHECK (market IN ('twse', 'tpex')),
            company_code TEXT NOT NULL,
            company_name TEXT,
            fiscal_year INTEGER NOT NULL,
            quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
            period_end TEXT NOT NULL,
            template TEXT NOT NULL,
            share_capital INTEGER,
            equity_parent INTEGER,
            equity_total INTEGER,
            non_controlling INTEGER,
            bvps REAL,
            treasury_shares INTEGER,
            par_value INTEGER NOT NULL,
            shares_issued INTEGER,
            shares_outstanding INTEGER,
            shares_implied_by_equity INTEGER,
            cross_check_diff REAL,
            cross_check_status TEXT NOT NULL,
            cross_check_reason TEXT,
            currency TEXT NOT NULL,
            unit_scale INTEGER NOT NULL CHECK (unit_scale > 0),
            available_on TEXT NOT NULL,
            available_on_basis TEXT NOT NULL,
            source TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            payload_digest TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_tw_share_capital_ticker_period
            ON tw_share_capital_observations (ticker, period_end DESC, fetched_at DESC);
        """
    )


def build_observation(row: Mapping[str, Any], *, fetched_at: datetime | None = None) -> dict[str, Any]:
    """`fetchers.mops_open_data.fetch_balance_sheet_quarter` 的一列 → 可寫入的觀測（含換算與交叉核對）。"""
    ticker = str(row.get("ticker") or "").strip().upper()
    market = str(row.get("market") or "").strip().lower()
    if not ticker:
        raise ShareCapitalError("季報股數觀測缺 ticker——代號解析不出來時不得寫入（INV-1）")
    if market not in {"twse", "tpex"}:
        raise ShareCapitalError(f"未知市場：{market}")
    year, quarter = int(row["fiscal_year"]), int(row["quarter"])
    if not str(row.get("source_url") or "").strip():
        raise ShareCapitalError(f"{ticker} {year}Q{quarter} 缺 source")
    capital = row.get("share_capital")
    treasury = row.get("treasury_shares") or 0
    issued = (int(capital) * UNIT_SCALE // PAR_VALUE) if capital else None
    outstanding = (issued - int(treasury)) if issued is not None else None
    # 每股參考淨值的分子：歸屬母公司業主權益；表上是「--」而且沒有非控制權益時，權益總計就是它。
    equity = row.get("equity_parent")
    if equity is None and not row.get("non_controlling"):
        equity = row.get("equity_total")
    bvps = row.get("bvps")
    usable = equity is not None and equity > 0 and bvps is not None and bvps > 0
    implied = int(round(float(equity) * UNIT_SCALE / float(bvps))) if usable else None
    if outstanding is None or outstanding <= 0:
        status, diff, reason = "not_checkable", None, "股本缺或換算後股數不為正"
    elif implied is None:
        status, diff, reason = "not_checkable", None, "權益或每股參考淨值缺、不為正，或權益分不出歸屬母公司的部分——無從核對"
    else:
        diff = round(abs(outstanding - implied) / implied, 6)
        if diff > CROSS_CHECK_TOLERANCE:
            status, reason = "mismatch", (f"股本÷{PAR_VALUE} 元扣庫藏股＝{outstanding:,} 股，權益÷每股淨值＝{implied:,} 股，"
                                          f"差 {diff:.2%}（> {CROSS_CHECK_TOLERANCE:.0%}；面額可能不是 {PAR_VALUE} 元）")
        else:
            status, reason = "ok", None
    stamp = (fetched_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "ticker": ticker, "market": market,
        "company_code": str(row.get("company_code") or "").strip(),
        "company_name": (str(row.get("company_name") or "").strip() or None),
        "fiscal_year": year, "quarter": quarter, "period_end": quarter_end(year, quarter),
        "template": str(row.get("template") or ""),
        "share_capital": capital, "equity_parent": row.get("equity_parent"), "equity_total": row.get("equity_total"),
        "non_controlling": row.get("non_controlling"), "bvps": bvps, "treasury_shares": row.get("treasury_shares"),
        "par_value": PAR_VALUE, "shares_issued": issued, "shares_outstanding": outstanding,
        "shares_implied_by_equity": implied, "cross_check_diff": diff, "cross_check_status": status,
        "cross_check_reason": reason, "currency": CURRENCY, "unit_scale": UNIT_SCALE,
        "available_on": statutory_deadline(year, quarter), "available_on_basis": AVAILABLE_ON_BASIS[0],
        "source": str(row.get("source_url")).strip(), "fetched_at": stamp.isoformat(),
    }


def append_share_capital(conn, observation: Mapping[str, Any], *, commit: bool = True) -> str:
    """冪等寫入一筆觀測（digest 不含 fetched_at：同一來源重抓同一季不會長出第二列）。"""
    payload = dict(observation)
    if payload.get("available_on_basis") not in AVAILABLE_ON_BASIS:
        raise ShareCapitalError(f"available_on_basis 未登記：{payload.get('available_on_basis')!r}")
    if payload.get("cross_check_status") not in CROSS_CHECK_STATUSES:
        raise ShareCapitalError(f"cross_check_status 未登記：{payload.get('cross_check_status')!r}")
    identity = {key: payload.get(key) for key in payload if key != "fetched_at"}
    payload_digest = _digest(_canonical_json(identity))
    params = {"observation_id": "tsc_" + payload_digest[:32], **payload, "payload_digest": payload_digest}
    columns = list(params)
    ensure_share_capital_schema(conn)
    conn.execute(f"INSERT OR IGNORE INTO tw_share_capital_observations ({','.join(columns)}) "
                 f"VALUES ({','.join('?' for _ in columns)})", tuple(params[c] for c in columns))
    if commit:
        conn.commit()
    return params["observation_id"]


def _row_count(conn) -> int:
    ensure_share_capital_schema(conn)
    return int(conn.execute("SELECT COUNT(*) FROM tw_share_capital_observations").fetchone()[0])


def _fetch_and_write(conn, year: int, quarter: int, watched: list[str], report: dict[str, Any]) -> None:
    from fetchers.mops_open_data import MARKETS, MopsOpenDataError, fetch_balance_sheet_quarter, select_tickers

    entry: dict[str, Any] = {"quarter": f"{year}Q{quarter}", "seen": 0, "written": 0, "rejected_templates": {},
                             "not_ok": []}
    before = _row_count(conn)
    for market in MARKETS:
        try:
            rows, rejected = fetch_balance_sheet_quarter(market, year, quarter)
        except MopsOpenDataError as exc:
            # 「這一季還沒出表」與「版型變了」都會走到這裡——記下來，不與「沒有我們的公司」同形（L13-2）。
            report["failed"].append({"market": market, "quarter": entry["quarter"], "reason": str(exc)})
            continue
        accepted, _counts = select_tickers(rows, watched)
        watched_rejected = [r for r in rejected if str(r.get("ticker") or "").upper() in watched]
        for r in watched_rejected:
            entry["rejected_templates"][r["ticker"]] = r["template"]
        for row in accepted:
            obs = build_observation(row)
            append_share_capital(conn, obs, commit=False)
            entry["seen"] += 1
            if obs["cross_check_status"] != "ok":
                entry["not_ok"].append({"ticker": obs["ticker"], "status": obs["cross_check_status"],
                                        "reason": obs["cross_check_reason"]})
    conn.commit()
    entry["written"] = _row_count(conn) - before
    report["quarters"].append(entry)
    report["written"] += entry["written"]
    report["seen"] += entry["seen"]


def _watched(tickers: Iterable[str] | None) -> list[str]:
    from engine_c.monthly_revenue import registry_taiwan_tickers

    return sorted({str(t).strip().upper() for t in (tickers if tickers is not None else registry_taiwan_tickers())})


def backfill(conn, quarters: int, *, tickers: Iterable[str] | None = None, today: date | None = None) -> dict[str, Any]:
    """回補最近 N 季（從已過法定期限的最近一季往回數）。"""
    if quarters < 1:
        raise ShareCapitalError("--backfill 至少要 1 季")
    watched = _watched(tickers)
    report: dict[str, Any] = {"watched": len(watched), "written": 0, "seen": 0, "quarters": [], "failed": []}
    year, quarter = latest_due_quarter(today or date.today())
    for _ in range(quarters):
        _fetch_and_write(conn, year, quarter, watched, report)
        year, quarter = previous_quarter(year, quarter)
    return report


def sync_latest(conn, *, tickers: Iterable[str] | None = None, today: date | None = None) -> dict[str, Any]:
    """只抓已過法定期限的最近一季（每季跑一次就跟得上；重跑冪等）。"""
    return backfill(conn, 1, tickers=tickers, today=today)


def share_capital_series(conn, ticker: str) -> list[dict[str, Any]]:
    """一檔的全部觀測（舊到新；含核對不一致的列）。"""
    ensure_share_capital_schema(conn)
    cur = conn.execute("SELECT * FROM tw_share_capital_observations WHERE ticker = ? ORDER BY period_end, fetched_at",
                       (str(ticker).strip().upper(),))
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _format(ticker: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"{ticker}｜{len(rows)} 季｜股數＝股本×{UNIT_SCALE}÷{PAR_VALUE} 元－庫藏股；可知日＝法定期限"]
    for r in rows:
        flag = "" if r["cross_check_status"] == "ok" else f"｜⚠ {r['cross_check_status']}：{r['cross_check_reason']}"
        lines.append(f"  {r['fiscal_year']}Q{r['quarter']}（期末 {r['period_end']}，可知 {r['available_on']}）｜"
                     f"流通在外 {r['shares_outstanding'] or 0:,}｜核對 {r['shares_implied_by_equity'] or 0:,}{flag}")
    if not rows:
        lines.append("  （沒有任何觀測——跑 `--backfill N`）")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="台股季報股數（Engine C 可重建觀測）")
    parser.add_argument("--ticker", help="印這一檔的序列")
    parser.add_argument("--sync", action="store_true", help="抓已過法定期限的最近一季")
    parser.add_argument("--backfill", type=int, metavar="N", help="回補最近 N 季")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    args = parser.parse_args(argv)

    from engine_c.db import get_conn

    conn = get_conn()
    try:
        for flag, fn in ((args.sync, lambda: sync_latest(conn)), (bool(args.backfill), lambda: backfill(conn, args.backfill))):
            if flag:
                report = fn()
                bad = [x for q in report["quarters"] for x in q["not_ok"]]
                print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else
                      f"寫入 {report['written']} 筆｜看到 {report['seen']}｜失敗 {len(report['failed'])} 次｜核對不一致 {len(bad)} 筆"
                      + "".join(f"\n  ⚠ {x['ticker']} {x['status']}：{x['reason']}" for x in bad)
                      + "".join(f"\n  ✗ {f['market']} {f['quarter']}：{f['reason']}" for f in report["failed"]))
        if args.ticker:
            rows = share_capital_series(conn, args.ticker)
            print(json.dumps(rows, ensure_ascii=False, indent=2, default=str) if args.json else _format(args.ticker.upper(), rows))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
