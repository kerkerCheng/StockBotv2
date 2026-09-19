#!/usr/bin/env python
"""`config/alpha_screen.json` 的門檻**套下去會怎樣** —— 量測，不改變任何行為。

## 為什麼是一支量測腳本，而不是直接接進籃子 filter

ROADMAP Phase 4 的驗收是「`top_pick` 的判定條件由三條變六條」。本檔只落地其中**兩條**
（市值上限、覆蓋家數上限），而且刻意**不改 `webapp/basket.py`**：

1. **先量測，後放閘**（L14-3）。放閘之前要先答得出「現有 16 檔有幾檔的判定真的變了」，
   而那正是本檔的輸出。
2. 正式接進 filter 還缺兩個決定：FX 要不要在每次 materialize 打外部、
   市值取不到時 D11 怎麼判（INV-3：不得靜默 filtered，也不得靜默放行）。
3. ⚠ 套下去會讓目前唯一的 `top_pick`（LITE）被擋、籃子變空。
   **那是合法結果**（AGENTS.md：籃子空就空，不得為了非空放寬條件），
   但它是一個該由人看過再放行的結論，不是順手改掉的參數。

所以這支腳本是 `config/alpha_screen.json` 的 consumer（INV-4：producer 指得出 consumer），
也是 Phase 4 正式實作時的驗收基準。

## 市值正規化（兩步，缺一不可）

未正規化的市值**不可跨標的比較**，而且錯的方向最糟——它會把最像「邊緣小公司」的標的
當成超大型股擋掉。實測：IQE.L 未正規化 54.8B → 正規化後 **0.76B**（籃子裡最小）。

- ①報價單位 → 結算幣別：registry 的 `market_currency` ＋ `identity/currency.py`
  （LSE 報 GBp、TASE 報 ILA 等 minor unit 差 100 倍）
- ②結算幣別 → USD：`engine_c.market_data.get_fx_snapshot`（pair 格式是 `GBP/USD`）

用法：
    python scripts/alpha_screen_check.py
    python scripts/alpha_screen_check.py --json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

CONFIG = _ROOT / "config" / "alpha_screen.json"
BASKET = _ROOT / "library" / "private" / "app" / "state" / "basket.json"
ENGINE_C = _ROOT / "library" / "private" / "engine_c" / "stockbot-engine-c-private-v1-458db5270ee2.db"

#: 封閉字彙。缺值**自成一類**，不併進「超標」也不靜默放行（INV-3）。
REASONS = {
    "market_cap_above_max": "市值高於上限（正規化為 USD 後比較）",
    "analyst_count_above_max": "賣方覆蓋家數高於上限",
    "market_cap_unknown": "市值取不到或無法正規化——不得靜默放行，也不得靜默擋掉",
    "analyst_count_unknown": "覆蓋家數取不到",
}


def _to_usd(amount: float, currency: str, cache: dict[str, float | None]) -> float | None:
    if currency == "USD":
        return amount
    pair = f"{currency}/USD"
    if pair not in cache:
        from engine_c.market_data import get_fx_snapshot

        cache[pair] = get_fx_snapshot(pair, "").get("rate")
    rate = cache[pair]
    return None if rate is None else amount * rate


def normalized_market_cap(ticker: str, conn: sqlite3.Connection,
                          cache: dict[str, float | None]) -> tuple[float | None, str | None]:
    """→ (市值 USD, 缺席理由)。**拿不到就回 None＋理由，絕不回 0**。

    ⚠ 報價單位與結算幣別**一律問 registry，不自己 parse `company_identity.json`**
    （2026-09-19）：`identity/registry.py` 早就把 `market_currency` 拆成
    `market_quote_unit`（`GBp`）與 `market_currency`（`GBP`）兩個欄位，本檔原本重造了一份
    ——而重造品會立刻開始偏離（L16）。同一份分類現在也跟著 packet 走
    （`MarketSnapshot.quote_unit`／`settlement_currency`）。
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
        "WHERE ticker=? ORDER BY snapshot_date DESC LIMIT 1", (ticker,)).fetchone()
    if not row or not row["price"] or not row["shares_outstanding"]:
        return None, "快照缺 price 或 shares_outstanding"
    unit = resolve_quote_unit(raw_unit)
    if unit is None:
        return None, f"報價單位 {raw_unit!r} 未登記於 currency_units.json（fail closed）"
    # ①報價單位 → 結算幣別（GBp→GBP 等 minor unit 差 100 倍）
    price = unit.to_settlement(row["price"]) if unit.is_minor_unit else row["price"]
    # ②結算幣別 → USD
    usd = _to_usd(price * row["shares_outstanding"], str(settlement), cache)
    if usd is None:
        return None, f"取不到 {settlement}/USD 匯率"
    return usd, None


def analyst_count(ticker: str, conn: sqlite3.Connection) -> int | None:
    """⚠ 取 **0y**（base 假設校準的那一年），不是 +1y——+1y 會在 rollover 當天崩塌
    （2026-09-19 實測 LITE 的 +1y 由 22 人變 1 人）。"""
    row = conn.execute(
        "SELECT analyst_count FROM consensus_estimates WHERE ticker=? AND metric='eps' "
        "AND relative_label='0y' ORDER BY snapshot_date DESC LIMIT 1", (ticker,)).fetchone()
    return int(row["analyst_count"]) if row and row["analyst_count"] is not None else None


def screen() -> dict[str, Any]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    cap_max = float(config["market_cap_max_usd"])
    analyst_max = int(config["analyst_count_max"])
    tickers = [r["ticker"] for r in json.loads(BASKET.read_text(encoding="utf-8"))["rows"]]

    conn = sqlite3.connect(ENGINE_C)
    conn.row_factory = sqlite3.Row
    cache: dict[str, float | None] = {}
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        cap, cap_absence = normalized_market_cap(ticker, conn, cache)
        count = analyst_count(ticker, conn)
        reasons: list[str] = []
        if cap is None:
            reasons.append("market_cap_unknown")
        elif cap > cap_max:
            reasons.append("market_cap_above_max")
        if count is None:
            reasons.append("analyst_count_unknown")
        elif count > analyst_max:
            reasons.append("analyst_count_above_max")
        rows.append({"ticker": ticker, "market_cap_usd": cap, "market_cap_absence": cap_absence,
                     "analyst_count": count, "reasons": reasons, "passes": not reasons})

    counts: dict[str, int] = {key: 0 for key in REASONS}
    for row in rows:
        for reason in row["reasons"]:
            counts[reason] += 1
    return {"thresholds": {"market_cap_max_usd": cap_max, "analyst_count_max": analyst_max},
            "input": len(rows), "accepted": sum(1 for r in rows if r["passes"]),
            "filtered": sum(1 for r in rows if not r["passes"]),
            "reason_labels": REASONS, "reasons": counts,
            "rows": sorted(rows, key=lambda r: (r["market_cap_usd"] is None, r["market_cap_usd"] or 0))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = screen()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0
    thresholds = result["thresholds"]
    print(f"# alpha_screen 門檻套用結果（量測，未改變任何行為）")
    print(f"門檻：市值 ≤ US${thresholds['market_cap_max_usd']:,.0f}｜覆蓋家數 ≤ {thresholds['analyst_count_max']}")
    print(f"input {result['input']}／accepted {result['accepted']}／filtered {result['filtered']}\n")
    print(f"{'tick':<11}{'市值(USD 十億)':<16}{'覆蓋':<7}{'判定'}")
    print("-" * 68)
    for row in result["rows"]:
        cap = f"{row['market_cap_usd'] / 1e9:,.2f}" if row["market_cap_usd"] else "—"
        verdict = "✅ 通過" if row["passes"] else "｜".join(row["reasons"])
        print(f"{row['ticker']:<11}{cap:<16}{str(row['analyst_count']):<7}{verdict}")
    print("\n理由計數：", json.dumps(result["reasons"], ensure_ascii=False))
    print("⚠ 這是量測，不是 filter——`webapp/basket.py` 的 top_pick 判定完全未改（先量測，後放閘）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
