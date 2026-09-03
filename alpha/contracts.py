"""Alpha Research Core 的型別契約。

本模組**只有型別與驗證，沒有任何外部相依**（不 import neo4j／yfinance／anthropic／
engine_c／decision_lab）。它是 `alpha/` 與其他所有層之間唯一的共同語言。

## 三條在型別層強制、不靠人記得的規則

1. **`AlphaSignal` 不得有部位欄位，也不得有 scalar 總分**（`assert_alpha_signal_shape`
   在 import 時就跑；加一個 `weight` 或 `value` 欄位會讓整個 package import 失敗）。
2. **`Score` 分 `declared` 與 `effective`**——F-25：宣告 corroborated 但引用不成立時，
   排序若用宣告值就會漏掉它。
3. **`RankedList` 同時帶截斷後的 rows 與截斷前的完整 id 集合**——F-20：只帶前 N 名
   會讓成員判斷把第 N+1 名誤判成「不在排序裡」。

## 刻意不做的事

- 不算加權總分（見 `AlphaSignal.ordering_key`）。
- 不把五套證據強度壓成一個分數（見 `EvidenceRef`）。
- 不把 `None` 當 0（見 `_rank_component`）。
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from typing import Any, Generic, Literal, Mapping, Protocol, Sequence, TypeVar, runtime_checkable

from .errors import ContractViolation
from .identity import SCALAR_IDENTIFIERS, CompanyId, EntityId, Ticker

T = TypeVar("T")


# ---------------------------------------------------------------------------
# 0. canonical 序列化（content-addressed digest 用）
# ---------------------------------------------------------------------------

def _canonical(obj: Any) -> Any:
    """把 dataclass／日期／集合遞迴轉成可穩定 JSON 序列化的結構。

    ⚠ identifier 型別渲染成**字串**而非物件：`CompanyId("co:axt")` → `"co:axt"`。
    它們在語意上是純量，只是被包成型別以免互相賦值（INV-1）；
    渲染成 `{"value": ...}` 會讓 digest payload 與 fixture 被無意義的巢狀淹沒。
    """
    if isinstance(obj, SCALAR_IDENTIFIERS):
        return str(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _canonical(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_canonical(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(_canonical(v) for v in obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def content_digest(payload: Any) -> str:
    """content-addressed digest。同一份內容永遠得到同一個 digest。"""
    blob = json.dumps(_canonical(payload), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractViolation(f"{label} 必須是非空字串")
    return value


# ---------------------------------------------------------------------------
# 1. EvidenceRef — 跨層 provenance 的唯一載體
# ---------------------------------------------------------------------------

EvidenceKind = Literal[
    "graph_claim", "graph_assertion", "graph_edge", "source_doc",
    "engine_c_observation", "engine_c_snapshot", "market_series", "external_document",
]

#: `EvidenceRef.kind` 是 **contract**（刻意有限）不是 taxonomy——多一種 kind 代表
#: 多一條 provenance 路徑，必須有人設計。打開它是 bug，不是設定。
EVIDENCE_KINDS: frozenset[str] = frozenset(EvidenceKind.__args__)  # type: ignore[attr-defined]


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """一條可追溯的證據引用。

    ⚠ **五套證據強度欄位刻意並列，不得壓成單一 evidence score。**
    現況圖裡有五種語意不同的強度字彙（`evidence_tier` 文件類型可靠度／
    `demand_proof_level` 需求證實程度／`confidence` 關係存在信心／
    `evidence_class` 排序用等級／L8 的獨立 origin 計數），各有正當理由。
    壓成一個分數是 L12「一表兩義」的相反錯誤：把五種問題壓成一個答案，
    下游只能二選一，而每一邊都是錯的。

    ⚠ **三個時間欄位缺一不可（可以是 None，但不得省略欄位）。**
    `published_at`＝世界知道這件事的時間；`retrieved_at`＝我們抓到的時間；
    `recorded_at`＝寫進系統的時間。F-27 就是前兩者被壓成一個欄位造成的。
    """

    ref: str
    kind: str

    # provenance
    source_doc_id: str | None = None
    origin_entity: str | None = None
    origin_event: str | None = None
    url: str | None = None
    quote: str | None = None

    # 時間（point-in-time 的骨架）
    published_at: date | None = None
    retrieved_at: date | None = None
    recorded_at: datetime | None = None

    # 強度：五套並列
    evidence_tier: int | None = None
    demand_proof_level: str | None = None
    confidence: float | None = None
    evidence_class: str | None = None
    corroborating_origins: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.ref, "EvidenceRef.ref")
        if self.kind not in EVIDENCE_KINDS:
            raise ContractViolation(
                f"EvidenceRef.kind 未登記：{self.kind!r}；已知 {sorted(EVIDENCE_KINDS)}"
            )
        if self.evidence_tier is not None and self.evidence_tier not in (1, 2, 3, 4):
            raise ContractViolation(
                f"evidence_tier 必須是 1–4（1=strongest）：{self.evidence_tier!r}"
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ContractViolation(f"confidence 必須落在 0..1：{self.confidence!r}")

    @property
    def is_dated(self) -> bool:
        """有沒有 `published_at`。⚠ 沒有**不等於**在 T 之前（L11-5）。"""
        return self.published_at is not None


@dataclass(frozen=True, slots=True)
class EvidenceSelection:
    """as-of 篩選的結果與**被排除的計數**。

    ⚠ 計數不是裝飾。INV-3（no silent drop）要求每個 filtering stage 都能回答
    input／accepted／filtered／reasons；沒有這三個數字，「as-of 之後證據變少了」
    與「本來就沒有證據」在下游同形（L13）。
    """

    kept: tuple[EvidenceRef, ...]
    excluded_future: tuple[EvidenceRef, ...] = ()
    excluded_undated: tuple[EvidenceRef, ...] = ()

    @property
    def input_count(self) -> int:
        return len(self.kept) + len(self.excluded_future) + len(self.excluded_undated)

    @property
    def accepted_count(self) -> int:
        return len(self.kept)

    @property
    def filtered_count(self) -> int:
        return len(self.excluded_future) + len(self.excluded_undated)

    def reasons(self) -> dict[str, int]:
        return {
            "published_after_as_of": len(self.excluded_future),
            "undated": len(self.excluded_undated),
        }


def select_point_in_time_evidence(
    refs: Sequence[EvidenceRef], *, as_of: date | None
) -> EvidenceSelection:
    """依 `as_of` 篩選證據。`as_of is None` 代表「當前視角」，不做篩選。

    **`published_at is None` 一律排除並計數**——「我找不到日期」不等於
    「它發生在 T 之前」（L11-5）。把未標日期的證據當成可用，等於讓回測看到未來。
    """
    if as_of is None:
        return EvidenceSelection(kept=tuple(refs))
    kept: list[EvidenceRef] = []
    future: list[EvidenceRef] = []
    undated: list[EvidenceRef] = []
    for ref in refs:
        if ref.published_at is None:
            undated.append(ref)
        elif ref.published_at > as_of:
            future.append(ref)
        else:
            kept.append(ref)
    return EvidenceSelection(tuple(kept), tuple(future), tuple(undated))


@dataclass(frozen=True, slots=True)
class EvidenceQuality:
    """一組證據**能撐多高**，以及為什麼。

    ⚠ 這是舊 `source_reliability` 軸的新家。它**不是** `AlphaSignal` 的第六個維度——
    「你憑什麼相信前面那些答案」不是一個投資問題，它是套在**所有**維度上的上限。

    - 舊語意：`weakest = min(五軸)`；`source_reliability` 最弱時它就是 weakest，
      而輸出只會說「證據不夠」，不會說「所以哪個投資維度看不清」。
    - 新語意：`effective = min(declared, ceiling)`，被壓下去的維度帶
      `downgrade_reason="evidence_quality_ceiling"`——**多回答了「什麼看不清」**。

    推導邏輯在 `alpha/evidence_quality.py`（型別住這裡，判斷住那裡）。
    """

    level: str
    independent_origins: int
    best_tier: int | None
    total_refs: int
    reason: str
    scale_version: str = "ordinal-v1"

    def __post_init__(self) -> None:
        from .levels import level_rank

        if level_rank(self.level) < 0:
            raise ContractViolation(f"EvidenceQuality.level 未登記：{self.level!r}")

    @property
    def ceiling(self) -> float:
        from .levels import level_to_ceiling

        return level_to_ceiling(self.level)

    def apply(self, declared: float) -> tuple[float, str | None]:
        """把上限套到宣告值上。回傳 `(effective, downgrade_reason)`。"""
        if declared <= self.ceiling:
            return declared, None
        return self.ceiling, "evidence_quality_ceiling"


# ---------------------------------------------------------------------------
# 2. Score / ComponentTrace / DisproofCondition / Catalyst
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ComponentTrace:
    """一個 score 的推導過程。**沒有 trace 的 score 不得存在。**"""

    trace_id: str
    rule_version: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[EvidenceRef, ...] = ()
    note: str | None = None

    def __post_init__(self) -> None:
        _nonempty(self.trace_id, "ComponentTrace.trace_id")
        _nonempty(self.rule_version, "ComponentTrace.rule_version")


@dataclass(frozen=True, slots=True)
class Score:
    """一個維度的分數，**宣告值與生效值分開**。

    F-25：`_validate_assessment` 在引用不成立時把 ceiling 打成 0 卻**不動 level**，
    於是「宣告 corroborated 但引用不成立」的軸用 raw level 排序會被漏掉。
    這裡把那個隱含資訊顯性化——**排序一律用 `effective`**。
    """

    declared: float
    effective: float
    trace_id: str
    downgrade_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("declared", "effective"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ContractViolation(f"Score.{name} 必須是數值：{value!r}")
            if not 0.0 <= float(value) <= 1.0:
                raise ContractViolation(f"Score.{name} 必須落在 0..1：{value!r}")
        if self.effective > self.declared:
            raise ContractViolation(
                "Score.effective 不得高於 declared——生效值只會因證據不成立而下降"
            )
        if self.effective < self.declared and not self.downgrade_reason:
            raise ContractViolation(
                "effective < declared 時必須寫 downgrade_reason（因果不得被截斷，L12）"
            )
        _nonempty(self.trace_id, "Score.trace_id")


@dataclass(frozen=True, slots=True)
class DisproofCondition:
    """可證偽條件。**L7 三件套缺一即拒收。**

    L7 原話：「光是填 `disproof_condition` 不夠。欄位有填但沒有後續流程，
    等於貼了一個永遠不會響的火警警報。」所以核查頻率與 48 小時動作是**必填**。
    """

    condition: str
    check_frequency: str
    action_within_48h: str
    evidence_refs: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.condition, "DisproofCondition.condition")
        _nonempty(self.check_frequency, "DisproofCondition.check_frequency（L7 核查頻率）")
        _nonempty(
            self.action_within_48h,
            "DisproofCondition.action_within_48h（L7 觸發後 48 小時內做什麼）",
        )


@dataclass(frozen=True, slots=True)
class Catalyst:
    """會讓市場重新定價的具名事件。`kind` 是**封閉字彙**，權威在
    `config/catalyst_kinds.json`（taxonomy——世界會長出新品類，加一列即可）。"""

    kind: str
    description: str
    expected_at: date | None = None
    date_confidence: Literal["confirmed", "estimated", "unknown"] = "unknown"
    evidence_refs: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        from .vocabulary import catalyst_kinds, validate_kind

        _nonempty(self.kind, "Catalyst.kind")
        validate_kind(self.kind, catalyst_kinds(), "Catalyst.kind")
        _nonempty(self.description, "Catalyst.description")


# ---------------------------------------------------------------------------
# 3. Snapshot 型別（每個欄位都是 X | None；None ＝ 不知道，不是 0）
# ---------------------------------------------------------------------------

FreshnessStatus = Literal["available", "stale", "missing", "quarantined"]


@dataclass(frozen=True, slots=True)
class FreshnessState:
    """一個 section 的新鮮度。沿用 Engine D 既有字彙，避免第二套狀態語言。"""

    as_of: date | None
    age_days: float | None
    status: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in ("available", "stale", "missing", "quarantined"):
            raise ContractViolation(f"FreshnessState.status 未登記：{self.status!r}")


@dataclass(frozen=True, slots=True)
class ScarcityInputs:
    """Q1 的結構輸入。全部來自 Engine A，全部帶 evidence。"""

    substitutability: int | None = None
    sole_source: bool | None = None
    qualification_status: str | None = None
    qualification_lead_time_weeks: int | None = None
    dependency_depth: int | None = None
    demand_anchor: EntityId | None = None
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class FundamentalsSnapshot:
    gross_margin: float | None = None
    operating_margin: float | None = None
    revenue_ttm: float | None = None
    free_cash_flow_ttm: float | None = None
    cash_and_equivalents: float | None = None
    total_debt: float | None = None
    shares_outstanding: float | None = None
    segment_revenue_share: Mapping[str, float] | None = None
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    price: float | None = None
    bar_date: date | None = None
    price_kind: str | None = None
    currency: str | None = None
    market_cap: float | None = None
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class ConsensusSnapshot:
    analyst_count: int | None = None
    target_mean: float | None = None
    forward_pe: float | None = None
    trailing_pe: float | None = None
    ev_revenue: float | None = None
    forward_eps: float | None = None
    revenue_estimate_next_fy: float | None = None
    estimate_revision_30d: float | None = None
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class ValuationSnapshot:
    """由上面幾張表**導出**的隱含假設。它是計算結果，不是觀測。"""

    market_implied_growth: float | None = None
    market_implied_margin: float | None = None
    internal_implied_growth: float | None = None
    internal_implied_margin: float | None = None
    method: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class StructuralContext:
    """`GraphResearchProvider` 回傳的公司結構切片。"""

    company_id: CompanyId | None
    edges: tuple[Mapping[str, Any], ...] = ()
    claims: tuple[Mapping[str, Any], ...] = ()
    counter_paths: tuple[Mapping[str, Any], ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()


# ---------------------------------------------------------------------------
# 4. RankedList — 截斷集合不得被當成全集（F-20）
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OrderingRule:
    """具名、版本化的排序鍵順序。

    ⚠ 換排序規則前必須能回答「現有 N 筆 signal 有幾筆排序會變」（L14）。
    把規則變成一個有名字的物件，就是為了讓那個問題問得出來。
    """

    name: str
    version: str
    keys: tuple[str, ...]

    def __post_init__(self) -> None:
        _nonempty(self.name, "OrderingRule.name")
        _nonempty(self.version, "OrderingRule.version")
        if not self.keys:
            raise ContractViolation("OrderingRule.keys 不得為空")


@dataclass(frozen=True, slots=True)
class RankedList(Generic[T]):
    """排序結果。**同時帶截斷後的 rows 與截斷前的完整 id 集合。**

    F-20 實測：ranking DTO 只帶前 `limit` 名，於是直接比對把**排 11 名之後的公司
    誤判成「不在排序裡」**。修法不是叫人記得，是讓型別本身帶著正確的東西——
    成員判斷只能經 `contains()`／`in`，而它讀的是 `full_ids`。
    """

    rows: tuple[T, ...]
    row_ids: tuple[str, ...]
    full_ids: tuple[str, ...]
    ordering_rule: OrderingRule
    truncated_at: int | None = None

    def __post_init__(self) -> None:
        if len(self.rows) != len(self.row_ids):
            raise ContractViolation("rows 與 row_ids 長度必須相同")
        missing = set(self.row_ids) - set(self.full_ids)
        if missing:
            raise ContractViolation(f"row_ids 必須是 full_ids 的子集；多出：{sorted(missing)}")

    @property
    def is_truncated(self) -> bool:
        return len(self.row_ids) < len(self.full_ids)

    def contains(self, identifier: Any) -> bool:
        """成員判斷——**讀 `full_ids`，不讀 `rows`**。"""
        return str(identifier) in set(self.full_ids)

    def __contains__(self, identifier: Any) -> bool:
        return self.contains(identifier)

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)


# ---------------------------------------------------------------------------
# 5. ResearchContext — 形成觀點時看到什麼（⚠ 不是 DecisionContext）
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ResearchContext:
    """研究工作區的 point-in-time 凍結。

    ⚠ **`ResearchContext` ≠ `DecisionContext`，兩者不得合併。**
    前者可重算（研究可以重跑）、無 authority；後者 append-only、是稽核責任的載體。
    合併的具體災難：research 一天跑十次都會建 context，若共用同一張表，
    Decision Store 會從「268 筆有責任的決策紀錄」變成「幾千筆研究草稿裡混著 268 筆決策」，
    而**兩者都是 append-only 拿不回來**（L10）。

    銜接方式是 `AlphaSignal.research_context_digest` ——引用，不複製。
    """

    ticker: Ticker
    company_id: CompanyId | None
    as_of: date | None

    graph: StructuralContext
    structural: ScarcityInputs
    fundamentals: FundamentalsSnapshot
    market: MarketSnapshot
    consensus: ConsensusSnapshot
    valuation: ValuationSnapshot
    catalysts: tuple[Catalyst, ...] = ()

    evidence_selection: EvidenceSelection = field(
        default_factory=lambda: EvidenceSelection(kept=())
    )
    freshness: Mapping[str, FreshnessState] = field(default_factory=dict)
    source_versions: Mapping[str, str] = field(default_factory=dict)
    digest: str = ""

    def __post_init__(self) -> None:
        if self.as_of is not None:
            late = [r for r in self.evidence_selection.kept
                    if r.published_at is None or r.published_at > self.as_of]
            if late:
                raise ContractViolation(
                    "as-of 模式下 kept evidence 不得含未標日期或晚於 as_of 的引用："
                    f"{[r.ref for r in late][:3]}"
                )
        if not self.digest:
            object.__setattr__(self, "digest", content_digest(self._digest_payload()))

    def _digest_payload(self) -> Mapping[str, Any]:
        return {
            "ticker": str(self.ticker),
            "company_id": str(self.company_id) if self.company_id else None,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "graph": _canonical(self.graph),
            "structural": _canonical(self.structural),
            "fundamentals": _canonical(self.fundamentals),
            "market": _canonical(self.market),
            "consensus": _canonical(self.consensus),
            "valuation": _canonical(self.valuation),
            "catalysts": _canonical(self.catalysts),
            "evidence": sorted(r.ref for r in self.evidence_selection.kept),
            "source_versions": _canonical(self.source_versions),
        }

    @property
    def evidence_refs(self) -> tuple[EvidenceRef, ...]:
        return self.evidence_selection.kept


# ---------------------------------------------------------------------------
# 6. AlphaSignal — research view，不是 position
# ---------------------------------------------------------------------------

#: 五個維度的宣告次序。**同時是 `ordering_key` 的 tie-break 次序來源**，
#: 所以改動它等於改排序規則，必須連 `DEFAULT_ORDERING_RULE.version` 一起改。
AXES: tuple[str, ...] = (
    "structural",          # Q1 Structural Scarcity
    "value_capture",       # Q2 Economic Value Capture
    "earnings_exposure",   # Q3 Earnings / FCF Exposure
    "expectation_gap",     # Q4 Expectation Gap
    "catalyst",            # Q5 Catalyst
)

#: tie-break 次序：先問「市場是不是錯了」（Q4），再問「這個結構有多硬」（Q1），
#: 再問「什麼時候會被重新定價」（Q5），最後才是 Q2／Q3。
#: ⚠ 這個順序是一個**可否證的研究判斷**，不是自然法則——換它要能答出幾筆排序會變。
_TIEBREAK: tuple[str, ...] = (
    "expectation_gap", "structural", "catalyst", "value_capture", "earnings_exposure",
)

DEFAULT_ORDERING_RULE = OrderingRule(
    name="weakest_then_gap_first",
    version="v1",
    keys=("incomplete", "weakest_effective") + _TIEBREAK + ("ticker",),
)

#: 出現在 `AlphaSignal` 欄位名裡即視為部位語意——**research view 不得攜帶部位**。
#:
#: ⚠ **`exposure` 刻意不在列上。** 第一版放了它，結果 import 時直接攔下
#: `earnings_exposure_score`——那是 Q3 的研究維度，不是部位。這是 L15 的現場實例：
#: **gate 攔下的若是格式而不是風險，該修的是它問問題的方式。**
#: `nav` 已經涵蓋真正的部位用法（`nav_exposure`），而 `earnings_exposure`／
#: `revenue_exposure` 是完全正當的研究詞彙。名單只留**無歧義**的 token。
FORBIDDEN_POSITION_TOKENS: frozenset[str] = frozenset(
    {"weight", "shares", "nav", "size", "position", "notional", "quantity",
     "allocation", "sizing", "lot", "portfolio", "capital"}
)

#: 單一綜合分數的欄位名。**加權總分有補償性**——2026-08-21 實測 pq1 排序
#: `tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0`，三個各自成立的弱理由相加就壓過
#: 真正的資本承諾事件；改成字典序後「只是信心／無內容」由 3 → 0。
#: 五個 score 有完全相同的形狀，所以套用同一個結論。
FORBIDDEN_COMPOSITE_FIELDS: frozenset[str] = frozenset(
    {"value", "alpha", "score", "composite", "composite_score", "total", "total_score",
     "rank_score", "overall"}
)


def assert_alpha_signal_shape(cls: type) -> None:
    """在 import 時強制「無部位欄位、無 scalar 總分」。

    ⚠ 這不是可選的 lint——它在模組載入時就跑。加一個 `weight: float` 或
    `value: float` 欄位會讓 `import alpha` 直接失敗，而不是等某個測試哪天想起來。
    """
    for f in fields(cls):
        parts = set(f.name.lower().split("_"))
        banned = parts & FORBIDDEN_POSITION_TOKENS
        if banned:
            raise ContractViolation(
                f"{cls.__name__}.{f.name} 帶部位語意 {sorted(banned)}；"
                "AlphaSignal 是 research view，部位由 portfolio/ 決定"
            )
        if f.name.lower() in FORBIDDEN_COMPOSITE_FIELDS:
            raise ContractViolation(
                f"{cls.__name__}.{f.name} 是單一綜合分數；加權總分有補償性"
                "（2026-08-21 pq1 實測），排序請用 ordering_key()"
            )


def _rank_component(score: Score | None) -> float:
    """排序用的分量。**`None` 與 `0.0` 產生不同的鍵。**

    `None`＝不知道 → `math.inf`（比任何實際分數都差，但不是 0）；
    `0.0`＝我判斷它很弱 → `-0.0`。把 `None` 當 0 會讓「沒研究」看起來像「研究過但很弱」。
    """
    if score is None:
        return math.inf
    return -float(score.effective)


@dataclass(frozen=True, slots=True)
class AlphaSignal:
    """一個標的在某個 `as_of` 的研究觀點。

    ⚠ **`AlphaSignal` != Position。** 它沒有、也永遠不會有部位欄位；
    ⚠ **v1 沒有 scalar `value`／`alpha`。** 排序由 `ordering_key()` 的字典序產生。
    兩條都由 `assert_alpha_signal_shape` 在 import 時強制。
    """

    ticker: Ticker
    company_id: CompanyId | None
    as_of: date

    structural_score: Score | None
    value_capture_score: Score | None
    earnings_exposure_score: Score | None
    expectation_gap_score: Score | None
    catalyst_score: Score | None

    direction: Literal["long", "short", "neutral"]
    confidence: float
    expected_horizon: str

    thesis: str
    variant_view: str
    bull_case: str
    base_case: str
    bear_case: str

    disproof_conditions: tuple[DisproofCondition, ...]
    catalysts: tuple[Catalyst, ...] = ()
    risks: tuple[str, ...] = ()

    evidence_quality: EvidenceQuality | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    model_components: Mapping[str, ComponentTrace] = field(default_factory=dict)
    research_context_digest: str = ""
    ordering_rule: OrderingRule = DEFAULT_ORDERING_RULE
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ContractViolation(f"confidence 必須落在 0..1：{self.confidence!r}")
        if not self.disproof_conditions:
            raise ContractViolation(
                "disproof_conditions 不得為空——可證偽是一等公民（L7／schema §3）"
            )
        for axis in AXES:
            score = self.score_for(axis)
            if score is None:
                continue
            if score.trace_id not in self.model_components:
                raise ContractViolation(
                    f"{axis}_score 的 trace_id={score.trace_id!r} 不在 model_components——"
                    "算不出來就不出分數，不是出一個沒有推導過程的分數"
                )
            trace = self.model_components[score.trace_id]
            if not trace.evidence_refs:
                raise ContractViolation(
                    f"{axis}_score 的 trace 沒有任何 EvidenceRef——"
                    "所有重要 conclusion 必須可回溯至 evidence（INV-6）"
                )
            # 證據品質是套在所有維度上的上限（舊 source_reliability 軸的新家）。
            # 超過上限代表「這組證據撐不起這個分數」——那是 L8 要防的事。
            if (self.evidence_quality is not None
                    and score.effective > self.evidence_quality.ceiling):
                raise ContractViolation(
                    f"{axis}_score 的 effective={score.effective} 超過證據品質上限 "
                    f"{self.evidence_quality.ceiling}（{self.evidence_quality.reason}）——"
                    "供應商自報不能撐起外部印證等級的結論（L8）"
                )

    # ---- 讀取 -------------------------------------------------------------
    def score_for(self, axis: str) -> Score | None:
        if axis not in AXES:
            raise ContractViolation(f"未知維度：{axis!r}；已知 {AXES}")
        return getattr(self, f"{axis}_score")

    @property
    def is_incomplete(self) -> bool:
        """任一維度為 `None` 即 incomplete——**不得靜默當成 0 參與比較**。"""
        return any(self.score_for(axis) is None for axis in AXES)

    @property
    def known_axes(self) -> tuple[str, ...]:
        return tuple(a for a in AXES if self.score_for(a) is not None)

    @property
    def weakest(self) -> str | None:
        """證據最弱的維度——**也是「該補什麼」**。全 None 時回 None。"""
        known = self.known_axes
        if not known:
            return None
        return min(known, key=lambda a: (self.score_for(a).effective, AXES.index(a)))  # type: ignore[union-attr]

    def ordering_key(self) -> tuple:
        """排序鍵（**升冪排序即為最佳在前**）。

        ⚠ **不做加權總分。** 鍵的順序是：
        `incomplete` → `weakest`（max-min）→ Q4 → Q1 → Q5 → Q2 → Q3 → ticker。
        字典序結構上沒有補償性；加權總分結構上有——一個弱維度無法被另外四個補回來。
        """
        weakest = self.weakest
        weakest_component = (
            math.inf if weakest is None else -float(self.score_for(weakest).effective)  # type: ignore[union-attr]
        )
        return (
            1 if self.is_incomplete else 0,
            weakest_component,
            *(_rank_component(self.score_for(axis)) for axis in _TIEBREAK),
            str(self.ticker),
        )


assert_alpha_signal_shape(AlphaSignal)


# ---------------------------------------------------------------------------
# 7. AlphaModel — 研究模型的唯一介面
# ---------------------------------------------------------------------------

@runtime_checkable
class AlphaModel(Protocol):
    """研究模型。**不負責 position sizing、leverage、portfolio constraints、execution。**"""

    name: str
    version: str

    def predict(
        self, ticker: Ticker, as_of: date, context: ResearchContext
    ) -> AlphaSignal: ...
