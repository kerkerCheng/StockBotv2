"""Valuation Model v1 的型別契約。**只有型別與驗證，零外部相依。**

## 這一層回答什麼

> 根據我們自己算出的內部基本面（`alpha/fundamental`），加上一條**明示**的估值判斷，
> 這門生意的 fair value 是多少；跟現價差多少。

它刻意**不**回答：預期報酬、horizon、進場價、買賣、機率加權情境——那些是 Step 2 以後。

## 兩個一等公民

| 型別 | 誰擁有它 | 可變性 |
|---|---|---|
| `ValuationAssumption` | A3 研究判斷（private append-only ledger） | 可重算；改假設＝append 新紀錄 |
| `ValuationResult`／`FairValueGap` | A3 模型輸出 | 由 `model.py` 確定性算出 |

## 三條在型別層強制的規則

1. **估值假設必須帶 basis、rationale、evidence、created_at、accounting_basis。** 它與
   `OperatingAssumption` 是同一套 epistemic system（同一組 basis 字彙、同一組 ref 角色、
   同一種 append-only／as-of 語意），只是**不是橋的 driver**——倍數不是財務橋的一段算術，
   所以住自己的型別與 ledger，而不是塞進 `ASSUMPTION_DRIVERS`。
2. **method 與 parameter 是封閉字彙（contract）。** 每個 method 對應 `model.py` 的一段算術；
   多一個 method 就要多一段算術，打開它是改程式不是改設定。
3. **沒有 hidden default multiple。** `ValuationResult` 只在 ledger 裡真的有一條生效的
   `ValuationAssumption` 時才有值；沒有就是 `missing`＋理由，不得由程式或 LLM 補一個數。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from ..contracts import EvidenceRef
from ..errors import ContractViolation
from ..fundamental.contracts import (
    ACCOUNTING_BASES, ASSUMPTION_BASES, ASSUMPTION_REF_ROLES, CONSENSUS_REF_PREFIX,
    PROVENANCE_SEMANTICS, TOTAL_SCOPE, AssumptionSelection, FiscalPeriod, ModeledMetric,
    weakest_basis,
)

MODEL_VERSION = "valuation-model/v1"

# ---------------------------------------------------------------------------
# 0. 封閉字彙
# ---------------------------------------------------------------------------

#: **contract，不是 taxonomy**：每個 method 對應 `model.py` 的一段算術。
#: v1 只有 forward earnings multiple——audit（2026-09-06）實測：內部可靠的 forward metric 只有
#: FY 目標期間的稀釋 EPS；沒有內部 FCF、D&A、EBITDA、資本支出或營運資金，所以 EV/EBITDA、
#: DCF、reverse DCF 都沒有資料可餵，**不為了完整硬做**。
METHOD_FORWARD_EARNINGS_MULTIPLE = "forward_earnings_multiple"
VALUATION_METHODS: tuple[str, ...] = (METHOD_FORWARD_EARNINGS_MULTIPLE,)


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    unit: str
    description: str
    lower: float | None = None
    upper: float | None = None


#: method → 它需要的 parameter（`ValuationAssumption.parameter`）。目前一個 method 一個 parameter。
METHOD_PARAMETERS: Mapping[str, Mapping[str, ParameterSpec]] = {
    METHOD_FORWARD_EARNINGS_MULTIPLE: {
        "target_pe": ParameterSpec(
            "multiple", "目標本益比（倍）；套用在**同一目標會計期間、同一口徑**的內部稀釋 EPS 上",
            lower=0.0, upper=500.0),
    },
}

#: method → 它消費的內部指標與該指標的單位。
METHOD_FUNDAMENTAL_INPUT: Mapping[str, tuple[str, str]] = {
    METHOD_FORWARD_EARNINGS_MULTIPLE: ("eps", "currency_per_share"),
}

#: fair value 與 gap 的公式字串（**唯一定義處**；read model 只抄，不得自己再寫一份）。
FAIR_VALUE_FORMULA: Mapping[str, str] = {
    METHOD_FORWARD_EARNINGS_MULTIPLE: "fair_value = internal_eps[target_period] × target_pe",
}
GAP_FORMULA = "absolute_gap = fair_value − current_price；relative_gap = fair_value / current_price − 1"
IMPLIED_MULTIPLE_FORMULA = "implied_multiple_at_price = current_price / internal_eps[target_period]"

#: 估值假設的口徑只能是 GAAP 或 non-GAAP——倍數套在哪一種 EPS 上是身分的一部分。
VALUATION_ACCOUNTING_BASES: tuple[str, ...] = ("gaap", "non_gaap")

#: **Step 2（2026-09-06）補的 value-date 語意：fair value 這個數字是「哪一天」的值。**
#: Step 1 audit 實測：v1 契約只有 `target_period`（EPS 屬於哪個會計期間）與 `as_of`（知識視角），
#: 答不出「223.60 是今天的 fair value（A）還是某個未來日期的 target value（B）」——兩種讀法算術相同、
#: 報酬語意完全不同，所以它必須是估值判斷自己宣告的封閉字彙，不得由 renderer 或文字註解猜。
#: - `spot`：fair value 是**估值視角日**（as_of 或 today）的值——「今天就該以 target_pe × 目標期間 EPS 交易」。
#: - `target_period_end`：fair value 是**目標會計期間結束日**的值——「到 FY 期末，市場會以 target_pe 定價那一年的 EPS」。
#: 未宣告（舊紀錄）＝`unspecified`：fair value 照算（Step 1 語意不變），但**報酬層拒算**（沒有時點就沒有 horizon）。
VALUE_DATE_SPOT = "spot"
VALUE_DATE_TARGET_PERIOD_END = "target_period_end"
VALUE_DATE_CONVENTIONS: tuple[str, ...] = (VALUE_DATE_SPOT, VALUE_DATE_TARGET_PERIOD_END)
VALUE_DATE_UNSPECIFIED = "unspecified"
VALUE_DATE_SEMANTICS: tuple[str, ...] = VALUE_DATE_CONVENTIONS + (VALUE_DATE_UNSPECIFIED,)
#: value_date 的機器可讀定義（**唯一定義處**；read model 只抄）。
VALUE_DATE_FORMULA: Mapping[str, str] = {
    VALUE_DATE_SPOT: "value_date = 估值視角日（as_of，否則 today）——fair value 是「現在」的值",
    VALUE_DATE_TARGET_PERIOD_END: "value_date = target_period.end——fair value 是目標會計期間結束日的值",
    VALUE_DATE_UNSPECIFIED: "value_date = None——估值假設未宣告 value_date_convention，時點語意未知（不猜）",
}

VALUATION_STATUSES: tuple[str, ...] = ("available", "missing")
GAP_STATUSES: tuple[str, ...] = (
    "comparable", "fair_value_missing", "price_missing", "incompatible_unit", "unverified_unit",
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
# 1. ValuationAssumption
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ValuationAssumption:
    """StockBot 對某個估值參數的**明示**判斷（例：FY2027 non-GAAP 目標本益比 25x）。

    ⚠ 它不是觀測、不是 LLM runtime 輸出。`basis` 說它是哪一種知識；`rationale` 說為什麼；
    `evidence_refs`＋`dependency_roles` 指回 ResearchContext／Engine C 的證據並宣告角色
    （supporting／calibration／comparison；**同期共識與市場倍數只能是 calibration**）；
    `created_at` 決定 as-of 視角下它存不存在；`supersedes_id`／`retracted` 是 append-only 的
    改值與撤回語意（與 `OperatingAssumption` 完全同一套）。

    與 `OperatingAssumption` 的差別只有三處：id 前綴 `va_`、`driver` 換成 `method`＋`parameter`、
    `accounting_basis` 必填且只能是 gaap／non_gaap（倍數套在哪種 EPS 上是身分）。
    """

    assumption_id: str
    company_id: str
    ticker: str
    period: FiscalPeriod
    method: str
    parameter: str
    value: float
    unit: str
    basis: str
    rationale: str
    evidence_refs: tuple[str, ...]
    created_at: datetime
    accounting_basis: str
    scope: str = TOTAL_SCOPE
    author: str = "session"
    supersedes_id: str | None = None
    retracted: bool = False
    dependency_roles: Mapping[str, str] = field(default_factory=dict)
    review_conditions: tuple[Any, ...] = ()
    provenance_semantics: str = "v2"
    #: Step 2：這條倍數判斷算出來的 fair value 是哪一天的值（`VALUE_DATE_CONVENTIONS`）。**沒有預設**：
    #: 舊紀錄是 None（＝unspecified），要補語意就 append 一筆新紀錄 supersede 它。
    value_date_convention: str | None = None

    def __post_init__(self) -> None:
        _nonempty(self.assumption_id, "ValuationAssumption.assumption_id")
        if not self.assumption_id.startswith("va_"):
            raise ContractViolation("assumption_id 必須以 va_ 開頭（由 new_valuation_assumption_id 產生）")
        _nonempty(self.company_id, "ValuationAssumption.company_id")
        _nonempty(self.ticker, "ValuationAssumption.ticker")
        params = METHOD_PARAMETERS.get(self.method)
        if params is None:
            raise ContractViolation(
                f"valuation method 未登記：{self.method!r}；已知 {list(VALUATION_METHODS)}——"
                "method 是 contract，多一個就要多一段算術")
        spec = params.get(self.parameter)
        if spec is None:
            raise ContractViolation(
                f"method {self.method} 沒有 parameter {self.parameter!r}；已知 {sorted(params)}")
        if self.unit != spec.unit:
            raise ContractViolation(f"{self.method}.{self.parameter} 的單位必須是 {spec.unit!r}，收到 {self.unit!r}")
        if self.scope != TOTAL_SCOPE:
            raise ContractViolation(f"v1 估值假設的 scope 只能是 {TOTAL_SCOPE!r}")
        if self.basis not in ASSUMPTION_BASES:
            raise ContractViolation(f"basis 未登記：{self.basis!r}；已知 {ASSUMPTION_BASES}")
        if self.accounting_basis not in VALUATION_ACCOUNTING_BASES:
            raise ContractViolation(
                f"估值假設的 accounting_basis 必須是 {VALUATION_ACCOUNTING_BASES}，收到 {self.accounting_basis!r}"
                "——倍數套在 GAAP 還是 non-GAAP EPS 上是身分，不得留空或 unverified")
        value = _finite(self.value, "ValuationAssumption.value")
        if spec.lower is not None and value < spec.lower:
            raise ContractViolation(f"{self.parameter}={value} 低於下限 {spec.lower}")
        if spec.upper is not None and value > spec.upper:
            raise ContractViolation(f"{self.parameter}={value} 高於上限 {spec.upper}")
        _nonempty(self.rationale, "ValuationAssumption.rationale")
        if self.value_date_convention is not None and self.value_date_convention not in VALUE_DATE_CONVENTIONS:
            raise ContractViolation(
                f"value_date_convention 未登記：{self.value_date_convention!r}；已知 {VALUE_DATE_CONVENTIONS}"
                "——fair value 是哪一天的值是封閉字彙，不得自由填寫")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ContractViolation("created_at 必須是帶時區的 datetime")
        if not self.retracted and not self.evidence_refs:
            raise ContractViolation(
                "ValuationAssumption 必須至少引用一條證據——沒有 provenance 的估值判斷不得存在（INV-6）")
        if any(not isinstance(r, str) or not r.strip() for r in self.evidence_refs):
            raise ContractViolation("evidence_refs 每一項必須是非空字串")
        if self.provenance_semantics not in PROVENANCE_SEMANTICS:
            raise ContractViolation(f"provenance_semantics 未登記：{self.provenance_semantics!r}")
        for ref, role in self.dependency_roles.items():
            if role not in ASSUMPTION_REF_ROLES:
                raise ContractViolation(f"dependency_roles[{ref}] 未登記：{role!r}；已知 {ASSUMPTION_REF_ROLES}")
            if ref not in self.evidence_refs:
                raise ContractViolation(f"dependency_roles 指到不在 evidence_refs 的 ref：{ref!r}")
            if role == "supporting" and ref.startswith(CONSENSUS_REF_PREFIX):
                raise ContractViolation(
                    f"同期共識 {ref!r} 不得作為估值假設的 supporting evidence——那是 provenance 循環；"
                    "請改列 calibration_refs")
        if self.provenance_semantics == "v2" and not self.retracted:
            missing = [r for r in self.evidence_refs if r not in self.dependency_roles]
            if missing:
                raise ContractViolation(f"v2 估值假設每條 ref 都必須宣告角色；缺：{missing[:3]}")
            if not any(role == "supporting" for role in self.dependency_roles.values()):
                raise ContractViolation("估值假設至少要有一條 supporting evidence（calibration 不算支持）")
        from ..refresh.contracts import ReviewCondition

        if any(not isinstance(c, ReviewCondition) for c in self.review_conditions):
            raise ContractViolation("review_conditions 每一項必須是 ReviewCondition")

    # ---- 與 OperatingAssumption 同形的介面（讓 select_assumptions／refresh 攤平器可以共用）----
    @property
    def driver(self) -> str:
        """`select_assumptions` 與 refresh 的 driver 相容欄位：`method.parameter`。"""
        return f"{self.method}.{self.parameter}"

    @property
    def key(self) -> tuple[str, str]:
        return (self.driver, self.scope)

    @property
    def created_on(self) -> date:
        return self.created_at.date()

    def role_of(self, ref: str) -> str:
        declared = self.dependency_roles.get(ref)
        if declared is not None:
            return declared
        if ref.startswith(CONSENSUS_REF_PREFIX):
            return "calibration"
        return "legacy_unclassified"

    @property
    def supporting_refs(self) -> tuple[str, ...]:
        return tuple(r for r in self.evidence_refs if self.role_of(r) in ("supporting", "legacy_unclassified"))

    @property
    def calibration_refs(self) -> tuple[str, ...]:
        return tuple(r for r in self.evidence_refs if self.role_of(r) == "calibration")


# ---------------------------------------------------------------------------
# 2. 模型輸出
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ValuationStep:
    """估值算式上的一格：`fundamental_input`（內部指標）／`assumption`（估值假設）／`derived`（算出）。"""

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
    input_dependency: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("fundamental_input", "assumption", "derived"):
            raise ContractViolation(f"ValuationStep.kind 未登記：{self.kind!r}")
        if self.value is None and self.basis != "none":
            raise ContractViolation(f"ValuationStep[{self.key}] 沒有值就沒有 basis（missing != zero）")
        if self.value is not None and self.basis == "none":
            raise ContractViolation(f"ValuationStep[{self.key}] 有值必須說出知識種類")
        if self.value is not None:
            _finite(self.value, f"ValuationStep[{self.key}].value")


@dataclass(frozen=True, slots=True)
class FundamentalInput:
    """估值消費的內部指標——**照抄** `ModeledMetric`，不重算。"""

    metric: str
    period: FiscalPeriod
    value: float | None
    unit: str
    accounting_basis: str
    currency: str | None
    input_dependency: str | None
    formula: str | None
    assumption_ids: tuple[str, ...]
    observation_refs: tuple[str, ...]
    reason: str | None = None

    @classmethod
    def from_metric(cls, metric: ModeledMetric, *, currency: str | None) -> "FundamentalInput":
        return cls(metric=metric.metric, period=metric.period, value=metric.value, unit=metric.unit,
                   accounting_basis=metric.accounting_basis, currency=currency,
                   input_dependency=metric.input_dependency, formula=metric.formula,
                   assumption_ids=tuple(metric.assumption_ids), observation_refs=tuple(metric.observation_refs),
                   reason=metric.reason)

    @property
    def is_known(self) -> bool:
        return self.value is not None


@dataclass(frozen=True, slots=True)
class CurrentPrice:
    """Engine C 的現價快照（A2 觀測；估值層只讀）。`unit` 是報價單位（可能是 minor unit，如 GBp）。"""

    value: float | None
    bar_date: date | None
    unit: str | None
    evidence_refs: tuple[str, ...]
    reason: str | None = None

    @property
    def is_known(self) -> bool:
        return self.value is not None


@dataclass(frozen=True, slots=True)
class FairValueGap:
    """fair value 與現價的差——**只在同單位、兩邊都有值時有數字**。

    ⚠ 它是「fair value 與現價差多少」，**不是** expected return、不是 upside forecast、
    不是 entry signal：horizon／return semantics 是 Step 2，本型別刻意沒有那些欄位。
    """

    status: str
    absolute_gap: float | None
    relative_gap: float | None
    implied_multiple_at_price: float | None
    unit: str | None
    reason: str | None
    price_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in GAP_STATUSES:
            raise ContractViolation(f"FairValueGap.status 未登記：{self.status!r}")
        if self.status != "comparable" and (self.absolute_gap is not None or self.relative_gap is not None):
            raise ContractViolation(f"FairValueGap status={self.status} 不得帶 gap 數字——不能硬減")
        if self.status == "comparable" and (self.absolute_gap is None or self.relative_gap is None):
            raise ContractViolation("comparable 必須兩個 gap 都有值")

    @property
    def is_known(self) -> bool:
        return self.status == "comparable"


@dataclass(frozen=True, slots=True)
class FairValueSensitivity:
    """一條輸入判斷動一格，fair value 動多少。純確定性微擾，不是機率、不是情境。"""

    assumption_id: str
    driver: str
    scope: str
    bump: float
    bump_unit: str
    delta_fair_value: float | None
    fair_value_relative: float | None


@dataclass(frozen=True, slots=True)
class ValuationResult:
    """一次估值執行的完整輸出——read model 只選取，不重算。

    `fair_value` 有值 ⇒ `calculation="deterministic"` 且 `input_dependency` 是所有輸入判斷
    （內部 EPS 的 input_dependency ＋ 估值假設的 basis）中最弱的那一種。

    Step 2 補的兩個欄位回答「這個數字是哪一天的值」：`value_date_semantics`（spot／target_period_end／
    unspecified，抄自生效估值假設的 `value_date_convention`）與 `value_date`（依 `VALUE_DATE_FORMULA` 導出的
    日期；unspecified 時是 None）。**它們不改 fair value 的算術**，只讓時點語意 machine-readable。
    """

    company_id: str
    ticker: str
    as_of: date | None
    method: str | None
    status: str                                    # available／missing
    reason: str | None
    target_period: FiscalPeriod | None
    accounting_basis: str | None
    fundamental_input: FundamentalInput | None
    assumptions: tuple[ValuationAssumption, ...]
    selection: AssumptionSelection                 # 與營運假設同一個計數型別（INV-3）
    fair_value: float | None
    currency: str | None
    formula: str | None
    input_dependency: str | None
    steps: tuple[ValuationStep, ...]
    current_price: CurrentPrice
    gap: FairValueGap
    sensitivities: tuple[FairValueSensitivity, ...] = ()
    #: 「fair value 裡多少是算術、多少是判斷」的機器可讀分解（純選取／計數，不是新判斷）。
    epistemics: Mapping[str, Any] = field(default_factory=dict)
    calculation: str = "deterministic"
    model_version: str = MODEL_VERSION
    digest: str = ""
    warnings: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)
    value_date: date | None = None
    value_date_semantics: str = VALUE_DATE_UNSPECIFIED

    def __post_init__(self) -> None:
        if self.status not in VALUATION_STATUSES:
            raise ContractViolation(f"ValuationResult.status 未登記：{self.status!r}")
        if self.value_date_semantics not in VALUE_DATE_SEMANTICS:
            raise ContractViolation(f"ValuationResult.value_date_semantics 未登記：{self.value_date_semantics!r}")
        if self.value_date_semantics == VALUE_DATE_UNSPECIFIED and self.value_date is not None:
            raise ContractViolation("value_date_semantics=unspecified 不得帶 value_date（不猜時點）")
        if self.value_date_semantics != VALUE_DATE_UNSPECIFIED and self.value_date is None:
            raise ContractViolation(f"value_date_semantics={self.value_date_semantics} 必須有 value_date")
        if self.value_date is not None and (not isinstance(self.value_date, date) or isinstance(self.value_date, datetime)):
            raise ContractViolation("ValuationResult.value_date 必須是 date")
        if self.method is not None and self.method not in VALUATION_METHODS:
            raise ContractViolation(f"ValuationResult.method 未登記：{self.method!r}")
        if self.accounting_basis is not None and self.accounting_basis not in ACCOUNTING_BASES:
            raise ContractViolation(f"accounting_basis 未登記：{self.accounting_basis!r}")
        if self.status == "available":
            if self.fair_value is None or self.input_dependency is None or not self.formula:
                raise ContractViolation("available 的估值必須有 fair_value、input_dependency 與 formula")
            _finite(self.fair_value, "ValuationResult.fair_value")
        elif self.fair_value is not None or self.input_dependency is not None:
            raise ContractViolation("missing 的估值不得帶 fair_value 或 input_dependency（missing != zero）")

    @property
    def is_known(self) -> bool:
        return self.fair_value is not None

    @property
    def gap_formula(self) -> str:
        return GAP_FORMULA

    @property
    def implied_multiple_formula(self) -> str:
        return IMPLIED_MULTIPLE_FORMULA

    @property
    def assumption_ids(self) -> tuple[str, ...]:
        """fair value 依賴的**全部**判斷：內部指標的營運假設＋估值假設。"""
        ops = tuple(self.fundamental_input.assumption_ids) if self.fundamental_input else ()
        return ops + tuple(a.assumption_id for a in self.assumptions)

    @property
    def value_date_formula(self) -> str:
        return VALUE_DATE_FORMULA[self.value_date_semantics]


def combined_input_dependency(fundamental_dependency: str | None, assumptions: Sequence[ValuationAssumption]) -> str | None:
    """fair value 的輸入知識種類＝所有輸入中最弱的那一種。"""
    bases = [b for b in ([fundamental_dependency] + [a.basis for a in assumptions]) if b]
    return weakest_basis(bases)


__all__ = [
    "FAIR_VALUE_FORMULA", "GAP_FORMULA", "GAP_STATUSES", "IMPLIED_MULTIPLE_FORMULA",
    "METHOD_FORWARD_EARNINGS_MULTIPLE", "METHOD_FUNDAMENTAL_INPUT", "METHOD_PARAMETERS", "MODEL_VERSION",
    "VALUATION_ACCOUNTING_BASES", "VALUATION_METHODS", "VALUATION_STATUSES", "VALUE_DATE_CONVENTIONS",
    "VALUE_DATE_FORMULA", "VALUE_DATE_SEMANTICS", "VALUE_DATE_SPOT", "VALUE_DATE_TARGET_PERIOD_END",
    "VALUE_DATE_UNSPECIFIED", "CurrentPrice",
    "FairValueGap", "FairValueSensitivity", "FundamentalInput", "ParameterSpec", "ValuationAssumption",
    "ValuationResult", "ValuationStep", "combined_input_dependency",
]
