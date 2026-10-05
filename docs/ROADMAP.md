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
| **2 讀圖兩種單位 ＋ 走圖** ✅（2026-09-26 結案；closeout [`2026-09-26-phase2-closeout.md`](reports/2026-09-26-phase2-closeout.md)；結案 R2 GO）（plan [`2026-09-25-001`](plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md)；2026-09-25 使用者定案 amendment A1–A6，五欄見 plan §0.4；原文「`READING_KINDS` 加 `socket`」「五型問句」「優先序＝lead 時間＋使用者點名」由 A1／A5／A4 取代） | **單位（A1）**：讀圖紀錄 v3 加 `unit`（`layer` 層／`socket` 插槽），判讀結論字彙 `READING_KINDS` 不動、v1／v2 算層；選取與 staleness 以（節點, 單位）各自算。**逐字（A2，L18）**：護城河／量必須引用需求側與供給側各至少一段圖上原文、寫入時由程式核對，插槽的護城河另需一段不是供應商自己的來源（L8）；反證每條加出處。**反向路徑（A3）**：只收 `competes_with`，`schema/vocab.json` 的 `counter_path_relation` 是唯一來源。**插槽視角**：`query.structure --unit socket`（還有誰供與各自 `qualification_status`、客戶端原文、上游、反向路徑、需求錨；分不出製造者還是零件供應商時明示；附加段不進 digest；插槽的供貨邊證據變動算高等級）。**走圖（A5）**：零 LLM、不打分的問句產生器，九型封閉字彙（硬需求下的薄層沒人讀、只一家且自報、供給側 sub 全未填、讀圖過期、lead 點名但不在圖、往下供貨的公司走不到錨、沒人供應、建模待補、重複節點候選），輸出研究佇列段 `graph_holes`（吸收 coverage 缺口／重複節點候選／讀圖過期三段），型別固定順序、型別內按 id；coverage 頁改走圖頁（kind `graph_walk`）；structure_readings 給一頁；個股頁加讀圖選配面板（由圖推、印狀態）。**pq1（A4）**：拿掉「坐在難替代邊上」一軸、`decision_impact` 的「排序」類換成「結構或讀圖會變」、同級按 lead 時間。**Graph MCP 退役（A6）**：旁支列排入 Step 2.1 | 讀圖是新中心；粒度題靠兩種讀圖解，不靠選唯一正確的層（G5）；研究方向由圖報洞與 lead 驅動，不由分數（G2） | ①ledger 出現第一份 `unit=socket` 讀圖（研究並行寫；plan Step 2.5 強模型）；②`graph_holes` 每型每日印命中／母體，且結案時母體 ≥10 的型別觸發率 <50%（不恆亮，L14-4）；③走圖頁與讀圖頁在 `webapp status` 列得出 kind（`graph_walk`、`structure_readings`）；④現行 v3 讀圖中護城河／量的兩半引用都核對得到（讀圖）；⑤反向路徑非空的節點 26 → 19（圖；2026-09-25 基準） | 0a |
| **3 候選狀態 ＋ 三題** ✅（2026-09-30 結案；closeout [`2026-09-30-phase3-closeout.md`](reports/2026-09-30-phase3-closeout.md)；結案 R2 GO）（plan [`2026-09-26-001`](plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md)；2026-09-26 使用者定案 amendment A1–A6、09-29 P0 review 後追加 A7 並細化 A3／A4，五欄見 plan §0.4：A1 敘事＝短評 v2 七格改題＋`rides[]`／`disproof[]`／`answers`／`candidate_state`；A2 主題等權組定義由 Phase 5 移入、程式與 UI 叫「主題等權組」；A3 三題資料源一次機械回填＋daily 零 LLM 增量、稀釋逐檔單一來源、going concern 結構化欄位；A4 收據只管 alpha、缺敘事另一個旗標附理由放行（不與 5% 硬擋的 override 共用）、賣出輕收據、beta 不要，Step 預先授權；A5 個股頁面板殘留併做；A6 Phase 2 帶過來三個小修（`company_id_for_ticker` 不放寬）；A7 覆蓋厚薄門檻＝候選板「邊緣」定義，非邊緣不能是可開；「做什麼」欄 2026-09-30 結案時照 A1／A2／A4／A5／A7 用語同步——amendment 原要求同 commit 改寫、當時只改了本欄，結案 R2 指出） | **敘事（A1）**：短評 v2（七格改題，`position`／`priced_in`／`what_must_be_true` 換 key）＋`rides[]`／`disproof[]`／`answers`／`candidate_state`（五值封閉字彙）；敘事寫反證時自動登記 `semantic_condition` watch（2026-09-24 amendment A2 由 Phase 1 移入：與 `candidate_state` 同一次改 ledger）；缺 X／等回落必帶 `watch_id`，不要必帶 reason；三題各接資料源與「無法量」出口（A3：一次機械回填＋daily 零 LLM 增量）：會死嗎＝歸零旗標補稀釋與 going concern 兩盞；已定價嗎＝自家 EV/S（虧損期 P/S）三年百分位、主題等權組（A2）中位數、30／90 天相對漲幅三行只印不判；出現在數字裡了嗎＝分部營收或月營收的結構變化；APP 稽核區印三題三行、首屏印候選狀態與三個字；候選狀態板（`candidates` kind，接手 Phase 0 退役的籃子頁位置；非邊緣＝非倍率候選，A7）；positions 連「已持有」；heartbeat 印各狀態檔數與最老滯留天數；readiness 核心面板換（A5：readings 升核心、鏈段需求錨改讀騎的讀圖）；**收據（A4）**：`record_trade.py` 的 alpha 成交事件內嵌 `research_receipt`（`declared`＝敘事 digest、騎的讀圖 digest、候選狀態、三題答案、在盯的 watch id；`derived`＝當天候選列與成交前持有）與使用者一句理由 `--why`，缺現行 v2 敘事的買進 fail closed、`--no-narrative-override` 附理由放行（不與 5% 硬擋的 `--override` 共用），beta 不要 | 沒有排序後的對稱風險是永遠不收斂（G6）；財務只回答三題（G3） | ①有敘事的檔 100% 有候選狀態；②「缺 X」100% 指向活的 watch；③三題每題對每檔有值或有 `absence_kind`；④歸零旗標四盞有值的檔數（2026-09-29 基準稀釋與 GC 是 0/73）；⑤新 alpha 成交事件 100% 帶 `research_receipt`（beta 不要，A4） | 1、2 |
| **4 層中心來源** ✅（2026-10-02 結案；closeout [`2026-10-02-phase4-closeout.md`](reports/2026-10-02-phase4-closeout.md)；結案 R2 兩輪條件修正後 GO；驗收 ①（A1）75→73（plan §11 的 4.4 基準；77→75 是 4.3 分類器變更，不算驗收）、②（A2）5→6 成立，③（A3）未量到——③a 102／113 只印、③b 0／0 沒有母體；「做什麼」欄的 `display_name` 100/100 實為 99/100（`co:nava_thailand` 刻意不補，plan §0.6 #4）；pq2 [666] 被 Neo4j 權限擋下、待使用者決定（closeout §5、plan §14 #26））（plan [`2026-10-01-001`](plans/2026-10-01-001-feat-phase4-layer-centric-sources-plan.md)；2026-10-01 使用者定案 12 題、反方驗證後改 8 處並同日確認，amendment A1–A5 五欄見 plan §0.4；執行者全程強模型） | **選源（A5）**：`source-trace` 加「輸入是層／節點時」專節（客戶 filing 供應商段 → 產業報告 → 規格書／teardown → 供應商自己的文件；claim 路由順序不動）並登記 `config/source_routes.json` 的 `layer_document` route；`company-onboard` 改成先答「坐哪一層」、入圖一律走 `prepare_research_action` → pq2 `ra_admission` → apply 入口（拿掉直接 load 的路）；`source_type` 加 `teardown`、`datasheet`。**packet**：RA request 頂層選填 `layer_enumerations[]`＝`{node, suppliers[], relation, origin_role}`，程式只核對「在本包」（supplier 在本包供貨邊且引文整詞含其名）；packet 印每份文件的 origin／source_type／tier 與「sub 引文不含可替代性語言」警告。**走圖第 2 型**：以現行層讀圖為記憶（有讀圖不再問）、命中旁印 open lead；lead 只在互動研究啟動時鑄（`source=graph_walk:<type>`），以 lead-intake 紀律追到終局（RA 入圖或 park 既有字彙＋watch），**不由 daily 鑄**。**origin 解析**：唯一 owner `resolve_origin`（`classify_evidence` 與讀圖 `verify_citations` 共用）＋`config/publishers.json`（只有自產資料的 kind 算外部印證、媒體永不整類升級）；「客戶高管在供應商新聞稿具名」併進 `self_reported`；名冊 `display_name` 補齊 100/100、加 `name_aliases`／`execution_symbol`，`_TICKER_ENRICHMENT` 退出身分解析。**sub 可稽核**：每筆帶 sub 的 assertion 以 repo 內字表逐字核對、標 `sub_language_in_quote`，住結構表／走圖 artifact 與常駐計數器，**消費端是否忽略留結案決定**。**併入兩個旁支（A4）**：apply 入口、SourceDoc section／title 寫回抽取 JSON。**2026-09-30 定案八項**：稀釋燈改讀 `StockIssuedDuringPeriodValueNewIssues`＋Engine C `METRICS` CHECK 遷移；240 條舊反證退役不印；`ignored` 接 held_index／心跳；百分位印覆蓋率；同敘事重複反證拒收 | 圖是公司中心（65% 單供應商）；65% 量到的是我們讀了誰的文件（G4）；只有一家且只有它自己說的邊，層文件才修得了 | ①（A1）對 Step 4.0 凍結的節點集合，**ns==1 且供貨邊全部自報**的節點數 → 下降（supply_side 口徑＝只算 `supplies_to`；另印 ns=0／1／2／≥3 絕對數，不做比例；§1.1 的 65% 留決定紀錄當歷史）；②（A2）**至少一份非供應商 origin 的來源、引文逐字具名該層 ≥2 家供應商**的層數 → 上升（「≥3 家」母體與「每家逐字撐住」只印）；③（A3）③a 存量：帶 sub（非 null）的 assertion 中引文不含字表語言的筆數只印當歷史（2026-10-01：113 筆為母體）；③b Phase 內新入圖或 supersede 的帶 sub assertion 中引文含字表語言的比例（目標 100%，缺的逐筆列出）；另印：origin 未解析 73 → N、needs_review 113 → N、因分類變更而變的邊逐條與 stale 的讀圖、稀釋燈國內申報人黃 24 → N（AXTI 必黃）、section／title 與抽取 JSON 不一致 10＋21 → 0、本 Phase 鑄的 lead 各到終局 | 2 |
| **5 量測** ✅（2026-10-02 結案；closeout [`2026-10-02-phase5-closeout.md`](reports/2026-10-02-phase5-closeout.md)；結案 R2 CONDITIONAL_GO（B1：驗收②的回查載體要使用者定）後，使用者選心跳常駐計數器（amendment A4）完成；驗收①③成立、②已交付未生效（真實 15 筆：對 0／錯 0／改寫 9／現行 2／非斷言 4，現行最早到期 2026-12-24）；plan [`2026-10-02-001`](plans/2026-10-02-001-feat-phase5-measurement-plan.md)；2026-10-02 使用者定案 8 題、amendment A1–A3 五欄見 plan §0.4；執行者全程 opus 5.5；同日稍早 amendment：不做報酬回測、預測表的「錯」分兩種——五欄見 [Phase 4 closeout §9](reports/2026-10-02-phase4-closeout.md)） | 量測層從 trade_log 加收據重建（舊 Decision Store 的 outcome 只當歷史）：**追蹤表分三條 lane 分印（A1）**——`live`＝trade_log 的 alpha 成交（成交價／日、收據照抄；`record_trade.py` 加 `--backfill-before-receipts` 讓 2026-09-30 前的成交能補登、收據標回填、回填由使用者照 Sheet 下指令）、`paper`＝每檔第一份 v2 敘事寫下日（帶當時候選狀態與首次點名的 lead 來源）、`history`＝舊店 22 筆入圖日錨點凍結只印；三量與籃子超額每 lane 各算、分母分開；**候選狀態每日序列（A2）**供決定紀錄 §10 的 2026-12-22 回查；**Phase 4 尾巴併入（A3）**：#29 ③b 認 supersede、#33 走圖第 2 型降級、#34 `classified_by` 字彙、setup 1b 預熱清單、apply 入口比對 `db.propertyKeys()`；主題等權籃子**沿用 Phase 3 定義的主題等權組**（2026-09-26 amendment A2 移入 Phase 3）；追蹤表加籃子基準與三個 power-law 統計量；圖預測對錯表（讀圖斷言 vs 後續證據；每筆「錯」依反例文件的 `published_at` 對讀圖日期機械分成**當時已有反例**〔讀得不夠〕與**之後才出現**〔判斷錯〕，沒有日期的另列、不壓成任一種）；帳號計分表接籃子超額。**不做報酬回測**：圖裡的公司是 2026 年回頭挑的（入圖前已漲 8／22），回測量到的是選樣；前向追蹤表就是量測本身——日後若有不靠人寫敘事的機械選股規則要被信任，才先量測後放閘（INV-5） | 報酬是慢迴路，圖的預測是快迴路（G9）；「讀得不夠」若記成「判斷錯」，預測表會隨我們多讀文件單調變差，量到的是研究量（L12） | ①追蹤表印籃子超額（paper／live 每列與 lane 聚合有值或有缺席 kind，A1）；②圖預測表有第一筆對／錯，每筆「錯」標明是哪一種（結案時若仍 0：夾具證明機制、closeout 寫「已交付、未生效」，回查由心跳常駐計數器承載——段 4「圖預測」行的「現行最早到期」與 `predictions.*` 快照鍵；2026-10-02 amendment A4 取代原「登記回查 date watch」，五欄見 plan §0.4——plan §11）；③計分表印量測起始日與樣本數；另印：三 lane 列數與量測起始日、候選狀態序列行數、Phase 4 尾巴各機制存在與否 | 3 |
| **6 證據判準** ✅（2026-10-04 結案；closeout [`2026-10-03-phase6-closeout.md`](reports/2026-10-03-phase6-closeout.md)；結案 R2 CONDITIONAL_GO（B1：驗收②等 pq2 [670]）→ 使用者 2026-10-03 對 [670]–[676] go、[677]／[678] drop → C1 五項成立 → 窄範圍覆核 GO；驗收①成立（逐來源違反 0；外部印證 250 → 230，補引文 RA 入圖後 236；降級 22 條逐條有去向）、②成立（2 → 0）、③成立、④副本實測成立（正式 APP 等 2026-10-04 05:30 daily 第一次寫募資文件清單）；plan [`2026-10-02-002`](plans/2026-10-02-002-feat-phase6-evidence-criteria-plan.md)；2026-10-02 使用者定案 15 題（「這些都OK」）、amendment A1 五欄見 plan §0.4；執行者全程 opus 5.5；R2-a（身分合併）、R2-b（稀釋燈）常規 opt-in） | **身分**：OpenLight 兩個代號合併（留 `co:openlight_photonics`）、`co:nava_thailand` 依一手來源定案（Lumentum 自己的廠區就退役、邊改掛 Lumentum；一家代工廠就補名字）；遷移與 RA packet 印入圖副作用（Phase 4 #32）。**來源**：「算不算外部印證」收成一個 owner——印證來源**自己的**引文要逐字具名主詞（主詞是名冊公司時；名冊先補 Apollo／Arista／GF 三個寫法；產品名不算），發布者的引文是轉述句（帶版本的字表）就不升，翻案靠逐份宣告 `origin_linkage=independent`；`classify_evidence`、讀圖 independent 引用核對、插槽視角、L8 稽核、層計數器、RA packet 共用；GSR 改登記 `media`；解析不到的 8 份非聯合稿逐份解析（名冊新公司、publishers、SourceDoc origin 更正走 pq2；那篇 CPO 綜述論文登記 `media`）；聯合公告偵測不改。**下游**：插槽讀圖同級標籤互換算低等級（排在任何改分類之前）；sub 的「引文撐不撐得住」旗標跟著值走到每個消費端（不忽略、不進 digest）。**稀釋燈**：窗內有募資文件（424B、S-1／F-1、8-K 第 3.02 項）才亮黃，只有發行金額沒有募資文件的不上色另列（EDGAR 申報清單、Engine C 新表）。**小修**：結構表逐列需求錨（走不到退回公司層並標明）、APP 偵測自己跑舊程式、追蹤表與計分表排除未收盤 K 棒、預測表改寫規則①收窄成「同 kind 或同日」、本機權限對 `record_trade.py`／`apply_ra_admission.py` 加 ask、4 則 lead 的 `classified_by` 更正（pq2）。**研究**（強模型）：降級邊從原文補具名引文（RA，pq2）、重讀被標籤變更弄 stale 的讀圖、四檔 v2 敘事換版或寫明不換。開工先收 [666] | 2026-10-02 模擬草案規則：244 條外部印證有 25 條撐不住（身分 4、逐來源不具名 12、轉述 2、GSR 7），有敘事的四檔（AXTI、COHR、LITE、Sivers）全中——Sivers 的 CW DFB「外部印證」是華星光年報撐的、那段引文沒提 Sivers；舊計數器只抓到 15 條，因為它認「這條邊任何一段引文具名」、連供應商自己的也算；OpenLight 兩個代號讓 OpenLight 自己的新聞稿被算成另一個代號的外部印證。這些標籤餵走圖第 2 型、層計數器 ①、個股頁「有客戶或第三方印證」與讀圖 staleness——先寫更多讀圖與敘事等於之後全部重讀（L18：標籤要指得回原始證據） | ①（A1）每條外部印證至少有一個印證來源的引文逐字具名供應商、且發布者的不是轉述——結案時逐來源違反 0；本 Phase 降級的每一條在研究收據有去向（補引文 RA／名冊寫法／身分修正／維持降級附理由）（圖）；另印外部印證 244 → N 逐條、①「獨家且全自報」73 → N（預期回升，是誠實的回升）、走圖第 2 型命中 0 → N；②同一家兩個代號、不是公司的公司節點 2 → 0（圖＋名冊；nava 查不到一手來源就照實寫未定案）；③被本 Phase 標籤變更弄 stale 的讀圖各有新一筆或明確延後且有到期（讀圖）；四檔 v2 敘事中引用到變更標籤的各有新版或不換版理由（敘事）；④稀釋燈亮黃的每一檔指得出窗內一份募資文件、11 檔逐檔前後對照（稽核區）；另印：解析不到的 SourceDoc 16 → N、sub 旗標出現在消費端的處數、本 Phase 鑄的 pq2 各到終局 | 5；[666] 收尾（Step 6.0） |
| **7 研究使用與量測（持續型）** ▶（2026-10-04 開；第一期到 2026-12-22 檢查點，之後每季一個檢查點，Phase 本身不「結案」；plan [`2026-10-04-001`](plans/2026-10-04-001-research-phase7-research-edge-plan.md)；使用者 2026-10-04 定案 Q1–Q8、A1–A4，amendment A1（本列）／A2（AGENTS 一句）五欄見 plan §0.4；能力盤點與設計 [`brainstorms/2026-10-04-phase7-research-edge-proposal.md`](brainstorms/2026-10-04-phase7-research-edge-proposal.md)） | **研究約 75%、量測約 15%、開發 ≤10%。** **7.0 開場**：預先登記（十個 edge 假說與殺死條件、14 個 case 與類型、裁決規則、failure log、開發 gate、漏網稽核母體）＋T0 凍結（手動 manifest）；開發 gate 落地＋兩個當下修（巢狀 writer lock、thesis 逾期提醒量錯）；敘事範本「要翻倍需要什麼」（營業數字，不寫目標價）＋市值與近四季營收兩個 placeholder＋「已定價」白話＋重押讀圖換格層引用；敘事「加碼條件」`confirm[]`（寫下即登記 watch、觸及只提醒、不是買進訊號）；個股頁首屏照五題排列＋候選板與個股頁標「和持股共用需求錨」；**外部雷達**：daily 加一步只開 WebSearch 的 `claude -p`，網址必須出自同一次搜尋結果、每日約 5 則、寫成 tier-4 secondary lead、不喚醒語意 watch、不另發通知（它不是 last30days：有 provenance 契約），**八週試驗：上線 56 天後「triaged_go 且追到一手或入圖、而且沒有別的管道更早登記」為 0 就退役**。**7.1／7.4 兩波研究**（光通訊跟 Q3 財報；電力與散熱兩條新鏈、該鏈的主題等權組在第一份敘事前前瞻定義；SNS 40 則 claim 裁決；二階瓶頸三個 case；800VDC 擱置五則回看）；**7.2 回放**（已定價、漏網稽核是機械的；parked 回查、輸家驗屍是研究）；**7.3** Q3 財報季裁決與 2×2；**7.5 檢查點**（決定紀錄 §10＋假說證據帳＋failure log 依重複次數排序＋雷達停止條件＋T1 manifest＋R2） | 機制遠超過使用（讀圖 4、敘事 4、可開每天 0、外部來源 1 個、測試 3,448）；edge 有沒有、從哪裡來，報酬量測要到 2027 才成熟，只能靠預先登記的案例、前瞻凍結與快迴路逐步淘汰假說；AXTI 顯示判斷層可能把我們從贏家身上說服走（n＝1）；LLM 研究者的知識截止（2026-06）讓之前的判讀回放不可信 | ①光通訊以外 ≥2 條鏈各有現行讀圖、每份 ≥1 條登記反證（讀圖、registry）；②新敘事每份有候選狀態、押的讀圖與翻倍條件，持有或可開的另有加碼條件（敘事）；③預先登記的 commit 早於 wave 1 任何新讀圖／敘事，T0 manifest 與當日心跳一致（讀圖、敘事、registry）；④S1 的 40 則 claim 各有裁決或到期（registry）；⑤Q3 財報後四檔敘事各有新版或不換版理由、窗內到期 watch 全部處置（敘事、registry）；⑥每個開了的 case 有產出 id 與裁決，2×2 各列（追蹤表）；⑦雷達上線、第一輪收據、八週停止條件有結論（registry）；⑧檢查點：H1–H10 每個有證據列與 n（追蹤表）；另：開發 Step 各自的測試與變異（機制），進 ROADMAP 的開發項每一項指得出 ≥2 個 case | 6 |

**每個 Phase 開工前要有 plan；沒有就停。** Phase 與 plan 檔的對照、以及「開 plan session」要貼的指令住 [`plans/README.md`](plans/README.md)。

### 研究並行（不是 Phase，但 Phase 3 的驗收靠它）

便宜模型蓋 Phase 1 到 3 期間，**互動 session 用強模型寫讀圖與敘事**：從既有 8 份讀圖與 3 份 thesis 的公司開始（InP 層、CW DFB 層、Sivers 的 Ayar 插槽），每份敘事末行寫候選狀態。研究走 pq1／pq2，不占本表。
**2026-10-04 起研究本身就是 Phase 7**（持續型；預先登記、凍結、檢查點），研究項仍走 pq1／pq2、不占本表。

### 旁支開發項（不是 Phase；不插進執行中的 Phase，排在 Phase 之間或使用者點名時做）

| 項目 | 做什麼 | 為什麼 | 驗收（機制存在與否） | 前置 |
|---|---|---|---|---|
| **Graph MCP 退役** ✅（2026-09-25 Phase 2 Step 2.1 交付；2026-09-24 使用者決定；plan 2026-09-24-001 §0.1 C5；**2026-09-25 排入 Phase 2 plan Step 2.1**，AGENTS「Local-first」那句的改寫使用者同日核准，逐字見 plan 2026-09-25-001 §0.4 A6） | **要拔乾淨，`.md` 也算（使用者 2026-09-24 明確要求）。** 開工第一步先跑盤點，逐檔分三類處置，清單寫進 STEP_RESULT：`git grep -n -i -E -e mcp_server -e graph_mcp -e "\bMCP\b" -e stockbotv2-graph -e "mcp\.minatoyukina" -e record_lead_decision -e apply_research_action -e load_extraction`（每個 pattern 一個 `-e`，命令裡不放豎線：表格裡的豎線若寫成跳脫形式，照原始 markdown 複製時會變成字面字元、grep 恆 0 命中）（2026-09-24 盤點：md 約 40 檔、py／測試約 19 檔）。①**刪**：`mcp_server/`（`graph_mcp.py`、`leads_tools.py`、`engine_c_tools.py`）與只守它的測試（`test_graph_mcp_manual`、`test_leads_mcp`、`test_engine_c_mcp` 等，逐檔列守什麼）。②**改寫（活文件與活程式）**：`AGENTS.md`（「cloud＋MCP 是備援」一句——判準句，另給五欄 amendment 請使用者核准）、`CONCEPTS.md`、`docs/OPERATIONS.md`「MCP server」節、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md`（含硬約束 12「Core 不得 import `mcp_server`」）、`docs/plans/README.md`、`prompts/intake_protocol.md`、`skills/*/SKILL.md`（daily-brief 等的「cloud session＋MCP 是備援」「雲端用 MCP `record_lead_decision`」）並跑 `sync_agent_skills.py` 讓 `.agents/`、`.claude/skills` 副本跟上、`deploy/cloudflare/`（README 與 `config.yml.example` 拿掉 `mcp.`／`neo4j.`）、`tests/test_layer_separation.py` 的 `KNOWN_MCP_CONSUMERS`、以及 `alpha/__init__.py`、`intake/`、`engine_b/todo.py`、`query/`、`webapp/api.py` 裡提到 MCP 的註解與分支（`intake/` 的 domain 本身留下，本機路徑仍在用）。③**封存進 `docs/archive/`**：`docs/remote-access-architecture.md`、`docs/solutions/architecture-patterns/mcp-connector-route-past-cloud-sandbox-egress.md`（原處留一行指向封存檔）。④**歷史留著不動**（keep-list，理由只准「歷史紀錄」）：`docs/archive/`、`docs/reports/`、`docs/brainstorms/`、`docs/refactor/`、`docs/lessons-incidents.md`、已 completed 的 dated plans。另清本機的 `.claude/settings.local.json` 裡 MCP 工具的權限條目。`scripts/retired_mechanism_grep.py` 加一組 MCP regex，**掃描範圍要涵蓋所有 tracked 的 `.md`**（現行 AREAS 沒有 `AGENTS.md`、`prompts/`、`deploy/`、`.claude/skills`，要補） | 手機改用 Claude Code Remote Control 操作本機 session——本機工具直接讀寫圖、所有人工 gate 照舊——不再需要 MCP；它是一個對外的寫入入口（`record_lead_decision`、`apply_research_action`、`load_extraction`），不用就不該開著。已先停（2026-09-24）：process 停、開機 vbs 移除、tunnel 的 `mcp.`、`neo4j.` hostname 移除（外部實測回 404）、claude.ai connector 由使用者斷開；claude.ai 上沒有任何雲端排程（RemoteTrigger list 為空） | ①`mcp_server/` 不存在；②MCP regex 的殭屍 grep 在**所有 tracked 檔（含每一個 `.md`）**扣 keep-list 為 0，keep-list 每條理由都是「歷史紀錄」類、且沒有「已列但不再命中」的腐壞條目；③`pytest` 綠、`python -m audit invariants` 綠；④`~/.cloudflared/config.yml` 沒有 `mcp.`、`neo4j.`（查證：`grep hostname ~/.cloudflared/config.yml`；2026-09-24 已完成）；⑤AGENTS 那一句的改寫有使用者核准紀錄 | Phase 1 結案（避免同時兩個 writer 改同一批檔） |
| **本機 Research Action apply 入口** ✅（2026-10-01 Phase 4 Step 4.2d 交付；2026-10-02 真實資料 [668] 經入口 apply、`complete-ra` 比對戳記結案，結案 R2 以夾具驗過入口八種拒絕無寫入——Phase 4 closeout §1 gate 8）（2026-09-25 Phase 2 Step 2.1 發現、R2-a 建議排進本表；**2026-10-01 併入 Phase 4 plan 2026-10-01-001 Step 4.2d**〔§0.4 A4〕：反方驗證確認 apply 前不存在 go 收據——bare `go` 被拒、`complete-ra` 在 apply 之後——所以入口驗「未結案 `ra_admission`／`ref_id`／digest／紀錄未過期」四道 fail closed、apply 前把 approval 戳記寫進 action 紀錄；授權載體仍是對話中的明確核准） | 做一支固定入口（`scripts/` 下的 apply 腳本）取代「互動 session 直接呼叫私有函式 `intake.application._apply_research_action_impl`」；要不要規定帶 pq2 `ra_admission` 的 `go` 收據（編號）才執行，排程時定；同一個 change 走 sandbox impact review，**不得**進任何無人值守 allowlist | 遠端入口退役後，graph admission gate 的最後一步只剩「在對話裡呼叫一個底線函式」——prepare（`scripts/prepare_research_action.py`）與 publish（`scripts/commit_pending_intake.py`）都有固定入口，唯獨 apply 沒有；沒有固定入口，就沒有地方掛收據檢查與權限規則 | ①固定入口存在且有測試；②對 digest 不符、未核准的 action fail closed（測試）；③`docs/OPERATIONS.md` 與 `prompts/intake_protocol.md` 改指向它 | 無（排在 Phase 之間） |
| **需求側可刻意不主張＋相對漲幅不上首屏** ✅（2026-09-30 使用者定案、同日交付；Phase 3 closeout §5 #3／#4、plan §14 #32／#43／#44） | ①Abstention 加 `readings/demand_side`：圖上**真的沒有**它坐的層時，讀圖面板宣告 `deliberate_abstention`（settled，照抄那筆紀錄的理由與 id）；圖上有它坐的層卻宣告需求側＝和圖矛盾，不採用、照舊要寫讀圖。②相對組 30／90 天漲幅從首屏 placeholder 字彙拿掉、寫入端不再要求已定價那格引用它；只在稽核區印 | 需求端 23 檔的讀圖面板原本永遠結不了案（研究的誠實終局「它不坐任何層」沒有地方寫）；[656] go 之後組內 15 檔的敘事寫不進去（寫入端要引用、型別層又不收） | ①字彙封閉性測試改列 `readings`；②需求側宣告只在無座位時 settled（變異：永遠採用→紅）；③相對漲幅不在首屏字彙、有值不強迫引用（變異：加回字彙→紅） | 無 |
| **成交紀錄：首次建倉走對話＋兩個小修** ✅（2026-09-30 完成：87884fe＋四輪 R2 條件修正 e455674／11d959f／d62002e／0a65a2e，第四次覆核 GO；使用者定案；Phase 3 closeout §5 #4、plan §14 #11／#34／#38；**資本路徑，R2 trigger**） | ①使用者一句話（「我買了 X 股、成本 Y」）→ `record_trade.py` 在 Sheet **新增一列**建倉（今天只能更新既有列），照舊過 5% 單筆與 ETF 槓桿硬擋、先 dry-run 印收據；②同一筆成交（trade_id 已在 trade_log）重跑 `--apply` 一律 fail closed、不寫 Sheet；③一筆成交只讀一次 Sheet，同一份 rows 給定位、硬擋與收據 | 使用者不想手改 Sheet；重跑會把 Sheet 扣兩次（HEAD 起既有）；三次讀 Sheet 是三份不同快照 | ①新列建倉的 dry-run／apply 測試（假 Sheet）、硬擋在新列照樣擋；②重跑 `--apply` 拒收測試、Sheet 未被寫；③讀 Sheet 次數＝1 的測試；R2 覆核 GO ｜**遺留**（R2 覆核 non-blocking，都不會寫錯 Sheet 金額）：①既有列路徑寫到一半丟網路例外時沒有還原（只印可能已寫的格；2026-08-01 起既有）——要用同一套「例外後回讀比對」處理；②5% 單筆硬擋的已持有加總仍按原字串，不按 `canonical_symbol`（Sheet 現況全是慣例寫法；2026-09-30 日股改名冊寫法後，觸發條件是使用者照舊習慣手寫一列 `TYO:` 再用 `--also-at-other-broker` 在別家券商以 `.T` 建倉——那時公司層級的擋也不觸發，因為 `TYO:` 查不到名冊；修法是 `_held_value_for_symbol` 改用 `canonical_symbol` 比對、`resolve_holding` 查名冊前先正規化，兩處都只會更嚴）；③beta 判別不先正規化；④分數股在 Sheet 顯示四捨五入時，開列失敗後的回讀認不出自己那一列（會判「無法確認」、不動手）；⑥手寫市值的列加碼後市值不會跟著變、下一筆 5% 硬擋會低估已持有，既有列路徑完全不提示（R2 覆核 C2）——**2026-10-01 唯一的手寫列 7803.T 已出清（使用者刪列），Sheet 目前沒有這種列**；機制缺口仍在，日後有人手寫市值才會再出現；⑦~~既有列路徑不檢查現金欄幣別~~ ✅ 2026-09-30 修（R2 覆核 C1：日股／歐股加碼沒給 `--cash-column` 時，預設 `cash_usd` 會把外幣金額當美元扣掉——實測 7803.T 加碼 H21 會從 18,700 變 −16,300；現在兩條路徑都擋、在讀 Sheet 之前，`--log-only` 不碰現金格不擋；**第二次覆核 B1 補上沒給 `--currency` 的那一半**：既有列多定位一格 `currency`，成交幣別（沒給時是 USD）對不上 Sheet 那一列就拒收、指路該給的旗標，`--log-only` 也擋〔trade_log 的幣別 append-only〕；`--cash-column` 改成封閉字彙 cash_usd／cash_twd／none；缺匯率時指路 `--fx-to-base` 而不是 override）；⑧**`--fx-to-base` 沒有合理性檢查**（第三次覆核 N5，既有）：EUR 匯率給成倒數時，FRA:2DG 在 5% 邊界會量成 4.07% 而放行（正確約 5.06%）——修法是用同一次讀到的那一列 `market_usd／shares` 反推隱含匯率來比對；前提是使用者輸入錯誤，提示已寫明方向；⑨使用者自己刪掉某一列後想用 `--log-only` 補記，會被指路 `--open-position`，但兩者不能併用——這條路沒有合法旗標記得下來（第三次覆核 F4，只有使用者自己刪列才會碰到）；⑩`--log-only` 仍印股數與成本的前後對照（那時 Sheet 已是手改後的狀態，等於多算一次；純顯示、不影響 trade_log；第四次覆核 NB3，既有）；第三次覆核的其他順手修已交付：匯率 ≤0 入口拒收、幣別不符的提示一次寫齊（USD 列也寫現金欄、賣出不叫人給匯率、--log-only 不提現金欄）、--log-only 不印不適用的現金對照、測試替身斷言那一列三格同一個 symbol＋broker；⑤~~日股的研究代號與 Sheet 寫法不同~~ ✅ 2026-09-30 使用者定案「把 Sheet 改成公司名冊的就好，不用為了 Sheet 多做一套邏輯」：Sheet 第 3 列 `TYO:7803` 改成 `7803.T`（只寫代號一格、寫前比對現值；回讀市值公式原文、市值與 NAV 不變，整張表嚴格解析通過），建倉白名單改收名冊寫法 `XXXX.T`、`TYO:` 拒收並提示改寫，`canonical_symbol` 的正規化方向改成名冊寫法；`config/holdings_coverage.json` 的不研究登記跟著改名（留 `previous_sheet_ticker`）。7803（Bushiroad）本來就不在名冊（2026-07-29 使用者決定不研究），所以仍列「持股解析不到」——那是 Phase 4 #49 要接的 ignored 名單，不是寫法問題 | 使用者 opt-in R2（資本路徑） |
| **APP 看得懂：首屏三個字可點、候選板與結構表活起來** ✅（2026-09-30 使用者回饋、同日交付：「騎是什麼、插槽是什麼」「會死／已定價等回落是要我去候選板看詳細嗎？候選板跟結構表都是死的頁面」） | ①首屏三個字可以點，點了打開同頁稽核區、跳到那一題的數字；會死嗎把不是綠的燈逐盞寫出來（燈名＋理由，照抄 wipeout 面板）；②候選狀態那行直接寫理由、在等什麼、哪天醒、最晚哪天到期重問；③「看候選板 →」改成「和其他檔一起看（候選板）→」；④使用者看得到的「騎」改成「押」（寫敘事的範本問句也改，舊敘事原文不動——ledger append-only），層／插槽的白話只有一份 `briefing/analyst_view/contracts.py::PLAIN_BET_UNITS`，經 `.meta.json` 給 APP；⑤候選板列出沒有敘事、不上板的檔（`no_narrative[]`，與計數同一來源），註明上板的路是寫敘事；⑥結構表以圖裡節點的名字取代內部代號（ID 放 title）、加搜尋與依層篩選（只篩不重排、篩掉幾條照印；層選項由 materialize 排好，app.js 不排序） | 使用者讀不懂首屏的詞、以為細節在別頁；候選板只有 4 列、結構表滿是 `tech:*` 代號 | 真資料重跑 materialize 後 Edge headless 實點：三個字點下去稽核區打開並捲到那一題、結構表 223 條邊全部有名字、搜尋與依層篩選改變列數、候選板列出無敘事清單；候選板「押在哪一格」也改印節點名與中文判讀；新測試 11 條 | 無（使用者直接要求） |
| **重載會洗掉 SourceDoc 的分段標籤與標題** ✅（2026-10-01 Phase 4 Step 4.2e 交付；2026-10-02 pq2 [663] 對齊圖側後 SourceDocSync 兩個方向 0＋0——Phase 4 closeout §2）（**2026-10-01 併入 Phase 4 plan 2026-10-01-001 Step 4.2e**〔§0.4 A4〕：修法改成「section／title 寫回抽取 JSON」而不是 loader `coalesce`——反方驗證指出 coalesce 只救增量重載，全量重建時 10 份 section 仍消失〔不在可重建輸入裡，L10〕、title first-wins 因檔名排序仍拿到 addendum；loader 契約不動；計數器改「圖上 section／title 與抽取 JSON 不一致的份數」10＋21 → 0；`is_legit_multi_section` 三處共用。原提案原文留存於下——2026-10-01 系統提案；起因：健康審查「重複 SourceDoc」從 09-13 起天天紅，使用者指示「修復它」——當下修法已做：pq2 [662] 以 `loader/migrate_sourcedoc_section.py` 還原 `meta_vistara_isca_2026.section=asic_and_deployment`，manifest `loader/manifests/sourcedoc-section-meta_vistara_isca_2026-20260930.json`，紅 1→0；調查確認是 2026-08-06 [89] 刻意的分段、不是真重複，兩個 doc_id 都被 append-only 紀錄引用、都不能併；Phase 1 報告把它列為「不修」是有日期的紀錄，不改） | ①`loader/load_to_neo4j.py::MERGE_SOURCE_DOC` 的 `sd.section = $section` 改成 `coalesce($section, sd.section)`，`check_duplicate_url` 的新 section 取「新值，沒有就用圖上同一個 doc_id 的既有值」（**動 contract**：section 從此不能靠重載清掉——依 L17 先給提案）；②同一處的 title 也被 addendum 蓋掉（base 的 title 現在是「…addendum wave 2（自主研究迴圈第 6 輪）」；lrcx_10_k、lrcx_10_q、poet_6_k、nvidia_photonics_pr 等同樣），要不要一起保留母文件標題（L18）；③常駐計數器「section 只存在圖上」：比對圖上與抽取 JSON 的 section——今天 10 份（aaoi_10_k_20260227_competition、fas_dod_mp_partnership_2025_07_15、jlmag_ar2022_hkex、lynas_q1_fy26_quarterly_2025_10_30、miningweekly_lynas_terbium_2025_06_18、nvidia_photonics_pr_2025_03_18、schaeffler_humanoid_partnership_pr_2026_01_13、svrc_state_of_robotics_2026_us、thehumanoid_schaeffler_supply_deal_2026、sivers_ar_2025_photonics_excerpt〔兩份抽取檔不一致〕）任一份被重載就多一條紅，從頭全量重放今天會在 11 份撞 DuplicateUrlError；④`query/health_audit.py::_is_legit_multi_section` 補單元測試（現在在 `# pragma: no cover` 的組裝層），並對齊 `audit/checks.py:150-166` 只擋「同 URL 且同 section」的判準（L12）；⑤同一事件、不同 URL 的重複 URL 稽核看不到（MACOM Q3 FY26 法說會兩份逐字稿、IQE 兩份）——目前沒有共同的 canonical 邊、沒有灌大證據，記錄不處理 | 標籤只存在圖上、不在可重建的輸入裡（L10）：下一次重載或重建，紅燈就安靜回來，而那條紅會被當成「要合併」誤修（09-13／09-20 週報就診斷錯了方向） | ①重載 addendum 後 `meta_vistara_isca_2026.section` 仍是 asic_and_deployment（測試）；②「section 只存在圖上」計數器出現在心跳或健康審查、今天的值 10；③`_is_legit_multi_section` 有單元測試且變異會紅 | 無；①動 contract，先給提案 |
| **Phase 4 plan 的使用者定案輸入** ✅（2026-10-02 隨 Phase 4 結案交付，**除**「員工股酬另列不上色」——稀釋燈改讀新股發行金額後，大型股的員工計畫仍亮黃、占市值 % 印在稽核層，拆分留 Phase 4 plan §14 #20 待決；**2026-10-02 排入 Phase 6 plan Step 6.6**：窗內有募資文件才亮黃）（**已排進 Phase 4 plan 2026-10-01-001**：稀釋燈 Step 4.6〔編法改讀 `StockIssuedDuringPeriodValueNewIssues`——反方對 AXTI／AAOI／LITE 實測 companyfacts，原指定的股數 tag 在 AXTI／LITE 不存在〕、240 條／`ignored`／百分位／重複反證 Step 4.7、`_TICKER_ENRICHMENT` 與「客戶高管具名」〔改採併進 `self_reported`，今天 0 條邊命中〕Step 4.1、邊緣門檻不動；2026-09-30 使用者「全照建議」；Phase 3 closeout §5 #1、#2、#5、#6、#9–#12 與 plan §14 #20、#29、#35、#49、#46、#42） | 稀釋燈只在真的增發募資（公開增發、ATM）才亮黃，員工股酬另列不上色；舊 session assessor 的 240 條反證退役不印；7803.T（2026-09-30 前 Sheet 寫 TYO:7803）改印「使用者決定不研究」不算解析不到〔**2026-10-01 7803 已出清、使用者刪列，這一項的觸發消失；`config/holdings_coverage.json` 的 ignored 清空——把 ignored 名單接進 held_index／心跳的機制本身仍可做**〕（`config/holdings_coverage.json` 已改名；同時看 `engine_b/cli.py::_held` 對不在名冊的 `XXXX.T` 持股不補純數字鍵——R2 覆核 JP-PQ1-3，目前 0 條 lead 受影響）；`_TICKER_ENRICHMENT` 退出身分解析（改走 registry／execution 別名）；「客戶高管在供應商新聞稿具名」不算獨立客戶端印證（只當弱佐證）；邊緣門檻 10B／12 位先不動；自家百分位把樣本覆蓋率印出來、不設門檻；同一份敘事內重複的反證條件拒收、跨公司不算重複 | 使用者已答完 Phase 3 結案留下的判斷題，寫 Phase 4 plan 時不再重問 | 各項排進 Phase 4 plan 或旁支時各自定驗收 | Phase 4 plan |
| **海外財報來源** ○（2026-09-30 使用者「之後再加、要排程」；**2026-10-04 使用者：研究過程用到就一起做**——研究撞到哪個市場的缺口就做那一格（①台股、②20-F 不用申請；③日、④韓等使用者申請 key），照 development-flow 一格一驗收，範圍大或有要使用者選的就停下問；Phase 3 closeout §5 #14；盤點與日韓查證：`docs/reports/2026-09-30-overseas-data-sources.md`；**2026-10-05 研究撞到①台股（聯亞、華星光、全新的敘事停在「缺 X：已定價嗎的主參照」）與日、澳、港（failure log #19）：①的 PLAN_PROPOSAL 已寫（來源 MOPS t163sb05 已驗證），見 `docs/plans/2026-10-05-001-feat-tw-historical-shares-proposal.md`；
**使用者 2026-10-05 go，①台股已做**：季報股本換算股數（÷10 元扣庫藏股、以權益÷每股淨值交叉核對，差 >2% 或期間內有配股除權的季整季不用）、
可知日＝一般業法定期限、金融業版型拒收；回補 14 季 168 筆（拒收 4）、月營收補到 2022-10；**12 檔台股已定價① 12/12 由缺席變有值**
（第 88–100 百分位）；S3 照月營收先例留互動式＋心跳計數器（比 plan 原寫的 daily 接線窄）；R2 CONDITIONAL_GO、兩條條件已修**） | 依「影響幾檔邊緣候選」排序：①台股歷史股數 ✅ 2026-10-05（MOPS t163sb05；12 檔台股 12/12 有值）；②20-F 年度封面股數（3 檔；SEC 有、程式刻意不收，只改程式；ADS 比率與幣別另處理）；③日本 EDINET API v2（3 檔；要使用者本人註冊、需簡訊或語音驗證；2024 後只有半年報與年報）；④韓國 OpenDART（3 檔全是非邊緣大型股，排最後）；中港、歐洲、加澳未驗證 | 邊緣候選 22 檔裡 18 檔是海外或 20-F，已定價的主參照（自家三年百分位）全部缺；非台股海外 13 檔的「出現在數字裡」也缺 | 每補一個市場：該市場邊緣檔的自家百分位從缺席變有值的檔數（個股頁稽核區）；可知日用申報日，不用抓取日（INV-6） | 各市場的 key 由使用者申請（日、韓） |
| **多主題等權組** ◐（2026-10-05 系統提出；PLAN_PROPOSAL [`2026-10-05-002`](plans/2026-10-05-002-feat-multi-theme-cohort-proposal.md)，Z2／R2；2026-10-06 使用者選 A（非組員列具名缺席），S1 已實作並上線；R2＝CONDITIONAL_GO（C1 APP 計分表那句「列在濾掉理由裡」不實、C2 組員但組報酬取不到的列沒進缺席名單），等使用者決定；S2 兩鏈的組走 pq2，spec 已備） | 追蹤表與計分表的組基準改成「每一列用自己所屬的組」（0 組、多組各有具名缺席）；題材 ledger 改以題材分組讀、新題材檔名加雜湊（既有檔不搬） | Phase 7 failure log #16（P1／C1 的組因「多於 1 組就整格缺席」沒鑄號）與 #26（散熱鏈四份敘事早於組落地）；盤點時另發現「電力」「散熱」的 ledger 檔名都是 `__.jsonl`，一建就互相蓋掉——2 次、同日 | 新增第二、三組後追蹤表有組超額的列數不減少（光通訊 15 列逐列相同）；電力、散熱各自讀得到現行組；散熱四份敘事的稽核區組中位數由缺席變有值 | 無（plan 7.1 ④ 的組 spec 在本項之後由研究 session 鑄 pq2） |
| **個股頁 schema** ○（2026-10-05 使用者指示；brainstorm [`2026-10-05-stock-page-schema`](brainstorms/2026-10-05-stock-page-schema.md)、PLAN_PROPOSAL [`2026-10-05-003`](plans/2026-10-05-003-feat-stock-page-schema-proposal.md)，Z3，S0 ✅、AWAITING_HUMAN） | 個股頁改由 schema 驅動：十二塊，每塊宣告問題、單位（題材錨／路徑／層／插槽／公司／事件）、誰寫、要看到什麼、缺席出口；技術與層的內容掛在節點上、同層共用（新研究 ledger「層說明」）；七檔測試集的填得滿表偵測 overfit。S1 磨合輪（畫布，不寫 production code）→ S2 合約 → S3 機械資料（需求錨、同業營收、吃到多少、台股地區別、既有 Engine C 觀測接頁）→ S4 層說明與同階段同業 → S5 版面 → S6 維護 | 使用者三輪回饋（第一輪 v1–v4 只對聯亞成立）；Engine C 已有客戶集中度 31 檔、分部 32 檔、backlog 32 檔，個股頁沒有一塊在印 | 七檔每一塊有值或具名缺席（個股頁稽核區）；每份層說明被 ≥2 頁引用（研究 ledger＋結構表）；回饋紀錄每列指得出版本與元素 | S2 起每個 Step 使用者點名；S3 命中 R2 第 2 條；非光通訊三檔的事件反應等「多主題等權組」 |

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
12. **Local-first；不開對外的寫入入口。**（2026-09-25 Phase 2 Step 2.1 改寫：原句「Core 不得 import `mcp_server`」守的套件已刪）
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
