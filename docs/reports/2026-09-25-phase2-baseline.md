---
date: 2026-09-25
topic: phase2-baseline
plan: docs/plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md
step: 2.0
---

# Phase 2 Step 2.0 — 基準快照

**這份報告只有一個用途：Phase 2 各 Step 與結案時逐項比對**（plan §1、§12）。現況數字會腐壞，所以連同**產生它們的命令**一起存。
本檔每個數字數的都是**圖、讀圖 ledger、等待 registry、機制存在與否**（邊數、節點數、id、kind、sha256、測試數），
沒有一個是研究結果，也沒有「幾檔通過某個 filter」。

- 快照時間：2026-09-25 12:05–12:40（台北）
- HEAD：`0a557b6`（工作區乾淨）
- Python：`.venv/Scripts/python.exe`
- 排程：`StockBotv2-Daily` 唯一；上次 2026-09-25 05:30、下次 2026-09-26 05:30（`schtasks /Query /TN StockBotv2-Daily /V /FO LIST`）

## 0. 今天 05:30 daily 的兩個失敗步驟（開工前照實記）

心跳段 1 印「失敗 2：07c_classification_health（exit 2）、15_invariants（exit 1）」。逐一查（`library/private/heartbeat/daily_run_2026-09-25.json`）：

| 步驟 | 當時的原因 | 現在 | 歸屬 |
|---|---|---|---|
| `15_invariants` | `Expiry` FAIL：[586] 在等事件卻沒有到期日（`invariants_2026-09-25.json`） | **PASS**——使用者 06:35 已補重問日（`f2159f7` 補記），12:05 重跑 13 PASS | 已解，不需動作 |
| `07c_classification_health` | 2 則 triaged_go lead 缺 `triage.classification`（`issue=missing`） | **仍 exit 2，且變 3 則**：`lead_44ce140c…`（AXTI 8-K 2026-07-29）、`lead_f6d7fdd6…`（AXTI 8-K 2026-07-22）、`lead_9b9d5797…`（x:aleabitoreddit $SIVE） | Phase 1 待決 #14＋#17（追源排回寫假 triage、缺分類沒人接）＝**本 Phase Step 2.9b**；pq1 drain 因此扣住這 3 則（見 §8） |

`python -m engine_b.cli classification-health` 12:10 重跑：`"active_unclassified_count": 3`，exit 2。

## 1. 全測試基準

`python -m pytest -q`（最後一行）；`ls tests/test_*.py | wc -l` → **183**

```text
2520 passed, 1 skipped, 1 warning in 248.32s (0:04:08)
exit=0
```

## 2. 六條 invariant

`python -m audit invariants` → **13 PASS／FAIL 0**（共檢查 4730 筆）。與本 Phase 相關的兩行：

```text
PASS    Orphans              134 個跨檔引用全部解析得到 [134 筆]
PASS    QueueSegments        pending_triage=0；fired_lead_requeue=0；fired_pq2_wake=0；semantic_pending_check=0；fired_reading_reread=0；fired_hypothesis_check=0；approved_work_orders=0；triaged_go_leads=13；forward_view_backlog=70；coverage_gaps=未讀到；duplicate_node_candidates=未讀到；stale_structure_readings=未讀到；pollable_watches=15；gated_gate_resolved=0；gated_no_pointer=0 [1931 筆]
```

⚠ `coverage_gaps`／`duplicate_node_candidates`／`stale_structure_readings` 三段在 audit 裡是「未讀到」——2.6 刪這三段、換成 `graph_holes` 時要確認新段在 audit 裡讀得到（不是繼承「未讀到」）。

## 3. APP state

`python -m webapp status`（state artifacts 段）：

```text
# State artifacts（7 份；目錄由 STOCKBOT_APP_STATE_DIR 決定）
- structure_table｜fresh（4.7h）｜current｜222 條邊／母體外 303 條
- beta｜fresh（4.7h）｜current｜sleeve 6 格／商品 14 檔
- coverage｜fresh（4.7h）｜current｜🔴 真缺口 9／🟡 建模待補 10／重複節點候選 23（沒人提過）
- watches｜fresh（4.7h）｜current｜在等 114／停滯 40
- positions｜fresh（4.7h）｜current｜逐檔 22／真實成交 1 檔
- structure_readings｜fresh（4.6h）｜current
- account_scorecard｜fresh（4.6h）｜current
```

Analyst views 73 份（有賭注 3 檔）。**7 個 kind**；本 Phase 結束時應為 `graph_walk` 取代 `coverage`、`structure_readings` 有頁。

個股頁文字 digest（`python scripts/analyst_view_text_digest.py --per-panel`）：73 檔；輸出檔 sha256 `ea0fed6548c32bb998506361806424f3acef54c0d3c438db5c07ab3c706c11f7`
（全文存 scratchpad；2.7 會照 plan 在同一天 materialize 前後再比一次，這裡只留指紋）。

## 4. 佇列與等待 registry

`python -m engine_b.cli counts` → `{"triaged_no_go": 573, "applied": 85, "parked": 483, "triaged_go": 13}`

`python -m engine_b.event_watch counters`：

```json
{"active": 114, "t1_date": 0, "t0_passive": 87, "t2_pollable": 15, "wake_pq2": 1, "wake_lead": 78, "wake_hypothesis": 3, "stalled": 40, "fired_unconsumed": 0, "expired": 0, "semantic_active": 27, "semantic_pending_check": 0, "semantic_flagged": 0, "wake_disproof": 27, "wake_reading": 5, "semantic_unreachable": 2, "expiry_decision_pending": 0, "expiry_thesis_review_pending": 0, "expiry_reread_pending": 0, "trace_expired_closed": 0, "trace_expired_closed_today": 0, "expiry_unresolved": 0}
```

**要跟著 2.5 走的數字：** `semantic_active` **27**、`wake_reading` **5**（2.5 新讀圖登記的語意 watch 以這兩個的前後差計）。

`python -m engine_b.todo list` → 球在使用者手上 0；等事件 2（[586] 已帶 2026-12-31；[632]）。

## 5. 殭屍 grep（Phase 0 八組）

`python scripts/retired_mechanism_grep.py`（驗收段）：

```text
## 驗收（差集；Phase 0 結案要三個數字都是 0）
  未列 keep-list 的命中（檔，組）數：0
  已列但不再命中（腐壞條目）數：0
  keep-list 條目數：286｜理由類別不合法：0
```

## 6. Graph MCP 盤點（2.1 的起點）

```bash
git grep -c -i -E -e 'mcp_server' -e 'graph_mcp' -e '\bMCP\b' -e 'stockbotv2-graph' -e 'mcp\.minatoyukina' \
  -e 'record_lead_decision' -e 'apply_research_action' -e 'load_extraction'
```

**81 個 tracked 檔、729 處命中。** 前十：`tests/test_intake.py` 60、`docs/plans/2026-07-16-001-…mobile…` 51、`mcp_server/graph_mcp.py` 35、
`docs/remote-access-architecture.md` 34、`docs/refactor/current-architecture.md` 34、`docs/plans/2026-09-24-001-…phase1…` 31、
`docs/refactor/target-architecture.md` 30、`docs/plans/2026-07-15-008-…` 30、`docs/plans/2026-07-24-001-…` 26、`tests/test_layer_separation.py` 23。
活的程式／設定檔（非 docs）另含：`intake/application.py` 12、`intake/__init__.py` 3、`intake/publish.py` 1、`engine_b/todo.py` 4、`crons/llm_step.py` 4、
`webapp/api.py` 1、`query/single_origin_report.py` 1、`query/health_audit.py` 1、`alpha/__init__.py` 1、`loader/migrate_entity_dedup_20260904.py` 1、
`schema/neo4j_setup.cypher` 1、`requirements.txt` 2、`.env.example` 4、`.codex/rules/stockbot-automations.rules` 1、`deploy/cloudflare/*` 24、
`prompts/intake_protocol.md` 4、`AGENTS.md` 1、`CONCEPTS.md` 3。（`load_extraction`／`apply_research_action` 也是 intake 的 domain 名稱，2.1 逐條分辨，不一律刪。）

## 7. 讀圖 ledger（2.3 的 id 基準）

`library/private/alpha/structure_readings/*.jsonl` **10 行**；以現行 `alpha.structure_reading.contracts.new_reading_id` 重算，**10／10 與檔內值逐字相同**：

| 節點 | 版本 | reading_id（檔內＝重算） | kind | created_at（UTC） |
|---|---|---|---|---|
| `mat:inp_substrate` | v1 | `sr_d6760bfe5d6e9164` | undecided | 2026-09-17T08:35:16 |
| `mat:inp_substrate` | v1 | `sr_81832cb37d87ab1d` | volume | 2026-09-17T09:20:49 |
| `mat:inp_substrate` | v1 | `sr_88340b81269fa1c2` | volume | 2026-09-17T11:15:29 |
| `mat:inp_substrate` | v1 | `sr_6ad5c884eb7bc3fb` | volume | 2026-09-18T05:32:42 |
| `mat:inp_substrate` | v1 | `sr_bc1ccb568c8886c0` | volume | 2026-09-18T15:02:21 |
| `mat:inp_substrate` | **v2（現行）** | `sr_ad503ae880ceb398` | volume | 2026-09-24T09:22:21 |
| `tech:cw_dfb_laser` | v1 | `sr_a6762186c7e8eb23` | volume | 2026-09-17T08:34:52 |
| `tech:cw_dfb_laser` | v1 | `sr_a181641ddb99c69c` | volume | 2026-09-18T15:05:45 |
| `tech:cw_dfb_laser` | v1 | `sr_caac0acae9a1c1cf` | volume | 2026-09-18T15:24:18 |
| `tech:cw_dfb_laser` | **v2（現行）** | `sr_d07679979a8e4202` | volume | 2026-09-24T09:22:24 |

`python -m alpha structure-reading mat:inp_substrate --check` → `digest 變了：False｜到期還有 83 天｜該重讀：False｜（沒有任何角度變動）`
`python -m alpha structure-reading tech:cw_dfb_laser --check` → `digest 變了：False｜到期還有 23 天｜該重讀：False｜（沒有任何角度變動）`

## 8. pq1 排序（2.8 要逐則解釋位移）

`python -m engine_b.cli drain --limit 50`（`--json` 全文存 scratchpad）：10 則排序 ＋ 3 則因缺分類被扣住（§0）。

| # | lead | first_seen | 排序標籤（`decision_impact`·`content_type`·瓶頸） | 來源 |
|---|---|---|---|---|
| 1 | `lead_26bd4214…` | 2026-09-01 | 候選集合·結構事實·**瓶頸** | x:aleabitoreddit |
| 2 | `lead_a56462e3…` | 2026-09-21 | 候選集合·結構事實·**瓶頸** | x:aleabitoreddit |
| 3 | `lead_628cbb8d…` | 2026-09-21 | 候選集合·結構事實 | system-decompose |
| 4 | `lead_f1694626…` | 2026-08-29 | 候選集合·結構事實 | decompose:nvda-cpo-switch-2026-08-29 |
| 5 | `lead_05fd6b85…` | 2026-09-24 | 排序·客戶端資本承諾·**瓶頸** | x:aleabitoreddit |
| 6 | `lead_43890d74…` | 2026-09-24 | 排序·結構事實·**瓶頸** | x:aleabitoreddit |
| 7 | `lead_c34859d8…` | 2026-09-21 | 排序·結構事實 | system-decompose |
| 8 | `lead_cad23eb9…` | 2026-09-24 | 排序·財務事實·**瓶頸** | x:aleabitoreddit |
| 9 | `lead_a6a00003…` | 2026-09-24 | 排序·財務事實 | mops:4979.TWO |
| 10 | `lead_6c5046ef…` | 2026-09-24 | 只是信心·結構事實 | x:aleabitoreddit |
| — | `lead_44ce140c…`、`lead_9b9d5797…`、`lead_f6d7fdd6…` | | withheld（classification missing） | |

`decision_impact` 為 `ranking` 的 5 則（#5–#9）就是 R-2 說的「每天還在被問一個已退役的排序問題」的現存樣本。

## 9. 舊 Decision Store（A5，只准讀；不可越線 3）

`?mode=ro` 連線（程式同 Phase 1 基準 §9）：

```text
backup_pre_v8_20260818T021452.db sha256=e887b3d458621e4cd7bb66913690d47d263d7188f9bbc1bacb4bc16ec57de350 live_choices=0 bytes=4804608
backup_pre_v9_20260902T032020Z.db sha256=af3dc690ce836b6026d86946c388d19f1500139287469f0f9fbe8711c4819d39 live_choices=1 bytes=11038720
decision_lab.db sha256=e99d1c79fd22dbe1099f30c4e06f2d1188f26a8cbfa987a27cd8842530951810 live_choices=1 bytes=16166912
```

**與 Phase 0／Phase 1 基準三檔逐字相同。結案時必須仍相同。**

## 10. 全圖 `result_digest`（2.2、2.4 證明「只有預期的節點變了」）

對圖上所有出現在 canonical 邊裡的節點跑 `build_structure(node, edges).result_digest()`：**278 個節點**
（co 92／tech 118／prod 52／mat 12／std 3／comp 1）。`node → digest` 存 scratchpad `digests_base.json`，
檔案 sha256（Windows 換行）`53af1bd163ea91deb83bc504f4fd420f817e99eb573422701d4b87babc60fe8c`；
JSON 字串本身（`sort_keys=True, indent=0`，LF）sha256 `c30f80a50aafaf9fb07c8d8573a1ba7c9aff8c9b0b73be4691ead82311058fe7`。

**2.2 的預期變動集合（預先算好，不是事後對帳）：** 8 條 `constrained_by` canonical 邊的兩端＝**14 個節點**——
`co:agility_robotics`、`co:applied_optoelectronics`、`co:coherent`、`co:iqe`、`comp:humanoid_precision_actuators`、`mat:inp_substrate`、
`prod:aaoi_400mw_narrow_linewidth_pump_laser`、`prod:vistara`、`tech:cpo`、`tech:cpo_full_stack_test`、`tech:cxl_memory_tiering`、
`tech:external_laser_source`、`tech:fiber_attach_unit`、`tech:inp_dfb_laser`。
⚠ plan §3 寫「變動的節點集合＝§0.2 那 7 個」——**7 是「反向路徑因此變空」的節點數，不是 digest 會變的節點數**：只要反向路徑裡有任何一條
`constrained_by`，即使還有 `competes_with`，digest 也會變。偏差 #1（plan §0.6）。

## 11. §0.2 表重跑（以重跑的為準）

| 事實 | plan §0.2 | 2026-09-25 重跑 | 一致？ |
|---|---|---|---|
| 讀圖 ledger | 10 行、2 節點；現行 2 份 v2 volume | 同（§7） | ✅ |
| canonical 邊逐字覆蓋 | 525／525 | **525／525** | ✅ |
| 需求側繞不過的節點 | 13 | **13**（名單相同） | ✅ |
| └ 薄層（1–3 家）且沒有現行讀圖 | 4／13 | **4／13**：hbm、semiconductor_manufacturing_equipment、six_inch_inp_production、uhp_laser | ✅ |
| └ 恰 1 家且不是外部印證 | 2／13 | **2／13**：semiconductor_manufacturing_equipment←AMAT `self_reported_costly`；six_inch_inp_production←Coherent `self_reported` | ✅ |
| └ 供給側 ≥1 家但 sub 全未填 | 2／7 | **2／7** | ✅ |
| └ 兩半都至少一段逐字可引 | 7／13 | **7／13** | ✅ |
| 反向路徑非空的節點 | 26；只靠 `constrained_by` 7 | **tech／mat／prod 範圍 26；只靠 `constrained_by` 7**（mat 1、prod 2、tech 4）。**全節點範圍是 51／9**（另含 `co:agility_robotics`、`comp:humanoid_precision_actuators`） | ✅（口徑＝tech／mat／prod；2.2 驗收沿用此口徑，並另報全節點 51→42） |
| 走不到需求錨 | 93／182；49／113；43／92；**6／51** | **93／182；49／113；43／92；6／51**（`co:aeva`、`co:agility_robotics`、`co:corning`、`co:ewellix`、`co:ime_cas`、`co:intel`） | ✅ |
| 產品節點 | 52；有 `supplies_to` 進來 13；其中無 `develops`／`deploys` 10 | **52；13；10**（amat_ags、amat_semiconductor_systems、blackwell、els_8ch_module、gf_scale、ph18da、quantum_dot_laser_epiwafer、spectrum_x、starlight、supernova） | ✅ |
| lead 點名但不在圖 | triaged_go 13 中 10 則有 company_ids；4 則點名圖上沒有的公司 | **13；10；4 則**（`co:amd` ×2、`co:iren` ×2、`co:sandisk` ×1，共 5 個（lead, 公司）對） | ✅ |
| coverage 現況 | 🔴 9／🟡 10／重複 23 | 同（§3） | ✅ |
| APP kinds | 7 | 7 | ✅ |

量測腳本存 scratchpad（`baseline_metrics.py`、`cp_scope.py`、`cp_digest_expect.py`），只讀圖與 ledger、不寫任何 authority。

## 12. 今天的心跳（12:06 手動產生；`python -m crons.heartbeat --out <scratchpad>\hb_base.md`）

```markdown
# Daily 心跳 — 2026-09-25 12:06 台北標準時間

## 1. 資料新鮮
- daily（run 4fe5bce1）：23 步完成｜**失敗 2**：07c_classification_health（failed，exit 2）、15_invariants（failed，exit 1）
- 排程設定與 config 一致（05:30／時限 240 分鐘）
- harvest 來源 36 個｜失敗 0 個｜最後一輪 2026-09-25 05:30
- 本月 X 花費 $0.12 / 上限 $10.00
- 行情 14 檔｜最新完整交易日 2026-09-20 ～ 2026-09-24｜降級 5 檔：0050.TW（quarantined）、006208.TW（quarantined）、00631L.TW（quarantined）、00981A.TW（quarantined）、DRAM（insufficient_history）
- 台股月營收 7/7 檔｜最新 2026-08｜已跟上公告期限
- FX 觀測 4 檔｜最新 as_of 2026-09-24（1 天前，容忍 ±3 天）｜全部在窗內
- APP artifact 今天已 materialize 7 份
- 備份：最後 0 天前（20260924T213737Z）｜Drive skipped｜還原驗證 有｜之後變動未備份 90 檔
- 健康審查 13 節｜**🔴 1**：重複 SourceDoc（同 URL 不同 doc_id）
- invariants 13 項｜**FAIL 1**：Expiry

## 2. 變了什麼
- 較昨變動：尚無上一份快照（第一次產生；之後每天逐項比對，只印變了的）
- watch：今日醒 3｜今日到期 0｜已觸發未消化 0｜語意標旗 0｜**未檢 0**（判定只在互動：`python -m engine_b.event_watch semantic-queue`）
- 反證：在盯 27（其中叫不醒 2）｜**觸及待處置 0**｜到期待複查 0（併進 thesis 複查／節點重讀）｜未盯 0（v1 讀圖散文 0 份不可機械數；凍結歷史 32 不盯）
- **今天第一次被點名、registry 沒有的名字 1**：AKAM（$AKAM signs $11.6B compute dea）｜累計被點名但未登記 110（`python -m engine_b.cli onboard-candidates`）
- thesis：active 2、revised 1｜該核查 0 檔
- 候選狀態板未落地（not_yet_recorded）：籃子 filter、目標價與多年視角已於 Phase 0 退役；接手的候選狀態板要到 Phase 3 才落地
- 結構讀圖 2 份｜現行 2｜**該重讀 0**（stale 0／過期 0；低級 0 不進佇列）
- 已定價嗎（財務三題）未落地（not_yet_recorded）：目標倍數背離計數器已於 2026-09-23 隨估值鏈退役；「已定價嗎」由 Phase 3 財務三題回答，主參照是自己的歷史、不設門檻
- beta 報告狀態 degraded｜警告 4 條：drawn_debt_present、issuer_concentration_warning:TSMC、issuer_lookthrough_partial、unclassified_holdings_assumed_unlevered_direct_issuer

## 3. 佇列
- **未 triage 0**｜新 harvest lead 需要分流｜分類層每日上限 30
- 分類層：本輪完成：處理 5、PASS 3、FILTER 2、拒收 0｜session d6d5ae32-5855-416a-9880-be3df68a84ea｜上次成功：2026-09-25 05:32（0 天前）
- 預篩 0｜標旗 0（可能觸及 0／無關 0／看不出 0）｜無全文 0｜無 fetcher 0｜截斷 0｜拒收 0
- pq1 可做 13｜機械段待清 0
- **pq2 球在你手上 0**｜池中未結案 2（差額＝等事件或已在 pq1 跑）
- watch 到期：今日 0｜累計 0（已處置：0；待決 watch_decision 0｜等 thesis 複查 0｜等重讀 0）｜追源到期結案今日 0
- 事件監看總數 127｜無到期的等待 0
- 距上次掃題材 5 天（2026-09-20；門檻 7 天）

## 4. 部位
（略：與本 Phase 無關，全文在 scratchpad `hb_base.md`；段名與行數：9 行）

## 5. 帳號計分表
- tier 分佈：measured 0／probation 1／trusted 0｜1 個帳號｜計分表 as-of 2026-09-24｜較昨：尚無上一份快照
- 完整表（每個帳號的量測窗、點名數、超額報酬、追源成功率）在 APP 帳號計分表頁｜已知偏差 3 條（也在 APP）
```

本 Phase 會動的心跳行：段 2「結構讀圖 N 份｜現行｜該重讀」（2.6 加單位拆分）、段 3「pq1 可做…」（2.6 新增「走圖：」一行並承接讀圖待重讀）。
段 1 的「invariants FAIL 1：Expiry」是讀 05:30 那次的 capture，12:05 重跑已 PASS（§0）。
