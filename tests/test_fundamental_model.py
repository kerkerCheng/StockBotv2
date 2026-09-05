"""Causal Fundamental Model（`alpha/fundamental`）的純邏輯測試——不需要 Neo4j／Engine C。

守的是四件事：
1. **假設的判斷 ≠ 算術的確定性**：輸出 `calculation=deterministic`，但 `input_dependency` 帶著
   最弱那條假設的知識種類；session 判斷不會因為經過公式就變成事實。
2. **Missing != Zero**：少一條假設、少一筆共識、缺口徑，一律 None＋理由，不補 0。
3. **會計期間與口徑是身分**：FY27 內部不得與 FY26／FY28 共識相減；GAAP 不得與 non-GAAP 相減；
   口徑靠去年實際值與一手數字核實，不靠慣例。
4. **PIT**：`as_of=T` 只看得到 `created_at <= T` 的假設、`recorded_at <= T` 的觀測、
   `captured_at <= T` 的共識。
"""
from __future__ import annotations

import inspect
from dataclasses import fields, replace
from datetime import date, datetime, timezone

import pytest

from alpha.contracts import EvidenceRef
from alpha.errors import ContractViolation
from alpha.fundamental import (
    ASSUMPTION_BASES, ASSUMPTION_DRIVERS, ConsensusEstimate, FiscalPeriod, FiscalYearActuals,
    FundamentalModelResult, ModeledMetric, OperatingAssumption, build_bridge,
    build_fundamental_model, compare_metric, verify_consensus_basis,
)
from alpha.fundamental.assumptions import (
    assumption_record, parse_assumption_record, select_assumptions,
)
from briefing.alpha_view.contracts import BASES

UTC = timezone.utc
BASE = FiscalPeriod(end=date(2026, 6, 30))
TARGET = BASE.shifted(1)                                # FY2027，至 2027-06-30
TODAY = date(2026, 9, 5)

ACT_REF = EvidenceRef(ref="engine_c://manual_observation/mo_fy2026", kind="engine_c_observation",
                      origin_entity="issuer_filing", published_at=date(2026, 8, 12),
                      retrieved_at=TODAY, recorded_at=datetime(2026, 9, 5, 4, 0, tzinfo=UTC))
GRAPH_REF = EvidenceRef(ref="graph://edge/co:coherent/supplies_to/co:nvidia", kind="graph_edge",
                        published_at=date(2026, 3, 2))
INDEX = {GRAPH_REF.ref: GRAPH_REF}

# 基期（COHR FY2026，8-K EX-99.1 的印刷數字，USD 絕對金額）
REVENUE = 7_118_200_000.0
DC = 5_274_600_000.0
IND = 1_843_600_000.0
NG_OI = 1_456_900_000.0


def _actuals(**over) -> FiscalYearActuals:
    base = dict(
        period=BASE, currency="USD", revenue=REVENUE,
        segment_revenue={"Datacenter & Communications": DC, "Industrial": IND},
        gaap={"operating_income": 897_900_000.0, "diluted_eps": 4.12, "diluted_shares": 195_400_000.0},
        non_gaap={"operating_income": NG_OI, "diluted_eps": 5.61, "diluted_shares": 195_400_000.0,
                  "interest_and_other_net": 118_100_000.0},
        evidence=(ACT_REF,), recorded_at=datetime(2026, 9, 5, 4, 0, tzinfo=UTC),
        source_filed_at=date(2026, 8, 12),
    )
    base.update(over)
    return FiscalYearActuals(**base)


def _assumption(driver: str, scope: str, value: float, *, basis: str = "session_judgment",
                created: str = "2026-09-05T08:00:00+00:00", refs=(GRAPH_REF.ref,),
                period_end: date = TARGET.end, **kw) -> OperatingAssumption:
    record = assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=period_end, driver=driver, scope=scope,
        value=value, basis=basis, rationale=f"test {driver}[{scope}]", evidence_refs=list(refs),
        created_at=datetime.fromisoformat(created), **kw)
    return parse_assumption_record(record)


def _full_set() -> list[OperatingAssumption]:
    return [
        _assumption("revenue_growth", "Datacenter & Communications", 0.60),
        _assumption("revenue_growth", "Industrial", -0.03),
        _assumption("operating_margin_delta", "mix_and_utilization", 0.025),
        _assumption("interest_and_other_net", "total", 118_100_000.0, basis="heuristic_proxy",
                    refs=(ACT_REF.ref,)),
        _assumption("tax_rate", "total", 0.19, basis="heuristic_proxy", refs=(ACT_REF.ref,)),
        _assumption("nci_attribution", "total", 12_200_000.0, basis="heuristic_proxy", refs=(ACT_REF.ref,)),
        _assumption("diluted_shares", "total", 203_400_000.0, basis="heuristic_proxy", refs=(ACT_REF.ref,)),
    ]


def _consensus(metric: str, value: float | None, *, period: FiscalPeriod = TARGET,
               year_ago: float | None = None, currency: str | None = "USD",
               captured: date = date(2026, 9, 4), analysts: int = 22) -> ConsensusEstimate:
    ref = EvidenceRef(ref=f"engine_c://consensus_estimate/COHR/{metric}/{period.end.isoformat()}",
                      kind="engine_c_observation", origin_entity="yfinance", published_at=captured)
    return ConsensusEstimate(metric=metric, period=period, value=value,
                             source=f"yfinance.{'earnings' if metric == 'eps' else 'revenue'}_estimate",
                             evidence=(ref,), analyst_count=analysts, year_ago_actual=year_ago,
                             currency=currency, captured_at=captured)


CONSENSUS = (_consensus("eps", 9.41634, year_ago=5.61), _consensus("revenue", 10_618_193_080.0))


def _run(assumptions=None, *, actuals=None, actuals_reason=None, consensus=CONSENSUS,
         as_of: date | None = None, today: date = TODAY, index=INDEX) -> FundamentalModelResult:
    return build_fundamental_model(
        company_id="co:coherent", ticker="COHR", as_of=as_of, today=today,
        actuals=_actuals() if actuals is None and actuals_reason is None else actuals,
        actuals_reason=actuals_reason, consensus=consensus, guidance=(),
        assumption_records=_full_set() if assumptions is None else assumptions,
        evidence_index=index,
    )


# ---------------------------------------------------------------------------
# 1. 橋的算術：給定固定輸入，輸出必須精確可算
# ---------------------------------------------------------------------------

def test_bridge_arithmetic_is_exact_given_fixed_inputs() -> None:
    result = _run()
    revenue = DC * 1.60 + IND * 0.97
    margin = NG_OI / REVENUE + 0.025
    oi = revenue * margin
    pretax = oi - 118_100_000.0
    net = pretax * (1 - 0.19)
    attributable = net + 12_200_000.0
    eps = attributable / 203_400_000.0
    assert result.status == "available"
    assert result.accounting_basis == "non_gaap"
    assert result.metrics["revenue"].value == pytest.approx(revenue)
    assert result.metrics["operating_margin"].value == pytest.approx(margin)
    assert result.metrics["operating_income"].value == pytest.approx(oi)
    assert result.metrics["net_income"].value == pytest.approx(attributable)
    assert result.metrics["eps"].value == pytest.approx(eps)
    # 同一組輸入再跑一次，逐位相同（deterministic）
    again = _run()
    assert again.metrics["eps"].value == result.metrics["eps"].value
    assert again.digest == result.digest


def test_every_known_output_traces_to_assumptions_and_observations() -> None:
    """沒有 naked number：每個有值的指標都指得回它用的假設 id 與基期觀測 ref。"""
    result = _run()
    for name, metric in result.metrics.items():
        assert metric.is_known, name
        assert metric.formula, name
        assert metric.assumption_ids, f"{name} 沒有假設依賴"
        assert ACT_REF.ref in metric.observation_refs, name
    eps = result.metrics["eps"]
    assert len(eps.assumption_ids) == 7                    # 七條假設全部進了 EPS
    step_keys = [s.key for s in result.steps]
    assert step_keys.index("base_revenue") < step_keys.index("internal_revenue") < step_keys.index("internal_eps")


# ---------------------------------------------------------------------------
# 2. 假設的判斷 ≠ 算術的確定性
# ---------------------------------------------------------------------------

def test_session_judgment_assumption_is_not_a_deterministic_observation() -> None:
    result = _run()
    growth = next(a for a in result.assumptions if a.scope == "Datacenter & Communications")
    assert growth.basis == "session_judgment"
    eps = result.metrics["eps"]
    assert eps.calculation == "deterministic"
    assert eps.input_dependency == "session_judgment"       # 最弱輸入決定依賴，不被公式洗白
    # 橋上：假設格帶自己的 basis，derived 格才是 deterministic，基期格是 observation
    kinds = {s.key: (s.kind, s.basis) for s in result.steps}
    assert kinds["revenue_growth:Datacenter & Communications"] == ("assumption", "session_judgment")
    assert kinds["tax_rate"] == ("assumption", "heuristic_proxy")
    assert kinds["base_operating_margin"] == ("observation", "observation")
    assert kinds["internal_eps"] == ("derived", "deterministic")


def test_assumption_basis_vocabulary_reuses_the_read_model_vocabulary() -> None:
    """Phase 1 的 `basis` 字彙是唯一的知識種類語言；假設不得自創第二套。"""
    assert set(ASSUMPTION_BASES) <= set(BASES)
    assert "deterministic" not in ASSUMPTION_BASES          # 輸入假設永遠不是確定性事實


def test_heuristic_only_inputs_yield_heuristic_dependency() -> None:
    """只用 heuristic 假設（沒有 session 判斷）時，依賴就是 heuristic——不高估也不低估。"""
    assumptions = [a for a in _full_set() if a.basis == "heuristic_proxy"] + [
        _assumption("revenue_growth", "total", 0.40, basis="heuristic_proxy", refs=(ACT_REF.ref,)),
        _assumption("operating_margin_delta", "carry", 0.0, basis="heuristic_proxy", refs=(ACT_REF.ref,)),
    ]
    result = _run(assumptions)
    assert result.metrics["eps"].input_dependency == "heuristic_proxy"
    assert result.metrics["operating_margin"].value == pytest.approx(NG_OI / REVENUE)


# ---------------------------------------------------------------------------
# 3. Missing != Zero
# ---------------------------------------------------------------------------

def test_missing_segment_assumption_makes_revenue_missing_not_zero_growth() -> None:
    assumptions = [a for a in _full_set() if a.scope != "Industrial"]
    result = _run(assumptions)
    revenue = result.metrics["revenue"]
    assert revenue.value is None and revenue.input_dependency is None
    assert "Industrial" in (revenue.reason or "")
    assert result.metrics["eps"].value is None
    assert result.status == "partial"                       # 營益率仍算得出
    contribution = next(s for s in result.steps if s.key == "segment_growth_contribution:Industrial")
    assert contribution.value is None and contribution.basis == "none"


def test_missing_margin_assumption_is_missing_not_zero_percent() -> None:
    assumptions = [a for a in _full_set() if a.driver != "operating_margin_delta"]
    result = _run(assumptions)
    margin = result.metrics["operating_margin"]
    assert margin.value is None
    assert "operating_margin_delta" in (margin.reason or "")
    assert result.metrics["revenue"].is_known
    assert result.metrics["eps"].value is None


def test_no_assumptions_at_all_is_missing_with_counts() -> None:
    result = _run([])
    assert result.status == "missing"
    assert all(not m.is_known for m in result.metrics.values())
    assert result.selection.input_count == 0 and result.selection.accepted_count == 0
    assert result.comparisons["eps"].status == "internal_missing"
    assert result.comparisons["eps"].absolute_gap is None


def test_missing_consensus_is_none_not_zero() -> None:
    result = _run(consensus=(_consensus("eps", None), _consensus("revenue", 10_618_193_080.0)))
    eps = result.comparisons["eps"]
    assert eps.status == "consensus_missing" and eps.absolute_gap is None and eps.relative_gap is None
    assert result.comparisons["revenue"].status == "comparable"
    assert result.comparisons["operating_margin"].status == "consensus_missing"


def test_missing_base_observation_makes_everything_missing_but_keeps_consensus_visible() -> None:
    result = _run(actuals=None, actuals_reason="Engine C 無 fiscal_year_results")
    assert result.status == "missing"
    assert result.base_period is None and result.target_period == TARGET   # 由最早的共識期間推
    assert result.metrics["eps"].value is None
    assert result.comparisons["eps"].status == "internal_missing"
    assert len(result.consensus) == 2                       # 共識仍現形


# ---------------------------------------------------------------------------
# 4. 期間與口徑是身分
# ---------------------------------------------------------------------------

def test_fy27_internal_is_not_compared_with_fy26_or_fy28_consensus() -> None:
    result = _run()
    internal = result.metrics["eps"]
    for other in (BASE, TARGET.shifted(1)):
        cmp = compare_metric("eps", internal, _consensus("eps", 13.955, period=other, year_ago=5.61),
                             consensus_basis="non_gaap", internal_currency="USD")
        assert cmp.status == "incompatible_period", other
        assert cmp.absolute_gap is None and cmp.relative_gap is None
    # 經模型：只有 FY2028 的共識 → 目標期間 FY2027 沒有共識可比，不是拿 FY2028 湊
    fy28_only = _run(consensus=(_consensus("eps", 13.955, period=TARGET.shifted(1), year_ago=9.416),))
    assert fy28_only.comparisons["eps"].status == "consensus_missing"


def test_fiscal_period_identity_is_the_end_date_not_the_label() -> None:
    a = FiscalPeriod(end=date(2027, 1, 31))
    b = FiscalPeriod(end=date(2027, 1, 25))                 # 52／53 週制的同一年
    c = FiscalPeriod(end=date(2027, 6, 30))
    assert a.same_as(b) and not a.same_as(c)
    assert a.label == c.label == "FY2027"                   # 標籤相同不代表同期——身分是日期
    assert FiscalPeriod(end=date(2024, 2, 29)).shifted(1).end == date(2025, 2, 28)
    with pytest.raises(ContractViolation):
        FiscalPeriod(end=date(2027, 6, 30), kind="ttm")


def test_consensus_basis_is_verified_against_primary_actuals_not_assumed() -> None:
    actuals = _actuals()
    assert verify_consensus_basis(_consensus("eps", 9.4, year_ago=5.61), actuals) == "non_gaap"
    assert verify_consensus_basis(_consensus("eps", 9.4, year_ago=4.12), actuals) == "gaap"
    assert verify_consensus_basis(_consensus("eps", 9.4, year_ago=5.0), actuals) == "unverified"
    assert verify_consensus_basis(_consensus("eps", 9.4, year_ago=None), actuals) == "unverified"
    assert verify_consensus_basis(_consensus("eps", 9.4, year_ago=5.61), None) == "unverified"
    # 去年實際值對應的不是我們手上的基期 → 不能核實
    assert verify_consensus_basis(_consensus("eps", 13.9, period=TARGET.shifted(1), year_ago=5.61),
                                  actuals) == "unverified"
    assert verify_consensus_basis(_consensus("revenue", 1.0e10), actuals) == "not_applicable"


def test_unverified_or_mismatched_basis_yields_no_gap() -> None:
    internal = _run().metrics["eps"]                         # non_gaap
    for basis in ("unverified", "gaap", "not_applicable"):
        cmp = compare_metric("eps", internal, _consensus("eps", 9.41634, year_ago=4.12),
                             consensus_basis=basis, internal_currency="USD")
        assert cmp.status == "incompatible_basis", basis
        assert cmp.absolute_gap is None and cmp.relative_gap is None
    # 經模型：year_ago 對到 GAAP → 口徑不合，不減
    gaap_consensus = _run(consensus=(_consensus("eps", 9.41634, year_ago=4.12),))
    assert gaap_consensus.comparisons["eps"].status == "incompatible_basis"
    assert gaap_consensus.consensus_bases[f"eps:{TARGET.end.isoformat()}"] == "gaap"


def test_comparable_gap_arithmetic_and_provenance() -> None:
    result = _run()
    cmp = result.comparisons["eps"]
    internal = result.metrics["eps"].value
    assert cmp.status == "comparable"
    assert cmp.accounting_basis_internal == cmp.accounting_basis_consensus == "non_gaap"
    assert cmp.absolute_gap == pytest.approx(internal - 9.41634)
    assert cmp.relative_gap == pytest.approx(internal / 9.41634 - 1.0)
    assert cmp.analyst_count == 22 and cmp.consensus_captured_at == date(2026, 9, 4)
    assert cmp.assumption_ids == result.metrics["eps"].assumption_ids
    assert cmp.consensus_refs == (f"engine_c://consensus_estimate/COHR/eps/{TARGET.end.isoformat()}",)
    rev = result.comparisons["revenue"]
    assert rev.status == "comparable" and rev.accounting_basis_consensus == "not_applicable"


def test_currency_mismatch_is_incompatible_unit() -> None:
    result = _run(consensus=(_consensus("revenue", 1.0e12, currency="KRW"),))
    assert result.comparisons["revenue"].status == "incompatible_unit"


def test_forward_pe_derived_eps_never_enters_the_model() -> None:
    """`price/pe_forward` 導出的 EPS-like 值不是分析師共識；模型連參數都沒有給它。"""
    source = inspect.getsource(build_fundamental_model) + inspect.getsource(compare_metric)
    for token in ("forward_eps", "pe_forward", "forward_pe", "ConsensusSnapshot"):
        assert token not in source, token
    with pytest.raises(ContractViolation):
        ConsensusEstimate(metric="forward_eps_proxy", period=TARGET, value=13.9, source="x", evidence=(ACT_REF,))


# ---------------------------------------------------------------------------
# 5. PIT
# ---------------------------------------------------------------------------

def test_assumptions_created_after_as_of_are_invisible() -> None:
    """只隔離假設的 PIT：基期觀測與共識都在 as_of 之前就存在，唯獨假設寫於 09-05。"""
    early_actuals = _actuals(recorded_at=datetime(2026, 8, 13, tzinfo=UTC))
    early_consensus = (_consensus("eps", 9.0, year_ago=5.61, captured=date(2026, 8, 20)),
                       _consensus("revenue", 1.0e10, captured=date(2026, 8, 20)))
    result = _run(as_of=date(2026, 9, 1), actuals=early_actuals, consensus=early_consensus)
    assert result.target_period == TARGET                   # 目標期間推得出來，只是沒有假設
    assert result.status == "missing"
    assert result.selection.reasons.get("created_after_as_of") == 7
    assert result.selection.accepted_count == 0
    assert result.metrics["eps"].value is None
    assert result.comparisons["eps"].status == "internal_missing"
    # 對照：as_of 在寫入之後就看得到
    later = _run(as_of=date(2026, 9, 5), actuals=early_actuals, consensus=early_consensus)
    assert later.status == "available" and later.as_of == date(2026, 9, 5)


def test_actuals_recorded_after_as_of_are_refused() -> None:
    result = _run(as_of=date(2026, 8, 20))                   # 觀測 recorded_at 09-05
    assert result.base_actuals is None
    assert result.status == "missing"
    assert any("lookahead" in w or "晚於 as_of" in w for w in result.warnings)


def test_consensus_captured_after_as_of_is_excluded() -> None:
    early = _assumption("revenue_growth", "total", 0.4, created="2026-08-01T00:00:00+00:00")
    result = build_fundamental_model(
        company_id="co:coherent", ticker="COHR", as_of=date(2026, 8, 15), today=TODAY,
        actuals=_actuals(recorded_at=datetime(2026, 8, 13, tzinfo=UTC)), actuals_reason=None,
        consensus=(_consensus("eps", 9.4, year_ago=5.61, captured=date(2026, 9, 4)),),
        guidance=(), assumption_records=[early], evidence_index=INDEX)
    assert result.consensus == ()
    assert result.comparisons["eps"].status in ("consensus_missing", "internal_missing")
    assert any("共識晚於 as_of" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# 6. Ledger 語意：supersede／retract／證據解析／字彙
# ---------------------------------------------------------------------------

def test_newer_record_supersedes_and_retraction_removes() -> None:
    first = _assumption("tax_rate", "total", 0.19, created="2026-09-01T00:00:00+00:00")
    second = _assumption("tax_rate", "total", 0.21, created="2026-09-02T00:00:00+00:00")
    accepted, selection = select_assumptions([first, second], target=TARGET, as_of=None, today=TODAY,
                                             evidence_index=INDEX)
    assert [a.value for a in accepted] == [0.21]
    assert selection.reasons == {"superseded_by_newer": 1}
    retraction = _assumption("tax_rate", "total", 0.21, created="2026-09-03T00:00:00+00:00",
                             supersedes_id=second.assumption_id, retracted=True)
    accepted, selection = select_assumptions([first, second, retraction], target=TARGET, as_of=None,
                                             today=TODAY, evidence_index=INDEX)
    assert accepted == ()                                    # 撤回不會讓更早的 0.19 復活
    assert selection.reasons == {"superseded_by_newer": 1, "superseded": 1, "retracted": 1}
    assert selection.filtered_count == 3
    # as-of 回到撤回之前：0.21 仍生效——ledger 是可回放的
    accepted, _ = select_assumptions([first, second, retraction], target=TARGET, as_of=date(2026, 9, 2),
                                     today=TODAY, evidence_index=INDEX)
    assert [a.value for a in accepted] == [0.21]


def test_unresolved_evidence_rejects_assumption_and_counts() -> None:
    bad = _assumption("revenue_growth", "Industrial", -0.03, refs=("graph://edge/does/not/exist",))
    assumptions = [a for a in _full_set() if a.scope != "Industrial"] + [bad]
    result = _run(assumptions)
    assert result.selection.reasons.get("unresolved_evidence") == 1
    assert bad.assumption_id not in {a.assumption_id for a in result.assumptions}
    assert result.metrics["revenue"].value is None           # 被拒的假設不會偷偷生效
    assert any(item[0] == bad.assumption_id and "unresolved_evidence" in item[1]
               for item in result.selection.rejected)


def test_other_period_assumptions_do_not_leak_into_the_target() -> None:
    fy28 = _assumption("revenue_growth", "total", 0.30, period_end=TARGET.shifted(1).end)
    accepted, selection = select_assumptions([fy28], target=TARGET, as_of=None, today=TODAY,
                                             evidence_index=INDEX)
    assert accepted == () and selection.reasons == {"other_period": 1}


def test_driver_vocabulary_is_closed_and_validated() -> None:
    with pytest.raises(ContractViolation, match="driver 未登記"):
        _assumption("capex_intensity", "total", 0.1)
    with pytest.raises(ContractViolation, match="必須至少引用一條證據"):
        _assumption("tax_rate", "total", 0.19, refs=())
    with pytest.raises(ContractViolation, match="低於下限"):
        _assumption("revenue_growth", "total", -1.5)
    with pytest.raises(ContractViolation, match="scope 只能是"):
        _assumption("tax_rate", "segment_a", 0.19)
    with pytest.raises(ContractViolation, match="basis 未登記"):
        _assumption("tax_rate", "total", 0.19, basis="deterministic")
    record = assumption_record(company_id="co:x", ticker="X", period_end=TARGET.end, driver="tax_rate",
                               scope="total", value=0.2, basis="heuristic_proxy", rationale="r",
                               evidence_refs=["e"], created_at=datetime(2026, 9, 5, tzinfo=UTC))
    record["unit"] = "currency"                               # 單位跟著 driver，改了就拒收
    with pytest.raises(ContractViolation, match="單位必須是"):
        parse_assumption_record(record)
    assert set(ASSUMPTION_DRIVERS) == {"revenue_growth", "operating_margin_delta",
                                       "interest_and_other_net", "tax_rate", "nci_attribution",
                                       "diluted_shares"}


def test_total_and_segment_growth_cannot_coexist() -> None:
    assumptions = _full_set() + [_assumption("revenue_growth", "total", 0.5)]
    with pytest.raises(ContractViolation, match="不得並存"):
        build_bridge(_actuals(), assumptions, TARGET)


# ---------------------------------------------------------------------------
# 7. 敏感度、口徑選擇、契約形狀
# ---------------------------------------------------------------------------

def test_sensitivities_are_deterministic_perturbations() -> None:
    result = _run()
    by_scope = {s.scope: s for s in result.sensitivities}
    dc = by_scope["Datacenter & Communications"]
    assert dc.bump == 0.01 and dc.bump_unit == "absolute_ratio"
    assert dc.delta_revenue == pytest.approx(DC * 0.01)
    assert dc.delta_eps is not None and dc.delta_eps > 0
    shares = by_scope["total"] if by_scope["total"].driver == "diluted_shares" else None
    # 股數 ×1.01 → EPS 幾乎 −1%（其他不變）
    share_sens = next(s for s in result.sensitivities if s.driver == "diluted_shares")
    assert share_sens.bump_unit == "relative"
    assert share_sens.eps_relative == pytest.approx(1 / 1.01 - 1.0)
    assert share_sens.delta_revenue == 0.0


def test_bridge_falls_back_to_gaap_when_non_gaap_block_is_absent() -> None:
    result = _run(actuals=_actuals(non_gaap=None))
    assert result.accounting_basis == "gaap"
    assert result.metrics["operating_margin"].value == pytest.approx(897_900_000.0 / REVENUE + 0.025)
    # 共識口徑核到 non_gaap，內部卻是 gaap → 不減
    assert result.comparisons["eps"].status == "incompatible_basis"


def test_outputs_carry_no_portfolio_or_capital_fields() -> None:
    banned = {"nav", "weight", "allocation", "position", "portfolio", "capital", "sizing", "notional"}
    for cls in (FundamentalModelResult, ModeledMetric, OperatingAssumption):
        for f in fields(cls):
            assert not (set(f.name.lower().split("_")) & banned), f"{cls.__name__}.{f.name}"


def test_modeled_metric_contract_enforces_missing_is_not_zero() -> None:
    with pytest.raises(ContractViolation):
        ModeledMetric(metric="eps", period=TARGET, value=1.0, unit="x", accounting_basis="gaap")   # 有值沒依賴
    with pytest.raises(ContractViolation):
        ModeledMetric(metric="eps", period=TARGET, value=None, unit="x", accounting_basis="gaap",
                      input_dependency="observation")                                              # 沒值卻有依賴
    ok = ModeledMetric(metric="eps", period=TARGET, value=None, unit="x", accounting_basis="gaap",
                       reason="缺假設")
    assert not ok.is_known


def test_model_result_is_replace_safe_for_read_model_tests() -> None:
    """read model 測試會用 `replace` 改一個值來證明 builder 只是 pass-through；契約要允許。"""
    result = _run()
    changed = replace(result.metrics["eps"], value=123.456)
    assert changed.value == 123.456 and changed.assumption_ids == result.metrics["eps"].assumption_ids
