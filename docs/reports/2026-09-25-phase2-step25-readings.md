---
date: 2026-09-25
topic: phase2-step25-readings
plan: docs/plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md
step: 2.5
kind: research-receipt
---

# Phase 2 Step 2.5 — 第一份插槽讀圖、InP 基板重讀、兩個插槽試跑（研究收據）

**這是研究收據，不是開發報告。** 讀圖 ledger 在 `library/private/`、不進 git，所以寫了什麼、憑什麼、登記了哪些等待，都以本檔為準。
本檔數的是**讀圖 ledger 的紀錄與引用、等待 registry 的計數、工具在真實資料上的輸出**；沒有任何一個數字是「幾檔通過某個 filter」。

一句話：**第一份插槽讀圖寫進去了，判 undecided——而且讀完之後，方向上反證多於確認。**
過程中工具在真實資料上現形三個毛病（當下修掉，偏差 #7–#9），圖上現形兩件要動圖的事（提 pq2 [651]、[652]，沒有改圖）。

---

## 1. 收據：寫進 ledger 的四份讀圖

| 節點 | 單位 | 判讀 | reading_id | 取代 | 引用（需求側／供給側） | 反證（沿用／新寫） | 語意 watch 登記／收掉 |
|---|---|---|---|---|---|---|---|
| `prod:supernova` | **socket** | undecided | `sr_268d2fd79db629ff` | — | 1／1 | 0／4 | 4／0 |
| `prod:els_8ch_module` | **socket** | undecided | `sr_35ca0ce58617d5f6` | — | 1／1 | 0／3 | 3／0 |
| `mat:inp_substrate` | layer | volume | `sr_bac985bacbea64b7` | `sr_ad503ae880ceb398` | 8／4 | 4（出處 `sr_ad503ae880ceb398`）／3 | 7／6 |
| `tech:cw_dfb_laser` | layer | volume | `sr_d49b81b6465e1181` | `sr_d07679979a8e4202` | 3／5 | 4（出處 `sr_a181641ddb99c69c`）／2 | 6／5 |

- 四份都是 v3；寫入前都用同一條路徑乾跑過（`structure_reading_record` ＋ `verify_citations` ＋ `verify_disproof_sources`，不 append），問題 0 才 `--add`。
- 寫完後四份 `--check` 全部 **current**；`python -m webapp materialize --structure-readings`：現行 4／stale 0／過期 0／該重讀 0；心跳段 2「結構讀圖 4 份｜現行 4｜該重讀 0」。
- ledger 10 行 → 14 行；解析失敗 0 行（既有 v1／v2 十行一個字沒動）。
- `tech:cw_dfb_laser` 這份是 plan §6 第 5 點的選做：它 10-18 到期，而且 **Phase 1 待決 #19（前一份的五條反證逐字搬自 `sr_a181641ddb99c69c`、沒有出處）在這份解決**——四條沿用的反證逐條標回 `sr_a181641ddb99c69c`。

## 2. 驗收（plan §6 與 §11；每個數字註明層）

| 驗收 | 前 | 後 | 層 |
|---|---|---|---|
| ROADMAP ①：ledger 裡 `unit=socket` 的紀錄 | 0 | **2** | 讀圖 |
| `mat:inp_substrate` 的層讀圖狀態 | stale（Step 2.2 預期） | **current** | 讀圖 |
| 語意 watch（`semantic_active`） | 27 | **36**（登記 20、被取代收掉 11） | registry |
| active watch 總數 | 114 | 123 | registry |
| 叫不醒（`semantic_unreachable`） | 2 | **3**（新增 2，見 §4.5） | registry |
| A2：現行 v3 的 moat／volume 兩半引用都核對得到 | —（0 份 v3） | **2／2**（InP、CW DFB） | 讀圖 |
| A1：現行讀圖按單位 | 層 2 | 層 2、插槽 2 | 讀圖 |

查證：`python -m engine_b.event_watch counters`（前後各跑一次，前值存在本 session scratchpad）；`python -m alpha structure-reading <node> --check`。

## 3. 三個產品在工具上顯示了什麼

### 3.1 `prod:supernova`（Sivers × Ayar，決定紀錄 §4.3 點名的插槽）

工具照實印出三個缺口：供給側只有一條、唯一原文是 tier 3 substack（origin 解析不到）；製造者「分不出」；需求錨走不到。依 A2 它**不能**寫成護城河——乾跑一份 `kind=moat`、把那段 substack 標 `independent=true`，寫入端拒收：「origin_entity ['silicon_matter_substack'] 解析不到任何 co:*」（§5）。

讀了以後的判斷（寫在讀圖裡）：
- **自家庫已有、但不在這一格的證據**：Sivers 2024-09-19 ECOC 新聞稿（tier 2，內含 Ayar CTO 具名）逐字寫 Sivers 16 波長陣列整合進 Ayar 第二代 SuperNova——**它在圖上，但掛在 `co:sivers_semiconductors supplies_to tech:wdm_laser_16ch`**；2023 年 1 百萬美元訂單掛在 `supplies_to co:ayar_labs`。這一格的證據散在三個節點，沒有一個節點看得到全貌。
- **圖外反向證據**：The Next Platform 2026-03-04（第三方，tier 3）寫 Lumentum、Coherent 與住友是 Ayar SuperNova 外部光源的雷射晶粒供應商，全文沒提 Sivers。
- **圖外確認端**：Sivers 2024-12-19 新聞稿引 Ayar CEO：以 NRE 與預購擴大關係、18–24 個月內放量；沒提 SuperNova。
- 2026-09-17 [588] 已記：Ayar 現行網站查不到任何具名 Sivers 的頁面。
- 判 undecided；**方向上反證多於確認**。四條確認／推翻條件已登記成 watch。三件要動圖的事提 **pq2 [652]**。
- ⚠ audit `PointInTime` 列出這份 substack **沒有 `published_at`**（擋住 3 條邊的 as-of 查詢）——這一格唯一的原文在任何 as-of 查詢裡都被排除。

### 3.2 `prod:els_8ch_module`（O-Net 的 ELS × Sivers 雷射陣列）

- 需求錨走得到（`tech:ai_switch → tech:cpo → 本節點`）——這是 SuperNova 沒有的。
- **產品節點的供給側把製造者與不同格子混在一起**：三條 `supplies_to` 其實是 O-Net（整合者＝製造者）、Sivers（雷射陣列那一格）、Enablence（star coupler 那一格）。A／B 判準比的是同一格的供應商，所以 sub 分布在這裡沒有意義。R-4 的兩義在這裡多一層：不只分不出製造者，也分不出格子。
- **工具毛病（已修，偏差 #9）**：拿同插槽另一家供應商 Enablence 發的聯合新聞稿標 `independent`，寫入端原本**放行**了一份 Sivers 的插槽護城河（§5）。
- 判 undecided，三條條件登記成 watch。

### 3.3 `prod:ph18da`（Tower × OpenLight）——沒寫讀圖

工具的輸出是對的（製造者「分不出」；客戶端原文認出 OpenLight 的一手新聞稿），但**插槽這個單位套不上它**：逐字寫「Tower Semiconductor’s PH18DA … platform」與 OpenLight「its PH18DA … developed in collaboration with Tower」——PH18DA 是一個代工製程平台，不是「客戶的產品裡的一格」。`prod:` 節點同時裝著客戶產品、供應商的型錄產品與製程平台（又一個一表多義），插槽單位只對第一種有意義；判斷「這個 prod: 是不是插槽」目前只能靠人讀逐字。
它的需求側只有一家（NewPhotonics，tier 3），值不值得讀成一層，等 R-4 修正（[651] 提案 Tower 與 OpenLight 都改 `develops`）之後再看。

### 3.4 工具毛病：在真實資料上現形、當下修掉的三個

| # | 毛病 | 真實資料上的樣子 | 修法 | 測試 |
|---|---|---|---|---|
| 偏差 #7 | 反向路徑「消失」與「新增」共用一個 kind，都標「同時是 disproof 觸發」 | `mat:inp_substrate --check`：「消失 1 條：co:iqe→mat:inp_substrate｜**同時是 disproof 觸發**」，心跳照數 | `counter_path_removed`（normal、不是觸發）；與 `supply_removed` 對稱（L17-3） | `test_counter_path_added_is_a_disproof_trigger_but_removed_is_not` |
| 偏差 #8 | `query.structure --quotes` 每條邊只印 3 段、每段切 200 字，**不說**；同文件同段重複印 | InP 基板 `co:lumentum` 那條邊 11 段只印 3 段，藏掉的是 Lumentum 10-K 與 Q4 法說「又向 AXT 找基板」——判斷供給側可不可替代的客戶端原文；CW DFB 藏 7 段 | 超過 3 段印「另有 N 段逐字沒印，出自哪幾份」、切斷處加「…」；取逐字時去掉同文件同段的重複 | `test_the_same_quote_from_the_same_doc_is_kept_once_per_edge`、`test_quotes_reach_the_reader…` 加三條斷言 |
| 偏差 #9 | 寫入端 `independent` 只排除「那條邊的供應商」（plan 待決 #12） | ELS 用 Enablence 新聞稿標 independent → 放行 | 插槽排除**該插槽所有供應商**（與插槽視角的「客戶端原文」同一定義）；層不變 | `test_independent_on_a_socket_excludes_every_supplier_of_that_socket` |

digest 沒有受影響：逐字與變化分級都不進 `result_digest`；四份讀圖寫完後 `--check` 全部 current。

### 3.5 看到但沒修（記進 plan §14 待決）

1. **插槽的客戶重讀 watch 登記 0**：`demand_side_customers()` 只收需求側的 `co:*`；SuperNova 的需求側是 `prod:teraphy_chiplet`、ELS 的是 `tech:cpo`，所以 Ayar／O-Net 出新文件叫不醒這兩格。R-4 修好之後，插槽的客戶其實是**製造者**（`develops`），那才是該綁的實體。
2. **兩條新 watch 叫不醒**：`ew_0138`（SuperNova ④，只綁私人公司 `co:ayar_labs`）、`ew_0140`（ELS ②，只綁港股 `co:o_net_technologies`）——沒有任何一手來源會為它們產出 lead。**沒有為了讓計數歸零去硬塞實體**；它們靠讀圖到期（2026-12-24）重問。要不要把 Ayar newsroom／HKEX 公告納入一手涵蓋面，是涵蓋面的決定。
3. **`classify_evidence` 把「支撐屬性值的引文」算成「印證這條邊存在」**（見 §4.3）。
4. **「客戶高管在供應商新聞稿裡具名」**（`counterparty_joint`）算不算插槽護城河要的客戶端印證：寫入端目前當成供應商自己。是契約問題，不是研究能解的。
5. **`prod:` 一表多義**（§3.3）。

## 4. 研究發現

### 4.1 `mat:inp_substrate`：3／3／3 第一次有客戶端原文

前兩份讀圖寫「沒有一段逐字在講客戶換不換得掉，3 憑的是市佔」。讀完整逐字（偏差 #8 修好之後才看得到），需求側的邊上其實有客戶自己講多源：
Coherent「we have multiple six-inch indium phosphide substrate suppliers」；Lumentum Q4 法說「we went out and we found additional substrate help from AXT」。反方向：Reuters「unlikely to switch suppliers easily … lengthy qualification cycles」。
合起來是**換不快，但加得了**——仍是 B。短缺的形狀也更清楚：Casela 預付 50% 換保留產能、Coherent 預付 US$22.3M 且保留解約權、AXT Q1 InP 積壓破 1 億美元（約季營收 7 倍）——**預付加解約權＝客戶在買量，不是被鎖住**。
政策面多一層：Lumentum 10-K「China restricted exports to Japan, which affected our substrate supply chain globally」——受管制衝擊的不只 AXT。反證 ⑤ 改寫為含原料與對美許可；新增 ⑦（客戶端改口單一來源）。
圖外：Digitimes 2026-06-15 標題「China eases InP substrate exports」，可見段落是在管制之下放行一批新貨，管制本身沒解除——⑤ 未觸發。

### 4.2 `tech:cw_dfb_laser`：Sivers 那條不是外部印證

前兩份讀圖寫「最低的 co:sivers_semiconductors 仍是外部印證」。那條邊唯一的非 Sivers 來源是華星光年報「本公司自 2019 年即與策略合作夥伴共同開發 CW DFB Laser 晶粒」——**年報全文 5,155 行（`library/raw/mops_4979_annual_report_2025.txt`）沒有一處寫出 Sivers**。那句是 2026-08-29 補 sub 時撐「這一層 sub=2」的研究判斷（`extractions/cw_dfb_substitutability_addendum_2026_08_29.json` 的 e2，同一句也掛在 `co:luxnet` 那條 e3）。
結論：**供給側六條沒有一條有客戶端或第三方印證**。判讀不變（B 不靠任何一家的外部印證），反證 ② 改寫為只認具名的印證。
另外完整逐字裡有反方向的量訊號：Lumentum 內製 CW 雷射下季約占兩成 transceiver——買家垂直整合會吃掉商用供應商（LuxNet、LandMark、VPEC、Sivers）的量，新增反證 ⑥。
⚠ 「華星光 sub=2 是對照組不改判」（2026-09-16）指的是 `co:luxnet` 那條邊，本輪沒碰任何 sub。

### 4.3 機制：一段 provenance 同時被當成「邊存在」與「屬性值」的證據（L12）

4.2 的根因不是那一筆抽取寫錯：`classify_evidence` 把掛在這條邊上、origin 不是主詞的**任何**逐字都算成外部印證，不管那段逐字是在證明「這條邊存在」還是在證明「某個屬性值」。層讀圖的判讀不受影響，但**插槽讀圖的供貨邊證據變動是 high**（Step 2.4），這個機制會讓插槽賭注的確認事件被一句不相關的話觸發。修它要動 `classify_evidence` 或 assertion 的 schema，是 Phase 4「層中心選源／substitutability 稽核」的範圍，記進 plan §14。

### 4.4 R-4 全圖盤點：真正的插槽只有 3 個，而且都是 Sivers 的

圖上有 `supplies_to` 進來的產品 13 個，逐條讀逐字：
- **10 個是製造者賣自己的產品**（AMAT ×2、NVIDIA ×3、POET ×2、Lam、Tower 的 PH18DA、IQE 的 QD 雷射磊晶片）；其中 POET→blazar 與 Lam→reliant 已經有 `develops`，`supplies_to` 是重複。
- **3 個是真正的零件進客戶產品**：`prod:supernova`、`prod:gf_scale`、`prod:els_8ch_module`——**三個都是 Sivers 的插槽**。插槽這個單位在圖上只存在於我們研究過的那一家（供應商計數＝研究深度，決定紀錄 §1.1 的同一個形狀）。
提案逐條寫在 **pq2 [651]**：10 個改 `develops`、補 `co:ayar_labs`／`co:globalfoundries` 的 `develops`、`co:o_net_technologies` 改 `develops`、PH18DA 補 `co:openlight develops`。go 只到研究包，入圖另取 `ra_admission`。
⚠ **這個提案在 go 之後被模擬推翻，改成「只加 develops」——見 §7。**

### 4.5 本 Step 鑄的 pq2

| 編號 | 內容 | go 授權 | 不含 |
|---|---|---|---|
| [651] | R-4：13 個產品裡 10 個的 `supplies_to` 其實是製造者——改 `develops`，補三個插槽的製造者 | 做成 ra_admission 研究包 | 入圖（另取編號）、讀圖改寫、schema 新關係、live |
| [652] | SuperNova 證據補齊：ECOC 2024 原文掛錯節點、Ayar CEO 預購引述未入圖、The Next Platform 反向證據追一手 | bounded research 到研究包 | 入圖（另取編號）、讀圖改寫、R-4、live |

## 5. 寫入端規則在真實資料上的乾跑（不 append）

| 案例 | spec | 結果 |
|---|---|---|
| SuperNova 寫成插槽護城河，substack 標 independent | `kind=moat`，引用同 §1 | **拒收**：「origin_entity ['silicon_matter_substack'] 解析不到任何 co:*」 |
| ELS 寫成 Sivers 的插槽護城河，Enablence 新聞稿標 independent | `kind=moat` | 修前：**放行**（problems []）；修後：**拒收**「是這個插槽的另一家供應商 ['co:enablence_technologies']」 |
| 四份正式讀圖 | 見 §1 | problems [] |

## 6. 沒做的事

- **沒有改圖**：[651]、[652] 都只是提案。
- 沒有為 PH18DA 寫讀圖（§3.3）。
- 沒有做 [652] 的追源；The Next Platform 那句是 WebFetch 摘錄，入圖前要逐字重核。
- 沒有追 Sivers 管理層「2027 年 production-ready」的一手（二手轉述，寫在 SuperNova 讀圖的圖外段，標明待追）。

## 7. 使用者 go [651]、[652] 之後（2026-09-25 同一 session）

使用者同時確認偏差 #9 的收緊。`go` 的語意是推進到下一道人工閘門；兩項都做到研究包，**沒有寫圖**。

### 7.1 [651]：原提案被推翻，改成「只加 develops」

準備研究包時先跑唯讀模擬（L11-6：這個修法若錯，最先壞哪一筆）：

| 修法 | digest 變動節點 | 失去需求錨的公司 | 結構表母體（公司→向下 sub≥4） |
|---|---|---|---|
| S1 改型別（[651] 原提案） | 13 | `co:nvidia` | 30 → 29（`co:tower_semiconductor → prod:ph18da` sub=4 消失） |
| S2 只加 `develops`（含 Sivers→SuperNova 重掛） | **0** | **0** | 30 → 30 |

原因：需求錨走訪與結構表都走 `supplies_to`、不走 `develops`；而對「供應商自己的產品／平台」（Blackwell、PH18DA…），`supplies_to` 的意思是「製造者賣這個東西」，
跟 `co:axt supplies_to mat:inp_substrate` 一樣，**並沒有錯**。R-4 的兩義真正的形狀是 `prod:` 一表多義（§3.5 第 5 點）——缺的只是「客戶產品」那幾格的製造者。

研究包＝`loader/manifests/r4-socket-makers-20260925.json`：8 份既有抽取檔新增 12 條（11 條製造者 `develops`＋Sivers→SuperNova 的 ECOC 原文重掛＝[652]①），
只引用各檔既有 sources、quote 一字不動。刻意不列 POET→Starlight（沒有逐字同時寫出兩個名字，L6）與 IQE→QD 雷射磊晶片（製造者說不清楚）。
工具：`loader/migrate_relation_rejudge.py --additions`（偏差 #10）；dry-run：files 8／edges_added 12／not_found []，每份改完都過 `loader/validate.py`。
**入圖閘門：pq2 [654]**（go＝備份→遷移→驗收全圖 digest 0 變動）。

### 7.2 [652]：Lumentum 那一半追到一手；Coherent、住友追不到

- **The Next Platform 原句逐字核對**：«laser makers Lumentum and Coherent (who along with Sumitomo are suppliers of laser dies to Ayar Labs for its SuperNova external light sources)»
  ——是作者插句，不是 Mark Wade 的引述；同文引述 Wade 的只有「the company is also buying semiconductor lasers and building its SuperNova remote light sources」。
- **Lumentum 部分追到一手**：Lumentum／Ayar 2022-03-09 聯合新聞稿（Lumentum IR）——Lumentum 以高量供應 CW-WDM MSA 外部雷射光源給 Ayar 的 optical I/O，
  Ayar CEO Charles Wuischpard 具名。**全文沒有 SuperNova**，依 L6 只入公司層級的 `co:lumentum supplies_to co:ayar_labs`。
- **Sivers 2024-12-19 新聞稿原文**（`python -m fetchers.mfn --url …`，JSON-LD datePublished 2024-12-19T07:49:17Z）：Mark Wade「Ayar Labs, a strategic customer of Sivers Semiconductors,
  **intends** to expand its relationship … through NRE and pre-purchase of products」；Sivers 自稱「in **advanced discussions**」。意向，不是合約；同樣沒有 SuperNova。
- 兩份做成研究包 **`ra_905c6719146417c137e3ded2c22dc75f`**（digest `79643b8f…`，到期 2026-10-25）→ **入圖閘門 pq2 [653]**。節點宣告照抄圖上現值（loader 對節點是覆寫）。
- **Coherent、住友**：追不到一手＝`isolated_tier_3`，依 source-trace 規則書**不產抽取、不入圖**（我在 [652] 提案裡寫的「追不到就以 tier 3 入圖」違反這條，已照規則書更正），
  建假設 **`hy_0007_2026-09-25`**（到期 2026-12-24）；`python -m query.bottleneck --what-if hy_0007_2026-09-25`：若為真，結構表新增 3 列（Coherent／Lumentum／住友 → SuperNova）
  ——「表有動」，值得追平行證據；SuperNova 讀圖第 2 條反證的 watch 已在盯這四家。
- **對 SuperNova 插槽的意義**：Ayar 的雷射來源從 2022 年起就不只 Sivers 一家（公司層級、一手）。這不是 SuperNova 那一格的證據（L6），所以插槽讀圖**現在不改**；
  [653]、[654] 入圖後插槽的供給側與製造者段會變，由那時的研究 session 重讀。

### 7.3 準備研究包時又現形的兩個系統問題（記進 plan §14 #20、#21，沒有順手改）

1. **聯合公告偵測對 71／100 家公司無效**：`co:ayar_labs` 等 71 家沒有 `display_name`，`_origin_mentions` 認不出它們。`classify_evidence` 註解點名的例子
   「Sivers 官方 PR，內含 Ayar Labs CTO 具名引述 → counterparty_joint」實際跑出來是 `self_reported`。所以 [654] 入圖後，Sivers→SuperNova 的文件數 1 → 2，證據等級仍是 needs_review。
   修它會牽動很多邊的證據等級，要先量再放。
2. **OpenLight 有兩個 registry ID**（`co:openlight`、`co:openlight_photonics`）。

### 7.4 pq2 狀態

| 編號 | 狀態 | 收據／下一步 |
|---|---|---|
| [651] | go ✓ | `authority:graph_migration_packet;ref:loader/manifests/r4-socket-makers-20260925.json` |
| [652] | go ✓ | `authority:research_packet;ref:ra_905c…＋manifest＋hy_0007` |
| [653] | 待核准（`ra_admission`） | 研究包 `ra_905c6719146417c137e3ded2c22dc75f` 入圖 |
| [654] | 待核准（manual） | 遷移 manifest 入圖（只加不改，12 條） |

## 參考來源（圖外，本 Step 查證用）

- [Lumentum／Ayar Labs 2022-03-09 聯合新聞稿（Lumentum IR）](https://investor.lumentum.com/financial-news-releases/news-details/2022/Lumentum-and-Ayar-Labs-Announce-Strategic-Collaboration-to-Supply-External-Light-Sources-for-Co-packaged-Optical-Interconnect-Solutions/default.aspx)
- [Sivers 2024-12-19 公告（MFN）](https://mfn.se/cis/a/sivers-semiconductors/sivers-semiconductors-and-ayar-labs-to-expand-their-partnership-on-enabling-high-volume-manufacturing-of-optical-i-o-solutions-for-scalable-cost-effective-ai-infrastructure-43633a81)

- [The Next Platform, 2026-03-04: Ayar Labs Gets $500 Million To Ramp Photonics Into 2028 AI Systems](https://www.nextplatform.com/connect/2026/03/04/ayar-labs-gets-500-million-to-ramp-photonics-into-2028-ai-systems/4093515)
- [Sivers／Ayar 2024-12-19 擴大合作新聞稿（PR Newswire）](https://www.prnewswire.com/news-releases/sivers-semiconductors-and-ayar-labs-to-expand-their-partnership-on-enabling-high-volume-manufacturing-of-optical-io-solutions-for-scalable-cost-effective-ai-infrastructure-302335984.html)
- [Sivers ECOC 2024 新聞稿（已入圖，doc `sivers_ayar_wdm16_ecoc_2024_09_19`）](https://www.sivers-semiconductors.com/press/sivers-semiconductors-16-wavelength-wdm-laser-demonstration-with-ayar-labs-set-to-light-up-ecoc-2024/)
- [Contrary Research: Ayar Labs（2025-10-30）](https://research.contrary.com/company/ayar-labs)
- [SEQH Capital Research: Sivers Q2 2026 update（2026-06-26）](https://www.seqhresearch.com/p/sivers-semiconductors-q2-2026-update)
- [Digitimes 2026-06-15: China eases InP substrate exports](https://www.digitimes.com/news/a20260615PD212/substrate-exports-capacity-2026-market.html)
- [TrendForce 2026-07-13: Sumitomo Electric InP 擴產 180 億日圓](https://www.trendforce.com/news/2026/07/13/news-sumitomo-electric-to-raise-inp-substrate-expansion-scale-with-jpy-18-billion/)
- [JX Advanced Metals 2026-06-16 新聞稿](https://www.jx-nmm.com/english/newsrelease/fy2026/20260616_02.html)
