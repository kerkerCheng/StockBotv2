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
from query.layer_stats import (BASELINE_KEY, BASELINES_PATH, CONTENT_BASELINE_KEY, assertion_content_digest,
                               compute_layer_stats, content_digests, load_baseline, load_content_baseline,
                               summary_line)
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
    # 夾具沒給內容基準：重寫那一格量不到——印缺席，不印 0（INV-3）。
    assert stats["sub_language"]["superseded_n"] is None and "重寫量不到（沒有內容基準，不是 0）" in line
    assert "不是 0" in summary_line(None)
    assert "不是 0" in summary_line({"absence": {"kind": "upstream_unavailable", "reason": "基準讀不到"}})


# ---------------------------------------------------------------------------
# ③b 認得「重寫」（Phase 5 Step 5.1，#29）：更正走廊沿用原 id 重寫，只看 id 會看不到
# ---------------------------------------------------------------------------

def _stats_with(rows, quotes, tmp_path: Path, *, content_baseline) -> dict:
    edges = list(collapse_assertions(rows).values())
    for edge in edges:
        edge.evidence = "self_reported"
    return compute_layer_stats(edges=edges, rows=rows, quotes_by_assertion=quotes, layer_nodes=LAYER_NODES,
                               baseline=BASELINE, registry=_Registry(), language=LANG,
                               publishers=load_publishers(_empty_publishers(tmp_path)),
                               content_baseline=content_baseline)


def test_three_b_counts_a_rewritten_assertion_under_its_old_id(tmp_path: Path) -> None:
    """同 id 換引文、或只宣告 origin_linkage（[666] 的形狀）→ 進 ③b 分母，與「新增」分開計。

    變異：把重寫的判定拿掉（只看 id 在不在凍結集合）→ 這條紅（重寫 0、分母只剩新增 2）。"""
    content = content_digests(ROWS, QUOTES, ids=BASELINE["frozen_assertions"])
    unchanged = _stats_with(ROWS, QUOTES, tmp_path, content_baseline=content)["sub_language"]
    assert (unchanged["superseded"], unchanged["superseded_n"]) == ([], 0)          # 沒動就不是重寫
    rows = []
    for row in ROWS:
        if row["assertion_id"] in ("r1", "r8"):
            # r1 帶 sub、只宣告 origin_linkage（[666] 的形狀）；r8 不帶 sub——改了也不進 ③b
            row = dict(row, origin_linkage="independent")
        rows.append(row)
    quotes = dict(QUOTES, r2=["Beta is the sole supplier of Y wafers"])           # r2 同 id、換一段引文
    stats = _stats_with(rows, quotes, tmp_path, content_baseline=content)
    sub = stats["sub_language"]
    assert sub["superseded"] == ["r1", "r2"] and sub["superseded_n"] == 2
    assert (sub["superseded_supported"], sub["superseded_unsupported"]) == (2, [])
    assert (sub["new_n"], sub["new_supported"]) == (2, 1)                          # 新增照舊、分開計
    assert sub["content_baseline"] == CONTENT_BASELINE_KEY
    assert "③b 新增或重寫的帶 sub supported 3／4（新增 2、重寫 2）" in summary_line(stats)


def test_three_b_rewrite_of_an_id_missing_from_the_content_baseline_still_counts(tmp_path: Path) -> None:
    """凍結集合裡有、內容基準裡沒有（5.1 當下不在圖上、後來又出現）→ 沒有可比的舊版，算重寫，不靜默當沒動。"""
    content = content_digests(ROWS, QUOTES, ids=BASELINE["frozen_assertions"] - {"r2"})
    assert _stats_with(ROWS, QUOTES, tmp_path, content_baseline=content)["sub_language"]["superseded"] == ["r2"]


def test_content_digest_moves_with_the_claim_not_with_research_volume() -> None:
    """指紋跟著主張走：引文、sub、證據三欄、邊、來源文件變了才變；補日期、改 confidence、引文順序不變。"""
    row = dict(ROWS[0], published_at="2026-06-01")
    base = assertion_content_digest(row, ["b quote", "a quote"])
    assert assertion_content_digest(dict(row, published_at=None, confidence=0.1), ["a quote", "b quote"]) == base
    for changed in (dict(row, origin_linkage="independent"), dict(row, source_type="filing"),
                    dict(row, origin="Someone Else"), dict(row, dst="mat:other"),
                    dict(row, source_doc_id="d_other"), dict(row, attributes=json.dumps({"substitutability": 2}))):
        assert assertion_content_digest(changed, ["a quote", "b quote"]) != base
    assert assertion_content_digest(row, ["a quote"]) != base


def test_content_baseline_lives_under_its_own_key_and_absence_is_none(tmp_path: Path) -> None:
    """append-only：內容基準是另一個鍵；檔案沒有這個鍵＝None（呼叫端印缺席），不是空 dict。"""
    path = tmp_path / "graph_baselines.json"
    path.write_text(json.dumps({"baselines": {BASELINE_KEY: {name: {"ids": ["x"]} for name in
                                                             ("frozen_nodes", "frozen_assertions", "sub_assertions")}}}),
                    encoding="utf-8")
    assert load_content_baseline(path) is None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["baselines"][CONTENT_BASELINE_KEY] = {"assertion_digests": {"digests": {"x": "abc"}}}
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_content_baseline(path) == {"x": "abc"} and load_baseline(path)["frozen_assertions"] == {"x"}


def test_the_real_content_baseline_covers_the_frozen_assertions_still_on_the_graph() -> None:
    """正式檔：內容基準的 id 都屬於 4.0 凍結的 assertion 集合（它是同一個母體的內容快照，不是另一個母體）。"""
    content = load_content_baseline()
    assert content is not None and content, "config/graph_baselines.json 缺內容基準（Phase 5 Step 5.1）"
    entry = json.loads(BASELINES_PATH.read_text(encoding="utf-8"))["baselines"][CONTENT_BASELINE_KEY]
    assert entry["assertion_digests"]["n"] == len(content)
    assert set(content) <= load_baseline()["frozen_assertions"]
    assert all(len(v) == 16 for v in content.values())
