"""Alpha Investment View（canonical read model）的**誠實性**測試。

守的不是「欄位有沒有」，是**這一層不得說謊**：
缺席不得變成 0、proxy 不得變成 model、session 判斷不得變成 deterministic、
structural causal 不得變成 financial causal、賣方目標價不得變成預期報酬、
view 不得長出任何部位欄位。全部跑在 fake provider 上，不需要 Neo4j／Engine C。
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from alpha.context import build_research_context
from alpha.contracts import (
    FORBIDDEN_POSITION_TOKENS, ConsensusSnapshot, EvidenceRef, FreshnessState,
    FundamentalsSnapshot, MarketSnapshot,
)
from alpha.errors import ContractViolation
from alpha.identity import CompanyId, Ticker
from alpha.models import compose_signal
from alpha.testing import FakeGraphResearchProvider
from briefing.alpha_view import (
    AlphaInvestmentView, Datum, DecisionFacts, ViewContractViolation,
    build_alpha_investment_view, compact_card,
)
from briefing.alpha_view.contracts import (
    CAP_FINANCIAL_CAUSAL, CAP_NARRATIVE_SCENARIOS, CAP_STRUCTURAL_CAUSAL, VALUELESS_STATUSES,
)

COMPANY = CompanyId("co:coherent")
TICKER = Ticker("COHR")
TODAY = date(2026, 9, 5)

_CORROBORATED = EvidenceRef(
    ref="graph://assertion/e1", kind="graph_edge",
    evidence_class="externally_corroborated", evidence_tier=1, published_at=date(2026, 5, 1),
)
_SELF_REPORTED = EvidenceRef(
    ref="graph://assertion/weak", kind="graph_edge",
    evidence_class="self_reported", evidence_tier=4, published_at=date(2026, 5, 1),
)


def _measurement() -> EvidenceRef:
    return EvidenceRef(ref="engine_c://financial_snapshot/COHR", kind="engine_c_snapshot",
                       origin_entity="yfinance", published_at=date(2026, 9, 4),
                       retrieved_at=date(2026, 9, 5))


class _FakeFundamentals:
    """Engine C 的 in-memory 替身；`forward_pe`／`trailing_pe` 可調，用來測 proxy 邊界。"""

    def __init__(self, *, forward_pe: float | None = 20.0, trailing_pe: float | None = 68.0,
                 available: bool = True, target_mean: float | None = 415.0):
        self.forward_pe = forward_pe
        self.trailing_pe = trailing_pe
        self.available = available
        self.target_mean = target_mean

    def _fresh(self) -> FreshnessState:
        return FreshnessState(date(2026, 9, 4), 1.0, "available")

    def fundamentals(self, ticker, *, as_of=None):
        if not self.available:
            return FundamentalsSnapshot(), FreshnessState(None, None, "missing", "無快照")
        return (FundamentalsSnapshot(gross_margin=0.375, operating_margin=0.118, revenue_ttm=7.1e9,
                                     free_cash_flow_ttm=-6.5e8, cash_and_equivalents=1.99e9,
                                     total_debt=3.55e9, shares_outstanding=1.958e8,
                                     segment_revenue_share=None, evidence=(_measurement(),)),
                self._fresh())

    def market(self, ticker, *, as_of=None):
        if not self.available:
            return MarketSnapshot(), FreshnessState(None, None, "missing", "無快照")
        return (MarketSnapshot(price=281.86, bar_date=date(2026, 9, 4), price_kind="close",
                               market_cap=281.86 * 1.958e8, evidence=(_measurement(),)),
                self._fresh())

    def consensus(self, ticker, *, as_of=None):
        if not self.available:
            return ConsensusSnapshot(), FreshnessState(None, None, "missing", "無快照")
        return (ConsensusSnapshot(analyst_count=22, target_mean=self.target_mean,
                                  forward_pe=self.forward_pe, trailing_pe=self.trailing_pe,
                                  ev_revenue=7.5, revenue_estimate_next_fy=1.467e10,
                                  revenue_estimate_next_fy_growth=0.382,
                                  evidence=(_measurement(),)),
                self._fresh())

    def estimate_revision(self, ticker, *, as_of=None, sessions=30):
        if not self.available:
            return None
        return {"from": "2026-08-04", "to": "2026-09-04", "observations": 31,
                "eps_change": 0.683, "price_change": -0.022, "estimate_vs_price": 0.72}


def _build(fundamentals: _FakeFundamentals | None = None):
    return build_research_context(
        ticker=TICKER, company_id=COMPANY,
        graph_provider=FakeGraphResearchProvider(company_id=COMPANY,
                                                 evidence_pool=(_CORROBORATED, _SELF_REPORTED)),
        fundamentals_provider=fundamentals or _FakeFundamentals(),
    )


def _judgment(**overrides: Any) -> dict[str, Any]:
    base = {
        "_produced_at": "2026-09-04",
        "axes": {
            "value_capture": {"level": "strong", "reason": "客戶端資本承諾",
                              "evidence": [_CORROBORATED.ref]},
            "earnings_exposure": {"level": "unknown", "reason": "無 segment revenue", "evidence": []},
            "expectation_gap": {"level": "weak", "reason": "市場已 price in 大幅成長",
                                "evidence": [_CORROBORATED.ref]},
            "catalyst": {"level": "unknown", "reason": "無結構化催化劑來源", "evidence": []},
        },
        "direction": "long", "confidence": 0.45, "expected_horizon": "2-4 quarters",
        "thesis": "sole_source 結構位置", "variant_view": "市場隱含 X／本 thesis Y／催化劑 Z",
        "bull_case": "毛利率上行", "base_case": "營收兌現毛利落後", "bear_case": "供給側擴張",
        "risks": ["FCF 為負"],
        "disproof_conditions": [{
            "condition": "毛利率連兩季低於 40.2%", "check_frequency": "quarterly",
            "action_within_48h": "強制 review",
        }],
    }
    base.update(overrides)
    return base


def _facts(**overrides: Any) -> DecisionFacts:
    base = dict(
        cohort_id="dc_test", research_status="READY", lifecycle_status="active",
        decision_effective_at="2026-08-31T11:30:20+00:00",
        legacy_weakest_axis="technical_causal_link",
        legacy_axis_levels={"technical_causal_link": "bounded_hypothesis"},
        catalyst="Q1 FY2027 財報（約 2026 年 11 月上旬）", disproof="毛利率跌破 40.2%",
        expiry="2027-02-28T00:00:00+00:00", coverage_created_at="2026-08-31 11:30:25",
        variant_perception=None,
    )
    base.update(overrides)
    return DecisionFacts(**base)


def _view(*, with_signal: bool = True, fundamentals: _FakeFundamentals | None = None,
          facts: DecisionFacts | None = None, judgment: dict[str, Any] | None = None,
          identity: dict[str, Any] | None = None, **kwargs: Any) -> AlphaInvestmentView:
    build = _build(fundamentals)
    signal = compose_signal(build, judgment or _judgment()) if with_signal else None
    return build_alpha_investment_view(
        build=build, signal=signal,
        signal_reason=None if with_signal else "測試：刻意不給判斷",
        dependency_paths=FakeGraphResearchProvider(company_id=COMPANY).get_dependency_paths(COMPANY),
        estimate_revision=(fundamentals or _FakeFundamentals()).estimate_revision(TICKER),
        decision_facts=facts if facts is not None else _facts(),
        catalyst_checkpoints=[{"date": date(2026, 12, 1), "what": "六吋 InP 產能倍增檢核點",
                               "decides": "產能倍增是否如期", "date_confidence": "estimated"}],
        checkpoint_source="thesis://lifecycle.json",
        thesis_lifecycle={"status": "active", "ticker": "COHR", "next_check": "2026-10-15",
                          "last_checked": "2026-07-17"},
        identity=identity or {"market_currency": "USD", "market_quote_unit": "USD",
                              "execution_venue": "NYSE"},
        today=TODAY, **kwargs,
    )


def _walk(node: Any, path: str = ""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield f"{path}.{key}".lstrip("."), key, value
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


# ---------------------------------------------------------------------------
# Missing != Zero
# ---------------------------------------------------------------------------

def test_missing_internal_eps_is_not_serialized_as_zero() -> None:
    """internal EPS 今天不存在——它必須是 `not_modeled` ＋ `null`，不是 0。"""
    view = _view()
    section = view.internal_fundamentals
    assert section.meta.status == "not_modeled"
    eps = next(d for d in section.items if d.key == "internal_eps")
    assert eps.status == "not_modeled" and eps.value is None
    payload = json.loads(json.dumps(view.to_dict(), ensure_ascii=False))
    serialized = next(d for d in payload["internal_fundamentals"]["items"] if d["key"] == "internal_eps")
    assert serialized["value"] is None
    assert serialized["status"] == "not_modeled"


def test_missing_implied_margin_is_not_zero_percent() -> None:
    view = _view()
    margin = next(d for d in view.price_implied_expectations.items if d.key == "market_implied_margin")
    assert margin.status == "not_modeled"
    assert margin.value is None
    assert margin.basis == "none"


def test_datum_contract_enforces_missing_is_not_zero() -> None:
    """型別層就擋：沒有值的狀態不得帶值；有值的狀態不得是 None。"""
    with pytest.raises(ViewContractViolation, match="missing != zero"):
        Datum(key="x", label="x", value=0, status="missing")
    with pytest.raises(ViewContractViolation, match="missing != zero"):
        Datum(key="x", label="x", value=0.0, status="not_modeled")
    with pytest.raises(ViewContractViolation, match="沒有值就要說沒有"):
        Datum(key="x", label="x", value=None, status="available", basis="observation")
    with pytest.raises(ViewContractViolation, match="沒有值"):
        Datum(key="x", label="x", value=None, status="missing", basis="deterministic")
    # 合法：False／0.0 都是值，不是缺席
    assert Datum(key="x", label="x", value=False, status="available", basis="observation").is_known
    assert Datum(key="x", label="x", value=0.0, status="available", basis="observation").is_known


def test_unknown_session_axis_is_missing_not_zero() -> None:
    """session 回答 unknown 的 Q3／Q5：status=missing、value=None、reason 說「不是 0」。"""
    view = _view()
    q3 = next(d for d in view.variant_view.scores if d.key == "earnings_exposure_score")
    q5 = view.catalysts.catalyst_score
    for datum in (q3, q5):
        assert datum.status == "missing" and datum.value is None
        assert "不是 0" in (datum.reason or "")


# ---------------------------------------------------------------------------
# 分析師目標價 ≠ 預期報酬
# ---------------------------------------------------------------------------

def test_analyst_target_is_not_expected_return() -> None:
    view = _view()
    assert view.expected_return.meta.status == "not_modeled"
    assert all(d.value is None and d.status == "not_modeled" for d in view.expected_return.items)
    assert any("賣方目標價" in x for x in view.expected_return.not_to_be_confused_with)
    target = next(d for d in view.consensus.items if d.key == "target_mean")
    assert target.is_known and "不是本系統的預期報酬" in target.label
    # view 不自己算目標價 vs 現價的比值：那是 scripts/alpha_expectation_gap.py 的產出（審計第 5 條）
    assert not any(d.key == "target_vs_price" for d in view.consensus.items)
    payload = view.to_dict()["expected_return"]
    numeric = [(p, v) for p, k, v in _walk(payload) if isinstance(v, (int, float)) and not isinstance(v, bool)]
    assert not numeric, f"expected_return 出現數值：{numeric}"


# ---------------------------------------------------------------------------
# Price-implied 是 proxy，不是 model
# ---------------------------------------------------------------------------

def test_price_implied_growth_is_marked_heuristic_proxy() -> None:
    view = _view()
    growth = next(d for d in view.price_implied_expectations.items if d.key == "market_implied_eps_growth")
    assert growth.is_known
    assert growth.basis == "heuristic_proxy"
    assert "trailing_pe/forward_pe" in (growth.method or "")
    assert view.price_implied_expectations.meta.basis == "heuristic_proxy"
    assert view.price_implied_expectations.reverse_dcf.status == "not_modeled"
    assert view.price_implied_expectations.meta.status == "partial"


def test_nonpositive_forward_pe_yields_not_applicable_not_a_negative_growth() -> None:
    """forward PE 為負 ＝ 分析師預估仍虧損；比值無意義，不得印成 −240%。"""
    view = _view(fundamentals=_FakeFundamentals(forward_pe=-43.1, trailing_pe=60.0))
    growth = next(d for d in view.price_implied_expectations.items if d.key == "market_implied_eps_growth")
    assert growth.value is None
    assert growth.status == "not_applicable"
    assert "nonpositive" in (growth.reason or "")


def test_loss_making_company_has_missing_implied_growth_with_reason() -> None:
    view = _view(fundamentals=_FakeFundamentals(trailing_pe=None))
    growth = next(d for d in view.price_implied_expectations.items if d.key == "market_implied_eps_growth")
    assert growth.value is None and growth.status == "missing"
    assert "pe_trailing_missing" in (growth.reason or "")


# ---------------------------------------------------------------------------
# 情境是散文；因果是結構不是財務
# ---------------------------------------------------------------------------

def test_scenarios_are_narrative_not_quantitative() -> None:
    view = _view()
    assert view.scenarios.scenario_type == CAP_NARRATIVE_SCENARIOS
    assert view.scenarios.meta.basis == "narrative"
    assert view.scenarios.meta.capability == CAP_NARRATIVE_SCENARIOS
    assert view.scenarios.bull.basis == "narrative"
    assert view.scenarios.probabilities.status == "not_modeled"
    assert view.scenarios.target_valuation.status == "not_modeled"


def test_causal_section_is_structural_not_financial() -> None:
    view = _view()
    assert view.causal_paths.meta.capability == CAP_STRUCTURAL_CAUSAL
    assert view.causal_paths.meta.capability != CAP_FINANCIAL_CAUSAL
    assert view.causal_paths.meta.basis == "structural_inference"
    assert view.causal_paths.financial_causal_model.status == "not_modeled"
    assert any("不是 financial causal model" in w for w in view.causal_paths.meta.warnings)
    assert view.earnings_bridge.meta.status == "not_modeled"
    assert all(d.value is None for d in view.earnings_bridge.steps)


# ---------------------------------------------------------------------------
# Q1 deterministic、Q2–Q5 session；沒有判斷時 Q1 仍在
# ---------------------------------------------------------------------------

def test_q1_is_deterministic_and_session_axes_are_session_judgment() -> None:
    view = _view()
    scores = {d.key: d for d in view.variant_view.scores}
    assert scores["structural_score"].basis == "deterministic"
    assert scores["structural_score"].authority == "alpha://context/structural_score"
    assert scores["value_capture_score"].basis == "session_judgment"
    assert scores["expectation_gap_score"].basis == "session_judgment"
    assert scores["value_capture_score"].value["session_level"] == "strong"
    assert not any(d.basis == "deterministic" for k, d in scores.items() if k != "structural_score")
    assert view.variant_view.meta.basis == "session_judgment"
    assert view.variant_view.thesis.basis == "session_judgment"
    assert view.expectation_gap.session_judgment.basis == "session_judgment"


def test_no_signal_leaves_variant_view_missing_but_q1_available() -> None:
    view = _view(with_signal=False)
    assert view.variant_view.meta.status == "missing"
    assert view.variant_view.thesis.status == "missing"
    assert "刻意不給判斷" in (view.variant_view.meta.reason or "")
    scores = {d.key: d for d in view.variant_view.scores}
    assert scores["structural_score"].is_known                      # Q1 不依賴 session
    assert all(not scores[k].is_known for k in scores if k != "structural_score")
    assert view.identity.signal.has_signal is False
    assert view.scenarios.meta.status == "missing"
    assert any("尚無 session 判斷" in w for w in view.warnings)


# ---------------------------------------------------------------------------
# 舊判斷要現形成 stale，不得藏、也不得冒充新的
# ---------------------------------------------------------------------------

def test_stale_judgment_is_flagged_not_hidden() -> None:
    build = _build()
    stale_judgment = _judgment(_packet_digest="sha256:0000000000deadbeef")
    with pytest.raises(ContractViolation, match="判斷需要重做"):
        compose_signal(build, stale_judgment)                     # 預設仍嚴格
    signal = compose_signal(build, stale_judgment, allow_stale_context=True)
    assert signal.metadata["context_mismatch"]["judged_context_digest"] == "sha256:0000000000deadbeef"
    view = build_alpha_investment_view(build=build, signal=signal, today=TODAY)
    assert view.variant_view.meta.status == "stale"
    assert view.identity.signal.context_matches is False
    assert view.identity.signal.judged_at == "2026-09-04"
    assert view.variant_view.thesis.status == "stale" and view.variant_view.thesis.is_known
    session_freshness = next(f for f in view.freshness if f.source == "session_judgment")
    assert session_freshness.status == "stale" and session_freshness.as_of == date(2026, 9, 4)
    assert any("過期" in w for w in view.warnings)


def test_fresh_judgment_matches_context() -> None:
    view = _view()
    assert view.identity.signal.context_matches is True
    assert view.variant_view.meta.status == "available"


# ---------------------------------------------------------------------------
# Alpha ≠ Position：view 不得長出部位欄位
# ---------------------------------------------------------------------------

def test_view_contains_no_position_fields() -> None:
    view = _view()
    banned = set(FORBIDDEN_POSITION_TOKENS) | {"target_weight", "supported_range", "nav_pct", "held"}
    offenders = []
    for path, key, _value in _walk(view.to_dict()):
        parts = set(str(key).lower().split("_"))
        if parts & banned:
            offenders.append(path)
    assert not offenders, f"read model 出現部位欄位：{offenders}"
    entry = view.entry_logic
    assert entry.meta.status == "not_modeled"
    assert all(d.value is None for d in entry.items)
    assert view.downside.meta.status == "not_modeled"


def test_authorities_are_logical_uris_not_private_paths() -> None:
    view = _view()
    for path, key, value in _walk(view.to_dict()):
        if key == "authority" and isinstance(value, str):
            assert "\\" not in value and "library" not in value, path
            assert "://" in value, path
    with pytest.raises(ViewContractViolation, match="檔案路徑"):
        Datum(key="x", label="x", value=1, status="available", basis="observation",
              authority="C:/Users/x/library/private/engine_c/db.sqlite")


# ---------------------------------------------------------------------------
# 覆蓋只到哪裡就說到哪裡：consensus partial、catalyst partial、falsification 不 overclaim
# ---------------------------------------------------------------------------

def test_consensus_is_partial_and_says_what_is_missing() -> None:
    view = _view()
    assert view.consensus.meta.status == "partial"
    assert "multi-year" in view.consensus.coverage_note
    assert any("multi-year consensus earnings model" in w for w in view.consensus.meta.warnings)
    growth = next(d for d in view.consensus.items if d.key == "revenue_estimate_next_fy_growth")
    assert "不得相減" in (growth.method or "")


def test_missing_snapshot_makes_sections_missing_not_not_modeled() -> None:
    """有能力、這檔沒資料＝missing；系統沒能力＝not_modeled。兩者不得共用一個值。"""
    view = _view(fundamentals=_FakeFundamentals(available=False))
    assert view.fundamentals.meta.status == "missing"
    assert view.consensus.meta.status == "missing"
    assert view.internal_fundamentals.meta.status == "not_modeled"
    price = next(d for d in view.fundamentals.items if d.key == "price")
    assert price.value is None and price.status == "missing"
    cap = view.capability_map()
    assert cap["fundamentals"]["status"] == "missing"
    assert cap["internal_fundamentals"]["status"] == "not_modeled"


def test_catalyst_capability_is_partial_and_reuses_shared_state() -> None:
    view = _view()
    section = view.catalysts
    assert section.meta.status == "partial"
    assert section.meta.capability == "structured_dates_without_repricing_link"
    assert section.quantitative_link.status == "not_modeled"
    assert section.narrative.basis == "narrative"
    assert section.watch_state.is_known
    assert section.watch_state.value["state"] == "watch"                    # 2027-02-28 尚未到期
    assert section.watch_state.authority == "shared://catalyst_state.assess_entry"
    assert section.checkpoints[0].date_confidence == "estimated"
    assert section.checkpoints[0].source == "thesis://lifecycle.json"


def test_catalyst_config_problems_surface_not_vanish() -> None:
    view = _view(facts=_facts(catalyst="", disproof=""))
    assert view.catalysts.watch_state.value["state"] == "config_broken"
    assert view.catalysts.problems
    assert any("設定不完整" in w for w in view.warnings)
    assert view.catalysts.narrative.status == "missing"
    assert "L7" in (view.falsification.narrative_disproof.reason or "")


def test_falsification_keeps_l7_triplet_and_does_not_claim_auto_invalidation() -> None:
    view = _view()
    section = view.falsification
    assert section.conditions and section.conditions[0].check_frequency == "quarterly"
    assert section.conditions[0].action_within_48h == "強制 review"
    assert section.conditions[0].basis == "session_judgment"
    assert section.meta.capability == "structured_conditions_with_expiry_watch"
    assert section.automatic_invalidation.status == "not_modeled"
    assert section.thesis_status.value["status"] == "active"


# ---------------------------------------------------------------------------
# 序列化、能力地圖、精簡卡、identity 警告
# ---------------------------------------------------------------------------

def test_to_dict_round_trips_json_and_keeps_nulls() -> None:
    view = _view()
    payload = view.to_dict()
    text = json.dumps(payload, ensure_ascii=False)
    back = json.loads(text)
    assert back["schema_version"] == "alpha-investment-view/v1"
    assert back["identity"]["ticker"] == "COHR"
    assert back["capability_map"]["expected_return"]["status"] == "not_modeled"
    nulls = [p for p, k, v in _walk(back) if k == "value" and v is None]
    assert nulls, "read model 裡沒有任何 null——代表缺席被填掉了"


def test_capability_map_lists_every_section_with_status_and_basis() -> None:
    view = _view()
    cap = view.capability_map()
    assert set(cap) == set(AlphaInvestmentView.SECTIONS_WITH_META)
    for name, info in cap.items():
        assert info["status"] and info["basis"], name
        if info["status"] in VALUELESS_STATUSES:
            assert info["basis"] == "none", name


def test_compact_card_is_pure_selection_from_the_view() -> None:
    view = _view()
    card = compact_card(view)
    assert card["ticker"] == "COHR"
    assert card["scores"]["structural"]["basis"] == "deterministic"
    assert card["scores"]["value_capture"]["session_level"] == "strong"
    assert card["scores"]["earnings_exposure"]["status"] == "missing"
    assert card["scores"]["earnings_exposure"]["effective"] is None
    growth = next(d for d in view.price_implied_expectations.items if d.key == "market_implied_eps_growth")
    assert card["market_implied_eps_growth"]["value"] == growth.value
    assert card["market_implied_eps_growth"]["basis"] == "heuristic_proxy"
    assert card["catalyst"]["state"] == "watch"
    assert set(card["not_modeled"]) >= {"internal_fundamentals", "earnings_bridge",
                                        "expected_return", "downside", "entry_logic"}
    banned = set(FORBIDDEN_POSITION_TOKENS)
    assert not any(set(str(k).lower().split("_")) & banned for _p, k, _v in _walk(card))


def test_compact_card_keeps_unknowns_as_none_with_reason() -> None:
    card = compact_card(_view(fundamentals=_FakeFundamentals(trailing_pe=None)))
    assert card["market_implied_eps_growth"]["value"] is None
    assert "pe_trailing_missing" in card["market_implied_eps_growth"]["reason"]


def test_quote_unit_mismatch_is_warned_in_identity() -> None:
    view = _view(identity={"market_currency": "GBP", "market_quote_unit": "GBp",
                           "execution_venue": "LSE"})
    assert any("100 倍" in w for w in view.identity.warnings)
    assert any("100 倍" in w for w in view.warnings)


def test_evidence_index_carries_three_time_fields_and_selection_counts() -> None:
    view = _view()
    item = next(i for i in view.evidence.index if i.ref == "engine_c://financial_snapshot/COHR")
    assert item.published_at == date(2026, 9, 4)
    assert item.retrieved_at == date(2026, 9, 5)
    assert view.evidence.selection.input_count == view.evidence.selection.accepted_count
    assert view.evidence.quality.basis == "deterministic"


def test_fixed_warnings_are_always_present() -> None:
    """相關性提醒與「研究判斷非回測」每次都講，不因每次一樣而省略（AGENTS Alpha 呈現契約）。"""
    for view in (_view(), _view(with_signal=False)):
        assert any("同一賭注" in w for w in view.warnings)
        assert any("不是回測" in w for w in view.warnings)


# ---------------------------------------------------------------------------
# 審計修正（2026-09-05）：as-of 拒答、basis 重貼標、精簡卡零值、上游壓平標註
# ---------------------------------------------------------------------------

def _as_of_build(as_of: date):
    from alpha.testing import as_of_capable

    provider = as_of_capable(FakeGraphResearchProvider(
        company_id=COMPANY, evidence_pool=(_CORROBORATED, _SELF_REPORTED)))
    return build_research_context(ticker=TICKER, company_id=COMPANY, graph_provider=provider,
                                  fundamentals_provider=_FakeFundamentals(), as_of=as_of)


def test_as_of_mode_refuses_sources_without_point_in_time_projection() -> None:
    """INV-6：Decision Store／thesis 檔沒有時點投影，as-of 視角下必須 `not_applicable`，
    **即使呼叫端不小心把當前值傳進來**（builder 自己擋，不靠 sources 記得）。"""
    build = _as_of_build(date(2026, 6, 30))
    view = build_alpha_investment_view(
        build=build, decision_facts=_facts(),                       # 故意傳當前值
        catalyst_checkpoints=[{"date": date(2026, 12, 1), "what": "x", "decides": "",
                               "date_confidence": "estimated"}],   # 故意傳當前檢核點
        thesis_lifecycle={"status": "active", "ticker": "COHR", "next_check": "2026-10-15"},
        today=TODAY,
    )
    assert view.identity.point_in_time_mode == "as_of"
    for datum in (view.catalysts.narrative, view.catalysts.watch_state, view.catalysts.expiry,
                  view.falsification.narrative_disproof, view.falsification.thesis_status,
                  view.variant_view.decision_store_variant_perception):
        assert datum.status == "not_applicable", datum.key
        assert datum.value is None
        assert "INV-6" in (datum.reason or ""), datum.key
    assert view.catalysts.checkpoints == ()
    assert view.identity.lifecycle.research_status is None
    assert "INV-6" in (view.identity.lifecycle.reason or "")
    assert any("as-of 視角" in w for w in view.warnings)
    # Engine A／C 的切片仍然是 T 時刻的：evidence index 裡沒有晚於 as_of 的引用
    assert all(i.published_at is None or i.published_at <= date(2026, 6, 30)
               for i in view.evidence.index)
    card = compact_card(view)
    assert card["catalyst"]["checkpoint_count"] is None and card["point_in_time_mode"] == "as_of"


def test_current_mode_keeps_decision_facts() -> None:
    """對照組：當前視角下 Decision Store 事實正常呈現（確認上一條不是把功能拿掉）。"""
    view = _view()
    assert view.identity.point_in_time_mode == "current"
    assert view.catalysts.watch_state.is_known
    assert view.falsification.narrative_disproof.is_known


def test_compact_card_counts_are_none_not_zero_without_a_signal() -> None:
    """精簡卡的 JSON 也要守 Missing != Zero：沒有 session 判斷時條數是不知道，不是 0。"""
    card = compact_card(_view(with_signal=False))
    assert card["disproof"]["condition_count"] is None
    assert card["catalyst"]["structured_count"] is None
    assert card["signal"]["has_signal"] is False
    with_signal = compact_card(_view())
    assert with_signal["disproof"]["condition_count"] == 1
    assert with_signal["catalyst"]["structured_count"] == 0     # 有判斷、判斷裡沒有催化劑＝知道是 0


def test_human_entered_checkpoints_are_observation_not_deterministic() -> None:
    """thesis JSON 裡人手填的檢核點與 status 是 observation；deterministic 的只有 assess_entry。"""
    view = _view(with_signal=False)
    assert view.catalysts.checkpoints                              # 只有檢核點、沒有 session 催化劑
    assert view.catalysts.meta.basis == "observation"
    assert view.catalysts.watch_state.basis == "deterministic"
    assert view.falsification.thesis_status.basis == "observation"
    assert "lifecycle_schedule" in (view.falsification.thesis_status.method or "")


def test_as_of_mode_accepts_decision_facts_that_carry_a_matching_as_of_marker() -> None:
    """Decision Store 有時間戳，`company_decision_facts(as_of=…)` 做過歷史過濾的事實**可以**進
    歷史卡；到期狀態以 as_of 當今天判定，不用真實今天。"""
    as_of = date(2026, 8, 15)
    build = _as_of_build(as_of)
    facts = _facts(point_in_time_mode="as_of", point_in_time_as_of="2026-08-15",
                   coverage_created_at="2026-08-15 03:06:02", expiry="2026-11-30T00:00:00+00:00")
    view = build_alpha_investment_view(build=build, decision_facts=facts, today=TODAY)
    assert view.catalysts.narrative.is_known
    watch = view.catalysts.watch_state
    assert watch.is_known and watch.as_of == as_of
    assert watch.value["days_to_expiry"] == (date(2026, 11, 30) - as_of).days   # 以 as_of 為今天
    assert "as-of 模式以 2026-08-15 為今天" in (watch.method or "")
    assert view.identity.lifecycle.decision_facts_as_of == "2026-08-15"
    # thesis 檔仍然沒有歷史 → 仍是 not_applicable
    assert view.falsification.thesis_status.status == "not_applicable"
    coverage_fresh = next(f for f in view.freshness if f.source == "decision_store_coverage")
    assert coverage_fresh.age_days == 0.0 and "as-of" in (coverage_fresh.reason or "")


def test_as_of_mode_reports_missing_when_authority_answers_none_as_of_t() -> None:
    """authority 回答「T 時刻沒有 cohort」是 missing（有能力、當時沒資料），不是 not_applicable。"""
    build = _as_of_build(date(2026, 6, 30))
    view = build_alpha_investment_view(
        build=build, decision_facts=None,
        decision_facts_reason="截至 as-of 2026-06-30，Engine D 尚無此公司的 cohort（歷史過濾後為空）",
        today=TODAY,
    )
    assert view.catalysts.narrative.status == "missing"
    assert "尚無" in (view.catalysts.narrative.reason or "")
    assert view.falsification.thesis_status.status == "not_applicable"      # thesis 檔無歷史


def test_compact_card_serializes_unknown_counts_as_json_null() -> None:
    payload = json.loads(json.dumps(compact_card(_view(with_signal=False)), ensure_ascii=False))
    assert payload["disproof"]["condition_count"] is None
    assert payload["catalyst"]["structured_count"] is None
    text = json.dumps(payload, ensure_ascii=False)
    assert '"condition_count": null' in text and '"condition_count": 0' not in text


def test_lifecycle_facts_have_no_permanently_empty_attention_field() -> None:
    from briefing.alpha_view.contracts import LifecycleFacts

    assert "attention" not in {f.name for f in LifecycleFacts.__dataclass_fields__.values()}


def test_as_of_mode_refuses_a_session_judgment_written_after_the_cutoff() -> None:
    """09-04 寫的判斷不得出現在 08-15 的歷史卡上：那是 T 之後的知識（lookahead），
    就算標 stale 也不行——builder 直接拒用並說明，Q2–Q5 與 thesis 全部 not_applicable。"""
    as_of = date(2026, 8, 15)
    build = _as_of_build(as_of)
    signal = compose_signal(build, _judgment())                       # _produced_at = 2026-09-04
    view = build_alpha_investment_view(build=build, signal=signal, today=TODAY)
    assert view.identity.signal.has_signal is False
    assert "lookahead" in (view.identity.signal.reason or "")
    assert view.variant_view.meta.status == "not_applicable"
    assert view.variant_view.thesis.status == "not_applicable"
    scores = {d.key: d for d in view.variant_view.scores}
    assert scores["structural_score"].is_known                        # Q1 是 T 時刻圖投影算的
    assert all(scores[k].status == "not_applicable" for k in scores if k != "structural_score")
    assert view.scenarios.meta.status == "not_applicable"
    assert view.catalysts.meta.as_of == as_of
    # 對照：判斷日期早於或等於 as_of 就可以用（只是照舊會因 digest 不同標 stale）
    early = compose_signal(build, _judgment(_produced_at="2026-08-01"), allow_stale_context=True)
    view_ok = build_alpha_investment_view(build=build, signal=early, today=TODAY)
    assert view_ok.identity.signal.has_signal is True
    assert view_ok.identity.signal.judged_at == "2026-08-01"
