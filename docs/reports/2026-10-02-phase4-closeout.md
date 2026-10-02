# Phase 4 層中心來源——結案報告（2026-10-02）

> plan：[`docs/plans/2026-10-01-001-feat-phase4-layer-centric-sources-plan.md`](../plans/2026-10-01-001-feat-phase4-layer-centric-sources-plan.md)（amendment A1–A5 見 §0.4、執行偏差 #1–#17 見 §0.6、反方驗證處置見 §0.7）；
> 基準：[`2026-10-01-phase4-baseline.md`](2026-10-01-phase4-baseline.md)（§1–§20 是 4.0，§21 4.4 計數器、§22 4.6 稀釋燈與遷移、§23 4.7 驗收）；
> 4.8 收據：[`2026-10-01-phase4-step48-research.md`](2026-10-01-phase4-step48-research.md)。
> 本檔每個數字都附查證命令；數的是**圖、讀圖、敘事、等待 registry、追蹤表、走圖問句、RA 紀錄、機制存在與否**（plan §11），
> 沒有一個是「幾檔通過某個 filter」——候選板「可開」只印不驗收。
> 量測時點：2026-10-02 07:14–07:31（台北；07:31 是本報告初版 commit `f92846f`；R2 N9 更正），pq2 [663]／[664]／[665]／[668] 入圖之後、以 daily ⑬ 同一行 materialize 一次（`webapp materialize --tracked --registry-listed --structure-table --beta --graph-walk --watches --positions --structure-readings --scorecard --candidates`，81/81）。
> 「4.0」＝`c1cae28` 當下的資料與程式；個股頁與結構表的 4.0 批次＝`library/private/backups/20260930T213948Z/files.zip`（與 baseline §11 同一批；逐面板 digest 與 4.0 記下的 292 個面板鍵 0 不符）。

## 0. Phase 4 做了什麼（20 個 Step commit＋3 個結案 commit，2026-10-01 → 10-02）

| Step | commit | 一句話 |
|---|---|---|
| 4.0 | c1cae28 | 基準快照（3006 測試／195 檔＋hook 修正 1 檔；invariants 13 PASS；凍結 186 個節點與 695 筆 assertion 進 `config/graph_baselines.json`） |
| 4.1 | 09f192c、bae6870、94b60ad | evidence 分類 Q8b-B（客戶高管具名併進自報）、名字比對唯一 owner `quote_names_company`、名冊 `display_name` 99/100＋`name_aliases`＋`execution_symbol`、`_TICKER_ENRICHMENT` 退出身分解析；R2-b GO（non-blocking 12 當下處置） |
| 4.2 | a27036a、39fa9cf | packet `layer_enumerations`＋揭露、`source_type`／`origin_linkage`／`origin_role` 字彙、apply 固定入口 `scripts/apply_ra_admission.py`（四道 fail closed＋核准戳記）、SourceDoc section／title 寫回抽取 JSON＋`is_legit_multi_section` 三處共用；R2-a GO（non-blocking 8 當下處置） |
| 4.3 | a7a8df8 | `config/publishers.json`＋origin 解析唯一 owner `resolve_origin`（`classify_evidence`／`verify_citations`／插槽視角／L8 稽核共用）；新等級 `media_relay` |
| 4.4 | 5ee3424 | 可替代性字表 v1、`sub_language_in_quote` 旗標（`query/sub_language.py`）、層計數器 ①②③ 與附屬計數器（走圖 artifact `layer_stats`、心跳段 3、結構表頁首同一行） |
| 4.5 | d3dea52 | 走圖第 2 型以現行層讀圖為記憶、命中旁印 open lead；互動鑄 lead（`graph_walk:<type>`）與 `classified_by`；三個 skill 改寫、`layer_document` route |
| 4.6 | da789e4、4eac6c9 | 稀釋燈改讀 `StockIssuedDuringPeriodValueNewIssues`（最近四季、窗尾取期末精確指標）、Engine C `METRICS` CHECK 遷移工具（正式庫 10-01 23:25 經使用者授權完成）、歸零燈串接點合一；R2-c GO（non-blocking 7 當下處置） |
| 4.7 | 552c095、a56f545、543aa04、7737426、cd0de93 | 240 條舊 session 判讀反證退役不印；`ignored` 接 held_index／心跳常駐計數器；自家百分位印覆蓋率；同版敘事重複反證拒收 |
| 4.8 | 9aa8cff | （強模型、研究）四件掛 pq2 [664]／[665]／[666]／[668]；SuperNova 插槽重讀、SIVE.ST 敘事換版；當下修兩個機制缺口（`OPEN_LEAD_STATUSES`、packet 層列舉走 owner） |
| 4.9 | 35f6cd5 | 新管線 full chain（夾具版）`tests/test_layer_document_full_chain.py` 4 條；真 runtime 那份 `test_full_chain_acceptance.py` 一條未動 |
| 結案 | 16fd4a8、081f8c6、abb0105、（本 commit） | 結案前記下待決 pq2；使用者 10-02 go 後 [663]／[664]／[665] 入圖（081f8c6）、[668] intake publish（abb0105，由 `commit_pending_intake` 產生）；本報告 |

## 1. 九項 completion gate（plan §12）

| # | gate | 結果 | 查證 |
|---|---|---|---|
| 1 | `pytest -q` 全綠；測試檔數差＝新增－退役；函式層級拿掉的每一個有去向 | ✅ **3214 passed, 1 skipped**（基準 3006 passed, 1 skipped）；測試檔 **196 → 207**＝＋11（`test_apply_ra_admission`、`test_company_onboard_skill`、`test_engine_c_equity_issuance`、`test_layer_document_full_chain`、`test_layer_enumerations`、`test_layer_stats`、`test_migrate_sourcedoc_json_section`、`test_name_matching`、`test_origin_resolution`、`test_sourcedoc_sync`、`test_sub_language`）－0。函式層級（baseline §1 同一條命令）：75c4dd3 **2466** → c1cae28 2471（hook 修正那檔）→ HEAD **2599**；對 c1cae28 新增 **138**、拿掉 **10**，去向見 §3 | `python -m pytest -q`；`git grep -n -E "^\s*(async )?def test_" <rev> -- 'tests/*.py'` |
| 2 | `python -m audit invariants` 綠（含新計數器） | ✅ **14 PASS／0 FAIL（共檢查 5388 筆）**（基準 13 項；新增 `SourceDocSync`，§0.6 #8）。`SourceDocSync`：重建會遺失或不確定 0（section 0／title 0）｜圖落後 JSON 0（section 0／title 0）｜圖上有、沒有任何抽取檔 0｜讀不了的抽取檔 0；PointInTime 207/220、681/699 | `python -m audit invariants`；`--only SourceDocSync` |
| 3 | 無未解釋語意 diff | ✅ **心跳**（與 4.0 那份 `hb_base.md` 逐行，61 → 62 行）：Phase 4 程式預期——健康審查 13→14 節且 🔴 1→0（4.2e 拆段判準合一、SourceDocSync 一節）、invariants 13→14、「持股解析不到 0（使用者決定不研究 0）」（4.7b 常駐格式；7803.T 是使用者 10-01 自己刪列）、讀圖現行 4→2／低級 0→2（4.3 讓 inp_substrate、cw_dfb 兩層讀圖 stale_low）、分類層行「互動 triage 254 則」與 pq1 行「其中互動起的研究 lead 0」（4.5b）、新增「層：①…」一行（4.4）、歸零旗標黃 57→44／綠 95→89／灰 120→139 且多 `method_not_applicable` 38、`provider_missing` 19（4.6：稀釋那盞 24 黃＋6 綠 → 11 黃）；4.8 入圖——走圖「獨家且自報」2/13→0/13、pq2 球在你 1→2（多 [666]，見 §5）、結構表 223→224 條邊且前三錨 `tech:ai_switch` 110→102（見下「結構表」）；其餘是日期、run id、行情、FX、備份、X 花費、NAV／追蹤表報酬、較昨 diff、LLM 額度警告消失（今天沒有 allowed_warning）——**未解釋 0**。**個股頁**（逐面板 digest 對 4.0 批次，292 個面板鍵相同）：argument **18／73** 變——8 檔公司名換成名冊 display_name（6481.T、AMD、CCXI、IREN、SNDK、TSLA、XFAB.PA、XPEV；4.1c）、9 檔押的層讀圖「現行」→「現行（圖上只有證據等級變了）」（2455.TW、3081.TWO、4979.TWO、5016.T、5802.T、AXTI、COHR、LITE、SIVE.ST；4.3）、LITE 的 Pluggable turnkey ELS module 由「公司自己說的，但寫在正式申報文件裡」升「有客戶或第三方印證」（4.3）、COHR 的 CW DFB 那段由「只有公司自己在講」升「有客戶或第三方印證」、薄弱清單 4→3 條（4.8 [668]）、LRCX「這家公司坐的層」多「Semiconductor Manufacturing Equipment」（4.8 [665]）；SIVE.ST 的 SuperNova 插槽 4.3 變 stale、4.8 重讀後回「現行」，對 4.0 淨差 0。**brief 3／73**（AXTI、COHR、LITE）只有 `brief:priced_in` 那句的百分位數字（90→91、85→89、96→99；authority 依每日價格填的 placeholder，句子模板 0 字變）。**research 15／73** 只差每日共識 notes——**排除 `notes::` 後 73／73 有序清單逐位相同**（判準同 Phase 3）。4.7a 的 judgment 列與 `disproofs` 欄：0 檔 | `python -m crons.heartbeat --out <tmp>`；`python scripts/analyst_view_text_digest.py --per-panel`；逐行比對腳本在本 session scratchpad（`p4_panel_linediff.py`、`p4_panel_segdiff.py`） |
| 4 | 無新 dual authority | ✅ origin 解析只有 `query/origin_resolution.py::resolve_origin`（`classify_evidence`、`verify_citations`、插槽視角、`scripts/audit_sole_source_independence.py`、packet 層列舉〔4.8 當下修〕共用）；名字比對只有 `quote_names_company`（packet、計數器共用）；sub 旗標只有 `query/sub_language.py`；拆段判準只有 `loader/load_to_neo4j.py::is_legit_multi_section`（loader、健康審查、audit 三處）；執行別名只有名冊派生的 `get_execution_aliases()`；稀釋燈串接點只有 `alpha/providers/wipeout.py::wipeout_for` | `git grep -n "def resolve_origin\|def quote_names_company\|def quote_has_sub_language\|def is_legit_multi_section\|def get_execution_aliases\|def wipeout_for"` |
| 5 | 無 silent drop | ✅ 層計數器每格印 0（③b「0／0（Phase 內還沒有新增帶 sub 的）」照印、不壓成 100%）；origin 解析不到的來源另計（②旁「origin 解析不到的來源 8」）不壓成第三方；packet 核對失敗分「引文沒具名」「不在本包」兩種；稀釋燈缺席每格有 `absence_kind`（73 檔：黃 11、`method_not_applicable` 38、`provider_missing` 19、`insufficient_evidence` 5）；SourceDocSync 兩個方向分開計 | `graph_walk` artifact 的 `layer_stats`；`library/private/app/analyst_view/*.json` 的 `overview.wipeout.lanes` |
| 6 | Point-in-time | ✅ `equity_issued_value` 以 `filed` 為可用日（`tests/test_engine_c_equity_issuance.py`）；互動鑄的 lead `published_at` 為 null、`first_seen` 記鑄號時間、refs 帶 `graph_walk_as_of`；`audit PointInTime` PASS（207／220、681／699，未定日 13 份照列） | `python -m audit invariants --only PointInTime` |
| 7 | lifecycle 可達 | ✅ 本 Phase 鑄的 lead **3／3 在終局 `applied`**（`lead_21765850…` COHR 六吋＝[664]、`lead_656e8e10…` AMAT＝[665]、`lead_198ada57…` cw_dfb＝[668]）；QueueLiveness 180 項 PASS、Expiry 127 個等待全部有到期；本 Phase 沒有 park 成 `awaiting_named_disclosure` 的 lead | `pending_leads.json` 依 `graph_walk_subject`／`directed:phase4-plan-4.8` 篩；`python -m audit invariants --only QueueLiveness` |
| 8 | executable protection | ✅ apply 入口四道 fail closed＋戳記先於 apply（`tests/test_apply_ra_admission.py`）、`complete-ra` 比對戳記（`tests/test_engine_b_todo.py::test_complete_ra_refuses_an_apply_that_bypassed_the_entry`）、packet 拒收（`tests/test_layer_enumerations.py`）、媒體不升級（`tests/test_origin_resolution.py`、4.9 第 3 條）、`execution_symbol` 衝突 raise、同敘事重複反證拒收（4.7d）、CHECK 遷移列數對帳（`tests/test_engine_c_history.py`），各 Step 的變異檢查都紅（commit message 與 §0.6 逐條）。殭屍 grep **三個 0**（未列 0／腐壞 0／理由不合法 0；keep-list 283＋I 組 19）。**真實資料上的入口**：[668] 經入口 apply（戳記 `pq2_n=668`、digest 相符）→ publish `abb0105` → `complete-ra` 收據 `action:ra_637a70ee…;digest:55d97c0b…;commit:abb0105e…`；[666] 經入口蓋了戳記、apply 被 Neo4j 權限擋下（§5），沒有任何繞過入口的寫入 | `python scripts/retired_mechanism_grep.py`；`library/private/research_actions/ra_637a70ee….json` 的 `execution.approval` |
| 9 | 驗收數的是 §11 的層 | ✅ §2 每個數字都是圖、讀圖、敘事、等待 registry、RA 紀錄、機制存在與否 | — |

**另核對（plan §12）：**
- 舊 Decision Store 三個 `*.db`：sha256 與 4.0 **逐字相同** ✅（`backup_pre_v8_20260818T021452.db`、`backup_pre_v9_20260902T032020Z.db`、`decision_lab.db`；`live_choices` 0／1／1 隨 sha 相同）。
- `library/trades/trade_log.jsonl`：2 行、sha256 `861d2008…c7b8d5`＝4.0 ✅（本 Phase 沒有真實成交）。
- `git diff c1cae28 HEAD -- AGENTS.md` **為空** ✅。
- `identity/registry.py::company_id_for_ticker`：diff 裡只有一行註解提到它（「`name_aliases` 不進 `by_ticker`」），函式本體 0 行變動 ✅；`name_aliases`／`execution_symbol` 不在 `by_ticker`（`tests/test_name_matching.py`、名冊測試）。
- `library/resolutions/`（tracked 28 檔）自 c1cae28 **0 行 diff** ✅。
- `collapse_assertions`：同一批現在的 699 筆 assertion，4.0 版（`git show c1cae28:query/bottleneck.py`）與現在版各 collapse 一次——537 條邊、key 集合相同、4.0 就有的每個欄位逐欄不同 **0** ✅（現在版只多 4.3 的 `origin_linkages` 欄）。
- `python -m webapp status` 列得出 8 個 kind；materialize 81/81。

## 2. ROADMAP Phase 4 驗收①②③（A1–A3）與 §11 其他列

**驗收結論（R2 C1／C1' 更正）：①（A1）75→73（plan §11 的 4.4 基準；77→75 是 4.3 分類器變更，不算驗收）、②（A2）5→6 成立；③（A3）未量到——③a 102／113 只印、③b 0／0 沒有母體，不寫成成立。**
初版 commit `f92846f` 的標題與結案 WORK_REQUEST 寫「驗收①②③」成立，以本段為準。

| # | 驗收 | 結果 | 層 | 查證 |
|---|---|---|---|---|
| ①（A1） | 對 4.0 凍結的 186 個節點，ns==1 且供貨邊全部自報的節點數 → 下降 | ✅ **75 → 73**（驗收基準＝4.4 的 75：plan §11、baseline §21）——4.8 −2（`tech:six_inch_inp_production`：Coherent 那條多一份交易對手 AXT 8-K 來源＝[664]；`tech:semiconductor_manufacturing_equipment`：由 1 家變 2 家＝[665]）。全程 77 → 75 → 73 裡 4.3 的 −2 是分類器變更、不算驗收（`tech:els_pluggable_module` 靠 Cignal AI 轉述公司說法〔§6 #30〕、`tech:mrm_200g` 的 TrendForce 引文不具名 TSMC〔「外部印證但引文不具名供應商」15 條之一，§6 #2〕）。supply_side 絕對數 ns 0／1／2／≥3＝72／82／22／10（4.4 時 72／83／21／10；集合外新節點 0） | 圖 | `graph_walk` artifact `layer_stats.supply`；heartbeat 段 3「層：」行 |
| ②（A2） | 至少一份非供應商 origin、引文逐字具名該層 ≥2 家供應商的層數 → 上升 | ✅ **5 → 6 層**（4.4 計數器上線時 5；計數器在 4.0 還不存在——它的 origin 解析是 4.3 的 owner，`mat:inp_substrate` 等層在 4.3 登記 GSR／Reuters 時已計入，baseline §21）。結案新增 `tech:cw_dfb_laser`：Global Semi Research（登記的產業研究）同一句具名 Coherent 與 Lumentum＝[668]。「≥3 家」母體 10、「每家撐住」9、origin 解析不到的來源 8（只印） | 圖 | `layer_stats.enumeration`（`named_by_non_supplier_layers`、`hits`） |
| ③（A3） | ③a 存量帶 sub 引文不含字表語言（只印）；③b Phase 內新增／supersede 的帶 sub assertion 中含字表語言的比例（目標 100%） | ⚪ **未量到——不算成立**（R2 C1）。③a **102／113**（存量，只印；v1 字表召回約一半，讀成上限——§6 #18）。③b **0／0——無母體**：Phase 內入圖的 4 筆新 assertion（[664] 1、[665] 1、[668] 2）都不帶 sub、Phase 內被重寫的 13 筆既有 assertion 也都不帶 sub（R2 逐筆核），所以「100%」既沒達成也沒失敗。**計數器盲點（R2 C2）**：`layer_stats` 以「assertion id 不在凍結集合」判「新」，而更正走廊重套一份文件會沿用原 id（[668] 的 GSR e1／e2 就是），所以 A3 定義裡的「supersede」它看不到——Phase 4 實際影響 0，但 [666] 若重試會重寫 4 筆帶 sub 的斷言（e1／e2／e9／e10，packet 旗標 4／4 含字表語言），③b 仍會印「0／0（Phase 內還沒有新增帶 sub 的）」（§6 #29） | 圖 | `layer_stats.sub_language` |
| 走圖第 2 型 | 命中逐筆＋旁印 open lead；本 Phase 鑄的 lead ≥2 筆各到終局 | ✅ 命中 **2 → 0**（AMAT＝SME 層、COHR＝六吋 InP 層，兩筆都因入圖消失）；lead 3 筆全部 `applied`（§1 gate 7） | 走圖 × lead registry | `python -m query.graph_walk --json`；`pending_leads.json` |
| packet | 至少 1 份 applied RA 帶 `layer_enumerations` 且核對通過；入口戳記存在 | ✅ [668] `ra_637a70ee…`：`layer_enumerations[0].origin_role=industry_report`、核對通過（兩家引文具名、origin 經 owner 解析為登記的產業研究）、`execution.approval={pq2_n:668, digest:55d97c0b…}`、`complete-ra` 收據帶 commit `abb0105` | RA 紀錄 | `library/private/research_actions/ra_637a70ee0dfd81040f59f834bce574e6.json` |
| origin 解析 | 未解析 origin 73 → N；needs_review 113 → N；class 變動邊逐條；stale 的讀圖與處置 | ✅ **SourceDoc 220 份：公司 155／發布者 49／解析不到 16**（4.0 只有名冊公司一種解析：73；4.1 後 65、4.3 後 16——與 4.3 commit 當時量的相同）。剩下 16 份＝**聯合公告 8**（AMD／Anthropic、GF／MPS、IQE／Quintessent、IQE／Tower、Lumentum／Ayar、Marvell／Lumentum、Sivers／SemiNex、Tower／OpenLight——§6 #3）＋名冊外公司 5（Credo、Noveon、Sojitz、Telescent、USA Rare Earth）＋Novanta／ATI、Soitec management（Reuters 訪談）、`Third-party Research` 泛稱（§6 #16）各 1；其中 source_type＝news 的 12 份（R2 C3-b 更正：初版把 news 份數寫成聯合公告數）。**evidence 分布** 4.0 外部印證 217／needs_review 113／自報 100／自報·filing 106（536 條）→ 結案 外部印證 244／media_relay 37／needs_review 37／自報 104／自報·filing 107／counterparty_joint 8（537 條）。**逐條歸因**（R2 C3-c 更正）：同一份現在的圖，4.0 程式 vs 現在程式直接比 **80 條**。審查者對同一份圖快照逐版本歸因：4.1b（09f192c）5 條、4.1c（bae6870）16 條、4.3（a7a8df8）**61 條**、其餘版本 0。其中 UMC 兩條（Evertiq 轉載的聯合稿）在 4.1c 與 4.3 各變一次（needs_review → counterparty_joint → media_relay），直接比只算一次；cw_dfb 兩條（Coherent／Lumentum）要有 [668] 的資料，4.3 的分類才會改到它們（GSR 登記為產業研究）——5＋16＋61−2＝80。a7a8df8 commit 當時記的 59 條是對當時的圖（還沒有 [668]）。4.0 程式下由資料造成的變動＝4.8 入圖 4 條（[664] Coherent→六吋 自報→外部印證、[665] Lam→SME 新邊 自報·filing、[668] Coherent／Lumentum→cw_dfb 自報→待判定〔4.0 程式不認得 GSR〕）。讀圖：4.3 造成 3 份 stale（inp_substrate、cw_dfb 層 stale_low；SuperNova 插槽 stale high→4.8 重讀 `sr_d85d672998445c50`）；現在「該重讀 0」 | 圖 × 讀圖 | `classdiff_close.json`（scratchpad `p4_classdiff_close.py --base-rev c1cae28`）；`p4_graph_close.py`；`p4_origin_owner_close.py`；R2 逐版本歸因 |
| 稀釋燈 | 國內申報人黃 24 → N（逐檔來源與理由）；AXTI 黃；非國內 `method_not_applicable` 38 | ✅ **黃 24 → 11**（AAOI、AXTI、COHR、INTC、IREN、LITE、LRCX、META、MP、MRVL、NVDA——逐檔金額、占市值、權益表原文在 baseline §22）；**AXTI 黃**（2026-04-01～06-30 600,083,000）；`method_not_applicable` **38**；`provider_missing` 19、`insufficient_evidence` 5；正式庫遷移 5637 列前後相同、新增 263 列 | 敘事（稽核區） | `overview.wipeout.lanes[lane=dilution]`；baseline §22 |
| 240 條退役 | downside／research 面板 judgment 列 240 → 0 | ✅ **0**（`"source": "judgment"` 0 檔、`disproofs` 欄 0 檔） | 敘事 | `grep -l '"source": *"judgment"' library/private/app/analyst_view/*.json` |
| section／title | 圖上與抽取 JSON 不一致 10＋21 → 0 | ✅ **0＋0**：4.2e 寫回抽取 JSON 後「重建會遺失」30 → 0；「圖落後 JSON」11 由 pq2 [663] 經 `loader/sourcedoc_sync.py --apply-graph` 寫 11 筆 → 0（收據 `loader/manifests/sourcedoc-graph-sync-20261001.json`） | 圖 | `python -m audit invariants --only SourceDocSync` |
| ignored、覆蓋率、重複反證、`classified_by`、`layer_document` route | 符號與測試存在；變異會紅 | ✅ 4.7b `portfolio/holdings.py::load_ignored`＋心跳常駐行；4.7c 覆蓋率 31 檔有 `coverage`；4.7d 拒收；4.5b `classified_by` 封閉字彙；`config/source_routes.json` 的 `layer_document`（rung 2、verified） | 機制存在與否 | 各 Step commit 的變異紀錄 |

**只印不驗收（plan §11 末句）：** 候選板今天 可開 0｜缺 X 0｜等回落 1｜不要 0｜已持有 1｜非倍率候選 2｜邊緣無法量 0｜舊版 0｜前提失效 0｜無敘事 69。
可開為零是合法結果。

**結構表（心跳「前三錨」那一行的解釋）：** 4.0 → 今天 05:31（入圖前）結構表 223 列**逐列相同**；入圖後 224 列＝[665] 新邊 1 列，另有 **Lam 的 8 列需求錨由 `tech:ai_switch` 換成 `tech:dram_technology`**。原因是 `query/bottleneck.py::demand_chain` 從**公司**往上 BFS 取最短的錨、同一家公司每列相同（設計寫明）：4.0 是 Lam → 3D NAND 製造 → AI 算力建置 → `ai_switch`（3 跳）；[665] 讓 Lam → SME 成立，而圖上本來就有 SME → `dram_technology`，最短變 2 跳。這是 4.8 資料在既有規則下的結果，不是本 Phase 的程式；「公司層單一最短錨讓 Lam 供先進封裝／NAND 的列也掛在 DRAM 錨下」記 §6 #27。

## 3. 拿掉的測試函式與去向（c1cae28 起；plan §0 第 8 條）

| 檔 | 拿掉 | 去向 |
|---|---|---|
| `test_intake.py`：`test_finalize_is_disabled_by_default`、`…_is_manifest_scoped_and_warns_about_other_pending_files`、`…_preflight_failure_writes_no_report`、`…_propagates_second_preflight_failure`、`…_push_failure_keeps_local_commit`、`…_rejects_malicious_slug_and_local_only_before_report`、`…_two_documents_creates_one_exact_commit_and_push`、`test_pending_graph_document_cannot_finalize` | 8 | 4.2d（a27036a）刪 `intake/application.py::_finalize_research_action_impl`（production 0 呼叫端）：commit／push／preflight／local-only／slug 行為由 `tests/test_action_publisher.py` 與 prepare 的 slug 驗證守；「圖寫入失敗＝pending_graph」那一半拆成 `test_graph_failure_leaves_the_document_pending_graph` 留著（commit message 寫明） |
| `test_stock_page_phase3.py::test_candidate_input_carries_the_judgment_action_under_the_key_downside_reads` | 1 | 4.7a（552c095）judgment 來源退役：翻面成 `test_candidate_input_no_longer_hands_the_old_judgment_disproofs_to_downside`（多傳就 TypeError） |
| `test_wipeout_flags.py::test_dilution_colours_only_after_a_full_year_and_does_not_split_by_cash_burn` | 1 | 4.6（da789e4）判色改看新股發行金額：由 `test_dilution_is_amber_on_an_issuance_record_and_does_not_split_by_cash_burn` 接手「不依燒錢分」，另加 `…annual_issuance_the_quarters_cannot_place…`、`…shares_rising_without_an_issuance_record…`、`…exits_without_an_issuance_reading_are_grey…`、`…negative_correction_does_not_cancel…` 等 |

`tests/test_full_chain_acceptance.py` 一條未拿、未搬。

## 4. 執行中發現、實際做了什麼（偏差摘要；全文在 plan §0.6）

- **名冊與分類（4.1／4.3）**：#4 `display_name` 99/100（`co:nava_thailand` 刻意不補）；#5 R2-b 後補 16 家品牌短名；#10 publishers 每筆多 `seen_in`、`origin_linkages` 記逐份宣告、同級 needs_review 勝 media_relay、登記 34 筆其餘 16 個去註解字串刻意不登記。
- **contract（4.2）**：#1 apply 入口改名避開殭屍 grep；#6 SourceDoc 計數器拆兩個方向（重建會遺失＝紅、圖落後 JSON＝黃）；#7 入口放行同編號同 digest 的 partial 重試；#9 R2-a 8 條當下修。
- **計數器（4.4／4.5）**：#11 L19 字表外洩測試改「任何一行」、`layer_stats` 住走圖 artifact、②的「非供應商」含媒體（強弱另由證據欄說）；#12 `graph_walk` refs 分類、`classified_by` 封閉字彙。
- **稀釋燈（4.6）**：#13 最近四季＝期末落在窗尾往回 320 天、衍生 Q4 兩條路、湊不齊不補 0；正式庫 `--apply` 先被權限檢查擋下、改副本，使用者授權後正式庫照跑、結果相同；#14 R2-c 7 條（判色看窗內任一筆 > 0、irregular_period 進拒寫清單…）。
- **小修（4.7）**：#15 `disproofs` 欄退役不留空、`load_ignored` fail safe、心跳常駐計數器。
- **研究（4.8）**：#16 AMAT／COHR 走 additions（同文件既有逐字）、cw_dfb 走 RA（要 `layer_enumerations` 收據）、自己撤回 [667]／[669]、當下修 `OPEN_LEAD_STATUSES` 與 packet origin 走 owner。
- **結案（#17，本次）**：①[664]／[665] 的 live 遷移需要 backup-dir 內**事先**有非空 `neo4j_export.json`——pq2 hint 只寫了 `--backup-dir`，沒寫要先做匯出；本次以 `scripts/backup_private.py` 既有的 `export_neo4j_payload`／`verify_neo4j_export` 現做（與 `migrate_611`–`615` 同形），沒有官方單一命令（§6 #28）。②[666] 被 Neo4j 擋下：`cloud_routine`（`routine_writer`）沒有 `CREATE NEW PROPERTY NAME`，而 `origin_linkage` 這個屬性名從沒建過 token（Phase 4 加進 `MERGE_SOURCE_DOC` 後每份都寫 null）——見 §5。

## 5. pq2 go 的執行紀錄（2026-10-02，使用者「664 665 666 668 663 go」）

| 編號 | 結果 | 收據 |
|---|---|---|
| [663] | ✅ SourceDoc 圖落後 JSON 11 筆標題同步（writer lock 下、經編號核對） | `authority:graph_sourcedoc_title_sync;ref:loader/manifests/sourcedoc-graph-sync-20261001.json` |
| [664] | ✅ additions：加 1、刪 0、重投影 3；lead → applied | `authority:graph_migration;ref:loader/manifests/cohr-six-inch-axt8k-corroboration-20261001.json`；遷移前圖匯出 `library/private/backups/cohr_six_inch_20261001/`（2688 nodes／6081 rels） |
| [665] | ✅ additions：加 1、刪 0、重投影 9；lead → applied | `authority:graph_migration;ref:loader/manifests/semi-equipment-lam-supply-20261001.json`；備份 `…/semi_equipment_lam_20261001/`（2689／6086） |
| [668] | ✅ 入口 apply → publish `abb0105` → `complete-ra`（lead 由 complete-ra 自己記帳推到 applied、補 `focus_company_id=co:lumentum`） | `action:ra_637a70ee0dfd81040f59f834bce574e6;digest:55d97c0b…;commit:abb0105e…` |
| [666] | ⛔ **未完成，等使用者決定**——見下 | — |

**[666] 卡在哪：**
1. 入口四道檢查通過、戳記寫入（`approval={pq2_n:666, digest:26924126…, at:2026-10-01T23:08:31Z}`），apply 寫第一份文件時 Neo4j 回 `Neo.ClientError.Security.Forbidden`：*Creating new property name on database 'neo4j' is not allowed for user 'cloud_routine' with roles [PUBLIC, routine_writer]*。RA 紀錄 `state=partial`、`graph_mutated=false`——**圖一筆都沒動**；更正走廊的新抽取檔與 raw 檔已寫在工作樹（`extractions/reuters_inp_export_controls_2026_06_11.json`、`library/raw/reuters_inp_export_controls_2026_06_11.txt`，未 commit；daily 心跳段 1 會印「開跑時工作區不乾淨（2 個路徑）」；daily 沒有 git 寫入步驟，不會把它們 commit 掉）。**它實際上不會到期**（R2 C3-a 更正：初版寫「2026-10-31 到期」）——`expires_at` 只對 `ready` 生效（`intake/actions.py::_effective_state`、`_compact_expired_actions`），入口對「同編號同 digest 的 partial」也不看到期（`scripts/apply_ra_admission.py` 第 80 行）；QueueLiveness 不檢查它（只看帶 `dispatch_status` 的項目），audit 也沒有任何檢查看 partial 的 RA——每天會出現的是心跳的「pq2 球在你手上」逐筆列出 [666]（R2 覆核 C3-a' 更正：上一版寫成「兜底是…與 QueueLiveness 的 14 天」）。
2. 根因：`loader/load_to_neo4j.py::MERGE_SOURCE_DOC` 在 4.2 加了 `sd.origin_linkage = $origin_linkage`，`schema/neo4j_setup.cypher` 的 1b 預熱沒補；之前每份都寫 null（不建 token），[666] 是第一份宣告 `origin_linkage=independent` 的 RA。loader 會寫的 38 個屬性名裡只缺這一個。4.9 full chain 用 fake loader、R2-a 也只在夾具上跑，所以沒撞到（L13：驗收是產出出現在下游，不是元件會動）。
3. 已做：依既有規範（`docs/archive/2026-09-25-remote-access-architecture.md:112`「新增 SourceDoc 欄位後須由 admin 重跑 setup 預熱 token；`cloud_routine` 不應取得 `CREATE NEW PROPERTY NAME`」）以 admin 執行 setup 1b 預熱敘述（sentinel 建立後即刪、殘留 0），`origin_linkage` token 已存在；`routine_writer` 權限**沒有**任何變動。
4. 用原編號重試時，執行環境的自動權限分類器以「Security Weaken」拒絕；依其規則不換方式繞過，留給使用者。對應的程式修正（setup 1b 預熱擴成 loader 會寫的全部屬性名＋一條「loader SET 的屬性名 ⊆ 預熱清單」測試，變異：刪掉 `origin_linkage` 那行 → 紅）**沒有 commit**，停放在 `git stash`（`stash@{0}`：「等使用者決定：neo4j_setup 1b 預熱補 loader 全部屬性名＋對稱測試」）。
5. 對結案驗收的影響：0——R2 在記憶體裡模擬它入圖（不碰圖）：6 條邊升為外部印證（Reuters 那份引文具名供應商的由「媒體轉述」升級，**另有 2 條由「自報·filing」升外部印證**——初版只寫了前者，R2 N4），但 ① 73、② 6、③b 0、「外部印證但引文不具名」15 **全部不變**；packet 驗收由 [668] 滿足。另注意：重試會重寫 4 筆帶 sub 的斷言，而 ③b 計數器看不到 supersede（§2 ③、§6 #29）。

## 6. Phase 5 要決定的問題（plan §14 #1–#34；#26–#28 是結案新增、#29–#34 來自結案 R2 的條件與 non-blocking，照實帶到下一個 plan session）

**要使用者決定（契約、判準、identity、權限）：**

| # | 問題 | 結案量到的 |
|---|---|---|
| 1 | sub 的消費端要不要忽略 `sub_language_in_quote=false` 的 sub | ③a 102／113 沒有可替代性措辭撐住（字表召回約一半→上限）；忽略後的母體變化在決定前要先量 |
| 2 | 「外部印證」要不要求引文逐字具名被印證的供應商 | 「外部印證但引文不具名供應商」**15** 條（`layer_stats.ec_quote_does_not_name_supplier`）；①在 4.3 少的 2 個節點有 1 個（`tech:mrm_200g`）靠的是這種引文 |
| 3 | `counterparty_joint` 的 320 分支要不要改以 `publisher`／雙發行人宣告為準 | 解析不到的 16 份裡聯合公告 8 份（news 型別 12 份） |
| 4 | 媒體自己的報導靠 `origin_linkage=independent` 宣告升級——要不要補 `same_origin` 機械偵測 | 第一份宣告的 [666] 尚未入圖 |
| 11 | `co:openlight` 與 `co:openlight_photonics` 同一家公司兩個 id | 名冊兩筆同名、名字比對兩家都不算 |
| 14 | 三張 graph completion 收據對不上任何現存或歸檔的抽取檔 | 日後走更正走廊會在寫圖之後才被拒 |
| 17 | 插槽讀圖 staleness 把「同級標籤拆分」算成高等級 | 4.3 造成 SuperNova 插槽 stale high、4.8 重讀處理 |
| 20 | 稀釋燈要不要分「對外募資」與「員工計畫」 | 黃 11 檔裡大型股（LRCX、NVDA、MRVL、INTC、META）多半是員工計畫 |
| 23 | 逐檔的 EDGAR 抓取紀錄（新表＝contract） | 在那之前靠「遷移後立刻跑非增量回填」的操作紀律 |
| 25 | alpha-card CLI 第 11 節仍印舊 session 判讀的反證（read model 的 `falsification.conditions`） | 4.7a 只退役個股頁兩處 |
| **26** | **（結案新增）[666] 怎麼收尾**：①核准用原編號重試（token 已存在；`python scripts/apply_ra_admission.py --pq2 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d` → `scripts/commit_pending_intake.py` → `python -m engine_b.todo complete-ra 666 --digest …`），並決定 stash 裡的預熱清單＋對稱測試要不要 commit（`git stash show -p stash@{0}`）；或 ②drop [666]（工作樹那兩個檔要還原）。**「admin 預熱 token」這一步本身要不要成為入圖流程的固定前置**（例：入口在 apply 前比對 loader 會寫的屬性名與 `db.propertyKeys()`，缺就 fail closed 並指路 admin 預熱），也一併決定 | 權限面：routine writer 0 變動；token 已由 admin 預熱 |
| **27** | **（結案新增）結構表需求錨是「公司層單一最短錨」**：[665] 讓 Lam 的 8 列（含供先進封裝、3D NAND 的列）整批由 `ai_switch` 換到 `dram_technology`。要不要改成逐列（瓶頸節點側）或印多錨 | 2026-09-18 實測過改成 dst 側會讓多數列失去錨（`demand_chain` docstring）；今天只有 Lam 一家受影響 |
| **28** | **（結案新增）圖遷移的事前匯出沒有單一官方命令**：`loader/migrate_relation_rejudge.py` 等 live 遷移要求 backup-dir 內事先有非空 `neo4j_export.json`，但只有 `backup_private.py run`（整包）會產生它；本次與 `migrate_611`–`615` 都是另寫小腳本呼叫 `export_neo4j_payload`。要不要給 `backup_private.py` 一個只匯出圖到指定目錄的子命令（daily ⑯ 用的工具＝要做 sandbox impact review），或讓遷移工具自己匯出 | pq2 hint 也應寫出這一步 |
| **30** | **（R2 N1）研究機構等自產資料類別「整家」升級，轉述公司說法也被抬成外部印證**：Cignal AI 對 LITE ELS 的兩段引文是「Lumentum announced…」「Both Lumentum and Coherent recently stated…」，卻讓 LITE 個股頁印「有客戶或第三方印證」，也是 ① 在 4.3 少 2 的其中之一（closeout 初版只點名了 `tech:mrm_200g`）。根因：`publishers.json` 依類別整家升級、不逐份；220 份 SourceDoc 宣告 `origin_linkage` 的 0 份。要不要逐份宣告（例如 industry_research 也要 `origin_linkage=independent` 才升） | 與 #2（引文不具名供應商 15 條）是同一個判準家族 |
| **31** | **（R2 N2）GSR 的登記類別**：`globalsemiresearch.substack.com` 登記為 industry_research（plan §9 第 1 項預定），另 4 個 Substack 都登記為 media；[668] 的 RA review 自己寫了「單位數字的出處沒寫」。② 的 +1 不受類別影響，但 cw_dfb 兩條邊升外部印證取決於它 | 由互動 session 維護 publishers，類別是判斷 |

**不需要使用者決定、下一個 plan 照列的（結案新增，R2 non-blocking）：**
- **#29（R2 C2）③b 計數器看不到 supersede**：`layer_stats` 以「assertion id 不在凍結集合」判「新」，更正走廊沿用原 id，所以 A3 定義的「supersede」量不到。Phase 4 影響 0；[666] 重試後會讀錯（4 筆帶 sub 被重寫、仍印 0／0）。要在 [666] 重試前或同時修（L13：成功與失敗同形）。
- **#32（R2 N3）入圖副作用 packet 沒揭露**：[668] 讓 `co:nvidia.abstraction_level` 由 device_chip 變 network_systems、co:nvidia 與 co:lumentum aliases 聯集；[664] co:axt 與 mat:inp_substrate aliases 聯集；[665] 讓 `lrcx_10_q_20260423.retrieved_at` 由 08-30 倒退到 07-19。根源：21 個多檔 doc_id 有 18 個 `retrieved_at` 各檔互異、取值看載入順序（與 4.2e 的 section／title 同一類，SourceDocSync 沒涵蓋）；loader 對節點的 `abstraction_level` 是最後載入者覆寫。讀者只有覆蓋掃描顯示與 PointInTime，影響低；`co:nvidia` 那一格改回要走圖寫入（pq2）。
- **#33（R2 N5）走圖第 2 型沒有降級**：讀圖 ledger 讀不到時第 1 型降級為 `upstream_unavailable`，第 2 型卻照算、把記憶當空的（對稱面，`tests/test_graph_walk.py:152-159` 只守第 1 型）。
- **#34（R2 N6）cw_dfb lead 的標籤不一致**：來源 `directed:phase4-plan-4.8`，卻帶 `classified_by=interactive:graph_walk`、`graph-walk://` URL 與 `graph_walk_subject`；`classified_by` 封閉字彙沒有「互動、但不是走圖命中」的值（L16）。
- **#26 補記（R2 N7）**：repo 的 setup 1b 仍只預熱 2 個屬性名（修正在 stash）；現庫 38 個 token 都已存在、失敗方式是 fail closed，所以只是要盡快決定。

**不需要使用者決定、下一個 plan 照列的（plan §14 既有）：** #5（`name_aliases` 中文名覆蓋、`yfinance_symbol`）、#6（可轉換特別股算黃；員工行權等三類股數來源）、#7（本 Phase 鑄的 lead 進不進第 5 型母體；`graph_walk:*` 來源標籤走到 Phase 5 量測）、#8（Phase 2／3 帶過來未併入的）、#9（「層文件只有付費」的 park 要不要有付費取得的 pq2 類別——付費永不列入常規授權）、#10（第 1 型也以研究啟動時鑄 lead）、#12（`co:nava_thailand` 疑似抽取錯誤）、#13（名字比對潛在誤中，今天 0 筆）、#15（Evertiq 轉載聯合稿的 origin／publisher 應改資料）、#16（`Third-party Research` 泛稱掛 31 條邊）、#18（字表 v2 要換新樣本再量）、#19（`proceeds_equity` 稽核欄）、#21（金額只計一個 tag＝已知至少）、#22（✅ 正式庫遷移已完成，紀律留著）、#24（資料層 `date.today()`，接 as-of 時改由呼叫端傳入）。

## 7. 使用者動作（非阻擋）

- **[666]**：見 §6 #26（重試或 drop 二擇一；partial 的 RA 實際不會到期，見 §5 第 1 點）。
- 題材掃描已 12 天未跑（門檻 7 天）；sivers memo 超過複查週期（34／30 天）；pq1 triaged_go 20 條——都是既有計數器，與本 Phase 無關。

## 8. 結案 R2（使用者已常規 opt-in）

一位乾淨 context 的唯讀審查者，對 HEAD `f92846f` 跑 plan §12 的八項＋[666] 判斷（在 repo 外以 `git archive` 匯出 9 個版本、單一 READ transaction 抓一份圖快照，所有比較對同一份快照；結束時 `git status --porcelain --ignored`、stash、HEAD 與開始時逐位元組相同）。

**verdict：CONDITIONAL_GO，blocking 0。** 八項全部 ✅，並獨立重現：A1 路徑 77→75→73（4.0 程式＋4.0 資料／現在程式＋4.0 資料／現在程式＋現在資料）、layer_stats 逐段相同、evidence 分布與 80 條逐條轉移相同、資料面只有 4.8 入圖（695 筆凍結 assertion 除 `updated_at` 外 0 欄變動）、③a 102／113（獨立重寫旗標）、`collapse_assertions` 對「凍結 695 列」與「現在全部列」兩種輸入都 0 差異、`edge_conflicts` sub 狀態與 4.0 相同、走圖第 2 型夾具 15／15、9 個應拒收 request 全拒、入口 8 種拒絕都無寫入、稀釋燈三檔對 SEC companyfacts 手核、CHECK 遷移 5637 列逐列未改＋新增 263、`by_ticker` 兩版完全相同、pq1 20 條逐位相同、名冊 12 家來源成立、`routine_writer` 權限未放寬（唯讀 SHOW PRIVILEGES）。[666]：「不影響 completion gate」成立、不擋結案。

| 條件／發現 | 內容 | 處置 |
|---|---|---|
| **C1** | ③（A3）是 0／0 沒有母體，不得寫成「成立」 | 本報告 §2 開頭改寫驗收結論、③ 列標「未量到」；ROADMAP ✅ 時同句註明 |
| **C2** | ③b 計數器以 id 判新、看不到更正走廊的 supersede；[666] 重試會讓它讀錯 | §2 ③ 列、§5 第 5 點寫明；plan §14 #29 |
| **C3-a** | 「RA 2026-10-31 到期」與程式不符（到期只對 `ready`） | §5 第 1 點、§7 更正（執行者對照 `intake/actions.py:859`、入口第 80 行確認） |
| **C3-b** | 「聯合公告 12」應為 8（12 是 news 份數） | §2 origin 列逐份列出 16 份（執行者重跑 owner 解析確認） |
| **C3-c** | 「80＝21＋59」：現在的圖上 4.3 改 61 條，UMC 兩條與 4.1 重疊、cw_dfb 兩條要 [668] 資料 | §2 origin 列改寫逐版本歸因（執行者在 `classdiff_close.json` 確認那四條） |
| N1 | Cignal AI 轉述被抬成外部印證（LITE ELS；① 在 4.3 少 2 之一） | §6 #30 |
| N2 | GSR（Substack）登記為 industry_research，另 4 個 Substack 是 media | §6 #31 |
| N3 | 入圖副作用 packet 沒揭露（`co:nvidia.abstraction_level`、aliases 聯集、`retrieved_at` 倒退） | §6 #32 |
| N4 | [666] 另有 2 條自報·filing 會升外部印證 | §5 第 5 點 |
| N5 | 走圖第 2 型讀圖 ledger 讀不到時不降級 | §6 #33 |
| N6 | cw_dfb lead 的 `classified_by`／URL 標籤與 directed 來源不一致 | §6 #34 |
| N7 | repo setup 1b 仍只預熱 2 個（修正在 stash） | §6 #26 補記 |
| N8 | ROADMAP「做什麼」欄寫 `display_name` 100/100，實際 99/100 | ROADMAP ✅ 時註明 |
| N9 | 量測時點寫 07:14–07:40，commit 是 07:31 | 報告開頭更正為 07:14–07:31 |

需要改程式的一律不在結案 R2 之後動（同 Phase 3 結案的處置），都登記成 §6 的題。

**覆核一**（同一位審查者只核 `git diff f92846f 268e7fe`）：**CONDITIONAL_GO**。C2、C3-c ✅；③ 已不再寫成成立；N1–N9 登記正確。剩三處逐字替換（都不需使用者決定）：
- **C1'**：結論句把 ① 寫成 77→73，但 plan §11 的 A1 是「4.4 基準 → 結案」、baseline §21 寫「結案驗收對 75 算」；77→75 是 4.3 的分類器變更（els_pluggable_module 靠轉述、mrm_200g 引文不具名），不算研究推動的驗收。
- **C3-a'**：「兜底是…與 QueueLiveness 的 14 天」不成立——`audit/checks.py::check_queue_liveness` 只檢查帶 `dispatch_status` 的 pq2 項目，[666] 沒有這個欄位；這句是審查者第一輪 C3-a 原文的錯、被照抄。
- **C3-b'**：§6 第 3 題那格仍寫「聯合公告 12 份」。
- 不擋：N1 標題的「媒體／」不精確（媒體要逐份宣告 independent 才升）；三處「§5 #」是初版的錯誤引用。

執行者對照 `audit/checks.py`（`dispatch_status in {queued, researching}`／`awaiting_approval` 才檢查）確認 C3-a' 後，逐字替換 9 處（替換腳本要求每個舊字串恰好出現一次，否則整批不寫）。

**覆核二**（另一位乾淨 context 的唯讀審查者，只核 `git diff 268e7fe b3aaa58` 的三條逐字替換與其依據）：**GO，blocking 0**。C1'（第 52、57 行與 plan §11:425、baseline §21:319 一致）、C3-a'（`check_queue_liveness` 只對 `dispatch_status` 為 queued／researching／awaiting_approval 的項目檢查；todo_pool 的 [666] 沒有這個欄位；`engine_b/todo.py::actionable_items` 與心跳確實每天逐筆列出它）、C3-b'（8＋5＋3＝16）逐條 ✅；全檔殘留的舊數字只出現在更正紀錄的引用裡；§6 #2／#27／#28／#30 引用都指得到；結束時 `git status --short` 與開始相同。

**結論：結案 R2 經兩輪條件修正後 GO**（第一輪 CONDITIONAL_GO → 覆核一 CONDITIONAL_GO → 覆核二 GO；所有條件都只改文件，沒有任何程式或 authority 在 R2 之後變動）。
