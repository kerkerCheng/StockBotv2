# 呈現責任重切 B2-beta：資產配置搬進 APP（`beta` state artifact＋圖表）

**日期：** 2026-09-08　**Zoom／Review：** Z1（既定計畫內的第二種 kind）／R1（財務呈現：單位、缺席≠0、band 語意）　**Verdict：** GO

## 1. 做了什麼

| 層 | 變更 |
|---|---|
| `webapp/contracts.py` | `STATE_SCHEMA_VERSIONS` 多登記 `beta`（封閉字彙第二個 kind） |
| `webapp/materialize.py` | `build_beta_artifact`（純函式：每格照抄，只加標籤與序列）＋ `materialize_beta`（以 `--no-refresh --no-record-risk` 純讀呼叫 `scripts/daily_beta_snapshot.run()`；序列只搬 Engine C `session_date`＋`close_adjusted`） |
| `webapp/api.py` | state handler 抽成 `_serve_state(kind)`；新增 `GET /api/v1/beta`；503 remedy／note 依 kind 分開 |
| `webapp/__main__.py` | `materialize --beta`；`status` 列 beta |
| `webapp/static/` | 導覽「資產配置」；`#/beta` 畫面：可動用資金（hero＋三小格）→ 現在的配置（水平堆疊條，色跟 sleeve）→ 距目標多遠（分歧條，灰帶＝容忍區間）→ 風控儀表（總曝險／槓桿 ETF 資金占比／換算槓桿曝險／貸款占 NAV／TSMC 已知至少）→ 逐檔卡（心跳、52 週位置儀表、自身收盤折線＋十字線 tooltip＋表格版）→ 新鮮度→「不是什麼」。調色盤＝dataviz 參考實例（深淺兩套）以 `--viz-*` CSS 角色掛載 |

## 2. 依 dataviz skill 的檢核

- 形式先於顏色：配置＝部分對整體→水平堆疊條（≤ 6 段、2px 表面間隙、圖例）；距目標＝對基準的差→分歧條（藍↔紅＋灰中性帶）；單一比值對上限→儀表；價格＝時間趨勢→單系列折線（無圖例、2px、10% 面積淡色、hairline 格線、端點標籤）。
- 色跟實體走：sleeve 的 `slot` 在 materialize 時依 target_allocation 順序固定，過濾／排序不重新上色。
- 狀態色（good／warning／critical）只用在風控儀表，且**永遠配圖示＋文字**。
- 每張圖都有表格版；tooltip 只加分。文字用 text token，不穿系列色。
- ⚠ **未跑 `validate_palette.js`**（本機無 node）：用的是 skill 文件裡已驗證的參考實例、未改任何 hex；換自家色時必須重跑。
- ⚠ **未做 render-and-look**（step 7）：我看不到瀏覽器；請你開 `#/beta` 看一次標籤碰撞、溢出、深淺色。

## 3. 驗收

| 條件 | 結果 |
|---|---|
| artifact 每格與 `daily_beta_snapshot --format json` 逐格相等 | ✅ 測試以 `is`／`==` 逐鍵比對 sleeves／instruments／risk_snapshot／capital |
| 動能欄位整組不進 artifact | ✅ fixture 故意帶 `rsi_14`／`macd_*`，測試掃整份 JSON 鍵名＝空；真實 artifact 同樣為空 |
| 標籤 SSOT | ✅ sleeve／狀態／降級原因全部來自 `portfolio.allocation` 的對照函式 |
| 缺席≠0 | ✅ alpha sleeve `actual=None`→「算不到」；DRAM 無序列→「沒有折線不是價格為 0」；隔離檔保留心跳、標明原因 |
| 認知狀態 vs 內容 | ✅ 價格心跳變→identity 不變；sleeve 狀態變→identity 變 |
| request path 純讀 | ✅ 四種證明涵蓋 `/api/v1/beta`；POST/PUT/PATCH/DELETE→405；缺 artifact→503＋`materialize --beta` |
| 真實資料 | ✅ 6 sleeve／14 檔，序列 7–28 個交易日（DRAM 0）；`status` state 2 份；daemon 重啟後 `/api/v1/health.state_kinds == ["ranking","beta"]` |
| 測試 | 焦點 148 passed（webapp 全部＋beta monitor＋daily snapshot）；完整套件 **2,056 passed／1 skipped**（1,989 → 2,056；B1 後再 +22：beta 17＋既有調整；full-chain 黑箱測試改用與子行程同一時鐘） |

## 4. R1（對抗回合）發現

- **單位**：折線數值是 provider 報價單位原值（TWD／JPY／USD…）未換算——原本沒標。已在 `series_note` 加註「不同檔的折線不可互比高低」。每檔各自一張圖，沒有跨檔同軸。
- `materialize --beta` 用 `--no-refresh`：行情校驗（TWSE freshness）來自最近一次 daily ETL，`report_status=degraded` 是「本次沒重抓」不是資料壞——畫面把 refresh 狀態與說明印出來。
- 貸款占 NAV 的儀表沒有 policy 上限（`callable_debt_cap=0` 語意不同），用 25% 純呈現刻度並標「只記錄，不設上限」——這是呈現刻度，不是新門檻。

## 5. Non-blocking debt

- 資產配置的「持股 NAV 比例」（大盤／CORE／槓桿／CASH／觀察 bucket）來自 `decision_lab today`，不在 beta monitor 的輸出裡，本 kind 沒帶。
- 序列只有 Engine C 觀測起（2026-07-27）之後的交易日；要 52 週折線得在 ETL 端存序列或另開 provider（materialize 刻意不打 yfinance）。
- Daily 的 Beta 段落尚未收斂（Phase C）：AGENTS Beta 契約改動與 skill 模板一起做。

## 6. 下一步（只是建議）

B2 其餘 kind：`coverage`／`positions`／`watches`；或先做 Phase C（Daily 收斂＋AGENTS Beta 契約），因為 ranking＋beta 已經是 Daily 裡最大的兩段持久狀態。
