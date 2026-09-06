"""`build_implied_return()`——現價 ＋ fair value（含 value-date 語意）＋ 明示 horizon → 確定性 base-case 隱含價格報酬。

```
ValuationResult（alpha/valuation；fair value、value_date、input_dependency）─┐
HorizonAssumption[]（ledger）── select(as_of) ──────────────────────────────┼─► build_implied_return ─► ImpliedReturnResult
CurrentPrice（Engine C；現價＋bar_date）───────────────────────────────────┘
        price_return ＝ fair_value / current_price − 1
        holding_period_days ＝ horizon_end − bar_date
        annualized ＝ (1 + price_return) ** (365.25 / days) − 1
```

## 五條規則

1. **四個輸入缺一就是 `missing`**：現價（含 bar_date）、fair value（同單位）、fair value 的 value-date 語意、
   生效的 horizon 判斷。沒有 hidden default（不補 12 個月、不補下一會計年度）。
2. **horizon 已過就不是報酬**：`horizon_end <= bar_date` → `missing`＋「需要新的 horizon 判斷」。
3. **只有 price return。** total return 恆 `not_modeled`（無股利／分配預測能力），不得冒充。
4. **沒有機率。** 這是 base case 的隱含報酬，不是機率加權期望值；型別沒有那個欄位。
5. **算術確定、輸入是判斷。** `calculation=deterministic`；`input_dependency`＝fair value 的輸入依賴與
   horizon basis 中最弱者；每一格 step 都標知識種類。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence

from ..contracts import EvidenceRef, content_digest
from ..fundamental.contracts import AssumptionSelection, FiscalPeriod
from ..valuation.contracts import VALUE_DATE_SPOT, VALUE_DATE_UNSPECIFIED, CurrentPrice, ValuationResult
from ..valuation.model import units_comparable
from .assumptions import select_horizon_assumptions
from .contracts import (
    ALIGNMENT_ALIGNED, ALIGNMENT_HORIZON_AFTER, ALIGNMENT_HORIZON_BEFORE, ALIGNMENT_SPOT,
    ANNUALIZED_RETURN_FORMULA, DAYS_PER_YEAR, HOLDING_PERIOD_FORMULA, HORIZON_START_FORMULA,
    PRICE_RETURN_FORMULA, RETURN_CONVENTION_BASE_CASE_PRICE, HorizonAssumption, ImpliedReturnResult,
    ReturnStep, combined_return_dependency,
)

_TOTAL_RETURN_REASON = ("本層沒有股利／分配預測能力（Engine C 無配息欄位、橋 v1 無配息假設）——"
                        "total_return 是 not_modeled，不是 0，也不是 price_return 的別名")


def _price_return(fair_value: float, price: float) -> float:
    return fair_value / price - 1.0


def _annualized(price_return: float, days: int) -> float:
    return (1.0 + price_return) ** (DAYS_PER_YEAR / days) - 1.0


def _alignment(value_date_semantics: str, value_date: date | None, horizon_end: date) -> str | None:
    if value_date_semantics == VALUE_DATE_SPOT:
        return ALIGNMENT_SPOT
    if value_date is None:
        return None
    if horizon_end == value_date:
        return ALIGNMENT_ALIGNED
    return ALIGNMENT_HORIZON_AFTER if horizon_end > value_date else ALIGNMENT_HORIZON_BEFORE


def _missing(
    *, company_id: str, ticker: str, as_of: date, reason: str, price: CurrentPrice, valuation: ValuationResult | None,
    horizon: HorizonAssumption | None, selection: AssumptionSelection, steps: Sequence[ReturnStep],
    warnings: Sequence[str], horizon_start: date | None = None, horizon_end: date | None = None,
    alignment: str | None = None,
) -> ImpliedReturnResult:
    fv_known = valuation is not None and valuation.is_known
    ids = tuple(valuation.assumption_ids) if valuation else ()
    if horizon is not None:
        ids += (horizon.assumption_id,)
    obs = tuple(price.evidence_refs)
    if valuation is not None and valuation.fundamental_input is not None:
        obs += tuple(valuation.fundamental_input.observation_refs)
    return ImpliedReturnResult(
        company_id=company_id, ticker=ticker, as_of=as_of, status="missing", reason=reason,
        return_convention=RETURN_CONVENTION_BASE_CASE_PRICE, current_price=price, price_as_of=price.bar_date,
        fair_value=valuation.fair_value if fv_known else None,
        fair_value_currency=valuation.currency if fv_known else None,
        fair_value_as_of=(valuation.as_of if valuation and valuation.as_of else (as_of if fv_known else None)),
        value_date=valuation.value_date if valuation else None,
        value_date_semantics=valuation.value_date_semantics if valuation else VALUE_DATE_UNSPECIFIED,
        target_period=valuation.target_period if valuation else None,
        horizon=horizon, horizon_selection=selection, horizon_start=horizon_start, horizon_end=horizon_end,
        holding_period_days=None, holding_period_years=None, price_return=None, annualized_price_return=None,
        total_return_status="not_modeled", total_return_reason=_TOTAL_RETURN_REASON, alignment=alignment,
        input_dependency=None, steps=tuple(steps), assumption_ids=ids, observation_refs=tuple(dict.fromkeys(obs)),
        digest=content_digest({"company_id": company_id, "ticker": ticker, "as_of": as_of, "status": "missing",
                               "reason": reason}),
        warnings=tuple(warnings),
    )


def build_implied_return(
    *,
    company_id: str,
    ticker: str,
    as_of: date | None,
    today: date,
    valuation: ValuationResult | None,
    valuation_reason: str | None,
    horizon_records: Sequence[HorizonAssumption],
    evidence_index: Mapping[str, EvidenceRef],
    price: CurrentPrice,
    parse_errors: Sequence[str] = (),
) -> ImpliedReturnResult:
    """一次 base-case implied return 執行。任何一段缺料都以 `missing`＋理由現形，不讓整體失敗、也不補預設值。"""
    cutoff = as_of or today
    warnings: list[str] = []
    steps: list[ReturnStep] = []

    # ---- 1. 現價（A2 觀測；只讀）----------------------------------------------------------
    if price.is_known and price.bar_date is not None:
        steps.append(ReturnStep(key="current_price", label=f"現價（Engine C，bar {price.bar_date}）", kind="price_input",
                                value=price.value, unit=f"quote_unit（{price.unit or '未知'}）", basis="observation",
                                observation_refs=tuple(price.evidence_refs)))
    else:
        why = price.reason or ("現價快照沒有 bar_date——沒有起算日就沒有 horizon" if price.is_known else "Engine C 無現價")
        steps.append(ReturnStep(key="current_price", label="現價（Engine C）", kind="price_input", value=None,
                                unit="quote_unit", basis="none", reason=why))

    # ---- 2. fair value 與它的 value-date 語意（照抄估值層，不重算）--------------------------
    if valuation is None:
        fv_reason: str | None = valuation_reason or "本次未執行 valuation model——沒有 fair value 就沒有報酬"
    elif valuation.as_of != as_of:
        fv_reason = "valuation 是在不同 as-of 視角下算的，拒用（INV-6）"
        warnings.append(fv_reason)
        valuation = None
    elif not valuation.is_known:
        fv_reason = f"fair value 缺席：{valuation.reason or '未知'}（不是 0）"
    else:
        fv_reason = None
    if valuation is not None and valuation.is_known:
        steps.append(ReturnStep(
            key="fair_value", label=f"Fair value（{valuation.target_period.label if valuation.target_period else '?'}，"
                                     f"{valuation.accounting_basis}）", kind="valuation_input",
            value=valuation.fair_value, unit="currency_per_share", basis="deterministic", formula=valuation.formula,
            assumption_ids=tuple(valuation.assumption_ids),
            observation_refs=tuple(valuation.fundamental_input.observation_refs) if valuation.fundamental_input else (),
            input_dependency=valuation.input_dependency))
        steps.append(ReturnStep(
            key="value_date", label="fair value 是哪一天的值（value_date）", kind="valuation_input",
            value=valuation.value_date, unit="date",
            basis="session_judgment" if valuation.value_date is not None else "none",
            formula=valuation.value_date_formula,
            assumption_ids=tuple(a.assumption_id for a in valuation.assumptions),
            reason=(None if valuation.value_date is not None else
                    "估值假設未宣告 value_date_convention——時點語意 unspecified，不猜")))
    else:
        steps.append(ReturnStep(key="fair_value", label="Fair value", kind="valuation_input", value=None,
                                unit="currency_per_share", basis="none", reason=fv_reason))

    # ---- 3. horizon 判斷選取（as-of／期間／supersede／證據解析）-------------------------------
    index: dict[str, EvidenceRef] = dict(evidence_index)
    if valuation is not None:
        for ref in valuation.evidence:
            index.setdefault(ref.ref, ref)
    target: FiscalPeriod | None = valuation.target_period if valuation is not None else None
    if target is not None:
        accepted, selection = select_horizon_assumptions(
            horizon_records, target=target, as_of=as_of, today=today, evidence_index=index, parse_errors=parse_errors)
    else:
        accepted = ()
        selection = AssumptionSelection(
            input_count=len(horizon_records) + len(parse_errors), accepted_count=0,
            reasons={"no_target_period": len(horizon_records) + len(parse_errors)})
    for record in accepted:
        if record.created_on > cutoff:                       # select 已擋；這裡是 PIT 自我核對
            raise AssertionError("select_horizon_assumptions 放行了 as-of 之後的假設")
    horizon: HorizonAssumption | None = accepted[0] if accepted else None
    if horizon is None:
        if selection.input_count:
            h_reason = "沒有生效的 horizon 判斷（" + "；".join(f"{k}={v}" for k, v in selection.reasons.items()) + "）"
        else:
            h_reason = "尚未寫入任何 horizon 判斷——沒有明示的實現日期就沒有報酬，不補 12 個月、不補下一會計年度"
        steps.append(ReturnStep(key="horizon_end", label="Horizon（fair value 何時被市場定價到）", kind="horizon_input",
                                value=None, unit="date", basis="none", reason=h_reason))
    else:
        steps.append(ReturnStep(
            key="horizon_end", label=f"Horizon（{horizon.period.label} fair value 於此日前實現）", kind="horizon_input",
            value=horizon.horizon_end, unit="date", basis=horizon.basis, assumption_ids=(horizon.assumption_id,),
            observation_refs=tuple(horizon.evidence_refs), reason=horizon.rationale[:200]))

    # ---- 4. 缺料判定（順序固定：現價 → fair value → 單位 → value-date → horizon → horizon 已過）------
    def _stop(reason: str, **kw: Any) -> ImpliedReturnResult:
        return _missing(company_id=company_id, ticker=ticker, as_of=as_of, reason=reason, price=price,
                        valuation=valuation, horizon=horizon, selection=selection, steps=steps, warnings=warnings, **kw)

    if not price.is_known:
        return _stop(price.reason or "Engine C 無現價——沒有起點就沒有報酬")
    if price.bar_date is None:
        return _stop("現價快照沒有 bar_date——沒有起算日就沒有 horizon（不得用 ETL 日冒充）")
    if valuation is None or not valuation.is_known:
        return _stop(fv_reason or "fair value 缺席")
    unit_status, unit_why = units_comparable(valuation.currency, price.unit)
    if unit_status != "comparable":
        return _stop(f"{unit_status}：{unit_why}")
    if price.value <= 0:
        return _stop("現價非正，相對報酬無定義")
    if valuation.value_date_semantics == VALUE_DATE_UNSPECIFIED:
        return _stop("fair value 的時點語意 unspecified（估值假設未宣告 value_date_convention）——"
                     "不知道這個數字是哪一天的值，就不能說「從哪天到哪天的報酬」")
    if horizon is None:
        return _stop(h_reason)
    horizon_start = price.bar_date
    horizon_end = horizon.horizon_end
    alignment = _alignment(valuation.value_date_semantics, valuation.value_date, horizon_end)
    if horizon_end <= horizon_start:
        return _stop(f"horizon_end {horizon_end} 不晚於現價 bar_date {horizon_start}——horizon 已過，"
                     "需要新的 horizon 判斷（不是報酬為 0）",
                     horizon_start=horizon_start, horizon_end=horizon_end, alignment=alignment)

    # ---- 5. 確定性算術 -------------------------------------------------------------------------
    days = (horizon_end - horizon_start).days
    years = days / DAYS_PER_YEAR
    price_return = _price_return(valuation.fair_value, price.value)          # type: ignore[arg-type]
    annualized = _annualized(price_return, days) if days >= 1 else None
    dependency = combined_return_dependency(valuation.input_dependency, horizon)
    all_ids = tuple(valuation.assumption_ids) + (horizon.assumption_id,)
    obs_refs = tuple(dict.fromkeys(tuple(price.evidence_refs)
                                   + (tuple(valuation.fundamental_input.observation_refs) if valuation.fundamental_input else ())))
    steps.append(ReturnStep(key="horizon_start", label="Horizon 起點（現價的 bar_date）", kind="derived",
                            value=horizon_start, unit="date", basis="deterministic", formula=HORIZON_START_FORMULA,
                            observation_refs=tuple(price.evidence_refs)))
    steps.append(ReturnStep(key="holding_period_days", label="持有期間（天）", kind="derived", value=days, unit="days",
                            basis="deterministic", formula=HOLDING_PERIOD_FORMULA, assumption_ids=(horizon.assumption_id,)))
    steps.append(ReturnStep(key="price_return", label="Base-case 隱含價格報酬（simple）", kind="derived",
                            value=price_return, unit="ratio", basis="deterministic", formula=PRICE_RETURN_FORMULA,
                            assumption_ids=all_ids, observation_refs=obs_refs, input_dependency=dependency))
    if annualized is not None:
        steps.append(ReturnStep(key="annualized_price_return", label="年化隱含價格報酬（compound）", kind="derived",
                                value=annualized, unit="ratio", basis="deterministic", formula=ANNUALIZED_RETURN_FORMULA,
                                assumption_ids=all_ids, observation_refs=obs_refs, input_dependency=dependency))
    if alignment == ALIGNMENT_HORIZON_BEFORE:
        warnings.append(f"horizon_end {horizon_end} 早於 value_date {valuation.value_date}：這是「市場提前定價」的判斷，"
                        "年化報酬因此以較短期間計——請確認這是刻意的")
    elif alignment == ALIGNMENT_HORIZON_AFTER:
        warnings.append(f"horizon_end {horizon_end} 晚於 value_date {valuation.value_date}：fair value 定義在較早的日期，"
                        "報酬卻假設較晚才實現——年化被稀釋")
    if days < 90:
        warnings.append(f"持有期間只有 {days} 天——年化會放大任何誤差，讀年化數字時請看 simple 報酬")
    warnings.extend(valuation.warnings)

    epistemics: dict[str, Any] = {
        "deterministic": ["報酬算術（fair_value / price − 1）", "年化算術（compound，365.25 天）",
                          "持有期間算術（horizon_end − bar_date）", "估值算術（內部 EPS × target_pe）", "財務橋算術"],
        "judgment_inputs": {
            "operating_and_valuation_assumptions": {"count": len(valuation.assumption_ids),
                                                    "input_dependency": valuation.input_dependency},
            "value_date_convention": {"semantics": valuation.value_date_semantics,
                                      "declared_by": [a.assumption_id for a in valuation.assumptions]},
            "horizon": {"count": 1, "by_basis": {horizon.basis: 1}, "assumption_id": horizon.assumption_id},
        },
        "observations": ["現價（Engine C snapshot）", "基期實際值（Engine C mechanical 觀測）"],
        "return_input_dependency": dependency,
        "this_is_not": ["probability-weighted expected return（沒有情境機率）", "total return（沒有股利／分配預測）",
                        "required return／entry price／buy-sell（Entry Logic 未建模）", "回測或統計勝率"],
        "one_sentence": (f"從 {horizon_start}（現價 {price.value:g} {price.unit}）到 {horizon_end}，在「{valuation.target_period.label if valuation.target_period else '?'} "
                         f"fair value {valuation.fair_value:.2f} 是 {valuation.value_date}（{valuation.value_date_semantics}）的值」與"
                         f"「市場在 {horizon_end} 前定價到那裡」的假設下，base-case 隱含價格報酬 {price_return:+.1%}"
                         + (f"、年化 {annualized:+.1%}" if annualized is not None else "") + "；輸入判斷最弱處＝"
                         f"{dependency}；total return 未建模"),
    }
    digest = content_digest({
        "company_id": company_id, "ticker": ticker, "as_of": as_of, "valuation_digest": valuation.digest,
        "horizon": horizon.assumption_id, "price": (price.value, price.bar_date),
    })
    evidence = [index[r] for r in horizon.evidence_refs if r in index]
    return ImpliedReturnResult(
        company_id=company_id, ticker=ticker, as_of=as_of, status="available", reason=None,
        return_convention=RETURN_CONVENTION_BASE_CASE_PRICE, current_price=price, price_as_of=price.bar_date,
        fair_value=valuation.fair_value, fair_value_currency=valuation.currency,
        fair_value_as_of=valuation.as_of or today, value_date=valuation.value_date,
        value_date_semantics=valuation.value_date_semantics, target_period=valuation.target_period,
        horizon=horizon, horizon_selection=selection, horizon_start=horizon_start, horizon_end=horizon_end,
        holding_period_days=days, holding_period_years=years, price_return=price_return,
        annualized_price_return=annualized, total_return_status="not_modeled", total_return_reason=_TOTAL_RETURN_REASON,
        alignment=alignment, input_dependency=dependency, steps=tuple(steps), assumption_ids=all_ids,
        observation_refs=obs_refs, epistemics=epistemics, digest=digest, warnings=tuple(warnings),
        evidence=tuple({r.ref: r for r in evidence}.values()),
    )


__all__ = ["build_implied_return"]
