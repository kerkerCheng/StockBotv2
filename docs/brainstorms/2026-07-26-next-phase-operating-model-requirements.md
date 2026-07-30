# 盲點審查報告：下一階段 Operating Model（三個工作流＋跨代理狀態）

> 狀態：Workstream A 的 Phase I Daily Beta Technical Monitor 與 Phase II-A household capital authority
> 已於 2026-07-28 完成；退休貸款政策亦已收斂為 zero-code manual contract，**不另開 Phase II-B engine**。
> Workstream B、通用 Daily runner 重構、ETF 完整 look-through、Sheet writer 與本機 single-writer guard 仍是
> 相鄰 brainstorm，只有重複摩擦出現時才另立 plan。
>
> 本文件把三個待討論工作流收在同一個 umbrella 下：
> 1. Alpha／Beta Portfolio Sleeve Monitor
> 2. Paywall ROI／合法手動入口
> 3. Token-efficient Daily Runner
>
> Alpha／Beta 的既有深度審查仍以
> [`2026-07-26-alpha-beta-sleeve-workflow-requirements.md`](2026-07-26-alpha-beta-sleeve-workflow-requirements.md)
> 為準；本文件只定義三者如何共用 authority、Daily 介面與跨 Codex／Claude 狀態。
>
> **範圍校正（2026-07-26 使用者定案）：** primary path 是本機 Codex session＋本機 Claude Code
> session；兩者直接讀同一 repo、Neo4j、Engine C／Decision Store 與 Google Sheet，採序列切換。
> Cloud session＋MCP 只是備援，不是本階段 parity／記憶共享目標，也不在本文件新增 remote surface。

> **2026-07-30 current-state override：** household／planned-outflow／百分比 reserve 與雙 cash range 已退役。
> 現行唯一自有現金公式是 `Portfolio CASH − cash floor`，供 Alpha／Beta 共用；貸款另列額度、已借款與利息，
> 不併入現金。下文相反描述只保留歷史脈絡，current authority 以 `AGENTS.md`、canonical daily skill 與程式為準。

## 最危險的三個盲點（先看這個）

1. 🔴 **把 Codex／Claude session memory 當成共享狀態** — Codex automation 的
   `$CODEX_HOME/automations/<id>/memory.md` 與 Claude transcript 都是 provider-local cache；若其中一句
   「使用者已 go」能覆蓋 `todo_pool.json`、Research Action receipt、Decision Store 或 lifecycle，換工具後就會
   重複詢問、重複 apply，甚至把未完成動作誤認為完成。
2. 🔴 **擊破 paywall，卻沒有合法保存與正確引擎落點** — DIGITIMES 的 ABF／PCB lead time 是帶時戳的
   supply-chain observation；即使合法訂閱並取得全文，也不應因為昂貴就升級 evidence tier，或硬塞進 Engine A。
   沒有 `local_only` 手動入口與 Engine C observation route，訂閱費只會換來更多無處安放的文字。
3. 🔴 **為省 token 把 deterministic orchestration 和高判斷風險動作包成一個黑盒** — Daily 的 harvest／ETL／
   todo sync 可合併，但 graph admission、thesis revise／retire、live facts 仍必須保留 exact artifact 與人工 gate；
   runner 變少輪不能等於權限變寬。

## 三個工作流的共同 Operating Contract

### Workstream A — Alpha／Beta Portfolio Sleeve Monitor

- 目標：讓個股 alpha cohort 與 ETF／指數／槓桿 beta sleeve 分流，Daily 只顯示 alpha exception 加一個
  beta aggregate。
- authority：Google Sheet 保存使用者核准的 `asset_type`／`strategy_sleeve`；versioned policy 保存 target bands、
  rebalance threshold、drawdown ladder、effective leverage cap 與 cooldown；Engine D 唯讀組合並產 review。
- 2026-07-28 深化：候選 sleeve 改為 `beta_core / beta_tilt / beta_leverage / alpha_single_name / cash`；
  `cash` 另分 operating floor 與 alpha reserve。Beta 進場先過 authority、core gap、leverage、liquidity、
  look-through overlap 與 cooldown gate，再由 drawdown／regime 決定部署速度；完整規則與現有持倉下限估算見
  Alpha／Beta 深度文件。
- 2026-07-28 使用者方向：beta 採 `accumulation_only`，一般回檔／熊市不賣；超過 band 時停止新增並把後續
  contribution 導向 underweight sleeve。這個偏好也涵蓋 daily leveraged ETF，但「指數長期向上」不被系統
  當成「daily 3x 終值必然向上」的事實；leverage 仍需 entry cap、stress loss budget 與產品結構例外。
- 2026-07-28 最終貸款方向：使用者目前約 30 歲、退休目標約 60 歲，目標函數是約 30 年後的
  `retirement_net_terminal_wealth` 最大化。指定額度利息按月支付、期間不攤還本金、到期一次還本；契約允許投資
  用途，故不再建立 lender-purpose／debt-service stress blocker。未動用額度仍只算 `contingent_liquidity`，不算
  NAV、deployable cash 或 alpha reserve；提款後 cash 與 debt 同時入帳。
- Engine ownership 定為 Engine D：固定 beta instrument registry／policy／permission／choice／fill 歸 D；Engine C 只供應
  price／FX／drawdown／volatility／look-through observations。固定標的不進 pq1；`HOLD`／`PAUSE CONTRIBUTION` 不進
  任何 pq，只有初次 policy、`CONTRIBUTE REVIEW` 與 `STRUCTURAL REVIEW` 進統一 pq2。3x 是可投資但非主力的
  `beta_leverage` satellite；依使用者偏積極科技型風險承受度，候選 combined cap 上修為 nominal 5–8%／
  effective 15–20%，尚未核准。
- 2026-07-28 signal／execution 校正：Engine C 對固定 universe 產 point-in-time RSI14、MACD 12-26-9、
  SMA20／50／200、252-day drawdown 與 realized volatility；槓桿商品使用 underlying `signal_benchmark`，不直接以
  TQQQ／00631L 自身複利路徑判斷水位。Engine D 先算 household／sleeve／effective-leverage hard ceiling，再讓
  signal state 只決定 discrete tranche pace。RSI／MACD／MA 不當三份獨立證據。
- 首波 universe 直接沿用目前 frozen Sheet 的 ETF／權值股：14 個商品去重為約 11 條 technical series；
  QQQ／TQQQ 共用 QQQ，0050／006208／00631L 共用 Taiwan 50。FRA:2DG、TYO:7803 暫留 alpha／single-name
  流程。偏積極型候選 guardrails 另設 tech look-through 60% warning／70% pause、single-company 30%／35%；
  全部必須改用已確認 household denominator 才能核准。
- 日線 technical refresh 不先架 server；包進現有台北 06:30 Daily 的 deterministic snapshot，按各交易所保存
  `last_complete_session`、missing-bar backfill、bounded retry 與 stale fail-closed。Phase I 已新增受控
  `scripts/daily_beta_snapshot.py` fixed entry、append-only Engine C observations 與 Sheet-conservative Engine D monitor。
  只有本機常離線且不接受隔日補跑、需要 intraday／market-close
  即時通知、每日必達 SLA 或 provider redundancy 時，才升級最小 always-on market-data worker。
- 使用者手動成交後希望由本機 session 同步 Google Sheet。現行 adapter 仍是 readonly；候選新增 explicit-fill-only
  narrow writer，要求穩定 `position_id`、pending checkpoint、exact row write、read-back digest 與 Decision Store
  reconciliation receipt。它不下 broker order，也不開放通用 Sheet range write。
- Phase I 已定：14 商品／11 series、五類監控分類、technical state／pace、Sheet reserve、stacked-leverage／tech
  proxy／known issuer cap 與 sequential contribution routing；全部維持 `paper_observation`。
- Phase II-A 已完成：私人 `Capital Authority` 保存 actual values；Portfolio cash 是自有 cash authority，reserve／
  planned outflows 與未動用 facility 分欄。Loan proceeds 不預先禁止任何標的，但只走 exact draw／instrument／tranche
  的人工 review；Daily 必須並列既有 `sheet_conservative` 與新的 household cash-supported candidate，再分開
  contingent-credit 與 manual loan-funded range，不能把額度算 NAV，也不能用較低私人 floor 靜默放寬 Phase I；
  runtime 維持 `spreadsheets.readonly`，authority／FX 失敗只降級 household path。
- 貸款政策到此收斂：不另開 Phase II-B engine、debt optimizer 或新 pq。使用者提出 exact draw 時，由 LLM 按當時
  borrowing cost、instrument／tranche、既有 leverage cap 與退休淨終值做一次性比較；每月利息若需靠賣出 beta
  支付，或扣除累計利息與到期本金後不優於無借款方案，即推翻該 tranche。broad unlevered beta 是主要候選，
  daily 3x 仍為衛星而非主力。
- Phase II 後續未定：完整 point-in-time ETF look-through、live policy promotion、explicit-fill-only Sheet
  narrow-write contract與 server promotion。另保留 zero-code-first 的問答型 LLM advisory：
  只在使用者明確提問時讀 beta monitor／Sheet aggregate 並按需補抓最新客觀資料，直接回答 rough scenario／替代策略；
  不跑每日 LLM 研究、不建 graph／新 authority、不自動進 pq，也不得放寬 deterministic hard caps。只有重複取數摩擦
  證明值得開發時，才考慮唯讀 compact context composer。
- 不可偷渡：持有一檔股票不自動等於建立 alpha cohort；ETF 不走 company onboarding；beta 急跌不自動等於買進。

### Workstream B — Paywall ROI／合法手動入口

- 目標：先量化付費牆造成的真實研究損失，再決定訂閱哪個來源；取得授權內容後仍遵守 provenance、
  storage permission 與 evidence tier。
- v0 ROI ledger 最少記：`domain`、`article_url`、`blocked_claim`、`active_thesis_impact`、
  `first_party_salvage`、`decision_changed`、`subscription_cost`、`storage_permission`。
- 候選購買門檻：滾動 30 天至少 3 個 material blocks，且至少一半無法由 tier 1–2 一手來源補回；單篇若直接
  影響重大持倉的 disproof condition，可例外人工評估。
- 合法入口：使用者以正常瀏覽器人工存取；只提供研究所需的有限 excerpt／locator 給本機 session，預設
  `local_only`。不得讓 routine 自動登入、繞過 access control、保存全文到 tracked repo，或分享帳號 cookie。
- 引擎分流：結構關係／慢變 claim 才考慮 Engine A；價格、lead time、utilization、shipment 等帶時戳內容進
  Engine C observation；純線索仍可 park 在 Engine B。
- 不可偷渡：付費不等於一手、專有數字不等於正確、同一研究機構多篇文章不等於獨立 origins。

### Workstream C — Token-efficient Daily Runner

- 目標：把零判斷或 deterministic 步驟收斂成少數本機命令，讓模型 token 集中在 triage、兩筆 priority pq1
  與 brief；不改變三道人工作業閘門。
- 建議邊界：
  1. `daily snapshot`：harvest、Engine C ETL、today、todo sync、健康摘要，輸出 compact JSON。
  2. `pq1 packet`：只把本輪上限內的 lead、既有 trace checkpoint 與必要 authority slice 送給研究模型。
  3. `dispatch`：deterministic parse 一行批次回覆，逐項 type-aware 執行；成功後才寫 completion receipt。
  4. `publish`：維持 exact pathset，不因 runner 合併而擴大 unattended Git 權限。
- 成功指標：正常無新 lead 日的 quota 消耗顯著低於首次 run；單筆 pq1 的 token 可歸因；中斷後不重讀已完成
  文件；同一核准不因換 session 重做。
- 不可偷渡：不得用縮短 prompt 省略 source-trace；不得把 `go` 推定成 live choice／fill；不得讓 compact
  snapshot 取代 underlying authorities。

## 跨 Codex／Claude：共享 authority，而不是共享敘事 memory

| 狀態 | Current-state authority | 跨工具方式 | session memory 的角色 |
|---|---|---|---|
| 政策／runbook／skill | `AGENTS.md`、`skills/`、`crons/*_prompt.md` | Git；兩端 skill adapters 由 sync script 生成 | 可摘要，不可覆寫政策 |
| pq1 注意力 | `library/leads/pending_leads.json` | 兩個本機 session 讀同一檔；Git 負責持久同步 | 只記「上次看到哪裡」的提示 |
| pq2 編號／決定稽核 | `library/leads/todo_pool.json` | 兩個本機 session 讀寫同一檔與 log | 不可宣稱某編號已 resolve |
| Research Action | server-owned action、exact ID＋digest、apply receipt | 兩個本機 session 讀同一 action store | 可提示 action ID，不是 apply receipt |
| Engine A | Neo4j | 兩個本機 session 直連同一 DB | 不保存圖的 current truth |
| Engine C | private runtime／manual observation ledger | 兩個本機 session 讀同一 private authority | 不保存 freshness 真相 |
| Engine D | private Decision Store | 兩個本機 session 讀寫同一 private authority | 不保存 choice／fill／decision truth |
| live inventory | Google Sheet | Google authority | 不複製持股數字 |
| thesis lifecycle | `thesis/lifecycle.json` | Git＋人工修改 | 不得自行 revise／retire |
| Weekly 歷史發現 | `docs/reports/weekly_scan_<date>.md` | Git | 可指向上次報告，不取代現況 |
| Codex／Claude memory | provider-local 檔案或 transcript | 不要求同步 | disposable advisory cache |

Codex 官方公開契約是：standalone scheduled task 每次 run 開一個新 chat、從 saved prompt 開始；只有
「排在既有 chat 裡的 task」才沿用該 chat context。因此目前本機看見的 automation `memory.md` 應視為
實作上的補充 cache，而不是可攜、跨 provider 或不可丟失的產品契約。可維護的長期指令仍應放 prompt、skill
與專案 authority，不應依賴該檔存在。

### 核准的 provider-neutral 完成條件

「使用者在 Claude 說了 go」本身不是完成。每個 todo 必須同時滿足：

1. 從 shared authority 重新讀 exact `n`、`type`、`ref_id`；RA 另核對 action digest。
2. 依 type 執行對應動作；失敗保留 active／authorized-but-incomplete，不先 resolve。
3. underlying authority 留下 receipt：RA apply state、Decision reassess、lifecycle edit、或其他 type-specific fact。
4. 最後才寫 `todo_pool.log`／resolution，供下一個 Codex／Claude session 重建。

本機 Claude Code 與本機 Codex 可直接完成上述四步，不需要同步各自的 session memory。正確的序列切換協定是：

1. 目前 agent 先完成、checkpoint 或明確停止寫入；不得只留下半句 transcript 當交接。
2. 下一個 agent 重新確認 branch／`git status --short`，再讀 `todo_pool.json`、exact action state 與相關
   private receipt；authority 與 memory 衝突時永遠以 authority 為準。
3. 收到 `go` 的 agent 負責完成 type-aware action；成功後才 resolve todo。若動作 partial／失敗，保留 active，
   讓另一個本機 session 可從 checkpoint 續跑。
4. 同一時間只能有一個 writer。Codex scheduled task 與 Claude Code interactive session 也算兩個 writer；
   若未來把 Weekly scheduler 搬給 Claude，必須先停用 Codex Weekly，不能雙排程並存。

Cloud session＋MCP 保留作備援：可在本機不便使用時讀 redacted brief、處理既有窄工具允許的工作，但不把
「cloud 能否完整 resolve unified todo」當成本階段需求。若未來備援使用頻率真的上升，再另立 remote parity
需求；本文件不先新增 remote tool。

## 逐視角發現

### A1 證偽官

- [🟡] **觀察**：Paywall ROI 若只記「遇到幾次」會高估聳動但無決策價值的文章。
  **修正**：購買門檻加入 `decision_changed` 與 `first_party_salvage`，不是只數 hits。
  **驗證／何時會爆**：訂閱後 90 天若沒有任何 article 改變 thesis、disproof 或 Engine C observation，ROI 假設失敗。

### A2 反身性／已被定價

- [🟡] **觀察**：付費研究可能只是比公開資訊更快，不保證形成 variant perception。
  **修正**：每個 material paid insight 仍要寫「股價隱含 X、本文支持 Y、催化劑 Z」。
  **驗證／何時會爆**：付費文章只有產業背景、沒有可證偽差異時，不計 material unlock。

### A3 證據稽核

- [🔴] **觀察**：Session memory 的自然語言摘要沒有 digest、receipt 或 point-in-time authority。
  **修正**：memory 永遠 advisory；核准前重新讀 exact item，完成後靠 authority receipt。
  **驗證／何時會爆**：刪掉所有 provider memory 後，若無法從 repo／private stores／Sheet 重建現況，設計不合格。

### A4 瓶頸壓力測試

- [🟡] **觀察**：Portfolio sleeve 把 beta 聚合後，可能掩蓋實際共同 chokepoint／factor。
  **修正**：beta aggregate 至少保留區域、產業與 effective leverage top exposures。
  **驗證／何時會爆**：所有單股 thesis 未變但科技 factor shock 造成越界時，Daily 必須仍能提出 de-risk review。

### A5 敘事 vs 數字

- [🟡] **觀察**：三個 workstream 都需要可量化 telemetry；否則只會以「感覺更省／更有用」收尾。
  **修正**：至少量測 sleeve exposure、paywall material unlock rate、每次 Daily calls／uncached input／quota delta。
  **驗證／何時會爆**：重構前後無法用同口徑比較，代表沒有驗證改善。

### B6 回測誠實官

- [🟡] **觀察**：Beta bands 與 paywall 購買門檻都可能看完結果後再調。
  **修正**：先 version policy，再做 30／90 天 forward observation。
  **驗證／何時會爆**：若每次錯過事件就改門檻，策略不可稽核。

### B7 Regime 依賴

- [🟡] **觀察**：Token telemetry 可能在「有兩筆 pq1」與「NO ACTION」日差異很大。
  **修正**：依 no-lead／triage-only／pq1／dispatch 四種 run class 比較，不拿單次平均混在一起。
  **驗證／何時會爆**：只有總 token、沒有 run class 時，無法判斷優化是否傷到研究品質。

### B8 訊號落地縫隙

- [🔴] **觀察**：付費 lead-time observation 目前可能被 park，Portfolio Sleeve 又讀不到它；研究與資本決策斷線。
  **修正**：設計 Engine C manual observation intake，並明確它何時觸發 cohort／sleeve reassess。
  **驗證／何時會爆**：取得 material paid claim 後，若只多一份筆記卻不影響任何 watch／decision，交接仍未完成。

### B9 風控／部位

- [🔴] **觀察**：跨 chat 核准若只同步 verb、不綁 exact item/digest，可能把舊的 `34 go` 套到重用編號或更新後 action。
  **修正**：authorization 綁 `n + type + ref_id + fingerprint/digest`，完成 receipt 另記。
  **驗證／何時會爆**：修改 title／digest 或 item 已 resolve 後，舊 authorization 必須 fail closed。

### C10 系統整合縫隙

- [🔴] **觀察**：Codex 排程直接寫 `master`；Claude Code interactive session 也可能同時寫同一 working tree／
  private store。即使兩邊都會讀最新 authority，並發 writer 仍可能造成 stale digest、重複 apply 或 Git 衝突。
  **修正**：維持人工序列切換；若實測常撞到排程時間，再設計 lightweight 本機 single-writer lease／abort guard。
  **驗證／何時會爆**：讓 Claude Code 在 06:30／週日 04:00 跨越排程時間執行 state mutation；Codex routine 必須
  能偵測已有 writer 並停止，而不是兩邊繼續。

### C11 單一視角風險

- [🟡] **觀察**：付費來源若集中 DIGITIMES／SemiAnalysis，可能把單一 channel-check lens 包裝成資訊優勢。
  **修正**：ROI ledger 同時記 origin concentration 與一手可驗證率。
  **驗證／何時會爆**：多篇內容實際引用同一供應鏈消息時，只算一個 origin event。

### C12 可操作性／scope

- [🔴] **觀察**：同時做 sleeve engine、付費內容 ingest、runner 重構與跨 agent orchestration，單人 scope 過大。
  **修正**：建議順序為 local handoff contract／telemetry → token runner → sleeve v0 → paywall manual route；
  single-writer guard 只有在真實排程碰撞反覆出現後再做。
  **驗證／何時會爆**：若第一階段還沒量到基準就新增多套 schema／lock／hook，代表過度設計。

## 整體可證偽條件

核心假設是「provider-neutral authorities 已足以重建現況；session memory 只需當 cache，而三個工作流可共用
同一 Daily／todo approval contract」。若刪除 Codex／Claude memory 後仍無法判斷某項是否已核准／執行，或同一
approval 在換工具後重做，則現有 authority contract 不足，必須新增 machine-readable authorization／receipt，
而不是同步自然語言摘要。

## 接下來盯什麼

1. 依 local-first 契約執行：本機 Codex／Claude Code 序列互換；cloud session＋MCP 只作備援。
2. 收集 3–7 次 Daily telemetry，依 run class 記 model calls、uncached input、quota delta 與 pq1 outcome。
3. 讓 paywall outcome 開始累積 30 天 ROI ledger，再決定是否買 DIGITIMES News。
4. 回到 Alpha／Beta 文件，核准現有資產的 core／tilt／leverage／alpha／cash 分類與最小 bands。
5. 再決定是否立項 deterministic Daily runner；只有真實發生排程／互動 session writer 碰撞，才加本機 lock。
