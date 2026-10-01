---
date: 2026-10-01
topic: phase4-baseline
plan: docs/plans/2026-10-01-001-feat-phase4-layer-centric-sources-plan.md
step: 4.0
---

# Phase 4 Step 4.0 — 基準快照

**這份報告只有一個用途：Phase 4 各 Step 與結案時逐項比對**（plan §1、§11、§12）。現況數字會腐壞，所以連同**產生它們的命令**一起存。
本檔每個數字數的都是**圖（供給側分布、evidence class、origin 解析、sub assertion、SourceDoc）、讀圖、敘事、等待 registry、lead registry、RA 紀錄、個股頁稽核區、機制存在與否**，
沒有一個是「幾檔通過某個 filter」。

- 快照時間：2026-10-01 15:55–16:45（台北）
- HEAD：`75c4dd3`（工作區乾淨；本 Step 之前另有一個維持營運 commit `866e883`——SessionStart hook 誤報修正，不動任何本報告量到的東西）
- Python：`.venv/Scripts/python.exe`（3.14.6）；Neo4j 以 `READ_ACCESS` session、Engine C 與舊 Decision Store 以 `?mode=ro`、companyfacts 唯讀網路
- 排程：`StockBotv2-Daily` 唯一；上次 2026-10-01 05:30（Last Result 0）、下次 2026-10-02 05:30、Status Ready（`schtasks /Query /TN StockBotv2-Daily /V /FO LIST`）
- 量測腳本與全文存 scratchpad（`p4_graph_base.py`、`p4_misc_base.py`、`p4_local_base.py`、`p4_companyfacts_base.py`、`p4_dilution_base.py`；只讀，不寫任何 authority）；下表列指紋，後續 Step 以同一支腳本重跑比對
- **凍結集合進 Git**：`config/graph_baselines.json` 的 `baselines.phase4_2026_10_01`——節點 186、EdgeAssertion 695、帶 sub 的 assertion 113，**只放 id、不放引文**（部分抽取檔受儲存權限限制、不進 Git）。A1 的節點集合與 A3 ③b「新」的判準都對它算；這份集合今天重取拿不回來（L10），所以檔案是 append-only：新基準加一個鍵，舊鍵不改

| scratchpad 檔 | 內容 | sha256 |
|---|---|---|
| `p4_graph_base.json` | §2–§5 圖的全明細（186 個節點的 supply_side 與 `result_digest`、536 條邊的 evidence、220 份 SourceDoc、113 筆 sub assertion 含引文全文） | `87ff3f17…2a46` |
| `p4_misc_base.json` | §1、§8、§13、§14、§16–§18 | `91a48dac…eb590` |
| `p4_local_base.json` | §6、§11、§12、§15 | `cbb77664…1b546` |
| `p4_companyfacts_base.json` | §10 companyfacts 逐檔 tag | `c5c6288e…a89a9` |
| `p4_dilution_base.json` | §10 稀釋燈逐檔 | `3e12286d…b3be` |
| `hb_base.md` | §9 心跳全文 | `a0b28327…ad29` |
| `graph_walk.out` | §7 走圖 `--json` 全文 | `8fada771…5b6a` |
| `drain.out`／`drain_order_base.txt` | §8 pq1 drain 全文／順序 | `557bef8c…b6a`／`a1dda4cb…31d5` |
| `digest_per_panel.out` | §11 個股頁文字 digest `--per-panel` | `0dd2066a…196a` |
| `zombie_grep.out` | §16 殭屍 grep 全文（改名前） | `e73ec975…cb10` |
| `engine_c_schema_base.json` | §13 各表 `PRAGMA table_info` | `ea99fbe2…a1e2` |
| `test_functions_base.txt` | §1 `def test_` 名單 | 名單（LF）`97a43c47…07e1` |
| `missing_rungs_base.json` | §18 parked lead 的 `missing_rungs` | `40890f94…cef6` |
| `edge_conflicts.out` | §5 `edge_conflicts --json` | `8b6c8010…ed95` |

（`p4_graph_base.json` 檔指紋 `87ff3f17928bf0294b6cb912309e5a728861e642b807edf2affc4157a18e2a46`；CRLF 存檔，指紋是檔案位元組。）

## 1. 全測試基準與 invariant

`python -m pytest -q` → **3006 passed, 1 skipped, 2 warnings**（256s）；`ls tests/test_*.py | wc -l` → **195**（本 Step 前的 hook 修正 commit 再加 1 → 196，見上）。

測試函式名單：`git grep -n -E "^\s*(async )?def test_" -- 'tests/*.py'` 正規化成 `檔::函式` 排序 → **2466 個**（LF 名單 sha256 `97a43c478ecf6662b39c901bdfe54a78c404ff34d8cb0e83cf13dc12d3db07e1`）。
結案比對以 `75c4dd3` 為起點重跑同一條命令（名單可由 `git show 75c4dd3:tests/...` 重建，不依賴 scratchpad）。

`python -m audit invariants` → **13 PASS／FAIL 0**（共檢查 4911 筆）。與本 Phase 相關的兩行：

```text
PASS    PointInTime          SourceDoc published_at 207/220（94.1%）；EdgeAssertion 可定日 677/695（97.4%）；已回填 22 份且 basis 全部指得回去 [937 筆]
PASS    QueueSegments        pending_triage=0；fired_lead_requeue=1；fired_pq2_wake=0；semantic_pending_check=1；fired_reading_reread=0；narrative_rewrite=0；fired_hypothesis_check=0；approved_work_orders=0；triaged_go_leads=20；forward_view_backlog=69；graph_holes=8；pollable_watches=15；gated_gate_resolved=0；gated_no_pointer=0 [2001 筆]
```

## 2. 圖——供給側分布（A1 的基準）

節點集合＝`MATCH (t) WHERE t.type IN ['TechNode','Product','Material']` → **186 個**，id 清單凍結在 `config/graph_baselines.json`。
其中 **2 個型別與 id 前綴不一致**：`comp:humanoid_precision_actuators`（TechNode）、`tech:poet_optical_interposer`（Product）——凍結集合以型別為準；
走圖 `_layer_nodes` 以前綴（`tech:`／`mat:`／`prod:`）為準，所以 `comp:` 那一個不在走圖母體裡。邊上出現、但不在型別集合裡的 tech／mat／prod 節點：0。

| 口徑 | ns=0 | ns=1 | ns=2 | ns≥3 | 查證 |
|---|---|---|---|---|---|
| §1.1（`SUPPLIES_TO\|DEVELOPS`，公司） | 30 | **118** | 28 | 10 | 決定紀錄 §1.1 的 Cypher |
| supply_side（`query.structure.build_structure` 的 `supply_side`，只算 `supplies_to`；**A1 的唯一 owner**） | 72 | **83** | 21 | 10 | `p4_graph_base.py` |

**A1 驗收的基準：ns==1 且供貨邊全部自報（evidence ∉ {externally_corroborated, counterparty_joint}）＝ 77 個。** evidence 組合：needs_review 17、self_reported 30、self_reported_costly 30。

節點：`mat:gaas_substrate`、`mat:germanium_substrate`、`prod:amat_ags`、`prod:amat_semiconductor_systems`、`prod:blackwell`、`prod:blazar`、`prod:gf_scale`、`prod:quantum_dot_laser_epiwafer`、`prod:reliant`、`prod:spectrum_x`、`prod:starlight`、`prod:supernova`、`prod:vera_verarubin`、`tech:200mm_equipment`、`tech:3d_nand_manufacturing`、`tech:3d_scaling`、`tech:acie_segment`、`tech:advanced_packaging_gf`、`tech:ai_switch`、`tech:broadcom_3d_silicon_cpo`、`tech:cloud_transceiver`、`tech:coherent_pic`、`tech:cowos`、`tech:cpo_full_stack_test`、`tech:deposition_etch_clean`、`tech:dram`、`tech:dram_technology`、`tech:dsp_1p6t`、`tech:dwdm_laser_array`、`tech:els_pluggable_module`、`tech:essential_chips_mature_node`、`tech:fd_soi`、`tech:fiber_collimator_array`、`tech:force_torque_sensor`、`tech:foundry_logic`、`tech:garnet_faraday_rotator`、`tech:glass_cpo`、`tech:icaps`、`tech:icube4`、`tech:ime_silicon_cpo`、`tech:info_packaging`、`tech:inp_cpo`、`tech:inp_dfb_laser`、`tech:intel_foveros`、`tech:intel_glass_cpo`、`tech:isolator`、`tech:leading_edge_logic_foundry`、`tech:lidar`、`tech:light_source_chip_to_chip`、`tech:lpo`、`tech:microlens_array`、`tech:module_assembly`、`tech:mrm_200g`、`tech:multi_rail`、`tech:narrow_linewidth_laser`、`tech:ndfeb_metal_alloy`、`tech:optical_circulator`、`tech:optical_scale_up`、`tech:planetary_roller_screw`、`tech:pm_fiber`、`tech:power_gan`、`tech:pump_laser`、`tech:rf_gan`、`tech:rf_soi`、`tech:robotics_as_a_service`、`tech:samsung_xcube`、`tech:scale_across`、`tech:semiconductor_manufacturing_equipment`、`tech:sige_platform`、`tech:six_inch_inp_production`、`tech:tec`、`tech:thermal_solutions`、`tech:transceiver_800g`、`tech:wdm_laser_16ch`、`tech:wss`、`tech:xpo_form_factor`、`tech:xpu`

ns==1 但有外部印證（不在 A1 計數內）6 個：`comp:humanoid_precision_actuators`←`co:schaeffler`、`prod:ph18da`←`co:tower_semiconductor`、`tech:coupe`←`co:tsmc`、`tech:cpo_fiber_attach`←`co:coherent`、`tech:cpo_packaging_assembly`←`co:fabrinet`、`tech:silicon_photonics_chiplet`←`co:tsmc`（皆 externally_corroborated）。

每個節點的 `result_digest`（186 個）存 `p4_graph_base.json` 的 `result_digests`——4.1／4.3 改分類器後逐個比對，列出 digest 變了的節點。

## 3. 圖——evidence 與 origin 解析

EdgeAssertion **695** → canonical 邊 **536**（`_classify_edges`，與 `structure_table` 同一個 owner）：

| externally_corroborated | counterparty_joint | self_reported_costly | needs_review | self_reported |
|---|---|---|---|---|
| 217 | **0** | 106 | **113** | 100 |

`classify_evidence` 325-330 分支（origin 解析到主詞、字串另具名他家 → counterparty_joint）命中的 SourceDoc：**0 份**（4.1a 刪它之前的基準）。

SourceDoc **220** 份：origin 解析得到 **147**／解析不到 **73**（沒有 origin 的 0）；`publisher` 欄有值 178。解析不到的按 `source_type`：news 41、industry_report 24、filing 4、paper 2、ir_deck 2。
解析不到的 origin **原始字串 59 個、`_strip_annotation` 後 57 個**（plan §0.2 的「59」是前者；§0.7 裁定 publishers 以後者為鍵）。

**57 個字串的第一輪歸類**（逐條看過名冊與文件型別；**4.3 才定案登記**，未登記＝不猜）：

| 歸類 | 數 | 字串 |
|---|---|---|
| 名冊公司缺名／逗號註解／子公司名（4.1 補名冊後應解析） | 9 | `Hexagon AB, with named Schaeffler management statements`（co:hexagon）、`JL MAG Rare-Earth`（co:jl_mag）、`Nidec Drive Technology`（co:nidec 子公司）、`Novanta/ATI`（co:novanta＋子公司）、`Sivers Semiconductors, with a named ALL.SPACE customer quotation`、`Sivers Semiconductors, with a named Tachyon Networks quotation`、`Soitec management`（co:soitec；Reuters 訪談）、`Sumitomo Electric Industries`（co:sumitomo_electric）、`穩懋半導體股份有限公司`（co:win_semiconductor） |
| 聯合公告（兩家以上具名；320 分支的事） | 8 | `AMD and Anthropic`、`GlobalFoundries and Monolithic Power Systems joint announcement`、`IQE plc / Quintessent Inc. joint announcement`、`IQE plc / Tower Semiconductor`、`Lumentum Holdings Inc. / Ayar Labs`、`Marvell/Lumentum`、`Sivers Semiconductors and SemiNex Corporation`、`Tower Semiconductor / OpenLight` |
| 名冊外公司（是公司、不是發布者；不進 publishers） | 5 | `Credo Semiconductor`、`Noveon Magnetics`、`Sojitz Corporation`（客戶端）、`Telescent`、`USA Rare Earth` |
| 媒體 | 16 | `Calcalist`、`DigiTimes`、`Evertiq`、`Hunterbrook Media`、`IEEE Spectrum`、`Impact Lab`、`Mining Weekly`、`Power & Motion`、`Rare Earth Exchanges`、`Reuters`、`Semiconductor Today`、`TechNews 科技新報`、`The Next Platform`、`Zacks Investment Research`、`all-about-industries`、`optics.org` |
| 社群／個人通訊 | 6 | `Borecraft`（論壇）、`Next Financial`、`aleabitoreddit`、`damnang_substack`、`primetrading_substack`、`silicon_matter_substack` |
| 產業研究 | 6 | `Cignal AI`、`Counterpoint Research`、`Global Semi Research`、`SVRC Research`、`SemiconductorX`、`TrendForce` |
| 研究機構（非營利） | 1 | `Federation of American Scientists` |
| 政府 | 2 | `Federal Communications Commission`、`U.S. Geological Survey` |
| 學術 | 3 | `Harper Adams University 研究團隊`、`Optica Publishing Group`、`Third-party Research`（唯一那份是學術論文 `Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era`；字串本身含糊） |
| 標準組織 | 1 | `Open CPX MSA` |

needs_review 113 條邊裡，未解析 origin 出現次數前五：`Third-party Research`（31 條邊，全來自那份學術論文）、`Reuters`（9）、`Next Financial (Substack)`（6）、`Semiconductor Today`（5）、`Global Semi Research`（4）。逐邊清單在 `p4_graph_base.json` 的 `needs_review_edges`。

## 4. 名冊

`config/company_identity.json` **100 家**：`display_name` 有值 **29**、缺 **71**；`aliases` 3 家（`co:sivers_semiconductors`：SIVEF、`co:sk_hynix`：SKHY、`co:x_fab`：XFAB）。
Sivers 的名冊 id 是 **`co:sivers_semiconductors`**（research_ticker `SIVE.ST`、display_name `Sivers Semiconductors AB`、aliases `SIVEF`；沒有 execution 欄——`FRA:2DG` 今天住 `identity/execution.py::_EXECUTION_ALIASES`）。

缺 `display_name` 的 71 家：`co:aehr_test_systems`、`co:agility_robotics`、`co:all_space`、`co:amd`、`co:ansys`、`co:anthropic`、`co:apollo`、`co:apple`、`co:applied_materials`、`co:arista`、`co:ayar_labs`、`co:blackstone`、`co:boston_dynamics`、`co:cadence`、`co:casela_technologies`、`co:celestial_ai`、`co:churchill_capital_xi`、`co:coreweave`、`co:corning`、`co:enablence_technologies`、`co:ewellix`、`co:google`、`co:gxo_logistics`、`co:hexagon`、`co:humanoid`、`co:hyperlight`、`co:hyundai_mobis`、`co:ime_cas`、`co:intel`、`co:iren`、`co:jabil`、`co:jl_mag`、`co:jx_advanced_metals`、`co:leaderdrive`、`co:lessengers`、`co:lightium_ag`、`co:liteon`、`co:lumilens`、`co:microsoft`、`co:mips_holding`、`co:mp_materials`、`co:nava_thailand`、`co:nebius`、`co:newphotonics`、`co:nidec`、`co:niron_magnetics`、`co:novanta`、`co:o_net_technologies`、`co:openai`、`co:openlight`、`co:openlight_photonics`、`co:oracle`、`co:proterial`、`co:samsung`、`co:sandisk`、`co:schaeffler`、`co:seminex`、`co:shuanghuan_driveline`、`co:soitec`、`co:spacexai`、`co:sumitomo_electric`、`co:tachyon_networks`、`co:tesla`、`co:texas_instruments`、`co:thk`、`co:umc`、`co:unitree`、`co:win_semiconductor`、`co:x_fab`、`co:xpeng`、`co:zhongji_innolight`。
⚠ `co:openlight` 與 `co:openlight_photonics` 兩筆都缺名、看起來是同一家——4.1c 補名時要先答「是不是同一家」，是的話那是 identity 決定（不在本 Phase 自行合併）。

## 5. 圖——sub（A3 ③a 的母體）

| 項 | 數 |
|---|---|
| EdgeAssertion 帶 `substitutability` key | 133 |
| 其中值非 null（**③a 母體，id 凍結**） | **113** |
| 其中 sub≥4 | 70 |
| 113 筆的 QUOTES 連結／不同 Source 節點／不同引文 | 203／163／161（≥190 字 72 段） |
| 113 筆中沒有任何 QUOTES 的 | 0 |
| 圖上 Source 節點／全部 QUOTES 連結 | 1074／1054 |

`python query/edge_conflicts.py --json`：帶 sub key 的邊 104——auto **81**／open **8**／empty **15**（empty＝只帶 null）；113 筆非 null 收斂成 89 條邊＝auto＋open；`library/resolutions/` **28 份**。113 筆的 id、edge_key、值與引文全文存 `p4_graph_base.json` 的 `sub_nonnull`（引文不進 Git）。

## 6. 讀圖、敘事、等待

`alpha.providers.structure_readings.reading_status_rows`（圖那一側）：4 份現行讀圖，**全部 `current`、`needs_reread_by_graph=False`**；供給側每條邊今天的 evidence（4.1／4.3 後逐份對照）：

| 讀圖 | 節點／單位 | 供給側（evidence） |
|---|---|---|
| `sr_bac985bacbea64b7` | `mat:inp_substrate`／layer | axt self_reported_costly、jx_advanced_metals needs_review、sumitomo_electric needs_review |
| `sr_d49b81b6465e1181` | `tech:cw_dfb_laser`／layer | coherent self_reported、landmark self_reported_costly、lumentum self_reported、luxnet self_reported_costly、sivers externally_corroborated、vpec self_reported_costly |
| `sr_268d2fd79db629ff` | `prod:supernova`／socket | sivers needs_review |
| `sr_35ca0ce58617d5f6` | `prod:els_8ch_module`／socket | enablence self_reported、o_net externally_corroborated、sivers externally_corroborated |

現行 v2 敘事 4 份（`alpha.narrative.contracts.select_brief`）：

| 檔 | brief_id | rides | 反證條數 |
|---|---|---|---|
| AXTI | `ib_3100d4c6f394b679` | `mat:inp_substrate`／layer | 5 |
| COHR | `ib_1ddf59d7c3cf4fe4` | `tech:cw_dfb_laser`／layer | 0 |
| LITE | `ib_bc97e6ccde70f264` | `tech:cw_dfb_laser`／layer | 0 |
| SIVE.ST | `ib_cb5642b674f08e14` | `tech:cw_dfb_laser`／layer、`prod:supernova`／socket、`prod:els_8ch_module`／socket | 5 |

`python -m engine_b.event_watch counters`：

```json
{"active": 125, "t1_date": 2, "t0_passive": 87, "t2_pollable": 15, "wake_pq2": 0, "wake_lead": 79, "wake_hypothesis": 3, "stalled": 42, "fired_unconsumed": 2, "expired": 0, "semantic_active": 36, "semantic_pending_check": 1, "semantic_flagged": 1, "wake_disproof": 36, "wake_reading": 5, "wake_brief": 2, "semantic_unreachable": 3, "expiry_decision_pending": 0, "expiry_thesis_review_pending": 0, "expiry_reread_pending": 0, "expiry_rewrite_pending": 0, "trace_expired_closed": 0, "trace_expired_closed_today": 0, "expiry_unresolved": 0}
```

## 7. 走圖

`python -m query.graph_walk --json`（圖 2688 個節點 id）：

```text
薄層沒人讀 4／13｜獨家且自報 2／13｜供給側未填 2／7｜讀圖該重讀 0／4｜lead 點名不在圖 7／13｜供貨走不到錨 6／51｜沒人供應 9／129｜建模待補 10／181｜重複節點 23／188
```

- 第 1 型 4 筆：`tech:hbm`、`tech:semiconductor_manufacturing_equipment`、`tech:six_inch_inp_production`、`tech:uhp_laser`。
- **第 2 型 2 筆**：`tech:semiconductor_manufacturing_equipment`←`co:applied_materials`（自報·filing；需求 `co:globalfoundries depends_on`，sub 4）、`tech:six_inch_inp_production`←`co:coherent`（供應商自報；需求 `tech:cw_dfb_laser depends_on`，sub 4）。
- 第 3 型 2 筆：同上兩個節點。第 5 型 7／13 **恆亮**（`always_on=True`）。

## 8. lead

`library/leads/pending_leads.json` **1186 則**：triaged_no_go 597／parked 484／applied 85／triaged_go **20**（`python -m engine_b.cli counts`）。
source 前綴前幾名：x 523、edgar 440、mfn 66、decompose 35（另有 `decompose-*`、`system_decompose` 等變體）、sivers 28、yahoo 26；`graph_walk:` 前綴 **0**（4.5／4.8 之後應出現）。
`python -m engine_b.cli drain --limit 500 --json` → **21 項**，順序（kind、lead_id、priority 三欄）sha256 `a1dda4cba5228f465c89ee98284594d400de667e7cf275d6696443f01d7161d5`——**4.1 R2-b 的 pq1 排序逐位比對對這一份**。

## 9. 心跳

`python -m crons.heartbeat --out <scratchpad>\hb_base.md`（不帶 `--write-snapshot`）→ sha256 `a0b28327b0c083636a1c6e009febbc02ea8290c158f53629d2f99f2ca5b7ad29`。段 3 的走圖行與上面 §7 同一行；「pq2 球在你手上 1」＝[632]；「距上次掃題材 11 天」。

## 10. 稀釋燈與 companyfacts（4.6 的前提）

73 份個股頁的稀釋燈（`p4_dilution_base.py`，讀 materialize 產物）：

| filer_class | 檔數 | 燈 |
|---|---|---|
| domestic_quarterly（10-K／10-Q 國內申報人） | 35 | **黃 24**／綠 6／灰 5（`insufficient_evidence`：CCXI、CRWV、GOOGL、IREN、META），來源全是 `sec_cover_shares` |
| foreign_annual | 8 | 灰 8（`insufficient_evidence`） |
| taiwan_monthly | 7 | 灰 7（`insufficient_evidence`） |
| unknown | 23 | 灰 23（`insufficient_evidence`） |

AXTI 黃（封面股數 +42.2%，2025-08-01 → 2026-08-03）、AAOI 黃（+52.3%）、LITE 黃（+28.3%）、COHR 黃（+26.0%）。

companyfacts（`fetchers.edgar.ticker_cik_map` → `fetchers.edgar_xbrl.fetch_companyfacts`，35 檔全部取得、0 錯誤、沒有任何 tag 多單位）：

| us-gaap tag | 35 檔中有 |
|---|---|
| `StockIssuedDuringPeriodValueNewIssues`（4.6 用） | **28** |
| `ProceedsFromIssuanceOfCommonStock` | 22 |
| `ProceedsFromIssuanceOrSaleOfEquity` | 8 |
| `StockIssuedDuringPeriodSharesStockOptionsExercised` | 28 |
| `StockIssuedDuringPeriodSharesNewIssues`（plan 原指定、已棄用） | 10 |
| `ProceedsFromIssuanceOfConvertiblePreferredStock` | 6 |

**4.6 前提（覆蓋 ≥20 檔）成立：28／35。** 但要帶著兩個事實進 4.6：
① 28 檔裡只有 **13 檔**在最近 400 天內有這個 tag 的 10-K／10-Q fact（AAOI、AXTI、CCXI、COHR、CRWV、INTC、IREN、LITE、LRCX、META、MP、MRVL、NVDA）；其餘 15 檔的 tag 只出現在舊申報（AMD 停在 2016、AEHR 2017…）——「公司仍按時申報、但窗內沒有這一行」與「從來沒有這個 tag」要分開處理（plan 的 `provider_missing` 只對後者）。
② 沒有這個 tag 的 7 檔：AAPL、AMAT、BX、JBL、MSFT、ORCL、TXN。
三檔手核：AXTI 2026-04-01～06-30 **600,083,000**（10-Q）、FY2025 93,550,000；AAOI 2026 H1 **1,028,207,000**（Q2 單季 645,758,000）；LITE 2025-12-28～2026-03-28 **1,999,700,000**（可轉換特別股，plan 預設算黃）。另 COHR 2026-01-01～03-31 1,998,735,000（plan 沒提到，4.6 逐檔列理由時要寫）。

## 11. 個股頁

`python -m webapp status`：Materialized Analyst Views **73 份**（ready 3：AXTI、COHR、LITE）；state artifacts **8 份**（structure_table、beta、graph_walk、watches、positions、structure_readings、account_scorecard、candidates）。
`python scripts/analyst_view_text_digest.py --per-panel` → `# TOTAL 5f7211dc40a76414 73 檔`（全文 sha256 見上表）。
**舊 session assessor 反證：downside 面板 `source="judgment"` 240 列、research 面板 `disproofs` 240 條，分布在 63 檔**（4.7a 的基準 → 0）。

## 12. Sheet 持股解析

唯讀讀 Sheet（`fetchers.gsheets.read_portfolio_values` → `parse_portfolio` → `portfolio.holdings.resolve_holdings`）：Sheet 標題列**沒有 `company_id`／`neo4j_id` 欄**。
逐列解析來源：`sheet_company_id` 1（**FRA:2DG**——那個 id 是 `_TICKER_ENRICHMENT` 注入的 `neo4j_id`，不是 Sheet 自帶）、`registry_ticker` 4（GOOGL、MU、NVDA、TSLA）、解析不到 13 列（10 個代號：0050.TW、006208.TW、00631L.TW、00981A.TW、2330.TW、DRAM、LON:VWRA、QQQ、SOXX、TQQQ——ETF 與 beta）。
⚠ `library/private/app/state/candidates.json` 仍列 `unresolved: ["7803.T"]`——那是今天 05:30 materialize 的產物，使用者白天才刪 Sheet 那一列；今天唯讀解析已沒有 7803，下一次 materialize 自然消失。

## 13. Engine C

`library/private/runtime_pointer.json` → `engine_c/stockbot-engine-c-private-v1-458db5270ee2.db`（`?mode=ro`）。各表列數：

| 表 | 列數 |
|---|---|
| price_history | 53231 |
| consensus_estimates | 6656 |
| financial_snapshots | 3690 |
| consensus_coverage_observations | 3687 |
| fundamental_history | **5637** |
| technical_observations | 1378 |
| monthly_revenue_observations | 343 |
| manual_observations | 336 |
| manual_fields | 218 |
| corporate_actions | 9 |
| sqlite_sequence | 4 |

`fundamental_history` 各 metric：cash 1290、revenue_quarter 1230、operating_income_quarter 1133、shares_outstanding_cover 595、total_debt 517、revenue_annual 456、operating_income_annual 416。
CHECK 原文（`sqlite_master`）——4.6 遷移前後對照：

```sql
metric TEXT NOT NULL CHECK (metric IN ('revenue_quarter', 'revenue_annual', 'operating_income_quarter', 'operating_income_annual', 'cash', 'total_debt', 'shares_outstanding_cover')),
```

`engine_c.history_backfill.METRICS` 7 值與 CHECK 逐字相同。全部表的 `PRAGMA table_info` sha256 `ea99fbe2144bd0c05d1bcff01a9a5692e23be625eac020af78dc38e010bca1e2`——4.6 遷移後，`fundamental_history` 以外的表必須算出同一份。

## 14. RA 紀錄與 pq2 池

`library/private/research_actions/`：**138 筆紀錄**（pushed 131／partial 5／expired 2；目錄 139 項＝138 筆＋`locks/`）。池裡 `ra_admission` **137 筆**（go 125／drop 12），全部已 resolve。
7 筆未 pushed 對應的 pq2 編號（全是 drop——4.2d 的新入口對它們一律拒絕，是既有語意）：

| RA | state | pq2 |
|---|---|---|
| `ra_032b64cc05094380e9046696c91142be` | partial | [360] drop |
| `ra_2081f7886d5606bbc108f1cf7190acef` | partial | [376] drop |
| `ra_59fd7818573f6b4a8e0b03f92cc03ced` | partial | [94] drop |
| `ra_5ee3b69676bf9ea15225ea6034edf819` | partial | [88]／[90]／[92] drop |
| `ra_9a8419e6ff52f2c414d3d928504bc491` | partial | [361] drop |
| `ra_50f3ddb6cfe718afd7e2ef8b0481e686` | expired | [80]／[81] drop |
| `ra_8b38e6ef1e15502479c28557851c018a` | expired | 池裡沒有對應編號 |

## 15. SourceDoc section／title 與抽取 JSON（4.2e 的基準）

圖上 220 份、抽取 JSON 243 個檔（`source_doc.doc_id` 去重 220 個，兩邊集合相同）；多檔 doc_id **21 個**；圖上有 section 的 **32 份**。

**section 不一致 11 份**：只存在圖上 10 份——`aaoi_10_k_20260227_competition`、`fas_dod_mp_partnership_2025_07_15`、`jlmag_ar2022_hkex`、`lynas_q1_fy26_quarterly_2025_10_30`、`meta_vistara_isca_2026`（10-01 剛在圖上還原，JSON 仍是 null）、`miningweekly_lynas_terbium_2025_06_18`、`nvidia_photonics_pr_2025_03_18`、`schaeffler_humanoid_partnership_pr_2026_01_13`、`svrc_state_of_robotics_2026_us`、`thehumanoid_schaeffler_supply_deal_2026`；兩份抽取檔互異 1 份——`sivers_ar_2025_photonics_excerpt`（`sivers_ar_2025.json` null、`sivers_ar_2025_photonics_excerpt.json` photonics）。

**title 不一致 19 個 doc_id**（JSON 之間不同或圖上不是其中之一）：`Broadcom_q2fy26_cpo`、`Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era`、`Nvidia_q1fy27`、`agility_robotics_sec_investor_presentation_2026_06`、`amat_10_k_20251212`、`gfs_20_f_20260227`、`iqe_tower_inp_epiwafer_agreement_2026_06_15`、`lrcx_10_k_20250811`、`lrcx_10_q_20260423`、`lumentum_q2fy26_cpo`、`meta_vistara_isca_2026`、`mops_4979_annual_report_2025`、`mu_10_q_q3fy2026_20260625`、`nvda_8k_ex991_20260826_q2fy27_pr`、`nvda_lumentum_partnership_pr_2026_03_02`、`nvidia_photonics_pr_2025_03_18`、`poet_6_k_20260514`、`tower_marvell_coherent_pic_6k_2026_06_18`、`tsem_openlight_cadence_pdk_6k_2026_08_11`。
多檔 doc_id 中標題本來一致的 2 個：`mrvl_10_k_fy2026_20260311`、`sivers_ar_2025_photonics_excerpt`。
⚠ 3 份 base 抽取檔是 git-ignored（`broadcom_q2fy26_cpo.json`、`nvidia_q1fy27.json`、`lumentum_q2fy26_cpo.json`——逐字稿，儲存權限）：4.2e 改它們只改本機檔、不進 Git；loader 讀的就是本機檔，所以計數器照樣歸零，但 fresh clone 沒有這三份（本來就沒有）。

**計數器基準：section 11＋title 19**（plan 寫 10＋21，更正見 §19）。

## 16. 不變的東西（結案要逐字相同）

舊 Decision Store（A5，只准讀）：

```text
backup_pre_v8_20260818T021452.db sha256=e887b3d458621e4cd7bb66913690d47d263d7188f9bbc1bacb4bc16ec57de350 live_choices=0 bytes=4804608
backup_pre_v9_20260902T032020Z.db sha256=af3dc690ce836b6026d86946c388d19f1500139287469f0f9fbe8711c4819d39 live_choices=1 bytes=11038720
decision_lab.db sha256=e99d1c79fd22dbe1099f30c4e06f2d1188f26a8cbfa987a27cd8842530951810 live_choices=1 bytes=16166912
```

與 Phase 0–3 基準三檔逐字相同。`library/trades/trade_log.jsonl`：**2 行**，sha256 `861d2008de8cdaa80c885b4e06da11ee0a2bf188526836dddcc1701a6bc7b8d5`。
`git diff 75c4dd3 HEAD -- AGENTS.md` 結案時應為空；`library/resolutions/` 28 份結案時應不變。

殭屍 grep（`python scripts/retired_mechanism_grep.py` 驗收段）：**改名前 未列 1／腐壞 0／不合法 0**——未列那 1 筆是 plan 檔本身：plan 指定的新 apply 入口檔名與 Phase 2 退役的遠端寫入工具同名，I 組命中 9 處（全部是那個檔名）。本 commit 把入口改名 `scripts/apply_ra_admission.py`、plan 9 處同步，**改名後三個 0**（plan §0.6 偏差 #1）。

## 17. 呼叫端清單（4.1d、4.2d 的起點）

`git grep -n "_EXECUTION_ALIASES\|_TICKER_ENRICHMENT\|_TICKER_ALIASES\|_YFINANCE_SYMBOL_ALIASES\|neo4j_id"` 的程式檔：`engine_b/cli.py`、`fetchers/gsheets.py`、`identity/execution.py`、`portfolio/holdings.py`、`tests/test_candidates.py`、`tests/test_record_trade_receipt.py`（另有 ROADMAP、plan、closeout 等文件）。
`git grep -n "_apply_research_action_impl\|_finalize_research_action_impl"` 的程式／活文件：`intake/application.py`、`loader/migrate_entity_dedup_20260904.py`、`prompts/intake_protocol.md`、`scripts/retired_mechanism_grep.py`、`skills/daily-brief/SKILL.md`、`skills/lead-intake/SKILL.md`、`tests/test_intake.py`、`tests/test_intake_reconciliation.py`、`tests/test_research_actions.py`。全文在 scratchpad `alias_callers.txt`、`apply_impl_callers.txt`。

## 18. 選源路徑表

`config/source_routes.json` **13 條**：local_library(1)、sec_edgar／szse／sse／mops／mfn／rns／dart／edinet／hkex(2)、issuer_site(3)、alternate_primary(4)、authorized_syndication(5)。沒有層文件 route。
parked lead 有 ticker 的 405 則，`missing_rungs`（以 refs 的 `source_routes_attempted` 為已走）分布：缺 5 條 404 則、缺 4 條 1 則——4.5 加 `layer_document` route 後預期多一條（八欄要寫）。

## 19. 對 plan §0.2 的更正（4.0 實測）

| plan 原寫 | 實測 | 影響 |
|---|---|---|
| 未解析 origin「59 個不同字串」 | 原始 59、`_strip_annotation` 後 57 | 4.3 以 57 個為鍵（§0.7 裁定②） |
| RA「既有 139 筆」 | 138 筆（plan 自列分項 131＋5＋2＝138；目錄 139 項含 `locks/`） | 無 |
| 「單份 SourceDoc 列 ≥2 家的層 10」 | supply_side 口徑 8 層、`supplies_to\|develops` 口徑 15 層（≥3 家都是 4） | A2 正式基準本來就在 4.4 名冊補齊後重量 |
| `nvidia_photonics_pr_2025_03_18`「沒有任何抽取 JSON」 | 有兩份（`nvidia_photonics_ecosystem_pr_2025_03_18.json`、`nvidia_photonics_pr_2025_03_18_fabrinet_addendum.json`；檔名不等於 doc_id），section 都是 null | 4.2e 直接寫回，不需重建或登記不可重建 |
| section／title 不一致「10＋21」 | 11（只在圖上 10＋兩份 JSON 互異 1）＋19 | 4.2e 計數器基準 11＋19 → 0 |
| Sivers（`co:sivers`） | 名冊 id 是 `co:sivers_semiconductors` | 4.1c 的 `execution_symbol` 加在這一筆 |
| 新入口 `scripts/` 下的 apply 腳本名 | 與退役遠端工具同名、撞殭屍 grep I 組 | 改名 `scripts/apply_ra_admission.py`（§0.6 #1） |

## 20. 本 Step 的 L11-6 ④

「如果這份基準是錯的，最先壞掉的是哪一筆」——A1 的 77 個節點與 A3 的 113 筆 id 若凍結錯，4.4 的計數器會對錯的集合算、結案驗收跟著錯。去看了：凍結的 186 個節點與 §1.1 Cypher 的 186 個逐一相同；
113 筆非 null 的 sub assertion 收斂成 **89 條邊，恰好是 `edge_conflicts` 的 auto 81＋open 8**（0 條對不上），empty 15 條是只帶 null 的邊、不在母體——兩個來源一致。
（初稿寫成「113 筆 → 104 條」，跑這條比對時被推翻、已更正：104 含 empty。）
