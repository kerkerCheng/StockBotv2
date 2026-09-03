"""⚠ 已搬到 `shared/capital_authority.py`（2026-09-03，Phase 3）。

**理由：** 它是 authority 的**讀取器**，不是 authority 的**擁有者**——
cash floor 與貸款額度的真相在私人 Google Sheet，這支只是把它讀成正規化 view。

而它有**兩個不同層的消費端**：`portfolio/allocation.py`（算可部署現金）與
Engine D（資本許可）。留在 Engine D 會讓 Portfolio 為了讀現金下限而 import
資本許可層，形成 `decision_lab ↔ portfolio` 相依環。

⚠ **語意一個字未變**：日常 credential scope 仍只有 `spreadsheets.readonly`；
未動用額度不算 NAV／cash／allocation；每次提款仍是 explicit manual review。

module aliasing shim——兩個路徑是同一個模組物件。
"""
import sys as _sys

from shared import capital_authority as _impl

_sys.modules[__name__] = _impl
