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
`python -m engine_b.cli drain --limit 500 --json` → **21 項**（20 條 lead＋1 筆 `fired_watch_pending`〔ew_0152_2026-09-30〕），順序（kind、lead_id、priority 三欄）sha256 `a1dda4cba5228f465c89ee98284594d400de667e7cf275d6696443f01d7161d5`——**4.1 R2-b 的 pq1 排序逐位比對對這一份**。
算法（R2-b 指出要寫清楚，否則重算對不上）：每項一行 `f"{kind}\t{lead.lead_id}\t{priority}\n"`、tab 分隔、LF 換行；**缺欄位時寫 Python 的 `None`**（那一筆 watch 寫成 `fired_watch_pending\tNone\tNone`）。

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

## 21. Step 4.4 常駐計數器的基準（A1／A2／A3；2026-10-01，4.1–4.3 之後）

查證：`python -m webapp materialize --graph-walk` 後讀 `graph_walk` artifact 的 `layer_stats`；同一行字在心跳段 3 與結構表頁首（`python -m crons.heartbeat`、APP `#/structure-table`）。

```
層：①獨家且全自報 75（凍結 186 個節點；集合外新節點 0）｜②非供應商來源列舉 ≥2 家 5 層（≥3 家母體 10；每家撐住 9；origin 解析不到的來源 8）｜③a sub 引文不含可替代性語言 102／113（存量）｜③b 新增帶 sub supported 0／0（Phase 內還沒有新增帶 sub 的）｜外部印證但引文不具名供應商 15｜字表 v1·narrow
```

- **①（A1）＝ 75**：凍結 186 個節點 ns 分布 0／1／2／≥3 見 artifact；§2 的 77 是 4.0 當下。離開集合的兩個節點**都是 4.3 登記發布者造成的**（4.1 為 0）：`tech:els_pluggable_module`（Lumentum 唯一供貨邊，自報·filing → 外部印證，Cignal AI）、`tech:mrm_200g`（TSMC 唯一供貨邊，待判定 → 外部印證，TrendForce）——⚠ 後者是「外部印證但引文不具名供應商」15 條之一（§14 #2）：①少 1 有一半是靠一段沒點名 TSMC 的引文。結案驗收對 75 算，並照印這一條。查證：scratchpad `p44_a1_diff.py`。
- **②（A2）＝ 5 層**：`mat:inp_substrate`（GSR、Reuters 各列舉 AXT／JX／Sumitomo）、`tech:external_laser_source`（Sivers 年報列 O-Net、POET）、`tech:rv_reducer`（Next Financial 列 Nabtesco、雙環）、`tech:tfln_platform`（Evertiq 轉載列 HyperLight、UMC）、`tech:uhp_laser`（Cignal AI 列 Coherent、Lumentum）。plan §9 第 1 項的兩個預期（Sumitomo／JX 兩條邊升為外部印證、②這一層由 0 變 1）在 4.3 登記 GSR 與 Reuters 時就已發生——Reuters 登記為媒體也算「非供應商來源」（列舉是列舉，證據強弱由 evidence 欄另說）；4.8 第 1 項剩下的是 Reuters 那份要不要宣告 `origin_linkage=independent`，它影響的是邊的證據等級，不影響②。
- **③a（A3）＝ 102／113**：113 筆每一筆都有逐字（0 筆缺）；寬版字表是 97／113——寬窄差 5 筆，主因不是字表寬窄。

### 準確率抽樣（只印，不放閘）

樣本：`edge_conflicts` sub 為 open 的 8 條邊＋auto 前 20 條邊（edge 字典序）＝ 42 筆 assertion；執行者逐筆讀引文判「這段在談可替代性／替代品認證／排他性嗎」，再對照旗標。腳本與逐筆輸出在 scratchpad（`p44_sample.py`／`.out`）。

| | 人判「有談」 | 人判「沒談」 |
|---|---|---|
| 旗標（窄版）有 | 6 | 0 |
| 旗標（窄版）沒有 | 6（其中 2 筆是弱例：「找到 AXT 額外的基板供應」） | 30 |

- **精確率 6／6**：旗標說「有」時都對（Reuters「不會輕易換供應商、換要很長的認證週期」、GF 20-F「不易替代」「single-sourced」）。
- **召回 6／12**（排除兩個弱例 6／10）：漏掉的寫法——`supplier validation`／`sole reducer supplier`（Next Financial）、`the only active domestic producer`（FAS）、點名替代供應商＋市占（Next Financial 的雙環）、`a limited number of suppliers`（GF 20-F）、「再找額外的基板供應」（Lumentum 法說）。
- 寬版只多抓到 1 筆（GSR「three players control over 90%」），而那是集中度措辭，人判不算——所以 v1 用窄版。
- 讀法：「沒有」的那一側約 6／36 其實有談，所以 102 偏高；打折後存量仍約四分之三的 sub 沒有可替代性措辭撐住——多數是法說／新聞稿的產品描述、產能、營收成長、「industry leader」「de facto standard」。
- **不拿這批樣本改字表**（同一批資料考自己會讓準確率失真）；v2 候選記入 plan §14 #18，換一批新樣本再量。

## 22. Step 4.6 稀釋燈與 CHECK 遷移（2026-10-01；先在唯讀副本上跑，使用者授權後正式庫照跑、結果相同）

**正式庫（2026-10-01 23:25 台北，使用者授權後）**：`--apply` 收據 `library/private/engine_c/backups/…pre-metrics-20261001T152504Z.{db,json}`——
5637 列、遷移前後內容摘要 `6a8c5aa2…` 相同；互動 writer lock 下非增量回填（EDGAR written 41／no_cik 29／lagging 3〔CDNS、TSM、UMC〕、
拒寫 17 組、`irregular_period_facts` 4〔全是 CCXI：營業利益與發行金額各兩筆，2025-06-04 成立起算的 26 天、210 天期間〕、`late_metrics_skipped` 0）。
對備份唯讀核對：舊 7 個指標 5637 列逐列相同（被改或被刪 0、新增 0）、封面股數 595 列相同、`PRAGMA table_info` 指紋仍是 §13 的 `ea99fbe2…`；
新指標 263 列（季 193、年 70；17 檔；filed＝fetched 日期 0、filed 空 0；USD 262／CNY 1；衍生 FY−9M 45、FY−ΣQ1..Q3 13）；
**正式庫逐檔燈色與下面副本的結果 73 檔完全相同**（R2-c 收尾的判色改動前後，副本 73 檔燈色與缺席種類也完全相同）。

以下是使用者授權前的副本試跑（正式庫的 `--apply` 當時被執行環境的權限檢查擋下）：
以 `?mode=ro` 連線、sqlite3 backup API 從正式庫複製（正式庫只讀、一字不寫）→ 對副本跑遷移 CLI（`--db <副本>`：dry-run → `--apply` → 再跑一次印「不需要遷移」）
→ 對副本跑非增量 EDGAR 回填（`--db <副本> --no-prices`，跑兩輪：第二輪驗新衍生路，`ON CONFLICT DO NOTHING` 只補新列）
→ 行程內把 Engine C 連線與市值正規化的庫路徑指向副本，逐檔走真正的串接點 `alpha.providers.wipeout.wipeout_for`。
改前＝今天 05:34 daily 的 analyst_view 產物（§10 讀的同一批）。正式庫遷移後照 OPERATIONS「Engine C」段三行重跑，數字應與本節相同（同一批 companyfacts、同一段程式）。

**遷移（副本）：** `fundamental_history` 5637 列，遷移前後列數與內容摘要相同（`6a8c5aa2…`）；CHECK 由 7 個字彙變 9 個（多 `equity_issued_value_quarter`／`_annual`）；
索引 `idx_fundamental_history_asof` 重建；全部表的 `PRAGMA table_info` 指紋遷移前後都是 §13 的 `ea99fbe2…`（CHECK 不在 table_info 裡，欄位一欄不變）。
**回填（副本）：** EDGAR written 41／no_cik 29／lagging 3（CDNS、TSM、UMC），`late_metrics_skipped` 0，拒寫 17 組全是舊指標。
**舊 7 個指標 5637 列逐列相同**（含封面股數 595 列，摘要 `c9d94d3d…`）；新指標 263 列（季度 193、年度 70；17 檔；幣別 USD 262／CNY 1〔XPEV，外國申報人，不判色〕）；
沒有任何一列的 `filed` 等於 `fetched_at` 的日期、沒有空 `filed`。第四季衍生：FY−9M 45 列、FY−ΣQ1..Q3 13 列（IREN FY2025、MRVL 各年度各版本）；營收／營業利益因新衍生路多出 **0** 列。

**燈（國內申報人 35 檔）：黃 24／綠 6／灰 5 → 黃 11／綠 0／灰 24**（`provider_missing` 19、`insufficient_evidence` 5）；外國年報 8、台股月報 7、unknown 23 共 38 檔全部 `method_not_applicable`。

| 黃（11） | 最近四季已知金額（只計這個 tag） | 占正規化市值 | 這筆是什麼 |
|---|---|---|---|
| AAOI | 1,351,351,000（四季都有） | 16.0% | 2025-Q3～2026-Q2 每季都有 |
| AXTI | 600,083,000（Q2'26）＋**FY2025 9355 萬歸不到季** | 11.8% | FY2025 年報有、2025 年三份 10-Q 都沒有這個 tag 的 fact → `unattributed`，不補 0 |
| COHR | 1,998,450,000（年度＝窗尾） | 3.5% | 10-Q（`0000820318-26-000013`）Note 12：2026-03-02 對 NVIDIA 私募 7,788,161 股、每股 $256.80、總額 $2B；權益表「Sale of shares net of issuance costs … 1,998,735」＝表內值（同一會計年度另有 Series B 特別股轉普通股 25.07 億，不是這個 tag、不在加總） |
| INTC | 949,000,000（2 季） | 0.15% | 窗內四季只有 2026 年兩季有這個 tag 的 fact（2025-06-29～09-27、09-28～12-27 兩季沒有）——金額是「已知至少」 |
| IREN | 3,058,036,000（年度＝窗尾） | 19.0% | — |
| LITE | 1,999,700,000（1 季） | 2.3% | 10-Q（`0001628280-26-030777`）權益表：「Issuance of Series A Convertible Preferred Stock, net of issuance costs … 1,999.7」（可轉換特別股照黃） |
| LRCX | 17,447,000（年度＝窗尾） | 0.004% | 每年小額、多季有值 |
| META | 450,000,000（2025-Q3） | 0.03% | — |
| MP | 724,209,000（2025-Q3） | 8.6% | — |
| MRVL | 27,600,000（2 季，其一是 FY−ΣQ1..Q3 衍生的第四季） | 0.01% | 每年 Q2 約 5000 萬、型態像員工股票計畫 |
| NVDA | 791,000,000（四季，兩季有值） | 0.01% | 每年 Q1、Q3 有值、型態像員工股票計畫 |

- **由黃轉灰的 17 檔**：14 檔 `provider_missing`（AEHR、AEVA、AMD、ANET、AVGO、BX、FN、GLW、MTSI、MU、NOVT、ORCL、TSLA、TXN——5 年回填窗內沒有這個 tag 的 10-K／10-Q fact）；
  3 檔 `insufficient_evidence`（APO 股數 +3.2%、GXO +0.2%、SNDK +0.8%——有 tag 但窗內為 0、股數卻增加，分不出員工股酬與沒標 tag 的增發）。
- **由綠轉灰的 4 檔**：AAPL、AMAT、JBL、MSFT（從來沒有這個 tag → `provider_missing`；改前的綠是「股數沒增加」）。**由綠轉黃 2**：LRCX、NVDA。**由灰轉黃 2**：IREN、META。
- **綠 0 的原因**：綠要「有 tag、窗內 0、股數窗滿一年且沒增加」三件同時成立；今天有 tag 且窗內 0 的 5 檔，股數不是增加就是窗不滿。這是規則照寫的結果，不是缺陷——`provider_missing` 不得冒充綠。
- **「會死嗎」那個字變了 25 檔**（多數是灰燈數 +1；AMD、ANET、APO、MTSI、MU、NOVT、SNDK、TSLA 8 檔由黃變綠——稀釋那盞由黃轉灰後，其他三盞的最差色是綠；
  LRCX、NVDA 由綠變黃；BX 由「黃（灰 3）」變「灰 4」；IREN、ORCL 仍是紅、灰燈數 ∓1）。
  **候選板「可開」計數不會動**：`alpha/providers/candidates.py::open_preconditions` 的四個前提（讀圖現行、answers 稽核行、反證 watch、連結）都不讀四盞燈。
- **剩下的已知限制**（plan §14 #19–#21）：大型股的這個 tag 多半是員工股票計畫（NVDA、MRVL、LRCX 型；燈照黃、占市值 % 印出來，INV-5 不設量級門檻）；
  公司另用自訂 tag 標的發行不在金額內（INTC）；10-Q 與 10-K 前後 tag 不一（CRWV FY2025 年度 6800 萬 < Q1'25 13.9 億；NVDA FY2024 年度有、三份 10-Q 沒有）。

逐檔明細：scratchpad `p46_trial/lamps_after.json`（session 結束即消失；正式庫遷移後以 materialize 產物為準）。

## 23. Step 4.7 四個小修的真實資料驗收（2026-10-01 23:27 materialize，daily ⑬ 同一行）

改前＝今早 05:34 daily 的產物（`library/private/backups/20260930T213948Z/files.zip` 內的 analyst_view，與 §11 同一批；文字 digest 總值 `5f7211dc40a76414`）。

| 驗收 | 改前 | 改後 |
|---|---|---|
| downside 面板 `source="judgment"` 列（4.7a） | 240（63 檔） | **0** |
| research 面板 `disproofs`（4.7a，欄位退役） | 240（73 檔都有這一欄） | 0（0 檔有這一欄） |
| downside 面板「有列／缺席」 | 63／10 | 4／69（有列的 4 檔＝AXTI、COHR、LITE、SIVE.ST，都是有登記反證的 v2 敘事；其餘 69 檔印「這家公司名下還沒有任何登記的反證（…）」） |
| 候選板 `holdings`（4.7b） | `unresolved ["7803.T"]`、沒有 `ignored` 欄 | `unresolved []`（使用者白天刪了 Sheet 那一列）、`ignored []`、`ignored_problem null`——心跳照印「持股解析不到 0（使用者決定不研究 0）」 |
| 自家歷史百分位印覆蓋率（4.7c） | 0 檔有 `coverage` | 31 檔 |
| 敘事 ledger 同版重複反證（4.7d） | — | 現行 v2 敘事 4 份、連舊版 8 筆 v2 紀錄：重複 0（新規則不擋任何既有敘事） |

**文字 digest**：總值 `5f7211dc40a76414` → `83a64c6612c12330`。brief／research 兩面板 73 檔文字逐字不變（research 面板 digest 只算敘事文字行，disproofs 清單不在內）；
**argument 面板 17 檔變了——逐行比對（34 行全在鏈段 `argument:chain`），沒有一行來自 4.7**：
① 8 檔公司名由 slug 換成名冊 display_name（6481.T、AMD、CCXI、IREN、SNDK、TSLA、XFAB.PA、XPEV；4.1c）；
② 9 檔押的層讀圖狀態「現行」→「現行（圖上只有證據等級變了）」（2455.TW、3081.TWO、4979.TWO、5016.T、5802.T、AXTI、COHR、LITE、SIVE.ST——4.3 讓
`mat:inp_substrate`、`tech:cw_dfb_laser` 兩層讀圖 stale_low）；SIVE.ST 另有 SuperNova 插槽「現行」→「圖變了、該重讀」（4.3 的 stale，4.8 第 5 項重讀）；
LITE 另有「Pluggable turnkey ELS module」一條由「公司自己說的，但寫在正式申報文件裡」升為「有客戶或第三方印證」（4.3 登記發布者），句中順序跟著換。
（先用「這 17 檔名下有沒有 4.1／4.3 改判的邊」去解釋，被資料推翻——9 檔名下沒有改判邊、20 檔有改判邊卻沒變；逐行比對才找到上面三種來源。）
