"""若今天結算：對有 Shadow 錨點的 cohort 計算實際報酬（不寫任何 authority）。

回答的問題是「系統過去的判斷準不準」——這是 `outcome_envelopes` 本該承擔、但至今
0 筆真實量測的那件事（8 筆全是開發驗證與 cohort 合併簿記）。

**本腳本不寫任何 authority**：不 close cohort、不寫 Decision Store、不寫 Engine C、不改任何
authority。它只是把既有的 Shadow 錨點與 Engine C 價格序列組起來，讓「系統的判斷準
不準」第一次能用證據回答。要真正結算仍須 `decision_lab close`（人工）。
⚠ **但它不是「完全唯讀」**（2026-09-24 Phase 1 Step 1.2a 更正原句）：render 時會寫兩個 ignored
private runtime 檔——`library/private/decision_lab/outcome_aggregate.json`（當日聚合）與
`outcome_aggregate.jsonl`（逐日序列）。它們在凍結舊店的目錄裡，但不是 `*.db`，所以舊店 sha256
比對不涵蓋（Phase 1 baseline §9）；daily 的 sandbox impact review 把它們列在寫入範圍內。

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
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

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
        # epoch 錨點 overlay（workstream #2，2026-09-02）：cohort 重開 epoch 後，
        # 量測起點應是重開當下的錨（reopen 時以 epoch_anchor event 記錄），
        # 不是 epoch 1 的 shadow——否則「重開後的判斷準不準」與舊判斷混在同一數字。
        # shadow 本體不覆寫（append-only）；這裡只在讀取端 overlay 最新一筆。
        anchors: dict[str, dict] = {}
        for row in conn.execute(
            """
            SELECT cohort_id, payload_json FROM decision_events
             WHERE event_type = 'epoch_anchor' ORDER BY observed_at
            """
        ):
            try:
                payload = json.loads(row["payload_json"])
                anchors[str(row["cohort_id"])] = {
                    "price": float(payload["price"]),
                    "currency": str(payload["currency"]),
                    "as_of": str(payload["as_of"]),
                    "epoch": payload.get("epoch"),
                }
            except (ValueError, TypeError, KeyError):
                continue
    shadows = [dict(r) for r in rows]
    for shadow in shadows:
        overlay = anchors.get(str(shadow["cohort_id"]))
        if overlay and shadow["status"] == "observed":
            shadow.update(
                price=overlay["price"], currency=overlay["currency"],
                as_of=overlay["as_of"], anchor_epoch=overlay["epoch"],
            )
    return shadows


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


def _peak_since(series: dict[date, float], anchor: date | None) -> tuple[float | None, date | None]:
    """錨點日（含）之後的最高收盤，與它出現的那一天。

    power-law 量測要問的是「**有沒有抓到倍數**」，而 D3 定案「目標價到了只提醒、
    出場只認反證」——所以標的可能一路抱著，用期末價會系統性低估「抓到過幾倍」。
    期末與期間高點是**兩個不同的問題**，兩個都要有答案，不得壓成一個數字（L12）。
    """
    if not anchor:
        return None, None
    after = [(d, v) for d, v in series.items() if d >= anchor and v > 0]
    if not after:
        return None, None
    best = max(after, key=lambda kv: kv[1])
    return best[1], best[0]


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


def _history_rows() -> tuple[list[dict], list[dict]]:
    """history lane（舊店 observed shadow 的入圖日錨點；凍結只印、不再新增）。

    ⚠ **這是原 `collect()` 的逐列計算，一字不動地搬進自己的函式**（Phase 5 Step 5.2，plan §3：「程式路徑不動，只改名
    與分段」）。基準那段迴圈抽成 `_apply_benchmarks`，三條 lane 共用。回 `(results, unavailable)`。
    """
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
                # 期間高點與 `absolute_return` 用**同一個分母**（Shadow 錨點，authority），
                # 否則「曾達 2 倍、現在剩 1.3 倍」這句話的兩個數字不可比。
                peak_raw, peak_date = _peak_since(series, anchor_date)
                peak_val, peak_ccy = _to_settlement(peak_raw, quote_unit)
                if peak_val is not None and peak_ccy == anchor_ccy:
                    row["peak_return"] = peak_val / anchor_val - 1.0
                    row["peak_date"] = peak_date
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

    return results, unavailable


def _apply_benchmarks(rows: list[dict], benchmarks: Mapping[str, Mapping[date, float]]) -> None:
    """每列對 QQQ／SOXX 的同期報酬與超額。**原 `collect()` 的那段迴圈原樣搬出**，三條 lane 共用（一份算法）。"""
    for row in rows:
        for symbol in (PRIMARY_BENCHMARK, REFERENCE_BENCHMARK):
            series = benchmarks.get(symbol)
            if not series or not row.get("anchor_date") or row.get("absolute_return") is None:
                continue
            a = _at_or_before(series, row["anchor_date"])
            b = _at_or_before(series, row["current_date"])
            if a and b and a[1] > 0 and a[0] != b[0]:
                row[f"bench_{symbol}"] = b[1] / a[1] - 1.0
                row[f"excess_{symbol}"] = row["absolute_return"] - row[f"bench_{symbol}"]


# ---------------------------------------------------------------------------
# 三條 lane（Phase 5 Step 5.2；plan §0.4 A1）：「買得準不準」與「判斷準不準」要兩個分母（L12）
# ---------------------------------------------------------------------------

#: 新 lane（paper＋live）＋主題等權組成員＋基準，去重後一輪最多取價幾檔——**這是無人值守的網路 surface 上限**
#: （daily 步驟 05 跑本腳本；照 `engine_b/account_scorecard.py::MAX_PRICED_SYMBOLS` 的做法）：超過就截斷、截掉的印出來，
#: 基準永遠留著。history lane 的 22 檔沿用原路徑、不在這個上限裡（plan §3 sandbox impact review）。
MAX_LANE_SYMBOLS = 60

TRADE_LOG = ROOT / "library" / "trades" / "trade_log.jsonl"
LEADS_PATH = ROOT / "library" / "leads" / "pending_leads.json"

#: 三條 lane。**分印、分母分開**——壓成一張表就是 L12（一個表示承載兩種語意）。
LANE_KEYS: tuple[str, ...] = ("live", "paper", "history")
LANE_LABELS: Mapping[str, str] = {
    "live": "我們真的買的：trade_log 的 alpha 成交（錨＝成交價、成交日）",
    "paper": "我們寫下判斷的：每檔第一份 v2 敘事寫下那天（錨＝那天收盤）",
    "history": "舊店入圖日：凍結只印、不再新增（錨＝claim 進圖那天，不含判斷）",
}
#: 各 lane 的錨點偏差，跟著 power-law 三量走（取代 history 那條「錨點是入圖日」——那句話對另兩條 lane 是錯的）。
LANE_ANCHOR_BIAS: Mapping[str, str] = {
    "history": "錨點是入圖日，不含任何進場時點判斷——這張表量的是「排序有沒有選到會漲的」，"
               "不是「我們買得準不準」。",
    "paper": "錨點是我們寫下判斷那天（第一份 v2 敘事）的收盤——量的是**判斷**不是進場；美股與歐股在台北下午寫下時"
             "還沒收盤，錨點含當天盤中的變動（同日內的前視，最多一個交易日）。",
    "live": "錨點是真實成交價——量的是買得準不準；樣本只有真實下單才會變大，時間經過不會讓它自己滿足。",
}
#: lane 空時印這句，不印 0%（L12：「還沒有列」與「有列但是 0」是相反的結論）。
LANE_EMPTY: Mapping[str, str] = {
    "live": "還沒有列——trade_log 還沒有任何 alpha 成交事件（舊成交由使用者用 `record_trade.py --backfill-before-receipts` 回填）",
    "paper": "還沒有列——還沒有任何一檔寫下 v2 敘事",
    "history": "還沒有列——舊店沒有 observed 的 shadow 錨點",
}


def _local_day(stamp: Any) -> date | None:
    """排程時區的日期（UTC 時戳不直接取 `.date()`）。規則與收據同一支：`portfolio.research_receipt._local_date`。"""
    from portfolio.research_receipt import _local_date

    return _local_date(stamp)


def _read_trade_log(path: Path) -> tuple[list[dict], list[str]]:
    """trade_log（append-only）。檔案不存在＝還沒有任何成交（不是讀不到）；壞行列進 problems，不靜默丟棄（INV-3）。"""
    if not path.is_file():
        return [], []
    events: list[dict] = []
    problems: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            problems.append(f"trade_log 第 {number} 行解析失敗——live lane 可能少列，不靜默當成沒有")
            continue
        if isinstance(event, dict):
            events.append(event)
        else:
            problems.append(f"trade_log 第 {number} 行不是 object")
    return events, problems


def _receipt_summary(receipt: Any) -> dict:
    """成交事件的研究收據 → live lane 的那一格（照抄，不重讀今天的敘事——不拿今天的判斷冒充當時）。"""
    if not isinstance(receipt, Mapping):
        return {"status": "receipt_absent",
                "label": "收據機制上線（2026-09-30）前的事件，沒有收據"}
    narrative = str(receipt.get("narrative") or "")
    if narrative == "backfilled":
        return {"status": "backfilled", "label": "回填：成交早於收據機制上線，當時沒有收據",
                "reason": receipt.get("backfill_reason")}
    declared = receipt.get("declared") if isinstance(receipt.get("declared"), Mapping) else {}
    state = declared.get("candidate_state")
    return {"status": narrative or "unknown", "label": receipt.get("narrative_label"),
            "brief_id": declared.get("brief_id"),
            "candidate_state": state.get("state") if isinstance(state, Mapping) else state,
            "answers": declared.get("answers")}


def live_lane_plan(events: Sequence[Mapping[str, Any]], *, is_beta: Callable[[str], bool],
                   resolve: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> dict:
    """trade_log → live lane 的列（**每一筆 alpha 買進一列**）。純函式，不取價。

    - alpha 判別只走 `risk.hard_caps.is_beta_symbol`（`beta_policy.json` 的 `sheet_aliases`；不自己再寫一份）。beta 事件
      只計數（「beta 事件 N 不進 lane」）。
    - 成交 symbol → 公司只走 `portfolio.holdings.resolve_holding`（INV-1）；`ticker` 是研究 ticker（解析不到才用成交代號）。
    - 賣出：同 symbol＋broker 的 FIFO，把最早一筆還沒結的買進列標 `closed`（賣出價＝終點）。股數不配對（plan §14 #7）。
    """
    buys: list[Mapping[str, Any]] = []
    sells: list[Mapping[str, Any]] = []
    beta_events = 0
    skipped: list[str] = []
    for event in sorted(events, key=lambda e: str(e.get("executed_at") or "")):
        symbol = str(event.get("symbol") or "").strip().upper()
        side = event.get("side")
        if not symbol or side not in ("buy", "sell"):
            skipped.append(f"{event.get('trade_id') or '?'}：symbol／side 不完整")
            continue
        if is_beta(symbol):
            beta_events += 1
            continue
        (buys if side == "buy" else sells).append(event)
    rows: list[dict] = []
    for event in buys:
        symbol = str(event["symbol"]).strip().upper()
        holding = resolve({"ticker": symbol}) or {}
        rows.append({
            "lane": "live",
            "ticker": holding.get("research_ticker") or symbol,
            "execution_symbol": symbol,
            "company_id": holding.get("company_id"),
            "research_ticker": holding.get("research_ticker"),
            "resolution": holding.get("source"),
            "trade_id": event.get("trade_id"),
            "broker": event.get("broker"),
            "executed_at": event.get("executed_at"),
            "anchor_date": _local_day(event.get("executed_at")),
            "anchor_raw": event.get("price"),
            "trade_currency": event.get("currency"),
            "shares": event.get("shares"),
            "receipt": _receipt_summary(event.get("research_receipt")),
            "closed": None,
            "note": [],
        })
    queues: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        queues[(row["execution_symbol"], str(row.get("broker") or ""))].append(row)
    unmatched: list[str] = []
    for event in sells:
        key = (str(event["symbol"]).strip().upper(), str(event.get("broker") or ""))
        queue = [r for r in queues.get(key, []) if r["closed"] is None]
        if not queue:
            unmatched.append(f"{event.get('trade_id') or '?'}（{key[0]}／{key[1]}）找不到可配對的買進")
            continue
        queue[0]["closed"] = {"trade_id": event.get("trade_id"), "executed_at": event.get("executed_at"),
                              "date": _local_day(event.get("executed_at")), "price": event.get("price"),
                              "currency": event.get("currency")}
        if event.get("shares") != queue[0].get("shares"):
            queue[0]["note"].append("賣出股數與這筆買進不同——只做 FIFO 配對、不做加權（plan §14 #7）")
    return {"rows": rows, "beta_events": beta_events, "unmatched_sells": unmatched, "skipped": skipped}


def _price_live_row(row: dict, *, series: Mapping[date, float], provider_unit: str | None, today: date) -> None:
    """live 列的報酬：錨＝成交價（成交幣別）；終點＝賣出價（已結）或**成交代號**的 provider 序列 today 或之前的收盤。
    兩端結算幣別必須相同——不同就 `currency_mismatch` 缺席，**不猜匯率**。"""
    from alpha.theme_cohort import close_on_or_before

    anchor = row.get("anchor_date")
    anchor_val, anchor_ccy = _to_settlement(row.get("anchor_raw"), row.get("trade_currency"))
    if anchor is None or anchor_val is None or anchor_val <= 0:
        row["absence_kind"] = "quote_unit_unresolved"
        row["note"].append(f"成交價或成交幣別無法解析（{row.get('anchor_raw')} {row.get('trade_currency')!r}）→ fail closed")
        return
    row.update(anchor_price=anchor_val, anchor_ccy=anchor_ccy,
               anchor_source=f"live@{anchor}（{row.get('trade_id')}；{row.get('anchor_raw')} {row.get('trade_currency')}）")
    closed = row.get("closed")
    if closed:
        end_day, end_raw, end_unit = closed.get("date"), closed.get("price"), closed.get("currency")
        row["realized"] = True
    else:
        bar = close_on_or_before(series, today) if series else None
        if bar is None:
            row["absence_kind"] = "no_price_series"
            row["note"].append(f"provider 沒有 {row.get('execution_symbol')} 的收盤序列 → 不計算")
            return
        end_day, end_raw, end_unit = bar[0], bar[1], provider_unit
        row["realized"] = False
    end_val, end_ccy = _to_settlement(end_raw, end_unit)
    if end_val is None:
        row["absence_kind"] = "quote_unit_unresolved"
        row["note"].append(f"終點報價單位無法解析（{end_unit!r}）→ fail closed")
        return
    if end_ccy != anchor_ccy:
        row["absence_kind"] = "currency_mismatch"
        row["note"].append(f"結算幣別不一致（成交 {anchor_ccy} / 終點 {end_ccy}）→ fail closed，不猜匯率")
        return
    row.update(current_date=end_day, current_raw=end_raw, current_price=end_val,
               absolute_return=end_val / anchor_val - 1.0)
    if series:
        window = {d: v for d, v in series.items() if end_day is None or d <= end_day}
        peak_raw, peak_date = _peak_since(window, anchor)
        peak_val, peak_ccy = _to_settlement(peak_raw, provider_unit)
        if peak_val is not None and peak_ccy == anchor_ccy:
            row["peak_return"] = max(peak_val, end_val) / anchor_val - 1.0
            row["peak_date"] = peak_date
        row["pre_anchor_return"] = _pre_anchor_return(series, anchor)


def _read_briefs(directory: Path | None = None) -> dict[str, tuple[list, list[str]]]:
    """敘事 ledger 每一本 → `(紀錄, 壞行)`。"""
    from alpha.providers.briefs import BRIEF_DIR, read_brief_records

    root = directory or BRIEF_DIR
    if not root.is_dir():
        return {}
    return {path.name[:-len(".jsonl")].upper(): read_brief_records(path.name[:-len(".jsonl")], directory=root)
            for path in sorted(root.glob("*.jsonl"))}


def first_named_by(company_id: str | None, leads: Mapping[str, Mapping[str, Any]]) -> dict | None:
    """最早點名本公司的 lead（`entities.company_ids` 含它、`first_seen` 最早者）：來源標籤跟著走到量測（AGENTS 量測段）。
    沒有回 `None`（呈現為 `no_lead_named`）。`first_seen` 是我們看到它的時間；`published_at` 另印、空就是空（INV-6）。"""
    if not company_id:
        return None
    hits = [lead for lead in leads.values()
            if company_id in (((lead or {}).get("entities") or {}).get("company_ids") or ())]
    if not hits:
        return None
    first = min(hits, key=lambda lead: (str(lead.get("first_seen") or "9999"), str(lead.get("lead_id") or "")))
    return {"lead_id": first.get("lead_id"), "source": first.get("source"), "first_seen": first.get("first_seen"),
            "published_at": first.get("published_at") or None}


def paper_lane_plan(briefs: Mapping[str, tuple[Sequence[Any], Sequence[str]]], *, today: date,
                    leads: Mapping[str, Mapping[str, Any]] | None) -> tuple[list[dict], dict]:
    """每檔**最早一筆未撤回的 `investor-brief/v2`**＝paper 錨點（不是 `select_brief` 的現行那筆）。純函式，不取價。

    回 `(rows, filter_report)`——每個 filter 都報 input／accepted／filtered／reasons（INV-3）：沒有 v2 的檔不是 paper 列；
    ledger 有壞行的檔照列但標 `ledger_unreadable` 缺席（壞的那行可能正是第一份 v2，錨點認不準）。"""
    from alpha.narrative.contracts import RECORD_VERSION_V1, RECORD_VERSION_V2, select_brief

    rows: list[dict] = []
    report = {"input": len(briefs), "accepted": 0, "filtered": {"no_v2": [], "ledger_unreadable": []}}
    for ticker, (records, errors) in sorted(briefs.items()):
        v2 = sorted((r for r in records if r.record_version == RECORD_VERSION_V2 and not r.retracted),
                    key=lambda r: (r.created_at, r.brief_id))
        if not v2 and not errors:
            report["filtered"]["no_v2"].append(ticker)
            continue
        report["accepted"] += 1
        if errors:
            report["filtered"]["ledger_unreadable"].append(ticker)
        first = v2[0] if v2 else None
        current = select_brief(list(records), as_of=None, today=today)
        v1 = [r for r in records if r.record_version == RECORD_VERSION_V1]
        cs = first.candidate_state if first is not None else None
        current_state = ("retracted" if current is None
                         else current.candidate_state.state if current.candidate_state is not None else "legacy_v1")
        company_id = first.company_id if first is not None else (records[0].company_id if records else None)
        row = {
            "lane": "paper", "ticker": ticker, "research_ticker": ticker, "company_id": company_id,
            "brief_id": first.brief_id if first else None,
            "anchor_at": first.created_at.isoformat() if first else None,
            "anchor_date": _local_day(first.created_at.isoformat()) if first else None,
            "anchor_state": cs.state if cs is not None else None,
            "current_brief_id": current.brief_id if current is not None else None,
            "current_state": current_state,
            "v2_records": len(v2),
            "earliest_v1": min(r.created_at for r in v1).isoformat() if v1 else None,
            "note": [],
        }
        # 首次點名它的 lead：lead registry 讀不到＝缺席（不是「沒人點名」）；讀得到但沒有＝no_lead_named。
        named = first_named_by(company_id, leads) if leads is not None else None
        row["first_named_by"] = named
        row["first_named_absence"] = ("upstream_unavailable" if leads is None
                                      else None if named else "no_lead_named")
        if errors:
            row["absence_kind"] = "ledger_unreadable"
            row["note"].append(f"敘事 ledger 有 {len(errors)} 行壞行——第一份 v2 認不準，不算報酬（INV-3）")
        rows.append(row)
    return rows, report


def _price_paper_row(row: dict, *, series: Mapping[date, float], quote_unit: str | None, today: date) -> None:
    """paper 列的報酬：錨點＝研究 ticker 的 provider 序列在錨點日或之前最近的收盤；終點＝today 或之前最近的收盤。
    兩端同一條序列、同一個報價單位，各自經 `_to_settlement`（GBp 不是 GBP）。"""
    from alpha.theme_cohort import close_on_or_before

    if row.get("absence_kind"):
        return
    anchor = row.get("anchor_date")
    if not series:
        row["absence_kind"] = "no_price_series"
        row["note"].append("provider 沒有這檔的收盤序列 → 不計算")
        return
    at = close_on_or_before(series, anchor) if anchor else None
    bar = close_on_or_before(series, today)
    if at is None or bar is None:
        row["absence_kind"] = "no_close_on_or_before_anchor"
        row["note"].append(f"錨點日 {anchor} 或之前沒有可用收盤 → 不計算（INV-6：不拿之後的價當錨）")
        return
    anchor_val, anchor_ccy = _to_settlement(at[1], quote_unit)
    current_val, current_ccy = _to_settlement(bar[1], quote_unit)
    if anchor_val is None or current_val is None or anchor_val <= 0 or anchor_ccy != current_ccy:
        row["absence_kind"] = "quote_unit_unresolved"
        row["note"].append(f"報價單位無法解析（registry={quote_unit!r}）→ fail closed，不計算")
        return
    row.update(anchor_bar_date=at[0], anchor_raw=at[1], anchor_price=anchor_val, anchor_ccy=anchor_ccy,
               current_date=bar[0], current_raw=bar[1], current_price=current_val,
               absolute_return=current_val / anchor_val - 1.0,
               anchor_source=(f"paper@{anchor}（{row.get('brief_id')}；{at[0]} 收盤 {at[1]} {quote_unit}"
                              f" → {anchor_val:.4f} {anchor_ccy}）"),
               pre_anchor_return=_pre_anchor_return(series, anchor))
    peak_raw, peak_date = _peak_since({d: v for d, v in series.items() if d <= bar[0]}, anchor)
    peak_val, peak_ccy = _to_settlement(peak_raw, quote_unit)
    if peak_val is not None and peak_ccy == anchor_ccy:
        row["peak_return"] = peak_val / anchor_val - 1.0
        row["peak_date"] = peak_date


def _provider_close_series(symbol: str, start: date) -> tuple[dict[date, float], str | None]:
    """新 lane 的取價：provider 已收盤序列＋它自報的報價單位（yfinance `history_metadata.currency`）。NaN 與非正數不收
    （歐洲標的會回 NaN 的未完成 K 棒）。抓不到回 `({}, None)`，由呼叫端標缺席。"""
    try:
        import yfinance as yf

        handle = yf.Ticker(symbol)
        hist = handle.history(start=start.isoformat(), auto_adjust=True)["Close"].dropna()
        unit = (getattr(handle, "history_metadata", None) or {}).get("currency")
    except Exception as exc:  # noqa: BLE001 — 單檔失敗只讓那一格缺席
        print(f"  ⚠ {symbol} 收盤序列抓取失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        return {}, None
    series = {ts.date(): float(close) for ts, close in hist.items() if close == close and float(close) > 0}
    return series, (str(unit) if unit else None)


def _apply_theme_cohort(rows: Sequence[dict], cohort: Any, series: Mapping[str, Mapping[date, float]]) -> None:
    """每列對主題等權組（排除本檔）的超額。共用 `alpha.theme_cohort.cohort_return`（追蹤表與計分表同一支）。**只印不比。**"""
    from alpha.theme_cohort import cohort_return

    if cohort is None:
        return
    for row in rows:
        if row.get("absolute_return") is None or not row.get("anchor_date") or not row.get("current_date"):
            continue
        result = cohort_return(cohort, start=row["anchor_date"], end=row["current_date"], series=series,
                               exclude_company=row.get("company_id"),
                               exclude_ticker=row.get("research_ticker") or row.get("ticker"))
        row["theme_cohort"] = result
        if result["return"] is not None:
            row["theme_cohort_return"] = result["return"]
            row["excess_theme_cohort"] = row["absolute_return"] - result["return"]


def chase_count(rows: Sequence[Mapping[str, Any]]) -> dict:
    """錨點前 30 日漲幅大於錨點後的列數——history 叫「入圖前已漲」、paper 叫「敘事前已漲」。純函式。"""
    paired = [r for r in rows if r.get("pre_anchor_return") is not None and r.get("absolute_return") is not None]
    chasing = [r for r in paired if r["pre_anchor_return"] > r["absolute_return"]]
    return {"paired": len(paired), "chasing": len(chasing),
            "tickers": [str(r.get("ticker")) for r in chasing]}


def lane_summary(rows: Sequence[Mapping[str, Any]], *, lane: str) -> dict:
    """一條 lane 的三量＋等權＋對主題等權組的超額。**每條 lane 各算、分母分開**；空 lane 回 n 0（呈現端印「還沒有列」）。"""
    measured = [r for r in rows if r.get("absolute_return") is not None]
    excess = [r["excess_theme_cohort"] for r in measured if r.get("excess_theme_cohort") is not None]
    anchors = [r["anchor_date"] for r in measured if r.get("anchor_date")]
    return {
        "lane": lane, "label": LANE_LABELS[lane], "n": len(rows), "measured": len(measured),
        "measurement_start": min(anchors).isoformat() if anchors else None,
        "aggregate": equal_weight_aggregate(list(rows)),
        "power_law": power_law_aggregate(list(rows), lane=lane),
        "theme_cohort_excess": {"n": len(excess), "mean": (sum(excess) / len(excess)) if excess else None,
                                "of": len(measured)},
        "chase": chase_count(rows),
        "absences": sorted({str(r["absence_kind"]) for r in rows if r.get("absence_kind")}),
    }


def _theme_cohort_info(cohorts: Sequence[Any], errors: Sequence[str]) -> tuple[Any, dict]:
    """現行主題等權組 → (組或 None, 呈現用的資訊)。0 組 `not_yet_recorded`；多於 1 組不猜哪一組適用（`ambiguous_cohort`）。"""
    info: dict[str, Any] = {"parse_errors": list(errors), "absence": None}
    if not cohorts:
        info["absence"] = {"kind": "not_yet_recorded", "reason": "主題等權組未定義（pq2 complete-theme-cohort 才寫得進來）"}
        return None, info
    if len(cohorts) > 1:
        info["absence"] = {"kind": "ambiguous_cohort",
                           "reason": f"現行主題等權組有 {len(cohorts)} 組——哪一組適用哪一列不由程式猜"}
        info["cohort_ids"] = [c.cohort_id for c in cohorts]
        return None, info
    cohort = cohorts[0]
    info.update(cohort_id=cohort.cohort_id, theme=cohort.theme, decided_on=cohort.decided_on.isoformat(),
                members=[m.ticker for m in cohort.members], members_total=len(cohort.members))
    return cohort, info


def collect(*, no_benchmark: bool = False, today: date | None = None,
            price_loader: Callable[[str, date], tuple[dict[date, float], str | None]] | None = None,
            history_loader: Callable[[], tuple[list[dict], list[dict]]] | None = None,
            benchmark_loader: Callable[[list[str], date, date], dict[str, dict[date, float]]] | None = None,
            trade_log_path: Path | None = None, brief_dir: Path | None = None,
            briefs: Mapping[str, tuple[Sequence[Any], Sequence[str]]] | None = None,
            leads: Mapping[str, Mapping[str, Any]] | None = None,
            cohorts: tuple[Sequence[Any], Sequence[str]] | None = None,
            is_beta: Callable[[str], bool] | None = None,
            resolve: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
            quote_unit_for: Callable[[str | None, str | None], str | None] | None = None,
            max_symbols: int = MAX_LANE_SYMBOLS) -> dict[str, Any]:
    """三條 lane 的資料收集（Phase 5 Step 5.2）。**render 與 APP 讀同一個函式**——APP 端另算一份會立刻開始偏離（L13）。

    回 `{"lanes": {live, paper, history}, "benchmarks", "theme_cohort", "price_budget", "today"}`：每條 lane 的 `rows`
    各自帶錨點、報酬、對 QQQ／SOXX 與主題等權組的超額；history 的逐列計算是原 `collect()` 一字不動（`_history_rows`）。
    所有外部輸入都可注入（測試不打網路、不讀舊店）；預設值就是正式資料源。**本函式不寫任何東西**——寫聚合檔的是 render。
    """
    today = today or _local_day(datetime.now(timezone.utc).isoformat()) or date.today()
    results, unavailable = (history_loader or _history_rows)()

    # ⚠ 新 lane 的任何一步讀壞（beta 政策檔、名冊、敘事 ledger、組 ledger），只讓**那一條 lane** 缺席——history 照走：
    # daily 步驟 05 在 5.2 之前不依賴這些檔，不得因為多了 lane 就整步失敗（L13：一格壞了其餘照發）。
    # 缺席帶理由、與「還沒有列」分開印（L12）。

    # live：trade_log
    try:
        events, log_problems = _read_trade_log(trade_log_path or TRADE_LOG)
        if is_beta is None:
            from risk.hard_caps import is_beta_symbol, load_beta_policy

            policy = load_beta_policy()
            is_beta = lambda symbol: is_beta_symbol(symbol, policy)  # noqa: E731
        if resolve is None:
            from portfolio.holdings import resolve_holding as resolve
        live = live_lane_plan(events, is_beta=is_beta, resolve=resolve)
        live["problems"] = log_problems
        live["absence"] = None
    except Exception as exc:  # noqa: BLE001
        reason = f"live lane 組不出來（{type(exc).__name__}: {str(exc)[:120]}）"
        live = {"rows": [], "beta_events": None, "unmatched_sells": [], "skipped": [], "problems": [reason],
                "absence": {"kind": "upstream_unavailable", "reason": reason}}

    # paper：敘事 ledger
    if leads is None:
        try:
            leads = (json.loads(LEADS_PATH.read_text(encoding="utf-8")).get("leads") or {})
        except (OSError, ValueError):
            leads = None                     # 讀不到＝first_named_by 缺席（upstream_unavailable），不是「沒人點名」
    try:
        paper_rows, paper_filter = paper_lane_plan(briefs if briefs is not None else _read_briefs(brief_dir),
                                                   today=today, leads=leads)
        paper_absence = None
    except Exception as exc:  # noqa: BLE001
        paper_rows, paper_filter = [], {"input": None, "accepted": 0, "filtered": {}}
        paper_absence = {"kind": "upstream_unavailable",
                         "reason": f"paper lane 組不出來（{type(exc).__name__}: {str(exc)[:120]}）"}

    # 主題等權組
    try:
        if cohorts is None:
            from alpha.providers.theme_cohorts import current_cohorts

            cohorts = current_cohorts()
        cohort, cohort_info = _theme_cohort_info(*cohorts)
    except Exception as exc:  # noqa: BLE001
        cohort = None
        cohort_info = {"parse_errors": [], "absence": {
            "kind": "upstream_unavailable", "reason": f"主題等權組讀不到（{type(exc).__name__}: {str(exc)[:120]}）"}}

    # 取價（新 lane＋組成員；有上限）。最早需要的起點＝各列錨點往前 PRE_ANCHOR_DAYS＋15 天。
    wanted: dict[str, date] = {}

    def want(symbol: str | None, anchor: date | None) -> None:
        if not symbol:
            return
        start = (anchor or today) - timedelta(days=PRE_ANCHOR_DAYS + 15)
        wanted[symbol] = min(start, wanted.get(symbol, start))

    from identity.execution import yfinance_symbol

    for row in live["rows"]:
        want(yfinance_symbol(row["execution_symbol"]), row.get("anchor_date"))
    for row in paper_rows:
        want(row["ticker"], row.get("anchor_date"))
    all_anchors = [r["anchor_date"] for r in (*results, *paper_rows, *live["rows"]) if r.get("anchor_date")]
    earliest = min(all_anchors) if all_anchors else today
    if cohort is not None:
        for member in cohort.members:
            want(member.ticker, earliest)
    always = [PRIMARY_BENCHMARK, REFERENCE_BENCHMARK]
    order = always + [s for s in wanted if s not in always]
    keep = order[:max(max_symbols, len(always))]
    truncated = order[len(keep):]
    loader = price_loader or _provider_close_series
    series: dict[str, dict[date, float]] = {}
    units: dict[str, str | None] = {}
    for symbol in keep:
        if symbol in always:
            continue                         # 基準由 `_benchmark_series` 抓（既有路徑），這裡只算進額度
        series[symbol], units[symbol] = loader(symbol, wanted[symbol])
    budget = {"cap": max_symbols, "requested": len(order), "fetched": len(keep), "truncated": truncated,
              "note": "history lane 的 22 檔沿用原路徑、不在這個上限裡"}

    unit_of = quote_unit_for or _market_quote_unit
    for row in live["rows"]:
        symbol = yfinance_symbol(row["execution_symbol"])
        if symbol in truncated:
            row["absence_kind"] = "truncated"
            row["note"].append(f"取價超過上限 {max_symbols} 檔被截掉——不是沒有價")
            continue
        _price_live_row(row, series=series.get(symbol) or {}, provider_unit=units.get(symbol), today=today)
    for row in paper_rows:
        if row["ticker"] in truncated:
            row.setdefault("absence_kind", "truncated")
            row["note"].append(f"取價超過上限 {max_symbols} 檔被截掉——不是沒有價")
            continue
        _price_paper_row(row, series=series.get(row["ticker"]) or {},
                         quote_unit=unit_of(row.get("company_id"), row["ticker"]), today=today)

    # 基準（三條 lane 一次抓，窗＝全部錨點最早一天到今天）
    benchmarks: dict[str, dict[date, float]] = {}
    lane_rows = (results, paper_rows, live["rows"])
    dated = [r for rows in lane_rows for r in rows if r.get("anchor_date") and r.get("current_date")]
    if not no_benchmark and dated:
        start = min(r["anchor_date"] for r in dated)
        end = max(r["current_date"] for r in dated)
        benchmarks = (benchmark_loader or _benchmark_series)([PRIMARY_BENCHMARK, REFERENCE_BENCHMARK], start, end)
    for rows in lane_rows:
        _apply_benchmarks(rows, benchmarks)
        _apply_theme_cohort(rows, cohort, series)
    if cohort is not None:
        cohort_info["missing_members"] = sorted(m.ticker for m in cohort.members if not series.get(m.ticker))

    return {
        "lanes": {"history": {"rows": results, "unavailable": unavailable, "absence": None},
                  "paper": {"rows": paper_rows, "filter": paper_filter, "absence": paper_absence},
                  "live": live},
        "benchmarks": benchmarks,
        "theme_cohort": cohort_info,
        "price_budget": budget,
        "today": today,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-benchmark", action="store_true",
                        help="不連外抓基準（診斷用：帶它時不寫聚合檔——當天那一行只由 daily 的完整跑法寫）")
    args = parser.parse_args()

    collected = collect(no_benchmark=args.no_benchmark)
    _render(collected, persist=not args.no_benchmark)
    return 0


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:+.1f}%"


def equal_weight_aggregate(results: list[dict]) -> dict:
    """推薦籃子的等權重聚合——AGENTS outcome 契約的量測基準。

    ⚠ 純函式，**markdown 與 APP artifact 讀同一份**：第二份實作會立刻開始偏離（L16）。
    各檔錨點日不同，這是跨持有期的粗聚合，**不是回測**。
    """
    abs_returns = [r["absolute_return"] for r in results if r.get("absolute_return") is not None]
    excess = [r.get(f"excess_{PRIMARY_BENCHMARK}") for r in results
              if r.get(f"excess_{PRIMARY_BENCHMARK}") is not None]
    return {
        "n": len(abs_returns),
        "absolute": (sum(abs_returns) / len(abs_returns)) if abs_returns else None,
        "excess": (sum(excess) / len(excess)) if excess else None,
        "benchmark": PRIMARY_BENCHMARK,
        "measured": len(abs_returns),
        "total": len(results),
    }


#: 「達 2 倍」的門檻。power-law 的目標是 2 到 10 倍（AGENTS「目標是倍率不是錯價」），
#: 2 倍是這條分佈的入場券，不是目標價。
DOUBLE_THRESHOLD = 1.0  # 報酬率 +100% ＝ 2 倍

#: 「滿 N 個月」用日曆日算，不用交易日——D15 問的是「12／24 個月內」，那是行事曆語意。
MATURITY_DAYS = {"12m": 365, "24m": 730}


def power_law_aggregate(results: list[dict], *, lane: str = "history") -> dict:
    """D15 的三個 power-law 統計量：**12／24 個月內達 2 倍的比例、最大單檔貢獻、籃子總報酬**。

    ⚠ 純函式，與 `equal_weight_aggregate` 並列；markdown、`outcome_aggregate.json`
    與 APP artifact 讀同一份（第二份實作會立刻開始偏離，L16）。

    ## 三個統計量各自的判準（寫出來才能被反駁）

    1. **達 2 倍的比例**：分母是**已滿 12／24 個月的檔數**，不是全部追蹤檔數。
       今天分母幾乎必然是 0——最早的錨點是 2026-07-21，整份追蹤表的歷史比一季還短。
       **回 `None` 而不是 0.0**：「沒有一檔滿 12 個月」與「滿了但沒有一檔翻倍」是兩個
       完全不同的結論，壓成同一個 0 就再也分不出來（L12）。同時另印
       `reached_2x_ever`／`reached_2x_now`（**不受成熟度限制**）——它回答「到今天為止
       有沒有任何一檔翻過倍」，是進行中的觀測，會隨時間只增不減，**因此系統性低估**。
    2. **最大單檔貢獻**：等權下單檔對籃子報酬的貢獻 ＝ `r_i / n`。power-law 的整個賭注
       是「一檔補回多檔」，所以要看得到那一檔是誰、它扛了多少。⚠ **這裡刻意不做除法。**
       首版印的是「佔籃子總報酬的比例」，2026-09-18 真實資料一跑就爆成 **15636%**
       ——籃子總報酬 +0.02%，分母接近 0。門檻式的修法（小於 X% 就回 None）會引入一個
       憑空的參數（INV-5：未量測的機制不得享有默認信任），所以改用恆等式：
       `basket_total ＝ top_contribution ＋ rest_contribution`。減法不可能爆，而且
       **更直接說出 power-law 的那件事**——那一檔扛了多少、其餘幾檔合計拖了多少。
    3. **籃子總報酬**：等權組合的報酬率，**就是 `equal_weight_aggregate()['absolute']`**
       ——D15 列的三個統計量裡這一個本來就在，這裡不另算一份，只把它放進同一個信封，
       讓三個數字一起被讀。

    ## 兩個刻意分開的數字

    `reached_2x_ever`（期間高點曾達）與 `reached_2x_now`（現價仍達）**兩個都印**：
    D3 定案「目標價到了只提醒、出場只認反證」，所以抱著回吐是預期內的行為，
    只印期末會系統性低估「有沒有抓到倍數」，只印高點則會高估「現在手上有什麼」。
    """
    measured = [r for r in results if r.get("absolute_return") is not None]
    n = len(measured)
    with_peak = [r for r in measured if r.get("peak_return") is not None]

    def _held_days(row: dict) -> int | None:
        a, c = row.get("anchor_date"), row.get("current_date")
        return (c - a).days if a and c else None

    held = [d for d in (_held_days(r) for r in measured) if d is not None]
    anchors = [r["anchor_date"] for r in measured if r.get("anchor_date")]

    maturity: dict[str, dict] = {}
    for label, days in MATURITY_DAYS.items():
        mature = [r for r in measured
                  if (_held_days(r) or 0) >= days and r.get("peak_return") is not None]
        hits = [r for r in mature if r["peak_return"] >= DOUBLE_THRESHOLD]
        maturity[label] = {
            "matured": len(mature),
            "reached_2x": len(hits),
            # 分母 0 → None，不是 0.0（見 docstring 第 1 點）
            "share": (len(hits) / len(mature)) if mature else None,
            "tickers": sorted(r["ticker"] for r in hits if r.get("ticker")),
        }

    basket_total = (sum(r["absolute_return"] for r in measured) / n) if n else None
    top = max(measured, key=lambda r: r["absolute_return"]) if n else None
    top_contribution = (top["absolute_return"] / n) if top else None
    # 恆等式而非比例：rest ＝ 籃子總報酬 − 最大單檔貢獻（見 docstring 第 2 點）。
    rest_contribution = (
        basket_total - top_contribution
        if basket_total is not None and top_contribution is not None else None
    )

    return {
        "n": n,
        "peak_measured": len(with_peak),
        "measurement_start": min(anchors).isoformat() if anchors else None,
        "max_days_held": max(held) if held else None,
        "maturity": maturity,
        "reached_2x_ever": sum(1 for r in with_peak if r["peak_return"] >= DOUBLE_THRESHOLD),
        "reached_2x_now": sum(1 for r in measured
                              if r["absolute_return"] >= DOUBLE_THRESHOLD),
        "basket_total_return": basket_total,
        "top_contributor": None if top is None else {
            "ticker": top.get("ticker"),
            "absolute_return": top["absolute_return"],
            "peak_return": top.get("peak_return"),
            "contribution": top_contribution,
            "rest_contribution": rest_contribution,
            "rest_n": (n - 1) if n else 0,
        },
        "threshold": DOUBLE_THRESHOLD,
        # 三個已知偏差，跟著數字走（AGENTS：計分表必印量測起始日與樣本數，並印三個已知偏差）。
        "known_biases": [
            "未滿 12／24 個月的檔數不進 `maturity` 的分母——分母小的時候那個比例是雜訊，"
            "不是結論；`reached_2x_ever` 則是進行中的下界，只增不減，**系統性低估**。",
            "各檔錨點日不同，這是跨持有期的粗聚合、不是回測；錨點跨度短時有效 n 遠小於檔數。",
            # 第三條跟著 lane 走（Phase 5 Step 5.2）：history 的「錨點是入圖日」對 paper／live 是錯的（L12）。
            # history 的字一個不改——`outcome_aggregate.jsonl` 的歷史行與它逐字相同。
            LANE_ANCHOR_BIAS[lane],
        ],
    }


def render_power_law(power: dict) -> list[str]:
    """D15 三個統計量的人類可讀版。**量測起始日與樣本數永遠先印**，偏差跟著數字走。

    ⚠ 不得只印「達 2 倍 0%」。今天的真相是「**沒有一檔滿 12 個月**」，那與「滿了但
    沒有一檔翻倍」是相反的結論；分母為 0 時印的是「還沒有分母」，不是一個假的 0%。
    """
    if not power.get("n"):
        return []
    out: list[str] = []
    start = power.get("measurement_start") or "?"
    days = power.get("max_days_held")
    out.append(
        chr(10) + f"**power-law 三量（D15）｜量測起始 {start}｜樣本 {power['n']} 檔｜"
        f"最長已持有 {days if days is not None else '?'} 天**"
    )
    total = power.get("basket_total_return")
    # ⚠ 這幾個數字用兩位小數，不用共用的 `_pct`：籃子總報酬接近 0 時（今天 +0.02%）
    # 一位小數會印成 `+0.0%`，而恆等式「總報酬 ＝ 最大單檔 ＋ 其餘」會看起來不成立。
    def pct2(v):
        return f"{v:+.2%}" if isinstance(v, (int, float)) else "—"
    out.append(f"- 籃子總報酬（等權）：{pct2(total)}　←與上一行的等權絕對是同一個數字")
    top = power.get("top_contributor")
    if top:
        peak = top.get("peak_return")
        peak_text = f"（期間高點 {_pct(peak)}）" if isinstance(peak, (int, float)) else ""
        out.append(
            f"- 最大單檔貢獻：{top.get('ticker') or '?'} {_pct(top.get('absolute_return'))}"
            f"{peak_text} → 等權貢獻 {pct2(top.get('contribution'))}"
        )
        out.append(
            f"  其餘 {top.get('rest_n')} 檔合計 {pct2(top.get('rest_contribution'))}"
            "　←恆等式：籃子總報酬 ＝ 最大單檔 ＋ 其餘，沒有除法所以不會爆"
        )
    for label in ("12m", "24m"):
        m = power["maturity"][label]
        if m["matured"]:
            names = ("：" + "／".join(m["tickers"])) if m["tickers"] else ""
            out.append(f"- {label} 內達 2 倍：{m['reached_2x']}/{m['matured']} "
                       f"（{m['share']:.0%}）{names}")
        else:
            out.append(f"- {label} 內達 2 倍：**尚無一檔滿 {label}**——"
                       "這不是 0%，是分母還沒出現")
    measured = power.get("peak_measured")
    out.append(
        f"- 到今天為止曾達 2 倍：{power['reached_2x_ever']}/{measured} 檔"
        f"（現價仍在 2 倍以上：{power['reached_2x_now']}）"
        "　←進行中的下界，只增不減，**系統性低估**"
    )
    for bias in power.get("known_biases", []):
        out.append(f"  ⚠ {bias}")
    return out


def _jsonable(value):
    """把聚合結果裡的 `date` 轉成 ISO 字串。**只轉型別，不改結構**。

    ⚠ 不用 `json.dumps(default=str)`：那會把任何不可序列化的東西都變成它的 `repr`，
    於是一個本來該爆的錯誤（例如不小心塞進一個模型物件）會靜默變成一串垃圾字元。
    """
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def collect_bet_convergence() -> dict:
    """V4（2026-09-19）：從已 materialize 的 analyst view 讀各檔賭注收斂，聚合成一份。

    ⚠ **讀 artifact，不重跑模型。** 這支腳本本來就不連 Neo4j；而賭注收斂是判讀的一部分，
    APP 呈現契約逐字禁止在讀取路徑重算（「LLM changes cognition; APP reads cognition」）。
    artifact 沒 materialize 過就回空——**「還沒 materialize」與「沒有賭注」不得同形**（L13-2）。
    """
    from alpha.gap_closure import bet_convergence

    directory = ROOT / "library" / "private" / "app" / "analyst_view"
    if not directory.is_dir():
        return {"n_bets": 0, "rows": [], "artifact_state": "no_artifact_dir"}
    entries: list[tuple[str, dict]] = []
    stale: list[str] = []
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith(".meta.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ticker = str(payload.get("ticker") or path.stem)
        closure = ((payload.get("overview") or {}).get("gap_closure") or {})
        value = closure.get("value")
        if not isinstance(value, dict):
            continue
        if "bet_since" not in value:
            # 這份 artifact 是 V4 之前產的：它的 variant 起算日還是判斷日（錯的起點）。
            # 靜默把它當成「沒有賭注」會讓一個**過期的 artifact** 長得像一個**誠實的空集合**。
            stale.append(ticker)
            continue
        entries.append((ticker, _dates_in_closure(value)))
    out = bet_convergence(entries, today=date.today())
    out["artifact_state"] = "stale_schema" if stale and not entries else "ok"
    out["stale_artifacts"] = stale
    return out


def _dates_in_closure(value: dict) -> dict:
    """artifact 裡的日期是 ISO 字串；純函式吃的是 `date`。只轉日期，其餘原樣。"""
    converted = dict(value)
    converted["bet_since"] = _as_date(value.get("bet_since"))
    for key in ("base", "variant"):
        leg = value.get(key)
        if isinstance(leg, dict):
            leg = dict(leg)
            for field in ("start_date", "now_date"):
                if leg.get(field) is not None:
                    leg[field] = _as_date(leg.get(field))
            converted[key] = leg
    return converted


def render_bet_convergence(conv: dict) -> list[str]:
    """V4 的人類可讀版。**沒有賭注時印「還沒有人下注」，不印 0%。**"""
    if not conv or not conv.get("n_bets"):
        if conv.get("stale_artifacts"):
            return [chr(10) + "**賭注收斂（V4）｜artifact 是 V4 之前產的**——"
                    f"{len(conv['stale_artifacts'])} 檔需要重跑 `python -m webapp materialize` 才量得到"]
        return [chr(10) + "**賭注收斂（V4）｜還沒有任何一檔寫下賭注**——這不是 0%，是還沒有分子也沒有分母"]
    out = [chr(10) + f"**賭注收斂（V4）｜掃描 {conv.get('scanned', '?')} 檔｜有賭注 {conv['n_bets']} 檔｜"
           f"量得到 {conv['measurable']} 檔**　←共識朝我們移動了嗎（不依賴賣出的驗證）"]
    lo, hi = conv.get("shortest_window_days"), conv.get("longest_window_days")
    if lo is not None:
        out.append(f"- 已觀測窗：{lo}–{hi} 天　←窗短時「沒動」幾乎是必然，不是市場否定了我們")
    waiting = conv.get("longest_days_waiting")
    if waiting is not None:
        out.append(f"- 最久還沒等到第一次共識抓取：{waiting} 天　←這個數字不與上一行合併")
    out.append(f"- 朝我們移動 {conv['toward_us']}｜反向 {conv['away_from_us']}｜"
               f"共識沒動 {conv['unchanged']}｜**賭注寫下後還沒有共識抓取 {conv['not_yet_observable']}**"
               f"　←最後一格不是「沒動」（另有 {conv.get('no_bet', 0)} 檔沒寫賭注）")
    for row in conv.get("rows", []):
        state = row.get("state")
        since = row.get("bet_since")
        since_text = since.isoformat() if hasattr(since, "isoformat") else (since or "?")
        if state == "not_yet_observable":
            waited = row.get("days_waiting")
            waited_text = f"（已等 {waited} 天）" if isinstance(waited, int) else ""
            out.append(f"  - {row['ticker']}：賭注 {since_text} 寫下，之後還沒有共識抓取{waited_text}")
            continue
        frac = row.get("closed_fraction")
        frac_text = f"{frac:+.1%}" if isinstance(frac, (int, float)) else "—"
        out.append(
            f"  - {row['ticker']}：自 {since_text} 起 {row.get('n_points')} 次抓取，"
            f"共識移動 {row.get('moved'):+.4g}（起點差距 {row.get('gap_at_start'):+.4g}）"
            f" → {frac_text}　[{state}]"
            if isinstance(row.get("moved"), (int, float)) and isinstance(row.get("gap_at_start"), (int, float))
            else f"  - {row['ticker']}：{state}")
    for bias in conv.get("known_biases", []):
        out.append(f"  ⚠ {bias}")
    return out


def live_lane_rows(results: list[dict], fills: dict[str, list[dict]]) -> tuple[list[dict], list[str]]:
    """真實成交 vs 只有 paper。回傳 (逐筆 fill 列, 只有 paper 的 ticker)。

    「live 報酬」以**實際成交價**為錨點，「shadow 報酬」以**入圖日**為錨點——兩者語意不同，
    後者不含任何進場時點判斷，不構成選股能力的證據。幣別不一致一律 fail closed，不猜匯率。
    """
    by_ticker = {str(r["ticker"]): r for r in results if r.get("ticker")}
    live_tickers = sorted(t for t in fills if t in by_ticker)
    paper_only = [t for t in by_ticker if t not in fills]
    rows: list[dict] = []
    for ticker in live_tickers:
        row = by_ticker[ticker]
        current_val, current_ccy = _to_settlement(
            row.get("current_raw"), _market_quote_unit(row.get("company_id"), ticker)
        )
        for fill in sorted(fills[ticker], key=lambda f: f["executed_at"] or date.min):
            live_ret = None
            if current_val is not None and fill["price"] > 0 and fill["currency"] == current_ccy:
                live_ret = current_val / fill["price"] - 1.0
            rows.append({
                "ticker": ticker, "company_id": row.get("company_id"),
                "executed_at": fill["executed_at"], "price": fill["price"],
                "shares": fill["shares"], "currency": fill["currency"],
                "current": current_val, "current_currency": current_ccy,
                "live_return": live_ret, "shadow_return": row.get("absolute_return"),
            })
    return rows, paper_only


def anchor_health(results: list[dict]) -> dict | None:
    """錨點體檢：樣本效度先於數字。

    ⚠ **刻意先講樣本效度再講數字**——反過來寫的話讀者會先看到「超額 +11%」再把 caveat
    當客套話，於是一份有效 n=1 的觀測讀起來像 10 個獨立驗證。
    """
    paired = [r for r in results
              if r.get("pre_anchor_return") is not None and r.get("absolute_return") is not None]
    if not paired:
        return None
    anchors = sorted(r["anchor_date"] for r in paired)
    chasing = [r for r in paired if r["pre_anchor_return"] > r["absolute_return"]]
    return {
        "paired": len(paired),
        "judgment_anchors": _judgment_anchor_count(),
        "first": anchors[0], "last": anchors[-1],
        "span_days": (anchors[-1] - anchors[0]).days,
        "weeks": len({(d.isocalendar()[0], d.isocalendar()[1]) for d in anchors}),
        "span_warn_days": ANCHOR_SPAN_WARN_DAYS,
        "pre_median": _median([r["pre_anchor_return"] for r in paired]),
        "post_median": _median([r["absolute_return"] for r in paired]),
        "chasing": len(chasing),
        "chasing_tickers": [str(r["ticker"]) for r in chasing],
        "pre_anchor_days": PRE_ANCHOR_DAYS,
    }


def _render(collected: Mapping[str, Any], *, persist: bool = True) -> None:
    """history lane 的表與三量（原樣）→ 三條 lane 分段。`persist=False`（`--no-benchmark` 的診斷跑法）不寫聚合檔：
    當天那一行只由 daily 的完整跑法寫——診斷跑法會把超額寫成 null、蓋掉當天的值（Phase 5 plan §0.6 #1）。"""
    lanes = collected["lanes"]
    results = lanes["history"]["rows"]
    unavailable = lanes["history"]["unavailable"]
    has_bench = bool(collected.get("benchmarks"))
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

    # 等權重聚合（2026-09-02 ROADMAP 交付）：AGENTS outcome 契約的量測基準——
    # 研究 cohort 以每檔等權計。錨點日各異，這是跨持有期的粗聚合，明標不是回測。
    # ⚠ 2026-09-23（Phase 0 Step 0b.3）：原本另 append 當日**排序**快照當前／後段對照的史料
    # （`_append_ranking_snapshot`）；跨檔排序退役，那一段整個拿掉，`ranking_order_snapshots.jsonl` 留檔不再寫。
    aggregate = equal_weight_aggregate(results)
    # V4 的分母是「寫了賭注的檔」，與追蹤表的分母無關——所以它在 `if` 外面算也在外面印。
    # 追蹤表空的時候賭注收斂仍然有話可說（反之亦然），綁在一起會讓其中一邊靜默消失。
    convergence = collect_bet_convergence()
    if aggregate["n"]:
        line = f"\n**等權重聚合（{aggregate['n']} 檔）：絕對 {_pct(aggregate['absolute'])}"
        if aggregate["excess"] is not None:
            line += f"｜超額({PRIMARY_BENCHMARK}) {_pct(aggregate['excess'])}"
        line += "**——各檔錨點日不同，粗聚合非回測"
        print(line)
        power = power_law_aggregate(results)
        for text in render_power_law(power):
            print(text)
        if persist:
            _persist_aggregate(n=aggregate["n"], ew_abs=aggregate["absolute"],
                               ew_excess=aggregate["excess"], power=power, convergence=convergence,
                               lanes=lanes_payload(collected), theme_cohort=collected.get("theme_cohort"))
    for text in render_bet_convergence(convergence):
        print(text)

    _render_live_lane(results, _live_fills())
    _render_chase_check(results)
    for text in render_lanes(collected):
        print(text)


def lanes_payload(collected: Mapping[str, Any]) -> dict:
    """三條 lane 的摘要（JSON 可序列化）——聚合檔的 `lanes`、APP artifact、心跳讀同一份（L16：呈現不重算）。
    lane 組不出來時 `absence` 帶理由：消費端印它，不印「還沒有列」（L12）。"""
    out = {}
    for lane in LANE_KEYS:
        summary = lane_summary(collected["lanes"][lane]["rows"], lane=lane)
        summary["absence"] = collected["lanes"][lane].get("absence")
        out[lane] = _jsonable(summary)
    return out


def render_lanes(collected: Mapping[str, Any]) -> list[str]:
    """三條 lane 分段印（Phase 5 Step 5.2）。**只印不比、不排序、不設門檻**；空 lane 印「還沒有列」，不印 0%。"""
    out = ["", "## 三條 lane——分母分開，不得合併讀（live 量買得準不準、paper 量判斷準不準、history 只是歷史）"]
    cohort = collected.get("theme_cohort") or {}
    if cohort.get("absence"):
        out.append(f"- 主題等權組：{cohort['absence']['reason']}（{cohort['absence']['kind']}）——超額那一格全部缺席，不是 0")
    else:
        missing = cohort.get("missing_members") or []
        out.append(f"- 主題等權組：`{cohort.get('cohort_id')}`（{cohort.get('theme')}，{cohort.get('decided_on')} 定，"
                   f"{cohort.get('members_total')} 檔；每列排除本檔）｜取不到價的成員 {len(missing)}"
                   + (f"：{'、'.join(missing)}" if missing else ""))
    if cohort.get("parse_errors"):
        out.append(f"- ⚠ 主題等權組 ledger 有 {len(cohort['parse_errors'])} 行壞行（不靜默丟棄）："
                   + "；".join(cohort["parse_errors"][:3]))
    budget = collected.get("price_budget") or {}
    out.append(f"- 取價：要 {budget.get('requested')} 檔、抓 {budget.get('fetched')} 檔（上限 {budget.get('cap')}）"
               + (f"｜**截掉 {len(budget['truncated'])} 檔：{'、'.join(budget['truncated'])}**" if budget.get("truncated") else "")
               + "｜history 的 22 檔沿用原路徑、不在這個上限裡")
    for lane in LANE_KEYS:
        rows = collected["lanes"][lane]["rows"]
        summary = lane_summary(rows, lane=lane)
        out.append("")
        out.append(f"### {lane}：{LANE_LABELS[lane]}")
        absence = collected["lanes"][lane].get("absence")
        if absence:
            out.append(f"- ⚠ {absence['reason']}（{absence['kind']}）——不是 0，也不是「還沒有列」")
            continue
        if lane == "live":
            live = collected["lanes"]["live"]
            out.append(f"- beta 事件 {live.get('beta_events', 0)} 不進 lane"
                       + (f"｜⚠ 配對不到的賣出：{'；'.join(live['unmatched_sells'])}" if live.get("unmatched_sells") else "")
                       + (f"｜⚠ {'；'.join(live['problems'])}" if live.get("problems") else ""))
        if lane == "paper":
            report = collected["lanes"]["paper"].get("filter") or {}
            filtered = report.get("filtered") or {}
            out.append(f"- 敘事 ledger {report.get('input', 0)} 本：進 lane {report.get('accepted', 0)}｜沒有 v2 "
                       f"{len(filtered.get('no_v2') or [])}｜ledger 有壞行 {len(filtered.get('ledger_unreadable') or [])}")
        if not rows:
            out.append(f"- {LANE_EMPTY[lane]}")
            continue
        if lane != "history":
            out.extend(_lane_table(rows, lane=lane))
        excess = summary["theme_cohort_excess"]
        out.append(f"- 等權絕對 {_pct(summary['aggregate']['absolute'])}｜對 {PRIMARY_BENCHMARK} 超額 "
                   f"{_pct(summary['aggregate']['excess'])}｜對主題等權組超額 "
                   + (f"{_pct(excess['mean'])}（{excess['n']}/{excess['of']} 列有值）" if excess["n"]
                      else f"還沒有值（{excess['of']} 列量得到報酬）"))
        chase = summary["chase"]
        label = {"history": "入圖前已漲", "paper": "敘事前已漲", "live": "成交前已漲"}[lane]
        out.append(f"- {label}：{chase['chasing']}/{chase['paired']}"
                   + (f"（{'、'.join(chase['tickers'])}）" if chase["tickers"] else ""))
        if lane != "history":
            out.extend(render_power_law(summary["power_law"]))
        if summary["absences"]:
            out.append(f"- 缺席：{'、'.join(summary['absences'])}（逐列理由在上表的註記）")
    return out


def _lane_table(rows: Sequence[Mapping[str, Any]], *, lane: str) -> list[str]:
    out = ["", f"| 標的 | 錨點日 | {'收據' if lane == 'live' else '當時→現行'} | 錨點前30日 | 絕對報酬 | "
               f"對 {PRIMARY_BENCHMARK} | 對主題等權組 | {'成交' if lane == 'live' else '首次點名'} |",
           "|---|---|---|---|---|---|---|---|"]
    for row in sorted(rows, key=lambda r: (str(r.get("anchor_date") or ""), str(r.get("ticker")))):
        if lane == "live":
            third = (row.get("receipt") or {}).get("status") or "—"
            last = f"{row.get('execution_symbol')} {row.get('anchor_raw')} {row.get('trade_currency')}" + (
                "（已賣出）" if row.get("closed") else "")
        else:
            third = f"{row.get('anchor_state') or '—'}→{row.get('current_state') or '—'}"
            named = row.get("first_named_by") or {}
            last = (f"{named.get('source')} {str(named.get('first_seen') or '')[:10]}" if named
                    else row.get("first_named_absence") or "—")
        cohort = row.get("theme_cohort") or {}
        cohort_cell = (_pct(row.get("excess_theme_cohort")) + f"（{cohort.get('members_used')}/{cohort.get('members_total')}）"
                       if row.get("excess_theme_cohort") is not None else "—")
        out.append(f"| {row.get('ticker')} | {row.get('anchor_date') or '—'} | {third} | "
                   f"{_pct(row.get('pre_anchor_return'))} | {_pct(row.get('absolute_return'))} | "
                   f"{_pct(row.get(f'excess_{PRIMARY_BENCHMARK}'))} | {cohort_cell} | {last} |")
    notes = [(r.get("ticker"), n) for r in rows for n in r.get("note") or []]
    for ticker, note in notes:
        out.append(f"- **{ticker}**：{note}")
    return out


def _persist_aggregate(*, n: int, ew_abs: float, ew_excess: float | None,
                       power: dict | None = None, convergence: dict | None = None,
                       lanes: dict | None = None, theme_cohort: Mapping[str, Any] | None = None) -> None:
    """把最新聚合值落成狀態檔 **＋ append 一筆時序**（2026-09-11 補時序）。

    ⚠ **為什麼要兩個檔**：`.json` 是 brief 首屏的最新值（既有消費端，形狀不動）；
    `.jsonl` 是時序。先前只有前者，而它是 `write_text` **覆寫**——於是「系統的判斷準不準」
    永遠只有今天一個點，**樣本外驗證結構上不可能做**（ROADMAP §F 要的是「保存當時的
    PIT view，事後對 actual 算誤差」，那需要歷史）。

    同一支腳本裡 `_append_ranking_snapshot` 早就是 append——**一個機制做了、它的對稱面
    沒做**，而且不會有任何東西壞掉，所以它安靜存在了 9 天（L17-3）。

    同一天重跑只保留最後一筆（以 `date` 去重），否則一天跑三次會讓那天的權重變三倍。
    """
    import json as _json

    payload = {
        "date": date.today().isoformat(),
        "n": n,
        "equal_weight_absolute": ew_abs,
        "equal_weight_excess": ew_excess,
        "benchmark": PRIMARY_BENCHMARK,
    }
    # D15：三個 power-law 統計量與等權值放同一個信封。**既有四個欄位一字不動**——
    # brief 首屏與 APP 都在讀它們，改名或改語意會讓既有消費端靜默偏掉。
    if power is not None:
        payload["power_law"] = power
    # V4：賭注收斂與 power-law 放同一個信封，**既有欄位一字不動**。它是第二個量測維度——
    # power-law 問「排序有沒有選到會漲的」（依賴股價），V4 問「共識有沒有朝我們移動」（不依賴賣出）。
    if convergence is not None:
        payload["bet_convergence"] = _jsonable(convergence)
    # Phase 5 Step 5.2：三條 lane 各自的三量與超額。**既有四欄＝history lane，一字不動**（序列不斷）；
    # 新資料只住 `lanes`，主題等權組的 id 跟著走（組換了看得出斷點，plan §14 #6）。
    if lanes is not None:
        payload["lanes"] = lanes
    if theme_cohort is not None:
        payload["theme_cohort"] = {k: theme_cohort.get(k) for k in ("cohort_id", "decided_on", "absence")}
    out = Path("library/private/decision_lab/outcome_aggregate.json")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    series = out.with_suffix(".jsonl")
    try:
        rows = []
        if series.is_file():
            for line in series.read_text(encoding="utf-8").splitlines():
                text = line.strip()
                if not text:
                    continue
                try:
                    row = _json.loads(text)
                except ValueError:
                    continue          # 壞掉的行不靜默丟掉整串，只跳過這一行
                if str(row.get("date")) != payload["date"]:
                    rows.append(row)
        rows.append(payload)
        series.write_text(
            "".join(_json.dumps(r, ensure_ascii=False) + chr(10) for r in rows),
            encoding="utf-8")
    except OSError:
        pass


def _live_fills() -> dict[str, list[dict]]:
    """ticker → 該檔的真實 live fill（使用者手動下單後回報的成交）。

    這是 `2026-08-18-alpha-live-user-sized` §4 驗收條件 5 的資料源：報表必須能分辨
    「有 live fill 的 cohort」與「只有 paper 的 cohort」，並各自算報酬。

    ⚠ **為什麼不能只用 Shadow 錨點算完就算數（§7）：** Shadow 錨點的語意是「這家公司的
    claim 那天進圖」，**不含任何進場時點判斷**——`decision_cohorts.dedupe_key` 全部是
    `claim:<hash>` 就是證據。fill 錨點才是「使用者決定買的那天、那個價」。兩者可能很接近
    （COHR 首筆：shadow@07-21 317.22 vs fill@08-18 316.23，差 0.3%），但那是巧合，
    語意完全不同，下一筆可能差很多。
    """

    fills: dict[str, list[dict]] = {}
    query = """
        SELECT f.execution_ref, f.shares, f.price, f.currency, f.executed_at,
               lc.selected_weight, lc.choice_type, dc.research_ticker
        FROM live_execution_reports f
        JOIN live_choices lc ON lc.choice_id = f.choice_id
        JOIN system_decisions sd ON sd.decision_id = f.decision_id
        JOIN decision_cohorts dc ON dc.cohort_id = sd.cohort_id
    """
    try:
        with _connect_ro(DECISION_DB) as conn:
            rows = conn.execute(query).fetchall()
    except sqlite3.Error:
        # 讀不到就當沒有 live fill——fail closed，宣稱「已有真實部位」的舉證責任在有資料那方。
        return fills
    for row in rows:
        ticker = str(row["research_ticker"] or "").strip()
        if not ticker:
            continue
        fills.setdefault(ticker, []).append(
            {
                "execution_ref": row["execution_ref"],
                "shares": float(row["shares"] or 0.0),
                "price": float(row["price"] or 0.0),
                "currency": str(row["currency"] or ""),
                "executed_at": _as_date(row["executed_at"]),
                "selected_weight": row["selected_weight"],
                "choice_type": row["choice_type"],
            }
        )
    return fills


def _render_live_lane(results: list[dict], fills: dict[str, list[dict]]) -> None:
    """把「真的下了單的」與「只有 paper 的」分開算——驗收條件 5。

    這一段刻意獨立於主表，而不是在主表加一欄。主表回答的是「這批標的自入圖以來走勢
    如何」，本段回答的是**「Engine D 有意見之後，使用者依它下的注表現如何」**——後者
    才是「系統準不準」的證據，前者不是（§7）。混在同一張表會讓兩個問題共用一個數字。
    """

    print("\n## 舊店的 live fill vs 只有入圖錨點的 cohort（history lane；凍結只印）\n")

    rows, paper_only = live_lane_rows(results, fills)
    live_tickers = sorted({row["ticker"] for row in rows})

    if not live_tickers:
        print(
            "- **舊店 live fill：0 筆。** 目前所有 cohort 都只有入圖錨點，"
            "「系統的建議準不準」還沒有任何真實資本的證據。"
        )
        print(f"- 只有入圖錨點的 cohort：{len(paper_only)} 個。")
        return

    header = (
        f"| {'標的':9} | {'成交日':10} | {'成交價':>10} | {'股數':>7} "
        f"| {'現價':>10} | {'live 報酬':>10} | {'同檔 shadow 報酬':>16} |"
    )
    print(header)
    print(
        f"|{'-' * 11}|{'-' * 12}|{'-' * 12}|{'-' * 9}"
        f"|{'-' * 12}|{'-' * 12}|{'-' * 18}|"
    )

    measured = 0
    for row in rows:
        if row["live_return"] is not None:
            measured += 1
        current_val = row["current"]
        print(
            f"| {row['ticker']:9} | {str(row['executed_at'] or '—'):10} "
            f"| {row['price']:>10.2f} | {row['shares']:>7.4g} "
            f"| {(f'{current_val:.2f}' if current_val else '—'):>10} "
            f"| {_pct(row['live_return']):>10} | {_pct(row['shadow_return']):>16} |"
        )

    print(
        f"\n- **有 live fill：{len(live_tickers)} 檔（已算出報酬 {measured} 筆）"
        f"｜只有入圖錨點：{len(paper_only)} 個 cohort。**"
    )
    print(
        "- 「live 報酬」以**實際成交價**為錨點，「shadow 報酬」以**入圖日**為錨點。"
        "兩者語意不同：後者不含任何進場時點判斷，不構成選股能力的證據（§7）。"
    )
    if len(live_tickers) < 3:
        print(
            f"- 🟠 **live 樣本僅 {len(live_tickers)} 檔，不足以回答「系統準不準」。**"
            "這個數字只有靠累積真實下單才會變大，時間經過不會讓它自己滿足。"
        )


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
    health = anchor_health(results)
    if health is None:
        return

    paired = [r for r in results
              if r.get("pre_anchor_return") is not None and r.get("absolute_return") is not None]
    anchors = [health["first"], health["last"]]
    span = health["span_days"]
    weeks = health["weeks"]
    judgment = health["judgment_anchors"]

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

    chasing = health["chasing_tickers"]
    pre_med = health["pre_median"]
    post_med = health["post_median"]
    print(
        f"\n- 錨點前 {PRE_ANCHOR_DAYS} 日中位：{_pct(pre_med)}｜錨點後中位：{_pct(post_med)}\n"
        f"- 錨點前漲幅大於錨點後：{len(chasing)} / {len(paired)}"
        + (f"（{'、'.join(chasing)}）" if chasing else "")
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
