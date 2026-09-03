# Current Architecture — 重構前的實測盤點

> **性質：** Phase 0 產出物之一。**這份文件描述 2026-09-03 的實際狀態，不是設計意圖。**
> 每個數字都附查證命令（`AGENTS.md`「現況數字會過期，判準不會」）；重構期間若數字對不上，
> 相信命令不要相信本檔。
>
> 姊妹文件：[`target-architecture.md`](target-architecture.md)、
> [`engine-d-decomposition.md`](engine-d-decomposition.md)、
> [`roadmap-migration.md`](roadmap-migration.md)、[`phase-1-plan.md`](phase-1-plan.md)。

---

## 0. 一句話總結

**上游（Signal → Evidence → Knowledge Graph → 結構理解）已經是成熟資產；下游
（Economic Value Capture → Earnings Exposure → Expectation Gap → AlphaSignal）
在程式碼裡不存在；中間那一段——research reasoning——目前寄居在 Engine D 裡面。**

不是「Engine D 寫得不好」，是**它是唯一一個有 point-in-time 凍結能力的地方，
所以任何需要「當時看到什麼」的東西都被塞進去了**。重構要做的是把 research 的
point-in-time 需求獨立成 `ResearchContext`，Engine D 才減得下來。

---

## 1. Package 盤點（實測 2026-09-03）

查證：`git ls-files <pkg> | grep '\.py$' | xargs wc -l | tail -1`

| Package | 檔數 | 行數 | 現行角色 | 判定 |
|---|---:|---:|---|---|
| `decision_lab/` | 35 | **13,502** | Engine D ＋ alpha research ＋ portfolio ＋ risk ＋ beta 呈現 ＋ 備份 | 🔴 god package |
| `engine_b/` | 13 | 6,598 | leads 狀態機、pq1 排序、pq2 待辦池、event watch、hypotheses | 🟡 `todo.py` 2,597 行過載 |
| `mcp_server/` | 8 | 4,016 | 遠端 12 工具、Research Action 協定 | 🟢 邊界清楚 |
| `engine_c/` | 14 | 3,634 | 財務／行情／人工觀測 | 🟢 邊界清楚 |
| `query/` | 8 | 2,427 | 圖查詢：瓶頸排序、覆蓋掃描、衝突、健康稽核 | 🟡 事實上的 research provider，但無 contract |
| `loader/` | 8 | 2,337 | JSON → Neo4j、edge resolution、migrations | 🟢 |
| `thesis/` | 7 | 2,234 | lane memo、L9 gate、**investment policy**、lifecycle 排程 | 🔴 混了四種東西 |
| `fetchers/` | 9 | 2,208 | EDGAR／MOPS／arXiv／X／Google Sheet／TWSE | 🟢 |
| `engine_d_runtime/` | 3 | 1,269 | Engine D 的 concrete authority composition | 🟢 但 `adapters.py` 1,229 行 |
| `crons/` | 4 | 1,211 | harvest、weekly digest、freshness | 🟢 |
| `notifications/` | 2 | 806 | Discord outbound | 🟢 |
| `paper_portfolio/` | 1 | 717 | 已凍結；只當 e2e 獨立重放驗證器 | 🟡 test-only（已書面記錄理由） |
| `identity/` | 5 | 440 | company registry／currency／execution alias | 🟢 SSOT |
| `storage/` | 2 | 375 | SQLite/Postgres 抽象 | 🟢 |
| `scripts/` | 24 | 5,160 | 操作入口與 migration | 🟡 混了 one-shot migration 與常駐入口 |
| `tests/` | 126 | 27,513 | — | 🟢 密度高（≈37% 的總行數）。**baseline 2026-09-03：1,175 passed / 0 skipped** |

**生產碼合計約 47,000 行，測試 27,500 行。** 測試密度是這個 repo 最強的資產之一，
重構的每一步都必須靠它們當安全網。

---

## 2. 實測依賴圖（package 層）

以 AST 解析所有 `import` / `from ... import` 產生。箭頭方向 = 「A 匯入 B」。

```
                    ┌──────────────────────────────────────┐
   crons ──────────▶│                                      │
   scripts ────────▶│   engine_b        engine_c           │
                    │      │  ▲            │  ▲            │
                    │      │  │            │  │            │
                    │      ▼  │            ▼  │            │
                    │   mcp_server ◀──▶ query              │
                    │      │                  │            │
                    └──────┼──────────────────┼────────────┘
                           ▼                  ▼
                     decision_lab ◀────▶ engine_d_runtime
                           │  ▲                │
                           ▼  │                ▼
                        thesis ┘            engine_c
                           │
                           ▼
                   identity / storage      （葉節點，無反向依賴）
```

### 2.1 已量測的相依環（7 條）

| 環 | 具體 import | 問題 |
|---|---|---|
| `decision_lab` ↔ `engine_d_runtime` | `decision_lab.cli` → `engine_d_runtime.bootstrap`；`engine_d_runtime.adapters` → `decision_lab.ranking_view` / `nav_exposure` / `adapters.graph` | domain 反向依賴 composition 層，`workflow_ports` 的隔離只做到一半 |
| `decision_lab` ↔ `thesis` | `decision_lab.sizing` → `thesis.investment_policy`；`thesis.preconditions` → `decision_lab.bootstrap` | **investment policy 住在 research package** |
| `decision_lab` ↔ `engine_c` | `engine_c.technical` → `decision_lab.beta_policy`；`engine_c.cutover` → `decision_lab.redaction` | Engine C 讀 Engine D 的 policy 與 redaction |
| `engine_b` ↔ `mcp_server` | `engine_b.todo` → `mcp_server.research_actions`；`mcp_server.leads_tools` → `engine_b` | 待辦池直接讀 RA 檔案格式 |
| `query` ↔ `mcp_server` | `query.health_audit` → `mcp_server.action_publisher`；`mcp_server.graph_mcp` → `query.graph_context` | 健康稽核讀發布器 |
| `query` ↔ `engine_b` | `query.bottleneck` → `engine_b.hypotheses`；`engine_b.cli` → `query` | what-if overlay |
| `fetchers` ↔ `engine_b` | `fetchers.edgar_watch` → `engine_b`；`engine_b.cli` → `fetchers.gsheets` | |

**共同形狀：沒有一層 domain contract，所以每個消費端都直接 import 生產端的 concrete module。**
這正是 §7「GraphResearchProvider」要解的病——只是它不只發生在 Neo4j 這一處。

### 2.2 已經做對的隔離（不要拆掉）

- `decision_lab/workflow_ports.py`：定義 `WorkflowDataProvider` Protocol，讓 `decision_lab`
  不必 import Neo4j／Google Sheet／yfinance。**這是 repo 裡唯一一個真正的 port，
  `GraphResearchProvider` 應該照它的形狀做。**
- `decision_lab/adapters/graph.py::Neo4jReadOnlyQueryPort`：唯讀 credential ＋ 寫入語句
  正規表達式攔截，`tests/test_graph_read_only.py` 守著。
- `identity/registry.py`：`co:*` ↔ ticker 的唯一 SSOT，`loader.TICKER_MAP` 由它生成。
- `storage/relational.py`：SQLite/Postgres 抽象，Engine C 與 Decision Store 共用。

---

## 3. Authority 邊界（誰擁有什麼真相）

| Authority | 儲存 | 可變性 | 現況筆數（2026-09-03） | 唯一寫入路徑 |
|---|---|---|---|---|
| **Engine A 知識圖譜** | Neo4j（local） | 可重建（extraction 檔是 ground truth） | Entity 297（TechNode 134／Company 92／Product 52／Material 12／Person 4／Standard 3）／Claim 372／EdgeAssertion 662／SourceDoc 200／canonical domain edge 529（`CITES` 1,034、`ABOUT` 293 另計） | `loader/load_to_neo4j.py`、MCP `apply_research_action` |
| **Engine B leads** | `library/leads/pending_leads.json`（tracked） | 狀態機 | pending 1／triaged_go 5／action_prepared 3／parked 401／applied 73／triaged_no_go 485 | `engine_b.cli`、MCP `record_lead_decision` |
| **Engine B pq2 池** | `library/leads/todo_pool.json`（tracked） | append-only log ＋ 可變狀態 | 見 `python -m engine_b.todo list` | `engine_b.todo` |
| **Event Watch** | `library/leads/event_watches.json`（tracked） | 狀態機 | 見 `engine_b.event_watch counters` | `engine_b.event_watch` |
| **Engine C ETL projection** | private SQLite | **可重建** | financial_snapshots 1,858（73 ticker，2026-07-08 → 09-03）／technical 1,000／consensus 1,855 | `engine_c/etl_*.py` |
| **Engine C 人工觀測 ledger** | 同上 | **append-only，Git 救不回** | manual_observations 85（backlog 32／customer_concentration 29／runway_inputs 7／…） | `engine_c/manual_observations.py` |
| **Engine D Decision Store** | private SQLite，schema v9 | **append-only，Git 救不回** | cohort 41／system_decisions 268／context_bundles 268／coverage_assessments 268／work_orders 142／shadow 41／outcome 12（已量測 2）／live_choices 1／live_fills 1／paper_events 9／cohort_thesis 1 | `decision_lab/store.py` |
| **Live inventory** | Google Sheet（外部） | 使用者手動 | — | 使用者；`scripts/record_trade.py` 窄寫入 |
| **Policy 數值** | `config/*.json`（tracked） | 版本化 | 17 個 config 檔 | 人工 |

查證：
```
python -c "from decision_lab.bootstrap import open_default_store as o; s=o(); \
print({t: s.table_count(t) for t in sorted(s.table_names())}); s.close()"
python -m engine_b.cli counts
```

**四個人工 gate（重構後一個都不准動）：** graph admission、Engine C 觀測寫入、
thesis mutation、live choice/fill。

---

## 4. Point-in-time 語意稽核 🔴

這是全案最重要的發現。**「歷史時間 T 不得看到 T 之後的資料」目前只有 Engine D 做得到。**

### 4.1 各層現況

| 層 | 時間欄位 | 能不能回答「T 時刻我知道什麼」 | 實測 |
|---|---|---|---|
| **Engine D Decision Store** | `effective_at`／content-addressed `context_bundles` | ✅ **可以**。凍結的是「該次評估實際用到的值」，之後上游改動不回寫 | 268 個 bundle，digest 定址 |
| **Engine C 人工觀測** | `as_of`（事實生效日）＋ `recorded_at`（寫入日）＋ `supersedes_id` | ✅ **可以**，雙時間軸完整 | 85 筆 |
| **Engine C technical** | `session_date`（交易日）＋ `fetched_at` | ✅ **可以** | 1,000 筆 |
| **Engine C financial_snapshots** | `snapshot_date`（ETL 執行日，本機時區）＋ `bar_date`（真實交易日） | 🟡 **部分**。兩者已於 2026-08-14 拆開，但 `bar_date` 只有 **1,101/1,858（59%）**，舊列全空 | 見下方查證 |
| **Engine A 知識圖譜** | node/edge 只有 `updated_at`＝**loader 寫入時間**（＝我們讀到的時間，不是世界知道的時間） | 🔴 **不行** | 見 4.2 |
| **Engine B leads** | `published_at` 部分、`first_seen` | 🟡 部分 | |

查證：
```
python -c "from engine_c.db import get_conn; c=get_conn().cursor(); \
c.execute('SELECT COUNT(*), COUNT(bar_date) FROM financial_snapshots'); print(c.fetchone())"
```

### 4.2 Engine A 的 point-in-time 缺口（實測）

**canonical edge 完全沒有時間欄位。** 它的 `attributes`（`substitutability`／`sole_source`／
`qualification_status`）是 **對所有 EdgeAssertion 的投影**，不分日期——換句話說，
今天投影出來的 `sole_source=true` 可能來自 2026-08 的文件，但你無法從 edge 本身知道
它在 2026-06-30 是不是已經成立。

唯一的時間線索是 `Claim/EdgeAssertion -[:CITES]-> SourceDoc.published_at`，而覆蓋率是：

| 路徑 | 有 `published_at` 的比例 |
|---|---|
| EdgeAssertion → SourceDoc | **382 / 662（58%）** |
| Claim → SourceDoc | **300 / 372（81%）** |
| SourceDoc 本身 | 166 / 200（83%），範圍 2022-08-22 → 2026-08-31 |

查證：
```
MATCH (a:EdgeAssertion)-[:CITES]->(d:SourceDoc)
RETURN count(a) AS assertions, count(d.published_at) AS with_published
```

**全 repo 沒有任何 `valid_from`／`valid_to`／`filed_at` 欄位**（grep 命中 0）。
`effective_at` 有 107 處但全部在 Engine D，語意是「決策生效時間」而非「事實生效時間」。

**結論（可否證）：** 今天無法對 Engine A 做 anti-lookahead backtest。
要做，最小可行路徑是 §Phase 6 的前置：
①把 `published_at` 覆蓋率補到 ~100%（34 份 SourceDoc 缺日期）；
②讓圖查詢層支援 `as_of` 參數，投影時只吃 `published_at <= as_of` 的 assertion；
③canonical edge 的屬性投影變成「as-of 投影」而不是「當前投影」。
③ 是真正的工程量，而且**必須在 provider 層做，不是在 Cypher 裡到處加 WHERE**——這正是
`GraphResearchProvider` 存在的第一個硬理由。

### 4.3 已經做對的部分（不要動）

- `ContextBundle` 的 content-addressed digest ＋ 「舊 decision 永遠引用原 digest」契約。
- `snapshot_date` vs `bar_date` 的拆分（2026-08-14 交付，L12「一表兩義」的正確修法）。
- Shadow observation 的「inception price 絕不事後回填」規則。
- `manual_observations.as_of` 應填**資產負債表日**而非申報日的紀律。

---

## 5. Engine D 責任外溢（逐檔判定摘要）

完整逐檔表在 [`engine-d-decomposition.md`](engine-d-decomposition.md)，這裡只給總量：

| 歸屬 | 檔數 | 行數 | 佔 `decision_lab/` |
|---|---:|---:|---:|
| 真正屬於 Engine D | 13 | 6,871 | 51% |
| 拆分中的大檔（`brief.py` 1,462＋`cli.py` 613） | 2 | 2,075 | 15% |
| **Portfolio（該搬走）** | 4 | 1,516 | 11% |
| Shared infrastructure | 10 | 1,231 | 9% |
| **Alpha Research（該搬走）** | 4 | 1,086 | 8% |
| **Risk（該搬走）** | 1 | 538 | 4% |
| Engine C 正規化 | 1 | 185 | 1% |

**最刺眼的三筆：**
1. `sizing.py`（491 行）名為 sizing，實際上是**五軸證據品質評估**——純 research judgment，
   而且它是全系統唯一一個「LLM 產出研究判斷 → 結構化寫入 → 程式驗證引用」的管道。
   那正是 `AlphaModel` 該長的樣子，只是現在長在 Engine D 裡。
2. `beta_monitor.py`（898 行）＋ `beta_policy.py`（445 行）＋ `nav_exposure.py`＋
   `portfolio_risk.py`（539 行）＝ **2,300+ 行的 Portfolio/Risk 層**住在 Decision Lab。
3. `catalyst_watch.py`＋`alpha_event_monitor.py`＋`ranking_view.py`＝ alpha 的
   catalyst／event／ranking，全是 research 語意。

---

## 6. 重複概念盤點

### 6.1 五套「證據強度」字彙（最嚴重的重複）

| 字彙 | 值域 | 住哪 | 語意 |
|---|---|---|---|
| `evidence_tier` | 1–4（strongest→weak） | SourceDoc（Engine A） | **文件類型**可靠度 |
| `demand_proof_level` | confirmed/guided/inferred/speculative | Claim（Engine A） | **需求主張**的證實程度 |
| `confidence` | 0.0–1.0 | node/edge/claim/assertion | 「這個關係存在」的信心 |
| `EVIDENCE_RANK` | 5 級（externally_corroborated…self_reported） | `query/bottleneck.py` | **排序用**的證據等級（由 origin_entity 推導） |
| 五軸 `level` | unknown/bounded_hypothesis/corroborated | Decision Store assessment | **決策軸**的證據充分度 |

五者**不是同義詞**，各有正當理由，但沒有任何一份文件說明它們如何互相換算。
重構不應強行合併（那會壓掉真實區別，L12 的反向錯誤），而應在 `EvidenceRef` contract 上
**把它們並列成顯性欄位**，讓消費端自己選要哪一個。

### 6.2 兩套 lifecycle（已知縫隙，`catalyst_watch.py` docstring 已載明）

| | `thesis/lifecycle.json` | Decision Store `probe_lifecycle_epochs` |
|---|---|---|
| 筆數 | 3 條 thesis | 13 個 epoch／41 個 cohort |
| 狀態 | active/watch/review_required/retired/revised（L7） | promoted/rejected/expired/revised |
| 排程 | `next_check` ＋ catalyst checkpoints | `expiry` ＋ catalyst free text |
| 消費者 | `crons/thesis_freshness_check.py`、`query/health_audit.py`、pq2 `thesis_lifecycle` | `catalyst_watch.py`、brief、outcome |

兩套互不知道。**重構定位：`thesis/lifecycle.json` 是 research thesis 生命週期
（該歸 Alpha Research），`probe_lifecycle_epochs` 是 decision case 生命週期（歸 Engine D）。
它們本來就該是兩個東西——問題不在於有兩套，在於沒有人寫下這句話。**

### 6.3 三套 catalyst 表示

`thesis/lifecycle.json.catalyst_checkpoints`（結構化）＋`thesis/catalyst_calendar.json`
（結構化，刻意分開，理由已寫在檔案 `_why_not_lifecycle_json`）＋
`coverage_assessments.catalyst`（**自由文字**）。前兩者共用 `lifecycle_schedule.catalyst_checkpoints()`
解析，第三者無結構、`catalyst_watch.py` 明文「刻意不解析散文日期」。

→ 第三者是 §6.5「Catalyst 需要封閉字彙」的直接目標。

### 6.4 四套等待機制

Event Watch（統一 registry）／RA `expires_at`／thesis `next_check`／catalyst calendar。
**2026-09-02 已實測三套的「假死」實例全為 0，依 L14 決定留著不動。**
→ 這是 KEEP，不是待辦。重構不得以「統一」為由推翻已量測的結論。

### 6.5 `thesis/` 混了四種東西

| 內容 | 實際性質 | 應歸屬 |
|---|---|---|
| `*_lane_memo.md`／`scoring_rubric.md`／`generate_lane_memo.py` | research thesis 的敘事渲染 | Alpha Research |
| `lifecycle.json`／`lifecycle_schedule.py`／`pending_lifecycle.py` | research thesis 生命週期與變更提案 | Alpha Research |
| `preconditions.py` | L9 gate（能不能輸出投資建議標籤） | Engine D（approval semantics） |
| **`investment_policy.py`（337 行）** | **資本政策數值載入與部位上限計算** | **Engine D（capital authority）** |
| `evidence_manifest.py` | memo 的證據契約驗證 | Alpha Research |

`investment_policy.py` 住在 `thesis/` 是本 repo 最明顯的一處錯置——
`decision_lab.sizing`／`decision_lab.store`／`paper_portfolio` 都要 import 它，
造成 `decision_lab ↔ thesis` 環。

---

## 7. North Star pipeline 的現況覆蓋 🔴

把 prompt 的主幹逐段對到程式碼。**這張表是整份重構的地圖。**

| # | Stage | 現行實作 | 成熟度 | 缺口 |
|---|---|---|---|---|
| 1 | External Signal / Source | `crons/harvest_leads.py`、`fetchers/*`、`engine_b/leads.py`、`signal-triage` skill | 🟢 成熟 | — |
| 2 | Evidence | `skills/source-trace`、`extract.py`、`prompts/extract_system.md`、`loader/validate.py` | 🟢 成熟 | SourceDoc `published_at` 覆蓋 83% |
| 3 | Knowledge Graph | `loader/load_to_neo4j.py`、`loader/edge_resolution.py`、`schema/` | 🟢 成熟 | 無 as-of 投影（§4.2） |
| 4 | Structural / Causal Understanding | `query/bottleneck.py`（唯一排序權威）、`query/coverage_gaps.py` | 🟢 可用 | `substitutability` 覆蓋僅 **79/529（15%）**；多跳因果無 domain object |
| 5 | **Economic Value Capture** | **無** | 🔴 **不存在** | pricing power／contract structure／ASP 只散在 `manual_observations` 的自由文字（valuation_pressure 3 筆） |
| 6 | **Earnings / FCF Impact** | **無** | 🔴 **不存在** | **Engine C 沒有 segment revenue 欄位**；無敏感度模型 |
| 7 | Market Expectations | Engine C `pe_forward`／`analyst_target_*`／`consensus_coverage_observations` | 🟡 部分 | 見 §8 |
| 8 | **Expectation Gap** | `cohort_thesis.variant_perception`（**1 筆**，自由文字） | 🔴 **幾乎不存在** | 無 implied fundamentals、無 reverse DCF、無 peer set |
| 9 | Catalyst | `catalyst_watch.py`＋兩個 calendar；`coverage_assessments.catalyst` 為散文 | 🟡 部分 | 無封閉字彙的 catalyst type |
| 10 | **Alpha Signal** | **無此物件** | 🔴 **不存在** | 最接近的是五軸 assessment（研究完整度）與 rank row（結構排序），兩者都不是 signal |
| 11 | Portfolio / Risk | `portfolio_risk.py`、`nav_exposure.py`、`beta_monitor.py`、`config/target_allocation.json` | 🟡 部分 | **刻意不給尺寸**（既有契約，KEEP）；缺 target exposure 抽象 |
| 12 | Capital Decision | Engine D 全套 | 🟢 成熟 | — |
| 13 | Outcome Learning | `outcome_envelopes`（12 筆，已量測 2）＋等權重聚合（2026-09-02 交付） | 🟡 剛起步 | 樣本 n 小且高度相關（同一 sector 窗口） |

**四個 🔴 連在一起就是「Alpha Research Core」要蓋的東西**，而它們正好是 prompt §6 的
五個問題中的第 2、3、4 題。第 1 題（Structural Scarcity）已經有 `rank_bottlenecks()`，
第 5 題（Catalyst）有半套。

---

## 8. Expectation Gap 還缺哪些資料（逐項實測）

以 `engine_c/schema.sql` ＋ `etl_yfinance.fetch_snapshot()` 的實際欄位比對 prompt §6.4 需求。

### 已經有的
| 需求 | 現有欄位 | 覆蓋 |
|---|---|---|
| 股價 | `financial_snapshots.price` | 1,858/1,858 |
| forward 倍數 | `pe_forward` | 1,766/1,858 |
| trailing 倍數 | `pe_trailing` | 1,346/1,858 |
| EV/Sales | `ev_revenue` | 1,839/1,858 |
| 分析師目標價與家數 | `analyst_target_{mean,high,low,count}` | 1,793/1,858 |
| 覆蓋家數時序 | `consensus_coverage_observations` | 1,855 筆 |
| 毛利／營益率 | `gross_margin`／`operating_margin` | 1,858/1,858 |
| FCF / 現金 / 負債 / 股數 | `free_cash_flow_ttm`／`cash_and_equivalents`／`total_debt`／`shares_outstanding` | 1,611–1,858 |

### 缺的（依重要性排序）

| # | 缺什麼 | 為什麼是硬缺口 | 取得難度 |
|---|---|---|---|
| 1 | **Segment revenue share** | §6.3 Earnings Exposure 的核心輸入。「AVGO 的 CPO 只是一塊業務」這句判斷目前**沒有任何欄位承載**，只能靠 LLM 每次重讀年報 | 中（10-K Item 8 分部附註；已有 `fetchers/edgar.py`＋`fetchers/mops.py`） |
| 2 | **Forward EPS 估計值** | 只有 `forwardPE`（比率）。可由 `price / pe_forward` 反推，但那是 implied 不是 estimate；且無法區分「估計被下修」與「股價漲了」 | 低（`yfinance.info.forwardEps` 直接有） |
| 3 | **Revenue estimate（next FY/Q）** | reverse DCF 與 implied growth 的起點 | 中（yfinance `analyst_price_targets`／`earnings_estimate` 可用性需實測） |
| 4 | **Estimate revision 時序** | 「估計正在被上修」是最強的 catalyst 之一 | 🟡 **已有雛形**：`financial_snapshots` 是每日快照，`pe_forward` 已累積 2026-07-08 → 09-03（57 天、73 ticker）。加上 forwardEps 後即可算 revision |
| 5 | **Peer group registry** | peer-relative expectations 需要一組同業。`config/sector_anchors.json` 是**需求錨點分組**，不是同業集合 | 低（config 新增） |
| 6 | **Reverse DCF 假設欄位** | WACC／terminal growth／margin path 沒有存放處 | 低（新 table 或 cohort 欄位） |
| 7 | **ASP / volume / incremental margin** | §6.3 敏感度 | 高（多半只在法說散文，需 LLM 抽取 → Engine C 人工觀測） |
| 8 | **市值 / analyst_count 進排序視野** | 「標的純度」判準（`AGENTS.md` Alpha 契約第 4 維）明文說「不在排序內，必須另看」。`scripts/alpha_purity_snapshot.py` 已存在但只是 daily 的一個 pane | 已有，缺 contract |

**注意 #4 的資產性質：每日快照跑了 57 天這件事本身就是 revision 資料的雛形**——
這是既有 routine 的意外紅利，不要在重構時把 ETL 停掉。

---

## 9. 執行入口盤點（重構不得打斷的東西）

| 入口 | 觸發 | 做什麼 | 權限來源 |
|---|---|---|---|
| Daily（Codex 本機排程 06:30 台北） | 排程 | harvest → triage → pq1 drain → beta snapshot → todo sync → brief → publish | `.codex/rules/stockbot-automations.rules` **16 條 exact prefix** |
| Weekly（週日 04:00 台北） | 排程 | topic discovery ＋ 健康審查，報告留 `docs/reports/` | 同上 |
| `/daily-brief`、`/alpha-status`、`/research-drain`… | 使用者 | 12 個 skill（`skills/*/SKILL.md` 為權威，兩端轉接層由 `scripts/sync_agent_skills.py` 生成） | 互動 approval |
| MCP（`mcp.minatoyukina.uk`） | 手機／web | 12 個工具；唯一遠端 Git 例外是 `leads.json` | URL token ＋ 最小權限 Neo4j 帳號 |
| Writer lock | 兩側 | `library/leads/.writer_lock.json`，TTL 90 分 | — |

⚠ **任何新增／改名 CLI 或參數前綴都必須走「sandbox impact review 五步」**
（`AGENTS.md` Codex sandbox 契約）。重構期間這條是最容易被忽略的硬約束：
**改 module 名稱可能改變 `python -m xxx` 的命令字串，那會靜默打斷 daily。**

---

## 10. 這份盤點得到的五個結論

1. **不要重建 Neo4j。** 圖裡有 297 個 entity、662 條 assertion、200 份 SourceDoc，
   而 `substitutability` 只填了 79 條——資產是**證據與 provenance**，不是節點數。
2. **Engine D 的 point-in-time 機制是全案最好的一塊，要複製它而不是繞過它。**
   `ResearchContext` 應該用同一套 content-addressed freeze，只是 authority 分開。
3. **Alpha Research Core 不是「從 Engine D 搬出來」，是「把四個不存在的階段蓋起來，
   順便把已經寫好的搬過去」。** 搬的部分（`sizing`／`catalyst_watch`／`alpha_event_monitor`／
   `ranking_view`）共 1,086 行，蓋的部分（Q2–Q4）是全新的。
4. **Portfolio/Risk 是最乾淨的一刀**——2,054 行、對外介面窄、測試齊全
   （`test_portfolio_risk`／`test_nav_exposure`／`test_beta_monitor`／`test_beta_policy`）、
   與 Decision Store 的耦合只有 policy 載入。**應該第一個搬，當作 strangler 的練習。**
5. **Point-in-time 是 Phase 6 的前置，不是 Phase 1 的。** 但 `EvidenceRef` 從第一天就要
   帶 `published_at`／`as_of`，否則之後補不回來（欄位可以後補，歷史資料補不回來）。

---

## 附錄 A：查證命令總表

```bash
# Package 行數
git ls-files decision_lab | grep '\.py$' | xargs wc -l | tail -1

# 依賴圖（重跑需重建 scripts/_tmp_depgraph.py，Phase 0 用後已刪）
# 或：grep -rn "^from \|^import " --include=*.py decision_lab | grep -v "^.*:from \."

# Engine A 盤點
MATCH (n) RETURN labels(n) AS l, count(*) AS c ORDER BY c DESC
MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC
MATCH (a:EdgeAssertion)-[:CITES]->(d:SourceDoc)
  RETURN count(a) AS assertions, count(d.published_at) AS with_published

# Engine C
python -c "from engine_c.db import get_conn; c=get_conn().cursor(); \
c.execute('SELECT COUNT(*),COUNT(bar_date) FROM financial_snapshots'); print(c.fetchone())"

# Engine D
python -c "from decision_lab.bootstrap import open_default_store as o; s=o(); \
print(s.capital_expression_counters()); s.close()"

# 瓶頸排序現況
python -m query.bottleneck

# 覆蓋缺口
python -m query.coverage_gaps

# leads / pq2
python -m engine_b.cli counts && python -m engine_b.todo list
```
