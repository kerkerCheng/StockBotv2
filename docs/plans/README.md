# Plans 索引

> **當前工作起點不在這裡。** 進行中的優先序看 [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表。
> 本檔只是歷史 plan 的狀態總表，方便判斷哪份還活著、哪份已被取代或完成。

每份 plan 的 frontmatter 帶 `status`；狀態語意：

- `active` — 尚未完成、仍是有效工作依據。
- `completed` — 產出已落地，僅留作歷史紀錄。
- `superseded` — 被後續 plan 取代（見該檔 `superseded_by`），不要再依它開工。

## 每個 Phase 開工前要有一份 plan（2026-09-22 起）

**分工：便宜模型執行 plan；plan 由強模型（fable）與使用者一起寫。** 執行者跑到 Phase 結案、R2 GO 之後，
若下一個 Phase 在下表沒有 plan 檔，就停在 `AWAITING_HUMAN`，HUMAN SUMMARY 的「下一步」印出下面這段指令，
並在 closeout 報告附「本 Phase 執行中發現、下一 Phase 要決定的問題清單」。使用者切到 fable 開新 session 貼 **`/phase-plan`**（skill 會照下面這段做；不能用 skill 時貼這段原文）：

```
讀 docs/ROADMAP.md 的 Phase <N> 那一列、docs/brainstorms/2026-09-22-graph-first-direction-decision.md、
上一個 Phase 的 closeout 報告（docs/reports/）與它列的待決問題。先 brainstorm：把要我決定的判斷點列出來問我，
不要先寫。定案後照 docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md 的骨架
（核准狀態與進度表、不可越線、Steps 各附改哪裡／怎麼驗、驗收數的是哪一層、已知陷阱、結案 R2 的 WORK_REQUEST）
寫 docs/plans/<日期>-<序號>-<type>-phase<N>-<slug>-plan.md，登記到本檔對照表，commit、push。
```

| Phase | plan 檔 | 狀態 |
|---|---|---|
| 0 拆 | [2026-09-22-001](2026-09-22-001-refactor-phase0-retire-plan.md) | completed（2026-09-23；closeout `docs/reports/2026-09-23-phase0-closeout.md`） |
| 1 等待與心跳 | [2026-09-24-001](2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md) | completed（2026-09-25；closeout `docs/reports/2026-09-25-phase1-closeout.md`；R2 GO） |
| 2 讀圖兩種單位加走圖 | [2026-09-25-001](2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md) | completed（2026-09-26；closeout `docs/reports/2026-09-26-phase2-closeout.md`；R2 GO） |
| 3 候選狀態加三題 | [2026-09-26-001](2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md) | active |
| 4 層中心來源 | 尚無 | — |
| 5 量測 | 尚無 | — |

---

| Plan | 主題 | 狀態 |
|------|------|------|
| [001 (2026-06-07)](2026-06-07-001-feat-cpo-vertical-slice-plan.md) | CPO 垂直切片 — 基礎建設 + extract 管線 | completed |
| [002 (2026-06-26)](2026-06-26-002-feat-cpo-vertical-slice-thesis-plan.md) | CPO 垂直切片 v1 — 多文件擴張 + thesis 生成 | completed |
| [003 (2026-06-27)](2026-06-27-003-feat-env-bootstrap-plan.md) | 環境重建 bootstrap | completed |
| [004 (2026-07-08)](2026-07-08-004-feat-investment-query-gap-audit-plan.md) | 投資查詢能力缺口審查 | superseded → 006 |
| [005 (2026-07-08)](2026-07-08-005-feat-second-vertical-slice-plan.md) | 第二條垂直切片 — 工業半導體設備（AMAT/LRCX） | completed |
| [006 (2026-07-10)](2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md) | Personal Investment Advisor 全 roadmap | superseded → 008 |
| [007a (2026-07-14)](2026-07-14-007-feat-source-trace-upgrade-plan.md) | Source Trace Manual 三入口追源 | superseded → 008 |
| [007b (2026-07-14)](2026-07-14-007-feat-remote-intake-provenance-plan.md) | 遠端入圖 provenance 帳本 | superseded → 008 |
| [008 (2026-07-15)](2026-07-15-008-feat-unified-workplan-plan.md) | 統一工作計畫 — Engine A 品質優先（Phase I–III） | completed（U13 遠端 finalize 由 mobile plan 取代） |
| [mobile (2026-07-16)](2026-07-16-001-feat-mobile-research-action-launch-plan.md) | Mobile Research Action 兩段式協定 | completed |
| [Decision Lab (2026-07-21)](2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md) | Engine D／Action-Oriented Alpha Decision Lab v1 | completed |
| [Engine D workflow (2026-07-22)](2026-07-22-001-feat-engine-d-operational-workflow-plan.md) | Raw Signal → Action Card／today brief operational workflow | completed |
| [Daily Approval Loop (2026-07-22)](2026-07-22-002-feat-daily-approval-loop-plan.md) | 每日 harvest／triage／brief／封閉動詞核准迴路（U1–U5） | completed（2026-07-26 由本機 v1.2 rollout 接手） |
| [Daily Approval Loop v1.1 (2026-07-24)](2026-07-24-001-feat-daily-approval-loop-v1-1-plan.md) | 優先研究佇列、可續跑 drain、閉環 evidence-delta、對話式批次核准、MCP leads 同步 | completed（2026-07-26 已建 Codex local daily scheduled task） |
| [Daily Beta Technical Monitor (2026-07-28)](2026-07-28-001-feat-daily-beta-technical-monitor-plan.md) | 固定持倉 universe 的日線 technical observation、beta safe contribution monitor 與 Daily 整合 | completed |
| [Household Capital Authority Phase II-A (2026-07-28)](2026-07-28-002-feat-household-capital-authority-plan.md) | 私人 Capital Authority 唯讀 adapter、point-in-time capital view 與 Daily 四欄輸出 | completed |
| [Portfolio Risk Policy Redesign (2026-07-29)](2026-07-29-001-refactor-portfolio-risk-policy-plan.md) | 只保留 ETF 槓桿／單筆 hard block、known issuer 穿透、drawn debt 與低雜訊事件監控 | completed |
| [Serenity 30-Day Research Campaign (2026-07-29)](2026-07-29-002-feat-serenity-30d-research-campaign-plan.md) | 30 天 X 分頁回補、圖片快取、scoped exploration triage 與 robotics 一手追源 | completed |
| [Phase 0 拆：退役估值鏈、排序驅動、decision_lab 研究側 (2026-09-22)](2026-09-22-001-refactor-phase0-retire-plan.md) | 給便宜模型的完整執行 plan：0a 停跑、0b 四批刪除（先斷 import 再刪）、0c 池子；驗收＝殭屍 grep 差集歸零、Decision Store sha256 不變 | completed（2026-09-23） |
| [Phase 1 等待與心跳 (2026-09-24)](2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md) | 一個 Windows daily（LLM 以 Claude CLI 零工具做 triage 與語意預篩、weekly 退役）、`semantic_condition` watch、反證登記 hook 與補登記、到期轉 pq2 `watch_decision`、心跳改版；驗收＝watch registry 的筆數與狀態 | completed（2026-09-25；closeout `docs/reports/2026-09-25-phase1-closeout.md`；R2 GO） |
| [Phase 2 讀圖兩種單位加走圖 (2026-09-25)](2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md) | Graph MCP 退役；反向路徑只收競爭關係；讀圖 v3（`unit` 層／插槽、兩半逐字引用由程式核對、反證出處）；插槽視角；強模型寫第一份插槽讀圖；走圖九型問句與 `graph_holes`、`graph_walk` kind；讀圖頁與個股頁讀圖面板；pq1 拿掉結構排序殘留；Phase 1 三個小修；驗收＝讀圖 ledger、走圖命中／母體、state kind | completed（2026-09-26；closeout `docs/reports/2026-09-26-phase2-closeout.md`；R2 GO） |
| [Phase 3 候選狀態加三題 (2026-09-26)](2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md) | 短評 v2（七格改題、`rides[]`／`disproof[]` 自動登記／`answers`／`candidate_state` 與「可開」前提驗證）；三題稽核區（Engine C 機械歷史回填、EV/S 或 P/S 自家三年百分位、主題等權組、going concern 結構化欄位）；候選狀態板 `candidates` kind 與心跳計數；個股頁首屏／稽核區／readiness 核心換；`record_trade.py` 收據；強模型寫四份 v2 敘事；驗收＝敘事 ledger、watch 連結、三題每檔有值或缺席 kind、收據 | active |

**目前 active plan：Phase 3（[2026-09-26-001](2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md)）——貼 `/phase-run` 續工。** 以下為歷史狀態： Portfolio Risk Policy Redesign、Daily Beta Technical Monitor v1、Household Capital Authority Phase II-A 與 Daily Approval Loop v1.0/v1.1 程式面均完成；退休貸款政策維持約 30 年退休淨終值導向的 manual contract，不另開 Phase II-B engine。現行 v1.3 runbook 由 Codex desktop 本機排程執行（daily 台北 06:30；weekly 週日 04:00，兩者錯開）。L9 財務核驗缺口已補齊。
