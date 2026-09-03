"""`GraphResearchProvider` 的契約測試。

跑在 `FakeGraphResearchProvider` 上；Phase 2 的 concrete provider 必須通過**同一組**
斷言（屆時把 fixture 換掉即可）。這樣「不用寫 Cypher」與「不用知道證據來自哪」
不會被混為一談。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.causal import CausalPath, CompanyImpact, StructuralEvent
from alpha.contracts import EvidenceRef, ScarcityInputs, StructuralContext
from alpha.errors import ContractViolation
from alpha.identity import CompanyId, EntityId
from alpha.provider import (
    AS_OF_METHODS, PROVIDER_METHODS, BottleneckRow, GraphResearchProvider, SupplyExposure,
)
from alpha.testing import FakeGraphResearchProvider, evidence

COMPANY = CompanyId("co:coherent")


@pytest.fixture()
def provider() -> FakeGraphResearchProvider:
    return FakeGraphResearchProvider()


def test_fake_satisfies_the_protocol(provider: FakeGraphResearchProvider) -> None:
    assert isinstance(provider, GraphResearchProvider)


def test_every_declared_method_exists(provider: FakeGraphResearchProvider) -> None:
    """`PROVIDER_METHODS` 是契約清單——加方法卻忘了列進去會被抓到。"""
    for name in PROVIDER_METHODS:
        assert callable(getattr(provider, name)), name
    assert set(AS_OF_METHODS) <= set(PROVIDER_METHODS)


# ---------------------------------------------------------------------------
# provenance 不得被隱藏
# ---------------------------------------------------------------------------

def _all_calls(p: FakeGraphResearchProvider):
    event = p.get_structural_changes_since(date(2026, 1, 1))[0]
    return {
        "get_company_structural_context": p.get_company_structural_context(COMPANY),
        "get_bottlenecks": p.get_bottlenecks(),
        "get_dependency_paths": p.get_dependency_paths(COMPANY),
        "get_substitution_paths": p.get_substitution_paths(COMPANY),
        "get_supply_exposure": p.get_supply_exposure(COMPANY, direction="upstream"),
        "get_second_order_beneficiaries": p.get_second_order_beneficiaries(event),
        "get_second_order_victims": p.get_second_order_victims(event),
        "get_claim_evidence": p.get_claim_evidence("claim:x"),
        "get_structural_changes_since": (event,),
    }


def test_every_method_returns_evidence(provider: FakeGraphResearchProvider) -> None:
    """provider 的價值是「不用寫 Cypher」，**不是**「不用知道證據來自哪」。"""
    results = _all_calls(provider)
    assert set(results) == set(PROVIDER_METHODS)
    for name, value in results.items():
        items = value if isinstance(value, (list, tuple)) else [value]
        assert items, f"{name} 回傳空集合"
        for item in items:
            if isinstance(item, EvidenceRef):
                continue
            refs = getattr(item, "evidence", None)
            if refs is None:                       # CompanyImpact 的證據掛在 path 上
                refs = getattr(getattr(item, "path", None), "evidence", ())
            assert refs, f"{name} 的回傳物件沒有 evidence：{type(item).__name__}"


def test_evidence_requirement_is_not_vacuous() -> None:
    """把 evidence 拿掉，型別本身就會拒絕——不是靠測試事後發現。"""
    with pytest.raises(ContractViolation, match="evidence"):
        BottleneckRow(
            company_id=COMPANY, edge_key="edge:x", relation="supplies_to",
            target_id=EntityId("co:nvidia"),
            inputs=ScarcityInputs(),
            demand_anchor=None, evidence=(),
        )
    with pytest.raises(ContractViolation, match="evidence"):
        SupplyExposure(company_id=COMPANY, direction="upstream",
                       counterparty_id=EntityId("mat:inp_substrate"),
                       relation="depends_on", evidence=())


# ---------------------------------------------------------------------------
# provider 不做判斷，只給結構事實
# ---------------------------------------------------------------------------

def test_bottleneck_row_carries_structural_inputs_not_a_verdict(
    provider: FakeGraphResearchProvider,
) -> None:
    """「這算不算瓶頸」是 `alpha/scarcity.py` 的事，不是 provider 的事。"""
    row = provider.get_bottlenecks()[0]
    assert row.inputs.substitutability == 5
    assert row.inputs.sole_source is True
    # provider 不得回傳分數／排名／建議
    for banned in ("score", "rank", "recommendation", "verdict"):
        assert not hasattr(row, banned)


def test_structural_context_shape(provider: FakeGraphResearchProvider) -> None:
    context = provider.get_company_structural_context(COMPANY)
    assert isinstance(context, StructuralContext)
    assert context.company_id == COMPANY
    assert context.counter_paths, "反證路徑是 coverage gate 的必要輸入，不得為空"


def test_second_order_impacts_are_derived_and_pathed(
    provider: FakeGraphResearchProvider,
) -> None:
    event = provider.get_structural_changes_since(date(2026, 1, 1))[0]
    for impact in (*provider.get_second_order_beneficiaries(event),
                   *provider.get_second_order_victims(event)):
        assert isinstance(impact, CompanyImpact)
        assert impact.derived is True          # 推論永遠不入圖
        assert isinstance(impact.path, CausalPath)
        assert impact.path.hops >= 1


def test_structural_event_requires_evidence() -> None:
    """結構事件是 claim，不是感覺。"""
    with pytest.raises(ContractViolation, match="evidence"):
        StructuralEvent(
            event_id="e", kind="capacity_constraint",
            subject_id=EntityId("mat:inp_substrate"), direction="tightening",
            observed_at=date(2026, 1, 1), evidence=(),
        )
