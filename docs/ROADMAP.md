# StockBotv2 — Roadmap（2026-09-22 重建：圖是中心）

> **本檔只放 active future work：Phase 與四欄（做什麼／為什麼／驗收／前置）。**
> 判準與邊界住 [`AGENTS.md`](../AGENTS.md)；程序住 [`OPERATIONS.md`](OPERATIONS.md)；
> 決定紀錄住 [`brainstorms/2026-09-22-graph-first-direction-decision.md`](brainstorms/2026-09-22-graph-first-direction-decision.md)（G1–G12）。
> 前一版（Alpha Edge Phase 0–7、amendment、backlog）逐字封存於
> [`archive/roadmap-alpha-edge-2026-09-22.md`](archive/roadmap-alpha-edge-2026-09-22.md)。
> 圖是中心版自己已交付的部分也封存（2026-11-01）：Phase 0–6 列、2026-09-22 快照、消費層對照表、Phase 0 退役清單在
> [`archive/roadmap-phase-delivery-log.md`](archive/roadmap-phase-delivery-log.md)；已交付的旁支列在
> [`archive/roadmap-backlog-log.md`](archive/roadmap-backlog-log.md)（各檔 2026-11-01 節）；2026-11-27 再封存 Phase 8 列、兩列已交付旁支與已交付索引的交付敘述（各檔 2026-11-27 節）。
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
    ↓                                  缺 X ──→ 鑄 watch         【Phase 3】
三個財務是非題：會死嗎／已定價嗎／出現在數字裡了嗎         【Phase 3】
    ↓
個股故事頁：偵探蒐證、一頁從頭讀得懂                       【Phase 8】
    ↓
人決定買不買、買多少；出場認反證；量測 power-law           【不變；Phase 5】

        等待 registry（已有，加「語意條件」kind）            【Phase 1】
        心跳：零 LLM 印 diff ｜ AI 層只讀 T0 篩過的文件 ｜「未檢 N」必印
```

**圖到人之間沒有任何一段算分數。** 舊管線在圖與人之間有十層，其中排序、籃子 filter、估值、多年橋、賭注四價、decision_lab 鑄號六層在 Phase 0 退役。

---

## Phase 表

> 標記：▶ 進行中｜◐ 部分交付、剩下的寫在該列｜○ 未開工｜✅ 完成。研究項（pq2）不占本表。
> **開著的（2026-11-27 整理；Phase 8 同日結案）：Phase 7 ▶；旁支 ▶ 1、◐ 3、⏸ 1、○ 1、維運 1。** 查證（列出標記不是 ✅ 的表格列；◐ 列的內文會有 ✅，所以只看粗體名稱後面那一格）：`grep -n "^| \*\*" docs/ROADMAP.md | grep -v "\*\* ✅"`
> **推進規則：** Verdict 為 `GO` 且沒有待使用者決定的問題時直接接續，Step 與 Phase 邊界一視同仁；六條停止條件住 `AGENTS.md`「協作與邊界」。
> **執行者是便宜模型時 Z1 以上預設 R1**（development-flow）。

| Phase | 做什麼 | 為什麼 | 驗收（數的是哪一層的東西） | 前置 |
|---|---|---|---|---|
| **0–6** ✅（2026-09-23 → 10-04 逐 Phase 結案：0 拆 09-23、1 等待與心跳 09-25、2 讀圖兩種單位＋走圖 09-26、3 候選狀態＋三題 09-30、4 層中心來源 10-02、5 量測 10-02、6 證據判準 10-04；plan、closeout 與 R2 verdict 的對照表住 [`plans/README.md`](plans/README.md)；四欄原列（含各 Phase 的 amendment 與結案數字）逐字封存於 [`archive/roadmap-phase-delivery-log.md`](archive/roadmap-phase-delivery-log.md) 2026-11-01 節） | North Star 圖上標了 Phase 號的那幾段：來源選擇（4）、走圖（2）、讀圖（2）、反證鑄 watch（1）、敘事與候選狀態（3）、三題（3）、量測（5）、證據判準（6）——都已交付，現行形狀住 ARCHITECTURE | 拆掉舊管線在圖與人之間的十層，圖到人之間才沒有分數；之後每一 Phase 各接一段 | 已結案；仍會自己出現的回查住心跳常駐計數器（Phase 5 ②圖預測表第一筆對／錯——段 4「圖預測」行；Phase 1 ④到期的 watch 不消失——短版狀態塊「watch 今日醒／到期／標旗」每天印） | — |
| **7 研究使用與量測（持續型）** ▶（2026-10-04 開；第一期到 2026-12-22 檢查點，之後每季一個檢查點，Phase 本身不「結案」；plan [`2026-10-04-001`](plans/2026-10-04-001-research-phase7-research-edge-plan.md)；使用者 2026-10-04 定案 Q1–Q8、A1–A4，amendment A1（本列）／A2（AGENTS 一句）五欄見 plan §0.4；能力盤點與設計 [`brainstorms/2026-10-04-phase7-research-edge-proposal.md`](brainstorms/2026-10-04-phase7-research-edge-proposal.md)） | **研究、量測、開發不設比例（2026-10-07 使用者定案，plan A5；原「研究約 75%、量測約 15%、開發 ≤10%」）：擋住研究的開發排在研究前，過 gate 的開發項隨時提；系統主動提出的仍要指得出真實案例與重複次數。** **7.0 開場**：預先登記（十個 edge 假說與殺死條件、14 個 case 與類型、裁決規則、failure log、開發 gate、漏網稽核母體）＋T0 凍結（手動 manifest）；開發 gate 落地＋兩個當下修（巢狀 writer lock、thesis 逾期提醒量錯）；敘事範本「要翻倍需要什麼」（營業數字，不寫目標價）＋市值與近四季營收兩個 placeholder＋「已定價」白話＋重押讀圖換格層引用；敘事「加碼條件」`confirm[]`（寫下即登記 watch、觸及只提醒、不是買進訊號）；個股頁首屏照五題排列＋候選板與個股頁標「和持股共用需求錨」；**外部雷達**：daily 加一步只開 WebSearch 的 `claude -p`，網址必須出自同一次搜尋結果、每日約 5 則、寫成 tier-4 secondary lead、不喚醒語意 watch、不另發通知（它不是 last30days：有 provenance 契約），**八週試驗：2026-10-05 上線、第 56 天是 11-29；原停止條件照舊——「triaged_go 且追到一手或入圖、而且沒有別的管道更早登記」全期為 0 就退役；11-30 出「第 56 天報告」（逐筆 lead id、按儀器版本分段計數、沒跑的天照印），非 0 時續不續由使用者在 12-22 檢查點決定（2026-10-21 A10）**。**7.1／7.4 兩波研究**（光通訊跟 Q3 財報；電力與散熱兩條新鏈、該鏈的主題等權組在第一份敘事前前瞻定義；SNS 40 則 claim 裁決；二階瓶頸三個 case；800VDC 擱置五則回看）；**7.2 回放**（已定價、漏網稽核是機械的；parked 回查、輸家驗屍是研究）；**7.3** Q3 財報季裁決與 2×2；**7.5 檢查點**（決定紀錄 §10＋假說證據帳＋failure log 依重複次數排序＋雷達停止條件＋T1 manifest＋R2） | 機制遠超過使用（讀圖 4、敘事 4、可開每天 0、外部來源 1 個、測試 3,448）；edge 有沒有、從哪裡來，報酬量測要到 2027 才成熟，只能靠預先登記的案例、前瞻凍結與快迴路逐步淘汰假說；AXTI 顯示判斷層可能把我們從贏家身上說服走（n＝1）；LLM 研究者的知識截止（2026-06）讓之前的判讀回放不可信 | ①光通訊以外 ≥2 條鏈各有現行讀圖、每份 ≥1 條登記反證（讀圖、registry）；②新敘事每份有候選狀態、押的讀圖（短檢查判不坐任何層／開發中／在需求側等，寫明理由、不另立 rides）與翻倍條件（判「不要」的寫出「為什麼翻不了倍」就算數——2026-10-21 使用者照推薦）；持有或可開、且狀態不是「不要」的，另有加碼條件；持有但判「不要」的非倍率持股，加碼與反證住它的 thesis（敘事；thesis 的反證數等待 registry；2026-10-21 A9）；③預先登記的 commit 早於 wave 1 任何新讀圖／敘事，T0 manifest 與當日心跳一致（讀圖、敘事、registry）；④S1 的 40 則 claim 各有裁決或到期（registry）；⑤Q3 財報季（2026-10-21～11-30）：裁決點落在窗內的現行敘事（持股＋缺 X＋等回落；名單在 2026-10-21 凍結並寫進 case 段），每份都有財報後新版或不換版理由；非倍率公司（含 LITE、COHR 的層面）的財報只當層的證據，寫進讀圖換版或 case 段；窗內到期與已觸發的 watch 全部處置（敘事、讀圖、registry）；⑥每個開了的 case 有產出 id 與裁決，2×2 各列（追蹤表）；⑦雷達上線、第一輪收據、11-30「第 56 天報告」（分版計數、逐筆 lead id）與八週停止條件有結論（registry）；⑧檢查點：H1–H10 每個有證據列與 n（追蹤表）；另：開發 Step 各自的測試與變異（機制），進 ROADMAP 的開發項每一項指得出 ≥2 個 case | 6 |
| **8 個股故事頁（消費端：問題清單、偵探分工、進 APP）** ✅ 2026-11-27（plan [`2026-11-26-001`](plans/2026-11-26-001-feat-phase8-story-page-app-plan.md)；結案報告 [`reports/2026-11-27-phase8-closeout.md`](reports/2026-11-27-phase8-closeout.md)——要使用者決定的五題 11-27 已答（§5）：舊頁先留、股價圖維持寫的時候畫、換版時條件沒改字的等待沿用原編號（當天做完）、撤回卡住先不改、下一檔做深 COHR；決定紀錄 [`brainstorms/2026-11-25-story-question-list-goal.md`](brainstorms/2026-11-25-story-question-list-goal.md)；原列逐字封存於 [`archive/roadmap-phase-delivery-log.md`](archive/roadmap-phase-delivery-log.md) 2026-11-27 節） | 每檔一頁從頭讀得懂的故事，一次寫到九成：問題清單住 skill [`stock-story`](../skills/stock-story/SKILL.md)（成績單＝[漏題帳](reports/phase8/story-question-log.md)），蒐證與落帳住 skill [`detective`](../skills/detective/SKILL.md)，一句「做深 <代號>」串起兩段；APP 個股頁先故事、後系統（ARCHITECTURE §6.12） | 使用者 2026-11-25：「希望起點能更接近我們的終點，例如下一隻深度偵探的股票，能一發到9成」 | 進展只數：**敘事**——因為做深而換版的檔數；**等待 registry**——故事頁「再一次要什麼」「夢醒」登記的 watch 條數 | 已結案；照帶小項見〈已交付列留下的遺留小項〉 |

**每個 Phase 開工前要有 plan；沒有就停。** Phase 與 plan 檔的對照、以及「開 plan session」要貼的指令住 [`plans/README.md`](plans/README.md)。

### 研究並行（不是 Phase）

**2026-10-04 起研究本身就是 Phase 7**（持續型；預先登記、凍結、檢查點），研究項仍走 pq1／pq2、不占本表。

### 旁支開發項（不是 Phase；不插進執行中的 Phase，排在 Phase 之間或使用者點名時做）

| 項目 | 做什麼 | 為什麼 | 驗收（機制存在與否） | 前置 |
|---|---|---|---|---|
| **海外財報來源** ◐（①台股 ✅ 2026-10-05、②20-F ✅ 2026-11-03、③日本 EDINET ✅／④韓國 OpenDART ✅ 2026-10-21，**剩中港、歐洲、加澳未驗證**；2026-09-30 使用者「之後再加、要排程」，2026-10-04 使用者「研究過程用到就一起做」——研究撞到哪個市場的缺口就做那一格，照 development-flow 一格一驗收，範圍大或有要使用者選的就停下問；Phase 3 closeout §5 #14；盤點 `docs/reports/2026-09-30-overseas-data-sources.md`；①的 plan `plans/2026-10-05-001-feat-tw-historical-shares-proposal.md`、③④的 plan `plans/2026-10-21-002-feat-jp-kr-filings-plan.md`（查證命令見該 plan「現況」那一行；OpenDART 個資 2 年重新同意掛 [835] pending 到 2028-09-21）；①③④ 的交付敘述逐字封存於 archive/roadmap-backlog-log.md 2026-11-01 節） | **剩中港、歐洲、加澳**（未驗證來源）。已做：①台股歷史股數（MOPS t163sb05；12 檔台股 12/12 有值）、②20-F 年度封面股數（ARBE、HIMX、POET 3/3；掛牌單位比率住名冊 `ordinary_per_listed_unit`，幣別不換照舊）、③日本 EDINET 13/13、④韓國 OpenDART 6/6 寫入 `fundamental_history` | 邊緣候選 22 檔裡 18 檔是海外或 20-F，已定價的主參照（自家三年百分位）全部缺；非台股海外 13 檔的「出現在數字裡」也缺（2026-09-30 盤點時的數；台日韓補完後只剩 20-F 與未驗證市場） | 每補一個市場：該市場邊緣檔的自家百分位從缺席變有值的檔數（個股頁稽核區）；可知日用申報日，不用抓取日（INV-6） | ②不用申請 key；中港、歐洲、加澳先驗來源 |
| **IR／E-IR 一手 feed** ⏸（failure log #147；使用者 2026-11-10「J 排到 12-22」；plan `2026-11-10-001` J） | 有現行敘事的公司，IR 新聞頁或 E-IR 登記成 harvest 一手 feed（逐家、只連那一台主機、UA 不帶信箱；新增對外主機要在同一個 change 做 sandbox impact review） | 只在 IR 網站的一手沒有 producer、watch 叫不醒（INV-4）：EROC 10-07 HD 長缸供貨新聞稿（沒交 8-K）、日東紡 3110.T 11-05 質疑應答（E-IR、不在 TDnet；`ew_0420` 沒醒）、雲南鍺業 002428 11-10 投資者關係活動記錄表（巨潮 `relation` 那一區，harvest 沒接；11-11 drain 才讀到）、三井金属 5706.T 10-30 官網新聞稿（MicroThin 產能提前，`ew_2307` 沒醒；failure log #157），4 次 | 12-22 先量：failure log #32 缺 X 回掃那 17 檔裡沒抓進來的 15 檔，漏掉的一手有幾則**只在 IR 頁上**（交易所、EDGAR、MOPS 都沒有）——數字交使用者選做不做；做的話重放 10-07、11-05 各出一筆 lead、叫醒 `ew_0420` | 2026-12-22 檢查點（plan `2026-11-02-001` §5「12-22 前不開新 feed」） |
| **停放未處置對照的計算量**（failure log #155；維運、不算進展） | `engine_b.impact.undisposed` 的名字比對：一次對照裡每家公司的可比寫法只算一次（依公司快取 `usable_name_forms`；比對規則仍只由 `query.bottleneck.quote_names_company` 擁有）；組心跳的測試改讀暫存 lead 池、不算真資料 | 2 次：11-03 daily ⑱ 12 天從 22 秒漲到 100 秒（上限 3 分鐘；當時修成一次心跳只算一次）；11-11 全套測試卡在組心跳的測試——真資料一次 `build_queue` 92.5 秒（728 則停放 lead、名字比對 140 萬次，寫法重算 28 秒、regex 50 秒），一支測試呼叫三次，全套改拆兩條平行才跑得完 | 同一份 lead 池改前改後「停放未處置對照」輸出逐列相同；真資料一次 `build_queue` 的秒數（基準 92.5）；組心跳的測試不再讀 `library/leads` | 無 |
| **產業序列的叫醒：經濟部玻纖布月資料** ○（未排程；2026-11-14 富喬試點，研究日誌三十七） | 經濟部工業產品群統計調查（`service.moea.gov.tw/EE520`，ASP.NET 表單）每月抓「玻璃纖維梭織布」那一列（產量、銷量、銷售值、存貨），算每公斤單價年增與存貨月數；敘事寫成這條序列的翻倍條件，登記成有 producer 的 watch——新的一期上架就檢、條件成立就醒。只做玻纖布；別的產品等有敘事真的寫了再加（L17：general 到資料支持的那一格） | 富喬 1815.TWO `ib_3ceb0197ab61b53a`（11-14）把假設寫成這條序列的數字（每公斤單價年增維持正、存貨月數留在 1 以下；2010 年那一輪是存貨先回升、兩個月後價格見頂），卻**不能登記成反證**：沒有程式每月去抓，登記了不會自己醒（INV-4）——現在是一段要人記得的文字（L14）。同層台玻 1802.TW 的翻倍條件同一條序列；使用者 11-14 兩次問「這個量我們能從哪裡看著更精準」。次數：1 檔已寫、1 檔同層待寫 | 等待 registry 裡有 producer 的序列 watch 由 0 筆變成 ≥1 筆（1815 的序列反證）；新的一期上架後，那筆 watch 的檢查紀錄前進一次（查證：`python -m engine_b.event_watch counters` 與該 watch 的檢查欄） | 新增對外主機要在同一個 change 做 sandbox impact review；欄位與查詢參數見研究日誌三十七 |
| **敘事事實句綁逐字錨點** ◐（failure log #163；使用者 2026-11-13「記進開發 ROADMAP」；Z2，三題同日「照你推薦做吧」已選、plan [`2026-11-13-001`](plans/2026-11-13-001-dev-fact-anchor-plan.md)：A 紀錄與比對 ✅ 2026-11-13（⑤ 落地 39 版、事實句 2,719）、A2 收自家紀錄 ✅ 2026-11-13（使用者「自家句 A」）、B 回填 ◐（COHR 32/32，⑤ 38 版；排進每次 drain）、C 重放 ○） | 敘事與故事裡講事實的句子，寫的時候各帶一段**逐字原文**（引用檔名＋那一段原文的字，像讀圖 citation 的 quote）；工具只拿句子比它自己那一段——數字、名稱、引號、日期、限定詞與保留語氣（原文寫 expected／may／預計，句子寫成已發生）；同一個事實只寫一處、別格引用它；衍生數字（比例、成長率）由工具從錨點的數字算，不手寫；**先只印、不擋寫入、不改候選狀態**（和現行逐句核對同一個位置） | 現行逐句核對是在整份引用裡猜「哪一行對得上」，猜錯就核錯。11-13 回頭核 27 份現行敘事：**27 份都有錯**，2,857 句改 207 句；工具重放（敘事 2,023 句）只標到改掉的 135 句裡的 56%，沒改的 1,888 句也標 27%（命中率約 13%）；事實抽樣① 11 份 8 份有錯（#163）。查不準的兩種錯各有 ≥ 2 個 case：主詞收窄或放寬（3110.T 特種電子布、LPK.DE「主要半導體廠多數」、ATS「NVIDIA 專用」）；衍生數字與保留語氣（AXTI「三分之二」——原文第二季約 79%、第三季約 87%；「committed to pay」寫成「付了」）——保留語氣三種寫法量過都只比亂猜好約 1.4 倍（`alpha/narrative/fact_check.py` 註記） | 同一組句子重放（11-13 回頭核那 27 份）：改掉的 135 句被錨點比對標到的比例（基準 56%）、沒改的 1,888 句被標的比例（基準 27%）；現行敘事的事實句有錨點的比例；可開與已持有每份都有帶錨點的一版（敘事） | ~~使用者選三題後出 plan~~ 已選（2026-11-13「照你推薦做吧」）：①另一份 append-only 紀錄、用句子指紋（不含引用）對回去，敘事格式不升版；②宣告可開（含前提失效）與已持有先補，其餘換版時才補；③比對不過只印、不擋寫入、不改候選狀態——量過（plan Step C）再談 |
| **偵探：計畫外線索組裝** ◐（使用者 2026-11-18「都做吧 做出一版我們再繼續精進」；M0 ✅、第一版 ✅ 同日；精進照案例庫） | 機械組線索包（`python -m alpha detective pack <代號>`：圖上一跳鄰居、同層供應商與買方、同層對手的客戶〔第二跳，每家只留最新 12 份〕；點名它們的自家庫文件、共識軌跡、由鄰居角色產生的問句；`--as-of` 回溯包排除日期不明與晚於回溯日、清掉我們後來寫的字，每一步數出來）→ 強模型唯讀子代理照 `PROMPT.md` 回報 → `python -m alpha detective verify` 核引文（含清單外）→ 主 session 寫進敘事量級段、每條登 watch → 案例庫 `skills/detective/cases.md` | 1 次：AXTI M0（2026-11-18）——共識 FY2027 約等於照計畫、單價不變的路徑；計畫外的漲價只有把兩份不同當事人的文件放在一起才看得到（AOI 10-Q 的金額＋雲南鍺業公告的片數 → 2027 年 4 吋每片約 1,080 美元），手組線索包花掉一整段 session | 第一版：①AXTI 回溯包（2026-09-07）對 M0 手組 58 份覆蓋 56、現況包對手組 137 份覆蓋 131，漏的類別印得出（圖上沒邊、第二跳每家上限）；②M0 的 31 條引文用 `verify` 重核 31／31 逐字且行號對、清單外 0；③AXTI 敘事 `ib_5018383c73cf77ed` 量級②③多了偵探線索，登 `ew_3562`（反證 #9）、`ew_3566`（加碼條件）。精進：案例庫「結果」欄每季數中／錯／未決（只數 watch 判定，不數跑了幾次、找到幾條） | M0 ✅；AGENTS 子代理常規 opt-in ② ✅ |
| **賭注句與今天的一頁** ▶（使用者 2026-11-22 簽核設計稿 [`brainstorms/2026-11-21-playbook-replay-design-v3.md`](brainstorms/2026-11-21-playbook-replay-design-v3.md) §4–§5；A0 賭注句與對帳日曆 ▶ 使用者 2026-11-22 定 1b／2B／3b（[`brainstorms/2026-11-22-a0-bet-line-proposal.md`](brainstorms/2026-11-22-a0-bet-line-proposal.md)），S1 寫入規則 ✅、S2 導出與計數 ✅、S3 畫面 ✅（2026-11-22 驗收當天：賭注句還沒寫 19、翻倍條件還沒寫成數字 0、沒有對帳日 0、90 天內日曆 13 列——現況讀短版 ⑤ 那三格；機制見 ARCHITECTURE §6.11）、S4 實際寫 ◐（先寫 3 檔給使用者看：6727.TWO、AEHR、COHR；其餘等使用者放行，剩幾檔讀短版 ⑤「賭注句還沒寫」，11-27 daily 是 16）；A1 機械回放 H16 ✅ 2026-11-22 判讀落帳——M1、M2、M3 都不確定，表 A 已交（[`reports/phase7/replay-h16-results.md`](reports/phase7/replay-h16-results.md)）；表 B ✅ 第一版 2026-11-23（私有、在對話裡交；M 標記今天的值沒算；要常看才做成 APP 頁）） | 每檔可開一句四格的賭注句（故事紀錄的選填鍵：押什麼｜翻倍要哪個營業數字｜下一個對帳日｜認錯看哪條反證）；未來 90 天的對帳日曆；表 A 大跌後的基準率；表 B 可開所騎的層今天的列 | 使用者 2026-11-20 原話「難把敘事組成一個我們在賭的東西」「沒辦法從三四十檔挑出幾個」；可開 17 檔都有敘事、「看了沒買」的紀錄 0 筆（案例 1 次，使用者指示） | 敘事：可開裡有賭注句的檔數、第 2 格是數字的檔數、缺對帳日的檔數；追蹤表：H16 每個確認型標記一條判讀。表 A、表 B 是機制 | 設計稿第三版簽核（✅ 2026-11-22） |

### 已交付的旁支（索引；原列逐字封存於 [`archive/roadmap-backlog-log.md`](archive/roadmap-backlog-log.md) 2026-11-01 起各節，含每項的驗收數字與查證命令）

> 日期＝交付日。這裡只留落點，讓程式註解裡的 `ROADMAP「標題」` 找得到；要看做了什麼、數字怎麼變，讀封存列。

- 2026-11-28 **刪舊版個股頁（`#/old/`，頁首＋十三塊）**（使用者「2 go」，沒有 ROADMAP 列、這一行就是紀錄）——`briefCard` 與只有它用的八個函式拿掉；需求錨與「吃到多少」兩張圖搬進「系統裡的它」的數字與出處（`systemNumbers`）；存著的舊連結轉到新版；機制見 ARCHITECTURE §6.12；`tests/test_webapp_api.py -k story_page_only`
- 2026-11-28 **故事頁的「系統裡的它」瘦身、排成故事的一節**（使用者指示「瘦身」「原本 old 還存在的那一段，就融合進去現在新的敘事頁面」，沒有 ROADMAP 列、這一行就是紀錄）——有故事頁的檔走 `storySystemBlock`（只留帳上會自己變的；故事講過的不重印）、沒有故事頁的照舊 `systemBlock`；機制見 ARCHITECTURE §6.12；`tests/test_story_hero.py -k slim`
- 2026-11-27 **淺寫頁首：還沒做深的檔先有一段頁首**（使用者指示「走2」，沒有 ROADMAP 列、這一行就是紀錄）——故事紀錄選填鍵 `hero`（`alpha/narrative/story.py::hero_problems`）、⑤「頁首還沒寫」（`todo.hero`，交付當天 18 檔）；新個股頁「系統裡的它」加回會不會死一行（`lampLine`）；機制見 ARCHITECTURE §6.11、§6.12；`tests/test_story_hero.py`
- 2026-11-19 **故事已定價段的股價脈絡帶截至日**——寫入端拒收沒有截至日的股價走勢句（`alpha.narrative.contracts.undated_price_move_claims`）；`tests/test_stories.py -k price_move`
- 2026-11-19 **偵探回溯：起漲點前看**——結論：停在校準用途（清淨組配對分辨 2／6，看不出）、遮名組 11-19 關閉；偵探提示出處格式鎖字（`tests/test_detective.py`）；plan `2026-11-18-001`；2027-05-31 重算見〈已交付列留下的遺留小項〉
- 2026-11-19 **閉環母體讀「買得到嗎」**——閉環母體封閉字彙加 `not_buyable`（`alpha/closure.py::POPULATIONS`）、候選板沒有敘事的列附 `access`；`tests/test_closure_population.py`
- 2026-11-19 **短版每週一印一行紙上籃子**——短版 ④ 每週一一行（`crons/heartbeat.py::paper_basket_line`）；`tests/test_paper_basket_line.py`
- 2026-11-18 **量級獨立一格**——敘事 v2 選填第八格 `magnitude`（`alpha/narrative/contracts.py::OPTIONAL_SLOT_KEYS_V2`）
- 2026-11-12 **敘事寫入前逐句核對**——`python -m alpha brief-check`（`alpha/narrative/fact_check.py`）、⑤「敘事還沒逐句核對」；`tests/test_fact_check.py`
- 2026-11-10 **敘事寫入收據列出上一版之後進池、這一版沒指到的一手**——`alpha/providers/unread_primary.py`；`tests/test_unread_primary.py`
- 2026-11-10 **台股重訊回補：每日補抓前幾天、新進範圍回補 90 天**——`crons/harvest_leads.py::harvest_mops_history`；sandbox impact review 在 OPERATIONS「台股重訊回補」；`tests/test_mops_history_backfill.py`
- 2026-11-10 **私有券商報告建索引、讀某檔時列出點名它的報告**——`python -m sourcing.private_docs`；`tests/test_private_docs.py`
- 2026-11-10 **研究讀燈與讀敘事全文的出口遮價格欄**——`python -m alpha lights`、`alpha/price_mask.py`；`tests/test_price_mask.py`
- 2026-11-10 **讀圖反證寫「新進」卻漏列 develops 的公司就在收據點名**——`alpha/structure_reading/entrants.py`；`tests/test_reading_entrants.py`
- 2026-11-10 **何時格的裁決點已過就叫重寫**——`alpha/narrative/checkpoints.py`；`tests/test_narrative_checkpoints.py`
- 2026-11-10 **錯的訊號逐條對反證**——`alpha.narrative.contracts.wrong_signal_items`；`tests/test_wrong_signal_refs.py`
- 2026-11-10 **負債燈只算借款、租賃另列**——Engine C 快照 `lease_liabilities`；`tests/test_wipeout_debt_leases.py`
- 2026-11-08 **首頁最上面一行「大盤同期」**——QQQ、SOXX、IWM、0050 最近 30 個交易日；`tests/test_webapp_home_benchmarks.py`
- 2026-11-04 **人工核准的屬性決議走到讀圖**——`query.bottleneck.collapse_assertions` 套 `library/resolutions/` 的核准決議；`tests/test_resolution_reaches_readings.py`
- 2026-11-04 **看了沒買與兩道門的 R2 條件修正**——`tests/test_looked_log.py`、`tests/test_open_two_gates.py`、`tests/test_stock_page_phase3.py`
- 2026-11-03 **逾期型反證**——敘事 `disproof[].deadline`；`tests/test_deadline_disproof.py`
- 2026-11-03 **可開分起始與加碼兩道門**——起始門四項決定可開、讀到邊與深挖清單改當加碼條件、已定價等回落併回可開；`tests/test_open_two_gates.py`
- 2026-11-03 **候選板標出只差已定價**（⚠ 同日隨等回落退役）——`tests/test_priced_only.py`
- 2026-11-03 **個股頁 schema**——`briefing/analyst_view/page_schema.py`、層說明 ledger（`python -m alpha layer-note`）、回饋紀錄 `docs/feedback/stock-page.jsonl`
- 2026-11-03 **敘事 stale 計數器**——`alpha.candidates.body_behind_readings`；`tests/test_narrative_stale_24.py`
- 2026-11-03 **海外財報來源 ②20-F**——名冊 `ordinary_per_listed_unit`；`tests/test_three_questions.py`
- 2026-11-03 **成交紀錄遺留八項**——`record_trade.py`；`tests/test_record_trade_leftovers.py`
- 2026-11-01 **等回落的重開條件**（⚠ 2026-11-03 隨等回落退役）——`tests/test_reopen.py`
- 2026-11-01 **alpha 格只觀測**——`config/target_allocation.json` 的 alpha 格 `observed_only`；`tests/test_alpha_observed_only.py`
- 2026-11-01 **週額度常駐計數器**——`crons/llm_step.py::_rate_limit`、短版 ④ 一行、`python -m crons.llm_quota`（只印不擋，門檻量到 2026-12-01 再定）；`tests/test_llm_quota.py`
- 2026-11-01 **邊緣門檻的遲滯與在門檻上計數器**——`alpha/providers/edge.py::attach_prior_judgments`；`tests/test_edge_hysteresis.py`
- 2026-10-31 **只改字面值的換版不重設判斷日**——敘事 v2 選填 `restates`，判斷日與正文版沿用被重述那一版；`tests/test_brief_restates.py`
- 2026-10-31 **首屏敘事不寫死燈色與價格報酬**——寫入端拒收「燈名＋顏色」、已定價那一格寫收盤價只印 ⚠；`tests/test_narrative_literals.py`
- 2026-10-31 **宣告可開前的深挖清單**（2026-11-03 起是加碼條件、不擋可開，見「可開分起始與加碼兩道門」）——`alpha/narrative/depth_check.py` 十個鍵，宣告可開時逐項印缺哪幾項（只印不擋）
- 2026-10-30 **等回落的價格叫醒**（⚠ 2026-11-03 隨等回落退役，見「可開分起始與加碼兩道門」）——候選板每天算 `pulled_back`、狀態塊「等回落 N（已回落 M）」；`tests/test_priced_since.py`
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
- **偵探回溯清淨組的完整窗口**——2027-05-31 重算對照、補 6／12 個月超額（`python -m alpha detective score --group clean`；plan `2026-11-18-001`）；到期是重看，不是丟。
- **故事頁照帶小項**（Phase 8 結案報告 §5 #5、§7）——敘事撤回又不再寫新版時，故事頁卡在「該對版」（使用者 11-27「先不改」，第一次真的撞到再選）；R2 不阻擋 N1、N2、N4 與窄範圍覆核兩條。今天都是 0 個真實案例。

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
