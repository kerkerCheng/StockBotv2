"""結構表逐列需求錨（Phase 6 Step 6.7a；plan 2026-10-02-002 §8 a，Phase 5 #27）。

守四件事：
1. 每列先從**這一列的瓶頸節點**往上走，走不到才退回公司，列上標 `anchor_basis`（row／company；兩邊都走不到＝None）。
   「有錨」的列只會多不會少（2026-09-18 的教訓：只從節點走會讓一批列失去錨——退回公司那一步就是為它留的）。
2. 退回公司的那一格印「公司層」：markdown、APP artifact（字彙與讀法跟著資料走，L16）、心跳「前三錨」那一行。
3. 錨的來處跟著值走到 provider 與個股頁（`ScarcityInputs.demand_anchor_basis`、`StructuralEdgeItem`）：
   不帶 basis 的消費端就是一格承載兩種問題（L12）。
4. 個股頁 builder 不得 import `query`，所以它的白話對照與 `ANCHOR_BASIS` 的 key 集合由本檔守著相同。
"""
from __future__ import annotations

import copy
import json
from datetime import date

from alpha.contracts import ScarcityInputs, StructuralContext
from alpha.identity import CompanyId, EntityId
from alpha.provider import BottleneckRow
from alpha.testing import FakeGraphResearchProvider
from query.bottleneck import (
    ANCHOR_BASIS, ANCHOR_COLUMN_NOTE, build_upward_index, collapse_assertions, demand_chain, render_markdown,
    structure_table,
)


class _Registry:
    companies = ()

    def company_id_for_ticker(self, ticker):
        return None

    def has_company(self, cid):
        return False

    def research_ticker(self, cid):
        return None

    def company(self, cid):
        return None


def _row(src, rel, dst, *, sub=None):
    return {"src": src, "relation": rel, "dst": dst, "confidence": 0.9,
            "attributes": json.dumps({"substitutability": sub} if sub is not None else {}), "origin": None}


#: 夾具圖（`tech:ai_switch` 是登記的需求錨）：
#:   axt supplies_to coherent（節點 coherent 自己接得到錨 → row，1 跳）
#:   axt supplies_to apple（apple 是需求終點、沒人記過誰需要它 → 退回公司 axt → company，2 跳）
#:   axt depends_on gallium（gallium 被 axt 需要，經公司自己往上 → row，3 跳；錨與公司層相同、跳數多一）
#:   nvidia supplies_to island（兩邊都走不到 → 沒有錨、basis None）
ROWS = [
    _row("co:axt", "supplies_to", "co:coherent", sub=5),
    _row("co:axt", "supplies_to", "co:apple", sub=4),
    _row("co:axt", "depends_on", "mat:gallium", sub=3),
    _row("co:coherent", "is_component_of", "tech:ai_switch"),
    _row("co:nvidia", "supplies_to", "co:island", sub=4),
]


def _table():
    return structure_table(ROWS, _Registry(), quotes_by_assertion={})


def _by_node(result):
    return {r["bottleneck"]: r for r in result["rows"]}


# ---------------------------------------------------------------------------
# 1｜先節點、後公司；有錨的列只多不少
# ---------------------------------------------------------------------------

def test_each_row_walks_from_its_own_bottleneck_first_and_falls_back_to_the_company() -> None:
    rows = _by_node(_table())
    assert (rows["co:coherent"]["chain"], rows["co:coherent"]["anchor_basis"]) == (
        ["tech:ai_switch", "co:coherent"], "row")
    assert rows["co:coherent"]["demand_hops"] == 1
    # apple 走不到 → 退回公司：鏈的終點是公司 axt，不是 apple
    assert (rows["co:apple"]["chain"], rows["co:apple"]["anchor_basis"]) == (
        ["tech:ai_switch", "co:coherent", "co:axt"], "company")
    assert rows["co:apple"]["demand_hops"] == 2
    # depends_on 的節點經由公司自己往上：節點自己接得到（row），跳數比公司層多一
    assert (rows["mat:gallium"]["chain"], rows["mat:gallium"]["anchor_basis"]) == (
        ["tech:ai_switch", "co:coherent", "co:axt", "mat:gallium"], "row")
    # 兩邊都走不到：沒有錨，basis 是 None（不是第三個值）
    assert (rows["co:island"]["demand_anchor"], rows["co:island"]["anchor_basis"],
            rows["co:island"]["demand_hops"]) == (None, None, None)


def test_rows_with_an_anchor_never_decrease_against_the_company_side_walk() -> None:
    """09-18 的教訓：改前（一律從公司走）有錨的每一列，改後都還有錨。"""
    result = _table()
    edges = list(collapse_assertions(ROWS).values())
    upward = build_upward_index(edges)
    for row in result["rows"]:
        if demand_chain(row["company_id"], upward):
            assert row["demand_anchor"], row
    before = sum(1 for r in result["rows"] if demand_chain(r["company_id"], upward))
    after = sum(1 for r in result["rows"] if r["demand_anchor"])
    assert after >= before


def test_the_same_company_can_now_carry_different_anchors_per_row() -> None:
    """改前同一家公司的每一列印同一個錨（Lam 的 9 列）；改後每列答自己的節點——鏈不同、跳數不同。"""
    axt = [r for r in _table()["rows"] if r["company_id"] == "co:axt"]
    assert len({tuple(r["chain"]) for r in axt}) == 3
    assert sorted(r["demand_hops"] for r in axt) == [1, 2, 3]


# ---------------------------------------------------------------------------
# 2｜「公司層」印在退回的那一格：markdown、artifact、心跳
# ---------------------------------------------------------------------------

def test_markdown_marks_only_the_fallback_cells_and_carries_the_reading() -> None:
    text = render_markdown(_table())
    assert "需求錨（逐列）" in text and "公司側需求錨" not in text
    assert ANCHOR_COLUMN_NOTE in text
    table_lines = [line for line in text.splitlines() if line.startswith("| co:")]
    apple = [line for line in table_lines if "co:apple" in line]
    others = [line for line in table_lines if "co:apple" not in line]
    assert apple and apple[0].rstrip().endswith("tech:ai_switch（公司層） |")
    assert all("公司層" not in line for line in others)
    assert "（距需求端 2 跳；公司層）" in text and "（距需求端 1 跳）" in text


def test_artifact_carries_the_basis_vocabulary_reading_and_identity() -> None:
    from webapp.materialize import build_structure_table_artifact

    result = _table()
    payload = build_structure_table_artifact(result, registry=_Registry())
    assert payload["vocab"]["anchor_basis"] == dict(ANCHOR_BASIS)
    assert payload["notes"]["anchor_column"] == ANCHOR_COLUMN_NOTE
    rows = {r["bottleneck"]: r for r in payload["rows"]}
    assert rows["co:apple"]["anchor_basis"] == "company"
    assert rows["co:apple"]["anchor_basis_label"] == ANCHOR_BASIS["company"]
    assert rows["co:coherent"]["anchor_basis_label"] == ANCHOR_BASIS["row"]
    assert rows["co:island"]["anchor_basis_label"] is None
    # 同一個錨、來處不同 → 認知變了（freshness identity 不同）
    flipped = copy.deepcopy(result)
    for row in flipped["rows"]:
        if row["bottleneck"] == "co:coherent":
            row["anchor_basis"] = "company"
    assert build_structure_table_artifact(flipped, registry=_Registry())["freshness_identity"] != (
        payload["freshness_identity"])


def _anchor_line(state_dir):
    import crons.heartbeat as hb

    section = hb.build_positions(state_dir=state_dir)
    lines = [line for line in section.lines if "個需求錨" in line]
    assert len(lines) == 1, section.lines
    return lines[0]


def test_heartbeat_anchor_line_counts_the_company_level_rows(tmp_path) -> None:
    from webapp.materialize import build_structure_table_artifact
    from webapp.store import StateArtifactStore

    StateArtifactStore(tmp_path).write(build_structure_table_artifact(_table(), registry=_Registry()))
    line = _anchor_line(tmp_path)
    assert "結構表 4 條邊" in line and "公司層 1 列" in line, line


def test_heartbeat_does_not_print_zero_company_rows_for_an_artifact_older_than_the_change(tmp_path) -> None:
    """舊 artifact 的列上沒有 `anchor_basis`：照實說錨是公司側，不印成「公司層 0 列」（成功與失敗不同形，L13）。"""
    from webapp.contracts import canonical_digest
    from webapp.materialize import build_structure_table_artifact
    from webapp.store import StateArtifactStore

    payload = build_structure_table_artifact(_table(), registry=_Registry())
    for row in payload["rows"]:
        row.pop("anchor_basis")
        row.pop("anchor_basis_label")
    payload.pop("content_digest")
    payload["content_digest"] = canonical_digest(payload)
    StateArtifactStore(tmp_path).write(payload)
    line = _anchor_line(tmp_path)
    assert "錨是公司側（artifact 早於逐列錨）" in line and "公司層 0 列" not in line, line


# ---------------------------------------------------------------------------
# 3｜來處跟著值走到 provider 與個股頁
# ---------------------------------------------------------------------------

def test_provider_carries_the_basis_into_q1_inputs_and_the_edge_list() -> None:
    from alpha.providers.graph_neo4j import Neo4jGraphResearchProvider

    provider = Neo4jGraphResearchProvider(driver=object(), registry=_Registry(), _assertion_rows=list(ROWS),
                                          _quotes_by_assertion={})
    rows = {str(r.target_id): r for r in provider.get_bottlenecks()}
    assert rows["co:apple"].inputs.demand_anchor_basis == "company"
    assert rows["co:apple"].inputs.dependency_depth == 2
    assert rows["co:coherent"].inputs.demand_anchor_basis == "row"
    edges = {e["target"]: e for e in provider.get_company_structural_context(CompanyId("co:axt")).edges}
    assert edges["co:apple"]["demand_anchor_basis"] == "company"
    assert edges["co:coherent"]["demand_anchor_basis"] == "row"


class _BasisProvider(FakeGraphResearchProvider):
    basis: str | None = None

    def get_bottlenecks(self, *, min_substitutability=4, as_of=None):
        refs = self._evidence(as_of)
        return (BottleneckRow(
            company_id=self.company_id, edge_key="edge:basis", relation="supplies_to",
            target_id=EntityId("co:apple"),
            inputs=ScarcityInputs(substitutability=5, sole_source=True, qualification_status="qualified",
                                  dependency_depth=2, demand_anchor=EntityId("tech:ai_switch"),
                                  demand_anchor_basis=self.basis, evidence=refs),
            demand_anchor=EntityId("tech:ai_switch"), evidence=refs,
        ),)

    def get_company_structural_context(self, company_id, *, as_of=None):
        refs = self._evidence(as_of)
        return StructuralContext(
            company_id=company_id,
            edges=({"relation": "supplies_to", "target": "co:apple", "substitutability": 5, "sole_source": True,
                    "qualification_status": "qualified", "demand_anchor": "tech:ai_switch", "demand_hops": 2,
                    "demand_anchor_basis": self.basis, "evidence_class": "self_reported"},),
            claims=(), counter_paths=(), evidence=refs,
        )


def _view_with(basis):
    from alpha.context import build_research_context
    from alpha.identity import Ticker
    from briefing.alpha_view import build_alpha_investment_view
    from tests.test_alpha_investment_view import _FakeFundamentals

    provider = _BasisProvider(company_id=CompanyId("co:axt"))
    provider.basis = basis
    build = build_research_context(ticker=Ticker("AXTI"), company_id=CompanyId("co:axt"),
                                   graph_provider=provider, fundamentals_provider=_FakeFundamentals())
    return build_alpha_investment_view(build=build, today=date(2026, 10, 3))


def test_stock_page_anchor_cells_say_company_level_only_for_the_fallback() -> None:
    from briefing.alpha_view.builder import ANCHOR_BASIS_NOTE
    from briefing.alpha_view.render import render_alpha_investment_view_markdown

    for basis in ("row", "company", None):
        view = _view_with(basis)
        cells = {d.key: d for d in view.structural_thesis.scarcity_inputs}
        expected = ANCHOR_BASIS_NOTE.get(str(basis or ""))
        assert cells["demand_anchor"].reason == expected and cells["dependency_depth"].reason == expected
        assert cells["demand_anchor"].value == "tech:ai_switch" and cells["dependency_depth"].value == 2  # 值照印
        edge = view.structural_thesis.edges[0]
        assert edge.demand_anchor_basis == basis
        text = render_alpha_investment_view_markdown(view)
        edge_line = next(line for line in text.splitlines() if line.startswith("| supplies") and "co:apple" in line)
        assert ("／2（公司層）" in edge_line) == (basis == "company"), edge_line   # markdown 會把 `_` 跳脫成 `\_`
    assert "公司層" in ANCHOR_BASIS_NOTE["company"] and ANCHOR_BASIS_NOTE["row"] is None


# ---------------------------------------------------------------------------
# 4｜白話對照與 SSOT 的 key 集合相同
# ---------------------------------------------------------------------------

def test_stock_page_basis_notes_cover_exactly_the_bottleneck_vocabulary() -> None:
    from briefing.alpha_view.builder import ANCHOR_BASIS_NOTE

    assert set(ANCHOR_BASIS_NOTE) == set(ANCHOR_BASIS)
