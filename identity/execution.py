"""Research ticker 與 live execution symbol 的中立別名——**派生自名冊**（`config/company_identity.json` 的 `execution_symbol`）。

⚠ 2026-10-01（Phase 4 Step 4.1d）之前，`{"SIVE.ST": "FRA:2DG"}` 寫死在本檔，另有 `fetchers/gsheets.py` 的
enrichment 表替 Sheet 列注入 `neo4j_id`——同一個身分事實住三個地方（L16）。現在執行代號是名冊的一欄，
本檔只派生；`get_execution_aliases()` 的**名稱與 `{research_ticker: execution_symbol}` 形狀不變**——凍結區的
持股 adapter（舊 Decision Store 那一側）與 `shared.identity_resolution.resolve_identity` 都吃這個形狀。
"""
from __future__ import annotations

from identity.registry import get_registry

#: **行情供應商（Yahoo）語法表，不是 identity。** 執行代號 `FRA:2DG` 是使用者與券商看到的寫法；
#: Yahoo 對同一檔要 `2DG.F`。它回答「去哪裡抓價」，不回答「這是哪家公司」，所以刻意不搬進名冊
#: （plan 2026-10-01-001 §0.3：`yfinance_symbol` 要不要進名冊留待決）。
_YFINANCE_SYMBOL_ALIASES: dict[str, str] = {
    "FRA:2DG": "2DG.F",
}


def get_execution_aliases() -> dict[str, str]:
    """`{research_ticker: execution_symbol}`，回傳 copy（consumer 改不到名冊）。唯一來源：名冊的 `execution_symbol`。"""

    return dict(get_registry().execution_aliases())


def yfinance_symbol(symbol: str) -> str:
    """Map a canonical execution symbol to Yahoo's provider-specific syntax."""

    normalized = symbol.strip().upper()
    return _YFINANCE_SYMBOL_ALIASES.get(normalized, normalized)
