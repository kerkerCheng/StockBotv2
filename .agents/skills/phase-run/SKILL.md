---
name: phase-run
description: >
  執行 active plan 的續工入口（預期由便宜模型執行）。當使用者說「/phase-run」「執行 plan」「續工」「接著做」
  「continue plan」時使用。它不是另一套流程：找到 docs/plans/README.md 對照表裡唯一 active 的 plan，
  從它進度表第一個未完成的 Step 接續，全程走 development-flow；沒有需要使用者核准的事就做到 Phase 結案，
  只有 AGENTS.md 的六條停止條件才停。不自建任何進度狀態，不開下一個 Phase。
  觸發詞：phase-run、執行 plan、續工、接著做、continue plan。
---

# Generated cross-agent adapter

Read `../../../skills/phase-run/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
