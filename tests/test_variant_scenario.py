"""V0「賭注」（variant scenario → payoff，2026-09-15）的純邏輯測試——不需要 Neo4j／Engine C。

守的是五件事：
1. **型別層的三條規則**：variant 只能是核心 driver、必須 independent、必須有 supporting 證據。
2. **overlay 不是取代**：variant 覆蓋同 key 的 base；其餘沿用 base；base 執行一個位元不變（既有 id 不變）。
3. **同一條算術**：variant 的 EPS／fair value／payoff 走的是同一個 bridge／valuation／implied_return。
4. **缺席要現形、且是 optional**：沒寫賭注 → payoff section missing＋not_yet_recorded；bet panel 不影響 readiness。
5. **consumer 不造格**：bet panel 每一行都是 read model 的同一個 Datum。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from alpha.errors import ContractViolation
from alpha.fundamental import (
    ASSUMPTION_SCENARIOS, BASE_SCENARIO, VARIANT_SCENARIO, build_fundamental_model,
    select_scenario_assumptions,
)
from alpha.fundamental.assumptions import assumption_record, new_assumption_id, parse_assumption_record
from alpha.implied_return import build_implied_return
from alpha.valuation import build_valuation
from alpha.valuation.assumptions import parse_valuation_assumption_record, valuation_assumption_record
from tests.test_fundamental_model import (
    ACT_REF, CONSENSUS, GRAPH_REF, INDEX, TARGET, TODAY, _actuals, _assumption, _full_set,
)
from tests.test_implied_return import TODAY as IR_TODAY, _horizon
from tests.test_valuation_model import CREATED, EDGE, PRICE, _index, _multiple

UTC = timezone.utc


def _variant(driver: str = "operating_margin_delta", scope: str = "mix_and_utilization", value: float = 0.045,
             **kw):
    # created 必須 ≤ TODAY（2026-09-05）——否則 as-of 選取會把它當成「還不存在」（INV-6）
    return _assumption(driver, scope, value, created="2026-09-05T09:00:00+00:00", scenario=VARIANT_SCENARIO, **kw)


def _model(records, *, scenario: str = BASE_SCENARIO, index=None):
    return build_fundamental_model(
        company_id="co:coherent", ticker="COHR", as_of=None, today=TODAY, actuals=_actuals(),
        actuals_reason=None, consensus=CONSENSUS, guidance=(), assumption_records=records,
        evidence_index=index or _index(), scenario=scenario)


# ---------------------------------------------------------------------------
# 1. 型別層：賭注的三條規則
# ---------------------------------------------------------------------------

def test_scenario_vocabulary_is_closed_and_defaults_to_base() -> None:
    # 2026-09-18（D2）：`downside`＝「判斷錯了值多少」，與 variant 對稱。
    # 這條斷言守的是**封閉性**，不是「只有兩個」——新增一個 scenario 就必須同時
    # 新增一條 payoff 算術與一組型別層規則，所以它必須在這裡被看見。
    assert ASSUMPTION_SCENARIOS == ("base", "variant", "downside")
    legacy = parse_assumption_record({k: v for k, v in assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, driver="tax_rate", scope="total",
        value=0.19, basis="heuristic_proxy", rationale="x", evidence_refs=[GRAPH_REF.ref],
        created_at=datetime(2026, 9, 5, tzinfo=UTC), derivation="carried_forward").items() if k != "scenario"})
    assert legacy.scenario == BASE_SCENARIO            # 舊行沒有欄位 → base（定義，不是猜）
    with pytest.raises(ContractViolation):
        _assumption("tax_rate", "total", 0.19, basis="heuristic_proxy", derivation="carried_forward", scenario="bull")


def test_variant_must_be_an_opinion_bearing_driver() -> None:
    with pytest.raises(ContractViolation, match="核心 driver"):
        _variant("tax_rate", "total", 0.10, basis="heuristic_proxy")


def test_variant_must_be_our_own_judgment_not_an_inversion_or_guidance() -> None:
    for derivation in ("consensus_inverted", "company_guidance", "carried_forward"):
        with pytest.raises(ContractViolation, match="independent"):
            _variant(derivation=derivation, refs=(GRAPH_REF.ref, "engine_c://consensus_estimate/COHR/eps/2027-06-30"),
                     calibration_refs=("engine_c://consensus_estimate/COHR/eps/2027-06-30",))


def test_variant_must_cite_supporting_evidence_not_only_calibration() -> None:
    consensus_ref = "engine_c://consensus_estimate/COHR/eps/2027-06-30"
    with pytest.raises(ContractViolation):
        _variant(refs=(), calibration_refs=(consensus_ref,))


def test_variant_valuation_multiple_must_be_independent_with_support() -> None:
    with pytest.raises(ContractViolation, match="independent"):
        _multiple(28.0, derivation="calibrated_to_market", refs=(EDGE,),
                  calibration_refs=("engine_c://consensus_estimate/COHR/eps/2027-06-30",), scenario=VARIANT_SCENARIO)
    ok = _multiple(28.0, scenario=VARIANT_SCENARIO)
    assert ok.scenario == VARIANT_SCENARIO


# ---------------------------------------------------------------------------
# 2. overlay：覆蓋不是取代；base 一個位元不變
# ---------------------------------------------------------------------------

def test_variant_overlays_the_same_key_and_leaves_the_rest_to_base() -> None:
    base = _full_set()
    variant = _variant(value=0.045)
    accepted, selection, overrides = select_scenario_assumptions(
        [*base, variant], scenario=VARIANT_SCENARIO, target=TARGET, as_of=None, today=TODAY, evidence_index=_index())
    assert overrides == (variant,)
    by_key = {a.key: a for a in accepted}
    assert by_key[("operating_margin_delta", "mix_and_utilization")].value == 0.045
    assert len(accepted) == len(base)                       # 一條覆蓋，其餘沿用
    assert selection.reasons.get("base_overridden_by_variant") == 1
    # base 執行完全不受 variant 紀錄影響
    base_accepted, base_sel, base_over = select_scenario_assumptions(
        [*base, variant], scenario=BASE_SCENARIO, target=TARGET, as_of=None, today=TODAY, evidence_index=_index())
    assert base_over == () and {a.assumption_id for a in base_accepted} == {a.assumption_id for a in base}
    assert "base_overridden_by_variant" not in base_sel.reasons


def test_existing_base_ids_do_not_change_because_scenario_exists() -> None:
    payload = assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, driver="operating_margin_delta",
        scope="mix_and_utilization", value=0.025, basis="session_judgment", rationale="x",
        evidence_refs=[GRAPH_REF.ref], created_at=datetime(2026, 9, 5, tzinfo=UTC), derivation="independent")
    without = {k: v for k, v in payload.items() if k not in ("scenario", "assumption_id")}
    assert new_assumption_id(without) == payload["assumption_id"]      # base 不參與 id
    as_variant = dict(payload, scenario=VARIANT_SCENARIO)
    assert new_assumption_id(as_variant) != payload["assumption_id"]   # variant 是另一筆


def test_a_variant_without_base_counterpart_is_still_accepted_and_reported() -> None:
    base = [a for a in _full_set() if a.key != ("operating_margin_delta", "mix_and_utilization")]
    variant = _variant()
    accepted, selection, overrides = select_scenario_assumptions(
        [*base, variant], scenario=VARIANT_SCENARIO, target=TARGET, as_of=None, today=TODAY, evidence_index=_index())
    assert overrides == (variant,) and variant in accepted
    assert "base_overridden_by_variant" not in selection.reasons


# ---------------------------------------------------------------------------
# 3. 同一條算術：variant 的 EPS／fair value／payoff
# ---------------------------------------------------------------------------

def test_variant_walks_the_same_bridge_and_only_the_overridden_driver_moves_eps() -> None:
    base = _full_set()
    variant = _variant(value=0.045)
    base_model = _model([*base, variant])
    var_model = _model([*base, variant], scenario=VARIANT_SCENARIO)
    assert base_model.scenario == BASE_SCENARIO and base_model.overrides == ()
    assert var_model.scenario == VARIANT_SCENARIO and var_model.overrides == (variant,)
    assert base_model.metrics["revenue"].value == var_model.metrics["revenue"].value      # 營收沒被覆蓋
    assert var_model.metrics["eps"].value > base_model.metrics["eps"].value
    assert base_model.digest != var_model.digest
    # base 的 EPS 與沒有 variant 紀錄時一模一樣（賭注寫進 ledger 不改 base）
    assert base_model.metrics["eps"].value == _model(base).metrics["eps"].value


def test_variant_multiple_cannot_be_applied_to_a_base_eps() -> None:
    base = _full_set()
    base_model = _model(base)
    with pytest.raises(ValueError, match="scenario"):
        build_valuation(company_id="co:coherent", ticker="COHR", as_of=None, today=TODAY, fundamental=base_model,
                        fundamental_reason=None, assumption_records=[_multiple()], evidence_index=_index(),
                        price=PRICE, scenario=VARIANT_SCENARIO)


def test_payoff_is_the_implied_return_of_the_variant_fair_value() -> None:
    base = _full_set()
    variant = _variant(value=0.045)
    var_model = _model([*base, variant], scenario=VARIANT_SCENARIO)
    valuation = build_valuation(
        company_id="co:coherent", ticker="COHR", as_of=None, today=IR_TODAY, fundamental=var_model,
        fundamental_reason=None, assumption_records=[_multiple(value_date_convention="target_period_end")],
        evidence_index=_index(), price=PRICE, scenario=VARIANT_SCENARIO)
    assert valuation.fair_value == pytest.approx(var_model.metrics["eps"].value * 25.0)
    payoff = build_implied_return(
        company_id="co:coherent", ticker="COHR", as_of=None, today=IR_TODAY, valuation=valuation, valuation_reason=None,
        horizon_records=[_horizon()], evidence_index=_index(), price=PRICE,
        eps_comparison=var_model.comparisons.get("eps"))
    assert payoff.is_known
    assert payoff.price_return == pytest.approx(valuation.fair_value / PRICE.value - 1)
    # 兩桿拆解用的是 variant 的 EPS 對共識
    assert payoff.attribution is not None and payoff.attribution.internal_eps == pytest.approx(var_model.metrics["eps"].value)


# ---------------------------------------------------------------------------
# 4.／5. read model 與 consumer：缺席現形、optional、不造格
# ---------------------------------------------------------------------------

def test_read_model_without_variant_says_not_yet_recorded_and_bet_is_optional() -> None:
    from briefing.analyst_view import build_analyst_view
    from tests.test_analyst_view import _full_view

    view = _full_view(with_criterion=False)
    ps = view.payoff_scenario
    assert ps.meta.status == "missing" and ps.meta.effective_absence_kind == "not_yet_recorded"
    assert ps.payoff_return.value is None and ps.overrides == ()
    analyst = build_analyst_view(view)
    assert analyst.bet.optional and analyst.bet.status == "missing"
    assert "bet：missing" in analyst.readiness.optional_unavailable
    assert not any(b.startswith("bet") for b in analyst.readiness.blockers)
    # bet 的每一行都是 read model 的同一個 Datum（consumer 不造格）
    allowed = {id(getattr(ps, name)) for name in (
        "scenario", "scenario_internal_eps", "scenario_fair_value", "value_date", "payoff_return",
        "annualized_payoff_return", "eps_contribution", "multiple_contribution", "epistemics",
        "base_fair_value", "base_price_return")} | {id(d) for d in ps.overrides}
    assert all(id(line.datum) in allowed for line in analyst.bet.lines)


def test_read_model_with_variant_carries_payoff_and_overrides_with_base_values() -> None:
    from briefing.alpha_view.builder import _payoff_section

    base = _full_set()
    variant = _variant(value=0.045)
    base_model = _model([*base, variant])
    var_model = _model([*base, variant], scenario=VARIANT_SCENARIO)
    base_val = build_valuation(company_id="co:coherent", ticker="COHR", as_of=None, today=IR_TODAY, fundamental=base_model,
                               fundamental_reason=None, assumption_records=[_multiple(value_date_convention="target_period_end")],
                               evidence_index=_index(), price=PRICE)
    var_val = build_valuation(company_id="co:coherent", ticker="COHR", as_of=None, today=IR_TODAY, fundamental=var_model,
                              fundamental_reason=None, assumption_records=[_multiple(value_date_convention="target_period_end")],
                              evidence_index=_index(), price=PRICE, scenario=VARIANT_SCENARIO)
    base_ret = build_implied_return(company_id="co:coherent", ticker="COHR", as_of=None, today=IR_TODAY, valuation=base_val,
                                    valuation_reason=None, horizon_records=[_horizon()], evidence_index=_index(), price=PRICE,
                                    eps_comparison=base_model.comparisons.get("eps"))
    var_ret = build_implied_return(company_id="co:coherent", ticker="COHR", as_of=None, today=IR_TODAY, valuation=var_val,
                                   valuation_reason=None, horizon_records=[_horizon()], evidence_index=_index(), price=PRICE,
                                   eps_comparison=var_model.comparisons.get("eps"))
    from briefing.alpha_view.builder import _VARIANT_COPY

    section = _payoff_section(var_model, var_val, var_ret, None, base_fundamental=base_model, base_valuation=base_val,
                              base_implied_return=base_ret, reference_day=IR_TODAY, reporting_unit="USD", absence_kind=None,
                              copy=_VARIANT_COPY)
    assert section.meta.status == "available"
    assert section.payoff_return.value == pytest.approx(var_ret.price_return)
    assert section.base_price_return.value == pytest.approx(base_ret.price_return)
    assert section.scenario_fair_value.value == pytest.approx(var_val.fair_value)
    assert len(section.overrides) == 1
    deps = section.overrides[0].dependencies
    assert deps["base_value"] == 0.025 and deps["scenario"] == "variant" and deps["layer"] == "operating"
    assert deps["supporting_refs"], "賭注假設必須帶 supporting 證據"
    assert section.eps_contribution.value is not None and section.multiple_contribution.value is not None


def test_retract_keeps_the_scenario_of_the_record_it_retracts(monkeypatch, tmp_path, capsys) -> None:
    """**撤回一條 variant／downside 假設，撤回紀錄必須沿用它的 scenario。**

    事發（2026-09-19）：`alpha assumptions --retract` 的分支寫於只有 base 的時期，
    加了 scenario 之後沒跟上——它不傳 `scenario`，於是一律預設 `base`，而型別層
    **正確地**擋下跨 scenario supersede（「variant 是 overlay，不是取代」）。
    合起來的效果是 **variant 與 downside 一旦寫錯就撤不回**，而 ledger 是 append-only，
    沒有第二條路可以修正。

    這是 L17 的形狀：機制只認得它當初那個案例；不會壞、不報錯，只是那條路不通。
    ⚠ 空跑檢查：把 `cli.py` retract 分支的 `scenario=target.scenario` 拿掉 → 這條會紅。
    """
    import argparse as _argparse

    from alpha import cli
    _ns = _argparse.Namespace

    target = _variant(value=0.045)
    captured: list = []
    monkeypatch.setattr("alpha.providers.assumptions.read_assumption_records",
                        lambda ticker: ([target], None))
    monkeypatch.setattr("alpha.providers.assumptions.append_assumption_record",
                        lambda record: captured.append(record) or tmp_path / "x.jsonl")
    monkeypatch.setattr(cli, "_resolve_company", lambda t: ("COHR", "co:coherent"))

    args = _ns(ticker="COHR", add=None, retract=target.assumption_id,
                              rationale="scope 寫錯", format="markdown", list=False)
    assert cli.cmd_assumptions(args) == 0
    assert captured, "撤回應該 append 一筆紀錄"
    row = captured[0]
    assert row["scenario"] == VARIANT_SCENARIO, (
        "撤回紀錄的 scenario 必須等於被撤回那筆；預設成 base 會被型別層擋下，等於 variant 撤不回")
    assert row["retracted"] is True
    assert row["supersedes_id"] == target.assumption_id
