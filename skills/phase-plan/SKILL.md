---
name: phase-plan
description: >
  為下一個 Phase 寫 plan 的入口（預期由 fable 與使用者一起）。當使用者說「/phase-plan」「寫下一個 plan」
  「Phase N 的 plan」「plan 下一個 Phase」時使用。先把要使用者決定的判斷點列出來問，定案後照 Phase 0 plan 的骨架
  寫 plan、登記對照表、commit、push，最後印一行「切便宜模型，/phase-run」。不實作、不動 code。
  觸發詞：phase-plan、寫 plan、下一個 Phase、plan Phase。
---

# Phase Plan — 跟使用者一起寫下一個 Phase 的 plan

**一句話：先 brainstorm 判斷點，再寫 plan；plan 裡是判斷，所以由強模型與使用者一起做。**

## 步驟

1. 讀 [`docs/plans/README.md`](../../docs/plans/README.md) 對照表，找**第一個「尚無」plan 的 Phase N**。
   若仍有 `active` 的 plan 未 completed → 停，說明「先 `/phase-run` 把它做完」。
2. 讀（順序）：`docs/ROADMAP.md` Phase N 那一列與相關節；決定紀錄
   `docs/brainstorms/2026-09-22-graph-first-direction-decision.md`；上一個 Phase 的 closeout 報告（`docs/reports/`）
   與它列的「下一 Phase 要決定的問題」；`docs/brainstorms/README.md` 標「設計來源仍有效」的檔，若本 Phase 擴充它們就讀。
3. **先 brainstorm，不先寫。** 把要使用者決定的判斷點列成一張清單，每點三行：選項、我的建議、理由一句。**一次問完，等答案。**
   ROADMAP 已定義到可直接執行的不問（那是思考紀律不是核准請求）。
4. 定案後寫 `docs/plans/<日期>-<序號>-<type>-phase<N>-<slug>-plan.md`，骨架照
   [`2026-09-22-001-refactor-phase0-retire-plan.md`](../../docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md)：
   frontmatter（`status: active`）、§0.5 核准狀態＋進度表＋開工指令、不可越線、Steps（改哪裡／怎麼改／怎麼驗）、
   驗收數的是哪一層（只准圖／讀圖／敘事／registry／追蹤表）、每批的 L11-6 第④問、已知陷阱、結案 R2 的 `WORK_REQUEST`、結案後停。
5. 登記到 `docs/plans/README.md` 對照表（`active`）；plan 需要改 ROADMAP 的 Phase 定義走五欄 amendment，不偷改。commit、push。
6. 收尾只印一行：「plan 寫好了。切便宜模型，貼 `/phase-run`。」

## 不做

- 不實作、不動 code、不跑 plan。
- 不改 `AGENTS.md` 判準句（要改先給五欄，等使用者）。
- 不替使用者決定判斷點；也不把已定義好的事拿來問。
