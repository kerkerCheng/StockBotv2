# 週審查 — 2026-08-09

> 掃描窗為 2026-08-02～2026-08-09。依本機 Weekly v1.2，本週只做 topic discovery、完整本機健康審查、
> lifecycle 唯讀提醒與統一 pq2；沒有執行 source-trace、claim extraction、graph admission、lifecycle 結論修改，
> 也沒有建立 PR／Issue。

## 30 秒 brief

- 🟢 本週 CPO／InP laser 的增量訊號相當密集：VIAVI 被轉述已有 CPO testing POs 與當季收入、Aeva 新增
  optical-connectivity JDA、AAOI 說明產能／qualification／CPO 時程、MACOM 被轉述提到 InP DFB laser shortage，
  Lumilens 則出現融資與大型客戶協議線索。七個去重後的 PASS topic 全都已由 daily 建成 `triaged_go` lead，
  Weekly 沒有重複註冊或提前追原文。
- 🟡 這些材料同時帶有反證價值：Aeva 可能是新的 CPO／NPO optical-source 競爭者；AAOI 的轉述若成立，
  其首代 CPO 參與受自身 laser capacity 約束。兩者都不能直接外推成 Sivers 受益。
- 🟢 完整本機 health audit 顯示 Engine C 39/39 檔 freshness 通過；Claim／EdgeAssertion provenance、schema、
  edge conflict、financial checklist、Research Action publish、skill adapter 均無新故障。
- 🟡 既有證據缺口仍是 Lumentum → UHP laser 的 `sole_source` 只有 Lumentum origin，以及
  `co:casela_technologies` identity 未登記；這兩項都不能靠猜測自動消除。
- 🔴 `sivers` 維持 `review_required`，人工分辨點仍是 2026-08-27；本週不改 lifecycle。
- 🟡 投組總曝險由 1.02x 小幅升至 1.03x；槓桿 ETF 資金占比 7.5%、換算槓桿曝險 17.7%、已提款貸款 0%；
  TSMC 已知至少 30.6% 仍是集中度警戒，但本週沒有風控門檻跨越。
- 📋 `todo sync` 新增 [107]–[110] 四個 system-derived 等事件項，沒有新增立即人工決策；現在唯一需決定的是
  [106] Agility bounded gap research。其餘九項都在等待既定事件或系統資料恢復。

## Topic Digest

### 1. VIAVI：CPO 測試 POs 與收入開始出現 — `research`（既有 pq1）

Daily 策展材料轉述 VIAVI 法說：公司已有 CPO testing POs、當季已有 CPO revenue，並預期 12 月開始加速；
同一材料另稱 1.6T ramp 很快、明年可與 800G 達到相近規模。若原文與 scope 成立，這會延續上週 FormFactor
的觀察：量產訊號不是先出現在所有光引擎／laser 廠，而可能先出現在測試設備與 production infrastructure。

- 來源：[Daily 策展材料](https://x.com/aleabitoreddit/status/2085174977272360987)
- Signal triage：具名公司、PO、收入季度與加速時間都可查，直接命中 CPO testing theme。
- 邊界：本週沒有核對 VIAVI transcript；材料對 NVIDIA、Ayar、FormFactor 的跨公司延伸都還不是 evidence。
- 路由：既有 `lead_3ecbb88f2a25a59854e1aadecf44f1da` 為 `triaged_go`；Weekly 不重複註冊。

### 2. Aeva：由 LiDAR 延伸至 AI data-center optical connectivity — `research / onboard 候選`

材料稱 Aeva 新增 Optical Connectivity 業務，與 optical-engine provider 簽 JDA，目標為 major hyperscaler
在 2027 下半年部署、2028 production ramp，並將沿用既有 high-volume manufacturing／foundry supply chain。
若成立，Aeva 不只是 Sivers 可能的下游 read-through，也可能是 ELSFP／on-chip light-source 的新競爭或整合節點；
不能因既有 LiDAR 關係就假定 Sivers 是該 JDA 的 laser supplier。

- 來源：[Daily 策展材料](https://x.com/aleabitoreddit/status/2085217487864643658)、
  [Aeva 既有 SOA 技術基準](https://investors.aeva.com/news-releases/news-release-details/aeva-unveils-industry-leading-high-power-semiconductor-optical)
- Signal triage：JDA、部署時間、production ramp 與 manufacturing scope 都可查，且帶來新的 company／counter-path。
- 邊界：本週沒有追 Aeva Q2 原文；`Aeva → Sivers`、hyperscaler 身分與產品 BOM 都未確認。
- 路由：既有 `lead_1aa835b32dc4e06468322d132acc925a` 為 `triaged_go`；公司研究完成前不 prepare onboard action。

### 3. AAOI／MACOM：InP laser shortage 與產能約束的兩個潛在獨立 origin — `research`（既有 pq1）

AAOI earnings 的三則策展材料可聚成同一事件：1.6T qualification、800G／1.6T 與 ELSFP 產能路徑、
2028 約 400,000 件／月 ELSFP 目標，以及需求比擴產後供給高 20%–40% 等具體說法；另有材料稱 AAOI 因要優先
供應自家 transceiver，沒有足夠 laser capacity 參與首代 CPO。MACOM 材料則逐字轉述「客戶因 InP DFB laser
一般性短缺而帶著 urgency 前來」。若兩份公司原文成立，它們能提供不同於 Sivers／Lumentum 自報的需求側佐證；
但仍不能證明 Sivers qualification、sole_source 或實際訂單。

- 來源：[AAOI 產能與時程材料](https://x.com/aleabitoreddit/status/2085499853099208716)、
  [AAOI 首代 CPO capacity 材料](https://x.com/aleabitoreddit/status/2085603590903902621)、
  [MACOM shortage 材料](https://x.com/aleabitoreddit/status/2085511646257332581)
- Signal triage：公司、數字、產品、qualification／production 時間與 transcript 措辭均可逐字查核；
  AAOI、MACOM 是潛在不同 `origin_entity`。
- 邊界：兩份正式 transcript 都未由 Weekly 核對；「中國落後 2–3 年」、「Sivers 因而受益」與客戶身分是
  策展者推論，不能混入原始公司 claim。
- 路由：AAOI 相關 `lead_ca5b0998d48307f3e510f657f0bef877`、
  `lead_9adb031e86660441500e62d9adc0bafe` 與 MACOM `lead_65cd6e71ec67ef60eb999082611afa8b`
  都已 `triaged_go`；既有未追蹤 AAOI 原始文件屬其他流程，本週未碰觸或納入 commit。

### 4. Lumilens：融資與大型客戶協議可能補 POET／Sivers 商業化橋 — `research / onboard 候選`

材料稱 Lumilens 以約 US$5.5b valuation 募資 US$700m，並有 multi-billion-dollar customer agreement；
策展者再把它連到 POET 的既有 PO／合約與 Sivers。若官方融資、客戶協議與產品 scope 都成立，Lumilens
可成為 POET／Sivers 路徑上的新商業化節點；目前只能視為值得追的 lead，不能把多層 OSINT mapping 當供應邊。

- 來源：[Daily 策展材料](https://x.com/aleabitoreddit/status/2085628664528662818)
- Signal triage：公司、估值、募資、客戶合約與既有 PO 金額均可查，可能提供新 origin。
- 邊界：本週未取得 Lumilens 融資公告、客戶協議或 POET 合約原文；top-3 hyperscaler 與 Sivers 連結未確認。
- 路由：既有 `lead_0372f419a6423004be01bfb464111aa8` 為 `triaged_go`；不直接 onboard。

### 5. 光收發器進口限制草案：Western supply-chain read-through 仍只是政策 lead — `research`（既有 pq1）

材料轉述美國政府正在研擬限制新的中國 optical transceiver／data-center devices，並可能豁免部分非中國供應商。
若正式規則成立，會改變 Innolight／Eoptolink 與 AAOI／Sivers／Lumentum／Coherent 的競爭環境；但「草案」不等於
已生效規則，產品 scope、豁免、既有設備與執法時點都可能翻轉投資含義。

- 來源：[Daily 策展材料](https://x.com/aleabitoreddit/status/2084597612175618342)、
  [轉載 Reuters 的 discovery carrier](https://www.usnews.com/news/top-news/articles/2026-08-04/exclusive-trump-administration-drafting-ban-on-chinese-data-center-devices-sources-say)
- Signal triage：具名公司與政策措辭可查，且是供應鏈結構性反證／催化劑。
- 邊界：本週未追政府文本，也未把政策草案視為任何公司的營收或市占證據。
- 路由：既有 `lead_7f66b743a034c41f6388aa800f333e62` 為 `triaged_go`。

### 6. Unitree IPO：Agility／CCXI 的 public-market 估值參照 — `research`（既有 pq1）

材料稱 Unitree 將於本月以約 US$9b valuation IPO，並與 Agility／CCXI 約 US$2.5b pre-money 的交易估值比較。
這不是 humanoid deployment 或 unit economics 證據，但若上市文件與時間成立，會提供中美 pure-play humanoid
的估值、財務揭露與供應鏈參照，對 Agility gap research 有用。

- 來源：[Daily 策展材料](https://x.com/aleabitoreddit/status/2085644051446108223)
- Signal triage：公司、IPO 時間與估值可查，直接命中 robotics／Agility 脈絡。
- 邊界：衍生市場的 US$36.04b implied value 不等於 IPO 定價；本週沒有核對 filing。
- 路由：既有 `lead_55d4f2734afbfab750d526b824198afb` 為 `triaged_go`。

## Thesis 核查

- `axt_inp`（AXT，`AXTI`）：維持 `active`；`last_checked=2026-08-04`、`next_check=2026-11-15`。
  8/4 已因 JX／Sumitomo 擴產 revise，Weekly 不重開同一裁決。
- `coherent_cpo`（Coherent，`COHR`）：維持 `active`；`next_check=2026-10-15`。
- `sivers`（Sivers Semiconductors，`SIVE.ST`）：維持 `review_required`；`last_checked=2026-07-26`、
  `next_check=2026-08-27`。本週 Aeva、AAOI、MACOM、Lumilens 都只是 pq1 lead，不能覆蓋 FY2025
  source-under-audit、重編與 going-concern 的人工 gate。
- 統一池已承接 lifecycle：pq2 [10] 與 decision review [42] 均等待 8/27，不重複列為立即決策。

## 系統健康審查（修前／修後）

### 修前

- 🟡 L8（來源獨立性：供應商自報不能當 `sole_source` 獨立佐證）：
  `co:lumentum -[supplies_to]-> tech:uhp_laser` 仍只有 Lumentum origin。
- 🟡 TICKER_MAP：`co:casela_technologies` 未登記。
- 🔴 Thesis：`sivers` 為 `review_required`；這是人工 gate，不是維護故障。
- 🟢 Engine C：39 檔全部通過 7 日 freshness 閾值。
- 🟢 Claim／EdgeAssertion 缺 CITES、重複 SourceDoc、graph schema mismatch、未處置 edge conflict、memo stale、
  financial checklist 不可跑、Research Action 待 publish、skill adapter 漂移均為 0。
- 🟡 第一次風險快照在受限 sandbox 因 Windows socket 權限拿不到 Google Sheet；以既有唯讀權限重跑後成功，
  holdings 與 capital authority 完整恢復，因此不是資料遺失或 repo blocker。

### 已修／未修邊界

- 本週沒有需要修改 code／config 的確定性維護缺陷。
- Lumentum origin、Casela identity 與 Sivers lifecycle 都需要新 evidence 或使用者 authority，不以猜測消警報。
- pq2 sync 新增 [107]–[110] 的 `waiting_on` 分類是統一池正常收斂，不是待人工修的 health failure。

### 修後

- 重跑完整 audit 後，Engine C 39/39 freshness 與其餘綠燈維持；三個既有人工／證據缺口沒有被假裝修掉。
- `git ls-files library/private` 仍為空；兩個既有未追蹤 AAOI raw 檔不在本週提交 pathset。

## 投組風險完整快照與較前次趨勢

- 今天不用啟動投入評估；距下一次每 5 個完整交易日的 baseline 提醒約 1 個 session。
- 自有現金可部署：USD 30,482（Portfolio CASH USD 31,103 − cash floor USD 620）；Alpha／Beta 共用。
- 本輪可人工評估上限：USD 0；這是今日 cadence／風控後上限，不是下單金額。
- 未動用貸款額度：USD 186,133；已借款 USD 0、估計月息 USD 0。未動用額度不算 NAV 或自有現金。
- 總曝險：1.03x（policy cap 1.75x）；自有資本歸零門檻約為指數跌 97%。
- 槓桿 ETF 資金占比 7.5%；換算槓桿曝險 17.7%；已提款貸款占 NAV 0%；合計換算曝險 17.7%。
- Alpha 總量 2.1%，僅警告、不阻擋。
- 已知 issuer 曝險：TSMC 30.6%（直接 17.6%／間接 12.9%）為集中警戒；Micron 2.1%、FRA:2DG 1.9%、
  Alphabet 1.7%、NVIDIA 1.1%、Tesla 0.8%、TYO:7803 0.2%。
- Look-through coverage 為 `partial`；未建模 `00981A.TW`、`DRAM`、`LON:VWRA`、`QQQ`、`SOXX`、`TQQQ`。
- 較 2026-08-02：總曝險約 +0.01x；槓桿 ETF 資金占比 +0.1 個百分點；換算槓桿曝險 +0.6 個百分點；
  Alpha +0.3 個百分點；TSMC 已知曝險 -1.2 個百分點。這些是快照差，不代表新交易歸因；本週沒有 hard-cap
  跨越或 live action。

## Triage 稽核

本輪三個 active themes 各做 2–3 組過去 7 天搜尋，並掃近期 Engine B 策展材料；去重後得到 11 個
candidate events／topic clusters。

**通過（7 個）：**

- 中國 optical transceiver／data-center device 進口限制草案：具名政策措辭與公司 scope 可查；既有 lead PASS。
- VIAVI CPO testing POs／當季 revenue／12 月加速：具體公司與時間可查；既有 lead PASS。
- Aeva Optical Connectivity JDA：具體 deployment／production 年份與 manufacturing scope 可查；既有 lead PASS。
- AAOI Q2／CPO capacity cluster：具體產能、qualification、需求缺口與產品時程可查；三則材料聚成同一 topic。
- MACOM InP DFB shortage：潛在不同 origin_entity，且有 transcript 措辭可查；既有 lead PASS。
- Lumilens 融資／客戶協議：可能補 POET／Sivers 商業化橋；既有 lead PASS。
- Unitree IPO／估值：可由上市文件核查，提供 Agility public-market 參照；既有 lead PASS。

**篩掉／去重（4 個）：**

- Sivers–GlobalFoundries、Sivers–POET 舊合作頁：都是掃描窗外既有基準，沒有本週新公司動作。
- Aeva 1 月 SOA 公告：可作技術基準，但不是本週 JDA 的新事件本身，不另建 lead。
- Agility 7 月 Fremont facility 與既有 Toyota／GXO deployment：均在掃描窗外；本週沒有新的 Digit 客戶部署。
- 8/4 Physical AI arXiv 論文與一般 humanoid capability 文章：沒有可直接連到追蹤公司投資 thesis 的新商業事件。

本週 PASS 率為 7/11，只作事後稽核，不是配額。七個 PASS topic 都已有 stable lead，因此
`pending_leads.json` 沒有 weekly 重複寫入。

## 建議 onboard 候選

- **Aeva（AEVA）**：若 Q2 官方文件確認 Optical Connectivity JDA、產品 scope 與 2027／2028 時程，應作為
  CPO／NPO optical-source 的新競爭／整合節點，而不是預設為 Sivers 下游。
- **VIAVI（VIAV）**：若 transcript 確認 testing POs 與 CPO revenue，可作 FormFactor 之外的量產前置 indicator。
- **Lumilens（private）**：若融資與 customer agreement 原文成立，可補 POET／Sivers 商業化路徑；目前不建供應邊。
- **Unitree（擬上市）**：待正式 filing 後可作 humanoid unit economics、產能與估值比較節點；目前只留 candidate。

## pq2（只列真正需使用者決定的穩定編號）

### [106] Agility Robotics：FCC robotics policy 後的公司級補缺口研究 — `decision_review`

**TL;DR：** FCC 的 tier-1 文件已確認「foreign-produced advanced robotic devices」被納入 Covered List，
但它不是 China-only 禁令、沒有點名 Agility 受益，也不證明 Digit 不屬政策範圍。RA apply 後產生的 Agility
Decision Shadow 仍是 `unresolved`／research-incomplete；[106] 只是在問要不要投入一輪 bounded gap research。

- 公司／ticker：Agility Robotics（Digit humanoid）；目前 public exposure 是 SPAC `CCXI`，交易完成後預定
  `AGLT`。Decision 仍以 `company_id_hint=co:agility_robotics` 運作，沒有把未完成交易當 current ticker truth。
- 誰供應誰／產品：本事件不是供應關係。FCC policy → foreign-produced advanced robotic devices；Agility 製造 Digit。
  現有 evidence 沒有建立「政策 → Agility beneficiary」edge。
- 事件成熟度：FCC DA 26-786 dated Claim 已完成 graph admission；company-level catalyst、競爭反向路徑、
  commercial maturity、identity／market／financial checklist 與 disproof condition 仍未完整。
- 投資意義：若 Digit 的產品原產地、equipment authorization 與競爭者受限範圍能被具體確認，政策可能改變
  美國 humanoid 競爭格局；在那之前 supported sizing 維持 `[0, 0]`，沒有 paper／live permission。
- 證據／反證限制：唯一 policy origin 是 FCC；Department of War 可給 Conditional Approval；公告不追溯證明
  既有型號全面撤銷，也不等於所有中國機器人被禁。Agility 的美國零件比例不能自行證明整機 classification。
- `106 go` 的 exact authority：只 dispatch `dc_317c2897cdcffda26c2c2e0e79074670` 最新 decision 的 bounded
  research work order 到 pq1，補 company identity、政策適用、counter-path、commercial／financial evidence 與
  disproof condition；取得新 receipt 後才 reassess。這不授權 graph admission、thesis revise／retire、
  paper／live position、持股修改或下單。

### 等事件（本週不需動作）

- [10] Sivers lifecycle、[42] Sivers decision：等 2026-08-27 Q2／重編分辨點。
- [74] Agility：等 S-4 公開／4Q 2026 closing 後登記 AGLT；[75] 是重複 cohort，只沿用 [74]。
- [81] 舊 Meta Vistara RA：等 2026-09-01 自動到期；不得 apply。
- [107] AAOI、[108] AXT、[110] Meta：本輪 decision 已是 `NO ACTION`，統一池等市場資料問題解除，
  不要求使用者現在再核准研究。
- [109] IQE：等 Confidence assessment、graph counter-path 與 execution context 缺口被系統／研究流程補齊。
