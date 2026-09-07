---
name: development-flow
description: >
  開發請求的統一入口：先做一次便宜的 scope triage（Zoom Level），再決定要多遠的 review
  （Review Level），最後以固定八欄的 STEP_RESULT 交回使用者。當使用者提出任何「改程式、
  改 config、改 schema、改呈現邏輯」的請求時使用——包含「我想做 X」「這裡壞了」「加一個
  功能」「重構 XXX」「這個能不能改成…」「zoom out」。它不是另一個 agent，預設由當前主
  agent 在既有 context 內完成，不 spawn。研究請求（改變「我知道什麼」）不走本 skill，
  走研究路徑：intake／source-trace／extraction 在 pq1，只有產生 exact authority mutation
  proposal 時才進 pq2 核准。觸發詞：我想做、幫我改、加一個、修一下、重構、zoom out、這個 Step、
  下一步要做什麼。
---

# Generated cross-agent adapter

Read `../../../skills/development-flow/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
