---
title: Daily Approval Loop v1.1 — 優先研究佇列、閉環回饋與對話式核准
type: feat
date: 2026-07-24
topic: daily-approval-loop-v1-1
status: completed
completed: 2026-07-24
artifact_readiness: implementation-ready
product_contract_source: user-directed
planning_mode: direct
execution: code
supersedes_interface: 2026-07-22-002（沿用其 U1–U5 產物，改寫介面與研究管線）
---

# Daily Approval Loop v1.1 — 優先研究佇列、閉環回饋與對話式核准

## Goal Capsule

- **Objective:** 把 v1.0（`2026-07-22-002`）的 harvest／triage／brief 骨架，升級成一條**可持續 drain 的優先研究管線**：leads 依 priority 排序、pq1（追源+抽取）自動消化到「等你核准」為止、人工 gate 只剩對話式批次核准、入圖後自動建 Shadow 追蹤，且**圖的變化（evidence-delta）每天回流到 brief**，讓迴路真正閉合。
- **User outcome:** 使用者每天在 Claude app 收到一份 action-first brief（由 cloud routine 產出、推播），用一行批次語法（`1 3 7 go 4 drop 5 6 pending`）核准，不必開本機 session、不必碰 GitHub UI。貴的研究（pq1）在背景替他消化；每天的 brief 因為昨天入了什麼證據而不同。
- **Authority contract:** 三道閘門不變——graph admission 必經明確核准、深挖研究由 priority/使用者驅動但入圖仍核准、live 資本永遠人工。**leads 狀態只是注意力 metadata，永不影響 evidence tier、decision 或圖。** 新增的 MCP 寫入面只准動 leads，不准動圖/碼。
- **平台假設:** 單一平台（Claude）。本次**不做** Claude/Codex 雙平台 token 分配（過度複雜，deferred）。
- **上線目標（L2）:** 用真實流量撞出 priority 權重、drain 節奏、evidence-delta 精度是否合用；v0 刻意最小，撞到回頭修。
- **Stop conditions:** 若實作需要讓 routine 自動入圖、MCP commit/push 超出 leads.json exact pathset、lead 狀態影響 evidence tier、evaluate-signal 在雲端建 decision、或從 recommendation 推定 choice/fill，立即停止回報。

## 承接 v1.0 與本次前置（已完成，非本 plan scope）

- v1.0（`2026-07-22-002`）已交付並 push：`engine_b/leads.py` 狀態機、`crons/harvest_leads.py`、`engine_b/cli.py`、`crons/pending_leads_digest.py`、`skills/daily-brief/SKILL.md`、`crons/daily_brief_prompt.md`、MCP `get_decision_brief`、U2 partial-identity 修復。
- **market_timestamp_future 系統性 bug 已修**（commit `7f60f0b`）：normalize 的 future 檢查改看 `as_of > max(evaluation, fetched_at)`，source 端夾 as_of 到不超過 fetched_at。本 plan 假設市場 lane 已可用。
- 已存在的 4 個 COHR + 1 LITE dev-test cohort 的 future blocker 已凍結不可改；本 plan 不 destructive reset，但 U3 的 Shadow-first 呈現不依賴這些 test 產物。

## 討論定案紀錄（2026-07-22 → 2026-07-24，本 plan 的設計來源）

規劃過程逐題釐清、已內化成下方 requirements 的決定：

- **Paper 改 Shadow-first：** 使用者要的「app 清單、隨意加、看自從追蹤變化多少」＝Shadow Observation（零資本、自動、無 gate）。funded paper（模擬 sizing）對個人手動 sizing 是過度設計 → 降為 deferred。預設流程：research 入圖 → 自動 Shadow 追蹤 → brief 顯示「自追蹤 +X%」。
- **PQ 是 pq1 預算分配器：** token 幾乎全花在 pq1（source-trace + extraction）；harvest 零 token、triage 便宜、pq2/入 probe 便宜。所以 priority 要 gate 的是「進入 pq1 的入口」，決定貴的 token 花在哪幾則。
- **可續跑靠持久 checkpoint：** 每個 lead 的 status 就是 checkpoint；被 5 小時限制/當機打斷後重跑同一 drain 命令即從剩下的接。不必撐過限制。
- **人工 gate 只剩 pq2：** pq1 全自動 drain 到 prepared；只有「核准入圖」是人工。
- **砍 GitHub UI，但 push 照常：** 不用 PR/Issue 看東西；cloud routine → Claude app 推播 → chat 批次回覆。leads 狀態由 **MCP 本機 commit+push（窄 pathset）** 同步，cloud 每天讀 pushed clone 看到最新狀態，全程不動圖。
- **批次語法：** `1 3 7 go 4 drop 5 6 pending`，type-aware dispatch。
- **閉環是關鍵：** 入圖 → 連結 probe → evidence-delta 回 brief，讓 brief 每天不同。
- **Lifecycle hook + 手動：** 砍 PR 寫 lifecycle.json；disproof 評估與 retired/revised 需人工判斷，SessionStart hook + weekly 唯讀提醒到期，使用者本機手動複查更新。
- **Weekly 瘦身：** 健康檢查 + 發現未知（horizon 掃描）+ 唯讀 lifecycle 到期提醒；不碰 lifecycle 寫入、不與 daily 重疊。
- **X：** 先 RSS + 手動貼（免費）撞需求，X API（特定無 RSS 帳號）deferred。harvest 更多來源不會讓管線更快、只會填滿 queue，所以 priority 更重要。

---

## Product Contract

### Actors

- **使用者：** 每天在 Claude app 讀 brief、回批次語法；核准入圖；手動貼消息（Fast Path）；週一次本機 session 補 Git 帳本、手動複查 thesis lifecycle。
- **Cloud routine（claude.ai 排程）：** 每日產 brief（心跳）→ best-effort drain pq1 到 prepared；經 MCP 讀決策/RA、寫 leads；不建 decision、不入圖、不改 lifecycle。
- **本機 MCP server：** leads 狀態的讀寫 + 窄 pathset commit/push 執行端；圖 admission 的 filesystem-first + graph 寫入端。
- **本機 session（週一次）：** 補 Git provenance 帳本；手動 thesis 複查。

### Requirements

**優先研究佇列（PQ）**

- R1. 每個 triaged_go lead 有一個**可重算的 priority 分數**，成分取自 signal-triage 五要素：tier、矛盾/反證價值（disproof 相關）、thesis 影響度（是否關聯已入圖/已入 probe 的公司）、新穎性、來源獨立性（L8 進展）。priority 不凍結——隨圖狀態可 re-rank。
- R2. priority gate 的是**進入 pq1 的入口**。drain 一律先取最高 priority 的 triaged_go。pq1 = source-trace + extraction，是唯一昂貴階段；harvest/triage/pq2 相對零成本。
- R3. **可續跑 drain：** 一個命令 pop 最高 priority 的 N 個 triaged_go → 對每個跑 pq1（trace + extract + prepare_research_action）→ **每個 lead 做完就 checkpoint status（researching→action_prepared）** → 直到 budget/限制到或 queue 空。重跑同命令從剩下的接（靠持久 status）。不得因中途中斷遺失已完成的 prepared action。
- R4. drain 的 runner 可以是 cloud routine（心跳後 best-effort）、本機 on-demand、或使用者手動貼消息插隊（Fast Path，最高 priority）。三者匯到同一 prepared → pq2。

**對話式核准（無 GitHub UI）**

- R5. brief 的每個 actionable item 有**穩定編號**（跨 section 連續）。使用者回**批次語法** `<編號…> <動詞> <編號…> <動詞> …`（空白/逗號分隔，一行多組）。動詞封閉集合：`go`／`drop`／`pending`。沒點到的編號預設不動。
- R6. dispatch 是 **type-aware**：`go` 對 raw lead → 進 pq1；對已 prepared 的 action → apply 入圖；對到期 thesis → 引導 reassess/複查。`drop` → park。`pending` → 明確 defer、留到之後 brief。動詞不新增任何權限語意。
- R7. 核准介面是**對話**（Claude app thread 或本機 session），**不使用 GitHub Issue/PR**。cloud routine 的 brief 產出即可被接續操作（帶 MCP + web），結尾附批次語法說明。

**MCP leads 同步（窄 pathset commit/push）**

- R8. 新增 MCP 工具讓 chat 驅動 leads 狀態：`get_pending_leads`（READ_ONLY：priority 排序的佇列 + harvest_log）、`record_lead_decision`（寫：triage/advance，只動 attention metadata）。**leads 狀態永不影響 evidence tier、decision 或圖。**
- R9. `record_lead_decision` 寫入後由**本機 MCP server** 對 `library/leads/pending_leads.json` **commit + push**，exact pathset 鎖死（只准這一個檔）。這是對既有「遠端無 Git」邊界的**窄例外**：只准 leads.json、不准圖/碼/extraction；憑證留本機、MCP 只觸發。cloud routine 讀 pushed clone → 每天看到最新 leads 狀態。
- R10. 圖 admission（apply）仍走 `apply_research_action`（MCP native approval）寫圖 + filesystem-first；**圖 provenance 帳本的 Git commit 仍走本機 publisher**（careful validation：master/空 index/ancestry/action trailer/exact pathset），週一次本機 session 補。不把高風險 provenance commit 搬上 MCP。

**閉環回饋（loop 的關鍵）**

- R11. 入圖時把該 lead **連結到其 focus company 的 probe**（若存在）。brief 的 per-probe 項要能顯示「自上次決策後新增的證據」及建議 `reassess`。
- R12. evidence-delta 要有**精度**：新證據標 material 的條件是它觸及該 probe **frozen context 的 causal path / thesis subject**，而非只是「這家公司多了一條 claim」。一般價格波動不得當 thesis 變（beta move → NO ACTION，沿用 v1.0 RISK6）。
- R13. **入圖後自動建 Shadow：** admission 成功後，對 focus company 建立零資本 Shadow Observation（研究 intent、range 0），凍結追蹤當下價格/catalyst/disproof。這是 composition（workflow 編排），不是 Engine A 呼叫 Engine D。已有 probe 的公司不重複建，改走 R11 的 evidence-delta。

**Shadow-first paper**

- R14. 預設追蹤是 Shadow（零資本、自動、無 gate）。brief 每個 probe 顯示「自追蹤變化 %」（inception price → current price；缺 inception 則標 unknown，不 backfill）。funded paper（模擬 sizing）**deferred**，只在使用者明確要時才走既有 `--intent paper`。

**Brief UX**

- R15. brief 修正 v1.0 的呈現問題：每項穩定編號 + 明確指令（如「→ research 2」）；**丟掉混亂的顏色維度**（不再用顏色混表 triage 與優先度）；Form 4 與較舊 filing 進「低優先（摺疊）」只列數量。
- R16. brief 分區 exception-first：需要你動作（決策佇列 REVIEW/TRADE/HEDGE、到期 thesis、等 apply 的 RA、有 evidence-delta 的 probe）／新 leads（priority 排序 + go 指令）／低優先摺疊／無事一行。無事輸出 `NO ACTION + 日期`。

**Lifecycle 與 Weekly**

- R17. 砍掉 weekly PR 寫 lifecycle.json。lifecycle 到期由 **SessionStart hook + weekly 唯讀提醒**雙重 surface；使用者本機**手動**複查更新（disproof 評估與 retired/revised 需人工判斷）。擴充 `crons/thesis_freshness_check.py` 讓它讀 `thesis/lifecycle.json` 的 `next_check`/`review_required`（現在只看 memo 檔日期）。
- R18. Weekly routine 瘦身為：系統健康審查 + 發現未知（horizon/topic discovery，找 watch 清單外的新公司）+ 唯讀 lifecycle 到期提醒（backstop）。不碰 lifecycle 寫入、不與 daily 消化已知重疊。

### Scope Boundaries

**Deferred（各自後續，不在本次）：** funded paper sizing lane、Formal Position lane 進 Engine D、Claude/Codex 雙平台 token 分配、X API harvest、圖 provenance 帳本經 MCP commit、push notification 客製化。
**Never：** routine 自動入圖或自動深挖無核准；lead 狀態影響 evidence tier/decision/圖；MCP commit/push 超出 leads.json exact pathset；evaluate-signal 在雲端建 decision；recommendation→choice/fill 推定；一次入圖多於一次確認。

---

## Key Technical Decisions

- **KTD1 — priority 是 pq1 預算分配器，不是排程器。** priority 只決定「貴的 pq1 token 先花在哪」；harvest/triage 便宜到不排。分數可重算（隨圖狀態），不凍結。
- **KTD2 — 可續跑靠 lead-status checkpoint，不靠撐過限制。** drain 冪等、逐 lead checkpoint；中斷重跑從剩下接。這讓長 queue 自然攤到數天，不需要單 session 撐 5 小時。
- **KTD3 — 人工 gate 只剩 pq2（核准入圖），對話式批次。** pq1 全自動；核准回歸對話（無 GitHub UI）；一次入圖只確認一次（走批次 go 就不再 native approval 疊加）。
- **KTD4 — leads 走 MCP 窄 pathset commit/push；圖 provenance 留本機 publisher。** 低風險 attention metadata 可走 MCP git（exact pathset）換取 cloud 每天同步；高風險 provenance 帳本留本機嚴格 publisher。這個「低風險走 MCP、高風險留本機」的分野是刻意的。
- **KTD5 — 閉環用既有 evidence_delta + reassess，不另建。** brief 已在算 evidence_delta；本次補「連結 probe + causal-path 精度 + 使用者可見 + 自動 Shadow」。不建平行機制。
- **KTD6 — Shadow-first 是呈現與預設的改變，不是架構重寫。** 系統本就支援 shadow-only probe；本次把它設為預設追蹤並顯示「變化%」，funded paper 降為可選。
- **KTD7 — daily routine 先心跳後 drain。** brief 便宜必完成（心跳可靠），pq1 貴的 drain 用剩餘預算 best-effort、可續跑；別讓 pq1 挾持心跳。
- **KTD8 — 單一平台。** 不做 Codex 分流；runner 就是 Claude（cloud routine + 本機 + chat）。

---

## Implementation Units

### U1 — Priority 分數與可續跑 pq1 drain

- **Files:** modify `engine_b/leads.py`（lead 加 `priority` 衍生欄與計分）、`engine_b/cli.py`（`list` 依 priority 排序、`drain` 子命令）；add `engine_b/priority.py`（計分，讀 signal-triage 五要素 + 圖狀態 hint）；add `tests/test_engine_b_priority.py`、擴 `tests/test_engine_b_cli.py`。
- **Approach:** priority = 可重算函數（tier + 矛盾價值 + thesis 影響 + 新穎性 + 獨立性），thesis 影響度需要「該公司是否已入圖/已入 probe」的 hint（唯讀查詢，不在 leads 模組硬耦合 Engine A/D，用注入）。`drain` 命令：pop 最高 priority 的 triaged_go、逐個推進 status 並 checkpoint、到 budget/限制或空；冪等重跑。pq1 的實際 trace+extract 由 skill/agent 執行（語意工作），`drain` 負責 pop 順序、狀態機與續跑契約。
- **Tests:** priority 排序、re-rank、drain 冪等續跑（中斷後重跑不重複已 prepared）、budget 上限、空佇列。
- **Dependencies:** 無（承接 v1.0 leads）。

### U2 — MCP leads 讀寫 + 窄 pathset commit/push

- **Files:** add `mcp_server/leads_tools.py`（core：get/record，可注入）；modify `mcp_server/graph_mcp.py`（+2 工具，10→12）；add `mcp_server/leads_git.py`（exact-pathset commit/push guard，僅 `library/leads/pending_leads.json`）；modify `docs/remote-access-architecture.md`（工具數、窄 Git 例外的安全說明）；add `tests/test_leads_mcp.py`。
- **Approach:** `get_pending_leads` READ_ONLY 回 priority 佇列 + harvest_log（redacted，無私有路徑）。`record_lead_decision` 寫 triage/advance（走 U1 的 leads API）後呼叫 leads_git 對 exact pathset commit+push；guard 驗只有 leads.json 被 stage、master、非圖/碼、憑證不外洩。錯誤不洩私有路徑。
- **Tests:** get/record round-trip；record 後 leads.json commit 且 pathset 只含 leads.json；拒絕任何非 leads 路徑；redaction；push 失敗（non-fast-forward）優雅處理不 corrupt。
- **Dependencies:** U1。

### U3 — 閉環：lead↔probe 連結、evidence-delta 精度、自動 Shadow

- **Files:** modify `decision_lab/brief.py`（per-probe evidence-delta 顯示 + causal-path 精度 + Shadow 變化%）、`decision_lab/workflow.py` 或新 orchestration（admission 後自動建 Shadow）、`engine_b/leads.py`（applied lead 記 focus company/probe ref）；add `tests/test_closed_loop.py`、擴 `tests/test_decision_brief.py`。
- **Approach:** admission 成功 → lead 記 focus company → 若無 probe 則自動 evaluate-signal（research intent）建 Shadow；若有 probe 則 R12 evidence-delta。evidence-delta 精度：比對當前圖 refs 與 probe frozen context 的 causal_paths/subject，只有觸及者標 material。brief per-probe 顯示「新證據 + 建議 reassess」與「自追蹤 +X%」。
- **Tests:** 入圖 co:X → 自動 Shadow；已有 probe 的 co:X 入新證據 → 下次 brief 標 material + reassess；只動價格 → 不標 material（NO ACTION）；無關 claim 不誤標；缺 inception price → 變化% unknown 不 backfill。
- **Dependencies:** U1（leads applied 狀態）。

### U4 — 對話式批次核准與 brief UX

- **Files:** modify `skills/daily-brief/SKILL.md`（批次語法 grammar + type-aware dispatch 表 + 穩定編號 + 丟顏色 + Form4/舊 filing 摺疊 + Shadow 變化%）；regenerate adapters（`sync_agent_skills.py`）；modify `decision_lab/brief.py` renderer（編號、分區）；擴 `tests/test_daily_brief_skill.py`、`tests/test_decision_brief.py`。
- **Approach:** brief renderer 給每 actionable item 跨 section 連續編號；skill 定義批次語法解析（`<nums> <verb>` 多組）與 type-aware dispatch（lead→pq1 via drain/Fast Path；prepared→apply；due thesis→reassess 引導；drop→park via MCP/CLI；pending→defer）。移除顏色，改明確指令字串。
- **Tests:** skill 契約（批次語法、封閉動詞、type-aware、無硬編政策）；編號穩定；Form4 摺疊；render 分區。
- **Dependencies:** U1、U2（dispatch 打 leads API/MCP）、U3（brief 內容）。

### U5 — Routine 重組、lifecycle hook、weekly 瘦身、文件

- **Files:** modify `crons/daily_brief_prompt.md`（先心跳後 best-effort drain；MCP 讀決策/寫 leads；無 GitHub、Claude app 推播 + 批次回覆說明）、`crons/weekly_scan_prompt.md`（瘦身：健康 + 發現未知 + 唯讀 lifecycle 提醒；砍 lifecycle 寫入）、`crons/thesis_freshness_check.py`（讀 lifecycle.json next_check/review_required）；modify `AGENTS.md`、`docs/plans/README.md`；擴 `tests/test_routine_prompts.py`、`tests/test_pending_leads_digest.py`（或新 lifecycle hook 測試）。
- **Approach:** daily prompt 排序心跳→drain；lifecycle 到期由 hook + weekly 唯讀提醒，寫入本機手動。weekly 明確只做健康 + horizon discovery + lifecycle 提醒。AGENTS 更新 v1.1 現狀與 operational 命令。
- **Tests:** hook 讀 lifecycle 到期；prompt 契約（daily 先心跳後 drain、cloud 只讀寫 leads 不寫圖/lifecycle、批次語法；weekly 不碰 lifecycle 寫入、保留 discovery + health + 唯讀提醒）。
- **Dependencies:** U1–U4。

## Dependency Order

`U1 → U2 → U3 → U4 → U5`。U1 定 priority/drain；U2 建 MCP leads 同步面；U3 閉環；U4 對話核准 UX；U5 wiring routine/lifecycle/docs。U1 完成即可本機試 drain；U2 後 chat 能驅動 leads；U3 後迴路閉合；U4 後對話核准可用；U5 上線。

## Risks

- **RISK1 — priority 權重拍腦袋。** signal-triage 本就 v0；用真實流量調，priority 可重算所以能迭代。
- **RISK2 — drain 在 cloud 燒 token。** 心跳先跑保證產出；drain best-effort + priority + 可續跑，攤到數天。撞到再限 batch 大小。
- **RISK3 — MCP leads git push 放寬「遠端無 Git」。** exact pathset 鎖死 leads.json、attention-only、憑證留本機；最壞情況只污染 watchlist 狀態，無圖/決策衝擊。security review 在 U2 明確覆蓋「不能經此 push 任何非 leads 檔」。
- **RISK4 — evidence-delta 太吵或太鈍。** causal-path 精度是 U3 重點；太吵→縮範圍，太鈍→放寬，用真實入圖撞。
- **RISK5 — 自動 Shadow 製造一堆空 probe。** 只對 admission 的 focus company 建；缺資料的 probe range 0、shadow-only，不佔資本、不強制動作。
- **RISK6 — 圖 provenance 帳本 lag。** apply filesystem-first 已寫本機檔，只是 git commit 延遲週一次；圖是真相（cloud 經 MCP 讀得到），帳本是備份，lag ≤ 一週可接受。

## Verification Contract

- Targeted：`test_engine_b_priority`、`test_engine_b_cli`、`test_leads_mcp`、`test_closed_loop`、`test_daily_brief_skill`、`test_routine_prompts`、`test_decision_brief`。
- Gates：完整 `pytest` 與 baseline 比對（現況 2 既知 failure：enablence 缺檔、sourcedoc section=None）、`sync_agent_skills.py --check`、`git diff --check`、`thesis/preconditions.py` 維持全綠。
- 上線驗收（真實）：一條 lead 從 harvest→triage→drain(pq1)→prepared→chat 批次 go/apply→入圖→自動 Shadow→隔日 brief 顯示 evidence-delta 全程跑通；MCP record_lead_decision 後 cloud 讀到最新 leads；批次語法三動詞各真實跑通；Engine A 無新增 write path（preservation 通過）。

## Definition of Done

- [x] priority 排序 + 可續跑 drain（中斷重跑不重複 prepared）。
- [x] MCP `get_pending_leads`/`record_lead_decision`（12 工具）+ leads.json 窄 pathset commit/push；拒絕任何非 leads 路徑（真實 temp git repo 測試）。
- [x] 入圖 → 連結 probe（既有 refs）→ evidence-delta（causal-path 精度）回 brief；`ensure_shadow_for_company` 自動建 Shadow；brief 顯示「自追蹤 +X%」。
- [x] 對話式批次語法 `go/drop/pending` type-aware dispatch（`engine_b/batch.py`）；brief 穩定編號、去顏色、Form4 摺疊（skill）。
- [x] daily 先心跳後 drain；weekly 瘦身（健康 + 發現未知 + 唯讀 lifecycle 提醒、不寫 lifecycle）；hook 讀 lifecycle 到期。
- [x] 無 GitHub UI；cloud → Claude app → chat 批次核准；push 照常（MCP/本機）。
- [x] AGENTS/README/remote-access 文件同步；sync clean；full suite 與 baseline 比對歸因；邏輯 commits，master 已 push。

> **完成狀態：** U1–U5 程式碼、skill、prompt、測試、文件全部交付並 push。剩 rollout（使用者在 claude.ai 建 daily routine 並 bake 數天）是 claude.ai 端操作，非程式工作。

## 上線 checklist（人工）

1. 實作完成、push backlog。
2. 使用者在 claude.ai 建 daily routine（貼 `crons/daily_brief_prompt.md`，排台北早上），確認產出推播到 app。
3. 連續數天 bake：真實流量撞 priority 權重、drain 節奏、evidence-delta 精度、批次語法手感；摩擦點回寫本節。
4. 決定是否要 X API（觀察 RSS + 手動貼漏掉多少）。
