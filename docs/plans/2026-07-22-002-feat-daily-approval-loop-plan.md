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
revised: 2026-07-22 (push 前提定案後修訂：git push 為狀態同步機制，MCP 增量縮為 1 工具)
---

# Daily Approval Loop - Plan

## Goal Capsule

- **Objective:** 把「發現 → 初篩 → 追源草稿 → 核准 → 入庫／決策」收斂成一條每日迴路：系統做便宜的 harvest／triage／聚合，使用者每天只面對一份 action-first 的 Daily Approval Brief，用封閉動詞集合（`apply`／`research`／`park`／`skip`…）一句話核准。
- **User outcome:** 使用者不再需要自己刷 X／Substack／EDGAR 找料；每天（本機或手機）看一頁 brief，回一句話，系統走既有流程。無事時 brief 是一行 `NO ACTION`。
- **Authority contract:** 三道閘門原封不動——graph admission 必經使用者核准 exact ID；深挖 research 必經使用者點名；live 資本行動永遠人工。Brief 本身純讀，不建立 decision、不下單、不入圖。pending leads 是 Engine B 的注意力狀態（attention metadata），**不是 evidence**——它不能提高 evidence tier、不能繞過 source-trace。
- **上線目標（L2 精神）：** 本 plan 以「儘快讓迴路真的跑起來、用真實流量撞出問題」為準；v0 刻意最小，已知會壞的地方列在 Risks，撞到回頭修。
- **Stop conditions:** 若實作需要讓 routine 自行入圖、自動深挖、自動建立 decision／choice／fill、或把 lead 狀態當 evidence 用，立即停止並回報。

## 架構事實（實作前提，已驗證）

1. **Push 是常規動作（2026-07-22 使用者定案）。** 先前 session 的「不 push」是保守預設，非需求。本 plan 前提：session 收尾把 master push 到 origin；cloud routine 的 GitHub clone 新鮮度＝上次 push（正常情況 ≤1 天）。私有隔離依 `.gitignore`（`library/private/`、`.env`），push 前以 `git ls-files library/private` 為空作 sanity check，不需逐次人工確認。
2. **Engine D Decision Store 永不進 git**（`library/private/decision_lab/`）——所以**決策佇列無論 push 與否都必須經本機 MCP gateway 讀取**；這是 MCP 唯一必要的新增面。
3. **Cloud routine 連不到本機**（`crons/weekly_scan_prompt.md` 明文）：它有 GitHub clone＋web search＋MCP connector。routine 的 prompt、harvest config、leads baseline 全部從 pushed clone 取得。
4. **Engine D 的 Action Card／today 已有 redacted public DTO**（operational workflow plan R17/KTD10）——手機／雲端讀 brief 只是曝露既有 DTO，不是新引擎。
5. **既有 bug 是本迴路的直接依賴：** registry 條目缺 execution metadata（market_currency 等）時 `evaluate-signal` 在 context freeze 階段丟 `context identity does not match cohort authority`（INVALID_REQUEST），違反 operational plan R9（missing 應為 domain result）。daily loop 的 `research <lead>` 會直接撞上，必須根治。

## Product Contract（收斂版）

### Actors

- **使用者：** 每天讀 brief、回動詞；核准 Research Action；點名深挖；live 行動仍手動。
- **本機 session（Claude Code／Codex）：** 執行 `/daily-brief` skill——inline harvest、triage 新 leads、組 brief、dispatch 動詞到既有流程、收尾 commit＋push。
- **Daily cloud routine：** 每日 harvest（web）＋ 與 pushed baseline 去重 ＋ 經 MCP 讀決策佇列 → 產 GitHub Issue brief；不入圖、不建 decision、不回寫 leads 狀態。
- **本機 MCP gateway：** private decision state 的唯一遠端視窗。

### Requirements

**Leads 狀態與 harvest**

- R1. pending leads 狀態存 `library/leads/pending_leads.json`（git tracked；**本機是 authority，push 是同步機制**——cloud routine 讀 pushed baseline，不寫回）。每條 lead：`lead_id`（URL content hash）、source、url、title、published_at、first_seen、status、triage 結果、refs（research_action_id 等）。URL hash 去重，重複 harvest 冪等。
- R2. Status 是封閉狀態機：`pending → triaged_go | triaged_no_go`；`triaged_go → researching → action_prepared → applied`；任何狀態可 `parked`。不變式：**任何 status 都不影響 evidence tier**。
- R3. Harvest 來源由 `crons/harvest_config.json` 設定（可編輯，不 hardcode）：v0 = aleabitoreddit RSS（channel 標題是 "Serenity"，見 AGENTS 既知坑）＋ EDGAR watch tickers 的新 filing 檢查（沿用 `fetchers/edgar.py` 的 submissions 查詢，比對已見 accession，只記 metadata——form 類型／日期／URL——不下載全文；8-K／10-K／10-Q／Form 4 高優先，S-8 等註冊雜訊交 triage 判）。Watch 清單 v0 手動維護是刻意的；future note：自動衍生規則（active thesis ∪ Engine D active cohorts ∪ 手動追加）等「研究新公司忘了加 watch」的摩擦真實出現再做。
- R4. Harvest 失敗必須誠實：每次 run 寫 harvest_log（run_at／source／ok|fetch_failed|parse_failed／new 數量）；**解析失敗 ≠ 無新文**，brief 必須把 failed source 標出來並提示 fallback（`site:aleabitoreddit.substack.com` web search）。

**Brief 組成與動詞**

- R5. Brief 是四佇列聚合、exception-first：(a) 決策佇列＝`decision_lab today` 的 redacted DTO；(b) 入庫佇列＝pending Research Actions（`get_research_action_status`）；(c) 注意力佇列＝triaged leads；(d) **thesis 生命週期到期佇列**＝讀 `thesis/lifecycle.json` 比對到期（active 90 天／watch 30 天／review_required 每日必列），due 項目就是「需要你動作」的一種（2026-07-22 定案：從 weekly scan 移交 daily，因為到期 review 本質是核准佇列項目，不該等週一）。無事輸出一行 `NO ACTION` ＋日期。
- R6. 動詞是封閉集合並在 brief 尾附說明：`research <n|topic>`（觸發 source-trace＋lead-intake）、`apply <ra_id>`（既有核准協定）、`park <n>`、`skip`；決策類（`accept`／`reduce`／`record fill`）僅本機，維持 explicit flags。動詞不新增任何權限語意。
- R7. Triage 由 `skills/signal-triage/SKILL.md` 判準執行（LLM 便宜判斷）。本機 triage 寫回 lead 的 triage 欄位；cloud routine 的 triage 只呈現在 Issue（不回寫狀態），本機隔天 inline harvest 冪等落地同批 leads 後重 triage（便宜，且避免遠端寫入面）。Triage 刻意寬鬆，丟棄也要記 reason。

**MCP surface（9 → 10）**

- R8. 新增一個工具：`get_decision_brief`（READ_ONLY）——原樣曝露 `decision_lab today` 既有 redacted public DTO，不得繞過 redaction 另組 payload。這是唯一新增，因為 Decision Store 永不進 git；leads／config／skills 一律走 pushed clone。
- R9. 工具遵守既有 gateway 紀律：READ_ONLY annotation、錯誤不洩 private path。`docs/remote-access-architecture.md` 的工具數（10）與資料流同步更新。*(Future note：若實際使用中 clone staleness 造成 Issue 重複列已處理 leads 且干擾明顯，再評估加 `get_pending_leads` live 視窗——v0 先不加。)*

**Push 節奏與安全 gate**

- R10. Push 慣例寫進 AGENTS：session 收尾（邏輯 commits 完成後）push master；rollout 前先把現有 ahead backlog push 掉。安全依既有 `.gitignore` ＋ redaction／preservation 測試；push 前 sanity check `git ls-files library/private` 為空。`/daily-brief` skill 的 dispatch 收尾步驟含 commit＋push。

**Cloud routine 與排程**

- R11. 新增 `crons/daily_brief_prompt.md`：每日（台北 06:30，錯開週掃 06:00）執行——讀 pushed clone 的 `pending_leads.json` baseline 與 harvest config → web harvest RSS／EDGAR → 與 baseline 去重後把**新發現直接列在 Issue**（含 triage 摘要，不回寫狀態）→ 經 MCP 讀 `get_decision_brief`＋`get_research_action_status` → 產出當日 GitHub Issue（title 含日期、label `daily-brief`，附動詞說明）→ 前一日 Issue 若無人動作自動 close 並在新 Issue 註記 carry-over。**Issue 版面分兩區：「今日新增」置頂、「carry-over（第 N 天）」在後**——baseline 久未 push 時重複項全部落在 carry-over 區，真新料不被淹沒。**Issue 以日期命名＝心跳：日期空洞即漏跑證據**，weekly scan 作 backstop。MCP 連不上時決策佇列標明降級，leads／RA 佇列照常（比純 MCP 方案更耐斷線）。
- R12. Routine 與 weekly scan 分工明確（2026-07-22 重新定案）：**daily＝一切需要使用者動作的東西（含 thesis lifecycle 到期，見 R5d）＋心跳；weekly 瘦身為 topic discovery＋系統健康審查＋Stage 0 legacy gate**。兩份 prompt 互相引用此分工，避免漂移。Weekly 存廢的後續判準：跑數週後若 topic discovery 從未產出使用者想深挖的主題，屆時砍 weekly 收斂成單一 routine（用真實數據決定，不預先合併）。
- R13. Session 開頭 digest 增加一行「pending leads N 條（M 條 triaged_go）」。**前置已完成（2026-07-22，commit 553755b）：** hooks 已從 `settings.local.json` 搬到 tracked `.claude/settings.json`（clone 即生效，含 cloud session），digest 腳本已改雙通道輸出（`systemMessage` 給終端 UI＋`additionalContext` 進 agent context 並指示第一則回覆轉述——手機 App 遙控與雲端介面都靠後者，因為它們不渲染 systemMessage）。U4 只需把 leads 計數依同一模式加進 digest；Codex 端 hook 設定放 `.codex/`，呼叫同一支 Python 腳本（AGENTS 雙代理原則）。

### 前置修復（進 scope）

- R14. **修 evaluate-signal 的 partial-identity crash：** registry 有 company_id＋ticker 但缺 execution metadata 時，wide capture 與 freeze 必須完成，缺欄以既有 blocker 語意呈現（`execution_currency_missing` 等已存在於 IdentityAuthority.blockers），funded lanes fail closed；不得丟 store exception。修法以 operational plan R9／KTD3 為準（domain result，非 INVALID_REQUEST），cohort identity binding 與 context identity 的一致性規則必須在測試中明確固定。
- R15. **Registry metadata 補齊 EDGAR watch 名單：** watch 清單內的美股 ticker 補 `market_currency`／`execution_currency`／`execution_venue`（依 filing cover 逐字，如 COHR 前例）；非美股與私人公司不在 watch 名單，不硬補。

### Scope Boundaries

**Deferred（各自獨立 plan，不在本次）：** Formal Position lane 進 Engine D；自動入圖放權（tier ≤2 自動 admission）；remote 寫入 decision（record-choice／fill 上手機）；push notification；X API harvest；來源清單大擴張；`get_pending_leads` live 視窗（見 R9 future note）。
**Never：** routine 自行入圖或自動深挖；lead 狀態影響 evidence tier；brief 產生 decision／交易；Engine D 寫 Sheet；cloud routine 直接 commit／push leads 狀態。

---

## Key Technical Decisions

- **KTD1 — git push 是狀態同步機制，MCP 只補 private state。** leads／config／skills／prompts 經 pushed clone 同步（新鮮度＝上次 push）；只有永不進 git 的 Decision Store 走 MCP（`get_decision_brief`）。比 MCP-everything 方案少兩個遠端工具、少一個遠端寫入面，且 tunnel 斷線只降級決策佇列。
- **KTD2 — 本機不裝排程器。** 本機 harvest 在 `/daily-brief` 執行時 inline 跑（秒級）；每日保底由 cloud routine 承擔。兩邊 URL-hash 冪等，重複無害。
- **KTD3 — brief 的決策內容只曝露既有 redacted DTO。** `get_decision_brief` 是 pass-through；任何新欄位需求回到 Engine D 的 DTO 層做，維持單一 redaction 路徑。
- **KTD4 — Issue 是 view，json 是 state。** 狀態變更一律落在本機 pending_leads.json（經動詞 dispatch）；cloud 只讀不寫。Issue 與 state 不同步時以 state 為準。
- **KTD5 — triage 跑在誰身上由呼叫端決定。** 本機 session（Claude Code／Codex 皆可，Codex 走 OpenAI 額度）與 cloud routine 用同一份 signal-triage skill 判準；plan 不綁定供應商。
- **KTD6 — 心跳可鑑漏。** 每日 Issue 以日期命名；漏跑＝日期空洞，人眼與 weekly scan 都能發現。這是「scheduled routine 比手動開 session 不會漏」的成立條件。

## Implementation Units

### U1 — Leads 狀態模組與 harvest script

- **Files:** add `engine_b/__init__.py`, `engine_b/leads.py`（狀態機、URL-hash 去重、harvest_log、atomic 寫檔）, `crons/harvest_leads.py`（RSS＋EDGAR watch）, `crons/harvest_config.json`；add `tests/test_engine_b_leads.py`。
- **Approach:** leads.py 只依賴標準庫；RSS 解析失敗記 `parse_failed` 不拋例外；EDGAR 用 submissions JSON 比對已見 accession，只記 metadata。config 含 feed 清單（附 Serenity 註記）與 watch tickers（v0：COHR、LITE、AMAT、LRCX、AXTI、AAOI、TSEM、GFS）。
- **Tests:** 去重冪等、狀態機非法轉移拒絕、parse 失敗誠實記錄、config 缺欄 fail closed。

### U2 — 修 partial-identity crash ＋ registry 補齊（R14–R15）

- **Files:** modify `decision_lab/context.py` 或 `decision_lab/workflow.py`（依實作判斷，以最小 diff 滿足 R9 語意）, `config/company_identity.json`；modify `tests/test_operational_workflow.py`（新增 partial-metadata fixture 案例）。
- **Approach:** 固定契約——「registry 能解析 company_id＋ticker 即可完成 capture＋freeze；execution metadata 缺失是 lane blocker 不是 identity 失敗」。負向測試：partial ticker 走完 evaluate-signal 得 REVIEW card＋blockers，無 exception；既有完整 metadata 案例不回歸。
- **Dependencies:** 無（可與 U1 並行）。

### U3 — MCP gateway `get_decision_brief`（R8–R9）

- **Files:** modify `mcp_server/graph_mcp.py`；modify `docs/remote-access-architecture.md`；add/extend gateway 測試。
- **Approach:** 呼叫 Engine D 既有 brief/today 純讀入口取 DTO，READ_ONLY annotation，pass-through 不重組。負向測試：輸出不含 private path／holdings rows／credentials（沿用既有 redaction 斷言）。
- **Dependencies:** 無新依賴（既有 Engine D）。

### U4 — `/daily-brief` skill 與 session digest（R5–R7、R10、R13）

- **Files:** add `skills/daily-brief/SKILL.md`（canonical）；regenerate `.agents/skills/`、`.claude/skills/`（`python scripts/sync_agent_skills.py`）；session-start digest 擴充（實作時查現行 hook 設定，最小改動）；modify `tests/test_skill_decision_contract.py` 或新增 parity 測試；modify `AGENTS.md`（push 慣例）。
- **Approach:** skill 定義：inline 跑 `python crons/harvest_leads.py` → 對 pending 新 leads 依 signal-triage 判準 triage 並寫回 → 跑 `python -m decision_lab today --format markdown` → 讀 `thesis/lifecycle.json` 列到期項（R5d）→ 組四佇列 brief（繁中、action-first、動詞說明在尾）→ 動詞 dispatch 表（`research <n>` → source-trace＋lead-intake；`apply <ra_id>` → 既有 apply＋`scripts/commit_pending_intake.py`；`park` → leads.py 狀態轉移）→ 收尾 commit＋push（含 `git ls-files library/private` sanity check）。skill 不含政策數值、不算 sizing。**明文注意事項：decision_lab 命令只在本機執行**——雲端 session 的 clone 沒有 private Decision Store，跑了會開出一個用完即棄的空 store（不污染真 store，但產出無效且造成困惑）。digest 擴充沿用 553755b 的雙通道模式（見 R13）。
- **Dependencies:** U1、U2（research 動詞會打 evaluate-signal）。

### U5 — Daily cloud routine 與上線（R11–R12）

- **Files:** add `crons/daily_brief_prompt.md`；modify `crons/weekly_scan_prompt.md`（**移除 thesis 生命週期核查段——已移交 daily（R5d／R12），瘦身為 topic discovery＋系統健康＋Stage 0 legacy gate**，並加分工註記）；modify `AGENTS.md`（開發優先序＋operational commands＋weekly scan 描述同步）。
- **Approach:** prompt 結構仿 weekly scan（前提宣告、clone baseline 讀取、MCP 降級規則、Stage 化流程、日期心跳 Issue 模板含動詞說明與 carry-over 規則）。
- **上線 checklist（人工步驟，寫進 prompt 檔頭）：**
  1. push 現有 master backlog（首次 rollout 前提）；
  2. 使用者在 claude.ai 建 daily routine（06:30 台北）；
  3. 連續跑 3 天，每天摩擦點記在當日 Issue 留言；
  4. 第 3 天彙整回寫本 plan 的「上線觀察」節或 docs/solutions。
- **Dependencies:** U3（MCP 工具）、U4（動詞語意定案後 Issue 模板才能引用）。

## Dependency Order

`U1 → {U2 ∥ U3} → U4 → U5`。U1 先定狀態；U2／U3 可並行；U4 把本機端跑通（**此時本機迴路即可上線試用**）；U5 補雲端與手機面。

## Risks（v0 已知會壞的地方，撞到再修）

- **RISK1 — 初期流量太稀，brief 天天 NO ACTION。** 接受；這是來源清單問題不是管線問題，擴源另議。
- **RISK2 — triage 判準太鬆／太緊。** signal-triage 本來就標為拍腦袋 v0；用真實流量調。
- **RISK3 — Issue view 與 json state 漂移**（使用者在 Issue 上打勾但沒回動詞）。v0 以 state 為準＋carry-over 註記；常發生再考慮讓 routine 讀 Issue 回寫。
- **RISK4 — clone staleness 與 RSS 視窗遺漏：** 使用者若幾天沒 push，routine 會重複列已處理的 leads（冪等、僅噪音，且都落在 carry-over 區）。**真的會漏的只有一種**：長期（2 週＋）不開本機 session，RSS 文章掉出 feed 視窗後本機 harvest 永遠抓不到，唯一紀錄剩舊 Issue（保底：回來後翻 Issue 用 `research <url>` 手動撈）；EDGAR 無此問題（submissions JSON 是完整歷史，回來補跑全抓得到）。撞到頻繁再加 `get_pending_leads` live 視窗或 Issue 機器可讀區塊（R9 future note）。
- **RISK5 — 忘記 push 使迴路劣化是新的人為依賴。** 緩解：/daily-brief 收尾步驟內建 push；Issue 重複噪音本身就是「該 push 了」的可見信號。
- **RISK6 — MCP tunnel 斷線。** 只降級決策佇列；leads／RA 佇列照常（KTD1 的耐斷線紅利）。

## Verification Contract

- Targeted：`python -m pytest tests/test_engine_b_leads.py tests/test_operational_workflow.py <gateway tests>`；U2 的 partial-identity 負向測試必須先綠。
- Suite／gates：`python -m pytest`（與既有 baseline 比對）、`python scripts/sync_agent_skills.py --check`、`git diff --check`、`python thesis/preconditions.py`（應維持全綠）。
- 上線驗收（真實使用，非 fixture）：連續 3 個 routine 日產出日期心跳 Issue；`research`／`apply`／`park` 三動詞各被真實執行至少一次；harvest 失敗至少人工注入一次驗證誠實降級；Engine A 無 write path 新增（preservation 測試維持通過）。

## Definition of Done

- [ ] 本機 `/daily-brief` 一個指令產出四佇列 brief（決策／入庫／注意力／lifecycle 到期），無事輸出 `NO ACTION`。
- [ ] partial-identity ticker 走完 evaluate-signal 不 crash，缺欄以 blocker 呈現。
- [ ] MCP 10 工具：`get_decision_brief` 過測試（含 redaction 斷言），remote-access 文件同步。
- [ ] Push 慣例寫入 AGENTS，/daily-brief 收尾含 commit＋push＋sanity check。
- [ ] Weekly scan prompt 已移除 thesis lifecycle 段並加分工註記；AGENTS 的 weekly 描述同步。
- [ ] Daily routine 連續 3 天產出日期心跳 Issue（今日新增／carry-over 兩區），carry-over 與降級規則被觀察到正確運作。
- [ ] 動詞 dispatch 三條路徑（research／apply／park）真實跑通各一次。
- [ ] AGENTS 更新、skill sync clean、full suite 與 baseline 比對歸因、邏輯 commits，**master 已 push**。

## 討論定案紀錄（2026-07-22，Q&A 收斂）

規劃過程中與使用者逐題釐清、已併入上方 requirements 的決定，留此供實作者回溯「為什麼」：

- **升格 vs Engine D：** 升格是 investment SOP／L9 的 per-thesis gate（→ Formal Position）；Engine D 是 per-signal 決策介面（Probe lane：shadow／paper／有界 live range）。兩者並存。使用者不需自記升格狀態：Probe lifecycle 在 private Decision Store（`today`／`card` 可查）、thesis 標籤在 Lane Memo、gate 即時算（`checklist.py`／`preconditions.py`）。**已知落差：** Formal Position 的完整 conviction sizing 尚未進 Engine D workflow（deferred，獨立 plan）。
- **自動化不放寬入圖閘門：** 抓進來的是 Signal→Shadow（零資本），不是自動 paper。三道閘門（graph admission 核准、深挖點名、live 人工）永不自動。token 大戶（深挖 research）永遠 gate 在使用者手上；自動段（harvest 零 token、triage 便宜）不會因來源變多而爆量。
- **Push 前提（本 plan 的地基）：** 先前 session 的「不 push」是保守預設非需求。push 解禁後 git 成為狀態同步機制，MCP 增量從 3 工具縮為 1（見 KTD1）。
- **Weekly 是否保留：** 保留但瘦身（R12）。cloud routine 相對「使用者主動開 session」的價值是**節奏保證／不漏**（心跳，KTD6），不是能力。存廢後續用真實數據決定。
- **Cloud triage 為何看得到卻寫不進：** 單一寫入者（只有本機 session 寫 state）避免併發與遠端寫入面；Issue 是給人看的 view 不是機器介面；重複成本花在最便宜的 triage 層。本機隔天 inline harvest 以 URL-hash 冪等落地同批 leads 後重 triage（見 R7）。
- **Remote 兩義：** 手機 App 遙控本機 session＝碰本機 working tree 本體（有 private runtime）；claude.ai/code 雲端 session＝clone 自 GitHub、碰不到本機（無 private runtime）。故 decision_lab 命令只在本機跑（U4 明文注意事項）。
- **PR #6／Issue #2 現況（查證於 2026-07-22）：** Issue #2＝SIVE 做空指控 credibility hold（review_by 2026-08-27）。PR #6＝2026-07-17 週報（`docs/reports/weekly_scan_2026-07-17.md`），**無抽取草稿待核准**——本週唯一夠格線索（AXT-Coherent 三年期 6 吋 InP 供應協議）因當次 cloud session egress 被 403 擋、無法逐字追源，依規則不產草稿、不入圖，僅列追源未果清單。此 PR 是純報告、merge 即結案，不觸發 Stage 0 load。
