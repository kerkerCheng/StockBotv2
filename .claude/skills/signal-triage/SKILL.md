---
name: signal-triage
description: >
  Stage 2 判斷層：決定一則從 web search 或 Engine B（如 aleabitoreddit）harvest 到的
  原始材料，值不值得進 pq1（source-trace＋抽取）。由 daily／weekly routine 在 harvest
  之後自動呼叫；設計上刻意寬鬆，PASS 後可自動研究，但不等於入圖核准。
  觸發詞：本 skill 由 routine 自動呼叫，不是使用者直接觸發的入口。
---

# Generated cross-agent adapter

Read `../../../skills/signal-triage/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
