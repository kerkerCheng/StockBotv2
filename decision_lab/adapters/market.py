"""⚠ 已搬到 `shared/market_normalization.py`（2026-09-03，Phase 3）。

**理由：** 外部行情／FX payload 的 fail-closed 正規化是**跨層的資料邊界**，
不是 Engine D 的判斷。`shared/capital_authority.py` 也要用它換算貸款幣別，
留在 Engine D 會讓 `shared → decision_lab` 形成環。

⚠ **F-02 的防線一個字未改**：報價單位 ≠ 結算幣別；`GBp` 與 `GBP` 大小寫敏感；
未登記且非 ISO 形式一律 fail closed。

module aliasing shim——兩個路徑是同一個模組物件。
"""
import sys as _sys

from shared import market_normalization as _impl

_sys.modules[__name__] = _impl
