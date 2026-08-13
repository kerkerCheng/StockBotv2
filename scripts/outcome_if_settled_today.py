"""若今天結算：對有 Shadow 錨點的 cohort 計算實際報酬（唯讀）。

回答的問題是「系統過去的判斷準不準」——這是 `outcome_envelopes` 本該承擔、但至今
0 筆真實量測的那件事（8 筆全是開發驗證與 cohort 合併簿記）。

**本腳本完全唯讀**：不 close cohort、不寫 Decision Store、不寫 Engine C、不改任何
authority。它只是把既有的 Shadow 錨點與 Engine C 價格序列組起來，讓「系統的判斷準
不準」第一次能用證據回答。要真正結算仍須 `decision_lab close`（人工）。

兩個必須小心的地方，都已 fail closed：

1. **報價單位 ≠ 結算幣別。** Shadow 存的 IQE.L 是 `GBP` 0.407（英鎊），Engine C 存的
   是 44.8（`GBp` 便士）。直接相除得 +10,900% 而不是 +10%。所有價格一律先經
   `identity.currency` 正規化成結算幣別；未登記且非 ISO 形式一律 fail closed。
2. **錨點日期不能將就。** Shadow 價格就是 Decision Store 認定的追蹤起點，它是 authority；
   不得為了「與現價同源、單位自動相消」而改用鄰近日期的 Engine C 快照。首版曾這麼做，
   結果 COHR 拿 07-18 的價格當 07-21 的錨點，把 +12.1% 報成 +28.1%——**單位安全換來
   日期錯誤，是更糟的交換**。

⚠ **現價不取自 Engine C `financial_snapshots`。** 2026-08-13 查證 `snapshot_date` 是
「跑 ETL 的日期」而非行情交易日：收盤後跑的那批被標成隔天（`fetched_at` 07-28 22:34
取到 07-28 收盤 42.76，卻標 `snapshot_date=07-29`），盤中跑的那批存的是盤中價。一個
欄位承載三種語意（L12），拿它當 as-of 會系統性差一天。現價改取 provider 最新**已收盤**
bar 並帶明確交易日；Engine C 僅用於不依賴日期的單位量級 sanity check。

用法：
    python scripts/outcome_if_settled_today.py
    python scripts/outcome_if_settled_today.py --no-benchmark   # 不連外
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identity.currency import resolve_quote_unit  # noqa: E402
from identity.registry import get_registry  # noqa: E402

DECISION_DB = ROOT / "library" / "private" / "decision_lab" / "decision_lab.db"
POINTER = ROOT / "library" / "private" / "runtime_pointer.json"

# 主基準 QQQ 依 2026-08-08 定案（alpha 標的全是科技／半導體，拿含金融、能源的全球
# 指數當基準會系統性美化結果）。SOXX 只作參考欄——registry 目前沒有 sector 欄位，
# 而「不採 provider 推斷的 sector」是幣別那條路教過的錯誤，所以不做自動覆寫。
PRIMARY_BENCHMARK = "QQQ"
REFERENCE_BENCHMARK = "SOXX"

# 單位 sanity check 的可接受量級區間（Engine C 最新價 ÷ provider 最新價）。
# 差一兩個交易日落在區間內；GBp/GBP 這種登記錯誤會是 ~100x，必然出界。
UNIT_SANITY_RANGE = (0.5, 2.0)


def _connect_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _engine_c_path() -> Path:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    return ROOT / "library" / "private" / pointer["engine_c"]


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _to_settlement(price: float | None, quote_code: str | None) -> tuple[float | None, str | None]:
    """回傳 (結算幣別金額, 結算幣別)；無法解析一律 (None, None) —— fail closed。"""
    if price is None or quote_code is None:
        return None, None
    unit = resolve_quote_unit(str(quote_code))
    if unit is None:
        return None, None
    return unit.to_settlement(float(price)), unit.currency


def _load_shadows() -> list[dict]:
    with _connect_ro(DECISION_DB) as conn:
        rows = conn.execute(
            """
            SELECT s.shadow_id, s.cohort_id, s.status, s.ticker, s.price, s.currency,
                   s.as_of, c.company_id, c.research_ticker
              FROM shadow_observations s
              LEFT JOIN decision_cohorts c ON c.cohort_id = s.cohort_id
             ORDER BY s.created_at
            """
        ).fetchall()
    return [dict(r) for r in rows]


def _market_quote_unit(company_id: str | None, ticker: str | None) -> str | None:
    """registry 登記的**報價**單位（IQE.L 是 GBp，不是 GBP）。"""
    registry = get_registry()
    cid = company_id
    if not cid and ticker:
        cid = registry.company_id_for_ticker(ticker)
    if not cid or not registry.has_company(cid):
        return None
    company = registry.company(cid)
    for key in ("market_quote_unit", "market_currency"):
        value = getattr(company, key, None) if not isinstance(company, dict) else company.get(key)
        if value:
            return str(value)
    return None


def _snapshots(conn: sqlite3.Connection, ticker: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT snapshot_date, price FROM financial_snapshots "
        "WHERE ticker = ? AND price IS NOT NULL ORDER BY snapshot_date",
        (ticker,),
    ).fetchall()


def _latest_close(ticker: str) -> tuple[date, float] | None:
    """最新一根**已收盤** bar 的 (交易日, 收盤價)，單位為 provider 報價單位。"""
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(period="1mo", auto_adjust=True)["Close"].dropna()
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ {ticker} 收盤序列抓取失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    if hist.empty:
        return None
    return hist.index[-1].date(), float(hist.iloc[-1])


def _benchmark_series(symbols: list[str], start: date, end: date) -> dict[str, dict[date, float]]:
    try:
        import yfinance as yf
    except ImportError:
        return {}
    out: dict[str, dict[date, float]] = {}
    for symbol in symbols:
        try:
            hist = yf.Ticker(symbol).history(
                start=(start - timedelta(days=7)).isoformat(),
                end=(end + timedelta(days=2)).isoformat(),
                auto_adjust=True,
            )
            out[symbol] = {
                ts.date(): float(close)
                for ts, close in hist["Close"].items()
                if close == close  # NaN guard
            }
        except Exception as exc:  # noqa: BLE001 — 基準抓不到只降級，不中斷報表
            print(f"  ⚠ benchmark {symbol} 抓取失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
    return out


def _at_or_before(series: dict[date, float], target: date) -> tuple[date, float] | None:
    candidates = [d for d in series if d <= target]
    if not candidates:
        return None
    best = max(candidates)
    return best, series[best]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-benchmark", action="store_true", help="不連外抓基準")
    args = parser.parse_args()

    shadows = _load_shadows()
    observed = [s for s in shadows if s["status"] == "observed"]
    unavailable = [s for s in shadows if s["status"] != "observed"]

    engine_c = _engine_c_path()
    results: list[dict] = []

    with _connect_ro(engine_c) as conn:
        for shadow in observed:
            ticker = shadow["ticker"] or shadow["research_ticker"]
            row: dict = {
                "ticker": ticker,
                "company_id": shadow["company_id"],
                "anchor_date": _as_date(shadow["as_of"]),
                "note": [],
            }
            quote_unit = _market_quote_unit(shadow["company_id"], ticker)
            snaps = _snapshots(conn, ticker) if ticker else []

            # 現價：直接取 provider 收盤並帶明確 bar date。
            # **不用 Engine C 的 snapshot_date**——2026-08-13 查證該欄是「跑 ETL 的
            # 日期」而非行情交易日，收盤後跑的那批被標成隔天（fetched 07-28 22:34
            # 取到 07-28 收盤 42.76，卻標 snapshot_date=07-29），盤中跑的那批則是
            # 盤中價。一個欄位承載三種語意（L12），拿它當 as-of 會系統性差一天。
            bar = _latest_close(ticker) if ticker else None
            if bar:
                row["current_date"], row["current_raw"] = bar
            else:
                row["note"].append("provider 無此 ticker 的收盤序列 → 不計算")

            # 錨點永遠是 Shadow 價格（Decision Store 的追蹤起點 authority）。
            # 兩端各自正規化成結算幣別後才相除。
            anchor_val, anchor_ccy = _to_settlement(shadow["price"], shadow["currency"])
            current_val, current_ccy = _to_settlement(row.get("current_raw"), quote_unit)

            if anchor_val is None:
                row["note"].append(
                    f"Shadow 報價單位無法解析（{shadow['currency']!r}）→ fail closed，不計算"
                )
            elif current_val is None:
                row["note"].append(
                    f"Engine C 報價單位無法解析（registry={quote_unit!r}）→ fail closed，不計算"
                )
            elif anchor_ccy != current_ccy:
                row["note"].append(
                    f"結算幣別不一致（shadow={anchor_ccy} / engine_c={current_ccy}）→ fail closed"
                )
            elif anchor_val <= 0:
                row["note"].append("Shadow 錨點價格非正數 → 不計算")
            else:
                row["absolute_return"] = current_val / anchor_val - 1.0
                row["anchor_raw"] = shadow["price"]
                row["anchor_ccy"] = anchor_ccy
                row["anchor_source"] = (
                    f"shadow@{row['anchor_date']}"
                    f"（{shadow['price']} {shadow['currency']} → {anchor_val:.4f} {anchor_ccy}）"
                )

            # 單位 sanity check：刻意**不依賴日期**。
            # 首版拿 Shadow 與「同日」Engine C 快照對比，但那個前提是錯的——
            # snapshot_date 不是交易日（見上方 _latest_close 的註解），於是 AXTI／META
            # 被報成 8.2%／5.2% 的假價差。真正要防的是報價單位登記錯誤（GBp 當成 GBP
            # 會差 100 倍），那是量級問題、與日期無關：拿 Engine C 最新價與 provider
            # 最新價比量級即可，差一兩個交易日不影響判斷。
            if current_val and snaps:
                e_val, e_ccy = _to_settlement(float(snaps[-1]["price"]), quote_unit)
                if e_val and e_ccy == current_ccy and current_val > 0:
                    ratio = e_val / current_val
                    if not UNIT_SANITY_RANGE[0] <= ratio <= UNIT_SANITY_RANGE[1]:
                        row["note"].append(
                            f"⚠ Engine C 與 provider 價格量級不符（比值 {ratio:.4g}）"
                            f"——疑似報價單位登記錯誤，registry={quote_unit!r}"
                        )

            results.append(row)

    # 基準
    benchmarks: dict[str, dict[date, float]] = {}
    dated = [r for r in results if r.get("anchor_date") and r.get("current_date")]
    if not args.no_benchmark and dated:
        start = min(r["anchor_date"] for r in dated)
        end = max(r["current_date"] for r in dated)
        benchmarks = _benchmark_series([PRIMARY_BENCHMARK, REFERENCE_BENCHMARK], start, end)

    for row in results:
        for symbol in (PRIMARY_BENCHMARK, REFERENCE_BENCHMARK):
            series = benchmarks.get(symbol)
            if not series or not row.get("anchor_date") or row.get("absolute_return") is None:
                continue
            a = _at_or_before(series, row["anchor_date"])
            b = _at_or_before(series, row["current_date"])
            if a and b and a[1] > 0 and a[0] != b[0]:
                row[f"bench_{symbol}"] = b[1] / a[1] - 1.0
                row[f"excess_{symbol}"] = row["absolute_return"] - row[f"bench_{symbol}"]

    _render(results, unavailable, bool(benchmarks))
    return 0


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:+.1f}%"


def _render(results: list[dict], unavailable: list[dict], has_bench: bool) -> None:
    print(f"# 若今天結算（{date.today().isoformat()}）— 唯讀，未寫入任何 authority\n")
    header = f"| {'標的':9} | {'錨點日':10} | {'現價日':10} | {'絕對報酬':>9} |"
    rule = f"|{'-' * 11}|{'-' * 12}|{'-' * 12}|{'-' * 11}|"
    if has_bench:
        header += f" {'QQQ':>8} | {'超額(QQQ)':>10} | {'SOXX':>8} |"
        rule += f"{'-' * 10}|{'-' * 12}|{'-' * 10}|"
    print(header)
    print(rule)

    measured = 0
    for row in sorted(results, key=lambda r: -(r.get("absolute_return") or -9)):
        line = (
            f"| {str(row['ticker']):9} | {str(row.get('anchor_date') or '—'):10} "
            f"| {str(row.get('current_date') or '—'):10} | {_pct(row.get('absolute_return')):>9} |"
        )
        if has_bench:
            line += (
                f" {_pct(row.get(f'bench_{PRIMARY_BENCHMARK}')):>8} "
                f"| {_pct(row.get(f'excess_{PRIMARY_BENCHMARK}')):>10} "
                f"| {_pct(row.get(f'bench_{REFERENCE_BENCHMARK}')):>8} |"
            )
        print(line)
        if row.get("absolute_return") is not None:
            measured += 1

    print(f"\n**已量測 {measured} / {len(results)} 個有 Shadow 錨點的 cohort。**")
    if unavailable:
        print(f"另有 {len(unavailable)} 個 cohort 的 Shadow 是 `unavailable`，無錨點可計算。")

    notes = [(r["ticker"], n) for r in results for n in r.get("note", [])]
    if notes:
        print("\n## 註記與資料缺口\n")
        for ticker, note in notes:
            print(f"- **{ticker}**：{note}")

    print("\n## 錨點來源\n")
    for row in results:
        if row.get("anchor_source"):
            print(f"- **{row['ticker']}**：{row['anchor_source']}（原始值 {row.get('anchor_raw')}）")


if __name__ == "__main__":
    raise SystemExit(main())
