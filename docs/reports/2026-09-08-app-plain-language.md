# APP 白話化＋單檔走勢圖

**日期：** 2026-09-08　**Zoom／Review：** Z1（純呈現層；字彙不動）／R1（別名是否宣稱過多、細節是否真的沒刪、走勢圖是否變成訊號）　**Verdict：** GO

## 1. 使用者原話與對應處置

| 回饋 | 處置 |
|---|---|
| 「單檔判讀太多展開、太多字、太多『這不是』」 | 頁面重排成 7 段，**只有一個** `<details>`；原本六個面板的每一格原樣收在裡面 |
| 「全部是內部術語，基本上看不懂」 | 加一層**顯示別名**（字彙不改）；前端不再維護第二份對照表 |
| 「單檔點進去，可能還是要有個股價走勢會比較好理解？」 | 加 180 個已收盤交易日的收盤折線（含十字線 tooltip 與表格版） |
| 「『錨點前／入圖以來／超額』是啥意思」 | 欄名改白話，術語降到表下說明列 |
| 「結案歸因又是啥」 | 改成「已結案的判斷」＋副標；四個計數器全改 |

## 2. 字彙一個字沒改

別名住 `briefing/analyst_view/contracts.py`（`PLAIN_PANEL_TITLES`／`PLAIN_LINE_LABELS`／`PLAIN_ABSENCE_SHORT`／`PLAIN_READINESS`），經 `.meta.json` 送到 `/api/v1/meta`。

**為什麼不直接改字彙：** `absence_kind`／panel key／line key 是 read model 與 private ledger 每筆紀錄的身分（L10）——改它們等於改紀錄。先例是 2026-09-07 的 `ACCOUNTING_BASIS_DISPLAY`：字彙留 `gaap`，畫面寫「As reported（法定財報口徑）」。

**前端不維護第二份。** app.js 裡原本有一張硬編碼的 `ABSENCE_SHORT`——那正是 L16 說的重造品：字彙一改它就安靜偏離，而且不會有東西報錯。已移除，改讀 API。原地留一行移除紀錄當剎車（測試禁的是 `const ABSENCE_SHORT` 與 `ABSENCE_SHORT[` 這兩種**用法**，不是提到這個名字）。

**別名不得宣稱 authority 沒有的東西**（同 `accounting_basis` 那條）：`ready` 的說明逐字寫著「**不是「可以買」的意思**——這裡只講資料完不完整」。測試斷言 `建議`／`推薦`／`安全`／`值得買`／`該買` 一個都不准出現，而「可以買」只准以否定形式出現。

主要別名：

| 內部字彙 | 畫面上 |
|---|---|
| `supplies_to`／`depends_on`／`constrained_by` | 供貨給／依賴／受限於（原 label 在 hover） |
| `sole_source` true／false／null | 獨家供應／有第二來源／**沒人說過是不是獨家** |
| 替代難度、需求錨點、距需求端 N 跳 | 有多難換掉、誰在花錢、離它 N 步 |
| 錨點前／入圖以來／超額 | 起算前 30 天／起算後到現在／同期比 QQQ 多／少 |
| 上線標的／可量測／結案歸因 | 追蹤中的公司／算得出報酬的／已結案的判斷 |
| `fair_value`／`price_return` | 我們算出的未來目標價／從現價到目標價要漲跌多少 |

## 3. 刪的是版面不是內容

單檔頁新順序：**結論 → 股價走勢 → 卡在哪 → 最脆弱的地方 → 什麼會推翻它 → 我們 vs 市場 → 完整細節**。

`tests/test_webapp_api.py` 斷言：① 這個順序；② 六個面板的 renderer（`renderFundamental`／`renderWhy`／`renderResearch`／`renderEntry`／`renderFreshness`）**都還在**那個 details 裡。API 回應一個欄位沒少。

## 4. 走勢圖是脈絡不是訊號

- 來源 `alpha/providers/close_series.py`，取 180 個**已收盤**交易日——不含今天的盤中 bar（那會讓單日報酬時而是昨收到現價、時而是昨收到今收，一個欄位兩種語意，L12）。
- 在 materialize 端抓、存進 artifact 的 `price_series`；**`freshness_identity` 不含它**——價格動了不算認知變了。
- **不畫任何均線或動能指標**，測試直接掃 `priceCard` 那段程式碼禁 `sma`／`rsi`／`macd`／`均線`／`突破`。
- 單位是 provider 報價單位原值、未換算幣別，畫面標明（IQE.L 是 GBp，與 GBP 差 100 倍）。
- 抓失敗只是沒有折線，**不讓整份 artifact 失敗**。

## 5. 驗收

| 條件 | 結果 |
|---|---|
| 白話別名只有一個家 | ✅ contracts → `.meta.json` → API；`plain_absence_short` 與 `absence_kinds` 涵蓋同一組 key（測試斷言集合相等，少一個就會有一格顯示裸 key） |
| 前端無第二份對照表 | ✅ `ABSENCE_SHORT` 的兩種用法都不存在；只留一行移除紀錄 |
| 別名不宣稱更多 | ✅ 五個誇大詞禁用；「可以買」只准否定形式 |
| 細節沒刪 | ✅ 六個 renderer 都在 details；順序測試通過 |
| 走勢圖 | ✅ 30 檔全有序列（145–180 個交易日）；`priceCard` 內無任何動能指標 token |
| 測試 | ✅ 2,110 → **2,114 passed／1 skipped**（新增 4 條守衛） |
| 部署 | ✅ 35 份 artifact 重新 materialize；daemon 重啟後 `/api/v1/stocks/COHR` 帶 180 筆序列 |

## 6. 誠實邊界

- **未做 render-and-look。** 我看不到瀏覽器——版面在手機上是否真的變好讀，要你開一次 `#/`（單檔）與 `#/positions` 才算數。
- 別名只涵蓋**最常出現**的那批 key；`assumption:*`／五軸分數等長尾仍是原 label，它們住在「完整細節」裡。若你點開後仍覺得看不懂，那批可以再補。
- `variant_view`／`thesis` 等欄位的**內容**本來就是研究員寫的散文，白話化只能改標籤，改不了內容。
