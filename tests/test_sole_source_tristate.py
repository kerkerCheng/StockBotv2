"""`sole_source` 的三態語意（Phase 1.1 第 4 項）：未填是 `None`，不是 `bool(None) == False`。

修在**上游**（`query/bottleneck.py::rank_bottlenecks`），不是只在 read model 貼註記——
壓平發生在排序權威的輸出，下游每一層（provider、Q1 佐證、view）都只能看到假的 False。
排序鍵仍是 `1 if sole_source else 0`（None 與 False 同為 0），所以排序語意不變。
"""
from __future__ import annotations

from datetime import date

from alpha.contracts import EvidenceRef, ScarcityInputs
from alpha.identity import CompanyId, EntityId
from alpha.provider import BottleneckRow
from alpha.providers.graph_neo4j import Neo4jGraphResearchProvider
from alpha.testing import FakeGraphResearchProvider
from query.bottleneck import rank_bottlenecks


class _Reg:
    """只實作 `rank_bottlenecks`／`classify_evidence` 用到的 registry surface。"""

    _map = {"co:a": "AAA", "co:b": "BBB", "co:c": "CCC"}
    companies = ()

    def research_ticker(self, company_id):
        return self._map.get(company_id)

    def company_id_for_ticker(self, ticker):
        return next((cid for cid, t in self._map.items() if t == ticker.strip().upper()), None)

    def has_company(self, company_id):
        return company_id in self._map


def _assertion(src, dst, *, attrs, conf=0.8, doc="d1"):
    return {"src": src, "relation": "supplies_to", "dst": dst, "attributes": attrs,
            "confidence": conf, "origin": "third_party", "source_doc_id": doc,
            "published_at": "2026-05-01"}


def test_rank_bottlenecks_keeps_unknown_sole_source_as_none_not_false() -> None:
    """三條邊：明確 True、明確 False、完全沒發言。第三條必須是 None。

    空跑檢查：把 `rank_bottlenecks` 的 `"sole_source": edge.sole_source` 改回
    `bool(edge.sole_source)` → 這條會紅。
    """
    rows = [
        _assertion("co:a", "tech:ai_switch", attrs={"substitutability": 5, "sole_source": True}),
        _assertion("co:b", "tech:ai_switch", attrs={"substitutability": 5, "sole_source": False}),
        _assertion("co:c", "tech:ai_switch", attrs={"substitutability": 5}),
    ]
    by_company = {r["company_id"]: r for r in rank_bottlenecks(rows, _Reg())["rows"]}
    assert by_company["co:a"]["sole_source"] is True
    assert by_company["co:b"]["sole_source"] is False
    assert by_company["co:c"]["sole_source"] is None, "未填必須是 None，不是 False"


def test_ordering_is_unchanged_because_unknown_and_false_both_sort_as_zero() -> None:
    """排序鍵 `1 if sole_source else 0` 對 None 與 False 一視同仁——這是本修正不改排序語意的機械保證。"""
    rows = [
        _assertion("co:b", "tech:ai_switch", attrs={"substitutability": 5, "sole_source": False}),
        _assertion("co:c", "tech:ai_switch", attrs={"substitutability": 5}),
        _assertion("co:a", "tech:ai_switch", attrs={"substitutability": 5, "sole_source": True}),
    ]
    ranked = [r["company_id"] for r in rank_bottlenecks(rows, _Reg())["rows"]]
    assert ranked[0] == "co:a"                                  # True 仍排最前
    assert set(ranked[1:]) == {"co:b", "co:c"}                  # False 與 None 同階


def test_structural_diff_treats_unknown_to_true_and_true_to_unknown_honestly() -> None:
    """未填→是 是新資訊（收緊）；是→未填 只是屬性從最可信文件上消失，不是世界鬆了。"""
    diff = Neo4jGraphResearchProvider._structural_diff  # noqa: SLF001
    base = {"substitutability": 5, "qualification_status": "qualified", "bottleneck": "tech:x"}
    known = {"tech:x"}
    unknown_to_true = diff({**base, "sole_source": None}, {**base, "sole_source": True}, known)
    assert any(kind == "capacity_constraint" and direction == "tightening" and "未填轉是" in what
               for kind, direction, what in unknown_to_true)
    true_to_unknown = diff({**base, "sole_source": True}, {**base, "sole_source": None}, known)
    assert not any("sole_source" in what for _k, _d, what in true_to_unknown)
    true_to_false = diff({**base, "sole_source": True}, {**base, "sole_source": False}, known)
    assert any(direction == "loosening" and "由是轉否" in what for _k, direction, what in true_to_false)


class _TriStateProvider(FakeGraphResearchProvider):
    """可指定 sole_source 三態的 fake provider。"""

    sole_source: bool | None = None

    def get_bottlenecks(self, *, sector=None, min_substitutability=4, as_of=None):
        refs = self._evidence(as_of)
        return (BottleneckRow(
            company_id=self.company_id, edge_key="edge:tri", relation="supplies_to",
            target_id=EntityId("co:nvidia"),
            inputs=ScarcityInputs(substitutability=5, sole_source=self.sole_source,
                                  qualification_status="qualified", evidence=refs),
            demand_anchor=EntityId("tech:ai_switch"), evidence=refs,
        ),)


def _view_with(sole_source):
    from alpha.context import build_research_context
    from alpha.identity import Ticker
    from briefing.alpha_view import build_alpha_investment_view
    from tests.test_alpha_investment_view import _FakeFundamentals

    provider = _TriStateProvider(company_id=CompanyId("co:coherent"))
    provider.sole_source = sole_source
    build = build_research_context(ticker=Ticker("COHR"), company_id=CompanyId("co:coherent"),
                                   graph_provider=provider, fundamentals_provider=_FakeFundamentals())
    return build_alpha_investment_view(build=build, today=date(2026, 9, 5))


def test_view_distinguishes_unknown_sole_source_from_false() -> None:
    """view 端：None → `missing`（未填≠否），False → available 且值為 False，不帶任何「可能未填」的註記。"""
    unknown = next(d for d in _view_with(None).structural_thesis.scarcity_inputs if d.key == "sole_source")
    assert unknown.status == "missing" and unknown.value is None
    assert "未填" in (unknown.reason or "")
    known_false = next(d for d in _view_with(False).structural_thesis.scarcity_inputs if d.key == "sole_source")
    assert known_false.status == "available" and known_false.value is False
    assert "壓平" not in (known_false.reason or "")
    known_true = next(d for d in _view_with(True).structural_thesis.scarcity_inputs if d.key == "sole_source")
    assert known_true.value is True


def test_q1_bonus_is_not_granted_for_unknown_sole_source() -> None:
    """Q1 的 sole_source 佐證只給明確 True；None 與 False 都不加成（排序與計分語意不變）。"""
    from alpha.context import structural_score

    ref = EvidenceRef(ref="graph://edge/x", kind="graph_edge", evidence_class="externally_corroborated",
                      evidence_tier=1)
    for value in (None, False):
        score, _ = structural_score(ScarcityInputs(substitutability=5, sole_source=value, evidence=(ref,)))
        assert score is not None and score.declared == 0.90
    score_true, _ = structural_score(ScarcityInputs(substitutability=5, sole_source=True, evidence=(ref,)))
    assert score_true.declared == 0.94
