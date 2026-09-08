# StockBotv2 — 系統架構

> **這份文件回答一個問題：系統長什麼樣、為什麼這樣切？**
>
> 它描述的是**目前的實現方式**，不是憲法。判別問法（`AGENTS.md` 的分野）：
> **「換掉 Neo4j、把 Engine D 拆成三個 package 之後，這句話還對嗎？」**
> 還對 → 它屬於 `AGENTS.md`（約束行為）；會跟著變 → 它屬於這裡。
>
> 五份文件的分工見 `AGENTS.md`「本檔的角色與另外四份」。
> 完整設計論證與逐檔搬遷判定見 [`refactor/target-architecture.md`](refactor/target-architecture.md)
> 與 [`refactor/current-architecture.md`](refactor/current-architecture.md)；本檔是它們的蒸餾版。

---

## 1. 五條 authority separation 今天由誰實現

**不可變的是權責分離（`AGENTS.md` §憲法），可變的是下面這一欄「今天由誰」。**
「四引擎架構」本身是 CURRENT_ARCHITECTURE，2026-09-03 使用者明示它不是憲法。

| Authority | 擁有什麼真相 | 唯一寫入者 | 可變性 | 今天由誰實現 |
|---|---|---|---|---|
| **A1 結構／證據** | 實體、關係、claim、provenance、逐字引文 | 經人工 admission gate 的 loader | 可重建（extraction 檔是 ground truth） | Engine A（Neo4j）＋`loader/` |
| **A2 財務觀測** | 帶時戳的財務／市場／共識觀測 | ETL（可重建）＋ append-only 人工 ledger | 混合 | Engine C（`engine_c/`） |
| **A3 研究判斷／Alpha** | 「我們相信什麼、憑什麼、什麼會推翻它」 | 研究流程（session 提議 → schema 驗證） | **可重算** | `alpha/`（Phase 1–6 建立） |
| **A4 Portfolio／Risk** | 目前曝險、目標配置、硬上限 | policy config ＋ Google Sheet（外部 authority） | 可重算 | `portfolio/`＋`risk/` |
| **A5 資本決策／問責** | 「當時憑什麼決定、使用者選了什麼、後來對不對」 | 明確的人工動作 | **append-only，Git 救不回** | Engine D（`decision_lab/`） |

### 四引擎的「不負責什麼」（這一欄比引擎命名有價值）

| 引擎 | 角色 | 不負責 |
|------|------|--------|
| **Engine A** | 供應鏈、物理／關係瓶頸、claim 與 provenance | Signal queue、部位、價格時序、交易決策 |
| **Engine B** | 外部 Signal discovery／intake 與研究注意力排序 | 提高 evidence tier、自動投資、graph admission bypass |
| **Engine C** | 財務、估值、市場與其他帶時戳 observation | thesis、持股真相、最終部位決策 |
| **Engine D** | Decision & Accountability：Shadow、Coverage、system decision、live choice／fill、lifecycle、outcome | 寫 Engine A、複製 Engine C current truth、取代 Google Sheet、broker routing、**任何部位尺寸** |

---

## 2. 分層與依賴方向

```
External Signal / Source
   │  Engine B — discovery / intake / source tracing
   ▼
Evidence ──────────────────────────────────┐
   │  loader + schema                      │ EvidenceRef 是唯一的跨層
   ▼                                       │ provenance 載體——任何一層都
Knowledge Graph（Engine A / Neo4j）         │ 不得「知道一件事卻說不出
   │  GraphResearchProvider（唯一出口）      │ 誰說的、什麼時候說的」
   ▼                                       │
Alpha Research Core（alpha/）◀─────────────┘◀── Engine C（財務／市場／共識）
   Q1 結構稀缺 → Q2 價值攫取 → Q3 盈餘曝險 → Q4 預期落差 → Q5 催化劑
   ↓ ResearchContext（as_of 凍結、content-addressed）
AlphaSignal — research view only，**不含部位**
   ▼
Portfolio（portfolio/）— view → target exposure ▸ Risk（risk/）— hard limits
   ▼
Engine D（decision_lab/）— 凍結 context、記錄 live choice、outcome attribution
```

**依賴方向只准 peripheral → core。** `alpha/` 的契約與模型層零外部相依
（`tests/test_layer_separation.py::FORBIDDEN_IN_ALPHA`），唯一允許碰外部世界的是
`alpha/providers/`。`audit/` 是 composition root：它看得到所有層，所有層看不到它。
`briefing/` 是 daily brief 與 **Alpha Investment Read Model**（§6.1）的組裝層，同樣看得到
所有層；Engine D 的 domain 模組不得 import 它（`FORBIDDEN_FOR_ENGINE_D`）。

**MCP／remote access 是 Legacy Peripheral，不是核心。** 新核心必須能在完全沒有 MCP
的情況下運作；`Core → mcp_server` 的 import 已於 Phase 3 歸零。

---

## 3. 記憶層（持久知識庫）

- **Neo4j 知識圖譜（Engine A）：** 供應鏈結構、技術關係、來源可追溯的主張。
  Property graph，不是 tree。選型理由見 `AGENTS.md` L1。
- **SQLite / Postgres（Engine C）：** 財務快照、Watchlist Gate。零安裝預設 SQLite；
  設 `POSTGRES_HOST`／`POSTGRES_DSN` 切 Postgres。SQLite authority 在 ignored
  `library/private/engine_c/`，由 `library/private/runtime_pointer.json` 指向。
  ETL projection 可由 tracked schema 重建；**同庫的 append-only manual observation
  ledger 是 private authority**（該不變式住 `AGENTS.md`）。
  見 [`solutions/tooling-decisions/engine-c-sqlite-dual-backend.md`](solutions/tooling-decisions/engine-c-sqlite-dual-backend.md)。
- **向量 RAG：** 暫用 Neo4j 內建，量大再分。

### Point-in-time：兩種凍結，不可混用

| | `ResearchContext`（A3） | `DecisionContext`（A5） |
|---|---|---|
| 凍結什麼 | 該次研究實際使用的 A1／A2 slice | 該次決策實際使用的全部 context ＋ policy version |
| 可否重算 | **可以**（研究可以重跑） | **不可以**（append-only，舊 decision 永遠引用原 digest） |
| 住哪 | `alpha/contracts.py` | Engine D 的 `context_bundles` |

⚠ 「凍結 Engine A」一律指**凍結該次實際使用的 slice**，不是 snapshot／dump 整張 Neo4j。

### as-of 圖投影（Phase 6）

canonical edge **沒有時間欄位**——唯一時間線索是 `CITES → SourceDoc.published_at`。
投影靠它做：`query/bottleneck.py::project_assertions_as_of` 依「引用的文件在 `as_of`
之前發表過沒有」篩 assertion，**再**交給 `rank_bottlenecks`。

⚠ **順序不可顛倒。** 先排序再砍列會留下用未來文件算出的 `substitutability` 與
`evidence`——列是對的、值是偷看來的，那是 lookahead 最難察覺的形式。
未定日一律排除**並計數**。圖上完全沒有日期、或 `as_of` 早於最早證據時，
`Neo4jGraphResearchProvider` 拋 `PointInTimeUnsupported` 而不是回空 list。

---

## 4. 管道層（Engine B discovery → 入庫）

```
文件 → library/raw/ → extract.py → loader/validate.py → loader/load_to_neo4j.py → Neo4j
fetchers/edgar.py ──────↑              engine_c/etl_yfinance.py → SQLite
線索 → source-trace → prepare_research_action（server-owned review packet）
     → 使用者明確核准 ID → apply_research_action（filesystem-first + resumable graph write）
     → 本機 session 執行 scripts/commit_pending_intake.py
```

- **抽取與 DB 解耦：** `extract.py` 只輸出 DB 無關 JSON；loader 可替換（L3）。
- **fetchers：** `fetchers/edgar.py`（美股 SEC EDGAR）、`fetchers/mops.py`（台股）。
- **daily harvest：** `crons/harvest_leads.py` 以 X API `since_id`＋EDGAR watch 抓
  metadata → triage PASS → routine 依 priority 自動 pq1 → prepared RA 才進 pq2。
- **每週審查：** `crons/weekly_scan_prompt.md`，只做 topic discovery ＋ lifecycle
  唯讀提醒 ＋ 健康審查；刻意與 daily 錯開。
- **本機音訊追源：** `scripts/transcribe_audio.py`（`faster-whisper`），模型與逐字稿
  只存 ignored `library/private/`。ASR 只提供 timestamp locator。
- **遠端存取：** 本機 MCP server ＋ Cloudflare Tunnel ＋ connector，十二工具 surface。
  完整資料流與安全邊界見 [`remote-access-architecture.md`](remote-access-architecture.md)。
- **各類來源的抽取 instruction：** [`extraction-instructions.md`](extraction-instructions.md)。

> ⚠ 這張圖裡的 `prepare_research_action`／`apply_research_action` 是 **MCP 的動詞**。
> 它們之所以出現在架構圖裡是歷史因素（Research Action 的 domain 曾被關在
> `mcp_server/` 裡），Phase 3 已把 domain 抽到 `intake/`。

---

## 5. Skill 層（Claude Code / Codex 共用操作介面）

權威內容在 `skills/<name>/SKILL.md`；`.agents/skills/`（Codex）與 `.claude/skills/`
（Claude Code）是**生成的薄轉接層**，不直接手改。

**這裡不重抄 skill 清單**——每個 `SKILL.md` 的 `description` frontmatter 就是權威，
兩端 harness 自動載入。曾經在此維護一張表，新增 `luna-reviewer` 後沒同步，表上長期
少一個（2026-08-19 發現）。**清單會腐壞，判準不會**。

---

## 6. Alpha Research Core（`alpha/`）

五個投資問題，取代舊的五軸 Confidence（不並存，轉換器 `alpha/legacy_axes.py`）：

| Score | 問句 | 主要輸入 |
|---|---|---|
| Q1 結構稀缺 | 這個位置有多難繞過？ | Engine A 的 `substitutability`／`sole_source`／qualification |
| Q2 價值攫取 | 卡住了，錢收得到嗎？ | 客戶端資本承諾、毛利、議價 |
| Q3 盈餘曝險 | 這塊業務對 EPS／FCF 多重要？ | `segment_revenue_share`（Engine C 人工 ledger） |
| Q4 預期落差 | 市場是不是已經 price in 了？ | forward EPS 修正 vs 股價變動（`engine_c/estimates.py`） |
| Q5 催化劑 | 什麼時候會被重新定價？ | catalyst watch、財報／認證里程碑 |

**`source_reliability` 不是第六個維度，是套在所有維度上的上限**
（`alpha/evidence_quality.py`）：「你憑什麼相信前面那些答案」不是投資問題。

**排序權威：** 結構排序的唯一權威是 `query/bottleneck.py::rank_bottlenecks()`；
alpha 排序必須**消費**它，不得重算結構分，也不得繞過它自建第二套結構評分。
它輸出兩份用途不同的排序：`rows`（可行動，證據優先）回答「現在能投什麼」，
`structural_rows`（純結構，不看證據）回答「該去補誰的證據」。

### 「哪些標的值得看」的四維度（`AlphaSignal` 五 score 的前身）

1. **瓶頸地位** — `substitutability` 4–5、`sole_source`、距需求端跳數。
2. **需求錨點** — 資金在不在那條鏈上；為空者不是候選。
3. **客戶端資本承諾** — 誰付錢給誰。客戶掏錢綁供應商＝真瓶頸；**供應商付錢或給股權
   換訂單＝不是瓶頸**（POET 以 2,292 萬份認股權證換 Lumilens 訂單）。這一項自帶方向
   性且最難偽造，任何以「替代難度」為主的排序都抓不到後者。
4. **標的純度** — 瓶頸業務占該公司多少。同為 `sub=5`，AVGO 的 CPO 只是一塊業務，
   AXTI／POET 才有資訊落差。市值與 `analyst_count` 在 Engine C，**不在排序內**。

### 排序驗證（Phase 6）

`alpha/backtest.py`＋`scripts/rank_forward_returns.py`：把 as-of 排序切前後段算等權
報酬。⚠ 它是**研究判斷的檢核，不是回測勝率**——期數個位數、標的高度集中在 AI 光互連，
前後段都不是獨立賭注；輸出強制列逐檔報酬與「這期主要由誰決定」。

---

### 6.1 Alpha Investment Read Model（`briefing/alpha_view/`，2026-09-05）

**角色一句話：StockBot 對一家公司目前投資理解的 canonical、machine-readable 表示。**
Alpha Card 只是它的一個 consumer。它是 **composition／read model，不是新的 authority**——
不重算 Q1–Q5、不重排、不算估值、不判定催化劑狀態，只做**選取、正規化、語意標註、組裝、
序列化**。

```
GraphResearchProvider ─┐
Engine C provider ─────┼─► alpha.context.build_research_context ─► ContextBuild ─┐
session 判斷檔 ────────┴─► alpha.models.compose_signal ──────────► AlphaSignal ──┤
Engine D 公開 cohort 事實（coverage／cohort_thesis／lifecycle）──────────────────┼─► build_alpha_investment_view
thesis/lifecycle.json＋catalyst_calendar.json、engine_c.checklist ──────────────┘          │
                                                                                          ▼
                                                                    AlphaInvestmentView（canonical DTO）
                                                                       │            │             │
                                                            Daily Brief 摘要   `python -m briefing   未來 Web／API
                                                            （compact_card）     alpha-card`（完整卡） （消費同一份 DTO）
```

**為什麼住 `briefing/` 而不是 `alpha/`：** 它必須同時看得到 Engine C、Engine D 與 thesis，
而 `alpha/contracts.py` 是零外部相依的 research contract。`AlphaSignal` 仍然只是研究判斷的
載體，**不是** UI DTO、不是跨層 composition blob、不含部位。四支檔案的分工：
`contracts.py`（型別＋字彙，純 stdlib）／`builder.py`（純函式組裝）／`render.py`
（Markdown，只依賴 contracts＋`shared.markdown`）／`sources.py`（唯一碰 I/O 的地方）。
`tests/test_alpha_view_render.py` 用 import 掃描守著這個分工。

**兩個正交的語意軸**（讓不同種類的知識在文字裡不再「看起來同樣可信」）：

| 軸 | 值 | 回答 |
|---|---|---|
| `status` | `available`／`partial`／`stale`／`missing`／`insufficient_evidence`／`not_modeled`／`not_applicable` | 這格有沒有東西、為什麼沒有。**`missing`＝有能力沒資料；`not_modeled`＝系統還沒有這個能力** |
| `basis` | `deterministic`／`observation`／`heuristic_proxy`／`session_judgment`／`narrative`／`structural_inference`／`none` | 這格是哪一種知識 |

`Datum` 在型別層強制 **Missing != Zero**：`status` 屬於「沒有值」那組時 `value` 必須是
`None`；`available` 時不得是 `None`。

**Authority map（每個 section 的真相來源與知識種類）：**

| Section | 來源 authority | basis／capability（今天） |
|---|---|---|
| structural_thesis | `rank_bottlenecks()`（經 provider）＋`alpha.context.structural_score` | Q1 `deterministic`；邊屬性 `observation` |
| causal_paths | `GraphResearchProvider` 的路徑／`propagate`／`get_structural_changes_since` | `structural_inference`，capability＝**`structural_causal_model`**（不是 financial） |
| fundamentals | Engine C `financial_snapshots`＋manual ledger（segment）＋`checklist` | `observation` |
| consensus | Engine C `financial_snapshots`＋`engine_c.estimates`＋**`consensus_estimates`**（FY-identified EPS／營收，`fiscal_items`） | `observation`，status **`partial`**（快照欄位＋0y／+1y 兩個會計年度；缺第三年起、目標價高低、逐位分布） |
| price_implied_expectations | `alpha.context._implied_valuation` | **`heuristic_proxy`**（trailing/forward PE − 1）；隱含利潤率與 reverse DCF `not_modeled` |
| internal_fundamentals | **`alpha/fundamental`**（§6.2）：假設 ledger → 確定性橋 | `deterministic`（capability `financial_causal_model`）；每格 `dependencies.input_dependency` 帶最弱輸入假設的知識種類。**沒有假設或沒有基期觀測＝`missing`**（有能力、沒資料），不再是 `not_modeled` |
| earnings_bridge | 同上 | 每格 observation／assumption／derived 各自標 basis；`assumptions`／`sensitivities`／`selection` 隨附 |
| expectation_gap | Q4（session）＋估計修正 vs 股價（`engine_c.estimates`）＋**`alpha/fundamental/compare`**（`numeric_comparisons`） | Q4 `session_judgment`（ordinal）**與**數值 gap `deterministic`（capability `numeric_internal_vs_consensus`）並存、分開標；數值 gap 只在同期、同口徑、同幣別時有值，否則 `not_applicable`／`missing` |
| catalysts | AlphaSignal.catalysts＋thesis checkpoints＋Engine D 散文＋`shared.catalyst_state` | `partial`，capability＝`structured_dates_without_repricing_link` |
| falsification | AlphaSignal.disproof_conditions（L7 三件套）＋Engine D 散文＋thesis lifecycle | capability＝`structured_conditions_with_expiry_watch`；自動失效引擎 `not_modeled` |
| scenarios | AlphaSignal bull／base／bear | **`narrative`**；機率 `not_modeled`；`target_valuation` 自 2026-09-06 起照抄 valuation 的單點 fair value（逐情境仍無） |
| valuation | **`alpha/valuation`**（§6.4）：內部 EPS × 明示目標倍數 | `deterministic`（capability `deterministic_fair_value_v1`）；fair value／`value_date`／現價／gap 分開，gap 附 `gap_is_not`；沒有估值假設或內部 EPS＝`missing`；估值假設未宣告時點語意時 `value_date`＝`missing` |
| implied_return | **`alpha/implied_return`**（§6.5）：現價 ＋ fair value 時點語意 ＋ 明示 horizon | `deterministic`（capability `base_case_implied_return_v1`）；`price_return`／`annualized_price_return` 確定性、`horizon` 與 `value_date` 是判斷、`total_return`／`probability_weighted_return` **`not_modeled`**；四個輸入缺一＝`missing`；每次列 `is_not` |
| entry_logic | **`alpha/entry`**（§6.6）：implied return ＋ **明示的要求報酬判準**（`investor_policy`） | `deterministic`（capability `analytical_entry_threshold_v1`）；`entry_price`／`price_to_entry_gap`／`hurdle_comparison` 確定性、`required_annualized_return` 是**投資人政策**（新 basis `investor_policy`）；沒有判準＝`missing`＋「缺投資門檻判斷，不是 ETL 缺口」；alignment 不對齊＝`review_required`；每次列 `is_not`（**不是 buy／sell、不是部位、不是資本許可**） |
| downside | — | **`not_modeled`**，並列出「不要跟什麼混淆」（賣方目標價、市場隱含成長、排序名次、**fair value gap**、**implied return**、**entry price**） |
| evidence | 全部 `EvidenceRef` 的索引＋as-of 篩選計數＋L8 品質摘要 | `observation` |

**as-of 視角的邊界（2026-09-05 Phase 1.1 定案）：** 三種來源三種處置，判準是「authority
答不答得出 T 時刻」。① Engine A（投影）與 Engine C（時序）：原生 as-of。② Decision Store：
append-only 且每張表帶時間戳，所以 `decision_lab.coverage_queries.company_decision_facts(as_of=…)`
做**真正的歷史過濾**（cohort `created_at`、decision `effective_at`、coverage `created_at`、
lifecycle 狀態由事件回放、variant perception 含 supersede 時點），回傳值帶 `point_in_time`；
builder **只接受標記與 `context.as_of` 相符的事實**，沒有標記或不符一律拒收成
`not_applicable`（呼叫端傳錯不會把當前值混進歷史卡）；到期狀態以 as_of 當今天判定。
③ `thesis/*.json` 與檢核點是當前狀態檔、沒有歷史 → 一律 `not_applicable` 並附 INV-6 原因。
Decision Store 只經 `mode=ro` sqlite 連線讀，查詢只回研究欄位、選 cohort 的規則寫在回傳值裡。

**判斷新鮮度：** session 判斷是對某一份 `ResearchContext` 做的。`compose_signal(...,
allow_stale_context=True)` 是唯讀 view 的明確 opt-in——舊判斷仍呈現但整段標 `stale`，
`identity.signal.context_matches=False`；`python -m alpha research --judgment` 維持嚴格。
判斷檔約定位置 `library/private/alpha/judgments/<TICKER>.json`（private，不進 Git）。

view 的 `capability_map()` 就是「知道什麼／還不知道什麼」的常駐計數器。

### 6.2 Causal Fundamental Model（`alpha/fundamental/`，2026-09-05 Phase 2 v1）

**角色一句話：根據我們知道的，我們對這門生意明確假設了什麼，那些假設推得出什麼數字，
跟同期共識差多少。** 它回答的是「StockBot 的內部預測」，**不是**估值、預期報酬或進場邏輯
（那三者仍 `not_modeled`）。

```
Engine A 證據 ─┐                                  Engine C（A2，唯讀）
               ├─► OperatingAssumption[]（A3，private append-only ledger）   fiscal_year_results（基期）
session 判斷 ──┘        │ select_assumptions(as_of)                          company_guidance（指引，證據）
                        ▼                                                    consensus_estimates（FY 別共識）
                 build_bridge（確定性算術）◄──────────────────────────────── 基期觀測
                        ▼
                 ModeledMetric[]（revenue／operating_margin／operating_income／net_income／eps）
                        ▼ verify_consensus_basis ＋ compare_metric
                 ExpectationComparison[]（只在同期、同口徑、同幣別時有數字）
                        ▼
                 briefing/alpha_view（只選取）→ internal_fundamentals／earnings_bridge／expectation_gap
```

**誰擁有什麼（authority 分工，不得混）：**

| 東西 | 擁有者 | 住哪 |
|---|---|---|
| 假設（值、basis、rationale、evidence、created_at） | A3 研究判斷，session 明示 | `library/private/alpha/assumptions/<TICKER>.jsonl`（append-only；`python -m alpha assumptions`） |
| 算術（revenue → margin → EPS） | A3，`alpha/fundamental/bridge.py` | 純函式，版本 `fundamental-bridge/v1` |
| 基期實際、指引、FY 別共識 | A2 Engine C | `manual_observations`（`fiscal_year_results`／`company_guidance`，mechanical）、`consensus_estimates`（ETL） |
| 口徑核實與比較 | A3，`alpha/fundamental/compare.py` | 純函式 |
| 組裝 | `briefing/alpha_view`（read model） | 不算任何數字 |

**認識論分界（本模型最重要的一條）：** 「FY27 D&C 營收成長 +60%」是 session 判斷；
「FY27 分部營收 ＝ 基期 × (1 + 成長)」是確定性算術。每個輸出都同時帶
`calculation="deterministic"` 與 `input_dependency`（最弱輸入假設的知識種類）；LLM 不得直接
吐 EPS，只能寫假設。缺任何一條假設就是 `missing`，不補 0 成長、0% 利潤率。

**會計期間與口徑是身分：** `FiscalPeriod.end` 才是身分，`FY2027` 只是結束年命名慣例；
provider 的 `0y`／`+1y` 在 ETL 抓取當下解析成絕對日期（`shared/fiscal.py`）。EPS 共識的
GAAP／non-GAAP 口徑不靠慣例，靠 `year_ago_actual` 與一手財報稀釋 EPS 機械核對（COHR：5.61 ＝
non-GAAP，≠ GAAP 4.12）；核不出來就 `unverified`，不得相減。

**PIT 三道門：** 假設 `created_at <= T`、觀測 `recorded_at <= T`、共識 `captured_at <= T`；
builder 另核對 model 的 `as_of` 與 context 相符，不符拒收。歷史時點沒有假設就是 `missing`，
不偷用現在的假設重建過去的 gap。

**刻意不做（下一階段）：** DCF／reverse DCF、目標價、預期報酬、下檔、進場價、opportunity
ranking、毛利率／營業費用拆分、FCF、季度期間。`rank_bottlenecks()` 仍是唯一排序權威。

### 6.3 Research Refresh／Dependency Invalidation（`alpha/refresh/`，2026-09-06 Step 0.5 v1）

**角色一句話：什麼變了？影響哪些研究成果？哪些只需重算？哪些需要重新研究？哪些已失效？**

它是 **dependency／orchestration authority**，不是 analyst authority——這條邊界必須寫死：

| 誰 | 產生什麼 | refresh 引擎對它做什麼 |
|---|---|---|
| Data authority（A1 Engine A、A2 Engine C） | 觀測、結構事實 | 只讀時序，導出 `ChangeEvent` |
| Research authority（A3：session 判斷、`OperatingAssumption`） | 判斷、假設 | **不產生、不修改**；只決定每個成果的 refresh state |
| Refresh／Invalidation（`alpha/refresh`） | `RefreshReport` | 不產生新事實、不產生新假設、不改 thesis、**不自動呼叫 LLM** |

```
Engine C 時序／圖投影差集／假設 ledger／Event Watch／lifecycle ─► briefing/alpha_view/changes.py ─► ChangeEvent[]
                                                                                                   │
既有 provenance（ComponentTrace.evidence_refs、OperatingAssumption.evidence_refs＋dependency_roles、  │
ModeledMetric.assumption_ids、ExpectationComparison.consensus_refs）─► artifacts.py ─► ArtifactDependency[]
                                                                                                   ▼
                                   alpha/refresh/resolver.py（policy.py 的表 × 引用命中 × 一層傳播）─► RefreshReport
                                                                                                   ▼
                                   briefing/alpha_view：refresh_status section＋各格 status；只組裝，不判 impact
```

**封閉字彙（contract）：** state ＝ `current`／`recalculate`／`review_required`／`invalidated`／`stale`／
`superseded`／`missing`；change class ＝ `market_price`／`consensus`／`financial_actual`／`company_guidance`／
`graph_edge`／`graph_claim`／`evidence`／`operating_assumption`／`fiscal_period_rollover`／`thesis_review_due`／
`disproof_signal`／`context_digest`（殘餘：digest 變了但沒有 class 能解釋——必須現形）。

**三條規則（改它們要先答出「現有幾個成果的 state 會變」，L14）：**

1. **`digest changed` 不是變化。** 每個 `ChangeEvent` 都指得出 class、authority、物件、`observed_at`（系統何時
   知道，決定 as-of 可見性）、`published_at`（世界何時知道，決定「判斷當時知不知道」）。同一身分、不同值才是
   變化——共識表「第一次出現」是資料覆蓋變了，不是世界變了（同 `documents` 不參與排序的理由）。
2. **recalculate ≠ review_required ≠ invalidated ≠ stale。** 確定性成果（Q1、橋、數值 gap、市場 proxy）的輸入
   變了 → `recalculate`；判斷型成果（Q2–Q5、thesis、假設）的依據 material change → `review_required`；
   supporting evidence 撤回／解析不到／review condition 宣告 → `invalidated`；L7 核查週期到期 → `stale`，
   不隱含任何新證據。舊 D&C 假設被新紀錄取代、或 FY2027 有了實際值 → `superseded`（歷史，不沿用）。
3. **不 cascade。** 影響只由 `policy.py` 的表（class → axis／basis／driver）與**引用命中**（變化的 ref ∈ 成果的
   supporting refs）決定；傳播只沿 `assumption_ids` 走一層（模型輸出 ← 假設）並標 `propagated_from`。
   **v1 materiality 立場：price-only 變化只讓市場導出量 recalculate，任何研究判斷維持 current**——沒有經量測的
   門檻能說「漲 6.6% 該重看、0.6% 不用」，假裝有比誠實說沒有更危險。共識有 1% 雜訊地板，那是抖動不是 materiality。

**假設 provenance（Step 0.5 擴充，舊 ledger 不改寫）：** `dependency_roles`（ref → `supporting`／`calibration`／
`comparison`）、`review_conditions`（machine-readable：metric／scope／period／operator／threshold／`on_trigger`）、
`provenance_semantics`（`legacy`＝2026-09-05 的 v1 紀錄；讀取端 fail safe：未分類 ref 當 supporting，同期共識 ref 依
前綴當 calibration）。**同期分析師共識不得是 supporting**（契約拒收）——那是 provenance 循環：共識支持假設 →
假設推出內部預測 → 再拿去比共識。Event Watch 的 `hypothesis_ref` 可指向 `oa_*` 假設 id；watch fired →
`disproof_signal` → 該假設 `review_required`，值不自動改。

**PIT：** `--as-of T` 只看 `observed_at <= T` 的變化、`established_at <= T` 的成果（其餘計數為 excluded）；
未來的 contradiction 不得回頭把歷史成果標 invalidated——當時它是 current。

**read model 的消費：** `SectionStatus` 多了 `review_required`／`invalidated`（有值但不得當 current）；`stale`
從此**只**表示時間／排程到期。`identity.signal.context_matches` 仍是「判斷對的是不是這份 context」的事實，
但它不再自動讓 Q2–Q5／thesis／情境整份 stale。沒跑變更偵測時（`refresh_changes=None`）退回舊語意並標
`change_detection=not_run`。`falsification.automatic_invalidation` 由 `not_modeled` 改為 `partial`（capability
`dependency_impact_v1`，明列不做：解析自然語言條件、改 thesis、呼叫 LLM）。

**入口：** `python -m briefing refresh <TICKER> [--scenario price_only|consensus_revision|graph_edge|new_guidance|
new_actual|fiscal_rollover|disproof] [--as-of]`；完整卡第 15 節；精簡卡 `refresh` 欄；`python -m alpha assumptions
--add` 的 spec 可帶 `calibration_refs`／`comparison_refs`／`review_conditions`。

**刻意不做（v1 限制）：** 語意 materiality（只有 class 級規則＋1% 雜訊地板）；自然語言 rationale／disproof 不解析；
`evidence`／`graph_claim` class 有契約但沒有 runtime 偵測來源（圖不記錄撤回）；ResearchContext 未持久化，所以
digest 殘餘差異只能整批標 `context_digest`；行情 as-of 仍以 `bar_date` 篩（判斷基線用 `fetched_at`）。

### 6.4 Valuation Model（`alpha/valuation/`，2026-09-06 Phase 2 Step 1 v1）

**角色一句話：根據我們自己的內部 EPS 與我們自己明示的目標倍數，這門生意值多少；跟現價差多少。**
它回答的是「StockBot 的 fair value」，**不是**預期報酬、horizon、進場價、買賣、機率加權情境（Step 2 以後）。

```
alpha/fundamental（內部 FY 目標期間 EPS，含 input_dependency）─┐
ValuationAssumption[]（A3，private append-only ledger）─ select(as_of) ─┼─► build_valuation ─► ValuationResult
Engine C 現價（A2，唯讀；`build.context.market`）──────────────────────┘        │
                                                                    fair_value ＝ internal_eps × target_pe（不含現價）
                                                                    gap ＝ fair_value vs current_price（同單位才算）
                                                                    ▼
                                                  briefing/alpha_view（只選取）→ valuation section／精簡卡 valuation 欄
```

**方法選擇（audit 2026-09-06，用資料證明）：** 內部可靠的 forward metric 只有 FY 目標期間的稀釋 EPS（橋 v1）；沒有內部
FCF、D&A、EBITDA、資本支出、營運資金，`financial_snapshots` 的 `total_debt`／`cash` 也沒有會計年度身分——所以 EV/EBITDA、
FCF／DCF、reverse DCF **沒有資料可餵，不為完整硬做**。v1 唯一 method＝`forward_earnings_multiple`（parameter `target_pe`），
method／parameter 是封閉字彙（`alpha/valuation/contracts.py::METHOD_PARAMETERS`），多一個 method 就要多一段算術。

**誰擁有什麼：**

| 東西 | 擁有者 | 住哪 |
|---|---|---|
| 估值假設（method／parameter／值／basis／rationale／證據角色／created_at／supersede／retract／review_conditions） | A3 研究判斷，session 明示 | `library/private/alpha/valuation/<TICKER>.jsonl`（append-only；`python -m alpha valuation`） |
| fair value 算術＋gap | A3，`alpha/valuation/model.py` | 純函式，版本 `valuation-model/v1`；公式字串唯一定義處 `FAIR_VALUE_FORMULA`／`GAP_FORMULA` |
| 內部 EPS | `alpha/fundamental`（§6.2） | 估值層**照抄** `ModeledMetric`，不重算 |
| 現價 | A2 Engine C | `build.context.market`（已依 as-of 過濾）；報價單位取自 registry |
| 組裝 | `briefing/alpha_view`（valuation section） | 不含任何估值公式（`tests/test_valuation_model.py` 以竄改＋import／token 掃描守著） |

**與 `OperatingAssumption` 同一套 epistemic system（刻意）：** 同一組 `basis` 字彙、同一組 ref 角色（supporting／calibration／
comparison；**同期共識與市場倍數只能是 calibration**）、同一種 append-only／as-of／supersede 語意，**連選取器都是同一支**
（`select_assumptions` duck-typed）。差別只有三處：id 前綴 `va_`、`driver` 換成 `method`＋`parameter`、`accounting_basis`
必填且只能 gaap／non_gaap。它**不是**橋的 driver——倍數不是財務橋的一段算術，所以住自己的型別與 ledger。

**四條規則：** ① **沒有 hidden default**：ledger 沒生效倍數→`missing`；內部 EPS 缺→`missing`；不補、不由 LLM 補。
② **同期、同口徑才乘**：估值假設的 period／accounting_basis 必須與內部 EPS 相同，不合是「口徑不合」不是「缺假設」。
③ **price 不進 fair value**：現價只進 gap；依賴層 fair value 的 refs 不含現價 ref，policy 表 `fair_value` 沒有
`market_price`，所以 price-only 變化只讓 gap `recalculate`。④ **gap 不是 expected return**：型別沒有 horizon／報酬欄位，
read model 每次都列 `gap_is_not` 四條。

**Refresh 整合（沿用 `alpha/refresh`，不另建 freshness）：** 新 change class `valuation_assumption`（policy 表對 Q1–Q5
一格都不動）；新 artifact type `valuation_assumption`（判斷型，規則同營運假設）／`fair_value`／`fair_value_gap`
（確定性）；傳播沿 `assumption_ids` 一層，上游可以是 `oa_*` 或 `va_*`。實跑 COHR：內部 EPS 假設被取代→fair value
`recalculate`；估值假設被取代→`recalculate`；估值假設的 supporting edge 變了→假設 `review_required`→fair value／gap
`review_required`（`propagated_from` 指名）；price-only→fair value `current`、gap `recalculate`。

**PIT：** 估值假設 `created_at <= T`；內部 EPS 沿用 fundamental 的三道門；fundamental 的 `as_of` 與估值視角不符一律拒用
（INV-6）。實跑 COHR `--as-of 2026-09-05`：EPS 8.94 在、估值假設（09-06）`created_after_as_of`→`missing`；
`--as-of 2026-08-15`：無基期觀測→`missing`，JSON 內無任何 `va_*` id。

**認識論（回答「fair value 裡多少是算術、多少是判斷」）：** 算術＝橋＋乘法＋基期實際值（Engine C mechanical 觀測）；
判斷＝內部 EPS 底下的 7 條營運假設（COHR：3 session_judgment＋4 heuristic_proxy）＋1 條估值假設（session_judgment）。
給定內部 EPS，**整個 gap 就是 `target_pe / implied_multiple_at_price − 1`**——即「我們的倍數 vs 市場對我們 EPS 付的倍數」；
EPS 的判斷藏在 implied multiple 與市場對共識 EPS 付的倍數之差裡。`ValuationResult.epistemics` 把這個分解機器可讀化。

**刻意不做（Step 2 以後）：** entry logic、buy／sell、portfolio、機率加權情境、逐情境目標估值、
多 method（EV/EBITDA／DCF 要先有內部現金流）、跨標的比較、consumer UI。**horizon 與報酬語意自 2026-09-06 起住 §6.5。**

### 6.5 Base-case Implied Return（`alpha/implied_return/`，2026-09-06 Phase 2 Step 2 v1）

**角色一句話：從哪一天（現價的 bar_date）到哪一天（明示的 horizon_end），在什麼假設下（內部 EPS 的營運假設＋目標倍數＋
value-date 語意＋realization horizon），現價走到 fair value 的 base-case 隱含價格報酬是多少。**
名稱刻意用 **implied** 不用 expected：「expected」在統計上是機率加權期望值，本層沒有任何機率。

```
alpha/valuation（fair value、value_date、input_dependency）─┐
HorizonAssumption[]（A3，private append-only ledger）─ select(as_of) ─┼─► build_implied_return ─► ImpliedReturnResult
Engine C 現價（A2，唯讀；含 bar_date）─────────────────────────────┘        price_return ＝ fair_value / current_price − 1
                                                                        days ＝ horizon_end − bar_date
                                                                        annualized ＝ (1 + r) ** (365.25 / days) − 1
                                                                        ▼
                                                     briefing/alpha_view（只選取）→ implied_return section／精簡卡 implied_return 欄
```

**先回答 Step 1 沒回答的問題：223.60 是哪一天的值？** v1 估值契約只有 `target_period`（EPS 屬於哪一年）與 `as_of`（知識視角），
**答不出**「今天的 fair value（A）」還是「未來某日的 target value（B）」——兩種讀法算術相同、報酬語意完全不同。修法是最小擴充：
`ValuationAssumption.value_date_convention`（封閉字彙 `spot`／`target_period_end`，**沒有預設**；舊紀錄讀成 `unspecified`，
content-addressed id 不變）→ `ValuationResult.value_date`／`value_date_semantics`（`VALUE_DATE_FORMULA` 唯一定義處）。
fair value 的算術一格不動；**時點未宣告時報酬層拒算**（不猜）。COHR 的 25x 宣告為 `target_period_end`：223.60 是 2027-06-30 的值。

**誰擁有什麼：**

| 東西 | 擁有者 | 住哪 |
|---|---|---|
| horizon 判斷（目標期間／`horizon_end`／basis／rationale／證據角色／created_at／supersede／retract／review_conditions） | A3 研究判斷，session 明示 | `library/private/alpha/horizon/<TICKER>.jsonl`（append-only；`python -m alpha horizon`） |
| value-date 語意 | A3，估值假設宣告 | `ValuationAssumption.value_date_convention`（§6.4 ledger） |
| 報酬算術＋年化 | A3，`alpha/implied_return/model.py` | 純函式，版本 `implied-return-model/v1`；公式字串唯一定義處 `PRICE_RETURN_FORMULA`／`ANNUALIZED_RETURN_FORMULA`／`HOLDING_PERIOD_FORMULA` |
| fair value | `alpha/valuation`（§6.4） | 報酬層**照抄**，不重算 |
| 現價 | A2 Engine C | 與估值層共用同一個 `CurrentPrice`（`bar_date` 是 horizon 起點） |
| 組裝 | `briefing/alpha_view`（implied_return section） | 不含任何報酬公式（`tests/test_implied_return.py` 以竄改＋import／token 掃描守著） |

**與營運／估值假設同一套 epistemic system（刻意）：** `HorizonAssumption` 用同一組 `basis` 字彙、同一組 ref 角色、同一種
append-only／as-of／supersede 語意、**同一支選取器**；id 前綴 `ha_`；`period` 是它服務的估值目標期間（估值換期間，horizon 就是
`other_period`，不沿用）；`horizon_end` 是明示日期，不是「12 個月」這種相對量；寫下時已過去的 horizon 契約拒收（INV-2）。

**五條規則：** ① **四個輸入缺一就 `missing`**：現價（含 bar_date）、fair value（同單位）、value-date 語意、生效 horizon；沒有 hidden
default。② **horizon 已過就不是報酬**（`horizon_end <= bar_date` → missing＋「需要新的 horizon 判斷」）。③ **只有 price return**：
`total_return_status` 恆 `not_modeled`（無股利／分配預測能力），不得冒充。④ **沒有機率**：型別裡沒有 probability-weighted 欄位。
⑤ **算術確定、輸入是判斷**：`calculation=deterministic`；`input_dependency`＝fair value 的輸入依賴與 horizon basis 中最弱者。
另有 `alignment`（`aligned`／`horizon_after_value_date`／`horizon_before_value_date`／`spot_value_realized_over_horizon`）只現形不阻擋。

**Refresh 整合（沿用 `alpha/refresh`）：** 新 change class `horizon_assumption`（Q1–Q5 與假設層一格不動）；新 artifact
`horizon_assumption`（判斷型，帶 `expires_at=horizon_end`——`ArtifactDependency.expires_at` 是本步新增的絕對到期欄位，到期即
`stale`）／`implied_return`（確定性；policy `{market_price, financial_actual}`；依賴＝fair value 的依賴＋現價 ref＋horizon）。
傳播上游泛化到 `ASSUMPTION_ARTIFACT_TYPES`（`oa_*`／`va_*`／`ha_*`）。實跑 COHR：price-only→只有 implied_return `recalculate`；
估值假設 review→implied_return `review_required`（`propagated_from` 指名）；horizon 被取代→`recalculate`；到期→horizon `stale`
→報酬 `stale`；無關的圖變化→`current`。

**PIT：** horizon `created_at <= T`；估值的 `as_of` 與報酬視角不符一律拒用（INV-6）；horizon 起點是現價的 `bar_date`（≤ T）。
實跑 COHR `--as-of 2026-09-05`：估值假設 v2 與 horizon 皆 `created_after_as_of` → `missing`，JSON 無 `ha_*`。

**認識論：** 算術＝報酬／年化／持有期間／估值／橋；判斷＝營運假設＋估值假設（含 value-date 語意）＋horizon；觀測＝現價＋基期實際值。
`ImpliedReturnResult.epistemics.one_sentence` 把「從哪天、到哪天、在什麼假設下」機器組成一句話。

**刻意不做（v1 限制）：** buy-sell／portfolio／consumer UI／機率加權情境／Valuation v2（historical normalized
multiple、peer multiple、growth durability、margin／ROIC quality、cycle position——backlog 不遺失）／total return／跨標的比較。
**Entry Logic 自 2026-09-06 起住 §6.6。**

### 6.6 Entry Logic（`alpha/entry/`，2026-09-06 Phase 2 Step 3 v1）

**角色一句話：已知現價、fair value（含時點語意）、明示 horizon 與**明示的要求報酬判準**，回答
「什麼價格以下才滿足這個報酬門檻」，以及現價相對那個門檻價在哪裡。**
它**不是** buy／sell、不是部位尺寸、不是資本許可——名稱刻意叫 **analytical entry threshold**。

```
alpha/implied_return（現價、fair value、value_date、horizon、年化隱含報酬）─┐
EntryCriterion[]（投資人政策 ledger）── select(as_of) ────────────────────┼─► build_entry_assessment ─► EntryAssessmentResult
                                                                            │   entry_price ＝ fair_value / (1 + h) ** (days / 365.25)
                                                                            │   gap ＝ current_price / entry_price − 1
                                                                            ▼   comparison ＝ current_price <= entry_price ? meets : above
                                              briefing/alpha_view（只選取）→ entry_logic section（第 13c 節）／精簡卡 entry_logic 欄
```

**先回答「hurdle 是誰的？」（動工前的 authority 盤點，2026-09-06）：** required return **不是公司事實**
（A1／A2 不擁有它）、**不是研究對公司的信念**（A3 的內容是「我們相信這家公司會怎樣」，不含「我要求幾 %」）、
**也不是資本決策**（A5 是「當時憑什麼決定、使用者選了什麼」，append-only 且 live 100% 人工——宣告一個 hurdle
不授權任何資本、不建立任何決策紀錄）。它回答的是「**我的資本**要求多少報酬才值得」，主詞是投資人。
結論：新增第三種知識種類 **`investor_policy`**，在本層與 A2 現價同一種地位——**注入的輸入**，只讀、不猜、
不補預設、不自動改。**沒有把 capital permission 偷塞進 Alpha。**

| 東西 | 擁有者 | 住哪 |
|---|---|---|
| 要求報酬判準（`convention`／值／`basis`／rationale／`reference_refs`／`created_at`／supersede／retract） | **投資人政策**（使用者明示） | `library/private/alpha/entry_criteria/<TICKER>.jsonl`（append-only；`python -m alpha entry-criterion`） |
| 門檻價／gap／comparison 算術 | A3 確定性導出，`alpha/entry/model.py` | 純函式，版本 `entry-model/v1`；公式字串唯一定義處 `ENTRY_PRICE_FORMULA`／`PRICE_TO_ENTRY_GAP_FORMULA`／`HURDLE_COMPARISON_RULE` |
| fair value／horizon／年化隱含報酬 | `alpha/implied_return`（§6.5） | 本層**照抄**，不重算 |
| 「該不該買、買多少」 | **使用者**（成為資本動作時才是 A5） | 本層型別裡**沒有那個欄位** |

**六條規則：** ① **兩個輸入缺一就 `missing`**：可用的 implied return、生效的判準；兩者的理由**分開寫**——
判準缺席是「**缺投資門檻判斷**，不是資料 ETL 缺口」，**不 invent 10%／15%／20%**。② **判準是注入的輸入**：
`basis` 封閉字彙只有 `investor_policy`（開放它就等於讓 hurdle 變成「對公司的判斷」）；`criterion_basis` 與
研究側的 `input_dependency` **分兩格**，不混。③ **判準刻意沒有 `period`**——要求報酬不隨估值換會計年度而失效；
也**刻意不共用 `select_assumptions`**（那支以會計期間為身分並要求證據解析到公司 evidence index，而投資人的
機會成本本來就不在那裡；硬套會製造「換了年度 hurdle 就 other_period」的假失效）。④ **alignment 不對齊不得
冒充 clean**：`aligned`／`spot`（明示）→ `clean`；`horizon_before/after_value_date` → 算術照列但
`assessment=review_required`＋理由，型別層擋住「不對齊卻標 clean」。⑤ **只有算術比較，沒有 action**：
`meets_analytical_hurdle` 就是 `current_price <= entry_price`（等號歸 meets——門檻價的定義就是「恰好滿足」）。
⑥ **型別層在 import 當下擋住資本語意**：`_assert_no_capital_fields` 掃描 `FORBIDDEN_POSITION_TOKENS` ＋
buy／sell／order／action／trade／permission，長出那種欄位是 import 失敗不是 lint 警告。

**Refresh 整合（沿用 `alpha/refresh`）：** 新 change class `entry_criterion`（Q1–Q5、假設層、fair value、
implied return **一格不動**——投資人政策變了不代表對公司的看法變了）；新 artifact `entry_criterion`（判斷型，
**`refs` 為空**：判準沒有 supporting evidence，所以結構事件／共識／指引都不會動它）／`entry_assessment`
（確定性；policy `{market_price, financial_actual}`；依賴＝implied return 的依賴＋criterion）。
實跑 COHR：price-only→`entry_assessment` `recalculate`、判準 `current`；graph_edge／consensus／new_actual／
disproof→上游 review 傳播成 `review_required`，**判準始終 `current`**；horizon 到期→整條 `stale`。
⚠ **criterion 同時列在 `refs` 與 `assumption_ids`，但今天只有 refs 那條會發動**（突變實測）：判準不可能變成
`review_required`／`invalidated`，第二輪傳播對它是 no-op——`assumption_ids` 留著是為了依賴宣告完整，
**不是一道已量測的守衛**（L14 同樣適用於自己寫的守衛）。

**PIT：** 判準 `created_at <= T`；上游 implied return 的 `as_of` 與本層視角不符一律拒用（INV-6）。
實跑 COHR `--as-of 2026-09-05`／`2026-08-15`：上游缺 → `missing`；`--as-of 2026-09-06` → available。

**Sandbox 驗算：** `python -m briefing entry <T> --sandbox-hurdle 0.15` 只在**記憶體**疊一筆 `author=sandbox`
的判準（`persisted=false`、warning 標明），**不寫任何 authority、不進變更偵測**；ledger 的 append 入口
明文拒收 `author=sandbox`——**demo 好看不是寫入 authority 的理由**。

**刻意不做（v1 限制）：** buy／sell／hold、position size／capital allocation／order、portfolio permission、
多 convention（total return hurdle、IRR、風險調整後門檻都要先有各自的算術與資料）、跨標的比較、
判準的到期語意（今天沒有 `expires_at`）；Analyst Consumer 已於 Step 3.5 交付（§6.7），APP／API 仍未做。

---

### 6.7 Analyst Consumer（`briefing/analyst_view/`，2026-09-07 Phase 2 Step 3.5 v1）

**角色一句話：把 canonical read model 依「使用者打開一檔股票時會依序問的六個問題」重新投影，
讓人在很短時間內看懂 StockBot 相信什麼、跟市場差在哪、怎麼算到這裡、最弱假設是什麼、什麼會讓結論需要重看。**

**先記下產品決策（它決定這一層長什麼樣）：** stock-level **主流程**是
`Evidence → Internal Forecast → Valuation／Future Target Value → Horizon → Implied Return`，
**終點是 implied return**；`EntryCriterion`／hurdle 是 **optional analytical capability**，
**不是必填資料，也不是 research completeness gate**。沒有 hurdle 時系統只說
「optional entry threshold unavailable」，**不得把這檔標成研究不完整**，也**不得**為了讓自己有答案
而要求使用者宣告一個固定的 10%／15%／20%。機會成本、風險調整後 hurdle 與跨標的比較留給未來的
Portfolio／Investor Policy 階段。

```
AlphaInvestmentView（§6.1 canonical read model；18 個 section，依資料結構排列）
        │  build_analyst_view（純函式；只組裝／排序／label）
        ▼
AnalystView ── headline   （Q4 現價 → future target value → 隱含報酬｜refresh／review state）
            ├─ fundamental（Q1 內部 revenue／EPS｜Q2 同期共識｜Q3 數值 gap｜口徑與會計期間）
            ├─ why        （Q5 生效假設＋basis｜脆弱輸入｜既有敏感度｜算式｜證據）
            ├─ research   （Q6 Q1–Q5／thesis／催化劑／disproof／missing・stale・review_required）
            └─ entry      （**optional**：有判準就顯示 analytical entry threshold；沒有就 Not set (optional)）
                │
        readiness（只看核心四段）＋refresh 摘要＋limits（「不是什麼」）
                │
     `python -m briefing analyst-view <T> [--as-of] [--format markdown|json] [-o]`
```

**它為什麼不可能變成第二個研究層（型別層強制，不是自律）：** panel 裡每一行的 `datum` 都是
`AlphaInvestmentView` 裡**同一個 `Datum` 物件的參照**（`is` 相等）；`AnalystLine` 刻意**沒有 `value` 欄位**，
所以「值」只有一個住處。`tests/test_analyst_view.py` 用 `id()` 集合逐行比對——compose 只要自己 `Datum(...)`
生一格（哪怕值一模一樣）就會紅。三支檔案另有 import allowlist、float 字面值掃描（**全模組 0 個**）與
「不得 import 任何 `alpha.*` 模型模組」的檢查。

**唯一被允許的數值動作是排序**：既有敏感度依 `abs(fair_value_relative)` 由大到小。它不產生新值，
也**不是新的 attribution model**——`context.sensitivity_order` 把這句話寫在資料裡。

**「最脆弱的輸入」是宣告好的列入規則，不是新判斷。** `WEAK_INPUT_RULES` 是封閉字彙，每一條 `WeakInput`
必須說出自己被哪一條規則列進來：`largest_modeled_sensitivity`（既有敏感度中 |Δ| 最大）／`refresh_flagged`／
`heuristic_proxy_input`／`session_judgment_input`／`weakest_known_axis`（抄 `AlphaSignal.weakest_axis`）／
`unknown_axis`（該軸 missing——**未知不是「沒問題」**）。

**status roll-up 與 readiness 都是查表。** panel `status` ＝來源 section `meta.status` 取最嚴
（`_WORST_FIRST` 是宣告好的嚴重度序，且 `source_statuses` 保留取最嚴之前的原值）；
`readiness` ∈ `ready`／`ready_with_flags`／`blocked`，**只看核心四段**，判準逐字寫在 `readiness.rule`。
**optional panel 不參與**——`tests/test_analyst_view.py` 逐欄比對「有判準 vs 沒判準」兩份投影的 readiness。

**頭條那一句話不是 consumer 造的。** `implied_return.epistemics.one_sentence` 由
`alpha://implied_return/model` 自己組出，consumer 只是把它挪到最前面並註明出處——造句就是在 read model
之外生出第二種說法。

**PIT／materialize：** `--as-of` 直接透傳到 `fetch_alpha_investment_view`；投影本身是純函式，
`AnalystView.to_dict()` 完全 JSON-able 且保留 `null`，可預先產生給未來 APP 點擊直接讀
（不需要 runtime LLM，也不需要重跑任何 authority）。

**刻意不做：** buy／sell／sizing／portfolio、跨標的比較與排序、任何新的 forecast／valuation／return 公式、
為 consumer 新建 attribution model、runtime LLM、APP／API（Step 5）。

---

### 6.8 缺席語意（`alpha/absence.py`＋`alpha/abstention/`，2026-09-07 Phase 2 Step 5）

**角色一句話：`status` 回答「這一格能不能用」，`absence_kind` 回答「它為什麼沒有」——兩者正交。**

事發（2026-09-07 Coverage Pilot §4.3）：6324.T 的估值 blocker 逐字是「尚未寫入任何估值假設」，
而真實狀態是研究結論「126x 錨不住任何可辯護的倍數，所以不寫」。**兩種語意共用一句話**（L12），
而 APP 會把那句話直接放到使用者眼前——他無從分辨「還沒做」與「這已經是答案」。

```
alpha/absence.py         封閉字彙 ABSENCE_KINDS（11 種）＋ DEFAULT_ABSENCE_KIND（status → kind 的查表）
        │                零相依（只有 __future__／typing），所以呈現層 import 它不違反分層
        ├─ ValuationResult.absence_kind      ← build_valuation 走到哪個分支**自己宣告**
        ├─ ImpliedReturnResult.absence_kind  ← 上游缺席時**繼承**估值層的 kind，不降級成「還沒寫」
        ├─ Datum.absence_kind / SectionMeta.absence_kind（read model）
        └─ AnalystPanel.absence_kind / AnalystBlocker（consumer；blockers 的欄位化版本）
```

**十一種 kind**：`not_yet_recorded`（還沒做）／`deliberate_abstention`（刻意不主張）／
`method_not_applicable`（方法對這筆資料無定義）／`upstream_unavailable`（上游缺，要補的是上游）／
`inputs_incompatible`（每格都有值但身分不相容）／`provider_missing`／`capability_absent`（not_modeled）／
`point_in_time_unavailable`／`insufficient_evidence`／`invalidated`／`not_applicable_unspecified`。

⚠ **`not_applicable` 的預設刻意是 `not_applicable_unspecified`。** 它今天同時被 PIT（沒有時點投影）
與方法層（本益比法遇到虧損）使用；猜任何一邊都是替 authority 造一個它沒說過的區別。知道自己是哪一種的
呼叫端要**明示**——那正是這張表存在的目的。

**`SETTLED_ABSENCE_KINDS`（刻意不主張／方法不適用／本層沒有這個能力）表示「這已經是答案，不要去補」。**
⚠ 它**不**讓 readiness 變好——blocked 還是 blocked，只是使用者知道該不該花力氣。

**`Abstention`（`alpha/abstention/`）是「刻意不主張」的 append-only authority。**
`library/private/alpha/abstentions/<TICKER>.jsonl`；content-addressed `ab_*` id、
`supersedes_id`／`retracted` 語意與假設 ledger 完全一致、as-of 選取共用同一套規則。
三條型別層強制：①**結構上不可能攜帶數字**（`_assert_no_value_fields` 在 import 當下掃描欄位名，
長出 `value`／`target_pe`／`multiple` 之類的欄位是 import 失敗）；②`reason` 與 `revisit_when` 都必填
（沒有「什麼證據出現才會改寫」的 abstention 是永遠不會響的火警警報，L7）；③`layer`／`subject` 是封閉字彙
（v1 只有 `valuation.forward_earnings_multiple.target_pe`），否則它會變成「任何一格都可以宣布自己是刻意留白」
的萬用擋箭牌。入口 `python -m alpha abstention <T> --list／--add spec.json／--retract <id>`。

**它不是第二份 ValuationAssumption authority。** 後者擁有「目標倍數是幾」，前者只擁有「我們不主張」；
宣告之後 `fair_value` 仍然是 `None`、readiness 仍然 `blocked`，改變的只有那句「為什麼」。

**accounting basis 的呈現別名（`ACCOUNTING_BASIS_DISPLAY`）** 解的是同一天記下的另一筆語意債：
`ACCOUNTING_BASES = ("gaap", "non_gaap", "not_applicable", "unverified")` 是 **contract identity**——
它是三本 private append-only ledger 每一筆紀錄身分的一部分，改字彙等於改既有紀錄的身分（L10）。
所以**不改字彙，加一層呈現別名**：`gaap` → 「As reported（法定財報口徑）」，
且 label **一律不含準則名稱**（Lynas 是 AASB／IFRS、HDS 是日本基準、IQE 是 IFRS，三者在 ledger 裡都寫 `gaap`；
authority 裡沒有「是哪一套準則」那一格，寫上去就是替它主張它沒說過的事）。`raw` 永遠一併輸出供稽核。

---

### 6.9 Web App／API（`webapp/`，2026-09-07 Phase 2 Step 5 MVP）

**產品 invariant：`LLM changes cognition; APP reads cognition.`**

```
authority（Neo4j／Engine C／private ledger）
     │  python -m webapp materialize   ← **唯一**會跑模型、連 DB、讀 ledger 的地方（約 4.2 秒／檔）
     ▼
AlphaInvestmentView → AnalystView → MaterializedArtifact（JSON，atomic write）
     │                                library/private/app/analyst_view/<TICKER>.json
     │  python -m webapp serve         ← 純讀：open → json.loads → validate → return
     ▼
GET /api/v1/{health,meta,stocks,stocks/{ticker},ranking,beta,coverage,watches} ＋ / （responsive Web App）
     ▼
Cloudflare Tunnel（既有那條）→ Cloudflare Access → iPhone Safari／桌機瀏覽器
```

**為什麼 materialize 與 serve 必須是兩條責任鏈：** 不只是「組裝一次要 4.2 秒」，而是
**點一下就重跑一次研究會讓 request path 有能力改變（或看起來改變）系統對一家公司的認知**。
分開之後，「APP 只是讀」變成一件可以被機械證明的事。

**四種互相獨立的證明**（`tests/test_webapp_request_path.py`，25 條）：
①**import 靜態掃描**（serve 端三個模組的 import 是 allowlist）；
②**runtime 模組哨兵**（打完一輪 request，斷言 `sys.modules` 沒多出任何模型／IO 模組——擋函式內延遲 import）；
③**檔案系統快照**（request 前後對 artifact 目錄與 `library/private/` 取雜湊，斷言一格未動——同時擋寫入與
cache-miss 自動重建）；④**socket 封殺**（request 期間 `connect`／`create_connection` 直接 raise，
斷言回應照樣完整正確）。⚠ 第 4 條攔的是 `connect` 而不是 socket 建構子：TestClient 的 event loop 自己要用
一對 loopback socket，攔建構子會攔到測試腳手架而不是被測物（L15-1）。

**artifact 契約**（`webapp/contracts.py`）：`schema_version`／`generated_at`／`as_of`／
`research_context_digest`／**兩個 digest**／`readiness`／`refresh`／`overview`／完整 `view`。
- **`content_digest`** 對整份內容取雜湊——偵測寫到一半或寫入後被改。
- **`freshness_identity`** 只對「認知狀態」取雜湊（as-of、context digest、read model 版本、readiness、
  refresh overall）。**價格動了不算認知變了**；兩件事共用一個訊號就會讓其中一件永遠讀不出來（L12）。
- fail closed：解析失敗／版本不符／digest 不合／缺必要欄位 → `ArtifactUnavailable` → **503**。
  ⚠ **「artifact 讀不到」（503）與「這檔沒有研究結論」（200 ＋ `readiness=blocked`）是兩件事，不得同形。**
- **stale 是狀態不是錯誤**：過期照樣回，明確標年齡，**絕不重建**。

**overview 是選取不是計算。** 清單卡片要的那幾格全部照抄 `AnalystView`——沒有百分比換算、沒有幣別換算、
沒有 gap 重算。單位原樣帶著走（GBp 與 GBP 差 100 倍，`dependencies.quote_unit` 是欄位不是要 parse 的句子）。

**private path 在 materialize 端遮蔽一次。** read model 的理由句會寫出 authority 檔案路徑
（例：「找不到 session 判斷檔（library/private/alpha/judgments/…）」）；那對開發者有用，但它是 private
filesystem 結構，不該經由 HTTP 出去。遮成 `«private-authority»`，**其餘文字逐字保留**。
在 materialize 端做一次，而不是讓每個消費端各自記得要遮（L16）。

**state artifact（2026-09-08，呈現責任重切 B1）：** per-ticker 的 Analyst View 之外，多了**跨標的的 state**
（`library/private/app/state/<kind>.json`；`webapp/contracts.py::STATE_SCHEMA_VERSIONS` 是封閉的 kind 字彙，
目前有 `ranking`／`beta`／`coverage`／`watches`）。`python -m webapp materialize --ranking` 走與 `python -m query.bottleneck` **同一條路**
（同一個 driver、`fetch_assertions`、registry），把 `rank_bottlenecks()` 的兩份排序**照抄**成 artifact——
不重排、不加權、不自建第二套結構評分；**每列每格與 CLI 輸出逐格相等**是驗收條件（`tests/test_webapp_ranking.py`）。
已知限制、兩份排序的說明、落差判準（可行動名次比純結構低 ≥ 2）與空產業組都從 `query.bottleneck` 的常數／函式取，
markdown 與 artifact 同源（L16）。`freshness_identity` 只含順序與每列的結構／證據欄位——`documents` 多一份
不算認知變了（L12）。`GET /api/v1/ranking` 與單檔同一套紀律：讀不到 503 ＋ remedy；排不出任何一列是
200 ＋ `top_pick=null` ＋ 理由，兩者不同形；四種 request-path 證明已涵蓋這條路由。
**APP 顯示排序但不重算排序**：唯一排序權威仍是 `rank_bottlenecks()`。

**`beta` kind（2026-09-08 B2）：** `python -m webapp materialize --beta` 以 `--no-refresh --no-record-risk` 純讀呼叫
`scripts/daily_beta_snapshot.run()`（同一個 `portfolio.allocation.build_beta_monitor`），**不重抓行情、不 append 風險快照**；
sleeve／差距狀態／行情狀態／降級原因的中文標籤全部從 `portfolio.allocation` 的對照函式取（L16）。逐檔折線的序列只搬
Engine C `technical_observations` 的 `session_date`＋`close_adjusted`——那張表還留著 08-29 前的動能欄位，**永遠不進 artifact**
（`tests/test_webapp_beta.py` 掃整份 JSON 鍵名）。畫面依 dataviz skill：水平堆疊條（現在的配置，色跟 sleeve 走）、分歧條
（距目標多遠，灰帶＝容忍區間）、儀表（風控上限、52 週位置）、單系列折線（自身收盤，含十字線 tooltip 與表格版）；
調色盤用 dataviz 參考實例的已驗證值（深淺兩套）。`freshness_identity` 只含各 sleeve 狀態／各檔行情狀態／風險警告，
價格心跳變了不算認知變了。

**`coverage`／`watches` kind（2026-09-08 B2b）：** 前者照抄 `query.coverage_gaps.scan()` 的分桶，並把 🔴 桶依
**前綴**切成「真正該挖的子瓶頸（`tech:`／`mat:`）」與「抽取產生的產品名詞（`prod:`）」——那是機械比對不是語意判斷，
判準與固定文字都住 `query/coverage_gaps.py`（markdown 與 artifact 同源）。後者照抄 Event Watch registry 的
`counters()`／`sweep_due()`／`is_stalled()` 與 `leads.trace_backlog()`，把**停滯**與**需要當場處置的追源**
獨立成區——那是這個機制唯一會安靜失效的地方（L14：防呆要自己出現）。兩者的 `freshness_identity` 只含
「哪些節點還空白」「有哪些 watch、各自什麼狀態」，節點改名或 `poll.last_checked` 更新不算認知變了。
⚠ **APP 不寫任何東西**：不喚醒 watch、不消化 fired、不改 lead 狀態。

**`positions` kind（2026-09-08 B2-positions）：** 把 `scripts/outcome_if_settled_today.py` 的資料收集段
抽成 `collect()`，另抽 `equal_weight_aggregate()`／`live_lane_rows()`／`anchor_health()` 三個純函式——
**markdown 與 artifact 讀同一份**（L16；第二份實作會立刻開始偏離）。抽取是行為保持的：`main()` 只剩
「collect → render」，輸出以「去數字後的骨架」比對零差異（盤中重跑會因價格變動換名次，所以不能比位元組）。
materialize **只呼叫 `collect()` 不呼叫 render**，因此不 append 排序快照、不寫聚合檔：維持唯讀。
計數器直接取 `DecisionStore.capital_expression_counters()`（本來就回傳 dict，不需重構 Engine D）。
⚠ 這一頁的**排版順序本身是判準**：真實部位 → **樣本效度** → 計數器 → 聚合 → 逐檔。反過來排的話，
一份有效 n 接近 1 的觀測會讀起來像 N 個獨立驗證（`tests/test_webapp_positions.py` 斷言這個順序）。state 目錄的解析只有一條規則
（`webapp/store.py::resolve_state_dir`：明示 > analyst 目錄下的 `state/` > 預設），serve／materialize／status 都走它。

**Web App 的資訊階層**（`webapp/static/`，vanilla JS，零外部資源，CSP 只允許 same-origin）：
清單卡片 → ①判讀狀態（blocked 時逐條寫「卡在哪一層＋為什麼」）→ ②頭條 → ③內部 vs 市場 →
④最脆弱的假設 → ⑤研究現況／disproof → ⑥Entry（optional）→ ⑦新鮮度 → ⑧「這份判讀不是什麼」。
formula／provenance／evidence／epistemics 全部收進 `<details>` drill-down。
**UI 只改資訊階層，不產生任何新的 summary judgment**：頭條那句話取自
`implied_return.epistemics.one_sentence`（authority 自組）並註明出處；
缺席語意的中文說明來自 `/api/v1/meta` 的字彙表，前端不維護第二份對照表。

**技術棧沿用既有的**：`starlette` ＋ `uvicorn` 已隨 `mcp>=1.28` 安裝，**本次沒有新增任何套件**，
也沒有前端建置工具鏈。部署重用既有 Cloudflare Tunnel（見 `deploy/cloudflare/README.md`）。

**刻意不做：** runtime chatbot／LLM、broker、買賣、部位尺寸、Portfolio 排序、跨標的排序的**重算**（`/ranking` 只照抄 `rank_bottlenecks()`）、
任何寫入端點、原生 App。

---

## 7. Engine D（Decision Lab）runtime

- Decision facts 存於 ignored `library/private/decision_lab/`；第一筆真實事件後只允許
  backup／restore 與 append-only correction，**不做破壞性 reset**。
- U7 之前的 `paper_events`／`live_supported_range`／`axis_ceiling` 欄位仍在歷史紀錄中
  可讀，但**不再增長也不回寫**。
- 資本表達層已於 2026-08-28 整組移除（`live_supported_range`／`axis_ceiling`／
  `paper_target`／probe cap／四動作）；注意力狀態只剩 `MONITOR`／`REVIEW`。
  真正的風控（5% 單筆、ETF 槓桿 cap、七天時效）全部保留——拿掉的是憑空的建議尺寸，
  不是煞車。

---

## 8. Portfolio / Risk（`portfolio/`＋`risk/`）

**單向：view → target exposure → hard limits。** A4 不形成 view，A3 不算尺寸。
判準與禁令（band 不是 gate、水位只呈現、不得復刻擇時語言）住 `AGENTS.md`；
這裡是它今天長什麼樣。

⚠ **呈現的家自 2026-09-08 起是 APP（`#/beta`），不是 Daily。** 下面這些欄位規格、燈號文字、
台股 freshness 與槓桿商品序列規則**一條都沒改**，改的是它們每天出現在哪裡：APP 由
`-m webapp materialize --beta` 每日更新、隨時可看，Daily 只印門檻跨越與狀態翻轉。
**Daily 仍須在 APP 當天沒被 materialize 時把這件事印出來**——否則「看不到」與「沒發生」同形（L12）。

**輸入／輸出（`target-architecture.md` §9）：**

| | `portfolio/` | `risk/` |
|---|---|---|
| 輸入 | `AlphaSignal[]` ＋ 現有持股 ＋ `config/target_allocation.json` | portfolio 的 target exposure |
| 輸出 | target exposure、配置差距、相對水位 | binding limits、violation 清單 |
| **不做** | 不形成 view、**不排序標的** | 不判斷好壞 |

`portfolio/alpha_exposure.py` 是 alpha 那一側的接點（Phase 7）：把 `AlphaSignal[]` join
到持股，回答「**這些候選我現在持有多少**」。它輸出的每個數字都是已經發生的事實，
**不是建議**；候選順序原樣沿用傳入順序（排序權威在 `rank_bottlenecks`，不在這一層）。
⚠ 它刻意以 duck typing 接受 signal，**不 import `alpha/`**——保持
`portfolio/ → alpha/` 沒有相依。
⚠ 持股讀不到時**整份降級並帶出 `blockers`，不逐檔輸出 0.0%**：那會讓使用者看到
「你一檔都沒買」，而事實是「我沒讀到你買了什麼」（L12）。
`single_position_nav_cap_reference` 的欄位名自己說出它不是 gate——真正的硬擋在
`store.record_live_choice`。

- **目標配置比例** SSOT 只有 `config/target_allocation.json`：sleeve 層級六格，分母是
  **已投入的非現金部位**（不含現金；cash floor 是另一個 authority）。
  查證：`python -c "import json;d=json.load(open('config/target_allocation.json'));print(d['basis'], sorted(d['sleeves']))"`
- **相對水位** 只用位置指標：52 週區間位置（主要）、距 52 週高點、距 SMA200，
  全部取自商品**自身**價格序列。⚠ **不得用動能指標表達水位**：RSI 量的是最近漲跌的
  單邊程度，與「站在自己區間哪裡」可以完全脫鉤，而且它正是 2026-08-01 測失敗的輸入，
  以「水位」之名放回來是換名字重來。
- **燈號固定配文字**：🟢行情正常／🔴資料不足（含 TWSE 官方較新而暫時隔離）／⚪歷史不足。
  舊語意（🟢可評估／🟡冷卻／排序中／⚪觀察／🔴暫停新增）已於 2026-08-29 廢止，不得回填。
- **標的表只負責三欄比較**：行情心跳（自身價格）、相對水位（自身價格）、所屬 sleeve
  配置狀態。可部署現金、投組 hard caps 與兩條相關性警告是**全局條件**，不在每檔重複。
- **逐檔心跳的最小要求**：每列明示商品自身的「最新完整交易日 `YYYY-MM-DD`＋1 日漲跌」；
  不能只寫沒有日期的「1 日」，也不能把最近收盤誤稱即時今日行情。
  `stale`／`quarantined` 時改列官方 reference 的日期與當日漲跌並附降級原因。
  逐檔表欄位保留完整（心跳 1／5／20 日＋52 週區間位置、距高點、距 SMA200）——
  2026-09-02 的「輕量版面」砍的是段落與重複敘述，**不是表格欄位**。
- 槓桿／重疊商品必須用自身價格序列：TQQQ 不得冒用 QQQ（實測 69% vs 85%），
  00631L／006208 同理不得冒用 0050。
- **台股 freshness：** `.TW` 先用 TWSE `STOCK_DAY_ALL` OpenAPI 校驗最新交易日；
  Yahoo session 落後、官方代碼缺列或 freshness 取不到時，該標的行情必須 `quarantined`，
  改列官方 reference 並附降級原因。⚠ 2026-08-29 起**單檔行情降級不再歸零任何 supported
  range**；降級的後果是那一列的水位不可信、必須現形，不是靜默消失。
  TWSE 的未還權 OHLC 只作最新日期與當日漲跌 reference，
  **不得混入 Yahoo adjusted-close 長期序列**。
- **自有現金可部署**固定顯示 `Portfolio CASH − cash floor`，並明說 cash floor 以上為
  Alpha／Beta 共用；另獨立顯示「未動用貸款額度／已借款／估計利息」，明標貸款不算自有現金。
  **不得用未解釋的斜線或 raw field name。**

## 8.1 兩條 gate 的補償控制細節

判準（「可否確定性重導」）與「放行與收緊必須同時發生」住 `AGENTS.md`；實作長這樣。

**Engine C 人工 ledger（`config/engine_c_observation_fields.json` 的 `verifiability`）：**
`mechanical` 換來的補償控制是 `append_manual_observation` 強制 value 必須是可機械比對的
JSON 數值（散文一律拒絕）——`mechanical` 的定義就是「可被重導核對」，而散文無法被 diff。
專用寫入口是 `scripts/record_mechanical_observation.py`，它**拒絕 judgment 欄位**，
那是它最重要的行為。⚠ 刻意**不驗 `source_ref` 格式**：現有觀測橫跨 SEC／AMF／HKEX／ASX／
TDnet 五種寫法，用 regex 驗會攔掉合法的法國 URD 引用（L15 記過的坑）。provenance 仍必填。
查證：`python -c "from engine_c.observation_fields import get_observation_field_registry as g;print(g().mechanical_field_names)"`

**圖 metadata 回填（`loader/source_dating.py`）四道補償控制：**
① 屬性白名單（只有 `published_at`／`retrieved_at`）；② `--basis` 必填並落地成節點屬性；
③ 寫入值另存 `published_at_backfilled`，**basis 與現值脫鉤是可偵測的**；
④ `published_at_method` 是封閉字彙，宣稱 `url_path` 的由 audit 拿當下的 `url` 重導。
另有一條真不變式：`published_at` 不得晚於 `retrieved_at`。
⚠ `loader/load_to_neo4j.py` 的 `MERGE_SOURCE_DOC` 用 `coalesce`，否則抽取 JSON 沒帶日期時
會把回填洗成 null，而**不會有任何東西報錯**。

---

## 9. 報告產出：cohort 是研究終點

Decision cohort 就是終點層級——Watchlist／Underwrite 三級模板已於 2026-09-02 除役
（實測：升格標記在生產碼中沒有任何下游消費端）。其中有價值的兩塊各有去處：

- **variant perception 收編進 cohort 的 thesis 欄位。** 操作定義：「當前股價／估值隱含
  的假設是 X，本 thesis 認為真實情況會是 Y，催化劑 Z 會讓市場重新定價。」
  重點是**股價說什麼**，不是「多數人信什麼」。
- **Lane Memo 降級為隨叫隨到的視圖**（`thesis/generate_lane_memo.py`）：想要一頁式綜合
  時從圖＋cohort＋variant perception 渲染。它是輸出格式，不是流程的一站，不 gate 任何事。

---

## 10. v0 Schema 的具體形狀

完整欄位表、vocab、claims 格式、`sole_source` 驗證規則見
[`../schema/graph_schema.md`](../schema/graph_schema.md)。

- **node** 帶內在慢變屬性（`ramp_difficulty_intrinsic`；`concentration_score` 為衍生值非手填）
- **edge** 帶關係型屬性（`substitutability`、`sole_source`、`structural_lead_time_weeks`、
  `ramp_execution`）
- `confidence` 只在不同 `origin_event` 之間累加（同一法說會多份摘要 ＝ 一個 origin_event）
- `consensus_coverage` / 股價 / 財務數字 → **不進圖**，進 Engine C

**三層 symbol 不可混用**（以 Sivers 為例）：研究行情是瑞典主掛牌 `SIVE.ST`（SEK）；
Google Sheet／execution authority 是 `FRA:2DG`（EUR）；Yahoo provider syntax 由
`identity/execution.py` 正規化成 `2DG.F`。快照對外仍回 canonical `FRA:2DG`。

---

## 11. 這份文件不涵蓋什麼

| 要找什麼 | 去哪 |
|---|---|
| 「我可以／不可以做什麼」 | [`../AGENTS.md`](../AGENTS.md) |
| 「這個詞是什麼意思」 | [`../CONCEPTS.md`](../CONCEPTS.md) |
| 「這件事怎麼跑」 | [`OPERATIONS.md`](OPERATIONS.md) |
| 「接下來要做什麼」 | [`ROADMAP.md`](ROADMAP.md) |
| 某個封閉字彙住哪、能不能擴充 | [`solutions/architecture-patterns/closed-vocabulary-registry.md`](solutions/architecture-patterns/closed-vocabulary-registry.md) |
| 36 筆歷史事故 → 六條 invariant → executable protection | [`refactor/historical-failure-matrix.md`](refactor/historical-failure-matrix.md) |
