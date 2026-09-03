"""⚠ 已搬到 `shared/blockers.py`（2026-09-03，Phase 3 B2）。

**理由：** blocker 字彙有跨層消費端——留在 Engine D 會形成 `engine_c → decision_lab` 相依環。

本檔是 **module aliasing shim**，不是複製：`decision_lab.blockers` 與
`shared.blockers` 是**同一個模組物件**，所以公開與私有名稱、`isinstance` 判定、
module-level 快取全部一致。用 `from ... import *` 會漏掉私有名稱而產生兩份行為
（實測：`tests/test_coverage_severity.py` 直接 import `_match` 就炸了）。
"""
import sys as _sys

from shared import blockers as _impl

_sys.modules[__name__] = _impl
