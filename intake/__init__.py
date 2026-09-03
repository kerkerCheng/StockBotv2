"""Intake — 研究材料進入系統的 **application layer**。

**回答一句話：一份外部文件怎麼變成圖裡有 provenance 的事實？**

```
raw 文件 → extraction → prepare（驗證＋凍結成 immutable action）
        → **使用者核准 exact action ID ＋ digest**（四個人工 gate 之一）
        → apply（filesystem-first ＋ 逐文件 checkpoint ＋ 冪等重放）
        → publish（本機 Git，每 action 一 commit）
```

## 為什麼它是獨立的 package 而不是 `mcp_server/` 的一部分

實測（2026-09-03）：`mcp_server/` 4,016 行有 **79% 不是 MCP**。這些邏輯只是因為
第一個入口是遠端而住進 transport package，導致 5 個 core 消費端被迫 import 它。

**MCP 是 optional adapter**：`intake/` 完全不 import `mcp`，本機路徑
（`scripts/prepare_research_action.py`、`scripts/commit_pending_intake.py`、
weekly digest）直接呼叫這裡，不經過任何遠端協定。
"""
from __future__ import annotations
