"""⚠ 已搬到 `risk/policy.py`（2026-09-03，Phase 3）。

**理由：** 它是**資本政策**（部位上限、槓桿 cap、覆蓋折扣），不是 research thesis。
留在 `thesis/` 會讓 Engine D 為了讀資本上限而 import research package，
形成 `decision_lab ↔ thesis` 相依環（實測 5 個 import 點）。

module aliasing shim——兩個路徑是同一個模組物件。
"""
import sys as _sys

from risk import policy as _impl

_sys.modules[__name__] = _impl
