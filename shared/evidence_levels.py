"""證據充分度的三階序數——**唯一定義**。

## 為什麼在 shared

兩個分屬不同層的消費端用同一組值：

- `decision_lab/sizing.py` 的舊五軸 gate（`_validate_assessment` 用它比較宣告等級
  與實質等級，`weakest_axis_of` 用它排序）＝Engine D 的 permission。
- `alpha/levels.py` 的序數→分數換算（`legacy_axes` 讀 268 筆歷史 payload 時要能
  無歧義解析）＝Alpha 的研究語彙。

⚠ **2026-09-04 之前這兩邊各存一份 tuple**，靠 `alpha/levels.py` 的一句註解
（「與 `decision_lab/sizing.py::LEVELS` 逐字相同——這是刻意的」）維持同步，
而**沒有任何測試守它**。這正是 L16 第 3 點：字彙一旦有行為後果就必須被強制。
真的漂了會怎樣？`convert_axis_results` 對歷史 payload 靜默誤轉——不報錯，
只是排序悄悄變了。

兩邊都不能 import 對方（`alpha` 不得依賴 Engine D，Engine D 不得依賴 `alpha`），
所以唯一的家是這裡。`tests/test_weakest_axis.py` 用 `is` 而不是 `==` 斷言同一個
物件——那才證明是同一份，不是又抄了一次。
"""
from __future__ import annotations

from typing import Final

__all__ = ["LEVELS"]

#: 三階序數，由弱到強。次序本身有意義（`LEVELS.index()` 是排序鍵），
#: 所以這是 **contract 不是 taxonomy**——新增一階要同時決定它在兩邊的行為，
#: 不是「加一列設定就好」。
LEVELS: Final[tuple[str, ...]] = ("unknown", "bounded_hypothesis", "corroborated")
