# 盲點審查報告：Beta 地基＋Alpha 衛星的 Daily Decision Workflow

> 狀態：下一階段 brainstorm；尚未授權實作 target bands、regime 規則或自動調倉。
>
> 本主題已與 Paywall ROI／合法手動入口、Token-efficient Daily Runner 一併收斂到
> [`2026-07-26-next-phase-operating-model-requirements.md`](2026-07-26-next-phase-operating-model-requirements.md)；
> 本檔保留 Portfolio Sleeve 的深度需求。

## 最危險的三個盲點（先看這個）

1. 🔴 **把所有 Sheet 持股都當 company cohort** — 現行 `decision_lab today` 會把每個正持股列成 `sheet_only_holding`，但 QQQ／VWRA／0050 等是 portfolio sleeve，不是可用公司圖譜 onboarding 的單一企業；硬塞會製造假 thesis 與 daily 噪音。
2. 🔴 **「大盤急殺後先追 beta」若沒有預先規則，就是事後 market timing** — 使用者提出 beta 急跌時是否優先加碼，但目前沒有 target band、drawdown ladder、regime definition 或冷卻期；模型可每天換理由，無法稽核。
3. 🟡 **名為穩固地基，不代表 factor 真分散** — 現有 Sheet 的「大盤」含 QQQ、VWRA、0050、006208；再疊加 SOXX、TQQQ、00631L 與大量科技個股，可能仍是美國 mega-cap／台灣半導體／槓桿 equity beta 的同向曝險。

## 逐視角發現

### A1 證偽官

- [🔴] **觀察**：目前只有「大盤是長期地基、其餘追 alpha」的方向，沒有何時承認 beta 配置失衡的條件。
  **為何是盲點**：任何跌幅都能被解釋成加碼機會，任何上漲也能被解釋成趨勢延續。
  **修正**：brainstorm 必須定義 target band、rebalance threshold、drawdown ladder、最大槓桿與停止加碼條件。
  **怎麼驗證／何時會爆**：同一組市場資料交給兩次 session，若會產生相反 beta 動作，規則未定義。

### A2 反身性／已被定價

- [🟡] **觀察**：大盤急殺本身不是非共識資訊。
  **修正**：beta 建議只回答資產配置偏離與風險補償，不把「跌很多」包裝成 alpha thesis。
  **驗證**：每個 beta 動作必須能指出 policy band／regime observation，而非敘事。

### A3 證據稽核

- [🟡] **觀察**：`market_usd` 依賴 GOOGLEFINANCE，DRAM 已有 ticker 失敗註記，TYO:7803 又使用手動價格公式。
  **修正**：保留 price source／override／as-of metadata；過期或取價失敗時 beta monitor fail closed。
  **驗證**：任一非零持股 market value 為 0 或無 as-of 時，brief 必須顯示 data-quality exception。

### A4 瓶頸壓力測試

- 此視角不適合直接判斷廣泛 ETF；重大盲點已由 factor concentration 取代。

### A5 敘事 vs 數字

- [🔴] **觀察**：目前 `bucket` 是 CORE／大盤／槓桿／觀察，混合「投資目的、風險型態、研究成熟度」三個維度。
  **修正**：Sheet 下一版分開 `asset_type`、`strategy_sleeve`、`research_scope`；不得再由單一 bucket 推全部語意。
  **驗證**：每個持股都能無歧義回答「是 beta_core、beta_tactical、alpha_single_name 或 cash」。

### B6 回測誠實官

- [🟡] **觀察**：若日後加入 regime signal，不能拿同一段歷史反覆調 drawdown 門檻。
  **修正**：先定規則再做 walk-forward／paper observation，保留未採納訊號。
  **驗證**：至少一個完整風險循環後，檢查扣除交易成本的相對結果。

### B7 Regime 依賴

- [🔴] **觀察**：「beta 急殺」未區分流動性 shock、衰退重定價、利率 shock 或單一科技 factor unwind。
  **修正**：regime 只能作風險縮放器；第一版先用少量可觀測狀態，不做宏觀預言模型。
  **驗證**：同跌幅但不同利率／信用／波動背景應允許不同建議。

### B8 訊號落地縫隙

- [🔴] **觀察**：Engine D 目前有 company cohort 與 portfolio hedge context，尚無 sleeve-level decision object。
  **修正**：新增 `Portfolio Sleeve Monitor`，輸出 `NO ACTION / REBALANCE REVIEW / DE-RISK REVIEW`，不走 company onboarding。
  **驗證**：QQQ/VWRA 不再產生 company cohort 待辦，但配置越界仍能在 daily 出現一個聚合項目。

### B9 風控／部位

- [🔴] **觀察**：TQQQ／00631L 與普通大盤混在總 equity beta，表面分散可能隱藏槓桿放大。
  **修正**：beta_core 與 beta_tactical 分開設上限；槓桿曝險以 effective exposure 而非 market value 計。
  **驗證**：報告同時顯示現金權重、名目 beta、槓桿後 effective beta 與主要區域／產業集中。

### C10 系統整合縫隙

- [🔴] **觀察**：Google Sheet 是 live inventory SSOT，但沒有策略 sleeve authority；Decision Cohort 又不應承擔 ETF 分類。
  **修正**：Sheet 保存使用者核准的 sleeve metadata；Engine D 只讀並聚合，policy 保存 bands，daily exception-first 呈現。
  **驗證**：修改一筆核准 sleeve 後，下一次 daily 的 alpha cohort 與 beta aggregate 分流可重現。

### C11 單一視角風險

- [🟡] **觀察**：系統長期以產業瓶頸／Serenity lens 找 alpha，容易低估持股其實共享相同科技 beta。
  **修正**：beta monitor 必須是第二個獨立 lens，不因 alpha thesis 強就降低 factor risk。
  **驗證**：即使所有單股 thesis 未變，組合 factor 超標仍能提出 HEDGE／DE-RISK review。

### C12 可操作性／scope

- [🟡] **觀察**：一次替 16 個持股做完整 onboarding 成本過高。
  **修正**：先只替非大盤單一個股建立有實質 claim 的 MVRP/cohort；ETF 進 sleeve，個股依持倉與風險排序分批。
  **驗證**：daily 首屏維持 exception-first，不因持股數線性增長。

## 整體可證偽條件

核心假設是「beta 地基可用低頻 sleeve policy 管理，alpha 個股用高資訊密度 cohort 管理」。若實測顯示
大多數重要動作都來自 ETF 內部成分／單一產業事件，或 sleeve aggregate 無法解釋實際風險，則需把
sector/thematic ETF 升為獨立 tactical-beta decision object，而不能只做 beta_core 聚合。

## 接下來盯什麼

1. 使用者核准四類語意：`beta_core`、`beta_tactical`、`alpha_single_name`、`cash`。
2. 決定哪些現有 ETF 屬 core 或 tactical；特別是 DRAM、SOXX、00981A、TQQQ、00631L。
3. 定義 beta target bands、最小再平衡偏離、drawdown ladder、槓桿後曝險上限與冷卻期。
4. 只為非大盤單一個股建立有 claim／disproof／expiry 的 MVRP/cohort，不建空洞「因為已持有」cohort。
5. Daily 最多顯示：alpha exceptions＋一個 beta sleeve aggregate；正常項目摺疊為 `NO ACTION`。
