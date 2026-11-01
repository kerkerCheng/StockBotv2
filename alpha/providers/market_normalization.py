"""市值正規化：報價單位 → 結算幣別 → USD（2026-09-19，Phase 4a）。

**跨標的比較之前必須做這件事，而且錯的方向最糟**——未正規化的市值會把最像
「邊緣小公司」的標的當成超大型股擋掉。實測 IQE.L 未正規化 54.8B → 正規化後 **0.76B**
（籃子裡最小的一檔），而 D11 的市值上限是 10B。

## 兩步，缺一不可

1. **報價單位 → 結算幣別**：registry 的 `market_quote_unit`／`market_currency`
   ＋ `identity/currency.py`（LSE 報 `GBp`、TASE 報 `ILA` 等 minor unit 差 100 倍）
2. **結算幣別 → USD**：`engine_c.market_data.get_fx_snapshot`

## ⚠ 為什麼這一支住 providers 而不是 provider 內部

`alpha/providers/fundamentals.py` 的 `market()` **刻意不換算 USD**（2026-09-19 缺陷 7）：
換算需要 FX，而 FX 要打外部——放進 provider 就等於**每次建 packet 都打外部**。
那一層只負責讓單位跟著值走；**正規化的責任在需要跨標的比較的那一層**，而那一層
一輪只跑一次（原本是 `webapp materialize --basket` 與 `scripts/alpha_screen_check.py`，兩者已於
2026-09-23 Phase 0 退役；Phase 3 候選板接手時仍從這裡取正規化後的值，`config/alpha_screen.json` 留）。

⚠ 這與 APP 呈現契約不衝突：**request path 不得抓外部，materialize 不是 request path**。

## 缺值不得靜默

拿不到就回 `(None, 理由)`，**絕不回 0**（INV-3）。消費端必須把「市值取不到」
記成自己的一種 filter 理由，不得併進「超標」，也不得靜默放行。
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Mapping

_ROOT = Path(__file__).resolve().parents[2]
ENGINE_C_DB = _ROOT / "library" / "private" / "engine_c" / "stockbot-engine-c-private-v1-458db5270ee2.db"


def _as_of_clause(as_of: date | None) -> tuple[str, tuple[str, ...]]:
    """`as_of` 給了就只看 `snapshot_date <= as_of` 的列（INV-6：T 時刻我知道什麼——用的是**取得日**，不是 bar 日）。
    邊緣門檻的遲滯（ROADMAP 2026-11-01）用它重算「輸入日前一天」的判定；回放驗收用同一條路。"""
    return (" AND snapshot_date <= ?", (as_of.isoformat(),)) if as_of is not None else ("", ())


def to_usd(amount: float, currency: str, cache: dict[str, float | None]) -> float | None:
    """結算幣別 → USD。`cache` 由呼叫端持有，**同一輪只打一次外部**。"""
    if currency.upper() == "USD":
        return amount
    pair = f"{currency.upper()}/USD"
    if pair not in cache:
        from engine_c.market_data import get_fx_snapshot

        cache[pair] = get_fx_snapshot(pair, "").get("rate")
    rate = cache[pair]
    return None if rate is None else amount * rate


def normalized_market_cap(
    ticker: str, conn: sqlite3.Connection, cache: dict[str, float | None], *, as_of: date | None = None,
) -> tuple[float | None, str | None]:
    """→ (市值 USD, 缺席理由)。**拿不到就回 None＋理由，絕不回 0**。`as_of`：只看取得日 ≤ 那一天的快照。

    ⚠ 報價單位與結算幣別**一律問 registry**：`identity/registry.py` 早就把
    `market_currency` 拆成 `market_quote_unit`（`GBp`）與 `market_currency`（`GBP`）
    兩個欄位，自己 parse 一份 JSON 就是重造，而重造品會立刻開始偏離（L16）。
    """
    from identity.currency import resolve_quote_unit
    from identity.registry import get_registry

    registry = get_registry()
    company_id = registry.company_id_for_ticker(ticker)
    if not company_id:
        return None, "registry 解析不到 company_id"
    company = registry.company(company_id)
    raw_unit = getattr(company, "market_quote_unit", None)
    settlement = getattr(company, "market_currency", None)
    if not raw_unit or not settlement:
        return None, "registry 沒有可解析的 market_currency，無法判斷報價單位（fail closed）"
    clause, params = _as_of_clause(as_of)
    row = conn.execute(
        "SELECT price, shares_outstanding FROM financial_snapshots "
        f"WHERE ticker=?{clause} ORDER BY COALESCE(bar_date, snapshot_date) DESC LIMIT 1", (ticker, *params)).fetchone()
    if not row or not row["price"] or not row["shares_outstanding"]:
        return None, "快照缺 price 或 shares_outstanding"
    unit = resolve_quote_unit(raw_unit)
    if unit is None:
        return None, f"報價單位 {raw_unit!r} 未登記於 currency_units.json（fail closed）"
    price = unit.to_settlement(row["price"]) if unit.is_minor_unit else row["price"]
    usd = to_usd(price * row["shares_outstanding"], str(settlement), cache)
    if usd is None:
        return None, f"取不到 {settlement}/USD 匯率"
    return usd, None


#: 覆蓋家數的三個來源（Phase 7 批次二 E10，failure log #64；使用者 2026-10-21 Q4 A）：取三者最大，門檻 12 照舊。
#: 事發：10-16 五檔只看 EPS 0y 被判邊緣（002472.SZ 8→19、002837.SZ 2→13、688017.SS 5→14、SOI.PA 6→19、XPEV 3→25），
#: 10-17 0522.HK 一天內 18→7 翻盤——provider 對 EPS 那一欄常常漏人，營收與目標價那兩欄才是全的。
COVERAGE_SOURCES: tuple[tuple[str, str], ...] = (
    ("eps_0y", "consensus_estimates：eps 0y"),
    ("revenue_0y", "consensus_estimates：revenue 0y"),
    ("target_price", "financial_snapshots：analyst_target_count"),
)


def coverage_counts(ticker: str, conn: sqlite3.Connection, *, as_of: date | None = None) -> dict[str, int | None]:
    """三個來源各自的家數（None＝沒有可用的量測）。⚠ 一律取 **0y**（base 假設校準的那一年），不是 +1y——
    2026-09-19 實測 LITE 的 +1y 在 rollover 當天由 22 人變 1 人。`as_of`：只看取得日 ≤ 那一天的列。

    ⚠ **家數 0 而估值也是 0 的列是 provider 的空殼列**（2026-10-21 實測 3163.TWO、3234.TWO 等 6 檔的營收 0y：avg／low／high
    全 0.0、家數 0）——那不是「零位分析師」的量測，當缺值；否則它們會由「無法量」變「邊緣」（L11-5：我找不到≠不存在）。"""
    clause, params = _as_of_clause(as_of)

    def estimate(metric: str) -> int | None:
        row = conn.execute(
            "SELECT analyst_count, estimate_avg FROM consensus_estimates WHERE ticker=? AND metric=? "
            f"AND relative_label='0y'{clause} ORDER BY snapshot_date DESC LIMIT 1", (ticker, metric, *params)).fetchone()
        if not row or row["analyst_count"] is None:
            return None
        if int(row["analyst_count"]) == 0 and not row["estimate_avg"]:
            return None
        return int(row["analyst_count"])

    row = conn.execute("SELECT analyst_target_count, analyst_target_mean FROM financial_snapshots WHERE ticker=? "
                       f"{clause} ORDER BY snapshot_date DESC LIMIT 1", (ticker, *params)).fetchone()
    target = None
    if row and row["analyst_target_count"] is not None and (row["analyst_target_count"] or row["analyst_target_mean"]):
        target = int(row["analyst_target_count"])
    return {"eps_0y": estimate("eps"), "revenue_0y": estimate("revenue"), "target_price": target}


def analyst_count(ticker: str, conn: sqlite3.Connection) -> int | None:
    """賣方覆蓋家數＝三個來源（`COVERAGE_SOURCES`）裡有量測的最大值；三個都沒有 → None（無法量）。"""
    counts = [n for n in coverage_counts(ticker, conn).values() if n is not None]
    return max(counts) if counts else None


def inputs_as_of(ticker: str, conn: sqlite3.Connection, *, as_of: date | None = None) -> str | None:
    """這一檔判定實際用到的**最新取得日**（快照與 0y 共識兩張表取大；`as_of` 給了就只看那天以前的）。None＝兩張表都沒有列。

    邊緣門檻的遲滯（2026-11-01）靠它定義「前一次判定」＝輸入日前一天的判定——同一天第二次 materialize 用的是同一筆快照，
    不得被數成「連續兩次」（plan 四問④）。"""
    clause, params = _as_of_clause(as_of)
    days: list[str] = []
    for sql in (f"SELECT MAX(snapshot_date) AS d FROM financial_snapshots WHERE ticker=?{clause}",
                f"SELECT MAX(snapshot_date) AS d FROM consensus_estimates WHERE ticker=? AND relative_label='0y'{clause}"):
        row = conn.execute(sql, (ticker, *params)).fetchone()
        if row and row["d"]:
            days.append(str(row["d"])[:10])
    return max(days) if days else None


def screen_inputs(tickers: list[str], *, db_path: Path | None = None, as_of: date | None = None,
                  fx_cache: dict[str, float | None] | None = None) -> dict[str, Mapping[str, Any]]:
    """一次取好一批標的的市值（USD）與覆蓋家數。**同一個 FX 快取，一輪只打一次外部**——呼叫端要跨兩次呼叫共用就傳 `fx_cache`。
    `as_of`：只看取得日 ≤ 那一天的列（遲滯的「前一次判定」與回放用）；每檔另回報實際用到的輸入日 `inputs_as_of`。
    ⚠ 匯率沒有歷史表（fx_history 只有 TWD／KRW）：as-of 的市值用的是**當下**的匯率——帶內純由匯率造成的翻轉這裡看不到。"""
    conn = sqlite3.connect(db_path or ENGINE_C_DB)
    conn.row_factory = sqlite3.Row
    cache: dict[str, float | None] = fx_cache if fx_cache is not None else {}
    try:
        out: dict[str, Mapping[str, Any]] = {}
        for ticker in tickers:
            cap, absence = normalized_market_cap(ticker, conn, cache, as_of=as_of)
            counts = coverage_counts(ticker, conn, as_of=as_of)
            measured = [n for n in counts.values() if n is not None]
            out[ticker] = {"market_cap_usd": cap, "market_cap_absence": absence,
                           "analyst_count": max(measured) if measured else None, "coverage_counts": counts,
                           "as_of": as_of.isoformat() if as_of is not None else None,
                           "inputs_as_of": inputs_as_of(ticker, conn, as_of=as_of)}
        return out
    finally:
        conn.close()


__all__ = ["ENGINE_C_DB", "analyst_count", "inputs_as_of", "normalized_market_cap", "screen_inputs", "to_usd"]
