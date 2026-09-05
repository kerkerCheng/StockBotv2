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
| consensus | Engine C `financial_snapshots`＋`engine_c.estimates` | `observation`，status **`partial`**（只有 next-FY 營收、PE、EV/Rev、目標價均值、導出 forward EPS） |
| price_implied_expectations | `alpha.context._implied_valuation` | **`heuristic_proxy`**（trailing/forward PE − 1）；隱含利潤率與 reverse DCF `not_modeled` |
| internal_fundamentals | — | **`not_modeled`** |
| earnings_bridge | — | **`not_modeled`**（列出今天已存在的原料：segment share、結構事件、依賴路徑） |
| expectation_gap | Q4（session）＋估計修正 vs 股價（`engine_c.estimates`） | Q4 `session_judgment`（ordinal）；數值 gap `not_modeled` |
| catalysts | AlphaSignal.catalysts＋thesis checkpoints＋Engine D 散文＋`shared.catalyst_state` | `partial`，capability＝`structured_dates_without_repricing_link` |
| falsification | AlphaSignal.disproof_conditions（L7 三件套）＋Engine D 散文＋thesis lifecycle | capability＝`structured_conditions_with_expiry_watch`；自動失效引擎 `not_modeled` |
| scenarios | AlphaSignal bull／base／bear | **`narrative`**；機率與目標估值 `not_modeled` |
| expected_return／downside／entry_logic | — | **`not_modeled`**，並列出「不要跟什麼混淆」（賣方目標價、市場隱含成長、排序名次） |
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

**下一階段的插座：** Causal Fundamental Model 落地後，`internal_fundamentals`／
`earnings_bridge`／`expectation_gap.internal_vs_*` 由 `not_modeled` 變成 `available`，
schema 不必重寫；view 的 `capability_map()` 就是「知道什麼／還不知道什麼」的常駐計數器。

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
