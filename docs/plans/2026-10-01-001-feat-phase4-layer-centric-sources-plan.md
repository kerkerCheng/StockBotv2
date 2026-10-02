---
date: 2026-10-01
topic: phase4-layer-centric-sources
status: active
derived_from: docs/ROADMAP.md（Phase 4 列＋旁支「Phase 4 plan 的使用者定案輸入」「本機 Research Action apply 入口」「重載會洗掉 SourceDoc 的分段標籤與標題」）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G4；§1.1、§5 Fisher scuttlebutt、§6.1）、docs/reports/2026-09-30-phase3-closeout.md §5、docs/reports/2026-09-26-phase2-closeout.md §5、docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md §14
plan_review: 反方驗證已做（2026-10-01，使用者對 12 題定案後以 workflow 跑：4 位反方各帶一個子系統切片帶程式碼推翻 3 題＋2 個橫切視角〔authority／Goodhart、過度工程〕，共 12 條 amend、0 條 wrong、12 條 blocking finding；覆核由 plan 作者逐條對照程式碼做〔第二層 25 位覆核者與補漏者撞額度未跑〕）；處置見 §0.7，改變原定案的 8 處由使用者 2026-10-01 確認（§0.1 第二張表）
---

# Phase 4 層中心來源（給執行模型的完整 plan）

> **執行者：全程強模型（使用者 2026-10-01 定案 #11「全程用 opus 5.5」）**，走 `skills/development-flow/SKILL.md`（Z1 以上 R1）；Step 4.8 是研究步驟，執行者就是強模型所以**不停、直接做**。
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 4」（含本 plan §0.4 的 amendment A1–A5）導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文（尤其「四個人工 gate」「圖的寫入紀律」「已知會失焦的指標判別法」「L6／L8／L11／L18／L19」）→ ROADMAP「Phase 4」與三列旁支 → 本 plan §0.1–§0.4、§0.7 →
> 決定紀錄 §1.1（單供應商 Cypher）、§5（Fisher scuttlebutt＝G4 的文件版）、§6.1（走圖的洞不得恆亮）→ `docs/refactor/historical-failure-matrix.md` §2 →
> `docs/OPERATIONS.md`「sandbox impact review 五步」→ `schema/graph_schema.md` §6–§7（origin_entity、L8、sole_source）→ `query/bottleneck.py::classify_evidence` 與 `_name_variants`／`_origin_mentions` 檔頭 →
> `query/graph_walk.py` 檔頭（九型、`always_on`）→ `engine_b/leads.py` 檔頭（狀態機、URL 必填、`triage()` 契約）→ `intake/actions.py` 檔頭（research-action/v1 拒收未知欄位、`REQUEST_OPTIONAL_FIELDS`）→
> `identity/registry.py::CompanyIdentity`（`display_name` 是 mechanical；`aliases` 是 ticker 不是名字）→ `alpha/wipeout.py` 檔頭 → `engine_c/history_backfill.py::METRICS`（封閉、進 CHECK）。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表／機制），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字是**圖（供給側邊的分布與 evidence class、帶 sub 的 assertion 與其引文旗標、SourceDoc 的 origin 解析、section／title 與抽取 JSON 的一致）、
> 走圖問句（第 2 型命中與旁邊印的讀圖／lead 狀態）、lead registry（研究啟動時鑄的 lead 與其終局）、RA 紀錄（`layer_enumerations` 核對結果、approval 戳記）、
> 個股頁稽核區（稀釋燈逐檔來源與顏色）、機制存在與否**（見 §11）。
> ⚠ 走圖第 2 型的命中數、單供應商計數都**只准往「圖更完整」的方向被研究改變**，不得用改母體定義、改分類器讓數字好看——那是 L19 的 Goodhart 鏈。本 plan 動到分類器的兩處（§0.7 Q8b-B、Q4）都要求結案印出「因此變動的邊數」。

**一句話目標：** 圖從「我們讀了誰的文件」變成「哪一層有誰在供、是誰說的」：每一份入圖的層文件都答得出「它列舉了哪一層的供應商集合、發文者是客戶端／第三方／供應商自己」；
每一條「只有一家且自報」的邊都有一個有到期的記憶（讀圖）與一條有終局的研究題（lead）在追；每一個 `substitutability` 都看得出它的逐字有沒有真的談可替代性。
它服務 G4「預算從深挖大公司移到列舉薄層的供應商集合」與決定紀錄 §1.1 的診斷「65% 單供應商量到的是我們讀了誰的文件」。

---

## 0.1 使用者定案（本 plan 的判斷全部來自這兩張表）

**2026-10-01 第一張（12 題；使用者：「除了 11 我應該全程用 opus 5.5 剩下都 ok 照你建議」）：**

| # | 題目 | 定案（反方驗證後改動的以 ★ 標、改法見第二張表） |
|---|---|---|
| 1 | 選源規則住哪 | **A**：改既有三個 skill，不新開 skill ★（層文件不當 source-trace「最上面一階」，改成「輸入是層／節點」專節＋登記 `source_routes.json`；company-onboard 整條入圖路改走 pq2） |
| 2 | packet 的「列舉了哪一層」怎麼記 | **A**：結構化 `layer_enumerations[]`＋packet 印 origin／source_type／tier＋`source_type` 加 `teardown`、`datasheet` ★（住頂層選填欄不住 `report`；只核對「在本包」不查圖；加 `relation`、`origin_role` 字彙） |
| 3 | 走圖第 2 型餵 lead-intake | ★ **改**：不由 daily 鑄 lead。記憶住讀圖（第 2 型 `hit_rule` 加「且該節點沒有現行層讀圖」）；lead 只在互動 session 研究啟動那一刻鑄（沿 2026-09-02 coverage-gap 前例），終局＝RA 入圖或 park（`awaiting_named_disclosure`／`not_pursued`＋watch） |
| 4 | 第 2 型「自報」判準的洞 | **A** ★：`config/publishers.json` 只有「自己產生資料」的 kind 才算外部印證；媒體轉述不升級（L11-3）；origin 解析一個 owner（`classify_evidence` 與 `verify_citations` 共用）；`display_name` 補齊 100/100 排在 Q8b-B 之後、publishers 之前 |
| 5 | `unsupported` 加在哪 | **A** 先量後放閘、消費端不改 ★（旗標叫 `sub_language_in_quote`、算在一個 owner、住結構表／走圖 artifact 不住投影 meta；分母是 sub 非 null 的 assertion） |
| 6 | 驗收③基準重量 | **A** ★：拆兩個數——存量只印當歷史；驗收是「Phase 4 新入圖的帶 sub assertion 中引文含字表語言的比例」（§0.4 A3） |
| 7 | 驗收①②計數器與「逐字撐住」 | **A** ★：①用 `query.structure` 的 supply_side（只算 `supplies_to`）當 owner、印絕對數不印比例，驗收句改「ns==1 且供貨邊全部自報的節點數 → 下降」；②驗收改「有一份非供應商 origin 的來源、引文逐字具名 ≥2 家供應商的層數 → 上升」，「每家逐字撐住」降為稽核欄（§0.4 A1、A2） |
| 8a | 稀釋燈編法 | **A** ★：tag 改 `us-gaap:StockIssuedDuringPeriodValueNewIssues`（三檔實測都有；原指定的股數 tag 在 AXTI／LITE 不存在）；印金額與占市值 %；「非 SEC」改「非 10-K／10-Q 國內申報人」；Engine C `METRICS` CHECK 遷移 → R2-c |
| 8b | 客戶高管具名編法 | ★ **改採替代案 B**：刪 `classify_evidence` 325-330 那支抬升、併進 `self_reported`（今天 0 條邊命中；連鎖由補 `display_name` 觸發，不由本題） |
| 8c | `_TICKER_ENRICHMENT` 退出身分解析 | **A** ★：保留 `get_execution_aliases()` 名稱與 dict 形狀（凍結區零改動）；名冊 constructor 對 `execution_symbol` 做衝突檢查；`_YFINANCE_SYMBOL_ALIASES` 留並註明是行情供應商語法；R2-b 加 pq1 排序逐位比對 |
| 9 | 兩個旁支併入 | **A** ★：apply 入口＝`--pq2 N --digest`＋四道 fail closed＋apply 前寫 approval 戳記（授權載體仍是對話中的明確核准）；SourceDoc section／title 改「寫回抽取 JSON」，loader 契約不動 |
| 10 | 研究 Step 先列舉哪幾層 | **A** ★：`mat:inp_substrate` 已有兩份第三方層文件在圖上（GSR、Reuters）——改成資料工（補名冊＋登記 publisher）後看計數器；`tech:cw_dfb_laser` 找公開層文件、找不到走誠實終局；第 2 型 2 筆：AMAT＝節點太粗走 RA、COHR 六吋 InP＝AXT 8-K 已在庫走 RA |
| 11 | 執行者模型 | **全程 opus 5.5**（使用者改建議；Phase 3 做法）；研究 Step 不停 |
| 12 | 執行期間 R2 | **A** ★：常規 opt-in；預定三處改為 R2-a（packet／loader／apply 入口）、R2-b（identity：名冊兩個新欄＋enrichment 去除＋pq1 排序比對）、R2-c（Engine C `METRICS` CHECK 遷移＋稀釋燈，沿 Phase 3 R2-c 定義）；evidence 分類變更不開 R2、改以結案印「class 變動邊數＋因此 stale 的讀圖數」 |

**2026-10-01 第二張（反方驗證後改變原定案的 8 處；使用者同日確認「Ok」，連同 R2 三處、LITE 可轉換算黃、名冊兩個新欄）：**

| # | 原定案 | 改成 | 為什麼（證據在 §0.7） |
|---|---|---|---|
| C1 | Q3 daily materialize 鑄 lead、跳 triage、三種終局 | 讀圖當記憶；lead 只在互動研究啟動時鑄；終局用既有字彙 | lead 狀態機沒有「自動結案」轉移；`parked→pending` 會清 triage 回 LLM 批次；`wake_lead` 到期是終局 `watch_expired` 不是重問；走圖每日重算 vs lead 有狀態＝第二個狀態源；鑄出的 lead 會把第 5 型 7/13 恆亮旗標無研究地關掉 |
| C2 | Q8b 新等級 `named_counterparty` | 替代案 B（刪抬升、併 `self_reported`） | 真實圖 `counterparty_joint`＝0 條、那支分支 0 份命中；新等級要同步 5 張對照表去承載一個 0 成員的類別；連鎖是補 `display_name` 時才發生 |
| C3 | Q8a 用 `StockIssuedDuringPeriodSharesNewIssues`＋`ProceedsFromIssuanceOfCommonStock` | 用 `StockIssuedDuringPeriodValueNewIssues`（金額）；proceeds 只當稽核欄 | 三位反方各自抓 companyfacts：股數 tag 在 AXTI、LITE 不存在、AAOI 停在 2014；AXTI 2026 Q2 增發 6 億美元只在金額 tag；照原案 AXTI（+42%）會印成「tag 缺席」 |
| C4 | Q4 登記的第三方一律 `externally_corroborated` | 只有 `own_analysis` 類 kind 升級；媒體永不整類升級，媒體文要升級須在 source_doc 宣告 `origin_linkage=independent` | 73 份未解析 origin 裡媒體轉述供應商新聞稿成對出現（Semiconductor Today／optics.org 同事件）；L11-3「多個二手都這樣說≠一手已證實」 |
| C5 | Q7 ①用 §1.1 Cypher（`SUPPLIES_TO|DEVELOPS`）印比例；②「逐字撐住」當驗收 | ①用 supply_side（`supplies_to`）印絕對數、驗收「ns==1 且全自報」；②驗收「非供應商來源具名 ≥2 家」，撐住降稽核欄 | 兩種定義同圖算出 118 vs 83 個單供應商（L12）；比例分母含 30 個 0 供應商節點，加 decompose 節點就「下降」；「逐字撐住」今天 0/10——引文寫「we／本公司」、71/100 家沒 `display_name`，量到的是名冊完整度 |
| C6 | Q5Q6 旗標住投影 meta；驗收③「存量比例 → 下降」 | 旗標算在一個 owner、住結構表／走圖 artifact；驗收③＝新入圖 assertion 的 supported 比例，存量只印 | `attribute_resolution_meta_json` 只有 `thesis/evidence_manifest` 在讀、不每日刷新；結構表／走圖讀 EdgeAssertion 不讀投影；存量不會自己變，「→ 下降」只剩稀釋＝研究量指標；字表寬窄把比例從 58% 搬到 95% |
| C7 | Q9 ①「要 pq2 go 收據才執行」；②loader `coalesce` | ①入口驗編號／ref_id／digest／未結案／未過期，apply 前寫 approval 戳記；②section／title 寫回抽取 JSON | `ra_admission` 的 go 收據只在 apply＋publish 後由 `complete-ra` 產生、bare go 被拒——apply 前不存在 go 收據；`coalesce` 只救增量重載，全量重建時 10 份 section 仍消失（不在可重建輸入裡，L10），title first-wins 在重建時因檔名排序仍拿到 addendum |
| C8 | Q10 兩層各找一份層文件 | `mat:inp_substrate` 改資料工；`tech:cw_dfb_laser` 保留研究＋誠實終局；AMAT 走 RA 拆節點 | GSR 報告（industry_report）與 Reuters 已逐字列舉 AXT／Sumitomo／JX 與份額、已入圖，卡在 origin 未登記＋兩家沒 `display_name`；cw_dfb 16 份來源沒有一份列舉供應商集合；AMAT 節點圖上已有 LRCX 與更細節點 |

**未改的定案一併確認：** 稀釋燈的 LITE 案例——`StockIssuedDuringPeriodValueNewIssues` 1,999.7M 是**可轉換特別股**，不是普通股增發；本 plan 預設**算黃**（募資就是募資，印出 instrument tag），使用者可改。

**刻意不做（2026-10-01 一併確認）：** `supplies_to → prod:` 不另給關係（[654] 只加 `develops` 已解、0 digest 變動）；`prod:` 一表多義不動；海外財報來源另排（要使用者註冊 key）；不改 `AGENTS.md` 判準句；不重量邊緣門檻；Phase 3 plan §14 其餘 Engine C 口徑題（#8、#9、#10、#15–#19、#21、#45）帶到 Phase 5 前。

**2026-09-30 已定案、本 Phase 直接做（ROADMAP 旁支「Phase 4 plan 的使用者定案輸入」）：** 舊 session assessor 240 條反證退役不印；`config/holdings_coverage.json` 的 `ignored` 名單接進 held_index／心跳（觸發 7803 已於 10-01 出清，做的是機制）；自家百分位印樣本覆蓋率、不設門檻；同一份敘事內重複的反證條件寫入端拒收、跨公司不算重複；邊緣門檻 10B／12 位不動。

## 0.2 現況實測（2026-10-01；**現況數字會腐壞，引用前重跑查證命令**）

| 事實 | 數字 | 查證 |
|---|---|---|
| 技術／產品／材料節點；§1.1 口徑（`SUPPLIES_TO\|DEVELOPS`）ns=0／1／2／≥3 | **186；30／118／28／10**（09-22：186／121）；**supply_side 口徑（只算 `supplies_to`）：72／83／？／10** | 決定紀錄 §1.1 的 Cypher；`query/structure.py:196-199` |
| canonical 邊的 evidence 分布 | **536 條**：externally_corroborated 217／needs_review 113／self_reported_costly 106／self_reported 100／**counterparty_joint 0** | `_classify_edges` 跑全圖（唯讀） |
| `classify_evidence` 325-330（origin 解析到主詞＋字串另具名他家）命中 | **0 份 SourceDoc**（Sivers／Ayar 那份因 `co:ayar_labs` 無 `display_name` 解析不出 Ayar） | `query/bottleneck.py:274-290、316-333`；`extractions/sivers_ayar_wdm16_ecoc_2024_09_19.json:130` |
| SourceDoc 220 份：origin 解析得到／不到 | **147／73**（59 個不同字串；news 41、industry_report 24、filing 4、paper 2、ir_deck 2）；`publisher` 欄 178 份有值 | `company_id_for_origin` 逐份跑 |
| needs_review 113 條邊按未解析 origin 分類 | 只有研究／政府／學術型 45；只有媒體型 43；名冊公司缺 `display_name`／逗號註解 15（其中 origin＝主詞自己 9）；其他 10 | 唯讀 probe（§0.7 Q4） |
| 補齊 `display_name` 的模擬（100 家） | **16/536 條邊變**：14 條 needs_review→counterparty_joint、2 條 self_reported→counterparty_joint（含 Sivers 自家 PR 的 3 條與 1 條假陽性 `co:apollo`：`_origin_mentions` ≥4 字子字串撞到）；另 9 條 needs_review→self_reported（origin 本來就是主詞） | 同上 |
| 名冊 | 100 家：`display_name` **29**、`aliases` 3；`co:jx_advanced_metals`、`co:sumitomo_electric`、`co:ayar_labs`、`co:o_net_technologies`、`co:applied_materials` 等無 `display_name`；`_strip_annotation` 只去尾端括號（逗號註解 ×3 解不到） | `config/company_identity.json`；`query/bottleneck.py:205-209` |
| 帶 `substitutability` 的 EdgeAssertion | key 存在 **133**，其中 **值非 null 113**（20 筆 null 不構成主張）；sub≥4 的 70 筆；QUOTES 連結 203、Source 節點 163、不同引文 161 段（≥190 字截斷 72 段）；字表敏感度：窄字表 supported 6/113、寬字表 47/113 | 唯讀 Cypher；`query/edge_conflicts.py:178-179`；`query/bottleneck.py:373-374` |
| `edge_conflicts` | 帶 sub 的邊 104：auto 81／open 8／empty 15；`library/resolutions/` 28 份（sub 8：7 choose_value、1 unknown） | `python query/edge_conflicts.py --json` |
| `attribute_resolution_meta_json` 的讀者 | **只有 `thesis/evidence_manifest.py`**；結構表／走圖／`get_bottlenecks`／Q1／鏈段／讀圖快照全部經 `collapse_assertions` 讀 EdgeAssertion；`edge_resolution project` 不在 daily 步驟裡 | grep；`query/bottleneck.py:357-419、718-728` |
| 讀圖 staleness 對 evidence／sub | digest key 含 evidence（`query/structure.py:135-159`）；層讀圖 evidence 變＝low（不進第 4 型）、插槽供給側 evidence 變＝high；sub 變＝high | `alpha/structure_reading/staleness.py:72-75、141-167` |
| 現行讀圖 | 4 檔（`tech_cw_dfb_laser` 5 筆、`mat_inp_substrate` 7 筆、`prod_supernova`、`prod_els_8ch_module` 各 socket）；cw_dfb 供給側 6 家、inp_substrate 3 家（axt costly、jx／sumitomo needs_review） | `library/private/alpha/structure_readings/` |
| 走圖今天 | 第 1 型 4/13、**第 2 型 2/13**（`tech:semiconductor_manufacturing_equipment`←AMAT 自報·filing：圖上已有 `co:lam_research` 與 `tech:deposition_etch_clean`；`tech:six_inch_inp_production`←COHR 自報：AXT 8-K `extractions/axti_8_k_20260702_coherent_inp_supply.json` s2 逐字「6-inch indium phosphide (InP) wafer substrates from AXT to Coherent」已在庫、未接到該節點）、第 3 型 2/7、第 5 型 7/13（always_on） | `python -m query.graph_walk --json` |
| 層文件現況 | `mat:inp_substrate`：GSR（industry_report，origin「Global Semi Research」未解析）逐字「AXT ~36%／Sumitomo ~42%／JX ~13%」、Reuters 出口管制文逐字三家——**兩份非供應商層文件已入圖**；`tech:cw_dfb_laser`：16 份來源全是供應商自家／需求端 Broadcom／談 POET 的第三方／Borecraft 論壇，**沒有列舉供應商集合的公開一手**；台股年報「競爭廠商」段（VPEC 2455、LandMark 3081 已在 extractions）具名同業 | `extractions/gsr_inp_substrate_market_2026_05_16.json`；grep origin_entity |
| `layer where a single SourceDoc lists ≥2 suppliers` | 10 層；其中 ≥3 家供應商的層 4（external_laser_source、cw_dfb_laser、els_8ch_module、inp_substrate） | 唯讀 probe |
| lead | 唯一入口 `engine_b/leads.py::register`（URL 必填、lead_id＝URL sha256）；狀態機 `triaged_go→researching／parked`、`applied` 只從 `action_prepared`、`parked→pending` 清 triage；`triage()` go 必附 classification、`classified_by` 寫死 `triage_semantic_v1`；trace_status 9 值含 `awaiting_named_disclosure`（非終局、需 trigger entities）；`wake_lead` watch 到期→`watch_expired` 終局；2026-09-02 coverage-gap 前例 4 筆：3 applied（經 RA）、1 parked（附 trigger＋pq2） | `engine_b/leads.py:45-53、167-180、491-493、954-1013`；`config/lead_trace_status.json`；`engine_b/event_watch.py:583-607` |
| RA packet | `report` 六欄 **exact fields**（多一個 key 拒收、`render_review_packet` 缺欄回 None）；頂層 `REQUEST_OPTIONAL_FIELDS={"focus_company_id"}`、digest＝整個 payload canonical sha256；既有 **139 筆**紀錄（131 pushed／5 partial／2 expired）manifest 都沒有 origin 欄；prepare 不開 Neo4j；pq2 列另有 `_ra_graph_impact` 印 origin＋tier | `intake/actions.py:35-68、176-191、194-265、602-614、647-688`；`engine_b/todo.py:1746-1774` |
| `ra_admission` 的 go | bare `go` 被 `_validate_go_receipt` 拒（receipt 必含 action;digest;commit）；唯一結案路＝apply＋publish 後 `complete-ra --digest`；池裡 137 筆全部已 resolve（125 go／12 drop）、**apply 前沒有任何「已授權」物件**；`.claude/settings.local.json:32` 有 `Bash(python *)` 寬鬆放行；無人值守 LLM step `--tools ""` | `engine_b/todo.py:284-300、1202-1270`；`crons/llm_step.py:40-64` |
| `_finalize_research_action_impl` | production 0 呼叫端；`tests/test_intake.py` 10 處；活文件點名 `_apply_research_action_impl` 的：`prompts/intake_protocol.md:100`、`skills/daily-brief/SKILL.md:700`、`skills/lead-intake/SKILL.md:155`（OPERATIONS 沒有） | grep |
| SourceDoc section／title | 圖上 32 份有 section；**10 份只存在圖上**（9 份 JSON 為 null、`nvidia_photonics_pr_2025_03_18` 沒有任何抽取 JSON）；21 個 doc_id 出現在兩份抽取檔（base＋addendum），圖上 title 是 addendum 的；loader 契約「一手優先、直接覆寫」只 coalesce published_at／retrieved_at；三處「合法拆段」判準互異（loader／health_audit／audit） | `loader/load_to_neo4j.py:155-175、300-335`；`query/health_audit.py:333-335`；`audit/checks.py:155-166` |
| `source_type` 字彙副本 | **四份**：`schema/vocab.json:81-89`、`intermediate_format.schema.json:88-98`、`extract.py:317-321`（硬編碼）、`skills/lead-intake/SKILL.md:113`（散文）；同步測試只單向（vocab ⊆ schema）；`query/bottleneck.py:401-402` 用 `source_type=='filing'` 判 costly | 讀四處；`tests/test_robotics_ontology.py:150-165` |
| 選源路徑登記表 | `config/source_routes.json` 13 條 route（rung／applies_to／tier_cap），`sourcing/routes.py::missing_rungs()` 是「你還沒試的清單」、park 必附收據；**沒有層文件 route** | 讀該檔 |
| skill 現況 | `source-trace` 是 claim 驅動（41-45 行實測「法說 quote 直接去 transcript」）；`company-onboard` Step 2 用不存在的 `--type`、Step 4b 的 extract 旗標不符、Step 1 指向已退役的 `TICKER_MAP`、**Step 4d 直接 `loader/load_to_neo4j.py` 入圖、全文零次提到 pq2**；`lead-intake:125-128` 規定 source-trace 是唯一分路規則；`research-drain:169` 已寫「層中心選源」；沒有任何測試覆蓋 company-onboard | 讀四個 skill |
| 稀釋燈 | 規則：最新點 vs ≥365 天前最近點，增加就黃；國內申報人 35 檔用 `shares_outstanding_cover`、其餘 38 檔（含 20-F 的 TSM／UMC／HIMX／GFS／TSEM／NBIS）用 yfinance；**companyfacts 實測**：`StockIssuedDuringPeriodSharesNewIssues` AXTI／LITE 不存在、AAOI 停 2014；`StockIssuedDuringPeriodValueNewIssues` 三檔都有（AXTI Q2'26 600.1M、AAOI H1'26 1,028.2M、LITE Q3 FY26 1,999.7M＝可轉換特別股）；proceeds tag 各家不同；員工行權另有 `StockIssuedDuringPeriodSharesStockOptionsExercised`；`METRICS` 7 值烤進 SQLite CHECK、`ensure_history_schema` 只 CREATE IF NOT EXISTS；`_span_class` 只有 quarter／nine_month／annual；wipeout 串接點兩處 | `alpha/wipeout.py:116-170`；`engine_c/history_backfill.py:65-92、127-156`；`alpha/providers/candidates.py:208-225`；`briefing/alpha_view/sources.py:438-451` |
| 舊 session assessor 反證 | 63 檔 240 條（私有可改寫 JSON，不是 ledger）；印在 downside 面板（`source="judgment"`、「未盯」）與 research 面板「什麼會推翻它」兩處 | `engine_b/disproof.py:467-613`；`briefing/analyst_view/compose.py:219、466-473` |
| `holdings_coverage.json` | `ignored: []`；**沒有 .py 讀它**；OPERATIONS 1494-1498 仍寫 `coverage=user_ignored` | grep |
| `_TICKER_ENRICHMENT`／別名 | 15 鍵，只有 FRA:2DG 帶 `neo4j_id`；`_TICKER_ALIASES` 是 `identity.execution.get_execution_aliases` 的 import 複本；`_EXECUTION_ALIASES={"SIVE.ST":"FRA:2DG"}`、`_YFINANCE_SYMBOL_ALIASES={"FRA:2DG":"2DG.F"}` 都寫死在 `identity/execution.py`；凍結區 `decision_lab/adapters/holdings.py` 只 `return get_execution_aliases()`；名冊 constructor 只對 research_ticker／aliases 做衝突檢查 | 讀上列 |
| 自家百分位 | `samples=len(series)` 已算、沒有分母；「滿 3 年」只看頭尾跨度 | `alpha/three_questions.py:204-261` |
| 同敘事重複反證 | 寫入端 `live_by_condition` 只比 thesis／reading 來源；`register_brief_watches` 只用 `brief:<id>#<n>` 去重；真實 ledger 4 檔本版內重複 0 | `alpha/providers/briefs.py:147-252`；`engine_b/narrative_watches.py:248-250` |
| daily | 唯一排程 `StockBotv2-Daily` 台北 05:30、上限 240 分；`13_materialize` 是 `webapp materialize --graph-walk`（只寫 state artifact）；`01_harvest` 是 `leads.register` 唯一無人值守入口；`DAILY_STEPS` 封閉有逐項相等測試 | `crons/daily_task.py:130-190` |
| 測試 | 3006 passed（HEAD `abc1198`）；`python -m audit invariants` 13 PASS | 最近 commit 訊息 |

## 0.3 本 Phase 刻意不做

- **不改 sub 的消費端**（`collapse_assertions`、走圖母體、鏈段、`get_bottlenecks`）：只量、只標、只印；結案印「若忽略 unsupported 母體變幾」留決定（§14）。
- **不讓「外部印證」要求引文具名供應商**（cw_dfb 讀圖指出的 L6 缺口）：本 Phase 只加計數器「externally_corroborated 但引文不具名供應商 N 條」，改判準留 §14。
- **不另給 `supplies_to → prod:` 關係**、不動 `prod:` 一表多義；不改 `counterparty_joint` 的 320 分支（整串不解析且具名 ≥2 家）。
- **不由 daily 鑄 lead**（C1）；不給走圖任何分數或優先序（G2）；第 1、3 型不接 lead。
- 不做海外財報來源；不重量邊緣門檻；不改 `AGENTS.md` 判準句；不做量測（Phase 5）。
- **不替使用者挑層**：Step 4.8 的兩層與兩筆命中是使用者點名；之後「下一個列舉誰」由走圖第 2 型命中（lead 時間）與使用者點名決定。
- **不自動入圖**：`layer_enumerations` 核對只是 packet 的機械檢查，入圖仍經 pq2 `ra_admission` 人工 gate；apply 入口不進任何無人值守 allowlist。
- 不新開 skill；不回填 Engine C 人工 ledger；不動舊 Decision Store；不放寬 `company_id_for_ticker`（加欄位不改既有解析語意；`name_aliases` 不進 `by_ticker`）。
- 不把 `_YFINANCE_SYMBOL_ALIASES` 搬進名冊（行情供應商語法，註明後留在 `identity/execution.py`）。
- Phase 3 plan §14 其餘各題（#2、#4、#5、#6、#7、#8–#10、#14–#19、#21–#24、#26–#28、#30、#31、#33、#36、#37、#39、#41、#44、#45、#47、#48、#50、#51）不在本 Phase，照實帶到 §14。

## 0.4 ROADMAP amendment（五欄；使用者 2026-10-01 定案；ROADMAP Phase 4 列同 commit 改寫）

**A1｜驗收①改絕對數、單一 owner、凍結節點集合**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「①單供應商節點比例 65% → 下降（Cypher 同決定紀錄 §1.1）」 |
| 新觀察 | §1.1 用 `SUPPLIES_TO\|DEVELOPS`、走圖與讀圖的 supply_side 只用 `supplies_to`，同一張圖算出 118 vs 83（L12）；比例分母含 30 個 0 供應商節點，decompose 加節點就「下降」；0→1 家是正當研究卻讓比例上升 |
| proposed change | 常駐計數器以 `query.structure` 的 supply_side 為唯一 owner（只算 `supplies_to`），印 ns=0／1／2／≥3 四個絕對數不加總不做比例；驗收①＝「對 Step 4.0 凍結的節點集合，ns==1 **且供貨邊全部自報**（evidence ∉ {externally_corroborated, counterparty_joint}）的節點數 → 下降」；§1.1 的 65% 留在決定紀錄當 09-22 歷史數 |
| why | 層文件修的正是「只有一家且只有它自己說」；這個數不被 decompose 加節點、也不被 0→1 家的正當研究推動 |
| impact | 新計數器（§5 Step 4.4）、`crons/heartbeat.py` 段 3、走圖 artifact、結構表頁首 |

**A2｜驗收②改「非供應商來源列舉」、「逐字撐住」降稽核欄**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「②供應商集合 ≥3 家且逐字撐住的層數 10 → 上升」 |
| 新觀察 | 「逐字撐住」沒有定義；依「每家供應商引文逐字含其名」今天是 0/10（一手 filing 寫「we／本公司」、71/100 家沒 `display_name`）——量到的是名冊完整度；「≥3 家」只會因入圖邊增加而升，讀三份供應商自家 PR 就能過＝研究量指標 |
| proposed change | 驗收②＝「至少一份來源的 origin 不是該層任一供應商、且該來源引文逐字具名該層 ≥2 家供應商的層數 → 上升」（G4 的指紋：一份文件列舉集合；基準在 Step 4.4 以名冊補齊後的名字集合重量，2026-10-01 粗量 ≥2 家層文件 10 層／其中 ≥3 家供應商 4 層）；「每家供應商撐住」（引文含名 **或** 該 assertion 的 SourceDoc origin 解析到這家）只當稽核欄印、不驗收；印「未解析 origin M」另一格，不把 None 壓成第三方 |
| why | AGENTS「會隨多讀一份文件單調上升的指標量的是研究量」；層文件的簽名是「一份非供應商文件具名多家」 |
| impact | 同 A1 的計數器；`query/bottleneck.py` 名字比對函式（與 packet 共用） |

**A3｜驗收③拆兩個數、字表進 repo、分母改 assertion**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「③`auto` 投影的 sub 中逐字不含可替代性語言的比例（2026-09-21 量 103/136）→ 下降」 |
| 新觀察 | 09-21 的字表與命令沒留下來；分母 136 含 sub=null；消費端不讀投影；存量 assertion 不會自己變，「→ 下降」只剩新 assertion 稀釋＝研究量；字表寬窄把比例從 58% 搬到 95% |
| proposed change | 「③a 存量：Step 4.4 以 repo 內字表 `config/substitutability_language.json`（版本化）對 sub 非 null 的 assertion（2026-10-01：113 筆）印『引文不含字表任一詞』的筆數與 id 清單——只印、當歷史；③b 驗收：Phase 4 期間新入圖或 supersede 的帶 sub assertion 中，引文含字表語言的比例（目標 100%，缺的逐筆列出並在 packet 以警告現形）」；旗標名 `sub_language_in_quote`，不叫 `unsupported` |
| why | 新資料才是機制在工作的證據（L14-1）；字表只給檢查器讀，prompts／skills 不得引用（L19） |
| impact | `config/substitutability_language.json`（新）、`query/sub_language.py`（新 owner）、結構表／走圖 artifact、packet 警告、健康審查／心跳 |

**A4｜兩個旁支併入 Phase 4；SourceDoc 修法改「資料對齊」**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 旁支「本機 Research Action apply 入口」○；「重載會洗掉 SourceDoc 的分段標籤與標題」○（①`coalesce`，動 contract 先提案） |
| 新觀察 | apply 前不存在 go 收據（bare go 被拒、`complete-ra` 在 apply 後）；`coalesce` 只救增量重載，全量重建 10 份 section 仍消失（不在可重建輸入，L10）、title first-wins 因檔名排序仍錯 |
| proposed change | 併入 Step 4.2：apply 入口＝`scripts/apply_ra_admission.py --pq2 N --digest …`，驗 ①未結案 `ra_admission` ②`ref_id==action_id` ③digest==凍結 digest ④紀錄 ready 且未過期（drop 永久拒絕），通過後先把 `approval={pq2_n, digest, at}` 寫進 action 紀錄 `execution` 再 apply；不 publish、不 resolve；`complete-ra` 加比對 `approval.pq2_n==n`；授權載體仍是對話中的明確核准（AGENTS「使用者主動指示＝已授權」）。SourceDoc：以一次性 migrate 腳本把 10 份 section 寫回抽取 JSON（base 與 addendum 同值；`nvidia_photonics_pr_2025_03_18` 沒有抽取檔→補建或登記不可重建）、21 對 addendum 的 `source_doc.title` 改回母文件標題；loader 契約不動；常駐計數器改「圖上 section／title 與抽取 JSON 不一致的份數」10 → 0 |
| why | 資料對齊輸入、不另做邏輯（使用者 09-30 的原則）；入口是 packet 核對唯一能掛收據的地方 |
| impact | `scripts/apply_ra_admission.py`（新）、`intake/application.py`、`engine_b/todo.py`、`extractions/*.json`（21＋9 份）、`loader/`、`query/health_audit.py`、`audit/checks.py`、三個活文件 |

**A5｜「做什麼」欄用語同步（不改定義）**

| 欄 | 內容 |
|---|---|
| 原 roadmap | 「走圖的『單供應商但繞不過』問句餵 lead-intake 當研究題；`substitutability` 的 `auto` 投影補可稽核性（逐字必含可替代性語言，否則標 `unsupported`）」 |
| 新觀察 | §0.7 C1、C6 |
| proposed change | 改寫為「走圖第 2 型以現行層讀圖為記憶（有讀圖不再問）、研究啟動時鑄 lead（source=`graph_walk:<type>`）以 lead-intake 紀律追到終局；每筆帶 `substitutability` 的 assertion 以 repo 內字表逐字核對、標 `sub_language_in_quote`，住結構表與常駐計數器，消費端是否忽略留結案決定；origin 解析一個 owner＋`config/publishers.json`（只有自產資料的 kind 算印證）；名冊 `display_name` 補齊 100/100、加 `name_aliases`／`execution_symbol`」 |
| why | L19：手段句被當目標 |
| impact | 只改 ROADMAP 那一欄 |

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者已核准的 PLAN_PROPOSAL**（§0.1 兩張表）。`AGENTS.md`「常規推進授權」照用：
Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step**，做到 Phase 4 結案為止。只有六條停止條件之一成立才停。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（#12）**：預定三處——**R2-a**（4.2 之後：packet／loader contract＋apply 入口＋抽取 JSON 回填）、
**R2-b**（4.1 之後：名冊兩個新欄＋enrichment 去除＋origin 解析修正；驗收含 pq1 排序逐位比對）、**R2-c**（4.6 之後：Engine C `METRICS` CHECK 遷移＋稀釋燈，financial units／destructive write）；
其他 Step 若命中 trigger 同樣直接發 `WORK_REQUEST`。NO_GO → `AWAITING_HUMAN`。evidence 分類變更（4.1 B、4.3 publishers）不開 R2，以結案印「class 變動邊數＋因此 stale 的讀圖數」當驗收（§0.7 Q12）。

**停點：** 無其他預定停點。4.8 由強模型做（#11）。4.8 會鑄 pq2 `ra_admission`（AMAT 拆節點、COHR 六吋接 AXT 8-K、cw_dfb 若找到層文件）——**掛號後在 HUMAN SUMMARY 列出，接著做下一件，不停在編號上等**；go 之後的 apply 走 4.2 的入口。

**每個 Step 一個 commit（大的 Step 可拆，進度表在最後一個 commit 才 ○→✅），訊息第一行寫 Step 編號；Step 為 GO 就 push。**
新 session 先看下面進度表與 `git log --oneline -20`，從第一個未 ✅ 的 Step 接續。

**同一 working tree 只讓一個 writer：** `StockBotv2-Daily`（台北 05:30）是唯一排程。4.6（daily 增量跟新 metric）與 4.4（materialize 新計數器）的 commit **不得跨越 05:30 還沒 push**；4.6 的 SQLite 遷移不得與 daily 同時跑；4.8 寫 `library/`（lead、讀圖、敘事、event_watches）前取得互動 writer lock（`scripts/writer_guard.py`）；R2 進行中不在主樹跑變異測試（Phase 3 偏差 #40、#41）。

| Step | 內容 | 狀態 | 執行者 | commit |
|---|---|---|---|---|
| 4.0 | 基準快照（`docs/reports/2026-10-01-phase4-baseline.md`；凍結集合 `config/graph_baselines.json`） | ✅ | 執行模型 | 見 git log「Step 4.0」 |
| 4.1 | 名冊與 origin 解析：Q8b-B → 名字比對函式 → `display_name` 100/100＋`name_aliases`＋`execution_symbol` → `_strip_annotation`／`_origin_mentions` 修 → enrichment 去除（R2-b：GO，non-blocking 處置見 §0.6 #5） | ✅ | 執行模型 | `09f192c`、`bae6870`＋收尾（見 git log「Step 4.1」） |
| 4.2 | contract 批：packet `layer_enumerations`＋揭露；`source_type`／`origin_linkage`／`origin_role` 字彙；apply 入口；抽取 JSON section／title 回填＋`is_legit_multi_section` 共用（R2-a：GO，non-blocking 處置見 §0.6 #9） | ✅ | 執行模型 | `a27036a`＋R2-a 收尾（見 git log「Step 4.2」） |
| 4.3 | `config/publishers.json`＋`resolve_origin` 唯一 owner（`classify_evidence`／`verify_citations` 共用；偏差見 §0.6 #10） | ✅ | 執行模型 | 見 git log「Step 4.3」 |
| 4.4 | 字表、`sub_language_in_quote`、三個常駐計數器（①②③）＋附屬計數器；走圖／結構表 artifact、心跳段 3、packet 警告（偏差見 §0.6 #11；基準見 baseline 報告 §21） | ✅ | 執行模型 | 見 git log「Step 4.4」 |
| 4.5 | 走圖第 2 型記憶與終局；三個 skill 改寫＋`source_routes.json` 層文件 route＋skill 測試（偏差見 §0.6 #12） | ✅ | 執行模型 | 見 git log「Step 4.5」 |
| 4.6 | 稀釋燈（`StockIssuedDuringPeriodValueNewIssues`）＋Engine C `METRICS` CHECK 遷移＋串接點合一（R2-c：GO，non-blocking 處置見 §0.6 #14；正式庫遷移＋回填 2026-10-01 23:25 經使用者授權完成，結果與副本相同——baseline 報告 §22） | ✅ | 執行模型 | `da789e4`、`4eac6c9`（見 git log「Step 4.6」） |
| 4.7 | 四個小修：240 條退役不印；`ignored` 接 held_index／心跳；百分位覆蓋率；同敘事重複反證拒收（偏差見 §0.6 #15；驗收見 baseline 報告 §23） | ✅ | 執行模型 | 見 git log「Step 4.7」 |
| 4.8 | 研究（強模型）：inp_substrate 資料工後重量；cw_dfb 層文件與誠實終局；AMAT／COHR 兩筆 lead 到終局（RA）；stale 讀圖與 SIVE.ST 敘事處置——**四件掛 pq2 等 go：[664]／[665]／[666]／[668]**；讀圖與敘事已寫入（收據 `docs/reports/2026-10-01-phase4-step48-research.md`；偏差見 §0.6 #16） | ✅ | **強模型** | 見 git log「Step 4.8」 |
| 4.9 | 新管線 full chain 測試（層文件 packet → apply 入口 → 計數器動；`tests/test_layer_document_full_chain.py` 4 條） | ✅ | 執行模型 | 見 git log「Step 4.9」 |
| 結案 | completion gate ＋ closeout ＋ R2 ＋ ROADMAP ✅——使用者 2026-10-02「664 665 666 668 663 go」：[663]／[664]／[665]／[668] 入圖完成，計數器照預期（① 75→73、② 5→6、第 2 型命中 2→0）；**[666] 被 Neo4j 權限擋下（`origin_linkage` 屬性名沒有 token），圖未動、等使用者決定**（偏差 #17、§14 #26）；closeout `docs/reports/2026-10-02-phase4-closeout.md`；結案 R2：CONDITIONAL_GO（blocking 0；C1–C3 只改文件，已修；non-blocking 登記 §14 #29–#34）→ 條件修正後覆核 | ○ | 執行模型 | `081f8c6`、`abb0105`＋closeout（見 git log「Phase 4 結案」） |

**開工／續工指令：貼 `/phase-run` 即可**（不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-10-01-001-feat-phase4-layer-centric-sources-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。沒有需要我核准的事就一直做到 Phase 4 結案；撞到六條停止條件才停（R2-a／b／c 已常規 opt-in，見 §0.5）。
Step 4.8 是研究步驟：執行者是強模型就直接做。每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0.6 執行偏差紀錄（執行者填；每筆寫「plan 原文怎麼寫／實際怎麼做／為什麼」，並回頭修本 plan 對應段落）

| # | Step | plan 原文 | 實際 | 為什麼 |
|---|---|---|---|---|
| 1 | 4.0（影響 4.2d、4.9、R2-a、結案 R2） | 4.2d 的新 apply 入口指定了一個與 Phase 2 退役的遠端寫入工具**同名**的檔名 | 改名 `scripts/apply_ra_admission.py`（「套用已核准的 pq2 `ra_admission`」）；本 plan 9 處同步改 | 殭屍 grep I 組以整詞比對那個工具名，plan 檔本身因此命中 9 處、驗收段「未列 1」；I 組 keep-list 只收 `historical_record`，一支新腳本不能列進去。不可越線 11「不得出現殭屍 grep 九組的新命中」——改名是唯一合規的路 |
| 2 | 4.0（影響 4.2e） | 「`nvidia_photonics_pr_2025_03_18` 沒有抽取檔→補建或登記不可重建」；計數器「10＋21 → 0」 | 該 doc_id 有兩份抽取檔（`nvidia_photonics_ecosystem_pr_2025_03_18.json`、`nvidia_photonics_pr_2025_03_18_fabrinet_addendum.json`——檔名不等於 doc_id），直接寫回；計數器基準 section 11（只在圖上 10＋兩份 JSON 互異 1）＋title 19 | 4.0 實測（baseline §15、§19）：原量測以檔名找抽取檔；title 21 是「多檔 doc_id」數，其中 2 個標題本來一致 |
| 4 | 4.1c | 「`display_name` 100/100」；§0.2 模擬「16 條升 counterparty_joint、9 條降 self_reported」 | **99/100**：`co:nava_thailand` 刻意不補（唯一來源是 Lumentum 逐字稿摘要的「Thailand (Nava)」「Nava (Thailand)」，看不出是代工廠還是 Lumentum 泰國廠所在地，名冊 `_note` 記理由、測試把它列為唯一允許的缺口）；真實圖 class 變動 a 0／b 5／c 16 條（c：10 條聯合公告升 counterparty_joint、Hexagon／Nidec 自家文件 2 條改判自報、JL MAG 年報 2 條改判自報·filing、Hexagon 說 Schaeffler 供貨給它 2 條升外部印證），Sivers 自家 PR 0 條升級、`co:apollo` 假陽性 0、stale 讀圖 0 | 不可越線 12「display_name 只填 mechanical 來源、不從 slug 推名」——沒有來源的名字補了就是編的；模擬是在 4.1a 之前跑的，a 先做之後 Sivers 自家 PR 不再升級，正是 §13 第一條「順序是硬的」要的效果 |
| 5 | 4.1 R2-b | （覆核 GO、blocking 0、non-blocking 12） | 當下處置：①名冊補 16 家品牌短名（Sivers、POET、MACOM、Lynas、Himax、FOCI、Aehr、Cadence、GXO、Aeva、Niron、Enablence、WIN Semiconductor、Tower、Meta、Agility——對全部引文與 origin 試算，命中逐筆都指那家）；②Casela 改逐字「Nanjing Casela Technologies Corporation, Ltd.」；③Leaderdrive 出處改上交所；④基準報告補 drain 指紋算法。evidence 分布不因此改變（相對 4.0 仍是 21 條）。轉給 4.3：`_origin_mentions` 讀含括號註解的原始 origin（否定語境「非 Schaeffler」被算成具名、Evertiq 轉載的聯合稿完全由註解驅動）、Sivers×SemiNex 只掛在一方網站的聯合稿算不算自家稿、`loader/validate.py::_core_tokens` 的去留；記入 §14：中日韓字整串與單字別名的潛在誤中（今天 0 筆） | 4.2a 的層列舉核對以名冊名字為準，短名缺會把正常 packet 誤拒——必須在 4.2a 上線前補；其餘屬 origin 解析唯一 owner 的範圍 |
| 6 | 4.2e | 常駐計數器「圖上 section／title 與抽取 JSON 不一致的份數」10＋21 → 0 | 計數器分兩個方向（`loader/sourcedoc_sync.py` 唯一算法）：**重建會遺失或不確定**（圖上有值 JSON 沒有、或同 doc_id 多份 JSON 互異）＝健康審查紅／audit FAIL；**圖落後 JSON**＝黃／只列。回填後前者 30 → 0、後者 0 → 11（圖上仍掛 addendum 標題）；圖那一側經 pq2 [663] 核准後由同一支工具 `--apply-graph` 對齊（本 Step 不寫 Neo4j）。改到的 9 份綁 graph completion 收據的抽取檔，先把舊版歸檔到 `extractions/superseded/`（更正走廊的規矩），收據不改寫 | L12：「不一致」承載兩種語意——只存在圖上的值重建就消失（資料損失），圖落後 JSON 重載就對齊；後者算 FAIL 會讓 audit 在等核准期間恆紅。收據那層 plan 沒寫到，是 L11-6 ④ 查出：直接改 JSON 會讓日後走更正走廊時找不到舊版而被擋 |
| 7 | 4.2d | `scripts/apply_ra_admission.py --pq2 N --digest … [--leads …]`；第四道「紀錄 ready 且未過期」 | 沒有 `--leads`（apply 的 lead 同步沿用預設路徑）、多 `--pool`／`--root` 兩個測試用選項；同一個編號、同一個 digest 已蓋過戳記而中斷在 partial／applying 的紀錄也放行（重試） | apply 中斷時使用者要能用同一個核准重試，否則「只收 ready」會把唯一的重試路徑擋死；換編號仍拒絕（同一筆紀錄不能被兩個編號核准） |
| 8 | 4.2e | `python -m audit invariants` 13 項 | 14 項（新增 `SourceDocSync`，INV-6） | plan §12 第 2 項「含新計數器」 |
| 13 | 4.6 | ①「trailing 一年」；②「Q4＝FY−9M 衍生照營收規則」；③真實資料逐檔驗收（隱含在正式庫）；④稽核欄 `proceeds_equity`「有餘裕才加，否則列 §14」；⑤燈的稽核欄（未指定欄位名） | ①**最近四季**＝期末落在（窗尾 − 320 天, 窗尾］的季度（`engine_c/checklist.py::_FOUR_QUARTERS_DAYS`）；窗尾只取期末精確的指標（季度流量＋資產負債表時點值，不取封面日）；②多一條衍生路：沒有 9M 時前三季單季齊全 →「年度 − 三季之和」（營收／營業利益走同一條，真實資料新增 0 列）；湊不齊**不補 0**——讀取端把「期末落在窗內、季度加總不到年度」的差額列進 `unattributed`，已知季度為 0 時燈判灰（`insufficient_evidence`）、不判綠；讀取端另分「CHECK 未遷移」「遷移後未回填」兩種 `upstream_unavailable`，不說成 `provider_missing`；③**正式庫 `--apply` 被執行環境權限檢查擋下**：改以 `?mode=ro`＋backup API 的副本跑遷移、兩輪非增量回填與逐檔燈色（baseline 報告 §22），**正式庫遷移留給使用者**——2026-10-01 23:25 使用者授權後完成，結果與副本相同（baseline 報告 §22）；④延後，§14 #19；⑤欄位名 `shares_note` → `outstanding_note`、拿掉與 `source` 重複的 `shares_source`；順手修 HEAD 既有的 `colour_available_on` 遇 2 月 29 日丟例外（改成 +365 天，與判定窗滿的尺相同） | ①365 天在 52／53 週制多加一季（正式庫 16 檔國內申報人是 52／53 週制；LITE 四季前那季期末離窗尾 364 天）；相鄰季度期末相距 80–100 天（同 `alpha/three_questions._QUARTER_GAP`），三季前最遠 300 天、四季前最近 320 天；封面日比期末晚 20–75 天，會讓年度列永遠對不上窗尾；②MRVL 四個會計年度、IREN FY2025 只有單季沒有 9M——只認 FY−9M 會漏一季；NVDA FY2024 年度 4.03 億、當年三份 10-Q 都沒有這個 tag（之後幾年同一行每季都有）——缺席不等於 0；AXTI FY2025 9355 萬三份 10-Q 都沒有 → 只能列為歸不到季；③不繞過權限檢查；副本與正式庫同一批資料、同一段程式；④本 Step 的餘裕用在①②（兩個真實資料推翻的缺口）；⑤`tests/test_full_chain_acceptance.py` 禁黑箱輸出欄位名含 `shares`（`alpha.contracts.FORBIDDEN_POSITION_TOKENS`）；L17：十行內、不動 contract，當下修 |
| 14 | 4.6 R2-c | （覆核 GO、blocking 0、non-blocking 7；8 條宣稱全部驗證成立，副本真實資料 0 檔判錯） | 當下處置：#1 判色改看**窗內任一筆 > 0**（`issued_total`；淨加總只印），負的衍生季與「年度 < 已知季度加總」列 `inconsistent`、窗內沒有正值時判灰，負的衍生季不算進 `unattributed` 的「已知」；#2 期間不是季／半年／9 個月／年的 fact 進拒寫清單（`kind=irregular_period`）、summary 另計 `irregular_period_facts`，`provider_missing` 理由改成「沒有可存成季度或年度的」——讀取端要能改判 `insufficient_evidence` 需要逐檔持久紀錄，記 §14 #23；#3 逐檔「遷移後還沒重抓」同樣需要持久紀錄 → §14 #23，OPERATIONS 補「遷移後立刻跑非增量回填、看逐檔 outcome」；#4 遷移前比對 `PRAGMA table_info` 欄名＝14 欄（不同就拒絕，不丟欄）、`--db` 不存在直接 exit 2（不建空檔）、dry-run 的 `MigrationError` 接住、使用者已持有同 owner 的鎖時不續期不釋放；#5 窗尾先取季度流量、沒有才退到時點值；#6a **前提覆蓋率口徑**：plan §1 第 10 項「有這個 tag」28／35 字面上過 ≥20，但照實作口徑（5 年窗內有可存的季／年 fact）只有 16／35、最近 400 天 12——HUMAN SUMMARY 點名交使用者判斷，不自行停或換指標；#6b 規則文字改成「companyfacts 分不出普通股或特別股，accession 指得回原文」（原句「tag 印出來可改判」說過頭）；#6c 指標拆 `_quarter`／`_annual`（照營收慣例）、單位照存（XPEV 1 列 CNY，外國申報人不判色）；#6d `basis=annual` 時 `quarters_found` 印 None、授權取每個 as_of 的生效紀錄；#7 → §14 #24。新測試 7 條＋1 條（變異檢查抓到「只有前後不一」那條路沒被單獨守住）；9 個變異全紅 | 都在十行級、不動 contract（L17）；#1 是唯一可能讓燈誤判綠的路，今天副本 0 檔中但兩種負值來源都有真實前例；#2／#3 的正解要新增「每檔每次抓取」的持久紀錄（新表），是 contract 變更 |
| 15 | 4.7 | a「`contracts.py:408` 的 `disproofs` 欄退役或留空（二擇一寫八欄）」；b「新讀者（`portfolio/holdings.py` 或 `alpha/candidates.py`）」「心跳『持股解析不到 N（使用者決定不研究 M）』」；c「CLI `render.py:384-401` 印 samples／覆蓋率」；d「`v2_write_problems` 加：本版 disproof[] 內 normalize(condition) 相同 → 拒收並印是第幾條」 | a①**退役**（不留空）；②空面板理由改「還沒有任何**登記的**反證」；③analyst-view CLI 5.4 改指向「錯了怎麼知道」面板；④read model 的 `falsification.conditions` 不動、alpha-card CLI 第 11 節照舊印；b①讀者 `portfolio/holdings.py::load_ignored`（讀不到、版本不對或任何一筆形狀不對 → 整份不採用、全部照列解析不到），`held_index` 只把「本來會解析不到」的列移到 `ignored[]`（解析得到的照算已持有）；②心跳那行改成常駐計數器——0 也印、舊 artifact 沒有那一欄印「未讀到」；③APP 候選板頁首另列名單、理由、決定日；④OPERATIONS 那段原本指向 Phase 0 已退役的讀者，改寫成現況；c①CLI 是 `briefing/analyst_view/render.py` 三題稽核行；②覆蓋率兩位小數、規則文字補「只印、不設門檻」；d 訊息「disproof[N]：與 disproof[M] 是同一個條件（正規化後相同）」，放在既有的反證迴圈裡 | a①一個結構上恆空的欄位就是靜默缺席（L12），而 APP／CLI 都要另寫「沒有」的分支；②舊判讀的文字仍在判斷檔裡，說「沒有任何反證」是過度主張（L11-5）；③原句「這一格空著就等於沒有出場條件」在退役後對已登記反證的檔是錯的；④builder 另有兩處讀它（風險摘要句、condition_count），在來源退役會超出 plan 點名的範圍——對稱面記 §14 #25；b①fail safe 寧可多問一次，不可把該問的藏起來；②L14：會自己出現的計數器，不是要人記得的段落；④那段描述的讀者已不存在，留著會讓下一個讀者以為名單有人在讀；c plan 寫的行號是 plan 撰寫當下的；d 判準同 `register-disproof` 的去重（`engine_b.disproof.normalize`），只比本版、跨公司不比 |
| 16 | 4.8 | ①AMAT／COHR「RA → pq2 → apply」；②cw_dfb「找到 → packet 帶 `layer_enumerations` → pq2」；③AMAT「把 GF 的需求邊改指更細節點（`tech:deposition_etch_clean` 等）並補 LRCX／TEL／ASML 的供貨邊，或拆節點」；④cw_dfb 的 lead「source=`graph_walk:thin_layer_unread` 或使用者點名」 | ①AMAT、COHR 走 `loader/migrate_relation_rejudge.py --additions`（manual pq2 [665]／[664]；同一份文件既有逐字、不新增）；②cw_dfb 走 RA [668]（更正走廊＋`layer_enumerations`）——先掛的 additions [667] 與 packet 印錯的 [669] 都是本 session 自己撤回（使用者未看過）；③只補 Lam（名冊有）；TEL／ASML／KLA 不在名冊，GF 20-F 全文沒有具名任何設備商，GF 那句講的就是泛稱設備——不拆節點、不改指；④來源寫 `directed:phase4-plan-4.8`（cw_dfb 已有讀圖，不是第 1 型命中）；⑤途中當下修兩個機制缺口：走圖第 2 型記憶漏 `action_prepared`（`OPEN_LEAD_STATUSES`）、packet 層列舉的 origin 解析沒走 4.3 的 owner（GSR 印成「解析不到」） | ①「同一份文件的同一段逐字也支持另一條邊」正是 additions 的設計用途（前例 [651]／[652]）；改走 RA 要多一份抽取檔版本，資訊不多一個字；②結案驗收要「applied RA 帶 `layer_enumerations`、apply 入口戳記」——只有 RA 路徑給得出；③沒有客戶端列舉、名冊外的公司要先 onboard；④不把非命中寫成命中（L12）；⑤L17、L16 |
| 17 | 結案 | 「go 之後依序：[664]／[665] 照各自 hint 跑 `loader/migrate_relation_rejudge.py --additions … --backup-dir …`；[666]／[668] 跑 `scripts/apply_ra_admission.py` → publish → `complete-ra`」 | ①[664]／[665] 的 live 遷移要求 backup-dir 內**事先**有非空 `neo4j_export.json`（hint 沒寫這一步）：以 `scripts/backup_private.py` 既有的 `export_neo4j_payload`／`verify_neo4j_export` 現做（與 `migrate_611`–`615` 同形）後照跑；[663]／[664]／[665] 的抽取檔與收據先自成一個 commit（`081f8c6`）並 push，否則 `commit_pending_intake` 以 `unexplained_ahead_commit` 拒絕 publish [668]。②[666] 入口蓋了戳記、apply 時 Neo4j `Forbidden`（`routine_writer` 沒有 `CREATE NEW PROPERTY NAME`；`origin_linkage` 從沒建過 token）——圖未動、RA `partial`；依既有規範以 admin 執行 setup 1b 預熱（token 已建、routine 權限 0 變動），用原編號重試時被執行環境的權限分類器以「Security Weaken」拒絕，**不繞過、留使用者決定**；對應的程式修正（預熱清單＋對稱測試）停放 `git stash`、不 commit。③[668]：`complete-ra` 自己記帳把 lead 推到 applied（不必先手動 advance） | ①遷移工具的前置條件寫在 docstring 不在 hint——L13（產出要出現在下游）；②4.2 加 `origin_linkage` 時漏了「新增 SourceDoc 欄位後預熱 token」這條要人記得的規範，4.9 用 fake loader、R2-a 只在夾具上跑，所以第一份非 null 的真實 apply 才撞到；分類器拒絕＝使用者的決定點（不可越線 13）；結案驗收不依賴 [666]（它不動 ②，baseline §21） |
| 3 | 4.0 | 「凍結節點集合」「凍結的 assertion id 集合」存檔，未指定位置 | `config/graph_baselines.json` 的 `baselines.phase4_2026_10_01`（tracked、append-only、**只放 id 不放引文**；`.gitignore` 補白名單） | 4.4 的常駐計數器每天要對它算，scratchpad 只活一個 session；這份集合今天重取拿不回來（L10）；部分抽取檔受儲存權限限制不進 Git，所以引文全文只留 scratchpad |
| 9 | 4.2 R2-a | （覆核 GO、blocking 0、non-blocking 8＋既有問題 1） | 當下處置 8 條：N1 名冊寫法全部與另一家共用（今天只有 OpenLight 兩個 id）→ 新狀態 `registry_names_shared`，列前置、不拒收（原本被當成「引文沒具名」拒收）；N2 蓋戳記在鎖內重查戳記（兩個未結編號同時跑，後到的不覆蓋）；N3 OPERATIONS 第 5 步改寫成實際跑過的那一次、repo 內串成一條的測試待 4.9；N4 讀**已存紀錄**時層列舉只驗形狀、不依賴當下字彙檔（對稱面：`focus_company_id` 也不再依賴當下名冊）；N5 沒戳記的舊 partial 拒絕訊息改說「重跑 prepare」；N6 `--apply-graph` 寫圖前核對編號（存在未結、`manual`、ref_id 以 `sourcedoc-title-sync:` 開頭；真實 [663] 通過、[662] 被擋）；N7 SourceDoc 計數器的紅燈判準收成一個 `is_red`：圖上有、沒有任何抽取檔與讀不了的抽取檔也算紅、而且計數（今天兩者 0、audit 照舊 PASS）；N8 apply 報告與 packet 共用同一個「發文者」行。新測試 7 條。既有問題（三張收據對不上任何現存或歸檔的抽取檔）記入 §14 #14 | 都在 10 行級、不動 contract（L17：當下修）；N1 會在 4.8／4.9 用到層 packet 之前誤拒，N6 守的正是 [663] 要走的那條寫圖路 |
| 10 | 4.3 | 每筆 `{origin, kind, corroborates, note}`；「media 文要升級須該 SourceDoc `origin_linkage=independent` 且仍不得是 same_origin」；消費端 `classify_evidence`／`verify_citations` | ①每筆多 `seen_in`（讓它被登記的那份 SourceDoc；載入時必填），測試用它核對拼字——10 份私有抽取檔不在 checkout 時該筆 skip（pytest 摘要計數）。②`CanonicalEdge` 加 `origin_linkages`（origin → 引用這條邊、出自該 origin 的各份文件的宣告集合），不是一個 independent 集合；**宣告 `same_origin` 的文件不論類別都不算印證**（研究機構轉述供應商新聞稿也是轉述）。③同級時 needs_review 勝 media_relay（還有沒認出來的來源）。④同一個 owner 另有兩個消費端：插槽視角的「可解析第三方原文」、`scripts/audit_sole_source_independence.py`（逐個 origin 走 owner，聚合規則不變）。⑤登記 34 筆＝4.1 後剩下的 50 個去註解字串中的 34 個，其餘 16 個刻意不登記（設定檔 `_not_registered` 逐類寫理由） | ①打錯字的登記會永遠比不到、而且是靜默的（那幾條邊一直待判定），驗它需要指得回一份文件（L18）；②同一家媒體的兩份文件可能一份自己採訪、一份轉述，只記布林會讓轉述搭便車；`same_origin` 是那份文件自己的宣告，忽略它違反 L12「任何會改變輸出的輸入都要出現在證據裡」，今天 0 份文件有宣告、影響 0 條邊；③結果不得隨迭代順序翻；④插槽視角的「客戶端或可解析第三方原文」與讀圖 independent 核對是同一個問題，兩處判準不同讀者會看到矛盾（L16）；⑤未登記＝不猜 |
| 11 | 4.4 | a「prompts/、skills/ 的任何檔不得引用該檔名或**逐字含 ≥5 個 terms**」；c「住 `materialize_graph_walk` 新增一段 `layer_stats`（或獨立 kind，二擇一）」；b 旗標「`fetch_all_quotes(driver)`」 | ①L19 測試改成「不得引用檔名」＋「**任何一行**不得同時含 ≥5 個不同的詞」（門檻數字照 plan）；②`layer_stats` 是 `graph_walk` artifact 的一段（不是新 kind），算在 `query.graph_walk.collect()` 那一次連線裡（純函式 `query/layer_stats.py`），artifact schema 升 `graph_walk/2`，心跳段 3 與結構表頁首讀 `layer_stats.summary` 同一行字；③`fetch_assertions` 多回 `e.id AS assertion_id`（不碰 QUOTES join，`documents` 計數不變）；④packet 警告存成紀錄的收據 `sub_language_check`（同層列舉的規矩：依賴當下字表，只在 prepare 跑一次），packet 與 apply 報告共用同一節；⑤②的「非供應商 origin」＝解析成發布者（媒體也算——列舉是列舉，證據強弱另由 evidence 欄說）或名冊公司但不是這一層的供應商；解析不到的不算、另計數；②對**現在**圖上的層節點算、①對凍結集合算；⑥名字比對唯一 owner `quote_names_company` 多一個選填 `shared`（大量比對時不必每次重算共用寫法） | ①整檔計數在今天的檔上就紅：`prompts/extract_system.md` 本來就含 11 個通用詞（replace、qualification…），skills 各 3–6 個——那是抽取規則本身的用詞，不是字表外洩；每行最多 3 個（docs 最多 4），抄進來的字表一定擠在一行；偵測器本身也有測試（把字表前 5 個詞排成一行會被抓到）；②新 kind 要動 STATE_KINDS／_STATE_NOTES／_STATE_FLAGS 三處卻沒有新讀者，計數器的輸入（邊、讀圖、逐字）本來就在走圖那次連線裡；③④⑤⑥見各自註解 |
| 12 | 4.5 | a「refs 帶 `graph_walk_subject==node`」（沒寫怎麼寫進去）；b「選填 `--classified-by`」「心跳與 `queue_segments` 把非 triage_semantic_v1 的分開計」；c source-trace「在分流表之後加一節」；company-onboard 改 Step 1／2／3／4b／4d／5 | ①`config/lead_ref_keys.json` 新分類 `graph_walk`（`graph_walk_subject`、`graph_walk_as_of`——不可越線 5 要的「refs 帶走圖命中的 as_of」），鑄號路多一步 `annotate`；②`classified_by` 是封閉字彙 `{triage_semantic_v1, interactive:graph_walk}`（argparse 與函式兩層拒收）；心跳「分類層上次成功」不算互動 triage、另印「互動 triage N 則」，pq1 行印「其中互動起的研究 lead N」；`queue_segments.observe` 多 `triaged_go_by_classifier`（分開計，不從 triaged_go_leads 扣掉——它們仍是研究工作）；③層文件節放在「### 2. 依序嘗試四條路徑」之後、「### 3. access boundary」之前（`### 2b`）；④company-onboard 另把 origin_entity 範例表的泛稱 `Third-party Research` 改成「寫真正的發布者」、Step 5 的 Lane Memo 份數檢查換成 `query.structure`／`query.graph_walk` 的入圖後驗收；⑤`extract.py` 與 `scripts/apply_ra_admission.py` 把 CLI 定義抽成 `build_parser()`（行為不變），skill 測試拿真 parser 解析每一行指令；⑥`layer_document` rung 2、verified=true（GSR／Cignal AI 兩份實例）；⑦plan 預期「`missing_rungs` 對舊 parked lead 會多報一條」——實際 0 筆：收據是 park 當下產生的字串、不重算，只有之後新 park 的「未走」多一格 | ①走圖旁印 open_lead 要有一欄可以對；②有行為後果的字彙要強制（L16）；③plan 同時要求「transcript 那句仍在層文件節之前」——放在分流表後面會排到它前面；④那條範例正是 §14 #16（31 條邊卡在待判定）的來源，改 skill 的同一個 change 不修就是讓它繼續長；Lane Memo 的「N/3」正是 plan 要拿掉的份數門檻；⑤字串比對驗不出旗標漂移；⑦L11-6：先看產生收據的那一行 |

## 0.7 反方驗證處置（2026-10-01；逐條原文在 workflow journal `wf_b64373a7-a95`，此處只列處置）

- **成立且已改進本 plan 的（覆核者＝plan 作者，逐條對照程式碼）：** Q1（層文件不當 claim 路由頂階；`source_routes.json` 要登記；company-onboard Step 4d 直接 load 是繞過 gate 的路；Step 3「N/3」門檻句）→ §6；Q2（`report` 是 exact fields、139 筆舊紀錄；prepare 不開 Neo4j；`develops` 也是供應關係；子字串誤拒、`_core_tokens` 既有；四份 `source_type` 副本；datasheet＝供應商自報）→ §3；Q3（第二個狀態源；狀態機無自動結案；`parked→pending` 清 triage；`wake_lead` 到期是終局；`classified_by` 一欄兩義；第 5 型母體污染；materialize 不是 Engine B writer）→ C1、§6；Q4（媒體轉述不得升級；origin 解析要一個 owner；`display_name` 補齊 16 條邊變、1 條假陽性、9 條降級；順序 B→display_name→publishers）→ C4、§4；Q5Q6（分母 113；投影 meta 沒人讀；旗標 owner 一個；存量不會自己變；字表敏感度；`_candidate_set_hash` 風險；`documents` 計數不能混 QUOTES join）→ C6、§5；Q7（兩種供應商定義；比例分母；「逐字撐住」0/10；「≥3 家」單調上升；G4 指紋＝一份文件列舉多家；None 不壓布林）→ C5、A1、A2；Q8a（tag 實測；LITE 可轉換；CHECK 遷移；「非 SEC」措辭；absence kind；串接點兩處）→ C3、§7；Q8b（0 條命中；連鎖由 display_name 觸發；5 張表）→ C2；Q8c（保留 `get_execution_aliases()` 形狀；constructor 衝突檢查；`_YFINANCE_SYMBOL_ALIASES`；`sheet_company_id` 失去 producer；pq1 逐位比對）→ §2；Q9（go 收據循環；coalesce 只救增量；title first-wins；三處判準互異；`_finalize` 刪；三個活文件）→ C7、A4；Q10（inp 已有層文件；cw_dfb 沒有；AMAT 粒度；COHR 的 AXT 8-K 在庫；驗收改圖裡的 class 分布）→ C8、§9；Q12（稀釋燈那條鏈沒有歸處；鑄 lead 改為 sandbox review＋idempotency；evidence 變更不開 R2）→ §0.5。
- **反方之間不一致、由作者裁定的：** ①Q3 的「要不要新 trace_status 字彙（`resolved_by_graph`／`node_too_coarse`／`superseded_by_graph`）」——三位各提一個；裁定**不加**（L17：lead 只在互動研究啟動時鑄，終局是 RA applied 或 park 既有字彙 `awaiting_named_disclosure`／`not_pursued`，「節點太粗」的修法本身就是一份 RA）。②Q4 的 publishers 以 `publisher` 欄還是 origin 字串為鍵——裁定以 **`_strip_annotation` 後的 origin 字串**為鍵（`classify_evidence` 解析的是它；`publisher` 欄 42 份為 null），並在 Step 4.0 列出 59 個未解析字串逐條標 kind。③Q7 ②的「≥2 家」還是「≥3 家」——裁定 ≥2（G4 的指紋是「列舉集合」，≥3 另印母體）。④Q12 四處還是三處——裁定三處（Q3 改後 daily 沒有新 writer；evidence 變更是 A3 可重算）。
- **反方提出但本 Phase 刻意不採的：** 「外部印證要求引文具名供應商」（改判準，先只量，§14）；`origin_linkage` 之外另加 `same_origin` 偵測（先靠宣告）；名冊 `yfinance_symbol` 欄（註明即可）；proceeds 兩個 tag 當觸發（只當稽核欄）。
- **未完成的覆核：** 第二層 25 位覆核者與補漏者因額度未跑；作者自查補漏：lead `published_at`（C1 後只剩互動鑄號，沿前例可為 null）、`origin_role` 字彙住 `schema/vocab.json`、字表版本化、`layer_enumerations` 對 `prod:` 插槽節點同一套核對、publishers 由互動 session 維護且未登記＝不猜。

---

## 0. 不可越線（違反即 NO_GO）

1. **不自動入圖**：Neo4j 只由 Step 4.8 經 pq2 `ra_admission` go 後的 apply 入口寫；其他 Step 的測試一律用 fake driver 或暫存圖；**`library/resolutions/` 與 EdgeAssertion 一筆都不改**（`sub_language_in_quote` 是 derived，寫在 artifact，不改 assertion、不進 `candidates` value）。
2. **讀圖 ledger、敘事 ledger、lead registry 只由 Step 4.8（強模型）經正式入口 append**；既有行一行都不改寫。
3. **不改 sub 的任何消費端行為**；**不改分類器讓數字好看**：4.1 B 與 4.3 publishers 是使用者定案的兩處，每處結案印「因此 class 變動的邊數（逐條）與因此 stale 的讀圖 id」。
4. **走圖第 2 型的 `scope_rule` 不動**；`hit_rule` 只加「且無現行層讀圖」一句（4.5），每次母體／命中變動逐筆列原因。
5. **lead 不得由任何無人值守步驟鑄**；合成 URL 的 lead `published_at` 留 null、`first_seen` 記鑄號時間、refs 帶走圖命中的 `as_of`（INV-6、L11-5）。
6. **`library/trades/trade_log.jsonl` 與 Google Sheet 不得在測試或試跑中寫入**；`record_trade.py` 試跑一律 dry-run（不帶 `--apply`、也不帶 `--log-only`）。
7. **任何 `python -m <module>` 或 `scripts/*.py` 新入口 → sandbox impact review 五步**（ROADMAP 硬約束 10），同 commit 改測試。已知會撞：4.2（`scripts/apply_ra_admission.py`，互動專用、**不進任何無人值守 allowlist**，review 要寫明它落在 `.claude/settings.local.json` 的 `Bash(python *)` 之下、補償控制是四道檢查＋戳記）、4.4（新唯讀 CLI 若有）、4.6（daily 增量跟新 metric、遷移腳本）、4.5（`engine_b.cli triage` 若加 `--classified-by`）。
8. **每刪一個測試檔或測試函式，八欄的 Blocking findings 列出它守的是什麼、現在由誰守。** 活機制的測試不可刪斷言。
9. **每個 Step 動手前先答 L11-6 第④問：「如果這個改動是錯的，最先壞掉的是哪一筆現有資料或哪個活的呼叫端？」去看那一筆，寫進八欄。** 各 Step 已預填一個起點。
10. **不排序、不打分、不設門檻**：計數器只印不判；`publishers.json` 的 `kind` 不是等級；字表命中數不是分數；lead 只按 lead 時間。
11. **命名：** 不得出現殭屍 grep 九組的新命中；旗標叫 `sub_language_in_quote`；字表叫 `substitutability_language`；lead source 叫 `graph_walk:<type>`；名冊新欄叫 `name_aliases`（名字）與 `execution_symbol`（執行代號），**都不進 `by_ticker`**。
12. **`identity/registry.py::company_id_for_ticker` 不得放寬**（資本歸屬路徑）；`display_name` 只填 mechanical 來源（EDGAR submissions `name`／交易所公告名／年報封面），不從 slug 推名、不用 Neo4j `Company.name`（LLM 寫的，不是 authority）。
13. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。**
14. **四個人工 gate、五條 authority separation、六條 invariant 全程適用。** packet 核對、origin 解析、evidence 分類都是 A1 的機械輔助，**不授權任何入圖**（L15）。
15. **同一 working tree 只讓一個 writer**（§0.5）。

---

## 1. Step 4.0 基準快照（Z0，一個 commit）

寫 `docs/reports/2026-10-0x-phase4-baseline.md`，每項附命令與輸出摘要；**唯讀**（Neo4j READ session、Engine C `?mode=ro`、companyfacts 唯讀網路）：

1. `python -m pytest -q` 通過數；測試檔數；`def test_` 名單存檔（結案比對函式層級增刪）。`python -m audit invariants`。
2. **圖——供給側分布**：兩種口徑各印 ns=0／1／2／≥3（§1.1 Cypher；supply_side 只算 `supplies_to`，由 `query.structure.build_structure` 導出）；**凍結節點集合**（supply_side 口徑下 tech／mat／prod 節點 id 清單存檔——A1 的驗收對它算）；ns==1 的節點逐個印供貨邊的 evidence class。
3. **圖——evidence**：`_classify_edges` 對全部 canonical 邊的五級計數（536：217／113／106／100／0 預期）；每條 needs_review 邊的未解析 origin 字串；**59 個未解析 origin 字串全清單**，逐條標「名冊公司缺名／逗號註解／媒體／產業研究／政府／學術／其他」（4.1、4.3 的輸入）；每個節點的 `result_digest`；`classify_evidence` 325-330 分支命中數（0 預期）。
4. **名冊**：100 家的 `display_name` 有／無清單；`aliases`；Sivers 條目。
5. **圖——sub**：sub 非 null 的 assertion 清單（id、edge_key、值、QUOTES 引文全文）存檔（4.4 的 ③a 對它算）；`python query/edge_conflicts.py --json` 的 auto／open／empty。
6. **現行讀圖**：每份 v3 讀圖的 id、節點、單位、status（`reading_status_rows`）、供給側每條邊的 evidence class（4.1／4.3 後逐份對照）；現行 v2 敘事四份的 brief_id 與 `rides[]`；`python -m engine_b.event_watch counters`。
7. **走圖**：`python -m query.graph_walk --json` 九型命中／母體；第 2 型每筆 `subject`／`supplier`／`evidence_label`。
8. **lead**：`pending_leads.json` 的 source 前綴計數；`python -m engine_b.cli drain` 的 lead 順序（4.1 R2-b 逐位比對用）。
9. **心跳**：`python -m crons.heartbeat --out <tmp>` 全文存檔。
10. **稀釋燈**：73 檔每檔的來源、顏色、inputs；**companyfacts tag 覆蓋率**：對 35 檔 10-K／10-Q 國內申報人查 `StockIssuedDuringPeriodValueNewIssues`、`ProceedsFromIssuanceOfCommonStock`、`ProceedsFromIssuanceOrSaleOfEquity`、`StockIssuedDuringPeriodSharesStockOptionsExercised` 有／無／多單位（唯讀網路；每檔記 CIK）——4.6 的前提；filer_class 分布（domestic_quarterly 35／其餘 38）。
11. **個股頁**：73 份核心面板文字 digest（`python scripts/analyst_view_text_digest.py --per-panel`）；downside 與 research 面板 `source="judgment"` 列數（240 預期）。
12. **Sheet 持股解析**：候選板 `holdings` 逐列 resolution 路徑；FRA:2DG 今天走 `sheet_company_id`；Sheet 有沒有 `company_id` 欄（唯讀）。
13. **Engine C**：正式庫各表 `PRAGMA table_info`、`sqlite_master` 裡 `fundamental_history` 的 CHECK 原文、列數；`METRICS` 清單。
14. **RA 紀錄**：139 筆的 state 分布；池裡 `ra_admission` 137 筆 resolution 分布；7 筆 partial／expired 對應的 pq2 編號。
15. **SourceDoc**：220 份的 `source_type`／`origin_entity`／`publisher`／`section`／`title`；「section／title 與抽取 JSON 不一致」清單（10 份 section＋21 對 title 預期）；`nvidia_photonics_pr_2025_03_18` 無抽取檔確認。
16. 舊 Decision Store 三個 `*.db` 的 sha256 與 `live_choices`；`trade_log.jsonl` 行數與 sha256；`python scripts/retired_mechanism_grep.py` 九組三個 0；`python -m webapp status` kind 清單。
17. `git grep -n "_EXECUTION_ALIASES\|_TICKER_ENRICHMENT\|_TICKER_ALIASES\|_YFINANCE_SYMBOL_ALIASES\|neo4j_id"` 呼叫端清單；`git grep -n "_apply_research_action_impl\|_finalize_research_action_impl"`。
18. `config/source_routes.json` 13 條 route 與 `missing_rungs` 對今天 parked lead 的輸出（4.5 加 route 後對照）。

## 2. Step 4.1 名冊與 origin 解析（Z2，R1 ＋ R2-b 常規 opt-in）

**順序是硬的（§0.7 Q4、Q8b）：a → b → c → d → e。**

**a｜Q8b 替代案 B。** 改哪裡：`query/bottleneck.py:325-330`（刪「解析到主詞且另具名他家 → counterparty_joint」的抬升；解析到主詞一律走 `filing_origins`→`self_reported_costly`，否則 `self_reported`）；`tests/test_structure_table.py:420-426` 翻面；`CONCEPTS.md` 五級說明同步（320 分支「整串不解析且具名 ≥2 家」**保留**）。
怎麼驗：真實圖重跑 `_classify_edges`：class 變動邊數 **0**（§0.2：今天 0 份命中）、讀圖 stale 0 份；翻面測試會紅→綠。
L11-6 ④：`tests/test_structure_table.py:413-426` 的三條斷言；`alpha/narrative/argument.py` 的 key 集合測試不該變（沒加字彙）。

**b｜名字比對函式（單一 owner）。** 改哪裡：`query/bottleneck.py`（在 `_name_variants`／`_origin_mentions` 旁新增公開函式 `quote_names_company(quote, company) -> bool`：名字集合＝`display_name` 核心名＋`name_aliases`＋既有 `_core_name` 變體；**整詞比對**（word boundary；中文名用完整字串），不用 ≥4 字子字串；`_origin_mentions` 改呼叫它）；`_strip_annotation` 補逗號註解（「Sivers Semiconductors, with a named …」→「Sivers Semiconductors」）。
怎麼驗：`co:apollo` 假陽性（「Google (Apollo/Palomar 團隊自著論文)」）不再命中；逗號註解 3 份解析到 Sivers；既有 `_origin_mentions` 測試照綠；新測試：「AXT Inc.」vs 引文「AXT」命中、「NVIDIA Corporation」vs「NVIDIA AI Data Center Infrastructure」命中（`loader/validate.py:44-48` 的既有案例）、「本公司」不命中任何人。
L11-6 ④：`classify_evidence` 320 分支用 `_origin_mentions` 數具名家數——整詞化後具名數只會減不會增（列出真實資料上變動的 doc）。

**c｜名冊補齊與兩個新欄（identity contract）。** 改哪裡：`identity/registry.py::CompanyIdentity` 加選填 `name_aliases: tuple[str, ...]`（名字，含中文名、常用短名；**不進 `by_ticker`**）與 `execution_symbol: str | None`（constructor 檢查：不得等於任何公司的 research_ticker／alias／另一家的 execution_symbol，衝突即 raise）；`from_path` 逐欄解析；`config/company_identity.json`：100 家 `display_name` 補齊（來源逐筆：SEC 申報人取 EDGAR submissions `name`、台股取公開資訊觀測站公司名、其餘取交易所公告或年報封面；來源寫進 config 的 `_display_name_sources` 或 commit message）、`name_aliases` 至少補 ≥3 家供應商層裡引文用的短名與中文名（AXT、Sumitomo、JX Nippon Mining & Metals、聯亞光電、華星光…）、Sivers `execution_symbol: "FRA:2DG"`；`.gitignore` 不變（config 已 tracked）。
怎麼驗：`tests/test_config_tracking.py` 綠；registry 載入 100/100 有 `display_name`；衝突夾具 raise；`name_aliases` 不影響 `company_id_for_ticker`（既有測試逐條綠）。
**真實資料試跑（結案也要印）：** 補齊後重跑 `_classify_edges`——class 變動邊逐條列（§0.2 模擬：16 條升 counterparty_joint〔a 做完後其中 Sivers 自家 PR 的 3 條應**不再**升級——驗 a 的效果〕、9 條降 self_reported）；哪些讀圖因此 stale（預期 `prod:supernova`、`prod:els_8ch_module` 插槽 high；層讀圖 low 不進第 4 型）。
L11-6 ④：`co:apollo` 那條邊；`prod:supernova` 插槽讀圖的供給側 evidence。

**d｜enrichment 退出身分解析。** 改哪裡：`identity/execution.py`（`_EXECUTION_ALIASES` 改由 `get_registry()` 的 `execution_symbol` 派生；**保留 `get_execution_aliases()` 名稱與 `{research_ticker: execution_symbol}` 形狀**；`_YFINANCE_SYMBOL_ALIASES` 留、docstring 註明「行情供應商語法表，不是 identity」）；`fetchers/gsheets.py::_TICKER_ENRICHMENT`（拿掉 `neo4j_id` 注入；名冊可解析的列改讀 `display_name`，ETF／未入名冊的列留表並註明「只給名字、不給身分」）；`portfolio/holdings.py`／`engine_b/cli.py::_held` 不改語意；`tests/test_record_trade_receipt.py:158、485-500`（485 改成模擬 Sheet 自帶 `company_id` 欄，或若 Sheet 沒有該欄則在 `RESOLUTION_SOURCES` 註明 `sheet_company_id` 目前只有測試會走並改 docstring）；`docs/OPERATIONS.md` 持股解析段。
怎麼驗：FRA:2DG 解析走 `execution_alias`（測試）；凍結區 `decision_lab/adapters/holdings.py` **0 行 diff**；`tests/test_gsheets_snapshot.py` 綠；**pq1 排序對全部 lead 逐位比對 4.0 第 8 項**（`_held` 的 company_ids 集合可能變——列出差異）；`record_trade.py` 對 FRA:2DG dry-run 一次、trade_log sha 不變。
L11-6 ④：`engine_b/cli.py:69-94` `_held` 的 except 若吃掉例外，pq1 排序會靜默變——逐位比對就是看這個。

**e｜結案數字。** 八欄印：origin 解析 147/73 → N/M（59 字串剩幾個）、needs_review 113 → N、class 變動邊逐條、stale 讀圖 id、pq1 逐位比對結果。

**R2-b（常規 opt-in）WORK_REQUEST：**
```
WORK_REQUEST（R2-b，Phase 4 Step 4.1）
Target: 4.1 的 commit；identity/registry.py、identity/execution.py、config/company_identity.json、fetchers/gsheets.py、query/bottleneck.py、tests
Claimed acceptance: company_id_for_ticker 語意不變；name_aliases／execution_symbol 不進 by_ticker；衝突 raise；display_name 100/100 且每筆有 mechanical 來源；
                    get_execution_aliases() 形狀不變、凍結區 0 diff；FRA:2DG 走 execution_alias；pq1 排序逐位與 4.0 相同（或差異逐條解釋）；
                    Q8b-B 在真實圖 0 條邊變；display_name 補齊後 class 變動邊逐條列且 Sivers 自家 PR 的邊沒有升級
Do not trust: 上面那行是待驗證的宣稱
Task: 自己跑 identity／holdings／record_trade 測試；抽 10 家 display_name 對來源核；自造 execution_symbol 衝突夾具；重跑 _classify_edges 比對 4.0；重跑 drain 逐位比對
Boundaries: 不改 code、不 commit、不寫 Sheet、不寫 trade_log、不核准 pq2
```

## 3. Step 4.2 contract 批：packet、字彙、apply 入口、抽取 JSON 回填（Z2，R1 ＋ R2-a 常規 opt-in）

**a｜packet `layer_enumerations[]` 與揭露。** 改哪裡：`intake/actions.py`（`REQUEST_OPTIONAL_FIELDS` 加 `layer_enumerations`——**頂層選填，不進 `report`**；每項 `{node, suppliers[], relation, origin_role}`；`relation` 只收 `schema/vocab.json` 新鍵 `layer_enumeration_relations`（初值 `supplies_to`、`develops`）；`origin_role` 收 vocab 新鍵 `origin_role`（`customer_filing`／`industry_report`／`spec_or_teardown`／`supplier_self`），未登記拒收（L16）；parse 時**只核對「在本包」**：node 與每家 supplier 都在本包 nodes、每家 supplier 至少一條 supplier→node 的邊且 relation 在允許集合、該邊 `source_ids` 指到的任一 quote 以 4.1b 的 `quote_names_company` 命中 supplier；**不查 Neo4j**；核對失敗分兩種原因報（「名冊無名可比」→ 列進 packet 前置清單不 fail closed；「引文真的沒具名」→ 拒收）；`origin_role=supplier_self` 時 origin 必須解析到 suppliers 之一，`customer_filing`／`industry_report`／`spec_or_teardown` 時 origin 不得解析到 suppliers 任一（警告不拒收，印出）；`render_review_packet` 加「層列舉」一節、文件清單每行多印 origin／source_type／tier（取值與 `engine_b/todo.py::_ra_graph_impact` 同一條路、`.get` 給「未記錄」）；`_validate_record` 必要欄位集合不改，舊 139 筆 render 不變。
怎麼驗：`tests/test_research_actions.py`：含 `layer_enumerations` 的 request digest 凍結；未知 relation／origin_role 拒收；supplier 不在本包拒收；引文不具名拒收並印原因；名冊無名列前置不拒；舊紀錄 render 逐字不變（固定夾具）；`report` 多 key 仍拒收。
L11-6 ④：131 筆 pushed 紀錄的 `_validate_record` 再驗證——它是最先壞的（若欄位誤放 `report`）。

**b｜`source_type` 字彙。** 改哪裡：`schema/vocab.json` 加 `teardown`、`datasheet`；`schema/intermediate_format.schema.json` enum 同步；`extract.py:317-321` choices 改讀 vocab（刪硬編碼）、help 文字加 tier 對照（datasheet＝供應商自報 tier 同 ir_deck；teardown＝第三方 tier 2、origin_entity＝拆解方）；`tests/test_robotics_ontology.py:150-165` 改成三處相等（vocab＝schema enum＝extract choices）；`skills/lead-intake/SKILL.md:113` 散文改「見 `schema/vocab.json`」；`skills/source-trace/SKILL.md` tier 表加兩行；`query/bottleneck.py:401-402` 不動（datasheet 不算 costly）。
怎麼驗：三處相等測試；loader 對 `source_type=teardown` 的 JSON 驗證通過。

**c｜`origin_linkage`（給 4.3 用的宣告欄）。** 改哪裡：`schema/intermediate_format.schema.json` source_doc 加選填 `origin_linkage ∈ {same_origin, independent}`（vocab 登記）；`loader/load_to_neo4j.py::MERGE_SOURCE_DOC` 寫入（缺＝null）；`prompts/extract_system.md` origin 段加一句「媒體文：轉述／改寫新聞稿＝same_origin；自己採訪或統計＝independent；不確定不填」。
怎麼驗：schema 測試；loader 寫入測試（fake driver）。

**d｜apply 入口。** 改哪裡：新 `scripts/apply_ra_admission.py --pq2 N --digest <sha256> [--leads …]`：讀池子，要求 ①`item.type=="ra_admission"` 且未 resolve（drop 永久拒絕）②`item.ref_id==action_id`（由紀錄反查）③digest==紀錄 `action_digest` ④紀錄 state ready 且未過期；通過後先把 `approval={"pq2_n": N, "digest": …, "at": …}` append 到 action 紀錄的 `execution`，再呼叫 `intake.application._apply_research_action_impl`；**不 publish、不 resolve**（`commit_pending_intake.py` 與 `complete-ra` 照舊；`engine_b/todo.py::complete_ra_admission` 加一行比對 `approval.pq2_n==n`、缺 approval 拒收）；刪 `intake/application.py::_finalize_research_action_impl` 與 `tests/test_intake.py` 的 10 處；`prompts/intake_protocol.md:100`、`skills/daily-brief/SKILL.md:700`、`skills/lead-intake/SKILL.md:155`、`docs/OPERATIONS.md` 改指入口（跑 `sync_agent_skills.py`）。
怎麼驗：四道 fail closed 各一條測試（編號不存在／型別不對／已 drop／digest 不符／已過期）；成功路徑在暫存紀錄上寫 approval 再 apply（fake）；`complete-ra` 缺 approval 拒收；**sandbox impact review 五步**（互動專用；落在 `Bash(python *)` 之下，補償控制＝四道檢查＋戳記；不進任何無人值守 allowlist）。
L11-6 ④：7 筆 partial／expired 的 RA（對應 drop）——新入口全部拒絕是既有語意，第一次撞到會以為入口壞了，訊息要寫「重提請重跑 prepare」。

**e｜抽取 JSON section／title 回填＋三處判準合一。** 改哪裡：一次性腳本 `loader/migrate_sourcedoc_json_section.py`（讀圖上 32 份有 section 的 doc，對 10 份只存在圖上的把 `source_doc.section` 寫回對應抽取 JSON——base 與 addendum 同值；`nvidia_photonics_pr_2025_03_18` 沒有抽取檔→從圖上 SourceDoc 與其 assertions 重建一份最小抽取檔或在 manifest 登記「不可重建、理由」（**4.0 實測更正：它有兩份抽取檔、直接寫回；另有 `sivers_ar_2025_photonics_excerpt` 兩份 JSON 互異也要對齊——§0.6 #2**）；21 對 addendum 的 `source_doc.title` 改回母文件標題（**4.0 實測：title 不一致 19 個 doc_id**）；manifest 記 before／after、只動這兩欄）；`loader/load_to_neo4j.py` 抽出公開 `is_legit_multi_section(sections) -> bool`（判準採 loader 的：全非空且兩兩互異），`query/health_audit.py:333-335` 與 `audit/checks.py:155-166` 改呼叫它、audit 改用 `normalize_url` 分組；常駐計數器「圖上 section／title 與抽取 JSON 不一致的份數」（住健康審查，今天 10＋21 → 0）；`docs/OPERATIONS.md:898-908` addendum 修復程序改成「以抽取 JSON 為準重載」。
怎麼驗：回填後重載 addendum 檔（fake driver 或暫存圖）section 仍在、title 是母文件；`is_legit_multi_section` 單元測試（放寬成 any → 紅）；計數器 → 0；`tests/test_load_dedup.py:72-79` 照綠。
L11-6 ④：`meta_vistara_isca_2026`／`_counter_path` 那對（10-01 剛修好的）——回填後兩個 JSON 都要有各自 section，否則 `check_duplicate_url` 會 raise。

**R2-a（常規 opt-in）WORK_REQUEST：**
```
WORK_REQUEST（R2-a，Phase 4 Step 4.2）
Target: 4.2 的 commit；intake/actions.py、intake/application.py、scripts/apply_ra_admission.py、engine_b/todo.py、schema/*、extract.py、loader/*、query/health_audit.py、audit/checks.py、extractions/（回填的 30 份）、prompts/intake_protocol.md
Claimed acceptance: layer_enumerations 是頂層選填、舊 139 筆 render 逐字不變、核對只看本包且區分兩種失敗；source_type 三處相等；apply 入口四道 fail closed 且 approval 先寫後 apply、不 publish 不 resolve、complete-ra 驗 approval；
                    抽取 JSON 回填後重載不洗掉 section／title、計數器 0；is_legit_multi_section 三處共用
Do not trust: 上面那行是待驗證的宣稱
Task: 自己跑相關測試；自造 6 個應拒收的 request 與 1 個應收的；對 2 筆舊 pushed 紀錄跑 render 比對；在暫存圖上重載 meta_vistara 兩份 JSON 看 section；確認 scripts/apply_ra_admission.py 不在任何無人值守 allowlist、sandbox review 五步寫齊
Boundaries: 不改 code、不 commit、不寫 Neo4j 正式圖、不 apply 任何 RA、不核准 pq2
```

## 4. Step 4.3 `publishers.json` 與 origin 解析唯一 owner（Z2，R1）

改哪裡：新 `config/publishers.json`（`.gitignore` 補 `!config/publishers.json`；每筆 `{origin: <_strip_annotation 後的字串>, kind, corroborates: bool, note}`；`kind` 封閉：`industry_research`、`teardown_lab`、`standards_body`、`government_statistics`、`academic`、`media`；**只有前五種 `corroborates=true`**，`media` 一律 false）；新 `query/origin_resolution.py::resolve_origin(origin) -> {kind: company|publisher|unresolved, id, corroborates}`（先 `company_id_for_origin`，再 publishers，否則 unresolved；**唯一 owner**）；`query/bottleneck.py::classify_evidence` 改讀它（publisher 且 corroborates → `externally_corroborated`；publisher 且 kind=media → 新標籤 `media_relay`，rank 與 needs_review 同級、**只為把 None 的兩義拆開**〔L12〕，進 EVIDENCE_RANK／LABEL／`argument.EVIDENCE_CLASS_PLAIN`／`evidence_quality`／`graph_neo4j` tier／`CORROBORATED_EVIDENCE` 不含它，並加一條測試「五張表 key 集合＝EVIDENCE_RANK.keys()」；media 文要升級須該 SourceDoc `origin_linkage=independent`〔4.2c〕且仍不得是 same_origin）；`alpha/providers/structure_readings.py::verify_citations` 的 `independent` 核對改讀同一個 owner（登記的 corroborates publisher 算獨立）；登記清單由 Step 4.0 第 3 項的 59 個字串逐條定（互動 session 判，未登記＝不猜）。
怎麼驗：`resolve_origin` 單元測試三態；同一 origin 在 `classify_evidence` 與 `verify_citations` 結論一致（測試）；media 不升級（變異：media corroborates=true → 紅）；真實圖重跑：needs_review 113 → N、因登記升級的邊逐條（預期含 GSR／Reuters 對 `mat:inp_substrate` 的 Sumitomo／JX 兩條）、因此 stale 的讀圖 id（預期 `mat_inp_substrate` 層 low、不進第 4 型）；走圖第 2 型命中前後。
L11-6 ④：`tech:cw_dfb_laser` 讀圖「本輪更正」段指出的那條——一句沒點名 Sivers 的華星光年報引文把 Sivers 邊抬成印證：本 Step **不**修它（§0.3），但要印出「externally_corroborated 且引文不具名供應商」的邊數（4.4 計數器）。
（執行後：每筆登記多一欄 `seen_in`；`CanonicalEdge` 記的是逐份文件的宣告 `origin_linkages`；`same_origin` 否決所有發布者；插槽視角與 L8 稽核腳本也走同一個 owner——見 §0.6 #10。真實圖 59 條邊變動、stale 讀圖 3 份、走圖第 2 型不變、「外部印證但引文不具名」15 條。）

## 5. Step 4.4 字表、`sub_language_in_quote`、常駐計數器（Z2，R1）

**a｜字表。** 新 `config/substitutability_language.json`（`version`、`_history`、`terms[]` 中英；初版由執行者從 `prompts/extract_system.md:314-322` 的三類語意〔replaceability／qualification of alternatives／exclusivity〕擬、寬窄兩版都存但只用一版並記名；`.gitignore` 補 `!`）；測試：`prompts/`、`skills/` 的任何檔不得引用該檔名或逐字含 ≥5 個 terms（L19 grep 測試）。
**b｜旗標 owner。** 新 `query/sub_language.py::quote_has_sub_language(quotes) -> bool` 與 `fetch_all_quotes(driver)`（按 assertion id collect；**不把 QUOTES OPTIONAL MATCH 塞進 `fetch_assertions`**——`documents` 計數會錯）；對 sub 非 null 的 assertion 各算一個 `sub_language_in_quote`；結構表每邊印 `assertions_without_sub_language: [ids]`（列表不是布林）、artifact 帶總數；**不寫投影 meta、不改 `collapse_assertions`**；packet（4.2a）對本包每條帶 sub 的邊印警告「sub 引文不含可替代性語言」不拒收；準確率抽樣：8 筆已裁決＋固定 20 筆 auto，執行者人讀對照旗標，結果寫進八欄與 baseline（只印，不放閘）。
**c｜三個計數器＋附屬。** 住 `webapp/materialize.py::materialize_graph_walk`（唯一為走圖連圖的地方）新增一段 `layer_stats`（或獨立 kind `layer_stats`，二擇一寫八欄；`STATE_KINDS`／`_STATE_NOTES`／`_STATE_FLAGS` 三處同步、`STATE_SCHEMA_VERSIONS` 升版）：①supply_side 口徑 ns=0／1／2／≥3 絕對數＋「ns==1 且全自報」節點數（對 4.0 凍結集合，另印集合外新節點數）；②「≥3 家」層數（母體）＋「有一份非供應商 origin 來源引文具名 ≥2 家」層數（驗收）＋「≥3 家且每家撐住」層數（稽核；撐住＝引文含名 **或** origin 解析到這家）＋未解析 origin 的來源數；③a 存量 unsupported 筆數＋id、③b Phase 內新增／supersede 的帶 sub assertion 中 supported 比例（以 4.0 凍結的 assertion id 集合判「新」）；附屬：「externally_corroborated 但引文不具名供應商」邊數；字表版本；心跳段 3 加一行照 `_graph_walk_line` 讀 artifact 印；結構表頁首讀同一份 artifact。
怎麼驗：純函式測試（夾具圖）每個數；`tests/test_heartbeat_graph_walk.py` 格式釘住的行不變、新行有測試；`test_webapp_graph_walk_watches.py`／`test_webapp_structure_table.py` artifact 形狀；真實資料跑一次把 ①②③ 印進八欄——**這是 A1／A2／A3 的基準**（4.1 補名冊後的名字集合）。
L11-6 ④：`query/bottleneck.py:391` `documents` 計數；`_candidate_set_hash`（旗標不得進 candidates）；心跳 `build_graph_walk_artifact` 升版後舊 artifact 的「型別不一致」警告。
sandbox impact review 五步（materialize 旗標若新增）。
（執行後：沒有新增 materialize 旗標或新入口，不需 review——見 §0.6 #11；①②③ 的基準與準確率抽樣見 baseline 報告 §21。）

## 6. Step 4.5 走圖第 2 型記憶與終局；skill 改寫（Z1＋Z2，R1）

**a｜走圖。** 改哪裡：`query/graph_walk.py` 第 2 型 `hit_rule` 加「且該節點沒有現行層讀圖」（與第 1 型同一個 `read_nodes`；`current`／`stale_low` 算現行）；每筆命中 `extra` 印 `open_lead`（refs 帶 `graph_walk_subject==node` 且 status ∈ {triaged_go, researching, parked 非終局} 的 lead id）與 `reading`（若有過期讀圖印 id）；`scope_rule` 不動；心跳段 3 不改格式。
怎麼驗：夾具：有現行層讀圖的單供應商節點不命中、讀圖過期後命中回來（會滅、會亮）；真實資料前後命中逐筆列原因。
**b｜lead 鑄號路（互動）。** 改哪裡：`engine_b/leads.py::triage` 與 `engine_b/cli.py triage` 加選填 `--classified-by`（預設不變 `triage_semantic_v1`；research-drain 用 `interactive:graph_walk`），心跳「分類層本輪結果」與 `queue_segments` 把非 `triage_semantic_v1` 的分開計；`skills/research-drain/SKILL.md` 段 4 ②改寫：研究啟動那一刻 `engine_b.cli register --source graph_walk:sole_supplier_self_reported --url <真實文件 URL 或 graph-walk://sole_supplier_self_reported/<node>> --title "<人寫的研究問句>"` → `triage --go --classification … --classified-by interactive:graph_walk` → 以 lead-intake／source-trace 追源；終局三種：找到第二家或第三方印證 → RA（`applied`）；公開層文件找不到／只有付費 → `advance` 到 `parked` 且 trace_status `awaiting_named_disclosure`（trigger entities＝該層客戶或供應商，`advance()` 自動建追源 watch、到期 `watch_expired` 計數現形）或 `not_pursued` 附理由；圖上已多了第二家 → 命中自己消失，lead 若仍 open 由 drain 段 4 以 `not_pursued`（理由「已由入圖消解：<edge>」）收掉。**不加 trace_status 字彙。**
怎麼驗：`tests/test_engine_b_leads.py` 的 `classified_by` 參數測試；skill 測試（`tests/test_skill_decision_contract.py` 可執行行）；sandbox review（CLI 旗標新增）。
**c｜三個 skill。** 改哪裡：`skills/source-trace/SKILL.md`——**不改 claim 路由頂階**，在分流表之後加一節「輸入是層／節點時：客戶 filing 供應商段 → 產業報告 → 規格書／teardown → 供應商自己的文件；41-45 行的 transcript 優先仍成立」、tier 表加 datasheet／teardown；`config/source_routes.json` 登記 `layer_document` route（applies_to always、rung 介於 local_library 與 issuer_site、tier_cap 1、how 指向該節）＋`tests/test_source_routes.py` 一條（`missing_rungs` 對舊 parked lead 會多報一條「沒試」——預期，寫八欄）；`skills/company-onboard/SKILL.md`——Step 1「坐哪一層」改必答（節點 id 或「未知→先走 system-decompose／走圖」）、`TICKER_MAP` 改指 `config/company_identity.json`；Step 2 改一句指向 source-trace 層文件節＋各市場 fetcher（`--forms`、`python -m fetchers.mops`），不自己列清單；Step 3「N/3 才能生成」改「列出自報／客戶端／第三方各幾份，packet 必帶 `layer_enumerations`」不留數門檻；Step 4b 改 extract.py 真旗標；**Step 4d／5 改 `prepare_research_action.py` → pq2 `ra_admission` → `scripts/apply_ra_admission.py`**，刪直接 load；`skills/lead-intake/SKILL.md:125-128` 加一句層文件節也是 source-trace 的；`skills/research-drain/SKILL.md:169` 加括號指節名；新 `tests/test_company_onboard_skill.py`（可執行行不得出現 `loader/load_to_neo4j.py`、必須出現 `prepare_research_action`）；`tests/test_source_trace_skill.py` 加「直接去 transcript」那句仍在層文件節之前；跑 `python scripts/sync_agent_skills.py`。
L11-6 ④：`tests/test_source_trace_skill.py:8-30` 鎖的固定字串。
（執行後：見 §0.6 #12；真實資料第 2 型前後都是 2／13——`tech:semiconductor_manufacturing_equipment`（AMAT，自報·filing）與 `tech:six_inch_inp_production`（COHR，自報），兩筆都沒有現行層讀圖、沒有進行中的 lead；鑄號在 4.8。）

## 7. Step 4.6 稀釋燈＋Engine C `METRICS` CHECK 遷移（Z2，R1 ＋ R2-c 常規 opt-in）

**前提：** Step 4.0 第 10 項的 tag 覆蓋率；若 `StockIssuedDuringPeriodValueNewIssues` 在 35 檔中覆蓋 <20 檔，停下寫八欄（不自行換指標）。
**a｜串接點合一。** `alpha/providers/candidates.py:208-225` 與 `briefing/alpha_view/sources.py:438-451` 的 `get_wipeout_inputs→wipeout_flags` 串接抽成一個函式（closeout §5 #19）。
**b｜Engine C。** `engine_c/history_backfill.py::METRICS` 加 `equity_issued_value`（`us-gaap:StockIssuedDuringPeriodValueNewIssues`；單季 fact＋年度，Q4＝FY−9M 衍生照營收規則；單位 USD、`unit_scale` 照存）；稽核欄（有餘裕才加，否則列 §14）`proceeds_equity`（有序 fallback `ProceedsFromIssuanceOfCommonStock` → `ProceedsFromIssuanceOrSaleOfEquity` → `ProceedsFromIssuanceOfConvertiblePreferredStock`、`_span_class` 加 six_month 桶）；**CHECK 遷移**：SQLite 以 backup API 先備份、table rebuild、對帳列數、CHECK 更新；Postgres migration 檔＋`schema.sql`；daily 增量在遷移後才收新 metric；遷移不得與 daily 同時跑、push 在 05:30 前。
**c｜燈。** `alpha/wipeout.py::dilution_flag`：國內申報人（`filer_class==domestic_quarterly`）——黃＝trailing 一年（實作＝最近四季、期末距窗尾 < 320 天；年度差額歸不到季時不判綠——§0.6 #13）`equity_issued_value` 加總 >0，印金額（USD）、占正規化市值 %（`market_normalization`）、同期封面股數變化 %、instrument tag（可轉換特別股照黃、印 tag——使用者可改）；股數增加但 `equity_issued_value` 為 0 → 不上色，另列「股數 +X%（無新股發行紀錄）」；tag 缺席 → `provider_missing`＋股數變化照印；其餘申報人 → `method_not_applicable`＋股數變化照印（**不再判色**）；窗不滿 → `insufficient_evidence`（保留 `colour_available_on`）；人工欄位 `equity_issuance_authorizations` 讀出來當脈絡印（今天 2 筆）；`CAP_WIPEOUT_FLAGS` 升版；`tests/test_wipeout_flags.py:121-130、168-182` 改。
怎麼驗：純函式測試每個出口；真實資料逐檔印「來源、tag、金額、顏色前後」——**AXTI（+42%、Q2'26 600.1M）必須黃、AAOI 黃、LITE 黃（可轉換，印 tag）**；國內申報人 30 檔 24 黃 → N 黃（逐檔列為什麼）；38 檔非國內全部 `method_not_applicable`（候選板「可開」計數若動要解釋）。
L11-6 ④：daily 05:30 的 EDGAR 段——CHECK 未遷移時 35 檔 edgar outcome=error 且該批 revenue／cash 一起沒寫。

**R2-c（常規 opt-in）WORK_REQUEST：**
```
WORK_REQUEST（R2-c，Phase 4 Step 4.6）
Target: 4.6 的 commit；engine_c/history_backfill.py、engine_c/db.py、engine_c/migrations/*、alpha/wipeout.py、alpha/providers/candidates.py、briefing/alpha_view/sources.py、tests
Claimed acceptance: CHECK 遷移前後列數相等、舊 metric 一筆不變；equity_issued_value 每列可答 T 時刻知道什麼（filed）；季度／年度期間去重；燈的六個出口各有測試；AXTI 黃；非國內申報人不判色且股數變化照印；daily 增量跟新 metric
Do not trust: 上面那行是待驗證的宣稱
Task: 自己跑測試；對 3 檔（AXTI、AAOI、LITE）手核 companyfacts 原始 fact 與表內值；確認遷移腳本對 WAL 庫用 backup API；確認沒有任何列的可用日取自 fetched_at；確認 shares_outstanding_cover 序列未被改
Boundaries: 不改 code、不 commit、不寫正式庫、不跑遷移
```

## 8. Step 4.7 四個小修（各 Z1，R1，可拆四個 commit）

**a｜240 條退役不印。** `engine_b/disproof.py::downside_rows` 拿掉 `judgment` 來源（`DOWNSIDE_SOURCES` 同步）、`page_input` 的 `judgment_conditions` 參數刪；research 面板 `disproofs=fs.conditions`（`compose.py:219`、`render.py:424`、`app.js:506-515`）拿掉；downside 固定註腳「一律未盯」刪；`briefing/analyst_view/contracts.py:408` 的 `disproofs` 欄退役或留空（二擇一寫八欄）；判斷檔原樣留（私有、不是 ledger）。驗：downside／research 面板 `source="judgment"` 列數 240 → 0；`tests/test_stock_page_phase3.py:97-111、245-254、613-615、805-813` 跟機制走；73 份 digest 變動逐檔預期。
**b｜`ignored` 接 held_index／心跳。** 新讀者（`portfolio/holdings.py` 或 `alpha/candidates.py`）讀 `config/holdings_coverage.json`，`sheet_ticker` 在 `ignored` 的列不算「解析不到」、候選板 `holdings.ignored[]` 另列（附 reason／decided_at）、心跳「持股解析不到 N（使用者決定不研究 M）」；`docs/OPERATIONS.md:1494-1498` 更新。驗：夾具 ignored 一筆 → unresolved 不含它、ignored 列印出；今天真實資料 ignored 0 照印 0。
**c｜百分位覆蓋率。** `alpha/three_questions.py::own_history` detail 加 `trading_days_in_window`（從 `price_bars` 在同一窗內數）與 `coverage=samples/trading_days`；CLI `render.py:384-401` 印 samples／覆蓋率；**不設門檻**。驗：LRCX 型夾具（751 日只有 314 樣本）印 0.42；無布林結論測試仍綠。
**d｜同敘事重複反證拒收。** `alpha/providers/briefs.py::v2_write_problems` 加：本版 `disproof[]` 內 `normalize(condition)` 相同 → 拒收並印是第幾條（沿 `event_watch.py:1217-1227` 的判準）；跨公司不比（既有）；**放寫入端不放 `_check_v2_static`**。驗：兩條相同 self 反證拒收（R2 探針重現）；真實 ledger 4 檔照綠。

## 9. Step 4.8 研究（**強模型、互動 session**；研究，不是開發）

**不停、直接做；每件都走正式入口；撞 pq2 掛號後接著做下一件。** 寫 `library/` 前取得互動 writer lock。

1. **`mat:inp_substrate`（資料工，不找新文件）：** 4.1／4.3 做完後重跑計數器——Sumitomo／JX 兩條邊應由 needs_review 變 externally_corroborated（GSR 登記為 `industry_research`、Reuters 登記為 `media` 且該 SourceDoc 若是 Reuters 自己的報導就宣告 `origin_linkage=independent`——這需要一次 RA 或 migrate 改抽取 JSON 的 `source_doc`，走 pq2 `ra_admission`）；驗收②這一層應從 0 變 1。若計數器沒動，寫八欄說為什麼（不改計數器）。（4.4 實測：兩條邊升級與②這一層計入都已在 4.3 發生——baseline 報告 §21；剩下 Reuters 那份的 `origin_linkage` 宣告，它只影響邊的證據等級。）
2. **`tech:cw_dfb_laser`：** 研究啟動時鑄 lead（source=`graph_walk:thin_layer_unread` 或使用者點名——寫明）；依 source-trace 層文件節找公開一手「列舉 CW DFB 供應商集合」的文件（候選：Coherent／Lumentum 10-K competition 段、台股年報「競爭廠商」段〔VPEC 2455、LandMark 3081 已在 extractions，先補抽 `competes_with`／`supplies_to`〕、客戶端 transceiver 廠文件）；找到 → packet 帶 `layer_enumerations`（origin_role 照實）→ pq2；找不到公開一手 → lead `awaiting_named_disclosure`（trigger entities＝Innolight／Eoptolink／Broadcom 等客戶）＋把「Lumentum 內製 CW 雷射」買家垂直整合反證登記為 watch（若現行讀圖還沒有）。
3. **第 2 型 AMAT→`tech:semiconductor_manufacturing_equipment`：** 鑄 lead（`graph_walk:sole_supplier_self_reported`）；終局＝RA 提案把 GlobalFoundries 的需求邊改指更細節點（`tech:deposition_etch_clean` 等）並補 LRCX／TEL／ASML 的供貨邊（各自逐字），或拆節點——一份 RA；pq2 go 後經 4.2 入口 apply；命中消失要出現在心跳 diff。
4. **第 2 型 COHR→`tech:six_inch_inp_production`：** 鑄 lead；先 grep 自家庫（L11-4）：`extractions/axti_8_k_20260702_coherent_inp_supply.json` s2；RA 把該 8-K 當 origin=AXT 的來源接到 Coherent 的供貨邊（或 `co:axt supplies_to tech:six_inch_inp_production` 若逐字支持）→ pq2 → apply；終局 `original_obtained`＋applied。
5. **stale 讀圖與敘事：** 4.1／4.3 讓 `prod:supernova`／`prod:els_8ch_module` 插槽讀圖 stale（high）→ 重讀（v3 契約、引用逐字由程式核對）；SIVE.ST 敘事若進 `narrative_rewrite` → 換版處置 `acknowledged_touched[]`；AXTI 若 `mat_inp_substrate` 層讀圖 stale_low 不動。
6. **收據：** `docs/reports/2026-10-xx-phase4-step48-research.md`：每件的 lead id、pq2 編號、RA id、入圖前後的 class 與計數器讀數、終局。

L11-6 ④：第 2 型兩筆命中消失後心跳段 3 的 diff 行；SIVE.ST 候選板狀態當天是否變（可開為零就零）。

## 10. Step 4.9 新管線 full chain 測試（Z1，R1）

夾具版端到端：一份 `origin_role=industry_report` 的層文件 request（`layer_enumerations` 2 家）→ prepare → 池裡 `ra_admission` → `scripts/apply_ra_admission.py --pq2 --digest`（fake driver）→ approval 戳記 → `complete-ra` → 計數器（夾具圖）②＋1、①−1；一份引文不具名的 request 被拒；一筆 media origin 文件不升級；走圖第 2 型對有現行讀圖的節點不問。`tests/test_full_chain_acceptance.py` 真 runtime 那份 27 條不動。

## 11. 驗收數的是哪一層（completion gate 第九項）

| 驗收 | 數的東西 | 層 |
|---|---|---|
| ROADMAP ①（A1） | 對 4.0 凍結節點集合，ns==1 且供貨邊全部自報的節點數：4.4 基準 → 結案（4.8 的 AMAT、COHR 兩筆應各減 1） | 圖 |
| ROADMAP ②（A2） | 有一份非供應商 origin 來源、引文逐字具名 ≥2 家供應商的層數：基準 → 結案（inp_substrate 應 +1）；「≥3 家」母體與「每家撐住」只印 | 圖 |
| ROADMAP ③（A3） | ③a 存量 unsupported 筆數與 id（只印）；③b Phase 內新增／supersede 的帶 sub assertion 中 supported 比例（100%，缺的逐筆） | 圖 |
| 走圖第 2 型 | 命中逐筆＋旁印 `open_lead`／`reading`；本 Phase 鑄的 lead ≥2 筆各到終局（applied／parked 附 trace_status 與 watch） | 走圖 × lead registry |
| packet | 至少 1 份 applied RA 帶 `layer_enumerations` 且核對通過；apply 入口的 approval 戳記存在 | RA 紀錄 |
| origin 解析 | 未解析 origin 73 → N；needs_review 113 → N；因 B／display_name／publishers 各自變動的邊逐條；因此 stale 的讀圖 id 與其處置 | 圖 × 讀圖 |
| 稀釋燈 | 國內申報人黃 24 → N（逐檔來源與理由）；AXTI 黃；非國內 `method_not_applicable` 38 | 敘事（稽核區） |
| 240 條退役 | downside／research 面板 `judgment` 列 240 → 0 | 敘事 |
| section／title | 圖上與抽取 JSON 不一致 10＋21 → 0（4.0 實測基準 11＋19，§0.6 #2） | 圖 |
| ignored、覆蓋率、重複反證、`classified_by`、`layer_document` route | 符號與測試存在；變異會紅 | 機制 |

**沒有任何一個是「幾檔通過某個 filter」。** 候選板「可開」數只印不驗收。

## 12. Phase 4 結案（completion gate：historical-failure-matrix §9 八項 ＋ 第九項）

1. `pytest -q` 全綠；測試檔數差＝新增－退役；函式層級以 4.0 名單比對，拿掉的每一個寫去向。
2. `python -m audit invariants` 綠（含新計數器「section／title 不一致」）。
3. 無未解釋語意 diff：心跳與 4.0 逐行對照；個股頁核心面板 digest 只在 4.7a（judgment 列）與 4.8（敘事換版）預期處變；research 面板排除 notes。
4. 無新 dual authority：origin 解析只有 `resolve_origin`（`classify_evidence`、`verify_citations`、packet 共用）；名字比對只有 `quote_names_company`（packet、計數器共用）；sub 旗標只有 `query/sub_language.py`；拆段判準只有 `is_legit_multi_section`；執行別名只有名冊派生的 `get_execution_aliases()`。
5. 無 silent drop：計數器每格印 0；未解析 origin 另印不壓成第三方；packet 核對失敗分兩種原因；稀釋燈六個出口各有 kind。
6. Point-in-time：`equity_issued_value` 以 `filed` 為可用日（測試）；lead `published_at` 不冒充；`audit PointInTime` PASS。
7. lifecycle 可達：本 Phase 鑄的 lead 都在終局或帶 watch；`awaiting_named_disclosure` 的 `auto_trigger_reachable=true`；`QueueLiveness` 綠。
8. executable protection：apply 入口四道 fail closed、packet 拒收、media 不升級、`execution_symbol` 衝突 raise、同敘事重複反證拒收、CHECK 遷移列數對帳，各有會紅的測試；殭屍 grep 九組三個 0。
9. 驗收數的是 §11 的層。

**另核對：** 舊 Decision Store 三個 `*.db` sha256 與 `live_choices` ＝ 4.0；`trade_log.jsonl` 不變；`git diff <4.0> HEAD -- AGENTS.md` 為空；`company_id_for_ticker` 語意未改（既有測試逐條）；`library/resolutions/` 不變；`collapse_assertions` 在真實資料上與 4.0 逐位相同。

closeout 報告存 `docs/reports/2026-10-xx-phase4-closeout.md`，附「本 Phase 執行中發現、Phase 5 要決定的問題」（§14 種子＋執行中新增）。

### 結案 R2（使用者已常規 opt-in；執行者不必再問）

```
WORK_REQUEST（R2，Phase 4 結案）
Target: master 最新 commit；docs/reports/…-phase4-baseline.md、…-phase4-step48-research.md、…-phase4-closeout.md；
        docs/plans/2026-10-01-001-feat-phase4-layer-centric-sources-plan.md（§0.4 amendment、§0.6 偏差、§0.7 處置）
Claimed acceptance: Phase 4 completion gate 九項全過、ROADMAP Phase 4 驗收①②③（A1–A3 定義）成立（見 closeout）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python -m pytest -q；python -m audit invariants；測試函式層級增刪自己比（4.0 commit 起），抽 5 個拿掉的函式確認去向成立
  2. 圖：重跑 supply_side 分布與「ns==1 且全自報」對 4.0 凍結集合；重跑 _classify_edges 與 4.0 比，class 變動邊逐條有歸因（B／display_name／publishers／4.8 入圖）；
     抽 5 條升級邊確認 origin 真的是自產資料的第三方、引文逐字具名
  3. sub：對 4.0 凍結的 assertion 集合重算 sub_language_in_quote，與 artifact 相同；Phase 內新增的帶 sub assertion 逐筆看引文；library/resolutions/ 與 collapse_assertions 輸出 ＝ 4.0
  4. lead：本 Phase 鑄的 lead 逐筆狀態、trace_status、watch；走圖第 2 型對有現行讀圖的節點不問（自造夾具）
  5. packet／apply：自造 6 個應拒收 request；對 4.8 的 RA 紀錄看 approval 戳記與 complete-ra；scripts/apply_ra_admission.py 不在任何無人值守 allowlist
  6. 稀釋燈：AXTI、AAOI、LITE 對 companyfacts 手核；非國內 38 檔 method_not_applicable；CHECK 遷移前後列數
  7. 名冊：display_name 100/100 抽 10 家核來源；name_aliases／execution_symbol 不在 by_ticker；凍結區 0 diff；pq1 排序逐位
  8. python scripts/retired_mechanism_grep.py 三個 0；Decision Store 三檔、trade_log、AGENTS.md 不變；section／title 不一致計數器 0
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet、不寫任何 ledger
```

### 結案之後：停，不要開 Phase 5

R2 回 GO 後：ROADMAP Phase 4 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。然後 **`AWAITING_HUMAN`**：Phase 5 還沒有 plan。
HUMAN SUMMARY 的「下一步」逐字印 `docs/plans/README.md`「每個 Phase 開工前要有一份 plan」那段指令。

## 13. 已知陷阱

- **順序是硬的：** Q8b-B（4.1a）→ 名字比對（4.1b）→ `display_name` 補齊（4.1c）→ publishers（4.3）。反過來做，Sivers 自家 PR 的 3 條邊會先被洗成 counterparty_joint、插槽讀圖 stale 兩次。
- **`report` 是 exact fields**：`layer_enumerations` 放進去會讓 131 筆 pushed 紀錄的 `_validate_record` 全部失效；放頂層 `REQUEST_OPTIONAL_FIELDS`。
- **prepare 不開 Neo4j**：`layer_enumerations` 核對只看本包；「在圖與否」apply 時自然驗。
- **`_origin_mentions` 的 ≥4 字子字串會撞 `co:apollo`**；整詞化後 320 分支的具名數只會減——列出變動 doc。
- **`aliases` 是 ticker、進 `by_ticker`**；名字放 `name_aliases`，否則 `company_id_for_ticker` 等於被資料放寬。
- **`display_name` 不得從 slug 推、不得抄 Neo4j `Company.name`**（LLM 寫的）；registry docstring 明寫 mechanical。
- **`get_execution_aliases()` 的名稱與 dict 形狀不能變**：凍結區 `decision_lab/adapters/holdings.py` 與 `shared.identity_resolution.resolve_identity` 都吃它。
- **投影 meta 沒人每日刷新、只有 `thesis/evidence_manifest` 在讀**：旗標住 artifact；**QUOTES 不得 join 進 `fetch_assertions`**（`documents` 計數會錯）；旗標不得進 `candidates` value（`_candidate_set_hash` 會翻 8 筆 approved resolution）。
- **sub 非 null 才算主張**：20 筆 `substitutability: null` 的 assertion 不進分母。
- **字表只給檢查器讀**：prompts／skills 不得引用檔名或堆 terms（grep 測試）；改字表＝換尺，要重印基準並升版。
- **lead 狀態機沒有自動結案；`parked→pending` 清 triage；`wake_lead` 到期是 `watch_expired` 終局**：任何「daily 自動鑄／自動結案」都是第二個狀態源。鑄 lead 只在互動研究啟動時。
- **鑄出的 lead 若帶 company_id 會進第 5 型母體**（今天 7/13 恆亮）——plan 寫明是否帶、心跳 diff 要解釋。
- **`materialize` 是 APP 讀 cognition**，不是 Engine B writer；計數器住它可以，鑄 lead 不行。
- **`awaiting_named_disclosure` 是非終局**：必須帶 trigger entities 否則 `trace_backlog` 標 `auto_trigger_reachable=false`。
- **apply 前不存在 go 收據**：入口驗編號／ref_id／digest／未結案／未過期，再寫 approval；7 筆 partial／expired（對應 drop）會被拒是既有語意。
- **抽取 JSON 是圖的 ground truth（L10）**：section／title 寫回 JSON，不是在 loader 加 coalesce；`meta_vistara` 兩份 JSON 都要有各自的 section 才過 `check_duplicate_url`。
- **三處「合法拆段」判準今天互異**：共用一個函式後 audit 改 `normalize_url` 分組；「同事件不同 URL」仍看不到（ROADMAP 116 ⑤，不是本次驗收）。
- **`StockIssuedDuringPeriodSharesNewIssues` 不能用**（AXTI／LITE 不存在、AAOI 停 2014）；金額 tag 三檔都有；cash-flow proceeds 是 YTD、`_span_class` 沒有 180 天桶。
- **`METRICS` 烤進 SQLite CHECK**：`ensure_history_schema` 只 CREATE IF NOT EXISTS；不遷移就加 metric，daily 的 EDGAR 段整批回滾。
- **「非 SEC」措辭錯**：TSM／UMC／HIMX／GFS／TSEM／NBIS 是 20-F 的 SEC 申報人；判準是 `filer_class != domestic_quarterly`。
- **`tests/test_wipeout_flags.py:121-130` 期望無 source 序列判色**：改規則要同 commit 改它。
- **evidence 等級是五張硬編碼表**：加標籤（`media_relay`）漏一處是 KeyError 或靜默降級；加「五張表 key 集合相等」測試。
- **evidence 進讀圖 digest**：層讀圖 evidence 變＝low（不進第 4 型）、插槽供給側＝high；每次改分類器都要印 stale 清單。
- **心跳段 3 格式被測試釘住**；`STATE_SCHEMA_VERSIONS` 升版後舊 artifact 會觸發「型別不一致」警告一天。
- **`companyfacts_lag` 對 20-F 恆不報落後**（Phase 3 陷阱沿用）。
- **Windows**：python 不認 `/tmp`，暫存用 scratchpad／`%TEMP%`；程式碼不要放 heredoc；子行程用 `sys.executable`；PowerShell 管線會加 BOM（JSON 用 `utf-8-sig` 或走 Bash）。
- **Neo4j 要開**；讀不到圖時計數器印 `upstream_unavailable`，不印 0。
- **可開為零就零**：4.8 的研究讓 SIVE.ST 進重寫、候選板當天變動都是合法結果。

## 14. 結案時要列的待決問題（種子；執行中發現的往下加）

1. **sub 的消費端要不要忽略 `sub_language_in_quote=false` 的 sub**（結案印：忽略後走圖 1–3 型母體 13 → ？、鏈段有邊可講的檔 → ？、會 stale 的讀圖 → ？）。
2. **「外部印證」要不要求引文逐字具名被印證的供應商**（結案印：externally_corroborated 217 條中引文不具名的 N 條；cw_dfb 讀圖指出的華星光案例）。
3. `counterparty_joint` 的 320 分支（整串不解析且具名 ≥2 家）要不要改成以 `publisher`／雙發行人宣告為準（lens 建議）。
4. 媒體自己的報導（Reuters 市占句）靠 `origin_linkage=independent` 宣告升級——要不要補 `same_origin` 的機械偵測（同事件成對文件）。
5. `name_aliases` 的中文名覆蓋到哪（台股／日股供應商）；`yfinance_symbol` 要不要進名冊。
6. 稀釋燈：可轉換特別股算黃（本 Phase 預設）；`proceeds_equity` 稽核欄若未做；員工行權／轉換／收購三類股數來源要不要各自印。
7. 本 Phase 鑄的 lead 要不要進第 5 型母體；`graph_walk:*` 管道的來源標籤怎麼走到 Phase 5 的量測。
8. Phase 2／3 帶過來未併入的：`wake_reading` 以節點為單位（#14）、兩條叫不醒的語意 watch（#16）、`verify_test_nonvacuity.py` 失效突變、Phase 3 §14 其餘各題（§0.3 清單）。
9. 「層文件只有付費」的 park 是否要有付費取得的 pq2 類別（AGENTS：任何付費永不列入常規授權）。
10. 走圖第 1 型（薄層沒人讀）要不要也以「研究啟動時鑄 lead」接管道量測。
11. **（4.1c 發現）`co:openlight` 與 `co:openlight_photonics` 是同一家公司的兩個 id**（OpenLight 自家新聞稿與 Tower 6-K 用後者、Semiconductor Today 那篇用前者）：合併是 identity 決定，本 Phase 不自行處理；名冊兩筆同名，名字比對對兩家都不算（`shared_name_forms`）。另：走圖第 9 型（重複節點）只掃非公司節點，所以沒抓到——要不要把公司節點納入。
12. **（4.1c 發現）`co:nava_thailand` 疑似抽取錯誤**（Lumentum 法說逐字稿摘要的「Nava (Thailand)」可能是 Lumentum 泰國廠所在的 Navanakorn 工業區，不是公司）：它讓 `tech:cloud_transceiver_1_6t` 多了一家「供應商」；是研究題，名冊刻意不補名。
13. **（4.1 R2-b）名字比對的潛在誤中（今天 0 筆）**：中日韓字整串比對「華星光」會比到「華星光電」（CSOT）；單字別名 `Sumitomo`／`Samsung` 會比到同集團其他公司；多詞寫法不分大小寫，小寫泛稱會比到公司名。要不要收緊（例：中文名要求後面不是「電」字、集團名要求接 Electric／Electronics）留待有誤中實例再決定（L17-4）。
14. **（4.2 R2-a，既有、不是 4.2 造成）三張 graph completion 收據對不上任何現存或歸檔的抽取檔**：`poet_6_k_20260514`（188b17c9）、`sivers_ar_2025_photonics_excerpt`（97fca409）、`tower_marvell_coherent_pic_6k_2026_06_18`（a64e317f）——母檔在 a27036a 沒被改，問題更早就在。後果：日後要走更正走廊更正這三份，`intake/provenance.py::_supersede_completion_receipt` 會拒絕，而且是在寫圖**之後**才拒絕（[542] 的形狀）。要嘛找回舊版歸檔、要嘛登記這三張收據的處置；查證：R2-a 的 `task4b_receipts.py`（該次覆核 scratchpad）。
15. **（4.3）Evertiq 轉載的 HyperLight／UMC／Wavetek 聯合稿**：那份 SourceDoc 的 `origin_entity` 寫的是轉載的媒體（帶註解「轉載…聯合新聞稿」），4.3 之前靠註解被判成雙方聯合；登記 Evertiq 為媒體、聯合偵測改讀去註解字串後，`co:umc supplies_to tech:tfln_platform` 與 `co:umc partnership_with co:hyperlight` 兩條由 counterparty_joint 降為 media_relay。正解是資料：`origin_entity` 寫聯合方、`publisher` 寫 Evertiq（判斷題，走 RA／pq2），不是把註解讀回來。
16. **（4.3）泛稱 `Third-party Research` 掛在一篇學術論文的 31 條邊上**，刻意不登記（用泛稱當登記鍵，日後任何寫成這樣的文件都會被當成印證）；那 31 條邊維持待判定。正解是該抽取檔的 `origin_entity` 寫出真正的作者／機構（RA）。
17. **（4.3）插槽讀圖的 staleness 把「同級標籤拆分」算成高等級**：`prod:supernova` 插槽讀圖因供貨邊的證據標籤由待判定改成媒體轉述（rank 同級）而 stale（high）——插槽規則「供貨邊證據變動＝高等級」是為「客戶或第三方第一次具名」設的，同級改名不是那種事件。今天由 4.8 重讀處理（plan §9 第 5 項本來就預期它 stale）；要不要讓 `alpha/structure_reading/staleness.py` 比 rank 而不是比標籤，留待決定。
18. **（4.4）可替代性字表 v1 的召回只有約一半**（抽樣 42 筆：精確率 6／6、召回 6／12，baseline 報告 §21）。漏掉的寫法：`validation`（英文；中文「驗證」已在）、`sole` 接名詞（sole reducer supplier）、`the only … producer`、`limited number of suppliers`、「再找額外的供應商」。v2 候選要**換一批新樣本**再量（同一批資料考自己會讓準確率失真），量完才決定換版；在那之前 ③a 的 102／113 要讀成「上限」——約 6／36 的「沒有」其實有談。另：存量 sub 約四分之三沒有可替代性措辭撐住，是 §14 #1（sub 的消費端要不要忽略不受支持的 sub）的第一個量測。
19. **（4.6）`proceeds_equity` 稽核欄沒做**（plan §7 b「有餘裕才加」）：有序 fallback `ProceedsFromIssuanceOfCommonStock` → `ProceedsFromIssuanceOrSaleOfEquity` → `ProceedsFromIssuanceOfConvertiblePreferredStock`、`_span_class` 加 six_month 桶。4.0 覆蓋：22／8／6 檔（35 檔中）。它能補 #20 的一部分（現金流量表的發行收入通常與權益表同一筆），但也會把員工股票計畫的收入算進來——做之前先決定 #20。
20. **（4.6）大型股的 `StockIssuedDuringPeriodValueNewIssues` 多半是員工股票計畫**（NVDA 每年 Q1、Q3 有值、MRVL 每年 Q2 約 5000 萬、LRCX 每年小額；占正規化市值 0.004%–0.03%）：燈照黃、占市值 % 印在稽核層（INV-5：不設量級門檻）。要不要分開「對外募資」與「員工計畫」：companyfacts 沒有權益表那一行的 label，要讀 XBRL instance 的 presentation／label linkbase 才分得出——是 v2 問題，先看使用者讀稽核層時會不會被這幾盞黃誤導。
21. **（4.6）金額只計這一個 tag＝已知至少**：公司另用自訂 tag 標的發行不在內（INTC 窗內四季只有兩季有這個 tag 的 fact）；10-Q 與 10-K 前後 tag 不一（CRWV FY2025 年度 6800 萬 < Q1'25 13.9 億；NVDA FY2024 年度有、三份 10-Q 沒有）。後者由讀取端擋住「誤判綠」：年度大於已知季度＝`unattributed`、負的衍生季或年度小於已知季度＝`inconsistent`（R2-c #1 之後才完整——原本只擋前一種），但金額仍可能少算。
22. ~~**（4.6）正式庫的 CHECK 遷移與非增量回填**~~：✅ 2026-10-01 23:25 使用者授權後完成（baseline 報告 §22：5637 列前後相同、舊指標逐列相同、正式庫逐檔燈色與副本 73 檔相同）。留著這一條是因為操作紀律仍適用：日後再加指標時，遷移後要立刻跑非增量回填（§14 #23）。
23. **（4.6 R2-c #2／#3）逐檔的 EDGAR 抓取紀錄**：`fundamental_history` 是 insert-or-ignore，`fetched_at` 只記「第一次寫入」，讀取端分不出「這檔遷移後重抓過、真的沒有這個 tag」與「還沒重抓」，也看不到「有 fact 但期間不規則沒存」（CCXI：10-Q 2025-06-04→06-30、10-K →12-31 兩筆）。正解是每次抓取每檔留一列（ticker、fetched_at、outcome、late_metrics_supported、irregular_period 筆數）——新表＝contract 變更，要不要做由使用者定；在那之前靠「遷移後立刻跑非增量回填、看逐檔 outcome」的操作紀律。
24. **（4.6 R2-c #7，HEAD 既有）資料層用 `date.today()`**：`wipeout_for(today=…)` 的 today 只到判色層，發行金額與封面股數的取數都用 `date.today()`（`engine_c/checklist.py::get_wipeout_inputs`）。as-of 視角接上之前無影響；接上時要一併改成由呼叫端傳入（INV-6）。
25. **（4.7a 的對稱面）alpha-card CLI 第 11 節仍印舊 session 判讀的反證**：4.7a 只照 plan 點名退役個股頁的 downside／research 兩處；read model 的 `falsification.conditions` 還有兩個讀者（`briefing/alpha_view/builder.py` 的風險摘要句「研究時寫下 N 條認錯條件」與 `condition_count`），`python -m briefing alpha-card` 第 11 節也照印。要不要在來源（builder）一併退役——那會改變 read model 與 alpha-card 的輸出——留待決定；判斷檔本身原樣留。
26. **（結案）[666] 收尾與「admin 預熱 token」的位置**：[666] apply 撞 Neo4j `Forbidden`（`origin_linkage` 沒有 property token；loader 會寫的 38 個名字裡只缺它），admin 已依既有規範預熱、routine 權限 0 變動；原編號重試被執行環境權限分類器拒絕。使用者二擇一：核准重試（`scripts/apply_ra_admission.py --pq2 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d` → `commit_pending_intake` → `complete-ra 666`；partial 的 RA 實際不會到期——`expires_at` 只對 `ready` 生效，入口對同編號同 digest 的 partial 也不看到期，QueueLiveness 不檢查它〔只看帶 `dispatch_status` 的項目〕，每天會出現的是心跳「pq2 球在你手上」逐筆列出，結案 R2 C3-a／C3-a'）或 drop（還原工作樹兩檔）。另決定：`git stash` 裡的「setup 1b 預熱擴成 loader 全部屬性名＋loader SET ⊆ 預熱清單的測試」要不要 commit；入口要不要在 apply 前比對 loader 會寫的屬性名與 `db.propertyKeys()`、缺就 fail closed 指路 admin 預熱（把要人記得的規範變成會自己出現的檢查，L14）。
27. **（結案）結構表需求錨是公司層單一最短錨**：[665] 新邊讓 Lam 8 列（含供先進封裝、3D NAND）整批由 `tech:ai_switch` 換到 `tech:dram_technology`（BFS 最短 3 跳 → 2 跳）。要不要逐列（瓶頸節點側）或印多錨——`demand_chain` docstring 記 2026-09-18 實測改 dst 側會讓多數列失去錨；今天只 Lam 一家。
28. **（結案）圖遷移的事前匯出沒有單一官方命令**：live 遷移要求 backup-dir 內事先有非空 `neo4j_export.json`，只有 `backup_private.py run`（整包）產生它；`migrate_611`–`615` 與本次都另寫小腳本呼叫 `export_neo4j_payload`。要不要加只匯出圖的子命令（daily ⑯ 的工具＝sandbox impact review）或讓遷移工具自己匯出；pq2 hint 也要寫出這一步。
29. **（結案 R2 C2）③b 計數器看不到 supersede**：`query/layer_stats.py` 以「assertion id 不在凍結集合」判「新」，更正走廊重套文件沿用原 id（[668] 的 GSR e1／e2），所以 A3 定義裡的「supersede」量不到。Phase 4 影響 0（被重寫的 13 筆都不帶 sub）；[666] 重試會重寫 4 筆帶 sub 的斷言（e1／e2／e9／e10），③b 仍會印「0／0（Phase 內還沒有新增帶 sub 的）」——成功與失敗同形（L13），要在 [666] 重試前或同時修。
30. **（結案 R2 N1）發布者整家升級，轉述公司說法也被抬成外部印證**：Cignal AI 對 LITE ELS 的引文是轉述公司的說法，卻讓個股頁印「有客戶或第三方印證」，也是 ① 在 4.3 少 2 之一（另一個是 `tech:mrm_200g`，§14 #2）；220 份 SourceDoc 宣告 `origin_linkage` 的 0 份。要不要逐份宣告才升級（使用者決定，與 #2 同一個判準家族）。
31. **（結案 R2 N2）GSR 的登記類別**：`globalsemiresearch.substack.com` 登記為 industry_research（§9 第 1 項預定），另 4 個 Substack 登記為 media；cw_dfb 兩條邊升外部印證取決於它（② 的 +1 不受影響）。
32. **（結案 R2 N3）入圖副作用 packet 沒揭露**：[668] 讓 `co:nvidia.abstraction_level` device_chip → network_systems、co:nvidia／co:lumentum aliases 聯集；[664] co:axt／mat:inp_substrate aliases 聯集；[665] 讓 `lrcx_10_q_20260423.retrieved_at` 08-30 → 07-19。根源：21 個多檔 doc_id 有 18 個 `retrieved_at` 各檔互異、取值看載入順序（與 4.2e 的 section／title 同類，SourceDocSync 沒涵蓋）；節點的 `abstraction_level` 最後載入者覆寫。packet 要不要預告節點屬性的變化；`co:nvidia` 那格改回要走圖寫入（pq2）。
33. **（結案 R2 N5）走圖第 2 型沒有降級**：讀圖 ledger 讀不到時第 1 型降級成 `upstream_unavailable`，第 2 型照算、把記憶當空的（對稱面；`tests/test_graph_walk.py:152-159` 只守第 1 型）。
34. **（結案 R2 N6）互動但非走圖命中的 lead 沒有字彙**：cw_dfb lead 來源 `directed:phase4-plan-4.8`，卻帶 `classified_by=interactive:graph_walk`、`graph-walk://` URL 與 `graph_walk_subject`；`classified_by` 封閉字彙要不要加一個值（L16）。
