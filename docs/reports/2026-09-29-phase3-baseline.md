---
date: 2026-09-29
topic: phase3-baseline
plan: docs/plans/2026-09-26-001-feat-phase3-candidate-states-three-questions-plan.md
step: 3.0
---

# Phase 3 Step 3.0 — 基準快照

**這份報告只有一個用途：Phase 3 各 Step 與結案時逐項比對**（plan §1、§12）。現況數字會腐壞，所以連同**產生它們的命令**一起存。
本檔每個數字數的都是**敘事 ledger、等待 registry、個股頁、Engine C 表、機制存在與否**（id、kind、sha256、列數、測試數），
沒有一個是研究結果。§12 的邊緣三態分布**只是 3.3 的比對基準，不是驗收數字**（plan §1 第 12 項）。

- 快照時間：2026-09-29 11:05–11:40（台北）
- HEAD：`ba33524`（工作區乾淨）
- Python：`.venv/Scripts/python.exe`
- 排程：`StockBotv2-Daily` 唯一；上次 2026-09-29 05:30、下次 2026-09-30 05:30、Status Ready（`schtasks /Query /TN StockBotv2-Daily /V /FO LIST`）
- 今天 05:30 的 daily：25 步完成、失敗 0（心跳段 1）
- 量測腳本與全文存 scratchpad（`baseline_p3.py`、`readings_base.py`；只讀，不寫任何 authority）；下表列指紋，後續 Step 以同一支腳本重跑比對

| scratchpad 檔 | 內容 | sha256 |
|---|---|---|
| `baseline_p3.json` | §3–§5、§7 每筆 watch、§8、§10、§11、§12 的逐檔明細 | `b05a85b1…6dc9e45` |
| `hb_base.md` | §6 心跳全文 | `2a08599a…c752aba` |
| `drain_base.json` | §13 pq1 drain 全文 | `2760eec3…2a5629` |
| `graph_walk_base.json` | §7 走圖 `--json` 全文 | `5458ea44…11209b` |
| `zombie_base.txt` | §9 殭屍 grep 全文 | `893d1d9a…ff538d` |
| `digest_base.txt` | §4 個股頁文字 digest `--per-panel` | `d06bccb7…853f00f8` |
| `engine_c_schema_base.json` | §11 各表 `PRAGMA table_info` | `4804fe25…242dce32` |
| `test_functions_base.txt` | §1 `def test_` 名單 | `23792907…0b1f5` |

## 1. 全測試基準

`python -m pytest -q`（最後一行）；`ls tests/test_*.py | wc -l` → **184**

```text
2592 passed, 1 skipped, 1 warning in 243.89s (0:04:03)
exit=0
```

測試函式名單：`git grep -n -E "^\s*(async )?def test_" -- 'tests/*.py'` 正規化成 `檔::函式` 排序 → **2156 個**（名單 sha256 `23792907abf891d01afc07886df1d84350e36ad1cb79f471e88a579eddc0b1f5`）。
結案比對以本 Step 的 commit 為起點重跑同一條命令（名單可由 `git show <3.0>:tests/...` 重建，不依賴 scratchpad）。

本機真 runtime 整合測試 `python -m pytest tests/test_full_chain_acceptance.py -q` → **27 passed**（62.8s）——3.9 的 L11-6 ④ 對這個數。

## 2. 六條 invariant

`python -m audit invariants` → **13 PASS／FAIL 0**（共檢查 4842 筆）。與本 Phase 相關的兩行：

```text
PASS    QueueLiveness        161 項進行中工作全部在 14 天內有進展 [161 筆]
PASS    QueueSegments        pending_triage=0；fired_lead_requeue=0；fired_pq2_wake=0；semantic_pending_check=0；fired_reading_reread=0；fired_hypothesis_check=0；approved_work_orders=0；triaged_go_leads=12；forward_view_backlog=70；graph_holes=60；pollable_watches=15；gated_gate_resolved=0；gated_no_pointer=0 [1965 筆]
```

**3.1a 的 L11-6 ④ 起點：** `graph_holes=60`（九型命中之和，異單位）——改後應變成「有命中的型別數」（今天九型全部命中 >0 以外的只有第 4 型＝0，見 §7），其他格不變。

## 3. 短評 ledger（v1 id 基準）

`library/private/alpha/briefs/*.jsonl` **3 檔 7 行**（AXTI 2、COHR 2、LITE 3），全部 `investor-brief/v1`。
以現行 `alpha.narrative.contracts.new_brief_id` 重算：**7／7 與檔內值逐字相同**。三檔現行紀錄：

| 檔 | 現行 brief_id | created_at（UTC） |
|---|---|---|
| AXTI | `ib_d6a413c3dbc796c5` | 2026-09-19T04:17:11 |
| COHR | `ib_37dfb9b27153eba8` | 2026-09-19T05:12:23 |
| LITE | `ib_b36e5f298bceef47` | 2026-09-19T04:17:55 |

## 4. 73 份個股頁

`python -m webapp status`（Materialized Analyst Views 段）：**73 份**；readiness **ready 3（AXTI、COHR、LITE）／blocked 70**。

blocker 分布（`baseline_p3.json` 的 `views[*].blockers`）：`brief=not_yet_recorded` 70；`research` 缺 10（`not_yet_recorded`）＋2（`deliberate_abstention`：012330.KS、NOVT）；`wipeout=upstream_unavailable` 3（5016.T、5802.T、BX）。

refresh：current 60／review_required 12／invalidated 1（TSM）。**非 current 的 13 檔，來源全部是 `operating_assumption`／`axis`／`thesis`**（退役估值鏈殘留，與讀圖無關——plan §0.2 那一列成立）：

| 檔 | refresh | 來源（artifact_type:artifact_id，operating_assumption 只計數） |
|---|---|---|
| 000660.KS、IREN、XPEV | review_required | operating_assumption ×1 |
| NBIS | review_required | operating_assumption ×2 |
| AXTI、COHR、LITE、LYC.AX | review_required | `axis:expectation_gap` |
| 6324.T | review_required | `axis:expectation_gap`、`thesis:session_judgment` |
| 5802.T | review_required | operating_assumption ×1、`axis:expectation_gap`、`thesis:session_judgment` |
| MP | review_required | operating_assumption ×2、`axis:expectation_gap`、`thesis:session_judgment` |
| SOI.PA | review_required | operating_assumption ×3、`axis:earnings_exposure`、`axis:expectation_gap`、`axis:value_capture`、`thesis:session_judgment` |
| TSM | invalidated | operating_assumption ×6 |

核心面板：`CORE_PANELS=("headline","brief","argument","research","wipeout")`、`OPTIONAL_PANELS=("fundamental","bet","readings")`（artifact 的 `readiness.core_panels` 逐檔相同）。

文字 digest：`python scripts/analyst_view_text_digest.py --per-panel` → `# TOTAL 64b0082598fd36a2 73 檔`（全文 sha256 見上表）。

argument：73 檔標題都是「為什麼這樣想：鏈、賭注、風險與認錯條件、時間表」；`argument:chain` 段 **73／73 status=available**，逐檔文字存 `baseline_p3.json` 的 `views[*].chain`（3.7 比對用）。例（AXTI）：「需求端是『Optical scale-up interconnect』。AXT, Inc.供應『Lumentum』；驗證中；有客戶或第三方印證。…」

## 5. 歸零旗標四盞（ROADMAP ④ 的基準）

以 `engine_c.checklist.get_wipeout_inputs` ＋ `alpha.wipeout.wipeout_flags` 對 73 檔重算（與個股頁同一條取數與判色；today＝2026-09-29）：

| 盞 | 有顏色（非灰） | 灰（依 absence_kind） |
|---|---|---|
| 現金跑道 | **67／73**（綠 44、黃 16、紅 7） | upstream_unavailable 6 |
| 負債 | **70／73**（綠 41、黃 17、紅 12） | upstream_unavailable 3 |
| 稀釋 | **0／73** | insufficient_evidence 73 |
| going concern | **0／73** | capability_absent 73 |

稀釋燈每檔的 `colour_available_on`（逐檔在 `baseline_p3.json`）：最早 **2027-07-08**（3 檔）、最晚 **2027-09-03**；分布 2027-07-18 ×27、2027-08-21 ×19，其餘 14 個日期各 1–3 檔。**3.3 的 L11-6 ④：非美股的檔不得失去這個日期。**

## 6. 今天的心跳（11:29 手動產生；`python -m crons.heartbeat --out <scratchpad>\hb_base.md`，不帶 `--write-snapshot`）

全文在 scratchpad。本 Phase 會動的行，逐字：

```text
（段 2）- 候選狀態板未落地（not_yet_recorded）：籃子 filter、目標價與多年視角已於 Phase 0 退役；接手的候選狀態板要到 Phase 3 才落地
（段 2）- 已定價嗎（財務三題）未落地（not_yet_recorded）：目標倍數背離計數器已於 2026-09-23 隨估值鏈退役；「已定價嗎」由 Phase 3 財務三題回答，主參照是自己的歷史、不設門檻
（段 2）- 反證：在盯 36（其中叫不醒 3）｜**觸及待處置 0**｜到期待複查 0（併進 thesis 複查／節點重讀）｜未盯 0（v1 讀圖散文 0 份不可機械數；凍結歷史 32 不盯）
（段 3）- 走圖：薄層沒人讀 4／13｜獨家且自報 2／13｜供給側未填 2／7｜讀圖該重讀 0／4｜lead 點名不在圖 4／8｜供貨走不到錨 6／51｜沒人供應 9／129｜建模待補 10／181｜重複節點 23／188（consumer：research-drain 第三段）
（段 4）- 賭注帳／量的候選／要幾倍：籃子 filter、目標價與多年視角已於 Phase 0 退役；接手的候選狀態板要到 Phase 3 才落地（not_yet_recorded）
（段 4）- 歸零旗標彙總：四盞燈的彙總原本由籃子 artifact 產生，籃子已退役；Phase 3 候選板接手前沒有上游（upstream_unavailable）　←逐檔那盞燈仍在個股頁，停的只有這個彙總計數
```

三個缺席常數住 `crons/heartbeat.py:604`（`_PRICED_IN_ABSENCE`）、`:608`（`_CANDIDATE_BOARD_ABSENCE`）、`:616`（`_WIPEOUT_ROLLUP_ABSENCE`）；使用處 `:658`、`:702`、`:1216-1219`。
段 2「較昨變動 4 項｜其餘 42 項相同」——較昨鍵目前 46 個（3.6 加 `candidate.*` 後要印「首日」而不是全算變動）。

## 7. 等待 registry、走圖、APP kind

`python -m engine_b.event_watch counters`：

```json
{"active": 123, "t1_date": 0, "t0_passive": 87, "t2_pollable": 15, "wake_pq2": 1, "wake_lead": 78, "wake_hypothesis": 3, "stalled": 40, "fired_unconsumed": 0, "expired": 0, "semantic_active": 36, "semantic_pending_check": 0, "semantic_flagged": 0, "wake_disproof": 36, "wake_reading": 5, "semantic_unreachable": 3, "expiry_decision_pending": 0, "expiry_thesis_review_pending": 0, "expiry_reread_pending": 0, "trace_expired_closed": 0, "trace_expired_closed_today": 0, "expiry_unresolved": 0}
```

**要跟著 3.4／3.5 走的數字：** `semantic_active` **36**（3.4 後必須仍是 36；3.5 的增量必須＝四份 `disproof[]` 中「新登」的條數）。

每筆 watch 的 `expiry_class`（`engine_b.event_watch.expiry_class`，147 筆，逐筆在 `baseline_p3.json` 的 `watch_expiry_class`）：
trace 80、reread 31、thesis_review 16、pq2 9、decision 6、reading 5。**3.4 的 L11-6 ④：這 147 筆一筆都不得變。**

`python -m engine_b.cli counts` → `{"triaged_no_go": 580, "applied": 85, "parked": 486, "triaged_go": 12}`

`python -m query.graph_walk --json`（圖 2688 個節點）九型命中／母體：

| # | 型 | 命中／母體 |
|---|---|---|
| 1 | 薄層沒人讀 | 4／13 |
| 2 | 獨家且自報 | 2／13 |
| 3 | 供給側未填 | 2／7 |
| 4 | 讀圖該重讀 | 0／4 |
| 5 | lead 點名不在圖 | 4／8 |
| 6 | 供貨走不到錨 | 6／51 |
| 7 | 沒人供應 | 9／129 |
| 8 | 建模待補 | 10／181 |
| 9 | 重複節點 | 23／188 |

九型命中之和＝60（＝§2 的 `graph_holes=60`）；**有命中的型別數＝8**（第 4 型為 0）——3.1a 改後的預期值。
第 5 型 `extra.unresolved_names` **12 個**：`AKAM、AMZN、ASML、CAPA、CXMT、DRAM、EWY、PSMC、SIVE、SOI、SPCX、STM`（3.1b 預期 → 10，SIVE、SOI 移出）。

`python -m webapp status`：state artifacts **7 份**（structure_table、beta、graph_walk、watches、positions、structure_readings、account_scorecard）；
state 目錄 `library/private/app/state/` **11 個檔**——不在 `STATE_KINDS` 的孤兒 **4 個**：`basket.json`、`coverage.json`、`multi_year.json`、`ranking.json`（3.1c 預期 → 0）。

## 8. 舊 Decision Store（A5，只准讀；不可越線 4）與成交事件

`?mode=ro` 連線：

```text
backup_pre_v8_20260818T021452.db sha256=e887b3d458621e4cd7bb66913690d47d263d7188f9bbc1bacb4bc16ec57de350 live_choices=0 bytes=4804608
backup_pre_v9_20260902T032020Z.db sha256=af3dc690ce836b6026d86946c388d19f1500139287469f0f9fbe8711c4819d39 live_choices=1 bytes=11038720
decision_lab.db sha256=e99d1c79fd22dbe1099f30c4e06f2d1188f26a8cbfa987a27cd8842530951810 live_choices=1 bytes=16166912
```

**與 Phase 0／1／2 基準三檔逐字相同。結案時必須仍相同。**

`library/trades/trade_log.jsonl`：**2 行**，sha256 `861d2008de8cdaa80c885b4e06da11ee0a2bf188526836dddcc1701a6bc7b8d5`（3.8 的 L11-6 ④；結案時除使用者真實成交外不變）。

## 9. 殭屍 grep

`python scripts/retired_mechanism_grep.py`（驗收段）：

```text
## 驗收（差集；Phase 0 結案要三個數字都是 0）
  未列 keep-list 的命中（檔，組）數：0
  已列但不再命中（腐壞條目）數：0
  keep-list 條目數：283＋I 組 19｜理由類別不合法：0
```

與短評相關的 keep-list 條目（3.4 後要縮小，且不得有「已列但不再命中」的腐壞條目）：

| 檔 | 組 | 理由（摘） |
|---|---|---|
| `alpha/narrative/contracts.py` | C | legacy_key：placeholder 字彙（`sell_side_target`）與首屏禁字表 |
| `alpha/narrative/contracts.py` | E | legacy_key：七格 placeholder 含 `{payoff}` |
| `alpha/models/session_assessor.py` | C | legacy_key：placeholder `{sell_side_target}` |
| `alpha/models/session_assessor.py` | D | retirement_note：multiple_horizon |
| `alpha/models/session_assessor.py` | E | legacy_key：placeholder `{payoff}`／`{bet_target}` |
| `alpha/models/session_assessor.py` | G | retirement_note：檔頭流程圖 |
| `tests/test_investor_brief.py` | C | legacy_key：placeholder 夾具與禁字表測試 |
| `tests/test_investor_brief.py` | D | retirement_note：multiple_question |
| `tests/test_investor_brief.py` | E | legacy_key：`{payoff}` 夾具 |
| `briefing/alpha_view/builder.py` | A／C／E／F／G／H | 退役註記、authority 字串、假設 ledger（與短評填值同檔） |

## 10. 三檔 v1 短評：原始 slot、placeholder、missing（3.4 比對用）

每格原始文字全文存 `baseline_p3.json` 的 `briefs.by_ticker[*].slots[*].text`。現行紀錄每格的 placeholder 清單：

| 格 | AXTI | COHR | LITE |
|---|---|---|---|
| demand／supply／bottleneck | — | — | — |
| market_view | `{assumption:revenue_growth[total]}`、`{market_multiple}`、`{analyst_count}`、`{sell_side_target}` | `{analyst_count}`、`{sell_side_target}`、`{market_multiple}` | 同 COHR |
| our_bet | `{assumption:revenue_growth[total]}`、`{bet_assumption:revenue_growth[total]}` | `{bet_assumption:operating_margin_delta[mix_and_utilization]}`、`{assumption:…[mix_and_utilization]}` | `{assumption:operating_margin_delta[guided_q1_margin_held_flat]}`、`{bet_assumption:…}` |
| if_right_if_wrong | `{bet_target}`、`{price}`、`{payoff}`、`{downside_target}`、`{downside_return}` | `{bet_target}`、`{base_target}`、`{price}`、`{payoff}` | `{bet_target}`、`{base_target}`、`{price}`、`{payoff}`、`{downside_target}`、`{downside_return}`（`{payoff}`、`{downside_return}` 各出現兩次） |
| when | `{next_checkpoint_date}` | `{next_checkpoint_date}`、`{value_date}` | 同 COHR |

fill 後的 missing（今天真實 artifact 的 `dependencies.missing`）：

| 檔 | market_view | our_bet | if_right_if_wrong | when |
|---|---|---|---|---|
| AXTI | `{assumption:revenue_growth[total]}` | 兩個 assumption 全缺 | `{bet_target}`、`{payoff}`、`{downside_target}`、`{downside_return}` | — |
| COHR | — | 兩個 assumption 全缺 | `{bet_target}`、`{base_target}`、`{payoff}` | `{value_date}` |
| LITE | — | 兩個 assumption 全缺 | `{bet_target}`、`{base_target}`、`{payoff}`、`{downside_target}`、`{downside_return}`、`{payoff}`、`{downside_return}` | `{value_date}` |

**固定 values 夾具**（每個 simple placeholder → `«名稱»`，但 `base_target`、`bet_target`、`payoff` → None；帶參數的一律缺）對 7 行各跑一次 `fill_brief`：
輸出（`json.dumps(sort_keys=True, indent=1, ensure_ascii=False)` 的 LF 字串）sha256 **`2feb0ba802ae0368ec58be167468caef845b1a756d0135fae30d1a56b06a6801`**。3.4 以同一夾具重跑必須逐字相同。

## 11. Engine C 正式庫（3.2 比對「舊表不變」）

`library/private/runtime_pointer.json` → `engine_c/stockbot-engine-c-private-v1-458db5270ee2.db`（SQLite，`?mode=ro` 連線）。各表列數：

| 表 | 列數 |
|---|---|
| consensus_coverage_observations | 3541 |
| consensus_estimates | 6080 |
| financial_snapshots | 3544 |
| manual_fields | 213 |
| manual_observations | 323 |
| monthly_revenue_observations | 175 |
| technical_observations | 1350 |
| sqlite_sequence | 4 |

全部表的 `PRAGMA table_info`（`{表: 欄位清單}`，`json.dumps(sort_keys=True, ensure_ascii=False)`）sha256 **`65cbef0fcf47cff77a22ee91ec8c8aac56075c2e3e787d70f2590164b89f11e7`**——3.2 建新表後，舊表部分必須算出同一個值。

## 12. 邊緣判定現況（3.3 用；**不是驗收數字**）

`alpha.providers.market_normalization.screen_inputs`（報價單位 → 結算幣別 → USD；分析師數取 0y）＋ `config/alpha_screen.json`（10B **AND** 12 位）對 73 檔：
**邊緣 25／非邊緣 46／無法量 2**。

- 無法量：CCXI、ENA.V（市值有、`analyst_count` 取不到）
- 邊緣（市值 USD 十億、分析師數）：002472.SZ 4.92/8、2455.TW 3.22/9、3081.TWO 7.85/7、3363.TWO 2.33/2、4971.TWO 0.69/1、4979.TWO 2.52/1、6268.T 3.54/8、6324.T 3.85/9、6481.T 4.58/10、6680.HK 0.46/1、688017.SS 7.52/4、AAOI 8.22/6、AEHR 3.22/3、AEVA 0.99/5、AXTI 4.83/5、HIMX 2.43/1、IQE.L 0.79/3、LYC.AX 9.73/12、NOVT 5.37/3、POET 1.28/1、SHA0.DE 6.94/5、SIVE.ST 1.01/1、SOI.PA 5.80/6、XFAB.PA 0.95/7、XPEV 7.80/3
- COHR、LITE 在非邊緣（plan §0.2 那一列成立）

## 13. pq1 排序（3.6 驗「`_held` 語意沒變 → 逐位不變」）

`python -m engine_b.cli drain --limit 50 --json`（全文在 scratchpad）：**12 則**。

| # | lead | first_seen | 排序標籤 | 來源 |
|---|---|---|---|---|
| 1 | `lead_26bd4214…` | 2026-09-01 | 候選集合·結構事實 | x:aleabitoreddit |
| 2 | `lead_a56462e3…` | 2026-09-21 | 候選集合·結構事實 | x:aleabitoreddit |
| 3 | `lead_628cbb8d…` | 2026-09-21 | 候選集合·結構事實 | system-decompose |
| 4 | `lead_f1694626…` | 2026-08-29 | 候選集合·結構事實 | decompose:nvda-cpo-switch-2026-08-29 |
| 5 | `lead_05fd6b85…` | 2026-09-24 | 結構或讀圖會變·客戶端資本承諾 | x:aleabitoreddit |
| 6 | `lead_43890d74…` | 2026-09-24 | 結構或讀圖會變·結構事實 | x:aleabitoreddit |
| 7 | `lead_13daec45…` | 2026-09-25 | 結構或讀圖會變·結構事實 | prnewswire:us_conec |
| 8 | `lead_c34859d8…` | 2026-09-21 | 結構或讀圖會變·結構事實 | system-decompose |
| 9 | `lead_cad23eb9…` | 2026-09-24 | 結構或讀圖會變·財務事實 | x:aleabitoreddit |
| 10 | `lead_a6a00003…` | 2026-09-24 | 結構或讀圖會變·財務事實 | mops:4979.TWO |
| 11 | `lead_bf096e97…` | 2026-09-25 | 只是信心·結構事實 | edgar:MRVL |
| 12 | `lead_6c5046ef…` | 2026-09-24 | 只是信心·結構事實 | x:aleabitoreddit |

⚠ 這份順序也會因 lead 本身的推進而變（新 lead、結案）；3.6 比對時以「同一天、同一個 pending_leads 狀態下，改前改後各跑一次」為準，本表只是今天的樣本。

## 14. §0.2 表重跑（以重跑的為準）

| 事實 | plan §0.2 | 2026-09-29 重跑 | 一致？ |
|---|---|---|---|
| 短評 ledger | 3 檔（AXTI 2、COHR 2、LITE 3），全 v1 | 同（§3） | ✅ |
| thesis lifecycle | 3 筆：AXTI、COHR、SIVE.ST | `['axt_inp', 'coherent_cpo', 'sivers']` | ✅ |
| 現行讀圖 | 全 v3、到期 2026-12-24；InP 層 volume 供給側 AXT／JX／住友、COHR／LITE 在需求側；CW DFB 層 volume 供給側含 COHR、LITE、Sivers；兩個插槽 undecided | 4 份現行：`sr_bac985bacbea64b7`（InP，layer/volume）、`sr_d49b81b6465e1181`（CW DFB，layer/volume）、`sr_35ca0ce58617d5f6`（ELS，socket/undecided）、`sr_268d2fd79db629ff`（SuperNova，socket/undecided），全部 v3、到期 2026-12-24；供給側名單同 plan | ✅ |
| 個股頁 readiness | 73 份，絕大多數 blocked、最常見 `brief=not_yet_recorded` | 73；blocked 70；`brief` 70 | ✅ |
| `refresh=review_required` 來源 | 全部 operating_assumption／axis／thesis | 同（§4 表） | ✅ |
| `get_bottlenecks` production 呼叫端 | `alpha/context.py:134`、`audit/checks.py:1142` | 同 | ✅ |
| 歸零旗標 | 稀釋 0/73、GC 0/73 | 同（§5） | ✅ |
| 心跳三個缺席常數 | `crons/heartbeat.py:604-620,658,702,1216-1219` | 同（§6） | ✅ |
| trade_log | 2 行；production reader 只有 `record_trade._already_recorded` | 2 行；`git grep trade_log -- '*.py'` 非測試命中全是註解與 `record_trade.py` 本身 | ✅ |
| APP 孤兒 artifact | coverage、ranking、basket、multi_year | 同（§7） | ✅ |
| 走圖第 5 型 unresolved | 12 個（含 SIVE、SOI） | 同（§7） | ✅ |
| `duplicate_nodes`／`coverage_gaps` CLI 的使用者 | research-drain SKILL 約 159 行、`tests/test_duplicate_nodes.py`、OPERATIONS:552 | 同；另有 `skills/daily-brief/SKILL.md:300` 一句歷史說明（「從 Daily 命令清單移除」）與 `docs/ARCHITECTURE.md`、`docs/refactor/current-architecture.md` 的描述 | ✅（3.1c 逐條處理 ARCHITECTURE／daily-brief 的提及） |
| 邊緣門檻 | COHR ≈62B、LITE ≈83.5B → 非邊緣 | 非邊緣（§12） | ✅ |
