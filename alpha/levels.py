"""序數等級與分數的唯一換算表。

## 為什麼要獨立成一個模組

新舊兩套軸都用「三階序數」表達證據充分度（`unknown` / `bounded_hypothesis` /
`corroborated`），而新的 `Score` 用 0..1 的浮點數。**換算表只能有一份**——
散在轉換器、模型與測試裡就會漂移（L16：分類有 SSOT 時要讓它跟著資料走）。

## ⚠ 這些浮點數是**序數佔位值，不是量測結果**

`0.0 / 0.5 / 0.85` 只保證**次序正確**，不保證「corroborated 的信心是
bounded_hypothesis 的 1.7 倍」。它們存在的唯一理由是新契約用連續值表達分數。

依 L14：**任何依賴這些數值大小（而非次序）的機制，上線前必須先被量測。**
目前唯一的消費者是 `ordering_key()` 的字典序比較——那只用到次序，所以安全。
若日後有人拿它們做加權、內插或期望值計算，那是一個新機制，要先過 L14。
"""
from __future__ import annotations

from typing import Final

from .errors import ContractViolation

#: 三階序數，由弱到強。與 `decision_lab/sizing.py::LEVELS` 逐字相同——
#: 這是刻意的：轉換器要能無歧義地讀舊 payload。
LEVELS: Final[tuple[str, ...]] = ("unknown", "bounded_hypothesis", "corroborated")

#: 序數 → 分數。**版本化**：改動它就是改動排序，必須答出「幾筆排序會變」。
LEVEL_SCALE_VERSION: Final[str] = "ordinal-v1"

_LEVEL_TO_SCORE: Final[dict[str, float | None]] = {
    "unknown": None,            # ⚠ None＝不知道，**不是 0.0**
    "bounded_hypothesis": 0.5,
    "corroborated": 0.85,
}

#: `unknown` 當成**上限**時的值。與上面不同：作為分數它是 `None`（不知道），
#: 作為上限它是 `0.0`（什麼都撐不住）。**同一個等級在兩種用途下語意不同**，
#: 所以用兩張表而不是一張——這正是 L12（一表兩義）的預防性應用。
_LEVEL_TO_CEILING: Final[dict[str, float]] = {
    "unknown": 0.0,
    "bounded_hypothesis": 0.5,
    "corroborated": 0.85,
}


def level_to_score(level: str) -> float | None:
    """序數 → 分數。`unknown` 回 `None`（不知道），不是 0。"""
    if level not in _LEVEL_TO_SCORE:
        raise ContractViolation(f"未登記的等級：{level!r}；已知 {LEVELS}")
    return _LEVEL_TO_SCORE[level]


def level_to_ceiling(level: str) -> float:
    """序數 → 上限。`unknown` 回 `0.0`（這組證據什麼都撐不住）。"""
    if level not in _LEVEL_TO_CEILING:
        raise ContractViolation(f"未登記的等級：{level!r}；已知 {LEVELS}")
    return _LEVEL_TO_CEILING[level]


def level_rank(level: str) -> int:
    """序數的位置。未登記一律視為最弱——寧可多提醒，也不要讓拼錯看起來很強。"""
    return LEVELS.index(level) if level in LEVELS else -1
