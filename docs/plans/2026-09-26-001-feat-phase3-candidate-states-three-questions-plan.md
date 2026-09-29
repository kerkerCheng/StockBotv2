---
date: 2026-09-26
revised: 2026-09-29（P0 review 後改寫；使用者追加定案 13–16）
topic: phase3-candidate-states-three-questions
status: active
derived_from: docs/ROADMAP.md（Phase 3，含本 plan §0.4 的 amendment A1–A7）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G3、G6、G8、G9、G12；§4.2、§6）、docs/reports/2026-09-26-phase2-closeout.md §5、docs/reports/2026-09-25-phase1-closeout.md §7、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md（`config/alpha_screen.json` 留給 Phase 3）
plan_review: P0 已做（2026-09-28，使用者問「需要 R2 嗎」後以 workflow 跑：8 面向唯讀審查→每個 finding 獨立反方驗證；95 個 finding，成立 57、推翻 7、31 個因額度未驗——其中獨有的由 plan 作者自己查證，成立 4）；完整性補查（2026-09-29，改寫後 c427d0c，3 視角：37 個 finding，成立 22、推翻 4、11 個因額度未驗——作者自查）。全部處置見 §0.7
---

# Phase 3 候選狀態 ＋ 財務三題（給執行模型的完整 plan）

> **執行者：跑 `/phase-run` 的模型，走 `skills/development-flow/SKILL.md`（Z1 以上預設 R1）。**
> 使用者 2026-09-26 表示本 Phase 用強模型接著跑；Step 3.5 是研究步驟（寫敘事），**執行者是強模型時不停、直接做**；
> 若換成便宜模型執行，輪到 3.5 時停下來請使用者切強模型（見 §6）。
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 3」（含本 plan §0.4 的 amendment A1–A7）導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文（尤其「消費契約」「資本與風控」）→ ROADMAP「Phase 3」「消費層對照表」「硬約束」→ 本 plan §0.1–§0.4、§0.7 →
> 決定紀錄 §4（三題的正解）與 §6（已知問題）→ `docs/refactor/historical-failure-matrix.md` §2 六條 invariant →
> `docs/OPERATIONS.md`「sandbox impact review 五步」→ `alpha/narrative/contracts.py` 檔頭（短評三條規則）→ `alpha/wipeout.py` 檔頭 →
> `engine_b/entities.py` 檔頭（lead 關聯寬鬆、資本歸屬嚴格）→ `config/alpha_screen.json` 的 `_doc`／`_absence_policy`。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字是**敘事 ledger 的紀錄與欄位、watch registry 的連結、
> 個股頁稽核區三題每檔的值或缺席、成交事件的研究收據、APP 的 state kind、機制存在與否**（見 §11）。
> ⚠ 「可開」的檔數**不是驗收數字**——可開為零就零（ROADMAP 硬約束 7）；它只在心跳與候選板上被印出來。

**一句話目標：** 每一份個股敘事的最後一行，都答得出「為什麼還沒買／為什麼可以開」，而且那個答案指得回一筆在等的 watch 或一句理由；
財務只回答三個是非題——會死嗎、已定價嗎、出現在數字裡了嗎——每題都印得出數字與資料源，印不出就說為什麼。
**程式不替人下結論：** 「可開」由寫的人宣告、程式只驗前提；三題中兩題的答案由寫的人宣告、程式只印數字並強制引用。
它服務 `AGENTS.md` 的「產出若無法讓人分辨做了什麼與沒做，它就不算產出」與 G6「沒有排序後的對稱風險是永遠不收斂」。

---

## 0.1 使用者定案（本 plan 的判斷全部來自這張表）

**2026-09-26（12 題，使用者：「大致都可以」＝全採建議選項）：**

| # | 題目 | 定案 |
|---|---|---|
| 1 | 敘事長什麼樣 | **A**：同一本短評 ledger 升 **v2**。七格改題：拿掉已退役的估值 placeholder；「市場怎麼看」改「已定價嗎」（必引稽核區數字）；「對了／錯了」改「什麼必須為真、錯的訊號」。加結構化欄位 `rides[]`（節點＋單位＋讀圖 id）、`disproof[]`、三題答案、`candidate_state`。v1 照讀、標「舊版、缺候選狀態」 |
| 2 | 「可開」誰判 | **A**：寫的人宣告，程式驗前提——騎的讀圖現行且結論是護城河或量、三題都有答案或宣告無法量、沒有待處置的反證；前提事後破掉時候選板印「可開（前提失效：…）」、ledger 不改寫。**「已持有」一律由 Sheet 推導**，寫的人不能宣告 |
| 3 | 已定價嗎的三年歷史 | **A**：一次機械回填——價格 3 年；營收歷史美股 EDGAR、台股月營收；有歷史淨負債的算 EV/S，沒有的算 P/S 並標口徑；其他市場印「無法量：歷史不可得」 |
| 4 | 主題籃子 | **A**：**定義移到 Phase 3**（append-only，每次變動附理由與日期；Phase 5 沿用）；第一版成分在研究步驟提出、使用者定（pq2） |
| 5 | 三題的答案誰給 | **A**：會死嗎＝四盞燈（機械）；已定價嗎、出現在數字裡了嗎＝程式只印數字＋資料源＋最新一期日期，答案由寫的人宣告、型別層強制引用那幾格 |
| 6 | 稀釋與 going concern | **A**：稀釋——回填同口徑股數一年以上（美股 EDGAR 封面股數）；going concern——新增結構化欄位（有／無／未查），互動 session 讀審計意見後寫，屬判讀，走 Engine C 判讀寫入 gate（pq2）。**非美股的處置由 #14 細化** |
| 7 | 成交收據範圍 | **A**：alpha 買進缺敘事 → fail closed，附理由的 override 放行並記「無敘事」；alpha 賣出要輕收據（一句理由＋觸發的反證 watch id，若有）；beta 不需收據。**旗標形狀由 P0 review 細化**（§0.4 A4：與 5% 硬擋的 `--override` 分開） |
| 8 | thesis 引用的 39 條 claim 反證（Phase 1 #1） | **A**：只自動登記新敘事 `disproof[]` 寫下的；39 條裡被新敘事引用到的，在研究步驟搬進去（G8「只登記被引用的」） |
| 9 | 強模型研究步驟 | **A**：排進 plan（Step 3.5）：用 v2 重寫 AXTI、COHR、LITE，寫 Sivers 第一份，每份宣告候選狀態；主題等權組第一版成分在這一步提 pq2。**使用者補充：本 Phase 用強模型執行，3.5 不必停下換模型** |
| 10 | 個股頁面板重排殘留（Phase 2 #8、#9、#12） | **A**：一起做——argument「鏈」段不再用 sub≥4 成員的需求錨、改印騎的讀圖；`review_required` 的路接回讀圖面板；argument 標題改 |
| 11 | Phase 2 帶過來的小修 | **a＋b＋c**：a `graph_holes` 段計數改「有命中的型別數」、刪重複加總、心跳與稽核共用一份；b cashtag 無後綴解析（registry 唯一才解析，歧義列出不猜）；c `coverage_gaps`／`duplicate_nodes` 兩支 CLI 退役＋清磁碟孤兒 artifact。d（稽核依賴 Neo4j）**維持不動** |
| 12 | R2 | **A**：執行期間六條 trigger 命中就**常規 opt-in**（直接發 `WORK_REQUEST`，NO_GO 才停） |

**2026-09-29（P0 review 與完整性補查後追加 5 題，全採建議選項）：**

| # | 題目 | 定案 |
|---|---|---|
| 13 | 覆蓋厚薄門檻（`config/alpha_screen.json`，ROADMAP／Phase 0 plan 明寫留給 Phase 3 當「邊緣」定義）怎麼進候選板 | **非邊緣不能是可開**：候選板逐列印「邊緣／非邊緣／邊緣無法量」；非邊緣的檔在顯示端進「非倍率候選」組；缺市值或覆蓋的另列「邊緣無法量」組（不靜默放行、不靜默濾掉，`_absence_policy`）；敘事照寫、ledger 不改 |
| 14 | 稀釋燈的非美股 | **逐檔單一來源**：美國國內申報人用 EDGAR 封面股數（回填一年以上）；其餘續用 yfinance 快照序列並標口徑，窗滿一年自己判色（保留既有 `colour_available_on` 那個有到期的等待）；兩個來源不混 |
| 15 | 回填之後歷史表怎麼長 | **daily 加一個零 LLM 的機械增量步驟**（最新收盤、EDGAR 新申報、封面股數）；sandbox impact review；最後一點太舊時印 `days_since_last` 並回缺席 |
| 16 | Step 3.8（資本路徑，AGENTS 停止條件③） | **預先授權**：內容已由 7A 決定、只加收緊；R2-b 回 GO 就照常 commit、push、接續；NO_GO 仍停 |
| 17 | 3.6 要把 `risk/hard_caps.py` 私有的 alpha／beta 判別改成公開（候選板排除 beta 要用） | **授權擴到這個純重構**：只匯出、硬擋行為一個字都不改、既有硬擋測試全綠才算數，3.8 的 R2-b 一併審；其他任何資本路徑改動仍停（2026-09-29） |

## 0.2 現況實測（2026-09-26 起、P0 review 2026-09-28 補；**現況數字會腐壞，引用前重跑查證命令**）

| 事實 | 數字 | 查證 |
|---|---|---|
| 短評 ledger | **3 檔**（AXTI 2 行、COHR 2 行、LITE 3 行），全是 `investor-brief/v1` | `ls library/private/alpha/briefs/`；每檔 `wc -l` |
| 短評裡的退役估值 placeholder | 三份現行短評的 `if_right_if_wrong` 都寫了 `{bet_target}`／`{payoff}`（COHR、LITE 另有 `{base_target}`），Phase 0 後填出來是「（尚無）」；`market_view` 用 `{sell_side_target}`／`{market_multiple}`／`{analyst_count}`；**`our_bet` 用 `{bet_assumption:driver[scope]}`**（variant overlay，已退役） | 讀三檔最後一行的 `slots` |
| `{assumption:…}` 的值來源 | 估值橋的生效假設，**已隨估值鏈退役**，builder 不再產生任何 assumption 值——恆印「（尚無）」 | `briefing/alpha_view/builder.py:302-305` |
| 殭屍 grep 對短評的 keep-list | `alpha/narrative/contracts.py`、`alpha/models/session_assessor.py`、`tests/test_investor_brief.py` 在 C 組（`sell_side_target`）以 legacy_key 留著 | `scripts/retired_mechanism_grep.py` 約 111–141 行 |
| thesis lifecycle | 3 筆：AXTI、COHR、SIVE.ST（Sivers 有 thesis 無短評；LITE 有短評無 thesis） | `python -c "import json;print(list(json.load(open('thesis/lifecycle.json',encoding='utf-8'))))"` |
| 現行讀圖（全部 v3，到期 2026-12-24） | `mat:inp_substrate` 層 volume——供給側 AXT、JX、住友；**COHR、LITE 在需求側**。`tech:cw_dfb_laser` 層 volume——供給側 **COHR、Landmark、LITE、LuxNet、Sivers、VPEC**。`prod:supernova`、`prod:els_8ch_module` 插槽 `undecided` | 各節點 ledger 最後一行的 `angles.supply_side`／`demand_side` |
| 個股頁 readiness | 73 份；絕大多數 `blocked`，最常見 blocker `brief=not_yet_recorded` | `python -m webapp status` |
| 核心／選配面板 | `CORE_PANELS=("headline","brief","argument","research","wipeout")`；`OPTIONAL_PANELS=("fundamental","bet","readings")` | `briefing/analyst_view/contracts.py:73,82` |
| `refresh=review_required` 的來源 | 今天全部來自 `operating_assumption`／axis／thesis（分析師目標均價變動、「calibrated relative to market consensus」的假設）——**已退役估值鏈的殘留，與讀圖無關** | `python -m webapp status` 的 refresh 欄＋各檔 refresh 明細 |
| argument「鏈」段 | 邊來自 `get_company_structural_context`；只經 `scarcity_inputs` 拿 `get_bottlenecks` 的 `demand_anchor`。`get_bottlenecks` 的 production 呼叫端：`alpha/context.py:134`（`build_research_context` Q1）、`audit/checks.py:1142`（**PointInTime 洩漏探針**） | `git grep -n get_bottlenecks -- '*.py'` |
| Engine C 後端 | **SQLite 是現行後端**；`engine_c/migrations/` 只給 Postgres；SQLite 建表住 `engine_c/db.py::_ensure_sqlite_schema`（`get_conn()` 每次開庫自動跑）；正式庫 WAL 模式；路徑由 `library/private/runtime_pointer.json` 決定 | 讀 `engine_c/db.py`、`engine_c/migrate.py` |
| Engine C 快照範圍 | `financial_snapshots` **2026-07-08 → 今天、73 檔**（每檔 21–62 列、中位數 54）；`ev_revenue` 72 檔有值；`price_kind` 757 列 NULL、48 列 intraday——**沒有任何一檔有三年歷史** | scratchpad 查詢 `SELECT ticker, count(*) … GROUP BY ticker` |
| 股數序列 | 73 檔都有 yfinance 快照序列，最長約 80 天 → 稀釋燈窗不滿一年，今天 0/73 判色（帶 `colour_available_on` ≈ 2027-07） | 同上 |
| EDGAR companyfacts | **已在 `fetchers/edgar_xbrl.py`**（tag 白名單、白名單內歧異拒寫、`filed`、單一計價單位、`companyfacts_lag`）；`scripts/backfill_fiscal_year_results.py` 用它寫過 66 檔 `fiscal_year_results`。**20-F 發行人**（TSM、GFS、TSEM、HIMX、POET、NBIS、UMC、XPEV 等）沒有 10-Q 季度事實；TSM、UMC、XPEV 是 USD 報價的 ADR、報表 TWD／CNY | 讀 `fetchers/edgar_xbrl.py` 註解 |
| 報價單位 ≠ 報表幣別 | IQE.L（GBp／GBP）、XFAB.PA（EUR／USD）、HEXA-B.ST（SEK／EUR）、ENA.V（CAD／USD）等；Engine C **沒有歷史匯率序列** | `financial_snapshots.financial_currency`；`identity/currency.py::resolve_quote_unit` |
| 月營收 | 7 檔台股、各 **24 個月（25 列，其中一個月重複）**（2024-09 → 2026-08）；**`published_at` 恆為 NULL**（`published_at_basis=statutory_deadline_only`，MOPS 沒有實際公告日），只有 `disclosure_deadline`（次月 10 日，法定上界）；`python -m engine_c.monthly_revenue --backfill N` 已存在 | `monthly_revenue_observations` |
| 分部／產品線營收占比 | 人工觀測 31 檔／8 檔，**每檔只有一個 as_of** | `manual_observations` 的 `segment_revenue_share`／`product_line_revenue_share` |
| going concern | `manual_fields` 的 `litigation_and_audit_flags` 1 筆（6594.T，自由文字）；**IQE.L 的 KPMG 查核意見與 note 2.2 逐字躺在 `debt_maturity_and_covenants`**（`alpha/wipeout.py` 檔頭點名的第一個案例）；`going_concern_flag()` 必回灰（`capability_absent`） | `alpha/wipeout.py::going_concern_flag` |
| Engine C 欄位登記 | 權威是 **`config/engine_c_observation_fields.json`**（屬性 `verifiability`＝mechanical／judgment；**沒有逐欄值字彙機制**）；judgment 欄位流程：`python -m engine_c.set_manual_field …` 鑄提案 → `python -m engine_b.todo sync` 取編號 → 核准後 `python -m engine_b.todo complete-observation <n>`（**bare `go` 被拒**）；值驗證前例在 `engine_c/pending_observations.py::propose()`（2026-08-14 LITE 事故：只在 ledger 端驗 → 核准後才失敗） | 讀上列檔案 |
| 語意 watch 契約 | `engine_b/event_watch.py::_validate_semantic` 只收 `source_ref` 以 `thesis:`／`reading:` 開頭；`entities` 至少一個 registry 解析得到的 `co:*`；`expires` 必填；`add_watch` 的喚醒目標恰好擇一（pq2／假設／lead／disproof_ref／wake_reading）；`expiry_class`：thesis→`thesis_review`、reading→`reread`、其餘→`decision`（鑄 pq2 `watch_decision`） | `engine_b/event_watch.py:359-390,561-580` |
| date watch 的生命週期 | `check_watches` 對 kind=date 在 `until ≤ 今天` 時轉 **`fired`**（不是 expired）；`mark_expired` 只轉 active；fired 且沒有 wake_pq2／wake_lead／disproof_ref／wake_reading 的一律被 `classify_watch` 歸到 `fired_hypothesis_check`（consumer＝research-drain 段 0b 假設對照）；`todo sync` 對沒有 wake_pq2 的 fired 直接跳過；`wake_target()` 沒有對應分支時印「沒有喚醒目標」；`event_watch add` CLI 沒有對應新目標的旗標 | `engine_b/event_watch.py:414-432,537-551,1056-1073,1139-1154`；`engine_b/queue_segments.py:207-217` |
| 讀圖狀態 | `reading_status_rows` 有四態：`current`、`stale_low`（只有低等級變動，不進重讀佇列）、`stale`、`expired` | `alpha/providers/structure_readings.py::reading_status_rows` |
| `engine_b/cli.py::_held` | 餵 **pq1 排序的「持股關聯」鍵**（含 beta 持股）與 daily triage 的 fail-closed（Sheet 讀不到 exit 2） | `git grep -n "_held" -- '*.py'` |
| writer lock | `scripts/writer_guard.py` 是既有的雙向 writer lock（daily 與互動 session 互斥） | 讀該檔 |
| `companyfacts_lag` | 只對照 10-K／10-Q——**20-F／40-F 發行人恆不報落後**；submissions 抓取失敗時回 `(snapshot, None, None)`、不警告 | `fetchers/edgar_xbrl.py:182-205` |
| lead 實體解析 | `engine_b/entities.py::_base_ticker_index`／`resolve_company_ids` **已做**「無後綴 ticker 唯一對應才解析」（多家時整組丟棄）；檔頭明寫「`company_id_for_ticker` 維持嚴格——資本歸屬必須精確」；走圖第 5 型對 `entities.tickers` 另用嚴格查詢重算 → `unresolved_names` 12 個（AKAM、AMZN、ASML、CAPA、CXMT、DRAM、EWY、PSMC、**SIVE**、**SOI**、SPCX、STM），其中 SIVE、SOI 是誤報 | `engine_b/entities.py:41-96`；`query/graph_walk.py:249-251` |
| `duplicate_nodes` CLI 的使用者 | `skills/research-drain/SKILL.md`（約 159 行，重複節點判定時的逐字對照，L18）、`tests/test_duplicate_nodes.py:164`（守門：skill 必須提到它）、`docs/OPERATIONS.md:552` | `git grep -n "query.duplicate_nodes"` |
| APP 孤兒 artifact | state 目錄中不在 `STATE_KINDS` 的：`coverage.json`、`ranking.json`、`basket.json`、`multi_year.json` | `ls` state 目錄對 `webapp/contracts.py::STATE_KINDS` |
| Sheet 持股 | Sivers 的 symbol 是 **`FRA:2DG`**（`registry.company_id_for_ticker` 回 None；對應住 `identity/execution.py::_EXECUTION_ALIASES`，方向 research→execution）；alpha 直接持股（2026-09-25 快照）只有 FRA:2DG、TYO:7803；**NVDA、MU、GOOGL、TSLA 是 beta instrument 但 registry 也解析得到 `co:*`** | Sheet 唯讀讀取；`config/beta_policy.json` `instruments` |
| alpha／beta 判別 | `risk/hard_caps.py::_instrument_for`（**私有**；賣出路徑在判別前就 return）；`risk/snapshot.py::build_portfolio_components` **另有一份**（sheet_aliases） | `risk/hard_caps.py:105`；`risk/snapshot.py` |
| `record_trade.py` | 已有 `--override`（硬擋放行）與 `--reason`（override 理由）；**帶 `--reason` 卻沒帶 `--override` 就 exit 2**；第一步 `locate_portfolio_cells` 必須恰好命中 1 列（dry-run 也一樣），否則 ValueError；每筆事件已帶 `hard_cap_check`（程式內也叫 receipt） | `scripts/record_trade.py` |
| `record_trade.py --log-only` | **不帶 `--apply` 也會寫 `trade_log.jsonl`**（`scripts/record_trade.py:253-275`）——「不帶 `--apply`」不等於 dry-run | 讀該段 |
| 成交事件 | `library/trades/trade_log.jsonl` 2 行；**讀它的 production 程式只有 `record_trade._already_recorded`**（另有 2 條測試讀真實 log）——positions、計分表都不讀 | `git grep -n trade_log -- '*.py'` |
| 心跳的缺席常數 | `_CANDIDATE_BOARD_ABSENCE`、`_PRICED_IN_ABSENCE`、**`_WIPEOUT_ROLLUP_ABSENCE`**（理由句「Phase 3 候選板接手前沒有上游」）；心跳零網路，只經 `_load_state` 讀 state artifact | `crons/heartbeat.py:604-620,658,702,1216-1219` |
| positions artifact | 只留 NAV 摘要（檔數＋最大一筆）；rows 是研究 cohort，live 欄來自 trade_log，**沒有逐檔持股** | 讀 `webapp/materialize.py` 的 positions |
| 已退役的 state kind | `basket`、`multi_year` 由 `webapp/contracts.py` 拒收——候選板**不能**叫 `basket` | `webapp/contracts.py:57-60` |
| 殭屍 grep B 組 | regex `basket\|籃子\|FILTER_REASONS\|payoff_not_positive\|market_cap_above_max\|analyst_count_above_max`，掃 code／skills／tests／config／static——**主題籃子不得叫「籃子」或 `basket`；邊緣判定的理由碼不得叫 `market_cap_above_max`／`analyst_count_above_max`**（A 組另掃「首選」）；`config/alpha_screen.json` 已在 keep-list | `scripts/retired_mechanism_grep.py:18` |
| 覆蓋厚薄門檻 | `config/alpha_screen.json`：`market_cap_max_usd` 10B **AND** `analyst_count_max` 12；市值必須先正規化（`alpha/providers/market_normalization.py`，Phase 0 註明「Phase 3 候選板接手時仍從這裡取」）；COHR 約 62B、LITE 約 83.5B → 非邊緣 | 讀該檔 `_doc`、`_why_*` |
| `graph_holes` 段計數 | 九型命中之和（異單位）；段說明文字（`engine_b/queue_segments.py:115-117`）逐字寫「計數＝九型命中筆數之和」；`research_total` 再加一次；心跳與 `audit/checks.py::_graph_holes` 各算一份；`graph_holes=60` 只出現在稽核 **QueueSegments** 那一行 | Phase 2 closeout §5 #1 |
| `test_full_chain_acceptance` | 本機真 runtime（Neo4j＋真實 ledger）整合測試，27 passed；12 條活判準（refresh 矩陣、PIT、黑箱 CLI 逐格相等）；skip 條件依賴凍結的 `decision_lab.db` 與 COHR assumptions ledger | 讀該檔；Phase 0 plan §0.6 偏差 #29 |

## 0.3 本 Phase 刻意不做

- **不動圖**（Neo4j 節點、邊、屬性）；不動讀圖 ledger（3.5 只**讀**現行讀圖）。
- 不做量測（Phase 5）：追蹤表的組基準、三個 power-law 統計量、圖預測對錯表、計分表接組超額。**本 Phase 只定義主題等權組、並讓「已定價嗎」讀它**；Phase 5 沿用同一個定義。
- 不做層中心選源與 `substitutability` 的 `auto` 投影稽核（Phase 4）。
- **三題不得長回估值模型**（ROADMAP「明確不做」）：不算目標價、不算 payoff、不對同業倍數校準、不設「已定價」門檻。組中位數只當脈絡印。
- **不做歷史匯率換算、不寫死 ADR 比率**：口徑不相容一律回 `inputs_incompatible`（§4.1）。
- 不讓候選狀態排序：候選板組內按 ticker 字母，沒有分數、沒有 top-N、沒有「最該買」。邊緣門檻只決定「算不算倍率候選」，不排序、不給尺寸。
- 不改 `AGENTS.md`（本 Phase 沒有任何判準句要改）。
- 不回填 Engine C 的**人工** ledger（`manual_observations` append-only）：回填只進新的機械歷史表（§3）。
- **不退役 `get_bottlenecks`**：它仍餵 `build_research_context` Q1 與 PointInTime 洩漏探針（AGENTS 指名的 INV-6 查證命令用它）；本 Phase 只讓 argument 鏈段不再吃它（§8）。
- **不整併 `risk/snapshot.py` 那份 alpha 判別**：本 Phase 新增的呼叫端一律用 `hard_caps` 的公開函式，snapshot 那份列 §14 待決。
- 不讓 `record_trade.py` 新增 Sheet 列：首次建倉照舊先手動建列（OPERATIONS 寫明）。
- Phase 2 closeout §5 其餘各題（#2 研究動作、#4 維持、#6／#7／#10／#11／#13–#17）不在本 Phase，照實帶到結案待決（§14）。

## 0.4 ROADMAP amendment（五欄；使用者 2026-09-26 定案 A1–A6、2026-09-29 追加 A7 並細化 A3／A4；ROADMAP Phase 3 列同 commit 改寫）

**A1｜敘事是短評 v2：七格改題，加結構化欄位**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「narrative ledger 加 `candidate_state`（五值封閉字彙）」 |
| 新觀察 | 敘事 ledger 就是短評 ledger（`library/private/alpha/briefs/`，3 檔）；七格裡兩格的題目與 placeholder 仍是已退役的估值鏈，`{assumption:…}`／`{bet_assumption:…}` 的值來源也已退役 |
| proposed change | `investor-brief/v2`：slot key 集合 `demand`、**`position`**（原 `supply`：題目改成「坐在哪幾層／格、各占多少營收」）、`bottleneck`、**`priced_in`**（原 `market_view`）、`our_bet`、**`what_must_be_true`**（原 `if_right_if_wrong`）、`when`——**題目變了的格換 key**（L12）；placeholder 字彙拿掉 `base_target`、`bet_target`、`base_return`、`payoff`、`downside_target`、`downside_return`、`value_date`、`sell_side_target`、`market_multiple` 與帶參數的 `{assumption:…}`／`{bet_assumption:…}`，加三題稽核區的 placeholder（§5）；結構化欄位 `rides[]`、`disproof[]`、`answers`、`candidate_state`、可選 `history_not_comparable`、`acknowledged_touched[]`。v1 照讀、id 不變 |
| why | L19：每次載入的題目會被當成目標；只加欄位，寫的人每次都會照舊題目寫估值 |
| impact | `alpha/narrative/`、`alpha/providers/briefs.py`、`alpha/cli.py` 的 brief 入口（含 `--retract`）、`alpha/models/session_assessor.py`、`briefing/alpha_view/builder.py`（填值）、`engine_b/event_watch.py`／`engine_b/todo.py`／`engine_b/disproof.py`／`engine_b/queue_segments.py`（敘事來源的 watch）、audit、殭屍 grep C／E 組 keep-list 縮小 |

**A2｜主題等權組定義從 Phase 5 移到 Phase 3**

| 欄 | 內容 |
|---|---|
| 原 roadmap | Phase 5「主題等權籃子定義（append-only、附理由與日期）」 |
| 新觀察 | 「已定價嗎」三行中的第二、三行都要它；留到 Phase 5，這兩行整個 Phase 3 只能印缺席 |
| proposed change | Phase 3 建 append-only 的主題等權組 ledger（§4.2），成分由研究步驟提 pq2（spec 凍結進 payload）、使用者定，go 後由 `complete-theme-cohort` 照凍結 spec 寫入並結案；**程式與 UI 一律叫「主題等權組」／`theme_cohort`**；Phase 5 沿用同一個定義 |
| why | 決定紀錄 §4.2「籃子定義與 G9 量測基準共用同一個」；§6.7「成分是一個判斷，寫下時附理由與日期，變動 append-only」 |
| impact | 新 ledger、讀取器、`python -m alpha theme-cohort`；ROADMAP Phase 5 列已改為沿用 |

**A3｜三題的資料源：一次機械回填＋daily 增量；稀釋逐檔單一來源；going concern 結構化欄位**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「已定價嗎＝自家 EV/S（虧損期 P/S）三年百分位…」「會死嗎＝歸零旗標補稀釋與 going concern 兩盞」 |
| 新觀察 | 快照最早 2026-07-08；股數序列約 80 天；going concern 沒有能判色的欄位；companyfacts 取數已在 `fetchers/edgar_xbrl.py`；台股月營收沒有實際公告日；ADR 與報價≠報表幣別的標的直接相乘會靜默算錯；一次回填後若無增量，幾週內就過期（P0 review） |
| proposed change | Engine C 加機械歷史表（價格 raw／adjusted＋分割事件、EDGAR 營收／營業利益／現金／債務／封面股數，每列帶 `filed` 與 accession），一次回填＋**daily 零 LLM 增量步驟**（#15）；台股營收直接讀 `monthly_revenue_observations`（回補 ≥48 個月），可用日＝`disclosure_deadline`（法定上界，照實標）；口徑不相容回 `inputs_incompatible`。稀釋燈逐檔單一來源（#14）、trailing 一年窗。going concern 加欄位 `going_concern_opinion`（judgment），值驗證在提案層與 ledger 層共用一個函式 |
| why | 不回填，這兩題三年內恆為缺席（L14-4 恆亮）；going concern 的措辭精度本身是 claim（L11-1），不得從自由文字機械推 |
| impact | `engine_c/db.py`（SQLite 建表）、Postgres migration＋`schema.sql`、`fetchers/edgar_xbrl.py`、新 `engine_c/history_backfill.py`、`crons/daily_task.py`、`config/engine_c_observation_fields.json`、`engine_c/pending_observations.py`、`engine_c/manual_observations.py`、`engine_c/checklist.py`、`alpha/wipeout.py` |

**A4｜成交收據：範圍、旗標、兩欄狀態**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「`record_trade.py --receipt`：成交事件內嵌…，缺收據 fail closed」 |
| 新觀察 | beta 沒有敘事；無條件 fail closed 等於研究 gate 資本；既有 `--override`／`--reason` 是 5% 硬擋的放行與理由，共用會讓一個旗標同時放行兩道 gate（L12）；Sheet 持有時推導狀態一律 held，收據只記它會丟掉敘事宣告；Sivers 在 Sheet 是 FRA:2DG（P0 review） |
| proposed change | 只管 alpha（beta 不要）；alpha 買進與賣出都必帶 `--why "<一句>"`（G12「使用者一句理由」）；缺現行 v2 敘事 fail closed，**另一個旗標** `--no-narrative-override "<理由>"` 放行並記 `narrative: absent`／`legacy_v1`；5% 硬擋的 `--override --reason` 原樣不動、互不放行；收據住事件的獨立 key `research_receipt`，分 `declared`（敘事宣告＋三前提當下重驗）與 `derived`（成交前 Sheet 推得的狀態）兩欄；Sheet symbol 經 execution 反向別名再查 registry。**使用者 2026-09-29 預先授權本 Step（#16）** |
| why | 收據是問責不是授權；「出場只認反證」所以賣出記是哪條反證；append-only，記錯改不回來 |
| impact | `scripts/record_trade.py`、`risk/hard_caps.py`（匯出公開判別函式）、共用的持股解析與 watch 歸屬函式、`docs/OPERATIONS.md` |

**A5｜個股頁面板重排一併處理 Phase 2 殘留**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「readiness 核心面板換」 |
| 新觀察 | argument「鏈」段只經 `get_bottlenecks` 取需求錨（sub≥4 成員＝filter 殘留，G1），但 `get_bottlenecks` 另有兩個不能拆的呼叫端；Phase 0 偏差 #16 的原意是讀圖面板升核心；`refresh=review_required` 今天全是退役估值鏈的殘留；ROADMAP 個股頁表要求 downside 每條反證連到 watch |
| proposed change | 鏈段的需求錨改取自敘事 `rides[]` 的讀圖需求側（不改 `get_bottlenecks` 本身）；readings 升核心＝接回 #16，讀圖面板的狀態只由讀圖對圖決定、**不吃** `refresh.overall`；downside 每條反證連到 watch id；argument 標題改 |
| why | 同一批面板，拆開做要改兩次同一份 digest 基準 |
| impact | `briefing/alpha_view/builder.py` 或 `briefing/analyst_view/compose.py`（鏈段在哪一層組，§8 二擇一）、`webapp/materialize.py` |

**A6｜Phase 2 帶過來的三個小修**

| 欄 | 內容 |
|---|---|
| 原 roadmap | （Phase 2 closeout §5 #1、#3、#5 待決） |
| 新觀察 | #3 的前提有誤：lead 端早已做唯一後綴解析，走圖第 5 型的 SIVE 是它自己用嚴格查詢算出的誤報；`duplicate_nodes` CLI 是 research-drain 的逐字工具（P0 review） |
| proposed change | a `graph_holes` 段計數＝**有命中的型別數**，段說明文字同改，刪 `research_total` 對它的加總，心跳與稽核共用一個函式；b **`company_id_for_ticker` 維持嚴格不動**，走圖第 5 型改用 lead 解析的同一份 resolver（`engine_b/entities.py` 提成共用），`_base_ticker_index` 碰到多家時改為列出候選（不猜）；c 走圖第 9 型先印兩端逐字，再退役 `query.coverage_gaps`／`query.duplicate_nodes` 的 CLI 入口（函式留），state 目錄中不在 `STATE_KINDS` 的孤兒檔清到 0 |
| why | a：異單位加總不該存在；b：INV-1「ID 沒解析對」要修在算錯的那一處，不放寬資本歸屬路徑；c：退役要拿乾淨，但 L18 的逐字不能跟著消失 |
| impact | `engine_b/queue_segments.py`、`audit/checks.py`、`crons/heartbeat.py`、`engine_b/entities.py`、`query/graph_walk.py`、`query/coverage_gaps.py`、`query/duplicate_nodes.py`、`skills/research-drain/SKILL.md`、`tests/test_duplicate_nodes.py`、`docs/OPERATIONS.md` |

**A7｜覆蓋厚薄門檻＝候選板的「邊緣」定義（2026-09-29 使用者定案 #13）**

| 欄 | 內容 |
|---|---|
| 原 roadmap | ROADMAP Phase 0 退役清單 B 組：「覆蓋厚薄門檻（`alpha_screen.json`）**留**，Phase 3 當『邊緣』定義用」；Phase 3 列未寫怎麼用 |
| 新觀察 | 初版 plan 漏了；COHR、LITE 是 3.5 要重寫的敘事，照門檻兩者都非邊緣 |
| proposed change | 候選狀態的顯示端推導多一條：非邊緣 → 「非倍率候選」組（宣告 `open` 也不算可開）；缺市值或覆蓋 → 「邊緣無法量」組；市值先經 `market_normalization` 正規化；每列印邊緣判定與兩個輸入值 |
| why | `AGENTS.md`「候選門檻是覆蓋厚薄，不是上市地」；目標是邊緣小公司的 power-law，不是大型股 |
| impact | 候選狀態推導函式（§7）、候選板、心跳計數、收據 `derived` 欄 |

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者已核准的 PLAN_PROPOSAL**（§0.1 共 17 題）。`AGENTS.md`「常規推進授權」照用：
Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step**，做到 Phase 3 結案為止。只有六條停止條件之一成立才停。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（#12）**：預定三處——R2-c（3.2 之後：財務 PIT／identity／units 與 Engine C schema）、
R2-a（3.4 之後：append-only 敘事 contract＋語意 watch 新來源）、R2-b（3.8 之後：資本路徑）；其他 Step 若命中 trigger 同樣直接發 `WORK_REQUEST`。NO_GO → `AWAITING_HUMAN`。

**停止條件③（資本）已由使用者 2026-09-29 預先授權兩處**：①Step 3.8 依本 plan §9 的內容（#16），R2-b 回 GO 就照常 commit、push、接續；②Step 3.6 把 `risk/hard_caps.py` 的判別函式改成公開（#17）——**只准匯出、硬擋行為不變、既有硬擋測試全綠**。超出這兩處的任何資本路徑改動、或 R2-b 不是 GO，一律停。

**停點：** 無其他預定停點。3.5 由強模型做（#9）；**若執行者是便宜模型，3.5 停下來印 §6 的「強模型貼這段」**。
3.5 會鑄兩類 pq2（主題等權組成分 `manual`、going concern 觀測 `engine_c_observation`）——**掛號後在 HUMAN SUMMARY 列出（使用者在場可當場 go），接著做下一件，不停在編號上等**；
go 之後的寫入由收到 go 的那個 session 做（§6 第 3 點）。

**每個 Step 一個 commit（大的 Step 可拆，進度表在最後一個 commit 才 ○→✅），訊息第一行寫 Step 編號；Step 為 GO 就 push。**
新 session 先看下面進度表與 `git log --oneline -20`，從第一個未 ✅ 的 Step 接續。commit 短碼由下一個 Step 的 commit 補填。

**同一 working tree 只讓一個 writer：** `StockBotv2-Daily`（台北 05:30）是唯一排程，它寫 `library/`（含 `event_watches.json`）、Engine C、APP artifact。
- **3.2（Engine C 建表＋daily 增量步驟）與 3.6（daily materialize 旗標）的 commit 不得跨越 05:30 還沒 push**；push 之後第一個 `get_conn()`（通常就是 daily）會在正式庫建新表——那是預期。
- 3.2 的回填**不得與 daily 同時跑**（同一個 SQLite）。
- **3.5 會寫 `library/leads/event_watches.json`**（敘事 disproof 登記）；3.2 的回填寫 Engine C 正式庫。
- **互斥靠既有的 writer lock（`scripts/writer_guard.py`），不靠查排程時間**：寫 `library/` 或 Engine C 正式庫之前先取得互動 writer lock、做完釋放；daily 持有鎖時等它結束。另外開工前查 `schtasks /Query /TN StockBotv2-Daily /V /FO LIST` 的下次執行時間，只用來規劃「commit 要在 05:30 前 push」。

| Step | 內容 | 狀態 | 執行者 | commit |
|---|---|---|---|---|
| 3.0 | 基準快照（`docs/reports/2026-09-29-phase3-baseline.md`） | ✅ | 執行模型 | `559414e` |
| 3.1 | Phase 2 帶過來的三個小修（A6 a／b／c） | ✅ | 執行模型 | `ebab3d0`、`50954a9`、見 3.1c |
| 3.2 | Engine C 機械歷史表＋一次回填＋daily 增量步驟；going concern 結構化欄位（R2-c：CONDITIONAL_GO → 條件修正後覆核 GO） | ✅ | 執行模型 | `aaf926b`、`42f2596`、`b403e78`＋收尾 |
| 3.3 | 三題稽核區；主題等權組 ledger；邊緣判定 | ✅ | 執行模型 | 見 git log「Step 3.3」 |
| 3.4 | 敘事 v2 契約＋敘事來源的語意 watch＋`narrative_rewrite` 佇列段（R2-a：CONDITIONAL_GO → 條件修正後覆核 GO） | ✅ | 執行模型 | `4e96223`、`0d4c7ad`＋收尾 |
| 3.5 | 研究：v2 重寫 AXTI／COHR／LITE、寫 Sivers；提主題等權組與 going concern 的 pq2 | ○ | **強模型** | |
| 3.6 | 候選狀態推導與候選板、`candidates` kind、心跳 | ○ | 執行模型 | |
| 3.7 | 個股頁：首屏、稽核區、readiness、argument 鏈段／標題、downside 連 watch | ○ | 執行模型 | |
| 3.8 | `record_trade.py` 研究收據（R2-b；#16 預先授權；R2-b 一併審 3.6 的 `hard_caps` 匯出） | ○ | 執行模型 | |
| 3.9 | 新管線 full chain 測試（保留現行 12 條活判準） | ○ | 執行模型 | |
| 結案 | completion gate ＋ closeout ＋ R2 ＋ ROADMAP ✅ | ○ | 執行模型 | |

**開工／續工指令：貼 `/phase-run` 即可**（不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。沒有需要我核准的事就一直做到 Phase 3 結案；撞到六條停止條件才停（3.8 的資本條件已預先授權，見 §0.5）。
Step 3.5 是強模型的研究步驟：執行者是強模型就直接做，不是就停下來印 §6 的「強模型貼這段」給我。
每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|
| 1 | 3.2 | 表的欄位：`fundamental_history(ticker, metric, period_start, period_end, filed, accession, value, currency, unit_scale, derived, source, fetched_at)` | 多兩欄 `form`、`tag` | `form` 是申報人類別判定的輸入（讀取端從已存列判，零網路）；`tag` 讓每一列指得回 companyfacts 的原 tag（L15：mechanical 要可重導）。plan 寫「名稱可調」 |
| 2 | 3.2 | 「國內申報人」例：EDGAR submissions 最近 18 個月有 10-Q | 同一條規則，輸入改成 companyfacts 各 fact 的 `form`／`filed`（回填時）或已存列（讀取端） | 讀取端（三題、稀釋燈）不得連網；兩個輸入都是同一份 companyfacts，判出同一個類別。落後檢查仍另查 submissions |
| 3 | 3.2 | 回填前跑 `companyfacts_lag`、落後就記缺席 | 抽成 `companyfacts_lag_status`（表單當參數、抓不到＝`unknown`、**快照日只看營收白名單 fact**）；`companyfacts_lag` 改成它的薄殼、行為不變 | 原函式寫死 10-K／10-Q（20-F 恆不報落後）、抓不到與「沒落後」同形；R2-c 另抓到 TSM／UMC 形狀（最新 20-F 只有封面 dei fact 會把快照推成 current），條件①修正 |
| 4 | 3.2 | as-of 讀取規則 | 抽成 `shared/as_of.py::latest_known_by_period`，Engine C 讀取端與三題逐日計算共用 | 同一條「T 時刻知道什麼」規則兩份實作的那天起就會開始偏離（L16）；`alpha/` 核心不得 import `engine_c`，所以放 `shared/` |
| 5 | 3.3 | 取數住 `engine_c/checklist.py` | 三題取數另立 `engine_c/three_question_inputs.py`；稀釋與 GC 的取數仍在 `checklist.get_wipeout_inputs`（加 `_cover_shares_series`、`_going_concern_record`） | checklist 是 L9 gate 的財務核驗清單（五項凍結），三題與它無關；塞進去會讓「動三題」與「動 gate 清單」改同一個檔。取數仍只在 Engine C |
| 6 | 3.3 | 20-F 的已定價①：股數與價格不是同一種證券單位（ADR）→ `inputs_incompatible` | 20-F／40-F 發行人一律 `inputs_incompatible`（不分是不是 ADR）；報表幣別≠報價結算幣別先判 | ADS 比率沒有登記、機械分不出 GFS（普通股）與 HIMX（ADS）；我們也沒存 20-F 的封面股數——一律不算比猜一個比率誠實（plan §0.3 不猜 ADR 比率） |
| 7 | 3.3 | 「出現在數字裡了嗎」沒有鮮度規則 | 最新一點太舊 → `insufficient_evidence`＋`days_since_last`（季 200 天、年 550 天、月 75 天） | 試跑：TSM 的年度營收最新一期停在 2023（Step 3.2 R2-c），照印就是把三年前的數字當現在；上限沿用 `edgar_xbrl._MAX_BASELINE_AGE_DAYS` 的量級 |
| 8 | 3.3 | 分部／產品線占比序列 | 同一個欄位有 ≥2 個觀測日才成序列；兩個欄位不湊點 | 試跑：3081.TWO 的產品線占比（2025-12）與分部占比（2026-06）被湊成一條「序列」——兩種切法不能相比（L12） |
| 9 | 3.3 | 稀釋燈 inputs 鍵名 | `base_outstanding`／`last_outstanding`（原 `first_shares`／`last_shares`） | 燈一亮 inputs 就進黑箱輸出，`shares` 是部位語意禁用字（`FORBIDDEN_POSITION_TOKENS`），`test_full_chain_acceptance` 抓到；公司的在外流通股數不是部位，但欄位名不得讓人分不出來 |
| 10 | 3.4 | （未寫）沒有短評時首屏列的題目 | 沒有短評的 70 檔，brief 面板列的是 **v2 七題**（原本是 v1 七題） | v1 的題目含已退役的估值題（市場怎麼看、對了值多少）；每次載入的題目會被當成目標（L19）。個股頁核心面板文字 digest 因此在這 70 檔的 brief 面板變動——3.7 的前後對照要把它列為預期變動 |
| 11 | 3.4 | 寫入端檢查 | `alpha brief --add` 寫入前讀 Neo4j（讀圖現行狀態）與 Engine C（三題），寫入後寫 `event_watches.json`；新寫一律 v2、v1 只收撤回 | 「現行」要跟現在的圖比才答得出；三題的 unmeasurable 要讀稽核區才驗得了；v1 新寫會把退役題目再帶回來 |
| 12 | 3.4 | `still_holds` 對到 watch 的 reactivate | 醒來的舊版 `brief:` watch 處置為 still_holds 時**收掉並記收據**，不 reactivate | 新一版的 `disproof[]` 會以新的 `brief:<新 id>#n` 重登同一條件；舊版的回 active 會與新版的同條件並存（L12：同一條件兩筆 watch） |
| 14 | 3.4 | §5 第 4 點：`link_source_ref` 指向的來源換版（讀圖重讀、memo 換版）→ 進 `narrative_rewrite` | 3.4 **沒做**，移進 3.6 的候選狀態推導（§7 第 1 點新增一條） | R2-a N1 抓到：3.4 沒實作也沒測試。它不是 watch 的狀態，是「現行敘事的連結斷了」——要從敘事往 registry 看，候選狀態推導本來就逐檔重算這件事；放 3.6 讓佇列段、audit、心跳與候選板用同一個判定 |
| 15 | 3.4 | （未寫）寫入端怎麼看「已過到期日、daily 還沒標記」的 watch | 寫入前先對本公司敘事來源的 watch 做 daily 同一條時間轉換（`narrative_watches.settle_due`：過 `expires`→expired、date 到 `until`→fired）；`candidate_state` 另外拒收照日期已過期的 watch；watch 登記在 append 前先在副本上預演 | R2-a C1／C4：否則換版會把「到期未判」當成還在等收掉，登記失敗會留下「ledger 有、registry 沒有」的半套寫入 |

## 0.7 P0 review 處置（2026-09-28／29；逐條原文在 workflow journal，此處只列處置）

- **成立且已改進本 plan 的**（57＋4）：分布在 §0.2（事實更正十餘列）、§0.4（A1、A3、A4、A6 改寫，新增 A7）、§2–§10 各 Step 的「改哪裡／怎麼改／怎麼驗」與 L11-6 ④、§11 驗收層標籤、§12 gate 文字、§13 陷阱、§14 待決。兩條 blocking（敘事來源的語意 watch 登記不進現行契約；disproof 條目缺 `entities`／`expires`）→ §5 第 4–7 點。
- **需要使用者決定的 4 條** → §0.1 #13–#16。
- **推翻的 7 條不採**（例：「audit PointInTime PASS 被當成歷史表 PIT 證據」——本 plan 從未這樣用；「成員限 Engine C 快照宇宙會帶偏差」——快照宇宙＝registry 全體有 ticker 的公司）。**但其中「成員限 Engine C 有快照」一句仍從 §6 拿掉**：4A 沒有這條限制，改由寫入端要求成員 registry 解析得到。
- **因額度未驗的 31 條**：與成立者重複的併入處置；獨有的由 plan 作者自己查證，成立 4 條（`alpha_screen.json` 漏接→A7；ROADMAP「downside 每條反證連到 watch」漏 Step→§8；`rides[]` 未驗公司在供給側且 §6 對 Sivers 的預設錯誤→§5、§6；觸及後重寫會卡死、「該重寫」沒有進佇列→§5 第 6–7 點）。其餘小項（心跳漏「無敘事 N」、3.5／3.9 缺 L11-6 ④、§11 層標籤）一併改。
- **完整性補查（2026-09-29，對改寫後的 c427d0c）**：37 個 finding，成立 22、推翻 4、11 個因額度未驗（作者自查：`--log-only` 寫 trade_log、`companyfacts_lag` 對 20-F 無效、國內申報人判定、`stale_low`、B 組理由碼、連結來源輪換、連結沒騎的讀圖、收據不連圖／網路——成立並改；TYO:7803 → §14）。主要改動：`wake_brief` 到點 fired 的路徑（三個視角各自獨立報到，其中一個判 blocking）；缺 X 的 watch 限本公司 `wake_brief`；換版／撤回不吞待判 watch、處置綁本公司全部版本；連結改用來源鍵；歸屬函式不含 `candidate_state.watch_id`、含連結來源；`_held` 不被取代；「已持有」＝股數 > 0；Sheet 讀不到的一致語意；心跳逐狀態最老滯留；讀圖升核心後 research-drain 段 5 的路線；「出現在數字裡」恢復分部序列優先；主題等權組寫入綁凍結 spec；writer lock。**需要使用者決定的 1 條 → §0.1 #17**。

---

## 0. 不可越線（違反即 NO_GO）

1. **不碰圖與讀圖 ledger**：不改 Neo4j；讀圖 ledger 只讀。
2. **敘事 ledger 只由 Step 3.5（強模型）經正式入口 append**；其他 Step 的測試一律用暫存目錄。**既有 7 行 v1 紀錄一行都不改寫**，`brief_id` 用新程式重算必須逐字相同。
3. **Engine C 人工 ledger（`manual_observations`、`manual_fields`）只能經既有人工觀測路徑 append，且 judgment 欄位要有 pq2 `complete-observation`**；回填只寫新的機械歷史表。**going concern 觀測的寫入是 Engine C 判讀寫入 gate**——3.5 只鑄 pq2，不寫。
4. **舊 Decision Store 只准讀**：3.0 記 sha256 與 `live_choices`，結案比對必須相同。
5. **`library/trades/trade_log.jsonl` 與 Google Sheet 不得在測試或試跑中寫入**；`record_trade.py` 的試跑一律 dry-run——**不帶 `--apply`、也不帶 `--log-only`**（後者不帶 `--apply` 也會寫 trade_log）——或指到暫存 log。
6. **任何 `python -m <module>` 命令字串變更 → sandbox impact review 五步**（ROADMAP 硬約束 10），同一個 commit 改相應測試。本 Phase 已知會撞：3.1c（兩支 CLI 退役）、3.2（新回填 CLI＋**daily 增量步驟**）、3.3（新子命令 `python -m alpha theme-cohort` 唯讀＋`python -m engine_b.todo complete-theme-cohort` 寫 private ledger，互動專用）、3.4（`python -m engine_b.event_watch add --wake-brief`）、3.6（daily materialize 旗標）。
7. **每刪一個測試檔或測試函式，八欄的 Blocking findings 列出它守的是什麼、現在由誰守。** 活機制的測試不可刪斷言。
8. **每個 Step 動手前先答 L11-6 第④問：「如果這個改動是錯的，最先壞掉的是哪一筆現有資料或哪個活的呼叫端？」去看那一筆，寫進八欄。** 各 Step 已預填一個起點。
9. **不排序、不打分、不設門檻**：候選板組內按 ticker；三題沒有「已定價／未定價」的門檻；組中位數只是脈絡；沒有跨檔合成數字。邊緣門檻沿用 `alpha_screen.json` 既有兩個數，不新增、不調。
10. **命名：** code／skills／tests／config／static 裡不得出現「籃子」「basket」、邊緣判定理由碼 `market_cap_above_max`／`analyst_count_above_max`（殭屍 grep B 組；改用例如 `cap_over_edge`／`coverage_over_edge`）、「首選」（A 組）與 `sell_side_target`、`payoff`、`隱含報酬`、`目標倍數`、`calibrat`（C／E 組）的新命中；主題籃子一律叫「主題等權組」／`theme_cohort`；新收據 key 叫 `research_receipt`（`hard_cap_check` 已被稱作 receipt）。
11. **`identity/registry.py::company_id_for_ticker` 不得放寬**（資本歸屬路徑；`engine_b/entities.py` 檔頭）。
12. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。**
13. **四個人工 gate、五條 authority separation、六條 invariant 全程適用。** 敘事與候選狀態是 A3（研究判斷、可重算、append-only）；收據是 A5；**A3 不得替 A5 做決定**——候選狀態不擋成交（收據只記它；缺敘事的 fail closed 可附理由放行），不給尺寸。

---

## 1. Step 3.0 基準快照（Z0，一個 commit）

寫 `docs/reports/2026-09-2x-phase3-baseline.md`，每項附命令與輸出摘要：

1. `python -m pytest -q` 通過數；測試檔數；以本 commit 為起點的 `def test_` 名單存檔（結案比對函式層級增刪）。
2. `python -m audit invariants`（13 PASS 預期）。
3. 短評 ledger：3 檔 7 行的 `brief_id` 用現行程式重算＝檔內值（7／7）。
4. 73 份個股頁：每檔 readiness、blockers、refresh 與其來源；核心面板文字 digest（`python scripts/analyst_view_text_digest.py --per-panel`）；每檔 argument chain 段文字（3.7 比對用）。
5. 歸零旗標四盞每盞有值（非灰）的檔數／73——**④ 的基準**（預期稀釋 0、GC 0）；稀釋燈每檔的 `colour_available_on`。
6. `python -m crons.heartbeat --out <tmp>` 全文存檔（段 2、段 4 三個缺席常數那幾行逐字記）。
7. `python -m engine_b.event_watch counters`；每筆既有 watch 的 `expiry_class`；`python -m query.graph_walk --json` 的九型命中／母體與第 5 型 `unresolved_names`；`python -m webapp status` 的 kind 清單；state 目錄檔案清單。
8. 舊 Decision Store 三個 `*.db` 的 sha256 與 `live_choices`（`?mode=ro`）；`trade_log.jsonl` 行數與 sha256。
9. `python scripts/retired_mechanism_grep.py` 九組三個 0；列出 C／E 組目前與短評相關的 keep-list 條目（3.4 後要縮小，且不得有「已列但不再命中」的腐壞條目）。
10. 三檔 v1 短評：每格**原始 slot 文字、placeholder 清單、fill 後的 missing 清單**（3.4 比對用——不比 fill 後的字面，因為每日數字會變）；另用一組固定 values 夾具跑一次 `fill_brief` 存輸出。
11. Engine C 正式庫各表的 `PRAGMA table_info` 與列數（3.2 比對「舊表不變」）。
12. 邊緣判定現況：`alpha/providers/market_normalization.py` 對 73 檔的正規化市值與分析師數、依 `alpha_screen.json` 的邊緣／非邊緣／無法量分布（3.3 用；**不是驗收數字**）。
13. pq1 排序：`python -m engine_b.cli drain` 列出的 lead 順序（3.6 驗「`_held` 語意沒變 → 逐位不變」用）。

## 2. Step 3.1 Phase 2 帶過來的三個小修（各 Z1，R1，可拆三個 commit）

**a｜`graph_holes` 段計數。** 改哪裡：`engine_b/queue_segments.py`（`graph_holes` Segment 的計數語意與**說明文字**〔:115-117〕、`research_total` 不再加 `graph_holes`）、`audit/checks.py::_graph_holes`、`crons/heartbeat.py::build_queue`。
怎麼改：新增一個共用函式（放在走圖或 queue_segments，二擇一，理由寫八欄）回「有命中的型別數」；心跳與稽核都呼叫它，刪掉另一份實作。心跳段 3 的九格逐型印法**不變**。
怎麼驗：`test_there_is_no_cross_type_number_anywhere_in_the_result` 等既有測試照綠；新測試斷言段計數 ≤ 9 且等於「命中 >0 的型別數」；`grep -n research_total` 的每個消費端寫明（目前沒有 production consumer）。
L11-6 ④：稽核 **QueueSegments** 那一行——看 3.0 的輸出，改後 `graph_holes` 從 60 變成型別數，其他格不變。

**b｜走圖第 5 型改用 lead 解析的 resolver。** 改哪裡：`engine_b/entities.py`（`_base_ticker_index`／`resolve_company_ids` 提成可共用的公開函式；多家對應時回候選清單而不是整組丟棄）、`query/graph_walk.py:249-251`。**`identity/registry.py` 不動**（§0 第 11 條）。
怎麼改：第 5 型的 `unresolved_names` 改用同一份 resolver；歧義（一個 base 對多家）列進明細並帶候選，不解析。
怎麼驗：`unresolved_names` 12 → 10（SIVE、SOI 移出），其餘 10 個逐一寫明是「registry 真的沒有」；造一個兩家同 base 的夾具，斷言不解析且列出候選；`company_id_for_ticker` 的所有 production 呼叫端（`git grep -n company_id_for_ticker -- '*.py'`）行為不變（它本身沒改，列清單即可）。
L11-6 ④：**registry 外的同名 cashtag**——`engine_b/entities.py` 已記的 ENA、SOI（`$SOI` 可能是 Solaris，不是 Soitec）：第 5 型把它們當「在圖」會不會誤報成已解析？寫進八欄（這是 lead 關聯的既有寬鬆規則，第 5 型只是改成與它一致）。

**c｜走圖第 9 型印逐字，再退役兩支 CLI＋孤兒。** 改哪裡：`query/graph_walk.py` 第 9 型的 markdown（沿用 `query/duplicate_nodes.py` 的 `_fmt_node` 印兩端逐字，不重寫）；`query/coverage_gaps.py`、`query/duplicate_nodes.py` 的 `__main__`／`main`；`skills/research-drain/SKILL.md`（約 159 行，改指走圖）＋`python scripts/sync_agent_skills.py`；`tests/test_duplicate_nodes.py:164`（守門改成斷言走圖輸出含兩端逐字）；`docs/OPERATIONS.md:552`；APP state 目錄。
怎麼驗：`python -m query.coverage_gaps` 不再是入口（或印退役訊息 exit 非 0，二擇一寫八欄）；走圖第 9 型輸出含兩端逐字；`git grep -n "query.coverage_gaps\|query.duplicate_nodes"` 在活文件與 skills 為 0（歷史文件除外）；**state 目錄中不在 `STATE_KINDS` 的檔為 0**（今天四個：coverage、ranking、basket、multi_year）；兩個 `render_markdown` 隨 CLI 退役或寫明誰用；拿掉的測試函式照 §0 第 7 條列去向。
L11-6 ④：research-drain 第三段的重複節點判定——退役後互動 session 在命令列上還看得到兩端逐字嗎（跑一次走圖第 9 型確認）。
sandbox impact review 五步（命令字串退役）。

## 3. Step 3.2 Engine C 機械歷史表＋回填＋daily 增量；going concern 欄位（Z2，R1 ＋ R2-c 常規 opt-in）

**改哪裡：** `engine_c/db.py::_ensure_sqlite_schema`（呼叫新的 `ensure_history_schema()`，比照 `monthly_revenue` 的 ensure 函式）；Postgres：`engine_c/migrations/<日期>_add_history_tables.sql`＋`engine_c/schema.sql`（雙後端對等）；`fetchers/edgar_xbrl.py`（擴充）；新模組 `engine_c/history_backfill.py`（CLI `python -m engine_c.history_backfill`，`--db <path>`、`--incremental`）；`crons/daily_task.py`＋`tests/test_daily_task.py`；`config/engine_c_observation_fields.json`、`engine_c/pending_observations.py`、`engine_c/manual_observations.py`。

**怎麼改：**
1. **表**（名稱可調，理由寫八欄）：
   - `price_history`（ticker、bar_date、close_raw、close_adjusted、quote_unit、settlement_currency、source、fetched_at）＋`corporate_actions`（ticker、date、kind＝split／…、ratio、source）。**報價單位照交易所存（例 GBp），另存結算幣別，不得為了通過驗證改寫成 ISO code**。
   - `fundamental_history`（ticker、metric ∈ {revenue_quarter, revenue_annual, operating_income_quarter, operating_income_annual, cash, total_debt, shares_outstanding_cover}、period_start、period_end、**filed**、**accession**、value、currency、unit_scale、derived（例：Q4＝FY−9M）、source、fetched_at）。唯一鍵含 accession（每份申報各一列）；讀取端 as-of T＝對每個 period_end 取 `filed ≤ T` 的最新一列。**TTM 由讀取端組，不存**。
   - 台股營收**不複製**進 `fundamental_history`：讀取端直接讀 `monthly_revenue_observations`（否則同一數字兩個 authority）。
2. **來源與範圍：**
   - 價格：yfinance 3 年日線（73 檔），raw 與 adjusted 都存，分割事件一併存。
   - EDGAR：**只對 10-K／10-Q 國內申報人**做季度＋年度（Q4＝FY−9M，標 `derived`）；現金、債務 tag 白名單 us-gaap 與 ifrs-full 各一份、白名單內歧異就拒寫（沿用 `edgar_xbrl` 的既有守則）；封面股數 `dei:EntityCommonStockSharesOutstanding`（多股類分維度申報或缺席 → 不加總、記缺席）。**20-F／40-F 發行人只存年度點**；回填前每檔跑 `companyfacts_lag`，落後就記缺席——⚠ 它只對照 10-K／10-Q，**對 20-F 恆不報落後**，抓取失敗時也不警告：20-F 另以 submissions 的最新 20-F `filed` 對照快照，抓取失敗記「落後未知」（不是「沒落後」）。
   - **「10-K／10-Q 國內申報人」由一個函式機械判定**（例：EDGAR submissions 最近 18 個月有 10-Q → 國內季度申報人；只有 20-F／40-F／6-K → 外國私人發行人），回填、增量、三題、稀釋燈四個消費端都呼叫它；判定結果與依據寫進回填報告。
   - 台股：`python -m engine_c.monthly_revenue --backfill 48`（3 年窗的第一點也要有 TTM）；可用日＝`disclosure_deadline`（法定上界，不是公告日），`published_at` 維持 NULL。**台股歷史股數**：先找機械來源（交易所公開的股本／發行股數）；**找不到就記缺席，不得用今天的股數回推**——結果照實寫八欄與 §14。
   - 其他市場不硬湊：讀取端回 `absence_kind`（§4）。
3. **daily 增量（#15）**：`DAILY_STEPS` 在 ETL 之後加一步 `python -m engine_c.history_backfill --incremental`（最新收盤、EDGAR 新申報、封面股數；零 LLM；失敗照 daily 其他 ETL 步驟的慣例記錄、不阻斷心跳）。sandbox impact review 五步；`tests/test_daily_task.py` 的 `DAILY_STEPS` 逐項相等同 commit 改。
4. **回填報告**：每檔每種 metric 的列數、最早、最晚、缺什麼與原因（20-F、companyfacts 落後、無機械來源、多股類…）；月營收重複月份的處理寫明。
5. **going concern（6A）**：`config/engine_c_observation_fields.json` 加 `going_concern_opinion`（category＝`regulatory_and_legal`、verifiability＝`judgment`、gate_member＝false、authorities 用既有 token）；值形狀寫死為 JSON `{opinion: substantial_doubt｜no_substantial_doubt｜not_reviewed, quote: 逐字, page, report_date}`；**一個驗證函式**同時在 `pending_observations.propose()` 與 `manual_observations.append_manual_observation()` 呼叫（提案層就拒收非法值，不發編號——2026-08-14 LITE 事故的前例）。本 Step **只登記欄位與驗證，不寫任何一筆**。

**怎麼驗：**
- 建表：對 `:memory:`／暫存 SQLite 呼叫 ensure 函式，斷言新表存在、舊表 `PRAGMA table_info` 與 3.0 相同；Postgres 側用 `tests/test_engine_c_migrations.py` 的 FakeConnection 模式驗新 `.sql` 被列入。
- 回填先對**暫存副本**跑（用 `sqlite3` backup API 產生，**不用檔案複製**——正式庫 WAL 模式），用真實網路，報告寫進八欄；再對正式 DB 跑（不得與 daily 同時）。
- 新測試：PIT（同一 period_end 兩列、filed 不同、值不同，T 落在兩者之間取舊值；月營收以 `disclosure_deadline` 判可用、不得讀 `fetched_at`）；冪等（重跑不重複）；分割（NVDA 型夾具：raw 市值連續、adjusted 報酬連續）；20-F 夾具只有年度點；`going_concern_opinion` 非法值在提案層被拒且不發編號。
- **L11-6 ④：** daily 的 Engine C ETL 與 `get_wipeout_inputs()` 讀的是舊表——確認舊表不變、daily 下一輪照常（3.0 的快照列數＋1 天）；push 之後第一個 `get_conn()`（daily）會在正式庫建新表。

**R2-c（常規 opt-in）WORK_REQUEST：**
```
WORK_REQUEST（R2-c，Phase 3 Step 3.2）
Target: 3.2 的 commit；engine_c/db.py、engine_c/history_backfill.py、fetchers/edgar_xbrl.py、crons/daily_task.py、engine_c/pending_observations.py、engine_c/manual_observations.py、回填報告
Claimed acceptance: 雙後端建表對等；歷史表每列可答 T 時刻知道什麼（filed／disclosure_deadline，不用 fetched_at）；20-F、口徑不相容、無機械來源都照實記缺席；分割處理正確；daily 增量步驟過 sandbox review；going_concern_opinion 在提案層就驗
Do not trust: 上面那行是待驗證的宣稱
Task: 自己跑相關測試；讀回填報告抽 3 檔（1 檔 10-Q 國內申報人、1 檔 20-F、1 檔台股）對原始 companyfacts／MOPS 手核三個點；
      確認沒有任何列的可用日取自 fetched_at；確認 company_id_for_ticker 沒被改；確認舊表 schema 不變
Boundaries: 不改 code、不 commit、不寫 Engine C 正式庫、不跑回填、不核准 pq2
```

## 4. Step 3.3 三題稽核區＋主題等權組＋邊緣判定（Z2，R1）

**改哪裡：** 新模組 `alpha/three_questions.py`（純函式，判定／取數分開，比照 `alpha/wipeout.py`）；`engine_c/checklist.py`（取數：歷史表、月營收、組成分價格）；`alpha/wipeout.py`（稀釋逐檔單一來源、trailing 窗；GC 讀新欄位）；主題等權組 ledger `library/private/alpha/theme_cohorts/<slug>.jsonl`（檔名沿用讀圖 ledger 的 `_slug` 慣例）與 `alpha/providers/theme_cohorts.py`、唯讀 CLI `python -m alpha theme-cohort`、`engine_b/todo.py`（`complete-theme-cohort` 與凍結 payload）；`briefing/alpha_view/`（read model 加 `three_questions` section）；邊緣判定函式（讀 `config/alpha_screen.json`＋`alpha/providers/market_normalization.py`，放在 `alpha/` 下，3.6 與 3.8 共用）。

**4.1 三題，每行都是 `{value, source, as_of, 口徑, rule}` 或 `absence_kind`（既有封閉字彙；需要新詞先登記，L16）：**

| 題 | 行 | 規則 | 缺席出口 |
|---|---|---|---|
| 會死嗎 | 四盞燈 | 既有 `wipeout_flags`。**稀釋（#14）**：逐檔**單一來源**——10-K／10-Q 國內申報人用 `shares_outstanding_cover`（分割調整到同一基準），其餘用 yfinance 快照序列，`inputs` 記來源；比較窗＝**最新一點 vs 距它 ≥365 天的最近一點**（trailing 一年，rule 字串同步改），不是整條序列頭尾。**going concern** 讀 `going_concern_opinion` 的生效紀錄（supersession 照 `live_observation_ids`）：`substantial_doubt`→紅、`no_substantial_doubt`→綠、`not_reviewed` 或無紀錄→灰 | 稀釋：窗不滿一年 → `insufficient_evidence`＋`colour_available_on`（**非美股保留這個有到期的等待**）；多股類／缺封面股數 → 退回 yfinance 單一來源或缺席，不加總。GC 無紀錄從 `capability_absent` 改 `not_yet_recorded`（欄位已存在，只是還沒人寫） |
| 已定價嗎 | ①自家歷史百分位 | **口徑由今天決定、整條序列同一口徑**：今天 TTM 營業利益 ≥0 且有同期淨負債 → EV/S；否則 P/S；口徑欄寫明。**今天那一點與歷史每一點用同一個函式算**（歷史表最新收盤×當期股數＋當期淨負債，÷ as-of 已 filed 的 TTM 營收），**不讀** `financial_snapshots.ev_revenue`。樣本頻率＝每個交易日；市值用 raw 收盤×當時股數。台股沒有營業利益 → 一律 P/S 並標口徑；台股沒有歷史股數來源 → 缺席 | 窗不滿 3 年：印實際窗長、`insufficient_evidence`（**剛上市也走這一個出口**）；敘事宣告 `history_not_comparable` → `inputs_incompatible`「自 <since> 起不可比」（宣告以參數傳入判定函式，取數仍在 Engine C）；**報價結算幣別 ≠ 報表幣別、或股數與價格不是同一種證券單位（ADR）→ `inputs_incompatible`**，寫明哪一種；非美非台（無歷史來源）→ `upstream_unavailable`「歷史不可得」（3A）；最後一點太舊 → 缺席並印 `days_since_last`（鮮度規則沿用 Engine C 既有快照鮮度判準，寫進 rule） |
| | ②主題等權組中位數 | 只認 `members[]` 成員資格；**本檔排除在自己的基準之外**；中位數只取與本檔同口徑、有值的成員並印 n；**只印，不比較、不算差** | 組未定義：`not_yet_recorded`「主題等權組未定義（pq2 [N]）」；不是任何組的成員：`not_yet_recorded`「不在任何主題等權組」；同口徑成員不足一半：`insufficient_evidence` |
| | ③相對組的 30／90 天漲幅 | 本檔 30／90 **個交易日**的調整後收盤報酬（當地幣別）− 成員同窗報酬的等權平均（本檔除外）；rule 寫明 | 同②；價格序列不足或太舊：`insufficient_evidence`＋`days_since_last` |
| 出現在數字裡了嗎 | 序列 | 依序取**第一個有 ≥2 點**的來源：**分部／產品線營收占比序列**（它最貼近敘事騎的那一層；今天每檔只有一點，所以今天不會被選中，但有第二個觀測時要優先用）→ 台股月營收（最近 12 個月 YoY 序列＋法定期限，標「法定期限，非實際公告日」）→ 10-Q 申報人的 EDGAR 季營收（最近 8 季）→ 20-F 的年度營收；分部／產品線占比只有一點時**另印一行當結構脈絡**（值＋觀測日），不佔序列位置。每行宣告實際用了哪個來源 | 都沒有：`upstream_unavailable`；只有一點：`insufficient_evidence` |

**4.2 主題等權組 ledger：** append-only、content-addressed id、`supersedes_id`；每筆必帶 `theme`、`members[]`（ticker＋company_id，registry 解析得到才收）、`reason`（含每個成員入選理由與排除了誰）、`decided_on`、`pq2_ref`。**寫入要綁住使用者的 go，不只驗編號存在**：比照 `ra_admission` 的凍結 payload——3.5 鑄 pq2 時把成分 spec 凍結進該編號的 payload 並記 digest；使用者 go 之後，唯一的寫入入口是一支 `complete-*` 型命令（例 `python -m engine_b.todo complete-theme-cohort <n>`），它讀**凍結的那份** spec、比對 digest、寫 ledger、以 `authority:theme_cohort;ref:<record id>` 結案——核准的東西＝寫進去的東西，bare `go` 拒收（同 `engine_c_observation`）。`python -m alpha theme-cohort` 只留唯讀（列出、查成員）。一檔屬於多組時②③逐組印。等權、成分變動即新紀錄。本 Step **只建機制、不寫任何一筆**。

**4.3 邊緣判定（#13）：** 讀 `config/alpha_screen.json` 的兩個數（AND）＋`market_normalization` 正規化市值（報價單位→結算幣別→USD）與分析師數；回 `edge ∈ {edge, not_edge, unmeasurable}`＋兩個輸入值＋缺哪一個＋理由碼（**不得用 `market_cap_above_max`／`analyst_count_above_max`**，殭屍 grep B 組）。取數在 materialize 時做一次、結果進 candidates artifact（§7）；**資本路徑（§9）只讀 artifact，不即時打 FX 或行情**。**不新增門檻、不調數字**；它只回答「算不算倍率候選」。

**怎麼驗：** 純函式測試每行每個缺席出口都會出現（L12：燈滅與燈綠不同形）；PIT 測試（造一檔在 T 之後才 filed 的營收，T 的百分位不得用到它）；TSM 型夾具（TWD 營收、USD ADR 價格）回 `inputs_incompatible`；「分部只有一點、但有 EDGAR 季營收」夾具走 EDGAR；稀釋 trailing 窗與非美股保留 `colour_available_on` 的測試；組 ledger：`complete-theme-cohort` 對編號不存在、型別不對、已 drop、凍結 spec 的 digest 不符、成員解析不到、重複 id 一律拒收，bare `go` 拒收；**稽核區沒有任何「門檻」「已定價／未定價」判定欄位**（測試斷言 section 裡沒有布林結論欄位）；邊緣判定對缺市值／缺覆蓋回 `unmeasurable`（不放行、不濾掉）。
真實資料試跑：73 檔三題每行的「有值／缺席（依 kind）」計數表寫進八欄——這就是 ROADMAP ③ 的第一次讀數；邊緣三態分布對 3.0 第 12 項。
sandbox impact review 五步（`python -m alpha theme-cohort` 唯讀子命令、`engine_b.todo complete-theme-cohort` 寫 private ledger——互動專用、不進任何無人值守 allowlist；OPERATIONS 補一列）。
**L11-6 ④：** 個股頁 wipeout 面板——稀釋改逐檔單一來源＋trailing 窗後，逐檔列「來源、窗長、比較的兩點、顏色前後」；任何一檔**從有色變灰**或**非美股失去 `colour_available_on`** 都要解釋。

## 5. Step 3.4 敘事 v2 契約＋敘事來源的語意 watch（Z2，R1 ＋ R2-a 常規 opt-in）

**改哪裡：** `alpha/narrative/contracts.py`（`RECORD_VERSION` 分支、slot 集合、placeholder 字彙、驗證）、`alpha/providers/briefs.py`（寫入端＋登記 hook）、`alpha/cli.py` 的 brief 入口（含 `--retract`）、`alpha/models/session_assessor.py`（`BRIEF_FRAME` 與 `_brief_frame` 的 `param_placeholders`／`_how_to_use`）、`briefing/alpha_view/builder.py`（`fill_brief`、`select_brief`）；
`engine_b/event_watch.py`（`_validate_semantic` 認 `brief:<brief_id>#<n>`；新喚醒目標 `wake_brief=<company_id>`；`expiry_class` 新類 `rewrite`，不鑄號；`wake_target()`／`watch_detail()`／`counters` 認 `wake_brief`；`add` CLI 加 `--wake-brief`）、`engine_b/todo.py`（`_collect_watch_expiry_rows` 排除 `rewrite`）、`engine_b/disproof.py`（「現行敘事」、`disproof_counts` 認敘事來源與連結項）、`engine_b/queue_segments.py`（新段 `narrative_rewrite`；**`classify_watch` 對 fired 先查 `wake_brief` 與 `brief:` 來源，歸到 `narrative_rewrite`，不得落到 `fired_hypothesis_check`**）、`webapp/materialize.py`（watches 頁的喚醒目標）、`audit/checks.py`（`check_expiry` 認 `rewrite` 的去處、QueueLiveness 的觸及待處置認 `brief:`〔今天只認 `thesis:`，約 811 行〕、Orphans 解析 `brief_id`）、`audit/sources.py`、`crons/heartbeat.py`（到期分類那一行）、`skills/research-drain/SKILL.md`（`narrative_rewrite` 的 consumer）、`scripts/retired_mechanism_grep.py`（keep-list 縮小）。

**怎麼改：**
1. **v1 不動**：`investor-brief/v1` 的 slot 集合、placeholder、`brief_id` 欄位集合原樣保留（id 依版本分支，比照讀圖 `_ID_FIELDS`／`_ID_FIELDS_V2`）；v1 的現行紀錄在候選板印「舊版，缺候選狀態」。
2. **v2 七格**（問題寫進新的 `BRIEF_FRAME_V2`，`do_not` 照舊風格）：`demand`（什麼在放量、誰在花錢）、`position`（坐在哪幾層／哪幾格、各占多少營收——**「出現在數字裡了嗎」的 placeholder 住這一格**）、`bottleneck`（為什麼卡在它——必須引用 `rides[]` 的讀圖結論；誰想殺它＝反向路徑）、`priced_in`（已定價嗎——**必須含 `{own_history_pctile}`**，組的兩行有值時必須一併引用）、`our_bet`（賭的是哪一件事、騎層還是插槽）、`what_must_be_true`（什麼必須為真、錯的訊號是什麼——**不得有價格或報酬**）、`when`（`{next_checkpoint_date}`）。
3. **v2 placeholder 字彙**：留 `price`、`analyst_count`、`next_checkpoint_date`、`ripeness`、`gap_closure`；拿掉 A1 列的九個 simple placeholder 與帶參數的 `{assumption:…}`、`{bet_assumption:…}`（v1 相容碼照留；它們的值來源已退役，§0.2）；新增三題稽核區的 placeholder（`own_history_pctile`、`own_history_basis`、`cohort_median`、`rel_return_30d`、`rel_return_90d`、`in_numbers_latest`、`in_numbers_as_of`；名稱可調，不得撞殭屍 grep）。
4. **結構化欄位**（全部進 v2 的 id 欄位集合）：
   - `rides[]`：`{node, unit, reading_id}`；寫入時：`reading_id` 是該（節點, 單位）的現行讀圖（`alpha/structure_reading/contracts.py::select_readings`＋`alpha/providers/structure_readings.py::reading_status_rows`）——**「現行」＝狀態 `current` 或 `stale_low`**（`stale_low` 只有低等級變動、不進重讀佇列，若不算現行，可開會被一個修不回來的狀態打掉）；`stale`、`expired` 不算。且**本公司在那份讀圖快照的供給側**（層：`supplies_to`／`develops` 進這個節點的 `co:*`；插槽：該插槽的供應商）。不在供給側 → 拒收並印它實際在哪一側。
   - `disproof[]`：每條 `{condition, check_frequency, action_48h, entities[], expires, source, link_source_ref?}`——L7 三件套；`entities` 至少一個 registry 解析得到的 `co:*`（預設帶本檔 company_id）；`expires` 必填、不得早於條件裡寫的日期；`source` 是 `self`、thesis claim id、thesis memo 條目或讀圖 id（指得回原文，L18）。**source 指向的條件已有在盯的 watch → 只記 `link_source_ref`（那筆 watch 的來源鍵，例 `reading:<reading_id>#n`、`thesis:<memo>#n`），不重登、也不記 watch id**——讀圖重讀或 memo 換版時舊 watch 會被收掉換新，watch id 會輪換，來源鍵不會；讀取端由來源鍵找當下在盯的 watch，**來源已不是現行（讀圖被 supersede、memo 條目消失）→ 候選板印「連結的反證來源已換版」並進 `narrative_rewrite`**。只有 `self` 與目前沒人盯的 thesis claim 才新登 `brief:<brief_id>#<n>`（比照 `register_reading_watches`）。
   - `answers`：`{priced_in: yes|no|unmeasurable, in_numbers: yes|no|unmeasurable}`；`unmeasurable` 只在對應稽核行全是缺席時允許；`yes`／`no` 時對應格（`priced_in`／`position`）必須含該題 placeholder（型別層強制，#5）。會死嗎不由人答。
   - `candidate_state`：`{state, watch_id?, reason?}`，`state ∈ {open, missing, priced_wait, pass}`（**`held` 不收**，#2）。`missing`／`priced_wait` 必帶 `watch_id`，那筆 watch 在寫入當下 `active`，且**必須是 `wake_brief=<本公司 company_id>` 的 watch**（kind 限 date／entity_filing_signal／related_entity_signal；寫敘事前先建好）——**不得指向 thesis／讀圖的語意 watch**（那些醒來走 thesis 複查或重讀，不會叫敘事重寫，語意也不同），**也不得指向任何 `brief:` 來源的 watch**（換版時會被 hook 收掉）；`pass` 必帶 `reason`；`open` 過第 5 點。
   - `history_not_comparable`（可選）：`{since, reason, source}`——§4.1 已定價①的「剛轉型」宣告。
   - `acknowledged_touched[]`（見第 6 點）。
5. **`open` 的寫入時前提（#2）**：①`rides[]` 至少一條、每條讀圖現行（`current`／`stale_low`）且 `kind ∈ {moat, volume}`；②兩個 `answers` 都有值；③本檔 thesis 與 `rides[]` 讀圖來源的語意 watch 中沒有「醒來待判」「觸及待處置」或「到期未判」的；本公司名下所有**未處置**的敘事來源 watch 都已在本版 `acknowledged_touched[]` 處置（第 6 點）。任一不過 → 拒收並印是哪一條。**邊緣門檻不在寫入時驗**（市值每天變）——由顯示端推導（§7）。寫入當下才成立的檢查**只放寫入端，不放 parse 路徑**（§13）。
6. **醒來／觸及／到期之後（INV-4、解除重寫死結、不得被換版或撤回吞掉）**：敘事來源的 watch（`brief:` 語意 watch 與 `wake_brief` watch）**醒來（fired）、被判觸及、或到期未判** → 進新佇列段 **`narrative_rewrite`**（consumer＝research-drain，skill 同 commit 補一段；audit QueueLiveness 認它），候選板印「敘事該重寫：<watch id> <醒來／觸及／到期未判>」。
   - **換版與撤回的 hook 不得收掉處於這三種狀態的 watch**；只有 `active`（沒醒、沒觸及、沒到期）的才照「換版收舊登新」收掉。
   - 下一次寫入（不論是否帶 `supersedes_id`、不論前一筆是否已撤回）必須在 `acknowledged_touched[]` 逐條處置**本公司名下所有**處於這三種狀態的敘事來源 watch——不是只看前一版。
   - 處置字彙對到 watch 既有的封閉收據字彙：`still_holds`（條件沒發生／判定無關 → 對應 watch 的 reactivate 或 not_touched 收據）、`thesis_changed`（判定觸及，敘事已據此改寫 → touched＋`handled`）、`retired`（條件不再適用 → consume，附理由）；hook 依處置寫對應收據收掉 watch。**不列就拒收**。
   - `check_expiry` 與 QueueLiveness 對 `rewrite` 類的「有去處」判準：該 watch 出現在 `narrative_rewrite` 段、且候選板 artifact 的該檔列帶著它。
7. **`wake_brief`（給 `missing`／`priced_wait` 用）**：`add_watch` 新增喚醒目標 `wake_brief=<company_id>`（與其他目標互斥）。**兩條路都要接**：①date watch 在 `until` 那天轉 **fired**——`classify_watch` 先查 `wake_brief`，歸到 `narrative_rewrite`（不得落到 `fired_hypothesis_check`）；②`expires` 過了 → `expiry_class=rewrite`，不鑄 pq2，同樣進 `narrative_rewrite`。`wake_target()` 回 `{kind: brief, ...}`，APP watches 頁照印。
8. **watch 歸屬函式（單一 SSOT，放 `engine_b/`）**：一家公司的 watch＝本公司 thesis 的 `thesis:` 來源＋現行敘事 `rides[]` 各讀圖的 `reading:` 來源＋**現行敘事 `disproof[].link_source_ref` 指向的來源**（包括沒騎的讀圖，例：COHR 連結 InP 讀圖的反證）＋本公司的 `brief:` 來源＋`wake_brief` 指向本公司的。**以來源歸屬，不以 `entities` 比對**（entities 記的是條件牽涉誰）；**`candidate_state.watch_id` 本身不構成歸屬**（否則「watch 必須歸屬本檔」的驗證是循環定義，ROADMAP ② 恆真）。第 4 點 `candidate_state`、第 5 點③、§7 顯示端重驗、§8 downside、§9 收據與 `--disproof-watch` 驗證都呼叫它。
9. **撤回**：`--retract` 沿用被撤那筆的 `record_version`；撤回 v2 觸發 hook，只收掉它登記的 `active` watch（第 6 點）。
   `disproof_counts`：連結項以被連結的那筆 watch 計為「在盯」，不另算、不重複算；敘事自己新登的照算。
10. **殭屍 grep**：v2 拿掉的 placeholder 只剩 v1 相容碼命中——keep-list 理由改寫成「v1 相容（legacy_key）」，不再需要的條目刪掉；「已列但不再命中」的腐壞條目為 0。

**怎麼驗：** v1 7 行 id 重算 7／7；v1 用 3.0 的固定 values 夾具跑 `fill_brief` 輸出逐字相同、原始 slot 文字＋placeholder 清單＋missing 清單相同；v2 拒收規則各一條會紅的測試（禁字、未知 placeholder、`{assumption:…}`、`priced_in` 缺 placeholder、`position` 缺 in_numbers placeholder 卻答 yes、`answers=unmeasurable` 但稽核行有值、disproof 缺 `entities`／缺 `expires`、`missing` 缺 watch_id／watch 不 active／watch 屬於別檔、`pass` 缺 reason、`open` 三前提各自不過、`held` 被拒、`rides[].reading_id` 不是現行、**本公司不在 `rides[]` 節點的供給側**、前一版有觸及 watch 但本版沒列 `acknowledged_touched`）；登記 hook（寫入即登記、換版收舊登新、同內容重跑不重複、**搬讀圖反證不產生第二筆 watch**、撤回 v2 收 active watch、撤回 v1 得 v1、**換版或撤回不收 fired／觸及／到期未判的 watch**、**撤回後重寫仍須處置它們**）；`missing` 指向 thesis／讀圖語意 watch、前一版 `brief:` watch、別家的 `wake_brief` → 拒收；**`wake_brief` date watch 到 `until` 轉 fired 後進 `narrative_rewrite`、不進 `fired_hypothesis_check`**；到期後 `todo sync` **不鑄** `watch_decision` 且 `check_expiry` PASS；`stale_low` 的讀圖可以騎、`stale` 不行；連結來源被 supersede → 候選板該檔進 `narrative_rewrite`；`narrative_rewrite` 段有 consumer（QueueLiveness PASS）；`disproof_counts` 與心跳「反證在盯／未盯」認得敘事來源；audit Orphans 解析得到 `brief_id`。
**L11-6 ④：** 真實 registry——`event_watch counters` 的 `semantic_active` 與 3.0 相同（還沒有 v2 敘事）；既有 thesis／讀圖來源的 watch 的 `expiry_class` 一筆都沒變（逐筆比對 3.0 第 7 項）。

**R2-a（常規 opt-in）WORK_REQUEST：**
```
WORK_REQUEST（R2-a，Phase 3 Step 3.4）
Target: 3.4 的 commit；alpha/narrative/contracts.py、alpha/providers/briefs.py、engine_b/event_watch.py、engine_b/todo.py、engine_b/disproof.py、engine_b/queue_segments.py、audit/checks.py
Claimed acceptance: v1 id 7／7 不變；v2 拒收規則全有會紅的測試；open 前提寫入時驗；disproof 寫入即登記 brief: 來源且已在盯的只以來源鍵連結；wake_brief 到點 fired 與到期兩條路都進 narrative_rewrite、不鑄 pq2、不進假設對照；醒來／觸及／到期未判的 watch 不被換版或撤回吞掉、重寫須逐條處置；缺 X 的 watch 只能是本公司的 wake_brief；held 不可宣告
Do not trust: 上面那行是待驗證的宣稱
Task: 自己跑相關測試與 audit invariants；用暫存目錄造 10 筆應拒收的 v2 spec 與 1 筆應收的，確認結果；
      確認 v2 的 id 欄位集合包含 rides／disproof／answers／candidate_state／history_not_comparable／acknowledged_touched、v1 的沒有；
      確認既有 thesis／reading 來源 watch 的 expiry_class 不變；確認沒有任何 code path 會為 v1 紀錄補寫候選狀態；殭屍 grep 九組三個 0 且 keep-list 無腐壞條目
Boundaries: 不改 code、不 commit、不寫真實 ledger 或 event_watches.json、不核准 pq2
```

## 6. Step 3.5 研究：v2 敘事四份＋兩類 pq2（**強模型、互動 session**；研究，不是開發）

**強模型貼這段（執行者是便宜模型時印給使用者）：**
```
讀 docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md §6，做 Step 3.5：
用 v2 重寫 AXTI、COHR、LITE 三份短評、寫 SIVE.ST 第一份，每份宣告候選狀態；提主題等權組與 going concern 的 pq2。完成後更新進度表、commit、push。
```

**寫 ledger 與 `event_watches.json` 前取得互動 writer lock（`scripts/writer_guard.py`，§0.5）**。

1. 每檔先跑：`python -m alpha research <T>` 的 packet（`brief_frame` 已是 v2）、`python -m query.structure <node> --unit <unit> --quotes`（它騎的每一格）、三題稽核區（3.3）、邊緣判定（3.3）。
2. **寫四份 v2**（AXTI、COHR、LITE、SIVE.ST），`supersedes_id` 指舊 v1（SIVE.ST 沒有舊版）。
   - `rides[]`：只能騎**本公司在供給側**的現行讀圖。現況（§0.2，寫之前重查）：AXTI → `mat:inp_substrate`（層、volume）；**COHR、LITE、Sivers → `tech:cw_dfb_laser`（層、volume）可騎**（COHR、LITE 在 InP 基板是需求側，不能騎它）；Sivers 的兩份插槽讀圖是 `undecided`，騎它們就不能宣告 `open`。**騎哪一格、宣告什麼狀態由寫的人判斷，本 plan 不預設**。
   - `disproof[]`：從該檔 thesis 引用的 claim 反證（Phase 1 #1：AXT 11、COHR 12、Sivers 16 條）與讀圖反證中挑**這份敘事真的依賴的**；已在盯的只以來源鍵連結（`link_source_ref`），沒人盯的才新登；沒被引用的不搬（#8）。
   - `answers`：照稽核區實際印出來的東西答；組未定義時 `priced_in` 仍要引用自家歷史那一行（或它的缺席）。
   - `missing`／`priced_wait` 的 watch：先用 `python -m engine_b.event_watch add --wake-brief <company_id> …` 建好（date：`until`＝你預計補上 X 的日子、`expires` 晚於它；或 entity_filing_signal／related_entity_signal：等某家公司出新文件），再寫敘事。**不得指向 thesis／讀圖的語意 watch**（§5 第 4 點）。
   - **COHR、LITE 非邊緣（#13）**：敘事照寫；候選板會把它們放進「非倍率候選」，不論宣告什麼。
3. **提 pq2（掛號後在 HUMAN SUMMARY 列出，使用者在場可當場 go；接著做下一件，不停）：**
   - `manual`：主題等權組第一版成分（theme＝`config/sector_anchors.json` 的現行題材；成員要求 registry 解析得到；每個成員入選理由一句、排除了誰與為什麼；**大公司是否入組要明寫理由**——決定紀錄 §4.2「主題整體漲三倍時一檔兩倍是輸」）。成分 spec 在鑄號時凍結進 pq2 payload（§4.2）；go 後由收到 go 的 session 跑 `python -m engine_b.todo complete-theme-cohort <n>` 寫入並結案。
   - `engine_c_observation`：AXTI、COHR、LITE、SIVE.ST **與 IQE.L**（逐字已核對、`alpha/wipeout.py` 點名的第一個案例）的 `going_concern_opinion`（讀最近一份年報審計意見，逐字引文＋頁碼；非英語照原文）。流程：`python -m engine_c.set_manual_field …` 鑄提案 → `python -m engine_b.todo sync` 取編號 → 使用者核准後 `python -m engine_b.todo complete-observation <n>`（**bare `go` 會被拒**）。
4. **工具毛病＝回頭修 3.3／3.4，記偏差**（比照 Phase 2 偏差 #7–#9）。
5. 收據：`docs/reports/2026-09-2x-phase3-step35-narratives.md`——每份的 `brief_id`、騎的格與供給側證據、候選狀態與它指的 watch、搬進來的反證與出處（新登／連結各幾條）、兩類 pq2 編號、首屏前後對照（對 3.0 第 10 項）、邊緣判定。
6. **四份的候選狀態沒有預期值**。全部是 `missing` 就照實寫——**不得為了讓候選板非空而放寬任何前提**（硬約束 7）。
**L11-6 ④：** 真實 registry——`event_watch counters` 的 `semantic_active` 增量必須＝四份 `disproof[]` 中「新登」的條數（連結的不增加），`wake_brief` 計數增量＝`missing`／`priced_wait` 的份數；否則就是重複登記或漏登。

## 7. Step 3.6 候選狀態推導與候選板＋心跳（Z2，R1）

**改哪裡：** 新的共用函式（位置先對 `tests/test_layer_separation.py` 的 import 規則選不違反的層，理由寫八欄；預設持股解析放 `portfolio/`、候選狀態推導放 `alpha/providers/`，**不放 alpha 核心**）：
- **持股身分解析**（Sheet 列 → company_id：先用 Sheet 列上的 company_id／`neo4j_id`，再經 `identity/execution.py` 的反向別名〔FRA:2DG→SIVE.ST〕，再查 registry；解析不到列進計數、不猜；`bucket=CASH` 的列不算「解析不到」）。**`engine_b/cli.py::_held` 改呼叫這一段身分解析，但保留它自己的語意**——含 beta 持股（它餵 pq1 排序的「持股關聯」鍵）與 Sheet 讀不到時 exit 2 的 fail-closed；**不得用排除 beta 的版本取代它**（會改變 pq1 排序與 daily triage）。
- **候選板用的「已持有」**＝身分解析＋**股數 > 0**（空列、賣光後留下的列不算）＋以 `risk/hard_caps.py` 匯出的公開判別函式排除 beta（匯出本身是 #17 授權的純重構：只匯出、行為不變、既有硬擋測試全綠）。
- **候選狀態推導**；`webapp/contracts.py`（新 kind `candidates`）、`webapp/materialize.py`（`--candidates`；持股讀一次、像 `readings_context` 一樣注入 candidates 與 `materialize_many`）、`webapp/__main__.py`（`_STATE_FLAGS`）、`webapp/api.py`（路由與 `_STATE_NOTES`）、`webapp/static/app.js`（新頁；候選板 held 列連到個股頁，positions 頁加連結到候選板 held 組）、`crons/daily_task.py`＋`tests/test_daily_task.py`、`crons/heartbeat.py`、`skills/alpha-status/SKILL.md`、`skills/daily-brief/SKILL.md`＋`python scripts/sync_agent_skills.py`。
（`hard_caps` 的公開判別函式在 3.6 匯出（#17）；3.8 沿用，R2-b 一併審。）

**怎麼改：**
1. **候選狀態推導（顯示端，每天重算，可重建的 derived cache；候選板、心跳、個股頁、收據共用一個函式）**，回傳 `{declared, derived, preconditions[], edge, held_source}`——**不只回最後一個值**：
   - Sheet 持有（alpha、股數 > 0，經持股解析）→ `derived=held`，`declared` 照留；Sheet 有、敘事沒有 → 「已持有、缺敘事」。
   - **Sheet 讀不到**：整板加一行「持股未讀到，已持有判定暫停（`upstream_unavailable`）」；held 組印缺席；其餘每一列照印敘事宣告，**但標「持股未驗」**——它們可能其實已持有，所以不得宣稱「不是已持有」，也不得把宣告當成 held 的替代。
   - 否則取現行 v2 敘事的宣告；`open` 每天重驗：①`rides[]` 讀圖仍現行（`current`／`stale_low`，未 `stale`、未過 `expires`）且 kind 仍 moat／volume；②`answers` 對應的稽核行沒有從有值變全缺席；③**§5 第 8 點歸屬函式給出的全部 watch**（本檔 thesis、`rides[]` 讀圖、連結的來源、現行敘事自己的）沒有醒來待判、觸及待處置或到期未判；④連結的反證來源仍是現行——破掉印「可開（前提失效：…）」。
   - **邊緣（#13）**：`not_edge` → 「非倍率候選」組（宣告 `open` 也不算可開）；`unmeasurable` → 「邊緣無法量」組。
   - **連結來源換版（R2-a N1，自 3.4 移入，偏差 14）**：現行 v2 敘事任一 `disproof[].link_source_ref` 已沒有 active／fired 的 watch（讀圖重讀收掉換新、memo 換版）→ 不論宣告哪一態都列「敘事該重寫：連結 <ref> 已換版」，並計進 `narrative_rewrite`（佇列段、audit QueueLiveness、心跳用同一個判定）；`open` 另失效（前提③）。
   - **`history_not_comparable`（R2-a N3）**：敘事宣告的「歷史不可比」要傳進三題讀取端（寫入端驗 unmeasurable 時、候選推導、3.7 稽核區），今天沒有人讀。
   - `missing`／`priced_wait` 的 watch 已不 active → 「缺 X（watch 已 <狀態>，該重寫）」；v1 現行 → 「舊版，缺候選狀態」；沒有敘事的 → 不上板，**計數另印「無敘事 N」**。
   - **滯留天數**：沿 `supersedes` 鏈往回，取連續宣告同一 state（`missing`／`priced_wait` 另要求同一 `watch_id`）的最早一筆 `created_at`——同 state 重寫不歸零。
2. **candidates artifact** 除上板的列，另帶 **73 檔的三題與四盞燈 rollup**（有值／依 kind 的缺席計數）與邊緣三態計數——心跳段 2 與段 4 只讀這一份（心跳零網路、只經 `_load_state`）。
3. **頁面**：五組（可開／缺 X／已定價等回落／不要／已持有）＋附組（非倍率候選、邊緣無法量、舊版、前提失效）；**組內按 ticker 字母**；每列印騎的讀圖判讀、三題三個字（§8 第 1 點）、邊緣判定與兩個輸入值、在等的 watch id 與到期、滯留天數。
4. **心跳**：段 2 以「候選：可開 N（最老 d 天）｜缺 X N（最老 d 天）｜等回落 N（最老 d 天）｜不要 N｜已持有 N｜非倍率候選 N｜邊緣無法量 N｜舊版 N｜前提失效 N｜無敘事 N」取代 `_CANDIDATE_BOARD_ABSENCE` 那行——**最老滯留逐狀態各印**（AGENTS「每個候選狀態的檔數與最老滯留天數」；一個全域值會被「不要」長期霸占）；`_PRICED_IN_ABSENCE` 那行換成「三題（73 檔）：已定價① 有值 N／缺席 M｜出現在數字裡 有值 N／缺席 M｜會死嗎 四盞非灰 N」——**措辭只數有值與缺席，不得讀成結論**；段 4 的 `_WIPEOUT_ROLLUP_ABSENCE` 改讀 rollup，「賭注帳／量的候選／要幾倍」那一行刪除並在程式註解寫明退役理由；較昨 diff 加 `candidate.*` 封閉鍵（每個組一個）。**0 也印**；候選板 artifact 讀不到印 `upstream_unavailable`。
5. `webapp status` 列得出 `candidates`。

**怎麼驗：** 推導測試（FRA:2DG 夾具應為 held；NVDA〔beta〕不得是 held；股數 0 的列不是 held；CASH 列不進「解析不到」；Sheet 讀不到時整板帶「持股未驗」、held 組缺席；**pq1 排序對 3.0 記下的 lead 清單逐位不變、daily triage 在 Sheet 讀不到時照舊 exit 2**（`_held` 語意沒變）；`hard_caps` 匯出後既有硬擋測試全綠；前提失效三種各一條，其中一條是**現行敘事自己的反證被觸及**；非邊緣宣告 open 落「非倍率候選」；邊緣無法量；watch 失效；v1 舊版；無敘事計數；同 state 重寫滯留不歸零）；`tests/test_webapp_request_path.py` 的四份路由清單加 `/api/v1/candidates`（含斷網與 405），`STATE_KINDS` 相等斷言、`_STATE_NOTES`、`_STATE_FLAGS` 同步，給 candidates 一個 fake payload（比照 `fake_positions_payload`）；心跳封閉鍵相等斷言更新；daily `DAILY_STEPS` 逐項相等測試同 commit 改；headless Edge 實際渲染候選板與 positions 連結（`reference_headless_edge_app_check`）。
**L11-6 ④：** 心跳的較昨 diff——新鍵第一天沒有昨天值，要印「首日」而不是把全部算成變動；拿 3.0 的心跳檔當昨天試跑。
sandbox impact review（daily 旗標）；**05:30 前 push**。

## 8. Step 3.7 個股頁：首屏、稽核區、readiness、面板殘留（Z2，R1）

**改哪裡：** `briefing/analyst_view/contracts.py`（`CORE_PANELS`、`OPTIONAL_PANELS`）、`briefing/analyst_view/compose.py`、`briefing/alpha_view/builder.py`（稽核區、`bet` 純文字、downside）、鏈段所在層（第 4 點二擇一）、`webapp/materialize.py`、`webapp/static/app.js`。

1. **首屏**：短評之後一行候選狀態（§7 推導的 `derived`）＋三題三個字：會死嗎＝四盞燈的最差色與灰燈數（「紅」「黃」「綠」「灰 N」，燈不是數字）；已定價嗎／出現在數字裡＝敘事宣告的「是／否／無法量」，v1 或無敘事印「未答」。
2. **稽核區**：三題各行 `{value, source, as_of, 口徑, rule}` 或缺席 kind 的中文；讀圖逐字（沿用讀圖面板）。
3. **readiness**：`CORE_PANELS` → `headline`、`brief`、`argument`、`research`、`readings`、`wipeout`；`fundamental`、`bet` 留選配。**readings 升核心就是 Phase 0 偏差 #16「review_required 的路」的接回**：讀圖面板在讀圖 stale 時自己是 `review_required`，readiness 因此變 `ready_with_flags`。**讀圖面板的狀態只由讀圖對圖決定，不把 `refresh.overall` 餵進去**（`refresh=review_required` 今天全是退役估值鏈殘留，§0.2）。
   ⚠ 升核心後，沒有讀圖的公司（今天約 63 檔）多一個未 settled 的 blocker，它餵 research-drain 段 5 的「每檔閉環」——**同 commit 在 `skills/research-drain/SKILL.md` 段 5 補一條路線**：讀圖缺席的 blocker 的下一步是「寫這家公司所在層／格的讀圖（強模型、研究）」或由走圖第 1 型排入；不得為了讓閉環收斂而把讀圖缺席標成 settled（「刻意不主張」只能來自 Abstention 紀錄）。
4. **argument 鏈段**：只改**需求錨的來源**——改取敘事 `rides[]` 讀圖的需求側（無 v2 敘事時用該公司連到的節點的現行讀圖，沿用 2.7 的組法）；鏈段的邊照舊來自 `get_company_structural_context`。組在哪一層二擇一、理由寫八欄：(a) `fetch_alpha_investment_view` 加讀圖注入參數，materialize 一次載入後傳入，builder 組鏈段；(b) 鏈段改在 compose 用注入輸入組句，比照讀圖面板列為 `INJECTED_PANELS` 例外。**不得讓 briefing import webapp，也不得每檔各自重載一次圖**。`get_bottlenecks` **不退役**（§0.3）；標題改成使用者看得懂的一句（執行者定，寫八欄）。
5. **downside**：每條反證連到它的 watch id（ROADMAP 個股頁「downside 每條反證連到 watch」）——用 §5 第 8 點的歸屬函式；沒有 watch 的反證印「未盯」。
6. **`bet`**：純文字——`our_bet` 格＋`rides[]` 的單位＋`what_must_be_true`；沒有任何價格。

**怎麼驗：** readiness 73 檔前後對照表（每檔 blocked／ready 變化逐檔指得出是哪個面板）；鏈段改寫後逐檔比對 3.0 記下的 chain 段，**變成 missing 的逐檔列出並改成明示缺席**；兩條方向相反的測試：讀圖節點上的邊變動 → 讀圖 stale → readiness `ready_with_flags`；只有 `operating_assumption` 的 `review_required` 時讀圖面板狀態不變；核心面板文字 digest 只在預期處變（brief 對 v2 四檔、argument 鏈段、readings 升核心）；`python -m audit invariants --only PointInTime` 照 PASS（探針仍在）；headless Edge 渲染一檔 v2（AXTI）與一檔無敘事（例 AAOI）。
**L11-6 ④：** 3.0 記下的 `ready`／`ready_with_flags` 清單——readings 升核心後，沒有讀圖的公司會不會從 ready 掉成 blocked；逐檔看，變化必須指得出原因。

## 9. Step 3.8 `record_trade.py` 研究收據（Z2，R1 ＋ R2-b 常規 opt-in；資本路徑；**使用者 2026-09-29 預先授權，#16**）

**改哪裡：** `scripts/record_trade.py`、`risk/hard_caps.py`（匯出公開判別函式，例 `instrument_for(symbol)`／`is_beta_symbol(symbol)`，取代私有 `_instrument_for` 的外部用法；若 3.6 已匯出則沿用）、測試 `tests/test_record_trade*.py`、`docs/OPERATIONS.md` 成交紀錄段（含首次建倉先手動建 Sheet 列）。

**怎麼改（#7、A4）：**
1. alpha／beta 判別只呼叫 `hard_caps` 的公開函式（**賣出路徑也要判**——今天 `check_trade_hard_caps` 在 sell 時第一步就 return，不能靠 verdict 間接取得）；Sheet symbol → company_id 用 §7 的**持股解析函式**（FRA:2DG→SIVE.ST），兩段都解析不到＝alpha 且 `narrative: unresolved`（不猜）。
2. **alpha 買進**：`--why "<一句>"` 必填；自動組 `research_receipt`：
   - `declared`：現行 v2 敘事的 `brief_id`（已是內容雜湊，不另算）、`candidate_state`、`answers`；`rides[]` 的 `reading_id` 與各讀圖**寫入當時**的 `result_digest`（從 ledger 讀）；在盯的 watch id（§5 第 8 點歸屬函式，讀 registry 檔）。
   - `derived`：**讀當天的 candidates artifact**（§7 推導的結果：前提重驗、失效原因、邊緣判定、三題稽核各行）並記它的 `as_of`；成交前由 Sheet 推得的持有狀態；`--log-only`（Sheet 已是成交後狀態）時標明。
   - **資本路徑不連 Neo4j、不即時打行情或 FX**：讀圖 staleness 要 Neo4j、邊緣判定要 FX，這兩者在 materialize 時已算好。artifact 缺席或 `as_of` 不是今天 → 收據照記 `derived: upstream_unavailable`＋原因，**不擋成交**（A3 不得替 A5 做決定，§0 第 13 條）。
   - **沒有現行 v2 敘事 → fail closed**（exit code 與硬擋、輸入錯誤各自區分）；`--no-narrative-override "<理由>"` 放行，收據寫 `narrative: absent`（或 `legacy_v1`——v1 沒有候選狀態，視同缺 v2）＋理由。
3. **alpha 賣出**：`--why` 必填；`--disproof-watch <id>`（可選，給了就用歸屬函式驗它屬於這檔）；附 `declared`／`derived`。缺 `--why` fail closed。
4. **5% 硬擋的 `--override --reason` 原樣不動**，既有「`--reason` 無 `--override` 就 exit 2」的守門保留；**兩個放行互不放行**：缺敘事的放行不會放行超過 5% 的買進，反之亦然。
5. **beta**：不需要收據，行為與今天相同。
6. 收據進 `trade_log.jsonl` 那一筆事件的 `research_receipt` key（不另開檔、不與 `hard_cap_check` 混）；**dry-run 也組收據並印出**；順序：locate（既有，必須恰好 1 列）→ 硬擋 → 收據。

**怎麼驗：** 測試全用暫存 log 與假 Sheet：FRA:2DG 買進找得到 SIVE.ST 的 v2 敘事且收據欄位齊全；無敘事 → fail closed、`--no-narrative-override` 後收據記 absent；v1 → 同無敘事並記 legacy_v1；**缺敘事放行不連帶放行 >5%**、**硬擋 override 不連帶放行缺敘事**；賣出缺 `--why` → fail closed；`--disproof-watch` 不屬於這檔 → 拒收（來源歸屬本檔但 entities 不含本檔 → 收；entities 含本檔但來源不歸屬 → 拒）；beta 不要求收據；`--log-only` 的 `derived` 標成交後；candidates artifact 缺席或過期 → 收據記 `upstream_unavailable`、成交照走；「registry 解析得到但沒有敘事的 alpha」用夾具測（真實 Sheet 沒有這種列）。**真實試跑只做 dry-run（不帶 `--apply`、不帶 `--log-only`）**，用 Sheet 裡確實存在的列：FRA:2DG（v2 敘事）、TYO:7803（registry 解析不到的 alpha → `narrative: unresolved`）、QQQ（beta），輸出貼八欄。
**L11-6 ④：** 今天沒有任何 production reader 讀 trade_log 事件內容（只有 `_already_recorded` 與兩條讀真實 log 的測試）——①那兩條測試在新欄位出現後照綠；②`tests/test_record_trade.py` 中因新規則改期望值的測試逐條列出；③舊事件缺 `research_receipt` 要被未來讀取端當 absence 而不是錯誤——寫進 §14 給 Phase 5。`trade_log.jsonl` sha256 不變。

**R2-b（常規 opt-in）WORK_REQUEST：**
```
WORK_REQUEST（R2-b，Phase 3 Step 3.8）
Target: 3.8 的 commit；scripts/record_trade.py、risk/hard_caps.py 與其測試、持股解析與 watch 歸屬函式
Claimed acceptance: alpha 買進缺 v2 敘事 fail closed、--no-narrative-override 附理由留收據；兩種放行互不放行；賣出缺 --why fail closed；beta 不變；硬擋順序與守門不變；research_receipt 分 declared／derived；FRA:2DG 解析到 SIVE.ST
Do not trust: 上面那行是待驗證的宣稱
Task: 自己跑測試；對 FRA:2DG（有 v2）、TYO:7803（無敘事）、QQQ（beta）各做一次 dry-run 並核對輸出；讀 diff 確認沒有任何路徑在 dry-run 寫 Sheet 或 trade_log；
      確認本 Step 新增的 alpha 判別呼叫都走 hard_caps 的公開函式；確認 3.6 對 risk/hard_caps.py 的改動只是匯出（git diff 該檔，硬擋判定邏輯逐行不變、既有硬擋測試全綠）；
      確認收據路徑沒有 Neo4j 連線或對外網路呼叫；library/trades/trade_log.jsonl sha256 ＝ baseline
Boundaries: 不改 code、不 commit、不帶 --apply、不動 Sheet、不核准 pq2
```

## 10. Step 3.9 新管線 full chain 測試（Z1，R1）

1. **新增**夾具版 full chain（新檔）：夾具圖 → 讀圖（暫存 ledger）→ v2 敘事（暫存 ledger、disproof 自動登記到暫存 watch 檔）→ 三題稽核區（暫存 Engine C）→ 候選狀態推導與 candidates artifact → 個股頁 compose → **心跳段 2 讀到候選計數與三題 rollup**（Phase 0 偏差 #29 的鏈）→ 收據 dry-run。每一段斷言**產出到了下一段手上**（L13），並有一條「中間一段缺席時，下一段印缺席而不是空白」的測試。
2. **現行 `tests/test_full_chain_acceptance.py` 的 12 條活判準保留**（原檔或搬到新檔，逐條寫出去向；§0 第 7 條）；它是本機真 runtime 整合測試，不得整檔替換成夾具版。skip 條件若仍依賴凍結的 `decision_lab.db`／COHR assumptions ledger，改成不依賴，或寫明為何仍需要。
**L11-6 ④：** 真 runtime 那份在本機仍跑得起來（27 passed 對 3.0）；拿掉或搬走的斷言逐條列。

## 11. 驗收數的是哪一層（completion gate 第九項）

| 驗收 | 數的東西 | 層 |
|---|---|---|
| ROADMAP ① 有敘事的檔 100% 有候選狀態 | 現行敘事是 v2 的檔數／有現行敘事的檔數（3.5 後預期 4／4；v1 現行 0） | 敘事 |
| ROADMAP ② 缺 X 100% 指向活的 watch | `missing`／`priced_wait` 敘事中，watch 為 active **且歸屬本檔**（§5 第 8 點）的份數／份數 | 敘事 × 等待 registry |
| ROADMAP ③ 三題每題對每檔有值或有 `absence_kind` | 73 檔 × 三題（逐行）中「有值或有 kind」的格數／總格數（應 100%）＋依 kind 的分布 | 敘事（個股頁稽核區；Engine C 觀測的投影） |
| ROADMAP ④ 歸零旗標四盞有值的檔數 | 每盞非灰的檔數：3.0 基準 → 結案（稀釋預期國內申報人上升；GC 取決於 pq2 是否 complete，照實寫） | 敘事（個股頁稽核區） |
| ROADMAP ⑤ 新成交事件 100% 帶收據 | 3.8 之後新增的 alpha 事件中帶 `research_receipt` 的筆數／筆數（**不數 `hard_cap_check`**）；0 筆時寫「已交付、未生效」＋測試證明 | 追蹤表（trade_log） |
| A1 v1 不變 | v1 7 行 id 重算 7／7 | 敘事 |
| 反證登記 | 敘事 `disproof[]` 總條數＝新登 `brief:` watch 數＋連結既有 watch 數；`semantic_active` 增量＝新登數 | 等待 registry |
| A2 主題等權組 | ledger 紀錄數（pq2 go 了才 ≥1；否則 0 並印缺席） | 機制存在與否 |
| A6 b | 走圖第 5 型 `unresolved_names` 12 → 10 | 圖（走圖問句） |
| A5、A6 a／c、A7、3.6 | 符號與 kind 存在與否、拒收測試 | 機制存在與否 |

**沒有任何一個是「幾檔通過某個 filter」。「可開」與「非倍率候選」的檔數只印不驗收。**

## 12. Phase 3 結案（completion gate：historical-failure-matrix §9 八項 ＋ 第九項）

1. `pytest -q` 全綠；測試檔數差＝新增－退役（逐檔）；**函式層級**以 3.0 名單比對，拿掉的每一個寫去向。
2. `python -m audit invariants` 綠。
3. 無未解釋語意 diff：心跳與 3.0 逐行對照；個股頁核心面板 digest 只在 3.7 預期處變。
4. 無新 dual authority：候選狀態只有一個推導函式（候選板、心跳、個股頁、收據共用）；持股身分解析只有一個函式（候選板、收據、`engine_b/cli.py::_held` 共用；`_held` 保留含 beta 與 fail-closed 的語意）；watch 歸屬只有一個函式；**本 Phase 新增的 alpha 判別呼叫全走 `hard_caps` 公開函式**（`risk/snapshot.py` 那份是既有、列 §14）；三題取數只在 Engine C、判定只在 `alpha/three_questions.py`／`alpha/wipeout.py`；台股營收只住 `monthly_revenue_observations`；主題等權組只有一本 ledger；lead 與走圖用同一份 ticker resolver。
5. 無 silent drop：候選板沒有敘事的檔計數、v1 舊版計數、前提失效計數、邊緣無法量計數、持股解析不到計數；三題每個缺席有 kind；回填報告列出每檔缺什麼。
6. Point-in-time：歷史表的 `filed`／`disclosure_deadline` 測試（**audit PointInTime 只查圖，不是歷史表的證據**）；`audit PointInTime` PASS（探針仍在）。
7. lifecycle 可達：敘事來源的語意 watch 與 `wake_brief` 的觸及／到期有 consumer（`narrative_rewrite` 段＋research-drain）；`QueueLiveness`、`check_expiry` 綠。
8. executable protection：v2 拒收規則、`open` 前提、`held` 不可宣告、供給側檢查、重寫須處置觸及、收據 fail closed、兩種放行互不放行、三題無門檻斷言，各有會紅的測試；殭屍 grep 九組三個 0。
9. 驗收數的是 §11 的層。

**另核對：** 舊 Decision Store 三個 `*.db` sha256 與 `live_choices` ＝ 3.0；`trade_log.jsonl` 除了使用者真實成交外不變；`git diff <3.0> HEAD -- AGENTS.md` 為空；`identity/registry.py::company_id_for_ticker` 未改。

closeout 報告存 `docs/reports/2026-09-2x-phase3-closeout.md`，附「本 Phase 執行中發現、Phase 4 要決定的問題」（§14 種子＋執行中新增）。

### 結案 R2（使用者已常規 opt-in；執行者不必再問）

```
WORK_REQUEST（R2，Phase 3 結案）
Target: master 最新 commit；docs/reports/…-phase3-baseline.md、…-phase3-step35-narratives.md、…-phase3-closeout.md；
        docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md（§0.4 amendment、§0.6 偏差、§0.7 P0 處置）
Claimed acceptance: Phase 3 completion gate 九項全過、ROADMAP Phase 3 驗收①–⑤成立（見 closeout）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python -m pytest -q；python -m audit invariants；測試函式層級增刪自己比（3.0 commit 起），抽 5 個拿掉的函式確認去向成立
  2. 敘事 ledger：v1 行 id 重算＝檔內值；每份現行 v2 的 rides[] 讀圖當時現行且本公司在供給側；disproof[] 每條不是對應一筆 brief: watch 就是連結到既有 watch（無重複登記）；
     missing／priced_wait 的 watch 現在 active 且歸屬本檔；自己造 5 個應拒收的 v2 spec 確認被拒
  3. 三題：73 檔 × 三題逐行「有值或有 kind」＝100%；抽 3 檔（國內申報人、20-F、台股）對歷史表手算自家百分位；確認沒有任何門檻或已定價布林欄位；
     PIT：任選一檔一個過去日期，確認只用到當時已 filed／已過法定期限的營收
  4. python -m webapp status 有 candidates；候選板組內按 ticker、無分數；FRA:2DG 是 held、beta 不是；非邊緣不在可開組；心跳段 2 候選與三題兩行照印（含 0）
  5. 個股頁：CORE_PANELS 含 readings、不含 fundamental；argument 鏈段不經 get_bottlenecks 取錨（get_bottlenecks 與 PointInTime 探針仍在）；首屏沒有任何價格報酬；downside 反證連 watch
  6. record_trade.py：對 FRA:2DG、TYO:7803、QQQ 各 dry-run 一次；trade_log.jsonl 與 baseline 的差只有使用者真實成交
  7. python scripts/retired_mechanism_grep.py：九組三個 0、keep-list 無腐壞；code／skills／tests／config／static 無「籃子」「basket」新命中
  8. library/private/decision_lab/*.db 的 sha256 與 live_choices ＝ baseline；git diff <3.0> HEAD -- AGENTS.md 為空；company_id_for_ticker 未改
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不寫任何 ledger
```

### 結案之後：停，不要開 Phase 4

R2 回 GO 後：ROADMAP Phase 3 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。然後 **`AWAITING_HUMAN`**：Phase 4 還沒有 plan。
HUMAN SUMMARY 的「下一步」逐字印 `docs/plans/README.md`「每個 Phase 開工前要有一份 plan」那段指令。

## 13. 已知陷阱

- **殭屍 grep B 組掃「籃子」「basket」**（code／skills／tests／config／static）：主題籃子一律「主題等權組」／`theme_cohort`；候選板 kind 叫 `candidates`，**不得**沿用已退役的 `basket` kind。C 組掃 `sell_side_target`，E 組掃 `payoff\b`——v2 拿掉它們後 keep-list 要同 commit 縮小，否則「已列但不再命中」會讓驗收紅。
- **短評 id 是 content-addressed**：v2 的新欄位只能加在 v2 的 id 欄位集合；動到 v1 的集合，7 行舊 id 全變。寫入當下才成立的檢查（watch active、讀圖現行、稽核行有值）**只放寫入端**，不放 parse 路徑——否則舊紀錄日後會變成解析失敗、從候選板安靜消失。
- **題目變了的格換 key**：`supply`→`position`、`market_view`→`priced_in`、`if_right_if_wrong`→`what_must_be_true`。
- **語意 watch 的來源與喚醒目標是封閉的**：`_validate_semantic` 只收 `thesis:`／`reading:`，`add_watch` 目標恰好擇一，`expiry_class` 其餘一律鑄 pq2——3.4 不改這三處，敘事的 watch 要嘛登記失敗、要嘛到期鑄出一堆 `watch_decision`。
- **date watch 到 `until` 是 fired、不是 expired**：只接到期那條路，`wake_brief` 會被 `classify_watch` 分去假設對照段（錯的 consumer，QueueLiveness 還會照綠）。
- **換版／撤回不得收掉醒來待判、觸及、到期未判的 watch**；只收 active 的。
- **連結反證用來源鍵，不用 watch id**：讀圖重讀、memo 換版時 watch id 會輪換。
- **`candidate_state.watch_id` 不構成歸屬**：否則「watch 屬於本檔」的驗證是循環定義。
- **「讀圖現行」＝`current`＋`stale_low`**：`stale_low` 不進重讀佇列，不算現行就修不回來。
- **`_held` 不得被排除 beta 的版本取代**：它餵 pq1 排序與 daily triage 的 fail-closed。
- **`--log-only` 不帶 `--apply` 也寫 trade_log**：試跑兩個都不帶。
- **互斥靠 `scripts/writer_guard.py`**，不靠查排程時間。
- **`companyfacts_lag` 對 20-F 恆不報落後、抓取失敗不警告**。
- **主題等權組的寫入綁凍結 spec＋`complete-theme-cohort`**：只驗「有編號」證明不了使用者 go 的是這一份。
- **Engine C 是 SQLite**：建表住 `engine_c/db.py::_ensure_sqlite_schema`，`engine_c/migrate.py` 在 SQLite 上會 SystemExit；正式庫 WAL，暫存副本用 backup API。
- **回填的日期**：財報數字的可用日是 `filed`（EDGAR）或法定期限（台股月營收，`published_at` 恆 NULL），不是會計期末、更不是抓取日（INV-6、L11-5）；唯一鍵含 accession，as-of 取 `filed ≤ T` 的最新一列。
- **口徑**：股數序列逐檔只收一個來源；報價單位照存；ADR 股數與價格不是同一種證券單位、報表幣別 ≠ 結算幣別 → `inputs_incompatible`，不換匯、不猜比率；分割用 raw／adjusted 分存處理。
- **「美股」≠「無後綴 ticker」**：EDGAR 季度路徑只對 10-K／10-Q 國內申報人；20-F（TSM、UMC、XPEV、GFS、TSEM、HIMX、POET、NBIS…）只有年度點。
- **「今天的倍數」與歷史同一個函式算**：不讀 `financial_snapshots.ev_revenue`（yfinance 口徑）。
- **稀釋燈的窗是 trailing 一年**，不是整條回填序列的頭尾——否則回填後幾乎全亮黃（L14-4）。
- **「已持有」只從 Sheet 推導，beta 排除、FRA:2DG 要經 execution 反向別名**；Sheet 讀不到時 held 組印 `upstream_unavailable`，不得退回敘事宣告。
- **`company_id_for_ticker` 不得放寬**：它在資本歸屬路徑上；寬鬆的 base 解析只住 lead 關聯（`engine_b/entities.py`）。
- **watch 歸屬以來源判，不以 `entities`**：entities 記的是條件牽涉誰（AXT 的第 3 條反證 entities 是 JX／住友；InP 讀圖反證的 entities 是 COHR／LITE）。
- **收據的兩個放行分開**：`--override --reason` 是 5% 硬擋的；缺敘事用 `--no-narrative-override`；`--reason` 無 `--override` 的既有守門保留。新收據 key `research_receipt`，不與 `hard_cap_check` 混。
- **`record_trade` 必須先 locate 到恰好一列 Sheet**：真實 dry-run 用 Sheet 已有的列；首次建倉先手動建列。
- **`get_bottlenecks` 不能退役**：PointInTime 探針與 Q1 仍用它。
- **`refresh=review_required` 不餵讀圖面板**：今天全是退役估值鏈殘留。
- **鏈段在 builder 組、讀圖在 webapp 注入**：不得讓 briefing import webapp；二擇一見 §8 第 4 點。
- **readiness 換核心會讓 blocked 數變**：那是預期，逐檔指得出是哪個面板；不得為了讓 ready 變多而把 `readings` 留選配。
- **daily 的 `DAILY_STEPS` 有逐項相等測試**：3.2 與 3.6 改它要同 commit 改測試並在 05:30 前 push；3.2 的回填不得與 daily 同時跑；3.5 寫 `event_watches.json` 前取得 writer lock。
- **新 kind 的測試面**：request-path 測試逐條列路由；`STATE_KINDS`、`_STATE_NOTES`（`webapp/api.py`）、`_STATE_FLAGS`（`webapp/__main__.py`）三處同步，少一處就是 500 或整批重跑。
- **Windows**：python 不認 `/tmp`，暫存用 scratchpad／`%TEMP%`；程式碼不要放 heredoc，用 Write 成檔再跑；子行程用 `sys.executable`。
- **Neo4j 要開**：`query.structure`、讀圖選取、走圖、整合測試都需要；讀不到圖時印 `upstream_unavailable`，不印 0。
- **可開為零就零**：3.5 四份全是 `missing`、或 COHR／LITE 落「非倍率候選」都是合法結果；看到候選板「可開 0」時要做的是研究，不是改前提或門檻。

## 14. 結案時要列的待決問題（種子；執行中發現的往下加）

1. Phase 2 closeout §5 未併入本 Phase 的：#2（3 則排回 lead 補分類——研究）、#4（稽核依賴 Neo4j，本 Phase 維持）、#6（聯合公告偵測 `display_name`，先量）、#7（`supplies_to → prod:` 兩義，Phase 4）、#10（走圖母體 <10 型別）、#11（Phase 1 §7 殘題）、#13（apply 入口旁支、`_finalize…` 無呼叫端、`verify_test_nonvacuity.py` 失效突變）、#14（`wake_reading` 以節點為單位）、#15（「客戶高管在供應商新聞稿具名」算不算客戶端印證——**要使用者決定**）、#16（兩條叫不醒的語意 watch）、#17（`classify_evidence` 屬性引文算邊印證、`prod:` 一表多義、SuperNova 原文未定日、OpenLight 兩個 ID）。
2. **「剛轉型」只能由敘事宣告**：若敘事沒寫而歷史其實不可比，百分位會照算——要不要讓讀圖或 thesis 也能宣告。
3. **主題等權組 pq2 若結案時仍未 go**：已定價②③全體缺席；照實寫，Phase 5 前要有人定。
4. **Phase 5 從 trade_log 收據重建量測**：`research_receipt` 欄位是否足夠由 Phase 5 plan 驗；舊事件缺它要當 absence。
5. **`get_bottlenecks`／Q1 scarcity 那條路**要不要退役（PointInTime 探針要先換成等價的 as-of 投影探針、跑讓它紅的突變）。
6. **`refresh=review_required` 的來源全是退役估值鏈殘留**（`operating_assumption`／axis／thesis）：refresh 規則要不要清。
7. **`risk/snapshot.py::build_portfolio_components` 的第二份 alpha 判別**：要不要改呼叫 `hard_caps` 公開函式。
8. **`fundamental_history` 年度營收與既有 `fiscal_year_results`（manual、mechanical）重疊**：兩者的關係與誰是年度營收的 authority。
9. **ADR 比率與報表幣別≠結算幣別的標的**（TSM、UMC、XPEV、IQE.L、XFAB.PA、HEXA-B.ST、ENA.V…）已定價①為 `inputs_incompatible`：要不要在 registry 登記 ADS 比率並加歷史匯率。
10. **台股歷史股數**：若 3.2 找不到機械來源，台股已定價①全體缺席——要不要人工觀測或換口徑。
11. **`record_trade.py` 首次建倉要不要能新增 Sheet 列**（今天必須先手動建列）。
12. **邊緣門檻的兩個數**（10B、12 位）是 2026-09-19 由 16 檔實測斷點定的；候選板上線後若「非倍率候選」與「邊緣無法量」長期占多數，要不要重量（不得為了可開非空而調）。
13. **TYO:7803 在 registry 解析不到**：「持股解析不到」計數會恆為 ≥1；要不要登記進 registry（identity 的決定）。
14. **決定紀錄 §10 的「可開恆為 0 或恆非 0」**：心跳每天印各狀態檔數，但較昨快照只留短期——2026-12-22 回查時要有足夠長的序列，屆時確認來源（完整性補查推翻了「沒有計數器」這條，但序列長度仍要在 Phase 5 前確認）。
15. **20-F 便利換算造成約一年延遲**（Step 3.2 R2-c）：TWD／RUB＋USD 便利換算的發行人，當年度 20-F 被「多單位就拒寫」擋掉，要等下一份的比較欄——要不要改成「只收報表本位幣那一個單位」（需要一個機械判定本位幣的來源）。
16. **companyfacts 部分收錄的發行人**（TSM、UMC：最新 20-F 只收到封面 fact）：落後檢查已把它們記成 `lagging` 不寫；何時補齊取決於 SEC，daily ②b 每天重試。要不要改由其他一手來源（公司年報）取年度營收——那是人工觀測，不是本表。
17. **價格 adjusted 序列的窗邊界斷層、分割事件只涵蓋 3 年窗**（R2-c #3、#9）：目前沒有消費端跨越窗邊界；Phase 5 量測若要更長的報酬序列，先處理這兩點。
18. **`engine_c/history.py` 只跑 SQLite**（R2-c #7）：Postgres 只做到建表對等；切後端前要補讀取端的佔位符。
19. **落後檢查還騙得過的一種更窄形狀**（R2-c 覆核 non-blocking #2）：最新申報只帶「比較年度」的營收、沒帶當年度時，快照日仍被推成 current。正式資料目前沒有；要不要改成比對「最新申報的 period_end 是否有營收 fact」。
20. **稀釋燈一年窗滿了之後 30 檔裡 24 檔亮黃**（Step 3.3 試跑）：規則是「一年內同口徑股數增加 → 黃」（D2，不設量級門檻）；FN +0.01% 與 AXTI +42% 同樣是黃。它量的是事實，但國內申報人 80% 亮黃接近恆亮（L14-4）——要不要把員工股酬等級與增發分開、用什麼非憑空的判準（例如只看有沒有 S-3／424B 發行），**要使用者決定**。今天照規則印、數字在稽核層。
21. **三題尚未接 as-of 視角**：歷史表的 PIT 讀法已備（`shared/as_of.py`），但 view 其他段在 as-of 下各有規則；目前 as-of 模式下三題 section 誠實缺席。
22. **R2-a non-blocking（Step 3.4 覆核）**：N2 寫入端「供給側」只認 `supplies_to`（plan 寫 supplies_to／develops，方向更嚴）、「它在需求側」的提示對外向需求邊會印成「兩側都不在」；N4 QueueLiveness：fired 的 `wake_brief`（非語意 kind）沒有滯留檢查、fired 的 `brief:` 語意 watch 滯留訊息指向的 consumer 寫成「semantic-queue → judge」；N5 v2 的禁字表與 placeholder 字彙在 parse 路徑上，日後改字彙會讓舊 v2 紀錄解析失敗（v1 早就如此，§13 要註明）；N8 舊版／已撤回版 fired 的 `brief:` watch 不進 `disproof_counts` 任何一格、brief ledger 的 parse errors 被 `current_briefs` 與 audit 忽略、舊版 `candidate_state` 用過的 `wake_brief` 若新版不再引用仍留著（醒來時多處置一次）。
23. **R2-a 覆核 non-blocking（0d4c7ad）**：①「今天」已統一成排程時區（`alpha brief` CLI 改用 `event_watch._today()`，收尾 commit 當場修）；②`settle_due` 只轉敘事來源的 watch——thesis／讀圖來源已過 expires、daily 還沒標記的，可開前提③最多晚一天才算「到期未判」（hook 不會收掉它們、不丟資料；3.6 每天重驗補上）；③寫入被拒時記憶體裡的 `ctx.watches` 已被時間轉換過（不存檔；CLI 丟掉 ctx，重用 ctx 的呼叫端要知道）；④**writer lock 沒有在 `alpha brief --add` 程式裡強制**：它在讀 registry 與存檔之間整份覆寫 `event_watches.json`，互斥只靠操作程序先取鎖——要不要在 CLI 內自動取鎖。
