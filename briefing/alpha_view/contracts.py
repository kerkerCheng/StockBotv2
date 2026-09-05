"""Alpha Investment View——**單一公司的 canonical read model**（型別與字彙）。

## 這一層是什麼、不是什麼

它是 **composition／read model**，不是新的 authority：把 Engine A（`GraphResearchProvider`）、
Engine C（`EngineCFundamentalsProvider`）、Alpha（`AlphaSignal`／`ResearchContext`）、
Engine D 的公開 cohort 事實與 thesis lifecycle **選取、正規化、語意標註、組裝、序列化**成
一份 presentation-independent 的結構。Daily Brief、CLI 與未來 Web／API 都消費同一份。

- **不算任何業務數字**：Q1–Q5、瓶頸排序、估值 proxy、催化劑狀態全部由既有 authority 算好，
  這裡只讀。
- **不含部位**：`AlphaSignal != Position`；持股、NAV、尺寸住 `portfolio/`／Engine D，
  本 view 一個欄位都不帶（`test_view_contains_no_position_fields` 守著）。
- **不是 `AlphaSignal` 的擴充**：`alpha/contracts.py` 仍是 research contract，零外部相依；
  本模組住組裝層（`briefing/`），因為它必須同時看得到 Engine C／Engine D／thesis。

## 兩個正交的語意軸（讓不同種類的知識在文字裡不再「看起來同樣可信」）

每個 `Datum`／`SectionMeta` 都帶兩個封閉字彙：

| 軸 | 回答什麼 | 值 |
|---|---|---|
| `status` | **這格有沒有東西、為什麼沒有** | `available`／`partial`／`stale`／`missing`／`insufficient_evidence`／`not_modeled`／`not_applicable` |
| `basis` | **這格的東西是哪一種知識** | `deterministic`／`observation`／`heuristic_proxy`／`session_judgment`／`narrative`／`structural_inference`／`none` |

- `missing`＝系統有這個能力、這檔沒資料；`not_modeled`＝系統**還沒有這個能力**
  （expected return、downside、entry logic…）。兩者下一步完全不同，所以不得共用一個值。
  ⚠ 2026-09-05 起 internal fundamentals／earnings bridge／numeric expectation gap **有能力了**
  （`alpha/fundamental`）：沒有假設或沒有基期觀測的公司是 `missing`，不再是 `not_modeled`。
- `heuristic_proxy` 是 `trailing_pe/forward_pe − 1` 這類粗略代理；它**不是** reverse DCF，
  也不得被讀成 modeled。
- `session_judgment` 是 session／LLM 的判斷（Q2–Q5、thesis、variant view）；
  `narrative` 是散文（bull／base／bear、Decision Store 的 catalyst／disproof 原文）。
- `structural_inference` 是圖上多跳推論（`CausalPath`／`CompanyImpact`）——它是
  **structural causal model**，不是 financial causal model；後者今天 `not_modeled`。

## Missing != Zero 在型別層強制

`Datum.__post_init__`：`status` 屬於「沒有值」那組時 `value` 必須是 `None`；反過來
`status="available"` 時 `value` 不得是 `None`。少了這一條，「internal EPS 未建模」與
「EPS＝0」在序列化後同形。
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Mapping

SCHEMA_VERSION = "alpha-investment-view/v1"

# ---------------------------------------------------------------------------
# 0. 封閉字彙（contract——刻意有限，打開它是 bug）
# ---------------------------------------------------------------------------

SectionStatus = Literal[
    "available", "partial", "stale", "missing",
    "insufficient_evidence", "not_modeled", "not_applicable",
]
SECTION_STATUSES: frozenset[str] = frozenset(SectionStatus.__args__)  # type: ignore[attr-defined]

#: 這些狀態代表「沒有值」——`Datum.value` 必須是 `None`。
VALUELESS_STATUSES: frozenset[str] = frozenset(
    {"missing", "insufficient_evidence", "not_modeled", "not_applicable"}
)

Basis = Literal[
    "deterministic",          # 由既有規則對已核准事實／量測算出（Q1、catalyst state、比值）
    "observation",            # 直接讀自 authority 的量測／已入圖事實（Engine C 快照、圖上的邊）
    "heuristic_proxy",        # 粗略代理（trailing/forward PE 隱含成長）
    "session_judgment",       # session／LLM 判斷（Q2–Q5、thesis、variant view）
    "narrative",              # 散文（bull/base/bear、Decision Store 的 catalyst／disproof 原文）
    "structural_inference",   # 圖上多跳推論（CausalPath／CompanyImpact）
    "none",                   # 沒有值，也就沒有 basis
]
BASES: frozenset[str] = frozenset(Basis.__args__)  # type: ignore[attr-defined]

#: 面向使用者的 basis 標籤（繁中）。renderer 只查表，不重新分類。
BASIS_LABEL: Mapping[str, str] = {
    "deterministic": "確定性規則",
    "observation": "觀測值",
    "heuristic_proxy": "粗略代理",
    "session_judgment": "session 判斷",
    "narrative": "散文",
    "structural_inference": "結構推論",
    "none": "—",
}
STATUS_LABEL: Mapping[str, str] = {
    "available": "有",
    "partial": "部分",
    "stale": "過期",
    "missing": "缺料",
    "insufficient_evidence": "證據不足",
    "not_modeled": "尚未建模",
    "not_applicable": "不適用",
}

#: capability 等級的具名常數——section 用它宣告「我做到哪裡」，消費端據此不得 overclaim。
CAP_STRUCTURAL_CAUSAL = "structural_causal_model"
CAP_FINANCIAL_CAUSAL = "financial_causal_model"
CAP_NARRATIVE_SCENARIOS = "narrative"
CAP_QUANTITATIVE_SCENARIOS = "quantitative_scenario_model"
CAP_STRUCTURED_DISPROOF = "structured_conditions_with_expiry_watch"
CAP_AUTOMATIC_INVALIDATION = "automatic_invalidation_engine"
CAP_CATALYST_UNLINKED = "structured_dates_without_repricing_link"
#: Phase 2：內部估計 vs **同期、同口徑**共識的數值 gap（不含估值、不含價格隱含側）。
CAP_NUMERIC_EXPECTATION_GAP = "numeric_internal_vs_consensus"


class ViewContractViolation(ValueError):
    """read model 的型別不變式被違反（例如 missing 卻帶了值）。"""


def _check_vocab(value: str, allowed: frozenset[str], label: str) -> None:
    if value not in allowed:
        raise ViewContractViolation(f"{label} 未登記：{value!r}；已知 {sorted(allowed)}")


# ---------------------------------------------------------------------------
# 1. Datum／SectionMeta——每一格都答得出「值／誰／怎麼來／多新／哪種知識」
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Datum:
    """一格可稽核的資料。

    - `value`：值；沒有就是 `None`（**不是 0、不是空字串、不是空 dict**）。
    - `authority`：誰擁有這個真相（邏輯 URI，如 `engine_c://financial_snapshots`、
      `engine_a://rank_bottlenecks`、`alpha://session_assessor/v1`、
      `decision_lab://coverage_assessments`）。**不得是檔案路徑**。
    - `method`：怎麼得到（規則版本、公式、或「人工判讀」）。
    - `unit`：單位語意。⚠ 報價單位 ≠ 結算幣別，`quote_unit`／`reporting_currency`／`ratio`
      要寫清楚，跨標的比較前不得假設同尺度。
    - `evidence_refs`：`EvidenceRef.ref` 的 key，指向 `EvidenceSection.index`。
    - `dependencies`：模型輸出的依賴（假設 id、觀測 ref、輸入知識種類、期間、口徑）。
      **`basis=deterministic` 只說算法確定；輸入是不是判斷看這裡的 `input_dependency`。**
    """

    key: str
    label: str
    value: Any = None
    status: str = "missing"
    basis: str = "none"
    authority: str | None = None
    method: str | None = None
    unit: str | None = None
    as_of: date | None = None
    reason: str | None = None
    evidence_refs: tuple[str, ...] = ()
    dependencies: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.key or not self.label:
            raise ViewContractViolation("Datum.key／label 必須是非空字串")
        _check_vocab(self.status, SECTION_STATUSES, "Datum.status")
        _check_vocab(self.basis, BASES, "Datum.basis")
        if self.status in VALUELESS_STATUSES and self.value is not None:
            raise ViewContractViolation(
                f"Datum[{self.key}] status={self.status} 卻帶著值 {self.value!r}——"
                "缺席與 0 不得同形（missing != zero）"
            )
        if self.status == "available" and self.value is None:
            raise ViewContractViolation(
                f"Datum[{self.key}] status=available 但 value 是 None——沒有值就要說沒有"
            )
        if self.status in VALUELESS_STATUSES and self.basis != "none":
            raise ViewContractViolation(
                f"Datum[{self.key}] 沒有值（{self.status}）就沒有 basis，不得標 {self.basis!r}"
            )
        if self.status not in VALUELESS_STATUSES and self.basis == "none":
            raise ViewContractViolation(
                f"Datum[{self.key}] 有值（{self.status}）必須說出它是哪一種知識（basis）"
            )
        if self.authority and ("\\" in self.authority or "/library/" in self.authority
                               or self.authority.startswith(("C:", "/"))):
            raise ViewContractViolation(
                f"Datum[{self.key}].authority 看起來是檔案路徑：{self.authority!r}；"
                "請用邏輯 URI，private path 不得進 read model"
            )

    @property
    def is_known(self) -> bool:
        return self.status not in VALUELESS_STATUSES


@dataclass(frozen=True, slots=True)
class SectionMeta:
    """一個 section 的整體語意標註。`capability` 宣告做到哪一級（見 `CAP_*`）。"""

    status: str
    basis: str
    authority: str | None = None
    capability: str | None = None
    reason: str | None = None
    as_of: date | None = None
    freshness: str | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_vocab(self.status, SECTION_STATUSES, "SectionMeta.status")
        _check_vocab(self.basis, BASES, "SectionMeta.basis")
        if self.status in VALUELESS_STATUSES and self.basis != "none":
            raise ViewContractViolation(
                f"SectionMeta status={self.status} 沒有內容，basis 必須是 none"
            )
        if self.freshness is not None and self.freshness not in (
            "available", "stale", "missing", "quarantined"
        ):
            raise ViewContractViolation(f"SectionMeta.freshness 未登記：{self.freshness!r}")


def not_modeled(key: str, label: str, reason: str) -> Datum:
    """「系統還沒有這個能力」的標準格。與 `missing`（有能力、沒資料）刻意分開。"""
    return Datum(key=key, label=label, value=None, status="not_modeled",
                 basis="none", reason=reason)


def missing(key: str, label: str, reason: str, *, authority: str | None = None) -> Datum:
    return Datum(key=key, label=label, value=None, status="missing", basis="none",
                 authority=authority, reason=reason)


# ---------------------------------------------------------------------------
# 2. 各 section 的內容型別
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SignalCompleteness:
    """`AlphaSignal` 的完整度與判斷新鮮度。"""

    has_signal: bool
    is_incomplete: bool | None = None
    known_axes: tuple[str, ...] = ()
    weakest_axis: str | None = None
    judged_at: str | None = None
    judged_context_digest: str | None = None
    current_context_digest: str | None = None
    context_matches: bool | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class LifecycleFacts:
    """Engine D 與 thesis lifecycle 的**公開**事實（不含任何部位／NAV／尺寸）。

    ⚠ 刻意沒有 `attention`（MONITOR／REVIEW）：它由 `decision_lab today` 的 brief 計算，
    本 view 不重算也不留一個永遠是 None 的欄位假裝有。
    """

    research_status: str | None = None      # READY／…（Engine D coverage）
    lifecycle_status: str | None = None     # Engine D probe lifecycle epoch status
    review_due_at: str | None = None
    decision_effective_at: str | None = None
    legacy_weakest_axis: str | None = None  # 舊五軸的最弱軸（Engine D）
    legacy_axis_levels: Mapping[str, str] | None = None  # 舊五軸各軸生效等級（Engine D）
    cohort_count: int | None = None         # 同公司有幾個 cohort；view 只呈現其中一個
    cohort_selection_rule: str | None = None
    decision_facts_as_of: str | None = None  # Engine D 事實的 as-of 截止（None＝當前）
    thesis_lifecycle_status: str | None = None   # thesis/lifecycle.json 的 status
    thesis_next_check: date | None = None
    thesis_next_check_source: str | None = None  # cadence／catalyst／unscheduled
    authority: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class IdentitySection:
    ticker: str
    company_id: str | None
    company_label: str
    market_currency: str | None
    market_quote_unit: str | None
    execution_venue: str | None
    as_of: date | None
    point_in_time_mode: str                 # "current"／"as_of"
    generated_on: date
    research_context_digest: str | None
    signal: SignalCompleteness
    data_completeness: tuple[Datum, ...]
    lifecycle: LifecycleFacts
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VariantViewSection:
    meta: SectionMeta
    thesis: Datum
    variant_view: Datum
    direction: Datum
    confidence: Datum
    expected_horizon: Datum
    #: 五個維度（Q1–Q5）的分數格。Q1 是確定性規則、Q2–Q5 是 session 判斷；
    #: 同一個 Datum 物件也出現在各自的 section（structural／expectation_gap／catalysts），
    #: 這裡是「研究判斷長什麼樣」的總表，不是第二份計算。
    scores: tuple[Datum, ...]
    risks: tuple[str, ...]
    decision_store_variant_perception: Datum


@dataclass(frozen=True, slots=True)
class StructuralEdgeItem:
    relation: str
    target: str
    substitutability: int | None
    sole_source: bool | None
    qualification_status: str | None
    demand_anchor: str | None
    demand_hops: int | None
    evidence_class: str | None
    purpose: str = "actionable"             # actionable／structural_only_not_actionable


@dataclass(frozen=True, slots=True)
class PathItem:
    nodes: tuple[str, ...]
    relations: tuple[str, ...]
    hops: int
    confidence: str                          # ImpactConfidence 名稱（最弱一段）
    weakest_link: str | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExposureItem:
    direction: str
    counterparty: str
    relation: str
    substitutability: int | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StructuralThesisSection:
    meta: SectionMeta
    structural_score: Datum                  # Q1
    scarcity_inputs: tuple[Datum, ...]
    ranking: tuple[Datum, ...]
    edges: tuple[StructuralEdgeItem, ...]
    supply_exposure: tuple[ExposureItem, ...]
    substitution_paths: tuple[PathItem, ...]
    evidence_quality: Datum
    coverage_caveats: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ImpactItem:
    event_id: str | None
    event_kind: str | None
    event_direction: str | None
    subject: str | None
    observed_at: date | None
    impact_direction: str
    magnitude: str
    time_horizon: str
    confidence: str
    path: PathItem
    rationale: str


@dataclass(frozen=True, slots=True)
class EventItem:
    event_id: str
    kind: str
    subject: str
    direction: str
    observed_at: date
    description: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CausalPathSection:
    meta: SectionMeta                        # capability 必為 CAP_STRUCTURAL_CAUSAL
    dependency_paths: tuple[PathItem, ...]
    substitution_paths: tuple[PathItem, ...]
    impacts_on_company: tuple[ImpactItem, ...]
    structural_events: tuple[EventItem, ...]
    financial_causal_model: Datum            # 恆 not_modeled，直到 revenue／margin／EPS bridge 存在


@dataclass(frozen=True, slots=True)
class FundamentalsSection:
    meta: SectionMeta
    items: tuple[Datum, ...]
    segment_revenue_share: Datum
    checklist: tuple[Datum, ...]


@dataclass(frozen=True, slots=True)
class ConsensusSection:
    meta: SectionMeta                        # 覆蓋只到 next-FY 營收＋forward PE ⇒ partial
    items: tuple[Datum, ...]
    coverage_note: str
    #: 會計年度別的 EPS／營收共識（Engine C `consensus_estimates`，身分是 fiscal_period_end）。
    fiscal_items: tuple[Datum, ...] = ()


@dataclass(frozen=True, slots=True)
class PriceImpliedSection:
    meta: SectionMeta
    items: tuple[Datum, ...]
    reverse_dcf: Datum                       # not_modeled


@dataclass(frozen=True, slots=True)
class InternalFundamentalsSection:
    meta: SectionMeta                        # available／partial／missing（alpha/fundamental）
    items: tuple[Datum, ...]
    plug_in_note: str
    period: str | None = None                # 目標會計期間標籤（FY2027）
    period_end: date | None = None           # 目標會計期間身分（結束日）
    base_period_end: date | None = None      # 基期會計年度結束日
    accounting_basis: str | None = None      # gaap／non_gaap／not_applicable


@dataclass(frozen=True, slots=True)
class EarningsBridgeSection:
    meta: SectionMeta
    steps: tuple[Datum, ...]                 # 基期觀測 → 假設 → 每一步 derived（含公式）
    inputs_available: tuple[Datum, ...]      # 今天已存在、可接進 bridge 的原料
    assumptions: tuple[Datum, ...] = ()      # 生效的 OperatingAssumption，每條各自標知識種類
    sensitivities: tuple[Datum, ...] = ()    # 每條假設動一格，輸出動多少（確定性微擾）
    selection: "EvidenceSelectionCounts | None" = None   # 假設的 as-of／supersede／證據解析計數
    period: str | None = None


@dataclass(frozen=True, slots=True)
class ExpectationGapSection:
    meta: SectionMeta
    session_judgment: Datum                  # Q4（ordinal，session 判斷）
    proxies: tuple[Datum, ...]               # 估計修正 vs 股價變動等 deterministic 原料
    internal_vs_consensus: Datum             # 數值 gap 總表（只在 apples-to-apples 時有值）
    internal_vs_price_implied: Datum         # not_modeled（估值側是下一階段）
    numeric_comparisons: tuple[Datum, ...] = ()   # 逐指標：revenue／eps／operating_margin


@dataclass(frozen=True, slots=True)
class CatalystItem:
    kind: str
    description: str
    expected_at: date | None
    date_confidence: str
    basis: str                               # session_judgment
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CheckpointItem:
    date: date
    what: str
    decides: str
    date_confidence: str                     # confirmed／estimated
    source: str                              # thesis/lifecycle.json／thesis/catalyst_calendar.json


@dataclass(frozen=True, slots=True)
class CatalystSection:
    meta: SectionMeta
    catalyst_score: Datum                    # Q5
    structured: tuple[CatalystItem, ...]
    checkpoints: tuple[CheckpointItem, ...]
    narrative: Datum                         # Engine D coverage_assessments.catalyst 原文
    watch_state: Datum                       # shared.catalyst_state.assess_entry 的 state
    expiry: Datum
    problems: tuple[str, ...]
    quantitative_link: Datum                 # not_modeled：催化劑 → 盈餘／重定價未量化


@dataclass(frozen=True, slots=True)
class DisproofItem:
    condition: str
    check_frequency: str
    action_within_48h: str
    basis: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FalsificationSection:
    meta: SectionMeta
    conditions: tuple[DisproofItem, ...]
    narrative_disproof: Datum                # Engine D coverage_assessments.disproof 原文
    thesis_status: Datum
    expiry_watch: Datum
    automatic_invalidation: Datum            # not_modeled


@dataclass(frozen=True, slots=True)
class ScenarioSection:
    meta: SectionMeta
    scenario_type: str                       # CAP_NARRATIVE_SCENARIOS
    bull: Datum
    base: Datum
    bear: Datum
    probabilities: Datum                     # not_modeled
    target_valuation: Datum                  # not_modeled


@dataclass(frozen=True, slots=True)
class NotModeledSection:
    """expected_return／downside／entry_logic 共用的形狀：全 not_modeled，附「不是什麼」。"""

    meta: SectionMeta
    items: tuple[Datum, ...]
    not_to_be_confused_with: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    ref: str
    kind: str
    source_doc_id: str | None
    origin_entity: str | None
    url: str | None
    quote: str | None
    published_at: date | None
    retrieved_at: date | None
    recorded_at: datetime | None
    evidence_tier: int | None
    evidence_class: str | None
    confidence: float | None
    corroborating_origins: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSelectionCounts:
    input_count: int
    accepted_count: int
    filtered_count: int
    reasons: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class EvidenceSection:
    meta: SectionMeta
    index: tuple[EvidenceItem, ...]
    selection: EvidenceSelectionCounts
    quality: Datum


@dataclass(frozen=True, slots=True)
class FreshnessItem:
    source: str
    status: str                              # available／stale／missing／quarantined
    as_of: date | None
    age_days: float | None
    reason: str | None


# ---------------------------------------------------------------------------
# 3. 整份 view
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AlphaInvestmentView:
    """StockBot 對**一家公司**目前投資理解的 canonical 表示。

    每個 section 都自帶 `meta.status`／`meta.basis`／`meta.capability`，所以消費端不必
    讀散文就知道「這一段是模型、proxy、session 判斷、還是尚未建模」。
    """

    schema_version: str
    identity: IdentitySection
    variant_view: VariantViewSection
    structural_thesis: StructuralThesisSection
    causal_paths: CausalPathSection
    fundamentals: FundamentalsSection
    consensus: ConsensusSection
    price_implied_expectations: PriceImpliedSection
    internal_fundamentals: InternalFundamentalsSection
    earnings_bridge: EarningsBridgeSection
    expectation_gap: ExpectationGapSection
    catalysts: CatalystSection
    falsification: FalsificationSection
    scenarios: ScenarioSection
    expected_return: NotModeledSection
    downside: NotModeledSection
    entry_logic: NotModeledSection
    evidence: EvidenceSection
    freshness: tuple[FreshnessItem, ...]
    warnings: tuple[str, ...] = ()

    #: 有 `meta` 的 section 名稱，`capability_map()` 依此列舉。
    SECTIONS_WITH_META = (
        "variant_view", "structural_thesis", "causal_paths", "fundamentals", "consensus",
        "price_implied_expectations", "internal_fundamentals", "earnings_bridge",
        "expectation_gap", "catalysts", "falsification", "scenarios", "expected_return",
        "downside", "entry_logic", "evidence",
    )

    def capability_map(self) -> dict[str, dict[str, str | None]]:
        """一眼看出「知道什麼／還不知道什麼」：section → status／basis／capability。"""
        out: dict[str, dict[str, str | None]] = {}
        for name in self.SECTIONS_WITH_META:
            meta: SectionMeta = getattr(self, name).meta
            out[name] = {"status": meta.status, "basis": meta.basis,
                         "capability": meta.capability}
        return out

    def to_dict(self) -> dict[str, Any]:
        """JSON-able dict。`None` 保留為 `null`，日期轉 ISO，Enum 轉 value。"""
        payload = _jsonable(self)
        payload["capability_map"] = self.capability_map()
        return payload


def _jsonable(obj: Any) -> Any:
    """遞迴轉成可 JSON 序列化的結構。⚠ `None` 永遠保留——它是 read model 的一等值。"""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _jsonable(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, Enum):
        return obj.value if not isinstance(obj.value, int) else obj.name.lower()
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Mapping):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(_jsonable(v) for v in obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


__all__ = [
    "AlphaInvestmentView", "BASES", "BASIS_LABEL", "Basis", "CAP_AUTOMATIC_INVALIDATION",
    "CAP_CATALYST_UNLINKED", "CAP_FINANCIAL_CAUSAL", "CAP_NARRATIVE_SCENARIOS",
    "CAP_NUMERIC_EXPECTATION_GAP",
    "CAP_QUANTITATIVE_SCENARIOS", "CAP_STRUCTURAL_CAUSAL", "CAP_STRUCTURED_DISPROOF",
    "CatalystItem", "CatalystSection", "CausalPathSection", "CheckpointItem",
    "ConsensusSection", "Datum", "DisproofItem", "EarningsBridgeSection", "EventItem",
    "EvidenceItem", "EvidenceSection", "EvidenceSelectionCounts", "ExpectationGapSection",
    "ExposureItem", "FalsificationSection", "FreshnessItem", "FundamentalsSection",
    "IdentitySection", "ImpactItem", "InternalFundamentalsSection", "LifecycleFacts",
    "NotModeledSection", "PathItem", "PriceImpliedSection", "SCHEMA_VERSION",
    "SECTION_STATUSES", "STATUS_LABEL", "ScenarioSection", "SectionMeta", "SectionStatus",
    "SignalCompleteness", "StructuralEdgeItem", "StructuralThesisSection",
    "VALUELESS_STATUSES", "VariantViewSection", "ViewContractViolation", "missing",
    "not_modeled",
]
