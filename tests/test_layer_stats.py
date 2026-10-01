"""層計數器（`query/layer_stats.py`；Phase 4 Step 4.4c）：ROADMAP Phase 4 ①②③ 的每一個數，在夾具圖上逐一釘住。

夾具：凍結集合 {mat:x, mat:y, mat:gone}；mat:x 只有 Alpha 一家且只有它自己說（①）；mat:y 有 Alpha／Beta／Gamma 三家，
一份 TrendForce 報告逐字列舉三家（②），一篇解析不到的部落格另列兩家（不算、但計數）；tech:new 是集合外的新節點，
掛兩筆 Phase 內新增的帶 sub assertion（③b）；Beta→Customer 是外部印證但引文沒點名 Beta（附屬）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from query.bottleneck import classify_evidence, collapse_assertions
from query.layer_stats import compute_layer_stats, summary_line
from query.origin_resolution import PUBLISHER_KINDS, load_publishers
from query.sub_language import SubLanguage

LANG = SubLanguage(version=1, variant="test", terms=("sole supplier", "only supplier", "qualified", "second source"))


class _Company:
    def __init__(self, cid, display_name, *aliases):
        self.company_id, self.display_name, self.name_aliases, self.aliases = cid, display_name, aliases, ()


class _Registry:
    def __init__(self):
        self._c = {c.company_id: c for c in (
            _Company("co:a", "Alpha Corp", "Alpha"), _Company("co:b", "Beta Inc.", "Beta"),
            _Company("co:c", "Gamma Ltd.", "Gamma"), _Company("co:cust", "Customer Co"))}

    @property
    def companies(self):
        return tuple(self._c.values())

    def company(self, cid):
        return self._c.get(cid)

    def company_id_for_ticker(self, ticker):
        return None

    def has_company(self, cid):
        return cid in self._c


def _row(aid, src, dst, origin, doc, *, sub=None, relation="supplies_to"):
    return {"assertion_id": aid, "src": src, "relation": relation, "dst": dst, "confidence": 0.8,
            "attributes": json.dumps({"substitutability": sub} if sub is not None else {}),
            "origin": origin, "source_doc_id": doc, "source_type": "news"}


ROWS = [
    _row("r1", "co:a", "mat:x", "Alpha Corp", "d_a", sub=4),
    _row("r2", "co:b", "mat:y", "Beta Inc.", "d_b", sub=3),
    _row("r3", "co:a", "mat:y", "TrendForce", "d_tf"),
    _row("r4", "co:c", "mat:y", "TrendForce", "d_tf"),
    _row("r5", "co:b", "mat:y", "Unknown Blog", "d_blog"),
    _row("r6", "co:c", "tech:new", "Gamma Ltd.", "d_c", sub=5),
    _row("r7", "co:a", "tech:new", "Alpha Corp", "d_a2", sub=2),
    _row("r8", "co:b", "co:cust", "Customer Co", "d_cust"),
    _row("r9", "co:c", "mat:w", "TrendForce", "d_tf_w"),      # 只有一家、但有第三方印證 → 不算 ①
]
QUOTES = {
    "r1": ["Alpha is the sole supplier of X substrates"],
    "r2": ["Beta ships Y wafers in volume"],
    "r3": ["Alpha, Beta and Gamma supply Y"],
    "r4": ["Alpha, Beta and Gamma supply Y"],
    "r5": ["Beta and Gamma both make Y"],
    "r6": ["Gamma is the only supplier of the new part"],
    "r7": ["Alpha ships the new part"],
    "r8": ["We buy wafers from a Korean vendor"],
    "r9": ["Gamma supplies W to every module maker"],
}
BASELINE = {"frozen_nodes": frozenset({"mat:x", "mat:y", "mat:w", "mat:gone"}),
            "frozen_assertions": frozenset({"r1", "r2", "r3", "r4", "r5", "r8", "r9"}),
            "sub_assertions": frozenset({"r1", "r2"})}
LAYER_NODES = ["mat:x", "mat:y", "mat:w", "tech:new"]


@pytest.fixture()
def stats(tmp_path: Path) -> dict:
    path = tmp_path / "publishers.json"
    path.write_text(json.dumps({
        "schema_version": 1, "kinds": {k: {"corroborates": v} for k, v in PUBLISHER_KINDS.items()},
        "publishers": [{"origin": "TrendForce", "kind": "industry_research", "corroborates": True, "seen_in": "d_tf"}],
    }), encoding="utf-8")
    pubs, reg = load_publishers(path), _Registry()
    edges = list(collapse_assertions(ROWS).values())
    for edge in edges:
        edge.evidence = classify_evidence(edge.src, edge.origins, reg, filing_origins=edge.filing_origins,
                                          origin_linkages=edge.origin_linkages, publishers=pubs)
    return compute_layer_stats(edges=edges, rows=ROWS, quotes_by_assertion=QUOTES,
                               layer_nodes=LAYER_NODES, baseline=BASELINE, registry=reg,
                               language=LANG, publishers=pubs)


def test_one_supply_distribution_over_the_frozen_set(stats) -> None:
    supply = stats["supply"]
    assert supply["frozen_n"] == 4 and supply["frozen_on_graph"] == 3 and supply["frozen_gone"] == ["mat:gone"]
    assert supply["ns"] == {"0": 0, "1": 2, "2": 0, "3+": 1}
    # 只有 Alpha、只有它自己說 → 算；mat:w 只有 Gamma 一家但 TrendForce 印證 → 不算
    assert supply["sole_self_reported_nodes"] == ["mat:x"]
    assert supply["new_nodes"] == ["tech:new"]                      # 集合外的新節點另印，不算進 ①


def test_two_counts_a_non_supplier_document_that_names_two_suppliers(stats) -> None:
    enum = stats["enumeration"]
    assert enum["layers"] == 4 and enum["layers_with_suppliers"] == 4 and enum["at_least_3"] == 1
    # mat:w 的 TrendForce 文件只具名一家：列舉要 ≥2 家才算
    assert enum["named_by_non_supplier_layers"] == ["mat:y"]
    hit = enum["hits"][0]
    assert (hit["doc"], hit["origin_kind"], hit["named"]) == ("d_tf", "publisher", ["co:a", "co:b", "co:c"])
    assert enum["unresolved_origin_sources"] == 1                    # 部落格解析不到：不算、但計數（不猜）
    assert enum["at_least_3_all_held_layers"] == ["mat:y"]           # 三家都被引文具名


def test_a_supplier_listing_its_rivals_is_not_a_layer_document(tmp_path: Path) -> None:
    """供應商自己的文件列舉同層對手，不是「非供應商來源」（L8：供應商自稱是弱主張）。"""
    reg = _Registry()
    rows = [_row("s1", "co:a", "mat:z", "Alpha Corp", "d_self"), _row("s2", "co:b", "mat:z", "Alpha Corp", "d_self")]
    quotes = {"s1": ["Alpha and Beta are the two qualified makers"], "s2": ["Alpha and Beta are the two qualified makers"]}
    edges = list(collapse_assertions(rows).values())
    for edge in edges:
        edge.evidence = "self_reported"
    out = compute_layer_stats(edges=edges, rows=rows, quotes_by_assertion=quotes, layer_nodes=["mat:z"],
                              baseline={**BASELINE, "frozen_nodes": frozenset({"mat:z"})}, registry=reg,
                              language=LANG, publishers=load_publishers(_empty_publishers(tmp_path)))
    assert out["enumeration"]["named_by_non_supplier"] == 0


def _empty_publishers(tmp_path: Path) -> Path:
    path = tmp_path / "empty_publishers.json"
    path.write_text(json.dumps({"schema_version": 1, "kinds": {k: {"corroborates": v} for k, v in PUBLISHER_KINDS.items()},
                                "publishers": []}), encoding="utf-8")
    return path


def test_three_splits_stock_from_new_sub_assertions(stats) -> None:
    sub = stats["sub_language"]
    assert sub["stock_n"] == 2 and sub["stock_unsupported"] == ["r2"] and sub["stock_gone"] == []
    assert (sub["new_n"], sub["new_supported"], sub["new_unsupported"]) == (2, 1, ["r7"])


def test_corroborated_edges_whose_quote_never_names_the_supplier_are_listed(stats) -> None:
    assert stats["ec_quote_does_not_name_supplier"] == ["co:b supplies_to co:cust"]


def test_summary_line_prints_every_number_and_absence_is_not_zero(stats) -> None:
    line = summary_line(stats)
    for fragment in ("①獨家且全自報 1", "集合外新節點 1", "②非供應商來源列舉 ≥2 家 1 層", "≥3 家母體 1", "每家撐住 1",
                     "origin 解析不到的來源 1", "③a sub 引文不含可替代性語言 1／2", "③b 新增帶 sub supported 1／2",
                     "外部印證但引文不具名供應商 1", "字表 v1·test"):
        assert fragment in line, fragment
    assert "不是 0" in summary_line(None)
    assert "不是 0" in summary_line({"absence": {"kind": "upstream_unavailable", "reason": "基準讀不到"}})
