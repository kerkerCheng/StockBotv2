# docs/brainstorms — 讀哪些、不讀哪些（2026-09-22 起）

> **規則：新 session 只讀「現行」與「設計來源」兩類；「已封存」的不要讀。** 每個已封存檔的開頭都有同樣的 banner，
> 直接打開也擋得住。本表是分類的 SSOT；新增 brainstorm 檔時在這裡登記一列（L16：分類要跟著資料走）。
> 分類判準：這份檔的決定是否已被更新的決定紀錄整併或取代？是 → 已封存；它是否仍是某個現行機制的設計來源？是 → 設計來源。

## 現行

| 檔 | 用途 |
|---|---|
| [`2026-09-22-graph-first-direction-decision.md`](2026-09-22-graph-first-direction-decision.md) | 方向決定紀錄 G1–G12；AGENTS.md、development-flow、ROADMAP、實作 plan 全部從它導出 |

## 設計來源仍有效（實作前要讀；衝突時以決定紀錄為準）

| 檔 | 為什麼還要讀 |
|---|---|
| [`2026-09-17-structural-reading-layer.md`](2026-09-17-structural-reading-layer.md) | G5 擴充它（加插槽讀圖 kind）；實作前要讀 |
| [`2026-09-18-verbatim-never-reaches-the-decision.md`](2026-09-18-verbatim-never-reaches-the-decision.md) | L18 的量測與架構；走圖與讀圖必須消費逐字 |
| [`2026-08-31-event-watch-module-requirements.md`](2026-08-31-event-watch-module-requirements.md) | G7 擴充它（加語意條件 kind）；實作前要讀 |

## 歷史證據（只在引用實測數字時讀）

| 檔 | 內容 |
|---|---|
| [`2026-07-31-leverage-glide-path-requirements.md`](2026-07-31-leverage-glide-path-requirements.md) | beta 訊號三次實測的完整證據；只在引用那些數字時讀 |

## 已封存（不要再讀；只為歷史稽核保留）

| 檔 | 為什麼不用再讀 |
|---|---|
| [`2026-09-21-graph-consumption-vs-ranking.md`](2026-09-21-graph-consumption-vs-ranking.md) | 待否證素材；採納的部分已整併進決定紀錄，未採納的不再追 |
| [`2026-09-16-alpha-edge-new-session-prompt.md`](2026-09-16-alpha-edge-new-session-prompt.md) | 舊路線的啟動 prompt；新啟動 prompt 由重建後的 ROADMAP 導出 |
| [`2026-09-16-alpha-edge-phase1-plan.md`](2026-09-16-alpha-edge-phase1-plan.md) | Phase 1 已結案，且其驗收行（排序出現台股）正是 G1 退役的對象 |
| [`2026-09-17-alpha-edge-phase2-plan.md`](2026-09-17-alpha-edge-phase2-plan.md) | Phase 2 已結案；心跳三層規格已抄進 AGENTS／ARCHITECTURE |
| [`2026-09-17-alpha-edge-phase3-plan.md`](2026-09-17-alpha-edge-phase3-plan.md) | Phase 3 已結案 |
| [`2026-09-17-no-evidence-case-zoom-out.md`](2026-09-17-no-evidence-case-zoom-out.md) | 方案建立在估值層之上；G3 停跑估值後失效。Abstention 紀錄本身仍在 ledger |
| [`2026-09-16-alpha-edge-discovery-requirements.md`](2026-09-16-alpha-edge-discovery-requirements.md) | D0–D15 中仍有效的（不給尺寸、realized 只提醒、覆蓋厚薄、beta 凍結、Daily 三層、Sheet 部位真相、power-law 統計量、X 帳號計分表）已抄進 AGENTS.md；被取代的（D8 補三格讓籃子非空、排序相關）由 G1／G6 取代。讀 AGENTS.md 即可 |
| [`2026-08-31-industry-sector-ranking-requirements.md`](2026-08-31-industry-sector-ranking-requirements.md) | 排序分產業組；G1 退役排序 |
| [`2026-08-21-research-attention-allocation-requirements.md`](2026-08-21-research-attention-allocation-requirements.md) | 注意力分配改由圖報洞＋lead 並行（G2）；decompose 入口的 SSOT 是 skills/system-decompose |
| [`2026-08-18-alpha-live-user-sized-requirements.md`](2026-08-18-alpha-live-user-sized-requirements.md) | §8 是 rank_bottlenecks 的設計依據（G1 退役）；「不給尺寸」已在 AGENTS.md |
| [`2026-08-13-capital-expression-direction-requirements.md`](2026-08-13-capital-expression-direction-requirements.md) | 資本表達層已於 2026-08-28 整組移除 |
| [`2026-08-02-confidence-axes-restructure-requirements.md`](2026-08-02-confidence-axes-restructure-requirements.md) | 五軸重構在「明確不排程」清單 |
| [`2026-07-26-next-phase-operating-model-requirements.md`](2026-07-26-next-phase-operating-model-requirements.md) | 舊 operating model；現行分工住 ARCHITECTURE／OPERATIONS |
| [`2026-07-26-alpha-beta-sleeve-workflow-requirements.md`](2026-07-26-alpha-beta-sleeve-workflow-requirements.md) | beta 開發凍結；sleeve 規則已在 AGENTS.md 資本與風控 |
| [`2026-07-13-source-trace-upgrade-requirements.md`](2026-07-13-source-trace-upgrade-requirements.md) | SSOT 是 skills/source-trace/SKILL.md |
| [`2026-08-31-unverified-screenshot-leads-requirements.md`](2026-08-31-unverified-screenshot-leads-requirements.md) | 已實作；SSOT 是 OPERATIONS「截圖假設層」 |
