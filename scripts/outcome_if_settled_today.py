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

# 錨點前回看天數（日曆日）。原本的用途是分辨「系統在追高」與「系統在低點接」。
#
# ⚠⚠ **2026-08-18 使用者指出、當日查證屬實：本報表的超額欄不能當成選股能力證據。**
# 兩個查證結果：
#   1. `decision_cohorts.dedupe_key` **全部**是 `claim:<hash>`——cohort 由**入圖**建立，
#      不是由「現在可以買」的判斷建立。錨點日的真實語意是「這家公司的 claim 那天進圖」。
#   2. 10 個 observed 錨點全部落在 2026-07-21 ~ 08-14（24 天），而 SOXX 在 07-28 見底，
#      正好在窗口正中間；全部又同屬 AI 光通訊主題。
# 合起來：**n 實際上是 1，不是 10**——一次 sector 移動被高度相關的標的複製了 10 次，
# 而那個窗口就是系統被建起來的期間。
#
# 因此本欄的正確讀法是「這批 cohort 是在什麼行情位置被建立的」，**不是**「系統挑得準不準」。
# 首版的結論行寫成「本輪不是追高形狀」，讀起來像背書——那是 L14 說的**接錯資料源的
# 計數器＝反向防呆**，比沒有計數器更糟。已改為強制先講清楚錨點的語意與樣本獨立性。
#
# 要讓這張表變成真的證據，需要的不是更多列，而是**錨點來自進場判斷**：
# 見 `docs/brainstorms/2026-08-18-alpha-live-user-sized-requirements.md` §7。
PRE_ANCHOR_DAYS = 30

# 錨點集中度警示門檻：跨度短於此天數就視為「同一次行情」，不得當成獨立樣本。
#
# ⚠ **跨度只是次要條件，不是主要判準。** 首版把紅字綁在跨度上，但跨度會隨 cohort 累積
# 自然超過 60 天，於是紅字**會自己關掉——而錨點仍然是入圖日、仍然不是進場判斷**。
# 語意問題沒被修，警報卻不響了（2026-08-18 紅隊審查抓到；同一形狀我當天早上才批評過）。
# 主要判準改成下方 `_judgment_anchor_count()`：有幾筆錨點真的來自使用者的進場決定。
ANCHOR_SPAN_WARN_DAYS = 60


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


def _provider_series(ticker: str, start: date) -> dict[date, float]:
    """provider 已收盤序列 {交易日: 收盤價}，單位為 provider 報價單位。

    一次抓足回看窗與現價，避免同一檔重複請求。單位不在此正規化——本序列的兩個用途
    （現價、錨點前漲幅）一個之後會正規化、一個是同序列相除，比值自動消單位。
    """
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(
            start=start.isoformat(), auto_adjust=True
        )["Close"].dropna()
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ {ticker} 收盤序列抓取失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        return {}
    return {ts.date(): float(close) for ts, close in hist.items() if close == close}


def _pre_anchor_return(series: dict[date, float], anchor: date) -> float | None:
    """錨點前 PRE_ANCHOR_DAYS 日的漲跌幅。

    ⚠ 兩端都取自**同一條 provider 序列**，不混入 Shadow 價格。Shadow 與 provider 的
    報價單位／還權基準未必相同，混用會重蹈 GBp/GBP 那類 100 倍錯誤；同序列相除則
    比值自動消單位，不需要 `_to_settlement`。
    """
    at = _at_or_before(series, anchor)
    before = _at_or_before(series, anchor - timedelta(days=PRE_ANCHOR_DAYS))
    if not at or not before or before[1] <= 0 or at[0] == before[0]:
        return None
    return at[1] / before[1] - 1.0


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
            anchor_date = row["anchor_date"]
            series = (
                _provider_series(
                    ticker,
                    (anchor_date or date.today()) - timedelta(days=PRE_ANCHOR_DAYS + 15),
                )
                if ticker
                else {}
            )
            if series:
                bar_date = max(series)
                row["current_date"], row["current_raw"] = bar_date, series[bar_date]
                if anchor_date:
                    row["pre_anchor_return"] = _pre_anchor_return(series, anchor_date)
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
    header = (
        f"| {'標的':9} | {'錨點日':10} | {'現價日':10} "
        f"| {f'錨點前{PRE_ANCHOR_DAYS}日':>10} | {'絕對報酬':>9} |"
    )
    rule = f"|{'-' * 11}|{'-' * 12}|{'-' * 12}|{'-' * 12}|{'-' * 11}|"
    if has_bench:
        header += f" {'QQQ':>8} | {'超額(QQQ)':>10} | {'SOXX':>8} |"
        rule += f"{'-' * 10}|{'-' * 12}|{'-' * 10}|"
    print(header)
    print(rule)

    measured = 0
    for row in sorted(results, key=lambda r: -(r.get("absolute_return") or -9)):
        line = (
            f"| {str(row['ticker']):9} | {str(row.get('anchor_date') or '—'):10} "
            f"| {str(row.get('current_date') or '—'):10} "
            f"| {_pct(row.get('pre_anchor_return')):>10} "
            f"| {_pct(row.get('absolute_return')):>9} |"
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

    _render_chase_check(results)


def _judgment_anchor_count() -> int:
    """有幾筆 live choice 帶著使用者的進場判斷（`user_sized` 或明確接受系統區間）。

    這是「這張表算不算證據」的主要判準，取代原本綁在錨點跨度上的警示——
    跨度會隨時間自然增長而讓警報自己關掉，這個數字不會。
    """
    try:
        with _connect_ro(DECISION_DB) as conn:
            row = conn.execute(
                "SELECT count(*) AS n FROM live_choices WHERE selected_weight > 0"
            ).fetchone()
        return int(row["n"] or 0)
    except sqlite3.Error:
        # 讀不到就當 0——fail closed。宣稱「已被量測」的舉證責任在有資料那一方。
        return 0


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _render_chase_check(results: list[dict]) -> None:
    """錨點體檢：常駐輸出，不需要任何人記得去跑。

    存在理由見 `2026-08-13-capital-expression-direction` §6——那一節的結論是
    「檢查點住在一份要人主動想起來去讀的文件裡」就會失效。

    ⚠ 本段**刻意先講樣本效度、再講數字**。反過來寫的話，讀者會先看到「超額 +11%」
    再把 caveat 當客套話——首版正是那樣，於是一份有效 n=1 的觀測讀起來像 10 個
    獨立驗證。這是 L14 說的「接錯資料源的計數器＝反向防呆」。
    """
    paired = [
        r
        for r in results
        if r.get("pre_anchor_return") is not None and r.get("absolute_return") is not None
    ]
    if not paired:
        return

    anchors = sorted(r["anchor_date"] for r in paired)
    span = (anchors[-1] - anchors[0]).days
    weeks = len({(d.isocalendar()[0], d.isocalendar()[1]) for d in anchors})
    judgment = _judgment_anchor_count()

    print(f"\n## 錨點體檢（列 {len(paired)} 筆）\n")
    print(
        f"- **來自進場判斷的錨點：{judgment} 筆**"
        f"（`live_choices.decided_at`）｜來自入圖日：{len(paired)} 筆"
    )
    print(
        f"- 錨點跨度：{anchors[0]} ~ {anchors[-1]}（{span} 天）｜獨立日曆週數：{weeks}"
    )

    # 主要判準：有沒有任何一筆錨點帶進場判斷語意。**這個條件不會因為時間經過而自動滿足。**
    if judgment == 0:
        print(
            "\n🔴 **沒有任何錨點來自進場判斷——本表不構成選股能力的證據。**\n"
            "  cohort 由入圖建立（`dedupe_key=claim:*`），錨點的語意是「這家公司的 claim"
            " 那天進圖」，不是「那天該買」。下方數字只描述**這批標的是在什麼行情位置入圖的**。\n"
            "  要讓這張表變成證據，需要的不是等更久，是讓錨點帶有進場判斷——"
            "`decision_lab record-choice --user-sized` 的 `decided_at` 天生就是那個錨點。"
        )
    # 次要判準：即使已有判斷錨點，樣本仍可能擠在同一次行情裡。
    if span < ANCHOR_SPAN_WARN_DAYS:
        print(
            f"\n🟠 **錨點跨度僅 {span} 天——不得視為 {len(paired)} 個獨立樣本。**"
            " 這批 cohort 建立於同一段期間，若又同屬一個主題，超額很可能是**同一次行情**"
            "被相關標的複製多次（有效 n 接近 1）。"
        )

    chasing = [r for r in paired if r["pre_anchor_return"] > r["absolute_return"]]
    pre_med = _median([r["pre_anchor_return"] for r in paired])
    post_med = _median([r["absolute_return"] for r in paired])
    print(
        f"\n- 錨點前 {PRE_ANCHOR_DAYS} 日中位：{_pct(pre_med)}｜錨點後中位：{_pct(post_med)}\n"
        f"- 錨點前漲幅大於錨點後：{len(chasing)} / {len(paired)}"
        + (f"（{'、'.join(str(r['ticker']) for r in chasing)}）" if chasing else "")
    )
    if pre_med > 0:
        print(
            "\n⚠ 錨點前中位為正——這批標的在入圖前已經在漲。日後若把錨點改成真正的"
            "進場判斷日，這一段必須先扣掉。"
        )

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
