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
                approved_at: str = "2026-09-10T10:00:00+08:00") -> dict:
    """照 `_validate_decision_against_conflict` 的規則組一份決議（候選集合雜湊與真的 detector 同一個函式算）。"""
    candidates = [{"assertion_id": r["assertion_id"], "value": json.loads(r["attributes"])["substitutability"]}
                  for r in rows]
    cid = conflict_id(KEY, "substitutability")
    digest = _candidate_set_hash(candidates)
    return {cid: {
        "schema_version": "1", "resolution_id": f"resolution_{cid.removeprefix('conflict_')}_{digest[:12]}",
        "conflict_id": cid, "edge_key": KEY, "attribute": "substitutability", "candidate_set_hash": digest,
        "action": action, "selected_value": value if action == "choose_value" else None,
        "supporting_assertion_ids": list(supporting), "rejected_assertion_ids": list(rejected),
        "supporting_source_ids": [f"{a}_s1" for a in supporting], "rationale": "測試用決議",
        "resolved_confidence": 0.8, "approved_by": "tester", "approved_at": approved_at,
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
