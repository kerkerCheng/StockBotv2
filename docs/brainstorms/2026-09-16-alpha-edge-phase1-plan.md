# Alpha Edge Phase 1 計畫（PLAN_PROPOSAL 核准版，2026-09-16）

> **性質：** ROADMAP Phase 1「讓邊緣公司浮上排序」的 Z3 PLAN_PROPOSAL，使用者 2026-09-16 核准；
> 本檔是**計畫與工單的紀錄**，讓下一個 session 不必重推。**進度的唯一權威仍是 [`docs/ROADMAP.md`](../ROADMAP.md) 的 Phase 表**
> （本檔的現況數字是當時實測，會腐壞；引用前先跑查證命令）。決定紀錄 D0–D15 在
> [`2026-09-16-alpha-edge-discovery-requirements.md`](2026-09-16-alpha-edge-discovery-requirements.md)。

## 0. 核准紀錄與常設授權

| 決策 | 使用者選擇（2026-09-16） | 意思 |
|---|---|---|
| A | go | ROADMAP Phase 1 驗收行更正（舊句劃線留原地）：L 當時已有 1 檔（IQE 第 28）、三條管道當時已各有 session 手抓的定日文件，照原句什麼都不做就達標 |
| B | 選 1 | 「排序認不出公司自己的名字」納入為 Step 1.0（已完成，見 §2） |
| C | 選 1 | 本 Phase **不改**「外部印證」契約：只有登記表裡的另一家公司能把邊升到外部印證；第三方媒體（DigiTimes、Semiconductor Today…）維持「待判定」。將來要擴充走 C2：已登記出版者的封閉清單（config），每家帶 `tier_cap`，**先量再給**（登記後先只影響研究優先序，量得出它點名的邊事後對不對才參與證據等級；INV-5）。Phase 4 有「幾條邊只有媒體印證」的實數時再開 |
| D | 選 2 | 「瓶頸業務占營收比例」記在**新欄位「產品線營收占比」**（mechanical），不覆寫既有的報導部門占比；本 Phase 只填資料，Phase 4 篩選層決定讀哪一欄 |
| 順序 | 照建議 | 1.0 → 1.1 → 1.2 → 1.3 |

**常設授權（2026-09-16 21:2x 使用者原話：「之後如果需要我核准的事情就幫我繼續 merge to master 不用過我核准」）：**
Step 的 Verdict 為 **GO** 且沒有待使用者決定的問題時，**直接合併 master 並接續下一個 Step，不逐 Step 請核准**。
仍要停下來的：Verdict 不是 GO、有待使用者決定的問題、動到四個人工 gate／資本／append-only authority、要改 `AGENTS.md` 判準句。
**四個人工 gate 不因此放寬**（AGENTS：不因任何理由放寬）：pq2 的圖寫入（`ra_admission`）、Engine C 判讀寫入（`engine_c_observation`）、
thesis mutation、live 仍逐筆核准——研究段落收尾照常給批次指令，使用者一次批。

## 1. Phase 1 的四個 Step

| Step | 做什麼 | 驗收（哪個數字會變） | 前置 | Zoom／Review |
|---|---|---|---|---|
| **1.0** ✅ | 公司名稱解析歸位（見 §2） | 改判 39 條邊、待判定 90 → 53、解析不到 131 → 83、IQE 28 → 12、排序仍 37 列 | — | Z1／R1 |
| **1.1** ✅（[579][580][581] 已 go 入圖） | `fetchers/mfn.py`＋`fetchers/rns.py`（與 `mops.py` 同構；互動式入口，不進無人值守）、`config/source_routes.json` 登記 `.ST`／`.L` 兩階、三條管道各 smoke 一份文件入圖 | 由抓取器產出、meta 帶 `published_at`、經 RA 入圖的文件：MOPS 2 → 3、MFN 0 → 1、RNS 0 → 1；`.ST`／`.L` 各多一階路由且 smoke 後 `verified=true`（查證 `python -m sourcing.routes SIVE.ST`）；IQE going concern 段落由「一手不支持」變可逐字引用；`.codex/rules` fixed entry 仍 20 條且 permission test 明確斷言兩支新抓取器**不在** allowlist | 1.0 | Z1／R1 ×2；sandbox impact review 五步 |
| **1.2** ✅（見 §2c） | 研究項（pq2）：七家補三格（§4 工單） | 可投資排序中 TW／TWO／ST 後綴檔數 0 → ≥1（目標 3；逐檔報進與不進的理由，INV-3）；`substitutability` 覆蓋 80 → ≥86／525；八家「產品線營收占比」4 → 8 | 1.1 的聯亞財報與 Sivers 期中報告；1.0 | 研究路徑（research-drain），不走 development-flow |
| **1.3** ✅（見 §2d） | 收尾：重跑排序、`python -m webapp materialize --ranking`、ROADMAP 回填 before → after、`audit invariants` FAIL 0、全套 pytest、push | Phase completion gate 八項；**TW／TWO／ST 仍為 0 就不得標完成**，只能標「研究已做、證據不足以進榜」並列缺哪份文件 | 1.2 | Z0／R0 |

## 2. Step 1.0 結果（2026-09-16，commit `69c8388`，merge `d06f5bf`）

- 事發：`query/bottleneck.py` 的 origin → `co:*` 解析讀 `getattr(c, "name", "")`，而 `CompanyIdentity` 從來沒有 `name`（100 家 0 家有）；
  測試的假登記表有，所以測試全綠、production 一家都解析不到（L17）。audit 腳本另抄了一份（L16）。
- 改法：`_name_variants()` 讀 `display_name`＋核心名稱＋`aliases`；`_core_name()` 去尾端法律型態 token（封閉清單）；`_strip_annotation()` 去
  origin 尾端一組括號註解；`classify_evidence()` 解析到主詞但同字串另具名他家 → `counterparty_joint`；registry 補 23 家 `display_name`
  （各自財報封面印的字串，commit 內附逐家依據）；假登記表改成真形狀；audit 腳本改匯入。
- 實測：39 條邊改判（升 31／降 8），每條升到外部印證的邊都指得出非主詞登記公司（違規 0）；排序仍 37 列；IQE 第 28 → 第 12（雙方聯合）；
  AVGO→CPO 第 21 → 第 1（Meta 自著論文解析成客戶端）。舊程式跑新測試檔 3 條紅。全套 pytest 2,451 passed／1 skipped。
- **殘餘（下一個 Step 接手）：**
  - Sivers→`tech:wdm_laser_16ch` 由待判定降為供應商自報：Ayar Labs 沒有登記名稱（庫內無其自家文件）。找到 Ayar Labs 自家文件補名即回雙方聯合 → 併入 1.2 的 Sivers 段。
  - 8 家未補名（庫內沒有它們自家文件印的英文名）：聯亞（1.1 抓合併財報時從封面補）、華星光、JL MAG、Schaeffler、住友電工、OpenLight、Niron、SemiNex。
  - Sivers→`tech:cw_dfb_laser` 升到外部印證的來源是華星光的年報（競爭者）：現行契約不分客戶或競爭者，留給 Phase 4。
  - 20 筆 origin 被當註解欄用（括號寫發行人／客戶端／轉載）：1.1 改 `docs/extraction-instructions.md` 時說明 `origin_entity` 只放發布者身分，脈絡放 `title`／`permission_basis`。
  - registry 同時有 `co:openlight` 與 `co:openlight_photonics`，未動。解析器仍住排序模組（原則上該住 identity 層），只收斂成一份、沒搬家。

## 2b. Step 1.1 結果（2026-09-17，branch `alpha-edge/phase1-step1.1`）

- 交付：`fetchers/mfn.py`、`fetchers/rns.py`（與 `mops.py` 同構；`fetchers/utils.py` 加共用 `build_headers`／`html_to_text`）；`mops.py` meta 補
  `published_at`（上傳時間民國轉西元）＋ method／basis／`retrieved_at`；`config/source_routes.json` 加 `mfn`（.ST）／`rns`（.L）兩條 rung2、smoke 後
  `verified=true`；`tests/test_mfn_fetcher.py`（12）、`tests/test_rns_fetcher.py`（10）、mops／routes／permission 各加斷言；OPERATIONS／ARCHITECTURE／
  source-trace skill／extraction-instructions 同步。全套 pytest 2,432＋45 passed；`audit invariants` FAIL 0。
- Smoke 三份落地並 prepare 成 pq2：[579] `mops_3081_separate_financial_statement_202602`（29 頁／26,720 字）、[580] `mfn_sivers_semiconductors_6543505f_att1`
  （22 頁／49,527 字，與手抓版 byte 數相同）、[581] `rns_iqe_9588930`（50,894 字，附註 2.2 Going concern 全段可讀）。**入圖計數（MOPS 2→3、MFN 0→1、RNS 0→1）在
  使用者 go 後才變。**
- 事實修正：§3 寫「聯亞 `--kind consolidated_financial_statement`」——實測聯亞無子公司，114／115 年財報區合併財報 0 份、只有 IFRSs 個別財報；
  抓取器的 INV-3 訊息直接指出換 kind。§3 的 RNS 假設「日期只有文字形式」正確，但一手日期在 RNS 本體 dateline（`IQE PLC / 28 May 2026`），
  頁面 JSON-LD 只是 WebPage；公司頁清單是 AJAX（`/company/IQE/announcements`）。investegate 於 2026-09-16 晚間連續 502 約半小時。
- L11-6 那一筆：`mops_4979_annual_report_2025` 圖裡 `published_at=2026-05-31`，但 MOPS 上傳時間是 115/05/07（→2026-05-07）、年報刊印日 115/03/30——
  三個都不一樣，圖裡那個來自兩份 extraction（`luxnet_4979_annual_report_fy2025.json`、`cw_dfb_substitutability_addendum_2026_08_29.json`）手填。
  方向保守（比真實可得日晚，不是 lookahead），**未動**；列為 1.3 收尾的候選修正（改 extraction 後重載，A1 可重建）。
- 殘餘：RA 的 `storage_permission` 走 `repo_full`＋`raw_text`＝抓取器全文——`repo_excerpt` 會合成「Source URL＋Excerpt」短文而與既存全文衝突，
  這是 intake 與 fetcher 之間的既有整合縫，不在本 Step 修；`retrieved_at` mops 用本機日期、mfn／rns 用 UTC 日期（皆 ≥ published_at）。
  聯亞 `display_name` 仍缺（財報封面只有中文；要英文版年報封面），併入 1.2。

## 3. Step 1.1 的實作事實（本輪已探測，不必重探）

- **MFN（Sivers，`.ST`）：** lead 的 `url` 形如 `https://mfn.se/cis/a/sivers-semiconductors/<headline-slug>-<id>`；單則頁可抓（約 100 KB），
  JSON-LD 內有 `"datePublished":"2026-08-27T16:01:48Z"`（＝RSS pubDate），全文在頁內，附件 PDF 在 `https://mb.cision.com/Main/.../*.pdf`。
  `published_at` 取 `datePublished`，method `filing_metadata`（MFN 是 Nasdaq Stockholm 的法定揭露管道）。瑞典文與英文各發一則、同一事件兩筆 lead，
  以英文版為 doc。⚠ 上一輪探到 404 是 URL 被截斷造成的，不是路由不通。Smoke 文件：Q2 2026 期中報告（既有手抓版 `sive_q2_2026_interim_report` 可對照）。
- **RNS（IQE，`.L`）：** 先前追源成功四次的主機是 investegate：`https://www.investegate.co.uk/announcement/rns/iqe--iqe/<headline-slug>/<id>`；
  頁面 HTML 可抓（約 55 KB），日期只有 `30 June 2026` 這種文字形式，沒有 JSON-LD；`published_at` 用公告日期，method `filing_metadata`。
  後備：LSE `londonstockexchange.com/news-article/IQE/...`（JS 頁，有 JSON API）。iqep.com 的 SSL 鏈與 investis RSS 都壞過（見 `crons/harvest_config.json` 的 rejected_candidates）。
  Smoke 文件：**FY2025 年度業績 RNS 全文**（2026-05-28 前後；HTML 內含財報附註的 going concern 段）——年報 PDF 的查核報告雙欄交錯，pdfplumber 也讀不出來，
  這是 IQE going-concern 待辦卡住的真正原因。
- **MOPS（聯亞，`.TWO`）：** `python -m fetchers.mops --co-id 3081 --kind consolidated_financial_statement --year 115`（民國查詢年度 115 回的是 114 年度）；
  分部附註在 mtype=A 財報；**「主要產品之營業比重」表在股東會年報**（既有 `lmoc_3081_annual_report_fy2025_20260508`，手抓版），兩份都要。
  既有由抓取器產出的入庫文件是 `mops_3363_annual_report_2025`、`mops_4979_annual_report_2025`（published_at 取 MOPS 上傳日，民國年轉西元）。
- **路由表：** `config/source_routes.json` 的 `routes[]` 每筆 `key／label／rung／applies_to=ticker_suffix／suffixes／tier_cap／verified／how／why`；
  `tests/test_source_routes.py` 允許 `verified=false` 的路由列出（`test_unverified_routes_are_listed_not_hidden`），smoke 通過再改 true。
- **Sandbox（五步）：** 兩支新抓取器只連 mfn.se／mb.cision.com／investegate.co.uk，無憑證、只寫 `library/raw/`；**不加** `.codex/rules` fixed entry
  （維持 20 條）；`tests/test_codex_daily_permissions.py::test_fetchers_directory_is_not_broadly_allowed` 加兩條斷言（`fetchers\\mfn.py`、`fetchers\\rns.py` 不在 allowlist）；
  結論寫進 `docs/OPERATIONS.md`「非美股 filing 抓取」節（標題改含 MFN／RNS）；`docs/ARCHITECTURE.md` §4 抓取器那一行同步；
  `skills/source-trace/SKILL.md` 路由行加 MFN／RNS 後跑 `python scripts/sync_agent_skills.py`。
- **測試形狀：** 照 `tests/test_mops_fetcher.py`（doc_id 穩定、日期解析、未知種類拒絕、列表與空集合的分辨）。
- **L11-6 最先壞的那一筆：** `published_at` 的曆法與時區——MOPS 民國年（對照組 `mops_3363` 2026-05-07／`mops_4979` 2026-05-31）；
  MFN 瑞典文與英文兩則必須得到同一個日期；RNS 的 `published_at` 不得晚於 `retrieved_at`（`audit invariants` 的 PointInTime 會抓）。

## 2c. Step 1.2 結果（2026-09-17，commit `3cbb0c0`；六個編號使用者已 go，全部入圖完成）

**驗收三項，兩項達標、一項是誠實的否定結果：**

| 驗收 | 結果 |
|---|---|
| 八家「產品線營收占比」4 → 8 | **7/8**（新欄位 `product_line_revenue_share`，決策 D2 不覆寫 `segment_revenue_share`）。已寫：3081／2455／3363／4979／4971／IQE.L／SIVE.ST；**AEHR 缺**——10-K 全文抽取只得 XBRL 表頭（既知坑），產品別營收要走 XBRL companyfacts 或 EX-99 |
| `substitutability` 覆蓋 80 → ≥86 | 本輪新增 **5 條**帶 sub 的 assertion（聯亞 3；全新 ×2、英特磊 ×2 皆 2），**已入圖**；canonical 邊 529 條、materialized 屬性 358 個（`python -m loader.edge_resolution project`）|
| 可投資排序出現 TW／TWO／ST ≥1 檔 | **❌ 0 檔**——**入圖後複量仍是 37 列、17 家、只有 IQE.L 一檔非美股**。唯一的變化是 IQE.L 由第 12 升到 **第 9**（Tower 客戶端印證讓該邊的證據等級變成「外部印證」）。**這是答案不是缺漏** |

**為什麼 0 檔——四家台系磊晶廠全部低於門檻 4：** 聯亞 3、華星光 2（對照組未動）、全新 2、英特磊 2。
判準不是自由心證：**各家在自家年報逐字互相具名指認對方是同層競爭者**（全新點名聯亞與 IQE、英特磊點名全新與 IQE、
聯亞點名英特磊與 IQE），證據方向一致指向「多家並存的量產供應層」。聯亞判 3 而非 4 的關鍵是**四年長約的條款完全未揭露**
——對照 IQE→Tower 判 4 的依據是雙向最低採購承諾逐字可讀。

**本輪的三個 packet：**
- **[583]** Tower Semiconductor 自家網域公告（`tower_iqe_inp_epiwafer_agreement_2026_06_15`）→ IQE→Tower 邊首次有客戶端自家文件背書，解 [562] 兩項 missing_data 之一（另一項「金額／量／期限」仍缺，需 Tower 20-F 重大合約附件）
- **[584]** 全新＋英特磊各補兩條 supplies_to 邊；兩份年報以 supersede 走廊由手抓節錄升級為抓取器全文
- **[585]** 聯亞 `tech:cw_dfb_laser` sub=3，附三條上下調 disproof

**⚠ 本輪撞到並當下修掉的靜默缺陷（L17）：** MOPS 的 PDF 會吐出 **CJK 相容表意文字**（U+F900–U+FAFF），
與正常字視覺完全相同但碼位不同（4971 年報 50 個、4979 年報 126 個）。逐字引用比對因此靜默失敗，
而失敗長得像「年報沒寫這句」。`pdf_to_text` 已加 NFC 正規化＋兩條測試（空跑檢查通過），OPERATIONS 坑 4 → 坑 5。
**既有入庫的 `mops_4979_annual_report_2025`（126 個）與 `intelliepi_4971_annual_report_fy2025_20260827`（2 個）仍含相容字元**，
清理須走 supersede 走廊——列為 1.3 候選。

**intake 走廊的結構事實（第一版嘗試撞到才知道）：** 同一份 PDF 若以新 doc_id 入圖會被 prepare 端的同 URL 守衛擋下
（會造出兩份 SourceDoc、同一 origin_entity ＝ L8 的假交叉驗證）。正解是**沿用既有 doc_id 走 `supersedes_extraction_sha256`**，
舊版歸檔、兩份都留；本輪三份年報都是這樣升級的。

**入圖收尾（2026-09-17，使用者批次 `579 580 581 583 584 585 go`）：** 六筆全部 apply → commit → push → `todo complete-ra` 結案，
各帶 `action/digest/commit/cohort` 完整 receipt。`audit invariants` FAIL 0｜PASS 13（檢查 4,087 筆）；
`python -m webapp materialize --ranking` 已重算（可行動 37 條／純結構 37 條）。

**⚠ 入圖途中撞到的第二個結構缺陷（已當下修，commit `4f92e06`）：** `commit_pending_intake.py` 對六筆全部回
`modified_tracked_action_path`——supersede **本來就會改既有 tracked 檔**，而 publish 的 preflight 把所有非 `??` 一律當成
「別的 writer 動過」。同一個 `git status` 承載兩種語意（L12），放寬會讓外來修改混進 action commit、收緊會讓 2026-09-11 立的
更正走廊在 publish 這一站死掉。修法是分開：**只有逐份宣告過 `supersedes_extraction_sha256` 的文件路徑**可為 ` M`，
且宣告讀自已被收據 hash 綁定的 extraction 檔，其餘路徑仍要求 `??`。兩條測試（放行面＋收緊面），空跑檢查通過。

**未做完的（1.3 或下一輪接手）：**
- 上詮 `co:foci→tech:fiber_attach_unit` 的 sub **刻意不填**：一手只有自述目標（「長期目標係成為 CPO 光纖陣列元件之主要及重要供應商」）與產能投資，沒有任何客戶端或第三方確認替代難度；Hunterbrook 是媒體，依決策 C1 維持待判定。缺的是 Himax 或 C 公司的具名確認。
- Sivers 15 條邊仍全部未填 sub；Ayar Labs 自家文件仍缺（ayarlabs.com 對本機 UA 回 403）。
- Aehr 補一條到需求錨的邊未做（`tech:cpo_full_stack_test` 實測走不到任何錨）。
- **圖的結構缺口（本輪新發現，不是公司問題）：** `tech:photodiode`、`tech:pluggable_transceiver`、`tech:transceiver_1_6t`、`tech:cloud_transceiver`、`tech:inp_dfb_laser`、`tech:cpo_full_stack_test` 全部**走不到任何需求錨**（實測 shortestPath 回空）。補在這些節點下的供應商邊入圖後仍是排序不可見。

## 2d. Step 1.3 結果（2026-09-17；Z0／R0，只回填文件與核對，未動任何程式）

**四件都做了：** ①ROADMAP Phase 1 驗收行回填 before → after（舊句劃線留原地）；②completion gate 八項逐項核對
（結果寫進 ROADMAP「Phase 1 completion gate 逐項核對」，含每項的查證命令）；③Phase 1 **維持 ▶ 不標 ✅**；
④未做完清單的去向交回使用者決定（見下）。**所有數字都是本輪現跑，沒有抄計畫檔。**

**驗收三項的誠實結果：**

| 驗收 | 目標 | 實測（2026-09-17） |
|---|---|---|
| 可投資排序出現 TW／TWO／ST | ≥1（目標 3） | **0，未達** |
| `substitutability` 覆蓋 | 80 → ≥86 | **85／529，未達，差 1 條** |
| 八家「產品線營收占比」 | 4 → 8 | **7**（AEHR 缺） |

**⚠ 上一輪漏記的一筆：** §2c 只寫「新增 5 條帶 sub 的 assertion，已入圖」，沒有回頭對驗收門檻 ≥86——
**5 條 ≠ 6 條，這一項是未達不是達標**。（L14：驗收條件是「現有資料有幾筆真的變了」，不是「這一步回傳成功」。）

**completion gate 八項全部過，但兩個必須寫下來的觀察：**
1. **§9 的「各 Phase 🔴 責任分配」表用的是舊 refactor 的 Phase 編號**（contracts／Portfolio-Risk／
   vertical slice／Engine D 分解…），**與 Alpha Edge 的 Phase 0–7 沒有任何對應關係**。第 8 項只能改成
   對照「本 Phase 實際動到哪些事故的形狀」（F-20 排序截斷、F-31 as-of 定日，兩筆在 §1 都已是 ✅）。
2. **`historical-failure-matrix.md` §4 的「✅17／🟡9／🔴10」是已腐壞的快照**——2026-09-17 逐列重量是
   **✅21／🟡8／🔴7**。ROADMAP 引用它的那句與該檔本身都已劃線改正並附一行可執行的計數命令。

**收尾時新發現的一檔（不在 Step 1.2 的七家工單裡）：**
**穩懋 `co:win_semiconductor`（3105.TWO）→ `co:sivers_semiconductors`，證據已是「外部印證」、`substitutability` 未填。**
它是台股裡**證據等級最高而只差一格**的一條邊，卻從來沒進過工單——因為工單是從「D7 初始三檔＋圖裡已知的邊緣公司」
手列的，不是從「門檻 filter 的 filtered 清單」機械導出的（L16：分類有 SSOT，但沒跟著資料送到需要它的地方）。

**門檻 4 的 filter 逐檔報表（INV-3）：** `input 222｜accepted 37｜filtered 185`；filtered 的理由只有三種——
`substitutability` 未填 **162**、`=3` **15**、`=2` **8**。**沒有一檔是因為走不到需求錨被濾掉。**
逐檔的「缺哪一份文件」寫在 ROADMAP 的 completion gate 節，不在此重複。

## 2e. 未做完清單（Step 1.2 的四件 ＋ Step 1.3 新增兩件）——**去向待使用者決定**

| # | 項目 | 性質 | 兩個候選去向 |
|---|---|---|---|
| 1 | 上詮 `co:foci` 的 sub 刻意不填（缺 Himax 或 C 公司具名確認） | 研究（等外部文件） | 另立 pq2 `pending --trigger`／併 Phase 4 |
| 2 | Sivers 15 條邊仍全部未填 sub；Ayar Labs 自家文件仍缺（403） | 研究 | 另立 pq2／併 Phase 4 |
| 3 | Aehr 補一條 `tech:cpo_full_stack_test` → 需求錨的邊 | 研究（補邊） | 另立 pq2／併 Phase 4 |
| 4 | 六個 tech 節點走不到任何需求錨（`photodiode`／`pluggable_transceiver`／`transceiver_1_6t`／`cloud_transceiver`／`inp_dfb_laser`／`cpo_full_stack_test`） | **圖的結構缺口**，不是公司問題 | 併 Phase 4 篩選層（需求側 vs 供給側正是它要分的）／另立開發項 |
| 5 | **穩懋 3105.TWO 那條邊補 sub**（證據已外部印證，只差一格） | 研究 | 另立 pq2／併下一輪補格 |
| 6 | **`mops_4979_annual_report_2025` 的兩個殘留**：圖中 `published_at=2026-05-31`，但 MOPS 上傳日是 2026-05-07（方向保守，非 lookahead）；同一份文件仍含 126 個 CJK 相容表意文字 | 資料更正（走 supersede 走廊，屬 `ra_admission`） | 另立 pq2／併下一輪 |

⚠ **第 6 項兩個問題在同一份文件上，正解是一次 supersede 同時修掉**，不要分兩次改同一份 extraction。

## 2f. §2e 六項的處置結果（2026-09-17，使用者「六項照你建議」＋批次 `587 588 589 590 go`）

| # | 編號 | 結果 |
|---|---|---|
| 1 | **[586]** | 已設 `pending --trigger`：等 Himax 或長約對手方首次具名確認。不需要使用者動作 |
| 2 | **[588] ✅** | Sivers 補兩條邊（`tech:dwdm_laser_array`、`co:o_net_technologies`）**皆判 2**，入圖待 **[594]** |
| 3 | **[589] ✅** | ⚠ **前提是錯的**——要補的那條邊已經存在，見下 |
| 4 | — | 併入 Phase 4，並把診斷更正為四種成因（見 ROADMAP Phase 4 那一列） |
| 5 | **[587] ✅** | 穩懋補 substitutability **判 2**，入圖待 **[591]** |
| 6 | **[590] ✅** | **不需要入圖核准**——見下 |

**三個值得記的結果：**

1. **[589] 的前提被實測推翻。** 工單說「先補邊再補格」，但圖裡**已經有**
   `tech:cpo --constrained_by--> tech:cpo_full_stack_test`。真正的卡點是
   `query/bottleneck.py` 的 `UPSTREAM_RELATIONS = ("enables", "is_component_of")` 不含 `constrained_by`，
   所以 `build_upward_index` 跳過它。**那是開發項不是研究項**，而且本輪明確不得改排序邏輯。
   ⚠ **刻意不用「再補一條 relation 不同但語意相同的邊」去繞過 traversal**——那是用資料操弄排序，比改程式更糟。
   順手查另外五個節點，發現六個「走不到錨」其實是**四種成因**（constrained_by 未走訪／`enables` 一表兩義／
   真的沒有需求方邊／鏈長），全部寫進 ROADMAP Phase 4。

2. **[590] 比預期輕：不需要 `ra_admission`。** ①`published_at` 2026-05-31 → 2026-05-07 走既有機械路徑
   （`scripts/backfill_source_dating.py --supersede`，AGENTS 明列既有 SourceDoc 的 `published_at` 回填屬 mechanical、免 pq2）；
   舊值不對應任何一手日期，很可能是月精度 `2026-05` 被取成月底。
   ⚠ 方向要明記：新值比舊值**早**三週，as-of 投影是**擴大**可見範圍不是縮小。
   ②CJK 相容表意文字：實測**兩份 extraction 與圖裡本來就都是 0 個**，126 個只存在於 `library/raw` 全文；
   重抓後全文經 NFC 與舊檔**逐字相同（88,393 字完全一致）**，證明只有相容字元被修掉、沒有任何內容位移。
   ③新發現（不在該項範圍）：`mops_4979_annual_report_2025` 沒有 canonical extraction，
   兩份其他檔名的 extraction 共用該 doc_id、且 url 是手造的 `mopsov.twse.com.tw` 路徑——
   **刻意不順手修**，造 canonical extraction 有機會在圖裡產生第二份 SourceDoc（L8 假交叉驗證的形狀）。

3. **Phase 1 的「八家產品線營收占比」由 7 補到 8／8，達標。** AEHR 的那一格不需要 XBRL companyfacts
   ——`revenues by product category` 表本來就在 10-K 正文裡（`mo_5a56be9daaef6ad94fd42bab4ee9093a`）。
   ⚠ 順帶發現：Engine C 既有的 `segment_revenue_share` 對 AEHR 存的是同一張表的同一組數字，
   代表「報導部門」與「產品線」被當成同一件事。

**⚠ 四項研究全部得到否定結果：穩懋 2、Sivers DWDM 2、Sivers→O-Net 2，加上先前的聯亞 3、華星光 2、全新 2、英特磊 2。
七家台股加 Sivers，沒有一條邊達到門檻 4。** 共同形狀是同一個：**夥伴關係公告很多，契約條款一條都沒有**
——而 IQE→Tower 判 4 的唯一依據就是雙向最低採購承諾逐字可讀。
這不是門檻太嚴，是這批標的目前真的沒有那種證據。

**Ayar Labs 缺口的性質改變了（[588] 最值得記的發現）：** 先前記為「ayarlabs.com 對本機 UA 回 403」，
本輪換路徑重試後發現——**Ayar Labs 現行網站上查不到任何具名 Sivers 的頁面**（`/press-releases/` 404、
`/news/` 八則公告無一提及、兩個搜尋索引還留著的舊 slug 一個重導一個回 JPEG、`/supernova/` 不具名任何供應商）。
**不是 UA 被擋，是內容已從現行站台移除，重抓不會解決。**
依 OPERATIONS「斷鏈要不要重新下載補檔，取決於來源可不可變」，公司 newsroom 頁不可重抓；
**Wayback 快照算不算一手是一個要先決定的契約問題**，本輪刻意不做。


## 4. Step 1.2 工單（七家；2026-09-16 實測現況）

| 公司 | 向下邊 | 卡點 | 要做的事 |
|---|---|---|---|
| 上詮 `co:foci` 3363.TWO | 1（→ `tech:fiber_attach_unit`）| sub 未填；3 份文件含 DigiTimes、Hunterbrook（媒體，維持待判定） | addendum 補 sub；找客戶端文件（Himax 是 partnership 邊的另一端） |
| 聯亞 `co:landmark_optoelectronics` 3081.TWO | 1（→ `tech:cw_dfb_laser`）| sub 未填；只有自家 MOPS 公告（2026-08-26 CW 雷射長約，客戶未具名） | 補 sub；補 `display_name`；客戶端文件待長約對手方揭露 |
| 華星光 `co:luxnet` 4979.TWO | 1（→ `tech:cw_dfb_laser`）| **sub 已判 2**（Borecraft 論壇＋年報） | **只重看、不得為進榜改判**；這是 1.2 的對照組 |
| 全新 `co:vpec` 2455.TW | **0** | 沒有任何瓶頸邊；年報 SourceDoc `vpec_2455_annual_report_fy2025_20260508` 已入圖 | **補邊**（addendum extraction，edge id 用唯一前綴，見 OPERATIONS「Addendum extraction 的 edge id 陷阱」） |
| IET-KY `co:intelliepi` 4971.TWO | **0** | 同上；`intelliepi_4971_annual_report_fy2025_20260827` 已入圖 | 補邊 |
| Sivers `co:sivers_semiconductors` SIVE.ST | 15，全部 sub 未填（一條為 2） | 需求錨走 GF 到成熟製程；`prod:els_8ch_module` 那條已外部印證（Enablence） | 挑 2–3 條關鍵邊補 sub（→ `co:ayar_labs`、`tech:wdm_laser_16ch`／`tech:dwdm_laser_array`、→ `co:globalfoundries`／`prod:gf_scale`）；找 Ayar Labs 自家文件補名 |
| Aehr `co:aehr_test_systems` AEHR | 1（→ `tech:cpo_full_stack_test`）| sub 未填，且**走不到需求錨** | 補 sub＋補一條到需求錨的邊（`tech:cpo_full_stack_test` 往 `tech:cpo`／`tech:ai_switch`） |
| IQE `co:iqe` IQE.L | 4 | 已在榜（第 12，雙方聯合）；[562] 補獨立來源仍開 | 不需研究；[562] 併入本段一起處理 |

**機制：**
- 開工時 `python -m engine_b.todo add "D8 補三格研究工程（七家）" --hint ...` 鑄 `manual` 編號，依「使用者主動指示＝已授權」受理時即 `go` resolve，receipt 註明出自決定紀錄 D8 與本計畫核准。
- 每份 graph delta：addendum extraction → `scripts/prepare_research_action.py --action-file library/leads/action_drafts/<x>.json` → `ra_admission` 編號 → 收尾批次指令一次批。
  先例：`extractions/iqe_tower_epiwafer_sub_addendum_2026_08_30.json`（[271]）。
- 「產品線營收占比」：先在 `config/engine_c_observation_fields.json` 登記新欄位（category `profitability`、authorities `engine_c_financial`／`engine_c_manual`、
  `verifiability=mechanical`、`gate_member=false`），⚠ `tests/test_engine_c_observation_fields.py::test_every_registered_field_is_citable_by_at_least_one_axis`
  要求新欄位被至少一個 axis 引用（Q3 盈餘曝險）——同 change 處理；資料用 `python scripts/record_mechanical_observation.py --ticker <T> --field <新欄位> --value '{...}' --source-ref "<年報 主要產品之營業比重 表>" --as-of <期末>`，免 pq2。
  八家現況：`segment_revenue_share` 已填 3081、3363、SIVE.ST、AEHR；缺 4979、2455、4971、IQE.L。
- 每消一格 `python -m webapp materialize <TICKER>`；段落收尾附建議摘要與批次指令。
- 題源排序照 OPERATIONS「自主研究迴圈」；**先 grep 自家庫**（上詮、聯亞、Sivers 的文件都已在庫）。

## 5. 不得做（沿用啟動 prompt）

部位尺寸、下單、連 broker、放寬四個人工 gate 或 L8、因籃子空而放寬條件（門檻 4 不動、華星光不改判）、把 last30days 串進無人值守管線、
擅自把新抓取器加進 Daily 的 fixed entry、改排序演算法或五級證據字彙。

## 6. 現況查證命令（引用前先跑）

```
python -m query.bottleneck --top-n 60                         # 37 列；IQE 第 12；TW/TWO/ST 0
python -m sourcing.routes SIVE.ST                              # .ST 今天 4 階、無交易所階
python -m audit invariants                                     # FAIL 0｜PASS 13
python -c "import json;d=json.load(open('config/company_identity.json',encoding='utf-8'));print(sum(1 for c in d['companies'] if c.get('display_name')))"   # 27
python -m engine_c.set_manual_field --list 4979.TWO            # 產品線占比缺的四家之一
```
