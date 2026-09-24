---
date: 2026-09-24
topic: phase1-baseline
plan: docs/plans/2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md
step: 1.0
---

# Phase 1 Step 1.0 — 基準快照

**這份報告只有一個用途：Phase 1 結案時逐項比對**（plan §1、§13）。現況數字會腐壞（`AGENTS.md`「現況數字會過期，判準不會」），
所以連同**產生它們的命令**一起存下來。本檔每個數字數的都是**等待 registry、pq2 池、機制存在與否**（kind 數、筆數、sha256、測試數），
沒有一個是研究結果，也沒有「幾檔通過某個 filter」。

- 快照時間：2026-09-24 14:46–15:10（台北）
- HEAD：`cb4b9c4`（工作區乾淨）
- Python：`.venv/Scripts/python.exe`

## 0. 單一 writer 狀態

| writer | 狀態 | 查證 |
|---|---|---|
| Codex `stockbotv2-daily-brief` | `PAUSED`（rrule 每日 05:30） | `grep ^status\|^rrule ~/.codex/automations/stockbotv2-*/automation.toml` |
| Codex `stockbotv2-weekly-scan` | `PAUSED`（rrule 週日 04:00） | 同上 |
| Windows `StockBotv2-Heartbeat` | Ready；上次 2026-09-24 07:00:01、結果 0；下次 2026-09-25 07:00 | `schtasks /Query /TN StockBotv2-Heartbeat /V /FO LIST` |
| Windows `StockBotv2-FxSync` | Ready；上次 2026-09-24 06:55:01、結果 0；下次 2026-09-25 06:55 | `schtasks /Query /TN StockBotv2-FxSync /V /FO LIST` |

`python scripts/writer_guard.py check` → `safe: true`、`writer_lock: null`、`daily_run_finished_at: 2026-09-22T05:51`（Codex daily 暫停後沒有再跑）。

```text
/c/Users/Cheng/.codex/automations/stockbotv2-daily-brief/automation.toml:status = "PAUSED"
/c/Users/Cheng/.codex/automations/stockbotv2-daily-brief/automation.toml:rrule = "RRULE:FREQ=WEEKLY;BYHOUR=5;BYMINUTE=30;BYDAY=SU,MO,TU,WE,TH,FR,SA"
/c/Users/Cheng/.codex/automations/stockbotv2-weekly-scan/automation.toml:status = "PAUSED"
/c/Users/Cheng/.codex/automations/stockbotv2-weekly-scan/automation.toml:rrule = "RRULE:FREQ=WEEKLY;BYDAY=SU;BYHOUR=4;BYMINUTE=0"
```

`~/.codex/.sandbox-bin/codex.exe --version` → `codex-cli 0.155.0-alpha.2.6`

## 1. 事件監看（等待 registry；結案驗收①–④的起點）

```powershell
.venv\Scripts\python.exe -c "import json,collections;w=json.load(open('library/leads/event_watches.json',encoding='utf-8'))['watches'];print(len(w));print(collections.Counter((x['kind'],x['status']) for x in w));a=[x for x in w if x['status']=='active'];print(collections.Counter('pq2' if x.get('wake_pq2') else 'lead' if x.get('wake_lead') else 'hyp' for x in a));print(sorted(x['expires'] for x in a)[:5])"
```

```text
95
Counter({('related_entity_signal', 'active'): 57, ('entity_filing_signal', 'active'): 27, ('fact_verification', 'active'): 5, ('fact_verification', 'consumed'): 4, ('date', 'consumed'): 1, ('date', 'active'): 1})
Counter({'lead': 80, 'pq2': 7, 'hyp': 3})
['2026-11-22', '2026-11-26', '2026-12-02', '2026-12-09', '2026-12-12']
exit=0
```

**要跟著 Phase 1 走的數字：** 總數 **95**（active 90 ／ consumed 5）；active 依喚醒對象 lead 80／pq2 7／假設 3；
**`semantic_condition` 0 筆**（驗收①的起點）；最早到期 2026-11-22（追源型）。

## 2. pq2 待辦池

`python -m engine_b.todo list`

```text
待辦事項統整：目前沒有需要你決定的項目。

## 等事件（2 項，觸發前不需動作）
  [586] 上詮 co:foci→tech:fiber_attach_unit 補 substitutability：等客戶端具名確認
        ↳ 等：Himax 或上詮 CPO 光纖陣列長約對手方在客戶端／法定文件首次具名確認上詮為該元件供應商（現況：一手只有上詮自述目標與產能投資，媒體報導依 C1 維持待判定）
  [632] SIVE.ST 的 B 路只剩一道門（qualification_status: sampling → qualified／designed_in），而沒有任何 watch 在等它
        ↳ 等：Sivers 期中／年報揭露 CW DFB／DWDM laser array 進入量產或客戶具名（qualification_status: sampling → qualified／designed_in）
exit=0
```

**球在使用者手上 0；等事件 2（#586、#632）。**

## 3. APP state 與 analyst view

`python -m webapp status`

```text
# Materialized Analyst Views（73 份；有賭注 3 檔；目錄由 STOCKBOT_APP_ARTIFACT_DIR 決定）
- 000660.KS｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 002472.SZ｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 005930.KS｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 012330.KS｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=deliberate_abstention
- 2301.TW｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 2455.TW｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 300308.SZ｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 3081.TWO｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 3105.TWO｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 3363.TWO｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 4971.TWO｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 4979.TWO｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 5016.T｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、wipeout=upstream_unavailable
- 5802.T｜blocked｜fresh（15.1h）｜refresh=review_required｜blockers: brief=not_yet_recorded、wipeout=upstream_unavailable
- 6268.T｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- 6324.T｜blocked｜fresh（15.1h）｜refresh=review_required｜blockers: brief=not_yet_recorded
- 6481.T｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 6594.T｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- 6680.HK｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 688017.SS｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- 688836.SS｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- AAOI｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- AAPL｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- AEHR｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- AEVA｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- AMAT｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- AMD｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- ANET｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- APO｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- AVGO｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- AXTI｜ready｜fresh（15.1h）｜refresh=review_required｜blockers: —
- BX｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded、wipeout=upstream_unavailable
- CCXI｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- CDNS｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- COHR｜ready｜fresh（15.1h）｜refresh=review_required｜blockers: —
- CRWV｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- ENA.V｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- FN｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- GFS｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- GLW｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- GOOGL｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- GXO｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- HEXA-B.ST｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- HIMX｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- INTC｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- IQE.L｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- IREN｜blocked｜fresh（15.1h）｜refresh=review_required｜blockers: brief=not_yet_recorded
- JBL｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- LITE｜ready｜fresh（15.1h）｜refresh=review_required｜blockers: —
- LRCX｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- LYC.AX｜blocked｜fresh（15.1h）｜refresh=review_required｜blockers: brief=not_yet_recorded
- META｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- MP｜blocked｜fresh（15.1h）｜refresh=review_required｜blockers: brief=not_yet_recorded
- MRVL｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- MSFT｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- MTSI｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- MU｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- NBIS｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- NOVT｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded、research=deliberate_abstention
- NVDA｜blocked｜fresh（15.1h）｜refresh=current｜blockers: brief=not_yet_recorded
- ORCL｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- POET｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- SHA0.DE｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded、research=not_yet_recorded
- SIVE.ST｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- SNDK｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- SOI.PA｜blocked｜fresh（15.0h）｜refresh=review_required｜blockers: brief=not_yet_recorded
- TSEM｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- TSLA｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- TSM｜blocked｜fresh（15.0h）｜refresh=invalidated｜blockers: brief=not_yet_recorded
- TXN｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- UMC｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- XFAB.PA｜blocked｜fresh（15.0h）｜refresh=current｜blockers: brief=not_yet_recorded
- XPEV｜blocked｜fresh（15.0h）｜refresh=review_required｜blockers: brief=not_yet_recorded
# State artifacts（7 份；目錄由 STOCKBOT_APP_STATE_DIR 決定）
- structure_table｜fresh（15.1h）｜current｜222 條邊／母體外 303 條
- beta｜fresh（15.1h）｜current｜sleeve 6 格／商品 14 檔
- coverage｜fresh（15.1h）｜current｜🔴 真缺口 9／🟡 建模待補 10／重複節點候選 23（沒人提過）
- watches｜fresh（15.1h）｜current｜在等 90／停滯 37
- positions｜fresh（15.1h）｜current｜逐檔 22／真實成交 1 檔
- structure_readings｜fresh（15.0h）｜current
- account_scorecard｜stale（160.4h）｜current
# 每檔閉環
- 段5 每檔閉環：到終局 3（ready 3／settled 0）／未到終局 70｜有 ready 檔的產業 1／5｜下一檔：000660.KS（有共識；EPS 為正；產業「記憶體」尚無 ready 檔；有帶 substitutability 的結構邊；已有基期觀測；缺：brief）
exit=0
```

## 4. 全測試基準

`python -m pytest -q`（最後幾行）；`ls tests/test_*.py | wc -l` → **175**

```text
  C:\Users\Cheng\code\StockBotv2\tests\test_webapp_api.py:15: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2180 passed, 1 skipped, 1 warning in 244.97s (0:04:04)
exit=0
```

## 5. 六條 invariant

`python -m audit invariants`

```text
PASS    Identity             圖 92 家全部在 registry 內（registry 另有 8 家尚未入圖，屬正常） [100 筆]
PASS    Duplicates           registry 100 家無 ticker／alias 碰撞 [100 筆]
PASS    Lifecycle            lifecycle epoch 與待辦池結案狀態一致 [663 筆]
PASS    Expiry               90 個進行中的等待全部有到期日 [90 筆]
PASS    Orphans              24 個跨檔引用全部解析得到 [24 筆]
PASS    QueueLiveness        5 項進行中工作全部在 14 天內有進展 [5 筆]
PASS    QueueSegments        pending_triage=0；fired_lead_requeue=0；fired_pq2_wake=0；fired_hypothesis_check=0；approved_work_orders=0；triaged_go_leads=3；forward_view_backlog=70；coverage_gaps=未讀到；duplicate_node_candidates=未讀到；stale_structure_readings=未讀到；pollable_watches=17；gated_gate_resolved=0；gated_no_pointer=0 [1876 筆]
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

總計 13 項｜FAIL 0｜SKIPPED 0｜PASS 13｜共檢查 4288 筆
exit=0
```

## 6. 健康審查

`python query/health_audit.py --local` — **13 節：🟢 12／🔴 1**（重複 SourceDoc `meta_vistara_isca_2026` ↔ `meta_vistara_isca_2026_counter_path`；plan §0.3 不修，列結案待決）。

```text
# 系統健康審查 — 2026-09-24

## 🟢 sole_source 單一來源（L8 weak）

_(none)_

## 🟢 Claim/EdgeAssertion 缺 CITES

_(none)_

## 🔴 重複 SourceDoc（同 URL 不同 doc_id）

- `https://aisystemcodesign.github.io/papers/isca26/vistara_camera_ready.pdf` ← ['meta_vistara_isca_2026', 'meta_vistara_isca_2026_counter_path']

## 🟢 Graph schema 版本

- 圖：`2026-07-16-u3b` / repo 期望：`2026-07-16-u3b`

## 🟢 未處置 edge conflict（M1：active 引用邊必須為零）

_(none)_

## 🟢 TICKER_MAP 覆蓋率

_(none)_

## 🟢 Thesis 到期核查

_(none)_

## 🟢 L7 欄位完整性（核查頻率 + 48h 動作）

_(none)_

## 🟢 Memo 新鮮度（超過各自核查週期）

_(none)_

## 🟢 Engine C 新鮮度（73 檔，閾值 7 天）

_(none)_

## 🟢 財務核驗清單可跑性

_(none)_

## 🟢 Research Action 待 publish

_(none)_

## 🟢 Skills 同步（Claude Code / Codex）

_(none)_
exit=0
```

## 7. Phase 0 殭屍 grep（0／0／0 仍成立）

`python scripts/retired_mechanism_grep.py`

```text

## A 排序當驅動／首選
  code: 15 檔｜alpha/providers/graph_neo4j.py(5)、query/bottleneck.py(5)、webapp/materialize.py(4)、webapp/api.py(3)、crons/daily_brief_prompt.md(3)、webapp/contracts.py(2)、engine_b/cli.py(2)、thesis/lifecycle.json(2)
  static: 2 檔｜webapp/static/app.js(2)、webapp/static/app.js(2)
  skills: 3 檔｜skills/alpha-status/SKILL.md(8)、skills/daily-brief/SKILL.md(4)、skills/system-decompose/SKILL.md(1)
  tests: 6 檔｜tests/test_webapp_structure_table.py(10)、tests/test_structure_table.py(9)、tests/test_alpha_view_brief.py(1)、tests/test_daily_brief_skill.py(1)、tests/test_webapp_api.py(1)、tests/fixtures/golden/structural_bottleneck.json(1)
  config: 2 檔｜config/alpha_screen.json(1)、.agents/skills/alpha-status/SKILL.md(1)
  livedocs: 1 檔｜docs/ARCHITECTURE.md(7)
  docs: 35 檔｜docs/archive/roadmap-pre-alpha-refactor.md(14)、docs/archive/roadmap-pre-alpha-edge.md(13)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(12)、docs/ROADMAP.md(11)、docs/archive/roadmap-phase-delivery-log.md(11)、docs/archive/roadmap-alpha-edge-2026-09-22.md(10)、docs/brainstorms/2026-09-22-graph-first-direction-decision.md(10)、docs/brainstorms/2026-09-17-no-evidence-case-zoom-out.md(8)

## B 籃子 filter
  code: 10 檔｜scripts/outcome_if_settled_today.py(17)、crons/heartbeat.py(9)、webapp/materialize.py(5)、webapp/contracts.py(3)、alpha/abstention/contracts.py(2)、alpha/providers/market_normalization.py(2)、crons/daily_brief_prompt.md(2)、alpha/gap_closure.py(1)
  static: 2 檔｜webapp/static/app.js(6)、webapp/static/app.js(6)
  skills: 3 檔｜skills/daily-brief/SKILL.md(3)、skills/alpha-status/SKILL.md(1)、skills/lead-intake/SKILL.md(1)
  tests: 10 檔｜tests/test_opinion_stance.py(6)、tests/test_wipeout_flags.py(6)、tests/test_heartbeat.py(4)、tests/test_routine_prompts.py(3)、tests/test_webapp_positions.py(2)、tests/test_absence_semantics.py(1)、tests/test_market_quote_unit.py(1)、tests/test_nav_exposure.py(1)
  config: 2 檔｜config/alpha_screen.json(3)、config/sector_anchors.json(1)
  livedocs: 3 檔｜docs/ARCHITECTURE.md(5)、CONCEPTS.md(3)、docs/OPERATIONS.md(1)
  docs: 30 檔｜docs/archive/roadmap-phase-delivery-log.md(40)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(32)、docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(31)、docs/archive/roadmap-backlog-log.md(30)、docs/ROADMAP.md(28)、docs/brainstorms/2026-09-17-no-evidence-case-zoom-out.md(24)、docs/archive/roadmap-alpha-edge-2026-09-22.md(18)、docs/reports/2026-09-22-phase0-baseline.md(15)

## C 估值／隱含報酬／尺
  code: 27 檔｜alpha/fundamental/contracts.py(13)、briefing/alpha_view/builder.py(12)、alpha/fundamental/assumptions.py(8)、briefing/analyst_view/compose.py(8)、briefing/analyst_view/contracts.py(6)、briefing/alpha_view/contracts.py(5)、webapp/materialize.py(5)、crons/heartbeat.py(5)
  static: 2 檔｜webapp/static/app.js(6)、webapp/static/app.js(6)
  skills: 2 檔｜skills/alpha-status/SKILL.md(2)、skills/research-drain/SKILL.md(1)
  tests: 17 檔｜tests/test_webapp_materialize.py(14)、tests/test_refresh_engine.py(12)、tests/test_webapp_api.py(12)、tests/test_alpha_investment_view.py(11)、tests/test_analyst_view.py(8)、tests/test_full_chain_acceptance.py(7)、tests/test_gap_closure.py(5)、tests/test_opinion_stance.py(5)
  config: 1 檔｜config/engine_c_observation_fields.json(1)
  livedocs: 3 檔｜docs/ARCHITECTURE.md(19)、CONCEPTS.md(9)、docs/OPERATIONS.md(5)
  docs: 30 檔｜docs/archive/roadmap-pre-alpha-edge.md(63)、docs/archive/2026-09-23-phase0-retired-sections.md(35)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(34)、docs/archive/roadmap-backlog-log.md(21)、docs/ARCHITECTURE.md(19)、docs/ROADMAP.md(19)、docs/reports/2026-09-07-coverage-pilot.md(10)、docs/reports/2026-09-07-full-chain-adversarial-acceptance.md(10)

## D 多年反向橋／要幾倍
  code: 10 檔｜briefing/analyst_view/compose.py(3)、webapp/contracts.py(3)、webapp/materialize.py(3)、alpha/contracts.py(2)、alpha/models/session_assessor.py(2)、briefing/cli.py(2)、briefing/alpha_view/contracts.py(2)、briefing/alpha_view/sources.py(2)
  static: 2 檔｜webapp/static/app.js(1)、webapp/static/app.js(1)
  tests: 3 檔｜tests/test_investor_brief.py(1)、tests/test_webapp_coverage_watches.py(1)、tests/test_webapp_structure_table.py(1)
  livedocs: 2 檔｜CONCEPTS.md(3)、docs/ARCHITECTURE.md(1)
  docs: 10 檔｜docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(23)、docs/ROADMAP.md(20)、docs/archive/roadmap-alpha-edge-2026-09-22.md(18)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(16)、docs/archive/roadmap-phase-delivery-log.md(14)、docs/reports/2026-09-22-phase0-baseline.md(10)、docs/reports/2026-09-23-phase0-closeout.md(8)、docs/archive/roadmap-completion-gate-log.md(6)

## E 賭注四價／variant overlay
  code: 19 檔｜briefing/alpha_view/builder.py(8)、alpha/narrative/contracts.py(4)、alpha/fundamental/contracts.py(3)、briefing/alpha_view/sources.py(3)、briefing/analyst_view/compose.py(3)、briefing/analyst_view/contracts.py(3)、alpha/legacy_axes.py(2)、alpha/abstention/contracts.py(2)
  static: 2 檔｜webapp/static/app.js(6)、webapp/static/app.js(6)
  skills: 2 檔｜skills/alpha-status/SKILL.md(2)、skills/research-drain/SKILL.md(1)
  tests: 11 檔｜tests/test_absence_semantics.py(3)、tests/test_alpha_legacy_conversion.py(2)、tests/test_investor_brief.py(2)、tests/test_webapp_api.py(2)、tests/test_webapp_materialize.py(2)、tests/fixtures/decision_lab/sive_reference_design.json(2)、tests/test_analyst_view.py(1)、tests/test_decision_blockers.py(1)
  config: 2 檔｜config/decision_blockers.json(2)、config/engine_c_observation_fields.json(1)
  livedocs: 3 檔｜CONCEPTS.md(6)、docs/ARCHITECTURE.md(4)、docs/OPERATIONS.md(3)
  docs: 31 檔｜docs/archive/roadmap-alpha-edge-2026-09-22.md(19)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(17)、docs/ROADMAP.md(14)、docs/archive/roadmap-backlog-log.md(13)、docs/archive/roadmap-phase-delivery-log.md(10)、docs/archive/roadmap-completion-gate-log.md(8)、docs/brainstorms/2026-09-16-alpha-edge-new-session-prompt.md(8)、docs/archive/roadmap-pre-alpha-edge.md(7)

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
  docs: 62 檔｜docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(63)、docs/archive/roadmap-pre-alpha-edge.md(44)、docs/plans/2026-08-28-001-refactor-bottleneck-ranking-terminus-plan.md(42)、docs/plans/2026-07-21-001-feat-action-oriented-alpha-decision-lab-plan.md(41)、docs/archive/roadmap-pre-alpha-refactor.md(35)、docs/plans/2026-07-22-001-feat-engine-d-operational-workflow-plan.md(32)、docs/refactor/target-architecture.md(32)、docs/OPERATIONS.md(29)

## H 估值模型 valuation/fundamental
  code: 20 檔｜engine_c/estimates.py(15)、alpha/providers/fundamentals.py(12)、briefing/alpha_view/builder.py(8)、briefing/alpha_view/changes.py(8)、engine_c/db.py(7)、engine_c/checklist.py(5)、engine_c/market_data.py(5)、alpha/contracts.py(4)
  tests: 20 檔｜tests/test_coverage_pilot_generalization.py(9)、tests/test_estimate_revision.py(6)、tests/test_alpha_investment_view.py(3)、tests/test_alpha_vertical_slice.py(3)、tests/test_analyst_view.py(3)、tests/test_consensus_coverage_collapse.py(3)、tests/test_overlay_scope_gate.py(3)、tests/test_refresh_engine.py(3)
  livedocs: 1 檔｜CONCEPTS.md(1)
  docs: 13 檔｜docs/archive/roadmap-pre-alpha-edge.md(13)、docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md(7)、docs/archive/roadmap-backlog-log.md(6)、docs/refactor/current-architecture.md(5)、docs/plans/2026-07-08-004-feat-investment-query-gap-audit-plan.md(4)、docs/ROADMAP.md(3)、docs/archive/agents-pre-graph-first-2026-09-22.md(1)、docs/refactor/phase-1-plan.md(1)

## 驗收（差集；Phase 0 結案要三個數字都是 0）
  未列 keep-list 的命中（檔，組）數：0
  已列但不再命中（腐壞條目）數：0
  keep-list 條目數：288｜理由類別不合法：0
exit=0
```

## 8. 備份

`python scripts/backup_private.py status` — 最後一次 **2026-09-19**（Drive `skipped`）；目前**沒有任何排程在跑備份**。

```text
{
  "artifacts": {
    "decision_lab.db": {
      "bytes": 14983168,
      "sha256": "073d7235f78ad874e28573af1a5477282ada96f954c5d19d1638e1fac18af1e0"
    },
    "engine_b_state.zip": {
      "bytes": 4147038,
      "sha256": "5c25cbc951d3114f64091dbcb871ed510bd06a7d223ae400a8f9aa327a923f82"
    },
    "engine_c.db": {
      "bytes": 5013504,
      "sha256": "60bfe2e230cbf236bcaff41a90661f89b964d13798fa5ab43dddd07d5b5a3184"
    },
    "files.zip": {
      "bytes": 62265946,
      "sha256": "8b2de264302c56706dad83980268b510d9416d2ff724c0ae40f4948dbec51427"
    },
    "neo4j_export.json": {
      "bytes": 3350908,
      "sha256": "c6feb2b5626e7eef2eb0a4f6d6b7824569ff14523392eaf3153d6cf4d39cc61d"
    }
  },
  "backup_dir": "backups/20260919T024734Z",
  "backup_id": "20260919T024734Z",
  "created_at": "2026-09-19T02:47:42.180349+00:00",
  "drive": {
    "status": "skipped"
  },
  "engine_b_state_members": 13,
  "files_zip_members": 993,
  "neo4j": {
    "nodes": 2641,
    "relationships": 5954
  },
  "restore_verification": {
    "backup_id": "20260919T024734Z",
    "verified_at": "2026-09-19T02:47:53.376737+00:00"
  }
}
exit=0
```

## 9. 舊 Decision Store（A5，只准讀；plan 不可越線 2）

以 `?mode=ro` URI 連線計數（只算 `*.db`；同目錄 daily 會寫的 `portfolio_risk_snapshots.jsonl`、`outcome_aggregate.json`／`.jsonl` 不在比對範圍）：

```text
backup_pre_v8_20260818T021452.db sha256=e887b3d458621e4cd7bb66913690d47d263d7188f9bbc1bacb4bc16ec57de350 live_choices=0 bytes=4804608
backup_pre_v9_20260902T032020Z.db sha256=af3dc690ce836b6026d86946c388d19f1500139287469f0f9fbe8711c4819d39 live_choices=1 bytes=11038720
decision_lab.db sha256=e99d1c79fd22dbe1099f30c4e06f2d1188f26a8cbfa987a27cd8842530951810 live_choices=1 bytes=16166912
```

**與 Phase 0 基準（`docs/reports/2026-09-22-phase0-baseline.md` §6）三個檔 sha256、`live_choices` 逐字相同。結案時必須仍相同。**

```python
import hashlib,glob,sqlite3,os,pathlib
for p in sorted(glob.glob('library/private/decision_lab/*.db')):
    h=hashlib.sha256(open(p,'rb').read()).hexdigest()
    c=sqlite3.connect(pathlib.Path(p).resolve().as_uri()+'?mode=ro',uri=True)
    print(os.path.basename(p),'sha256='+h,'live_choices=%d'%c.execute('select count(*) from live_choices').fetchone()[0],'bytes=%d'%os.path.getsize(p))
```

## 10. thesis 反證條目（驗收①分母的 thesis 部分）

依標題含「推翻」定位、數到下一個任何層級標題為止（`- ` 或 `1. ` 開頭的行）；現行 memo 以 `thesis/lifecycle.json` 的 `memo` 為準：

| thesis | lifecycle | 現行 memo | 反證標題 | 條目數 | 行號 |
|---|---|---|---|---|---|
| `axt_inp` | active | `thesis/axt_inp_v1_lane_memo.md` | L103 `## 7. 什麼會推翻這個 thesis` | **6** | 105、106、108、109、110、111 |
| `coherent_cpo` | revised | `thesis/coherent_cpo_v2_lane_memo.md` | L39 `## 6. 什麼會推翻這個 thesis` | **5** | 41–45 |
| `sivers` | active | `thesis/sivers_v4_lane_memo.md` | L56 `## 6. 什麼會推翻這個 Thesis（Disproof Conditions）` | **5** | 58–62 |

**合計 16**（與 plan §0.2 相同）。

## 11. 讀圖 ledger（驗收①分母的讀圖部分）

`python -m alpha structure-reading <node> --format json` 的 `current`：

| 節點 | 紀錄數 | 現行 reading_id |
|---|---|---|
| `mat:inp_substrate` | 5 | `sr_bc1ccb568c8886c0` |
| `tech:cw_dfb_laser` | 3 | `sr_caac0acae9a1c1cf` |

合計 8 筆紀錄、**現行 2 份**；`parse_errors` 皆空。兩份現行讀圖的反證條數在 Step 1.6 逐字列出後定數。

## 12. 今天的心跳原文（2026-09-24 07:00 排程產出，`library/private/heartbeat/heartbeat_2026-09-24.md`）

注意段 3「未 triage 0｜…（零＝真的沒有，不是沒跑）」**今天是假的**：harvest 最後一輪 2026-09-22 05:33（Codex daily 暫停），這正是 Step 1.2a 要修的 L13 同形。

```markdown
# Daily 心跳 — 2026-09-24 07:00 台北標準時間

> 零 LLM、零網路：只讀本機 authority 與已 materialize 的 state。**不判讀、不研究、不下單。**
> 它回答「系統還活著、這些數字是多少」；要決定什麼、要研究什麼不在這裡。

## 1. 資料新鮮
- harvest 來源 36 個｜失敗 0 個｜最後一輪 2026-09-22 05:33
- 本月 X 花費 $0.06 / 上限 $10.00
- 行情 14 檔｜最新完整交易日 2026-09-18 ～ 2026-09-21｜降級 3 檔：006208.TW（quarantined）、00981A.TW（quarantined）、DRAM（insufficient_history）
- 台股月營收 7/7 檔｜最新 2026-08｜已跟上公告期限
- FX 觀測 4 檔｜最新 as_of 2026-09-23（1 天前，容忍 ±3 天）｜全部在窗內
- APP artifact 今天已 materialize 0 份｜**不是今天的 7 份**：account_scorecard、beta、coverage、positions、structure_readings、structure_table、watches

## 2. 變了什麼
- 事件監看：本輪該查 2｜已觸發未消費 0｜到期 0
- thesis：active 2、revised 1｜該核查 0 檔
- 候選狀態板未落地（not_yet_recorded）：籃子 filter、目標價與多年視角已於 Phase 0 退役；接手的候選狀態板要到 Phase 3 才落地
- 結構讀圖 2 份｜現行 2｜**該重讀 0**（stale 0／過期 0；低級 0 不進佇列）
- 已定價嗎（財務三題）未落地（not_yet_recorded）：目標倍數背離計數器已於 2026-09-23 隨估值鏈退役；「已定價嗎」由 Phase 3 財務三題回答，主參照是自己的歷史、不設門檻
- beta 報告狀態 degraded｜警告 4 條：drawn_debt_present、issuer_concentration_warning:TSMC、issuer_lookthrough_partial、unclassified_holdings_assumed_unlevered_direct_issuer

## 3. 佇列
- **未 triage 0**｜新 harvest lead 需要分流（零＝真的沒有，不是沒跑）｜分類層每日上限 30
- pq1 可做 3｜機械段待清 0
- **pq2 球在你手上 0**｜池中未結案 2（差額＝等事件或已在 pq1 跑）
- 到期歸檔 watch 0｜事件監看總數 95｜無到期的等待 0

## 4. 部位
- alpha（瓶頸研究衛星）占已投入非現金 1.72%｜**只觀測不設目標**（D1）
- 追蹤表 22 檔｜等權絕對 7.55%｜對 QQQ 超額 3.42%｜正式結算過 2 筆
- 入圖前已漲（chasing）8/22 檔
- 賭注帳／量的候選／要幾倍：籃子 filter、目標價與多年視角已於 Phase 0 退役；接手的候選狀態板要到 Phase 3 才落地（not_yet_recorded）
- 歸零旗標彙總：四盞燈的彙總原本由籃子 artifact 產生，籃子已退役；Phase 3 候選板接手前沒有上游（upstream_unavailable）　←逐檔那盞燈仍在個股頁，停的只有這個彙總計數
- 結構表 222 條邊分佈在 9 個需求錨（前三：tech:ai_switch 110、tech:optical_scale_up 38、tech:essential_chips_mature_node 29）——**N 檔不等於 N 個獨立機會**
- power-law：籃子總報酬 7.55%｜最大單檔 AXTI 3.47%／其餘 21 檔 4.08%｜曾達 2 倍 1/22（現價仍達 0）｜**還沒有一檔滿 12 個月**（最長持有 64 天）
- 賭注收斂：**還沒有任何一檔寫下賭注**（掃過 22 檔）——這不是 0%，是還沒有分子也沒有分母
- **alpha 全歸零淨值少 1.60%**（alpha 佔 NAV 的比例本身；純呈現、零門檻，尺寸仍由使用者決定）

## 5. 帳號計分表
- 計分表是 weekly 才算的，本輪是 daily（method_not_applicable）
```

## 13. 個股頁文字 digest（結案 gate 3 的基準）

`python scripts/analyst_view_text_digest.py --per-panel`（結案時照 Phase 0 在同一天 materialize 前後再比一次）

```text
# analyst view 文字 digest（73 檔；目錄 C:\Users\Cheng\code\StockBotv2\library\private\app\analyst_view）
# 只 hash 敘事文字：title／display_label／datum 的 value・text・label・note・reason／notes／questions
000660.KS	286af31cd2289b69	our_bet=0／brief=29／argument=13／research=58
    000660.KS.our_bet	e3b0c44298fc1c14	0 段
    000660.KS.brief	f9967e4d97a5bd6a	29 段
    000660.KS.argument	f50bc5981d6aefa8	13 段
    000660.KS.research	5f1dacb68469b40e	58 段
002472.SZ	e9789c577bef3b58	our_bet=0／brief=29／argument=13／research=58
    002472.SZ.our_bet	e3b0c44298fc1c14	0 段
    002472.SZ.brief	f9967e4d97a5bd6a	29 段
    002472.SZ.argument	9fa971eb2f60d793	13 段
    002472.SZ.research	35f537de4ce28d09	58 段
005930.KS	85e3bee5b3f2334f	our_bet=0／brief=29／argument=13／research=58
    005930.KS.our_bet	e3b0c44298fc1c14	0 段
    005930.KS.brief	f9967e4d97a5bd6a	29 段
    005930.KS.argument	c728bdf6db6d81d0	13 段
    005930.KS.research	753bdd9753b2b86f	58 段
012330.KS	0579eda3a81dc4d3	our_bet=0／brief=29／argument=13／research=59
    012330.KS.our_bet	e3b0c44298fc1c14	0 段
    012330.KS.brief	f9967e4d97a5bd6a	29 段
    012330.KS.argument	9b242727123e2028	13 段
    012330.KS.research	7ecdc474ab0b3d84	59 段
2301.TW	cda038bffc898f6e	our_bet=0／brief=29／argument=13／research=59
    2301.TW.our_bet	e3b0c44298fc1c14	0 段
    2301.TW.brief	f9967e4d97a5bd6a	29 段
    2301.TW.argument	b8755979a41cd668	13 段
    2301.TW.research	996abd37b45a26d8	59 段
2455.TW	415fbe53009fdccb	our_bet=0／brief=29／argument=13／research=63
    2455.TW.our_bet	e3b0c44298fc1c14	0 段
    2455.TW.brief	f9967e4d97a5bd6a	29 段
    2455.TW.argument	956aa84673598e5a	13 段
    2455.TW.research	a664dd6143325c03	63 段
300308.SZ	d75bcae84cee919f	our_bet=0／brief=29／argument=13／research=59
    300308.SZ.our_bet	e3b0c44298fc1c14	0 段
    300308.SZ.brief	f9967e4d97a5bd6a	29 段
    300308.SZ.argument	af48f4581e74d5db	13 段
    300308.SZ.research	e772bc5d5fb802a9	59 段
3081.TWO	8d5b46c8cc0b6cfd	our_bet=0／brief=29／argument=13／research=58
    3081.TWO.our_bet	e3b0c44298fc1c14	0 段
    3081.TWO.brief	f9967e4d97a5bd6a	29 段
    3081.TWO.argument	a31e69fdfaaf1bc2	13 段
    3081.TWO.research	960ba9f80d6b479a	58 段
3105.TWO	f248d6859fdea999	our_bet=0／brief=29／argument=13／research=58
    3105.TWO.our_bet	e3b0c44298fc1c14	0 段
    3105.TWO.brief	f9967e4d97a5bd6a	29 段
    3105.TWO.argument	2e188e06f00bd061	13 段
    3105.TWO.research	ac0554cdfaf0e3fa	58 段
3363.TWO	a1ab6b8433fb1046	our_bet=0／brief=29／argument=13／research=58
    3363.TWO.our_bet	e3b0c44298fc1c14	0 段
    3363.TWO.brief	f9967e4d97a5bd6a	29 段
    3363.TWO.argument	d6d644264350fac3	13 段
    3363.TWO.research	425202db798f70dd	58 段
4971.TWO	702af14a9ba0c8e5	our_bet=0／brief=29／argument=13／research=58
    4971.TWO.our_bet	e3b0c44298fc1c14	0 段
    4971.TWO.brief	f9967e4d97a5bd6a	29 段
    4971.TWO.argument	cd7d926e404b2732	13 段
    4971.TWO.research	6bb2add3be0e36cc	58 段
4979.TWO	5655587507dc912b	our_bet=0／brief=29／argument=13／research=58
    4979.TWO.our_bet	e3b0c44298fc1c14	0 段
    4979.TWO.brief	f9967e4d97a5bd6a	29 段
    4979.TWO.argument	93282c04b975f16b	13 段
    4979.TWO.research	3b178107c10b2f18	58 段
5016.T	1c918e47f9abbe9a	our_bet=0／brief=29／argument=13／research=58
    5016.T.our_bet	e3b0c44298fc1c14	0 段
    5016.T.brief	f9967e4d97a5bd6a	29 段
    5016.T.argument	e83fc8e04fd428d3	13 段
    5016.T.research	04ddaa6aefe03734	58 段
5802.T	7e7a7766d5314f60	our_bet=0／brief=29／argument=13／research=58
    5802.T.our_bet	e3b0c44298fc1c14	0 段
    5802.T.brief	f9967e4d97a5bd6a	29 段
    5802.T.argument	e0a6ada202ffd583	13 段
    5802.T.research	dc509a54877240b6	58 段
6268.T	e1b32b6047adc631	our_bet=0／brief=29／argument=13／research=74
    6268.T.our_bet	e3b0c44298fc1c14	0 段
    6268.T.brief	f9967e4d97a5bd6a	29 段
    6268.T.argument	bd3e3ff8947e5af6	13 段
    6268.T.research	d9c788b8d4ed9432	74 段
6324.T	62732170ca83c945	our_bet=0／brief=29／argument=13／research=60
    6324.T.our_bet	e3b0c44298fc1c14	0 段
    6324.T.brief	f9967e4d97a5bd6a	29 段
    6324.T.argument	626896a5b5272bb7	13 段
    6324.T.research	98c2a24e6eac4e91	60 段
6481.T	d758ce1f23110167	our_bet=0／brief=29／argument=13／research=66
    6481.T.our_bet	e3b0c44298fc1c14	0 段
    6481.T.brief	f9967e4d97a5bd6a	29 段
    6481.T.argument	4b86671f3cd6c672	13 段
    6481.T.research	cd4016f4e3eb6d69	66 段
6594.T	ce575084627711fe	our_bet=0／brief=29／argument=13／research=74
    6594.T.our_bet	e3b0c44298fc1c14	0 段
    6594.T.brief	f9967e4d97a5bd6a	29 段
    6594.T.argument	ee587c3c1eed6bbf	13 段
    6594.T.research	cc5382c68614fc24	74 段
6680.HK	06b66444c0de74dd	our_bet=0／brief=29／argument=13／research=58
    6680.HK.our_bet	e3b0c44298fc1c14	0 段
    6680.HK.brief	f9967e4d97a5bd6a	29 段
    6680.HK.argument	b8b9cf0c551282e7	13 段
    6680.HK.research	737bc3c9f0744ed3	58 段
688017.SS	a31fac05317d600f	our_bet=0／brief=29／argument=13／research=60
    688017.SS.our_bet	e3b0c44298fc1c14	0 段
    688017.SS.brief	f9967e4d97a5bd6a	29 段
    688017.SS.argument	7d3e3fc2f06eba2a	13 段
    688017.SS.research	d1542c38c26531ba	60 段
688836.SS	6ddee90f17c5c992	our_bet=0／brief=29／argument=13／research=64
    688836.SS.our_bet	e3b0c44298fc1c14	0 段
    688836.SS.brief	f9967e4d97a5bd6a	29 段
    688836.SS.argument	479c52b94a294f1d	13 段
    688836.SS.research	b3f61b7a8771cdb7	64 段
AAOI	eb4336faae3ae052	our_bet=0／brief=29／argument=13／research=58
    AAOI.our_bet	e3b0c44298fc1c14	0 段
    AAOI.brief	f9967e4d97a5bd6a	29 段
    AAOI.argument	d4db62e657868820	13 段
    AAOI.research	e8885a16633c10b7	58 段
AAPL	78f3d94c4c75c37e	our_bet=0／brief=29／argument=13／research=59
    AAPL.our_bet	e3b0c44298fc1c14	0 段
    AAPL.brief	f9967e4d97a5bd6a	29 段
    AAPL.argument	82a1dc5eadf24ac5	13 段
    AAPL.research	a003dc701c151926	59 段
AEHR	106cebc803f4a9ee	our_bet=0／brief=29／argument=13／research=58
    AEHR.our_bet	e3b0c44298fc1c14	0 段
    AEHR.brief	f9967e4d97a5bd6a	29 段
    AEHR.argument	48db55e20c346d3c	13 段
    AEHR.research	30ffe5c0d1de01e8	58 段
AEVA	96c022bcc9604a36	our_bet=0／brief=29／argument=13／research=58
    AEVA.our_bet	e3b0c44298fc1c14	0 段
    AEVA.brief	f9967e4d97a5bd6a	29 段
    AEVA.argument	ec7c2d0db263e2a6	13 段
    AEVA.research	b5e3753cc15b1e43	58 段
AMAT	7650efa852c2df3c	our_bet=0／brief=29／argument=13／research=58
    AMAT.our_bet	e3b0c44298fc1c14	0 段
    AMAT.brief	f9967e4d97a5bd6a	29 段
    AMAT.argument	acfc5f9765fdadeb	13 段
    AMAT.research	175cf94212762ae5	58 段
AMD	e5372120788d7ba2	our_bet=0／brief=29／argument=13／research=58
    AMD.our_bet	e3b0c44298fc1c14	0 段
    AMD.brief	f9967e4d97a5bd6a	29 段
    AMD.argument	82cee7a39bb270f3	13 段
    AMD.research	ab5a30d6b4945777	58 段
ANET	1c732b989bd4c6f6	our_bet=0／brief=29／argument=13／research=58
    ANET.our_bet	e3b0c44298fc1c14	0 段
    ANET.brief	f9967e4d97a5bd6a	29 段
    ANET.argument	942e9d59226ac68c	13 段
    ANET.research	dda54517f24d1664	58 段
APO	b3afed12ad4aeda7	our_bet=0／brief=29／argument=13／research=62
    APO.our_bet	e3b0c44298fc1c14	0 段
    APO.brief	f9967e4d97a5bd6a	29 段
    APO.argument	d098c5f4b33760c0	13 段
    APO.research	81a01fa1437e73f2	62 段
AVGO	e13bd29d1760c7de	our_bet=0／brief=29／argument=13／research=58
    AVGO.our_bet	e3b0c44298fc1c14	0 段
    AVGO.brief	f9967e4d97a5bd6a	29 段
    AVGO.argument	c1f0c566deec3aec	13 段
    AVGO.research	e45f46e60d37c29a	58 段
AXTI	b76c9ac04da7d92f	our_bet=1／brief=32／argument=13／research=59
    AXTI.our_bet	003b60768d92d5ff	1 段
    AXTI.brief	30429cf894eac969	32 段
    AXTI.argument	07629c47af719736	13 段
    AXTI.research	c37c2478c2c3d45e	59 段
BX	f9b87fd515b15dff	our_bet=0／brief=29／argument=13／research=62
    BX.our_bet	e3b0c44298fc1c14	0 段
    BX.brief	f9967e4d97a5bd6a	29 段
    BX.argument	69373c630922f179	13 段
    BX.research	81a01fa1437e73f2	62 段
CCXI	630bed2038dda768	our_bet=0／brief=29／argument=13／research=60
    CCXI.our_bet	e3b0c44298fc1c14	0 段
    CCXI.brief	f9967e4d97a5bd6a	29 段
    CCXI.argument	ecedf2bd20ace99a	13 段
    CCXI.research	f421905977cf178a	60 段
CDNS	af1a1a5501c0b793	our_bet=0／brief=29／argument=13／research=58
    CDNS.our_bet	e3b0c44298fc1c14	0 段
    CDNS.brief	f9967e4d97a5bd6a	29 段
    CDNS.argument	24c7bf334542a8a5	13 段
    CDNS.research	a56e928476ecacd6	58 段
COHR	9138a4ef94b203f1	our_bet=1／brief=32／argument=13／research=59
    COHR.our_bet	eed12e446ba752f5	1 段
    COHR.brief	8ba51fdbf43f44de	32 段
    COHR.argument	7d97a411802d1a0c	13 段
    COHR.research	854f793962efb8c3	59 段
CRWV	938afaf59fc9f206	our_bet=0／brief=29／argument=13／research=58
    CRWV.our_bet	e3b0c44298fc1c14	0 段
    CRWV.brief	f9967e4d97a5bd6a	29 段
    CRWV.argument	70e70f89a3065e65	13 段
    CRWV.research	8c3b4accae149114	58 段
ENA.V	a29706607d96ab73	our_bet=0／brief=29／argument=13／research=60
    ENA.V.our_bet	e3b0c44298fc1c14	0 段
    ENA.V.brief	f9967e4d97a5bd6a	29 段
    ENA.V.argument	05c616bf8b7643f0	13 段
    ENA.V.research	f421905977cf178a	60 段
FN	94a211be6ac56105	our_bet=0／brief=29／argument=13／research=58
    FN.our_bet	e3b0c44298fc1c14	0 段
    FN.brief	f9967e4d97a5bd6a	29 段
    FN.argument	453fa9fede4e846c	13 段
    FN.research	24631fc8071b9edf	58 段
GFS	00093f0f95b6d9e1	our_bet=0／brief=29／argument=13／research=58
    GFS.our_bet	e3b0c44298fc1c14	0 段
    GFS.brief	f9967e4d97a5bd6a	29 段
    GFS.argument	34d46b5b9f264d81	13 段
    GFS.research	9b0572a9a7622452	58 段
GLW	d8c2ab6db407aa24	our_bet=0／brief=29／argument=13／research=58
    GLW.our_bet	e3b0c44298fc1c14	0 段
    GLW.brief	f9967e4d97a5bd6a	29 段
    GLW.argument	737959b290a0ea1a	13 段
    GLW.research	1dff572eb9b68500	58 段
GOOGL	b27238504df5a158	our_bet=0／brief=29／argument=13／research=58
    GOOGL.our_bet	e3b0c44298fc1c14	0 段
    GOOGL.brief	f9967e4d97a5bd6a	29 段
    GOOGL.argument	34d68921e1e79423	13 段
    GOOGL.research	c42ad512f673d153	58 段
GXO	4068aa583b940f51	our_bet=0／brief=29／argument=13／research=58
    GXO.our_bet	e3b0c44298fc1c14	0 段
    GXO.brief	f9967e4d97a5bd6a	29 段
    GXO.argument	c9a7c662dee832fa	13 段
    GXO.research	fb9b86e001550898	58 段
HEXA-B.ST	0a4bfdf74ba5af09	our_bet=0／brief=29／argument=13／research=58
    HEXA-B.ST.our_bet	e3b0c44298fc1c14	0 段
    HEXA-B.ST.brief	f9967e4d97a5bd6a	29 段
    HEXA-B.ST.argument	28c2f6121b3dc5cb	13 段
    HEXA-B.ST.research	502ea072a38c6bc0	58 段
HIMX	c530f330d9d12cce	our_bet=0／brief=29／argument=13／research=58
    HIMX.our_bet	e3b0c44298fc1c14	0 段
    HIMX.brief	f9967e4d97a5bd6a	29 段
    HIMX.argument	04d0c00609445f7a	13 段
    HIMX.research	0d4383dbd81a24ca	58 段
INTC	9b63023fd934d810	our_bet=0／brief=29／argument=13／research=58
    INTC.our_bet	e3b0c44298fc1c14	0 段
    INTC.brief	f9967e4d97a5bd6a	29 段
    INTC.argument	827aeb31556e955c	13 段
    INTC.research	d0049ee1841f1c4e	58 段
IQE.L	1ffb717a96b556d3	our_bet=0／brief=29／argument=13／research=58
    IQE.L.our_bet	e3b0c44298fc1c14	0 段
    IQE.L.brief	f9967e4d97a5bd6a	29 段
    IQE.L.argument	e57c8f32d63827a6	13 段
    IQE.L.research	abd189d7e03b6275	58 段
IREN	a6372c5129475cc9	our_bet=0／brief=29／argument=13／research=61
    IREN.our_bet	e3b0c44298fc1c14	0 段
    IREN.brief	f9967e4d97a5bd6a	29 段
    IREN.argument	849c3ec47ac7902d	13 段
    IREN.research	8598f848f6fe691f	61 段
JBL	08434e553476f975	our_bet=0／brief=29／argument=13／research=62
    JBL.our_bet	e3b0c44298fc1c14	0 段
    JBL.brief	f9967e4d97a5bd6a	29 段
    JBL.argument	489e219f66d23146	13 段
    JBL.research	81a01fa1437e73f2	62 段
LITE	09ecf63f956f90e5	our_bet=1／brief=32／argument=13／research=78
    LITE.our_bet	fddad13c577a371a	1 段
    LITE.brief	8d22b3da5f0e3187	32 段
    LITE.argument	68eba0c66d616638	13 段
    LITE.research	43b30e46685390a0	78 段
LRCX	cea28966d8f5b5b9	our_bet=0／brief=29／argument=13／research=58
    LRCX.our_bet	e3b0c44298fc1c14	0 段
    LRCX.brief	f9967e4d97a5bd6a	29 段
    LRCX.argument	a294567ac7d821b0	13 段
    LRCX.research	3ac6315c5d83ea58	58 段
LYC.AX	b11f3e9591fabff3	our_bet=0／brief=29／argument=13／research=62
    LYC.AX.our_bet	e3b0c44298fc1c14	0 段
    LYC.AX.brief	f9967e4d97a5bd6a	29 段
    LYC.AX.argument	f16e31702e3d9739	13 段
    LYC.AX.research	988654a304a04f82	62 段
META	a517c924e9d77998	our_bet=0／brief=29／argument=13／research=58
    META.our_bet	e3b0c44298fc1c14	0 段
    META.brief	f9967e4d97a5bd6a	29 段
    META.argument	bc6615ab38dda6f0	13 段
    META.research	9edfcd0005fe2c70	58 段
MP	30aae1aca5f85f4a	our_bet=0／brief=29／argument=13／research=60
    MP.our_bet	e3b0c44298fc1c14	0 段
    MP.brief	f9967e4d97a5bd6a	29 段
    MP.argument	51e6604856dc51a2	13 段
    MP.research	53e157f3d72d7da7	60 段
MRVL	d93ec0bf91863e42	our_bet=0／brief=29／argument=13／research=58
    MRVL.our_bet	e3b0c44298fc1c14	0 段
    MRVL.brief	f9967e4d97a5bd6a	29 段
    MRVL.argument	0776f7d2bdb14bdd	13 段
    MRVL.research	1bcdfd66b9011f3d	58 段
MSFT	8a632881ffc5851f	our_bet=0／brief=29／argument=13／research=58
    MSFT.our_bet	e3b0c44298fc1c14	0 段
    MSFT.brief	f9967e4d97a5bd6a	29 段
    MSFT.argument	e2707f325d7450d7	13 段
    MSFT.research	86a3b4fd6646945c	58 段
MTSI	d647c48ce7c744b9	our_bet=0／brief=29／argument=13／research=58
    MTSI.our_bet	e3b0c44298fc1c14	0 段
    MTSI.brief	f9967e4d97a5bd6a	29 段
    MTSI.argument	c70e280b812f16ad	13 段
    MTSI.research	b3fb57e667526cb6	58 段
MU	8f6ca893c85bc2ca	our_bet=0／brief=29／argument=13／research=63
    MU.our_bet	e3b0c44298fc1c14	0 段
    MU.brief	f9967e4d97a5bd6a	29 段
    MU.argument	3a85f5a9b2206f6c	13 段
    MU.research	dc3c361ae497d2ae	63 段
NBIS	bfec135852e5dd19	our_bet=0／brief=29／argument=13／research=59
    NBIS.our_bet	e3b0c44298fc1c14	0 段
    NBIS.brief	f9967e4d97a5bd6a	29 段
    NBIS.argument	803d411d6e0a1f26	13 段
    NBIS.research	49d8864709a4050b	59 段
NOVT	667398bb84ab6338	our_bet=0／brief=29／argument=13／research=58
    NOVT.our_bet	e3b0c44298fc1c14	0 段
    NOVT.brief	f9967e4d97a5bd6a	29 段
    NOVT.argument	fbfe567a95d2ab68	13 段
    NOVT.research	9bd3fd19f7034b00	58 段
NVDA	3926504429884082	our_bet=0／brief=29／argument=13／research=58
    NVDA.our_bet	e3b0c44298fc1c14	0 段
    NVDA.brief	f9967e4d97a5bd6a	29 段
    NVDA.argument	ce947280afa80458	13 段
    NVDA.research	46053908126f65e1	58 段
ORCL	a91b3766be70d3c5	our_bet=0／brief=29／argument=13／research=58
    ORCL.our_bet	e3b0c44298fc1c14	0 段
    ORCL.brief	f9967e4d97a5bd6a	29 段
    ORCL.argument	174fd9212414fcf8	13 段
    ORCL.research	c2f748a420ea8ae4	58 段
POET	1e3ded4df3b44d98	our_bet=0／brief=29／argument=13／research=58
    POET.our_bet	e3b0c44298fc1c14	0 段
    POET.brief	f9967e4d97a5bd6a	29 段
    POET.argument	2c9a78f489cd6693	13 段
    POET.research	f850878a5b818ac1	58 段
SHA0.DE	1baa91497497e87b	our_bet=0／brief=29／argument=13／research=62
    SHA0.DE.our_bet	e3b0c44298fc1c14	0 段
    SHA0.DE.brief	f9967e4d97a5bd6a	29 段
    SHA0.DE.argument	385f5298d826cfec	13 段
    SHA0.DE.research	f138b44fde13393d	62 段
SIVE.ST	5d3796c3c1040a09	our_bet=0／brief=29／argument=13／research=57
    SIVE.ST.our_bet	e3b0c44298fc1c14	0 段
    SIVE.ST.brief	f9967e4d97a5bd6a	29 段
    SIVE.ST.argument	8ab07410c013d3dc	13 段
    SIVE.ST.research	b589cf560bebc15e	57 段
SNDK	877efeece0e72a76	our_bet=0／brief=29／argument=13／research=58
    SNDK.our_bet	e3b0c44298fc1c14	0 段
    SNDK.brief	f9967e4d97a5bd6a	29 段
    SNDK.argument	aa18c63e2a3a1cc2	13 段
    SNDK.research	f6fd556ae6d29bcf	58 段
SOI.PA	d3f7c638284216bf	our_bet=0／brief=29／argument=13／research=59
    SOI.PA.our_bet	e3b0c44298fc1c14	0 段
    SOI.PA.brief	f9967e4d97a5bd6a	29 段
    SOI.PA.argument	e2e2201e4e534eb1	13 段
    SOI.PA.research	fc600a668423d8cc	59 段
TSEM	a760c95a9066e8ab	our_bet=0／brief=29／argument=13／research=60
    TSEM.our_bet	e3b0c44298fc1c14	0 段
    TSEM.brief	f9967e4d97a5bd6a	29 段
    TSEM.argument	eecbb708c82d5a3c	13 段
    TSEM.research	3516259b3fe311d5	60 段
TSLA	70ce2fc73e93ccf4	our_bet=0／brief=29／argument=13／research=60
    TSLA.our_bet	e3b0c44298fc1c14	0 段
    TSLA.brief	f9967e4d97a5bd6a	29 段
    TSLA.argument	308c3c4bf4118c94	13 段
    TSLA.research	59120571d31f6478	60 段
TSM	c4e05fa5fecf3595	our_bet=0／brief=29／argument=13／research=58
    TSM.our_bet	e3b0c44298fc1c14	0 段
    TSM.brief	f9967e4d97a5bd6a	29 段
    TSM.argument	6f3c15b8a2704056	13 段
    TSM.research	d152ff2672daf0e1	58 段
TXN	4240169e44667f7b	our_bet=0／brief=29／argument=13／research=58
    TXN.our_bet	e3b0c44298fc1c14	0 段
    TXN.brief	f9967e4d97a5bd6a	29 段
    TXN.argument	922a3d6c2dd9024d	13 段
    TXN.research	4e6a8dab7340997a	58 段
UMC	95afae3b00e23466	our_bet=0／brief=29／argument=13／research=58
    UMC.our_bet	e3b0c44298fc1c14	0 段
    UMC.brief	f9967e4d97a5bd6a	29 段
    UMC.argument	d195fd82e8931cba	13 段
    UMC.research	697819f2acdd85a5	58 段
XFAB.PA	a46059cfac04c5ef	our_bet=0／brief=29／argument=13／research=58
    XFAB.PA.our_bet	e3b0c44298fc1c14	0 段
    XFAB.PA.brief	f9967e4d97a5bd6a	29 段
    XFAB.PA.argument	35645c386cbbf7a3	13 段
    XFAB.PA.research	605dd6e68ae183bf	58 段
XPEV	013e2e8f325db47f	our_bet=0／brief=29／argument=13／research=58
    XPEV.our_bet	e3b0c44298fc1c14	0 段
    XPEV.brief	f9967e4d97a5bd6a	29 段
    XPEV.argument	312cf862678d15f7	13 段
    XPEV.research	77f35d82e9adb0d4	58 段
# TOTAL	3b53b1839e2aaace	73 檔
```

## 14. 舊排程工作的 XML（Step 1.2a 註冊範本）

完整原檔存於 `library/private/heartbeat/legacy_tasks/StockBotv2-Heartbeat.xml`、`StockBotv2-FxSync.xml`（gitignored）；
下面是同一份內容，只把本機使用者 SID 的中段遮掉。`schtasks /Query /TN <name> /XML`

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Alpha Edge D12 daily heartbeat: zero-LLM, zero-network. Runs crons/heartbeat_task.py then the existing Discord publisher. Independent of Codex so the heartbeat still fires when the LLM layer is down.</Description>
    <URI>\StockBotv2-Heartbeat</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-21-…-1001</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
    <IdleSettings>
      <Duration>PT10M</Duration>
      <WaitTimeout>PT1H</WaitTimeout>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
  </Settings>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-09-17T07:00:00+08:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\Users\Cheng\code\StockBotv2\.venv\Scripts\python.exe</Command>
      <Arguments>crons\heartbeat_task.py</Arguments>
      <WorkingDirectory>C:\Users\Cheng\code\StockBotv2</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <URI>\StockBotv2-FxSync</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-21-…-1001</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
    <IdleSettings>
      <Duration>PT10M</Duration>
      <WaitTimeout>PT1H</WaitTimeout>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
  </Settings>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-09-19T06:55:00+08:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\Users\Cheng\code\StockBotv2\.venv\Scripts\python.exe</Command>
      <Arguments>scripts\sync_fx_observations.py</Arguments>
      <WorkingDirectory>C:\Users\Cheng\code\StockBotv2</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```
