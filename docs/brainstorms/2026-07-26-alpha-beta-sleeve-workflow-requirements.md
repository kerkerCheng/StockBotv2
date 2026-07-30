# 盲點審查報告：Beta 地基＋Alpha 衛星的 Daily Decision Workflow

> 狀態：Phase I Daily Beta Technical Monitor 已於 2026-07-28 實作為 `paper_observation`；不含自動調倉、
> household capital authority 或 Google Sheet 寫回。正式規格與驗收見
> [`../plans/2026-07-28-001-feat-daily-beta-technical-monitor-plan.md`](../plans/2026-07-28-001-feat-daily-beta-technical-monitor-plan.md)。
> Phase II-A household capital authority 已於同日完成；私人數值只存在 Google Sheet
> `Capital Authority`，tracked 文件只保存 authority routing、fail-closed 與人工資本邊界。實作與驗收見
> [`../plans/2026-07-28-002-feat-household-capital-authority-plan.md`](../plans/2026-07-28-002-feat-household-capital-authority-plan.md)。
>
> 本主題已與 Paywall ROI／合法手動入口、Token-efficient Daily Runner 一併收斂到
> [`2026-07-26-next-phase-operating-model-requirements.md`](2026-07-26-next-phase-operating-model-requirements.md)；
> 本檔保留 Portfolio Sleeve 的深度需求。

> **2026-07-30 current-state override：** 下文的 household／planned outflows／5% operating reserve／3% alpha
> reserve／雙 cash range 只保留為歷史推導，不再是 current contract。現行唯一共同可投資現金池為
> `Portfolio CASH − cash floor`，供 Alpha 與 Beta 共用；兩者分配由各自 sizing／campaign policy 另行決定。
> `Capital Authority` 只保留 cash floor 與貸款必要條款，貸款不併入自有現金並另計利息。Current authority
> 以 `AGENTS.md`、`skills/daily-brief/SKILL.md` 與程式為準。

## 最危險的三個盲點（先看這個）

1. 🔴 **把「指數長期向上」直接推成「daily 3x 長抱必然向上」** — daily reset 的終值依賴報酬路徑；
   underlying 長期正報酬與 3x ETF 長期正報酬可以同時一正一負。若此假設不拆開，永久持有信念會掩蓋產品風險。
2. 🔴 **只看貸款買進後的名目資產終值，沒看退休時的淨終值** — 未動用額度不是資產；提款後 cash 與 debt
   同時增加。真正比較基準是退休時資產終值扣除本金、累計利息與其機會成本，而不是「30 年後大盤大概更高」。
3. 🔴 **no-sell policy 讓所有風控不可逆地前移到進場** — 不賣可以是紀律，但 target upper band 將不能靠出售修復；
   新增部位若沒有 entry cap、contribution routing 與產品結構例外，錯誤 concentration 只會永久累積。

## 2026-07-28 延伸：Beta 進場時機不是猜底，而是先取得部署許可

> 本節的 TechnicalObservation／Sheet-conservative monitor 已授權並完成 Phase I；候選 range 仍不構成調倉、
> live choice／fill 或 broker order。
> 數字來自 2026-07-28 09:08（Asia/Taipei）Decision Lab 凍結的 Google Sheet snapshot；
> 該 snapshot `status=unconfirmed`，只適合需求討論，不是交易指令。

### 2026-07-28 第二輪使用者方向：Beta 是 accumulation-only 地基

使用者目前的核心偏好是：

1. 買進大盤 beta 後原則上持有至退休，不因回檔、熊市或一般 regime 變化賣出。
2. 這個 no-sell 信念目前也涵蓋 TQQQ／00631L 等 daily leveraged ETF；但不代表一次 all-in 或無上限加碼。
3. Beta 地基之外的 surplus capital 才用於 StockBot 的 alpha；Phase II-A 以私人 capital authority 產
   household cash-supported candidate，loan facility 另列 contingent capacity，不混成同一個 surplus。
4. 自有可投資現金直接認 Google Sheet `Portfolio` cash 欄位，不另建立重複的表外 cash；家庭 reserve、
   planned outflows 與未動用貸款額度則由私人 `Capital Authority` tab 保存。

### 2026-07-28 最終方向校正：退休淨終值導向，不另建貸款引擎

這一輪把貸款政策收斂到足以執行、但不過度工程化的版本：

1. **目標函數**：使用者目前約 30 歲、退休目標約 60 歲；策略以約 30 年後的
   `retirement_net_terminal_wealth` 最大化為方向，不以壓低短期波動或回撤作為第一目標。
2. **可投入範圍**：只有使用者明確指定、確信可一路持有到到期的貸款額度才進人工討論；系統不把整個
   undrawn facility 自動視為可買金額。
3. **已確認契約現金流**：利息按月支付、期間內不用攤還本金、到期一次還本；契約允許投資用途，資金用途
   不再是系統 blocker。
4. **不另開 Phase II-B engine**：不建立 household cash-flow optimizer、debt-service stress engine 或新的 pq 流程。
   每次實際提款仍由使用者明確指定 draw／instrument／tranche，LLM 按當時資料做一次性比較即可。
5. **資產選擇邊界**：貸款資金可討論 broad beta、tilt、daily leverage 或 alpha，不做類別禁令；但 broad
   unlevered beta 是主要候選，daily 3x 因 daily reset 與 path dependency 維持衛星定位，不因期限長而升為主力。
6. **最小會計邊界**：未提款仍只列 contingent credit；提款後 cash 與 drawn debt 必須同時入帳。唯一持續要守的
   operational condition 是每月利息能由既定現金流支付、不必被迫賣出；本金則在到期終值比較中完整扣除。

Daily Brief 的 Beta 首屏因此採三行 TL;DR：先說約 30 年後 `retirement_net_terminal_wealth` 目標，
再列今日可人工評估標的，最後列已觸發的動態風控。technical signal 只調整新增 timing／pace，不能把
短期燈號誤寫成退休目標本身、自動賣出指令或 live permission。

因此，早期 brainstorm 中的一般化 lender-purpose、12–24 個月 debt-service reserve、callable／freeze 與多情境
壓力引擎，均不再是這位使用者目前的 implementation prerequisite。若未來契約或支付能力改變，再重新開題；
現在不為尚未發生的例外建系統。

這個方向將 v0 從傳統「雙向 rebalance」改成 **contribution-routing policy**：低於 band 的 sleeve 優先取得
新資金，超過上緣的 sleeve 停止新增，但不因越界自動賣出。也就是說，beta position 是近似 absorbing state；
風控主要發生在 entry 前，日後靠新投入資金稀釋 concentration，而不是靠頻繁交易修正。

但需把兩個命題分開：

- **使用者偏好**：「我願意承受大幅回撤，長期不賣。」這是可被 policy 接受的行為選擇。
- **產品事實假設**：「只要大盤長期向上，daily 3x 長期終值也必然向上。」這不成立為保證，不能寫成系統事實。

Daily leveraged ETF 的長期終值具有 path dependency。忽略費用，若指數第一天 +10%、第二天 -8%，指數仍為
`1.10 × 0.92 = 1.012`，累計 +1.2%；daily 3x 則為 `1.30 × 0.76 = 0.988`，累計 -1.2%。
因此正報酬指數可以和負報酬 3x ETF 同時成立；波動、持有期、融資成本與費用會進一步改變結果。

SEC 的 investor bulletin 明確指出 daily reset 產品在週、月、年期間可能顯著偏離其 daily multiple，甚至在
underlying index 上漲時承受重大虧損；ProShares 也只承諾 TQQQ 的 daily 3x target，並說明一天以上報酬可顯著
高於或低於 Daily Target。這不是要求使用者賣出，而是要求 `beta_leverage` 的 entry cap 與壓力測試不能被
「退休前不賣」取代。

來源：

- [SEC／Investor.gov：Leveraged and Inverse ETFs](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec)
- [ProShares TQQQ 官方產品頁](https://www.proshares.com/our-etfs/leveraged-and-inverse/tqqq)

### 修正資本分母：持倉、可投入資本與授信不能混成一個數字

上一輪的 98.62% 是 **Sheet account effective exposure / Sheet NAV**，不是 household-level 滿倉判定。
外部現金與其他可投資資產若存在，會擴大真實 capital denominator；因此「目前可供 beta ladder 使用的資金
接近零」只能描述 Sheet 內部，不能外推到整體資產。

候選 household capital authority 至少拆成：

| 欄位 | 是否進 investable capital | 用途 |
|---|---|---|
| `sheet_market_value` | 是 | 現有 live securities inventory |
| `external_investable_cash` | 是，需 as-of／currency | 尚未進 Sheet、確定可投入的現金 |
| `other_liquid_investments` | 是，扣除重複計算 | 其他券商／基金／短債等 |
| `operating_floor` | 否，從可部署額扣除 | 緊急預備金與日常流動性 |
| `planned_outflows_reserve` | 否，從可部署額扣除 | 稅、房屋、教育或已知大額支出 |
| `drawn_investment_debt` | 負債；不得只把 proceeds 算資產 | 計 household net capital、每月利息與到期本金 |
| `undrawn_credit_limit` | **否** | 只記 `contingent_liquidity`，不是現金、NAV 或 alpha reserve |

概念公式先定為：

```text
household_net_investable_capital
  = sheet_market_value
  + external_investable_cash
  + other_liquid_investments
  - drawn_investment_debt

verified_deployable_cash
  = portfolio_cash
  - operating_floor
  - planned_outflows_reserve
  - committed_beta_budget
  - alpha_reserve

retirement_net_terminal_wealth
  = retirement_portfolio_value
  - outstanding_principal_at_maturity
  - accumulated_interest_and_opportunity_cost
```

`undrawn_credit_limit` 不出現在上述兩個公式。若日後真的提款，必須同時增加 cash 與 debt，並重算：

- `gross_effective_exposure / household_net_investable_capital`
- 當期 borrowing cost 與每月利息現金流
- 到期本金與退休時 `retirement_net_terminal_wealth`
- 若 instrument 是 daily leveraged ETF，另看產品自身的 path-dependent terminal distribution

使用者已確認此 facility 利息按月支付、期間不攤還本金、到期一次還本，且契約允許投資用途。故目前不另建
一般化 debt-service reserve／lender-purpose／callable stress engine；只有每月利息無法在不賣資產下支付，或契約
本身日後變更時，才把貸款路徑降級並重新討論。

### 目前 Sheet 持倉的第一個診斷：帳戶內不是缺 beta，而是 beta 不夠乾淨

目前 NAV 約 USD 410,651；依可直接辨識的持倉先做下限估算：

| 曝險 | NAV 比重 | 解讀 |
|---|---:|---|
| VWRA | 26.30% | 最接近全球、非槓桿的 `beta_core` 候選 |
| QQQ | 14.45% | Nasdaq-100 mega-cap／growth tilt；不是全市場 core |
| 0050＋006208 | 12.08% | 台灣大型股 beta，但兩者高度重疊；不能以兩檔名義當成兩份分散 |
| TQQQ＋00631L | 7.04% nominal；約 16.39% daily effective | 應隔離為 `beta_leverage`，不得計入穩固 core |
| 現金 | 10.73% | 看似有 dry powder，但若同時保留安全底線與 alpha reserve，可動用額度很薄 |
| 非現金 equity＋槓桿額外曝險 | **至少 98.62% effective** | 尚未把 SOXX 約 2.0 beta、個股 beta 與 ETF 內部重疊納入，真實風險可能更高 |

台積電集中度尤其容易被表面 ETF 數量掩蓋：直接 2330 已佔 17.61%；再用 0050 的 58.69%、
006208 的 57.39%，以及 00631L 的 daily 2x 台灣 50 目標做 look-through，台積電等效曝險下限約
**30.24% NAV**。這還沒計 VWRA、SOXX、00981A 內的間接持倉，因此只能叫 lower bound。

來源：

- [元大 0050 持股比重（2026-07-23）](https://www.yuantaetfs.com/product/detail/0050/ratio)
- [富邦 006208 基金資訊（2026-06-30）](https://www.fubon.com/asset-management/fund/info/assets?Fd=40)
- [元大 00631L 基本資訊](https://www.yuantaetfs.com/product/detail/00631L/Basic_information)
- [ProShares TQQQ Summary Prospectus](https://prod.proshares.com/globalassets/proshares/prospectuses/tqqq_summary_prospectus.pdf)

**因此「讓大盤更穩固」的操作定義應改成：在 household denominator 下，以新資金持續擴大 core，同時限制
新增 concentration 與 stacked leverage；不是只把更多錢投入名稱看似是指數的商品。**

### Sleeve 語意需要從四類擴成五類

原本的 `beta_core / beta_tactical / alpha_single_name / cash` 仍把非槓桿 tilt 與 daily leverage 混在一起。
候選分類改為：

1. `beta_core`：非槓桿、廣泛分散、預計跨完整週期持有；目前最清楚的候選是 VWRA。
2. `beta_tilt`：有意識的區域／風格／產業偏離；QQQ、0050、006208、SOXX、00981A 先放此層，
   是否把其中一檔升為 core 需使用者明確核准。
3. `beta_leverage`：daily reset 的 TQQQ、00631L；獨立 nominal 與 effective exposure cap，永不充當 core。
4. `alpha_single_name`：必須有 claim、disproof、expiry 與 supported range 的個股；持有本身不構成 alpha。
5. `cash`：再分 `operating_floor` 與 `alpha_reserve`；beta ladder 不得吃掉 alpha reserve。

每個 beta sleeve 另帶 `exit_policy=accumulation_only`。`beta_leverage` 可尊重使用者 no-sell 偏好，但必須另帶
`new_money_cap`、`stress_loss_budget` 與 `product_structure_exception`；若基金終止、改變 investment objective、
無法正常追蹤或出現其他產品結構事件，仍需人工 review，不能把「永不賣」擴張成「永不重新判斷產品是否存在」。

### Workflow／Engine ownership：主責是 Engine D，不走一般研究 pq

這不是新的第五個 engine，也不應塞進 Engine A／B。最小責任分配如下：

| 資料／行為 | Authority／owner | 說明 |
|---|---|---|
| 固定 beta instrument registry、五類 sleeve、bands、entry cap、no-sell／structural exception | **Engine D versioned policy** | 資本規則與使用者偏好，不是研究 claim |
| live holdings | Google Sheet | 維持現有 live inventory SSOT；目前唯讀，候選新增「使用者明確回報 fill 後」的窄寫回 adapter |
| external cash／assets／drawn debt／undrawn limits | Google Sheet 新 tab 或 ignored private capital snapshot（二擇一） | 人工 current-state authority；Engine D freeze 當次使用 slice |
| price、FX、252-day high、drawdown、volatility、fund look-through observation | **Engine C** | 帶時戳 market／portfolio observation；不決定是否投入 |
| contribution permission、使用者 choice、手動 fill、outcome | **Engine D private Decision Store** | 可稽核資本決定；不寫回 broker／Sheet |
| company claims／supply-chain thesis | Engine A | 固定 beta ETF 本身不需要 company onboarding |
| 外部 signal discovery／研究排程 | Engine B | 日常 beta monitor 不使用；只有罕見產品結構事件需要追原文時才介入 |

Daily／weekly workflow 的 beta 分支應是 deterministic portfolio monitor：

```text
Google Sheet holdings + capital authority
              +
Engine C market／FX／drawdown／look-through
              +
Engine D versioned sleeve policy
              ↓
Engine D Portfolio Sleeve Monitor
              ↓
HOLD / PAUSE CONTRIBUTION / CONTRIBUTE REVIEW / STRUCTURAL REVIEW
```

#### pq contract

- **不進 pq1：** 固定 instrument universe 不需要 source-trace、company onboarding、Research Action 或每日 LLM 研究。
- **不進任何 pq：** `HOLD`、`PAUSE CONTRIBUTION`、正常 band／drawdown telemetry；Daily 只顯示 aggregate。
- **一次性 pq2：** 初次核准 instrument mapping、bands、capital policy、stacked-leverage cap 與 structural exceptions。
- **例外 pq2：** `CONTRIBUTE REVIEW` 涉及 live 資本，或 `STRUCTURAL REVIEW` 需要使用者決定；兩者進現有統一
  待辦編號空間，但不先繞 pq1。使用者 `go` 只記 choice／permission，仍由使用者手動下單並回報 fill。
- **罕見 pq1 → pq2：** 只有基金更換標的指數、objective、issuer／closure 等事件本身尚未查清時，才建立 bounded
  product-structure research；研究完成後需要採取動作才回 pq2。
- **使用者問答不進 pq：** 使用者直接問「這次像不像黑天鵝／regime shift」「目前有沒有更好的配置方法」時，
  LLM 可按需抓取最新客觀資料後直接回答；除非使用者進一步要求修改 policy 或投入 live 資本，否則不建立
  pq1／pq2、Decision receipt 或持久化研究工作。

所以「標的固定」確實消除了日常研究 pq；但不能消除 live 資本的人工核准。這是 exception-only pq2，
不是 lead／thesis queue。

### 2026-07-28 問答型 LLM 顧問：列入 Phase II 邊界，但採 zero-code-first

使用者希望保留一個輕量、rough、可持續對話的判讀層：當使用者主動詢問目前下跌是否可能是系統性壓力、
是否有更合適的投資策略、或某個 deterministic 訊號應如何解讀時，LLM 可讀取當下 beta monitor／Sheet aggregate，
並按問題需要補抓市場、信用、波動、政策或事件等最新客觀資料後直接回答。

這個能力不建立第五個 engine，也不複製 Engine A 的 graph／claim／Research Action 複雜度。候選 contract 為：

1. **只由明確提問觸發**：不加入每日固定 LLM 研究，不因一般 `HOLD`／technical telemetry 自動產生評論。
2. **資料可多抓、狀態不必多存**：回答 current／latest 問題時必須使用帶時間戳的最新來源；預設只在對話中
   組合證據，不建立圖節點、thesis lifecycle 或新的 current-state authority。
3. **回答而非拍板**：輸出可包含 rough scenario、支持／反方解釋、組合影響與 policy-compatible alternatives；
   「黑天鵝」不作二元事實分類，改用 `normal pullback / regime shift suspected / systemic stress suspected /
   event shock / high ambiguity` 等帶不確定性的語言。
4. **不得改 hard cap**：LLM 建議不能提高 Sheet／household deployable cash、campaign budget、leverage、factor、
   single-company ceiling，也不能推定 choice／fill；若使用者要採取 live 動作，仍回既有 Engine D 人工邊界。
5. **只有重複摩擦才寫 helper**：若後續反覆需要同一組 portfolio／technical／macro context，Phase II 才考慮
   一支唯讀 compact context composer；在此之前直接問答即可，不為了形式完整先建 schema、queue 或新 pipeline。

因此這項目在 roadmap 上與 household authority／look-through 一起列為 Phase II clarification，但使用者現在已可
直接提問，不需等 Phase II 工程完成。只有當它變成穩定、重複、可驗收的資料組裝需求，才另立 implementation unit。

### 2026-07-28 Phase II-A 收斂：Capital Authority 與 loan-funded discussion contract

本輪已將 household capital 的實際 current-state 數值寫入 Google Sheet 私人 `Capital Authority` tab；tracked repo
不保存個人金額。使用者確認的產品 contract 為：

1. **自有現金不重複計算**：可投資 cash 只讀 `Portfolio.cash_twd／cash_usd`；`Capital Authority` 只保存
   routing reference、家庭 operating floor 與 planned-outflow reserve。
2. **未動用額度不是資產**：房屋擔保 credit facility 維持 `contingent_liquidity`；未提款時不增加 NAV、
   household net investable capital 或 Daily deployable cash。
3. **不做標的類別禁令**：依使用者偏好，loan proceeds 可討論配置到 broad beta、tilt、daily leverage 或 alpha；
   系統不預先禁止某一類商品。
4. **但永遠是人工資本路徑**：Daily 不產自動 loan-funded supported range。每次提款、標的、總額與 tranche 必須
   由使用者明確討論／核准；「足夠信心」只是對話判斷，不能被 parser 當成 machine permission。
5. **提款後雙邊入帳**：一旦實際提款，同時增加 cash 與 drawn debt，重算 household net capital、stacked leverage、
   每月利息與退休淨終值。已確認期間只付月息、不攤還本金、到期一次還本；契約允許投資用途，不再為此另建 blocker。
6. **不靜默放寬 Phase I**：私人 operating floor 只用於新的 household candidate；Phase I 既有 5% NAV operating
   reserve＋3% NAV alpha reserve 所產 `sheet_conservative` range 同時保留。Phase II-A 先並列 paper observation；
   household candidate 仍沿用既有 alpha reserve，直到 live promotion 另行核准，不能因私人 floor 較低就直接
   覆蓋舊 hard maximum。

Phase II-A 預期輸出必須分四欄，禁止合成一個誤導性的「可買金額」：

```text
sheet_conservative_range          # Phase I 既有 5% operating＋3% alpha reserve
household_cash_supported_range    # Portfolio cash 扣 private floor、planned outflows與既有alpha reserve
contingent_credit_available       # 只顯示可討論額度與條款完整度，不算資本
loan_funded_supported_range       # 預設 manual_review_required；無 exact choice 時不給自動數字
```

brainstorm 至此可視為 settled；Phase II-A 已完成唯讀 `Capital Authority` adapter、point-in-time capital view、
上述四欄輸出與 Daily 整合。貸款方向不另開 Phase II-B engine；ETF 完整 look-through、live promotion、成交後
Sheet writer 與 server 若日後真的有重複摩擦，再各自另立切片。

### 3x 定位定案方向：可投資的 `beta_leverage` 衛星，不是主力

這輪同意使用者的方向：TQQQ／00631L 不列為禁止資產，也不要求因一般回檔出售；但它們不計入
`beta_core` target，不用來證明地基已穩固。候選 v0 約束為：

1. **combined nominal cap**：所有 daily leveraged beta 市值合計，先以 household net investable capital 的
   5–8% 作偏積極型討論起點。
2. **combined effective cap**：依 2x／3x 換算後合計 15–20% 作偏積極型討論起點；風控看此欄，不只看市值。
3. **funding rule**：Daily deterministic range 只使用 `verified_deployable_cash`。使用者允許 loan proceeds 投入
   daily leveraged ETF，但每次都必須另走 exact draw／instrument／tranche 的人工 review；比較退休淨終值、
   借款成本與既有 leverage cap，不能視為一般 beta contribution 或自動 permission。
4. **accumulation-only 行為**：低於 cap 可依 ladder 小額貢獻；高於 cap 只 `PAUSE CONTRIBUTION`，不自動賣出。
5. **satellite budget**：3x 與 alpha 各有獨立 reserve，不能因大盤急跌吃掉 alpha budget，也不能由 alpha conviction
   反向放寬 leverage cap。

上述 5–8%／15–20% 是依使用者「大盤承受度高、科技曝險可較高」所上修的 forward-observation candidate，
不是已核准數字。依目前 Sheet denominator，TQQQ＋00631L 約 7.04% nominal／16.39% effective，落在此候選帶內；
但 household denominator 未完成，目前仍不能判定真實使用率，也不產生賣出建議。

### 2026-07-28 使用者需求校正：Technical signal 決定 timing，Engine D 決定 safe size

使用者真正想要的 recurring workflow 是：對固定追蹤的權值股／廣泛、產業與槓桿 ETF，每日收盤後觀察
RSI、MACD、MA、drawdown 等水位；訊號到達候選區時，系統回答「現在可考慮加多少、在 household／sleeve／
stacked-leverage 限制下仍算安全」。使用者自行下單；成交後明確要求系統同步 Google Sheet。

這與前述 Engine D sleeve monitor 一致，但要鎖死一條邊界：

> **Technical signal 只決定 `when / pace`，不能提高 `safe ceiling`。**

即使 RSI 極低、MACD 翻正或跌破長期均線，若 household capital 未確認、cash reserve 不足、sleeve／effective
leverage 已滿或同一 drawdown tranche 已用完，輸出仍是 `PAUSE CONTRIBUTION`。反過來，容量很大但沒有訊號時
只輸出 `HOLD`，不因有錢就自動投入。

#### Engine C：產生 point-in-time `TechnicalObservation`

固定 universe 不需要 LLM。Engine C 每日 deterministic 計算並保存／freeze 至少：

```text
as_of / fetched_at / source / series_digest
close_raw / close_adjusted
drawdown_from_252d_high
RSI(14)
MACD(12,26,9): line / signal / histogram / histogram_slope
SMA(20) / SMA(50) / SMA(200)
distance_to_each_MA
realized_vol_20d / realized_vol_60d
data_status / blockers
```

目前 `engine_c.market_data.get_tradeability_snapshot()` 只抓約 2 個月、至少 20 sessions，且使用
`auto_adjust=False` 的 raw close，足夠 execution price／ADV，不足以可靠計算 SMA200、252-day high 與跨拆股／配息
technical signal。實作時需新增獨立的 technical history path（至少 252 個完整 sessions）；execution raw price 與
signal adjusted series 不可混成一欄。

#### Leveraged ETF 的 signal 必須看 underlying，不看產品自身水位

instrument registry 需另存 `signal_benchmark`：

| 可交易商品 | signal benchmark 候選 | 原因 |
|---|---|---|
| TQQQ | QQQ／Nasdaq-100 | TQQQ 自身價格含 daily 3x compounding／volatility path |
| 00631L | 0050／Taiwan 50 Index | 00631L 自身是 daily 2x 結果，不代表 underlying 的原始水位 |
| QQQ | QQQ | 非槓桿產品可直接觀察 |
| 0050／006208 | Taiwan 50 benchmark | 兩檔共用同一區域 beta 水位，避免把重疊商品算成兩個獨立訊號 |
| SOXX／其他 sector ETF | 自身 unlevered benchmark／ETF | sector signal 只能觸發 `beta_tilt` budget，不能動用 broad core budget |

交易價格仍取實際 execution ticker；signal benchmark 只決定 timing。若 benchmark observation missing／stale，
該商品 contribution permission fail closed。

#### RSI／MACD／MA 不是三張獨立選票

三者都由同一價格序列衍生，不能用「三個 indicator 同意」假裝三份獨立證據。候選角色分工：

- **跌深程度**：252-day drawdown＋RSI(14)。RSI <30 可標 oversold，但不能單獨觸發滿 tranche；強下跌中 RSI
  可長時間維持低檔。
- **動能轉折**：MACD histogram slope／signal crossover。MACD 適合確認趨勢動能，不把它誤當 oversold 指標。
- **長期 regime**：price relative to SMA200、SMA50 slope。它只縮放 pace；不因跌破 MA200 就強迫賣 accumulation-only core。

Fidelity 將 MACD 定義為趨勢／動能 oscillator，Schwab 也提醒 RSI 的 oversold trap 與 indicator whipsaw；因此 v0
不採「indicator 越多、信心線性相加」，而採 role-separated state machine。

來源：

- [Fidelity：MACD](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/macd)
- [Charles Schwab：Choosing Technical Indicators](https://www.schwab.com/learn/story/choosing-technical-indicators-to-analyze-stocks)
- [Charles Schwab：Technical Indicators—3 Trading Traps](https://www.schwab.com/learn/story/technical-indicators-3-trading-traps-to-avoid)

#### Engine D：從 signal state 算 supported contribution range

候選公式先鎖責任，不先鎖 RSI／MA 的最佳門檻：

```text
base_tranche_notional
  = frozen_beta_budget × signal_pace

safe_order_notional
  = min(
      base_tranche_notional,
      verified_deployable_cash,
      remaining_effective_sleeve_capacity / leverage_multiple,
      remaining_overlap_capacity / look_through_multiplier,
      stress_loss_budget / stressed_loss_rate
    )
```

`signal_pace` 只能取 versioned policy 的離散值，例如 `0 / 0.25 / 0.5 / 1.0`；indicator 不得產生 policy 外的
連續槓桿。對 TQQQ，若 household 只剩 3% Nasdaq effective capacity，則市場訂單上限約為 household capital 的
1%，不是 3%；00631L 同理除以 2。

Engine D public output 至少包含：

```text
instrument / signal_benchmark / signal_state / as_of
current_nominal_weight / current_effective_weight
safe_order_range_base / currency
binding_constraint
remaining_budget_after_max
action = HOLD | PAUSE CONTRIBUTION | CONTRIBUTE REVIEW
```

indicator threshold、signal pace 與實際 outcome 必須做 forward paper observation；不得先試多組 RSI／MACD／MA
參數，再只保留歷史上表現最好者。

### 運行方式：v1 已包進現有 Daily，不先架 always-on server

日線 RSI／MACD／MA 只需要每日完整收盤價，不需要即時行情或 LLM。v1 已把它加入現有台北 06:30 Daily 的
deterministic snapshot，順序為：

```text
price-history refresh／missing-bar backfill
→ Engine C TechnicalObservation
→ Engine D sleeve／safe-size monitor
→ decision_lab today／todo sync／Daily Brief
```

06:30 可取得最新美股收盤，台股／日股／歐洲則使用上一個已完整收盤 session；對日線 accumulation workflow
可接受。若日後要求「台股今天收盤後立刻判斷」，再增設約 14:30 的區域 market-close task，不必因此搬整套
A／B／C／D 上 server。

本機 automation rule 仍只允許固定入口，不允許 unattended 任意 Python／shell；Phase I 已以
`scripts/daily_beta_snapshot.py` 作受控 fixed entry 並加入窄 allowlist，不靠 prompt 臨時拼命令。可靠性 contract：

1. 每個 benchmark 保存 `last_complete_session`、`fetched_at`、provider 與 digest；缺 bar 時下次啟動先補歷史價格。
2. provider timeout／空資料以 bounded retry 處理；仍失敗就標 `stale/missing` 並 fail closed，不產
   `CONTRIBUTE REVIEW`。
3. Daily 檢查前次成功日期，Weekly health report 顯示連續漏跑／provider failure；補到價格資料不等於假裝當天
   曾即時發出 decision／notification。
4. 每日保存 scalar TechnicalObservation；不能只保存可重算的最新 history，否則無法稽核當時看見的訊號。

只有出現以下任一需求，才把最小 market-data worker 升級到 always-on server：本機經常關機且不能接受隔日
補跑、要求每日必達通知／SLA、需要 intraday 訊號、需跨市場各自收盤即時觸發，或要雙 provider redundancy。
即使升級，也只搬價格擷取／排程與 heartbeat；live choice、Google Sheet inventory、Engine D 決策與人工下單仍
維持既有 authority 邊界。

### 首波固定 universe：沿用目前 ETF／權值股，先去重 benchmark

首波不另外選新標的；用 2026-07-28 frozen Sheet 中已持有的 ETF／權值股。Phase I registry 已固定為
14 個商品／11 條 series；目前 policy mode 是 `paper_observation`，若升格成 live mandate 仍需一次性 pq2 核准。
其中單一權值股不冒充 `beta_core`，必須另過 single-company／look-through cap。

| 目前持有商品 | 候選 sleeve | technical series／signal benchmark | 備註 |
|---|---|---|---|
| LON:VWRA | beta_core | VWRA adjusted series | 全球 unlevered core |
| QQQ／TQQQ | beta_tilt／beta_leverage | 共用 QQQ／Nasdaq-100 | TQQQ 只取實際 execution price，不用自身路徑判斷水位 |
| SOXX | beta_tilt | SOXX | 半導體 sector budget |
| DRAM | beta_tilt_active | DRAM | Roundhill 主動式記憶體 thematic ETF；非 daily leveraged ETF，另留 manager／methodology risk |
| 0050／006208／00631L | beta_tilt／beta_leverage | 共用 0050／Taiwan 50 | 三檔只算一個 market signal，曝險仍逐檔 look-through 加總 |
| 00981A | beta_tilt_active | 00981A adjusted series | 主動統一台股增長；績效比較指標不等於被動追蹤，另保留 manager／mandate structural risk |
| 2330 | large_cap_tilt／alpha_single_name | 2330 | 不計入 beta_core；與台灣 50 重疊加總 |
| GOOGL／MU／NVDA／TSLA | large_cap_tilt／alpha_single_name | 各自 adjusted series | technical 只給 timing，仍受單一公司 cap |

這樣 14 個持有商品約只需 11 條 unique technical series。FRA:2DG 與 TYO:7803 暫留既有 alpha／single-name
流程，不納入本輪「大盤／權值股」beta monitor；若之後要加，也不需要改 TechnicalObservation schema。

產品分類核對來源：[Roundhill DRAM 官方產品頁](https://www.roundhillinvestments.com/etf/dram/)；
[臺灣證券交易所 00981A ETF 資訊](https://wwwc.twse.com.tw/zh/ETFortune-institute/etfInfo/00981A)。

#### 偏積極科技型的 candidate guardrails

以下是互相重疊的 guardrails，不是相加後必須等於 100% 的資產配置。Phase I 先以 Sheet NAV 產明確標為
`sheet_conservative` 的 paper range；要升格為 household-level permission，分母仍必須換成已確認的 household
net investable capital：

- daily leveraged beta：combined nominal 5–8%、effective 15–20%；兩道上限都要通過。
- technology／semiconductor look-through：60% 顯示 warning、70% 暫停新增相關曝險。
- single-company look-through：30% 顯示 warning、35% 暫停新增；直接股與 ETF 內含持股合併計算。
- 高風險承受度可提高 equity／tech budget，不能降低 operating reserve、債務服務預備金，也不能把 loan-funded
  3x 從人工 review 變成 Daily 自動 deployable cash。

目前 Sheet 的 TQQQ＋00631L 約 7.04% nominal／16.39% effective，位於候選 leverage band；TSMC 直接加已知
台灣 50 look-through 下限約 30.24%，已進 single-company warning 區但未達 hard pause。兩者都只是 Sheet-level
觀察；表外資產、現金與 drawn debt 納入後才可形成 household-level permission。

### 成交後 Google Sheet 同步：符合使用者目標，但目前尚未實作

目前 `fetchers/gsheets.py` 使用 `spreadsheets.readonly` scope，Decision Lab 也明定不寫 Sheet。因此「使用者成交後
請系統更新 Google Sheet」是這輪新增的產品需求，不是現行能力。候選的窄寫回 contract：

1. `CONTRIBUTE REVIEW` 進 pq2；使用者 `go` 後只記 Engine D choice，不下單。
2. 使用者自行成交，再明確提供／確認 `position_id`、side、shares、price、currency、executed_at、broker／account、
   execution_ref，並要求同步 Sheet。
3. Engine D 先 checkpoint `pending_inventory_sync`；runtime 的窄 Google Sheet adapter 只可更新該 exact position，
   不可改公式、其他列、sleeve policy 或現金列。
4. 寫入後立即 read-back，核對 shares／cost／sheet digest；成功才 `record-fill` 並完成原 pq2。
5. 若 Sheet 成功但 Decision Store 失敗，或反之，保留 active reconciliation exception，不宣稱完成。

現有 Sheet 同一 ticker 可能有多個 broker／重複列（例如 VWRA、2330、00981A），所以未來寫回不能用 ticker 當唯一
key，也不能依可移動的 row number；需先加穩定 `position_id`。若使用者在沒有既有 `CONTRIBUTE REVIEW` 的情況下
自行交易，仍可走相同 `manual_execution_sync` receipt，但不進 pq1。

這條路徑不改兩個邊界：系統不替使用者下 broker order；Google Sheet 仍是 current live inventory authority，
Engine D 只保存 choice／fill／sync receipt 與當時 sheet digest。

0050 與 006208、QQQ 與 TQQQ、2330 與台灣 50 ETF 等配對必須做 look-through overlap；分類標籤不能取代
曝險加總。

### Candidate v0：Beta deployment permission

Beta 加碼必須依序通過以下 gate；任何一項失敗就輸出 `PAUSE CONTRIBUTION / REVIEW`，而不是猜下一個低點：

1. **Authority gate**：holdings、NAV、FX、price 與 sleeve metadata 已確認且未過期。
2. **Capital-authority gate**：Sheet 外 investable cash、其他資產、drawn debt 與 undrawn limits 已分開；缺資料時
   只能給 account-level observation，不能宣稱 household-level 滿倉或有多少 surplus。
3. **Core-gap gate**：`beta_core` 低於核准 target band 下緣；若已在 band 內，價格下跌本身不構成加碼理由。
4. **Stacked-leverage gate**：ETF effective leverage 加上 balance-sheet debt 後未越界；越界時新增現金只能改善
   unlevered core 品質，不能再加槓桿。
5. **Liquidity gate**：`verified_deployable_cash` 必須為正；undrawn credit 不算 deployable cash。
6. **Overlap gate**：look-through 後，單一公司、區域與 factor 不因本次加碼突破 cap。
7. **Cooldown gate**：同一 drawdown tier 已執行後，至少等待 10 個交易日或下一個週收盤，避免連日跌勢中重複觸發。

這裡的優先順序是 **band 偏離 > drawdown > regime**：band 決定是否需要買，drawdown 只決定部署速度，
regime 只縮放 tranche，不扮演宏觀預言。

### Candidate v0：Drawdown ladder（待 forward paper observation）

Drawdown 一律相對於核准的 `beta_core benchmark` 252-day closing high 計算，不看個人損益、不混用盤中低點，
也不能用 SOXX／QQQ 的跌幅替 VWRA core 觸發。候選規則：

| Core benchmark drawdown | 可部署的 beta budget | 行動 |
|---|---:|---|
| 0% 至 -10% | 0% 額外 drawdown tranche | 只做定期投入或 band rebalance |
| -10% 至 -15% | 25% | 第一 tranche，只買 `beta_core` |
| -15% 至 -25% | 再 25% | 第二 tranche；重新驗 leverage／cash／overlap |
| -25% 至 -35% | 再 25% | 第三 tranche；信用／流動性壓力時減半 |
| 低於 -35% | 最後 25% | 保留人工確認，不自動 all-in |

`beta budget` 是本輪事前凍結的 `min(core_gap, verified_deployable_cash)`，不是每跌一級重新拿全部現金或
未動用授信計算。若市場反彈但某 sleeve 穿越上緣，accumulation-only policy 下只停止該 sleeve 新增、把後續
contribution 導向 underweight sleeve；不為了機械回到中點賣出既有 beta。

### 對「現在正下跌」的 provisional response（已按 household denominator 修正）

目前較合理的 action 不是立刻增加總 beta，而是：

1. **既有 beta 不因下跌觸發賣出**，符合使用者 accumulation-only 偏好；但新增 TQQQ／00631L 仍要等
   既有 leverage cap 與 exact tranche 人工 review，不能由「退休時大盤較高」單一信念自動放行；不再等待一套
   新的 debt stress engine。
2. **把 beta core 與 tilt 重新分類後再判斷是否有 core gap**。若只有 VWRA 算嚴格 core，問題是 core 品質不足；
   若把 QQQ／台灣 50 全算 core，問題則是隱含科技／台積電集中度過高。兩種定義會導出完全不同的加碼結論，
   因此不能先交易、後補定義。
3. **補完整 household capital authority 後再定義 surplus**。Sheet 內現金約 10.73%，但外部現金／資產尚未計；
   因此現在不能判定 beta ladder 實際可用資金接近零。未動用授信額度先保持在 `contingent_liquidity`，不納入 surplus。
4. **若要改善地基，資金方向優先是非槓桿、較廣泛的 core，而不是新增重疊 ETF**；可用未來新資金或日後
   tactical 越界的再平衡改善，不因單日急跌被迫一次完成。

這個 provisional response 不是「永遠不買」，而是把買進條件從「跌了／有額度」改成「household capital 已確認、
core 低於 band、verified cash 可用、stacked leverage 未超標、重疊未惡化，而且 drawdown tier 尚未使用」。

### Phase II-A 已收斂；仍待 live promotion 核准的 policy 數字

自有 cash authority、私人 operating floor、planned outflows 與 credit-facility current state 已存在 Google Sheet
`Capital Authority`；exact 個人數值不進 tracked repo。貸款可討論所有標的，但只走人工 exact-choice／分批路徑。
使用者已確認利息每月支付、期間不還本、到期一次還本，且契約允許投資用途。這些條件不再是 roadmap blocker；
但 Daily 仍不自動產生 loan-funded range，私人 Sheet authority 尚未同步前可繼續誠實顯示舊的條款完整度警告。

下列數字留待 30–90 天 paper observation 後的 live promotion，而非 Phase II-A reader 的 blocker：

- `beta_core` target／lower／upper band。
- `beta_tilt` 總上限，以及 QQQ／台灣大型股是否有任何一檔可列 core。
- `beta_leverage` nominal cap、effective cap 與最長持有／expiry。
- look-through 的單一公司（尤其台積電）、半導體、Nasdaq growth 與台灣區域 cap。
- drawdown ladder 是採上表 4 tranche，或只用月度／季度 band rebalance 的更簡版本。

## 逐視角發現

### A1 證偽官

- [🔴] **觀察**：目前只有「大盤是長期地基、其餘追 alpha」的方向，沒有何時承認 beta 配置失衡的條件。
  **為何是盲點**：任何跌幅都能被解釋成加碼機會，任何上漲也能被解釋成趨勢延續。
  **修正**：brainstorm 必須定義 target band、rebalance threshold、drawdown ladder、最大槓桿與停止加碼條件。
  **怎麼驗證／何時會爆**：同一組市場資料交給兩次 session，若會產生相反 beta 動作，規則未定義。

- [🔴] **觀察**：若「地基更穩」沒有明確定義為 drawdown、波動、有效 beta 或集中度改善，增加 ETF 數量也能被
  自我解釋成成功。
  **為何是盲點**：目前持倉即已證明多檔 ETF 可同時放大同一台積電／Nasdaq factor。
  **修正**：事前指定主指標：portfolio effective equity、最大單一公司 look-through、beta_core band 與 cash reserve。
  **怎麼驗證／何時會爆**：調整後若名目 ETF 數增加，但上述任一風險指標未改善，就不算「地基更穩」。

- [🔴] **觀察**：使用者方向包含「即使 3x 放到退休也相信往上」，但這把行為承受度與產品報酬事實混為一談。
  **為何是盲點**：daily 3x 的 long-horizon 終值並不只由 index 起點／終點決定。
  **修正**：保留 no-sell 偏好，但把可證偽主張改為「在事前核准的波動／融資成本／持有期 stress grid 下，
  這筆 3x entry 的 loss budget 可承受」，而不是「終值必然上漲」。
  **怎麼驗證／何時會爆**：任何 underlying 累計正報酬而 3x 累計負報酬的路徑都足以推翻必然性；文件內
  +10%／-8% 兩日例子已構成反例。

### A2 反身性／已被定價

- [🟡] **觀察**：大盤急殺本身不是非共識資訊。
  **修正**：beta 建議只回答資產配置偏離與風險補償，不把「跌很多」包裝成 alpha thesis。
  **驗證**：每個 beta 動作必須能指出 policy band／regime observation，而非敘事。

### A3 證據稽核

- [🟡] **觀察**：`market_usd` 依賴 GOOGLEFINANCE，DRAM 已有 ticker 失敗註記，TYO:7803 又使用手動價格公式。
  **修正**：保留 price source／override／as-of metadata；過期或取價失敗時 beta monitor fail closed。
  **驗證**：任一非零持股 market value 為 0 或無 as-of 時，brief 必須顯示 data-quality exception。

- [🔴] **觀察**：Google Sheet 是 live holdings authority，但不是 household assets／liabilities authority。
  **修正**：增加獨立的 capital-capacity input，至少有 external cash、other investments、drawn debt 與 undrawn limits；
  所有欄位需 as-of、currency、source 與確認狀態。
  **驗證**：移除 Sheet 外口頭資訊後，若系統仍能報 household surplus 數字，代表它在幻覺 capital denominator。

### A4 瓶頸壓力測試

- 此視角不適合直接判斷廣泛 ETF；重大盲點已由 factor concentration 取代。

### A5 敘事 vs 數字

- [🔴] **觀察**：目前 `bucket` 是 CORE／大盤／槓桿／觀察，混合「投資目的、風險型態、研究成熟度」三個維度。
  **修正**：Sheet 下一版分開 `asset_type`、`strategy_sleeve`、`research_scope`；不得再由單一 bucket 推全部語意。
  **驗證**：每個持股都能無歧義回答「是 beta_core、beta_tilt、beta_leverage、alpha_single_name 或 cash」。

- [🟢] **已收斂**：使用者已確認本策略可用額度的利息按月支付、期間不攤還本金、到期一次還本，且契約允許
  投資用途；策略目標是約 30 年後退休淨終值最大化。
  **保留邊界**：未提款仍只算 contingent liquidity；每筆 draw 仍需 exact-choice review，提款後 cash／debt 同時入帳。
  **驗證**：增加 undrawn limit 不得改變 Daily cash-supported range；只有使用者明確提款後，資產與負債才同時改變。

### B6 回測誠實官

- [🟡] **觀察**：若日後加入 regime signal，不能拿同一段歷史反覆調 drawdown 門檻。
  **修正**：先定規則再做 walk-forward／paper observation，保留未採納訊號。
  **驗證**：至少一個完整風險循環後，檢查扣除交易成本的相對結果。

- [🟡] **觀察**：只看 TQQQ 自成立以來的成功路徑，容易把一段強 Nasdaq trend 當成所有退休期路徑。
  **修正**：stress grid 必須涵蓋高波動橫盤、先跌後漲、利率高檔與長期溫和成長，不以單一起始日證明策略。
  **驗證**：若換起始月份、提款／投入時點或 financing cost 後結論翻轉，策略是 path-dependent，不得宣稱普遍成立。

### B7 Regime 依賴

- [🔴] **觀察**：「beta 急殺」未區分流動性 shock、衰退重定價、利率 shock 或單一科技 factor unwind。
  **修正**：regime 只能作風險縮放器；第一版先用少量可觀測狀態，不做宏觀預言模型。
  **驗證**：同跌幅但不同利率／信用／波動背景應允許不同建議。

- [🟡] **觀察**：SOXX 的回檔不能直接當成 broad beta 的便宜訊號；截至 2026-07-22 官方資料仍顯示 YTD
  NAV total return +84.67%、3 年 equity beta 約 2.00、P/E 約 69.78。
  **修正**：drawdown trigger 綁核准的 core benchmark；sector/thematic ETF 只受自己的 tilt band 管理。
  **驗證**：SOXX 急跌但 VWRA core 仍在 band 時，不得自動動用 core beta budget。
  **來源**：[iShares SOXX 官方資料](https://www.ishares.com/us/products/239705/SOXX)。

- [🔴] **觀察**：accumulation-only 對 unlevered broad beta 與 daily 3x 的 regime 敏感度不同。
  **修正**：core 可用低頻 contribution routing；leverage 必須在 entry 時用 volatility／drawdown／financing-cost
  stress 決定是否仍有 `new_money_permission`。
  **驗證**：相同 Nasdaq 長期 CAGR 下，提高日波動後若 3x 終值／drawdown 顯著惡化，系統必須收緊新增額度。

### B8 訊號落地縫隙

- [🔴] **觀察**：Engine D 目前有 company cohort 與 portfolio hedge context，尚無 sleeve-level decision object。
  **修正**：新增 `Portfolio Sleeve Monitor`，輸出 `HOLD / PAUSE CONTRIBUTION / CONTRIBUTE REVIEW / STRUCTURAL REVIEW`，
  不走 company onboarding。
  **驗證**：QQQ/VWRA 不再產生 company cohort 待辦，但配置越界仍能在 daily 出現一個聚合項目。

- [🔴] **觀察**：「逢跌加碼」沒有 budget freeze 時，每一層 drawdown 都可能重新把全部現金當成可部署資金。
  **修正**：跨入第一個 tier 時凍結 `beta_budget = min(core_gap, verified_deployable_cash)`，後續 tranche 只切這一筆 budget。
  **驗證**：連續四級下跌後，累計部署不得超過首次凍結 budget，且 alpha reserve 保持未動用。

- [🔴] **觀察**：傳統 `REBALANCE` action 暗示可以賣出，但使用者方向是 accumulation-only。
  **修正**：sleeve output 改為 `CONTRIBUTE / PAUSE CONTRIBUTION / HOLD / STRUCTURAL REVIEW`；只有產品結構例外
  或使用者明確 override 才出現 sell-side action。
  **驗證**：sleeve 超過 upper band 時，系統應把新錢導向其他 sleeve，而不是自動產生賣單建議。

- [🔴] **觀察**：若 RSI／MACD／MA 同時負責 timing 與 sizing，極端 oversold 會繞過 capital／leverage cap。
  **修正**：Engine C 只產 technical state；Engine D 先算 hard ceiling，再讓 `signal_pace` 切 tranche。
  **驗證**：把 RSI 從 35 降到 15，若 remaining effective capacity 不變，safe maximum 不得增加。

### B9 風控／部位

- [🔴] **觀察**：TQQQ／00631L 與普通大盤混在總 equity beta，表面分散可能隱藏槓桿放大。
  **修正**：beta_core、beta_tilt 與 beta_leverage 分開設上限；槓桿曝險以 effective exposure 而非 market value 計。
  **驗證**：報告同時顯示現金權重、名目 beta、槓桿後 effective beta 與主要區域／產業集中。

- [🔴] **觀察**：目前估算的 effective equity 下限已約 98.62%，但這還沒套 SOXX 約 2.0 beta、個股 beta 與
  ETF look-through；在這個狀態新增 beta 可能提高總風險，而非穩固地基。
  **修正**：任何 beta deployment 先算 factor-adjusted effective exposure；未完成前預設 `PAUSE CONTRIBUTION / REVIEW`。
  **驗證**：若只看 market value 會允許加碼、套 effective exposure 後會越 cap，系統必須採後者並 fail closed。

- [🔴] **觀察**：`daily leveraged ETF × balance-sheet borrowing` 是 stacked leverage；兩者相乘放大 asset drawdown，
  但貸款本金／利息不隨 ETF 跌幅下降。
  **修正**：不另建通用 debt stress engine，但 exact-choice review 必須比較 gross effective exposure、每月利息與
  退休淨終值；daily 3x 維持衛星上限，不能只因借款期限長就升為主力。
  **驗證**：若加入借款成本與到期本金後，候選配置的退休淨終值分布不優於無借款方案，或每月利息需靠賣出
  beta 支付，該 tranche 不成立。

### C10 系統整合縫隙

- [🔴] **觀察**：Google Sheet 是 live inventory SSOT，但沒有策略 sleeve authority；Decision Cohort 又不應承擔 ETF 分類。
  **修正**：Sheet 保存使用者核准的 sleeve metadata；Engine D 只讀並聚合，policy 保存 bands，daily exception-first 呈現。
  **驗證**：修改一筆核准 sleeve 後，下一次 daily 的 alpha cohort 與 beta aggregate 分流可重現。

- [🔴] **觀察**：Engine D 目前只有 Sheet holdings，無法知道表外現金／資產與 debt；因此 account-level exposure
  被誤讀成 household-level capacity。
  **修正**：先設計最小、人工確認的 capital-capacity snapshot；它只影響 portfolio permission，不寫回 Sheet、
  不把 lender limit 當 NAV。
  **驗證**：同一持倉搭配不同外部現金／drawn debt 時，系統必須產生不同 surplus 與 stacked-leverage 結果。

- [🟡] **觀察**：若因 ETF 標的固定就完全繞過 unified pq，`CONTRIBUTE REVIEW` 會成為 Engine D 之外的第二條
  live-capital 核准路徑。
  **修正**：日常 telemetry 無 pq；只有需要使用者投入／處理結構例外的 action 進現有 pq2，且沿用 choice／manual fill 邊界。
  **驗證**：任何 beta live fill 都能回溯到 explicit choice／permission；`HOLD` 日不得製造 todo。

- [🔴] **觀察**：使用者期望成交後由系統更新 Google Sheet，但現行 adapter 只有 readonly scope，且 Sheet 存在
  同 ticker 多列；直接按 ticker 寫回可能改錯 broker position。
  **修正**：新增 user-triggered narrow write adapter 與穩定 `position_id`；pending checkpoint → exact write → read-back
  digest → `record-fill`，任何 partial failure 留 reconciliation exception。
  **驗證**：兩列同 ticker 時，只有指定 `position_id` 的 shares／cost 改變；重放同 execution_ref 不得重複加股數。

### C11 單一視角風險

- [🟡] **觀察**：系統長期以產業瓶頸／Serenity lens 找 alpha，容易低估持股其實共享相同科技 beta。
  **修正**：beta monitor 必須是第二個獨立 lens，不因 alpha thesis 強就降低 factor risk。
  **驗證**：即使所有單股 thesis 未變，組合 factor 超標仍能提出 HEDGE／DE-RISK review。

### C12 可操作性／scope

- [🟡] **觀察**：一次替 16 個持股做完整 onboarding 成本過高。
  **修正**：先只替非大盤單一個股建立有實質 claim 的 MVRP/cohort；ETF 進 sleeve，個股依持倉與風險排序分批。
  **驗證**：daily 首屏維持 exception-first，不因持股數線性增長。

- [🟡] **觀察**：一次加入完整技術因子平台、最佳化器與通用 Sheet 編輯器會過度設計。
  **修正**：第一切片只做固定 universe、日線 close、RSI14／MACD 12-26-9／SMA20-50-200／252d drawdown、
  discrete signal pace，以及只更新 position row 的窄 writer。
  **驗證**：不需要 LLM 或任意 Sheet range write，就能從日線資料產一個可重現 `CONTRIBUTE REVIEW` 並完成 read-back receipt。

- [🔴] **觀察**：本機 Daily 若遇關機、排程未啟動或單一 provider 失敗，技術資料可能悄悄停在舊交易日；
  指標數值仍看似正常，卻不是當日訊號。
  **修正**：每條 benchmark 保存 `last_complete_session` 與 digest，Daily／Weekly 做 missed-run heartbeat；stale／missing
  一律 fail closed，只補價格 bar，不回填成當時已發生的 decision。
  **驗證**：刻意跳過兩個排程日再啟動，系統可補齊 bars、明確顯示漏跑期間，且不產生倒填的 live review。

- [🟡] **觀察**：台北 06:30 同時服務美股與亞洲市場，時間語意不同；若把 fetch time 當成共同 market close，
  會製造假同步。
  **修正**：每條 series 使用自己的 `last_complete_session`／exchange timezone；只有需要台股當日收盤立即動作時
  才另加 14:30 regional task。
  **驗證**：06:30 brief 中美股與台股能顯示不同 session date，且 freshness 判斷各自正確。

## 整體可證偽條件

核心假設改為「accumulation-only beta 可用 contribution routing 管理；自有現金走 deterministic range，使用者明確
指定且能持有到期的貸款只走 manual tranche，目標是退休淨終值最大化」。若每月利息必須靠出售 beta 支付，貸款
與 no-sell policy 不相容；若扣除累計利息、機會成本與到期本金後，貸款方案不優於無貸款方案，借款提高終值的
假設即被推翻。若 underlying 長期上漲但 daily 3x 仍產生不可承受虧損，`beta_leverage` 不得因退休 horizon 自動
取得新增資金。若 changing RSI／MACD／MA thresholds 會改變 hard safe ceiling，代表 timing 與 sizing 責任沒有隔離；
若 sleeve aggregate 仍無法解釋 ETF 內部 factor，需提升 look-through 粒度。

## 接下來盯什麼

1. Phase II-A plan／唯讀 adapter／strict schema／freshness／FX／content digest／Daily 四欄均已完成；先觀察
   `sheet_conservative_range` 與 `household_cash_supported_range` 的差異是否真的改善決策。
2. 繼續累積 30–90 天 paper observation；再核准 live beta bands 與 drawdown ladder。貸款政策不另開 Phase II-B engine。
3. 使用者提出實際提款時，再以當時利率、exact instrument／tranche 比較退休淨終值；核准後 cash／debt 原子更新。
4. 私人 `Capital Authority` 的還款條款日後另以明確 Sheet write 同步；本次只更新 tracked policy，不擴張 readonly runtime。
5. ETF 完整 look-through、explicit-fill-only Sheet writer 與 server promotion只有在重複摩擦出現時才另立切片。

## 2026-07-29 延伸：Daily Mobile 首屏與完成通知

使用者以 Codex Mobile 實機檢視後，確認寬表格會讓燈號、ticker 與多欄指標擁擠換行。後續若正式修改
Daily Brief，採以下 presentation hierarchy；這是 UI／通知 brainstorm，不改 technical policy、capital range
或人工 live gate：

1. 首屏先列主力大盤 ETF／權值：`QQQ`、`TQQQ`、`LON:VWRA`、`SOXX`、`00631L.TW`、
   `2330.TW`、`00981A.TW`；`0050.TW`／`006208.TW` 可置於同類次順位。本輪語音輸入出現 `VERA`，
   暫按現有 universe 的 `LON:VWRA` 理解，正式改 universe 前需再核對。
2. Mobile 不用多欄 table；每檔只顯示 ticker＋文字燈號、一行必要指標與一句原因。燈號必須配文字，
   `可評估` 不得縮寫成 `買進`，也不推定 choice／order／fill。
3. `GOOGL`、`TSLA`、`NVDA`、`MU` 等個股繼續追蹤，但放在次區塊，以一兩句 exception-first 摘要或
   可摺疊內容呈現；只有狀態改變或形成非零 review range 才提升到首屏。
4. 1／5／20 日漲跌可作為 App-like context，但必須由正式 TechnicalObservation／可重現行情計算提供；
   2026-07-29 已實作為 Engine C adjusted-close `return_1d`／`return_5d`／`return_20d`，由 06:30 fixed entry
   隨 technical refresh append；舊 observation 保持 NULL，不回寫假造歷史 decision。
5. 通知先觀察 Codex Inbox，不立即增加外部服務。若一段時間後仍無法可靠提醒手機，第一個 fallback
   候選是 Discord webhook；token／URL 只放本機 `.env` 或 private authority，實作與 unattended send
   必須另行核准。
