# StockBotv2 — 專案記憶 (Project Memory)

> 任何 session 在此資料夾開工前先讀本檔。這裡記錄定案、判準、與踩過的坑。

## 專案一句話
高度利用 LLM 做「AI 產業鏈科研 + 股市量化」的系統,產出個股完整報告與產業 thesis,作為投資指引。本機單人自用。使用者會寫 Python、碰過 API。

## 三大引擎
- **引擎A — 科研引擎:** 抓高品質報告/報導/論文/官方資訊,建知識庫(property graph)+ RAG。核心、最難、最優先確保深度。
- **引擎B — SNS 語意爬蟲:** X 大佬推文/小道消息 → 找線索 → 餵給 A。本身不進知識庫,除非推文是高密度技術內容。
- **引擎C — 基本面引擎:** 爬客觀數字,出投資建議。tabular / 時間序列為主。

## 關鍵定案 (Decisions)
- **開發工具:** 主力 Claude Code(或 Cursor 接 Claude),Cursor 當輔助 review。
- **資料庫(polyglot):** 知識圖譜 → **Neo4j**;基本面數字/時間序列/文件 metadata → **Postgres**;向量 RAG 先用 Neo4j 內建向量,量大再分出去。
- **抽取與 DB 解耦:** `extract.py` 只輸出 DB 無關的 node/edge JSON 中介格式;「JSON → 寫進 DB」是可替換的 loader。DB 選擇不可綁死資料。
- **graph 用 property graph,不用 tree。** 供應鏈/技術拓樸本質是 DAG。節點帶 `type` + `abstraction_level`,邊帶 `relation` 型別。每個 node/edge 必掛 `source_ids` + `confidence`(來源可追溯是鐵律)。
- **schema 字彙(type/relation 種類)用對照表管理、留鬆;表的「形狀」鎖死。** 加新邊型別 = 加一列設定,不動表結構。
- **開發順序:垂直切片優先。** 第一條切片 = CPO/矽光子,一個標的端到端跑通(手選 8~10 篇一手資料 → extract → 圖+向量 → 出 thesis → 人工評分),再談自動化。引擎順序 C → A → B(C 最客觀好驗證;B 最後做)。
- **一手來源優先於通用搜尋:** 通用搜尋(Tavily 等)只配 LLM 品質評分 gate,用在第三層。一手來源依市場分路(來源登記表,借自 serenity-skill 的 market-source-playbook):
  - **美股:** SEC EDGAR(10-K/10-Q/8-K/S-1/Form 4)、法說會逐字稿、IR 簡報、客戶/供應商 filings。
  - **台股:** 公開資訊觀測站(MOPS)、**月營收揭露**、法說會 / IR、上下游上市公司交叉驗證。
  - **A股(備用):** 年報/季報/臨時公告、交易所問詢函、互動易、招投標/中標、環評能評、海關數據、上下游交叉驗證。
  - **技術/學術:** arXiv + Semantic Scholar API、OFC/ECOC 議程與論文、公司技術白皮書、專利、標準組織。
  - 核驗清單(出投資建議前必看):客戶集中度、毛利率/產能利用率、backlog/營收結構、稀釋(增資/可轉債/SBC/內部人賣股)、估值壓力。

## v0 Schema(定案,故意會壞、等真實資料來撞)

> 設計原則:表的「形狀」鎖死,字彙(type/relation/層級種類)用對照表留鬆。
> 方法論藍圖借自 chokepoint-atlas skill(見 L4),但只抄概念、不裝套件。

### 節點 `nodes`
欄位形狀(鎖死):`id, type, name, abstraction_level, role, aliases[], attributes(jsonb), confidence, source_ids[], updated_at`

- `type`(字彙,留鬆): Company | Product | TechNode | Material | Standard | Person
- `abstraction_level`(採 chokepoint-atlas 的 stack 分層,取代舊的籠統四層):
  `end_demand` | `network_systems` | `module_subsystem` | `device_chip` | `test_yield` | `foundry_packaging` | `equipment_epitaxy` | `materials_substrate`
- `role`(公司在 stack 的角色): leader | bottleneck_supplier | disruptor | foundry | test | network | adjacent_silicon | material_base
- **內在(慢變)瓶頸屬性放這裡:** `ramp_difficulty_intrinsic`(1-5,該品類本質上多難量產)、`concentration_score`(1-5,且應為**衍生值** = 數進入此 component 的供應邊並加權市占,存成有來源的快取,非手填)

### 邊 `edges`
欄位形狀(鎖死):`id, src_id, dst_id, relation, attributes(jsonb), confidence, source_ids[], updated_at`

- `relation`(字彙,留鬆): supplies_to | is_component_of | competes_with | enables | depends_on | invests_in | licenses_to
- **關係型(會隨另一端而變)瓶頸屬性放這裡:** `substitutability`(1-5)、`sole_source`(bool)、`lead_time`、`qualification_status`、supplier 端的 `ramp_execution`(這家供應商實際 ramp 能力,與 node 的內在難度分開)

### 證據與信心(四階,鐵律:每個 node/edge 必掛 source_ids)
`evidence_tier`:
1. **strongest** — filings / 法說會逐字稿 / IR 材料 / 客戶供應商直接揭露
2. **strong** — 官方供應商名單變動 / design-win 公告 / 產能擴張通知
3. **medium** — 可信產業報導 / 券商研究摘要
4. **weak** — 社群貼文 / 未證實論壇說法

`demand_proof_level`(需求主張的證據強度,**掛在需求主張/邊上,不是 node 靜態欄**): confirmed | guided | inferred | speculative

### 不進圖的東西(時變觀測,歸引擎B/C 的 Postgres 時間序列)
- `consensus_coverage`(underfollowed | emerging | crowded):這是**股票/公司的市場認知**,且會隨時間變,屬 Company 的帶時戳觀測,**不是物理 component 的靜態圖屬性**。

### 報告產出三級模板(借自 chokepoint-atlas output-formats)
1. **Directional Lane Memo**(先給方向):一句 thesis → 需求驅動 → stack 摘要 → 主瓶頸 → 最強證據 → 什麼會推翻它 → 接下來盯什麼
2. **Watchlist**(thesis 成立後才給名字):每檔附 role / 為何重要 / 已確認 / 待驗證 / 主風險
3. **Underwrite Sheet**(單一標的深挖)

每份 thesis/claim 必帶 `disproof_condition`(可證偽是一等公民)。

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
2. **值會隨時間變嗎?** 會 → 不是靜態圖屬性,是「帶時戳的觀測」(進 Postgres,不進圖)。
3. **講的是物理現實,還是證據強度 / 市場認知?** 後兩者 → 是 metadata 或市場狀態,不是實體屬性。

**結論:** 品類集中度/內在量產難度 = node(且集中度應衍生);可替代性/sole-source/lead-time/供應商 ramp 執行力 = edge;需求證據強度 = 證據 metadata 掛在主張上;市場擁擠度 = 時變觀測進 Postgres。
**一句話:** 瓶頸的本質是「一條關係會不會斷」,所以瓶頸的 alpha 大半在**邊**上,不在點上。別把分數無腦掛 node。

### L6 — 第一次真實抽取撞出的三個 schema/pipeline gap

**事發:** 用 Coherent Q3 FY2026 法說會 CPO 段落跑完 extract → validate → load → Browser review 後發現。

**Gap 1 — Claim 節點沒有 `name` 欄位**
Neo4j Browser 找不到 `name` 就拿 `confidence`(0.55)當顯示標籤,讓人以為是一個數值節點。
修法:loader 在寫入 Claim 時自動從 `statement` 截前 30 字填成 `name`,或 Browser query 時 `RETURN c.id + ": " + c.statement` 手動補。

**Gap 2 — `source_ids` 是文件內局部 ID,跨文件後無法在圖裡直接追溯**
樣本(s2/s4)與法說會(s2/s4)指向完全不同的 quote,但在 Neo4j 裡看節點的 `source_ids` 時無法知道是哪份文件的 s2。Sources 沒有存進 Neo4j,只存在各自 JSON 裡。
修法方向(v1):source ID 改成全域唯一格式 `<doc_id>_s<N>`(例: `coherent_q3fy26_s2`);或把 sources 也寫成 Neo4j 節點(`Source` label),讓圖本身可追溯。v0 先接受這個限制,追溯時需對照原始 JSON。

**Gap 3 — `ABOUT` 邊類型未在 `vocab.json` 登記**
loader 自動建 Claim→subject 的 `ABOUT` 關係,但這個 relation 沒有進 `schema/vocab.json`。validate.py 的 vocab 層目前只檢查 Edge(非 Claim 邊)的 relation 欄位,所以沒有報錯,但在字彙表上是個洞。
修法:在 `vocab.json` 的 `relation` 清單補上 `about`(或決定 Claim 邊不走 vocab 檢查);同步更新 `loader/validate.py` 說明。

**Gap 4 — LLM 從類別詞推斷出具體產品節點(幻覺型態)**
s15 quote 只說「data center interconnect 需求強」,LLM 自己推出 ZR/ZR+ DCI Transceivers 節點,但文件從未出現 ZR/ZR+ 字樣。quote 支持的是「DCI 需求」這個類別,不是具體型號。
修法:在 `prompts/extract_system.md` 加強規則:「若 quote 只提到產品類別(如 'data center interconnect'),不要抽出具體型號節點(如 ZR/ZR+)。具體產品名稱必須在 quote 裡逐字出現。」

**通用判準:**
1. Schema gap 只有在真實資料撞上去才會現形。凍結 v0 讓資料教你,比白板多討論兩週更有價值(L2 再次驗證)。
2. 局部 ID 在單文件內沒問題,跨文件 MERGE 後就會產生命名空間衝突。設計 ID 時要問「這個 ID 在系統全局還是文件局部?」
3. LLM 最常見的幻覺型態之一:從類別詞推斷出具體實體。review 時重點抽查「具體型號/公司名是否逐字出現在 quote 裡」。

### L5 — chokepoint-atlas / serenity-skill 是方法論藍圖,不是相依套件
兩者都是純 prompt 的研究方法論 skill(無狀態、模仿 Serenity/Crux 兩位 X 大佬),沒有持久化知識庫。**抄骨架(stack 分層、role 分類、證據四階、question-ladder 當抽取 prompt、output-formats 當報告模板),不裝套件、不綁相依。** 它們補的是「怎麼想」,我們專案補的是它們缺的「記得」(持久化知識庫)。注意是**單一 lens**(偏小市值瓶頸獵手、高風險),當眾多視角之一,別讓系統世界觀被綁死。

**已評估、可撿的零件:**
- serenity-skill 的 `market-source-playbook` → 已併入上方「一手來源」登記表(尤其台股 MOPS/月營收)。
- serenity-skill 的 `bottleneck-scorecard.json` + 評分腳本(8 因子 + 8 扣分項 → 排序)→ **留給引擎C 參考**,不是引擎A 要用的。它把因子攤平在一張表,正好反證 L4:持久化的庫必須拆到 node/edge/時變觀測,不能攤平。

<!-- ===== 自訂:Skill 輸出翻譯(2026-06 加) ===== -->
## Skill 輸出語言
執行 last-30-days skill 時,最終輸出翻成繁體中文...
<!-- ===== 自訂結束 ===== -->