"""Entry Logic v1 的型別契約。**只有型別與驗證，零外部相依。**

## 這一層回答什麼

> 已知現價（含 bar_date）、fair value（含 value-date 語意）、明示 horizon 與**明示的要求報酬判準**，
> 「什麼價格以下才滿足這個報酬門檻？」現價相對那個門檻價在哪裡？

它刻意**不**回答：該不該買、買多少、何時下單、部位／配置／資本許可——名稱刻意叫
**analytical entry threshold**：它是一條**算出來的價格門檻**，不是 signal、不是 action。
`current_price <= entry_price` 只能表示 **meets analytical hurdle**，不得翻譯成「應該買」。

## Authority audit（2026-09-06，動工前先盤點）

`required return／hurdle` 不是公司事實（A1／A2 不擁有它），也不是「我們相信這家公司會怎樣」
（A3 的內容不含它）——它回答的是「**我的資本**要求多少報酬才值得」，主詞是投資人，不是公司。
它也不是資本決策（A5 是「當時憑什麼決定、使用者選了什麼」，append-only）：宣告一個 hurdle
不授權任何資本、不建立任何決策紀錄。所以：

| 東西 | 是誰的 | 本層怎麼對待它 |
|---|---|---|
| `EntryCriterion`（要求報酬判準） | **投資人政策**（`basis=investor_policy`；由使用者明示、append-only、as-of 可選取、可 supersede） | 與 A2 現價一樣是**注入的輸入**：本層只讀、不猜、不補預設、不自動改 |
| entry price／gap／comparison 算術 | A3 確定性導出（`alpha/entry/model.py`） | 純函式，公式唯一定義處在本檔 |
| 「該不該買、買多少」 | **使用者**（成為資本動作時才是 A5） | 本層**沒有那個欄位**（型別層以 token 掃描擋住） |

判準沒有 → `status=missing`＋「缺的是投資門檻判斷，不是資料 ETL 失敗」；**不 invent 10%／15%／20%**。

## 五條在型別層強制的規則

1. **hurdle 是明示紀錄，不是常數。** 沒有生效的 `EntryCriterion` → `missing`。
2. **convention 是封閉字彙（contract）。** v1 只有 `annualized_required_price_return`；多一個 convention
   就要多一段算術，打開它是改程式不是改設定。
3. **Missing != Zero。** 任一輸入缺席 → `status=missing`＋理由，數值欄位一律 `None`。
4. **沒有 buy／sell／size／allocation／order 欄位。** `EntryCriterion` 與 `EntryAssessmentResult` 在 import 當下
   就被 `_assert_no_capital_fields` 掃描——長出那種欄位是 import 失敗，不是 lint 警告。
5. **alignment 不對齊就不是 clean。** `horizon_before_value_date`／`horizon_after_value_date` 保留算術展示，
   但 `assessment=review_required`；只有 `aligned` 與（明示的）`spot_value_realized_over_horizon` 可以 `clean`。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from ..contracts import FORBIDDEN_POSITION_TOKENS
from ..errors import ContractViolation
from ..fundamental.contracts import AssumptionSelection, FiscalPeriod
from ..implied_return.contracts import (
    ALIGNMENT_ALIGNED, ALIGNMENT_SPOT, ALIGNMENTS, DAYS_PER_YEAR, HorizonAssumption,
)
from ..valuation.contracts import CurrentPrice

MODEL_VERSION = "entry-model/v1"

# ---------------------------------------------------------------------------
# 0. 封閉字彙與公式（唯一定義處）
# ---------------------------------------------------------------------------

#: 要求報酬的 convention——**contract**：每個 convention 對應 `model.py` 的一段算術。
CONVENTION_ANNUALIZED_PRICE_RETURN = "annualized_required_price_return"
ENTRY_CONVENTIONS: tuple[str, ...] = (CONVENTION_ANNUALIZED_PRICE_RETURN,)

#: 判準的知識種類。刻意**只有一種**：hurdle 是投資人的政策宣告，不是觀測、不是 session／LLM 對公司的判斷。
#: 「這家公司該要求較高的風險溢酬」是另一種物件（A3 的 risk-premium 判斷），v1 刻意不建模——
#: 兩者混在同一格會讓「投資人要什麼」與「研究認為公司多危險」同形（L12）。
CRITERION_BASIS_INVESTOR_POLICY = "investor_policy"
CRITERION_BASES: tuple[str, ...] = (CRITERION_BASIS_INVESTOR_POLICY,)

#: `required_return` 的 driver 名稱（讓 refresh artifact 的 driver 語意與其他判斷型紀錄同形）。
CRITERION_DRIVER = "required_return"
CRITERION_SCOPE = "total"

#: hurdle 的合法範圍：`(1 + hurdle)` 必須為正，上限只是擋打錯位數（500% 年化不是政策）。
HURDLE_LOWER_EXCLUSIVE = -1.0
HURDLE_UPPER_INCLUSIVE = 5.0

ENTRY_PRICE_FORMULA = ("entry_price = fair_value / (1 + annualized_hurdle) ** (holding_period_days / 365.25)"
                       "——現價等於它時，年化隱含價格報酬恰等於 hurdle")
PRICE_TO_ENTRY_GAP_FORMULA = ("price_to_entry_gap = current_price / entry_price − 1；"
                              "price_to_entry_gap_abs = current_price − entry_price（正值＝現價高於門檻價）")
HURDLE_COMPARISON_RULE = ("current_price <= entry_price ⇒ meets_analytical_hurdle；否則 above_analytical_entry"
                          "（等價於 annualized_implied_price_return >= hurdle；只是算術比較，不是買賣）")

#: 現價相對門檻價的位置——純算術比較，**不是** action。
COMPARISON_MEETS = "meets_analytical_hurdle"
COMPARISON_ABOVE = "above_analytical_entry"
HURDLE_COMPARISONS: tuple[str, ...] = (COMPARISON_MEETS, COMPARISON_ABOVE)

#: 這次評估能不能當 clean 讀：`clean`＝alignment 對齊（或 spot 且已明示）；`review_required`＝
#: value_date 與 horizon_end 不一致，算術照列但不得冒充 current actionable result。
ASSESSMENT_CLEAN = "clean"
ASSESSMENT_REVIEW_REQUIRED = "review_required"
ASSESSMENT_STATES: tuple[str, ...] = (ASSESSMENT_CLEAN, ASSESSMENT_REVIEW_REQUIRED)
#: 只有這些 alignment 可以 clean。
CLEAN_ALIGNMENTS: frozenset[str] = frozenset({ALIGNMENT_ALIGNED, ALIGNMENT_SPOT})

ENTRY_STATUSES: tuple[str, ...] = ("available", "missing")

#: 型別層禁止的 token：部位語意（與 `AlphaSignal` 同一份）＋ action 語意。欄位名任何一段命中即 import 失敗。
FORBIDDEN_ENTRY_TOKENS: frozenset[str] = FORBIDDEN_POSITION_TOKENS | frozenset(
    {"buy", "sell", "order", "action", "actionable", "trade", "permission"})


def _assert_no_capital_fields(cls: type) -> None:
    for f in fields(cls):
        parts = set(f.name.lower().split("_"))
        banned = parts & FORBIDDEN_ENTRY_TOKENS
        if banned:
            raise ContractViolation(
                f"{cls.__name__}.{f.name} 帶部位／action 語意 {sorted(banned)}；"
                "Entry Logic 只輸出 analytical threshold，買賣／部位／資本由使用者與 Engine D 決定")


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
# 1. EntryCriterion——投資人的要求報酬判準（注入的輸入，不是研究判斷）
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EntryCriterion:
    """投資人對「這檔要求多少年化價格報酬」的**明示**宣告（例：COHR 要求年化 15%）。

    ⚠ 它不是公司事實、不是 session 對公司的判斷、不是資本許可。`basis` 只能是 `investor_policy`；
    `rationale` 說為什麼（機會成本、借款成本、風險容忍——投資人自己的理由）；`reference_refs` 是
    provenance 指標（例：`config://beta_policy`、`engine_c://financial_snapshot/SOXX`），**不要求解析到
    公司的 evidence index**——投資人的機會成本本來就不在那裡；`created_at` 決定 as-of 視角下它存不存在；
    `supersedes_id`／`retracted` 是 append-only 的改值與撤回語意。

    刻意**沒有** `period`：要求報酬不隨估值的目標會計年度換期而失效——它是投資人的政策，不是對某一年的判斷。
    """

    criterion_id: str
    company_id: str
    ticker: str
    convention: str
    value: float
    basis: str
    rationale: str
    created_at: datetime
    author: str = "user"
    reference_refs: tuple[str, ...] = ()
    supersedes_id: str | None = None
    retracted: bool = False

    def __post_init__(self) -> None:
        _nonempty(self.criterion_id, "EntryCriterion.criterion_id")
        if not self.criterion_id.startswith("ec_"):
            raise ContractViolation("criterion_id 必須以 ec_ 開頭（由 new_entry_criterion_id 產生）")
        _nonempty(self.company_id, "EntryCriterion.company_id")
        _nonempty(self.ticker, "EntryCriterion.ticker")
        if self.convention not in ENTRY_CONVENTIONS:
            raise ContractViolation(
                f"convention 未登記：{self.convention!r}；已知 {list(ENTRY_CONVENTIONS)}——"
                "convention 是 contract，多一個就要多一段算術")
        if self.basis not in CRITERION_BASES:
            raise ContractViolation(
                f"EntryCriterion.basis 未登記：{self.basis!r}；已知 {list(CRITERION_BASES)}——"
                "hurdle 是投資人政策，不是觀測、不是 session 對公司的判斷")
        value = _finite(self.value, "EntryCriterion.value")
        if not (HURDLE_LOWER_EXCLUSIVE < value <= HURDLE_UPPER_INCLUSIVE):
            raise ContractViolation(
                f"hurdle={value} 超出範圍（{HURDLE_LOWER_EXCLUSIVE} < hurdle <= {HURDLE_UPPER_INCLUSIVE}）")
        _nonempty(self.rationale, "EntryCriterion.rationale")
        _nonempty(self.author, "EntryCriterion.author")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ContractViolation("created_at 必須是帶時區的 datetime")
        if any(not isinstance(r, str) or not r.strip() for r in self.reference_refs):
            raise ContractViolation("reference_refs 每一項必須是非空字串")

    # ---- 與其他判斷型紀錄同形的介面（refresh 攤平器／變更偵測可以共用）----
    @property
    def driver(self) -> str:
        return CRITERION_DRIVER

    @property
    def scope(self) -> str:
        return CRITERION_SCOPE

    @property
    def key(self) -> tuple[str, str]:
        return (self.convention, self.scope)

    @property
    def created_on(self) -> date:
        return self.created_at.date()


_assert_no_capital_fields(EntryCriterion)


# ---------------------------------------------------------------------------
# 2. 模型輸出
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EntryStep:
    """entry 算式上的一格：`criterion_input`（投資人判準）／`return_input`（照抄 implied return）／
    `price_input`（現價）／`derived`（算出）。"""

    key: str
    label: str
    kind: str
    value: Any
    unit: str
    basis: str                       # investor_policy／observation／deterministic／session_judgment／none
    formula: str | None = None
    assumption_ids: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    reason: str | None = None
    input_dependency: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("criterion_input", "return_input", "price_input", "derived"):
            raise ContractViolation(f"EntryStep.kind 未登記：{self.kind!r}")
        if self.value is None and self.basis != "none":
            raise ContractViolation(f"EntryStep[{self.key}] 沒有值就沒有 basis（missing != zero）")
        if self.value is not None and self.basis == "none":
            raise ContractViolation(f"EntryStep[{self.key}] 有值必須說出知識種類")
        if isinstance(self.value, (int, float)) and not isinstance(self.value, bool):
            _finite(self.value, f"EntryStep[{self.key}].value")


@dataclass(frozen=True, slots=True)
class EntryAssessmentResult:
    """一次 entry 評估的完整輸出——read model 只選取，不重算。

    `status="available"` ⇒ `entry_price`／`price_to_entry_gap`／`required_annualized_return`／
    `current_annualized_implied_return`／`hurdle_comparison`／`assessment`／`input_dependency` 全部有值；
    `calculation="deterministic"`；`input_dependency`＝implied return 的輸入依賴（研究側判斷中最弱者——
    判準本身是投資人政策，另列 `criterion_basis`，不混進研究依賴）。

    ⚠ 型別裡刻意**沒有** buy／sell／size／allocation／order／actionable 欄位（import 時掃描）；
    `hurdle_comparison=meets_analytical_hurdle` 只是「現價 ≤ 門檻價」的算術事實。
    """

    company_id: str
    ticker: str
    as_of: date | None
    status: str                                    # available／missing
    reason: str | None
    convention: str
    criterion: EntryCriterion | None
    criterion_selection: AssumptionSelection
    criterion_reason: str | None                   # 判準缺席的理由（與上游缺席分開）
    implied_return_status: str                     # available／missing（照抄上游）
    implied_return_reason: str | None
    current_price: CurrentPrice
    price_as_of: date | None
    fair_value: float | None
    fair_value_currency: str | None
    value_date: date | None
    value_date_semantics: str
    target_period: FiscalPeriod | None
    horizon: HorizonAssumption | None
    horizon_start: date | None
    horizon_end: date | None
    holding_period_days: int | None
    required_annualized_return: float | None
    current_annualized_implied_return: float | None
    entry_price: float | None
    price_to_entry_gap: float | None               # current_price / entry_price − 1
    price_to_entry_gap_abs: float | None           # current_price − entry_price
    hurdle_comparison: str | None                  # meets_analytical_hurdle／above_analytical_entry
    assessment: str | None                         # clean／review_required
    assessment_reason: str | None
    alignment: str | None
    input_dependency: str | None
    criterion_basis: str | None
    steps: tuple[EntryStep, ...]
    research_assumption_ids: tuple[str, ...]       # 營運＋估值＋horizon 假設（oa_／va_／ha_）
    observation_refs: tuple[str, ...]              # 現價 ref＋基期觀測 ref
    epistemics: Mapping[str, Any] = field(default_factory=dict)
    calculation: str = "deterministic"
    model_version: str = MODEL_VERSION
    digest: str = ""
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in ENTRY_STATUSES:
            raise ContractViolation(f"EntryAssessmentResult.status 未登記：{self.status!r}")
        if self.convention not in ENTRY_CONVENTIONS:
            raise ContractViolation(f"convention 未登記：{self.convention!r}")
        if self.hurdle_comparison is not None and self.hurdle_comparison not in HURDLE_COMPARISONS:
            raise ContractViolation(f"hurdle_comparison 未登記：{self.hurdle_comparison!r}")
        if self.assessment is not None and self.assessment not in ASSESSMENT_STATES:
            raise ContractViolation(f"assessment 未登記：{self.assessment!r}")
        if self.alignment is not None and self.alignment not in ALIGNMENTS:
            raise ContractViolation(f"alignment 未登記：{self.alignment!r}")
        if self.criterion_basis is not None and self.criterion_basis not in CRITERION_BASES:
            raise ContractViolation(f"criterion_basis 未登記：{self.criterion_basis!r}")
        #: **本層自己算出來的**數字（門檻價、gap、要求報酬）——`missing` 時一律 None。
        #: `current_annualized_implied_return` 不在列上：它與 `fair_value`／`value_date`／`horizon_*` 一樣是
        #: **上游照抄值**，缺判準時仍該看得見（讀者要知道「現在的隱含報酬是多少」才知道要不要宣告 hurdle）。
        own = (self.entry_price, self.price_to_entry_gap, self.price_to_entry_gap_abs,
               self.required_annualized_return)
        numeric = own + (self.current_annualized_implied_return,)
        if self.status == "available":
            if any(v is None for v in numeric) or self.input_dependency is None:
                raise ContractViolation("available 的 entry 評估必須有 entry_price／gap／hurdle／年化隱含報酬／input_dependency")
            for value, label in zip(numeric, ("entry_price", "price_to_entry_gap", "price_to_entry_gap_abs",
                                              "required_annualized_return", "current_annualized_implied_return")):
                _finite(value, f"EntryAssessmentResult.{label}")
            if self.entry_price <= 0:                                        # type: ignore[operator]
                raise ContractViolation("entry_price 必須為正")
            if self.hurdle_comparison is None or self.assessment is None or self.criterion is None:
                raise ContractViolation("available 的 entry 評估必須有 hurdle_comparison／assessment／criterion")
            if self.assessment == ASSESSMENT_CLEAN and self.alignment not in CLEAN_ALIGNMENTS:
                raise ContractViolation(
                    f"alignment={self.alignment!r} 不得標 clean——value_date 與 horizon_end 不一致時只能 review_required")
            if self.assessment == ASSESSMENT_REVIEW_REQUIRED and not self.assessment_reason:
                raise ContractViolation("review_required 必須附 assessment_reason（L12：因果不得被截斷）")
            if self.horizon_start is None or self.horizon_end is None or self.holding_period_days is None:
                raise ContractViolation("available 的 entry 評估必須有 horizon 起迄與持有天數")
        else:
            if any(v is not None for v in own):
                raise ContractViolation("missing 的 entry 評估不得帶本層自己算的數字（missing != zero）")
            if self.current_annualized_implied_return is not None:
                _finite(self.current_annualized_implied_return, "EntryAssessmentResult.current_annualized_implied_return")
            if self.hurdle_comparison is not None or self.assessment is not None or self.input_dependency is not None:
                raise ContractViolation("missing 的 entry 評估不得帶 comparison／assessment／input_dependency")
            if not self.reason:
                raise ContractViolation("missing 必須附理由（L12：因果不得被截斷）")

    @property
    def is_known(self) -> bool:
        return self.entry_price is not None

    @property
    def formulas(self) -> dict[str, str]:
        return {"entry_price": ENTRY_PRICE_FORMULA, "price_to_entry_gap": PRICE_TO_ENTRY_GAP_FORMULA,
                "hurdle_comparison": HURDLE_COMPARISON_RULE}

    @property
    def criterion_id(self) -> str | None:
        return self.criterion.criterion_id if self.criterion is not None else None


_assert_no_capital_fields(EntryAssessmentResult)


__all__ = [
    "ASSESSMENT_CLEAN", "ASSESSMENT_REVIEW_REQUIRED", "ASSESSMENT_STATES", "CLEAN_ALIGNMENTS", "COMPARISON_ABOVE",
    "COMPARISON_MEETS", "CONVENTION_ANNUALIZED_PRICE_RETURN", "CRITERION_BASES", "CRITERION_BASIS_INVESTOR_POLICY",
    "CRITERION_DRIVER", "CRITERION_SCOPE", "DAYS_PER_YEAR", "ENTRY_CONVENTIONS", "ENTRY_PRICE_FORMULA",
    "ENTRY_STATUSES", "FORBIDDEN_ENTRY_TOKENS", "HURDLE_COMPARISONS", "HURDLE_COMPARISON_RULE",
    "HURDLE_LOWER_EXCLUSIVE", "HURDLE_UPPER_INCLUSIVE", "MODEL_VERSION", "PRICE_TO_ENTRY_GAP_FORMULA",
    "EntryAssessmentResult", "EntryCriterion", "EntryStep",
]
