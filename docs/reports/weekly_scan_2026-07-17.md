# 本週訊號掃描 — 2026-07-17

> Stage 0：`get_extraction_rules` 呼叫成功，MCP 連線正常。上週 PR #1（2026-07-11 週報）為 merged 且未標 `loaded`，但其「待核准清單」明寫零抽取草稿，已依規則補標 `loaded` 並留言記錄（doc_ids = 無）。
>
> **環境限制（本次新發現，影響 Stage 2.5 全部追源）：** 本次 session 的 `WebFetch` 與 `curl` 對外部站台一律回 403（已測 SEC EDGAR 兩個 URL、7 個財經新聞站、以及對照組 en.wikipedia.org，全部同樣被拒），proxy status 顯示為「destination host not allowed by organization's egress policy for this session」。這代表本次 routine 唯一可用的外部資訊管道是 `WebSearch`（其回傳為 AI 摘要，非逐字原文+locator）。依 `skills/source-trace/SKILL.md`「搜尋摘要不算原文」的鐵律，本週**任何**新素材都無法達到 `original_obtained`/`tier_1_2_honest_passthrough` 門檻，即使原文本身是 tier 1 SEC filing 且已定位到確切 URL。這不是「找不到原文」，是「環境連不到」，兩者性質不同，請見下方「追源未果清單」。建議檢查此 cloud routine session 的 egress allowlist 是否應納入 `sec.gov` 等一手來源站台。

## ⚡ 30 秒 brief

**本週最重要的一手來源候選——AXT（Tongmei）與 Coherent 簽署的三年期 6 吋 InP 晶圆供應協議——因上述環境限制無法取得逐字原文，本週不產抽取草稿。** 這則協議命中 AGENTS.md 開發優先序第一項（Coherent InP 依賴鏈唯一非自報來源候選），且多篇獨立財經媒體交叉報導的具體數字（$22,288,500 預付款、2026-06-25 生效、3 年期、6 吋晶圆、北京廠擴產）高度一致；但依專案鐵律，AI 搜尋摘要不能取代逐字 quote，故僅列入「追源未果清單」與「可能觸發 disproof 的訊號」，**不寫入圖**，待下次有 SEC EDGAR 可達的環境（本機 `fetchers/edgar.py`，或本 cloud routine 的 egress 政策開放後）重新追源。

其餘：Sivers Semiconductors 治理/財報可信度危機（Issue #2 追蹤中）本週持續惡化——SEK 700M 私募已完成且超額認購、董事會完成護盤買股、放空比例升至約 17%（3 月時僅 1.6%）、據報瑞典檢方已就洩密時點展開調查（未經一手來源核實，標「？」）。Issue #2 既有的人工核查已設定 2026-08-27（重編後 Q2 財報）為分辨點，本次僅追加監控留言，不重啟審查週期。

## 各主題發現

### cpo（Co-Packaged Optics 供應鏈）

本週唯一具體、可能有價值的新素材是 **AXT-Tongmei × Coherent 三年期 6 吋 InP 晶圆《Master Development and Supply Agreement》**（多家財經媒體報導生效日 2026-06-25，Coherent 預付 US$22,288,500，AXT 承諾 2026–2028 擴充北京廠產能）。這則協議與圖中既有的 `Coherent -DEPENDS_ON-> 6-inch indium phosphide fabrication`（confidence 0.90，來源全部是 Coherent 自己的法說會）高度相關，且若能取得原文，會是**目前罕見的、非 Coherent 自報的獨立佐證**——直接呼應 AGENTS.md M1「Coherent／Lumentum／客戶端公司各達 ≥3 個 distinct origin_entity」的目標。但因本次 session 的 `WebFetch`/`curl` 對外部站台全數 403（見上方環境限制說明），無法取得逐字原文與 locator，依規則不產抽取草稿，也不能寫入圖。詳見「追源未果清單」與「可能觸發 disproof 的訊號」。

其餘 CPO 相關新聞（Coherent OFC 2026 CPO 展示與 $15B/$4B SAM、Broadcom Tomahawk 6「Davisson」進入出貨階段、Nvidia Quantum-X/Spectrum-X CPO 交換器時程、Lumentum 由 Qorvo 廠址轉換的 Greensboro InP 擴產）皆為圖中既有主張（`coherent_q3fy26_cpo_cl5/cl6`、`Broadcom_q2fy26_cpo_cl1/cl2`、`lumentum_q3fy26_cpo_cl3` 等）的進度重複報導，沒有新增可查核的供應商名稱或瓶頸屬性，本週不觸發新抽取。

### sivers（Sivers Semiconductors InP 雷射）

本主題本週**沒有供應鏈面的新進展**（GlobalFoundries SCALE 合作仍是 6/2 舊聞，圖中已有 `sivers_gf_pr_2026_06_02` 來源）。核心動態延續上週 Issue #2 追蹤的治理/財報可信度危機：

- SEK 700M 私募已完成，據報獲多倍超額認購（瑞典/國際機構投資人參與）
- 董事會成員（Bami Bastani、Karin Raj、Helena Svancar、Todd Thomson、Joakim Nideborn）已於 7/13 完成 AGM 核准的護盤買股，鎖股至少 12 個月
- 股價持續走弱：7/15 收 39.66 SEK，單日跌 6.55%
- 放空比例據報已升至約 17%（3 月時僅 1.6%）
- 據報瑞典檢方已就洩密時點展開調查（來源為單一搜尋摘要，未能定位一手公告，標「？」，不作為確認事實）

Issue #2（2026-07-12 人工核查）已完成完整處置：thesis 標記 `review_required`、confidence 已下修、close 條件設在 2026-08-27（重編後 Q2 財報出爐）。本週動態未觸發字面 disproof 條件，也未改變既定的 8/27 分辨點，故僅於 Issue #2 追加監控留言，不重啟審查週期（見下方留言連結）。

## 抽取草稿

**本週無抽取草稿。** 唯一具備高潛在價值的新素材（AXT-Coherent 供應協議）因本次 session 的 egress 政策封鎖所有外部站台，無法取得逐字原文，依 L6 反幻覺鐵律與 source-trace 規則不產草稿。Sivers 本週動態屬公司治理/財報時變觀測，依 schema 設計本就不進圖（進 Engine C）。

## Triage 稽核

本次 harvest 約 12 則原始材料（web search 10 個查詢，覆蓋 cpo/sivers 兩主題核心公司與反證關鍵字；engine_b 管道 `site:aleabitoreddit.substack.com` 與帳號活動搜尋）。

**通過（1 則，因環境限制未能完成抽取）：**
- AXT-Tongmei × Coherent InP 晶圆供應協議 — 判斷理由：關聯性高（直接命中 Coherent 既有 `DEPENDS_ON` 6-inch InP fabrication 節點）、新穎性高（圖中最新 AXT 文件是 2026-05-14 的 10-Q，早於這份 6/25 生效的協議）、**潛在獨立性是四要素裡最高分項**（AXT 已於本週前 onboard 完成，這份協議若能入圖會是 Coherent InP 依賴鏈第一個非自報獨立來源）。可引用性理論上足夠（多篇報導數字一致），但受環境限制無法驗證逐字 quote，故僅放行到追源階段，最終未產草稿。

**篩掉（約 11 則）：**
- Coherent OFC 2026 CPO 展示、$15B/$4B/$2B SAM 數字 — 篩掉理由：與圖中既有 `coherent_q3fy26_cpo_cl5/cl6` 重複，無新資訊。
- Broadcom Tomahawk 6「Davisson」進入出貨階段 — 篩掉理由：既有 bookings/AI 營收主張的進度更新，新聞稿未點名具體光學元件供應商，無法補強任何 edge。
- Nvidia Quantum-X/Spectrum-X CPO 交換器時程、11 家生態系夥伴 — 篩掉理由：屬既有已知 roadmap 重複報導，無新瓶頸訊號。
- Lumentum Greensboro（原 Qorvo 廠址）InP 擴產「點名 NVIDIA 為客戶」的細節 — 篩掉理由：與圖中既有 `lumentum_q3fy26_cpo_cl3` 相關但細節（NVIDIA 具名客戶）無法逐字驗證（同一環境限制），暫不補強。
- LPO/copper 替代技術產業通論文章 — 篩掉理由：無具體可查核的新事件或日期，屬教學性質內容重複出現在搜尋結果。
- Marvell Celestial AI Photonic Fabric 整合時程 — 篩掉理由：與圖中既有 `optica_celestial_2025` 主張重複，無新素材。
- Sivers-GlobalFoundries SCALE 合作 — 篩掉理由：6/2 舊聞，已在圖中（`sivers_gf_pr_2026_06_02`）。
- Sivers-WIN Semi InP 雷射二極體可靠性問題指控（Ningi Research）— 篩掉理由：非本週新素材，已於 Issue #2 的 2026-07-12 人工核查留言中處置。
- Sivers 財報時程/私募/董事買股等公司治理動態 — 篩掉理由：屬時變觀測，不適合抽取入圖（已寫入本週報告脈絡與 Issue #2 留言，供人工評估來源可信度延續判斷）。
- aleabitoreddit 近期貼文搜尋 — 篩掉理由：最新一篇仍是 2026-05-20 的 Sivers 客戶地圖文章，已在圖中（`aleabitoreddit_sivers_cpo_customer_map`），本週查無新貼文。
- aleabitoreddit 帳號活動/追蹤數里程碑（如「超越 Elon Musk 成為 X 第一大訂閱帳號」）— 篩掉理由：帳號自身動態非供應鏈訊號，關聯性不足。

## 追源未果清單

```yaml
claim: "AXT（Tongmei）與 Coherent 簽署三年期 6 吋 InP 晶圆 Master Development and Supply Agreement，
  Coherent 預付約 US$22,288,500，2026-06-25 生效，AXT 承諾 2026–2028 擴充北京廠產能。"
lead_url: "https://www.tipranks.com/news/company-announcements/axt-signs-major-inp-wafer-supply-agreement
  （另有 sahmcapital / gurufocus / msn / seekingalpha / intellectia / trendonify 等至少 6 家獨立媒體報導相同數字）"
claimed_origin: "AXT Inc. — SEC Form 8-K（含新聞稿 exhibit 99.1 與協議摘要 exhibit）"
attempts:
  - route: "SEC EDGAR 直接原文（exhibit 99.1 新聞稿）"
    query_or_url: "https://www.sec.gov/Archives/edgar/data/1051627/000121390026002690/ea027235801ex99-1_axtinc.htm"
    result: "blocked"
    note: "WebFetch 回 403；本 session 的 agent proxy 對 sec.gov 判定為 egress 政策不允許"
  - route: "SEC EDGAR 直接原文（協議摘要 exhibit）"
    query_or_url: "https://www.sec.gov/Archives/edgar/data/0001051627/000143774926014204/ex_906119.htm"
    result: "blocked"
    note: "同上，403"
  - route: "交叉方：財經新聞站直接抓取原文（tipranks / sahmcapital / gurufocus / intellectia）"
    query_or_url: "上列 4 個 URL 逐一嘗試"
    result: "blocked"
    note: "全數 403；並以中性對照網址 en.wikipedia.org/wiki/AXT,_Inc. 測試，同樣 403，確認是本 session 整體 egress 政策封鎖，非個別站台反爬蟲"
  - route: "第三層：exact-phrase 通用搜尋（WebSearch 工具）"
    query_or_url: "AXT Coherent Master Development and Supply Agreement $22,288,500 / 6-inch indium phosphide"
    result: "found"
    note: "至少 7 家獨立媒體對金額/日期/期限/廠址數字高度一致，但這是 AI 搜尋引擎的摘要文字，不是逐字掃描的原文+locator，依 skills/source-trace/SKILL.md 不能當 quote 使用"
trace_status: "既非 original_obtained 也非 isolated_tier_3——原文是可定位的 tier 1 SEC filing，
  問題出在本 session 網路政策全站封鎖外部 host（連中性對照頁 Wikipedia 都被拒），
  是環境連線限制，不是來源品質問題"
obtained_origin_entity: null
obtained_source_type: "filing（聲稱，未獨立驗證）"
evidence_tier: null
quote: null
locator: null
storage_permission: "不適用（未產生 extraction 草稿）"
next_action: "park_trace_backlog — 待下次有 SEC EDGAR/外部站台可達的環境重跑追源
  （本機 session 可用 fetchers/edgar.py，或本 cloud routine 的 egress allowlist 開放 sec.gov 後）"
```

## 待印證清單

由 `query/single_origin_report.py` 的 `SINGLE_ORIGIN_CYPHER`（`$company_id` 替換為 `null`）即時導出。本次查詢：**single-origin 42 筆，orphan provenance 0 筆**（無缺 origin_entity 或缺 SourceDoc 的項目）。以下按公司分組列出 single-origin claim（僅單一 `origin_entity`，尚待第二個獨立來源印證）：

**`co:axt`**（4 筆，全部來自 AXT 自己的 10-K/10-Q）
- `axti_10_k_20260317_cl1` — 中國已將 InP 基板列入出口管制清單，AXT 稱出口許可證是目前最大挑戰
- `axti_10_k_20260317_cl2` — 初始 InP 出口許可證僅涵蓋歐洲/日本部分客戶，美國出貨許可仍待批
- `axti_10_k_20260317_cl3` — 無單一客戶佔營收 >10%，10-K 未點名具體客戶（**本週 disproof 候選，見下節**）
- `axti_10_k_20260317_cl4` — AXT 自稱 InP/低 EPD GaAs 競爭者少、專有製程構成進入門檻（自報競爭地位）

**`co:coherent`**（8 筆，全部來自 Coherent 自己的法說會/OFC 簡報）
- `coherent-corp..._cl1`〜`cl6`（OFC 3/17 簡報：NVIDIA 多年期供應協議、CPO 首發營收時程、InP 產能倍增、$15B SAM 等）
- `coherent_q2fy26_cpo_cl1`〜`cl5`（Q2 法說：CPO design win、6 吋 InP 良率、scale-up TAM、多家 InP 基板供應商、產品線規劃）
- `coherent_q3fy26_cpo_cl1`〜`cl5`（Q3 法說：Sherman 廠地位、NVIDIA $2B 投資協議、營收時程、垂直整合、SAM）

**`co:lumentum`**（9 筆，全部來自 Lumentum 自己的法說會）
- `lumentum_q2fy26_cpo_cl1`〜`cl5`、`lumentum_q3fy26_cpo_cl1`〜`cl4`（InP 產能吃緊、400mW 雷射近乎唯一來源、OCS backlog、Greensboro 新廠時程等）

**`co:broadcom`**（3 筆，全部來自 Broadcom 自己的法說會）
- `Broadcom_q2fy26_cpo_cl1/cl2/cl4` — CPO 事實標準地位、bookings 超出貨 3 倍、$100B+ FY2027 目標

**`co:nvidia`**（1 筆有公司標記，另有 3 筆未標記公司但同源）
- `Nvidia_q1fy27_cl5` — 因出口許可不確定性排除中國數據中心營收（其餘 cl1–cl4 為未綁定公司節點的產業級主張，同樣僅 NVIDIA 自報）

**`co:applied_optoelectronics`**（1 筆，AAOI 自己的新聞稿，2026-07-14）
- `aaoi_pearland_expansion_pr_2026_07_14_cl1` — Pearland, TX 擴產近 40 萬平方英尺，與 Tower METI 擴產同日公告

**`co:sivers_semiconductors` × `co:ayar_labs` / `co:marvell_technology`**（2 筆，均來自 aleabitoreddit）
- `aleabitoreddit_sivers_cpo_customer_map_cl1` — Sivers 列名 Ayar Labs 供應商網站，未經一手文件確認
- `aleabitoreddit_sivers_cpo_customer_map_cl3` — Marvell Celestial 為 Sivers 客戶，屬 tier 3 推論未經確認

**`co:poet_technologies`**（1 筆，來自 damnang_substack）
- `damnang_poet_ofc2026_review_2026_03_cl1` — POET OFC 2026 展示是否使用 Sivers DFB 雷射陣列未經證實

**未綁定特定公司節點（產業級主張）：**
- `Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era_c1/c2/c3`（Third-party Research：Broadcom 3D CPO 頻寬、Intel 1T 電晶體目標、玻璃基板 CPO）
- `gsr_inp_substrate_market_2026_05_16_cl1/cl2`（Global Semi Research：InP 基板三雄寡占市場結構與產能利用率，2026-05-16 時點觀測）
- `enablence_sivers_onet_ofc_pr_2026_03_17_cl1`（Enablence Technologies：Sivers/O-Net/Enablence 三方 ELS 模組公告）

## 建議 onboard 候選

無新增候選。AXT 已於本週前完成 onboard（圖中已有 `co:axt` 節點與 10-K/10-Q 來源的 claims），本週發現的 AXT-Coherent 協議屬於既有公司的新素材（因環境限制未能入圖，見上方「追源未果清單」），不是新公司提案。

## 可能觸發 disproof 的訊號

⚠ **AXT — `axti_10_k_20260317_cl3` 的 disproof_condition 疑似被本週素材觸發，但無法以本次可用手段確認**

現有 confirmed claim（來源：`axti_10_k_20260317`）：「AXT sells substrates primarily to epitaxial-layer companies... no customer represented more than 10% of revenue in 2023-2025 and the 10-K names no specific customers, so any AXT-to-specific-device-maker supply edge requires a customer-side or third-party source.」

**disproof_condition 原文：**「A future AXT filing discloses a >10% customer or names specific device-maker customers.」

本週多篇獨立財經媒體一致報導 AXT 於 SEC 8-K 中具名揭露 Coherent 為其 InP 晶圆《Master Development and Supply Agreement》的交易對象——若屬實，這正是 disproof_condition 後半句「names specific device-maker customers」的字面觸發。但因本次 session 的 egress 政策封鎖了 SEC EDGAR 與所有測試過的新聞站台（見上方環境限制說明與追源未果清單），**無法以逐字原文獨立確認這則 8-K 是否真的具名點出 Coherent**，故本週不主張此 claim 進入 `review_required`，僅標記待下次可連上 SEC EDGAR 的環境（本機或 egress 政策調整後的 cloud routine）優先核查。若核實屬實，這同時也是 Coherent InP 依賴鏈 L8 來源獨立性的重大進展，兩件事應一併處理。

（Sivers Semiconductors 的既有可信度警訊持續依 Issue #2 既定的 2026-08-27 分辨點監控中，本週動態未觸發新的字面 disproof 條件，詳見上方「各主題發現」。）
