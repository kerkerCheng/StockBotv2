"""⚠ 已搬到 `portfolio/policy.py`（2026-09-03，Phase 3）。

**理由：** beta policy 與目標配置是 Portfolio 的事；`engine_c.technical` 也要讀它，留在 Engine D 形成相依環。

module aliasing shim——兩個路徑是同一個模組物件，公開與私有名稱皆一致。
"""
import sys as _sys

from portfolio import policy as _impl

_sys.modules[__name__] = _impl
