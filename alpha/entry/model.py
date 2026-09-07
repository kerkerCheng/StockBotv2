"""`build_entry_assessment()`——implied return（現價、fair value、時點、horizon、年化隱含報酬）＋ 明示的要求報酬判準
→ 確定性的 analytical entry threshold。

```
ImpliedReturnResult（alpha/implied_return；現價／fair value／value_date／horizon／年化）─┐
EntryCriterion[]（投資人政策 ledger）── select(as_of) ───────────────────────────────┼─► build_entry_assessment ─► EntryAssessmentResult
                                                                                       │   entry_price ＝ fair_value / (1 + h) ** (days / 365.25)
                                                                                       │   gap ＝ current_price / entry_price − 1
                                                                                       └   comparison ＝ current_price <= entry_price ? meets : above
```

## 五條規則

1. **兩個輸入缺一就是 `missing`**：可用的 implied return（它自己已要求現價／fair value／時點／horizon 齊全）與
   生效的判準。理由**分開寫**：判準缺席是「投資門檻尚未宣告」，不是資料 ETL 失敗；不 invent 10%／15%／20%。
2. **判準是注入的輸入，不是本層的判斷。** 本層不猜、不補預設、不自動改；`criterion_basis` 另列，不混進研究側
   的 `input_dependency`。
3. **alignment 不對齊就不是 clean。** `aligned`／`spot_value_realized_over_horizon`（明示）→ `clean`；
   `horizon_before_value_date`／`horizon_after_value_date` → 算術照列、`assessment=review_required`＋理由。
4. **只有算術比較，沒有 action。** `meets_analytical_hurdle` 是「現價 ≤ 門檻價」；型別裡沒有 buy／sell／size。
5. **算術確定、輸入是判斷。** `calculation=deterministic`；`input_dependency`＝implied return 的輸入依賴。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from ..contracts import content_digest
from ..fundamental.contracts import AssumptionSelection
from ..implied_return.contracts import (
    ALIGNMENT_HORIZON_AFTER, ALIGNMENT_HORIZON_BEFORE, ALIGNMENT_SPOT, DAYS_PER_YEAR, ImpliedReturnResult,
)
from ..valuation.contracts import VALUE_DATE_UNSPECIFIED, CurrentPrice
from .contracts import (
    ASSESSMENT_CLEAN, ASSESSMENT_REVIEW_REQUIRED, CLEAN_ALIGNMENTS, COMPARISON_ABOVE, COMPARISON_MEETS,
    CONVENTION_ANNUALIZED_PRICE_RETURN, ENTRY_PRICE_FORMULA, HURDLE_COMPARISON_RULE, PRICE_TO_ENTRY_GAP_FORMULA,
    EntryAssessmentResult, EntryCriterion, EntryStep,
)
from .criteria import select_entry_criteria

THIS_IS_NOT: tuple[str, ...] = (
    "buy／sell／hold 建議（型別裡沒有 action 欄位）",
    "position size／capital allocation／order（系統不給部位尺寸；買多少、何時買由使用者判斷）",
    "portfolio permission（A5 是唯一能授權資本的地方，且 live 100% 人工）",
    "probability-weighted expected return 或 total return 的門檻（上游 implied return 本身沒有那些）",
    "opportunity ranking／回測／統計勝率",
)

_NO_CRITERION_REASON = ("缺投資門檻判斷（entry criterion）：尚未宣告任何 required-return 判準——"
                        "這不是資料 ETL 缺口，是使用者尚未寫下「要求多少年化報酬」；不補 10%／15%／20%")


def _entry_price(fair_value: float, hurdle: float, days: int) -> float:
    return fair_value / (1.0 + hurdle) ** (days / DAYS_PER_YEAR)


def _gap(price: float, entry_price: float) -> tuple[float, float]:
    return price / entry_price - 1.0, price - entry_price


def _comparison(price: float, entry_price: float) -> str:
    return COMPARISON_MEETS if price <= entry_price else COMPARISON_ABOVE


def _assessment(alignment: str | None, value_date: date | None, horizon_end: date | None) -> tuple[str, str | None]:
    if alignment in CLEAN_ALIGNMENTS:
        if alignment == ALIGNMENT_SPOT:
            return ASSESSMENT_CLEAN, ("fair value 是 spot 值（估值視角日的值）；entry price 假設現價在 horizon 內收斂到它，"
                                      "hurdle 以整段持有期間折現——這是明示的讀法，不是預設")
        return ASSESSMENT_CLEAN, None
    if alignment == ALIGNMENT_HORIZON_BEFORE:
        return ASSESSMENT_REVIEW_REQUIRED, (f"horizon_end {horizon_end} 早於 value_date {value_date}：fair value 定義在較晚的日期，"
                                            "entry price 卻以較短期間折現——算術照列，但不得當 clean 的門檻價；請先確認 horizon 判斷")
    if alignment == ALIGNMENT_HORIZON_AFTER:
        return ASSESSMENT_REVIEW_REQUIRED, (f"horizon_end {horizon_end} 晚於 value_date {value_date}：fair value 定義在較早的日期，"
                                            "entry price 卻以較長期間折現——算術照列，但不得當 clean 的門檻價；請先確認 horizon 判斷")
    return ASSESSMENT_REVIEW_REQUIRED, "value_date 與 horizon_end 的關係未知——不得當 clean 的門檻價"


def _missing(
    *, company_id: str, ticker: str, as_of: date | None, reason: str, upstream: ImpliedReturnResult | None,
    upstream_reason: str | None, price: CurrentPrice, criterion: EntryCriterion | None,
    selection: AssumptionSelection, criterion_reason: str | None, steps: Sequence[EntryStep], warnings: Sequence[str],
) -> EntryAssessmentResult:
    ok = upstream is not None
    return EntryAssessmentResult(
        company_id=company_id, ticker=ticker, as_of=as_of, status="missing", reason=reason,
        convention=CONVENTION_ANNUALIZED_PRICE_RETURN, criterion=criterion, criterion_selection=selection,
        criterion_reason=criterion_reason,
        implied_return_status=(upstream.status if ok else "missing"),
        implied_return_reason=(upstream.reason if ok else upstream_reason),
        current_price=price, price_as_of=price.bar_date,
        fair_value=(upstream.fair_value if ok else None), fair_value_currency=(upstream.fair_value_currency if ok else None),
        value_date=(upstream.value_date if ok else None),
        value_date_semantics=(upstream.value_date_semantics if ok else VALUE_DATE_UNSPECIFIED),
        target_period=(upstream.target_period if ok else None), horizon=(upstream.horizon if ok else None),
        horizon_start=(upstream.horizon_start if ok else None), horizon_end=(upstream.horizon_end if ok else None),
        holding_period_days=(upstream.holding_period_days if ok else None),
        required_annualized_return=None,
        # 上游照抄值：缺判準時仍看得見「現在的年化隱含報酬是多少」——那正是決定要不要宣告 hurdle 的資訊。
        current_annualized_implied_return=(upstream.annualized_price_return if ok else None), entry_price=None,
        price_to_entry_gap=None, price_to_entry_gap_abs=None, hurdle_comparison=None, assessment=None,
        assessment_reason=None, alignment=(upstream.alignment if ok else None), input_dependency=None,
        criterion_basis=(criterion.basis if criterion is not None else None), steps=tuple(steps),
        research_assumption_ids=(tuple(upstream.assumption_ids) if ok else ()),
        observation_refs=(tuple(upstream.observation_refs) if ok else tuple(price.evidence_refs)),
        epistemics={"this_is_not": list(THIS_IS_NOT)},
        digest=content_digest({"company_id": company_id, "ticker": ticker, "as_of": as_of, "status": "missing",
                               "reason": reason}),
        warnings=tuple(warnings),
    )


def build_entry_assessment(
    *,
    company_id: str,
    ticker: str,
    as_of: date | None,
    today: date,
    implied_return: ImpliedReturnResult | None,
    implied_return_reason: str | None,
    criterion_records: Sequence[EntryCriterion],
    parse_errors: Sequence[str] = (),
    price: CurrentPrice | None = None,
) -> EntryAssessmentResult:
    """一次 entry 評估。任何一段缺料都以 `missing`＋理由現形，不讓整體失敗、也不補預設值。

    `price` 只在 `implied_return is None` 時用來保留現價格（讓 read model 仍印得出現價）；有上游時一律照抄上游的現價。
    """
    cutoff = as_of or today
    warnings: list[str] = []
    steps: list[EntryStep] = []

    # ---- 1. 判準選取（as-of／supersede／retract；沒有期間、沒有證據解析）--------------------------
    accepted, selection = select_entry_criteria(criterion_records, as_of=as_of, today=today, parse_errors=parse_errors)
    for record in accepted:
        if record.created_on > cutoff:                       # select 已擋；這裡是 PIT 自我核對
            raise AssertionError("select_entry_criteria 放行了 as-of 之後的判準")
    criterion: EntryCriterion | None = accepted[0] if accepted else None
    if criterion is None:
        if selection.input_count:
            criterion_reason: str | None = ("沒有生效的 entry criterion（"
                                            + "；".join(f"{k}={v}" for k, v in selection.reasons.items()) + "）——不補預設")
        else:
            criterion_reason = _NO_CRITERION_REASON
        steps.append(EntryStep(key="required_annualized_return", label="要求年化價格報酬（投資人判準）",
                               kind="criterion_input", value=None, unit="ratio", basis="none", reason=criterion_reason))
    else:
        criterion_reason = None
        steps.append(EntryStep(
            key="required_annualized_return", label=f"要求年化價格報酬（{criterion.author} 宣告的投資人政策）",
            kind="criterion_input", value=criterion.value, unit="ratio", basis=criterion.basis,
            assumption_ids=(criterion.criterion_id,), observation_refs=tuple(criterion.reference_refs),
            reason=criterion.rationale[:200]))

    # ---- 2. 上游 implied return（照抄，不重算）-----------------------------------------------------
    if implied_return is not None and implied_return.as_of != as_of:
        implied_return_reason = "implied return 是在不同 as-of 視角下算的，拒用（INV-6）"
        warnings.append(implied_return_reason)
        implied_return = None
    upstream_price = implied_return.current_price if implied_return is not None else price
    if upstream_price is None:
        upstream_price = CurrentPrice(value=None, bar_date=None, unit=None, evidence_refs=(),
                                      reason="呼叫端未提供現價")
    if implied_return is not None and implied_return.is_known:
        steps.append(EntryStep(key="current_price", label=f"現價（Engine C，bar {implied_return.horizon_start}）",
                               kind="price_input", value=upstream_price.value,
                               unit=f"quote_unit（{upstream_price.unit or '未知'}）", basis="observation",
                               observation_refs=tuple(upstream_price.evidence_refs)))
        steps.append(EntryStep(
            key="fair_value", label=f"Fair value（{implied_return.target_period.label if implied_return.target_period else '?'}；"
                                     f"{implied_return.value_date_semantics}，value_date {implied_return.value_date}）",
            kind="return_input", value=implied_return.fair_value, unit="currency_per_share", basis="deterministic",
            assumption_ids=tuple(a for a in implied_return.assumption_ids if not a.startswith("ha_")),
            input_dependency=implied_return.input_dependency))
        steps.append(EntryStep(
            key="holding_period_days", label=f"持有期間（{implied_return.horizon_start} → {implied_return.horizon_end}）",
            kind="return_input", value=implied_return.holding_period_days, unit="days", basis="deterministic",
            formula=implied_return.formulas["holding_period"],
            assumption_ids=((implied_return.horizon.assumption_id,) if implied_return.horizon else ())))
        steps.append(EntryStep(
            key="current_annualized_implied_return", label="現價的年化隱含價格報酬（照抄 implied return）",
            kind="return_input", value=implied_return.annualized_price_return, unit="ratio",
            basis="deterministic" if implied_return.annualized_price_return is not None else "none",
            formula=implied_return.formulas["annualized_price_return"], assumption_ids=tuple(implied_return.assumption_ids),
            input_dependency=implied_return.input_dependency,
            reason=(None if implied_return.annualized_price_return is not None else "持有期間不足 1 天，上游未年化")))
    else:
        why = (implied_return.reason if implied_return is not None else
               (implied_return_reason or "本次未執行 implied return model——沒有 implied return 就沒有門檻價"))
        steps.append(EntryStep(key="fair_value", label="Fair value／horizon（照抄 implied return）", kind="return_input",
                               value=None, unit="currency_per_share", basis="none",
                               reason=f"上游 implied return 缺席：{why}"))

    # ---- 3. 缺料判定：上游先於判準（兩者都缺時理由並列）--------------------------------------------
    def _stop(reason: str) -> EntryAssessmentResult:
        return _missing(company_id=company_id, ticker=ticker, as_of=as_of, reason=reason, upstream=implied_return,
                        upstream_reason=implied_return_reason, price=upstream_price, criterion=criterion,
                        selection=selection, criterion_reason=criterion_reason, steps=steps, warnings=warnings)

    blockers: list[str] = []
    if implied_return is None or not implied_return.is_known:
        why = (implied_return.reason if implied_return is not None else implied_return_reason) or "implied return 缺席"
        blockers.append(f"上游 implied return 缺席（{why}）")
    if criterion is None:
        blockers.append(criterion_reason or _NO_CRITERION_REASON)
    if blockers:
        return _stop("；另：".join(blockers))
    assert implied_return is not None and criterion is not None
    if implied_return.annualized_price_return is None or implied_return.holding_period_days is None:
        return _stop("上游持有期間不足 1 天，沒有年化隱含報酬可比——不猜")
    if upstream_price.value is None or upstream_price.value <= 0:
        return _stop("現價缺席或非正——門檻價比較無定義")

    # ---- 4. 確定性算術 -------------------------------------------------------------------------
    hurdle = criterion.value
    days = implied_return.holding_period_days
    fair_value = implied_return.fair_value
    price_value = upstream_price.value
    entry_price = _entry_price(fair_value, hurdle, days)                    # type: ignore[arg-type]
    gap_rel, gap_abs = _gap(price_value, entry_price)
    comparison = _comparison(price_value, entry_price)
    assessment, assessment_reason = _assessment(implied_return.alignment, implied_return.value_date,
                                                implied_return.horizon_end)
    dependency = implied_return.input_dependency
    research_ids = tuple(implied_return.assumption_ids)
    obs_refs = tuple(implied_return.observation_refs)
    all_ids = research_ids + (criterion.criterion_id,)
    steps.append(EntryStep(key="entry_price", label="Analytical entry price（現價等於它時年化隱含報酬＝hurdle）",
                           kind="derived", value=entry_price, unit="currency_per_share", basis="deterministic",
                           formula=ENTRY_PRICE_FORMULA, assumption_ids=all_ids, observation_refs=obs_refs,
                           input_dependency=dependency))
    steps.append(EntryStep(key="price_to_entry_gap", label="現價相對門檻價（相對）", kind="derived", value=gap_rel,
                           unit="ratio", basis="deterministic", formula=PRICE_TO_ENTRY_GAP_FORMULA,
                           assumption_ids=all_ids, observation_refs=obs_refs, input_dependency=dependency))
    steps.append(EntryStep(key="hurdle_comparison", label="現價 vs 門檻價（算術比較，不是 action）", kind="derived",
                           value=comparison, unit="enum", basis="deterministic", formula=HURDLE_COMPARISON_RULE,
                           assumption_ids=all_ids, observation_refs=obs_refs, input_dependency=dependency))
    if assessment == ASSESSMENT_REVIEW_REQUIRED:
        warnings.append(f"assessment=review_required：{assessment_reason}")
    elif assessment_reason:
        warnings.append(assessment_reason)
    if criterion.author.lower() == "sandbox":
        warnings.append("判準是 SANDBOX（非持久、未寫入 ledger）——這份結果只用來驗算，不是使用者宣告的政策")
    warnings.extend(implied_return.warnings)

    epistemics: dict[str, Any] = {
        "deterministic": ["門檻價算術（fair_value / (1+h)^(days/365.25)）", "gap 算術", "比較（current_price <= entry_price）",
                          "上游：報酬／年化／持有期間／估值／橋算術"],
        "judgment_inputs": {
            "research_side": {"assumption_ids": list(research_ids), "input_dependency": dependency},
            "criterion": {"criterion_id": criterion.criterion_id, "basis": criterion.basis, "author": criterion.author,
                          "created_at": criterion.created_at.isoformat()},
        },
        "observations": ["現價（Engine C snapshot）", "基期實際值（Engine C mechanical 觀測）"],
        "input_dependency": dependency,
        "criterion_basis": criterion.basis,
        "this_is_not": list(THIS_IS_NOT),
        "one_sentence": (f"在要求年化 {hurdle:+.1%}（{criterion.basis}，{criterion.criterion_id}）下，"
                         f"{implied_return.target_period.label if implied_return.target_period else '?'} fair value "
                         f"{fair_value:.2f}（{implied_return.value_date} 的值）於 {implied_return.horizon_end} 前實現的"
                         f"門檻價是 {entry_price:.2f}；現價 {price_value:g}（bar {implied_return.horizon_start}）"
                         f"{'低於或等於' if comparison == COMPARISON_MEETS else '高於'}門檻價 {abs(gap_rel):.1%}"
                         f"——{comparison}；年化隱含 {implied_return.annualized_price_return:+.1%} vs 要求 {hurdle:+.1%}；"
                         f"assessment={assessment}；這不是買賣建議、不是部位"),
    }
    digest = content_digest({"company_id": company_id, "ticker": ticker, "as_of": as_of,
                             "implied_return_digest": implied_return.digest, "criterion": criterion.criterion_id})
    return EntryAssessmentResult(
        company_id=company_id, ticker=ticker, as_of=as_of, status="available", reason=None,
        convention=CONVENTION_ANNUALIZED_PRICE_RETURN, criterion=criterion, criterion_selection=selection,
        criterion_reason=None, implied_return_status=implied_return.status, implied_return_reason=None,
        current_price=upstream_price, price_as_of=upstream_price.bar_date, fair_value=fair_value,
        fair_value_currency=implied_return.fair_value_currency, value_date=implied_return.value_date,
        value_date_semantics=implied_return.value_date_semantics, target_period=implied_return.target_period,
        horizon=implied_return.horizon, horizon_start=implied_return.horizon_start, horizon_end=implied_return.horizon_end,
        holding_period_days=days, required_annualized_return=hurdle,
        current_annualized_implied_return=implied_return.annualized_price_return, entry_price=entry_price,
        price_to_entry_gap=gap_rel, price_to_entry_gap_abs=gap_abs, hurdle_comparison=comparison, assessment=assessment,
        assessment_reason=assessment_reason, alignment=implied_return.alignment, input_dependency=dependency,
        criterion_basis=criterion.basis, steps=tuple(steps), research_assumption_ids=research_ids,
        observation_refs=obs_refs, epistemics=epistemics, digest=digest, warnings=tuple(warnings),
    )


__all__ = ["THIS_IS_NOT", "build_entry_assessment"]
