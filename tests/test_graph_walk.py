"""走圖（`query/graph_walk.py`，Phase 2 Step 2.6）：九型問句各自「命中／母體」，不排序、不加總、不 gate。

fixture 全部離線（不連 Neo4j、不讀真實 ledger）：這一層的責任是「一份圖 → 九型問句」，
綁在真實資料上只會讓測試在 DB 沒開時變成綠色的空跑（L13-2）。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from query import graph_walk as gw
from query.bottleneck import collapse_assertions
from query.coverage_gaps import classify

ROOT = Path(__file__).resolve().parents[1]
ANCHOR = "tech:ai_accelerator"


def _row(src, relation, dst, *, sub=None, origin="Someone"):
    attrs = {"substitutability": sub} if sub is not None else {}
    return {"src": src, "relation": relation, "dst": dst, "attributes": attrs, "confidence": 0.8,
            "origin": origin, "source_type": "press_release", "source_doc_id": f"doc_{src}_{dst}",
            "published_at": None}


def _edges(rows):
    return list(collapse_assertions(rows).values())


class FakeRegistry:
    def __init__(self, companies, tickers):
        self._companies = set(companies)
        self._tickers = dict(tickers)

    def has_company(self, cid):
        return cid in self._companies

    def company_id_for_ticker(self, ticker):
        return self._tickers.get(ticker)


def fake_graph():
    """一張小圖：
    - `mat:thin`：需求側 sub 5、兩家供應商（一家填 sub）→ 薄層
    - `mat:sole`：需求側 sub 4、一家供應商、sub 沒填、證據自報 → 薄層＋獨家自報＋未填
    - `mat:thick`：需求側 sub 4、四家 → 不薄
    - `mat:soft`：需求側 sub 2 → 不在母體
    - `co:orphan` 往下供貨但走不到錨
    """
    rows = [
        _row(ANCHOR, "depends_on", "mat:thin", sub=5),
        _row("co:a", "supplies_to", "mat:thin", sub=3), _row("co:b", "supplies_to", "mat:thin"),
        _row(ANCHOR, "depends_on", "mat:sole", sub=4),
        _row("co:solo", "supplies_to", "mat:sole"),
        _row(ANCHOR, "depends_on", "mat:thick", sub=4),
        *[_row(f"co:t{i}", "supplies_to", "mat:thick", sub=2) for i in range(4)],
        _row(ANCHOR, "depends_on", "mat:soft", sub=2),
        _row("co:a", "supplies_to", "mat:soft", sub=2),
        _row("co:orphan", "supplies_to", "tech:nowhere"),
    ]
    return _edges(rows)


def _cov(node, *, direct=(), indirect=(), status=None, degree=1):
    return {"node": node, "name": node, "direct": list(direct), "indirect": list(indirect),
            "status": status or classify(list(direct), list(indirect), node), "degree": degree,
            "abstraction_level": None}


def fake_coverage():
    return [
        _cov("tech:gap"),                                       # 沒人供應
        _cov("tech:isolated", degree=0),                        # 沒人供應、孤立
        _cov("prod:noise"),                                     # 抽取副產品，只計數
        _cov("tech:npo", indirect=["co:lumentum"]),             # 建模待補
        _cov("mat:thin", direct=["co:a"]),                      # 已覆蓋
        _cov("tech:export_control", status="concept"),          # 概念節點
    ]


def fake_leads():
    return {
        "L_old": {"lead_id": "L_old", "status": "triaged_go", "first_seen": "2026-09-01T00:00:00+00:00",
                  "entities": {"company_ids": ["co:amd", "co:a", "co:not_in_registry"], "tickers": ["AMD", "CXMT"]}},
        "L_new": {"lead_id": "L_new", "status": "researching", "first_seen": "2026-09-20T00:00:00+00:00",
                  "entities": {"company_ids": ["co:iren"], "tickers": ["IREN"]}},
        "L_in": {"lead_id": "L_in", "status": "triaged_go", "first_seen": "2026-09-10T00:00:00+00:00",
                 "entities": {"company_ids": ["co:a"], "tickers": []}},
        "L_empty": {"lead_id": "L_empty", "status": "triaged_go", "entities": {"company_ids": [], "tickers": []}},
        "L_parked": {"lead_id": "L_parked", "status": "parked", "entities": {"company_ids": ["co:amd"]}},
    }


REGISTRY = FakeRegistry({"co:amd", "co:iren", "co:a"}, {"AMD": "co:amd", "IREN": "co:iren"})


def fake_readings():
    return [
        {"node": "mat:inp_substrate", "unit": "layer", "reading_id": "sr_1", "status": "current",
         "needs_reread_by_graph": False, "needs_reread": True, "reason": "無變化"},
        {"node": "prod:supernova", "unit": "socket", "reading_id": "sr_2", "status": "stale",
         "needs_reread_by_graph": True, "needs_reread": True, "reason": "供給側多一家"},
        {"node": "tech:gone", "unit": None, "reading_id": None, "status": None, "reason": "已全部撤回"},
    ]


def run_walk(**overrides):
    kw = dict(edges=fake_graph(), graph_nodes=["co:a", "co:b", "mat:thin", ANCHOR],
              reading_rows=fake_readings(), leads=fake_leads(), registry=REGISTRY,
              coverage_rows=fake_coverage(),
              duplicate_buckets={"unmentioned": [{"pair": ["tech:eml", "tech:inp_eml"], "rules": ["id_token_subset"],
                                                  "same_abstraction_level": True, "left": None, "right": None}],
                                 "mentioned": [{"pair": ["tech:x", "tech:x_y"]}]},
              duplicate_node_total=20, anchors=[ANCHOR])
    kw.update(overrides)
    return gw.walk(**kw)


def _q(result, key):
    return next(q for q in result["questions"] if q["key"] == key)


# ---------------------------------------------------------------------------
# 封閉字彙與「不排序、不加總」
# ---------------------------------------------------------------------------

def test_question_types_are_a_closed_vocabulary_in_reading_order() -> None:
    # ⚠ 刻意硬編：加一型就該讓這條紅一次，逼人答「它指得出哪一個研究動作、母體多大、實測命中率」（L14-4）。
    assert gw.QUESTION_TYPE_KEYS == (
        "thin_layer_unread", "sole_supplier_self_reported", "supply_unfilled", "reading_stale",
        "lead_not_in_graph", "supplier_no_anchor", "no_supplier", "modelling_gap", "duplicate_node")
    result = run_walk()
    assert [q["key"] for q in result["questions"]] == list(gw.QUESTION_TYPE_KEYS)
    assert [q["order"] for q in result["questions"]] == list(range(1, 10))
    for q in result["questions"]:
        assert q["next_action"] and q["scope_rule"] and q["hit_rule"]


def test_there_is_no_cross_type_number_anywhere_in_the_result() -> None:
    """plan §0 第 7 條：沒有跨型別合成的數字、沒有 top-N、沒有「最該研究」。"""
    result = run_walk()
    assert set(result) == {"title", "questions", "graph_nodes", "this_is_not", "rules"}
    for q in result["questions"]:
        assert set(q) == {"key", "order", "short", "question", "scope_rule", "hit_rule", "next_action",
                          "hit_n", "scope_n", "judged", "rate", "always_on", "hits", "extra", "absence"}
    line = gw.summary_line(result)
    assert line.count("｜") == 8 and "合計" not in line and "總" not in line


def test_summary_line_prints_zero_and_absence_differently() -> None:
    result = run_walk(reading_rows=[])
    assert "讀圖該重讀 0／0" in gw.summary_line(result)
    result = run_walk(reading_rows=None)
    assert "讀圖該重讀 upstream_unavailable" in gw.summary_line(result)
    # 讀不到 ledger 就不能宣稱「沒人讀過」——第 1 型一起降級，不是 0。
    assert "薄層沒人讀 upstream_unavailable" in gw.summary_line(result)
    assert _q(result, "reading_stale")["hit_n"] is None


def test_query_layer_imports_alpha_only_in_the_graph_walk_composition() -> None:
    """`query/` 不 import `alpha/`；唯一例外是 `graph_walk.collect()`（讀圖狀態的算法住讀圖 provider）。

    空跑檢查：在 `query/structure.py` 加 `from alpha.structure_reading import READING_UNITS` → 這條會紅。
    """
    offenders = []
    for path in (ROOT / "query").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "alpha":
                offenders.append((path.name, node.lineno))
            elif isinstance(node, ast.Import) and any(a.name.split(".")[0] == "alpha" for a in node.names):
                offenders.append((path.name, node.lineno))
    assert [name for name, _ in offenders] == ["graph_walk.py"], offenders
    source = (ROOT / "query" / "graph_walk.py").read_text(encoding="utf-8")
    collect_src = source[source.index("def collect("):source.index("# 呈現")]
    assert "from alpha.providers.structure_readings import reading_status_rows" in collect_src


# ---------------------------------------------------------------------------
# 各型
# ---------------------------------------------------------------------------

def test_thin_sole_and_unfilled_read_the_same_structure_as_query_structure() -> None:
    result = run_walk()
    thin, sole, unfilled = (_q(result, k) for k in ("thin_layer_unread", "sole_supplier_self_reported",
                                                   "supply_unfilled"))
    # 母體：需求側有 sub≥4 的節點（mat:soft 的 sub 2 不在母體）。
    assert thin["scope_n"] == sole["scope_n"] == 3
    assert [h["subject"] for h in thin["hits"]] == ["mat:sole", "mat:thin"]
    assert thin["hits"][1]["suppliers"] == ["co:a", "co:b"]
    assert [h["subject"] for h in sole["hits"]] == ["mat:sole"]
    assert sole["hits"][0]["supplier"] == "co:solo"
    # 未填：母體是需求側 sub≥4 且供給側 ≥1 家；mat:thin 有一條填了 → 不命中。
    assert unfilled["scope_n"] == 3 and [h["subject"] for h in unfilled["hits"]] == ["mat:sole"]


def test_a_current_reading_of_any_unit_takes_a_layer_out_of_thin_layer_unread() -> None:
    readings = fake_readings() + [{"node": "mat:thin", "unit": "layer", "reading_id": "sr_3",
                                   "status": "current", "needs_reread_by_graph": False}]
    assert [h["subject"] for h in _q(run_walk(reading_rows=readings), "thin_layer_unread")["hits"]] == ["mat:sole"]


def test_externally_corroborated_sole_supplier_is_not_asked() -> None:
    edges = fake_graph()
    for e in edges:
        if e.src == "co:solo":
            e.evidence = "externally_corroborated"
    assert _q(run_walk(edges=edges), "sole_supplier_self_reported")["hits"] == []


def test_reading_stale_counts_the_graph_side_only_and_scope_is_current_readings() -> None:
    """watch 那一側（客戶出新文件）是 `fired_reading_reread` 段的事；這裡再算一次就是兩個計數器。"""
    q = _q(run_walk(), "reading_stale")
    assert q["scope_n"] == 2
    assert [(h["subject"], h["unit"]) for h in q["hits"]] == [("prod:supernova", "socket")]
    assert "供給側多一家" in q["hits"][0]["text"]
    assert q["extra"]["withdrawn"] == ["tech:gone（全部單位）"]


def test_lead_not_in_graph_separates_unresolved_names_from_companies_missing_from_the_graph() -> None:
    q = _q(run_walk(), "lead_not_in_graph")
    # 母體：triaged_go／researching 且有具名公司（L_empty 沒有、L_parked 狀態不對）。
    assert q["scope_n"] == 3
    # 首見時間舊的先；co:a 在圖上不算。
    assert [(h["subject"], h["companies"]) for h in q["hits"]] == [("L_old", ["co:amd"]), ("L_new", ["co:iren"])]
    # INV-1：registry 解析不到的名字不算命中，但另列（INV-3）。
    assert q["extra"]["unresolved_names"] == ["CXMT", "co:not_in_registry"]


def test_lead_without_first_seen_sorts_last_and_is_counted_not_backfilled() -> None:
    leads = fake_leads()
    leads["L_nodate"] = {"lead_id": "L_nodate", "status": "triaged_go",
                         "entities": {"company_ids": ["co:iren"], "tickers": []}}
    q = _q(run_walk(leads=leads), "lead_not_in_graph")
    assert q["hits"][-1]["subject"] == "L_nodate" and q["hits"][-1]["first_seen"] is None
    assert q["extra"]["no_first_seen"] == ["L_nodate"]


def test_supplier_no_anchor_scope_is_companies_supplying_downward() -> None:
    q = _q(run_walk(), "supplier_no_anchor")
    # co:a／co:b／co:solo／co:t0..3 供貨進的層都接到錨；co:orphan 供 tech:nowhere，走不到。
    assert q["scope_n"] == 8
    assert [h["subject"] for h in q["hits"]] == ["co:orphan"]


def test_coverage_types_reuse_the_scanner_buckets_and_count_product_noise_separately() -> None:
    result = run_walk()
    no_sup, modelling = _q(result, "no_supplier"), _q(result, "modelling_gap")
    assert [h["subject"] for h in no_sup["hits"]] == ["tech:gap", "tech:isolated"]
    # 孤立節點的下一步不是「誰供應它」。
    assert "先確認它該掛在 stack 哪一層" in no_sup["hits"][1]["text"]
    assert no_sup["extra"]["product_noise"] == ["prod:noise"]
    assert all(h["subject"] != "prod:noise" for h in no_sup["hits"])
    # 母體：非概念的 tech／mat（prod 是抽取副產品、不是題目）。
    assert no_sup["scope_n"] == 4
    assert [h["subject"] for h in modelling["hits"]] == ["tech:npo"] and modelling["scope_n"] == 5


def test_duplicate_type_counts_unmentioned_pairs_only() -> None:
    q = _q(run_walk(), "duplicate_node")
    assert [h["pair"] for h in q["hits"]] == [["tech:eml", "tech:inp_eml"]]
    assert q["scope_n"] == 20 and q["extra"]["registry_mentioned"] == ["tech:x|tech:x_y"]


def test_always_on_is_flagged_only_when_the_scope_is_large_enough() -> None:
    q = _q(run_walk(), "thin_layer_unread")
    assert q["judged"] is False and q["always_on"] is None      # 母體 3 <10：只印不判
    big = _q(run_walk(duplicate_node_total=1), "duplicate_node")
    assert big["judged"] is False
    edges = fake_graph()
    rows = [_row(ANCHOR, "depends_on", f"mat:x{i}", sub=4) for i in range(10)]
    rows += [_row("co:z", "supplies_to", f"mat:x{i}") for i in range(10)]
    q = _q(run_walk(edges=edges + _edges(rows)), "thin_layer_unread")
    assert q["judged"] is True and q["always_on"] is True and q["rate"] >= gw.ALWAYS_ON_RATE
    assert "恆亮" in gw.render_markdown(run_walk(edges=edges + _edges(rows)))


def test_markdown_prints_every_type_even_at_zero() -> None:
    md = gw.render_markdown(run_walk(leads={}, reading_rows=[]))
    for qt in gw.QUESTION_TYPES:
        assert f"（`{qt.key}`）" in md
    assert "lead 點名不在圖（`lead_not_in_graph`）　0／0" in md


@pytest.mark.parametrize("key", gw.QUESTION_TYPE_KEYS)
def test_every_hit_carries_a_subject_and_a_question_sentence(key) -> None:
    for hit in _q(run_walk(), key)["hits"]:
        assert hit["subject"] and hit["text"]
