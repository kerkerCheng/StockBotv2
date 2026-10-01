# Phase 4 Step 4.8 研究收據（2026-10-01，互動 session、強模型）

> plan §9。每件都走正式入口；撞到 pq2 就掛號、接著做下一件。寫 `library/` 前已取得互動 writer lock。
> **入圖（graph admission）一件都沒有自己做**——四件掛 pq2 等使用者 `go`。

## 總表

| # | 對象 | lead | 掛號 | 研究包 | 現在的終局 |
|---|---|---|---|---|---|
| 1 | `mat:inp_substrate`：Reuters 2026-06-11 報導宣告 `origin_linkage=independent` | （資料工，plan 不要求鑄 lead） | pq2 **[666]** `ra_admission` | `ra_b98730bb2721d909a9cf3f3746fec135`（更正走廊，只改 `source_doc` 兩欄） | 等 go |
| 2 | `tech:cw_dfb_laser` 的層文件 | `lead_198ada57ea4366384b6e4f9855826998`（`directed:phase4-plan-4.8`，plan 點名、非走圖命中） | pq2 **[668]** `ra_admission` | `ra_637a70ee0dfd81040f59f834bce574e6`（更正走廊＋`layer_enumerations`，`origin_role=industry_report`） | `action_prepared`，等 go |
| 3 | 走圖第 2 型 AMAT → `tech:semiconductor_manufacturing_equipment` | `lead_656e8e10664835d242e6985cd8354dbc` | pq2 **[665]** `manual` | `loader/manifests/semi-equipment-lam-supply-20261001.json`（dry-run：1 邊） | `action_prepared`，等 go |
| 4 | 走圖第 2 型 COHR → `tech:six_inch_inp_production` | `lead_21765850ffd25e34a02986223be82825` | pq2 **[664]** `manual` | `loader/manifests/cohr-six-inch-axt8k-corroboration-20261001.json`（dry-run：1 邊） | `action_prepared`，等 go |
| 5 | `prod:supernova` 插槽讀圖 stale → 重讀；SIVE.ST 敘事換版 | — | — | 讀圖 `sr_d85d672998445c50`（取代 `sr_268d2fd79db629ff`）；敘事 `ib_457146d29ad50ef0`（取代 `ib_cb5642b674f08e14`） | **已寫入**（A3，不 gate） |

## 1. Reuters 的 `origin_linkage`（[666]）

- 讀自家庫的抽取檔與原文摘錄：s2（不具名業內人士：Coherent 主要由 AXT 供貨、Lumentum 主要由住友與 JX 供貨、換供應商要很長的認證週期）、
  s3（市占：AXT 與住友合計近八成、JX 約一成）、s5（SemiAnalysis 分析師）是 Reuters 自己採訪得來；s1（AXT 五月說的話）、s6（Coherent CEO）
  是轉述公司自己的說法。宣告是文件層級，依多數內容判 `independent`。
- packet 的 L8 註記寫明：`co:axt supplies_to co:coherent` 真正撐住印證的是 s2，不是 s1（同源轉述）。
- go 之後：掛在這份文件的 11 條斷言裡，引文具名供應商的那些由「媒體轉述」升為外部印證；層計數 ② 不變（`mat:inp_substrate` 在 4.3 已計入）。

## 2. CW DFB 雷射層的層文件（[668]）

- 先 grep 自家庫（L11-4）：全部抽取檔裡「提到 CW 雷射、又同句具名 ≥2 家供應商」的逐字只有一筆——Global Semi Research 2026-06-10 的 s4：
  「Nvidia's guidance to Coherent and Lumentum for high-power CW lasers climbed from roughly 40 million units in January to about
  100 million units by April and May」。GSR 已登記為產業研究發布者（非供應商 origin），這句目前只掛在公司層級的 `supplies_to co:nvidia`。
- 研究包在同一份文件補兩條 `supplies_to tech:cw_dfb_laser`（逐字不動），packet 的層列舉核對：兩家「引文具名 ✓」、發文者「登記的發布者（industry_research）」。
- go 之後：Coherent、Lumentum 兩條供貨邊由自報升為外部印證；層計數 ② 這一層 +1。
- 缺口：LandMark／LuxNet／VPEC／Sivers 仍沒有非供應商的列舉；這句講 Nvidia 給兩家的量，不是市占。
- **撤回兩筆自己剛提的提案**（使用者未看過）：先以 additions manifest 掛了 [667]，對照結案驗收（要 applied RA 帶 `layer_enumerations`、
  經 4.2 apply 入口與戳記）改走 RA；第一次凍結的 `ra_b6ee03d5e814b88979ff920482853c95`（[669]）packet 把 GSR 印成「解析不到」——
  4.2a 的層列舉核對沒有走 4.3 的 origin 解析 owner（L16，已當下修，見下），同一 payload 重新凍結為 [668]。[667]、[669] 都已 drop 並寫明理由。

## 3. AMAT：半導體製造設備層（[665]）

- 客戶端具名列舉**查過、不存在**：GlobalFoundries 2026-02-27 20-F 全文（SEC 原文，約 66 萬字）沒有具名任何一家設備商——
  只有「from a limited number of suppliers」。這是讀過全文之後的「沒有」，不是「找不到」（L11-5）。
- 自家庫 Lam 10-Q（2026-04-23）既有逐字 s4：「Lam Research Corporation is a global supplier of innovative wafer fabrication
  equipment and services to the semiconductor industry.」→ additions manifest 補 `co:lam_research supplies_to` 這一層（逐字不動）。
- TEL、ASML、KLA 不在名冊——要入圖得先 onboard，本包不含。plan 提的「GF 需求邊改指更細節點」不做：GF 那句講的就是泛稱設備。
- go 之後：這一層由 1 家變 2 家、走圖第 2 型 AMAT 那筆命中消失、層計數 ① −1。兩家都是自報（各自的申報）——回答的是「不是獨家」，不是外部印證。

## 4. COHR：6 吋 InP 量產層（[664]）

- 先查自家庫：AXT 2026-07-02 8-K（origin AXT，交易對手）的 s2「mass development and supply … 6-inch indium phosphide (InP) wafer
  substrates from AXT to Coherent」、s3「a prepayment of US$22,288,500 from Coherent to AXT」——交易對手的一手指名 Coherent 在做 6 吋 InP 量產。
- additions manifest 在同一份抽取檔補 `co:coherent supplies_to tech:six_inch_inp_production`（逐字不動）。
- 注意：那份 8-K 在圖上有兩份 SourceDoc（`axti_8_k_20260702_coherent_inp_supply`、`axti_8k_coherent_msda_2026_07_02`）——本包不合併，只掛在前者。
- go 之後：Coherent 那條供貨邊多一份交易對手來源、走圖第 2 型 COHR 那筆命中消失、層計數 ① −1。
  缺口：只回答「證據只有它自己說」，沒回答「是不是只有 Coherent 一家做 6 吋 InP」。

## 5. SuperNova 插槽重讀與 SIVE.ST 敘事換版（已寫入）

- stale 的原因是 4.3 的同級標籤拆分（供貨邊證據由「待判定」改成「媒體轉述」；plan §14 #17）。重讀判讀仍是 **undecided**，
  把 9-25 之後的圖況寫實：插槽主人 `co:ayar_labs develops prod:supernova` 已入圖（9-25 的缺口②消解）、供給側仍只有 Sivers、
  客戶端一手仍 0 份、需求錨仍走不到；反向證據（The Next Platform）的 Lumentum 那段已追到 2022-03-09 聯合新聞稿，但只在公司層級
  （`co:lumentum supplies_to co:ayar_labs`，原文沒寫 SuperNova）。四條反證延續（第二條補上 Lumentum 已追到的那段）：
  watch 被取代收掉 4、新登 4。
- SIVE.ST 敘事押的 SuperNova 讀圖換版 → 敘事換版只改那一個 ride 指標，七格、反證、answers、候選狀態不變（watch 連結既有 5、新登 0）。
- 刷新後：走圖「讀圖該重讀」1 → **0**；讀圖彙總 現行 2／stale 0；候選板 SIVE.ST 仍是「已持有」、可開 0（可開為零就零）。
- plan 一併提到的 `prod:els_8ch_module` 插槽讀圖仍是現行，不重讀；AXTI 押的 `mat:inp_substrate` 層讀圖 stale_low，照 plan 不動。

## 研究途中撞到、當下修的兩個機制缺口（L17）

1. **走圖第 2 型的記憶漏了 `action_prepared`**：4.5a 借用第 5 型的「正在研究」狀態組（triaged_go／researching），研究包掛 pq2 等 go 的
   lead 不旁印——下一個 session 會在同一筆命中旁重鑄。改用 `OPEN_LEAD_STATUSES`（多 `action_prepared`），第 5 型那組不動。
   真實資料：AMAT、COHR 兩筆命中旁 `open_lead` 由 `[]` 變成各自的 lead id。
2. **packet 層列舉的 origin 解析沒走唯一 owner**：4.2a 只認名冊公司，登記的發布者印成「解析不到」；改走
   `query.origin_resolution.resolve_origin`，packet 印「登記的發布者（類別）」；舊收據沒有新欄位的照舊渲染。

## L11-6 ④ 與計數器

- 走圖第 2 型兩筆命中、層計數 ① 75、② 5 層、③a 102／113 **都要等 go 入圖後才會動**——今天的讀數不變。
  go 之後預期：① 75 → 73（AMAT、COHR 兩筆）、② 5 → 6 層（cw_dfb）、第 2 型命中 2 → 0、心跳段 3 的較昨 diff 會出現這兩行。
- SIVE.ST 候選板狀態當天沒變（已持有；可開 0）。

## 等使用者決定

| 編號 | 一句話 | go 會讓哪個數字變 |
|---|---|---|
| [664] | AXT 8-K 當 Coherent 6 吋 InP 量產的外部印證（同文件既有逐字） | 第 2 型命中 −1、① −1 |
| [665] | Lam 也供半導體製造設備這一層（Lam 自己 10-Q 既有逐字） | 第 2 型命中 −1、① −1 |
| [666] | Reuters InP 報導宣告 independent | 該文件 11 條斷言裡具名供應商的升外部印證 |
| [668] | GSR 同一句具名 Coherent 與 Lumentum 供 CW 雷射（層文件） | cw_dfb 兩條供貨邊升外部印證、② +1 |

（另有 4.2 留下的 [663]：圖上 11 份 SourceDoc 的 title 對齊抽取 JSON。）
