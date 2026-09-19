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

#: 封閉字彙。缺值**自成一類**，不併進「超標」也不靜默放行（INV-3）。
REASONS = {
    "market_cap_above_max": "市值高於上限（正規化為 USD 後比較）",
    "analyst_count_above_max": "賣方覆蓋家數高於上限",
    "market_cap_unknown": "市值取不到或無法正規化——不得靜默放行，也不得靜默擋掉",
    "analyst_count_unknown": "覆蓋家數取不到",
}


# ⚠ 正規化與覆蓋家數的 SSOT 已於 2026-09-19 搬到 `alpha/providers/market_normalization.py`
# ——`webapp/basket.py` 的 filter 與本量測腳本現在用**同一支**（L16：兩個消費端各留一份
# 必然開始偏離）。本檔只負責「套門檻並印表」。
from alpha.providers.market_normalization import (  # noqa: E402
    ENGINE_C_DB as _ENGINE_C_DB, analyst_count, normalized_market_cap,
)

def bottleneck_share_upper_bounds() -> list[tuple[str, float | None]]:
    """D11 第五條「瓶頸業務占營收下限」的**鑑別力量測**（2026-09-19，Phase 4a）。

    ⚠ **這一條至今沒有接進 filter，而這支函式就是不接的理由。**

    系統沒有「瓶頸業務占營收」這個數字——大部分公司不揭露到那個顆粒度。
    能拿到的最細是 `segment_revenue_share`（分部占比），而**分部占比是真值的上界**：
    瓶頸業務一定包含在某個分部裡，所以「瓶頸業務占比 ≤ 最大分部占比」。
    上界低於門檻 → **確定不合格**；上界高於門檻 → **什麼都不能說**
    （TSM 的 HPC 分部 57.6% 裡，矽光子晶粒只是極小一塊）。

    **2026-09-19 實測 15／16 檔有分部資料，用上界法的鑑別力：**
    門檻 20% → 擋 0 檔｜30% → 0 檔｜40% → 2 檔｜50% → 2 檔｜60% → 8 檔。
    合理門檻（20–40%）下**擋 0–2 檔＝恆滅，零鑑別力**（L14-4：清除率近 0 的不是閘門）。
    而把門檻拉到 60% 才擋得動時，被擋的是 TSM／AVGO／SOI.PA 這些**分部切得比較細**的公司
    ——**那不是 D11 想擋的東西**（它想擋的是「瓶頸業務只佔 3%」那種）。

    **所以這條規則要生效，缺的不是對應表，是「瓶頸業務的營收」這個數字本身。**
    """
    import sqlite3

    from alpha.contracts import Ticker
    from alpha.providers.fundamentals import EngineCFundamentalsProvider

    del sqlite3
    provider = EngineCFundamentalsProvider()
    tickers = [r["ticker"] for r in json.loads(BASKET.read_text(encoding="utf-8"))["rows"]]
    out: list[tuple[str, float | None]] = []
    for ticker in tickers:
        snapshot, _freshness = provider.fundamentals(Ticker(ticker))
        shares = getattr(snapshot, "segment_revenue_share", None)
        out.append((ticker, max(shares.values()) if shares else None))
    return out


def screen() -> dict[str, Any]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    cap_max = float(config["market_cap_max_usd"])
    analyst_max = int(config["analyst_count_max"])
    tickers = [r["ticker"] for r in json.loads(BASKET.read_text(encoding="utf-8"))["rows"]]

    conn = sqlite3.connect(_ENGINE_C_DB)
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
    print("\n## D11 第五條（瓶頸業務占營收下限）的鑑別力——**這是它至今沒接進 filter 的理由**")
    bounds = bottleneck_share_upper_bounds()
    values = [v for _t, v in bounds if v is not None]
    print(f"分部資料 {len(values)}／{len(bounds)} 檔｜用『最大分部占比』當上界（真值一定 ≤ 它）")
    for threshold in (0.2, 0.3, 0.4, 0.5, 0.6):
        blocked = sum(1 for v in values if v < threshold)
        note = "　← 恆滅，零鑑別力" if blocked <= 2 else ""
        print(f"  門檻 {threshold:.0%} → 確定不合格 {blocked}／{len(values)} 檔{note}")
    print("⚠ 上界高於門檻時**什麼都不能說**：TSM 的 HPC 分部 57.6% 裡矽光子晶粒只是極小一塊。")
    print("⚠ 這一條缺的不是對應表，是**「瓶頸業務的營收」這個數字本身**——大部分公司不揭露。")
    print("\n⚠ 市值與覆蓋家數兩條**已於 2026-09-19 接進 `webapp/basket.py` 的 filter**；"
          "本檔仍是它們的量測與重構驗證基準。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
