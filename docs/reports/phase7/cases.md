# Phase 7 case 表（cases）

> **性質：評估檔。** 每個 case 一段，開題時只放「登記見 registration §2」；之後的研究產出、裁決、2×2、failure log 條目**都在該段下 append**，不改舊行。
> **只寫 id**（`sr_*`、`ib_*`、`ew_*`、`hy_*`、lead id、RA id、pq2 編號、SourceDoc id）——研究本身照常寫進各自的 ledger／registry、照常走四個人工 gate；
> 本檔不是第二個狀態源（lead、pq2、watch 的狀態只住各自的 registry）。判讀規則、時點定義、「錯」的分法、2×2 的錨點：見
> [`registration.md`](registration.md) §0、§3。評估永遠用登記當時那一版（registration §0 第 4 條）。
>
> 段內四格（plan 附錄 B）：**研究產出**｜**裁決**（每次一行：日期｜文件｜結論｜「錯」的 kind）｜**2×2**｜**failure log 條目**（寫 `failure-log.md` 的編號）。

## 2×2 彙總（每列一份判斷；registration §3.3）

| case | 被評的判斷（id） | 結構斷言：證實／推翻／尚未到裁決點 | 錨點 | 對該鏈組超額（量測日） | 格 |
|---|---|---|---|---|---|
| O3 | `ib_b36ecf9dc00459d9`（不要：不是瓶頸） | 證實（依既有證據：付錢方向一手，2026-10-04） | 2026-10-04 | 7.5 記 | 待 7.5 |
| O4 | `ib_27713885500a7607`（不要：讀不出卡在它——量、產能、長約都是自報，客戶端沒有一手） | 尚未到裁決點（Q3 財報 11 月上旬；`hy_0004` 到期 2026-12-31） | 2026-10-05 | 7.5 記 | 待 7.5 |

---

## O1 AXTI／InP 基板

- 登記：registration §2 O1（開題 2026-10-04）
- 研究產出：（尚無）
- 裁決：（尚無）
- 2×2：尚未到裁決點
  - 2026-10-05｜research-drain 段 5：InP 基板層的兩家日本大廠第一份敘事（押 `sr_b8b405c96d8747c1`，不要：非邊緣）——住友電工 `ib_456a9bf890f61d5c`、JX 金屬 `ib_eab1aee5a0c458ce`；會死嗎先用一手決算短信補 runway 觀測（`mo_4083f561…`、`mo_a200134b…`：現金跑道綠、負債黃）
- failure log：（尚無）

## O1-U InP 上游：銦、晶體生長、出口管制（二階）

- 登記：registration §2 O1-U（開題 2026-10-04）
- 研究產出：（尚無）
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
- failure log：（尚無）

## O2 SIVE.ST／CW DFB 與 ELS

- 登記：registration §2 O2（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜lead_f1694626 → `ra_b85b2836cd650508c1c0ca9ffdbce88d` → pq2 **[680]**（華星光 EML 2H26 初始出貨、CW／EML 晶片代工、誼虹關係人流程；SourceDoc `mops_4979_investor_conference_20260828`）；舊版 [679] 待 drop（failure log #3）
  - 2026-10-04｜lead_43890d74 → `ra_08f8b529fc5e049dde9a5c0439e7451b` → pq2 **[682]**（Sivers 的代工穩懋：CW-DFB、EML 標「Ongoing Qualification」、6 吋 InP developing；SourceDoc `mops_3105_company_presentation_20260909`）
  - 2026-10-04｜使用者 go：[680] 入圖（intake commit `c842321b`）、[682] 入圖（`6c119121`）；[679] drop（舊版重複號）
  - 2026-10-04｜[682] 入圖讓 CW DFB 層讀圖 stale（`supply_added` co:win_semiconductor，**同時觸發反證①「供給側出現第七家」**）→ 重讀 `sr_3a4fe5719994dfdc`（取代 `sr_00e18cf604cc66b9`）：維持 volume、**窗口變短**——第七家是 Sivers 自己的代工穩懋、CW-DFB 仍在合格（代工產能進場＝量被補上的形狀，不是新的設計對手）；反證①改寫成「第八家」、新增⑦「穩懋 CW-DFB 改標量產或客戶具名其代工的 CW DFB 進量產」，其餘五條沿用；watch 新登 7（`ew_0177`–`ew_0183_2026-10-04`，⑦是 `ew_0183`）、收舊 6
  - 2026-10-04｜押這一層的三份敘事換版：SIVE.ST `ib_23cd73accba5a2d9`（rides 換新讀圖；position／our_bet「六家」改「七家」；bottleneck 補「它的 CW DFB 由穩懋代工，穩懋 2026 年 8–9 月簡報仍標合格中」；反證⑤連到新讀圖 #6；SuperNova 插槽舊引用 `sr_268d2fd79db629ff` 被 7.0c 規則擋下、換成現行 `sr_d85d672998445c50`）、COHR `ib_6b25ffb22bdf93fb`、LITE `ib_36704076dae600d4`（只換讀圖與「六家」）；候選狀態、answers、反證條件都不變
- 裁決：（尚無）
  - 2026-10-04｜Jabil 8-K Ex.99.1（Q4 FY26，申報 2026-09-30）｜`ew_0108` 的 Jabil 條件未觸及（全文 Sivers、photonic 都是 0 處）｜—（H7：未觸及不記列）
  - 2026-10-04｜`mops_3105_company_presentation_20260909` p.23｜代工端 CW-DFB 到 2026-09 仍「Ongoing Qualification」——是敘事②（ELS 年底前量產）時程的脈絡，不是裁決；裁決點照舊（Q3 2026-11-26、ELS readiness 2026-12-31）｜—
  - 2026-10-05｜research-drain 段 5：同層四檔台股第一份敘事（都押 `sr_3a4fe5719994dfdc`）——聯亞 `ib_30cb4f95b4afd196`、華星光 `ib_cf97b7317300793a`、
    全新 `ib_a731593be71a5745` 宣告「缺 X」：已定價嗎的主參照（台股歷史股數沒有機械來源；全新另缺 CW 雷射量產，年報只寫 115 年研發計畫），wake `ew_0210`–`ew_0212`
    （10-12）；穩懋 `ib_502f00c21da9f504`「不要」（非邊緣，13 位分析師；照 LITE 前例）。台股歷史股數一格的 PLAN_PROPOSAL：
    `docs/plans/2026-10-05-001-feat-tw-historical-shares-proposal.md`（MOPS t163sb05 已驗證）
  - 2026-10-05｜台股歷史股數上線（使用者 go；merge `36009426`）——已定價①由缺席變有值，三份「缺 X」提早在 wake 前重寫（plan 驗收④）：
    聯亞 `ib_210ad3fcc2fd16bd`、華星光 `ib_a96a1281c2a9991c` 缺的只剩已定價主參照 → **已定價等回落**（自家三年 P/S 第 91／92 百分位，
    寫入時約 75 倍／17 倍、三年中位數約 22.5／6.9 倍；沿用 `ew_0211`／`ew_0212` 10-12 叫醒）；全新 `ib_570813b069dd72ec` 仍「缺」
    （CW 雷射量產與客戶），已定價 yes（第 100 百分位，三年最高）；穩懋 `ib_08670f914111ce1d` 已定價 yes（第 98 百分位）。
    聯亞 2026Q2 的股本含 7 月除權的配股、交叉核對沒過，照第一季股數乘配股比例算（稽核區列出）
  - 2026-10-06｜InP 磊晶層說明（O6 段）回頭改了這一層兩檔：全新 `ib_17223c84a138a416`（舊版「CW 雷射還沒有量產、沒有客戶」被同一份年報推翻，缺的換成 CW 磊晶的量與變體）、
    聯亞 `ib_0884c44e92587161`（已定價等回落不變；加 IDM 收回外包、別家磊晶廠合格、設備落地延後三條反證）
  - 2026-10-06｜積壓：雷達 lead_c07d7676（AK&M「Sivers 出售 Sivers Photonics 給 Nordic Acquisition」，頁面時間 2026-10-06）→ park `contradicts`——內文是 2024-08-06 與 byNordic 簽不具約束力意向書的舊聞再刊；
    Sivers 的 MFN 2026 年沒有出售或分拆公告（最新 09-29 臨時股東會通知：換會計師、員工選擇權、C 股）。不觸及 Sivers thesis 的反證（雷達本來就不叫醒語意 watch）；雷達八週試驗記一則偽陽性
- 2×2：尚未到裁決點
- failure log：（尚無）
  - #1（lead_f1694626 被排回）、#3（[679]／[680] 重複號）

## O3 POET

- 登記：registration §2 O3（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜定向 lead_99ae527d（`directed:phase7-7.1-O3`）→ `ra_db4d61204188fe02647edd6309e5ecea` → pq2 **[684]**：POET×Lumilens 聯合新聞稿（POET 6-K Ex.99.1，accession 0001171843-26-003413）——「POET has granted Lumilens a warrant to purchase up to 22,921,408 common shares」，依 Lumilens 對訂單的累計付款分批 vest；5,000 萬美元訂單「subject to the successful development and ultimate qualification of the modules」。**v2 敘事等 [684] 入圖後再寫**：敘事每格只能引用圖上的證據，而「不要」的理由（付錢方向）原本在圖上沒有一手
  - 2026-10-04 更正（不改登記本身，registration §0 第 4 條）：登記「開題時已知」把認股權證的出處寫成 `ra_353d5e662ef996de0a8f0f649e599819`——那其實是 Schaeffler 人形致動器那一包，只拿 POET 當類比；ARCHITECTURE §6 的「2,292 萬份認股權證」數字本身經上述一手核對無誤（22,921,408）
  - 2026-10-04｜使用者 go：[684] 入圖（intake commit `bf533d2c`）——供貨邊多一份聯合新聞稿 SourceDoc `poet_lumilens_supply_agreement_pr_2026_05_14` 與兩條 claim（cl1 付錢方向、cl2 訂單附開發與合格條件）
  - 2026-10-04｜v2 敘事 `ib_b36ecf9dc00459d9`：候選狀態「不要」，理由寫「不是瓶頸」（供應商拿股權換訂單），不是「非邊緣」——它是邊緣公司（寫入時市值約 13.5 億美元、分析師 1 位，兩條都在門檻內）；answers：已定價＝量不到（20-F／40-F 申報者的既有 fail-closed 規則，不是缺資料）、出現在數字裡＝否（最新一年營收年增 +2494.6% 是從極小基數起跳，訂單還沒進營收）；rides 空（POET 不在任何現行讀圖的供給側；它的雷射站在 CW DFB 層的反向路徑上，引 `sr_00e18cf604cc66b9`）；反證 1 條登記成 `ew_0173_2026-10-04`（客戶端／第三方具名唯一或關鍵供應商，或客戶掏錢；到期 2027-06-30）。materialize 後首屏七句渲染，「已定價」那格印「（尚無）」並標 partial
- 付錢方向（H10）：供應商掏錢（登記時已知）
- 裁決：（尚無）
  - 2026-10-04｜`poet_lumilens_supply_agreement_pr_2026_05_14`（POET×Lumilens 聯合新聞稿，published 2026-05-14）｜付錢方向＝供應商掏錢，一手證實；敘事的結構結論「不是瓶頸」依既有證據成立（登記：既有證據即可結案）｜—（不是錯）
- 2×2：尚未到裁決點
  - 2026-10-04｜列＝結構結論成立（付錢方向，一手）；錨＝敘事日 2026-10-04；欄＝照登記在 7.5 記（光通訊組超額）
  - 2026-10-05｜research-drain 段 5：光寶（2301.TW）在圖上只是 POET 的合作夥伴、沒有層——Abstention 沒有讀圖這一格，改用 POET 6-K s4 補「光寶 develops 可插拔光收發器」，入圖包 pq2 **[708]**（副作用：舊版節點宣告會改回 POET 與光學中介層的兩個欄位，批次揭露）
- failure log：（尚無）

## O4 AAOI

- 登記：registration §2 O4（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜lead_cad23eb9 park（`original_obtained`）：AAOI 424B5（2026-08-21）逐字「aggregate offering price of up to $600,000,000」、前一份 Equity Distribution Agreement 2026-05-14；Engine C `equity_offering_filings` 已收四份 424B5（02-26、03-12、05-14、08-21）——稀釋燈本來就有輸入，不是圖增量（預期的 failure mode「稀釋」照實出現，不是裁決）
  - 2026-10-05｜research-drain 段 5：可插拔收發器層讀圖 `sr_c73e2f2e0523cf76`（undecided：模組層「需求超過產能」只有二手，缺貨的一手在下一層雷射）；第一份 v2 敘事 `ib_27713885500a7607`（不要；已定價 yes＝自家三年 P/S 第 86.8 百分位；現金跑道紅燈、ATM 最高 6 億美元）——2×2 錨點 2026-10-05
  - 2026-10-06｜積壓：lead_a9478647（X：「AAOI 的 6 億美元 ATM 用完了、均價約 105.36」「每月 4.71 億美元收發器營收＋每月 40 萬 ELSFP」）→ park `lead_only_tier_4`——一手只有 2026-08-21 的 ATM 協議；
    9-10、9-15 兩份 8-K 是購地與寧波廠房租約；Q2 法說的「每月 40 萬」是 ELS／ELSFP 2028 年的目標、不是現況。等第三季 10-Q（約 11 月上旬）的 ATM 段
- 裁決：（尚無）
- 2×2：尚未到裁決點
- failure log：（尚無）

## O5 COHR 外部光源第二來源

- 登記：registration §2 O5（開題 2026-10-04；斷言 2026-09-19 已被推翻）
- 研究產出：（尚無）
  - 2026-10-04｜只讀核對：圖上 `co:coherent`→`co:nvidia` 的全部 assertion 與各自 SourceDoc 的 `published_at`／`retrieved_at`、三份推翻文件抽取檔的 git 首次提交日、`thesis/lifecycle.json` 的 `coherent_cpo.mutations`、COHR 敘事 ledger 的 v1 兩版
- 裁決（含「錯」的 kind 核對；登記時預期 `already_available`）：（尚無）
  - 2026-10-04｜`nvidia_sipho_blog_partner_roles`（published 2025-03-27，進庫 2026-09-01）、`nvda_lumentum_partnership_pr_2026_03_02`（published 2026-03-02，抽取檔首次提交 2026-07-21）、`cohr_10_q_20260506`（published 2026-05-06，進庫 2026-07-22）；mutation `tm_22e3402849969072a39e129099112d5e`（2026-09-19 active→review_required，[629]）、`tm_19715e6780f4be9ad63dcd26be6de49c`（2026-09-21 →revised，[636]）｜「唯一」被推翻，**`already_available`，與登記預期相同**，而且分兩段：①2026-07-17 thesis memo 重生成時，三份都已公開、但都還沒進庫——公開卻沒取得；②2026-09-15 v1 敘事 `ib_5c84b4d53fdab440` 的 bottleneck 格寫「目前只有它一家被 NVIDIA 設計進去」時，三份都已在圖上——**庫內已有卻沒讀到**（那一格引用了 coherent→nvidia 邊與 NVIDIA–Coherent 新聞稿，沒引用同在圖上的 Lumentum 新聞稿與 10-Q 的「非獨家」）｜already_available
  - 2026-10-04｜`coherent_q3fy26_cpo_e10`（Coherent 自己的 Q3 FY26 法說；抽取檔在 `.gitignore` 第 96 行、沒有 git 歷史）｜當時 `sole_source=true` 的出處是**發行人自報**——L8 要客戶端或第三方印證；2026-09-19 [627] 改成 false。現行的保護：`loader/validate.py` 的 G5 對受益方自報的 sole_source 發 WARN（不擋），v2 敘事 bottleneck 格的 do_not「供應商自己說的獨家不算，要說出是誰印證的」——本 case 不另開 failure log｜（脈絡，不是另一個裁決）
- 2×2：尚未填（錨＝2026-09-19）
  - 價格照登記在 7.5 記（推翻日 2026-09-19 起對光通訊組超額；脈絡列：thesis memo 2026-07-17 → 2026-09-19）
  - 2026-10-05｜research-drain 段 5：CPO 層讀圖 `sr_e8161208a37aa915`（neither：需求側有 pluggable、NPO、銅可選，台積電的人說瓶頸在雷射、光纖、連接器與測試——在下一層）；矽光子兩節點讀圖 `sr_3ad043cb553dfc94`、`sr_9ee10fb4ef6dd06e`（volume，讀成量：Tower 6-K 客戶預付 2.9 億美元保留 2027 產能）；敘事 AVGO `ib_845f22ec395d69dd`、TSM `ib_e30d810241bf6f8d`、TSEM `ib_af02a0f36157286b`、GFS `ib_a43c94cc33417379`（皆非邊緣的不要）；Soitec 坐上 Photonics-SOI 基板層的入圖包 pq2 **[706]**
  - 2026-10-05｜research-drain 段 5（CPO 鏈續）：CPO 層供給側三檔——FN `ib_10c81951aab63573`、MRVL `ib_54f0fb5339cfe7cf`（皆非邊緣的不要）、HIMX `ib_ccda271575147a0b`（不要：讀不出卡在它——晶圓級光學還在合作開發、客戶沒具名；出現在數字裡 no）；中際旭創 300308.SZ `ib_0ef521433d4bf145`（非邊緣的不要，押矽光子讀圖）；CPO 全堆疊測試層讀圖 `sr_6f781528583b68af`（undecided：需求側只有台積電主管一句轉述、供給側只有 Aehr 自報，晶圓級燒機只是全堆疊測試的一段）＋AEHR `ib_cd56ea272f1cf77f`（缺 X，`ew_0231`：供給側列舉與客戶端具名；已定價 yes＝自家三年 P/S 第 96.8 百分位，X 補上後也是等回落）
  - 2026-10-05｜research-drain 段 5（CPO 鏈的邊緣檔）：外部光源層 `sr_879ba9bc8ad69222`（undecided：NVIDIA 自己的部落格點名 Coherent 供 ELS 模組、Lumentum 剛拿到第一張 ELS 模組單〔2027 下半年交貨〕，但缺的在下一層雷射；Open CPX MSA v1.0 允許模組內建光源，是反向路徑）——POET 的讀圖格因此到終局；FAU 層 `sr_4c83c85cdb490db9`（undecided）＋上詮 `ib_7f2b578b1255a438`（缺 X，`ew_0248`：FAU 客戶與量；EV／營收約 31 倍）；NPO 層 `sr_f004cdb4639c6441`（undecided，沒有需求側）＋AEVA `ib_336f1ed819a1a757`（不要：NPO 只在聯合開發，2027 下半年初次部署）；Enablence `ib_5951751518182665`（不要：會死嗎——現金跑道約 1.3 個月、總負債約 6,147 萬美元，押 ELS 8 通道插槽）。⚠ FAU 讀圖第一次送出時把 Hunterbrook 標成 independent，被拒（媒體轉述不是第三方印證，L11-3），已改
  - 2026-10-05｜使用者 go [706] [708] 入圖之後：Photonics-SOI 基板層（新節點）第一份讀圖 `sr_f0f03b1e543dc73a`（undecided：鎖產能的說法只有
    Soitec 自己、沒拆到這一層；供給側只讀了它一家）；可插拔層重讀 `sr_5bb7fd1ac509a55b`、CPO 層重讀 `sr_d909737c0809a580`（判讀不變；光寶是開發邊、不進供給側）；
    AAOI、AVGO、FN、HIMX、MRVL、TSM 六份敘事改押。Soitec SOI.PA `ib_598ed7484b941868`（缺 X，`ew_0270`：矽光子代工廠談 Photonics-SOI 的一手＋已定價主參照；
    11/18 H1'27 業績叫醒）——寫之前補 Engine C mechanical 三筆：FY2024-25 分部占比 `mo_528c25876a644d9d82a53ae2997d8a8e`（URD 比較欄）、
    Q1'27 營收 `mo_cdf9ed0095729b3551848732f1c1ef51`（一手 PDF：Edge & Cloud AI 6,500 萬歐元、固定匯率年增 46%，Photonics-SOI「sales doubling」）、
    FY27 指引 `mo_336a965dfca0eebd7bceba03f227b0f2`（Photonics-SOI 營收倍增以上）；光寶 2301.TW `ib_f496cf15e39a2f7a`（非邊緣的不要，約 201 億美元；研究判斷沿用 09 月版）
  - 2026-10-06｜**外部光源層說明 v1**（個股頁 S4 第四份；`library/private/research_notes/layer_notes/tech_external_laser_source.md`）——O5 的層級補完：
    客戶端點名的 ELS 供應商仍只有 Coherent（NVIDIA 部落格）；Lumentum 第一張 ELS 模組單 2027 下半年交貨、Cignal 2026 Q1「largest purchase order ever for the ELSFPs」但「no products shipping in volume yet」；
    AAOI 法說：ELSFP「very limited production now」、2028 年約每月 40 萬顆、CPO 雷射「just can't make enough of them to be involved in their current first-generation deployments」；
    「為什麼外接」寫在 OIF ELSFP 2.0 標準裡（可替換、眼睛安全、熱隔離：「Lasers have historically demonstrated significantly lower maximum reliable junction temperatures than silicon die」），Broadcom TH6-Davisson 用「Field-Replaceable ELSFP Laser Modules」。
    讀圖換版 `sr_879ba9bc8ad69222` → **`sr_b17aaffaae5665a0`（仍 undecided）**：模組這一層沒有任何交期或配額原文，量的限制在下一層的 CW 雷射（`sr_3a4fe5719994dfdc`，volume）；E1–E5 五條條件登成 watch（模組本身短缺、第二家被客戶點名、改用 ILM、整合方具名量產、AAOI 放量改口或被具名）。
    因層說明改變的候選狀態 0 筆（AAOI、POET 維持「不要」）；沒有敘事騎在這份讀圖上。下一輪的 RA：AAOI 的 ELS 供貨邊（要具名原文）、Broadcom depends_on 外部光源（更正走廊）
  - 2026-10-06｜**FAU 層說明 v1**（個股頁 S4 第五份，Amendment 第一批收齊；`library/private/research_notes/layer_notes/tech_fiber_attach_unit.md`）。
    **舊讀圖寫「沒有客戶端點名誰是主力」是表示法造成的錯**：NVIDIA 夥伴角色部落格（2025-03-27，已入圖）點名「Browave, Corning, Senko, TFC Communication, and Coherent」做 CPO 光纖組件，但那份抽取建的是同義節點 `tech:cpo_fiber_attach`，FAU 讀圖看不到（failure log #36；合併＋補邊登 pq1 `lead_0c2c98b5b76b7696376923480ca613bf`）。
    NVIDIA 2025-08-26 另一篇：「detachable optical connector that enhances assembly yield and supports fully automated, mass-manufacturing workflows」。上詮不在點名的五家；2025 年營收跳接線 63%、「C 公司」70.16%。
    讀圖換版 `sr_4c83c85cdb490db9` → **`sr_b93ee89a97c130e6`（仍 undecided；F2 交期／配額、F4 Coherent 整合廠量產兩條條件登 watch）**；上詮敘事換版 `ib_9becf6585056d78d`（仍「缺」，X 換成「FAU 用在哪個 CPO 平台、客戶是誰」；反證改寫加入 C 公司占比、加碼條件「任一 CPO 平台具名上詮」）。因層說明改變的候選狀態 0 筆
  - 2026-10-07｜外部光源、FAU 兩份層說明遷入 ledger（個股頁 S4a）：`ln_f7996a796a5e53c8`、`ln_863549fd0f4a7468`——兩份的層主張原本就掛在讀圖與敘事的 watch 上，不重登。
- failure log：（尚無）
  - #27（SOI.PA FY2026 分部占比兩筆都生效，「出現在數字裡」被默默丟——當下修為印衝突；序列仍成不了，合併紀錄留 7.5）

## O6 光通訊磊晶與 MOCVD 產能（二階）

- 登記：registration §2 O6（開題 2026-10-04）
- 研究產出：（尚無）
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
  - 2026-10-05｜research-drain 段 5：光二極體層讀圖 `sr_1de9b7868a235363`（undecided：圖上沒有需求側）；英特磊 `ib_fcc9cb3a94644c63`（不要：磷化銦主力在高頻、國防、量子運算，不在 AI 光互連路徑上；會死嗎兩盞紅燈）
  - 2026-10-05｜IQE：補記 Engine C 兩筆（H1 2026 期中結果 `mo_cff71545649a72f530ff7e0ddc704829`、分部占比第二點 `mo_27e86e110a827d67b59fc763d59a46f7`，出處 2026-09-07 半年報：營收年增 43%、Photonics 年增 45%〔一部分是美國國防資金釋出〕、調整後淨現金 3,020 萬英鎊）；量子點雷射磊晶層 `sr_99a7ed3847bc398e`（undecided：一家供應、一個私人買方）；敘事 `ib_da0aabd997e48b44`（缺 X，`ew_0249`：**InP 磊晶在圖上還不是一層**——IQE 的 InP 磊晶邊接在 Tower、MACOM 公司上，LandMark、VPEC、IntelliEPI 是它的競爭者但沒有層節點；這正是本 case 要建的層）
  - 2026-10-06｜**InP 磊晶片層說明 v1**（plan A3 排第一件；個股頁 schema S4 第一份；`library/private/research_notes/layer_notes/mat_inp_epiwafer.md`，四段規格＋讀後報告＋要文件）。
    研究產出：敘事 2455.TW `ib_17223c84a138a416`（缺；X 由「CW 雷射的量產與客戶」換成「CW 磊晶的量與變體」——舊版前提被同一份年報推翻）、
    4971.TWO `ib_514681199015f82a`（**不要 → 缺**：同一份年報寫 InP PIN 磊晶是 AI 資料庫傳輸用、需求暴量；`ew_0287` 11-16）、
    IQE.L `ib_bbf92ca867cdbff2`（缺；層讀法補上，卡的是設計勝出轉成量而不是產能）、3081.TWO `ib_0884c44e92587161`（已定價等回落；加三條反證）；
    watch 新登 7 條來自層說明主張（`ew_0279`、`ew_0281`、`ew_0283`、`ew_0284`、`ew_0285`、`ew_0288`、`ew_0289`），另 3 條（A6–A8）待層節點入圖後掛層讀圖（failure log #31）；
    RA `ra_fa462ddd1c8de64cfabd60675b3e2c97` → pq2 **[715]**（新節點 `mat:inp_epiwafer`、四家供貨邊、三條 is_component_of、一條 depends_on 基板；五份文件不改任何既有節點）；
    向使用者要文件 pq2 **[716]**（磊晶份額報告，探索型）、**[717]**（全新法說／券商報告）、**[718]**（聯亞券商報告／法說 memo）——lead `lead_b45ed041d5cefd35df04f635ce56e55c`、`lead_dbc229430d64f31160d9c0a70a608816`、`lead_fa374a524e8a4a6d1243f2dbb0ab31ba`。
    一手新增進 library/raw：聯亞 MOPS 重訊七則（長約、兩份基板合約、四次設備預算、AIXTRON 兩筆與艾司摩爾一筆取得設備）、Citi 法說簡報、AIXTRON 三份、MACOM 新聞稿、IQE RNS 四份、Yole 2021 宣傳單節錄、Smit 2014 節錄、中央社轉述。
  - 讀後報告摘要：答到——變體分三類（一次長完／光柵＋覆蓋成長／BH 再成長）、MBE 與 MOCVD 在雷射與光偵測器兩側優勢相反、MOCVD 機台 2026 排隊（AIXTRON 雷射系統出貨由 Q2 延到 Q3）而 2027 落地、IDM 在加自己的磊晶（Lumentum G10-AsP）；
    沒答到——聯亞客戶是誰（代號）、高功率 CW 客戶選 BH 還是脊形、開放市場的新份額；相反——兩份敘事被自家年報推翻（failure log #32）；**因層說明改變候選狀態：1 筆（4971.TWO）**。
  - H5 初判（7.4 寫結論，判準不改）：(i) **表示法為主、證據為輔**（圖上沒有磊晶層；客戶具名缺）；(ii) **暫判「沒有」**（開放市場做得出量的只有聯亞，已是已定價等回落；IQE 缺量、全新缺變體、英特磊缺印證且兩盞紅燈；設備層 AIXTRON 不在名冊、沒讀）。
  - 2026-10-07｜**InP 層說明遷入 ledger `ln_2a0c6b4830dbf1b1`**（個股頁 S4a）；A6–A8 登記 `ew_0310`–`ew_0312`（`layer_note:` 來源鍵、到期 2026-12-31）——#31 解。
    全新、英特磊英文年報兩條出處在 library/raw 對不到（英文版節錄只在 [715] 的包裡），照實不列、reread_reason 寫「[715] 核准後換版補」（failure log #37）。
- failure log：#31（層說明沒有 watch 來源鍵；2026-10-07 S4a 解）、#32（反證在登記前就已成立、永遠不會醒）、#33（`fetchers.mops --include-english` 蓋掉中文版；當下修）；#17 第 4 次（[715] 圖影響行）；#37（層說明的出處 id 對不上 raw 檔名）

## S1 X 帳號 40 則首次點名的 claim 裁決

- 登記：registration §2 S1、§6（框架 40 則＝registration 附錄 B）
- 研究產出（截圖假說 `hy_*` id）：（尚無）
  - 2026-10-04｜`hy_0008_2026-10-04`～`hy_0027_2026-10-04`（20 則結構／財務型；14 verified hit、6 active 帶到期）；逐則見下表，摘要與 H6 判讀在表後；failure log #7
- 逐則（registration §6 第 5 項的欄位；類型與裁決都是封閉字彙）：

| # | symbol | lead id | 主張原文 | 類型 | 一手文件與 `published_at` | 帳號發文日 | 系統接觸日 | 其他管道最早 `first_seen` | 價格（點名 → 一手） | 裁決 | `hy_*`／到期 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | AAOI | `lead_476bd1f0…` | while optical names like $AAOI corrected. | 價格 | — | 2026-06-29 | 2026-07-29 | 2026-07-22 | 點名→2026-10-02：-23.0%／超額 -31.4% | —（價格型不裁決） | 不寫（§6 第 4 條） |
| 2 | MU | `lead_476bd1f0…` | Memory from $SNDK to $MU was the market's main focus this month | 無可否證主張 | — | 2026-06-29 | 2026-07-29 | 2026-08-20 | — | 不適用 | 不寫（§6 第 4 條） |
| 3 | SNDK | `lead_476bd1f0…` | Memory from $SNDK to $MU was the market's main focus this month | 無可否證主張 | — | 2026-06-29 | 2026-07-29 | — | — | 不適用 | 不寫（§6 第 4 條） |
| 4 | AXTI | `lead_b75a2feb…` | Before it was just posting with a few $RDDT friends on ideas like $AXTI, $NBIS, or $ALAB | 無可否證主張 | — | 2026-06-30 | 2026-07-29 | 2026-07-22 | — | 不適用 | 不寫（§6 第 4 條） |
| 5 | CCXI | `lead_1d29da02…` | They're set to be listed on NASDAQ via $CCXI as early as September (per Digitimes). | 財務 | CCXI 8-K Ex.99.1（accession 0001213900-26-071287）（2026-06-24）：「today announced they have entered into a definitive business combination agreement」——一手早於點名 6 天；合併尚未交割（S-4/A 2026-09-30 仍在審），『as early as September』是下限措辭，不算推翻 | 2026-06-30 | 2026-07-29 | 2026-08-11 | 2026-06-24→2026-06-30（一手→點名（一手在前））：+45.5%／超額 +51.1% | 證實 | `hy_0008_2026-10-04`（verified hit） |
| 6 | GFS | `lead_2cb82f4c…` | This is the perfect time to get ideal strategic investors like $GFS on the cap table. | 無可否證主張 | — | 2026-06-30 | 2026-07-29 | 2026-07-22 | — | 不適用 | 不寫（§6 第 4 條） |
| 7 | GOOGL | `lead_401029a4…` | Hard to see a world where US AI hyperscaler capex drops dramatically from $GOOGL to $META. | 無可否證主張 | — | 2026-06-30 | 2026-07-29 | 2026-09-01 | — | 不適用 | 不寫（§6 第 4 條） |
| 8 | JBL | `lead_b75a2feb…` | without mentioning $JBL, Ayar, $GFS or others for CPO scale up or pluggables | 結構 | sivers_jabil_pr_2026_04_15（2026-04-15）：「Sivers Semiconductors Collaborates With Jabil on Energy Efficient 1.6T Pluggable Optical Transceiver Module」——Sivers 新聞稿（供應商端）；Jabil 端的具名在 Sivers Q2 2026 報告（2026-08-27） | 2026-06-30 | 2026-07-29 | 2026-08-13 | 2026-04-15→2026-06-30（一手→點名（一手在前））：+26.4%／超額 +0.4% | 證實 | `hy_0009_2026-10-04`（verified hit） |
| 9 | META | `lead_401029a4…` | Hard to see a world where US AI hyperscaler capex drops dramatically from $GOOGL to $META. | 無可否證主張 | — | 2026-06-30 | 2026-07-29 | 2026-08-11 | — | 不適用 | 不寫（§6 第 4 條） |
| 10 | NBIS | `lead_b5569506…` | Discussion on $NBIS was fun back when there was a lot of debate on Neoclouds | 無可否證主張 | — | 2026-06-30 | 2026-07-29 | — | — | 不適用 | 不寫（§6 第 4 條） |
| 11 | NVDA | `lead_1d29da02…` | Investors include Foxconn, $NVDA, $AMZN, Softbank, and now Serenity. | 結構 | CCXI 8-K Ex.99.1（accession 0001213900-26-071287）（2026-06-24）：「including DCVC, NVIDIA, Amazon, SoftBank Vision Fund 2, Foxconn, Schaeffler, Abico, and Playground Global」——主詞是 Agility 的投資人；一手早於點名 6 天；S-4/A（2026-09-30）再確認 | 2026-06-30 | 2026-07-29 | 2026-08-13 | 2026-06-24→2026-06-30（一手→點名（一手在前））：+0.5%／超額 +6.1% | 證實 | `hy_0010_2026-10-04`（verified hit） |
| 12 | SIVE.ST | `lead_2cb82f4c…` | $SIVE is raising ~$61M (600M SEK) to expand manufacturing capacity for InP lasers and optical amplifiers. | 財務 | Sivers 新聞稿（MFN）（2026-06-30）：「Sivers Semiconductors Announces Intention to Carry Out a Directed Share Issue of Approximately SEK 600 Million」——同日加碼為約 SEK 700M（12,280,701 股 @ SEK 57）；一手與點名同日 | 2026-06-30 | 2026-07-29 | 2026-08-11 | 2026-06-30→2026-06-30（點名→一手）：+0.0%／超額 +0.0% | 證實 | `hy_0011_2026-10-04`（verified hit） |
| 13 | TSLA | `lead_c95925a7…` | So if $TSLA Optimus makes tens of millions of humanoids: Who’s going to make them all look hot? | 無可否證主張 | — | 2026-06-30 | 2026-07-29 | 2026-08-13 | — | 不適用 | 不寫（§6 第 4 條） |
| 14 | XFAB.PA | `lead_b75a2feb…` | I'm grateful to some outlets, like in Belgium for $XFAB coverage | 無可否證主張 | — | 2026-06-30 | 2026-07-29 | — | — | 不適用 | 不寫（§6 第 4 條） |
| 15 | AEVA | `lead_6ac36990…` | Feels like $OUST, $AEVA and other names were pretty flat until the announcement. | 價格 | — | 2026-07-01 | 2026-07-29 | 2026-08-15 | 點名→2026-10-02：-46.9%／超額 -55.9% | —（價格型不裁決） | 不寫（§6 第 4 條） |
| 16 | CRWV | `lead_b72df36b…` | they were forced to immediately sign massive $48B+ contracts with Neoclouds like $CRWV and $NBIS. | 結構 | CoreWeave 8-K（2025-09-25）（2025-09-25）：「Meta has initially committed to pay CoreWeave up to approximately $14.2 billion」——核心（Meta 與 CoreWeave 的大合約）證實、一手早於點名約 9 個月；『$48B+』合計數沒有逐一核對（引文經搜尋摘要，入圖前要逐字重核） | 2026-07-01 | 2026-07-29 | — | 2025-09-25→2026-07-01（一手→點名（一手在前））：-32.4%／超額 -456.3% | 證實 | `hy_0012_2026-10-04`（verified hit） |
| 17 | TSM | `lead_2fb91876…` | Shunsin recebtly confirmed a direct $TSM COUPE partnership. | 結構 | — | 2026-07-01 | 2026-07-29 | 2026-08-30 | — | 未定 | `hy_0013_2026-10-04`／到期 2027-03-31 |
| 18 | XPEV | `lead_56c00023…` | I’m aware of $XPEV and other names like Ubtech. | 無可否證主張 | — | 2026-07-01 | 2026-07-29 | — | — | 不適用 | 不寫（§6 第 4 條） |
| 19 | AEHR | `lead_f7882130…` | $AEHR down -18.3% | 價格 | — | 2026-07-02 | 2026-07-29 | 2026-09-01 | 點名→2026-10-02：+53.2%／超額 +36.2% | —（價格型不裁決） | 不寫（§6 第 4 條） |
| 20 | AMAT | `lead_cc5e07e8…` | $AMAT down -11% | 價格 | — | 2026-07-02 | 2026-07-29 | 2026-07-22 | 點名→2026-10-02：-10.4%／超額 -27.4% | —（價格型不裁決） | 不寫（§6 第 4 條） |
| 21 | AMD | `lead_f3cf03ef…` | And players like $AMD are currently talking with players such as $AAOI (Rosenblatt channel checks). | 結構 | — | 2026-07-02 | 2026-07-29 | — | — | 未定 | `hy_0014_2026-10-04`／到期 2027-03-31 |
| 22 | COHR | `lead_8838f7b8…` | $AXTI signs 3-year wafer deal with $COHR. "Coherent will make a prepayment of $22,288,500 to AXT-Tongmei in exchange for a committed supply capacity." | 結構 | axti_8k_coherent_msda_2026_07_02（2026-07-02）：「for a prepayment of US$22,288,500 (the "Prepayment") from Coherent to AXT」——一手與點名同日（推文附 8-K 連結） | 2026-07-02 | 2026-07-29 | 2026-07-22 | 2026-07-02→2026-07-02（點名→一手）：+0.0%／超額 +0.0% | 證實 | `hy_0015_2026-10-04`（verified hit） |
| 23 | GLW | `lead_f7882130…` | $GLW down -11.4% | 價格 | — | 2026-07-02 | 2026-07-29 | — | 點名→2026-10-02：-16.4%／超額 -33.4% | —（價格型不裁決） | 不寫（§6 第 4 條） |
| 24 | INTC | `lead_9c307b5e…` | If this turns into an $INTC type situation | 無可否證主張 | — | 2026-07-02 | 2026-07-29 | — | — | 不適用 | 不寫（§6 第 4 條） |
| 25 | IREN | `lead_6d1adf0b…` | $IREN founders award themselves $1.14B+ of stock based compensation. Vesting over 4 years timeframe. | 財務 | IREN DEFA14A（accession 0001140361-26-028014）（2026-07-09）：「They vest in four equal annual tranches over the four years from the grant date」——授予 2026-07-01、四年分期證實；推文的 $1.14B 與澳洲媒體的澳幣標題相同（約 US$788M，tier 3），一手只稱 headline dollar value、未逐字給數；可能有更早的 DEF 14A，未查 | 2026-07-02 | 2026-07-29 | — | 2026-07-02→2026-07-09（點名→一手）：+7.5%／超額 +9.6% | 證實 | `hy_0016_2026-10-04`（verified hit） |
| 26 | LITE | `lead_f3cf03ef…` | $LITE is completely sold out for the next 2 years (per $POET AGM) likely starting into 2029. | 結構 | lumentum_q2fy26_cpo（2026-02-03）：「all capacity locked under LTAs through calendar 2027」——核心（產能多年被長約鎖滿）證實、一手早於點名；『2 years／into 2029』比一手的『through calendar 2027』更遠，那一段未證實 | 2026-07-02 | 2026-07-29 | 2026-07-22 | 2026-02-03→2026-07-02（一手→點名（一手在前））：+67.4%／超額 -142.8% | 證實 | `hy_0017_2026-10-04`（verified hit） |
| 27 | MRVL | `lead_cc5e07e8…` | $MRVL down -11% | 價格 | — | 2026-07-02 | 2026-07-29 | 2026-08-21 | 點名→2026-10-02：+11.0%／超額 -6.0% | —（價格型不裁決） | 不寫（§6 第 4 條） |
| 28 | POET | `lead_6d639346…` | $POET entering volume production is revenue. | 結構 | — | 2026-07-02 | 2026-07-29 | 2026-08-15 | — | 未定 | `hy_0018_2026-10-04`／到期 2027-03-31 |
| 29 | MSFT | `lead_e7d01288…` | $MSFT was underwater DCs. | 無可否證主張 | — | 2026-07-04 | 2026-07-29 | — | — | 不適用 | 不寫（§6 第 4 條） |
| 30 | FN | `lead_3a46a020…` | downstream IP acqusition -> into contract manufacturing like $FN, and others | 無可否證主張 | — | 2026-07-06 | 2026-07-29 | — | — | 不適用 | 不寫（§6 第 4 條） |
| 31 | IQE.L | `lead_8088f665…` | Nomura’s report cites $AXTI and $IQE as the leading players. | 結構 | — | 2026-07-06 | 2026-07-29 | 2026-08-11 | — | 未定 | `hy_0019_2026-10-04`／到期 2027-03-31 |
| 32 | AAPL | `lead_586d4451…` | most profitable company in the world beating $NVDA and $AAPL | 財務 | Samsung 2Q26 earnings guidance（2026-07-07）＋AAPL 10-Q（0000320193-26-000013）＋NVDA 10-Q（0001045810-26-000052）（2026-07-07）：「Samsung 2Q26 營業利益 ₩89.4T（約 US$58.4B）＞ NVDA 1Q FY27 營業利益 $53.536B ＞ AAPL 2Q FY26 營業利益 $35.885B」——比的是點名當時各自最新一季；Samsung 是初估（guidance）；匯率換算出自 CNBC 等報導 | 2026-07-07 | 2026-07-29 | — | 2026-07-07→2026-07-07（點名→一手）：+0.0%／超額 +0.0% | 證實 | `hy_0020_2026-10-04`（verified hit） |
| 33 | ORCL | `lead_d95d26c1…` | recently inked major computing deals with $CRVW, Google, $ORCL, and others. | 結構 | — | 2026-07-07 | 2026-07-29 | — | — | 未定 | `hy_0021_2026-10-04`／到期 2027-03-31 |
| 34 | AVGO | `lead_0c4d787d…` | $META 'Iris' will enter mass production in September via $AVGO and TSMC | 結構 | — | 2026-07-13 | 2026-07-29 | 2026-08-13 | — | 未定 | `hy_0022_2026-10-04`／到期 2026-10-30 |
| 35 | MTSI | `lead_62327c9d…` | CEO says “TBD” with commercial timing and it’s in reliability work right now. | 結構 | MACOM Q2 FY2026 法說逐字稿（2026-05-07）（2026-05-07）：「I would put it in the category of a TBD」——另一句「What our fab is doing today is dialing in a process of record. That work is not complete.」；引文經 WebFetch 摘要擷取，入圖前要逐字重核 | 2026-07-13 | 2026-07-29 | 2026-08-15 | 2026-05-07→2026-07-13（一手→點名（一手在前））：-14.6%／超額 +5.7% | 證實 | `hy_0023_2026-10-04`（verified hit） |
| 36 | TSEM | `lead_b1e793c5…` | $TSM, $GFS, and $TSEM in silicon photonics foundry capacity | 結構 | tsem_20_f_20260430（2026-04-30）：「mainly to expand our silicon photonics (SiPho) and silicon germanium (SiGe) capacity and capabilities」——一手早於點名 | 2026-07-13 | 2026-07-29 | 2026-07-22 | 2026-04-30→2026-07-13（一手→點名（一手在前））：+3.9%／超額 +13.7% | 證實 | `hy_0024_2026-10-04`（verified hit） |
| 37 | 000660.KS | `lead_cb2644d6…` | This Is Not the Time to Sell Samsung Electronics and $SKHY | 價格 | — | 2026-07-17 | 2026-07-29 | — | 點名→2026-10-02：-0.0%／超額 -41.0% | —（價格型不裁決） | 不寫（§6 第 4 條） |
| 38 | SOI.PA | `lead_f8b10528…` | Higher silicon photonics penetration means more TAM for cw lasers like $SIVE (cw) / SOI wafer demand for $SOI. | 結構 | soitec_fy26_results_2026_05_27（2026-05-27）：「Strong momentum in Photonics-SOI, a powerful growth driver addressing surging AI data center demand, with revenue above $100m in FY26」——一手早於點名 | 2026-07-17 | 2026-07-29 | — | 2026-05-27→2026-07-17（一手→點名（一手在前））：-43.4%／超額 -9.1% | 證實 | `hy_0025_2026-10-04`（verified hit） |
| 39 | SHA0.DE | `lead_26bd4214…` | planetary roller screws, 6D force sensors, and dexterous hands resist domestic substitution ... eg. $SHA0.DE for planetary | 結構 | Schaeffler 新聞稿（2025-03-31）（2025-03-31）：「linear actuators, such as ball and planetary roller screw assemblies, can be used in various humanoid joints」——只證實『Schaeffler 供人形用的行星滾柱螺桿』；『難以國產替代』是中國通路調查，未證實；引文經 WebFetch 擷取 | 2026-09-01 | 2026-09-01 | — | 2025-03-31→2026-09-01（一手→點名（一手在前））：+109.6%／超額 -604.8% | 證實 | `hy_0026_2026-10-04`（verified hit） |
| 40 | LYC.AX | `lead_fc1f6fdd…` | Japan has locked up 75% of Lynas’s medium/heavy rare-earth output | 結構 | lynas_asx_jare_enhanced_2026_03_10（2026-03-10）：「75% of all HRE oxides produced by Lynas will be made available to Japanese industry」——一手早於點名 | 2026-09-04 | 2026-09-04 | — | 2026-03-10→2026-09-04（一手→點名（一手在前））：-13.5%／超額 -110.2% | 證實 | `hy_0027_2026-10-04`（verified hit） |

- 2026-10-04 摘要（強模型、互動 session）：40 則全查。類型：結構 16、財務 4、價格 7、無可否證 13（只計數、記「不適用」、不寫進假說層）。結構＋財務 20 則寫進截圖假說層 `hy_0008`～`hy_0027`：證實 14（verify hit）、推翻 0、未定 6（帶到期，到期是重問不是丟）。
- **H6 判讀（§1 的線）**：已裁決 14（≥ 10）；證實率 14／14；證實者提前天數（一手 `published_at` − 帳號發文日，正＝帳號較早）＝[-519, -279, -178, -149, -76, -74, -67, -51, -6, -6, 0, 0, 0, 7]，**中位數 -59 天 ≤ 0 → 削弱（殺死條件成立）**。白話：這個帳號講的結構／財務事實幾乎都對，但一手多半早已公開（14 則裡 10 則一手在前、3 則同日、只有 IREN 晚 7 天——而 IREN 可能有更早的 DEF 14A 沒查）；它的價值是把已公開的一手串起來，不是比一手早知道。
- 對系統其他管道（其他管道最早 `first_seen` − 帳號發文日，有紀錄的 8 則）：[9, 20, 20, 33, 42, 42, 44, 44]——帳號全部較早，但系統的 EDGAR／MFN 管道 2026-07-22 前後才開始收、X 的回補日是 2026-07-29，這段「提前」多半是系統起跑日的偏差，不是帳號的資訊優勢（登記的 failure mode 之一）。
- 價格型 7 則（點名 → 2026-10-02；超額＝對光通訊組 `tc_35b0d5cd521656ea` 排除本檔）：AAOI -23.0%（超額 -31.4%）；AEVA -46.9%（超額 -55.9%）；AEHR +53.2%（超額 +36.2%）；AMAT -10.4%（超額 -27.4%）；GLW -16.4%（超額 -33.4%）；MRVL +11.0%（超額 -6.0%）；000660.KS -0.0%（超額 -41.0%）。只記路徑、不進 H6 主判讀。
- 偏差照登記：框架只含名冊有 id 的代號（偏向我們已在追的名字）；一則貼文多檔（30 個 lead 出 40 則）。價格欄由 `alpha.theme_cohort.series_return`／`cohort_return` 機械算出（Engine C `price_history` 的 `close_adjusted`，休市日取前一日）。

- 摘要（7.1 收尾寫；H6 的量法）：（尚無）
- failure log：（尚無）

## P1 345／765 kV 超高壓變壓器

- 登記：registration §2 P1（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜開題稽核 pq2 **[685]**（使用者 Q2 選題，受理即 resolve，收據 `authority:plan_approval`）
  - 2026-10-04｜**decompose 收據**（system-decompose；不入圖、不提高 tier）——系統：資料中心變電站用 345 kV 級大型電力變壓器（LPT）；選題理由：plan §0.1 Q2「電力（超高壓變壓器與它的上游：電工鋼、套管、分接開關、測試產能）」；一手來源：DOE《Electric Grid Supply Chain Review: Large Power Transformers and High Voltage Direct Current Systems》（2022-02，政府報告，tier 1；對供應商而言是第三方）。拆出 11 層：GOES、鐵芯疊片、CTC 銅導線、絕緣紙板、絕緣油、套管、有載分接開關、儲油櫃／膠囊、整機製造、出廠測試（試驗台）、運輸（最後 5–10 英里）。DOE 點名的兩大瓶頸是 GOES 產能與 LPT 測試產能（p.20–21）；「Imports account for 82% of the consumption of LPTs in 2019」。三題：幾家能做——GOES 全球 13 家、達 DOE 規格只有日韓德；分接開關美國 3 家＋德國 1 家（未具名）；套管、絕緣材料美國各少數幾家；其餘未知。換掉要多久（合格）——全部未知（DOE 給的是交貨週期，不是合格週期）。客戶資本承諾——全部未知。⚠ 這份是 2022 年的快照（AI 資料中心需求之前），2026 年現況要另找一手。對照圖：圖上 0 個變壓器／電工鋼／分接開關／套管／變電站節點，名冊 0 家——**收斂：拆出 11 層｜✅ 0｜🟡 0｜🔴 11**
  - 2026-10-04｜研究題目（pq1，`decompose:lpt-345kv-2026-10-04`，triaged_go）：lead_7b63986b（LPT 整機：進口來源、交期、客戶端資本承諾）；P2 的五題見下
  - 2026-10-04｜第一份層文件入圖包 pq2 **[687]**（定向 lead_c1a91083 → `ra_c6cf9c678063f86f9015d868a8423ec7`）：DOE 2022 LPT 供應鏈深度評估（政府報告、對公司是第三方；`config/publishers.json` 隨包加 DOE）——新節點 `tech:large_power_transformer` 與五個元件層、`constrained_by` GOES／測試產能兩條、`co:cleveland_cliffs`（CLF）→ GOES、`co:hyosung_heavy_industries`（298040.KS）→ LPT；名冊兩筆隨包 staged。**[688] 取代 [687]**（第一版沒聲明 focus_company_id、被 sync 標 BLOCKER；補 co:hyosung_heavy_industries 重新 prepare 成 `ra_ed8e3518b20d6d20ec577fea7900b748`；[687] 請 drop，failure log #3 第 2 次）。⚠ 2022 年快照、不接 AI 資料中心需求錨（入圖後走圖會報「走不到錨」，那是對的提醒）；failure log #8
  - 2026-10-04｜需求端接線入圖包 pq2 **[689]**（定向 lead_775a39b4 → `ra_eb76b41fb28879e307d0eea82fefcee5`）：IREN FY2026 10-K（AI 資料中心營運商＝買方端）——`co:iren depends_on` LPT 與新節點 `tech:hv_circuit_breaker`（交期 16–72／15–113 週），`tech:ai_compute_buildout enables tech:large_power_transformer`（「capacity-constrained supply chains for AI infrastructure」）；補上 [688] 走不到 AI 需求錨的缺口
  - 2026-10-04｜使用者 go：[688] 入圖（intake commit `832a244e`）、[689] 入圖（`9a682aab`）；[687] drop（舊版缺 focus_company_id）
  - 2026-10-04｜**電力鏈第一份讀圖** `sr_a884792198990379`（`tech:large_power_transformer`，層）：**undecided**——需求側讀得出繞不過（IREN 10-K：高壓變壓器／開關設備單點故障、交期 16–72 週且在增加，買方端但只有一家），供給側讀不出形狀（圖上只有 HICO 一家且是能力不是出貨；同一份 DOE 說 2019 年 82% 靠進口——**已知至少 1 家，不是薄層**）；DOE 點名的兩個瓶頸（GOES 產能、測試台）在下一層，形狀指向量（B）但是 2022 年快照、不宣告。缺：供給側列舉（lead_7b63986b）、任一條供貨邊的替代難度、2026 年現況。反證 2 條登記：`ew_0174_2026-10-04`（IREN 交期鬆動）、`ew_0175_2026-10-04`（GOES／測試瓶頸解除），另客戶重讀 `ew_0176_2026-10-04`（IREN 出新文件 → 本層該重讀）。驗收①（光通訊以外的鏈有現行讀圖＋≥1 條登記反證）電力這一條成立
  - 2026-10-04｜pq1 drain 第二條 lead_7b63986b（LPT 整機）→ `ra_81137972d1ac8783b356db14c45a6a0c` → pq2 **[692]**：①DOE 更正走廊（舊內容逐字保留）＋p.13–15——第三方政府報告依字母序具名 8 家美國 LPT 廠（Delta Star、Hitachi Energy、HICO、Hyundai Power Transformers USA、Niagara、Pennsylvania Transformer Technology、SPX→GE Prolec、Virginia Transformer）與逐家產能、2019 年國產 137／進口 617 台、2020 年進口來源（墨 45%、加 15%、中 7%、韓 5%）、GOES 兩大抱怨與 GOES 進口 85% 來自南韓；②**HD 現代電氣 DART 2026-05-07：765kV 超高壓變壓器與電抗器 US$117.6M，MISO／SPP 區的大型公用事業下單（未具名），「계약금ㆍ선급금 유무 유」——客戶付訂金／預付款**（超高壓設備的業界常態，記成弱的資本承諾；沒有 AI 字樣）；③HD 現代電氣 2026-03-07 新聞稿：Montgomery 第二廠約 2 億美元、產能 +50%、765kV 級製造與**試驗**能力、2027-04 完工。名冊七筆隨包（HD 現代電氣 267260.KS、Hitachi 6501.T、Prolec GE null、四家私人 null）；LPT 節點補韓文別名。可投資性：8 家裡上市的都是大型集團，其餘私人。入圖後 LPT 讀圖會 stale（供給側 1 → 8），要重讀
  - 2026-10-05｜使用者 go：[692] 入圖（intake commit `3e87c3b9`，名冊 `eeaa5bfa`）。**LPT 層重讀 `sr_c848a9726dc30560`（undecided → volume，取代 sr_a884792198990379）**：
    上一份寫的「缺哪一格」補上兩格——①供給側列舉（DOE 8 家＋2019 年 82% 進口）、③2026 年現況（IREN 交期 16–72 週；HD 現代 765kV 合約有客戶預付、阿拉巴馬 +50% 擴產與 765 kV 測試能力 2027-04）；
    ②替代難度仍空白，所以是「讀成量」不是「證實是量」，沒有任何一家讀得成 A。765 kV 那一段在美國本土仍薄（2022 年名單裡寫到 765 kV 能力的只有 HICO）。
    坐在這層的上市公司曉星重工（298040.KS，約 25.9 兆韓元、19 位分析師）、HD 現代電氣（267260.KS，約 24.4 兆韓元、22 位）都是大型股——這層讀成量，不代表有可開的邊緣公司。
    反證 3 條在盯（沿用：需求側鬆動、上游瓶頸解除；新增：量的窗口關閉——預付消失、交期縮短或 765 kV 新產能到位）
  - 2026-10-05｜[699] 入圖後 LPT 讀圖 stale（下一層多一條 constrained_by 分接開關）→ 第二次重讀 `sr_711f7130aba5d5b8`：判讀不變（volume），
    下一層補一句「分接開關也可能是瓶頸」與 CTC、絕緣兩層的供給側（皆私人）
- 主題等權組（電力；必須早於本鏈第一份敘事）：`tc_1a8d8a8911b327d5`「AI 資料中心電力」（曉星重工 298040.KS、HD 現代電氣 267260.KS；pq2 [713]，2026-10-06 寫入）
  - 2026-10-04｜還不能定：照光通訊組的選員準則（主業就是這一層、名冊解析得到、有價格歷史；需求端與綜合集團不入組），名冊上的電力鏈上市公司只有曉星重工（298040.KS）合格——Cleveland-Cliffs（CLF）主業是汽車用鋼、電工鋼只是業務之一（判斷，未量化占比，同住友電工被排除的理由），IREN 是需求端。合格 1 家、不到 2 家下限；等 lead_7b63986b 等供給側研究把 LPT／開關設備的上市供應商補進名冊再定（本鏈還沒有敘事，前瞻要求仍守得住）
  - 2026-10-05｜[692] 入圖後合格的是曉星重工、HD 現代電氣兩檔（主業是電力設備、名冊解析得到、Engine C 已有價格），湊到下限；**仍延後**：
    現行程式只支援一組基準，第二組一寫進 ledger，追蹤表與計分表的組超額就整格缺席（failure log #16）。本鏈還沒有要寫的敘事，前瞻要求仍守得住
  - 2026-10-05｜多主題等權組開發（使用者 go）在動手前停下：非組員列的基準要使用者三選一（plan 2026-10-05-002 SCOPE_ESCALATION）。
    本鏈四檔先只做研究判斷，**敘事仍不寫**（守 plan 7.1 ④）：HD 現代電氣 267260.KS、曉星重工 298040.KS、日立 6501.T（皆非邊緣；
    LPT 層量的一手：現代電氣的 DART 合約有訂金／預付）、Cleveland-Cliffs CLF（**邊緣**：約 65 億美元、6 位）。
    脈絡（只記、不歸因）：現代電氣、曉星都在 2026-05-07 見頂——同日現代電氣公告那筆預付合約——之後各跌約 52%、39%（Engine C 日線）
  - 2026-10-06｜多主題等權組 S1 GO（每一列只跟自己所屬的組比）後鑄 [713]、使用者 go、`complete-theme-cohort 713` 寫入 `tc_1a8d8a8911b327d5`；
    排除日立（綜合集團）、CLF（主業汽車用鋼）、IREN（需求端）。本鏈第一份敘事的前置條件（plan 7.1 ④）解除。
    ⚠ 兩檔都是韓股，Engine C 沒有機械營收序列 →「已定價①」算不出，②（組中位數）因此是 upstream_unavailable；③（相對組漲幅）有值。
- 裁決：（尚無）
- 2×2：尚未到裁決點
- failure log：（尚無）
  - #9（11 條 decompose 題目缺分類被 drain withheld；回填腳本吃不下 `triage: None`——當下修）
  - #11（[689] IREN 的 depends_on 印 self_reported_costly——買方自述被當成供應商自報；與 C1 [694] 同形）
  - #16（第二個主題等權組會讓追蹤表與計分表的組基準整格缺席——本鏈的組因此延後）

## P2 變壓器上游：電工鋼、套管、分接開關、測試產能（二階）

- 登記：registration §2 P2（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜decompose 收據見 P1（同一次拆解）；本段的研究題目（pq1，triaged_go）：lead_21b7830d（GOES）、lead_188e1fa1（測試產能）、lead_e0948fc0（有載分接開關；德國那一家要具名）、lead_857be4a6（高壓套管）、lead_bf2fb4a7（CTC 銅導線）
  - 2026-10-04｜補一題 lead_de46bc48（變壓器絕緣材料；買方端一手：Forgent S-1「we rely on a single supplier for certain specialized insulation material used in our transformer products」）；[687] 把 GOES、CTC、分接開關、套管、絕緣材料、測試產能六個上游層建成節點（供給側只有 GOES 一家美國廠，其餘零供應商＝走圖的洞）
  - 2026-10-04｜pq1 drain 第一條 lead_21b7830d（GOES）→ `ra_a4864a6a92163da08b4f6eb529081fab` → pq2 **[691]**：JFE 2025-08-04 新聞稿（JSW JFE 印度合資：前 thyssenkrupp 印度廠、5 萬 → 25 萬噸／年 2028–2030，另一廠 10 萬噸 2027）＋Cliffs 2026 Q2 10-Q（產品清單逐字含 GOES；「Transformers are in short supply … exacerbated by the anticipated widespread adoption of AI」）；名冊三筆隨包（合資 null、co:jfe_holdings 5411.T、co:jsw_steel JSWSTEEL.NS）。查無一手：題材掃描說的 Cliffs Weirton 變壓器廠（10-Q 只有 Weirton tinplate 停產）、現代製鐵 2026-04 北美 GOES 協議（只見市場研究稿、韓文新聞 0 則）。**對 H5 (ii) 的初步證據：GOES 供給側是鋼鐵巨頭（Cliffs、JFE、JSW）與私人合資，沒有看到非共識、可投資的標的**（7.4 寫結論）；美國 LPT 用的 DOE 規格級 GOES（日韓德）的具名廠商與其美國客戶仍未入圖
  - 2026-10-05｜使用者 go：[691] 入圖（intake commit `8d02fc72`，名冊 `eeaa5bfa`）。
  - 2026-10-05｜四條 DOE 元件題合成一次 DOE 更正（[692] 之後第二次，舊內容逐字保留）→ `ra_75938cdde252742d00f98b3fcb5b8ee6` → pq2 **[699]**：
    ①CTC（lead_bf2fb4a7）：stakeholder 說北美 3 家、美國只有 2 家；Sam Dong「manufactures CTC at its Rogersville, Tennessee facility」→ 供貨邊；
    Essex Furukawa（DOE：「it remains unclear if CTC can be produced at any of the domestic facilities」）與 REA（Fort Wayne 廠有能力，引 2008 年文獻；
    單字「REA」在電網文件常指 Rural Electrification Administration，放名冊會誤中）只進 claim。②絕緣（lead_de46bc48）：「a potential supply concern due to a lack of
    domestic manufacturing」，Weidmann、Cindus → 兩條供貨邊；DuPont（Nomex）是 stakeholder 轉述，只進 claim；**Forgent 10-K 的單一供應商不接 LPT 絕緣層**——
    它的產品是配電級（dry type、liquid filled）與中壓設備，全文沒有 power transformer，那家供應商也沒具名（L12）。③分接開關（lead_e0948fc0）：
    「could also be a bottle neck」→ LPT constrained_by 分接開關；三家國內與一家德國廠都沒具名，「是誰」仍開著。④套管（lead_857be4a6）：只有引自 2014 年的
    「up to five months」→ 帶日期 claim；lead park（partial，自動建 watch 等 2026 年一手）。**撤回**：該 lead 標題的「非中國瓷件只剩美日波蘭」在 DOE 全文找不到
    （porcelain 只在儀用變壓器與開關段，Poland 只在 GOES 廠清單）——10-04 decompose 時寫錯。名冊三筆隨包 staged（Sam Dong、Weidmann、Cindus，皆私人、null）。
    ⚠ 決策區塊的「圖影響」印 +19 節點、20 邊、12 claims，實際新增 3 節點、4 邊、4 claims（failure log #17）
  - 2026-10-05｜使用者 go：[699] 入圖（intake commit `5c689235`，名冊 `62e32880`）；CTC、絕緣兩層的讀圖照 plan 留給 7.4 的二階 case（P2 結論 7.4 寫）
  - 2026-10-05｜research-drain 段 5（CLF 的讀圖格）：GOES 層第一份讀圖 `sr_467982cb902b776c`（undecided）——DOE（2022）把美國 GOES 產能列為
    LPT 兩大瓶頸之一、國內只供兩成，但 LPT 廠的高規格 GOES 靠日、韓、德進口，Cliffs 的國內 GOES 有量與品質的抱怨（獨家≠換不掉）；
    2025–26 年沒有任何買方談 GOES 交期或預付。缺：①近兩年的買方一手、②全球 GOES 供給側列舉、③Cliffs 的 GOES 產能與品質升級。
    ⚠ 寫入時 DOE「唯一 GOES 廠」那句被驗證器判為轉述句、不得標第三方印證（L11-3），已改。坐在這一層的上市公司只有 CLF——邊緣，但它是
    綜合鋼廠、GOES 占比答不出來（研究判斷已存，敘事等電力組）
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
- failure log：（尚無）
  - #9（同 P1）
  - #10（[691] 合資股東的新聞稿被分類成外部印證；與 C1 [690] 同形）
  - #17（[699] 的圖影響行把整份更正文件當成增量）

## P3 800VDC 擱置五則回看

- 登記：registration §2 P3（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜（給 7.4 的指向，不是裁決）NVIDIA 部落格「NVIDIA, Partners Drive Next-Gen Efficient Gigawatt AI Factories in Buildup for Vera Rubin」（blogs.nvidia.com，2025 OCP）逐字列 800 VDC 夥伴——silicon：ADI、AOS、EPC、Infineon、Innoscience、MPS、Navitas、onsemi、Power Integrations、Renesas、Richtek、ROHM、STMicroelectronics、Texas Instruments；power system components：BizLink、Delta、Flex、GE Vernova、Lead Wealth、LITEON、Megmeet；data center power systems：ABB、Eaton、GE Vernova、Heron Power、Hitachi Energy、Mitsubishi Electric、Schneider Electric、Siemens、Vertiv。是客戶端（平台方）的生態名單——對五則的 park 理由（例：「ecosystem membership is not a supply contract」）正好是那個理由描述的東西，回看時要分清「名單」與「供貨」
  - 2026-10-05｜（給 7.4 的指向，不是裁決）題材掃描 lead_b050a3ee（台達 2026-09-29 PR Newswire：800 VDC In-Row Power「for the fast deployment and scalability of AI data centers based on
    NVIDIA Vera Rubin architecture」、keynote 談「Delta Electronics' collaboration with NVIDIA and the roadmap for 800VDC power architecture」）→ park（`original_obtained`，觸發欄寫「無」）：
    供應商自報的產品發表與合作字樣，**不補 lead_fa672a29 的缺口**（supplier relationship not proven）；台達 2025 年報同樣只寫已發展 19 吋 90kW DC/DC 機架式電源
    （800VDC 降 50／48VDC）與列間 1MW 800VDC 電源系統，沒有具名客戶。PR 的散熱段轉給 C1（[697]）
- 逐則（park 理由今天站不站得住；H2 的「證實」定義）：（尚無）
- failure log：（尚無）

## C1 液冷台股供應商

- 登記：registration §2 C1（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜開題稽核 pq2 **[686]**（使用者 Q2 選題，受理即 resolve，收據 `authority:plan_approval`）
  - 2026-10-04｜**decompose 收據**——系統：GB300 NVL72 機櫃的直接液冷迴路；選題理由：plan §0.1 Q2「散熱（小規模，台股液冷）」；一手來源：Lenovo Press LP2357（2026-08-30，整機廠規格書：「The liquid cooling solution consists of a CDU, rear manifold, quick disconnects, and cold plates for the CPUs, GPUs, ConnectX-8 network adapters, and all NVSwitch components」——WebFetch 摘要轉出，入圖前要逐字重核）、OCP 產品目錄（UQD 開放規格，至少 7 家上架）。拆出 6 層：冷板、機櫃後置 manifold（304L／316L）、快接頭（UQD／UQDB）、CDU（液對液熱交換＋泵）、冷卻液（去離子水／PG25，大宗品）、廠務水側。三題：幾家能做——快接頭 OCP 目錄至少 7 家（SITELIN、CEJN、Stäubli、JPC、Parker、BEEHE、Danfoss Hansen），其餘未知；換掉要多久、客戶資本承諾——全部未知。對照圖：只有泛稱的 `tech:thermal_solutions`（Coherent 一條邊，指光模組熱管理），冷板／manifold／快接頭／CDU 都沒有；名冊 0 家台股散熱公司——**收斂：拆出 6 層（冷卻液不出題）｜✅ 0｜🟡 0｜🔴 5**。⚠ 先入為主的風險（登記的 failure mode）：快接頭「開放規格＋多家上架」支持 08-29 的「競爭層」結論，題目刻意寫成找反例（NVIDIA 指定的盲插件有幾家通過）
  - 2026-10-04｜研究題目（pq1，`decompose:gb300-nvl72-dlc-2026-10-04`，triaged_go）：lead_5b8cc7e2（冷板）、lead_1345d45b（manifold）、lead_6698f145（快接頭）、lead_f96bfb99（CDU）
  - 2026-10-04｜第一份層文件入圖包 pq2 **[690]**（定向 lead_ba882ac7 → `ra_c6bd011413367fec896f89429c605404`）：Ecolab 8-K（收購 CoolIT 協議，2026-03-20）＋交割新聞稿（2026-07-02）——新節點 `tech:coolant_distribution_unit`、`tech:liquid_cooling_cold_plate`，CoolIT（非上市）供這兩層、`tech:ai_compute_buildout enables` 兩層、Ecolab acquired CoolIT、CoolIT partnership_with NVIDIA／AMD；名冊 co:ecolab（ECL）、co:coolit_systems（null）隨包 staged。⚠ 兩層供給側只畫了一家，不得讀成薄層；Eaton 申報對 Boyd 沒有液冷字樣，不建邊。題材掃描 lead_f7c61cbb 已 park（由 [690] 承接）
  - 2026-10-04｜使用者 go：[690] 入圖（intake commit `32d81f4a`）
  - 2026-10-04｜pq1 drain 冷板題 lead_5b8cc7e2 → `ra_cfa47fbc9d74f2a53ba98c1c86b01d1d` → pq2 **[693]**：**NVIDIA 自己的 COMPUTEX 2024 新聞稿（客戶端）**點名散熱夥伴並刊出高管引言——AVC「providing efficient cooling for its AI hardware」→ AVC supplies_to NVIDIA；Danfoss「high-performance quick disconnect … couplings」→ 快接頭層（新節點）；Dover 的 CPC「connector technology … liquid-cooled NVIDIA GPUs」→ Dover supplies_to NVIDIA；健策 2026-05-29 自述 GPU／CPU cold plates、liquid distribution manifolds → 冷板層、manifold（新節點）。名冊四筆隨包（奇鋐 3017.TW、健策 3653.TW、Danfoss null、Dover DOV）。**邊緣判定（yfinance 2026-10-04）：冷板層被點名的都不是邊緣**——健策約新台幣 1.0 兆／11 位、奇鋐約 1.35 兆／17 位、台達約 4.9 兆、Dover 約 255 億美元；第二線富世達（快接頭，約 1,580 億／9 位）、高力（CDU，約 1,400 億／7 位）是邊緣，留給快接頭、CDU 兩題。Digitimes 說 NVIDIA 在 GTC 2026 點名四家 Vera Rubin 冷板供應商（AVC、Cooler Master、健策、台達）——NVIDIA 原文找不到，只當媒體轉述
  - 2026-10-04｜pq1 drain manifold 題 lead_1345d45b → `ra_c0a5eac2241398fb6b4418a57db8e88b` → pq2 **[694]**：NVIDIA 技術部落格 2025-05-16（MGX）——`co:nvidia depends_on` 冷板、manifold、快接頭三層（需求側第一次有真正的客戶），**並逐字說「Diverse sourcing options within the MGX ecosystem … avoiding vendor lock-in … a broad array of certified components」**：客戶自己刻意多源——**C1 登記的 failure mode（快接頭／冷板是競爭層的先入為主）第一次有客戶端原文支持，不是只靠開放規格目錄**；它同時意味這三層的倍率不靠護城河，只能靠量（讀圖時照實寫）
  - 2026-10-04｜pq1 drain 快接頭題 lead_6698f145 → `ra_ee1d0eef3fd7e0d3f03c02aa1ef632cd` → pq2 **[695]**：**富世達（6805.TW，邊緣：約新台幣 1,580 億、9 位）**2025 年報（MOPS，2026-05-07）自述 UQD「通過水冷供應認證並切入 GB200/GB300」、「冷水板+UQD」切入北美四大 CSP、「已通過 Rubin 測試並挑戰國際大廠壟斷地位」；伺服器產品組件營收 5.31% → 36.29%（含滑軌，快接頭占比未揭露）；集團母公司奇鋐（e2）。題目要找的反例（NVIDIA 指定盲插件只有少數幾家通過）**沒找到客戶端一手**——供應商說既有國際大廠寡占、NVIDIA 說刻意多源，形狀是少數認證廠＋新進者；折疊手機轉軸仍占 56%，快接頭不是主業（進主題組前要先判斷）
  - 2026-10-04｜pq1 drain CDU 題 lead_f96bfb99 → `ra_7601b10717ea4855869caeb026e380c6` → pq2 **[696]**：**高力（8996.TW，邊緣：約新台幣 1,400 億、7 位）**2025 年報（股東會後修訂本，MOPS 2026-08-06）自述液冷「分岐管和冷卻液分配裝置，成功攻入 GB200 供應鏈名單」、子公司高力熱能科技「積極投入高效能 Manifold、CDU、Radiator…並透過取得主要客戶之產品認證」（認證仍在進行，所以 qualification 不填）；分歧管改真空爐硬焊「能突破產能瓶頸」；合併營業比重板式熱交換器 26.28%、熱能產品 73.72%（液冷與燃料電池零件沒拆開——燃料電池那塊年報說受惠美國電力市場，是另一條 AI 電力題）。至此 C1 的四個 decompose 題都到終局（[693]–[696] 待核准），散熱兩層讀圖等這幾包入圖後再寫
  - 2026-10-04｜讀圖**刻意延後**：`tech:coolant_distribution_unit`、`tech:liquid_cooling_cold_plate` 兩層各只有 1 條需求接線與 1 條供貨（CoolIT，非上市），現在寫只會是空的 undecided——為了驗收①的計數補格子正是 L19 的形狀。等 lead_f96bfb99（CDU）／lead_5b8cc7e2（冷板）的供給側研究有實料再讀；驗收①的散熱這一條目前未成立
  - 2026-10-05｜冷板、CDU 兩層的供給側補大型股：定向 lead_a03a034a → `ra_0f423ab9e5cf9d9fef9c6c28335682c5` → pq2 **[697]**：**台達（2308.TW，大型股，約新台幣 4.9 兆，不是候選）**
    2025 年報（MOPS 2026-05-08）自述液冷「由板端冷板模組延伸至系統端冷卻架構…搭配…冷卻液分配控制器(CDU)」「相關液冷散熱產品亦持續擴大於資料中心場域之應用與出貨」、
    液冷系統業務是「114 年台達最重要的成長動能之一」→ 冷板、CDU 各一條自報供貨邊；名冊 `co:delta_electronics` 隨包 staged（**不放單字別名 Delta**：名冊已有 co:delta_star，#4 的形狀）。
    為什麼補大型股：讀圖的兩半引用與走圖的「薄層沒人讀」「供給側未填」都數圖上的供給側——只有 CoolIT 和邊緣廠時兩層會被算薄（高力包 [696] 寫的「讀圖時不得讀成薄層」是要人記得的段落；入圖才會自己出現）。
    ⚠ [698] 是同一包重跑 prepare 的重複號（digest 相同），請 drop（failure log #3 第 3 次）。指路：題材掃描 lead_b050a3ee（台達 2026-09-29 PR：VR NVL72 專用冷板、HVDC 3.6MW in-row CDU——同一家自報的產品展示，不另入）；CDU 層的 Vertiv 等仍未入，讀圖寫「已知至少」
  - 2026-10-05｜使用者 go：[693]–[697] 入圖（intake commit `b6a9ecb8`、`70445eea`、`f997a37d`、`33b04f15`、`f32cf77d`；名冊 `eeaa5bfa`），[698] drop。
    **散熱鏈第一份讀圖 `sr_c7d89e1c0d9dae02`（`tech:liquid_cooling_quick_disconnect`，層，undecided）**：A 被擋掉——UQD 是開放規格（Universal quick disconnect），
    NVIDIA MGX 技術文逐字說「Diverse sourcing options … avoiding vendor lock-in」；B 沒有證據——沒有任何客戶端或第三方說快接頭缺貨、配額、交期拉長或預付，
    富世達的成長（伺服器產品占營收 5.3% → 36.3%，含滑軌）可能是分食國際大廠份額（它自己說在「挑戰國際大廠壟斷地位」），那是換供應商、不是大家都缺。
    缺：快接頭交期／配額／預付、GB300／Rubin 合格的 UQD 名單（客戶端或第三方）。反證 2 條在盯（單一來源出現；富世達伺服器產品連兩季下滑或失去認證）。
    **冷板、CDU、manifold 不讀**：圖上各 2–3 家、公開資料還有 Vertiv、Schneider 等大廠，加上 NVIDIA 刻意多源——不是薄層（plan ⑤ 只讀薄層）
  - 主題等權組：還沒定——組員要能在名冊解析（INV-1），台股散熱公司目前 0 家在名冊；組員等選源找出各層坐了誰再定（仍早於本鏈第一份敘事）
  - 2026-10-05｜research-drain 段 5（每檔閉環）：冷板 `sr_c867b738814b90ad`、CDU `sr_0475081d107b32d1`、manifold `sr_765d267e7a75ea1d` 三層讀圖（皆 undecided）——是閉環要的（台達、健策、高力的讀圖格要有座位上的讀圖），**不改上面「不是薄層」的結論**：三份都寫明沒有任何缺貨、配額或換不掉的原文（plan ⑤ 只讀薄層——這三份是為了閉環而讀，7.5 一併檢討閉環與 ⑤ 的張力）。研究判斷 2308.TW、3653.TW、8996.TW、6805.TW；敘事 台達 `ib_bd2d8179e84470ae`、健策 `ib_17d06f172878bde1`（皆非邊緣的不要；健策已漲近九倍、市值約 1.0 兆元）、高力 `ib_2bcbfdeaac1af639`（缺 X，`ew_0245`）、富世達 `ib_5cf338161818520a`（缺 X，`ew_0246`）
  - 2026-10-05｜⚠ **違反 plan 7.1 ④：本鏈第一份 v2 敘事（上面四份，2026-10-05 04:28 UTC）寫在主題等權組落地之前**——閉環佇列照 NEXT_PICK_RULE 排到散熱四檔，執行者（本 session）沒有先讀本段的前置條件。錨日因此是 2026-10-05。緩解：組員候選（奇鋐、健策、高力、富世達）在敘事之前已寫進本段（commit `afdb4698`，2026-10-04 23:16 UTC，早約 5 小時）——組成不是事後挑的；正式落地仍待 #16。7.5 量本鏈的組超額時以那份候選名單當組成，並標明是本段事後補記。電力鏈（P1）的敘事一律等主題組落地後才寫（failure log #26）
  - 2026-10-05｜閉環：奇鋐（3017.TW）讀圖格 upstream_unavailable（圖上只有「供貨給 NVIDIA」的公司對公司邊）→ 入圖包 pq2 **[710]**（`ra_ebe8b7c611c92719dc4f3def70fa1584`，lead_d96c6c89）：英文版年報逐字——2025 是 AVC 的「Inaugural Year of Liquid Cooling」、長期投入 Cold Plates 與 CDU、擴產聚焦 critical cold plate components、擴充 manifold systems 產能 → 冷板、CDU、manifold 三條自報供貨邊；副作用：不改任何既有節點。⚠ 中文版通篇寫「本公司」，prepare 的層列舉具名檢查拒收（未寫入、未鑄號），改用同日上傳的英文版（FE4，doc_id 照 3081／4979 慣例加 `_fe4`）。媒體（Digitimes 2026-03-18，付費）報導 NVIDIA 在 GTC 點名 Vera Rubin 四家冷板供應商（奇鋐、Cooler Master、健策、台達）——NVIDIA 網域找不到名單，沒有逐字，不進包
  - 2026-10-05｜Dover（DOV）的層邊**不做**：10-K 只寫「thermal connectors used in liquid cooling of data centers」（Pumps & Process Solutions 的有機成長來源），沒有逐字 quick disconnect；10-04 快接頭讀圖對 NVIDIA 新聞稿那句同樣具體程度的話已判「不接到層」（L6），同一把尺。CPC 自己的「Everis UQD／UQDB」頁面與 2025-07 新聞稿是那個逐字，但官網與轉載站都擋腳本（403），這輪拿不到。DOV 留在未到終局
  - 2026-10-05｜使用者 go [710] 入圖之後：冷板 `sr_7d2a979f43e3fc92`、CDU `sr_7f07d59f15b6e8dc`、manifold `sr_baee167c3dfb3b71` 三層重讀
    （供給側各多奇鋐一家，判讀都不變：undecided——自報、沒有買方說缺，奇鋐擴冷板與歧管產能是供給在追）；台達、健策、高力三份敘事改押；
    奇鋐 3017.TW 研究判斷＋敘事 `ib_0267a789158134ca`（非邊緣的不要：約 425 億美元、16 位）。主題等權組仍延後：多主題等權組的開發使用者已 go，落地後才鑄號
  - 2026-10-05｜台股歷史股數上線後，散熱五檔的已定價改答 yes（自家三年 P/S：台達第 88、奇鋐 98、健策 99、富世達 98、高力 97 百分位）——
    台達 `ib_9c0f71b96255f81b`、奇鋐 `ib_db24d66f75352f9a`、健策 `ib_867664f2d398ab84`（不要，照舊）；富世達 `ib_68c9b09fc97449b5`、
    高力 `ib_ba882a638b9dfca9`（仍「缺」：快接頭層與 CDU／分歧管的量的證據），X 由兩格縮成一格。
    ⚠ 多主題等權組 S1 停在 SCOPE_ESCALATION（非組員列的基準要使用者三選一，plan 2026-10-05-002），散熱組仍延後
- 主題等權組（散熱；必須早於本鏈第一份敘事）：`tc_2efac5d9b16b46cf`「AI 資料中心散熱」（奇鋐、健策、高力、富世達；pq2 [714]，2026-10-06 寫入——晚於本鏈四份敘事，failure log #26）
  - 2026-10-05｜候選：奇鋐（3017.TW）、健策（3653.TW）、高力（8996.TW）、富世達（6805.TW；伺服器產品占營收 36%，年報說「已成為公司主要獲利引擎」——判斷入組）；
    台達（主業電源）、Ecolab、Dover（多角化）、CoolIT、Danfoss（非上市）、雙鴻、Vertiv（不在名冊）排除。四檔在 Engine C 都有價格。**延後**：同 P1，failure log #16
  - 2026-10-06｜S1 GO 後鑄 [714]、使用者 go、`complete-theme-cohort 714` 寫入 `tc_2efac5d9b16b46cf`（成員與排除照 10-05 候選，未改）。
    驗收（個股頁 artifact，重算後）：四檔「已定價②」由缺席變有值（奇鋐、富世達 13.76 倍；健策、高力 10.49 倍——組內其他成員的股價營收比中位數）、
    「已定價③」30／90 日相對組漲幅有值；追蹤表裡四檔改跟散熱組比（今天錨點 10-05、還沒有新收盤，明天起有數字），台達照舊「不是任何組的組員」。
  - 2026-10-06｜**快接頭層說明 v1**（個股頁 schema S4 第二份、散熱鏈第一份；`library/private/research_notes/layer_notes/tech_liquid_cooling_quick_disconnect.md`，四段規格＋讀後報告＋要文件）。
    讀法：**需求繞不過，但這一層不卡**——OCP UQD 規格把介面寫死、明文「universal interchangeability」，v2 由 NVIDIA 與 CPC 執筆寫「any willing supplier」；
    OCP 目錄上架 UQD／UQDB 的廠商 2023 年 2 → 2024 年 5 → 2025 年 10 → 2026-10-06 共 18（富世達、CPC、中航光電不在目錄）；富世達 2025 年「重大資本支出：無」、月產 300 萬顆——資本輕。
    **量的那一格答成反面**：同時賣快接頭（CPC）與熱交換器（SWEP）的 Dover，2025 年 Q2／Q3 10-Q 與 10-K 都把「thermal connectors used in liquid cooling of data centers」列為成長來源，2026 年 Q1／Q2 10-Q 不再列；
    Q2 法說「Our lead times overall are in balance … But in areas like heat exchangers, people are trying out there to secure supply」（熱交換器訂單「including longer lead-time orders」、產能 12 個月翻倍）。
    2024–25 年確實緊過（經濟日報 2024-07-22 國際大廠零件漏水、雲端業者要台廠進來；富世達 2025-03 法說「供貨吃緊」）。富世達 2025 年營收 25.43% 賣給「奇宏深圳」（關係企業，奇鋐的深圳子公司）——快接頭主要跟著奇鋐的冷板模組出貨，是換供應商、不是大家都缺。
    讀圖換版 `sr_c7d89e1c0d9dae02`（undecided）→ **`sr_d46b2882a58b8dfc`（neither）**，反證 5 條 `ew_0291`–`ew_0295`（Q1 一兩家合格／Q2 缺貨一手／Q4 以年計擴產／Q6 無閥接頭吃掉用量／Q3 在位者退出），舊的 2 條隨換版收掉；
    **因層說明改變的候選狀態 1 筆：富世達 6805.TW「缺 → 不要」**（`ib_188e19ab994e5234`；重開條件 `ew_0296`、`ew_0297`，Q2 連結 `ew_0292`）；奇鋐維持「不要」（非邊緣）。
    入圖包 pq2 **[719]**（`ra_2fc72a02a98b6f249fc1e391faeba09b`）：Dover／CPC 新聞稿（2026-07-22，逐字「a leading provider of quick disconnect couplings … for thermal management」——**10-05 那筆「Dover 的層邊不做、DOV 留在未到終局」由此接上**）、Stäubli 新聞稿（自述在 NVIDIA RVL）、Parker 與英維克的 OCP 上架頁 → 快接頭層四條自報供貨邊；名冊 co:parker_hannifin、co:staubli、co:envicool 隨包 staged；不改任何既有節點。
    向你要文件 pq2 **[720]**：Rubin 托盤快接頭的合格名單或份額（NVIDIA RVL 不公開）。
    **沒問到卻讀到：散熱鏈的量訊號在 CDU 裡的硬焊板式熱交換器**（Dover／SWEP），高力的本業正是它——下一份層說明直接做（高力敘事停在「缺：CDU 與分歧管兩層的量的證據」）
  - 2026-10-06｜**板式熱交換器層說明 v1**（個股頁 S4 第三份、散熱鏈第二份；`library/private/research_notes/layer_notes/tech_brazed_plate_heat_exchanger.md`；提議節點 `tech:brazed_plate_heat_exchanger`——CDU 層讀圖的「下一層」原本 0 條）。
    讀法：**這一層在排隊，而且是量（B）不是護城河。**Google 的 Deschutes CDU 規格（客戶端）：熱交換器「First source vendor: Alfa Laval ● Model: CB210-276AH」、每台 2 MW CDU 三顆，同時寫零件「sourced from multiple vendors that are widely known in the industry」；
    Dover 第一季法說：大型與特大型熱交換器交期「extended materially」、客戶「would need to get in line」、「very few competitors」；第二季：12 個月內產能翻倍、客戶「securing capacity well ahead of need」；Alfa Laval 第二季報：資料中心需求轉成訂單「mainly for delivery in 2027」。
    OCP 目錄：照 Deschutes 做 2 MW CDU 的 8 家，板式熱交換器上架只有 Alfa Laval——**同一台機器，CDU 層厚、熱交換器層薄**。沒有任何 CDU 買方一手說熱交換器缺（Vertiv：壅塞多半在自家供應鏈）。
    **量的受益者是 Alfa Laval、Dover 這類大型股；邊緣公司在這一層看不到**——高力的板式熱交換器是本業，但沒有一份文件說它進了資料中心 CDU。
    **改正：高力敘事 10-05 版寫的「熱能產品 62.3% → 73.7%」是同一年的個體與合併兩欄**（failure log #35）；真正跨年的是主要客戶表：「SMC」1.50 億（3.75%）→ 26.50 億（40.26%）、Bloom Energy 31.27%。美超微 2026-03-20 8-K：三名相關個人因出口管制被起訴、公司不是被告（媒體寫成公司被起訴）。
    高力敘事換版 `ib_e94c9d2cc0c11d46`（仍「缺」，X 換成「板式熱交換器有沒有進資料中心 CDU」＋「美超微以外客戶量產」；反證 `ew_0298`、加碼條件 `ew_0299`、`ew_0300`；舊 `ew_0278` 收掉）——**因層說明改變的候選狀態 0 筆**（改寫不是改判）。
    建層入圖包 pq2 **[721]**（`ra_d1e2d64cda6c73c3d2ed568ddeab803c`：新節點＋Alfa Laval（客戶端點名，designed_in）、Danfoss 供貨邊＋「是 CDU 元件」＋`co:google depends_on` CDU；名冊 co:alfa_laval 隨包 staged）；向你要文件 pq2 **[722]**（高力的客戶與產品拆分）。H1–H3 三條層主張等 [721] 入圖後的層讀圖（failure log #31 第 2 次）
  - 2026-10-07｜快接頭、板式熱交換器兩份層說明遷入 ledger（個股頁 S4a）：`ln_9adebe4be9952856`、`ln_1c39f088ea8cec08`；
    板式熱交換器 H1–H3 不等層讀圖、直接以 `layer_note:` 來源鍵登記 `ew_0313`–`ew_0315`（到期 2026-12-31；`co:alfa_laval` 是 staged 名冊、不掛實體，[721] 核准後換版補）——#31 第 2 次那一筆一併解。
- 裁決：（尚無）
- 2×2：尚未到裁決點
- failure log：（尚無）
  - #9（同 P1）
  - #10（[690] CoolIT 的兩條供貨邊印 externally_corroborated——文件是收購方 Ecolab 發的）
  - #11（[694] NVIDIA 自己的 depends_on 被預告成「供應商自報」——買方自述與供應商自誇共用一個值）
  - #3（[698] 是 [697] 重跑 prepare 的重複號，內容逐位相同）
  - #16（同 P1：第二個主題等權組會讓組基準整格缺席——本鏈的組因此延後）
  - #17（[719] 的圖影響印 +8 節點，實際新節點 3 個——第 5 次）
  - #34（富世達「缺 → 不要」換版後，舊「缺」的 wake_brief 等待 `ew_0246` 沒人收，10-12 會叫醒一份剛寫好的「不要」敘事）
  - #11（[721] Google 自己的 CDU 規格 → `co:google depends_on` CDU 被預告成「供應商自報」——第 3 次）、#17（[721] 印 +10 節點、實際新 2 個——第 6 次）、#31（板式熱交換器層主張等層讀圖——第 2 次）
  - #35（高力敘事把年報「個體／合併」兩欄讀成兩個年度；本 session 對話也差點重犯）

## B1 AI 生醫的上游實驗量

- 登記：registration「更正與追加」2026-10-06 B1（開題 2026-10-06）
- 研究產出：（尚無）
  - 2026-10-06｜開題稽核 pq2 **[723]**（使用者 2026-10-06 主動選題，受理即 resolve，收據 `authority:user_directive`）
  - 2026-10-06｜種子 lead `lead_7cb87fe0d59de4b7cf175f5a47be602a`（qinbafrank 轉述 Freda Duan，`user_shared:qinbafrank`，tier 4，triaged_go `interactive:directed`）
  - 2026-10-07｜**decompose 收據**——系統 A：Anthropic 2026-08-18 那一輪 AI binder「設計→濕實驗驗證」campaign（1,320 個設計交 Adaptyv 全收、Twist 收 1,260，HT-SPR 量結合，354 個有結合——Adaptyv 單家 336）；系統 B：一個單抗 program 的 IND-enabling 臨床前包（FDA 估典型 program 用 144 隻 NHP）；旁支 A′：擾動圖譜（不在原文那條 binder 迴路上）。選題理由＝使用者原話（[723]）。一手來源 160 多份（Anthropic 技術報告與資料集、Adaptyv 方法頁、Twist 10-K／10-Q／法說、GenScript 中報、CRL 10-K 與法說、昭衍／美迪西／百普賽斯／義翹半年報、FDA 文件）；拆出 22 層，反方查證補 4 層可開題的（表達細胞株與培養基、抗體庫與 display、齧齒類與比格犬、CMC／毒理批）＋7 層併入既有題目或只記錄；圖上全是未知層（🔴，圖上生醫節點 0）。研究地圖（含 160 多個出處與反方查證全文）存 `library/private/research_notes/decompose/aibio_aidd_2026-10-07.md`（private）
  - 2026-10-07｜研究題目（pq1，`decompose:aibio-aidd-2026-10-07`，triaged_go interactive:directed；**一層一則**，同層的問題綁在一起）20 則：A2 基因合成 lead_e4d82d83、A2d 合成原料 lead_85e28284、A3 蛋白表達 lead_6e52b6fc、A3b 無細胞試劑 lead_f7129a60、A4 標靶抗原 lead_bf44dbb5、A4b 捕捉表面 lead_cb4b5bf7、A5 HT-SPR lead_7abdbb7b、A6 驗證資料工廠 lead_6a976956、A8 自動化 lead_286783b8、A9 可開發性 lead_76d64853、A10 迴路內 NGS lead_49ab494d、B1 GLP 毒理 lead_e2dc4890、B2 實驗猴 lead_872257be、B3 跨境 lead_341c3850、B5 NAMs（反證開關）lead_e354e088、表達細胞株與培養基 lead_8c8f5ea9、抗體庫 lead_347614bf、齧齒類與比格犬 lead_0a06ea04、CMC／毒理批 lead_26c8d843、需求端 D1–D7 lead_0d1081c8。不開題：A1 設計（開源、非瓶頸）、A7 數據擬合（無上市者）、A′ 定序與單細胞（大型股、不在迴路上；只當證據）
  - 2026-10-07｜**開題原文逐條對照**（原文＝SNS t4）：TWST 三位數訂單成長（供應商指引，FY25 基數約 $25M）、GenScript AIDD 1H26 翻倍、4,000+ designs/day（官網自述、口徑未定義）、1,320／354 都有一手；**「通路調查 8,000／日、往 16,000」沒有一手**（Adaptyv 自述量級差兩個數量級以上）；猴價上行在中國有買方原文（美迪西）、價位只有二手（中檢院 19 萬是招標預算、成交 17.8 萬）、美國不成立（CRL：「lower NHP sourcing costs」）；**「CRO 產能緊」在美國被否認**（CRL：「we don't see a bottleneck there」），中國只有匿名轉述；**鏈上的「定序」不在 binder 迴路上**（讀出是 HT-SPR）
  - 2026-10-07｜反方查證抓到的讀法錯（研究地圖內已標，未進任何 ledger）：§5 把半年報裡就有的營收拆分寫成「沒有數字」（L11-5）——百普賽斯重組蛋白 80.37%、技術服務 2.82%，所以它的曝險在抗原試劑（A4）、不在 AI 表達服務；昭衍的 4,384 萬是預付款總額（它自己持猴，不是乾淨的買方訊號）；Twist 增資兩個數字是基本額對含超額配售、不矛盾

## X1 已定價回放（R1）

- 登記：registration §2 X1、§7.2
- 報告：（尚無；`replay-r1-priced.md`）
  - 2026-10-05｜[`replay-r1-priced.md`](replay-r1-priced.md)：31 列 × 4 個時點＝124 格，有值 **10** 格（PIT 違規 0：每格用到的最晚申報日都 ≤ 時點）；**H9 判讀線：history 子群「不足」、只在組裡的 9 檔「不足」**（每組湊不到 n ≥ 4；錨點那格 history 高 5、低 1）。缺席分型：非 SEC 40、三年窗不滿 34（Engine C 價格 2023-08-31 起，時點早於約 07-31 量不到）、台股 20、20-F 16、EV/S 缺 4。**之後曾達 2 倍的 21 格（18 檔）在那個時點全部「未量」**——「已定價有沒有把贏家說服走」現有資料回答不了（不足 ≠ 否定）
- H9（X1 的部分）：不足（n）
- failure log：（尚無）
  - #12（Engine C 價格歷史深度：三年窗不滿 34 格）

## X2 parked 回查（R2）

- 登記：registration §2 X2、§7.3（樣本 36 則＝registration 附錄 C）
- 報告：（尚無；`replay-r2-parked.md`）
  - 2026-10-05｜[`replay-r2-parked.md`](replay-r2-parked.md)：36 則（附錄 C 程式重算逐則相同）**證實 1**、未證實 11、無法判 2（registry 沒寫 park 理由）、**不適用 22**（park 理由本來就不是缺證據：例行 Form 4、行事曆、重複、非上市標的）；
    依層母體加權的證實比例 1.93%（全樣本為分母）／12.91%（排除不適用與無法判）。唯一證實：`lead_6e6000e1`（缺 Agility 歷史財報 → CCXI S-4 2026-09-04 含經審計財報），
    CCXI park→證實 −4.9%、證實→量測 −10.5%（機器人鏈組未定義，只印絕對報酬；n＝1 不進判讀線）。EDGAR 層 10 則裡 9 則不適用——這個母體量到的主要是「例行申報被正確 park」
  - 撞到的事：①2 則 parked 沒有 park 理由也沒有觸發條件（`lead_e590eca7`、`lead_27625bd1`）；②同一份 S-4 讓四則 park 等的東西出現，四則今天仍是 parked、沒有接回
    （S-4/A 本身已走 EDGAR feed 入圖成 [683]）——`original_obtained` 是終局值、park 時不自動建 watch，母體 353 則裡有 watch 在等的只有 9 則
  - 2026-10-05｜T2 輪詢補跑（研究段第 7 段 `pollable_watches` 自 09-21 沒人跑；15 條全查、各一次搜尋）：**2 條等的一手早已出現**——
    `ew_0020`：NVDA 8-K 2026-08-17 Item 1.01 已揭露對 OpenAI 租約的 residual value guaranties（10-Q 寫上限 $105B），`lead_2f5aebfb` 等了 49 天才接回（#15 第 2 次）；
    `ew_0032`：FCC 26-50（Third Report and Order，07-22 通過、Federal Register 09-11 刊出、10-13 生效）已出，但 FCC 自己寫主要光模組廠都不在 Covered List，
    不滿足 `lead_7f66b743` 的原主張（「禁中國光模組」）。另登記 `lead_8e5a2815`（Silex Microsystems 據二手代工 Google OCS 的 MEMS 微鏡，一手路徑是上市公開說明書；待 triage），
    兩則 lead 補了一手路徑（`lead_85a70a23`：「Elazr」應為聯鈞 3450.TW；`lead_9258d25d`：鴻騰董事長的短缺說法只有二手）；其餘 10 條未命中
  - 2026-10-05｜Silex 後續：`lead_8e5a2815`（PhotonCap 二手指路）被 daily 分流 no-go——判斷本身沒錯（二手、沒有原文），錯在我登記的是指路而不是一手；
    改登記定向 `lead_3dae07ce` 追到一手：Silex Microsystems（SILEX.ST，2026-05-07 掛牌，約 190 億克朗、4 位分析師）SFSA 核准的公開說明書 p.23
    「Silex manufactures MEMS for AI applications, such as optical circuit switches in data centres」、p.73 技術含「micro-mirror arrays」→ pq2 **[700]**
    （`tech:mems_mirror_array` 第一家供應商，自報·filing）；客戶集中度（最大客戶 2025 全年 25%）與 SMEI 持股 45.2% 進帶日期 claim。
    Q2 法說的「only MEMS foundry producing OCS」「10 OCS customers … one in high volume production」只有模型轉述（原文 403），不入圖。客戶未具名
    → 使用者 go，[700] 入圖（intake commit `d9c54b7c`，名冊 `62e32880`）。**MEMS 鏡陣列層讀圖 `sr_87952c233a4e591b`（undecided）**：「一家已知代工＋集中客戶」
    的形狀只有自報；客戶端原文（Google Apollo 論文）說晶片「inherently inexpensive due to fabrication within a silicon wafer process」、Google 換過供應方——
    可替代性證據指向不高；缺：客戶端或第三方點名 OCS 的 MEMS 代工、能量產的代工有幾家。Silex 的敘事等 Engine C 有它的價格與財報（名冊今天才進）再寫
  - 2026-10-05｜雷達第一次無人值守運行（daily 05:30）：搜尋 15 次、新增 1 則（Sivers 人事的二手轉寫，標題「Shepherd Glasgow Fab Into Mass Production」不是原文）
    ——追到 Sivers 09-24 一手公告後 park：Photonics CTO（CST Global 共同創辦人）退休、Amkor 出身的工程副總 10-31 到任；留給 10-29 thesis 複查
- H2（X2 的部分）：**不足**（證實 1 < 4）；與 P3（7.4）合併判
- failure log：（尚無）
  - #15（park 缺的那一樣出現了、文件也進來了，卻沒有接回那則 park；一份 S-4、四則）

## X3 漏網稽核（R3）

- 登記：registration §2 X3、§5
- 報告：第一次（窗口 2026 Q3）（尚無；`replay-r3-missed-q3.md`）；第二次（7.5）（尚無）
  - 2026-10-05｜第一窗 [`replay-r3-missed-q3.md`](replay-r3-missed-q3.md)：58 檔全有價格、光通訊組 Q3 等權 +1.0%、前四分之一 15 檔。**照官方比對法「系統沒有接觸」6 檔：健策（+101%）、雙鴻（+51%）、奇鋐（+32%）、南亞科（+24%）、上詮、英特磊**——後兩檔是比對法的問題（上詮 08-24 X 帳號與 08-25 decompose 的 lead 沒有公司身分；英特磊 09-17 已經年報進圖、09-30 入組，但定義不含「進圖」「入組」）；**窗口內接觸卻沒研究 8 檔**（全新 09-17 park、LandMark 讀圖 09-17〔字串比對另見 08-26 中央社〕、晶豪科 08-27 X 帳號反覆點名後 park、華星光 09-24 park、LITE、AXTI、IQE、韓美）；窗口後才接觸 1 檔（CLF，10-04 電力鏈開題）。「接觸早於窗口起點」第一窗無法觀測（lead registry 07-22 開機，晚於窗口起點 07-01）
  - 7.5 failure log 候選（不是條目）：健策、雙鴻、奇鋐（散熱：Q2 選題前沒有任何管道）、南亞科（記憶體：「刻意不做」的代價）
  - 2026-10-05｜research-drain 段 5（每檔閉環）碰到一組**母體外的贏家**：IC 載板兩檔——AT&S（ATS.VI）由 2025-02 低點約 €11 到 2026-06-22 高點 €239（約 22 倍）、三星電機（009150.KS）由 2025-04 低點約 ₩11 萬到 2026-06-19 高點 ₩227 萬（約 21 倍）（Engine C 日線）。§5.2 的 43 檔觀察名單有「先進封裝／測試」類、沒有 IC 載板類，第一窗看不到它們。載板層 2026-10-04 才入圖（[681]；lead 來自 2026-09-30 一則 X 推文），已在漲勢尾端；而買方的缺貨原文 2026-05-28 就公開了（Marvell Q1 10-Q：大尺寸載板供給吃緊＋8.7 億美元訂金鎖產能）。依 §5.3 第 2 點，看得到價格之後才追加的成分不進已過的窗口。研究產出：讀圖 `sr_229707b4d4cd4f82`（volume）；敘事 ATS.VI `ib_6f4af1dbbf5e1b56`（缺 X：已定價的主參照量不到，補上後最可能是等回落）、009150.KS `ib_498e2bc68d1a77ad`（非邊緣的不要）
  - 2026-10-05｜使用者 go [711]：R3 母體追加 IC 載板類 6 檔（ATS.VI、009150.KS、4062.T、3037.TW、3189.TW、8046.TW），從第二窗起；
    第一窗不重算（registration、cohort-changes 已記，commit `8a059096`）
  - 7.5 failure log 候選：R3 的母體只看得到事先想到的類別——這一組真正漏掉的贏家，結構上在分母之外（「我找不到」與「它不存在」是兩個 claim，L11-5）；另外 05-28 的買方原文到 10-04 才進圖，中間沒有任何管道把它送進研究
- failure log：（尚無）
  - #13（lead 實體不隨名冊重算：LandMark、上詮照官方比對法變成「沒有 lead」）

## X4 history lane 輸家驗屍（R4）

- 登記：registration §2 X4、§7.4
- 報告：（尚無；`replay-r4-losers.md`）
  - 2026-10-05｜[`replay-r4-losers.md`](replay-r4-losers.md)：**AEVA、MP、Lynas、Nidec、JL Mag 五檔全部「證據不足以判」**——入圖後到 10-02 沒有任何一手回頭碰到入圖時的結構主張（AEVA、MP 在 EDGAR 入圖後 0 份非內部人申報；Lynas 入圖後唯一的一手是 10-01 換股收購 Meteoric——資本配置；JL Mag 只有股東會與股息公告；Nidec 入圖時唯一一條 assertion 沒有發表日、投影是空的）。不構成 H1／H3 的反例。描述（不判讀）：三檔稀土同期一起跌；MP 客戶資本承諾最齊全仍 −20%（窗口太短，不進 H10）；JL Mag 入圖時的證據全是 2022 年報
  - 2026-10-05｜research-drain 段 5（每檔閉環）把驗屍的五檔接成讀圖＋敘事（不是裁決，裁決點不變）：
    - 諧波減速器層 `sr_2dd5e99d68a4d0b7`（undecided；Nidec、HDS、綠的同層）；6324.T 敘事 `ib_6fd7f9b9e5dbe451`（不要：讀不出卡住誰）
    - 稀土磁材層 `sr_b38b36acdfdfeddc`（volume，**只對中國以外**：買方的包銷、保底價、預付鎖的是非中國供給）；分離重稀土層 `sr_a0bb6b6fe6cb3050`
      （moat，中國以外、時間領先：Lynas 是唯一在商業量產的；MP 的分離廠還在蓋）。反證 watch `ew_0198`–`ew_0202`
    - MP `ib_f7742f86bcb0bb00`（已定價等回落，`ew_0203`；自家三年 P/S 第 58.7 百分位但結構證據全是 2025-07 公開頭條）；
      LYC.AX `ib_3980aa5b40612922`（缺 X，`ew_0204`：重稀土實際出貨量＋澳洲申報人量不到財報）；6680.HK `ib_7456aa56a3e881d8`
      （不要：量只對中國以外成立，金力在中國側）。MP、LYC.AX 非邊緣（覆蓋 15、13 位）；6680.HK 邊緣但快照市值只算 H 股
  - 2026-10-05｜research-drain 段 5（機器人鏈續）：RV 減速器層 `sr_697ae401ae6935a7`（undecided：Nabtesco 自估工業機器人關節六成，人形用不用 RV 沒有一手）、人形機器人致動器層 `sr_ae3ca36af2a1cc15`（undecided：供給側只讀到 Schaeffler，唯一客戶具名是互惠交易）；研究判斷檔 6268.T、SHA0.DE；敘事 Nabtesco `ib_50de584aea2b6198`、雙環 `ib_0a869635854d456e`、Schaeffler `ib_989c75cb4e73914a`（皆不要：讀不出卡在它／量太小）；現代摩比斯坐上致動器層的入圖包 pq2 **[707]**
  - 2026-10-05｜research-drain 段 5（機器人鏈續）：綠的諧波 688017.SS `ib_12123549c9ea634a`（不要：讀不出卡在它——諧波層至少三家、它是追趕的中國廠，人形客戶只有二手；押諧波層 `sr_2dd5e99d68a4d0b7`）
  - 2026-10-05｜使用者 go [705] [707] 入圖、[704] drop（被 [705] 取代）之後：
    - 稀土磁材層重讀 `sr_4ef39c5afa160b75`（仍 volume、只對中國以外）：USA Rare Earth 第一次以自己的供貨邊坐上這一層——10-Q 寫 Stillwater
      「has commenced commercial production; however, we have not begun generating revenue」，中國以外的新產能在開、還沒有營收，反證②沒有觸發；
      Noveon 的新聞稿仍掛在 MP 的供貨邊上（failure log #14 未解）
    - USAR 研究判斷＋敘事 `ib_5b0e62610b7ee01a`（缺 X，`ew_0257`：自己的買方承諾、磁材營收、已定價主參照；11 月 10-Q 後重寫）；
      MP `ib_4c4dd0d12a6c9f1d`（已定價等回落，`ew_0203`）、6680.HK `ib_677c6eba7d7d4276`（不要）改押新讀圖，判讀沒變
    - 致動器層重讀 `sr_14456dc4d147f3f3`（undecided）：現代摩比斯供 Atlas 致動器是集團內採購、Schaeffler 綁的是互惠交易——兩條客戶端具名都不算獨立印證；
      現代摩比斯 `ib_c8e5e572872abec6`（非邊緣的不要：約 252 億美元、28 位）；SHA0.DE `ib_3671da7bf86f5edc` 改押
  - 2026-10-05｜Nidec 入圖後的一手補查（R4 報告原寫「未查」）：窗口內（09-01 入圖 → 10-02）唯一的一手是 2026-09-30 延遲發布的 FY2025 決算摘要——第三方委員會確認多起管理層參與的不當會計、6,321 億日圓減損、營業虧損 5,190 億日圓；東證特別注意銘柄指定在 2025-10-28（早於入圖）。這是治理／會計事件，**沒有觸及入圖時的結構主張**（FLEXWAVE），R4 結論不變（證據不足以判）；只記事實、不做「它為什麼跌」的因果歸因（L14）。觀測 `mo_b35ec2d6cdd9154e1be5d12cb1a67e3b`；敘事 Nidec `ib_96330eed2aea24c9`（非邊緣的不要，治理風險記在 our_bet）、宇樹 688836.SS `ib_68f7e54c0de8e0a2`（非邊緣的不要；只坐自家整機 G1，failure log #22 第二型）
- failure log：（尚無）
  - #14（反證以被評公司的供貨 assertion 形式入圖：MP 磁材邊上的 Noveon、USA Rare Earth 文件，引文沒有 MP）
  - #19（海外財報缺口：6324.T、LYC.AX、6680.HK 的已定價嗎與出現在數字裡都量不到）、#20（A＋H 檔快照市值只算 H 股）
