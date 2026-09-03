# Target Architecture — Alpha Research Core 與四層分離

> **性質：** Phase 0 產出物之一。這份是**目標**，不是現況；現況見
> [`current-architecture.md`](current-architecture.md)。
>
> 這份文件的責任是把「重構完成時長什麼樣」寫到**足以被反駁**的程度：
> 每個新物件都有欄位、每條邊界都有一句「什麼東西不准跨過去」。

---

## 0. North Star 與分層

```
External Signal / Source
   │  Engine B — discovery / intake / source tracing
   ▼
Evidence  ──────────────────────────────────┐
   │  loader + schema                       │ EvidenceRef 是唯一的
   ▼                                        │ 跨層 provenance 載體
Knowledge Graph (Engine A / Neo4j)          │ ——任何一層都不得
   │                                        │ 「知道一件事卻說不出
   │  GraphResearchProvider（唯一出口）      │ 誰說的、什麼時候說的」
   ▼                                        │
┌────────────────────────────────────────┐  │
│  Alpha Research Core   （alpha/）       │◀─┘
│  ─────────────────────────────────────  │
│  Q1 Structural Scarcity                 │◀── Engine C（財務／市場／共識）
│  Q2 Economic Value Capture              │
│  Q3 Earnings / FCF Exposure             │
│  Q4 Expectation Gap  ← 系統最重要的一層  │
│  Q5 Catalyst                            │
│         ↓ AlphaModel.predict()          │
│      ResearchContext (as_of 凍結)        │
└────────────────────────────────────────┘
   │
   ▼
AlphaSignal  ── research view only，不含部位
   │
   ▼
Portfolio (portfolio/) — view → target exposure
   │
   ▼
Risk (risk/) — hard limits
   │
   ▼
Engine D (decision_lab/) — capital permission、DecisionContext freeze、
   │                        immutable history、outcome attribution
   ▼
Outcome Learning ──────────────────▶ 回饋到 AlphaModel 的量測
```

> **⚠ 這條主幹之外還有兩件事必須先講清楚，否則下面的契約會被誤讀：**
> **①「四引擎」不是憲法**——真正不可變的是五條 authority separation，見 **§12**。
> **②MCP／remote 是 optional adapter，不是核心**——依賴方向與邊界見 **§14**。
> 與新方向的逐條衝突分析見 **§13**；`AGENTS.md` 該怎麼調整見 **§15**。

**四個角色一句話：**

| 層 | 回答什麼 | **絕不做什麼** |
|---|---|---|
| Alpha Research | 「我們認為未來會怎樣，跟市場定價差多少」 | 不算部位、不碰資本、不寫 Engine A |
| Portfolio | 「這個 view 換算成多少 target exposure」 | 不形成 view、不下單 |
| Risk | 「這個 exposure 撞到哪條硬上限」 | 不判斷好壞、不排序 |
| Engine D | 「這筆資本被允許嗎、當時憑什麼、後來對不對」 | 不做研究、不算估值、不生成 thesis |

---

## 1. 目錄佈局

沿用 repo 既有的**平面 top-level package** 慣例，不引入 `stockbot/` namespace。

> **✅ 2026-09-03 使用者定案：平面 `alpha/`。** prompt §18 的範例原本是
> `python -m stockbot.alpha research ASML`；改成 `stockbot/` 需要搬動全部 15 個
> top-level package，屬 §20 明令禁止的「為了整理目錄做沒有價值的大 rename」，
> 而且會改變 `.codex/rules/stockbot-automations.rules` 裡 **16 條 exact command prefix**
> 的字串——那會**靜默打斷 daily 排程**。MVP 命令因此是：
> ```
> python -m alpha research COHR --as-of 2026-06-30
> ```
> ⚠ **首條 vertical slice 用 COHR 而不是 prompt 範例的 ASML**（2026-09-03 使用者定案）：
> 實測 ASML **不在 registry 的 100 家裡、也不在圖中**，要先走完整 onboard 才跑得動——
> 那會讓第一條切片同時測試 onboard 與新架構兩件事，出問題時分不清是哪一邊。

```
alpha/                          ← 新增。Alpha Research Core
  contracts.py                    EvidenceRef / ResearchContext / AlphaSignal / AlphaModel
  provider.py                     GraphResearchProvider（Protocol，唯一的圖出口）
  providers/
    graph_neo4j.py                concrete：包 query/ 的既有 Cypher，不新寫查詢
    fundamentals.py               concrete：包 engine_c
    expectations.py               concrete：包 engine_c 共識／估值 ＋ implied 計算
  context.py                      ResearchContext 組裝與 content-addressed freeze
  scarcity.py                     Q1（消費 query.bottleneck，不重算排序）
  value_capture.py                Q2
  earnings_exposure.py            Q3
  expectation_gap.py              Q4
  catalysts.py                    Q5
  causal.py                       StructuralEvent / CausalPath / CompanyImpact
  models/
    llm_assessor.py               structured LLM reasoning → schema-validated payload
    composite.py                  deterministic 組合 → AlphaSignal
  thesis/                         ← 由現 thesis/ 搬入（research 那部分）
    lifecycle.py, memo.py, evidence_manifest.py
  cli.py                          python -m alpha research | digest | memo

portfolio/                      ← 新增。view → target exposure
  exposure.py                     ← decision_lab/nav_exposure.py
  allocation.py                   ← decision_lab/beta_monitor.py（目標差距＋相對水位）
  policy.py                       ← decision_lab/beta_policy.py

risk/                           ← 新增。hard limits only
  limits.py                       ← thesis/investment_policy.py 的 cap 部分 ＋ store._HARD_CAP_BLOCKERS
  snapshot.py                     ← decision_lab/portfolio_risk.py

decision_lab/                   ← 保留名稱（見 §7），瘦身後只剩 Engine D
engine_b/  engine_c/  loader/  query/  identity/  storage/  fetchers/  mcp_server/
crons/  notifications/  scripts/  schema/  prompts/  skills/
```

**`query/` 不解散。** 它是 Cypher 的家；`alpha/providers/graph_neo4j.py` 呼叫它，
不是取代它。這樣 `rank_bottlenecks()` 仍是唯一排序權威（`AGENTS.md` 硬契約）。

---

## 2. `EvidenceRef` — 跨層 provenance 的唯一載體

**存在理由：** 現況有五套證據強度字彙（見 current-architecture §6.1），各有正當語意，
但沒有一個物件同時帶著它們。結果是每一層都要自己回頭查圖。

```python
@dataclass(frozen=True, slots=True)
class EvidenceRef:
    ref: str                      # 穩定引用字串，例 "graph://assertion/<id>"、
                                  # "sec://0001..."、"engine_c://manual_observation/<id>"
    kind: Literal["graph_claim", "graph_assertion", "graph_edge",
                  "source_doc", "engine_c_observation", "engine_c_snapshot",
                  "market_series", "external_document"]

    # ── provenance（來自 Engine A SourceDoc，或 Engine C ledger）
    source_doc_id: str | None
    origin_entity: str | None     # 誰說的（L8 獨立性判準的輸入）
    origin_event: str | None      # 哪個原始事件（confidence 只在不同 event 間累加）
    url: str | None
    quote: str | None             # 逐字引文（L6 反幻覺：具體型號必須逐字出現）

    # ── 時間（point-in-time 的骨架，⚠ 三個都不得省略）
    published_at: date | None     # 世界知道這件事的時間
    retrieved_at: date | None     # 我們抓到它的時間
    recorded_at: datetime | None  # 寫進我們系統的時間

    # ── 強度（五套字彙全部並列，不壓成一個分數）
    evidence_tier: Literal[1, 2, 3, 4] | None        # SourceDoc 文件類型可靠度
    demand_proof_level: str | None                   # Claim 的需求證實程度
    confidence: float | None                         # 圖上「關係存在」的信心 0–1
    evidence_class: str | None                       # bottleneck.EVIDENCE_RANK 的 5 級
    corroborating_origins: tuple[str, ...] = ()      # 其他獨立 origin_entity（L8）
```

**硬規則：**
1. **`AlphaSignal` 的每一個分數都必須能列出支持它的 `EvidenceRef`。**
   算不出來就不出分數，不是出一個沒有引用的分數。
2. **不得把五個強度欄位加權成單一 evidence score。** 那正是 L12「一表兩義」的相反錯誤：
   把五種不同的問題壓成一個答案，下游只能二選一。
3. **`published_at is None` 是合法值，但在 point-in-time 模式下必須被排除並計數。**
   「沒有日期」不等於「日期在 T 之前」（L11-5：我找不到 ≠ 它不存在）。

---

## 3. `GraphResearchProvider` — Neo4j 是 implementation detail

```python
class GraphResearchProvider(Protocol):
    """Alpha Research 讀圖的唯一介面。Cypher 不得出現在 alpha/ 之外的任何地方。"""

    def get_company_structural_context(
        self, company_id: str, *, as_of: date | None = None
    ) -> StructuralContext: ...

    def get_bottlenecks(
        self, *, sector: str | None = None, min_substitutability: int = 4,
        as_of: date | None = None
    ) -> Sequence[BottleneckRow]: ...

    def get_dependency_paths(
        self, company_id: str, *, max_hops: int = 3, as_of: date | None = None
    ) -> Sequence[CausalPath]: ...

    def get_substitution_paths(
        self, company_id: str, *, as_of: date | None = None
    ) -> Sequence[CausalPath]: ...          # 反證路徑：誰能取代它

    def get_supply_exposure(
        self, company_id: str, *, direction: Literal["upstream", "downstream"],
        as_of: date | None = None
    ) -> Sequence[SupplyExposure]: ...

    def get_second_order_beneficiaries(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]: ...

    def get_second_order_victims(
        self, event: StructuralEvent, *, max_hops: int = 3
    ) -> Sequence[CompanyImpact]: ...

    def get_claim_evidence(self, claim_id: str) -> Sequence[EvidenceRef]: ...

    def get_structural_changes_since(
        self, since: date, *, company_id: str | None = None
    ) -> Sequence[StructuralEvent]: ...
```

**三條硬規則：**

1. **provenance 不得被隱藏。** 每個回傳型別都必須有 `evidence: tuple[EvidenceRef, ...]`
   欄位。provider 的價值是「不用寫 Cypher」，不是「不用知道證據來自哪」。
2. **`as_of` 是一等參數，不是選配。** 即使 Phase 1–5 的 concrete 實作只支援
   `as_of=None`（＝當前圖），簽名從第一天就要有它，並在 `as_of` 非 None 時
   **明確拋 `PointInTimeUnsupported`**——不准靜默回傳當前資料。
   （L13：成功與失敗在同一個訊號上同形，是最危險的形狀。）
3. **provider 不做判斷。** 它回傳結構事實與證據；「這算不算瓶頸」是 `alpha/scarcity.py` 的事。

### 3.1 as-of 投影的技術路徑（Phase 6 前置）

現況：canonical edge 的 `attributes` 是**對所有 EdgeAssertion 的當前投影**，無日期。
目標：`as_of` 模式下改走
```
EdgeAssertion -[:CITES]-> SourceDoc  WHERE d.published_at <= $as_of
  → 重跑 loader/edge_resolution.py 的 collapse 規則
  → 得到 as-of canonical attributes
```
**這只能在 provider 層做**（一次），不能在各消費端各加 WHERE（N 次，必漏）。
前置條件與缺口見 current-architecture §4.2。

---

## 4. `ResearchContext` — 形成觀點時看到什麼

```python
@dataclass(frozen=True, slots=True)
class ResearchContext:
    ticker: str
    company_id: str | None
    as_of: date

    graph: StructuralContext                  # provider 產出，含 evidence
    structural: ScarcityInputs                # substitutability / sole_source / qualification / lead_time
    fundamentals: FundamentalsSnapshot        # Engine C：margin / revenue / FCF / shares / debt
    market: MarketSnapshot                    # 價格、FX、流動性
    consensus: ConsensusSnapshot              # analyst count / target / forward 倍數 / estimates
    valuation: ValuationSnapshot              # 由上述導出的 implied fundamentals
    catalysts: tuple[CatalystRef, ...]

    evidence_refs: tuple[EvidenceRef, ...]    # 全部引用的去重聯集
    freshness: Mapping[str, FreshnessState]   # 每個 section 的 as-of 距離與狀態
    source_versions: Mapping[str, str]        # policy_version / schema_version / provider 版本
    digest: str                               # content-addressed（同 Engine D 的作法）
```

### ⚠ `ResearchContext` ≠ `DecisionContext`——**兩者不得合併，理由不是潔癖**

| | `ResearchContext`（alpha/） | `DecisionContext`（decision_lab/context.py，既有） |
|---|---|---|
| 回答 | 形成投資觀點時看到什麼 | 真的動用資本時凍結了什麼 |
| 何時建立 | 每次 research，可能一天多次 | 只在 `evaluate-signal`／`reassess` 時 |
| 內容 | 偏重結構、估值、預期 | 偏重 identity、持股、FX、政策版本、freshness gate |
| 可否重算 | **可以**（研究可以重跑） | **不可以**（append-only，舊 decision 永遠引用原 digest） |
| Authority | 無——它是研究工作區 | **是**——它是稽核責任的載體 |
| 失效後果 | 研究要重做 | 決策紀錄失真，L10 明令不得破壞性重建 |

**合併的具體災難：** research 一天跑十次，每次都會建一個 context。若它們與
DecisionContext 共用同一張表，Decision Store 會從「268 筆有責任的決策紀錄」
變成「幾千筆研究草稿裡混著 268 筆決策」，而**兩者都是 append-only 拿不回來**。

**銜接方式：** `AlphaSignal` 帶 `research_context_digest`。Engine D freeze 時把那個
digest 記進 `DecisionContext`，形成「這筆決策引用了哪一份研究」的可稽核鏈——
但不複製內容。

---

## 5. `AlphaSignal` — research view，不是 position

```python
@dataclass(frozen=True, slots=True)
class AlphaSignal:
    ticker: str
    company_id: str | None
    as_of: date

    # ── 五個成分（prompt §6 的五問，各自可 explain）
    # ⚠ 每個 score 都是 `Score | None`；`None` = 不知道，`0.0` = 我判斷它很弱。
    # 每個 Score 內含 declared 與 effective 兩個值（F-25，見 phase-1-plan §2.1b）。
    structural_score: Score | None       # Q1 Structural Scarcity
    value_capture_score: Score | None    # Q2 Economic Value Capture
    earnings_exposure_score: Score | None  # Q3 Earnings / FCF Exposure
    expectation_gap_score: Score | None  # Q4 Expectation Gap
    catalyst_score: Score | None         # Q5 Catalyst

    direction: Literal["long", "short", "neutral"]
    confidence: float                    # 0..1

    # ⚠ v1 刻意**沒有** scalar `value` / `alpha` 欄位。理由見下方硬規則 4。
    # 排序由 ordering_key() 以 deterministic 字典序產生，不做加權總分。
    def ordering_key(self) -> tuple: ...

    expected_horizon: str               # 例 "2-4 quarters"

    # ── 敘事（LLM 產出，schema 驗證後才進來）
    thesis: str
    variant_view: str                   # 市場隱含 X／本 thesis Y／催化劑 Z
    bull_case: str
    base_case: str
    bear_case: str

    catalysts: tuple[Catalyst, ...]
    risks: tuple[str, ...]
    disproof_conditions: tuple[DisproofCondition, ...]   # ⚠ 必填非空

    evidence_refs: tuple[EvidenceRef, ...]
    model_components: Mapping[str, ComponentTrace]       # 每個分數的推導過程
    research_context_digest: str
    metadata: Mapping[str, Any]                          # model id / prompt version / rubric version
```

**硬規則：**

1. **`AlphaSignal != Position`。** 它沒有、也永遠不會有 `weight`／`shares`／`nav_pct`
   欄位。要 sizing 就去 `portfolio/`。
   （這條直接繼承 `AGENTS.md`「Alpha 呈現契約」：系統終點是排序，不是尺寸。
   拿掉的是憑空的建議尺寸，不是煞車。）
2. **`disproof_conditions` 非空**，且每條必須帶「核查頻率」與「觸發後 48 小時內做什麼」
   （L7：欄位有填但沒有後續流程＝貼一個永遠不會響的火警警報）。
3. **每個 `*_score` 都必須在 `model_components` 有對應 trace**，trace 裡列出
   輸入值、`EvidenceRef` 與規則版本。**算不出來就是 `None`，不是 0.0**——
   0.0 是「我判斷它很弱」，`None` 是「我不知道」，兩者混用就是 L12。
4. **v1 不產生 scalar `value` / `alpha`（2026-09-03 使用者定案）。**
   ⚠ **這一條刻意偏離原 prompt §18 的 MVP 範例輸出 `"alpha": 0.42`**，理由是本 repo 的實測：
   2026-08-21 pq1 排序用加權總分，`tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0`——
   **三個各自成立的弱理由相加，就壓過了一則講「誰掏 122 億綁誰」的資本承諾事件**，
   於是每日 5 個 slot 有 3 個排的是 7 週前、公司已明文降範圍的 Form 4。
   改成 **LLM 做封閉字彙分類 ＋ 程式做字典序**之後，「只是信心／無內容」由 3 → 0、
   前 20 名 Form 4 由 16 → 0。**字典序結構上沒有補償性，加權總分結構上有。**
   五個 score 有完全相同的形狀，所以套用同一個結論。
   - **排序：** `ordering_key()` 回傳 tuple，第一鍵是**最弱的那個 score**
     （同 `weakest_axis` 的形狀），其後依 Q4 → Q1 → Q5 → Q2 → Q3。
     排序鍵順序本身是一個可版本化、可否證的決定，寫成具名 `OrderingRule`。
   - **重開條件：** 若日後仍要 scalar，必須先能回答「換掉組合規則，現有 N 筆 signal
     有幾筆排序會變」，並通過 L14 的三個免 outcome 測試。
   - **`test_alpha_signal_has_no_composite_scalar`** 守住這條（掃欄位名，
     出現 `value`／`alpha`／`score`（單數總分）即失敗）。
5. **`expectation_gap_score` 不得由低本益比直接得出**（§20 明令）。
   它必須是 `internal_implied_fundamentals` 與 `market_implied_fundamentals` 的**差**。
6. **`None` 不是 0。** `None`＝不知道（該 score 算不出來），`0.0`＝我判斷它很弱。
   `ordering_key()` 對 `None` 的處理必須顯性（排最後，且該 signal 標為 `incomplete`），
   不得把 `None` 當 0 參與比較。

---

### 5.0 舊五軸 → 新五 score 的乾淨轉換（2026-09-03 使用者定案：**取代，不並存**）

實測 41 個 operational cohort（`python scripts/dualrun_axis_conversion.py`）：

| 舊軸（問「證據多強」） | 新 score（問投資問題） |
|---|---|
| `technical_causal_link` | `structural`（Q1） |
| `commercial_maturity` | `value_capture`（Q2） |
| `financial_resilience` | `earnings_exposure`（Q3）⚠ **只轉得到一半** |
| `valuation_payoff` | `expectation_gap`（Q4） |
| **`source_reliability`** | **無**——它是 meta 軸 → `EvidenceQuality` 上限 |
| **無** | **`catalyst`（Q5）**——舊系統沒有這一軸 → 轉換後恆為 `None` |

**`source_reliability` 的處置是本次轉換最重要的設計決定。**
它不是一個投資問題（「你憑什麼相信前面那些答案」不是「這檔好不好」），
所以不能當第六個維度。它從**第五個被 `min()` 的分量**變成**套在所有維度上的上限**：

```
舊：weakest = min(五軸)             → 只說「證據不夠」
新：effective = min(declared, ceiling) → 說「所以**哪個投資維度**看不清」
```

**實測依據（L14 恆亮測試）：舊 `source_reliability` 在 41 個 cohort 中有
33 個（80%）是 weakest**——它幾乎總是最弱，於是其他四軸的判斷很少改變結論。
一個觸發率 80% 的分量沒有鑑別力。

> ⚠ **誠實的但書：新 `weakest` 也有 73% 集中在 `structural`。**
> 轉換**換了標籤，沒有解決集中**——依同一條 L14 測試，新 weakest 同樣接近恆亮。
> 差別只在**可行動性**（新標籤指得出下一步：補 counter-path）。
> **那是可讀性的改善，不是鑑別力的改善。** 真正要讓這個數字下降的是
> Phase 4／5（補 Q3 的 segment revenue、Q5 的結構化 catalyst），不是再改一次標籤。

**兩個誠實的缺口，不得用預設值填掉：**
1. **Q3 只轉得到一半**——舊軸問「公司撐不撐得住」，新 Q3 問「對 EPS/FCF 多重要」，
   後者需要 segment revenue share，而 **Engine C 沒有這個欄位**。轉換結果帶
   `partial:legacy_financial_resilience_only`。
2. **Q5 沒有來源**——轉換後 `catalyst_score is None`。**那是正確答案**：
   填預設值會讓「沒有結構化催化劑」看起來像「催化劑很弱」。

**轉換是單向的。** Decision Store append-only，268 筆歷史 payload 永不改寫（L10）；
`alpha/legacy_axes.py` 只有 `convert_axis_results()`，**沒有也不會有 `to_legacy()`**
——那會製造兩份可寫的真相。

**dual run 結果：41 個 cohort、5 類 semantic diff、UNEXPECTED = 0**
（依 `historical-failure-matrix.md` §8，unexplained diff 未歸零前不得移除 legacy）。

### 5.1 v1 的 MVP 輸出形狀（取代 prompt §18 的範例）

```jsonc
{
  "ticker": "COHR",
  "company_id": "co:coherent",
  "as_of": "2026-06-30",
  "direction": "long",
  "confidence": 0.78,

  // 五個 score，各自 declared / effective 分開，各自可 explain
  "scores": {
    "structural":        { "declared": 0.94, "effective": 0.94, "trace": "ct_a1b2" },
    "value_capture":     { "declared": 0.82, "effective": 0.82, "trace": "ct_c3d4" },
    "earnings_exposure": { "declared": 0.79, "effective": 0.41, "trace": "ct_e5f6",
                           "downgrade_reason": "segment_revenue_missing" },
    "expectation_gap":   null,        // ← 不知道，不是 0
    "catalyst":          { "declared": 0.55, "effective": 0.55, "trace": "ct_g7h8" }
  },
  "weakest": "expectation_gap",       // ← 排序第一鍵，也是「該補什麼」
  "research_status": "incomplete",    // 有 None score

  "thesis": "...",
  "variant_view": "市場隱含 X／本 thesis 認為 Y／催化劑 Z",
  "bull_case": "...", "base_case": "...", "bear_case": "...",
  "catalysts": [...], "risks": [...],
  "disproof_conditions": [
    { "condition": "...", "check_frequency": "quarterly",
      "action_within_48h": "..." }          // ← L7 三件套，缺一即 raise
  ],
  "evidence_refs": [...],
  "model_components": { "ct_a1b2": { "inputs": {...}, "rule_version": "...",
                                     "evidence_refs": [...] } },
  "research_context_digest": "sha256:...",
  "metadata": { "model": "...", "prompt_version": "...", "ordering_rule": "v1" }
}
```

**⚠ 沒有 `"alpha": 0.42` 這一欄。** `weakest` ＋ 五個 score 就是排序資訊；
`ordering_key()` 由它們產生 deterministic 的序。
**每個值都可 explain**——`trace` 指向 `model_components` 裡的推導過程與 `EvidenceRef`。

---

## 6. `AlphaModel` — 研究模型的唯一介面

```python
class AlphaModel(Protocol):
    name: str
    version: str

    def predict(
        self, ticker: str, as_of: date, context: ResearchContext
    ) -> AlphaSignal: ...
```

**模型不負責：** position sizing、leverage、portfolio constraints、trade execution。

### 6.1 LLM 與 deterministic 的分工（prompt §11 落地）

```
deterministic retrieval            ← GraphResearchProvider ＋ Engine C
        ↓
structured LLM reasoning           ← alpha/models/llm_assessor.py
        ↓  （產出 JSON，帶 evidence_refs）
schema validation                  ← contracts.py，pydantic/dataclass 驗證
        ↓  （引用必須解析得到 ResearchContext 內的物件，否則 reject）
deterministic calculation          ← alpha/models/composite.py
        ↓
AlphaSignal
```

| LLM 負責（語意） | Python 負責（確定性） |
|---|---|
| substitutability 判斷、qualification barrier、switching cost | 財務比率、估值數學、歷史報酬 |
| technological moat、bottleneck durability | EPS／FCF 敏感度計算 |
| pricing power、management commentary 解讀 | 排序、portfolio sizing、risk limits |
| causal chain、variant perception、disproof condition | implied growth／implied margin 的反解 |

**L15 的順序不可反：先解析身分，再查權限。** LLM 可以解析與提議，
**不可以授權**——evidence tier、graph admission、資本、live choice 永遠 deterministic。

**不為了 multi-agent 而 multi-agent**（§20）：`llm_assessor` 是**一個**呼叫，
不是五個 persona 各答一題。五個問題可以在同一次 structured output 裡回答。

### 6.2 現有的 AlphaModel 雛形（重要發現）

**`decision_lab reassess <cohort> --assessment <file.json>` 已經就是這個介面。**
研究 agent 產出五軸 JSON → Engine D 驗證引用 → 凍結進 decision。

換句話說**「LLM 產出研究判斷 → schema 驗證 → deterministic 消費」這條管線已經跑了幾個月、
有 268 筆紀錄**。Phase 3 要做的不是發明新介面，是把那個檔案的 schema
從「五軸 assessment」升級成 `AlphaSignal`，並讓 Engine D 透過 adapter 消費它。

---

## 7. Engine D 的目標邊界

**package 名稱維持 `decision_lab/`。** 理由：①`decision_payload` 的 `"sizing"` key 等
歷史欄位已凍結在 268 筆 append-only 紀錄裡；②`python -m decision_lab ...` 出現在
daily 的 exact command rule 裡；③改名是 §20 禁止的無價值 rename。
文件與對話一律稱它 **Engine D**。

**Engine D 保留：**
- Point-in-Time **Decision**Context freeze（`context.py`、`store.freeze_context_bundle`）
- Investment policy 的**強制**（不是計算——計算歸 `risk/`）
- Capital authority（`capital_authority.py`：cash floor、貸款額度）
- Approval semantics（`coverage.py` 的 lane 權限、`blocker_severity`）
- Action Card（`action_card.py`）
- Explicit human choice（`execution.record_live_choice` / `record_live_fill`）
- Immutable decision history（`store.py`）
- Outcome attribution（`outcomes.py`）

**Engine D 移出：** fundamental research、structural analysis、valuation research、
catalyst analysis、thesis generation、alpha scoring、expectation-gap reasoning、
beta 呈現、NAV 呈現、投組風險快照。

**Engine D 消費 AlphaSignal 的方式（Phase 3）：**
```python
# decision_lab/adapters/alpha.py  ← 新增，唯一入口
def coverage_assessment_from_signal(signal: AlphaSignal) -> AssessmentPayload:
    """把 AlphaSignal 轉成既有五軸 assessment payload；不改 store schema。"""
```
**先不動 Decision Store schema。** 舊 268 筆紀錄不回寫（L10：拿不回來的資料只能 append）。

---

## 8. 多跳因果的 domain objects

現況：圖有 529 條 canonical domain edge、`DEPENDS_ON` 49 條、`CONSTRAINED_BY` 8 條，
但**沒有任何物件表達「A 卡住 → B 受害 → C 受益」**。

```python
@dataclass(frozen=True, slots=True)
class StructuralEvent:
    event_id: str
    kind: Literal["capacity_constraint", "capacity_expansion", "qualification",
                  "design_win", "competitor_exit", "substitution", "price_move",
                  "regulatory", "supply_disruption"]
    subject_id: str                       # co:* / tech:* / mat:*
    direction: Literal["tightening", "loosening"]
    observed_at: date
    evidence: tuple[EvidenceRef, ...]

@dataclass(frozen=True, slots=True)
class CausalPath:
    nodes: tuple[str, ...]                # 圖上的節點 id 序列
    relations: tuple[str, ...]            # 邊 relation 序列，len == len(nodes) - 1
    hops: int
    weakest_link: str                     # 這條路上最不確定的一段（edge_key）
    evidence: tuple[EvidenceRef, ...]

@dataclass(frozen=True, slots=True)
class CompanyImpact:
    company_id: str
    ticker: str | None
    direction: ImpactDirection            # BENEFICIARY / VICTIM / AMBIGUOUS
    magnitude: ImpactMagnitude            # HIGH / MEDIUM / LOW / UNKNOWN
    confidence: ImpactConfidence          # 由 path 上最弱一段決定，不是平均
    time_horizon: TimeHorizon             # WEEKS / QUARTERS / YEARS
    path: CausalPath
    rationale: str                        # LLM 產出，必須引用 path 上的節點
```

**兩條硬規則：**
1. **`confidence` 取路徑上最弱的一段，不取平均。**
   平均會讓「三段強＋一段完全沒證據」看起來比「兩段中等」可靠——那正是
   `AGENTS.md` 反覆講的補償性問題（pq1 排序 2026-08-22 已經因為同一個病重排過一次）。
2. **多跳結論永遠標 `derived`，不入圖。**
   圖只存有逐字證據的關係；`CompanyImpact` 是推論，住 `alpha/`，
   要入圖必須另走 admission gate。

---

## 9. Portfolio / Risk 的目標邊界

| | `portfolio/` | `risk/` |
|---|---|---|
| 輸入 | `AlphaSignal[]` ＋ 現有持股 ＋ `config/target_allocation.json` | portfolio 的 target exposure |
| 輸出 | target exposure、配置差距、相對水位 | binding limits、violation 清單 |
| **不做** | 不形成 view、不排序標的 | 不判斷好壞 |

**既有契約完全不變，一個字都不放寬：**
- **系統不產生任何 alpha 部位尺寸**（`AGENTS.md` Alpha 呈現契約）。
  `portfolio/` 對 alpha 只輸出「候選＋NAV 佔比呈現」，不輸出建議股數。
- **beta 的訊號機制已於 2026-08-29 拔除**（實測 0 勝 3 敗），
  `portfolio/allocation.py` 只做「目標比例 ＋ 相對水位」，
  **不得以任何名義復刻擇時語言**（今天是否投入／本輪上限／節奏）。
- **三個硬擋保留：** 5% 單筆 NAV、ETF 槓桿 nominal 20%／effective 40%，
  ＋凍結快照七天時效。numeric SSOT 仍是
  `config/investment_policy.json` 與 `config/beta_policy.json`。
- 相對水位**只呈現、不排序、不換算金額**；一旦拿它排序，它就變回訊號。

---

## 10. Testing 目標（prompt §19 落地）

| 測試類 | 守什麼 | 最小斷言 |
|---|---|---|
| **Graph provider contract** | 每個 provider 方法回傳的物件都帶非空 `evidence` | fake provider ＋ Neo4j provider 跑同一組斷言 |
| **Evidence provenance** | `AlphaSignal` 的每個非 None score 都能列出 ≥1 個 `EvidenceRef` | 反例：手工造一個無引用的 score → 必須 raise |
| **Point-in-time** | `as_of` 模式下不得回傳 `published_at > as_of` 的證據 | **7/5 才發布的 filing 不得出現在 6/30 的 `ResearchContext`** |
| **Anti-lookahead** | `as_of` 未實作時必須 `raise PointInTimeUnsupported`，不得靜默回當前資料 | 這條比上一條更早需要（L13） |
| **AlphaSignal schema** | 必填欄位、`disproof_conditions` 非空、無 position 欄位 | 掃輸出 key，出現 `weight`/`shares`/`nav` 即失敗（同 `test_nav_exposure` 的禁用字手法） |
| **無加權總分** | `AlphaSignal` 沒有 scalar `value`／`alpha`；排序由 `ordering_key()` 的字典序產生 | 加一個 `value: float` 欄位 → 必須紅（§5 硬規則 4） |
| **Earnings sensitivity** | 敏感度計算對已知輸入給出已知輸出 | 手算對照 |
| **Expectation gap** | 低 P/E 不得單獨產生高 gap 分數 | 造一個低 P/E ＋ 共識與 thesis 一致的案例 → gap ≈ 0 |
| **Causal path** | `confidence` 取最弱段而非平均 | 三強一弱的路徑 → confidence == 弱段 |
| **Engine D / Alpha separation** | `decision_lab/` 不得 import `alpha/`；`alpha/` 不得 import `decision_lab.store` | import 掃描測試（同 `tests/test_storage_boundary.py` 手法） |
| **Cypher containment** | `alpha/` 之外（除 `query/`、`loader/`、`mcp_server/`）不得出現 Cypher 字串 | 正規表達式掃描 |

**既有 126 個測試檔全部保留。** 重構期間它們是唯一能證明「行為沒變」的東西——
2026-08-28 的 U2 就是靠 characterization 測試在三分鐘內打臉一個「零行為變化」的錯誤宣稱。

---

## 11. 明確不做的事（§20 落地檢查表）

| 禁止 | 本設計如何遵守 |
|---|---|
| 重建 Neo4j | `alpha/providers/graph_neo4j.py` 只讀既有圖；`loader/` 不動 |
| 丟掉 provenance | `EvidenceRef` 是強制欄位，provider 每個回傳型別都帶它 |
| 用 vector RAG 取代 KG | 本設計不含任何 embedding 檢索；RAG 仍是 Neo4j 內建、供 memo 用 |
| 新增大量 persona agents | `llm_assessor` 是一支，不是五支 |
| LLM 做 deterministic math | §6.1 分工表；`composite.py` 是純 Python |
| LLM 直接交易 | live choice/fill 仍 100% 人工，Engine D 邊界不動 |
| 把 bottleneck 當 buy signal | `structural_score` 只是五分之一；`value` 必須經過 Q2–Q5 |
| 把低 P/E 當 expectation gap | §5 硬規則 5 ＋ §10 測試 |
| 混合 research state 與 capital state | §4 的 ResearchContext / DecisionContext 對照表 |
| 讓 Engine D 繼續膨脹 | §7 移出清單 ＋ §10 separation 測試 |
| 無價值大 rename | `decision_lab/`、`query/`、`engine_*` 全部保留原名 |
| 訊號未可信就 overfit backtest | Phase 6 排在最後，且 point-in-time 前置未達成前不得跑 |
| 第二套 graph / financial current-state authority | provider 是**唯讀 view**，不落地任何快取表 |

---

## 12. 真正的憲法：五條 authority separation（取代「四引擎」）

> **使用者定案（2026-09-03）：不要把「Engine A/B/C/D 四引擎架構本身」當成不可變憲法。**
> 引擎命名是**現行實現方式**；不可變的是**權責分離**。

| # | Authority | 擁有什麼真相 | 唯一寫入者 | 可變性 | 今天由誰實現 |
|---|---|---|---|---|---|
| **A1** | **Structural / Evidence truth** | 實體、關係、claim、provenance、逐字引文 | 經人工 admission gate 的 loader | 可重建（extraction 檔是 ground truth） | Engine A（Neo4j）＋`loader/` |
| **A2** | **Financial observation** | 帶時戳的財務／市場／共識觀測 | ETL（可重建）＋ append-only 人工 ledger | 混合：projection 可重建、ledger 只能 append | Engine C |
| **A3** | **Research belief / Alpha** | 「我們相信什麼、憑什麼、什麼會推翻它」 | 研究流程（LLM 提議 → schema 驗證） | **可重算**（研究可以重跑） | 🔴 **今天沒有家**——散在 Engine D 的五軸、`thesis/`、`query/bottleneck` |
| **A4** | **Portfolio / Risk** | 目前曝險、目標配置、硬上限 | policy config ＋ Google Sheet（外部 authority） | 可重算 | 🔴 散在 `decision_lab/` 的 beta／nav／risk 模組 |
| **A5** | **Capital decision / accountability** | 「當時憑什麼決定、使用者選了什麼、後來對不對」 | 明確的人工動作 | **append-only，Git 救不回** | Engine D |

**五條分離規則（這才是憲法）：**

1. **A1 不含時變數字。** 股價、估值、共識、未來 EPS、capex 推估**永不入圖**
   （L4；也是 2026-09-03 使用者對 investable digest 的「分段隔離」直覺）。
2. **A3 不得成為第二個 A1／A2 current-state authority。** research provider 是唯讀 view，
   不落地任何快取表。
3. **A3 可重算、A5 不可重算。** 這是 `ResearchContext` 與 `DecisionContext` 必須分開的
   全部理由（§4；也是 L10 與 F-30 的直接推論）。
4. **A4 不形成 view，A3 不算尺寸。** view → target exposure → hard limits 是單向的。
5. **A5 是唯一能授權資本的地方**，且 live 永遠 100% 人工。
   **research automation ≠ capital authority。**

**判別問法：** 一條規則若在「換掉 Neo4j」「把 Engine D 拆成三個 package」之後仍然成立，
它屬於這五條；否則它是 CURRENT_ARCHITECTURE。

---

## 13. 與新方向的逐條衝突分析

> 對使用者列出的 12 條新方向，逐條檢查 `AGENTS.md` 現況：
> ✅相容｜🟡缺口（不衝突但沒寫）｜🔴衝突（現行文字必須改）

| # | 新方向 | 判定 | `AGENTS.md` 現況與處置 |
|---|---|---|---|
| 1 | **Structural importance ≠ investability** | ✅ | 已明文：「**『是個真瓶頸』不等於『現在該投』**」（主題範圍段）。四維度已含需求錨點／客戶端資本承諾／標的純度。**不需改，只需升格為 `AlphaSignal` 的 Q1–Q3 分工** |
| 2 | **Bottleneck ≠ buy signal** | 🔴 **部分衝突** | 判準本身相容（「已知會失焦的指標」「進場靠判斷，出場靠 disproof」）。**衝突在這一句：「唯一排序權威是 `rank_bottlenecks()`，不得另建平行排序」**——`AlphaSignal.value` 排序會直接違反它的字面。**處置：改寫為「結構排序的唯一權威是 `rank_bottlenecks()`；alpha 排序必須消費它作為 `structural_score`，不得重算結構分，也不得繞過它自建第二套結構評分」** |
| 3 | **ResearchContext ≠ DecisionContext** | 🟡 缺口 | `AGENTS.md` 只定義 DecisionContext，且措辭讓人以為**任何**凍結 context 都屬 Engine D。**處置：新增一句「研究工作區的凍結不是 Engine D authority」**（§4 表格） |
| 4 | **AlphaSignal ≠ Position** | ✅ | Alpha 呈現契約已極強：「系統不給部位尺寸」「拿掉的是憑空的建議尺寸，不是煞車」。**直接繼承** |
| 5 | **Research automation ≠ capital authority** | ✅ | 四個 gate ＋「LLM 可以解析與提議，不可以授權」（L15）。**直接繼承，且要寫進 §12 的 A5** |
| 6 | **Alpha 必須考慮 market expectation / variant perception** | 🟡 **缺口** | variant perception 的**操作定義已有**（2026-09-02 定案：市場隱含 X／thesis Y／催化劑 Z），但「哪些標的值得看」的**四維度不含 expectation gap**。**處置：四維度 → 五 score，expectation gap 是新增的第四題** |
| 7 | **Engine D 不應承擔 fundamental research／thesis／valuation／catalyst／alpha scoring** | 🔴 **衝突（轉換方案已定，見 §5.0）** | `AGENTS.md` 的 Engine D 表格逐字寫著它擁有「Shadow、Coverage、**五軸 Confidence、瓶頸排序**、NAV 比例呈現、outcome」。**處置：Engine D 的 authority 欄改為 §12 的 A5。五軸已於 2026-09-03 定案由新五 score 取代（不並存），轉換器 `alpha/legacy_axes.py` 已交付並跑過 41 cohort dual run** |
| 8 | **LLM qualitative／deterministic numeric** | ✅ | L15 逐字已有。**處置：從 lesson 升格為 §6.1 的架構分工表** |
| 9 | **所有歷史 research／backtest 必須 point-in-time correct** | 🔴 **重大缺口** | 現行 point-in-time contract **只涵蓋 Engine D 決策**，不涵蓋研究與回測；**Engine A 根本沒有 as-of 能力**（`current-architecture.md` §4.2 實測）。**處置：INV-6 ＋ `GraphResearchProvider.as_of` ＋ `PointInTimeUnsupported`** |
| 10 | **所有重要 conclusion 可回溯至 evidence** | 🟡 | 圖層已極強（每個 node/edge/claim 必掛 `source_ids`），但**五軸 assessment 的 reason 是自由文字**、`variant_perception` 也是。**處置：`AlphaSignal` 的每個非 None score 強制帶 `EvidenceRef`** |
| 11 | **所有重要 thesis 必須有 disproof** | ✅ | L7 ＋ schema「可證偽是一等公民」。**處置：升格為 `DisproofCondition` 型別強制（含核查頻率與 48h 動作）** |
| 12 | **Local-first, remote-capable if needed later** | ✅ | 「Local-first 方針（2026-07-26 使用者定案）」已存在，且 daily／weekly prompt 逐字禁用 MCP。**處置：把管道層架構圖裡的 MCP 動詞移出**（見 §14） |

**淨結論：2 條真衝突（#2、#7）、3 條重大缺口（#3、#6、#9）、其餘相容。**
`AGENTS.md` 的判準絕大多數**支持**新方向——衝突集中在「Engine D 擁有什麼」與
「排序權威」兩句話，而它們都是 CURRENT_ARCHITECTURE 而非 INVARIANT。

---

## 14. Optional Remote Adapters — 依賴方向

> **核心原則：新的核心系統必須能在完全沒有 MCP 的情況下正常運作。**
> **Dependency direction 必須由 peripheral 指向 core。Core 不得依賴 MCP。**

### 14.1 目標依賴圖

```
  ┌──────────────────────────────────────────────────────┐
  │  Optional Remote Adapters  （可整包刪除，core 不受影響）  │
  │  ───────────────────────────────────────────────────  │
  │  mcp_server/  @mcp.tool 包裝層 (222 行)                 │
  │  mcp_server/  leads_tools / decision_tools /           │
  │               engine_c_tools / leads_git  (411 行)      │
  │  cloudflared tunnel · connector 設定 · mobile UX         │
  └───────────────────────┬──────────────────────────────┘
                          │  只准這個方向
                          ▼
  ┌──────────────────────────────────────────────────────┐
  │  Application Boundary  （use case / application service）│
  │  ───────────────────────────────────────────────────  │
  │  intake/    prepare_extraction · apply_action ·        │
  │             finalize · publish                         │
  │             （由 graph_mcp 的 _impl 與 intake.py 抽出）  │
  │  alpha/     research(ticker, as_of) -> AlphaSignal      │
  │  decision/  evaluate · reassess · record_choice         │
  └───────────────────────┬──────────────────────────────┘
                          │
                          ▼
  ┌──────────────────────────────────────────────────────┐
  │  Core Domain                                          │
  │  Engine A(loader/query) · Engine C · alpha/ ·          │
  │  portfolio/ · risk/ · Engine D · identity/             │
  └──────────────────────────────────────────────────────┘
```

**硬規則：**

1. **`Core Domain → mcp_server` 的 import 必須為 0。**
   落成 `tests/test_layer_separation.py::test_core_does_not_import_mcp_server`。
   ⚠ 今天**不是** 0——`engine_b/todo.py`、`query/health_audit.py`、
   `crons/weekly_scan_digest.py`、`scripts/*` 共 5 個消費端
   （`current-architecture.md` §12.2）。
2. **application boundary 的每個 use case 必須能在沒有 MCP 的情況下被本機直接呼叫。**
   今天 `scripts/prepare_research_action.py` 已經在做（呼叫 `_prepare_research_action_impl`），
   只是走的是私有底線函式——把它變成公開 application service 就完成了。
3. **若 MCP 相容性與新核心架構衝突，優先選擇新核心架構。**
   不得為了保留目前 MCP API shape 而增加 domain complexity。

### 14.2 MCP 元件分類

| 元件 | 行 | 分類 | 處置 |
|---|---:|---|---|
| `research_actions.py` | 1,128 | **EXTRACT_FROM_CORE** | 搬到 `intake/actions.py`（application layer）。**domain semantics 全部保留**：bounded mutation／content digest／immutable review packet／explicit approval／idempotent apply／state machine |
| `graph_mcp.py` 的 `_impl` 函式 | 660 | **EXTRACT_FROM_CORE** | 升為公開 application service：`intake.prepare_extraction()`／`intake.apply_action()`／`intake.finalize()` |
| `intake.py` | 608 | **EXTRACT_FROM_CORE** | 搬到 `intake/provenance.py`。**與遠端完全無關**（filesystem 原語） |
| `action_publisher.py` | 528 | **EXTRACT_FROM_CORE** | 搬到 `intake/publish.py`。docstring 已自陳 local-only |
| `graph_mcp.py` 的 `@mcp.tool` 包裝 | 222 | **KEEP_AS_ADAPTER** | 留在 `mcp_server/`，改為只呼叫 application service |
| `leads_tools.py` | 147 | **KEEP_AS_ADAPTER** | |
| `engine_c_tools.py` | 112 | **KEEP_AS_ADAPTER** | |
| `decision_tools.py` | 88 | **KEEP_AS_ADAPTER** | ⚠ `engine_b/todo.py` 目前 import 它 → 必須改指向 `decision_lab.brief` 本身 |
| `leads_git.py` | 64 | **LEGACY_BUT_HARMLESS**（原始理由已失效） | 它存在的理由是「讓 cloud routine 讀 pushed leads」，而 cloud routine 已於 2026-07-26 移回本機。**保留但標記；若手機入口停用即 OBSOLETE** |
| `docs/remote-access-architecture.md`（152 行） | — | **LEGACY_BUT_HARMLESS** | 保留為 adapter 文件，開頭加一句「本檔描述 optional peripheral，不是核心架構」 |
| Cloudflare tunnel／startup vbs／connector 權限設定 | — | **DEFER** | 純 ops，寫在 OPERATIONS |
| `skills/daily-brief` 的 5 處 MCP 提及 | — | **LEGACY_BUT_HARMLESS** | 都已標明「cloud＋MCP 是備援」，措辭正確 |
| MCP quota／expiry／5 MiB／two-call UX／server ID | — | **OBSOLETE（作為 domain rule）** | 見 `current-architecture.md` §12.5：這些是 transport 限制，**不得升格為 domain invariant** |

### 14.3 Research Action 的語意拆分（不得因為 MCP 可忽略就整包刪掉）

| 保留為 core domain | 降級為 transport |
|---|---|
| bounded research mutation（一次核准 ＝ 一個有界的變更集） | MCP server ID |
| provenance（`storage_permission`／`permission_basis`／canonical hash） | remote provider session |
| immutable review packet | cloud-specific apply API |
| content digest ＝ identity（stale／tampered payload 在 graph mutation 前拒絕） | MCP tool exposure |
| explicit approval before graph mutation（**四個 gate 之一**） | mobile two-call workflow |
| idempotent apply ＋ 逐文件 checkpoint ＋ filesystem-first | native approval UX |
| Research Action state machine（INV-2） | 遠端 Git 限制 |

---

## 15. `AGENTS.md` 應如何調整（第一輪不執行，只提出）

> 依 `current-architecture.md` §11 的分類，四份清單。**⚠ lesson learned 一條都不刪。**

### 15.1 應保留在 `AGENTS.md`（真正的 INVARIANT，約 110 行）

工作語言｜現況數字會過期，判準不會｜資本與風控（三個硬擋／共同現金池只有一條／兩個槓桿指標
不得混用／capital authority 逐次人工）｜授權載體唯一＝pq2 編號｜`go` 的語意＝推進到下一個
人工 gate｜系統不給部位尺寸｜Alpha 交付要求（必須有序清單＋明確首選＋各自 disproof＋
點明相關性）｜量測／訊號／脈絡三分｜通知不是 authority｜一手來源優先｜`co:*` 不得由名稱猜｜
報價單位 ≠ 結算幣別｜L4 三分｜同一 working tree 單一 writer｜session memory 不是 authority
**＋新增：五條 authority separation（§12）與六條 hard invariant
（`historical-failure-matrix.md` §2）**

### 15.2 應搬到別處

| 內容 | 搬到 | 為什麼 |
|---|---|---|
| Codex sandbox 權限 16 條 rule 的抄本 | `docs/OPERATIONS.md`（`.codex/rules` 已是權威） | 「清單會腐壞」的現行違規——同一份清單存在兩處 |
| Luna 委派契約 | `skills/luna-reviewer/SKILL.md`（已是權威） | 同上 |
| pq2 的呈現規格（決策行格式／內容密度／措辭層／四段分段軸，約 90 行） | `skills/daily-brief/SKILL.md` | 它是 presentation contract，不是 authority |
| Daily routine 權限與 retry 邊界 | `docs/OPERATIONS.md` | PROCEDURE |
| Daily Brief outbound 通知的操作細節（invariant「通知不是 authority」留下） | `docs/OPERATIONS.md` | PROCEDURE |
| 報告留檔策略 | `docs/OPERATIONS.md` | PROCEDURE |
| 五套證據強度字彙的對照 | `CONCEPTS.md` | 它是詞彙表 |
| 「四引擎」架構表 | 本 refactor 的 ADR（＝本檔 §12） | 它是 CURRENT_ARCHITECTURE |

### 15.3 應因新 Alpha Research architecture 而修改

| 現行文字 | 改成 |
|---|---|
| Engine D「Current-state authority」欄含 **五軸 Confidence、瓶頸排序、NAV 比例呈現** | Engine D 只擁有 **A5**（capital permission／DecisionContext／approval semantics／immutable history／outcome attribution） |
| 「**唯一排序權威**是 `rank_bottlenecks()`，不得另建平行排序」 | 「**結構**排序的唯一權威是 `rank_bottlenecks()`；alpha 排序必須消費它作為 `structural_score`，不得重算結構分或自建第二套結構評分」 |
| 「哪些標的值得看」**四維度** | **五 score**（Structural Scarcity／Value Capture／Earnings Exposure／**Expectation Gap**／Catalyst）；四維度成為前三者的判準細節 |
| 「報告產出：**cohort 是終點**」 | 「**`AlphaSignal` 是研究終點**；cohort 是 decision case 的身分，不是研究的顆粒度」 |
| point-in-time contract（只講 Engine D） | 加一句：**研究與回測同樣受 point-in-time 約束**；`ResearchContext` 是研究側的凍結，**不是 Engine D authority** |
| 管道層 ASCII 圖含 `prepare_research_action`／`apply_research_action` | 改為 application service 名稱；MCP 移到圖外標為 optional adapter |
| 「MCP server 十二工具 surface」 | 標明為 optional peripheral，並指向 §14 |

### 15.4 只是 legacy implementation constraint（不是 invariant，未來可整段移除）

遠端工具無 Git 能力 ＋ leads.json 窄例外（cloud routine 已不存在）｜
MCP action quota（5 MiB／10 文件／50 非終態／100 MiB／30 天）｜
prepare/apply 兩次呼叫 ＋ 一次 native approval 的 UX 描述｜
`GraphSchemaState.version` 由 routine 帳號在每次寫圖前讀取（Neo4j RBAC 細節）｜
Cloudflare tunnel／`httpHostHeader` 改寫／DNS-rebinding 421｜
ChatGPT web-only、connector refresh 等第三方平台限制｜
U7／U12 等已完成 plan 的編號引用

---

## 16. 優先順序（衝突時的裁決順序）

1. Core domain correctness
2. Alpha Research architecture
3. Point-in-time correctness
4. Evidence provenance
5. Engine D decomposition
6. Local developer ergonomics
7. Backtest / portfolio integration
8. Optional remote adapters
9. **Legacy MCP compatibility**

**若 MCP 相容性與新核心架構衝突，優先選擇新核心架構。
MCP 不得成為這次重構的主要設計約束。**

---

## 17. 重構後的文件集合與分工

> **本節定義 Phase 3.9 之後每份文件各自回答什麼問題。**
> ⚠ `docs/ARCHITECTURE.md` **今天不存在**——它在 Phase 3.9 由本檔（`target-architecture.md`）
> 蒸餾而成；`docs/refactor/` 整個目錄在 Phase 8 之後封存到 `docs/archive/`。

### 17.1 五份文件各回答一個互斥的問句

| 檔案 | 回答的問句 | 內容判準 | 何時讀 | 行數（現況 → 目標） |
|---|---|---|---|---|
| **`AGENTS.md`** | **「我可以／不可以做什麼？」** | **會約束行為的規則**：invariant、authority 邊界、四個人工 gate、lesson 的判準句 | **每個 session 完整載入** | 771 → **≤450** |
| **`CONCEPTS.md`** | **「這個詞是什麼意思？」** | **詞彙表**：專案特有語意的名詞。不含規則、不含流程、不含結構 | 遇到不懂的詞 | 190 → ~260 |
| **`docs/ARCHITECTURE.md`** | **「系統長什麼樣、為什麼這樣切？」** | **結構與邊界**：層、authority separation、contract、依賴方向，**以及為什麼**（ADR 理由） | 新增 module／動邊界前 | 0 → ~300（新檔） |
| **`docs/OPERATIONS.md`** | **「這件事怎麼跑？」** | **可執行程序**：命令、環境變數、排程、排錯順序 | 要動手執行時 | 492 → ~670 |
| **`docs/ROADMAP.md`** | **「接下來要做什麼？」** | **active future work ＋ 驗收條件** | 規劃下一步時 | 242（已到位） |

**一句話判準：這句話改變的是我的行為、我的用詞、我的結構、我的按鍵、還是我的排程？**

### 17.2 三組容易混淆的邊界

**① `AGENTS.md` vs `ARCHITECTURE.md`——最容易混的一組。**
分野**已經量過了**，就是 `current-architecture.md` §11 的分類：
**INVARIANT → `AGENTS.md`（約 110 行）｜CURRENT_ARCHITECTURE → `ARCHITECTURE.md`（約 150 行）。**

判別問法：**「換掉 Neo4j、把 Engine D 拆成三個 package 之後，這句話還對嗎？」**
還對 → AGENTS；會跟著變 → ARCHITECTURE。

實例對照：

| 內容 | 去哪 |
|---|---|
| 「Core 不得 import `mcp_server`」 | **AGENTS**（約束行為） |
| 「為什麼依賴方向必須 peripheral → core；`mcp_server/` 79% 是 domain 的實測」 | **ARCHITECTURE**（結構與理由） |
| 「五條 authority separation」 | **AGENTS**（它是憲法） |
| 「今天由 Engine A/B/C/D 四個 package 實現這五條」 | **ARCHITECTURE**（實現方式會變） |
| 「`AlphaSignal` 不得有 position 欄位」 | **AGENTS** |
| 「`AlphaSignal` 的完整欄位定義與 `ordering_key()` 設計」 | **ARCHITECTURE** |

⚠ **允許鏡像，但 AGENTS 那一句必須短且連過去。** 完整論證只寫一份，在 ARCHITECTURE。

**② `CONCEPTS.md` vs `ARCHITECTURE.md`。**
CONCEPTS 定義**名詞本身**，ARCHITECTURE 定義**名詞之間的關係與邊界**。

| 內容 | 去哪 |
|---|---|
| 「`EvidenceRef` 是什麼」 | **CONCEPTS** |
| 「為什麼五套證據強度欄位並列而不壓成一個分數」 | **ARCHITECTURE** |
| 「不得壓成單一分數」 | **AGENTS** |

**③ `AGENTS.md` vs `OPERATIONS.md`。**
> **OPERATIONS 的內容被改壞 → 跑不起來。
> AGENTS 的內容被改壞 → 跑起來了，但做錯事。**

這是最實用的一條分野。「16 條 sandbox rule 的清單」被改壞只會讓排程失敗（OPERATIONS）；
「unattended surface 變更必須做 impact review」被刪掉會讓人在無人值守路徑上加危險命令
（AGENTS）。**現況兩者都在 `AGENTS.md`，清單那份是「清單會腐壞」的現行違規。**

### 17.3 不在這五份裡的東西

| 位置 | 是什麼 | 為什麼不合併 |
|---|---|---|
| `skills/*/SKILL.md`（12 個） | **操作手冊 ＋ 呈現契約**：一個具體工作怎麼做、輸出長什麼樣 | 兩端 harness 自動載入；`description` frontmatter 是權威。pq2 的 90 行呈現規格搬來這裡 |
| `docs/solutions/*/*.md`（9 篇） | **單一事故的事後檢討**（帶 `problem_type` frontmatter 可搜尋） | 它們是**個案**；餵養 AGENTS 的 lesson 判準與 ARCHITECTURE 的設計理由，但不取代兩者 |
| `docs/historical-failure-matrix.md` | **回歸憲法**：36 筆事故 → 六條 invariant → executable protection 對照 | Phase 8 由 `docs/refactor/` 移出成常駐檔。⚠ 它會**逐步溶解**——§2 六條 invariant 進 AGENTS、§3 audit 規格變成 `alpha/audit/` 的 code、§7 golden fixtures 變成測試。**殘留的只有矩陣本身**（一份活的登記表），這正是「lesson 必須 executable」套用在文件自己身上 |
| `schema/graph_schema.md`＋`schema/vocab.json` | **機器可讀的 schema 規格** | 有程式直接消費（`loader/validate.py`）；改它等於改資料格式 |
| `docs/brainstorms/`、`docs/plans/`、`docs/reports/` | 需求推導、交付規格、point-in-time 報告 | 純歷史，`docs/plans/` 已轉純歷史 |
| `CLAUDE.md` | 只有一行 `@AGENTS.md` | 雙代理相容轉接層，不放內容 |

### 17.4 Phase 3.9 的搬移對照（B 類一次做完）

```
AGENTS.md 771 行
  ├─ 110  INVARIANT ─────────────────► 留下
  ├─ 200  LESSON_LEARNED ────────────► 留下（改寫成五欄格式，一條都不刪）
  ├─ 150  CURRENT_ARCHITECTURE ──────► docs/ARCHITECTURE.md（新檔）
  ├─  90  pq2 呈現規格 ──────────────► skills/daily-brief/SKILL.md
  ├─ ~30  Luna 委派契約 ─────────────► skills/luna-reviewer/SKILL.md
  ├─ ~15  五套證據強度字彙 ───────────► CONCEPTS.md（Phase 1 就搬，A 類）
  └─ ~180 PROCEDURE（sandbox rule 抄本／
          daily 權限／報告留檔／通知細節）► docs/OPERATIONS.md
  ＋新增   五條 authority separation
          六條 hard invariant ────────► AGENTS.md
```

**驗收（Phase 3.9 exit criteria）：**
- `AGENTS.md` **771 → ≤450 行**，且 INVARIANT **一條未刪**
- **16 條 lesson 全部保留**，各自標明 implementation 可不可改
- `grep` 不到與 `.codex/rules`／`skills/*` 重複的清單（消除「清單會腐壞」的現行違規）
- 五份文件的任一句話，都能明確歸到 §17.1 的一個問句底下——**歸不到就是它不該存在**
