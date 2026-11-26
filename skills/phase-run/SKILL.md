---
name: phase-run
description: >
  執行 active plan 的續工入口（預期由便宜模型執行）。當使用者說「/phase-run」「執行 plan」「續工」「接著做」
  「continue plan」時使用。它不是另一套流程：找到 docs/plans/README.md 對照表裡唯一 active 的 plan（或使用者指名的那一份），
  從它進度表第一個未完成的 Step 接續，全程走 development-flow；沒有需要使用者核准的事就做到 Phase 結案，
  只有 AGENTS.md 的六條停止條件才停。不自建任何進度狀態，不開下一個 Phase。
  觸發詞：phase-run、執行 plan、續工、接著做、continue plan。
---

# Phase Run — 執行 active plan

**一句話：找 active plan（或使用者指名的那一份），從第一個未 ✅ 的 Step 接著做，沒有要核准的事就做到結案。**
流程本體是 [`skills/development-flow/SKILL.md`](../development-flow/SKILL.md)，本 skill 只負責「從哪裡開始、到哪裡停」。

## 步驟

1. **使用者指名了 plan 檔**（`/phase-run docs/plans/<檔名>`）就做那一份——它在 [`docs/plans/README.md`](../../docs/plans/README.md)
   任一張表的狀態必須以 `active` 開頭，否則停下回報。（2026-11-26：Phase 7 是持續型，佔著「Phase ↔ plan」表唯一的 active；
   同時進行的開發 plan 登記在下面那張表、由使用者指名。）
   **沒指名**：讀「Phase ↔ plan」對照表，找 `status=active` 的 plan。**必須唯一。** 0 份 → 停，回一句「沒有 active plan，請切 fable 執行 `/phase-plan`」；
   2 份以上 → `AWAITING_HUMAN`。那一份若是持續型的研究 Phase，照它進度表的執行者欄——研究 Step 交回強模型。
2. 讀該 plan 全文（`AGENTS.md` 每個 session 本來就要先讀）。
3. 看 plan §0.5 進度表與 `git log --oneline -20`，找**第一個未 ✅ 的 Step**；已 ✅ 的不重做。
   進度表有「執行者」欄時，那個 Step 寫的不是自己（便宜模型遇到「強模型」）就停下交回，不跳過它去做後面的。
4. **單一 writer 確認：** plan 若要求暫停排程，且進度表還沒記「排程已暫停」，先問使用者一句「daily 排程暫停了嗎」，
   得到肯定後把它記進進度表；這是開工前唯一要問的話。
5. 從那個 Step 起走 development-flow：Z1 以上預設 R1；**Phase 結案、與執行期間 trigger 命中的 R2 已常規 opt-in**
   （`AGENTS.md`「協作與邊界」），能 spawn 就直接發 `WORK_REQUEST`，不能就把原文交回。
6. **沒有需要使用者決定的事就直接做下一個 Step**，Step 與 Phase 邊界一視同仁；只有六條停止條件才停。
   每個 Step 一個 commit（第一行寫 Step 編號）、更新進度表、GO 就 push（push 前 `git ls-files library/private` 應為空）。
7. 走到 plan 的「結案」節就照它停：標 ✅、登記 completed、印下一步指令，`AWAITING_HUMAN`。

## 不做

- 不自建進度狀態：進度只住 plan 的進度表與 git log（不建第二個狀態源）。
- 不開下一個 Phase：沒有 plan 就停。
- 不寫任何 authority、不動四個人工 gate、不放寬 plan 的「不可越線」。
- 不替使用者決定 plan 沒定義的事：撞到就 `SCOPE_ESCALATION` ＋ `AWAITING_HUMAN`。
