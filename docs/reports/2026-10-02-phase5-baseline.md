---
date: 2026-10-02
topic: phase5-baseline
plan: docs/plans/2026-10-02-001-feat-phase5-measurement-plan.md
step: 5.0
---

# Phase 5 Step 5.0 — 基準快照

**這份報告只有一個用途：Phase 5 各 Step 與結案時逐項比對**（plan §1、§11、§12）。現況數字會腐壞，所以連同**產生它們的命令**一起存。
本檔每個數字數的都是**追蹤表、讀圖、敘事、等待 registry、計分表、機制存在與否**，沒有一個是「幾檔通過某個 filter」。

- 快照時間：2026-10-02 14:20–15:20（台北）
- HEAD：`d7d3c6e`；工作樹另有 [666] 的兩個未 commit 檔（`extractions/reuters_inp_export_controls_2026_06_11.json`、`library/raw/reuters_inp_export_controls_2026_06_11.txt`）——**不屬於本 Phase，不碰**（plan §0.5）
- Python：`.venv/Scripts/python.exe`（3.14.6）；Neo4j 以 `READ_ACCESS` session、舊 Decision Store 以 `?mode=ro`、Google Sheet 以 readonly scope、yfinance 唯讀網路
- 排程：`StockBotv2-Daily` 唯一；上次 2026-10-02 05:30:01（Last Result 0）、下次 2026-10-03 05:30、Status Ready（`schtasks /Query /TN StockBotv2-Daily /V /FO LIST`）
- 量測腳本與全文存 scratchpad（只讀，不寫任何 authority）；下表列指紋，後續 Step 以同一支腳本重跑比對

| scratchpad 檔 | 內容 | sha256 |
|---|---|---|
| `pytest_base.out` | §1 全測試輸出 | `2725d668…c002` |
| `test_functions_base.txt` | §1 `def test_` 名單（`檔::函式`、`LC_ALL=C sort`、LF） | `666649f2…e9c3` |
| `invariants_base.out` | §1 `python -m audit invariants` | `9d900b07…bf2d` |
| `outcome_base.md` | §2 追蹤表全文（不寫檔的包裝，見 §2） | `cc08f857…0f2c` |
| `hb_base.md` | §3 心跳全文 | `78a3fc50…0ad0` |
| `p5_readings_base.json`／`p5_chain_links.json` | §5 讀圖 15 筆欄位／每個 supersede 環節的快照比對 | `079eae1e…23e1`／`523082e0…2c94` |
| `p5_misc_base.json` | §2 artifact、§4、§7、§8、§9、§11、§12 | `e5993b10…4ba2` |
| `p5_scorecard_nan.json` | §8 計分表 NaN 的來源 | `b8a2132c…ea1b` |
| `p5_neo4j_keys.json` | §10 `db.propertyKeys()` | `4b779c5c…049d` |
| `zombie_grep_base.out`／`webapp_status_base.out` | §12 | `766349a4…65a0`／`54d384ea…b319` |

（`test_functions_base.txt` 全指紋 `666649f2158cce9e5f5d94fa12d6775f3c89dce5cda435f7c2a1aee2d8ade9c3`；`hb_base.md` 全指紋 `78a3fc50d969ffd25dd0c9669e36769c88ed59ff71ac5a5d78b86266ba680ad0`。）

## 1. 全測試基準與 invariant

`python -m pytest -q` → **3214 passed, 1 skipped, 2 warnings**（262s）；`ls tests/test_*.py | wc -l` → **207**。

測試函式名單：`git grep -n -E "^\s*(async )?def test_" HEAD -- 'tests/*.py'` → **2599 行**，正規化成 `檔::函式`（函式名允許非 ASCII——`tests/test_entity_aliases.py::test_放行必須配一個看得見的補償控制`）後 `LC_ALL=C sort` → 2599 個、無重複（LF 名單 sha256 `666649f2…e9c3`）。
結案比對以 `d7d3c6e` 為起點重跑同一條命令（名單可由 `git show d7d3c6e:tests/...` 重建，不依賴 scratchpad）。

`python -m audit invariants` → **14 PASS／FAIL 0**（共檢查 5387 筆）。與本 Phase 相關的兩行：

```text
PASS    PointInTime          SourceDoc published_at 207/220（94.1%）；EdgeAssertion 可定日 681/699（97.4%）；已回填 22 份且 basis 全部指得回去 [941 筆]
PASS    QueueSegments        pending_triage=0；fired_lead_requeue=0；fired_pq2_wake=0；semantic_pending_check=1；fired_reading_reread=0；narrative_rewrite=0；fired_hypothesis_check=0；approved_work_orders=0；triaged_go_leads=20；forward_view_backlog=69；graph_holes=7；pollable_watches=15；gated_gate_resolved=0；gated_no_pointer=0 [2019 筆]
```

## 2. 追蹤表（history lane 的基準）

**命令的偏差（plan §0.6 #1）：** plan 寫「`python scripts/outcome_if_settled_today.py --no-benchmark` 全文存檔」，但 CLI 的 `_render` 會呼叫 `_persist_aggregate`——
覆寫 `outcome_aggregate.json` 並把 `.jsonl` 裡**今天那一行**換掉；帶 `--no-benchmark` 時 `equal_weight_excess` 會被寫成 `null`（今天 05:30 daily 寫的是 `0.04027674185013119`）。
那違反不可越線 #3（既有四欄一字不動）。所以改用 scratchpad 的 `p5_outcome_nowrite.py`：以檔案路徑 import 同一支腳本、把 `_persist_aggregate` 換成只記次數的 no-op、呼叫同一個 `main()`——
輸出與 CLI 逐字相同；`_persist_aggregate` 被叫 1 次、全部攔下；跑前跑後兩個聚合檔的 sha256 相同（`.json` `dab6e21b…f758`、`.jsonl` `e83205e0…af53`）。
daily 步驟 `05_outcome` 的 argv 不帶 `--no-benchmark`（`crons/daily_task.py:148-149`），所以只有人工診斷跑法會蓋掉當日的超額——5.2 一併根除（plan §0.6 #1）。

**全文**（`outcome_base.md`，2026-10-02 14:5x 台北的價格）：22 列、已量測 22／22、另 25 個 cohort 的 Shadow 是 `unavailable`。

| 項 | 值 |
|---|---|
| 等權絕對（＝籃子總報酬） | +8.66% |
| 最大單檔 | AXTI +91.3%（期間高點 +124.4%）→ 等權貢獻 +4.15%；其餘 21 檔合計 +4.51% |
| 12m／24m 內達 2 倍 | 尚無一檔滿 12m／24m（分母 0，不是 0%） |
| 曾達 2 倍 | 1／22（現價仍達 0） |
| 量測起始／最長持有 | 2026-07-21／72 天 |
| 錨點體檢 | 來自進場判斷的錨點 1（`live_choices`）；跨度 2026-07-21～09-10（51 天）、8 個日曆週；錨點前 30 日中位 +0.8%／錨點後中位 +6.7%；入圖前已漲 8／22（COHR、AEVA、MP、LYC.AX、HIMX、6680.HK、6594.T、000660.KS） |
| live 段 | COHR 2026-08-18 10 股 @316.23 USD → 現價 319.19、live +0.9%（同檔 shadow 也是 +0.9%：COHR 的錨點已由 epoch anchor 改成成交日）；只有 paper 20 個 cohort |

**`positions` artifact**（`library/private/app/state/positions.json`，今早 daily ⑬ materialize）：

| 欄 | 值 |
|---|---|
| `schema_version`／`generated_at` | `stockbot-app/positions/1`／2026-10-01T23:14:55Z |
| `content_digest` | `sha256:debe917213d29dd18e60d239b3d84a0507ce8ddc74305d261af24ff5f96ddff9` |
| `rows` 22 列的 digest（`json.dumps(rows, sort_keys=True, ensure_ascii=False)`） | `2b004d2bdf07d5d3b71a172a26eb16e9a86ffbe8af5d04d381e1b2967330f106` |
| `power_law` digest（同算法） | `29b67c5eb9b4f163c26b70da66a70058ce673851adeed40455c98cf2eb6c455f` |
| **錨點 digest**（跨日穩定，見下） | `6ea352edfb9dab3a90844bba2b964e587ebf79f3db3b09b18cd71cdcaafe7b93` |
| `aggregate` | n 22、absolute 0.08660755054367225、excess(QQQ) 0.040549857359199366 |
| `power_law` | n 22、`measurement_start` 2026-07-21、`max_days_held` 72、`reached_2x_ever` 1、`reached_2x_now` 0、maturity 12m／24m 都是 matured 0、`share` null；top AXTI contribution 0.04151、rest 0.04510（rest_n 21） |
| `anchor_health` | paired 22、judgment_anchors 1、span 51 天、weeks 8、chasing 8 |
| `counters` | total_cohorts 33、shadow_anchored 33、shadow_measurable 21、eligible 28、legacy_eligible 1、orphan 10、outcomes 12、measured_outcomes 2、live_choices 1、live_fills 1 |
| `live` | rows 1（COHR）、paper_only 20 |

⚠ **「history 22 列與 5.0 逐位相同」只在同一份價格上成立。** 每列帶現價與報酬，三次各自抓價的結果在第 4 位小數就不同（05:3x daily 寫的 0.0866299…、07:14 materialize 的 0.0866076…、14:5x 包裝的 +8.66%）。
所以 5.2 的比對分兩層：**同一份價格**（注入同一個 loader，或同一次抓取）跑改前／改後兩份 `collect()`，history lane 的 `rows` 與 `power_law` digest 必須逐位相同；
**跨日**只比錨點——`sorted((ticker, company_id, anchor_date, anchor_price, anchor_currency))` 的 `json.dumps(..., ensure_ascii=False)` sha256 ＝ `6ea352ed…7b93`（22 列，含 LITE 兩列）。

`library/private/decision_lab/outcome_aggregate.jsonl`：**20 行**（2026-09-11 起，缺 09-17、09-23），每一行的 `equal_weight_excess` 都有值。最後一行四欄：

```json
{"date": "2026-10-02", "n": 22, "equal_weight_absolute": 0.08662994086861778, "equal_weight_excess": 0.04027674185013119, "benchmark": "QQQ"}
```

最後一行的鍵：`benchmark`、`bet_convergence`、`date`、`equal_weight_absolute`、`equal_weight_excess`、`n`、`power_law`（還沒有 `lanes`）。

## 3. 心跳

`python -m crons.heartbeat --out <scratchpad>\hb_base.md`（不帶 `--write-snapshot`）→ sha256 `78a3fc50…0ad0`（6443 bytes）。`SNAPSHOT_KEYS` **56 個**：

`watch.active`、`watch.fired`、`watch.expired`、`watch.consumed`、`semantic.active`、`semantic.pending_check`、`semantic.flagged`、`pq2.open`、`pq2.actionable`、`lead.pending`、`lead.triaged_go`、`lead.triaged_no_go`、`lead.researching`、`lead.action_prepared`、`lead.applied`、`lead.parked`、`reading.current`、`reading.needs_reread`、`walk.thin_layer_unread`、`walk.sole_supplier_self_reported`、`walk.supply_unfilled`、`walk.reading_stale`、`walk.lead_not_in_graph`、`walk.supplier_no_anchor`、`walk.no_supplier`、`walk.modelling_gap`、`walk.duplicate_node`、`thesis.active`、`thesis.watch`、`thesis.review_required`、`thesis.realized`、`thesis.revised`、`thesis.retired`、`disproof.watching`、`disproof.unreachable`、`disproof.touched_pending`、`disproof.expired_pending`、`disproof.unwatched`、`thesis.sidecar_mismatch`、`prescreen.no_text`、`prescreen.no_fetcher`、`health.red`、`invariants.fail`、`tier.probation`、`tier.measured`、`tier.trusted`、`candidate.open`、`candidate.missing`、`candidate.priced_wait`、`candidate.pass`、`candidate.held`、`candidate.not_multiple`、`candidate.edge_unmeasurable`、`candidate.legacy`、`candidate.precondition_failed`、`candidate.no_narrative`。

**段 4 逐行**（5.2／5.4 只准在預期處變）：

```text
- alpha（瓶頸研究衛星）占已投入非現金 1.46%｜**只觀測不設目標**（D1）
- NAV：大盤 57.4%、CORE 22.4%、槓桿 7.7%、CASH 6.6%、觀察 5.9%｜最大單筆 LON:VWRA 30.1%（15 檔；只呈現，完整表在 APP positions）｜「槓桿」格＝投入槓桿 ETF 的資金占 NAV，不是乘上倍數後的曝險
- 追蹤表 22 檔｜等權絕對 8.66%｜對 QQQ 超額 4.05%｜正式結算過 2 筆
- 入圖前已漲（chasing）8/22 檔
- 歸零旗標 73 檔 × 4 盞：紅 20｜黃 44｜綠 89｜**灰（沒量到）139**（insufficient_evidence 5、method_not_applicable 38、not_yet_recorded 68、provider_missing 19、upstream_unavailable 9）——⚠ 灰不是綠；有紅燈 13 檔：002472.SZ、4971.TWO、AAOI、COHR、CRWV、ENA.V、HIMX、IQE.L…
- 結構表 224 條邊分佈在 9 個需求錨（前三：tech:ai_switch 102、tech:optical_scale_up 39、tech:essential_chips_mature_node 29）——**N 檔不等於 N 個獨立機會**
- power-law：籃子總報酬 8.66%｜最大單檔 AXTI 4.15%／其餘 21 檔 4.51%｜曾達 2 倍 1/22（現價仍達 0）｜**還沒有一檔滿 12 個月**（最長持有 72 天）
- 賭注收斂：**還沒有任何一檔寫下賭注**（掃過 22 檔）——這不是 0%，是還沒有分子也沒有分母
- **alpha 全歸零淨值少 1.37%**（alpha 佔 NAV 的比例本身；純呈現、零門檻，尺寸仍由使用者決定）
```

**段 5 逐行**（5.5 只准加「籃子基準：有／無」一格）：

```text
- tier 分佈：measured 0／probation 1／trusted 0｜1 個帳號｜計分表 as-of 2026-10-01｜較昨：沒有變化
- 完整表（每個帳號的量測窗、點名數、超額報酬、追源成功率）在 APP 帳號計分表頁｜已知偏差 3 條（也在 APP）
```

段 2 的候選行：「候選：可開 0｜缺 X 0｜等回落 1（最老 3 天）｜不要 0｜已持有 1｜非倍率候選 2｜邊緣無法量 0｜舊版 0｜前提失效 0｜無敘事 69」。段 3 的層行：「①獨家且全自報 73…③b 新增帶 sub supported 0／0（Phase 內還沒有新增帶 sub 的）」。

## 4. 敘事（paper lane 的錨點）

`library/private/alpha/briefs/*.jsonl`，4 檔、16 筆紀錄、撤回 0。**錨點＝每檔最早一筆未撤回的 `investor-brief/v2`**（不是 `select_brief` 的現行那筆）；`created_at` 是 UTC，日期以台北換算：

| 檔 | 第一份 v2 `brief_id` | `created_at`（UTC） | 錨點日（台北） | 當時 `candidate_state.state` | 現行（最新）`brief_id`／state | v2 筆數 | v1 最早 |
|---|---|---|---|---|---|---|---|
| AXTI（`co:axt`） | `ib_b6b3b1b8ebaaa438` | 2026-09-29T05:46:20 | 2026-09-29 | `priced_wait` | `ib_3100d4c6f394b679`／`priced_wait` | 2 | 2026-09-17T10:18:25 |
| COHR（`co:coherent`） | `ib_9a581a19a43d2e41` | 2026-09-29T05:46:24 | 2026-09-29 | `pass` | `ib_1ddf59d7c3cf4fe4`／`pass` | 2 | **2026-09-15T04:40:45**（v1 最早） |
| LITE（`co:lumentum`） | `ib_78d7b285e8b517ea` | 2026-09-29T05:46:27 | 2026-09-29 | `pass` | `ib_bc97e6ccde70f264`／`pass` | 2 | 2026-09-18T17:35:00（台北 09-19） |
| SIVE.ST（`co:sivers_semiconductors`） | `ib_84e5efaf6360f042` | 2026-09-29T05:46:31 | 2026-09-29 | `missing` | `ib_457146d29ad50ef0`（10-01 換版）／`missing` | 3 | 沒有 v1 |

⚠ 四檔第一份 v2 都是 09-29 台北 13:46 那一批（兩分鐘後又各換一版）；SIVE.ST 的錨點是 `ib_84e5…`（09-29），**不是** 10-01 換版那筆。
四本 ledger 指紋：AXTI `ac917627…d830`、COHR `85b04f3c…7bcf`、LITE `93653d6e…a5e5`、SIVE.ST `b0936b04…68d1`（全文在 `p5_misc_base.json` 的 `ledger_sha256`）。

## 5. 讀圖與預測表手算（5.4 的對照答案）

`library/private/alpha/structure_readings/*.jsonl`，**15 筆**（4 本 ledger），撤回 0、supersede 鏈分岔 0（每筆最多一個後繼）。逐筆欄位在 `p5_readings_base.json`；每個 supersede 環節「快照變了什麼」用 staleness 的既有分級（`_angle_changes`，唯一 owner）比對 r 與 s 兩份存下來的 `angles`，並列出兩筆之間 `query/structure.py` 的 commit（`p5_chain_links.py`）。

### 5.1 撞到的事：§5 原規則把「查詢程式改版」算成「預測被驗證」

plan §0.2 寫「supersede 鏈裡只有 SuperNova 09-25→10-01 是圖變了之後的重讀，其餘是同日或隔日 schema 升版（digest 相同）」——**實測不成立**：
inp 與 cw 兩條鏈有 **5 個同 kind 環節的 `result_digest` 不同**。逐環比對後，這 5 個環節的快照差異都對得上查詢程式的 commit 或 schema 升版，**沒有一個是供給側多一家或少一家**：

| 環節（r → s） | 時間（台北） | 快照變了什麼（staleness 分級） | 兩筆之間的 `query/structure.py` commit |
|---|---|---|---|
| inp `sr_88340b81…` → `sr_6ad5c884…`（v1→v1） | 09-17 19:15 → 09-18 13:32 | 需求側多一條 `co:iqe→mat:inp_substrate`（high） | `2140eca` constrained_by 進需求走訪（09-18 09:10） |
| inp `sr_6ad5c884…` → `sr_bc1ccb56…`（v1→v1） | 09-18 13:32 → 23:02 | 需求側一增一減（`tech:ai_compute_buildout`＋、`tech:inp_eml`－）＋證據標籤 19 處（low） | `7e6a3bd` 逐字入圖、`53b059f` [608][609][610] 資料歸位＋enables 程式歸位 |
| inp `sr_ad503ae8…` → `sr_bac985ba…`（**v2→v3**） | 09-24 17:22 → 09-25 14:18 | 反向路徑少一條 `co:iqe→mat:inp_substrate`（normal） | `73d8c53` 反向路徑只收 competes_with（＋v3 契約三個 commit） |
| cw `sr_a6762186…` → `sr_a181641d…`（v1→v1） | 09-17 16:34 → 09-18 23:05 | 下一層多兩條（`mat:inp_substrate`、`tech:external_laser_source`）＋證據標籤 14 處 | `2140eca`、`7e6a3bd`、`53b059f` |
| cw `sr_a181641d…` → `sr_caac0aca…`（v1→v1） | 09-18 23:05 → 23:24（19 分鐘） | 下一層少 `tech:external_laser_source→tech:cw_dfb_laser`（normal） | `1656f15` 證據欄從未被賦值的修正（23:09） |

照 §5 原規則（`rewritten`＝同 digest 且未到期；否則同 kind＝`held`），這 5 筆會被判 **`held`（對）**——那正是 plan §5 的 L11-6 ④ 點名的失敗形狀「改寫被算成驗證」，
而且 ROADMAP ②（「圖預測表有第一筆對／錯」）會在 5.4 上線當天被這 5 筆假性滿足，與 §0.1 #4 預期的「結案仍是 0 → 已交付、未生效＋回查 watch」相反。
使用者定案 #3 的原句是「同 kind 取代且**圖有變**或已到期＝對」——查詢程式改版不是圖有變。`result_digest` 一個表示承載「圖變了」與「查法變了」兩種語意（L12），所以修的是 §5 的機械代理，不是定案本身。

**§5 的修正（plan §0.6 #2；5.4 照這版寫）：** `rewritten` 一列改成——有後繼 s、r 在 `s.created_on` 當天未到期，且下列任一：
①`s.result_digest == r.result_digest`（原規則）；②`s.kind == r.kind`，而 `s.record_version != r.record_version`（schema 升版，plan 原文對 rewritten 的說明就是「schema 升版、補引文」）
或 s 沒有帶來 r 沒引用過的來源（`{c.source_id for c in s.citations} − {… for c in r.citations}` 為空；v1／v2 沒有引用欄，兩邊皆空）。
**不同 kind 的後繼不套②**——定案 #3 的「錯」不要求圖有變，只排除同 digest 的改寫；r 已到期時一律不是改寫（定案「已到期＝對」照舊）。
`held`／`reversed` 兩列文字不變（「不是 rewritten」的範圍跟著收窄）。

### 5.2 逐筆手算

| 節點／單位 | reading_id | kind | 版 | `created_at`（UTC） | `expires` | 後繼 | digest r→s | 原規則 | **修正後** | 依據 |
|---|---|---|---|---|---|---|---|---|---|---|
| `mat:inp_substrate`／layer | `sr_d6760bfe5d6e9164` | undecided | v1 | 09-17 08:35 | 12-16 | `sr_81832cb3…` | `bff24bdf`→`e6c668f8` | non_assertion | **non_assertion** | kind 非斷言 |
| | `sr_81832cb37d87ab1d` | volume | v1 | 09-17 09:20 | 12-16 | `sr_88340b81…` | 相同 | rewritten | **rewritten** | ① 同 digest、未到期 |
| | `sr_88340b81269fa1c2` | volume | v1 | 09-17 11:15 | 12-16 | `sr_6ad5c884…` | `e6c668f8`→`8cad4fd6` | held | **rewritten** | ② 同 kind、新來源 ∅（v1 無引用） |
| | `sr_6ad5c884eb7bc3fb` | volume | v1 | 09-18 05:32 | 12-17 | `sr_bc1ccb56…` | `8cad4fd6`→`142b3ea0` | held | **rewritten** | ② 同上 |
| | `sr_bc1ccb568c8886c0` | volume | v1 | 09-18 15:02 | 12-17 | `sr_ad503ae8…` | 相同 | rewritten | **rewritten** | ① |
| | `sr_ad503ae880ceb398` | volume | v2 | 09-24 09:22 | 12-17 | `sr_bac985ba…` | `142b3ea0`→`01893fb9` | held | **rewritten** | ② v2→v3 schema 升版 |
| | `sr_bac985bacbea64b7` | volume | v3 | 09-25 06:18 | **12-24** | — | — | open | **open** | 無後繼、反證 watch 7 筆無判觸及、未到期 |
| `tech:cw_dfb_laser`／layer | `sr_a6762186c7e8eb23` | volume | v1 | 09-17 08:34 | 10-17 | `sr_a181641d…` | `b74e731d`→`c21169d0` | held | **rewritten** | ② 同 kind、新來源 ∅ |
| | `sr_a181641ddb99c69c` | volume | v1 | 09-18 15:05 | 10-18 | `sr_caac0aca…` | `c21169d0`→`88f8c81e` | held | **rewritten** | ② 同上 |
| | `sr_caac0acae9a1c1cf` | volume | v1 | 09-18 15:24 | 10-18 | `sr_d0767997…` | 相同 | rewritten | **rewritten** | ① |
| | `sr_d07679979a8e4202` | volume | v2 | 09-24 09:22 | 10-18 | `sr_d49b81b6…` | 相同 | rewritten | **rewritten** | ①（也是 v2→v3） |
| | `sr_d49b81b6465e1181` | volume | v3 | 09-25 06:24 | **12-24** | — | — | open | **open** | 無後繼、反證 watch 6 筆無判觸及、未到期 |
| `prod:supernova`／socket | `sr_268d2fd79db629ff` | undecided | v3 | 09-25 06:19 | 12-24 | `sr_d85d6729…` | `a4b10c34`→`2fdceb23` | non_assertion | **non_assertion** | kind 非斷言（digest 不同也不是 held） |
| | `sr_d85d672998445c50` | undecided | v3 | 10-01 15:41 | 12-31 | — | — | non_assertion | **non_assertion** | |
| `prod:els_8ch_module`／socket | `sr_35ca0ce58617d5f6` | undecided | v3 | 09-25 06:21 | 12-24 | — | — | non_assertion | **non_assertion** | |

| 計數 | held | reversed | disproof_touched | retracted | rewritten | open | expired_unread | non_assertion | 合計 |
|---|---|---|---|---|---|---|---|---|---|
| 原規則 | **5** | 0 | 0 | 0 | 4 | 2 | 0 | 4 | 15 |
| **修正後（5.4 的對照答案）** | **0** | 0 | 0 | 0 | **9** | 2 | 0 | 4 | 15 |

`earliest_open_expiry` ＝ **2026-12-24**（兩筆 open 都是）——結案登記的回查 date watch 用這一天。

## 6. 反證 watch（5.4 的輸入）

`library/leads/event_watches.json`：157 筆（`related_entity_signal` 59、`semantic_condition` 53、`entity_filing_signal` 32、`fact_verification` 9、`date` 4）。
語意 watch（**`kind == "semantic_condition"`**，不是 `semantic`）53 筆：active 36／consumed 16／fired 1；`source_ref` 前綴 `reading:` 35、`thesis:` 16、`brief:` 2。

**來源 `reading:` 的 35 筆：active 20、consumed 15（全部 `closed.note="superseded by sr_…"`，沒有 `closed.kind`）。** 判觸及（yes）0 筆、判無關（no）6 筆（全部是同一則 lead `lead_20ce4e7d…`——Sivers 臨時股東會召集公告）、`semantic_flag` 0 筆：

| 讀圖 | 狀態 | 判無關 |
|---|---|---|
| `sr_ad503ae8…`（inp v2，已被取代） | consumed 6 | 0 |
| `sr_bac985ba…`（inp v3，現行） | active 7 | 0 |
| `sr_d0767997…`（cw v2，已被取代） | consumed 5 | 0 |
| `sr_d49b81b6…`（cw v3，現行） | active 6 | 2 |
| `sr_268d2fd7…`（SuperNova 09-25，已被取代） | consumed 4 | 2 |
| `sr_d85d6729…`（SuperNova 10-01，現行） | active 4 | 0 |
| `sr_35ca0ce5…`（ELS，現行） | active 3 | 2 |

**5.4 要照的實際形狀（plan §5 的寫法要跟著改，§0.6 #5）：**

- `source_ref` 的格式是 **`reading:<reading_id>#<第幾條>`**（例 `reading:sr_ad503ae880ceb398#1`），不是 `reading:<reading_id>`——比對要去掉 `#n`。
- 「觸及」寫在**單數** `judgment`（`touches == "yes"`，字串）：`event_watch.judge(touches=True)` 與 `record_touched`（pq2 `watch_decision` 的 go）都寫這一格並把 watch 轉 consumed；
  判無關（`touches == "no"`）append 到**複數** `judgments` 並 reactivate。今天所有語意 watch 都沒有單數 `judgment`。
- 判觸及指到文件的欄位：`judge` 那條路的 `judgment.lead_id`（＝`woken_by.lead_id`）→ `library/leads/pending_leads.json` 那則 lead 的 **`published_at`**；
  `record_touched` 那條路的 `lead_id` 是 `null`（只有 `evidence`＝pq2 收據字串與 `quote`）→ 種類只能是 `undated`。`semantic_flag` 的結構是 `{lead_id, at, verdict, quote, session_id}`。
- lead registry 今天 1193 則：`published_at` 空 54 則（用到時→`undated`，不拿 `first_seen` 冒充）；與 `first_seen` 同日 380 則（x 209、edgar 145——日更 harvest 的正常情形，不是冒充）。
- SourceDoc（反例文件走 citations 那條路）：圖上 220 份、`published_at` 空 13 份（與 PointInTime 207／220 一致）。

## 7. 主題等權組

`alpha.providers.theme_cohorts.current_cohorts()` 回 **(組清單, 壞行清單)** 兩項——今天 1 組、壞行 0：

- `cohort_id` `tc_35b0d5cd521656ea`｜題材「AI 光互連／CPO」｜`decided_on` 2026-09-30｜`pq2_ref` 656｜`supersedes_id` null｜ledger `AI_____CPO.jsonl` 1 行、sha256 `25721a7a…7503`
- 成員 **15**，逐檔試 yfinance 近 20 日收盤（`dropna` 後）：**全部取得到、缺價 0**。

| ticker | company_id | 報價單位 | 20 日內根數 | 最後一根 |
|---|---|---|---|---|
| AXTI | `co:axt` | USD | 14 | 2026-10-01 |
| IQE.L | `co:iqe` | **GBp** | 13 | 2026-09-30 |
| 4971.TWO | `co:intelliepi` | TWD | 13 | 2026-10-02 |
| 2455.TW | `co:vpec` | TWD | 13 | 2026-10-02 |
| 3081.TWO | `co:landmark_optoelectronics` | TWD | 13 | 2026-10-02 |
| 4979.TWO | `co:luxnet` | TWD | 13 | 2026-10-02 |
| SIVE.ST | `co:sivers_semiconductors` | SEK | 13 | 2026-09-30 |
| COHR | `co:coherent` | USD | 14 | 2026-10-01 |
| LITE | `co:lumentum` | USD | 14 | 2026-10-01 |
| 300308.SZ | `co:zhongji_innolight` | CNY | 12 | 2026-09-30（十一長假休市） |
| AAOI | `co:applied_optoelectronics` | USD | 14 | 2026-10-01 |
| FN | `co:fabrinet` | USD | 14 | 2026-10-01 |
| POET | `co:poet_technologies` | USD | 14 | 2026-10-01 |
| ENA.V | `co:enablence_technologies` | CAD | 14 | 2026-10-01 |
| 3363.TWO | `co:foci` | TWD | 13 | 2026-10-02 |

⚠ IQE.L、SIVE.ST 的最後一根是 09-30，因為 **10-01 那根收盤是 NaN**（見 §8）——不 `dropna` 的取價會把它當成最新收盤。成員裡有本 Phase paper lane 的 AXTI、COHR、LITE、SIVE.ST 四檔（籃子超額要排除本檔）。

## 8. 計分表

`library/private/app/state/account_scorecard.json`（今早 materialize，`generated_at` 2026-10-01T23:20:49Z，`content_digest` `sha256:1306f20f…43bf`）：

- `price_budget`：cap 200、requested 42、fetched 42、truncated []；基準 QQQ／SOXX；horizons 30／90 天；tier：probation 1、measured 0、trusted 0
- `point_in_time.mode` ＝ `current`；`known_biases` 3 條（倖存者、後見之明、單邊上漲）
- 帳號 1 個：`source_id` `aleabitoreddit`（status active、tier probation since 2026-09-17）、`measurement_start` 2026-06-29、`measurement_end` 2026-10-01、`named_calls` 991、`distinct_symbols` 40

| 五欄 | 值（全部點名） | n | 首次點名版（每 symbol 一則） |
|---|---|---|---|
| 點名後 30 天超額 vs QQQ／SOXX | −0.4357／−0.2772 | 770 | −0.0716／+0.0280（n 39） |
| 點名後 90 天超額 vs QQQ／SOXX | −0.1532／**NaN** | 110 | −0.1565／−0.0310（n 28） |
| 點名前 30 天漲幅 | +0.0754 | 991 | — |
| 追源成功率 | 0.3885 | 471 | — |
| 假設命中率 | `capability_absent`（值 null，不填 0） | 0 | — |
| no-go 率 | 0.6450 | 524 | — |

**撞到的既有缺陷：「點名後 90 天超額 vs SOXX」這格是 NaN**——既不是數字、也不是缺席。根因（`p5_scorecard_nan.py` 包一層 loader 重建，不寫檔）：
`engine_b/account_scorecard.py::_yfinance_closes` 沒有濾 NaN 收盤，而 yfinance 對 5 檔歐洲標的在 **2026-10-01** 回了一根 NaN 收盤（IQE.L、SHA0.DE、SIVE.ST、SOI.PA、XFAB.PA；SOXX、QQQ 本身沒有）。
終點落在那一天的點名得到 NaN 報酬，NaN 混進 `statistics.median` 時排序結果不確定——這一格印 NaN，**同一批值算出的 QQQ 那格也可能被靜默算錯**。
追蹤表的 `_provider_series` 有 `.dropna()`＋`close == close` 兩道，所以 §2 沒被污染。處置排進 5.5（plan §0.6 #3）：取價濾 NaN；5.5 的「五欄既有值逐位不變」改成「同一份價格上，除了被 NaN 污染的格以外逐位不變，污染的格逐格列出」。
5.2 的主題等權組報酬函式（追蹤表與計分表共用）同樣必須濾 NaN。

## 9. trade_log、舊店、Sheet

- `library/trades/trade_log.jsonl`：**2 行**、sha256 `861d2008de8cdaa80c885b4e06da11ee0a2bf188526836dddcc1701a6bc7b8d5`——QQQ 10 股 @687.79 USD（IB，2026-07-31）、VWRA 170 股 @194.16 USD（FUBON，2026-09-01），**兩筆都是 beta、都沒有 `research_receipt`**
- 舊 Decision Store（A5，只准讀；`?mode=ro`）：

```text
backup_pre_v8_20260818T021452.db sha256=e887b3d458621e4cd7bb66913690d47d263d7188f9bbc1bacb4bc16ec57de350 live_choices=0 bytes=4804608
backup_pre_v9_20260902T032020Z.db sha256=af3dc690ce836b6026d86946c388d19f1500139287469f0f9fbe8711c4819d39 live_choices=1 bytes=11038720
decision_lab.db sha256=e99d1c79fd22dbe1099f30c4e06f2d1188f26a8cbfa987a27cd8842530951810 live_choices=1 bytes=16166912
```

  與 Phase 0–4 基準三檔逐字相同。`live_execution_reports` 唯一一筆：`ib-cohr-2026-08-18-10sh` 10 股 @316.23 USD、2026-08-18T15:02:30Z。
- **Google Sheet（唯讀 `python fetchers/gsheets.py`，24 列）**：alpha 兩列都在「觀察」格、都在 IB——FRA:2DG 2000 股 @6.84 EUR、**COHR 10 股 @316.23 USD**。
  ⚠ plan §0.2 寫「COHR 列不在 Sheet 上」——使用者已在 plan 之後整理 Sheet 補上了（`6399011`、`d7d3c6e` 的 Sheet 整理）。兩檔仍然**都沒有 trade_log 事件**。

## 10. Phase 4 尾巴

- **pq2 [666]**：`ra_admission`、`ref_id` `ra_b98730bb2721d909a9cf3f3746fec135`、池中未結案（`resolution` null）；RA 紀錄 `state=partial`、`action_digest` `26924126…e50d`（與 plan §0.5 的重試指令相同）、
  **核准戳記在 `execution.approval`**＝`{pq2_n: 666, digest: 26924126…e50d, at: 2026-10-01T23:08:31Z}`（初版誤讀頂層欄位寫成「沒有戳記」，2026-10-02 更正）——所以重試走 apply 入口的「同編號同 digest 重試」路徑，四道檢查會過；
  `execution.last_error`＝`document_not_complete`：以 `cloud_routine`（routine_writer）身分寫 Neo4j 時 `Creating new property name … not allowed`、`graph_mutated=false`。`expires_at` 2026-10-31T15:48:56Z。標題「Reuters 2026-06-11 InP 出口管制報導宣告 origin_linkage=independent」。心跳「pq2 球在你手上 1」＝[666]。
- **Neo4j property token（唯讀 `CALL db.propertyKeys()`）**：56 個；**`origin_linkage` 已存在**；stash 版 setup 1b 預熱清單 37 個屬性名**全部已有 token、缺 0**。
  ⚠ Phase 4 結案時 [666] 正是缺 `origin_linkage` 被 Forbidden 擋下——現在 token 已在，[666] 重試不會再撞同一道（token 怎麼建的不在本報告的量測範圍；本 session 沒有任何寫入）。
- **`stash@{0}`**「等使用者決定：neo4j_setup 1b 預熱補 loader 全部屬性名＋對稱測試（pq2 [666] Forbidden origin_linkage）」：`schema/neo4j_setup.cypher` +41／−1（預熱 sentinel 由 2 個屬性名擴成 37 個，附註解）、`tests/test_robotics_ontology.py` +20（`test_neo4j_setup_prewarms_every_property_the_loader_sets`：loader 所有 Cypher 常數 SET 的屬性名 ⊆ 預熱清單，`id` 除外；先斷言 `origin_linkage` 在解析結果裡，空集合不得冒充通過）。
- **`query/layer_stats.py:141`** 判「新」的那一行：`new = sorted(a for a in flags if a not in baseline["frozen_assertions"])`——只看 id 在不在凍結集合（#29）。
- **`query/graph_walk.py` 第 1 型降級**（`walk()` 內）：`if readings is None: parts["thin_layer_unread"] = None`——讀圖 ledger 讀不到時第 1 型印 `upstream_unavailable`；
  **第 2 型沒有對稱降級**：`current_layer_nodes` 由 `readings or ()` 算，讀不到時是空集合、照常出數字（#33）。守第 1 型的測試是 `tests/test_graph_walk.py:152-159`（`test_summary_line_prints_zero_and_absence_differently`）。

## 11. 候選板

`library/private/app/state/candidates.json`（`generated_at` 2026-10-01T23:20:45Z，`content_digest` `sha256:f96eee2a…d0bc`，`today` 2026-10-02）：

| 可開 | 缺 X | 等回落 | 不要 | 已持有 | 非倍率候選 | 邊緣無法量 | 舊版 | 前提失效 | 無敘事 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 1 | 0 | 1 | 2 | 0 | 0 | 0 | 69 |

最老滯留：等回落 3 天（缺 X、可開無）。`holdings`：status ok、beta 排除 17、解析不到 0、使用者決定不研究 0。**可開 0 是合法結果**（不驗收）。

## 12. 不變的東西（結案要逐字相同）

| 對象 | 指紋 |
|---|---|
| 舊店三個 `*.db` | 見 §9 |
| `library/trades/trade_log.jsonl` | `861d2008…b8d5`（除非使用者自己回填——那時逐筆列出並附指令時間） |
| `AGENTS.md` | `b029f7b93fd1d6e37783511a14139ac55c43861b6e33c904d7c5522226dc536e`（`git diff d7d3c6e HEAD -- AGENTS.md` 結案時應為空） |
| 讀圖 ledger | inp `bc43b2d8…d4fe`、ELS `edf2b719…78be`、SuperNova `064f1b40…3b0f`、cw `f8e4439b…671c` |
| 敘事 ledger | 見 §4 |
| 主題等權組 ledger | `25721a7a…7503` |
| `library/leads/event_watches.json` | `d00710e5…0a37`（結案登記的回查 date watch 除外；daily 每天會動它，所以結案比的是「讀圖／敘事來源的語意 watch 逐筆不變」，不是整檔） |
| `outcome_aggregate.json`／`.jsonl` | `dab6e21b…f758`／`e83205e0…af53`（daily 每天 append；結案比的是**既有行的四欄逐位不變**） |

`python -m webapp status`：state artifacts **8 份**（structure_table、beta、graph_walk、watches、positions、structure_readings、account_scorecard、candidates）。
殭屍 grep（`python scripts/retired_mechanism_grep.py` 驗收段）：**未列 0／腐壞 0／不合法 0**。

## 13. 對 plan §0.2 的更正（5.0 實測）

| plan 原寫 | 實測 | 影響 |
|---|---|---|
| 讀圖 supersede 鏈「只有 SuperNova 是圖變了之後的重讀，其餘 digest 相同」 | inp、cw 兩鏈有 5 個同 kind 環節 digest 不同（全對得上查詢程式 commit 或 schema 升版） | §5 `rewritten` 規則修正（§0.6 #2）；5.4 真實資料預期 held 0／rewritten 9 |
| 「`watch.judgment.touches == "yes"`」 | 對，但判無關寫在複數 `judgments`；`source_ref` 是 `reading:<id>#n`；`kind` 是 `semantic_condition` | §5 輸入與 §13 陷阱同步（§0.6 #5） |
| 「Sheet 漏了 COHR 列」 | Sheet 已有 COHR 10 股 @316.23 USD（觀察格、IB） | 5.3 結尾的回填指令範本照實寫「Sheet 已有、trade_log 沒有」 |
| 「[666] 被 Forbidden 擋下」（Phase 4 結案時） | `origin_linkage` token 已存在、stash 預熱清單 37 名全在 | 5.1 的入口檢查對今天的圖會放行；[666] 重試仍是使用者動作 |
| lead registry（未列） | 1193 則 | — |
| 計分表「五欄有值的格」（未提 NaN） | 90 天 vs SOXX 是 NaN（歐洲 5 檔 10-01 NaN 收盤） | 5.5 修取價（§0.6 #3）；5.2 籃子函式濾 NaN |
| `outcome_if_settled_today.py --no-benchmark` 當查證命令 | 會覆寫當日聚合行、超額寫成 null | 5.0 改用包裝；5.2 根除；結案 R2 第 2 項同步（§0.6 #1） |
| 「history 22 列與 5.0 逐位相同」 | 跨日只有錨點穩定 | 5.2 分兩層比（§0.6 #4） |

## 14. 本 Step 的 L11-6 ④

「如果這份基準是錯的，最先壞掉的是哪一筆」——**預測表的手算**：5.4 會拿它當對照答案，手算錯了 5.4 會把錯的規則寫成對的。
試圖讓結論變假的動作：①用程式（`p5_chain_links.py`，走 staleness 的唯一 owner）重比每個環節，而不是憑 plan §0.2 的敘述——推翻了 plan 的「digest 相同」；
②對 5 個 digest 變動的環節逐一找出兩筆之間的 commit——5 個都找得到（若有一個環節期間沒有任何查詢程式 commit、且供給側真的多了一家，修正後的規則就該讓它算 `held`；今天沒有這種環節）；
③確認沒有分岔（每筆最多一個後繼）、沒有撤回、沒有判觸及——所以 `reversed`／`retracted`／`disproof_touched` 三格今天必然是 0，與規則版本無關。
**追蹤表的歷史四欄**：跑包裝前後兩個聚合檔 sha256 相同，證明本 Step 沒有寫進那條序列。

## 15. Step 5.1 #29：③b 的內容基準與真實資料驗收（2026-10-02 15:14 台北）

**內容基準**：`config/graph_baselines.json` 新鍵 `assertion_content_2026_10_02`（append-only；`git diff` 只有新增 708 行、0 行刪改——4.0 的鍵逐位不變）。
由唯讀 session 對今天的圖算：`query.layer_stats.content_digests(fetch_assertions, fetch_all_quotes, ids=4.0 凍結的 assertion 集合)`，
指紋＝`assertion_content_digest`（邊＋`source_doc_id`＋逐字＋sub＋`origin`／`source_type`／`origin_linkage`，sha256 前 16 碼；不含 `published_at`、`confidence`）。
產生腳本 scratchpad `p51_content_baseline.py`（乾跑印統計、`--write` 才寫；寫前驗格式可逐位重現、寫後驗既有鍵相同）。

| 量 | 值 |
|---|---|
| 圖上 EdgeAssertion | 699 |
| 4.0 凍結 695 筆今天在圖上 | 695（不見的 0）→ 內容基準 **695 筆** |
| 不在凍結集合的 | 4（`axti_8_k_20260702_coherent_inp_supply_add_edge:a4bc2`、`gsr_cpo_not_delayed_2026_06_10_e3`／`_e4`、`lrcx_10_q_20260423_add_edge:7991c`——Phase 4 的 [664]／[665]／[668]，都不帶 sub） |
| 帶 sub 的 | 113（全部在凍結集合內） |
| 檔指紋 | 改前 `adb1c88d…6d8a` → 改後 `ad52cbac…a2cc` |

**真實資料**（scratchpad `p51_layer_real.py`，唯讀）：今天 ③b **新增 0、重寫 0**——「③b 新增或重寫的帶 sub supported 0／0（還沒有新增或重寫帶 sub 的）」；
①73、②6 層、③a 102／113、外部印證不具名 15 與心跳（§3）相同。
**模擬 [666] 重試**（記憶體裡只把 Reuters 那份 11 筆 assertion 的 `origin_linkage` 改成 `independent`，不碰圖）：**重寫 4**＝`_e1`、`_e2`、`_e9`、`_e10`，4／4 含字表語言——
正是 Phase 4 closeout §2 ③ 預言的那 4 筆；改前的計數器對同一個情境會印 0／0（成功與失敗同形，L13）。
變異：把重寫判定換成空集合 → `tests/test_layer_stats.py` 2 條紅；還原 11 條綠。

## 16. Step 5.2 三條 lane 的真實資料驗收（2026-10-02 15:3x–16:2x 台北）

scratchpad `p52_collect_real.py`（`collect()` 唯讀；跑前跑後兩個聚合檔指紋不變）：

| lane | 列 | 算得出報酬 | 量測起始 | 等權 | 對 QQQ 超額 | 對主題等權組超額 | 前已漲 |
|---|---|---|---|---|---|---|---|
| live | **0**（beta 事件 2 不進 lane；配對不到的賣出 0、壞行 0） | 0 | — | — | — | 還沒有值 | — |
| paper | **4**（AXTI、COHR、LITE、SIVE.ST；ledger 4 本、沒有 v2 0、壞行 0） | 4 | **2026-09-29** | +5.67% | +5.12% | +3.71%（4/4） | 敘事前已漲 3/4 |
| history | 22 | 22 | 2026-07-21 | +8.94% | +4.29% | −2.51%（22/22） | 入圖前已漲 8/22 |

- paper 的錨點全是第一份 v2（AXTI `ib_b6b3…`、COHR `ib_9a58…`、LITE `ib_78d7…`、SIVE.ST `ib_84e5…`——**不是** 10-01 換版那份）；當時→現行狀態：AXTI priced_wait→priced_wait、COHR／LITE pass→pass、SIVE.ST missing→missing；首次點名：AXTI／COHR／LITE 是 `edgar:` 的 lead（07-22），SIVE.ST 是 `x:aleabitoreddit`（07-25）。
- 主題等權組 `tc_35b0d5cd521656ea`：15 檔、缺價 0；每列排除本檔（paper 四檔都是成員 → 各比 14 檔）。取價要 17 檔、抓 17 檔（上限 60、截掉 0）。
- **history 錨點指紋** `6ea352ed…7b93`＝§2（跨日穩定）；**同一份價格上**改前（git HEAD 版腳本）與改後的 history rows（拿掉新加的主題等權組三個鍵）、三量、等權**逐位相同**（scratchpad `p52_history_same_prices.py`：rows digest `a77673f6…` 兩邊相同）。
- `python -m webapp materialize --positions` → `stockbot-app/positions/2`（88,913 bytes），聚合檔指紋不變（materialize 不寫它）。
- 心跳段 4 與 §3 逐行對照：新增「追蹤表 history 22｜paper 4｜live 0（beta 事件 2 不進 lane）｜主題等權組 tc_35b0d5cd521656ea（2026-09-30 定）」、history 那行多「對主題等權組超額」、「入圖前已漲」旁多「敘事前已漲（paper）3/4」、新增 paper 與 live 兩行；其餘數字變動來自盤中價格與使用者白天整理過的 Sheet（NAV 15→16 檔＝補上 COHR）。其他段只差標頭時間與「首日 5 項」（新快照鍵）。
- headless Edge 在臨時實例（127.0.0.1:8798，驗完即關）渲染 `#/positions`：三條 lane 區塊在最前、paper 表 4 列、live 印「還沒有列」、樣本效度仍在聚合數字之前。
- ⚠ **長駐 APP（PID 15956，2026-09-10 23:13 起跑）用的是 09-10 的程式**：`/api/v1/positions` 回 503（schema `/2` 不認得），結構表、走圖、讀圖、候選板四個 GET 本來就回 404——重啟它是使用者動作（plan §14 #11）。
- 變異：lane 混算、組不排除本檔、幣別不一致仍算、取價不濾 NaN、`--no-benchmark` 照寫、paper 錨改用現行敘事、live 讀壞不降級——7 種全紅，還原後全綠。

## 17. Step 5.4 圖預測對錯表的真實資料驗收（2026-10-02 16:4x 台北）

- `python -m webapp materialize --structure-readings` → `stockbot-app/structure_readings/2`（53,390 bytes；現行 2／stale 0／低級 2／過期 0）。
- 預測段與 §5.2 的修正後手算**逐筆相同**（15 筆；scratchpad `p54_real_check.py`）：

| held | reversed | disproof_touched | retracted | rewritten | open | expired_unread | non_assertion | 合計 |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 9 | 2 | 0 | 4 | 15 |

  `earliest_open_expiry` ＝ **2026-12-24**；`unreadable_nodes` 空、`retraction_markers` 0、as-of 缺席不適用（現行視角）。
  ROADMAP ②（「圖預測表有第一筆對／錯」）今天**仍是 0**——照 §0.1 #4：機制由夾具證明，結案寫「已交付、未生效」並登記 2026-12-24 的回查 date watch。
- 心跳與 5.2 那次（`hb_52.md`）逐行對照：段 4 只多一行
  `圖預測：對 0｜錯 0（當時已有 0／之後才出現 0／未定日 0）｜現行 2｜到期未重讀 0｜改寫 9｜非斷言 4｜現行最早到期 2026-12-24`；
  「首日 5 項」→「首日 8 項」（新快照鍵 `predictions.held`、`predictions.wrong`、`predictions.expired_unread`）；其餘差異是兩次之間的盤中價格。
- headless Edge 在臨時實例（127.0.0.1:8798，驗完即關）渲染 `#/structure-readings`：「圖預測對錯表：讀圖說的，後來對了嗎」區塊印出 對 0／錯 0（當時已有 0／之後才出現 0／未定日 0）／現行 2（最早 2026-12-24 到期）／改寫／非斷言 9／4，沒有殘留「載入中」。
- 變異（worktree）：拿掉條件②、沒日期壓成之後才出現、`source_ref` 全等比對、判無關也算觸及、接進 staleness、撤回當改寫——6 種全紅，還原後全綠。

## 18. Step 5.5 計分表接主題等權組基準的真實資料驗收（2026-10-02 台北）

**同一份價格、改前改後**（scratchpad `p55_same_prices.py`：yfinance 換成快取替身，每檔只真的抓一次，改前＝master 的
`engine_b/account_scorecard.py`、改後＝5.5；讀主樹的 lead registry 與主題等權組 ledger，唯讀）：

- 既有格（QQQ／SOXX 超額、點名前漲幅、追源、假設、no-go；全部點名與每檔最早兩組）**16／16 逐位相同**；被 NaN 污染而改變 **0** 格——今天抓到的價格沒有任何一檔有 NaN 收盤。
- `price_budget.requested` 42 → **49**：增量 7 ＝ 成員中原本不在取價清單的檔數（`theme_cohort_added`：2455.TW、300308.SZ、3081.TWO、3363.TWO、4971.TWO、4979.TWO、ENA.V）；截掉 0。
- 主題等權組 `tc_35b0d5cd521656ea`（AI 光互連／CPO，2026-09-30 定）：成員 15、取得到價 15、缺價 0。
- 對組的超額（`x:aleabitoreddit`）：全部點名 30 天 −6.42%（n=790）、90 天 −13.55%（n=116）；每檔最早一次 30 天 −1.96%（n=39）、90 天 −11.10%（n=29）。**只印不比**。

**10-01 NaN 重放**（`p55_nan_replay.py`：同一份價格，把 IQE.L、SHA0.DE、SIVE.ST、SOI.PA、XFAB.PA 的 2026-10-01 收盤換成 NaN，各 1 列）：

| 格 | 早上 artifact（10-01T23:20Z） | 重放：改前 → 改後 | 乾淨價格（改前＝改後） |
|---|---|---|---|
| 全部｜30 天 vs QQQ | −43.57%（n=770） | −34.27% → **−0.63%** | −0.63%（n=790） |
| 全部｜30 天 vs SOXX | −27.72%（n=770） | −26.85% → **−0.06%** | −0.06% |
| 全部｜90 天 vs QQQ | −15.32%（n=110） | −14.44% → **−15.32%** | −15.32%（n=116） |
| 全部｜90 天 vs SOXX | **NaN**（n=110） | NaN → **−5.70%** | −5.70% |
| 全部｜點名前 30 天漲幅 | +7.54%（n=991） | +7.54% → **−1.46%** | −1.46% |
| 每檔最早｜30 天 vs QQQ | −7.16%（n=39） | −7.16% → **−11.11%** | −11.11% |
| 每檔最早｜30 天 vs SOXX | +2.80%（n=39） | +2.80% → **+1.49%** | +1.49% |
| 每檔最早｜90 天 vs QQQ／SOXX、點名前漲幅 | — | 不變 | — |

重放時被污染的 **7／10** 格，改後的值都等於乾淨價格的值。**污染不只讓一格變 NaN**：NaN 混進中位數的排序後，看起來正常的格也被靜默算錯——早上那份 artifact 只有「90 天 vs SOXX」露出 NaN，其餘被污染的格看不出來（plan §14 #15）。

- `python -m webapp materialize --scorecard`：✓ account_scorecard → account_scorecard.json（349,043 bytes；1 個帳號／991 則具名點名；schema `/2`；取價 49 檔、截掉 0）
- 心跳段 5 與 §3 逐行對照：第二行變成 `完整表（每個帳號的量測窗、點名數、超額報酬、追源成功率）在 APP 帳號計分表頁｜已知偏差 4 條（也在 APP）｜主題等權組基準：有`（「已知偏差 3 條」→ 4 條、行尾多那一格）；第一行只差計分表 as-of。
- headless Edge 在臨時實例（127.0.0.1:8798，驗完即關）渲染 `#/account-scorecard`：首段印主題等權組 `tc_35b0d5cd521656ea`（成員 15、取得到價 15、缺價 —）與「為主題等權組多抓」7 檔；帳號表三個基準並排（30 天：QQQ −0.6%、SOXX −0.1%、主題等權組 −6.4%，n=790）；四條已知偏差在頁尾；沒有殘留「載入中」
- 變異（worktree）：拿掉 NaN 過濾、不排除本檔、成員排在點名之前、組缺席壓成 0、心跳不看缺席一律印有、freshness 不看組、組報酬改中位數——7 種全紅；路由守門：meta 漏列、`STATE_ROUTES` 漏列、request path 叫 `build_scorecard`——3 種全紅。還原後全綠。
