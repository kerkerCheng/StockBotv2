# Phase 0 拆——結案報告（2026-09-23）

> plan：[`docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md`](../plans/2026-09-22-001-refactor-phase0-retire-plan.md)；
> 基準：[`2026-09-22-phase0-baseline.md`](2026-09-22-phase0-baseline.md)；決定紀錄 G1–G12：
> [`docs/brainstorms/2026-09-22-graph-first-direction-decision.md`](../brainstorms/2026-09-22-graph-first-direction-decision.md)。
> 本檔每個數字都附查證命令；數的全是**機制存在與否**（kind 數、命中數、sha256、pq2 數、測試數），沒有一個是研究結果。

## 0. Phase 0 做了什麼（20 個 commit，2026-09-22 → 09-23）

| Step | commit | 一句話 |
|---|---|---|
| 0.0 | d6e3fca | 基準快照（八組殭屍 grep、9 kind、pq2 19、2823 測試、Store sha256、73 檔文字 digest） |
| 0a.1–0a.4 | 36f59f9／b65c1a1／4c78df4／20f21a4 | 停跑：排程與 rules（14 → 12 條）、心跳與 APP 入口（9 → 7 kind）、七個 skill 改句、池子停鑄 |
| 0c | cd275e3 | pq2 17 筆 decision_review 批次 drop（未結案 19 → 2） |
| 0b.1a | e38c7ee | 個股頁消費層：`why` 退役、`argument` 升核心、那把尺與四價下架 |
| 0b.1b-D／F／E | 2fb7960／c1d0331／bd34a63 | 多年反向橋、entry criterion、賭注四價整組退役 |
| 0b.1b-C/H | 3be1756／1ed420e | 估值品質計數器退役；樞紐拆除（6 個估值 section、`alpha/valuation`／`implied_return`／FY+1 橋刪） |
| 0b.2 | d796e2f | 估值鏈收尾（expectation_gap 腳本、`multiple_horizon` 讀寫） |
| 0b.3 | 7db4e1f | 排序與籃子退役：`rank_bottlenecks` → `structure_table`、kind `ranking` → `structure_table`、籃子模組刪 |
| 0b.4（1/3） | 8d62c11 | 硬擋搬家：5% 單筆與 ETF 槓桿 cap 搬進 `scripts/record_trade.py`（`risk/hard_caps.py`） |
| 0b.4（2/3） | 27007f9 | decision_lab 研究側退役：12 個模組＋`engine_d_runtime`＋today brief 組裝刪、舊店凍結、28 個測試檔跟機制走 |
| 0b.4（3/3） | aa92bb1 | config 散文、活文件封存（9 段逐字進 archive）、keep-list 53 → 288 條 |

## 1. 九項 completion gate

| # | gate | 結果 | 查證 |
|---|---|---|---|
| 1 | `pytest -q` 全綠，測試數與基準的差＝刪除的測試檔 | ✅ **2180 passed, 1 skipped**（基準 2823 passed）；刪 **52 檔**＋改名 2 檔（逐檔守什麼見 §2） | `python -m pytest -q`；`git log --diff-filter=D --name-only --pretty=format: d6e3fca..HEAD -- tests/ \| sort -u` |
| 2 | `python -m audit invariants` 綠 | ✅ 13 項 PASS／0 FAIL（共檢查 4288 筆） | `python -m audit invariants` |
| 3 | materialize 前後 73 檔 `brief`／`argument`／`research` 文字不變 | ✅ materialize 79/79 成功（73 檔＋6 個 state kind）；**73/73 檔**的 `brief`／`argument`／`research` 逐面板 digest 前後**逐字相同**（0 個面板不同）。與基準的差異只有 0b.1a／0b.3 已記錄的：`why` 面板退役（§0.8 裁決 A）、`argument` 由六段變三段（§0.6 #27）、COHR／GFS 的「鏈」段同分邊列舉順序（§0.6 #41） | `python scripts/analyst_view_text_digest.py --per-panel` 前後比對（`argument` 的「鏈」段同分邊列舉順序差異見 plan §0.6 #41） |
| 4 | 無新 dual authority：`record_live_choice(` 呼叫端＝0 | ✅ 0 個呼叫端（只剩 store.py 自己的 docstring 與 keep-list 理由）；`record_live_choice`／`record_live_fill` 直接 raise `FrozenStoreError` | `grep -rn "record_live_choice(" --include=*.py .` |
| 5 | 心跳五段照印；拿掉的段落印 `not_yet_recorded` | ✅ 五段標題都在；段 2「候選狀態板未落地（not_yet_recorded）」「已定價嗎（財務三題）未落地（not_yet_recorded）」；段 4「賭注帳／量的候選／要幾倍…（not_yet_recorded）」 | `python -m crons.heartbeat --out <temp>` |
| 6 | Point-in-time 測試綠 | ✅ 含在全測試（`tests/test_alpha_point_in_time.py`、`test_alpha_as_of_projection.py`、`test_alpha_view_as_of_cohr.py`）；audit `PointInTime` PASS | 同 1、2 |
| 7 | lifecycle 可達：pq2 未結案 2；watches 95 | ✅ pq2 未結案 **2**（[586]、[632]，皆 `manual`）；watches **95**（active 90／consumed 5）；新鑄 `source=decision_lab` 自 2026-09-23 起 **0** | `python -m engine_b.todo list`；`library/leads/event_watches.json`；`todo_pool.json` 的 `added_at` |
| 8 | 殭屍 grep 差集：未列 keep-list 的（檔，組）＝0、已列但不再命中＝0、理由類別全合法 | ✅ **0／0／0**；keep-list **288** 條（A／B 53、C 49、D 15、E 36、F 5、G 95、H 40 扣重複）；輸出見 §3 | `python scripts/retired_mechanism_grep.py` |
| 9 | 驗收數的是機制存在與否 | ✅ 本檔每個數字都是 kind 數／命中數／sha256／pq2 數／測試數 | — |

**ROADMAP Phase 0 驗收①–⑥：** ①差集歸零（gate 8）✅；②新鑄 `source=decision_lab` 0 ✅；③`webapp status` 7 kind、無 `multi_year`／`basket`（也無 `ranking`）✅；
④心跳五段照印、段 2 印候選狀態板未落地 ✅；⑤Decision Store sha256 前後相同、`live_choices` 仍為 1（§4）✅；⑥`record_trade.py` dry-run 對超 5% 成交 fail closed（`tests/test_record_trade.py::test_dry_run_over_five_percent_fails_closed_without_touching_sheet_or_log`）✅。

## 2. 刪除的測試檔逐檔守什麼（52 檔＋2 改名；硬約束 9）

| commit | 檔 | 守的退役機制 |
|---|---|---|
| 2fb7960（D） | test_reverse_bridge、test_reverse_bridge_ev_to_sales、test_reverse_bridge_multiple、test_multi_year_artifact、test_multi_year_view、test_brief_multiple_question、test_bridge_span_years | 多年反向橋（`alpha/reverse`）、`multi_year` kind／view、短評「要翻倍需要什麼為真」那一句、跨年橋 |
| c1d0331（F） | test_entry_logic | entry criterion／門檻價（`alpha/entry`） |
| bd34a63（E） | test_bet_endgame、test_bet_state_opinion_in_base、test_brief_downside_symmetry、test_downside_overlay、test_variant_scenario | 賭注四價 overlay、下檔對稱、目標價到了沒、variant 情境的 payoff 算術 |
| 1ed420e（C／H） | test_implied_return、test_valuation_model、test_fundamental_model、test_target_multiple_drift、test_alpha_view_sources | 隱含報酬模型、估值模型、FY+1 因果橋、目標倍數背離、樞紐取數層的估值／horizon ledger 執行 |
| d796e2f（C） | test_alpha_expectation_gap | `scripts/alpha_expectation_gap.py`（內部 vs 共識 gap 腳本） |
| 7db4e1f（A／B） | test_webapp_basket、test_basket_screen_thresholds、test_ranking_view、test_alpha_backtest、test_catalyst_shape_reasons | 籃子頁與門檻、`ranking` kind／pane、排序前後段回測、籃子 filter 的催化劑形狀理由 |
| 27007f9（G） | test_decision_lab_e2e、test_operational_workflow、test_operational_cli、test_decision_lab_cli、test_action_card、test_decision_brief、test_decision_brief_mcp、test_decision_context、test_decision_execution、test_decision_outcomes、test_closed_loop、test_coverage_gate、test_coverage_severity、test_live_lane_reachable、test_probe_sizing、test_weakest_axis、test_signal_intake、test_shadow_backfill、test_shadow_baseline、test_shadow_expiry_clock、test_workflow_snapshot_failure、test_holdings_fetch_failure、test_engine_d_runtime、test_alpha_signal_adapter、test_decision_review_title、test_decision_review_churn、test_optional_branches、test_cohort_without_subject | Engine D 研究側：evaluate-signal／reassess／today／card 工作流、action card、decision brief（含 MCP 工具）、context 凍結、coverage gate 與嚴重度、live lane 的 store 寫入、五軸 sizing 與最弱軸、signal intake、shadow 建立／回填／到期、runtime provider、alpha→五軸 adapter、decision_review 標題與 churn、cohort 無主詞抑制 |
| 改名（7db4e1f） | test_bottleneck_ranking → test_structure_table；test_webapp_ranking → test_webapp_structure_table | 活的斷言（三態、去重、證據上限、逐格相等）改主詞為結構表 |

活機制的測試沒有刪斷言；改主詞的檔（`test_layer_separation`、`test_engine_b_todo`、`test_standing_authorization`、`test_alpha_view_brief`、`test_today_first_screen`、`test_backup_entrypoint`、`test_engine_c_observation_fields`、`test_external_data_validation`、`test_account_scorecard`、`test_routine_prompts`、`test_daily_brief_skill`、`test_graph_mcp_manual`、`test_config_tracking`、`test_engine_b_cli`、`test_decision_blockers`、`test_no_llm_api_dependency`）逐條見各 Step 的八欄與 plan §0.6。

## 3. 殭屍 grep（gate 8 輸出）

```text
## A 排序當驅動／首選
  code: 15 檔｜alpha/providers/graph_neo4j.py(5)、query/bottleneck.py(5)、webapp/materialize.py(4)、webapp/api.py(3)、crons/daily_brief_prompt.md(3)、webapp/contracts.py(2)、engine_b/cli.py(2)、thesis/lifecycle.json(2)
  static: 2 檔｜webapp/static/app.js(2)、webapp/static/app.js(2)
  skills: 3 檔｜skills/alpha-status/SKILL.md(8)、skills/daily-brief/SKILL.md(4)、skills/system-decompose/SKILL.md(1)
  tests: 6 檔｜tests/test_webapp_structure_table.py(10)、tests/test_structure_table.py(9)、tests/test_alpha_view_brief.py(1)、tests/test_daily_brief_skill.py(1)、tests/test_webapp_api.py(1)、tests/fixtures/golden/structural_bottleneck.json(1)
  config: 2 檔｜config/alpha_screen.json(1)、.agents/skills/alpha-status/SKILL.md(1)
  livedocs: 1 檔｜docs/ARCHITECTURE.md(7)
  docs: 34 檔｜docs/archive/roadmap-pre-alpha-refactor.md(14)、docs/archive/roadmap-pre-alpha-edge.md(13)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(12)、docs/ROADMAP.md(11)、docs/archive/roadmap-phase-delivery-log.md(11)、docs/archive/roadmap-alpha-edge-2026-09-22.md(10)、docs/brainstorms/2026-09-22-graph-first-direction-decision.md(10)、docs/brainstorms/2026-09-17-no-evidence-case-zoom-out.md(8)
## B 籃子 filter
  code: 10 檔｜scripts/outcome_if_settled_today.py(17)、crons/heartbeat.py(9)、webapp/materialize.py(5)、webapp/contracts.py(3)、alpha/abstention/contracts.py(2)、alpha/providers/market_normalization.py(2)、crons/daily_brief_prompt.md(2)、alpha/gap_closure.py(1)
  static: 2 檔｜webapp/static/app.js(6)、webapp/static/app.js(6)
  skills: 3 檔｜skills/daily-brief/SKILL.md(3)、skills/alpha-status/SKILL.md(1)、skills/lead-intake/SKILL.md(1)
  tests: 10 檔｜tests/test_opinion_stance.py(6)、tests/test_wipeout_flags.py(6)、tests/test_heartbeat.py(4)、tests/test_routine_prompts.py(3)、tests/test_webapp_positions.py(2)、tests/test_absence_semantics.py(1)、tests/test_market_quote_unit.py(1)、tests/test_nav_exposure.py(1)
  config: 2 檔｜config/alpha_screen.json(3)、config/sector_anchors.json(1)
  livedocs: 3 檔｜docs/ARCHITECTURE.md(5)、CONCEPTS.md(3)、docs/OPERATIONS.md(1)
  docs: 29 檔｜docs/archive/roadmap-phase-delivery-log.md(40)、docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(31)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(31)、docs/archive/roadmap-backlog-log.md(30)、docs/ROADMAP.md(28)、docs/brainstorms/2026-09-17-no-evidence-case-zoom-out.md(24)、docs/archive/roadmap-alpha-edge-2026-09-22.md(18)、docs/reports/2026-09-22-phase0-baseline.md(15)
## C 估值／隱含報酬／尺
  code: 27 檔｜alpha/fundamental/contracts.py(13)、briefing/alpha_view/builder.py(12)、alpha/fundamental/assumptions.py(8)、briefing/analyst_view/compose.py(8)、briefing/analyst_view/contracts.py(6)、briefing/alpha_view/contracts.py(5)、webapp/materialize.py(5)、crons/heartbeat.py(5)
  static: 2 檔｜webapp/static/app.js(6)、webapp/static/app.js(6)
  skills: 2 檔｜skills/alpha-status/SKILL.md(2)、skills/research-drain/SKILL.md(1)
  tests: 17 檔｜tests/test_webapp_materialize.py(14)、tests/test_refresh_engine.py(12)、tests/test_webapp_api.py(12)、tests/test_alpha_investment_view.py(11)、tests/test_analyst_view.py(8)、tests/test_full_chain_acceptance.py(7)、tests/test_gap_closure.py(5)、tests/test_opinion_stance.py(5)
  config: 1 檔｜config/engine_c_observation_fields.json(1)
  livedocs: 3 檔｜docs/ARCHITECTURE.md(19)、CONCEPTS.md(9)、docs/OPERATIONS.md(5)
  docs: 29 檔｜docs/archive/roadmap-pre-alpha-edge.md(63)、docs/archive/2026-09-23-phase0-retired-sections.md(35)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(33)、docs/archive/roadmap-backlog-log.md(21)、docs/ARCHITECTURE.md(19)、docs/ROADMAP.md(19)、docs/reports/2026-09-07-coverage-pilot.md(10)、docs/reports/2026-09-07-full-chain-adversarial-acceptance.md(10)
## D 多年反向橋／要幾倍
  code: 10 檔｜briefing/analyst_view/compose.py(3)、webapp/contracts.py(3)、webapp/materialize.py(3)、alpha/contracts.py(2)、alpha/models/session_assessor.py(2)、briefing/cli.py(2)、briefing/alpha_view/contracts.py(2)、briefing/alpha_view/sources.py(2)
  static: 2 檔｜webapp/static/app.js(1)、webapp/static/app.js(1)
  tests: 3 檔｜tests/test_investor_brief.py(1)、tests/test_webapp_coverage_watches.py(1)、tests/test_webapp_structure_table.py(1)
  livedocs: 2 檔｜CONCEPTS.md(3)、docs/ARCHITECTURE.md(1)
  docs: 9 檔｜docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(23)、docs/ROADMAP.md(20)、docs/archive/roadmap-alpha-edge-2026-09-22.md(18)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(16)、docs/archive/roadmap-phase-delivery-log.md(14)、docs/reports/2026-09-22-phase0-baseline.md(10)、docs/archive/roadmap-completion-gate-log.md(6)、CONCEPTS.md(3)
## E 賭注四價／variant overlay
  code: 19 檔｜briefing/alpha_view/builder.py(8)、alpha/narrative/contracts.py(4)、alpha/fundamental/contracts.py(3)、briefing/alpha_view/sources.py(3)、briefing/analyst_view/compose.py(3)、briefing/analyst_view/contracts.py(3)、alpha/legacy_axes.py(2)、alpha/abstention/contracts.py(2)
  static: 2 檔｜webapp/static/app.js(6)、webapp/static/app.js(6)
  skills: 2 檔｜skills/alpha-status/SKILL.md(2)、skills/research-drain/SKILL.md(1)
  tests: 11 檔｜tests/test_absence_semantics.py(3)、tests/test_alpha_legacy_conversion.py(2)、tests/test_investor_brief.py(2)、tests/test_webapp_api.py(2)、tests/test_webapp_materialize.py(2)、tests/fixtures/decision_lab/sive_reference_design.json(2)、tests/test_analyst_view.py(1)、tests/test_decision_blockers.py(1)
  config: 2 檔｜config/decision_blockers.json(2)、config/engine_c_observation_fields.json(1)
  livedocs: 3 檔｜CONCEPTS.md(6)、docs/ARCHITECTURE.md(4)、docs/OPERATIONS.md(3)
  docs: 30 檔｜docs/archive/roadmap-alpha-edge-2026-09-22.md(19)、docs/ROADMAP.md(14)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(14)、docs/archive/roadmap-backlog-log.md(13)、docs/archive/roadmap-phase-delivery-log.md(10)、docs/archive/roadmap-completion-gate-log.md(8)、docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(8)、docs/archive/roadmap-pre-alpha-edge.md(7)
## F entry criterion
  code: 4 檔｜alpha/cli.py(2)、alpha/refresh/contracts.py(2)、briefing/alpha_view/builder.py(1)、scripts/verify_test_nonvacuity.py(1)
  tests: 1 檔｜tests/test_webapp_request_path.py(1)
  livedocs: 2 檔｜CONCEPTS.md(2)、docs/ARCHITECTURE.md(1)
  docs: 7 檔｜docs/archive/roadmap-pre-alpha-edge.md(6)、docs/archive/2026-09-23-phase0-retired-sections.md(3)、docs/ROADMAP.md(2)、CONCEPTS.md(2)、docs/ARCHITECTURE.md(1)、docs/archive/roadmap-alpha-edge-2026-09-22.md(1)、docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(1)
## G decision_lab 鑄號／reassess
  code: 53 檔｜engine_b/todo.py(16)、crons/daily_brief_prompt.md(10)、engine_b/queue_segments.py(9)、scripts/backup_private.py(9)、decision_lab/cli.py(8)、scripts/verify_test_nonvacuity.py(8)、scripts/migrate_decision_store_v8.py(6)、scripts/outcome_if_settled_today.py(5)
  skills: 5 檔｜skills/daily-brief/SKILL.md(8)、skills/lead-intake/SKILL.md(5)、skills/alpha-status/SKILL.md(1)、skills/investment-research/SKILL.md(1)、skills/research-drain/SKILL.md(1)
  tests: 31 檔｜tests/test_private_backup_restore.py(23)、tests/test_layer_separation.py(22)、tests/test_engine_b_todo.py(16)、tests/test_standing_authorization.py(16)、tests/test_codex_daily_permissions.py(10)、tests/test_alpha_view_brief.py(8)、tests/test_backup_entrypoint.py(8)、tests/test_queue_segments.py(7)
  config: 4 檔｜config/decision_blockers.json(8)、config/authority_tokens.json(5)、config/standing_authorization.json(3)、config/engine_c_observation_fields.json(2)
  livedocs: 3 檔｜docs/OPERATIONS.md(29)、docs/ARCHITECTURE.md(9)、CONCEPTS.md(6)
  docs: 60 檔｜docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(60)、docs/archive/roadmap-pre-alpha-edge.md(44)、docs/plans/2026-08-28-001-refactor-bottleneck-ranking-terminus-plan.md(42)、docs/plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md(41)、docs/archive/roadmap-pre-alpha-refactor.md(35)、docs/plans/2026-07-22-001-feat-engine-d-operational-workflow-plan.md(32)、docs/refactor/target-architecture.md(32)、docs/OPERATIONS.md(29)
## H 估值模型 valuation/fundamental
  code: 20 檔｜engine_c/estimates.py(15)、alpha/providers/fundamentals.py(12)、briefing/alpha_view/builder.py(8)、briefing/alpha_view/changes.py(8)、engine_c/db.py(7)、engine_c/checklist.py(5)、engine_c/market_data.py(5)、alpha/contracts.py(4)
  tests: 20 檔｜tests/test_coverage_pilot_generalization.py(9)、tests/test_estimate_revision.py(6)、tests/test_alpha_investment_view.py(3)、tests/test_alpha_vertical_slice.py(3)、tests/test_analyst_view.py(3)、tests/test_consensus_coverage_collapse.py(3)、tests/test_overlay_scope_gate.py(3)、tests/test_refresh_engine.py(3)
  livedocs: 1 檔｜CONCEPTS.md(1)
  docs: 12 檔｜docs/archive/roadmap-pre-alpha-edge.md(13)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(7)、docs/archive/roadmap-backlog-log.md(6)、docs/refactor/current-architecture.md(5)、docs/plans/2026-07-08-004-feat-investment-query-gap-audit-plan.md(4)、docs/ROADMAP.md(3)、docs/archive/agents-pre-graph-first-2026-09-22.md(1)、docs/refactor/phase-1-plan.md(1)

## 驗收（差集；Phase 0 結案要三個數字都是 0）
  未列 keep-list 的命中（檔，組）數：0
  已列但不再命中（腐壞條目）數：0
  keep-list 條目數：288｜理由類別不合法：0
```

活文件（OPERATIONS／ARCHITECTURE／CONCEPTS）剩餘命中逐句審過：只剩①退役註記（「X 已於 … 退役」）、②禁止句（「不排序、不設門檻、不給首選」「沒有目標價、沒有隱含報酬」）、
③留下的檔名與路徑（`decision_lab/store.py`、`library/private/decision_lab/outcome_aggregate.json`）、④regex 過度匹配活字彙（`calibrat` 命中假設 ledger 的 ref 角色 `calibration_refs`；`籃子總報酬` 是 AGENTS 量測用語；`pe_forward` 是 Engine C 欄位名），
⑤2026-09-22 Step 0a.1 的 sandbox review 記錄本身（它就是退役的紀錄）。整節退役的 9 段逐字封存於 [`docs/archive/2026-09-23-phase0-retired-sections.md`](../archive/2026-09-23-phase0-retired-sections.md)。

## 4. 舊 Decision Store（A5 不受傷）

| 檔 | sha256 | live_choices | 與基準 |
|---|---|---|---|
| decision_lab.db | e99d1c79fd22dbe1099f30c4e06f2d1188f26a8cbfa987a27cd8842530951810 | 1 | 逐字相同 |
| backup_pre_v9_20260902T032020Z.db | af3dc690ce836b6026d86946c388d19f1500139287469f0f9fbe8711c4819d39 | 1 | 逐字相同 |
| backup_pre_v8_20260818T021452.db | e887b3d458621e4cd7bb66913690d47d263d7188f9bbc1bacb4bc16ec57de350 | 0 | 逐字相同 |

查證：`python -m decision_lab status`（新的唯讀窗，`mode=ro` 直連、不開 store）；`python -m decision_lab history --decisions`。

## 5. 硬擋搬家（0b.4 1/3；R2 trigger「capital／destructive write」，常規 opt-in）

- 規則住 `risk/hard_caps.py`，數字 SSOT 不變（`config/investment_policy.json` 的 `single_position_nav_cap`＝0.05；`config/beta_policy.json` 的 `leveraged_nominal_cap`＝0.2／`leveraged_effective_cap`＝0.4）。
- `scripts/record_trade.py` 每一筆**買進**在寫 Sheet／trade_log 前必過；dry-run 也擋（exit 3）；`--override --reason` 放行並把理由與整份 verdict 寫進事件紀錄；賣出 `not_applicable`；NAV／匯率量不到一律 `unmeasurable`（fail closed）；跨幣別要 `--fx-to-base`。
- 5% 單筆只管不在 `beta_policy.instruments` 的標的（beta ETF 本來就超過 5%，套上去煞車就變噪音，L14）；ETF cap 只在 `leverage_multiple > 1` 時比、nominal／effective 各比各的。
- 舊店 `record_live_choice`／`record_live_fill` 直接 raise `FrozenStoreError`（根除，不只顯形）。
- 測試 20 條：`tests/test_hard_caps.py`（12）＋`tests/test_record_trade.py`（8）。

## 6. 0b.4 的 sandbox impact review 五步（unattended surface 變更）

| 步 | 結論 |
|---|---|
| 1 path／side effect／capability | 沒有新增任何 path、side effect 或 capability。移除：`python -m engine_b.todo reassess-stale` 子命令（rule 早於 0a.1 移除）、`python -m decision_lab` 的研究側子命令（rule 早於 0a.1 移除）、`engine_b.cli drain --decision-work-orders`（drain 早於 09-17 移出 allowlist）；`engine_b.todo standing-go` **不再開 Decision Store**（surface 變窄：不再讀 private DB）；`scripts/catalyst_watch.py` 命令字串與讀法不變（`coverage_queries` 留）。MCP `get_decision_brief` 工具移除。 |
| 2 canonical skill／prompt／本檔 | `crons/daily_brief_prompt.md`（Decision work order 段與 step 7 改退役註記）、`skills/daily-brief/SKILL.md`（遠端 fallback 只剩 leads 路徑）、OPERATIONS（本報告 §3 所列）。 |
| 3 最窄 rule | `.codex/rules` **仍 12 條，沒有新增、沒有放寬**。 |
| 4 permission contract test | `tests/test_codex_daily_permissions.py`（12 條斷言不變）、`tests/test_routine_prompts.py`（改斷言退役註記）綠。 |
| 5 端到端 smoke | `python -m engine_b.todo standing-go`（dry-run）候選 0／跳過 0；`python -m engine_b.todo list` 正常；`python -m engine_b.todo reassess-stale` 回 argparse invalid choice；`python -m decision_lab status／history` 可跑；`python -m crons.heartbeat` 五段照印。 |

⚠ **跑著的 MCP process（PID 12388／29728，2026-08-27 起）仍是舊 tool surface**（in-memory 的 `briefing.public_view` 早已載入），
要照 OPERATIONS「改完 mcp_server 一定要重啟」由使用者重啟；重啟前遠端仍看得到 `get_decision_brief`，重啟後是 11 個工具。

## 7. 本 Phase 執行中發現、Phase 1 要決定的問題（plan §5「結案之後」要求）

1. **today brief 退役後三個 pane 沒有消費端**：備份新鮮度（`briefing/sources.load_backup_status`＋`briefing/render.render_backup_status`）、NAV 比例（`portfolio/brief.render_nav_exposure`）、position events／outcome aggregate（`alpha/brief.py`）。心跳（Phase 1 主角）要不要接？備份新鮮度原本是 daily 首屏常駐紅燈，現在**沒有任何地方印**——這是 0b.4 造成的觀測缺口（plan §0.6 #44）。
2. **`forward_view_backlog` 的主詞已換成「去寫短評」**（0b.1a：blocked 18 → 70，全部是 `brief=not_yet_recorded`；plan §0.6 #14）。Phase 1 心跳段 5 印它時要說清楚。
3. **`counter_path_relation` 字彙（`schema/vocab.json`）沒有 loader 了**（唯一 loader 隨 `engine_d_runtime` 退役）：Phase 2 走圖的 counter path 問句要接它，還是把字彙一併退役？
4. **watch registry 的語意條件 kind**（Phase 1 主題）：0b.4 把 daily prompt 裡「反證條件必須可觀測、有門檻、有日期；到期不得早於催化劑」的判準留下、載體拿掉；Phase 1 的 `semantic_condition` 要承接這三件套（L7）。
5. **反證登記的來源**：舊店 `coverage_assessments.disproof`（凍結歷史，個股頁 research 面板仍讀）與 thesis／讀圖的反證兩套並存；Phase 1「411 條舊反證只登記被讀圖或敘事引用的」要決定凍結歷史那一套算不算。
6. **`watch_decision` 的 go 語意**（ROADMAP Phase 1 已列）。
7. **`ra_admission` 的 receipt 契約改為三欄**（`action;digest;commit`，cohort 已退，plan §0.6 #47）：文件與 skill 已同步；Phase 1 若要「入圖後自動登記 watch」，接點在 `complete_ra_admission`。
8. **`config/decision_blockers.json` 的角色**：現在只服務讀凍結 payload 與 `resolution_mode` 分類；Phase 1 watch registry 的「等你決定／等事件」分類要不要沿用它的 `resolution_mode` 字彙，還是另立？
9. **舊 Decision Store 的 `research_work_orders`（160 筆）與 `probe_lifecycle_epochs`（13 筆）**：audit `Lifecycle`／`QueueLiveness` 仍讀它們（PASS）；Phase 1 一個 registry 落地後，audit 的這兩項要不要改讀新 registry。

## 8. 附錄：本次實跑的命令

```powershell
python -m pytest -q
python -m audit invariants
python scripts/retired_mechanism_grep.py
python -m webapp status | tail -12
python -m engine_b.todo list
python -m decision_lab status
python -m crons.heartbeat --out $env:TEMP\heartbeat_closeout.md
python scripts/analyst_view_text_digest.py --per-panel      # materialize 前
python -m webapp materialize --tracked --registry-listed --structure-table --beta --coverage --watches --positions --structure-readings
python scripts/analyst_view_text_digest.py --per-panel      # materialize 後
git log --diff-filter=D --name-only --pretty=format: d6e3fca..HEAD -- tests/ | sort -u
```
