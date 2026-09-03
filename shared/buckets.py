"""Google Sheet `bucket` 欄位的現金判定——**跨層共用的中立字彙**。

原本住在 `engine_d_runtime/adapters.py`，於是 `portfolio/exposure.py` 為了判斷
「哪一列是現金」必須 import 整個 Engine D runtime——那是 `decision_lab ↔
engine_d_runtime` 相依環的來源之一。

⚠ 語意（`AGENTS.md`「曝險邊界」）：**`bucket=CASH` 計入 NAV 但不計曝險。**
這是一個字彙判定，不是政策——政策數值（cap、warning）仍在 `config/*.json`。
"""
from __future__ import annotations

CASH_BUCKET_LABELS: frozenset[str] = frozenset({"cash", "現金"})
