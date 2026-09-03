"""⚠ 已搬到 `portfolio/exposure.py`（2026-09-03，Phase 3）。

**理由：** NAV 佔比呈現是 Portfolio 層；它原本 import `engine_d_runtime.adapters`，是 `decision_lab ↔ engine_d_runtime` 環的來源之一。

module aliasing shim——兩個路徑是同一個模組物件，公開與私有名稱皆一致。
"""
import sys as _sys

from portfolio import exposure as _impl

_sys.modules[__name__] = _impl
