# 開發：Phase 7 批次三——ROADMAP 盤點後「除了 S6 都可以直接做」的五項（2026-11-01）

> 日期 2026-11-01｜狀態：**APPROVED**（使用者 2026-11-01「感覺除了S6都可以直接做欸？ 做完我們再來討論S6？」＝ROADMAP 2026-11-01 盤點
> 的開放項裡，S6（個股頁 schema 維護）之外全部授權施工；S6 留到本批做完再討論）｜載體：本檔＋ROADMAP（開發項不走 pq2）。
> **順序（同日告知使用者）：** A 邊緣門檻的遲滯與「在門檻上」計數器 → B 週額度常駐計數器 → C 敘事 stale 計數器 ②④＋寫入端拒收
> 「一字不改」 → D 成交紀錄 8 個遺留（資本路徑，收尾跑一次窄範圍 R2）→ E 20-F 年度封面股數（排最後）。撞到要使用者選的就停下問。
> **不碰：** 四個人工 gate 的語意（入圖、Engine C 判讀寫入、thesis mutation、live）；邊緣門檻值本身（`config/alpha_screen.json`）；
> AGENTS 判準句；ROADMAP 的 Phase／Step 定義。

## 0. 進度

| # | ROADMAP 列 | 做什麼（一句） | Zoom／Review | 狀態 |
|---|---|---|---|---|
| A | 邊緣門檻的遲滯與「在門檻上」計數器 ○ | 撤回建議只在**連續兩次**判定都非邊緣後才出現；候選板、心跳、closure-gate 多一格「在門檻上」 | Z1／R1 | ✅ 11-01（回放 K=1 撤回建議 5 → K=2 4＋1 待確認；真資料在門檻上 20、待確認 0） |
| B | 週額度常駐計數器 ○ | daily 短版 ④ 每天印週額度與 5 小時用量；互動 fan-out 前有命令可讀同一個數 | Z1／R1 | ○ |
| C | 敘事 stale 計數器 ◐（剩 ②④＋寫入端拒收） | ②騎的讀圖 kind 變了、④供給側家數變了也列「該重寫」；寫入端拒收一字不改的換版 | Z1–Z2／R1 | ○ |
| D | 成交紀錄遺留 ①②③④⑥⑧⑨⑩ | `scripts/record_trade.py` 的八個已知小洞 | Z1／**R2**（資本路徑） | ○ |
| E | 海外財報來源 ◐（剩 ②20-F） | 20-F 年度封面股數進 Engine C；ADS 比率要使用者選就停 | Z2／R1 | ○ |

## A 邊緣門檻的遲滯與「在門檻上」計數器

```
INTAKE
Zoom: Z1（候選板讀邊緣判定的那一格、閉環母體讀同一格、心跳與 closure-gate 的印法；SIDE_GROUPS 與門檻值不動）
Review: R1（A3 研究判斷的呈現與計數；不寫任何 authority；撤回仍是使用者 go；六條 R2 trigger 都不命中）
Case: failure log #110 第 4 次（11-01 LYC.AX 重寫隔天又回到 13 家、照規則撤回；10-22 起 11 天內撤回 5、重寫 3）
```

**現況（2026-11-01 唯讀）：** `alpha/providers/candidates.py::derive_row` 看到當天 `edge.state == "not_edge"` 就把列放進附組
「非倍率候選」，⑤「敘事該重寫」那一格的「非邊緣仍有敘事 N」與心跳段 2 的「非倍率（有舊敘事 N）」都讀這個附組；drain 看到就撤回。
判定的輸入取 Engine C **最新一筆**快照（`market_normalization.screen_inputs`：`financial_snapshots`／`consensus_estimates` 的
`snapshot_date` 最新列），沒有「前一次怎麼判」的概念，也沒有任何計數器說「這檔在門檻上」。
Engine C 的表**每天都留一列**（`snapshot_date`／`consensus_estimates.snapshot_date`），所以「前一次判定」不必另存序列：對同一批
輸入加 `snapshot_date <= 前一日` 就重算得出來（INV-6：T 時刻我知道什麼）——回放也用同一條路。

**做什麼：**
①`screen_inputs`／`edge_states` 加 `as_of`（只取 `snapshot_date <= as_of` 的列）並回報實際用到的輸入日 `inputs_as_of`；今天判非邊緣的檔
另算一次「輸入日前一天」的判定掛在 `edge["prior"]`（同一個 FX 快取，一輪仍只打一次外部）。
②`derive_row`：非邊緣**且前一次也非邊緣**才進「非倍率候選」；前一次不是（邊緣、無法量、沒有更早的判定、沒讀到）＝「非邊緣待確認」——
缺 X／等回落／不要照敘事分組、列上 `edge_note` 寫「非邊緣待確認：今天判非邊緣、前一日（日期）判邊緣——明天再看，連續兩次才列撤回建議」；
宣告可開的照「缺輸入不放行」的既有路放進「可開但邊緣無法量」附組（同一句標記）。`counts.not_edge_pending` 常駐。
③翻回來（非邊緣 → 邊緣）照舊**不加遲滯**：沒有敘事的邊緣檔仍進「邊緣卻沒敘事」。
④「在門檻上」：`alpha/edge.py` 純函式——分析師在上限 ±1 家（11–13）或市值在上限 ±10%（9.0B–11.0B USD）；每個判定帶 `on_threshold[]`；
候選板 `on_threshold[]`（整個宇宙逐檔：代號、判定、家數、市值、哪一條在門檻上、有沒有敘事）＋`counts.on_threshold`；心跳段 2 每天印檔數與名單、
短版 ④ 非 0 才印檔數；closure-gate 印一行；只計數、不排序、不改門檻。
⑤閉環母體：`population_for` 多一個輸入 `edge_pending`——非邊緣待確認的檔留在母體（理由碼 `not_edge_pending`），母體與候選板不會一邊撤一邊留。
⑥`python -m alpha edge <T…> --replay --from D --to D`：逐日重算判定序列（同一個函式、同一份門檻），對「連續 K 次」K＝1／2／3 各印撤回建議與
重寫出現幾次——驗收命令，也是日後回放的工具。

**四問：** ①根除（門檻上的單日翻轉不再直接變成撤回建議）＋顯形（在門檻上、非邊緣待確認兩個常駐計數）。②程式。③加一個「前一次判定」的比對——
拿掉的是「當天一筆就撤回」。④最先壞掉的那一筆：**同一天第二次 materialize**（互動 session 重算）——前一次若定義成「上一次 materialize」，
同日兩次就會把同一筆快照數成連續兩次，遲滯形同沒有；所以前一次定義成**輸入日前一天的判定**（`inputs_as_of − 1`），同日重算答案不變。
看過：11-01 的候選板 `not_multiple` 0、無敘事 107 檔非邊緣——後者沒有敘事、不受遲滯影響，計數不變。

**驗收（現有資料回放，不是「幾檔通過 filter」）：** `--replay` 對 002837.SZ、6481.T、LYC.AX、AMKR 回放 2026-10-10～11-01 的判定序列：
K＝1（現行）撤回建議出現次數 vs K＝2（本次）；「在門檻上」在心跳段 2 每天印（11-01 第一次印出的檔數記在落地段）。
機制：測試＋變異（拿掉前一次比對 → 紅；前一次沒讀到 → 待確認而不是非倍率 → 綠）。
**前置：** 無。

**落地（2026-11-01）：** `alpha/edge.py`（`on_threshold`／`band_label`／`not_edge_confirmed`／`replay_retraction_suggestions`、帶寬與
`NOT_EDGE_CONFIRM_RUNS=2` 常數）；`alpha/providers/market_normalization.py`（`as_of`、`inputs_as_of`、共用 `fx_cache`）；
`alpha/providers/edge.py`（`edge_states(as_of, fx_cache)`、`attach_prior_judgments`、`edge_states_with_prior`、`replay_edge_states`）；
`alpha/candidates.py`（`not_edge_pending_note`、`on_threshold_entries`／`on_threshold_line`、`counts.not_edge_pending`）；
`alpha/providers/candidates.py`（`derive_row` 的非邊緣格、`candidate_context` 改用 `edge_states_with_prior`、`load_board` 的 `on_threshold[]`）；
`webapp/materialize.py`＋`webapp/contracts.py`（candidates /3；序列多 `edge` 兩格）；`crons/heartbeat.py`（段 2 兩行、快照兩鍵、附組只數真的少輸入的）；
`crons/daily_brief.py`（短版 ④ 非 0 才印）；`alpha/closure.py`＋`alpha/providers/closure.py`＋`webapp/__main__.py`（母體 `not_edge_pending`、
closure-gate 一行）；`alpha/cli.py`（`edge --replay --from --to`）。文件：ROADMAP 列搬進已交付索引（原列封存 archive/roadmap-backlog-log.md）、
failure log #110 末欄、ARCHITECTURE 候選板段、CONCEPTS 邊緣判定、research-drain skill 非倍率段。
**回放 10-21～11-01 四檔：** K=1 撤回建議 5／重寫 3（＝實際發生的 5／3）；K=2 撤回建議 4（各晚一天）＋LYC.AX 11-01 待確認／重寫 3；K=3 撤回建議 3／重寫 2。
英維克 7 天、THK 5 天的出走不是單日雜訊——遲滯只擋 LYC.AX 這種隔日翻回的；要不要把 K 加到 3 留給使用者（本次照 ROADMAP 寫的 2）。
**真資料（11-01 全量 materialize）：** 在門檻上 20 檔（分析師 11–13 家 17 檔、市值 9.0B–11.0B 美元 3 檔；其中有敘事 6 檔：002270.SZ、002837.SZ、6268.T、
AMKR、MXL、SPB.TO）、非邊緣待確認 0、非倍率仍有敘事 0；心跳段 2 第二行與 closure-gate 都印得出名單。測試：`tests/test_edge_hysteresis.py` 15 條＋
`tests/test_candidates.py`／`test_coverage_counts.py`／`test_webapp_candidates_series.py` 改動；相關 12 檔 336 passed。
