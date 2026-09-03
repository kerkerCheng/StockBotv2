"""⚠ 已搬到 `alpha/ranking.py`（2026-09-03，Phase 3）。

**理由：** 瓶頸排序 → 股票清單是 Alpha Research 的呈現層，不是 Engine D 的職責。

module aliasing shim——兩個路徑是同一個模組物件，公開與私有名稱皆一致。
"""
import sys as _sys

from alpha import ranking as _impl

_sys.modules[__name__] = _impl
