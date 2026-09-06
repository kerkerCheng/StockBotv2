"""`build_valuation()`——內部基本面 × 明示估值假設 → 確定性 fair value → 與現價的差。

```
FundamentalModelResult（alpha/fundamental；內部 EPS）─┐
ValuationAssumption[]（ledger）── select(as_of) ──────┼─► build_valuation ─► ValuationResult
MarketSnapshot（Engine C；現價）──────────────────────┘        │
                                                           fair_value ＝ internal_eps × target_pe
                                                           gap ＝ fair_value vs current_price（同單位才算）
```

## 四條規則

1. **沒有 hidden default。** ledger 沒有生效的估值假設 → `missing`；內部 EPS 缺 → `missing`。
   不補倍數、不補 EPS、不由 LLM 補。
2. **同期、同口徑才乘。** 估值假設的 `period` 必須與內部 EPS 的期間相同、`accounting_basis`
   必須與內部 EPS 口徑相同；不同就是 `missing`＋理由（不是缺假設，是口徑／期間不合）。
3. **price 不進 fair value。** fair value 只依賴內部 EPS 與估值假設；現價只用在 gap。
   所以 price-only 變化不會動 fair value，只會動 gap（refresh 引擎據此分開標 state）。
4. **gap 不是 expected return。** 它只回答「fair value 比現價高／低多少」；horizon、報酬
   語意、進場價一律不在這裡（Step 2）。
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, Mapping, Sequence

from ..contracts import EvidenceRef, content_digest
from ..fundamental.contracts import (
    AssumptionSelection, FiscalPeriod, FundamentalModelResult, OperatingAssumption,
)
from .assumptions import select_valuation_assumptions
from .contracts import (
    FAIR_VALUE_FORMULA, GAP_FORMULA, IMPLIED_MULTIPLE_FORMULA, METHOD_FUNDAMENTAL_INPUT,
    METHOD_PARAMETERS, VALUATION_METHODS, CurrentPrice, FairValueGap, FairValueSensitivity,
    FundamentalInput, ValuationAssumption, ValuationResult, ValuationStep, combined_input_dependency,
)

#: 估值假設的微擾：倍數 ×1.01。
_RELATIVE_BUMP = 0.01


def _units_match(fair_value_currency: str | None, price_unit: str | None) -> tuple[str, str | None]:
    """fair value 的幣別（報表幣別）與現價的報價單位是否同尺度。

    ⚠ 報價單位 ≠ 結算幣別（AGENTS：GBp／ILA／ZAc 是 minor unit）。這裡**不換算**——
    任一邊不知道 → `unverified_unit`；兩邊都知道但不同 → `incompatible_unit`。價格會差 100 倍的事
    不得靠猜。
    """
    if not fair_value_currency or not price_unit:
        return "unverified_unit", "fair value 幣別或現價報價單位未知——不得假設同尺度"
    if fair_value_currency.upper() != price_unit.upper():
        return "incompatible_unit", (f"fair value 以 {fair_value_currency} 計，現價報價單位是 {price_unit}"
                                     "——不同尺度不得相減（報價單位 ≠ 結算幣別，本層不換算）")
    return "comparable", None


def _gap(fair_value: float | None, price: CurrentPrice, *, currency: str | None) -> FairValueGap:
    if fair_value is None:
        return FairValueGap(status="fair_value_missing", absolute_gap=None, relative_gap=None,
                            implied_multiple_at_price=None, unit=None, reason="fair value 缺席（不是 0）",
                            price_refs=price.evidence_refs)
    if not price.is_known:
        return FairValueGap(status="price_missing", absolute_gap=None, relative_gap=None,
                            implied_multiple_at_price=None, unit=None,
                            reason=price.reason or "Engine C 無現價", price_refs=price.evidence_refs)
    status, why = _units_match(currency, price.unit)
    if status != "comparable":
        return FairValueGap(status=status, absolute_gap=None, relative_gap=None,
                            implied_multiple_at_price=None, unit=None, reason=why, price_refs=price.evidence_refs)
    if price.value <= 0:
        return FairValueGap(status="price_missing", absolute_gap=None, relative_gap=None,
                            implied_multiple_at_price=None, unit=None, reason="現價非正，相對差無定義",
                            price_refs=price.evidence_refs)
    return FairValueGap(status="comparable", absolute_gap=fair_value - price.value,
                        relative_gap=fair_value / price.value - 1.0, implied_multiple_at_price=None,
                        unit=currency, reason=None, price_refs=price.evidence_refs)


def _fair_value(method: str, fundamental: FundamentalInput, assumption: ValuationAssumption) -> float:
    """每個 method 一段算術。v1 只有 forward earnings multiple。"""
    if method == "forward_earnings_multiple":
        assert fundamental.value is not None
        return fundamental.value * assumption.value
    raise AssertionError(f"method {method} 沒有算術——契約層應已擋下")


def build_valuation(
    *,
    company_id: str,
    ticker: str,
    as_of: date | None,
    today: date,
    fundamental: FundamentalModelResult | None,
    fundamental_reason: str | None,
    assumption_records: Sequence[ValuationAssumption],
    evidence_index: Mapping[str, EvidenceRef],
    price: CurrentPrice,
    parse_errors: Sequence[str] = (),
    method: str = "forward_earnings_multiple",
) -> ValuationResult:
    """一次估值執行。任何一段缺料都以 `missing`＋理由現形，不讓整體失敗、也不補預設值。"""
    if method not in VALUATION_METHODS:
        raise ValueError(f"valuation method 未登記：{method!r}；已知 {VALUATION_METHODS}")
    metric_name, _unit = METHOD_FUNDAMENTAL_INPUT[method]
    parameter = next(iter(METHOD_PARAMETERS[method]))
    cutoff = as_of or today
    warnings: list[str] = []
    steps: list[ValuationStep] = []
    reason: str | None = None

    # ---- 1. 內部指標（照抄，不重算）------------------------------------------------
    fundamental_input: FundamentalInput | None = None
    target: FiscalPeriod | None = None
    currency: str | None = None
    if fundamental is None:
        reason = fundamental_reason or "本次未執行 fundamental model——沒有內部 EPS 就沒有估值"
    else:
        metric = fundamental.metrics.get(metric_name)
        currency = fundamental.base_actuals.currency if fundamental.base_actuals else None
        target = fundamental.target_period
        if metric is None:
            reason = f"fundamental model 沒有 {metric_name} 輸出"
        else:
            fundamental_input = FundamentalInput.from_metric(metric, currency=currency)
            if not fundamental_input.is_known:
                reason = f"內部 {metric_name} 缺席：{metric.reason or fundamental.reason or '未知'}（不是 0）"
        if fundamental.as_of != as_of:
            warnings.append("fundamental model 的 as_of 與估值視角不符——拒用（INV-6）")
            fundamental_input, reason = None, "fundamental model 是在不同 as-of 視角下算的，拒用（INV-6）"
    if fundamental_input is not None:
        steps.append(ValuationStep(
            key=f"internal_{metric_name}", label=f"內部稀釋 EPS（{fundamental_input.period.label}，{fundamental_input.accounting_basis}）",
            kind="fundamental_input", value=fundamental_input.value, unit=fundamental_input.unit,
            basis="deterministic" if fundamental_input.is_known else "none",
            formula=fundamental_input.formula, assumption_ids=fundamental_input.assumption_ids,
            observation_refs=fundamental_input.observation_refs, reason=fundamental_input.reason,
            input_dependency=fundamental_input.input_dependency))
    else:
        steps.append(ValuationStep(key=f"internal_{metric_name}", label="內部稀釋 EPS", kind="fundamental_input",
                                   value=None, unit="currency_per_share", basis="none", reason=reason))

    # ---- 2. 估值假設選取（as-of／期間／supersede／證據解析）-----------------------------
    index: dict[str, EvidenceRef] = dict(evidence_index)
    model_evidence: list[EvidenceRef] = []
    if fundamental is not None:
        for ref in fundamental.evidence:
            index.setdefault(ref.ref, ref)
    if target is not None:
        accepted, selection = select_valuation_assumptions(
            assumption_records, target=target, as_of=as_of, today=today,
            evidence_index=index, parse_errors=parse_errors)
    else:
        accepted = ()
        selection = AssumptionSelection(
            input_count=len(assumption_records) + len(parse_errors), accepted_count=0,
            reasons={"no_target_period": len(assumption_records) + len(parse_errors)})
    for record in accepted:
        if record.created_on > cutoff:                       # select 已擋；這裡是 PIT 自我核對
            raise AssertionError("select_valuation_assumptions 放行了 as-of 之後的假設")

    # 同一個 method／parameter 只會有一條生效（同 key 最新者勝出）；別的 method 的假設不參與。
    wanted_key = (f"{method}.{parameter}", "total")
    chosen = [a for a in accepted if a.key == wanted_key]
    others = [a for a in accepted if a.key != wanted_key]
    if others:
        warnings.append(f"{len(others)} 條生效估值假設屬於其他 method，本次未用："
                        + "、".join(a.driver for a in others))
    assumption: ValuationAssumption | None = chosen[0] if chosen else None

    fair_value: float | None = None
    dependency: str | None = None
    formula: str | None = None
    basis_used: str | None = fundamental_input.accounting_basis if fundamental_input else None
    if assumption is None:
        if reason is None:
            reason = ("沒有生效的估值假設（" + "；".join(f"{k}={v}" for k, v in selection.reasons.items()) + "）"
                      if selection.input_count else
                      f"尚未寫入任何估值假設（{method}.{parameter}）——沒有 explicit target multiple 就沒有 fair value，不補預設")
        steps.append(ValuationStep(key=parameter, label="目標本益比假設", kind="assumption", value=None,
                                   unit="multiple", basis="none", reason=reason))
    else:
        steps.append(ValuationStep(
            key=parameter, label=f"目標本益比假設（{assumption.period.label}，{assumption.accounting_basis}）",
            kind="assumption", value=assumption.value, unit=assumption.unit, basis=assumption.basis,
            assumption_ids=(assumption.assumption_id,), observation_refs=tuple(assumption.evidence_refs),
            reason=assumption.rationale[:200]))
        if fundamental_input is not None and fundamental_input.is_known:
            # 期間與口徑是身分：不合就是 missing，且理由要說是「不合」不是「缺」。
            if not assumption.period.same_as(fundamental_input.period):
                reason = (f"估值假設針對 {assumption.period.label}（至 {assumption.period.end}），內部 EPS 是 "
                          f"{fundamental_input.period.label}（至 {fundamental_input.period.end}）——不同會計期間不得相乘")
            elif assumption.accounting_basis != fundamental_input.accounting_basis:
                reason = (f"估值假設口徑 {assumption.accounting_basis}，內部 EPS 口徑 {fundamental_input.accounting_basis}"
                          "——GAAP／non-GAAP 不得混算（不是缺假設，是口徑不合）")
            else:
                fair_value = _fair_value(method, fundamental_input, assumption)
                dependency = combined_input_dependency(fundamental_input.input_dependency, [assumption])
                formula = FAIR_VALUE_FORMULA[method]
                for ref in assumption.evidence_refs:
                    if ref in index:
                        model_evidence.append(index[ref])
    all_ids = (tuple(fundamental_input.assumption_ids) if fundamental_input else ()) \
        + ((assumption.assumption_id,) if assumption is not None else ())
    if fair_value is not None:
        steps.append(ValuationStep(
            key="fair_value", label=f"Fair value（{target.label if target else '?'}）", kind="derived",
            value=fair_value, unit="currency_per_share", basis="deterministic", formula=formula,
            assumption_ids=all_ids, observation_refs=fundamental_input.observation_refs if fundamental_input else (),
            input_dependency=dependency))
    else:
        steps.append(ValuationStep(key="fair_value", label="Fair value", kind="derived", value=None,
                                   unit="currency_per_share", basis="none", reason=reason or "上游缺料"))

    # ---- 3. 現價與 gap（price 不進 fair value）----------------------------------------
    gap = _gap(fair_value, price, currency=currency)
    if gap.is_known and fundamental_input is not None and fundamental_input.value:
        gap = replace(gap, implied_multiple_at_price=price.value / fundamental_input.value)  # type: ignore[operator]

    # ---- 4. 敏感度：每條輸入判斷動一格，fair value 動多少 ----------------------------
    sensitivities: list[FairValueSensitivity] = []
    if fair_value is not None and assumption is not None and fundamental is not None:
        for s in fundamental.sensitivities:
            delta = (s.delta_eps * assumption.value) if s.delta_eps is not None else None
            sensitivities.append(FairValueSensitivity(
                assumption_id=s.assumption_id, driver=s.driver, scope=s.scope, bump=s.bump, bump_unit=s.bump_unit,
                delta_fair_value=delta, fair_value_relative=(delta / fair_value) if (delta is not None and fair_value) else None))
        bumped = _fair_value(method, fundamental_input, replace(assumption, value=assumption.value * (1 + _RELATIVE_BUMP)))  # type: ignore[arg-type]
        sensitivities.append(FairValueSensitivity(
            assumption_id=assumption.assumption_id, driver=assumption.driver, scope=assumption.scope,
            bump=_RELATIVE_BUMP, bump_unit="relative", delta_fair_value=bumped - fair_value,
            fair_value_relative=(bumped - fair_value) / fair_value if fair_value else None))

    # ---- 5. 認識論分解（純計數／選取；回答「多少是算術、多少是判斷」）-------------------
    epistemics: dict[str, Any] = {}
    if fair_value is not None and assumption is not None and fundamental is not None:
        op_by_basis: dict[str, int] = {}
        for a in fundamental.assumptions:
            if a.assumption_id in (fundamental_input.assumption_ids if fundamental_input else ()):
                op_by_basis[a.basis] = op_by_basis.get(a.basis, 0) + 1
        epistemics = {
            "deterministic": ["財務橋算術（fundamental-bridge）", f"估值算術（{formula}）",
                              "基期實際值（Engine C mechanical 觀測）"],
            "judgment_inputs": {
                "operating_assumptions": {"count": sum(op_by_basis.values()), "by_basis": op_by_basis},
                "valuation_assumptions": {"count": 1, "by_basis": {assumption.basis: 1}},
            },
            "fair_value_input_dependency": dependency,
            "multiple_share_of_gap": ("gap 完全可寫成 target_pe / implied_multiple_at_price − 1：給定內部 EPS，"
                                      "整個 gap 就是「我們的倍數 vs 市場對我們 EPS 付的倍數」；EPS 本身的判斷"
                                      "則藏在 implied_multiple_at_price 與市場對共識 EPS 付的倍數之差裡"),
            "note": "沒有任何一個輸入數字是觀測到的 fair value；fair value 是判斷的確定性函數，不是事實",
        }

    status = "available" if fair_value is not None else "missing"
    digest = content_digest({
        "company_id": company_id, "ticker": ticker, "as_of": as_of, "method": method,
        "target": target, "fundamental_digest": fundamental.digest if fundamental else None,
        "assumption": assumption.assumption_id if assumption else None,
        "price": (price.value, price.bar_date),
    })
    return ValuationResult(
        company_id=company_id, ticker=ticker, as_of=as_of, method=method, status=status, reason=reason,
        target_period=target, accounting_basis=basis_used, fundamental_input=fundamental_input,
        assumptions=tuple(chosen), selection=selection, fair_value=fair_value, currency=currency if fair_value is not None else None,
        formula=formula, input_dependency=dependency, steps=tuple(steps), current_price=price, gap=gap,
        sensitivities=tuple(sensitivities), epistemics=epistemics, digest=digest, warnings=tuple(warnings),
        evidence=tuple({r.ref: r for r in model_evidence}.values()),
    )


__all__ = ["GAP_FORMULA", "IMPLIED_MULTIPLE_FORMULA", "build_valuation"]
