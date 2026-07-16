---
name: investment-research
description: >
  對知識圖譜（Neo4j）+ 財務資料（SQLite）提問，產出有根據的投資研究回答。
  當使用者問關於標的的瓶頸性、競爭地位、供應鏈位置、thesis 狀態、或說「評估XXX」、
  「分析XXX的競爭位置」、「XXX 在 CPO 供應鏈的地位」、「thesis 還成立嗎」、
  「建議買嗎」、「怎麼看XXX」、「幫我分析$TICKER」時，使用本 skill。
  研究 agent（Claude Code / Codex）是分析引擎；圖譜是跨 session 的持久記憶；本 skill 定義如何接取這份記憶並組成回答。
  觸發詞：評估、分析、怎麼看、建議、thesis、CPO、瓶頸、供應鏈、$TICKER。
---

# Generated cross-agent adapter

Read `../../../skills/investment-research/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
