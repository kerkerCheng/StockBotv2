"""⚠ 已搬到 `portfolio/allocation.py`（2026-09-03，Phase 3）。

**理由：** 行情心跳、相對水位與 sleeve 配置差距是 Portfolio 層，不是資本許可層。

module aliasing shim——兩個路徑是同一個模組物件，公開與私有名稱皆一致。
"""
import sys as _sys

from portfolio import allocation as _impl

_sys.modules[__name__] = _impl
