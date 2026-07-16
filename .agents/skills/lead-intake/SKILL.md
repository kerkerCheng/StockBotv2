---
name: lead-intake
description: >
  把一條「原料」(X 推文 / 產業報導 / 法說會 / 論文 / 小道消息)從進場到入庫的完整驗證 SOP。
  當使用者丟來一條推文、一則新聞、一份文件、或任何「我看到這個消息,該怎麼查證、該不該加進知識庫」
  的線索時,務必使用本 skill。它定義:拆原子 claim → 依源登記表跑獨立驗證 → 套用證據/獨立性/幻覺
  鐵律自動標記 → 分層決定入圖或 park → 接既有 extract/loader pipeline 入庫 → 產出 Directional
  Lane Memo。本 skill 是引擎B(線索)與引擎A(知識庫)之間的閘門,也是系統規模化「亂抓」後不被
  低品質資訊淹沒的護城河。觸發詞:驗證推文、查證消息、這條要不要入庫、餵給引擎A、跑 intake、線索處理。
---

# Generated cross-agent adapter

Read `../../../skills/lead-intake/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
