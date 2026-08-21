---
name: system-decompose
description: >
  由上而下拆解一個真實系統（NVIDIA 機櫃、TPU pod、humanoid），從一手規格列出它必須有哪些層、
  哪一層會先卡住，最後才對照圖譜找出「我們從來不知道的層」。當使用者說「拆解 XXX」
  「decompose XXX」「XXX 的 stack 有哪些層」「我們還漏了什麼瓶頸」「由上而下看一次」時使用。
  **這是系統裡唯一能產出「圖裡根本沒這個節點」的機制**——排序與覆蓋掃描都只能從既有節點
  往回看。選哪個系統由使用者決定，不得由無人值守排程自行挑題。
  產出是研究地圖不是知識：不入圖、不提高 evidence tier、不建 pq2 編號。
  觸發詞：拆解、decompose、stack 有哪些層、還漏了什麼、由上而下。
---

# Generated cross-agent adapter

Read `../../../skills/system-decompose/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
