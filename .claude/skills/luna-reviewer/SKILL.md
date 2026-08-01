---
name: luna-reviewer
description: >-
  明確 opt-in 的 Luna 委派＋主代理 review 工作流。只在使用者明確輸入
  `$luna-reviewer ...`、`Luna reviewer：...`、`Luna reviewer: ...`，或清楚說
  「這次用 Luna reviewer」時使用；不得因任務看起來機械、便宜、適合平行化，
  或只提到 pq1、alpha、audit 而自動啟動。適用於 pq1 bounded drain、alpha 事實蒐集、
  repo／queue 盤點、測試與 log 分析等可逐項驗收的唯讀子任務。Luna 只交 review packet；
  主代理負責選樣、驗證、唯一寫入、人工 gate 與最終結論。
---

# Generated cross-agent adapter

Read `../../../skills/luna-reviewer/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
