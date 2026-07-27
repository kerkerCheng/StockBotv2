"""Research ticker 與 live execution symbol 的中立別名 registry。"""
from __future__ import annotations


_EXECUTION_ALIASES: dict[str, str] = {
    "SIVE.ST": "FRA:2DG",
}

# Portfolio/execution symbols are stable user-facing identifiers. Market-data
# vendors can require a different syntax for the same venue and security.
_YFINANCE_SYMBOL_ALIASES: dict[str, str] = {
    "FRA:2DG": "2DG.F",
}


def get_execution_aliases() -> dict[str, str]:
    """回傳 copy，避免 consumer 改寫 execution alias authority。"""

    return dict(_EXECUTION_ALIASES)


def yfinance_symbol(symbol: str) -> str:
    """Map a canonical execution symbol to Yahoo's provider-specific syntax."""

    normalized = symbol.strip().upper()
    return _YFINANCE_SYMBOL_ALIASES.get(normalized, normalized)
