"""⚠ 已搬到 `intake/actions.py`（2026-09-03，Phase 3b）。

**理由：** Research Action 的 domain（bounded mutation／content digest／immutable review packet／state machine）不是 MCP transport；本機 pq2 待辦池與 weekly digest 都直接消費它。

module aliasing shim——兩個路徑是同一個模組物件。
"""
import sys as _sys

from intake import actions as _impl

_sys.modules[__name__] = _impl
