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
| B | 週額度常駐計數器 ○ | daily 短版 ④ 每天印週額度與 5 小時用量；互動 fan-out 前有命令可讀同一個數 | Z1／R1 | ✅ 11-01（兩窗都記；④ 每天一行＋摘要行旗（≥ 80% 只印不擋）；`python -m crons.llm_quota [--probe]`；真資料：daily 06:30 的紀錄 7 天 86%、探針 12:00 當下 **99%**） |
| C | 敘事 stale 計數器 ◐（剩 ②④＋寫入端拒收） | ②騎的讀圖 kind 變了、④供給側家數變了也列「該重寫」；寫入端拒收一字不改的換版 | Z1–Z2／R1 | ✅ 11-03（回放 497 版：⑫ 會擋下 30 次換騎——判讀變了 1＝AEVA、家數變了 29；現行 89 份 ②0 ④0） |
| D | 成交紀錄遺留 ①②③④⑥⑧⑨⑩ | `scripts/record_trade.py` 的八個已知小洞 | Z1／**R2**（資本路徑） | ✅ 2026-11-03（R2 NO_GO（B1、B2）→ 使用者「D 照修法做＋負數價格一起擋」→ 修正 → 窄範圍覆核 GO，見 D 節末） |
| E | 海外財報來源 ◐（剩 ②20-F） | 20-F 年度封面股數進 Engine C；ADS 比率要使用者選就停 | Z2／R1 | ◐ 使用者 11-03「E 1A 2A」→ 施工中 |

> **2026-11-01 12:10 停在 B 之後：** B 自己的探針量到週額度 **99%**（11-02 23:00 重置；daily 06:30 的紀錄是 86%，白天互動 session 吃掉
> 13 個百分點）。C（Z1–Z2 真資料回放）、D（資本路徑，收尾要一位 R2 reviewer）、E 都會再吃同一個池子，而 11-02 05:30 的 daily 起跑在重置之前
> ——照 development-flow「spawn 前先讀週額度、≥ 80% 先說出來」停下，C–E 與 S6 討論等使用者決定是否重置後接續。commit A `1c57bad3`、B `8883a8a6`。
> **2026-11-03 接續**（使用者「繼續吧」）：週額度已重置（`python -m crons.llm_quota` → 7 天 1%）；11-02 那天 99% 仍全部跑完（沒有
> `rate_limited`），11-03 在 `allowed` 時也帶了 seven_day 窗——B 留下的「平常帶不帶七天窗」有答案了：帶。

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
全套 2065 passed（修一條：心跳快照鍵清單多兩個計數器）；commit `1c57bad3`。
**補記（2026-11-01 晚，雲端 session）：** 「全套」不是全部——`tests/test_phase3_full_chain.py` 三條在 `1c57bad3` 之後 ERROR：夾具把
`edge_states` 換成只收 `tickers` 的 lambda，`edge_states_with_prior` 帶 `db_path`／`thresholds`／`fx_cache` 呼叫它就 TypeError。
當下修（一行，夾具改收 `**_kw`），三條回綠。雲端容器全套：4,460 passed、13 failed、6 errors、59 skipped——13 failed 與 6 errors 在改動前的程式上一樣（缺 `library/private` 與抽取檔），與本項無關。

## B 週額度常駐計數器

```
INTAKE
Zoom: Z1（`llm_step._rate_limit` 多記每個窗；心跳段 3／短版 ④ 多一行、摘要行多一旗；一個新的唯讀 CLI；不動任何 authority、
      不動 daily 的步驟清單與 LLM argv）
Review: R1（無人值守路徑只多「記」與「印」；探針是互動命令、與 daily 同一組 argv／白名單／能力檢查；六條 R2 trigger 都不命中）
Case: ROADMAP 列：雷達 10-04 起 24 天有 8 天沒跑，週額度用完 2 次共 6 天（10-09～10-12、10-24～10-25）；互動 session 10-09、
      10-17 兩次整批 agent 撞額度（記憶 feedback-fanout-token-cost）
```

**現況（2026-11-01 唯讀）：** `_rate_limit` 只留 `rateLimitType` 指的那一窗（今天的執行紀錄 17 次呼叫全是 `seven_day 0.86
allowed_warning`，5 小時窗看不到）；心跳段 3 與短版 ④ 的額度行只在不是 `allowed` 才印（`quota_entries`）；互動 session 沒有任何命令可讀。
11-01 探針抓到的原始事件：`status: allowed_warning` 時 `unifiedWindows` 兩窗都在、各帶 `utilization`／`resetsAt`／`status`
（five_hour 0.53 allowed、seven_day 0.97 allowed_warning）。ROADMAP ① 的疑問「平常 allowed 時帶不帶 seven_day」本輪抓不到
（週額度已在警告區）——程式對缺窗的處理是印「未回報」、不猜；11-02 23:00 重置後下一輪 daily 的紀錄就會回答。

**做什麼：** ①`_rate_limit` 多 `windows`（每個窗三格：utilization／resetsAt／status；沒有 unifiedWindows 就 `{}`）——執行紀錄
`calls[].rate_limit` 自動帶著。②`crons.heartbeat.quota_usage(rows)`（最後一次有回報的呼叫；舊格式讀成一窗、另一窗「未回報」）＋
`quota_usage_line`（短版 ④ 每天一行：「LLM 額度：7 天 X%（重置）｜5 小時 Y%（重置）」，週 ≥ 門檻粗體；沒有可讀用量說為什麼）＋
`quota_flag`（摘要行「週額度已用 X%」，只管 7 天窗）；門檻 `QUOTA_FLAG_THRESHOLD = 0.80` 只印不擋；完整心跳段 3 在警告行之後
也印用量行。③`python -m crons.llm_quota [--probe] [--json]`：讀同一個函式；`--probe` 另跑一次最小 `claude -p`（haiku、low、零工具、
與 daily 同一組 argv 與白名單、cwd 同一個空目錄）讀當下的數；exit 永遠 0。development-flow skill R2 段：spawn 前先跑它。

**四問：** ①顯形（兩個常駐計數：短版 ④ 每天一行、摘要行的旗）。②程式。③加記兩窗＋印；沒有拿掉任何東西。④最先壞掉的那一筆：
**舊格式的執行紀錄**（11-01 以前 `rate_limit` 沒有 `windows`）——`quota_usage` 把它讀成一個窗、另一窗印「未回報（舊格式只記一窗）」，
不印 0%；看過：今天的紀錄（17 次呼叫、舊格式）印「7 天 86%｜5 小時 未回報」。

**驗收（現有資料）：** 執行紀錄每次呼叫有兩個窗（11-02 起的 `calls[].rate_limit.windows`）；短版 ④ 每天出現週額度一行（11-02 起）；
一個月內週額度用完導致 daily LLM 步驟 `rate_limited` 的天數（基準 24 天 6 天；量到 12-01，門檻 0.80 到那天再定）。
機制：測試＋變異（拿掉 `windows` → 紅；0.79 → 不加旗 → 綠）。**前置：** 無。

**落地（2026-11-01）：** `crons/llm_step.py`（`_rate_limit` 的 `windows`、`RATE_LIMIT_WINDOW_KEYS`）；`crons/heartbeat.py`
（`QUOTA_FLAG_THRESHOLD`、`QUOTA_WINDOW_ORDER`、`_schedule_zone`／`_reset_text`（從 `quota_entries` 抽出共用）、`quota_usage`、
`quota_usage_line`、`quota_flag`；`_quota_lines_from` 加用量行；`summary_line` 加旗）；`crons/daily_brief.py`（④ 多一行，自己降級）；
`crons/llm_quota.py`（新；CLI＋探針）。文件：ROADMAP 列搬進已交付索引（原列逐字封存 archive/roadmap-backlog-log.md）、盤點句的查證命令
改成只看粗體名稱後的標記（原命令 `grep -v "✅"` 會把內文帶 ✅ 的 ◐ 列也濾掉）、OPERATIONS 心跳段命令＋失敗模式表一列、ARCHITECTURE 段 3 敘述、
development-flow skill R2 段、plans README。測試：`tests/test_llm_quota.py` 11 條；`test_daily_task` 兩處逐項相等、`test_heartbeat_phase1`
用量行隨改；四檔 212 passed；變異①拿掉 windows → 2 條紅、②0.79 不加旗／0.80 加旗。
**真資料：** `python -m crons.llm_quota` → 「**7 天 86%**（11-02 23:00 重置；≥ 80% 只印不擋）｜5 小時 未回報（舊格式只記一窗）」（daily 06:30，
17 次呼叫）；`--probe` 約 12:00 → 「**7 天 99%**｜5 小時 79%」（haiku，2.9 秒，0.0005 美元）——白天互動 session 吃掉 13 個百分點；
11-02 05:30 的 daily 會在週額度重置（11-02 23:00）之前起跑，LLM 步驟預期 `rate_limited`（這就是基準要數的那種日子）。

## C 敘事 stale 計數器 ②④＋寫入端拒收「一字不改」

```
INTAKE
Zoom: Z1–Z2（候選列多一種 rewrite 原因與整板清單兩個 kind；寫入端多一道拒收 ⑫；candidates artifact /6（雲端 session 11-01 已用掉 /4、/5）；⑤ 讀新 kind。
      敘事紀錄的 contract 不動——拒收只看既有欄位）
Review: R1（A3 研究判斷的寫入規則收緊、不放寬任何 gate；不碰資本與 append-only 的既有紀錄；六條 R2 trigger 都不命中）
Case: failure log #93（10-20 使用者點名）：AEVA 換騎跨過 undecided→neither、COHR／LITE／SIVE.ST 換騎跨過 7→9 家，正文一字不改
```

**現況（2026-11-03 唯讀）：** ①騎舊讀圖、③新邊沒讀 10-29 已交付；②④ 沒有任何程式在算——寫入端只檢查 rides 現行、在供給側，
正文一字不改的換騎照收。量測：現行 89 份 v2 裡 25 份的正文版早於現行版、11 份換騎過，判讀與家數都沒變（②0、④0，與 10-29 一致）。

**判法（落地前跑過試圖讓它變假的回放，L11-6）：** 比讀圖紀錄的**結構**——正文版（`body_version`）騎的讀圖 vs 這一格現行的讀圖：
`kind` 不同＝②；快照供給側公司數不同＝④。**不解析正文的「N 家」**：真資料的「N 家」多半是客戶數（「三家具名客戶」「一家不具名的客戶」），
比字面會誤報（L16）。ROADMAP ④ 原句「正文寫死的家數與現行讀圖供給家數不同」量成「供給家數自正文寫成後變了」——涵蓋原句的
COHR／LITE／SIVE.ST，也涵蓋正文沒寫數字、競爭格局已變的情形。同樣家數換了成員不算（回放 0 次）。

**四問：** ①根除（寫入端 ⑫ 擋住「一字不改就過」）＋顯形（候選列與 ⑤ 的兩種新原因）。②程式。③加一道比對；拿掉的是「換騎不看判讀與家數」。
④最先壞掉的那一筆：**判斷不變、只想換騎的那一次寫入**——現在要在正文裡寫一句新的判讀或家數為什麼不改變結論；回放顯示這種情形
過去 30 次（判讀 1、家數 29），都是正文該對一次的情形（例：3363 光纖陣列 2→6 家、6805 快接頭 2→6 家）。

**落地（2026-11-03）：** `alpha/candidates.py`（`supply_side_companies`、`body_behind_readings`、`body_behind_reasons`、兩個前綴與
`BODY_BEHIND_KINDS`、`REWRITE_WHY` 兩個五字）；`alpha/providers/briefs.py`（`_supply_side` 改呼叫同一個函式、⑫ `body_behind_problems`）；
`alpha/providers/candidates.py`（`derive_row(readings_by_id=…)` 的 `rewrite_reading_changes`／`reading_change_unchecked`、`board_rewrite`
兩個 kind、`candidate_context` 載入全部讀圖紀錄、板上 `reading_change_check`）；`webapp/materialize.py`＋`webapp/contracts.py`（/6、check 進
freshness_identity）；`engine_b/todo_ledger.py`（`BEHIND_KINDS` 兩格、`COVERAGE` 兩格、沒算／沒比成的註記）。文件：ROADMAP 列搬進已交付索引
（原列逐字封存 archive；順手補上 B 那一列漏掉的表頭）、failure log #93 末欄、ARCHITECTURE 待做清單段、research-drain skill ⓑ‴。
測試：`tests/test_narrative_stale_24.py` 12 條、`tests/test_todo_ledger.py` 夾具與兩條；變異 4 種各自轉紅（3／2／2／4）。
**真資料：** materialize 後 `reading_change_check` ok、沒比成 0、②0 ④0；⑤「敘事該重寫 6 檔（watch 醒 12 條；已回落 1（AXTI））」照舊、
沒有沒算註記；serve 重啟（/6）health stale=false。

## D 成交紀錄遺留 ①②③④⑥⑧⑨⑩

```
INTAKE
Zoom: Z1（`scripts/record_trade.py` 既有列寫入的例外分支、顯示與兩個新旗標；`fetchers/gsheets.py` 兩個純函式與 `_is_our_row`；
      `risk/hard_caps.py`、`risk/snapshot.py` 的代號比對改走同一條正規化；`canonical_symbol` 搬到 `identity/symbols.py`）
Review: R2（資本路徑：硬擋的已持有加總與 beta 判別、Sheet 寫入的例外分支、trade_log 的新欄位——六條 trigger 命中「資本／append-only」）
Case: 2026-09-30 R2 四輪覆核留下的 non-blocking（原在 ROADMAP「已交付列留下的遺留小項」第一條，交付後移到已交付索引「成交紀錄遺留八項」）
```

**現況（2026-11-03 唯讀）：** 八項都還在——①既有列路徑丟網路例外只印「請手動核對」；②`_held_value_for_symbol` 比原字串；③`beta_instrument_for`
與 `risk/snapshot.py` 的別名表比原字串（`TPE:0050`、`TPE:00631L` 被當 alpha——後者的槓桿 cap 沒比）；④`_is_our_row` 股數比 1e-9；
⑥既有列不讀公式；⑧`--fx-to-base` 只驗 > 0；⑨沒有旗標；⑩`--log-only` 照印「舊 → 新」。

**判法（每項一句）：**
- ① 例外後逐格回讀，每格分四種：還是舊值、已是新值、新舊顯示一樣分不出（`ambiguous`；新舊數值真的相同時是 `same`，無害）、其他（含讀不到）。
  全舊＝此刻沒寫進去（exit 2、不記；11-03 修正：隔 `ABSENT_RECHECK_SECONDS` 再讀一次，訊息不承諾重跑安全——見本節末「修正」）；全新＝記事件並標 `sheet_write_note`；
  寫一半＝**補寫其餘格**（expected 是寫入前的值，照舊逐格重讀），回讀全新才記；其他或分不出＝請手動核對、不補寫、不記。
  **往前補、不往回還原**：Sheet 讀回的是格式化後的字串，分數股寫回會失真；而往前補的每一格都是這筆成交本來就要寫的值。
- 顯示值比對統一成 `gsheets.display_matches(display, value)`：容許的誤差＝顯示到最後一位的半個單位（`0.33` 容 0.005、`100` 容 0.5）；
  讀不成數字一律不算（`$3,000`、`Loading...`、空字串）。建倉路徑的現金回讀（`_cash_outcome`）改用同一個判定。
- ②③ `canonical_symbol` 搬到 `identity/symbols.py`（純函式；`risk/` 不為一條字串規則 import I/O 層），`fetchers.gsheets.canonical_symbol`
  是同一個函式物件；已持有加總、beta 判別、snapshot 別名表三處兩邊都正規化。
- ④ `_is_our_row` 的股數比對改 `display_matches`。
- ⑥ 既有列（非 `--log-only`）多讀一次公式，用建倉同一條多數規則（≥ 三分之二的持股列是公式的欄＝公式欄）判那一列有沒有手寫值；
  有就拒絕（dry-run 也擋，exit 2）——股數一改、手寫的市值不跟著變，NAV 與 5% 都量錯。公式讀不到或那一列對不上＝印「沒能確認」、照常進行
  （跟上線前一樣，不新增一種失敗）。`--log-only` 不擋：Sheet 已由使用者手動改好。
- ⑧ 買進、成交幣 ≠ 基準幣、給了 `--fx-to-base` 時，用同一列（代號正規化＋券商）的「市值 ÷ 股數 ÷ 成交價」反推匯率；比值超出 [0.5, 2]
  就拒收（exit 2，印反推值）——日圓、台幣的倒數與小數點位移都差十倍以上，價格一天的漂移遠小於兩倍；**接近 1 的幣別（歐元對美元）
  給成倒數只差兩成、抓不到**，也不會把硬擋量錯很多。`--log-only` 只警告（成交可能是很久以前）；首次建倉沒有同一列，印「沒能核對」。
- ⑨ `--row-deleted`：只配 `--log-only`、只收賣出、必須明給 `--currency` 與 `--broker`（沒有那一列可以讀；後兩條是 11-03 修正）、Sheet 還有那一列就拒收；不定位；事件多記
  `sheet_row: deleted_by_user`。`--log-only` 定位不到時的提示多一行指路。
- ⑩ `--log-only` 改印「Sheet 那一列現在：shares …｜avg_cost …」，不印「舊 → 新」。

**四問：** ①根除（①⑧⑨ 把「請手動核對」「沒檢查」「沒有旗標」換成機械判定；②③④ 同一檔的兩種寫法、四捨五入的顯示當同一件事）。②程式。
③加的是比對與一個旗標；拿掉的是 ⑩ 的對照與 ① 的「一律請人看」。④最先壞掉的那一筆：**⑧ 一筆價格當天漂移超過兩倍的成交**（不會發生在
加碼既有列的常態；真的發生時拒收訊息印出反推值，改正匯率或換用 `--log-only` 都走得通）；**⑥ 一列手寫市值的持股**（2026-10-01 起 Sheet
沒有這種列——唯讀查證見下）。

**落地（2026-11-03）：** `identity/symbols.py`（新；`canonical_symbol` 搬家）；`fetchers/gsheets.py`（`display_matches`、`manual_formula_columns`、
`_is_our_row` 比顯示值、`canonical_symbol` 改成同一個函式物件）；`risk/hard_caps.py`（已持有加總、beta 判別兩邊正規化）、`risk/snapshot.py`
（別名表與查表正規化）、`portfolio/policy.py`（別名唯一性在正規化後成立）；`scripts/record_trade.py`（`--row-deleted`、`_manual_value_refusal`、
`_fx_sanity`、`_cell_outcome`／`_cash_outcome`／`_settle_partial_write`、`--log-only` 的顯示與負數檢查）。文件：OPERATIONS「記錄成交」、
ROADMAP（遺留小項移出、已交付索引一行；原文逐字封存 archive）。
**測試：** `tests/test_record_trade_leftovers.py` 36 條；`test_record_trade_open_position.py` 兩處隨改（既有列多讀一次公式＝`[False, True]`；
`--log-only` 不再印「僅此兩格」標題）。**變異 10 種各自轉紅：** 顯示值退回 1e-9（4）、已持有比原字串（1）、beta 判別比原字串（1）、snapshot 比原字串（1）、
不查手寫值（3）、「那一列還在」比不到（1）、寫入例外退回一律請人看（7）、不核對匯率（5）、同值當成沒寫（1）、policy 唯一性比原字串（1）。
**真資料（Sheet 唯讀）：** ⑥ 19 列持股手寫值 0、沒能確認 0；②③ 寫法與正規化不同的列 0、beta 判別原字串與正規化都 14 列；⑧ 8 列非 USD 的反推匯率
（市值 ÷ 股數 ÷ yfinance 最新收盤）對 yfinance 匯率比值 0.983–1.000；乾跑 0050.TW（TAISHIN）`--fx-to-base 0.0307` 照用、給倒數 32.6 → exit 2（高 983 倍），
trade_log 沒動。① 在真 Sheet 上不做故障注入（要真的寫），只靠替身的五種情形。

**R2（2026-11-03，乾淨 context 的唯讀 reviewer；全套 4613 passed；變異數字與本節一致）：NO_GO → AWAITING_HUMAN（不自動修）。**
- **B1** `--row-deleted` 配買進：那一列已刪＝已持有 0，`--log-only` 又不加成交額——5% 上限與槓桿 cap 恆判 pass，超過上限的買進不用 override
  就寫進 append-only 的 trade_log（探針：8% NAV 的買進 exit 0、`post_trade_weight=0.0`；TQQQ 同樣 pass）。主 agent 對照程式碼確認成立。
  修法方向：`--row-deleted` 只收賣出（文件寫的用途就是清倉後刪列），或買進一律 `unmeasurable`、要 `--override --reason`。
- **B2** ①「一格都沒寫進去」的訊息說照原命令重跑「會被比對擋下、不會重複寫」——錯：重跑會重讀 Sheet，伺服器稍後才套用時，套用後的值
  被當成寫入前，比對照過、股數與現金算兩次（探針：10 → 20 → 30）。建倉路徑早有 `ABSENT_RECHECK_SECONDS` 隔幾秒再讀，既有列沒做對稱面（L17）。
  修法方向：absent 時照建倉路徑再讀一次；訊息改成「重跑前先核對這幾格仍是寫入前的值」；OPERATIONS、本節、archive 三處同步。
- non-blocking：N1 `--row-deleted` 沒要求明給 `--broker`（預設 IB 寫進 append-only）；N2 `TPE:2330`／`TPE:00631L` 寫法改照 beta_policy 分類
  （宣稱改成「沒有放寬，只有依 policy 修正分類」；真 Sheet 0 列受影響）；N3 手寫值檢查沒防兩次讀取之間插列（該比對公式表那一列的 symbol／broker）；
  N4 手寫值檢查涵蓋所有公式欄、訊息只講市值；N5 建倉路徑的現金回讀在新舊顯示相同時改判「分不出」（較安全，沒有測試）；N6 `fetchers/build_dashboard.py`
  的槓桿別名沒正規化（只影響 Sheet 顯示）；N7 既有的洞：`--price`／`--shares` 沒驗 > 0（負價格讓硬擋 delta 為負而 pass）——另登記；N8 文件已註明的限制。

**修正（2026-11-03，使用者「D 照修法做＋負數價格一起擋」）：**
- **B1** `--row-deleted` 只收賣出（買進 exit 2、Sheet 0 讀）——文件寫的用途本來就是清倉後刪列。
- **B2** absent 時照建倉路徑隔 `ABSENT_RECHECK_SECONDS`（3 秒）再讀一次：第二次讀到新值＝照「已套用」記（`sheet_write_note` 註明第二次才讀到）；
  兩次都是舊值＝不記、exit 2，訊息改成「重跑 `--apply` 之前先看一眼 Sheet，確認這幾格還是寫入前的值」並逐格印寫入前的值，不再說重跑不會重複寫。
  OPERATIONS、本節 ①、archive 三處同步。
- **N1** `--row-deleted` 必須明給 `--broker`（原本默默預設 IB 寫進 append-only）。
- **N2** 只改措辭：②③ 讓 `TPE:2330`、`TPE:00631L` 這類寫法照 `beta_policy` 分類——**沒有放寬任何上限，只有依 policy 修正分類**
  （`TPE:00631L` 原本被當 alpha、槓桿 cap 沒比，修正後照比）；真 Sheet 0 列受影響。
- **N3** 手寫值檢查先比對值表與公式表那一列的 symbol／broker／bucket，對不上＝「沒能確認」照常進行（不新增一種失敗）。
- **N4** 拒收訊息照實說：手寫的欄在市值鏈上（`market_*`、`nav_base`）才說「市值與 NAV 會量錯」，否則說「不在市值鏈上，但照樣不知道該不該跟著變」。
- **N5** 補測試：建倉現金回讀讀到「5,000」（寫入前 5000、要寫 4999.7）＝分不出、不刪列、不記；逐字「5000」照舊刪列還原。
- **N7** `--shares`／`--price` 必須是大於 0 的有限數，讀 Sheet 前就擋（dry-run、`--apply`、`--log-only` 都 exit 2、Sheet 0 讀）。
- **N6 不改**：`fetchers/build_dashboard.py` 的別名只影響 Sheet 上的顯示，不進硬擋與 snapshot。**N8** 文件已註明的限制，照留。
- 對稱面（L17）：`--log-only` 定位不到那一列時的指路跟著 B1 走——賣出指去 `--row-deleted …--broker`，買進改指「先在 Sheet 加好那一列」；
  `--row-deleted` 的 `--help` 同步。
- **測試** `tests/test_record_trade_leftovers.py` 36 → 52 條。**變異第二輪 8 種各自轉紅：** row-deleted 收買進（1）、row-deleted 不要求券商（1）、
  absent 不再讀（2）、訊息退回承諾重跑安全（1）、只擋非有限數不擋 ≤ 0（4）、建倉現金分不出當舊值（1）、手寫值檢查不比對那一列（1）、
  買進也指去 row-deleted（1）。

**窄範圍覆核（2026-11-03，乾淨 context 的唯讀 sonnet；審 `d30cef3a..9e0194c7`）：GO**——九條宣稱全部成立，blocking 無；跑 239＋24 條測試、
探針 2 支（row-deleted 買進的 6 種旗標組合都在碰 Sheet 前 exit 2；重讀後「兩新一舊」照常往前補、「兩新一認不得」請人看）。
non-blocking 一條當下修（L17，B2 的對稱面）：建倉路徑現金格寫入逾時只讀一次就刪列——伺服器晚到套用會留下扣了現金卻沒有持股列。
`_cash_outcome` 讀到舊值時同樣隔 `ABSENT_RECHECK_SECONDS` 再讀；刪列訊息不再說「現金沒動」、改叫人重跑前先看一眼現金格。
測試 +1（52 → 53）、變異 2 種各自轉紅（不再讀、訊息退回「現金沒動」）；這條是同一判法的鏡像、只動失敗分支，由主 agent 對照程式碼覆核，
沒有再開覆核。順帶改掉 OPERATIONS 一句過時的「既有列寫到一半沒有還原、ROADMAP 待排程」。

## E 海外財報來源 ②20-F 年度封面股數——PLAN_PROPOSAL（AWAITING_HUMAN）

```
INTAKE
Zoom: Z2（engine_c 回填收 20-F 封面股數；三題「已定價①」對年報申報人的口徑；名冊多一個掛牌單位欄位）
Review: R1（A2 財務觀測可重建；名冊欄位是 contract——打開它要使用者選）
Case: ROADMAP「海外財報來源」剩 ②；邊緣候選裡 3 檔（ARBE、HIMX、POET）的「已定價①」恆為 inputs_incompatible
```

**現況（2026-11-03 唯讀；DB 與 SEC 實測，UA 用 repo 預設、不帶 email）：**
- 三檔都判 `foreign_annual`（最近 18 個月沒有 10-Q、有 20-F）；`fundamental_history` 有 `revenue_annual`（到 FY2025）、`cash`，
  **沒有封面股數**（`engine_c/history_backfill.py` 對非 domestic 刻意 `continue`）、**沒有季度營收**（20-F 只有年度）。
- SEC companyfacts 的 20-F 有年度 `dei:EntityCommonStockSharesOutstanding`：ARBE 8 筆、HIMX 16 筆、POET 9 筆（最新一筆封面日 2026-03）。
- 掛牌單位（20-F 封面與內文原文）：**ARBE**「Ordinary shares, par value NIS 0.000216 per share｜ARBE｜Nasdaq」＝普通股直接掛牌；
  **POET**「Common Shares, no par value｜POET｜Nasdaq Capital Market」＝普通股直接掛牌；**HIMX**「Ordinary Shares … * Not for trading, but only in
  connection with the listing … of American Depositary Shares」＋內文「ADSs … each of which represents two ordinary shares」＋「a change in our ADS ratio
  from one ADS representing one ordinary share to one ADS representing two ordinary shares」——**比率會隨時間變**。
- 封面股數的變化：POET 42.5M（2024-03）→ 76.5M（2025-04）→ 132.3M（2026-03）；ARBE 78.2M → 105.2M → 122.6M。

**只改程式做得到的部分：** 回填收 20-F 封面股數（拿掉那個 `continue`，股數照記原單位＝普通股）；「已定價①」對年報申報人用年度營收當
TTM（一年一點）。**做不到、要你選的兩件事：**

1. **HIMX 的掛牌單位比率住哪裡？**（名冊多一個欄位是 contract，L2）
   - **A（推薦）**：`config/company_identity.json` 的 listing 多一個 `ordinary_per_listed_unit`，**帶生效日**（一個列表：從哪天起一單位＝幾股普通股、
     出處＝哪份申報的哪一句）；沒登記＝照舊 inputs_incompatible（不猜）。HIMX 現在登記 2（出處 FY2025 20-F），1:1 的那一段要先查到改比率的日期才登記。
   - B：不支援 ADS，只做普通股直接掛牌的（ARBE、POET）；HIMX 照舊缺席。
2. **年度申報人的「已定價①」要不要算？**營收一年一點、股數一年一點——POET 一年內股數 76.5M → 132.3M，用上一份封面股數算市值，
   下一份 20-F 出來前最多低估約四成。
   - **A（推薦）**：算，但稽核區照印「年度點」口徑與股數的封面日、距今天數；股數超過 13 個月沒有新封面就整列缺席（不拿舊股數冒充當天）。
     首屏那一句仍要引用稽核區的數字（AGENTS「已定價」）。
   - B：不算，照舊缺席（20-F 發行人的「已定價①」恆為無法量）。

**驗收（照 ROADMAP 那一列）：** 邊緣檔「已定價①」從缺席變有值的檔數——1A＋2A＝3（ARBE、HIMX、POET）、1B＋2A＝2、2B＝0。
**不動：** 換匯（報表幣 ≠ 結算幣的 TSM、UMC、XPEV、NBIS 照舊缺席）、6-K 季度（不是機械來源）。
