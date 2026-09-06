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
| valuation | **`alpha/valuation`**（§6.4）：內部 EPS × 明示目標倍數 | `deterministic`（capability `deterministic_fair_value_v1`）；fair value／現價／gap 三格分開，gap 附 `gap_is_not`；沒有估值假設或內部 EPS＝`missing` |
| expected_return／downside／entry_logic | — | **`not_modeled`**，並列出「不要跟什麼混淆」（賣方目標價、市場隱含成長、排序名次、**fair value gap**） |
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

**刻意不做（Step 2 以後）：** expected return、horizon、entry logic、buy／sell、portfolio、機率加權情境、逐情境目標估值、
多 method（EV/EBITDA／DCF 要先有內部現金流）、跨標的比較、consumer UI。

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
