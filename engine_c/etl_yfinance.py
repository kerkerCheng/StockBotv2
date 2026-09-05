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
import math
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
    yf = None

from identity.registry import TICKER_MAP
from engine_c.db import (
    DB_TYPE,
    get_conn,
    upsert_consensus_estimate,
    upsert_coverage_observation,
    upsert_snapshot,
)
from shared.fiscal import FISCAL_YEAR_LABELS, epoch_to_date, fiscal_label, resolve_fiscal_year_end


COVERAGE_SOURCE = "yfinance.info.numberOfAnalystOpinions"
#: 會計年度別共識的來源標記（metric → yfinance 屬性、去年實際值欄位）。
FISCAL_ESTIMATE_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("eps", "earnings_estimate", "yearAgoEps"),
    ("revenue", "revenue_estimate", "yearAgoRevenue"),
)
YFINANCE_CACHE_DIR = Path(
    os.environ.get(
        "YFINANCE_CACHE_DIR",
        Path(__file__).resolve().parent / ".yfinance-cache",
    )
)


def _configure_yfinance_cache() -> None:
    """Keep yfinance's SQLite cookie/timezone cache in a writable local root."""

    if yf is None or not hasattr(yf, "set_tz_cache_location"):
        return
    YFINANCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(YFINANCE_CACHE_DIR))


def _sf(val) -> float | None:
    try:
        result = float(val) if val is not None else None
    except (TypeError, ValueError):
        return None
    return result if result is not None and math.isfinite(result) else None


def _si(val) -> int | None:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _bar_identity(info: dict) -> tuple[str | None, str | None]:
    """由 provider **明示欄位**導出 (bar_date, price_kind)；導不出就回 (None, None)。

    2026-08-13 查證：`snapshot_date` 存的是跑 ETL 的當地日期，而 `price` 取自
    `currentPrice`／`regularMarketPrice`——盤中跑是盤中價、收盤後跑是收盤價，且
    UTC 晚班會把當天的美股收盤標成隔天。一個欄位承載三種語意（L12），拿它當 as-of
    的消費者全部系統性差一天。

    這裡只讀 provider 明講的欄位（`regularMarketTime` 的 epoch ＋
    `exchangeTimezoneName` ＋ `marketState`），**不做推斷**——「不採 provider 推斷的
    sector」那條路教過的錯誤（見 AGENTS.md 報價單位一節）。欄位缺就誠實回 None，
    由 NULL 表示「as-of 未知」，不猜。

    `price_kind`：`marketState == "REGULAR"` 代表盤中，價格還會變；其餘狀態
    （PRE／PREPRE／POST／POSTPOST／CLOSED）代表 regular session 已結束，
    `regularMarketPrice` 就是該交易日收盤。
    """
    epoch = info.get("regularMarketTime")
    tz_name = info.get("exchangeTimezoneName")
    if not isinstance(epoch, (int, float)) or isinstance(epoch, bool) or not tz_name:
        return None, None
    try:
        from zoneinfo import ZoneInfo

        stamp = datetime.fromtimestamp(float(epoch), ZoneInfo(str(tz_name)))
    except Exception:
        return None, None
    state = str(info.get("marketState") or "").upper()
    kind = "intraday" if state == "REGULAR" else "close"
    return stamp.date().isoformat(), kind


def fetch_snapshot(ticker: str) -> dict | None:
    """yfinance 抓一個 ticker 的當日快照。"""
    if yf is None:
        print("[etl] WARN: yfinance 未安裝（pip install yfinance）", file=sys.stderr)
        return None
    _configure_yfinance_cache()
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        print(f"[etl] WARN: yfinance failed for {ticker}: {e}", file=sys.stderr)
        return None

    price = _sf(info.get("currentPrice"))
    if price is None:
        price = _sf(info.get("regularMarketPrice"))
    if price is None:
        print(f"[etl] WARN: no price data for {ticker}", file=sys.stderr)
        return None

    bar_date, price_kind = _bar_identity(info)
    revenue_next = _next_fy_revenue_estimate(t, ticker)
    fetched_at = datetime.now(timezone.utc)
    snapshot_date = date.today()
    return {
        # 會計年度別共識（Phase 2）：在抓取當下就解析成絕對會計期間，`run_etl` 另存
        # `consensus_estimates` 表。它不是 financial_snapshots 的欄位，所以放在底線鍵下，
        # `upsert_snapshot` 只讀具名欄位、不會碰到它。
        "_consensus_estimates": _fiscal_estimates(
            t, info, ticker, snapshot_date=snapshot_date, bar_date=bar_date,
            fetched_at=fetched_at,
        ),
        "ticker":               ticker,
        # ⚠ snapshot_date 是「跑 ETL 的當地日期」，**不是行情交易日**。它是 UNIQUE
        # 鍵的一半，保留原語意不動；要 as-of 的消費者一律讀 bar_date。
        "snapshot_date":        snapshot_date,
        "bar_date":             bar_date,
        "price_kind":           price_kind,
        "gross_margin":         _sf(info.get("grossMargins")),
        "operating_margin":     _sf(info.get("operatingMargins")),
        "revenue_ttm":          _si(info.get("totalRevenue")),
        "shares_outstanding":   _si(info.get("sharesOutstanding")),
        "cash_and_equivalents": _sf(info.get("totalCash")),
        "total_debt":           _sf(info.get("totalDebt")),
        "free_cash_flow_ttm":   _sf(info.get("freeCashflow")),
        "ev_revenue":           _sf(info.get("enterpriseToRevenue")),
        "pe_trailing":          _sf(info.get("trailingPE")),
        "pe_forward":           _sf(info.get("forwardPE")),
        "price":                price,
        "analyst_target_mean":  _sf(info.get("targetMeanPrice")),
        "analyst_target_high":  _sf(info.get("targetHighPrice")),
        "analyst_target_low":   _sf(info.get("targetLowPrice")),
        "analyst_target_count": _si(info.get("numberOfAnalystOpinions")),
        # 下一會計年度的營收共識（Phase 4c）。⚠ 絕對值是**該標的的報表幣別**，
        # 不是 USD——只能比同一標的的時間序列，不得跨標的比絕對值（同 Phase 4a 的單位陷阱）。
        # `..._growth` 無單位，那一欄才可以跨標的比。
        "revenue_estimate_next_fy":          revenue_next["avg"],
        "revenue_estimate_next_fy_growth":   revenue_next["growth"],
        "revenue_estimate_next_fy_analysts": revenue_next["analysts"],
        "fetched_at":           fetched_at,
    }


def _fiscal_estimates(
    ticker_obj, info: dict, ticker: str, *, snapshot_date, bar_date, fetched_at,
) -> list[dict]:
    """會計年度別的 EPS／營收共識，每一筆帶**絕對的** `fiscal_period_end`。

    ⚠ `0y`／`+1y` 是相對於抓取日的標籤——COHR 在 2026-09 抓到的 `+1y` 是 FY2028，
    而既有的 `revenue_estimate_next_fy` 欄位就存的是它。內部估計要與共識做同期比較，
    身分必須在抓取當下就用 provider 的 `lastFiscalYearEnd`／`nextFiscalYearEnd` 解析成
    日期（`shared.fiscal.resolve_fiscal_year_end`）；解析不出來的期間**不寫列**。

    ⚠ 取不到一律沒有列，不是 0（同 `_next_fy_revenue_estimate` 的理由，L12）。
    ⚠ provider 不宣告 GAAP／non-GAAP：`year_ago_actual` 保存去年實際值，讓讀取端能與
    一手財報數字機械核對，本函式**不猜** basis。
    """
    last_end = epoch_to_date(info.get("lastFiscalYearEnd"))
    next_end = epoch_to_date(info.get("nextFiscalYearEnd"))
    rows: list[dict] = []
    for metric, attr, year_ago_column in FISCAL_ESTIMATE_SOURCES:
        try:
            frame = getattr(ticker_obj, attr)
        except Exception as exc:  # noqa: BLE001 — provider 失敗只降級成「這檔沒有」
            print(f"[etl] WARN: {attr} failed for {ticker}: {exc}", file=sys.stderr)
            continue
        index = getattr(frame, "index", None)
        if frame is None or index is None:
            continue
        for label in FISCAL_YEAR_LABELS:
            if label not in index:
                continue
            period_end = resolve_fiscal_year_end(
                label, last_fiscal_year_end=last_end, next_fiscal_year_end=next_end)
            if period_end is None:
                print(f"[etl] WARN: {ticker} {attr} {label}: fiscal calendar unresolved "
                      f"(last={last_end}, next={next_end}); row skipped", file=sys.stderr)
                continue
            row = frame.loc[label]
            avg = _sf(row.get("avg"))
            if avg is None:
                continue
            rows.append({
                "ticker": ticker,
                "snapshot_date": snapshot_date,
                "bar_date": bar_date,
                "metric": metric,
                "period_kind": "fiscal_year",
                "relative_label": label,
                "fiscal_period_end": period_end.isoformat(),
                "fiscal_label": fiscal_label(period_end),
                "estimate_avg": avg,
                "estimate_low": _sf(row.get("low")),
                "estimate_high": _sf(row.get("high")),
                "analyst_count": _si(row.get("numberOfAnalysts")),
                "year_ago_actual": _sf(row.get(year_ago_column)),
                "growth": _sf(row.get("growth")),
                "currency": (str(row.get("currency")) if row.get("currency") else None),
                "source": f"yfinance.{attr}",
                "fetched_at": fetched_at,
            })
    return rows


def _next_fy_revenue_estimate(ticker_obj, ticker: str) -> dict:
    """`+1y` 的分析師營收共識。取不到一律回三個 `None`，**不回 0**。

    ⚠ **ROADMAP 曾寫「yfinance 沒有絕對營收估計」，那句話是假的。**
    2026-09-04 實測 `revenue_estimate` 直接給 `+1y` 的 avg／growth／numberOfAnalysts，
    73/73 檔全覆蓋。這是「引用自家文件的現況陳述前先跑查證命令」第三次抓到同型錯誤。

    ⚠ 取不到時回 `None` 而不是 0：「沒有共識」與「共識是零成長」是兩件事（L12）。
    """
    empty = {"avg": None, "growth": None, "analysts": None}
    try:
        frame = ticker_obj.revenue_estimate
    except Exception as exc:  # noqa: BLE001 — provider 失敗只降級成「這檔沒有共識」
        print(f"[etl] WARN: revenue_estimate failed for {ticker}: {exc}", file=sys.stderr)
        return empty
    if frame is None or "+1y" not in getattr(frame, "index", ()):
        return empty
    row = frame.loc["+1y"]
    return {
        "avg": _sf(row.get("avg")),
        "growth": _sf(row.get("growth")),
        "analysts": _si(row.get("numberOfAnalysts")),
    }


def coverage_observation_from_snapshot(snapshot: dict) -> dict:
    """Project the raw yfinance field into an objective observation row."""

    count = snapshot.get("analyst_target_count")
    return {
        "ticker": snapshot["ticker"],
        "observation_date": snapshot["snapshot_date"],
        "analyst_count": count,
        "source": COVERAGE_SOURCE,
        "data_status": "observed" if count is not None else "manual_required",
        "fetched_at": snapshot["fetched_at"],
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
        estimates = snap.pop("_consensus_estimates", [])
        try:
            upsert_snapshot(conn, snap, commit=False)
            upsert_coverage_observation(
                conn, coverage_observation_from_snapshot(snap), commit=False
            )
            for row in estimates:
                upsert_consensus_estimate(conn, row, commit=False)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            print(f"FAILED ({type(exc).__name__}: {exc})")
            continue
        print(f"ok  (price={snap['price']}, gm={snap['gross_margin']}, "
              f"fy_estimates={len(estimates)})")
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
    return 0 if args.dry_run or n == len(tickers) else 1


if __name__ == "__main__":
    raise SystemExit(main())
