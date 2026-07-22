---
title: Daily Approval Loop - Plan
type: feat
date: 2026-07-22
topic: daily-approval-loop
status: ready
artifact_readiness: implementation-ready
product_contract_source: user-directed
planning_mode: direct
execution: code
---

# Daily Approval Loop - Plan

## Goal Capsule

- **Objective:** 把「發現 → 初篩 → 追源草稿 → 核准 → 入庫／決策」收斂成一條每日迴路：系統做便宜的 harvest／triage／聚合，使用者每天只面對一份 action-first 的 Daily Approval Brief，用封閉動詞集合（`apply`／`research`／`park`／`skip`…）一句話核准。
- **User outcome:** 使用者不再需要自己刷 X／Substack／EDGAR 找料；每天（本機或手機）看一頁 brief，回一句話，系統走既有流程。無事時 brief 是一行 `NO ACTION`。
- **Authority contract:** 三道閘門原封不動——graph admission 必經使用者核准 exact ID；深挖 research 必經使用者點名；live 資本行動永遠人工。Brief 本身純讀，不建立 decision、不下單、不入圖。pending leads 是 Engine B 的注意力狀態（attention metadata），**不是 evidence**——它不能提高 evidence tier、不能繞過 source-trace。
- **上線目標（L2 精神）：** 本 plan 以「儘快讓迴路真的跑起來、用真實流量撞出問題」為準；v0 刻意最小，已知會壞的地方列在 Risks，撞到回頭修。
- **Stop conditions:** 若實作需要讓 routine 自行入圖、自動深挖、自動建立 decision／choice／fill、或把 lead 狀態當 evidence 用，立即停止並回報。

## 架構事實（實作前提，已驗證）

1. **Cloud routine 連不到本機**（`crons/weekly_scan_prompt.md` 明文）：它有 GitHub clone＋web search＋MCP connector。本機 master 慣性領先未 push，所以 **repo 檔案不能當雲端的 live 狀態來源；pending leads 的 live 視窗必須是本機 MCP gateway**（server 在本機，可讀寫本機檔案與唯讀 Engine D store）。
2. **MCP gateway 現有 9 工具**（READ_ONLY／ADDITIVE／PREPARE 三類 annotation）；新工具沿用同一 annotation 與 redaction 紀律，surface 從 9 → 12。
3. **Engine D 的 Action Card／today 已有 redacted public DTO**（operational workflow plan R17/KTD10）——手機／雲端讀 brief 只是曝露既有 DTO，不是新引擎。
4. **既有 bug 是本迴路的直接依賴：** registry 條目缺 execution metadata（market_currency 等）時 `evaluate-signal` 在 context freeze 階段丟 `context identity does not match cohort authority`（INVALID_REQUEST），違反 operational plan R9（missing 應為 domain result）。registry 大多數公司缺這些欄位，daily loop 的 `research <lead>` 會直接撞上。2026-07-22 已以補 COHR metadata 繞過一次；本 plan 必須根治。

## Product Contract（收斂版）

### Actors

- **使用者：** 每天讀 brief、回動詞；核准 Research Action；點名深挖；live 行動仍手動。
- **本機 session（Claude Code／Codex）：** 執行 `/daily-brief` skill——inline harvest、triage 新 leads、組 brief、dispatch 動詞到既有流程。
- **Daily cloud routine：** 每日 harvest（web）＋ triage ＋ 經 MCP 讀本機狀態 → 產 GitHub Issue brief；不入圖、不建 decision。
- **本機 MCP gateway：** leads 狀態與 decision brief 的唯一 live 視窗。

### Requirements

**Leads 狀態與 harvest**

- R1. pending leads 狀態存本機 `library/leads/pending_leads.json`（tracked；git 副本只是 lagging mirror，live 讀寫一律經狀態模組或 MCP）。每條 lead：`lead_id`（URL content hash）、source、url、title、published_at、first_seen、status、triage 結果、refs（research_action_id 等）。URL hash 去重，重複 harvest 冪等。
- R2. Status 是封閉狀態機：`pending → triaged_go | triaged_no_go`；`triaged_go → researching → action_prepared → applied`；任何狀態可 `parked`。不變式：**任何 status 都不影響 evidence tier**。
- R3. Harvest 來源由 `crons/harvest_config.json` 設定（可編輯，不 hardcode）：v0 = aleabitoreddit RSS（channel 標題是 "Serenity"，見 AGENTS 既知坑）＋ EDGAR watch tickers 的新 filing 檢查（沿用 `fetchers/edgar.py` 的 submissions 查詢，只記 metadata 不下載全文）。
- R4. Harvest 失敗必須誠實：每次 run 寫 harvest_log（run_at／source／ok|fetch_failed|parse_failed／new 數量）；**解析失敗 ≠ 無新文**，brief 必須把 failed source 標出來並提示 fallback（`site:aleabitoreddit.substack.com` web search）。

**Brief 組成與動詞**

- R5. Brief 是三佇列聚合、exception-first：(a) 決策佇列＝`decision_lab today` 的 redacted DTO；(b) 入庫佇列＝pending Research Actions（`get_research_action_status`）；(c) 注意力佇列＝triaged leads。無事輸出一行 `NO ACTION` ＋日期。
- R6. 動詞是封閉集合並在 brief 尾附說明：`research <n|topic>`（觸發 source-trace＋lead-intake）、`apply <ra_id>`（既有核准協定）、`park <n>`、`skip`；決策類（`accept`／`reduce`／`record fill`）僅本機，維持 explicit flags。動詞不新增任何權限語意。
- R7. Triage 由 `skills/signal-triage/SKILL.md` 判準執行（LLM 便宜判斷），結果寫回 lead 的 triage 欄位；triage 刻意寬鬆，寧可多列一條待判斷、不可默默丟棄（丟棄也要記 reason）。

**MCP surface（9 → 12）**

- R8. 新增三個 bounded 工具：`get_pending_leads`（READ_ONLY：佇列＋harvest_log）、`record_lead`（ADDITIVE：以 URL hash upsert lead 註冊或 triage 欄位；**只能寫 attention metadata**，不能碰 graph／evidence／decision）、`get_decision_brief`（READ_ONLY：today 的既有 redacted public DTO 原樣曝露，不得繞過 redaction 另組 payload）。
- R9. 三工具遵守既有 gateway 紀律：annotation 分類、輸入驗證、錯誤不洩 private path；`record_lead` 拒絕含 secret 的 payload。`docs/remote-access-architecture.md` 的工具數與資料流同步更新。

**Cloud routine 與排程**

- R10. 新增 `crons/daily_brief_prompt.md`：每日（台北 06:30，錯開週掃 06:00）執行 harvest（web fetch RSS／EDGAR）→ 經 `record_lead` 註冊＋triage → 讀 `get_pending_leads`＋`get_decision_brief`＋`get_research_action_status` → 產出當日 GitHub Issue（label `daily-brief`，附動詞說明）→ 前一日 Issue 若無人動作自動 close 並在新 Issue 註記 carry-over。MCP 連不上時照 weekly scan 慣例：不卡住、Issue 開頭標明降級範圍。
- R11. Routine 與 weekly scan 分工明確：daily 只做「佇列＋今日行動」；topic discovery 深度聚類、thesis 生命週期、系統健康仍歸 weekly。兩份 prompt 互相引用此分工，避免漂移。
- R12. 本機 session 開頭 digest 增加一行「pending leads N 條（M 條 triaged_go）」——沿用既有 session-start digest 機制擴充，不另建通知系統。

### 前置修復（進 scope）

- R13. **修 evaluate-signal 的 partial-identity crash：** registry 有 company_id＋ticker 但缺 execution metadata 時，wide capture 與 freeze 必須完成，缺欄以既有 blocker 語意呈現（`execution_currency_missing` 等已存在於 IdentityAuthority.blockers），funded lanes fail closed；不得丟 store exception。修法以 operational plan R9／KTD3 為準（domain result，非 INVALID_REQUEST），cohort identity binding 與 context identity 的一致性規則必須在測試中明確固定。
- R14. **Registry metadata 補齊 EDGAR watch 名單：** watch 清單內的美股 ticker 補 `market_currency`／`execution_currency`／`execution_venue`（依 filing cover 逐字，如 COHR 前例）；非美股與私人公司不在 watch 名單，不硬補。

### Scope Boundaries

**Deferred（各自獨立 plan，不在本次）：** Formal Position lane 進 Engine D；自動入圖放權（tier ≤2 自動 admission）；remote 寫入 decision（record-choice／fill 上手機）；push notification；X API harvest；來源清單大擴張。
**Never：** routine 自行入圖或自動深挖；lead 狀態影響 evidence tier；brief 產生 decision／交易；Engine D 寫 Sheet。

---

## Key Technical Decisions

- **KTD1 — 狀態的 live 視窗是 MCP，不是 git。** pending_leads.json 本機為 authority；雲端讀寫一律經 gateway 工具。理由：master 慣性不 push，repo clone 必然 stale。
- **KTD2 — 本機不裝排程器。** 本機 harvest 在 `/daily-brief` 執行時 inline 跑（秒級）；每日保底由 cloud routine 承擔。兩邊 URL-hash 冪等，重複無害。避免 Windows Task Scheduler 這類新維運面。
- **KTD3 — brief 的決策內容只曝露既有 redacted DTO。** `get_decision_brief` 是 pass-through，不重組 payload；任何新欄位需求回到 Engine D 的 DTO 層做，維持單一 redaction 路徑。
- **KTD4 — Issue 是 view，json 是 state。** GitHub Issue 只是每日渲染結果與手機閱讀面；狀態變更一律落在 pending_leads.json（經動詞 dispatch 或 `record_lead`）。Issue 與 state 不同步時以 state 為準。
- **KTD5 — triage 跑在誰身上由呼叫端決定。** 本機 session（Claude Code／Codex 皆可，Codex 走 OpenAI 額度）與 cloud routine 用同一份 signal-triage skill 判準；plan 不綁定供應商。

## Implementation Units

### U1 — Leads 狀態模組與 harvest script

- **Files:** add `engine_b/__init__.py`, `engine_b/leads.py`（狀態機、URL-hash 去重、harvest_log、atomic 寫檔）, `crons/harvest_leads.py`（RSS＋EDGAR watch）, `crons/harvest_config.json`；add `tests/test_engine_b_leads.py`。
- **Approach:** leads.py 只依賴標準庫；RSS 解析失敗記 `parse_failed` 不拋例外；EDGAR 用 submissions JSON 比對已見 accession，只記 metadata。config 含 feed 清單（附 Serenity 註記）與 watch tickers（v0：COHR、LITE、AMAT、LRCX、AXTI、AAOI、TSEM、GFS）。
- **Tests:** 去重冪等、狀態機非法轉移拒絕、parse 失敗誠實記錄、config 缺欄 fail closed。

### U2 — 修 partial-identity crash ＋ registry 補齊（R13–R14）

- **Files:** modify `decision_lab/context.py` 或 `decision_lab/workflow.py`（依實作判斷，以最小 diff 滿足 R9 語意）, `config/company_identity.json`；modify `tests/test_operational_workflow.py`（新增 partial-metadata fixture 案例）。
- **Approach:** 固定契約——「registry 能解析 company_id＋ticker 即可完成 capture＋freeze；execution metadata 缺失是 lane blocker 不是 identity 失敗」。負向測試：partial ticker 走完 evaluate-signal 得 REVIEW card＋blockers，無 exception；既有完整 metadata 案例不回歸。
- **Dependencies:** 無（可與 U1 並行）。

### U3 — MCP gateway 三工具（R8–R9）

- **Files:** modify `mcp_server/graph_mcp.py`；modify `docs/remote-access-architecture.md`；add/extend `tests/test_graph_mcp.py`（或既有 gateway 測試檔）。
- **Approach:** `get_pending_leads`／`record_lead` 直接用 U1 的 leads.py（單一狀態實作）；`get_decision_brief` 呼叫 Engine D 既有 brief/today 純讀入口取 DTO。`record_lead` 的欄位 allowlist 固定在工具層；secret 掃描沿用既有 gateway 慣例。
- **Dependencies:** U1；`get_decision_brief` 依賴既有 Engine D，無新依賴。

### U4 — `/daily-brief` skill 與 session digest（R5–R7、R12）

- **Files:** add `skills/daily-brief/SKILL.md`（canonical）；regenerate `.agents/skills/`、`.claude/skills/`（`python scripts/sync_agent_skills.py`）；session-start digest 擴充（實作時查現行 hook 設定，最小改動）；modify `tests/test_skill_decision_contract.py` 或新增 parity 測試。
- **Approach:** skill 定義：inline 跑 `python crons/harvest_leads.py` → 對 pending 新 leads 依 signal-triage 判準 triage 並寫回 → 跑 `python -m decision_lab today --format markdown` → 組三佇列 brief（繁中、action-first、動詞說明在尾）→ 動詞 dispatch 表（`research <n>` → source-trace＋lead-intake；`apply <ra_id>` → 既有 apply＋`scripts/commit_pending_intake.py`；`park` → leads.py 狀態轉移）。skill 不含政策數值、不算 sizing。
- **Dependencies:** U1、U2（research 動詞會打 evaluate-signal）。

### U5 — Daily cloud routine 與上線（R10–R11）

- **Files:** add `crons/daily_brief_prompt.md`；modify `crons/weekly_scan_prompt.md`（加一段分工註記）；modify `AGENTS.md`（開發優先序＋operational commands）。
- **Approach:** prompt 結構仿 weekly scan（前提宣告、MCP 降級規則、Stage 化流程、Issue 模板含動詞說明與 carry-over 規則）。上線 checklist（人工步驟，寫進 prompt 檔頭）：使用者在 claude.ai 建 daily routine（06:30 台北）→ 連續跑 3 天 → 每天的摩擦點記在當日 Issue 留言 → 第 3 天彙整回寫本 plan 的「上線觀察」節或 docs/solutions。
- **Dependencies:** U3（MCP 工具）、U4（動詞語意定案後 Issue 模板才能引用）。

## Dependency Order

`U1 → {U2 ∥ U3} → U4 → U5`。U1 先定狀態；U2 可並行（獨立 bug fix）；U3 依賴 U1 的狀態模組；U4 把本機端跑通（**此時本機迴路即可上線試用**）；U5 補雲端與手機面。

## Risks（v0 已知會壞的地方，撞到再修）

- **RISK1 — 初期流量太稀，brief 天天 NO ACTION。** 接受；這是來源清單問題不是管線問題，擴源另議。
- **RISK2 — triage 判準太鬆／太緊。** signal-triage 本來就標為拍腦袋 v0；用真實流量調。
- **RISK3 — Issue view 與 json state 漂移**（使用者在 Issue 上打勾但沒回動詞）。v0 以 state 為準＋carry-over 註記；若真實使用中常發生，再考慮讓 routine 讀 Issue 回寫。
- **RISK4 — MCP tunnel 斷線時手機面全失。** 降級規則已定（R10）；本機面不受影響。
- **RISK5 — `record_lead` 是新的遠端寫入面。** 已用 allowlist＋attention-only 邊界壓低風險；security review 在 U3 測試中明確覆蓋「不能經此工具影響 graph／decision／tier」。

## Verification Contract

- Targeted：`python -m pytest tests/test_engine_b_leads.py tests/test_operational_workflow.py <gateway tests>`；U2 的 partial-identity 負向測試必須先綠。
- Suite／gates：`python -m pytest`（與既有 baseline 比對）、`python scripts/sync_agent_skills.py --check`、`git diff --check`、`python thesis/preconditions.py`（應維持全綠）。
- 上線驗收（真實使用，非 fixture）：連續 3 個 routine 日產出 brief Issue；`research`／`apply`／`park` 三動詞各被真實執行至少一次；harvest 失敗至少人工注入一次驗證誠實降級；Engine A 無 write path 新增（preservation 測試維持通過）。

## Definition of Done

- [ ] 本機 `/daily-brief` 一個指令產出三佇列 brief，無事輸出 `NO ACTION`。
- [ ] partial-identity ticker 走完 evaluate-signal 不 crash，缺欄以 blocker 呈現。
- [ ] MCP 12 工具：三新工具過測試，remote-access 文件同步。
- [ ] Daily routine 連續 3 天產出 Issue，carry-over 與降級規則被觀察到正確運作。
- [ ] 動詞 dispatch 三條路徑（research／apply／park）真實跑通各一次。
- [ ] AGENTS 更新、skill sync clean、full suite 與 baseline 比對歸因、邏輯 commits、不 push。
