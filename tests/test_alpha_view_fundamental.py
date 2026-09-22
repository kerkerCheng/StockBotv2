"""Alpha Investment Read Model × Causal Fundamental Model：builder 只選取、renderer 只排版。

守的是 Phase 2 的 read-model 整合契約：`internal_fundamentals`／`earnings_bridge`／
`expectation_gap.internal_vs_consensus` 由 `alpha.fundamental` 填入，builder 不自算；
沒有模型輸出時是 `missing`（有能力沒資料），不是 `not_modeled`；Q4 的 session 判斷與
數值 gap 並存且分開標示；as-of 不符的 model 被拒收。
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from briefing.alpha_view import compact_card, render_alpha_cards, render_alpha_investment_view_markdown
from briefing.alpha_view.contracts import CAP_FINANCIAL_CAUSAL, CAP_NUMERIC_EXPECTATION_GAP
from tests.test_alpha_investment_view import TODAY, _as_of_build, _view
from tests.test_alpha_view_brief import _card
from tests.test_fundamental_model import _actuals, _run

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def test_read_model_fills_internal_fundamentals_from_the_model_not_by_itself() -> None:
    model = _run()
    view = _view(fundamental_model=model)
    section = view.internal_fundamentals
    assert section.meta.status == "available"
    assert section.meta.capability == CAP_FINANCIAL_CAUSAL
    assert section.meta.basis == "deterministic"
    assert section.period == "FY2027" and section.period_end == date(2027, 6, 30)
    assert section.base_period_end == date(2026, 6, 30) and section.accounting_basis == "non_gaap"
    eps = next(d for d in section.items if d.key == "internal_eps")
    assert eps.value == model.metrics["eps"].value                       # 逐位相同：沒有重算
    assert eps.basis == "deterministic" and eps.authority == "alpha://fundamental/bridge"
    assert eps.dependencies["input_dependency"] == "session_judgment"
    assert eps.dependencies["assumption_ids"] == list(model.metrics["eps"].assumption_ids)
    assert eps.dependencies["accounting_basis"] == "non_gaap"
    assert "engine_c://manual_observation/mo_fy2026" in eps.evidence_refs
    assert view.capability_map()["internal_fundamentals"]["status"] == "available"
    assert view.capability_map()["earnings_bridge"]["capability"] == CAP_FINANCIAL_CAUSAL
    # 因果 section 的財務橋一格：available，但 causal section 本身仍是 structural
    assert view.causal_paths.financial_causal_model.status == "available"
    assert view.causal_paths.meta.capability == "structural_causal_model"


def test_bridge_section_carries_steps_assumptions_and_sensitivities_with_their_own_basis() -> None:
    model = _run()
    bridge = _view(fundamental_model=model).earnings_bridge
    assert bridge.meta.status == "available" and bridge.period == "FY2027"
    assert len(bridge.steps) == len(model.steps)
    by_key = {d.key: d for d in bridge.steps}
    assert by_key["base_revenue"].basis == "observation"
    assert by_key["revenue_growth:Datacenter & Communications"].basis == "session_judgment"
    assert by_key["tax_rate"].basis == "heuristic_proxy"
    assert by_key["internal_eps"].basis == "deterministic" and by_key["internal_eps"].method
    assert {d.basis for d in bridge.assumptions} == {"session_judgment", "heuristic_proxy"}
    assert all(d.authority == "alpha://fundamental/assumptions" for d in bridge.assumptions)
    assert all(d.dependencies and d.dependencies["assumption_id"].startswith("oa_") for d in bridge.assumptions)
    assert len(bridge.sensitivities) == len(model.sensitivities)
    assert bridge.selection is not None and bridge.selection.accepted_count == 7


def test_numeric_gap_and_q4_coexist_and_are_labelled_differently() -> None:
    model = _run()
    view = _view(fundamental_model=model)
    gap = view.expectation_gap
    assert gap.session_judgment.basis == "session_judgment"              # Q4 仍在，仍是 session 判斷
    assert gap.meta.capability == CAP_NUMERIC_EXPECTATION_GAP
    eps = next(d for d in gap.numeric_comparisons if d.key == "internal_vs_consensus_eps")
    assert eps.status == "available" and eps.basis == "deterministic"
    assert eps.authority == "alpha://fundamental/compare"
    assert eps.value["relative_gap"] == model.comparisons["eps"].relative_gap
    assert eps.value["period"] == "FY2027" and eps.value["analyst_count"] == 22
    margin = next(d for d in gap.numeric_comparisons if d.key == "internal_vs_consensus_operating_margin")
    assert margin.status == "missing" and margin.value is None and "consensus_missing" in (margin.reason or "")
    assert gap.internal_vs_consensus.status == "partial"                 # 三個指標只有兩個可比
    assert gap.internal_vs_price_implied.status == "not_modeled"          # 估值側仍未建模
    assert any("不是 Q4" in (gap.internal_vs_consensus.reason or "") for _ in (0,))


def test_incompatible_comparisons_render_as_not_applicable_never_as_numbers() -> None:
    from tests.test_fundamental_model import _consensus

    # ⚠ 2026-09-13 起 `year_ago=4.12`（核到 GAAP）不再產生 incompatible——**橋會跟著共識改用 GAAP**
    # （ROADMAP：橋的口徑選取要跟著已核實的共識口徑走）。要測「不可比一律顯示不適用」，
    # 就得用一個**真的無從核實**的共識：`year_ago` 對不上基期的任何一個 EPS → `unverified`。
    model = _run(consensus=(_consensus("eps", 9.41634, year_ago=7.77),))
    assert model.consensus_bases[f"eps:{model.target_period.end.isoformat()}"] == "unverified"
    view = _view(fundamental_model=model)
    eps = next(d for d in view.expectation_gap.numeric_comparisons if d.key == "internal_vs_consensus_eps")
    assert eps.status == "not_applicable" and eps.value is None
    assert "incompatible_basis" in (eps.reason or "")
    assert view.expectation_gap.internal_vs_consensus.value is None
    text = render_alpha_investment_view_markdown(view)
    line = next(l for l in text.splitlines() if "內部 EPS vs 共識 EPS" in l)
    assert "不適用" in line and "incompatible" in line


def test_builder_is_pass_through_not_a_calculator() -> None:
    model = _run()
    metrics = dict(model.metrics)
    metrics["eps"] = replace(metrics["eps"], value=123.456)
    tampered = replace(model, metrics=metrics)
    view = _view(fundamental_model=tampered)
    eps = next(d for d in view.internal_fundamentals.items if d.key == "internal_eps")
    assert eps.value == 123.456                                          # builder 照抄，不重算


def test_without_a_model_sections_are_missing_not_not_modeled() -> None:
    view = _view(fundamental_model=None, fundamental_model_reason="測試：provider 無 fiscal 能力")
    assert view.internal_fundamentals.meta.status == "missing"
    assert "provider 無 fiscal 能力" in (view.internal_fundamentals.meta.reason or "")
    assert view.earnings_bridge.meta.status == "missing"
    assert view.expectation_gap.internal_vs_consensus.status == "missing"
    assert view.implied_return.meta.status == "missing"                  # Step 2：有能力了；沒資料是 missing
    # D2（2026-09-18）：下檔**已經建模**——它是 downside scenario 走同一條橋的結果。
    # 所以這裡從 `not_modeled`（沒這個能力）變成 `missing`（有能力、這一檔還沒有人寫）。
    # ⚠ 這兩者的下一步完全不同，正是這條斷言要守的：`not_modeled` 沒有人該去補，
    # `missing` 有——它會帶著 `not_yet_recorded` 出現在待辦裡。
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：E 組（賭注四價 overlay）退役。
    assert not hasattr(view, "downside"), "退役的 section 不得復活"
    assert view.consensus.fiscal_items == ()


def test_partial_model_is_partial_in_the_read_model() -> None:
    from tests.test_fundamental_model import _full_set

    model = _run([a for a in _full_set() if a.scope != "Industrial"])
    view = _view(fundamental_model=model)
    assert view.internal_fundamentals.meta.status == "partial"
    revenue = next(d for d in view.internal_fundamentals.items if d.key == "internal_revenue")
    assert revenue.status == "missing" and revenue.value is None and "Industrial" in (revenue.reason or "")
    margin = next(d for d in view.internal_fundamentals.items if d.key == "internal_operating_margin")
    assert margin.is_known
    step = next(d for d in view.earnings_bridge.steps if d.key == "segment_growth_contribution:Industrial")
    assert step.status == "missing" and step.value is None


def test_builder_refuses_a_model_run_at_a_different_as_of() -> None:
    build = _as_of_build(date(2026, 8, 15))
    from briefing.alpha_view import build_alpha_investment_view

    current_model = _run()                                               # as_of=None（當前）
    view = build_alpha_investment_view(build=build, fundamental_model=current_model, today=TODAY)
    assert view.internal_fundamentals.meta.status == "missing"
    assert "INV-6" in (view.internal_fundamentals.meta.reason or "")
    assert view.expectation_gap.numeric_comparisons and all(
        d.value is None for d in view.expectation_gap.numeric_comparisons)
    # 對照：用同一個 as_of 跑的 model 可以進歷史卡（假設寫於 09-05 → 在 08-15 是 missing，這也是對的）
    matching = _run(as_of=date(2026, 8, 15), actuals=_actuals())
    view_ok = build_alpha_investment_view(build=build, fundamental_model=matching, today=TODAY)
    assert "INV-6" not in (view_ok.internal_fundamentals.meta.reason or "")
    assert view_ok.internal_fundamentals.meta.status == "missing"        # 當時沒有假設、觀測也還沒寫


def test_consensus_section_lists_fy_identified_items_and_keeps_forward_eps_out_of_the_gap() -> None:
    model = _run()
    view = _view(fundamental_model=model)
    fiscal = {d.key: d for d in view.consensus.fiscal_items}
    assert "consensus_eps_FY2027" in fiscal and fiscal["consensus_eps_FY2027"].basis == "observation"
    assert fiscal["consensus_eps_FY2027"].authority == "engine_c://consensus_estimates"
    assert fiscal["consensus_eps_FY2027"].value["accounting_basis"] == "non_gaap"
    assert "FY2027" in (view.consensus.meta.reason or "")
    forward = next(d for d in view.consensus.items if d.key == "forward_eps")
    assert forward.authority == "engine_c://estimates"                    # 導出值，另一個 authority
    eps_gap = next(d for d in view.expectation_gap.numeric_comparisons if d.key == "internal_vs_consensus_eps")
    assert "engine_c://financial_snapshot/COHR" not in eps_gap.evidence_refs   # 導出 EPS 不是共識
    assert any("consensus_estimate" in r for r in eps_gap.evidence_refs)
    assert eps_gap.dependencies["accounting_basis_consensus"] == "non_gaap"


def test_renderer_prints_assumptions_with_their_knowledge_kind_and_no_zero_for_missing() -> None:
    model = _run()
    text = render_alpha_investment_view_markdown(_view(fundamental_model=model))
    assert "目標期間：FY2027" in text
    assert "生效的營運假設" in text and "敏感度" in text and "逐指標" in text
    assert "輸入知識種類 **session 判斷**" in text
    eps_line = next(l for l in text.splitlines() if "內部稀釋 EPS 估計" in l)
    assert "〔確定性規則｜`alpha://fundamental/bridge`" in eps_line
    growth_line = next(l for l in text.splitlines() if "假設 revenue\\_growth\\[Datacenter" in l
                       or "假設 revenue_growth[Datacenter" in l)
    assert "session 判斷" in growth_line
    partial = render_alpha_investment_view_markdown(_view(fundamental_model=_run(
        [a for a in __import__("tests.test_fundamental_model", fromlist=["_full_set"])._full_set()
         if a.driver != "operating_margin_delta"])))
    margin_line = next(l for l in partial.splitlines() if "內部營益率估計" in l)
    assert "缺料" in margin_line and "0.0%" not in margin_line


def test_compact_card_and_daily_brief_cell_select_the_gap_without_recomputing() -> None:
    model = _run()
    card = compact_card(_view(fundamental_model=model))
    assert card["internal_fundamentals_status"] == "available"
    assert card["internal_vs_consensus"]["eps"]["status"] == "available"
    assert card["internal_vs_consensus"]["eps"]["relative_gap"] == model.comparisons["eps"].relative_gap
    assert card["internal_vs_consensus"]["eps"]["period"] == "FY2027"
    assert "internal_fundamentals" not in card["not_modeled"]
    row = next(l for l in render_alpha_cards([card]) if l.startswith("| co:coherent"))
    assert "（FY2027）" in row and row.count("|") == 12        # Step 0.5 多一欄 Refresh；Step 1 多一欄 Fair value
    # 舊 fixture 沒有這個欄位 → 「未提供」，不是 0
    legacy = next(l for l in render_alpha_cards([_card()]) if l.startswith("| co:coherent"))
    assert "未提供" in legacy and legacy.count("|") == 12


def test_sources_fail_soft_when_the_provider_has_no_fiscal_capability(monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha.identity import CompanyId, Ticker
    from briefing.alpha_view import sources
    from tests.test_alpha_investment_view import _FakeFundamentals, _build

    build = _build()
    model, reason, _records = sources._fundamental_model(  # noqa: SLF001
        build, _FakeFundamentals(), Ticker("COHR"), CompanyId("co:coherent"), as_of=None, today=TODAY)
    assert model is None and "沒有" in reason

    class _Exploding(_FakeFundamentals):
        def fiscal_year_results(self, ticker, *, as_of=None):
            raise RuntimeError("boom")

        def fiscal_consensus(self, ticker, *, as_of=None):
            return (), None

        def company_guidance(self, ticker, *, as_of=None):
            return (), None

    model, reason, _records = sources._fundamental_model(  # noqa: SLF001
        build, _Exploding(), Ticker("COHR"), CompanyId("co:coherent"), as_of=None, today=TODAY)
    assert model is None and "執行失敗" in reason and "boom" in reason


def test_evidence_index_resolves_the_models_own_citations() -> None:
    """假設引用的 engine_c://manual_observation／consensus_estimate 必須出現在卡片自己的 evidence index，
    否則讀者拿著卡片對不回引用（Phase 2 驗收 2026-09-06 抓到的 provenance 缺口）。"""
    model = _run()
    view = _view(fundamental_model=model)
    indexed = {item.ref for item in view.evidence.index}
    for ref in model.evidence:
        assert ref.ref in indexed
    engine_c_refs = {r for d in view.earnings_bridge.assumptions for r in d.evidence_refs
                     if r.startswith("engine_c://")}
    assert engine_c_refs and engine_c_refs <= indexed        # graph:// 引用由 context 供應，fixture 不含
    # 沒有模型時 evidence index 不受影響
    assert "engine_c://manual_observation/mo_fy2026" not in {i.ref for i in _view().evidence.index}


def test_reporting_currency_label_comes_from_the_filing_not_from_the_quote_currency() -> None:
    """`reporting_currency（X）` 的 X 必須是**財報幣別**，不是報價幣別。

    事發（2026-09-13，XFAB.PA）：這個標籤一直是用 registry 的 `market_currency` 組的，
    而它掛的是法定財報幣別的數字（內部營收／營業利益／淨利／fair value）。
    兩者相同的美股看不出來；不同的 5 檔全部標錯——最危險的是 **IQE.L（GBP 財報／GBp 報價）**，
    把報表數字標成 minor unit 會差 100 倍，正是 `AGENTS.md`「報價單位 ≠ 結算幣別」那一條。

    ⚠ 不得回退到 `market_currency`：答不出報表幣別就寫「未知」——
    「不知道」與「等於報價幣別」是兩個 claim，後者舉證責任高得多（L11-5）。
    """
    model = _run()
    assert model.base_actuals is not None
    view = _view(fundamental_model=model,
                 identity={"market_currency": "SEK", "market_quote_unit": "SEK"})

    units = {item.unit for item in view.internal_fundamentals.items
             if item.unit and item.unit.startswith("reporting_currency")}
    assert units, "內部基本面沒有任何 reporting_currency 欄位——這個測試會變成恆真"
    for unit in units:
        assert model.base_actuals.currency in unit, f"{unit} 沒有用財報幣別"
        assert "SEK" not in unit, "報價幣別漏進了報表幣別的標籤"
