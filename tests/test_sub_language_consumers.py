"""sub 旗標跟著值走到消費端（Phase 6 Step 6.5；plan 2026-10-02-002 §6）。

守四件事：
1. canonical 邊的旗標＝**贏得 sub 值的那筆** assertion 的旗標——同一條邊另一筆撐得住、但 confidence 較低，仍印贏家那筆的；
   沒有 sub／沒核對 → None（不是 False）。
2. **不進讀圖 digest、不進 staleness 快照列**：只差旗標的兩份圖，result_digest 逐位相同、讀圖 status 仍是 current
   （plan §0 第 6 條：否則字表升版那天每一份讀圖都變 stale，量到的是程式改版不是圖）。
3. 走圖第 1 型命中旁印「需求側 sub≥4 有 M 條，其中引文撐得住 N 條」（沒核對另計）。
4. 個股讀取模型「替代難度」那一格旁註；**只印**：值不變、Q1 不變。
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timezone

from alpha.contracts import EvidenceRef, ScarcityInputs
from alpha.identity import CompanyId, EntityId
from alpha.provider import BottleneckRow
from alpha.testing import FakeGraphResearchProvider
from query.bottleneck import collapse_assertions, structure_table
from query.sub_language import SubLanguage, canonical_sub_language, sub_language_flags

LANG = SubLanguage(version=1, variant="test", terms=("sole supplier", "only qualified", "second source"))


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


def _row(aid, conf, sub, *, src="co:a", dst="mat:x", relation="supplies_to"):
    return {"assertion_id": aid, "src": src, "relation": relation, "dst": dst, "confidence": conf,
            "attributes": json.dumps({"substitutability": sub} if sub is not None else {}),
            "origin": "Some Blog", "source_doc_id": f"d_{aid}"}


# ---------------------------------------------------------------------------
# 1｜旗標跟著值走
# ---------------------------------------------------------------------------

def test_the_flag_is_the_winning_assertions_flag_not_the_prettiest_one() -> None:
    """a1（confidence 0.9、sub 4）的引文沒談可替代性；a2（0.6、sub 5）撐得住——值是 a1 給的，旗標就是 a1 的 False。"""
    rows = [_row("a1", 0.9, 4), _row("a2", 0.6, 5)]
    quotes = {"a1": ["Alpha ships X in volume"], "a2": ["Alpha is the only qualified supplier of X"]}
    flags = sub_language_flags(rows, quotes, language=LANG)
    assert flags == {"a1": False, "a2": True}
    edge = collapse_assertions(rows)[("co:a", "supplies_to", "mat:x")]
    assert (edge.substitutability, edge.sub_assertion_id) == (4, "a1")
    assert canonical_sub_language(edge, flags) is False
    row = structure_table(rows, _Registry(), quotes_by_assertion=quotes, sub_language_flags=flags,
                          sub_language_label=LANG.label)["rows"][0]
    assert (row["substitutability"], row["sub_assertion_id"], row["sub_language_in_quote"]) == (4, "a1", False)
    assert row["assertions_without_sub_language"] == ["a1"]                     # 逐筆清單照留
    # 反過來：贏家撐得住 → True（另一筆撐不住也不影響）
    flipped = [_row("a1", 0.5, 4), _row("a2", 0.6, 5)]
    edge = collapse_assertions(flipped)[("co:a", "supplies_to", "mat:x")]
    assert (edge.sub_assertion_id, canonical_sub_language(edge, flags)) == ("a2", True)


def test_no_sub_or_no_check_is_none_not_false() -> None:
    rows = [_row("a1", 0.9, None)]
    quotes = {"a1": ["Alpha ships X"]}
    flags = sub_language_flags(rows, quotes, language=LANG)
    edge = collapse_assertions(rows)[("co:a", "supplies_to", "mat:x")]
    assert flags == {} and canonical_sub_language(edge, flags) is None            # 沒有 sub：沒有旗標
    with_sub = collapse_assertions([_row("a2", 0.9, 4)])[("co:a", "supplies_to", "mat:x")]
    assert canonical_sub_language(with_sub, None) is None                         # 沒核對：不是 False
    table = structure_table([_row("a2", 0.9, 4)], _Registry(), quotes_by_assertion={})
    assert table["rows"][0]["sub_language_in_quote"] is None and table["sub_language"] is None


# ---------------------------------------------------------------------------
# 2｜不進讀圖 digest、不進 staleness 快照列
# ---------------------------------------------------------------------------

def _structure_with_flag(flag):
    from query.structure import build_structure

    rows = [_row("d1", 0.9, 5, src="tech:module", dst="mat:x", relation="depends_on"),
            _row("s1", 0.8, 3, src="co:a", dst="mat:x")]
    edges = list(collapse_assertions(rows).values())
    for edge in edges:
        edge.evidence = "needs_review"
        edge.sub_language_in_quote = flag if edge.substitutability is not None else None
    return build_structure("mat:x", edges)


def test_the_flag_never_reaches_the_reading_digest_or_snapshot_rows() -> None:
    from alpha.providers.structure_readings import evidence_rank
    from alpha.structure_reading.contracts import parse_structure_reading_record, structure_reading_record
    from alpha.structure_reading.staleness import reading_status

    before, after = _structure_with_flag(None), _structure_with_flag(False)
    assert before.result_digest() == after.result_digest()
    rows = after.as_dict()["angles"]["supply_side"]
    assert rows[0]["sub_language_in_quote"] is False                              # 邊的輸出帶旗標（給人看）
    record = structure_reading_record(
        node="mat:x", structure=before.as_dict(), unit="layer", kind="undecided",
        reading="測試：只差旗標的兩份圖，讀圖不得因此變 stale。", expires=date(2026, 12, 31),
        created_at=datetime(2026, 10, 3, tzinfo=timezone.utc), author="test")
    assert all(len(row) == 7 for rows in record["angles"].values() for row in rows)   # 快照列只有七格
    status = reading_status(parse_structure_reading_record(record), after.as_dict(), today=date(2026, 10, 3),
                            evidence_rank=evidence_rank())
    assert status["status"] == "current" and not status["changes"]


# ---------------------------------------------------------------------------
# 3｜走圖第 1 型旁註
# ---------------------------------------------------------------------------

def test_thin_layer_hits_say_how_many_demand_quotes_hold_up() -> None:
    from query.graph_walk import demand_quote_note, layer_questions

    rows = [_row("d1", 0.9, 5, src="tech:module", dst="mat:x", relation="depends_on"),
            _row("d2", 0.9, 4, src="tech:board", dst="mat:x", relation="depends_on"),
            _row("d3", 0.9, 4, src="tech:other", dst="mat:x", relation="depends_on"),
            _row("s1", 0.8, None, src="co:a", dst="mat:x")]
    edges = list(collapse_assertions(rows).values())
    flags = {"tech:module": True, "tech:board": False, "tech:other": None}
    for edge in edges:
        edge.evidence = "needs_review"
        edge.sub_language_in_quote = flags.get(edge.src)
    hit = layer_questions(edges, read_nodes=())["thin_layer_unread"]["hits"][0]
    assert hit["subject"] == "mat:x" and hit["demand_quote"] == {"n": 3, "held": 1, "unchecked": 1}
    assert hit["demand_quote_note"] == "需求側 sub≥4 有 3 條，其中引文撐得住 1 條、1 條沒核對"
    assert demand_quote_note(2, 2, 0) == "需求側 sub≥4 有 2 條，其中引文撐得住 2 條"


# ---------------------------------------------------------------------------
# 4｜個股讀取模型「替代難度」旁註：只印，值與 Q1 不變
# ---------------------------------------------------------------------------

class _FlagProvider(FakeGraphResearchProvider):
    quote_supported: bool | None = None

    def get_bottlenecks(self, *, min_substitutability=4, as_of=None):
        refs = self._evidence(as_of)
        return (BottleneckRow(
            company_id=self.company_id, edge_key="edge:flag", relation="supplies_to",
            target_id=EntityId("co:nvidia"),
            inputs=ScarcityInputs(substitutability=5, substitutability_quote_supported=self.quote_supported,
                                  sole_source=True, qualification_status="qualified", evidence=refs),
            demand_anchor=EntityId("tech:ai_switch"), evidence=refs,
        ),)


def _view_with(flag):
    from alpha.context import build_research_context
    from alpha.identity import Ticker
    from briefing.alpha_view import build_alpha_investment_view
    from tests.test_alpha_investment_view import _FakeFundamentals

    provider = _FlagProvider(company_id=CompanyId("co:coherent"))
    provider.quote_supported = flag
    build = build_research_context(ticker=Ticker("COHR"), company_id=CompanyId("co:coherent"),
                                   graph_provider=provider, fundamentals_provider=_FakeFundamentals())
    return build_alpha_investment_view(build=build, today=date(2026, 10, 3))


def test_the_substitutability_cell_carries_the_note_but_the_value_and_q1_do_not_move() -> None:
    from alpha.context import structural_score

    views = {flag: _view_with(flag) for flag in (None, True, False)}
    cells = {flag: next(d for d in v.structural_thesis.scarcity_inputs if d.key == "substitutability")
             for flag, v in views.items()}
    assert {cell.value for cell in cells.values()} == {5}                        # 值照印
    assert cells[None].reason is None                                            # 沒核對：不寫任何字
    assert "沒有在談可替代性" in cells[False].reason and "有在談可替代性" in cells[True].reason
    ref = EvidenceRef(ref="graph://edge/x", kind="graph_edge", evidence_class="externally_corroborated",
                      evidence_tier=1)
    base = ScarcityInputs(substitutability=5, sole_source=True, evidence=(ref,))
    scores = {flag: structural_score(replace(base, substitutability_quote_supported=flag))[0].declared
              for flag in (None, True, False)}
    assert len(set(scores.values())) == 1                                        # Q1 不看旗標（只印不放閘）
