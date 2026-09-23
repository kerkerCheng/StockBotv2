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
from pathlib import Path
from typing import Any, Mapping

_ROOT = Path(__file__).resolve().parents[2]
ENGINE_C_DB = _ROOT / "library" / "private" / "engine_c" / "stockbot-engine-c-private-v1-458db5270ee2.db"


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
    ticker: str, conn: sqlite3.Connection, cache: dict[str, float | None],
) -> tuple[float | None, str | None]:
    """→ (市值 USD, 缺席理由)。**拿不到就回 None＋理由，絕不回 0**。

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
    row = conn.execute(
        "SELECT price, shares_outstanding FROM financial_snapshots "
        "WHERE ticker=? ORDER BY COALESCE(bar_date, snapshot_date) DESC LIMIT 1", (ticker,)).fetchone()
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


def analyst_count(ticker: str, conn: sqlite3.Connection) -> int | None:
    """賣方覆蓋家數。⚠ 取 **0y**（base 假設校準的那一年），不是 +1y。

    +1y 會在 rollover 當天崩塌——2026-09-19 實測 LITE 的 +1y 由 22 人變 1 人，
    而它的 base 校準在 0y。拿 +1y 當覆蓋門檻會在每年某一天把整批標的誤判成「無人覆蓋」。
    """
    row = conn.execute(
        "SELECT analyst_count FROM consensus_estimates WHERE ticker=? AND metric='eps' "
        "AND relative_label='0y' ORDER BY snapshot_date DESC LIMIT 1", (ticker,)).fetchone()
    return int(row["analyst_count"]) if row and row["analyst_count"] is not None else None


def screen_inputs(tickers: list[str], *, db_path: Path | None = None) -> dict[str, Mapping[str, Any]]:
    """一次取好一批標的的市值（USD）與覆蓋家數。**同一個 FX 快取，一輪只打一次外部。**"""
    conn = sqlite3.connect(db_path or ENGINE_C_DB)
    conn.row_factory = sqlite3.Row
    cache: dict[str, float | None] = {}
    try:
        out: dict[str, Mapping[str, Any]] = {}
        for ticker in tickers:
            cap, absence = normalized_market_cap(ticker, conn, cache)
            out[ticker] = {"market_cap_usd": cap, "market_cap_absence": absence,
                           "analyst_count": analyst_count(ticker, conn)}
        return out
    finally:
        conn.close()


__all__ = ["ENGINE_C_DB", "analyst_count", "normalized_market_cap", "screen_inputs", "to_usd"]
