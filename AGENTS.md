# StockBotv2 — 專案記憶 (Project Memory)

> 任何 session 在此資料夾開工前先讀本檔。這裡記錄定案、判準、與踩過的坑。

## Claude Code / Codex 雙代理相容契約

- **專案記憶唯一權威：** `AGENTS.md`。`CLAUDE.md` 只用 `@AGENTS.md` 匯入，不再複製內容；更新專案記憶只改本檔。
- **研究 skill 唯一權威：** `skills/<name>/SKILL.md`。`.agents/skills/`（Codex）與 `.claude/skills/`（Claude Code）是生成的薄轉接層，不直接手改。
- 新增 skill 或修改 skill 的 `name` / `description` 後，執行 `python scripts/sync_agent_skills.py`；交接前用 `python scripts/sync_agent_skills.py --check` 驗證兩端無漂移。
- **平台設定分開：** Codex 設定放 `.codex/`，Claude Code 本機設定放 `.claude/settings.local.json`；共用行為應呼叫同一支 repo Python 程式，不在兩份 hook 裡複製業務邏輯。
- **切換原則：** 同一 working tree 只讓一個 agent 寫入；序列切換沿用同一 feature branch。若兩邊同時工作，必須使用不同 worktree / branch。交接訊息至少附目前 plan 路徑、進行中的 U-ID、`git status --short`、最後一次驗證命令與結果。
- 本機開發 agent 可以是 Claude Code 或 Codex；架構中明指 `claude.ai` custom connector 的遠端流程仍維持 Claude，不因本機開發工具切換而改名。

## 工作語言（繁體中文）

**與使用者的所有溝通、以及實作過程本身的敘述，一律用繁體中文——不只是最終答案，過程也是。**

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
| `skills/signal-triage` | 週掃 harvest 後判斷是否值得列入 Topic Digest（深挖由本機 session 點名） |
| `skills/source-trace` | 推文／轉述／截圖／二手報導先追回原文；tier 3–4 未果隔離 |
| `skills/evidence-conflict-resolution` | EdgeAssertion 屬性衝突產 proposal；只在人工核准後寫 resolution |

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
- **引擎B（自動 harvest 未建；ad hoc 手機入口已建）：** X 推文/小道消息 → 線索 → 走 `skills/lead-intake` 閘門 → Research Action → 入庫。自動 X/trending harvest 仍未建。
- **每週審查（cloud routine，台北 06:00，`crons/weekly_scan_prompt.md`）：** 只做 topic discovery（不追源、不抽取，深挖由使用者本機 session 點名「research topic N」）+ thesis 生命週期**到期制**核查（L7 的流程實作；狀態存 `thesis/lifecycle.json`，active 90 天／watch 30 天）+ 系統健康審查（審查查詢唯一權威 `query/health_audit.py`；Engine C 等本機項目由使用者跑 `python query/health_audit.py --local` 補齊）。原 `crons/thesis_monitor_prompt.md` 季度 cron 已併入此處刪除（CronCreate 7 天過期，跑不起來）。
- **各類來源的 AI 抽取 instruction：** [`docs/extraction-instructions.md`](docs/extraction-instructions.md)
- **遠端存取（手機 App / web / cloud routine 讀寫圖與查 Engine C）：** 本機 MCP server（`mcp_server/graph_mcp.py`）+ Cloudflare Tunnel + connector。九工具 surface 沒有 remote Git；完整資料流、安全邊界、Research Action／storage 協定與跨平台限制：[`docs/remote-access-architecture.md`](docs/remote-access-architecture.md)

---

## 什麼值得開發 / 什麼交給 Claude

### 值得開發（邊際效益高、省 token、跨 session 有用）

| 類別 | 具體項目 | 理由 |
|------|---------|------|
| 知識累積 | 更多公司 onboarding、更多高品質文件 | 圖的大小決定回答的深度 |
| Skill 介面 | SKILL.md 檔（已有 7 個）| 讓 Claude Code / Codex 每次都能正確使用記憶 |
| 高槓桿 fetcher | EDGAR 季報自動更新、arXiv 論文抓取 | 減少人工取文件摩擦 |
| G5 L8 偏誤檢查 | `validate.py` 加 origin_entity 同質性警告（2026-07-17 已實作：供應商自報 sole_source 在文件層 WARN） | 低工程量、高資料品質槓桿 |

### 不值得自己開發（Claude 做得更好或沒意義）

| 類別 | 理由 |
|------|------|
| 長文解讀、文章分析 | Claude 的 context window + 推理比自製 pipeline 好 |
| Text2Cypher / 對話式查詢 | 直接給 Claude 原始 graph context，Claude 自己解讀 |
| 自動選文件頁面（G2）| Claude 看 TOC 判斷比 embedding filter 更準確 |
| 節點重要性評分（G8）| Claude 從 edge 數量、tier、公司規模能即時判斷 |
| 公司識別（G1）| Claude training data 知道公司是誰，hallucination 風險由 TICKER_MAP 控制 |
| 自動代替使用者做最終投資決定或送單 | Engine D 可以提出有邊界的建議與 paper counterfactual，但 live 接受、覆寫與 broker 下單永遠需要人工 |

---

## 引擎B（信號入庫）設計草稿

**定位：** X / SubStack 信號 → 用戶判斷 → `/lead-intake` → 圖。引擎B 是「人工閘門前的信號彙整」，不是自動入庫。

**已確認的初始信號來源：**
- `aleabitoreddit`：X 帳號，有同名 SubStack。會寫產業供應鏈深度分析（evidence tier 3）。是 SIVE Sivers 客戶地圖的原始來源。

**Cron 追蹤方案（待實作，已定案方向）：**
- **RSS 路線（免費，優先）：** SubStack 有 RSS feed（`https://aleabitoreddit.substack.com/feed`）；cron 定期抓新文章，存成 pending leads 清單，每次 session 開頭提示「有 N 條待判斷」。
  - 讀取注意（2026-07-21 實測）：feed 本身正常（HTTP 200、合法 RSS XML），但 **channel 標題是 "Serenity"、不是帳號名**——看到 "Serenity" 就是這個 feed，別當成別的來源。Substack 首頁需 JavaScript、不能直接爬。**讀取器解析失敗 ≠ 無新文**：失敗時必須 fallback 到 `site:aleabitoreddit.substack.com` web search，並在報告註明用了 fallback。
- **X API 路線（$100/mo）：** 可抓短推文，但 SubStack 已含主要深度文章，RSS 對 aleabitoreddit 夠用。
- **入庫邊界：** aleabitoreddit 的內容最高只能是 `evidence_tier: 3`，需客戶端文件升級 L8 才能用於 Lane Memo。

**待做：** 建 `crons/` 目錄下的 RSS 抓取腳本 + `pending_leads.json` 格式定義。

---

## 開發優先序

> `docs/plans/` 已轉純歷史（見 [`docs/plans/README.md`](docs/plans/README.md)）；當前工作起點只看本節。
> 小工作直接照本節做、不再開 plan 檔；只有大型開發才新建 plan。

**（已完成）M1 CPO Depth Sprint** — 2026-07-18 達標：AXT 已 onboard（`TICKER_MAP` 有 `co:axt: "AXTI"`）；Coherent／Lumentum／NVIDIA／Broadcom 各 ≥3 個 distinct `origin_entity`；20 條 edge conflict 全數 resolve 並 project 進圖（`python loader/edge_resolution.py project --dry-run` 的 `open_conflicts=0`）。**遺留 backlog（仍開）：** TSEM intake（ra_2bf1494b）的 2027–29 光通訊集體擴產 oversupply watch、MACOM/Semtech 作為 Tower TIA 客戶（tier 3，待客戶端揭露印證）、GF 對 Tower 專利訴訟未追源。

**（已完成）Action-Oriented Alpha Decision Lab v1** — 2026-07-21 完成：本機手動 Signal → Shadow Observation → Coverage／Confidence → lane-specific sizing → funded paper／Action Card → outcome 閉環。SIVE／空圖 fixtures、Engine C rebuild、Decision Store backup/restore、paper replay與 Neo4j 唯讀 preservation proof 均有測試。Engine C 與 Decision／paper runtime 已私有化且不再由 Git 追蹤；live inventory 只認 Google Sheet，交易仍由使用者手動執行。唯一歷史 plan：[`docs/plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md`](docs/plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md)。**未包含：** 排程 Daily Brief、自動 harvest、remote decision MCP、broker routing。

**（已完成）Engine D operational workflow** — 2026-07-22 完成：`python -m decision_lab evaluate-signal "<Signal>"` 可由 raw Signal 自動完成 wide capture、exact identity、Engine A/C／market／FX／Sheet authority read、content-addressed freeze、Coverage／Confidence／sizing、atomic decision／eligible paper 與 Action Card；`reassess` 建立新 context 與 attributed delta、不改舊 decision；`today` 純讀輸出 `NO ACTION / REVIEW / TRADE / HEDGE`。正常入口不要求 internal digest／Coverage ID／idempotency key。Unresolved identity、空圖、missing／stale／manual_required 會保存 cohort／Shadow、歸零 funded range並產 bounded work order。Live 仍只由明確 `record-choice`、使用者手動下單及 `record-fill` 建立 facts，Google Sheet 不被 Engine D 寫回。歷史 plan：[`docs/plans/2026-07-22-001-feat-engine-d-operational-workflow-plan.md`](docs/plans/2026-07-22-001-feat-engine-d-operational-workflow-plan.md)。**仍未包含：** 排程、notification、remote Decision MCP、broker routing、自動 harvest。

**Operational commands／外部設定：**
- 研究預設：`python -m decision_lab evaluate-signal "<Signal>" --ticker <TICKER> --intent research --format markdown`；只有使用者明確要求才用 `paper`／`live`。
- 新資料重評：`python -m decision_lab reassess <decision_id> --assessment <assessment.json> --intent <research|paper|live> --format markdown`；live 另加 `--confirm-holdings`。
- 今日摘要：`python -m decision_lab today --format markdown`；既有卡片：`python -m decision_lab card <decision_id>`。
- Engine A exact-name／bounded context 需專用唯讀帳號：`NEO4J_URI`、`NEO4J_DECISION_READER_USER`、`NEO4J_DECISION_READER_PASSWORD`，可選 `NEO4J_DATABASE`；不得 fallback 到可寫帳號。
- Live holdings 需 `GSHEETS_SERVICE_ACCOUNT_JSON`、`GSHEETS_SPREADSHEET_ID`，可選 `GSHEETS_SHEET_NAME`。Sheet operational rows 必須有 `ticker`、`shares`、`currency`、`market_value_base`、`nav_base`、`base_currency`；成本基礎不能代替 mark-to-market NAV。
- Price／FX 預設沿用 yfinance（無 API key）；Engine C authority 仍由 ignored private runtime pointer／既有 Postgres env 決定。非同幣 FX 缺失或方向不符一律 fail closed。

**（已完成）第二條垂直切片／L9 前置條件 #1** — 2026-07-19 由 commit `a7abdf5` 交付 AMAT/LRCX mature-node Lane Memo、evidence manifest 與 scoring；主題為非 AI／非 CPO，評分 23/30（可信度 4、可證偽性 4、市場差異度 4），`thesis/preconditions.py` 的 `_check_second_slice()` 已通過。歷史規格：[`docs/plans/2026-07-08-005-feat-second-vertical-slice-plan.md`](docs/plans/2026-07-08-005-feat-second-vertical-slice-plan.md)。

1. **（已完成 2026-07-22）L9 剩餘財務核驗缺口**
   — COHR「客戶集中度」與「Backlog／訂單能見度」已以一手 filing 補入 Engine C manual observation ledger（append-only，含逐字 provenance）：客戶集中度出自 FY2025 10-K segment note「Major Customers」（兩大客戶各佔 12%／10%，主要來自 Networking segment；另註 NVIDIA 2026-03-02 投資 $2B＋多年期產能協議至 2030 的前瞻集中度旗標，出自 Q3 FY2026 10-Q）；COHR 不揭露美元 backlog／RPO，依規則填替代指標＝Q4 FY2026 guided revenue $1.91B–$2.05B（8-K EX-99.1，filed 2026-05-06）＋ NVIDIA 產能協議。`python thesis/preconditions.py` 全綠、`python engine_c/checklist.py COHR` 五項 gate_pass=true；**L9 三前置條件全部達標，投資諮詢 gate 開放**。一手文件存 `library/raw/cohr_10_k_20250815.txt`、`cohr_10_q_20260506.txt`、`cohr_ex991_20260506.txt`。

2. **知識覆蓋自動化**
   — `fetchers/edgar.py` 的 10-Q CLI 已可用（2026-07-18 驗證 AMAT/LRCX 最新 10-Q 抓取正常：`python fetchers/edgar.py --ticker AMAT --forms 10-Q --n 1`）。剩：SIVE 找 3 個不同 `origin_entity` 的獨立來源；RSS pending leads（見上方引擎B 待做）。先讓手機 ad hoc loop 穩定，再擴自動 harvest。

---

## 來源登記表（一手來源優先）

通用搜尋（Tavily 等）只配 LLM 品質評分 gate，用在第三層。一手來源依市場分路；
**LLM／routine 可執行的機器版路由與未果處置唯一權威是 [`skills/source-trace/SKILL.md`](skills/source-trace/SKILL.md)**，此處只留快速記憶：

- **美股：** SEC EDGAR（10-K/10-Q/8-K/S-1/Form 4）、法說會逐字稿、IR 簡報、客戶/供應商 filings。
- **台股：** 公開資訊觀測站（MOPS）、**月營收揭露**、法說會/IR、上下游上市公司交叉驗證。
- **A股（備用）：** 年報/季報/臨時公告、交易所問詢函、互動易、招投標/中標、環評能評、海關數據、上下游交叉驗證。
- **技術/學術：** arXiv + Semantic Scholar API、OFC/ECOC 議程與論文、公司技術白皮書、專利、標準組織。
- 核驗清單（出投資建議前必看）：客戶集中度、毛利率/產能利用率、backlog/營收結構、稀釋（增資/可轉債/SBC/內部人賣股）、估值壓力。

---

## v0 Schema

設計原則：表的「形狀」鎖死，字彙（type/relation/層級）用對照表留鬆；屬性按 L4「物理 / 關係 / 時變」三分歸位。完整欄位表、vocab、claims 格式、sole_source 驗證規則：見 [`schema/graph_schema.md`](schema/graph_schema.md)。

**快速記憶：**
- **圖公司 ID（`co:*`）不要憑公司名猜。** 唯一權威是 `config/company_identity.json`，由 `identity/registry.py` 載入；loader 的 `TICKER_MAP` 只是由同一 registry 生成的相容介面。查圖前先查 registry，或用 `query/health_audit.py` 的 `COMPANY_IDS_CYPHER` 列出圖中 Company 再比對。例：Sivers 是 `co:sivers_semiconductors`，不是 `co:sivers`（2026-07-21 週掃即因猜 ID 未命中而漏掉 Sivers 的圖內比對）。ID 未命中時要區分「ID 沒解析對」與「圖中真無此公司」，不能默默跳過。
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

---

<!-- ===== 自訂：Skill 輸出翻譯（2026-06 加） ===== -->
## Skill 輸出語言
併入上方「## 工作語言（繁體中文）」——Skill 最終輸出（含 last-30-days）一律翻成繁體中文；整個實作過程亦同。
<!-- ===== 自訂結束 ===== -->

## Imported Claude Cowork project instructions
