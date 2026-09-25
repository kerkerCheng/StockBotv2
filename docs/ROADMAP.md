# StockBotv2 — Roadmap（2026-09-22 重建：圖是中心）

> **本檔只放 active future work：Phase 與四欄（做什麼／為什麼／驗收／前置）。**
> 判準與邊界住 [`AGENTS.md`](../AGENTS.md)；程序住 [`OPERATIONS.md`](OPERATIONS.md)；
> 決定紀錄住 [`brainstorms/2026-09-22-graph-first-direction-decision.md`](brainstorms/2026-09-22-graph-first-direction-decision.md)（G1–G12）。
> 前一版（Alpha Edge Phase 0–7、amendment、backlog）逐字封存於
> [`archive/roadmap-alpha-edge-2026-09-22.md`](archive/roadmap-alpha-edge-2026-09-22.md)。
>
> ⚠ **驗收只准數圖、讀圖、敘事、等待 registry、追蹤表裡的東西**（G10）。本檔任何「幾檔通過某個 filter」型的驗收行都是違規，
> development-flow 八欄會把它判 NO_GO。
> ⚠ **現況數字會腐壞。** 每個數字附查證命令，引用前先跑。
> ⚠ **開發項只住這裡，不進 pq2。** 判準：`go` 之後改變的是「我知道什麼」（研究，pq2）還是「系統怎麼運作」（開發，本檔）。

---

## North Star

系統要能回答：**哪些邊緣小公司坐在一層被集中需求擠壓的薄供應層上；我們多早、憑哪條邊與哪段逐字知道；
判斷錯了什麼會先告訴我們；事後哪個管道與特徵真的產出了贏家。** 現行題材見〈研究主題範圍〉，本檔不綁題材。

```
來源選擇：公司的文件 → 層的文件                         【Phase 4】
    ↓
圖：節點／邊／逐字／provenance ＋ 入圖 gate                【不變】
    ↓
走圖（機械，零 LLM）：圖報洞 ＋ lead 點名 → 研究佇列       【Phase 2】
    ↓
讀圖（LLM，append-only）：層讀圖 ＋ 插槽讀圖              【Phase 2；研究並行】
    ↓                                  反證寫下 ──→ 鑄 watch    【Phase 1】
個股敘事（LLM，append-only）：哪幾層、占多少營收、誰想殺它  【Phase 3；研究並行】
    ↓                                  缺 X／等回落 ──→ 鑄 watch 【Phase 3】
三個財務是非題：會死嗎／已定價嗎／出現在數字裡了嗎         【Phase 3】
    ↓
人決定買不買、買多少；出場認反證；量測 power-law           【不變；Phase 5】

        等待 registry（已有，加「語意條件」kind）            【Phase 1】
        心跳：零 LLM 印 diff ｜ AI 層只讀 T0 篩過的文件 ｜「未檢 N」必印
```

**圖到人之間沒有任何一段算分數。** 舊管線在圖與人之間有十層，其中排序、籃子 filter、估值、多年橋、賭注四價、decision_lab 鑄號六層在 Phase 0 退役。

## 現在在哪裡（2026-09-22 快照）

| 事實 | 數字 | 查證 |
|---|---|---|
| 技術／產品／材料節點；其中圖上只有一家供應商的 | 186；121（65%） | 決定紀錄 §1.1 的 Cypher |
| 結構讀圖 ledger | 8 份，2 個節點 | `ls library/private/alpha/structure_readings/` |
| thesis lifecycle | 3 筆 | `python -c "import json;print(len(json.load(open('thesis/lifecycle.json',encoding='utf-8'))))"` |
| Event Watch | 95 筆；語意條件 0 筆 | `python -m engine_b.cli counts`（或讀 `library/leads/event_watches.json`） |
| 圖上帶反證的 claim；有消費者的 | 411；0 | 決定紀錄 §1.5 |
| pq2 未結案；其中 decision_review | 19；17 | `python -m engine_b.todo list` |
| APP state kinds | 9（ranking／beta／coverage／watches／positions／basket／structure_readings／account_scorecard／multi_year） | `python -m webapp status` |
| 個股頁 | 73 份；有賭注 3 檔 | 同上 |

**一句話：圖是公司中心的、反證沒有人盯、注意力被財務層吃掉。** Phase 0 先拆，Phase 1 先接反證，Phase 2 才把讀圖變中心。

## 消費層對照表（2026-09-22 使用者定案）

### 頁面

| 頁 | 現在 | 之後 | Phase |
|---|---|---|---|
| 籃子 | 排序順序 × 賭注 × payoff>0 × 催化劑 → 首選 | **候選狀態板**：有敘事的公司按五狀態分組（可開／缺 X／等回落／不要／已持有），組內不排名；每列印讀圖判讀、三題三盞、在等的 watch | 0 停、3 建 |
| 要幾倍 | 多年反向橋算「要 2 倍營收得成長幾 %」 | **頁面退役**；「要翻倍需要什麼為真」變成敘事裡的一段文字 | 0 |
| 瓶頸排序 | 可行動 37 條，餵籃子與 pq1 | **降級為結構表**：逐邊稽核（sub 填了沒、自報還是外部印證、走不走得到錨），拿掉排名框架與 top-N，不餵任何佇列；anchor_gaps 與未填格併進走圖 | 0 降、2 併 |
| coverage | 真缺口／建模待補／重複節點候選 | **走圖頁**：加新問句型別；這頁就是研究佇列 | 2 |
| watches | 在等／停滯 | 留，擴充：語意條件、今日醒／到期／標旗、反證在盯／未盯、未檢 N | 1 |
| structure_readings | 只有 API | **給它一頁**：每層與每插槽一份判讀、staleness、逐字 | 2 |
| positions | 逐檔／真實成交 | 留，加「已持有」連回候選板 | 3 |
| beta | sleeve 六格 | 凍結不動 | — |
| account_scorecard | 帳號計分表 | 留，Phase 5 加主題籃子基準 | 5 |

### 個股頁（三層骨架與「句不是格」不動）

| 層 | 留 | 拿掉 | 加 |
|---|---|---|---|
| 首屏 | 短評七格（`our_bet` 文字）、歸零旗標那顆燈 | 那把尺（現價／沒賭對／賭對／判斷錯了）、「要翻倍需要什麼為真」計算框 | 末行候選狀態；三題三個字 |
| 論證 | argument（「為什麼這樣想：鏈、數字、市場、賭注、風險、時間表」，73 檔都有內容）、research、downside | `why`（「怎麼算到這裡：假設、敏感度、算式、證據」——只吃估值鏈三個輸入，問的問題已被 G3 退役；2026-09-23 執行者實測後由使用者定案退役）、`bet` 的四個價格、`entry`（73 檔全 missing） | `bet` 改純文字（型別、騎層或插槽、什麼必須為真）；downside 每條反證連到 watch；讀圖判讀一段 |
| 稽核區 | fundamental 原始數字、limits、absence 分型 | q4 隱含報酬、q7 payoff | 三題各三行數字與資料源；讀圖逐字 |

Readiness 規則同步換：核心面板改為 headline、短評、argument、research、讀圖、歸零旗標；`why` 退役、fundamental 降為選配。
⚠ argument 的「數字」「賭注」段今天也讀估值鏈，刪除後要確認沒有任何一檔的 argument 變空（否則升核心後又 blocked）。

---

## Phase 表

> 標記：▶ 進行中｜○ 未開工｜✅ 完成。研究項（pq2）不占本表。
> **推進規則：** Verdict 為 `GO` 且沒有待使用者決定的問題時直接接續，Step 與 Phase 邊界一視同仁；六條停止條件住 `AGENTS.md`「協作與邊界」。
> **執行者是便宜模型時 Z1 以上預設 R1**（development-flow）。

| Phase | 做什麼 | 為什麼 | 驗收（數的是哪一層的東西） | 前置 |
|---|---|---|---|---|
| **0 拆** ✅（2026-09-23 結案；closeout `docs/reports/2026-09-23-phase0-closeout.md`） | **0a 停跑**：排程與 APP 不再呼叫估值、反向橋、賭注四價、decision_lab 鑄號與 reassess；排序不再餵籃子與 pq1；multi_year kind 退役；heartbeat 段 2 不印目標價；三個研究 skill 的首選／籃子／payoff 句同 commit 改；sandbox 規則的兩條退役入口移除。**0b 刪除**：依下方退役清單刪模組、測試、config、文件段；decision_lab 舊店凍結唯讀、研究側刪（見下表）；5% 單筆與 ETF 槓桿 cap 的硬擋搬進 `scripts/record_trade.py`，寫 Sheet 前查、超過 fail closed、override 須附理由；`sheet_only_holding` kind 退役（Sheet 有、敘事沒有的持股改列候選板「已持有、缺敘事」）；OPERATIONS 的 decision_lab 命令段、ARCHITECTURE §8.2、CONCEPTS 同 commit 更新。**0c 池子**：17 筆未結案 decision_review 一次批次 `drop`，理由「機制退役」，receipt 註明語境；`standing_authorization.json` 移除 `decision_review` 類別 | 立刻減少注意力噪音，並移除 Goodhart 誘因；停跑而不刪會讓 blocker 與 missing 繼續長回來 | ①**殭屍 grep 差集歸零**：退役清單的八組 regex 在 code／skills／tests／config／static 的命中，**扣掉腳本 keep-list（逐（檔，組）附理由，理由限五類：留下的檔、legacy key、廢止註記、禁止句、守門斷言）之後為 0**，且 keep-list 沒有「已列但不再命中」的腐壞條目；②新鑄 pq2 中 `source=decision_lab` 為 0（查 `todo_pool.json` 的 `added_at` 在 Phase 0 結案日之後）；③`python -m webapp status` 沒有 `multi_year`、`basket` kind；④心跳五段照印且段 2 印「候選狀態板未落地（not_yet_recorded）」；⑤Decision Store 檔案 sha256 前後相同、`live_choices` 仍為 1；⑥`record_trade.py` dry-run 對超過 5% 的成交 fail closed（新增測試） | 無 |
| **1 等待與心跳** ✅（2026-09-25 結案；closeout `docs/reports/2026-09-25-phase1-closeout.md`；R2 GO；②③④ 的回查改用心跳常駐計數器——使用者 2026-09-25 定案，plan 偏差 #29）（plan [`2026-09-24-001`](plans/2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md)；2026-09-24 使用者定案 amendment A1–A6，含 P0 review 後的 C1–C7，五欄見 plan §0.4） | **排程（A1）**：一個 Windows daily（**心跳不靠 LLM；其他步驟可以用 LLM，但 LLM 只產出提議，由程式驗證後寫入**（C4）；封閉步驟清單：抓資料、ETL、FX、triage、watch 比對與到期處置、sync、materialize、健康審查、invariants、本機備份、心跳、每天唯一一則 Discord），取代 Heartbeat／FxSync 兩個工作，是**唯一的排程**；時間只住 `config/daily_routine.json`，註冊命令由它導出、每次執行自我比對；LLM 只做 triage 與語意預篩，**且是 daily 裡的步驟**（Claude CLI `claude -p` 零工具、規則與資料由程式塞進 prompt、只回 JSON、每次執行檢查 init 能力欄位，由程式驗證後寫入；Codex 不在任何無人值守步驟裡；C1、C4、C6）；長版 Daily Brief 退出無人值守；weekly 退役（題材掃描改互動 skill，Discord 與 session 開頭常駐「距上次掃題材 N 天」）。**等待**：Event Watch 加 `semantic_condition` kind（條件原文、實體、層或插槽、來源指標、核查頻率、48 小時動作、到期）；讀圖（contract v2 `disproof[]`）與 thesis（envelope 結構化反證）寫反證時自動登記，敘事的登記移到 Phase 3（A2）；thesis 與讀圖自己的反證——既有 16 條 thesis 反證與 2 份現行讀圖的反證——由強模型補登記（圖上 411 條 claim 反證本 Phase 不登記；thesis 引用的那些列進結案待決）；語意 watch 只比對 **feed 宣告的**一手文件（排除持股申報）、不看 triage，醒來＝待檢，判定在互動 session；AI 預篩預設開（daily 以程式抓醒來那份文件的全文、Claude CLI 零工具只回標旗、程式驗證引文逐字後寫入，只標旗不改狀態；A4、C2、C7）；判定「觸及」後由該 thesis 的 `thesis_lifecycle` 項目接住、讀圖來源標該重讀（A5、C3）；`entity_filing_signal` 加 wake target `wake_reading`（客戶節點出新文件 → 該層讀圖標 stale）；到期（A3、A7）：thesis 來源的反證到期併進那份 thesis 的複查項目（go／drop 後續盯到下一個核查點）、讀圖來源的列進節點重讀理由；沒有自己複查週期的（假設型等）才鑄 pq2 新 kind `watch_decision`（go＝研究結論已發生、不含任何 authority；續等＝watch 以新到期日回 active、等待只住 registry；`drop`＝放棄），pq2 型翻回「球在你」，追源型 lead 轉終局並計數。**心跳**：較昨 diff（昨天快照落地）＋ watch 今日醒／到期／標旗／未檢 N ＋ 反證在盯／觸及待處置／未盯／叫不醒 ＋ pq2 逐筆（go 授權／不含）＋ harvest 沒跑必亮 ＋ 分類層本輪結果 ＋ 備份、健康審查、NAV、計分表每天 | 出場只認反證，反證沒人盯之前其他都是空的；registry 已存在且沒漏，缺的只是語意條件（決定紀錄 §1.5）；2026-09-24 實測 Codex 暫停讓抓資料與喚醒全停、心跳卻照印「未 triage 0」——「LLM 失敗心跳照發」必須在結構上成立 | ①watch 中 `semantic_condition` 筆數 0 → ≥ 16（3 份 thesis 的反證條目）＋ 2 份現行讀圖的反證條數（A2；Step 1.6 逐字列出後定數），並寫出其中可被動喚醒 N、叫不醒 M；②心跳出現第一次真實的「今日醒 ≥1」；③心跳印「未檢 N」且 N>0（預篩只標旗、不減少未檢；預篩關閉或失敗時照印；A6）；④到期的 watch 不消失：thesis／讀圖來源的出現在 thesis 複查項目／節點重讀理由，假設型出現在 pq2 為 `watch_decision`（`user_decision`）（A7）；②③④ 結案時若尚未自然發生：測試證明機制、照實寫「已交付、未生效」並登記回查 date watch（④ 讀圖來源最早 2026-11-18、假設型最早 2027-01-01，A3、A7）；⑤一個 Windows daily、每天一則 Discord、排程時間與 config 一致、triage 是其中一步（機制存在與否，A1／C1） | 0a |
| **2 讀圖兩種單位 ＋ 走圖** ▶（plan [`2026-09-25-001`](plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md)；2026-09-25 使用者定案 amendment A1–A6，五欄見 plan §0.4；原文「`READING_KINDS` 加 `socket`」「五型問句」「優先序＝lead 時間＋使用者點名」由 A1／A5／A4 取代） | **單位（A1）**：讀圖紀錄 v3 加 `unit`（`layer` 層／`socket` 插槽），判讀結論字彙 `READING_KINDS` 不動、v1／v2 算層；選取與 staleness 以（節點, 單位）各自算。**逐字（A2，L18）**：護城河／量必須引用需求側與供給側各至少一段圖上原文、寫入時由程式核對，插槽的護城河另需一段不是供應商自己的來源（L8）；反證每條加出處。**反向路徑（A3）**：只收 `competes_with`，`schema/vocab.json` 的 `counter_path_relation` 是唯一來源。**插槽視角**：`query.structure --unit socket`（還有誰供與各自 `qualification_status`、客戶端原文、上游、反向路徑、需求錨；分不出製造者還是零件供應商時明示；附加段不進 digest；插槽的供貨邊證據變動算高等級）。**走圖（A5）**：零 LLM、不打分的問句產生器，九型封閉字彙（硬需求下的薄層沒人讀、只一家且自報、供給側 sub 全未填、讀圖過期、lead 點名但不在圖、往下供貨的公司走不到錨、沒人供應、建模待補、重複節點候選），輸出研究佇列段 `graph_holes`（吸收 coverage 缺口／重複節點候選／讀圖過期三段），型別固定順序、型別內按 id；coverage 頁改走圖頁（kind `graph_walk`）；structure_readings 給一頁；個股頁加讀圖選配面板（由圖推、印狀態）。**pq1（A4）**：拿掉「坐在難替代邊上」一軸、`decision_impact` 的「排序」類換成「結構或讀圖會變」、同級按 lead 時間。**Graph MCP 退役（A6）**：旁支列排入 Step 2.1 | 讀圖是新中心；粒度題靠兩種讀圖解，不靠選唯一正確的層（G5）；研究方向由圖報洞與 lead 驅動，不由分數（G2） | ①ledger 出現第一份 `unit=socket` 讀圖（研究並行寫；plan Step 2.5 強模型）；②`graph_holes` 每型每日印命中／母體，且結案時母體 ≥10 的型別觸發率 <50%（不恆亮，L14-4）；③走圖頁與讀圖頁在 `webapp status` 列得出 kind（`graph_walk`、`structure_readings`）；④現行 v3 讀圖中護城河／量的兩半引用都核對得到（讀圖）；⑤反向路徑非空的節點 26 → 19（圖；2026-09-25 基準） | 0a |
| **3 候選狀態 ＋ 三題** ○ | narrative ledger 加 `candidate_state`（五值封閉字彙）；敘事寫反證時自動登記 `semantic_condition` watch（2026-09-24 amendment A2 由 Phase 1 移入：與 `candidate_state` 同一次改 ledger）；缺 X／等回落必帶 `watch_id`，不要必帶 reason；三題各接資料源與「無法量」出口：會死嗎＝歸零旗標補稀釋與 going concern 兩盞；已定價嗎＝自家 EV/S（虧損期 P/S）三年百分位、主題籃子中位數、30／90 天相對漲幅三行只印不判；出現在數字裡了嗎＝分部營收或月營收的結構變化；APP 稽核區印三題三行、首屏印候選狀態與三個字；籃子頁改候選狀態板；positions 連「已持有」；heartbeat 印各狀態檔數與最老滯留天數；readiness 核心面板換；`record_trade.py --receipt`：成交事件內嵌敘事 digest、讀圖 digest、候選狀態、三題答案、在盯的 watch id、使用者一句理由，缺收據 fail closed | 沒有排序後的對稱風險是永遠不收斂（G6）；財務只回答三題（G3） | ①有敘事的檔 100% 有候選狀態；②「缺 X」100% 指向活的 watch；③三題每題對每檔有值或有 `absence_kind`；④歸零旗標四盞有值的檔數（今天稀釋與 GC 是 0/73）；⑤新成交事件 100% 帶收據 | 1、2 |
| **4 層中心來源** ○ | 抽取入口的選源規則：層文件優先（客戶 filing 供應商名單、產業報告、規格書、teardown）；onboarding packet 必含「這份文件列舉了哪一層的供應商集合」；走圖的「單供應商但繞不過」問句餵 lead-intake 當研究題；`substitutability` 的 `auto` 投影補可稽核性（逐字必含可替代性語言，否則標 `unsupported`） | 圖是公司中心（65% 單供應商）；65% 量到的是我們讀了誰的文件（G4） | ①單供應商節點比例 65% → 下降（Cypher 同決定紀錄 §1.1）；②供應商集合 ≥3 家且逐字撐住的層數 10 → 上升；③`auto` 投影的 sub 中逐字不含可替代性語言的比例（2026-09-21 量 103/136）→ 下降 | 2 |
| **5 量測** ○ | 量測層從 trade_log 加收據重建（舊 Decision Store 的 outcome 只當歷史）；主題等權籃子定義（append-only、附理由與日期）；追蹤表加籃子基準與三個 power-law 統計量；圖預測對錯表（讀圖斷言 vs 後續證據）；帳號計分表接籃子超額 | 報酬是慢迴路，圖的預測是快迴路（G9） | ①追蹤表印籃子超額；②圖預測表有第一筆對／錯；③計分表印量測起始日與樣本數 | 3 |

**每個 Phase 開工前要有 plan；沒有就停。** Phase 與 plan 檔的對照、以及「開 plan session」要貼的指令住 [`plans/README.md`](plans/README.md)。

### 研究並行（不是 Phase，但 Phase 3 的驗收靠它）

便宜模型蓋 Phase 1 到 3 期間，**互動 session 用強模型寫讀圖與敘事**：從既有 8 份讀圖與 3 份 thesis 的公司開始（InP 層、CW DFB 層、Sivers 的 Ayar 插槽），每份敘事末行寫候選狀態。研究走 pq1／pq2，不占本表。

### 旁支開發項（不是 Phase；不插進執行中的 Phase，排在 Phase 之間或使用者點名時做）

| 項目 | 做什麼 | 為什麼 | 驗收（機制存在與否） | 前置 |
|---|---|---|---|---|
| **Graph MCP 退役** ▶（2026-09-24 使用者決定；plan 2026-09-24-001 §0.1 C5；**2026-09-25 排入 Phase 2 plan Step 2.1**，AGENTS「Local-first」那句的改寫使用者同日核准，逐字見 plan 2026-09-25-001 §0.4 A6） | **要拔乾淨，`.md` 也算（使用者 2026-09-24 明確要求）。** 開工第一步先跑盤點，逐檔分三類處置，清單寫進 STEP_RESULT：`git grep -n -i -E -e mcp_server -e graph_mcp -e "\bMCP\b" -e stockbotv2-graph -e "mcp\.minatoyukina" -e record_lead_decision -e apply_research_action -e load_extraction`（每個 pattern 一個 `-e`，命令裡不放豎線：表格裡的豎線若寫成跳脫形式，照原始 markdown 複製時會變成字面字元、grep 恆 0 命中）（2026-09-24 盤點：md 約 40 檔、py／測試約 19 檔）。①**刪**：`mcp_server/`（`graph_mcp.py`、`leads_tools.py`、`engine_c_tools.py`）與只守它的測試（`test_graph_mcp_manual`、`test_leads_mcp`、`test_engine_c_mcp` 等，逐檔列守什麼）。②**改寫（活文件與活程式）**：`AGENTS.md`（「cloud＋MCP 是備援」一句——判準句，另給五欄 amendment 請使用者核准）、`CONCEPTS.md`、`docs/OPERATIONS.md`「MCP server」節、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md`（含硬約束 12「Core 不得 import `mcp_server`」）、`docs/plans/README.md`、`prompts/intake_protocol.md`、`skills/*/SKILL.md`（daily-brief 等的「cloud session＋MCP 是備援」「雲端用 MCP `record_lead_decision`」）並跑 `sync_agent_skills.py` 讓 `.agents/`、`.claude/skills` 副本跟上、`deploy/cloudflare/`（README 與 `config.yml.example` 拿掉 `mcp.`／`neo4j.`）、`tests/test_layer_separation.py` 的 `KNOWN_MCP_CONSUMERS`、以及 `alpha/__init__.py`、`intake/`、`engine_b/todo.py`、`query/`、`webapp/api.py` 裡提到 MCP 的註解與分支（`intake/` 的 domain 本身留下，本機路徑仍在用）。③**封存進 `docs/archive/`**：`docs/remote-access-architecture.md`、`docs/solutions/architecture-patterns/mcp-connector-route-past-cloud-sandbox-egress.md`（原處留一行指向封存檔）。④**歷史留著不動**（keep-list，理由只准「歷史紀錄」）：`docs/archive/`、`docs/reports/`、`docs/brainstorms/`、`docs/refactor/`、`docs/lessons-incidents.md`、已 completed 的 dated plans。另清本機的 `.claude/settings.local.json` 裡 MCP 工具的權限條目。`scripts/retired_mechanism_grep.py` 加一組 MCP regex，**掃描範圍要涵蓋所有 tracked 的 `.md`**（現行 AREAS 沒有 `AGENTS.md`、`prompts/`、`deploy/`、`.claude/skills`，要補） | 手機改用 Claude Code Remote Control 操作本機 session——本機工具直接讀寫圖、所有人工 gate 照舊——不再需要 MCP；它是一個對外的寫入入口（`record_lead_decision`、`apply_research_action`、`load_extraction`），不用就不該開著。已先停（2026-09-24）：process 停、開機 vbs 移除、tunnel 的 `mcp.`、`neo4j.` hostname 移除（外部實測回 404）、claude.ai connector 由使用者斷開；claude.ai 上沒有任何雲端排程（RemoteTrigger list 為空） | ①`mcp_server/` 不存在；②MCP regex 的殭屍 grep 在**所有 tracked 檔（含每一個 `.md`）**扣 keep-list 為 0，keep-list 每條理由都是「歷史紀錄」類、且沒有「已列但不再命中」的腐壞條目；③`pytest` 綠、`python -m audit invariants` 綠；④`~/.cloudflared/config.yml` 沒有 `mcp.`、`neo4j.`（查證：`grep hostname ~/.cloudflared/config.yml`；2026-09-24 已完成）；⑤AGENTS 那一句的改寫有使用者核准紀錄 | Phase 1 結案（避免同時兩個 writer 改同一批檔） |

---

## Phase 0 退役清單（grep 盤點，2026-09-22；驗收＝殭屍 grep 歸零）

> 數字是**檔案數**（同一檔可能命中多組）。盤點腳本的八組 regex 就是驗收用的殭屍 grep；
> 範圍：`alpha briefing webapp engine_b engine_c decision_lab thesis query crons scripts mcp_server shared portfolio risk loader identity audit skills tests config .codex webapp/static`，
> 排除 `docs/archive`、`docs/lessons-incidents.md`、`library/`。**不做成常駐 linter**（L16-4）；Phase 0 結案時跑一次，之後每季跑一次。
> **驗收是差集不是絕對零**（2026-09-23 執行者實測後定案）：合法的提及有五類——留下的檔名（如 `decision_lab/store.py`）、讀歷史用的 legacy key（如 `decision_review`）、
> 廢止註記、禁止句、守門斷言——逐（檔，組）列進腳本的 keep-list 並附一句理由；驗收數字是「命中但不在 keep-list 的（檔，組）數」。
> 它抓的是「沒有殭屍機制」，字串只是 proxy；keep-list 讓 proxy 的誤報變成可被質疑的一行字，而不是縮窄 regex（那會變第二份要維護的退役清單）。

| 組 | regex | 程式 | 畫面 | skill | 測試 | config | 處置 |
|---|---|---|---|---|---|---|---|
| A 排序當驅動／首選 | `rank_bottlenecks\|top_pick\|首選\|可行動排序\|actionable_rows\|structural_rows` | 28（`query/bottleneck.py`、`webapp/basket.py`、`alpha/ranking.py`、`briefing/alpha_view/builder.py`…） | `app.js` | 4（alpha-status、daily-brief、system-decompose、blind-spot-audit） | 14 | `alpha_screen.json`、`lead_classification.json` | `query/bottleneck.py` 留但改名結構表、拿掉排名與 top-N、不再被佇列 import；`alpha/ranking.py`、`alpha/backtest.py` 刪；skill 句改；測試跟機制走 |
| B 籃子 filter | `basket\|籃子\|FILTER_REASONS\|payoff_not_positive\|market_cap_above_max\|analyst_count_above_max` | 15（`webapp/basket.py`、`crons/heartbeat.py`、`scripts/outcome_if_settled_today.py`、`scripts/alpha_screen_check.py`…） | `app.js`、`index.html` | 1 | 14 | `alpha_screen.json` | `basket.py` 整個換成候選狀態板（Phase 3 建之前 kind 退役）；覆蓋厚薄門檻（`alpha_screen.json`）**留**，Phase 3 當「邊緣」定義用；兩個 scripts 刪 |
| C 估值／隱含報酬／尺 | `implied_return\|future_target\|sell_side_target\|target_reached\|q4_implied_return\|q7_payoff\|隱含報酬\|market_implied_eps\|required_eps\|目標倍數\|calibrat` | 51（`briefing/alpha_view/builder.py` 166 處、`alpha/valuation/`、`alpha/implied_return/`、`alpha/cli.py`…） | `app.js` | 2 | 37 | `engine_c_observation_fields.json` | `alpha/valuation`、`alpha/implied_return` 刪；`builder.py` 與 `analyst_view/compose.py` 拿掉尺、q4、q7、future_target、sell_side_target、target_reached；Engine C 的 `consensus_estimates` 資料**留**（三題「已定價」要用） |
| D 多年反向橋／要幾倍 | `alpha\.reverse\|build_reverse_bridge\|multi_year\|multiple_horizon\|要幾倍\|倍率射程\|要翻倍需要什麼為真\|RETURN_MULTIPLE_LADDER` | 18（`briefing/multi_year.py`、`alpha/reverse/`、`webapp/materialize.py`、`alpha/models/session_assessor.py`…） | `app.js`、`index.html` nav | 0 | 10 | — | `alpha/reverse`、`briefing/multi_year.py`、`scripts/multi_year_check.py`、`materialize_multi_year`、`/api/v1/multi-year`、nav 刪；判斷檔的 `multiple_horizon` 欄位資料留（ledger append-only）但不再消費 |
| E 賭注四價／variant overlay | `variant\.overlay\|variant_overlay\|payoff\b\|沒賭對\|賭對了值\|判斷錯了值\|bet_state` | 26（`webapp/basket.py`、`briefing/alpha_view/builder.py`、`alpha/narrative/argument.py`…） | `app.js` 29 處 | 1 | 24 | `decision_blockers.json`、`engine_c_observation_fields.json` | payoff 計算刪；`bet/variant.overlay` ledger **資料留**（append-only），`bet` 面板改純文字讀 `our_bet`；`sizing.py`／`test_probe_sizing.py` 刪（資本表達層 08-28 已移除，殘留） |
| F entry criterion | `EntryCriterion\|entry_criterion\|alpha\.entry` | 17（`alpha/entry/`、`alpha/providers/entry_criteria.py`、`alpha/cli.py`…） | — | 1 | 3 | — | 整個刪（73 檔全 missing，從未用過） |
| G decision_lab 鑄號／reassess | `decision_lab\|decision_review\|reassess\|DecisionContext\|assessment_gap` | 67（`engine_b/todo.py` 150 處、`decision_lab/cli.py`、`brief.py`、`workflow.py`、`engine_b/queue_segments.py`、`crons/daily_brief_prompt.md`…） | — | 5 | 63 | `decision_blockers.json`、`authority_tokens.json`、`standing_authorization.json` | **凍結**：見下表。`engine_b/todo.py` 的 decision_lab collector 刪；`queue_segments` 的 reassess 段刪；`.codex/rules` 的 `decision_lab today` 與 reassess-stale 兩條 fixed entry 移除（sandbox impact review 五步）；MCP `get_decision_brief` 工具退役（查證：`mcp_server/` 內 grep） |
| H 估值模型 | `alpha\.valuation\|alpha\.fundamental\|FundamentalsSnapshot\|ValuationMethod\|pe_forward` | 27（`engine_c/estimates.py`、`alpha/providers/fundamentals.py`、`scripts/alpha_expectation_gap.py`…） | — | 0 | 29 | — | `alpha/fundamental`（FY+1 因果橋）刪；`alpha/providers/fundamentals.py` **留**改為只供三題與稽核區原始數字；`engine_c/estimates.py` 留（資料層）；`scripts/alpha_expectation_gap.py` 刪 |

### decision_lab 凍結（G12；A5 append-only，Git 救不回；動之前必讀 historical-failure-matrix）

**為什麼是凍結不是切一半：** live 收據掛在 `live_choices.decision_id → system_decisions → context_bundles ＋ coverage_assessments`，也就是退役中的 cohort→context→coverage 鏈；研究側刪掉後舊店沒有寫入入口。實際在用的 `scripts/record_trade.py` 寫 Sheet 與 trade_log，**不查 5% 上限、不寫收據**，歷來 `live_choices` 只有 1 筆。所以煞車與收據搬到成交路徑，舊店凍結成歷史檔案館。

| 留（唯讀歷史） | 刪 | 搬 |
|---|---|---|
| `store.py`（只保留查詢；寫入方法無呼叫端，docstring 標 frozen 2026-09-22）、`schema.sql`、`models.py`、`bootstrap.py`（備份還原測試要用）、`adapters/`（portfolio／risk 讀 Sheet 持股）、`cli.py` 的唯讀 history／status 子命令 | `execution.py`、`outcomes.py`、`sizing.py`、`context.py`、`coverage.py`、`coverage_queries.py`、`intake.py`、`workflow.py`、`workflow_ports.py`、`brief.py`、`action_card.py`、`references.py`、`cli.py` 的 `today`／`reassess`／`card` | `_assert_user_sized_within_capital_caps` → `risk/`，由 `record_trade.py` 在 `--apply` 前呼叫（NAV 讀 Sheet） |

驗收（A5 不受傷）：Decision Store 檔案 sha256 前後相同；`select count(*) from live_choices` 仍為 1；`python -m audit invariants` 全綠；`tests/test_private_backup_restore.py` 綠；`record_trade.py` dry-run 超 5% fail closed。

### 測試跟機制走（硬約束 9 修訂）

退役機制的測試檔**同一個 commit 退役**，不留殭屍斷言；活的機制的測試不可刪斷言。已知要退的測試檔（依 grep）：
`test_implied_return`、`test_valuation_model`、`test_reverse_bridge*`、`test_multi_year_*`、`test_entry_logic`、`test_probe_sizing`、`test_webapp_basket`、
`test_basket_screen_thresholds`、`test_bet_endgame`、`test_variant_scenario`、`test_decision_lab_e2e`、`test_action_card`、`test_alpha_expectation_gap`、
`test_full_chain_acceptance`（重寫為新管線的 full chain）。**每刪一個測試檔，STEP_RESULT 列出它守的是哪個退役機制。**

---

## 硬約束（沿用 2026-09-16，2026-09-22 修訂三條）

1. **不重建 Neo4j。** 資產是 EdgeAssertion 的 provenance。
2. **舊 Decision Store 凍結唯讀：schema 不動、資料不刪、不再寫入**（L10）。新收據住 `library/trades/trade_log.jsonl` 的成交事件內；硬擋住 `record_trade.py`（G12）。
3. **四個人工 gate 不放寬；L8 不放寬。**
4. ~~`rank_bottlenecks()` 仍是唯一排序權威~~ → **排序不再是任何佇列或頁面的輸入**；結構表只做稽核（G1）。
5. **系統不給 alpha 部位尺寸、不下單、不連 broker。**
6. **beta 訊號不得復刻；beta 開發凍結。**
7. ~~不因籃子空就放寬篩選條件~~ → **候選狀態「可開」為零就零，不得放寬**；讓它非空的路是研究。
8. **last30days 不串進無人值守管線。**
9. ~~既有測試檔全部保留~~ → **測試跟機制走**：退役機制的測試同 commit 退役；活的機制不可刪斷言。
10. **改任何 `python -m <module>` 命令字串前先走 sandbox impact review 五步。**
11. **六條 hard invariant 全程適用。**
12. **Local-first；Core 不得 import `mcp_server`。**
13. **Sheet 是部位真相**；alpha 不用貸款資金是使用者紀律，系統不建 gate。
14. **`AGENTS.md` 只寫目標與邊界**；lesson 判準句不刪，事發住 `docs/lessons-incidents.md`。

## 研究主題範圍

- **現行題材（2026-09）：AI capex。** 需求錨 SSOT 是 `config/sector_anchors.json`；**本檔與 AGENTS 都不綁題材**。
- 新題材由使用者選；機制是 `system-decompose`，提案自動鑄 pq2（manual 型），同時 open 最多兩個，drop 過的不重生。
- HBM：SK Hynix／Samsung 不主動 onboarding（擁擠度）。humanoid 的可投資機會在零組件供應商不在整機。

## 明確不做（理由已量測，勿重開）

- **不做加權綜合分數、不做全域排序、不做首選**（G1；2026-09-22）。
- **三題不得長回估值模型**：不算目標價、不算 payoff、不對 peer 倍數校準（2026-09-11 量過「需求同源不代表估值可比」）。
- **不做 ROADMAP 驗收 linter**（L16-4：會誤報的防呆本身是過度工程）；驗收層由 development-flow 八欄的人工欄位守。
- 沿用：peer valuation／`peer_groups.json`、等待機制三套併入 Event Watch（G7 是加 kind 不是併）、待辦池 evidence conflict 類型、ETF 完整 look-through、Confidence 五軸重構、技術指標擴充、貸款 glide path、parked lead embedding 召回、`coverage_gaps` 走 `DEPENDS_ON`。理由逐條在 archive「明確不排程」。

## 每個 Phase 的 completion gate

historical-failure-matrix §9 八項（regression suite、invariant audit、無未解釋語意 diff、無新 dual authority、無 silent drop、point-in-time、lifecycle 可達、該 Phase 的 critical failure 有 executable protection）＋ **第九項（2026-09-22）：驗收數字數的是圖／讀圖／敘事／registry／追蹤表**。

## 看起來像缺口但不是（請勿「修正」）

- 人工 runway 觀測寫入後 `financial_runway_manual_required` 仍亮，多半是 100 天鮮度窗，正解是用最新一季財報刷新觀測；`as_of` 填資產負債表日。
- 5 個 cohort 的 `expiry` 仍是 `+72h` 預設值，不要去清：lifecycle 已 `expired`，修它讓 0 筆下游資料變化。

## 本檔自己的 disproof

決定紀錄 §10 的四條照用，外加一條：**Phase 0 的殭屍 grep 在結案六個月後若重新非零，代表退役沒拿乾淨或有人把它加回來**——那時該做的是查是誰、為什麼，不是再跑一次刪除。
