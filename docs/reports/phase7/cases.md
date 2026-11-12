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
| O4 | `ib_27713885500a7607`（不要：讀不出卡在它——量、產能、長約都是自報，客戶端沒有一手） | 第一個裁決點（Q3 財報，11-06 記）：量撐住了、具名還沒有；第二個 `hy_0004` 到期 2026-12-31 | 2026-10-05 | 7.5 記 | 待 7.5 |

---

## O1 AXTI／InP 基板

- 登記：registration §2 O1（開題 2026-10-04）
- 研究產出：（尚無）
- 裁決：（尚無）
  - 2026-11-03（回填；Q3 法說部分，10-Q 部分約 11-13 後補）｜AXT 第三季新聞稿（8-K 2026-10-29）＋法說逐字稿（10-29）｜①讀圖（量的賭注、窗口到 2026–2028）：維持——反證④被 AXT 自寫「2026 年產能倍增已超過」觸及，InP 基板讀圖 10-30 三次換版判讀都維持量（現行 `sr_5bd84c00f10ad7da`）②敘事「必須為真」：Q2 是新基本盤**證實**（Q3 營收 7,340 萬美元、毛利率 56.0%）；擴產沒提前、沒有第四家：未推翻（補進列舉的 Freiberger、雲南鍺業、光智科技都是既有廠）；客戶照約付款：待 10-Q ③thesis v4（不是結構性受益者）：推翻條件 §7b（Q3 營收 ≥ 6,000 萬美元）成立，[893] active → review_required；revised／retired 跟 10-Q 一起做（[896]），「錯」的 kind 等那個結論｜H7／H9／H10 待量測日（11-28）與 10-Q。逐版明細見 Q3W 段第 4 列的裁決行；寫的時候沒有看價格
- 2×2：尚未到裁決點
  - 2026-10-05｜research-drain 段 5：InP 基板層的兩家日本大廠第一份敘事（押 `sr_b8b405c96d8747c1`，不要：非邊緣）——住友電工 `ib_456a9bf890f61d5c`、JX 金屬 `ib_eab1aee5a0c458ce`；會死嗎先用一手決算短信補 runway 觀測（`mo_4083f561…`、`mo_a200134b…`：現金跑道綠、負債黃）
- failure log：（尚無）

## O1-U InP 上游：銦、晶體生長、出口管制（二階）

- 登記：registration §2 O1-U（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-17｜Wave 2（唯讀研究 workflow wf_59646a4e-958（9 位）＋走圖判定 wf_c1f5a527-bef；寫入由主 session）：一手——商務部、海關總署公告 2025 年第 10 號原文、USGS MCS 2026 Indium、AXT FY2025 10-K（庫內）、住友電工 CS MANTECH 2016 長晶論文、Dowa 有報（2026-06-23）、5N Plus 2025 年報；InP 基板層讀圖換版 `sr_9aa50cb6a36e4822`（判讀不變 volume；反證⑤措辭改準、寫進「上游折進第一層」）；AXTI `ib_9f388500f6291544`、002428.SZ `ib_0c3c7db62b3f2c47` 敘事換騎（內容一字不改）。
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
  - 2026-10-17｜**(i)＝都沒擋**：表示法——現有字彙裝得下（DEPENDS_ON／SUPPLIES_TO／CONSTRAINED_BY，原料節點有 mat:rare_earth_metals 前例）；出口管制是時變的監管狀態，照 L4 住讀圖反證⑤的 watch，位置正確。證據——結論需要的一手都拿得到。**(ii)＝沒有**：上游折進了第一層——①管制物項是「3C004.a．磷化铟」本身（所有形態，含多晶）、三甲基铟、三乙基铟與 3E004 生產技術，**銦金屬不在清單**；②銦是冶煉副產品：中國精銦 760 噸占全球 1,100 噸的 70%，中國以外約 340 噸，消費大宗是 ITO，2025 年美國到岸價只漲 11%（USGS）；③AXT 自製 InP 多晶與 pBN 坩堝、自有 VGF，住友自有 VB，看不到獨立的長晶代工層；④邊緣冶煉廠（錫業 000960.SZ、株冶 600961.SS、Dowa 5714.T、5N Plus VNP.TO）銦占營收是零頭或分不出來（Dowa 有報銦與鋅合併成一行、InP 0 處；5N Plus 年報 InP 0 處），Korea Zinc、Umicore 非邊緣，Indium Corporation 私人——最上游真正可投資的就是第一層本身（AXT、雲南鍺業都垂直整合）。指標：讀圖 `sr_9aa50cb6a36e4822`。圖沒有自己報出這個上游：走圖九型沒有一型命中 InP 基板或銦；「下一層 0 條」在 204 個 mat／tech／prod 節點裡 173 個恆亮（L14-4）——本 case 是 7.0a 人工登記開的題。旁支轉給 O6：三甲基铟、三乙基铟是管制品、也是 MOCVD 前驅物（南大光电 300346.SZ 判邊緣 4.35B／1 家，沒查它的 TMIn 營收）。
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
  - 2026-10-07｜續工 ⑤（走圖第 1 型「薄層沒人讀」）：**UHP 雷射層第一份讀圖 `sr_26e0a9fe152d5a71`（volume）**——CW DFB 層的 400 mW 高功率子集合；客戶端 NVIDIA 新聞稿：「nonexclusive」協議、數十億美元採購承諾＋產能取得權（被引用那一句沒有逐字寫出 Lumentum，不標外部印證）；Coherent 也供（Cignal 轉述）；下一層 InP 晶圓產能 fully allocated（Lumentum 自述）。坐這一格的只有 Lumentum、Coherent（非邊緣）；三條反證登 watch（訂單取消或供給寬鬆／第三家被客戶點名量產／改用不需外部高功率雷射的架構）
  - 2026-10-17｜使用者 go **[783]**（Ligent 招股書＋官網新聞稿入圖）→ **CW DFB 層反證①「第八家」觸發**：海信寬帶（Ligent，9856.HK）2026 年第一季量產 75mW 高功率 CW-DFB，「These laser chips are either sold to external Chinese and overseas customers or used for our in-house production of optical transceivers.」——同時是新商用供應商與買家自製（反證⑥那一型，發生在中國收發器廠）。
    讀圖換版 `sr_640eff4b41cefb8a`（**維持 volume、窗口再短**：規模小——光晶片占它營收 1.6%；①改成「第九家」）；押這一層的七份敘事換騎，華星光 `ib_909214fd8f0f382e`、Sivers `ib_7ff0b3092b27e675`、聯亞 `ib_9ad8fd1d85f44300`、全新 `ib_824c2cead1f98942` 在「為什麼卡在它」補 Ligent 一句（候選狀態都不變）
- 2×2：尚未到裁決點
  - 2026-10-18｜[798] go＋入圖後：CW DFB 讀圖 `sr_877bf0d2e984aecb`（volume 不變、窗口再縮）——兩週內第七、八、九家（穩懋、Ligent、光環）都是既有三五族產線轉進；反證①改成第十家並把「進入門檻低」寫成本層定性，另加⑧價格與稼動率（家數條件兩週觸發三次、判讀都沒變——#68 同型）；押這層的 7 份敘事換騎。
  - 2026-10-19｜Ayar／Wiwynn Substack lead 停 awaiting_named_disclosure（一手 10-16 已入圖；七份一手都是展示，沒有具名量產客戶或雷射晶粒廠；Wiwynn 是 Ayar 策略投資人）。OCP 2026 追線：[817] Oracle depends_on LPO（800G 15.6 萬條鏈路）＋ LRO competes_with LPO（1.6T 改 LRO）、[815] Nokia develops 6 吋 InP（onboard）待核准；買方口述（Arista 交期 3 個月→9–12 個月、Meta 說 DSP 與雷射吃緊）見讀圖換版。
  - 2026-10-19｜讀圖換版：外部光源插槽 SuperNova `sr_470b3e4a5af4e5c3`、FAU `sr_f1bec617ddd1dacf`（Wiwynn 兩份展示稿；SENKO 自稱展示用它的可拆 FAU）、CW DFB `sr_def7cb705477572e`（新增反證⑨）、可插拔 `sr_f0ffe8e47d5e2d30`（undecided 照舊）、模組 DSP `sr_68ef6e4e806a8563`、TIA `sr_b4b092ec2aae3474`、CPO `sr_3892c7001d76a6fc`、NPO `sr_7fa43e00e0b03227`（改判 neither）、全堆疊測試 `sr_e0596e1ad9f818ce`、InP 基板 `sr_e8cab2cad68816c0`；上詮、波若威（已定價改答是）敘事換版，其餘騎乘的 14 份換騎。
  - 2026-10-19（核准後）｜[817] Oracle、[815] Nokia、[818] PD 建模邊入圖；LPO `sr_93c474eaf0b36807`、可插拔 `sr_2ef646179411e5be`、光偵測器 `sr_d1ff0e724eb5d464`、6 吋 InP `sr_0cde28aa6c1bcc63` 換版；[819] 向你要環宇 200G PD 文件。
  - 2026-10-19（券商報告）｜[764] CPO 測試分工與量產時點——全堆疊測試讀圖 `sr_43733ba80b33970d`、AEHR `ib_74a43a0177565ffc`、FORM `ib_cb5228f385ddece6`；[765] Lumentum OCS 客戶地位——MEMS 讀圖 `sr_6fea82e5c4f0f52c`、Silex `ib_fa5061575d5e8ffa`；[803] Lumentum 晶片製程與磊晶來源——光環 `ib_280a088fc3140f02`、華星光 `ib_e0f20f182c6be46e`、聯亞 `ib_cc19ea7d73fdbdac`（全部券商稱、不入圖）（券商內容私有：library/private/research_notes/doc_requests/）。
  - 2026-10-20｜FormFactor 一手：券商轉述的 CPO 營收追回 Q2 法說——講的是全公司 CPO 營收，insertion 1 只是加速原因；「The CPO piece does flow through that 10% customer」＋10-Q 附註 2 台積電 11.0% → 入圖包 [825]（co:formfactor supplies_to co:tsmc，供應商自述、標弱）。CPO 全堆疊測試讀圖 `sr_74e45898380212a2`（undecided 不變）、FORM `ib_faf0d9e681f38d6b`（不要不變、理由改由一手撐）、AEHR 換騎。
  - 2026-10-20｜Lumentum 一手核券商四題：OCS 大客戶沒點名、預期 2027 年初才成第一大供應商（券商講過頭）；10-K 沒有 MEMS、沒有 epitaxy；雷射晶片 OFC 簡報列 MAKE → 入圖包 [827]（co:lumentum develops tech:mems_mirror_array，設計權）。MEMS 讀圖 `sr_a7bd059e23aa6e88`（undecided、加反證④）、Silex `ib_26d8129aa16683a2`、光環 `ib_6f2e71838ae8c328`（更正前版「差距收窄只靠晶粒」）、華星光 `ib_268b1bed22dcf35f`、聯亞 `ib_899f7c33036e91af`；候選狀態都不變。
  - 2026-10-20｜走圖第 7 型 `tech:lro`（圖上 0 家）追到底：入圖包 [828]（Jabil 模組 is_variant_of LRO）、[829]（Credo、Marvell〔TRO〕、MaxLinear、Semtech、中際旭創、新易盛、Ligent 供 LRO＋LRO depends_on 光模組 DSP＋對稱邊；全是自報、MaxLinear 最弱）、[830]（MaxLinear 10-K claim 更正：LRO 保留發送端 DSP）；Broadcom／AAOI／Coherent 沒找到量產一手（L11-5）。LRO 第一份讀圖、DSP／LPO 換版、MXL 敘事等 [829] 入圖後在真圖上重跑再寫。
  - 2026-10-20（核准後）｜[823]–[830] 使用者 go、入圖（intake 32b40920…e62564ea）。LRO 第一份讀圖 `sr_6c64cb3c6d3f8e11`（neither：發送端 DSP 三家、OIF 互通協議、沒有缺貨一手）；光模組 DSP `sr_a5003860dc987d46`、LPO `sr_a25896f0e7912080`（都維持 neither；更正「1.6T 從零顆 DSP 走回半顆」——把全重定時算進來是持平到下降）；MXL `ib_a8bb7f16d2935af3`（不要不變）。CPO 全堆疊測試 `sr_28a7f4dd8f29433f`、MEMS 鏡陣列 `sr_8dd7652e9ca791bf` 只改「待核准／圖外」措辭；AEHR、FORM、Silex 換騎。走圖第 7 型 `tech:lro` 消失。
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
  - 2026-11-06｜research-drain pq1：第三季 8-K（11-05，lead_a034d6b9 `original_obtained`）營收 2.699 億美元（去年同期 1.186 億、年增約 128%），第四季指引 3.85–4.2 億；
    與一家 Tier 1 超大型資料中心客戶簽多年期策略協議（沒具名）；美國 2027 擴產因取得電力較久延後。第三季 10-Q：與「major hyperscale data center customer」的三年 LTA
    （2026-06 到 2029-05，某些 1.6T 產品需求的 10%），客戶沒具名；第三次 ATM 10-01 完成（約 570 萬股、均價 105.36 美元、淨得約 5.88 億）＋EWB 2 億美元貸款——
    lead_49085eb7 由 `contradicts` 改 `original_obtained`（ATM 缺口回答了）；8 月 TLDR「第四季逾 5 億美元」被指引推翻（lead_20eb32ac `contradicts`）。敘事不換版（不要的兩個理由——讀不出卡在它、客戶沒具名——都沒動）
- 裁決：2026-11-06（第一個裁決點，第三季財報）｜**量撐住了、具名還沒有**——自報的量出現在營收（年增約 128%、第四季指引再往上），不是「自報未撐住」；
  客戶端或第三方一手具名 AAOI 的量產供貨仍沒有，不是「自報被確認」。第二個裁決點照舊：`hy_0004` 2026-12-31 到期。揭露：這次沒看 AAOI 價格
- 2×2：尚未到裁決點（第二個裁決點 2026-12-31）
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
  - 2026-10-07｜續工 ①（晚段）：**波若威 3163.TWO 第一份敘事 `ib_a35b0492e80432ee`（缺 X）**——押 FAU 層 `sr_8c9292bfbc2b492a`；X＝①FAU 層的量或換不掉（五家被客戶點名、Coherent 可整套自製）②CPO 光纖套件與配線盒量產出現在營收（2025 年報致股東報告書：115 年下半年開始量產；8 月營收年增 9.7%）③已定價主參照（自家歷史只湊得出約兩年）；等待 `ew_0371`（11-16）、反證 1、加碼條件 1（同日 `ib_987df2c1dad5c4e7` 換版：評價利益的主詞改成「股票與 ETF」）。三項必查都做：致股東報告書、表頭（113／114 兩年度合併）、同義節點（`tech:cpo_fiber_attach` 未併，續工 ⑥）。順帶發現：①本業利潤薄、淨利大半是持股評價（2026 H1 透過損益按公允價值衡量之金融資產利益 2.92 億元 vs 營收 12.48 億元）；②季報股數 2026Q2 mismatch 17.5% 是待分配股票股利（每股 1.75 元）、不是增資；③月營收缺 2024-05——今天的 36 個月回補漏掉那一個月，補回後已定價窗 484 → 726 天（仍不滿三年）
  - 2026-10-07｜使用者 go：**[730] FAU 同義節點合併**（commit `a5024b04`：`config/entity_aliases.json` 一筆＋`loader/migrate_fau_merge_20261007.py`；備份 `20261007T141331Z` 後 apply）——`tech:cpo_fiber_attach` 刪除、Coherent 掛在舊節點的供貨邊併進既有那條、FAU 多一條 is_component_of `tech:scale_out_cpo`（原邊搬家，不是新來源）、cl1 改指 FAU；舊 id 殘留 assertion／claim／關係 0、重投影 11 條邊 0 衝突、audit invariants 14 PASS。FAU 讀圖重讀 **`sr_aa0b79ad032a31c4`**（仍 undecided，「表示法缺陷」修完）；波若威 `ib_45fdc0945f279b22`、上詮 `ib_84f838c2b0cc8801` 換騎（各格內容不變）。`tech:cpo`／`tech:scale_out_cpo` 疑似同義，另案
  - 2026-10-07｜向你要文件 pq2 **[735]**：波若威（3163）、上詮（3363）的 CPO 光纖組件／FAU 營收占比與客戶平台（台灣券商報告或法說 memo；兩檔都停在「缺」）
  - 2026-10-08｜**Photonics-SOI 層說明 v1**（層深讀入口「下一層 0 條」——矽光子 PIC 層判量、上游沒接；SOI.PA「缺 X」指向這一層；`library/private/research_notes/layer_notes/mat_photonics_soi_wafer.md`，ledger `ln_b3a788384542e760`）：
    **客戶說換不掉、供應商說不缺**——GF 2025 年度 20-F：300mm SOI「our primary supplier」是 Soitec、占 SOI 晶圓支出約 71%、換一家「would take us an extended period」、替代來源近期拿不到量（客戶端一手，**不分光子**；GF 與 Soitec 2024 年協議增補名稱只寫 RFSOI 與 FD）；
    Soitec 自己的 URD：FY2026-27 獲利受「low fab loading」影響、AI 領域 Photonics-SOI 的競爭者是 SEH（持 Smart Cut 授權到 2033）與 GlobalWafers；聯電 20-F 泛指矽晶圓「supplies……are adequate」。
    讀圖換版 `sr_f0f03b1e543dc73a` → **`sr_6707b77bd1a5958c`（仍 undecided：A 有客戶端一手但不是這一層的〔L6〕、B 指向不缺）**；層主張 S1–S4 登 watch（`ew_0422`–`ew_0425`）；
    SOI.PA 敘事換版 `ib_01af87313ad148a5`（仍「缺」，X 縮成「光子用 SOI 的客戶端一手」＋已定價主參照；反證加一條連 S1）。因層說明改變的候選狀態 0 筆。
    新摘錄三份（程式截取、逐字）：`soitec_urd_fy2026_photonics_competition_excerpt`、`gfs_20_f_20260227_soi_supplier_risk_excerpt`、`umc_20_f_20260430_wafer_suppliers_excerpt`。
    旁證（L11-4）：GF 這份 20-F 早已入圖（`gfs_20_f_20260227`），但策展摘錄只收了 Raw Materials 那一句、沒收風險段的 71%——failure log #46
  - 2026-10-17｜**E2 成立 → 外部光源層改判 neither**：使用者 go [773]（Broadcom OCP 2026 TH6-Davisson 夥伴投影片）、[779]（NVIDIA 部落格「Lumentum, Sumitomo, and Coherent: These vendors provide ELS assembly, optical alignment, and test with the silicon photonics engine.」）入圖，[778] 把 `prod:els_module`、`tech:els_pluggable_module` 併進 `tech:external_laser_source`。
    客戶端點名的 ELS 供應商由 1 家（Coherent）變成：NVIDIA 三家＋Broadcom 的 ELSFP 夥伴七家（eoptolink、O-Net、TFC、FIT、Source Photonics、Aperion、Ligent）；買方 Meta 明寫「OIF ELSFP compliance to enable open ecosystem and multi-sourcing」。
    讀圖換版 `sr_3429846bcf5ae77a` → `sr_a5736ee4bae76eaf` → 同日更正 **`sr_62e2a48a354f407c`（neither：模組這一格不卡——買方刻意多源、組裝產能從收發器產線挪得過來；錢流向下一層的高功率雷射晶片）**——更正的是「高功率雷射要嘛向外買、要嘛還在開發」一句：Ligent 官網 2026-09-07 自述 ELSFP「featuring self‑developed CW lasers」、100 mW 版已初步商用，[773] 的 claim 早已寫明，寫讀圖前沒 grep 自家庫（L11-4，failure log #76）；E2 處置（入圖完成、不再登記），E1／E3–E5 沿用、新增「量產只集中在一兩家」一條。
    **O5 的讀法**：「Coherent 是唯一」早已推翻（10-04 的 `already_available`），這次連「第二來源」都不稀有了——這一格的倍率不在模組。
    邊緣檔 Ligent（9856.HK，海信寬帶）第一份敘事 `ib_6a9066192211ada6` → 同日更正 **`ib_c2ed62e6e0972a48`（不要**：只坐這一格、本體是數通光模組 69.4%；它自述 ELSFP 用自研 CW 雷射，但自製雷射的模組廠不只它、光晶片只占營收 1.6%——光晶片長到一成以上或 400mW 照時程通過驗證由反證叫醒）。
    Sivers 換騎 `ib_bd872222b5a0eaa6`（→ `ib_fbbe08ac5b795369` 換引用到更正版讀圖），「為什麼卡在它」補 Broadcom 的「standard lasers. You don't need fancy combs」與「you don't even need an external laser source」。Lumentum ELS 邊的合格狀態衝突 pq2 **[781]**（取 qualifying）
- failure log：（尚無）
  - #27（SOI.PA FY2026 分部占比兩筆都生效，「出現在數字裡」被默默丟——當下修為印衝突；序列仍成不了，合併紀錄留 7.5）
  - #46（入圖時的策展摘錄只收當時要的那句，同一份申報裡更強的客戶端證據留在庫外——10-08 要重抓 EDGAR 才看得到）

## O6 光通訊磊晶與 MOCVD 產能（二階）

- 登記：registration §2 O6（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-07｜使用者 go **[715]** 入圖（intake `2b2814f8`）：`mat:inp_epiwafer` 建層；第一份層讀圖 `sr_d16f22339e294216`（volume；層說明 A6–A8 登成讀圖反證）。鄰層換版、判讀不變：CW DFB `sr_d6819880c609bef7`、InP 基板 `sr_3771f0c4c0264542`（需求側多一條買方四年長約）、光二極體 `sr_162c61ce62e6e2fe`；騎這些讀圖的敘事重新連結（聯亞、全新、華星光、SIVE、COHR、LITE、穩懋、AXTI、住友電工、JX、英特磊；COHR／LITE／AXTI 補「已定價」組中位數引用）。要文件 [716][724][725] 改寫成具體去哪找（元大／凱基 App、搜尋字、日期區間；failure log #38）。
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
  - 2026-10-17｜**Wave 2 結論**（唯讀研究 workflow wf_59646a4e-958（9 位）＋走圖判定 wf_c1f5a527-bef；寫入由主 session）：**(i)＝證據**——開題時是表示法（圖上沒有磊晶層），[715] 一個 RA 一天就解；層建好之後四檔敘事卡的格全是證據或價格（聯亞已定價等回落、IQE 缺承諾的量與 InP 營收拆分、全新缺 CW 磊晶的量與變體、英特磊份額只有自報），層讀圖缺的三格（聯亞客戶全是代號、BH 還是脊形沒有客戶端文件、份額只有 Yole 2021）也是證據。表示法只剩設備層（圖上沒有 MOCVD 節點，AIXTRON、Veeco 不在名冊）。**(ii)＝沒有**——設備層讀得出是薄的、集中需求也真的灌進去了：買方 MOPS 取得資產公告三筆具名「AIXTRON SE」（聯亞 2026-06-17 約 8.37 億元、08-26 約 9.9 億元；全新 07-30 約 6.53 億元一批、每單位約 9,335 萬元，用途只寫「供生產使用」、不分 InP 或 GaAs）；AIXTRON 新聞稿具名 Lumentum 下多台 G10-AsP；光電占接單 Q1 近七成、Q2 約 75%；Q3 初估接單約 2.75 億歐元、CEO「driven by strong demand for equipment for laser applications in AI data center communications」；現金流主要來自客戶預付款。但可投資的那一半不成立：AIXTRON 非邊緣（41.7 億美元、15 位分析師——比第一層四檔的 8／8／1／3 位都擁擠）；Veeco（邊緣 26.1 億、3 位）的化合物半導體只占 Q2 營收 11%，且在等 Axcelis 全股票併購（SAMR 未批）。這一層押的是量、時鐘短：管理層說 2026 年的限制是爬坡速度不是產能上限、約 15 家雷射廠占相關接單約八成（皆轉述）。指標：讀圖 `sr_d16f22339e294216`；敘事 `ib_37cabf618c6f1978`、`ib_c490d6f9208776d2`、`ib_afd3e889b15a9ed6`、`ib_82e4ee2f96d53261`。另：反證 watch `ew_0643`（AIXTRON 雷射設備大批出貨再延後）的比對實體掛在聯亞，AIXTRON 自己 10-29 的完整季報叫不醒它——10-29 後由互動 session 手動判一次（failure log #71）。開題登記預測的 failure mode「設備產能下游文件很少寫」只對一半：台灣 MOPS 第 20 款寫得出交易相對人，但不寫機型與用途。
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
  - 2026-10-07｜續工 ⑤（走圖第 1 型）：**6 吋 InP 產線層第一份讀圖 `sr_ad7419b129b4dad5`（undecided）**——這一格是製造能力、不是多家供貨的市場：只有 Coherent 自述在 6 吋量產（「客戶因此選它」也是它轉述的），穩懋在開發（develops 邊，不在供給側快照）；量的訊號在下一層（Coherent 預付 AXT 2,228.85 萬美元鎖 6 吋基板）。兩條條件登 watch（第二家 6 吋 InP 量產／客戶端寫明選供應商的理由是 6 吋）。邊緣公司不在這一格
  - 2026-10-18｜**盤點 B 組（光通訊電子件與封裝）**：①pq2 **[789]**——GF 2026-10-08 新聞稿：與 TSMC 簽製造協議在美國 Malta 供 CoWoS 用矽中介層（2028 上半年量產爬坡、初始五年；**原文無金額**，WebFetch 摘要的「$2 billion」不存在）——圖上矽中介層第一個供應商，並把 tech:cowos 接到先進封裝總稱節點（先進封裝讀圖缺口①的建模那一半）。②pq2 **[791]**（取代 [790]）——GF＋Marvell 擴大 SiGe 產能協議（2026-09-17，Burlington）＋Marvell 投資人日簡報（2026-10-06）「SiGe Drivers / TIAs」「Multi-foundry」：SiGe 平台供應商 1→2、TIA／驅動器接上 NPO 與 CPO；[790] 把 enables 方向寫反（failure log #78，當下修）。③**LPO 第一份讀圖 `sr_bfd181ebfe7dee2b`（neither，層）**：Meta 一個 hop 量產、模組廠多家（Ligent、中際、新易盛）、Arista 交換器支援，沒有任何缺貨一手；它是光模組 DSP 層的反向路徑，需求錨走不到是建模缺口（is_variant_of 不走訪）。④MRM 兩個節點（`tech:micro_ring_modulator`、`tech:mrm_200g`）是變體不是同義，但共用別名 MRM——第 9 型偵測不到（failure log #79，量測全圖 10 對）。
  - 2026-10-18（第二段）｜三個小缺口到終局：①CPO 測試讀圖缺口③台積電徐國晉「四大瓶頸」——只有 SEMI 矽光子峰會（8/31）的媒體轉述，官方逐字稿或簡報找不到（「我找不到」≠「不存在」），讀圖原本就寫「未取得官方逐字稿」，不換版；②FAU：Broadcom 點名的 TwinstarTech 是上海松江的被動光元件廠（官網：光纖陣列、MPO、「Co-package optics」，13,000 m²、700+ 人），沒看到掛牌資訊；大立光的邊在下一層微透鏡陣列，FAU 讀圖不寫是對的；③InP 上游旁支（三甲基銦）：南大光電 300346.SZ 2025 年報「前驱体材料（含 MO 源）」占營收 27.61%、不拆三甲基銦，MO 源以 LED 外延為主（全球 MO 源市場約 1.8 億美元，年報引述）、內銷 92%、沒有 InP 磊晶客戶具名——無 graph delta，旁支結案。
  - 2026-10-18（第三段）｜[791][795][797] go＋入圖後：TIA／驅動器 `sr_39d9cc30a0930d3f`、SiGe 平台 `sr_34ab9730422a03c2` 第一份讀圖（都 undecided：一個月內兩家 TIA 廠各自向晶圓廠鎖 SiGe 產能是量的形式，但沒有任何一方寫缺貨或交期、兩家晶圓廠都在擴產）；LPO `sr_5f0f6049746b4e05`（neither 不變，Semtech 進供給側是印證方向）；光二極體 `sr_d98d104c46bdb6f9`（undecided 不變：環宇自述「極高的市佔率」撐不起改判、第一大客戶 66%）；CPO `sr_13fb65acb28af9b2`、NPO `sr_9a05655ba2466b7a` 補下一層 TIA。名冊批次 [796] 短檢查③：VIAV（測試儀器、年報無 CPO、自列七家競爭者）、COHU（測試分類機與測試座、無 CPO／矽光子字樣）——都寫「不要」附一條重開反證。環宇、光環第一份敘事定稿（缺 X），等光互連主題組 v2 pq2 [802]（補登組定義後才登記的五家）go 後寫入；光環的 CW 雷射功率等級與客戶向你要文件 [803]；光環的股數：初版誤判快照多算私募，公開文件追源找到 2026-09-21 現增 1,500 萬股收足——快照正確，同日更正（failure log #82）。
  - 2026-10-19｜AMEC lead 停 not_pursued（ZDNet 單一媒體、試的是功率 SiC／GaN 機台；AMEC 半年報 2026H1 才啟動 InP 專用 MOCVD 開發）；段 4 走圖新命中 `co:gcs_holdings` 走不到錨 → [818] 補 `tech:pluggable_transceiver depends_on tech:photodiode`（更正走廊、引文是環宇年報已入圖的 s1）。
  - 2026-10-20｜InP 磊晶層說明 v2 `ln_acc43e2ebfbd2a7a`：Lumentum 10-K 全文沒有 epitaxy；住友與聯亞的磊晶份額仍只有券商一個出處（內容私有）。
  - 2026-10-20（[819] 讀完）｜券商報告列了三家美國模組廠的 200G PD 供應商分工——券商稱、不入圖（券商內容私有：library/private/research_notes/doc_requests/）；環宇第一大客戶（66.19%）沒答到。光偵測器讀圖 `sr_dc76762c792f4c96`（更正「沒有一家寫 200G/lane」：MACOM 2025-03-25 自寫）、環宇 `ib_3a006e2f3d922739`、英特磊 `ib_199a6ef5fec4fde0`（缺 X 不變）；[820] drop 後換號重生 [822] 再 drop（failure log #89）。
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
  - 2026-10-18｜[792] go＋入圖後：LPT 讀圖 `sr_f55b7769209acef2`（volume 不變）——需求側由 IREN 一家擴到四家買方（Oncor、Core Scientific、Fermi），其中兩家付代價鎖貨（Oncor 靠供應商關係換到交期承諾、2027Q1 才到第一批；Fermi 借 1.2 億美元預購高壓設備）；Oncor 的需求來自電網、不經 AI；反證①盯的公司補齊四家（#65 同型）。
  - 2026-10-20｜使用者點名 Microsoft 退出 Nscale：一手核到只退 Loughton 一站（50 MW；雙方發言人經 AFP／Reuters 轉述）、Monarch 1.35 GW 意向書夏天已失效由 Anthropic 接手——不是需求反轉、不計入已取消需求；FT 原文 → 向你要文件 [821]。副產：Nscale S-1 p.31 站點的大型電力變壓器有顯著部分來自中國 → 入圖包 [824]（第五家買方，名冊隨包 staged co:nscale）；LPT 讀圖 `sr_e317c089018c5d45`（volume 不變；Nscale 圖外、行政命令 14421、Loughton 卡在併網不是變壓器）。雷達市場層只找正向大事 → failure log #88、當下修 8e6dad9b。
  - 2026-10-20（核准後）｜LPT 讀圖 `sr_a784972def54595a`：Nscale 由圖外改成引用（[824]），反證①補 Nscale 的鬆動條件與核查節奏。
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
  - 2026-10-07｜續工 ③④（晚段）：**電工鋼層重讀 `sr_4815aae51426ad76`**（取代 `sr_467982cb902b776c`；仍 undecided，新增「**這一層沒有可投資的公司**」——坐在這一層的上市公司都是綜合鋼廠：Cliffs 的「Stainless and electrical steel」合計 5.25 億美元、占 2026 Q2 營收 52.26 億的一成〔10-Q 產品線營收表，raw 節錄〕、JFE 的電磁鋼板不拆營收〔有報 grep〕；DOE 2022 的 13 家 GOES 廠與日韓德規格級廠也是綜合鋼廠；登記兩個條件 watch：買方一手的交期／配額／預付 → 量、GOES 占營收過半的上市公司或電工鋼分拆 → 重答可投資）。CLF 廣度短敘事 `ib_d4e4af073bed51db`（**不要：曝險太薄**；同日 `ib_7854f58bf92e65a2` 換讀圖 id）。5411.T 短檢查＝**①補供貨邊**：JFE 自己的「電磁鋼板戦略」說明會資料（2024-10-24）p.3——GO 在倉敷生產、用於電力與配電變壓器、主要賣給重電廠 → `ra_c9dc8e5f9266b905f385ecf602b7dc37` → pq2 **[729]**（directed lead `lead_47e5000ff705cdb71b11d64867555128`）；同一份 p.8：日本國內擴產的是車用 NO、GO 只在印度擴。敘事 `ib_458fb43e6f11c7f8`（不要：曝險太薄；同日 `ib_ad8a0cfcc5383313` 換讀圖 id）。⚠ [729] 的搜尋摘要寫「統合報告與有報都沒拆 GO」——寫的當下只讀了有報，統合報告（2025 版第 5、7 節）事後 grep 才核對到同樣沒拆（L11-5：結論碰巧對，順序錯）
  - 2026-10-07｜使用者 go：[729] 入圖（intake commit `0b1c05e0`；`complete-ra` 結案）→ 讀圖檢查把電工鋼層標成該重讀（供給側新增 co:jfe_holdings 一條）→ **重讀 `sr_761bd010a662901a`**（取代 `sr_4815aae51426ad76`；仍 undecided、仍「這一層沒有可投資的公司」）：新的邊只多確認一家日本規格級廠，沒有量、價或換不掉的證據；JFE 把國內擴產給了車用 NO 而不是 GO，是供應商自述、不當反證；兩個條件 watch 改掛新版（舊的兩筆收掉）
  - 2026-10-08｜**更正 10-05 那筆的「撤回」**（上面那句保留不刪）：DOE 有寫——報告 p.21（PDF 第 36 頁）：「When the end-users request that porcelain for bushings to be sourced outside of China, there are limited sources available including U.S., Japan, and Poland.」
    10-05 的「全文找不到」是 pypdf 文字層把字拆開（porcela in、a va ila ble）造成的 grep 失誤（L11-5，failure log #47）；原標題的「只剩」仍過度——原文是 including（列舉）。套管 lead 的 parked_reason 已附加同一則更正
  - 2026-10-08｜走圖第 7 型「沒人供應」→ **分接開關層**：入圖包 pq2 **[739]**（`ra_fc186b9d57144e080858681047aa468b`；lead `lead_b97b021796c41c7ba053937e98a48f14`，`graph_walk:no_supplier`）——
    華明裝備（002270.SZ；系統口徑邊緣 22.8 億美元、10 家；名冊條目隨包 staged）`supplies_to tech:transformer_tap_changer`（自報：「国内第一、全球第二」「国内尚无成规模竞争对手」；
    分接開關 2025 年營收 21.02 億元、毛利率 59.61%、出口 +47%；2026 上半年 +14.6%、出口 +44.6%、新增訂單增速與去年同期相當；500kV 以上仍以進口為主；在辦 H 股）。
    層說明草稿 v0（`library/private/research_notes/layer_notes/tech_transformer_tap_changer.md`，主張 T1–T4 等入圖後登 watch）。缺：2026 年的客戶端一手（DART 檢索頁擋自動查詢）、德國那家是誰（推一步 MR，非上市）
  - 2026-10-08（同晚，續）｜**2026 年第三方一手補上**：National Laboratory of the Rockies NLR/TP-5700-96742（2026-05-06，訪談美國變壓器廠與供應商；媒體轉述「套管 130 週」追回原文）——
    「OLTCs take 80–90 weeks to procure and have just 1 or 2 U.S. manufacturers; otherwise, they are typically sourced from Europe」「Reinhausen is the only U.S. OLTC producer」
    「U.S. manufacturers also import bushings and OLTCs from Germany and Switzerland」「345-kV bushings take more than 130 weeks」「Hitachi Energy manufactures bushings domestically, but production is generally limited to the ≤235 kV class」。
    入圖包 pq2 **[740]**（`ra_834d8a606e347ffeb3d1ba3f1f866d14`；5 條邊；名冊隨包 staged `co:reinhausen`，私人、ticker null）；套管 lead `lead_857be4a6`（park 等的「2026 年一手」到了）與分接開關 lead 都接上。
    **讀法改變**：美國這段缺貨的受益者是 Reinhausen（私人）與 Hitachi Energy（日立子公司）；報告沒提到中國貨源——華明（[739]）不在美國這條線上，它的量是中國電網＋美國以外出口（穩定成長、不是爆量）。層說明草稿同步改寫（加 T5）
  - 2026-10-08｜使用者 go [739][740] → 入圖（intake 9e617677、b32229a7）、名冊（華明、Reinhausen）登記、發布者名冊補登國家實驗室（包裡已寫明第三方）→
    分接開關層說明 ledger `ln_0a3b60a33ecff0cf`（T1–T5 登 watch）；**第一份讀圖 `sr_8d94aadb859c3e65`（volume）**——需求側第三方 2026 一手、客戶在接受換品牌（不是護城河），
    可投資的純供應商只有華明且不在美國這條線上；**套管層第一份讀圖 `sr_92e8df93643eedad`（volume）**——沒有可投資的純供應商；LPT 層重讀 `sr_d78aa6617c9eb00f`（判讀不變，下一層補 2026 證據）；
    **華明第一份 v2 敘事 `ib_5c26d7071cc7ae09`（缺）**：X＝全球缺口流向它的一手、已定價主參照；反證連讀圖 #1、層說明 T1、T4；等待 `ew_0435` 在 10-31（第三季報）叫醒。
    走圖「沒人供應」12 → 10（分接開關、套管都有了供應商）
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
  - 2026-10-17｜**Wave 2 結論**（唯讀研究 workflow wf_59646a4e-958（9 位）＋走圖判定 wf_c1f5a527-bef；寫入由主 session）。新的一手：國家實驗室 NLR/TP-5700-96742 全文（圖上那份只節錄了分接開關與套管）其實寫了 CTC 與壓板——「However, for CTCs, which are a critical component of LPT windings, Sam Dong is the only domestic manufacturer.」「This reliance on a single U.S. supplier creates a supply chain bottleneck, prompting original equipment manufacturers to turn to imported CTC.」（2025 年訪談）、部分區域 CTC 供應商退出、GOES 與 CTC 各占 LPT 成本約 25%、壓板「a single domestic manufacturer」且「not many options outside of China」；**美國海關提單**（ImportKey 彙整頁）：KSH International（KSHINTL.NS，邊緣 0.67B／1 家）2026-10-12 把「CONTINUOUSLY TRANSPOSED CONDUCTORS CTC」運給 Virginia Transformer、10-14 運給同地址的 Georgia Transformer；Precision Wires India（PRECWIRE.NS，邊緣 0.86B／1 家）10-06、10-13 把 CTC 運給 Pennsylvania Transformer——兩家 LPT 廠都在圖上。KSH 自己的簡報：產品線有 Continuously Transposed Conductors、出口約三成含美國、產能 2027-03 擴到約兩倍、FY26 利用率 64.8%——**薄只在美國國內這一段**，印度產能正在倍增，量的窗口可能比 LPT 本身早關。→ 入圖包 pq2 **[774]**（`ra_f5dbda57026d610cd39a4b7127af527a`；NLR 走更正走廊；名冊兩筆 staged；發布者「U.S. Customs and Border Protection」與 ImportKey 能不能當入圖來源，請在核准時一併判斷）。絕緣層：沒有上市、主業是絕緣材料的邊緣公司（Weidmann、Cindus 私人；Nomex 2026-04-01 已由 DuPont 賣給私人的 Arclin；日立能源印度非邊緣）。
  - **(i)＝證據**：開題時表示法是 0，decompose 一天補上；之後擋的是證據——下游 filing 從不具名上游、政府報告具名的都是私人公司或大集團；把上市邊緣公司連上 LPT 廠的是海關提單，這類來源不在管線裡。附帶表示法缺口：走圖第 7 型只認「零條供應邊」、認不得「只有私人或巨頭供應」，CTC、絕緣、套管、電工鋼四層都不亮（failure log #72）。**(ii)＝有**：分接開關的華明（002270.SZ，邊緣 2.28B／10 家；讀圖 `sr_8d94aadb859c3e65`、敘事 `ib_5c26d7071cc7ae09`「缺」——它不在美國這條線上）；CTC 層的 KSH、Precision Wires 待 [774] 入圖後補讀圖與敘事才成列。其餘層：電工鋼、套管、絕緣＝沒有；出廠測試＝供給側照定義是 LPT 廠自己（`lead_188e1fa1` 停放理由）。
  - **H5 帳（三個二階 case，判準 7.0a 凍結、wave 2 不改）**：O6 (ii)＝沒有、O1-U (ii)＝沒有、P2 (ii)＝有 → 三個裡 2 個 (ii)＝沒有＝**達到「削弱」（殺死條件）**；正式裁決照登記在 7.5 寫。proposal §8 的產品化條件（≥2 個 (i)＝表示法擋住，而且上游有第一層看不到的候選）：三個 case 的 (i) 都不是表示法——不成立。讀法：往上游走沒有比第一層更容易找到非共識公司；P2 那一個「有」是靠一類新來源（海關提單）找到的，不是靠往上游走本身。
  - 2026-10-17｜使用者 go **[774]** → 入圖（名冊 KSH、Precision Wires；發布者名冊補「U.S. Customs and Border Protection」＝監管紀錄）。**CTC 層第一份讀圖 `sr_6f443137842396a1`（volume，範圍限美國國內）**、**絕緣材料層 `sr_37d39efa37d1f2f4`（undecided）**；LPT 層換版 `sr_6dd80c0c8c245f16`（判讀 volume 不變，下一層接上這兩層）。
    新讀一手三份（節錄進 `library/raw/`）：KSH Q1 FY27 簡報＋法說逐字稿——「CTC will represent anywhere between 50% to 75% of that segment」（特殊線材占營收 75%）、美國「each of them represented between 8% to 11% of total revenue」、與 Hitachi Energy 簽五年框架但「no quantity or, you know, price defined」、新客戶「link it to the market price」、Q1 每噸 EBITDA 93,325 盧比（去年 65,885）；
    KSH FY26 年報：營業現金流 −6.50 億、購置設備 −16.28 億盧比（IPO 39.75 億補上）；Precision Wires FY26 年報：出口 14.83%、CTC 占比未揭露、「USA imposed substantial tariffs on Indian Products during the year」。
    **KSH 敘事 `ib_3ce1b35b6eadad69`（缺 X，`ew_0770` 11/20 叫醒）**：X＝①Q1 每噸 EBITDA 的跳升是價還是 CTC 占比暫時偏高（管理層自己說兩三季內回落）②Hitachi 框架寫不寫出量③全球（不只美國）也緊的第三方證據——讀圖只證到美國那段，而美國只占它營收約一成；
    歸零旗標補 mechanical 基期 `mo_c5a370fb876637f9268caf1e5030b87b`（FY26 現金、總債、自由現金流）→ 現金跑道與負債兩盞紅（擴產＋營運資金燒錢），持續經營意見是 judgment、鑄 pq2 **[782]**。
    **Precision Wires 敘事 `ib_cdf43407f53be8b9`（不要：CTC 只是五個產品之一、出口共 14.83%，美國這段推不動整家公司）**。
    P2 (ii) 照舊＝有（KSH 是邊緣、缺 X）；但 KSH 的「有」要靠全球也緊才成倍率——讀圖只證到美國、美國約一成，H5 的「上游有非共識候選」在這一檔是**有候選、尚無倍率路徑**
  - 2026-10-17（夜）｜使用者 go **[785]**（KSH Q1 FY27 簡報＋法說入圖：KSH→Hitachi 五年框架〔自述、量價未定〕、CTC 占特殊線材 50–75%、美國 8–11%）、**[782]** KSH 持續經營意見（無保留）寫入 Engine C、[787] Precision Wires 的同型提案鑄號。
    CTC 讀圖主動換版 `sr_cf14fb582d8b131d`（判讀不變；缺口②的 KSH 半邊補上；digest 沒變——既有邊多自述來源），KSH `ib_63239e9aa6a0fe97`、Precision Wires `ib_168eab8e1e4814c8` 換騎。
    同夜發現 Precision Wires 與 Ligent 被閉包閘門用過期座位表排出母體（failure log #77，當下修）——補 mechanical 基期 `mo_ab3412cdfd022d1e1d04fb000b2c991a`（FY26：自由現金流 −2.07 億盧比；營業現金流含 usance 信用狀買銅 1,01,811 lakhs 的應付帳款）後到終局
  - 2026-10-18｜**盤點 B 組（workflow 9 位撞 session 額度全滅，主 session 用它們下載的檔接手）**：
    ①華明（[788] 待核）：H 股 Application Proof（Frost & Sullivan，公司委託）2024 年分接開關全球份額 17.9% 第二、海外營收 19.9%；美國海關提單 2026 年 5–9 月幾乎每月直接出貨 OLTC 給 Prolec GE（Shreveport、Waukesha）——推翻分接開關讀圖「華明不在美國這條線上」那句，[788] 核准後重讀 `sr_8d94aadb859c3e65`、改寫 `ib_5c26d7071cc7ae09` X①、層說明 `ln_0a3b60a33ecff0cf` T5。
    ②LPT 第二個開口的買方：pq2 **[792]**——Oncor 8-K（2025-11-05）「securing critical long-lead time equipment, including large power transformers」＋供應商交期承諾、首批 2027 Q1；Core Scientific 10-K「lead times of 12 to 18 months or longer」；Fermi 10-K 1.2 億美元高壓設備倉儲融資提前採購變壓器——名冊隨包 staged 三家（Oncor 股權未上市 ticker null）。CoreWeave、Equinix、DLR 等 10-K 沒寫變壓器交期；Constellation 的週數是轉引 NIAC，不收。
    ③絕緣、套管、電工鋼的對美出貨人（ImportKey 海關頁 175 檔）：壓板（台州新源）、絕緣件（遼寧 XD 興啟、Sabar、Permali Wallace、Transvick、Enpay、常州英中）、CRGO 鐵芯（Amod）、套管（HSP→HSP US、Trench、MGC Moser Glaser、Onload Gears）全是私人公司或大集團子公司；唯一上市、邊緣大小的是**江蘇神馬電力（603530.SS，市值 2.36B、分析師量不到）**——複合空心絕緣子直接出貨 Siemens Energy Grid Technologies、Hitachi Energy USA（Mt Pleasant），年報自述與 Hitachi Energy、Siemens Energy、GE Vernova「形成了扎实的合作基础」、2025 海外新簽訂單 10.12 億元（+36.40%）。四維初判客戶端資本承諾無、瓶頸地位未知 → 不打包，登記 `lead_c461550b4e3297ae7285479bd1772796` 誠實停放（awaiting_named_disclosure，觸發 co:hitachi 文件與神馬 Q3／年報）。
  - 2026-10-18（第二段）｜乾式變壓器讀圖換版 `sr_cfed15e6eb35a726`（判讀 undecided 不變）：補 Hammond 2026-09-22 新聞稿——Fort Worth 新廠 2027 Q4 起分段投產、初期約 CAD 2.5 億年產能（產能計畫是時變數字，只寫在讀圖）；Hammond 敘事換騎。
  - 2026-10-18（第三段）｜[788] go＋入圖後：分接開關讀圖 `sr_e785dae2f2565756`（volume 不變），**更正上一版「華明不在美國這條線上」**——美國海關提單顯示華明直接出貨 OLTC 給 Prolec GE 的兩個美國據點（樣本 2026-05～09，總筆數 255、2006 年起）；錯在把國家實驗室訪談沒提到中國讀成美國沒有中國貨源（L11-5）。層說明 v2 `ln_1614e38d9e1bc5c0`（T5 換成「美國這條線斷了」才觸發的新主張、份額補 F&S：華明 17.9% 第二、前三家 82.5%）；華明敘事 `ib_91bdb2db3f24de2a`（「缺」不變，缺的①改成「量在加速的一手」）。
  - 2026-10-18（第四段）｜公開文件追源：美國海關紀錄彙整（ImportYeti）華明給 Prolec GE 近四季 2／4／2／8 筆、第二個美國收貨人 Georgia Transformer（Virginia Transformer，品名 Tap Changer，零星）；DART：HD 現代電氣 2025 年報第一次把 MR 列為電裝品主要買進對象（沒寫品項）、曉星只揭露鋼板與銅——分接開關讀圖 `sr_c12929ba0fe07ae5`（volume 不變）、華明敘事換版（缺不變，筆數序列寫清楚能說明與不能說明的）。
  - 2026-10-19｜使用者同意鑄號後同意：[810] 名冊加 Shanghai Huaming Power（H 股申請書釋義的全資子公司）→ [811] 入圖 `co:huaming supplies_to co:virginia_transformer`（美國海關提單 ON LOAD TAP CHANGER→GEORGIA TRANSFORMER CORPORATION，2024-06-06；[809] 別名）；我自己寫的 claim 把季別寫成月份（2024-08 原文沒有）→ 更正包 [814] 待核准（failure log #85）。層說明 v3 `ln_9cd5959ee169e979`：韓國客戶端（HD 現代電氣 2025 年報第一次列 MR、華明不在）、Prolec GE 近四季 2／4／2／8 筆、新增主張 T6。
  - 2026-10-19｜分接開關讀圖 `sr_7bee958cc9d81d73`（VTC 由圖外改圖上、韓國客戶端）、華明敘事換版（連結改指層說明 v4）。
  - 2026-10-19（核准後）｜[814] 更正入圖：[811] claim 改成季別（季初 2024-04、07、10、2026-04 各 1 筆）。
  - 2026-10-20｜分接開關讀圖 `sr_de2bb0babc93f7b5`：更正「美國限制還沒讀到一手」——白宮行政命令 14421（2026-08-26）授權能源部逐筆禁止受管外國實體（含中國）的大電力系統設備與關鍵零件；沒點名分接開關、實施規則 12-24 前才出 → 主 session 判反證③（ew_1115、ew_1121）不觸發；華明換騎 `ib_5da1949ec73110da`、日期等待 `ew_1339_2026-10-20`（12-24 叫醒華明敘事）。
- failure log：（尚無）
  - #9（同 P1）
  - #10（[691] 合資股東的新聞稿被分類成外部印證；與 C1 [690] 同形）
  - #17（[699] 的圖影響行把整份更正文件當成增量）
  - #47（10-05 用 grep 判定 DOE「沒寫」套管瓷件那句，實際是 PDF 文字層拆字——撤回了一個對的說法）

## P3 800VDC 擱置五則回看

- 登記：registration §2 P3（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜（給 7.4 的指向，不是裁決）NVIDIA 部落格「NVIDIA, Partners Drive Next-Gen Efficient Gigawatt AI Factories in Buildup for Vera Rubin」（blogs.nvidia.com，2025 OCP）逐字列 800 VDC 夥伴——silicon：ADI、AOS、EPC、Infineon、Innoscience、MPS、Navitas、onsemi、Power Integrations、Renesas、Richtek、ROHM、STMicroelectronics、Texas Instruments；power system components：BizLink、Delta、Flex、GE Vernova、Lead Wealth、LITEON、Megmeet；data center power systems：ABB、Eaton、GE Vernova、Heron Power、Hitachi Energy、Mitsubishi Electric、Schneider Electric、Siemens、Vertiv。是客戶端（平台方）的生態名單——對五則的 park 理由（例：「ecosystem membership is not a supply contract」）正好是那個理由描述的東西，回看時要分清「名單」與「供貨」
  - 2026-10-05｜（給 7.4 的指向，不是裁決）題材掃描 lead_b050a3ee（台達 2026-09-29 PR Newswire：800 VDC In-Row Power「for the fast deployment and scalability of AI data centers based on
    NVIDIA Vera Rubin architecture」、keynote 談「Delta Electronics' collaboration with NVIDIA and the roadmap for 800VDC power architecture」）→ park（`original_obtained`，觸發欄寫「無」）：
    供應商自報的產品發表與合作字樣，**不補 lead_fa672a29 的缺口**（supplier relationship not proven）；台達 2025 年報同樣只寫已發展 19 吋 90kW DC/DC 機架式電源
    （800VDC 降 50／48VDC）與列間 1MW 800VDC 電源系統，沒有具名客戶。PR 的散熱段轉給 C1（[697]）
- 逐則（park 理由今天站不站得住；H2 的「證實」定義）：（尚無）
  - 2026-10-17｜**Wave 2 回看**（唯讀研究 workflow wf_59646a4e-958（9 位）＋走圖判定 wf_c1f5a527-bef；寫入由主 session）——嚴格照 H2「證實＝之後的一手補上 park 理由缺的那一樣」：
    ①VRM（lead_18be6b77；「named-supplier role remains unproven」）→ **未證實，理由仍成立**：NVIDIA 800 VDC 技術部落格 dateModified 2026-01-14 名單沒更新；OCP 2026 部落格沒點名任何 VRM 廠；光寶只自述有 VRM 產品線；「MPS 拿約 70%」只是分析師轉述。
    ②BBU／超級電容（lead_3e0ba028；「wait for named product or supplier disclosure」）→ **理由字面不成立、仍未證實**：具名產品已出現（台達 PR 2026-10-15「a 4RU 80 kW battery backup unit (BBU)」、光寶 PR 2026-10-15「a 108kW Capacitor Backup Unit (CBU)」），都是供應商自報；誰供貨沒有客戶端一手。
    ③整流與 busway（lead_4c2881be；「ecosystem membership is not a supply contract」）→ **未證實（邊界）**：客戶端 Visionbay 2026-09-16「has begun designing K-1 … alongside … Vertiv 800 VDC power distribution systems」、NVIDIA 2026-10-12 部落格同述——客戶端具名，但是**設計選用**，不是 park 理由缺的**供貨合約**。⚠ **判準在此定一次**：設計選用不算 H2 的證實（之後 X2、P3 照同一條用）。Vertiv 非邊緣、不在名冊。
    ④GaN／SiC（lead_a4c2e143；「beneficiary ranking would be inference」）→ **未證實，理由仍成立**：Navitas 24kW 800V-to-12V PDB 是與 NVIDIA 的合作（轉載）、Claros 是供應商併購；Navitas 8-K 2026-08-25「short - to mid - term (2027/2028) financial model remain unchanged」；POWI、AOS、Innoscience 09-03 之後沒有訂單或 design win。
    ⑤DC/DC power shelf（lead_fa672a29；「supplier relationship not proven」）→ **未證實，理由仍成立**：台達 90 kW、光寶 95 kW shelf 都是自報展示；「±400VDC及800VDC系統均陸續出貨…2026年相關產品整體規模有限」只見工商時報轉述。
    **H2 合併**：P3 嚴格 0/5（含邊界也只有 1/5），X2 1/36，證實數 < 4 → H2 維持「不足」。**世界動了什麼**：從「名單」往「產品與設計選用」動了一格，不是量產訂單；一手與轉述都把 800V 放量放在 2027。**SST（題材掃描 lead_3b9966f3，同日）**：一手只有設計採用——Infineon PR 2026-09-29「will deliver silicon carbide (SiC) power devices to Eaton … MVSST 2.0」（未來式）、Wolfspeed→私人新創 Amperesand（3.3 kV WolfPACK）、Eaton 8-K 收購 Resilient Power Systems；台達「年底 100 台」含送樣、放量年由「最慢 2027」滑到「2028」（皆轉述）；SST 製造商至少 3 家、SiC 至少 2 家，**不是薄層**，邊緣的只有 Wolfspeed（一家私人客戶、「會死嗎」先亮燈）——不開新層，停放等台達 Q3 法說的實際台數。
    ⚠ **機制缺陷（failure log #69）**：五則 09-03 停成 `original_obtained`，理由句卻是在等具名揭露——沒有觸發、沒有 watch。當下修：un-park 後改停 `awaiting_named_disclosure`、各掛 ew_0744–0748（到期 2027-02-14）。
  - 2026-10-19｜（AMEC 追線順帶）Magnachip 8-K 2026-09-21 EX-99.1：授權 Navitas GeneSiC 平面式 SiC（1,200V–3,300V+）在南韓廠 port／qualify／internalize，Navitas 投資 Magnachip——給 800VDC 回看的輸入，庫裡尚無紀錄。
- failure log：（尚無）
  - #69（停放分類把「等待」與「結案」混在 original_obtained）

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
  - 2026-10-07｜使用者 go **[719]**（`00620dd2`）、**[721]**（`2f9cc269`）入圖；快接頭層換版 `sr_cb1c40dda3dfe779`（neither 不變，供給側 2 → 6）；板式熱交換器第一份讀圖 `sr_c9f76761751db6e3`（volume；層說明 H1–H3 登成讀圖反證）；**CDU 層 undecided → neither**（`sr_015aca2693d7ebfc`：客戶規格開放給任何 CDU 廠、OCP 8 家照做，卡的在下一層——F48）。高力敘事 `ib_653dc98f04d1be26`（缺 不變；兩句判讀措辭跟著改）、富世達 `ib_838820aaeaaba244`（重新連結）。[722] 改寫時查到三則**轉述**：高力板式熱交換器切入美系 CSP（MoneyDJ 2026-04-09 轉述公司、鉅亨 06-17 港系外資、經濟日報 06-22 本國投顧）——H4 加碼條件要一手，未觸發；已寫進層說明。
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
  - 2026-10-07｜續工 ③（晚段）：**冷板 `sr_4d0e1386fed45cec`、分歧管 `sr_62439eac8d9c7edd` 重讀**（取代 `sr_7d2a979f43e3fc92`、`sr_baee167c3dfb3b71`；仍 undecided——上一版沒有登記任何條件、不會自己醒〔INV-2〕；各登兩個條件 watch：買方或廠商一手寫出該零件本身的交期／配額／預付 → 量；某世代平台只有一兩家合格 → 護城河）。對倍率：冷板層圖上 4 家都是非邊緣大廠或私人（台達、奇鋐、健策、CoolIT），邊緣大小的台廠雙鴻（3324）不在圖上、沒有任何 lead → directed lead `lead_d9c78bb0aff0b8a882d925766c309410`（triaged_go，層深讀入口）——「沒讀」不寫成「沒有可投資的公司」；分歧管層的邊緣公司只有高力，它的倍率要靠 CDU 與板式熱交換器的位置。高力敘事改押新分歧管讀圖 `ib_2b74e3b9fd70ec80`（文字與候選狀態不變）
- 裁決：（尚無）
- 2×2：尚未到裁決點
  - 2026-10-07｜續工 ①（/phase-run）：**冷板層說明 v1 `ln_4211fda64a785417`**（個股頁 S4 第六份；主張 K1 Vera Rubin 四家、K2 MCL／MCCP 登 watch）→ 冷板讀圖換版 **`sr_c2cae5b7616559ec`（undecided → neither）**：DigiTimes 導言寫 NVIDIA「will centralize procurement of cold plates and, at GTC, named four suppliers」（奇鋐、Cooler Master、健策、台達；媒體，NVIDIA 自己的新聞稿與技術文沒點名）——客戶自己點名四家、跨世代換人＝不是換不掉；沒有買方說缺＝不是量。directed lead 的答案：雙鴻（3324）是冷板、分歧管、CDU 的量產供應商（年報自述，伺服器營收 2026Q2 占 78%、客戶只寫代號），但分析師 16 家、**系統口徑非倍率**，而且不在 Vera Rubin 的四家 → 入圖包 pq2 **[732]**（三條供貨邊，名冊隨包 staged）；邊緣大小的力致、泰碩、建準年報只寫到開發或佈局。**這一層沒有可投資的邊緣公司**（failure log #43：上一版把雙鴻寫成邊緣大小是目測）
  - 2026-10-18｜盤點清單：板式熱交換器層第三家供應商 → pq2 **[794]**（Dover FY2025 10-K「brazed plate heat exchangers … including an increasing opportunity in data center cooling applications」；Q2 10-Q 資料中心冷卻熱交換器需求加速、分部訂單年增 45.8%「including longer lead-time orders」、book-to-bill 1.23）——讀圖原本只引 Dover 法說轉錄的「交期拉長」，換成它自己的申報書面版本。
  - 2026-10-18｜wfC：「NVIDIA 在 GTC 點名 Vera Rubin 冷板四家」查無 NVIDIA 一手（DigiTimes 圖說像現場展示）；冷板讀圖 `sr_10c0ba5b1caa04bf` 的「換得掉」改靠供給側五家量產、分歧管讀圖 `sr_47059f62582b16c2` 缺口②結案（NVIDIA 只確認 VR 機櫃有 tray 分歧管、由 MGX 生態製造、不具名）。
  - 2026-10-18（第二段）｜[794] go＋入圖後：板式熱交換器讀圖 `sr_ed36a21f43f0ab2e`（volume 不變）——Dover 的邊入圖讓供給側 2→3，但它本來就算在圖外、可補產能沒增加；10-Q 的「longer lead-time orders」把量的訊號從法說推進到法定申報（仍是供應商自述、分部合計）；反證新增④（Dover 連兩季不再提熱交換器訂單且訂單出貨比跌破 1）。
  - 2026-10-18（第三段）｜公開文件追源：沒有任何 CDU 廠點名高力（規格書本來就不寫熱交換器品牌）；高力 2025 年報 SMC（AI 伺服器）占比三處數字對不上（之前寫的 40.26% 是錯讀）——板式熱交換器讀圖 `sr_1f99a7bd1f5fbf52`、高力敘事換版（缺不變）；層說明的同一處錯讀待改。
  - 2026-10-19｜板式熱交換器層說明 v2 `ln_de7867429c3c4ab9` 更正 SMC 錯讀（年報三處對不上，三到四成）；富世達 lead 停 partial（擴產 450／600 萬只見媒體，等 11-04 前後 Q3 法說）——UQD v2.0.0 定稿（2026-09-22 生效、§10 至少與 3 家交叉驗證）與 NVIDIA MQD／MQDB 開放的一手見讀圖換版。
  - 2026-10-19｜快接頭讀圖 `sr_988b390273595704`（neither 不變；UQD 草案／定稿分開、Rubin 的 UQD08 與 MQD／MQDB）、富世達與英維克敘事換版。
  - 2026-10-19（券商報告）｜[722] 券商報告讀完：高力板式熱交換器的新客戶、出貨時程與某液冷客戶放緩，全是券商稱（tier 2）（券商內容私有：library/private/research_notes/doc_requests/）；高力敘事 `ib_7f9c1e375a59db6b`、板式熱交換器讀圖 `sr_3ae141cc5c4257e9`、層說明 v3 `ln_1141930c2307e617`；缺 X 照舊等 11-14 財報。
  - 2026-10-20｜高力一手核完：MOPS 月營收說明只寫兩類產品年增（券商說的客戶放緩對不到一手）；會計師查核附註定案客戶集中 SMC 40.26%、Bloom 31.27%（年報中文表印反）；Bloom 端只有春暉智控深交所問詢回覆點名「台湾高力」→ 不出 RA：Bloom 非邊緣、圖上沒有燃料電池／現場發電層（decompose 選題，待使用者決定）。高力 `ib_e062d42bc4716cfa`、板式熱交換器讀圖 `sr_dc4c28519ee17080`、層說明 v4 `ln_1d68c522c39ddb41`。
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
  - 2026-10-07｜AI 生醫研究題全部到終局：AIDD 這條沒有 power-law 的邊緣候選；唯一緊的是中國實驗猴，但需求的一手歸因是創新藥授權、不是 AI。日期等待：ew_0316（FDA 單抗指引定稿，2027-03-31）、ew_0317（BIOSECURE 名單，2026-12-31）、ew_0318（AI 新藥需求端，2026-11-30）。
  - 2026-10-07｜延伸題材：使用者「B ok」→ pq2 **[726]**（受理即 resolve）中國創新藥授權 → 臨床前毒理 → 實驗猴 decompose（`library/private/research_notes/decompose/cn_licensing_nhp_2026-10-07.md`，7 層全不在圖）；7 題當天到終局（`…/2026-10-07_pq1_cnbio_q3a_innostar.md`、`…_cnbio_theme_closeout.md`）：益諾思是買猴的人（一手否定「成本法藏猴資產」）、昭衍公允價值入帳且猴資產約占市值 6%、純做猴的天勤生物（深交所審核中）與鼎泰藥研（港股第二次遞表）未上市——**上市公司層沒有候選**；掛 ew_0319（兩家掛牌，2027-03-31，T2 輪詢）。
  - 2026-10-17｜**更正**（上面那句保留不刪）：「天勤生物（深交所審核中）」是錯的——深交所、上交所 API 用「天勤」「湖北天勤」「天勤生物」都查無；**中信證券 2026-08-13 公告終止對湖北天勤生物的輔導**（「因公司战略调整原因」）；港交所在審名單（2026-10-17）也沒有。當時依據搜尋摘要、沒開詳情頁（L11-3、L11-5）。鼎泰藥研（TriApex）港交所狀態 A、只有 2026-06-15 的第一次申請版本，約 2026-12-15 失效。**「上市公司層沒有候選」不變，唯一的潛在入口只剩鼎泰。**另兩件同日一手：①商務部、科技部公告 2026 年第 48 號（10-16，徵求意見到 11-15）修訂禁限出口技術目錄——生物醫藥只列 CGT／siRNA 技術工藝平台與病原微生物功能增強，「对外授权许可、利用相关技术工艺提供外包研发和生产服务等……不属于管理范围」，**碰不到抗體／ADC 授權這條鏈頭**（lead_f12babb1）；②昭衍 2026-05-19 業績說明會「目前行业内食蟹猴供应仍然偏紧」但「国内猴子进口政策出现松动迹象」——供給側的反向訊號，政策原文未找到；新浪那則「24 萬」是財經博主一句「据悉」，「三省訂完」是 07-13 記者電訪被雷達併成同一條 10 月事實（lead_268ffc9e，failure log #70）。

## G1 IC 載板上游：低膨脹玻纖布（T-glass）

- 登記：registration「更正與追加」2026-10-07 G1（開題 2026-10-07）
- 研究產出：
  - 2026-10-07｜入圖包 pq2 **[733]**（`ra_5dc9439157d8eb9d1b13a9f9d16558b5`；directed lead `lead_2d4195f84bee1e416fb7b1be5297bfaf`）：新節點 `mat:ic_substrate_glass_cloth`＋4 條邊——日東紡 supplies_to（2026-08-05 說明資料與主要質疑応答：T ガラス需求「引き続き非常に強い」、增強到 2028、在漲價、承認客戶在評估別家）、玻纖布 is_component_of IC 載板（日東紡用途表：CPU/GPU/ASIC 要低 CTE，高階 T）、景碩 constrained_by 玻纖布（買方年報：2H25 起玻纖布缺料、2026 持續、要找新供應商）、景碩 supplies_to IC 載板；名冊隨包 staged 日東紡、景碩
  - 2026-10-07｜層說明草稿 v0（`library/private/research_notes/layer_notes/mat_ic_substrate_glass_cloth.md`，入圖後寫進 ledger；主張 T1–T4）；向你要文件 pq2 **[734]**（T-glass 供需缺口、份額、第二來源認證）
  - 日東紡用系統口徑是邊緣（市值約 6,690 億日圓、分析師 9 家），FY2026 營業利益預估 300 億日圓裡 280 億是電子材料——入圖後寫第一份敘事前，要先定本鏈的主題等權組（走 pq2）
  - 2026-10-07｜使用者 go [733] → 入圖（名冊 6a5f3a52、intake 69372708）；玻纖布層第一份讀圖 `sr_49dcdbd60da7b239`（**volume**；反證 2 條＋客戶端重讀 1 條登 watch）；IC 載板層重讀 `sr_312353108b9975b5`（volume，供給側加景碩）；層說明 ledger `ln_3552bc3a00c18c0d`（T3、T4 登 watch；T1、T2 由讀圖條件盯）
  - 2026-10-08｜`python -m alpha edge 3110.T`（A6）＝邊緣（42.3 億美元、9 家；yfinance 補值，逐欄標來源）——#43 的目測換成系統判定
  - 2026-10-08｜本鏈主題等權組 pq2 **[736]**（「AI 封裝載板與上游材料」6 檔：ATS.VI、Ibiden、欣興、景碩、南電、日東紡；Ibiden、欣興、南電三筆名冊隨號 staged）——**鑄在日東紡第一份敘事之前**（failure log #26 的教訓）；日東紡敘事排在 [736] 落地之後
  - 2026-10-08｜旁證：T4 反向路徑（玻璃核心載板）上的 LPKF（LPK.DE，TGV／LIDE 雷射；X 帳號 3 則 lead 07-27 起）在名冊批次 [737] 裡——登記後玻璃核心的新聞才對得上公司
  - 2026-10-08｜使用者 go [736] → 主題等權組 `tc_5061f2233f77a865` 落地（Ibiden、欣興、南電隨號登記）→ **日東紡第一份 v2 敘事 `ib_c8f278b954e90d5d`（缺）**：
    押玻纖布層 `sr_49dcdbd60da7b239`（量）；X＝①T-glass 份額與第二來源在高階載板的認證（[734] 向你要文件）②已定價主參照（日本申報人沒有自家歷史）；
    反證連讀圖兩條與層說明 T4（玻璃核心）；等待 `ew_0436` 在 11-10（第 2 季決算說明會後）叫醒。順序符合 #26 的教訓：對照組先、敘事後
- 裁決：（尚未到裁決點；日東紡 2026 年度第 2 季決算說明會 2026-11 上旬）
  - 2026-10-18｜wfC：Ibiden（載板廠，客戶端）Q&A 說玻纖布供應商由日台兩家擴到可望第三、四家、採購風險在降（反證②部分觸及）；玻璃芯是真反向路徑但時鐘在 2027 下半以後、三星電機同時把最大投資押在有機 FCBGA 到 2028——T-glass 讀圖換版 `sr_0d8d2afdea2d7172`（volume 不變、窗口再短），日東紡敘事更正，入圖包 pq2 [800]。
  - 2026-10-18（第二段）｜[800] go＋入圖後：T 布讀圖 `sr_6784a1f8ca5a9aee`、IC 載板讀圖 `sr_bdf526a7db003e99` 換版（都 volume 不變）；載板層補三星電機世宗 2028-09 才量產、越南 2030-06 前營運（同一份新聞稿的圖外原句），反證③到期延到 2028-12-31。
  - 2026-10-18｜[799] go＋入圖後（同族的另一鏈：高速 PCB 材料）：高速 CCL `sr_d15a83b63718e79f`（neither：這一層厚、排隊的是裡面的料；daily lead「CCL 交期 6 個月以上」查無一手；TTM 年報寫 CCL「generally readily available」）、HVLP 銅箔 `sr_007e68bb6d9ca403`（volume，薄的是 HVLP4 以上：台燿寫瓶頸、滬電寫優先配額、三井一年兩次漲價）、PCB 用 Low-Dk 布 `sr_ff00dd2a40d7715a`（volume，只押 Low Dk2）——Low-Dk 布層跟本層是同一批公司與熔爐（日東紡、台玻、富喬、建榮），兩層一起緊也可能一起鬆。新鏈主題組 pq2 [801]（8 檔等權）——金居、三井金屬、富喬的第一份敘事等它 go；台玻排除在組外（營收六成平板玻璃）。名冊批次 [796] 的 TTMI 短檢查③：在高速 CCL 需求側（PCB 廠）。台玻第一份敘事 `ib_5a22d69af8f2d5d7`（缺 X：台光電、台燿、台玻三份 2025 年報的進銷貨段都讀過、都沒有點名台玻——向你要文件 [804]；第二代布占營收無法量）。[801] go 後：金居 `ib_c50158c6c28beca4`（缺 X：HVLP4 以上三井自估份額六到八成、低等級已有新競爭者——金居的成長可能大半不在薄的那一級；[805]）、富喬 `ib_11c5d910826ae3c8`（缺 X：它自己寫第二代紗「逐漸難以滿足新世代應用需求」、年報預估 2026 各產品線銷量低於 2025、自家三年第 98.5 百分位——補齊也多半落在等回落或不要；[806]）、三井金屬 `ib_291b5c2e3b96f04f`（不要：曝險太薄；MicroThin 那一層圖上沒有，已登記走圖洞線索）。
  - 2026-10-18（第三段）｜公開文件追源：TPCA×工研院 2026-05-06（2025 全球 HVLP 產能 2.34 萬噸、日系逾六成、金居 10.3%；37／16／10 只見於金居年報）、古河 QA（HVLP4 日本為主但韓台在追）、三井 2026-08-17（2031 年後 VSP 合計 2,600 噸／月）——HVLP 讀圖 `sr_3034eea415df3712`（volume 不變）、金居與三井敘事換版；台玻擴產一手（紗場 22.5 億、窯爐改建 47 億、增建冷修 22.42 億；2026 高階布供貨 +40–50%）與 2026Q2 玻纖部門營收已超過平板玻璃——Low-Dk 布讀圖 `sr_70e62330234aaf30`、台玻敘事換版、富喬換騎。
  - 2026-10-19｜台玻進 PCB 組 v2（[807]）後敘事更正 `ib_e5a7eca4a3519ae8`（已定價改引組中位數）；HVLP 讀圖 `sr_09a0f817a34a4a64` 反證④補古河（[808]）、金居與三井換騎；入圖包待核准：[813] 京東方 develops 玻璃芯（onboard；一手 IR 記錄表——測試是廠內做的、2027 上半年達量產投資決策條件）、[816] 極薄載體銅箔層（新節點；三井 MicroThin 主導有競爭者法定文件印證，「只有三井」被德福 C-IC2、方邦可剝銅、CFL DoubleThin 否定；onboard 德福〔邊緣〕、方邦〔邊緣無法量〕、CFL〔私人〕）、[812] GF–TSMC 中介層協議更正（副標題「Multi-year $2 billion」當初漏讀，failure log #84）。
  - 2026-10-19（核准後）｜[813] 京東方、[816] 極薄載體銅箔層、[812] GF 金額更正入圖；極薄載體銅箔層第一份讀圖判 moat `sr_6aca83ddbb6d63d1`；德福、方邦第一份敘事（缺 X）、三井加騎；IC 載板 `sr_046781b61f68dff3` 與 IC 載板玻纖布 `sr_cd14412c16fc279b` 補京東方；[820] 向你要德福文件。
  - 2026-10-19（券商報告）｜[804][806] 券商轉載的聯茂產品線表（10-20 由聯茂一手對上）——Low-Dk 布讀圖 `sr_ef4ce6b4ac4b7345`、台玻 `ib_28920bc567830056`、富喬換版；[805] 券商對金居 HVLP4 份額與 HVLP3/4 產能的估計（券商內容私有：library/private/research_notes/doc_requests/）——HVLP 讀圖 `sr_dc5f1d9865eda833`、金居 `ib_2af852aa24e6760d`（撤回敘事自己「10% 多半高估」的推一步）、三井換騎。
  - 2026-10-20｜CCL 一手：聯茂官網 IT-999GSE2「uses Low Dk2 glass」、IT-999GSE3「uses Q glass」（券商轉載的產品線表在聯茂對上）；台燿 TU-953Q 規格書沒寫布種、台光電 EM-896K3 只有廣告——券商說兩家都改用 Q 布，對這兩家仍是券商稱；Trainium3 升 HVLP4（SemiAnalysis）但供應商沒人點名 → 入圖包 [823]（新節點石英布＋is_component_of 高速 CCL＋competes_with Low-Dk 布）、[826]（onboard 菲利華、聯茂）。Low-Dk 布讀圖 `sr_4c65b28f5fedb95c`、HVLP `sr_a06e3595d99cb164`（都 volume 不變）、台玻 `ib_fece8543d4c2ef9f`、富喬 `ib_b558cc4eda361a5f`、金居 `ib_368c5f2791000f13`。
  - 2026-10-20｜YMT（韓）四維初判不過、維持 park（含極薄箔那一列最多約占營收 5%、需求錨只到 mSAP）；極薄載體銅箔讀圖第三版 `sr_431d7f58b2bcd6ac`（更正「2023 年之後還往下走」——2026 上半年已超過 2025 全年）、三井 `ib_5f43db606ef74b6f`（瓶頸格措辭）、德福與方邦換騎。
  - 2026-10-20（核准後）｜石英布第一份讀圖 `sr_037ce5e723690b34`（undecided：聯茂同級兩版並列、台燿年報把 Q glass 列進瓶頸料；供給側只有菲利華自述在認證）；Low-Dk 布 `sr_3ac9c21d8aa96ffd`（volume 不變；反證③「石英布成主流」判沒觸發——並列不是主流）；高速 CCL `sr_de14c044019dea62`（neither 不變、補第 5 條反證盯聯茂）。聯茂 6213.TW 第一份敘事 `ib_1d60d81e43b11639`「不要」（寡占厚層裡的大廠、這一輪營收翻倍第一個原因是漲價）；菲利華 300395.SZ `ib_115d2ed83e352547`「缺 X」（石英布約占營收 11.7%、做布的子公司只持股 48.11%；11-01 叫醒 `ew_1414_2026-10-20`）；台玻、富喬換騎並改措辭；PCB 組 v3 加聯茂 → pq2 [832]。
- failure log：
  - #43（名冊外的公司判不了邊緣——本 case 的日東紡、台玻、建榮也是目測）、#44（09-29 研究結論寫了「可能的薄層在上游」卻沒變成 lead）

## X1 已定價回放（R1）

- 登記：registration §2 X1、§7.2
- 報告：（尚無；`replay-r1-priced.md`）
  - 2026-10-05｜[`replay-r1-priced.md`](replay-r1-priced.md)：31 列 × 4 個時點＝124 格，有值 **10** 格（PIT 違規 0：每格用到的最晚申報日都 ≤ 時點）；**H9 判讀線：history 子群「不足」、只在組裡的 9 檔「不足」**（每組湊不到 n ≥ 4；錨點那格 history 高 5、低 1）。缺席分型：非 SEC 40、三年窗不滿 34（Engine C 價格 2023-08-31 起，時點早於約 07-31 量不到）、台股 20、20-F 16、EV/S 缺 4。**之後曾達 2 倍的 21 格（18 檔）在那個時點全部「未量」**——「已定價有沒有把贏家說服走」現有資料回答不了（不足 ≠ 否定）
  - 2026-10-07｜（旁證，不進 H9 判讀線）個股頁 schema 負錨點時光機頁（`docs/brainstorms/2026-10-05-stock-page-schema.md` §15；Phase 7 偏差 #24）：負錨點兩檔 T 當天自家三年股價營收比百分位 **99、100**（合晶 2021-11-30、矽創 2021-07-30，之後一年 −42%、−46%），贏家三檔 2025-06-30 **27、83、31**；五張頁都是看結果挑的、兩組時代不同——要量只能預先登記後在 H12 事件全集上測（新假說候選，待使用者決定登不登記）。R1 照舊、H9 照舊「不足」
  - 2026-10-07｜（旁證，不進 H9 判讀線）使用者 go（pq2 [731]）→ **H13** 在 H12 的 2015–2022 事件全集上測（登記 commit 8d8043df 早於計算）：**削弱**——量的拐點裡價在自家三年頂端＋毛利在前高的那組（n＝123）6 個月內先跌 30% 較多（14.6% 對 8.7%），但 12 個月內曾達 2 倍也較多（16.3% 對 8.4%）；只看價：先跌 18.1% 對 7.1%、曾達 2 倍 13.8% 對 9.0%、超額中位數 −11.9% 對 −3.4%——自家三年百分位在頂端量到的是兩邊尾巴都肥，不是方向（`replay-h13-priced-margin-top.md`）。H9 照舊「不足」
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
  - 2026-10-07｜續工 ④（晚段）：**Silex SILEX.ST 第一份敘事 `ib_d5144057cac442c4`（缺 X）**——押鏡陣列層 `sr_87952c233a4e591b`；讀 2026 Q2 季報（2026-07-17）：電信終端市場（含光學交換器）R12 4.62 億克朗、約占 15.1 億的三成，OCS 本身不揭露；CEO 段「optical switches in data centers」客戶興趣特別強、買美國廠是為了「get closer to our largest customers」。X＝①客戶端或第三方點名 OCS 的 MEMS 代工 ②OCS 營收占比 ③已定價主參照（瑞典申報人、上市五個月）；等待 `ew_0376`（11-05，Q3 季報 11-04）、連結讀圖反證 `ew_0194`、`ew_0195`、加碼條件 1
  - 2026-10-07｜Silex「缺 X」①的一手補查：Lumentum FY2026 10-K（2026-08-17）——OCS「contributed more than $90.0 million of revenue during fiscal year 2026」、需求「outpacing our current supply」要做供給分配；**全文「MEMS」0 次**，OCS 鏡陣列自製或外包沒有揭露（`library/raw/lite_10_k_20260817_ocs_excerpt.txt`）。EDGAR 全文檢索「MEMS」＋「optical circuit」2025-06 起只有 Tower 的 6-K（它說的是矽光子 OCS，另一條技術路線、可能是鏡陣列層的反向路徑候選）。下一份 OCS 鏡陣列層說明的起點：客戶端點名多半不公開，可能要向使用者要券商的 OCS 供應鏈報告
- H2（X2 的部分）：**不足**（證實 1 < 4）；與 P3（7.4）合併判
  - 2026-10-07｜（旁證，不在 R2 固定樣本、不進判讀線）日東紡（T-glass）兩則 park：`lead_ffdc392c`（07-25，X 帳號「Nittobo / glass fiber/cloth」）、`lead_d8fee64e`（09-04，「Nittobo T-Glass」）；09-29 `lead_9a65a3ce` 的研究結論寫「可能的薄層在上游（玻纖布、ABF 膜），目前未驗證」卻沒變成 lead——10-07 是走圖「下一層 0 條」把它撿回來（case G1、pq2 [733]；failure log #44）。價格：收盤 07-24 3,195 → 10-06 3,640 日圓（分割後，約 +14%）；52 週那次 1,412 → 6,580 的大漲大跌在第一次接觸之前
  - 2026-10-18｜公開文件追源：一手能證實已量產的 MEMS-OCS 代工只有 Silex（賽微 2023-12 公告、Silex IPO 說明書「proven at Google, others pilot」——客戶沒點名）；賽微北京到 2026-08 仍未量產；Lumentum R300 的晶圓在哪做沒有一手——MEMS 鏡陣列讀圖 `sr_a04f3136bf4d1bb1`（判不出不變，主缺口改成 Lumentum）、Silex 敘事換版；[765] 的公開那一半大半答了，券商報告仍要。
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
  - 2026-10-07｜pq1 drain 再撞到同形（brainstorm F51）：景碩、欣興、南電、Ibiden 52 週約 5–10 倍，10-05 的載板層讀圖供給側只列 AT&S、三星電機；四檔已由 [711] 追加進第二窗母體——7.5 照算，不另加。
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
  - 2026-10-18｜**盤點 B 組（人形量產客戶一手）**：pq2 **[793]**——宇樹招股意向書（2026-07-31）「公司实现机器人核心零部件关节模组的自研自产……降低了对外部供应 链的依赖」，生產環節含電機、減速器及關節模組，原材料「市场供应充足」、前五大供應商 22–26% 多匿名——量最大的人形廠不是外部致動器供應商的客戶；入圖後重讀致動器層 `sr_14456dc4d147f3f3` 的需求側。環動科技（雙環傳動分拆）招股書申報稿：客戶全匿名（主要客戶 1、2）、工業機器人為主、前五大 78.34%——無 graph delta。
  - 2026-10-18（第二段）｜[793] go＋入圖後：致動器層讀圖 `sr_90eff8f4a5dea998` 由 undecided 改判 neither——理由在需求側：量產中的宇樹自製關節模組、說原料供應充足，其餘三個買方各是互惠、集團內、未點名；產能那一半是結構推論（量還沒到），反證①盯的公司補上宇樹、Humanoid、Boston Dynamics；現代摩比斯、Schaeffler 敘事各改兩句（state 不變）。
- failure log：（尚無）
  - #14（反證以被評公司的供貨 assertion 形式入圖：MP 磁材邊上的 Noveon、USA Rare Earth 文件，引文沒有 MP）
  - #19（海外財報缺口：6324.T、LYC.AX、6680.HK 的已定價嗎與出現在數字裡都量不到）、#20（A＋H 檔快照市值只算 H 股）

## Q3W Q3 財報季窗內名單（Step 7.3 中迴路；amendment A8，2026-10-21 凍結）

- 登記：plan §0.4 A8（使用者 2026-10-21 `A7-A12 go`）；ROADMAP Phase 7 驗收⑤。**名單 commit 後不改**；更正只在本段尾 append（日期、改什麼、為什麼）。
  凍結的版本只管⑤（財報後新版或不換版理由）；O1、O2 等 7.0a 已登記 case 的 2×2 仍用登記那一版（registration §0 第 4 條）。
- 窗：2026-10-21～2026-11-30（含兩端）。
- 凍結時點：ledger 與 registry 讀於 2026-10-21 13:23（+08:00），commit 前同日主 session 重跑 `freeze.py` 名單逐列相同；敘事 ledger 最後一筆寫入 2026-10-20 22:56（+08:00）；候選板 artifact
  `generated_at` 2026-10-20T22:06:30Z（＝`candidate_state_series.jsonl` 的 2026-10-21 那一行）。兩邊一致：現行 v2 敘事 73；宣告缺 X 26、
  已定價等回落 3、不要 44；候選板已持有 2（COHR、SIVE.ST）。
- 規則（看任何 Q3 結果之前寫，機械）：
  1. 母體＝凍結時點每檔現行 v2 敘事（最新一筆、未撤回）中宣告 `missing`／`priced_wait` 的，加上候選板的已持有
     （`library/private/app/state/candidates.json` 的 `groups.held`，由 Sheet readonly 推導；本段沒有讀 Sheet）→ 30 份。
     板上側欄（邊緣無法量、非倍率候選）照宣告狀態算。
  2. 裁決點＝候選狀態那筆 watch 的 `until`；持股沒有候選 watch 的（COHR，宣告「不要」）＝它在窗內的第一份定期財報。
  3. 裁決點在窗內 → 名單（28）；不在 → 排除並寫理由（2）。
  4. 凍結後新寫或改判的敘事不追加；名單內的敘事若在財報前換版，⑤仍要一份**財報後**的新版或不換版理由。
  5. 非倍率公司（名單內的 COHR、側欄「非倍率候選」的 MP；名單外的 LITE——2026-10-20 撤回、沒有現行敘事）的財報只當層的證據：
     寫進讀圖換版或本段，不做股價裁決。

### 名單（28；依裁決點排序；敘事 id 後括號是寫入日 UTC）

| # | ticker | 名稱 | 宣告狀態（板上分組） | 凍結的敘事 | 裁決點 | 來源 | 候選 watch（until） | 凍結時已觸發未檢 |
|---|---|---|---|---|---|---|---|---|
| 1 | 002428.SZ | 雲南鍺業 | 缺 X | `ib_141707402b3c5904`（10-19） | Q3 季報**已公告**（10-20 晚間；cninfo 披露日 10-21） | [b][c] | `ew_0684`（11-01） | — |
| 2 | 002270.SZ | 華明裝備 | 缺 X | `ib_5da1949ec73110da`（10-20） | Q3 季報 10-27（預約；法定 10-31） | [b] | `ew_0435`（10-31）；另 `ew_1339`（12-24，窗外） | — |
| 3 | 300395.SZ | 菲利華 | 缺 X | `ib_115d2ed83e352547`（10-20） | Q3 季報 10-27（預約） | [b] | `ew_1414`（11-01） | — |
| 4 | AXTI | AXT | 已定價等回落 | `ib_11a30b994d9658d7`（10-20） | Q3 財報與法說 10-29 盤後（13:30 PT＝台北 10-30 04:30）；10-Q 約 11 月中 | [a] | `ew_0148`（11-13）；另 `ew_1433`（10-31） | — |
| 5 | LYC.AX | Lynas | 缺 X | `ib_205494066a93e359`（10-17） | 9 月季季報 10-29 | [d] | `ew_0204`（11-03） | — |
| 6 | AEHR | Aehr Test Systems | 缺 X | `ib_56caa0a0838b432a`（10-20） | FY27 Q1 財報 11-02 盤後 | [e] | `ew_0636`（11-03） | `ew_1381`、`ew_1382`（加碼條件） |
| 7 | COHR | Coherent | 不要（非邊緣；板上已持有） | `ib_4233a575e88d7756`（10-20） | FY27 Q1 財報 11-04 盤後（敘事 when 的 12-01 產能檢核點在窗外） | [f] | —（不要，沒有候選 watch） | CW DFB 層 6 筆 |
| 8 | KSHINTL.NS | KSH International | 缺 X | `ib_63239e9aa6a0fe97`（10-17） | Q2 FY27 董事會核財報 11-04 | [g] | `ew_0770`（11-20） | — |
| 9 | SILEX.ST | Silex Microsystems | 缺 X | `ib_c0f560eed6ba7575`（10-20） | Q3 季報 11-04 | [h] | `ew_0376`（11-05） | — |
| 10 | 3110.T | 日東紡 | 缺 X | `ib_fa7246ba7b1720d4`（10-19） | 第 2 四半期決算發表 11-05 | [i] | `ew_0436`（11-10） | — |
| 11 | ATS.VI | AT&S | 缺 X | `ib_a1f52f8f289e7baa`（10-19） | 2026/27 半年報 11-05 | [j] | `ew_0242`（11-06） | — |
| 12 | MP | MP Materials | 缺 X（板上非倍率候選） | `ib_5fe12d2ae072b121`（10-20） | Q3 財報 11-05 盤後 | [k] | `ew_0203`（11-09） | — |
| 13 | USAR | USA Rare Earth | 缺 X | `ib_1344a7b770ec2cd9`（10-17） | Q3 10-Q 未定日（推論期限 11-09） | [l] | `ew_0257`（11-12） | — |
| 14 | 1802.TW | 台玻 | 缺 X | `ib_9e01b3c3839caac7`（10-20） | 10 月營收 11-10；Q3 財報 11-14 | [m] | `ew_0978`（11-16） | — |
| 15 | 1815.TWO | 富喬 | 缺 X | `ib_c6362220eca7e383`（10-20） | 同上 | [m] | `ew_0996`（11-16） | — |
| 16 | 2455.TW | 全新 | 缺 X | `ib_149da848892f4240`（10-20） | 同上 | [m] | `ew_0617`（11-14） | CW DFB 層 6 筆 |
| 17 | 3081.TWO | 聯亞 | 已定價等回落 | `ib_899f7c33036e91af`（10-19） | 同上 | [m] | `ew_0620`（11-14） | CW DFB 層 6 筆 |
| 18 | 3163.TWO | 波若威 | 缺 X（板上邊緣無法量） | `ib_809005cc91d199e7`（10-19） | 同上 | [m] | `ew_0371`（11-16） | — |
| 19 | 3234.TWO | 光環 | 缺 X（板上邊緣無法量） | `ib_6f2e71838ae8c328`（10-19） | 同上 | [m] | `ew_0985`（11-16） | CW DFB 層 6 筆 |
| 20 | 3363.TWO | 上詮 | 缺 X | `ib_269a5366ae7ad2b2`（10-19） | 同上 | [m] | `ew_0626`（11-14） | — |
| 21 | 4971.TWO | 英特磊 | 缺 X | `ib_199a6ef5fec4fde0`（10-19） | 同上 | [m] | `ew_0287`（11-16） | — |
| 22 | 4979.TWO | 華星光 | 已定價等回落 | `ib_268b1bed22dcf35f`（10-19） | 同上 | [m] | `ew_0629`（11-14） | CW DFB 層 6 筆 |
| 23 | 4991.TWO | 環宇-KY | 缺 X | `ib_3a006e2f3d922739`（10-19） | 同上 | [m] | `ew_0983`（11-16） | — |
| 24 | 8358.TWO | 金居 | 缺 X | `ib_d961530614c4690c`（10-20） | 同上 | [m] | `ew_0990`（11-16） | — |
| 25 | 8996.TW | 高力 | 缺 X | `ib_e062d42bc4716cfa`（10-19） | 同上 | [m] | `ew_0632`（11-14） | — |
| 26 | SOI.PA | Soitec | 缺 X | `ib_7c82a9ab254240cc`（10-17） | H1'27 業績 11-18 盤後 | [n] | `ew_0270`（11-19） | — |
| 27 | SIVE.ST | Sivers | 缺 X（板上已持有） | `ib_81fcd7087c1afe4c`（10-20） | Q3 季報 11-26 | [o] | `ew_0149`（11-26） | 15 筆（見下） |
| 28 | IQE.L | IQE | 缺 X | `ib_2e55ac7988833cdb`（10-17） | 窗內沒有排定的財報；裁決點＝候選 watch 叫醒日 11-30 | [p] | `ew_0249`（11-30） | — |

- CW DFB 層 6 筆＝讀圖 `sr_def7cb705477572e` 的 `ew_1101`、`ew_1102`、`ew_1103`、`ew_1105`、`ew_1107`、`ew_1108`（10-19／10-20 醒）。
  SIVE.ST 另 9 筆：thesis `sivers_v4` 的 `ew_0108`–`ew_0111`、`ew_1443`；讀圖 `sr_35ca0ce58617d5f6` 的 `ew_0139`、`ew_0141`（ENA.V 共用）；
  讀圖 `sr_470b3e4a5af4e5c3` 的 `ew_1075`、`ew_1077`。
- 第 1 列：Q3 季報在凍結之前已公開；被評的敘事寫於 10-19（UTC），早於文件，照規則 1–3 列入。
- 第 4 列：registration O1 與 `thesis/lifecycle.json#axt_inp.catalyst_checkpoints` 寫的 10-30 是估計（`date_confidence: estimated`）；
  公司 10-01 新聞稿定 10-29 盤後（PT）。不改登記，評估照實際日期。

### 排除（2；裁決點不在窗內）

| ticker | 名稱 | 宣告狀態 | 敘事 | 理由 |
|---|---|---|---|---|
| 301511.SZ | 德福科技 | 缺 X | `ib_2b118f6314f9dc06`（10-20） | 候選 watch `ew_1177` until 2027-04-30；敘事 when：「真正的裁決點是 2026 年報（法定期限 2027 年 4 月 30 日）」——窗內的 Q3 季報（cninfo 預約 10-30、變更為 10-27）只看整體毛利率 |
| 688020.SS | 方邦股份 | 缺 X（板上邊緣無法量） | `ib_29309d271eca27b1`（10-20） | 候選 watch `ew_1178` until 2027-04-30；敘事 when：「真正會裁決的是 2026 年年報」——窗內的 Q3 季報（cninfo 預約 10-30）「不會拆可剝銅」 |

不在母體：宣告「不要」且不是持股的 43 份；LITE 沒有現行敘事（最後一筆 `ib_ffe45711ead6b37c` 是 2026-10-20 的撤回紀錄）。

### 窗內的層證據財報（非倍率；⑤要寫進讀圖換版或本段）

| 公司 | 日期 | 來源 | 對應的層 |
|---|---|---|---|
| COHR（名單第 7 列，持股） | 11-04 盤後 | [f] | CW DFB 層 `sr_def7cb705477572e`；InP 基板層 `sr_e8cab2cad68816c0` 的需求側 |
| LITE（沒有現行敘事） | 11-05 盤後 | [q] | 同上兩層的需求側；另 `ew_0121`（`mat:inp_substrate`）、`ew_1110`（`tech:cw_dfb_laser`）兩筆讀圖喚醒已因 Lumentum 新文件醒、未檢 |

另：AAOI Q3 11-05 盤後 [r]——由 O4 段照 registration §2 O4 的裁決點處理，不進本名單（宣告「不要」）。

### 凍結時窗內要處置的 watch

- 已觸發未檢 21（`fired`：語意 19＋申報型 2）。名單內綁 17：CW DFB 層 6、SIVE.ST 另 9、AEHR 2。名單外 4：POET `ew_0173`（敘事反證）、
  9856.HK `ew_0833`（讀圖 `sr_62e2a48a354f407c`）、`ew_0121`、`ew_1110`（讀圖喚醒）。預篩標旗 14（likely_unrelated 10、cannot_tell 4）——標旗不是判定。
- `expires` 落在窗內 10：追源型 9（`ew_0041`、`ew_0454`、`ew_0471`、`ew_0475`、`ew_0479`、`ew_0487`、`ew_0507`、`ew_0526`、`ew_0541`；到期由 daily
  轉 lead 終局並計數）；敘事型 1：`ew_0656`（FORM 舊「缺」的等待，11-05 醒、11-20 到期；FORM 10-16 已改判不要——failure log #34 同形）。
- `until` 落在窗內（date 叫醒）46：名單的候選與附加等待 28（上表；AXTI 兩筆）；HPS-A.TO `ew_0593`（11-05；現行敘事是不要，#34 同形）；
  追源型 17（`ew_0318`、`ew_0440`、`ew_0443`、`ew_0461`、`ew_0465`、`ew_0470`、`ew_0515`、`ew_0519`、`ew_0531`、`ew_0533`、`ew_0539`、
  `ew_0544`、`ew_0552`、`ew_0558`、`ew_0566`、`ew_0568`、`ew_0740`）。

### 查證命令

- 名單版本：`python -m alpha brief <TICKER> --list`（每列的 `ib_*` 是凍結時點前最後一筆、未撤回）。
- 候選板計數：`library/private/measurement/candidate_state_series.jsonl` 的 `"date": "2026-10-21"` 那一行（`held` 2、`missing` 21、`priced_wait` 3；
  `side`：`edge_unmeasurable` 6、`not_multiple` 1）——側欄 6＋1 裡宣告缺 X 的是 3163.TWO、3234.TWO、688020.SS、MP。
- 已觸發：`python -m engine_b.event_watch counters`（`fired_unconsumed` 21、`semantic_pending_check` 19、`semantic_flagged` 14）；逐筆 `python -m engine_b.event_watch semantic-queue`。
- 窗內到期與叫醒（凍結時印 `expires_in_window 10 until_in_window 46 fired 21`）：
  `python -c "import json;w=json.load(open('library/leads/event_watches.json',encoding='utf-8'))['watches'];L=[x for x in w if x['status'] in ('active','fired')];print('expires_in_window',sum(1 for x in L if '2026-10-21'<=str(x.get('expires'))[:10]<='2026-11-30'),'until_in_window',sum(1 for x in L if '2026-10-21'<=str(x.get('until'))[:10]<='2026-11-30' and not '2026-10-21'<=str(x.get('expires'))[:10]<='2026-11-30'),'fired',sum(1 for x in w if x['status']=='fired'))"`
- A 股預約披露日：巨潮資訊 `http://www.cninfo.com.cn/new/information/getPrbookInfo`（POST `sectionTime=2026-09-30&market=szsh&stockCode=<代號>`；
  `f002d_0102` 首次預約、`f003d_0102` 第一次變更、`f006d_0102` 實際披露）。

### 裁決點來源（2026-10-21 查；tier：1＝公司或交易所自己發布，3＝轉述或資料商）

- [a] AXT 新聞稿 2026-10-01（tier 1，經轉載逐字核對；BusinessWire 原址回 403）：「will announce its financial results for the third quarter 2026 in a press release immediately following the close of market on October 29, 2026」——https://www.stocktitan.net/news/AXTI/axt-inc-schedules-third-quarter-2026-earnings-release-for-october-29-1r3y6691ysip.html
- [b] 巨潮資訊預約披露（tier 1）：002270 首次預約 10-27；002428 預約與實際 10-21；300395 首次預約 10-27；301511 首次 10-30、變更 10-27；688020 首次 10-30。
- [c] 界面新聞 2026-10-20（tier 3，只佐證公告時間）：https://www.jiemian.com/article/15214009.html
- [d] kalkine 轉述 ASX 公告（tier 3；ASX 原件沒開）：https://kalkine.com.au/news/announcements/lynas-rare-earths-to-release-september-2026-quarterly-results-on-29-october
- [e] Aehr 2026-10-08（tier 1）：「Monday, November 2, at 5:00 p.m. Eastern Time」——https://www.aehr.com/2026/10/aehr-test-systems-to-announce-first-quarter-fiscal-2027-financial-results-on-november-2-2026/
- [f] Coherent 新聞稿 2026-10-14（tier 1，經轉載）：「will release its fiscal 2027 first-quarter financial results on November 4, 2026, after the NYSE closes」——https://www.stocktitan.net/news/COHR/coherent-corp-announces-timing-of-fy2027-first-quarter-earnings-ddaorgdddw11.html
- [g] trendlyne 轉載 KSH 給 BSE 的 2026-10-12 通知（tier 1 內容、轉載；BSE 原件沒開）：「scheduled on 04/11/2026, inter alia, to consider and approve unaudited financial results for the quarter and six-months period ended on September 30, 2026」——https://trendlyne.com/latest-news/all/3360394/KSHINTL/ksh-international-ltd/
- [h] Silex Q2 季報財報行事曆（tier 1）：`library/raw/silex_q2_2026_interim_report_2026_07_17_excerpt.txt:35`「Interim report Q3 2026 4 November 2026」
- [i] 日東紡 IR カレンダー（tier 1）：「2027年3月期 第2四半期決算発表 11月5日」——https://www.nittobo.co.jp/ir/calender.htm
- [j] MarketScreener 行事曆（tier 3；ats.net 行事曆頁抓不到內容，敘事寫入時也標「第三方日程」）——https://www.marketscreener.com/quote/stock/AT-S-AUSTRIA-TECHNOLOGIE--6814931/calendar/
- [k] MP 2026-10-08（tier 1）：「after the U.S. markets close on Thursday, November 5, 2026」——https://investors.mpmaterials.com/investor-news/news-details/2026/MP-Materials-Announces-Date-for-Third-Quarter-2026-Financial-Results-and-Webcast/default.aspx
- [l] USAR 沒有公告 Q3 日期（10-21 搜尋）。推論：Q2 10-Q 在 2026-08-10 申報（季末＋41 天；第 40 天是週日），像 40 天申報人 → Q3 期限 11-09；申報人類別沒查。
- [m] 證券交易法第 36 條（季報：每季終了後 45 日內＝11-14，當天是週六；月營收：每月 10 日以前）。法說會日期沒查。
- [n] Soitec Q1'27 新聞稿 p.5（tier 1）：「H1'27 Results are due to be published on November 18th, 2026, after market close.」——https://www.soitec.com/docs/default-source/financial-documents/2026-2027/en/soitec---cp-q1'27---en.pdf
- [o] Sivers 財報行事曆（tier 1）：「November 26, 2026 Interim report」；2026-07-09 新聞稿「Q3 2026 Interim Report: November 26, 2026」——https://www.sivers-semiconductors.com/investors/financial-calendar/
- [p] IQE 財報行事曆（tier 1）：只列 2026-09-07 中期業績，之後沒有日程——https://www.iqep.com/investors/events/financial-calendar/
- [q] Lumentum 2026-10-05（tier 1）：「will release its fiscal first quarter 2027 financial results on Thursday, November 5th, 2026, after the market closes」——https://investor.lumentum.com/financial-news-releases/news-details/2026/Lumentum-Announces-Reporting-Date-for-Fiscal-First-Quarter-2027-Financial-Results/default.aspx
- [r] AAOI 新聞稿（搜尋摘要，原文沒開）：11-05——https://www.tradingview.com/news/prnewswire:0a001e72f0789:0-applied-optoelectronics-announces-date-of-third-quarter-2026-financial-results-conference-call/

### 裁決（逐檔 append：日期｜ticker｜文件｜新版 `ib_*` 或不換版理由｜「錯」的 kind）

- （尚無）
- 2026-10-22｜002428.SZ｜2026 年第三季度報告（巨潮 2026-10-21 刊登；`library/raw/yng_002428_q3_2026_report_excerpt.txt`）｜新版 `ib_7d91b08d37505c0c`：仍缺 X，等的文件由三季報改成 2026 年報（`ew_1497`，2027-05-01）；之後到 10-30 五版只換騎或補定位格，候選理由一字不改（現行 `ib_77bf446488c5f152`）｜錯：無——被評的斷言（騎 InP 基板層的量：供貨協議在第三、四季變成營收）尚未到裁決點：季報不拆產品，自有反證①（化合物半導體營收不高於上半年季均或毛利率 < 30%）要等 2026 年報｜三格（另列、不進判讀線）：①部分——合同負債 1.98 億元主要是磷化銦預收款（錢先到）；「變成營收」與買方是誰都沒回答 ②仍缺 X ③同一件（仍在等產品別營收，文件換成年報）
- 2026-10-31｜002270.SZ｜2026 年第三季度報告（董事會 2026-10-27；`library/raw/cninfo_002270_q3_2026_report_excerpt.txt`）｜新版 `ib_fbaef401915f3723`：仍缺 X（`missing_kind=filing`；`ew_1892`，2027-01-31）｜錯：無——被評的斷言（讀不出卡在它；賭全球分接開關缺口溢到第二大廠、出口占比往上）尚未到裁決點：季報沒有點名、交期、配額，也沒寫新增訂單｜三格（另列、不進判讀線）：①否——海外用戶收入前三季年增 45.91%（推一步第三季約 48%，與上半年 44.6% 同速：維持不是加速），沒有變壓器廠點名用它 ②仍缺 X ③同一件（缺口流向華明的一手、已定價主參照不變；H 股發行規模由 when 的「另外盯」升進缺的清單，不是新的門柱）
- 2026-10-31｜300395.SZ｜2026 年第三季度報告（董事會 2026-10-23、巨潮 10-24 掛出——名單寫的「10-27 預約」照實際日期評；`library/raw/cninfo_300395_q3_2026_report_excerpt.txt`）｜新版 `ib_1c0bba935e67a6e4`：仍缺 X（`missing_kind=filing`；`ew_1891`，12-15，到期前沒有就等年報）｜錯：無——被評的斷言（讀不出卡在它；賭石英布在 M9 以上變主料、菲利華被買方點名）尚未到裁決點：季報不分產品｜三格（另列、不進判讀線）：①否——前三季營收 20.82 億（年增 50.7%）、第三季 7.74 億，石英電子布的收入、認證、客戶一字未提 ②仍缺 X ③同一件（四項不變；多記一句前三季少數股東損益 3,104 萬是中益轉盈的影子）
- 2026-10-30｜AXTI｜第三季財報新聞稿（8-K 2026-10-29；`library/raw/axti_8k_2026_10_29_q3_2026_results_excerpt.txt`）＋法說逐字稿（10-29，第三方機器轉錄；`library/raw/axti_q3_2026_earnings_call_transcript_excerpt.txt`）｜新版 `ib_7486b16fd41c958c`（10-29 23:30 UTC，新聞稿後）→ `ib_57cb9d4b4428727e`（換騎、補法說的毛利率歸因）→ `ib_22424c1f01f6ca63`（10-31 已回落重問）：仍已定價等回落，錨重設在 10-30 收盤（自家三年 P/S 第 82.4 → 79.9 百分位）｜錯：無——被評的「必須為真」①第二季是新基本盤：**證實**（第三季營收 7,340 萬美元 > 4,758.9 萬、毛利率 56.0% > 35%；凍結版自有反證①反方向成立、不會再響，已改寫成第四季條件）②擴產沒提前、沒有新增產能：未推翻（AXT 自寫 2026 年產能倍增目標已超過，觸及讀圖反證④，三次換版判讀維持量；列舉補進的光智科技〔先锐〕是既有廠換老闆）③客戶照約付款：待 10-Q（約 11-13）｜三格不適用（不是缺 X）；候選狀態沒有移動。同一份新聞稿另觸發 thesis `axt_inp` §7b（[893] → review_required），記在 O1 段
- 2026-10-31｜LYC.AX｜2027 財年第一季季報（ASX 公告 2026-10-28 21:12 UTC，文件日期 10-29；`library/raw/lynas_asx_quarterly_sept_2026_excerpt.txt`）＋2026 年報的分部與 JARE 貸款段｜凍結版 10-22 因分析師家數 >12 機械撤回（`ib_ddbccbca78353625`，在季報之前）；季報後 10-31 翻回邊緣重發 `ib_514f4fefdd74a1d0`：仍缺 X（`missing_kind=filing`；`ew_1935`，2027-02-05）；11-01 分析師 13 家再撤回（`ib_6197543b76dce17f`；failure log #110 第 4 次，不是改判）｜錯：無——被評的斷言（分離重稀土層的護城河：中國以外只有它商業量產、時間領先）尚未到裁決點：兩條層反證（第二家商業級出貨 `ew_0875`、確定採購縮減 `ew_0876`）都還在盯、沒觸及｜三格（另列、不進判讀線）：①否——Dy＋Tb 一季 23 噸，距 JARE 確定採購成規模還遠、JARE 提貨量沒有公開數字；已定價仍量不到（系統沒有澳洲申報人的機械財報歷史）②撤回（非邊緣）——季報後那一版仍缺 X，撤回是門檻 ±1 家的機械翻轉 ③同一件
- 2026-11-04｜AEHR｜2027 財年第一季財報新聞稿（8-K 2026-11-02；`library/raw/aehr_8k_ex991_fq1fy27_results_2026_11_02.txt`）＋法說逐字稿（11-02，第三方轉錄；`library/raw/aehr_fq1fy27_earnings_call_transcript_excerpt.txt`）｜新版 `ib_9c60147ca0404cc7`：缺 X → 可開（11-03 兩道門：X＝客戶具名、客戶為什麼選晶圓級，屬讀到邊，改列加碼條件 c1／c2；起始門四項都過；另加兩條逾期型反證）｜錯：無——被評的「必須為真」①backlog 轉成有利潤的營收：本季證實（營收 3,300 萬美元、季增 75%，由去年同季虧損轉成淨利 720 萬，backlog 仍升到 1.009 億）②錯的訊號（轉換慢於預期、客戶端寫出別家燒機設備）都沒出現；瓶頸的形狀（晶圓級那一段只有它，沒被反證也沒被客戶證實）不變；成長多了一條封裝級燒機（雲端客戶第一顆 AI 處理器每月十幾台 Sonoma），凍結版沒寫到｜三格（另列、不進判讀線）：①否——客戶仍沒具名；為什麼選晶圓級只有執行長自述（封裝級篩不掉某些早夭失效、晶圓級篩檢成本是良率改善的一小部分）②移動：缺 X → 可開——移動來自門的設計改變（11-03），不是 X 被回答 ③不適用（不再是缺 X；加碼條件 c1／c2 與舊 X 是同一件）｜揭露：寫這行之前看過研究包裡的現價與「同窗口股價 -39.3%」那一行（研究包 valuation 方法說明），沒看量測日的價格
- 2026-11-04｜002428.SZ｜關於簽訂日常經營重大合同的公告（深交所 2026-054，11-03 晚間披露、文件日期 11-04；`library/raw/yng_002428_ann_2026_054_aoi_inp_lta.txt`）＋公告 2026-035（上市公司持有雲南鑫耀 55.83%；`library/raw/yng_002428_ann_2026_035_xinyao_stake.txt`）｜新版 `ib_6ddbc1599db83fd7`：缺 X → 可開（11-03 兩道門：上一版缺的三件——營收拆分、買方是誰、已定價主參照——都不是起始門；起始門四項都過；營收拆分、AOI 自己的一手、為什麼選它、7 月那張單的買方改列加碼條件 c1–c4；另加兩條出口許可相關的反證，其中一條逾期型：2027-09-30 前境外營收沒有跳過 1 億元）｜錯：無——被評的斷言（騎 InP 基板層的量：7 月供貨協議在第三、四季變成營收）仍未到裁決點（要等 2026 年報）；這份公告不是營收，是第二張更大的單：買方第一次具名（AOI），2027 年度合同 1.944 億美元、以兩用物項出口許可為前提；凍結版沒寫到的是上市公司只分得磷化銦利潤的 55.83%｜三格（另列、不進判讀線）：①部分——「買方是誰」對新合同回答了（AOI；7 月那張仍不具名），「變成營收」沒回答 ②移動：缺 X → 可開——移動主要來自門的設計改變（11-03），新的具名長約讓起始門更站得住，但不是 X 被回答 ③不適用（不再是缺 X；加碼條件 c1／c3／c4 與舊 X 是同一件）｜揭露：寫這行之前沒看今天或量測日的價格；priced_in 沿用上一版 10-30 快照的倍數；入圖包 [902]（雲南鍺業供貨給 AOI）待核准
- 2026-11-04｜AXTI｜沒有新文件（第三季 10-Q 截至 11-04 還沒申報，EDGAR 最新是 10-29 的 8-K）；新讀的只有已存在的 Lumentum FY4Q26 法說轉錄（`library/raw/lite_transcript_q4fy2026.txt`）與 Q2 10-Q 的增資段｜新版 `ib_f5ec6e1cf7fae13b`：已定價等回落 → 可開（11-03 兩道門：「等回落」併回可開；起始門四項都過；深挖清單十項查完——上一版唯一缺的「客戶為什麼選它」由 Lumentum 執行長自己的話作答：「we found additional substrate help from AXT, Inc.」，為了多一份基板產能、不是換不掉；另加一條逾期型反證：2027-06-30 前北京六吋沒開始量產出貨）｜錯：無——被評的斷言照 10-30 那一行：①第二季是新基本盤已證實 ②擴產沒提前、沒有新增產能未推翻 ③客戶照約付款待 10-Q；這一版是字彙與清單的換版，不是文件引起的，「錯」的 kind 照舊等 10-Q 與 [896]｜三格：不適用（名單登記時是已定價等回落，不是缺 X）｜揭露：寫這行之前，印候選板列時看到了判斷日以來的報酬（−6.8%）——不是為了裁決去看的，照實記下；裁決只引用文件，不引用這個數
- 2026-11-04｜SILEX.ST｜2026 第三季報告（Nasdaq Stockholm 2026-11-04 07:30 CET，MFN 原檔；`library/raw/silex_q3_2026_interim_report_2026_11_04_excerpt.txt`）＋法說逐字稿（11-04，Investing.com，經抓取工具轉錄、本機沒核到原文；`library/raw/silex_q3_2026_call_investing_excerpt.txt`）｜新版 `ib_ec150dd0b2b4ab98`：缺 X → 可開（11-03 兩道門：上一版缺的三件——客戶端或第三方點名它代工與 Lumentum 的鏡片在哪裡做屬讀到邊，改列加碼條件 c1、c2；OCS 占營收多少本季第一次寫出；已定價的主參照量不到是一句脈絡；起始門四項都過；另加一條逾期型反證：2027-06-30 前開發中的 OCS 客戶沒有一家轉量產）｜錯：無——被評的斷言（鏡陣列層的護城河：只有它量產得出 OCS 用的 MEMS 鏡，而且 OCS 的量撐得起它）尚未到裁決點：季報與法說都沒有客戶或第三方點名、Lumentum 的鏡片來源仍沒揭露；四條層反證都沒觸及（賽微北京沒宣布量產、Lumentum 11-02 新聞稿沒寫越過那位客戶）；量的那一半往證實走一步（OCS 約占總營收三成、電信第三季年增 68.3%；法說稱最大那位是「The only OCS customer who really is in production in the world today」，另有 10 家開發中）｜三格（另列、不進判讀線）：①部分——②OCS 占比答了（約三成，CEO 段），①客戶點名與 Lumentum 鏡片來源、③已定價主參照都沒答 ②移動：缺 X → 可開——移動來自門的設計改變（11-03）與 X② 被回答，X① 沒有被回答 ③不適用（不再是缺 X；加碼條件 c1、c2 與舊 X① 是同一件）｜寫的時候沒有看價格（敘事已定價一格沿用 10-20 的「上市價 81 克朗、五個月約翻倍」脈絡，沒有更新）
- 2026-11-05｜COHR｜FY2027 第一季財報 8-K（2026-11-04 盤後；新聞稿＋投影片）＋10-Q（季度至 2026-09-30，同日申報）｜不換版——非倍率持股（名單規則 5：財報只當層的證據、不做股價裁決）；現行 `ib_01924d886ff09619`（11-04 14:05 UTC，財報前）騎的 CW DFB 讀圖這次沒有被叫醒，敘事不用換；層的證據寫進四份讀圖換版：InP 基板 `sr_36505176157af3f8`（反證⑥觸及：翻倍的是元件晶圓廠、不是自供基板）、InP DFB `sr_ab7dec2b636728f7`（反證②觸及：擴產第一段落地、缺口沒消失）、六吋 InP `sr_f9f07562a7d9d36a`、DSP `sr_72dff6c738f4e7f4`，判讀都不變；thesis v3 照 [836] 另做｜錯：無——被評的斷言（凍結版 `ib_4233a575e88d7756` 的必須為真兩條證據＋錯的訊號）：①六吋產能倍增是否如期：**證實、提前一季**（8-K 投影片「Internal InP output capacity doubled YoY one quarter early; on track to more than double again by CY27-end」）②買家內製的比例：兩份文件都沒寫（Lumentum 下季約兩成那句等 Lumentum 自己的文件）③錯的訊號都沒出現——毛利改善寫明來自定價優化、良率與成本（不是降價），訂單延伸到 CY28、長約一般簽到這個十年結束（「LTAs typically extend through the end of the decade」），10-Q 寫 InP 仍是 industry-wide shortage；scale-up 沒有延後或改回銅（PhotonLink 預計 2027-03 季營收破 1 億美元）｜寫的時候沒有看價格
- 2026-11-06｜3363.TWO｜第三季合併財報董事會通過＋新增資本支出（櫃買重訊 2026-11-05；`library/raw/mops_3363_board_resolutions_20261105_q3_capex.txt`；完整季報 11-14 前上傳）＋奇景 6-K（11-05；`library/raw/himax_6k_q3_2026_cpo_foci_excerpt.txt`）＋鉅亨 11-05 報導（`library/raw/cnyes_3363_q3_2026_capex_20261105_excerpt.txt`）＋9-09 法說的第三方整理（`library/raw/vocus_3363_investor_conference_20260909_summary_excerpt.txt`）｜新版 `ib_e419cb775d8649eb`：缺 X → 可開（11-03 兩道門：X＝FAU 用在哪個 CPO 平台、客戶是誰，屬讀到邊，留在加碼條件 c1，另加 c2〔FAU 營收拆分或 C 公司以外的大客戶〕；起始門四項都過；另加一條逾期型反證〔2027-07-10 前，2027 年上半年沒有一個月營收達 3.4 億元〕與一條稀釋反證）｜錯：無——被評的「必須為真」①FAU 在 2026 下半年量產並出現在月營收裡：尚未到裁決點，時程往後移——第三季營收約 6.0 億元、季增約四成，但 FAU 只是「依客戶需求開始微量貢獻營收」（第三方整理轉述新聞）；奇景說工程量產已開始、量產時點由終端客戶決定、它自己的 CPO 業務 2027 年起才有像樣貢獻；凍結版寫的「2026 下半年量產」沒被推翻也沒被證實 ②毛利要跟著上來：尚未到裁決點、目前反方向——前三季毛利率約 5.1%（2025 年全年約 19%），新產線成本先到 ③具名的 CPO 平台：沒有（重訊沒寫 FAU 或客戶；鉅亨「據了解」國內半導體客戶、COUPE，沒具名）④錯的訊號（量產延後、認證失敗、C 公司占比腰斬）都沒出現；季報不揭露主要客戶表｜三格（另列、不進判讀線）：①否——平台與客戶都沒被回答 ②移動：缺 X → 可開——移動來自門的設計改變（11-03），不是 X 被回答 ③不適用（不再是缺 X；加碼條件 c1 與舊 X 是同一件）｜揭露：寫這行之前，印候選板列時看到「判斷日以來 −36.6%」、讀研究包時看到現價與「同窗口股價 -41.4%」——不是為了裁決去看的，照實記下；裁決只引用文件
- 2026-11-06｜ATS.VI｜2026/27 半年報（11-05；ats.net PDF，`library/raw/ats_h1_2026_27_report_excerpt.txt`）＋第二季法說簡報（11-05；`library/raw/ats_q2_2026_27_conference_call_slides_excerpt.txt`；AT&S 沒有公開逐字稿）＋新聞稿｜凍結版之後 10-23 換過一版 `ib_cf353e90a3a82667`（NVIDIA 10-21 載板協議、財報前）；財報後新版 `ib_fa6e2936923f5eec`：缺 X → 可開（11-03 兩道門：X＝已定價的主參照〔自家三年倍數〕，系統沒有奧地利申報人的機械財報歷史、半年報也答不了，11-03 起是一句脈絡、不是起始門；起始門四項都過；深挖清單十項都是引用——客戶為什麼選它由 Marvell 自己的話作答〔多一份產能，不是換不掉〕；另加一條逾期型反證〔2027-06-30 前 2026/27 匯率調整後營收年增沒達 45%〕與加碼條件 c1 客戶自己的文件具名、c2 Kulim 新線量產）｜錯：無——被評的「必須為真」①2026/27 指引是起點：半年報確認全年指引（營收 +45–55%、EBITDA 利潤率 32–37%），上半年營收年增 45.4%、EBITDA 利潤率 33.2%，2027/28 還要再長尚未到裁決點 ②when 寫的兩件——客戶付款開始入帳：**證實**（合約負債上半年新增 4.21 億歐元，另有 2.11 億歐元客戶預付款應收）；載板價格調升延續：**證實**（Microelectronics 分部營收年增 82.9%，原文「higher volumes, higher prices」；簡報「improved pricing」「Material availability continues to be tight」）③錯的訊號（新產能開出後交期縮短、價格回落、客戶承諾縮減）都沒出現；凍結版沒寫到的是 NVIDIA 10-21 的載板協議沒有它（10-23 那一版已寫進）、Kulim 第二廠多一位沒具名的長期客戶｜三格（另列、不進判讀線）：①否——已定價的主參照仍量不到（半年報不會給系統沒有的歷史序列）②移動：缺 X → 可開——移動來自門的設計改變（11-03），不是 X 被回答 ③不適用（不再是缺 X）｜揭露：寫這行之前看了價格——研究包的現價與「10-06 以來股價 −51.2%」、為了寫已定價那一格的脈絡印了最近 30 個交易日的收盤（10-06 約 226 歐元、11-05 收 110.2 歐元），並查了下跌原因（二手報導：沒有公司本身的觸發事件，科技股整體回檔）；裁決只引用文件，不引用價格
- 2026-11-05（11-09 回填）｜AXTI｜Coherent FY2027 第一季財報 8-K 與 10-Q（2026-11-04；買方文件，觸及磷化銦基板層讀圖反證⑥）｜新版 `ib_963ef5f9be18a99a`：連結換版——騎的讀圖由 `sr_5bd84c00f10ad7da` 換成 `sr_36505176157af3f8`（⑥判觸及後重讀仍是量），七格正文與候選狀態（可開）不變｜錯：無——這份文件寫的是 Coherent 元件廠產能翻倍（需求側加量），不是買方自供基板；被評的斷言照 10-30 那一行｜三格：不適用（名單登記時是已定價等回落）｜揭露：回填時已看過候選板列（判斷日以來 −24.3%，11-09 讀候選板時印出）——不是為了裁決去看的；裁決只引用文件
- 2026-11-07（11-09 回填）｜AXTI｜光智科技公告 2026-069（2026-11-06，先锐與 Coherent 2027–2029 六吋磷化铟衬底長期供貨意向協議；`library/raw/gzkj_300489_ann_2026_069_coherent_inp_loi_excerpt.txt`）＋光智科技第三季報（六吋在手訂單近萬片；`library/raw/gzkj_300489_q3_2026_inp_orders_excerpt.txt`）｜新版 `ib_5a2398613c6e7598`：可開不變；改「卡在誰」的先锐那句與必須為真②（Coherent 在分散六吋來源）｜錯：無——反證「客戶退出或要回預付」沒觸發（意向協議沒寫 AXT、Coherent 沒申報任何改變）；同一版仍寫先锐「是既有的廠換了老闆，不是新蓋的產能」，見下一行｜三格：不適用｜揭露：同上一行
- 2026-11-09｜AXTI｜沒有 AXT 自己的新文件（第三季 10-Q 截至 11-09 還沒申報，EDGAR 最新是 11-06 的 13G/A）；新讀的是同層與買方：光智科技投資者關係活動記錄表 2026-003（2026-09-24 刊登，先锐兩個擴產案；`library/raw/gzkj_300489_ir_20260924_xianrui_capacity_excerpt.txt`）與 2026-004（11-02；`library/raw/gzkj_300489_ir_20261102_inp_excerpt.txt`）、雲南鍺業 2026 半年報的擴產段（2026-08-28；`library/raw/yng_002428_h1_2026_report_excerpt.txt`，10-17 已在自家庫）、Coherent FY2027 第一季法說（11-04，第三方轉錄；`library/raw/cohr_q1fy27_earnings_call_substrates_excerpt.txt`）、科創板日報 2026-08-22（媒體轉述；`library/raw/cls_kcb_inp_substrate_shortage_buyers_2026_08_22_excerpt.txt`）｜新版 `ib_3404da090f1a4434`：可開不變；換騎 `sr_0b5c82b7f896c8e6`（讀圖反證①判實質觸及，重讀仍是量），照①的 48 小時動作重答已定價（仍已定價，翻倍條件把中國兩家的新產能算進去）；第二季歸因改準；加通美私募逾期型反證與兩條加碼條件｜錯：`already_available`——凍結版 `ib_11a30b994d9658d7`（2026-10-20）必須為真②的後半「也沒有新增的產能」與它自己的錯訊號「出現新增產能的供應商」，寫下時已有反例：雲南鍺業半年報（2026-08-28，45 萬片擴產案）與先锐調研紀錄（2026-09-24，40 噸與 100 萬片兩案）都早於 10-20；②的前半「擴產沒有提前開出來」未推翻（兩家都還沒投產、先锐沒寫時程）。判讀（量）與候選狀態（可開）沒動——窗口變短，賭注沒翻｜三格：不適用｜揭露：同 11-05 那一行
- 2026-11-06（11-09 回填）｜002428.SZ｜AOI 第三季 10-Q（2026-11-05，期後事項與 MD&A；`library/raw/aaoi_10q_q3_2026_supply_agreement_lta_excerpt.txt`）｜新版 `ib_d4bd15eef71f00d8`：可開不變；加碼條件 c1（AOI 自己的一手）由這份 10-Q 確認（金額 1.944 億美元一致、預付最多 4,000 萬美元、出口要中國核准，沒具名供應商、沒寫材料），需求與時點兩格改寫｜錯：無——被評的斷言（騎磷化銦基板層的量：7 月供貨協議在第三、四季變成營收）仍未到裁決點（要等 2026 年報）｜三格（另列、不進判讀線）：①部分——凍結版的 X「買方是誰」由買方自己的申報補上一半（寫了合同、沒具名），營收拆分沒回答 ②沒移動（可開）③不適用（不再是缺 X）｜揭露：寫這行之前沒看 002428.SZ 的價格
- 2026-11-09｜002428.SZ｜沒有雲南鍺業自己的新文件；新讀的是同層：先锐調研紀錄（2026-09-24、11-02）、Coherent 11-04 法說、科創板日報 2026-08-22（長光華芯在驗證導入雲南鍺業與北京通美；雲南鍺業董秘辦說 6 吋大規模量產尚需時日——都是媒體轉述）｜新版 `ib_4b1b29b6df8d10ad`：可開不變；換騎 `sr_0b5c82b7f896c8e6`，照讀圖反證①的 48 小時動作重答已定價（仍量不到、仍當已定價看）；「想殺它的」補先锐擴產、刪「Coherent 自建襯底」（Coherent 11-04 的季報與法說都沒寫自製基板）｜錯：無——被評的斷言仍未到裁決點（2026 年報）；先锐擴產是競爭者的新產能，沒有投產時程｜三格：①否 ②沒移動（可開）③不適用｜揭露：同上一行
- 2026-11-09｜AXTI｜沒有新文件｜重述版 `ib_dab0eafb05d15bd9`（restates `ib_3404da090f1a4434`，判斷日不歸零）：只改已定價格的字面值——「約 23 倍」是 10-29 收盤算的（P/S 31.8 × 1.26／1.71），11-04 起各版照抄成「同一個價格」，11-09 版又誤標成 11-07；改成「10-29 收盤約 23 倍、11-06 收盤約 15 倍」｜錯：無（字面值更正，不是判斷）｜三格：不適用｜揭露：更正時看了 11-06 收盤的稽核數（P/S 20.3、第 77.3 百分位）
- 2026-11-07（11-09 回填）｜4979.TWO｜第三季合併財報（2026-11-05 發布——名單寫的「11-14 法定期限」照實際日期評；`library/raw/mops_4979_q3_2026_consolidated_excerpt.txt`）｜新版 `ib_1377263d575f95ea`：可開不變（等回落 → 可開發生在 11-04 `ib_2ed2787c83135b60`，是 11-03 兩道門把「等回落」併回可開，不是這份財報引起的）；獲利那句改成第三季實數、已定價重答仍判已定價；11-09 重述 `ib_d88ba85698358391` 只標錯的訊號編號｜錯：無——被評的斷言（凍結版 `ib_268b1bed22dcf35f`）：①近四季營收兩三年內明顯放大、CW 晶粒占比要上來：**部分**——第三季晶粒單季年增約六成六，但占營收 13.6%、和上半年 13.9% 差不多，還沒上來（兩三年的條件，尚未到裁決點）②錯的訊號都沒出現：穩懋 11 月簡報 CW-DFB 仍是合格中、Lumentum 10-Q 沒寫自家 CW 比例、晶粒客戶沒有流失（晶粒營收仍在長）③凍結版候選理由的「8 月獲利沒跟上營收」被第三季**推翻**：營業利益約年增一倍、毛利率約 27%（上半年約 24%）｜三格：不適用（名單登記時是已定價等回落，不是缺 X）｜揭露：11-07 那版重答已定價時看了價格（三十個交易日跌約一半）、11-09 為深挖清單看了 11-06 收盤的 P/S 百分位——不是為了裁決去看的，照實記下；裁決只引用文件
- 2026-11-09（文件 10-28）｜3081.TWO｜第三季個別財務報告（MOPS 電子書 2026-10-28 上傳——名單寫的「11-14 法定期限」照實際日期評；`library/raw/mops_3081_separate_financial_statement_202603_excerpt.txt`）＋10-28 法說簡報的自結數字（10-31 那版已讀）｜新版 `ib_12493ccc3f5a8b04`：可開不變、仍判已定價（等回落 → 可開發生在 11-04 `ib_a8d4f8b64e024ca6`，是 11-03 兩道門的規則合併、不是文件引起的）；10-31 那版讀了法說簡報、仍等回落；財報本身到 11-09 才讀——承諾附註多了長約的履約保證金美金 5,000 萬元截至發布日尚未收訖、三份原料長約（A01／A02／A03）、設備合約總價 14.29 億元未認列 5.60 億元，補兩條逾期型反證（保證金 2027-03-31、第四季營收 2027-01-31）｜錯：無——被評的斷言（凍結版 `ib_899f7c33036e91af`）：①長約的量 2027 年起出貨、2027 年產能 2.5 倍：尚未到裁決點（設備還在付款交機：未認列 5.60 億元；AIXTRON 10-29 前九月新聞稿寫產出逐季增加、沒有再說延後）②錯的訊號：穩懋改標量產——沒有（11 月簡報仍合格中）；大客戶占比腰斬——季報沒有客戶表，待年報；長約客戶縮減提貨——沒有，但保證金還沒收到（新登逾期型）；設備出貨再延後——沒有｜三格：不適用（名單登記時是已定價等回落，不是缺 X）｜揭露：11-09 寫已定價格時看了 11-06 收盤的 P/S 百分位與三十個交易日的報酬——不是為了裁決去看的，照實記下；裁決只引用文件
- 2026-11-09（11-10 回填）｜002428.SZ｜沒有雲南鍺業自己的新文件（巨潮 09-15 之後只有 09-17 孫公司砷化鎵項目借款、09-23 控股股東質押、11-07 控股股東不減持承諾；調研紀錄最新仍是 09-11）；讀到邊專找（子代理 E1）新讀買方 AOI 第三季法說（11-05，第三方轉錄；`library/raw/aaoi_q3_2026_call_fool_substrate_lta_six_suppliers_excerpt.txt`）｜新版 `ib_4a353f1d49f6152c`（完整重讀）→ `ib_2dc773cdf21c06c3`（讀到邊專找）：可開不變；已定價格「10-30 的快照 42 倍、715 倍」更正成 11-06 收盤快照的 29 倍、268 倍（42／715 是 10-21 三季報前的快照，10-16 起照抄十四版、11-04 版補日期時標錯；failure log #137 同族）；錯的訊號逐條標反證編號、補上原本沒列的第 2、5 條；加碼條件原 c1（AOI 自己的一手）由已存在的法說確認、拿掉，為什麼選它改成引用——AOI 執行長：基板有六家供應商、每一家都在合作，長約是為了確保供給、主要為 2028 年（＝多一份量、押它的擴產）｜錯：無——被評的斷言（騎磷化銦基板層的量：7 月供貨協議在第三、四季變成營收）仍未到裁決點（2026 年報）；凍結版沒寫到的是買方有六家基板供應商（什麼會換掉它＝AOI 另外的供應商），與騎的讀圖（量）一致｜三格：①否 ②沒移動（可開）③不適用｜揭露：完整重讀時為更正已定價格看了 10-16、10-30、11-06 三筆估值快照（倍數，不是報酬）——不是為了裁決去看的；裁決只引用文件
- 2026-11-09（11-10 回填）｜AXTI｜沒有 AXT 自己的新文件（第三季 10-Q 截至 11-09 還沒申報）；讀到邊專找（子代理 E1）新讀 Coherent FY2027 第一季 10-Q 全文（11-04）、AOI 第三季法說（11-05，第三方轉錄；同上一行的節錄）、Lumentum 10-Q（11-03）｜不換版——沒有答到加碼條件的新一手：c1（Coherent 自己寫出 AXT 的角色）——Coherent 10-Q 全文沒有 substrate、AXT、預付的字；c2（境內買方具名通美）沒有新文件。AOI 執行長「six suppliers for substrate」是層的事實（買方多來源化），留給下一次磷化銦基板層重讀；全新 2025 年報主要原料段寫「基板 AXT、Freiberger、香港商住友電工」（客戶端具名、不說理由）早在自家庫、敘事沒引，留給下一次換版（AXT 第三季 10-Q）補進深挖清單｜錯：無——被評的斷言照 11-09 那一行（③客戶照約付款仍待 10-Q）｜三格：不適用｜揭露：沒有自報的價格曝光（failure log #152 記的五次不含這一檔）
- 2026-11-09（11-10 回填）｜SILEX.ST｜沒有 Silex 自己的新文件（MFN 11-04 之後沒有新公告）；完整重讀新讀賽微三季報（10-29）、Lumentum 10-Q（11-03）、11-02 新聞稿與併購電話會、新易盛 10-29 調研紀錄；讀到邊專找（子代理 E1）新讀 Lightwave 2010-11-18 報導（DALSA 替 JDSU 量產 WSS 用的光學 MEMS 鏡陣列）與 Lumentum 2026-09～11 的公開職缺｜新版 `ib_1b7298d392fc3048`（完整重讀）→ `ib_ed8c718838aaa3e9`（讀到邊專找）：可開不變；已定價格「上市價 81 克朗，5 個月後約翻倍」是價格幅度（failure log #120），改寫成上市價與鎖定期兩件一手事實；錯的訊號逐條標反證編號；「什麼會讓它被換掉」的底補上：Silex 以外至少有一家 Lumentum 用過的 MEMS 代工（2010 年、WSS，不能讀成 OCS 鏡片現在在那裡做）｜錯：無——被評的斷言照 11-04 那一行（鏡陣列層的護城河）；四條層反證都沒觸及（賽微三季報沒寫 OCS 鏡陣列量產；Lumentum 10-Q 全文沒有 MEMS、沒點名客戶；Lumentum 的職缺沒有一份寫 MEMS 晶圓製程）｜三格：①否 ②沒移動（可開）③不適用｜揭露：完整重讀時為改寫已定價格看了上市以來的日線（上市首日大漲、之後回落）——不是為了裁決去看的；裁決只引用文件
- 2026-11-10｜002270.SZ｜沒有新文件（巨潮 10-31 之後只有 11-03 回購進展公告；港交所 11-09 的進行中申請清單仍只有 03-06 第一次呈交）｜新版 `ib_c818f66176b40cc3`（子代理 H2 照 11-03 起始門重判）：缺 X → 可開（X① 缺口的量流向華明→加碼條件 c1、c2，X② H 股發行規模→c3，X③ 已定價主參照量不到是一句脈絡；起始門四項都過；加第 5 條逾期型：2027-04-30 年報法定期限前沒寫出 2026 全年海外用戶收入年增四成以上）｜錯：無——被評的斷言照 10-31 那一行，仍未到裁決點（年報）｜三格：①否 ②移動：缺 X → 可開——規則合併（11-03），不是文件引起的 ③不適用｜揭露：子代理 E 的底稿把字面股價與三季報的回購成交價寫進已定價格，H2 與主 session 都讀到（寫入前拿掉）——不是為了裁決去看的
- 2026-11-10｜300395.SZ｜沒有新的財報；新讀巨潮 11-04 董事長提議回購與 11-09 董事會回購方案（`library/raw/cninfo_300395_20261109_buyback_plan_excerpt.txt`），同層日東紡 11-05 決算說明、中材科技 10-26 調研｜新版 `ib_bbeb0ecf853182b2`（組 B 完整重讀）：缺 X → 可開（11-03 起始門四項都過——石英布層判讀未定也算過；上一版缺的買方點名、終端認證結果、石英布份量改列加碼條件，已定價主參照量不到是一句脈絡；補逾期型第 4 條）；反證三條、讀圖四條都沒碰到（聯茂英文產品頁 11-09 仍兩款並列；10-31 後沒有石英布營收或停測的字；11 月三則公告沒有中益增資）｜錯：無——被評的斷言照 10-31 那一行，仍未到裁決點（年報）｜三格：①否 ②移動：缺 X → 可開——規則合併，不是文件引起的 ③不適用｜揭露：子代理讀回購方案時看到回購價格上限（刻意不節錄）；已定價格沿用 10-20 的脈絡句（含三年高點的股價），這一版沒有重看
- 2026-11-10｜AEHR｜2027 財年第一季 10-Q（2026-11-06；會計年度改到 6 月底，多一個 2026-05-30～06-26 的過渡月）｜新版 `ib_6400a8d865f185ac`：可開不變；已定價嗎由 yes 改答 unmeasurable——候選板前提失效「已定價的稽核行已全部缺席」：近四季營收接不成連續一年，自家歷史 P/S 缺席（insufficient_evidence），也不在主題等權組，要等 2027 會計年度（2027-06-25 止）的年報才接得起來（推一步：約 2027 年 8～9 月）；脈絡那句（11-04 市值約是全年指引營收的 14 倍）留著，翻倍條件不放寬；同日判掉 10-Q 叫醒的 `ew_2167`–`ew_2173`（都沒觸及）｜錯：無——被評的「必須為真」照 11-04 那一行；10-Q 沒有推翻（客戶仍沒具名）｜三格：①否 ②沒移動（可開）③不適用｜揭露：沒有看價格（改答是稽核行缺席的機械結果）
- 2026-11-10｜KSHINTL.NS｜Q2／H1 FY2027 財報新聞稿與擴產公告（董事會 2026-11-04；公司官網，`library/raw/ksh_international_q2fy27_press_release_capex_2026_11_04_excerpt.txt`）＋董事會決議所附財報（數字一致；BSE／NSE 原址對本機回 403／逾時）；Q2 法說（11-05）逐字稿與簡報到 11-09 官網都還沒有｜新版 `ib_47ed81c208a4f070`（子代理 H1）：維持缺 X，但缺的換成會死嗎——燈的輸入還是 2026-03-31 年報的資產負債表，現金跑道與負債兩項在最糟那一格；上一版的三件 X 改列加碼條件 c1–c3 → `ib_646629b34c8a551f`：缺 X → 可開——主 session 把 11-04 董事會決議附件 A 的上半年財報寫成機械觀測 `mo_0c53b7c4d1ada6ec993b5cd33d5cd665`（as-of 2026-09-30；mechanical，不經 pq2），重算後兩項都不是紅（本業賺得出現金；擴產仍要再借錢或增資）；另加一條逾期型反證：2027-06-15 前沒公布 FY27 全年銷量達 33,000 噸｜錯：無——被評的「必須為真」（凍結版 `ib_63239e9aa6a0fe97`）：①銷量走向 FY28 約 4.5–5 萬噸：尚未到裁決點，Q2 8,842 噸（年增 26%、季增 11%）②每噸 EBITDA 在 CTC 占比回落時仍守在約 9 萬：Q2 約 101,400，沒跌回——但 CTC 占比沒揭露、公司把一部分歸給盧比走弱，「回落時守住」還沒被測到 ③Hitachi 框架寫出量：沒有 ④擴產撐得住：往證實走一步——上半年營業現金流轉正 4.26 億盧比、總債 48.10 → 34.13 億；錯的訊號（每噸 < 75,000、擴產後利用率連兩季 < 六成、出口轉年減）都沒出現，美國提單沒查｜三格（另列、不進判讀線）：①部分——X①「跳升是價還是組合」：Q2 每噸更高，公司歸因出口占比、利用率、盧比走弱與效率，沒寫價、也沒寫 CTC 占比，沒有直接回答；X② Hitachi 的量、X③ 美國以外也緊的第三方證據：否 ②移動：缺 X → 可開——移動來自門的設計改變（11-03）與會死嗎改用 9 月底的數，不是 X 被回答 ③不適用（加碼條件 c1–c3 與舊 X 是同一件）｜揭露：沒有自報的價格曝光（已定價答量不到）
- 2026-11-10｜3110.T｜第 2 四半期決算短信（2026-11-05 TDnet）、決算說明資料與主要質疑應答（同日，E-IR；`library/raw/nittobo_fy2026_q2_results_presentation_and_qa_2026_11_05_excerpt.txt`）＋中材科技 10-26 調研（`library/raw/sinoma_002080_ir_20261026_special_glass_cloth_excerpt.txt`）｜凍結版之後 11-04 換過一版 `ib_ac85f34c4fa3cbf8`（決算前；已定價嗎由量不到補答已定價——自家三年 P/S 第 73.5 百分位，出現在數字裡補答已出現；當時沒寫這一行）；決算後新版 `ib_bcbac8f9eb6618d4`（組 B 完整重讀）：缺 X → 可開（是 11-03 兩道門把第二來源認證進度改成加碼條件 c1，不是決算回答了 X）；位置換上修後數字、時間窗照層說明 #1 的 48 小時動作改寫、補逾期型第 4 條｜錯：無——被評的斷言（凍結版 `ib_fa7246ba7b1720d4`）：①缺口撐到 2027–28、日東紡繼續漲價、電子材料獲利再往上：**到目前為止是**——電子材料上半年營業利益年增 63.1%、全年預估 280 → 319 億日圓，公司寫價格改定貢獻、來期再談；日東紡把擴產排到 2029 年度（供應商自述）②錯的訊號都沒出現：沒有需給緩和或降價、沒有載板廠寫不再短缺或第二來源合格、玻璃核心仍是送樣 ③逆風那句（Ibiden 第三、四家可望量產）沒有新的客戶端文件更新｜三格：①否——第二來源在高階載板的認證進度，決算只有日東紡的傳聞（「認定作業が進んでいるとは聞いている」）②移動：缺 X → 可開（規則合併）；凍結版的 X②（已定價主參照）11-04 已補答 ③不適用｜揭露：子代理起草時沒有看價格；已定價格沿用 11-04 寫下的快照（第 73.5 百分位），這一版沒有重算
- 2026-11-10｜USAR｜第三季財報新聞稿（8-K 2026-11-09；`library/raw/usar_8k_20261109_q3_2026_results_magnet_revenue_cash_excerpt.txt`）；10-Q 截至 11-10（台北 09:33）還沒申報（申報人類別 Non-accelerated，法定期限 11-16——名單 [l] 推論的「40 天申報人」錯了，裁決點照公司自排的 11-09 不變）｜新版 `ib_248568aa8d30d7b4`（子代理 H2 照 11-03 起始門重判）：缺 X → 可開（X① 磁材買方承諾→加碼條件 c1；X② 磁材營收由這份 8-K 部分回答——9 月第一筆、金額沒拆，寫成金額且有毛利改列 c2；X③ 是一句脈絡；起始門四項都過；第 3 條逾期型改成 2026 年 10-K 仍寫沒有確定的磁材協議）｜錯：`already_available`——凍結版我們賭什麼「現金 15.3 億美元、負債很少，撐得到量產」寫下時已有反例：9-04 8-K Item 2.03（子公司承接 DFC 貸款）與 9-15 補充風險因子都早於 10-17（8-K 的 9-30 資產負債表：非流動應付票據 3.06 億、權利金義務 3.62 億）；另 `emerged_later`——必須為真「Serra Verde 第一階段照計畫在 2026 年底到年產約 4,000 噸」：9-04 公司確實寫年底，11-09 改排 2027 年第二季。卡在哪（磁材沒有買方包銷或預付）仍成立；錯的訊號「磁材營收遲遲不出現」沒觸發｜三格：①部分——X② 第一筆磁材營收出現、金額沒拆；X① 否（前瞻聲明仍列商談與備忘錄轉成確定訂單）；X③ 否 ②移動：缺 X → 可開——11-03 規則，不是這份財報引起的 ③不適用｜揭露：寫的時候被動看過候選板理由與子代理 F 底稿的 EV／營收約 137 倍、共識營收約 8.7 倍成長、共識營收約 7.1 億（10 月快照）；沒有看股價與報酬
- 2026-11-10｜1802.TW｜第三季合併財報（2026-11-02 董事會通過、11-06 上傳電子書——名單寫的「11-14 法定期限」照實際日期評；`library/raw/mops_1802_fs_3q2026_segment_capex_excerpt.txt`）＋11-02 窯爐案重訊（`library/raw/mops_1802_ann_20261102_kiln_cold_repair_excerpt.txt`）｜新版 `ib_c56cdb82a089cf9a`（組 B 完整重讀）：缺 X → 可開（是 11-03 兩道門把買方點名、第二代占比改成加碼條件 c1、c3，不是財報回答了 X）；位置與必須為真換成第三季數字、補逾期型反證第 7 條｜錯：無——被評的斷言（凍結版 `ib_9e01b3c3839caac7`）：①第二代布還緊、台玻新產能開出就被吃下：**部分**——玻璃纖維部門第三季對外營收年增 124%、部門稅前 39.41 億元（第二季 21.99 億元），11 月再加窯爐案；但部門含大陸廠與一般玻纖、第二代拆不開，沒有買方點名 ②錯的訊號都沒出現：買方沒寫緩解（滬電 10 月仍寫鎖定優先配額）、沒有降價（日東紡說低誘電價格維持現狀）、部門營收沒轉年減、沒有增資 ③凍結版的「上半年合計仍是平板玻璃略多」被前三季合計翻過來（更新，不是錯）｜三格：①否——買方點名與第二代占比都沒被回答，擴產只多了金額（時程仍沒寫）②移動：缺 X → 可開（規則合併，不是文件）③不適用｜揭露：子代理起草時沒有看價格；已定價格沿用 10-16 收盤寫下的快照（第 89.5 百分位），這一版沒有重算
- 2026-11-10｜1815.TWO｜第三季董事會重訊（2026-11-04；合併財報電子書到 11-10 未上傳）＋10 月營收＋10-15 澄清媒體、10-16 注意交易（`library/raw/mops_1815_ann_2026q3_notices_excerpt.txt`、`library/raw/mops_1815_rev_202610_excerpt.txt`）｜新版 `ib_68df999615b25893`（組 B 完整重讀）：缺 X → 可開（是 11-03 兩道門把第二代占比、客戶為什麼選它改成加碼條件 c2、c1，不是文件回答了 X）；位置補毛利率、必須為真拿掉燈色、補逾期型第 9 條（2027-12-31 前泰國布廠沒有投產）｜錯：無——被評的斷言（凍結版 `ib_c6362220eca7e383`）：①第二代補不上、富喬放量、泰國廠 2027 下半年接上：**部分**——營收年增逐月放大到 10 月 85.62%、前三季毛利率 42.5%（2025 全年 28%）、泰國廠務工程已發包；第二代單獨仍量不到 ②錯的訊號都沒出現（沒有緩解、降價、月營收年減、延後、增資、改用第三代）③凍結版候選理由的「年報預估 2026 銷量低於 2025、成長得靠價格與組合」——毛利率的跳升與「價格與組合」那半句一致，銷量那半句季報不拆、仍無法驗｜三格：①否——公司 10-15 公告說產品占比不是它的資訊；客戶印證沒有新文件 ②移動：缺 X → 可開（規則合併）③不適用｜揭露：子代理起草時沒有看價格；已定價格沿用 10-18 寫下的快照（第 98.5 百分位），這一版沒有重算
- 2026-11-10｜2455.TW｜第三季個別財報（董事會 10-29、電子書 115/10/30 14:46 上傳——名單寫的裁決點「11-14 法定期限」照實際上架日評；`library/raw/mops_2455_separate_financial_statement_202603_excerpt.txt`）＋10-29 重訊兩則（第四、五次無擔保可轉債合計 15 億元；`library/raw/mops_2455_material_info_20261029_cb4_cb5_excerpt.txt`）＋09-04 法說簡報（`library/raw/mops_2455_investor_conference_20260904_excerpt.txt`）｜新版 `ib_7ea80219de4eeb2d`（11-09，完整重讀）：仍缺 X（`missing_kind=filing`；改等 2026 年報，約 2027-05）→ `ib_77e7e9710163b715`（子代理 H1 照 11-03 起始門重判）：缺 X → 可開（X＝CW 雷射磊晶的量與變體改列加碼條件 c1、客戶為什麼選它 c2；起始門四項都過；補第 5 條逾期型：2027-06-30 前 2026 年報還寫不出 CW 雷射的量或新客戶）｜錯：無——被評的斷言（賭它的 CW 雷射與光偵測器磊晶接住這一層的缺口；說不出 CW 的量與變體、和聯亞是不是同一個市場）尚未到裁決點：季報單一部門、只按地區拆，簡報只列產品名；凍結版的四條錯的訊號都沒出現（簡報產品頁仍列 CW-Laser、穩懋仍合格中、自己第三季毛利率升到 45%、沒有改回銅的新一手）；凍結版沒寫到的是第三季毛利率跳到 45%、「其他」地區單季 2.88 億元與 10-29 兩次可轉債 15 億元｜三格（另列、不進判讀線）：①否——CW 雷射的量與變體季報與三場簡報都沒寫 ②移動：缺 X → 可開——移動來自門的設計改變（11-03），不是 X 被回答（11-09 那一版還沒照門重判）③不適用（加碼條件 c1 與舊 X 是同一件）｜揭露：子代理 A 掃私有券商報告時 grep 輸出帶到元大 07-23、09-21 報告內的報告日股價與目標價；子代理 H1 讀檔時工具印出 `priced_at_write`（failure log #152）——都不是為了裁決去看的；裁決只引用文件
- 2026-11-10｜3081.TWO｜沒有聯亞自己的新文件；讀到邊專找（子代理 E2）新讀 TrendForce 2026-06-03 新聞稿（研究機構）｜新版 `ib_0b801fc08d207719`：可開不變、仍判已定價；卡在哪一格更正，判斷、候選狀態、反證與加碼條件一字不改｜錯：`already_available`（事實格，不碰賭注）——凍結版 `ib_899f7c33036e91af` 卡在哪一格寫「第三方第一次具名是券商」（凱基 2026-08-18）；寫下時（10-19）TrendForce 06-03 已把它列在 CW-DFB 產能 Broadcom、住友之後（四家合計約 74%）。TrendForce 是產能排名、沒寫客戶、份額與理由——客戶那一格仍只有私有券商報告（內容不進 repo），加碼條件 c2（為什麼選它）的字面沒達到；客戶端查過沒有命中（EDGAR 全文搜尋 2001-01-01～2026-11-09 沒有「LandMark Optoelectronics」；Lumentum 第一季 10-Q 與併購電話會沒寫磊晶向誰買）｜三格：不適用（名單登記時是已定價等回落）｜揭露：沒有自報的價格曝光（failure log #152 記的五次不含這一檔）
- 2026-11-10｜3163.TWO｜第三季合併財報董事會通過（MOPS 重訊 2026-11-05，只有累計數；電子書 11-09 未上傳）＋董事會決議與菲律賓子公司資金貸與（重訊 11-05）＋10 月營收（MOPS；`library/raw/mops_3163_material_info_q3_2026_excerpt.txt`）＋Coherent FY2027 第一季法說（11-04，第三方轉錄；`library/raw/cohr_q1fy27_earnings_call_photonlink_fiber_excerpt.txt`）｜新版 `ib_6711f55c36af304c`（子代理 C 完整重讀）：仍缺 X（`missing_kind=filing`），補兩條逾期型反證（下半年營收年增不高於上半年 2027-01-15；到 2027-05-31 沒有一手寫 CPO 已量產）→ `ib_23c138a5b0bac65f`（子代理 H1 照 11-03 起始門重判）：缺 X → 可開（押的 FAU 層判 undecided、不是 neither；原本的 X：量產出現在營收→c1，自己寫出 CPO 已量產→c2，客戶端或第三方寫出為什麼選它或向它鎖量→c3；已定價那一格拿掉 10-16 收盤的字面倍數與「高檔」）｜錯：無——被評的斷言（凍結版）：①CPO 光纖套件與配線盒 2026 下半年開始量產：尚未到裁決點——重訊與月營收拆不出 CPO，公司沒寫延後也沒寫已量產 ②本業營業利益率由約 5% 拉到兩位數（2027 的條件）：尚未到裁決點、目前反方向——前三季約 3%、第三季單季約 2% ③錯的訊號：量產延後——沒有；Coherent 整套自製——接近（Coherent 說這一季出貨的 CPO 產品包括自家光纖組件，沒寫給哪個平台）；下半年月營收沒有加速——尚未到裁決點（7–10 月年增 19.0%、上半年 17.5%，10 月 11.35% 放緩）｜三格（另列、不進判讀線）：①否——CPO 量產與層的量都沒被回答 ②移動：缺 X → 可開——移動來自門的設計改變（11-03），不是 X 被回答 ③不適用（加碼條件 c1–c3 與舊 X 是同一件）｜揭露：子代理 C 起草時沒有看價格（已定價格沿用 10-16 收盤的數）；主 session 11-10 印稽核區時看到「−32.9%」（failure log #152）——不是為了裁決去看的
- 2026-11-10｜3234.TWO｜第三季合併財報董事會通過（櫃買重訊 2026-11-05 16:23；`library/raw/tpex_3234_q3_2026_material_info_excerpt.txt`；完整季報到 11-09 還沒上電子書）＋10 月營收＋現增公開說明書全文（2026-08-19；`library/raw/mops_3234_cash_increase_prospectus_2026_projection_excerpt.txt`）｜新版 `ib_bb400ace8d786037`（11-07，重訊後；當時沒寫這一行）→ `ib_128e84839032c5ef`（子代理完整重讀）：仍缺 X（`missing_kind=filing`：第三季合併財報上電子書、會死嗎重算後重判）；同日重述 `ib_8b465524008dd144`（必須為真格的燈色改寫成燈背後的事實，failure log #120 第 5 次）｜錯：無——被評的斷言（騎 CW DFB 層的量：溢出的代工量灌進它、矽光代工 2026 年做到四成營收；必須為真「毛利率要持續上升、營業虧損翻成獲利」）：①毛利跟上營收、虧損翻成獲利：第三季**證實**（單季營收約 3.26 億元、毛利率約 30%、營業利益約 3,600 萬元，重訊累計數減上半年推算；前三季累計仍營業虧損 2,136 萬元）②矽光代工占四成：尚未到裁決點（2026 年報）③錯的訊號（月營收連兩月年減、降價遞延、再增資）都沒出現；凍結版沒寫到的是公開說明書自己預估擴產產線 2027 年新增營收 6.08 億元｜三格（另列、不進判讀線）：①否——代工的是整顆還是幾站、功率、客戶，重訊與公開說明書都沒寫 ②仍缺 X ③同一件——候選理由仍列代工內容與客戶兩格（①的答案可能把賭注從押層改成押插槽）；照 11-03 起始門，擋住可開的實際是會死嗎（燈的輸入是 6 月底的資產負債表：欠的比現金多、本業又在燒錢；9 月現增後的數字要等第三季合併財報）｜揭露：子代理起草時沒有看價格；11-07 那一版重看已定價時看了三十個交易日的報酬（跌約三成六）與自家三年 P/S 百分位——不是為了裁決去看的
- 2026-11-10｜4971.TWO｜沒有第三季新文件（電子書到 11-09 23:33 還沒上傳；11-12 法說已公告）；新讀今年三場法說簡報（03-12、05-07、08-27——凍結版前後十版敘事都沒引用）與 10 月營收｜新版 `ib_33924219d8916903`（子代理完整重讀）：缺 X → 可開（11-03 兩道門：上一版缺的①份額印證屬讀到邊，改列加碼條件 c1；②資金那一格是會死嗎，11-09 的燈不是紅；押的光偵測器層判不出〔undecided〕可以；補逾期型第 4 條）；反證第 1 條由「占比連兩季下滑」改成「金額連兩季年減」——占比會被其他產品線帶著走，2025 年第二、三季就字面成立過（L12）；處置醒來的 `ew_1872`（觸發文件是聯亞的活動通知，沒有內容）｜錯：無——被評的斷言（凍結版 `ib_199a6ef5fec4fde0`：高速 InP PIN 磊晶的商用訂單集中在它手上、基板配額跟得上擴產）尚未到裁決點：份額仍只有自報與券商稱；錯的訊號都沒出現（占比只在第二季降一季、全新或聯亞沒有具名拿下同一批大廠）。凍結版沒寫到的是兩句寫下前就有的一手：5 月簡報「磷化銦基板供應不足為主要瓶頸」、8 月簡報「客戶開始接受使用不同基板廠商的磊晶片」——基板那一半的條件有一手、沒被引用，不推翻斷言｜三格（另列、不進判讀線）：①否——份額印證沒有新文件（私有券商報告有相關線索，沒有份額）；資金那一格不是由文件回答，是 10-29 燈的規則改版後不再是紅 ②移動：缺 X → 可開——移動來自門的設計改變（11-03），不是 X 被回答 ③不適用（加碼條件 c1 與舊 X① 是同一件）｜揭露：沒有自報的價格曝光（failure log #152 記的五次不含這一檔）
- 2026-11-10｜4979.TWO｜沒有華星光自己的新文件；讀到邊專找（子代理 E2）新讀 TrendForce 2026-06-03 新聞稿（研究機構）｜新版 `ib_7d81228648ea1099`：可開不變（仍判已定價）；卡在哪一格更正，判斷、候選狀態、反證與加碼條件一字不改｜錯：`already_available`（事實格，不碰賭注）——凍結版 `ib_268b1bed22dcf35f` 卡在哪一格寫「券商給了第一條具名線索」（凱基 2026-08-18；內容不進 repo）；寫下時（10-19）TrendForce 06-03 已把它列在 CW-DFB 產能 Broadcom、住友之後（四家合計約 74%）。TrendForce 沒寫它的份額、客戶與理由，加碼條件 c1 的字面沒達到；客戶端 EDGAR 全文搜尋只有舊文件（Inphi FY2017–FY2020 10-K 列為封裝組裝承包商、不是 CW；InnoLight 2015 年 F-1 列為關係人供應商；Semtech 列為客戶）｜三格：不適用（名單登記時是已定價等回落）｜揭露：沒有自報的價格曝光（failure log #152 記的五次不含這一檔）
- 2026-11-10（文件 11-03）｜4991.TWO｜第三季線上法說簡報（2026-11-03，含 p.7 營收結構圖）＋同日重訊（第三季合併財報董事會通過；參與子公司威力富科技現增）＋6／9／10 月營收說明（`library/raw/mops_4991_conf_3q26_20261103_excerpt.txt`；電子書到 11-09 23:33 還沒上傳）｜新版 `ib_fe1661b388fc5817`（子代理完整重讀）：缺 X → 可開（11-03 兩道門：上一版缺的第一大客戶、模組廠印證、自有光電元件拆分屬讀到邊與五項必看，改列加碼條件 c1–c3；起始門四項都過；另加逾期型反證〔2027-06-30 前沒寫出 200G/lane PD 量產出貨〕；反證第 2 條由占比改寫成金額）｜錯：無——被評的斷言（讀不出卡在它；賭 200G PD 外賣集中在少數幾家、環宇是其一；必須為真「第二季掉下來的毛利率要回得去」「自有光電元件要跟著 1.6T 放量」）：①毛利率回得去：第三季回到 47.0%（去年同季 47.4%），仍低於第一季 54.5%——**部分證實** ②自有光電元件放量：第三季金額年增約 47%（營收乘簡報圖上占比推算），是哪一代沒寫 ③錯的訊號：「自有光電元件占比比前一年回落」字面成立（71% 對去年同季 75%），但金額年增約 47%、9、10 月說明寫需求持續成長——判沒有出現、條文改寫；三家以上可互換、擴大自製、PD 跌價都沒出現｜三格（另列、不進判讀線）：①否——第一大客戶、中國那一側、PD 拆分都沒回答 ②移動：缺 X → 可開——移動來自門的設計改變（11-03），不是 X 被回答 ③不適用（加碼條件 c1–c3 與舊 X 是同一件）｜揭露：寫的時候沒有看價格；為核起始門讀了候選板 artifact 的會死嗎那一欄（只印那一欄，沒印已定價與報酬）
- 2026-11-10｜8358.TWO｜第三季董事會重訊（2026-11-06；合併財報電子書到 11-10 未上傳）＋10 月營收＋11-06 可轉債董事會重訊＋9-14／10-16／10-31／11-04 馬來西亞四則（`library/raw/mops_8358_ann_2026_cb_malaysia_q3_notices_excerpt.txt`、`library/raw/mops_8358_rev_202610_excerpt.txt`）｜凍結版之後 11-07 連結換版 `ib_24f437d669ea28be`（只換騎的讀圖；沒有回掃前一天的可轉債重訊，當時也沒寫這一行）；新版 `ib_b5bbc390d1f315b0`（組 B 完整重讀）：仍缺 X、補 `missing_kind=filing`，X 換成可轉債的轉換價格與稀釋、馬來西亞廠規模（原三格改列加碼條件）；反證第 7 條照 48 小時動作改寫、補第 8（逾期型）、9 條｜錯：兩條——被評的斷言（凍結版 `ib_d961530614c4690c`）：①「翻倍要的量主要只能來自三廠」：`already_available`——10-16 重訊（檳城子公司增資 14 億元、「於馬來西亞設立生產據點」）與 9-14 設東南亞子公司都早於凍結版建立日 10-20 ②登記的錯的訊號「為擴產辦現金增資或發轉換公司債」觸及：`emerged_later`——11-06 董事會決議發行上限 70 億元可轉債；量與價那半（月營收連續 12 個月月增、前三季毛利率 27.5%）沒錯｜三格：①否——誰買 HVLP4、HVLP4 占比、三廠產能都沒被回答 ②沒移動（缺 X）③不是同一件事：新的 X 是可轉債稀釋與馬來西亞廠規模｜揭露：子代理起草時沒有看價格；已定價格沿用 10-18 的判斷句，其中券商脈絡句帶著報告日的股價（凍結版就有）；稀釋要等轉換價格，這一版沒有用價格重算
- 2026-11-10｜8996.TW｜沒有第三季財報（電子書到 11-09 還沒上傳；裁決點仍是第三季財報）；完整重讀（子代理 F）新讀 MOPS 10–11 月重訊（第五、六次可轉債、11-03 合資、11-05 注意交易公告）、10 月營收、美超微第一季 10-Q（11-06）、Vertiv 第三季 10-Q（10-28）、Munters 第三季新聞稿（10-23）｜新版 `ib_997cbe5e3a96c280`（11-09）：仍缺 X（兩格 X 不變；`missing_kind=filing`；處置 `ew_1564`）→ `ib_2ddab30be4ac54d2`（子代理 H1 照 11-03 起始門重判）：缺 X → 可開，押注收窄成只押分歧管層 `sr_47059f62582b16c2`（undecided）——CDU 層 `sr_fafc68d3f1b3a5dc` 判 neither，過不了起始門②；拿掉的依據是一手：年報說散熱團隊開發出分岐管和冷卻液分配裝置，但產能規劃只寫分歧管；兩格 X 沿用為加碼條件 c1、c2，新增 c3（買方或第三方寫出為什麼選它的分歧管）；補第 3 條逾期型（2026 年度合併財報附註仍只有美超微與 Bloom 兩家占一成以上，2027-04-15 到期）｜錯：無——被評的斷言（凍結版 `ib_e062d42bc4716cfa`：賭液冷的量加上客戶分散）尚未到裁決點（第三季財報）；錯的訊號都沒出現（美超微 10-Q：大陪審團傳票、沒有實體清單；Vertiv、Munters 沒寫 CDU 交期或拒單）；凍結版自己寫 CDU 層已判 neither 仍押著它——押注收窄是起始門②的要求，不是文件推翻｜三格（另列、不進判讀線）：①否——買方點名它的板式熱交換器、美超微以外客戶量產都沒被回答 ②移動：缺 X → 可開——移動來自門的設計改變（11-03），不是 X 被回答 ③不適用（加碼條件 c1、c2 與舊 X 是同一件）｜揭露：子代理 F 的底稿已定價格帶著日線高低點的字面價格（H1 這一版拿掉）；H1 grep 私有券商報告時輸出帶到目標價與收盤價標籤（failure log #152）——不是為了裁決去看的
- 2026-11-10｜SIVE.ST｜沒有 Sivers 自己的新財報（第三季報告 11-26）；完整重讀補讀 MFN 10-22 臨時股東會公告（終止 Deloitte、改選 EY；P11 認股權最多 728 萬股、約 2%）；讀到邊專找（子代理 E2）新讀 POET 2025-09-29 的 6-K（兩家聯合新聞稿）、POET 2025 年度 20-F 與 2026 年第二季 MD&A、O-Net 英文官網新聞、Ayar 官網｜新版 `ib_360aad29a29b40f2`（完整重讀）→ `ib_665e02e4ef20e4e4`（讀到邊專找）：仍缺 X（已持有；`missing_kind=filing`，等 11-26）；換會計師與 P11 寫進候選理由、何時與稀釋；錯的訊號逐條標反證編號（failure log #140）；卡在哪一格補 POET 那條與「買方年報不再提它」｜錯：無——尚未到裁決點（11-26）；換會計師不在反證第 4 條（收入認列、審計調整、持續經營敘述惡化）的字面裡，不算觸及｜三格（另列、不進判讀線）：①否——客戶端具名與為什麼選它沒有新一手 ②沒移動（缺 X）③不同件——11-04 那一版 `ib_fa3a9fa2c100bf44`（當時沒寫這一行）已把擋住的那一項改寫成會死嗎（2025 年報查核報告的持續經營重大不確定性、6 月底的資產負債表），凍結版的 X（客戶端具名、可量的財報數字）改列加碼條件 c1、c3 與一句脈絡｜加碼條件 c3（現行 `ew_2503`）主 session 判不收：POET 那份是兩家的聯合新聞稿（不算「不只 Sivers 自己說」），POET 之後的 20-F 與 MD&A 不再提它、光源寫自家「Blazar」——c3 照舊盯｜揭露：沒有自報的價格曝光（failure log #152 記的五次不含這一檔）
- 2026-11-10｜IQE.L｜沒有 IQE 自己的新文件（窗內沒有排定的財報；裁決點＝候選 watch 叫醒日 11-30）；子代理 C 的完整重讀新讀 Tower、MACOM 11 月法說兩份節錄｜新版 `ib_3697fc256da71508`（子代理 H2 照 11-03 起始門重判，底稿是 C 組的可開草稿）：維持缺 X，缺的換成會死嗎——候選板 11-10 的負債那一盞讀 6 月底期中報表：現金 4,160 萬英鎊、含 IFRS 16 租賃總借款 5,394 萬、近四季營業現金流 −392 萬英鎊（上半年 −644 萬，主要是付了 779 萬利息）；不含租賃有淨現金 3,020 萬、會計師繼續經營結論沒有重大不確定性，照寫在我們賭什麼；三分法 filing（2027 年 1 月交易更新、2026 年度結果 AIM 期限 2027-06-30），候選 watch 沿用 `ew_0249`（11-30）；C 組的錯的訊號標號、第 3 條逾期型、加碼條件 c1、c2、深挖清單照用｜錯：尚未到裁決點（11-30）——這一行只記換版，被評的斷言照凍結版，11-30 再評｜三格（另列、不進判讀線）：①否 ②沒移動（缺 X）③不同件——凍結版的 X（Tower、MACOM 兩筆承諾的量與 InP 營收拆分；已定價主參照）改列加碼條件與一句脈絡，擋起始門的換成會死嗎（負債那一盞的租賃口徑，failure log #118 第 3 次，口徑交使用者決定）｜揭露：子代理 C、H2 讀個股頁物化檔時帶到價格欄（failure log #152）；C 組的「寫的時候沒有看價格」對它的草稿不成立——不是為了裁決去看的
- 2026-11-10｜補記（不是裁決）｜名單內 11-03 之後只換騎的讀圖或只改字面的版本，當時沒在同一個動作寫行（處置紀錄 11-03 那一條的規則）——判斷與候選狀態都沒動，逐檔列出：002428.SZ `ib_1b6b4577b0078e28`（11-04 重述，只補深挖清單）、`ib_41ab9d55c9f65134`（11-05 連結換版）；AEHR `ib_ef3447ce8489cbfa`（11-05 換騎，[905] 入圖後全堆疊測試層判讀仍 undecided）；USAR `ib_26cf74dd128cb65d`（11-04 連結換版）；2455.TW `ib_3cdaed1f01285676`、`ib_bab257baa5d86cf8`、`ib_5aaac7480b48b79f`、`ib_bbbdfa1a7a60c37c`（11-04～11-07 CW DFB 層四次連結換版）；3081.TWO `ib_db47c667610ff7c6`（11-04 重述：燈色改寫成燈背後的事實）、`ib_d07fca8bea7e200a`、`ib_5a55d77d4d83e563`、`ib_9a569a9a181a38d4`（連結換版）；3234.TWO `ib_8cc20824b9b495d7`、`ib_bf57227c86504383`、`ib_11c0ecb7db941a40`、`ib_a60f3aa3ec7e69b6`（連結換版）；4979.TWO `ib_0a950a6639822155`（11-04 重述：燈色）、`ib_ea826837074b4d76`、`ib_3c333eade7e24e45`、`ib_d26e2035cdeb3293`（連結換版）；SIVE.ST `ib_12f3d97f379400d5`、`ib_ed2dfa0ea01e04b8`、`ib_b7bf89261a3595f5`（連結換版）。共 23 版。連結換版由換騎工具批次寫、不經寫 Q3W 行這一步；這類版本不改判斷，寫行只會是「錯：無、三格沒移動」｜查證：`python -m alpha brief <TICKER> --list`
- 2026-11-10（晚間）｜AEHR｜2027 財年第一季 10-Q（2026-11-06）的客戶集中度附註與地區營收（`library/raw/aehr_10q_fq1fy27_2026_11_06_excerpt.txt`；同日稍早那一行只讀了會計年度改制）｜新版 `ib_aff2f44d30e94c92`：何時格換版（候選板「何時格的裁決點已過」：點名的第一季 10-Q 已交）——可開不變；10-Q 寫兩家客戶占第一季營收 47.5%、25.1%，都沒具名（去年同季占一成以上的是另外三家），亞洲出貨 67%；錯的訊號逐條對反證第 1–4 條；何時格換到 2027 年初的第二季｜錯：無——被評的「必須為真」照 11-04 那一行；客戶集中度高但沒有推翻任何一條（客戶仍沒具名、沒有取消或延後）｜三格：①否 ②沒移動（可開）③不適用｜揭露：沒有看價格
- 2026-11-11｜USAR｜第三季法說逐字（11-09，Motley Fool 轉錄；`library/raw/usar_q3_2026_call_fool_and_10q_q2_customers_excerpt.txt`）＋第二季 10-Q 客戶集中度附註；第三季 10-Q 到 11-11 仍未申報（法定期限 11-16）｜新版 `ib_c65d61f1524a82c5`：只補深挖清單（latest_call、customer_concentration 由缺改引用），候選狀態與各格不動（可開，11-10 已由缺 X 移來）｜錯：無新增——法說說磁材仍在原型銷售、意向書與 MOU 約 2,500 噸不具約束力；Round Top 最終投資決定推到 2027 下半年，不在凍結版任何斷言上｜三格（另列、不進判讀線）：①否——磁材買方仍沒具名、沒有包銷或預付 ②不動（可開）③同一件（買方承諾，c1）
- 2026-11-11｜002270.SZ｜09-14 投資者關係活動記錄表（巨潮 relation 欄，2026 年最新一份；`library/raw/cninfo_002270_ir_2026_09_14_and_ar2025_customers_excerpt.txt`）＋2025 年報前五大客戶段｜新版 `ib_a2b82a626adfa33b`：補深挖清單兩項，卡點、賭注兩格各補一句；候選狀態不動（可開，11-10 由缺 X 移來）｜錯：無（待層重讀）——但凍結版（10-20）漏讀一份寫下時已公告的反面證據：紀錄裡華明自己答「变压器交付的瓶颈是分接开关吗？」「不是」，交期「整体没有明显变化」、產能「还存在较大弹性」；凍結版的賭注是「缺口溢到第二大廠」，這幾句對「分接開關層讀成量」不利、對「溢到有空產能的第二家」兩面——是 `already_available` 型的漏讀，不是斷言已錯；層讀圖 `sr_de2bb0babc93f7b5` 要重讀｜三格：①否——X（缺口流向華明在加速、海外變壓器廠具名）這份紀錄沒回答 ②不動（可開）③同一件
- 2026-11-11｜KSHINTL.NS｜沒有新讀的一手內文：Engine C 11-10 快照（估值壓力那一項）＋NSE 公告清單標題（11-04 員工認股配發 35,182 股；11-09 第二季法說逐字稿已申報，本機下載被擋、沒讀）｜新版 `ib_f3a10b5c8558f39f`：只補深挖清單（valuation_pressure 由缺改引用：自家歷史量不到、快照倍數當脈絡）、已定價那一格的本益比由約 48 倍改成快照的約 45 倍；候選狀態不動（可開）｜錯：無新增——沒有新的一手內容可評｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前已看過 11-10 快照的價格與本益比（為了估值壓力那一項）；這一版沒動任何判斷
- 2026-11-11｜3110.T｜有價證券報告書第 165 期（2026-06-18 提出，EDINET `S100YDBM`；`library/raw/nittobo_yuho_fy2025_customers_contracts_capex_excerpt.txt`）——主要客戶、重要契約、設備新設計畫｜新版 `ib_5b78d38505b84cc7`：深挖清單十項查完（customer_concentration：沒有客戶占合併營收 10% 以上）；position 補兩件事實、bottleneck 補一句推論；候選狀態不動（可開）｜錯：無新增斷言錯——但凍結版（`ib_fa7246ba7b1720d4`，10-19）漏讀兩件寫下時已公開的事：福島 150 億日圓玻璃布設備 2026-12 完工、公司寫全做 T 布可到現在產量約三倍（有報 06-18），與 2025-11-28 委託南亞塑膠織布（有報；第一季說明資料 08-05 也寫「南亜プラスチックとの協業」）——`already_available` 型的漏讀；它們對斷言①「日東紡繼續漲價」不利（量由它自己補、缺口收斂時先受壓的是價格），到目前價格改定還在談，所以不是已錯｜三格：①否——第二來源在高階載板的認證進度，有報沒寫 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜4971.TWO｜沒有新文件（第三季電子書與 11-12 法說都還沒出）；重讀庫裡第二季合併財報附註六(十三)股本（`library/raw/mops_4971_consolidated_financial_statement_202602.txt`）｜新版 `ib_b6f8d37850fff0cd`：深挖清單 dilution 由缺改引用（5-5 換股增發 7,200 仟股、流通股數多 18.0%，換來的光聖股票列金融資產）、latest_call 照台股慣例引 08-27 簡報 → `ib_7de60ee67819d246`：何時格修字（佔位字被寫成月營收的日子、還留著缺 X 時期的等待句）；候選狀態不動（可開）｜錯：無新增——換股稀釋在凍結版寫下時已在財報裡，凍結版「光聖持股是後盾」那句沒寫股數代價，不是斷言錯｜三格：①否——份額印證（c1）沒有新的客戶端文件 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜4991.TWO｜11-03 法說問答（富果依錄影用 AI 整理的備忘錄，二手；鉅亨報導）＋ 2026-04-09 重訊（GDR 現金增資，鉅亨逐字轉載；`library/raw/gcs_4991_gdr_board_20260409_and_fugle_call_memo_20261103_excerpt.txt`）｜新版 `ib_80b414c47c43589c`：深挖清單十項查完（latest_call 引二手備忘錄並標明；dilution 補 GDR）；必須為真改寫、卡點補一句、何時格換；候選狀態不動（可開）｜錯：`already_available`——凍結版（`ib_3a006e2f3d922739`，10-19）必須為真寫「7.86 億元要變成出貨，而不是再增資」，寫下時 GDR 現金增資（最多 1,000 萬股、約 8.3%）已經董事會（4-09）與股東會（6-03）通過；那一條在寫下時就朝錯的方向，GDR 還沒送件，所以是「漏讀已公開的反面事實」不是「已發生」｜三格：①部分——X（為什麼選它／什麼會換掉它）：管理層自己說缺料期間客戶調整了供應商、2027 年 100G 市佔可能微幅受影響，200G 多了矽鍺 PD；是供應商說法的二手整理，不是模組廠一手，c2 沒碰到 ②不動（可開）③同一件｜揭露：寫這一行前看到價格——鉅亨報導頁側欄帶出 4991 的報價與漲跌（沒有主動查；這一版沒動候選狀態）
- 2026-11-11｜3163.TWO｜115 年唯一一場法說（03-10，凱基）的簡報（MOPS pptx；`library/raw/mops_3163_investor_conference_20260310_excerpt.txt`）｜新版 `ib_09e4363f6e3094a9`：只補深挖清單（latest_call 由缺改引用），簡報沒有新事實——CPO 產品「115年下半年度開始量產」與年報同句；候選狀態不動（可開）｜錯：無新增｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜3081.TWO｜10 月營收（MOPS 上櫃彙總表；`library/raw/mops_otc_monthly_revenue_202610_3081_3363_4979.txt`）｜新版 `ib_e07957f32b74c6fe`：只改何時格（何時格寫的 11-10 裁決點已過）——10 月 5.70 億元、月增 5.5%、年增 183%，公司備註數據中心產品出貨增加；候選狀態不動（可開）｜錯：無新增｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜3363.TWO｜同上｜新版 `ib_06a87ffeb5873362`：只改何時格——10 月 2.29 億元、月增 2.0%、年增 70%，離逾期型反證的約 3.4 億元還遠（那條 2027 上半年才判）；候選狀態不動（可開）｜錯：無新增｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜4979.TWO｜同上｜新版 `ib_a43b66c6068e6d01`：只改何時格——10 月 5.58 億元、月減 2.8%、年增 75%，月營收沒拆晶粒，晶粒那條反證照舊等年報；候選狀態不動（可開）｜錯：無新增｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜002270.SZ｜同一份 09-14 投資者關係活動記錄表（層讀圖重讀，沒有新文件；`library/raw/cninfo_002270_ir_2026_09_14_and_ar2025_customers_excerpt.txt`）｜新版 `ib_623ee94823dd7460`：換騎分接開關層新讀圖 `sr_523b68e16040fb7a`（undecided，取代 `sr_de2bb0babc93f7b5` volume）；卡點兩句、押注括號與候選理由改寫；候選狀態不動（可開——判不出不擋起始門）｜錯：`already_available`——凍結版（10-20）押注的前提「這一層讀成量」，寫下時已有對它不利的發行人公告（09-14）；層重讀後判不出：前提沒了，斷言沒被推翻（美國 80–90 週的第三方一手仍在）｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜002428.SZ｜投資者關係活動記錄表 2026-011（11-10 特定對象調研與現場參觀，巨潮「投资者关系」欄；`library/raw/ynge_002428_ir_20261110_inp_locked_2027_6inch_export_excerpt.txt`）——心跳抓不到，drain 讀 carrioresearch 一則轉述貼文時回頭追到｜新版 `ib_3bae811c871ca1b3`：可開不變；換騎磷化銦基板層新讀圖 `sr_28626aae8c8dbe26`（仍 volume，取代 `sr_0b5c82b7f896c8e6`；反證⑧①被這份紀錄觸及），照⑧的 48 小時動作重答出現在數字裡了嗎——6 吋在手約 1.3 萬片、約 3 億元，客戶主要在海外，部分已取得出口許可在交，先出現在 2026 年報的境外營收，機械序列仍量不到（答案不變）；部位格補擴產首批設備已調試、現有與在建產能被客戶鎖到 2027 年底，必須為真②改成境外營收跳起來，深挖清單 latest_call 由 09-11 換成這一份｜錯：無——被評的斷言（7 月供貨協議在第三、四季變成營收）仍未到裁決點（2026 年報）；6 吋正式合同與海外交付在 09-11 那份紀錄沒有（那份寫需求以 3–4 吋為主），11-10 才寫出｜三格：①否 ②沒移動（可開）③不適用｜揭露：寫這一行前沒有看價格
- 2026-11-11｜AXTI｜沒有 AXT 自己的新文件（第三季 10-Q 截至 11-11 仍未申報；EDGAR 10-28、10-29 兩份 8-K 之後沒有）；新讀的是同層：雲南鍺業投資者關係活動記錄表 2026-011（11-10；同上一行的節錄）｜新版 `ib_f2c2591dbd811ba8` → 重述 `ib_9a18e08d1cfb1142`（同日，只在錯的訊號逐條標反證編號）：可開不變；換騎 `sr_28626aae8c8dbe26`，照⑧的 48 小時動作重答必須為真與已定價——中國同業的 6 吋已部分取得出口許可對海外交（收窗的第一步，客戶沒具名、對不到 AOI 與 Coherent 那兩張），但雲南鍺業連在建產能都被客戶鎖到 2027 年底、新開出的量不進現貨；必須為真②補這件事與「許可對中國同業是逐單放行、拿得到的，同一個桶子對它不是優勢」，錯的訊號第 7 條改成「對海外的交付放大到超過 11-10 的口徑」；已定價仍判 yes、翻倍條件不放寬｜錯：無——被評的斷言（③客戶照約付款）仍待 10-Q；凍結版寫「中國另兩家最快 2027 下半年、要出口許可才到得了美國公司」，11-10 那份說的是對海外（沒說美國）、部分、在交——是新事實，不是凍結版寫下時已可得｜三格：不適用｜揭露：寫這一行前沒有看價格；已定價的重答照 11-06 收盤的脈絡，沒有看新價格
- 2026-11-11｜3110.T｜沒有新文件（讀圖換版帶動）｜新版 `ib_edf9b4cc05c9a70d`：連結換版——IC 載板玻纖布層讀圖 `sr_cd14412c16fc279b` → `sr_ad8a8636c637ad63`（上層說明 `ln_3552bc3a00c18c0d` 第 1 條被日東紡 11-05 主要質疑応答觸及——T ガラス 2029 年度再增約兩成，48 小時動作「重讀時鐘」補做；判讀維持 volume、四條反證一字不改；`ew_0420` 留作 IR 一手 feed 12-22 重放的探針）；敘事的翻倍時間窗 11-10 那版已寫，判斷、候選狀態不動｜錯：無｜三格：不適用｜揭露：寫這一行前沒有看價格
- 2026-11-11｜1802.TW｜沒有新文件（同上一行的讀圖換版）｜新版 `ib_bf1f5697c7474c99`：連結換版（引用的玻纖布層讀圖 id 換成 `sr_ad8a8636c637ad63`）；判斷、候選狀態、加碼條件不動｜錯：無｜三格：不適用｜揭露：寫這一行前沒有看價格
- 2026-11-11｜IQE.L｜沒有 IQE 自己的新文件（investegate RNS 清單到 11-11，最新一則是 11-09 的持股變動通知）；讀圖換版帶動：InP 磊晶層第二版 `sr_a3859d8e49f2a6b9`（[919] 入圖住友化學，商用磊晶廠 4→5 家）＋Coherent 第一季法說節錄（11-04，第三方轉錄；`library/raw/cohr_q1fy27_earnings_call_inp_mix_oversupply_excerpt.txt`）｜新版 `ib_cf7c72f352201bba`：換騎（`sr_d16f22339e294216` → `sr_a3859d8e49f2a6b9`）；卡在哪一格補住友化學與 Coherent 的自製／外購比例，賭什麼與必須為真補時鐘（2027 下半年到 2028 年），何時補這一層的觀測點；加第 4 條連讀圖第 1 條（供給鬆）；候選狀態不動（缺 X：會死嗎）｜錯：尚未到裁決點（11-30）——這一行只記換版；新進者多一家與 IDM 自製時點是層的事實，沒有碰到凍結版的斷言（設計勝出轉成量、承諾變成揭露得出的量）｜三格（另列、不進判讀線）：①否 ②沒移動（缺 X）③同 11-10 那一行（不同件：擋起始門的是會死嗎）｜揭露：寫這一行前沒有看價格（這一版 priced_in 照舊量不到，沒有開 `--prices`）
- 2026-11-11｜3081.TWO｜沒有聯亞自己的新文件；新讀買方：中國五家光模組廠投資者關係紀錄（中際旭創 10-29／11-03、新易盛 10-29、華工 10-30、天孚 10-28、東山精密 11-02；`library/raw/cn_transceiver_ir_records_2026q3_material_supply_excerpt.txt`）｜新版 `ib_61ed061c9561e2b8`：卡在哪補買方第三季口徑——核心前提引的中際旭創 7 月紀錄是長協、預付款、股權投資鎖光芯片產能，同一家 10–11 月改口「物料供给在逐步改善中」，華工、東山點名的瓶頸是 DSP 與 PCB；判斷、候選狀態（可開）、反證與加碼條件一字不改｜錯：無新增——五家都沒點名聯亞；讀圖 `sr_790f15cdae054ce3` 反證①–⑨沒被字面觸及（雲嶺光電 8-27 已寫量產、索爾思只有小批量外售，依①但書不算）；買方口徑轉向是讀圖【窗口】那一段（2027 上半年附近開始關）的同方向證據，不是反證｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜4979.TWO｜同上一行（買方五家投資者關係紀錄）｜新版 `ib_6b51a534f5fdfb4b`：卡在哪補同一段買方口徑，推一步寫成「缺口收窄時晶粒要靠客戶選它的理由長大」——就是加碼條件 c1；故事卡點、事件、位置各補一句｜錯：無新增——五家都沒點名華星光；讀圖反證沒被字面觸及｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格；寫完之後，比對新舊故事的工具印出上一則故事事件格的一句「同組股價一起回落約一半」——不是為了裁決去看的，這一行的判斷沒有因此改
- 2026-11-11｜2455.TW｜11-09 重訊兩則（第二、三次可轉債行使贖回權，11-19 為申請轉換最後期限；`library/raw/mops_2455_material_info_20261109_cb2_cb3_call_excerpt.txt`）＋同上一行的買方五家投資者關係紀錄｜新版 `ib_eac1ca49f374f35d`：卡在哪補買方口徑；必須為真的股數那一句補贖回——9 月底兩次還剩面額 3.848 億元，照前三季平均轉換價推全數轉換約再多 240 萬股、約 1.3%；故事卡點、事件、必須為真各補一句｜錯：無新增——五家都沒點名全新；讀圖反證沒被字面觸及；凍結版的四條錯的訊號仍都沒出現｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜8996.TW｜第三季合併財報董事會通過（MOPS 重訊 2026-11-11 17:43，只有 1–9 月累計數；`library/raw/mops_8996_material_info_20261111_q3_board_excerpt.txt`；完整季報到 11-11 電子書還沒上傳，法定期限 11-14）＋同日法說公告（11-13 黑石財經論壇）｜新版 `ib_60c9536ff9b739d8`：累計數減上半年推單季——營收 37.43 億元（與 7–9 月月營收合計一致）、毛利率約 28.3%、營益率約 17.7%（第二季約 12.9%）；位置、必須為真的利潤率句、何時格換成董事會數字，錯的訊號第 1 條的推算補一句第三季合計已高於第一季（部門待核）；候選狀態不動（可開）；故事照現行敘事重寫｜錯：無——被評的斷言（凍結版 `ib_e062d42bc4716cfa`：賭液冷的量加上客戶分散）：量的那一半，第三季營收季增約六成、回到第一季之上（熱能產品部門數字待完整季報）；客戶分散那一半期中財報不揭露，仍等 2026 年度合併財報附註（逾期型第 3 條 2027-04-15）｜三格：①否——買方點名它的板式熱交換器、美超微以外客戶量產都沒被回答 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜3110.T｜沒有日東紡自己的新文件；新讀買方（載板廠）的口徑：欣興董事長 9-02 SEMICON、10-20 TPCA 兩場演講（媒體逐字轉述；`library/raw/unimicron_chairman_tpca_semicon_2026_tglass_shortage_media_excerpt.txt`）＋欣興 11-16 法說簡報（MOPS 11-11 上傳，只有財務頁）｜新版 `ib_e4d71c37cb56ceca`：卡在哪補一段——欣興說 T-glass 從一兩年前開始吃緊、2027 年最關鍵材料約兩成缺口、部分日本供應商開始規劃擴產，和 Ibiden 8 月的「材料採購風險會下降」口徑分歧；何時格的觀測點換成欣興 11-16 法說與載板廠自己寫下的文件；判斷、候選狀態（可開）、反證與加碼條件一字不改｜錯：無新增——加碼條件 c1 要載板廠或晶片廠的一手文件，媒體轉述的演講不算；反證②（載板廠一手寫出不再短缺）方向相反、沒被觸及｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜1802.TW｜沒有台玻自己的新文件；新讀最大買方台光電 10-29 法說的第三方二手整理（股感知識庫 10-30，依簡報與影音；`library/raw/stockfeel_2383_q3_2026_call_glass_cloth_materials_secondhand_excerpt.txt`）｜新版 `ib_3d0948d96e16f803`：卡在哪補一段——M10 的原料供應商「有好幾家，不會不足」、ASIC 也足夠、部分客戶用 Low Dk 2 而不全是 Q 布；E 布緊、預期供應商可能把 Low Dk 產能轉向 E 布；判斷、候選狀態（可開）、反證與加碼條件一字不改；故事卡點、事件各補一句｜錯：無新增——方向是錯的訊號第 1 條（買方寫第二代布也緩解），但只有二手、反證要的是買方一手，形式上沒觸及；登記為待一手（台光電年報進貨段、下一場法說）｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜1815.TWO｜同上一行（台光電法說二手整理）｜新版 `ib_d6370fcb10364058`：卡在哪補同一段；故事卡點與事件兩格補一句｜錯：無新增——同上，第 1 條形式上沒觸及｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜300395.SZ｜同上一行（台光電法說二手整理）｜新版 `ib_387b6b0bffa1e419`：卡在哪補一段——「部分客戶用料不全是 Q 布，有些使用 Low Dk 2」；判斷、候選狀態（可開）、反證與加碼條件一字不改；故事卡點、事件各補一句｜錯：無新增——方向接近反證第 1 條（寫明 M9 量產只用第二代布），但只有二手、說的是「部分客戶」，形式上沒觸及｜三格：①否 ②不動（可開）③同一件｜揭露：我的匯出工具誤取了 10-29 的舊故事當底稿、印出它的已定價格（有一句股價走勢與倍數）——不是為了裁決去看的；最後寫入的故事以 11-09 那一則為底，裁決只引用文件
- 2026-11-11｜SIVE.ST｜沒有 Sivers 自己的新文件（第三季報告 11-26）；新讀 CW DFB 層的買方：中國五家光模組廠投資者關係紀錄（`library/raw/cn_transceiver_ir_records_2026q3_material_supply_excerpt.txt`；同 3081.TWO 那一行）｜新版 `ib_34404e82234c4966`：卡在哪補買方第三季口徑（核心物料逐步改善、點名的瓶頸換成 DSP 與 PCB、索爾思計劃外售光芯片）→ 重述 `ib_75683d17d3eeb41a`（同日，只改何時格的佔位字：第三季報告寫成自己的日子 11-26，佔位字單獨一句）；判斷、候選狀態（缺 X；板上已持有）、反證與加碼條件一字不改｜錯：無新增——五家都沒點名 Sivers；讀圖反證沒被字面觸及｜三格：①否 ②不動（缺 X）③不適用｜揭露：寫這一行前沒有看價格
- 2026-11-11｜3163.TWO｜天孚通信 10-29 投資者關係紀錄問答 2（同 3081 那一行的五家紀錄節錄 `library/raw/cn_transceiver_ir_records_2026q3_material_supply_excerpt.txt`；天孚自述 CPO 架構配套的 FAU、ELS「目前相关产品已实现稳定量产交付」，預計 2027 年 CPO 配套產品占營收比重明顯增加）｜新版 `ib_fda7cfcbde7cc735`：卡在哪補這一句——被 NVIDIA 點名的五家之一已自述量產交付，波若威自己的文件還停在「115 年下半年開始量產」（就是加碼條件 c2）；判斷、候選狀態（可開）、反證與加碼條件一字不改｜錯：無新增——天孚沒點名波若威；讀圖 `sr_f1bec617ddd1dacf` 兩條反證（FAU 交期／配額、Coherent 的 FAU 給具名平台）都沒碰到；凍結版的「CPO 光纖套件與配線盒 2026 下半年開始量產」仍未到裁決點（公司沒寫延後、也沒寫已量產）｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格
- 2026-11-11｜3363.TWO｜同上一行（天孚 10-29 自述）｜新版 `ib_a0334276f3a2275c`：卡在哪補同一句，推一步寫成「上詮不在 NVIDIA 那份點名裡、FAU 還只是微量貢獻營收，同一層寫自己已量產的多一家」（就是加碼條件 c1）；同段只改字面重述 `ib_9cc4fe4624e25b66`（必須為真格的錯的訊號逐條標反證編號——寫入端提示沒標；四條原本都對得到第 1–3 條）；判斷、候選狀態（可開）、反證與加碼條件一字不改｜錯：無新增——天孚沒點名上詮；讀圖兩條反證沒碰到；凍結版①「FAU 在 2026 下半年量產並出現在月營收裡」仍未到裁決點（10 月 2.29 億元）｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前，為查反證、加碼條件與寫入端提示，印出候選理由與必須為真格時看到已定價的脈絡（11-06 寫的自家三年 P/S 百分位、「價格已經押在量產之後」）——不是為了裁決去看的，這一行只引用文件
- 2026-11-11｜KSHINTL.NS｜Q2 FY27 法說（11-05）逐字稿（11-09 申報；BSE 附件路徑下載，連結取自 Screener——pq2 [914] 不再需要你提供；`library/raw/ksh_international_q2fy27_earnings_call_2026_11_05_excerpt.txt`）｜新版 `ib_13e3fe64ebf8b2d2`：需求格更正 Hitachi 框架的簽約時點（第一季簽、8-11 宣布——同日事實抽樣抓到的那一句），補「AI 資料中心是很小的一塊」；定位格補每噸 EBITDA 的歸因（CTC 占比偏高、出口、利用率、盧比；財務長說加工費率增加「not that significant」——組合不是漲價）與管理層的長期約 85,000；卡在哪補出口客戶都在擴產、美國以外緊不緊沒說；必須為真格尾巴補一句；何時格與深挖清單 latest_call 改引用逐字稿；候選狀態（可開）、反證與加碼條件不改｜錯：無新增——被評的「必須為真」（凍結版 `ib_63239e9aa6a0fe97`）②每噸 EBITDA 在 CTC 占比回落時守在約 9 萬：尚未到裁決點，但管理層自己的長期數字是約 85,000（另說 75,000–85,000 是長期水準），往反方向一步；③Hitachi 框架寫出量：沒有（量「still to get that in place」，說約兩季內給答案）；①銷量走向 FY28 約 4.5–5 萬噸：尚未到裁決點（管理層說今年 26% 的量成長可持續）；加碼條件 c1–c3 都沒被回答｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前，印深挖清單時看到估值壓力那一項的快照倍數（11-10 近四季本益比約 44.5 倍、EV／營收約 1.9 倍）——不是為了裁決去看的，這一行只引用文件
- 2026-11-11｜ATS.VI｜沒有新讀的一手｜新版 `ib_b5f65639efb99211`（只改字面重述 `ib_fa6e2936923f5eec`）：必須為真格的錯的訊號逐條標反證編號——新產能開出後交期縮短、價格回落或客戶承諾縮減對到第 1、2 條，可轉債全換稀釋 4% 那條寫不設反證的理由（已發行、量已知，稀釋那一盞燈照算）；寫入端提示（failure log #160 之後重掃，可開 3 檔之一）；判斷、候選狀態（可開）、反證與加碼條件不動｜錯：無新增——沒有新的一手內容可評｜三格：①否 ②不動（可開）③同一件｜揭露：寫這一行前沒有看價格（只印了必須為真格「錯的訊號」那一段與反證清單）
- 2026-11-12｜MP｜2026 年第三季 10-Q（EDGAR 2026-11-06；`library/raw/mp_10q_q3_2026_segments_magnets_excerpt.txt`）｜不換版理由：非倍率——凍結版 `ib_5fe12d2ae072b121` 之後的 10-22 版已因分析師家數超過門檻機械撤回（`ib_6ad4de3c578e6599`），沒有現行敘事；照本段規則 5 只當層的證據、不做股價裁決｜錯：不適用（非倍率不裁決）——層證據寫在這裡：磁材分部第三季營收只有磁材前驅產品 1,862 萬美元（前一年同季 2,191 萬），成品 NdFeB 磁鐵 2025-12 起在 Independence 生產、仍沒有單獨的營收列，量產設備還在最後試車；10X 新廠 2026 年春天開工；Apple 預付累計 8,000 萬美元、都還沒認列營收；NdPr 氧化物與金屬營收 1.01 億美元（前一年同季 3,091 萬），第一季另簽一家美國科技與工業公司的包銷；7 月起 Project Swarm 讓美國與盟國的無人機、馬達廠預約 10X 的產能（公司自述，不是買方的話）。對照磁材層讀圖 `sr_f6888e317022f5ea`（量）的三條反證：包銷縮減或保底價重議——沒有；中國以外產能閒置、庫存累積或降價求售——沒有；中國撤銷出口管制——不在這份文件。讀圖不換版。（到點日 11-09＝名單候選 watch 欄的 ew_0203，本段補寫。）｜查證：`python -m alpha brief MP --list`

### 2×2

- 名單每份一列（registration §3.3：到量測日沒有裁決寫「尚未到裁決點」、組未定義寫「組未定義」，都不填格）。（尚無）

#### Q3W 處置紀錄（append）

- 2026-10-21（凍結當天）｜凍結時已觸發未檢 21 條全部處置：語意 19 條互動判定 touches=no（三份觸發文件逐份讀原文：Sivers 10-20 光達量產訂單新聞稿 13 條——光達、客戶未具名，不是資料中心 CW 光源，ew_1443 的條文本來就排除光達；POET 6-K 附件 99.1 只公告 11-16 季報 4 條；Aehr 8-K 股東會投票結果 2 條），各條理由寫在 watch 的判定紀錄；讀圖重讀訊號 2 條（ew_0121、ew_1110）是 X 推文誤醒、reactivate 回去等 Lumentum 自己的一手文件（failure log #98 當下修）。查證：`python -m engine_b.event_watch counters` 的 `fired_unconsumed` 0、`semantic_pending_check` 0。
- 處置後，名單內三檔等回落（3081.TWO、4979.TWO、AXTI）假設改宣告可開，四個機械前提都成立（`open_preconditions` 失效 0 條）——可開與否只剩「已定價嗎」的判斷，照各自裁決點重看（AXTI 10-29 盤後、台股 11-10 月營收與 11-14 第三季財報）。
- 2026-11-01｜追加量測「缺 X 會不會結案」（`registration.md` 同日追加，先於其餘 20 份的財報後新版）：寫每一份財報後新版或不換版理由時，另記三格——①凍結版的 X 有沒有被這份財報回答（是／部分／否，附段落）②候選狀態有沒有移動 ③仍缺 X 時新的 X 是不是同一件事。已看過的 002428.SZ、002270.SZ、300395.SZ、LYC.AX 另列、不進判讀線；11-30 窗結束後一次判。
- 2026-11-03｜回填第 1–5 列的裁決行（整體盲點審查 2026-11-01 §2 D：研究端都做了、量測端 0 行；plan `2026-11-02-001` §1 第 1 條）：逐版讀 `library/private/alpha/briefs/<T>.jsonl` 的候選理由、when、note 與引用的節錄檔，對照研究日誌十一、十三；被評的斷言用凍結那一版自己寫的瓶頸／賭注／必須為真。**寫的時候沒有看任何價格**（第一個量測日是 002428.SZ 的 11-20；其餘 11-22～11-28）。之後名單內的換版或複查，裁決行在同一個動作 append（research-drain SKILL 段 `narrative_rewrite` ⓔ）；短版 ④ 每天印「Q3W 裁決：到點 N｜已寫 M」，到點未寫的逐檔點名。
- 2026-11-03｜預先登記「月營收會不會讓人重答」（整體盲點審查 2026-11-01 external-4；plan `2026-11-02-001` §2 第 14 條；**先於 10 月營收公布**）：
  11-10 月營收公布後、11-14 Q3 財報公布前，數第 14–25 列（台股 12 檔）有幾檔被重答——重答＝該檔敘事 ledger 在窗內多一筆新版，
  或本段寫了一行不換版理由；只是讀了、沒寫下來的不算。反方預測 0。**0 → 不加任何營收叫醒**（問題在判斷、不在叫醒）；
  非 0 → 逐檔寫重答改了哪一格，再談營收叫醒。結果 11-14 append 在本段（N／12＋逐檔）。查證：
  `python -c "from alpha.providers.briefs import read_brief_records as r; [print(t, [b.brief_id for b in r(t)[0] if '2026-11-10' <= b.created_at.isoformat()[:10] < '2026-11-14']) for t in '1802.TW 1815.TWO 2455.TW 3081.TWO 3163.TWO 3234.TWO 3363.TWO 4971.TWO 4979.TWO 4991.TWO 8358.TWO 8996.TW'.split()]"`
- 2026-11-10｜月營收量測（上一條）的干擾揭露——先於 11-14 的結果行寫下，不改登記的數法：
  ①11-09～11-10（UTC）12 檔裡 11 檔有新版（只有 3363.TWO 沒有），起因是使用者 11-09 指示的完整重讀與照 11-03 起始門的重判，不是 10 月營收。
  ②查證命令的窗（`created_at` 11-10～11-13 UTC）今天數到 3 檔：2455.TW `ib_77e7e9710163b715`、3163.TWO `ib_23c138a5b0bac65f`、8996.TW `ib_2ddab30be4ac54d2`——三版都是子代理 H1 的起始門重判（11-10 01:37–01:47 UTC）。
  ③窗前（11-09 UTC）的版本：1802.TW `ib_c56cdb82a089cf9a`、1815.TWO `ib_68df999615b25893`、2455.TW `ib_7ea80219de4eeb2d`、3081.TWO `ib_12493ccc3f5a8b04`／`ib_0b801fc08d207719`、3163.TWO `ib_6711f55c36af304c`、3234.TWO `ib_128e84839032c5ef`（`ib_8b465524008dd144` 是 restates，不算重答）、4971.TWO `ib_33924219d8916903`、4979.TWO `ib_7d81228648ea1099`（`ib_d88ba85698358391` 是 restates）、4991.TWO `ib_fe1661b388fc5817`、8358.TWO `ib_b5bbc390d1f315b0`、8996.TW `ib_997cbe5e3a96c280`。
  ④登記假設 10 月營收 11-10 才公布；實際上多檔在 11-10 之前就上了 MOPS（波若威、高力由子代理 C、F 標出；光環、金居、富喬、英特磊、環宇的 11-09 版本已引用 10 月營收）——窗的起點和營收公布對不上。
  ⑤所以 11-14 照登記數 N／12 時，這個月多半不可判：數到的是門與重讀，不是營收。判讀方式（照數、剔除起始門重判與完整重讀的版本、或順延到 12 月營收）交使用者；11-14 的結果行照登記寫，另附這一條。查證：上一條的命令（11-10 印 2455.TW、3163.TWO、8996.TW 各一筆，其餘空）。
- 2026-11-10｜月營收量測**順延到 12 月**（使用者 11-10「月營收量測順延到 12 月」；理由見上一條：11 月的窗被起始門重判與完整重讀汙染，多檔 10 月營收早於 11-10 上架）：
  ①窗改成 2026-12-01～12-16（UTC，`created_at`）——涵蓋 11 月營收的法定期限 12-10 與之後 6 天；12 月沒有季報，不需要「季報前」的截止。
  ②母體（第 14–25 列台股 12 檔）、重答的定義、反方預測 0、決策規則（0 → 不加營收叫醒；非 0 → 逐檔寫重答改了哪一格再談）照 11-03 登記不變。
  ③**起因不是營收的新版照數，但結果行逐檔寫起因**（該版 note 寫的觸發文件或指示），判讀時把「營收引起」與「其他起因」分開數；restates 照舊不算重答。
  ④11-14 不寫結果行（11 月的窗作廢）；結果 12-17 append 在本段（N／12＋逐檔起因）。營收叫醒照舊等這個量（plan `2026-11-02-001` §5）。查證：
  `python -c "from alpha.providers.briefs import read_brief_records as r; [print(t, [(b.brief_id, 'restates' if b.restates else '', (b.note or '')[:40]) for b in r(t)[0] if '2026-12-01' <= b.created_at.isoformat()[:10] < '2026-12-17']) for t in '1802.TW 1815.TWO 2455.TW 3081.TWO 3163.TWO 3234.TWO 3363.TWO 4971.TWO 4979.TWO 4991.TWO 8358.TWO 8996.TW'.split()]"`

## 敘事事實抽樣與影子重寫（2026-11-03 起；登記：`registration.md` 檔尾「量測追加三條」①③）

> 種子、判讀線與「有事實錯」的定義照登記，這裡只記結果。① 每段 research-drain 收尾一行；③ 每月第一段一行（2026-12 起）。
> 執行指示住 research-drain SKILL 段 6「量測抽樣」。

### ① 敘事事實抽樣（日期｜brief_id｜句數 n｜有事實錯的句 m｜錯在哪一格；無引用的句另記）

- 2026-11-04｜`ib_3a006e2f3d922739`（4991.TWO，10-19 版；種子「2026-11-04」從當時現行 v2 敘事 90 份抽中）｜n＝36｜m＝0｜錯：無；無引用 1 句（定位格「6 月的成長公司歸因於代工與權利金」——月營收說明不在它引用的節錄裡，`alpha://three_questions/v1/4991.TWO#in_numbers_series` 只有數字）｜核對的一手：年報三份節錄（營收結構、客戶與地區、光二極體）、2Q26 法說節錄、凱基 2026-08-18 報告 p.1／p.6／p.7、光二極體層讀圖 `sr_dc76762c792f4c96`；同一家模型核對（不盲）
- 2026-11-05｜`ib_2b1e96d1530c63c2`（300757.SZ，11-05 版；種子「2026-11-05」從當時現行 v2 敘事 91 份抽中）｜n＝39（七格，以「。」與括號外「；」切句）｜m＝2｜錯：需求格「替一家海外核心客戶」——電話會議紀錄只寫「海外核心客户」、沒寫幾家（數字過精）；必須為真格「CPO 在 2027 年架構收斂」——TrendForce 原文是 CPO **測試**架構收斂（主詞）；無引用 3 句（卡在哪格與我們賭什麼格各一句「營收大宗是耦合與組裝設備」——營收沒拆，只有上半年同一集團約 12.61 億元訂單撐得起「已知最大的一筆訂單」，是沒標的推論；何時格 H 股與 A 股年報的法定期限沒附出處，規則本身無誤）；另有兩處數字在原檔、不在公開節錄（前三季營收 10.01 億元／年增 140.51%，三季報全文；「德國」ficonTEC，半年報全文與 TrendForce）｜核對的一手：羅博特科 2025 年報、2026 半年報、三季報（全文與節錄）、10-28 電話會議紀錄全文、H 股超額配售公告、TrendForce 2026-10-13 新聞稿全文（11-05 重抓：七段各對得到至少兩家，歸段是我們做的、原文沒逐段對應）、全堆疊測試層讀圖 `sr_fb7269d0f5f6fece`、Engine C 11-05 快照；同一家模型核對、且是同日自己寫的那一份（不盲）｜**處置**：同日改版 `ib_4c0f62346f9acdf9`（判斷、候選狀態、反證與加碼條件不變）＋故事 `st_8f934ae6a0cf1264`；同日再換第三版 `ib_c8afaa3f507dbed3`＋故事 `st_75771de2115801a3`（已定價改答量不到，failure log #131——收尾物化撞到，與抽樣無關）
- 2026-11-06｜`ib_f345308446e7b039`（CECO，10-31 版——10-28 判斷版 `ib_0348eec9da3f4394` 的字面值重述；種子「2026-11-06」從當時現行 v2 敘事 92 份抽中）｜n＝22（七格，以「。」與括號外「；」切句）｜m＝1｜錯：定位格「第二季營收年增 {in_numbers_latest}，10-Q 說增加主要來自大型燃氣發電專案的排放與排氣系統」——它引用的 10-Q 那句講的是**訂單**（第二季訂單 +192% 到 7.985 億美元）；10-Q 的營收段寫有機成長最大來源是發電市場、其餘增加來自 6 月 1 日合併的 Thermon（約 17.9% 營收不是有機），「由大型燃氣發電專案的在手交貨帶動」是工程系統部門營收那一句（主詞）。同一個錯也在候選理由與故事的定位、營收兩格。無引用 1 句：何時格「第三季財報（2026 年 11 月上旬）」日期沒附出處（事實對：10-27 公告 11-09 美東盤前）。另記：引用不全但事實對 2 處（定位格的「SCR 系統、消音」在 10-K 產品段節錄、該格沒引；卡在哪格的 Liberty 向 Wärtsilä 買的設備包含「Emissions System」在 `lbrt_10q_2026q2_ex103_wartsila_equipment_supply.txt`，只經讀圖正文轉述、讀圖引文清單沒有它）；對得上引用、但引用的 authority 本身可疑 1 處（必須為真格「照現在的速度現金撐不到一年」照 Engine C 快照：yfinance 自由現金流近四季 −1.629 億美元 → 4.5 個月；EDGAR 營業現金流減資本支出近四季 −2,160 萬 → 約 34 個月，照 10-Q 上半年的速度約 9 個月——句子在「現在的速度」讀法下成立，燈的輸入是 failure log #118 第 2 次）；股價那句（10-28：上半年大漲、6 月見高點後跌回年初以下）對收盤序列：年初 59.85、6-22 高 99.67、10-27 收 50.15｜核對的一手：CECO 2026Q2 10-Q 全文（11-06 重抓 EDGAR）、FY2025 10-K、2025Q4 與 2026Q1 財報稿全文、Liberty 2026Q2 10-Q Ex.10.3、排放系統層讀圖 `sr_ec43c226592362e4`（MDEQ 許可引文）、Engine C 快照與個股頁 artifact、收盤序列、EDGAR submissions（到 11-06 還沒公布第三季）、ew_1734（11-12 叫醒，對）；同一家模型核對（不盲），不是同日自己寫的那份｜**處置**：同日改版 `ib_8d7690602aaf1a29`（restates 判斷版：判斷、候選狀態、answers、反證不變；定位格與候選理由改正，何時格補日期出處，燒錢句改錨 10-Q 上半年營業現金流）＋故事 `st_52c11fba13873aab`；新節錄 `library/raw/ceco_10q_2026q2_net_sales_orders_segment_excerpt.txt`（六段，斷言是重抓原文的子字串）｜累積 3 份、有事實錯 2 份（判讀線 ≥ 10 份才判）
- 2026-11-07｜`ib_f4c788a5b4122f7e`（POWI，10-08 版；種子「2026-11-07」從當時現行 v2 敘事 93 份抽中）｜n＝20（七格，以「。」與括號外「；」切句）｜m＝3｜錯：需求格「並說這些技術的開發要幾年才完成」、卡在哪格「資料中心等級的高功率氮化鎵，它自己說還要幾年」、我們賭什麼格「自己估要幾年」——10-K 策略段是兩段：資料中心 AI 電源那一段（「additional products incorporating GaN transistors」→ 預期應用含資料中心）沒寫時程，「several years」寫在下一段、以「Additionally」開頭講電動車驅動模組與垂直氮化鎵（主詞）。同一個錯也在候選理由與故事的候選、卡在哪、需求、事件、我們賭什麼五格。舊節錄 `powi_10k_fy2025_10q_2026q2_short_check_excerpt.txt` 只收了兩句、沒收兩段的分界，錯是從節錄斷句產生的。無引用 2 句（定位格「它現在出貨的氮化鎵在充電器與家電電源」、卡在哪格「那一層供應商很多」）。另記：引用不全但事實對 1 處（定位格「多為經銷商」——10-K 銷售段寫經銷占產品營收約 69%，舊節錄沒收這句）｜核對的一手：POWI FY2025 10-K 全文（11-07 重抓 EDGAR）、2026Q2 與 Q3 10-Q、舊節錄；同一家模型核對（不盲），不是同日自己寫的那份｜**處置**：同日改版 `ib_546a7daafb789244`（restates：判斷、候選狀態〔不要〕、answers、反證條文不變——反證 watch 換登 `ew_2336`、舊 `ew_0583` 收掉；三句主詞錯與候選理由改正，定位格改「含經銷商；年報寫經銷占產品營收約七成」，何時格寫第三季 10-Q 已讀、下一個觀測點 2026 年報；已定價格照寫入規則補「寫這句的 2026-10-08 當天」，「便宜不是理由」改「價格位置不是理由」）＋故事 `st_0b36c991521d9690`；新節錄 `library/raw/powi_10k_fy2025_strategy_10q_2026q3_excerpt.txt`（兩段策略原文、經銷占比、Q3 10-Q 營收／前十大／終端市場表／風險因子的資料中心句）。另：第三季 10-Q（11-05）是這份敘事自訂的觀測點、抽到前沒有人讀過——POWI 不在 EDGAR 監看清單（failure log #133 第 3 次）；照讀：終端市場表仍四格、沒有資料中心，成長來自工業與通訊，反證未觸發｜累積 4 份、有事實錯 3 份（判讀線 ≥ 10 份才判）
- 2026-11-07 深夜（同日第三段）｜`ib_f20c19fb2f6dfeb6`（MOD，10-17 版；種子「2026-11-07」從當時現行 v2 敘事 93 份抽中——同一個種子、清單已換了幾版，抽到的不同）｜n＝24（七格，以「。」與括號外「；」切句）｜m＝3｜錯：卡在哪格「一年內圖上的供應商由 4 家變 8 家，新進者（AAON、Munters 與它）都做得進來」——CDU 層讀圖只寫 AAON、Munters 是 2025 年才做進來，Modine 是「新的一家」（10-17 讀進圖），引用裡沒有一句說它是新進者；圖上 4 → 8 是 10-07 到 10-17 我們讀進來的量，不是一年內的市場進入（主詞）。另兩句寫的時候對、讀的時候錯（跟著即時值漂）：已定價格「第 {own_history_pctile} 百分位，在中間」——11-07 填出第 5 百分位；定位格「最新一季營收年增 {in_numbers_latest}…但同季毛利率降 340 個基點到 20.8%」——即時值已換成第二季（+34.6%，9 月止），340 個基點、20.8% 是第一季的數（第二季全公司降 160 個基點到 20.7%、資料中心部門降 470 個基點到 19.7%）。無引用 2 句：需求格「也沒有任何雲端業者點名它」（超出引用的缺席主張，L11-5）；卡在哪格「卡住的料在它的上游（CDU 裡的大型板式熱交換器那一層讀成量的賭注）」——它引用的讀圖明寫 10-Q「沒點名零件、沒說是 CDU」，句子把兩件事接成一件、沒標推論。另記：「並說加了合格供應商」——原文是正在認證（qualifying additional suppliers），時態偏差、不計。故事層把錯放大：「一年內供應商由 4 家變 8 家」（拿掉了「圖上」）、「卡住的料在上游的大型板式熱交換器」（推論寫成事實）；同在 CDU 層的 AAON、Munters 故事也寫「一年內 4 家變 8 家」｜核對的一手：MOD FY2026 10-K 節錄、第一季 10-Q 節錄（07-30）、第二季 10-Q 全文（11-04 申報，11-07 重抓 EDGAR——抽到前沒人讀，failure log #133 第 4 次；照讀：CDU 仍沒拆、沒有交期字樣、零件供應受限照寫，三條反證都沒碰到）、CDU 層讀圖 `sr_fafc68d3f1b3a5dc`、三問稽核行與個股頁 artifact（11-07）；同一家模型核對（不盲），不是同日自己寫的那份｜**處置**：同日改版 `ib_0b47a5f1742076a7`（restates：判斷、候選狀態〔不要〕、answers、反證條文不變）＋故事 `st_5c68839e51d36e6d`（AAON、Munters 故事同句一起改）；新節錄 `library/raw/modine_10_q_20261104_data_centers_margin_excerpt.txt`（六段，斷言是重抓原文的子字串）。兩句漂移是機制缺口：故事層沒接 #94 的位置詞檢查（現行故事 16 檔有凍住的位置詞、3 檔已矛盾），同一輪查到燈色倒裝語序過了 #120——failure log #137 當下修（`526d3942`），故事 20 份、敘事 4 份換寫｜累積 5 份、有事實錯 4 份（判讀線 ≥ 10 份才判）
- 2026-11-11｜`ib_edcc9629afe195de`（LPK.DE，10-08 版；種子「2026-11-11」從當時現行 v2 敘事 93 份抽中）｜n＝20（七格，以「。」與括號外「；」切句）｜m＝1｜錯：需求格「主要半導體廠多數已在開發與認證階段使用它的 LIDE」——年報 p.5 寫「The majority of the relevant players in the semiconductor market」（半導體市場的多數相關業者），「主要」與「半導體廠」是敘事自己收窄的主詞；同一句也在候選理由。無引用 5 句：需求格前半「年報寫晶片廠與供應鏈正轉向玻璃基板與玻璃穿孔」不在它引用的節錄裡；定位格分部列表的「焊接」、我們賭什麼格「營收以 PCB、焊接、太陽能雷射為主」——節錄只有 Solar 2,830 萬與 Electronics 3,590 萬歐元，其餘約 5,100 萬歐元的分部沒抄；定位格「玻璃基板那一層在圖上只有兩家在開發」沒附讀圖引用；何時格第三季報告與年報的日期沒附出處（已自寫「以公司公告為準」）｜核對的一手：`library/raw/lpkf_annual_report_2025_short_check_excerpt.txt`（年報 p.5／p.9／p.40／p.54／p.55）；數字（營收 1.153 億歐元、年減 6.2%、訂單 9,160 萬歐元年減 19.9%、backlog 2,700 萬歐元、電子部門 3,590 萬歐元）全對；同一家模型核對（不盲）
- 2026-11-11 午（同日第二段）｜`ib_f3a10b5c8558f39f`（KSHINTL.NS，11-10 版；種子「2026-11-11」從當時現行 v2 敘事 92 份抽中——同一個種子、清單已換了幾版，抽到的不同）｜n＝36（七格，以「。」與括號外「；」切句）｜m＝1｜錯：需求格「8 月和 Hitachi Energy 簽了五年供貨框架」——它引用的 Q1 簡報 p.14 寫「During the quarter, we also signed a long-term framework agreement with a large Global transformer OEM」，簽約在 Q1（4–6 月），8-11 法說才宣布；無引用 4 句（定位格「銷量 8,842 噸（年增 26%、季增 11%）」與「2025 年 12 月才上市」、必須為真格「FY26（19.2 億盧比）」與每噸「約 68,000」、「上半年 16,811 噸」——引用的三份節錄與 Engine C 觀測都沒有這幾個數，季增 11% 與 16,811 噸跟 Q1 的 7,969 噸算得通）；其餘數字全對（Q1、Q2 營收與每噸 EBITDA、出口占比 26／27／32%、美國 8–11%、產能 57,845／72,200 噸、利用率 75%、總債 48.10→34.13 億、上半年營業現金流 4.26 億、FY26 營業現金流 −6.50 億、購置設備 16.28 億、IPO 淨額 39.75 億、海關提單兩筆與同址、國家實驗室兩句、Precision Wires 年報的關稅句）；另「CTC 約占總營收四到五成」是 50–75%×75%＝37.5–56%，寫窄了（自己標明的乘法，不算錯）；已定價格的本益比是快照時變值，沒回查
- 2026-11-11 下午（同日第三段）｜`ib_edf9b4cc05c9a70d`（3110.T，11-11 版；種子「2026-11-11」從當時現行 v2 敘事 94 份抽中——同一個種子、清單又換了幾版，抽到的不同）｜n＝43（七格，以「。」與括號外「；」切句）｜m＝1｜錯：卡在哪格「中國的宏和科技 2026 半年報也自述低熱膨脹玻纖布 2024 年通過下游認證、2025 年起批量供應 CCL 客戶」——半年報第二句的主詞是「特种电子布」（低介電與低膨脹都在內）：「公司2025年开始批量供应特种电子布给下游CCL客户」，敘事把它收窄成低熱膨脹布；無引用 3 句（定位格「決算短信寫全社營收年增 19.4%」——引用的 11-05 節錄沒有全社營收那一列；卡在哪格的券商報告那句——券商原文不進 repo、也不在引用裡；已定價格「11 月 4 日當天第 73.5 百分位」——引用的是每天重算的值，對不回寫下那天）；邊界、不計錯：定位格「公司寫的原因是 T ガラス、NER 賣多、E ガラス比重降與價格改定」——決算短信講上半年原因只寫特殊玻璃賣多、擴產與價格改定，「E ガラスの比率が低下」出自說明會講全年預估上修的因素｜核對的一手：日東紡 11-05 決算短信／說明資料／主要質疑應答節錄、08-05 第一季說明資料與 Q&A、有價證券報告書節錄、景碩與建榮年報節錄、台玻年報節錄、宏和半年報節錄、Ibiden 08-05 Q&A、中材科技 10-26 調研節錄；同一家模型核對（不盲）
- 2026-11-11 晚（同日第四段）｜`ib_eeb5dab3fdcb9a4d`（5411.T，11-11 版；種子「2026-11-11」從當時現行 v2 敘事 94 份抽中——同一個種子、清單又換了幾版，抽到的不同）｜n＝27（七格，以「。」與括號外「；」切句）｜m＝0｜錯：無。無引用 4 句：定位格「綜合鋼鐵集團（鋼鐵、工程、商社）」——三個事業別不在它引用的說明會節錄與 Engine C 快照裡；定位格「有価証券報告書只把它列為鋼鐵產品之一」——沒掛有報（10-07 那段 grep 過有報，見上方 10-07 紀錄，但敘事沒引用）；已定價格「11 月 4 日當天第 53.6 百分位」——引用的是每天重算的值，對不回寫下那天；何時格「2026 年度決算（約 2027 年 5 月）」沒附出處｜邊界、不計錯：卡在哪格掛的讀圖是 10-07 已被同日重讀取代的 `sr_4815aae51426ad76`（現行 `sr_761bd010a662901a`；兩版判讀與這兩句的內容一樣）；候選理由（不在七格裡）「日本本廠的 GO 供貨邊已打包等入圖（pq2 [729]）」過時——[729] 10-07 已 go、入圖（池子紀錄 commit 0b1c05e0，圖上 co:jfe_holdings 有供貨與持股兩條業務邊），定位格寫的「2026-10-07 入圖」才對｜核對的一手：JFE 電磁鋼板策略說明會節錄（2024-10-24，p.3／p.5／p.8／p.10）、2025-08-04 印度合資新聞稿（圖上 source）、11-06 上半年度決算說明會節錄、Engine C 半年營收（五個半年年增 −3.9%、−4.9%、−7.3%、−8.9%、−4.2%）、電工鋼層現行讀圖、待辦池 [729] 紀錄、稽核區「不在任何主題等權組」；同一家模型核對（不盲）
- 2026-11-12｜`ib_51f5eb078ad5624c`（688020.SS，11-09 版；種子「2026-11-12」從當時現行 v2 敘事 94 份抽中）｜n＝38（七格，以「。」與括號外「；」切句）｜m＝0｜錯：無。無引用 1 句：何時格「2026 年年報（2027 年 4 月 30 日前）」——法定期限，沒有引用。另記一處引用指偏：需求格「較大的一塊是伺服器記憶體封裝（也是三井自述）」——它引的三井 Q1 紀要節錄（`mitsui_kinzoku_q1fy27_briefing_minutes_copper_foil_excerpt.txt`）沒有這句，同一份紀要的另一個節錄檔（`…_microthin_pkg_price_excerpt.txt`）寫「PKG 向けについては、特にサーバー のメモリ用途において非常に需要が強く」、FY2025 說明會紀要寫「規模としてはメモリ向けが大きく」（經讀圖 `sr_431d7f58b2bcd6ac`）——與一手相符、不算錯｜核對的一手：方邦 2025 年報四份節錄（產品別表 p.32：電磁屏蔽膜 181,127,172.35 元／−5.75%、銅箔 88,084,456.89 元／毛利率 −1.24、銅板 38,935,969.88 元＝FCCL（同頁「FCCL 产品销售额同比增加71.21%」對到該列）、其他 25,333,029.38 元；可剝銅受托開發「增加利润929.25 万元」）、2026-07-01 風險提示（62.64 萬元、0.18%、「市场情绪过热及非理性炒作」）、一季報、半年報三份節錄（營收 17,281.52 萬元／+0.27%、銅箔 −20.25%、存貨跌價 −14,830,575.76 元、固定資產減值那一行空白）、第三季報（營收 275,196,444.78 元／+2.57%、歸母淨利 −48,514,427.52 元、資產減值損失 −24,657,195.38 元、「受技术开发合同项目阶段性减少影响」）、德福半年報、三井兩份紀要；讀圖的稼動率推算（2025 年度約七成→2026 年度預估約八成七）與盧森堡銅箔、YMT 的座位在讀圖原文。
- 2026-11-12 下午（同日第二段）｜`ib_4ad6f4e1f90c40f2`（6234.TWO，11-12 版；種子「2026-11-12」從當時現行 v2 敘事 99 份抽中——同一個種子、清單已換了幾版，抽到的不同）｜n＝38（七格，以「。」與括號外「；」切句）｜m＝1｜錯：定位格「兩個部門：鑽頭部門…；設備部門…」——它引用的第二季財報部門資訊是三欄（鑽頭、設備、其他部門），其他部門沒有對外營收，但上半年部門利益 1,881 萬元、6 月底部門資產 26.4 億元（前一年上半年部門損失 7,623 萬元），「兩個」數錯了（數字）。無引用 3 句：卡在哪格「沒有任何買方一手寫為什麼選它」——讀圖寫的是「圖上沒有任何買方說它為什麼選某一家」，句子拿掉了「圖上」（超出引用的缺席主張，L11-5）；何時格「之後每月 10 日前的月營收、2026 年度財報（2027-03-31 前）」法定期限沒附出處；何時格「沒有增資計畫」——節錄只有資本支出計畫的資金來源欄「自有資金」，年報全文另寫「目前以自有資金支應營運所需」、節錄沒收。另記：事實對、但數字只在全文不在公開節錄 1 處（定位格「現金與定存等金融資產比借款多」——第二季財報附註六(一) 現金及約當現金 7.94 億元、(九) 不算約當現金的定期存單 14.93 億元〔附註八：其中 1.28 億元質押〕，大於短期借款 10.99 億元）。邊界、不計錯：我們賭什麼格「量翻倍之後」——節錄只有上半年鑽頭部門 +72%，全文第二季鑽頭部門 6,550 萬 → 1.35 億元（+106%）、讀圖引的 10 月合併月營收 +335.8%；卡在哪格「它說自己在 IC 載板鑽頭上比日系便宜」——年報原文是「相對於日系廠商高單價的鑽頭產品更具競爭力」，比的是價格、沒直接寫「便宜」｜核對的一手：高僑第二季合併財報（全文與節錄：部門資訊、收入細分、營業外、借款、現金、其他金融資產、質押）、2026-11-11 第三季董事會重訊、2025 年報（全文與兩份節錄）、鑽針層讀圖 `sr_31b44c2545a00f0c`（含鼎泰投資者關係紀錄引文）、`python -m alpha edge 6234.TWO`（市值 0.16B、家數取不到）與三題燈（10 月月營收年增 +335.8%、已定價主參照 P/S）；同一家模型核對（不盲），而且是同日自己寫的那一份｜**處置**：同日重述 `ib_2587b81c515f2c38`（restates：判斷、候選狀態〔缺 X〕、answers、反證條文不變——自訂反證 watch 照寫入端換登；定位格改「營收來自兩個部門」並補其他部門那一欄、現金與定存寫出數字，卡在哪格收回到「圖上」，何時格改年報原話）＋故事改指新版 `st_26f2b9d8397abf86`（故事七格沒有這三句，內容不變）；節錄 `library/raw/mops_6234_2025_2026_segments_q3_board_excerpt.txt` 補 9 段（部門表頭、前一年第二季、部門資產、現金、其他金融資產兩段、質押、年報資金來源句、資本支出表頭；斷言是全文空白正規化後的子字串）｜**偏差註記**：這一段收尾先核的是 8021.TW（`ib_e6607723cc9ea287`，本段寫的可開那一份），不是種子抽中的這一份——發現後改回種子；8021 那份的核對結果不併入本段（見研究日誌第三十段）｜累積 11 份、有事實錯 8 份（73%）——**過了登記的判讀線（≥ 10 份、≥ 30%）：敘事事實率不足**；照 `registration.md` 2026-11-03 量測追加三條 ①，7.5 檢查點（2026-12-22）把寫入前的逐句核對修法提給使用者，結果不改任何候選狀態。上一行（688020.SS）已是第 10 份、7／10，當時沒宣告，本行補上
- 2026-11-12 晚｜（標記，不是抽樣）判讀線過線後修法上線：寫入前逐句核對 `python -m alpha brief-check`（failure log #163）。2026-11-13 起每一行加一欄：抽到的那一版有沒有核對紀錄（`fc_…`／「未核」）；核過與未核分開判（`registration.md` 2026-11-12）

### ③ 影子重寫一致率（月份｜5 份｜候選狀態一致 N／5｜X 或已定價結論一致 M／5）

- （尚無）
