---
date: 2026-09-22
topic: phase0-baseline
plan: docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md
step: 0.0
---

# Phase 0 Step 0.0 — 基準快照

**這份報告只有一個用途：Phase 0 結案時逐項比對。** 現況數字會腐壞（`AGENTS.md`「現況數字會過期，判準不會」），
所以把它們連同**產生它們的命令**一起存下來；結案的九項 gate 全部是「與本檔的數字比」。

- 快照時間：2026-09-22 15:28–15:42（台北）
- HEAD：`7c00e4a`（工作區乾淨）
- Python：`.venv/Scripts/python.exe`

## 0. 單一 writer 狀態（plan §0.5 要求）

plan 要求執行期間暫停排程。本機實測的排程 writer 只有兩個 Windows 工作，**今天都不會再觸發**：

| 工作 | 命令 | 上次 | 下次 |
|---|---|---|---|
| `StockBotv2-Heartbeat` | `crons/heartbeat_task.py` | 2026-09-22 07:00 | **2026-09-23 07:00** |
| `StockBotv2-FxSync` | `scripts/sync_fx_observations.py` | 2026-09-22 06:55 | **2026-09-23 06:55** |

查證：`Get-ScheduledTask | ... | Get-ScheduledTaskInfo`（見下方命令附錄）。
Codex desktop 的 daily（台北 06:30）與 weekly（週日 04:00）不在 Windows Task Scheduler 內，機械查不到；
今天是星期二，weekly 不會跑，daily 的下一次同樣是明天早上。

> ⚠ **時限是 2026-09-23 06:30。** Phase 0 若跨到明天早上，必須先暫停 Codex daily／weekly 與上面兩個工作，
> 否則會有第二個 writer 動到 0a.1／0a.2 改的同一批檔。

## 1. 殭屍機制 grep（八組 × 六區）

`python scripts/retired_mechanism_grep.py`

```text

## A 排序當驅動／首選
  code: 28 檔｜query/bottleneck.py(25)、webapp/basket.py(22)、webapp/materialize.py(16)、alpha/ranking.py(14)、alpha/providers/graph_neo4j.py(11)、briefing/alpha_view/builder.py(9)、webapp/api.py(7)、webapp/__main__.py(7)
  static: 2 檔｜webapp/static/app.js(17)、webapp/static/app.js(17)
  skills: 4 檔｜skills/alpha-status/SKILL.md(9)、skills/daily-brief/SKILL.md(5)、skills/system-decompose/SKILL.md(2)、skills/blind-spot-audit/SKILL.md(1)
  tests: 14 檔｜tests/test_bottleneck_ranking.py(33)、tests/test_webapp_ranking.py(23)、tests/test_webapp_basket.py(17)、tests/test_sole_source_tristate.py(7)、tests/test_hypotheses.py(3)、tests/test_ranking_view.py(3)、tests/test_alpha_expectation_gap.py(1)、tests/test_alpha_view_render.py(1)
  config: 2 檔｜config/alpha_screen.json(2)、config/lead_classification.json(1)
  livedocs: 3 檔｜docs/ARCHITECTURE.md(18)、docs/OPERATIONS.md(3)、CONCEPTS.md(1)
  docs: 34 檔｜docs/ARCHITECTURE.md(18)、docs/archive/roadmap-pre-alpha-refactor.md(14)、docs/archive/roadmap-pre-alpha-edge.md(13)、docs/ROADMAP.md(11)、docs/archive/roadmap-phase-delivery-log.md(11)、docs/archive/roadmap-alpha-edge-2026-09-22.md(10)、docs/brainstorms/2026-09-22-graph-first-direction-decision.md(10)、docs/brainstorms/2026-09-17-no-evidence-case-zoom-out.md(8)

## B 籃子 filter
  code: 15 檔｜webapp/basket.py(49)、crons/heartbeat.py(26)、scripts/outcome_if_settled_today.py(18)、webapp/materialize.py(16)、webapp/__main__.py(14)、scripts/alpha_screen_check.py(12)、webapp/api.py(7)、query/bottleneck.py(5)
  static: 4 檔｜webapp/static/app.js(10)、webapp/static/app.js(10)、webapp/static/index.html(3)、webapp/static/index.html(3)
  skills: 1 檔｜skills/daily-brief/SKILL.md(1)
  tests: 14 檔｜tests/test_webapp_basket.py(31)、tests/test_bet_endgame.py(20)、tests/test_basket_screen_thresholds.py(18)、tests/test_heartbeat.py(12)、tests/test_wipeout_flags.py(12)、tests/test_catalyst_shape_reasons.py(6)、tests/test_opinion_stance.py(6)、tests/test_webapp_ranking.py(4)
  config: 1 檔｜config/alpha_screen.json(3)
  livedocs: 3 檔｜docs/ARCHITECTURE.md(11)、docs/OPERATIONS.md(3)、CONCEPTS.md(3)
  docs: 27 檔｜docs/archive/roadmap-phase-delivery-log.md(40)、docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(31)、docs/archive/roadmap-backlog-log.md(30)、docs/ROADMAP.md(28)、docs/brainstorms/2026-09-17-no-evidence-case-zoom-out.md(24)、docs/archive/roadmap-alpha-edge-2026-09-22.md(18)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(18)、docs/ARCHITECTURE.md(11)

## C 估值／隱含報酬／尺
  code: 51 檔｜briefing/alpha_view/builder.py(166)、alpha/entry/model.py(85)、alpha/valuation/contracts.py(32)、briefing/alpha_view/sources.py(29)、briefing/analyst_view/compose.py(29)、alpha/valuation/assumptions.py(24)、alpha/reverse/contracts.py(22)、alpha/cli.py(21)
  static: 2 檔｜webapp/static/app.js(18)、webapp/static/app.js(18)
  skills: 2 檔｜skills/research-drain/SKILL.md(3)、skills/alpha-status/SKILL.md(2)
  tests: 37 檔｜tests/test_implied_return.py(60)、tests/test_full_chain_acceptance.py(35)、tests/test_entry_logic.py(30)、tests/test_alpha_investment_view.py(23)、tests/test_valuation_model.py(23)、tests/test_closure.py(14)、tests/test_reverse_bridge.py(14)、tests/test_variant_scenario.py(14)
  config: 1 檔｜config/engine_c_observation_fields.json(1)
  livedocs: 3 檔｜docs/ARCHITECTURE.md(35)、docs/OPERATIONS.md(17)、CONCEPTS.md(9)
  docs: 26 檔｜docs/archive/roadmap-pre-alpha-edge.md(63)、docs/ARCHITECTURE.md(35)、docs/archive/roadmap-backlog-log.md(21)、docs/ROADMAP.md(19)、docs/OPERATIONS.md(17)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(14)、docs/reports/2026-09-07-coverage-pilot.md(10)、docs/reports/2026-09-07-full-chain-adversarial-acceptance.md(10)

## D 多年反向橋／要幾倍
  code: 18 檔｜briefing/multi_year.py(30)、briefing/alpha_view/sources.py(15)、briefing/alpha_view/builder.py(14)、briefing/cli.py(9)、webapp/__main__.py(8)、briefing/alpha_view/contracts.py(6)、webapp/materialize.py(6)、alpha/models/session_assessor.py(5)
  static: 4 檔｜webapp/static/app.js(4)、webapp/static/app.js(4)、webapp/static/index.html(1)、webapp/static/index.html(1)
  tests: 10 檔｜tests/test_multi_year_artifact.py(14)、tests/test_multi_year_view.py(8)、tests/test_reverse_bridge.py(8)、tests/test_reverse_bridge_ev_to_sales.py(6)、tests/test_brief_multiple_question.py(4)、tests/test_reverse_bridge_multiple.py(4)、tests/test_webapp_ranking.py(4)、tests/test_investor_brief.py(3)
  docs: 6 檔｜docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(23)、docs/ROADMAP.md(20)、docs/archive/roadmap-alpha-edge-2026-09-22.md(18)、docs/archive/roadmap-phase-delivery-log.md(14)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(12)、docs/archive/roadmap-completion-gate-log.md(6)

## E 賭注四價／variant overlay
  code: 26 檔｜webapp/basket.py(47)、briefing/alpha_view/builder.py(39)、briefing/alpha_view/sources.py(9)、briefing/analyst_view/contracts.py(8)、briefing/alpha_view/contracts.py(7)、briefing/analyst_view/compose.py(7)、briefing/alpha_view/render.py(6)、alpha/narrative/argument.py(5)
  static: 2 檔｜webapp/static/app.js(29)、webapp/static/app.js(29)
  skills: 1 檔｜skills/research-drain/SKILL.md(1)
  tests: 24 檔｜tests/test_bet_endgame.py(21)、tests/test_probe_sizing.py(21)、tests/test_webapp_basket.py(13)、tests/test_variant_scenario.py(12)、tests/test_bet_state_opinion_in_base.py(10)、tests/test_brief_downside_symmetry.py(9)、tests/test_weakest_axis.py(8)、tests/test_downside_overlay.py(7)
  config: 2 檔｜config/decision_blockers.json(2)、config/engine_c_observation_fields.json(1)
  livedocs: 3 檔｜docs/ARCHITECTURE.md(4)、CONCEPTS.md(4)、docs/OPERATIONS.md(3)
  docs: 28 檔｜docs/archive/roadmap-alpha-edge-2026-09-22.md(19)、docs/ROADMAP.md(14)、docs/archive/roadmap-backlog-log.md(13)、docs/archive/roadmap-phase-delivery-log.md(10)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(10)、docs/archive/roadmap-completion-gate-log.md(8)、docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(8)、docs/archive/roadmap-pre-alpha-edge.md(7)

## F entry criterion
  code: 17 檔｜alpha/entry/criteria.py(18)、alpha/entry/contracts.py(16)、alpha/cli.py(14)、alpha/providers/entry_criteria.py(14)、alpha/entry/__init__.py(9)、briefing/alpha_view/builder.py(9)、briefing/alpha_view/sources.py(7)、scripts/verify_test_nonvacuity.py(6)
  skills: 1 檔｜skills/alpha-status/SKILL.md(1)
  tests: 3 檔｜tests/test_entry_logic.py(26)、tests/test_analyst_view.py(3)、tests/test_webapp_request_path.py(1)
  livedocs: 2 檔｜docs/ARCHITECTURE.md(4)、CONCEPTS.md(2)
  docs: 6 檔｜docs/archive/roadmap-pre-alpha-edge.md(6)、docs/ARCHITECTURE.md(4)、docs/ROADMAP.md(2)、CONCEPTS.md(2)、docs/archive/roadmap-alpha-edge-2026-09-22.md(1)、docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(1)

## G decision_lab 鑄號／reassess
  code: 67 檔｜engine_b/todo.py(150)、decision_lab/cli.py(24)、decision_lab/brief.py(20)、decision_lab/workflow.py(18)、engine_b/queue_segments.py(16)、crons/daily_brief_prompt.md(13)、scripts/verify_test_nonvacuity.py(13)、decision_lab/store.py(11)
  skills: 5 檔｜skills/daily-brief/SKILL.md(21)、skills/investment-research/SKILL.md(12)、skills/lead-intake/SKILL.md(7)、skills/research-drain/SKILL.md(6)、skills/alpha-status/SKILL.md(3)
  tests: 63 檔｜tests/test_engine_b_todo.py(166)、tests/test_operational_workflow.py(23)、tests/test_private_backup_restore.py(23)、tests/test_decision_lab_e2e.py(21)、tests/test_layer_separation.py(19)、tests/test_standing_authorization.py(13)、tests/test_action_card.py(9)、tests/test_codex_daily_permissions.py(9)
  config: 4 檔｜config/decision_blockers.json(8)、config/authority_tokens.json(5)、config/standing_authorization.json(3)、config/engine_c_observation_fields.json(2)
  livedocs: 3 檔｜docs/OPERATIONS.md(42)、docs/ARCHITECTURE.md(7)、CONCEPTS.md(6)
  docs: 58 檔｜docs/archive/roadmap-pre-alpha-edge.md(44)、docs/OPERATIONS.md(42)、docs/plans/2026-08-28-001-refactor-bottleneck-ranking-terminus-plan.md(42)、docs/plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md(41)、docs/archive/roadmap-pre-alpha-refactor.md(35)、docs/plans/2026-07-22-001-feat-engine-d-operational-workflow-plan.md(32)、docs/refactor/target-architecture.md(32)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(30)

## H 估值模型 valuation/fundamental
  code: 27 檔｜engine_c/estimates.py(15)、scripts/alpha_expectation_gap.py(13)、alpha/providers/fundamentals.py(12)、briefing/alpha_view/builder.py(9)、briefing/alpha_view/changes.py(9)、engine_c/db.py(7)、briefing/alpha_view/sources.py(6)、engine_c/checklist.py(5)
  tests: 29 檔｜tests/test_coverage_pilot_generalization.py(13)、tests/test_valuation_model.py(10)、tests/test_fundamental_model.py(9)、tests/test_reverse_bridge.py(9)、tests/test_absence_semantics.py(8)、tests/test_alpha_expectation_gap.py(8)、tests/test_estimate_revision.py(6)、tests/test_downside_overlay.py(5)
  livedocs: 1 檔｜CONCEPTS.md(1)
  docs: 12 檔｜docs/archive/roadmap-pre-alpha-edge.md(13)、docs/archive/roadmap-backlog-log.md(6)、docs/refactor/current-architecture.md(5)、docs/plans/2026-07-08-004-feat-investment-query-gap-audit-plan.md(4)、docs/ROADMAP.md(3)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(3)、docs/archive/agents-pre-graph-first-2026-09-22.md(1)、docs/refactor/phase-1-plan.md(1)
```

**結案要歸零的是 code／static／skills／tests／config 五區**（`livedocs` 逐句判斷，`docs` 含 archive 不計）。
目前五區沒有一組是 0。

## 2. APP state kind（9 份）

`python -m webapp status`

```text
# Materialized Analyst Views（73 份；有賭注 3 檔；目錄由 STOCKBOT_APP_ARTIFACT_DIR 決定）
…（73 檔逐行省略，見 `python -m webapp status` 全文）
# State artifacts（9 份；目錄由 STOCKBOT_APP_STATE_DIR 決定）
- ranking｜fresh（9.7h）｜current｜可行動 37 條／純結構 37 條
- beta｜fresh（9.7h）｜current｜sleeve 6 格／商品 14 檔
- coverage｜fresh（9.7h）｜current｜🔴 真缺口 9／🟡 建模待補 10／重複節點候選 23（沒人提過）
- watches｜fresh（9.7h）｜current｜在等 90／停滯 37
- positions｜fresh（9.7h）｜current｜逐檔 22／真實成交 1 檔
- basket｜fresh（9.7h）｜current｜16 檔／通過 filter 0／首選 無
- structure_readings｜fresh（9.7h）｜current
- account_scorecard｜stale（113.1h）｜current
- multi_year｜stale（27.4h）｜current
# 每檔閉環
- 段5 每檔閉環：到終局 66（ready 55／settled 7／等財報 4）／未到終局 7｜有 ready 檔的產業 4／5｜下一檔：APO（有共識；EPS 為正；不在瓶頸排序的產業組內；不在瓶頸排序內；已有基期觀測；缺：headline、fundamental、why、research）
```

九個 kind：`ranking`、`beta`、`coverage`、`watches`、`positions`、`basket`、`structure_readings`、
`account_scorecard`、`multi_year`。**0a.2 後應為 7**（少 `basket`、`multi_year`）；
批 3 後 `ranking` 改名 `structure_table`。Materialized analyst view **73 份**（`.meta.json` 不是股票，不計）。

## 3. pq2 待辦池（未結案 19）

`python -m engine_b.todo list`

型別實測（讀 `library/leads/todo_pool.json`，總項目 650）：

| type | 未結案筆數 | 編號 |
|---|---|---|
| `decision_review` | **17** | 200、276、279、348、362、407、421、458、461、492、493、494、495、522、558、640、644 |
| `manual` | **2** | 586、632 |

與 plan §1 的預期（17 ＋ 2 ＝ 19）**相符**。0c 只 drop 上面那 17 個，兩個 `manual` 不動；
結案時 `todo list` 未結案應 = 2。

```text
待辦事項統整（回覆用編號；`<編號…> go｜drop｜pending`）

## decision_review — REVIEW 有兩種成因，逐項 hint 才是準的：有 blocker → go 派回 pq1；無 blocker → 改跑 reassess
  [558] co:unitree：補估值錨點：市值、分析師覆蓋與隱含假設，回答股價已經定價了什麼（已 defer）
        ↳ go＝bounded research（派回 pq1）；不含入圖、Engine C 寫入與 live
        ↳ 當前 missing_data：688836.SS 的價格序列進 Engine C（目前 valuation_payoff 只有 fx、沒有 marke；同期 EPS 共識（新上市、賣方覆蓋未建立）（共 2 項）｜coverage 仍有 blocker：go 會 dispatch 回 pq1 做 bounded research，完成後才 reassess

## pq1 進行中（2 項，不需動作）
  [640] co:vpec：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證（queued：wo_4118848b803612907f43005c82997071）
  [644] co:newphotonics：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證（queued：wo_3d9f3ce1ea028a264bbb675ddd19c3d9）

## 等事件（16 項，觸發前不需動作）
  [200] co:agility_robotics：補客戶端商業承諾：訂單、產能協議或預付款等付錢方向的證據
        ↳ 等：Agility Robotics S-4 由 2026-07-13 機密遞交轉為公開申報並生效，首次揭露歷史財報與 300M+ committed orders 條件
  [276] co:broadcom：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證
        ↳ 等：執行面 context 缺失／財務核驗清單欄位缺失或待人工填入／技術指標觀測問題
  [279] co:micron_technology：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證
        ↳ 等：技術指標觀測問題
  [348] co:nvidia：殘餘缺口——MRM 良率數字改判結構性不可得:TSMC 不揭露 wafer/die 良率,公開唯一量化是 BER<1E-08(process-contr
        ↳ 等：TSMC 或客戶端首次揭露 MRM wafer/die 良率（目前公開唯一量化是 BER<1E-08，屬結構性不揭露）
  [362] co:tsmc：補 counter-path：什麼會讓這條因果鏈斷掉（第二供應源、客戶自製、技術替代）
        ↳ 等：3Q26 財報季 FII/Fabrinet 出貨驗證點(MRM/COUPE 量產爬坡實測)
  [407] co:hyperlight：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證
        ↳ 等：UMC/Wavetek TFLN 量產進度公告、客戶具名、或 [404] 入圖後寫 assessment
  [421] co:proterial：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證
        ↳ 等：任一 OEM/客戶具名採用 Proterial HRE-free 磁石,或 Proterial 揭露量產訂單/重新上市
  [458] co:google：補估值錨點：市值、分析師覆蓋與隱含假設，回答股價已經定價了什麼
        ↳ 等：GOOGL 價格序列進 Engine C ETL（上游資料缺口，bounded research 解不掉；真要解是開發項，載體 ROADMAP）
  [461] co:soitec：殘餘缺口——產能保留協議任一對手方具名(客戶端或法定文件)
        ↳ 等：Soitec 或其產能保留協議的任一對手方在法定文件／客戶端揭露裡首次具名（現況：協議存在但對手方全部未具名）
  [492] co:niron_magnetics：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證
        ↳ 等：Niron Magnetics 任何法定財報／S-1 出現（watch ew_0080 兜底；原 [466] 已 park：未上市、財務軸結構性不可解）
  [493] co:ewellix：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證
        ↳ 等：Schaeffler 一手揭露 Ewellix／行星滾柱螺桿營收拆分（watch ew_0081；原 [467] 已 park）
  [494] co:nabtesco：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證
        ↳ 等：Nabtesco 有価証券報告書『主要な販売先』或客戶端具名揭露（watch ew_0082；原 [459] 已 park：短信不揭露客戶集中度）
  [495] co:schaeffler：補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證
        ↳ 等：Schaeffler AR 2026 客戶結構或人形夥伴訂單金額（watch ew_0083；原 [460] 已 park：半年報不揭露）
  [522] co:nidec：補客戶端商業承諾：訂單、產能協議或預付款等付錢方向的證據
        ↳ 等：2026-09-30；第53期(2026/3期)有価証券報告書提出（法定期限 2026-06-30，公司 2026-06-16 公告申請延長至 2026-09-30）——相手先別販売実績與受注残高只存在於這份尚未提出的文件；同時第三者委員会已查出多拠点會計不正、過年度決算訂正進行中，既有第52期數字亦在更正範圍
  [586] 上詮 co:foci→tech:fiber_attach_unit 補 substitutability：等客戶端具名確認
        ↳ 等：Himax 或上詮 CPO 光纖陣列長約對手方在客戶端／法定文件首次具名確認上詮為該元件供應商（現況：一手只有上詮自述目標與產能投資，媒體報導依 C1 維持待判定）
  [632] SIVE.ST 的 B 路只剩一道門（qualification_status: sampling → qualified／designed_in），而沒有任何 watch 在等它
        ↳ 等：Sivers 期中／年報揭露 CW DFB／DWDM laser array 進入量產或客戶具名（qualification_status: sampling → qualified／designed_in）
```

佇列段計數 `python -m engine_b.cli counts`：

```json
{"triaged_no_go": 555, "applied": 85, "parked": 488, "triaged_go": 3}
```

## 4. 全測試基準

`python -m pytest -q`

```text
2823 passed, 1 skipped, 1 warning in 398.91s (0:06:38)
```

- 測試檔數：**226**（`ls tests/test_*.py | wc -l`）
- 結案 gate 1 的比對式：**結案時的測試檔數 ＝ 226 − 刪除的測試檔數**，且每刪一檔要列出它守的是哪個退役機制。

## 5. 六條 invariant（13 項檢查全綠）

`python -m audit invariants`

```text
PASS    Identity             圖 92 家全部在 registry 內（registry 另有 8 家尚未入圖，屬正常） [100 筆]
PASS    Duplicates           registry 100 家無 ticker／alias 碰撞 [100 筆]
PASS    Lifecycle            lifecycle epoch 與待辦池結案狀態一致 [663 筆]
PASS    Expiry               90 個進行中的等待全部有到期日 [90 筆]
PASS    Orphans              24 個跨檔引用全部解析得到 [24 筆]
PASS    QueueLiveness        22 項進行中工作全部在 14 天內有進展 [22 筆]
PASS    QueueSegments        pending_triage=0；fired_lead_requeue=0；fired_pq2_wake=0；fired_hypothesis_check=0；reassess_stale=0；approved_work_orders=2；triaged_go_leads=3；forward_view_backlog=11；coverage_gaps=未讀到；duplicate_node_candidates=未讀到；stale_structure_readings=未讀到；pollable_watches=17；gated_gate_resolved=0；gated_no_pointer=0 [1876 筆]
PASS    GateDiscrimination   三條 lane 64 個 gate 量過觸發率、其中 24 個樣本夠也量得出清除率（349 份 assessment、47 個 cohort）：沒有恆亮（≥95%）也沒有不會滅（≤5%）的 [64 筆]
          ⚠ 40/64 個 gate 樣本不足，清除率無從判斷（<5 個 cohort 有過後續評估）——**不當作通過也不當作失敗**：coverage:best_source_missing（觸發 0.6%，只有 1 個 cohort 有清除機會）、coverage:causal_path_missing（觸發 0.6%，只有 1 個 cohort 有清除機會）、coverage:financial_quarantined（觸發 1.1%，只有 2 個 cohort 有清除機會）、coverage:graph_company_missing（觸發 4.0%，只有 4 個 cohort 有清除機會）、coverage:identity_unresolved（觸發 4.3%，只有 4 個 cohort 有清除機會）、coverage:independent_source_missing（觸發 3.4%，只有 3 個 cohort 有清除機會）、live:execution_fx_stale（觸發 0.6%，只有 1 個 cohort 有清除機會）、live:execution_market_adv_invalid（觸發 1.4%，只有 1 個 cohort 有清除機會）…
PASS    PointInTime          SourceDoc published_at 205/218（94.0%）；EdgeAssertion 可定日 664/681（97.5%）；已回填 22 份且 basis 全部指得回去 [921 筆]
          ⚠ 13 份 SourceDoc 仍未定日，擋住 17 條 EdgeAssertion——它們在任何 as-of 查詢裡都會被排除並計為 undated（L11-5：留 null 比猜一個日期誠實）。查證：python scripts/backfill_source_dating.py --list
          未定日：damnang_poet_ofc2026_review_2026_03（擋住 3 條）
          未定日：silicon_matter_sivers_ayar_2026_03_14（擋住 3 條）
          未定日：aehr_official_sipho_test_2026（擋住 1 條）
          未定日：cohr_lpe_garnet_faraday_ds_2026（擋住 1 條）
          未定日：hds_us_technology_sub_20260903（擋住 1 條）
          未定日：hyperlight_official_tfln_2026（擋住 1 條）
PASS    EvidenceProvenance   1 份 signal 的 3 個分數全部指得回證據 [3 筆]
PASS    GraphFinancialJoin   圖中 92 家可 join，另 27 家為私人公司（ticker=None 是明確標記，不是缺漏） [92 筆]
PASS    AlphaLineage         1 份 signal 都帶 context digest [1 筆]
          ⚠ ResearchContext 尚未持久化（無 contexts/ 目錄），本次只驗了 digest 存在與格式——**不等於 lineage 完整**。⚠ 這個缺口與 as-of 投影無關（投影已於 Phase 6 落地並由 PointInTime check 驗證）：缺的是把 ResearchContext 落地成可解析的檔案。
PASS    DecisionLineage      349 筆決策全部追得回凍結的 context bundle [349 筆]

總計 13 項｜FAIL 0｜SKIPPED 0｜PASS 13｜共檢查 4305 筆
```

**兩個要跟著 Phase 0 走的數字：** 進行中的等待 **90**（`Expiry`）、事件監看總數 **95**
（`library/leads/event_watches.json`：active 90 ／ consumed 5）。plan 結案 gate 7 的「watches 95 筆仍在」指的是這個 95。

## 6. 舊 Decision Store（A5，只准讀）

```text
backup_pre_v8_20260818T021452.db  sha256=e887b3d458621e4cd7bb66913690d47d263d7188f9bbc1bacb4bc16ec57de350  live_choices=0  bytes=4804608
backup_pre_v9_20260902T032020Z.db  sha256=af3dc690ce836b6026d86946c388d19f1500139287469f0f9fbe8711c4819d39  live_choices=1  bytes=11038720
decision_lab.db  sha256=e99d1c79fd22dbe1099f30c4e06f2d1188f26a8cbfa987a27cd8842530951810  live_choices=1  bytes=16166912
```

**結案時三個檔的 sha256 與 `live_choices` 必須逐字相同。** `decision_lab.db` 的 `live_choices` = 1 是歷史唯一一筆。

## 7. 個股頁文字 digest（結案 gate 3 與 R2 檢查 7 的比對基準）

gate 3 要求「materialize 前後，73 檔的 `brief`／`why`／`research` 面板**文字**不變」。
沒有固定配方就比不出來，所以本 Step 加了一支唯讀腳本 `scripts/analyst_view_text_digest.py`：
**只 hash 敘事文字**（`title`／`display_label`／`datum` 的 `value`・`text`・`label`・`note`・`reason`／`notes`／`questions`），
不 hash 數字、時戳、`dependencies` payload——那些本來就隨刷新而動，算進去會讓 gate 永遠紅、於是永遠被忽略。

`python scripts/analyst_view_text_digest.py`

```text
# analyst view 文字 digest（73 檔；目錄 C:\Users\Cheng\code\StockBotv2\library\private\app\analyst_view）
# 只 hash 敘事文字：title／display_label／datum 的 value・text・label・note・reason／notes／questions
000660.KS	ff950633836bdd3b	our_bet=0／brief=32／why=87／research=58
002472.SZ	126c2401c3a60fe2	our_bet=0／brief=32／why=87／research=58
005930.KS	60d9fb9eee3aa3ce	our_bet=0／brief=32／why=88／research=58
012330.KS	5f94f6afec4c3430	our_bet=0／brief=32／why=88／research=59
2301.TW	736e6be2f20359a2	our_bet=0／brief=32／why=87／research=59
2455.TW	de0d967c722e3daf	our_bet=0／brief=32／why=88／research=63
300308.SZ	0942ce2014054d1d	our_bet=0／brief=32／why=87／research=59
3081.TWO	dc2d3d830a26b129	our_bet=0／brief=32／why=87／research=58
3105.TWO	76bccd8a7c11eaaa	our_bet=0／brief=32／why=88／research=58
3363.TWO	9b2f72c6698801a4	our_bet=0／brief=32／why=78／research=58
4971.TWO	aa31630500ed6c3b	our_bet=0／brief=32／why=87／research=58
4979.TWO	c0c162b7f948b5be	our_bet=0／brief=32／why=93／research=58
5016.T	f39de170cfd568fa	our_bet=0／brief=32／why=87／research=58
5802.T	cb5f3c8c027add22	our_bet=0／brief=32／why=88／research=58
6268.T	8f98e9ce7679488f	our_bet=0／brief=32／why=34／research=74
6324.T	009f97ec5fff11b8	our_bet=0／brief=32／why=54／research=60
6481.T	8f4d7ddf7777747f	our_bet=0／brief=32／why=87／research=66
6594.T	67c1c9d4b7dc79a6	our_bet=0／brief=32／why=34／research=74
6680.HK	0ebe2595ae3b3799	our_bet=0／brief=32／why=90／research=58
688017.SS	d85bd1591f70ae12	our_bet=0／brief=32／why=88／research=60
688836.SS	fae3e31b9cd42891	our_bet=0／brief=32／why=34／research=64
AAOI	b84286fa06001777	our_bet=0／brief=32／why=51／research=58
AAPL	043aa5374381382c	our_bet=0／brief=32／why=88／research=59
AEHR	edbea2d88f513f29	our_bet=0／brief=32／why=87／research=58
AEVA	df85049932652996	our_bet=0／brief=32／why=84／research=58
AMAT	871cc1c21b22334d	our_bet=0／brief=32／why=88／research=58
AMD	25d5e37a16a63d1c	our_bet=0／brief=32／why=88／research=58
ANET	9393acdf51677084	our_bet=0／brief=32／why=87／research=58
APO	97bfb1ca9984faea	our_bet=0／brief=32／why=34／research=62
AVGO	c90756b43a0bf698	our_bet=0／brief=32／why=88／research=58
AXTI	681787cd9d4837d2	our_bet=1／brief=35／why=78／research=59
BX	d5bf6cc85c45212e	our_bet=0／brief=32／why=34／research=62
CCXI	12ceaf9a645e0cd7	our_bet=0／brief=32／why=34／research=60
CDNS	7d1dfd5c304ced9c	our_bet=0／brief=32／why=87／research=58
COHR	03166b11e44f778c	our_bet=1／brief=35／why=92／research=64
CRWV	d3760edeabb27bc2	our_bet=0／brief=32／why=78／research=58
ENA.V	977367f17c3ce726	our_bet=0／brief=32／why=34／research=60
FN	a9060da3ca11f7b2	our_bet=0／brief=32／why=87／research=58
GFS	0560e9334055ca29	our_bet=0／brief=32／why=88／research=58
GLW	588c2fc069a83c28	our_bet=0／brief=32／why=87／research=58
GOOGL	39e1e4929815398a	our_bet=0／brief=32／why=92／research=58
GXO	163187fbe8f74e01	our_bet=0／brief=32／why=87／research=58
HEXA-B.ST	734389f9dc85cdec	our_bet=0／brief=32／why=90／research=58
HIMX	f46c67504d24dd59	our_bet=0／brief=32／why=88／research=58
INTC	5f8f18c02e466adc	our_bet=0／brief=32／why=88／research=58
IQE.L	fda81f7c6c57984d	our_bet=0／brief=32／why=51／research=58
IREN	16fc378fe0a988ed	our_bet=0／brief=32／why=78／research=61
JBL	97bfb1ca9984faea	our_bet=0／brief=32／why=34／research=62
LITE	ab1474827b82e31a	our_bet=1／brief=32／why=88／research=80
LRCX	ad8a68d4c7b7b0a4	our_bet=0／brief=32／why=87／research=58
LYC.AX	d6d6cde4330d99bb	our_bet=0／brief=32／why=88／research=62
META	ea9db0afb8edead5	our_bet=0／brief=32／why=88／research=58
MP	5f150c5e226b4655	our_bet=0／brief=32／why=51／research=60
MRVL	041ca7d7ccb9cacc	our_bet=0／brief=32／why=88／research=58
MSFT	60fb442f7ee840c8	our_bet=0／brief=32／why=87／research=58
MTSI	9984ae1257688adb	our_bet=0／brief=32／why=88／research=58
MU	5805e4c551bacd65	our_bet=0／brief=32／why=34／research=63
NBIS	e4468d077cb21d06	our_bet=0／brief=32／why=78／research=59
NOVT	802fa42bf9f51ed7	our_bet=0／brief=32／why=88／research=58
NVDA	bb4f2055c0c4a141	our_bet=0／brief=32／why=87／research=58
ORCL	243ced313ba580f9	our_bet=0／brief=32／why=92／research=58
POET	dfb43ad3eb97e3f5	our_bet=0／brief=32／why=51／research=58
SHA0.DE	ee1ee9119782e8a4	our_bet=0／brief=32／why=34／research=62
SIVE.ST	8d980944000869c2	our_bet=0／brief=32／why=78／research=57
SNDK	ddb65b6b1550220c	our_bet=0／brief=32／why=88／research=58
SOI.PA	d525402efcd2584c	our_bet=0／brief=32／why=84／research=59
TSEM	124b4a9fecdf59a0	our_bet=0／brief=32／why=88／research=60
TSLA	48b7d0290382874c	our_bet=0／brief=32／why=87／research=60
TSM	1ab61b38fd001bda	our_bet=0／brief=32／why=34／research=58
TXN	111e8cd065d2d2b4	our_bet=0／brief=32／why=87／research=58
UMC	6d4fc6a789214ba0	our_bet=0／brief=32／why=88／research=58
XFAB.PA	434826de862712ca	our_bet=0／brief=32／why=84／research=58
XPEV	156a8c5439862413	our_bet=0／brief=32／why=84／research=58
# TOTAL	c3358d25e7fd4c32	73 檔
```

**TOTAL digest 是結案時的單一比對值。** 逐檔 digest 讓「哪一檔的文字被改到」指得出來。

> ⚠ **已發現的張力，0b.1 必須先處理（可能是 `SCOPE_ESCALATION`）：**
> `why` 面板現在的標題是「怎麼算到這裡：假設、敏感度、算式、證據」，33 條 line 幾乎全是估值鏈的
> 假設與 `fair_value`／`gap`。plan 要 `why` 留在核心面板且文字不變，但批 2 要刪掉餵它的估值鏈——
> **兩者不可能同時成立。** 0b.1 動手前要先答：`why` 面板退役後的主詞是什麼（讀圖？敘事？），
> 還是它其實屬於稽核區。這是 plan §6「切不開就停」的候選。

## 8. 心跳基準（五段照印）

`python -m crons.heartbeat`

```markdown
# Daily 心跳 — 2026-09-22 15:35 台北標準時間

> 零 LLM、零網路：只讀本機 authority 與已 materialize 的 state。**不判讀、不研究、不下單。**
> 它回答「系統還活著、這些數字是多少」；要決定什麼、要研究什麼不在這裡。

## 1. 資料新鮮
- harvest 來源 36 個｜失敗 0 個｜最後一輪 2026-09-22 05:33
- 本月 X 花費 $0.06 / 上限 $10.00
- 行情 14 檔｜最新完整交易日 2026-09-18 ～ 2026-09-21｜降級 3 檔：006208.TW（quarantined）、00981A.TW（quarantined）、DRAM（insufficient_history）
- 台股月營收 7/7 檔｜最新 2026-08｜已跟上公告期限
- FX 觀測 4 檔｜最新 as_of 2026-09-21（1 天前，容忍 ±3 天）｜全部在窗內
- APP artifact 今天已 materialize 7 份｜**不是今天的 2 份**：account_scorecard、multi_year

## 2. 變了什麼
- 事件監看：本輪該查 2｜已觸發未消費 0｜到期 0
- thesis：active 2、revised 1｜該核查 0 檔
- 現價已高於目標價（**提醒不是動作**，D3：`realized` 不觸發出場）：AXT, Inc.、Coherent Corp.、GlobalFoundries Inc.、Lynas Rare Earths Ltd.、SK hynix Inc.、Tower Semiconductor Ltd.、co:soitec（SOI.PA）
- 結構讀圖 2 份｜現行 2｜**該重讀 0**（stale 0／過期 0；低級 0 不進佇列）
- 目標倍數背離：**19 檔超過 5%**（在帶內 26｜不適用 1｜比不了 2）：INTC -17.3%、AMD -16.0%、4979.TWO -14.1%、META -12.8%、688017.SS -12.1%…——宣告零折溢價卻背離，**要嘛重新校準、要嘛寫出折溢價的證據**
- beta 報告狀態 degraded｜警告 4 條：drawn_debt_present、issuer_concentration_warning:TSMC、issuer_lookthrough_partial、unclassified_holdings_assumed_unlevered_direct_issuer

## 3. 佇列
- **未 triage 0**｜新 harvest lead 需要分流（零＝真的沒有，不是沒跑）｜分類層每日上限 30
- pq1 可做 5｜機械段待清 0
- **pq2 球在你手上 1**｜池中未結案 19（差額＝等事件或已在 pq1 跑）
- 到期歸檔 watch 0｜事件監看總數 95｜無到期的等待 0

## 4. 部位
- alpha（瓶頸研究衛星）占已投入非現金 1.77%｜**只觀測不設目標**（D1）
- 追蹤表 22 檔｜等權絕對 8.72%｜對 QQQ 超額 4.64%｜正式結算過 2 筆
- 入圖前已漲（chasing）8/22 檔
- 籃子 16 檔｜有賭注 3｜刻意不主張 0｜**欠一個答案 10**｜觀點已在 base、待決定 overlay 3：AVGO、IQE.L、MP、TSM、TSEM、GFS、MU、POET…
- 要幾倍（多年視角）16 檔｜算得出 2｜**還沒寫下目標年度 13**：AVGO、LITE、SOI.PA、IQE.L、MP、TSM、TSEM、GFS…｜沒有判斷檔 1
- 量的候選 15 家（已研究、低於門檻）｜通過條件 0｜**欠一個答案 4**｜觀點已在 base、待決定 overlay 8：5802.T、6268.T、GFS、SHA0.DE
- 可投資排序 37 列分佈在 8 個需求錨（前三：tech:ai_switch 15、tech:optical_scale_up 9、tech:essential_chips_mature_node 6）——**N 檔不等於 N 個獨立機會**
- power-law：籃子總報酬 8.72%｜最大單檔 AXTI 3.95%／其餘 21 檔 4.77%｜曾達 2 倍 1/22（現價仍達 0）｜**還沒有一檔滿 12 個月**（最長持有 62 天）
- 賭注收斂（共識朝我們移動了嗎）：有賭注 3 檔｜朝我們 0｜反向 0｜共識沒動 2｜**賭注寫下後還沒有共識抓取 1**｜已觀測 1–3 天　←窗短時「沒動」幾乎是必然，不是市場否定了我們
- **alpha 全歸零淨值少 1.65%**（alpha 佔 NAV 的比例本身；純呈現、零門檻，尺寸仍由使用者決定）
- 歸零旗標 16 檔 × 4 盞：紅 2｜黃 8｜綠 20｜**灰（沒量到）34**——⚠ 灰不是綠；有紅燈：COHR、IQE.L

## 5. 帳號計分表
- 計分表是 weekly 才算的，本輪是 daily（method_not_applicable）
```

**五段標題：** 1 資料新鮮／2 變了什麼／3 佇列／4 部位／5 帳號計分表。結案時五段必須都還在。

> ⚠ **plan 0a.2 的描述與實際位置有落差：** plan 寫「段 2 的『現價過目標價』與籃子行」，
> 但實測「現價已高於目標價」在**段 2**，籃子／要幾倍／量的候選／可投資排序／賭注收斂等行在**段 4**。
> 0a.2 要改的是這兩段，換成 `not_yet_recorded` 的一行，不是只改段 2。

## 附錄：本次實跑的命令

```bash
python scripts/retired_mechanism_grep.py
python -m webapp status
python -m engine_b.todo list
python -m engine_b.cli counts
python -m pytest -q
python -m audit invariants
python scripts/analyst_view_text_digest.py
python -m crons.heartbeat
ls tests/test_*.py | wc -l
python - <<'EOF'
import hashlib,glob,sqlite3,os
for p in sorted(glob.glob('library/private/decision_lab/*.db')):
    print(os.path.basename(p), hashlib.sha256(open(p,'rb').read()).hexdigest(),
          sqlite3.connect(p).execute('select count(*) from live_choices').fetchone()[0])
EOF
```

```powershell
Get-ScheduledTask | ForEach-Object { $t=$_; $_.Actions | ForEach-Object {
  if ("$($_.Execute) $($_.Arguments)" -match 'StockBot|codex') {
    [pscustomobject]@{Task=$t.TaskName; State=$t.State; Cmd="$($_.Execute) $($_.Arguments)"} } } }
Get-ScheduledTask -TaskName 'StockBotv2-Heartbeat','StockBotv2-FxSync' | Get-ScheduledTaskInfo
```
