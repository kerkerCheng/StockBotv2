"""Base-case Implied Return v1（`alpha/implied_return`，Phase 2 Step 2）的測試——純邏輯＋refresh＋read model 整合。

守的是 Step 2 的 12 條驗收：
1. 現價＋fair value＋明示 horizon → 確定性報酬；2. horizon 缺 → missing（不補 12 個月）；3. fair value 缺 → missing；
4. 現價缺 → missing；5. price-only → return recalculate；6. 估值假設 review_required → return review_required；
7. horizon 假設 supersede → recalculate；8. 年化算術正確；9. price return ≠ total return；10. PIT 不偷看未來；
11. 不支援的公司 → 誠實 missing；12. builder／renderer 不含報酬公式。
另守：value-date 語意未宣告 → missing；horizon 到期 → stale（INV-2）；無關的圖變化不亂 cascade；ledger round trip；
核心不 import I/O／LLM。
"""
from __future__ import annotations

import ast
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.implied_return import (
    ANNUALIZED_RETURN_FORMULA, DAYS_PER_YEAR, PRICE_RETURN_FORMULA, HorizonAssumption, ImpliedReturnResult,
    build_implied_return, horizon_assumption_record, parse_horizon_assumption_record,
)
from alpha.refresh import (
    ARTIFACT_FAIR_VALUE, ARTIFACT_HORIZON_ASSUMPTION, ARTIFACT_IMPLIED_RETURN, ARTIFACT_VALUATION_ASSUMPTION,
    CURRENT, GRAPH_EDGE, HORIZON_ASSUMPTION, MARKET_PRICE, RECALCULATE, REVIEW_REQUIRED, STALE, SUPERSEDED,
    VALUATION_ASSUMPTION, ChangeEvent, artifacts_from_implied_return, artifacts_from_model,
    artifacts_from_valuation, end_of_day, resolve_refresh,
)
from alpha.refresh.policy import DERIVED_CLASS_POLICY
from alpha.valuation import VALUE_DATE_TARGET_PERIOD_END, VALUE_DATE_UNSPECIFIED, CurrentPrice
from tests.test_fundamental_model import ACT_REF, TARGET, _run
from tests.test_valuation_model import CREATED, EDGE, PRICE, SNAP, _index, _multiple, _valuation

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
H_CREATED = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)
TODAY = date(2026, 9, 7)


def _horizon(horizon_end: date = TARGET.end, *, basis: str = "session_judgment", period_end: date = TARGET.end,
             refs=(ACT_REF.ref,), created: datetime = H_CREATED, **kw) -> HorizonAssumption:
    record = horizon_assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=period_end, horizon_end=horizon_end, basis=basis,
        rationale=f"test horizon {horizon_end}", evidence_refs=list(refs), created_at=created, **kw)
    return parse_horizon_assumption_record(record)


def _valued(model=None, *, as_of: date | None = None, today: date = TODAY, price: CurrentPrice = PRICE,
            convention: str | None = VALUE_DATE_TARGET_PERIOD_END, multiple: float = 25.0):
    """有宣告 value-date 語意的估值（Step 2 的 COHR 形狀）。"""
    model = model or _run(as_of=as_of, today=today, index=_index())
    return _valuation([_multiple(multiple, value_date_convention=convention)], model=model, as_of=as_of, today=today,
                      price=price)


def _return(valuation=None, horizons=None, *, as_of: date | None = None, today: date = TODAY,
            price: CurrentPrice = PRICE, valuation_reason: str | None = None) -> ImpliedReturnResult:
    if valuation is None and valuation_reason is None:
        valuation = _valued(as_of=as_of, today=today, price=price)
    return build_implied_return(
        company_id="co:coherent", ticker="COHR", as_of=as_of, today=today, valuation=valuation,
        valuation_reason=valuation_reason, horizon_records=[_horizon()] if horizons is None else horizons,
        evidence_index=_index(), price=price)


# ---------------------------------------------------------------------------
# 1. 現價＋fair value＋明示 horizon → 確定性報酬
# ---------------------------------------------------------------------------

def test_price_value_and_explicit_horizon_yield_a_deterministic_return() -> None:
    valuation = _valued()
    result = _return(valuation)
    assert result.status == "available" and result.return_convention == "base_case_implied_price_return"
    assert result.price_return == pytest.approx(valuation.fair_value / PRICE.value - 1)
    assert result.price_return == pytest.approx(valuation.gap.relative_gap)            # 同一個數，語意不同
    assert result.horizon_start == PRICE.bar_date == date(2026, 9, 4)
    assert result.horizon_end == date(2027, 6, 30) and result.holding_period_days == 299
    assert result.holding_period_years == pytest.approx(299 / DAYS_PER_YEAR)
    assert result.annualized_price_return == pytest.approx((1 + result.price_return) ** (DAYS_PER_YEAR / 299) - 1)
    assert result.value_date == date(2027, 6, 30) and result.value_date_semantics == "target_period_end"
    assert result.alignment == "aligned"
    assert result.calculation == "deterministic" and result.input_dependency == "session_judgment"
    assert result.formulas["price_return"] == PRICE_RETURN_FORMULA
    assert result.formulas["annualized_price_return"] == ANNUALIZED_RETURN_FORMULA
    assert set(result.assumption_ids) == set(valuation.assumption_ids) | {result.horizon.assumption_id}
    assert SNAP in result.observation_refs and ACT_REF.ref in result.observation_refs
    kinds = {s.key: (s.kind, s.basis) for s in result.steps}
    assert kinds["current_price"] == ("price_input", "observation")
    assert kinds["fair_value"] == ("valuation_input", "deterministic")
    assert kinds["value_date"] == ("valuation_input", "session_judgment")
    assert kinds["horizon_end"] == ("horizon_input", "session_judgment")
    assert kinds["price_return"] == ("derived", "deterministic")
    assert kinds["annualized_price_return"] == ("derived", "deterministic")
    assert "從 2026-09-04" in result.epistemics["one_sentence"] and "到 2027-06-30" in result.epistemics["one_sentence"]
    assert "total return 未建模" in result.epistemics["one_sentence"]
    again = _return(valuation)
    assert again.price_return == result.price_return and again.digest == result.digest
    # heuristic horizon → 依賴仍是最弱者（session_judgment 來自估值）；觀測型 horizon 對 heuristic-only 估值不會抬高依賴
    proxy = _return(valuation, [_horizon(basis="heuristic_proxy")])
    assert proxy.input_dependency == "session_judgment"


# ---------------------------------------------------------------------------
# 2–4. horizon 缺／fair value 缺／現價缺 → missing（Missing != Zero）
# ---------------------------------------------------------------------------

def test_missing_horizon_is_missing_not_twelve_months() -> None:
    none = _return(horizons=[])
    assert none.status == "missing" and none.price_return is None and none.annualized_price_return is None
    assert none.input_dependency is None and "不補 12 個月" in (none.reason or "")
    assert none.fair_value is not None and none.value_date == date(2027, 6, 30)     # fair value 與時點都在，只缺 horizon
    other = _return(horizons=[_horizon(period_end=TARGET.shifted(1).end, horizon_end=TARGET.shifted(1).end)])
    assert other.status == "missing" and dict(other.horizon_selection.reasons) == {"other_period": 1}
    retract = parse_horizon_assumption_record(horizon_assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, horizon_end=TARGET.end,
        basis="session_judgment", rationale="retracted", evidence_refs=[ACT_REF.ref],
        supersedes_id=_horizon().assumption_id, retracted=True, created_at=H_CREATED + timedelta(days=1)))
    gone = _return(horizons=[_horizon(), retract], today=date(2026, 9, 10))
    assert gone.status == "missing" and "retracted=1" in (gone.reason or "")
    unresolved = _return(horizons=[_horizon(refs=("graph://gone",))])
    assert unresolved.status == "missing" and "unresolved_evidence" in (unresolved.reason or "")
    # 過期的 horizon 不是報酬 0：missing＋「需要新的 horizon 判斷」
    late_price = replace(PRICE, bar_date=date(2027, 7, 1))
    expired = _return(_valued(price=late_price), price=late_price)
    assert expired.status == "missing" and "horizon 已過" in (expired.reason or "")
    # 寫下時就已經過去的 horizon 連紀錄都建不出來（INV-2）
    with pytest.raises(ContractViolation, match="INV-2"):
        _horizon(horizon_end=date(2026, 9, 1))


def test_missing_fair_value_is_missing() -> None:
    model = _run(index=_index())
    no_multiple = _valuation([], model=model)
    result = _return(no_multiple)
    assert result.status == "missing" and result.price_return is None and "fair value 缺席" in (result.reason or "")
    assert result.fair_value is None and result.value_date_semantics == VALUE_DATE_UNSPECIFIED
    none = _return(valuation=None, valuation_reason="provider 無 fiscal 能力")
    assert none.status == "missing" and "provider 無 fiscal 能力" in (none.reason or "")
    assert none.target_period is None and dict(none.horizon_selection.reasons) == {"no_target_period": 1}


def test_value_date_semantics_unspecified_makes_return_missing_even_with_fair_value_and_horizon() -> None:
    """Step 1 的舊估值假設（沒有 value_date_convention）：fair value 照算，報酬拒算——不猜「223.60 是哪一天的值」。"""
    legacy = _valued(convention=None)
    assert legacy.status == "available" and legacy.value_date is None and legacy.value_date_semantics == VALUE_DATE_UNSPECIFIED
    result = _return(legacy)
    assert result.status == "missing" and "unspecified" in (result.reason or "")
    assert result.fair_value == legacy.fair_value and result.horizon is not None      # 兩個輸入都在，缺的是時點語意
    spot = _valued(convention="spot")
    assert spot.value_date == TODAY and spot.value_date_semantics == "spot"
    spot_return = _return(spot)
    assert spot_return.status == "available" and spot_return.alignment == "spot_value_realized_over_horizon"
    with pytest.raises(ContractViolation, match="value_date_convention"):
        _multiple(value_date_convention="next_year")


def test_missing_price_is_missing() -> None:
    no_price = CurrentPrice(value=None, bar_date=None, unit="USD", evidence_refs=(), reason="無快照")
    result = _return(_valued(price=no_price), price=no_price)
    assert result.status == "missing" and "無快照" in (result.reason or "")
    no_bar = replace(PRICE, bar_date=None)
    result2 = _return(_valued(price=no_bar), price=no_bar)
    assert result2.status == "missing" and "bar_date" in (result2.reason or "")
    gbp = replace(PRICE, unit="GBp")
    result3 = _return(_valued(price=gbp), price=gbp)
    assert result3.status == "missing" and "incompatible_unit" in (result3.reason or "")
    with pytest.raises(ContractViolation, match="missing != zero"):
        replace(result, price_return=0.0)


# ---------------------------------------------------------------------------
# 5–7. refresh：price-only → recalculate；估值假設 review → 傳播；horizon supersede → recalculate
# ---------------------------------------------------------------------------

def _artifacts(result, valuation, model, *, horizon_records=(), valuation_records=()):
    build_at = end_of_day(TODAY)
    return (artifacts_from_model(model, build_at=build_at)
            + artifacts_from_valuation(valuation, build_at=build_at, assumption_records=valuation_records,
                                       base_period_end=model.base_period.end)
            + artifacts_from_implied_return(result, build_at=build_at, horizon_records=horizon_records,
                                            base_period_end=model.base_period.end))


def _resolve(changes, *, result, valuation, model, today=date(2026, 9, 8), **kw):
    return resolve_refresh(ticker="COHR", company_id="co:coherent",
                           artifacts=_artifacts(result, valuation, model, **kw), changes=changes, today=today)


def test_price_only_change_recalculates_the_return_and_nothing_judgmental() -> None:
    model = _run(index=_index())
    valuation = _valued(model)
    result = _return(valuation)
    later = datetime(2026, 9, 8, 12, tzinfo=UTC)
    # 依賴宣告是契約：報酬的依賴必須含現價 ref（observation）與每一條輸入假設（input，含 horizon）；class 規則也吃 market_price。
    dep = next(a for a in _artifacts(result, valuation, model) if a.artifact_type == ARTIFACT_IMPLIED_RETURN)
    assert dep.refs.get(SNAP) == "observation" and MARKET_PRICE in DERIVED_CLASS_POLICY["implied_return"]
    assert dep.refs.get(result.horizon.assumption_id) == "input" and result.horizon.assumption_id in dep.assumption_ids
    assert all(dep.refs.get(a) == "input" for a in valuation.assumption_ids)
    report = _resolve([ChangeEvent(change_type=MARKET_PRICE, ticker="COHR", authority="t", changed_ref=SNAP,
                                   observed_at=later, material_fields=("price",))],
                      result=result, valuation=valuation, model=model)
    assert report.artifact(f"{ARTIFACT_IMPLIED_RETURN}:implied_return").state == RECALCULATE
    assert report.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{result.horizon.assumption_id}").state == CURRENT
    assert report.artifact(f"{ARTIFACT_FAIR_VALUE}:fair_value").state == CURRENT
    assert report.artifact(f"{ARTIFACT_VALUATION_ASSUMPTION}:{valuation.assumptions[0].assumption_id}").state == CURRENT
    # 無關的圖變化（沒命中任何 supporting ref）→ 報酬 current，不亂 cascade
    calm = _resolve([ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", authority="t",
                                 changed_ref="graph://edge/co:someone_else/supplies_to/co:nobody", observed_at=later,
                                 material_fields=("substitutability",))],
                    result=result, valuation=valuation, model=model)
    assert calm.artifact(f"{ARTIFACT_IMPLIED_RETURN}:implied_return").state == CURRENT
    assert calm.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{result.horizon.assumption_id}").state == CURRENT


def test_valuation_assumption_review_required_propagates_to_the_return() -> None:
    model = _run(index=_index())
    valuation = _valued(model)
    result = _return(valuation)
    va_id = valuation.assumptions[0].assumption_id
    later = datetime(2026, 9, 8, 12, tzinfo=UTC)
    report = _resolve([ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", authority="t", changed_ref=EDGE,
                                   observed_at=later, material_fields=("substitutability",), detail="sub 5 → 3")],
                      result=result, valuation=valuation, model=model)
    assert report.artifact(f"{ARTIFACT_VALUATION_ASSUMPTION}:{va_id}").state == REVIEW_REQUIRED
    ret = report.artifact(f"{ARTIFACT_IMPLIED_RETURN}:implied_return")
    assert ret.state == REVIEW_REQUIRED and f"{ARTIFACT_VALUATION_ASSUMPTION}:{va_id}" in ret.propagated_from
    # horizon 只引用基期觀測，不因這條邊動搖
    assert report.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{result.horizon.assumption_id}").state == CURRENT
    # read model：報酬那格不得再當 current
    from briefing.alpha_view import compact_card
    from tests.test_alpha_investment_view import _view

    edge = ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", company_id="co:coherent",
                       authority="engine_a://graph_research_provider", changed_ref=EDGE,
                       observed_at=datetime(2026, 9, 7, 23, 59, 59, tzinfo=UTC), material_fields=("substitutability",))
    view = _view(fundamental_model=model, valuation=valuation, valuation_records=list(valuation.assumptions),
                 implied_return=result, horizon_records=[result.horizon], refresh_changes=[edge], today=TODAY)
    assert view.implied_return.price_return.status == "review_required"
    assert view.implied_return.meta.status == "review_required"
    assert view.implied_return.horizon.status == "available"
    assert compact_card(view)["implied_return"]["status"] == "review_required"


def test_horizon_supersede_recalculates_the_return_and_expiry_makes_it_stale() -> None:
    model = _run(index=_index())
    valuation = _valued(model)
    old = _horizon()
    result = _return(valuation, [old])
    later = datetime(2026, 9, 8, 12, tzinfo=UTC)
    dep = next(a for a in _artifacts(result, valuation, model) if a.artifact_type == ARTIFACT_IMPLIED_RETURN)
    assert dep.refs.get(old.assumption_id) == "input" and old.assumption_id in dep.assumption_ids
    report = _resolve([ChangeEvent(change_type=HORIZON_ASSUMPTION, ticker="COHR", authority="t", changed_ref="ha_new",
                                   related_refs=(old.assumption_id,), observed_at=later)],
                      result=result, valuation=valuation, model=model)
    assert report.artifact(f"{ARTIFACT_IMPLIED_RETURN}:implied_return").state == RECALCULATE
    assert report.artifact(f"{ARTIFACT_FAIR_VALUE}:fair_value").state == CURRENT          # horizon 不動 fair value
    # 真的 supersede：新紀錄勝出、舊紀錄 superseded、報酬用新 horizon 算
    new = _horizon(date(2027, 12, 31), created=H_CREATED + timedelta(days=1), supersedes_id=old.assumption_id)
    result2 = _return(valuation, [old, new])
    assert result2.horizon == new and result2.holding_period_days == (date(2027, 12, 31) - PRICE.bar_date).days
    assert result2.alignment == "horizon_after_value_date" and any("晚於 value_date" in w for w in result2.warnings)
    hist = _resolve([], result=result2, valuation=valuation, model=model, horizon_records=[old, new])
    assert hist.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{old.assumption_id}").state == SUPERSEDED
    assert hist.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{new.assumption_id}").state == CURRENT
    # 到期（INV-2）：horizon_end 到了 → horizon stale → 報酬 stale；估值層不動
    due = _resolve([], result=result, valuation=valuation, model=model, today=date(2027, 7, 1))
    assert due.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{old.assumption_id}").state == STALE
    assert due.artifact(f"{ARTIFACT_IMPLIED_RETURN}:implied_return").state == STALE
    assert due.artifact(f"{ARTIFACT_FAIR_VALUE}:fair_value").state == CURRENT
    not_yet = _resolve([], result=result, valuation=valuation, model=model, today=date(2027, 6, 29))
    assert not_yet.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{old.assumption_id}").state == CURRENT


# ---------------------------------------------------------------------------
# 8–9. 年化算術；price return ≠ total return
# ---------------------------------------------------------------------------

def test_annualization_math_is_compound_over_365_25_days() -> None:
    model = _run(index=_index())
    for end, multiple in ((date(2027, 6, 30), 25.0), (date(2028, 9, 4), 40.0), (date(2026, 9, 12), 30.0)):
        valuation = _valued(model, multiple=multiple)
        result = _return(valuation, [_horizon(end)])
        days = (end - PRICE.bar_date).days
        assert result.holding_period_days == days >= 1
        r, ann = result.price_return, result.annualized_price_return
        assert ann == pytest.approx((1 + r) ** (DAYS_PER_YEAR / days) - 1)
        assert (1 + ann) ** (days / DAYS_PER_YEAR) - 1 == pytest.approx(r)            # 反向換算回 simple
        if days == 731:
            assert ann == pytest.approx((1 + r) ** 0.5 - 1, rel=1e-3)                    # 兩年 ≈ 開根號
    # 已知數值：−20.7% over 299 天 → 年化 −24.6%（COHR 2026-09-06 形狀）
    cohr = _return(_valued(model), [_horizon(date(2027, 6, 30))])
    assert cohr.price_return == pytest.approx(-0.2067, abs=5e-4)
    assert cohr.annualized_price_return == pytest.approx(-0.2464, abs=5e-4)
    short = _return(_valued(model), [_horizon(date(2026, 9, 20))])
    assert any("放大" in w for w in short.warnings)


def test_price_return_is_not_total_return_and_has_no_probability_field() -> None:
    result = _return()
    assert result.total_return_status == "not_modeled" and "not_modeled" in result.total_return_reason
    fields = {f for f in ImpliedReturnResult.__dataclass_fields__}
    assert "total_return" not in fields and "expected_return" not in fields
    assert not any("probab" in f for f in fields)
    with pytest.raises(ContractViolation, match="total_return_status"):
        replace(result, total_return_status="available")
    assert "total return" in " ".join(result.epistemics["this_is_not"])
    from tests.test_alpha_investment_view import _view

    model = _run(index=_index())
    valuation = _valued(model)
    view = _view(fundamental_model=model, valuation=valuation, implied_return=_return(valuation))
    assert view.implied_return.total_return.status == "not_modeled" and view.implied_return.total_return.value is None
    assert view.implied_return.probability_weighted_return.status == "not_modeled"
    assert view.implied_return.price_return.is_known
    assert "expected return" in " ".join(view.implied_return.is_not)


# ---------------------------------------------------------------------------
# 10. PIT：as-of 不得看到未來的 horizon／估值／價格
# ---------------------------------------------------------------------------

def test_historical_view_does_not_leak_future_horizon_or_valuation() -> None:
    # horizon 寫於 09-06 09:00；估值假設寫於 09-06 08:00 → as-of 09-05 兩者皆不存在
    then_val = _valued(as_of=date(2026, 9, 5))
    assert then_val.status == "missing"
    then = _return(then_val, [_horizon()], as_of=date(2026, 9, 5))
    assert then.status == "missing" and dict(then.horizon_selection.reasons) == {"created_after_as_of": 1}
    payload = json.dumps({"ids": list(then.assumption_ids), "h": then.horizon.assumption_id if then.horizon else None})
    assert "ha_" not in payload
    # as-of 09-06：兩者都在
    later = _return(_valued(as_of=date(2026, 9, 6)), [_horizon()], as_of=date(2026, 9, 6))
    assert later.status == "available"
    # 估值視角與報酬視角不符 → 拒用（INV-6）
    mismatch = _return(_valued(), [_horizon()], as_of=date(2026, 9, 6))
    assert mismatch.status == "missing" and "INV-6" in (mismatch.reason or "")
    # refresh：as-of 之前的視角看不到之後建立的 horizon 成果
    model = _run(index=_index())
    valuation = _valued(model)
    result = _return(valuation)
    report = resolve_refresh(ticker="COHR", company_id="co:coherent", artifacts=_artifacts(result, valuation, model),
                             as_of=date(2026, 9, 5), today=TODAY)
    assert report.artifact(f"{ARTIFACT_HORIZON_ASSUMPTION}:{result.horizon.assumption_id}") is None
    assert report.excluded_artifacts.get("established_after_as_of", 0) >= 1
    # builder：as-of 模式收到別的時點跑的報酬 → 拒收
    from tests.test_alpha_investment_view import _view
    from alpha.testing import FakeGraphResearchProvider  # noqa: F401  （確認 fixture 可用）

    view = _view(implied_return=result, horizon_records=[result.horizon])
    assert view.implied_return.meta.status == "available"


# ---------------------------------------------------------------------------
# 11–12. read model：不支援的公司誠實 missing；builder／renderer 不含公式
# ---------------------------------------------------------------------------

def test_unsupported_company_is_honest_missing_in_the_view_and_card() -> None:
    from briefing.alpha_view import compact_card, render_alpha_cards, render_alpha_investment_view_markdown
    from tests.test_alpha_investment_view import _view

    view = _view(fundamental_model=None, fundamental_model_reason="provider 無 fiscal 能力",
                 valuation=None, valuation_reason="本次未執行 valuation model（無內部 EPS）",
                 implied_return=None, implied_return_reason="本次未執行 implied return model（無 fair value）")
    assert view.implied_return.meta.status == "missing" and view.implied_return.price_return.value is None
    assert "無 fair value" in (view.implied_return.meta.reason or "")
    assert view.capability_map()["implied_return"]["status"] == "missing"
    card = compact_card(view)
    assert card["implied_return"]["status"] == "missing" and card["implied_return"]["price_return"] is None
    assert card["implied_return"]["reason"] and "implied_return" not in card["not_modeled"]
    assert render_alpha_cards([card])                                            # 卡表不因新欄位失敗
    text = render_alpha_investment_view_markdown(view)
    assert "## 13a. Base-case implied return" in text and "implied return 不是什麼" in text
    # 有 fair value 沒 horizon：section missing，理由指向 horizon
    model = _run(index=_index())
    valuation = _valued(model)
    result = _return(valuation, [])
    view2 = _view(fundamental_model=model, valuation=valuation, implied_return=result)
    assert view2.implied_return.meta.status == "missing" and "12 個月" in (view2.implied_return.price_return.reason or "")
    assert view2.implied_return.fair_value.is_known and view2.implied_return.value_date.is_known
    payload = json.loads(json.dumps(view2.to_dict(), ensure_ascii=False))
    assert payload["implied_return"]["price_return"]["value"] is None
    assert payload["valuation"]["value_date"]["value"] == "2027-06-30"


def test_builder_and_renderer_copy_the_return_without_computing_it() -> None:
    from briefing.alpha_view import render_alpha_investment_view_markdown
    from briefing.alpha_view.contracts import CAP_BASE_CASE_IMPLIED_RETURN
    from tests.test_alpha_investment_view import _view

    model = _run(index=_index())
    valuation = _valued(model)
    result = _return(valuation)
    view = _view(fundamental_model=model, valuation=valuation, valuation_records=list(valuation.assumptions),
                 implied_return=result, horizon_records=[result.horizon])
    section = view.implied_return
    assert section.meta.status == "available" and section.meta.capability == CAP_BASE_CASE_IMPLIED_RETURN
    assert section.price_return.value == result.price_return                       # 逐位相同
    assert section.annualized_price_return.value == result.annualized_price_return
    assert section.price_return.method.startswith(PRICE_RETURN_FORMULA)
    assert section.annualized_price_return.method == ANNUALIZED_RETURN_FORMULA
    assert section.price_return.dependencies["input_dependency"] == "session_judgment"
    assert section.price_return.dependencies["horizon_start"] == "2026-09-04"
    assert section.price_return.dependencies["horizon_end"] == "2027-06-30"
    assert section.horizon.basis == "session_judgment" and section.horizon.dependencies["assumption_id"].startswith("ha_")
    assert section.value_date.value == date(2027, 6, 30) and section.value_date.basis == "session_judgment"
    assert view.valuation.value_date.value == date(2027, 6, 30)
    assert view.capability_map()["implied_return"]["status"] == "available"
    # 竄改：builder 只抄，不重算
    tampered = replace(result, price_return=0.123, annualized_price_return=0.456)
    tview = _view(fundamental_model=model, valuation=valuation, implied_return=tampered, horizon_records=[result.horizon])
    assert tview.implied_return.price_return.value == 0.123 and tview.implied_return.annualized_price_return.value == 0.456
    text = render_alpha_investment_view_markdown(view).replace("\\", "")      # markdown_text 會跳脫 - 與 _
    line = next(l for l in text.splitlines() if l.startswith("- Base-case 隱含價格報酬（simple"))
    assert f"{result.price_return * 100:+.1f}%" in line
    assert "不是 probability-weighted expected return" in text
    # import／token 掃描：組裝層與 renderer 不得 import 報酬算術、不得自己寫報酬公式
    for rel in ("briefing/alpha_view/builder.py", "briefing/alpha_view/render.py", "briefing/cli.py"):
        source = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        assert "alpha.implied_return.model" not in imported and "alpha.implied_return" not in imported, rel
        for token in ("build_implied_return", "/ current_price", "/ price.value", "** (365", "365.25 /", "DAYS_PER_YEAR"):
            assert token not in source, (rel, token)


# ---------------------------------------------------------------------------
# ledger round trip ＋ 核心相依邊界
# ---------------------------------------------------------------------------

def test_horizon_ledger_round_trips_and_rejects_duplicates(tmp_path: Path) -> None:
    from alpha.providers.horizon_assumptions import append_horizon_assumption_record, read_horizon_assumption_records

    record = horizon_assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, horizon_end=TARGET.end, basis="session_judgment",
        rationale="r", evidence_refs=[ACT_REF.ref], calibration_refs=["engine_c://consensus_estimate/COHR/eps/2027-06-30"],
        created_at=H_CREATED)
    path = append_horizon_assumption_record(record, directory=tmp_path)
    assert path.name == "COHR.jsonl"
    loaded, errors = read_horizon_assumption_records("COHR", directory=tmp_path)
    assert errors == [] and loaded[0].assumption_id == record["assumption_id"] and loaded[0].horizon_end == TARGET.end
    assert loaded[0].calibration_refs == ("engine_c://consensus_estimate/COHR/eps/2027-06-30",)
    with pytest.raises(ContractViolation, match="重複"):
        append_horizon_assumption_record(record, directory=tmp_path)
    with pytest.raises(ContractViolation, match="supersedes_id"):
        append_horizon_assumption_record(horizon_assumption_record(
            company_id="co:coherent", ticker="COHR", period_end=TARGET.end, horizon_end=TARGET.end,
            basis="session_judgment", rationale="r", evidence_refs=[ACT_REF.ref], supersedes_id="ha_nope",
            created_at=H_CREATED), directory=tmp_path)
    path.write_text(path.read_text(encoding="utf-8") + '{"period_end": "2027-06-30"}\n', encoding="utf-8")
    loaded2, errors2 = read_horizon_assumption_records("COHR", directory=tmp_path)
    assert len(loaded2) == 1 and len(errors2) == 1
    with pytest.raises(ContractViolation, match="provenance 循環|calibration"):
        _horizon(refs=("engine_c://consensus_estimate/COHR/eps/2027-06-30",))


def test_valuation_ledger_v2_keeps_old_ids_and_parses_legacy_rows() -> None:
    """加 `value_date_convention` 不得改變舊紀錄的 content-addressed id；舊行 parse 成 unspecified。"""
    from alpha.valuation.assumptions import new_valuation_assumption_id, valuation_assumption_record

    base = valuation_assumption_record(company_id="co:coherent", ticker="COHR", period_end=TARGET.end, value=25.0,
                                       basis="session_judgment", accounting_basis="non_gaap", rationale="r",
                                       evidence_refs=[EDGE], created_at=CREATED,
                                       derivation="independent")
    assert "value_date_convention" not in base
    legacy_payload = {k: v for k, v in base.items() if k != "assumption_id"}
    assert new_valuation_assumption_id(legacy_payload) == base["assumption_id"]
    assert new_valuation_assumption_id({**legacy_payload, "value_date_convention": None}) == base["assumption_id"]
    declared = valuation_assumption_record(company_id="co:coherent", ticker="COHR", period_end=TARGET.end, value=25.0,
                                           basis="session_judgment", accounting_basis="non_gaap", rationale="r",
                                           evidence_refs=[EDGE], created_at=CREATED,
                                           derivation="independent",
                                           value_date_convention="target_period_end")
    assert declared["assumption_id"] != base["assumption_id"] and declared["value_date_convention"] == "target_period_end"


def test_implied_return_core_never_imports_io_or_llm_clients() -> None:
    forbidden = {"anthropic", "openai", "requests", "httpx", "neo4j", "yfinance", "engine_c", "decision_lab",
                 "sqlite3", "subprocess", "briefing"}
    for path in (ROOT / "alpha" / "implied_return").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
        assert not (roots & forbidden), (path, roots & forbidden)


# ---------------------------------------------------------------------------
# 13. 兩桿拆解（2026-09-09 P2）：EPS 差異 × 倍數差異；拆不出來不影響報酬
# ---------------------------------------------------------------------------

def _return_with_comparison(model=None, *, multiple: float = 25.0, comparison="model"):
    from tests.test_fundamental_model import _run as run_model

    model = model or run_model(as_of=None, today=TODAY, index=_index())
    valuation = _valuation([_multiple(multiple, value_date_convention=VALUE_DATE_TARGET_PERIOD_END)],
                           model=model, as_of=None, today=TODAY, price=PRICE)
    eps_cmp = model.comparisons["eps"] if comparison == "model" else comparison
    result = build_implied_return(
        company_id="co:coherent", ticker="COHR", as_of=None, today=TODAY, valuation=valuation,
        valuation_reason=None, horizon_records=[_horizon()], evidence_index=_index(), price=PRICE,
        eps_comparison=eps_cmp)
    return model, valuation, result


def test_attribution_is_an_identity_of_the_price_return() -> None:
    """(1+R) = (E_int/E_cons) × (PE_t / (P/E_cons))；兩桿加上交互項必須等於總報酬（浮點 1e-9）。"""
    model, valuation, result = _return_with_comparison()
    attr = result.attribution
    assert attr is not None and attr.is_known
    cmp = model.comparisons["eps"]
    assert cmp.status == "comparable"
    market_pe = PRICE.value / cmp.consensus
    assert attr.market_multiple_on_consensus == pytest.approx(market_pe)
    assert attr.eps_contribution == pytest.approx(cmp.internal / cmp.consensus - 1)
    assert attr.multiple_contribution == pytest.approx(25.0 / market_pe - 1)
    assert attr.eps_contribution + attr.multiple_contribution + attr.interaction == pytest.approx(result.price_return, abs=1e-9)
    # COHR 形狀：內部 EPS 略低於共識（小負），倍數 25x vs 市場 ~29.9x（−16% 左右）——倍數桿是主因
    assert attr.multiple_contribution < attr.eps_contribution < 0.05
    assert attr.multiple_contribution == pytest.approx(-0.1648, abs=5e-3)
    # step 與 epistemics 都帶著它；one_sentence 說出兩桿
    keys = {s.key: s for s in result.steps}
    assert keys["eps_contribution"].value == pytest.approx(attr.eps_contribution)
    assert keys["multiple_contribution"].value == pytest.approx(attr.multiple_contribution)
    assert result.epistemics["attribution"]["multiple_contribution"] == pytest.approx(attr.multiple_contribution)
    assert "EPS 差異貢獻" in result.epistemics["one_sentence"] and "倍數差異貢獻" in result.epistemics["one_sentence"]
    # 倍數折價超過 5% → warning 提醒原則（提醒，不阻擋、不改數字）
    assert any("倍數桿" in w and "折價" in w for w in result.warnings)


def test_attribution_missing_never_removes_the_return() -> None:
    """拆不出來（沒有共識比較）→ 拆解 missing＋語意；price_return 照樣 available。"""
    _model, _valuation, result = _return_with_comparison(comparison=None)
    assert result.status == "available" and result.price_return is not None
    attr = result.attribution
    assert attr is not None and attr.status == "missing" and attr.absence_kind == "upstream_unavailable"
    assert attr.eps_contribution is None and attr.multiple_contribution is None
    keys = {s.key: s for s in result.steps}
    assert keys["eps_contribution"].value is None and keys["eps_contribution"].reason
    assert "兩桿拆解缺席" in result.epistemics["one_sentence"]


def test_attribution_declares_which_kind_of_absence() -> None:
    from tests.test_fundamental_model import _consensus, _run as run_model

    # 共識缺 → provider_missing
    model = run_model(as_of=None, today=TODAY, index=_index(),
                      consensus=(_consensus("eps", None), _consensus("revenue", 10_618_193_080.0)))
    _m, _v, result = _return_with_comparison(model=model)
    assert result.attribution.status == "missing" and result.attribution.absence_kind == "provider_missing"
    # 共識非正 → method_not_applicable（市場倍數無定義，與本益比法同一條件）
    model = run_model(as_of=None, today=TODAY, index=_index(),
                      consensus=(_consensus("eps", -1.0, year_ago=5.61), _consensus("revenue", 10_618_193_080.0)))
    if model.comparisons["eps"].status == "comparable":
        _m, _v, result = _return_with_comparison(model=model)
        assert result.attribution.absence_kind == "method_not_applicable"


def test_attribution_contract_rejects_broken_identity_and_numbers_on_missing() -> None:
    from alpha.implied_return import ReturnAttribution

    with pytest.raises(ContractViolation):
        ReturnAttribution(status="available", reason=None, absence_kind=None, consensus_eps=9.0, internal_eps=9.0,
                          target_multiple=25.0, market_multiple_on_consensus=30.0, eps_ratio=1.0, multiple_ratio=25 / 30,
                          eps_contribution=0.0, multiple_contribution=25 / 30 - 1, interaction=0.0, price_return=0.1)
    with pytest.raises(ContractViolation):
        ReturnAttribution(status="missing", reason="x", absence_kind="provider_missing", eps_contribution=0.0)


def test_read_model_and_analyst_headline_copy_the_two_levers_without_computing() -> None:
    """builder／analyst 只抄：兩格的值＝模型的值；缺席時仍占一格並帶 absence_kind。"""
    from briefing.alpha_view.builder import _implied_return_section
    from tests.test_valuation_model import TARGET as _T  # noqa: F401 — 只確認 fixture 可用

    _model, _valuation, result = _return_with_comparison()
    section = _implied_return_section(result, None, reference_day=TODAY, reporting_unit="USD", refresh={})
    assert section.eps_contribution.value == pytest.approx(result.attribution.eps_contribution)
    assert section.multiple_contribution.value == pytest.approx(result.attribution.multiple_contribution)
    assert section.attribution.value["market_multiple_on_consensus"] == pytest.approx(result.attribution.market_multiple_on_consensus)
    assert "折價" in section.multiple_contribution.reason

    _model, _valuation, absent = _return_with_comparison(comparison=None)
    section = _implied_return_section(absent, None, reference_day=TODAY, reporting_unit="USD", refresh={})
    assert section.eps_contribution.value is None and section.eps_contribution.absence_kind == "upstream_unavailable"
    assert section.price_return.value is not None
