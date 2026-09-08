# 呈現責任重切 B2b：研究缺口與事件監看搬進 APP（`coverage`＋`watches`）

**日期：** 2026-09-08　**Zoom／Review：** Z1（既定計畫內的第三、四種 kind）／R1（唯讀性、分類是否被重造、停滯是否現形）　**Verdict：** GO

## 1. 這一步刻意縮小的 scope

原 ROADMAP 把 `coverage`／`positions`／`watches` 記成一個 bullet。實作前查證後拆開：

- `coverage`、`watches` 的資料源**已有結構化函式**（`coverage_gaps.scan()`、`event_watch.counters()/sweep_due()/is_stalled()`、`leads.trace_backlog()`），materialize 只是照抄。
- `positions` 沒有：`scripts/outcome_if_settled_today.py` 只有 `main()` 直接 render（沒有回傳結構化結果），`decision_lab today` 的計數器也只有 markdown。要做它得先重構這兩支——**而它們都是 daily 排程正在跑的程式**，所以那一步的驗收必須包含「markdown 逐位元組不變」，是另一個 Step 的份量。

**不順便重構整套**，因此本 Step 只交付兩種 kind。

## 2. 做了什麼

| 層 | 變更 |
|---|---|
| `query/coverage_gaps.py` | 抽出 `COVERAGE_TITLE`／`BUCKET_NOTE`／`BUCKET_LABELS`／`BUCKET_NEXT_STEP`／`RESEARCH_GAP_SPLIT_NOTE`／`RESEARCH_QUESTION_TEMPLATE`／`COVERAGE_SCOPE_NOTE` 與 `bucketize()`／`split_research_gaps()`；`render_markdown` 改用它們（markdown 逐位元組不變） |
| `engine_b/event_watch.py` | 從 `_render_watch` 抽出 `watch_detail()`／`wake_target()`（WATCH_KINDS 的平行消費端仍只有一處，L16） |
| `webapp/materialize.py` | `build_coverage_artifact`／`materialize_coverage`；`build_watches_artifact`／`materialize_watches`（後者**唯讀**：不喚醒、不 mark-checked、不改 lead） |
| `webapp/{contracts,api,__main__}.py` | 登記兩個 kind；`GET /api/v1/coverage`／`/watches`；`materialize --coverage --watches`；`status` 列兩者 |
| `webapp/static/` | `#/coverage`：四格 KPI → 🔴 真缺口（每個節點一句可直接進 pq1 的研究題目）→ 產品名詞（摺疊、只計數）→ 🟡 建模待補 → 其餘摺疊。`#/watches`：四格 KPI（在等／停滯／fired 未消化／追源需處置）→ 停滯區 → 追源需處置區 → 全部 watch（本輪該查的在前）。依 dataviz「是不是圖表」判準：這兩頁是計數＋清單，**不畫圖**（>7 類且每類都有意義 → 表格／清單，不是更多顏色） |

**兩個判斷刻意留在來源模組：** 🔴 桶的 `prod:` 切分（前綴比對，可機械重導）與研究題目模板（同一節點永遠得到同一句）——這樣 markdown 與 artifact 不會各養一份判準（L16）。

## 3. 驗收

| 條件 | 結果 |
|---|---|
| 既有 CLI 輸出不因重構改變 | ✅ `python -m query.coverage_gaps` 1,833 bytes、`python -m engine_b.event_watch list` 14,758 bytes，改前改後 `cmp` **逐位元組相同** |
| artifact 照抄 authority | ✅ counts 等於 `bucketize()` 的分桶；counters 等於 `event_watch.counters()`；detail／target 逐筆等於 `watch_detail()`／`wake_target()` |
| 🔴 不被當成研究待辦數 | ✅ `research_gap_real` 與 `research_gap_product_noise` 分開；`prod:` 沒有 `question` 欄位 |
| 停滯不被埋起來 | ✅ `stalled` 獨立成區＋KPI 計數；追源 backlog 只列 `stalled`／`expired`／`unwatched` |
| 認知狀態 vs 內容 | ✅ 節點改名／`poll.last_checked` 更新 → identity 不變；節點由缺口變覆蓋、watch 由 active 變 fired → identity 變 |
| request path 純讀 | ✅ 四種證明涵蓋兩條新路由；四種寫入動詞 → 405；缺 artifact → 503＋各自的 remedy |
| 真實資料 | ✅ coverage：🔴 5（真缺口）／🟡 15／✅ 170／⚪ 6，共 196 節點；watches：在等 38／停滯 11／fired 未消化 39／追源需處置 26。`status` state 4 份 |
| 測試 | 焦點 151 passed（新檔 26 條）；完整套件 **2,091 passed／1 skipped**（2,056 → 2,091；新增 26 條＋既有調整） |

## 4. R1 發現

- `watches` artifact 有 114 KB（38 筆 active＋39 筆 fired＋26 筆 backlog，各帶 query hint 與 entities）。讀取仍是毫秒級，但這是 state artifact 裡最大的一份；若之後 watch 數再翻倍，該考慮把 `fired`／`expired` 收成計數＋最近 N 筆。這輪不做（過早最佳化）。
- `fired_unconsumed` 39 筆——比 08-31 的 38 筆又多一筆。這個數字只會往上，因為沒有人在消化它；APP 現在讓它常駐可見，但**解決它需要人**，不是這一步能修的。
- coverage 的 🔴 只有 5 個，但 🟡 有 15 個——後者的下一步是「補邊」而不是「重新研究」，畫面上把兩者的下一步分開寫，避免使用者把 15 個當成 15 個研究題目。

## 5. Non-blocking debt

- `positions` kind 未做（見 §1），Pane 4 仍只在 Daily。
- `watches` 頁沒有「消化 fired」的動作按鈕——APP 無寫入端點是 hard invariant，處置只能在對話裡做。
- 未做 render-and-look（我看不到瀏覽器）。

## 6. 下一步（只是建議）

**A（daily materialize 排程）**，而不是 C。理由：Daily 一旦不再印這些段落，APP 就必須每天被 materialize，否則使用者打開看到的是幾天前的數字——那正是 L13（管子只接一頭）。A 完成後再做 C 的 Daily 收斂。
