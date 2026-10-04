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
- 付錢方向（H10）：供應商掏錢（登記時已知）
- 裁決：（尚無）
- 2×2：尚未到裁決點
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
- 主題等權組（電力；必須早於本鏈第一份敘事）：（尚無）
- 裁決：（尚無）
- 2×2：尚未到裁決點
- failure log：（尚無）

## P2 變壓器上游：電工鋼、套管、分接開關、測試產能（二階）

- 登記：registration §2 P2（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜decompose 收據見 P1（同一次拆解）；本段的研究題目（pq1，triaged_go）：lead_21b7830d（GOES）、lead_188e1fa1（測試產能）、lead_e0948fc0（有載分接開關；德國那一家要具名）、lead_857be4a6（高壓套管）、lead_bf2fb4a7（CTC 銅導線）
  - 2026-10-04｜補一題 lead_de46bc48（變壓器絕緣材料；買方端一手：Forgent S-1「we rely on a single supplier for certain specialized insulation material used in our transformer products」）；[687] 把 GOES、CTC、分接開關、套管、絕緣材料、測試產能六個上游層建成節點（供給側只有 GOES 一家美國廠，其餘零供應商＝走圖的洞）
- 結論（H5 的 (i)(ii)，7.4 寫）：（尚無）
- failure log：（尚無）

## P3 800VDC 擱置五則回看

- 登記：registration §2 P3（開題 2026-10-04）
- 研究產出：（尚無）
- 逐則（park 理由今天站不站得住；H2 的「證實」定義）：（尚無）
- failure log：（尚無）

## C1 液冷台股供應商

- 登記：registration §2 C1（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜開題稽核 pq2 **[686]**（使用者 Q2 選題，受理即 resolve，收據 `authority:plan_approval`）
  - 2026-10-04｜**decompose 收據**——系統：GB300 NVL72 機櫃的直接液冷迴路；選題理由：plan §0.1 Q2「散熱（小規模，台股液冷）」；一手來源：Lenovo Press LP2357（2026-08-30，整機廠規格書：「The liquid cooling solution consists of a CDU, rear manifold, quick disconnects, and cold plates for the CPUs, GPUs, ConnectX-8 network adapters, and all NVSwitch components」——WebFetch 摘要轉出，入圖前要逐字重核）、OCP 產品目錄（UQD 開放規格，至少 7 家上架）。拆出 6 層：冷板、機櫃後置 manifold（304L／316L）、快接頭（UQD／UQDB）、CDU（液對液熱交換＋泵）、冷卻液（去離子水／PG25，大宗品）、廠務水側。三題：幾家能做——快接頭 OCP 目錄至少 7 家（SITELIN、CEJN、Stäubli、JPC、Parker、BEEHE、Danfoss Hansen），其餘未知；換掉要多久、客戶資本承諾——全部未知。對照圖：只有泛稱的 `tech:thermal_solutions`（Coherent 一條邊，指光模組熱管理），冷板／manifold／快接頭／CDU 都沒有；名冊 0 家台股散熱公司——**收斂：拆出 6 層（冷卻液不出題）｜✅ 0｜🟡 0｜🔴 5**。⚠ 先入為主的風險（登記的 failure mode）：快接頭「開放規格＋多家上架」支持 08-29 的「競爭層」結論，題目刻意寫成找反例（NVIDIA 指定的盲插件有幾家通過）
  - 2026-10-04｜研究題目（pq1，`decompose:gb300-nvl72-dlc-2026-10-04`，triaged_go）：lead_5b8cc7e2（冷板）、lead_1345d45b（manifold）、lead_6698f145（快接頭）、lead_f96bfb99（CDU）
  - 主題等權組：還沒定——組員要能在名冊解析（INV-1），台股散熱公司目前 0 家在名冊；組員等選源找出各層坐了誰再定（仍早於本鏈第一份敘事）
- 主題等權組（散熱；必須早於本鏈第一份敘事）：（尚無）
- 裁決：（尚無）
- 2×2：尚未到裁決點
- failure log：（尚無）

## X1 已定價回放（R1）

- 登記：registration §2 X1、§7.2
- 報告：（尚無；`replay-r1-priced.md`）
- failure log：（尚無）

## X2 parked 回查（R2）

- 登記：registration §2 X2、§7.3（樣本 36 則＝registration 附錄 C）
- 報告：（尚無；`replay-r2-parked.md`）
- failure log：（尚無）

## X3 漏網稽核（R3）

- 登記：registration §2 X3、§5
- 報告：第一次（窗口 2026 Q3）（尚無；`replay-r3-missed-q3.md`）；第二次（7.5）（尚無）
- failure log：（尚無）

## X4 history lane 輸家驗屍（R4）

- 登記：registration §2 X4、§7.4
- 報告：（尚無；`replay-r4-losers.md`）
- failure log：（尚無）
