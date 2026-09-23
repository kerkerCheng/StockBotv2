"""Engine D — 舊 Decision Store 的**唯讀歷史檔案館**（frozen 2026-09-22，G12）。

研究側（signal intake → context → coverage → decision → action card → live choice）於
Phase 0 Step 0b.4 整組退役；剩下的只有：

- `store.py`：SQLite authority 的存取類別（append-only、私有、備份還原要用）。寫入方法無呼叫端。
- `coverage_queries.py`：`mode=ro` 的純讀查詢，供個股頁的 research 面板與 `scripts/catalyst_watch.py` 讀歷史
  catalyst／disproof／expiry。
- `cli.py`：`python -m decision_lab status`／`history` 兩個唯讀子命令。
- `bootstrap.py`、`models.py`、`schema.sql`、`adapters/holdings.py`：store 與備份還原的相依。

live 收據自 2026-09-22 起住 `library/trades/trade_log.jsonl`（`scripts/record_trade.py`），
資本硬擋住 `risk/hard_caps.py`。
"""

from .store import DecisionStore

__all__ = ["DecisionStore"]
