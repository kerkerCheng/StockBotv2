# Phase 3 Step 3.7 收據：個股頁首屏、稽核區、readiness、鏈段、downside（2026-09-30）

> 開發步驟（Z2，R1）。真實資料 materialize 兩輪，都持互動 writer lock、只寫 derived cache：
> 02:24–02:31 台北（初版）、03:14–03:20 台北（R1 修正後，本檔數字以這一輪為準）；daily 在 05:30。
> 本檔是收據，不是 current-state truth——現況以下列查證命令為準（AGENTS「現況數字會過期」）。

查證命令：`python -m webapp status`、`python scripts/analyst_view_text_digest.py --per-panel`、
`python -m audit invariants --only PointInTime`、`python -m briefing analyst-view <T>`、`python -m pytest tests/test_stock_page_phase3.py -q`。

## 1. 做了什麼（plan §8 六點）

| 點 | 落點 | 真實資料 |
|---|---|---|
| ① 首屏末行 | 注入面板 `candidate`：候選狀態＝候選板同一個 `derive_row`（同一輪共用一份 context）；三個字（會死嗎＝四盞最差色＋灰 N；兩題＝敘事宣告，v1／無敘事「未答」） | 4 檔上板（AXTI 已定價等回落、COHR／LITE 非倍率候選、SIVE.ST 已持有）；69 檔不上板、三個字照印（兩題「未答」）；個股頁與候選板的邊緣判定市值逐位相同 |
| ② 稽核區 | 選配面板 `three_questions`（read model `ThreeQuestionsSection.lines` 的同一個 Datum）；APP 稽核區三題卡（序列逐鍵攤開 EDGAR／台股月營收／分部占比三種形狀、推算出處照印） | 73 檔都有 9–11 行；主題等權組三行全是 `not_yet_recorded`（pq2 [656] 待 go） |
| ③ readiness | `CORE_PANELS`＝headline／brief／argument／research／**readings**／wipeout；讀圖面板狀態只由讀圖對圖決定；as-of 明確拒絕 | 見 §2 |
| ④ 鏈段 | 需求端讀騎的讀圖（或坐的層／插槽的現行讀圖）的需求側客戶；邊照舊；標題改 | 見 §3 |
| ⑤ downside | 注入面板 `downside`：每條反證 → watch id／狀態，沒有的印「未盯」；同一筆 watch 只印一列 | 在盯 49、未盯 240（全部是舊 session assessor 判讀的反證，§14 #29）；10 檔名下沒有任何反證 |
| ⑥ bet | our_bet＋騎的層／插槽（新 `investor_brief.rides`）＋什麼必須為真；沒有價格 | 4 份 v2 三格都有；其餘三格 `not_yet_recorded` |

偏差 27–34、待決 §14 #29–32 見 plan。

## 2. readiness：73 檔前後（3.7 前＝2026-09-29 05:31 台北那一輪 daily 的 artifact）

- 狀態轉移：blocked→blocked 69、ready→ready 4（AXTI、COHR、LITE、SIVE.ST——全部有讀圖）。**0 檔從 ready 掉成 blocked**（L11-6 ④）。
- 63 檔多一個 readings blocker——全部原本就因 `brief=not_yet_recorded` blocked：
  - `not_yet_recorded` 40 檔：坐了層或插槽、那裡還沒有讀圖（下一步：寫讀圖，research-drain 段 5）；
  - `upstream_unavailable` 23 檔：圖上沒有它供貨或開發的層（下一步：補圖或判定它在需求側；settle 管道待決，§14 #32）。
  - 其中 BX 同時少了 `wipeout=upstream_unavailable`（Engine C 補上稀釋那盞燈的資料，與 3.7 無關）。
- 其餘 10 檔（4 份 v2＋6 檔坐在已讀圖的層）readiness 不變。讀圖面板 available 10、missing 63；stale 0。
- `refresh=review_required` 的 12 檔（退役估值鏈殘留，3.0 §4）沒有一檔因此多出 readings flag——面板不吃 `refresh.overall`。

逐檔表（blocker 變化逐檔指得出面板）：

| 檔 | readiness | blocker 變化（原因） | 鏈段需求端 | 首屏末行 | downside |
|---|---|---|---|---|---|
| 000660.KS | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| 002472.SZ | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 4 |
| 005930.KS | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 4 |
| 012330.KS | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| 2301.TW | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| 2455.TW | blocked → blocked | — | 坐的層讀圖 1 份 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| 300308.SZ | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| 3081.TWO | blocked → blocked | — | 坐的層讀圖 1 份 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| 3105.TWO | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| 3363.TWO | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| 4971.TWO | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| 4979.TWO | blocked → blocked | — | 坐的層讀圖 1 份 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| 5016.T | blocked → blocked | — | 坐的層讀圖 1 份 | 不上板｜灰 4／未答／未答 | 在盯 0／未盯 5 |
| 5802.T | blocked → blocked | — | 坐的層讀圖 1 份 | 不上板｜灰 4／未答／未答 | 在盯 0／未盯 3 |
| 6268.T | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 0 |
| 6324.T | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 4 |
| 6481.T | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| 6594.T | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 0 |
| 6680.HK | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| 688017.SS | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| 688836.SS | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 0 |
| AAOI | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜紅（灰 1）／未答／未答 | 在盯 0／未盯 5 |
| AAPL | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| AEHR | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 5 |
| AEVA | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 4 |
| AMAT | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 1）／未答／未答 | 在盯 0／未盯 5 |
| AMD | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| ANET | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| APO | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 0 |
| AVGO | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| AXTI | ready → ready | — | 騎的讀圖 1 份 | 已定價等回落｜黃（灰 1）／是／是 | 在盯 14／未盯 5 |
| BX | blocked → blocked | readings=upstream_unavailable（少了 wipeout=upstream_unavailable） | 圖上沒有坐的層 | 不上板｜黃（灰 3）／未答／未答 | 在盯 0／未盯 0 |
| CCXI | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜綠（灰 3）／未答／未答 | 在盯 0／未盯 0 |
| CDNS | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| COHR | ready → ready | — | 騎的讀圖 1 份 | 非倍率候選｜紅（灰 1）／是／是 | 在盯 11／未盯 4 |
| CRWV | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 4 |
| ENA.V | blocked → blocked | — | 坐的層讀圖 1 份 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 0 |
| FN | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 5 |
| GFS | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| GLW | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 5 |
| GOOGL | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| GXO | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| HEXA-B.ST | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| HIMX | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| INTC | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 5 |
| IQE.L | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| IREN | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| JBL | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 0 |
| LITE | ready → ready | — | 騎的讀圖 1 份 | 非倍率候選｜黃（灰 1）／是／是 | 在盯 6／未盯 4 |
| LRCX | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| LYC.AX | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 4 |
| META | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| MP | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| MRVL | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 4 |
| MSFT | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| MTSI | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 4 |
| MU | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 0 |
| NBIS | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| NOVT | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 4 |
| NVDA | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| ORCL | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜紅（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| POET | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| SHA0.DE | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 0 |
| SIVE.ST | ready → ready | — | 騎的讀圖 3 份 | 已持有｜紅（灰 2）／無法量／無法量 | 在盯 18／未盯 3 |
| SNDK | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| SOI.PA | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 2）／未答／未答 | 在盯 0／未盯 4 |
| TSEM | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| TSLA | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| TSM | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 3 |
| TXN | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜黃（灰 1）／未答／未答 | 在盯 0／未盯 3 |
| UMC | blocked → blocked | readings=not_yet_recorded | 坐的地方沒讀圖 | 不上板｜綠（灰 2）／未答／未答 | 在盯 0／未盯 5 |
| XFAB.PA | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜紅（灰 2）／未答／未答 | 在盯 0／未盯 4 |
| XPEV | blocked → blocked | readings=upstream_unavailable | 圖上沒有坐的層 | 不上板｜綠（灰 3）／未答／未答 | 在盯 0／未盯 3 |

## 3. argument 鏈段（對 3.0 基準 `baseline_p3.json` 的 `views[*].chain`）

- `argument:chain` **73/73 available、0 檔變 missing**；73 檔文字都變（需求端那一句換了來源）。
- 需求端依據：騎的讀圖 4（v2 四檔）／坐的層的現行讀圖 6／坐了但沒讀圖 40／圖上沒有坐的層 23——後兩種都印明示缺席的一句。
- 沒有 sub≥4 邊的 57 檔（與 3.0 同數）：原句「圖裡還沒有 X 的供應鏈連結」改為「X 在圖上還沒有評為難替代（替代難度 4 以上）的連結」（偏差 30；邊的過濾本身待決 §14 #30）。
- 標題 73/73 為「憑什麼這樣想：它在哪條鏈上、錯了怎麼知道、什麼時候知道」。
- `get_bottlenecks` 未退役；`python -m audit invariants --only PointInTime` → PASS（探針仍在）。

## 4. 核心面板文字 digest（`scripts/analyst_view_text_digest.py --per-panel`）

| 面板 | 3.7 前→後 變動檔數 | 原因 |
|---|---|---|
| research | 0 | — |
| argument | 73 | 標題＋鏈段需求端（預期） |
| brief | 69 | 沒寫短評的 69 檔改列 v2 七題——3.4 偏差 #10 的變動，這一輪才第一次被 materialize（標題、notes、理由句不變；只有七題的題目） |
| our_bet | 0 | — |

3.0→3.7 前另有：brief／our_bet 4 檔（3.5 寫的 v2 敘事）、argument 1 檔（SIVE.ST，3.5 之後圖變了）。

## 5. 其他驗證

- 全套測試：`2825 passed, 1 skipped`（R1 修正後，主樹，與 materialize 不並行）。
- 變異檢查：兩輪覆核的 30 個修法各拿掉一行，30 個全紅（途中存活過 2 個：`downside_rows` 的預設參數在定義時綁死根目錄、撤回格子經 page_input 的那段沒人驗——都已修並補斷言）。
- 覆核：R1（5 面向＋逐條反駁，41 條、38 條成立）全修；第二輪 3 個唯讀 agent 逐條核對——blocking 全部修好、無新 blocking，另 13 條 non-blocking 當下修（plan 偏差 #34）。
- `disproof_counts` 抽出 `watch_category`／`condition_key` 後，對真實 registry／lifecycle／讀圖／敘事逐項等於 HEAD 版（預期 37、在盯 37）。
- `python -m audit invariants` → 13 項 PASS（FAIL 0、SKIPPED 0）。
- headless Edge 實際渲染：AXTI（v2、上板）、AAOI（無敘事、坐了沒讀）、2301.TW（台股月營收、圖上沒有坐的層）——首屏末行、論證層 downside、稽核區三題（含推算出處、千元、可用日）都在，畫面沒有內部 key、沒有 Python repr。
- daily ⑬ 同一條命令實耗 330 秒（3.6 前 282–298 秒；上限 25 分鐘）。

## 6. 已知限制（不擋本 Step）

- 13 條既有測試在沒有 `.env`／`library/leads`／`extractions`／watch registry／Engine C 的 checkout 會紅（讀真實資料的測試隔離問題；§14 #31）。
- 舊判讀反證 240 條全印「未盯」、鏈段的邊仍經 sub≥4 過濾、23 檔沒有坐的層的讀圖 blocker 沒有 settle 管道——都是使用者決定（§14 #29、#30、#32）。
