# 週審查 — 2026-08-16

> 掃描窗為 2026-08-09～2026-08-16。依本機 Weekly v1.2，本週只做 topic discovery、完整本機健康審查、
> lifecycle 唯讀提醒與統一 pq2；沒有執行 source-trace、claim extraction、graph admission、lifecycle 結論修改，
> 也沒有建立 branch、worktree、PR 或 Issue。

## 30 秒 brief

- 🟢 CPO／InP laser 的商業化訊號繼續增強：Lumentum 首次揭露 ELS module order 與更高 UHP CPO laser demand；
  Coherent 說明 InP 產能在 2026 年底前倍增、2027 年再倍增，CPO/NPO 已列為 H2 2026 起的新 growth engine。
  兩個事件都已有 daily PASS lead；Lumentum 8-K 與 Coherent 法說會 lead 已完成入圖，Weekly 沒有重複註冊。
- 🟡 Sivers 與 SemiNex 公告約 US$3.4m 的 next-generation InP light-source program，涵蓋 CPO ELS、
  multi-wavelength DFB arrays 與 SOA，目標 2027 下半年 sampling／early production。這是具體 program，
  但仍是雙方自報且不是客戶 qualification、volume order 或已認列收入。
- 🟡 Unitree IPO 已從「預計上市」進到 8/10 申購；daily 所見「零售超額認購 8,000 倍」仍未取得可核對的
  發行結果公告，因此維持 parked，不把預上市衍生品估值外推成 Agility／CCXI 基本面。
- 🟢 完整本機 health audit 顯示 Engine C 41/41 freshness 通過，Engine B harvest failure 為 0；Claim／
  EdgeAssertion provenance、schema、edge conflict、financial checklist、Research Action publish、skill adapter 均無新故障。
- 🟡 既有證據／authority 缺口未變：Lumentum → UHP laser 的 `sole_source` 只有 Lumentum origin、
  `co:casela_technologies` identity 未登記，以及 Sivers lifecycle 仍為 `review_required`。
- 🟡 投組總曝險維持 1.03x；槓桿 ETF 資金占比 7.8%、換算槓桿曝險 18.2%、已提款貸款 0%、alpha 2.2%；
  TSMC 已知至少 30.9% 仍是集中度警戒，沒有 hard-cap 跨越。
- 📋 `todo sync` 新增 [154]–[158]，第二次同步新增 0。真正需決定的是 [154] Aeva、[155] AXT、[157] NVIDIA；
  [156] IQE 與 [158] Sivers 都在等系統／匯率資料，不占決策注意力。

## Topic Digest

### 1. Lumentum／Coherent：CPO 從 capacity thesis 走向 order／ramp — `research`（既有 pq1／已入圖）

Lumentum 8/11 FY2026 Q4 官方結果揭露：季度營收 US$1.01b，並將「increasing demand for ultra-high-power
CPO lasers」、「initial order for ELS modules」及 NPO engagements 列為 in-rack optics 開始滲透的證據。
Coherent 8/12 FY2026 Q4 結果則顯示 Datacenter & Communications 季營收 US$1.615b；官方簡報稱內部 InP output
預計 2026 年底倍增、2027 年再倍增，六吋平台已生產 EML、CW laser 與 photodiode，CPO/NPO 新營收路徑標為
H2 2026 起。這兩份公司原文互相強化「qualified InP capacity 是 binding constraint」的方向，但不能直接證明
Sivers qualification、sole_source 或客戶分配。

- 來源：[Lumentum FY2026 Q4 結果](https://investor.lumentum.com/financial-news-releases/news-details/2026/Lumentum-Announces-Fourth-Quarter-and-Full-Fiscal-Year-2026-Results/default.aspx)、
  [Coherent FY2026 Q4 結果](https://www.coherent.com/news/press-releases/fourth-quarter-and-fiscal-year-2026-results)、
  [Coherent 8/12 investor presentation](https://www.coherent.com/content/dam/coherent/site/en/documents/investors/investor-presentations/2026/august-12/investor-presentation-20260812.pdf)
- Signal triage：具名公司、order、產品、產能倍增節點與營收時點均可逐字查核；Lumentum／Coherent 是兩個
  不同 origin_entity，對 CPO capacity／merchant-supply 路徑有獨立價值。
- 邊界：Coherent 的 CPO/NPO timing 與產能目標仍是 issuer guidance；Lumentum ELS 是 initial order，尚未等於
  交付或收入。法說會中的 merchant laser policy 不是契約承諾。
- 路由：Lumentum `lead_d144605273591c7cecce472033bb367a` 已 `applied`；Coherent transcript
  `lead_caa3e0209d61d6de504ac996be1f03fc` 已 `applied`，10-K `lead_b17774619e11d4e923796f2710a55e58`
  仍為 `triaged_go`。Weekly 不重複註冊或提前研究 10-K。

### 2. Sivers–SemiNex：US$3.4m InP light-source program — `research`（既有 pq1）

Sivers 與 SemiNex 8/13 公告一項初始價值約 US$3.4m 的共同 program，目標是 CPO 的 high-power ELS、
high-channel-count DFB arrays 與 SOA gain stages；customer sampling／early production ramp 目標為 2027 下半年。
事件增加了一條產品開發與美國製造夥伴路徑，也把 scope 從單一 DFB array 擴至 light-source stack；但公告沒有
揭露客戶、qualification、最低採購量、付款結構或收入認列，不能視為 CPO volume win。

- 來源：[Sivers 官方公告](https://www.sivers-semiconductors.com/press/sivers-semiconductors-announces-3-4m-program-with-seminex-for-next-generation-inp-light-sources-used-to-power-ai-data-centers/)
- Signal triage：Sivers、SemiNex、US$3.4m、產品範圍與 2H 2027 時點均具體可查；官方英文代表 lead PASS，
  瑞典文、MFN 與 X 轉述均去重 FILTER。
- 邊界：Sivers 與 SemiNex 是 program 當事方，兩份公司表述不是獨立 demand confirmation；SemiNex 也可能是
  capability／競爭路徑，不應自動解讀成 Sivers moat 擴大。
- 路由：既有 `lead_3a961f18b09ca9fd8c60d40209af24ce` 為 `triaged_go`；本週不追源、不抽取、不入圖。

### 3. Sivers：warrant exercise 與 share-price-linked social-tax revaluation — `research / FYI`（既有 pq1）

Sivers 同日另發布 Bootstrap 行使 warrants，以及 Q2 因股價上漲重估 social-tax liability 的公告。前者影響稀釋與
資本結構，後者屬 share-price-linked accounting effect；兩者都值得在 8/27 財報前保留，但都沒有解除 FY2025
重編、going-concern、Photonic 量產收入與 evidence-gate 問題。

- 來源：[Sivers newsroom](https://www.sivers-semiconductors.com/)
- Signal triage：兩個官方事件都有具名 counterparty／會計科目與可核對影響；代表英文 leads PASS，語言與載體
  重複 FILTER。
- 邊界：warrant exercise 不等於營運現金流改善；social-tax revaluation 也不能當作核心業務惡化或改善的代理。
- 路由：`lead_6129876cd9d82706d294e7d5b03aa8cf`、`lead_360d8205bc213c74de182069147142ca`
  均為 `triaged_go`；lifecycle 維持唯讀。

### 4. Unitree IPO：進入申購但估值 read-through 仍需隔離 — `research`（既有 parked lead）

Unitree（688836.SH）已依發行日程於 8/10 開放申購，事件從上週的 IPO 預期進到可由正式發行文件核對的階段。
Daily 策展材料另稱零售超額認購超過 8,000 倍，並推論上市後可成為 Agility／CCXI 的估值催化劑；本週搜尋能確認
發行與申購日程，但沒有取得支持 8,000 倍的發行結果原文，因此只保留 lead，不把熱度當 commercial deployment、
unit economics 或 Agility 客戶需求的證據。

- 來源：[Unitree IPO 發行與申購日程](https://www.chinadaily.com.cn/a/202607/30/WS6a6b71eea310986e2b46836d.html)、
  [Daily 策展材料](https://x.com/aleabitoreddit/status/2087000954742927390)
- Signal triage：公司、股票代碼、申購日與正式 filing 可查，故 IPO 事件 PASS；8,000 倍、US$30b+ opening value
  與 Agility read-through 在缺乏原始發行結果時不升格。
- 邊界：IPO 估值不是 humanoid 實際部署、毛利率、RaaS payback 或 CCXI 合併條件的佐證。
- 路由：既有 `lead_e1daca4662d70cba294c939a608ae05c` 維持 `parked`；Weekly 不重跑 source-trace。

## Thesis 核查

- `axt_inp`（AXT，`AXTI`）：維持 `active`；`last_checked=2026-08-04`、`next_check=2026-11-15`。
  本週 Lumentum／Coherent demand evidence 與 AXT Q2 10-Q 形成 material delta，因此出現 [155]，但沒有自動修改
  lifecycle。供給擴張、出口許可與客戶端履約仍是主要反證路徑。
- `coherent_cpo`（Coherent，`COHR`）：維持 `active`；`last_checked=2026-07-17`、`next_check=2026-10-15`。
  Q4 結果與法說支持 InP capacity／CPO ramp，但 12 月六吋 InP 產能檢核點尚未到；不提前 revise。
- `sivers`（Sivers Semiconductors，`SIVE.ST`）：維持 `review_required`；`last_checked=2026-07-26`、
  `next_check=2026-08-27`。SemiNex、warrant 與 social-tax events 都只是 pq1 leads，不能覆蓋 FY2025
  source-under-audit、重編、going-concern 與 Photonics 量產收入的人工 gate。
- 統一池已承接 lifecycle：pq2 [10] 等待 8/27，不重複列為立即決策。

## 系統健康審查（修前／修後）

### 修前

- 🟡 L8（來源獨立性）：`co:lumentum -[supplies_to]-> tech:uhp_laser` 的 `sole_source` 仍只有 Lumentum origin。
- 🟡 TICKER_MAP：`co:casela_technologies` 未登記。
- 🔴 Thesis：`sivers` 為 `review_required`；這是人工 gate，不是維護故障。
- 🟢 Engine C：41 檔全部通過 7 日 freshness 閾值，較上週 39 檔增加 2 檔。
- 🟢 Claim／EdgeAssertion 缺 CITES、重複 SourceDoc、graph schema mismatch、未處置 edge conflict、memo stale、
  financial checklist 不可跑、Research Action 待 publish、skill adapter 漂移均為 0。
- 🟢 Engine B `harvest-health=[]`；當前狀態計數為 `triaged_go=95`、`triaged_no_go=442`、`parked=81`、
  `applied=25`。

### 已修／未修邊界

- 本週沒有 health audit 指向的可確定性 code／config／ETL 維護缺陷，因此沒有為了消警報修改系統。
- Lumentum origin、Casela identity 與 Sivers lifecycle 都需要新 evidence 或使用者 authority，不以猜測修復。
- `todo sync` 首次新增 [154]–[158]，第二次同步新增 0；這是統一池正常收斂，並非 health failure。
- Engine D 常駐量測顯示 current calculator decisions 17、current non-zero live ranges 9、measured outcomes 0；
  這只是機制診斷，不作為 alpha 部位或下單指引。

### 修後

- 完整 audit 的 41/41 Engine C freshness 與其餘綠燈維持；三個既有人工／證據缺口沒有被假裝消除。
- `git ls-files library/private` 將在提交前再驗證；private authority 不進 Git。

## 投組風險完整快照與較前次趨勢

- 今天不用啟動投入評估；距下一次每 5 個完整交易日的 baseline 提醒約 1 個 session。
- 自有現金可部署：USD 30,567（Portfolio CASH USD 31,192 − cash floor USD 625）；Alpha／Beta 共用。
- 本輪可人工評估上限：USD 0；這是今日 cadence／風控後上限，不是下單金額。
- 未動用貸款額度：USD 187,477；已借款 USD 0、估計月息 USD 0。未動用額度不算 NAV 或自有現金。
- 總曝險：1.03x（policy cap 1.75x）；自有資本歸零門檻約為指數跌 97%。
- 槓桿 ETF 資金占比 7.8%；換算槓桿曝險 18.2%；已提款貸款占 NAV 0%；合計換算曝險 18.2%。
- Alpha 總量 2.2%，僅警告、不阻擋。
- 已知 issuer 曝險：TSMC 30.9%（直接 17.5%／間接 13.3%）為集中警戒；Micron 2.2%、FRA:2DG 2.0%、
  Alphabet 1.6%、NVIDIA 1.0%、Tesla 0.8%、TYO:7803 0.2%。
- Look-through coverage 為 `partial`；未建模 `00981A.TW`、`DRAM`、`LON:VWRA`、`QQQ`、`SOXX`、`TQQQ`。
- 台股 technical lane 中 00631L／00981A／0050／006208 因 TWSE 官方日期較 Yahoo 新而暫停新增；這是商品級
  timing quarantine，不是 Engine C 41 檔 health freshness 失敗，也沒有觸發賣出。
- 較 2026-08-09：總曝險不變；槓桿 ETF 資金占比 +0.3 個百分點；換算槓桿曝險 +0.5 個百分點；
  Alpha +0.1 個百分點；TSMC 已知曝險 +0.3 個百分點；自有現金可部署約 +USD 85。沒有 hard-cap 跨越。

## Triage 稽核

本輪三個 active themes 各做 2–3 組過去 7 天搜尋，並掃近期 Engine B 策展／公司官方來源；同一事件、語言版本
與載體重複折成代表性 cluster 後，共 10 個 candidate events／clusters。

**通過（6 個）：**

- Lumentum FY2026 Q4：UHP CPO laser demand、initial ELS order、NPO engagement 與指引均可查；既有 leads PASS／applied。
- Coherent FY2026 Q4：Datacenter & Communications 成長、六吋 InP 擴產與 CPO/NPO timing 可查；既有 leads PASS／applied。
- Sivers–SemiNex US$3.4m program：具名 counterparty、產品 scope 與 2H 2027 時點可查；官方英文代表 lead PASS。
- Sivers Bootstrap warrant exercise：具名資本結構事件可查；官方英文代表 lead PASS。
- Sivers social-tax liability revaluation：具名會計科目與時點可查；官方英文代表 lead PASS。
- Unitree IPO 申購進展：公司、股票代碼與 8/10 申購日程可查；既有 lead PASS 後因原始結果未果 parked。

**篩掉／去重（4 個）：**

- OCP APAC「Ayar／Lightmatter 將有公告」：搜尋未找到能對應追蹤公司、產品、order 或部署的具體新公告；
  generic event calendar 不另建 topic。
- Sivers–SemiNex 的 MFN、瑞典文與 X 轉述：都與官方英文頁同一 origin_event；作者對 product overlap／
  類比其他交易的推論沒有新增可引用 atom。
- Unitree「8,000 倍超額認購／US$30b+ 開盤」：本週未取得原始發行結果；只保留 trace backlog，不能當 evidence。
- Photonics 股價反彈、長期持有與 sector rotation 貼文：雖點名 SIVE／LITE／COHR／AAOI，核心是市場情緒，
  沒有新增可查公司事件。

本週 PASS 率為 6/10，只作事後稽核，不是配額。六個 PASS clusters 都已有 stable lead，因此
`pending_leads.json` 沒有 Weekly 重複寫入。

## 建議 onboard 候選

- **SemiNex（private）**：若後續一手文件能釐清 US$3.4m program 的付款、製造分工、customer sampling 與
  qualification scope，可作 Sivers 的 capability／counter-path 節點；目前不建供應邊。
- **Unitree（688836.SH）**：正式上市與發行結果可作 humanoid unit economics、財務與估值比較節點；在 filing
  research 完成前，不把 IPO 熱度外推到 Agility。
- **本週無其他新候選**：Aeva 已於本週另一流程完成 onboard，Coherent／Lumentum／Sivers 已在圖中。

## pq2（只列真正需使用者決定的穩定編號）

### [154] Aeva Optical Connectivity：補完整 Decision research — `decision_review`

**TL;DR：** Aeva Technologies（`AEVA`）已由一手 8-K 確認成立 Optical Connectivity 業務，並以自有 high-power
optical-source technology 參與 unnamed customer 的 NPO solution，目標供 unnamed hyperscaler 於 2027 下半年
初始部署、2028 production ramp；但目前 financial／commercial／counter-path assessment 幾乎是空的。

- 公司／ticker：Aeva Technologies（`AEVA`）；既有核心業務是 FMCW 4D LiDAR，本項是 AI data-center NPO 新業務線。
- 誰供應誰／產品：Aeva → NPO optical-source technology；JDA 對手與 hyperscaler 均未具名，不能推定為 Sivers 客戶。
- 事件成熟度：JDA／guided deployment，不是 qualified volume production；目前 financial snapshot 缺失。
- 投資意義：若 Aeva 能把 LiDAR 光源能力轉為可量產 NPO，會新增 CPO／NPO competitor／integrator 路徑；若客戶、
  毛利、runway 與 backlog 不成立，這只是一個尚未商業化的新敘事。
- 證據／反證限制：缺 counter-path、backlog、customer concentration、dilution、gross-margin trend、runway、
  valuation payoff；唯一具體商業節點仍是 issuer 自報的 unnamed JDA。
- `154 go` 的 exact authority：只把 `wo_227a34d29c647e52088ffc623336cb5b` dispatch 到 pq1，補上述 research gaps，
  取得新 receipt 後才 reassess。這不授權 graph admission、thesis mutation、paper／live position、Sheet 修改或下單。

### [155] AXT：InP evidence delta 後的 bounded 複查 — `decision_review`

**TL;DR：** AXT（`AXTI`）供應 InP substrates，已具名連到 Coherent、Lumentum 與 Casela；本週 Lumentum／Coherent
對 InP capacity、ELS／CPO demand 的新證據觸及既有 thesis 因果結構，因此統一池要求是否重開 bounded research。
目前 Action Card 本身仍為 `NO_ACTION`；本項是在問要不要花 pq1 成本重新核對，不是資本建議。

- 公司／ticker：AXT（`AXTI`）；上游 InP／GaAs／Ge substrate supplier。
- 誰供應誰／產品：AXT → Coherent／Lumentum／Casela 的 InP substrate／capacity commitments；下游用於 EML、CW laser、
  photodiode 與 CPO／transceiver。
- 事件成熟度：AXT Q2 10-Q 與具名 agreements 已有 issuer filing；Lumentum／Coherent demand evidence 變強，
  但客戶端採購量、qualification、良率、逐季履約與完整合約仍不透明。
- 投資意義：material delta 可能強化 near-term InP bottleneck，但 AXT lifecycle v4 同時受 JX／Sumitomo 大幅擴產與
  中國出口許可約束，不能把 CPO demand 等同 AXT 的結構性議價權。
- 證據／反證限制：現有供應承諾多為 AXT 自報；Reuters 只獨立支持出口許可延遲造成中斷，未驗證合約履行。
- `155 go` 的 exact authority：只重新 dispatch cohort 的 bounded research work order 到 pq1，聚焦新 material evidence、
  客戶端履約與出口許可，再用新 receipt reassess；不改 `axt_inp` lifecycle、不自動入圖、不改 paper／live／Sheet、不下單。

### [157] NVIDIA：CPO supply-chain evidence delta 後的 bounded 複查 — `decision_review`

**TL;DR：** NVIDIA（`NVDA`）既有 Vera Rubin／Spectrum-X thesis，本週 Coherent、Lumentum 的產能與 photonics evidence
使同 cohort 出現 material delta。Current card 仍是 `NO_ACTION`，且核心 disproof 仍是 Vera Rubin 延後或 Data Center
營收／gross-margin 同步惡化；本項只問是否重跑一次 bounded research／reassess。

- 公司／ticker：NVIDIA（`NVDA`）。
- 誰供應誰／產品：NVIDIA 提供 Blackwell、Vera Rubin、Spectrum-X；並投資／合作 Coherent、Lumentum 擴充 CPO、
  pluggable optics 與 laser capacity。Broadcom 提供 system-level CPO counter-path。
- 事件成熟度：Coherent／Lumentum 的 capacity commitments 與公司文件為真金白銀的供應端 corroboration，但仍不是
  hyperscaler 對 Vera Rubin／Spectrum-X 的逐項 production acceptance 或採購量。
- 投資意義：新 evidence 強化 NVIDIA 光互連供應鏈正在擴產的因果橋；它不能單獨證明 NVIDIA 最終出貨節奏、
  客戶集中風險或下一季 margin。
- 證據／反證限制：缺具名 hyperscaler acceptance；current execution FX 亦缺，但那屬系統資料而非本項研究授權。
- `157 go` 的 exact authority：只 dispatch `wo_838495a6e6a49a5a663aedb52b1f0ece` 到 pq1，核對 material delta 後
  取得新 receipt 再 reassess；不入圖、不改 thesis、不建立 live choice／fill、不改 Sheet、不下單。

### 不需現在決定

- [129] AAOI 的 pq1 已完成，現在只等 [134] exact disproof／catalyst gate；[129] 不吃 `go／drop／pending`。
- [10] Sivers lifecycle：等 2026-08-27 Q2／重編分辨點。
- [74] Agility：等 S-4 公開或 4Q 2026 closing／AGLT 掛牌。
- [81] 舊 Meta Vistara RA：等 2026-09-01 自動到期；不得 apply。
- [134] AAOI disproof：等 Q3 2026 guidance 後再以 Q4 revenue 下緣設定門檻。
- [139] Lumentum：等 2026-08-20 FY2026 10-K 完整 cash-flow statement。
- [156] IQE：等執行面 context／匯率資料恢復。
- [158] Sivers decision：等匯率資料恢復；lifecycle 的 8/27 gate 仍由 [10] 承接。
