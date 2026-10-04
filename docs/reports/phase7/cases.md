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

---

## O1 AXTI／InP 基板

- 登記：registration §2 O1（開題 2026-10-04）
- 研究產出：（尚無）
- 裁決：（尚無）
- 2×2：尚未到裁決點
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
- failure log：（尚無）

## O4 AAOI

- 登記：registration §2 O4（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜lead_cad23eb9 park（`original_obtained`）：AAOI 424B5（2026-08-21）逐字「aggregate offering price of up to $600,000,000」、前一份 Equity Distribution Agreement 2026-05-14；Engine C `equity_offering_filings` 已收四份 424B5（02-26、03-12、05-14、08-21）——稀釋燈本來就有輸入，不是圖增量（預期的 failure mode「稀釋」照實出現，不是裁決）
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
- failure log：（尚無）

## O6 光通訊磊晶與 MOCVD 產能（二階）

- 登記：registration §2 O6（開題 2026-10-04）
- 研究產出：（尚無）
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
- failure log：（尚無）

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
- 主題等權組（電力；必須早於本鏈第一份敘事）：（尚無）
  - 2026-10-04｜還不能定：照光通訊組的選員準則（主業就是這一層、名冊解析得到、有價格歷史；需求端與綜合集團不入組），名冊上的電力鏈上市公司只有曉星重工（298040.KS）合格——Cleveland-Cliffs（CLF）主業是汽車用鋼、電工鋼只是業務之一（判斷，未量化占比，同住友電工被排除的理由），IREN 是需求端。合格 1 家、不到 2 家下限；等 lead_7b63986b 等供給側研究把 LPT／開關設備的上市供應商補進名冊再定（本鏈還沒有敘事，前瞻要求仍守得住）
- 裁決：（尚無）
- 2×2：尚未到裁決點
- failure log：（尚無）
  - #9（11 條 decompose 題目缺分類被 drain withheld；回填腳本吃不下 `triage: None`——當下修）
  - #11（[689] IREN 的 depends_on 印 self_reported_costly——買方自述被當成供應商自報；與 C1 [694] 同形）

## P2 變壓器上游：電工鋼、套管、分接開關、測試產能（二階）

- 登記：registration §2 P2（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜decompose 收據見 P1（同一次拆解）；本段的研究題目（pq1，triaged_go）：lead_21b7830d（GOES）、lead_188e1fa1（測試產能）、lead_e0948fc0（有載分接開關；德國那一家要具名）、lead_857be4a6（高壓套管）、lead_bf2fb4a7（CTC 銅導線）
  - 2026-10-04｜補一題 lead_de46bc48（變壓器絕緣材料；買方端一手：Forgent S-1「we rely on a single supplier for certain specialized insulation material used in our transformer products」）；[687] 把 GOES、CTC、分接開關、套管、絕緣材料、測試產能六個上游層建成節點（供給側只有 GOES 一家美國廠，其餘零供應商＝走圖的洞）
  - 2026-10-04｜pq1 drain 第一條 lead_21b7830d（GOES）→ `ra_a4864a6a92163da08b4f6eb529081fab` → pq2 **[691]**：JFE 2025-08-04 新聞稿（JSW JFE 印度合資：前 thyssenkrupp 印度廠、5 萬 → 25 萬噸／年 2028–2030，另一廠 10 萬噸 2027）＋Cliffs 2026 Q2 10-Q（產品清單逐字含 GOES；「Transformers are in short supply … exacerbated by the anticipated widespread adoption of AI」）；名冊三筆隨包（合資 null、co:jfe_holdings 5411.T、co:jsw_steel JSWSTEEL.NS）。查無一手：題材掃描說的 Cliffs Weirton 變壓器廠（10-Q 只有 Weirton tinplate 停產）、現代製鐵 2026-04 北美 GOES 協議（只見市場研究稿、韓文新聞 0 則）。**對 H5 (ii) 的初步證據：GOES 供給側是鋼鐵巨頭（Cliffs、JFE、JSW）與私人合資，沒有看到非共識、可投資的標的**（7.4 寫結論）；美國 LPT 用的 DOE 規格級 GOES（日韓德）的具名廠商與其美國客戶仍未入圖
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
- failure log：（尚無）
  - #9（同 P1）
  - #10（[691] 合資股東的新聞稿被分類成外部印證；與 C1 [690] 同形）

## P3 800VDC 擱置五則回看

- 登記：registration §2 P3（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜（給 7.4 的指向，不是裁決）NVIDIA 部落格「NVIDIA, Partners Drive Next-Gen Efficient Gigawatt AI Factories in Buildup for Vera Rubin」（blogs.nvidia.com，2025 OCP）逐字列 800 VDC 夥伴——silicon：ADI、AOS、EPC、Infineon、Innoscience、MPS、Navitas、onsemi、Power Integrations、Renesas、Richtek、ROHM、STMicroelectronics、Texas Instruments；power system components：BizLink、Delta、Flex、GE Vernova、Lead Wealth、LITEON、Megmeet；data center power systems：ABB、Eaton、GE Vernova、Heron Power、Hitachi Energy、Mitsubishi Electric、Schneider Electric、Siemens、Vertiv。是客戶端（平台方）的生態名單——對五則的 park 理由（例：「ecosystem membership is not a supply contract」）正好是那個理由描述的東西，回看時要分清「名單」與「供貨」
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
  - 主題等權組：還沒定——組員要能在名冊解析（INV-1），台股散熱公司目前 0 家在名冊；組員等選源找出各層坐了誰再定（仍早於本鏈第一份敘事）
- 主題等權組（散熱；必須早於本鏈第一份敘事）：（尚無）
- 裁決：（尚無）
- 2×2：尚未到裁決點
- failure log：（尚無）
  - #9（同 P1）
  - #10（[690] CoolIT 的兩條供貨邊印 externally_corroborated——文件是收購方 Ecolab 發的）
  - #11（[694] NVIDIA 自己的 depends_on 被預告成「供應商自報」——買方自述與供應商自誇共用一個值）

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
- failure log：（尚無）

## X3 漏網稽核（R3）

- 登記：registration §2 X3、§5
- 報告：第一次（窗口 2026 Q3）（尚無；`replay-r3-missed-q3.md`）；第二次（7.5）（尚無）
  - 2026-10-05｜第一窗 [`replay-r3-missed-q3.md`](replay-r3-missed-q3.md)：58 檔全有價格、光通訊組 Q3 等權 +1.0%、前四分之一 15 檔。**照官方比對法「系統沒有接觸」6 檔：健策（+101%）、雙鴻（+51%）、奇鋐（+32%）、南亞科（+24%）、上詮、英特磊**——後兩檔是比對法的問題（上詮 08-24 X 帳號與 08-25 decompose 的 lead 沒有公司身分；英特磊 09-17 已經年報進圖、09-30 入組，但定義不含「進圖」「入組」）；**窗口內接觸卻沒研究 8 檔**（全新 09-17 park、LandMark 讀圖 09-17〔字串比對另見 08-26 中央社〕、晶豪科 08-27 X 帳號反覆點名後 park、華星光 09-24 park、LITE、AXTI、IQE、韓美）；窗口後才接觸 1 檔（CLF，10-04 電力鏈開題）。「接觸早於窗口起點」第一窗無法觀測（lead registry 07-22 開機，晚於窗口起點 07-01）
  - 7.5 failure log 候選（不是條目）：健策、雙鴻、奇鋐（散熱：Q2 選題前沒有任何管道）、南亞科（記憶體：「刻意不做」的代價）
- failure log：（尚無）
  - #13（lead 實體不隨名冊重算：LandMark、上詮照官方比對法變成「沒有 lead」）

## X4 history lane 輸家驗屍（R4）

- 登記：registration §2 X4、§7.4
- 報告：（尚無；`replay-r4-losers.md`）
  - 2026-10-05｜[`replay-r4-losers.md`](replay-r4-losers.md)：**AEVA、MP、Lynas、Nidec、JL Mag 五檔全部「證據不足以判」**——入圖後到 10-02 沒有任何一手回頭碰到入圖時的結構主張（AEVA、MP 在 EDGAR 入圖後 0 份非內部人申報；Lynas 入圖後唯一的一手是 10-01 換股收購 Meteoric——資本配置；JL Mag 只有股東會與股息公告；Nidec 入圖時唯一一條 assertion 沒有發表日、投影是空的）。不構成 H1／H3 的反例。描述（不判讀）：三檔稀土同期一起跌；MP 客戶資本承諾最齊全仍 −20%（窗口太短，不進 H10）；JL Mag 入圖時的證據全是 2022 年報
- failure log：（尚無）
  - #14（反證以被評公司的供貨 assertion 形式入圖：MP 磁材邊上的 Noveon、USA Rare Earth 文件，引文沒有 MP）
