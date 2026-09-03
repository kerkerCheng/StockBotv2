"""⚠ 已搬到 `intake/provenance.py`（2026-09-03，Phase 3b）。

**理由：** filesystem provenance 原語（canonical hash／atomic publish／no-clobber／storage permission）**與遠端完全無關**。

module aliasing shim——兩個路徑是同一個模組物件。
"""
import sys as _sys

from intake import provenance as _impl

_sys.modules[__name__] = _impl
