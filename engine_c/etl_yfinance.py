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


#: **yfinance 這兩個利潤率欄位的期間不同，而 provider 自己沒有宣告。**（2026-09-13 登記）
#: 兩次獨立驗證（2026-09-12）：SNDK 快照 `operatingMargins` 0.78472 ≈ Q4 FY2026 單季 GAAP
#: 營益率 7,037÷8,965＝0.78494，而同一份的 `grossMargins` 0.71474 **精確等於全年** 14,472÷20,248；
#: 000660.KS 快照 0.76328003 逐位等於 2Q2026 單季，而 TTM 實為 68.0%（差 8.3pp）。
#: ⚠ **受影響的是每一檔**——`operating_margin > gross_margin` 只在「最近一季特別好」時才看得出來
#: （全庫只有 MU／SNDK／000660.KS 三檔，三家都是記憶體廠），其餘同樣錯配、只是看不出來。
#: 這兩個常數是**宣告**，不是推論：它們描述的是 yfinance 欄位的定義，不是某一列資料的性質，
#: 所以不放 DB 欄位（每列都一樣的值放進每一列只會讓人以為它可能不一樣）。
SNAPSHOT_OPERATING_MARGIN_PERIOD = "latest_quarter"
SNAPSHOT_GROSS_MARGIN_PERIOD = "annual_or_ttm"

#: 季度資產負債表的租賃列（2026-11-10，failure log #118）：先取合計列，沒有就把長短期兩列有值的加起來。
#: `info.totalDebt` 含租約（IQE.L 2026-06-30：5,394 萬英鎊＝借款 1,141 萬＋租賃 4,253 萬），負債燈要比的是借款。
LEASE_TOTAL_ROW = "Capital Lease Obligations"
LEASE_PART_ROWS: tuple[str, ...] = ("Long Term Capital Lease Obligation", "Current Capital Lease Obligation")
BALANCE_SHEET_TOTAL_DEBT_ROW = "Total Debt"
#: 52／53 週制的季末與日曆月底最多差一週，而 Yahoo 季報表的欄用日曆月底標（LITE `mostRecentQuarter` 2026-09-26 → 欄 2026-09-30、
#: AVGO 2026-08-02 → 欄 2026-07-31）。
QUARTER_LABEL_DRIFT_DAYS = 7
#: yfinance info 的金額是 float32 轉來的（MXL info.totalDebt 186,004,992 vs 季報表 186,005,000）：float32 約 7 位有效數字，
#: 相對差 1e-6 以內算同一個數。
SAME_NUMBER_REL = 1e-6


def _column_date(column) -> date | None:
    if hasattr(column, "date"):
        try:
            return column.date()
        except (TypeError, ValueError):
            return None
    try:
        return date.fromisoformat(str(column)[:10])
    except ValueError:
        return None


def _same_number(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= SAME_NUMBER_REL * max(abs(a), abs(b), 1.0)


def lease_liabilities_from_balance_sheet(frame, period_end: date | None, total_debt: float | None) -> float | None:
    """`frame`：yfinance `quarterly_balance_sheet`（列＝科目、欄＝期末日）。租賃必須取自 **`info.totalDebt` 那一季**的欄，
    不拿別季的拼（INV-6）——Yahoo 季報表常晚 info 一季（2026-11-10：AXTI info 已是第三季、表只到第二季），落後的時候就是分不出。

    找那一欄：①Total Debt 跟 `info.totalDebt` 是同一個數的欄（KSHINTL.NS：`mostRecentQuarter` 寫 6 月，info 的總債其實是 3 月那一欄）；
    ②沒有就取離 `period_end`（`mostRecentQuarter`）一週內最近的欄，再核一次 info 的總債**確實含租賃**——它離「含租賃的總債」比離
    「扣掉租賃的借款」近才扣（3234.TWO info 3.983 億 vs 季報表 3.999 億、扣掉租賃 3.003 億台幣）；離借款比較近＝info 的總債本來
    就不含租賃，扣了會把借款低估、塗成綠 → None。
    那一欄裡：合計列有值 → 它；否則長短期兩列有值的加總；租賃列都沒有值、但 Total Debt 有值 → 0.0（那一季的總債裡沒有租賃這一項——
    量到的零，不是沒量）；都找不到 → None（分不出租賃）。
    """
    if frame is None or getattr(frame, "empty", True) or total_debt is None:
        return None

    def cell(row: str, column) -> float | None:
        if row not in frame.index:
            return None
        try:
            return _sf(frame.loc[row, column])
        except (TypeError, ValueError, KeyError):
            return None

    def lease_of(column) -> float | None:
        total = cell(LEASE_TOTAL_ROW, column)
        if total is not None:
            return total
        parts = [value for value in (cell(row, column) for row in LEASE_PART_ROWS) if value is not None]
        if parts:
            return sum(parts)
        return 0.0 if cell(BALANCE_SHEET_TOTAL_DEBT_ROW, column) is not None else None

    same = [c for c in frame.columns if _same_number(cell(BALANCE_SHEET_TOTAL_DEBT_ROW, c), total_debt)]
    if same:
        return lease_of(same[0])
    if period_end is None:
        return None
    near = sorted((abs((d - period_end).days), i) for i, c in enumerate(frame.columns)
                  if (d := _column_date(c)) is not None and abs((d - period_end).days) <= QUARTER_LABEL_DRIFT_DAYS)
    if not near:
        return None
    column = frame.columns[near[0][1]]
    lease = lease_of(column)
    if not lease:                      # None（分不出）或量到的 0——0 不必再核含不含
        return lease
    bs_total = cell(BALANCE_SHEET_TOTAL_DEBT_ROW, column)
    if bs_total is None:
        return None
    return lease if abs(total_debt - bs_total) < abs(total_debt - (bs_total - lease)) else None


def _quarter_lease_liabilities(ticker_obj, info: dict, ticker: str) -> float | None:
    """與 `info.totalDebt` 同一季的租賃負債；取不到一律 None（燈照總債判並說分不出），不是 0。"""
    total_debt = _sf(info.get("totalDebt"))
    if total_debt is None:
        return None
    period_end = epoch_to_date(info.get("mostRecentQuarter"))
    try:
        frame = ticker_obj.quarterly_balance_sheet
    except Exception as exc:  # noqa: BLE001 — provider 失敗只降級成「分不出租賃」
        print(f"[etl] WARN: quarterly_balance_sheet failed for {ticker}: {exc}", file=sys.stderr)
        return None
    lease = lease_liabilities_from_balance_sheet(frame, period_end, total_debt)
    if lease is None and frame is not None and not getattr(frame, "empty", True):
        print(f"[etl] WARN: {ticker} 季報表找不到 info.totalDebt 那一季（mostRecentQuarter {period_end}）的租賃——"
              "負債燈照總債判", file=sys.stderr)
    return lease


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
    lease = _quarter_lease_liabilities(t, info, ticker)
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
        # 2026-10-29：歸零燈分「本業燒錢」（營業現金流 < 0）與「擴產花錢」（營業現金流 ≥ 0、自由現金流 < 0）。
        "operating_cash_flow_ttm": _sf(info.get("operatingCashflow")),
        # 2026-11-10（#118）：與 total_debt 同一季的租賃負債——負債燈比總債扣掉它的借款；租賃另列。
        "lease_liabilities":    lease,
        "ev_revenue":           _sf(info.get("enterpriseToRevenue")),
        "pe_trailing":          _sf(info.get("trailingPE")),
        "pe_forward":           _sf(info.get("forwardPE")),
        "price":                price,
        # 2026-09-13：**資產負債表與營收欄位的幣別**，與 `price` 的報價幣別不是同一件事。
        # ADR／跨市場掛牌（XPEV＝CNY 財報／USD 報價）兩者不同，而 EV／Sales 會把
        # 內部營收減這裡的淨負債——混幣別相減會靜默算錯。讀不到就留 None，不猜。
        "financial_currency":   (str(info.get("financialCurrency")).upper()
                                 if info.get("financialCurrency") else None),
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
