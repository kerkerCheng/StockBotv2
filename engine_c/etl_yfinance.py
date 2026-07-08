"""
etl_yfinance.py — 用 yfinance 拉財務快照，寫入 Postgres financial_snapshots。

每天執行一次（或手動觸發）。會跳過當天已有紀錄的 ticker。

用法:
    python engine_c/etl_yfinance.py                   # 抓 TICKER_MAP 所有非 null ticker
    python engine_c/etl_yfinance.py COHR LITE          # 只抓指定 ticker
    python engine_c/etl_yfinance.py --dry-run          # 印出要抓的 ticker，不寫入
"""
from __future__ import annotations

import argparse
import os
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

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("需要 psycopg2: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

from loader.load_to_neo4j import TICKER_MAP

INSERT_SNAPSHOT = """
INSERT INTO financial_snapshots (
    ticker, snapshot_date,
    gross_margin, operating_margin, revenue_ttm,
    shares_outstanding,
    ev_revenue, pe_trailing, pe_forward, price,
    analyst_target_mean, analyst_target_high, analyst_target_low, analyst_target_count,
    fetched_at
) VALUES (
    %(ticker)s, %(snapshot_date)s,
    %(gross_margin)s, %(operating_margin)s, %(revenue_ttm)s,
    %(shares_outstanding)s,
    %(ev_revenue)s, %(pe_trailing)s, %(pe_forward)s, %(price)s,
    %(analyst_target_mean)s, %(analyst_target_high)s, %(analyst_target_low)s, %(analyst_target_count)s,
    %(fetched_at)s
)
ON CONFLICT (ticker, snapshot_date) DO UPDATE SET
    gross_margin         = EXCLUDED.gross_margin,
    operating_margin     = EXCLUDED.operating_margin,
    revenue_ttm          = EXCLUDED.revenue_ttm,
    shares_outstanding   = EXCLUDED.shares_outstanding,
    ev_revenue           = EXCLUDED.ev_revenue,
    pe_trailing          = EXCLUDED.pe_trailing,
    pe_forward           = EXCLUDED.pe_forward,
    price                = EXCLUDED.price,
    analyst_target_mean  = EXCLUDED.analyst_target_mean,
    analyst_target_high  = EXCLUDED.analyst_target_high,
    analyst_target_low   = EXCLUDED.analyst_target_low,
    analyst_target_count = EXCLUDED.analyst_target_count,
    fetched_at           = EXCLUDED.fetched_at
"""


def _safe_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> int | None:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def fetch_snapshot(ticker: str) -> dict | None:
    """yfinance 抓一個 ticker 的當日快照。回傳 dict 或 None（失敗時）。"""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        print(f"[etl] WARN: yfinance failed for {ticker}: {e}", file=sys.stderr)
        return None

    if not info.get("regularMarketPrice") and not info.get("currentPrice"):
        print(f"[etl] WARN: no price data for {ticker}, possibly delisted or invalid", file=sys.stderr)
        return None

    return {
        "ticker":               ticker,
        "snapshot_date":        date.today(),
        "gross_margin":         _safe_float(info.get("grossMargins")),
        "operating_margin":     _safe_float(info.get("operatingMargins")),
        "revenue_ttm":          _safe_int(info.get("totalRevenue")),
        "shares_outstanding":   _safe_int(info.get("sharesOutstanding")),
        "ev_revenue":           _safe_float(info.get("enterpriseToRevenue")),
        "pe_trailing":          _safe_float(info.get("trailingPE")),
        "pe_forward":           _safe_float(info.get("forwardPE")),
        "price":                _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        "analyst_target_mean":  _safe_float(info.get("targetMeanPrice")),
        "analyst_target_high":  _safe_float(info.get("targetHighPrice")),
        "analyst_target_low":   _safe_float(info.get("targetLowPrice")),
        "analyst_target_count": _safe_int(info.get("numberOfAnalystOpinions")),
        "fetched_at":           datetime.now(timezone.utc),
    }


def get_connection():
    """建立 Postgres 連線。"""
    dsn = os.environ.get("POSTGRES_DSN")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "stockbot"),
        user=os.environ.get("POSTGRES_USER", "stockbot"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )


def run_etl(tickers: list[str], dry_run: bool = False) -> int:
    """抓 tickers 的快照，寫入 Postgres。回傳成功筆數。"""
    if dry_run:
        print(f"[dry-run] would fetch: {', '.join(tickers)}")
        return 0

    conn = get_connection()
    success = 0
    try:
        with conn.cursor() as cur:
            for ticker in tickers:
                print(f"[etl] fetching {ticker}...", end=" ", flush=True)
                snap = fetch_snapshot(ticker)
                if snap is None:
                    print("SKIP")
                    continue
                cur.execute(INSERT_SNAPSHOT, snap)
                conn.commit()
                print(f"ok  (price={snap['price']}, gross_margin={snap['gross_margin']})")
                success += 1
    finally:
        conn.close()
    return success


def main() -> int:
    ap = argparse.ArgumentParser(description="yfinance → Postgres ETL for Engine C")
    ap.add_argument("tickers", nargs="*", help="指定 ticker（空白則抓 TICKER_MAP 所有非 null）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.tickers:
        tickers = [t.upper() for t in args.tickers]
    else:
        tickers = [t for t in TICKER_MAP.values() if t is not None]

    if not tickers:
        print("no tickers to fetch", file=sys.stderr)
        return 1

    print(f"{'[dry-run] ' if args.dry_run else ''}fetching {len(tickers)} tickers...")
    n = run_etl(tickers, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"\n✓ {n}/{len(tickers)} snapshots written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
