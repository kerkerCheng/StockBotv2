"""Engine C 機械歷史表：價格（raw／adjusted＋分割）與 EDGAR 基本面（每份申報各一列）——Phase 3 Step 3.2。

## 它解什麼

財務三題的「已定價嗎」要**自家三年歷史**的 EV/S 或 P/S 百分位，稀釋燈要**一年以上**的同口徑股數。
2026-09-29 基準：`financial_snapshots` 最早 2026-07-08、股數序列約 80 天——兩題三年內恆為缺席（L14-4 恆亮）。
本模組一次回填、之後由 daily 增量（`--incremental`），讓歷史自己長。

## 三張表（可重建的 ETL 觀測，不是 append-only judgment ledger——L10：今天重取一次拿得回來）

- `price_history`：每個交易日一列。`close_raw` 是**當時實際成交的價**（yfinance 的 `Close` 已做分割調整，
  這裡用 `corporate_actions` 乘回去），`close_adjusted` 是分割＋股利調整（報酬用）。報價單位照交易所存
  （例 `GBp`），另存結算幣別——**不得為了通過驗證改寫成 ISO code**（AGENTS「圖的寫入紀律」）。
- `corporate_actions`：分割事件（`kind='split'`，ratio＝新股數／舊股數）。
- `fundamental_history`：EDGAR companyfacts 的營收、營業利益、現金、債務、封面股數。**每份申報各一列**
  （唯一鍵含 accession），所以同一期間被後來的申報重編時兩列並存；讀取端 as-of T 取 `filed ≤ T` 的最新一列
  （`engine_c/history.py`）。**TTM 由讀取端組，不存。**

## 三條時間語意（INV-6、L11-5）

1. 財報數字的可用日是 **`filed`**（EDGAR 申報日），不是會計期末、更不是抓取日。`fetched_at` 只是抓取紀錄。
2. 衍生的 Q4（＝年度 − 前三季累計）標 `derived`，`filed` 取兩份申報較晚的那個。
3. 台股月營收**不複製**進這裡：讀取端直接讀 `monthly_revenue_observations`，可用日＝`disclosure_deadline`
   （法定上界，不是實際公告日）——同一個數兩個 authority 會立刻開始偏離（L16）。

## 口徑與拒寫（沿用 `fetchers/edgar_xbrl.py` 的守則）

- tag 白名單；同一期間、同一份申報裡白名單 tag 給出不同的數 → 拒寫該期並列進報告（不挑一個）。
- 同一期間出現多種計價單位 → 拒寫（不換算）。
- 封面股數同一份申報出現多個值（多股類分維度申報）→ 拒寫，**不加總**。
- **10-K／10-Q 國內申報人**存季度＋年度；**20-F／40-F 發行人只存年度點**、不存封面股數（ADS 與普通股不是同一種
  證券單位）。誰是哪一種由 `classify_filer` 一個函式判（回填、增量、三題、稀釋燈都呼叫它）。
- companyfacts 比 EDGAR submissions 舊（`fetchers.edgar_xbrl.companyfacts_lag_status`）→ 這一檔**這一輪不寫**、
  記缺席；抓不到 submissions → 照寫並記「落後未知」（不是「沒落後」）。

## 這支不做的事

不換匯、不猜 ADR 比率、不回推台股歷史股數（沒有機械來源就記缺席）、不寫人工 ledger、不判讀任何東西。

用法::

    python -m engine_c.history_backfill                      # 全體回填（價格 3 年＋EDGAR），印報告摘要
    python -m engine_c.history_backfill --incremental        # daily：價格重抓、EDGAR 只在有新申報時重抓
    python -m engine_c.history_backfill --db <path> --tickers AXTI COHR --report <file.json>
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: 價格回填的窗（年）。已定價①的百分位窗是 3 年；多抓 30 天讓第一個交易日也有前後文。
PRICE_HISTORY_YEARS = 3
#: 基本面回填的窗（年）：3 年百分位的第一點要有 TTM，所以往前多一年；再留一年給重編比較欄。
FUNDAMENTAL_LOOKBACK_YEARS = 5

#: `fundamental_history.metric` 的封閉字彙。新增一種＝改契約（建表的 CHECK 同步）。
METRICS: tuple[str, ...] = (
    "revenue_quarter", "revenue_annual",
    "operating_income_quarter", "operating_income_annual",
    "cash", "total_debt", "shares_outstanding_cover",
)

#: 國內季度申報人的判定窗：最近 18 個月內有 10-Q。
QUARTERLY_WINDOW_DAYS = 548
FILER_CLASSES: tuple[str, ...] = ("domestic_quarterly", "foreign_annual", "unknown")

DOMESTIC_FORMS: tuple[str, ...] = ("10-K", "10-Q")        # 前綴：含 /A
FOREIGN_ANNUAL_FORMS: tuple[str, ...] = ("20-F", "40-F")

#: 期間長度（天）。13 週季度約 91 天、14 週季度 98 天都落在季度窗內；52／53 週制年度落在年度窗內。
_QUARTER_DAYS = (75, 105)
_NINE_MONTH_DAYS = (250, 290)
_ANNUAL_DAYS = (300, 400)

#: 存量（instant）指標的白名單：**每個 namespace 只放一個 tag**——現金與債務各家的拆法不同，
#: 放兩個以上歧異守則就會把整批合法的檔擋掉（`edgar_xbrl.IFRS_REVENUE_TAGS` 同一個理由）。
#: 債務只收「總額」的那一行；沒有這一行的公司淨負債就缺席、已定價①退回 P/S（照實標口徑），不拿分項相加。
INSTANT_TAGS: Mapping[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "cash": (("us-gaap", ("CashAndCashEquivalentsAtCarryingValue",)),
             ("ifrs-full", ("CashAndCashEquivalents",))),
    "total_debt": (("us-gaap", ("LongTermDebt",)), ("ifrs-full", ("Borrowings",))),
    "shares_outstanding_cover": (("dei", ("EntityCommonStockSharesOutstanding",)),),
}

SOURCE_PRICES = "yfinance://history"
SOURCE_EDGAR = "sec://companyfacts"


class HistoryBackfillError(RuntimeError):
    """輸入不合法（不是「抓不到」——抓不到記進報告，不 raise）。"""


# ---------------------------------------------------------------------------
# 建表
# ---------------------------------------------------------------------------

_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS price_history (
    ticker TEXT NOT NULL,
    bar_date TEXT NOT NULL,
    close_raw REAL,
    close_adjusted REAL,
    quote_unit TEXT,
    settlement_currency TEXT,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, bar_date)
);
CREATE TABLE IF NOT EXISTS corporate_actions (
    ticker TEXT NOT NULL,
    action_date TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('split')),
    ratio REAL NOT NULL CHECK (ratio > 0),
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, action_date, kind)
);
CREATE TABLE IF NOT EXISTS fundamental_history (
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL CHECK (metric IN ({metrics})),
    period_start TEXT,
    period_end TEXT NOT NULL,
    filed TEXT NOT NULL,
    accession TEXT NOT NULL,
    form TEXT NOT NULL,
    value REAL NOT NULL,
    currency TEXT NOT NULL,
    unit_scale INTEGER NOT NULL DEFAULT 1 CHECK (unit_scale > 0),
    derived TEXT,
    tag TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, metric, period_end, accession)
);
CREATE INDEX IF NOT EXISTS idx_fundamental_history_asof
    ON fundamental_history (ticker, metric, period_end, filed);
""".format(metrics=", ".join(f"'{m}'" for m in METRICS))


def ensure_history_schema(conn: sqlite3.Connection) -> None:
    """非破壞性建表（SQLite）。Postgres 走 `engine_c/migrations/20260929_add_history_tables.sql`。

    `engine_c.db._ensure_sqlite_schema` 每次開庫都呼叫它（比照 `ensure_monthly_revenue_schema`）；
    **只 CREATE IF NOT EXISTS，不動任何既有表**。
    """
    conn.executescript(_SQLITE_DDL)


# ---------------------------------------------------------------------------
# 申報人類別（回填、增量、三題、稀釋燈共用這一個函式）
# ---------------------------------------------------------------------------

def classify_filer(filings: Iterable[tuple[str, date]], *, today: date) -> tuple[str, str]:
    """`(form, filed)` 清單 → `(類別, 依據)`；類別 ∈ `FILER_CLASSES`。

    - `domestic_quarterly`：最近 18 個月內有 10-Q（季度＋年度都存；稀釋燈用封面股數）；
    - `foreign_annual`：最近 18 個月內沒有 10-Q、但有 20-F／40-F（只存年度點）；
    - `unknown`：兩者都沒有（下市、換掛牌、companyfacts 缺這一段）——**不猜**，消費端記缺席。

    輸入可以是 companyfacts 的 fact（回填時）或 `fundamental_history` 已存的列（讀取端，`filer_class()`）——
    兩者都是同一份 companyfacts 的 `form`／`filed`，所以判出來是同一個類別。
    """
    start = today - timedelta(days=QUARTERLY_WINDOW_DAYS)
    recent = [(str(f), d) for f, d in filings if d is not None and start <= d <= today]
    quarterly = sorted(d for f, d in recent if f.startswith("10-Q"))
    if quarterly:
        return "domestic_quarterly", f"最近 18 個月有 10-Q（最新 filed {quarterly[-1].isoformat()}）"
    foreign = sorted(d for f, d in recent if f.startswith(FOREIGN_ANNUAL_FORMS))
    if foreign:
        return "foreign_annual", f"最近 18 個月沒有 10-Q、有 20-F／40-F（最新 filed {foreign[-1].isoformat()}）"
    return "unknown", "最近 18 個月既沒有 10-Q 也沒有 20-F／40-F"


def filer_class(conn: Any, ticker: str, *, today: date) -> tuple[str, str]:
    """讀取端的申報人類別：從 `fundamental_history` 已存列的 `form`／`filed` 判（零網路）。"""
    rows = conn.execute("SELECT DISTINCT form, filed FROM fundamental_history WHERE ticker = ?",
                        (ticker,)).fetchall()
    pairs = []
    for form, filed in rows:
        try:
            pairs.append((str(form), date.fromisoformat(str(filed)[:10])))
        except ValueError:
            continue
    return classify_filer(pairs, today=today)


# ---------------------------------------------------------------------------
# EDGAR companyfacts → 列（純函式）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Fact:
    namespace: str
    tag: str
    value: float
    unit: str
    start: date | None
    end: date
    accession: str
    filed: date
    form: str


def _as_date(text: Any) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except (TypeError, ValueError):
        return None


def _facts(facts: Mapping[str, Any], namespace: str, tag: str, *, forms: Sequence[str]) -> list[_Fact]:
    node = ((facts.get("facts") or {}).get(namespace) or {}).get(tag)
    if not node:
        return []
    out: list[_Fact] = []
    for unit, entries in (node.get("units") or {}).items():
        for entry in entries or ():
            form = str(entry.get("form") or "")
            if not form.startswith(tuple(forms)):
                continue
            end, filed = _as_date(entry.get("end")), _as_date(entry.get("filed"))
            accession = str(entry.get("accn") or "")
            value = entry.get("val")
            if not (end and filed and accession) or isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            out.append(_Fact(namespace, tag, float(value), str(unit), _as_date(entry.get("start")), end,
                             accession, filed, form))
    return out


def _span_class(fact: _Fact) -> str | None:
    if fact.start is None:
        return "instant"
    days = (fact.end - fact.start).days
    for name, (lo, hi) in (("quarter", _QUARTER_DAYS), ("nine_month", _NINE_MONTH_DAYS),
                           ("annual", _ANNUAL_DAYS)):
        if lo <= days <= hi:
            return name
    return None


def _flow_tags(concept: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    from fetchers.edgar_xbrl import (
        IFRS_OPERATING_INCOME_TAGS, IFRS_REVENUE_TAGS, OPERATING_INCOME_TAGS, REVENUE_TAGS,
    )

    if concept == "revenue":
        return (("us-gaap", REVENUE_TAGS), ("ifrs-full", IFRS_REVENUE_TAGS))
    return (("us-gaap", OPERATING_INCOME_TAGS), ("ifrs-full", IFRS_OPERATING_INCOME_TAGS))


def _resolve_groups(candidates: Iterable[_Fact], key: Callable[[_Fact], tuple],
                    *, label: str, rejected: list[dict[str, Any]], multi_value_reason: str,
                    horizon: date | None = None) -> dict[tuple, _Fact]:
    """同一組（期間、申報）的白名單 fact 收斂成一筆；多單位或多值 → 拒寫並記原因（不挑一個）。

    `horizon`：期末早於它的組本來就不寫（回填窗外），拒寫**不記**——算進去會把拒寫數灌大（R2-c non-blocking #1）。
    ⚠ 窗只套在「記不記」，不套在候選：窗邊界之前的 9M 累計仍要拿來衍生窗內的第四季（R2-c 覆核 non-blocking #1）。
    """
    groups: dict[tuple, list[_Fact]] = {}
    for fact in candidates:
        groups.setdefault(key(fact), []).append(fact)
    out: dict[tuple, _Fact] = {}
    for group_key, facts in groups.items():
        units = {f.unit for f in facts}
        record = horizon is None or max(f.end for f in facts) >= horizon
        if len(units) > 1:
            if record:
                rejected.append({"metric": label, "key": [str(k) for k in group_key],
                                 "reason": f"同一期間同一份申報出現多種計價單位 {sorted(units)}——不換算，拒寫"})
            continue
        values = {round(f.value, 2) for f in facts}
        if len(values) > 1:
            if record:
                detail = "；".join(sorted(f"{f.namespace}:{f.tag}={f.value:,.0f}" for f in facts))
                rejected.append({"metric": label, "key": [str(k) for k in group_key],
                                 "reason": f"{multi_value_reason}（{detail}）——不挑一個，拒寫"})
            continue
        out[group_key] = sorted(facts, key=lambda f: (f.namespace, f.tag))[0]
    return out


def build_fundamental_rows(facts: Mapping[str, Any], *, ticker: str, filer: str, today: date,
                           fetched_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """companyfacts → `(fundamental_history 的列, 拒寫清單)`。**純函式**：不連網、不寫檔。

    `filer`：`domestic_quarterly` 存季度＋年度＋封面股數；`foreign_annual` 只存年度點（不存封面股數）；
    `unknown` 一列都不產生（呼叫端記缺席）。
    """
    if filer not in FILER_CLASSES:
        raise HistoryBackfillError(f"未知的申報人類別：{filer!r}")
    if filer == "unknown":
        return [], []
    forms = DOMESTIC_FORMS if filer == "domestic_quarterly" else FOREIGN_ANNUAL_FORMS
    horizon = today - timedelta(days=365 * FUNDAMENTAL_LOOKBACK_YEARS)
    rejected: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    def emit(metric: str, fact: _Fact, *, start: date | None = None, derived: str | None = None,
             filed: date | None = None, tag: str | None = None, value: float | None = None) -> None:
        if fact.end < horizon:
            return
        rows.append({
            "ticker": ticker, "metric": metric,
            "period_start": (start or fact.start).isoformat() if (start or fact.start) else None,
            "period_end": fact.end.isoformat(), "filed": (filed or fact.filed).isoformat(),
            "accession": fact.accession, "form": fact.form,
            "value": fact.value if value is None else value, "currency": fact.unit, "unit_scale": 1,
            "derived": derived, "tag": tag or f"{fact.namespace}:{fact.tag}",
            "source": SOURCE_EDGAR, "fetched_at": fetched_at,
        })

    for concept in ("revenue", "operating_income"):
        candidates = [f for namespace, tags in _flow_tags(concept) for tag in tags
                      for f in _facts(facts, namespace, tag, forms=forms)]
        by_span: dict[str, list[_Fact]] = {}
        for fact in candidates:
            span = _span_class(fact)
            if span in ("quarter", "nine_month", "annual"):
                by_span.setdefault(span, []).append(fact)
        key = lambda f: (f.start, f.end, f.accession)  # noqa: E731
        reason = "白名單 tag 對同一期間給出不同的數"
        annual = _resolve_groups(by_span.get("annual", ()), key, label=f"{concept}_annual",
                                 rejected=rejected, multi_value_reason=reason, horizon=horizon)
        for fact in annual.values():
            emit(f"{concept}_annual", fact)
        if filer != "domestic_quarterly":
            continue
        quarter = _resolve_groups(by_span.get("quarter", ()), key, label=f"{concept}_quarter",
                                  rejected=rejected, multi_value_reason=reason, horizon=horizon)
        for fact in quarter.values():
            emit(f"{concept}_quarter", fact)
        nine = _resolve_groups(by_span.get("nine_month", ()), key, label=f"{concept}_nine_month",
                               rejected=rejected, multi_value_reason=reason, horizon=horizon)
        # 第四季：companyfacts 沒有直接的 3 個月 fact 時，以「年度 − 同一會計年度的前三季累計」衍生，標 derived。
        # 累計取 `filed ≤ 年度 filed` 的最新一筆（那是年報發出時已知的版本）；filed 取兩者較晚者（INV-6）。
        quarter_ends = {f.end for f in quarter.values()}
        for fy in annual.values():
            if fy.end in quarter_ends or fy.start is None:
                continue
            nines = [n for n in nine.values()
                     if n.start == fy.start and n.end < fy.end and n.filed <= fy.filed and n.unit == fy.unit]
            if not nines:
                continue
            nm = max(nines, key=lambda n: (n.filed, n.end))
            emit(f"{concept}_quarter", fy, start=nm.end + timedelta(days=1),
                 derived=f"FY−9M：{fy.accession}（{fy.tag}）−{nm.accession}（{nm.tag}）",
                 filed=max(fy.filed, nm.filed), value=fy.value - nm.value,
                 tag=f"{fy.namespace}:{fy.tag}")

    for metric, spec in INSTANT_TAGS.items():
        if metric == "shares_outstanding_cover" and filer != "domestic_quarterly":
            continue
        candidates = [f for namespace, tags in spec for tag in tags
                      for f in _facts(facts, namespace, tag, forms=forms) if f.start is None]
        reason = ("同一份申報的封面股數有多個值（多股類分別申報）——不加總" if metric == "shares_outstanding_cover"
                  else "白名單 tag 對同一時點給出不同的數")
        resolved = _resolve_groups(candidates, lambda f: (f.end, f.accession), label=metric,
                                   rejected=rejected, multi_value_reason=reason, horizon=horizon)
        for fact in resolved.values():
            emit(metric, fact)
    return rows, rejected


# ---------------------------------------------------------------------------
# 價格（yfinance）→ 列
# ---------------------------------------------------------------------------

def build_price_rows(bars: Sequence[Mapping[str, Any]], *, ticker: str, quote_unit: str | None,
                     settlement_currency: str | None, fetched_at: str
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """`[{date, close, adj_close, split}]`（yfinance `auto_adjust=False` 的 Close 已做分割調整）→
    `(price_history 列, corporate_actions 列)`。**純函式**。

    `close_raw`＝`Close` × 該日之後所有分割比例的乘積：2024-06-07 NVDA 的 `Close` 是 120.89（已除以 10），
    當天實際成交約 1,208.9——市值要用當時的價乘當時的股數，兩者都得是「當時」的單位。
    """
    ordered = sorted((b for b in bars if b.get("date") is not None), key=lambda b: b["date"])
    splits = [(b["date"], float(b["split"])) for b in ordered if b.get("split") and float(b["split"]) > 0]
    actions = [{"ticker": ticker, "action_date": d.isoformat(), "kind": "split", "ratio": r,
                "source": SOURCE_PRICES, "fetched_at": fetched_at} for d, r in splits]
    rows = []
    for bar in ordered:
        # 沒有收盤也沒有調整後收盤的列不是觀測（2026-09-29 實測：歐股當天的列 yfinance 先給 NaN）——不寫，
        # 呼叫端以 `len(bars) - len(rows)` 計數進報告（INV-3：不靜默丟）。
        if bar.get("close") is None and bar.get("adj_close") is None:
            continue
        factor = 1.0
        for split_date, ratio in splits:
            if bar["date"] < split_date:
                factor *= ratio
        close = bar.get("close")
        rows.append({
            "ticker": ticker, "bar_date": bar["date"].isoformat(),
            "close_raw": (float(close) * factor if close is not None else None),
            "close_adjusted": (float(bar["adj_close"]) if bar.get("adj_close") is not None else None),
            "quote_unit": quote_unit, "settlement_currency": settlement_currency,
            "source": SOURCE_PRICES, "fetched_at": fetched_at,
        })
    return rows, actions


def fetch_price_bars(ticker: str, *, today: date) -> list[dict[str, Any]]:
    """yfinance 3 年日線（含今天）。取不到就 raise——空序列會被讀成「沒有價格」。"""
    import math

    import yfinance as yf

    start = today - timedelta(days=365 * PRICE_HISTORY_YEARS + 30)
    frame = yf.Ticker(ticker).history(start=start.isoformat(), end=(today + timedelta(days=1)).isoformat(),
                                      auto_adjust=False, actions=True)
    if frame is None or frame.empty:
        raise HistoryBackfillError(f"{ticker}：yfinance 沒有回任何日線")
    bars = []
    for index, row in frame.iterrows():
        close = row.get("Close")
        adj = row.get("Adj Close")
        split = row.get("Stock Splits")
        bars.append({
            "date": index.date(),
            "close": None if close is None or (isinstance(close, float) and math.isnan(close)) else float(close),
            "adj_close": None if adj is None or (isinstance(adj, float) and math.isnan(adj)) else float(adj),
            "split": float(split) if split and not (isinstance(split, float) and math.isnan(split)) else 0.0,
        })
    return bars


# ---------------------------------------------------------------------------
# 寫入（冪等）
# ---------------------------------------------------------------------------

def upsert_prices(conn: Any, rows: Sequence[Mapping[str, Any]], actions: Sequence[Mapping[str, Any]]) -> int:
    """價格與分割是可重建投影：同一天重抓就覆寫（股利會讓整條 adjusted 序列回頭改，所以每天整段重抓）。"""
    conn.executemany(
        """INSERT INTO price_history (ticker, bar_date, close_raw, close_adjusted, quote_unit,
                                      settlement_currency, source, fetched_at)
           VALUES (:ticker, :bar_date, :close_raw, :close_adjusted, :quote_unit,
                   :settlement_currency, :source, :fetched_at)
           ON CONFLICT (ticker, bar_date) DO UPDATE SET
               close_raw = excluded.close_raw, close_adjusted = excluded.close_adjusted,
               quote_unit = excluded.quote_unit, settlement_currency = excluded.settlement_currency,
               source = excluded.source, fetched_at = excluded.fetched_at""", list(rows))
    conn.executemany(
        """INSERT INTO corporate_actions (ticker, action_date, kind, ratio, source, fetched_at)
           VALUES (:ticker, :action_date, :kind, :ratio, :source, :fetched_at)
           ON CONFLICT (ticker, action_date, kind) DO UPDATE SET
               ratio = excluded.ratio, source = excluded.source, fetched_at = excluded.fetched_at""",
        list(actions))
    return len(rows)


def insert_fundamentals(conn: Any, rows: Sequence[Mapping[str, Any]]) -> int:
    """一份申報的一個數永遠不變：唯一鍵（ticker, metric, period_end, accession）已存在就不動（冪等）。"""
    before = conn.execute("SELECT COUNT(*) FROM fundamental_history").fetchone()[0]
    conn.executemany(
        """INSERT INTO fundamental_history (ticker, metric, period_start, period_end, filed, accession, form,
                                            value, currency, unit_scale, derived, tag, source, fetched_at)
           VALUES (:ticker, :metric, :period_start, :period_end, :filed, :accession, :form,
                   :value, :currency, :unit_scale, :derived, :tag, :source, :fetched_at)
           ON CONFLICT (ticker, metric, period_end, accession) DO NOTHING""", list(rows))
    return conn.execute("SELECT COUNT(*) FROM fundamental_history").fetchone()[0] - before


# ---------------------------------------------------------------------------
# 編排
# ---------------------------------------------------------------------------

def universe() -> list[tuple[str, str]]:
    """`(company_id, ticker)`——與 daily ETL 同一份宇宙（`identity.registry.TICKER_MAP` 的非 null 值）。"""
    from identity.registry import TICKER_MAP

    return sorted(((cid, t) for cid, t in TICKER_MAP.items() if t), key=lambda x: x[1])


def _registry_units(company_id: str) -> tuple[str | None, str | None]:
    from identity.registry import get_registry

    company = get_registry().company(company_id)
    return (getattr(company, "market_quote_unit", None), getattr(company, "market_currency", None))


def _latest_stored_filed(conn: Any, ticker: str) -> date | None:
    row = conn.execute("SELECT MAX(filed) FROM fundamental_history WHERE ticker = ?", (ticker,)).fetchone()
    return _as_date(row[0]) if row and row[0] else None


def _metric_summary(conn: Any, ticker: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for metric, n, first, last, filed in conn.execute(
            """SELECT metric, COUNT(*), MIN(period_end), MAX(period_end), MAX(filed)
               FROM fundamental_history WHERE ticker = ? GROUP BY metric""", (ticker,)):
        out[metric] = {"rows": n, "earliest_period_end": first, "latest_period_end": last, "latest_filed": filed}
    return out


def backfill_ticker_edgar(conn: Any, ticker: str, cik: str | None, *, today: date, incremental: bool,
                          fetched_at: str, fetch_facts: Callable[[str], Mapping[str, Any]] | None = None,
                          lag_status: Callable[..., Mapping[str, Any]] | None = None,
                          submissions_latest: Callable[[str, Sequence[str]], date | None] | None = None,
                          ) -> dict[str, Any]:
    """一檔的 EDGAR 段。每一條路都落到一個具名結局（INV-3：「查不到了」不是合法 lifecycle）。"""
    from fetchers.edgar_xbrl import XbrlUnavailable, companyfacts_lag_status, fetch_companyfacts

    fetch_facts = fetch_facts or fetch_companyfacts
    lag_status = lag_status or companyfacts_lag_status
    report: dict[str, Any] = {"cik": cik}
    if not cik:
        report.update(outcome="no_cik", absence=(
            "帶交易所後綴的非美國掛牌——不查 SEC，EDGAR 不適用" if "." in ticker else
            "company_tickers.json 查不到這個 ticker——不是 SEC 申報人，EDGAR 不適用"))
        return report
    if incremental:
        stored = _latest_stored_filed(conn, ticker)
        if stored is not None and submissions_latest is not None:
            try:
                newest = submissions_latest(cik, DOMESTIC_FORMS + FOREIGN_ANNUAL_FORMS)
            except Exception as exc:  # noqa: BLE001 — 抓不到就照常重抓 companyfacts，不猜「沒新申報」
                newest = None
                report["submissions_error"] = type(exc).__name__
            if newest is not None and newest <= stored:
                report.update(outcome="unchanged", latest_filed=stored.isoformat())
                return report
    try:
        facts = fetch_facts(cik)
    except XbrlUnavailable as exc:
        report.update(outcome="unavailable", absence=str(exc))
        return report
    forms_seen = []
    for namespace in (facts.get("facts") or {}).values():
        for entry in namespace.values():
            for items in (entry.get("units") or {}).values():
                for item in items:
                    forms_seen.append((str(item.get("form") or ""), _as_date(item.get("filed"))))
    filer, basis = classify_filer(forms_seen, today=today)
    report.update(filer_class=filer, filer_basis=basis)
    if filer == "unknown":
        report.update(outcome="unknown_filer", absence=basis)
        return report
    forms = DOMESTIC_FORMS if filer == "domestic_quarterly" else FOREIGN_ANNUAL_FORMS
    # R2-c（2026-09-29）：快照日只看**會被消費的營收白名單 fact**——TSM／UMC 最新 20-F 只收到封面 dei／srt，
    # 看全部 namespace 會被推成 current，FY2025 營收就靜默缺席。
    lag = dict(lag_status(cik, facts, forms=forms, snapshot_tags=revenue_whitelist()))
    report["lag"] = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in lag.items()}
    if lag.get("status") == "lagging":
        report.update(outcome="lagging", absence=lag.get("warning"))
        return report
    rows, rejected = build_fundamental_rows(facts, ticker=ticker, filer=filer, today=today, fetched_at=fetched_at)
    written = insert_fundamentals(conn, rows)
    report.update(outcome="written", rows_built=len(rows), rows_new=written, rejected=rejected,
                  lag_unknown=(lag.get("status") == "unknown"))
    return report


def revenue_whitelist() -> set[tuple[str, str]]:
    """落後檢查的快照 tag：營收白名單（us-gaap＋ifrs-full）。它是每一檔都一定會消費的那一組 fact。"""
    return {(namespace, tag) for namespace, tags in _flow_tags("revenue") for tag in tags}


def _submissions_latest(cik: str, forms: Sequence[str]) -> date | None:
    from fetchers.edgar import get_filings

    filed = [_as_date(f.get("filed_date")) for f in get_filings(cik, list(forms), 1, raise_on_error=True)]
    filed = [d for d in filed if d is not None]
    return max(filed) if filed else None


def run(conn: Any, *, tickers: Sequence[str] | None = None, incremental: bool = False, today: date | None = None,
        sleep: float = 0.15, prices: bool = True, edgar: bool = True) -> dict[str, Any]:
    """回填（或增量）一批標的，回報告。任何一檔失敗都不讓整批停（記進報告）。"""
    today = today or date.today()
    fetched_at = datetime.now(timezone.utc).isoformat()
    pairs = universe()
    if tickers:
        wanted = {t.upper() for t in tickers}
        pairs = [(c, t) for c, t in pairs if t.upper() in wanted]
        missing = sorted(wanted - {t.upper() for _c, t in pairs})
        if missing:
            raise HistoryBackfillError(f"不在 Engine C 宇宙（TICKER_MAP）：{missing}")
    report: dict[str, Any] = {"mode": "incremental" if incremental else "backfill", "today": today.isoformat(),
                              "fetched_at": fetched_at, "tickers": {}}
    cik_map: dict[str, str] | None = None
    cik_error = None
    if edgar:
        try:
            from fetchers.edgar import ticker_cik_map

            cik_map = ticker_cik_map()
        except Exception as exc:  # noqa: BLE001
            cik_error = f"company_tickers.json 抓不到：{type(exc).__name__}"
            report["cik_map_error"] = cik_error
    for company_id, ticker in pairs:
        entry: dict[str, Any] = {"company_id": company_id}
        if prices:
            quote_unit, settlement = _registry_units(company_id)
            try:
                bars = fetch_price_bars(ticker, today=today)
                rows, actions = build_price_rows(bars, ticker=ticker, quote_unit=quote_unit,
                                                 settlement_currency=settlement, fetched_at=fetched_at)
                upsert_prices(conn, rows, actions)
                conn.commit()
                entry["prices"] = {"outcome": "written", "rows": len(rows), "splits": len(actions),
                                   "empty_bars_skipped": len(bars) - len(rows),
                                   "earliest": rows[0]["bar_date"] if rows else None,
                                   "latest": rows[-1]["bar_date"] if rows else None,
                                   "quote_unit": quote_unit, "settlement_currency": settlement}
            except Exception as exc:  # noqa: BLE001
                entry["prices"] = {"outcome": "unavailable", "absence": f"{type(exc).__name__}: {exc}"[:300]}
        if edgar:
            if cik_map is None:
                entry["edgar"] = {"outcome": "unavailable", "absence": cik_error}
            else:
                cik = cik_map.get(ticker.upper()) if "." not in ticker else None
                try:
                    entry["edgar"] = backfill_ticker_edgar(
                        conn, ticker, cik, today=today, incremental=incremental, fetched_at=fetched_at,
                        submissions_latest=_submissions_latest)
                    conn.commit()
                except Exception as exc:  # noqa: BLE001
                    conn.rollback()
                    entry["edgar"] = {"cik": cik, "outcome": "error", "absence": f"{type(exc).__name__}: {exc}"[:300]}
                entry["edgar"]["metrics"] = _metric_summary(conn, ticker)
                if cik:
                    time.sleep(sleep)
        report["tickers"][ticker] = entry
    report["summary"] = summarize(report)
    return report


def summarize(report: Mapping[str, Any]) -> dict[str, Any]:
    from collections import Counter

    tickers = report.get("tickers") or {}
    return {
        "tickers": len(tickers),
        "prices": dict(Counter((e.get("prices") or {}).get("outcome", "skipped") for e in tickers.values())),
        "edgar": dict(Counter((e.get("edgar") or {}).get("outcome", "skipped") for e in tickers.values())),
        "filer_class": dict(Counter((e.get("edgar") or {}).get("filer_class", "—") for e in tickers.values())),
        "rejected_groups": sum(len((e.get("edgar") or {}).get("rejected") or ()) for e in tickers.values()),
    }


def _open(db: str | None):
    if db:
        from engine_c.db import _ensure_sqlite_schema

        conn = sqlite3.connect(db)
        _ensure_sqlite_schema(conn)
        return conn
    from engine_c.db import _use_postgres, get_conn

    if _use_postgres():
        raise HistoryBackfillError("歷史回填目前只支援 SQLite（現行後端）；Postgres 由 migration 建表，寫入未接")
    return get_conn()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Engine C 機械歷史表：回填／daily 增量（零 LLM）")
    parser.add_argument("--db", help="SQLite 路徑（省略＝runtime pointer 指的正式庫）")
    parser.add_argument("--tickers", nargs="*", help="只跑這幾檔（預設＝TICKER_MAP 全體）")
    parser.add_argument("--incremental", action="store_true",
                        help="daily：價格整段重抓、EDGAR 只在 submissions 有新申報時重抓")
    parser.add_argument("--no-prices", action="store_true")
    parser.add_argument("--no-edgar", action="store_true")
    parser.add_argument("--report", help="完整報告寫到這個 JSON 檔")
    args = parser.parse_args(argv)
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    conn = _open(args.db)
    try:
        report = run(conn, tickers=args.tickers, incremental=args.incremental,
                     prices=not args.no_prices, edgar=not args.no_edgar)
    finally:
        conn.close()
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "summary": report["summary"]}, ensure_ascii=False))
    # 單檔失敗不 fail 整步（daily 其他 ETL 的慣例）；全部價格都抓不到才 exit 1，讓心跳段 1 看得到。
    return 1 if prices_all_failed(report) else 0


def prices_all_failed(report: Mapping[str, Any]) -> bool:
    outcomes = [(e.get("prices") or {}).get("outcome") for e in (report.get("tickers") or {}).values()]
    outcomes = [o for o in outcomes if o is not None]
    return bool(outcomes) and all(o == "unavailable" for o in outcomes)


if __name__ == "__main__":
    raise SystemExit(main())
