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
- 逐則（registration §6 第 5 項的欄位；類型與裁決都是封閉字彙）：

| # | symbol | lead id | 主張原文 | 類型 | 一手文件與 `published_at` | 帳號發文日 | 系統接觸日 | 其他管道最早 `first_seen` | 價格（點名 → 一手） | 裁決 | `hy_*`／到期 |
|---|---|---|---|---|---|---|---|---|---|---|---|

- 摘要（7.1 收尾寫；H6 的量法）：（尚無）
- failure log：（尚無）

## P1 345／765 kV 超高壓變壓器

- 登記：registration §2 P1（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜開題稽核 pq2 **[685]**（使用者 Q2 選題，受理即 resolve，收據 `authority:plan_approval`）
  - 2026-10-04｜**decompose 收據**（system-decompose；不入圖、不提高 tier）——系統：資料中心變電站用 345 kV 級大型電力變壓器（LPT）；選題理由：plan §0.1 Q2「電力（超高壓變壓器與它的上游：電工鋼、套管、分接開關、測試產能）」；一手來源：DOE《Electric Grid Supply Chain Review: Large Power Transformers and High Voltage Direct Current Systems》（2022-02，政府報告，tier 1；對供應商而言是第三方）。拆出 11 層：GOES、鐵芯疊片、CTC 銅導線、絕緣紙板、絕緣油、套管、有載分接開關、儲油櫃／膠囊、整機製造、出廠測試（試驗台）、運輸（最後 5–10 英里）。DOE 點名的兩大瓶頸是 GOES 產能與 LPT 測試產能（p.20–21）；「Imports account for 82% of the consumption of LPTs in 2019」。三題：幾家能做——GOES 全球 13 家、達 DOE 規格只有日韓德；分接開關美國 3 家＋德國 1 家（未具名）；套管、絕緣材料美國各少數幾家；其餘未知。換掉要多久（合格）——全部未知（DOE 給的是交貨週期，不是合格週期）。客戶資本承諾——全部未知。⚠ 這份是 2022 年的快照（AI 資料中心需求之前），2026 年現況要另找一手。對照圖：圖上 0 個變壓器／電工鋼／分接開關／套管／變電站節點，名冊 0 家——**收斂：拆出 11 層｜✅ 0｜🟡 0｜🔴 11**
  - 2026-10-04｜研究題目（pq1，`decompose:lpt-345kv-2026-10-04`，triaged_go）：lead_7b63986b（LPT 整機：進口來源、交期、客戶端資本承諾）；P2 的五題見下
- 主題等權組（電力；必須早於本鏈第一份敘事）：（尚無）
- 裁決：（尚無）
- 2×2：尚未到裁決點
- failure log：（尚無）

## P2 變壓器上游：電工鋼、套管、分接開關、測試產能（二階）

- 登記：registration §2 P2（開題 2026-10-04）
- 研究產出：（尚無）
  - 2026-10-04｜decompose 收據見 P1（同一次拆解）；本段的研究題目（pq1，triaged_go）：lead_21b7830d（GOES）、lead_188e1fa1（測試產能）、lead_e0948fc0（有載分接開關；德國那一家要具名）、lead_857be4a6（高壓套管）、lead_bf2fb4a7（CTC 銅導線）
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
