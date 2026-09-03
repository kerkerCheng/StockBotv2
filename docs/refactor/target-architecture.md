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

> **⚠ 這是一個刻意的取捨，一行可改。** prompt §18 的範例是
> `python -m stockbot.alpha research ASML`。改成 `stockbot/` 需要搬動全部 15 個
> top-level package，屬 §20 明令禁止的「為了整理目錄做沒有價值的大 rename」，
> 而且會改變 `.codex/rules/stockbot-automations.rules` 裡 **16 條 exact command prefix**
> 的字串——那會**靜默打斷 daily 排程**。因此 MVP 命令定為：
> ```
> python -m alpha research ASML --as-of 2026-06-30
> ```
> 若使用者仍要 `stockbot.alpha`，Phase 1 加一個 `stockbot/` shim package 即可，
> 但 daily 的 16 條 rule 必須同時走 sandbox impact review。

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

    # ── 綜合
    value: float                        # -1..1，方向與強度。**不是部位大小**
    confidence: float                   # 0..1

    # ── 五個成分（prompt §6 的五問，各自可 explain）
    structural_score: float             # Q1 Structural Scarcity
    value_capture_score: float          # Q2 Economic Value Capture
    earnings_exposure_score: float      # Q3 Earnings / FCF Exposure
    expectation_gap_score: float        # Q4 Expectation Gap
    catalyst_score: float               # Q5 Catalyst

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
4. **`value` 不是由五個分數固定加權而來。** 加權是未經量測的機制（L14）。
   Phase 2 先用最保守的形式：**`value` 由 deterministic 規則從五個分數導出，
   規則寫成一個具名的 `CompositionRule` 並版本化**，且第一版就要能回答
   「換掉這條規則，現有 N 筆 signal 有幾筆排序會變」。
5. **`expectation_gap_score` 不得由低本益比直接得出**（§20 明令）。
   它必須是 `internal_implied_fundamentals` 與 `market_implied_fundamentals` 的**差**。

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
