# StockBotv2 — 專案記憶 (Project Memory)

> 任何 session 在此資料夾開工前先讀本檔。這裡記錄定案、判準、與踩過的坑。

## Claude Code / Codex 雙代理相容契約

- **專案記憶唯一權威：** `AGENTS.md`。`CLAUDE.md` 只用 `@AGENTS.md` 匯入，不再複製內容；更新專案記憶只改本檔。
- **研究 skill 唯一權威：** `skills/<name>/SKILL.md`。`.agents/skills/`（Codex）與 `.claude/skills/`（Claude Code）是生成的薄轉接層，不直接手改。
- 新增 skill 或修改 skill 的 `name` / `description` 後，執行 `python scripts/sync_agent_skills.py`；交接前用 `python scripts/sync_agent_skills.py --check` 驗證兩端無漂移。
- **平台設定分開：** Codex 設定放 `.codex/`，Claude Code 本機設定放 `.claude/settings.local.json`；共用行為應呼叫同一支 repo Python 程式，不在兩份 hook 裡複製業務邏輯。
- **Local-first 方針（2026-07-26 使用者定案）：** 未特別寫 `claude.ai`／cloud 時，文件中的「Claude」一律指**本機 Claude Code session**。Daily／Weekly／todo 核准的 primary path 是本機 Codex 與本機 Claude Code 可序列互換、直接讀同一套 repo／private authorities；**cloud session＋MCP 是備援**，只使用既有受限 surface，不要求與本機 session 完全等權。
- **Provider-neutral 執行契約（2026-07-29 使用者定案）：** 本機 Codex 與本機 Claude Code 都是可互換 executor，不把 routine、研究或 pq2 完成權寫死給某一方。任一 agent 只有在使用者對 **exact pq2 item** 明確核准後，才可走完整 type-aware 動作；權限與完成狀態綁定 action type、underlying authority 與 receipt，不綁 provider。模型 recommendation／session transcript／「使用者通常會同意」都不能自我授權。
- **切換原則：** 同一 working tree 只讓一個 agent 寫入；本機 Codex／Claude Code 序列切換可沿用 `master` 與同一組 private authorities，但下一個 agent 必須重新讀 `git status --short`、`todo_pool.json`、對應 action／decision receipt，不得依賴上一個 session 的自然語言摘要。若兩邊同時工作，必須使用不同 worktree / branch；排程與互動 session 也算兩個 writer，不能重疊。交接訊息至少附目前 plan 路徑、進行中的 U-ID、`git status --short`、最後一次驗證命令與結果。
- **Session memory 不是 authority：** Codex automation `memory.md`、Codex task context 與 Claude Code transcript 都只可當 disposable advisory cache，不需同步。使用者在任一個本機 session 核准 todo 後，必須先完成 type-aware 動作並留下 underlying receipt，最後才寫 `todo_pool.log`／resolution；未寫 authority 的「已 go」不得被另一個 agent 視為完成。
- 本機開發 agent 可以是 Claude Code 或 Codex；架構中明指 `claude.ai` custom connector 的遠端流程仍維持 Claude，不因本機開發工具切換而改名。
- **Push 政策（2026-07-22 使用者定案）：** push 是常規動作——session 收尾（邏輯 commits 完成後）把 master push 到 origin，不需逐次人工確認。私有隔離依 `.gitignore`（`library/private/`、`.env`）；push 前 sanity check：`git ls-files library/private` 應為空。本機 daily scheduled task 只可經 `scripts/publish_daily_state.py` 發布 `pending_leads.json`＋`todo_pool.json`；不得用 unattended 廣泛 Git 命令碰其他檔。

### Codex custom-agent 委派契約（2026-08-01 使用者定案）

- 專案級 `.codex/agents/luna-operator.toml` 定義 `luna_operator`：使用 `gpt-5.6-luna`／`ultra`／`read-only`，只接明確、重複、可逐項驗收的機械型工作。主代理負責拆 scope、列 acceptance criteria、檢查回傳證據，並作最後判斷。
- 適合委派：repo／queue 盤點、確定性資料檢查、測試與 log 分析、pq1 原始文件追源與原子 claim 抽取、依固定清單蒐集 alpha 財務事實與反證。所有回傳都只是 review packet，不是 authority。
- 不得委派給 `luna_operator`：任何 working-tree 或 private authority 寫入、evidence tier 升級、graph admission、pq2 核准／resolve、thesis revise／retire、資本配置、live choice／fill、commit 或 push。這些仍由主代理依既有人工 gate 執行。
- 同一 working tree 維持主代理為唯一 writer。若未來確需 writing subagent，必須另建 worktree／branch、明確指定唯一 owner，且不得沿用 `luna_operator` 的唯讀角色暗示授權。

## 工作語言（繁體中文）

**與使用者的所有溝通、以及實作過程本身的敘述，一律用繁體中文——不只是最終答案，過程也是。**

- **使用者輸入可能是簡體（語音輸入所致），這不改變工作語言：** 使用者常用語音輸入，辨識結果可能是簡體字。回覆一律維持**繁體中文**，不要跟著切簡體、也不要因輸入是簡體就以為要改語言。
- **溝通與敘述：** 對話回覆、工具呼叫之間的狀態更新、步驟說明、分析、計畫、思考敘述。
- **產出物文字：** Task 的 subject/description、commit message、PR 說明、plan 檔、docs/ 報告。
- **程式碼：** 新寫的註解／docstring 跟隨該檔既有語言慣例（既有英文檔可維持英文）；面向本專案的新說明文字優先中文。
- **Skill 最終輸出**（含 last-30-days 等）翻成繁體中文。

**維持原文、不強行翻譯：** 程式識別符（變數／函式／類別名）、既定英文技術術語（going concern、sole_source、evidence tier、backlog…）、第三方 API 欄位與字串、檔名／路徑、以及引用一手文件的逐字 quote。

判準：語言規範針對「溝通與敘述」，不是把程式碼或逐字證據中文化。若發現實作過程飄成英文，視為違反本規範，切回中文。

## 定位一句話

**Engine A/B/C 研究輸入 + Engine D 決策責任 → 有根據且可控的投資決策。**

使用者提出公司、thesis 或外部 Signal → 研究 agent 結合 Engine A 的因果／證據 context、Engine B 的線索與 Engine C 的財務／市場狀態 → Engine D（Decision Lab）凍結決策當下實際使用的 context，產生可稽核的 `NO ACTION / REVIEW / TRADE / HEDGE` 與受支持部位區間。使用者保留最終接受、縮小、覆寫與手動下單權力。本機單人自用，使用者會寫 Python、碰過 API。

---

## 系統架構（四引擎／四層）

| 引擎 | 角色 | Current-state authority | 不負責 |
|------|------|-------------------------|--------|
| **Engine A** | 供應鏈、物理／關係瓶頸、claim 與 provenance | Neo4j | Signal queue、部位、價格時序、交易決策 |
| **Engine B** | 外部 Signal discovery／intake 與研究注意力排序 | 來源登記與 pending lead／Research Action | 提高 evidence tier、自動投資、graph admission bypass |
| **Engine C** | 財務、估值、市場與其他帶時戳 observation | SQLite／Postgres private runtime | thesis、持股真相、最終部位決策 |
| **Engine D** | Decision & Accountability Engine（Decision Lab）：Shadow、Coverage、Confidence、paper/live permission、Action Card、outcome | Private Decision Store；paper events 是模擬帳本真相 | 寫 Engine A、複製 Engine C current truth、取代 Google Sheet、broker routing |

### Skill 層（Claude Code / Codex 共用操作介面）
權威內容存在 `skills/` 目錄，每個 skill 是告訴研究 agent「如何使用記憶層」的操作手冊；兩端的自動發現路徑由上方轉接層提供。

| Skill | 觸發場景 |
|-------|---------|
| `skills/investment-research` | 問投資問題、評估標的、生成 thesis |
| `skills/lead-intake` | 丟來一條推文/報導/消息，要入庫 |
| `skills/blind-spot-audit` | 已有 thesis，要找反駁角度 |
| `skills/company-onboard` | 新公司尚未入圖，要找文件並 onboarding |
| `skills/signal-triage` | harvest 後判斷是否值得進自動 pq1；PASS 只授權追源／抽取，不授權入圖 |
| `skills/source-trace` | 推文／轉述／截圖／二手報導先追回原文；tier 3–4 未果隔離 |
| `skills/evidence-conflict-resolution` | EdgeAssertion 屬性衝突產 proposal；只在人工核准後寫 resolution |
| `skills/daily-brief` | 本機每日 harvest／Engine C refresh／triage／today／穩定 pq2 核准 brief |

### 決策層（Engine D — Decision & Accountability Engine／Decision Lab）

- **責任：** 將 Engine A/B/C、versioned policy 與 Google Sheet holdings 轉成可稽核的資本許可與下一步行動；保存 Signal cohort、Shadow、Coverage、Confidence Envelope、system decision、paper event、明確的 live choice/fill、lifecycle 與 outcome attribution。
- **Point-in-time contract：** 「凍結 Engine A」一律指**凍結該次決策實際使用的 Engine A context slice**，不是 snapshot／dump 整張 Neo4j。Engine D 將該 slice 與財務、價格、FX、持股、policy 的 as-of values／refs／versions 組成 content-addressed context bundle；舊 decision 永遠引用原 digest，不因 A/B/C 後續更新而改寫。
- **資本邊界：** eligible paper 可與 system decision 原子寫入；live 只輸出 supported range，必須由使用者明確接受、手動下單並回報，Google Sheet 仍是 live inventory 唯一權威。
- **Runtime：** Decision／paper facts 存於 ignored `library/private/decision_lab/`；第一筆真實事件後只允許 backup／restore與 append-only correction，不做破壞性 reset。

### 記憶層（持久知識庫）
- **Neo4j 知識圖譜（引擎A）：** 供應鏈結構、技術關係、來源可追溯的主張。Property graph，不是 tree。
- **SQLite / Postgres 財務數據（引擎C）：** 財務快照、Watchlist Gate。零安裝預設用 SQLite；設 `POSTGRES_HOST`/`POSTGRES_DSN` 切換 Postgres。SQLite authority 已移至 ignored `library/private/engine_c/`，由 `library/private/runtime_pointer.json` 指向；ETL projection 可由 tracked schema 重建，但同庫的 append-only manual observation ledger 是 private authority，刪除／重建前必須先做 recovery backup，不能假設 Git 能救回。見 [`docs/solutions/tooling-decisions/engine-c-sqlite-dual-backend.md`](docs/solutions/tooling-decisions/engine-c-sqlite-dual-backend.md)。
- **向量 RAG：** 暫用 Neo4j 內建，量大再分。

### 管道層（Engine B discovery／知識入庫的機器）
```
文件 → library/raw/ → extract.py → loader/validate.py → loader/load_to_neo4j.py → Neo4j
fetchers/edgar.py ──────↑                        engine_c/etl_yfinance.py → SQLite
遠端線索 → source-trace → prepare_research_action（server-owned review packet）
         → 使用者明確核准 ID + 一次 native approval
         → apply_research_action（filesystem-first + resumable graph write + report）
         → 本機 session 執行 scripts/commit_pending_intake.py（每 action 一 commit、整批一 push）
```
- **抽取與 DB 解耦：** `extract.py` 只輸出 DB 無關 JSON；loader 可替換。DB 選型不綁死資料。
- **fetchers（已有）：** `fetchers/edgar.py`（美股 SEC EDGAR，免費無 paywall）。
- **引擎B（X／EDGAR daily harvest 已建；trending horizon 由 weekly 負責）：** `crons/harvest_leads.py` 在本機以 X API `since_id`＋EDGAR watch 抓 metadata → triage PASS → routine 依 priority 自動 pq1（source-trace＋extract）→ prepared Research Action 才進 pq2 等使用者核准入圖。ad hoc 手機入口仍走 `skills/lead-intake`。
- **本機音訊追源：** 官方 podcast／錄音沒有 transcript 時，用 `scripts/transcribe_audio.py` 跑 `faster-whisper`；預設 CPU `small.en`，模型與完整逐字稿只存 ignored `library/private/`。ASR 只提供 timestamp locator，不自行提高 evidence tier；精確技術詞與 quote 仍須回聽核對。cloud fallback 不假設有此工具。
- **每週審查（Codex 本機排程，台北週日 04:00，`crons/weekly_scan_prompt.md`）：** 只做 topic discovery（不追源、不抽取）＋thesis lifecycle 唯讀提醒＋完整本機健康審查。可確定性維護先修；需要證據／thesis／持倉 authority 的大事才進統一 pq2。刻意與 daily 06:30 錯開，報告留 `docs/reports/`。
  - **Weekly authority hierarchy：** `AGENTS.md` 是政策 SSOT；`crons/weekly_scan_prompt.md` 是 executable runbook，只有開發／人工修 policy 時才改，weekly routine 本身不得自我改寫。`docs/reports/weekly_scan_<date>.md` 是當週 point-in-time 歷史報告，不是 current-state truth；現況仍以 leads／todo pool／lifecycle／Engine A-C-D 各自 authority 為準。
- **各類來源的 AI 抽取 instruction：** [`docs/extraction-instructions.md`](docs/extraction-instructions.md)
- **遠端存取（手機 App／web／Claude chat fallback）：** 本機 MCP server（`mcp_server/graph_mcp.py`）+ Cloudflare Tunnel + connector。十二工具 surface，Git 能力僅 leads.json 一個窄例外；daily／weekly 現行排程不需要 MCP，因為直接在本機 repo 執行。完整資料流、安全邊界、Research Action／storage 協定與跨平台限制：[`docs/remote-access-architecture.md`](docs/remote-access-architecture.md)

> MCP server 重啟程序、雲端 egress 白名單等操作細節見 [`docs/OPERATIONS.md`](docs/OPERATIONS.md)。


---

## 本檔的角色與另外兩份

`AGENTS.md` 是**政策 SSOT**：判準、契約、邊界、踩過的坑。每個 session 開工前讀本檔。

另外兩份按需載入，不必每次讀：

| 檔案 | 內容 | 什麼時候讀 |
|------|------|-----------|
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | 指令、環境變數、排程流程、harvest／MCP 操作陷阱 | 要實際執行操作時 |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 交付歷史、開放 backlog、未來想法 | 規劃或決定下一步時 |

拆分理由：本檔每個 session 完整載入，所以每加一段都在花掉未來每一次執行的 context。
判準與契約值得這個成本，指令表與交付紀錄不值得。

**新增內容放哪：** 是判準或會約束行為的規則 → 本檔；是怎麼跑的程序 → OPERATIONS；
是做完什麼或想做什麼 → ROADMAP。

---

## 現行運作契約

> 這些是**當下生效的規則**，不是歷史紀錄。交付時間與 plan 連結見 [`ROADMAP.md`](docs/ROADMAP.md)。

### 統一待辦池（廣義 pq2）

**所有真正需要使用者決策的事只有一個編號空間**——prepared RA 入圖核准、決策複查、thesis 到期、Sheet-only 持股、手動 authority。Raw／triaged leads 留在 pq1 由 routine 自動研究，不占 pq2 編號；否則同一題會在研究前與入圖前問兩次。

編號首次進池後直到 resolve 才釋放；狀態存 tracked `library/leads/todo_pool.json`，append-only `log` 保留核准與 migration 稽核。

**「等你決定」與「等事件」分離（2026-07-30）：** 池子同時裝著兩種性質不同的東西，混在一起會讓訊噪比降到約 1:1（歷來 76 個編號有 31 個被 drop）。`config/decision_blockers.json` 的 `resolution_mode` 是分類判準：`user_decision`／`awaiting_external`／`system_internal`。保守規則——**只要有一個 blocker 需要人決定，整個項目就留在決策佇列**，寧可多問也不要安靜藏起來。使用者亦可用 `pending --until/--trigger` 明確指定等待條件，優先於自動推導。

**Daily pq1 budget：** 每輪上限唯一 authority 是 `config/daily_routine.json`（目前 5，是吞吐量 cap 不是每日 quota）；排序權重唯一 authority 是 `engine_b/priority.py`。tracked thesis impact 由非 retired lifecycle ＋ non-terminal Decision cohorts 自動導出。

**待核准內容密度（2026-07-30 使用者定案）：** stable pq2 編號不只列短標題。每項先給一段 TL;DR，再明列完整公司／ticker、誰供應誰、產品／材料／技術、事件成熟度、投資意義、證據與反證限制，以及 `go` 實際授權的 action type；**不得假設使用者能從 `co:*` ID 或內部術語自行還原主詞。** 這是 `skills/daily-brief/SKILL.md` 的共用 presentation contract。

**提醒去重：** lifecycle SessionStart hook 只提醒尚未進池的新到期項目；已存在的 `thesis_lifecycle`（含 deferred）由 Daily Brief 顯示，hook 必須靜默。新提醒只走 `additionalContext` 呈現一次。

### Decision gap dispatch

`decision_review go` 的語意是把最新 decision 綁定的 proposed work order checkpoint 成 pq1 `queued`，**不是**立刻沿用舊 assessment 做 bare `reassess`。原 pq2 項目在 queued／researching／awaiting_approval 期間保持 active 但不重複詢問；只有研究未果的 parked receipt，或補缺口後產生的**新 decision receipt**才能 resolve。

Decision gap jobs 優先占用同一個 daily pq1 budget。若研究結果需要 graph admission、Engine C manual observation、thesis revise／retire 或其他 authority mutation，完整 packet 必須回 pq2，**原人工 gate 不放寬**。Live choice／fill 永遠不由此路徑推定。

### Sheet 持股覆蓋分類

`sheet_only_holding` 只針對**真正沒有任何機制負責**的持股。`decision_lab/brief.py` 的 `_sheet_only_items` 依 Sheet ticker 分三類：beta policy 涵蓋（`coverage=beta_policy`）、使用者明確不研究（`coverage=user_ignored`，登記於 `config/holdings_coverage.json`）、其餘 `coverage=uncovered`。前兩類判 `NO ACTION` ＋空 blockers，仍在 daily brief 現形但不占 pq2 編號。

**`todo drop` 對這類項目無效**——它只清當次編號，sync 會依 Sheet 持股＋無 cohort 重新推導並配新編號（2026-07-29 實測 [18]-[33] → [46]-[60]）；要真正解除必須改覆蓋分類或建 cohort。覆蓋設定檔讀取失敗一律 fail safe 退回 `REVIEW`。beta universe 的 SSOT 只有 `config/beta_policy.json`。

### Source-trace backlog 防漏

`parked` 不等同「註記後遺忘」。pq1 每次因 `isolated_tier_3`／截圖／paywall 未果而 park 時，必須留下 `trace_status`、`trace_attempts_ref`、`trace_next_trigger` 與 `trace_requires_user`。

一般 scheduled／event-triggered 重查仍屬 pq1，不占 pq2；只有需要使用者提供合法 access、核准付費或明確改變研究優先權時，`todo sync` 才建立 `source_trace_review`。該類型的 `go` 只把 exact lead dispatch 回 pq1，**不代表相信截圖、提高 evidence tier 或 graph admission**；取得原文並 prepare 後，入圖仍是另一個 `ra_admission` pq2。任何新訂閱／購買必須另列 exact 金額與方案。

**Lead 之間的關聯鍵（2026-07-30）：** URL hash 只認同一篇文章。跨文章的關聯靠 `engine_b/entities.py` 的具名標的做**確定性**比對（cashtag、`edgar:<TICKER>`、registry 反查的 `co:*`）。主題相關但無共同 ticker 的仍靠語意，`trace_next_trigger` 仍是自由文字且**沒有任何程式在評估它**——改善方向見 [`ROADMAP.md`](docs/ROADMAP.md)。

### 資本與風控

**Numeric SSOT：** `config/investment_policy.json` 與 `config/beta_policy.json`。只有 **ETF 槓桿 cap 與 5% 單筆上限**會把 live supported range 歸零，其餘曝險只記錄／警告。使用者仍可走 prepared `live_override` 留下 exact action ＋ reason receipt；系統不自動下單。

**共同可投資現金池只有一條：** `Portfolio CASH − cash floor`，供 Alpha／Beta 共用。不扣 operating reserve、alpha reserve 或 planned outflows，沒有 Sheet／household 雙 range。Alpha／Beta 如何分配由各自 campaign budget、Decision sizing、單筆上限與風控決定，**cash floor 不承擔 sleeve allocation**。cash floor authority 失效時 fail closed，不回退到百分比 reserve。

**兩個槓桿指標不得混用：** `nominal_weight` 是「投入槓桿 ETF 的資金占 NAV」（5/8% warning/cap）；`effective_weight` 是乘上 2x／3x 後的「換算槓桿曝險」（15/20% warning/cap）。面向使用者不得把前者寫成模糊的「名目槓桿」。

**Capital Authority：** 私人 Google Sheet 只保留 `cash_floor` 與 `credit_facility` 兩種 record；日常 credential scope 只有 `spreadsheets.readonly`。貸款額度、已借款、利率、計息方式、期限與還本方式獨立保存；**未動用額度不算 NAV／cash／allocation**。每次提款、標的與 tranche 都是 explicit manual review，「高信心」不構成 machine permission。

**曝險邊界：** Sheet `bucket=CASH` 列計入 NAV 但不計曝險。未知非現金持股按 unlevered direct issuer ＋ alpha exposure 誠實降級，不因缺 mapping 阻擋。`issuer_loads` 只代表 policy 已登記的 ownership look-through，輸出必標 `partial`；Engine A 上游依賴不可混成 issuer ownership。**既有 frozen decision 不回寫**，重新 reassess 才使用新 policy／calculator。

**退休貸款資本目標（2026-07-28 使用者定案）：** 使用者約 30 歲、退休目標約 60 歲；可長抱至到期的貸款資本以約 30 年後 `retirement_net_terminal_wealth` 最大化為方向，不以降低中途回撤為第一目標。契約為利息按月支付、期間不攤還本金、到期一次還本、允許投資用途。broad unlevered beta 是主要候選；daily 3x 可投資但維持衛星定位，exact review 必須扣除借款成本與到期本金比較退休淨終值，**月息若需靠賣出 beta 支付則該 tranche 不成立**。

### Beta 呈現契約（2026-07-30 使用者定案）

底層與首屏都只保存一條 `self_funded_supported_range`。自有現金可部署固定顯示 `Portfolio CASH − cash floor`，並明說 cash floor 以上為 Alpha／Beta 共用。另獨立顯示「未動用貸款額度／已借款／估計利息」，明標貸款不算自有現金。**不得用未解釋的斜線或 raw field name。**

燈號固定配文字：🟢可評估、🟡冷卻／排序中、⚪觀察、🔴資料不足／暫停新增。Beta 區先用三行 TL;DR 說明目標、今日可人工評估標的與已觸發風控；technical signal 只決定新增 timing／pace，**不因一般回檔自動賣出**。

### 技術訊號的地位（2026-08-01 實測後定案）

**訊號不得 gate 自有現金投入。** `config/beta_policy.json` 的 `signal.baseline_pace` 是不受訊號影響的例行投入下限，訊號只能在其上加碼。

**例行提醒與貸款分離（2026-08-01）：** 自有現金 baseline 每 5 個完整交易日主動提醒一次；週期以 Engine C append-only `TechnicalObservation` 的 distinct session count 定錨，不跟 RSI／MACD／tier 變化走。提醒只是人工評估 prompt，不是下單許可。貸款不在例行提醒內；提款時間表、金額、標的與 tranche 留待未來另案人工核准。

三次實測全部失敗：以訊號 gate 現金投入使終值**輸給無腦定投 8.5%**（QQQ 91.5%、SOXX 91.9%）；訊號調節借款提取**無可測得效果**；訊號決定投給哪個標的**輸給固定單押最佳標的 22%**，且三分之一時間買進 CAGR 僅 7.2% 的弱標的——「買跌最深的」會系統性把錢導向長期較弱的資產。`stretched_above_sma200` 同為未實測的推論。

因此：**未驗證的訊號機制不得覆蓋有證據的 baseline**；呈現須寫「例行投入 / 節奏 X%」而非自相矛盾的「未觸發 / 節奏 X%」。但 baseline 不等於「無論如何都投」——資料不足／stale／quarantined 時仍誠實歸零。

**台股 technical freshness（2026-08-01）：** `.TW` 的最新交易日先用 TWSE 官方 `STOCK_DAY_ALL` OpenAPI 校驗；Yahoo session 落後、官方代碼缺列或 TWSE freshness 無法取得時，該標的 technical signal 必須 `quarantined`／supported range 歸零。TWSE 的未還權 OHLC 只作最新日期與當日漲跌 reference，不得直接混入 Yahoo adjusted-close 長期序列；完整還權歷史另需明確的資料源與調整規則。

**須區分量測與訊號：** 總曝險倍數、歸零門檻、追繳門檻、利息覆蓋屬**量測**，有價值且應強化（本輪所有決策翻轉皆由此而來）；RSI／MACD／tier／pace 屬**訊號**，三次受測皆未通過。完整證據與未實作項見 [`docs/brainstorms/2026-07-31-leverage-glide-path-requirements.md`](docs/brainstorms/2026-07-31-leverage-glide-path-requirements.md)。

### 事件監控

issuer 曝險 ≥20% 且對應 series 單日報酬首次跌破 -4% 才產 ephemeral `event_search_requests`；daily agent 只做一次 WebSearch，輸出可能原因＋曝險並標未經查證，**不建 lead／decision、不進 pq1/pq2、不寫 Engine A**。需要深挖才另走 lead-intake。

### 報告留檔策略

**daily brief 不留檔**（只出在 session；稽核價值由待辦池 log ＋ leads 狀態機 ＋ Decision Store 承擔）；**weekly report 留檔**（`docs/reports/`，含無法從池重建的 topic discovery 與健康審查趨勢）。不回到 PR/Issue 形式——那會產生與池競爭的第二個狀態源。

**Weekly authority hierarchy：** `AGENTS.md` 是政策 SSOT；`crons/weekly_scan_prompt.md` 是 executable runbook，只有開發／人工修 policy 時才改，**weekly routine 本身不得自我改寫**。`docs/reports/weekly_scan_<date>.md` 是當週 point-in-time 歷史報告，不是 current-state truth。

---

---

## 來源登記表（一手來源優先）

通用搜尋（Tavily 等）只配 LLM 品質評分 gate，用在第三層。**機器可執行的路由與未果處置唯一權威是 [`skills/source-trace/SKILL.md`](skills/source-trace/SKILL.md)**；快速記憶：美股走 SEC EDGAR，台股走公開資訊觀測站（含月營收揭露），A股走年報／問詢函／海關數據，技術走 arXiv／OFC/ECOC／專利。各市場都優先做上下游上市公司交叉驗證。

出投資建議前必看的核驗清單五項：客戶集中度、毛利率／產能利用率、backlog／營收結構、稀釋、估值壓力。

## v0 Schema

設計原則：表的「形狀」鎖死，字彙（type/relation/層級）用對照表留鬆；屬性按 L4「物理 / 關係 / 時變」三分歸位。完整欄位表、vocab、claims 格式、sole_source 驗證規則：見 [`schema/graph_schema.md`](schema/graph_schema.md)。

**快速記憶：**
- **圖公司 ID（`co:*`）不要憑公司名猜。** 唯一權威是 `config/company_identity.json`，由 `identity/registry.py` 載入；loader 的 `TICKER_MAP` 只是由同一 registry 生成的相容介面。查圖前先查 registry，或用 `query/health_audit.py` 的 `COMPANY_IDS_CYPHER` 列出圖中 Company 再比對。例：Sivers 是 `co:sivers_semiconductors`，不是 `co:sivers`（2026-07-21 週掃即因猜 ID 未命中而漏掉 Sivers 的圖內比對）。ID 未命中時要區分「ID 沒解析對」與「圖中真無此公司」，不能默默跳過。
- **Sivers 三層 symbol 不可混用：** Engine C／研究行情是瑞典主掛牌 `SIVE.ST`（SEK）；Google Sheet／execution authority 保留 `FRA:2DG`（EUR）；Yahoo provider syntax 由 `identity/execution.py` 正規化成 `2DG.F`。快照對外仍回 canonical `FRA:2DG`，不得把瑞典 ADV／currency 冒充 Frankfurt live liquidity。
- node 帶內在慢變屬性（`ramp_difficulty_intrinsic`、`concentration_score` 為衍生值非手填）
- edge 帶關係型屬性（`substitutability`、`sole_source`、`structural_lead_time_weeks`、`ramp_execution`）
- `confidence` 只在不同 `origin_event` 之間累加（同一法說會多份摘要 = 一個 origin_event）
- `sole_source` 需客戶端或第三方印證；供應商自稱 → `verified_by_absence`（weak，≤0.5）
- `consensus_coverage` / 股價 / 財務數字 → 不進圖，進引擎 C（SQLite）

### 報告產出三級模板
1. **Directional Lane Memo**(先給方向):一句 thesis → 需求驅動 → stack 摘要 → 主瓶頸 → 最強證據 → 什麼會推翻它 → 接下來盯什麼 → **variant perception(市場現在信 X,本 thesis 認為 Y,催化劑 Z)**
   - Lane Memo 是方向備忘,**不是可操作的投資建議**。財務核驗清單(5 項)是升格到 Watchlist 的 gate,不是 Lane Memo 的 gate。
   - `variant perception` 是**必填欄**,不是選填。缺這一段的 Lane Memo 不能升格(無論其他分數多高)。
   - **Variant perception 的正確操作定義:「當前股價/估值隱含的假設是 X,本 thesis 認為真實情況會是 Y,催化劑 Z 會讓市場重新定價。」** 重點是股價說什麼,不是「多數人信什麼」——市場可以一半信 X、一半信 Y,但若股價仍以 X 的假設定價,信 Y 且 Y 對就有 alpha。可從 forward P/E / EV/Sales / 分析師共識估值推斷股價的隱含假設。
2. **Watchlist**(thesis 成立後才給名字):每檔附 role / 為何重要 / 已確認 / 待驗證 / 主風險
   - **升格條件(全部滿足才能升格):**(a) Lane Memo 評分通過失敗閾值;(b) variant perception 已明確寫出;(c) 財務核驗清單 5 項完成(客戶集中度 / 毛利率趨勢 / backlog / 稀釋 / 估值壓力)。
3. **Underwrite Sheet**(單一標的深挖)

每份 thesis/claim 必帶 `disproof_condition`(可證偽是一等公民)。thesis 生命週期:`active` → 定期核查 disproof 條件 → 條件觸發 → 強制 review → `retired` 或 `revised`。欄位存在不等於流程存在;disproof 條件觸發時必須有明確的下一步動作(見 L7)。

## 踩過的坑 / 通用判準 (Lessons)

> **引用慣例（對使用者輸出時）：** 使用者記不住 L 編號對應。任何回覆或報告提到 L1–L10 時，
> 該編號第一次出現必須括號備註一句是哪條判準，例如「L7（thesis 生命週期：disproof 條件要附
> 核查頻率 + 48h 觸發動作）」、「L8（來源獨立性：供應商自報不能當 sole_source 獨立佐證）」。
> 同一份輸出內重複出現同編號可不再備註。

### L1 — 不要為了「少裝一個系統」而用不成熟工具去做專案核心
**事發:** 一開始為了「單一系統省維運」推薦 Postgres+pgvector+**AGE** 做知識圖譜。但 AGE 是整個棧裡最不成熟的一塊,而知識圖譜是本專案最核心的部分 → 等於用最弱的工具做最重要的事。後修正為 Neo4j。

**通用判準(下次這樣想):**
1. 先問「**這個元件是不是專案的核心 / 皇冠寶石?**」核心元件 → 優化**能力、生態系成熟度、可觀測性(尤其視覺化/人工 review)**,而不是優化「系統數量」。
2. 「少一個系統」這個好處,在**本機/單人/Docker** 情境下其實很廉價,不該拿它去換核心能力。只有在多人維運、雲端成本、SRE 負擔重時,「系統數量」才是該優化的目標。
3. 需要**人工 review / 持續成長**的資料結構 → 視覺化能力是硬需求,選型必須把它當一等公民。
4. polyglot(多種 DB 各司其職)對「質化知識 + 量化數字」雙軌系統是**正確架構**,不是過度設計。別用「統一技術棧」當反射性理由。

### L2 — 不要在動工前追求「完美 schema」
v0 schema 的對錯只有真實資料能驗證。凍結一個會壞的 v0 → 用真實資料撞它 → 撞出的洞才是真需求。判準:「現在搞錯、以後要搬全部資料才能修」的決定才現在想清楚(表的形狀);「以後加一列設定就能補」的(字彙)直接動工讓資料教你。

### L3 — 別讓 DB / 框架的選型卡住垂直切片
抽取層輸出 DB 無關 JSON,選型隨時可換。先動工跑出第一批真實抽取結果,比白板上多論證兩週更有價值。Agent 框架(LangGraph/CrewAI)等流程穩了再包,起步用純 Python 函式 + 簡單佇列。

### L4 — 屬性歸位:物理 / 關係 / 時變 三分(schema 建模鐵律)
**事發:** 評估 chokepoint-atlas 給的 `ComponentNode` 五個瓶頸欄位(concentration / substitutability / ramp_difficulty / demand_proof_level / consensus_coverage)。它們長得像同類,實際分屬三種物件;作者全塞進一個 node,是因為他的 skill 無狀態、不在乎持久化。我們的庫會長大、要 review、要 join 時間序列,混在一起會爛。

**三連問判準(決定一個屬性放哪):**
1. **換掉關係另一端,值會變嗎?** 不變 → node;會變 → edge。
2. **值會隨時間變嗎？** 會 → 不是靜態圖屬性，是「帶時戳的觀測」（進 SQLite，不進圖）。
3. **講的是物理現實,還是證據強度 / 市場認知?** 後兩者 → 是 metadata 或市場狀態,不是實體屬性。

**結論：** 品類集中度/內在量產難度 = node；可替代性/sole-source/lead-time/供應商 ramp 執行力 = edge；需求證據強度 = 證據 metadata 掛在主張上；市場擁擠度 = 時變觀測進 SQLite。
**一句話：瓶頸的 alpha 大半在邊上，不在點上。**

### L5 — chokepoint-atlas / serenity-skill 是方法論藍圖，不是相依套件
兩者都是純 prompt 的研究方法論 skill，沒有持久化知識庫。**抄骨架（stack 分層、role 分類、證據四階、output-formats 當報告模板），不裝套件、不綁相依。** 它們補的是「怎麼想」，我們專案補的是它們缺的「記得」（持久化知識庫）。注意是**單一 lens**（偏小市值瓶頸獵手），當眾多視角之一，別讓系統世界觀被綁死。

**已評估、可撿的零件：**
- serenity-skill 的 `market-source-playbook` → 已併入上方「一手來源」登記表（尤其台股 MOPS/月營收）。
- serenity-skill 的 `bottleneck-scorecard.json` → **留給引擎C 參考**，不是引擎A 要用的。

### L6 — 第一次真實抽取撞出的 schema/pipeline gap

**事發：** 用 Coherent Q3 FY2026 法說會 CPO 段落跑完 extract → validate → load → Browser review 後發現。

**Gap 1 — Claim 節點沒有 `name` 欄位：** loader 在寫入 Claim 時自動從 `statement` 截前 30 字填成 `name`。

**Gap 2 — `source_ids` 是文件內局部 ID，跨文件後無法追溯：** source ID 改成全域唯一格式 `<doc_id>_s<N>`（例：`coherent_q3fy26_s2`）；或把 sources 寫成 Neo4j 節點（`Source` label）。

**Gap 3 — `ABOUT` 邊類型未在 `vocab.json` 登記：** 在 `vocab.json` 的 relation 清單補上 `about`；同步更新 `loader/validate.py`。

**Gap 4 — LLM 從類別詞推斷出具體產品節點（幻覺型態）：** quote 只說「data center interconnect 需求強」，LLM 自己推出 ZR/ZR+ 節點。修法：`prompts/extract_system.md` 加規則「具體型號/公司名必須在 quote 裡逐字出現」。

**通用判準：**
1. Schema gap 只有真實資料撞上去才會現形（L2 再次驗證）。
2. 局部 ID 在單文件內沒問題，跨文件 MERGE 後會命名空間衝突。
3. LLM 最常見幻覺型態：從類別詞推斷具體實體。review 時重點抽查「具體型號/公司名是否逐字出現在 quote 裡」。

### L7 — Thesis 生命週期:`disproof_condition` 是欄位,不是流程
**判準:** 光是填 `disproof_condition` 不夠。欄位有填但沒有後續流程,等於貼了一個永遠不會響的火警警報。

**Thesis 生命週期定義:**
- `active`:thesis 成立,定期核查 disproof 條件(建議每季一次)
- `watch`:有 leading indicator 朝 disproof 方向移動,升高監控頻率
- `review_required`:disproof 條件已觸發,強制 review(不能繼續持有不檢查)
- `retired`:確認 thesis 失效,出場並記錄推翻原因
- `revised`:修正後的 thesis 成立,重新進入 `active` 並更新 disproof 條件

**何時會爆:** 每條 thesis 的 `disproof_condition` 應附「核查頻率」與「觸發後 48 小時內要做什麼」。沒有這兩個欄位,生命週期只是一張圖。

### L8 — 自我報告確認偏誤:供應商的法說會不能作為「自己是瓶頸」的獨立佐證
**事發:** 計畫用 Lumentum 法說會作為「Lumentum 是 CPO 外部雷射 sole_source」的主要佐證。但 Lumentum 在法說會裡天然會強調自家不可替代性;這份文件不是獨立證據,是當事人陳述。

**判準:**
1. **來源獨立性檢查(多文件入圖前):** 文件選源清單中,至少 3 個不同 `origin_entity`。「被分析的公司自己的文件」只能算佐證,不能算主要確認來源。
2. **`sole_source` 確認來源必須是客戶端或第三方:** 供應商自稱 sole_source → `verified_by_absence`(弱)。客戶在法說會中說「目前只有一個供應商」、或第三方產業報告列供應商名單只有該公司 → 才能考慮 `verified_by_search`(強)。
3. **圖裡的交叉驗證:** 若某條 `sole_source=true` 的邊,其所有 source_ids 的 `origin_entity` 全是同一家供應商,標記 `sole_source_evidence_quality: weak`。

### L9 — 上游三引擎匯流至 Engine D 的前置條件（Engine C 與 formal 投資建議開放前必做）
**Engine A→C join key：** Engine A 的圖節點（如 `co:coherent`）和 Engine C 的財務數字（Coherent 的毛利率）要能自動對齊，需要共同 ID（如 ticker `COHR`）。join key 由 `config/company_identity.json`／`identity.registry` 維護（靜態 lookup，不用 LLM 推斷）；loader 的 `TICKER_MAP` 由此生成。私人公司映射到 `None`（不是空缺，是明確標記）。

**投資諮詢開放的三個前置條件（全部滿足才開放）：**
1. 第二條垂直切片必須是**非 AI / 非 CPO** 主題，且跑通相同的 extract → thesis → 評分流程。
2. thesis→部位的最小規則已定義（進場條件 / 單檔上限 / 持有期 / thesis 失效即出場），哪怕是人工執行的規則。見 [`docs/investment-sop.md`](docs/investment-sop.md)（`thesis/preconditions.py` 的 `_check_investment_rules()` 依賴此檔）。
3. 財務核驗清單 5 項（客戶集中度 / 毛利率趨勢 / backlog / 稀釋 / 估值壓力）已能一鍵從 Engine C 查出，並且必須在 Watchlist 升格前執行。

### L10 — 早期資料庫以 correctness 優先，不背錯誤相容包袱

目前圖譜與資料量仍小，schema／attribute／ID 設計的 refactor 成本很低。遇到 provenance、資料正確性或安全邊界等高風險問題時，**允許直接改 schema、搬移／重建／覆寫既有資料與調整介面**；不要為了保留已知不正確的相容性而疊 workaround。仍須保留 Neo4j dump／資料備份、dry-run、migration manifest、reconciliation 與測試，確保變更可驗證、可回復。此授權不等於任意擴 scope；只用於修正已確認的高風險設計問題。

### L11 — 自己引用的「事實」要套跟圖裡 claim 同一套追源紀律（尤其審計／法律術語）

**事發（2026-07-20）：** 追 SIVE 的 Ningi 做空 audit 時，把「公司／Board 在 2025 年報**自揭** material going-concern uncertainty」誤述成「**審計出具** going-concern 保留意見」，還在 audit ledger／trace 報告裡標成「公司 tier-1 審計佐證」。實際來源只是二手聚合新聞的措辭「auditor going-concern qualification」＋ 自家二手 memo，沒追到逐字一手。諷刺的是當下正在執行 source-trace、正在替 SIVE 掛 credibility hold——對圖裡的 claim 嚴格追源，對自己口頭引用的事實卻放鬆。被使用者追問「這是哪份文件」後，才逐字核 AR PDF（Deloitte 簽證）發現落差：一手只支持「公司自揭 material uncertainty」，`qualified opinion`／`material uncertainty related to going concern` 等審計正式用語在可抽文字中為 0。

**通用判準（下次這樣想）：**
1. **具體審計／法律術語的措辭精度本身就是一個 claim。** qualified opinion、going-concern qualification、restatement、default、fraud、sole_source 這類詞，必須一手核對、不能沿用二手框架。「公司自揭 material uncertainty」≠「審計出具保留意見」，強度與責任主體都不同。
2. **對自己要輸出的事實，套用跟圖裡 claim 同一套 tier 與追源紀律。** 方向「感覺對」、剛好嵌得進已成形的敘事時，恰恰最該起疑（確認偏誤）；別對外部 claim 嚴、對自己引用鬆（雙重標準）。
3. **多個二手都這樣說 ≠ 一手已證實。** 它們可能同源於一個原始誤述（假交叉驗證）；見 L8（來源獨立性：供應商／單一來源自報不算獨立佐證）與 source-trace 的 tier 3–4 隔離原則。
4. **追源前先 grep 自家庫。** 一手常常已 ingest 在手邊（此例 raw excerpt 裡其實寫的是中性的「prepared on a going concern basis」＋一個風險段標題，早該提醒我那跟「審計保留意見」不是同一件事）。

---

## 文件化學習

踩過的坑與設計決定沉澱在 `docs/solutions/`（按問題類型分類，帶 YAML frontmatter 可搜尋：`module`, `tags`, `problem_type`）；共用領域詞彙見 `CONCEPTS.md`。

**遇到「某個事實塞不進既有欄位／狀態／關係」時先讀 [`docs/solutions/architecture-patterns/closed-vocabulary-registry.md`](docs/solutions/architecture-patterns/closed-vocabulary-registry.md)。** 它列出每個封閉字彙住在哪、能不能擴充、以及擴充要改 config 還是改 code，省去逐一讀 Python 才知道邊界的成本。判準是 taxonomy（世界會長出新品類→字彙留鬆，放 `config/`／`schema/`）vs contract（刻意有限→打開它是 bug）。⚠ 新增 `config/*.json` 必須同時在 `.gitignore` 補 `!config/<name>.json`，否則 fresh clone 與另一個 agent 會缺檔而靜默失效；`tests/test_config_tracking.py` 是這道剎車。

---

<!-- ===== 自訂：Skill 輸出翻譯（2026-06 加） ===== -->
## Skill 輸出語言
併入上方「## 工作語言（繁體中文）」——Skill 最終輸出（含 last-30-days）一律翻成繁體中文；整個實作過程亦同。
<!-- ===== 自訂結束 ===== -->

## Imported Claude Cowork project instructions
