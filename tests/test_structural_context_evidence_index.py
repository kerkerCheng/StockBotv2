"""研究判斷的證據索引收這家公司的全部供貨／開發邊，Q1 照舊只用達門檻的子集（2026-10-08，Phase 7 failure log #25）。

事發：寫 ATS.VI 的研究判斷時，packet 的證據索引只有財務快照——AT&S 的供貨邊（Kulim 擴產由客戶全額出資、Marvell 點名）在圖上，
卻引用不了：「算不算瓶頸」（substitutability ≥ 4）與「能不能被引用」共用一個子集（L12）。回放（真圖）：AT&S 索引的圖引用 0 → 9、
NOVT 0 → 2，兩家的 Q1 列都還是 0。
"""
from __future__ import annotations

from datetime import date

from alpha.providers.graph_neo4j import Neo4jGraphResearchProvider


def _assertion(dst: str, published: str | None, *, sub: int | None, doc: str, src: str = "co:ats",
               relation: str = "supplies_to") -> dict:
    attrs = {} if sub is None else {"substitutability": sub}
    return {"src": src, "relation": relation, "dst": dst, "attributes": attrs, "confidence": 0.9,
            "origin": "Third Party Research", "source_type": "news", "source_doc_id": doc, "published_at": published}


def _provider(*rows) -> Neo4jGraphResearchProvider:
    return Neo4jGraphResearchProvider(driver=object(), _assertion_rows=list(rows), _quotes_by_assertion={})


def test_unscored_supply_edges_are_citable_but_do_not_become_q1_edges() -> None:
    provider = _provider(
        _assertion("co:amd", "2026-06-15", sub=None, doc="ats_kulim_pr"),          # 沒填 substitutability
        _assertion("co:marvell_technology", "2026-09-22", sub=2, doc="ats_mrvl"),   # 填了但低於門檻
    )
    context = provider.get_company_structural_context("co:ats")
    refs = {e.ref for e in context.evidence}
    assert "graph://source/ats_kulim_pr" in refs and "graph://source/ats_mrvl" in refs
    assert "graph://edge/co:ats/supplies_to/co:amd" in refs
    assert context.edges == ()                                   # edges 照舊只放達門檻的
    assert [r for r in provider.get_bottlenecks() if str(r.company_id) == "co:ats"] == []   # Q1 輸入不變


def test_the_wider_index_still_respects_as_of() -> None:
    provider = _provider(
        _assertion("co:amd", "2026-06-15", sub=None, doc="early"),
        _assertion("co:marvell_technology", "2026-09-22", sub=None, doc="late"),
    )
    refs = {e.ref for e in provider.get_company_structural_context("co:ats", as_of=date(2026, 7, 1)).evidence}
    assert "graph://source/early" in refs and "graph://source/late" not in refs
