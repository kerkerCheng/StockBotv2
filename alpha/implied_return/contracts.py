"""Base-case Implied Return v1 的型別契約。**只有型別與驗證，零外部相依。**

## 這一層回答什麼

> 從**哪一天**（現價的 bar_date）到**哪一天**（明示的 horizon_end），在**什麼假設下**
> （內部 EPS 的營運假設＋估值倍數＋value-date 語意＋realization horizon），
> 現價走到 fair value 的 base-case 隱含**價格**報酬是多少；年化是多少。

它刻意**不**回答：機率加權的期望報酬（沒有 bull／base／bear 機率）、總報酬（沒有股利／分配預測）、
進場價、買賣、部位——名稱刻意叫 **implied return**，不叫 expected return：
「expected」在統計上是機率加權的期望值，本層沒有任何機率。

## 三個一等公民

| 型別 | 誰擁有它 | 可變性 |
|---|---|---|
| `HorizonAssumption` | A3 研究判斷（private append-only ledger） | 可重算；改 horizon＝append 新紀錄 |
| `ImpliedReturnResult` | A3 模型輸出 | 由 `model.py` 確定性算出 |
| 公式字串（`PRICE_RETURN_FORMULA` 等） | 本檔（唯一定義處） | read model 只抄 |

## 四條在型別層強制的規則

1. **horizon 是判斷，不是常數。** 「fair value 會在 2027-06-30 前被市場定價到」本身是一條需要
   basis／rationale／evidence／created_at 的判斷；沒有生效的 `HorizonAssumption` → return `missing`，
   不得偷用「12 個月」或「下一會計年度」。
2. **price return 與 total return 分開。** 沒有股利／分配預測就是 `total_return_status=not_modeled`，
   不得把 price return 冒充 total return。
3. **Missing != Zero。** 現價、fair value、value-date 語意、horizon 任一缺席 → `status=missing`＋理由，
   `price_return`／`annualized_price_return` 必須是 None。
4. **沒有 probability-weighted expected return 欄位。** 型別裡連插座都沒有——加上去就是打開契約。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from ..absence import check_absence_kind, default_absence_kind
from ..contracts import EvidenceRef
from ..errors import ContractViolation
from ..fundamental.contracts import (
    ASSUMPTION_BASES, ASSUMPTION_REF_ROLES, CONSENSUS_REF_PREFIX, PROVENANCE_SEMANTICS, TOTAL_SCOPE,
    AssumptionSelection, FiscalPeriod, weakest_basis,
)
from ..valuation.contracts import CurrentPrice

MODEL_VERSION = "implied-return-model/v1"

# ---------------------------------------------------------------------------
# 0. 封閉字彙與公式（唯一定義處）
# ---------------------------------------------------------------------------

#: 這個報酬是哪一種報酬——**contract**：每個 convention 對應 `model.py` 的一段算術。
RETURN_CONVENTION_BASE_CASE_PRICE = "base_case_implied_price_return"
RETURN_CONVENTIONS: tuple[str, ...] = (RETURN_CONVENTION_BASE_CASE_PRICE,)

#: horizon 的 driver 名稱（讓 `select_assumptions`／refresh 的 key 語意與其他假設同形）。
HORIZON_DRIVER = "realization_horizon"

HORIZON_START_FORMULA = "horizon_start = current_price.bar_date（報酬從這個價格所屬的交易日起算）"
HOLDING_PERIOD_FORMULA = ("holding_period_days = (horizon_end − horizon_start).days；"
                          "holding_period_years = holding_period_days / 365.25")
PRICE_RETURN_FORMULA = "price_return = fair_value / current_price − 1"
ANNUALIZED_RETURN_FORMULA = "annualized_price_return = (1 + price_return) ** (365.25 / holding_period_days) − 1"
DAYS_PER_YEAR = 365.25

#: value_date 與 horizon_end 的關係（機器可讀；不阻擋、只現形）。
ALIGNMENT_ALIGNED = "aligned"                              # horizon_end == value_date
ALIGNMENT_HORIZON_AFTER = "horizon_after_value_date"       # 市場在 value_date 之後才定價到那個值
ALIGNMENT_HORIZON_BEFORE = "horizon_before_value_date"     # 市場提前定價（在 value_date 之前就到）
ALIGNMENT_SPOT = "spot_value_realized_over_horizon"        # fair value 是「現在」的值；horizon 是收斂期
ALIGNMENTS: tuple[str, ...] = (ALIGNMENT_ALIGNED, ALIGNMENT_HORIZON_AFTER, ALIGNMENT_HORIZON_BEFORE, ALIGNMENT_SPOT)

RETURN_STATUSES: tuple[str, ...] = ("available", "missing")
#: total return 的 status：本層**沒有**股利／分配預測能力（Engine C 無此欄位、橋 v1 無配息假設），
#: 所以是 `not_modeled`（系統沒能力），不是 `missing`（有能力沒資料）。
TOTAL_RETURN_STATUSES: tuple[str, ...] = ("not_modeled",)


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


def _date(value: Any, label: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ContractViolation(f"{label} 必須是 date：{value!r}")
    return value


# ---------------------------------------------------------------------------
# 1. HorizonAssumption
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HorizonAssumption:
    """StockBot 對「fair value 何時會被市場定價到」的**明示**判斷（例：FY2027 fair value 於 2027-06-30 前實現）。

    ⚠ 它不是事實、不是常數、不是 renderer 的預設。與 `OperatingAssumption`／`ValuationAssumption` 同一套
    epistemic system：`basis`／`rationale`／`evidence_refs`＋`dependency_roles`／`created_at`／supersede／
    retract／`review_conditions`；**同一支選取器**（as-of、期間、supersede、證據解析）。

    `period` 是這條 horizon 服務的目標會計期間（＝估值的 target_period）：估值換期間，horizon 就是
    `other_period`，不沿用。`horizon_end` 是明示日期——不是「12 個月」這種相對量。
    """

    assumption_id: str
    company_id: str
    ticker: str
    period: FiscalPeriod
    horizon_end: date
    basis: str
    rationale: str
    evidence_refs: tuple[str, ...]
    created_at: datetime
    scope: str = TOTAL_SCOPE
    author: str = "session"
    supersedes_id: str | None = None
    retracted: bool = False
    dependency_roles: Mapping[str, str] = field(default_factory=dict)
    review_conditions: tuple[Any, ...] = ()
    provenance_semantics: str = "v2"

    def __post_init__(self) -> None:
        _nonempty(self.assumption_id, "HorizonAssumption.assumption_id")
        if not self.assumption_id.startswith("ha_"):
            raise ContractViolation("assumption_id 必須以 ha_ 開頭（由 new_horizon_assumption_id 產生）")
        _nonempty(self.company_id, "HorizonAssumption.company_id")
        _nonempty(self.ticker, "HorizonAssumption.ticker")
        _date(self.horizon_end, "HorizonAssumption.horizon_end")
        if self.scope != TOTAL_SCOPE:
            raise ContractViolation(f"v1 horizon 假設的 scope 只能是 {TOTAL_SCOPE!r}")
        if self.basis not in ASSUMPTION_BASES:
            raise ContractViolation(f"basis 未登記：{self.basis!r}；已知 {ASSUMPTION_BASES}")
        _nonempty(self.rationale, "HorizonAssumption.rationale")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ContractViolation("created_at 必須是帶時區的 datetime")
        if not self.retracted and self.horizon_end <= self.created_at.date():
            raise ContractViolation(
                f"horizon_end {self.horizon_end} 不晚於建立日 {self.created_at.date()}——"
                "寫下時就已經過去的 horizon 不是判斷（INV-2：每個等待都必須有未來的到期）")
        if not self.retracted and not self.evidence_refs:
            raise ContractViolation(
                "HorizonAssumption 必須至少引用一條證據——沒有 provenance 的 horizon 判斷不得存在（INV-6）")
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
                raise ContractViolation(f"同期共識 {ref!r} 不得作為 horizon 假設的 supporting evidence；請改列 calibration_refs")
        if self.provenance_semantics == "v2" and not self.retracted:
            missing = [r for r in self.evidence_refs if r not in self.dependency_roles]
            if missing:
                raise ContractViolation(f"v2 horizon 假設每條 ref 都必須宣告角色；缺：{missing[:3]}")
            if not any(role == "supporting" for role in self.dependency_roles.values()):
                raise ContractViolation("horizon 假設至少要有一條 supporting evidence（calibration 不算支持）")
        from ..refresh.contracts import ReviewCondition

        if any(not isinstance(c, ReviewCondition) for c in self.review_conditions):
            raise ContractViolation("review_conditions 每一項必須是 ReviewCondition")

    # ---- 與 OperatingAssumption 同形的介面（讓 select_assumptions／refresh 攤平器可以共用）----
    @property
    def driver(self) -> str:
        return HORIZON_DRIVER

    @property
    def key(self) -> tuple[str, str]:
        return (self.driver, self.scope)

    @property
    def created_on(self) -> date:
        return self.created_at.date()

    @property
    def value(self) -> date:
        """`assumption_changes` 等共用工具讀 `value`；horizon 的值就是日期本身。"""
        return self.horizon_end

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
class ReturnStep:
    """報酬算式上的一格：`price_input`（現價）／`valuation_input`（fair value 與 value date）／
    `horizon_input`（horizon 判斷）／`derived`（算出）。"""

    key: str
    label: str
    kind: str
    value: Any
    unit: str
    basis: str                       # observation／session_judgment／heuristic_proxy／deterministic／none
    formula: str | None = None
    assumption_ids: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    reason: str | None = None
    input_dependency: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("price_input", "valuation_input", "horizon_input", "derived"):
            raise ContractViolation(f"ReturnStep.kind 未登記：{self.kind!r}")
        if self.value is None and self.basis != "none":
            raise ContractViolation(f"ReturnStep[{self.key}] 沒有值就沒有 basis（missing != zero）")
        if self.value is not None and self.basis == "none":
            raise ContractViolation(f"ReturnStep[{self.key}] 有值必須說出知識種類")
        if isinstance(self.value, (int, float)) and not isinstance(self.value, bool):
            _finite(self.value, f"ReturnStep[{self.key}].value")


@dataclass(frozen=True, slots=True)
class ImpliedReturnResult:
    """一次 base-case implied return 執行的完整輸出——read model 只選取，不重算。

    `status="available"` ⇒ `price_return` 有值、`horizon_start`／`horizon_end`／`holding_period_days` 齊、
    `calculation="deterministic"`、`input_dependency`＝所有輸入判斷（fair value 的 input_dependency ＋ horizon
    的 basis）中最弱的那一種。`annualized_price_return` 只在 `holding_period_days ≥ 1` 時有值。
    `total_return_status` 恆為 `not_modeled`（本層沒有股利／分配預測能力）。

    ⚠ 型別裡刻意**沒有** probability_weighted／expected_return 欄位；也沒有 entry／required return／position。
    """

    company_id: str
    ticker: str
    as_of: date | None
    status: str                                    # available／missing
    reason: str | None
    return_convention: str
    current_price: CurrentPrice
    price_as_of: date | None
    fair_value: float | None
    fair_value_currency: str | None
    fair_value_as_of: date | None                  # fair value 是在哪個視角日算出的（估值的 as_of／today）
    value_date: date | None                        # fair value 是哪一天的值（抄自估值層，不猜）
    value_date_semantics: str                      # spot／target_period_end／unspecified
    target_period: FiscalPeriod | None
    horizon: HorizonAssumption | None
    horizon_selection: AssumptionSelection
    horizon_start: date | None
    horizon_end: date | None
    holding_period_days: int | None
    holding_period_years: float | None
    price_return: float | None
    annualized_price_return: float | None
    total_return_status: str
    total_return_reason: str
    alignment: str | None                          # value_date 與 horizon_end 的關係
    input_dependency: str | None
    steps: tuple[ReturnStep, ...]
    assumption_ids: tuple[str, ...]                # 營運假設＋估值假設＋horizon 假設
    observation_refs: tuple[str, ...]              # 現價 ref＋內部 EPS 的基期觀測 ref
    epistemics: Mapping[str, Any] = field(default_factory=dict)
    calculation: str = "deterministic"
    model_version: str = MODEL_VERSION
    digest: str = ""
    warnings: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)
    #: Step 5：報酬缺席時**是哪一種缺席**（`alpha/absence.py`）。上游（估值）缺席時直接繼承它的 kind——
    #: 「fair value 是刻意不主張」與「horizon 還沒寫」對使用者是兩件完全不同的事。
    absence_kind: str | None = None

    def __post_init__(self) -> None:
        if self.absence_kind is not None:
            check_absence_kind(self.absence_kind, "ImpliedReturnResult.absence_kind")
            if self.status != "missing":
                raise ContractViolation("有報酬就沒有缺席語意——absence_kind 只在 status=missing 時存在")
        if self.status not in RETURN_STATUSES:
            raise ContractViolation(f"ImpliedReturnResult.status 未登記：{self.status!r}")
        if self.return_convention not in RETURN_CONVENTIONS:
            raise ContractViolation(f"return_convention 未登記：{self.return_convention!r}")
        if self.total_return_status not in TOTAL_RETURN_STATUSES:
            raise ContractViolation(f"total_return_status 未登記：{self.total_return_status!r}")
        if self.alignment is not None and self.alignment not in ALIGNMENTS:
            raise ContractViolation(f"alignment 未登記：{self.alignment!r}")
        if self.status == "available":
            if self.price_return is None or self.input_dependency is None:
                raise ContractViolation("available 的報酬必須有 price_return 與 input_dependency")
            _finite(self.price_return, "ImpliedReturnResult.price_return")
            if self.horizon_start is None or self.horizon_end is None or self.holding_period_days is None:
                raise ContractViolation("available 的報酬必須有 horizon_start／horizon_end／holding_period_days")
            if self.holding_period_days <= 0:
                raise ContractViolation("holding_period_days 必須為正——horizon 已過就不是報酬")
            if self.annualized_price_return is not None:
                _finite(self.annualized_price_return, "ImpliedReturnResult.annualized_price_return")
        else:
            if self.price_return is not None or self.annualized_price_return is not None:
                raise ContractViolation("missing 的報酬不得帶數字（missing != zero）")
            if self.input_dependency is not None:
                raise ContractViolation("missing 的報酬不得帶 input_dependency")
            if not self.reason:
                raise ContractViolation("missing 必須附理由（L12：因果不得被截斷）")

    @property
    def effective_absence_kind(self) -> str | None:
        """報酬「為什麼沒有」。明示優先；沒明示就查 `status` 的預設表（查表，不推論）。"""
        if self.status != "missing":
            return None
        return self.absence_kind or default_absence_kind("missing")

    @property
    def is_known(self) -> bool:
        return self.price_return is not None

    @property
    def formulas(self) -> dict[str, str]:
        return {
            "horizon_start": HORIZON_START_FORMULA, "holding_period": HOLDING_PERIOD_FORMULA,
            "price_return": PRICE_RETURN_FORMULA, "annualized_price_return": ANNUALIZED_RETURN_FORMULA,
        }


def combined_return_dependency(valuation_dependency: str | None, horizon: HorizonAssumption | None) -> str | None:
    """報酬的輸入知識種類＝fair value 的輸入依賴與 horizon 判斷中最弱者。"""
    bases = [b for b in (valuation_dependency, horizon.basis if horizon else None) if b]
    return weakest_basis(bases)


__all__ = [
    "ALIGNMENTS", "ALIGNMENT_ALIGNED", "ALIGNMENT_HORIZON_AFTER", "ALIGNMENT_HORIZON_BEFORE", "ALIGNMENT_SPOT",
    "ANNUALIZED_RETURN_FORMULA", "DAYS_PER_YEAR", "HOLDING_PERIOD_FORMULA", "HORIZON_DRIVER",
    "HORIZON_START_FORMULA", "MODEL_VERSION", "PRICE_RETURN_FORMULA", "RETURN_CONVENTIONS",
    "RETURN_CONVENTION_BASE_CASE_PRICE", "RETURN_STATUSES", "TOTAL_RETURN_STATUSES", "HorizonAssumption",
    "ImpliedReturnResult", "ReturnStep", "combined_return_dependency",
]
