# StockBotv2 — 專案記憶 (Project Memory)

> 任何 session 在此資料夾開工前先讀本檔。這裡記錄定案、判準、與踩過的坑。

## 定位一句話

**Claude + 結構化持久記憶 → 有根據的投資研究對話。**

使用者說公司名或 thesis → Claude 從 Neo4j 圖取 context、Engine C 取財務數據 → 合成有來源可追溯的回答。Claude 是分析引擎；圖譜是跨 session 的研究筆記本。本機單人自用，使用者會寫 Python、碰過 API。

---

## 系統架構（三層）

### Skill 層（Claude 的操作介面）
存在 `skills/` 目錄，每個 skill 是告訴 Claude「如何使用記憶層」的操作手冊。

| Skill | 觸發場景 |
|-------|---------|
| `skills/investment-research` | 問投資問題、評估標的、生成 thesis |
| `skills/lead-intake` | 丟來一條推文/報導/消息，要入庫 |
| `skills/blind-spot-audit` | 已有 thesis，要找反駁角度 |

### 記憶層（持久知識庫）
- **Neo4j 知識圖譜（引擎A）：** 供應鏈結構、技術關係、來源可追溯的主張。Property graph，不是 tree。
- **SQLite / Postgres 財務數據（引擎C）：** 財務快照、Watchlist Gate。零安裝預設用 SQLite；設 `POSTGRES_HOST`/`POSTGRES_DSN` 切換 Postgres。見 [`docs/solutions/tooling-decisions/engine-c-sqlite-dual-backend.md`](docs/solutions/tooling-decisions/engine-c-sqlite-dual-backend.md)。
- **向量 RAG：** 暫用 Neo4j 內建，量大再分。

### 管道層（知識入庫的機器）
```
文件 → library/raw/ → extract.py → loader/validate.py → loader/load_to_neo4j.py → Neo4j
fetchers/edgar.py ──────↑                        engine_c/etl_yfinance.py → SQLite
```
- **抽取與 DB 解耦：** `extract.py` 只輸出 DB 無關 JSON；loader 可替換。DB 選型不綁死資料。
- **fetchers（已有）：** `fetchers/edgar.py`（美股 SEC EDGAR，免費無 paywall）。
- **引擎B（未建）：** X 推文/小道消息 → 線索 → 走 `skills/lead-intake` 閘門 → 入庫。
- **各類來源的 AI 抽取 instruction：** [`docs/extraction-instructions.md`](docs/extraction-instructions.md)

---

## 什麼值得開發 / 什麼交給 Claude

### 值得開發（邊際效益高、省 token、跨 session 有用）

| 類別 | 具體項目 | 理由 |
|------|---------|------|
| 知識累積 | 更多公司 onboarding、更多高品質文件 | 圖的大小決定回答的深度 |
| Skill 介面 | SKILL.md 檔（已有 3 個）| 讓 Claude 每次都能正確使用記憶 |
| 高槓桿 fetcher | EDGAR 季報自動更新、arXiv 論文抓取 | 減少人工取文件摩擦 |
| G5 L8 偏誤檢查 | `validate.py` 加 origin_entity 同質性警告 | 低工程量、高資料品質槓桿 |

### 不值得自己開發（Claude 做得更好或沒意義）

| 類別 | 理由 |
|------|------|
| 長文解讀、文章分析 | Claude 的 context window + 推理比自製 pipeline 好 |
| Text2Cypher / 對話式查詢 | 直接給 Claude 原始 graph context，Claude 自己解讀 |
| 自動選文件頁面（G2）| Claude 看 TOC 判斷比 embedding filter 更準確 |
| 節點重要性評分（G8）| Claude 從 edge 數量、tier、公司規模能即時判斷 |
| 公司識別（G1）| Claude training data 知道公司是誰，hallucination 風險由 TICKER_MAP 控制 |
| 自動投資決策 | 永遠需要人工決策，不是開發方向 |

---

## 引擎B（信號入庫）設計草稿

**定位：** X / SubStack 信號 → 用戶判斷 → `/lead-intake` → 圖。引擎B 是「人工閘門前的信號彙整」，不是自動入庫。

**已確認的初始信號來源：**
- `aleabitoreddit`：X 帳號，有同名 SubStack。會寫產業供應鏈深度分析（evidence tier 3）。是 SIVE Sivers 客戶地圖的原始來源。

**Cron 追蹤方案（待實作，已定案方向）：**
- **RSS 路線（免費，優先）：** SubStack 有 RSS feed（`https://aleabitoreddit.substack.com/feed`）；cron 定期抓新文章，存成 pending leads 清單，每次 session 開頭提示「有 N 條待判斷」。
- **X API 路線（$100/mo）：** 可抓短推文，但 SubStack 已含主要深度文章，RSS 對 aleabitoreddit 夠用。
- **入庫邊界：** aleabitoreddit 的內容最高只能是 `evidence_tier: 3`，需客戶端文件升級 L8 才能用於 Lane Memo。

**待做：** 建 `crons/` 目錄下的 RSS 抓取腳本 + `pending_leads.json` 格式定義。

---

## 開發優先序（接下來三件事）

1. **第二條垂直切片（非 AI / 非 CPO 主題）**
   — L9 前置條件；驗證方法論不是 AI 多頭特例，而是跨主題有效的框架。

2. **SIVE 來源品質升級**
   — 目前 SIVE 的關鍵主張多為自我報告（L8 弱）。找 3 個不同 `origin_entity` 的獨立來源（客戶端文件優先：Coherent 法說會提到 SIVE？O-Net 財報？）。

3. **EDGAR 季報自動更新**
   — `fetchers/edgar.py` 已有，加個 CLI 一鍵拉最新 10-Q（含 `--max-chars` guard），讓圖內美股公司的財務數據不過期。

---

## 來源登記表（一手來源優先）

通用搜尋（Tavily 等）只配 LLM 品質評分 gate，用在第三層。一手來源依市場分路：

- **美股：** SEC EDGAR（10-K/10-Q/8-K/S-1/Form 4）、法說會逐字稿、IR 簡報、客戶/供應商 filings。
- **台股：** 公開資訊觀測站（MOPS）、**月營收揭露**、法說會/IR、上下游上市公司交叉驗證。
- **A股（備用）：** 年報/季報/臨時公告、交易所問詢函、互動易、招投標/中標、環評能評、海關數據、上下游交叉驗證。
- **技術/學術：** arXiv + Semantic Scholar API、OFC/ECOC 議程與論文、公司技術白皮書、專利、標準組織。
- 核驗清單（出投資建議前必看）：客戶集中度、毛利率/產能利用率、backlog/營收結構、稀釋（增資/可轉債/SBC/內部人賣股）、估值壓力。

---

## v0 Schema

設計原則：表的「形狀」鎖死，字彙（type/relation/層級）用對照表留鬆；屬性按 L4「物理 / 關係 / 時變」三分歸位。完整欄位表、vocab、claims 格式、sole_source 驗證規則：見 [`schema/graph_schema.md`](schema/graph_schema.md)。

**快速記憶：**
- node 帶內在慢變屬性（`ramp_difficulty_intrinsic`、`concentration_score` 為衍生值非手填）
- edge 帶關係型屬性（`substitutability`、`sole_source`、`lead_time`、`ramp_execution`）
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

### L9 — 三引擎匯流的前置條件(Engine C 與投資諮詢開放前必做)
**Engine A→C join key：** Engine A 的圖節點（如 `co:coherent`）和 Engine C 的財務數字（Coherent 的毛利率）要能自動對齊，需要共同 ID（如 ticker `COHR`）。join key 由 `loader/load_to_neo4j.py` 的 `TICKER_MAP` 維護（靜態 lookup，不用 LLM 推斷）。私人公司映射到 `None`（不是空缺，是明確標記）。

**投資諮詢開放的三個前置條件（全部滿足才開放）：**
1. 第二條垂直切片必須是**非 AI / 非 CPO** 主題，且跑通相同的 extract → thesis → 評分流程。
2. thesis→部位的最小規則已定義（進場條件 / 單檔上限 / 持有期 / thesis 失效即出場），哪怕是人工執行的規則。見 [`docs/investment-sop.md`](docs/investment-sop.md)（`thesis/preconditions.py` 的 `_check_sop()` 依賴此檔）。
3. 財務核驗清單 5 項（客戶集中度 / 毛利率趨勢 / backlog / 稀釋 / 估值壓力）已能一鍵從 Engine C 查出，並且必須在 Watchlist 升格前執行。

---

## 文件化學習

踩過的坑與設計決定沉澱在 `docs/solutions/`（按問題類型分類，帶 YAML frontmatter 可搜尋：`module`, `tags`, `problem_type`）；共用領域詞彙見 `CONCEPTS.md`。

---

<!-- ===== 自訂：Skill 輸出翻譯（2026-06 加） ===== -->
## Skill 輸出語言
執行 last-30-days skill 時，最終輸出翻成繁體中文...
<!-- ===== 自訂結束 ===== -->