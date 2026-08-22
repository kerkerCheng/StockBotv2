# 週審查 — 2026-08-23

> 掃描窗為 2026-08-16～2026-08-23。依本機 Weekly v1.2，本週只做 topic discovery、完整本機健康審查、
> lifecycle 唯讀提醒與統一 pq2；沒有執行 source-trace、claim extraction、graph admission、lifecycle 結論修改，
> 也沒有建立 branch、worktree、PR 或 Issue。

## 30 秒 brief

- 🟢 CPO 出現一個新的系統級 demand anchor：SK hynix 8/20 公布與學界共同提出的 CPO roadmap，明確把
  optical interconnect 從 rack／pod 延伸到 memory interface 與 photonic interposer。這證明 memory 廠正把 optics
  納入系統架構，但仍是 roadmap，不是量產產品、採購單或對 Ayar／Celestial／Sivers 等具名供應商的確認。
- 🟢 Robotics 出現本週唯一新 lead：Hexagon AEON 進入 Schaeffler Humanoid Gym，雙方規劃未來數年至少部署
  1,000 台，並在未來六個月開始多 use-case 的 Train–Validate–Deploy。`lead_9bea5f8821e22427497284c68f2551d4`
  已以 `structural_fact / candidate_set` PASS；公告沒有約束性採購額，未冒充 capital commitment。
- 🟡 Unitree 已於 8/19 以 `688836` 在上交所科創板上市，正式提供 pure-play humanoid 公開市場比較標的；上市與
  股本可由交易所公告核對，但首日漲幅、估值熱度不能外推成部署、毛利或 Agility／CCXI 基本面。
- ⚪ Sivers 本週沒有新的營運 atom；只有 8/27 Q2 發表會邀請。`sivers` 仍為 `review_required`，34 天未核查且
  超過自己的 30 天週期；正式分辨點仍是 8/27，本週不提前 revise／retire。
- 🟢 修後完整 health audit：Engine C 60/60 freshness 通過；Claim／EdgeAssertion provenance、schema、edge conflict、
  financial checklist、Research Action publish、skill adapter 均無新故障。唯一維護修復是把誤導的
  「Memo 新鮮度（>90 天）」改為「超過各自核查週期」。
- 🟡 既有證據／identity 缺口：Lumentum → UHP laser 的 `sole_source` 仍只有 Lumentum origin；
  `co:all_space`、`co:casela_technologies`、`co:seminex` 尚未登記 identity。這些不能靠猜測消警報。
- 🟡 投組總曝險維持 1.03x；槓桿 ETF 資金占比 7.6%、換算槓桿曝險 17.6%、已提款貸款 0%、alpha 2.0%；
  TSMC 已知至少 31.3% 仍是集中度警戒。今天 2330.TW 已到例行人工投入評估日，本輪上限 USD 1,074，
  不是下單許可。
- 📋 `todo sync` 新增 0、active 18。現在唯一需要新決定的是 [199] IQE bounded research；[202]–[204] 已排入 pq1，
  Sivers [10] 仍等 8/27，其餘為既有 waiting／deferred／in-flight 項目。

## Topic Digest

### 1. SK hynix：CPO roadmap 延伸至 memory interface — `research`（既有 pq1／parked）

SK hynix 8/20 官方說明與 UVA、UIUC、NTU、MIT、Yonsei 等研究者共同發表的 Nature Electronics roadmap。
它把 CPO 定位為解決 AI cluster bandwidth wall 的系統技術，列出每 node 超過 100 Tb/s、低於 1 pJ/bit、
chip-to-chip latency 低於 10 ns 等技術目標；長期架構以 photonic interposer 直接連接 XPU 與 memory pool。

- 來源：[SK hynix 官方 newsroom](https://news.skhynix.com/en/cpo-in-nature-electronics/)
- Signal triage：公司、技術架構、性能目標與 memory-interface 路徑均可逐字核對；它會改變 CPO candidate set 與
  system decomposition，因此屬 `structural_fact / candidate_set`。
- 邊界：官方頁只證明 SK hynix 的技術 roadmap 與開放協作意圖。Ayar、Celestial、Sivers、POET、AMS Osram 或
  microLED 商業化時點都不是該頁確認的 vendor selection；沒有採購額、qualification、量產時點或具名客戶。
- 路由：既有 `lead_f7b34fc90c9ed8c306133ea148a412aa` 已取得官方 technical context，因具名供應商推論未驗證而
  `parked`；Weekly 不重複註冊、不重跑 source-trace。

### 2. Hexagon／Schaeffler：AEON 進 Humanoid Gym，規劃至少 1,000 台 — `research`（本週新 pq1）

Hexagon Robotics 與 Schaeffler 8/19 公告 AEON 進入德國 Humanoid Gym，先以 imitation learning 與代表性工廠任務
訓練、驗證，再部署到 Schaeffler 全球工廠。公告稱未來六個月擴展多個 manufacturing workflows，並支持未來數年
至少 1,000 台 AEON 的規劃部署；Schaeffler 同時是部署方與 actuator supplier。

- 來源：[Hexagon 官方公告](https://hexagon.com/company/newsroom/press-releases/2026/towards-factory-deployment-how-aeon-is-trained-to-perform)
- Signal triage：具名雙方、機器人、訓練場域、數量與六個月驗證窗口皆可查，且是 graph 既有 Schaeffler actuator
  路徑以外的新 demand anchor；`tier=1`、`novelty`、`independent`，分類為
  `structural_fact / candidate_set`。
- 邊界：「planned rollout」不是具約束力採購最低量，公告也沒有價格、付款、逐年交付或 acceptance criteria。
  在未取得合約／deployment receipt 前，不把 1,000 台當已簽 backlog 或已部署 fleet。
- 路由：新增 `lead_9bea5f8821e22427497284c68f2551d4`，狀態 `triaged_go`；後續只由 bounded pq1 決定能否
  形成 prepared RA，本週不抽取、不入圖。

### 3. Unitree：688836 正式上市，pure-play benchmark 成形 — `research / FYI`（既有 pq1）

上交所 8/18 公告 Unitree A 股自 8/19 起在科創板交易，證券代碼 `688836`；公司總股本 404,464,340 股，
首批上市流通 30,087,720 股。這使 Unitree 從「預計 IPO」變成可由正式 filing、行情與財務資料研究的公開標的，
也為 humanoid pure-play 提供市場比較點。

- 來源：[上海證券交易所上市公告](https://www.sse.com.cn/disclosure/announcement/listing/ipo/c/c_20260818_10829204.shtml)
- Signal triage：上市日、代碼、總股本與可交易股數可查；事件屬 `financial_fact / confidence_only`，因上市本身不改變
  humanoid 供應鏈候選集合或 deployment thesis。
- 邊界：首日價格與超額認購是市場熱度，不是 humanoid unit economics、實際商業部署、毛利率或 Agility／CCXI
  合併條件的佐證。
- 路由：既有 `lead_826473daf6f4deaaff8503a106f6efd6` 已 PASS；Weekly 不重複註冊，也不把官方頁回寫成
  source-trace receipt。

### 4. Sivers：只有 Q2 發表會邀請，沒有新營運內容 — `FYI / FILTER`

8/20 官方頁只確認 8/27 發表 Q2 2026 report 並舉辦 presentation；沒有財務數字、重編結果、Photonic 量產收入、
客戶 qualification 或新訂單。這是 lifecycle 分辨點的 calendar heartbeat，不值得用 Weekly 另建 pq1 topic。

- 來源：[Sivers 官方邀請](https://www.sivers-semiconductors.com/press/invitation-to-presentation-of-sivers-semiconductors-q2-2026-report/)
- 路由：daily 已有代表 lead；瑞典文／MFN 版本為同一事件重複。正式 8/27 文件出現後再由既有 harvest／lifecycle
  流程處理，本週不提前核查。

## Thesis 核查

- `axt_inp`（AXT，`AXTI`）：維持 `active`；`last_checked=2026-08-04`、`next_check=2026-11-15`。
  本週沒有新的 lifecycle disproof 結論；JX／住友擴產、出口許可與長約履約仍是主要反證路徑。
- `coherent_cpo`（Coherent，`COHR`）：維持 `active`；`last_checked=2026-07-17`、
  `next_check=2026-10-15`。SK hynix roadmap 是 CPO demand context，不是 Coherent design-win 或 12 月六吋 InP
  產能倍增的完成證明。
- `sivers`（Sivers Semiconductors，`SIVE.ST`）：維持 `review_required`；`last_checked=2026-07-26`、
  `next_check=2026-08-27`、週期 30 天。34 天 freshness 提醒已成立，但既有人工決議就是持有至 8/27 分辨點；
  本週沒有新報表可供 revise／retire。
- 統一池仍由 [10] 承接 Sivers lifecycle，等待 8/27；Weekly 不重複建立編號。

## 系統健康審查（修前／修後）

### 修前

- 🟡 L8（來源獨立性）：`co:lumentum -[supplies_to]-> tech:uhp_laser` 的 `sole_source` 仍只有 Lumentum origin。
- 🟡 TICKER_MAP：`co:all_space`、`co:casela_technologies`、`co:seminex` 未登記。
- 🔴 Thesis：`sivers` 為 `review_required`；這是人工 gate，不是維護故障。
- 🟡 Memo：Sivers 34 天未核查、超過自己的 30 天週期；audit 舊標題卻寫「>90 天」，人類可讀語意錯誤。
- 🔴 managed sandbox 內第一次 audit 無權執行 `Get-Acl`，因此 fail closed 顯示 Engine C private root 非 owner-only。
  這是 sandbox 可見性，不是 authority ACL 已證實漂移。

### 已修／未修邊界

- 修正 `query/health_audit.py` 的 memo section 標題為「超過各自核查週期」，並新增 regression test；沒有更改
  freshness 判斷、lifecycle 日期或 Sivers 狀態。
- 使用同一支 audit 在 managed sandbox 外唯讀重跑，owner-only validation 通過，Engine C 60/60 freshness 與
  financial checklist 均正常；沒有修改 private ACL、SQLite 或 pointer。
- Lumentum origin 與三個 identity gap 需要新 evidence／確切法律實體與 ticker authority，不以猜測修復。
- Engine B `harvest-health=[]`；狀態計數為 `triaged_go=100`、`triaged_no_go=454`、`parked=139`、`applied=34`。
- Engine D 常駐量測為 current calculator decisions 43、current non-zero live ranges 14、measured outcomes 0；
  這是機制診斷，不作為 alpha 部位尺寸或下單指引。

### 修後

- 🟢 Engine C 60/60 在 7 日 freshness 閾值內；財務核驗清單可跑。
- 🟢 Claim／EdgeAssertion 缺 CITES、重複 SourceDoc、schema mismatch、active edge conflict、待 publish RA、
  skill adapter drift 均為 0。
- 🟡／🔴 剩餘項目都是明示的 evidence／identity／lifecycle blocker，沒有被維護修復假裝消除。

## 投組風險完整快照與較前次趨勢

- 今天應啟動人工投入評估；每 5 個完整交易日的 baseline 本期已到，候選為 `2330.TW`。
- 自有現金可部署：USD 30,632（Portfolio CASH USD 31,261 − cash floor USD 629）；Alpha／Beta 共用。
- 本輪可人工評估上限：USD 1,074；這是 cadence／單輪預算／風控後上限，不是下單金額。
- 未動用貸款額度：USD 188,561；已借款 USD 0、估計月息 USD 0。未動用額度不算 NAV 或自有現金。
- 總曝險：1.03x（policy cap 1.75x）；自有資本歸零門檻約為指數跌 97%。
- 槓桿 ETF 資金占比 7.6%；換算槓桿曝險 17.6%；已提款貸款占 NAV 0%；合計換算曝險 17.6%。
- Alpha 總量 2.0%，僅警告、不阻擋。
- 已知 issuer 曝險：TSMC 31.3%（直接 18.0%／間接 13.3%）為集中警戒；Micron 2.3%、FRA:2DG 1.8%、
  Alphabet 1.6%、NVIDIA 1.0%、Tesla 0.8%、TYO:7803 0.2%。
- Look-through coverage 為 `partial`；未建模 `00981A.TW`、`DRAM`、`LON:VWRA`、`QQQ`、`SOXX`、`TQQQ`。
- `2330.TW` 最新完整交易日為 2026-08-21，單日 +1.5%；它只有例行 baseline，沒有相對加碼證據。
  00631L／00981A／0050／006208 仍因 TWSE 官方日期較 Yahoo 新而暫停新增。
- 較 2026-08-16：總曝險不變；槓桿 ETF 資金占比 -0.2 個百分點；換算槓桿曝險 -0.6 個百分點；
  Alpha -0.2 個百分點；TSMC 已知曝險 +0.4 個百分點；自有現金可部署約 +USD 65。沒有 hard-cap 跨越。

## Triage 稽核

三個 active themes 各做 2–3 組過去 7 天搜尋，並盤點 8/16 之後 Engine B 的 83 筆新增／新發現 leads；
排除 46 筆 Form 4 後，再把同事件、語言版本與載體重複折成 8 個 candidate clusters。

**通過（4 個）：**

- SK hynix CPO／memory-interface roadmap：官方架構與性能目標可查；既有 lead 已完成 technical-context 研究並 parked。
- Hexagon AEON／Schaeffler Humanoid Gym：具名雙方、至少 1,000 台規劃與六個月窗口可查；本週唯一新 PASS lead。
- Unitree `688836` 正式上市：交易所公告可查；既有 daily lead 承接，分類為低決策影響的財務事件。
- 策展來源主動警告「Innolight 取得 NVIDIA NPO order」等流傳截圖為偽造：對 provenance／candidate-set 有反證價值；
  既有 `lead_c305e0153545aec5bef3198d76a2b56a` 已 PASS，未把偽造內容當 evidence。

**篩掉／去重（4 個）：**

- Sivers Q2 presentation 邀請：只有日期與 webinar，無營運 atom；瑞典文／MFN 版本同事件去重。
- AAOI／LITE／SIVE「整條 optics shortage」社群 composite：核心已由既有 earnings／filing leads 覆蓋，沒有新的
  獨立 origin 或具名 commitment。
- Unitree「能跑贏 Usain Bolt」與上市估值外推 Agility：前者是公司宣稱的表演能力，後者是市場情緒；都不形成
  factory deployment 或 unit economics 證據。
- Schaeffler 8/13 formed strain-wave gearbox 公告：技術數字具體，但在本週 7 日窗口外，僅作 Hexagon topic 背景，
  不重複註冊成 Weekly lead。

本週 cluster PASS 率為 4/8，只作事後稽核，不是配額。四個 PASS 中三個已有 stable lead；因此
`pending_leads.json` 只新增 Hexagon／Schaeffler 一筆。

## 建議 onboard 候選

- **Unitree Robotics（`688836`）**：上市障礙已解除；下一步應從交易所 filing 建立 legal identity、研究 ticker、
  財務與 unit economics，而不是沿用首日估值貼文。純候選，本週不自動登記或入圖。
- **Hexagon Robotics／Hexagon AB**：先由 pq1 確認實際 contracting entity、Schaeffler 1,000 台規劃是否有 binding
  purchase／acceptance，以及 actuator 供應雙向關係；形成 prepared action 後才進 pq2。
- **SK hynix（`co:sk_hynix`）**：identity registry 已有、Neo4j 尚無公司節點。官方 roadmap 足以讓它成為
  memory-side system research 候選，但不足以建立 Ayar／Celestial／Sivers 等 supplier edge。

## pq2（只列真正需使用者決定的穩定編號）

### [199] IQE：MACOM 客戶端資本承諾後的 bounded 複查 — `decision_review`

**TL;DR：** IQE plc（`IQE.L`）已由一手 regulatory announcement 確認：客戶 MACOM 完成 £45m 戰略投資
（£30m equity＋£15m 無息 convertible notes），雙方同時簽訂 long-term supply agreements。這是客戶把資本交給
供應商的具方向性事件，可能提高 IQE 在 InP／AI photonics 候選中的排序；但協議產品組合、採購量、期限、排他性、
收入與 production conversion 都未披露，因此 current card 仍是 `REVIEW`，不是買進或部位尺寸建議。

- 公司／ticker：IQE plc（`IQE.L`）；compound-semiconductor epiwafer supplier。
- 誰供應誰／產品：IQE → MACOM 的 long-term supply agreements；IQE 同期稱 data-centre／AI optical photonics 的
  InP demand 加速，但沒有證明 MACOM 協議全部屬 InP 或 CPO。
- 事件成熟度：投資已完成、協議已簽，強於純 roadmap；但缺 purchase minimum、qualification、volume schedule 與
  counterparty-side filing corroboration。
- 投資意義：customer-to-supplier payment direction 是瓶頸性的重要離散訊號；若後續顯示只是一般融資、協議無最低量
  或沒有轉成 production revenue，排序提升就不成立。
- 現有 disproof：Tower 或主要客戶宣布第二家合格 InP epiwafer supplier；IQE 2026 photonics／InP 相關營收沒有連續
  兩季 YoY ≥20%；或 Tower／IQE 協議終止、縮減、未於 2027 前產生可辨識營收。MACOM 新協議需在 bounded research
  中決定是否補入，而不是 Weekly 自行改寫。
- `199 go` 的 exact authority：只 dispatch IQE 的 bounded gap research 到 pq1，核對 MACOM 協議 scope、客戶端文件、
  production conversion 與排名影響，再用新 receipt reassess。不授權 graph admission、Engine C observation、
  thesis mutation、paper／live position、Google Sheet 修改或下單。

### 不需現在決定

- [202] Coherent、[203] Lumentum、[204] Marvell 已排入 pq1，等待研究 receipt；不要重複 `go`。
- [129] AAOI 仍在 `awaiting_approval`，真正 gate 是 [134] 等 Q3 guidance 後設定 Q4 revenue disproof。
- [10] Sivers 等 2026-08-27；[81] 舊 Meta Vistara RA 等 2026-09-01 自動到期。
- [167]、[168]、[181]、[182]、[187]、[188]、[192]、[193]、[194]、[200] 均為使用者既有 deferred 項目，
  本週沒有替它們推定新授權。
