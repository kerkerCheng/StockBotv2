---
name: evidence-conflict-resolution
description: >
  審查 Engine A 同一 canonical edge 屬性的多份 EdgeAssertion 衝突，判斷時間／產品／客戶 scope、
  新證據是否 supersede 舊證據、或是否應移到 dated observation，並產生可由 deterministic resolver
  驗證的 resolution proposal。當使用者說「merge edge conflict」「解決 sole_source／substitutability／
  qualification／lead-time 衝突」「看 conflict queue」「這兩份證據怎麼合併」時使用。只處理投資研究
  圖譜的 evidence conflict，不處理 Git merge conflict；不得自行修改 resolution JSON 或 Neo4j。
---

# Generated cross-agent adapter

Read `../../../skills/evidence-conflict-resolution/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
