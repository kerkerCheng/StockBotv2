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

### Codex sandbox／private authority 整合契約（2026-08-25 使用者定案）

- **`workspace-write` 是路徑邊界，不是「repo 內所有 OS 能力都可用」。** 一般 repo 檔案可在 sandbox 內讀寫；但命令即使只碰 repo 內路徑，只要還會呼叫 Windows identity／ACL（`whoami`、`Get-Acl`、`icacls`）、credential store、網路、child shell、`.git`，或 permission profile 對該子路徑有更窄限制，仍可能需要 outside-sandbox exact rule。`library/private/` 雖在 repo 內，開啟 authority 前會驗 owner-only ACL，所以屬 capability-sensitive path。
- **任何 unattended routine 的 executable surface 變更都要做 sandbox impact review。** Daily、Weekly、todo 核准、publisher 或其他排程只要新增／改名 CLI、subcommand、參數前綴，或讓原命令開始讀寫 private authority／網路／OS security API，必須在**同一個 change**完成：①列出 path＋side effect＋OS/network capability；②更新 canonical skill／prompt 與 `docs/OPERATIONS.md`；③需要越界時新增最窄 `.codex/rules/*.rules` exact prefix；④更新 permission contract test，明確斷言允許項與禁止的相鄰動詞；⑤用 scheduled task 的相同 sandbox／exact command 跑一次端到端 smoke test。不能因目標檔「在 repo 裡」就省略這份 review。
- **排錯先看 command surface，再碰 ACL 或要求重啟。** `PrivateStorageVerificationUnavailable` 表示目前執行環境無法完成驗證，不等於 ACL invalid。固定順序是：確認 exact CLI／subcommand → 查它是否出現在 rules → 比對 sandbox 內外的 verification status → 只有 status=`invalid` 才修 ACL。重啟只會重新載入**已存在**的 rule，不能補上一條根本沒寫的 rule；rule 缺漏時不得把重啟當修復。
- **不得用 broad permission 掩蓋整合缺口。** 不放行整個 Python、PowerShell、Git、`engine_b.todo` 或 working tree；只放行能由既有人工 gate、action type 與 receipt 約束的最窄 command prefix。若無法把副作用縮到可安全 allowlist 的入口，就保留互動 approval，不加入 unattended rule。

### Codex custom-agent 委派契約（2026-08-01 使用者定案）

- 專案級 `.codex/agents/luna-operator.toml` 定義 `luna_operator`：使用 `gpt-5.6-luna`／`max`／`read-only`，只接明確、重複、可逐項驗收的機械型工作。`ultra` 經 2026-08-01 實際 spawn 驗證不受 Luna runtime 支援；`max` 是目前最高可用 effort。主代理負責拆 scope、列 acceptance criteria、檢查回傳證據，並作最後判斷。
- **預設關閉、每次明確 opt-in（2026-08-02 使用者定案）：** 跨 session 入口是 `$luna-reviewer ...` 或 `Luna reviewer：...`（半形冒號亦可）；只有該次指令啟動，完成後自動退出。未出現明確入口時不得因工作看似機械、便宜或適合平行化而自行派 Luna。完整分工與 pq1／alpha 路由以 `skills/luna-reviewer/SKILL.md` 為準；它只啟動既有 `luna_operator`，不是第二個 agent。
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

使用者提出公司、thesis 或外部 Signal → 研究 agent 結合 Engine A 的因果／證據 context、Engine B 的線索與 Engine C 的財務／市場狀態 → Engine D（Decision Lab）凍結決策當下實際使用的 context，產生可稽核的**瓶頸度排序**（以股票為單位、附最弱軸與 disproof）與「今天要不要複查」的注意力標記。**系統不給部位尺寸**——買多少、什麼時候買由使用者在買入前自行判斷，並自行手動下單。本機單人自用，使用者會寫 Python、碰過 API。

---

## 系統架構（四引擎／四層）

| 引擎 | 角色 | Current-state authority | 不負責 |
|------|------|-------------------------|--------|
| **Engine A** | 供應鏈、物理／關係瓶頸、claim 與 provenance | Neo4j | Signal queue、部位、價格時序、交易決策 |
| **Engine B** | 外部 Signal discovery／intake 與研究注意力排序 | 來源登記與 pending lead／Research Action | 提高 evidence tier、自動投資、graph admission bypass |
| **Engine C** | 財務、估值、市場與其他帶時戳 observation | SQLite／Postgres private runtime | thesis、持股真相、最終部位決策 |
| **Engine D** | Decision & Accountability Engine（Decision Lab）：Shadow、Coverage、五軸 Confidence、瓶頸排序、NAV 比例呈現、outcome | Private Decision Store | 寫 Engine A、複製 Engine C current truth、取代 Google Sheet、broker routing、**任何部位尺寸** |

### Skill 層（Claude Code / Codex 共用操作介面）
權威內容存在 `skills/` 目錄，每個 skill 是告訴研究 agent「如何使用記憶層」的操作手冊；兩端的自動發現路徑由上方轉接層提供。

**這裡不重抄 skill 清單與觸發場景**——每個 `skills/*/SKILL.md` 的 `description` frontmatter
就是權威，兩端 harness 都會自動載入。曾經在此維護一張表，結果新增 `luna-reviewer` 後沒同步，
表上長期少一個（2026-08-19 發現）。同理適用於任何 repo 裡已有結構化來源的清單：
**清單會腐壞，判準不會**（見「現況數字會過期，判準不會」）。

### 決策層（Engine D — Decision & Accountability Engine／Decision Lab）

- **責任：** 將 Engine A/B/C、versioned policy 與 Google Sheet holdings 轉成可稽核的**瓶頸度排序與研究缺口**；保存 Signal cohort、Shadow、Coverage、五軸 Confidence、system decision、明確的 live choice/fill、lifecycle 與 outcome attribution。
- **Point-in-time contract：** 「凍結 Engine A」一律指**凍結該次決策實際使用的 Engine A context slice**，不是 snapshot／dump 整張 Neo4j。Engine D 將該 slice 與財務、價格、FX、持股、policy 的 as-of values／refs／versions 組成 content-addressed context bundle；舊 decision 永遠引用原 digest，不因 A/B/C 後續更新而改寫。
- **資本邊界（2026-08-28 定案）：** Engine D **不產生任何部位尺寸**。live choice 的尺寸來源一律是使用者，系統只負責記錄，並在記錄時硬擋三個真實資本上限（5% 單筆 NAV、ETF 槓桿 nominal／effective）＋凍結快照七天時效。手動下單與回報仍由使用者執行，Google Sheet 仍是 live inventory 唯一權威。
- **Runtime：** Decision facts 存於 ignored `library/private/decision_lab/`；第一筆真實事件後只允許 backup／restore與 append-only correction，不做破壞性 reset。U7 之前的 `paper_events`／`live_supported_range`／`axis_ceiling` 欄位仍在歷史紀錄中可讀，但不再增長也不回寫。

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
- **每週審查（Codex 本機排程，台北週日 04:00，`crons/weekly_scan_prompt.md`）：** 只做 topic discovery（不追源、不抽取）＋thesis lifecycle 唯讀提醒＋完整本機健康審查。可確定性維護先修；需要證據／thesis／持倉 authority 的大事才進統一 pq2。刻意與 daily 06:30 錯開，報告留 `docs/reports/`。authority hierarchy 見「報告留檔策略」。
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

### ⚠ 現況數字會過期，判準不會（2026-08-19 定案）

**任何「目前 N 筆」「至今 0／8」「從未發生過」型陳述，在文件裡都是會腐壞的快照。**
判準寫進文件是對的（它不隨時間變），**現況數字寫進文件是錯的**——它會在某天悄悄變成假的，
而讀者無從察覺。

實測代價（2026-08-19 一天內兩次）：① ROADMAP 寫著「`live_choices`／`live_execution_reports`
仍為 0 筆——live 這條路徑從未被走過」，agent 直接引用它告訴使用者「這條路徑從未被走過」，
但使用者前一天就走完了全鏈；② ROADMAP 寫著 `commercial_maturity` 的缺口是「缺人去讀年報」，
agent 差點照做，實測後發現 7 個積壓沒有一個是讀年報能解的。

**規則：**
1. 政策檔與 ROADMAP 陳述現況時，**必須附上查證命令或 authority 路徑**，讓讀者能一行驗證，
   而不是相信文字。例：不寫「`live_choices` 為 0 筆」，寫「`live_choices` 筆數見
   `library/private/decision_lab/decision_lab.db`，查證：`select count(*) from live_choices`」。
2. **引用自家文件的現況陳述前，先跑那條查證命令。** 這是 L11 第 2 點（別對外部 claim 嚴、
   對自家文件鬆）的直接應用；兩次事故都是 30 秒內可否證。
3. Lesson 的「事發」段落是**歷史記錄**，其中的數字是當時實測值，**不因現況改變而更新**；
   但必須帶事發日期，避免被誤讀成現況。
4. 數字若確實需要常駐可見，**做成會自己出現的計數器**（如 daily brief 首屏的「非零 live 區間／
   已量測 outcome」），不要靠文件段落——L14 已經寫過「真正的防呆是會自己出現的常駐計數器，
   不是要人讀的段落」。

---

## 現行運作契約

> 這些是**當下生效的規則**，不是歷史紀錄。交付時間與 plan 連結見 [`ROADMAP.md`](docs/ROADMAP.md)。

### 統一待辦池（廣義 pq2）

**所有真正需要使用者決策的事只有一個編號空間**——prepared RA 入圖核准、決策複查、thesis 到期、Sheet-only 持股、手動 authority。Raw／triaged leads 留在 pq1 由 routine 自動研究，不占 pq2 編號；否則同一題會在研究前與入圖前問兩次。

編號首次進池後直到 resolve 才釋放；狀態存 tracked `library/leads/todo_pool.json`，append-only `log` 保留核准與 migration 稽核。

**`go` 的語意＝推進到下一個人工 gate（2026-08-30 使用者定案）：** 使用者的 `go` 不是
「把這題排進佇列」，是「授權你往下走，直到撞上我下一個需要授權的 gate」。排入 pq1、
checkpoint、reassess 都只是路上的簿記；**互動 session 收到 go 就在當次把研究做到產出
packet（新 pq2 編號）或誠實 park 為止**，不得 dispatch 完就停。無人值守排程受 budget cap
約束可以只做一段，但未完成的必須留在佇列由下一個執行者接續（provider-neutral），
不得把「已排入」回報成「已推進」（L13：驗收是產出出現在下游手上）。

**建議只由 pool ground truth 導出＋必過 L14（2026-08-30 使用者定案）：** 任何 agent／routine
對 pq2 編號給處置建議前，適用三條硬規則。事發：2026-08-30 weekly 對八個編號建議 `drop`，
聲稱「來源已停止產出」——實測 `source_cleared` 是 **0/8**，其中兩項是等事件、一項是使用者
明示 defer；同晨 daily 又對其中三項建議 `go`，兩份排程直接互相矛盾。
1. **推薦 `go` 前必須答得出「go 會讓哪個數字變」**（L14）。receipt 已判定 bounded research
   解不了的（需使用者 scope 決策、需世界先發生某事），不得推薦 `go`——改建議
   `pending --trigger`，或把真正要的 scope 問題直接問出來。「go 了沒用」的每一次
   都是這條沒守。
2. **推薦 `drop` 前必須查 pool ground truth**（`source_cleared` 實值＋`waiting_on`＋
   `deferred_at`），並附查證命令。collector 仍會重新推導的項目 drop 只會換號重生
   （`sheet_only` [18]-[33]→[46]-[60] 先例）——這種項目的正確建議是修 collector 端分類，
   不是叫使用者 drop。
3. **分工：weekly 只發現、不處置。** 週報對 pq2 至多列「疑似 stale——待互動 session 以
   ground truth 驗證」，不得輸出 go／drop 清單；處置建議只由讀得到 pool 現值的
   daily／互動 session 給出。
**收尾建議摘要是義務：** 每個研究段落、daily／weekly 報告與較長的互動回覆，結尾必附
「建議摘要」——`go`／`drop`／`pending`／不動各列編號＋一句理由，**最後一行單獨給
可直接複製的批次指令**（如 `252 253 256 257 go 255 pending`），使用者不回讀全文
即可複製回覆（2026-08-30 使用者定案）。

**授權載體唯一＝pq2 編號（2026-08-30 使用者定案，取代所有口頭授權）：** 任何需要使用者
核准的**研究與 authority 動作**——研究工程（大項）、終局 cohort 的重建（`evaluate-signal`
建新 cohort）、sub 補值這類 graph-write 研究——**一律先以 `todo add` 鑄成 `manual` 型 pq2
編號再請求核准**；hint 必須寫成決策行（`go`＝exact 動作；不含＝相鄰排除）。口頭「可以做」不
構成授權管道；收尾建議摘要只得引用編號，不得出現「口頭指示即可」類措辭。理由：使用者的
核准介面收斂為唯一一種（編號＋`go`），終局 cohort 被收集端正確排除不是例外的藉口——
收集端不鑄的號，提案端自己鑄。

**⚠ 系統開發項不走 pq2，唯一載體是 [`docs/ROADMAP.md`](docs/ROADMAP.md)（2026-08-31 使用者
定案，修正 08-30 版本）：** 原句把「機制／判準實作」也列進 pq2，那是錯的。**改動的是程式、
config、schema 或呈現邏輯，而不是圖／Engine C／thesis／資本裡的任何一筆事實 → 它是開發項，
進 ROADMAP 的「開放 backlog」或「未來想法」，不鑄 pq2 編號。**

判準一句話：**`go` 之後改變的是「我知道什麼」還是「系統怎麼運作」？** 前者是研究（pq2），
後者是開發（ROADMAP）。邊界案例照這句判——例如「補某條邊的 substitutability」改變的是圖裡的
事實，是研究；「改 `rank_bottlenecks` 的排序鍵」改變的是系統行為，是開發，即使兩者都會讓
排序表變樣。

理由不是分類潔癖，是**兩種東西的決策資訊完全不同**：研究項要的是「證據夠不夠、授權到哪」，
一行決策行就夠；開發項要的是「這會讓哪個數字變、驗收條件、與其他開發項的相對優先序」（L14
第 5 點），而那些**只有在 ROADMAP 的表格裡才排得出來**——擠進 pq2 的 hint 一行寫不下，也
無法與其他 backlog 項比較。實測：2026-08-31 之前約 10 個開發項走過 pq2（[270][304][305][306]
[315][321][322][323][324][329]），每一個都稀釋了同一份待辦清單的訊噪比，而使用者真正要在
pq2 決定的只有研究與 authority。

開發項的核准仍然存在，只是形式不同：**使用者指著 ROADMAP 的項目說要做**，或在對話中直接
要求（適用上面「使用者主動指示＝已授權」）。系統主動提出的開發構想寫進 ROADMAP 待排程，
**不主動要求 `go`**——它會在下次規劃時被一起看，而不是插隊進每日核准迴路。

四個 authority gate（graph admission、Engine C 寫入、thesis mutation、live）不因此改變：
開發項落地後若要動圖或 authority，那是另一個 pq2 編號。
**使用者主動指示＝已授權（2026-08-30 補）：** 使用者口頭／文字請求的工作，鑄號只為稽核
（受理時即以 `go` resolve，receipt 註明使用者指示語境），**不得回頭再請求一次 `go`**——
重複要核准是介面失敗。`go` 請求流程只適用於**系統主動提案**的項目。四個 authority gate
（graph admission、Engine C 寫入、thesis mutation、live）不因此放寬：使用者指示的研究
產出若要入圖，admission 編號照鑄照問——那是新的決策點，不是重複請求。

**Onboard 也走 pq2（2026-08-29 使用者定案）：** 使用者對系統的核准介面收斂為**唯一一種——pq2 編號＋`go`**。新公司 onboard 不再是獨立的對話流程審批：發現方（自主迴圈、routine 或互動研究）把 registry 增列與首批 extraction 打包成 prepared RA 取 `ra_admission` 編號，packet 內必含 L8 來源清單（origin_entity 多樣性現況）與 registry 條目內容；`go` 授權＝「registry 加該公司＋apply 該 RA 入圖」，不含 thesis／live。互動 session 可當場 sync 取號並立刻 `go`，不必等 daily——統一的是**核准的載體**，不是核准的時機。`skills/company-onboard` 的文件發現與 L8 判準照舊，只有最後的核准動作改由 pq2 承載。

**「等你決定」與「等事件」分離（2026-07-30）：** 池子同時裝著兩種性質不同的東西，混在一起會讓訊噪比降到約 1:1（歷來 76 個編號有 31 個被 drop）。`config/decision_blockers.json` 的 `resolution_mode` 是分類判準：`user_decision`／`awaiting_external`／`system_internal`。保守規則——**只要有一個 blocker 需要人決定，整個項目就留在決策佇列**，寧可多問也不要安靜藏起來。使用者亦可用 `pending --until/--trigger` 明確指定等待條件，優先於自動推導。

**人工判讀不等於外部事件（2026-08-15 使用者定案）：** 若現有公開資料已可開始 bounded research、source-trace、assessment 或 manual observation proposal，`go` 的決定是「是否啟動這份研究」，所以項目必須留在 `user_decision`；不能因 next step 含「人工填入／人工判讀」就藏進 `awaiting_external`。只有世界必須先產生新 filing、掛牌或到達既定日期才屬 `awaiting_external`。純 `system_internal`（例如 frozen market／FX context 的自然老化）不建立 pq2；既有誤分類項由 sync 留下 deterministic retirement audit 後結案。Graph admission、Engine C observation 寫入、thesis mutation 與 live gate 仍各自另取 exact 人工核准，研究 `go` 不會跨越它們。

**Daily pq1 budget：** 每輪上限唯一 authority 是 `config/daily_routine.json` 的 `pq1.drain_limit_per_run`，它是**吞吐量 cap 不是每日 quota**；查證：`python -c "import json;print(json.load(open('config/daily_routine.json'))['pq1']['drain_limit_per_run'])"`。排序權重唯一 authority 是 `engine_b/priority.py`。tracked thesis impact 由非 retired lifecycle ＋ non-terminal Decision cohorts 自動導出。

**待核准內容密度（2026-07-30 使用者定案）：** stable pq2 編號不只列短標題。每項先給一段 TL;DR，再明列完整公司／ticker、誰供應誰、產品／材料／技術、事件成熟度、投資意義、證據與反證限制，以及 `go` 實際授權的 action type；**不得假設使用者能從 `co:*` ID 或內部術語自行還原主詞。** 這是 `skills/daily-brief/SKILL.md` 的共用 presentation contract。

**決策行優先（2026-08-29 使用者定案）：** 每個 active pq2 item 的**第一行必須是決策行**——
「做什麼 — 為什麼是現在 ｜ `go` 授權什麼，不含什麼」，一行寫完，使用者不展開也能決定要不要展開。

⚠ **這不是推翻上面那條密度契約，是補它的另一半。** 2026-07-30 那條修的是相反的毛病（項目只有
`co:*` ID，使用者無法還原主詞）；使用者現在感受到的是它的代價——**完整不等於可掃描**。
所以決策行改的是**閱讀順序**，密度欄位一項都不減，全部原樣收在決策行下面。
判準：術語可以留（使用者接受術語），但「要讀完四段才知道要不要動作」不行。

決策行的「不含」欄不是修辭。`go` 一律只授權該項自己的 action type，而最相鄰的下一步
（研究 `go` 不含入圖、入圖 `go` 不含 thesis mutation、任何 `go` 都不含 live）必須逐項寫出來——
否則使用者要靠記憶區分授權邊界，而那正是這些 gate 存在的理由。

**面向使用者的措辭層：內部識別符不是給使用者讀的（2026-08-31 使用者定案）：** 這是同一個
張力的第三次調整，方向一致、不是推翻前兩次——07-30 修的是「只給 `co:axt` 無法還原主詞」，
08-29 修的是「要讀完四段才知道要不要動作」，本次修的是**術語密度本身**。使用者的原話：
「我可能 care 這次核准建立了哪兩個公司之間的哪種關係，但他是怎麼在圖裡用什麼 property
表達，其實我不是很在意。」

1. **判準是「望文生義還是要查表」，不是「內不內部」（2026-08-31 使用者補充）。**
   使用者原話：「`co:axt` 這類內部 ID 好像也可以留著……但太長或比較艱澀的 label，
   我偏好直接能看懂的。」所以 `co:axt`／`co:coherent` 本身就是公司名，**留著**，
   翻譯反而多一層轉換；真正要翻的是含縮寫或長蛇形命名的：
   `tech:uhp_laser` → 超高功率雷射、`mat:inp_substrate` → 磷化銦基板、
   `externally_corroborated` → 客戶端印證、`self_reported_costly` → 供應商自報、
   `research_assessment_missing` → 缺獨立來源、`ra_admission` → 入圖核准。
   翻譯後首次出現以反引號附原始 label，讓使用者能貼回來查圖。
2. **三樣必須留，其餘可省：** pq2 編號（唯一核准介面）、公司全名＋ticker、
   `go` 授權什麼／不含什麼。前兩者是使用者的操作把手，第三者是四個 authority gate 的界線——
   省掉它，使用者就得靠記憶區分「核准入圖」與「核准下單」。
3. **待辦分段軸是「現在能不能決定」，不是項目類型，也不是「上次有沒有說晚點」
   （2026-08-31 使用者發現）。** 四段固定：建議 `go`／建議 `drop`／**你之前說晚點再決定的**／
   不用動（等事件＋進行中）。
   ⚠ **`deferred_at` 只影響排序，不影響可見性。** 分段依據是 `waiting_on` 是否為空：
   為空＝你隨時可以決定，**必須逐項現形並附已等待天數**；有值＝世界要先發生某事，
   才可摺疊成一行。事發：2026-08-31 brief 把 [193]（付費報告 access，已 defer 10 天）
   與 [230]（已 defer 6 天）跟「等事件」混在同一段摺疊，使用者當場指出
   「這個不應該被藏起來」——兩者 `waiting_on` 都是空的，是欠著的決定不是等待中的事件。
   附天數是為了讓拖延自己現形（L14：防呆要會自己出現，不是要人記得）。
4. **內部機制名稱不出現在使用者可讀區**：`action_digest`、`focus_company_id`、`cohort_id`、
   `work order`、`consumed marker` 等留在 receipt 與 log，不進 brief 正文。

判準：**問「使用者讀到這個詞，要做的決定會不同嗎？」** 不會 → 它是實作細節，收進 receipt。

**提醒去重：** lifecycle SessionStart hook 只提醒尚未進池的新到期項目；已存在的 `thesis_lifecycle`（含 deferred）由 Daily Brief 顯示，hook 必須靜默。新提醒只走 `additionalContext` 呈現一次。

### Decision gap dispatch

`decision_review go` 的語意是把最新 decision 綁定的 proposed work order checkpoint 成 pq1 `queued`，**不是**立刻沿用舊 assessment 做 bare `reassess`。原 pq2 項目在 queued／researching／awaiting_approval 期間保持 active 但不重複詢問；只有研究未果的 parked receipt，或補缺口後產生的**新 decision receipt**才能 resolve。

Decision gap jobs 優先占用同一個 daily pq1 budget。若研究結果需要 graph admission、Engine C manual observation、thesis revise／retire 或其他 authority mutation，完整 packet 必須回 pq2，**原人工 gate 不放寬**。Live choice／fill 永遠不由此路徑推定。

### Sheet 持股覆蓋分類

`sheet_only_holding` 只針對**真正沒有任何機制負責**的持股。`decision_lab/brief.py` 的 `_sheet_only_items` 依 Sheet ticker 分三類：beta policy 涵蓋（`coverage=beta_policy`）、使用者明確不研究（`coverage=user_ignored`，登記於 `config/holdings_coverage.json`）、其餘 `coverage=uncovered`。前兩類判 `MONITOR` ＋空 blockers，仍在 daily brief 現形但不占 pq2 編號。

**`todo drop` 對這類項目無效**——它只清當次編號，sync 會依 Sheet 持股＋無 cohort 重新推導並配新編號（2026-07-29 實測 [18]-[33] → [46]-[60]）；要真正解除必須改覆蓋分類或建 cohort。覆蓋設定檔讀取失敗一律 fail safe 退回 `REVIEW`。beta universe 的 SSOT 只有 `config/beta_policy.json`。

### Source-trace backlog 防漏

`parked` 不等同「註記後遺忘」。pq1 每次因 `isolated_tier_3`／截圖／paywall 未果而 park 時，必須留下 `trace_status`、`trace_attempts_ref`、`trace_next_trigger` 與 `trace_requires_user`。

**等待條件的唯一 registry 是 Event Watch（2026-08-31 [321] 定案）：** 追源 backlog 已併入
`library/leads/event_watches.json`，與待辦等待、假設對照共用同一個引擎、同一組計數器。
線索 park 的當下自動建 watch 並取得**到期日**（`config/event_watch.json` 的 `trace_ttl_days`，
預設 120 天＝一個財報週期＋緩衝）。

⚠ 併入的理由不是整齊。原本 consumed-marker（防同一標的重複喚醒、保護 pq1 預算）**沒有
到期兜底**，標的用完即靜默沉底——實測 50 筆有 10 筆已不可能再被喚醒，而
`auto_trigger_reachable` 對它們全回 `true`：那個欄位只答「有沒有標的可比對」，卻被讀成
「還會不會醒」（L12 一個表示兩種語意）。原設計刻意把搬家排最後並註明「那端現況健康、
收益最低」，**而「現況健康」從未被驗證過**——L14 的又一次實例，寫在自家設計文件裡的
假設同樣要跑命令否證。

現況改用 `wake_state` 四態：`watching`（有事件在等）／`stalled`（具名標的已全部觸發過
一輪，被動層短期不會再醒，靠到期或主動輪詢救）／`expired`（到期，該決定續等或放棄）／
`unwatched`（沒有任何機制在等它，唯一真正的黑洞）。**後三者用
`engine_b.cli trace-backlog --needs-attention` 撈出並逐筆處置——它們等下去不會有事發生。**

一般 scheduled／event-triggered 重查仍屬 pq1，不占 pq2；只有需要使用者提供合法 access、核准付費或明確改變研究優先權時，`todo sync` 才建立 `source_trace_review`。該類型的 `go` 只把 exact lead dispatch 回 pq1，**不代表相信截圖、提高 evidence tier 或 graph admission**；取得原文並 prepare 後，入圖仍是另一個 `ra_admission` pq2。任何新訂閱／購買必須另列 exact 金額與方案。

**Lead 之間的關聯鍵（2026-07-30；2026-08-02 補 executable linkage）：** URL hash 只認同一篇文章。跨文章的關聯靠 `engine_b/entities.py` 的具名標的做**確定性**比對（cashtag、`edgar:<TICKER>`、registry 反查的 `co:*`）。主題相關但無共同 ticker 的仍靠語意。`trace_next_trigger` 保留給人讀；機器改用 `trace_trigger_kind=related_entity_signal`＋`trace_trigger_entities`。同標的的新 lead 通過 triage 後，會把不需人工 access／付費的 parked trace 排回 bounded pq1，留下 triggering lead receipt；不提高 evidence tier、不授權入圖。Decision `waiting_on` 只有明確綁定 `event_type=decision_evidence_delta` 時，才由同 cohort 的 material evidence receipt 喚醒原 stable pq2 編號；不猜測其他自然語言 trigger，只恢復人工複查，不自動 dispatch。

### 資本與風控

**Numeric SSOT：** `config/investment_policy.json` 與 `config/beta_policy.json`（目標配置比例另在 `config/target_allocation.json`，它是錨點不是 gate）。只有 **ETF 槓桿 cap 與 5% 單筆上限**是硬擋，其餘曝險只記錄／警告。使用者仍可走 prepared `live_override` 留下 exact action ＋ reason receipt；系統不自動下單。

⚠ 這句原本寫的是「把 **live supported range** 歸零」。`live_supported_range` 已隨 U7 移除（見「Alpha 呈現契約」），但**硬擋本身仍在**——`store.record_live_choice` 對每一筆非零 live 選擇仍擋這三碼，外加凍結快照七天時效與「部位量不到就 fail closed」。移除的是系統給的建議區間，不是煞車。

**共同可投資現金池只有一條：** `Portfolio CASH − cash floor`，供 Alpha／Beta 共用。不扣 operating reserve、alpha reserve 或 planned outflows，沒有 Sheet／household 雙 range。Alpha／Beta 如何分配由 `config/target_allocation.json` 的目標配置比例、Decision sizing、單筆上限與風控決定，**cash floor 不承擔 sleeve allocation**。cash floor authority 失效時 fail closed，不回退到百分比 reserve。

**兩個槓桿指標不得混用：** `nominal_weight` 是「投入槓桿 ETF 的資金占 NAV」（12.5%／20% warning/cap）；`effective_weight` 是乘上 2x／3x 後的「換算槓桿曝險」（30%／40% warning/cap）。面向使用者不得把前者寫成模糊的「名目槓桿」。數值仍只以 `config/beta_policy.json` 為 SSOT；本段是人類可讀鏡像。

**Capital Authority：** 私人 Google Sheet 只保留 `cash_floor` 與 `credit_facility` 兩種 record；日常 credential scope 只有 `spreadsheets.readonly`。貸款額度、已借款、利率、計息方式、期限與還本方式獨立保存；**未動用額度不算 NAV／cash／allocation**。每次提款、標的與 tranche 都是 explicit manual review，「高信心」不構成 machine permission。

**曝險邊界：** Sheet `bucket=CASH` 列計入 NAV 但不計曝險。未知非現金持股按 unlevered direct issuer ＋ alpha exposure 誠實降級，不因缺 mapping 阻擋。`issuer_loads` 只代表 policy 已登記的 ownership look-through，輸出必標 `partial`；coverage 為 partial 時，人類輸出一律寫「已知至少 X%」，不得把已建模部分冒充完整曝險。Engine A 上游依賴不可混成 issuer ownership。**既有 frozen decision 不回寫**，重新 reassess 才使用新 policy／calculator。

**退休貸款資本目標（2026-07-28 使用者定案）：** 使用者約 30 歲、退休目標約 60 歲；可長抱至到期的貸款資本以約 30 年後 `retirement_net_terminal_wealth` 最大化為方向，不以降低中途回撤為第一目標。契約為利息按月支付、期間不攤還本金、到期一次還本、允許投資用途。broad unlevered beta 是主要候選；daily 3x 可投資但維持衛星定位，exact review 必須扣除借款成本與到期本金比較退休淨終值，**月息若需靠賣出 beta 支付則該 tranche 不成立**。

### Alpha 呈現契約（2026-08-15 使用者定案；2026-08-28 資本表達層已整組移除）

**alpha 對使用者的輸出是「候選＋事件追蹤」，不是部位尺寸。** 系統只負責兩件使用者自己做不動的事：
**哪些標的值得看**、以及**它們有什麼新事件**；買多少、什麼時候買由使用者決定。

理由是實測而非偏好（以下為 **2026-08-15 定案當時的實測值，非現況**）：6 個 ELIGIBLE cohort
每檔 target 固定 0.1% NAV、合計 0.6%（以可部署現金 USD 30,567 計，每檔約 30 美元），
而該尺寸來自當時**從未被 outcome 驗證**的 `axis_ceiling`（`measured_outcomes` 0/8）。
依 L14「未經量測的機制不得享有默認信任，**gate 也不例外**」，它沒有資格決定資本。

> **現況查證（數字會變，判準不會）：**
> `python -c "from decision_lab.bootstrap import open_default_store as o; s=o(); c=s.capital_expression_counters(); print('measured', c['measured_outcomes'], '/', c['outcomes'], '| eligible', c['eligible_cohorts'], '/', c['total_cohorts']); s.close()"`
> **本契約的結論不隨這個數字改變**——它同時建立在使用者的可用性判斷上
> （「產出若無法讓人分辨做了什麼與沒做，它就不算產出」），那部分與 outcome 筆數無關。使用者的原話是「繞了這麼久只得到我很早就看到的幾間公司、都等於 0.2%，
我會不知道我到底做了什麼」——**產出若無法讓人分辨做了什麼與沒做，它就不算產出**。

**⚠ 2026-08-28 更新：本契約當時只做了一半，剩下的另一半已完成。** 2026-08-15 的版本留下
「paper lane 繼續運作，它是記分板不是建議」——但 `supported_range` 仍在輸出、`axis_ceiling`
仍在決定資本。實測（2026-08-28）21 個 operational cohort 有 20 個 `live_supported_range`
是 `[0,0]`，而排序第一名 COHR 的三個資本風控**沒有一個 binding**，唯一 binding 的是
`weakest_axis` 的 0.002——一個從未被驗證的機制在決定資本，正是 L14 明文禁止的事。

**因此 alpha 的資本表達層已整組移除：** `live_supported_range`、`axis_ceiling`、
`paper_target`、probe cap 與四動作（`NO_ACTION`／`REVIEW`／`TRADE`／`HEDGE`）都不再產生。
系統終點是**瓶頸度排序**，注意力狀態只剩 `MONITOR`／`REVIEW`（今天要不要看這一檔）。
五軸保留，角色由「決定資本上限」改為「決定排序與指出最弱軸」。

**outcome 量測改為等權重報酬追蹤：** 只記「哪天推薦了這檔、當時股價、之後報酬率」，
不含部位大小或 NAV 佔比；比較基準是等權重，回答「排序前段的標的後續報酬是否優於後段」。
價格錨點仍由 Shadow observation 提供（它只有價格與時點，不含部位）。

**真正的風控完全不變：** 5% 單筆上限、ETF 槓桿 nominal／effective cap、總曝險 cap 全部保留
（numeric SSOT 仍是 `config/investment_policy.json` 與 `config/beta_policy.json`）。
拿掉的是**憑空的建議尺寸**，不是煞車——`record_live_choice` 對每一筆非零 live 選擇仍硬擋
那三個上限與凍結快照七天時效。live choice／fill 仍然 100% 人工，系統不連 broker。

> **查證（別相信這段文字，跑一次）：**
> `python -c "import json;p=json.load(open('config/investment_policy.json'));print('probe_lane keys:', sorted(p['probe_lane']));print('single_position_nav_cap:', p['single_position_nav_cap'])"`
> `probe_lane` 不該再有 `axis_ceilings`／`probe_book_nav_cap`／`single_probe_nav_cap`／
> `live_adv_fraction_cap`；`single_position_nav_cap` 應仍是 0.05。

**反向新增的 NAV 比例呈現（純呈現、零門檻）：** 從 Google Sheet 讀持股，輸出各標的佔 NAV
百分比、bucket 分布與相關性分組。**不判斷好壞、不告警、不阻擋任何動作**——失衡由使用者
看數字自行判斷。5% 單筆上限在這裡只作參考線，不進入 gate 判定。

#### 「哪些標的值得看」的判準與交付要求（2026-08-19 使用者定案）

⚠ **本段是 2026-08-15 契約缺的另一半。** 原契約把「不給尺寸」寫了三段、「要給什麼」
只有半句且未定義判準，實際行為因此退化成**只列清單、不排序**（2026-08-19 實例：
agent 以「outcome 0/8 未驗證」拒絕推薦）。

**使用者的實際用法（原話）：「哪個公司佔據了瓶頸、且是市場資金關注的部分，
那我們就去投，再來看 disproof。」** 判準經 2026-08-21 收斂為四維度：

1. **瓶頸地位（結構）** — `substitutability` 4–5／5、`sole_source`、距需求端跳數。
2. **需求錨點** — 資金在不在那條鏈上。demand anchor 為空者（實測如 GlobalFoundries
   那批）不是候選。
3. **客戶端資本承諾** — **誰付錢給誰，這一項自帶方向性且最難偽造**：
   客戶掏錢綁供應商＝真瓶頸（NVIDIA 對 COHR 的 20 億投資＋2030 產能協議；Micron 的
   take-or-pay＋4.22 億押金）；**供應商付錢或給股權換訂單＝不是瓶頸**（POET 以
   2,292 萬份認股權證換 Lumilens 訂單）。任何以「替代難度」為主的排序都抓不到後者。
4. **標的純度（是 alpha 還是 beta）** — 瓶頸業務占該公司多少。同為 `sub=5`，AVGO
   （市值 1.73 兆、45 位分析師覆蓋）的 CPO 只是一塊業務，研究它接近研究 beta；
   AXTI（4.8B、5 位）、POET（1.4B、**0 位**）才有資訊落差。市值與 `analyst_count`
   在 Engine C，**不在排序內，必須另看**。

**⚠ 已知會失焦的指標——不得單獨用作瓶頸性證據：**
- **`evidence` 等級**：最高級 `externally_corroborated` 必須靠研究找到客戶端文件才拿得到，
  預設每條邊都是 `self_reported`。它是**研究深度的函數**。
- **同一 chokepoint 的供應商計數**：`mat:inp_substrate` 7 家 vs `tech:uhp_laser` 1 家，
  反映的是**我們研究了幾家**，不是世界上有幾家。
- **`documents` 計數**：`bottleneck.py` 已排除，否則分數會變成「我們讀了幾份文件」。

判別法：**這個指標會隨我們多讀一份文件而單調上升嗎？** 會 → 它測的是研究量。
客戶端資本承諾不會（離散事件，要嘛發生要嘛沒有），供應商計數會。

**唯一排序權威是 `query/bottleneck.py` 的 `rank_bottlenecks()`**，不得另建平行排序。
（`axis_ceiling` 與 paper target 曾被誤當排序代理，它們是資本閘門不是選股判準，已於
2026-08-28 移除；`research_status` 是研究完整度，也不得拿來排序。）
它輸出**兩份排序，用途不同、不可互換**：
- `rows`（可行動）：`evidence` 優先於 `substitutability`，回答「**現在能投什麼**」——
  證據不夠強的邊不能拿來下注。
- `structural_rows`（純結構）：完全不看證據，回答「**該去補誰的證據**」——結構很卡但
  證據沒跟上的邊是研究最高 ROI。實測差異：可行動第 1 是 COHR→NVIDIA，純結構第 1 是
  AVGO→CPO；而 LITE→UHP laser（`sub=5`＋`sole_source`）因 `self_reported` 在可行動
  排序落到第 10。

**交付要求（違反即視為未完成）：**
- 必須輸出**有序清單與明確的首選**，並直接回答「現在要加碼哪一檔」。
- 若因證據不足而無法排序，必須指出**缺哪一項具體證據**，不得以「未經 outcome 驗證」搪塞。
- **「outcome 還沒驗證」不是拒絕排序的理由，不論當下比值是多少。** 不出手就沒有 outcome，
  沒 outcome 就不敢排序，是死循環；L14 要求的是「不得讓未量測機制**決定資本尺寸**」，
  不是「不得表達研究判斷」。判斷與尺寸是兩件事，尺寸仍然不給。
  ⚠ 這條刻意**不寫死比值**：先前寫成「`outcome 0/8` 不是理由」，等於把判準綁在一個會變的
  數字上——數字一變（2026-08-26 實測已是 2/12），讀者會以為判準跟著失效或需要重新論證。
- 排序是**研究判斷**，必須明標它不是回測或統計勝率，並附各候選的 disproof。
- 必須點明候選之間的**相關性**：本圖標的高度集中於 AI 光互連，列出 N 檔不等於 N 個獨立
  機會（見「進行中」workstream 對錨點樣本效度的下修）。全買是同一賭注下 N 次，不是分散。

**進場靠判斷，出場靠 disproof。** 反證的用途是決定何時承認判斷錯了，不是進場的前置條件；
把兩者混用會產生「永遠不出手、只累積反證」的無效產出。

### Beta 呈現契約（2026-07-30 使用者定案；2026-08-29 拔除訊號後改寫）

**Beta 不再回答「今天該不該投」，只回答兩件事：各 sleeve 距目標配置多遠、每檔現在在什麼水位。** 使用者的實際行為是定期投入而非擇時，每次真正要決定的只有「這次投哪一檔」。訊號整組移除的實測依據見下一節；呈現層**不得以任何名義復刻擇時語言**（今天是否投入、本輪上限、節奏、可評估／暫停新增）。

底層與首屏仍只保存一條 `self_funded_supported_range`，但它已重新定義為**可部署現金本身**（`Portfolio CASH − cash floor`），不再乘任何 pace 或單輪比例；只有槓桿／總曝險硬擋或資本 authority 失效才會讓它歸零。自有現金可部署固定顯示 `Portfolio CASH − cash floor`，並明說 cash floor 以上為 Alpha／Beta 共用。另獨立顯示「未動用貸款額度／已借款／估計利息」，明標貸款不算自有現金。**不得用未解釋的斜線或 raw field name。**

**目標配置比例的 SSOT 只有 `config/target_allocation.json`：** sleeve 層級六格，分母是**已投入的非現金部位**（不含現金；cash floor 是另一個 authority），`band` 是**容忍區間不是 gate**——落在區間內即視為到位、沒有偏好。**再平衡只用新投入的錢往低於目標的格子補，不賣出**；此表只給差距，**不給金額、不排名、不產生部位尺寸**。查證：`python -c "import json;d=json.load(open('config/target_allocation.json'));print(d['basis'], sorted(d['sleeves']))"`。**貸款 tranche 不適用配置建議**，仍走「Capital Authority」既有的逐次 explicit manual review。

**相對水位只用位置指標：** 52 週區間位置（主要）、距 52 週高點、距 SMA200，全部取自商品**自身**價格序列。它**只呈現、不參與排序、不換算金額**，且必須寫明「長期上漲的標的多數時間落在高位是正確資訊，不是該等回檔的訊號」——2026-07-31 回測顯示等回檔才投入對 30 年終值是負貢獻。**不得用動能指標表達水位**：RSI 量的是最近漲跌的單邊程度，與「站在自己區間哪裡」可以完全脫鉤，而且它正是 2026-08-01 測失敗的輸入，以「水位」之名放回來是換名字重來。

**燈號只表達行情資料狀態，不表達投入建議**，固定配文字：🟢行情正常、🔴資料不足（含 TWSE 官方較新而暫時隔離）、⚪歷史不足。**舊語意（🟢可評估／🟡冷卻／排序中／⚪觀察／🔴暫停新增）已於 2026-08-29 廢止，不得回填。**

標的表只負責三欄比較：**行情心跳（自身價格）**、**相對水位（自身價格）**與**所屬 sleeve 配置狀態**。可部署現金、投組 hard caps 與兩條相關性警告是全局條件，不在每檔重複。

**兩條相關性警告每天都要講一次，不因每天一樣而省略：**（a）**alpha 與 beta 是同一個賭注**——alpha 目前全在 AI 光互連、`beta_tilt` 是 QQQ／SOXX／台股半導體，兩個 sleeve 的目標比例分開寫**不代表**它們是兩個獨立風險來源；（b）**TSMC look-through 約 28%**（2330 直接持有 ＋ 0050／006208／00631L 內含權重），高於 `issuer_concentration_warning` 0.25，且系統算不出精確值——`issuer_loads` 覆蓋恆為 `partial`。

槓桿／重疊商品必須使用**自身價格序列**：TQQQ 的水位不得冒用 QQQ（2026-08-29 實測 69% vs 85%），00631L／006208 同理不得冒用 0050。這條原本規範訊號基準，訊號拔除後改規範水位。

**真實風控完全不變：** ETF 槓桿 nominal／effective cap、總曝險 cap 與 5% 單筆上限全部保留，numeric SSOT 仍是 `config/beta_policy.json` 與 `config/investment_policy.json`；`config/target_allocation.json` 不歸零任何東西、不阻擋任何動作。

**行情表是每日心跳，不受今日是否投入影響（2026-08-05 使用者定案；2026-08-29 措辭跟著字彙更新）：** 即使所有 sleeve 都「到位（區間內、無偏好）」、今天沒有任何配置缺口，主力逐檔表仍不得省略。每列必須明示商品自身的「最新完整交易日 `YYYY-MM-DD`＋1 日漲跌」；不能只寫沒有日期的「1 日」，也不能把最近收盤誤稱即時今日行情。`stale`／`quarantined` 時改列官方 reference 的日期與當日漲跌並附降級原因，不得因非操作日把行情濃縮成一行狀態摘要。

### 技術訊號的地位（2026-08-01 實測後定案；2026-08-29 整組移除）

**實測記錄（歷史，不因後續移除而改寫）：** 三次實測全部失敗——以訊號 gate 現金投入使終值**輸給無腦定投 8.5%**（QQQ 91.5%、SOXX 91.9%）；訊號調節借款提取**無可測得效果**；訊號決定投給哪個標的**輸給固定單押最佳標的 22%**，且三分之一時間買進 CAGR 僅 7.2% 的弱標的——「買跌最深的」會系統性把錢導向長期較弱的資產。`stretched_above_sma200` 同為未實測的推論。完整證據與未實作項見 [`docs/brainstorms/2026-07-31-leverage-glide-path-requirements.md`](docs/brainstorms/2026-07-31-leverage-glide-path-requirements.md)。**這段是拔除的依據，任何改寫都不得刪減它。**

**因此：訊號機制已於 2026-08-29 整組移除（commit `6aa31de`），不是降級使用。** 移除清單：三態系統動作 `CONTRIBUTE REVIEW`／`HOLD`／`PAUSE CONTRIBUTION`、RSI／MACD／`sma_50_slope`／tier、`signal.baseline_pace`／`allowed_paces`／`repeat_after_sessions`／`stretched_above_sma200`、`campaign_budget_fraction_by_sleeve` 與單輪 campaign budget 百分比、每檔 `supported_order_range`／`binding_constraints`、「本輪可評估上限」這個概念，以及「自有現金 baseline 每 5 個完整交易日主動提醒一次」的例行提醒節奏。**這些字彙不得以任何名義回到文件或輸出**——包括改名成「熱度」「節奏」，或借用「水位」之名讓動能指標重新參與排序／尺寸（水位本身合法，前提是它只呈現）。查證：`python -c "import json;print(sorted(json.load(open('config/beta_policy.json'))))"` 不應出現 `signal`（現為 capital／capital_scope／instruments／market_data／mode／policy_version／risk／schema_version）。

拔的依據是「已被量測為有害」，不只是「太長」——這是 L14 第 2 點（gate 本身也要被驗證）的直接執行。取代它的是**目標配置比例 ＋ 相對水位**，見上一節。

**須區分量測、訊號與脈絡：** 總曝險倍數、歸零門檻、追繳門檻、利息覆蓋屬**量測**，有價值且應強化（本輪所有決策翻轉皆由此而來）；RSI／MACD／tier／pace 屬**訊號**，三次受測皆未通過，現已移除。位置指標（52 週區間位置、距 52 週高點、距 SMA200）是**呈現用的脈絡**——既不是量測也不是訊號，它不決定任何金額、不參與任何排序；**一旦有人拿它排序或調整尺寸，它就變回訊號**，適用同一條實測紀律。

**台股 technical freshness（2026-08-01，仍生效）：** `.TW` 的最新交易日先用 TWSE 官方 `STOCK_DAY_ALL` OpenAPI 校驗；Yahoo session 落後、官方代碼缺列或 TWSE freshness 無法取得時，該標的行情必須 `quarantined`，改列官方 reference 的日期與當日漲跌並附降級原因。⚠ 2026-08-29 起**單檔行情降級不再歸零任何 supported range**（已無逐檔區間，共用區間只由資本 authority 與硬擋決定）；降級的後果是那一列的水位不可信、必須現形，不是靜默消失。TWSE 的未還權 OHLC 只作最新日期與當日漲跌 reference，不得直接混入 Yahoo adjusted-close 長期序列；完整還權歷史另需明確的資料源與調整規則。

### 事件監控

issuer 曝險 ≥20% 且對應 series 單日報酬首次跌破 -4% 才產 ephemeral `event_search_requests`；daily agent 只做一次 WebSearch，輸出可能原因＋曝險並標未經查證，**不建 lead／decision、不進 pq1/pq2、不寫 Engine A**。需要深挖才另走 lead-intake。

### Daily routine 權限與 retry 邊界（2026-08-09 使用者定案）

Codex standalone scheduled task 會沿用 legacy `workspace-write` sandbox，project permission profile 不得再當作
Daily authority；唯一權限來源是 `.codex/rules/stockbot-automations.rules` 的十六個窄 fixed entry，涵蓋固定連外、
owner-only private read／staging 與 publisher；這些命令
**第一次呼叫就用 `require_escalated` 命中 exact outside-sandbox rule**，不是先失敗再以升權重重跑。權限取得後若仍遇暫時性 transport
error，只允許該命令既有的 bounded、idempotent retry 作最後一步；不得重跑整份 Daily Brief、重做已 checkpoint
的研究／authority mutation，或把 permission failure 冒充成「零筆」。retry 用盡後保存結構化 failure 並 fail closed。

十六個入口是：harvest、Engine C ETL、Alpha purity snapshot、SEC EDGAR pq1 fetch、**MOPS 台股 pq1 fetch**、Beta snapshot、pending priority list、pq1 drain、
catalyst watch、Alpha outcome snapshot、Research Action prepare、decision today、todo sync、已核准 work order checkpoint、state publisher、brief publisher。
⚠ `fetchers/` **不是整包放行**：只有 `edgar.py` 與 `mops.py` 兩支公開文件下載器在列（無憑證、
不碰 identity／ACL、不寫 private authority）。同目錄的 `gsheets.py` 使用 Google service account 憑證，
屬 credential-bearing surface，刻意不放行。
`query.bottleneck`、`query.coverage_gaps`、harvest health、trace backlog、todo list 與 JSON 檢查已可在 sandbox 正常執行，不另升權。
work checkpoint rule 只匹配 `engine_b.todo work`：它只能推進已有 `dispatch_ref` 的 exact USER-GO 項目，
不得代替 `dispatch`／`resolve`／`reassess`。使用者核准後的 apply／reassess／complete-ra／commit intake 不加入 unattended rule，仍走 type-aware 人工 gate。

### 報告留檔策略

**daily brief 不留檔**（只出在 session；稽核價值由待辦池 log ＋ leads 狀態機 ＋ Decision Store 承擔）；**weekly report 留檔**（`docs/reports/`，含無法從池重建的 topic discovery 與健康審查趨勢）。不回到 PR/Issue 形式——那會產生與池競爭的第二個狀態源。

**Weekly authority hierarchy：** `AGENTS.md` 是政策 SSOT；`crons/weekly_scan_prompt.md` 是 executable runbook，只有開發／人工修 policy 時才改，**weekly routine 本身不得自我改寫**。`docs/reports/weekly_scan_<date>.md` 是當週 point-in-time 歷史報告，不是 current-state truth；現況仍以 leads／todo pool／lifecycle／Engine A-C-D 各自 authority 為準。

### Daily Brief provider-neutral outbound 通知（2026-08-04）

Daily Brief 完成後可由 Codex 或本機 Claude Code 呼叫同一支 `scripts/publish_daily_brief.py`，
outbound-only 送到 Discord private Forum channel。**三條判準：**

- **通知不是 authority：** 不接受 Discord `go`／交易／入圖指令，不寫 todo、Decision、Graph 或 Sheet，
  也不改變人工 graph admission／live gate。
- **Canonical Brief 只有一份：** task 最終回覆與 Discord publisher 必須使用同一份最終 Markdown。
  publisher 完成後不得再為 task 另寫精簡版、摘要版或刪除 Beta 表格；delivery receipt 可附在完整
  brief 後方，但不能取代或重寫任何 section。
- **失敗不得阻斷：** 發送失敗是 `delivery_failed`／`not_configured` 的 best-effort 狀態；
  `.env`、webhook 與 `library/private/notifications/` 永遠不得進 Git。

去重鍵、Forum thread 保存、分段重試與 PowerShell UTF-8 陷阱等操作細節見
[`docs/OPERATIONS.md`](docs/OPERATIONS.md)。

---

## 來源登記表（一手來源優先）

通用搜尋（Tavily 等）只配 LLM 品質評分 gate，用在第三層。**機器可執行的路由與未果處置唯一權威是 [`skills/source-trace/SKILL.md`](skills/source-trace/SKILL.md)**；快速記憶：美股走 SEC EDGAR，台股走公開資訊觀測站（含月營收揭露），A股走年報／問詢函／海關數據，技術走 arXiv／OFC/ECOC／專利。各市場都優先做上下游上市公司交叉驗證。

出投資建議前必看的核驗清單五項：客戶集中度、毛利率／產能利用率、backlog／營收結構、稀釋、估值壓力。

## v0 Schema

設計原則：表的「形狀」鎖死，字彙（type/relation/層級）用對照表留鬆；屬性按 L4「物理 / 關係 / 時變」三分歸位。完整欄位表、vocab、claims 格式、sole_source 驗證規則：見 [`schema/graph_schema.md`](schema/graph_schema.md)。

**快速記憶：**
- **圖公司 ID（`co:*`）不要憑公司名猜。** 唯一權威是 `config/company_identity.json`，由 `identity/registry.py` 載入；loader 的 `TICKER_MAP` 只是由同一 registry 生成的相容介面。查圖前先查 registry，或用 `query/health_audit.py` 的 `COMPANY_IDS_CYPHER` 列出圖中 Company 再比對。例：Sivers 是 `co:sivers_semiconductors`，不是 `co:sivers`（2026-07-21 週掃即因猜 ID 未命中而漏掉 Sivers 的圖內比對）。ID 未命中時要區分「ID 沒解析對」與「圖中真無此公司」，不能默默跳過。
- **報價單位 ≠ 結算幣別（2026-08-05 定案）：** 交易所報價單位（LSE 的 `GBp`、TASE 的 `ILA`、JSE 的 `ZAc`）是 provider 直接回傳的 `currency`，但它是 minor unit，不是 ISO-4217 結算幣別。唯一正規化入口是 `identity/currency.py`＋`config/currency_units.json`；`config/company_identity.json` 寫交易所實際報價的單位，registry 對外一律以結算幣別呈現 `*_currency`、原始單位存 `*_quote_unit`。價格換算只在行情層做一次（`quote_price × factor`），FX pair 一律用結算幣別，不得再折第二次。ISO code 形式的新幣別不必登記；未登記且非 ISO 形式一律 fail closed 出 `market_quote_unit_unregistered`，**不得為了通過驗證把報價單位直接改寫成 ISO code——價格會差 100 倍。**
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

> **引用慣例（對使用者輸出時）：** 使用者記不住 L 編號對應。任何回覆或報告提到 L1–L16 時，
> 該編號第一次出現必須括號備註一句是哪條判準，例如「L7（thesis 生命週期：disproof 條件要附
> 核查頻率 + 48h 觸發動作）」、「L8（來源獨立性：供應商自報不能當 sole_source 獨立佐證）」。
> 同一份輸出內重複出現同編號可不再備註。

> **L1–L3、L5 是專案早期的選型與動工判準，架構已定案，此處只留判準句**（2026-08-19 壓縮，
> 編號原地保留供交叉引用；事發經過見 git history）。

### L1 — 不要為了「少裝一個系統」而用不成熟工具去做專案核心
核心元件優化**能力、生態成熟度、可觀測性**，不優化「系統數量」——後者在本機／單人情境下很廉價。需要人工 review 的資料結構，視覺化是硬需求；polyglot 對「質化知識＋量化數字」雙軌是正確架構，別拿「統一技術棧」當反射性理由。**Neo4j 已定案，不再重開。**

### L2 — 不要在動工前追求「完美 schema」
「現在搞錯、以後要搬全部資料才能修」的才現在想清楚（表的形狀）；「以後加一列設定就能補」的（字彙）直接動工讓資料教你。

### L3 — 別讓 DB / 框架的選型卡住垂直切片
抽取層輸出 DB 無關 JSON，選型隨時可換。Agent 框架等流程穩了再包，起步用純 Python 函式＋簡單佇列。

### L4 — 屬性歸位:物理 / 關係 / 時變 三分(schema 建模鐵律)
**事發:** 評估 chokepoint-atlas 給的 `ComponentNode` 五個瓶頸欄位(concentration / substitutability / ramp_difficulty / demand_proof_level / consensus_coverage)。它們長得像同類,實際分屬三種物件;作者全塞進一個 node,是因為他的 skill 無狀態、不在乎持久化。我們的庫會長大、要 review、要 join 時間序列,混在一起會爛。

**三連問判準(決定一個屬性放哪):**
1. **換掉關係另一端,值會變嗎?** 不變 → node;會變 → edge。
2. **值會隨時間變嗎？** 會 → 不是靜態圖屬性，是「帶時戳的觀測」（進 SQLite，不進圖）。
3. **講的是物理現實,還是證據強度 / 市場認知?** 後兩者 → 是 metadata 或市場狀態,不是實體屬性。

**結論：** 品類集中度/內在量產難度 = node；可替代性/sole-source/lead-time/供應商 ramp 執行力 = edge；需求證據強度 = 證據 metadata 掛在主張上；市場擁擠度 = 時變觀測進 SQLite。
**一句話：瓶頸的 alpha 大半在邊上，不在點上。**

### L5 — chokepoint-atlas / serenity-skill 是方法論藍圖，不是相依套件
**抄骨架（stack 分層、role 分類、證據四階、output-formats），不裝套件、不綁相依。** 它們補「怎麼想」，本專案補它們缺的「記得」。⚠ 它是**單一 lens**（偏小市值瓶頸獵手）——當眾多視角之一，**別讓系統世界觀被綁死**。（評估已於早期結案，細節見 git history。）

### L6 — 第一次真實抽取撞出的 schema/pipeline gap

首次真實抽取（Coherent 法說 CPO 段落）撞出四個洞，Gap 1–3 均已修復並於 2026-08-14 驗證。

**Gap 4 仍然活著——LLM 從類別詞推斷出具體實體（最常見的幻覺型態）：** quote 只說「data center interconnect 需求強」，LLM 自己推出 ZR/ZR+ 節點。防線在 `prompts/extract_system.md`：**具體型號／公司名必須在 quote 裡逐字出現**；review 時重點抽查這一項。

**通用判準：**
1. Schema gap 只有真實資料撞上去才會現形（L2 再次驗證）。
2. 局部 ID 在單文件內沒問題，跨文件 MERGE 後會命名空間衝突。

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

**投資諮詢開放的三個前置條件**（第二條非 AI／CPO 垂直切片、thesis→部位最小規則、財務核驗清單五項可一鍵查出）**已於 2026-07-22 全部達標，gate 已開放**；判準與現況由 `thesis/preconditions.py` 機器強制（`check_all()` 隨時可跑），不在此複述以免與程式漂移。三者的規格分別住 `docs/investment-sop.md`、`engine_c/checklist.py`。**核驗清單五項仍是 Watchlist 升格前的必要 gate。**

### L10 — 早期資料庫以 correctness 優先，不背錯誤相容包袱

目前圖譜與資料量仍小，schema／attribute／ID 設計的 refactor 成本很低。遇到 provenance、資料正確性或安全邊界等高風險問題時，**允許直接改 schema、搬移／重建／覆寫既有資料與調整介面**；不要為了保留已知不正確的相容性而疊 workaround。仍須保留 Neo4j dump／資料備份、dry-run、migration manifest、reconciliation 與測試，確保變更可驗證、可回復。此授權不等於任意擴 scope；只用於修正已確認的高風險設計問題。

**⚠ 適用範圍（2026-08-13 補；本條寫於只有 Neo4j 的時期）：** 只適用 **Engine A graph、tracked schema 與可由 ETL 重建的 projection**。**不適用 private append-only authority**——Engine C 的 manual observation ledger（`library/private/engine_c/`）與 Decision Store（`library/private/decision_lab/`）都是**沒有第二份來源、Git 救不回**的真相。那兩者依各自契約辦理：只允許 backup／restore 與 append-only correction，**不做破壞性 reset、不覆寫、不重建**；發現錯誤用新的 correction record supersede 舊筆，兩筆都留在 ledger 裡。判準：**問「這筆資料今天重新取一次拿得回來嗎？」拿得回來 → 適用本條；拿不回來 → 只能 append。**

### L11 — 自己引用的「事實」要套跟圖裡 claim 同一套追源紀律（尤其審計／法律術語）

**事發（2026-07-20）：** 追 SIVE 的 Ningi 做空 audit 時，把「公司／Board 在 2025 年報**自揭** material going-concern uncertainty」誤述成「**審計出具** going-concern 保留意見」，還在 audit ledger／trace 報告裡標成「公司 tier-1 審計佐證」。實際來源只是二手聚合新聞的措辭「auditor going-concern qualification」＋ 自家二手 memo，沒追到逐字一手。諷刺的是當下正在執行 source-trace、正在替 SIVE 掛 credibility hold——對圖裡的 claim 嚴格追源，對自己口頭引用的事實卻放鬆。被使用者追問「這是哪份文件」後，才逐字核 AR PDF（Deloitte 簽證）發現落差：一手只支持「公司自揭 material uncertainty」，`qualified opinion`／`material uncertainty related to going concern` 等審計正式用語在可抽文字中為 0。

**通用判準（下次這樣想）：**
1. **具體審計／法律術語的措辭精度本身就是一個 claim。** qualified opinion、going-concern qualification、restatement、default、fraud、sole_source 這類詞，必須一手核對、不能沿用二手框架。「公司自揭 material uncertainty」≠「審計出具保留意見」，強度與責任主體都不同。
2. **對自己要輸出的事實，套用跟圖裡 claim 同一套 tier 與追源紀律。** 方向「感覺對」、剛好嵌得進已成形的敘事時，恰恰最該起疑（確認偏誤）；別對外部 claim 嚴、對自己引用鬆（雙重標準）。
3. **多個二手都這樣說 ≠ 一手已證實。** 它們可能同源於一個原始誤述（假交叉驗證）；見 L8（來源獨立性：供應商／單一來源自報不算獨立佐證）與 source-trace 的 tier 3–4 隔離原則。
4. **追源前先 grep 自家庫。** 一手常常已 ingest 在手邊（此例 raw excerpt 裡其實寫的是中性的「prepared on a going concern basis」＋一個風險段標題，早該提醒我那跟「審計保留意見」不是同一件事）。
5. **「我找不到」與「它不存在」是兩個不同的 claim，後者舉證責任高得多**（2026-08-15，原列於 L15）。工具回報的「沒有」先問它是不是「讀不到」：WebFetch 對 8.6MB PDF 回 `NO MAJOR CUSTOMER NOTE`，同時自陳解析失敗（兩義訊號，L12）。**關鍵字未命中要改用語意定位**（分部附註／IFRS 8 段落／目錄），不是換幾個關鍵字再放棄——搜 `accounted for` 而年報寫 `account for`，一個時態差異就造出「這個 gate 對非美股結構性不可及」的架構級假結論；真相是 SIVE 用 Note 5、IQE 用 Note 4.3，兩者都揭露。
6. **同一套紀律適用於自己的技術診斷，不只引用的事實（2026-08-19 補）。** 一天內三個診斷落地後被推翻，共同形狀是**錯誤朝「有洞察力的結論」偏**，且每個都能用本檔的 lesson 語言包裝——**能套進某條 L 只代表值得查，不代表已經查過**。落地前跑一條**試圖讓結論變成假**的命令（不是驗證它為真）；三次都有 30 秒可否證的命令而沒人跑。清單與各自的否證命令見 [`ROADMAP.md`「已撤回的診斷」](docs/ROADMAP.md)。

### L12 — 一個表示承載兩種語意：閘門顆粒度錯位的共同形狀

**事發（2026-08-05）：** 一個 session 內修掉四個表面無關的缺陷——LSE 標的行情永遠 quarantine（`currency` 同時是報價單位 GBp 與結算幣別 GBP）、歐洲標的整份行情被一根未結算 bar 廢掉（`market_history_row_invalid` 同時是「值缺席」與「值損毀」）、人工 runway 觀測永遠過期（`financial_freshness_days` 同時管每日快照與財報週期兩種節奏）、待辦池無法得知項目已完成（collector 回傳 `[]` 同時是「成功但無結果」與「執行失敗」）。分屬 Engine B/C/D，卻是同一個形狀。

**判準：** 某個表示同時承載兩種語意時，下游被迫二選一，而**兩邊都是錯的**——這正是它難修、也活得久的原因。修法形狀永遠一樣：**不是放寬也不是收緊，是先分開再各自定規則**；分開後每一邊都能套用比原本更嚴格的規則，混在一起時只能取兩者的下限。

**最有用的兩個訊號：**（a）**兩個修法方向都會壞**——若「放寬」與「收緊」都能舉出具體災難，多半不是參數沒調好，是兩件事被壓在一起；（b）**修法讓警報消失得太乾淨**——把 registry 直接改成 ISO code 會通過所有驗證、清掉所有 blocker，卻餵出差 100 倍的價格，比原本整份 quarantine 危險得多（同 L11 的確認偏誤）。

另一個相鄰但不同的毛病是**因果被截斷**：`action_card` 由 `core_blockers` 判成 REVIEW，卻只把 `assessment_blockers` 放進自己的 `blockers`，下游只能從殘餘資訊猜原因。判準：**任何會改變輸出的輸入，都必須出現在該輸出自己的證據欄位裡。**

完整實例、五個訊號與修法對照見 [`docs/solutions/architecture-patterns/one-representation-two-meanings.md`](docs/solutions/architecture-patterns/one-representation-two-meanings.md)。

### L13 — 基礎設施改動的驗收是「端到端有產出」，不是「元件會動」

**事發（2026-08-11～12，兩天內三次）：**（一）補上 SIVE／IQE filing watcher，feed 抓得到、`parse_rss` 解得出、harvest 實跑 78 筆 new，於是宣告「SIVE 從完全靠人記得變成有自動監測」——但那 78 筆全部躺在 `pending`，排程只 triage 自己當輪抓到的，`pending` 不進 pq1 drain。管子只接了一頭。（二）替待辦項目綁 `--event-type decision_evidence_delta`，它正確喚醒了，於是宣告「這樣比較嚴格」——但 `reactivation_event` 只寫不讀，沒有 consumed-marker，於是每次 sync 都重新喚醒，等待條件永遠黏不住。（三）從 `counts` 沒有 `researching`／`action_prepared` 推論「排程沒跑 pq1」——但**跑完**的 drain 同樣不留 in-flight 狀態，實際上 5 個 slot 全滿。

**判準：**
1. **驗收條件寫成「產出出現在下游消費者手上」，不是「這一步回傳成功」。** 交付前必須答得出「這條路徑的產出最後出現在哪裡、誰會消費它」；答不出來就是死路，不算完成。
2. **最危險的是成功與失敗在同一個訊號上同形**——空集合、沒有 in-flight 狀態、回傳 OK 都是。要驗就驗那個會因為「真的成功」而改變的東西（例如再跑一次 sync 看「新增 0」，而不是看命令有沒有報錯）。
3. 這是 L12 的操作版：L12 說一個表示承載兩種語意會讓下游二選一；這裡是**驗證者**自己讀了那個兩義訊號，於是把「沒發生」誤讀成「已完成」。

---

### L14 — 未經量測的機制不得享有默認信任，**gate 也不例外**

**事發（2026-08-13）：** 「AXTI／LITE／COHR／SIVE 兩週漲 31–64%，系統為何沒形成入場判斷」。
實測 72 筆 decision 的 `live_supported_range` **全是 [0,0]**、`axis_ceiling` 從未超過
0.002、已量測 outcome 0/8；三個真正的資本上限（單筆 5%、單 probe 0.5%、probe book 2%）
**一次都沒 binding 過**——100% 的歸零由資料與研究完整度造成。而同一診斷已被正確寫下
四次，每次都沒改到 binding constraint。

**判準：**
1. **驗收條件寫成「現有資料有幾筆真的變了」**，不是「這一步回傳成功」。答案是 0 就代表
   沒改到 binding constraint，不論改動本身多正確，**不得標記完成**。這是 L13 的量化版。
2. **gate 本身也要被驗證。** 2026-08-01 已對技術訊號執行過（0 勝 3 敗，於是移出資本
   路徑），同一標準卻從未套用到 blocker。**「更嚴格比較安全」不是免於驗證的理由。**
3. **順序不可顛倒：先量測，後放閘。** 先放寬而沒有量測 ＝ 拆煞車不裝儀表板。
4. 判斷 gate 有沒有用的三個**免 outcome** 測試：**恆亮**（觸發率近 100% ＝ 零鑑別力）、
   **不會滅**（清除率近 0 ＝ 那是牆不是閘門）、**講不出因果機制**（說不出「亮起時標的更
   可能變壞」＝ 行政流程假扮風控）。第四種失效「會滅但沒用」需要 outcome 才測得了。
5. **每次修東西先分兩類**，否則會「東補西補一個月而沒有方向」（2026-08-13 使用者實測感受）：
   **維持營運**（管線壞了、腳本報錯）直接修、不必對齊終點，但**它也不算進展**；
   **改變行為**（新增／收緊 gate、改判準、改欄位語意、改 sizing）動手前必須答出
   **「這會讓哪個 baseline 數字變？」**，答不出來就不做或先進 ROADMAP 未排程。
   混在一起就是那一個月的成因：管線修復帶來進展的**感覺**，改變行為的那些從未被量測。

**⚠ 寫進本檔不等於會生效。** L12（08-06）與其操作版 L13（08-12）相隔六天，就是同一形狀
在本檔已完整載入的情況下復發。**真正的防呆是會自己出現的常駐計數器，不是要人讀的段落**
（現行：daily brief 首屏的「非零 live 區間 / 已量測 outcome」兩個數字）。

**動 Engine D 資本層前必讀**
[`2026-08-13-capital-expression-direction`](docs/brainstorms/2026-08-13-capital-expression-direction-requirements.md)
的 §2（凍結 baseline，audit 拿它做 diff）與 §4（步驟與驗收條件）。該檔 §1 的 D1–D5 是
**方向、尚未成為政策**——實測前不得升格為本檔規則。

---

### L15 — Gate 與語言處理的分工：先解析「這是什麼」，再判「它算不算數」

**事發（2026-08-13～14）：** 五軸 evidence gate 用 `ref in reference_index`（exact 字串相等）
當判準。研究者寫 `yfinance://history`，index 的 key 是 `yfinance://history/AAOI`——
**一個少了 ticker 後綴的字串，讓整筆決策的資本歸零**，實測 22 次。gate 問的是字串相不相等，
真正要問的是「這個引用指不指向同一份來源」；用機械比對當語意問題的代理，**攔下的是格式
不是風險**。同輪另發現判準是 `any(失敗)` 而非「至少一個合格」，多附一個脈絡引用就整軸歸零。

**判準：**
1. **gate 的正當性來自「它對目標有幫助」，不來自「它存在」或「它比較嚴格」**（L14 延伸）。
   自問：**這個 gate 攔下的，是不是它想攔的東西？** 若攔的是格式、時區、字串後綴、單位
   寫法、缺一個參數——它攔錯了，該修的是它問問題的方式。
2. **語意交給語言處理，權限永遠 deterministic。**
   語意（LLM 擅長、機械比對必誤判）：兩個引用是否同一來源、某陳述算不算獨立佐證、
   推文在講哪家公司、文件屬於哪個 `origin_entity`。
   權限（永遠由 registry／人工 gate 決定）：authority 歸屬、evidence tier、資本、
   graph admission、live choice。**LLM 可以解析與提議，不可以授權**；不確定時用語言能力
   去解決、不要被自己的 gate 卡死，但解析結果必須落成可稽核的確定性紀錄。
3. **順序不可反：先解析身分，再查權限。** 解析時若偏好「能通過的答案」，等於讓引用去尋找
   能通過的權威——那正是 L8／L11 要防的 laundering（實作見 `sizing.py::_resolve_reference`）。
4. **放寬解析不等於放寬判準——分開之後兩邊都要更嚴。** 引用改成無歧義解析（exact →
   唯一前綴，兩個以上候選就不猜）＋「至少一個合格」之後，**零個合格仍然歸零**，且不合格者
   必須列進 `context_only_refs` 現形供稽核。這是 L12 的形狀。

---

### L16 — 分類已經有 SSOT 時，要讓它**跟著資料走**到需要它的地方

**事發（2026-08-26，一天內三次）：** 三次把已有唯一權威的分類又自己推導一份——
① `trace_status` 自創 9 個同義詞，而 `trace_backlog` 正是靠其中兩個值決定 lead 去留；
② 在 `engine_b.todo` 手寫一組 stale 清單去判斷「哪些 blocker 要人動手」，而
`config/decision_blockers.json` 的 `resolution_mode` 早就是唯一權威；
③ 口頭把 `co:axt` 的 `system_internal` blocker 斷言成「bug 要解」，而 registry 的
`next_step` 直接寫著怎麼處理——實測一次 reassess 就從 REVIEW 變 NO ACTION。

**三次都不是粗心。共同形狀是：我需要一個分類，系統有，但我手上的介面沒帶。**
在那個位置上自己猜一份是阻力最小的路，而且**猜錯不會有任何東西壞掉**，它只會安靜偏掉。
偏的方向還是固定的——**永遠偏向「看起來需要更多研究」**，因為不確定時把東西說成
「要人處理」感覺比較安全。那正是讓待辦池訊噪比降到 1:1 的機制。

**判準：**
1. 需要一個分類時先問兩層，缺一不可：**(a) 這個分類有 SSOT 嗎？**
   **(b) 它有沒有跟著資料送到需要它的地方？** 三次全部死在第 (b) 層——SSOT 都在，
   只是沒送出來。只問 (a) 會得到「有啊」然後繼續猜。
2. **修法是把分類附到 payload 上，不是再寫一份文件叫人記得去查。**
   實例：brief item 從只給 blocker code 改成同時給 `blockers_by_mode`
   （`user_decision`／`system_internal`／`awaiting_external`），消費端從此沒有動機自己猜。
   同 L14「真正的防呆是會自己出現的常駐計數器，不是要人讀的段落」。
3. **字彙一旦有行為後果就必須被強制。** `trace_status` 是自由字串卻決定 lead 去留，
   於是打錯不報錯、只是靜默沉底。收斂成封閉字彙後，**寫入端連已淘汰的同義詞都要拒絕**——
   同義詞的危險不是拼法不整齊，是它讓寫的人以為表達了一個沒被記錄的區別。
4. ⚠ **不要用會誤報的 linter 來防這件事。** 同日實測過「掃描重複字彙分組」的原型：
   16 個命中有 14 個在 `tests/`（測試斷言特定 code 集合本來就正當），2 個 production
   命中都是有書面理由的政策集合（如 `store.py::_HARD_CAP_BLOCKERS`）。
   做一個會誤報的防呆來防止過度工程，本身就是過度工程。

**與 L15 的分工：** L15 講「解析與權限要分開」；本條講**分開之後，分類結果必須送到
下游手上**。否則每個消費端都會重造一份，而重造品會立刻開始偏離。

---

## 文件化學習

踩過的坑與設計決定沉澱在 `docs/solutions/`（按問題類型分類，帶 YAML frontmatter 可搜尋：`module`, `tags`, `problem_type`）；共用領域詞彙見 `CONCEPTS.md`。

**遇到「某個事實塞不進既有欄位／狀態／關係」時先讀 [`docs/solutions/architecture-patterns/closed-vocabulary-registry.md`](docs/solutions/architecture-patterns/closed-vocabulary-registry.md)。** 它列出每個封閉字彙住在哪、能不能擴充、以及擴充要改 config 還是改 code，省去逐一讀 Python 才知道邊界的成本。判準是 taxonomy（世界會長出新品類→字彙留鬆，放 `config/`／`schema/`）vs contract（刻意有限→打開它是 bug）。⚠ 新增 `config/*.json` 必須同時在 `.gitignore` 補 `!config/<name>.json`，否則 fresh clone 與另一個 agent 會缺檔而靜默失效；`tests/test_config_tracking.py` 是這道剎車。

---

## Imported Claude Cowork project instructions
