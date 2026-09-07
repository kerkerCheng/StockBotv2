"""Entry Logic v1（`alpha/entry`，Phase 2 Step 3）的測試——純邏輯＋refresh＋read model 整合＋authority 邊界。

守的是 Step 3 的驗收：
1. 沒有判準 → missing（缺的是「投資門檻判斷」，不是 ETL 失敗；不 invent 10%／15%／20%）；
2. 現價 > 門檻價／3. 現價 < 門檻價／4. 現價 == 門檻價（三種比較都只是算術，不是 action）；
5. hurdle 變高 → entry price 單調下降；6. price-only → 確定性重算；7. 估值／horizon 上游 review 傳播；
8. alignment 不對齊不得當 clean；9. criterion supersede；10. 歷史 PIT；11. Missing != Zero；12. 決定性；
13. **沒有 buy／sell／sizing／portfolio authority 洩漏**；14. renderer／builder 不重算公式。
"""
from __future__ import annotations

import ast
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.entry import (
    ASSESSMENT_CLEAN, ASSESSMENT_REVIEW_REQUIRED, COMPARISON_ABOVE, COMPARISON_MEETS,
    CONVENTION_ANNUALIZED_PRICE_RETURN, ENTRY_PRICE_FORMULA, FORBIDDEN_ENTRY_TOKENS, EntryAssessmentResult,
    EntryCriterion, build_entry_assessment, entry_criterion_record, parse_entry_criterion_record,
)
from alpha.errors import ContractViolation
from alpha.implied_return import DAYS_PER_YEAR
from alpha.refresh import (
    ARTIFACT_ENTRY_ASSESSMENT, ARTIFACT_ENTRY_CRITERION, ARTIFACT_FAIR_VALUE, ARTIFACT_HORIZON_ASSUMPTION,
    ARTIFACT_IMPLIED_RETURN, ARTIFACT_VALUATION_ASSUMPTION, CURRENT, ENTRY_CRITERION, GRAPH_EDGE, MARKET_PRICE,
    RECALCULATE, REVIEW_REQUIRED, STALE, SUPERSEDED, ChangeEvent, artifacts_from_entry,
    artifacts_from_implied_return, artifacts_from_model, artifacts_from_valuation, end_of_day, resolve_refresh,
)
from alpha.refresh.policy import DERIVED_CLASS_POLICY
from alpha.valuation import CurrentPrice
from tests.test_fundamental_model import ACT_REF, TARGET, _run
from tests.test_implied_return import H_CREATED, TODAY, _horizon, _return, _valued
from tests.test_valuation_model import EDGE, PRICE, SNAP, _index

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
C_CREATED = datetime(2026, 9, 6, 10, 0, tzinfo=UTC)


def _criterion(value: float = 0.15, *, basis: str = "investor_policy", created: datetime = C_CREATED,
               author: str = "user", **kw) -> EntryCriterion:
    record = entry_criterion_record(
        company_id="co:coherent", ticker="COHR", value=value, basis=basis,
        rationale=f"test hurdle {value}", created_at=created, author=author, **kw)
    return parse_entry_criterion_record(record)


def _entry(implied=None, criteria=None, *, as_of: date | None = None, today: date = TODAY,
           implied_reason: str | None = None, price: CurrentPrice | None = None) -> EntryAssessmentResult:
    if implied is None and implied_reason is None:
        implied = _return(as_of=as_of, today=today)
    return build_entry_assessment(
        company_id="co:coherent", ticker="COHR", as_of=as_of, today=today, implied_return=implied,
        implied_return_reason=implied_reason,
        criterion_records=[_criterion()] if criteria is None else criteria, price=price)


# ---------------------------------------------------------------------------
# 1. 沒有判準 → missing（缺的是投資門檻判斷，不是 ETL）
# ---------------------------------------------------------------------------

def test_no_criterion_is_missing_and_names_the_missing_judgment_not_an_etl_gap() -> None:
    result = _entry(criteria=[])
    assert result.status == "missing"
    assert result.entry_price is None and result.price_to_entry_gap is None
    assert result.required_annualized_return is None and result.hurdle_comparison is None
    assert result.assessment is None and result.input_dependency is None
    assert "投資門檻判斷" in (result.reason or "") and "不是資料 ETL 缺口" in (result.reason or "")
    # **不得** invent 任何常見 hurdle：模型與契約的原始碼裡不存在可當預設值的 10%／15%／20% 常數
    for rel in ("alpha/entry/model.py", "alpha/entry/contracts.py", "alpha/entry/criteria.py"):
        source = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)}
        assert not (literals & {0.10, 0.12, 0.15, 0.20, 0.25}), (rel, literals)
    assert all(s.value is None for s in result.steps if s.kind == "criterion_input")
    # 上游明明是好的：缺的只有判準這一格——**上游照抄值仍然看得見**，包括現在的年化隱含報酬
    # （讀者要先知道「現在隱含幾 %」才知道自己該不該宣告 hurdle；把它一起吞掉會讓缺口看起來比實際更大）
    assert result.implied_return_status == "available" and result.fair_value is not None
    assert result.horizon_end == date(2027, 6, 30) and result.criterion is None
    assert result.current_annualized_implied_return is not None
    assert result.current_annualized_implied_return == pytest.approx(-0.2464, abs=5e-4)
    # 但本層自己算的三格一定是 None（missing != zero）
    assert (result.entry_price, result.price_to_entry_gap, result.required_annualized_return) == (None, None, None)
    assert result.criterion_selection.input_count == 0
    step = next(s for s in result.steps if s.key == "required_annualized_return")
    assert step.value is None and step.basis == "none" and "投資門檻判斷" in (step.reason or "")
    # 有紀錄但都被拒（全撤回）→ 一樣 missing，理由帶計數
    retracted = _criterion(0.15, supersedes_id=_criterion().criterion_id, retracted=True,
                           created=C_CREATED + timedelta(days=1))
    gone = _entry(criteria=[_criterion(), retracted], today=date(2026, 9, 10))
    assert gone.status == "missing" and "retracted=1" in (gone.reason or "")


def test_missing_upstream_and_missing_criterion_are_reported_separately() -> None:
    """上游缺席與判準缺席是兩個不同的洞——理由必須分開講（L12：兩種語意不得同形）。"""
    model = _run(index=_index())
    no_horizon = _return(_valued(model), [])
    both = build_entry_assessment(company_id="co:coherent", ticker="COHR", as_of=None, today=TODAY,
                                  implied_return=no_horizon, implied_return_reason=None, criterion_records=[])
    assert both.status == "missing"
    assert "上游 implied return 缺席" in (both.reason or "") and "投資門檻判斷" in (both.reason or "")
    upstream_only = build_entry_assessment(company_id="co:coherent", ticker="COHR", as_of=None, today=TODAY,
                                           implied_return=no_horizon, implied_return_reason=None,
                                           criterion_records=[_criterion()])
    assert upstream_only.status == "missing" and "上游 implied return 缺席" in (upstream_only.reason or "")
    assert "投資門檻判斷" not in (upstream_only.reason or "")     # 判準在，不該被算進缺口
    assert upstream_only.criterion is not None and upstream_only.criterion_reason is None
    none_at_all = build_entry_assessment(company_id="co:coherent", ticker="COHR", as_of=None, today=TODAY,
                                         implied_return=None, implied_return_reason="provider 無 fiscal 能力",
                                         criterion_records=[_criterion()])
    assert none_at_all.status == "missing" and "provider 無 fiscal 能力" in (none_at_all.reason or "")


# ---------------------------------------------------------------------------
# 2–4. 現價高於／低於／等於門檻價
# ---------------------------------------------------------------------------

def test_price_above_below_and_exactly_at_the_entry_price() -> None:
    model = _run(index=_index())
    hurdle = 0.15
    days = 299

    def _at(price_value: float):
        price = replace(PRICE, value=price_value)
        return _entry(_return(_valued(model, price=price), price=price), [_criterion(hurdle)])

    # 先用現價算出門檻價，再拿門檻價本身回頭當現價 → 必須恰好是 meets（等號那條邊）
    base = _at(281.86)
    fair_value = base.fair_value
    expected = fair_value / (1 + hurdle) ** (days / DAYS_PER_YEAR)
    assert base.entry_price == pytest.approx(expected)
    assert base.hurdle_comparison == COMPARISON_ABOVE and base.price_to_entry_gap > 0
    assert base.price_to_entry_gap == pytest.approx(281.86 / expected - 1)
    assert base.price_to_entry_gap_abs == pytest.approx(281.86 - expected)
    assert base.current_annualized_implied_return < hurdle          # 高於門檻價 ⇔ 年化隱含 < 要求

    below = _at(expected * 0.9)
    assert below.hurdle_comparison == COMPARISON_MEETS and below.price_to_entry_gap < 0
    assert below.current_annualized_implied_return > hurdle
    assert below.entry_price == pytest.approx(expected)             # 門檻價不隨現價變（fair value／horizon 沒變）

    exact = _at(expected)
    assert exact.hurdle_comparison == COMPARISON_MEETS              # `<=` 的等號歸 meets
    assert exact.price_to_entry_gap == pytest.approx(0.0, abs=1e-12)
    assert exact.price_to_entry_gap_abs == pytest.approx(0.0, abs=1e-9)
    # 等於門檻價時，年化隱含報酬恰等於 hurdle——這是門檻價的定義
    assert exact.current_annualized_implied_return == pytest.approx(hurdle, abs=1e-9)
    # 三種情況都只是算術比較，沒有任何 action 字樣
    for result in (base, below, exact):
        assert result.hurdle_comparison in (COMPARISON_MEETS, COMPARISON_ABOVE)
        assert "買" not in result.epistemics["one_sentence"].replace("不是買賣建議", "")


# ---------------------------------------------------------------------------
# 5. hurdle 變高 → entry price 單調下降
# ---------------------------------------------------------------------------

def test_higher_hurdle_monotonically_lowers_the_entry_price() -> None:
    model = _run(index=_index())
    implied = _return(_valued(model))
    prices = [(h, _entry(implied, [_criterion(h)]).entry_price) for h in (-0.05, 0.0, 0.05, 0.10, 0.15, 0.25, 0.50)]
    values = [p for _h, p in prices]
    assert values == sorted(values, reverse=True), prices          # 嚴格遞減
    assert all(a > b for a, b in zip(values, values[1:]))
    zero = next(p for h, p in prices if h == 0.0)
    assert zero == pytest.approx(implied.fair_value)               # hurdle=0 ⇒ 門檻價＝fair value
    # hurdle 是投資人政策，不受研究側影響：同一個 implied return 下只有它在動
    assert len({_entry(implied, [_criterion(h)]).fair_value for h, _p in prices}) == 1


# ---------------------------------------------------------------------------
# 6–7. refresh：price-only → recalculate；上游 review → 傳播；criterion supersede → recalculate
# ---------------------------------------------------------------------------

def _artifacts(entry, implied, valuation, model, *, criterion_records=(), horizon_records=(), valuation_records=()):
    build_at = end_of_day(TODAY)
    return (artifacts_from_model(model, build_at=build_at)
            + artifacts_from_valuation(valuation, build_at=build_at, assumption_records=valuation_records,
                                       base_period_end=model.base_period.end)
            + artifacts_from_implied_return(implied, build_at=build_at, horizon_records=horizon_records,
                                            base_period_end=model.base_period.end)
            + artifacts_from_entry(entry, build_at=build_at, criterion_records=criterion_records))


def _resolve(changes, *, entry, implied, valuation, model, today=date(2026, 9, 8), **kw):
    return resolve_refresh(ticker="COHR", company_id="co:coherent",
                           artifacts=_artifacts(entry, implied, valuation, model, **kw), changes=changes, today=today)


def test_price_only_change_recalculates_the_entry_assessment_deterministically() -> None:
    model = _run(index=_index())
    valuation = _valued(model)
    implied = _return(valuation)
    criterion = _criterion()
    entry = _entry(implied, [criterion])
    later = datetime(2026, 9, 8, 12, tzinfo=UTC)
    dep = next(a for a in _artifacts(entry, implied, valuation, model) if a.artifact_type == ARTIFACT_ENTRY_ASSESSMENT)
    assert dep.refs.get(SNAP) == "observation" and MARKET_PRICE in DERIVED_CLASS_POLICY["entry_assessment"]
    assert dep.refs.get(criterion.criterion_id) == "input" and criterion.criterion_id in dep.assumption_ids
    report = _resolve([ChangeEvent(change_type=MARKET_PRICE, ticker="COHR", authority="t", changed_ref=SNAP,
                                   observed_at=later, material_fields=("price",))],
                      entry=entry, implied=implied, valuation=valuation, model=model)
    assert report.artifact(f"{ARTIFACT_ENTRY_ASSESSMENT}:entry_assessment").state == RECALCULATE
    assert report.artifact(f"{ARTIFACT_ENTRY_CRITERION}:{criterion.criterion_id}").state == CURRENT   # 判準不因價格重看
    assert report.artifact(f"{ARTIFACT_IMPLIED_RETURN}:implied_return").state == RECALCULATE
    # 真的重算：價格變了，門檻價不變、gap 變
    new_price = replace(PRICE, value=300.0)
    again = _entry(_return(_valued(model, price=new_price), price=new_price), [criterion])
    assert again.entry_price == pytest.approx(entry.entry_price)
    assert again.price_to_entry_gap > entry.price_to_entry_gap
    assert again.hurdle_comparison == entry.hurdle_comparison == COMPARISON_ABOVE
    # 無關的圖變化不亂 cascade
    calm = _resolve([ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", authority="t",
                                 changed_ref="graph://edge/co:someone_else/supplies_to/co:nobody", observed_at=later,
                                 material_fields=("substitutability",))],
                    entry=entry, implied=implied, valuation=valuation, model=model)
    assert calm.artifact(f"{ARTIFACT_ENTRY_ASSESSMENT}:entry_assessment").state == CURRENT
    assert calm.artifact(f"{ARTIFACT_ENTRY_CRITERION}:{criterion.criterion_id}").state == CURRENT


def test_valuation_and_horizon_upstream_review_propagates_into_the_entry_assessment() -> None:
    model = _run(index=_index())
    valuation = _valued(model)
    implied = _return(valuation)
    criterion = _criterion()
    entry = _entry(implied, [criterion])
    va_id = valuation.assumptions[0].assumption_id
    later = datetime(2026, 9, 8, 12, tzinfo=UTC)
    report = _resolve([ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", authority="t", changed_ref=EDGE,
                                   observed_at=later, material_fields=("substitutability",), detail="sub 5 → 3")],
                      entry=entry, implied=implied, valuation=valuation, model=model)
    assert report.artifact(f"{ARTIFACT_VALUATION_ASSUMPTION}:{va_id}").state == REVIEW_REQUIRED
    ent = report.artifact(f"{ARTIFACT_ENTRY_ASSESSMENT}:entry_assessment")
    assert ent.state == REVIEW_REQUIRED and f"{ARTIFACT_VALUATION_ASSUMPTION}:{va_id}" in ent.propagated_from
    # 判準本身不動——結構證據不是它的依據（它沒有 supporting evidence）
    assert report.artifact(f"{ARTIFACT_ENTRY_CRITERION}:{criterion.criterion_id}").state == CURRENT
    # horizon 到期（INV-2）→ horizon stale → implied return stale → entry assessment stale
    due = _resolve([], entry=entry, implied=implied, valuation=valuation, model=model, today=date(2027, 7, 1),
                   horizon_records=[implied.horizon])
    assert due.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{implied.horizon.assumption_id}").state == STALE
    assert due.artifact(f"{ARTIFACT_ENTRY_ASSESSMENT}:entry_assessment").state == STALE
    # read model：門檻價那格不得再當 current
    from briefing.alpha_view import compact_card
    from tests.test_alpha_investment_view import _view

    edge = ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", company_id="co:coherent",
                       authority="engine_a://graph_research_provider", changed_ref=EDGE,
                       observed_at=datetime(2026, 9, 7, 23, 59, 59, tzinfo=UTC), material_fields=("substitutability",))
    view = _view(fundamental_model=model, valuation=valuation, valuation_records=list(valuation.assumptions),
                 implied_return=implied, horizon_records=[implied.horizon], entry=entry, entry_records=[criterion],
                 refresh_changes=[edge], today=TODAY)
    assert view.entry_logic.entry_price.status == "review_required"
    assert view.entry_logic.meta.status == "review_required"
    assert view.entry_logic.criterion.status == "available"
    assert compact_card(view)["entry_logic"]["status"] == "review_required"


def test_criterion_supersede_recalculates_and_only_the_newest_hurdle_is_used() -> None:
    model = _run(index=_index())
    valuation = _valued(model)
    implied = _return(valuation)
    old = _criterion(0.15)
    later = datetime(2026, 9, 8, 12, tzinfo=UTC)
    entry = _entry(implied, [old])
    report = _resolve([ChangeEvent(change_type=ENTRY_CRITERION, ticker="COHR", authority="t", changed_ref="ec_new",
                                   related_refs=(old.criterion_id,), observed_at=later)],
                      entry=entry, implied=implied, valuation=valuation, model=model)
    assert report.artifact(f"{ARTIFACT_ENTRY_ASSESSMENT}:entry_assessment").state == RECALCULATE
    assert report.artifact(f"{ARTIFACT_FAIR_VALUE}:fair_value").state == CURRENT           # 判準不動 fair value
    assert report.artifact(f"{ARTIFACT_IMPLIED_RETURN}:implied_return").state == CURRENT   # 也不動報酬
    # 真的 supersede：新紀錄勝出、舊紀錄 superseded、門檻價用新 hurdle 算
    new = _criterion(0.25, created=C_CREATED + timedelta(days=1), supersedes_id=old.criterion_id)
    result2 = _entry(implied, [old, new])
    assert result2.criterion == new and result2.required_annualized_return == 0.25
    assert result2.entry_price < entry.entry_price
    hist = _resolve([], entry=result2, implied=implied, valuation=valuation, model=model, criterion_records=[old, new])
    assert hist.artifact(f"{ARTIFACT_ENTRY_CRITERION}:{old.criterion_id}").state == SUPERSEDED
    assert hist.artifact(f"{ARTIFACT_ENTRY_CRITERION}:{new.criterion_id}").state == CURRENT
    # 撤回不讓舊值復活
    retract = _criterion(0.25, created=C_CREATED + timedelta(days=2), supersedes_id=new.criterion_id, retracted=True)
    gone = _entry(implied, [old, new, retract], today=date(2026, 9, 10))
    assert gone.status == "missing" and gone.criterion is None


# ---------------------------------------------------------------------------
# 8. alignment 不對齊不得被當 clean
# ---------------------------------------------------------------------------

def test_alignment_mismatch_is_not_a_clean_entry_result() -> None:
    model = _run(index=_index())
    valuation = _valued(model)
    aligned = _entry(_return(valuation, [_horizon(date(2027, 6, 30))]), [_criterion()])
    assert aligned.alignment == "aligned" and aligned.assessment == ASSESSMENT_CLEAN
    assert aligned.assessment_reason is None
    late = _entry(_return(valuation, [_horizon(date(2027, 12, 31), created=H_CREATED)]), [_criterion()])
    assert late.alignment == "horizon_after_value_date"
    assert late.status == "available" and late.entry_price is not None          # 算術照列
    assert late.assessment == ASSESSMENT_REVIEW_REQUIRED and "晚於 value_date" in (late.assessment_reason or "")
    assert any("review_required" in w for w in late.warnings)
    early = _entry(_return(valuation, [_horizon(date(2027, 3, 31))]), [_criterion()])
    assert early.alignment == "horizon_before_value_date" and early.assessment == ASSESSMENT_REVIEW_REQUIRED
    # spot 語意可以 clean，但必須明示理由（讀者要知道那是哪種讀法）
    spot = _entry(_return(_valued(model, convention="spot")), [_criterion()])
    assert spot.alignment == "spot_value_realized_over_horizon" and spot.assessment == ASSESSMENT_CLEAN
    assert "spot" in (spot.assessment_reason or "")
    # 型別層擋住「不對齊卻標 clean」
    with pytest.raises(ContractViolation, match="clean"):
        replace(late, assessment=ASSESSMENT_CLEAN)
    # read model：assessment=review_required 時整個 section 不得是 available
    from tests.test_alpha_investment_view import _view

    view = _view(fundamental_model=model, valuation=valuation, implied_return=_return(valuation, [_horizon(date(2027, 12, 31))]),
                 entry=late, entry_records=[_criterion()])
    assert view.entry_logic.meta.status == "review_required"
    assert view.entry_logic.assessment.value["state"] == "review_required"
    assert view.entry_logic.entry_price.is_known                                # 算術仍看得到


# ---------------------------------------------------------------------------
# 9–10. 歷史 PIT
# ---------------------------------------------------------------------------

def test_historical_view_does_not_leak_a_future_criterion() -> None:
    # 判準寫於 09-06 10:00 → as-of 09-05 不存在
    then = _entry(_return(_valued(as_of=date(2026, 9, 5)), as_of=date(2026, 9, 5)), [_criterion()],
                  as_of=date(2026, 9, 5))
    assert then.status == "missing" and then.criterion is None
    assert dict(then.criterion_selection.reasons) == {"created_after_as_of": 1}
    payload = json.dumps({"c": then.criterion_id, "reason": then.reason})
    assert "ec_" not in payload
    later = _entry(_return(_valued(as_of=date(2026, 9, 6)), as_of=date(2026, 9, 6)), [_criterion()],
                   as_of=date(2026, 9, 6))
    assert later.status == "available" and later.criterion is not None
    # 上游視角與本層視角不符 → 拒用（INV-6）
    mismatch = _entry(_return(), [_criterion()], as_of=date(2026, 9, 6))
    assert mismatch.status == "missing" and "INV-6" in " ".join(mismatch.warnings)
    # refresh：as-of 之前看不到之後建立的成果
    model = _run(index=_index())
    valuation = _valued(model)
    implied = _return(valuation)
    entry = _entry(implied, [_criterion()])
    report = resolve_refresh(ticker="COHR", company_id="co:coherent",
                             artifacts=_artifacts(entry, implied, valuation, model), as_of=date(2026, 9, 5), today=TODAY)
    assert report.artifact(f"{ARTIFACT_ENTRY_CRITERION}:{entry.criterion.criterion_id}") is None


# ---------------------------------------------------------------------------
# 11–12. Missing != Zero；決定性
# ---------------------------------------------------------------------------

def test_missing_is_never_zero_and_the_same_inputs_give_the_same_result() -> None:
    result = _entry(criteria=[])
    with pytest.raises(ContractViolation, match="missing != zero"):
        replace(result, entry_price=0.0)
    with pytest.raises(ContractViolation, match="missing"):
        replace(result, hurdle_comparison=COMPARISON_MEETS)
    ok = _entry()
    again = _entry()
    assert ok.entry_price == again.entry_price and ok.digest == again.digest
    assert ok.calculation == "deterministic" and ok.input_dependency == "session_judgment"
    assert ok.criterion_basis == "investor_policy"          # 投資人政策不混進研究依賴
    assert ok.convention == CONVENTION_ANNUALIZED_PRICE_RETURN
    assert ok.formulas["entry_price"] == ENTRY_PRICE_FORMULA
    # available 少任何一格數字都不合法
    with pytest.raises(ContractViolation, match="available"):
        replace(ok, entry_price=None)
    with pytest.raises(ContractViolation, match="entry_price 必須為正"):
        replace(ok, entry_price=-1.0)
    # 判準本身的契約：basis／convention／範圍
    with pytest.raises(ContractViolation, match="basis 未登記"):
        _criterion(basis="session_judgment")
    with pytest.raises(ContractViolation, match="convention 未登記"):
        _criterion(convention="total_return")
    with pytest.raises(ContractViolation, match="超出範圍"):
        _criterion(-1.5)
    with pytest.raises(ContractViolation, match="超出範圍"):
        _criterion(9.0)


# ---------------------------------------------------------------------------
# 13. authority 邊界：沒有 buy／sell／sizing／portfolio 洩漏
# ---------------------------------------------------------------------------

def test_no_buy_sell_sizing_or_portfolio_authority_leaks_anywhere() -> None:
    fields = {f for f in EntryAssessmentResult.__dataclass_fields__} | {f for f in EntryCriterion.__dataclass_fields__}
    for name in fields:
        assert not (set(name.lower().split("_")) & FORBIDDEN_ENTRY_TOKENS), name
    assert not any(t in fields for t in ("action", "recommendation", "signal", "target_price", "decision"))
    # ⚠ 上面只證明「今天沒有壞欄位」，不證明**守衛會擋下明天新增的**——那正是 tripwire 最容易變成裝飾品的地方。
    # 所以直接對守衛本身出招：長出 action／sizing 欄位的型別必須在建立當下就炸。
    from dataclasses import dataclass as _dataclass

    from alpha.entry.contracts import _assert_no_capital_fields

    for bad_field in ("buy_action", "target_weight", "order_id", "position_size", "capital_permission"):
        offender = _dataclass(type(bad_field, (), {"__annotations__": {bad_field: float}}))
        with pytest.raises(ContractViolation, match="部位／action 語意"):
            _assert_no_capital_fields(offender)
    clean = _dataclass(type("ok", (), {"__annotations__": {"entry_price": float}}))
    _assert_no_capital_fields(clean)                     # 正常欄位不得誤報（gate 要攔對東西，L15）
    result = _entry()
    # 序列化後也不得出現部位／action 欄位（含 read model）
    from briefing.alpha_view import compact_card
    from tests.test_alpha_investment_view import _view, _walk

    model = _run(index=_index())
    valuation = _valued(model)
    view = _view(fundamental_model=model, valuation=valuation, implied_return=_return(valuation),
                 entry=_entry(_return(valuation)), entry_records=[_criterion()])
    # ⚠ 整份 view 的掃描刻意把 `action` 排除：refresh 的 `required_action`（「重算即可」「要人複查」）是**下一步**
    # 不是交易動作，攔它就是 L15 記過的「gate 攔錯東西」。`actionable` 仍在列上——那才是真的洩漏訊號。
    banned = (set(FORBIDDEN_ENTRY_TOKENS) - {"action"}) | {"target_weight", "supported_range", "nav_pct", "held"}
    offenders = [path for path, key, _v in _walk(view.to_dict())
                 if set(str(key).lower().split("_")) & banned]
    assert not offenders, offenders
    assert not [p for p, k, _v in _walk(view.to_dict()) if str(k).lower() in ("action", "actionable", "recommendation")]
    card = compact_card(view)
    assert not [k for k in card["entry_logic"] if set(k.lower().split("_")) & banned]
    # 比較值本身是封閉字彙，且刻意帶 "analytical"——讀者不會把它讀成 action
    assert card["entry_logic"]["hurdle_comparison"] in ("meets_analytical_hurdle", "above_analytical_entry")
    assert "analytical" in card["entry_logic"]["hurdle_comparison"]
    # is_not 每次都列，且明說不是資本許可
    text = " ".join(view.entry_logic.is_not)
    assert "buy" in text and "position size" in text and "portfolio permission" in text
    assert "A5" in text and "live 100% 人工" in text
    # entry 層不得 import 任何資本／決策模組
    forbidden = {"anthropic", "openai", "requests", "httpx", "neo4j", "yfinance", "engine_c", "decision_lab",
                 "sqlite3", "subprocess", "briefing", "portfolio", "risk"}
    for path in (ROOT / "alpha" / "entry").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
        assert not (roots & forbidden), (path, roots & forbidden)
    assert result.status == "available"


def test_the_hurdle_is_investor_policy_not_a_research_judgment(tmp_path: Path) -> None:
    """authority 分界：判準的 basis 只能是 investor_policy，且它不進 `input_dependency`（研究側最弱輸入）。"""
    result = _entry()
    assert result.criterion.basis == "investor_policy" and result.criterion.author == "user"
    assert result.input_dependency == "session_judgment"                # 研究側；與 criterion_basis 分開兩格
    assert result.criterion_basis == "investor_policy"
    assert result.criterion.criterion_id not in result.research_assumption_ids
    assert all(a.startswith(("oa_", "va_", "ha_")) for a in result.research_assumption_ids)
    epi = result.epistemics
    assert epi["judgment_inputs"]["criterion"]["basis"] == "investor_policy"
    assert "research_side" in epi["judgment_inputs"]
    # 判準沒有會計期間：估值換年度不會讓 hurdle 變成 other_period 而假失效
    assert not hasattr(result.criterion, "period")
    # ledger 的 append 入口是唯一寫入者，且拒收 sandbox。
    # ⚠ **一定要指定 `directory=tmp_path`**：這個斷言預期會 raise，但如果哪天守衛被拿掉（或被突變工具拿掉），
    # 沒指定目錄的呼叫就會把一筆假判準寫進**真實的 private ledger**——2026-09-06 實測過一次，
    # 突變跑完之後 `python -m briefing entry COHR` 真的長出一個 author=sandbox 的 hurdle。
    # 測試不得有能力污染 authority（L13：驗證者自己造成的副作用最難發現）。
    from alpha.providers.entry_criteria import append_entry_criterion_record, read_entry_criterion_records

    with pytest.raises(ContractViolation, match="sandbox"):
        append_entry_criterion_record(entry_criterion_record(
            company_id="co:coherent", ticker="COHR", value=0.15, basis="investor_policy", rationale="r",
            author="sandbox", created_at=C_CREATED), directory=tmp_path)
    assert read_entry_criterion_records("COHR", directory=tmp_path) == ([], [])


# ---------------------------------------------------------------------------
# 14. read model：builder／renderer 只抄，不重算
# ---------------------------------------------------------------------------

def test_builder_and_renderer_copy_the_threshold_without_computing_it() -> None:
    from briefing.alpha_view import render_alpha_investment_view_markdown
    from briefing.alpha_view.contracts import CAP_ANALYTICAL_ENTRY_THRESHOLD
    from tests.test_alpha_investment_view import _view

    model = _run(index=_index())
    valuation = _valued(model)
    implied = _return(valuation)
    criterion = _criterion()
    entry = _entry(implied, [criterion])
    view = _view(fundamental_model=model, valuation=valuation, valuation_records=list(valuation.assumptions),
                 implied_return=implied, horizon_records=[implied.horizon], entry=entry, entry_records=[criterion])
    section = view.entry_logic
    assert section.meta.status == "available" and section.meta.capability == CAP_ANALYTICAL_ENTRY_THRESHOLD
    assert section.entry_price.value == entry.entry_price                       # 逐位相同
    assert section.price_to_entry_gap.value["relative"] == entry.price_to_entry_gap
    assert section.price_to_entry_gap.value["absolute"] == entry.price_to_entry_gap_abs
    assert section.entry_price.method.startswith(ENTRY_PRICE_FORMULA)
    assert section.required_annualized_return.value == criterion.value
    assert section.required_annualized_return.basis == "investor_policy"        # read model 也標它是政策
    assert section.criterion.dependencies["criterion_id"].startswith("ec_")
    assert section.criterion.dependencies["persisted"] is True
    assert section.hurdle_comparison.value == entry.hurdle_comparison
    assert section.current_annualized_implied_return.value == implied.annualized_price_return
    assert view.capability_map()["entry_logic"]["status"] == "available"
    # 竄改：builder 只抄，不重算
    tampered = replace(entry, entry_price=99.9, price_to_entry_gap=0.5, hurdle_comparison=COMPARISON_MEETS)
    tview = _view(fundamental_model=model, valuation=valuation, implied_return=implied, entry=tampered,
                  entry_records=[criterion])
    assert tview.entry_logic.entry_price.value == 99.9
    assert tview.entry_logic.price_to_entry_gap.value["relative"] == 0.5
    assert tview.entry_logic.hurdle_comparison.value == COMPARISON_MEETS
    text = render_alpha_investment_view_markdown(view).replace("\\", "")
    assert "## 13c. 進場邏輯" in text and "entry logic 不是什麼" in text
    assert "不是 buy／sell／hold 建議" in text
    line = next(l for l in text.splitlines() if l.startswith("- Analytical entry price"))
    assert f"{entry.entry_price:,.2f}" in line or f"{entry.entry_price:.2f}" in line
    # import／token 掃描：組裝層與 renderer 不得 import 門檻價算術、不得自己寫折現公式
    for rel in ("briefing/alpha_view/builder.py", "briefing/alpha_view/render.py", "briefing/cli.py"):
        source = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        assert "alpha.entry.model" not in imported and "alpha.entry" not in imported, rel
        # 只列**門檻價算術**專屬的形狀：折現、與門檻價比較、重算 gap。
        # （不列 `365.25`——implied return section 的欄位標籤本來就寫著「compound，365.25 天」，
        #   攔它等於攔一段文案而不是攔重算，那是 L15 的「gate 攔錯東西」。）
        for token in ("build_entry_assessment", "** (result.holding", "(1 + hurdle)", "(1.0 + hurdle)",
                      "<= result.entry_price", "result.current_price.value / result.entry_price",
                      "/ result.entry_price", "** (days"):
            assert token not in source, (rel, token)


def test_unsupported_company_is_honest_missing_in_the_view_and_card() -> None:
    from briefing.alpha_view import compact_card, render_alpha_cards, render_alpha_investment_view_markdown
    from tests.test_alpha_investment_view import _view

    model = _run(index=_index())
    valuation = _valued(model)
    implied = _return(valuation)
    no_criterion = _entry(implied, [])
    view = _view(fundamental_model=model, valuation=valuation, implied_return=implied, entry=no_criterion)
    assert view.entry_logic.meta.status == "missing"
    assert "投資門檻判斷" in (view.entry_logic.entry_price.reason or "")
    assert view.entry_logic.criterion.status == "missing"
    assert view.entry_logic.fair_value.is_known and view.entry_logic.horizon_window.is_known   # 上游看得到
    assert view.capability_map()["entry_logic"]["status"] == "missing"
    card = compact_card(view)
    assert card["entry_logic"]["status"] == "missing" and card["entry_logic"]["entry_price"] is None
    assert "entry_logic" not in card["not_modeled"]
    assert render_alpha_cards([card])                                            # 卡表不因新欄位失敗
    payload = json.loads(json.dumps(view.to_dict(), ensure_ascii=False))
    assert payload["entry_logic"]["entry_price"]["value"] is None
    assert payload["entry_logic"]["hurdle_comparison"]["value"] is None
    text = render_alpha_investment_view_markdown(view)
    assert "缺投資門檻判斷" in text


def test_sandbox_hurdle_is_never_persisted_and_is_marked_in_the_view() -> None:
    """`--sandbox-hurdle` 只在記憶體驗算：結果標得出它非持久，且 ledger 的寫入口拒收它。"""
    from tests.test_alpha_investment_view import _view

    model = _run(index=_index())
    implied = _return(_valued(model))
    sandbox = _criterion(0.15, author="sandbox")
    result = _entry(implied, [sandbox])
    assert result.status == "available" and result.criterion.author == "sandbox"
    assert any("SANDBOX" in w for w in result.warnings)
    view = _view(fundamental_model=model, valuation=_valued(model), implied_return=implied, entry=result,
                 entry_records=[])
    assert view.entry_logic.criterion.dependencies["persisted"] is False
    from briefing.alpha_view import compact_card

    assert compact_card(view)["entry_logic"]["criterion_persisted"] is False


# ---------------------------------------------------------------------------
# ledger round trip
# ---------------------------------------------------------------------------

def test_entry_criterion_ledger_round_trips_and_rejects_duplicates(tmp_path: Path) -> None:
    from alpha.providers.entry_criteria import append_entry_criterion_record, read_entry_criterion_records

    record = entry_criterion_record(
        company_id="co:coherent", ticker="COHR", value=0.15, basis="investor_policy",
        rationale="借款成本＋機會成本", reference_refs=["config://investment_policy"], created_at=C_CREATED)
    path = append_entry_criterion_record(record, directory=tmp_path)
    assert path.name == "COHR.jsonl"
    loaded, errors = read_entry_criterion_records("COHR", directory=tmp_path)
    assert errors == [] and loaded[0].criterion_id == record["criterion_id"] and loaded[0].value == 0.15
    assert loaded[0].reference_refs == ("config://investment_policy",)
    with pytest.raises(ContractViolation, match="重複"):
        append_entry_criterion_record(record, directory=tmp_path)
    with pytest.raises(ContractViolation, match="supersedes_id"):
        append_entry_criterion_record(entry_criterion_record(
            company_id="co:coherent", ticker="COHR", value=0.2, basis="investor_policy", rationale="r",
            supersedes_id="ec_nope", created_at=C_CREATED), directory=tmp_path)
    path.write_text(path.read_text(encoding="utf-8") + '{"value": 0.1}\n', encoding="utf-8")
    loaded2, errors2 = read_entry_criterion_records("COHR", directory=tmp_path)
    assert len(loaded2) == 1 and len(errors2) == 1                    # 壞行不靜默丟棄（INV-3）
