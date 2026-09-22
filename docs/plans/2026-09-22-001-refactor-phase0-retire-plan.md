---
date: 2026-09-22
topic: phase0-retire
status: active
derived_from: docs/ROADMAP.md（Phase 0）、docs/brainstorms/2026-09-22-graph-first-direction-decision.md（G1–G12）
---

# Phase 0 拆：退役估值鏈、排序驅動、decision_lab 研究側（給執行模型的完整 plan）

> **執行者：便宜模型，走 `skills/development-flow/SKILL.md`（Z1 以上預設 R1）。**
> 本 plan 從 [`docs/ROADMAP.md`](../ROADMAP.md)「Phase 0」與「Phase 0 退役清單」導出；衝突時以 ROADMAP 與
> [決定紀錄 G1–G12](../brainstorms/2026-09-22-graph-first-direction-decision.md) 為準，並回頭修本 plan。
>
> **開工前必讀（順序）：** `AGENTS.md` 全文 → ROADMAP「Phase 0」「退役清單」「decision_lab 凍結」「硬約束」→
> `docs/refactor/historical-failure-matrix.md` §2 六條 invariant → `docs/OPERATIONS.md`「sandbox impact review 五步」→ 本 plan。
>
> **每個 Step 交回 `HUMAN SUMMARY` ＋ 八欄；Acceptance status 每個數字註明數的是哪一層（圖／讀圖／敘事／registry／追蹤表），
> 「幾檔通過某個 filter」型的數字直接 NO_GO。** 本 Phase 的驗收數字全部是「殭屍 grep 命中數」「state kind 數」「pq2 未結案數」
> 「Decision Store sha256」這類**機制存在與否**的計數，不是研究結果。

---

## 0.5 核准狀態、續工方式、進度表

**本 plan 是使用者 2026-09-22 已核准的 PLAN_PROPOSAL。** 0b 的 Z2 不再停等核准；`AGENTS.md`「常規推進授權」照用：
Verdict 為 `GO` 且沒有待使用者決定的問題就**直接做下一個 Step，Step 與 Phase 邊界一視同仁**，做到 Phase 0 結案為止。
只有六條停止條件之一成立才停（其中本 Phase 會撞到的只有：§6「撞到就停」的切不開情況、Verdict 不是 GO、需要 R2）。
0c 的 pq2 批次 drop 已授權（見 §4），不再回頭請求。
**本 Phase 執行期間六條 trigger 命中的 R2 一律常規 opt-in（使用者 2026-09-22 定案）**：0b.4 動到成交路徑硬擋時直接發 `WORK_REQUEST`，不停下來問。

**每個 Step 一個 commit，訊息第一行寫 Step 編號；Step 為 GO 就 push。** 這是續工的唯一依據：新 session 先看下面進度表與 `git log --oneline -20`，
從第一個未 ✅ 的 Step 接續，不重做已 ✅ 的。進度表由執行者在每個 Step 的 commit 裡更新（把 ○ 改 ✅ 並填 commit 短碼）。

**同一 working tree 只讓一個 writer 寫入：** 執行本 plan 期間**暫停 Codex daily／weekly 排程**（它們與 0a.1、0a.2 改的是同一批檔），Phase 0 結案後再開。

> **排程狀態（2026-09-22 15:28 實測，Step 0.0 記錄）：** 本機唯二的排程 writer `StockBotv2-Heartbeat`
> 與 `StockBotv2-FxSync` 下次觸發都是 **2026-09-23 早上**；今天是星期二，Codex weekly（週日）不跑，
> daily（台北 06:30）同樣是明天。**今天沒有第二個 writer，所以未停排程也不衝突。**
> ⚠ **時限 2026-09-23 06:30**：Phase 0 若跨到明天早上，續工的第一件事是先暫停排程再動手。
> 查證與細節見 [基準報告 §0](../reports/2026-09-22-phase0-baseline.md)。

**進度表的 commit 欄：** 一個 Step 的 commit 短碼在它自己的 commit 裡算不出來（填進去就會改變雜湊），
所以**由下一個 Step 的 commit 補填**；`○ → ✅` 本身在該 Step 的 commit 裡完成。

| Step | 內容 | 狀態 | commit |
|---|---|---|---|
| 0.0 | 基準快照 | ✅ | |
| 0a.1 | 排程與規則停跑 | ○ | |
| 0a.2 | 心跳與 APP 入口停跑 | ○ | |
| 0a.3 | 研究 skill 改句 | ○ | |
| 0a.4 | 池子收集端停鑄 | ○ | |
| 0b.1 | 個股頁樞紐重寫、斷 import | ○ | |
| 0b.2 | 刪估值鏈 | ○ | |
| 0b.3 | 排序與籃子 | ○ | |
| 0b.4 | 四價、decision_lab 凍結、硬擋搬家、活文件 | ○ | |
| 0c | 池子 17 筆 drop | ○ | |
| 結案 | 九項 gate ＋ closeout 報告 ＋ ROADMAP 標 ✅ | ○ | |

**開工／續工指令：貼 `/phase-run` 即可**（skill 會照下面這段做；不能用 skill 時貼這段原文）：

```
讀 docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md，依 §0.5 的進度表與 git log 找到第一個未完成的 Step，
從那裡開始，走 development-flow（Z1 以上 R1）。沒有需要我核准的事就一直做到 Phase 0 結案；撞到六條停止條件才停。
每個 Step 一個 commit 並更新進度表，GO 就 push。每個 Step 交回 HUMAN SUMMARY 與八欄。
```

## 0. 不可越線（違反即 NO_GO）

1. **不碰資料 authority：** 不碰 Neo4j、Engine C ledger、thesis lifecycle、Google Sheet、`library/private/`、`library/trades/`。
2. **舊 Decision Store 只准讀。** Step 0.0 記下檔案 sha256 與 `live_choices` 筆數，Phase 結案時比對，必須相同。
3. **不刪 `docs/archive/`、`docs/lessons-incidents.md`、`docs/brainstorms/`。** 退役機制的文字只從活文件（OPERATIONS／ARCHITECTURE／CONCEPTS／skills）拿掉。
4. **任何 `python -m <module>` 命令字串變更 → sandbox impact review 五步**，同一個 commit 改 `.codex/rules` 與 `tests/test_codex_daily_permissions.py`。
5. **每刪一個測試檔，八欄的 Blocking findings 列出它守的是哪個退役機制。** 活機制的測試不可刪斷言（ROADMAP 硬約束 9）。
6. **每批動手前先答 L11-6 第④問：「如果這個刪除是錯的，最先壞掉的是哪一筆現有資料或哪個活的 import？」去看那一筆，寫進八欄。**
7. **撞到需要使用者決定的事 → `AWAITING_HUMAN`，不自行擴 scope。** 已知會撞的：某個檔同時服務活機制與退役機制且切不開（見 §6）。
8. **四個人工 gate、五條 authority separation、六條 invariant 全程適用。** 本 Phase 不寫任何 authority。

## 1. Step 0.0 基準快照（Z0，一個 commit）

全部存進 `docs/reports/2026-09-2x-phase0-baseline.md`（日期用實跑日）：

```bash
python scripts/retired_mechanism_grep.py                 # 八組命中數（code／static／skills／tests／config／livedocs）
python -m webapp status | tail -12                        # 9 個 state kind
python -m engine_b.todo list                              # pq2 未結案（預期 19：17 decision_review ＋ 2 manual）
python -m pytest -q 2>&1 | tail -1                        # 全綠基準與測試數
python -m audit invariants                                # 六 invariant 綠
python - <<'EOF'
import hashlib,glob,sqlite3
for p in glob.glob('library/private/decision_lab/*.db'):
    print(p, hashlib.sha256(open(p,'rb').read()).hexdigest()[:16],
          sqlite3.connect(p).execute('select count(*) from live_choices').fetchone())
EOF
```

驗收：報告存在且含上面每一項的實際輸出。**這些數字是 Phase 結案時的比對基準**（現況數字會腐壞，所以要存下來）。

## 2. Step 0a 停跑（Z1，四個小 commit）

目的：**先讓退役機制不再產生任何注意力**，再刪。每項改最少的東西。

| # | 改哪裡 | 怎麼改 | 怎麼驗 |
|---|---|---|---|
| 0a.1 排程與規則 | `crons/daily_brief_prompt.md`、`crons/weekly_scan_prompt.md`、`engine_b/queue_segments.py`、`.codex/rules/*`、`config/standing_authorization.json` | prompt 拿掉 decision_lab `today`／reassess／籃子／首選段；`queue_segments` 移除 reassess-stale 段與任何以 `rank_bottlenecks` 順序餵的段；`.codex/rules` 移除 `decision_lab today` 與 reassess-stale 兩條 fixed entry（**五步 review**，`tests/test_codex_daily_permissions.py` 同 commit）；standing_authorization 移除 `decision_review` 類別（`engine_b/standing_authorization.py` 載入時驗封閉性，`tests/test_standing_authorization.py` 同 commit） | `python -m engine_b.cli counts` 佇列段少 reassess；`pytest tests/test_codex_daily_permissions.py tests/test_standing_authorization.py tests/test_routine_prompts.py` 綠 |
| 0a.2 心跳與 APP 入口 | `crons/heartbeat.py` 段 2；`webapp/__main__.py` materialize 清單；`webapp/api.py` 路由；`webapp/static/index.html` nav | 段 2 的「現價過目標價」與籃子行換成一行 `候選狀態板未落地（not_yet_recorded）`（**五段永遠出現**）；materialize 清單移除 `multi_year`、`basket`；`/api/v1/multi-year` 與 basket 路由移除；nav 移除「要幾倍」「籃子」（籃子 Phase 3 以候選板回來） | `python -m webapp status` 沒有 `multi_year`、`basket`；`pytest tests/test_heartbeat.py tests/test_webapp_request_path.py` 綠（heartbeat 測試裡斷言籃子行的斷言跟機制退役，列進八欄） |
| 0a.3 研究 skill | `skills/daily-brief/SKILL.md`、`skills/research-drain/SKILL.md`、`skills/alpha-status/SKILL.md`、`skills/investment-research/SKILL.md`、`skills/blind-spot-audit/SKILL.md`、`skills/system-decompose/SKILL.md` | 拿掉或改寫首選、籃子、payoff、隱含報酬、目標價、排序驅動研究、decision_review 的句子；alpha-status 的「現在該投什麼」改答「候選狀態板（Phase 3 前印未落地）」；跑 `python scripts/sync_agent_skills.py` | `python scripts/retired_mechanism_grep.py` 的 skills 列 → 0；`pytest tests/test_daily_brief_skill.py tests/test_agent_workflow.py` 綠（skill 測試裡斷言退役段落的斷言跟機制走） |
| 0a.4 池子收集端 | `engine_b/todo.py` | `collect_all(include_decisions=False)` 成為唯一路徑：移除 `collect_from_decisions` 的呼叫；`ITEM_TYPES` 與 `GO_AUTHORIZATION` 裡的 `decision_review`、`sheet_only_holding` **改成 legacy 標記**（照 `lead_research` 的寫法，不刪 key：池裡歷史項目仍是這兩個 type，讀取要認得，且 `tests/test_engine_b_todo.py` 斷言兩個 dict 鍵一致） | 跑一次 collect 後 `todo list` 沒有新鑄的 decision_review；`pytest tests/test_engine_b_todo.py` 綠 |

**0a 結案驗收：** 心跳五段照印；`webapp status` 9 kind → 7；skills 命中 0；`todo` 新鑄來源無 `decision_lab`。

## 3. Step 0b 刪除（Z2 一次 PLAN_PROPOSAL，四批各一個 commit）

**順序不可換：先斷 import，再刪模組。** 2026-09-22 的 importer 地圖（`docs/ROADMAP.md` 退役清單的補充，實跑時重算一次）：

| 要刪的 | 被誰 import（活的程式，不含測試） |
|---|---|
| `alpha/valuation` | `briefing/alpha_view/sources.py`、`builder.py`、`alpha/implied_return/*`、`alpha/providers/valuation_assumptions.py`、`alpha/entry/*`、`alpha/cli.py`、`alpha/refresh/artifacts.py` |
| `alpha/implied_return` | `builder.py`、`sources.py`、`contracts.py`、`render.py`、`alpha/providers/horizon_assumptions.py`、`alpha/cli.py`、`alpha/closure.py`、`alpha/entry/*`、`alpha/refresh/artifacts.py` |
| `alpha/fundamental` | **25 個**：含 `alpha/contracts.py`、`alpha/providers/fundamentals.py`、`alpha/providers/assumptions.py`、`briefing/multi_year.py`、`builder.py`、`sources.py`… → **它有兩半**：`FundamentalsSnapshot` 這類**資料契約**要留，FY+1 因果橋**模型**要刪 |
| `alpha/reverse` | `briefing/multi_year.py`、`sources.py` |
| `alpha/entry` | `builder.py`、`sources.py`、`contracts.py`、`render.py`、`alpha/providers/entry_criteria.py`、`alpha/cli.py`、`alpha/refresh/artifacts.py` |
| `alpha/ranking` | `decision_lab/brief.py`、`alpha/brief.py`、`briefing/today.py`、`sources.py` |
| `alpha/backtest` | `scripts/rank_forward_returns.py` |
| `briefing/multi_year` | `briefing/cli.py`、`sources.py`、`webapp/materialize.py` |
| `webapp/basket` | `webapp/materialize.py` |
| `rank_bottlenecks()` 當排序 | `alpha/providers/graph_neo4j.py`、`webapp/materialize.py`、`builder.py`、`basket.py`、`webapp/api.py`、`alpha/ranking.py`、`query/structure.py`、`alpha/provider.py`、`engine_b/cli.py` |
| decision_lab 研究側 | `engine_b/todo.py`、`briefing/today.py`、`sources.py`、`engine_b/signal_source_registry.py`、`alpha/catalyst.py`、`alpha/cli.py`、`briefing/public_view.py`、`briefing/render.py`、`engine_b/leads.py` |
| `decision_lab.store`（**唯讀留**） | `alpha/__init__.py`、`briefing/today.py`、`webapp/api.py`、`webapp/materialize.py`、`webapp/__init__.py`、`webapp/__main__.py`（positions kind 讀 live choice 歷史，讀取合法） |

**樞紐是 `briefing/alpha_view/builder.py`（估值鏈 166 處）與 `sources.py`。** 它們 import 了幾乎所有退役模組，所以第一批是重寫樞紐，不是刪模組。

### 批 1｜斷 import：個股頁 builder 重寫（最大的一批）

- 檔：`briefing/alpha_view/{builder,sources,contracts,render,changes}.py`、`briefing/analyst_view/{compose,contracts}.py`、
  `alpha/refresh/artifacts.py`、`alpha/closure.py`、`alpha/cli.py`、`alpha/contracts.py`、
  `alpha/providers/{valuation_assumptions,horizon_assumptions,entry_criteria,assumptions,fundamentals}.py`、
  `webapp/{api,materialize,__main__}.py`、`webapp/static/{app.js,index.html}`。
- 做：依 ROADMAP「消費層對照表／個股頁」——首屏拿掉尺（現價／沒賭對／賭對／判斷錯了）與「要翻倍需要什麼為真」計算框；
  論證層 `bet` 改純文字（讀 `our_bet`）、`entry` 面板刪；稽核區拿掉 q4 隱含報酬、q7 payoff；`overview` 拿掉 `implied_return`、`payoff`、
  `future_target`、`sell_side_target`、`target_reached`；readiness 核心面板改為 headline、短評、why、research、歸零旗標（讀圖面板 Phase 2 加）、
  fundamental 降為選配。`alpha/fundamental` 的 `FundamentalsSnapshot` 等資料契約搬進 `alpha/contracts.py` 或留在 `alpha/fundamental/contracts.py`，
  模型檔（因果橋）留到批 2 刪。`alpha/cli.py` 拿掉 valuation／implied／entry／reverse 子命令。
- 驗收：**importer 地圖重算後，退役模組只被退役模組自己與測試 import**；`python -m webapp materialize` 全 73 檔成功；
  `python -m webapp status` 的 blocked 檔數不因 fundamental 缺席而增加（readiness 規則換了）；`pytest tests/test_webapp_request_path.py tests/test_analyst_view.py tests/test_absence_semantics.py` 綠（斷言尺與 q4／q7 的測試跟機制走，逐一列出）。
- L11-6 第④問：**最先壞的是 `alpha/providers/fundamentals.py`**——它 import `alpha.fundamental` 三處；動手前確認它要的是資料契約不是模型。

### 批 2｜刪估值鏈

- 刪：`alpha/valuation/`、`alpha/implied_return/`、`alpha/fundamental/`（只留資料契約，若已搬則整包刪）、`alpha/reverse/`、`alpha/entry/`、
  `alpha/providers/entry_criteria.py`、`briefing/multi_year.py`、`scripts/multi_year_check.py`、`scripts/alpha_expectation_gap.py`、
  `alpha/models/session_assessor.py` 裡的 `multiple_horizon` 讀寫（判斷檔資料留，不再消費）。
- 刪測試：`test_implied_return`、`test_valuation_model`、`test_fundamental_model`、`test_reverse_bridge*`、`test_multi_year_*`、`test_entry_logic`、
  `test_brief_multiple_question`、`test_variant_scenario`（四價部分）、`test_estimate_revision`（若只服務估值）。`test_full_chain_acceptance` **重寫**成新管線
  （圖 → 讀圖 ledger → 敘事 → 三題 absence → 心跳），不是刪。
- 驗收：殭屍 grep 的 C、D、F、H 四組在 code／static／tests 命中 0；`pytest` 全綠。
- L11-6 第④問：**最先壞的是 `engine_c/estimates.py`**——H 組 regex 命中它 15 處，但它是資料層（共識估計），**留**；確認刪的是 `alpha/` 的模型不是它。

### 批 3｜排序與籃子

- 刪：`alpha/ranking.py`、`alpha/backtest.py`、`scripts/rank_forward_returns.py`、`webapp/basket.py`、`scripts/outcome_if_settled_today.py`、`scripts/alpha_screen_check.py`。
- 改：`query/bottleneck.py` → 結構表：保留逐邊 rows（證據等級、sub、sole_source、qualification、自報／外部印證、走不走得到錨）、`anchor_gaps`、
  INV-3 的 filtered reasons；**拿掉** `min_substitutability` 當排名門檻、top-N、「可行動排序」與「純結構排序」兩份序、`--sector` 分組；
  函式改名 `structure_table()`，`rank_bottlenecks` 名稱不留 alias。`alpha/providers/graph_neo4j.py`、`alpha/provider.py`、`query/structure.py`、
  `engine_b/cli.py`、`webapp/{materialize,api}.py` 改讀結構表；state kind `ranking` → `structure_table`；`app.js` 排序頁改結構表頁（拿掉排名框）。
  `config/alpha_screen.json`（覆蓋厚薄門檻）**留**，改由 Phase 3 候選板消費；`config/lead_classification.json` 的排序引用改走圖。
- 刪測試：`test_webapp_basket`、`test_basket_screen_thresholds`、`test_bet_endgame`、`test_ranking_view`；`test_bottleneck_ranking`、`test_webapp_ranking`、
  `test_sole_source_tristate` **改寫**成結構表測試（保留三態、去重、證據上限那些活的斷言）。
- 驗收：殭屍 grep 的 A、B 兩組命中 0；`webapp status` 列得出 `structure_table`；`pytest` 全綠。
- L11-6 第④問：**最先壞的是 `engine_b/priority.py`／`queue_segments.py` 有沒有拿排序當 pq1 優先序**——0a.1 應已移除，動手前 grep 一次 `rank_bottlenecks` 確認只剩結構表。

### 批 4｜賭注四價、decision_lab 凍結、硬擋搬家、活文件

- 賭注四價（E 組）：payoff 計算與四價渲染刪；`bet/variant.overlay` ledger **資料留**；`alpha/narrative/argument.py` 的 payoff 引用改文字；
  `config/decision_blockers.json`、`config/engine_c_observation_fields.json` 裡只服務 payoff／估值的 blocker 碼與欄位移除（封閉字彙，`tests/test_config_tracking.py` 與相應測試同 commit）；
  `decision_lab/sizing.py`、`tests/test_probe_sizing.py`、`test_weakest_axis`、`test_downside_overlay`、`test_bet_state_opinion_in_base`、`test_brief_downside_symmetry` 刪。
- decision_lab 凍結（依 ROADMAP「decision_lab 凍結」表）：刪 `execution.py`、`outcomes.py`、`sizing.py`、`context.py`、`coverage.py`、`coverage_queries.py`、
  `intake.py`、`workflow.py`、`workflow_ports.py`、`brief.py`、`action_card.py`、`references.py`；`cli.py` 只留唯讀 `history`／`status`；
  `store.py` 寫入方法留著但無呼叫端，docstring 第一行加 `frozen 2026-09-22（G12）`；`engine_b/todo.py` 刪 `collect_from_decisions` 與所有 decision_review 分支
  （legacy 標記已在 0a.4）；`briefing/today.py`、`public_view.py`、`render.py` 拿掉 decision brief pane；`alpha/catalyst.py`、`engine_b/signal_source_registry.py`、
  `engine_b/leads.py` 的研究側 import 斷掉；MCP `get_decision_brief` 工具退役（先 `grep -rn get_decision_brief` 找定義）。
  刪測試：`test_decision_lab_e2e`、`test_action_card`、`test_operational_workflow`、`test_layer_separation`（若只驗研究側）；`test_private_backup_restore` **留且必須綠**。
- 硬擋搬家：`store.py` 的 `_assert_user_sized_within_capital_caps` 搬到 `risk/`（或 `portfolio/`，選已有 policy 載入的那個），
  `scripts/record_trade.py` 在 `--apply` 前呼叫：以 Sheet NAV 算成交後單筆占比與槓桿曝險，超過 5% 單筆或 ETF 槓桿 cap → fail closed；
  `--override --reason "<理由>"` 才放行並在 trade_log 事件寫 `override_reason`。**新增測試**：dry-run 超 5% 必須 fail closed；override 無 reason 必須拒絕。
- 活文件：`docs/OPERATIONS.md` 的 decision_lab 命令段、`docs/ARCHITECTURE.md` §8.2 對應列與 §7／§9 提到 Engine D 研究側的段、`CONCEPTS.md` 的相關詞條
  **同 commit 更新**；殭屍 grep 的 `livedocs` 命中逐句列在八欄，只有「不做 X」「X 已退役」型的句子可留。
- 驗收：殭屍 grep 的 E、G 兩組命中 0；Decision Store sha256 與 `live_choices` 與 Step 0.0 相同；`python -m audit invariants` 綠；
  `pytest tests/test_private_backup_restore.py` 綠；record_trade 兩個新測試綠；`pytest` 全綠。
- L11-6 第④問：**最先壞的是 positions kind**——`webapp/materialize.py` 讀 `DecisionStore` 取 live choice 歷史；確認它只用讀取方法，凍結後仍能 materialize。

## 4. Step 0c 池子（Z0，一個 commit）

17 筆未結案 `decision_review` 一次批次 `drop`，理由逐字：「機制退役（ROADMAP Phase 0，2026-09-22 使用者定案 G3／G12）」。
這是 pq2 動作；**使用者已於 2026-09-22 明示授權**（`AGENTS.md`「使用者主動指示＝已授權」），receipt 註明語境。
只 drop `type=decision_review` 且未結案的；2 筆 `manual` 不動。

驗收：`python -m engine_b.todo list` 未結案 = 2（manual）；`todo_pool.log` 有 17 筆 drop 且理由相同。

## 5. Phase 0 結案（completion gate 九項）

1. `pytest -q` 全綠，測試數與 0.0 基準的差＝刪除的測試檔（逐檔列在八欄）。
2. `python -m audit invariants` 綠。
3. 語意 diff：`python -m webapp materialize` 前後，73 檔的 `brief`／`why`／`research` 面板內容不變（只拿掉面板，不改文字）。
4. 無新 dual authority：收據只住 trade_log，舊店無寫入呼叫端（grep `record_live_choice(` 呼叫端 = 0）。
5. 無 silent drop：心跳五段照印；被拿掉的段落印 `not_yet_recorded` 不是空白。
6. Point-in-time 測試綠。
7. lifecycle 可達：pq2 未結案 2；watches 95 筆仍在。
8. Executable protection：`scripts/retired_mechanism_grep.py` 五個驗收區（code／static／skills／tests／config）全 0，輸出存進 `docs/reports/…-phase0-closeout.md`。
9. **驗收數的是機制存在與否**（kind 數、命中數、sha256、pq2 數），沒有一個是「幾檔通過某個 filter」。

結案後同 commit：ROADMAP Phase 0 標 ✅、ARCHITECTURE §8.2 的「建議區間已移除、煞車仍在」列改指 `record_trade.py`。

### 結案 R2（使用者已常規 opt-in；執行者不必再問）

九項 gate 由執行者自報之後，**發下面這份 `WORK_REQUEST` 給乾淨 context 的 reviewer**（能 spawn 就 spawn；不能就原文交回由使用者貼給新 session）。
reviewer 只讀不寫，回 `REVIEW`（verdict `GO`／`NO_GO` ＋ findings）；`NO_GO` → `AWAITING_HUMAN`，執行者不得自動修。

```
WORK_REQUEST（R2，Phase 0 結案）
Target: master 最新 commit；docs/reports/…-phase0-baseline.md 與 …-phase0-closeout.md
Claimed acceptance: Phase 0 九項 gate 全過（見 closeout 報告）
Do not trust: 上面那行是待驗證的宣稱，不是事實
Task: 直接讀 repo，自己跑下列檢查，逐項 ✅／❌ 附實際輸出，回 REVIEW（含 verdict）
  1. python scripts/retired_mechanism_grep.py → code／static／skills／tests／config 五區全部 0；livedocs 命中逐句列出並判斷是否為禁止句
  2. python -m webapp status | tail -10 → 沒有 basket、multi_year；kind 數與 closeout 一致
  3. python -m engine_b.todo list → 未結案 2，皆 manual
  4. python -m pytest -q → 全綠；測試檔數差 ＝ closeout 列出的刪除清單，逐檔核對「守的是哪個退役機制」是否成立
  5. python -m audit invariants → 全綠
  6. library/private/decision_lab/*.db 的 sha256 與 live_choices 筆數 ＝ baseline 報告
  7. library/private/app/analyst_view/COHR.json：overview 沒有 payoff／implied_return／future_target／sell_side_target／target_reached 鍵；
     overview.brief.our_bet 與 view.why／research 的文字 digest ＝ baseline（只拿掉面板，不改文字）
  8. python -m crons.heartbeat --out <temp> → 五段標題都在；段 2 含「候選狀態板未落地」且 absence_kind 為 not_yet_recorded
  9. grep -rn "record_live_choice(" 呼叫端 ＝ 0（舊店無寫入端）；scripts/record_trade.py 的兩個新測試存在且綠
Boundaries: 不改 code、不 commit、不核准 pq2、不入圖、不動 thesis、不動 Sheet
```

使用者留下的只有三件：讀 reviewer 的 verdict；reviewer 對「刪除的測試守什麼」有疑慮時裁決；三個月後決定紀錄 §10 的四條否證。

### 結案之後：停，不要開 Phase 1

R2 回 GO 後：ROADMAP Phase 0 標 ✅、`docs/plans/README.md` 對照表本列改 completed，commit、push。
然後 **`AWAITING_HUMAN`**：Phase 1 還沒有 plan，不得自行開工。HUMAN SUMMARY 的「下一步」逐字印 `docs/plans/README.md`
「每個 Phase 開工前要有一份 plan」那段指令，並在 closeout 報告附「本 Phase 執行中發現、Phase 1 要決定的問題」清單
（例如：語意條件 kind 的欄位、watch_decision 的 go 語意、哪些反證先登記）。這是本 plan 唯一刻意的停點。

## 6. 已知陷阱

- **`ITEM_TYPES` 是封閉字彙且有測試綁鍵一致**（`tests/test_engine_b_todo.py`）：退役 kind 用 legacy 標記，不刪 key。
- **心跳五段永遠出現**（`crons/heartbeat.py` 三條不可退讓）：拿掉的內容換成 `absence_kind` 行，不能整段消失。
- **config 封閉字彙改動**要同步 `tests/test_config_tracking.py` 與 `.gitignore` 的 `!config/<name>.json`。
- **`alpha/fundamental` 有兩半**：資料契約留、模型刪；`engine_c/estimates.py` 是資料層，留。
- **`decision_lab.store` 的讀取端合法**（positions kind、backup／restore）；凍結是「無寫入呼叫端」不是「無人 import」。
- **Windows：python 不認 `/tmp`**，暫存用 `%TEMP%`；大檔用 Write 工具不用 heredoc（>8 KB 會截斷）。
- **測試裡的退役斷言**：`test_heartbeat`（籃子行）、`test_daily_brief_skill`（首選段）、`test_alpha_investment_view`（尺與相關性）等會紅——
  紅的斷言若守的是退役機制就跟著退役並列出；若守的是活的判準（例如相關性提醒必印）就**改主詞不刪斷言**。
- **`scripts/verify_test_nonvacuity.py`** 列了退役測試的空跑檢查（估值鏈 13 處、entry 6 處）：同批更新，否則它會對不存在的測試報錯。
- **撞到就停：** 某個檔同時服務活機制與退役機制且切不開（例如 `briefing/alpha_view/sources.py` 裡讀圖與估值共用一個 loader）→
  `SCOPE_ESCALATION` ＋ `AWAITING_HUMAN`，不自行重構整套。
