---
date: 2026-10-02
topic: phase5-measurement
status: active
derived_from: docs/ROADMAP.md（Phase 5 列＋2026-10-02 amendment A1「不做報酬回測、錯分兩種」）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G9、§4.2、§6.7、§10）、docs/reports/2026-10-02-phase4-closeout.md §6（#26、#29、#33、#34）、docs/reports/2026-09-30-phase3-closeout.md §5 #16–#17、AGENTS.md「消費契約：圖是中心」量測段
---

# Phase 5 量測（給執行模型的完整 plan）

> **執行者：全程 opus 5.5（使用者 2026-10-02 定案 #7）**，走 `skills/development-flow/SKILL.md`（Z1 以上 R1）。本 Phase **沒有研究步驟**：全是機械量測、夾具測試與一支資本路徑的旗標。
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 5」（含本 plan §0.4 的 amendment A1–A3）導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文（尤其「消費契約」的量測段、「已知會失焦的指標判別法」、「資本與風控」、L12／L13／L14）→ ROADMAP「Phase 5」列與 Phase 4 closeout §9 的 amendment →
> 本 plan §0.1–§0.4 → 決定紀錄 §4.2（籃子與 G9 量測基準共用同一個）、§6.7（籃子成分是判斷）、§10（本檔自己的 disproof：「可開」恆 0／恆非 0 要 12-22 回查）→
> `scripts/outcome_if_settled_today.py` 檔頭與 `power_law_aggregate` docstring（三量各自的判準、「分母 0 回 None 不回 0」、恆等式不做除法）→ `webapp/materialize.py::materialize_positions`／`build_positions_artifact`（**只呼叫 collect()，不呼叫 render**）→
> `crons/heartbeat.py::build_positions`（段 4）與 `SNAPSHOT_KEYS` → `engine_b/account_scorecard.py` 檔頭（五欄、三個刻意不做、三個已知偏差）→ `alpha/theme_cohort.py` 檔頭（三條規則）→
> `alpha/structure_reading/contracts.py` 檔頭（「存輸入不存結論」「維護的是讀圖跟圖還一不一致，不是讀圖對不對——對不對要靠 outcome 量測」）與 `staleness.py` 檔頭 →
> `portfolio/research_receipt.py` 檔頭（收據兩半、`NARRATIVE_STATES` 封閉字彙）→ `scripts/record_trade.py` 的 `--log-only`／`--open-position` 註解 → `engine_b/event_watch.py::judge`／`record_touched`（`judgment.touches` 是「觸及」的機械紀錄）→
> `docs/OPERATIONS.md`「sandbox impact review 五步」→ `docs/refactor/historical-failure-matrix.md` §2。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（追蹤表／讀圖／敘事／registry／機制），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字是**追蹤表**（三條 lane 各自的列數、量測起始日、三量、對主題等權組的超額）、
> **讀圖**（圖預測對錯表的每一列與「錯」的種類）、**計分表**（籃子基準有值的格數）、**等待 registry**（結案登記的回查 watch）、**機制存在與否**（見 §11）。
> ⚠ 三量、超額、預測表**只印不判、不排序、不設門檻**；候選板「可開」數只印不驗收；預測表不得因「供給側多一家」自動判錯（§0.1 #3）。

**一句話目標：** 讓「賭對了值多少、判斷錯了值多少、哪個管道產出贏家」三句話第一次有會自己出現的數字：追蹤表從「舊店入圖日」換成「我們真的買的」與「我們寫下判斷的」兩條 lane（舊的凍結只印），
每條 lane 印三個 power-law 統計量與對主題等權組的超額；每一份讀圖斷言有一個機械的對／錯終局，錯的分「當時已有反例」與「之後才出現」；計分表多一個主題等權組基準。
**它不改變任何判斷、不給尺寸、不排序**——量測是快慢兩條迴路的儀表板（G9），不是新的 gate。

---

## 0.1 使用者定案（2026-10-02；8 題，使用者「基本上都 ok，全程用 opus 5.5」）

| # | 題目 | 定案 |
|---|---|---|
| 1 | 追蹤表的列與錨點 | **A**：三條 lane 分印——`live`＝trade_log 的 alpha 成交（成交價／日、收據照抄）；`paper`＝每檔**第一份 v2 敘事寫下日**（列上帶當時候選狀態、之後的變化、首次點名它的 lead 來源）；`history`＝舊 Decision Store 22 筆入圖日錨點，凍結只印、不再新增。三量與籃子超額每 lane 各算、分母分開（§0.4 A1） |
| 2 | live lane 空白怎麼辦 | **A**：`record_trade.py` 加 `--backfill-before-receipts`（只准配 `--log-only`、成交日早於收據上線日 2026-09-30、必附理由、收據寫 `backfilled` 不拿今天的敘事冒充）；旗標走 R2-a（資本路徑）。**回填哪幾筆由使用者在互動 session 下指令，照整理後的 Google Sheet 補**（使用者 2026-10-02：COHR 與 SIVE 都「買了就沒賣」，Sheet 漏了 COHR 列、另行整理）；本 plan 不寫任何成交 |
| 3 | 圖預測對錯表的單位與判準 | **A**：單位＝一筆讀圖；斷言只算 `kind∈{moat, volume}`；判定只來自兩種既有紀錄（被不同 kind 的新讀圖取代或撤回＝錯；同 kind 取代且圖有變或已到期＝對；同 digest 的同日改寫＝改寫不算；反證 watch 被互動 session 判觸及＝錯）；錯的種類由反例文件 `published_at` 對舊讀圖 `created_at` 機械分，沒日期另列。**不加** staleness 的 `supply_added` 自動判錯 |
| 4 | 驗收②結案時仍是 0 | **A**：夾具測試證明機制、closeout 寫「已交付、未生效」、登記 date watch 回查（最早讀圖到期 2026-12-24）；**不為了驗收去重讀** |
| 5 | 候選狀態每日序列 | **A**：`materialize --candidates` 時 append 一個不刪的 `library/private/measurement/candidate_state_series.jsonl`（同日去重）；心跳不變（§0.4 A2） |
| 6 | Phase 4 尾巴 | **A**：#29（③b 計數器認 supersede）、#33（走圖第 2 型降級）、#34（`classified_by` 字彙）三個小修＋stash 的 setup 1b 預熱清單與對稱測試 commit＋apply 入口加 `db.propertyKeys()` 比對 fail closed，排成 Step 5.1；**[666] 重試是使用者動作，等 5.1 修完 #29 之後再 go**。另外 10 題判準類（closeout §6 #1–#4、#11、#17、#20、#27、#30、#31）**不進本 Phase**，結案後開一次「證據判準」brainstorm 一併定（§0.4 A3） |
| 7 | 執行者與 R2 | 執行者**全程 opus 5.5**（使用者改建議）；執行期間六條 trigger 命中的 R2 **常規 opt-in**，預定一處 **R2-a＝Step 5.3**（`record_trade.py` 旗標，資本路徑）；唯讀 reader 不開 R2；結案 R2 已常規（AGENTS） |
| 8 | 籃子基準細節（plan 作者定、使用者未反對） | 用量測當下生效的那一份主題等權組（印 `cohort_id`／`decided_on`）；本檔從自己的籃子排除；缺價成員印出、不猜；計分表把它當第三個基準（QQQ／SOXX／主題等權組），用現行組回溯——計分表本來就是「今天回頭看」（`point_in_time.mode=current`），偏差已印在表上；產出都住既有 kind（`positions`／`structure_readings`／`account_scorecard`），不開新 kind |

## 0.2 現況實測（2026-10-02；**現況數字會腐壞，引用前重跑查證命令**）

> 5.0 實測的更正（讀圖鏈 digest、watch 形狀、Sheet 已有 COHR 列、`origin_linkage` token 已存在、計分表 NaN、`--no-benchmark` 會寫檔、跨日只比錨點）見 [`docs/reports/2026-10-02-phase5-baseline.md`](../reports/2026-10-02-phase5-baseline.md) §13；本表保留寫 plan 當時的快照。

| 事實 | 數字 | 查證 |
|---|---|---|
| 追蹤表（`positions` kind） | **22 列，錨點全是舊 Decision Store 的入圖日**（量測起始 2026-07-21、最長 72 天）；三量：籃子總報酬 +8.66%、最大單檔 AXTI（等權貢獻 +4.15%／其餘 21 檔 +4.51%）、曾達 2 倍 1/22（現價仍達 0）、12 個月分母 0；對 QQQ 超額 +4.05%；「入圖前已漲」8/22 | `library/private/app/state/positions.json`（`rows`、`power_law`、`anchor_health`）；`python scripts/outcome_if_settled_today.py --no-benchmark` |
| `positions` 的 producer | daily 步驟 `05_outcome`＝`scripts/outcome_if_settled_today.py`（寫 `library/private/decision_lab/outcome_aggregate.json`＋`.jsonl`）；`webapp materialize --positions` 以檔案路徑 import 它、**只呼叫 `collect()` 不呼叫 render**；`counters` 來自凍結舊店的 `capital_expression_counters()` | `crons/daily_task.py:148-149`；`webapp/materialize.py:1235-1271` |
| trade_log | **2 筆、都是 beta**（QQQ 2026-07-31 IB、LON:VWRA 2026-09-01 FUBON）、都沒有 `research_receipt`（收據機制 2026-09-30 Phase 3 Step 3.8 才上線）；sha256 `861d2008…c7b8d5` | `library/trades/trade_log.jsonl` |
| 舊店 live fill | **1 筆**：COHR 2026-08-18 10 股 @316.23 USD（`ib-cohr-2026-08-18-10sh`）；`live_choices` 1；shadow observed 22／unavailable 25、cohort 47 | `decision_lab.db`（`mode=ro`） |
| Google Sheet alpha 持股 | FRA:2DG（Sivers）2000 股 @6.84 EUR 在 IB；**COHR 列不在 Sheet 上**（使用者 2026-10-02：沒賣，Sheet 漏列）；兩檔都沒有 trade_log 事件 | `python fetchers/gsheets.py`；候選板 `holdings` |
| v2 敘事 | **4 檔**（AXTI `priced_wait`／COHR `pass`／LITE `pass`／SIVE.ST `missing`），第一份 v2 都在 2026-09-29（SIVE.ST 10-01 換版）；v1 最早 09-15（COHR） | `library/private/alpha/briefs/*.jsonl` |
| 主題等權組 | **1 組**（`tc_35b0d5cd521656ea`，2026-09-30，pq2 [656]），成員含 AXTI、IQE.L、4971.TWO、2455.TW、3081.TWO、4979.TWO、SIVE.ST… | `library/private/alpha/theme_cohorts/AI_____CPO.jsonl` |
| 讀圖 ledger | **15 筆、現行 4**（`tech:cw_dfb_laser` volume v3、`mat:inp_substrate` volume v3、`prod:supernova` socket undecided、`prod:els_8ch_module` socket undecided）；supersede 鏈裡**只有 SuperNova 09-25 → 10-01 是圖變了之後的重讀**（evidence 標籤變、digest 不同），其餘是同日或隔日 schema 升版（v1→v2→v3，digest 相同）；inp 鏈 09-17 第一筆 undecided → 同日 volume；現行斷言（moat／volume）最早到期 2026-12-24 | `library/private/alpha/structure_readings/*.jsonl` |
| 讀圖來源的反證 watch | 語意 watch 53 筆（active 36／fired 1／consumed 16）；來源 `reading:` 35、`thesis:` 16、`brief:` 2；「觸及」的機械紀錄＝`watch.judgment.touches == "yes"`（`judge` 與 `record_touched` 同形） | `library/leads/event_watches.json`；`engine_b/event_watch.py:703-729、997-1024` |
| 計分表 | 1 個帳號（`aleabitoreddit`，probation）；基準 QQQ／SOXX；`MAX_PRICED_SYMBOLS` 200；心跳段 5 每天只印 tier 分布 | `config/signal_sources.json`；`engine_b/account_scorecard.py` |
| 候選板計數 | 可開 0｜缺 X 0｜等回落 1｜不要 0｜已持有 1｜非倍率候選 2｜無敘事 69；心跳快照只留 **14 天**（`SNAPSHOT_KEYS`），沒有任何序列保留到 12-22 | `library/private/app/state/candidates.json`；`crons/heartbeat.py:29、1694-1705` |
| Phase 4 尾巴 | pq2 [666] `partial`（圖未動）；`stash@{0}`「neo4j_setup 1b 預熱補 loader 全部屬性名＋對稱測試」未 commit；工作樹 2 檔未 commit（`extractions/reuters_inp_export_controls_2026_06_11.json`、`library/raw/reuters_inp_export_controls_2026_06_11.txt`）；③b 計數器以「id 不在凍結集合」判新 | `git status`、`git stash list`；`query/layer_stats.py` |
| 測試 | 3214 passed／1 skipped（Phase 4 結案）；`python -m audit invariants` 14 PASS | Phase 4 closeout §1 |

## 0.3 本 Phase 刻意不做

- **不做報酬回測**（ROADMAP 2026-10-02 amendment）；不做任何機械選股規則；不把三量、超額或預測表接進任何排序、候選狀態或尺寸（G1、G6、INV-5）。
- **不寫任何成交**：trade_log、Google Sheet 一筆都不寫；回填是使用者在互動 session 用 Step 5.3 的旗標下的指令，本 plan 只做旗標。
- **不重讀任何讀圖、不寫敘事、不動 thesis**：驗收②若結案時沒自然發生就照實寫（§0.1 #4）。
- **不讓「供給側多一家」自動判錯**；不用 LLM 判任何對／錯（L15：判定來自既有的人工紀錄，程式只分類時間）。
- **不改主題等權組的成分與寫入入口**（`complete-theme-cohort` 不動）；成分變動仍是 pq2 判斷。
- 不開新 state kind；不改 `AGENTS.md` 判準句；不動舊 Decision Store 的任何檔案（含 `outcome_aggregate.json(l)` 的既有四個欄位）。
- Phase 4 closeout §6 的判準類 10 題（#1–#4、#11、#17、#20、#27、#30、#31）與資料口徑題（#5–#10、#12–#16、#18、#19、#21、#23–#25、#28、#32）不在本 Phase，照實帶到 §14。
- 不做海外財報來源；不重量邊緣門檻。

## 0.4 ROADMAP amendment（五欄；使用者 2026-10-02 定案；ROADMAP Phase 5 列同 commit 改寫）

**A1｜追蹤表三條 lane；live lane 的回填旗標**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「量測層從 trade_log 加收據重建（舊 Decision Store 的 outcome 只當歷史）」——沒有定「我們寫下判斷的那些檔」從哪天起算 |
| 新觀察 | trade_log 今天 2 筆都是 beta；alpha 真實持股（COHR、SIVE）都在收據機制上線之前成交、沒有事件；只從 trade_log 重建＝live lane 永遠 0 列，而「判斷錯了值多少」（我們說不要／缺 X 的後來漲了多少）只有從敘事日起算才量得到——用「可開」當錨就是把 filter 當母體（G10 反面） |
| proposed change | 追蹤表分三條 lane 分印：`live`＝trade_log alpha 成交（錨＝成交價／日，收據照抄）；`paper`＝每檔第一份 v2 敘事寫下日（錨＝那天收盤；列帶當時候選狀態、之後的變化、首次點名它的 lead 來源）；`history`＝舊店 22 筆入圖日錨點，凍結只印、不再新增。三量與籃子超額每 lane 各算、分母分開。`record_trade.py` 加 `--backfill-before-receipts`（只准配 `--log-only`、成交日早於 2026-09-30、必附理由、收據寫 `backfilled`），回填由使用者照 Sheet 下指令 |
| why | 兩個問題要兩個分母：「買得準不準」（live）與「判斷準不準」（paper）壓成一張表就是 L12；舊店錨點是入圖日、不含判斷，只能當歷史。造收據是 INV-6 破口，所以回填的收據必須標缺席 |
| impact | 只動 `scripts/outcome_if_settled_today.py`、`webapp/materialize.py::materialize_positions`、`crons/heartbeat.py` 段 4、APP positions 頁、`scripts/record_trade.py`（旗標，R2-a）；`outcome_aggregate.json(l)` 既有四欄一字不動（新資料住 `lanes`）；不動任何 authority；daily 步驟清單不變，`05_outcome` 的網路 surface 變大（多抓 paper／live 與籃子成員的收盤）→ 同 change 做 sandbox impact review 並給上限常數 |

**A2｜候選狀態每日序列**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 沒有 |
| 新觀察 | 決定紀錄 §10 要在 2026-12-22 回查「可開恆為 0 或恆非 0」，Phase 3 closeout §5 #17 也列為「Phase 5 前要有答案」；心跳快照只留 14 天、候選板 artifact 每天覆蓋——到時候沒有任何序列可看 |
| proposed change | `materialize --candidates` 每天 append 一行到 `library/private/measurement/candidate_state_series.jsonl`（日期、五狀態與側欄各自檔數、無敘事檔數、最老滯留天數；同日重跑只留最後一筆），只寫不讀；心跳不變 |
| why | 常駐計數器要有序列才能被回查（L14：真正的防呆是會自己出現的計數器） |
| impact | 只動 `webapp/materialize.py::materialize_candidates`（新寫入路徑→sandbox impact review）；derived 時序，不是 authority |

**A3｜Phase 4 尾巴併入**

| 欄 | 內容 |
|---|---|
| 原 roadmap | Phase 4 closeout §6 #29、#33、#34 與 #26 的三件機制題沒有歸處 |
| 新觀察 | [666] 重試會重寫 4 筆帶 sub 的斷言，③b 計數器看不到 supersede → 成功與失敗同形（L13）；repo 的 setup 1b 只預熱 2 個屬性名、修正停在 stash；apply 入口撞 token 缺席時是 Neo4j 回 Forbidden 才知道（要人記得的規範） |
| proposed change | Step 5.1 做 #29、#33、#34、stash commit、入口加 `db.propertyKeys()` 比對 fail closed；[666] 的 go 由使用者在 5.1 之後下 |
| why | 都是十行級、不動 contract 的小修（L17：當下修），而且 #29 必須先於 [666] 重試 |
| impact | `query/layer_stats.py`、`query/graph_walk.py`、`config/lead_ref_keys.json`／`engine_b/leads.py`（字彙）、`schema/neo4j_setup.cypher`、`scripts/apply_ra_admission.py`；不動圖 |

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者已核准的 PLAN_PROPOSAL**（§0.1）。`AGENTS.md`「常規推進授權」照用：Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step**，做到 Phase 5 結案為止。只有六條停止條件之一成立才停。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（#7）**：預定一處 **R2-a**（5.3 之後：`record_trade.py` 旗標＝資本路徑）；其他 Step 若命中 trigger 同樣直接發 `WORK_REQUEST`。NO_GO → `AWAITING_HUMAN`。

**停點：** 無其他預定停點。[666] 的重試是使用者動作（5.1 結束的 HUMAN SUMMARY 要印出重試指令：`python scripts/apply_ra_admission.py --pq2 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d` → `python scripts/commit_pending_intake.py` → `python -m engine_b.todo complete-ra 666 --digest …`），執行者不代跑、不停在它上面。
回填成交同理：5.3 結束的 HUMAN SUMMARY 印出指令範本，由使用者照 Sheet 填值；執行者不代跑。

**每個 Step 一個 commit（大的 Step 可拆，進度表在最後一個 commit 才 ○→✅），訊息第一行寫 Step 編號；Step 為 GO 就 push。**
新 session 先看下面進度表與 `git log --oneline -20`，從第一個未 ✅ 的 Step 接續。

**同一 working tree 只讓一個 writer：** `StockBotv2-Daily`（台北 05:30）是唯一排程。5.2（daily 步驟 05 的腳本）與 5.6（materialize 新寫入）的 commit **不得跨越 05:30 還沒 push**；本 Phase 沒有任何 Step 寫 `library/` 的 authority ledger，不需要互動 writer lock；R2 進行中不在主樹跑變異測試。
⚠ 工作樹裡 [666] 的兩個未 commit 檔**不屬於本 Phase**：每個 Step 的 commit 只 `git add` 自己改的檔，不得把它們一起 commit 或還原。

| Step | 內容 | 狀態 | 執行者 | commit |
|---|---|---|---|---|
| 5.0 | 基準快照（`docs/reports/2026-10-02-phase5-baseline.md`；偏差見 §0.6 #1–#5：§5 改寫規則修正、追蹤表查證命令改不寫檔、計分表 NaN、跨日只比錨點、watch 實際形狀） | ✅ | 執行模型 | 見 git log「Step 5.0」 |
| 5.1 | Phase 4 尾巴：#29 ③b 認 supersede、#33 第 2 型降級、#34 `classified_by` 字彙、stash 預熱清單＋對稱測試、apply 入口 `db.propertyKeys()` 檢查（偏差見 §0.6 #6–#9；驗收見 baseline 報告 §15） | ✅ | 執行模型 | 見 git log「Step 5.1」（5.1a–5.1d） |
| 5.2 | 量測層三條 lane＋主題等權組籃子基準（`collect()` 重建、positions artifact v2、心跳段 4、APP positions 頁；sandbox impact review） | ○ | 執行模型 | |
| 5.3 | `record_trade.py --backfill-before-receipts`（R2-a） | ○ | 執行模型 | |
| 5.4 | 圖預測對錯表（純函式＋`structure_readings` artifact v2＋讀圖頁＋心跳段 4 一行） | ○ | 執行模型 | |
| 5.5 | 計分表接主題等權組基準 | ○ | 執行模型 | |
| 5.6 | 候選狀態每日序列 | ○ | 執行模型 | |
| 5.7 | 新管線 full chain 測試（夾具版） | ○ | 執行模型 | |
| 結案 | completion gate ＋ closeout ＋ R2 ＋ ROADMAP ✅ ＋ 回查 watch | ○ | 執行模型 | |

**開工／續工指令：貼 `/phase-run` 即可**（不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-10-02-001-feat-phase5-measurement-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。沒有需要我核准的事就一直做到 Phase 5 結案；撞到六條停止條件才停（R2-a 已常規 opt-in，見 §0.5）。
[666] 重試與成交回填是我的動作：印出指令就接著做下一個 Step，不要停在上面等。每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|
| 1 | 5.0（影響 5.2、結案 R2） | §1 第 2 項與結案 R2 第 2 項：「`python scripts/outcome_if_settled_today.py --no-benchmark` 全文存檔」 | 5.0 以 scratchpad 包裝取全文（同一個 `main()`，`_persist_aggregate` 換成 no-op；兩個聚合檔指紋跑前跑後相同）；**5.2 根除**：`--no-benchmark` 是診斷旗標，帶它時 `_render` 不寫聚合檔（daily 步驟 05 的 argv 不帶它，序列照舊）；結案 R2 第 2 項因此可直接用 CLI | CLI 的 render 會覆寫當日那一行，`--no-benchmark` 時 `equal_weight_excess` 被寫成 null（今天 daily 寫的是 0.0403）——違反不可越線 #3；「記得用包裝」是要人記得的段落，根除只要一個條件 |
| 2 | 5.0（影響 5.4） | §5 `rewritten`＝有後繼、同 digest、r 未到期；否則同 kind＝`held`（對）。§0.2「其餘是 schema 升版、digest 相同」 | `rewritten` 加條件②：**同 kind** 的後繼若 schema 版本不同、或沒有帶來 r 沒引用過的來源（`new_sources` 為空），也是改寫；**不同 kind 不套②**；r 已到期照舊不是改寫。真實資料：原規則 held 5／rewritten 4 → 修正後 held 0／rewritten 9（逐筆見 baseline §5） | 實測 inp／cw 兩鏈有 5 個同 kind 環節 digest 不同，快照差異全對得上 `query/structure.py` 的 commit（需求走訪加 constrained_by、證據欄修正、反向路徑只收 competes_with）與 schema 升版，沒有一個是供給側增減。原規則會把它們算成 5 筆「對」＝§5 L11-6 ④點名的「改寫被算成驗證」，並讓 ROADMAP ② 在 5.4 當天被假性滿足。定案 #3 的原句是「同 kind 取代且**圖有變**或已到期＝對」——查法變了不是圖變了；`result_digest` 一個表示承載兩種語意（L12），修的是機械代理不是定案。「新來源」與「錯的種類」用同一個 `new_sources`（一個 owner） |
| 3 | 5.0（影響 5.2、5.5） | §6 驗收「五欄既有值逐位不變」 | 5.5 加：`_yfinance_closes` 濾 NaN 收盤；驗收改「同一份價格上，被 NaN 污染的格以外逐位不變，污染的格逐格列出改前改後」。5.2 的主題等權組報酬函式同樣濾 NaN（照 `_provider_series` 的 `.dropna()`＋`close == close`） | 計分表「點名後 90 天 vs SOXX」今天是 NaN：yfinance 對 5 檔歐洲標的（IQE.L、SHA0.DE、SIVE.ST、SOI.PA、XFAB.PA）在 10-01 回了 NaN 收盤，計分表取價沒濾；NaN 混進中位數時排序結果不確定，同一批值算出的 QQQ 格也可能被靜默算錯，而 NaN 不等於自己、「逐位不變」對它無法成立。十行內、不動 contract（L17 當下修），住 5.5 本來就要改的檔 |
| 4 | 5.0（影響 5.2、§11、§12、結案 R2） | §3「真實資料：history 22 列與 5.0 逐位相同（`rows` 與 `power_law` 的 digest）」 | 分兩層：**同一份價格**（注入同一個 loader 或同一次抓取）跑改前／改後兩份 `collect()`，history 的 `rows`／`power_law` digest 逐位相同；**跨日**只比錨點 digest（baseline §2：`sorted((ticker, company_id, anchor_date, anchor_price, anchor_currency))` 的 sha256＝`6ea352ed…7b93`） | 每列帶現價，三次各自抓價在第 4 位小數就不同（daily 05:3x、materialize 07:14、5.0 14:5x）；跨日比 rows digest 必然不同，那不是回歸 |
| 5 | 5.0（影響 5.4） | §5 輸入「來源為 `reading:<r.reading_id>` 的語意 watch `judgment.touches == "yes"`」；種類「標旗／判定引用的那份文件的 `published_at`」 | 照實際形狀寫進 §5：`kind == "semantic_condition"`；`source_ref` 是 `reading:<id>#<第幾條>`（比對去掉 `#n`）；觸及只看**單數** `judgment`（判無關 append 在複數 `judgments`）；文件日期＝`judgment.lead_id` → lead registry 那則的 `published_at`（空→`undated`）；`record_touched`（pq2 `watch_decision`）那條路 `lead_id` 是 null → `undated` | §13 要求「5.0 先查清楚再寫 5.4」；照原文的 `reading:<id>` 全等比對會 0 命中且不報錯（成功與失敗同形，L13） |
| 6 | 5.1（#29） | 「凍結集合要補存當時的內容 digest（phase4 集合只存 id：5.1 補一份 `assertion_digests`）」；內容＝「quote＋sub＋evidence 的 canonical」；L11-6 ④「`new` 必須與 closeout §2 相同（4 筆）」 | 內容基準住**另一個鍵** `assertion_content_2026_10_02`（695 筆，不寫進 phase4 那個鍵）；指紋另含邊（src／relation／dst）與 `source_doc_id`；`new`（帶 sub、不在凍結集合）今天是 **0**——closeout 的「4 筆」是 Phase 4 新入圖、都不帶 sub 的 assertion 總數，兩者分開核（baseline §15：集合外 4 筆、帶 sub 的 0） | `config/graph_baselines.json` 自己的規則是「新的基準加一個鍵，既有鍵一個字都不改」；同 id 被重套到另一條邊或另一份文件也是重寫；L11-6 ④ 的兩個數口徑不同，混著比會讓對的計數器看起來錯 |
| 7 | 5.1（#33） | 「讀圖 ledger 讀不到／有壞行時第 2 型與第 1 型同形」 | 新 `reading_rows_or_none`：讀不到或有壞行都回 `None`——第 1、2、**4** 型一起降級（第 4 型原本在壞行時拿殘缺資料照算，`collect()` 把壞行清單丟掉） | 壞行與讀不到同形才不會有「第 1、2 型降級、第 4 型照算」的半套；今天 ledger 沒有壞行，九型數字逐字不變 |
| 8 | 5.1（stash、apply 入口） | 「與 loader 會寫的屬性名集合比對」；stash 的對稱測試自帶 regex | 「loader 會寫的屬性名」收成 `loader.load_to_neo4j.written_property_names()` 唯一一份（38 個＝預熱 37＋`id`），對稱測試與入口都讀它；token 檢查用 apply 寫圖的同一組 routine 憑證；Phase 4 的 `tests/test_layer_document_full_chain.py` 經 `main()` 呼叫入口，補一行注入假檢查（否則它會連真的 Neo4j） | 兩份 regex 會漂開（L16）；用別的憑證查會看到不同的權限世界；測試不該依賴圖開著（以錯的 `NEO4J_URI` 重跑兩個入口測試檔仍 15 條綠） |
| 9 | 5.1（#34） | 「既有 cw_dfb lead 的紀錄不改寫…登記 §14」 | 照做；另查到 3 則 `directed:sub_backfill` 的 lead 被互動 session 鑄號、卻標成預設的 `triage_semantic_v1`（同一個形狀，計入「分類層上次成功」的候選），一併登記 §14 #3、不改寫 | lead registry 是 authority，改資料走 pq2 |

---

## 0. 不可越線（違反即 NO_GO）

1. **不寫任何 authority**：trade_log、Google Sheet、敘事 ledger、讀圖 ledger、主題等權組 ledger、thesis、Event Watch 一筆都不寫（結案登記的回查 date watch 除外，它是等待 registry 的常規用法）；Neo4j 只讀（5.1 的 `db.propertyKeys()` 也是讀）。
2. **`record_trade.py` 試跑一律 dry-run**（不帶 `--apply`、也不帶 `--log-only`）；測試用假 Sheet 與暫存 trade_log；真實 `library/trades/trade_log.jsonl` 的 sha256 在結案時與 5.0 相同（**除非使用者自己回填了**——那時列出每一筆事件並附使用者指令的時間）。
3. **舊 Decision Store 三個 `*.db` 與 `outcome_aggregate.json(l)` 既有四欄**（`date`／`n`／`equal_weight_absolute`／`equal_weight_excess`／`benchmark`）**一字不動**；歷史序列只 append `lanes`，不改舊行。
4. **不排序、不打分、不設門檻、不判**：三量、超額、預測表、序列都只印；分母 0 印「還沒有分母」不印 0%；缺席每格有 `absence_kind`。
5. **預測表的「錯」只來自兩種既有人工紀錄**（不同 kind 的 supersede／撤回、`judgment.touches=yes`）；**不得**把 staleness 的 `supply_added`、`documents` 增加、或任何 LLM 判讀當成錯。
6. **任何 `python -m <module>` 或 `scripts/*.py` 的行為變更 → sandbox impact review 五步**（ROADMAP 硬約束 10）：5.2（`05_outcome` 腳本多抓價、`materialize --positions`）、5.3（`record_trade.py` 旗標——互動專用、不進任何無人值守 allowlist）、5.6（materialize 新寫入路徑）。網路 surface 要有上限常數並在報表上現形（照 `MAX_PRICED_SYMBOLS` 的做法）。
7. **每刪一個測試函式，八欄的 Blocking findings 列出它守的是什麼、現在由誰守。** 活機制的測試不可刪斷言；心跳段 4 的格式測試改主詞不刪判準。
8. **每個 Step 動手前先答 L11-6 第④問：「如果這個改動是錯的，最先壞掉的是哪一筆現有資料或哪個活的呼叫端？」去看那一筆，寫進八欄。** 各 Step 已預填一個起點。
9. **命名：** 不得出現殭屍 grep 九組的新命中（`basket`、`籃子`、`payoff`、`首選`…）：主題籃子一律「主題等權組」／`theme_cohort`；lane 叫 `live`／`paper`／`history`；預測表叫 `predictions`、終局字彙見 §5；序列檔叫 `candidate_state_series.jsonl`；旗標叫 `--backfill-before-receipts`。
10. **INV-1：** 成交 symbol → 公司只走 `portfolio/holdings.py::resolve_holding`；paper lane 的公司來自敘事紀錄的 `company_id`；籃子成員的 ticker 來自 ledger（已經 registry 驗過）。執行代號（FRA:2DG）的行情符號只走 `identity/execution.py` 既有的 yfinance 別名。
11. **INV-6：** 錨點價一律是「錨點日或之前最近的收盤」，兩端同一條 provider 序列、同一結算幣別，否則印缺席（沿用 `outcome_if_settled_today.py` 的 `_to_settlement` 紀律：報價單位 ≠ 結算幣別、GBp 不是 GBP）。預測表的「錯的種類」只看 `published_at`，沒日期一律 `undated`，不拿 `retrieved_at` 冒充。
12. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。**
13. **四個人工 gate、五條 authority separation、六條 invariant 全程適用。**
14. **同一 working tree 只讓一個 writer**（§0.5）；[666] 的兩個未 commit 檔不碰。

---

## 1. Step 5.0 基準快照（Z0，一個 commit）

寫 `docs/reports/2026-10-xx-phase5-baseline.md`，每個數字附命令：

1. `python -m pytest -q` 總數、測試檔數、函式層級名單（`git grep -n -E "^\s*(async )?def test_" HEAD -- 'tests/*.py' | wc -l`）；`python -m audit invariants`。
2. 追蹤表：`python scripts/outcome_if_settled_today.py --no-benchmark` 全文存檔（22 列、三量、錨點體檢、live 段；5.0 實際以不寫檔的包裝跑，§0.6 #1）；`positions.json` 的 `content_digest`、`aggregate`、`power_law`、`anchor_health`、`counters`；`outcome_aggregate.jsonl` 行數與最後一行。
3. 心跳：`python -m crons.heartbeat --out <scratchpad>/hb_base.md`，段 4 逐行存檔；`SNAPSHOT_KEYS` 清單。
4. 敘事：4 檔 v2 第一份的 `brief_id`／`created_at`／`candidate_state.state`；v1 最早日期。
5. 讀圖：15 筆的 `reading_id`／`node`／`unit`／`kind`／`created_at`／`expires`／`supersedes_id`／`result_digest`／`retracted`；按 §5 的規則**手算**一次預測表（預期：斷言 2 筆 `open`、非斷言、`rewritten` 若干、對／錯 0）——這份手算是 5.4 的對照答案。
6. 反證 watch：來源 `reading:` 的 35 筆各自狀態、`judgment` 有無；`semantic_flag` 的結構（哪個欄位指到文件 id）。
7. 主題等權組：`cohort_id`、成員 ticker 與各自 yfinance 能不能取到收盤（`python -c` 逐檔試；印缺的）。
8. 計分表：`account_scorecard.json` 的 `price_budget`、五欄有值的格、`measurement_start`。
9. trade_log sha256、舊店三個 `*.db` sha256、`live_choices` 數、Sheet alpha 持股（唯讀 `python fetchers/gsheets.py --summary`）。
10. Phase 4 尾巴：[666] 的 RA 紀錄 state、`stash@{0}` 的 diff 摘要（`git stash show -p stash@{0}`）、`query/layer_stats.py` 判「新」的那一行、`graph_walk.py` 第 1 型降級的那一段。
11. 候選板 `counts`、`side` 計數、`no_narrative` 數。

L11-6 ④（本 Step）：沒有改動；但手算預測表時若發現 §5 的規則對現有 15 筆分不出來的情況（例：supersede 鏈分岔），**寫進 baseline 並回頭修 §5**，不要等到 5.4 才撞。

## 2. Step 5.1 Phase 4 尾巴（Z1，R1；四個小 commit 可）

| 件 | 改哪裡 | 怎麼改 | 怎麼驗 |
|---|---|---|---|
| #29 ③b 認 supersede | `query/layer_stats.py` | 「新」改成兩種都算：id 不在凍結集合、**或** id 在集合但 `collapse` 輸入的內容 digest（quote＋sub＋evidence 的 canonical）與凍結時不同——凍結集合要補存當時的內容 digest（`config/graph_baselines.json` 的 phase4 集合只存 id：5.1 補一份 `assertion_digests`，由當下的圖算、append-only、不改既有 id 集合）；兩種分開計數（`new`／`superseded`），③b 的分母＝兩者之和 | 夾具：同 id 換引文 → 進分母；真實資料：今天 superseded 應為 0（[666] 未重試）且 `new` 與 Phase 4 結案相同；變異：拿掉 digest 比對 → 紅 |
| #33 第 2 型降級 | `query/graph_walk.py` | 讀圖 ledger 讀不到／有壞行時第 2 型與第 1 型同形：`upstream_unavailable`、母體與命中都不印數字；`tests/test_graph_walk.py:152-159` 的對稱面補第 2 型 | 變異：第 2 型照算 → 紅 |
| #34 `classified_by` 字彙 | `engine_b/leads.py`（封閉字彙）、`config/lead_ref_keys.json`（若字彙住這裡）、鑄號 CLI | 加 `interactive:directed`（互動研究、非走圖命中）；既有 cw_dfb lead 的紀錄**不改寫**（lead registry 是 authority；改資料要走 pq2——登記 §14）；心跳與 `queue_segments` 分開計 | argparse 與函式兩層拒收未登記值；既有值照收 |
| stash 預熱清單 | `schema/neo4j_setup.cypher` 1b、新測試 | `git stash pop`（或 `git stash apply` 後確認 diff 只有這兩處）；測試「loader 會 SET 的屬性名 ⊆ 預熱清單」；變異：刪掉 `origin_linkage` 那行 → 紅 | 測試綠；`git stash list` 為空 |
| apply 入口 `db.propertyKeys()` | `scripts/apply_ra_admission.py` | apply 前以**唯讀** session 查 `CALL db.propertyKeys()`，與 loader 會寫的屬性名集合比對，缺就 fail closed 並印「缺 X，請 admin 執行 setup 1b 預熱」——戳記在這之後才寫（缺 token 不留戳記）；Neo4j 讀不到 → fail closed 印 `upstream_unavailable` | 夾具 driver 回缺一個名 → 拒絕且無戳記；全在 → 照舊 |

HUMAN SUMMARY 末尾印 [666] 重試指令（§0.5）。
L11-6 ④：#29 若判錯，最先壞的是結案時 Phase 4 的 ③b 數字（0／0）——重跑 `layer_stats` 對今天的圖，`new` 必須與 closeout §2 相同（4 筆）。

## 3. Step 5.2 量測層三條 lane＋籃子基準（Z2，R1）

**改哪裡：** `scripts/outcome_if_settled_today.py`（`collect()`、`_render`、`_persist_aggregate`、新的 lane 函式）、`webapp/materialize.py::materialize_positions`／`build_positions_artifact`、`webapp/contracts.py`（`STATE_SCHEMA_VERSIONS["positions"]` → `/2`）、`crons/heartbeat.py::build_positions`＋`SNAPSHOT_KEYS`、`webapp/static/app.js`／`index.html` positions 頁、`tests/test_heartbeat.py`、`tests/test_webapp_positions.py`、新 `tests/test_measurement_lanes.py`、`docs/OPERATIONS.md`（sandbox impact review 紀錄）。

**三條 lane 的定義（純函式，各自一個 builder；`collect()` 回 `{"lanes": {...}, "benchmarks": ...}`）：**

| lane | 列 | 錨點 | 列上另印 |
|---|---|---|---|
| `live` | `library/trades/trade_log.jsonl` 裡 `side=buy` 且**不是 beta**（symbol 不在 `config/beta_policy.json` 任一 `sheet_aliases`，沿 `risk/hard_caps` 既有的 alpha 判別）的每一筆事件；同 symbol＋broker 之後的 `sell` 事件把對應買進列標 `closed`（賣出價＝終點、`realized`），今天 0 筆 | `executed_at` 的排程時區日期與成交價、成交幣別；現價取**成交代號**的 provider 序列（`identity/execution.py` 的 yfinance 別名，FRA:2DG → 2DG.F），幣別必須等於成交幣別，否則 `currency_mismatch` 缺席、不猜匯率 | `research_receipt`：有 → `declared.candidate_state`、`brief_id`、`answers`；`backfilled` → 印「回填、無當時收據」；沒有（舊事件）→ `receipt_absent`。beta 事件數另印「beta 事件 N 不進 lane」 |
| `paper` | 敘事 ledger 每個 ticker 檔裡**最早一筆 `record_version=investor-brief/v2` 且未撤回**的紀錄（不是 `select_brief` 的現行那筆） | `created_at` 的排程時區日期；錨點價＝研究 ticker 的 provider 序列在那天或之前最近的收盤；缺序列 → `no_price_series` 缺席 | 當時 `candidate_state.state`、現行 state（`select_brief`）、換版次數；`first_named_by`＝`pending_leads.json` 裡 `entities.company_ids` 含本公司的最早 lead 的 `source`＋日期（沒有 → `no_lead_named`）；v1 最早日期（只印）；30 天敘事前漲幅（沿 `_pre_anchor_return`） |
| `history` | 舊店 observed shadow（現在的 22 列）——**程式路徑不動**，只改名與分段 | 不變 | `known_biases` 不變；「不再新增」一句印在表頭 |

**每條 lane 各算：** `equal_weight_aggregate`、`power_law_aggregate`（既有純函式直接套，量測起始日＝該 lane 最早錨點）、對 QQQ／SOXX 的超額（既有）、**對主題等權組的超額**：`alpha/providers/theme_cohorts.current_cohorts()` 取現行組（0 組 → `not_yet_recorded`「主題等權組未定義」），每列的籃子報酬＝成員（排除本檔）在錨點日→現價日的等權平均（每個成員兩端都取該日或之前最近收盤；取不到的成員列出、不進平均；`members_used/members_total` 印在列上）；lane 層級印 `cohort_id`、`decided_on`、成員數、缺價成員。**只印不比**。
提醒：IQE.L 是 GBp——成員報酬是同序列相除，單位自動相消；但 live／paper 的錨點與現價仍走 `_to_settlement`。

**`_persist_aggregate`：** 既有四欄＝history lane（與過去相同、序列不斷）；新增 `lanes: {live: {...}, paper: {...}, history: {...}}`（各含 `n`、`measurement_start`、aggregate、power_law、cohort_excess）。同日去重照舊。
**`materialize_positions`：** artifact 升 `stockbot-app/positions/2`，`rows`＝history（舊讀者不壞）、新增 `lanes`；`freshness_identity` 加三條 lane 的 ticker 集合與 `measurement_start`（價格變動不算認知變化）。`this_is_not` 加一句：「paper lane 的錨點是我們寫下判斷那天，量的是判斷不是進場；live 才是買得準不準」。
**心跳段 4：** 「追蹤表 history 22｜paper N｜live N」一行；每條 lane 一行三量＋對主題等權組超額（lane 空時印「還沒有列」不印 0%）；「入圖前已漲」改成 history 的「入圖前已漲」與 paper 的「敘事前已漲」兩格；`SNAPSHOT_KEYS` 加 `positions.lane.paper.n`／`live.n`／`reached_2x_ever` 各 lane，讓較昨 diff 看得到。
**APP positions 頁：** 三張表分段（history 的表沿用現在的欄位；paper 多候選狀態與 `first_named_by`；live 多收據欄）；頁首印 lane 定義一句與 `this_is_not`。

**網路上限：** 新常數 `MAX_LANE_SYMBOLS`（例 60）：paper＋live＋籃子成員＋基準去重後超過就截斷、**把截掉的印出來**（同 `MAX_PRICED_SYMBOLS`）。

**5.0 帶進來的三件（§0.6 #1、#3、#4）：** ①`--no-benchmark`（診斷旗標）時 `_render` 不呼叫 `_persist_aggregate`——daily 的 argv 不帶它，序列照舊；②主題等權組報酬函式取價濾 NaN（照 `_provider_series` 的 `.dropna()`＋`close == close`；IQE.L、SIVE.ST 今天就有 10-01 的 NaN 收盤）；③`current_cohorts()` 回（組清單, 壞行清單）兩項，壞行數印在 lane 層（INV-3）。

**sandbox impact review（同 commit 寫進 OPERATIONS 既有那一節）：** `05_outcome` 步驟 argv 不變；網路 surface 由「22 檔＋2 基準」變「上限 `MAX_LANE_SYMBOLS`」；寫入仍只有 `library/private/decision_lab/outcome_aggregate.json(l)`；`materialize --positions` 仍只呼叫 `collect()`（不寫聚合檔）。

**怎麼驗：** 夾具 trade_log（1 筆 alpha 有收據、1 筆 backfilled、1 筆 beta、1 筆賣出）＋夾具敘事 ledger（2 檔 v2、其中 1 檔有 v1 在前）＋夾具組＋注入價格 loader → 三 lane 列數、錨點、三量、籃子超額、缺席 kind 逐格斷言；真實資料：同一份價格上 history 22 列與改前逐位相同（`rows` 與 `power_law` 的 digest）、跨日錨點 digest＝baseline §2 的 `6ea352ed…7b93`（§0.6 #4）、paper 4 列錨點 2026-09-29（SIVE.ST 以第一份 v2 09-29 為準，不是 10-01 換版）、live 0 列＋「beta 事件 2 不進 lane」；心跳段 4 與 5.0 逐行對照只在預期處變；變異：lane 混算（paper 進 history 分母）→ 紅；成員不排除本檔 → 紅；幣別不一致仍算 → 紅；籃子取價不濾 NaN → 紅；`--no-benchmark` 寫了聚合檔 → 紅。
L11-6 ④：最先壞的是 `outcome_aggregate.jsonl` 的歷史四欄（既有消費端 `_outcome_series`）——跑完後讀最後一行，四欄的值必須等於 history lane 的值。

## 4. Step 5.3 `record_trade.py --backfill-before-receipts`（Z2，R1 ＋ R2-a 常規 opt-in）

**改哪裡：** `scripts/record_trade.py`、`portfolio/research_receipt.py`（`NARRATIVE_STATES` 加 `backfilled`、`build_receipt` 的回填分支）、`tests/test_record_trade_receipt.py`、`tests/test_record_trade.py`、`docs/OPERATIONS.md`（記成交那一節補「回填舊成交」）。

**怎麼改：**
- 新旗標 `--backfill-before-receipts "<理由>"`：①必須同時給 `--log-only`（Sheet 已是現況，不碰）；②`executed_at` 的日期必須早於 `RECEIPT_EPOCH = 2026-09-30`（收據機制上線日，常數＋註解；等於或之後一律拒收「這筆應該走正常路徑」）；③只收 alpha（beta 本來不需要收據 → 拒收並說明）；④收據＝`{"version": RECEIPT_VERSION, "side", "why", "sheet_symbol", "company_id", "research_ticker", "resolution", "narrative": "backfilled", "narrative_label": "回填：成交早於收據機制上線，當時沒有收據", "backfill_reason": <理由>, "declared": None, "derived": None}`——**不讀敘事、不讀候選板、不讀個股頁**（不拿今天的判斷冒充當時）；⑤硬擋照跑（`--log-only` 既有語意：不碰現金格、照算 5% 與 ETF cap）；⑥同 `trade_id` 重跑照舊 fail closed；⑦賣出回填不要求 `--disproof-watch`。
- 不改 `--open-position`、`--apply` 任何路徑；不改 Sheet 讀寫。

**怎麼驗：** 假 Sheet＋暫存 trade_log：合法回填一筆 → 事件帶 `research_receipt.narrative == "backfilled"`、Sheet 零寫入；缺 `--log-only` 拒；日期 ≥ epoch 拒；beta 拒；沒理由拒；硬擋超 5% 仍擋；變異：回填分支讀了敘事 ledger → 紅（夾具不給 ledger 路徑，讀就炸）。真實 trade_log sha 不變。
**R2-a `WORK_REQUEST`**：審查者以假 Sheet 跑七種拒收、一種放行，並確認 `--apply` 路徑 0 行變動、`NARRATIVE_STATES` 封閉性測試仍在。
HUMAN SUMMARY 末尾印回填指令範本（使用者照 Sheet 填：COHR 2026-08-18 10 股 @316.23 USD IB；FRA:2DG 的成交日與價由使用者給）。
L11-6 ④：最先壞的是現行 `--log-only` 的正常路徑（它仍要讀今天的敘事建收據）——測試矩陣裡保留一條「不帶旗標的 `--log-only` 收據仍是 `present`」。

## 5. Step 5.4 圖預測對錯表（Z2，R1）

**改哪裡：** 新 `alpha/structure_reading/predictions.py`（純函式）、`webapp/materialize.py::materialize_structure_readings`（讀 ledger 的那支；加 `predictions` 段、schema `structure_readings/2`）、`webapp/contracts.py`、讀圖頁 `app.js`、`crons/heartbeat.py` 段 4 一行、新 `tests/test_reading_predictions.py`。

**輸入：** 每個節點 ledger 的全部紀錄（含撤回）、語意 watch（`kind == "semantic_condition"`、`source_ref` 以 `reading:<reading_id>#` 開頭——格式是 `reading:<id>#<第幾條>`，§0.6 #5）、lead registry 的 `published_at`（`disproof_touched` 的種類用）、SourceDoc `published_at` 對照表（`materialize` 那次連線以唯讀 Cypher 取 `doc_id → published_at`；Neo4j 讀不到 → 種類欄整段 `upstream_unavailable`，終局欄照算）、today。

**每一筆讀圖 r 的終局（封閉字彙，一筆恰好一格）：**

| 終局 | 判準 | 算什麼 |
|---|---|---|
| `non_assertion` | `r.kind ∉ {moat, volume}`（neither／undecided） | 母體，不判 |
| `retracted` | `r.retracted` | 錯；種類依撤回它的那筆（若有 supersedes 指向它的紀錄）多出的 citation 算，沒有 → `undated` |
| `rewritten` | 有後繼 s（`s.supersedes_id == r.reading_id`）、r 在 `s.created_on` 當天未到期，且下列任一：①`s.result_digest == r.result_digest`；②`s.kind == r.kind`，而 `s.record_version != r.record_version` 或 `new_sources(s, r)`（定義見 `reversed` 列）為空。**不同 kind 不套②**（§0.6 #2） | 改寫（schema 升版、補引文、查詢程式改版後重存快照、同一輪研究內補寫），不算對錯 |
| `held` | 有後繼 s、不是 `rewritten`、`s.kind == r.kind` | 對 |
| `reversed` | 有後繼 s、不是 `rewritten`、`s.kind != r.kind`（含翻成 neither／undecided） | 錯；種類：`new_sources = {c.source_id for c in s.citations} − {… for c in r.citations}`，取它們的 `published_at` 最小值：`< r.created_on` → `already_available`（當時已有反例＝讀得不夠）；全部 `≥` → `emerged_later`（之後才出現＝判斷錯）；沒有新來源或都沒日期 → `undated` |
| `disproof_touched` | 沒有後繼，且任一 `source_ref` 為 `reading:<r.reading_id>#n` 的語意 watch 帶**單數** `judgment` 且 `judgment.touches == "yes"`（判無關寫在複數 `judgments`，不算） | 錯；種類：`judgment.lead_id` → lead registry 那則的 `published_at` 對 `r.created_on`，同上三分；`lead_id` 為 null（`record_touched` 那條路）或 `published_at` 空 → `undated`（baseline §6） |
| `expired_unread` | 沒有後繼、未觸及、`today > r.expires` | 到期未重讀（與走圖第 4 型同一件事，這裡只是終局視角） |
| `open` | 其餘 | 現行 |

**輸出：** 逐筆列（node／unit／kind／created_on／expires／終局／錯的種類／依據的 reading 或 watch id／反例文件 id 與 `published_at`）＋計數 `{held, reversed:{already_available, emerged_later, undated}, disproof_touched:{同}, retracted:{同}, rewritten, open, expired_unread, non_assertion}`＋`earliest_open_expiry`（結案登記回查用）。供給側變了但還沒重讀的筆數**不在這張表**（那是 staleness 的事，只印一句「stale 待重讀 N 見讀圖頁」）。
**心跳段 4 一行：** `圖預測：對 N｜錯 M（當時已有 a／之後才出現 b／未定日 c）｜現行 K｜到期未重讀 J｜改寫 R｜非斷言 Z`；`SNAPSHOT_KEYS` 加對／錯／到期未重讀。
**讀圖頁：** 一張表，終局與種類用字彙的中文；每列連到那筆讀圖。

**怎麼驗：** 夾具 ledger：鏈 A（volume → 同日 v3 改寫 → 圖變後 volume、帶一份新來源）＝`rewritten`＋`held`；鏈 A'（同 kind、digest 變了但沒有新來源；另一條 v2→v3 digest 變）＝兩筆都 `rewritten`（§0.6 #2 的負向對照）；鏈 B（moat → 到期後 neither，新 citation 的文件 `published_at` 早於舊讀圖）＝`reversed/already_available`；鏈 C（volume，watch 觸及、文件晚於讀圖）＝`disproof_touched/emerged_later`；鏈 D（undecided）＝`non_assertion`；鏈 E（撤回）＝`retracted/undated`；真實資料：與 baseline §5.2 的修正後手算逐筆相同（`held` 0、錯 0、`rewritten` 9、`open` 2、`non_assertion` 4；SuperNova 09-25 那筆＝`non_assertion`）；變異：把 `supply_added` 接進來 → 紅（測試斷言 staleness 的變化不改終局）；`published_at` 缺時壓成 `emerged_later` → 紅；拿掉條件②（同 kind 只看 digest）→ 真實資料 `held` 變 5、紅；`source_ref` 改回全等比對 → 鏈 C 的觸及 0 命中、紅。
L11-6 ④：最先壞的是 inp 鏈 `sr_88340b81…`、`sr_6ad5c884…`、`sr_ad503ae8…` 與 cw 鏈 `sr_a6762186…`、`sr_a181641d…` 五筆（digest 變了，但變的是查法不是圖，baseline §5.1）——若規則把它們判成 `held`，那是改寫被算成驗證。

## 6. Step 5.5 計分表接主題等權組基準（Z1，R1）

**改哪裡：** `engine_b/account_scorecard.py`（`score_account`、`build_scorecard`、`render`）、APP 計分表頁、`tests/test_account_scorecard.py`、`crons/heartbeat.py` 段 5（只加「籃子基準：有／無」一格，不印數字）。
**怎麼改：** 先修取價：`_yfinance_closes` 跳過 NaN 收盤（§0.6 #3；今天「點名後 90 天 vs SOXX」＝NaN）。讀現行主題等權組（0 組 → 每個籃子格 `not_yet_recorded`）；成員 ticker 併進 `wanted`（仍受 `MAX_PRICED_SYMBOLS`，被截的印出）；對每則點名、每個 horizon 算 `excess_{h}d_vs_theme_cohort`＝本檔報酬 − 成員（排除本檔）等權報酬；`metrics` 多這幾格（`Metric`，缺席同既有 `insufficient_sample`／`revisit_after` 規則）；payload 多 `theme_cohort: {cohort_id, decided_on, members_total, members_priced, missing[]}`；`KNOWN_BIASES` 加一條「籃子成分是 2026-09-30 定的、對更早的點名是回溯」；`render` 與 APP 各印；`freshness_identity` 加籃子格有沒有值。
**怎麼驗：** 注入 loader 的夾具：兩個成員＋一檔點名 → 籃子超額等於手算；本檔是成員時被排除；組缺席 → `not_yet_recorded`；真實資料：`price_budget.requested` 增加的數＝成員中原本不在取價清單的檔數（`wanted` 是集合、會去重）；同一份價格上五欄既有值除被 NaN 污染的格以外逐位不變，污染的格逐格列出改前改後（§0.6 #3）；變異：拿掉 NaN 過濾 → 夾具（一檔終點是 NaN 收盤）紅。
L11-6 ④：最先壞的是 `price_budget` 截斷邏輯（基準永遠留著的那段）——籃子成員不是基準、可被截，截掉就整格缺席並印出，不得讓基準被擠掉。

## 7. Step 5.6 候選狀態每日序列（Z1，R1）

**改哪裡：** `webapp/materialize.py::materialize_candidates`、新 `library/private/measurement/`（目錄由程式建）、`tests/test_webapp_candidates*.py`、`docs/OPERATIONS.md`（sandbox impact review：materialize 新寫入路徑）。
**怎麼改：** artifact 寫完後 append `{"date", "counts": {open, missing, priced_wait, pass, held}, "side": {not_multiple, edge_unmeasurable, legacy, precondition_failed}, "no_narrative", "oldest_stall_days", "generated_at"}`；同日重跑只留最後一筆（照 `_persist_aggregate` 的做法，壞行只跳過）；只寫不讀；寫失敗不讓 materialize 失敗（印警告）。
**怎麼驗：** 暫存目錄：兩次同日 → 1 行；跨日 → 2 行；壞行不吞掉整檔。真實跑一次 materialize 後檔案出現第一行、`counts` 與 artifact 的 `counts` 相同。
L11-6 ④：最先壞的是 `materialize --candidates` 的 request path 哨兵（`tests/test_webapp_request_path.py`）——新寫入必須在 materialize 端、不在任何 request path。

## 8. Step 5.7 新管線 full chain 測試（Z1，R1）

新 `tests/test_measurement_full_chain.py`：夾具 trade_log＋敘事 ledger＋組＋讀圖 ledger＋watch＋注入價格 → `collect()` 三 lane → `build_positions_artifact` → 心跳段 4 的那幾行；`prediction_table` → `structure_readings` artifact 的 `predictions` 段 → 心跳那一行；`build_scorecard` 的籃子格。斷言的是**數字出現在下游**（artifact 與心跳文字），不是函式會動（L13）。既有 `tests/test_full_chain_acceptance.py` 不動。

## 11. 驗收數的是哪一層（completion gate 第九項）

| 驗收 | 數的東西 | 層 |
|---|---|---|
| ROADMAP ① 追蹤表印籃子超額 | paper／live 每列與 lane 聚合的 `excess_theme_cohort` 有值或有缺席 kind；history 不要求（它不是判斷） | 追蹤表 |
| ROADMAP ② 圖預測表有第一筆對／錯，每筆「錯」標明種類 | `predictions` 的 `held + reversed + disproof_touched + retracted` ≥ 1 且每筆錯有種類；**結案時若為 0**：夾具測試證明機制、closeout 寫「已交付、未生效」、登記 date watch 回查（到期日＝`earliest_open_expiry`，今天是 2026-12-24） | 讀圖 × 等待 registry |
| ROADMAP ③ 計分表印量測起始日與樣本數 | 既有 `measurement_start`／`named_calls` 照印；新加籃子格的 `n` 與 `members_priced` | 計分表 |
| 三條 lane | history 22 列：錨點 digest 與 5.0 相同、同一份價格上 rows／power_law 逐位相同（§0.6 #4）；paper 4 列、錨點 2026-09-29、三量每格有值或「還沒有分母」；live 0 列（或使用者回填後的 N 列，逐筆附指令時間）＋「beta 事件 2 不進 lane」 | 追蹤表 |
| 候選狀態序列 | `candidate_state_series.jsonl` 行數＝結案日 − 5.6 交付日 ＋ 1（daily 每天一行） | 追蹤表 |
| Phase 4 尾巴 | ③b 的 `new`／`superseded` 兩格印出且今天 superseded 0；第 2 型降級夾具；`classified_by` 新值；stash 為空；入口對缺 token 的夾具 fail closed | 機制存在與否 |
| 回填旗標 | 七種拒收一種放行的測試；真實 trade_log sha 與 5.0 相同（或列出使用者回填的事件） | 機制存在與否 |

**沒有任何一個是「幾檔通過某個 filter」。** 候選板「可開」數只印不驗收。

## 12. Phase 5 結案（completion gate：historical-failure-matrix §9 八項 ＋ 第九項）

1. `pytest -q` 全綠；測試檔數差＝新增－退役；函式層級以 5.0 名單比對，拿掉的每一個寫去向。
2. `python -m audit invariants` 綠。
3. 無未解釋語意 diff：心跳與 5.0 逐行對照，只在段 4（lane 行、預測行）、段 5（籃子基準格）預期處變；個股頁核心面板 digest 0 檔變（本 Phase 不碰敘事與讀圖）；history lane 的 22 列錨點 digest 與 5.0 相同、同一份價格上三量逐位相同（§0.6 #4）。
4. 無新 dual authority：三量與等權只有 `outcome_if_settled_today.py` 的兩個純函式（三 lane、APP、心跳共用）；籃子報酬只有一個函式（追蹤表與計分表共用——放 `alpha/theme_cohort.py` 或新模組，兩個消費端 import 同一個）；預測終局只有 `predictions.py`；alpha 判別沿 `risk/hard_caps` 既有函式；symbol → 公司只走 `resolve_holding`。
5. 無 silent drop：每條 lane 空時印「還沒有列」；分母 0 印「還沒有分母」；籃子缺價成員逐檔印；預測表 `undated` 與 `upstream_unavailable` 分開；截斷的 symbol 印出。
6. Point-in-time：錨點價是錨點日或之前的收盤（測試）；預測表種類只看 `published_at`；`audit PointInTime` PASS。
7. lifecycle 可達：結案登記的回查 date watch 有到期；`QueueLiveness` 綠。
8. executable protection：回填旗標七種拒收、lane 混算變異紅、`supply_added` 接入變異紅、入口缺 token fail closed、`_persist_aggregate` 四欄不變的測試；殭屍 grep 九組三個 0。
9. 驗收數的是 §11 的層。

**另核對：** 舊店三個 `*.db` sha256 ＝ 5.0；`trade_log.jsonl` sha ＝ 5.0（或列出使用者回填）；`git diff <5.0> HEAD -- AGENTS.md` 為空；敘事、讀圖、組、watch 四個 ledger sha ＝ 5.0（結案登記的 date watch 除外）；Google Sheet 本 Phase 沒有任何程式寫入（`record_trade.py` 試跑全是 dry-run）；`python -m webapp status` 仍列 8 個 kind。

closeout 報告存 `docs/reports/2026-10-xx-phase5-closeout.md`，附「本 Phase 執行中發現、下一步要決定的問題」（§14 種子＋執行中新增），並附一段「證據判準 brainstorm 的題目清單」（§0.1 #6 延後的 10 題，各附結案當天量到的數字）。

### 結案 R2（使用者已常規 opt-in；執行者不必再問）

```
WORK_REQUEST（R2，Phase 5 結案）
Target: master 最新 commit；docs/reports/…-phase5-baseline.md、…-phase5-closeout.md；
        docs/plans/2026-10-02-001-feat-phase5-measurement-plan.md（§0.4 amendment、§0.6 偏差）
Claimed acceptance: Phase 5 completion gate 九項全過、ROADMAP Phase 5 驗收①③成立、②依 §11 的兩種寫法之一（見 closeout）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python -m pytest -q；python -m audit invariants；測試函式層級增刪自己比（5.0 commit 起）
  2. 追蹤表：python scripts/outcome_if_settled_today.py --no-benchmark（5.2 起它不寫聚合檔）；history 22 列的錨點 digest 與 5.0 baseline §2 比（現價跨日會變，不比 rows digest）；paper 4 列的錨點日與第一份 v2 敘事的 created_at 逐筆核；
     三量用自己寫的十行腳本重算一次；籃子超額抽 2 列手算（成員排除本檔、缺價成員列出）；outcome_aggregate.jsonl 既有四欄與舊行逐位不變
  3. 預測表：對 15 筆真實讀圖自己依 plan §5 的表手判一次，與 artifact 逐筆比；自造夾具鏈（含 supply_added 不得判錯）；Neo4j 關掉時種類欄是 upstream_unavailable 不是 undated
  4. 計分表：籃子格的 n 與 members_priced；五欄既有值逐位不變；price_budget 的增量＝成員數
  5. 回填旗標：假 Sheet 跑七種拒收一種放行；--apply 路徑 0 行 diff；真實 trade_log sha（或使用者回填的事件逐筆對照指令）
  6. Phase 4 尾巴：layer_stats 的 new／superseded 對今天的圖；第 2 型降級夾具；stash 為空；入口缺 token fail closed（夾具）
  7. 心跳：與 5.0 逐行對照，未解釋 diff 0；SNAPSHOT_KEYS 新鍵在快照裡
  8. python scripts/retired_mechanism_grep.py 三個 0；Decision Store 三檔、AGENTS.md、四個 ledger 不變；Sheet 沒有程式寫入
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不寫任何 ledger、不跑 record_trade.py --apply／--log-only
```

### 結案之後：停，不要開 Phase 6

R2 回 GO 後：ROADMAP Phase 5 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。然後 **`AWAITING_HUMAN`**：ROADMAP 沒有 Phase 6——HUMAN SUMMARY 的「下一步」印兩件事：①「證據判準 brainstorm」的題目清單在 closeout 哪一節；②`docs/plans/README.md`「每個 Phase 開工前要有一份 plan」那段指令。

## 13. 已知陷阱

- **`outcome_if_settled_today.py` 是 daily 步驟 05、也被 `materialize --positions` 以檔案路徑 import**：`collect()` 的回傳形狀變了，`materialize_positions` 同 commit 改；materialize **不得**呼叫 render（render 會寫聚合檔）。
- **`_persist_aggregate` 既有四欄是 brief／APP 時序的既有消費端（`_outcome_series`）**：四欄＝history lane，新資料只能加 `lanes`；同日去重照舊。
- **研究 ticker ≠ 成交代號 ≠ 行情符號**：SIVE.ST（研究、SEK）／FRA:2DG（Sheet、EUR）／2DG.F（yfinance）——live lane 用成交代號的行情、paper lane 用研究 ticker 的行情，兩邊各自與自己的錨點同幣別；`identity/execution.py::_YFINANCE_SYMBOL_ALIASES` 是唯一對照。IQE.L 報價是 GBp（`identity.currency.resolve_quote_unit`）。
- **敘事「第一份 v2」不是 `select_brief`**：`select_brief` 取現行最新；錨點要的是最早的 v2——自己走一遍紀錄、跳過撤回；v1 只印日期不當錨。
- **`created_at` 是 UTC**：日期用排程時區（`engine_b.event_watch._local_timezone()`，沿 `research_receipt._local_date` 的退回規則）。
- **主題等權組成員 ticker 是 registry 的研究 ticker**：yfinance 對 `.TWO`／`.TW`／`.ST`／`.L` 都取得到，但要逐檔試（5.0 第 7 項），取不到的成員必須印出。成員含本檔時排除；組變動（supersede）時籃子跟著現行組，列上印 `cohort_id` 讓讀者看得出換過。
- **讀圖 supersede 鏈的改寫**（5.0 實測更正，§0.6 #2）：digest 相同的環節只有 4 個（inp `sr_81832cb3…→sr_88340b81…`、`sr_bc1ccb56…→sr_ad503ae8…`，cw `sr_caac0aca…→sr_d0767997…`、`sr_d0767997…→sr_d49b81b6…`）；另有 5 個同 kind 環節 digest 不同，但差異來自查詢程式改版與 schema 升版、兩邊都沒有新來源——修正後的規則照樣判 `rewritten`；SuperNova 09-25→10-01 digest 不同但兩筆都是 undecided → 前者 `non_assertion`（不是 `held`）。
- **`judgment.touches` 的值是字串 `"yes"`／`"no"`**（不是布林）；觸及在單數 `judgment`、判無關在複數 `judgments`；`source_ref` 是 `reading:<id>#n`；文件日期走 `judgment.lead_id` → lead 的 `published_at`（baseline §6）。
- **yfinance 對歐洲標的會回一根 NaN 收盤**（2026-10-01：IQE.L、SHA0.DE、SIVE.ST、SOI.PA、XFAB.PA）——任何新取價都要濾（`.dropna()`＋`close == close`），否則中位數與等權平均被靜默污染（baseline §8）。
- **SourceDoc `published_at` 有 13 份未定日**（PointInTime 207／220）：反例文件落在那 13 份 → `undated`，不猜。
- **心跳段 4／段 5 的格式被 `tests/test_heartbeat.py` 釘住**；`SNAPSHOT_KEYS` 是封閉清單，加鍵要同 commit 改測試；舊快照沒有新鍵時 diff 印「首日」不印變動。
- **`STATE_SCHEMA_VERSIONS` 升版後舊 artifact 會觸發「型別不一致」警告一天**（Phase 4 同）。
- **`record_trade.py` 的 `--log-only` 既有語意**：Sheet 已是成交後狀態、不碰現金格、仍算硬擋、仍建收據——回填分支只換收據那一段，其餘不動；`RECEIPT_EPOCH` 是常數不是讀 trade_log 推（trade_log 今天沒有任何收據事件可推）。
- **beta 判別沿 `risk/hard_caps`**（`config/beta_policy.json` 的 `sheet_aliases`），不自己再寫一份（Phase 3 R2 抓過第二份判別）。
- **`layer_stats` 的凍結集合只存 id**（`config/graph_baselines.json`，append-only）：補內容 digest 是新鍵、不改既有鍵；引文全文不進 Git。
- **Neo4j 要開**：預測表的種類欄與 5.1 的 `db.propertyKeys()` 都要圖；讀不到印 `upstream_unavailable`、不印 0。
- **Windows**：python 不認 `/tmp`，暫存用 scratchpad；程式碼不放 heredoc；子行程用 `sys.executable`；PowerShell 管線會加 BOM。
- **可開為零就零**：候選板今天可開 0 是合法結果，序列裡的 0 也是。

## 14. 結案時要列的待決問題（種子；執行中發現的往下加）

1. **證據判準 brainstorm（結案後開，使用者 2026-10-02 定案延後）**：Phase 4 closeout §6 #1（sub 消費端忽略 `sub_language_in_quote=false`）、#2（外部印證要求引文具名）、#3（`counterparty_joint` 320 分支）、#4（`same_origin` 機械偵測）、#11（`co:openlight` 兩個 id）、#17（插槽 staleness 比 rank）、#20（稀釋燈分員工計畫）、#27（結構表單一最短錨）、#30（發布者整家升級）、#31（GSR 類別）——結案時各附當天量到的數字。
2. Phase 4 closeout §6 其餘資料口徑題照帶：#5、#6、#7（`graph_walk:*` 來源標籤走到量測——本 Phase paper lane 的 `first_named_by` 是第一步，lead 來源與走圖型別的對照留這裡）、#8、#9、#10、#12、#13、#14、#15、#16、#18、#19、#21、#23、#24、#25、#28、#32。
3. #34 的既有 cw_dfb lead 紀錄（`classified_by=interactive:graph_walk` 與 `directed:` 來源不一致）要不要改資料（lead registry 是 authority，走 pq2）。5.1 另查到同形的 3 則：`directed:sub_backfill` 的 `lead_3238fc77…`、`lead_39841af8…`、`lead_cbd50ac5…`（互動鑄號、標成預設 `triage_semantic_v1`）；5.1 起字彙有 `interactive:directed` 可用。
4. Phase 3 closeout §5 #14（Engine C 口徑）、#15（三題 as-of 視角）照帶。
5. history lane 什麼時候退役（它的三量在 paper／live 有足夠樣本前仍是唯一有歷史長度的序列）。
6. 主題等權組 supersede 時籃子序列的斷點怎麼呈現（本 Phase 只印 `cohort_id`）。
7. live lane 的賣出配對只做同 symbol＋broker 的 FIFO；分批買進、部分賣出的加權要不要做（今天 0 筆，L17：等有資料）。
8. 回填：FRA:2DG 的成交日與價由使用者提供；COHR 2026-08-18 10 股 @316.23（舊店 `ib-cohr-2026-08-18-10sh`）。
9. 預測表要不要納入 thesis memo 的反證觸及（今天 thesis 來源的語意 watch 16 筆）——ROADMAP 寫的是「讀圖斷言」，本 Phase 只做讀圖。
10. 計分表的籃子基準對 2026-09-30 之前的點名是回溯（已印在 `KNOWN_BIASES`）；要不要對每則點名記「點名時組是否已定義」。
