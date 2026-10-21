"""證據等級認得「誰在說」：買方自述與關係人自述（2026-10-21 批次二 E9；failure log #11、#10）。

- #11：`depends_on`／`constrained_by` 的主詞是**買方**——買方自己說「我靠它」是需求側一手，不是供應商自誇。
  只拆標籤，rank 與供應商自報相同（不放寬也不收緊 gate；要不同 rank 先量測，INV-5）。
- #10：母子公司、收購方、合資股東說的不是第三方印證（L8）。只認**控制**：`acquired`，或 `invests_in` 宣告
  `attributes.control`。**少數股權不算**——NVIDIA 對 Coherent／Lumentum 的策略投資若算關係人，NVIDIA 以客戶身分說的
  供貨會從外部印證掉下來（2026-10-21 實測 9 條）。持股邊本身不套（拿它降它自己是循環）。

registry 用真的 `IdentityRegistry`（同 test_corroboration）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from identity.registry import CompanyIdentity, IdentityRegistry
from query.bottleneck import (EVIDENCE_LABEL, EVIDENCE_RANK, SELF_SPEAKER_CLASSES, best_evidence, classify_evidence,
                              collapse_assertions, structure_table)
from query.origin_resolution import RELATED_PARTY_CLASSES, related_parties

PARENT, CHILD, SIBLING, CUSTOMER, INVESTOR = "co:ecolab", "co:coolit_systems", "co:nalco", "co:nvidia", "co:fund"
CDU = "tech:coolant_distribution_unit"
CHILD_Q = "CoolIT Systems supplies coolant distribution units for liquid-cooled racks"
DEMAND_Q = "NVIDIA liquid-cooled racks depend on coolant distribution units"


def _registry() -> IdentityRegistry:
    return IdentityRegistry(version=1, companies=(
        CompanyIdentity(PARENT, "ECL", display_name="Ecolab Inc.", name_aliases=("Ecolab",)),
        CompanyIdentity(CHILD, None, display_name="CoolIT Systems", name_aliases=("CoolIT",)),
        CompanyIdentity(SIBLING, None, display_name="Nalco Water", name_aliases=("Nalco",)),
        CompanyIdentity(CUSTOMER, "NVDA", display_name="NVIDIA Corporation", name_aliases=("NVIDIA",)),
        CompanyIdentity(INVESTOR, None, display_name="Strategic Fund", name_aliases=("Strategic Fund",)),
    ))


def _row(aid, origin, *, src=CHILD, relation="supplies_to", dst=CDU, source_type="press_release", attributes=None):
    return {"src": src, "relation": relation, "dst": dst, "attributes": attributes or {}, "confidence": 0.8,
            "origin": origin, "source_type": source_type, "origin_linkage": None, "source_doc_id": f"doc_{aid}",
            "published_at": None, "assertion_id": aid}


def _classes(rows, quotes):
    """正式組合（`structure_table`／`_classify_edges` 同一條）：收斂 → 控制關係 → 逐邊分類。"""
    edges = collapse_assertions(rows)
    related = related_parties(edges.values())
    return {key: classify_evidence(e.src, e.origins, _registry(), filing_origins=e.filing_origins,
                                   quotes_by_assertion=quotes, origin_assertions=e.origin_assertions,
                                   relation=e.relation, related=related)
            for key, e in edges.items()}


ACQUIRED = _row("h1", "Ecolab Inc.", src=PARENT, relation="acquired", dst=CHILD)


# ---------------------------------------------------------------------------
# #11 買方自述
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("relation", ["depends_on", "constrained_by"])
def test_buyer_speaking_about_its_own_dependency_is_a_buyer_self_report(relation) -> None:
    rows = [_row("b1", "NVIDIA", src=CUSTOMER, relation=relation)]
    assert _classes(rows, {"b1": ["NVIDIA relies on CDUs"]})[(CUSTOMER, relation, CDU)] == "buyer_self_reported"
    rows = [_row("b1", "NVIDIA", src=CUSTOMER, relation=relation, source_type="filing")]
    assert _classes(rows, {"b1": ["NVIDIA relies on CDUs"]})[(CUSTOMER, relation, CDU)] == "buyer_self_reported_costly"


def test_supplier_speaking_about_its_own_supply_is_still_a_supplier_self_report() -> None:
    rows = [_row("s1", "CoolIT Systems")]
    assert _classes(rows, {"s1": [CHILD_Q]})[(CHILD, "supplies_to", CDU)] == "self_reported"


def test_buyer_self_report_keeps_the_rank_of_the_cell_it_was_split_from() -> None:
    """只拆標籤：rank、弱證據集合與它拆出來的那一格相同——不放寬、不收緊任何 gate。"""
    assert EVIDENCE_RANK["buyer_self_reported"] == EVIDENCE_RANK["self_reported"]
    assert EVIDENCE_RANK["buyer_self_reported_costly"] == EVIDENCE_RANK["self_reported_costly"]
    assert EVIDENCE_LABEL["buyer_self_reported"] == "買方自述"
    assert "buyer_self_reported" in SELF_SPEAKER_CLASSES


def test_a_lone_buyer_self_report_is_not_swallowed_by_the_default() -> None:
    """`best_evidence` 的起點若是 self_reported，同級同序的買方自述贏不過它——整條邊會印回「供應商自報」。"""
    assert best_evidence(["buyer_self_reported"]) == "buyer_self_reported"
    assert best_evidence([]) == "self_reported"


# ---------------------------------------------------------------------------
# #10 關係人自述
# ---------------------------------------------------------------------------

def test_the_acquirer_speaking_about_its_subsidiary_is_a_related_party_not_corroboration() -> None:
    rows = [ACQUIRED, _row("r1", "Ecolab Inc.")]
    classes = _classes(rows, {"h1": ["Ecolab acquired CoolIT"], "r1": [CHILD_Q]})
    assert classes[(CHILD, "supplies_to", CDU)] == "related_party"
    rows = [ACQUIRED, _row("r1", "Ecolab Inc.", source_type="filing")]
    assert _classes(rows, {"r1": [CHILD_Q]})[(CHILD, "supplies_to", CDU)] == "related_party_costly"


def test_the_same_quote_from_an_unrelated_customer_still_corroborates() -> None:
    """拿掉持股邊 → 同一段逐字回到外部印證（變異對照：判定的來源是控制關係，不是 origin 字串）。"""
    rows = [_row("r1", "Ecolab Inc.")]
    assert _classes(rows, {"r1": [CHILD_Q]})[(CHILD, "supplies_to", CDU)] == "externally_corroborated"


def test_the_holding_edge_itself_is_not_downgraded_by_itself() -> None:
    """子公司說「母公司是誰」是對手方對持股這件事的陳述——拿持股邊去降它自己是循環。"""
    rows = [ACQUIRED, _row("h2", "CoolIT Systems", src=PARENT, relation="acquired", dst=CHILD)]
    classes = _classes(rows, {"h1": ["Ecolab acquired CoolIT"], "h2": ["Ecolab acquired CoolIT Systems"]})
    assert classes[(PARENT, "acquired", CHILD)] == "externally_corroborated"


def test_a_minority_investment_does_not_make_the_investor_a_related_party() -> None:
    minority = _row("i1", "Strategic Fund", src=INVESTOR, relation="invests_in", dst=CHILD)
    rows = [minority, _row("r1", "Strategic Fund")]
    assert related_parties(collapse_assertions(rows).values()) == {}
    assert _classes(rows, {"r1": [CHILD_Q]})[(CHILD, "supplies_to", CDU)] == "externally_corroborated"


def test_an_investment_declared_as_control_makes_the_investor_a_related_party() -> None:
    joint = _row("i1", "Strategic Fund", src=INVESTOR, relation="invests_in", dst=CHILD,
                 attributes={"control": True})
    rows = [joint, _row("r1", "Strategic Fund")]
    assert _classes(rows, {"r1": [CHILD_Q]})[(CHILD, "supplies_to", CDU)] == "related_party"


def test_two_subsidiaries_of_the_same_parent_are_related_but_co_investors_are_not() -> None:
    rows = [ACQUIRED, _row("h3", "Ecolab Inc.", src=PARENT, relation="acquired", dst=SIBLING),
            _row("r1", "Nalco Water")]
    assert _classes(rows, {"r1": [CHILD_Q]})[(CHILD, "supplies_to", CDU)] == "related_party"
    co_owners = related_parties(collapse_assertions([
        _row("j1", "x", src=PARENT, relation="invests_in", dst=CHILD, attributes={"control": True}),
        _row("j2", "x", src=INVESTOR, relation="invests_in", dst=CHILD, attributes={"control": True})]).values())
    assert INVESTOR not in co_owners[PARENT] and PARENT not in co_owners[INVESTOR]


def test_the_subject_itself_wins_the_tie_with_its_related_party_in_any_order() -> None:
    for origins in (["CoolIT Systems", "Ecolab Inc."], ["Ecolab Inc.", "CoolIT Systems"]):
        rows = [ACQUIRED] + [_row(f"t{i}", o) for i, o in enumerate(origins)]
        quotes = {f"t{i}": [CHILD_Q] for i in range(2)}
        assert _classes(rows, quotes)[(CHILD, "supplies_to", CDU)] == "self_reported"


def test_related_party_ranks_with_self_reports_and_is_weak() -> None:
    from alpha.narrative.argument import WEAK_CLASSES

    assert EVIDENCE_RANK["related_party"] == EVIDENCE_RANK["self_reported"]
    assert EVIDENCE_RANK["related_party_costly"] == EVIDENCE_RANK["self_reported_costly"]
    assert {"related_party", "buyer_self_reported"} <= WEAK_CLASSES
    assert RELATED_PARTY_CLASSES <= set(EVIDENCE_RANK)


def test_structure_table_wires_the_control_relations_in() -> None:
    """正式路徑（`structure_table`）自己算控制關係——呼叫端不必、也不能忘了給。"""
    rows = [ACQUIRED, _row("r1", "Ecolab Inc.", attributes={"substitutability": 4})]
    table = structure_table(rows, _registry(), quotes_by_assertion={"r1": [CHILD_Q]})
    evidence = {(r["company_id"], r["bottleneck"]): r["evidence"] for r in table["rows"]}
    assert evidence[(CHILD, CDU)] == "related_party"


# ---------------------------------------------------------------------------
# 讀圖引用核對與插槽視角：同一個 owner、同一個答案
# ---------------------------------------------------------------------------

def _reading(origin_doc: str):
    from alpha.structure_reading.contracts import structure_reading_record

    structure = {"node": CDU, "result_digest": "e" * 64, "anchor_chain": None, "angles": {
        "supply_side": [{"src": CHILD, "relation": "supplies_to", "dst": CDU, "substitutability": 4,
                         "sole_source": None, "qualification_status": None, "evidence": "related_party",
                         "documents": 1}],
        "demand_side": [{"src": CUSTOMER, "relation": "depends_on", "dst": CDU, "substitutability": None,
                         "sole_source": None, "qualification_status": None, "evidence": "buyer_self_reported",
                         "documents": 1}],
        "next_layer": [], "counter_path": []}}
    citations = [{"angle": "demand_side", "edge": [CUSTOMER, "depends_on", CDU], "quote": DEMAND_Q,
                  "source_id": "nvda_doc", "independent": False},
                 {"angle": "supply_side", "edge": [CHILD, "supplies_to", CDU], "quote": CHILD_Q,
                  "source_id": origin_doc, "independent": True}]
    disproof = [{"condition": "任一液冷整合商在正式文件宣布改用自製 CDU 並量產", "entities": [CHILD],
                 "check_frequency": "每季", "action_48h": "重讀這一層", "source": "self"}]
    return structure_reading_record(
        node=CDU, structure=structure, unit="layer", kind="moat", reading="測試：關係人標 independent。",
        expires=date(2026, 12, 24), created_at=datetime(2026, 10, 21, 3, 0, tzinfo=timezone.utc), author="test",
        citations=citations, disproof=disproof)


def test_a_citation_from_a_related_party_marked_independent_is_rejected() -> None:
    from alpha.providers.structure_readings import verify_citations

    quotes = {(CHILD, "supplies_to", CDU): [{"quote": CHILD_Q, "doc": "ecl_pr", "origin": "Ecolab Inc.",
                                             "origin_linkage": None}],
              (CUSTOMER, "depends_on", CDU): [{"quote": DEMAND_Q, "doc": "nvda_doc", "origin": "NVIDIA",
                                               "origin_linkage": None}]}
    related = related_parties(collapse_assertions([ACQUIRED]).values())
    problems = verify_citations(_reading("ecl_pr"), quotes, registry=_registry(), related=related)
    assert any("控制關係" in p for p in problems), problems
    assert not any("控制關係" in p for p in verify_citations(_reading("ecl_pr"), quotes, registry=_registry(),
                                                         related={}))


def test_socket_view_does_not_list_a_related_party_as_a_customer_quote() -> None:
    from query.bottleneck import CanonicalEdge
    from query.structure import SOCKET_NO_CUSTOMER_QUOTE, build_socket_view

    socket = "prod:cdu_rack"
    edges = [CanonicalEdge(src=CHILD, relation="supplies_to", dst=socket),
             CanonicalEdge(src=PARENT, relation="acquired", dst=CHILD, control=True)]
    quotes = {(CHILD, "supplies_to", socket): [{"quote": "CoolIT supplies the CDU rack", "doc": "ecl_pr", "tier": 1,
                                                "origin": "Ecolab Inc.", "origin_linkage": None}]}
    view = build_socket_view(socket, edges, quotes, registry=_registry())
    assert view.customer_quotes == [] and view.customer_absence == SOCKET_NO_CUSTOMER_QUOTE
    assert [s["resolved_as"] for s in view.sources] == ["關係人"]
    unrelated = build_socket_view(socket, edges[:1], quotes, registry=_registry())
    assert [q["company"] for q in unrelated.customer_quotes] == [PARENT]
