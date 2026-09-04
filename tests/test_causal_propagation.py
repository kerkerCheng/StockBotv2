"""Phase 5：多跳因果傳播。

驗收條件（ROADMAP）：對 ≥1 個真實事件產出 ≥1 個二階受益／受害者，
路徑可追溯到 `EvidenceRef`。

實跑（2026-09-04，36 條真實排序列）：
  mat:inp_substrate tightening → co:nvidia VICTIM
    路徑 mat:inp_substrate → co:coherent → co:nvidia [constrains｜supplies_to]
  co:coherent      tightening → co:lumentum／co:broadcom BENEFICIARY
    路徑 co:coherent → tech:external_laser_source → co:lumentum [supplies_to｜also_supplied_by]

本檔用注入的排序列測，不連 Neo4j。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.causal import (
    ImpactDirection, ImpactMagnitude, StructuralEvent, TimeHorizon,
)
from alpha.contracts import EvidenceRef
from alpha.identity import EntityId
from alpha.providers.graph_neo4j import Neo4jGraphResearchProvider

_EVIDENCE = (EvidenceRef(ref="graph://edge/test", kind="graph_edge"),)


def _rows(*extra):
    """一條 InP → Coherent → NVIDIA 的鏈，外加呼叫端追加的列。"""
    base = [
        {"company_id": "co:coherent", "relation": "depends_on",
         "bottleneck": "mat:inp_substrate", "substitutability": 5,
         "confidence": 0.9, "evidence": "externally_corroborated",
         "sources": ["sd_1"], "ticker": "COHR", "lead_time_weeks": None},
        {"company_id": "co:coherent", "relation": "supplies_to",
         "bottleneck": "co:nvidia", "substitutability": 5,
         "confidence": 0.9, "evidence": "externally_corroborated",
         "sources": ["sd_2"], "ticker": "COHR", "lead_time_weeks": None},
    ]
    return base + list(extra)


def _provider(rows):
    return Neo4jGraphResearchProvider(driver=None, _ranked={"rows": rows})


def _event(subject: str, direction: str = "tightening") -> StructuralEvent:
    return StructuralEvent(
        event_id=f"se_{subject}", kind="supply_disruption",
        subject_id=EntityId(subject), direction=direction,
        observed_at=date(2026, 9, 4), description="測試事件", evidence=_EVIDENCE,
    )


# ---------------------------------------------------------------------------
# 驗收條件本身
# ---------------------------------------------------------------------------

def test_a_supply_disruption_reaches_a_second_order_victim_with_evidence() -> None:
    """ROADMAP 的 exit criterion：≥1 個二階受害者，且路徑追溯得到 EvidenceRef。"""
    victims = _provider(_rows()).get_second_order_victims(_event("mat:inp_substrate"))

    assert len(victims) == 1
    impact = victims[0]
    assert str(impact.company_id) == "co:nvidia"
    assert impact.path.nodes == ("mat:inp_substrate", "co:coherent", "co:nvidia")
    assert impact.path.hops == 2
    assert impact.path.evidence, "路徑必須帶得回 EvidenceRef，否則無法稽核"
    assert impact.derived is True


def test_impacts_are_always_derived_and_never_graph_facts() -> None:
    """多跳推論不得被誤讀成圖上的事實——契約層已擋，這裡確認傳播沒繞過它。"""
    for impact in _provider(_rows()).propagate(_event("mat:inp_substrate")):
        assert impact.derived is True
        assert "推論" in impact.rationale


# ---------------------------------------------------------------------------
# 方向：這是實跑時真的印錯過的一條
# ---------------------------------------------------------------------------

def test_path_relations_read_in_the_direction_of_travel() -> None:
    """⚠ 圖上的邊有自己的方向，而衝擊是**逆著依賴走**的。

    事發（2026-09-04 首次實跑）：路徑印出
    `mat:inp_substrate -depends_on-> co:coherent`——**方向剛好講反**
    （真實的邊是 `co:coherent depends_on mat:inp_substrate`）。讀的人會以為
    substrate 依賴 coherent。逆走的邊因此改用衍生標籤 `constrains`。
    """
    impact = _provider(_rows()).get_second_order_victims(_event("mat:inp_substrate"))[0]

    assert impact.path.relations == ("constrains", "supplies_to")
    assert "depends_on" not in impact.path.relations, (
        "逆走的邊不得沿用原標籤——那會把因果方向講反"
    )


def test_loosening_flips_every_direction() -> None:
    """同一條路徑，事件方向反過來，影響方向就整組反過來。"""
    rows = _rows()
    tightening = _provider(rows).propagate(_event("mat:inp_substrate", "tightening"))
    loosening = _provider(rows).propagate(_event("mat:inp_substrate", "loosening"))

    assert {i.direction for i in tightening} == {ImpactDirection.VICTIM}
    assert {i.direction for i in loosening} == {ImpactDirection.BENEFICIARY}


def test_a_substitute_benefits_when_the_subject_tightens() -> None:
    """替代鏈：供同一個 chokepoint 的**其他**公司在 subject 收緊時受惠。"""
    rows = _rows({
        "company_id": "co:lumentum", "relation": "supplies_to",
        "bottleneck": "co:nvidia", "substitutability": 5, "confidence": 0.9,
        "evidence": "externally_corroborated", "sources": ["sd_3"],
        "ticker": "LITE", "lead_time_weeks": None,
    })
    beneficiaries = _provider(rows).get_second_order_beneficiaries(_event("co:coherent"))

    assert [str(i.company_id) for i in beneficiaries] == ["co:lumentum"]
    assert beneficiaries[0].path.relations == ("supplies_to", "also_supplied_by")


# ---------------------------------------------------------------------------
# 不得 overclaim
# ---------------------------------------------------------------------------

def test_first_order_relations_are_not_returned() -> None:
    """**二階＝至少 2 跳。** 1 跳是圖上直接看得到的關係，不需要推論。

    co:coherent 直接 depends_on inp_substrate，所以它不該出現在二階清單裡；
    出現了就代表這一層在重複圖已經說過的話。
    """
    impacts = _provider(_rows()).propagate(_event("mat:inp_substrate"))

    assert all(i.path.hops >= 2 for i in impacts)
    assert "co:coherent" not in {str(i.company_id) for i in impacts}


def test_second_order_magnitude_never_claims_high() -> None:
    """二階最高只給 MEDIUM——它是推論不是觀測，給 HIGH 是 overclaim。"""
    impacts = _provider(_rows()).propagate(_event("mat:inp_substrate"))

    assert impacts
    assert all(i.magnitude is not ImpactMagnitude.HIGH for i in impacts)
    assert impacts[0].magnitude is ImpactMagnitude.MEDIUM


def test_substitutability_is_not_clamped_to_the_confidence_range() -> None:
    """⚠ `_finite` 把值夾在 0..1，它是 `confidence` 專用的。

    事發（2026-09-04 首次實跑）：magnitude 用 `_finite` 讀 `substitutability`(1–5)，
    於是**每一筆都回 None** → 所有 magnitude 都變 UNKNOWN。看起來像「資料不足」，
    實際上資料好好地在那裡。這條把 sub=5 必須讀得到釘住。
    """
    from alpha.providers.graph_neo4j import _finite, _number

    assert _finite(5) is None, "_finite 夾 0..1 是它的正確行為"
    assert _number(5) == 5.0, "_number 不夾範圍，供 substitutability／lead_time 用"

    impact = _provider(_rows()).propagate(_event("mat:inp_substrate"))[0]
    assert impact.magnitude is not ImpactMagnitude.UNKNOWN


def test_time_horizon_stays_unknown_when_the_graph_has_no_lead_time() -> None:
    """圖上沒有 `lead_time_weeks` 就回 UNKNOWN——**不套「供應鏈大概一季」的預設值**。

    編出來的時間會被下游當成可以排程的東西。
    """
    impact = _provider(_rows()).propagate(_event("mat:inp_substrate"))[0]
    assert impact.time_horizon is TimeHorizon.UNKNOWN


def test_time_horizon_comes_from_the_graph_when_it_is_there() -> None:
    """反向確認：圖上有 lead time 時要真的用它，否則上一條也會恆真。"""
    rows = _rows()
    rows[0] = {**rows[0], "lead_time_weeks": 60}
    impact = _provider(rows).propagate(_event("mat:inp_substrate"))[0]
    assert impact.time_horizon is TimeHorizon.YEARS


def test_only_companies_get_impacts_not_intermediate_nodes() -> None:
    """`tech:`／`mat:` 是路徑上的中繼點，不是可投資標的。"""
    rows = _rows({
        "company_id": "co:coherent", "relation": "supplies_to",
        "bottleneck": "tech:cpo", "substitutability": 5, "confidence": 0.9,
        "evidence": "externally_corroborated", "sources": ["sd_4"],
        "ticker": "COHR", "lead_time_weeks": None,
    })
    impacts = _provider(rows).propagate(_event("mat:inp_substrate"))

    assert impacts
    assert all(str(i.company_id).startswith("co:") for i in impacts)


def test_confidence_is_the_weakest_link_not_the_average() -> None:
    """一條鏈的可信度不會高於它最不可信的那一環（補償性防線）。"""
    rows = _rows()
    rows[1] = {**rows[1], "confidence": 0.1}      # 第二段很弱
    impact = _provider(rows).propagate(_event("mat:inp_substrate"))[0]

    from alpha.causal import ImpactConfidence

    assert impact.confidence is ImpactConfidence.LOW, (
        "三段強證據不得把一段沒證據的補起來"
    )


def test_as_of_still_raises_when_the_projection_does_not_exist() -> None:
    """傳播不得偷偷繞過 as-of 保險絲。

    ⚠ Phase 6 之後這條保險絲**換了條件、沒有拿掉**：從「as-of 一律拒絕」變成
    「投影不存在時拒絕」。這裡注入的 assertion 一條 `published_at` 都沒有——
    圖上沒有時間資訊時，唯一誠實的回答是「答不了」，不是「那天沒有瓶頸」（L13）。
    """
    from alpha.errors import PointInTimeUnsupported

    undated = Neo4jGraphResearchProvider(driver=None, _assertion_rows=[
        {"src": "co:coherent", "relation": "depends_on", "dst": "mat:inp_substrate",
         "attributes": {"substitutability": 5}, "confidence": 0.9,
         "source_doc_id": "sd_1", "published_at": None},
    ])
    with pytest.raises(PointInTimeUnsupported, match="沒有任何一條"):
        undated.get_dependency_paths(
            EntityId("co:coherent"), as_of=date(2026, 1, 1)  # type: ignore[arg-type]
        )
