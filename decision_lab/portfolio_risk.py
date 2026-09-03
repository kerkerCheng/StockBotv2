"""⚠ 已搬到 `risk/snapshot.py`（2026-09-03，Phase 3）。

**理由：** 槓桿倍數、issuer 曝險與門檻跨越是 Risk 層——它只套硬上限，不判斷好壞。

module aliasing shim——兩個路徑是同一個模組物件，公開與私有名稱皆一致。
"""
import sys as _sys

from risk import snapshot as _impl

_sys.modules[__name__] = _impl
