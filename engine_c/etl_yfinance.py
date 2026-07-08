"""
etl_yfinance.py — 用 yfinance 拉財務快照，寫入 Engine C 資料庫。

後端：SQLite（預設，零安裝）或 Postgres（設 POSTGRES_HOST/DSN）。
每天執行一次（或手動觸發）。會跳過當天已有紀錄的 ticker。

用法:
    python engine_c/etl_yfinance.py                   # 抓 TICKER_MAP 所有非 null ticker
    python engine_c/etl_yfinance.py COHR LITE          # 只抓指定 ticker
    python engine_c/etl_yfinance.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import yfinance as yf
except ImportError:
    print("需要 yfinance: pip install yfinance", file=sys.stderr)
    sys.exit(1)

from loader.load_to_neo4j import TICKER_MAP
from engine_c.db import get_conn, upsert_snapshot, DB_TYPE


def _sf(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _si(val) -> int | None:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def fetch_snapshot(ticker: str) -> dict | None:
    """yfinance 抓一個 ticker 的當日快照。"""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        print(f"[etl] WARN: yfinance failed for {ticker}: {e}", file=sys.stderr)
        return None

    if not info.get("regularMarketPrice") and not info.get("currentPrice"):
        print(f"[etl] WARN: no price data for {ticker}", file=sys.stderr)
        return None

    return {
        "ticker":               ticker,
        "snapshot_date":        date.today(),
        "gross_margin":         _sf(info.get("grossMargins")),
        "operating_margin":     _sf(info.get("operatingMargins")),
        "revenue_ttm":          _si(info.get("totalRevenue")),
        "shares_outstanding":   _si(info.get("sharesOutstanding")),
        "ev_revenue":           _sf(info.get("enterpriseToRevenue")),
        "pe_trailing":          _sf(info.get("trailingPE")),
        "pe_forward":           _sf(info.get("forwardPE")),
        "price":                _sf(info.get("currentPrice") or info.get("regularMarketPrice")),
        "analyst_target_mean":  _sf(info.get("targetMeanPrice")),
        "analyst_target_high":  _sf(info.get("targetHighPrice")),
        "analyst_target_low":   _sf(info.get("targetLowPrice")),
        "analyst_target_count": _si(info.get("numberOfAnalystOpinions")),
        "fetched_at":           datetime.now(timezone.utc),
    }


def run_etl(tickers: list[str], dry_run: bool = False) -> int:
    if dry_run:
        print(f"[dry-run] would fetch: {', '.join(tickers)}")
        return 0

    conn = get_conn()
    success = 0
    for ticker in tickers:
        print(f"[etl] fetching {ticker}...", end=" ", flush=True)
        snap = fetch_snapshot(ticker)
        if snap is None:
            print("SKIP")
            continue
        upsert_snapshot(conn, snap)
        print(f"ok  (price={snap['price']}, gm={snap['gross_margin']})")
        success += 1
    conn.close()
    return success


def main() -> int:
    ap = argparse.ArgumentParser(description=f"yfinance → {DB_TYPE} ETL for Engine C")
    ap.add_argument("tickers", nargs="*", help="指定 ticker（空白則抓 TICKER_MAP 所有非 null）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tickers = [t.upper() for t in args.tickers] if args.tickers else [
        t for t in TICKER_MAP.values() if t is not None
    ]
    if not tickers:
        print("no tickers", file=sys.stderr)
        return 1

    print(f"{'[dry-run] ' if args.dry_run else ''}backend={DB_TYPE}, fetching {len(tickers)} tickers...")
    n = run_etl(tickers, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"\n✓ {n}/{len(tickers)} snapshots written to {DB_TYPE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
