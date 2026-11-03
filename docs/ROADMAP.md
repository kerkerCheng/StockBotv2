# StockBotv2 — Roadmap（2026-09-22 重建：圖是中心）

> **本檔只放 active future work：Phase 與四欄（做什麼／為什麼／驗收／前置）。**
> 判準與邊界住 [`AGENTS.md`](../AGENTS.md)；程序住 [`OPERATIONS.md`](OPERATIONS.md)；
> 決定紀錄住 [`brainstorms/2026-09-22-graph-first-direction-decision.md`](brainstorms/2026-09-22-graph-first-direction-decision.md)（G1–G12）。
> 前一版（Alpha Edge Phase 0–7、amendment、backlog）逐字封存於
> [`archive/roadmap-alpha-edge-2026-09-22.md`](archive/roadmap-alpha-edge-2026-09-22.md)。
> 圖是中心版自己已交付的部分也封存（2026-11-01）：Phase 0–6 列、2026-09-22 快照、消費層對照表、Phase 0 退役清單在
> [`archive/roadmap-phase-delivery-log.md`](archive/roadmap-phase-delivery-log.md)；已交付的旁支列在
> [`archive/roadmap-backlog-log.md`](archive/roadmap-backlog-log.md)（各檔 2026-11-01 節）。
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

---

## Phase 表

> 標記：▶ 進行中｜◐ 部分交付、剩下的寫在該列｜○ 未開工｜✅ 完成。研究項（pq2）不占本表。
> **開著的（2026-11-01 盤點；同日批次三 A、B 交付後，晚上加「候選板標出只差已定價」◐；11-03 批次三 C 交付）：Phase 7 ▶；旁支 ◐ 3、○ 0。** 查證（列出標記不是 ✅ 的表格列；◐ 列的內文會有 ✅，所以只看粗體名稱後面那一格）：`grep -n "^| \*\*" docs/ROADMAP.md | grep -v "\*\* ✅"`
> **推進規則：** Verdict 為 `GO` 且沒有待使用者決定的問題時直接接續，Step 與 Phase 邊界一視同仁；六條停止條件住 `AGENTS.md`「協作與邊界」。
> **執行者是便宜模型時 Z1 以上預設 R1**（development-flow）。

| Phase | 做什麼 | 為什麼 | 驗收（數的是哪一層的東西） | 前置 |
|---|---|---|---|---|
| **0–6** ✅（2026-09-23 → 10-04 逐 Phase 結案：0 拆 09-23、1 等待與心跳 09-25、2 讀圖兩種單位＋走圖 09-26、3 候選狀態＋三題 09-30、4 層中心來源 10-02、5 量測 10-02、6 證據判準 10-04；plan、closeout 與 R2 verdict 的對照表住 [`plans/README.md`](plans/README.md)；四欄原列（含各 Phase 的 amendment 與結案數字）逐字封存於 [`archive/roadmap-phase-delivery-log.md`](archive/roadmap-phase-delivery-log.md) 2026-11-01 節） | North Star 圖上標了 Phase 號的那幾段：來源選擇（4）、走圖（2）、讀圖（2）、反證鑄 watch（1）、敘事與候選狀態（3）、三題（3）、量測（5）、證據判準（6）——都已交付，現行形狀住 ARCHITECTURE | 拆掉舊管線在圖與人之間的十層，圖到人之間才沒有分數；之後每一 Phase 各接一段 | 已結案；仍會自己出現的回查住心跳常駐計數器（Phase 5 ②圖預測表第一筆對／錯——段 4「圖預測」行；Phase 1 ④到期的 watch 不消失——date watch 讀圖來源最早 2026-11-18、假設型最早 2027-01-01） | — |
| **7 研究使用與量測（持續型）** ▶（2026-10-04 開；第一期到 2026-12-22 檢查點，之後每季一個檢查點，Phase 本身不「結案」；plan [`2026-10-04-001`](plans/2026-10-04-001-research-phase7-research-edge-plan.md)；使用者 2026-10-04 定案 Q1–Q8、A1–A4，amendment A1（本列）／A2（AGENTS 一句）五欄見 plan §0.4；能力盤點與設計 [`brainstorms/2026-10-04-phase7-research-edge-proposal.md`](brainstorms/2026-10-04-phase7-research-edge-proposal.md)） | **研究、量測、開發不設比例（2026-10-07 使用者定案，plan A5；原「研究約 75%、量測約 15%、開發 ≤10%」）：擋住研究的開發排在研究前，過 gate 的開發項隨時提；系統主動提出的仍要指得出真實案例與重複次數。** **7.0 開場**：預先登記（十個 edge 假說與殺死條件、14 個 case 與類型、裁決規則、failure log、開發 gate、漏網稽核母體）＋T0 凍結（手動 manifest）；開發 gate 落地＋兩個當下修（巢狀 writer lock、thesis 逾期提醒量錯）；敘事範本「要翻倍需要什麼」（營業數字，不寫目標價）＋市值與近四季營收兩個 placeholder＋「已定價」白話＋重押讀圖換格層引用；敘事「加碼條件」`confirm[]`（寫下即登記 watch、觸及只提醒、不是買進訊號）；個股頁首屏照五題排列＋候選板與個股頁標「和持股共用需求錨」；**外部雷達**：daily 加一步只開 WebSearch 的 `claude -p`，網址必須出自同一次搜尋結果、每日約 5 則、寫成 tier-4 secondary lead、不喚醒語意 watch、不另發通知（它不是 last30days：有 provenance 契約），**八週試驗：2026-10-05 上線、第 56 天是 11-29；原停止條件照舊——「triaged_go 且追到一手或入圖、而且沒有別的管道更早登記」全期為 0 就退役；11-30 出「第 56 天報告」（逐筆 lead id、按儀器版本分段計數、沒跑的天照印），非 0 時續不續由使用者在 12-22 檢查點決定（2026-10-21 A10）**。**7.1／7.4 兩波研究**（光通訊跟 Q3 財報；電力與散熱兩條新鏈、該鏈的主題等權組在第一份敘事前前瞻定義；SNS 40 則 claim 裁決；二階瓶頸三個 case；800VDC 擱置五則回看）；**7.2 回放**（已定價、漏網稽核是機械的；parked 回查、輸家驗屍是研究）；**7.3** Q3 財報季裁決與 2×2；**7.5 檢查點**（決定紀錄 §10＋假說證據帳＋failure log 依重複次數排序＋雷達停止條件＋T1 manifest＋R2） | 機制遠超過使用（讀圖 4、敘事 4、可開每天 0、外部來源 1 個、測試 3,448）；edge 有沒有、從哪裡來，報酬量測要到 2027 才成熟，只能靠預先登記的案例、前瞻凍結與快迴路逐步淘汰假說；AXTI 顯示判斷層可能把我們從贏家身上說服走（n＝1）；LLM 研究者的知識截止（2026-06）讓之前的判讀回放不可信 | ①光通訊以外 ≥2 條鏈各有現行讀圖、每份 ≥1 條登記反證（讀圖、registry）；②新敘事每份有候選狀態、押的讀圖（短檢查判不坐任何層／開發中／在需求側等，寫明理由、不另立 rides）與翻倍條件（判「不要」的寫出「為什麼翻不了倍」就算數——2026-10-21 使用者照推薦）；持有或可開、且狀態不是「不要」的，另有加碼條件；持有但判「不要」的非倍率持股，加碼與反證住它的 thesis（敘事；thesis 的反證數等待 registry；2026-10-21 A9）；③預先登記的 commit 早於 wave 1 任何新讀圖／敘事，T0 manifest 與當日心跳一致（讀圖、敘事、registry）；④S1 的 40 則 claim 各有裁決或到期（registry）；⑤Q3 財報季（2026-10-21～11-30）：裁決點落在窗內的現行敘事（持股＋缺 X＋等回落；名單在 2026-10-21 凍結並寫進 case 段），每份都有財報後新版或不換版理由；非倍率公司（含 LITE、COHR 的層面）的財報只當層的證據，寫進讀圖換版或 case 段；窗內到期與已觸發的 watch 全部處置（敘事、讀圖、registry）；⑥每個開了的 case 有產出 id 與裁決，2×2 各列（追蹤表）；⑦雷達上線、第一輪收據、11-30「第 56 天報告」（分版計數、逐筆 lead id）與八週停止條件有結論（registry）；⑧檢查點：H1–H10 每個有證據列與 n（追蹤表）；另：開發 Step 各自的測試與變異（機制），進 ROADMAP 的開發項每一項指得出 ≥2 個 case | 6 |

**每個 Phase 開工前要有 plan；沒有就停。** Phase 與 plan 檔的對照、以及「開 plan session」要貼的指令住 [`plans/README.md`](plans/README.md)。

### 研究並行（不是 Phase）

**2026-10-04 起研究本身就是 Phase 7**（持續型；預先登記、凍結、檢查點），研究項仍走 pq1／pq2、不占本表。

### 旁支開發項（不是 Phase；不插進執行中的 Phase，排在 Phase 之間或使用者點名時做）

| 項目 | 做什麼 | 為什麼 | 驗收（機制存在與否） | 前置 |
|---|---|---|---|---|
| **海外財報來源** ◐（①台股 ✅ 2026-10-05、②20-F ✅ 2026-11-03、③日本 EDINET ✅／④韓國 OpenDART ✅ 2026-10-21，**剩中港、歐洲、加澳未驗證**；2026-09-30 使用者「之後再加、要排程」，2026-10-04 使用者「研究過程用到就一起做」——研究撞到哪個市場的缺口就做那一格，照 development-flow 一格一驗收，範圍大或有要使用者選的就停下問；Phase 3 closeout §5 #14；盤點 `docs/reports/2026-09-30-overseas-data-sources.md`；①的 plan `plans/2026-10-05-001-feat-tw-historical-shares-proposal.md`、③④的 plan `plans/2026-10-21-002-feat-jp-kr-filings-plan.md`（查證命令見該 plan「現況」那一行；OpenDART 個資 2 年重新同意掛 [835] pending 到 2028-09-21）；①③④ 的交付敘述逐字封存於 archive/roadmap-backlog-log.md 2026-11-01 節） | **剩中港、歐洲、加澳**（未驗證來源）。已做：①台股歷史股數（MOPS t163sb05；12 檔台股 12/12 有值）、②20-F 年度封面股數（ARBE、HIMX、POET 3/3；掛牌單位比率住名冊 `ordinary_per_listed_unit`，幣別不換照舊）、③日本 EDINET 13/13、④韓國 OpenDART 6/6 寫入 `fundamental_history` | 邊緣候選 22 檔裡 18 檔是海外或 20-F，已定價的主參照（自家三年百分位）全部缺；非台股海外 13 檔的「出現在數字裡」也缺（2026-09-30 盤點時的數；台日韓補完後只剩 20-F 與未驗證市場） | 每補一個市場：該市場邊緣檔的自家百分位從缺席變有值的檔數（個股頁稽核區）；可知日用申報日，不用抓取日（INV-6） | ②不用申請 key；中港、歐洲、加澳先驗來源 |
| **個股頁 schema** ◐（S0–S5 ✅ 2026-10-05 → 10-15；**剩 S6 維護——設計已出（2026-11-03，plan「S6 維護——設計」節），待使用者選兩題**；2026-10-05 使用者指示；brainstorm [`2026-10-05-stock-page-schema`](brainstorms/2026-10-05-stock-page-schema.md)、PLAN_PROPOSAL [`2026-10-05-003`](plans/2026-10-05-003-feat-stock-page-schema-proposal.md)，Z3；S0–S5 的歷程與 amendment D–G 逐字封存於 archive/roadmap-backlog-log.md 2026-11-01 節；查證：`python -m webapp status` 列得出 `layer_notes`、`python -m alpha layer-note mat:inp_epiwafer`） | 個股頁改由 schema 驅動：十三塊，每塊宣告問題、單位（題材錨／路徑／層／插槽／公司／事件）、誰寫、要看到什麼、缺席出口；技術與層的內容掛在節點上、同層共用（研究 ledger「層說明」）——S0 畫布、S4 層說明、S2 合約、S3 機械資料、S5 版面都已交付。**S6 維護**：層說明到期重讀接走圖第 4 型、回饋紀錄常駐；先設計再開工 | 使用者三輪回饋（第一輪 v1–v4 只對聯亞成立）；S5 結案時記下 S6 的兩件事還沒有落點：層說明到期後的重讀沒有接進走圖第 4 型、回饋紀錄沒有常駐的地方 | 因層說明改變候選狀態的筆數、層說明主張登記成 watch 的裁決（registry）；每份層說明被 ≥2 頁引用（研究 ledger＋結構表）；回饋紀錄每列指得出版本與元素 | 使用者選 S6 設計的兩題（回饋紀錄的形狀、範圍）後開工（沿用「S2 起每個 Step 使用者點名」） |
| **候選板標出只差已定價** ◐（程式 ✅ 2026-11-01 雲端 session；**剩真資料驗收**：本機 materialize 一次後候選板、心跳與短版印出；使用者 11-01「我覺得你講的都算方向正確…可以直接改?」；failure log #123；查證：`python -m crons.heartbeat` 段 2 候選行的「只差已定價」、`python -m webapp status` 的 candidates/4） | 等回落列假設把已定價當脈絡、改宣告可開，用**同一個** `open_preconditions` 驗前提，結果放 `open_gaps`（另加它不查的兩項：沒押讀圖、邊緣不是邊緣）；心跳狀態塊、短版 ④ 等回落行、首頁卡片晶片、個股頁候選行照印；research-drain 段 5 ⓪：標了就只重答已定價那一格、收尾摘要點名給使用者下價格判斷。**不改分組、不改可開的前提**；把已定價改成可開裡的脈絡（A1 第 4 點的完整版）是使用者的決定，見 `plans/2026-11-01-002-dev-priced-wait-proposal.md` | 10-21 Q3W 處置紀錄：3081.TWO、4979.TWO、AXTI 四個機械前提全過、只差已定價；10-31 三檔被價格叫醒重答仍寫等回落；等回落不進使用者的決策時刻（A1 第 1 點），A1 第 4 點卻說已定價是脈絡不是否決——價格判斷實際由寫敘事的 session 下掉（3 檔同形） | 候選板每一列等回落帶前提清單（候選板＝敘事＋讀圖＋registry 推導）、使用者看得到；⚠ 標了幾檔不是驗收（G10）。效力看慢迴路：等回落 → 可開／不要／已持有在重看日之前的轉換數（敘事 ledger；10-30：0）與使用者對標了的檔留下的決定（成交紀錄或敘事換版）；`tests/test_priced_only.py` 18 條、變異 7 種全紅 | 本機 materialize 一次（雲端容器沒有 `library/private`） |

### 已交付的旁支（索引；原列逐字封存於 [`archive/roadmap-backlog-log.md`](archive/roadmap-backlog-log.md) 2026-11-01 節，含每項的驗收數字與查證命令）

> 日期＝交付日。這裡只留落點，讓程式註解裡的 `ROADMAP「標題」` 找得到；要看做了什麼、數字怎麼變，讀封存列。

- 2026-11-03 **敘事 stale 計數器**（①③＋同源 10-29；②④＋寫入端拒收 11-03）——正文最後一次改動時騎的讀圖 vs 這一格現行的讀圖：判讀（kind）或供給側家數變了 → 候選列 `rewrite[]`、整板 `kind=reading_kind／supply_count`、⑤「敘事該重寫」點名（`alpha.candidates.body_behind_readings`；比讀圖結構、不解析正文「N 家」）；寫入端 ⑫ 拒收正文一字不改卻跨過這兩種改變的換騎。回放 497 版：正文沒改的換騎 115，判讀變了 1（AEVA 10-19）、家數變了 29（含 COHR／LITE／SIVE.ST）；現行 89 份 ②0 ④0；`tests/test_narrative_stale_24.py`；plan `plans/2026-11-01-001-dev-phase7-batch3-plan.md` C
- 2026-11-03 **海外財報來源 ②20-F**（使用者「E 1A 2A」）——名冊 `ordinary_per_listed_unit`（一個掛牌單位＝幾股普通股，帶生效日與出處；沒登記＝照舊 inputs_incompatible）；回填收 20-F 封面股數（原單位＝普通股），取數層按封面日當時的比率換成掛牌單位；已定價①對年報申報人用年度點（營收最多 550 天、營業利益同樣取年度點判口徑），最新封面申報後 13 個月沒有新封面的那一天不算樣本、今天超過整列缺席，稽核區印「年度點」與封面日、申報日、距今天數；`tests/test_three_questions.py`、`test_three_question_inputs.py`、`test_identity_registry.py`；plan `plans/2026-11-01-001-dev-phase7-batch3-plan.md` E。**真資料**：ARBE 13.2、HIMX 81.4、POET 46.3（缺席 → 有值 3 檔，覆蓋率都 1.0）；EFXT 照舊缺席（CAD≠USD）
- 2026-11-03 **成交紀錄遺留八項**（`record_trade.py`；2026-09-30 R2 四輪覆核的 non-blocking ①②③④⑥⑧⑨⑩）——寫入回應失敗時逐格回讀（沒寫＝隔 3 秒再讀、不承諾重跑安全／全寫／寫一半往前補／認不得請人看）、顯示值比對容許四捨五入（`gsheets.display_matches`）、同一檔的兩種寫法在 5% 上限、beta 判別、snapshot 別名表與 policy 唯一性都當同一檔（`identity/symbols.py`）、公式欄有手寫值的列拒絕改股數、`--fx-to-base` 用同一列反推匯率核對（差兩倍以上拒收）、`--log-only --row-deleted`（只收賣出、必給券商與幣別）、`--log-only` 只印現值、股數與成交價必須 > 0；`tests/test_record_trade_leftovers.py`；plan `plans/2026-11-01-001-dev-phase7-batch3-plan.md` D。**真資料**：19 列持股手寫市值 0、寫法與正規化不同 0、beta 判別變動 0；8 列非 USD 的反推匯率與 yfinance 差 0–2%
- 2026-11-01 **等回落的重開條件**——敘事 `candidate_state.reopen`（價位或自家三年百分位，或「不適用：」），新寫的等回落必帶；寫了可比對條件的列叫醒只看它（取代回落叫醒），沒寫的舊紀錄進一次「沒寫重開」由 drain 補寫；心跳狀態塊「重開達成／沒寫重開」、短版與個股頁印條件與距離；`tests/test_reopen.py`；plan `plans/2026-11-01-002-dev-priced-wait-proposal.md` P1。**真資料**：本機下一次 materialize 後現行四份等回落會在 ⑤ 列「沒寫重開」，drain 各補一版
- 2026-11-01 **alpha 格只觀測**——2026-09-16 D1 落地（使用者「兩點都照你建議吧」）：`config/target_allocation.json` 的 alpha 格 `observed_only`、不帶目標；配置差距只印實際佔比、不進「低於／高於目標」摘要、不引導新資金；beta 五格目標不動（合計 0.90）、全部有目標時總和仍須 1.0；`tests/test_alpha_observed_only.py`；plan `plans/2026-11-01-002-dev-priced-wait-proposal.md` P3
- 2026-11-01 **週額度常駐計數器**——每次 `claude -p` 的 `rate_limit.windows` 記下每個窗（`crons/llm_step.py::_rate_limit`）；短版 ④ 每天一行「LLM 額度：7 天 X%（重置）｜5 小時 Y%（重置）」、週用量 ≥ 80% 粗體＋摘要行「週額度已用 X%」（`crons.heartbeat.quota_usage`／`quota_flag`；**只印不擋**，門檻量到 2026-12-01 再定）；互動 session 開 workflow／fan-out 前 `python -m crons.llm_quota [--probe]` 讀同一個數。11-01 真資料：daily 06:30 的紀錄 7 天 86%、探針 12:00 當下 99%（5 小時 79%）；基準 24 天裡 6 天 `rate_limited`；`tests/test_llm_quota.py`；plan `plans/2026-11-01-001-dev-phase7-batch3-plan.md` B
- 2026-11-01 **邊緣門檻的遲滯與在門檻上計數器**——撤回建議要**連續兩次**判非邊緣（今天＋輸入日前一天的 as-of 判定；`alpha/providers/edge.py::attach_prior_judgments`），今天才翻的列帶「非邊緣待確認——明天再看」照敘事分組、閉環母體留著；候選板／心跳段 2／closure-gate 印「在門檻上」（上限 ±1 家或 ±10%）名單，只計數；門檻值不動。回放 10-21～11-01 四檔：現行規則撤回建議 5／重寫 3 → 4（＋1 待確認）／3（`python -m alpha edge 002837.SZ 6481.T LYC.AX AMKR --replay --from 2026-10-21`）；`tests/test_edge_hysteresis.py`；plan `plans/2026-11-01-001-dev-phase7-batch3-plan.md` A
- 2026-10-31 **只改字面值的換版不重設判斷日**——敘事 v2 選填 `restates`，判斷日與正文版沿用被重述那一版；`tests/test_brief_restates.py`
- 2026-10-31 **首屏敘事不寫死燈色與價格報酬**——寫入端拒收「燈名＋顏色」、已定價那一格寫收盤價只印 ⚠；`tests/test_narrative_literals.py`
- 2026-10-31 **宣告可開前的深挖清單**——`alpha/narrative/depth_check.py` 十個鍵，宣告可開時逐項印缺哪幾項（只印不擋）
- 2026-10-30 **等回落的價格叫醒**——候選板每天算 `pulled_back`、狀態塊「等回落 N（已回落 M）」；`tests/test_priced_since.py`
- 2026-10-30 **缺 X 三分法與文件請求上限**——`candidate_state.missing_kind`（filing／layer／user_document）、同時開著的文件請求上限 5 只印不擋、心跳段 5「文件請求計分」
- 2026-10-30 **融資型資料中心 capex 進需求錨**——`oracle_cash_capex`／`coreweave_cash_capex` 兩條單一型序列掛四個錨；`tests/test_demand_anchor.py`
- 2026-10-29 **個股頁：故事層與依據層**——每格分故事與依據、故事 ledger（`python -m alpha stories --gaps`）；ARCHITECTURE §6.11
- 2026-10-29 **paper 線取價上限照代號截掉過半**——拿掉上限全部取價，抓不到的逐檔列 `price_budget.unpriced`／`rate_limited`
- 2026-10-28 **APP 照使用者問題重組**——11 頁 → 5 頁（公司／每日／圖／成績單／資產配置）；[`brainstorms/2026-10-28-app-attention-ia.md`](brainstorms/2026-10-28-app-attention-ia.md)，每段去處 ARCHITECTURE §6.9
- 2026-10-27 **叫醒先過預篩（追源線索、讀圖客戶重讀）**——`event_watch.wake_screen` 唯一判斷、`wake-queue`／`wake-judge`；`tests/test_wake_screen.py`
- 2026-10-21 **已定價變動常駐計數器**——心跳段 2 等回落行印「判斷日的百分位 → 今天」；`tests/test_priced_since.py`
- 2026-10-21 **雷達精進**——A 當下修、B 市場層第 6 題、C1–C4（`engine_b/impact.py` 影響對照、停放前處置、摘要「可能怎麼影響」、讀過的層輪替）；`docs/reports/phase7/miss-replay.md`
- 2026-10-15 **人工觀測的取代鏈收多值（Engine C `manual_observations`）**——A：唯一 owner `engine_c.manual_observations`＋append-only `manual_observation_supersessions`；closure-gate「同一期間有多筆生效觀測」14 → 0；[757] 換匯值的更正另鑄 [758]，2026-10-15 go、已寫入 Engine C ledger
- 2026-10-08 **名冊候選分層與批次登記**——A：`onboard-candidates --tier／--mark-supply／--draft`、`todo add-registry-batch`／`complete-registry-batch`、`engine_b.cli registry-rescan`；plan `plans/2026-10-08-001-dev-phase7-batch-plan.md`
- 2026-10-08 **daily 短版三個修正**——健康度只在額度真被擋才寫「沒跑」、市場大事逐則列、待你決定帶建議指令；`tests/test_daily_digest.py`
- 2026-10-08 **名冊外判邊緣**——`python -m alpha edge <代號…>`，同一個邊緣判定、逐欄標來源
- 2026-10-07 **研究預算分層（深度在層、廣度在檔）**——Phase 7 Step 7.0g：閉環母體收窄、母體外逐檔列名、資料檢查母體＝全部個股頁
- 2026-10-06 **多主題等權組**——追蹤表與計分表每一列用自己所屬的組；[713] 電力、[714] 散熱；plan `plans/2026-10-05-002-feat-multi-theme-cohort-proposal.md`
- 2026-10-02 **Phase 4 plan 的使用者定案輸入**——八項各排進 Phase 4／6 plan（稀釋燈改讀新股發行金額 → Phase 6 只認募資文件、240 條舊反證退役、`_TICKER_ENRICHMENT` 退出身分解析…）
- 2026-10-01 **重載會洗掉 SourceDoc 的分段標籤與標題**——Phase 4 Step 4.2e：section／title 寫回抽取 JSON，不一致計數 10＋21 → 0
- 2026-10-01 **本機 Research Action apply 入口**——Phase 4 Step 4.2d：固定入口，未結案 `ra_admission`／`ref_id`／digest／未過期四道 fail closed
- 2026-09-30 **需求側可刻意不主張＋相對漲幅不上首屏**——Abstention `readings/demand_side`（圖上真的沒座位才 settled）；相對漲幅只在稽核區
- 2026-09-30 **成交紀錄：首次建倉走對話＋兩個小修**——`record_trade.py` 新列建倉、同一 trade_id 重跑 fail closed、一筆成交只讀一次 Sheet；R2 四輪後 GO；遺留見下
- 2026-09-30 **APP 看得懂：首屏三個字可點、候選板與結構表活起來**——三個字點開稽核區、候選狀態行寫理由與到期、結構表用節點名
- 2026-09-25 **Graph MCP 退役**——Phase 2 Step 2.1：`mcp_server/` 刪、I 組殭屍 grep 掃所有 tracked 檔（`scripts/retired_mechanism_grep.py`）

### 已交付列留下的遺留小項（未排程；不占四欄——要排程時照 AGENTS 補四欄與案例次數；事發與修法方向住封存列）

- **SourceDoc 重複稽核 ⑤**——同一事件、不同 URL 的重複看不到（MACOM Q3 FY26 兩份逐字稿、IQE 兩份）：沒有共同 canonical 邊、沒灌大證據，記錄不處理。
- **`ignored` 名單接 held_index／心跳**——機制可做；`config/holdings_coverage.json` 的 ignored 目前清空（7803 已出清），沒有觸發案例。

---

## Phase 0 退役清單（已封存；執行面在測試裡）

八組 regex、keep-list 的五類合法理由、「驗收是差集不是絕對零」、decision_lab 凍結表（留／刪／搬）與「測試跟機制走」的清單（2026-09-22 盤點、09-23 結案）逐字封存於 [`archive/roadmap-phase-delivery-log.md`](archive/roadmap-phase-delivery-log.md) 2026-11-01 節。執行面：`scripts/retired_mechanism_grep.py`（A–H 八組＋I 組 Graph MCP），`tests/test_retired_mechanisms_stay_retired.py` 每次 pytest 重現三個驗收數字（2026-10-06 使用者指示；Phase 7 failure log #30）；誤報的處理是改字、或列 keep-list 並寫出類別與理由，不放寬 regex。查證：`python scripts/retired_mechanism_grep.py`。

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
  2026-10-06 使用者加選 **AI 生醫**（pq2 [723]）；2026-10-21 收窄成「三問全中才算」：付錢的是 AI 程式、買的是實體輸入且量跟著 AI 走、落得到一層或具名供應商（使用者「生醫 go」；同日移除非 AI 的中國創新藥授權鏈 `cnbio`）——需求錨等 decompose 在圖上長出節點後再進 `sector_anchors.json`，
  它與 AI capex 共用「前沿 AI 實驗室的支出」這個上游（相關性要點明，N 條鏈 ≠ N 個獨立賭注）。查證：`grep -n aibio config/themes.txt`。
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
