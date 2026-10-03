---
date: 2026-10-02
topic: phase6-evidence-criteria
status: active
derived_from: docs/ROADMAP.md（Phase 6 列；本 plan §0.4 amendment A1 新增）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G4、G5、G7、§6.6、§10）、docs/reports/2026-10-02-phase5-closeout.md §5–§6（證據判準 10 題與 Phase 5 留下的使用者題）、docs/reports/2026-10-02-phase4-closeout.md §6、AGENTS.md（L6、L8、L12、L13、L16、L17、L18、L19；INV-1、INV-5、INV-6）
---

# Phase 6 證據判準（給執行模型的完整 plan）

> **執行者：全程 opus 5.5（使用者 2026-10-02 定案 #13）**，走 `skills/development-flow/SKILL.md`（Z1 以上 R1）。本 Phase 有**一個研究 Step（6.8）**與兩處圖寫入（6.2、6.3），圖寫入一律等使用者對 pq2 編號 `go`。
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 6」（本 plan §0.4 的 amendment A1 新增）導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文（尤其「圖的寫入紀律」、L6／L8／L12／L13／L16／L17／L18／L19、INV-1／INV-6、「四個人工 gate」）→ ROADMAP「Phase 6」列 →
> 本 plan §0.1–§0.4 → `docs/reports/2026-10-02-phase4-closeout.md` §6（題目原文：#1–#4、#11、#12、#15、#16、#17、#20、#27、#30、#31、#32）→
> `query/origin_resolution.py` 全檔（三態解析、`PUBLISHER_KINDS` 封閉字彙、`publisher_lifts`）→ `query/bottleneck.py::classify_evidence`／`collapse_assertions`／`quote_names_company`／`company_id_for_origin`／`demand_chain`／`structure_table` →
> `query/structure.py::_classify_edges`／`build_socket_view` → `alpha/providers/structure_readings.py::verify_citations`／`_independence_problems` → `alpha/structure_reading/staleness.py`（`CHANGE_KINDS`、`_angle_changes`）→
> `query/layer_stats.py`、`query/sub_language.py`（字表的形狀與 L19 守門）→ `identity/registry.py`（`CompanyIdentity` 欄位、`by_ticker` 不收名字）→
> `loader/migrate_entity_dedup_20260904.py` 與 `loader/migrate_relation_rejudge.py` 檔頭（「改抽取檔 → scoped 重載 → 刪舊 → 重投影」與 additions 的限制）→ `loader/migrate_sourcedoc_json_section.py`、`loader/sourcedoc_sync.py` →
> `alpha/wipeout.py::dilution_flag` 與 `_DILUTION_RULE`、`engine_c/checklist.py::_equity_issuance`、`fetchers/edgar.py::get_filings` → `docs/OPERATIONS.md`「sandbox impact review 五步」→ `docs/refactor/historical-failure-matrix.md` §2。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表／機制），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字是**圖**（每條邊的證據等級與它的逐來源核對、身分）、**讀圖**（被標籤變更弄 stale 的那幾份有沒有重讀）、
> **敘事**（四檔 v2 敘事換版或不換版的理由；稽核區的稀釋燈）、**等待 registry**（本 Phase 鑄的 pq2 各到終局）、**機制存在與否**（見 §11）。
> ⚠ 證據等級**只會因為三種事變動**：本 Phase 的分類規則（只會讓標籤變保守）、資料更正（名冊寫法、名冊新公司、publishers、SourceDoc origin、身分合併），以及研究補回的引文（RA）。
> 每一次變動都要逐條列出「哪條邊、從什麼到什麼、因為哪個事件」——不准只報總數。

**一句話目標：** 讓「外部印證」這個標籤名副其實——印證來源必須是另一個實體、它自己的引文要逐字具名那家供應商、而且不是在轉述供應商自己的話；
把今天製造假印證的兩個身分錯誤修掉；讓下游（讀圖 staleness、sub、稀釋燈、結構表）不再把兩種意思壓成一格。**它不排序、不打分、不設門檻**：
標籤變保守是讓你讀到的「有客戶或第三方印證」可以信，不是新的 gate。

---

## 0.1 使用者定案（2026-10-02；15 題，使用者「這些都OK」＝全照建議）

| # | 題目 | 定案 |
|---|---|---|
| 1 | Phase 6 做什麼 | **a 證據判準**（全套）；研究量照「研究並行」在互動 session 跑、不進 Phase；海外財報是 Phase 7 候選 |
| 2 | 身分清理（Phase 4 #11、#12） | **a**：OpenLight 兩個代號合併（留 `co:openlight_photonics`）；`co:nava_thailand` 先以一手來源定案（Lumentum 自己的廠區 → 退役、邊改掛 Lumentum；真的是一家代工廠 → 補名字留著）；名冊改＋圖遷移走 pq2；遷移與 RA packet 印入圖副作用（Phase 4 #32） |
| 3 | 外部印證要不要求引文具名供應商（#2） | **a**：**逐來源**——印證來源自己的引文要逐字具名主詞（主詞是名冊公司時），否則那個來源只給「待判定」；名冊先補 Apollo／Arista／GF 三個寫法；產品名不算具名；截得不夠的在研究 Step 從同一份文件補具名引文（RA，pq2） |
| 4 | 轉述偵測（#30，#4 併入） | **a**：發布者的引文要「具名主詞且不是轉述句」才升；轉述動詞是帶版本的字表；偵測只會讓標籤變保守；翻案靠那份文件宣告 `origin_linkage=independent`（pq2）；媒體同一套，不另做 same_origin 偵測 |
| 5 | GSR 的類別（#31） | **a**：Global Semi Research 改登記為 `media`（跟另外 4 個 Substack 一致）；某一份有自己的數據時逐份宣告 independent |
| 6 | 聯合公告分支與解析不到的來源（#3，併 Phase 4 #15、#16） | **a**：聯合公告的字串偵測不改；另 8 份逐份解析——公司進名冊、發布者進 publishers、SourceDoc origin 更正走 pq2；那篇 CPO 綜述論文（Chen et al., Micromachines 2025, MDPI Review）只轉述廠商資料 → 登記為 `media` |
| 7 | sub 的消費端（#1） | **b**：「引文撐不撐得住」旗標跟著值走到每個消費端，不忽略；字表 v2 照 Phase 4 #18 延後 |
| 8 | 插槽讀圖 staleness 分級（#17） | **a**：同一級的標籤互換算低等級、跨級才算高等級；**排在任何改分類的動作之前做** |
| 9 | 稀釋燈：募資 vs 員工計畫（#20） | **a**：窗內有募資文件（424B、S-1／F-1、8-K 第 3.02 項）才亮黃；只有發行金額、沒有募資文件的不上色另列；EDGAR 申報清單要做 sandbox impact review |
| 10 | 結構表需求錨（#27） | **a**：逐列——從那一列的節點往上找最短錨，找不到才退回公司層並標「公司層」 |
| 11 | Phase 內的研究 Step | **a**：強模型①從降級邊的原文補具名引文（RA，pq2）②重讀 stale 的讀圖 ③四檔敘事中引用到變更標籤的，換版或寫明不換 |
| 12 | [666] | **b**：Step 6.0 第一件事，用使用者 10-02 的 `go` 重跑；入口照樣驗編號／digest／token；被權限分類器擋下就停下、把三行指令交給使用者，**不換方式繞過** |
| 13 | 執行者 | **a**：全程 opus 5.5 |
| 14 | 執行期間六條 trigger 命中的 R2 | **a 常規 opt-in**：預定兩處——**R2-a**＝Step 6.2（身分合併：INV-1＋authority 變更）、**R2-b**＝Step 6.6（稀釋燈改讀募資文件：財務時點＋新寫入面）；其他 Step 命中同樣直接發；條件修正後的覆核一律開新的、窄範圍的審查者（不喚回原審查者） |
| 15 | Phase 5 留下的使用者題 | **併入**：#11 APP 自偵舊程式、#12 排除未收盤 K 棒、#18 預測表改寫規則①收窄成「同 kind 或同日」、#3 四則 lead 的 `classified_by` 更正（一個 manual pq2）、#14 本機權限對 `record_trade.py`／`apply_ra_admission.py` 加「每次先問」（改使用者本機檔，使用者確認後生效）、#15 6.0 查一次有沒有 tier 決定引用過舊計分表數字；**照帶**：#5、#6、#9、#10（12-22 回查時一起看）；**使用者動作**：#8 FRA:2DG 回填 |

## 0.2 現況實測（2026-10-02 寫 plan 當下；**現況數字會腐壞，引用前重跑查證命令**）

| 事實 | 數字 | 查證 |
|---|---|---|
| canonical 邊與證據等級 | **537 條**（699 筆 assertion）：外部印證 244／自報·filing 107／自報 104／媒體轉述 37／待判定 37／雙方聯合 8 | `python -c "import collections; from query.structure import _load_edges; e=_load_edges(); print(len(e), collections.Counter(x.evidence for x in e).most_common())"` |
| 舊計數器「外部印證但引文不具名供應商」 | **15 條**——口徑是「這條邊任何一段引文具名」，**供應商自己的引文也算**，所以漏掉 Sivers→CW DFB 那種（撐它外部印證的是華星光年報，那段引文沒提 Sivers） | `library/private/app/state/graph_walk.json` 的 `layer_stats.ec_quote_does_not_name_supplier` |
| 草案規則的模擬（plan 作者在記憶體裡跑，**不是驗收基準**；6.0 要重算） | 25 條外部印證會掉級：身分 4（OpenLight 3、nava 1）、逐來源不具名 12、轉述 2（都是 Cignal AI：LITE→ELS pluggable、COHR→UHP）、GSR 7；外部印證 244 → 219；①「獨家且全自報」73 → 77（多 `tech:cpo_fiber_attach`、`tech:cpo_packaging_assembly`、`tech:els_pluggable_module`、`tech:mrm_200g`）；被碰到的現行讀圖：`mat:inp_substrate`、`tech:cw_dfb_laser`（兩份層讀圖）；有敘事的四檔全中 | §1 第 4 項給模擬口徑 |
| 只靠「研究機構類」發布者撐住的外部印證 | 24 條（GSR 7、SVRC 3、TrendForce 3、Open CPX MSA 3、Cignal AI 2、USGS 2、Harper Adams 2、Counterpoint 1、SemiconductorX 1） | 同上 |
| GSR 改 media 的連鎖 | AXT→InP 降為自報·filing（AXT 10-K）；住友／JX→InP 與兩條競爭邊退回 Reuters（今天未宣告＝媒體轉述；[666] 會把那份 Reuters 宣告為 independent）；Coherent／Lumentum→CW DFB 降為媒體轉述 | `config/publishers.json`（34 筆；GSR `seen_in=gsr_inp_substrate_market_2026_05_16`） |
| 解析不到的 SourceDoc | **16／220**：聯合公告 8（字串偵測判雙方聯合，8 條邊）＋名冊外公司 5（Credo、Noveon、Sojitz〔客戶端〕、Telescent、USA Rare Earth）＋`Novanta/ATI`＋`Soitec management (Reuters interview)`＋`Third-party Research`（`cpo_chip_package_paper` 與 `cpo_paper_coverage_addendum_2026_08_30` 兩份抽取檔、同一篇綜述論文，掛 31 條邊） | `query.origin_resolution.resolve_origin` 對每份 `origin_entity` |
| 身分 | 名冊 100 家；`co:openlight`（1 條邊，來自 `extractions/semitoday_ph18da_volume_2026_03_20.json`）與 `co:openlight_photonics`（4 條邊）同名同別名；`co:nava_thailand` 沒有 `display_name`（`_note`：看不出是代工廠還是 Lumentum 泰國廠所在地）、唯一來源是 `lumentum_q2fy26_cpo` 的兩段摘要句 | `config/company_identity.json`；`grep -rln '"co:openlight"' extractions/` |
| sub | 帶 sub 的 assertion 113 筆，引文含字表語言 11 筆；sub≥4 的 70 筆只有 7 筆撐得住（字表 v1·narrow，召回約一半） | `layer_stats.sub_language`；`query/sub_language.py` |
| 稀釋燈 | 73 檔：黃 11（AAOI、AXTI、COHR、INTC、IREN、LITE、LRCX、META、MP、MRVL、NVDA）；NVDA／MRVL／LRCX／META／INTC 的發行額 ≤ 市值 0.15% | `library/private/app/analyst_view/*.json` 的 `overview.wipeout.lanes[lane=dilution]`；Phase 4 baseline §22 |
| 結構表需求錨 | Lam 的 9 列全部錨在 `tech:dram_technology`（`demand_chain` 從**公司**走） | `library/private/app/state/structure_table.json` |
| 讀圖／敘事 | 現行讀圖 4 份（`mat:inp_substrate`、`tech:cw_dfb_laser` 兩份層讀圖；`prod:supernova`、`prod:els_8ch_module` 兩份插槽讀圖）；v2 敘事 4 檔（AXTI、COHR、LITE、SIVE.ST） | `ls library/private/alpha/structure_readings/ library/private/alpha/briefs/` |
| 候選板 | 可開 0｜缺 X 0｜等回落 1｜不要 0｜已持有 2｜非倍率候選 1｜無敘事 69 | `library/private/app/state/candidates.json` |
| [666] | `partial`（圖未動）；token 已存在、入口會先查 token；工作樹兩個未 commit 檔＝它的更正走廊產物 | `git status`；`library/private/research_actions/` |
| Phase 5 #15 | `config/signal_sources.json` 自建立後沒有變更（tier 從未升降）；pq2 池裡沒有引用計分表的 tier 項目 | `git log --oneline -- config/signal_sources.json` |
| 本機權限 | `.claude/settings.local.json`：allow 52 條（含 `Bash(python *)`）、ask 0、deny 0 | 讀檔 |
| 測試 | 3303 passed／1 skipped；`python -m audit invariants` 14 PASS（Phase 5 結案） | Phase 5 closeout §1 |

## 0.3 本 Phase 刻意不做

- **不排序、不打分、不設門檻**；不讓證據等級、sub 旗標、稀釋燈進任何候選狀態的前提或排序（G1、G6、INV-5）。候選板「可開」只印不驗收。
- **不忽略任何 sub 值**（§0.1 #7）；字表 v2 不做（Phase 4 #18 照帶）。
- **不改聯合公告的偵測**（§0.1 #6）；不新增 SourceDoc 的共同發行人欄位；不另做媒體 same_origin 偵測（由轉述字表涵蓋，§0.1 #4）。
- **轉述偵測只套在發布者 origin**；公司 origin（例如 NVIDIA 的部落格寫「Coherent announced…」）不套——今天沒有資料撐這一格（L17：機制只 general 到資料支持的那一格）。
- **不動 `routine_writer` 權限**；Neo4j 回 Forbidden 一律停下問使用者（不自行 admin 預熱再重試）。
- **不重建 Neo4j、不改 Engine C 既有表的 CHECK**（稀釋燈的募資文件住新表）。
- 不寫 trade_log、不寫 Google Sheet、不動舊 Decision Store、不動 thesis lifecycle；讀圖與敘事只在 Step 6.8 寫。
- 不改 `AGENTS.md` 判準句；不開新 state kind（產出住既有 kind：`graph_walk`、`structure_table`、`structure_readings`、個股頁）。
- 不做海外財報來源（Phase 7 候選）；不做 Phase 5 #5／#6／#9／#10；不碰邊緣門檻。

## 0.4 ROADMAP amendment（五欄；使用者 2026-10-02 定案；ROADMAP 同 commit 新增 Phase 6 列）

**A1｜新增 Phase 6「證據判準」**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 沒有 Phase 6；Phase 5 closeout §5 #1 列「證據判準 brainstorm」（Phase 4 closeout §6 的 10 題延後到 Phase 5 結案後一次定） |
| 新觀察 | 2026-10-02 在記憶體裡模擬草案規則：244 條外部印證有 25 條撐不住（身分 4、逐來源不具名 12、轉述 2、GSR 7），有敘事的四檔（AXTI、COHR、LITE、Sivers）全中；舊計數器只抓到 15 條，因為它認「這條邊任何一段引文具名」、連供應商自己的也算；OpenLight 兩個代號讓 OpenLight 自己的新聞稿被算成另一個代號的外部印證（3 條）；這些標籤餵走圖第 2 型、層計數器 ①、個股頁「有客戶或第三方印證」與讀圖 staleness |
| proposed change | ROADMAP Phase 表新增「6 證據判準」一列（做什麼／為什麼／驗收／前置見 ROADMAP），plan＝本檔 |
| why | 先寫更多讀圖與敘事，等於之後全部重讀；標籤名副其實是讀圖與敘事的地基（L18：標籤要指得回原始證據；L6：型號與公司名必須逐字出現在引文） |
| impact | 新增一列；不改 Phase 0–5 任何一列；旁支表「Phase 4 plan 的使用者定案輸入」那一列的「員工股酬另列不上色」註明排入本 Phase Step 6.6 |

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者已核准的 PLAN_PROPOSAL**（§0.1）。`AGENTS.md`「常規推進授權」照用：Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step**，做到 Phase 6 結案為止。只有六條停止條件之一成立才停。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（#14）**：預定 **R2-a**（6.2：遷移工具＋dry-run＋名冊 diff，在鑄 pq2 之前）與 **R2-b**（6.6：真實資料試跑之後）；其他 Step 若命中 trigger 同樣直接發 `WORK_REQUEST`。NO_GO → `AWAITING_HUMAN`。
條件修正後的覆核：開一位新的、窄範圍（只核那幾行與其依據）的審查者，條件原文照貼給它，不喚回原審查者（大 context 續跑一次就是幾十萬 token）。

**pq2 停點（掛號後接著做下一件，不停在編號上等——AGENTS）：**
- 6.2 身分遷移（一個 manual pq2，manifest＋dry-run＋R2-a verdict 附在 hint）；6.3 SourceDoc origin 更正（一個 manual pq2）、四則 lead 的 `classified_by` 更正（一個 manual pq2）；6.8 補具名引文的 RA（`ra_admission`，每份文件一個）。
- 每個 Step 的 HUMAN SUMMARY 末尾印「目前等你 go 的編號」與一行批次指令；**結案前若 6.2 的編號仍未 go**：停在 `AWAITING_HUMAN`（驗收②靠它，這是使用者的決定）；其他編號未 go 照實寫進 closeout，不擋結案。
- [666]（6.0a）被權限分類器擋下：印三行指令交給使用者、接著做 6.1；它落地時把它造成的證據等級變動當成獨立事件記一次。

**每個 Step 一個 commit（大的 Step 可拆，進度表在最後一個 commit 才 ○→✅），訊息第一行寫 Step 編號；Step 為 GO 就 push。**
新 session 先看下面進度表與 `git log --oneline -20`，從第一個未 ✅ 的 Step 接續。

**同一 working tree 只讓一個 writer：** `StockBotv2-Daily`（台北 05:30，`config/daily_routine.json`）是唯一排程。動到 daily 步驟會跑的程式（6.4 materialize 的結構表與走圖、6.6 EDGAR 步驟、6.7 追蹤表取價）的 commit **不得跨越 05:30 還沒 push**；
寫 `library/` 的 authority（6.3 lead registry、6.8 讀圖／敘事／`event_watches.json`）前先 `python scripts/writer_guard.py acquire --minutes <N> --purpose "<做什麼>"`，寫完 `release`；R2 進行中不在主樹跑變異測試。

| Step | 內容 | 狀態 | 執行者 | commit |
|---|---|---|---|---|
| 6.0 | [666] 收尾（10-02 的 go；10-03 apply／publish／結案，6 條升外部印證）＋基準快照（`docs/reports/2026-10-03-phase6-baseline.md`；證據等級凍結進 `config/graph_baselines.json` 的 `evidence_classes_2026_10_03`；偏差見 §0.6 #1–#3） | ✅ | 執行模型 | 見 git log「Step 6.0」 |
| 6.1 | 插槽讀圖 staleness：同級標籤互換算低等級（任何改分類之前；rank 由呼叫端注入、沒有預設；真實資料見 baseline §15） | ✅ | 執行模型 | 見 git log「Step 6.1」 |
| 6.2 | 身分清理：OpenLight 合併、nava 定案（Lumentum 自有 Navanakorn 廠→退役）；遷移與 RA packet 印入圖副作用（#32）；R2-a GO（兩條非阻擋觀察補防線）；**pq2 [670] 等 go，apply 在 go 之後**（baseline §16；偏差 §0.6 #4–#5） | ✅ | 執行模型 | 見 git log「Step 6.2」 |
| 6.3 | 證據資料：名冊兩個寫法（Arista、GF；Apollo 誤中不加）、GSR→media（3 條）、名冊新公司 5 家（2 條升級附引文）、`origin_entity` 進 SourceDoc 同步欄位（iqe 對齊）、綜述論文期刊登記 media；**pq2 [671]（SourceDoc origin 三筆）、[672]（四則 lead 標籤）等 go**（baseline §17；偏差 §0.6 #6–#8） | ✅ | 執行模型 | 見 git log「Step 6.3」 |
| 6.4 | 分類規則：逐來源具名＋轉述字表（唯一 owner `corroboration`）、所有消費端改走它、計數器改口徑、packet 印「入圖後證據等級會變的邊」；真實圖外部印證 250 → 230（升 2〔6.3c〕、降 22〔6.3b GSR 3＋規則 19：未具名 13／名冊無名 4／轉述 2〕）、違反 0、①73 → 77（與 §0.2 預測相同）；[670] hint 依新規則更新（baseline §18；偏差 §0.6 #10–#12） | ✅ | 執行模型 | 見 git log「Step 6.4」 |
| 6.5 | sub 旗標跟著值走到消費端（不進 digest）：贏得 sub 值那一筆的旗標印在結構表、五個角度的邊、走圖第 1 型、「替代難度」旁註；4 份現行讀圖 status 與 digest 改前改後逐位相同；真實結構表 66 列帶 sub（撐得住 9／撐不住 57）（baseline §19） | ✅ | 執行模型 | 見 git log「Step 6.5」 |
| 6.6 | 稀釋燈只認募資文件（EDGAR 申報清單、新表、sandbox impact review）：真實 11 檔黃 → 10（LRCX 轉灰）、每盞黃燈指得出窗內一份募資文件；daily 請求數不變；R2-b CONDITIONAL_GO（已知限制漏寫 MRVL 的兩份公司債說明書）→ 條件修正 → 窄範圍覆核 GO（baseline §20；偏差 §0.6 #13–#15；待決 §14 #10） | ✅ | 執行模型 | 見 git log「Step 6.6」 |
| 6.7 | 小修：結構表逐列錨、APP 自偵舊程式、排除未收盤 K 棒、預測表改寫規則①、本機 ask 規則——a 有錨 211 → 213（改前有錨改後沒錨 0；Lam 9 列 6 列逐列、3 列公司層；「公司層」跟著錨走到個股頁）；b 頁面頂端「請重啟」橫幅（headless Edge 三種情況）；c 盤中 K 棒拿掉並計數（同一份價格上追蹤表逐欄相同、計分表只差時間戳記）；d 真實 15 筆預測終局不變；e ask 16 條（下一次跑請使用者確認會被問）（baseline §21；偏差 §0.6 #16–#17） | ✅ | 執行模型 | 見 git log「Step 6.7」 |
| 6.8 | 研究（強模型）：補具名引文（RA，pq2）、重讀 stale 的讀圖、四檔敘事換版或不換版理由（收據 `docs/reports/2026-10-xx-phase6-step68-research.md`） | ○ | 執行模型 | |
| 6.9 | 新管線 full chain 測試（證據鏈與稀釋燈鏈） | ○ | 執行模型 | |
| 結案 | completion gate ＋ closeout ＋ R2 ＋ ROADMAP ✅ | ○ | 執行模型 | |

**開工／續工指令：貼 `/phase-run` 即可**（不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-10-02-002-feat-phase6-evidence-criteria-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。沒有需要我核准的事就一直做到 Phase 6 結案；撞到六條停止條件才停（R2-a、R2-b 已常規 opt-in，見 §0.5）。
圖寫入一律等我對 pq2 go：鑄號後印出批次指令就接著做下一個 Step，不要停在編號上等。每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|
| 1 | 6.0 | （plan commit `8c7cc574`）`docs/plans/README.md` 對照表 Phase 6 的狀態格寫 `**active**（…）` | 改成 `active（…）`（與其他列同一個寫法） | 加粗讓狀態格不以封閉字彙開頭：`tests/test_phase_status_hint.py::test_real_readme_status_cells_start_with_a_known_word` 紅、SessionStart hook 報「沒有 active plan」（10-03 session 開頭就是這樣錯的）。維持營運，不算進展（baseline §1） |
| 2 | 6.0（影響 6.4、6.8、結案 R2） | §5 owner：發布者過 `publisher_lifts` 後「要有一段具名主詞、而且不含轉述字表任何一個詞」的引文；§13「6.4 的轉述檢查也套在那份 Reuters 的引文上（若是「AXT said…」型就不升）」 | **宣告 `origin_linkage=independent` 的文件不套轉述檢查**（具名照樣要）；轉述與具名都在過 `publisher_lifts` 的那幾份文件裡逐份判。§5、§13 改寫 | ROADMAP Phase 6 列與 §0.1 #4 都寫「翻案靠逐份宣告 `origin_linkage=independent`」，6.8 第 1 項的 `relay` 補救也是「宣告 independent 的 RA」——只有 §13 的註記相反；依檔頭「衝突時以 ROADMAP 為準」。照 §13 的讀法，[666] 的 6 條會全部退回（Reuters s1「AXT … said」是轉述，但 s2「…, the person said」是 Reuters 自己採訪、s5 是 SemiAnalysis 分析師，草案字表三段都判轉述）＝抵銷使用者 10-02 核准的宣告（baseline §3） |
| 3 | 6.0（影響 §11、6.3b、6.3e） | §0.2／§11「外部印證 244 → N」；§0.2 GSR 連鎖 7 條；6.3e 綜述論文「31 條邊」 | 以 [666] 之後的 **250** 起算（凍結鍵 `evidence_classes_2026_10_03`）；GSR→media 只掉 **3** 條（另 4 條由宣告 independent 的 Reuters s3 撐住）；論文掛 **34** 條 distinct edge_key | [666] 在 6.0a 先落地；規則那一半（未具名 12、轉述 2、名冊無名 1）與 §0.2 逐條相同（baseline §3、§6、§12） |
| 4 | 6.2b／6.2c | 「節點宣告照抄圖上 `co:openlight_photonics` 的現值」（只寫改名的那一個） | 兩份重載檔裡**每個圖上已存在的節點**都照抄現值（`align_nodes_to_graph`：type／name／abstraction_level／role、別名圖上在前聯集、屬性圖上鍵優先、confidence 不高於圖上）；遷移工具改成 manifest 驅動、dry-run 在記憶體裡改抽取檔與名冊（go 之前 repo 一個資料檔都不動），apply 先寫圖再寫檔 | dry-run 量到 `semitoday_ph18da_volume_2026_03_20` 原樣重載會把 `co:newphotonics` 的 abstraction_level（module_subsystem→device_chip）與 role（disruptor→null）蓋掉——只照抄改名那一個，claimed acceptance「副作用 0」不成立（與 2026-09-04 去重遷移「三份抽取檔的 attributes 改成一致的聯集」同一個做法）；先寫圖再寫檔是為了中途失敗可續跑（baseline §16.2） |
| 5 | 6.2d | 「`scripts/prepare_research_action.py` 產 packet 時以唯讀 session 比對…」 | 照做（`intake.application._merge_side_effect_receipt`）；另把 `tests/test_research_actions.py::test_prepare_validates_every_document_without_graph_or_publication` 改寫成 `…_reads_the_graph_read_only_and_never_publishes`（假 driver 擋寫入 Cypher） | 舊測試守的「prepare 不開圖」從來沒被守住：同 URL 多段檢查本來就開圖，並以 `except Exception: pass` 吞掉 AssertionError 絆線；6.2d 起 prepare 本來就要唯讀查圖，守的東西收窄成「只讀、不寫、不 publish」（plan 不可越線 11：刪改測試要寫它守的是什麼、現在由誰守） |
| 6 | 6.3a（影響 6.4、6.8） | 名冊三個寫法：`co:apollo` 加「Apollo」、`co:arista` 加「Arista」、`co:globalfoundries` 加「GF」 | 只加 Arista、GF；**Apollo 不加** | 全圖逐字整詞比對：「Apollo」4 段裡 2 段是 Google 的「Apollo OCS platform」（專案代號）——plan 本節的規則「有任何一筆不是在講這家公司 → 不加那個寫法、寫進偏差」；`co:apollo invests_in co:broadcom` 在 6.4 之後進 `corroboration_withheld.unnamed`，6.8 讀原文決定（baseline §17.1） |
| 7 | 6.3e | `MDPI Micromachines`：`seen_in: cpo_chip_package_paper` | `seen_in: Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era` | `seen_in` 的契約是「讓這筆被登記的那份 **SourceDoc id**」（`query/origin_resolution.py::Publisher`）；`cpo_chip_package_paper` 是抽取檔的檔名，SourceDoc id 是後者（baseline §6） |
| 8 | 6.3d | Soitec 那份的新 origin「`Soitec（Reuters 訪談逐字）`」 | 「`Soitec（管理層受 Reuters 訪談所述）`」 | 摘錄（`library/raw/reuters_soitec_capacity_reservations_2026_08_31.txt`）是 Reuters 法文報導的轉述，不是管理層逐字——措辭精度本身是 claim（L11-1）；去註解後同樣解析成 `co:soitec` |
| 9 | 6.3e（影響 [671]） | 6.3e 單獨一項：`config/publishers.json` 登記 `MDPI Micromachines` | 條目寫進更正 manifest 的 `publishers_add`，由 `--corrections --apply`（[671] go 之後）在 origin 更正落地後**同一步**登記；publishers.json 先撤回 | `tests/test_origin_resolution.py::test_every_registration_spells_the_origin_of_the_document_it_came_from` 要求登記對得上 `seen_in` 那份文件**現在**的 origin（L18）——先登記就是一筆指不回原文的登記（初版 commit `e9e53620` 這樣做、全測試紅了一條） |
| 10 | 6.4 | `collapse_assertions` 多記 `origin_assertions: {origin: set(assertion_id)}`；`classify_evidence` 多收 `quotes_by_assertion`（必填） | `origin_assertions: {origin: [(assertion_id, doc, linkage)]}`，**取代** `CanonicalEdge.origin_linkages`（退役）；`classify_evidence` 多收**兩個**必填關鍵字（`quotes_by_assertion`、`origin_assertions`），原本的 `origin_linkages` 參數拿掉；另加 `edge_corroborations`（每個 origin 的判定，`layer_stats` 讀 `withheld`）與 `best_evidence` | §0.6 #2 的轉述豁免與 `publisher_lifts` 都是**文件層級**的宣告——只記 assertion id 就不知道每段逐字出自哪份、那份宣告了什麼；兩個欄位並存＝同一個宣告兩種表示（L12），拿掉舊的那個，所有呼叫端被迫重看一次 |
| 11 | 6.4 | `build_socket_view` 的 `third_party` 改問 owner；客戶端原文照印，旁註「未具名供應商」 | 發布者的引文**過了 `publisher_lifts`** 就列（與改前相同的母體），沒具名或轉述句同樣旁註（`Corroboration.publisher_lifted`、`withheld`）；不只撐得住外部印證的才列 | 只列撐得住的會讓改前列得出的第三方原文靜默消失（INV-3）；「`verify_citations` 收得下的引文這裡要列得出來」仍成立（收得下 ⊆ 列出）；旁註就是在說「列出來不等於撐得住」。待決見 §14 #8 |
| 12 | 6.4 | §13：「名冊無名可比」＝`company_name_forms` 回空 tuple | 另含「每個寫法都與另一家共用」（`query.bottleneck.usable_name_forms` 空；名字比對 `_named_by` 與 owner 共用這一個 helper） | 第一版把 OpenLight 3 條判成 `unnamed`——6.8 會被導去讀原文，而原文寫的「OpenLight」對兩個代號都不算、永遠比不到；補救是身分清理（[670]），與 `no_name_forms` 同一種。6.0 的模擬（`sim_b0`）本來就這樣判 |
| 13 | 6.6 | 新表 `equity_offering_filings`（ticker、cik、form、items、filed、accession 主鍵、fetched_at） | 照建，**另加** `equity_offering_checks`（每檔最後一次抓清單的時間、清單涵蓋起點、筆數）；清單之外也存 S-8／S-3 等「不算募資」的登記表單（判定在讀取端，表裡不存判定） | 只有一張表時「抓過、窗內沒有」與「從沒抓過」同形（L12、INV-3）；submissions 的 `recent` 只給最近約 1000 筆，沒有涵蓋起點就說不出窗內「沒有」（INV-6）。存 S-8／S-3 是為了讓灰燈印得出「窗內只有員工計畫登記」 |
| 14 | 6.6 | 灰燈理由「只有發行金額、窗內沒有募資文件（S-8 員工計畫不算募資）」 | 「只有發行金額、窗內沒有募資文件——員工計畫登記與增資授權不算募資（窗內有哪些申報在稽核層）」；黃燈理由同樣不帶表單代號與日期 | 既有契約 D2「紅黃綠不給數字」：理由句不得帶數字（`tests/test_wipeout_flags.py::test_lamp_reasons_do_not_leak_company_numbers`）——「S-8」「424B5」與申報日都帶數字；代號與日期改住稽核層的 inputs |
| 15 | 6.6（R2-b CONDITIONAL_GO） | （未提） | C1：已知限制補 MRVL（424B5 `0001193125-26-142958`、424B2 `0001193125-26-147640` 是 Senior Notes）——`_DILUTION_RULE`、baseline §20、§14 #10 三處。C2（可選，照做）：規則文字的表單清單補「8-K（含 8-K/A）」與 S-8 POS、S-3／F-3 家族的 /A、ASR、MEF 變體 | C1：初版的「已知限制」只寫手核過的 NVDA、META，MRVL 的 424B5／424B2 沒讀封面就沒寫——自己引用的限制要套同一套追源紀律（L11-2）；判色不變（MRVL 另有 8-K 3.02 ×4 與 424B7）。C2：文字寫的比程式少，讀規則的人會以為 8-K/A 不算。兩項都只動文字，不動判定；窄範圍覆核（乾淨 context）見進度表 |
| 16 | 6.7a（影響結案 §12 第 3 項） | 改哪裡：`structure_table`、APP 結構表頁、心跳「前三錨」 | 另把 `anchor_basis` 帶到 alpha provider（`ScarcityInputs.demand_anchor_basis`、邊表）、個股頁「需求錨點／距需求端跳數」旁註與邊表「（公司層）」、session assessor 的輸入；心跳那一行多「公司層 N 列」（舊 artifact 印「錨是公司側」） | 列上的 `demand_anchor` 一改成逐列，凡是印它的地方都承載兩種問題——只改 plan 列的三處，個股頁的同一格就是 L12 的形狀（L16：分類跟著資料走）。實測 provider 同公司順序只有 GFS 變、Q1 取到的邊 0 家變，但 Q1 那條邊的錨 3 家、跳數 9 家會變——**結案的個股頁逐檔歸因多一個來源「6.7a 逐列錨」**（AXTI、COHR 的稽核區兩格；baseline §21a） |
| 17 | 6.7c | owner 讓「追蹤表兩支與計分表一支共用」 | 另接上追蹤表的**第三支** `_benchmark_series`（基準）與 owner 自己的 `fetch_close_series`（走勢折線、事件監控）；計數住 `price_budget.closing_bars`（追蹤表、計分表、APP 兩頁有才印）；`fetch_close_series` 的 `today` 參數（沒有呼叫端用）換成 `now`／`states` | 基準是對稱面（L17）：歐股收盤後、美股盤中時，指數的當日值同樣是進行中的，拿它算超額會把半天的漲跌當終點；`fetch_close_series` 原本「丟日期＝台北今天那根」是同一個問題的第二套規則——同一個模組留兩套「收盤了沒」就是 dual authority，而且美股盤中的當日 K 棒日期是美東昨天、舊規則照樣放行。daily 05:30 各市場都已收盤，同一份價格上追蹤表逐欄相同、計分表只差時間戳記（baseline §21c） |

---

## 0. 不可越線（違反即 NO_GO）

1. **圖寫入只有四種、都要收據**：[666]（使用者 10-02 已 go，經 `scripts/apply_ra_admission.py` 入口）；6.2 身分遷移、6.3 SourceDoc origin 更正、6.8 補引文 RA——各自的 pq2 被使用者 `go` 之後才寫。live 遷移前先在 backup-dir 放非空的 `neo4j_export.json`（`scripts/backup_private.py` 的 `export_neo4j_payload`／`verify_neo4j_export`，Phase 4 #28 的做法）。其他 Step 對 Neo4j 只讀。
2. **分類規則只會讓標籤變保守。** 任何一條邊因本 Phase 的**程式**而升級＝bug。會升級的只有資料更正（名冊寫法、名冊新公司、publishers、SourceDoc origin、身分合併、[666]、補回的引文），而且每一條升級都要列出「哪段引文、哪個事件」（L18）。
3. **一個 owner**：「這個 origin 對這條邊算不算外部印證」只有一個函式；`classify_evidence`、`verify_citations`（讀圖引用的 independent 核對）、`build_socket_view`、`scripts/audit_sole_source_independence.py`、`layer_stats`、RA packet 全部問它（L16）。名字比對仍只走 `quote_names_company`。
4. **「名冊無名可比」與「引文沒具名」與「轉述」三種不得壓成一格**（L12；`quote_names_company` docstring 的要求）：每條沒升的邊帶它是哪一種。
5. **不排序、不打分、不設門檻、不判**：證據等級、sub 旗標、稀釋燈都不進候選狀態前提、排序或尺寸；分母 0 印「還沒有分母」不印 0%；讀不到印 `upstream_unavailable` 不印 0。
6. **sub 旗標與證據核對的附加欄位不得進讀圖的 `result_digest`**：否則每一份讀圖在部署那天全變 stale，量到的是我們的程式改版、不是圖（同 Phase 5 #2 的教訓）。
7. **轉述字表與具名規則不得出現在 `prompts/`、`skills/`**（L19：抽取端讀得到就會挑不含這些字的引文，旗標恆滅）；比照 `config/substitutability_language.json` 的守門測試。
8. **INV-1**：公司身分只走 `config/company_identity.json`；合併走「改抽取檔 → scoped 重載 → 刪舊 → 重投影」，不做 Cypher 手術；名冊新增公司前先查圖上有沒有既有 `co:*` id，有就用它，不另起一個。
9. **INV-6**：募資文件以 EDGAR 的 `filed` 日落窗；沒有日期的不猜；as-of 視角不得拿現在的申報清單冒充。
10. **任何 `python -m <module>` 或 `scripts/*.py` 的行為變更 → sandbox impact review 五步**（ROADMAP 硬約束 10）：6.4（materialize `--structure-table`／`--graph-walk`／`--structure-readings` 多讀全部逐字）、6.6（daily EDGAR 步驟多寫一張表）、6.7（追蹤表與計分表取價、APP）。
11. **每刪一個測試函式，八欄的 Blocking findings 列出它守的是什麼、現在由誰守。** 活機制的測試不可刪斷言；`tests/test_heartbeat.py` 釘住的格式改主詞不刪判準。
12. **每個 Step 動手前先答 L11-6 第④問：「如果這個改動是錯的，最先壞掉的是哪一筆現有資料或哪個活的呼叫端？」去看那一筆，寫進八欄。** 各 Step 已預填一個起點。
13. **命名**：不得出現殭屍 grep 九組的新命中（`basket`、`籃子`、`payoff`、`首選`…）；新名字：`corroboration`（owner）、`corroboration_withheld`（沒升的邊）、`relay_language`（字表）、`equity_offering_filings`（新表）、`anchor_basis`（結構表）。
14. **不寫 trade_log、Google Sheet、舊 Decision Store、thesis**；讀圖 ledger、敘事 ledger、`event_watches.json` 只在 6.8 經正式入口寫；lead registry 只在 6.3 的 pq2 go 之後寫。
15. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。** 四個人工 gate、五條 authority separation、六條 invariant 全程適用。

---

## 1. Step 6.0 [666] 收尾＋基準快照（Z0／Z1）

**6.0a [666]（使用者 2026-10-02 已 go；§0.1 #12）：**
```
python scripts/apply_ra_admission.py --pq2 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d
python scripts/commit_pending_intake.py
python -m engine_b.todo complete-ra 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d
```
入口照樣驗編號／digest／戳記／property token。**任何一步被執行環境的權限分類器擋下、或 Neo4j 回 Forbidden：停手，不換方式重試**，把三行指令印給使用者、接著做 6.0b（[666] 落地時另記它的證據等級變動）。
成功時記：重寫的 assertion 數（Phase 4 closeout 預告 4 筆帶 sub 的 e1／e2／e9／e10，③b 計數器應印「重寫 4」）、證據等級變動逐條（預告 6 條升外部印證）。

**6.0b 基準快照：** 寫 `docs/reports/2026-10-xx-phase6-baseline.md`，每個數字附命令：

1. `python -m pytest -q` 總數、測試檔數、函式層級名單（`git grep -n -E "^\s*(async )?def test_" HEAD -- 'tests/*.py' | wc -l` 並存名單 sha）；`python -m audit invariants`。
2. **證據等級凍結**：537 條（或 [666] 之後的數）canonical 邊 → `{(src, relation, dst): evidence}` 寫進 `config/graph_baselines.json` 新鍵 `evidence_classes_2026_10_xx`（既有鍵一個字都不改；同時存 origin 清單），報告印分布。
3. **逐來源模擬（6.4 的對照答案）**：寫一支 scratchpad 腳本，對每條外部印證邊、逐 origin 判「這個 origin 的引文有沒有具名主詞」（主詞是名冊公司時；用 `quote_names_company`，名冊沒有寫法另計）與「發布者的引文是不是轉述句」（草案字表：`announced`／`said`／`says`／`stated`／`states`／`according to`／`表示`／`宣布`），列出會掉級的邊與原因；與 §0.2 的模擬（逐來源不具名 12、轉述 2）逐條對照，差異寫進報告並回頭修 §5。
4. 走圖 artifact 的 `layer_stats` 全段、九型命中／母體；心跳 `python -m crons.heartbeat --out <scratchpad>/hb_base.md`（段 3「層：」行逐字存檔）；`SNAPSHOT_KEYS` 清單。
5. 讀圖 4 份的 status 與 staleness 明細（`python -m alpha structure-reading <node> --check`）；四檔 v2 敘事的 `brief_id`；每檔個股頁「這家公司坐的層」各邊的證據標籤（之後換版的對照）。
6. 解析不到的 SourceDoc 16 份逐份（origin、source_type、掛幾條邊）；`config/publishers.json` 筆數；名冊筆數；圖上是否已有 Credo／Noveon／Sojitz／Telescent／USA Rare Earth 的 `co:*` 節點（Cypher 唯讀）。
7. 稀釋燈 11 檔逐檔：金額、占市值、tag、accession；結構表 Lam 的列與錨。
8. 四則 lead 的 `classified_by` 現值（`lead_198ada57…`、`lead_3238fc77…`、`lead_39841af8…`、`lead_cbd50ac5…`）。
9. Phase 5 #15：`git log --oneline -- config/signal_sources.json` 與 pq2 池裡引用計分表的 tier 項目數——若仍是「從未升降、0 項」，這一題結案（寫進報告）。
10. 長駐 APP：`python -m webapp status`、正在跑的 `webapp serve` 行程與啟動時間（PowerShell `Get-CimInstance Win32_Process`）。
11. trade_log sha256、舊店三個 `*.db` sha256、四個 ledger（讀圖、敘事、主題等權組、`event_watches.json`）sha256、`.claude/settings.local.json` 的 allow／ask／deny 條數。

L11-6 ④（本 Step）：[666] 若入圖時改壞了東西，最先壞的是 `mat:inp_substrate` 那幾條邊——跑完後對它們逐條比對「重寫前後的引文與 sub」（RA packet 的預告）。

## 2. Step 6.1 插槽讀圖 staleness：同級標籤互換算低等級（Z1，R1）

**改哪裡：** `alpha/structure_reading/staleness.py::_angle_changes`、`tests/test_structure_reading*.py`（staleness 的那幾條）、`docs/ARCHITECTURE.md` 讀圖 staleness 一段。
**怎麼改：** 插槽的供給側證據變動：前後兩個等級的 rank（唯一 owner `query.bottleneck.EVIDENCE_RANK`）**不同**才是 `supply_evidence`（high）；**相同**（例：待判定 ↔ 媒體轉述，rank 都是 1）走 `evidence`（low），detail 寫「同級互換」。層讀圖的分級一字不動。
若分層規則（`tests/test_layer_separation.py`）不允許 `alpha/structure_reading` import `query`，以參數注入 rank 表，**不得**在 alpha 抄一份 rank。
**怎麼驗：** 夾具：插槽供給側 needs_review→media_relay → low；needs_review→externally_corroborated → high；層讀圖同樣變動 → low（不變）；變異：拿掉 rank 比較 → 紅。真實資料：4 份現行讀圖的 status 與 6.0 相同（本 Step 不改任何標籤）。
L11-6 ④：最先壞的是 `prod:supernova` 插槽讀圖（Phase 4 4.3 曾因同級拆分被標 stale high）——用它 09-25 那份的快照重放 4.3 的變動，應判 low。

## 3. Step 6.2 身分清理（Z2，R1 ＋ R2-a 常規 opt-in；圖寫入等 pq2）

**6.2a nava 先定案（研究，強模型）：** 讀一手來源（Lumentum 10-K Item 2 Properties、Q2 FY26 法說逐字稿原文——`extractions/lumentum_q2fy26_cpo_raw.txt` 是摘要句，不是逐字），回答「Nava 是 Lumentum 自己在泰國 Navanakorn 的廠區，還是一家代工廠」。三種結果：
- **自己的廠區** → 退役：名冊刪 `co:nava_thailand`；`extractions/lumentum_q2fy26_cpo.json` 刪 `co:lumentum supplies_to co:nava_thailand`（對自己供貨沒有意義）、把 `co:nava_thailand supplies_to tech:cloud_transceiver_1_6t` 改掛 `co:lumentum`（同檔已有同一條邊就併 sources）、刪節點宣告。
- **一家代工廠** → 補名字：名冊補 `display_name`（附出處）與 `name_aliases: ["Nava"]`，圖不動。
- **查不到** → 名冊 `_note` 補上查過哪些來源；驗收②照實寫「nava 未定案」，不猜。
收據寫進 6.0 的 baseline 報告附錄（或 6.8 收據），每個判斷附原文。

**6.2b OpenLight 合併（留 `co:openlight_photonics`）：**
- `extractions/semitoday_ph18da_volume_2026_03_20.json`：`co:openlight` → `co:openlight_photonics`（節點宣告與邊）；**節點宣告照抄圖上 `co:openlight_photonics` 的現值**（`type`／`name`／`abstraction_level`／`role`／`aliases`／`attributes`／`confidence`，同 `migrate_relation_rejudge.py --additions` 的做法）；`co:openlight` 有、canonical 沒有的別名列出來，聯集進 canonical。
- 名冊刪 `co:openlight`；`co:openlight_photonics._note` 改寫成合併紀錄（日期、pq2 編號）。合併後 `OpenLight` 這個 origin 經 `company_id_for_origin` 的名字比對解析成 `co:openlight_photonics`（slug `co:openlight` 不再存在）——**測試要釘住這一條**。
- `library/leads/todo_pool.json` 等歷史紀錄裡的 `co:openlight` 不改（歷史）；但 lead registry、event_watches、讀圖、敘事若有**活的**引用，列出來（今天 grep 只在 todo_pool）。

**6.2c 遷移工具：** 照 `loader/migrate_entity_dedup_20260904.py` 的四步（改抽取檔 → 只重載那幾份 → 刪舊 id 的 assertion 與節點 → 重投影受影響的 edge_key），新寫一支 scoped 腳本（或擴既有那支，不複製 `_supersede`／`_cleanup`／`_admin_driver`），`--dry-run` 預設、`--backup-dir` 必填（裡面要先有非空 `neo4j_export.json`）、`--pq2 N` 必填（核對：存在、未結案、型別 `manual`、ref_id 是本工具掛的那種——同 `migrate_sourcedoc_json_section.py` 的編號核對）；manifest 存 `loader/manifests/identity-cleanup-2026xxxx.json`。
**dry-run 必印入圖副作用（#32 的遷移那一半）：** 每個被重載的節點逐欄「圖上現值 → 重載後」、別名聯集、SourceDoc 欄位（`title`／`section`／`retrieved_at`／`origin_entity`）衝突；**證據等級會變的邊**（用當下的 `classify_evidence` 在記憶體裡算一次）。

**6.2d RA packet 的入圖副作用（#32 的 RA 那一半）：** `scripts/prepare_research_action.py` 產 packet 時以唯讀 session 比對抽取檔要 MERGE 的節點與 SourceDoc 對圖上現值，印「會被覆寫的節點屬性」「別名聯集」「SourceDoc 欄位衝突（含 `retrieved_at` 倒退）」；Neo4j 讀不到印「副作用無法核對（upstream_unavailable）」，**不印「無副作用」**。（「證據等級會變的邊」那一段在 6.4 owner 落地後補。）

**6.2e R2-a → pq2：** R2-a（WORK_REQUEST 見下）GO 之後鑄一個 manual pq2（`python -m engine_b.todo add …`，hint 附 manifest、dry-run 全文、R2-a verdict），印批次指令，**接著做 6.3**。go 之後：匯出圖 → `--apply` → 重投影 → 記證據等級變動逐條 → `complete` 收據（`authority:graph_migration;ref:loader/manifests/…`）。

```
WORK_REQUEST（R2-a，Phase 6 Step 6.2）
Target: master 最新 commit；loader/ 的身分遷移腳本與 manifest；config/company_identity.json 的 diff；scripts/prepare_research_action.py 的副作用段
Claimed acceptance: dry-run 只動 manifest 列的抽取檔、節點宣告照抄圖上現值（副作用 0）、OpenLight 合併後 origin 解析到 co:openlight_photonics、nava 的處置有一手原文
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo 與 diff，自己跑 dry-run 與測試（不帶 --apply）；核對名冊沒有任何 by_ticker 衝突；核對沒有活的引用指向被刪的 id；回 REVIEW（含 verdict）
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不跑 --apply
```

**怎麼驗：** 夾具：兩個 id 同名 → 合併後名字比對對 canonical 成立、origin 解析到 canonical；遷移 dry-run 對夾具圖印出的副作用逐欄正確；packet 對夾具 driver 印覆寫與衝突、driver 讀不到印 `upstream_unavailable`；變異：節點宣告不照抄圖上現值 → 副作用不為 0 → 紅。
L11-6 ④：最先壞的是 `co:openlight_photonics partnership_with co:tower_semiconductor`——合併後那份 Tower／OpenLight 聯合 6-K 應判「雙方聯合」（OpenLight 不再是兩家共用的寫法），dry-run 的證據等級預告要印出這一條。

## 4. Step 6.3 證據資料（Z1，R1；SourceDoc origin 與 lead 標籤等 pq2）

每個子項一個 commit、每個 commit 附「證據等級變動逐條」（同一份圖、改前改後各算一次）。

| 件 | 改哪裡 | 怎麼改 | 怎麼驗 |
|---|---|---|---|
| a 名冊三個寫法 | `config/company_identity.json` | `co:apollo` 加 `name_aliases: ["Apollo"]`、`co:arista` 加 `["Arista"]`、`co:globalfoundries` 加 `["GF"]`；每筆 `_name_aliases_source` 指向那段引文的 doc | 對**全部**引文跑一次整詞比對，列出每個新寫法命中的引文；有任何一筆不是在講這家公司 → 不加那個寫法、寫進偏差（單字、兩個字母的寫法誤中風險最高） |
| b GSR → media | `config/publishers.json` | `Global Semi Research` 的 `kind: media`、`corroborates: false`，`note` 寫定案日期與理由（[668] RA review「單位數字的出處沒寫」；與另 4 個 Substack 一致） | 載入檢查通過；證據等級變動逐條（預期 7 條，§0.2） |
| c 名冊新公司 | `config/company_identity.json` | Credo、Noveon Magnetics、Sojitz、Telescent、USA Rare Earth：先查圖上有沒有既有 `co:*` 節點（有就用那個 id）；`display_name` 附一手出處（申報封面或官網）；上市的填 `research_ticker`（CRDO、2768.T、USAR），私人公司明確 `null`（L9） | 名冊載入無衝突；每家的 origin 解析由「解析不到」變「公司」；**Sojitz 是客戶端，它的邊可能升外部印證——逐條列出那段引文**（§0 第 2 條） |
| d SourceDoc origin 更正（pq2） | 抽取檔 `source_doc.origin_entity`＋圖（`loader/sourcedoc_sync.py::FIELDS` 加 `origin_entity`；`loader/migrate_sourcedoc_json_section.py --apply-graph --pq2 N` 寫圖） | 三份：`Soitec management (Reuters interview)` → `Soitec（Reuters 訪談逐字）`；`Novanta/ATI（供應商官方應用頁）` → `Novanta（子公司 ATI Industrial Automation 官方應用頁）`；`Third-party Research` → `MDPI Micromachines（Chen et al. 2025 綜述）`——**`cpo_chip_package_paper.json` 與 `cpo_paper_coverage_addendum_2026_08_30.json` 兩份要同一個值**（同一 doc_id 多份 JSON 互異＝SourceDocSync 紅）；先鑄 manual pq2（hint 附逐份舊值→新值與原文出處），go 之後才改 JSON 與圖，同一次做完 | SourceDocSync 兩個方向 0＋0；三份的 origin 解析分別是公司 co:soitec／公司 co:novanta／發布者 MDPI Micromachines；證據等級變動逐條 |
| e 綜述論文登記 | `config/publishers.json` | `MDPI Micromachines`：`kind: media`（綜述，轉述廠商公開資料——原文「based on data from OpenAI and Broadcom's official reports」「adapted from semiconductor-related websites」），`seen_in: cpo_chip_package_paper` | 它的 34 條邊（baseline §6；plan 原寫 31，§0.6 #3）由待判定變媒體轉述（同級，6.1 之後只會讓讀圖 stale_low）；②「origin 解析不到的來源」減少 |
| f 四則 lead 的 `classified_by`（pq2） | `library/leads/pending_leads.json`（authority） | 鑄一個 manual pq2（hint 列四則、舊值→新值 `interactive:directed`）；go 之後在 writer lock 下、先備份、只改這四則的這一個欄位，收據記舊值與新值 | 四則的值；心跳「分類層上次成功」不再被它們冒充（6.0 的值對照） |

L11-6 ④：最先壞的是 `layer_stats.enumeration`（②「非供應商來源列舉 ≥2 家」）——名冊新公司與新寫法會改變「誰算非供應商來源」與「引文具名幾家」，②的層數可能變；逐層列出變化與原因，不得把它當驗收進展報（它不是本 Phase 的驗收）。

## 5. Step 6.4 分類規則：逐來源具名＋轉述字表（Z2，R1）

**改哪裡：** `query/origin_resolution.py`（新 owner）、新 `config/relay_language.json`＋`.gitignore` 的 `!config/relay_language.json`、`docs/solutions/architecture-patterns/closed-vocabulary-registry.md`（登記新字表）、`query/bottleneck.py`（`collapse_assertions`、`classify_evidence`、`structure_table`）、`query/structure.py`（`_classify_edges`、`_snapshot`、`_load_edges`、`build_socket_view`）、`alpha/providers/structure_readings.py::_independence_problems`、`scripts/audit_sole_source_independence.py`、`query/layer_stats.py`、`intake/actions.py`（packet）、`webapp/materialize.py`（結構表呼叫端傳逐字）、`crons/heartbeat.py`（段 3 那一行）、`docs/ARCHITECTURE.md`（證據等級一節）、`CONCEPTS.md`（「外部印證」的定義）、`docs/OPERATIONS.md`（sandbox impact review）、測試。

**owner（建議名 `corroboration`）：** 輸入＝`resolution`、主詞、這個 origin 引用這條邊的逐字、各份文件的 `origin_linkage`、名冊；輸出＝等級＋沒升的理由（`withheld ∈ {None, "unnamed", "no_name_forms", "relay"}`）。規則：
- **名冊公司、不是主詞**：主詞是名冊公司時，這個 origin 至少一段引文具名主詞（`quote_names_company`）才給「外部印證」；主詞在名冊沒有任何寫法 → `no_name_forms`（待判定）；有寫法但引文沒具名 → `unnamed`（待判定）。主詞不是名冊公司（技術節點之間的邊）→ 照舊。
- **名冊公司、是主詞**：照舊（自報；filing 出身為自報·filing）。
- **發布者**：先過 `publisher_lifts`（類別與逐份宣告，照舊）；過了之後，主詞是名冊公司時要有一段「具名主詞、而且不含轉述字表任何一個詞」的引文才給外部印證，否則 `relay`（有具名但都是轉述句）或 `unnamed`／`no_name_forms` → 媒體轉述；沒過 `publisher_lifts` → 媒體轉述（照舊）。
  **逐份文件判**：只在過了 `publisher_lifts` 的那幾份文件裡找引文；**那份文件宣告 `origin_linkage=independent` 時不套轉述檢查**（具名照樣要）——ROADMAP「翻案靠逐份宣告 `origin_linkage=independent`」（§0.6 #2）。
- **解析不到**：照舊（聯合公告偵測 → 雙方聯合；否則待判定）。
- 取各 origin 能支持的最高等級（照舊）。

**轉述字表 `config/relay_language.json`：** 形狀照 `config/substitutability_language.json`（`schema_version`、`version`、`active`、`variants`、`_history`、`_doc`）；v1 的詞：`announced`、`announces`、`said`、`says`、`stated`、`states`、`according to`、`表示`、`宣布`；比對規則同 sub 字表（ASCII 整詞不分大小寫、中日韓整串）。**不得出現在 `prompts/`、`skills/`**（§0 第 7 條；測試照 `tests/test_sub_language.py` 的守門寫）。改字表＝升 version 並在 `_history` 記一行。

**資料流：** `collapse_assertions` 多記 `origin_assertions: {origin: [(assertion_id, doc, linkage)]}`（取代 `origin_linkages`；§0.6 #10）；`classify_evidence` 多收 `quotes_by_assertion`、`origin_assertions`（**必填**——呼叫端沒給就丟例外，不得靜默把全部降級，L13）；三個呼叫端（`structure_table`、`_classify_edges`、`_snapshot`／`_load_edges`）在**同一個 transaction** 裡多跑 `query.sub_language.fetch_all_quotes`（不得 join 進 `fetch_assertions`：會灌大 `documents`）。
**讀圖引用核對：** `_independence_problems` 改問 owner——標了 `independent` 的引用，那段**被引用的逐字**必須具名主詞（公司 origin 與發布者都是）、發布者的那段不得是轉述句；違反時訊息照三種理由分開寫。既有讀圖不回頭重驗（append-only），6.8 的重讀要過新規則。
**插槽視角：** `build_socket_view` 的 `third_party` 改問 owner；客戶端原文照印，旁註「未具名供應商」；發布者過了 `publisher_lifts` 的引文照列、沒具名或轉述同樣旁註（§0.6 #11）。
**計數器：** `layer_stats` 的 `ec_quote_does_not_name_supplier` 退役（新規則下結構上恆 0），換成 `corroboration_withheld: {unnamed: [...], no_name_forms: [...], relay: [...]}`（每條：邊、origin、文件——這就是 6.8 的補引文清單）＋ `ec_without_naming_quote`（逐來源口徑的違反數，應恆為 0；非 0＝bug）＋ 證據等級對 6.0 基準鍵的升降數與逐條（`evidence_vs_baseline`）。`summary_line` 改成「…｜外部印證違反 0｜沒升：未具名 a／名冊無名 b／轉述 c｜證據等級較 6.0：升 x／降 y」；結構表頁首與心跳段 3 讀同一行（L16）。
**RA packet：** 6.2d 的副作用段補「入圖後證據等級會變的邊」（把 packet 的抽取併進當下的 rows 與逐字，用 owner 在記憶體裡算前後）。

**sandbox impact review：** daily ⑬ 的 materialize（`--structure-table`、`--graph-walk`、`--structure-readings`）多一條**唯讀** Cypher（全部逐字），argv 不變、無新主機或憑證、寫入不變。寫進 OPERATIONS 既有那一節。

**怎麼驗：** 夾具：①客戶 origin 引文具名 → 外部印證；②客戶 origin 引文不具名 → 待判定＋`unnamed`；③主詞名冊無寫法 → `no_name_forms`；④產業研究「Lumentum announced…」→ 媒體轉述＋`relay`；⑤同一 origin 一段轉述、一段具名非轉述 → 外部印證；⑥媒體宣告 independent、引文具名非轉述 → 外部印證；⑦技術節點之間的邊不套具名 → 照舊；⑧呼叫端沒給逐字 → 例外；⑨`verify_citations` 對②④的 independent 引用拒收、理由分開。
真實資料：證據等級變動逐條與 6.0 第 3 項的模擬逐條對照（差異逐條解釋）；`ec_without_naming_quote` 0；①「獨家且全自報」與走圖第 2 型命中的變化逐節點列出。
變異：拿掉轉述檢查 → ④紅；具名改成「任何一段引文」（舊口徑）→ Sivers 那條（夾具化）紅；`classify_evidence` 的 `quotes_by_assertion` 給預設空 dict → ⑧紅。
L11-6 ④：最先壞的是 Sivers→CW DFB（華星光年報）與 Lumentum→NVIDIA（NVIDIA 新聞稿抽到的那句沒寫 Lumentum）——前者應降為自報·filing，後者應降為待判定並進 `corroboration_withheld.unnamed`（6.8 補引文的對象）。

## 6. Step 6.5 sub 旗標跟著值走到消費端（Z1，R1）

**改哪裡：** `query/bottleneck.py::collapse_assertions`（多記 `sub_assertion_id`＝贏得 sub 值的那筆 assertion）、`query/structure.py`（邊的輸出多 `sub_language_in_quote`）、`query/bottleneck.py::structure_table`（列上多 canonical 那一格；既有 `assertions_without_sub_language` 照留）、`briefing/alpha_view/builder.py`（「替代難度」那一格旁註）、`query/graph_walk.py`（第 1 型命中旁印「需求側 sub≥4 其中引文撐得住 N」）、APP 結構表頁與個股頁、測試。
**怎麼改：** 旗標由 `query/sub_language.py::sub_language_flags` 算（唯一 owner），canonical 邊取 `sub_assertion_id` 那一筆的旗標；沒有 sub 的邊沒有旗標（不是 False）；**只印、不忽略、不改任何 sub、不改走圖母體**。
**⚠ 不進 digest：** 旗標與字表版本都不得進 `query.structure` 的 `result_digest` 與 staleness 的快照列（§0 第 6 條）——字表升版也不能讓讀圖變 stale。
**怎麼驗：** 夾具：sub 由引文不撐的 assertion 贏得 → 旗標 False 跟著印；同一條邊另一筆撐得住的 assertion confidence 較低 → 仍印贏家那筆的旗標；**4 份現行讀圖的 `result_digest` 與 status 與改前逐位相同**；變異：把旗標放進 digest → 讀圖 status 測試紅。
L11-6 ④：最先壞的是 `query.structure` 的 `--digest` 輸出（staleness 比對用）——改前改後對 4 個讀圖節點各跑一次，逐位相同。

## 7. Step 6.6 稀釋燈只認募資文件（Z2，R1 ＋ R2-b 常規 opt-in）

**改哪裡：** `fetchers/edgar.py`（`get_filings` 多回 `items`；或拆成「抓一次 submissions JSON」與「依表單篩」兩段，讓同一次抓取同時給落後檢查與募資文件——**不增加請求數**）、daily 步驟 `02b_history_incremental`（`python -m engine_c.history_backfill --incremental`；argv、timeout、連網宣告由 `tests/test_daily_task.py` 逐項斷言，argv 不得變）、Engine C 新表 `equity_offering_filings`（`ticker`、`cik`、`form`、`items`、`filed`、`accession` 主鍵、`fetched_at`；`CREATE TABLE IF NOT EXISTS`，**不動既有表的 CHECK**）與 `equity_offering_checks`（每檔最後一次抓清單的時間與涵蓋起點；§0.6 #13）、`engine_c/checklist.py::_equity_issuance`（讀窗內募資文件）、`alpha/wipeout.py::dilution_flag` 與 `_DILUTION_RULE`、個股頁稽核區、`docs/OPERATIONS.md`（sandbox impact review）、測試。
**募資文件（封閉清單，寫成常數＋註解）：** `424B1`–`424B5`、`424B7`、`S-1`、`S-1/A`、`F-1`、`F-1/A`；`8-K` 且 `items` 含 `3.02`（未註冊股權出售＝私募）。**不算**：`S-8`（員工計畫）、`S-3`／`F-3`／`S-3ASR`（只是授權——授權已是人工欄位 `equity_issuance_authorizations`，照舊只印）。
**判色：** 窗內新股發行金額 > 0 **且** 窗內有一份募資文件（`filed` 落在發行金額那個窗的期間到最新一份定期報告申報日之間，INV-6）→ 黃，稽核區印那份文件（form、日期、accession、items）；發行金額 > 0 但窗內沒有募資文件 → **不上色**，`absence_kind=insufficient_evidence`，理由「只有發行金額、窗內沒有募資文件——員工計畫登記與增資授權不算募資」（理由句不帶數字，§0.6 #14），另列；其餘分支照舊。抓不到 submissions → `upstream_unavailable`，不判綠也不判黃。
**sandbox impact review：** daily EDGAR 步驟 argv 不變、請求數不變（同一份 submissions）、多寫 Engine C 一張新表（私有庫）；互動回填（若需要）在 writer lock 下跑。
**怎麼驗：** 夾具：金額＋424B5 → 黃；金額＋只有 S-8 → 不上色另列；金額＋8-K 3.02 → 黃；金額＋S-3 → 不上色（授權不是募資）；抓取失敗 → `upstream_unavailable`。**真實資料：11 檔逐檔前後對照**，每檔印配到的文件或「沒有募資文件」，並抽 4 檔（AXTI、COHR、NVDA、INTC）到 EDGAR 網頁手核；黃燈每一檔都指得出一份文件。變異：把 S-8 加進清單 → 夾具紅；不看日期窗 → 夾具（窗外的 424B5）紅。
**R2-b `WORK_REQUEST`**：審查者對 11 檔自己查 EDGAR submissions 核對配到的文件與窗、確認請求數沒變、新表不影響既有表、`_DILUTION_RULE` 文字與程式一致；Boundaries 同 R2-a，另「不寫 Engine C 正式庫」。
L11-6 ④：最先壞的是 COHR（對 NVIDIA 的 20 億美元私募）與 LITE（可轉換特別股）——它們的發行是真的，若配不到 8-K 3.02 會被錯判成不上色；先看這兩檔。

## 8. Step 6.7 小修（Z1，R1；五件各一個 commit 可）

| 件 | 改哪裡 | 怎麼改 | 怎麼驗 |
|---|---|---|---|
| a 結構表逐列需求錨（#27） | `query/bottleneck.py::structure_table`（`demand_chain` 呼叫處）、APP 結構表頁、心跳段 3「前三錨」 | 先 `demand_chain(edge.dst, …)`（這一列的節點往上），走不到才 `demand_chain(edge.src, …)`；列上多 `anchor_basis ∈ {row, company}`，退回公司層的那格印「公司層」；`demand_chain` 本身不改 | Lam 的 9 列逐列印錨與 basis；改前改後「有錨」的列數不得減少（09-18 的教訓）；夾具：節點側走得到 → row、走不到 → company |
| b APP 自偵舊程式（Phase 5 #11） | `webapp/`（啟動時記程式指紋：`webapp/**/*.py` 與 `webapp/static/*` 的最大 mtime＋檔數）、`/api/v1/health`、首頁 | 每次請求比對啟動指紋與現在（只做本機 `stat`，不跑 subprocess、不讀網路——request path 規則），不同就首頁頂端印「APP 跑的是 <啟動時間> 的程式，之後程式有更新——請重啟」 | `tests/test_webapp_request_path.py` 照綠；夾具改 mtime → health 回 stale；Edge headless 看首頁橫幅 |
| c 排除未收盤 K 棒（Phase 5 #12） | 一個 owner（現行的收盤序列 owner，優先 `alpha/providers/close_series.py`，否則新開並讓追蹤表兩支與計分表一支共用） | 最後一根 bar 的日期＝交易所本地今天、且現在早於 yfinance `history_metadata.currentTradingPeriod.regular.end` → 拿掉那一根並計數；拿不到交易時段 → 保留並計數「收盤狀態未知」（不靜默丟） | 夾具：盤中 → 拿掉；收盤後 → 保留；沒有 metadata → 保留＋計數；daily 05:30 的真實輸出逐位不變 |
| d 預測表改寫規則①（Phase 5 #18） | `alpha/structure_reading/predictions.py` | ①「同 digest」加條件：**同 kind 或同日**（使用者 10-02 原句「同 digest 的同日改寫」） | 真實 15 筆終局與 Phase 5 結案相同（今天 0 筆受影響）；夾具：同 digest、不同 kind、隔日 → 不是改寫（落到 reversed） |
| e 本機 ask 規則（Phase 5 #14） | `.claude/settings.local.json`（gitignored，用 `update-config` skill） | `permissions.ask` 加 `record_trade.py` 與 `apply_ra_admission.py` 的 Bash 與 PowerShell 寫法（`python` 與 `.venv\Scripts\python.exe` 兩種直譯器）；先以 skill 的規則確認 ask 優先於 allow——**不是的話停下問使用者**，不刪 `Bash(python *)` | JSON 解析通過、ask 條數；HUMAN SUMMARY 請使用者下一次跑時確認會被問 |

L11-6 ④：a 最先壞的是心跳段 3 的「前三錨」與 `tests/test_structure_table.py`——改前改後逐列對照；c 最先壞的是 history lane 的 22 列（同一份價格上逐位不變，Phase 5 #4 的口徑）。

## 9. Step 6.8 研究（強模型；Z-research；寫 ledger 前取 writer lock）

收據：`docs/reports/2026-10-xx-phase6-step68-research.md`（每一項附原文與決定）。

1. **補具名引文**：`layer_stats.corroboration_withheld.unnamed` 的每一條，讀那份來源原文（`library/raw/`、原始 URL）：原文**有**具名這家供應商、且就是支持這條邊的那一句 → 走 RA 更正走廊（新逐字，`scripts/prepare_research_action.py`；packet 印 6.2d／6.4 的副作用與證據等級預告）→ 每份文件一個 `ra_admission` pq2；原文**沒有** → 收據寫「維持降級」與理由（例：NVIDIA 部落格的角色描述沒點名、USGS 只寫地點、SVRC 沒提 Agility、華星光年報不是在講 Sivers）。`relay` 的每一條：原文若有那家發布者自己的數據（不是轉述）→ 宣告 `origin_linkage=independent` 的 RA；沒有 → 維持。
   預期（§0.2 模擬，6.0 會重算）：補得回的候選是 NVIDIA×Lumentum 合作新聞稿（兩條）、NVIDIA 寫 Coherent 德州廠的部落格、TrendForce 寫 TSMC MRM 的那篇、Meta 的 Bailly 論文。
2. **鑄號後接著做**：RA 編號鑄好就印批次指令，接著做 6.9；使用者 go 後經 `scripts/apply_ra_admission.py` 入口 apply、`commit_pending_intake.py`、`complete-ra`。
3. **重讀讀圖**：本 Phase 標籤變更（[666]、6.2、6.3、6.4、補引文）之後 status 不是 `current` 的每一份（預期 `mat:inp_substrate`、`tech:cw_dfb_laser`），以 `python -m alpha structure-reading <node> --add spec.json` 寫新一筆（v3；兩半引用由程式核對、independent 引用過 6.4 的新規則）。RA 若還沒 go：照現況重讀、收據註明「補引文落地後可能再 stale_low」。重讀不了的明確延後並登記到期（INV-2）。
4. **四檔敘事**：AXTI、COHR、LITE、SIVE.ST 各列出「這檔坐的層／押的讀圖裡，證據標籤變了的邊」，判斷 v2 敘事的文字有沒有依賴舊標籤（例：寫了「有客戶印證」而那條已降級）→ 依賴就寫新版（`python -m alpha brief <T> --add spec.json`；反證照 v2 規則自動登記 watch），不依賴就在收據寫「不換版」與理由。
5. **不做**：不改 thesis、不入圖（除經 pq2 的 RA）、不動候選狀態以外的任何判斷；候選板「可開」照實印。

L11-6 ④：最先壞的是 AXTI 敘事押的 InP 層讀圖——它的 `rides[]` digest 指向舊讀圖；新讀圖寫入後，個股頁讀圖面板應顯示「現行」並指向新那筆（materialize 一次核對）。

## 10. Step 6.9 新管線 full chain 測試（Z1，R1）

新 `tests/test_evidence_criteria_full_chain.py`：
- **證據鏈**：夾具 assertion（客戶 origin 不具名、發布者轉述、發布者具名非轉述、名冊新寫法、身分合併前後）＋逐字 → `_classify_edges` → `query.structure` 插槽視角與 `structure_table` → `layer_stats`（`corroboration_withheld`、`ec_without_naming_quote` 0）→ 走圖第 2 型 → 心跳段 3 那一行文字；`verify_citations` 對不具名的 independent 引用拒收。
- **稀釋燈鏈**：夾具 companyfacts 發行金額＋夾具募資文件表 → `_equity_issuance` → `dilution_flag` → 個股頁稽核區那一格。
斷言的是**數字與標籤出現在下游**（artifact、心跳文字、個股頁），不是函式會動（L13）。既有 `tests/test_full_chain_acceptance.py`、`tests/test_layer_document_full_chain.py`、`tests/test_measurement_full_chain.py` 不動（若因呼叫端簽名變更要改，只改呼叫、不刪斷言，八欄列出）。

---

## 11. 驗收數的是哪一層（completion gate 第九項）

| 驗收 | 數的東西 | 層 |
|---|---|---|
| ROADMAP ①（A1）外部印證名副其實 | `ec_without_naming_quote`＝0（逐來源口徑）；本 Phase 降級的每一條在 6.8 收據有去向（補引文 RA 編號／名冊寫法／身分修正／維持降級＋理由）；**另印**外部印證 244（或 6.0 基準數）→ N 逐條、①「獨家且全自報」73 → N（預期回升，誠實的回升）、走圖第 2 型命中 0 → N | 圖 |
| ROADMAP ② 身分 | 同一家兩個代號、不是公司的公司節點：2 → 0（nava 若查不到一手來源：照實寫「未定案」與查過的來源） | 圖＋名冊 |
| ROADMAP ③ 讀圖與敘事跟上 | 被本 Phase 標籤變更弄 stale 的讀圖，每份有新一筆讀圖或明確延後且有到期；四檔 v2 敘事中引用到變更標籤的，各有新版或收據裡的不換版理由 | 讀圖、敘事 |
| ROADMAP ④ 稀釋燈 | 亮黃的每一檔指得出窗內一份募資文件；11 檔逐檔前後對照（不上色的每一檔印理由） | 敘事（稽核區） |
| 另印 | 解析不到的 SourceDoc 16 → N；sub 旗標出現在消費端的處數；staleness 同級互換的機制；[666] 的證據等級變動 | 圖、機制 |
| 小修 | Lam 9 列逐列錨＋basis；APP 舊程式橫幅；未收盤 K 棒計數；預測表規則①；ask 規則 | 機制存在與否 |
| pq2 | 本 Phase 鑄的每個編號（6.2、6.3d、6.3f、6.8 RA）在終局或在列（AGENTS：等待不得消失） | 等待 registry |

**沒有任何一個是「幾檔通過某個 filter」。** 候選板「可開」只印不驗收。

## 12. Phase 6 結案（completion gate：historical-failure-matrix §9 八項 ＋ 第九項）

1. `pytest -q` 全綠；測試檔數差＝新增－退役；函式層級以 6.0 名單比對，拿掉的每一個寫去向。
2. `python -m audit invariants` 綠（含 SourceDocSync、PointInTime、QueueLiveness、Expiry）。
3. 無未解釋語意 diff：心跳與 6.0 逐行對照，只在段 3「層：」行（新計數器）、前三錨、稀釋燈相關的歸零旗標計數、[666]／6.2／6.3 入圖造成的變動處變；個股頁面板 digest 對 6.0 批次逐檔歸因（證據標籤變動、敘事新版、稀釋燈、6.7a 逐列錨〔§0.6 #16〕）；**讀圖 `result_digest` 的變動只來自圖真的變了**（不是 6.5 的旗標）。
4. 無新 dual authority：「算不算外部印證」只有 owner 一個函式（列出全部呼叫端）；名字比對只有 `quote_names_company`；轉述字表只有一個 loader；募資文件判定只有 `_equity_issuance`→`dilution_flag` 一條路；需求錨只有 `demand_chain`。
5. 無 silent drop：沒升外部印證的每條邊帶三種理由之一；名冊無名可比與引文沒具名分開；Neo4j／EDGAR 讀不到印 `upstream_unavailable`；未收盤 K 棒拿掉的與「收盤狀態未知」的都計數。
6. Point-in-time：募資文件以 `filed` 落窗；`audit PointInTime` PASS；as-of 視角沒有拿現在的申報清單冒充。
7. lifecycle 可達：本 Phase 鑄的 pq2 都在終局或心跳逐筆列出；延後的讀圖有到期。
8. executable protection：§5 的九個夾具與三個變異、6.1／6.5／6.6 的變異、遷移工具 `--pq2` 核對與 dry-run 預設、L19 守門測試；殭屍 grep 三個 0。
9. 驗收數的是 §11 的層。

**另核對：** 舊店三個 `*.db` sha256＝6.0；`library/trades/trade_log.jsonl` sha＝6.0；`git diff <6.0> HEAD -- AGENTS.md` 為空；主題等權組 ledger sha＝6.0；讀圖、敘事 ledger 與 `event_watches.json` 的變動只來自 6.8（逐筆對收據）；Google Sheet 本 Phase 沒有任何程式寫入；`python -m webapp status` 仍列 8 個 kind；`git ls-files library/private` 為空。

closeout 報告存 `docs/reports/2026-10-xx-phase6-closeout.md`，附「本 Phase 執行中發現、下一步要決定的問題」（§14 種子＋執行中新增）與「pq2 go 的執行紀錄」。

### 結案 R2（使用者已常規 opt-in；執行者不必再問）

```
WORK_REQUEST（R2，Phase 6 結案）
Target: master 最新 commit；docs/reports/…-phase6-baseline.md、…-phase6-step68-research.md、…-phase6-closeout.md；
        docs/plans/2026-10-02-002-feat-phase6-evidence-criteria-plan.md（§0.4 amendment、§0.6 偏差）
Claimed acceptance: Phase 6 completion gate 九項全過、ROADMAP Phase 6 驗收①②③④成立（或依 closeout 照實寫的未成立項）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python -m pytest -q；python -m audit invariants；測試函式層級增刪自己比（6.0 commit 起）
  2. 證據等級：對今天的圖自己寫十行腳本，逐條外部印證邊、逐 origin 核對「引文具名主詞」與「發布者引文不是轉述句」（字表讀 config/relay_language.json；宣告 origin_linkage=independent 的文件不套轉述——plan §0.6 #2），違反應為 0；
     與 config/graph_baselines.json 的 6.0 基準鍵逐條比，每條升降都歸得到一個事件（規則／資料更正／身分合併／[666]／補引文 RA）；抽 3 條升級的邊讀原文
  3. 身分：名冊沒有 co:openlight；圖上沒有 co:openlight 節點；OpenLight 這個 origin 解析到 co:openlight_photonics；nava 的處置與收據原文一致
  4. staleness：同級互換夾具判 low；4 份現行讀圖的 result_digest 不受 6.5 的旗標影響（拿 6.5 前後的程式各算一次）
  5. 稀釋燈：11 檔自己查 EDGAR submissions，核對每一檔配到的募資文件與日期窗；S-8 不算、S-3 不算
  6. 研究收據：每條 corroboration_withheld.unnamed 都有去向；重讀的讀圖過新的 independent 規則；四檔敘事換版或不換版理由與標籤變動對得上
  7. 心跳：與 6.0 逐行對照，未解釋 diff 0；SNAPSHOT_KEYS 新鍵在快照裡
  8. python scripts/retired_mechanism_grep.py 三個 0；Decision Store 三檔、trade_log、AGENTS.md、主題等權組 ledger 不變；Sheet 沒有程式寫入；config/relay_language.json 不出現在 prompts/、skills/
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不寫任何 ledger、不跑任何 --apply
```

### 結案之後：停，不要開 Phase 7

R2 回 GO 後：ROADMAP Phase 6 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。然後 **`AWAITING_HUMAN`**：ROADMAP 沒有 Phase 7——HUMAN SUMMARY 的「下一步」印三件事：
①Phase 7 候選（旁支「海外財報來源」：台股股數與 20-F 不用申請、日韓要使用者申請 key）與「先研究到 12-22 回查」兩條路，各一句理由；②決定紀錄 §10 的 12-22 回查四條與今天的值（讀圖 ledger 份數、「可開」序列、pq2 新鑄來源、單供應商比例）；③`docs/plans/README.md`「每個 Phase 開工前要有一份 plan」那段指令。

## 13. 已知陷阱

- **`fetch_assertions` 不得 join 逐字**（會灌大 `documents`，`query/sub_language.py::fetch_all_quotes` 的註解）；逐字另查、在 Python 端以 assertion id 對。
- **分類的呼叫端不只一個**：`query/bottleneck.py::structure_table`（第 797 行附近，materialize 結構表用）、`query/structure.py::_classify_edges`（走圖、讀圖快照、`_load_edges`）、`verify_citations`、`build_socket_view`、`scripts/audit_sole_source_independence.py`、`intake/actions.py`（packet 的 origin 顯示）。動手前 `git grep -n "classify_evidence(\|_classify_edges(\|publisher_lifts(\|resolve_origin("` 列全，逐個改或寫明為何不改。
- **舊計數器的口徑錯在「任何一段引文」**：它把供應商自己的引文也算成具名，所以 Sivers→CW DFB（華星光年報）漏掉。新口徑一律逐來源。
- **「名冊無名可比」不等於「引文沒具名」**：`company_name_forms` 回空 tuple 是前者（`co:nava_thailand` 今天就是），**每個寫法都與另一家共用也是**（`usable_name_forms` 空；OpenLight 兩個代號——§0.6 #12），要分開報（`quote_names_company` docstring）。
- **單字與兩個字母的寫法誤中風險最高**（`Apollo`、`Arista` 是單一個詞，比對分大小寫；`GF` 兩個字母）：6.3a 要對全部引文掃一次、逐筆看命中；`shared_name_forms` 只防名冊內兩家共用，防不了普通字。
- **OpenLight 合併後的解析順序**：`company_id_for_origin` 先 ticker、再 slug（`co:openlight` 今天就是靠 slug 命中的）、再整串名字、再核心名稱；名冊刪掉 `co:openlight` 之後要靠 `name_aliases` 的整串比對解析到 canonical——測試釘住。
- **scoped 重載會用抽取檔的節點宣告覆寫圖上的節點屬性**（`MERGE_NODE` 是 `SET`，最後載入者贏；`migrate_entity_dedup_20260904.py` 檔頭的「順帶發現」）：改 id 時節點宣告照抄圖上 canonical 的現值。
- **同一個 doc_id 的多份抽取檔**（base＋addendum）要同一個 `origin_entity`，否則 SourceDocSync 判紅（重建時載入順序決定結果）：綜述論文就是兩份。
- **live 遷移的事前匯出沒有單一官方命令**（Phase 4 #28）：照 `migrate_611`–`615` 與 Phase 4 結案的做法，用 `scripts/backup_private.py` 的 `export_neo4j_payload`／`verify_neo4j_export` 寫進 backup-dir。
- **Neo4j 新屬性名要 admin 預熱**：apply 入口會先查 `db.propertyKeys()`；本 Phase 若會寫新的屬性名（例如 SourceDoc 多一個欄位），先改 `schema/neo4j_setup.cypher` 1b 與 `loader.load_to_neo4j.written_property_names()`、請使用者以 admin 跑預熱——**撞到 Forbidden 停下問，不自行預熱再重試**。
- **sub 旗標與字表版本不得進 digest**（§0 第 6 條）；`query.structure` 的 `as_dict` 若被拿去算 digest，附加欄位要放在 digest 範圍外（照插槽視角「附加段不進 digest」的做法）。
- **轉述字表的 L19**：不得出現在 `prompts/`、`skills/`；`intake` 的 packet 可以印「這段被判轉述」的結果，但不得把字表本身印給抽取端。
- **GSR 改 media 不回頭重驗既有讀圖**：讀圖 ledger append-only；舊讀圖若以 GSR 當 independent 引用，它在寫入當時是合法的；新規則只管新寫的（6.8 重讀）。
- **[666] 與本 Phase 互相影響**：它把一份 Reuters 宣告為 independent，InP 那幾條邊由 Reuters 撐住外部印證（[666] 之後外部印證 250，baseline §0）；**宣告 independent 的文件不套轉述檢查**（§0.6 #2：ROADMAP「翻案靠逐份宣告」；原註記寫「轉述檢查也套在那份 Reuters 上」，與 ROADMAP 衝突），具名照樣要——s2／s3／s5 都具名主詞，6 條保住；s1「AXT … said」的同源性由 [666] RA 的 L8 備註承載（宣告是文件層級的）。
- **EDGAR**：`rate_sleep()` 與 User-Agent 照 `fetchers/edgar.py`；submissions 的 `recent` 只保證最近約一年或 1000 筆，申報多的大型股（NVDA）在窗內仍夠，但要測；8-K 的 `items` 是逗號分隔字串（例 `"1.01,3.02,9.01"`）。
- **COHR、LITE 的發行是私募**：配的是 8-K 第 3.02 項，不是 424B；配不到就是判色寫錯，不是它們沒募資。
- **yfinance 的交易時段**：`history_metadata` 有時缺 `currentTradingPeriod`；缺就保留那根並計數「收盤狀態未知」，不靜默丟。
- **APP request path 規則**：不跑 subprocess、不讀網路、不重建；指紋只用本機 `stat`。
- **心跳格式被 `tests/test_heartbeat.py` 釘住**；`SNAPSHOT_KEYS` 是封閉清單，加鍵要同 commit 改測試；舊快照沒有新鍵時 diff 印「首日」。
- **`config/graph_baselines.json` 只加鍵**；新 config（`relay_language.json`）要在 `.gitignore` 補白名單、在 closed-vocabulary registry 登記（`tests/test_config_tracking.py` 是剎車）。
- **Windows**：python 不認 `/tmp`，暫存用 scratchpad；程式碼不放 heredoc（寫成檔再跑）；子行程用 `sys.executable`；PowerShell 管線會加 BOM。
- **可開為零就零**：候選板今天可開 0 是合法結果；本 Phase 不為它做任何事。

## 14. 結案時要列的待決問題（種子；執行中發現的往下加）

1. **12-22 回查**（決定紀錄 §10）：讀圖 ledger 份數、「可開」序列（`candidate_state_series.jsonl`）、pq2 新鑄來源、單供應商比例——結案 HUMAN SUMMARY 印今天的值。
2. Phase 5 closeout §5 照帶：#5（history lane 退役）、#6（主題等權組換版斷點）、#9（預測表納入 thesis 反證觸及）、#10（計分表逐則記組是否已定義）；#8 FRA:2DG 回填（使用者動作）。
3. Phase 4 closeout §6 其餘資料口徑題照帶：#5、#6、#7、#8、#9、#10、#13、#14、#18（sub 字表 v2）、#19、#21、#23、#24、#25、#28。
4. Phase 3 closeout §5 #14（Engine C 口徑）、#15（三題 as-of 視角）照帶。
5. 轉述偵測只套發布者（§0.3）：若之後出現公司 origin 轉述另一家公司說法的案例，再擴（L17）。
6. 字表 v1 的轉述詞是否漏掉常見寫法（`unveiled`、`launched`、`introduced` 是事實陳述還是轉述，本 Phase 刻意不收）——要換樣本量過再改。
   另一面（6.4 實作時發現）：`states` 會誤中「United States」（2026-10-03 真實資料 0 筆受影響；只會讓標籤變保守）——同一次量。
7. Phase 7 候選：旁支「海外財報來源」（邊緣候選 22 檔裡 18 檔缺「已定價」的主參照）。
8. （6.4）插槽視角：發布者過了 `publisher_lifts` 但沒具名或只是轉述的引文照列並旁註（§0.6 #11）——讀的人若覺得雜訊多，再議要不要只列撐得住的。
9. （6.0–6.3 帶進來的，見 baseline §14、§16.3、§17.3）更正走廊 `raw_excerpt` 表頭重複；`tests/test_intake.py` 的 `forbidden_driver` 絆線可能空跑；
   Noveon／USA Rare Earth 那兩段引文掛在 MP 的邊上是否抽取錯置；`co:apollo` 的名字寫法（「Apollo」在圖上一半是 Google 的專案代號）。
10. （6.6）**424B2／424B5 分不出股權或債**：NVDA、META 的黃燈配到的是公司債說明書（手核封面：Notes／Senior Notes，baseline §20）；
    MRVL 配到的 10 份裡 424B5、424B2 各一份也是 Senior Notes（R2-b 手核；它另有 8-K 第 3.02 項與 424B7 的股權文件，黃燈不受影響）。
    要分有兩條路：①每份**新出現**的 424B 多抓一次文件或申報費用附件判股權／債（daily 偶爾多 1–2 次請求，違反本 Phase「請求數不變」）；
    ②維持現狀、讀的人看稽核層的文件代號自己判。這是使用者的題（改清單或請求數都動到 §0.1 #9 的定案）。
