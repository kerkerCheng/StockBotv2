# 週審查 — 2026-08-02

> 掃描窗為 2026-07-26～2026-08-02。依本機 Weekly v1.2，只做 topic discovery、完整本機健康審查、
> lifecycle 唯讀提醒與統一 pq2；本週沒有執行 source-trace、claim extraction、graph admission、
> lifecycle 結論修改或 PR／Issue 建立。

## 30 秒 brief

- 🟢 本週三個可研究 topic 都已由 daily 建成既有 `triaged_go` lead：FormFactor 的 CPO 測試營收加速、
  X-FAB 的 silicon-photonics 2028 volume-production 時程、POET／Sivers 對 2026 年底 production 的措辭。
  Weekly 沒有重複註冊，也沒有提前追原文或抽取。
- 🟢 修復 Schaeffler ticker 漂移：官方現行代碼為 `SHA0`，Engine C 改用 `SHA0.DE` 後成功補建 snapshot；
  38 檔 freshness 由 1 檔缺失恢復為全數通過。
- 🟡 仍有兩個證據型健康缺口：Lumentum → UHP laser 的 `sole_source` 只有 Lumentum origin；
  `co:casela_technologies` 尚未有可確認的 public/private ticker 身分，不猜測填入 registry。
- 🔴 `sivers` 維持 `review_required`，8/27 才到人工分辨點；本週不改 lifecycle 結論。
- 🟡 投組總曝險 1.02x；槓桿 ETF 資金占比 7.4%、換算槓桿曝險 17.1%、已提款貸款 0%；
  TSMC 已知穿透曝險 31.8% 為集中度警戒，但不構成自動賣出或 live action。
- 📋 統一 pq2 新增 0 項。現在真正需決定的是 [78]、[82]、[79]；另 6 項均在等既定事件。

## Topic Digest

### 1. FormFactor：CPO 測試從 R&D 題材進入可見營收 — `research`（既有 pq1）

Daily 策展 lead 轉述 FormFactor Q2 call：2026 CPO revenue 原先預期為 US$10–20m，如今公司預期在 Q3
結束前超過該區間、全年顯著高於 US$20m，並稱短期 CPO 業務加速；材料另把需求連到 scale-up／scale-out
switch 的 production infrastructure。若一手文件成立，投資意義不是「CPO 終局已確定」，而是測試設備商開始
出現早期 volume indicator，可用來交叉檢查光引擎／laser volume ramp 是否仍只停在 roadmap。

- 來源：[Daily 策展材料](https://x.com/aleabitoreddit/status/2082720873908494456)、
  [FormFactor Q2 IR event](https://formfactorinc.gcs-web.com/)
- Signal triage：關聯性與可引用性通過；具體公司、數字與時間點可查，且 FormFactor 不在現有核心 watch。
- 邊界：本週未核對 call transcript，也未接受材料對 TSMC COUPE／NVIDIA 的供應鏈歸因。
- 路由：既有 `lead_45471772e76a5682418cca948152f7da` 已是 `triaged_go`；Weekly 不重複註冊。

### 2. X-FAB：三個 silicon-photonics 專案，volume production 指向 2028 — `research / onboard 候選`

Daily 策展 lead 轉述 X-FAB Q2 call：公司正在推進 CPO、手上有三個 silicon-photonics 專案，
但 photonics volume production 預計到 2028 才開始。這同時提供正向與反證價值：X-FAB 是現有 watch 外的
potential foundry node；然而 2028 時程也反駁「2027 全產業同步大量營收化」的過快敘事。

- 來源：[Daily 策展材料](https://x.com/aleabitoreddit/status/2083106805949878330)、
  [X-FAB Investor Relations](https://www.xfab.com/investors/)
- Signal triage：具體公司、專案數與 volume-production 年份可查；新 origin／counter-timeline 使其通過。
- 邊界：本週未核對完整 earnings transcript，亦未判斷三個專案的客戶、產品、qualification 或收入規模。
- 路由：既有 `lead_3a7c4e5db3ecc1c420c1464fb73ac3c2` 已是 `triaged_go`；在公司文件研究完成前只列
  onboard 候選，不直接建公司 action 或 pq2。

### 3. POET／Sivers：`production readiness` 是否升級為 `production` — `research`（既有 pq1）

本週材料聲稱 POET 新文章把 POET–Sivers 合作由「2026 年底 production readiness」改寫為
「production targeted by end of 2026」。若是官方、同 scope 的真正措辭升級，會直接影響 Sivers 量產時程；
但也可能只是行銷摘要改寫，不能在核對原文、產品 scope、qualification 與訂單前當成 volume order。

- 來源：[Daily 策展材料](https://x.com/aleabitoreddit/status/2083114743729107236)、
  [既有 POET–Sivers 官方基準頁](https://www.poet-technologies.com/news/poet-technologies-and-sivers-semiconductors-collaborate-on-external-light-sources-for-co-packaged-optics-and-next-generation-ai-market)
- Signal triage：Sivers／POET 具名、措辭與日期可查，且可能更新現有 claim，因此通過。
- 邊界：既有官方基準仍寫 production readiness；本週沒有進一步追到新文章全文，故只列 topic、不能視為證據。
- 路由：既有 `lead_d3b3988d99ff494fe07af958c6b5bc1e` 已是 `triaged_go`；不另建 weekly lead。

### Robotics：本週 sparse-week 心跳

本週沒有通過去重的新 robotics event。Agility 7/23 CFO 任命在掃描窗外且偏公司治理；「FCC 將禁止中國
humanoid／quadruped 進口」的 7/28 轉述已是既有 parked lead，先前 bounded trace 未找到正式規則文本，
因此不重複建項、不把政策傳聞當 Agility／CCXI 的需求證據。一般 humanoid、teleoperation 與 AMR 比較文也
沒有掃描窗內的新公司動作或數字。

## Thesis 核查

- `sivers`（Sivers Semiconductors，`SIVE.ST`）：維持 `review_required`；`last_checked=2026-07-26`、
  `next_check=2026-08-27`。POET 措辭 topic 只會進 pq1 核查，不足以改變使用者已決議的 8/27 分辨點，
  也不授權新增 live 資本。
- `coherent_cpo`（Coherent，`COHR`）：維持 `active`；`next_check=2026-10-15`。
- 統一池已承接 lifecycle：pq2 [10] 與 decision review [42] 都在等 8/27，本週不重複提醒為立即決策。

## 系統健康審查（修前／修後）

### 修前

- 🟡 L8（來源獨立性：供應商自報不能當 sole_source 獨立佐證）：
  `co:lumentum -[supplies_to]-> tech:uhp_laser` 只有 Lumentum origin。
- 🟡 TICKER_MAP：`co:casela_technologies` 未登記。
- 🔴 Thesis：`sivers` 為 `review_required`；這是人工 gate，不是維護故障。
- 🟡 Engine C：38 檔中 `SHA.DE` 完全沒有 snapshot。
- 🟢 Claim／EdgeAssertion 缺 CITES、重複 SourceDoc、edge conflict、schema mismatch、memo stale、
  財務 checklist 不可跑、Research Action 待 publish、skill adapter 漂移均為 0。

### 已修

- Schaeffler 官方 share data 的 ticker 是 `SHA0`；`SHA.DE` 在 Yahoo 無資料，`SHA0.DE` 可成功取得
  EUR 7.09 與 gross margin 18.357% 的 snapshot。本週將 `co:schaeffler` research ticker 修為
  `SHA0.DE`，同步更新 identity test；[官方基礎資料](https://www.schaeffler.com/en/investor-relations/share/basic-data/)。
- `tests/test_identity_registry.py`：5 passed。

### 修後

- 🟢 Engine C freshness：38 檔全數通過 7 日閾值。
- 🟡 Lumentum sole_source 單一 origin、Casela identity gap 與 Sivers lifecycle 維持原狀。
- Casela 不直接填 `research_ticker=null`：現有圖證據只有 AXT filing 對供應合約的 issuer-origin 描述，尚不足以
  斷言它沒有公開掛牌身分；此項保留為 identity research gap，不占 pq2、也不以猜測消黃燈。

## 投組風險完整快照與較前次趨勢

- 自有現金可部署：USD 30,461（Portfolio CASH USD 31,080 − cash floor USD 619）；Alpha／Beta 共用。
- 本輪可人工評估上限：USD 0；距下次每 5 個完整交易日的 baseline 提醒約 1 個 session。
- 未動用貸款額度：USD 185,787；已借款 USD 0、估計月息 USD 0。未動用額度不算 NAV 或自有現金。
- 總曝險：1.02x（policy cap 1.75x）；自有資本歸零門檻約為指數跌 98%。
- 槓桿 ETF 資金占比 7.4%；換算槓桿曝險 17.1%；已提款貸款占 NAV 0%；合計換算曝險 17.1%。
- Alpha 總量 1.8%，僅警告、不阻擋。
- 已知 issuer 曝險：TSMC 31.8%（直接 18.5%／間接 13.3%）為集中警戒；Micron 2.0%、Alphabet 1.7%、
  FRA:2DG 1.6%、NVIDIA 1.0%、Tesla 0.8%、TYO:7803 0.2%。
- Look-through coverage 為 `partial`；未建模 `00981A.TW`、`DRAM`、`LON:VWRA`、`QQQ`、`SOXX`、`TQQQ`。
- 前次 weekly 因舊 Google Sheet operational holdings 欄位不足，沒有可比的完整風險數值；本週是可用的
  weekly baseline，不能把「從未知恢復」誤寫成曝險週增。當日既有 risk history 沒有門檻跨越或狀態翻轉。

## Triage 稽核

本輪三個 active themes 各做 2–3 組搜尋，另掃近期 Engine B 策展材料；去重後得到 7 個 candidate events。

**通過（3 個）：**

- FormFactor Q2 CPO testing revenue acceleration：具名公司、收入區間與季度時間點可查；既有 lead 已 PASS。
- X-FAB 三個 silicon-photonics projects／2028 volume production：新 foundry node 且有 counter-timeline；
  既有 lead 已 PASS。
- POET／Sivers 2026 年底 production 措辭：可能更新現有量產 claim；既有 lead 已 PASS。

**篩掉／去重（4 個）：**

- 一般 LPO／CPO／copper 比較 guide：沒有掃描窗內的新公司事件，只是常設解說。
- Sivers 官方 newsroom：掃描窗內沒有新的公司公告；不把舊增資、舊合作換標題當新 topic。
- Agility CFO 任命：7/23、超出 7 日窗，且未新增 deployment／unit economics／訂單證據。
- FCC 中國 humanoid／quadruped 禁令轉述：已是 parked lead，沒有正式規則文本，不重複放行。

本週 PASS 率是 3/7，只用於事後稽核，不是配額。三個 PASS 都已有 stable lead，因此 `pending_leads.json`
沒有 weekly 重複寫入。

## 建議 onboard 候選

- **FormFactor（FORM）**：若一手 Q2 transcript 確認 CPO 測試收入與 production-infrastructure 量化訊號，
  可作光源／光引擎量產前置 indicator。現階段只是 candidate，不 prepare action。
- **X-FAB（XFAB）**：若公司文件確認三個 photonics 專案、CPO scope 與 2028 volume production，可作
  歐洲 silicon-photonics foundry node 與 CPO 時程反證。現階段只是 candidate，不 prepare action。

## pq2（只列真正需使用者決定的穩定編號）

### [78] AXT–Lumentum 六年 InP substrate capacity reservation — `ra_admission`

**TL;DR：** AXT（`AXTI`）向 Lumentum（`LITE`）保留 InP wafer-substrate capacity；六年合約與兩筆各
US$43.5m deposit 是實質 demand commitment，但 deposit 是 shipment credits，不是已認列營收。

- 誰供應誰：AXT／Tongmei → Lumentum；產品為 InP wafer substrate。
- 事件成熟度：2026-07-26 簽訂的 binding Capacity Reservation Agreement；tier-1 AXT 8-K 已揭露摘要，
  完整合約預計隨 Q3 2026 10-Q exhibit 公開。
- 投資意義：直接補上 AXT 與 Lumentum 的具名長約關係，支持上游 InP capacity commitment，不支持
  sole_source、exclusivity、qualification、實際 shipment volume 或 realized revenue。
- 證據／反證限制：只有 AXT 這一個 origin_event；Lumentum 尚未獨立確認。第二筆 deposit 的 timing／terms
  要到 2028 再定，另有 shortfall、refund、quality、force-majeure 與 termination 邊界。
- `78 go` 的 exact authority：apply `ra_83889cf03637953caa587c21f8e97886` 的最小 graph delta
  （`co:axt -[supplies_to]-> co:lumentum`＋三項有 disproof 的 claim），並 handoff Decision Shadow 到
  `co:axt`。不授權提高 sole_source、修改 thesis、建立 live choice 或下單。

### [82] Meta Vistara CXL 記憶體擴充平台（reviewed） — `ra_admission`

**TL;DR：** Meta（`META`）作者群的 ISCA 2026 論文支持 Meta 自研 Vistara CXL memory-expander ASIC，
把 DDR4 memory 橋接到 host processors；目前只能證明產品與技術關係，不能外推 production 或供應商。

- 誰供應誰／做什麼：Meta develops `prod:vistara`；Vistara 是 CXL memory-expander ASIC，不建立外部供應邊。
- 事件成熟度：一手技術論文已發表；`demand_proof_level=inferred`，不是客戶訂單或量產 receipt。
- 投資意義：補上 hyperscaler 自研記憶體擴充 silicon 的結構性 context；若要推到 DRAM、CXL vendor 或
  alpha，仍需新的供應商／客戶材料。
- 證據／反證限制：只有 Meta 一個 origin_event；不包含 production deployment、DRAM supplier、外部客戶、
  成本節省或效率數字。
- `82 go` 的 exact authority：apply corrected `ra_62c5841f8de2c67890cbefb805ba8d77`，只新增
  `prod:vistara`、`co:meta -[develops]-> prod:vistara` 與一項 inferred claim，handoff 到 `co:meta`。
  不授權舊 [81] 草稿、不建立供應商 edge、不修改 thesis 或 live position。

### [79] Applied Optoelectronics（AAOI）補缺口研究 — `decision_review`

**TL;DR：** AAOI（`AAOI`）已有 800G／1.6T pluggables 與 400mW CPO pump-laser sampling 路徑，
但需求端與財務韌性仍只有 bounded hypothesis；現有 system decision 是 `DATA_NEEDED`，不是交易建議。

- 誰供應誰／產品：AAOI 供應 optical transceivers，並開發 400mW narrow-linewidth pump laser；後者目前只到
  select-customer samples／sampling，尚無客戶端 qualification 或 design-win receipt。
- 事件成熟度：已完成兩輪 bounded research 與 reassess；圖有 causal／counter paths，但 commercial
  maturity 未超過 bounded hypothesis。
- 投資意義：若 800G 超過 400G、pump laser 量產、FAB4／Pearland 擴產被需求吸收，營運槓桿可上升；反面是
  FY2025 前十大客戶占 96.6%、Digicomm 獨家代理占 53.1%、Microsoft 28.8%，且 PO backlog 可改期／取消。
- 主要缺口：Digicomm 終端 sell-through、可量化不可取消訂單、pump-laser 客戶 qualification、季度 capex burn
  與利用率、債務到期／covenant，以及在 hyperscaler 不具名供應商的結構下可取得何種替代驗證。
- `79 go` 的 exact authority：只 dispatch latest decision 的 bounded gap research 到 pq1；取得新 receipt 後才
  reassess。這不等於沿用舊 assessment、自動建立 paper／live position、修改持股或下單。

### 等事件（本週不需動作）

- [10] Sivers lifecycle、[42] Sivers decision：等 2026-08-27 Q2／重編分辨點。
- [64] AXT decision：等下一個 review 點或新 filing。
- [74] Agility：等 S-4／4Q 2026 closing 後 AGLT identity；[75] 是重複 cohort，只沿用 [74]。
- [81] 舊 Meta Vistara RA：已由 [82] corrected action 取代，等 2026-09-01 自動到期；不得 apply。
