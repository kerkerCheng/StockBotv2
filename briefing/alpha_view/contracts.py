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
  （probability-weighted expected return、total return、downside、entry logic…）。兩者下一步完全不同，所以不得共用一個值。
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

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Mapping

from alpha.absence import ABSENCE_KINDS, check_absence_kind, default_absence_kind

SCHEMA_VERSION = "alpha-investment-view/v1"

# ---------------------------------------------------------------------------
# 0. 封閉字彙（contract——刻意有限，打開它是 bug）
# ---------------------------------------------------------------------------

SectionStatus = Literal[
    "available", "partial", "stale", "missing",
    "insufficient_evidence", "not_modeled", "not_applicable",
    "review_required", "invalidated",
]
SECTION_STATUSES: frozenset[str] = frozenset(SectionStatus.__args__)  # type: ignore[attr-defined]

#: Step 0.5（2026-09-06）加的兩個 status——它們**有值**（舊判斷仍保留為歷史資訊），但不得再當
#: current：`review_required`＝依據發生 material change，要人重看；`invalidated`＝已知前提不成立。
#: `stale` 從此**只**表示時間／排程到期（Engine C 快照超過 14 天、核查週期到了），不再兼任
#: 「context digest 變了」——那正是 Step 0 抓到的 over-invalidation（L12：一個表示兩種語意）。
REFRESH_STATUSES: frozenset[str] = frozenset({"available", "stale", "review_required", "invalidated"})

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
    "investor_policy",        # 投資人自己宣告的政策（Step 3 的要求報酬判準）——不是觀測、不是研究判斷
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
    "investor_policy": "投資人政策",
    "none": "—",
}
STATUS_LABEL: Mapping[str, str] = {
    "available": "有",
    "partial": "部分",
    "stale": "過期（排程）",
    "missing": "缺料",
    "insufficient_evidence": "證據不足",
    "not_modeled": "尚未建模",
    "not_applicable": "不適用",
    "review_required": "需複查",
    "invalidated": "已失效",
}

#: capability 等級的具名常數——section 用它宣告「我做到哪裡」，消費端據此不得 overclaim。
CAP_STRUCTURAL_CAUSAL = "structural_causal_model"
CAP_NARRATIVE_SCENARIOS = "narrative"
CAP_QUANTITATIVE_SCENARIOS = "quantitative_scenario_model"
CAP_STRUCTURED_DISPROOF = "structured_conditions_with_expiry_watch"
CAP_AUTOMATIC_INVALIDATION = "automatic_invalidation_engine"
CAP_CATALYST_UNLINKED = "structured_dates_without_repricing_link"
#: Step 0.5：dependency impact（什麼變了 → 影響誰 → 哪種 state）。它評估 machine-readable 條件與
#: 已分類的變化，**不解析自然語言 disproof、不改 thesis、不自動呼叫 LLM**——所以不是
#: `CAP_AUTOMATIC_INVALIDATION`（那個名字保留給「會自己判定條件並改狀態」的東西，今天不存在）。
CAP_DEPENDENCY_IMPACT = "dependency_impact_v1"
# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：七個 capability 常數退役**——
# `CAP_FINANCIAL_CAUSAL`（FY+1 因果橋）、`CAP_NUMERIC_EXPECTATION_GAP`（內部 vs 共識數值 gap）、
# `CAP_DETERMINISTIC_FAIR_VALUE`（Step 1 估值）、`CAP_BASE_CASE_IMPLIED_RETURN`（Step 2 隱含報酬）、
# `CAP_ANALYTICAL_ENTRY_THRESHOLD`（Step 3 進場門檻，F 組）、`CAP_VARIANT_PAYOFF`／`CAP_DOWNSIDE_OVERLAY`
# （賭注四價，E 組）。宣告它們的 section 都不在了；沒有 producer 的字彙不留（L16）。
#: 2026-09-15：投資人短評——七格前因後果，文字由 session 寫（append-only ledger）、數字由 authority 填。
CAP_INVESTOR_BRIEF = "investor_brief_v1"
#: 2026-09-15：論證層——六段分析師報告體。算術與圖的敘述由封閉句型組；判斷的長文照抄 session 寫的。
CAP_ARGUMENT = "argument_layer_v1"
#: 2026-09-18（D2）：歸零旗標——四盞紅黃綠燈（現金跑道／負債／稀釋／going concern）。
#: **量測不是訊號**：不參與排序、不決定尺寸。判色規則與「為什麼這盞不亮」住 `alpha/wipeout.py`。
CAP_WIPEOUT_FLAGS = "wipeout_flags_v1"


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
    #: **Step 5：「沒有值」是哪一種沒有**（`alpha/absence.py` 的封閉字彙）。
    #: 由知道自己走了哪個分支的那一段程式明示；沒明示就由 `status` 查表得到預設
    #: （`effective_absence_kind`）。消費端一律不得 parse `reason` 去猜（L16）。
    absence_kind: str | None = None

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
        if self.absence_kind is not None:
            check_absence_kind(self.absence_kind, f"Datum[{self.key}].absence_kind")
            if self.status not in VALUELESS_STATUSES:
                raise ViewContractViolation(
                    f"Datum[{self.key}] 有值（{self.status}）卻帶缺席語意 {self.absence_kind!r}——"
                    "absence_kind 只描述「為什麼沒有」")
        if self.authority and ("\\" in self.authority or "/library/" in self.authority
                               or self.authority.startswith(("C:", "/"))):
            raise ViewContractViolation(
                f"Datum[{self.key}].authority 看起來是檔案路徑：{self.authority!r}；"
                "請用邏輯 URI，private path 不得進 read model"
            )

    @property
    def is_known(self) -> bool:
        return self.status not in VALUELESS_STATUSES

    @property
    def effective_absence_kind(self) -> str | None:
        """這一格「為什麼沒有」。有值 → `None`；明示優先；沒明示就查 `status` 的預設表。"""
        if self.is_known:
            return None
        return self.absence_kind or default_absence_kind(self.status)


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
    #: Step 5：整個 section 缺內容時**是哪一種缺席**（`alpha/absence.py`）。與 `Datum` 同一套字彙。
    absence_kind: str | None = None
    #: 2026-09-13：**這一格的缺席已經被一筆 append-only `Abstention` 宣告過**（帶 `ab_*` id）。
    #: 與 `absence_kind` 正交——`absence_kind` 說「為什麼沒有值」（可能是上游的原因），
    #: 它說「作者已經決定這一格不必補」。實測 POET：`absence_kind=upstream_unavailable`
    #: 而 ledger 裡有 live 的 `ab_42838d2eec25b735`，於是畫面在叫人去做研究已判定不值得做的事。
    settled_by: str | None = None

    @property
    def effective_absence_kind(self) -> str | None:
        if self.status not in VALUELESS_STATUSES:
            return None
        return self.absence_kind or default_absence_kind(self.status)

    def __post_init__(self) -> None:
        _check_vocab(self.status, SECTION_STATUSES, "SectionMeta.status")
        _check_vocab(self.basis, BASES, "SectionMeta.basis")
        if self.absence_kind is not None:
            check_absence_kind(self.absence_kind, "SectionMeta.absence_kind")
            if self.status not in VALUELESS_STATUSES:
                raise ViewContractViolation(
                    f"SectionMeta 有內容（{self.status}）卻帶缺席語意 {self.absence_kind!r}")
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


def missing(key: str, label: str, reason: str, *, authority: str | None = None,
            absence_kind: str | None = None) -> Datum:
    """「有能力、沒資料」的標準格。`absence_kind` 由知道自己走了哪個分支的呼叫端明示；
    不給就是 `not_yet_recorded`（`alpha/absence.py` 的預設表）。"""
    return Datum(key=key, label=label, value=None, status="missing", basis="none",
                 authority=authority, reason=reason, absence_kind=absence_kind)


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
    #: thesis 層級的 refresh state（alpha.refresh）；None＝無判斷。它與 `context_matches` 分開：
    #: 後者是「判斷對的是不是這份 context」的事實，前者是「變化動不動搖這份判斷」的結論。
    refresh_state: str | None = None


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
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`financial_causal_model` 那一格隨 FY+1 因果橋退役。


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


# ⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`PriceImpliedSection`（PE 比值 proxy）、
# `InternalFundamentalsSection`（我們的 FY+1 預測）、`EarningsBridgeSection`（因果橋）三個 section 退役。**
# 它們同出於 `alpha/fundamental` 的模型；模型已刪。Engine C 的共識資料留在 `ConsensusSection.fiscal_items`。


@dataclass(frozen=True, slots=True)
class ExpectationGapSection:
    """預期差：**session 判斷（Q4）＋ 共識時序的量測**，沒有任何數值 gap。

    ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`proxies`（PE 比值 proxy、估計修正 vs 股價）、
    `internal_vs_consensus`／`numeric_comparisons`（內部 vs 共識數值 gap）、`internal_vs_price_implied`、
    `opinion_stance`（我們有沒有形成觀點）、`reverse_bridge`（D 組）、`multiple_derivation`（目標倍數來源）
    七個欄位整組退役——它們全部讀 FY+1 因果橋或估值鏈。留下的兩格是量測：共識自判斷日以來移了多少、
    共識時序本身。**量測不是訊號**：不排序、不決定尺寸。
    """

    meta: SectionMeta
    session_judgment: Datum                  # Q4（ordinal，session 判斷）
    #: V2（2026-09-15）：共識自判斷日以來的移動＋共識時序本身。2026-09-23 起沒有內部值，
    #: 所以 `closed_fraction` 恆 None（不是 0）——量到的只有共識自己的移動。
    gap_closure: Datum | None = None
    consensus_series: Datum | None = None


@dataclass(frozen=True, slots=True)
class CatalystItem:
    kind: str
    description: str
    expected_at: date | None
    date_confidence: str
    basis: str                               # session_judgment
    evidence_refs: tuple[str, ...]
    #: V1（2026-09-15）：裁決哪幾條假設；`state`＝pending（未到）／due（到期、還沒重看）／resolved（到期後
    #: 所有被指名的假設都有更新的紀錄）／unlinked（沒指名）。**機械計數**：只看日期與 ledger 的 created_at。
    resolves: tuple[str, ...] = ()
    state: str = "unlinked"
    unresolved_ids: tuple[str, ...] = ()


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
    #: 催化劑那一格**為什麼沒進熟成度**的機械計數（2026-09-19，七缺陷之 1）。
    #: `quantitative_link` 在沒有任何 linked 催化劑時是 `not_modeled`，而型別層禁止
    #: 無值狀態帶值——於是「有催化劑但沒填 resolves」「有 resolves 但日期晚」「根本沒有催化劑」
    #: 三件事在下游長得一模一樣（L12）。這一格**永遠 available**，由 producer 宣告形狀。
    shape: Datum


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
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`target_valuation`（照抄 valuation.fair_value）隨估值鏈退役。


@dataclass(frozen=True, slots=True)
class MarketSection:
    """現價（A2 觀測）。**2026-09-23（Phase 0 Step 0b.1）新增：把現價從估值鏈裡搬出來。**

    事發：現價原本只住在 `ValuationSection.current_price`／`ImpliedReturnSection.current_price`／
    `EntryLogicSection.current_price` 三個地方——**全部是退役的 section**。於是「這一檔現在多少錢」
    這個純觀測會跟著估值模型一起消失，而它與估值一點關係都沒有（它是 Engine C 的收盤快照）。

    這一節只有一格，且**沒有任何算術**：值、報價單位、bar 日期、證據全部照抄 Engine C 快照。
    `meta.status` 由「有沒有價」決定，不由估值算不算得出來決定——這是本次搬家的整個重點。
    """

    meta: SectionMeta                          # available／missing
    price: Datum


# ⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`ValuationSection`（Step 1 fair value）與
# `ImpliedReturnSection`（Step 2 隱含報酬，含 `target_reached`）退役。** 現價（它們共用的 `current_price`）
# 已於 0b.1a 搬進 `MarketSection`。「已定價嗎」由財務三題回答（Phase 3），主參照是自己的歷史、不設門檻。


# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：`PayoffScenarioSection` 退役（E 組）。**
# 它是賭注／下檔的四個價格（目標價、報酬、EPS 貢獻、倍數貢獻）＋ overrides。
# `bet` 面板已於 0b.1a 改成純文字（讀短評的 `our_bet`）；ledger 資料留著（L10）。


@dataclass(frozen=True, slots=True)
class InvestorBriefSection:
    """投資人短評（2026-09-15）：七格前因後果。**文字照抄 ledger、數字照抄既有 Datum**——本 section 不算任何數。

    - `slots`：七格，每格的 `value` 是填好數字的句子；`dependencies` 帶原文、placeholder、缺值清單與引用。
    - ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`scale`（一把尺）欄位退役；`multiple_question` 同批退役。
    - `status_light`：refresh overall 的白話版（一個燈，不是一串狀態）。
    - ⚠ `multiple_question` 已於 2026-09-23（Phase 0 Step 0b.1b）隨多年反向橋退役。
    """

    meta: SectionMeta
    slots: tuple[Datum, ...]
    status_light: Datum
    brief_id: str | None
    is_not: tuple[str, ...]
    #: 要翻倍需要什麼為真（2026-09-20）。`None`＝這一檔還沒寫下倍率射程，**刻意不印**。


@dataclass(frozen=True, slots=True)
class ArgumentSection:
    """論證層（2026-09-15）：六段——這條鏈怎麼走／數字怎麼算出來／和市場差在哪／賭注／風險與認錯條件／時間表。

    - 每段一個 Datum：`value` 是段落文字；`dependencies["citations"]` 是這段引用到的 claim（statement、誰說的、哪天）；
      `dependencies["long_form"]` 是 session 寫的長文（假設理由、賭注理由、風險、推翻條件）原文清單。
    - 算術與圖的敘述由 `alpha.narrative.argument` 的封閉句型組；本 section 不算任何數。
    - 任何一段缺料就 `missing`＋理由（不補、不硬寫）。
    """

    meta: SectionMeta
    paragraphs: tuple[Datum, ...]
    is_not: tuple[str, ...]


# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：`EntryLogicSection` 退役（F 組）。**
# 進場門檻（要求報酬 → 門檻價 → 現價比較）73 檔全 missing、從未用過。
# **進場靠判斷，出場靠 disproof**——系統不再有「門檻價」這個概念。


@dataclass(frozen=True, slots=True)
class NotModeledSection:
    """「這個能力系統沒有」的形狀：全 `not_modeled`，附「不要跟什麼混淆」。

    ⚠ 2026-09-18（D2）起 **`downside` 不再用它**——下檔已經建模，它是 `PayoffScenarioSection`。
    本型別保留給真正沒有能力的東西；用它之前先問一次：**這是「沒有這個能力」還是
    「有能力但這一檔還沒人寫」？** 後者要用 `missing`＋`not_yet_recorded`，因為兩者的
    下一步完全不同——`not_modeled` 沒有人該去補，`missing` 有。
    """

    meta: SectionMeta
    items: tuple[Datum, ...]
    not_to_be_confused_with: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WipeoutFlagsSection:
    """歸零旗標（D2，2026-09-18）：四盞紅黃綠燈——**這家公司會不會歸零**。

    每盞燈一個 `Datum`，`value` 是 `{"colour", "reason", "rule", "inputs"}`；**燈不亮時
    `status` 不是 available，而是帶 `absence_kind` 的缺席**——所以「這盞是綠的」與「這盞沒點亮」
    在型別層就不可能同形（L12）。

    `tally` 是紅／黃／綠／灰的計數（常駐計數器，L14）。**不參與排序、不決定尺寸**——
    它與總曝險倍數、追繳門檻同屬「量測」，不是訊號（AGENTS「須區分量測、訊號與脈絡」）。
    """

    meta: SectionMeta
    lanes: tuple[Datum, ...]
    tally: Mapping[str, int]
    is_not: tuple[str, ...]


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
class RefreshItem:
    """一個研究成果的 refresh state（由 `alpha.refresh.resolve_refresh` 算出，這裡只抄）。"""

    artifact_type: str
    artifact_id: str
    label: str
    state: str
    reasons: tuple[str, ...]
    changed_refs: tuple[str, ...]
    dependency_refs: tuple[str, ...]
    detected_at: datetime | None
    established_at: datetime | None
    required_action: str
    propagated_from: tuple[str, ...]
    kind: str


@dataclass(frozen=True, slots=True)
class ChangeItem:
    """一件已分類的變化（`alpha.refresh.ChangeEvent` 的 view 形狀）。"""

    change_id: str
    change_type: str
    authority: str
    changed_ref: str
    observed_at: datetime
    effective_at: date | None
    old_version: str | None
    new_version: str | None
    material_fields: tuple[str, ...]
    detail: str
    target_artifact: str | None


@dataclass(frozen=True, slots=True)
class RefreshStatusSection:
    """什麼變了、影響哪些研究成果、各自處在哪種 state、要做什麼。

    read model **只組裝**：impact 由 `alpha.refresh` 單一 authority 算出。`overall` 是所有非終局
    成果的最高 state；`counts` 是各 state 的個數（常駐計數器，L14）。
    """

    meta: SectionMeta
    overall: str
    policy_version: str
    counts: Mapping[str, int]
    items: tuple[RefreshItem, ...]
    changes: tuple[ChangeItem, ...]
    excluded_changes: Mapping[str, int]
    excluded_artifacts: Mapping[str, int]
    notes: tuple[str, ...]
    digest: str
    change_detection: str                    # "authority_time_series"／"not_run"／"scenario"
    judged_context_matches: bool | None


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
    #: ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`price_implied_expectations`／`internal_fundamentals`／
    #: `earnings_bridge`／`valuation`／`implied_return` 五個欄位隨估值鏈退役。
    expectation_gap: ExpectationGapSection
    catalysts: CatalystSection
    falsification: FalsificationSection
    scenarios: ScenarioSection
    #: 2026-09-23（Phase 0 Step 0b.1）：現價自己的家。它曾是估值的輸入，不是估值的產物；
    #: 估值退役後它還在（個股頁的「現在多少錢」讀它）。
    market: MarketSection
    #: D2（2026-09-18）：由 `NotModeledSection` 換成與賭注**對稱**的 overlay。
    #: 舊語意「系統不產生下檔估計」已作廢——現在它是「反證成真時的假設套同一條橋」，
    #: 仍然不是 bear case、沒有機率加權。
    #: D2（2026-09-18）：歸零旗標四盞燈。與 `downside` 是同一個問題的兩面——
    #: 後者答「判斷錯了值多少」，它答「這家公司會不會直接歸零」。
    wipeout_flags: WipeoutFlagsSection
    evidence: EvidenceSection
    freshness: tuple[FreshnessItem, ...]
    refresh_status: RefreshStatusSection
    investor_brief: InvestorBriefSection
    argument: ArgumentSection
    warnings: tuple[str, ...] = ()

    #: 有 `meta` 的 section 名稱，`capability_map()` 依此列舉。
    SECTIONS_WITH_META = (
        "variant_view", "structural_thesis", "causal_paths", "fundamentals", "consensus",
        "expectation_gap", "catalysts", "falsification", "scenarios", "market",
        "wipeout_flags", "evidence", "refresh_status",
        "investor_brief", "argument",
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
        payload = {f.name: _jsonable(getattr(obj, f.name)) for f in fields(obj)}
        # `Datum`／`SectionMeta` 的 `absence_kind` 對外一律輸出**生效值**（明示優先，否則查
        # `status` 的預設表）。序列化後的消費端（APP／API）沒有 property，若原樣輸出 None，
        # 每個消費端都得自己再實作一次那張表——而重造品會立刻開始偏離（L16）。
        if isinstance(obj, (Datum, SectionMeta)):
            payload["absence_kind"] = obj.effective_absence_kind
        return payload
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
    "CAP_INVESTOR_BRIEF", "InvestorBriefSection", "CAP_ARGUMENT", "ArgumentSection",
    "CAP_CATALYST_UNLINKED", "CAP_DEPENDENCY_IMPACT",
    "CAP_NARRATIVE_SCENARIOS", "MarketSection",
    "ChangeItem", "REFRESH_STATUSES", "RefreshItem", "RefreshStatusSection",
    "CAP_QUANTITATIVE_SCENARIOS", "CAP_STRUCTURAL_CAUSAL", "CAP_STRUCTURED_DISPROOF",
    "CatalystItem", "CatalystSection", "CausalPathSection", "CheckpointItem",
    "ConsensusSection", "Datum", "DisproofItem", "EventItem",
    "EvidenceItem", "EvidenceSection", "EvidenceSelectionCounts", "ExpectationGapSection",
    "ExposureItem", "FalsificationSection", "FreshnessItem", "FundamentalsSection",
    "IdentitySection", "ImpactItem", "LifecycleFacts",
    "NotModeledSection", "PathItem", "SCHEMA_VERSION",
    "SECTION_STATUSES", "STATUS_LABEL", "ScenarioSection", "SectionMeta", "SectionStatus",
    "SignalCompleteness", "StructuralEdgeItem", "StructuralThesisSection",
    "ABSENCE_KINDS", "VALUELESS_STATUSES", "VariantViewSection", "ViewContractViolation", "missing",
    "not_modeled",
]
