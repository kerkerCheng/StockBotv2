"""Intake — 研究材料進入系統的 **application layer**。

**回答一句話：一份外部文件怎麼變成圖裡有 provenance 的事實？**

```
raw 文件 → extraction → prepare（驗證＋凍結成 immutable action）
        → **使用者核准 exact action ID ＋ digest**（四個人工 gate 之一）
        → apply（filesystem-first ＋ 逐文件 checkpoint ＋ 冪等重放）
        → publish（本機 Git，每 action 一 commit）
```

## 為什麼它是獨立的 package

這些邏輯歷史上因為第一個入口是遠端 adapter 而住進 transport package，導致 5 個 core
消費端被迫 import 它（2026-09-03 抽出）。遠端 adapter 已於 2026-09-25 退役刪除
（ROADMAP 旁支「遠端入口退役」／Phase 2 Step 2.1）：本機路徑
（`scripts/prepare_research_action.py`、`scripts/commit_pending_intake.py`、
本機互動 session）直接呼叫這裡，不經過任何遠端協定。
"""
from __future__ import annotations
