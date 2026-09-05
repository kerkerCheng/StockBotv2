"""Causal Fundamental Model 的型別契約。**只有型別與驗證，零外部相依。**

## 四個一等公民

| 型別 | 誰擁有它 | 可變性 |
|---|---|---|
| `FiscalPeriod` | 共同語言 | 身分是 `end` 日期，`FY2027` 只是呈現慣例 |
| `OperatingAssumption` | A3 研究判斷（private append-only ledger） | 可重算；改假設＝append 新紀錄 |
| `FiscalYearActuals`／`ConsensusEstimate`／`GuidanceObservation` | A2 Engine C 觀測 | 由 provider 唯讀取出 |
| `ModeledMetric`／`ExpectationComparison` | A3 模型輸出 | 由 `bridge.py`／`compare.py` 確定性算出 |

## 三條在型別層強制的規則

1. **假設必須帶 basis、rationale、evidence、created_at。** 沒有 provenance 的假設不得存在
   （INV-6）；retracted 紀錄例外，它只是一個「撤回」標記。
2. **driver 是封閉字彙（contract）。** 每個 driver 對應 `bridge.py` 的一段算術；多一個 driver
   就要多一段算術，所以打開它是改程式不是改設定。
3. **模型輸出分兩層標：`calculation="deterministic"` 與 `input_dependency`（最弱輸入的
   知識種類）。** 前者說「算法確定」，後者說「輸入是判斷」，兩者不得壓成一個欄位（L12）。
"""
from __future__ import annotations

import calendar
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Sequence

from ..contracts import EvidenceRef
from ..errors import ContractViolation

MODEL_VERSION = "causal-fundamental-model/v1"
BRIDGE_VERSION = "fundamental-bridge/v1"

# ---------------------------------------------------------------------------
# 0. 會計期間（身分是日期）
# ---------------------------------------------------------------------------

FISCAL_PERIOD_KINDS: tuple[str, ...] = ("fiscal_year",)

#: 兩個會計期間視為「同一期」的容忍天數。52／53 週制的年度結束日會在同一週內浮動
#: （NVDA 1 月最後一個週日：2026-01-25 vs 2027-01-31），嚴格相等會把同一年判成不同年。
PERIOD_MATCH_TOLERANCE_DAYS = 10


def _add_years(value: date, years: int) -> date:
    year = value.year + years
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return date(year, value.month, day)


@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    """一個會計期間。**`end` 是身分**；`label` 只是結束年命名的呈現慣例。"""

    end: date
    kind: str = "fiscal_year"

    def __post_init__(self) -> None:
        if self.kind not in FISCAL_PERIOD_KINDS:
            raise ContractViolation(
                f"FiscalPeriod.kind 未登記：{self.kind!r}；已知 {FISCAL_PERIOD_KINDS}")
        if not isinstance(self.end, date) or isinstance(self.end, datetime):
            raise ContractViolation("FiscalPeriod.end 必須是 date")

    @property
    def label(self) -> str:
        return f"FY{self.end.year}"

    @property
    def start(self) -> date:
        return _add_years(self.end, -1) + timedelta(days=1)

    def same_as(self, other: "FiscalPeriod", *,
                tolerance_days: int = PERIOD_MATCH_TOLERANCE_DAYS) -> bool:
        return (self.kind == other.kind
                and abs((self.end - other.end).days) <= tolerance_days)

    def shifted(self, years: int) -> "FiscalPeriod":
        return FiscalPeriod(end=_add_years(self.end, years), kind=self.kind)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "label": self.label,
                "start": self.start.isoformat(), "end": self.end.isoformat()}


# ---------------------------------------------------------------------------
# 1. 封閉字彙
# ---------------------------------------------------------------------------

#: 會計口徑。`not_applicable`＝這個量沒有口徑之分（營收）；`unverified`＝provider 沒宣告、
#: 也沒能用一手數字核對出來——**不得**與任何口徑相減。
ACCOUNTING_BASES: tuple[str, ...] = ("gaap", "non_gaap", "not_applicable", "unverified")

#: 假設的知識種類。**與 read model 的 `Basis` 字彙同名同義**（`tests` 斷言它是子集）：
#: `observation`＝值直接取自同期觀測；`heuristic_proxy`＝機械規則（如「沿用上一年」）；
#: `session_judgment`＝session／LLM 的判斷。刻意沒有 `deterministic`——輸入假設不會是
#: 確定性事實，確定性的是橋的算術。
ASSUMPTION_BASES: tuple[str, ...] = ("observation", "heuristic_proxy", "session_judgment")

#: 由弱到強的次序，用來算 `input_dependency`（最弱輸入）。
_BASIS_STRENGTH: Mapping[str, int] = {"session_judgment": 0, "heuristic_proxy": 1, "observation": 2}


def weakest_basis(bases: Sequence[str]) -> str | None:
    known = [b for b in bases if b in _BASIS_STRENGTH]
    if not known:
        return None
    return min(known, key=lambda b: _BASIS_STRENGTH[b])


@dataclass(frozen=True, slots=True)
class DriverSpec:
    unit: str
    scope_kind: str            # segment_or_total／component／total
    description: str
    lower: float | None = None
    upper: float | None = None


TOTAL_SCOPE = "total"

#: **contract，不是 taxonomy**：每個 driver 對應 `bridge.py` 的一段算術。
ASSUMPTION_DRIVERS: Mapping[str, DriverSpec] = {
    "revenue_growth": DriverSpec(
        "ratio", "segment_or_total",
        "基期營收成長率；scope 是分部名稱或 total（兩者不得並存）", lower=-1.0, upper=5.0),
    "operating_margin_delta": DriverSpec(
        "ratio", "component",
        "相對基期營益率的變化量（小數，+0.025 ＝ +2.5 個百分點）；scope 是成分標籤（mix／utilization／pricing…），可多條相加",
        lower=-1.0, upper=1.0),
    "interest_and_other_net": DriverSpec(
        "currency", "total", "利息與其他（收益）費用淨額，絕對金額（正值＝費用）"),
    "tax_rate": DriverSpec("ratio", "total", "有效稅率（小數）", lower=-1.0, upper=1.0),
    "nci_attribution": DriverSpec(
        "currency", "total", "歸屬母公司前的非控制權益調整，絕對金額（正值＝加回母公司）"),
    "diluted_shares": DriverSpec("shares", "total", "稀釋加權平均股數（絕對股數）", lower=0.0),
}

COMPARISON_STATUSES: tuple[str, ...] = (
    "comparable", "internal_missing", "consensus_missing",
    "incompatible_period", "incompatible_basis", "incompatible_unit",
)


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractViolation(f"{label} 必須是數值：{value!r}")
    if not math.isfinite(float(value)):
        raise ContractViolation(f"{label} 必須是有限數：{value!r}")
    return float(value)


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractViolation(f"{label} 必須是非空字串")
    return value


# ---------------------------------------------------------------------------
# 2. OperatingAssumption
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OperatingAssumption:
    """StockBot 對某個未來 driver 的**明示**假設。

    ⚠ 它不是事實。`basis` 說它是哪一種知識；`rationale` 說為什麼；`evidence_refs` 指回
    ResearchContext／Engine C 的證據；`created_at` 決定 as-of 視角下它存不存在。
    """

    assumption_id: str
    company_id: str
    ticker: str
    period: FiscalPeriod
    driver: str
    scope: str
    value: float
    unit: str
    basis: str
    rationale: str
    evidence_refs: tuple[str, ...]
    created_at: datetime
    author: str = "session"
    accounting_basis: str = "not_applicable"
    supersedes_id: str | None = None
    retracted: bool = False

    def __post_init__(self) -> None:
        _nonempty(self.assumption_id, "OperatingAssumption.assumption_id")
        if not self.assumption_id.startswith("oa_"):
            raise ContractViolation("assumption_id 必須以 oa_ 開頭（由 new_assumption_id 產生）")
        _nonempty(self.company_id, "OperatingAssumption.company_id")
        _nonempty(self.ticker, "OperatingAssumption.ticker")
        spec = ASSUMPTION_DRIVERS.get(self.driver)
        if spec is None:
            raise ContractViolation(
                f"driver 未登記：{self.driver!r}；已知 {sorted(ASSUMPTION_DRIVERS)}——"
                "driver 是 contract，多一個就要多一段橋的算術")
        if self.unit != spec.unit:
            raise ContractViolation(
                f"driver {self.driver} 的單位必須是 {spec.unit!r}，收到 {self.unit!r}")
        _nonempty(self.scope, "OperatingAssumption.scope")
        if spec.scope_kind == "total" and self.scope != TOTAL_SCOPE:
            raise ContractViolation(f"driver {self.driver} 的 scope 只能是 {TOTAL_SCOPE!r}")
        if self.basis not in ASSUMPTION_BASES:
            raise ContractViolation(
                f"basis 未登記：{self.basis!r}；已知 {ASSUMPTION_BASES}")
        if self.accounting_basis not in ACCOUNTING_BASES:
            raise ContractViolation(f"accounting_basis 未登記：{self.accounting_basis!r}")
        value = _finite(self.value, "OperatingAssumption.value")
        if spec.lower is not None and value < spec.lower:
            raise ContractViolation(f"{self.driver}={value} 低於下限 {spec.lower}")
        if spec.upper is not None and value > spec.upper:
            raise ContractViolation(f"{self.driver}={value} 高於上限 {spec.upper}")
        _nonempty(self.rationale, "OperatingAssumption.rationale")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ContractViolation("created_at 必須是帶時區的 datetime")
        if not self.retracted and not self.evidence_refs:
            raise ContractViolation(
                "OperatingAssumption 必須至少引用一條證據——沒有 provenance 的假設不得存在（INV-6）")
        if any(not isinstance(r, str) or not r.strip() for r in self.evidence_refs):
            raise ContractViolation("evidence_refs 每一項必須是非空字串")

    @property
    def key(self) -> tuple[str, str]:
        return (self.driver, self.scope)

    @property
    def created_on(self) -> date:
        return self.created_at.date()


# ---------------------------------------------------------------------------
# 3. Engine C 觀測（由 provider 唯讀取出；這裡只定型別）
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FiscalYearActuals:
    """某個**已報告**會計年度的損益骨架。全部來自 Engine C 人工 ledger（`fiscal_year_results`）。

    `gaap`／`non_gaap` 是印在財報／新聞稿上的數字（自由鍵，但橋只讀固定幾個）；
    `exit_quarter` 是最後一季的 run-rate 原料，明標為季度。
    """

    period: FiscalPeriod
    currency: str
    revenue: float
    segment_revenue: Mapping[str, float] | None
    gaap: Mapping[str, float]
    non_gaap: Mapping[str, float] | None
    evidence: tuple[EvidenceRef, ...]
    exit_quarter: Mapping[str, Any] | None = None
    source_filed_at: date | None = None
    recorded_at: datetime | None = None
    observation_id: str | None = None

    def __post_init__(self) -> None:
        _nonempty(self.currency, "FiscalYearActuals.currency")
        if _finite(self.revenue, "FiscalYearActuals.revenue") <= 0:
            raise ContractViolation("FiscalYearActuals.revenue 必須為正")
        if not self.evidence:
            raise ContractViolation("FiscalYearActuals 必須帶 evidence（INV-6）")
        if self.segment_revenue is not None:
            for name, value in self.segment_revenue.items():
                _finite(value, f"segment_revenue[{name}]")
        for name, block in (("gaap", self.gaap), ("non_gaap", self.non_gaap)):
            if block is None:
                continue
            for key, value in block.items():
                if value is not None:
                    _finite(value, f"{name}.{key}")

    def block(self, basis: str) -> Mapping[str, float] | None:
        if basis == "gaap":
            return self.gaap
        if basis == "non_gaap":
            return self.non_gaap
        return None

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(r.ref for r in self.evidence)


@dataclass(frozen=True, slots=True)
class ConsensusEstimate:
    """一筆會計期間別的分析師共識（Engine C `consensus_estimates`）。`value is None`＝缺料。"""

    metric: str
    period: FiscalPeriod
    value: float | None
    source: str
    evidence: tuple[EvidenceRef, ...]
    low: float | None = None
    high: float | None = None
    analyst_count: int | None = None
    year_ago_actual: float | None = None
    growth: float | None = None
    currency: str | None = None
    captured_at: date | None = None
    fetched_at: datetime | None = None
    relative_label: str | None = None

    def __post_init__(self) -> None:
        if self.metric not in ("eps", "revenue"):
            raise ContractViolation(f"ConsensusEstimate.metric 未登記：{self.metric!r}")
        if not self.evidence:
            raise ContractViolation("ConsensusEstimate 必須帶 evidence（INV-6）")

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(r.ref for r in self.evidence)


@dataclass(frozen=True, slots=True)
class GuidanceObservation:
    """公司公開指引（Engine C `company_guidance`）。它是「公司說了什麼」，不是本系統的假設。"""

    period_label: str
    period_kind: str
    period_end: date | None
    basis: str
    values: Mapping[str, float]
    issued_at: date | None
    evidence: tuple[EvidenceRef, ...]
    observation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ContractViolation("GuidanceObservation 必須帶 evidence（INV-6）")

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(r.ref for r in self.evidence)


# ---------------------------------------------------------------------------
# 4. 模型輸出
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BridgeStep:
    """橋上的一格。`kind`：observation（基期觀測）／assumption（輸入假設）／derived（算出）。"""

    key: str
    label: str
    kind: str
    value: float | None
    unit: str
    basis: str                       # observation／heuristic_proxy／session_judgment／deterministic／none
    formula: str | None = None
    assumption_ids: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    reason: str | None = None
    scope: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("observation", "assumption", "derived"):
            raise ContractViolation(f"BridgeStep.kind 未登記：{self.kind!r}")
        if self.value is None and self.basis != "none":
            raise ContractViolation(f"BridgeStep[{self.key}] 沒有值就沒有 basis（missing != zero）")
        if self.value is not None and self.basis == "none":
            raise ContractViolation(f"BridgeStep[{self.key}] 有值必須說出知識種類")
        if self.value is not None:
            _finite(self.value, f"BridgeStep[{self.key}].value")


@dataclass(frozen=True, slots=True)
class ModeledMetric:
    """一個內部估計。**沒有 naked number**：值、期間、單位、口徑、公式、依賴全在一起。"""

    metric: str
    period: FiscalPeriod
    value: float | None
    unit: str
    accounting_basis: str
    calculation: str = "deterministic"
    input_dependency: str | None = None    # 最弱輸入假設的 basis；None＝沒有值
    formula: str | None = None
    assumption_ids: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.accounting_basis not in ACCOUNTING_BASES:
            raise ContractViolation(f"ModeledMetric.accounting_basis 未登記：{self.accounting_basis!r}")
        if self.value is not None:
            _finite(self.value, f"ModeledMetric[{self.metric}].value")
            if self.input_dependency is None:
                raise ContractViolation(
                    f"ModeledMetric[{self.metric}] 有值就必須說出輸入依賴的知識種類")
        elif self.input_dependency is not None:
            raise ContractViolation(f"ModeledMetric[{self.metric}] 沒有值就沒有輸入依賴")

    @property
    def is_known(self) -> bool:
        return self.value is not None


@dataclass(frozen=True, slots=True)
class Sensitivity:
    """一條假設動一格，輸出動多少。純確定性微擾，不是機率、不是情境。"""

    assumption_id: str
    driver: str
    scope: str
    bump: float
    bump_unit: str                      # absolute_ratio（+0.01）／relative（×1.01）
    delta_revenue: float | None
    delta_operating_income: float | None
    delta_eps: float | None
    eps_relative: float | None


@dataclass(frozen=True, slots=True)
class ExpectationComparison:
    """內部估計 vs 共識——**只在 `status == "comparable"` 時有數字**。"""

    metric: str
    status: str
    internal_period: FiscalPeriod | None
    consensus_period: FiscalPeriod | None
    internal: float | None
    consensus: float | None
    absolute_gap: float | None
    relative_gap: float | None
    unit: str | None
    accounting_basis_internal: str | None
    accounting_basis_consensus: str | None
    analyst_count: int | None
    consensus_captured_at: date | None
    reason: str | None
    assumption_ids: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    consensus_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in COMPARISON_STATUSES:
            raise ContractViolation(f"ExpectationComparison.status 未登記：{self.status!r}")
        if self.status != "comparable" and (self.absolute_gap is not None or self.relative_gap is not None):
            raise ContractViolation(
                f"ExpectationComparison[{self.metric}] status={self.status} 不得帶 gap 數字——不能硬減")
        if self.status == "comparable" and (self.internal is None or self.consensus is None):
            raise ContractViolation("comparable 必須兩邊都有值")


@dataclass(frozen=True, slots=True)
class AssumptionSelection:
    """as-of／supersede／證據解析後的計數（INV-3：每個 filter 都能報 input／accepted／filtered／reasons）。"""

    input_count: int
    accepted_count: int
    reasons: Mapping[str, int]
    rejected: tuple[tuple[str, str], ...] = ()   # (assumption_id, reason)

    @property
    def filtered_count(self) -> int:
        return self.input_count - self.accepted_count


@dataclass(frozen=True, slots=True)
class FundamentalModelResult:
    """一次模型執行的完整輸出——read model 只選取，不重算。"""

    company_id: str
    ticker: str
    as_of: date | None
    target_period: FiscalPeriod | None
    base_period: FiscalPeriod | None
    accounting_basis: str
    status: str                             # available／partial／missing
    reason: str | None
    metrics: Mapping[str, ModeledMetric]
    steps: tuple[BridgeStep, ...]
    assumptions: tuple[OperatingAssumption, ...]
    selection: AssumptionSelection
    sensitivities: tuple[Sensitivity, ...]
    comparisons: Mapping[str, ExpectationComparison]
    consensus: tuple[ConsensusEstimate, ...]
    guidance: tuple[GuidanceObservation, ...]
    base_actuals: FiscalYearActuals | None
    #: 每筆共識的口徑核實結果，key＝`f"{metric}:{period_end}"`（見 `compare.verify_consensus_basis`）。
    consensus_bases: Mapping[str, str] = field(default_factory=dict)
    model_version: str = MODEL_VERSION
    bridge_version: str = BRIDGE_VERSION
    digest: str = ""
    warnings: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status not in ("available", "partial", "missing"):
            raise ContractViolation(f"FundamentalModelResult.status 未登記：{self.status!r}")
        if self.accounting_basis not in ACCOUNTING_BASES:
            raise ContractViolation(f"accounting_basis 未登記：{self.accounting_basis!r}")

    def metric(self, name: str) -> ModeledMetric | None:
        return self.metrics.get(name)


__all__ = [
    "ACCOUNTING_BASES", "ASSUMPTION_BASES", "ASSUMPTION_DRIVERS", "BRIDGE_VERSION",
    "COMPARISON_STATUSES", "FISCAL_PERIOD_KINDS", "MODEL_VERSION",
    "PERIOD_MATCH_TOLERANCE_DAYS", "TOTAL_SCOPE", "AssumptionSelection", "BridgeStep",
    "ConsensusEstimate", "DriverSpec", "ExpectationComparison", "FiscalPeriod",
    "FiscalYearActuals", "FundamentalModelResult", "GuidanceObservation", "ModeledMetric",
    "OperatingAssumption", "Sensitivity", "weakest_basis",
]
