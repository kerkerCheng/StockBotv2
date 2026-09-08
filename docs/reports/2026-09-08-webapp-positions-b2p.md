# 呈現責任重切 B2-positions：部位與問責搬進 APP

**日期：** 2026-09-08　**Zoom／Review：** Z1／R1（抽取是否行為保持、兩種報酬語意、樣本效度排序、materialize 是否唯讀）　**Verdict：** GO

這是「呈現責任重切」Phase 的**最後一段持久內容**。Daily 現在只剩心跳。

## 1. 為什麼要先重構

`positions` 的兩個資料源本來都只有 render、沒有結構化回傳：

- `scripts/outcome_if_settled_today.py` 的 `main()` 從頭算到尾直接 `print`
- `decision_lab today` 的計數器——查證後**不需要重構**：`DecisionStore.capital_expression_counters()` 本來就回傳 dict

所以只動了前者，抽出 `collect()` 與三個純函式（`equal_weight_aggregate`／`live_lane_rows`／`anchor_health`）。
理由是 L16 的正面版：**同一份計算要有第二個消費端時，兩邊讀同一個函式**——APP 端另算一份的話，第二份會立刻開始偏離。

## 2. 抽取是行為保持的（驗收的核心）

這支腳本是 daily 排程在跑的（`.codex/rules` 有 exact entry），所以驗收條件是「輸出不變」。

⚠ **不能用逐位元組比對**：今天是交易日，`_provider_series` 會拿到盤中價，連續兩次執行的數字本來就不同（實測相隔數分鐘，AXTI 由 +44.2% 變 +49.7%）。改用**去數字後的骨架比對**：

| 比對 | 結果 |
|---|---|
| 行數 | 74 → 74 |
| 排序後骨架差異 | **0** |
| `main()` 內容 | 只剩 `parse_args → collect → _render`，6 行；`yf.` 與 `_load_shadows` 都不在 |

（中途一次比對出現 6 處差異，全是**相鄰兩列互換名次**——表格依報酬排序，盤中價變動就換位。同一批列、同樣的欄位。）

## 3. 做了什麼

| 層 | 變更 |
|---|---|
| `scripts/outcome_if_settled_today.py` | 抽 `collect()` ＋三個純函式；三個 render 改為消費它們 |
| `webapp/materialize.py` | `build_positions_artifact`（純函式）＋ `materialize_positions`（**只呼叫 `collect()` 不呼叫 render**，所以不 append 排序快照、不寫聚合檔：唯讀） |
| `webapp/{contracts,api,__main__}.py` | 登記第五種 kind；`GET /api/v1/positions`；`materialize --positions` |
| `webapp/static/` | `#/positions`：**真實成交 → 樣本效度 → 常駐計數器 → 等權聚合 → 逐檔**。排版順序本身是判準 |
| Daily | 「部位與問責」由完整段落改成**只印變動**（新增 fill、disproof 觸發、計數器分子變動、live 樣本數變化）；引用報酬時必須標明是 live 還是 shadow |

## 4. 這一頁最容易被讀錯的兩件事（都做成守衛）

1. **兩種報酬的錨點語意不同。** live 以**實際成交價**為錨；shadow 以**入圖日**為錨——那天的語意是「這家公司的 claim 進圖了」，不是「那天是進場時機」。shadow 報酬**不構成選股能力的證據**。測試斷言兩者不得共用同一個數字。
2. **樣本效度先於數字。** 錨點跨度 42 天、判斷錨點 1 筆——反過來排版的話，一份有效 n 接近 1 的觀測會讀起來像 20 個獨立驗證。前端測試斷言「樣本效度」區塊必須排在「等權聚合」之前。

## 5. 驗收

| 條件 | 結果 |
|---|---|
| daily 腳本輸出不變 | ✅ 行數 74→74、去數字骨架差異 **0**；`main()` 只剩 collect→render |
| artifact 照抄 | ✅ 逐格 `is` 比對；計數器直接取 store 的 dict |
| 缺席不是 0 | ✅ 無報酬的列排在最後、值為 `None`，不混進中間當「持平」 |
| materialize 唯讀 | ✅ 測試斷言 `materialize_positions` 內不得出現 `_render`／`_append_ranking_snapshot`／`_persist_aggregate` |
| 認知 vs 內容 | ✅ 價格動→identity 不變；多／少一筆真實成交→identity 變 |
| request path 純讀 | ✅ 四種證明涵蓋 `/positions`；寫入動詞→405；缺 artifact→503＋remedy |
| 真實資料 | ✅ 逐檔 20 列、真實成交 1 檔（COHR）、只有 paper 18 個；計數器 上線 21/28、可量測 19/28、live 1 選擇/1 成交；daemon `state_kinds` 五種齊 |
| 測試 | ✅ 2,088 → **2,110 passed／1 skipped**（新檔 16＋既有調整） |

## 6. R1 發現

- **Daily 會重複抓一次行情**：daily 既有的 `outcome_if_settled_today.py` 與收尾的 `materialize --positions` 各跑一次 `collect()`（各自打 yfinance）。與 beta 的 Sheet 重讀同一形狀。要消除得讓 daily 那支把 artifact 也寫掉，那會讓「render 腳本」與「materialize」兩個責任混在一起，不划算。
- **`unavailable` 21 筆**（多半是無 ticker 的未上市或殘骸）在 APP 只給計數與清單，不當成缺陷——它們本來就沒有價格錨。
- 兩條先前的守衛（「部位與問責不得省略」「尚未有 APP 畫面」）**正確地紅了**，因為事實變了。改成新事實，並把 `AGENTS.md` 的判準改成機械可查：**`python -m webapp status` 列得出那個 kind 才算搬完**——原本寫「目前是部位與問責」是會過期的現況陳述。

## 7. Phase 收尾狀態

APP 六個畫面：單檔判讀／瓶頸排序／資產配置／研究缺口／在等什麼／我的部位。
Daily 模板具名 section：**6,030 → 2,671 字元**。

**Phase 還剩的**：APP 的 alpha 文案去術語化（使用者 2026-09-08 提出「太難懂」），以及 C 留下的「≤7K 實測待下一份 brief」。
