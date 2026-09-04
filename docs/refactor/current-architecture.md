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

唯一的時間線索是 `Claim/EdgeAssertion -[:CITES]-> SourceDoc.published_at`，而覆蓋率是
（**下表是 2026-09-03 Phase 0 的盤點值，是歷史記錄；現況見表後的 Phase 6 更新**）：

| 路徑 | 有 `published_at` 的比例（2026-09-03 實測） |
|---|---|
| EdgeAssertion → SourceDoc | **382 / 662（58%）** |
| Claim → SourceDoc | **300 / 372（81%）** |
| SourceDoc 本身 | 166 / 200（83%），範圍 2022-08-22 → 2026-08-31 |

> **⚠ 2026-09-04 Phase 6 更新——本節的「結論」已不再成立。**
> 回填 21 份 SourceDoc 後：EdgeAssertion **645 / 662（97.4%）**、
> Claim **359 / 372（96.5%）**、SourceDoc **187 / 200（93.5%）**。
> 三個前置條件的現況：①**部分達成**（13 份留 null，多為無出版日的常設產品頁，
> L11-5 判定留 null 比猜日期誠實）；②③**已達成**——
> `query/bottleneck.py::project_assertions_as_of` ＋
> `Neo4jGraphResearchProvider._rank(as_of)`，且過濾發生在 `rank_bottlenecks` **之前**，
> 所以屬性投影本身就是 as-of 投影而不是「當前投影再砍列」。
> 查證：`python -m audit invariants --only PointInTime`（它會實跑一次投影驗沒漏水）。
> **本節其餘文字保留原樣**：它記錄的是動工前的狀態，不隨現況改寫。

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

## 11. `AGENTS.md` 規則分類 audit（771 行，30 個章節）

> **前提：`AGENTS.md` 不是憲法。** 它混了五種東西，其中只有一種是真正不可變的。
> **⚠ 本節只做分類與衝突分析，第一輪不重寫 `AGENTS.md`。**

### 11.1 分類判準

| 代碼 | 定義 | 判別問法 |
|---|---|---|
| **INVARIANT** | 不論未來 architecture 如何改變都成立 | 「換掉 Neo4j／換掉 Engine D，這句話還對嗎？」 |
| **CURRENT_ARCHITECTURE** | 只是目前實現 invariant 的方式，可重構 | 「它有沒有提到具體 module／欄位／引擎名稱？」 |
| **LESSON_LEARNED** | 踩坑所得。**必須保留學到的 invariant，不必保留當時的 implementation** | 「事發段落是不是在描述一次具體事件？」 |
| **PROCEDURE** | 具體操作流程 | 「它是不是在教人怎麼跑一個命令？」 |
| **OBSOLETE** | 已不符合新架構 | 「它描述的東西還存在嗎？」 |

### 11.2 逐節分類

| `AGENTS.md` 章節 | 行 | 分類 | 底下的 invariant 是什麼（若非 INVARIANT） |
|---|---|---|---|
| Claude Code / Codex 雙代理相容契約 | 5–17 | **PROCEDURE**＋2 條 INVARIANT | ①**同一 working tree 只有一個 writer**；②**session memory 不是 authority**——授權綁 action type ＋ underlying authority ＋ receipt，**不綁 provider**。其餘（skill 轉接層同步、平台設定分開）→ OPERATIONS |
| Codex sandbox／private authority 整合契約 | 18–24 | **PROCEDURE**＋1 條 INVARIANT | **unattended 的 executable surface 變更必須在同一個 change 完成 impact review**；不得用 broad permission 掩蓋整合缺口。其餘 → OPERATIONS |
| Codex custom-agent 委派契約（Luna） | 25–32 | **PROCEDURE** | → `skills/luna-reviewer/SKILL.md`（已是權威，此處是重複） |
| 工作語言（繁體中文） | 33–46 | **INVARIANT** | 使用者偏好，與架構無關 |
| 定位一句話 | 47–54 | **CURRENT_ARCHITECTURE** | invariant＝「研究輸入 ＋ 決策責任 → 可稽核的投資決策；**系統不給部位尺寸**」。「Engine A/B/C/D」是實現方式 |
| **系統架構（四引擎／四層）** | 55–105 | **CURRENT_ARCHITECTURE** 🔴 | ⚠ **使用者明示：四引擎架構本身不是憲法。** 真正的 invariant 是**五條 authority separation**（見 `target-architecture.md` §12）。此表的價值在「誰不負責什麼」那一欄，不在引擎命名 |
| ↳ Skill 層 | 64–71 | PROCEDURE ＋1 INVARIANT | **清單會腐壞，判準不會**（已有實測：新增 luna-reviewer 後表就漏一個） |
| ↳ 決策層 Engine D | 72–78 | 混合 | **INVARIANT**：point-in-time contract（凍結的是「該次決策實際使用的 slice」，不是 snapshot 全庫）＋ 資本邊界（不產生任何部位尺寸、三個硬擋、七天時效）。**CURRENT_ARCHITECTURE**：runtime 路徑與 U7 欄位歷史 |
| ↳ 記憶層 | 79–83 | **CURRENT_ARCHITECTURE**＋1 INVARIANT | Neo4j／SQLite 是選型；invariant＝**append-only manual ledger 是 private authority，刪除／重建前必須先 recovery backup** |
| ↳ 管道層 | 84–105 | **CURRENT_ARCHITECTURE** 🔴 | ⚠ ASCII 管線圖裡有 `prepare_research_action` → `apply_research_action`——**那是 MCP 的動詞，被寫進了架構圖**。見 §12 |
| 本檔的角色與另外兩份 | 106–124 | **PROCEDURE** | |
| ⚠ 現況數字會過期，判準不會 | 125–149 | **INVARIANT**（meta） | 陳述現況必須附查證命令；引用自家文件前先跑那條命令 |
| 統一待辦池（廣義 pq2） | 154–278 | 混合 🔴 | **INVARIANT**：**授權載體唯一＝pq2 編號**；`go` 的語意＝推進到下一個人工 gate；「等你決定」與「等事件」分離；建議只由 pool ground truth 導出。**PROCEDURE**（→ `skills/daily-brief`）：批次語法、決策行格式、內容密度、措辭層、四段分段軸——**這 124 行裡約 90 行是呈現規格** |
| Decision gap dispatch | 279–284 | **CURRENT_ARCHITECTURE** | invariant＝`go` 只推進到下一個 gate，authority mutation 仍需另外核准 |
| Sheet 持股覆蓋分類 | 285–290 | **CURRENT_ARCHITECTURE** | invariant＝**derived item 的 drop 必須改變推導條件**（＝F-17／INV-3） |
| Source-trace backlog 防漏 | 291–315 | **LESSON_LEARNED** → CURRENT_ARCHITECTURE | invariant＝**每個等待都必須有到期**；「可觸發」與「還會醒」是兩個問題（＝F-15／INV-2） |
| 資本與風控 | 316–331 | **INVARIANT** | 三個硬擋、共同現金池只有一條、兩個槓桿指標不得混用、capital authority 逐次人工。**這一節幾乎全是 invariant** |
| Alpha 呈現契約 | 332–433 | 混合 🔴 | **INVARIANT**：系統不給尺寸；outcome 等權重量測；交付要求（必須輸出有序清單與明確首選、不得以「未驗證」搪塞、必須點明相關性）。**CURRENT_ARCHITECTURE**：「哪些標的值得看」**四維度**——它是 `AlphaSignal` 五 score 的前身，**將被取代而非推翻**。**LESSON_LEARNED**：U7 移除清單與已知會失焦的指標 |
| Beta 呈現契約 | 434–457 | **CURRENT_ARCHITECTURE** | 整節將隨 `portfolio/` 搬家。invariant＝相對水位只呈現、不排序、不換算金額 |
| 技術訊號的地位 | 458–469 | **LESSON_LEARNED**（不得刪減）＋1 INVARIANT | 三次回測 0 勝 3 敗是拔除依據，**任何改寫都不得刪減**。invariant＝**量測／訊號／脈絡三分**，脈絡一旦被拿去排序或調尺寸就變回訊號 |
| 事件監控 | 470–473 | **CURRENT_ARCHITECTURE** | |
| Daily routine 權限與 retry 邊界 | 474–491 | **PROCEDURE** | → OPERATIONS（16 條 rule 的清單本身是 `.codex/rules` 的權威，此處是第二份抄本——**「清單會腐壞」的現行違規**） |
| 報告留檔策略 | 492–497 | **PROCEDURE**＋1 INVARIANT | invariant＝**不建立與待辦池競爭的第二個狀態源** |
| Daily Brief outbound 通知 | 498–515 | **PROCEDURE**＋1 INVARIANT | invariant＝**通知不是 authority**；canonical brief 只有一份 |
| 來源登記表 | 516–521 | **PROCEDURE**＋1 INVARIANT | invariant＝一手來源優先；出建議前的財務核驗五項 |
| v0 Schema 快速記憶 | 522–535 | 混合 | **INVARIANT**：`co:*` 不得由名稱猜（F-01）；**報價單位 ≠ 結算幣別**（F-02）；L4 三分。**CURRENT_ARCHITECTURE**：node/edge 具體欄位 |
| 報告產出：cohort 是終點 | 536–558 | **CURRENT_ARCHITECTURE** 🔴 | 「cohort 是研究終點」將被 **`AlphaSignal` 是研究終點**取代。**INVARIANT**：variant perception 的操作定義（市場隱含 X／thesis Y／催化劑 Z）、財務核驗五項、每份 thesis 必帶 `disproof_condition` |
| L1–L16 | 559–762 | **LESSON_LEARNED** | 見 §11.3 |
| 文件化學習 | 763–770 | **PROCEDURE**＋1 INVARIANT | invariant＝taxonomy（世界會長新品類→留鬆）vs contract（刻意有限→打開它是 bug） |

**量化：771 行中約 **310 行是 PROCEDURE**（應搬 OPERATIONS／skills）、
約 **200 行是 LESSON_LEARNED**、約 **150 行是 CURRENT_ARCHITECTURE**、
只有約 **110 行是真正的 INVARIANT**。**

### 11.3 L1–L16 的五欄重寫（lesson 不得刪除，但要把 implementation 與 invariant 分開）

> 格式：**Context → Failure → Learned invariant → Current implementation → Implementation may change?**

| L | Learned invariant（**不變**） | Current implementation | 可改？ |
|---|---|---|---|
| **L1** | 核心元件優化能力／生態成熟度／可觀測性，不優化「系統數量」；需人工 review 的資料結構，視覺化是硬需求 | Neo4j（已定案） | **NO**（選型已鎖，但理由是 invariant） |
| **L2** | 「現在搞錯、以後要搬全部資料才能修」的現在想清楚（表的形狀）；「以後加一列設定就能補」的直接動工 | `schema/vocab.json` 字彙留鬆 | YES |
| **L3** | 抽取層輸出 DB 無關 JSON，選型隨時可換 | `extract.py` → `loader/` | YES |
| **L4** | **物理／關係／時變三分。三連問：換掉另一端值會變嗎（→edge）／隨時間變嗎（→時變觀測）／講的是物理現實還是證據強度（→metadata）。瓶頸的 alpha 大半在邊上，不在點上** | node/edge attributes、Engine C 時變觀測 | **NO**——這是 schema 建模鐵律，新架構的 `ScarcityInputs`／`FundamentalsSnapshot` 分野直接繼承它 |
| **L5** | chokepoint-atlas 是**單一 lens**（偏小市值瓶頸獵手），當眾多視角之一，別讓世界觀被綁死 | 無相依套件 | YES |
| **L6** | **具體型號／公司名必須在 quote 裡逐字出現**（反幻覺）；schema gap 只有真實資料撞上去才會現形；局部 ID 跨文件 MERGE 會命名空間衝突 | `prompts/extract_system.md`、`loader` 加 doc_id 前綴 | YES（實作）／**NO**（逐字規則） |
| **L7** | **`disproof_condition` 是欄位不是流程。** 每條 disproof 必須附「核查頻率」與「觸發後 48 小時內做什麼」，否則是一個永遠不會響的火警警報 | `thesis/lifecycle.json`＋`catalyst_watch.py` | YES（實作）／**NO**（三件套要求 → `DisproofCondition` 型別強制） |
| **L8** | **供應商自報不算獨立佐證。** 多文件入圖前至少 3 個不同 `origin_entity`；`sole_source` 需客戶端或第三方；全同一 origin 則標 weak | `validate.py` WARN、`single_origin_report.py` | YES（實作）／**NO**（獨立性判準 → `EvidenceRef.corroborating_origins`） |
| **L9** | 跨引擎 join 必須有**靜態 lookup 的共同 ID**，不由 LLM 推斷；私有公司映射到**明確 null** 而非空缺 | `config/company_identity.json` | YES（實作）／**NO**（＝INV-1） |
| **L10** | **「這筆資料今天重新取一次拿得回來嗎？」拿得回來→可重建可覆寫；拿不回來→只能 append** | Engine A 可重建；Engine C ledger／Decision Store 只能 append | **NO**（＝INV-6 的一半，也是 ResearchContext/DecisionContext 分離的依據） |
| **L11** | 具體審計／法律術語的措辭精度本身就是一個 claim；對自己引用的事實套跟圖裡 claim 同一套 tier 紀律；**多個二手都這樣說 ≠ 一手已證實**；追源前先 grep 自家庫；**「我找不到」與「它不存在」是兩個 claim**；同一套紀律適用於自己的技術診斷 | ROADMAP「已撤回的診斷」 | **NO**（全部是 invariant） |
| **L12** | **一個表示承載兩種語意時，下游被迫二選一而兩邊都錯。** 修法永遠是先分開再各自定規則。兩個訊號：兩個修法方向都會壞／修法讓警報消失得太乾淨。**任何會改變輸出的輸入，都必須出現在該輸出自己的證據欄位裡** | 各處 | **NO** |
| **L13** | **驗收條件寫成「產出出現在下游消費者手上」。** 最危險的是成功與失敗在同一個訊號上同形 | — | **NO**（＝INV-4） |
| **L14** | **未經量測的機制不得享有默認信任，gate 也不例外。** 三個免 outcome 測試（恆亮／不會滅／講不出因果機制）。先量測後放閘。**維持營運 vs 改變行為要先分兩類** | daily brief 常駐計數器 | **NO**（＝INV-5） |
| **L15** | **語意交給語言處理，權限永遠 deterministic；先解析身分，再查權限。** gate 攔下的若是格式而非風險，該修的是它問問題的方式。放寬解析不等於放寬判準 | `sizing._resolve_reference` | YES（實作）／**NO**（分工原則） |
| **L16** | **分類已有 SSOT 時要讓它跟著資料走到需要它的地方。** 修法是把分類附到 payload 上，不是再寫一份文件叫人記得去查。**不要用會誤報的 linter 來防這件事** | `blockers_by_mode` 等 | **NO** |

**結論：16 條 lesson 中，13 條的 learned invariant 標記為「implementation may change: NO」
——它們不是實作細節，是新架構必須繼承的 domain contract。**
其中 L4／L10／L13／L14／L15／L16 已直接收斂進 `historical-failure-matrix.md` 的 INV-1～INV-6。

---

## 12. MCP / Remote access coupling 實測 🔴

> **使用者定位（2026-09-03）：MCP／remote access／cloud session 是 Legacy Peripheral，
> 不是核心架構。** 新核心必須能在完全沒有 MCP 的情況下運作。

### 12.1 實測：`mcp_server/` 有 79% 不是 MCP

`mcp_server/` 4,016 行的實際組成（AST 量測）：

| 內容 | 行 | 佔比 | 這是什麼 |
|---|---:|---:|---|
| `research_actions.py` | 1,128 | 28% | Research Action 的 **domain**：bounded mutation、content digest、immutable review packet、state machine、idempotent apply、publication receipt |
| `graph_mcp.py` 的 `_impl` 函式 | 660 | 16% | **application services**：`_prepare_extraction_impl`／`_apply_research_action_impl`／`_finalize_research_action_impl`／`_load_extraction_impl`／`_prepare_research_action_impl` |
| `intake.py` | 608 | 15% | **filesystem provenance 原語**：canonical extraction hash、atomic publish、no-clobber、storage permission。**與遠端無關** |
| `action_publisher.py` | 528 | 13% | **local-only Git 發布**。docstring 逐字寫著「intentionally **not** imported by the remote MCP tool surface」 |
| `graph_mcp.py` 其他 helper | 241 | 6% | 驗證與錯誤處理 |
| **小計：非 MCP 的 domain／application** | **3,165** | **79%** | |
| `@mcp.tool()` 包裝層 | 222 | 6% | **真正的 transport** |
| `leads_tools.py` | 147 | 4% | remote adapter |
| `engine_c_tools.py` | 112 | 3% | remote adapter |
| `decision_tools.py` | 88 | 2% | remote adapter |
| `leads_git.py` | 64 | 2% | 窄 Git 例外（見 12.4） |
| **小計：真正的 transport／adapter** | **633** | **16%** | |

查證：
```
python - <<'EOF'
import ast; t=ast.parse(open("mcp_server/graph_mcp.py",encoding="utf-8").read())
tool=sum(n.end_lineno-n.lineno+1 for n in t.body if isinstance(n,ast.FunctionDef)
         and any("mcp.tool" in ast.unparse(d) for d in n.decorator_list))
impl=sum(n.end_lineno-n.lineno+1 for n in t.body if isinstance(n,ast.FunctionDef)
         and n.name.endswith("_impl"))
print("tool wrapper", tool, "| _impl", impl)
EOF
```

### 12.2 Core → MCP 的反向依賴（**dependency direction 目前是錯的**）

| 消費端 | import 什麼 | 為什麼這是問題 |
|---|---|---|
| **`engine_b/todo.py`**（pq2 待辦池，2,597 行） | `mcp_server.research_actions`（3 處）、`mcp_server.decision_tools`（2 處） | **統一待辦池——本 repo 最核心的人工核准介面——依賴一個名為 MCP 的 package** |
| `query/health_audit.py` | `mcp_server.graph_mcp.GRAPH_SCHEMA_VERSION`、`mcp_server.action_publisher.publication_status` | 健康稽核依賴 transport package |
| `crons/weekly_scan_digest.py` | `mcp_server.intake`、`mcp_server.research_actions` | 本機 weekly 依賴 MCP package |
| `scripts/commit_pending_intake.py` | `mcp_server.action_publisher`、`mcp_server.research_actions` | 本機 Git 收尾依賴 MCP package |
| `scripts/prepare_research_action.py` | **`mcp_server.graph_mcp._prepare_research_action_impl`** | 本機路徑直接呼叫一個**私有底線函式**——這本身就是「domain 被關在 transport 裡」最直接的證據 |

**沒有任何 core module 需要 MCP 協定本身；它們需要的是被關在 `mcp_server/` 裡的 domain。**

### 12.3 實測：現行 routine 已經不用 MCP

| 檔案 | 逐字 |
|---|---|
| `crons/daily_brief_prompt.md:5` | 「不要使用 Claude cloud clone 或**遠端 MCP 降級路徑**」 |
| `crons/weekly_scan_prompt.md:4` | 「**不靠 MCP 才能讀本機 authority**」 |
| `skills/daily-brief/SKILL.md:25` | 「預設就是 Claude Code 本機；**cloud session＋MCP 是備援**」 |

`AGENTS.md` 也已寫下 **Local-first 方針（2026-07-26 使用者定案）**。
**因此「MCP 是 peripheral」不是這次的新決定，是把既成事實寫進架構。**

### 12.4 已經失效的理由（`leads_git.py`）

`leads_git.py` 的存在理由逐字是：「本機 MCP server 把 leads.json commit+push，
讓 **cloud routine** 每天讀 pushed clone 看到最新狀態」。
**而 cloud routine 已於 2026-07-26 移回本機。** 這條窄 Git 例外的原始理由已不成立；
它現在只服務手機 chat 入口。→ 分類見 `target-architecture.md` §14。

### 12.5 哪些「看起來像 domain rule」其實是 transport 問題

| 現行規則 | 真實性質 | 處置 |
|---|---|---|
| prepare／apply **兩次呼叫** ＋ 一次 native approval | **transport**（mobile UX：先讓使用者看 packet 再按一次確認） | 本機可以是一個函式兩個階段，不必是兩次 RPC |
| server 簽發 action **ID** | **transport**（跨 session 需要 handle） | 本機用 content digest 即可定址 |
| 單 action **5 MiB／10 文件／50 個非終態／100 MiB staging／30 天過期** | **transport／ops quota** | 不是 domain invariant，不得升格 |
| **遠端工具完全沒有 Git 能力**＋唯一窄例外 leads.json | **transport security** | 本機路徑本來就有 Git；這條不適用 core |
| `storage_permission`／`permission_basis` 兩欄必填 | **domain**（provenance） | ✅ 保留為 core |
| **content digest ＋ exact ID 核准** | **domain**（approval boundary 的完整性） | ✅ 保留為 core（digest 是 identity，不是 authentication） |
| **immutable review packet** | **domain** | ✅ 保留 |
| **idempotent apply ＋ 逐文件 checkpoint** | **domain**（filesystem-first、partial retry） | ✅ 保留 |
| `focus_company_id` 自我聲明 | **domain**（identity binding，INV-1） | ✅ 保留 |
| Research Action **state machine**（ready／partial／applied／expired） | **domain**（INV-2 lifecycle） | ✅ 保留 |

> ⚠ **這張表是本節最重要的產出。** 它防止的是：因為「MCP 可以忽略」就把
> bounded research mutation、provenance、digest identity、explicit approval、
> idempotent apply 一起丟掉——**那些是這個系統最貴的資產之一，只是住錯了 package。**

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
