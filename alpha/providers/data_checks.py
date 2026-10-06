"""資料檢查的取數（Phase 7 Step 7.0g-1；plan A4）：營收量級。

比的是**同一家公司的兩個獨立量級**：個股頁印的近四季營收（快照 `revenue_ttm`＋貼上的幣別標籤）對基期觀測的年營收。
**標籤用 builder 同一個函式**（`alpha.contracts.reporting_currency_for`）——這個檢查要驗的就是那張標籤（failure log #23：
UMC 的新台幣快照被貼上 20-F 的美元標籤，印成「2,507 億 USD」）。

- **只在 materialize 呼叫**：換匯要打外部（`alpha/providers/market_normalization.py` 的理由），closure-gate 每輪都跑，不能放那裡。
- 判定（帶子、命中、覆蓋）住 `alpha/closure.py`；本檔只取數，比不了的寫 `missing` 理由——跳過不得安靜（INV-3）。
- 為什麼不併進 `alpha.providers.candidates.load_board`：那支被大量測試以假資料呼叫，這一項要讀真的 Engine C 與 FX。
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


def revenue_magnitude_pairs(
    tickers: Sequence[str], *,
    provider: Any = None,
    to_usd: Callable[[float, str, dict[str, float | None]], float | None] | None = None,
    fx_cache: dict[str, float | None] | None = None,
) -> dict[str, dict[str, Any]]:
    """`{ticker: {printed_value, printed_currency, printed_usd, base_value, base_currency, base_usd, missing}}`。

    `provider`／`to_usd`：測試的縫；預設 `EngineCFundamentalsProvider` 與 `market_normalization.to_usd`。
    `fx_cache`：同一輪同一個幣別只換一次匯（由呼叫端持有）。
    """
    from alpha.contracts import Ticker, reporting_currency_for

    if provider is None:
        from alpha.providers.fundamentals import EngineCFundamentalsProvider

        provider = EngineCFundamentalsProvider()
    if to_usd is None:
        from alpha.providers.market_normalization import to_usd as _to_usd

        to_usd = _to_usd
    cache: dict[str, float | None] = fx_cache if fx_cache is not None else {}
    out: dict[str, dict[str, Any]] = {}
    for raw in tickers:
        ticker = str(raw)
        row: dict[str, Any] = {"printed_value": None, "printed_currency": None, "printed_usd": None,
                               "base_value": None, "base_currency": None, "base_usd": None, "missing": None}
        try:
            snap, _fresh = provider.fundamentals(Ticker(ticker))
            actuals, reason = provider.fiscal_year_results(Ticker(ticker))
        except Exception as exc:  # noqa: BLE001 — 一檔讀不到不該讓整輪掛掉；理由照寫
            row["missing"] = f"讀不到（{type(exc).__name__}）"
            out[ticker] = row
            continue
        value = getattr(snap, "revenue_ttm", None)
        label = reporting_currency_for(snap, actuals)
        row.update(printed_value=value, printed_currency=label)
        missing: list[str] = []
        if value is None:
            missing.append("快照沒有近四季營收")
        if not label:
            missing.append("標籤答不出幣別")
        if actuals is None:
            text = str(reason or "")
            # 「Engine C 無這檔的 fiscal_year_results 觀測」是常態（沒寫基期）；其餘照抄第一句——那是要人去修的資料（L12）
            missing.append("沒有生效基期觀測" if (not text or "fiscal_year_results 觀測" in text)
                           else text.split("：")[0].split("。")[0][:90])
        else:
            row.update(base_value=getattr(actuals, "revenue", None), base_currency=getattr(actuals, "currency", None))
            if row["base_value"] is None or not row["base_currency"]:
                missing.append("基期沒有年營收或幣別")
        if not missing:
            row["printed_usd"] = to_usd(float(value), str(label), cache)
            row["base_usd"] = to_usd(float(row["base_value"]), str(row["base_currency"]), cache)
            if row["printed_usd"] is None:
                missing.append(f"缺匯率 {label}/USD")
            if row["base_usd"] is None:
                missing.append(f"缺匯率 {row['base_currency']}/USD")
        row["missing"] = "；".join(missing) or None
        out[ticker] = row
    return out


__all__ = ["revenue_magnitude_pairs"]
