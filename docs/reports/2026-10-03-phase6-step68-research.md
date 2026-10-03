# Phase 6 Step 6.8 研究收據（2026-10-03 台北 12:4x–14:xx）

plan：`docs/plans/2026-10-02-002-feat-phase6-evidence-criteria-plan.md` §9。單一 writer：`scripts/writer_guard.py acquire --minutes 120`（13:04）→ 寫完 `release`。
原網頁一律 2026-10-03 重新抓（scratchpad `p68_pages/`；Python 憑證庫過期的兩份改用 curl，WebFetch 只當備援、不拿它的轉述當逐字）。
量測腳本：`p68_withheld.py`（清單）、`p68_candidates.py`（原檔裡的具名句，名字比對走唯一 owner `quote_names_company`）、`p68_grep.py`（HTML 逐字）、
`p68_build_drafts.py`／`p68_prepare_all.py`（RA 草稿與 prepare）、`p68_down22.py`（對 6.0 基準逐條）。

## 0. 結論

| 項 | 結果 |
|---|---|
| 本 Phase 降級 22 條的去向 | **補引文 RA 6 條**（4 份文件 → pq2 [673]–[676]）、**身分修正 4 條**（[670]）、**6.3b 定案 3 條**（GSR 是媒體）、**維持降級 8 條**＋**延後 1 條**（各附理由） |
| 補引文落地後（預期，以 apply 當下重算為準） | `corroboration_withheld`：未具名 13 → **8**、轉述 2 → **1**；外部印證 +6 |
| 重讀讀圖 | InP `sr_bac985bacbea64b7` → **`sr_b8b405c96d8747c1`**、CW DFB `sr_d49b81b6465e1181` → **`sr_00e18cf604cc66b9`**（判讀都仍是 volume）；四份讀圖全部 current |
| 四檔敘事 | **LITE** 改一句措辭＋重押讀圖（`ib_c8dd6783f5fd2dd2`）；**AXTI／COHR／SIVE.ST** 七格文字不改、只重押讀圖（`ib_8c35bc994d0c1047`／`ib_0c22f37bf4b8052c`／`ib_c9445bd7b28f7fcf`） |
| 作廢的 staging 紀錄 | [677]、[678]：建議 drop（見 §2） |

## 1. 降級 22 條逐條（對 6.0 凍結基準 `evidence_classes_2026_10_03`）

### 1.1 補引文 → RA（原網頁有具名、而且就是撐這條邊的那一句）

| 邊 | 6.0 → 現在 | 原文（逐字，2026-10-03 重抓核對） | 去向 |
|---|---|---|---|
| `co:coherent supplies_to tech:cpo_fiber_attach` | 外部印證 → 待判定 | NVIDIA 開發者部落格 `<li><strong>Browave, Corning, Senko, TFC Communication, and Coherent:</strong> Industry experts with optical connectors and fiber assemblies for linking the ELS lasers with polarization, maintaining fibers into the silicon photonics engine, and data output to the front panel.</li>` | **[673]**（新增 s7） |
| `co:fabrinet supplies_to tech:cpo_packaging_assembly` | 外部印證 → 待判定 | 同頁 `<li><strong>Foxconn and Fabrinet:</strong> These partners provide expertise in system-level CPO assembly and testing, …</li>` | **[673]**（s8） |
| `co:sumitomo_electric supplies_to co:nvidia` | 外部印證 → 待判定 | 同頁 `<li><strong>Lumentum, Sumitomo, and Coherent:</strong> These vendors provide ELS assembly, optical alignment, and test with the silicon photonics engine.</li>` | **[673]**（s9） |
| `co:coherent depends_on tech:inp_6inch_fab` | 外部印證 → 待判定 | NVIDIA 部落格導言「Coherent’s expansion at its Sherman, Texas, campus scales what it calls the world’s first volume production 6-inch indium phosphide fab, a key supplier across NVIDIA’s AI stack.」 | **[675]**（s6） |
| `co:lumentum supplies_to co:nvidia` | 外部印證 → 待判定 | NVIDIA 新聞稿開頭段「NVIDIA today announced multiyear strategic agreements with Lumentum Holdings Inc. (NASDAQ: LITE) to accelerate innovation in advanced optics technologies, …」（緊接的下一段就是既有 s2 的採購承諾） | **[676]**（s5） |
| `co:lumentum supplies_to tech:els_pluggable_module` | 外部印證 → 自報·filing（轉述） | Cignal AI 公開段、Cignal 自己的分析「Some of the most vertically integrated vendors, such as Coherent and Lumentum, are already pivoting to supplying other component parts (e.g. ELSFPs) into CPO.」 | **[674]**（s5；**不**宣告整份 independent——那會連兩句轉述一起豁免） |

計畫原本預期「NVIDIA 部落格的角色描述沒點名」——**實際有**：原抽取的 locator 就寫著表頭名單，只是 quote 只抄了冒號後半句。
三份 NVIDIA 文件的發話者都是 NVIDIA（這幾家的客戶）自己的敘述，不是引述供應商。

### 1.2 身分修正（名冊無名可比）→ [670]

`co:nava_thailand supplies_to tech:cloud_transceiver_1_6t`、`co:openlight_photonics` 的 3 條（develops ph18da／partnership_with Tower／supplies_to NewPhotonics）：
不是讀原文能補的——nava 沒有名字、兩個 OpenLight 代號共用每個寫法。pq2 [670] 的合併與退役落地後由那一份的預告接手（baseline §16、§18.2）。

### 1.3 6.3b 定案（GSR 是媒體）

`co:axt supplies_to mat:inp_substrate`（外部印證 → 自報·filing）、`co:coherent supplies_to tech:cw_dfb_laser`、`co:lumentum supplies_to tech:cw_dfb_laser`（外部印證 → 媒體轉述）：
撐外部印證的是 Global Semi Research 兩份文件（`gsr_inp_substrate_market_2026_05_16`「U.S.-based AXT including its Chinese subsidiary Beijing Tongmei (~36% share, …)」、
`gsr_cpo_not_delayed_2026_06_10`「Nvidia's guidance to Coherent and Lumentum for high-power CW lasers climbed …」）。6.3b 依使用者定案把 GSR 登記為媒體（轉述廠商資料）、
沒有宣告 independent，所以不再算第三方——**維持**（不是讀原文的題）。

### 1.4 維持降級（附理由）

| 邊 | 6.0 → 現在 | 原文查到的 | 理由 |
|---|---|---|---|
| `co:agility_robotics constrained_by comp:humanoid_precision_actuators` | 外部印證 → 媒體轉述 | SVRC 原頁 actuator 段「Actuator dependency — ~5% of global actuator supply. Series elastic actuators, quasi-direct-drive motors, and precision reducers overwhelmingly sourced from Japan, Germany, and China.」 | 講的是全美國總量；點名 Agility 的句子都在講出貨量與客戶合約，沒有一句把 Agility 和 actuator 連起來 |
| `co:apollo invests_in co:broadcom` | 外部印證 → 待判定 | Broadcom 法說「…with Apollo and Blackstone…」「…currently being launched by Apollo.」 | 原文只寫「Apollo」，全份 0 處「Apollo Global Management」；「Apollo」不能當寫法（Google 的 Apollo OCS 專案代號，6.3a／§0.6 #6） |
| `co:broadcom supplies_to tech:cpo` | 外部印證 → 待判定 | NextPlatform 轉載裡 Meta 自己的話（「…the techies at Meta Platforms write in their paper…」）都沒寫 Broadcom；點名 Broadcom、講 Bailly 的是 NextPlatform 自己的敘述 | origin 是 Meta，要 Meta 自己的話具名；「Bailly」是產品名不是公司寫法。ECOC 論文全文沒取得。線索（未查證，抓取逾時、本步不追新來源）：Broadcom 2025-10-01 GlobeNewswire 新聞稿可能有 Meta 主管引言——若要補是一份新文件的 RA |
| `co:hyundai_mobis supplies_to co:boston_dynamics` | 外部印證 → 待判定 | BD 官網「Hyundai Mobis announced that it has formed a strategic collaboration with Boston Dynamics…」「The company stated on the 7th that it will supply actuators for Atlas…」 | 撐邊的那一句（The company stated…）沒具名；整段是 Hyundai Mobis 的新聞稿掛在 BD 官網、主張的發出者是供應商（L8）——拼兩句補名字會把轉述算成客戶印證。origin 該不該改成 Hyundai Mobis 列結案待決 |
| `co:mp_materials supplies_to mat:separated_heavy_reo` | 外部印證 → 媒體轉述 | USGS「…provided a rare-earths producer in Mountain Pass, CA, with a $150 million direct loan…」 | 只寫地點，全份 0 處點名 MP Materials |
| `co:sivers_semiconductors supplies_to tech:cw_dfb_laser` | 外部印證 → 自報·filing | 華星光年報「本公司自 2019 年即與策略合作夥伴共同開發 CW DFB Laser 晶粒的研發及量產…」 | 年報兩份文字檔共 12,089 句、0 處點名 Sivers（讀圖 sr_d49b81b6465e1181 早已在文中更正） |
| `co:tsmc supplies_to tech:mrm_200g` | 外部印證 → 媒體轉述 | TrendForce「As noted by Economic Daily News , TSMC has announced that the world’s first 200Gbps micro-ring modulator (MRM) based on its COUPE platform is scheduled to enter mass production later in 2026.」 | 唯一具名 TSMC 的那句是轉述 TSMC 自己的宣布——補進去只會從「未具名」換成「轉述句」，證據等級不變；依 L14 不鑄號 |
| `co:coherent supplies_to tech:uhp_laser` | 外部印證 → 媒體轉述 | Cignal「…Coherent announced a PO for its high-power laser for the same application.」；Cignal 自己那句講的是 ELSFP 等零組件 | 講高功率雷射本身的只有轉述句；Cignal 自己的分析句不撐「高功率雷射」這個節點（L6：型號要在 quote 裡） |

### 1.5 延後（附到期）

`co:lumentum supplies_to tech:uhp_laser`（外部印證 → 待判定）：同一份 NVIDIA 新聞稿撐的，但這條邊住**另一份抽取檔** `lite_uhp_sole_source_downgrade_addendum_2026_08_30.json`
（同一個 doc_id、不同檔名）。更正走廊以 `extractions/<doc_id>.json` 定位，改不到它；在主抽取檔加同一條邊會撞上 assertion id（`{doc_id}_{本地 id}`，重建時 `source_ids` 誰後載誰贏）
或在同一份文件下多一筆重複 assertion。**附錄抽取檔怎麼歸位**是使用者的題——列進 Phase 6 結案待決（plan §14），到期＝結案當天。

## 2. 鑄號（pq2）

| 編號 | 內容 | action／digest | 預告（prepare 當下對圖算） |
|---|---|---|---|
| [673] | NVIDIA 矽光子部落格：三段原文完整條目 | `ra_309e724ef12a11cba6209f646508fcd0`／`7a91ad0ea647597f8c2ff4b381f02d44d43c6c9ea75d68dad0a568cd6e0fff92` | 3 條 待判定 → 外部印證；節點副作用 0 |
| [674] | Cignal AI：Cignal 自己的分析句 | `ra_685dc8b9f0e3ecc4cab9a05d18bd80aa`／`9ec76e5c0df7444aa1d698dbbd3cd20eb82060da2618edbdf56c1d24fca470c5` | Lumentum→ELS 自報·filing → 外部印證；副作用 0 |
| [675] | NVIDIA 部落格（Coherent 德州廠）導言句 | `ra_78f65e23e9e0aa5b16ef465c97a977bd`／`3269f78e40c783953b5fad215f46d2c057bcc0dedd1b2ac60f4f4d4d081dc5c6` | Coherent→6 吋 InP 廠 待判定 → 外部印證；副作用 0 |
| [676] | NVIDIA×Lumentum 新聞稿開頭句 | `ra_a9e346764dd6cb73f401361e19a65ed7`／`fd72368d33fbaec2f91ac8b92a5a36092740f3ea9b8bb687a71c2c1c5b9cfd31` | Lumentum→NVIDIA 待判定 → 外部印證；副作用 0 |
| [677] | **作廢**：[673] 的第一版 | `ra_df9ac0489f8fe0bcff47f21a94656a49` | 重載會把 `co:coherent` 的 role、`co:sumitomo_electric`／`co:nvidia` 的層級與 role 蓋掉 → 對齊後重做成 [673] |
| [678] | **作廢**：[676] 的第一版 | `ra_edc4a9c802866376d8c8d6c230ea55ef` | 重載會讓 SourceDoc `retrieved_at` 從 2026-08-30 倒退回 2026-07-21 → 對齊後重做成 [676] |

四份草稿都從現有抽取檔複製：**只新增來源與 `source_ids`、舊來源一字不動**（`Source` 是 append-only 的證據，loader 對 quote 是 `coalesce($quote, s.quote)`——
改舊 id 的逐字會把它洗掉）；`supersedes_extraction_sha256`＝`intake.provenance.canonical_extraction_hash`（現存檔）；節點宣告照抄圖上現值
（`loader.migrate_identity_cleanup.plan_extraction_edit` 的 `align_nodes_to_graph`，6.2 偏差 §0.6 #4 同一條規則）；摘錄只傳本文（不帶表頭——baseline §0 的重複表頭事故）。
action 紀錄沒有「撤回」狀態，[677]／[678] 只能由 pq2 drop（drop 的 `ra_admission` 不會換號重生：`engine_b.todo` 的 `_dropped_before`）。

批次指令（含先前的 [670]–[672]）：`670 go 671 go 672 go 673 go 674 go 675 go 676 go 677 drop 678 drop`

go 之後（每一號）：`python scripts/apply_ra_admission.py --pq2 <N> --digest <上表 digest>` → `python scripts/commit_pending_intake.py` → `python -m engine_b.todo complete-ra <N> --digest <digest>`。

附帶發現（不擋）：`nvda_lumentum_partnership_pr_2026_03_02_s3`（high-performance lasers, modules, and optical subsystems…）其實出自新聞稿末尾的「About Lumentum」——
Lumentum 自己的公司簡介；`library/raw` 摘錄把它寫成「Lumentum will provide …」也不準確（L18：標籤要指得回原文）。本步不覆寫既有逐字，列結案待決。

## 3. 重讀讀圖

| 節點 | 舊 → 新 | 標籤變動（--check） | 判讀 |
|---|---|---|---|
| `mat:inp_substrate` | `sr_bac985bacbea64b7` → **`sr_b8b405c96d8747c1`** | Sumitomo、JX 供貨 待判定 → 外部印證；Lumentum 需求 自報·filing → 外部印證（[666]：Reuters 宣告 independent） | volume 不變：升的是印證強度不是可替代性（仍 3／3／3） |
| `tech:cw_dfb_laser` | `sr_d49b81b6465e1181` → **`sr_00e18cf604cc66b9`** | Coherent、Lumentum 供貨 供應商自報 → 媒體轉述（GSR）；Sivers 外部印證 → 自報·filing；反向路徑 Blazar 待判定 → 媒體轉述 | volume 不變：供給側六條仍沒有具名的客戶端或第三方印證；反證②措辭更新 |

引用與反證照原順序複製（反證出處：原本寫 self 的指回被取代那份）；反證 watch 換新（InP 7、CW DFB 6，舊的收掉）。寫入後四份讀圖 `--check` 全部 current（到期 90／90／89／82 天）。
[673]–[676] 會改等級的 7 條邊**都不在任何一份現行讀圖的角度裡**（`p68_ra_vs_readings.py`），go 之後不會因此 stale。

## 4. 四檔 v2 敘事

| 檔 | 跟它有關、對 6.0 變了的邊 | 文字有沒有依賴舊標籤 | 處置 |
|---|---|---|---|
| AXTI | `co:axt supplies_to mat:inp_substrate` 外部印證 → 自報·filing | 沒有：需求格本來就寫「都是 AXT 自己在 8-K／10-Q 揭露的合約條款，客戶端還沒有自己的原文」；瓶頸格靠的是 Coherent、Lumentum 自己的話 | 文字不改；**只重押讀圖** → `ib_8c35bc994d0c1047`（反證 3 條連結改指新讀圖同編號的 watch） |
| COHR | Coherent 的 6 吋廠、光纖、CW DFB、UHP，Lumentum／Sivers 的 CW DFB | 沒有：瓶頸格「它自報的替代難度最高，但沒有客戶端或第三方印證」與降級後一致；「NVIDIA 部落格把 Lumentum、住友電工和它並列」與原文相符 | 文字不改；**只重押讀圖** → `ib_0c22f37bf4b8052c` |
| LITE | Lumentum→NVIDIA、CW DFB、ELS、UHP，Coherent／Sivers 的 CW DFB | **有一句**：「它那條供貨邊是**自報**、沒有外部印證」——現在那條邊是媒體轉述（GSR）；「沒有外部印證」仍成立，「是自報」是舊標籤（L11-1：措辭精度本身是 claim） | **改這一句＋重押讀圖** → `ib_c8dd6783f5fd2dd2`；其餘六格、候選狀態（不要）不變 |
| SIVE.ST | Sivers／Coherent／Lumentum 的 CW DFB | 沒有：「它那條供貨邊只有自家年報、沒有外部印證」正是降級後的標籤 | 文字不改；**只重押讀圖** → `ib_c9445bd7b28f7fcf` |

**為什麼文字不改也要寫新版**（plan §9 第 4 項原本只寫「不依賴就寫不換版理由」）：敘事的 `rides[]` 釘著讀圖 id，讀圖換版後
個股頁論證段的需求端會印「押的那份讀圖已不是現行——需求端要等敘事重寫才說得出來」，候選判定也只認 current／stale_low。
照 Phase 4 Step 4.8（SuperNova 重讀後 SIVE 只重押讀圖）的先例。scratchpad materialize 四檔核對：押的讀圖全部 current、論證段 0 處「要等敘事重寫」。

## 5. 不做（plan §9 第 5 項）

沒改 thesis、沒入圖（只鑄 RA 號）、沒動候選狀態以外的判斷；候選板「可開」照實印。
