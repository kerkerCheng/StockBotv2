"""F19（2026-11-04）：人工核准的屬性決議要走到讀圖、走圖與結構表。

三者共用唯一的收斂點 `query.bottleneck.collapse_assertions`；它原本逐文件取最高 confidence、不讀決議——
真資料 24 個核准決議裡 9 個印出來的和決議不同（brainstorm 2026-10-28 F19；同一條邊兩個值、下游各讀一個，L12）。
決議值怎麼來的判定只有一份（`query.edge_conflicts.build_edge_states`＋`loader.edge_resolution.build_projection`），
這裡守的是「讀圖這一側真的拿到它」，以及 as-of 視角不偷看之後才核准的決議（INV-6）。
全部離線（不連 Neo4j）。
"""
from __future__ import annotations

import json
from datetime import date

import pytest

import query.bottleneck as qb
from loader.edge_resolution import ResolutionValidationError
from loader.load_to_neo4j import edge_key
from query.bottleneck import (
    AS_OF_ROW_KEY, approved_resolutions, collapse_assertions, project_assertions_as_of, structure_table,
)
from query.edge_conflicts import _candidate_set_hash, conflict_id
from query.structure import build_structure, render_markdown

from test_structure_table import _FakeRegistry

SRC, REL, DST = "co:maker", "supplies_to", "tech:layer"
KEY = edge_key(SRC, REL, DST)
TRIPLE = (SRC, REL, DST)


def _row(aid: str, sub, conf: float, *, published: str = "2026-06-01") -> dict:
    return {"src": SRC, "relation": REL, "dst": DST, "attributes": json.dumps({"substitutability": sub}),
            "confidence": conf, "assertion_id": aid, "source_ids": [f"{aid}_s1"], "source_doc_id": f"doc_{aid}",
            "published_at": published, "origin": SRC}


def _resolution(rows, *, action: str = "choose_value", value=None, supporting=(), rejected=(),
                approved_at: str = "2026-09-10T10:00:00+08:00", key: str = KEY, sources=None) -> dict:
    """照 `_validate_decision_against_conflict` 的規則組一份決議（候選集合雜湊與真的 detector 同一個函式算）。
    `sources` 不給＝每筆支持的 assertion 取 `<id>_s1`（`_row` 的來源 id）。"""
    candidates = [{"assertion_id": r["assertion_id"], "value": json.loads(r["attributes"])["substitutability"]}
                  for r in rows]
    cid = conflict_id(key, "substitutability")
    digest = _candidate_set_hash(candidates)
    return {cid: {
        "schema_version": "1", "resolution_id": f"resolution_{cid.removeprefix('conflict_')}_{digest[:12]}",
        "conflict_id": cid, "edge_key": key, "attribute": "substitutability", "candidate_set_hash": digest,
        "action": action, "selected_value": value if action == "choose_value" else None,
        "supporting_assertion_ids": list(supporting), "rejected_assertion_ids": list(rejected),
        "supporting_source_ids": list(sources) if sources is not None else [f"{a}_s1" for a in supporting],
        "rationale": "測試用決議", "resolved_confidence": 0.8, "approved_by": "tester", "approved_at": approved_at,
    }}


def test_approved_value_beats_the_highest_confidence_and_the_sub_flag_follows_it() -> None:
    """核准選 4，即使最高 confidence 那份說 5——讀圖要印 4，sub 旗標也要跟著「給出 4 的那幾份」裡最可信的一份。"""
    rows = [_row("a1", 5, 0.9), _row("a2", 4, 0.6), _row("a3", 4, 0.7)]
    res = _resolution(rows, value=4, supporting=("a2", "a3"), rejected=("a1",))

    before = collapse_assertions(rows, resolutions={})[TRIPLE]
    assert (before.substitutability, before.sub_assertion_id, before.resolved) == (5, "a1", {})

    after = collapse_assertions(rows, resolutions=res)[TRIPLE]
    assert after.substitutability == 4
    assert after.sub_assertion_id == "a3"
    assert after.resolved == {"substitutability": "choose_value"}
    assert after.documents == 3, "決議只改值，不改份數"


def test_a_decision_not_to_give_a_value_prints_no_value_and_says_why() -> None:
    """`unknown`：值是 None，但不得印成「—」（那是「沒有文件發言過」）——讀圖表與結構表都要說是決議判的。"""
    rows = [_row("a1", 5, 0.9), _row("a2", 3, 0.6)]
    res = _resolution(rows, action="unknown")

    edge = collapse_assertions(rows, resolutions=res)[TRIPLE]
    assert (edge.substitutability, edge.sub_assertion_id, edge.resolved) == (None, None, {"substitutability": "unknown"})

    view = build_structure(DST, [edge])
    assert view.angles["supply_side"][0].as_dict()["resolved"] == {"substitutability": "unknown"}
    assert "核准決議不給值（unknown）" in render_markdown(view)

    table = structure_table(rows, _FakeRegistry(), quotes_by_assertion={}, resolutions=res)
    (row,) = table["rows"]
    assert row["substitutability"] is None
    assert row["resolved_attributes"] == {"substitutability": "unknown"}


def test_a_decision_whose_candidate_set_changed_is_not_applied() -> None:
    """新證據進來（候選集合變了）決議就過期：照舊逐文件取最高 confidence，不拿舊決議蓋新證據。"""
    rows = [_row("a1", 5, 0.9), _row("a2", 4, 0.6)]
    res = _resolution(rows, value=4, supporting=("a2",), rejected=("a1",))
    edge = collapse_assertions([*rows, _row("a3", 2, 0.5)], resolutions=res)[TRIPLE]
    assert (edge.substitutability, edge.resolved) == (5, {})


def test_as_of_view_only_applies_decisions_approved_by_that_day() -> None:
    """兩份文件 6 月就在，決議 9-10 才核准：8-01 的 as-of 讀圖不得看到 9-10 的決議（INV-6）。
    呼叫端就算把整包決議傳進來也一樣——日期跟著列走，不靠呼叫端記得篩。"""
    rows = [_row("a1", 5, 0.9, published="2026-06-01"), _row("a2", 4, 0.6, published="2026-06-02")]
    res = _resolution(rows, value=4, supporting=("a2",), rejected=("a1",))

    early = project_assertions_as_of(rows, date(2026, 8, 1))
    assert all(r[AS_OF_ROW_KEY] == date(2026, 8, 1) for r in early.rows)
    assert AS_OF_ROW_KEY not in rows[0], "投影給的是副本，不改傳進來的列（當前視角與 as-of 共用快取）"
    assert collapse_assertions(early.rows, resolutions=res)[TRIPLE].substitutability == 5

    late = project_assertions_as_of(rows, date(2026, 9, 30))
    assert collapse_assertions(late.rows, resolutions=res)[TRIPLE].substitutability == 4
    assert collapse_assertions(rows, resolutions=res)[TRIPLE].substitutability == 4, "當前視角照套"


def test_the_marker_alone_does_not_move_the_reading_digest() -> None:
    """決議選的剛好就是最高 confidence 那個值：值沒變，讀圖的 digest 也不得變（標記不進 digest）。"""
    rows = [_row("a1", 5, 0.9), _row("a2", 4, 0.6)]
    res = _resolution(rows, value=5, supporting=("a1",), rejected=("a2",))
    with_marker = build_structure(DST, [collapse_assertions(rows, resolutions=res)[TRIPLE]])
    without = build_structure(DST, [collapse_assertions(rows, resolutions={})[TRIPLE]])
    assert with_marker.angles["supply_side"][0].resolved == {"substitutability": "choose_value"}
    assert with_marker.result_digest() == without.result_digest()


def test_the_default_reads_the_approved_resolutions(monkeypatch) -> None:
    """不給 `resolutions` 的呼叫端（讀圖、走圖、結構表、物化都是）也要拿到決議——預設讀 `library/resolutions` 現值。"""
    rows = [_row("a1", 5, 0.9), _row("a2", 4, 0.6)]
    res = _resolution(rows, value=4, supporting=("a2",), rejected=("a1",))
    monkeypatch.setattr(qb, "approved_resolutions", lambda *a, **k: res)
    assert collapse_assertions(rows)[TRIPLE].substitutability == 4
    assert structure_table(rows, _FakeRegistry(), quotes_by_assertion={})["rows"][0]["substitutability"] == 4


def test_resolution_files_are_read_through_the_schema_and_fail_closed(tmp_path) -> None:
    """讀法只有 `load_resolutions` 一份（驗 schema、檔名要等於 conflict_id）。壞掉就丟例外——不靜默退回取最高 confidence。"""
    rows = [_row("a1", 5, 0.9), _row("a2", 4, 0.6)]
    res = _resolution(rows, value=4, supporting=("a2",), rejected=("a1",))
    (cid, body), = res.items()
    (tmp_path / f"{cid}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")

    loaded = approved_resolutions(tmp_path)
    assert set(loaded) == {cid}
    assert collapse_assertions(rows, resolutions=loaded)[TRIPLE].substitutability == 4
    assert approved_resolutions(tmp_path / "沒有這個目錄") == {}

    broken = dict(body)
    del broken["rationale"]
    (tmp_path / f"{cid}.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ResolutionValidationError):
        approved_resolutions(tmp_path)


# ---------------------------------------------------------------------------
# 2026-11-05 R2 條件與非阻斷（使用者「照審查建議修，條件二選 b」）
# ---------------------------------------------------------------------------

def test_redeclaring_a_document_that_holds_a_supporting_assertion_keeps_the_decision() -> None:
    """R2 F1：更正走廊重宣告同一份文件（值不變），入圖預告重建的列要帶 `source_ids`——少了它，決議核對支持的來源 id
    時對不到，「證據等級預告」「圖影響」就降成讀不到。"""
    from loader.load_to_neo4j import evidence_id
    from loader.merge_side_effects import rows_after_load

    a1, a2 = evidence_id("doc_one", "e1"), evidence_id("doc_two", "e1")
    rows = [{**_row(a1, 5, 0.9), "source_doc_id": "doc_one", "source_ids": ["doc_one_s1"]},
            {**_row(a2, 4, 0.6), "source_doc_id": "doc_two", "source_ids": ["doc_two_s1"]}]
    res = _resolution(rows, value=4, supporting=(a2,), rejected=(a1,), sources=("doc_two_s1",))
    redeclared = {"source_doc": {"doc_id": "doc_two", "origin_entity": SRC, "source_type": "filing",
                                 "published_at": "2026-06-01"},
                  "sources": [{"id": "doc_two_s1", "quote": "逐字"}],
                  "edges": [{"id": "e1", "src_id": SRC, "relation": REL, "dst_id": DST,
                             "attributes": {"substitutability": 4}, "confidence": 0.6, "source_ids": ["doc_two_s1"]}]}

    after, _quotes = rows_after_load(rows, {}, {}, [redeclared])
    assert next(r for r in after if r["assertion_id"] == a2)["source_ids"] == ["doc_two_s1"]
    edge = collapse_assertions(after, resolutions=res)[TRIPLE]
    assert (edge.substitutability, edge.resolved) == (4, {"substitutability": "choose_value"})


def _other_edge_rows():
    other = ("co:other", REL, DST)
    rows = [{**_row(f"b{i}", sub, conf), "src": "co:other"} for i, (sub, conf) in enumerate([(5, 0.9), (2, 0.6)], 1)]
    return other, rows, _resolution(rows, value=2, supporting=("b2",), rejected=("b1",), key=edge_key(*other))


def test_an_invalid_decision_is_isolated_to_its_own_cell_and_named() -> None:
    """R2 F2(b)（使用者 11-05 選）：雜湊相符、支持的來源 id 卻對不到（[841] 那種更正拿掉一個引用）——只有那一格標
    「決議失效、待重核」、不給值（不印未驗證的值、也不退回被否決的最高 confidence），別條邊的決議照套、不丟例外。"""
    from loader.edge_resolution import build_projection, invalid_resolutions
    from query.edge_conflicts import build_edge_states

    rows = [_row("a1", 5, 0.9), _row("a2", 4, 0.6)]
    broken = _resolution(rows, value=4, supporting=("a2",), rejected=("a1",), sources=("a2_s9",))
    other, other_rows, fine = _other_edge_rows()

    edges = collapse_assertions([*rows, *other_rows], resolutions={**broken, **fine})
    assert (edges[TRIPLE].substitutability, edges[TRIPLE].sub_assertion_id, edges[TRIPLE].resolved) == (
        None, None, {"substitutability": "invalid"})
    assert (edges[other].substitutability, edges[other].resolved) == (2, {"substitutability": "choose_value"})
    # 格子標籤只有一份（讀圖表與結構表共用）；分布那一行也會出現同一串字，所以直接驗格子
    assert [qb.resolved_cell("5/5", a) for a in (None, "choose_value", "unknown", "invalid")] == [
        "5/5", "5/5（核准）", "核准決議不給值（unknown）", "決議失效、待重核"]
    assert "決議失效、待重核" in render_markdown(build_structure(DST, edges.values()))

    states = build_edge_states([{"id": r["assertion_id"], "edge_key": edge_key(r["src"], r["relation"], r["dst"]),
                                 "src_id": r["src"], "relation": r["relation"], "dst_id": r["dst"],
                                 "attributes": json.loads(r["attributes"]), "confidence": r["confidence"],
                                 "source_ids": r["source_ids"], "source_doc_id": r["source_doc_id"],
                                 "origin_entity": r["origin"], "evidence_tier": None,
                                 "published_at": r["published_at"]} for r in [*rows, *other_rows]])
    (named,) = invalid_resolutions(states, {**broken, **fine})
    assert (named["edge_key"], named["attribute"], named["status"]) == (KEY, "substitutability", "invalid")
    assert "a2_s9" in named["error"]
    with pytest.raises(ResolutionValidationError):        # 寫圖那一側照舊整批停（project_graph／project_edge_keys）
        build_projection(states, {**broken, **fine})


def test_a_gap_decided_by_a_resolution_is_not_counted_as_unfilled() -> None:
    """R2 F3：值是 None 的分三種說——沒有文件發言過（未填）、核准決議判不給值、決議失效；結構表 CLI 與供給側分布
    不得把後兩種併回「未填」。"""
    from query.structure import _sub_distribution

    rows = [_row("a1", 5, 0.9), _row("a2", 3, 0.6)]
    withheld = collapse_assertions(rows, resolutions=_resolution(rows, action="unknown"))[TRIPLE]
    plain = collapse_assertions([{**_row("c1", None, 0.5), "src": "co:plain"}], resolutions={})[("co:plain", REL, DST)]
    other, other_rows, fine = _other_edge_rows()
    valued = collapse_assertions(other_rows, resolutions=fine)[other]
    supply = build_structure(DST, [withheld, plain, valued]).angles["supply_side"]
    assert _sub_distribution(supply) == "2｜另有 1 條未填｜1 條核准決議不給值"
    assert _sub_distribution([e for e in supply if e.src == SRC]) == "（沒有值）｜1 條核准決議不給值"
    assert _sub_distribution([e for e in supply if e.src == "co:plain"]) == "（都沒填）｜另有 1 條未填"

    table = structure_table(rows, _FakeRegistry(), quotes_by_assertion={},
                            resolutions=_resolution(rows, action="unknown"))
    assert "核准決議不給值（unknown）" in qb.render_markdown(table)


def test_a_confidence_tie_gives_the_sub_flag_to_the_first_row() -> None:
    """R2 F4（M2）：給出核准值的幾筆 confidence 同分時，sub 旗標給先到的那筆（與收斂同一條規則）。"""
    rows = [_row("a1", 5, 0.9), _row("a2", 4, 0.7), _row("a3", 4, 0.7)]
    res = _resolution(rows, value=4, supporting=("a2", "a3"), rejected=("a1",))
    assert collapse_assertions(rows, resolutions=res)[TRIPLE].sub_assertion_id == "a2"


def test_rows_with_different_as_of_marks_use_the_earliest_day() -> None:
    """R2 F4（M3）：一批列帶不同的 as-of 標記時取最早那天——保守的那一邊，不讓較晚的標記把之後才核准的決議帶進來。"""
    rows = [{**_row("a1", 5, 0.9), AS_OF_ROW_KEY: date(2026, 8, 1)},
            {**_row("a2", 4, 0.6), AS_OF_ROW_KEY: date(2026, 9, 30)}]
    res = _resolution(rows, value=4, supporting=("a2",), rejected=("a1",))
    assert collapse_assertions(rows, resolutions=res)[TRIPLE].substitutability == 5


def test_a_decision_approved_on_the_as_of_day_is_known_that_day() -> None:
    """R2 F4（M7）：核准當天就算已知（台北日期；`approved_at` 帶時區）。"""
    rows = [_row("a1", 5, 0.9, published="2026-06-01"), _row("a2", 4, 0.6, published="2026-06-02")]
    res = _resolution(rows, value=4, supporting=("a2",), rejected=("a1",), approved_at="2026-09-10T10:00:00+08:00")
    on_day = project_assertions_as_of(rows, date(2026, 9, 10))
    assert collapse_assertions(on_day.rows, resolutions=res)[TRIPLE].substitutability == 4
    day_before = project_assertions_as_of(rows, date(2026, 9, 9))
    assert collapse_assertions(day_before.rows, resolutions=res)[TRIPLE].substitutability == 5
