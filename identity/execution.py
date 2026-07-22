"""Research ticker 與 live execution symbol 的中立別名 registry。"""
from __future__ import annotations


_EXECUTION_ALIASES: dict[str, str] = {
    "SIVE.ST": "FRA:2DG",
}


def get_execution_aliases() -> dict[str, str]:
    """回傳 copy，避免 consumer 改寫 execution alias authority。"""

    return dict(_EXECUTION_ALIASES)
