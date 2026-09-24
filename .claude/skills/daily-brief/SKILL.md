---
name: daily-brief
description: >
  互動 session 的每日核准迴路（2026-09-24 起**只在互動 session**；無人值守的每日訊息是 Windows daily
  的心跳）：讀當天 daily 的輸出與待辦池現值，把今日決策與到期 thesis 聚合成一份 action-first 的
  Daily Approval Brief，給 pq2 建議與批次指令。持久現況（結構／資產配置／研究缺口／在等什麼）自 2026-09-08
  起住 APP，Daily 只印較昨變動。使用者用一行批次語法
  （`1 3 7 go 4 drop 5 6 pending`）
  核准。當使用者說「daily brief」「今天有什麼要處理」「跑每日摘要」「有哪些待判斷」「今天需要
  動作嗎」時使用。三道閘門不放寬：graph admission 必經核准、深挖由 priority/使用者驅動但入圖仍
  核准、live 資本永遠人工。本 skill 不下單、不自動入圖。觸發詞：daily brief、
  每日摘要、今天有什麼、待判斷、今天需要動作嗎。
---

# Generated cross-agent adapter

Read `../../../skills/daily-brief/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
