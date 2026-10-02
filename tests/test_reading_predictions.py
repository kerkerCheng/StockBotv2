"""圖預測對錯表（Phase 5 Step 5.4；plan §5）：每一份讀圖斷言一個機械的終局；錯的分「當時已有」與「之後才出現」。

夾具鏈（plan §5「怎麼驗」）：
- A：volume → 同日同 digest 改寫 → 圖變後 volume、帶一份新來源 ＝ rewritten＋held
- A'：同 kind、digest 變了但沒有新來源；另一條 v2→v3 digest 變 ＝ 兩筆都 rewritten（5.0 修正的負向對照）
- B：moat → 到期後 neither，新 citation 的文件早於舊讀圖 ＝ reversed／already_available
- C：volume，反證 watch 判觸及、文件晚於讀圖 ＝ disproof_touched／emerged_later
- D：undecided ＝ non_assertion
- E：撤回 ＝ retracted／undated（撤回紀錄本身是標記，不進表）
外加：真實 15 筆 ledger 的形狀（5.0 baseline §5.2 的修正後手算）逐筆相同。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from alpha.structure_reading.contracts import Citation, DisproofEntry, StructureReading
from alpha.structure_reading.predictions import (OUTCOMES, new_sources, prediction_rows, timing_kind)

TODAY = date(2026, 10, 2)
V3 = "structure-reading/v3"


def _reading(rid, node, kind, created, expires, *, supersedes=None, digest="d0", version=V3,
             cites=(), retracted=False, unit="layer") -> StructureReading:
    """契約要的欄位自動補齊（v2／v3 的斷言要反證；v3 的斷言要需求側與供給側各一段引用）——補的兩端相同，
    不影響「新來源」的比較；夾具真正在比的只有 `cites`。"""
    asserting = kind in ("moat", "volume") and not retracted
    citations: tuple = ()
    if version == V3 and (asserting or cites):
        supply = list(cites) or ["doc_supply_base"]
        citations = (Citation(angle="demand_side", edge=("tech:need", "depends_on", node), quote="d" * 30,
                              source_id="doc_demand"),) + tuple(
            Citation(angle="supply_side", edge=("co:x", "supplies_to", node), quote="q" * 30, source_id=s)
            for s in supply)
    disproof: tuple = ()
    if version != "structure-reading/v1" and asserting:
        disproof = (DisproofEntry(condition="c" * 25, entities=("co:x",), check_frequency="30 天", action_48h="重讀",
                                  source="self" if version == V3 else None),)
    return StructureReading(
        reading_id=rid, node=node, result_digest=digest, kind=kind, reading="r" * 30, angles={},
        anchor_chain=None, created_at=datetime.fromisoformat(f"{created}T06:00:00+00:00"),
        expires=date.fromisoformat(expires), supersedes_id=supersedes, retracted=retracted,
        record_version=version, unit=unit, citations=citations, disproof=disproof)


SOURCES = {"doc_old": "2026-05-01", "doc_new": "2026-11-20", "doc_a": "2026-09-01", "doc_month": "2026-09"}

CHAIN_A = [
    _reading("sr_a1", "mat:a", "volume", "2026-09-17", "2026-12-16", digest="d1", cites=["doc_a"]),
    _reading("sr_a2", "mat:a", "volume", "2026-09-17", "2026-12-16", digest="d1", cites=["doc_a"], supersedes="sr_a1"),
    _reading("sr_a3", "mat:a", "volume", "2026-11-25", "2027-02-20", digest="d2", cites=["doc_a", "doc_new"],
             supersedes="sr_a2"),
]
CHAIN_A2 = [
    _reading("sr_q1", "mat:q", "volume", "2026-09-17", "2026-12-16", digest="q1", version="structure-reading/v1"),
    _reading("sr_q2", "mat:q", "volume", "2026-09-18", "2026-12-16", digest="q2", version="structure-reading/v1",
             supersedes="sr_q1"),
    _reading("sr_q3", "mat:q", "volume", "2026-09-24", "2026-12-17", digest="q3", version="structure-reading/v2",
             supersedes="sr_q2"),
    _reading("sr_q4", "mat:q", "volume", "2026-09-25", "2026-12-24", digest="q4", cites=["doc_a"],
             supersedes="sr_q3"),
]
CHAIN_B = [
    _reading("sr_b1", "tech:b", "moat", "2026-09-20", "2026-10-20", digest="b1", cites=["doc_a"]),
    _reading("sr_b2", "tech:b", "neither", "2026-10-25", "2027-01-20", digest="b2", cites=["doc_a", "doc_old"],
             supersedes="sr_b1"),
]
CHAIN_C = [_reading("sr_c1", "tech:c", "volume", "2026-09-20", "2026-12-20", digest="c1", cites=["doc_a"])]
CHAIN_D = [_reading("sr_d1", "prod:d", "undecided", "2026-09-25", "2026-12-24", unit="socket")]
CHAIN_E = [
    _reading("sr_e1", "tech:e", "moat", "2026-09-20", "2026-12-20", digest="e1", cites=["doc_a"]),
    _reading("sr_e2", "tech:e", "moat", "2026-09-28", "2026-12-20", digest="e1", supersedes="sr_e1", retracted=True),
]
WATCHES = [
    {"watch_id": "ew_c", "kind": "semantic_condition", "source_ref": "reading:sr_c1#1", "status": "consumed",
     "judgment": {"touches": "yes", "lead_id": "lead_new", "quote": "x"}},
    # 判無關（複數 judgments）不算觸及；別的讀圖的 watch 不算
    {"watch_id": "ew_no", "kind": "semantic_condition", "source_ref": "reading:sr_a3#1", "status": "active",
     "judgments": [{"touches": "no", "lead_id": "lead_old"}]},
]
LEADS = {"lead_new": "2026-10-01", "lead_old": "2026-08-01"}


def _table(*chains, watches=WATCHES, sources=SOURCES, leads=LEADS):
    by_node: dict = {}
    for chain in chains:
        for reading in chain:
            by_node.setdefault(reading.node, []).append(reading)
    return prediction_rows(by_node, today=TODAY, watches=watches, source_published=sources, lead_published=leads)


def _outcomes(table) -> dict[str, tuple[str, str | None]]:
    return {r["reading_id"]: (r["outcome"], r["wrong_kind"]) for r in table["rows"]}


def test_every_fixture_chain_lands_in_exactly_one_outcome() -> None:
    table = _table(CHAIN_A, CHAIN_A2, CHAIN_B, CHAIN_C, CHAIN_D, CHAIN_E)
    assert _outcomes(table) == {
        "sr_a1": ("rewritten", None), "sr_a2": ("held", None), "sr_a3": ("open", None),
        "sr_q1": ("rewritten", None), "sr_q2": ("rewritten", None), "sr_q3": ("rewritten", None),
        "sr_q4": ("open", None),
        "sr_b1": ("reversed", "already_available"), "sr_b2": ("non_assertion", None),
        "sr_c1": ("disproof_touched", "emerged_later"),
        "sr_d1": ("non_assertion", None),
        "sr_e1": ("retracted", "undated"),
    }
    assert table["retraction_markers"] == 1                                   # 撤回紀錄本身不進表
    assert set(table["counts"]) == set(OUTCOMES)
    assert table["counts"]["held"] == 1 and table["counts"]["reversed"]["already_available"] == 1
    assert table["wrong_total"] == 3 and table["earliest_open_expiry"] == "2026-12-24"


def test_a_digest_change_without_new_sources_is_a_rewrite_not_a_verification() -> None:
    """5.0 修正（plan §0.6 #2）：查法改版讓 digest 變了、同讀法、沒有新來源 → 改寫。變異：拿掉條件② → 這條紅。"""
    outcomes = _outcomes(_table(CHAIN_A2))
    assert outcomes["sr_q1"][0] == outcomes["sr_q2"][0] == outcomes["sr_q3"][0] == "rewritten"


def test_staleness_never_decides_an_outcome() -> None:
    """供給側多一家（staleness 的 supply_added）不是判定：本模組沒有吃 staleness 的入口——終局只看 ledger 與判觸及。"""
    import inspect

    params = set(inspect.signature(prediction_rows).parameters)
    assert params == {"records_by_node", "today", "watches", "source_published", "lead_published"}
    # 同一份 ledger，不論圖現在怎麼變，終局都一樣（沒有任何圖的輸入）
    assert _outcomes(_table(CHAIN_C, watches=[])) == {"sr_c1": ("open", None)}


def test_missing_or_imprecise_dates_are_undated_never_emerged_later() -> None:
    """沒有日期不得壓成「之後才出現」；年月精度跨過讀圖那一天也是未定日（INV-6：不猜）。"""
    assert timing_kind([], created_on=date(2026, 9, 20)) == "undated"
    assert timing_kind([None], created_on=date(2026, 9, 20)) == "undated"
    assert timing_kind(["2026-09"], created_on=date(2026, 9, 20)) == "undated"
    assert timing_kind(["2026-08"], created_on=date(2026, 9, 20)) == "already_available"
    assert timing_kind(["2026-10"], created_on=date(2026, 9, 20)) == "emerged_later"
    assert timing_kind(["2026-11-01", None], created_on=date(2026, 9, 20)) == "undated"
    assert timing_kind(["2026-11-01", "2026-01-01"], created_on=date(2026, 9, 20)) == "already_available"
    unknown = _table(CHAIN_B, sources={})
    assert _outcomes(unknown)["sr_b1"] == ("reversed", "undated")


def test_an_unreadable_graph_is_upstream_unavailable_not_undated() -> None:
    table = _table(CHAIN_B, sources=None)
    assert _outcomes(table)["sr_b1"] == ("reversed", "upstream_unavailable")
    assert _outcomes(_table(CHAIN_C, leads=None))["sr_c1"] == ("disproof_touched", "upstream_unavailable")


def test_touched_uses_the_singular_judgment_and_the_hash_suffixed_source_ref() -> None:
    """判觸及只看單數 `judgment`；`source_ref` 是 `reading:<id>#n`（全等比對會 0 命中，L13）。"""
    plural_only = [{"watch_id": "ew", "kind": "semantic_condition", "source_ref": "reading:sr_c1#2",
                    "judgments": [{"touches": "yes"}]}]
    assert _outcomes(_table(CHAIN_C, watches=plural_only))["sr_c1"] == ("open", None)
    pq2_path = [{"watch_id": "ew", "kind": "semantic_condition", "source_ref": "reading:sr_c1#2",
                 "judgment": {"touches": "yes", "lead_id": None, "via": "watch_decision:700"}}]
    assert _outcomes(_table(CHAIN_C, watches=pq2_path))["sr_c1"] == ("disproof_touched", "undated")


def test_an_expired_reading_reread_with_the_same_kind_holds() -> None:
    """定案 #3「同 kind 取代且…已到期＝對」：到期之後才重讀，不再問 digest 或新來源。"""
    late = [_reading("sr_l1", "tech:l", "volume", "2026-09-01", "2026-09-30", digest="l1"),
            _reading("sr_l2", "tech:l", "volume", "2026-10-01", "2026-12-30", digest="l1", supersedes="sr_l1")]
    assert _outcomes(_table(late))["sr_l1"] == ("held", None)
    unread = [_reading("sr_u1", "tech:u", "moat", "2026-07-01", "2026-09-30", digest="u1")]
    assert _outcomes(_table(unread))["sr_u1"] == ("expired_unread", None)


def test_new_sources_compares_citation_sets() -> None:
    assert new_sources(CHAIN_A[2], CHAIN_A[1]) == ["doc_new"]
    assert new_sources(CHAIN_A2[1], CHAIN_A2[0]) == []
    # v2 → v3：v2 沒有引用欄，v3 的引用全是「新」——所以 schema 升版要另外判成改寫（條件②的版本那一半）
    assert set(new_sources(CHAIN_A2[3], CHAIN_A2[2])) == {"doc_a", "doc_demand"}


# ---------------------------------------------------------------------------
# 真實 ledger 的形狀（5.0 baseline §5.2 修正後手算）：held 0、錯 0、rewritten 9、open 2、non_assertion 4
# ---------------------------------------------------------------------------

def _real_shape():
    v1, v2, v3 = "structure-reading/v1", "structure-reading/v2", "structure-reading/v3"
    inp, cw = "mat:inp_substrate", "tech:cw_dfb_laser"
    inp_cites = ["axti_10_k_20260317", "reuters_inp_export_controls_2026_06_11"]
    cw_cites = ["coherent_q2fy26_cpo", "sivers_ar_2025_photonics_excerpt"]
    return [
        _reading("sr_d6760bfe5d6e9164", inp, "undecided", "2026-09-17", "2026-12-16", digest="bff24bdf", version=v1),
        _reading("sr_81832cb37d87ab1d", inp, "volume", "2026-09-17", "2026-12-16", digest="e6c668f8", version=v1,
                 supersedes="sr_d6760bfe5d6e9164"),
        _reading("sr_88340b81269fa1c2", inp, "volume", "2026-09-17", "2026-12-16", digest="e6c668f8", version=v1,
                 supersedes="sr_81832cb37d87ab1d"),
        _reading("sr_6ad5c884eb7bc3fb", inp, "volume", "2026-09-18", "2026-12-17", digest="8cad4fd6", version=v1,
                 supersedes="sr_88340b81269fa1c2"),
        _reading("sr_bc1ccb568c8886c0", inp, "volume", "2026-09-18", "2026-12-17", digest="142b3ea0", version=v1,
                 supersedes="sr_6ad5c884eb7bc3fb"),
        _reading("sr_ad503ae880ceb398", inp, "volume", "2026-09-24", "2026-12-17", digest="142b3ea0", version=v2,
                 supersedes="sr_bc1ccb568c8886c0"),
        _reading("sr_bac985bacbea64b7", inp, "volume", "2026-09-25", "2026-12-24", digest="01893fb9", version=v3,
                 supersedes="sr_ad503ae880ceb398", cites=inp_cites),
        _reading("sr_a6762186c7e8eb23", cw, "volume", "2026-09-17", "2026-10-17", digest="b74e731d", version=v1),
        _reading("sr_a181641ddb99c69c", cw, "volume", "2026-09-18", "2026-10-18", digest="c21169d0", version=v1,
                 supersedes="sr_a6762186c7e8eb23"),
        _reading("sr_caac0acae9a1c1cf", cw, "volume", "2026-09-18", "2026-10-18", digest="88f8c81e", version=v1,
                 supersedes="sr_a181641ddb99c69c"),
        _reading("sr_d07679979a8e4202", cw, "volume", "2026-09-24", "2026-10-18", digest="88f8c81e", version=v2,
                 supersedes="sr_caac0acae9a1c1cf"),
        _reading("sr_d49b81b6465e1181", cw, "volume", "2026-09-25", "2026-12-24", digest="88f8c81e", version=v3,
                 supersedes="sr_d07679979a8e4202", cites=cw_cites),
        _reading("sr_268d2fd79db629ff", "prod:supernova", "undecided", "2026-09-25", "2026-12-24", digest="a4b10c34",
                 unit="socket"),
        _reading("sr_d85d672998445c50", "prod:supernova", "undecided", "2026-10-01", "2026-12-31", digest="2fdceb23",
                 unit="socket", supersedes="sr_268d2fd79db629ff"),
        _reading("sr_35ca0ce58617d5f6", "prod:els_8ch_module", "undecided", "2026-09-25", "2026-12-24",
                 digest="5de79ccf", unit="socket"),
    ]


def test_the_real_ledger_shape_matches_the_baseline_hand_count() -> None:
    """5.0 baseline §5.2：修正後 held 0、錯 0、rewritten 9、open 2、non_assertion 4；SuperNova 09-25＝非斷言。
    變異：拿掉條件②（同 kind 只看 digest）→ held 變 5，這條紅。"""
    table = _table(_real_shape(), watches=[], sources={}, leads={})
    counts = table["counts"]
    assert (counts["held"], counts["rewritten"], counts["open"], counts["non_assertion"]) == (0, 9, 2, 4)
    assert table["wrong_total"] == 0 and counts["expired_unread"] == 0
    assert _outcomes(table)["sr_268d2fd79db629ff"] == ("non_assertion", None)
    assert table["earliest_open_expiry"] == "2026-12-24"


# ---------------------------------------------------------------------------
# 下游：structure_readings artifact v2 與心跳段 4（數字出現在消費端，L13）
# ---------------------------------------------------------------------------

def _artifact(table):
    from webapp.structure_readings import build_structure_readings_artifact

    return build_structure_readings_artifact(rows=[], predictions=table)


def test_artifact_v2_carries_the_table_with_labels_and_points_stale_elsewhere() -> None:
    from webapp.contracts import validate_state_artifact

    table = _table(CHAIN_A, CHAIN_A2, CHAIN_B, CHAIN_C, CHAIN_D, CHAIN_E)
    payload = _artifact(table)
    validate_state_artifact("structure_readings", payload)
    assert payload["schema_version"] == "stockbot-app/structure_readings/2"
    section = payload["predictions"]
    assert section["counts"] == table["counts"] and section["wrong_total"] == 3
    assert section["labels"]["outcomes"]["held"].startswith("對") and "stale" not in section["counts"]
    assert "不在這張表" in section["stale_note"]
    # 終局變了才算認知變化
    moved = dict(table, rows=[dict(r, outcome="held") if r["reading_id"] == "sr_q4" else r for r in table["rows"]])
    assert _artifact(moved)["freshness_identity"] != payload["freshness_identity"]
    assert _artifact(None)["predictions"] is None


def test_heartbeat_prints_one_line_and_three_absences_never_zero(tmp_path) -> None:
    import crons.heartbeat as hb
    from webapp.store import StateArtifactStore

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    assert hb._predictions_line(state_dir).startswith("圖預測：structure_readings artifact 讀不到")
    store = StateArtifactStore(state_dir)
    store.write(_artifact(None))
    assert "還沒有 predictions" in hb._predictions_line(state_dir) and "不是 0" in hb._predictions_line(state_dir)
    store.write(_artifact({"absence": {"kind": "point_in_time_unavailable", "reason": "預測表只有現在的視角"}}))
    assert "point_in_time_unavailable" in hb._predictions_line(state_dir)
    store.write(_artifact(_table(CHAIN_A, CHAIN_A2, CHAIN_B, CHAIN_C, CHAIN_D, CHAIN_E)))
    assert hb._predictions_line(state_dir) == (
        "圖預測：對 1｜錯 3（當時已有 1／之後才出現 1／未定日 1）｜現行 2｜到期未重讀 0｜改寫 4｜非斷言 2"
        "｜現行最早到期 2026-12-24")
    values = hb.collect_snapshot(now=datetime(2026, 10, 2, tzinfo=timezone.utc), state_dir=state_dir,
                                 leads_path=tmp_path / "none.json", thesis_path=tmp_path / "none.json",
                                 run_record_path=None, capture_dir=None)
    assert (values["predictions.held"], values["predictions.wrong"], values["predictions.expired_unread"]) == (1, 3, 0)
