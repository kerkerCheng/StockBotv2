---
date: 2026-10-03
topic: phase6-baseline
plan: docs/plans/2026-10-02-002-feat-phase6-evidence-criteria-plan.md
step: 6.0
---

# Phase 6 Step 6.0 — [666] 收尾＋基準快照

**這份報告只有一個用途：Phase 6 各 Step 與結案時逐項比對**（plan §1、§11、§12）。現況數字會腐壞，所以連同**產生它們的命令**一起存。
本檔每個數字數的都是**圖、讀圖、敘事、等待 registry、機制存在與否**，沒有一個是「幾檔通過某個 filter」。

- 快照時間：2026-10-03 05:40–06:05（台北）；今天的 daily（run `23916ca2`）05:30:01 開跑、05:40:20 收工（26 步、失敗 0），快照全部在它之後
- HEAD：`06350d0b`（[666] 的 publish commit）；本 Step 的 commit 之前工作樹另有本報告、`config/graph_baselines.json` 新鍵、`docs/plans/README.md` 一格的修正（§1）
- Python：`.venv/Scripts/python.exe`；Neo4j 讀取一律 `session.execute_read`（[666] 的 apply 除外，見 §0）；Google Sheet 只經 `materialize --candidates` 唯讀
- 單一 writer：daily 收工後 `python scripts/writer_guard.py check` 只剩「工作樹不乾淨」一條（＝[666] 的兩個未 commit 檔，本 Step 自己的產物）→ `acquire --minutes 90` 後才寫
- 量測腳本與全文存 scratchpad（只讀，不寫任何 authority）；下表列指紋，後續 Step 以同一支腳本重跑比對

| scratchpad 檔 | 內容 | sha256 |
|---|---|---|
| `pre666b.json`／`post666.json` | §0 [666] 前後的全圖 canonical 邊證據等級＋InP／Reuters 相關 41 筆 assertion 的逐字與 sub（`snapshot_evidence.py`） | `1d2d4be5…d5c8`／`30382a9f…e521` |
| `sim_b0.json`、`sim_b_gsr.json`、`sim_b_merge.json`、`sim_b_alias.json`、`sim_b_all.json`、`sim_b_all_strict.json` | §3 逐來源模擬（`p6_sim.py`）六個情境 | `7d2127c6…0aa0`、`fef58850…185f`、`f529fbca…81eb2`、`3d889c2d…aaff`、`a845f959…5383`、`b802aa1f…a5c8` |
| `pytest_base.out`／`test_functions_base.txt`／`invariants_base.out` | §1 | `3ab9c27b…9504`／`c1db1da2…db98`／`ce1eaabc…5e29` |
| `hb_base.md` | §4 心跳全文（`python -m crons.heartbeat --out`，不帶 `--write-snapshot`） | `92176410…12b7` |
| `p6_base.json`／`p6_stockpage_base.json`／`p6_dilution_base.json` | §4–§11（`p6_baseline_collect.py`、`p6_stockpage_evidence.py`、`p6_dilution.py`） | `46a785ce…81de2`／`ba1c62d4…87fc`／`02cbe18e…f07b` |
| `materialize_post666.log` | §0 [666] 之後重 materialize 的輸出 | `4a3d7626…6861` |

## 0. [666] 收尾（6.0a；使用者 2026-10-02 的 `go`）

```text
python scripts/apply_ra_admission.py --pq2 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d
  → ✓ 四道檢查與 token 檢查通過，核准戳記已寫入（重試：沿用原戳記）；status=applied、open_conflict_ids=[]
python scripts/commit_pending_intake.py
  → status=pushed；commit 06350d0b（extractions/…json、library/raw/…txt、library/intake/2026-10-01-ra_b98730bb….md）
python -m engine_b.todo complete-ra 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d
  → [666] resolution=go、receipt action:ra_b98730bb…;digest:26924126…;commit:06350d0b…
```

沒有被權限分類器擋下、沒有 Forbidden（token 已在，Phase 5 Step 5.1d 的入口檢查先查過）。loader 印的 `[node-merge] … 保留既有` 9 行＝節點的 name／aliases **保留圖上現值**，沒有被這份抽取覆寫。

**證據等級變動（[666] 是獨立事件；同一份圖、前後各算一次，`snap_diff.py pre666b.json post666.json`）：** assertion 699→699、canonical 邊 537→537；
唯一改的是 Reuters 那份 11 筆 assertion 的 `origin_linkage`：None → `independent`。**升外部印證 6 條**（Phase 4 closeout 預告 6 條，逐條相符）：

| 邊 | 前 → 後 |
|---|---|
| `co:axt supplies_to co:coherent` | 自報·filing → 外部印證 |
| `co:axt supplies_to co:landmark_optoelectronics` | 媒體轉述 → 外部印證 |
| `co:axt supplies_to co:vpec` | 媒體轉述 → 外部印證 |
| `co:jx_advanced_metals supplies_to co:lumentum` | 媒體轉述 → 外部印證 |
| `co:lumentum depends_on mat:inp_substrate` | 自報·filing → 外部印證 |
| `co:sumitomo_electric supplies_to co:lumentum` | 媒體轉述 → 外部印證 |

分布：外部印證 244 → **250**、自報·filing 107 → 105、媒體轉述 37 → 33（其餘不變）。
③b 計數器印「**重寫 4**」（e1／e2／e9／e10 四筆帶 sub、內容指紋因 `origin_linkage` 改變；supported 4／4）——與 Phase 4 closeout 預告相同。

**L11-6 ④（本 Step）：** 最先壞的是 `mat:inp_substrate` 那幾條邊 → 對 41 筆 InP／Reuters 相關 assertion 逐筆比對 src／relation／dst／source_doc_id／origin／attributes（含 sub）／逐字／confidence：
**除了 Reuters 11 筆的 `origin_linkage` 之外 0 處變動**。

⚠ 附帶發現（不擋，記進 §14 待決）：這次寫回的 `library/raw/reuters_inp_export_controls_2026_06_11.txt` 多了一組重複的「Source URL／Excerpt:」表頭——
寫 [666] 草稿的 session 把舊檔全文（含表頭）當成 `raw_excerpt` 傳入，`intake/provenance.py::_raw_artifact_text` 又加一次表頭。摘錄那一句完整、圖上的逐字不受影響；
它是使用者核准的那個 digest 的內容，所以不改。

`python -m webapp materialize --tracked --registry-listed --structure-table --graph-walk --structure-readings --candidates`（daily ⑬ 的同一行去掉不依賴圖的 beta／watches／positions／scorecard）→ 77/77，[666] 之後的 artifact 是下面各節的來源。

## 1. 全測試基準與 invariant

`python -m pytest -q -p no:cacheprovider` → **1 failed, 3302 passed, 1 skipped**（276s）：

```text
FAILED tests/test_phase_status_hint.py::test_real_readme_status_cells_start_with_a_known_word
```

原因：plan commit `8c7cc574` 把 `docs/plans/README.md` 對照表 Phase 6 那一格寫成 `**active**（…）`——不是以封閉字彙開頭，SessionStart hook（`crons/phase_status_hint.py`）因此判成「沒有 active」（今天 session 開頭的提示就是這樣錯的）。
修法：那一格改成 `active（…）`（與其他列同一個寫法）；改後該檔 5 passed、hook 印「Phase 6 證據判準 執行中｜下一個 Step：6.0」。plan §0.6 #1。**全測試以修正後為基準：3303 passed、1 skipped**（與 Phase 5 結案相同）。

`ls tests/test_*.py | wc -l` → **211**。測試函式名單：`git grep -n -E "^\s*(async )?def test_" HEAD -- 'tests/*.py'`（HEAD＝`06350d0b`）→ **2673** 個、無重複，
正規化成 `檔::函式` 後 `LC_ALL=C` 排序（LF）sha256 `c1db1da283b988bf2407227b97862a5291410a373c74a437cedc7d10fa76db98`（`test_functions.py`）。結案比對以 `06350d0b` 為起點重跑同一條命令。

`python -m audit invariants` → **14 PASS／FAIL 0／SKIPPED 0**（共檢查 5397 筆）。與本 Phase 相關的三行：

```text
PASS    SourceDocSync        SourceDoc 與抽取 JSON：重建會遺失或不確定 0（section 0／title 0）｜圖落後 JSON 0（section 0／title 0）｜圖上有、沒有任何抽取檔 0｜讀不了的抽取檔 0 [220 筆]
PASS    PointInTime          SourceDoc published_at 207/220（94.1%）；EdgeAssertion 可定日 681/699（97.4%）；已回填 22 份且 basis 全部指得回去 [941 筆]
PASS    QueueSegments        pending_triage=0；…；triaged_go_leads=23；forward_view_backlog=69；graph_holes=7；pollable_watches=15；… [2027 筆]
```

## 2. 證據等級凍結（`config/graph_baselines.json` 新鍵 `evidence_classes_2026_10_03`）

[666] 之後、本 Phase 改任何規則或資料之前的全圖：`query.structure._classify_edges(fetch_assertions(...))`（＝`collapse_assertions`＋`classify_evidence`）。
鍵內容：`taken_at`、`head`（`06350d0b`）、`report`（本檔）、`plan`、`scope`、`assertions` 699、`canonical_edges` **537**、`distribution`、`classes`（`"src relation dst"` → 等級，537 筆）、`origins`（同鍵 → 排序後的 origin 字串，537 筆）。
只放 id 與 origin 字串，不放引文（檔頭 `_doc` 的規則）。寫入腳本（scratchpad `freeze_evidence.py`）在寫前寫後比對既有兩個鍵的 canonical JSON——**一字不變**；檔案格式照原本 `indent=1`，`git diff` 只有新增 2270 行、刪除 0。

| 外部印證 | 自報·filing | 供應商自報 | 待判定 | 媒體轉述 | 雙方聯合 |
|---|---|---|---|---|---|
| **250** | 105 | 104 | 37 | 33 | 8 |

查證：`python -c "import json; d=json.load(open('config/graph_baselines.json',encoding='utf-8'))['baselines']['evidence_classes_2026_10_03']; print(d['canonical_edges'], d['distribution'])"`

## 3. 逐來源模擬（6.4 的對照答案；scratchpad `p6_sim.py`，唯讀）

**規則（plan §5 的 owner 草案，逐 origin 判、取最高）：**
- 名冊公司、不是主詞、主詞是名冊公司 → 這個 origin 自己的引文至少一段具名主詞（`quote_names_company`）才是外部印證；主詞在名冊**沒有可用寫法**（`company_name_forms` 扣掉兩家共用的）→ `no_name_forms`；有寫法但沒具名 → `unnamed`；兩者都 → 待判定。主詞不是名冊公司 → 照舊。
- 發布者 → 逐份文件先過 `publisher_lifts`；過了的文件裡，要有一段具名主詞的引文，且**那份文件沒宣告 `origin_linkage=independent` 時**那段不得含草案轉述詞（`announced`／`said`／`says`／`stated`／`states`／`according to`／`表示`／`宣布`；ASCII 整詞不分大小寫、中日韓整串）→ 否則 `relay`／`unnamed`／`no_name_forms` → 媒體轉述。
- 解析不到、主詞自己 → 照舊。

⚠ **「宣告 independent 的文件不套轉述檢查」是本 Step 撞到的 plan 內部衝突的裁決**（plan §0.6 #2）：ROADMAP Phase 6 列（「發布者的引文是轉述句就不升，**翻案靠逐份宣告 `origin_linkage=independent`**」）、
§0.1 #4（同一句）、6.8 第 1 項（`relay` 的補救＝宣告 independent 的 RA）三處都是這個讀法；只有 §13 陷阱註記寫「6.4 的轉述檢查也套在那份 Reuters 的引文上」。依 plan 檔頭「衝突時以 ROADMAP 為準」採前者、§13 改寫。
兩種讀法的差別剛好是 [666] 那 6 條（`sim_b_all.json` vs `sim_b_all_strict.json`）：照 §13 的讀法，6 條會全部退回（s1「AXT … said in May」是 AXT 自己的話被轉述；
s2「…, the person said」是 Reuters 自己採訪的不具名業內人士；s5「SemiAnalysis' Wang said …, he said」是第三方分析師——草案字表三段都判成轉述），等於把使用者 10-02 核准的宣告整個抵銷。
[666] 的 RA 已在 L8 備註寫明「宣告是文件層級的，分不到逐句；axt→coherent 升級的意思是有一位非 AXT 的知情者也這樣說」。

**結果（[666] 之後的圖；`sim_b*.json`）：**

| 情境 | 舊規則 外部印證 | 新規則 外部印證 | 新規則掉級（理由） |
|---|---|---|---|
| 今天的資料（`sim_b0`） | 250 | 230 | 20：未具名 14、轉述 2、名冊無名 4（nava 1、OpenLight 3——兩個代號同名，寫法全被當成共用） |
| ＋三個資料更正（GSR→media、OpenLight 合併、Apollo／Arista／GF 寫法；`sim_b_all`） | **244** | **229** | 15：未具名 12、轉述 2、名冊無名 1（nava） |

**規則那一半與 plan §0.2 的模擬逐條相同**（§0.2 是 [666] 之前算的：未具名 12、轉述 2、身分 4 其中 nava 1 在這裡歸「名冊無名」、OpenLight 3 由合併處理）。差異只在資料更正那一半：
§0.2 寫 GSR 7 條，[666] 之後只剩 **3 條**——另外 4 條（`co:jx_advanced_metals`／`co:sumitomo_electric` → `mat:inp_substrate`、`co:axt competes_with co:jx_advanced_metals`、`co:sumitomo_electric competes_with co:axt`）現在由宣告 independent 的 Reuters s3 撐住。
所以 §11 的「外部印證 244 → N」改以本鍵的 **250** 起算（plan §0.6 #3）。

規則掉級的 15 條（`sim_b_all`；括號＝撐住舊等級、新規則下不撐的那個 origin 與文件）：

| 邊 | 舊 → 新 | 理由 |
|---|---|---|
| `co:agility_robotics constrained_by comp:humanoid_precision_actuators` | 外部印證 → 媒體轉述 | 未具名（SVRC Research `svrc_state_of_robotics_2026_us`） |
| `co:broadcom supplies_to tech:cpo` | 外部印證 → 待判定 | 未具名（Meta 自著論文 `meta_bailly_ecoc2025_via_nextplatform`） |
| `co:coherent depends_on tech:inp_6inch_fab` | 外部印證 → 待判定 | 未具名（NVIDIA `nvidia_blog_coherent_texas_2026_06_16`） |
| `co:coherent supplies_to tech:cpo_fiber_attach` | 外部印證 → 待判定 | 未具名（NVIDIA `nvidia_sipho_blog_partner_roles`） |
| `co:coherent supplies_to tech:uhp_laser` | 外部印證 → 媒體轉述 | 轉述（Cignal AI s1「Coherent announced a PO…」） |
| `co:fabrinet supplies_to tech:cpo_packaging_assembly` | 外部印證 → 待判定 | 未具名（NVIDIA `nvidia_sipho_blog_partner_roles`） |
| `co:hyundai_mobis supplies_to co:boston_dynamics` | 外部印證 → 待判定 | 未具名（Boston Dynamics `boston_dynamics_hyundai_mobis_atlas_actuators_2026_01_07`） |
| `co:lumentum supplies_to co:nvidia` | 外部印證 → 待判定 | 未具名（NVIDIA `nvda_lumentum_partnership_pr_2026_03_02`；今天另由 GSR 撐住，GSR→media 之後才掉） |
| `co:lumentum supplies_to tech:els_pluggable_module` | 外部印證 → 自報·filing | 轉述（Cignal AI s1「Lumentum announced…」、s3「…recently stated…」） |
| `co:lumentum supplies_to tech:uhp_laser` | 外部印證 → 待判定 | 未具名（NVIDIA `nvda_lumentum_partnership_pr_2026_03_02`） |
| `co:mp_materials supplies_to mat:separated_heavy_reo` | 外部印證 → 媒體轉述 | 未具名（USGS `usgs_mcs2026_rare_earths_heavy`） |
| `co:nava_thailand supplies_to tech:cloud_transceiver_1_6t` | 外部印證 → 待判定 | 名冊無名（Lumentum `lumentum_q2fy26_cpo`；6.2 定案） |
| `co:sivers_semiconductors supplies_to tech:cw_dfb_laser` | 外部印證 → 自報·filing | 未具名（華星光 `mops_4979_annual_report_2025`） |
| `co:sumitomo_electric supplies_to co:nvidia` | 外部印證 → 待判定 | 未具名（NVIDIA `nvidia_sipho_blog_partner_roles`） |
| `co:tsmc supplies_to tech:mrm_200g` | 外部印證 → 媒體轉述 | 未具名（TrendForce `trendforce_tsmc_pic_capacity_2026_07_08`） |

資料更正各自的效果（舊規則下，`sim_cross.py sim_b0 sim_b_<x> 0`）：
- **GSR→media**：`co:axt supplies_to mat:inp_substrate` 外部印證 → 自報·filing；`co:coherent`／`co:lumentum supplies_to tech:cw_dfb_laser` 外部印證 → 媒體轉述（3 條）。
- **OpenLight 合併**：`co:openlight_photonics develops prod:ph18da` 外部印證 → 供應商自報；`partnership_with co:tower_semiconductor` 外部印證 → 雙方聯合；`supplies_to co:newphotonics` 外部印證 → 媒體轉述（併入 `co:openlight` 那條 SemiToday 的邊）；
  `partnership_with co:cadence`、`co:tower_semiconductor develops prod:ph18da` 待判定 → **雙方聯合**（升級——資料更正：Tower／OpenLight 聯合 6-K 的 origin 在合併後具名兩家不共用寫法的名冊公司）。
- **三個寫法**：舊規則下 0 條；新規則下救回 `co:apollo invests_in co:broadcom`、`co:arista enables tech:xpo_form_factor`、`co:globalfoundries develops prod:gf_scale`（6.3a 的命中掃描要逐筆核對）。
- 任何情境下「新規則讓某條邊升級」＝**0**（`upgrades` 欄；plan 不可越線 2）。

## 4. 走圖與心跳

`library/private/app/state/graph_walk.json`（[666] 之後 materialize，`generated_at` 2026-10-02T21:43:13Z，`content_digest` `sha256:5e44280b…5f9f`）：

```text
層：①獨家且全自報 73（凍結 186 個節點；集合外新節點 0）｜②非供應商來源列舉 ≥2 家 6 層（≥3 家母體 10；每家撐住 9；origin 解析不到的來源 8）｜③a sub 引文不含可替代性語言 102／113（存量）｜③b 新增或重寫的帶 sub supported 4／4（新增 0、重寫 4）｜外部印證但引文不具名供應商 15｜字表 v1·narrow
```

- ① supply ns 0／1／2／≥3＝72／82／22／10、frozen_on_graph 186、frozen_gone 0、new_nodes 0
- ② `named_by_non_supplier_layers`：`mat:inp_substrate`、`tech:cw_dfb_laser`、`tech:external_laser_source`、`tech:rv_reducer`、`tech:tfln_platform`、`tech:uhp_laser`；母體 114 層有供應商、≥3 家 10、每家撐住 9
- ③ checked 113、stock_unsupported 102、superseded 4（supported 4）、new 0
- **舊計數器 `ec_quote_does_not_name_supplier` 15 條**：agility→actuators、apollo→broadcom、arista→xpo、broadcom→cpo、coherent→cpo_fiber_attach、fabrinet→cpo_packaging_assembly、gf→gf_scale、hyundai_mobis→boston_dynamics、mp→separated_heavy_reo、nava→cloud_transceiver_1_6t、openlight_photonics ×3、sumitomo→nvidia、tsmc→mrm_200g。
  與 §3 新規則的 20 條（`sim_b0`）比，舊口徑漏 5 條——全是「供應商自己的引文具名了自己、撐住外部印證的那份卻沒具名」或轉述：coherent→inp_6inch_fab、coherent→uhp（轉述）、lumentum→els（轉述）、lumentum→uhp、sivers→cw_dfb（plan §13「舊口徑錯在任何一段引文」）。
- 九型命中／母體：薄層沒人讀 4／13｜獨家且自報 **0**／13｜供給側未填 2／7｜讀圖該重讀 0／4｜lead 點名不在圖 7／16｜供貨走不到錨 6／51｜沒人供應 9／129｜建模待補 10／181｜重複節點 23／188

心跳（`hb_base.md`，sha256 `92176410…12b7`、7426 bytes）：段 3「層：」行與上面 artifact 的 `summary` 逐字相同；段 2「較昨變動 9 項」；段 4「歸零旗標 73 檔 × 4 盞：紅 21｜黃 44｜綠 88｜灰 139」。
`SNAPSHOT_KEYS` **64 個**＝Phase 5 baseline 的 56 個＋Phase 5 加的 8 個（`positions.lane.paper.n`、`positions.lane.live.n`、`positions.lane.history.reached_2x_ever`、`positions.lane.paper.reached_2x_ever`、`positions.lane.live.reached_2x_ever`、`predictions.held`、`predictions.wrong`、`predictions.expired_unread`）。

## 5. 讀圖、敘事、個股頁

**讀圖 4 份**（`python -m alpha structure-reading <node> --check --format json`）：

| 節點 | 單位 | 現行 | status | 變動（全部 low） | 到期 |
|---|---|---|---|---|---|
| `mat:inp_substrate` | 層 | `sr_bac985bacbea64b7` | **stale_low** | 供給側 axt 自報·filing→外部印證、sumitomo 待判定→外部印證、jx 待判定→外部印證；需求側 lumentum 自報·filing→外部印證 | 82 天 |
| `tech:cw_dfb_laser` | 層 | `sr_d49b81b6465e1181` | **stale_low** | 供給側 coherent／lumentum 供應商自報→外部印證；反向路徑 blazar 待判定→媒體轉述 | 82 天 |
| `prod:supernova` | 插槽 | `sr_d85d672998445c50` | current | — | 89 天 |
| `prod:els_8ch_module` | 插槽 | `sr_35ca0ce58617d5f6` | current | — | 82 天 |

讀圖 ledger 指紋（Phase 5 起不變）：inp `bc43b2d8…d4fe`（7 行）、ELS `edf2b719…78be`（1）、SuperNova `064f1b40…3b0f`（2）、cw `f8e4439b…671c`（5）。

**v2 敘事 4 檔**（`library/private/alpha/briefs/*.jsonl` 最後一行）：AXTI `ib_3100d4c6f394b679`、COHR `ib_1ddf59d7c3cf4fe4`、LITE `ib_bc97e6ccde70f264`、SIVE.ST `ib_457146d29ad50ef0`（全是 `investor-brief/v2`）；
ledger 指紋 AXTI `ac917627…d830`（4 行）、COHR `85b04f3c…7bcf`（4）、LITE `93653d6e…a5e5`（5）、SIVE.ST `b0936b04…68d1`（3）。

**個股頁「這條鏈怎麼走」**（`argument:chain` 那一格；每條邊的證據標籤就印在這段裡；6.8 換版的對照，全文在 `p6_stockpage_base.json`）：
- AXTI：「…AXT, Inc.供應「Coherent」；已通過客戶驗證；**有客戶或第三方印證**。AXT, Inc.供應「Lumentum」；驗證中；**有客戶或第三方印證**。每一段連結都有客戶或第三方印證。」
- COHR：「…Coherent供應「NVIDIA」；已被設計進客戶產品；有客戶或第三方印證。Coherent供應「High-power CW DFB laser」；…有客戶或第三方印證。Coherent依賴「Indium Phosphide (InP) substrate」；…有客戶或第三方印證。Coherent依賴「6-inch InP Fab」；…有客戶或第三方印證。Coherent供應「External Laser Source」；驗證中；有客戶或第三方印證。另外 3 條連結（…）只有公司自己在講…」
- LITE：「…Lumentum供應「Ultra-high-power laser chip」；…有客戶或第三方印證。Lumentum依賴「Indium Phosphide (InP) substrate」；有客戶或第三方印證。Lumentum供應「Pluggable turnkey ELS module」；驗證中；有客戶或第三方印證。Lumentum供應「Optical Circuit Switch」；…公司自己說的，但寫在正式申報文件裡。另外 2 條…」
- SIVE.ST：「Sivers Semiconductors 在圖上還沒有評為難替代（替代難度 4 以上）的連結，這一段沒有邊可講。押的層「High-power CW DFB laser」…」

⚠ §3 的規則掉級裡，COHR（6-inch InP Fab、UHP——注意 COHR 鏈段印的是 External Laser Source）、LITE（UHP、ELS pluggable）的鏈段今天都印「有客戶或第三方印證」——6.8 第 4 項的核對對象。

## 6. SourceDoc 的 origin 解析

圖上 SourceDoc **220** 份：解析成公司 155、登記的發布者 49、**解析不到 16**（與 plan §0.2 相同）：

| 類 | 文件（origin；掛幾條邊） |
|---|---|
| 聯合公告（字串偵測判雙方聯合）8 | `amd_anthropic_helios_partnership_20260722`（AMD and Anthropic；2）、`gf_mps_manufacturing_agreement_2026_09_09`（GlobalFoundries and Monolithic Power Systems joint announcement；0）、`iqe_quintessent_qdl_supply_2026_09_03`（1）、`iqe_tower_inp_epiwafer_agreement_2026_06_15`（1）、`lumentum_ayar_els_collab_pr_2022_03_09`（1）、`mrvl_lite_scaleup_ocs_pr_2026_03_16`（2）、`sivers_seminex_inp_program_2026_08_13`（3）、`tsem_openlight_cadence_pdk_6k_2026_08_11`（Tower Semiconductor / OpenLight (joint press release)；4） |
| 名冊外公司 5 | `credo_npo_vs_cpo_20260821`（Credo Semiconductor；1：`tech:near_package_optics competes_with tech:cpo`）、`noveon_series_c_2026_01_19`（Noveon Magnetics；1：`co:mp_materials supplies_to mat:rare_earth_magnets`）、`sojitz_hre_import_2025_10_30`（Sojitz Corporation（客戶端）；1：`co:lynas supplies_to mat:separated_heavy_reo`）、`telescent_collimator_weak_link_2024_12_16`（Telescent（…）；0）、`usar_stillwater_phase1a_2026_03_26`（USA Rare Earth；1：`co:mp_materials supplies_to mat:rare_earth_magnets`） |
| 寫法要更正 3 | `novanta_humanoid_ft_2026`（Novanta/ATI（供應商官方應用頁）；1：`co:novanta supplies_to tech:force_torque_sensor`）、`reuters_soitec_capacity_reservations_2026_08_31`（Soitec management (Reuters interview)；0）、`Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era`（Third-party Research；**34 條邊**——plan §0.2 寫 31） |

16 份的 `source_type`：綜述論文 `paper`、`amd_anthropic_helios_partnership_20260722` `ir_deck`、`credo_npo_vs_cpo_20260821` `industry_report`、`tsem_openlight_cadence_pdk_6k_2026_08_11` `filing`，其餘 12 份 `news`；`origin_linkage` 全部未宣告。

`config/publishers.json` 34 筆；名冊 `config/company_identity.json` 100 家。
**圖上沒有** Credo／Noveon／Sojitz／Telescent／USA Rare Earth 的 `co:*` 節點（Cypher：id 與 name 都查，唯一命中 `co:lynas`「Lynas Rare Earths」是另一家）——6.3c 新增時 id 照名冊慣例新起。
身分相關節點仍在圖上：`co:nava_thailand`、`co:openlight`、`co:openlight_photonics`（2 → 0 是驗收②）。

## 7. 稀釋燈與結構表

**稀釋燈**（`overview.wipeout.lanes[lane=dilution]`；73＋1 份個股頁）：黃 **11**、`method_not_applicable` 38、`provider_missing` 19、`insufficient_evidence` 5、沒有這一格 1。黃的 11 檔（金額只計 `us-gaap:StockIssuedDuringPeriodValueNewIssues`）：

| 檔 | 窗內發行（正值加總） | 占正規化市值 | 窗 | facts（accession／filed／期間） |
|---|---|---|---|---|
| AAOI | 1,351,351,000 | 13.769% | 2025-08-14～2026-06-30 | 4 季：`0001437749-25-033627`（11-06）、`…-26-005875`（02-26，FY−9M）、`…-26-015620`（05-07）、`…-26-026278`（08-06） |
| AXTI | 600,083,000 | 10.657% | 2025-08-14～2026-06-30 | `0001437749-26-027677`（2026-08-13；Q2'26）；另 FY2025 9355 萬歸不到季 |
| COHR | 1,998,450,000 | 3.028% | 2025-08-14～2026-06-30 | 年度：`0000820318-26-000020`（2026-08-14；FY2026） |
| INTC | 949,000,000 | 0.150% | 2025-08-11～2026-06-27 | 2 季：`0000050863-26-000079`（04-24）、`…-26-000157`（07-24） |
| IREN | 3,058,036,000 | 18.583% | 2025-08-14～2026-06-30 | 年度：`0001878848-26-000052`（2026-08-27） |
| LITE | 1,999,700,000 | 2.054% | 2025-08-11～2026-06-27 | `0001628280-26-030777`（2026-05-06；可轉換特別股） |
| LRCX | 17,447,000 | 0.004% | 2025-08-12～2026-06-28 | 年度：`0000707549-26-000037`（2026-08-07） |
| META | 450,000,000 | 0.028% | 2025-08-14～2026-06-30 | `0001628280-25-047240`（2025-10-30） |
| MP | 724,209,000 | 8.657% | 2025-08-14～2026-06-30 | `0001801368-25-000054`（2025-11-07） |
| MRVL | 27,600,000 | 0.012% | 2025-09-15～2026-08-01 | `0001835632-25-000197`（12-03）、`…-26-000011`（03-11，FY−ΣQ1..Q3） |
| NVDA | 791,000,000 | 0.014% | 2025-09-09～2026-07-26 | `0001045810-25-000230`（11-19）、`…-26-000052`（05-20） |

**結構表**（`structure_table.json`，`generated_at` 2026-10-02T21:43:10Z，`content_digest` `sha256:50ebdaeb…4c96`）：224 列、需求錨 9 個（前三 tech:ai_switch 102、tech:optical_scale_up 39、tech:essential_chips_mature_node 29；無錨 13）。
**Lam 9 列**（`prod:reliant`、`tech:3d_nand_manufacturing`、`tech:3d_scaling`、`tech:advanced_packaging`、`tech:deposition_etch_clean`、`tech:dram_manufacturing`、`tech:foundry_logic`、`tech:nand`、`tech:semiconductor_manufacturing_equipment`）**全部錨在 `tech:dram_technology`**，
chain 全是 `tech:dram_technology → tech:semiconductor_manufacturing_equipment → co:lam_research`（`demand_chain` 從公司走；6.7a 的對照）。

## 8. 四則 lead 的 `classified_by`（6.3f 的舊值）

`library/leads/pending_leads.json`（1201 則）：`lead_198ada57ea4366384b6e4f9855826998`、`lead_3238fc77ac974944b52a2916205b98a6`、`lead_39841af82ef4211a19116d249331dd5d`、`lead_cbd50ac57aa511c2d6c4e531b759f7a7`——
四則 `classified_by` **都是 null**（欄位不存在）、`classified_at` null、`status` applied。

## 9. Phase 5 #15（tier 決定有沒有引用過舊計分表數字）——**結案**

`git log --oneline -- config/signal_sources.json` → 兩個 commit：`6320ed66`（2026-07-22，建檔）、`8eee2e1a`（2026-09-17，加 `tier` 欄位、初值一律 `probation`、`tier_since` 2026-09-17）。之後沒有任何變更——**tier 從未升降**。
pq2 池全部 669 項（含已結案）裡，沒有任何 tier 型別的項目、也沒有任何一項同時提到 tier 與計分表 → **0 項**。沒有 tier 決定引用過舊計分表數字，這一題結案。

## 10. 長駐 APP

`python -m webapp status`：state artifacts **8 份**（structure_table、beta、graph_walk、watches、positions、structure_readings、account_scorecard、candidates），全部 fresh／current；analyst views 73 份。
正在跑的 `webapp serve`（`Get-CimInstance Win32_Process`）：**兩組**——預設埠 PID 20820／15956（**2026-09-10 23:13 啟動**，之後的程式改動它都沒載入）、`--port 8799` PID 37080／6992（2026-10-01 21:19 啟動）。6.7b 的「APP 自偵舊程式」要讓這種情況自己出現在首頁。

## 11. 不變的東西（結案要逐字相同）

| 對象 | 指紋 |
|---|---|
| `library/trades/trade_log.jsonl` | `861d2008de8cdaa80c885b4e06da11ee0a2bf188526836dddcc1701a6bc7b8d5`（2 行，與 Phase 5 相同） |
| 舊店 `backup_pre_v8_20260818T021452.db`／`backup_pre_v9_20260902T032020Z.db`／`decision_lab.db` | `e887b3d4…de350`／`af3dc690…d39`／`e99d1c79…51810`（與 Phase 0–5 相同） |
| 主題等權組 ledger `AI_____CPO.jsonl` | `25721a7a…7503` |
| `library/leads/event_watches.json` | `d00710e5…0a37`（daily 每天會動；結案比讀圖／敘事來源的語意 watch 逐筆） |
| 讀圖 ledger／敘事 ledger | 見 §5 |
| `AGENTS.md` | `b029f7b93fd1d6e37783511a14139ac55c43861b6e33c904d7c5522226dc536e`（`git diff 06350d0b HEAD -- AGENTS.md` 結案時應為空） |
| `.claude/settings.local.json` | allow 52／ask 0／deny 0（6.7e 之前） |

## 12. 對 plan §0.2 的更正（6.0 實測）

| plan 原寫 | 實測 | 影響 |
|---|---|---|
| 外部印證 244 | [666] 之後 **250**（+6，逐條見 §0） | §11 的「外部印證 → N」以 250 起算（§0.6 #3） |
| 草案模擬 25 條掉級（GSR 7） | [666] 之後：資料更正 6（GSR 3、OpenLight 3）＋規則 15（未具名 12、轉述 2、名冊無名 1）＝21；250 → 229 | §3；規則那一半與 §0.2 逐條相同 |
| §13「6.4 的轉述檢查也套在那份 Reuters 的引文上」 | 與 ROADMAP「翻案靠逐份宣告 independent」衝突；照 ROADMAP | §0.6 #2；§5、§13 同步改寫 |
| 綜述論文掛 31 條邊 | 圖上 `Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era` 掛 **34** 條 distinct edge_key | 6.3e 的預期改 34 |
| 舊計數器 15 條 | 15 條（同）；新規則 20 條，多的 5 條見 §4 | — |
| 心跳「pq2 球在你手上 6」（10-02） | 今天 **0**、池中未結案 1（[586]，等客戶端具名確認）——[632] drop、[663]／[664]／[665]／[668] go 都在 10-02 結案 | 本 Phase 鑄的編號是唯一會進來的 |
| （未列）session 開頭 hook 說「無 active」 | plans README 那一格加粗所致；本 Step 修正 | §1、§0.6 #1 |

## 13. 本 Step 的 L11-6 ④

「如果 [666] 入圖改壞了東西，最先壞的是哪一筆」→ `mat:inp_substrate` 那幾條邊：41 筆 assertion 逐筆比對，除 Reuters 11 筆的 `origin_linkage` 之外 0 處變動（§0）。
「如果基準量錯了，最先壞的是 6.4 的逐條對照」→ 同一份圖上以兩個獨立入口各算一次分布：`snapshot_evidence.py`（`_classify_edges`）與 `p6_sim.py` 的舊規則重算，**537 條逐條相同**（`sim_b0.json` 的 `old` 分布＝§2 的分布）。

## 14. 本 Step 新增的待決（併進 closeout §14）

- 更正走廊的 `raw_excerpt` 若帶著寫入端自己的「Source URL／Excerpt:」表頭會重複（§0 附帶發現）——在 `create_action` 拒收或在草稿工具去表頭；不在本 Phase 範圍。

## 15. Step 6.1 插槽讀圖同級互換的真實資料驗收（2026-10-03 06:2x 台北）

改動：`alpha/structure_reading/staleness.py::_evidence_change`——插槽讀圖供給側的 evidence 變動，前後 rank（`query.bottleneck.EVIDENCE_RANK`，呼叫端以 `evidence_rank=` 注入、沒有預設）
相同＝`evidence`（low，detail 註「同級互換」）、不同＝`supply_evidence`（high）；rank 表查不到的標籤照跨級算。層讀圖一字不動。

- **4 份現行讀圖 `--check` 的 status 與 §5 逐份相同**（inp stale_low 4×evidence、cw stale_low 3×evidence、SuperNova current、ELS current；scratchpad `p61_replay.py` ①）。
- **L11-6 ④ 重放**：`prod:supernova` 09-25 那份（`sr_268d2fd79db629ff`）的快照對 10-01 那份（`sr_d85d672998445c50`）的快照＝Phase 4 Step 4.3 拆出媒體轉述的那次變動：
  新程式 → **stale_low**（`co:sivers_semiconductors→prod:supernova` needs_review → media_relay「同級互換」＋需求側一條 evidence，兩條都 low）；
  同一份資料以「每個標籤各自一級」（＝6.1 之前的行為）重算 → stale **high**（`supply_evidence`）——就是當時被推進重讀佇列的那一次。
- 測試：`tests/test_structure_reading_v3.py` 新增同級互換 low、查不到 rank 照跨級、`reading_status` 沒有預設 rank 三條；兩個既有 helper 補 `evidence_rank=`。
  變異：把 rank 比較拿掉（`if rank_before == rank_after:` → `if False:`）→ `test_a_same_rank_swap_on_a_socket_supply_edge_is_low` 紅（scratchpad `mutate.py`，跑完還原）。
  全測試 3306 passed／1 skipped。

## 16. Step 6.2 身分清理（2026-10-03）

### 16.1 nava 定案（6.2a；研究收據）

**結論：「Nava」是 Lumentum 自己在泰國 Navanakorn（Nava Nakorn）工業區的製造廠，不是一家代工廠 → 退役 `co:nava_thailand`、那條供貨邊改掛 `co:lumentum`。**

| 來源 | 逐字 | 判讀 |
|---|---|---|
| SEC DEF 14A，Lumentum Holdings Inc.，2023-09-22 申報（https://www.sec.gov/Archives/edgar/data/1633978/000130817923000998/llite2023_def14a.htm），Sustainability 段 | "We started solar panel installations at our San Jose, California corporate headquarters and our largest manufacturing facility in Navanakorn, Thailand, with an estimated completion date in the first half of fiscal 2024." | 一手（公司自己的法定申報）：Navanakorn 是**Lumentum 自己最大的製造廠** |
| Lumentum FY2026 10-K Item 2 Properties（庫內 `library/raw/lite_10_k_fy2026_20260817.txt`） | "…of which we own approximately 2,136,000 square feet, including the 1,173,000 square feet manufacturing sites in Thailand…" | 一手：泰國的製造廠是**自有** |
| Lumentum Q2 FY2026 法說摘要（`library/raw/lumentum_q2fy26_cpo.txt` Passage 4／10） | "Transceiver revenue grew ~$50M sequentially, leveraging expanded manufacturing capacity in Thailand (Nava)"；"stepping on the gas at Nava (Thailand)" | 與上兩者一致：「Nava」＝泰國那座自有廠的地名簡稱；抽取時把它建成一家公司（name 還寫成 contract manufacturer） |

旁證（媒體、不當依據）：Semiconductor Today 2022-02-04 轉述 Lumentum 新聞稿 "Lumentum's Thailand Navanacorn factory"；Lumentum 官方 X 帳號 "expansion of its production facility in Nava"。
10-K 另寫 "Our significant contract manufacturing partners are located primarily in Thailand, Taiwan, Malaysia and the Philippines"——泰國也有代工夥伴，但沒有任何來源把「Nava」指向代工廠；DEF 14A 那句把 Navanakorn 明寫成 "our … manufacturing facility"。

### 16.2 遷移工具 dry-run（6.2c；`python loader/migrate_identity_cleanup.py`，唯讀）

- 抽取檔：`semitoday_ph18da_volume_2026_03_20.json`——`co:openlight` → `co:openlight_photonics`（節點宣告＋`ph3` 的 src）；
  `lumentum_q2fy26_cpo.json`（local_only、不進 Git）——刪 `e27`（`co:lumentum supplies_to co:nava_thailand`）、`e28`（`co:nava_thailand supplies_to tech:cloud_transceiver_1_6t`）併入同檔既有的 `e7`
  （`co:lumentum supplies_to tech:cloud_transceiver_1_6t`，s8 早已在 e7 的 source_ids，**併入 0 個新來源**；e28 的 `qualification_status: qualified` 不併——s8 原文只講泰國產能，e7 的 `designed_in` 留著）、刪節點宣告。
- **入圖副作用（Phase 4 #32）**：兩份檔原樣重載時，`co:newphotonics` 的 `abstraction_level` 會被覆寫（module_subsystem → device_chip）、`role`（disruptor → null）——
  所以兩份檔**每個在圖上已存在的節點**都照抄圖上現值（`align_nodes_to_graph`；plan 原文只寫改名那一個，§0.6 #4）；照抄後兩份檔的副作用 **0**（只剩 `co:openlight_photonics` 的別名聯集「OpenLight」）。
- 名冊：100 → 98 家（刪 `co:openlight`、`co:nava_thailand`；`co:openlight_photonics._note` 改寫成合併紀錄，pq2 編號鑄號後填）。合併後 origin「OpenLight」「OpenLight Photonics」「OpenLight Photonics Inc.」都解析到 `co:openlight_photonics`。
- 圖上指著舊 id 的 assertion 只有 3 筆（`lumentum_q2fy26_cpo_e27`、`_e28`、`semitoday_ph18da_volume_2026_03_20_ph3`），全在 manifest 的兩份文件裡；claim 0；活的引用（lead registry、event_watches、hypotheses、讀圖、敘事 ledger）0；
  `library/leads/todo_pool.json` 一處提到 `co:openlight`——已結案項目的歷史文字，不改。
- **證據等級會變的邊（8 條；與 §3 `sim_b_merge` 逐條相同，另加 nava 兩條消失）**：

| 邊 | 改前 → 改後 |
|---|---|
| `co:lumentum supplies_to co:nava_thailand` | 供應商自報 → （邊消失） |
| `co:nava_thailand supplies_to tech:cloud_transceiver_1_6t` | 外部印證 → （邊消失；併入 Lumentum 自己的那條，等級不變） |
| `co:openlight supplies_to co:newphotonics` | 媒體轉述 → （邊消失；併入 canonical） |
| `co:openlight_photonics develops prod:ph18da` | 外部印證 → 供應商自報 |
| `co:openlight_photonics partnership_with co:tower_semiconductor` | 外部印證 → **雙方聯合**（plan 的 L11-6 ④：Tower／OpenLight 聯合 6-K） |
| `co:openlight_photonics supplies_to co:newphotonics` | 外部印證 → 媒體轉述 |
| `co:openlight_photonics partnership_with co:cadence` | 待判定 → 雙方聯合（升級：資料更正——聯合 6-K 的 origin 合併後具名兩家不共用寫法的名冊公司） |
| `co:tower_semiconductor develops prod:ph18da` | 待判定 → 雙方聯合（同上） |

### 16.3 RA packet 的入圖副作用（6.2d）

prepare 多一次 READ session（`intake.application._merge_side_effect_receipt` → `loader.merge_side_effects.side_effects`，與遷移 dry-run 同一個 owner），收據存在 RA 紀錄 `merge_side_effect_check`，packet 與 apply 報告都印「入圖副作用」一節；讀不到圖印「副作用無法核對」。
「入圖後證據等級會變的邊」那一段在 6.4 owner 落地後補（plan 原文）。
⚠ 順帶發現：既有測試 `test_prepare_validates_every_document_without_graph_or_publication` 守的「prepare 不開圖」從來沒被守住——同 URL 多段檢查本來就開圖，並以 `except Exception: pass` 吞掉測試的 AssertionError 絆線。
改寫成 `test_prepare_reads_the_graph_read_only_and_never_publishes`（假 driver 擋任何寫入 Cypher、斷言 READ session 真的跑了）；新程式的兩處例外處理對 AssertionError 一律往外丟。
同型的絆線在 `tests/test_intake.py`（`forbidden_driver` 兩處）可能一樣空跑——不在本 Step 範圍，記進 closeout 待決。

## 17. Step 6.3 證據資料（2026-10-03）

### 17.1 名冊三個寫法（6.3a）——加 Arista、GF；**Apollo 不加**

全圖逐字整詞比對（`query.bottleneck._form_pattern`，單一個詞分大小寫；scratchpad `p63a_alias_scan.py`）：

| 寫法 | 命中 | 判讀 | 決定 |
|---|---|---|---|
| `Arista` | 1 段：Coherent OFC 2026-03-17 s18「This was announced by Arista and ourselves and a bunch of other partners」 | 講的是 Arista Networks | 加進 `co:arista.name_aliases` |
| `GF` | 8 段：GF 20-F s9、optics.org ×2、Semiconductor Today ×2、Sivers 新聞稿 ×3（s1 原文「GlobalFoundries (NASDAQ: GFS) (GF)」） | 全部講 GlobalFoundries | 加進 `co:globalfoundries.name_aliases` |
| `Apollo` | 4 段：Broadcom Q2 FY26 s3／s4（Apollo Global Management）、**`google_apollo_ocs_2022` s1／s2「The Apollo OCS platform…」「…in the Apollo layer」（Google 的專案代號）** | 有 2 段不是在講這家公司 | **不加**（plan §4 6.3a 規則；§0.6 #6）——`co:apollo invests_in co:broadcom` 在 6.4 之後會是「未具名」，6.8 處理 |

證據等級變動（舊規則、改前＝HEAD、改後＝工作樹；`evidence_diff.py`）：**0 條**——寫法只在 6.4 的逐來源具名規則與層計數器 ② 起作用。

### 17.2 GSR → media（6.3b）

`config/publishers.json` 的 `Global Semi Research`：`industry_research`／`corroborates: true` → **`media`／`false`**（移到 media 組；note 記定案日期與理由——
[668] RA 的「反向證據與缺口」逐字「②GSR 是付費研究的公開摘錄，單位數字的出處沒寫」；與 Next Financial／damnang／primetrading／silicon_matter 四個 Substack 一致）。載入檢查通過（34 筆）。
證據等級變動（舊規則；`evidence_diff.py` 改前＝6.3a 的 commit）**3 條**＝§3 的 GSR 預測逐條：

| 邊 | 改前 → 改後 | 原因 |
|---|---|---|
| `co:axt supplies_to mat:inp_substrate` | 外部印證 → 自報·filing | GSR 不再撐；剩 AXT 自己的 10-K |
| `co:coherent supplies_to tech:cw_dfb_laser` | 外部印證 → 媒體轉述 | GSR 不再撐（[668] 那一句） |
| `co:lumentum supplies_to tech:cw_dfb_laser` | 外部印證 → 媒體轉述 | 同上 |

另外 4 條原本由 GSR 撐的（JX／住友 → InP、兩條競爭邊）由宣告 independent 的 Reuters s3 撐住，不變。

### 17.3 名冊新公司（6.3c）

圖上沒有這 5 家的 `co:*` 節點（§6），id 新起；`display_name` 都附一手出處；名字寫法先對全圖逐字整詞比對（`Credo`、`Credo Semiconductor`、`Noveon Magnetics`、`Sojitz Corporation`、`Telescent`、`USA Rare Earth` 命中 0；`Noveon` 1 段、`Sojitz` 2 段，都講本公司）：

| id | display_name（出處） | research_ticker | name_aliases |
|---|---|---|---|
| `co:credo` | Credo Technology Group Holding Ltd（10-K FY2026 封面「CREDO TECHNOLOGY GROUP HOLDING LTD」） | CRDO（NASDAQ） | Credo（官網頁尾「©2026 Credo, Inc.」）、Credo Semiconductor（10-K Exhibit 21.1 子公司「Credo Semiconductor Inc.」，California） |
| `co:noveon_magnetics` | Noveon Magnetics, Inc.（官網新聞稿首句） | null（私人） | Noveon（同稿自訂簡稱） |
| `co:sojitz` | Sojitz Corporation（官網頁尾「© Sojitz Corporation.」） | 2768.T（TSE） | Sojitz（同頁自稱） |
| `co:telescent` | Telescent Inc.（官網頁尾「TELESCENT Inc. …Irvine CA」） | null（私人） | （核心名稱 Telescent 已足夠） |
| `co:usa_rare_earth` | USA Rare Earth, Inc.（10-K FY2025 封面，CIK 1970622） | USAR（NASDAQ） | — |

名冊 100 → 105（[670] go 之後 103）；載入無衝突、沒有新的共用寫法。5 份文件的 origin 由「解析不到」變「公司」（`resolve_origin`）。
⚠ 有 research_ticker 的 3 家（CRDO、2768.T、USAR）會進 `TICKER_MAP`——下一次 daily 會多 3 份個股頁（`--registry-listed`）與 Engine C 的行情／財報列；這是名冊條目的正常後果，不是新機制。

證據等級變動（舊規則）**2 條，都是升級——資料更正（名冊新公司）**，逐條附引文（plan 不可越線 2、L18）：

| 邊 | 改前 → 改後 | 撐住的那段引文（origin） |
|---|---|---|
| `co:lynas supplies_to mat:separated_heavy_reo` | 待判定 → 外部印證 | 「Sojitz has begun the import of heavy rare earths (HREs) produced by Australia-based Lynas Rare Earths Ltd into Japan.」（Sojitz，客戶端；引文具名 Lynas——6.4 之後照樣撐得住） |
| `tech:near_package_optics competes_with tech:cpo` | 待判定 → 外部印證 | 「NPO is being evaluated as a practical architectural option…」等 3 段（Credo 官網部落格；主詞是技術節點，具名規則不套——⚠ Credo 自己在推 NPO，是利益相關的技術比較） |

⚠ **順帶發現（抽取錯誤，6.8 的對象）**：`noveon_series_c_2026_01_19`（「Noveon was the first company to reshore full-scale production of sintered rare earth magnets…」）與
`usar_stillwater_phase1a_2026_03_26`（「successful commissioning of its commercial magnet production line (Phase 1a)…」）的引文講的是**它們自己**做磁鐵，卻掛在 `co:mp_materials supplies_to mat:rare_earth_magnets`——引文裡沒有 MP。
舊規則下這條邊另有來源、等級本來就是外部印證，所以 0 條變動；6.4 之後這兩個 origin 會進 `corroboration_withheld.unnamed`。可能的正解是 Noveon／USAR 各自的供貨邊（新的知識主張＝RA，pq2）。
