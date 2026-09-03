"""⚠ 已搬到 `intake/publish.py`（2026-09-03，Phase 3b）。

**理由：** local-only Git 發布——原 docstring 就自陳「intentionally **not** imported by the remote MCP tool surface」。

module aliasing shim——兩個路徑是同一個模組物件。
"""
import sys as _sys

from intake import publish as _impl

_sys.modules[__name__] = _impl
