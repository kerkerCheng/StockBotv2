# 每週審查 — 2026-08-30

> 審查窗：2026-08-23～2026-08-30（Asia/Taipei）。本報告是 point-in-time 快照；topic discovery 只做發現與 triage，未追源、抽取、入圖、修改 thesis lifecycle、建立 PR／Issue，亦未產生任何部位尺寸或下單建議。

## 30 秒 brief

- 本週唯一新增且通過 triage 的 topic lead 是 [ASMPT 先進封裝／CPO 組裝設備展示](https://semi.asmpt.com/en/news-center/press-releases/asmpt-showcases-ap-innovations-for-ai-and-hpc-at-ectc-2027/)：它支持「CPO 量產需要次微米貼合、膠材控制與可重複組裝」這個候選層，但仍只是供應商自述與展會預告，沒有客戶 qualification、訂單、量產份額或經濟性證據。已登記為 `lead_5365613adf1bce24257876e3dab03eea`，留在 pq1；沒有自動研究或入圖。
- 聯亞四年 CW laser 合約與 CapEx、Sivers Q2、XPeng Robotics 融資都已有既存 lead／研究路徑，本輪沒有重複登記。XPeng 的資金是財務投資人對 OEM 的股權融資，不是客戶對上游供應商的 commitment，故不據此 onboard。
- 健康審查先發現 Engine C 缺 `3363.TWO`、`4979.TWO`、`FN` 三個快照，已用既有 ETL 補齊；複查為 67／67。source-trace backlog 的「無機器可觸發 entity」由 9 筆降至 2 筆，剩 Accton／智邦與 SENKO／US Conec，因無安全 ticker／registry 對應而不猜 ID。
- 圖譜目前唯一實質警訊仍是 Lumentum → `tech:uhp_laser` 的單一 origin。這是 **L8 來源獨立性規則**：同一關係即使有多份文件，只要都出自同一經濟實體，仍視為單一來源，不能冒充獨立驗證。
- 三份 lifecycle 都是 `active`，本週無到期：AXT 下次 2026-11-15、Coherent CPO 下次 2026-10-15、Sivers 下次 2026-09-28。Sivers 已於本週由其他核准流程更新至 v4；本輪只讀，沒有重做結論。
- 投組總曝險維持 1.03x；槓桿 ETF 投入資本占 NAV 7.8%、換算槓桿曝險 18.1%；Alpha 風險快照占 NAV 1.5%；TSMC ownership look-through 覆蓋仍為 partial，已知至少 31.8%。共同可投資現金為 USD 30,710，未動用貸款額度 USD 189,705，不計入 NAV 或可投資現金。
- `todo sync` 新增 0，目前 12 項 active。最新 authority 中唯一可用 `go` 執行的是 **[256] CW DFB exact graph delta**；另有 **[81]、[200]、[230]、[249]、[252]、[253]、[254]、[255]** 已由來源停止產出，等待使用者以 `drop` 確認關閉。它們不是新的研究 `go`。

## Topic Digest

### 1. CPO／先進封裝：ASMPT 暴露「組裝設備」候選層

- **發現：** ASMPT 2026-08-24 的官方展示材料把 CPO 製造需求明列為 ultra-precise alignment、controlled adhesive application 與 repeatable assembly，並列出 AMICRA NANO／NOVA、MEGA 等設備。
- **投資意義：** 這不是再多一間光模組公司，而是把 CPO 的 assembly／bonding equipment 層放進候選地圖；若量產良率由次微米貼合與膠材流程約束，設備可能是圖譜目前低覆蓋的瓶頸層。
- **證據限制：** 來源是設備商自述；沒有客戶名、qualification、量產機台數、收入占比、sole-source 或替代性資料。現階段只能支持 `structural_fact / candidate_set`，不能支持商業成熟度或競爭護城河。
- **處置：** PASS，進 pq1；不追源、不抽取、不入圖。

### 2. CPO／CW laser：聯亞已有 applied 路徑，不重複

- [聯亞四年合約報導](https://udn.com/news/story/7240/9715655)所述美國客戶 CW laser agreement 與擴產，已由 `lead_c5b…` 完成既有流程並套用 `ra_baf…`。
- 本週沒有第二份獨立 origin 能新增 qualification／minimum purchase／客戶集中度結論，因此不建立 duplicate lead，也不提高任何 evidence tier。

### 3. Sivers：Q2 更新重要，但 authority 已於既有流程吸收

- [Sivers 官方 Q2 2026 更新](https://news.cision.com/sivers-semiconductors/r/sivers-semiconductors-reports-q2-2026-results-as-product-growth--record-pipeline-and-customer-ramps-%2Cc4388331)報告 product revenue 年增 18% 與 USD 1.2B pipeline；同一 origin 的既存 lead 已處理，不能當成獨立 corroboration。
- lifecycle authority 現為 v4／`active`，下次檢查 2026-09-28；本輪只確認狀態與日期，不重寫 thesis。

### 4. Robotics：XPeng 融資不是上游採購承諾

- [XPeng Robotics 官方融資公告](https://www.xpeng.com/pressroom/news/01a03797fccda01e0de68a02a256006a)稱融資超過 USD 900M、投後估值超過 USD 6.3B，資金用於 R&D 與 mass production。
- 方向上支持 humanoid 產業獲得資本，但付款方向是投資人 → OEM，不是客戶 → 零組件供應商；沒有 actuator、reducer、sensor、部署客戶或採購量的新證據。既存 `lead_6e600…` 維持 parked，不建 onboard packet。

### 5. 本週沒有新增、可驗證的 humanoid deployment commitment

- 8/19 的 Hexagon／Schaeffler 與 8/20 的 SK hynix roadmap 都在前一審查窗且已有 lead；本輪不重複。
- 新聞與社群搜尋沒有找到同時滿足「近七日、具名付款方向、可核對部署／採購承諾、與既有圖譜有新差異」的第二個 robotics topic。

## Thesis lifecycle 唯讀核查

| Thesis | 狀態 | `last_checked` | `next_check` | 本週處置 |
|---|---:|---:|---:|---|
| `axt_inp` | active | 2026-08-04 | 2026-11-15 | 無到期；只讀 |
| `coherent_cpo` | active | 2026-07-17 | 2026-10-15 | 無到期；只讀 |
| `sivers` | active | 2026-08-29 | 2026-09-28 | v4 已由既有核准流程更新；本輪只讀 |

近期可觀測事件仍是 AXT 2026-10-30／2026-11-13、Coherent capacity 2026-12-01、Sivers Q3 2026-11-26 與 ELS readiness 2026-12-31。這些是提醒，不是本週 thesis mutation 或 pq2 核准項。

## 完整本機健康審查

### 修前

- `query/health_audit.py --local`：claims 無 missing citation、無 duplicate claim、schema 一致、無 evidence conflict、無 TICKER_MAP identity gap、無 lifecycle due、無 memo freshness gap。
- Engine C 共 67 個 ticker，缺 `3363.TWO`、`4979.TWO`、`FN` 三個 snapshot。
- 圖譜警訊：Lumentum → `tech:uhp_laser` 只有 Lumentum 單一 origin，L8 weak。
- source-trace backlog 共 47 筆，其中 9 筆缺機器可用 trigger entity；主因是 system-decompose 候選只把公司名寫在敘述，未能映射到 top-level entity。

### 確定性維護

- 執行既有 Engine C ETL 補 `3363.TWO`、`4979.TWO`、`FN`，三筆皆成功。
- 執行 entity backfill：13 筆既有 lead 補上可確定性導出的 entity。
- 對 7 筆 frozen trace 以既有 registry／ticker 做 exact annotation：OSA、MRM、SoIC、fiber、FOCI、ODM、LuxNet；沒有新增公司、猜測 ticker 或改 evidence tier。

### 修後

- Engine C 為 67／67；完整 health audit 除 Lumentum 單一 origin 外皆通過。
- source-trace backlog 仍為 47 筆，但 unreachable 由 9 降至 2：
  - `lead_1c805d…`：Accton／智邦，沒有安全且已登記的 ticker mapping。
  - `lead_55bd36…`：SENKO／US Conec connector，屬 private／未登記實體。
- 這兩筆保留為健康 blocker，不建立臆測 entity、不自動 onboard，也不占 pq2。
- skill sync、classification health、harvest health 均無新錯誤；`todo sync` 新增 0，active 12。

## 投組風險快照

> 本節只呈現 policy target gap、相對水位與硬風控監測；不是買入時機、投入金額或部位排序建議。

### Target allocation gap

| Sleeve | 現況 | 目標 | Gap | 相對水位 |
|---|---:|---:|---:|---|
| `beta_core` | 28.1% | 40.0% | -11.9pp | 低於 band |
| `beta_tilt` | 32.7% | 25.0% | +7.7pp | 高於 band |
| `beta_tilt_active` | 3.6% | 3.0% | +0.6pp | band 內 |
| `beta_leverage` | 8.4% | 10.0% | -1.6pp | band 內 |
| `large_cap_tilt` | 25.5% | 12.0% | +13.5pp | 高於 band |
| `alpha` | 1.7% | 10.0% | -8.3pp | 低於 band |

`alpha` 1.7% 是 sleeve allocation 的 invested non-cash 分母；下方風險快照的 1.5% 是占 NAV，兩者不能混用。

### 槓桿、集中度與現金

- 總曝險 1.03x，低於 policy cap 1.75x；估算 ruin threshold 97%。
- 槓桿 ETF 投入資本占 NAV 7.8%；換算槓桿曝險 18.1%；已動用貸款債務為 0，因此 combined effective 仍為 18.1%。
- Alpha 已知曝險占 NAV 1.5%。Alpha 與 Beta 同時偏向 AI／photonics，相關性風險仍存在。
- TSMC ownership look-through 覆蓋為 `partial`：已知至少 31.8%（direct 18.1%、indirect 13.7%），不可把已建模部分寫成完整曝險。
- 共同可投資現金 USD 30,710；cash floor USD 632；Portfolio CASH USD 31,343。
- 未動用貸款額度 USD 189,705；依 policy 不計入 NAV、cash 或 allocation。

### 與 2026-08-23 週報比較

- 總曝險：1.03x → 1.03x，持平。
- 槓桿 ETF 投入資本占 NAV：7.6% → 7.8%（+0.2pp）；換算槓桿曝險：17.6% → 18.1%（+0.5pp）。
- Alpha 占 NAV：2.0% → 1.5%（-0.5pp）。
- TSMC 已知至少曝險：31.3% → 31.8%（+0.5pp），coverage 仍是 partial。
- 共同可投資現金：USD 30,632 → USD 30,710（+USD 78）；未動用貸款額度：USD 188,561 → USD 189,705（+USD 1,144）。

## Triage 稽核

審查窗內共 87 筆 lead：`parked` 73、`triaged_no_go` 9、`applied` 4、`triaged_go` 1。來源包含 Form 4 20、system-decompose 15、curated X 28 與 weekly discovery 2；其餘為既有 routine 來源。

### PASS／有實質路徑

- **ASMPT CPO assembly equipment**：本週新增唯一 PASS；`structural_fact / candidate_set`，Tier 1 supplier self-report，進 pq1。
- **聯亞 CW laser agreement／CapEx**：既存 applied；本週不重複。
- **Sivers Q2 與 lifecycle v4**：既存路徑已吸收；同一 origin 不算獨立 corroboration。
- **XPeng Robotics 融資**：既存 lead；保留為產業資本訊號，但 payment direction 不支持上游供應鏈 commitment。

### FILTER／NO-GO 類群

- MRVL／Reddit 的 Spider-Man 玩笑與純情緒貼文：沒有可驗證的新 claim。
- 美國太空政策：超出本週 CPO／robotics／Sivers themes，且無現有 thesis impact。
- 作者身分、績效展示、社交互動與語言貼文：不是公司／技術／付款方向證據。
- 關稅與地緣政治泛論：沒有具名供應關係或可觀測 thesis disproof。
- 純轉貼／摘要而無新原始事件：已有相同事件的 canonical lead，避免 URL／事件重複。

## Onboard 候選

- **ASMPT（候選，未 prepared）：** 值得研究 advanced packaging／CPO assembly equipment 層；在 onboard 前仍需確認 legal identity／ticker、產品與 CPO 量產的實際收入／qualification、客戶 origin 多樣性與替代設備。這輪不建立 registry 條目或 RA。
- **AIXTRON（既存候選，不重建）：** 由聯亞擴產路徑帶出，但需把 equipment purchase／capacity dependency 與 supplier marketing 分開；沿用既存 lead。
- **Accton／智邦、SENKO／US Conec（identity blocker，不是 onboard 建議）：** 本輪只確認 entity linkage 無法安全自動完成。必須先有合法實體／ticker 或 registry 判定，再談 prepared onboard RA。
- **XPeng Robotics（本輪不建議）：** 融資支持 OEM 擴張，卻未提供上游零組件供應與付款方向；不足以因單一估值事件擴張圖譜。

## 統一 pq2：本週真正可決定的項目

`todo sync` 目前有 12 個 active 編號。唯一可用 `go` 執行 exact authority mutation 的是 [256]；八個來源已停止產出的舊項目需要 `drop` closure confirmation。`drop` 只關閉 stale pq2 編號，不撤回既有 graph、Engine C、thesis 或 Decision receipt。

### [256] Sivers／LuxNet → CW DFB 的 exact graph delta

**核准載入已 validate 的 CW DFB substitutability addendum — 現在 extraction 已凍結且 validation 通過，可把 Sivers 與 LuxNet 的 CW DFB 可替代性明確寫入圖譜 ｜ `go` 只授權載入 `extractions/cw_dfb_substitutability_addendum_2026_08_29.json` 的 exact delta 與 judgment claim；不含擴寫其他 edge、thesis mutation、Decision reassess 或 live。**

- 公司／ticker：Sivers Semiconductors（SIVE.ST）與 LuxNet（4979.TWO）。
- Exact delta：`sivers → cw_dfb` 與 `luxnet → cw_dfb` 的 `substitutability=2`，加上 packet 內已驗證的 judgment claim。
- 投資意義：把「兩家都能供 CW DFB」從敘述轉成可查詢的替代性，避免 sole-source／chokepoint 判斷把同層競爭者漏掉。
- 證據限制：`substitutability=2` 是有來源約束的分析判斷，不等於兩者在 wavelength、功率、yield、qualification 或 customer share 上完全可互換。
- 檔案：[`extractions/cw_dfb_substitutability_addendum_2026_08_29.json`](../../extractions/cw_dfb_substitutability_addendum_2026_08_29.json)

### 待 `drop` 確認關閉的八個 stale 項目

以下八項的 canonical source 本輪皆成功執行，但已不再產出該項；sync 因此只要求人確認是否關閉，不接受研究 `go`。若同意，可一次回覆：`81 200 230 249 252 253 254 255 drop`。

- **[81] 關閉 Meta Vistara CXL 記憶體擴充平台舊項 — source 已不再產出，避免 completed candidate 長留決策列 ｜ `drop` 只關閉 [81]；不刪已套用的 Meta／CXL evidence、graph 或 Decision receipt。**
- **[200] 關閉 Agility Robotics 客戶商業承諾補證舊項 — source 已不再產出，現行 pipeline 不再要求這個 work item ｜ `drop` 只關閉 [200]；不改 Agility lifecycle、graph 或任何 live authority。**
- **[230] 關閉 Schaeffler 獨立來源補證舊項 — source 已不再產出，避免把無 executable target 的編號重問一次 ｜ `drop` 只關閉 [230]；不把供應商自報升級成獨立證據，也不改 graph。**
- **[249] 關閉 Marvell（MRVL）估值錨舊項 — source 已不再產出，current producer 沒有新的 valuation action ｜ `drop` 只關閉 [249]；不表示估值缺口已獲證明，也不改 Decision 或 live。**
- **[252] 關閉 Tower Semiconductor（TSEM）獨立來源補證舊項 — source 已不再產出，沒有新的 bounded research work order ｜ `drop` 只關閉 [252]；不提高 Tower–IQE InP 關係的 evidence tier。**
- **[253] 關閉 Harmonic Drive Systems（6324.T）獨立來源補證舊項 — source 已不再產出，沒有新的 humanoid reducer 研究授權 ｜ `drop` 只關閉 [253]；不改 commercial maturity、graph 或 thesis。**
- **[254] 關閉 Landmark Optoelectronics／聯亞（3081.TWO）獨立來源補證舊項 — source 已不再產出，沒有新的 customer／valuation work order ｜ `drop` 只關閉 [254]；不撤回已 applied 的 CW laser RA，也不改 thesis。**
- **[255] 關閉 Micron（MU）獨立來源補證舊項 — source 已不再產出，沒有新的 HBM／RPO work order ｜ `drop` 只關閉 [255]；不把既有 current decision context當成獨立 corroboration。**

### Active 但本週不需動作

- **[193] Rosenblatt access：** 已 defer；若未來需要付費，仍須另核准 exact 金額／方案。
- **[129] AAOI reassess：** bounded research 已完成，等相鄰 exact gate [134]，不再吃一次 `go`。
- **[134] AAOI Q3 guidance：** 等外部事件；Q3 2026 guidance 公布前不需動作。

## 本輪執行邊界與查證入口

- Health：`.venv\\Scripts\\python.exe query\\health_audit.py --local`
- Risk：`.venv\\Scripts\\python.exe scripts\\daily_beta_snapshot.py --format markdown --no-refresh --risk-view full --no-record-risk`
- Engine B：`.venv\\Scripts\\python.exe -m engine_b.cli counts`、`classification-health`、`harvest-health`、`trace-backlog`
- pq2：`.venv\\Scripts\\python.exe -m engine_b.todo sync`
- Lifecycle authority：`thesis/lifecycle.json`

本輪沒有 source-trace、extraction、graph admission、lifecycle mutation、Research Action apply、PR／Issue、branch 或 worktree。
