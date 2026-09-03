"""⚠ 已搬到 `decision_lab/public_view.py`（2026-09-03，Phase 3b）。

**理由：** 它產生的是 **Engine D 自己的 redacted public DTO**——把 `today` 的輸出
過一次 `assert_safe_payload`。那是 Engine D 的呈現契約，不是 MCP transport；
`engine_b/todo.py`（pq2 待辦池）也直接消費它。

module aliasing shim——兩個路徑是同一個模組物件。
"""
import sys as _sys

from decision_lab import public_view as _impl

_sys.modules[__name__] = _impl
