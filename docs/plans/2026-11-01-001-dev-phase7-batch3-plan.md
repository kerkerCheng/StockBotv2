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
| D | 成交紀錄遺留 ①②③④⑥⑧⑨⑩ | `scripts/record_trade.py` 的八個已知小洞 | Z1／**R2**（資本路徑） | ◐ 11-03 實作完成；**R2 NO_GO（B1、B2）→ AWAITING_HUMAN**；程式在分支 `dev/batch3-d`、未合併（D 節在該分支） |
| E | 海外財報來源 ◐（剩 ②20-F） | 20-F 年度封面股數進 Engine C；ADS 比率要使用者選就停 | Z2／R1 | ◐ **PLAN_PROPOSAL → AWAITING_HUMAN**（兩個要你選：HIMX 的 ADS 比率住哪、年報申報人算不算已定價①） |

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

## D 成交紀錄遺留 ①②③④⑥⑧⑨⑩（指路）

實作、測試、真資料與 R2 回報都在分支 `dev/batch3-d`（commit `6f75730b`）的本檔「## D」節——R2 NO_GO 之後不自動修、不合併（AGENTS「協作與邊界」）。兩條 blocking：**B1** `--row-deleted` 配買進讓 5% 上限與槓桿 cap 恆判 pass；**B2**「一格都沒寫進去」的訊息宣稱重跑不會重複寫（錯：伺服器稍後套用時重跑算兩次）。修法方向與 non-blocking N1–N8 見該節末。

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
