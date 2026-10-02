# Phase 5 量測 — 結案報告（2026-10-02）

> plan：[`docs/plans/2026-10-02-001-feat-phase5-measurement-plan.md`](../plans/2026-10-02-001-feat-phase5-measurement-plan.md)（偏差全文 §0.6 #1–#31）；
> 基準：[`2026-10-02-phase5-baseline.md`](2026-10-02-phase5-baseline.md)（§1–§14 是 5.0 快照，§15–§20 是各 Step 的真實資料驗收）。
> 執行者全程 opus 5.5。本報告的數字都是 2026-10-02 17:0x–17:2x 台北量的；**現況數字會腐壞，引用前重跑各列的查證命令**。

## 0. Phase 5 做了什麼（18 個 Step commit，2026-10-02；起點 `d7d3c6e`）

| Step | commit | 內容 |
|---|---|---|
| 5.0 | 0fff701、94263ea | 基準快照；§5「改寫」規則修正（查法改版不是圖有變，§0.6 #2）；[666] 核准戳記位置更正 |
| 5.1 | ccdeb50、454f58a、5d2869a、4ed3026 | Phase 4 尾巴：③b 認得重寫（內容基準 `assertion_content_2026_10_02`）、走圖第 2 型降級、`classified_by` 加 `interactive:directed`、setup 1b 預熱清單補齊＋apply 入口蓋戳記前查 property token |
| 5.2 | 985383e | 追蹤表三條 lane（live／paper／history）各印三量與對主題等權組的超額；positions artifact `/2`、心跳段 4、APP |
| 5.3 | f70a548、f7db01f、323e4fa | `record_trade.py --backfill-before-receipts`；R2-a CONDITIONAL_GO → 三個條件＋兩個硬化 → 窄範圍覆核 GO |
| 5.4 | cdeb11f、0204d12 | 圖預測對錯表（`alpha/structure_reading/predictions.py`）、structure_readings artifact `/2`、讀圖頁、心跳一行 |
| 5.5 | bc3c771、f00f300 | 計分表第三個基準（主題等權組，排除本檔）、取價跳過 NaN 收盤、**APP 計分表頁（之前不存在）**、心跳段 5 一格 |
| 5.6 | 3530ba9、a9f51c9 | 候選狀態每日序列 `library/private/measurement/candidate_state_series.jsonl` |
| 5.7 | 575d814、31317d1 | 新管線 full chain 測試（三條鏈的下游斷言） |

## 1. 九項 completion gate（plan §12）

| # | gate | 結果 | 查證 |
|---|---|---|---|
| 1 | `pytest -q` 全綠；測試檔數差＝新增－退役；函式層級拿掉的每一個有去向 | ✅ **3303 passed, 1 skipped**（5.0：3214 passed, 1 skipped）；測試檔 **207 → 211**＝＋4（`test_measurement_lanes`、`test_reading_predictions`、`test_webapp_candidates_series`、`test_measurement_full_chain`），退役 0；函式 **2599 → 2673**，**拿掉 0**、新增 74（§3） | `python -m pytest -q`；`git grep -n -E "^\s*(async )?def test_" <rev> -- 'tests/*.py'`（5.0 名單 sha `666649f2…e9c3` 重建一致） |
| 2 | `python -m audit invariants` 綠 | ✅ **14 PASS／0 FAIL（共檢查 5387 筆）**；PointInTime 207/220、681/699；QueueLiveness 179 項；Expiry 127 個等待全部有到期 | `python -m audit invariants` |
| 3 | 無未解釋語意 diff | ✅ **心跳**與 5.0 的 `hb_base.md` 逐行對照（61 → 65 行），每一行都歸得到類：**Phase 5 程式預期**——段 4 多「追蹤表 history 22｜paper 4｜live 0（beta 事件 2 不進 lane）｜主題等權組 tc_35b0d5cd521656ea」、history 行多「對主題等權組超額」、「敘事前已漲（paper）3/4」、paper 行、live 行「還沒有列」、「圖預測」行；段 3 ③b 改成「新增或重寫」（5.1 #29）；段 5 「已知偏差 3→4 條」與「主題等權組基準：有」；「首日 8 項」＝新快照鍵；**白天的資料**——使用者整理 Sheet 補上 COHR（NAV 15→16 檔、候選已持有 1→2、非倍率候選 2→1）與盤中價格；**新私有檔**——備份「之後變動未備份」95→96（序列檔，在備份範圍內）；**既有程式的四捨五入**——段 2 分類層「0 天前→1 天前」在 17:31 之後才翻（`{days:.0f}`，最後改動 dcc8d2c、09-24，不是 Phase 5；結案 R2 補歸類）。**個股頁核心面板 0 檔變**：Phase 5 對個股頁組裝程式（`briefing/`、`webapp/materialize.py::materialize_view`／`build_overview`）0 個 hunk，敘事與讀圖 ledger 逐位元與 5.0 相同。**history lane**：錨點 digest `6ea352ed…7b93`＝5.0；同一份價格上 rows／三量逐位相同（baseline §16） | `python -m crons.heartbeat --out <檔>`（不帶 `--write-snapshot`）；`git diff d7d3c6e HEAD -- webapp/materialize.py` 的 hunk 標頭 |
| 4 | 無新 dual authority | ✅ 三量與等權只有 `scripts/outcome_if_settled_today.py` 的 `power_law_aggregate`／`equal_weight_aggregate`（三條 lane、APP 的 `positions_lanes`、心跳讀 artifact 共用）；主題等權組報酬只有 `alpha.theme_cohort.cohort_return`、「哪一組是基準」只有 `measurement_cohort`（追蹤表與計分表共用，5.5 把追蹤表那份搬過來）；預測終局只有 `alpha/structure_reading/predictions.py`；alpha 判別只走 `risk/hard_caps` 的 `is_beta_symbol`；symbol → 公司只走 `resolve_holding`（live lane 與回填共用） | 各模組 docstring 與 `tests/test_measurement_full_chain.py` |
| 5 | 無 silent drop | ✅ 空 lane 印「還沒有列」（live 今天就是）；未滿 12 個月印「還沒有一檔滿 12 個月」不印 0%；組缺價成員逐檔列（`theme_cohort.missing`）；預測表 `undated` 與 `upstream_unavailable` 分開、壞行節點列在 `unreadable_nodes`；被截掉的取價列在 `price_budget.truncated`；序列壞行原樣保留 | `tests/test_measurement_lanes.py`、`tests/test_reading_predictions.py`、`tests/test_account_scorecard.py`、`tests/test_webapp_candidates_series.py` |
| 6 | Point-in-time | ✅ 錨點價取錨點日或之前的可用收盤（`test_series_return_skips_nan_and_never_looks_ahead`）；預測表錯的種類只看 `published_at`，不拿 `retrieved_at`／`first_seen` 冒充；as-of 視角的預測段明確回 `point_in_time_unavailable`；`audit PointInTime` PASS | `python -m audit invariants --only PointInTime` |
| 7 | lifecycle 可達 | ✅ QueueLiveness、Expiry PASS；**驗收②的回查由心跳常駐計數器承載**（結案 R2 B1 → 使用者 2026-10-02 選 A，ROADMAP amendment A4；plan §0.6 #31；§9）：date watch 只能叫醒 pq2／假設／lead／敘事，回查是開發項而 AGENTS「開發項不走 pq2」——Phase 1 結案撞過同一個衝突、使用者選了心跳計數器。回查由每天自己出現的計數器承載：心跳段 4「圖預測…｜現行最早到期 2026-12-24」與快照鍵 `predictions.held`／`predictions.wrong`／`predictions.expired_unread`；兩份現行讀圖 12-24 到期當天進走圖第 4 型 | `python -m crons.heartbeat`；`crons/heartbeat.py::SNAPSHOT_KEYS` |
| 8 | executable protection | ✅ 回填旗標：七種拒收逐字斷言理由＋排程時區讀不到拒收＋名冊讀不到 fail closed＋一種放行（`tests/test_record_trade_receipt.py` §7）；lane 混算變異紅（5.2）；`supply_added` 接進預測表的變異紅（5.4）；apply 入口缺 token fail closed（`tests/test_apply_ra_admission.py`）；聚合檔既有四欄不變（`test_persist_keeps_the_four_fields_and_adds_lanes`）；請求路徑四種證明改走同一份 `STATE_ROUTES`，另有守門測試（5.5）；**殭屍 grep 未列 0／腐壞 0／不合法 0** | `python scripts/retired_mechanism_grep.py` |
| 9 | 驗收數的是 §11 的層 | ✅ §2 每個數字都是追蹤表、讀圖、等待 registry、計分表或機制存在與否；沒有任何一個是「幾檔通過某個 filter」 | — |

**另核對（plan §12）：**
- 舊店三個 `*.db`：sha256 與 5.0 **逐字相同** ✅。
- `library/trades/trade_log.jsonl`：sha256 `861d2008…b8d5`＝5.0 ✅——使用者還沒有回填，本 Phase 沒有任何程式寫入它（`record_trade.py` 的試跑全在假 Sheet＋暫存 trade_log 的測試與 R2-a 的 harness 裡）。
- `git diff d7d3c6e HEAD -- AGENTS.md` **為空** ✅。
- 四個 ledger：敘事 4 本、讀圖 4 本、主題等權組 1 本的 sha256＝5.0 ✅；Event Watch registry 157 筆，讀圖來源語意 watch 35（active 20／consumed 15、判觸及 0、判無關 6）、敘事來源 2＝5.0 ✅（本 Phase 0 筆寫入）。
- 聚合檔 `outcome_aggregate.json`／`.jsonl`：sha256 與 5.0 相同 ✅（既有四欄當然逐位不變）。
- Google Sheet：本 Phase 沒有任何程式寫入 ✅（R2-a 以記次替身驗過回填路徑 Sheet 寫入函式 0 呼叫）。
- `python -m webapp status` 列得出 **8 個 kind** ✅。

## 2. ROADMAP Phase 5 驗收與 §11 其他列

| 驗收 | 數的東西 | 結果 |
|---|---|---|
| ① 追蹤表印主題等權組超額 | paper／live 每列與 lane 聚合的 `excess_theme_cohort` 有值或有缺席 kind | ✅ paper **4／4 列有值**（positions artifact：平均 +4.07%；17:1x 以當下價格重算 +4.93%——只差價格時點）；live **0 列**＝「還沒有列」（不是 0%）；history 22／22（−2.42%）。主題等權組 `tc_35b0d5cd521656ea`（AI 光互連／CPO，09-30 定）15 檔、缺價 0；每列排除本檔 |
| ② 圖預測表有第一筆對／錯，每筆錯標明種類 | `predictions` 的 held＋reversed＋disproof_touched＋retracted | ⚪ **已交付、未生效**（照 §0.1 #4）：真實 15 筆＝對 0／錯 0／改寫 9／現行 2／非斷言 4，與 baseline §5.2 手算逐筆相同；機制由夾具證明（`tests/test_reading_predictions.py` 11 條、full chain 1 條：對 1／錯 2 種類各一）。現行最早到期 **2026-12-24**；回查由心跳常駐計數器承載（使用者 2026-10-02 選 A，amendment A4） |
| ③ 計分表印量測起始日與樣本數 | `measurement_start`／`named_calls`；新加的組格 `n` 與 `members_priced` | ✅ `x:aleabitoreddit`：量測期間 2026-06-29 → 10-01、具名點名 991 則／40 檔；對組超額 30 天 n=790、90 天 n=116（每檔最早一次 39／29）；`members_priced` 15／15 |
| 三條 lane | history 錨點與 5.0 相同；paper 錨點 09-29；live 0 列＋beta 事件不進 lane | ✅ history 22 列錨點 digest＝5.0；paper 4 列錨點全是第一份 v2（AXTI `ib_b6b3…`、COHR `ib_9a58…`、LITE `ib_78d7…`、SIVE.ST `ib_84e5…`，09-29）、三量每格有值或印「還沒有一檔滿 12 個月」；live 0 列、beta 事件 2 不進 lane、配對不到的賣出 0 |
| 候選狀態序列 | 行數＝結案日 − 5.6 交付日 ＋ 1 | ✅ 1 行（10-02 交付、10-02 結案；與 artifact 計數逐鍵相同，baseline §19） |
| Phase 4 尾巴 | ③b 兩格、第 2 型降級、`classified_by`、stash、入口缺 token | ✅ ③b「新增或重寫的帶 sub supported 0／0」、superseded 0；第 2 型降級夾具；`interactive:directed`；`git stash list` 空；入口缺 token fail closed（夾具） |
| 回填旗標 | 七種拒收一種放行；trade_log 指紋 | ✅ 測試 63 條綠（含 R2-a 條件修正後新增 3 條）；trade_log 指紋＝5.0（使用者尚未回填） |

## 3. 測試函式增刪（`d7d3c6e` → HEAD）

**拿掉 0 個。** 新增 74 個：`test_measurement_lanes` 19、`test_account_scorecard` 11、`test_reading_predictions` 11、`test_record_trade_receipt` 9、
`test_webapp_candidates_series` 7、`test_layer_stats` 5、`test_apply_ra_admission` 4、`test_measurement_full_chain` 3，
`test_engine_b_cli`、`test_engine_b_leads`、`test_graph_walk`、`test_robotics_ontology`、`test_webapp_request_path` 各 1。
既有 `tests/test_full_chain_acceptance.py` 0 行變動。

## 4. 執行中發現、實際做了什麼（偏差摘要；全文 plan §0.6）

- **量測口徑（5.0）**：§5 原規則會把查詢程式改版算成「預測被驗證」（5 筆假性的「對」）→ 加條件②，真實資料對 5→0（#2）；追蹤表的診斷跑法會蓋掉當日聚合值 → 5.2 根除（#1）；跨日只比錨點 digest（#4）；watch 的實際形狀（#5）。
- **計分表的 NaN（#3、#27）**：yfinance 對歐股回 NaN 收盤，NaN 混進中位數後**看起來正常的格也被靜默算錯**——重放 10-01 的形狀，7／10 格被污染（「30 天 vs QQQ」乾淨 −0.63%、污染 −34.27%；daily 那天早上的 artifact 印 −43.57%）。5.5 起取價跳過 NaN。
- **APP 計分表頁本來不存在（#23）**：心跳段 5 自 Phase 1 起寫「完整表在 APP 帳號計分表頁」，那一句一直不成立；5.5 補上唯讀頁，並讓請求路徑的四種證明改走同一份路由清單（補上一直沒被證明的 `/structure-readings`）。
- **資本路徑（5.3，#16–#17）**：R2-a 抓到 5% 測試被「市值合計≠NAV」頂替、OPERATIONS 的「乾跑」說法不成立 → 修正；名冊與排程時區讀不到改 fail closed。
- **單一答案（#24）**：「哪一組是基準」由追蹤表腳本搬到 `alpha.theme_cohort.measurement_cohort`，計分表共用。
- **序列（#28–#29）**：壞行原樣保留（序列拿不回來，L10）、原子改寫；試跑只寫在自己的 state 目錄裡。
- **預測表（#18–#22）**：撤回紀錄是標記、壞行節點整個不進表、as-of 明確拒絕、心跳多「現行最早到期」、年月精度跨讀圖日＝未定日。
- **結案回查（#31）**：不登記 date watch、改用心跳常駐計數器（gate 7）。

## 5. 下一步要決定的問題（plan §14 #1–#15；結案新增 #16–#21）

**要使用者決定：**

| # | 問題 |
|---|---|
| 1 | 「證據判準 brainstorm」——10 題與結案當天的數字在 §6 |
| 3 | #34 的既有 cw_dfb lead 與 3 則 `directed:sub_backfill` lead 的 `classified_by` 要不要改資料（lead registry 是 authority，走 pq2） |
| 5 | history lane 什麼時候退役（paper／live 樣本夠之前，它是唯一有歷史長度的序列） |
| 6 | 主題等權組 supersede 時序列的斷點怎麼呈現（本 Phase 只印 `cohort_id`） |
| 8 | 回填：FRA:2DG 的成交日與價由使用者給；成交時間若落在台北 2026-09-30 00:00–07:06 會被拒收（以日期為界是 §4 ② 的規格）；硬擋量的是**今天**的 Sheet |
| 9 | 預測表要不要納入 thesis memo 的反證觸及（今天 thesis 來源的語意 watch 16 筆） |
| 10 | 計分表的主題等權組基準對 09-30 之前的點名是回溯（已印在已知偏差）；要不要逐則記「點名時組是否已定義」 |
| 11 | 長駐 APP 跑舊程式（§7）；要不要讓 APP 自己偵測「程式比載入時新」並在首頁現形 |
| 12 | 白天互動跑追蹤表會取到歐股與台股**盤中尚未收盤**的當日 K 棒；要不要在取價端排除 |
| 14 | 本機 gitignored 的 `.claude/settings.local.json` 有 `Bash(python *)`：互動 session 不經提示就能跑會寫 trade_log（`--apply` 時還寫 Sheet）的 `record_trade.py`；要不要收窄 |
| 15 | 過去的計分表數字可能被 NaN 靜默算錯，之前存下的 artifact 沒有歷史版本——若 tier 升降曾引用過，要重看 |
| **16** | ✅ **已定（2026-10-02 使用者選 A：心跳常駐計數器；ROADMAP amendment A4）**——**（結案新增）驗收②的回查載體**：照 Phase 1 前例用心跳常駐計數器（本次做法），或改登記 date watch（要先鑄一個 manual pq2 當喚醒目標——與「開發項不走 pq2」衝突，所以需要你明說）。**結案 R2 B1：決定前 ROADMAP Phase 5 不標 ✅**；兩個選項與五欄草案在 §9 |
| **18** | **（結案 R2 N2）改寫規則①（同 digest＝改寫）不分 kind、也不限同日**：同一張圖、不同 kind 的後繼（例 volume→neither 純改判）會記成「改寫」而不是「錯」；定案 #3 的原句是「同 digest 的**同日**改寫」。今天 0 筆。要不要把①收窄成「同 kind 或同日」 |

**不需要使用者決定、下一個 plan 照列的：**
- #2 Phase 4 closeout §6 其餘資料口徑題照帶（#5–#10、#12–#16、#18–#19、#21、#23–#25、#28、#32）。
- #4 Phase 3 closeout §5 #14（Engine C 口徑）、#15（三題 as-of 視角）。
- #7 live lane 的賣出配對只做同 symbol＋broker 的 FIFO；分批與部分賣出的加權等有資料再做（L17）。
- #13 回填在既有 `--log-only` 語意下做不到兩種：全數出清的賣出、Sheet 已刪列的成交（COHR、FRA:2DG 都還持有，今天不受影響）。
- **#19（結案 R2 N3）** 預測表的讀圖日期（`created_on`）沿用讀圖契約的 UTC 日期，paper lane 用排程時區：台北 00:00–08:00 寫的讀圖，「當時已有／之後才出現」的分界會差一天。今天錯 0 筆。
- **#20（結案 R2 N1）** 心跳「N 天前」以 `{days:.0f}` 四捨五入：同一天 05:31 的紀錄過了 17:31 就印「1 天前」（既有程式，不在 Phase 5 範圍）。
- **#21（結案 R2 N4）** 殭屍 grep 以（檔，組）計 keep-list，已登記的檔裡**新增**的命中抓不到；R2 手掃 Phase 5 新增行 2 處（`crons/heartbeat.py` 讀既有鍵、`docs/OPERATIONS.md` 寫聚合檔的既有路徑），都在既有 keep 理由內。
- **#17（結案新增）** `engine_b.event_watch._local_timezone` 有 `lru_cache`：同一行程讀過一次之後設定檔變得讀不到也不會讓回填拒收（CLI 每次新行程，不受影響；R2-a 窄範圍覆核 non-blocking）。回填的殘餘風險另兩條：`why` 是記錄當下補寫的回憶（靠 `narrative=backfilled` 與 `recorded_at` 區分）、`executed_at` 由使用者聲明沒有交叉核對（硬擋仍在）。

## 6. 「證據判準 brainstorm」題目清單（Phase 4 closeout §6 的 10 題；結案當天量到的數字）

本 Phase 沒有寫圖（Neo4j 唯讀、[666] 未重試），下列數字是 2026-10-02 17:1x 重新量的，與 Phase 4 結案同日。

| # | 問題 | 2026-10-02 量到的 | 查證 |
|---|---|---|---|
| 1 | sub 的消費端要不要忽略 `sub_language_in_quote=false` 的 sub | ③a **102／113**（存量帶 sub 的引文不含可替代性語言）；③b 新增或重寫 0／0；字表 v1·narrow | `materialize --graph-walk` 的 `layer_stats` |
| 2 | 「外部印證」要不要求引文逐字具名被印證的供應商 | 外部印證但引文不具名供應商 **15** 條 | `layer_stats.ec_quote_does_not_name_supplier` |
| 3 | `counterparty_joint` 的 320 分支要不要改以 `publisher`／雙發行人宣告為準 | SourceDoc **220**：公司 155／發布者 49／**解析不到 16**；16 份裡**聯合公告 8**（GlobalFoundries＋Monolithic Power、IQE／Quintessent、IQE／Tower、AMD＋Anthropic、Sivers＋SemiNex、Tower／OpenLight、Marvell／Lumentum、Lumentum／Ayar Labs）、news 型別 12 | `query.origin_resolution.resolve_origin` 對每份 `origin_entity`（唯讀 Cypher） |
| 4 | 媒體報導靠 `origin_linkage=independent` 升級——要不要補 `same_origin` 機械偵測 | 宣告 `origin_linkage` 的 SourceDoc **0／220**；第一份宣告的 [666] RA 仍 partial（核准戳記 10-01 23:08Z 在）、未入圖 | Cypher `d.origin_linkage`；RA 檔 |
| 11 | `co:openlight` 與 `co:openlight_photonics` 同一家兩個 id | 兩個 id 都在名冊，`display_name` 同為「OpenLight Photonics Inc.」、`name_aliases` 同為「OpenLight」 | `config/company_identity.json` |
| 17 | 插槽讀圖 staleness 把同級標籤拆分算高等級 | 現行讀圖 4 份：SuperNova 插槽 current、ELS 插槽 current、inp 層 stale_low、cw 層 stale_low；**stale high 0**（SuperNova 在 4.8 重讀後已不是 high） | structure_readings artifact |
| 20 | 稀釋燈要不要分「對外募資」與「員工計畫」 | 73 檔：**黃 11**——NVDA、META、INTC、LRCX、MRVL 五檔的發行額占市值都 ≤0.15%；LITE 2.1%、COHR 3.2%、MP 8.8%、AXTI 11.2%、AAOI 14.8%、IREN 19.1%；灰 62（method_not_applicable 38、provider_missing 19、insufficient_evidence 5）；紅 0、綠 0 | 個股 artifact 的 `wipeout_dilution` |
| 27 | 結構表需求錨是「公司層單一最短錨」 | Lam **9 列全部錨在 `tech:dram_technology`**（含供先進封裝、3D NAND、foundry logic 的列）；結構表 224 條。Phase 4 closeout 記的是「8 列整批換錨」，兩數口徑的差未追——決定前逐列對 | structure_table artifact |
| 30 | 研究機構等自產類別「整家」升級，轉述也被抬成外部印證 | 逐份宣告 `origin_linkage` 的 SourceDoc 0／220（同 #4）；外部印證但引文不具名 15（同 #2） | 同上 |
| 31 | GSR 的登記類別 | Global Semi Research＝`industry_research`；另 4 個 Substack（Next Financial、damnang、primetrading、silicon_matter）＝`media` | `config/publishers.json` |

## 7. 使用者動作（非阻擋）

1. **[666] 重試**（5.1 已修 ③b，可以重試）：
   ```powershell
   python scripts/apply_ra_admission.py --pq2 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d
   python scripts/commit_pending_intake.py
   python -m engine_b.todo complete-ra 666 --digest 26924126cf54ca581410ddd47bbe41a647327a5590cbf22f40af0a9bbd7ee50d
   ```
2. **回填收據機制上線前的舊成交**（**沒有乾跑**：通過入口檢查就寫進 append-only 的 trade_log；先拿券商通知與 Sheet 那一列核對）：
   ```powershell
   python scripts/record_trade.py --symbol COHR --side buy --shares 10 --price 316.23 --currency USD --executed-at 2026-08-18T11:02:30-04:00 --broker IB --why "<一句：當時為什麼買>" --log-only --backfill-before-receipts "Sheet 已有這筆、trade_log 沒有（收據機制上線前的成交）"
   ```
   FRA:2DG 照同一個樣子，換成你的成交日與價，另加 `--currency EUR --fx-to-base <1 EUR = ? USD>`。
3. **重啟兩個長駐 APP**：PID 15956（127.0.0.1:8790，2026-09-10 23:13 起）與 PID 6992（127.0.0.1:8799，2026-10-01 21:19 起）都跑 Phase 5 之前的程式，讀不到 positions／structure_readings／account_scorecard 的 `/2`，也沒有計分表頁。
4. **§5「改寫」規則的收據**（5.0）：同 kind 的後繼若 schema 版本不同、或沒有帶來新來源，也算改寫——真實資料「對」5→0。你可以否決，否決就改回原規則。
5. **驗收②的回查**（§5 #16）：已定——使用者 2026-10-02 選 A（心跳常駐計數器），不登記 date watch、不鑄 pq2。
6. **本機權限**（§5 #14）：要不要把 `.claude/settings.local.json` 的 `Bash(python *)` 收窄。

## 8. 結案 R2（使用者已常規 opt-in）

**verdict：CONDITIONAL_GO，blocking 1。**（2026-10-02 17:20–17:45 台北，乾淨 context、全程唯讀；主樹 29 個關鍵檔的指紋前後相同；
只用 yfinance 取價與 Neo4j 唯讀查詢；沒有 materialize、stash、Sheet、真的 `record_trade.py`、停服務；暫存目錄已刪。）

八項全部 ✅，並獨立重現：
1. `pytest -q` 3303 passed, 1 skipped；`audit invariants` 14 PASS（與結案輸出逐字相同）；函式 2599 → 2673、拿掉 0、新增 74（5.0 名單 sha 重建一致）；
   既有測試刪的 8 行 assert 都有等價或更強的替代（請求路徑四種證明改走 `STATE_ROUTES`＋守門測試；`KNOWN_BIASES` 3→4 另加一條斷言）。
2. 追蹤表：`--no-benchmark` 跑前跑後兩個聚合檔 sha 相同；history 錨點 digest MATCH；paper 4 列錨點逐筆＝第一份 v2；三量自寫腳本重算與
   `power_law_aggregate` 逐值相同；對組超額手算 4 列（AXTI、SIVE.ST、META、IQE.L）誤差 1e-12 內、本檔都排除；離線拿掉 ENA.V 價格時逐檔列出、不進平均；
   在暫存副本模擬 daily 的 `_render(persist=True)`，非今天的 19 行逐位元相同。
3. 預測表：真實 15 筆依 §5 自判、與 artifact 逐筆相同；自造 25 筆夾具全如預期；供給側多一家（staleness `supply_added`）終局仍是現行；
   以 monkeypatch 讓 SourceDoc 日期讀不到時錯的種類是 `upstream_unavailable` 不是 `undated`，另三種降級也對。
4. 計分表：舊版程式以檔案路徑 import、同一份價格（快取替身）下既有 16 格與 991 筆 stamps 逐位相同；`price_budget` 42 → 49、增量 7＝新增成員；
   組格 n 790／116、每檔最早 39／29、`members_priced` 15／15；NaN 重放舊版污染 7／10、新版 10／10＝乾淨值。
5. 回填旗標：七種拒收 exit 2、理由逐字、Sheet 0 讀 0 寫、判斷 0 讀；`2026-09-29T16:30Z`（台北已是 09-30）正確拒收；放行一筆收據正確；5% 照擋；
   `--apply` 段 149 行 0 差異，`fetchers/gsheets.py`、`risk/hard_caps.py`、`portfolio/holdings.py`、`identity/execution.py` 0 行變動；trade_log sha＝5.0。
6. Phase 4 尾巴：對今天的圖重算 ③b 新增 0、重寫 0、存量 102/113；第 2 型降級（讀圖給 None、壞行副本）；stash 空；入口缺 token exit 2、只跑
   `CALL db.propertyKeys()`、不蓋戳記。
7. 心跳：61 → 65 行全部歸得到類（R2 多歸一行：段 2 分類層「0 天前→1 天前」，17:31 之後才翻，`crons/heartbeat.py` 的 `{days:.0f}` 四捨五入，
   最後改動 dcc8d2c、09-24，不是 Phase 5）；個股頁組裝程式 0 hunk；`SNAPSHOT_KEYS` 56 → 64，8 個新鍵都在 `collect_snapshot` 回傳值裡且有值。
8. 殭屍 grep 0／0／0、keep-list 本 Phase 沒動；舊店三檔、四個 ledger、`event_watches.json` sha＝5.0；AGENTS.md 0 行；Phase 5 非測試新增的行沒有 gsheets
   呼叫，寫 Sheet 的呼叫點全在 0 差異的 `--apply` 分支；候選狀態序列 1 行＝`candidates.json` 計數。

**Blocking B1：驗收②的回查載體還沒經使用者決定，ROADMAP 不能先標 ✅。** ROADMAP 第 99 行的驗收②寫「登記回查 date watch」；結案初版把 plan §11、§12 #7
改成心跳計數器、ROADMAP 沒改——等於改了 ROADMAP 的驗收定義（停止條件④），也偏離 §0.1 #4。Phase 1 前例的程序是「結案時向使用者提出，使用者選」。
修法：先取得使用者對 §5 #16 的選擇——(a) 選心跳計數器：同一個 commit 以五欄 amendment 改 ROADMAP 驗收②那句話（草案在 §9）；(b) 選 date watch：照 §7 #5
的三行指令登記，`python -m audit invariants --only Expiry` PASS。選定並完成之後不需要再覆核。
**處置（執行者）：** plan §11、§12 #7 先還原原文、§0.6 #31 改寫成「待使用者定」、ROADMAP 與 plans README 不動、`AWAITING_HUMAN`。
**B1 解除（2026-10-02）：** 使用者選 A（「A 繼續吧」）。同一個 commit：ROADMAP Phase 5 列以五欄 amendment A4 改寫驗收②那一句並標 ✅、plan §0.4 A4／§11／§12 #7／§0.6 #31／進度表與 frontmatter、`docs/plans/README.md` 本列 completed。依 B1 修法原文，選定並完成之後不需要再覆核。

**Non-blocking（都進 §5）：** N1 心跳「N 天前」四捨五入（既有程式）；N2 改寫規則①不分 kind、也不限同日（定案 #3 原句是「同 digest 的**同日**改寫」）；
N3 預測表的讀圖日期用 UTC、paper lane 用排程時區；N4 殭屍 grep 以（檔，組）計，已登記的檔裡新增的命中抓不到（手掃 Phase 5 新增行 2 處，都在既有 keep 理由內）。

## 9. 驗收②的回查載體（結案 R2 B1；§5 #16）——**使用者 2026-10-02 定案：A**

**定案：(a) 心跳常駐計數器。** 下面的五欄已原樣成為 plan §0.4 的 amendment A4，ROADMAP Phase 5 列同一個 commit 改寫。

兩份現行讀圖（inp 層、cw_dfb 層）2026-12-24 到期。驗收②「圖預測表有第一筆對／錯」今天是 0，回查要有一個會自己出現的載體。

- **(a) 心跳常駐計數器（Phase 1 前例；結案時暫用的就是這個）**——心跳段 4 每天印「圖預測：…｜現行最早到期 2026-12-24」；快照鍵
  `predictions.held`／`predictions.wrong`／`predictions.expired_unread` 第一次從 0 變非 0 的那天，Daily 的「較昨變動」會自己印出來；
  兩份讀圖 12-24 到期當天進走圖第 4 型「讀圖該重讀」（研究的佇列）。選它要改 ROADMAP 驗收②那句話，五欄草案如下。
- **(b) 登記 date watch**——照 §7 #5 的三行指令：先鑄一個 manual pq2 當喚醒目標，再登記 `kind=date`、until 2026-12-24 的 watch，pq2 設 pending 綁那筆 watch。
  它與 AGENTS「開發項不走 pq2」衝突，所以需要你明說這一次例外。

**(a) 的五欄 amendment 草案（A4｜驗收②的回查載體）：**

| 欄 | 內容 |
|---|---|
| 原 roadmap | ②「結案時若仍 0：夾具證明機制、closeout 寫「已交付、未生效」、登記回查 date watch——plan §11」 |
| 新觀察 | date watch 的喚醒目標只能是 pq2／假設／lead／敘事四選一；回查是 ROADMAP 驗收（開發項），AGENTS「開發項不走 pq2」；Phase 1 結案撞過同一個衝突，使用者 2026-09-25 選心跳計數器。心跳已經每天印「現行最早到期 2026-12-24」，`predictions.*` 快照鍵第一次變非 0 時 Daily 自己印出來 |
| proposed change | ② 的最後一句改成「…closeout 寫「已交付、未生效」，回查由心跳常駐計數器承載（段 4「圖預測」行的「現行最早到期」與 `predictions.held`／`predictions.wrong`／`predictions.expired_unread` 快照鍵）」；不登記 date watch |
| why | 等待住會自己出現的計數器（L14），不另建一個要鑄 pq2 才叫得醒的等待；與 Phase 1 的定案同一條規則 |
| impact | 只改 ROADMAP Phase 5 列與 plan §11、§12 #7 的文字；不寫任何 authority；Event Watch 0 筆 |

選定之後：ROADMAP Phase 5 標 ✅、`docs/plans/README.md` 本列改 completed、plan 進度表「結案」✅，commit、push——不需要再覆核（R2 B1 的修法原文）。

